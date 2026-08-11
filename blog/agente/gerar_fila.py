#!/usr/bin/env python3
'''Gera uma fila hub-and-spoke de keywords, com fallback local.'''
import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


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


def load_key():
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
    key = load_key()
    model = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': 0.8, 'responseMimeType': 'application/json'}}
    request = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise AgentError('Gemini recusou a autenticação; verifique GEMINI_API_KEY')
        if exc.code == 429:
            raise AgentError('Gemini informou limite de uso atingido')
        raise AgentError(f'Gemini retornou HTTP {exc.code}')
    except urllib.error.URLError as exc:
        raise AgentError(f'falha de rede ao chamar Gemini: {getattr(exc, "reason", "erro de conexão")}')
    except TimeoutError:
        raise AgentError('tempo esgotado ao chamar Gemini')
    except json.JSONDecodeError:
        raise AgentError('Gemini retornou uma resposta que não é JSON')
    except OSError as exc:
        raise AgentError(f'erro de comunicação com Gemini: {exc}')
    try:
        return body['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        raise AgentError('Gemini retornou uma resposta sem lista de sugestões')


def parse_response(text):
    value = (text or '').strip()
    match = re.search(r'^```(?:json)?\s*(.*?)\s*```$', value, re.I | re.S)
    if match:
        value = match.group(1).strip()
    try:
        data = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AgentError(f'resposta do Gemini não é JSON válido: {exc.msg}')
    if isinstance(data, dict):
        data = data.get('keywords') or data.get('suggestions')
    if not isinstance(data, list):
        raise AgentError('resposta do Gemini não contém uma lista de keywords')
    return data


def slugify(value):
    normalized = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode('ascii').lower()
    normalized = re.sub(r'[^a-z0-9]+', '-', normalized).strip('-')
    return normalized[:80] or 'artigo'


def default_product(config):
    products = config.get('products') or {}
    if products:
        return next(iter(products.keys()))
    return config.get('produto') or config.get('product') or 'produto-principal'


def prompt_for(topic, config):
    site = config.get('site') or {}
    niche = config.get('niche') or config.get('nicho') or site.get('tagline') or topic
    product = default_product(config)
    return f'''Você é um estrategista de conteúdo SEO. Para o nicho ou tema {topic}, dentro do contexto {niche}, crie uma arquitetura hub-and-spoke.
Retorne SOMENTE JSON estrito: uma lista de 6 a 10 objetos. Cada objeto deve conter keyword, slug, produto, tier, volume_mes, cpc_top_brl, intencao e spoke_of.
Inclua 1 ou 2 objetos tier pillar, com tema amplo. Os demais devem ser tier cluster e spoke_of deve apontar para o id do pillar correspondente; use spoke_of como referência textual temporária ao pillar ou deixe-o nulo para que o programa associe. Use produto {product}, slugs únicos em kebab-case, intenções de busca realistas e null quando não souber volume ou CPC. Não invente dados com falsa precisão. Não inclua promessas de ganhos financeiros.'''


def fallback(topic, product):
    phrases = [
        f'{topic}: guia completo',
        f'como aplicar {topic} no dia a dia',
        f'ferramentas para {topic}',
        f'estratégias de {topic}',
        f'como começar com {topic}',
        f'erros comuns em {topic}',
        f'boas práticas de {topic}',
    ]
    return [{'keyword': phrase, 'slug': slugify(phrase), 'produto': product, 'tier': 'pillar' if index == 0 else 'cluster', 'volume_mes': None, 'cpc_top_brl': None, 'intencao': 'informacional', 'spoke_of': None} for index, phrase in enumerate(phrases)]


def normalize(items, product):
    cleaned = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get('keyword') or '').strip()
        if not keyword:
            continue
        slug = slugify(item.get('slug') or keyword)
        if slug in seen:
            continue
        seen.add(slug)
        tier = 'pillar' if str(item.get('tier', '')).lower() == 'pillar' else 'cluster'
        cleaned.append({'keyword': keyword, 'slug': slug, 'produto': str(item.get('produto') or product), 'tier': tier, 'volume_mes': item.get('volume_mes'), 'cpc_top_brl': item.get('cpc_top_brl'), 'intencao': str(item.get('intencao') or 'informacional'), 'spoke_of': item.get('spoke_of')})
    if len(cleaned) < 6 or len(cleaned) > 10:
        raise AgentError(f'Gemini retornou {len(cleaned)} keywords; eram necessárias 6 a 10')
    pillars = [item for item in cleaned if item['tier'] == 'pillar'][:2]
    if not pillars:
        cleaned[0]['tier'] = 'pillar'
        pillars = [cleaned[0]]
    pillar_indexes = [cleaned.index(item) for item in pillars]
    for index, item in enumerate(cleaned):
        if item['tier'] == 'pillar':
            item['spoke_of'] = None
        else:
            item['spoke_of'] = None
            nearest = pillar_indexes[index % len(pillar_indexes)]
            item['_pillar_index'] = nearest
    return cleaned


def make_queue(items, topic):
    pillars = [index for index, item in enumerate(items) if item['tier'] == 'pillar']
    keywords = []
    for index, item in enumerate(items, 1):
        pillar_index = item.pop('_pillar_index', None)
        parent_id = index if pillar_index is None else pillar_index + 1
        keywords.append({'id': f'kw-{index:03d}', 'keyword': item['keyword'], 'slug': item['slug'], 'produto': item['produto'], 'tier': item['tier'], 'volume_mes': item.get('volume_mes'), 'cpc_top_brl': item.get('cpc_top_brl'), 'intencao': item.get('intencao') or 'informacional', 'spoke_of': None if item['tier'] == 'pillar' else f'kw-{parent_id:03d}', 'status': 'pending', '_published_at': None})
    return {'_comment': f'Fila hub-and-spoke gerada para: {topic}', '_updated': datetime.now(timezone.utc).isoformat(), 'keywords': keywords}


def main():
    parser = argparse.ArgumentParser(description='Gera a fila de keywords do blog')
    parser.add_argument('tema', nargs='?')
    parser.add_argument('--nicho')
    parser.add_argument('--config')
    parser.add_argument('--output', '--queue', dest='output')
    args = parser.parse_args()
    topic = (args.nicho or args.tema or '').strip()
    if not topic:
        raise AgentError('informe o nicho ou tema como argumento')
    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config).expanduser() if args.config else root / 'config.json'
    output = Path(args.output).expanduser() if args.output else root / 'queue.json'
    config = read_json(config_path)
    product = default_product(config)
    try:
        items = normalize(parse_response(call_gemini(prompt_for(topic, config))), product)
        print('[fila] sugestões obtidas do Gemini')
    except AgentError as exc:
        print(f'[fila][aviso] Gemini indisponível ({exc}); usando fallback local', file=sys.stderr)
        items = normalize(fallback(topic, product), product)
    queue = make_queue(items, topic)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        raise AgentError(f'não foi possível gravar {output}: {exc}')
    print(f'[fila] queue.json gerado com {len(queue["keywords"])} keywords pendentes')


if __name__ == '__main__':
    try:
        main()
    except AgentError as exc:
        print(f'[fila][erro] {exc}', file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f'[fila][erro] erro inesperado: {exc}', file=sys.stderr)
        sys.exit(1)
