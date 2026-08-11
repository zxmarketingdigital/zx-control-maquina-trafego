#!/usr/bin/env python3
"""Verifica pixel e link antes de uma subida de campanha."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GRAPH_VERSION = "v21.0"
META_ENV = Path.home() / ".operacao-ia" / "config" / "meta.env"


class GuardianError(Exception):
    pass


def redact(value, secret=""):
    text = str(value)
    return text.replace(secret, "[TOKEN REDACTED]") if secret else text


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


def graph_stats(pixel, token):
    now = datetime.now(timezone.utc)
    params = {
        "since": int((now - timedelta(hours=48)).timestamp()),
        "until": int(now.timestamp()),
        "access_token": token,
    }
    request = Request(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{pixel}/stats?{urlencode(params)}",
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            message = payload.get("error", {}).get("message", "resposta sem detalhes")
        except (ValueError, AttributeError):
            message = "resposta sem detalhes"
        raise GuardianError(f"Graph API HTTP {exc.code}: {redact(message, token)}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise GuardianError(f"não foi possível consultar o pixel: {redact(exc, token)}") from None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise GuardianError("a Graph API retornou JSON inválido") from None
    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        message = error.get("message", "erro não especificado") if isinstance(error, dict) else error
        raise GuardianError(f"a Graph API recusou a consulta: {redact(message, token)}") from None
    return payload


def event_count(value):
    keys = {"events_received", "event_count", "events", "count", "num_events", "total_events"}
    if isinstance(value, dict):
        total = 0
        found = False
        for key, item in value.items():
            if key in keys and isinstance(item, (int, float)):
                total += item
                found = True
            elif isinstance(item, (dict, list)):
                nested = event_count(item)
                if nested is not None:
                    total += nested
                    found = True
        return total if found else None
    if isinstance(value, list):
        values = [event_count(item) for item in value]
        values = [item for item in values if item is not None]
        return sum(values) if values else None
    return None


def check_pixel(pixel, token):
    if not token:
        return False, "META_ACCESS_TOKEN não configurado em ~/.operacao-ia/config/meta.env"
    try:
        payload = graph_stats(pixel, token)
        count = event_count(payload)
        if count is None:
            return False, "a resposta não informou a contagem de eventos recentes"
        if count <= 0:
            return False, "pixel sem evento recente — confirme a instalação antes de gastar com anúncio"
        return True, f"{int(count)} evento(s) encontrado(s) nas últimas 48h"
    except Exception as exc:
        return False, str(exc)


def check_link(link):
    if not link:
        return True, "não solicitado"
    if not link.startswith(("http://", "https://")):
        return False, "URL precisa usar http:// ou https://"
    request = Request(link, headers={"User-Agent": "meta-campaign-preflight/1.0"}, method="HEAD")
    try:
        with urlopen(request, timeout=5) as response:
            if response.status == 200:
                return True, f"HTTP {response.status}"
            status = response.status
    except HTTPError as exc:
        status = exc.code
        if status not in {403, 405, 501}:
            return False, f"HTTP {status}"
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return False, f"erro de conexão: {exc}"

    if status not in {403, 405, 501}:
        return False, f"HTTP {status}"
    request = Request(link, headers={"User-Agent": "meta-campaign-preflight/1.0"}, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            if response.status == 200:
                response.read(1)
                return True, f"HTTP {response.status} após fallback GET"
            return False, f"HTTP {response.status}"
    except HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return False, f"erro de conexão: {exc}"


def parse_args():
    parser = argparse.ArgumentParser(description="Guardian read-only para pixel e link")
    parser.add_argument("--pixel", required=True)
    parser.add_argument("--link")
    return parser.parse_args()


def main():
    args = parse_args()
    env = read_env_file(META_ENV)
    pixel_ok, pixel_message = check_pixel(args.pixel.strip(), env.get("META_ACCESS_TOKEN", "").strip())
    link_ok, link_message = check_link(args.link)
    print(f"{'✅' if pixel_ok else '❌'} Pixel recebendo evento recente: {pixel_message}")
    if args.link:
        print(f"{'✅' if link_ok else '❌'} Link de destino: {link_message}")
    else:
        print("✅ Link de destino: não solicitado")
    if pixel_ok and link_ok:
        print("PASS: preflight aprovado; pode subir a campanha.")
        return 0
    print("BLOCK: preflight reprovado; não suba a campanha.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("❌ Guardian: falha inesperada ao executar o check; não suba a campanha.", file=sys.stderr)
        sys.exit(1)
