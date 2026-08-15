#!/usr/bin/env python3
"""Testes do fluxo Google Ads da Etapa 4.

Isolamento: cada teste aponta HOME para um diretório temporário ANTES de
importar o módulo, porque os caminhos de configuração são resolvidos no import.
Nunca reatribuir as constantes do módulo depois de importado — os valores
default dos parâmetros já foram capturados e continuariam apontando para o
arquivo real do usuário.
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent / "setup_pago_meta_google.py"


class FluxoGoogleTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home_original = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_dir.name
        spec = importlib.util.spec_from_file_location("setup_pago_google_test", SETUP)
        self.setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.setup)
        # Prova o isolamento em vez de afirmá-lo: se falhar, o teste escreveria
        # na configuração real de quem rodou a suíte.
        self.assertTrue(str(self.setup.GOOGLE_ENV).startswith(self.temp_dir.name))
        self.assertTrue(str(self.setup.META_PROFILE).startswith(self.temp_dir.name))
        self.setup.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.instaladas = []
        self.setup.instalar_skill = self.instaladas.append

    def tearDown(self):
        if self.home_original is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.home_original
        self.temp_dir.cleanup()

    def rodar(self, respostas):
        env, saida, _ = self.rodar_com_estado(respostas)
        return env, saida

    def rodar_com_estado(self, respostas):
        fila = list(respostas)
        self.setup.resposta = lambda prompt, default="": (fila.pop(0) if fila else default)
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            estado = self.setup.executar_google()
        return self.setup.ler_env(self.setup.GOOGLE_ENV), saida.getvalue(), estado

    def test_pular_nao_instala_skill_nem_pede_perfil(self):
        env, _ = self.rodar(["pular"])
        self.assertEqual(env.get("STATUS"), "skipped")
        self.assertEqual(self.instaladas, [])
        self.assertFalse(self.setup.GOOGLE_PROFILE.exists())

    def test_customer_id_invalido_nao_e_gravado(self):
        # Normalizar antes de validar faria '1234567890x' virar conta boa.
        env, _ = self.rodar(["sim", "1234567890x"])
        self.assertEqual(env.get("STATUS"), "pending")
        self.assertNotIn("GOOGLE_ADS_CUSTOMER_ID", env)
        self.assertEqual(self.instaladas, [])

    def test_sem_credencial_fica_pendente_e_nao_instala(self):
        env, _ = self.rodar(["sim", "123-456-7890", "", "pular", "pular"])
        self.assertEqual(env.get("STATUS"), "pending")
        self.assertEqual(self.instaladas, [])

    def test_refresh_token_sozinho_conecta(self):
        env, saida = self.rodar(
            ["sim", "123-456-7890", "", "", "1//refresh-real", "vendas", "cpa=80", "cpa"]
        )
        self.assertEqual(env.get("STATUS"), "connected")
        self.assertEqual(env.get("GOOGLE_ADS_CUSTOMER_ID"), "1234567890")
        self.assertNotIn(self.setup.GOOGLE_TOKEN_NAME, env, "não pode inventar access token")
        self.assertNotIn("1//refresh-real", saida, "credencial não pode aparecer na saída")
        self.assertEqual(
            sorted(self.instaladas), ["google-metrics-fetcher", "google-performance-analyzer"]
        )
        perfil = json.loads(self.setup.GOOGLE_PROFILE.read_text(encoding="utf-8"))
        self.assertTrue(perfil["primary_kpi"])
        self.assertEqual(oct(self.setup.GOOGLE_ENV.stat().st_mode)[-3:], "600")

    def test_perfil_google_nao_sobrescreve_o_do_meta(self):
        valido = {
            "objectives": ["vendas"],
            "metrics": [{"name": "roas", "target": 2.0}],
            "primary_kpi": "roas",
            "tag": "meta",
        }
        self.setup.salvar_perfil(valido)
        self.setup.salvar_perfil({**valido, "tag": "google"}, self.setup.GOOGLE_PROFILE)
        self.assertEqual(self.setup.carregar_perfil()["tag"], "meta")
        self.assertEqual(self.setup.carregar_perfil(self.setup.GOOGLE_PROFILE)["tag"], "google")
        # O default do Meta precisa continuar sendo o arquivo do Meta: foi
        # parametrizar sem preservar isso que sobrescreveu um perfil real.
        self.assertEqual(self.setup.salvar_perfil.__defaults__, (self.setup.META_PROFILE,))
        self.assertEqual(self.setup.carregar_perfil.__defaults__, (self.setup.META_PROFILE,))

    def test_customer_id_invalido_no_env_nao_e_reaproveitado(self):
        # Normalizar antes de validar transformaria o lixo gravado à mão em
        # conta boa, e as skills seriam instaladas apontando para ela.
        self.setup.atualizar_env(
            self.setup.GOOGLE_ENV,
            {
                "GOOGLE_ADS_CUSTOMER_ID": "1234567890x",
                "GOOGLE_ADS_REFRESH_TOKEN": "1//refresh-real",
            },
        )
        self.setup.salvar_perfil(
            {
                "objectives": ["vendas"],
                "metrics": [{"name": "cpa", "target": 80.0}],
                "primary_kpi": "cpa",
            },
            self.setup.GOOGLE_PROFILE,
        )
        env, saida, estado = self.rodar_com_estado(["pular"])
        self.assertEqual(estado, "skipped")
        self.assertEqual(self.instaladas, [], "instalou skill com conta não confirmada")
        self.assertIn("10 dígitos", saida)
        self.assertEqual(env.get("GOOGLE_ADS_CUSTOMER_ID"), "1234567890x")

    def test_refresh_token_existente_e_reaproveitado_sem_redigitar(self):
        self.setup.atualizar_env(self.setup.GOOGLE_ENV, {"GOOGLE_ADS_REFRESH_TOKEN": "1//ja-salvo"})
        # Enter nos dois prompts de credencial: "não tenho nada novo".
        env, _, estado = self.rodar_com_estado(
            ["sim", "123-456-7890", "", "", "", "vendas", "cpa=80", "cpa"]
        )
        self.assertEqual(estado, "connected")
        self.assertEqual(env.get("STATUS"), "connected")
        self.assertEqual(env.get("GOOGLE_ADS_REFRESH_TOKEN"), "1//ja-salvo")

    def test_login_customer_id_da_mcc_e_gravado(self):
        env, _, estado = self.rodar_com_estado(
            ["sim", "123-456-7890", "999-999-9999", "", "1//refresh", "vendas", "cpa=80", "cpa"]
        )
        self.assertEqual(estado, "connected")
        self.assertEqual(env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"), "9999999999")

    def test_segunda_execucao_com_so_refresh_token_reaproveita_a_instalacao(self):
        """Refresh-only já conectado NÃO pode ser rebaixado para skipped.

        credencial_google devolve o refresh quando não há access token, então
        instalacao_valida enxerga a conexão e nem chega a perguntar. Se alguém
        fizer instalacao_valida olhar só o access token, o aluno que conectou
        por refresh volta a ser tratado como desconectado e um 'pular' apaga
        uma conexão que funcionava.
        """
        self.setup.atualizar_env(
            self.setup.GOOGLE_ENV,
            {
                "GOOGLE_ADS_REFRESH_TOKEN": "1//refresh-real",
                "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
                "STATUS": "connected",
            },
        )
        self.setup.salvar_perfil(
            {
                "objectives": ["vendas"],
                "metrics": [{"name": "cpa", "target": 80.0}],
                "primary_kpi": "cpa",
            },
            self.setup.GOOGLE_PROFILE,
        )
        # Nenhuma resposta na fila: se o fluxo perguntar algo, cai no default
        # 'pular' e o teste pega o rebaixamento.
        env, saida, estado = self.rodar_com_estado([])
        self.assertEqual(estado, "connected")
        self.assertEqual(env.get("STATUS"), "connected")
        self.assertNotIn("1//refresh-real", saida)
        self.assertEqual(
            sorted(self.instaladas), ["google-metrics-fetcher", "google-performance-analyzer"]
        )

    def test_enter_preserva_a_mcc_ja_salva(self):
        """Trava a semântica de merge do .env, não um ramo do executar_google.

        Hoje a preservação vem de atualizar_env, que só reescreve as chaves
        recebidas — este teste fica verde mesmo mexendo no cálculo do login_id.
        Ele existe para o dia em que alguém passar a gravar a chave sempre (com
        "" quando o aluno der Enter) ou tornar atualizar_env destrutivo: aí a
        MCC some do env e a próxima campanha de quem opera sob conta gestora
        falha com CUSTOMER_NOT_FOUND.
        """
        self.setup.atualizar_env(
            self.setup.GOOGLE_ENV, {"GOOGLE_ADS_LOGIN_CUSTOMER_ID": "9999999999"}
        )
        env, _, estado = self.rodar_com_estado(
            ["sim", "123-456-7890", "", "", "1//refresh", "vendas", "cpa=80", "cpa"]
        )
        self.assertEqual(estado, "connected")
        self.assertEqual(env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"), "9999999999")

    def test_main_falha_quando_conexao_pedida_fica_pendente(self):
        # Pendente é diferente de pulado: o aluno PEDIU para conectar. Sair 0
        # aqui faria a Etapa 4 ser reportada como concluída sem conexão.
        self.setup.executar_meta = lambda: None
        self.setup.executar_google = lambda: "pending"
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(self.setup.main([]), 1)
        self.assertIn("PENDENTE", saida.getvalue())

        self.setup.executar_google = lambda: "skipped"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.setup.main([]), 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.setup.main(["--skip-google"]), 0)

    def test_developer_token_nao_conta_como_credencial(self):
        # Ele identifica a aplicação, não o dono da conta.
        self.assertEqual(self.setup.credencial_google({"GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), "")
        self.assertEqual(
            self.setup.credencial_google({"GOOGLE_ADS_REFRESH_TOKEN": "1//x"}), "1//x"
        )
        self.assertEqual(self.setup.credencial_google({self.setup.GOOGLE_TOKEN_NAME: "pular"}), "")


if __name__ == "__main__":
    unittest.main()
