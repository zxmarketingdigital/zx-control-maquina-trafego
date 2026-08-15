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
        fila = list(respostas)
        self.setup.resposta = lambda prompt, default="": (fila.pop(0) if fila else default)
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.setup.executar_google()
        return self.setup.ler_env(self.setup.GOOGLE_ENV), saida.getvalue()

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

    def test_developer_token_nao_conta_como_credencial(self):
        # Ele identifica a aplicação, não o dono da conta.
        self.assertEqual(self.setup.credencial_google({"GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), "")
        self.assertEqual(
            self.setup.credencial_google({"GOOGLE_ADS_REFRESH_TOKEN": "1//x"}), "1//x"
        )
        self.assertEqual(self.setup.credencial_google({self.setup.GOOGLE_TOKEN_NAME: "pular"}), "")


if __name__ == "__main__":
    unittest.main()
