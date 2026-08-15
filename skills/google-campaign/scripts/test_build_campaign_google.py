#!/usr/bin/env python3
import contextlib
import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import build_campaign_google as build


class BuildCampaignGoogleTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.products = self.root / "produtos"
        self.products.mkdir()
        self.ledger = self.root / "logs" / "google-ads-ledger.json"
        self.profile = self.root / "google_perfil.json"
        self.product = {
            "nome": "Curso Agentes IA",
            "preco": 37,
            "link_checkout": "https://exemplo.test/checkout?origem=produto",
            "google_titulos": [
                "Aprenda a criar agentes de IA",
                "Curso prático sem código",
                "Domine automação com IA",
            ],
            "google_descricoes": [
                "Aprenda a criar agentes de IA de forma prática.",
                "Curso direto ao ponto para trabalhar com IA.",
            ],
            "google_keywords": ["curso agentes ia", "criar agentes de ia"],
        }
        (self.products / "teste-google.json").write_text(
            json.dumps(self.product, ensure_ascii=False), encoding="utf-8"
        )
        self.patches = patch.multiple(
            build,
            PRODUCTS_DIR=self.products,
            LEDGER_PATH=self.ledger,
            GOOGLE_PROFILE_PATH=self.profile,
        )
        self.patches.start()

    def tearDown(self):
        self.patches.stop()
        self.temp_dir.cleanup()

    def test_aprenda_passa_no_gate_de_limite_de_palavra(self):
        self.assertEqual(build.validar_copy(["Aprenda a criar agentes de IA"], 37), [])

    def test_termos_de_ganho_falham(self):
        self.assertTrue(build.validar_copy(["Renda extra com IA"], 37))
        self.assertTrue(build.validar_copy(["Fature 5 dígitos"], 37))

    def test_preco_e_valor_monetario(self):
        self.assertEqual(build.validar_copy(["Curso completo por R$37"], 37), [])
        self.assertTrue(build.validar_copy(["Curso completo por R$500"], 37))

    def test_plano_tem_geo_idioma_e_status_paused(self):
        plan = build.build_plan(
            self.product,
            "teste-google",
            build.parse_budget("30"),
            "1234567890",
            run_stamp="20240101010101",
        )
        serialized = json.dumps(plan, ensure_ascii=False)
        self.assertIn("geoTargetConstants/2076", serialized)
        self.assertIn("languageConstants/1014", serialized)
        campaign_step = next(step for step in plan["passos"] if step["ordem"] == 2)
        ad_group_step = next(step for step in plan["passos"] if step["ordem"] == 4)
        ad_step = next(step for step in plan["passos"] if step["ordem"] == 6)
        self.assertEqual(campaign_step["payload"]["status"], "PAUSED")
        self.assertEqual(ad_group_step["payload"]["status"], "PAUSED")
        self.assertEqual(ad_step["payload"]["status"], "PAUSED")

    def test_keywords_sao_sequenciais_e_phrase(self):
        plan = build.build_plan(
            self.product,
            "teste-google",
            build.parse_budget("30"),
            "1234567890",
            run_stamp="20240101010101",
        )
        keyword_steps = [step for step in plan["passos"] if step["ordem"] == 5]
        self.assertEqual(len(keyword_steps), len(self.product["google_keywords"]))
        for step, keyword in zip(keyword_steps, self.product["google_keywords"]):
            self.assertTrue(step["sequencial"])
            self.assertEqual(step["payload"]["keyword"]["match_type"], "PHRASE")
            self.assertEqual(step["payload"]["keyword"]["text"], keyword)

    def test_slug_nao_escapa_da_pasta_de_produtos(self):
        # Sem a guarda, o slug vira caminho e lê arquivo fora de produtos/.
        alvo = self.root / "segredo.json"
        alvo.write_text(json.dumps(self.product, ensure_ascii=False), encoding="utf-8")
        for slug in ("../segredo", "../../etc/passwd", "/etc/passwd", "Teste_Google"):
            with self.assertRaises(build.ConfigError):
                build.read_product(slug)

    def test_campaign_key_ignora_formatacao_do_budget(self):
        # "30", "30.00" e "30,00" são o MESMO orçamento: chave diferente quebra o dedupe.
        keywords = self.product["google_keywords"]
        chaves = {
            build.campaign_key("teste-google", keywords, build.parse_budget(valor), "1234567890")
            for valor in ("30", "30.00", "30,00")
        }
        self.assertEqual(len(chaves), 1)
        diferente = build.campaign_key(
            "teste-google", keywords, build.parse_budget("31"), "1234567890"
        )
        self.assertNotIn(diferente, chaves)

    def test_campaign_key_separa_contas_diferentes(self):
        # Mesmo produto em duas contas do aluno é operação DIFERENTE.
        keywords = self.product["google_keywords"]
        budget = build.parse_budget("30")
        a = build.campaign_key("teste-google", keywords, budget, "1111111111")
        b = build.campaign_key("teste-google", keywords, budget, "2222222222")
        self.assertNotEqual(a, b)

    def test_gate_barra_promessa_de_ganho_com_o_proprio_preco(self):
        # O valor bate com o preço, mas "por dia" transforma preço em renda.
        self.assertTrue(build.validar_copy(["Ganhe R$37 por dia"], 37))
        self.assertTrue(build.validar_copy(["Receba R$37 todo mês"], 37))
        self.assertTrue(build.validar_copy(["Ganhe mais com IA"], 37))
        self.assertTrue(build.validar_copy(["Lucre com agentes de IA"], 37))
        # O preço sozinho continua permitido.
        self.assertEqual(build.validar_copy(["Curso completo por R$37"], 37), [])

    def test_perfil_nao_pode_trocar_geo_nem_idioma(self):
        for perfil in (
            {"geo": "geoTargetConstants/2840"},
            {"language": "languageConstants/1000"},
        ):
            with self.assertRaises(build.ConfigError):
                build.build_plan(
                    self.product,
                    "teste-google",
                    build.parse_budget("30"),
                    "1234567890",
                    profile=perfil,
                    run_stamp="20240101010101",
                )

    def test_customer_id_rejeita_lixo(self):
        self.assertEqual(build._customer_id("123-456-7890"), "1234567890")
        self.assertEqual(build._customer_id("1234567890"), "1234567890")
        for invalido in ("1234567890x", "12 34 56 78 90", "123456789", "abc"):
            with self.assertRaises(build.ConfigError):
                build._customer_id(invalido)

    def test_url_preserva_parametro_repetido(self):
        produto = dict(self.product)
        produto["link_checkout"] = "https://exemplo.test/checkout?coupon=vip&coupon=student"
        (self.products / "com-cupom.json").write_text(
            json.dumps(produto, ensure_ascii=False), encoding="utf-8"
        )
        plan = build.build_plan(
            produto, "com-cupom", build.parse_budget("30"), "1234567890",
            run_stamp="20240101010101",
        )
        url = plan["url_rastreada"]
        self.assertIn("coupon=vip", url)
        self.assertIn("coupon=student", url)
        self.assertEqual(url.count("utm_source=google"), 1)

    def test_registrar_recusa_id_invalido_e_marca_parcial(self):
        args = ["--produto", "teste-google", "--budget", "30", "--conta", "1234567890"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(args), 0)
        chave = json.loads(self.ledger.read_text(encoding="utf-8"))[0]["campaign_key"]

        # ID não numérico ou zero não pode fechar o ledger como criado.
        for ruim in ("0", "erro", "-5"):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    build.main(["--registrar", "--campaign-key", chave, "--campaign-id", ruim]), 1
                )
        self.assertEqual(json.loads(self.ledger.read_text(encoding="utf-8"))[0]["status"], "planned")

        # Só campanha, sem grupo e anúncio: operação incompleta vira 'partial'.
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                build.main(["--registrar", "--campaign-key", chave, "--campaign-id", "555"]), 0
            )
        self.assertEqual(json.loads(self.ledger.read_text(encoding="utf-8"))[0]["status"], "partial")

        # Com os três IDs, fecha como criado.
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                build.main([
                    "--registrar", "--campaign-key", chave, "--campaign-id", "555",
                    "--ad-group-id", "666", "--ad-id", "777",
                ]), 0
            )
        final = json.loads(self.ledger.read_text(encoding="utf-8"))[0]
        self.assertEqual(final["status"], "created")
        self.assertNotIn("pendencia", final)

    def test_passos_encadeados_avisam_sobre_placeholder(self):
        plan = build.build_plan(
            self.product,
            "teste-google",
            build.parse_budget("30"),
            "1234567890",
            run_stamp="20240101010101",
        )
        for step in plan["passos"]:
            payload = step["payload"]
            tem_placeholder = any(
                payload.get(campo) == 0
                for campo in ("campaign_id", "ad_group_id", "campaign_budget_id")
            )
            if tem_placeholder:
                self.assertIn("PLACEHOLDER", step.get("nota", ""))

    def test_campaign_key_nao_vaza_para_o_payload_da_api(self):
        plan = build.build_plan(
            self.product,
            "teste-google",
            build.parse_budget("30"),
            "1234567890",
            run_stamp="20240101010101",
        )
        for step in plan["passos"]:
            self.assertNotIn("campaign_key", step["payload"])

    def test_gate_barra_moeda_estrangeira_e_valor_por_extenso(self):
        # O contrato proíbe QUALQUER valor monetário que não seja o preço.
        for texto in ("Curso por 500 reais", "Curso por US$500", "Curso por €99", "Plano por $19"):
            self.assertTrue(build.validar_copy([texto], 37), texto)
        # O preço do produto por extenso continua permitido.
        self.assertEqual(build.validar_copy(["Curso por 37 reais"], 37), [])

    def test_gate_barra_cadencia_com_barra_e_adverbio(self):
        # "R$37/mês" e "R$37 mensalmente" são recorrência, não preço.
        for texto in ("Curso R$37/mês", "Curso R$37 mensalmente", "Curso R$37 por semana"):
            self.assertTrue(build.validar_copy([texto], 37), texto)

    def test_forcar_substitui_em_vez_de_duplicar(self):
        # Duas entradas com a mesma chave deixariam o --registrar sem saber onde gravar.
        args = ["--produto", "teste-google", "--budget", "30", "--conta", "1234567890"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(args), 0)
            self.assertEqual(build.main(args + ["--forcar"]), 0)
        entries = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertIn("substituiu", entries[0])

        chave = entries[0]["campaign_key"]
        tentativa_atual = entries[0]["attempt_id"]
        tentativa_antiga = entries[0]["substituiu"][0]["attempt_id"]
        self.assertNotEqual(tentativa_atual, tentativa_antiga)

        registrar = ["--registrar", "--campaign-key", chave, "--campaign-id", "555"]
        with contextlib.redirect_stdout(io.StringIO()):
            # Sem --attempt-id não dá para saber se os IDs são da tentativa viva
            # ou de um retorno atrasado do MCP referente à tentativa substituída.
            self.assertEqual(build.main(registrar), 1)
            self.assertEqual(build.main(registrar + ["--attempt-id", tentativa_antiga]), 1)
            self.assertEqual(build.main(registrar + ["--attempt-id", tentativa_atual]), 0)
        self.assertEqual(
            json.loads(self.ledger.read_text(encoding="utf-8"))[0]["campaign_id"], "555"
        )

    def test_registrar_nao_herda_ids_de_outra_campanha(self):
        args = ["--produto", "teste-google", "--budget", "30", "--conta", "1234567890"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(args), 0)
        chave = json.loads(self.ledger.read_text(encoding="utf-8"))[0]["campaign_key"]

        with contextlib.redirect_stdout(io.StringIO()):
            build.main([
                "--registrar", "--campaign-key", chave,
                "--campaign-id", "100", "--ad-group-id", "200",
            ])
            # Segunda tentativa: campanha NOVA. O grupo 200 é da campanha 100.
            build.main([
                "--registrar", "--campaign-key", chave,
                "--campaign-id", "101", "--ad-id", "300",
            ])
        final = json.loads(self.ledger.read_text(encoding="utf-8"))[0]
        self.assertEqual(final["campaign_id"], "101")
        self.assertNotIn("ad_group_id", final)
        self.assertEqual(final["status"], "partial")

    def test_ledger_nao_perde_entrada_em_concorrencia(self):
        """Sem lock, dois escritores leem o mesmo ledger e o último replace apaga o outro.

        A janela é injetada de propósito (sleep depois da leitura). Sem isso o
        teste fica verde mesmo com o lock desligado — ou seja, não provaria nada:
        as duas escritas raramente se sobrepõem por acaso.
        """
        leitura_original = build._read_ledger

        def leitura_lenta():
            entradas = leitura_original()
            time.sleep(0.2)  # mantém o escritor dentro da janela crítica
            return entradas

        erros = []

        def escrever(indice):
            try:
                build.append_ledger({"campaign_key": f"chave-{indice}", "produto": f"p{indice}"})
            except Exception as exc:  # pragma: no cover - só aparece se o lock travar
                erros.append(exc)

        with patch.object(build, "_read_ledger", leitura_lenta):
            threads = [threading.Thread(target=escrever, args=(indice,)) for indice in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
                self.assertFalse(thread.is_alive(), "o lock travou a escrita")

        self.assertEqual(erros, [])
        entries = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(
            {entry["campaign_key"] for entry in entries},
            {"chave-0", "chave-1"},
            "uma das entradas foi perdida: leitura-modificação-escrita sem serialização",
        )

    def test_dedupe_do_ledger_sem_forcar(self):
        args = [
            "--produto", "teste-google",
            "--budget", "30",
            "--conta", "123-456-7890",
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build.main(args), 0)
            self.assertEqual(build.main(args), 1)
        entries = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "planned")

    def test_reserva_da_chave_acontece_dentro_do_lock(self):
        """Dois planejamentos simultâneos da MESMA chave: só um pode reservar.

        Se a checagem de duplicidade acontecer antes do lock, os dois passam,
        os dois planos vão para o MCP e nascem duas campanhas iguais na conta
        do aluno — com uma única entrada no ledger para os dois.
        """
        leitura_original = build._read_ledger

        def leitura_lenta():
            entradas = leitura_original()
            time.sleep(0.2)
            return entradas

        resultados = []

        def planejar():
            try:
                build.append_ledger(
                    {"campaign_key": "mesma-chave", "produto": "teste-google"}
                )
                resultados.append("reservou")
            except build.ConfigError:
                resultados.append("recusado")

        with patch.object(build, "_read_ledger", leitura_lenta):
            threads = [threading.Thread(target=planejar) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
                self.assertFalse(thread.is_alive(), "o lock travou a reserva")

        self.assertEqual(
            sorted(resultados),
            ["recusado", "reservou"],
            "a segunda reserva passou: a checagem de duplicidade está fora do lock",
        )
        self.assertEqual(len(json.loads(self.ledger.read_text(encoding="utf-8"))), 1)

    def test_cadencia_com_numero_sem_moeda_reprova(self):
        # Sem símbolo de moeda o regex monetário não casa, mas a promessa é a mesma.
        for texto in ("Receba 100 por dia", "Receba 100/dia", "Ate 500 ao mes"):
            self.assertTrue(build.validar_copy([texto], 37), texto)
        # Cadência sem número nenhum não é promessa de ganho.
        self.assertEqual(build.validar_copy(["Aulas novas por semana"], 37), [])

    def test_login_customer_id_da_mcc_chega_ao_plano(self):
        plan = build.build_plan(
            self.product,
            "teste-google",
            build.parse_budget("30"),
            "1234567890",
            run_stamp="20240101010101",
            login_customer_id="9999999999",
        )
        # A conta do ALUNO continua sendo a de operação; a MCC só autentica.
        self.assertEqual(plan["customer_id"], "1234567890")
        self.assertEqual(plan["login_customer_id"], "9999999999")
        self.assertTrue(any("9999999999" in nota for nota in plan["gotchas"]))

    def test_sem_mcc_o_plano_nao_inventa_login_customer_id(self):
        plan = build.build_plan(
            self.product,
            "teste-google",
            build.parse_budget("30"),
            "1234567890",
            run_stamp="20240101010101",
        )
        self.assertNotIn("login_customer_id", plan)


if __name__ == "__main__":
    unittest.main()
