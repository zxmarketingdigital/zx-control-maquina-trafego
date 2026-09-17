#!/usr/bin/env python3
"""Agendamento diário do blog do Setup 15, em qualquer sistema.

- macOS: LaunchAgent (launchagents/com.setup15.blog-daily.plist.template)
- Windows: Agendador de Tarefas (schtasks) chamando um wrapper .cmd
- Linux: crontab do usuário, numa linha marcada

Todas as funções devolvem {"ok": bool, "sistema": str, "detalhe": str} e nunca
lançam exceção por causa do sistema operacional.
"""
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "blog"
PLIST_TEMPLATE = ROOT / "launchagents" / "com.setup15.blog-daily.plist.template"
LABEL = "com.setup15.blog-daily"
WINDOWS_TASK = "ZXSetup15BlogDaily"
CRON_MARKER = "# zx-setup15-blog-daily"
# Comandos de sistema curtos (launchctl/schtasks/crontab): 30s é folga ampla.
CMD_TIMEOUT = 30


def _sistema(sistema):
    return sistema or platform.system()


def _home(home):
    return Path(home) if home else Path.home()


def plist_path(home=None):
    return _home(home) / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def wrapper_path(home=None):
    return _home(home) / ".operacao-ia" / "bin" / "blog-daily.cmd"


def _result(ok, sistema, detalhe):
    return {"ok": bool(ok), "sistema": sistema, "detalhe": detalhe}


def _run(args, input_text=None):
    """Roda um comando curto; devolve CompletedProcess ou None se não rodou."""
    try:
        return subprocess.run(
            args,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=CMD_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _output(proc):
    if proc is None:
        return ""
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def _parse_hora(hora):
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(hora or "").strip())
    if not match:
        return None
    hh, mm = int(match.group(1)), int(match.group(2))
    if hh > 23 or mm > 59:
        return None
    return hh, mm


# ---------------------------------------------------------------- macOS

def _instalar_darwin(blog_dir, node_bin, hh, mm, home):
    if not PLIST_TEMPLATE.is_file():
        return _result(False, "Darwin", f"Template não encontrado: {PLIST_TEMPLATE}")
    target = plist_path(home)
    node_dir = str(Path(node_bin).parent)
    plist = PLIST_TEMPLATE.read_text(encoding="utf-8")
    plist = plist.replace("{BLOG_DIR}", xml_escape(str(blog_dir)))
    plist = plist.replace("{HOME}", xml_escape(str(_home(home))))
    plist = plist.replace("{NODE_BIN}", xml_escape(node_bin))
    plist = plist.replace("{NODE}", xml_escape(node_bin))
    plist = re.sub(
        r"(<key>Hour</key>\s*<integer>)\d+(</integer>)", r"\g<1>%d\g<2>" % hh, plist
    )
    plist = re.sub(
        r"(<key>Minute</key>\s*<integer>)\d+(</integer>)", r"\g<1>%d\g<2>" % mm, plist
    )
    plist = plist.replace(
        "<string>/usr/local/bin:", "<string>" + xml_escape(node_dir) + ":/usr/local/bin:", 1
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        _run(["launchctl", "unload", str(target)])
    target.write_text(plist, encoding="utf-8")
    _run(["launchctl", "load", str(target)])
    listed = _run(["launchctl", "list"])
    matches = [line for line in _output(listed).splitlines() if LABEL in line]
    if matches:
        detalhe = f"LaunchAgent instalado em {target}.\n" + "\n".join(matches)
    else:
        detalhe = (
            f"LaunchAgent gravado em {target}, mas o label ainda não apareceu em "
            "'launchctl list'; confira o status do launchctl."
        )
    return _result(True, "Darwin", detalhe)


def _remover_darwin(home):
    target = plist_path(home)
    if not target.exists():
        return _result(True, "Darwin", "LaunchAgent blog-daily: já removido")
    unloaded = _run(["launchctl", "unload", str(target)])
    aviso = ""
    if unloaded is None or unloaded.returncode != 0:
        aviso = " (unload não confirmou; o job pode já não estar carregado)"
    try:
        target.unlink()
    except OSError as exc:
        return _result(False, "Darwin", f"Não foi possível remover {target}: {exc}")
    return _result(True, "Darwin", f"LaunchAgent blog-daily removido{aviso}")


def _status_darwin(home):
    target = plist_path(home)
    listed = _run(["launchctl", "list"])
    carregado = any(LABEL in line for line in _output(listed).splitlines())
    return _result(
        target.exists() and carregado,
        "Darwin",
        f"plist {'existe' if target.exists() else 'ausente'}; "
        f"job {'carregado' if carregado else 'não carregado'}",
    )


# ---------------------------------------------------------------- Windows

def _cmd_quote(value):
    # Dentro de um .cmd, % precisa ser dobrado para não virar variável.
    return '"' + str(value).replace("%", "%%") + '"'


def _instalar_windows(blog_dir, node_bin, hh, mm, home):
    wrapper = wrapper_path(home)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    blog = Path(blog_dir)
    linhas = [
        "@echo off",
        "chcp 65001 >nul",
        "cd /d " + _cmd_quote(blog),
        'if not exist "logs" mkdir "logs"',
        _cmd_quote(node_bin)
        + ' "generator\\daily_publish.js" >> "logs\\blog-daily.log" 2>> "logs\\blog-daily-err.log"',
        "",
    ]
    wrapper.write_text("\r\n".join(linhas), encoding="utf-8")
    proc = _run([
        "schtasks", "/Create", "/SC", "DAILY", "/TN", WINDOWS_TASK,
        "/TR", '"' + str(wrapper) + '"',
        "/ST", "%02d:%02d" % (hh, mm), "/F",
    ])
    if proc is None:
        return _result(False, "Windows", "Não foi possível executar o schtasks.")
    if proc.returncode != 0:
        return _result(False, "Windows", "schtasks recusou a criação: " + _output(proc))
    return _result(
        True,
        "Windows",
        f"Tarefa '{WINDOWS_TASK}' criada no Agendador de Tarefas "
        f"(todo dia às {hh:02d}:{mm:02d}), executando {wrapper}.",
    )


def _remover_windows(home):
    proc = _run(["schtasks", "/Delete", "/TN", WINDOWS_TASK, "/F"])
    partes = []
    if proc is not None and proc.returncode == 0:
        partes.append(f"Tarefa '{WINDOWS_TASK}' removida")
    else:
        partes.append(f"Tarefa '{WINDOWS_TASK}': já removida ou inexistente")
    wrapper = wrapper_path(home)
    try:
        if wrapper.exists():
            wrapper.unlink()
            partes.append("wrapper removido")
    except OSError as exc:
        return _result(False, "Windows", f"Não foi possível remover {wrapper}: {exc}")
    return _result(True, "Windows", "; ".join(partes))


def _status_windows(home):
    proc = _run(["schtasks", "/Query", "/TN", WINDOWS_TASK])
    existe = proc is not None and proc.returncode == 0
    return _result(
        existe,
        "Windows",
        _output(proc) if existe else f"Tarefa '{WINDOWS_TASK}' não encontrada",
    )


# ---------------------------------------------------------------- Linux

def _crontab_atual():
    if not shutil.which("crontab"):
        return None
    proc = _run(["crontab", "-l"])
    if proc is None:
        return None
    if proc.returncode != 0:
        # "no crontab for <user>" = crontab vazio
        return ""
    return proc.stdout or ""


def _sem_marcador(texto):
    return [line for line in texto.splitlines() if CRON_MARKER not in line]


def _gravar_crontab(linhas):
    conteudo = "\n".join(linhas).strip("\n")
    conteudo = conteudo + "\n" if conteudo else ""
    proc = _run(["crontab", "-"], input_text=conteudo)
    return proc is not None and proc.returncode == 0, _output(proc)


def _instalar_linux(blog_dir, node_bin, hh, mm):
    atual = _crontab_atual()
    if atual is None:
        return _result(
            False,
            "Linux",
            "crontab não encontrado. Agende manualmente: "
            f"cd {shlex.quote(str(blog_dir))}; node generator/daily_publish.js",
        )
    comando = (
        f"cd {shlex.quote(str(blog_dir))} && {shlex.quote(node_bin)} "
        "generator/daily_publish.js >> logs/blog-daily.log 2>> logs/blog-daily-err.log"
    )
    # No crontab, % vira quebra de linha se não for escapado.
    comando = comando.replace("%", "\\%")
    linha = f"{mm} {hh} * * * {comando} {CRON_MARKER}"
    ok, saida = _gravar_crontab(_sem_marcador(atual) + [linha])
    if not ok:
        return _result(False, "Linux", "crontab recusou a gravação: " + saida)
    return _result(True, "Linux", f"Linha adicionada ao crontab (todo dia às {hh:02d}:{mm:02d}).")


def _remover_linux():
    atual = _crontab_atual()
    if atual is None:
        return _result(True, "Linux", "crontab não encontrado; nada a remover")
    if CRON_MARKER not in atual:
        return _result(True, "Linux", "Agendamento blog-daily: já removido")
    ok, saida = _gravar_crontab(_sem_marcador(atual))
    if not ok:
        return _result(False, "Linux", "crontab recusou a gravação: " + saida)
    return _result(True, "Linux", "Linha do blog-daily removida do crontab")


def _status_linux():
    atual = _crontab_atual()
    existe = bool(atual) and CRON_MARKER in atual
    return _result(existe, "Linux", "linha presente no crontab" if existe else "sem linha no crontab")


# ---------------------------------------------------------------- API

def instalar(
    hora="08:00",
    blog_dir=None,
    node_bin=None,
    sistema=None,
    home=None,
):
    # type: (str, Optional[Path], Optional[str], Optional[str], Optional[Path]) -> dict
    so = _sistema(sistema)
    parsed = _parse_hora(hora)
    if parsed is None:
        return _result(False, so, f"Hora inválida: {hora!r} (use HH:MM)")
    hh, mm = parsed
    blog = Path(blog_dir) if blog_dir else BLOG_DIR
    node = node_bin or shutil.which("node")
    if not node:
        return _result(False, so, "Node não foi encontrado; não foi possível agendar.")
    try:
        (blog / "logs").mkdir(parents=True, exist_ok=True)
        if so == "Darwin":
            return _instalar_darwin(blog, node, hh, mm, home)
        if so == "Windows":
            return _instalar_windows(blog, node, hh, mm, home)
        if so == "Linux":
            return _instalar_linux(blog, node, hh, mm)
    except OSError as exc:
        return _result(False, so, f"Não foi possível agendar: {exc}")
    return _result(
        False,
        so,
        f"Sistema {so} sem agendador suportado. Rode manualmente: node blog/generator/daily_publish.js",
    )


def remover(sistema=None, home=None):
    so = _sistema(sistema)
    try:
        if so == "Darwin":
            return _remover_darwin(home)
        if so == "Windows":
            return _remover_windows(home)
        if so == "Linux":
            return _remover_linux()
    except OSError as exc:
        return _result(False, so, f"Não foi possível remover o agendamento: {exc}")
    return _result(True, so, "Nenhum agendamento conhecido para este sistema")


def status(sistema=None, home=None):
    so = _sistema(sistema)
    if so == "Darwin":
        return _status_darwin(home)
    if so == "Windows":
        return _status_windows(home)
    if so == "Linux":
        return _status_linux()
    return _result(False, so, "Sistema sem agendador suportado")


if __name__ == "__main__":
    import json
    import sys

    acao = sys.argv[1] if len(sys.argv) > 1 else "status"
    funcoes = {"instalar": instalar, "remover": remover, "status": status}
    if acao not in funcoes:
        print("Uso: agendador.py [instalar|remover|status]")
        raise SystemExit(2)
    resultado = funcoes[acao]()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    raise SystemExit(0 if resultado["ok"] else 1)
