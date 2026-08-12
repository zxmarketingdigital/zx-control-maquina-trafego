#!/usr/bin/env python3
"""Setup 15 — Etapa 1: coleta e validação de credenciais."""
import argparse
import getpass
import json
import os
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".operacao-ia" / "config"

CREDENTIALS = {
    "gemini": ("gemini.env", "GEMINI_API_KEY"),
    "meta": ("meta.env", "META_ACCESS_TOKEN"),
    "google_ads": ("google_ads.env", "GOOGLE_ADS_DEVELOPER_TOKEN"),
    "cloudflare": ("cloudflare.env", "CLOUDFLARE_API_TOKEN"),
}


def mascarar(valor):
    if len(valor) <= 8:
        return "••••"
    return valor[:4] + "…" + valor[-4:]


def ler_env(path):
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


def atualizar_env(path, atualizacoes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not preservar_se_existente(path):
        return False
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
    except OSError:
        return False
    return True


def proteger_arquivo(path):
    if path.exists():
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def preservar_se_existente(path):
    """Antes de um arquivo existente ser sobrescrito, guarda uma cópia do
    estado original — só na primeira vez (nunca sobrescreve um backup já feito),
    para que setup_uninstall.py possa restaurar em vez de apagar.

    Retorna True se não havia nada a preservar ou se a preservação teve
    sucesso (agora ou antes). Retorna False se o arquivo existe e a cópia
    de segurança falhou — nesse caso o chamador não deve prosseguir com a
    sobrescrita, para não perder a versão anterior sem backup nenhum."""
    if not path.exists():
        return True
    ja_tem_backup = list(path.parent.glob(f".s15-backup-{path.name}-*"))
    if ja_tem_backup:
        return True
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    backup_path = path.parent / f".s15-backup-{path.name}-{timestamp}"
    tmp_path = path.parent / f".s15-backup-{path.name}-{timestamp}.tmp"
    try:
        shutil.copy2(path, tmp_path)
        os.chmod(tmp_path, 0o600)
        tmp_path.rename(backup_path)
        return True
    except OSError:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        return False


def validar_gemini(key):
    """Confere a chave consultando a lista de modelos da API Gemini."""
    url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + key
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status < 200 or response.status >= 300:
                return False
            json.loads(response.read().decode("utf-8"))
            return True
    except Exception:
        return False


def validar_opcional(valor):
    return bool(valor and valor.strip())


def ler_resposta(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def ler_segredo(prompt):
    try:
        return getpass.getpass(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def caminho_da(identificador):
    nome, _ = CREDENTIALS[identificador]
    return CONFIG_DIR / nome


def coletar_gemini():
    path = caminho_da("gemini")
    chave_nome = CREDENTIALS["gemini"][1]
    existente = ler_env(path).get(chave_nome, "").strip()

    if existente:
        print("\nGEMINI_API_KEY já encontrada: " + mascarar(existente))
        escolha = ler_resposta("Digite manter ou substituir: ").lower()
        if escolha not in ("s", "sim", "substituir", "trocar", "y", "yes"):
            print("Validando a chave existente...")
            if validar_gemini(existente):
                proteger_arquivo(path)
                print("✅ Gemini mantido e validado: " + mascarar(existente))
                return True
            print("❌ A chave existente não foi validada. Será necessário informar outra.")
        else:
            print("Informe a nova chave do Gemini.")

    print("\nA chave do Gemini é a única credencial obrigatória e funciona no nível gratuito.")
    print("Crie uma chave no Google AI Studio: entre com sua conta Google, abra a área de API keys e gere uma chave gratuita.")
    while True:
        chave = ler_segredo("GEMINI_API_KEY (não digite 'pular', a digitação fica oculta): ")
        if not chave or chave.lower() == "pular":
            print("❌ A chave do Gemini é obrigatória para continuar.")
            continue
        print("Validando a chave do Gemini...")
        if not validar_gemini(chave):
            print("❌ A chave não foi validada. Confira a chave e tente novamente.")
            continue
        if not atualizar_env(path, {chave_nome: chave, "STATUS": "configurado"}):
            print("❌ Não foi possível gravar a configuração do Gemini com permissão restrita.")
            return False
        print("✅ Gemini validado e salvo: " + mascarar(chave))
        return True


def coletar_opcional(identificador, titulo, explicacao, instrucao):
    filename, chave_nome = CREDENTIALS[identificador]
    path = CONFIG_DIR / filename
    existente = ler_env(path).get(chave_nome, "").strip()

    print(f"\n{titulo}")
    print(explicacao)
    if existente:
        print(f"Já configurado: {mascarar(existente)}")
        escolha = ler_resposta("Digite manter, substituir ou pular: ").lower()
        if escolha not in ("s", "sim", "substituir", "trocar", "y", "yes"):
            print("✅ Credencial opcional mantida: " + mascarar(existente))
            proteger_arquivo(path)
            return True
        valor = ler_segredo(instrucao + " (ou 'pular', digitação oculta): ")
        if not valor or valor.lower() == "pular":
            print("⏭️  Integração deixada para depois; a credencial existente foi preservada.")
            return True
    else:
        valor = ler_segredo(instrucao + " (ou 'pular', digitação oculta): ")
        if not valor or valor.lower() == "pular":
            if atualizar_env(path, {"STATUS": "pulado"}):
                print("⏭️  Integração opcional pulada.")
            else:
                print("⚠️  Não foi possível registrar a opção pulada.")
            return True

    if not validar_opcional(valor):
        print("⚠️  Credencial vazia; integração deixada para depois.")
        return True
    if not atualizar_env(path, {chave_nome: valor, "STATUS": "configurado"}):
        print("⚠️  Não foi possível salvar esta credencial com permissão restrita.")
        return True
    print("✅ Credencial opcional salva: " + mascarar(valor))
    print("   A validação de conexão da plataforma será feita na etapa de integração.")
    return True


def mostrar_status():
    print("Configuração atual das credenciais (valores mascarados):")
    for identificador, (filename, chave_nome) in CREDENTIALS.items():
        path = CONFIG_DIR / filename
        valores = ler_env(path)
        valor = valores.get(chave_nome, "").strip()
        if valor:
            print(f"  {identificador}: configurada ({mascarar(valor)})")
        elif valores.get("STATUS") == "pulado":
            print(f"  {identificador}: opcional — pulada")
        else:
            print(f"  {identificador}: não configurada")
        proteger_arquivo(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Configura as credenciais do Setup 15")
    parser.add_argument("--status", action="store_true", help="lista somente o estado atual")
    args = parser.parse_args(argv)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if args.status:
        mostrar_status()
        return 0

    print("\n🔐 Etapa 1 — Chaves e contas")
    print("A chave do Gemini é obrigatória. Meta Ads, Google Ads e Cloudflare são opcionais e podem ser puladas.")
    try:
        gemini_ok = coletar_gemini()
        coletar_opcional(
            "meta",
            "Meta Ads — integração opcional",
            "O token permite ler dados da conta de anúncios. Ele pode ser obtido no Business Manager, por OAuth ou por um usuário do sistema.",
            "Cole o token de acesso da Meta",
        )
        coletar_opcional(
            "google_ads",
            "Google Ads — integração opcional",
            "O token de desenvolvedor é solicitado no Centro de API do Google Ads; a autenticação da conta será concluída quando a integração for escolhida.",
            "Cole o token de desenvolvedor do Google Ads",
        )
        coletar_opcional(
            "cloudflare",
            "Cloudflare — integração opcional",
            "O token permite publicar o blog no Cloudflare Pages. Crie-o no painel da Cloudflare com apenas as permissões necessárias.",
            "Cole o token de API da Cloudflare",
        )
    except KeyboardInterrupt:
        print("\n❌ Entrada interrompida. Nenhuma credencial foi exibida.")
        return 1

    if not gemini_ok:
        print("\n❌ A Etapa 1 não foi concluída porque o Gemini não foi validado.")
        return 1
    print("\n✅ Etapa 1 concluída. O Gemini está configurado; integrações opcionais podem ser conectadas depois.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
