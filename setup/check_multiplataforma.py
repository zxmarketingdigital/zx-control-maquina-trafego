#!/usr/bin/env python3
"""Check estático: nenhum script do Setup 15 depende de algo que só existe no macOS.

Roda em qualquer sistema (inclusive no CI Windows) e sai 1 se achar um padrão proibido
fora dos pontos liberados. Uso: python setup/check_multiplataforma.py
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Arquivos que podem citar recursos do macOS porque só rodam nele (ou tratam o caso por SO).
LIBERADOS = {
    "launchagents/com.setup15.blog-daily.plist.template",
    "setup/agendador.py",
    "setup/setup_base_s15.py",
    "setup/check_multiplataforma.py",
    "tests/test_multiplataforma.py",
}

# Padrão liberado só num arquivo, porque lá ele já está protegido por checagem de SO.
LIBERADOS_POR_PADRAO = {
    ("skills/gerar-imagem/scripts/gerar.py", "sips só existe no macOS"),
}

EXTENSOES = {".py", ".js", ".mjs", ".sh", ".md", ".json", ".ts", ".tsx", ".html"}
IGNORAR_DIRS = {".git", "node_modules", "__pycache__", ".venv", "out", "dist"}

PADROES = [
    (re.compile(r"^\s*import fcntl\s*$"), "import fcntl sem guarda de SO (use msvcrt no Windows)"),
    (re.compile(r"\blaunchctl\b"), "launchctl só existe no macOS (use setup/agendador.py)"),
    (re.compile(r"\bsips\b"), "sips só existe no macOS"),
    (re.compile(r"/opt/homebrew"), "/opt/homebrew só existe no macOS"),
    (re.compile(r"ln -sf?\b"), "link simbólico exige Modo de Desenvolvedor no Windows"),
    (re.compile(r"os\.symlink\(|\.symlink_to\("), "link simbólico exige Modo de Desenvolvedor no Windows"),
    (re.compile(r"['\"]/tmp/"), "/tmp fixo não existe no Windows (use tempfile.gettempdir())"),
    (re.compile(r"'file://'\s*\+|\"file://\"\s*\+|`file://\$\{"), "file:// montado à mão quebra no Windows (use pathToFileURL)"),
    (re.compile(r"spawnSync\(\s*['\"]python3['\"]"), "python3 fixo no Node (use resolvePython())"),
    (re.compile(r"\[\s*['\"]python3['\"]\s*,"), "python3 fixo em subprocess (use sys.executable)"),
    (re.compile(r"/Applications/Google Chrome"), "Chrome fixo no caminho do macOS (resolver por SO)"),
    (re.compile(r"^\s*open\s+\S+\.(mp4|png|html)\b"), "comando open só existe no macOS"),
    (re.compile(r"source \./timings\.sh"), "build em bash não roda no PowerShell (use build.mjs)"),
]

# Trechos em que o padrão aparece só como alternativa dentro de um resolvedor por SO.
EXCECOES_LINHA = [
    re.compile(r"process\.platform === 'darwin'"),
    re.compile(r"platform\.system\(\) == ['\"]Darwin['\"]"),
    re.compile(r"os\.name == ['\"]nt['\"]"),
    re.compile(r"existe so no macOS|só no macOS|só existe no macOS|macOS em `/Applications`"),
]


def arquivos(incluir_liberados=False):
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in EXTENSOES:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(part in IGNORAR_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if rel.startswith("SPEC") or (rel in LIBERADOS and not incluir_liberados):
            continue
        yield rel, path


def varrer():
    achados = []
    for rel, path in arquivos():
        try:
            texto = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        linhas = texto.splitlines()
        for numero, linha in enumerate(linhas, 1):
            if any(exc.search(linha) for exc in EXCECOES_LINHA):
                continue
            for padrao, motivo in PADROES:
                if padrao.search(linha):
                    if (rel, motivo) in LIBERADOS_POR_PADRAO:
                        continue
                    # import fcntl dentro de bloco else (guardado por SO) é permitido.
                    if "import fcntl" in linha and numero > 1 and linha.startswith((" ", "\t")):
                        continue
                    achados.append((rel, numero, motivo, linha.strip()[:120]))
    return achados


def ast_39():
    erros = []
    for rel, path in arquivos(incluir_liberados=True):
        if not rel.endswith(".py"):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=rel, feature_version=(3, 9))
        except SyntaxError as erro:
            erros.append((rel, erro.lineno or 0, "sintaxe incompatível com Python 3.9", str(erro.msg)))
    return erros


def main():
    achados = varrer() + ast_39()
    if not achados:
        print("OK: nenhuma dependência exclusiva do macOS encontrada.")
        return 0
    print(f"FALHOU: {len(achados)} ponto(s) dependem de um sistema específico:")
    for rel, numero, motivo, trecho in achados:
        print(f"  {rel}:{numero}: {motivo}\n      {trecho}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
