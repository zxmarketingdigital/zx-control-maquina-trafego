#!/usr/bin/env python3
'''Gera um artigo do blog usando a API do Gemini.'''
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RETRYABLE_HTTP_CODES = (429, 500, 502, 503, 504)
MAX_ATTEMPTS = 3


class AgentError(Exception):
    pass


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise AgentError(f'arquivo não encontrado: {path}')
    except json.JSONDecodeError as exc:
        raise AgentError(f'JSON inválido em {path}: {exc.msg}')
    except OSError as exc:
        raise AgentError(f'não foi possível ler {path}: {exc}')


def load_gemini_key():
    value = os.environ.get('GEMINI_API_KEY', '').strip()
    env_file = Path.home() / '.operacao-ia' / 'config' / 'gemini.env'
    if not value and env_file.exists():
        try:
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                name, candidate = line.split('=', 1)
                if name.strip() == 'GEMINI_API_KEY':
                    value = candidate.strip().strip('"').strip("'")
                    break
        except OSError as exc:
            raise AgentError(f'não foi possível ler a configuração da chave Gemini: {exc}')
    if not value:
        raise AgentError('GEMINI_API_KEY não configurada em ~/.operacao-ia/config/gemini.env')
    return value


def call_gemini(prompt):
    key = load_gemini_key()
    model = os.environ.get('GEMINI_MODEL', 'gemini-flash-latest')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.7, 'responseMimeType': 'application/json'},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    body = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode('utf-8'))
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise AgentError('Gemini recusou a autenticação; verifique GEMINI_API_KEY')
            if exc.code not in RETRYABLE_HTTP_CODES or attempt == MAX_ATTEMPTS:
                if exc.code == 429:
                    raise AgentError('Gemini informou limite de uso atingido; tente novamente mais tarde')
                raise AgentError(f'Gemini retornou HTTP {exc.code}')
            time.sleep(0.5 * attempt)
        except urllib.error.URLError as exc:
            if attempt == MAX_ATTEMPTS:
                reason = getattr(exc, 'reason', 'falha de rede')
                raise AgentError(f'falha de rede ao chamar Gemini: {reason}')
            time.sleep(0.5 * attempt)
        except TimeoutError:
            if attempt == MAX_ATTEMPTS:
                raise AgentError('tempo esgotado ao chamar Gemini')
            time.sleep(0.5 * attempt)
        except json.JSONDecodeError:
            raise AgentError('Gemini retornou uma resposta que não é JSON')
        except OSError as exc:
            if attempt == MAX_ATTEMPTS:
                raise AgentError(f'erro de comunicação com Gemini: {exc}')
            time.sleep(0.5 * attempt)

    try:
        return body['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        if body.get('promptFeedback'):
            raise AgentError('Gemini bloqueou o prompt e não gerou conteúdo')
        raise AgentError('Gemini retornou uma resposta sem texto')


def parse_json_response(text):
    cleaned = (text or '').strip()
    fenced = re.search(r'^```(?:json)?\s*(.*?)\s*```$', cleaned, re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AgentError(f'resposta do Gemini não é JSON válido: {exc.msg}')


def config_context(config):
    site = config.get('site') or {}
    blog = config.get('blog') or {}
    products = config.get('products') or {}
    product_names = []
    for key, product in products.items():
        if isinstance(product, dict):
            product_names.append(f'{key}: {product.get("name", key)}')
        else:
            product_names.append(str(key))
    niche = config.get('niche') or config.get('nicho') or blog.get('niche') or blog.get('nicho') or site.get('tagline') or 'negócios e tecnologia'
    tone = config.get('tone') or config.get('tom') or blog.get('tone') or blog.get('tom') or 'claro, educativo e prático'
    product = config.get('produto') or config.get('product') or site.get('featuredProduct')
    return str(niche), str(tone), str(product or ''), ', '.join(product_names) or 'produto principal'


def build_prompt(keyword, slug, produto, tier, config):
    niche, tone, configured_product, product_options = config_context(config)
    product_context = produto or configured_product or 'produto principal'
    return f'''Você é um redator especialista em SEO para um blog brasileiro.
Crie um artigo original, útil e factual para o nicho: {niche}.

Keyword-alvo: {keyword}
Slug obrigatório: {slug}
Produto associado: {product_context}
Tier: {tier or 'cluster'}
Tom de voz do blog: {tone}
Produtos disponíveis no projeto: {product_options}

Retorne SOMENTE JSON estrito, sem markdown, comentários ou texto antes/depois.
O objeto deve ter exatamente este schema: slug (string), keyword (string), title (string), description (string), produto (string), proofPoint (string), sections (lista com exatamente 4 objetos, cada um com h2 string e points lista de strings) e faq (lista com exatamente 3 objetos, cada um com q string e a string).
Use slug exatamente igual ao informado, keyword exatamente igual à keyword-alvo e produto exatamente igual ao produto associado.
O title deve ser claro e adequado para SEO, e a description deve ter entre 120 e 160 caracteres. Cada seção deve ter pontos concretos, não frases vazias. O proofPoint deve ser uma evidência, método de verificação ou ressalva honesta, sem inventar estatísticas.

Não prometa ganho financeiro. Não use frases como ganhe dinheiro, renda garantida, lucro garantido, dinheiro fácil ou qualquer promessa de retorno. Explique limites, riscos e que resultados dependem de contexto, execução e validação. Não faça afirmações médicas, jurídicas ou financeiras sem qualificação.
Escreva em português do Brasil, priorizando a intenção de busca da keyword e entregando instruções aplicáveis.'''


def validate_article(article, slug, keyword, produto):
    if not isinstance(article, dict):
        raise AgentError('resposta do Gemini não é um objeto JSON')
    required = ('slug', 'keyword', 'title', 'description', 'produto', 'proofPoint', 'sections', 'faq')
    missing = [field for field in required if field not in article]
    if missing:
        raise AgentError(f'artigo sem campos obrigatórios: {", ".join(missing)}')
    if article.get('slug') != slug:
        raise AgentError('slug retornado pelo Gemini difere do slug solicitado')
    if article.get('keyword') != keyword:
        raise AgentError('keyword retornada pelo Gemini difere da keyword da fila')
    if produto and article.get('produto') != produto:
        raise AgentError('produto retornado pelo Gemini difere do produto da fila')
    for field in ('title', 'description', 'produto', 'proofPoint'):
        if not isinstance(article.get(field), str) or not article[field].strip():
            raise AgentError(f'campo {field} ausente ou inválido')
    sections = article.get('sections')
    if not isinstance(sections, list) or len(sections) != 4:
        raise AgentError('sections deve conter exatamente 4 seções')
    for index, section in enumerate(sections, 1):
        if not isinstance(section, dict) or not isinstance(section.get('h2'), str) or not isinstance(section.get('points'), list) or not section['points']:
            raise AgentError(f'sections[{index}] deve conter h2 e uma lista points não vazia')
        if not all(isinstance(point, str) and point.strip() for point in section['points']):
            raise AgentError(f'sections[{index}].points contém item inválido')
    faq = article.get('faq')
    if not isinstance(faq, list) or len(faq) != 3:
        raise AgentError('faq deve conter exatamente 3 perguntas')
    for index, item in enumerate(faq, 1):
        if not isinstance(item, dict) or not isinstance(item.get('q'), str) or not isinstance(item.get('a'), str) or not item['q'].strip() or not item['a'].strip():
            raise AgentError(f'faq[{index}] deve conter q e a')


def get_inputs(args, root):
    queue_path = Path(args.queue).expanduser() if args.queue else root / 'queue.json'
    config_path = Path(args.config).expanduser() if args.config else root / 'config.json'
    queue = read_json(queue_path)
    config = read_json(config_path)
    item = next((entry for entry in (queue.get('keywords') or []) if entry.get('slug') == args.slug), None)
    if item is None:
        raise AgentError(f'slug não encontrado na fila: {args.slug}')
    keyword = args.keyword or item.get('keyword')
    produto = args.produto or item.get('produto')
    tier = args.tier or item.get('tier') or 'cluster'
    if not keyword:
        raise AgentError(f'keyword ausente na fila para o slug {args.slug}')
    if not produto:
        raise AgentError(f'produto ausente na fila para o slug {args.slug}')
    return str(keyword), str(produto), str(tier), config


def main():
    parser = argparse.ArgumentParser(description='Gera um artigo do blog com Gemini')
    parser.add_argument('--slug', required=True)
    parser.add_argument('--keyword')
    parser.add_argument('--produto')
    parser.add_argument('--tier')
    parser.add_argument('--config')
    parser.add_argument('--queue')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    keyword, produto, tier, config = get_inputs(args, root)
    prompt = build_prompt(keyword, args.slug, produto, tier, config)
    try:
        raw = call_gemini(prompt)
        try:
            article = parse_json_response(raw)
            validate_article(article, args.slug, keyword, produto)
        except AgentError as first_error:
            correction = f'''A resposta anterior não passou no parser ou no schema: {first_error}.
Corrija-a e retorne SOMENTE um JSON estrito, sem fences. Use exatamente slug {args.slug}, keyword {keyword}, produto {produto}, exatamente 4 sections com h2 e points, e exatamente 3 itens faq com q e a. Não inclua promessas de ganho financeiro.
Resposta anterior:
{raw[:16000]}'''
            try:
                article = parse_json_response(call_gemini(correction))
                validate_article(article, args.slug, keyword, produto)
            except AgentError as second_error:
                raise AgentError(f'falha após duas tentativas: {second_error}') from None
    except AgentError:
        raise
    except Exception as exc:
        raise AgentError(f'falha inesperada ao gerar artigo: {exc}') from None

    output = root / 'content' / 'articles' / f'{args.slug}.json'
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(article, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        raise AgentError(f'não foi possível gravar {output}: {exc}')
    print(f'[agente] artigo gerado: content/articles/{args.slug}.json')


if __name__ == '__main__':
    try:
        main()
    except AgentError as exc:
        print(f'[agente][erro] {exc}', file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f'[agente][erro] erro inesperado: {exc}', file=sys.stderr)
        sys.exit(1)
