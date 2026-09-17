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


def _proc(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


class AgendadorWindowsTest(unittest.TestCase):
    def setUp(self):
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
        cria = self.chamadas[-1]
        self.assertEqual(cria[:2], ["schtasks", "/Create"])
        self.assertIn(agendador.WINDOWS_TASK, cria)
        self.assertEqual(cria[cria.index("/ST") + 1], "07:05")
        self.assertEqual(cria[cria.index("/TR") + 1], '"' + str(wrapper) + '"')
        # nenhuma chamada exclusiva do macOS
        self.assertFalse(any(c[0] == "launchctl" for c in self.chamadas))
        self.assertTrue((self.blog / "logs").is_dir())

    def test_remover_apaga_tarefa_e_wrapper(self):
        agendador.instalar(blog_dir=self.blog, node_bin="node", sistema="Windows", home=self.home)
        r = agendador.remover(sistema="Windows", home=self.home)
        self.assertTrue(r["ok"], r)
        self.assertFalse(agendador.wrapper_path(self.home).exists())
        self.assertEqual(self.chamadas[-1][:2], ["schtasks", "/Delete"])

    def test_hora_invalida_nao_chama_nada(self):
        r = agendador.instalar(hora="25:00", blog_dir=self.blog, node_bin="node",
                               sistema="Windows", home=self.home)
        self.assertFalse(r["ok"])
        self.assertEqual(self.chamadas, [])

    def test_schtasks_ausente_retorna_erro_sem_lancar(self):
        self.patch.stop()
        with mock.patch.object(agendador, "_run", return_value=None):
            r = agendador.instalar(blog_dir=self.blog, node_bin="node", sistema="Windows", home=self.home)
        self.patch.start()
        self.assertFalse(r["ok"])


class AgendadorLinuxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.blog = Path(self.tmp.name) / "blog"
        self.crontab = "0 1 * * * echo outro\n"

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
        self.assertEqual(self.crontab.count(agendador.CRON_MARKER), 1)
        self.assertIn("echo outro", self.crontab)
        self.assertIn("30 8 * * *", self.crontab)
        self.assertTrue(agendador.status(sistema="Linux")["ok"])
        r = agendador.remover(sistema="Linux")
        self.assertTrue(r["ok"], r)
        self.assertNotIn(agendador.CRON_MARKER, self.crontab)
        self.assertIn("echo outro", self.crontab)


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
