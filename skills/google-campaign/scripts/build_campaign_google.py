#!/usr/bin/env python3
"""Planejador e validador de campanhas Google Ads Search.

Este script não chama a API do Google Ads. Ele gera o plano que será executado
pelo Claude através do MCP Pipedream e mantém o ledger da operação.
"""

import argparse
import contextlib
import fcntl
import hashlib
import json
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


CONFIG_DIR = Path.home() / ".operacao-ia" / "config"
GOOGLE_ENV_PATH = CONFIG_DIR / "google_ads.env"
GOOGLE_PROFILE_PATH = CONFIG_DIR / "google_perfil.json"
PRODUCTS_DIR = CONFIG_DIR / "produtos"
LEDGER_PATH = Path.home() / ".operacao-ia" / "logs" / "google-ads-ledger.json"

GEO_BRASIL = "geoTargetConstants/2076"
IDIOMA_PT_BR = "languageConstants/1014"
MICROS = 1_000_000

MAX_TITULOS = 15
MAX_TITULO_CHARS = 30
QTD_DESCRICOES = 4
MAX_DESCRICAO_CHARS = 90
MIN_TITULOS = 3
MIN_DESCRICOES = 2

NEGATIVAS_PADRAO = (
    "gratis", "gratuito", "free", "download", "instalar", "login",
    "anthropic", "ingles", "excel", "emprego", "vaga", "pdf", "torrent",
)

REQUIRED_PRODUCT_FIELDS = (
    "nome", "preco", "link_checkout", "google_titulos",
    "google_descricoes", "google_keywords",
)

# Esta lista nasceu de uma reprovação real de anúncio por política de ganhos não confiáveis.
# Os RADICAIS abaixo são bloqueados isoladamente, não só dentro de frases feitas:
# "ganhe dinheiro" como frase exata deixava passar "Ganhe R$37 por dia", que é
# promessa de ganho explícita. O gate é fail-closed de propósito — reescrever um
# título custa um minuto, um anúncio reprovado custa a conta do aluno.
TERMOS_PROIBIDOS_GANHO = (
    "ganhe",
    "ganha",
    "ganhar",
    "ganho",
    "ganhe dinheiro",
    "fature",
    "faturamento",
    "faturar",
    "4 digitos",
    "5 digitos",
    "6 digitos",
    "7 digitos",
    "renda",
    "lucro",
    "lucrar",
    "lucre",
    "ganhos",
    "retorno garantido",
    "receba por",
    "dinheiro no bolso",
)

# Mesmo valendo o preço do produto, um valor com cadência vira promessa de
# recebimento recorrente ("Ganhe R$37 por dia"). O preço é um preço, não uma renda.
CADENCIA_PROIBIDA = (
    "por dia", "ao dia", "por semana", "ao semana", "por mes", "ao mes",
    "por hora", "a hora", "todo dia", "todo mes", "toda semana", "por venda",
    "por cliente", "por ano", "ao ano",
    # advérbios e formas com barra: "R$37/mês", "R$37 mensalmente"
    "mensal", "mensalmente", "diario", "diariamente", "semanal", "semanalmente",
    "anual", "anualmente", "/mes", "/dia", "/semana", "/ano", "/h",
)

# Valor monetário em qualquer notação usada em copy — não só "R$".
# "Curso por 500 reais" e "US$500" também violam o contrato de preço único.
# É UM regex com alternância ORDENADA, não uma lista de padrões independentes:
# `R\$` precisa ser tentado antes de `\$`, senão o `$37` de dentro de "R$37"
# casa como dólar e o gate reprova o próprio preço do produto.
PADRAO_MONETARIO = re.compile(
    r"(?P<moeda>R\$|US\$|USD|\$|€|EUR)\s*(?P<valor>[\d.,]+)"
    r"|(?P<valor_pos>[\d.,]+)\s*(?P<moeda_pos>reais|d[oó]lares|euros)\b",
    re.IGNORECASE,
)
MOEDAS_BRL = ("r$", "reais")


class ConfigError(Exception):
    """Erro de configuração apresentado ao usuário."""


def fail(message):
    """Interrompe a execução com uma mensagem em português."""
    raise ConfigError(message)


def load_env(path=GOOGLE_ENV_PATH):
    """Carrega um arquivo simples KEY=VALUE sem expor os valores."""
    if not Path(path).exists():
        return {}

    values = {}
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        values[key] = value
    return values


def read_product(slug):
    """Lê o JSON do produto e verifica os campos obrigatórios."""
    # O slug vira nome de arquivo: sem esta guarda, "../../.ssh/id_rsa" sairia
    # de produtos/ e leria qualquer arquivo da máquina do aluno.
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(slug or "")):
        fail(
            f"Slug de produto inválido: {slug!r}. Use apenas letras minúsculas, "
            "números e hífen, começando por letra ou número."
        )
    products_dir = Path(PRODUCTS_DIR).resolve()
    path = (products_dir / f"{slug}.json").resolve()
    try:
        path.relative_to(products_dir)
    except ValueError:
        fail(f"Slug de produto inválido: {slug!r}. O caminho sai da pasta de produtos.")
    if not path.exists():
        fail(
            f"Produto não encontrado: {slug}. Crie {path} com o formato JSON "
            "do produto antes de montar a campanha."
        )
    try:
        product = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Não foi possível ler o produto {slug}: {exc}")
    if not isinstance(product, dict):
        fail(f"O produto {slug} precisa ser um objeto JSON.")

    missing = [field for field in REQUIRED_PRODUCT_FIELDS if field not in product]
    if missing:
        fail(
            "Produto incompleto. Inclua no JSON os campos: "
            f"{', '.join(REQUIRED_PRODUCT_FIELDS)}. Ausentes: {', '.join(missing)}. "
            "Não invente copy ou keywords e não use promessa de ganho."
        )
    return product


def parse_budget(value):
    """Converte reais para Decimal e valida um valor positivo."""
    try:
        budget = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        fail(f"Budget inválido: {value}. Informe um valor em reais, por exemplo 30.")
    if not budget.is_finite() or budget <= 0:
        fail("O budget precisa ser maior que zero.")
    return budget


def validate_link(link):
    """Verifica se o checkout usa HTTP ou HTTPS."""
    if not isinstance(link, str):
        fail("link_checkout inválido. Informe uma URL http(s) no JSON do produto.")
    parsed = urlsplit(link.strip())
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        fail("link_checkout inválido. Informe uma URL http(s) no JSON do produto.")
    return link.strip()


def _read_ledger():
    if not Path(LEDGER_PATH).exists():
        return []
    try:
        data = json.loads(Path(LEDGER_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Não foi possível ler o ledger do Google Ads: {exc}")
    if not isinstance(data, list):
        fail("O ledger do Google Ads está inválido: o formato esperado é uma lista JSON.")
    return data


@contextlib.contextmanager
def _ledger_lock():
    """Serializa leitura-modificação-escrita do ledger.

    A escrita atômica sozinha evita arquivo pela metade, mas não evita perda:
    dois processos que leem a mesma lista e gravam em seguida deixam só a
    última entrada. O lock fecha a janela inteira, não só o replace.
    """
    ledger_path = Path(LEDGER_PATH)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.with_name(f"{ledger_path.name}.lock")
    with open(lock_path, "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _write_ledger(entries):
    ledger_path = Path(LEDGER_PATH)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = ledger_path.with_name(f"{ledger_path.name}.tmp")
    temporary.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(ledger_path)


def append_ledger(entry, forcar=False):
    """Reserva a campaign_key e grava, tudo DENTRO do mesmo lock.

    A checagem de duplicidade precisa acontecer aqui, e não antes: conferir
    fora do lock deixa dois planejamentos simultâneos verem "não existe",
    emitirem o mesmo plano e criarem DUAS campanhas de verdade no Google —
    o ledger guardaria só uma e a outra ficaria gastando sem rastro.

    Replanejar com --forcar substitui a tentativa anterior em vez de anexar
    uma segunda: duas entradas com a mesma chave deixariam o --registrar sem
    saber em qual gravar os IDs devolvidos pelo MCP.
    """
    with _ledger_lock():
        entries = _read_ledger()
        chave = entry.get("campaign_key")
        anteriores = [e for e in entries if e.get("campaign_key") == chave]
        if anteriores and not forcar:
            fail(
                f"Campanha já planejada para esta campaign_key: {chave}. "
                "Use --forcar somente se tiver conferido o ledger — ele SUBSTITUI "
                "a tentativa anterior (guardada no campo 'substituiu')."
            )
        entry = dict(entry)
        if anteriores:
            entry["substituiu"] = [
                {
                    chave_campo: anterior.get(chave_campo)
                    for chave_campo in (
                        "status", "attempt_id", "campaign_id", "ad_group_id", "ad_id", "created_at",
                    )
                }
                for anterior in anteriores
            ]
            entries = [e for e in entries if e.get("campaign_key") != chave]
        entries.append(entry)
        _write_ledger(entries)
    return entry


def campaign_key(produto, keywords, budget, customer_id=""):
    """Gera a chave estável usada para deduplicar o planejamento.

    A conta entra na chave: o mesmo produto planejado para duas contas do aluno
    é operação DIFERENTE, e sem o customer_id o --registrar acharia a entrada da
    conta errada e gravaria ali os IDs da outra campanha.
    """
    # O budget entra canonizado em micros inteiros: "30", "30.00" e "30,00"
    # descrevem o mesmo orçamento e precisam gerar a MESMA chave, senão o
    # dedupe falha e a mesma campanha é planejada duas vezes.
    canonical = json.dumps(
        {
            "produto": produto,
            "keywords": list(keywords),
            "budget_micros": _micros(budget),
            "customer_id": str(customer_id or ""),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _attempt_id():
    """Identificador curto e ÚNICO desta tentativa de planejamento.

    Deliberadamente aleatório, não derivado de chave + horário: dois
    planejamentos da mesma chave no mesmo segundo gerariam o mesmo hash, e aí
    o --registrar voltaria a aceitar como válido o retorno atrasado do MCP da
    tentativa substituída — que é exatamente o que este campo existe para
    impedir.
    """
    return uuid.uuid4().hex[:12]


def existing_campaign(key, ledger=None):
    """Retorna a entrada do ledger para a chave, quando existir."""
    entries = _read_ledger() if ledger is None else ledger
    return next((entry for entry in entries if entry.get("campaign_key") == key), None)


def _sem_acentos(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _parse_money_number(value):
    number = value.strip().replace(" ", "")
    if "," in number and "." in number:
        number = number.replace(".", "").replace(",", ".")
    elif "," in number:
        number = number.replace(",", ".")
    elif "." in number:
        parts = number.split(".")
        if len(parts) > 1 and len(parts[-1]) == 3:
            number = "".join(parts)
    try:
        return Decimal(number)
    except InvalidOperation:
        return None


def validar_copy(textos, preco):
    """Devolve lista de violações (texto, termo). Vazia = aprovado."""
    preco_decimal = Decimal(str(preco).replace(",", "."))
    violations = []

    for texto in textos:
        original = str(texto)
        normalizado = _sem_acentos(original).casefold()
        for termo in TERMOS_PROIBIDOS_GANHO:
            termo_normalizado = _sem_acentos(termo).casefold()
            # Os limites de palavra evitam reprovar "aprenda" por conter "renda".
            if re.search(r"\b" + re.escape(termo_normalizado) + r"\b", normalizado, re.IGNORECASE):
                violations.append((original, termo))

        cadencia_encontrada = _cadencia_em(normalizado)
        # Cadência + qualquer número é promessa de recebimento recorrente,
        # tenha ou não símbolo de moeda: "Receba 100 por dia" não casa com
        # nenhum padrão monetário e passava. O gate é fail-closed: se a copy
        # legítima falar de tempo ("15 min por dia"), reescrever o título custa
        # um minuto — um anúncio reprovado por ganho custa a conta do aluno.
        if cadencia_encontrada and re.search(r"\d", normalizado):
            violations.append(
                (original, f"número com cadência {cadencia_encontrada!r}")
            )

        for match in PADRAO_MONETARIO.finditer(original):
            moeda = match.group("moeda") or match.group("moeda_pos") or ""
            valor = match.group("valor") or match.group("valor_pos") or ""
            # Só a notação em reais pode coincidir com o preço do produto.
            # "US$37" com preco 37 é outro valor, em outra moeda.
            em_reais = moeda.strip().casefold() in MOEDAS_BRL
            monetary_value = _parse_money_number(valor)
            if not em_reais or monetary_value is None or monetary_value != preco_decimal:
                violations.append((original, f"valor monetário {match.group(0).strip()}"))
            elif cadencia_encontrada:
                # O valor bate com o preço, mas com cadência vira promessa de renda.
                violations.append((original, f"preço com cadência {cadencia_encontrada!r}"))
    return violations


def _cadencia_em(normalizado):
    """Devolve a primeira cadência encontrada no texto já normalizado."""
    for cadencia in CADENCIA_PROIBIDA:
        # Formas com barra ("/mes") não têm limite de palavra à esquerda.
        padrao = (
            re.escape(cadencia) + r"\b"
            if cadencia.startswith("/")
            else r"\b" + re.escape(cadencia) + r"\b"
        )
        if re.search(padrao, normalizado):
            return cadencia
    return None


def _price(product):
    try:
        value = Decimal(str(product["preco"]).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        fail("preco inválido. Informe o preço do produto como número no JSON.")
    if not value.is_finite() or value < 0:
        fail("preco inválido. Informe um preço maior ou igual a zero no JSON.")
    return value


def _micros(value):
    return int((value * MICROS).to_integral_value(rounding=ROUND_HALF_UP))


def _slugify(value):
    value = _sem_acentos(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "campanha-google"


def _tracked_link(link, slug, run_stamp, ad_number=1):
    parsed = urlsplit(link)
    tracking = {
        "sck": f"google-{slug}",
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": f"{slug}-{run_stamp}",
        "utm_content": f"{slug}-{run_stamp}-ad{ad_number}",
    }
    # Lista de pares, não dict: um checkout pode legitimamente repetir a mesma
    # chave (?coupon=vip&coupon=student) e o dict descartaria o primeiro valor.
    # Só as chaves de tracking são substituídas; o resto do link é preservado.
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in tracking
    ]
    query.extend(tracking.items())
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _profile_constant(profile, names, default, label):
    """Confere o perfil contra a constante obrigatória; ela NÃO é sobrescrevível.

    Geo Brasil e idioma Português são invariantes do produto: o aluno é
    brasileiro, a copy é em português e o checkout é em reais. Um perfil com
    geoTargetConstants/2840 mandaria a campanha para os EUA e queimaria o
    orçamento dele em silêncio. Divergência falha alto, em vez de ser ignorada,
    para o aluno corrigir o perfil em vez de descobrir pela fatura.
    """
    for name in names:
        if name in profile:
            value = profile[name]
            if not isinstance(value, str) or not value.strip():
                fail(f"{label} não pode ficar vazio no google_perfil.json.")
            if value.strip() != default:
                fail(
                    f"{label} não pode ser alterado no google_perfil.json: "
                    f"encontrado {value.strip()!r}, obrigatório {default!r}. "
                    "Geo Brasil e idioma Português são fixos; corrija o perfil "
                    "antes de planejar a campanha."
                )
            return value.strip()
    return default


def _customer_id(value):
    # Estrito de propósito: limpar caracteres arbitrários aceitaria "1234567890x"
    # como 1234567890 e mandaria a operação para uma conta que o aluno não digitou.
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d{10}|\d{3}-\d{3}-\d{4}", raw):
        fail(
            f"customer id inválido: {raw!r}. Informe a conta do Google Ads como "
            "10 dígitos (1234567890) ou no formato 123-456-7890."
        )
    return raw.replace("-", "")


def _validate_lists(product):
    titles = product.get("google_titulos")
    descriptions = product.get("google_descricoes")
    keywords = product.get("google_keywords")
    guidance = (
        "Use no JSON google_titulos com 3 a 15 itens de até 30 caracteres, "
        "google_descricoes com 2 a 4 itens de até 90 caracteres e "
        "google_keywords com ao menos uma string. Não invente copy ou keyword; "
        "a regra de ouro é não prometer ganho."
    )

    if not isinstance(titles, list) or not (MIN_TITULOS <= len(titles) <= MAX_TITULOS):
        fail(f"google_titulos insuficiente ou inválido. {guidance}")
    if any(not isinstance(title, str) or not title.strip() for title in titles):
        fail(f"Cada google_titulos precisa ser uma string não vazia. {guidance}")
    too_long = [title for title in titles if len(title) > MAX_TITULO_CHARS]
    if too_long:
        fail(f"Título excede {MAX_TITULO_CHARS} caracteres: {too_long[0]!r}. {guidance}")

    if not isinstance(descriptions, list) or not (MIN_DESCRICOES <= len(descriptions) <= QTD_DESCRICOES):
        fail(f"google_descricoes insuficiente ou inválido. {guidance}")
    if any(not isinstance(description, str) or not description.strip() for description in descriptions):
        fail(f"Cada google_descricoes precisa ser uma string não vazia. {guidance}")
    too_long = [description for description in descriptions if len(description) > MAX_DESCRICAO_CHARS]
    if too_long:
        fail(f"Descrição excede {MAX_DESCRICAO_CHARS} caracteres: {too_long[0]!r}. {guidance}")

    if not isinstance(keywords, list) or not keywords:
        fail(f"google_keywords insuficiente ou inválido. {guidance}")
    if any(not isinstance(keyword, str) or not keyword.strip() for keyword in keywords):
        fail(f"Cada google_keywords precisa ser uma string não vazia. {guidance}")
    return titles, descriptions, [keyword.strip() for keyword in keywords]


def _validate_copy_or_fail(titles, descriptions, price):
    violations = validar_copy(list(titles) + list(descriptions), price)
    if violations:
        lines = [
            'Copy reprovada pela política do Google de "ganhos não confiáveis".',
            "Remova promessas de ganho e valores monetários que não sejam o preço do produto:",
        ]
        lines.extend(f"- {texto!r} -> {termo!r}" for texto, termo in violations)
        fail("\n".join(lines))


def build_plan(
    product,
    produto,
    budget,
    customer_id,
    cpc_bid=None,
    profile=None,
    run_stamp=None,
    login_customer_id="",
):
    """Valida o produto e devolve o plano completo para os sete estágios."""
    titles, descriptions, keywords = _validate_lists(product)
    price = _price(product)
    link = validate_link(product["link_checkout"])
    _validate_copy_or_fail(titles, descriptions, price)

    profile = {} if profile is None else profile
    geo = _profile_constant(
        profile,
        ("geo_target_constant", "geo_target", "geo", "geoTargetConstant"),
        GEO_BRASIL,
        "geo do Google Ads",
    )
    language = _profile_constant(
        profile,
        ("language_constant", "idioma_pt_br", "idioma", "language", "languageConstant"),
        IDIOMA_PT_BR,
        "idioma do Google Ads",
    )
    if not geo or not language:
        fail("Geo e idioma são obrigatórios e não podem ficar vazios.")

    slug = _slugify(produto)
    stamp = run_stamp or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    tracked = _tracked_link(link, slug, stamp)
    key = campaign_key(produto, keywords, budget, customer_id)
    cpc = budget * Decimal("0.20") if cpc_bid is None else cpc_bid
    if cpc <= 0:
        fail("cpc-bid precisa ser maior que zero.")

    extra_negative = product.get("google_negativas_extra", [])
    if extra_negative is None:
        extra_negative = []
    if not isinstance(extra_negative, list) or any(
        not isinstance(item, str) or not item.strip() for item in extra_negative
    ):
        fail("google_negativas_extra precisa ser uma lista de strings não vazias.")
    negatives = list(NEGATIVAS_PADRAO) + [item.strip() for item in extra_negative]

    campaign_name = f"{product['nome']} - Google Search"
    passos = [
        {
            "ordem": 1,
            "tool": "google_ads-create-or-update-campaign-budget",
            "descricao": "Criar o orçamento diário compartilhado da campanha.",
            "payload": {
                "customer_id": customer_id,
                "name": f"Budget - {slug}",
                "amount_micros": _micros(budget),
                "delivery_method": "STANDARD",
                "explicitly_shared": False,
            },
            "instruction": "Crie ou atualize o orçamento diário para este customer id. EXECUTE NOW (perform the mutate).",
        },
        {
            "ordem": 2,
            "tool": "google_ads-create-or-update-campaign",
            "descricao": "Criar a campanha Search pausada, somente na rede Google Search.",
            "payload": {
                "customer_id": customer_id,
                "campaign_budget_id": 0,
                "name": campaign_name,
                "advertising_channel_type": "SEARCH",
                "status": "PAUSED",
                "manual_cpc": {},
                "target_google_search": True,
                "target_search_network": False,
                "target_content_network": False,
                "target_partner_search_network": False,
                "contains_eu_political_advertising": "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
            },
            "nota": "campaign_budget_id: 0 é PLACEHOLDER. Substitua pelo ID numérico retornado no passo 1 antes de executar.",
            "instruction": "Crie a campanha Search com status PAUSED e apenas Google Search. EXECUTE NOW (perform the mutate).",
        },
        {
            "ordem": 3,
            "tool": "google_ads-create-or-remove-campaign-criteria",
            "descricao": "Aplicar a localização do Brasil e o idioma português.",
            "payload": {
                "customer_id": customer_id,
                "campaign_id": 0,
                "remove": False,
                "criteria": [
                    {"type": "LOCATION", "geo_target_constant": geo},
                    {"type": "LANGUAGE", "language_constant": language},
                ],
            },
            "nota": (
                "campaign_id: 0 é PLACEHOLDER — substitua pelo ID numérico retornado no passo 2. "
                "PASSO OBRIGATÓRIO: sem geo e idioma a campanha do aluno veicula no mundo inteiro "
                "e consome o orçamento dele. Não pule nem execute com o placeholder."
            ),
            "instruction": "Adicione obrigatoriamente o geo e o idioma antes de qualquer veiculação. EXECUTE NOW (perform the mutate).",
        },
        {
            "ordem": 4,
            "tool": "google_ads-create-or-update-ad-group",
            "descricao": "Criar o grupo de anúncios Search Standard pausado.",
            "payload": {
                "customer_id": customer_id,
                "campaign_id": 0,
                "name": f"Grupo - {slug}",
                "type": "SEARCH_STANDARD",
                "status": "PAUSED",
                "cpc_bid_micros": _micros(cpc),
            },
            "nota": "campaign_id: 0 é PLACEHOLDER. Substitua pelo ID numérico retornado no passo 2 antes de executar.",
            "instruction": "Crie o grupo de anúncios pausado com o lance CPC indicado. EXECUTE NOW (perform the mutate).",
        },
    ]

    for keyword in keywords:
        passos.append(
            {
                "ordem": 5,
                "tool": "google_ads-create-or-update-keywords",
                "descricao": f"Adicionar a keyword {keyword!r} em correspondência de frase.",
                "sequencial": True,
                "payload": {
                    "customer_id": customer_id,
                    "campaign_id": 0,
                    "ad_group_id": 0,
                    "keyword": {"text": keyword, "match_type": "PHRASE"},
                },
                "nota": (
                    "campaign_id e ad_group_id: 0 são PLACEHOLDERS — use os IDs numéricos "
                    "dos passos 2 e 4. Executar uma keyword por vez: lote dispara "
                    "CONCURRENT_MODIFICATION e exige retry."
                ),
                "instruction": "Adicione esta keyword PHRASE individualmente e aguarde o retorno antes da próxima. EXECUTE NOW (perform the mutate).",
            }
        )

    passos.extend(
        [
            {
                "ordem": 6,
                "tool": "google_ads-create-responsive-search-ad",
                "descricao": "Criar o anúncio responsivo de pesquisa pausado.",
                "payload": {
                    "customer_id": customer_id,
                    "ad_group_id": 0,
                    "status": "PAUSED",
                    "final_urls": [tracked],
                    "headlines": titles,
                    "descriptions": descriptions,
                },
                "nota": (
                    "ad_group_id: 0 é PLACEHOLDER — substitua pelo ID retornado no passo 4. "
                    "Ele é NUMÉRICO, não resource name. Não usar path1/path2."
                ),
                "instruction": "Crie o RSA pausado usando os títulos, descrições e URL já validados. EXECUTE NOW (perform the mutate).",
            },
            {
                "ordem": 7,
                "tool": "google_ads-create-or-remove-campaign-criteria",
                "descricao": "Adicionar as palavras-chave negativas padrão e extras do produto.",
                "payload": {
                    "customer_id": customer_id,
                    "campaign_id": 0,
                    "remove": False,
                    "negative": True,
                    "match_type": "BROAD",
                    "keywords": negatives,
                },
                "nota": "campaign_id: 0 é PLACEHOLDER. Substitua pelo ID numérico retornado no passo 2 antes de executar.",
                "instruction": "Adicione as negativas BROAD da campanha para proteger o budget. EXECUTE NOW (perform the mutate).",
            },
        ]
    )

    plano = {
        "campaign_key": key,
        # Identifica ESTA tentativa. A campaign_key sozinha é estável entre
        # replanejamentos: sem o attempt_id, um retorno atrasado do MCP de uma
        # tentativa já substituída seria gravado na tentativa nova.
        "attempt_id": _attempt_id(),
        "customer_id": customer_id,
        "produto": produto,
        "run_stamp": stamp,
        "url_rastreada": tracked,
        "gotchas": [
            "Retornos vazios são intermitentes: confira via list e reexecute; nunca duplique sem checar.",
            "RSA não edita in-place: remova o anúncio e crie um novo.",
            "Listagens não filtram por campanha nem trazem policy_summary; o motivo da reprovação só aparece no painel.",
        ],
        "passos": passos,
    }
    if login_customer_id:
        # Conta sob MCC: sem informar a conta gestora, a operação pode falhar
        # com CUSTOMER_NOT_FOUND mesmo com o customer_id certo. Ele é contexto
        # de acesso, não muda a conta em que a campanha é criada.
        plano["login_customer_id"] = login_customer_id
        plano["gotchas"].insert(
            0,
            f"Conta sob MCC: use login customer id {login_customer_id} como conta gestora "
            f"ao chamar o MCP; a campanha continua sendo criada em {customer_id}.",
        )
    return plano


def _load_profile():
    if not Path(GOOGLE_PROFILE_PATH).exists():
        return {}
    try:
        profile = json.loads(Path(GOOGLE_PROFILE_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Não foi possível ler google_perfil.json: {exc}")
    if not isinstance(profile, dict):
        fail("google_perfil.json precisa conter um objeto JSON.")
    return profile


def _google_id(value, label):
    """Aceita apenas ID numérico positivo devolvido pela API."""
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d+", raw) or int(raw) <= 0:
        fail(
            f"{label} inválido: {raw!r}. Registre apenas o ID numérico positivo "
            "devolvido pelo MCP. Se o passo falhou, não registre: refaça o passo "
            "e só então feche o ledger."
        )
    return raw


def _register(args):
    if not args.campaign_key or not args.campaign_id:
        fail("--registrar exige --campaign-key e --campaign-id.")
    campaign_id = _google_id(args.campaign_id, "campaign-id")
    ad_group_id = _google_id(args.ad_group_id, "ad-group-id") if args.ad_group_id else ""
    ad_id = _google_id(args.ad_id, "ad-id") if args.ad_id else ""

    with _ledger_lock():
        entries = _read_ledger()
        matches = [e for e in entries if e.get("campaign_key") == args.campaign_key]
        if not matches:
            fail(f"Campaign key não encontrada no ledger: {args.campaign_key}")
        if len(matches) > 1:
            fail(
                f"Há {len(matches)} entradas com a campaign key {args.campaign_key}. "
                "Confira o ledger e resolva a ambiguidade antes de registrar; "
                "registrar às cegas associaria os IDs à campanha errada."
            )
        entry = matches[0]
        # Esta chave já foi replanejada: existe mais de uma tentativa real no
        # mundo, e um retorno atrasado do MCP pode ser da tentativa antiga.
        # Sem o attempt_id não há como distinguir, e registrar às cegas marcaria
        # como criada uma campanha que pertence à tentativa substituída.
        if entry.get("substituiu") and not args.attempt_id:
            fail(
                f"Esta campaign_key foi replanejada ({len(entry['substituiu'])} tentativa(s) "
                f"substituída(s)). Informe --attempt-id {entry.get('attempt_id')} para confirmar "
                "que os IDs são desta tentativa, e não da anterior."
            )
        if args.attempt_id and args.attempt_id != entry.get("attempt_id"):
            fail(
                f"attempt-id não corresponde à tentativa ativa desta campaign_key. "
                f"Ativa: {entry.get('attempt_id')}. Informado: {args.attempt_id}. "
                "Se estes IDs são de uma tentativa anterior, não registre aqui: "
                "a campanha antiga precisa ser conferida e removida no painel."
            )
        # Campanha diferente da registrada antes = OUTRA tentativa. Grupo e
        # anúncio da tentativa anterior pertencem à campanha antiga: mantê-los
        # aqui montaria um registro Frankenstein (campanha nova + grupo velho),
        # e o aluno acharia que a operação fechou completa.
        if entry.get("campaign_id") and entry["campaign_id"] != campaign_id:
            entry.pop("ad_group_id", None)
            entry.pop("ad_id", None)
        entry["campaign_id"] = campaign_id
        if ad_group_id:
            entry["ad_group_id"] = ad_group_id
        if ad_id:
            entry["ad_id"] = ad_id
        # 'created' só quando os três objetos existem de fato. Sem grupo ou anúncio,
        # a operação ficou pela metade: marcar 'created' esconderia isso do aluno.
        completo = bool(entry.get("campaign_id") and entry.get("ad_group_id") and entry.get("ad_id"))
        entry["status"] = "created" if completo else "partial"
        if not completo:
            faltando = [
                nome for nome, campo in (("ad_group_id", "ad_group_id"), ("ad_id", "ad_id"))
                if not entry.get(campo)
            ]
            entry["pendencia"] = (
                f"Faltam {' e '.join(faltando)}: execute os passos restantes e registre de novo."
            )
        else:
            entry.pop("pendencia", None)
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_ledger(entries)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Planeja uma campanha Google Ads Search.")
    parser.add_argument("--produto")
    parser.add_argument("--budget")
    parser.add_argument("--conta")
    parser.add_argument("--login-conta", default="")
    parser.add_argument("--cpc-bid")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--forcar", action="store_true")
    parser.add_argument("--registrar", action="store_true")
    parser.add_argument("--campaign-key")
    parser.add_argument("--campaign-id")
    parser.add_argument("--ad-group-id")
    parser.add_argument("--ad-id")
    parser.add_argument("--attempt-id", default="")
    args = parser.parse_args(argv)

    try:
        if args.registrar:
            return _register(args)
        if not args.produto or args.budget is None:
            fail("--produto e --budget são obrigatórios para planejar uma campanha.")

        product = read_product(args.produto)
        budget = parse_budget(args.budget)
        env = load_env()
        account_value = args.conta or env.get("GOOGLE_ADS_CUSTOMER_ID")
        if not account_value:
            fail(
                "Conta do Google Ads não encontrada. Informe --conta ou conecte a conta "
                "na Etapa 4 (GOOGLE_ADS_CUSTOMER_ID)."
            )
        account = _customer_id(account_value)
        login_value = args.login_conta or env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
        login_account = _customer_id(login_value) if login_value.strip() else ""
        cpc_bid = parse_budget(args.cpc_bid) if args.cpc_bid is not None else None
        plan = build_plan(
            product,
            args.produto,
            budget,
            account,
            cpc_bid=cpc_bid,
            profile=_load_profile(),
            login_customer_id=login_account,
        )

        key = plan["campaign_key"]
        # A reserva da chave acontece DENTRO do lock, em append_ledger. Conferir
        # aqui e gravar depois deixaria dois planejamentos simultâneos passarem
        # e criarem duas campanhas de verdade — o ledger guardaria uma só.
        if not args.dry_run:
            append_ledger(
                {
                    "campaign_key": key,
                    "attempt_id": plan["attempt_id"],
                    "produto": args.produto,
                    "customer_id": account,
                    "budget": str(budget),
                    "keywords": product["google_keywords"],
                    "status": "planned",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                forcar=args.forcar,
            )
        # O plano só é impresso depois da reserva: imprimir antes entregaria ao
        # aluno passos executáveis de uma campanha que o ledger vai recusar.
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except ConfigError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERRO: não foi possível gravar o ledger: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
