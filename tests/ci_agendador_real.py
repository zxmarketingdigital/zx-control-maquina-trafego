"""Só para o CI: cria a tarefa de verdade no agendador do sistema, dispara e remove.

Não roda nos testes locais (mexeria no agendador da máquina). Uso no CI:
    python tests/ci_agendador_real.py
"""

import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "setup"))

import agendador  # noqa: E402


def main():
    so = platform.system()
    if so != "Windows":
        print(f"{so}: teste real só roda no Windows (launchd/cron exigem sessão de usuário).")
        return 0
    tmp = Path(tempfile.mkdtemp()) / "blog com espaço"
    (tmp / "generator").mkdir(parents=True)
    sentinela = "SENTINELA-" + uuid.uuid4().hex
    # Fixture mínima: prova que o wrapper .cmd rodou o node com o script certo, na pasta certa.
    (tmp / "generator" / "daily_publish.js").write_text(
        "console.log(%r + ' ' + process.cwd());\n" % sentinela, encoding="utf-8"
    )
    home = Path(tempfile.mkdtemp())
    r = agendador.instalar(hora="23:59", blog_dir=tmp, sistema="Windows", home=home)
    print(r)
    if not r["ok"]:
        return 1
    try:
        st = agendador.status(sistema="Windows", home=home)
        print(st)
        if not st["ok"]:
            return 1
        subprocess.run(["schtasks", "/Run", "/TN", agendador.windows_task_name()], check=True)
        log = tmp / "logs" / "blog-daily.log"
        err = tmp / "logs" / "blog-daily-err.log"
        for _ in range(60):
            texto = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
            if sentinela in texto:
                break
            time.sleep(1)
        else:
            print("A tarefa não escreveu a sentinela em 60s — o wrapper .cmd não rodou o node.")
            for p in (log, err):
                if p.exists():
                    print(f"--- {p.name}\n{p.read_text(encoding='utf-8', errors='replace')}")
            return 1
        print(texto)
        if "blog com espaço" not in texto:
            print("O node não rodou dentro da pasta do blog.")
            return 1
        return 0
    finally:
        rm = agendador.remover(sistema="Windows", home=home)
        print(rm)
        if agendador.status(sistema="Windows", home=home)["ok"]:
            print("A tarefa continuou existindo depois de remover.")
            sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
