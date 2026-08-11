#!/usr/bin/env python3
"""Setup 15 — Etapa 5: tracking de canal e preflight de campanhas.

O schema lógico de canal usado pelo tracking é:

    channel, traffic_source, utm_source, utm_medium, utm_campaign,
    gclid, referrer_host

A classificação deve ser feita em cascata, na ordem **sck > gclid > utm >
referrer**: primeiro uma SCK explícita, depois o identificador gclid, depois os
parâmetros UTM e, por fim, o host do referenciador. O SQL de persistência não é
implementado nesta etapa; o script client-side é apenas copiado para a LP do
aluno.
"""
import datetime as dt
import filecmp
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / "skills"
SKILLS_DST = Path.home() / ".claude" / "skills"
STATE_ROOT = Path.home() / ".operacao-ia"
SCRIPTS_DST = STATE_ROOT / "scripts"
CONFIG_DIR = STATE_ROOT / "config"
TRACKING_ENV = CONFIG_DIR / "tracking.env"
TRACKING_DST = SCRIPTS_DST / "zx-tracking.js"
PROGRESS = CONFIG_DIR / "setup15_progress.json"
PREFLIGHT_SOURCE = SKILLS_SRC / "meta-campaign" / "scripts" / "preflight_guardian.py"

CHANNEL_SCHEMA = (
    "channel",
    "traffic_source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "gclid",
    "referrer_host",
)
CLASSIFIER_PRECEDENCE = ("sck", "gclid", "utm", "referrer")


# ---------------------------------------------------------------------------
# Arquivos e configuração protegida
# ---------------------------------------------------------------------------
def _read_input(prompt: str, default: str = "") -> str:
    try:
        answer = input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    answer = answer.strip()
    return answer if answer else default


def _mask(value: str) -> str:
    if not value:
        return "(não informado)"
    if len(value) <= 4:
        return "••••"
    if len(value) <= 12:
        return f"{value[:2]}…{value[-2:]}"
    return f"{value[:8]}…{value[-4:]}"


def _read_env(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path.is_file():
        return result
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            result[key.strip()] = value
    except (OSError, UnicodeError):
        return {}
    return result


def _write_env(path: Path, values: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in sorted(values):
        value = str(values[key]).replace("\n", " ").replace("\r", " ")
        lines.append(f"{key}={value}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _tracking_source() -> Optional[Path]:
    """Localiza o script sem depender de uma única organização da pasta skills/."""
    candidates = (
        SKILLS_SRC / "tracking-canal-vendas" / "zx-tracking.js",
        SKILLS_SRC / "tracking-canal-vendas" / "scripts" / "zx-tracking.js",
        SKILLS_SRC / "tracking" / "zx-tracking.js",
        SKILLS_SRC / "zx-tracking.js",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if SKILLS_SRC.is_dir():
        for candidate in sorted(SKILLS_SRC.rglob("zx-tracking.js")):
            if candidate.is_file():
                return candidate
    return None


def _copy_tracking(source: Optional[Path]) -> None:
    if source is None:
        print("⚠️ zx-tracking.js ainda não encontrado em skills/; a cópia será feita quando a skill chegar ao repo.")
        return

    SCRIPTS_DST.mkdir(parents=True, exist_ok=True)
    if TRACKING_DST.is_file() and filecmp.cmp(str(source), str(TRACKING_DST), shallow=False):
        print("⏭ zx-tracking.js já está idêntico no destino, pulado.")
        return

    if TRACKING_DST.exists():
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = TRACKING_DST.with_name(f"zx-tracking.js.bak-{timestamp}")
        shutil.copy2(TRACKING_DST, backup)
        print(f"💾 Versão local diferente preservada em {backup}.")

    shutil.copy2(source, TRACKING_DST)
    print("✅ zx-tracking.js copiado para ~/.operacao-ia/scripts/zx-tracking.js.")


# ---------------------------------------------------------------------------
# Instalação idempotente da skill preflight_guardian
# ---------------------------------------------------------------------------
def _dirs_equal(left: Path, right: Path) -> bool:
    if not (left.is_dir() and right.is_dir()):
        return False
    comparison = filecmp.dircmp(str(left), str(right))
    if (
        comparison.left_only
        or comparison.right_only
        or comparison.diff_files
        or comparison.funny_files
    ):
        return False
    return all(_dirs_equal(left / name, right / name) for name in comparison.common_dirs)


def _backup_path(slug: str) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return SKILLS_DST / f".s15-backup-{slug}-{timestamp}"


def install_preflight_guardian(source: Optional[Path] = None) -> bool:
    destination = SKILLS_DST / "preflight_guardian"
    destination_file = destination / "preflight_guardian.py"
    if source is None or not source.is_file():
        print("⚠️ Skill preflight_guardian ainda não encontrada em skills/; não é erro fatal.")
        return False

    SKILLS_DST.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    if destination_file.is_file() and filecmp.cmp(str(source), str(destination_file), shallow=False):
        print("⏭ Skill preflight_guardian: já idêntica, pulada.")
        return True

    if destination_file.exists():
        backup = _backup_path("preflight_guardian.py")
        shutil.copy2(destination_file, backup)
        print(f"💾 Backup do preflight_guardian criado em {backup}.")

    shutil.copy2(source, destination_file)
    print("✅ Skill preflight_guardian instalada em ~/.claude/skills/.")
    return True


def _set_tracking_pending(pending: bool) -> None:
    try:
        progress = {}
        if PROGRESS.exists():
            progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
            if not isinstance(progress, dict):
                raise ValueError("checkpoint não contém um objeto JSON")
        progress["etapa5_pendente"] = pending
        stages = progress.setdefault("stages", {})
        if isinstance(stages, dict):
            stages["5"] = {
                "status": "pending" if pending else "completed",
                "title": "Etapa 5 — Tracking e mensuração",
            }
        PROGRESS.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS.write_text(
            json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"⚠️ Não foi possível atualizar o checkpoint de tracking: {exc}")


# ---------------------------------------------------------------------------
# PIXEL_ID opcional
# ---------------------------------------------------------------------------
def configure_pixel() -> None:
    values = _read_env(TRACKING_ENV)
    configured = values.get("PIXEL_CONFIGURED", "").lower() == "true"
    current = values.get("PIXEL_ID", "").strip()

    if current:
        print(f"✅ PIXEL_ID já configurado e reaproveitado ({_mask(current)}).")
    elif configured:
        print("⏭ PIXEL_ID não informado anteriormente; configuração opcional mantida em branco.")
    else:
        pixel = _read_input("PIXEL_ID (opcional; pressione Enter para pular): ", "")
        values["PIXEL_ID"] = pixel
        values["PIXEL_CONFIGURED"] = "true"
        if pixel:
            print(f"✅ PIXEL_ID gravado de forma protegida ({_mask(pixel)}).")
        else:
            print("⏭ PIXEL_ID não informado; o tracking local continuará disponível.")

    values.setdefault("PIXEL_ID", current)
    values["TRACKING_SCHEMA"] = ",".join(CHANNEL_SCHEMA)
    values["CHANNEL_CLASSIFIER"] = ">".join(CLASSIFIER_PRECEDENCE)
    values.setdefault("PIXEL_CONFIGURED", "true")
    _write_env(TRACKING_ENV, values)
    print("✅ tracking.env gravado com chmod 600.")


def main() -> int:
    print("\n[█████░░░░░] Etapa 5 de 8 — Tracking e mensuração")
    print(
        "O tracking registra canal, origem, UTMs, gclid e referenciador. "
        "A precedência é sck > gclid > utm > referrer."
    )

    tracking_source = _tracking_source()
    preflight_source = PREFLIGHT_SOURCE if PREFLIGHT_SOURCE.is_file() else None
    _copy_tracking(tracking_source)
    install_preflight_guardian(preflight_source)
    configure_pixel()

    if tracking_source is None and preflight_source is None:
        _set_tracking_pending(True)
        print(
            "\n⚠️ Etapa 5 pendente: nenhum tracking foi instalado e o gate de tracking "
            "não está ativo. Adicione zx-tracking.js ou preflight_guardian ao repo "
            "e execute esta etapa novamente."
        )
        return 1

    _set_tracking_pending(False)

    print(
        "\n📋 Para instalar manualmente na sua LP, abra "
        "~/.operacao-ia/scripts/zx-tracking.js, copie o conteúdo e cole-o dentro "
        "de uma tag <script> no <head> do site. A instalação na LP é guiada pelo Claude."
    )
    print("✅ Etapa 5 concluída; integrações e domínio podem ser configurados depois.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
