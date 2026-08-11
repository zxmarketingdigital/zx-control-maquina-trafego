#!/usr/bin/env python3
"""Cria campanhas Meta pausadas a partir da configuração de um produto."""

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import subprocess
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

GRAPH_BASE = "https://graph.facebook.com/v21.0"
CONFIG_DIR = Path.home() / ".operacao-ia" / "config"
META_ENV_PATH = CONFIG_DIR / "meta.env"
PRODUCTS_DIR = CONFIG_DIR / "produtos"
LEDGER_PATH = Path.home() / ".operacao-ia" / "logs" / "ads-ledger.json"
REQUIRED_PRODUCT_FIELDS = ("nome", "preco", "link_checkout", "headline", "descricao", "pixel_id")


class MetaAPIError(RuntimeError):
    pass


def load_env(path=META_ENV_PATH):
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
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def fail(message):
    raise RuntimeError(message)


def read_product(slug):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        fail("Slug de produto inválido; use apenas letras minúsculas, números e hífens.")

    products_dir = PRODUCTS_DIR.resolve()
    path = (PRODUCTS_DIR / f"{slug}.json").resolve()
    try:
        path.relative_to(products_dir)
    except ValueError:
        fail("O caminho da configuração do produto está fora do diretório de produtos esperado.")

    if not path.exists():
        fail(
            f"Produto '{slug}' não encontrado em {path}. "
            "Cadastre o produto primeiro nessa pasta, com nome, preço, link_checkout, "
            "headline, descricao e pixel_id."
        )
    try:
        product = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Não foi possível ler a configuração do produto '{slug}': {exc}")
    if not isinstance(product, dict):
        fail(f"A configuração do produto '{slug}' precisa ser um objeto JSON.")
    missing = [field for field in REQUIRED_PRODUCT_FIELDS if not product.get(field)]
    if missing:
        fail(f"A configuração do produto '{slug}' não contém: {', '.join(missing)}.")
    return product


def parse_budget(value):
    try:
        amount = Decimal(str(value).replace(",", "."))
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
        cents = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        fail("--budget precisa ser um valor diário positivo em reais, por exemplo 25,90.")
    if cents < 1:
        fail("--budget precisa resultar em pelo menos R$ 0,01.")
    return str(int(cents))


def validate_link(link):
    parsed = urlsplit(str(link))
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        fail("O link_checkout do produto precisa ser uma URL HTTP ou HTTPS válida.")


def tracked_link(link, slug, run_stamp, ad_number):
    parsed = urlsplit(str(link))
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("utm_content", f"{slug}-{run_stamp}-ad{ad_number}"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def account_id(value):
    account = str(value or "").strip()
    if account.startswith("act_"):
        account = account[4:]
    if not account or not account.isdigit():
        fail("ID de conta inválido. Informe --conta com o ID numérico da conta Meta ou configure META_AD_ACCOUNT_ID.")
    return account


def safe_message(message, token):
    text = str(message)
    if token:
        text = text.replace(token, "[TOKEN OCULTO]")
    return text


def decode_response(raw):
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text[:500]}


def api_error(payload, status=None, token=None):
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        error = payload["error"]
        message = error.get("message", "erro sem mensagem")
        code = error.get("code")
        suffix = f" (código {code})" if code is not None else ""
        return MetaAPIError(f"Meta Graph API recusou a operação{suffix}: {safe_message(message, token)}")
    status_text = f" (HTTP {status})" if status else ""
    if isinstance(payload, dict) and payload.get("raw"):
        detail = payload["raw"]
    else:
        detail = "resposta inválida ou vazia"
    return MetaAPIError(f"Meta Graph API retornou erro{status_text}: {safe_message(detail, token)}")


def graph_post(endpoint, payload, token, timeout=60):
    fields = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            fields[key] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            fields[key] = str(value)
    request = Request(
        GRAPH_BASE + endpoint,
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "operacao-ia-meta-campaign/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = decode_response(response.read())
            status = getattr(response, "status", 200)
    except HTTPError as exc:
        body = decode_response(exc.read())
        raise api_error(body, exc.code, token) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise MetaAPIError(f"Não foi possível conectar à Meta Graph API: {safe_message(exc, token)}") from None
    if not isinstance(body, dict) or body.get("error"):
        raise api_error(body, status, token)
    return body


def multipart_post(endpoint, file_path, token):
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    boundary = f"----operacaoia{int(time.time() * 1000000)}"
    filename = file_path.name
    try:
        content = file_path.read_bytes()
    except OSError as exc:
        fail(f"Não foi possível ler o criativo '{file_path}': {exc}")
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="source"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    request = Request(
        GRAPH_BASE + endpoint,
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "operacao-ia-meta-campaign/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            body = decode_response(response.read())
            status = getattr(response, "status", 200)
    except HTTPError as exc:
        body = decode_response(exc.read())
        raise api_error(body, exc.code, token) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise MetaAPIError(f"Não foi possível enviar o criativo à Meta: {safe_message(exc, token)}") from None
    if not isinstance(body, dict) or body.get("error"):
        raise api_error(body, status, token)
    return body


def media_type(path):
    guessed = mimetypes.guess_type(str(path))[0] or ""
    if guessed.startswith("video/") or path.suffix.lower() in {".mp4", ".mov", ".m4v", ".avi", ".webm"}:
        return "video"
    if guessed.startswith("image/") or path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "image"
    fail(f"Tipo de criativo não reconhecido: '{path}'. Use uma imagem ou vídeo aprovado.")


def image_hash(uploaded):
    images = uploaded.get("images")
    if isinstance(images, dict):
        for item in images.values():
            if isinstance(item, dict) and item.get("hash"):
                return item["hash"]
    if uploaded.get("hash"):
        return uploaded["hash"]
    fail("A Meta não retornou o hash da imagem enviada.")


def video_id(uploaded):
    value = uploaded.get("id") or uploaded.get("video_id")
    if value:
        return value
    fail("A Meta não retornou o ID do vídeo enviado.")


def story_spec(product, tracking_url, kind, media_value, page_id=None):
    if kind == "image":
        spec = {
            "link_data": {
                "image_hash": media_value,
                "link": tracking_url,
                "message": str(product["descricao"]),
                "name": str(product["headline"]),
                "description": str(product["descricao"]),
                "call_to_action": {"type": "LEARN_MORE", "value": {"link": tracking_url}},
            }
        }
    else:
        spec = {
            "video_data": {
                "video_id": media_value,
                "message": str(product["descricao"]),
                "title": str(product["headline"]),
                "link_description": str(product["descricao"]),
                "call_to_action": {"type": "LEARN_MORE", "value": {"link": tracking_url}},
            }
        }
    if page_id:
        spec["page_id"] = page_id
    return spec


def make_ledger_entry(creative, ad_id, adset_id, campaign_id, timestamp, campaign_key=None):
    entry = {
        "criativo": str(creative),
        "ad_id": str(ad_id),
        "adset_id": str(adset_id),
        "campaign_id": str(campaign_id),
        "timestamp": timestamp,
    }
    if campaign_key:
        entry["campaign_key"] = campaign_key
    return entry


def campaign_key(product_slug, creatives, budget_cents):
    payload = {
        "produto": product_slug,
        "criativos": sorted(str(creative) for creative in creatives),
        "budget": budget_cents,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def existing_campaign(campaign_key_value):
    if not LEDGER_PATH.exists():
        return None
    try:
        current = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Não foi possível ler o ledger existente {LEDGER_PATH}: {exc}")
    if not isinstance(current, list):
        fail(f"O ledger {LEDGER_PATH} precisa conter uma lista JSON.")
    for entry in current:
        if not isinstance(entry, dict):
            continue
        if entry.get("campaign_key") == campaign_key_value and entry.get("campaign_id"):
            return entry
    return None


def append_ledger(entries):
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LEDGER_PATH.exists():
        try:
            current = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"Não foi possível ler o ledger existente {LEDGER_PATH}: {exc}")
        if not isinstance(current, list):
            fail(f"O ledger {LEDGER_PATH} precisa conter uma lista JSON.")
    else:
        current = []
    current.extend(entries)
    temporary = LEDGER_PATH.with_name(LEDGER_PATH.name + ".tmp")
    try:
        temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(LEDGER_PATH)
    except OSError as exc:
        fail(f"Não foi possível gravar o ledger {LEDGER_PATH}: {exc}")


def build_parser():
    parser = argparse.ArgumentParser(description="Cria campanha Meta pausada com rastreamento por anúncio.")
    parser.add_argument("--produto", required=True, help="Slug do produto cadastrado")
    parser.add_argument("--criativo", required=True, action="append", help="Imagem ou vídeo aprovado; pode repetir")
    parser.add_argument("--budget", required=True, help="Orçamento diário em reais")
    parser.add_argument("--objetivo", default="LEAD_GENERATION", choices=("LEAD_GENERATION", "CONVERSIONS", "TRAFFIC"))
    parser.add_argument("--conta", help="ID numérico da conta de anúncios")
    parser.add_argument("--dry-run", action="store_true", help="Exibe os payloads sem chamar a API")
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Pula a checagem de tracking; desaconselhado, use apenas em emergência",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Cria mesmo se já houver uma campanha equivalente no ledger",
    )
    return parser


def main():
    args = build_parser().parse_args()
    product = read_product(args.produto)
    validate_link(product["link_checkout"])
    budget_cents = parse_budget(args.budget)
    env = load_env()
    account = account_id(args.conta or env.get("META_AD_ACCOUNT_ID"))
    token = env.get("META_ACCESS_TOKEN", "").strip()
    if not args.dry_run and not token:
        fail(f"META_ACCESS_TOKEN não encontrado em {META_ENV_PATH}.")

    creatives = [Path(item).expanduser() for item in args.criativo]
    for creative in creatives:
        if not creative.is_file():
            fail(f"Criativo não encontrado: {creative}")
        media_type(creative)

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    run_stamp = now.strftime("%Y%m%d%H%M%S")
    campaign_name = f"{product['nome']} | {args.produto} | {run_stamp}"
    adset_name = f"Conjunto | {args.produto} | {run_stamp}"
    account_endpoint = f"/act_{account}"
    objective_api = {
        "LEAD_GENERATION": "OUTCOME_LEADS",
        "CONVERSIONS": "OUTCOME_SALES",
        "TRAFFIC": "OUTCOME_TRAFFIC",
    }[args.objetivo]
    optimization = {
        "LEAD_GENERATION": "LEAD_GENERATION",
        "CONVERSIONS": "OFFSITE_CONVERSIONS",
        "TRAFFIC": "LINK_CLICKS",
    }[args.objetivo]
    event_type = "LEAD" if args.objetivo == "LEAD_GENERATION" else "PURCHASE"
    page_id = env.get("META_PAGE_ID", "").strip() or None

    campaign_payload = {
        "name": campaign_name,
        "objective": objective_api,
        "status": "PAUSED",
        "special_ad_categories": [],
    }
    adset_payload = {
        "name": adset_name,
        "campaign_id": "<campaign_id>",
        "daily_budget": budget_cents,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": optimization,
        "promoted_object": {"pixel_id": str(product["pixel_id"]), "custom_event_type": event_type},
        "targeting": {"geo_locations": {"countries": ["BR"]}},
        "status": "PAUSED",
    }

    planned_ads = []
    for number, creative in enumerate(creatives, start=1):
        kind = media_type(creative)
        tracking_url = tracked_link(product["link_checkout"], args.produto, run_stamp, number)
        planned_ads.append(
            {
                "number": number,
                "path": creative,
                "kind": kind,
                "tracking_url": tracking_url,
                "creative_name": f"{args.produto} | {run_stamp} | ad{number}",
            }
        )

    key = campaign_key(args.produto, args.criativo, budget_cents)
    if not args.dry_run and not args.forcar:
        previous = existing_campaign(key)
        if previous:
            print(
                f"já existe uma campanha equivalente (ID {previous['campaign_id']}), "
                f"criada em {previous.get('timestamp', 'data desconhecida')} — "
                "use --forcar para criar mesmo assim",
                file=sys.stderr,
            )
            return 1

    if not args.dry_run and not args.skip_preflight:
        preflight_path = (Path(__file__).resolve().parent / "preflight_guardian.py").resolve()
        preflight_result = subprocess.run(
            [sys.executable, str(preflight_path), "--pixel", str(product["pixel_id"])],
            check=False,
        )
        if preflight_result.returncode != 0:
            print(
                "preflight de tracking falhou — corrija antes de subir campanha",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.dry_run:
        preview = {
            "dry_run": True,
            "account": account,
            "campaign": {"endpoint": f"{account_endpoint}/campaigns", "payload": campaign_payload},
            "adset": {"endpoint": f"{account_endpoint}/adsets", "payload": adset_payload},
            "ads": [],
        }
        for planned in planned_ads:
            story = story_spec(product, planned["tracking_url"], planned["kind"], "<media_id_or_hash>", page_id)
            preview["ads"].append(
                {
                    "media_upload": {
                        "endpoint": f"{account_endpoint}/{'advideos' if planned['kind'] == 'video' else 'adimages'}",
                        "filename": str(planned["path"]),
                    },
                    "creative": {
                        "endpoint": f"{account_endpoint}/adcreatives",
                        "payload": {"name": planned["creative_name"], "object_story_spec": story},
                    },
                    "ad": {
                        "endpoint": f"{account_endpoint}/ads",
                        "payload": {
                            "name": planned["creative_name"],
                            "adset_id": "<adset_id>",
                            "creative": {"creative_id": "<creative_id>"},
                            "status": "PAUSED",
                        },
                    },
                    "tracking_url": planned["tracking_url"],
                }
            )
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    campaign_response = graph_post(f"{account_endpoint}/campaigns", campaign_payload, token)
    campaign_id = campaign_response.get("id")
    if not campaign_id:
        fail("A Meta não retornou o ID da campanha criada.")

    adset_payload["campaign_id"] = campaign_id
    adset_response = graph_post(f"{account_endpoint}/adsets", adset_payload, token)
    adset_id = adset_response.get("id")
    if not adset_id:
        fail("A Meta não retornou o ID do conjunto criado.")

    entries = []
    for planned in planned_ads:
        upload_endpoint = f"{account_endpoint}/{'advideos' if planned['kind'] == 'video' else 'adimages'}"
        uploaded = multipart_post(upload_endpoint, planned["path"], token)
        media_value = video_id(uploaded) if planned["kind"] == "video" else image_hash(uploaded)
        creative_payload = {
            "name": planned["creative_name"],
            "object_story_spec": story_spec(product, planned["tracking_url"], planned["kind"], media_value, page_id),
        }
        creative_response = graph_post(f"{account_endpoint}/adcreatives", creative_payload, token)
        creative_id = creative_response.get("id")
        if not creative_id:
            fail("A Meta não retornou o ID do criativo criado.")
        ad_payload = {
            "name": planned["creative_name"],
            "adset_id": adset_id,
            "creative": {"creative_id": creative_id},
            "status": "PAUSED",
        }
        ad_response = graph_post(f"{account_endpoint}/ads", ad_payload, token)
        ad_id = ad_response.get("id")
        if not ad_id:
            fail("A Meta não retornou o ID do anúncio criado.")
        entry = make_ledger_entry(planned["path"], ad_id, adset_id, campaign_id, timestamp, key)
        append_ledger([entry])
        entries.append(entry)

    print(f"Campanha criada (PAUSED): {campaign_id}")
    print(f"Conjunto criado (PAUSED): {adset_id}")
    for entry in entries:
        print(f"Anúncio criado (PAUSED): {entry['ad_id']} — criativo {entry['criativo']}")
    print(f"Revise no Ads Manager antes de ativar: https://business.facebook.com/adsmanager/manage/campaigns?act={account}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Operação interrompida.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
