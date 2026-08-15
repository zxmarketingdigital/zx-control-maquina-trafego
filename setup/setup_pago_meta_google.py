#!/usr/bin/env python3
"""Setup 15 — Etapa 4: tráfego pago Meta e Google Ads.

As conexões de plataforma são deliberadamente stubs. A autenticação real ocorre
na conversa do Claude, via MCP oficial (ou pelo fallback de System User Token),
e este script apenas recebe e grava o token que já foi obtido. Nenhuma campanha
é publicada por este arquivo.
"""

import argparse
import datetime as dt
import filecmp
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / "skills"
SKILLS_DST = Path.home() / ".claude" / "skills"
BACKUP_BASE = SKILLS_DST
CONFIG_DIR = Path.home() / ".operacao-ia" / "config"
META_ENV = CONFIG_DIR / "meta.env"
META_PROFILE = CONFIG_DIR / "meta_perfil.json"
GOOGLE_ENV = CONFIG_DIR / "google_ads.env"
GOOGLE_PROFILE = CONFIG_DIR / "google_perfil.json"

META_SKILLS = ("meta-metrics-fetcher", "meta-performance-analyzer")
GOOGLE_SKILLS = ("google-metrics-fetcher", "google-performance-analyzer")
META_TOKEN_NAME = "META_ACCESS_TOKEN"
GOOGLE_TOKEN_NAME = "GOOGLE_ADS_ACCESS_TOKEN"
META_MCP_PLACEHOLDER = "<META_TOKEN_OBTIDO_VIA_MCP>"
META_SYSTEM_USER_PLACEHOLDER = "<META_TOKEN_OBTIDO_VIA_SYSTEM_USER>"
GOOGLE_PLACEHOLDER = "<GOOGLE_ADS_TOKEN_OBTIDO_VIA_CONEXAO>"


def mascarar(valor: str) -> str:
    """Mascara segredos sem revelar valores curtos por inteiro."""
    valor = str(valor)
    if len(valor) <= 8:
        return "••••"
    return valor[:4] + "…" + valor[-4:]


def ler_env(path: Path) -> dict[str, str]:
    """Lê um .env simples, sem expandir variáveis nem executar conteúdo."""
    if not path.exists():
        return {}
    valores = {}
    try:
        linhas = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return valores
    for linha in linhas:
        texto = linha.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            continue
        nome, valor = texto.split("=", 1)
        nome = nome.strip()
        if nome.startswith("export "):
            nome = nome[7:].strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[nome] = valor
    return valores


def atualizar_env(path: Path, atualizacoes: dict[str, str]) -> bool:
    """Atualiza somente as chaves indicadas e protege o arquivo com chmod 600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        linhas = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    except OSError:
        linhas = []

    encontrados = set()
    novas_linhas = []
    for linha in linhas:
        texto = linha.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            novas_linhas.append(linha)
            continue
        nome = texto.split("=", 1)[0].strip()
        if nome.startswith("export "):
            nome = nome[7:].strip()
        if nome in atualizacoes:
            novas_linhas.append(f"{nome}={atualizacoes[nome]}")
            encontrados.add(nome)
        else:
            novas_linhas.append(linha)

    for nome, valor in atualizacoes.items():
        if nome not in encontrados:
            novas_linhas.append(f"{nome}={valor}")

    try:
        path.write_text("\n".join(novas_linhas).rstrip("\n") + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
    except OSError as exc:
        print(f"❌ Não foi possível gravar {path.name}: {exc}")
        return False
    return True


def proteger(path: Path) -> None:
    if path.exists():
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def resposta(prompt: str, padrao: str = "") -> str:
    try:
        valor = input(prompt)
    except (EOFError, KeyboardInterrupt):
        return padrao
    valor = valor.strip()
    return valor if valor else padrao


def foi_pulado(valor: str) -> bool:
    return valor.strip().lower() in {"pular", "skip", "não", "nao", "n", "no"}


def dirs_equal(a: Path, b: Path) -> bool:
    """True se as árvores de diretórios são idênticas em conteúdo."""
    if not (a.exists() and b.exists() and a.is_dir() and b.is_dir()):
        return False
    cmp = filecmp.dircmp(str(a), str(b))
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(dirs_equal(a / sub, b / sub) for sub in cmp.common_dirs)


def proximo_backup(slug: str, timestamp: str) -> Path:
    destino = BACKUP_BASE / f".s15-backup-{slug}-{timestamp}"
    contador = 2
    while destino.exists():
        destino = BACKUP_BASE / f".s15-backup-{slug}-{timestamp}-{contador}"
        contador += 1
    return destino


def instalar_skill(slug: str) -> str:
    """Instala uma skill, fazendo backup antes de substituir uma versão customizada."""
    src = SKILLS_SRC / slug
    dst = SKILLS_DST / slug
    if not src.exists() or not src.is_dir():
        print(f"⚠️ Skill de origem ausente no repo; instalação adiada: {slug}")
        return "missing"

    try:
        SKILLS_DST.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copytree(src, dst)
            print(f"✅ Skill instalada: {slug}")
            return "installed"
        if dirs_equal(src, dst):
            print(f"⏭ Skill já idêntica; mantida: {slug}")
            return "skipped"

        backup = proximo_backup(slug, dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
        shutil.copytree(dst, backup)
        shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"🔄 Skill atualizada com backup: {slug}")
        print(f"   Backup: {backup}")
        return "updated"
    except OSError as exc:
        print(f"⚠️ Não foi possível instalar a skill {slug}: {exc}")
        return "error"


def token_valido(valor: str, placeholders: tuple[str, ...] = ()) -> bool:
    # O prompt oferece 'pular' como resposta: sem esta guarda a palavra vira o
    # token e o .env fica STATUS=connected sem credencial nenhuma, fazendo a
    # auditoria dizer ao aluno que a conta está conectada quando não está.
    valor = (valor or "").strip()
    if not valor or foi_pulado(valor):
        return False
    return valor not in placeholders and not valor.startswith("<")


def conectar_via_mcp(token: str = "") -> str:
    """Stub do MCP oficial da Meta.

    O Claude realiza o fluxo OAuth/MCP na conversa e passa o token já obtido
    para esta função. Sem token recebido, o retorno explícito é apenas um
    placeholder para que a integração real nunca seja simulada pelo script.
    """
    return token.strip() if token and token.strip() else META_MCP_PLACEHOLDER


def conectar_via_system_user_token(token: str = "") -> str:
    """Stub do fallback de System User Token da Meta.

    O token deve ser obtido e validado pelo Claude fora deste script. A função
    somente devolve o valor recebido ou um placeholder não utilizável.
    """
    return token.strip() if token and token.strip() else META_SYSTEM_USER_PLACEHOLDER


def conectar_google_ads(token: str = "") -> str:
    """Stub da conexão Google Ads.

    A autenticação real é conduzida pelo Claude. Este script apenas grava o
    token de acesso que já tiver sido obtido; sem entrada, retorna placeholder.
    """
    return token.strip() if token and token.strip() else GOOGLE_PLACEHOLDER


def carregar_perfil(path: Path = META_PROFILE) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        perfil = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(perfil, dict):
        return None
    objetivos = perfil.get("objectives", perfil.get("objetivos"))
    metricas = perfil.get("metrics", perfil.get("metricas", perfil.get("kpis")))
    kpi = perfil.get("primary_kpi", perfil.get("kpi_primario"))
    return perfil if objetivos and metricas and kpi else None


def salvar_perfil(perfil: dict, path: Path = META_PROFILE) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(perfil, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.chmod(path, 0o600)
        return True
    except OSError as exc:
        if path == META_PROFILE:
            nome = "meta_perfil.json"
        else:
            nome = path.name
        print(f"❌ Não foi possível gravar {nome}: {exc}")
        return False


def ler_metricas() -> list[dict] | None:
    texto = resposta(
        "Métricas e metas numéricas, separadas por vírgula (ex.: cpa=80, roas=3): "
    )
    if not texto or foi_pulado(texto):
        return None
    metricas = []
    for item in texto.split(","):
        item = item.strip()
        if "=" in item:
            nome, alvo = item.split("=", 1)
        elif ":" in item:
            nome, alvo = item.split(":", 1)
        else:
            print("⚠️ Cada métrica precisa ter uma meta numérica, no formato nome=valor.")
            return None
        try:
            numero = float(alvo.strip())
        except ValueError:
            print("⚠️ Meta de métrica inválida; o perfil não foi substituído.")
            return None
        if not nome.strip():
            return None
        metricas.append({"name": nome.strip(), "target": numero})
    return metricas or None


def criar_perfil_interativo(path: Path = META_PROFILE, rotulo: str = "Meta") -> bool:
    print(f"\nVamos registrar o perfil de objetivos e KPIs da conta {rotulo}.")
    objetivos_texto = resposta(
        "Objetivos de campanha (multi-seleção, separados por vírgula; ou 'pular'): "
    )
    if not objetivos_texto or foi_pulado(objetivos_texto):
        print(f"⚠️ Perfil {rotulo} deixado para depois; nenhum objetivo foi inventado.")
        return False
    objetivos = [item.strip() for item in objetivos_texto.split(",") if item.strip()]
    metricas = ler_metricas()
    if not metricas:
        print(f"⚠️ Perfil {rotulo} deixado para depois; as métricas precisam de metas numéricas.")
        return False

    kpi_texto = resposta(
        "KPI primário (nome; Enter usa a primeira métrica; ou 'pular'): "
    )
    if foi_pulado(kpi_texto):
        print(f"⚠️ Perfil {rotulo} deixado para depois.")
        return False
    if not kpi_texto:
        kpi = metricas[0]
    else:
        nome_kpi = kpi_texto
        correspondente = next(
            (metrica for metrica in metricas if metrica["name"].lower() == nome_kpi.lower()),
            None,
        )
        if correspondente:
            kpi = correspondente
        else:
            alvo = resposta(f"Meta numérica de {nome_kpi}: ")
            try:
                kpi = {"name": nome_kpi, "target": float(alvo)}
            except ValueError:
                print("⚠️ Meta do KPI primário inválida; o perfil não foi criado.")
                return False

    perfil = {
        "version": 1,
        "objectives": objetivos,
        "metrics": metricas,
        "primary_kpi": {"name": kpi["name"], "target": kpi["target"]},
        "accounts": [],
        "scale_at": {},
        "kill_at": {},
    }
    if salvar_perfil(perfil, path):
        print(f"✅ {path.name} criado com objetivos e metas numéricas.")
        return True
    return False


def criar_perfil_google_interativo() -> bool:
    return criar_perfil_interativo(GOOGLE_PROFILE, "Google Ads")


def instalar_skills_meta() -> None:
    for slug in META_SKILLS:
        instalar_skill(slug)


def instalar_skills_google() -> None:
    for slug in GOOGLE_SKILLS:
        instalar_skill(slug)


def executar_meta() -> None:
    valores = ler_env(META_ENV)
    token_existente = valores.get(META_TOKEN_NAME, "").strip()
    perfil_existente = carregar_perfil()

    if token_valido(token_existente, (META_MCP_PLACEHOLDER, META_SYSTEM_USER_PLACEHOLDER)) and perfil_existente:
        proteger(META_ENV)
        proteger(META_PROFILE)
        print(f"✅ Instalação Meta válida reaproveitada (token {mascarar(token_existente)}).")
        instalar_skills_meta()
        return

    if token_valido(token_existente, (META_MCP_PLACEHOLDER, META_SYSTEM_USER_PLACEHOLDER)):
        proteger(META_ENV)
        print(f"✅ Token Meta existente reaproveitado: {mascarar(token_existente)}")
    else:
        print("\nMeta Ads: o Claude tentará autenticar pelo MCP oficial.")
        print("Se o MCP falhar, o Claude usará o fallback de System User Token.")
        escolha = resposta("Conectar Meta agora? [sim/pular]: ", "pular").lower()
        if foi_pulado(escolha):
            print("⏭ Meta Ads pulado; nenhuma credencial foi solicitada.")
            metodo = None
        else:
            metodo = resposta("Método [mcp/system_user_token]: ", "mcp").lower()
        if metodo is not None:
            token_recebido = resposta(
                "Token já obtido pelo Claude (ou 'pular'; ele não será exibido): "
            )
            if metodo in {"system_user_token", "system", "system-user-token"}:
                token = conectar_via_system_user_token(token_recebido)
                origem = "system_user_token"
            else:
                token = conectar_via_mcp(token_recebido)
                origem = "mcp"
            if token_valido(token, (META_MCP_PLACEHOLDER, META_SYSTEM_USER_PLACEHOLDER)):
                if atualizar_env(META_ENV, {META_TOKEN_NAME: token, "TOKEN_SOURCE": origem, "STATUS": "connected"}):
                    print(f"✅ Meta conectado; token salvo de forma protegida: {mascarar(token)}")
            else:
                print("⚠️ Nenhum token real recebido; a conexão Meta ficou pendente.")

    if not perfil_existente:
        criar_perfil_interativo()
    else:
        proteger(META_PROFILE)
        print("✅ meta_perfil.json existente e válido foi reaproveitado.")
    instalar_skills_meta()


def normalizar_customer_id(valor: str) -> str:
    """Aceita customer IDs com hífens e devolve somente os dez dígitos."""
    return "".join(caractere for caractere in (valor or "") if caractere.isdigit())


def customer_id_valido(valor: str) -> bool:
    """Valida o valor BRUTO, não o normalizado.

    Validar depois de remover não-dígitos faz '1234567890x' virar '1234567890'
    e ser aceito — um erro de digitação seria gravado como conta boa e o aluno
    operaria na conta errada sem nunca ver um aviso.
    """
    bruto = (valor or "").strip()
    return bool(re.fullmatch(r"[0-9]{10}|[0-9]{3}-[0-9]{3}-[0-9]{4}", bruto))


def credencial_google(valores: dict[str, str]) -> str:
    """Devolve a credencial que de fato AUTENTICA o acesso à conta do aluno.

    O developer token NÃO entra aqui: ele identifica a aplicação perante a API,
    não o dono da conta — no fluxo do produto quem o detém é o Pipedream, e o
    aluno só faz OAuth. Aceitá-lo como credencial fazia o setup gravar
    STATUS=connected e instalar as skills sem nenhuma autenticação real.
    """
    acesso = valores.get(GOOGLE_TOKEN_NAME, "").strip()
    if token_valido(acesso, (GOOGLE_PLACEHOLDER,)):
        return acesso
    refresh = valores.get("GOOGLE_ADS_REFRESH_TOKEN", "").strip()
    if token_valido(refresh, (GOOGLE_PLACEHOLDER,)):
        return refresh
    return ""


def executar_google() -> None:
    valores = ler_env(GOOGLE_ENV)
    acesso_existente = valores.get(GOOGLE_TOKEN_NAME, "").strip()
    token_existente = credencial_google(valores)
    customer_existente = normalizar_customer_id(valores.get("GOOGLE_ADS_CUSTOMER_ID", ""))
    perfil_existente = carregar_perfil(GOOGLE_PROFILE)

    instalacao_valida = (
        token_valido(token_existente, (GOOGLE_PLACEHOLDER,))
        and customer_id_valido(customer_existente)
        and perfil_existente
    )
    if instalacao_valida:
        proteger(GOOGLE_ENV)
        proteger(GOOGLE_PROFILE)
        print(
            f"✅ Instalação Google Ads válida reaproveitada "
            f"(credencial {mascarar(token_existente)}; conta {mascarar(customer_existente)})."
        )
        instalar_skills_google()
        return

    if token_valido(token_existente, (GOOGLE_PLACEHOLDER,)):
        proteger(GOOGLE_ENV)
        print(f"✅ Credencial Google Ads existente reaproveitada: {mascarar(token_existente)}")

    # Daqui para baixo cada recusa SAI da função. O aluno que pulou, digitou um
    # ID inválido ou não trouxe credencial não responde questionário de perfil
    # nem recebe as skills de Google instaladas: skill sem conta para operar é
    # promessa vazia na área de membros, e instalar assim contradiz o 'pular'.
    escolha = resposta("Conectar Google Ads agora? [sim/pular]: ", "pular").lower()
    if foi_pulado(escolha):
        atualizar_env(GOOGLE_ENV, {"STATUS": "skipped"})
        print("⏭ Google Ads pulado; a conexão continua opcional.")
        return

    customer_informado = resposta(
        "Customer ID da conta Google Ads (10 dígitos, hífens aceitos): "
    )
    # Valida o que o aluno DIGITOU; normaliza só depois de aprovar.
    if not customer_id_valido(customer_informado):
        atualizar_env(GOOGLE_ENV, {"STATUS": "pending"})
        print(
            "⚠️ Customer ID inválido. Informe os 10 dígitos da conta ao conectar o Google Ads "
            "na Etapa 4; nenhuma conta padrão será usada."
        )
        return
    customer_id = normalizar_customer_id(customer_informado)

    login_informado = resposta(
        "Login customer ID da MCC (opcional; Enter se a conta não estiver sob MCC): "
    )
    if login_informado and not customer_id_valido(login_informado):
        atualizar_env(GOOGLE_ENV, {"STATUS": "pending"})
        print("⚠️ Login customer ID inválido; use 10 dígitos ou deixe em branco.")
        return
    login_id = normalizar_customer_id(login_informado) if login_informado else ""

    token_recebido = resposta(
        "Access token já obtido pelo Claude (ou 'pular'; ele não será exibido): "
    )
    token = conectar_google_ads(token_recebido) if token_recebido else acesso_existente
    refresh_token = resposta(
        "Refresh token Google Ads já obtido pelo Claude (opcional neste stub): "
    )
    acesso_ok = token_valido(token, (GOOGLE_PLACEHOLDER,))
    refresh_ok = token_valido(refresh_token, (GOOGLE_PLACEHOLDER,))
    # Refresh token sozinho TAMBÉM conecta: ele renova o access token. Exigir
    # access aqui contradizia credencial_google, que já o aceita, e deixava
    # pendente um aluno que na prática está conectado.
    if not acesso_ok and not refresh_ok:
        atualizar_env(GOOGLE_ENV, {"STATUS": "pending"})
        print("⚠️ Nenhuma credencial real recebida; Google Ads ficou pendente.")
        return

    atualizacoes = {"GOOGLE_ADS_CUSTOMER_ID": customer_id, "STATUS": "connected"}
    if acesso_ok:
        atualizacoes[GOOGLE_TOKEN_NAME] = token
    if refresh_ok:
        atualizacoes["GOOGLE_ADS_REFRESH_TOKEN"] = refresh_token
    if login_id:
        atualizacoes["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] = login_id
    if not atualizar_env(GOOGLE_ENV, atualizacoes):
        # Sem gravar o .env não há conexão nenhuma: o próximo passo leria o
        # arquivo antigo e operaria com a conta errada.
        print("⚠️ Não foi possível gravar google_ads.env; Google Ads ficou pendente.")
        return
    exibido = mascarar(token) if acesso_ok else "via refresh token"
    print(f"✅ Google Ads conectado; credenciais salvas de forma protegida: acesso {exibido}")

    if not perfil_existente:
        criar_perfil_google_interativo()
    else:
        proteger(GOOGLE_PROFILE)
        print("✅ google_perfil.json existente e válido foi reaproveitado.")
    instalar_skills_google()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Configura Meta Ads e Google Ads do Setup 15")
    parser.add_argument("--skip-meta", action="store_true", help="pula somente a sub-etapa Meta")
    parser.add_argument("--skip-google", action="store_true", help="pula somente a sub-etapa Google Ads")
    args = parser.parse_args(argv)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    print("\n[████░░░░░░] Etapa 4 de 8 — Tráfego pago: Meta + Google")
    if args.skip_meta:
        print("⏭ Meta Ads pulado por opção explícita.")
    else:
        executar_meta()
    if args.skip_google:
        print("⏭ Google Ads pulado por opção explícita.")
    else:
        executar_google()

    print(
        "\ncpa/roas vêm do PIXEL, que pode contar PIX gerado e ainda não pago — sempre cruzar "
        "com venda paga real antes de cortar budget de qualquer campanha."
    )
    print("✅ Etapa 4 concluída; nenhuma campanha foi publicada ou ativada por este script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
