#!/usr/bin/env python3
"""Cria uma campanha Meta pausada a partir da configuração de um produto."""

import argparse
import json
import mimetypes
import re
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


GRAPH_VERSION = "v21.0"
HOME = Path.home()
CONFIG_DIR = HOME / ".operacao-ia" / "config"
PRODUCTS_DIR = CONFIG_DIR / "produtos"
META_ENV = CONFIG_DIR / "meta.env"
LEDGER_PATH = HOME / ".operacao-ia" / "logs" / "ads-ledger.json"
OBJECTIVES = ("LEAD_GENERATION", "CONVERSIONS", "TRAFFIC")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".webm"}


class ConfigError(Exception):
    pass


class MetaAPIError(Exception):
    pass


def read_env_file(path):
    values = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def redact(value, secret=""):
    text = str(value)
    if secret:
        text = text.replace(secret, "[TOKEN REDACTED]")
    return text[:500]


def graph_url(path):
    return f"https://graph.facebook.com/{GRAPH_VERSION}{path}"


def graph_request(method, path, token, fields=None, multipart=None):
    fields = dict(fields or {})
    if method == "GET":
        fields["access_token"] = token
        query = urlencode(fields)
        url = f"{graph_url(path)}?{query}" if query else graph_url(path)
        request = Request(url, method="GET")
    elif multipart is not None:
        boundary = f"----CodexMeta{uuid.uuid4().hex}"
        body = bytearray()
        multipart_fields = dict(fields)
        multipart_fields["access_token"] = token
        for key, value in multipart_fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            body.extend(str(value).encode())
            body.extend(b"\r\n")
        filename, content_type, content = multipart
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="filename"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n".encode()
        )
        body.extend(content)
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        request = Request(
            graph_url(path),
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
    else:
        fields["access_token"] = token
        request = Request(
            graph_url(path),
            data=urlencode(fields).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            error = payload.get("error", {})
            message = error.get("message") or payload
        except (ValueError, TypeError):
            message = raw or exc.reason
        raise MetaAPIError(f"Graph API HTTP {exc.code}: {redact(message, token)}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise MetaAPIError(f"não foi possível conectar à Graph API: {redact(exc, token)}") from None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise MetaAPIError("a Graph API retornou uma resposta inválida") from None
    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        message = error.get("message", "erro não especificado") if isinstance(error, dict) else error
        raise MetaAPIError(f"a Graph API recusou a operação: {redact(message, token)}") from None
    return payload


def load_product(slug):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", slug):
        raise ConfigError("o slug do produto contém caracteres inválidos")
    path = PRODUCTS_DIR / f"{slug}.json"
    if not path.exists():
        raise ConfigError(
            f"produto '{slug}' não cadastrado em ~/.operacao-ia/config/produtos/{slug}.json; "
            "cadastre o produto primeiro"
        )
    try:
        product = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"não foi possível ler a configuração do produto: {exc}") from None
    if not isinstance(product, dict):
        raise ConfigError("a configuração do produto precisa ser um objeto JSON")
    required = ("nome", "preco", "link_checkout", "headline", "descricao", "pixel_id")
    missing = [key for key in required if key not in product]
    if missing:
        raise ConfigError(f"configuração do produto incompleta; faltam: {', '.join(missing)}")
    link = str(product["link_checkout"]).strip()
    if urlsplit(link).scheme not in {"http", "https"} or not urlsplit(link).netloc:
        raise ConfigError("link_checkout precisa ser uma URL HTTP ou HTTPS válida")
    if not str(product["pixel_id"]).strip():
        raise ConfigError("pixel_id do produto não pode ficar vazio")
    return product


def normalize_account(account):
    account = (account or "").strip()
    if account.startswith("act_"):
        account = account[4:]
    if not account or not account.isdigit():
        raise ConfigError("informe uma conta Meta válida em --conta ou META_AD_ACCOUNT_ID")
    return account


def money_to_cents(value):
    try:
        amount = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ConfigError("--budget precisa ser um valor diário em reais") from None
    if not amount.is_finite() or amount <= 0:
        raise ConfigError("--budget precisa ser maior que zero")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def tracked_link(link, slug, run_stamp, ad_number):
    parts = urlsplit(link)
    params = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
              if key not in {"utm_source", "utm_medium", "utm_campaign", "utm_content"}]
    params.extend(
        [
            ("utm_source", "meta"),
            ("utm_medium", "paid_social"),
            ("utm_campaign", f"{slug}-{run_stamp}"),
            ("utm_content", f"{slug}-{run_stamp}-ad{ad_number}"),
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))


def objective_settings(objective):
    return {
        "LEAD_GENERATION": ("LEAD_GENERATION", "LEAD"),
        "CONVERSIONS": ("OFFSITE_CONVERSIONS", "PURCHASE"),
        "TRAFFIC": ("LINK_CLICKS", "PURCHASE"),
    }[objective]


def creative_kind(path):
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    raise ConfigError(f"formato de criativo não suportado: {path}")


def targeting_payload():
    return {
        "geo_locations": {"countries": ["BR"]},
        "age_min": 18,
        "age_max": 65,
    }


def payload_plan(args, product, account, creatives, budget_cents, run_stamp):
    optimization_goal, event = objective_settings(args.objetivo)
    campaign_name = f"{product['nome']} | {args.objetivo} | {run_stamp}"
    campaign = {
        "name": campaign_name,
        "objective": args.objetivo,
        "status": "PAUSED",
        "special_ad_categories": [],
    }
    adset = {
        "name": f"{product['nome']} | conjunto | {run_stamp}",
        "campaign_id": "<campaign_id> pós-criação",
        "daily_budget": budget_cents,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": optimization_goal,
        "targeting": targeting_payload(),
        "promoted_object": {"pixel_id": str(product["pixel_id"]), "custom_event_type": event},
        "status": "PAUSED",
    }
    ads = []
    for number, path in enumerate(creatives, 1):
        link = tracked_link(product["link_checkout"], args.produto, run_stamp, number)
        kind = creative_kind(path)
        if kind == "image":
            creative = {
                "name": f"{product['nome']} | criativo {number}",
                "object_story_spec": {
                    "link_data": {
                        "link": link,
                        "message": str(product["descricao"]),
                        "name": str(product["headline"]),
                        "description": str(product["descricao"]),
                        "image_hash": "<hash do upload>",
                        "call_to_action": {"type": "LEARN_MORE", "value": {"link": link}},
                    }
                },
            }
            upload = {"endpoint": f"/act_{account}/adimages", "arquivo": path}
        else:
            creative = {
                "name": f"{product['nome']} | criativo {number}",
                "object_story_spec": {
                    "video_data": {
                        "video_id": "<id do upload>",
                        "message": str(product["descricao"]),
                        "title": str(product["headline"]),
                        "link_description": str(product["descricao"]),
                        "call_to_action": {"type": "LEARN_MORE", "value": {"link": link}},
                    }
                },
            }
            upload = {"endpoint": f"/act_{account}/advideos", "arquivo": path}
        ads.append(
            {
                "criativo": path,
                "tracking_link": link,
                "upload": upload,
                "creative_payload": creative,
                "ad_payload": {
                    "name": f"{product['nome']} | anúncio {number}",
                    "adset_id": "<adset_id pós-criação>",
                    "creative": {"creative_id": "<creative_id pós-criação>"},
                    "status": "PAUSED",
                },
            }
        )
    return {"campaign": campaign, "adset": adset, "ads": ads}


def upload_creative(path, account, token, kind):
    content = Path(path).read_bytes()
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    endpoint = f"/act_{account}/adimages" if kind == "image" else f"/act_{account}/advideos"
    response = graph_request("POST", endpoint, token, multipart=(Path(path).name, content_type, content))
    if kind == "image":
        images = response.get("images", {}) if isinstance(response, dict) else {}
        first = next(iter(images.values()), {}) if isinstance(images, dict) else {}
        asset_id = first.get("hash") if isinstance(first, dict) else None
    else:
        asset_id = response.get("id") if isinstance(response, dict) else None
    if not asset_id:
        raise MetaAPIError(f"a Graph API não retornou o identificador do criativo {path}")
    return asset_id


def create_campaign(args, product, account, token, creatives, budget_cents, run_stamp):
    plan = payload_plan(args, product, account, creatives, budget_cents, run_stamp)
    campaign_response = graph_request("POST", f"/act_{account}/campaigns", token, plan["campaign"])
    campaign_id = campaign_response.get("id") if isinstance(campaign_response, dict) else None
    if not campaign_id:
        raise MetaAPIError("a Graph API não retornou o ID da campanha")

    adset_fields = dict(plan["adset"])
    adset_fields["campaign_id"] = campaign_id
    adset_fields["targeting"] = json.dumps(adset_fields["targeting"], separators=(",", ":"))
    adset_fields["promoted_object"] = json.dumps(adset_fields["promoted_object"], separators=(",", ":"))
    adset_response = graph_request("POST", f"/act_{account}/adsets", token, adset_fields)
    adset_id = adset_response.get("id") if isinstance(adset_response, dict) else None
    if not adset_id:
        raise MetaAPIError("a Graph API não retornou o ID do conjunto de anúncios")

    ledger_rows = []
    for number, item in enumerate(plan["ads"], 1):
        kind = creative_kind(item["criativo"])
        asset_id = upload_creative(item["criativo"], account, token, kind)
        creative_fields = dict(item["creative_payload"])
        story = dict(creative_fields["object_story_spec"])
        if kind == "image":
            link_data = dict(story["link_data"])
            link_data["image_hash"] = asset_id
            story["link_data"] = link_data
        else:
            video_data = dict(story["video_data"])
            video_data["video_id"] = asset_id
            story["video_data"] = video_data
        creative_fields["object_story_spec"] = json.dumps(story, separators=(",", ":"))
        creative_response = graph_request("POST", f"/act_{account}/adcreatives", token, creative_fields)
        creative_id = creative_response.get("id") if isinstance(creative_response, dict) else None
        if not creative_id:
            raise MetaAPIError(f"a Graph API não retornou o creative_id do anúncio {number}")
        ad_fields = {
            "name": item["ad_payload"]["name"],
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}, separators=(",", ":")),
            "status": "PAUSED",
        }
        ad_response = graph_request("POST", f"/act_{account}/ads", token, ad_fields)
        ad_id = ad_response.get("id") if isinstance(ad_response, dict) else None
        if not ad_id:
            raise MetaAPIError(f"a Graph API não retornou o ad_id do anúncio {number}")
        ledger_rows.append(
            {
                "criativo": item["criativo"],
                "ad_id": ad_id,
                "adset_id": adset_id,
                "campaign_id": campaign_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    return campaign_id, adset_id, ledger_rows


def append_ledger(rows):
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LEDGER_PATH.exists():
        try:
            ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"não foi possível ler o ledger existente: {exc}") from None
        if not isinstance(ledger, list):
            raise ConfigError("o ledger existente precisa ser uma lista JSON")
    else:
        ledger = []
    ledger.extend(rows)
    LEDGER_PATH.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Cria campanha Meta pausada com tracking por anúncio")
    parser.add_argument("--produto", required=True)
    parser.add_argument("--criativo", action="append", required=True)
    parser.add_argument("--budget", required=True)
    parser.add_argument("--objetivo", choices=OBJECTIVES, default="LEAD_GENERATION")
    parser.add_argument("--conta")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    env = read_env_file(META_ENV)
    product = load_product(args.produto)
    account = normalize_account(args.conta or env.get("META_AD_ACCOUNT_ID"))
    budget_cents = money_to_cents(args.budget)
    creatives = []
    for raw_path in args.criativo:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            raise ConfigError(f"criativo não encontrado: {raw_path}")
        creative_kind(path)
        creatives.append(str(path))

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    plan = payload_plan(args, product, account, creatives, budget_cents, run_stamp)
    if args.dry_run:
        print("DRY-RUN: nenhuma chamada foi enviada à Graph API e nenhum ledger foi alterado.")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    token = env.get("META_ACCESS_TOKEN", "").strip()
    if not token:
        raise ConfigError("META_ACCESS_TOKEN não encontrado em ~/.operacao-ia/config/meta.env")
    campaign_id, adset_id, rows = create_campaign(
        args, product, account, token, creatives, budget_cents, run_stamp
    )
    append_ledger(rows)
    print("Campanha criada com status PAUSED.")
    print(f"Campanha: {campaign_id}")
    print(f"Conjunto: {adset_id}")
    print(f"Anúncios criados: {len(rows)}")
    print(f"Ads Manager: https://business.facebook.com/adsmanager/manage/campaigns?act={account}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ConfigError, MetaAPIError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("ERRO: falha inesperada ao preparar a campanha; verifique a configuração e tente novamente.", file=sys.stderr)
        sys.exit(1)
