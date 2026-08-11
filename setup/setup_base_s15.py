#!/usr/bin/env python3
"""Setup 15 — Etapa 0: Base e diagnóstico."""
import json
import platform
import shutil
import sys
from pathlib import Path

OPERACAO = Path.home() / ".operacao-ia"
CONFIG_DIR = OPERACAO / "config"
PROGRESS = CONFIG_DIR / "setup15_progress.json"

REQUIRED_DIRS = [
    CONFIG_DIR,
    OPERACAO / "scripts",
    OPERACAO / "dashboards",
    OPERACAO / "leads",
    OPERACAO / "logs",
]

ETAPAS = [
    "Etapa 0 — Base e diagnóstico",
    "Etapa 1 — Chaves e contas",
    "Etapa 2 — Criativos com IA: imagem",
    "Etapa 3 — Criativos com IA: vídeo",
    "Etapa 4 — Tráfego pago avançado: Meta + Google",
    "Etapa 5 — Tracking e mensuração",
    "Etapa 6 — Tráfego orgânico e Blog SEO",
    "Etapa 7 — A Máquina no automático",
    "Etapa 8 — Auditoria e fechamento",
]


def check_python():
    version = sys.version_info
    if version < (3, 9):
        print(f"❌ Python 3.9+ requerido. Você tem {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor} disponível")
    return True


def check_node():
    if shutil.which("node"):
        print("✅ Node.js instalado")
    else:
        print("⚠️  Node.js não encontrado — necessário para partes do vídeo e do blog")
    return True


def check_chrome():
    commands = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
    paths = (
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
    )
    if any(shutil.which(command) for command in commands) or any(path.exists() for path in paths):
        print("✅ Google Chrome/Chromium instalado")
    else:
        print("⚠️  Google Chrome não encontrado — necessário para renderização local de vídeo")
    return True


def check_ffmpeg():
    if shutil.which("ffmpeg"):
        print("✅ ffmpeg instalado")
    else:
        print("⚠️  ffmpeg não encontrado — necessário para exportar vídeos MP4")
    return True


def check_gh():
    if shutil.which("gh"):
        print("✅ gh CLI instalado")
    else:
        print("⚠️  gh CLI não encontrado — necessário apenas para partes de deploy e repositório")
    return True


def create_dirs():
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
    print(f"✅ Estrutura criada ou reaproveitada em {OPERACAO}/")


def load_progress():
    if not PROGRESS.exists():
        progress = {
            "setup": 15,
            "phase_completed": 0,
            "stages": {},
        }
        PROGRESS.write_text(
            json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return progress

    try:
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(
            f"❌ checkpoint corrompido em {PROGRESS} — mova/apague o arquivo "
            "pra recomeçar, ou peça ajuda"
        )
        raise SystemExit(1)

    if not isinstance(progress, dict):
        print(
            f"❌ checkpoint corrompido em {PROGRESS} — mova/apague o arquivo "
            "pra recomeçar, ou peça ajuda"
        )
        raise SystemExit(1)
    return progress


def save_progress(progress):
    stages = progress.setdefault("stages", {})
    stages["0"] = {
        "status": "completed",
        "title": ETAPAS[0],
    }
    PROGRESS.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def show_plan():
    print("\n" + "=" * 64)
    print("PLANO DAS 9 ETAPAS — Setup 15")
    print("=" * 64)
    for etapa in ETAPAS:
        print(f"  {etapa}")
    print("=" * 64)


def main():
    print(f"\n🔍 Diagnóstico inicial — {platform.system()} {platform.release()}\n")
    python_ok = check_python()
    check_node()
    check_chrome()
    check_ffmpeg()
    check_gh()

    create_dirs()
    progress = load_progress()
    if progress is not None:
        try:
            save_progress(progress)
        except OSError:
            print("⚠️  Não foi possível atualizar o checkpoint; os dados existentes foram preservados")

    show_plan()

    if not python_ok:
        print("\n❌ A Etapa 0 não pode ser concluída com esta versão do Python.")
        return 1

    print(f"\n✅ Etapa 0 concluída. Checkpoint salvo em {PROGRESS}.")
    print("Pronto para a Etapa 1 (Chaves e contas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
