"""Permissao restrita de arquivo de segredo, multiplataforma.

No Windows, os.chmod() so alterna o atributo somente-leitura: stat() sempre
devolve 0o666 (gravavel) ou 0o444 (somente-leitura) para qualquer arquivo,
nunca os bits POSIX de grupo/outros. `chmod 600` e um no-op de seguranca real
la. Este modulo usa icacls para de fato restringir o acesso a conta do dono
no Windows, e cai no chmod POSIX normal em qualquer outro sistema.
"""
import os
import subprocess
import sys


def lock_down(path):
    """Restringe o arquivo ao dono. Levanta OSError se a chamada falhar."""
    path = str(path)
    if sys.platform == "win32":
        result = subprocess.run(
            ["icacls", path, "/inheritance:r", "/grant:r", f"{os.environ.get('USERNAME', '')}:F"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise OSError(f"icacls falhou ({result.returncode}): {(result.stderr or result.stdout).strip()}")
        return
    os.chmod(path, 0o600)


def is_locked_down(path):
    """Retorna (bool, detalhe) dizendo se o arquivo esta restrito ao dono.

    No Windows não comparamos nome de grupo (ex.: "Users"/"Usuários",
    "Everyone"/"Todos" mudam por idioma do SO — o curso é majoritariamente
    Windows em pt-BR). Em vez disso validamos a propriedade de verdade: a ACL
    não pode ter nenhuma entrada herdada da pasta pai, e o único principal
    com acesso tem que ser a conta atual — exatamente o que `lock_down()`
    produz via `/inheritance:r /grant:r`.
    """
    path_str = str(path)
    if sys.platform == "win32":
        result = subprocess.run(["icacls", path_str], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return False, f"não foi possível ler a ACL via icacls: {(result.stderr or result.stdout).strip()}"
        lines = result.stdout.splitlines()
        if lines:
            lines[0] = lines[0].replace(path_str, "", 1)
        aces = [line.strip() for line in lines if ":(" in line]
        if not aces:
            return False, "não foi possível interpretar a ACL retornada pelo icacls"
        expected = {os.environ.get("USERNAME", "").upper(), f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".upper()}
        for ace in aces:
            if "(I)" in ace:
                return False, (
                    f"ACL ainda tem entrada herdada da pasta pai ({ace}); execute novamente a etapa "
                    "para restringir com icacls"
                )
            principal = ace.split(":", 1)[0].strip().upper()
            if principal not in expected:
                return False, (
                    f"ACL concede acesso a outra conta além da sua ({ace}); execute novamente a etapa "
                    "para restringir com icacls"
                )
        return True, "ACL restrita à sua conta (icacls)"
    from pathlib import Path

    mode = oct(Path(path).stat().st_mode)[-3:]
    if mode != "600":
        return False, f"permissão {mode}; execute novamente a etapa para corrigir para 600"
    return True, "permissão 600"
