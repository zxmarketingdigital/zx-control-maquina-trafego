"""Testes multiplataforma do Setup 15 (rodam em Windows, macOS e Linux, sem rede).

Uso: python -m unittest discover -s tests -v
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "setup"))

import agendador  # noqa: E402
import check_multiplataforma  # noqa: E402


def _load(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, str(caminho))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _node_sempre_executavel(test):
    """Os testes usam caminhos de node fictícios (inclusive do Windows); a checagem
    real do bit de execução tem classe própria."""
    test.node_executavel_real = agendador._node_executavel
    patch = mock.patch.object(agendador, "_node_executavel", return_value=True)
    patch.start()
    test.addCleanup(patch.stop)


def _chamada(chamadas, *prefixo):
    """Pega a chamada pelo COMEÇO dos argumentos, nunca pela posição na lista.

    O runner do CI (Linux/macOS) tem pwsh no PATH, então a instalação do Windows
    dispara também o Set-ScheduledTask de bateria e a última chamada deixa de ser
    o schtasks. Selecionar por conteúdo mantém o teste igual nos três sistemas.
    """
    alvo = list(prefixo)
    achadas = [list(c) for c in chamadas if list(c)[:len(alvo)] == alvo]
    assert len(achadas) == 1, "esperava 1 chamada %s, achei %d em %r" % (alvo, len(achadas), chamadas)
    return achadas[0]


def _proc(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


class AgendadorWindowsTest(unittest.TestCase):
    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.blog = Path(self.tmp.name) / "blog 100%"
        self.chamadas = []

        def fake_run(args, input_text=None):
            self.chamadas.append(list(args))
            return _proc(args)

        self.patch = mock.patch.object(agendador, "_run", side_effect=fake_run)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_instalar_cria_wrapper_e_tarefa(self):
        r = agendador.instalar(
            hora="07:05", blog_dir=self.blog, node_bin=r"C:\Program Files\nodejs\node.exe",
            sistema="Windows", home=self.home,
        )
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["sistema"], "Windows")
        wrapper = agendador.wrapper_path(self.home)
        conteudo = wrapper.read_bytes().decode("utf-8")
        self.assertIn("\r\n", conteudo)
        self.assertIn("chcp 65001", conteudo)
        # % dobrado para não virar variável do cmd
        self.assertIn("blog 100%%", conteudo)
        self.assertIn(r'"C:\Program Files\nodejs\node.exe" "generator\daily_publish.js"', conteudo)
        cria = _chamada(self.chamadas, "schtasks", "/Create")
        self.assertIn(agendador.windows_task_name(), cria)
        self.assertEqual(cria[cria.index("/ST") + 1], "07:05")
        self.assertEqual(cria[cria.index("/TR") + 1], '"' + str(wrapper) + '"')
        # nenhuma chamada exclusiva do macOS
        self.assertFalse(any(c[0] == "launchctl" for c in self.chamadas))
        self.assertTrue((self.blog / "logs").is_dir())

    def test_remover_apaga_tarefa_e_wrapper(self):
        agendador.instalar(blog_dir=self.blog, node_bin=r"C:\nodejs\node.exe", sistema="Windows", home=self.home)
        r = agendador.remover(sistema="Windows", home=self.home)
        self.assertTrue(r["ok"], r)
        self.assertFalse(agendador.wrapper_path(self.home).exists())
        _chamada(self.chamadas, "schtasks", "/Delete")

    def test_delete_negado_preserva_wrapper(self):
        agendador.instalar(blog_dir=self.blog, node_bin=r"C:\nodejs\node.exe", sistema="Windows", home=self.home)
        self.patch.stop()

        def fake_run(args, input_text=None):
            return _proc(args, returncode=1 if args[1] == "/Delete" else 0, stderr="Acesso negado.")

        with mock.patch.object(agendador, "_run", side_effect=fake_run):
            r = agendador.remover(sistema="Windows", home=self.home)
        self.patch.start()
        self.assertFalse(r["ok"], r)
        self.assertTrue(agendador.wrapper_path(self.home).exists())

    def test_wrapper_usa_pushd_e_propaga_codigo(self):
        agendador.instalar(blog_dir=self.blog, node_bin=r"C:\nodejs\node.exe", sistema="Windows", home=self.home)
        conteudo = agendador.wrapper_path(self.home).read_text(encoding="utf-8")
        self.assertIn('pushd "' + str(self.blog).replace("%", "%%") + '" || exit /b 1', conteudo)
        self.assertNotIn("cd /d", conteudo)
        self.assertTrue(conteudo.rstrip().endswith("exit /b %RC%"))

    def _remover_com_query_negada(self, lista_stdout):
        agendador.instalar(blog_dir=self.blog, node_bin=r"C:\nodejs\node.exe", sistema="Windows", home=self.home)
        self.patch.stop()
        chamadas = []

        def fake_run(args, input_text=None):
            chamadas.append(list(args))
            if args[:3] == ["schtasks", "/Query", "/TN"]:
                return _proc(args, returncode=1, stderr="ERRO: Acesso negado.")
            if args[:2] == ["schtasks", "/Query"]:
                return _proc(args, stdout=lista_stdout)
            return _proc(args)

        with mock.patch.object(agendador, "_run", side_effect=fake_run):
            r = agendador.remover(sistema="Windows", home=self.home)
        self.patch.start()
        self.assertFalse(any(c[:2] == ["schtasks", "/Delete"] for c in chamadas))
        return r

    def test_query_negada_com_tarefa_na_lista_preserva_wrapper(self):
        nome = agendador.windows_task_name()
        r = self._remover_com_query_negada('"\\%s","N/A","Pronto"\r\n' % nome)
        self.assertFalse(r["ok"], r)
        self.assertTrue(agendador.wrapper_path(self.home).exists())

    def test_query_falha_e_tarefa_fora_da_lista_e_ausencia(self):
        r = self._remover_com_query_negada('"\\OutraTarefa","N/A","Pronto"\r\n')
        self.assertTrue(r["ok"], r)
        self.assertFalse(agendador.wrapper_path(self.home).exists())

    def test_nome_da_tarefa_e_por_usuario(self):
        a = agendador.windows_task_name("Ana")
        b = agendador.windows_task_name("Bruno")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith(agendador.WINDOWS_TASK + "-Ana-"))
        self.assertNotEqual(agendador.windows_task_name("João"), agendador.windows_task_name("Jo_o"))
        self.assertRegex(agendador.windows_task_name("Ana&Leo Silva"), r"^[A-Za-z0-9_-]+$")

    def test_hora_invalida_nao_chama_nada(self):
        r = agendador.instalar(hora="25:00", blog_dir=self.blog, node_bin="node",
                               sistema="Windows", home=self.home)
        self.assertFalse(r["ok"])
        self.assertEqual(self.chamadas, [])

    def test_schtasks_ausente_retorna_erro_sem_lancar(self):
        self.patch.stop()
        with mock.patch.object(agendador, "_run", return_value=None):
            r = agendador.instalar(blog_dir=self.blog, node_bin=r"C:\nodejs\node.exe", sistema="Windows", home=self.home)
        self.patch.start()
        self.assertFalse(r["ok"])


class AgendadorLinuxTest(unittest.TestCase):
    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.blog = Path(self.tmp.name) / "blog"
        self.crontab = (
            "0 1 * * * echo outro\n"
            "0 2 * * * echo backup # zx-setup15-blog-daily-backup\n"
        )

        def fake_run(args, input_text=None):
            if args[:2] == ["crontab", "-l"]:
                return _proc(args, stdout=self.crontab)
            if args[:2] == ["crontab", "-"]:
                self.crontab = input_text
                return _proc(args)
            raise AssertionError(args)

        self.patches = [
            mock.patch.object(agendador, "_run", side_effect=fake_run),
            mock.patch.object(agendador.shutil, "which", return_value="/usr/bin/crontab"),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_instalar_e_idempotente_e_preserva_outras_linhas(self):
        for _ in range(2):
            r = agendador.instalar(hora="08:30", blog_dir=self.blog, node_bin="/usr/bin/node", sistema="Linux")
            self.assertTrue(r["ok"], r)
        nossas = [l for l in self.crontab.splitlines() if agendador._linha_nossa(l)]
        self.assertEqual(len(nossas), 1)
        self.assertIn("echo outro", self.crontab)
        self.assertIn("zx-setup15-blog-daily-backup", self.crontab)
        self.assertIn("30 8 * * *", self.crontab)
        self.assertTrue(agendador.status(sistema="Linux")["ok"])
        r = agendador.remover(sistema="Linux")
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.crontab.count(agendador.CRON_MARKER), 1)  # só a do backup
        self.assertIn("zx-setup15-blog-daily-backup", self.crontab)
        self.assertFalse(agendador.status(sistema="Linux")["ok"])
        self.assertIn("echo outro", self.crontab)


class CrontabAtualTest(unittest.TestCase):
    """_crontab_atual() só pode tratar como vazio o caso 'no crontab for <user>';
    qualquer outro returncode != 0 tem que abortar (None), nunca sobrescrever
    o crontab do usuário com só as nossas linhas."""

    def setUp(self):
        self.patches = [mock.patch.object(agendador.shutil, "which", return_value="/usr/bin/crontab")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _com_run(self, returncode, stdout="", stderr=""):
        proc = _proc(["crontab", "-l"], returncode=returncode, stdout=stdout, stderr=stderr)
        return mock.patch.object(agendador, "_run", return_value=proc)

    def test_ok_devolve_conteudo(self):
        with self._com_run(0, stdout="0 1 * * * echo oi\n"):
            self.assertEqual(agendador._crontab_atual(), "0 1 * * * echo oi\n")

    def test_no_crontab_for_vira_vazio(self):
        with self._com_run(1, stderr="no crontab for rafael\n"):
            self.assertEqual(agendador._crontab_atual(), "")

    def test_erro_generico_aborta_sem_virar_vazio(self):
        with self._com_run(1, stderr="crontab: spool ilegível\n"):
            self.assertIsNone(agendador._crontab_atual())

    def test_remover_com_crontab_ilegivel_nao_finge_sucesso(self):
        with self._com_run(1, stderr="crontab: spool ilegível\n"):
            r = agendador.remover(sistema="Linux")
        self.assertFalse(r["ok"], r)

    def test_instalar_com_crontab_ilegivel_aborta_com_mensagem_clara(self):
        # Chamador ponta-a-ponta: erro genérico do "crontab -l" não pode virar
        # gravação de crontab só com a nossa linha (perda dos agendamentos do
        # usuário) nem lançar traceback cru — tem que devolver ok=False com detalhe
        # que fale da LEITURA (não de uma falha de escrita disfarçada).
        #
        # 🔴 luna-review (17/09): a versão anterior mockava `_run` com
        # `return_value` fixo, então uma regressão que reintroduzisse o bug
        # (tratar rc!=0 como vazio e seguir para `crontab -` de gravação)
        # também bateria em returncode=1 e passaria — ok=False vindo da
        # ESCRITA, não do abort esperado na LEITURA. Corrigido: side_effect
        # que registra as chamadas e falha o teste se "crontab -" (gravação)
        # for invocado.
        chamadas = []

        def fake_run(args, input_text=None):
            chamadas.append(list(args))
            if args == ["crontab", "-"]:
                # Nenhuma gravação pode acontecer depois de leitura ilegível.
                return _proc(args, returncode=0)
            return _proc(args, returncode=1, stderr="crontab: spool ilegível\n")

        with mock.patch.object(agendador, "_run", side_effect=fake_run):
            r = agendador.instalar(sistema="Linux", blog_dir=Path("/tmp/blog"), node_bin="node")

        self.assertFalse(r["ok"], r)
        self.assertIsInstance(r["detalhe"], str)
        self.assertNotIn("Traceback", r["detalhe"])
        self.assertIn("crontab", r["detalhe"].lower())
        self.assertIn(["crontab", "-l"], chamadas)
        self.assertNotIn(["crontab", "-"], chamadas)


class AgendadorDarwinRemoverTest(unittest.TestCase):
    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.plist = agendador.plist_path(self.home)
        self.plist.parent.mkdir(parents=True)
        self.plist.write_text("<plist quebrado", encoding="utf-8")
        self.carregado = True
        self.remove_funciona = True

        def fake_run(args, input_text=None):
            if args[:2] == ["launchctl", "unload"]:
                return _proc(args, returncode=1, stderr="Invalid property list")
            if args[:2] == ["launchctl", "remove"]:
                if self.remove_funciona:
                    self.carregado = False
                return _proc(args, returncode=0 if self.remove_funciona else 1)
            if args[:2] == ["launchctl", "list"]:
                linha = "-\t0\t%s\n" % agendador.LABEL if self.carregado else ""
                return _proc(args, stdout="-\t0\tcom.apple.x\n" + linha)
            return _proc(args)

        self.patch = mock.patch.object(agendador, "_run", side_effect=fake_run)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_unload_falho_remove_pelo_label(self):
        r = agendador.remover(sistema="Darwin", home=self.home)
        self.assertTrue(r["ok"], r)
        self.assertFalse(self.plist.exists())

    def test_job_que_nao_sai_preserva_plist(self):
        self.remove_funciona = False
        r = agendador.remover(sistema="Darwin", home=self.home)
        self.assertFalse(r["ok"], r)
        self.assertTrue(self.plist.exists())

    def test_plist_ausente_mas_job_carregado_e_removido(self):
        self.plist.unlink()
        r = agendador.remover(sistema="Darwin", home=self.home)
        self.assertTrue(r["ok"], r)
        self.assertFalse(self.carregado)


class AgendadorLinuxCaminhoTest(AgendadorLinuxTest):
    def test_blog_relativo_vira_absoluto_no_crontab(self):
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            r = agendador.instalar(blog_dir=Path("blog"), node_bin="/usr/bin/node", sistema="Linux")
        finally:
            os.chdir(cwd)
        self.assertTrue(r["ok"], r)
        linha = [l for l in self.crontab.splitlines() if agendador._linha_nossa(l)][0]
        self.assertIn(os.path.abspath(str(self.blog)).replace("%", "\\%"), linha)
        self.assertNotIn("cd blog ", linha)

    def test_barra_invertida_no_caminho_recusa_sem_gravar(self):
        antes = self.crontab
        blog = Path(self.tmp.name) / "a\\%b" / "blog"
        r = agendador.instalar(blog_dir=blog, node_bin="/usr/bin/node", sistema="Linux")
        self.assertFalse(r["ok"], r)
        self.assertEqual(self.crontab, antes)


class AgendadorDarwinInstalarTest(unittest.TestCase):
    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.blog = self.home / "blog"
        self.carregado = True  # job antigo em memória, sem plist no disco
        self.remove_funciona = True
        self.load_rc = 0
        self.chamadas = []

        def fake_run(args, input_text=None):
            self.chamadas.append(args[:2])
            if args[:2] == ["launchctl", "remove"]:
                if self.remove_funciona:
                    self.carregado = False
                return _proc(args)
            if args[:2] == ["launchctl", "load"]:
                if self.load_rc == 0:
                    self.carregado = True
                return _proc(args, returncode=self.load_rc, stderr="Load failed")
            if args[:2] == ["launchctl", "list"]:
                linha = "-\t0\t%s\n" % agendador.LABEL if self.carregado else ""
                return _proc(args, stdout=linha)
            return _proc(args)

        self.patch = mock.patch.object(agendador, "_run", side_effect=fake_run)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_plist_nao_reprocessa_marcador_no_caminho(self):
        blog = self.home / "curso-{HOME}" / "blog"
        r = agendador.instalar(blog_dir=blog, node_bin="/usr/local/bin/node",
                               sistema="Darwin", home=self.home)
        self.assertTrue(r["ok"], r)
        plist = agendador.plist_path(self.home).read_text(encoding="utf-8")
        self.assertIn("curso-{HOME}", plist)

    def _instalar(self):
        return agendador.instalar(hora="10:00", blog_dir=self.blog, node_bin="/usr/bin/node",
                                  sistema="Darwin", home=self.home)

    def test_job_antigo_sem_plist_e_removido_antes_do_load(self):
        r = self._instalar()
        self.assertTrue(r["ok"], r)
        self.assertLess(self.chamadas.index(["launchctl", "remove"]),
                        self.chamadas.index(["launchctl", "load"]))

    def test_job_antigo_que_nao_sai_aborta_sem_load(self):
        self.remove_funciona = False
        r = self._instalar()
        self.assertFalse(r["ok"], r)
        self.assertNotIn(["launchctl", "load"], self.chamadas)

    def test_load_falho_nao_finge_sucesso(self):
        self.load_rc = 1
        r = self._instalar()
        self.assertFalse(r["ok"], r)


class AgendadorProtecoesTest(unittest.TestCase):
    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_nao_traduz_cr(self):
        eco = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"
        lido = agendador._run([sys.executable, "-c", eco], input_text="a\r#b\n")
        self.assertEqual(lido.stdout, "a\r#b\n")

    def test_run_preserva_bytes_que_nao_decodificam(self):
        legado = b"# manuten\xe7\xe3o \x81\x8d\n"
        eco = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"
        lido = agendador._run([sys.executable, "-c",
                               "import sys; sys.stdout.buffer.write(%r)" % legado])
        self.assertIsNotNone(lido)
        self.assertEqual(lido.returncode, 0)
        devolvido = agendador._run([sys.executable, "-c", eco], input_text=lido.stdout)
        self.assertEqual(devolvido.stdout, lido.stdout)
        import locale
        enc = locale.getpreferredencoding(False)
        self.assertEqual(devolvido.stdout.encode(enc, "surrogateescape"), legado)

    def test_status_com_erro_de_disco_devolve_dict(self):
        with mock.patch.object(agendador, "_status_darwin", side_effect=PermissionError("negado")):
            r = agendador.status(sistema="Darwin", home=self.base)
        self.assertFalse(r["ok"])
        self.assertIn("negado", r["detalhe"])

    def test_node_relativo_vira_absoluto(self):
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            resolvido = agendador._resolver_node("./runtime/node")
            esperado = os.path.join(os.getcwd(), "runtime", "node")
        finally:
            os.chdir(cwd)
        self.assertTrue(os.path.isabs(resolvido))
        self.assertEqual(resolvido, esperado)
        self.assertEqual(agendador._resolver_node(r"C:\nodejs\node.exe"), r"C:\nodejs\node.exe")
        with mock.patch.object(agendador.shutil, "which", return_value="./bin/node"):
            self.assertEqual(agendador._resolver_node("node"),
                             os.path.join(os.getcwd(), "bin", "node"))
        with mock.patch.object(agendador.shutil, "which", return_value=None):
            r = agendador.instalar(blog_dir=self.base / "blog", node_bin="node", sistema="Linux")
        self.assertFalse(r["ok"], r)

    def test_node_sem_permissao_de_execucao_nao_mexe_no_agendamento(self):
        node = self.base / "node"
        node.write_text("#!/bin/sh\n", encoding="utf-8")
        node.chmod(0o644)
        with mock.patch.object(agendador, "_node_executavel", self.node_executavel_real), \
                mock.patch.object(agendador, "_run", side_effect=AssertionError("não devia agendar")):
            r = agendador.instalar(blog_dir=self.base / "blog", node_bin=str(node), sistema="Linux")
        self.assertFalse(r["ok"], r)
        self.assertIn("executável", r["detalhe"])
        node.chmod(0o755)
        self.assertTrue(self.node_executavel_real(str(node)))
        self.assertFalse(self.node_executavel_real(str(self.base)))

    def test_windows_home_com_percentual_recusa_sem_tocar_em_nada(self):
        home = self.base / "%USERNAME%"
        with mock.patch.object(agendador, "_run", side_effect=AssertionError("não devia chamar")):
            r = agendador.instalar(blog_dir=self.base / "blog", node_bin=r"C:\nodejs\node.exe",
                                   sistema="Windows", home=home)
        self.assertFalse(r["ok"], r)
        self.assertFalse(agendador.wrapper_path(home).exists())

    def test_windows_create_falho_restaura_wrapper_anterior(self):
        home = self.base / "home"
        wrapper = agendador.wrapper_path(home)
        wrapper.parent.mkdir(parents=True)
        wrapper.write_bytes(b"wrapper antigo")
        falha = lambda a, input_text=None: _proc(a, returncode=1, stderr="Servico parado")
        with mock.patch.object(agendador, "_run", side_effect=falha):
            r = agendador.instalar(blog_dir=self.base / "blog B", node_bin=r"C:\nodejs\node.exe",
                                   sistema="Windows", home=home)
        self.assertFalse(r["ok"], r)
        self.assertEqual(wrapper.read_bytes(), b"wrapper antigo")
        wrapper.unlink()
        with mock.patch.object(agendador, "_run", side_effect=falha):
            agendador.instalar(blog_dir=self.base / "blog B", node_bin=r"C:\nodejs\node.exe",
                               sistema="Windows", home=home)
        self.assertFalse(wrapper.exists())


class AgendadorWindowsCondicoesTest(unittest.TestCase):
    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.chamadas = []
        self.ps_rc = 0

        def fake_run(args, input_text=None):
            self.chamadas.append(args)
            if "powershell" in args[0]:
                return _proc(args, returncode=self.ps_rc, stderr="sem modulo")
            return _proc(args)

        self.patch_run = mock.patch.object(agendador, "_run", side_effect=fake_run)
        self.patch_run.start()
        self.patch_which = mock.patch.object(
            agendador.shutil, "which",
            side_effect=lambda nome: r"C:\\Windows\\powershell.exe" if nome in ("powershell", "pwsh") else nome,
        )
        self.patch_which.start()

    def tearDown(self):
        self.patch_which.stop()
        self.patch_run.stop()
        self.tmp.cleanup()

    def _instalar(self):
        return agendador.instalar(blog_dir=self.home / "blog", node_bin=r"C:\\nodejs\\node.exe",
                                  sistema="Windows", home=self.home)

    def test_wrapper_desliga_expansao_atrasada(self):
        r = self._instalar()
        self.assertTrue(r["ok"], r)
        linhas = agendador.wrapper_path(self.home).read_text(encoding="utf-8").splitlines()
        self.assertEqual(linhas[1].lower(), "setlocal enableextensions disabledelayedexpansion")
        primeiro_pushd = next(i for i, l in enumerate(linhas) if l.startswith("pushd "))
        self.assertLess(1, primeiro_pushd)

    def test_libera_execucao_na_bateria(self):
        r = self._instalar()
        self.assertTrue(r["ok"], r)
        ps = [a for a in self.chamadas if "powershell" in a[0]]
        self.assertEqual(len(ps), 1, self.chamadas)
        comando = ps[0][-1]
        self.assertIn("-AllowStartIfOnBatteries", comando)
        self.assertIn("-DontStopIfGoingOnBatteries", comando)
        self.assertIn(agendador.windows_task_name(), comando)
        self.assertNotIn("bateria", r["detalhe"])

    def test_powershell_falho_nao_derruba_instalacao(self):
        self.ps_rc = 1
        r = self._instalar()
        self.assertTrue(r["ok"], r)
        self.assertIn("bateria", r["detalhe"])
        self.assertTrue(agendador.wrapper_path(self.home).exists())


class AgendadorRollbackTest(unittest.TestCase):
    """Uma instalação frustrada não pode derrubar o agendamento que já funcionava."""

    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.plist = agendador.plist_path(self.home)
        self.plist.parent.mkdir(parents=True, exist_ok=True)
        self.plist.write_bytes(b"<plist>anterior</plist>")
        self.carregado = True
        self.load_rc = 0
        self.chamadas = []

        def fake_run(args, input_text=None):
            self.chamadas.append(args[:2])
            if args[:2] == ["launchctl", "remove"]:
                self.carregado = False
            elif args[:2] == ["launchctl", "load"]:
                if self.load_rc == 0:
                    self.carregado = True
                return _proc(args, returncode=self.load_rc, stderr="Load failed")
            elif args[:2] == ["launchctl", "list"]:
                return _proc(args, stdout="-\t0\t%s\n" % agendador.LABEL if self.carregado else "")
            return _proc(args)

        self.patch = mock.patch.object(agendador, "_run", side_effect=fake_run)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _instalar(self):
        return agendador.instalar(blog_dir=self.home / "blog", node_bin="/usr/local/bin/node",
                                  sistema="Darwin", home=self.home)

    def test_plist_ilegivel_nao_descarrega_job_antigo(self):
        with mock.patch.object(agendador, "_gravar_atomico",
                               side_effect=PermissionError("somente leitura")):
            r = self._instalar()
        self.assertFalse(r["ok"], r)
        self.assertEqual(self.plist.read_bytes(), b"<plist>anterior</plist>")
        self.assertNotIn(["launchctl", "unload"], self.chamadas)
        self.assertNotIn(["launchctl", "remove"], self.chamadas)
        self.assertTrue(self.carregado)

    def test_load_falho_restaura_e_recarrega_o_plist_anterior(self):
        self.load_rc = 1
        r = self._instalar()
        self.assertFalse(r["ok"], r)
        self.assertEqual(self.plist.read_bytes(), b"<plist>anterior</plist>")
        self.assertEqual(self.chamadas.count(["launchctl", "load"]), 2)


class AgendadorCronSeparadorTest(unittest.TestCase):
    """O crontab separa registros só por LF: U+2028 num caminho não pode virar linha nova."""

    def setUp(self):
        _node_sempre_executavel(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.blog = Path(self.tmp.name) / "blog\u2028novo"
        self.crontab = "0 5 * * * /usr/bin/backup.sh\n"

        def fake_run(args, input_text=None):
            if args[:2] == ["crontab", "-l"]:
                return _proc(args, stdout=self.crontab)
            if args[:1] == ["crontab"]:
                self.crontab = input_text
                return _proc(args)
            return _proc(args)

        self.patch_run = mock.patch.object(agendador, "_run", side_effect=fake_run)
        self.patch_run.start()
        self.patch_which = mock.patch.object(agendador.shutil, "which",
                                             side_effect=lambda nome: "/usr/bin/" + nome)
        self.patch_which.start()

    def tearDown(self):
        self.patch_which.stop()
        self.patch_run.stop()
        self.tmp.cleanup()

    def test_cr_em_linha_alheia_sobrevive(self):
        # text=True traduziria o CR em LF e partiria o comando do vizinho em duas linhas.
        self.crontab = "0 1 * * * /usr/bin/printf 'A\r#B' >> /tmp/probe\n"
        original = self.crontab
        r = agendador.instalar(blog_dir=self.blog, node_bin="/usr/bin/node", sistema="Linux")
        self.assertTrue(r["ok"], r)
        self.assertIn(original.rstrip("\n"), self.crontab)
        r = agendador.remover(sistema="Linux")
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.crontab, original)

    def test_instalar_remover_nao_deixa_fragmento(self):
        r = agendador.instalar(blog_dir=self.blog, node_bin="/usr/bin/node", sistema="Linux")
        self.assertTrue(r["ok"], r)
        nossas = [l for l in self.crontab.split("\n") if agendador.CRON_MARKER in l]
        self.assertEqual(len(nossas), 1, self.crontab)

        r = agendador.instalar(blog_dir=self.blog, node_bin="/usr/bin/node", sistema="Linux")
        self.assertTrue(r["ok"], r)
        self.assertEqual(len([l for l in self.crontab.split("\n") if agendador.CRON_MARKER in l]), 1)

        r = agendador.remover(sistema="Linux")
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.crontab, "0 5 * * * /usr/bin/backup.sh\n")
        self.assertNotIn("daily_publish", self.crontab)


class AgendadorSemSuporteTest(unittest.TestCase):
    def test_sistema_desconhecido_nao_lanca(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = agendador.instalar(blog_dir=Path(tmp), node_bin="node", sistema="Plan9")
        self.assertFalse(r["ok"])
        self.assertIn("manualmente", r["detalhe"])


class LockTest(unittest.TestCase):
    """O lock precisa serializar de verdade no sistema em que o teste roda."""

    def _exercitar(self, lock_factory):
        ordem = []

        def trabalhador(nome):
            with lock_factory():
                ordem.append(nome + ":in")
                time.sleep(0.2)
                ordem.append(nome + ":out")

        threads = [threading.Thread(target=trabalhador, args=(n,)) for n in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        self.assertEqual(len(ordem), 4)
        # entradas e saídas nunca intercaladas
        self.assertEqual(ordem[0][0], ordem[1][0])
        self.assertEqual(ordem[2][0], ordem[3][0])

    def test_lock_gerar_imagem(self):
        gerar = _load("gerar_mod", ROOT / "skills/gerar-imagem/scripts/gerar.py")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(gerar, "GERAR_LOCK", os.path.join(tmp, "g.lock")):
                self._exercitar(gerar.codex_lock)

    def test_lock_ledger_google(self):
        mod = _load("gcamp_mod", ROOT / "skills/google-campaign/scripts/build_campaign_google.py")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(mod, "LEDGER_PATH", Path(tmp) / "ledger.json"):
                self._exercitar(mod._ledger_lock)


class TimeoutImagemTest(unittest.TestCase):
    def test_env_do_timeout(self):
        gerar = _load("gerar_mod_t", ROOT / "skills/gerar-imagem/scripts/gerar.py")
        casos = {None: 600, "900": 900, "abc": 600, "0": 600, "-5": 600}
        for valor, esperado in casos.items():
            env = dict(os.environ)
            env.pop("ZX_IMAGE2_TIMEOUT", None)
            if valor is not None:
                env["ZX_IMAGE2_TIMEOUT"] = valor
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(gerar._image2_timeout(), esperado, valor)


class TetoDeProcessoTest(unittest.TestCase):
    """O teto do image2 precisa valer mesmo com um processo neto segurando os pipes."""

    def test_timeout_derruba_arvore(self):
        gerar = _load("gerar_mod_teto", ROOT / "skills/gerar-imagem/scripts/gerar.py")
        neto = "import time; time.sleep(60)"
        filho = ("import subprocess, sys, time; "
                 "subprocess.Popen([sys.executable, '-c', %r]); time.sleep(60)" % neto)
        inicio = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            gerar._run_com_teto([sys.executable, "-c", filho], "prompt com acento: promoção ☕", 2)
        self.assertLess(time.monotonic() - inicio, 12)

    def test_stdin_utf8_chega_inteiro(self):
        gerar = _load("gerar_mod_utf8", ROOT / "skills/gerar-imagem/scripts/gerar.py")
        codigo = "import sys; dado = sys.stdin.buffer.read(); sys.stdout.buffer.write(dado.decode('utf-8')[::-1].encode('utf-8'))"
        r = gerar._run_com_teto([sys.executable, "-c", codigo], "café ☕", 30)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "☕ éfac")


class CodexArgvTest(unittest.TestCase):
    """No Windows o shim codex.cmd passa pelo cmd.exe; o entrypoint JS evita isso."""

    def test_windows_cmd_usa_node_e_entrypoint(self):
        gerar = _load("gerar_mod_argv", ROOT / "skills/gerar-imagem/scripts/gerar.py")
        with tempfile.TemporaryDirectory() as tmp:
            npm_dir = os.path.join(tmp, "Ana&Leo", "npm")
            entry = os.path.join(npm_dir, "node_modules", "@openai", "codex", "bin", "codex.js")
            os.makedirs(os.path.dirname(entry))
            Path(entry).write_text("", encoding="utf-8")
            shim = os.path.join(npm_dir, "codex.cmd")
            achados = {"codex": shim, "node": "node.exe"}
            with mock.patch.object(gerar.os, "name", "nt"), \
                    mock.patch.object(gerar.shutil, "which", side_effect=achados.get):
                self.assertEqual(gerar._codex_argv(), ["node.exe", entry])
            with mock.patch.object(gerar.os, "name", "posix"), \
                    mock.patch.object(gerar.shutil, "which", side_effect=achados.get):
                self.assertEqual(gerar._codex_argv(), [shim])
            with mock.patch.object(gerar.shutil, "which", return_value=None):
                self.assertIsNone(gerar._codex_argv())


class CheckEstaticoTest(unittest.TestCase):
    def test_repo_sem_dependencia_exclusiva_do_macos(self):
        achados = check_multiplataforma.varrer() + check_multiplataforma.ast_39()
        self.assertEqual(achados, [], "\n".join(map(str, achados)))

    def test_check_pega_regressao(self):
        linha = "subprocess.run(['python3', 'x.py'])"
        self.assertTrue(any(p.search(linha) for p, _ in check_multiplataforma.PADROES))


if __name__ == "__main__":
    unittest.main()
