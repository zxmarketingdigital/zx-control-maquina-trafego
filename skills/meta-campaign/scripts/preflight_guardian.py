#!/usr/bin/env python3
"""Checagem somente leitura de pixel Meta e link de destino."""

import argparse
import json
import math
import sys
from numbers import Number
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

GRAPH_BASE = "https://graph.facebook.com/v21.0"
META_ENV_PATH = Path.home() / ".operacao-ia" / "config" / "meta.env"


class CheckError(RuntimeError):
    pass


def load_env():
    values = {}
    if not META_ENV_PATH.exists():
        return values
    for raw_line in META_ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key.strip()] = value
    return values


def safe_message(message, token):
    text = str(message)
    return text.replace(token, "[TOKEN OCULTO]") if token else text


def decode_response(raw):
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {"raw": text[:500]}


def graph_error(payload, status, token):
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        error = payload["error"]
        message = error.get("message", "erro sem mensagem")
        code = error.get("code")
        suffix = f" (código {code})" if code is not None else ""
        return CheckError(f"Meta Graph API recusou a consulta{suffix}: {safe_message(message, token)}")
    detail = payload.get("raw", "resposta inválida ou vazia") if isinstance(payload, dict) else "resposta inválida"
    return CheckError(f"Meta Graph API retornou erro (HTTP {status}): {safe_message(detail, token)}")


def get_pixel_stats(pixel, token):
    endpoint = f"/{quote(str(pixel).strip(), safe='')}/stats?{urlencode({'date_preset': 'last_2_days'})}"
    request = Request(
        GRAPH_BASE + endpoint,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "operacao-ia-preflight/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = decode_response(response.read())
            status = getattr(response, "status", 200)
    except HTTPError as exc:
        payload = decode_response(exc.read())
        raise graph_error(payload, exc.code, token) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise CheckError(f"não foi possível consultar o pixel: {safe_message(exc, token)}") from None
    if not isinstance(payload, dict) or payload.get("error"):
        raise graph_error(payload, status, token)
    return payload


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, Number):
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0:
        return None
    return value


def collect_values(value, wanted, found):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in wanted:
                number = numeric(child)
                if number is not None:
                    found.append(number)
            collect_values(child, wanted, found)
    elif isinstance(value, list):
        for child in value:
            collect_values(child, wanted, found)


def event_count(payload):
    for keys in (
        {"events_received"},
        {"event_count", "total_events", "events"},
        {"count"},
    ):
        found = []
        collect_values(payload, keys, found)
        if found:
            return sum(found)
    return None


def check_pixel(pixel):
    env = load_env()
    token = env.get("META_ACCESS_TOKEN", "").strip()
    if not token:
        raise CheckError(f"META_ACCESS_TOKEN não encontrado em {META_ENV_PATH}")
    payload = get_pixel_stats(pixel, token)
    count = event_count(payload)
    if count is None:
        raise CheckError("a API não informou a contagem de eventos recentes")
    if count <= 0:
        raise CheckError("pixel sem evento recente — confirme a instalação antes de gastar com anúncio")
    return f"pixel recebeu {int(count) if count.is_integer() else count:g} evento(s) nas últimas 48h"


def validate_link(link):
    parsed = urlsplit(link)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise CheckError("URL precisa usar HTTP ou HTTPS e conter um host")


def get_link_status(link):
    request = Request(link, headers={"User-Agent": "operacao-ia-preflight/1.0"}, method="HEAD")
    try:
        with urlopen(request, timeout=5) as response:
            return getattr(response, "status", 200)
    except HTTPError as exc:
        if exc.code != 405:
            raise CheckError(f"servidor respondeu HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise CheckError(f"erro de conexão: {exc}") from None

    request = Request(link, headers={"User-Agent": "operacao-ia-preflight/1.0"}, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            return getattr(response, "status", 200)
    except HTTPError as exc:
        raise CheckError(f"servidor respondeu HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise CheckError(f"erro de conexão: {exc}") from None


def check_link(link):
    validate_link(link)
    status = get_link_status(link)
    if status != 200:
        raise CheckError(f"resposta final HTTP {status}; esperado HTTP 200")
    return "link respondeu HTTP 200"


def build_parser():
    parser = argparse.ArgumentParser(description="Verifica tracking e link antes de subir campanha Meta.")
    parser.add_argument("--pixel", required=True, help="ID do pixel Meta")
    parser.add_argument("--link", help="URL de destino para testar")
    return parser


def main():
    args = build_parser().parse_args()
    pixel_ok = False
    link_ok = True
    try:
        detail = check_pixel(args.pixel)
        pixel_ok = True
        print(f"✅ Pixel: {detail}")
    except Exception as exc:
        print(f"❌ Pixel: {exc}")

    if args.link:
        try:
            detail = check_link(args.link)
            link_ok = True
            print(f"✅ Link: {detail}")
        except Exception as exc:
            link_ok = False
            print(f"❌ Link: {exc}")
    else:
        print("✅ Link: não solicitado (check opcional)")

    if pixel_ok and link_ok:
        print("Preflight aprovado: pode subir a campanha.")
        return 0
    print("Preflight reprovado: não suba a campanha até corrigir os checks falhos.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("❌ Preflight interrompido.")
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Preflight: {exc}")
        sys.exit(1)
