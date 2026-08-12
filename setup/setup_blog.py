#!/usr/bin/env python3
"""Configura o blog SEO e o agente diário do Setup 15."""

import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "blog"
CONFIG_EXAMPLE = BLOG_DIR / "generator" / "config.example.json"
CONFIG_PATH = BLOG_DIR / "config.json"
QUEUE_PATH = BLOG_DIR / "queue.json"
DAILY_PUBLISH = BLOG_DIR / "generator" / "daily_publish.js"
PLIST_TEMPLATE = ROOT / "launchagents" / "com.setup15.blog-daily.plist.template"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.setup15.blog-daily.plist"


YES = {"s", "sim", "y", "yes", "1"}
NO = {"n", "nao", "não", "no", "0"}


def ask_yes_no(prompt, default=True):
    suffix = " [S/n] " if default else " [s/N] "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in YES:
            return True
        if answer in NO:
            return False
        print("Responda com sim ou não.")


def ask_text(prompt, default=None, required=True):
    suffix = ""
    if default:
        suffix = f" [{default}]"
    while True:
        value = input(prompt + suffix + ": ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("Esse campo é necessário para continuar.")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Não foi possível ler {path.name}: {exc}")
        return None


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _product_key(name, index):
    key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return key or f"produto-{index}"


def collect_real_products():
    print("\nAgora informe o(s) produto(s) reais do projeto: nome, preço e link da oferta.")
    print("Pressione Enter no nome para pular esta etapa.")
    products = {}
    index = 1
    while True:
        name = ask_text(
            "Nome do produto real (Enter para pular)",
            required=False,
        )
        if not name:
            break
        price = ask_text("Preço do produto")
        offer_link = ask_text("Link da oferta")
        key = _product_key(name, index)
        while key in products:
            index += 1
            key = _product_key(name, index)
        products[key] = {
            "name": name,
            "price": price,
            "lp": offer_link,
            "checkout": offer_link,
            "pitch": "",
            "cta": "Conhecer o produto",
        }
        index += 1
        if not ask_yes_no("Quer adicionar outro produto real?", default=False):
            break

    if products:
        return products
    print(
        "⚠️ Nenhum produto real foi informado. O artigo usaria dados de exemplo; "
        "a publicação ficará bloqueada até você preencher essa informação."
    )
    return None


def has_real_products(config):
    products = config.get("products") if isinstance(config, dict) else None
    if not isinstance(products, dict) or not products:
        return False
    placeholders = (
        "r$00,00",
        "seu-dominio.com.br",
        "seu produto aqui",
        "outro produto seu",
    )
    for product in products.values():
        if not isinstance(product, dict):
            return False
        name = str(product.get("name", "")).strip()
        price = str(product.get("price", "")).strip()
        links = (str(product.get("lp", "")).strip(), str(product.get("checkout", "")).strip())
        if not name or not price or not any(links):
            return False
        values = (name.lower(), price.lower(), *(link.lower() for link in links))
        if any(marker in value for value in values for marker in placeholders):
            return False
    return True


def collect_site_config(current=None):
    current = current or {}
    current_site = current.get("site", {})
    if not isinstance(current_site, dict):
        current_site = {}

    print("\nVamos configurar o blog para o seu projeto.")
    name = ask_text(
        "Nome do site/produto",
        current_site.get("name"),
    )
    base_url = ask_text(
        "baseUrl do domínio onde o blog será publicado",
        current_site.get("baseUrl", "https://seu-dominio-a-definir.example"),
    )
    nicho = ask_text(
        "Nicho ou tema do blog (texto livre)",
        current_site.get("nicho"),
    )

    if not CONFIG_EXAMPLE.is_file():
        print(f"Arquivo de referência não encontrado: {CONFIG_EXAMPLE}")
        return None

    example = load_json(CONFIG_EXAMPLE)
    if not isinstance(example, dict):
        print("O config.example.json não contém um objeto JSON válido.")
        return None

    site = example.setdefault("site", {})
    if not isinstance(site, dict):
        site = {}
        example["site"] = site
    site["name"] = name
    site["baseUrl"] = base_url
    site["nicho"] = nicho
    products = collect_real_products()
    if products is not None:
        example["products"] = products
    return example


def ensure_config():
    if CONFIG_PATH.exists():
        print(f"Já existe {CONFIG_PATH.relative_to(ROOT)}.")
        if ask_yes_no("Quer reconfigurar o site, domínio e nicho?", default=False):
            config = collect_site_config(load_json(CONFIG_PATH) or {})
            if config is None:
                return None
            try:
                save_json(CONFIG_PATH, config)
            except OSError as exc:
                print(f"Não foi possível salvar a configuração: {exc}")
                return None
            print(f"Configuração atualizada em {CONFIG_PATH.relative_to(ROOT)}.")
            return config

        config = load_json(CONFIG_PATH)
        if not isinstance(config, dict):
            print("A configuração existente não pode ser usada sem reconfiguração.")
            return None
        site = config.get("site", {})
        if not isinstance(site, dict) or not site.get("nicho"):
            print("A configuração existente não tem site.nicho; reconfigure para continuar.")
            return None
        if not has_real_products(config):
            products = collect_real_products()
            if products is not None:
                config["products"] = products
                try:
                    save_json(CONFIG_PATH, config)
                except OSError as exc:
                    print(f"Não foi possível salvar os produtos reais: {exc}")
                    return None
                print(f"Produtos reais atualizados em {CONFIG_PATH.relative_to(ROOT)}.")
        print("Configuração existente preservada.")
        return config

    config = collect_site_config()
    if config is None:
        return None
    try:
        save_json(CONFIG_PATH, config)
    except OSError as exc:
        print(f"Não foi possível salvar a configuração: {exc}")
        return None
    print(f"Configuração criada em {CONFIG_PATH.relative_to(ROOT)}.")
    return config


def redact_output(text):
    if not text:
        return ""
    result = str(text)
    for key, value in os.environ.items():
        if value and len(value) >= 8 and any(
            marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")
        ):
            result = result.replace(value, value[:4] + "…" + value[-4:])
    result = result.replace(str(ROOT), "<repo>")
    result = result.replace(str(Path.home()), "~")
    return result


def run_command(args):
    try:
        return subprocess.run(
            list(args),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"Não foi possível executar {' '.join(args)}: {exc}")
        return None


def show_command_output(result):
    if result is None:
        return ""
    stdout = redact_output(result.stdout or "")
    stderr = redact_output(result.stderr or "")
    output = "\n".join(part for part in (stdout, stderr) if part.strip())
    if output:
        print(output.rstrip())
    else:
        print("(o comando não produziu saída)")
    return "\n".join(part for part in (stdout, stderr) if part)


def queue_items(queue):
    if isinstance(queue, list):
        return queue
    if isinstance(queue, dict):
        for key in ("keywords", "queue", "items"):
            value = queue.get(key)
            if isinstance(value, list):
                return value
    return []


def show_queue_summary():
    queue = load_json(QUEUE_PATH)
    items = queue_items(queue)
    if not items:
        print("Não foi possível identificar keywords em blog/queue.json.")
        return False

    pillars = [item for item in items if isinstance(item, dict) and str(item.get("tier", "")).lower() == "pillar"]
    print(f"Keywords disponíveis na fila: {len(items)}")
    print("Títulos tier=pillar:")
    if pillars:
        for item in pillars:
            title = item.get("title") or item.get("titulo") or item.get("keyword") or item.get("slug")
            print(f"  - {title}")
    else:
        print("  (nenhum pillar encontrado)")
    return True


def ensure_queue(config):
    site = config.get("site", {})
    nicho = site.get("nicho") if isinstance(site, dict) else None
    if not nicho:
        print("O campo site.nicho não está configurado.")
        return False

    regenerate = True
    if QUEUE_PATH.exists():
        print(f"Já existe {QUEUE_PATH.relative_to(ROOT)}.")
        regenerate = ask_yes_no("Quer gerar novamente a fila para o nicho configurado?", default=False)

    if regenerate:
        print(f'Gerando a fila para o nicho: {nicho}')
        python_bin = "python3" if shutil.which("python3") else sys.executable
        result = run_command([
            python_bin,
            "blog/agente/gerar_fila.py",
            nicho,
        ])
        output = show_command_output(result)
        if result is None or result.returncode != 0:
            print("A geração da fila falhou; nenhum artigo será iniciado nesta execução.")
            return False
        if output:
            print("Fila gerada pelo agente.")

    return show_queue_summary()


def infer_check(text, kind):
    lower = text.lower()
    negative = re.search(r"(falh|fail|erro|reprov|não passou|nao passou|blocked|bloqueado)", lower)
    if negative:
        return "reprovado ou não identificado"

    if kind == "safety":
        if re.search(r"safety[^\n]*(aprov|pass|ok|approved|passed)|(?:aprov|pass)[^\n]*safety", lower):
            return "aprovado"
    if kind == "validate":
        if "24/24" in lower or re.search(r"validat[^\n]*(aprov|pass|ok|approved|passed)", lower):
            return "passou"
    return "não identificado na saída"


def html_paths(text):
    paths = re.findall(r"(?i)[A-Za-z0-9_./~:-]+\.html", text)
    result = []
    for path in paths:
        path = redact_output(path).rstrip(".,;)")
        if path not in result:
            result.append(path)
    return result


def build_local_only():
    node_bin = shutil.which("node")
    if not node_bin:
        print("Node não foi encontrado; o BUILD local não pôde ser executado.")
        return
    print("\nBUILD local do blog (sem publicação):")
    result = run_command([node_bin, "blog/generator/build.js"])
    show_command_output(result)
    if result is None or result.returncode != 0:
        print("O BUILD local terminou com erro; nenhum artigo foi publicado.")
    else:
        print("BUILD local concluído; nenhum artigo foi publicado.")


def publish_first_article(config):
    if not has_real_products(config):
        print(
            "\n⚠️ Os produtos ainda têm dados de exemplo. O primeiro artigo sairia "
            "com preço/link de exemplo, então a publicação não será oferecida."
        )
        if ask_yes_no("Quer fazer somente o BUILD local, sem publicar, por enquanto?", default=True):
            build_local_only()
        else:
            print("BUILD local pulado. Preencha os produtos reais antes de publicar.")
        return

    if not ask_yes_no("Quer gerar o PRIMEIRO artigo agora como teste?", default=True):
        print("Primeiro artigo pulado. Ele poderá ser gerado pelo agente diário depois.")
        return

    node_bin = shutil.which("node")
    if not node_bin:
        print("Node não foi encontrado. Instale-o ou rode manualmente o pipeline quando estiver disponível.")
        return

    print("\nSimulação do primeiro artigo (dry-run; nada será gravado):")
    dry_run = run_command([node_bin, "blog/generator/daily_publish.js", "--dry-run"])
    dry_output = show_command_output(dry_run)
    if dry_run is None or dry_run.returncode not in (0, 3):
        print("O dry-run falhou; a publicação real não será executada.")
        return
    if dry_run.returncode == 3:
        print("O primeiro artigo ainda não existe — ele será gerado com o Gemini na publicação real a seguir.")

    if not ask_yes_no("O resultado parece correto. Quer publicar de fato o primeiro artigo?", default=False):
        print("Publicação real cancelada; o dry-run não gravou alterações.")
        return

    print("\nPublicação real do primeiro artigo:")
    published = run_command([node_bin, "blog/generator/daily_publish.js"])
    published_output = show_command_output(published)
    combined = "\n".join(part for part in (dry_output, published_output) if part)
    print("\nResumo do pipeline:")
    print(f"  Safety-check: {infer_check(combined, 'safety')}")
    print(f"  validate.js: {infer_check(combined, 'validate')}")
    paths = html_paths(combined)
    print("  HTML gerado em: " + (", ".join(paths) if paths else "não identificado na saída"))
    if published is None or published.returncode != 0:
        print("  Resultado: a publicação terminou com erro; verifique a saída acima.")
    else:
        print("  Resultado: comando de publicação concluído.")


def install_launchagent():
    if platform.system() != "Darwin":
        print("\nA automação diária por LaunchAgent só está disponível no macOS.")
        print("Você pode rodar manualmente: node blog/generator/daily_publish.js")
        print("ou agendar esse comando via cron no seu sistema.")
        return

    if not ask_yes_no("Quer instalar o LaunchAgent de publicação diária às 08:00?", default=True):
        print("LaunchAgent não instalado.")
        return

    node_bin = shutil.which("node")
    python_bin = shutil.which("python3") or sys.executable
    if not node_bin:
        print("Node não foi encontrado; não foi possível instalar o LaunchAgent.")
        return
    if not PLIST_TEMPLATE.is_file():
        print(f"Template não encontrado: {PLIST_TEMPLATE}")
        return

    try:
        template = PLIST_TEMPLATE.read_text(encoding="utf-8")
        plist = template.replace("{BLOG_DIR}", xml_escape(str(BLOG_DIR)))
        plist = plist.replace("{HOME}", xml_escape(str(Path.home())))
        plist = plist.replace("{NODE_BIN}", xml_escape(node_bin))
        plist = plist.replace("{NODE}", xml_escape(node_bin))
        plist = plist.replace("{PYTHON}", xml_escape(python_bin))
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        (BLOG_DIR / "logs").mkdir(parents=True, exist_ok=True)
        already_exists = PLIST_PATH.exists()
        if already_exists:
            subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True, text=True, check=False)
        PLIST_PATH.write_text(plist, encoding="utf-8")
        subprocess.run(["launchctl", "load", str(PLIST_PATH)], capture_output=True, text=True, check=False)
    except OSError as exc:
        print(f"Não foi possível gravar ou carregar o LaunchAgent: {exc}")
        return

    try:
        listed = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            check=False,
        )
        matches = [line for line in (listed.stdout or "").splitlines() if "com.setup15.blog-daily" in line]
        print(f"LaunchAgent instalado em {PLIST_PATH}.")
        print("Validação (launchctl list | grep setup15.blog-daily):")
        if matches:
            print("\n".join(matches))
        else:
            print("Label ainda não apareceu na lista; confira o status do launchctl.")
    except OSError as exc:
        print(f"Não foi possível validar o LaunchAgent: {exc}")


def print_deploy_instructions():
    print("\nDeploy não será executado automaticamente.")
    print("Quando tiver uma conta Cloudflare e o projeto pronto, rode:")
    print("  cd blog && wrangler pages deploy public/ --project-name=<nome>")
    print("Substitua <nome> pelo nome do projeto Pages desejado.")


def main():
    print("=== Etapa 6 — Blog SEO ===")
    print("Vou instalar o motor do blog e um agente que escreve e publica artigos diariamente no seu nicho.")
    print("A configuração e a fila ficam neste repositório; o deploy Cloudflare continua opcional.")

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    config = ensure_config()
    if config is None:
        return 1

    if not ensure_queue(config):
        return 1

    products_ready = has_real_products(config)
    publish_first_article(config)
    if products_ready:
        install_launchagent()
    else:
        print("LaunchAgent não instalado enquanto os produtos reais não forem preenchidos.")
    print_deploy_instructions()
    print("\nSetup do blog concluído. O killswitch do agente é ~/.operacao-ia/config/.blog-killswitch.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nSetup interrompido pelo usuário.")
        raise SystemExit(130)
