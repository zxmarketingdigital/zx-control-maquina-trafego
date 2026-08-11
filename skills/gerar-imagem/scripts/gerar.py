#!/usr/bin/env python3
'''Gerador de imagem com Gemini/Imagen como caminho padrao e Codex opcional.

Uso:
  python3 gerar.py --prompt '...' --output /tmp/file.png
  python3 gerar.py --prompt '...' --output /tmp/file.png --size 1280x720
  python3 gerar.py --prompt '...' --output /tmp/file.png --provider auto --json
'''

import argparse
import base64
import fcntl
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager

VALID_SIZES = {
    '1024x1024', '1280x720', '720x1280', '1792x1024', '1024x1792',
    '1536x1024', '1024x1536', '1080x1080', '1080x1350', '1080x1920',
    '1920x1080',
}
GEMINI_MODEL = 'gemini-3.1-flash-image-preview'
IMAGEN_MODEL = 'imagen-4.0-ultra-generate-001'
CODEX_GEN_DIR = os.path.expanduser('~/.codex/generated_images')
ENV_DIR = os.path.expanduser('~/.operacao-ia/config')
GERAR_LOCK = '/tmp/gerar-imagem-codex.lock'
_SECRETS = set()

# Reforco anti-distorcao anexado a TODO prompt (image2, gemini, imagen). O gpt-image-2 tende a
# esticar/alargar pessoas, rostos, mockups e texto pra preencher a largura do formato — recorrente
# em artes de trafego. Ver feedback_imagem_proporcao_natural_nao_esticar.
ANTI_DISTORCAO = (
    ' REGRA OBRIGATÓRIA DE PROPORÇÃO: todos os elementos — pessoas, rostos, mãos, corpos, objetos, '
    'logos, mockups, ícones e o texto — devem ter proporção anatômica e geométrica NATURAL e REALISTA. '
    'NUNCA esticar, alargar, achatar, espremer ou distorcer nenhum elemento (horizontal ou verticalmente) '
    'para preencher o espaço. Corpos e rostos humanos SEMPRE em escala humana correta, sem ombros/tronco '
    'alargados. Se sobrar espaço, deixar margem ou fundo em vez de deformar qualquer elemento.'
)


def _remember_secret(value):
    if value and len(value) > 4:
        _SECRETS.add(value)
    return value


def _redact(value):
    text = str(value or '')
    for secret in sorted(_SECRETS, key=len, reverse=True):
        text = text.replace(secret, '[REDACTED]')
    return text


def log(message, json_mode):
    if not json_mode:
        print(_redact(message), file=sys.stderr, flush=True)


def load_env_key(name):
    '''Busca uma chave no ambiente e nos arquivos de configuracao locais.'''
    if os.environ.get(name):
        return _remember_secret(os.environ[name])

    candidates = []
    if os.path.isdir(ENV_DIR):
        candidates.extend(
            os.path.join(ENV_DIR, filename)
            for filename in sorted(os.listdir(ENV_DIR))
            if filename.endswith('.env')
        )
    candidates.extend([
        os.path.expanduser('~/.zshrc'),
        os.path.expanduser('~/.profile'),
        os.path.expanduser('~/.bashrc'),
        os.path.expanduser('~/.openclaw/.env'),
    ])

    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding='utf-8') as env_file:
                for line in env_file:
                    line = line.strip()
                    if line.startswith('export '):
                        line = line[7:].lstrip()
                    key, separator, value = line.partition('=')
                    if not separator or key.strip() != name:
                        continue
                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                        value = value[1:-1]
                    else:
                        value = value.split('#', 1)[0].strip()
                    if value and not value.startswith('$') and value not in {
                        'YOUR_API_KEY', 'secret-key', 'another-secret'
                    }:
                        return _remember_secret(value)
        except OSError:
            continue
    return None


def _cor_fundo_pil(img):
    '''Cor dominante das bordas laterais — o fundo real da arte.

    Usa a moda de uma paleta quantizada, e nao a media. Media entre o fundo e um
    elemento contrastante devolve uma cor que nao existe na arte e deixa a emenda
    do pad visivel.
    '''
    from collections import Counter
    from PIL import Image

    rgb = img.convert('RGB')
    width, height = rgb.size
    faixa = min(width, max(8, round(width * 0.04)))
    tiras = Image.new('RGB', (faixa * 2, height))
    tiras.paste(rgb.crop((0, 0, faixa, height)), (0, 0))
    tiras.paste(rgb.crop((width - faixa, 0, width, height)), (faixa, 0))

    teto = 300_000
    if tiras.width * tiras.height > teto:
        fator = (teto / (tiras.width * tiras.height)) ** 0.5
        tiras = tiras.resize(
            (max(1, int(tiras.width * fator)), max(1, int(tiras.height * fator))),
            Image.NEAREST,
        )

    buffer = tiras.tobytes()
    pixels = [
        (buffer[index], buffer[index + 1], buffer[index + 2])
        for index in range(0, len(buffer), 3)
    ]
    if not pixels:
        return (255, 255, 255)
    contagem = Counter((r // 16, g // 16, b // 16) for r, g, b in pixels)
    balde = contagem.most_common(1)[0][0]
    selecionados = [
        pixel for pixel in pixels
        if (pixel[0] // 16, pixel[1] // 16, pixel[2] // 16) == balde
    ]
    quantidade = len(selecionados)
    return tuple(
        round(sum(pixel[channel] for pixel in selecionados) / quantidade)
        for channel in range(3)
    )


def _resize_sips_padfit(path, target_width, target_height):
    '''Fallback sem Pillow: contain + pad via sips, nunca -z sozinho.'''
    info = subprocess.run(
        ['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path],
        check=True, capture_output=True, text=True,
    ).stdout
    dimensions = {}
    for line in info.splitlines():
        if ':' in line:
            key, _, value = line.strip().partition(':')
            if key in ('pixelWidth', 'pixelHeight'):
                dimensions[key] = int(value.strip())
    source_width = dimensions['pixelWidth']
    source_height = dimensions['pixelHeight']
    if (source_width, source_height) == (target_width, target_height):
        return

    scale = min(target_width / source_width, target_height / source_height)
    new_width = max(1, round(source_width * scale))
    new_height = max(1, round(source_height * scale))
    # As dimensoes ja foram calculadas de forma proporcional; sips apenas reamostra.
    subprocess.run(
        ['sips', '--resampleHeightWidth', str(new_height), str(new_width), path],
        check=True, capture_output=True,
    )
    subprocess.run(
        ['sips', '--padToHeightWidth', str(target_height), str(target_width),
         '--padColor', 'FFFFFF', path],
        check=True, capture_output=True,
    )


def resize_png(path, target_size):
    '''Ajusta o PNG para target_size preservando a proporcao do conteudo (pad-fit).

    O gpt-image-2 pode ignorar o --size pedido e devolver dimensao diferente. Usar
    sips -z cru forca a dimensao exata e estica a imagem; isso deforma rostos,
    logotipos e tipografia. O pad-fit usa contain e preenche a sobra com a cor de
    fundo amostrada da propria arte, sem desfazer a regra ANTI_DISTORCAO.
    '''
    target_width, target_height = (int(value) for value in target_size.split('x'))
    try:
        from PIL import Image
    except ImportError:
        _resize_sips_padfit(path, target_width, target_height)
        return

    with Image.open(path) as source:
        has_alpha = 'A' in source.getbands() or 'transparency' in source.info
        image = source.convert('RGBA') if has_alpha else source.convert('RGB')
        ready = image.size == (target_width, target_height)
    if ready:
        return

    scale = min(target_width / image.width, target_height / image.height)
    new_width = max(1, round(image.width * scale))
    new_height = max(1, round(image.height * scale))
    resized = image.resize((new_width, new_height), Image.LANCZOS)
    background = _cor_fundo_pil(image)

    if image.mode == 'RGBA':
        canvas = Image.new('RGBA', (target_width, target_height), background + (255,))
        # Sem mascara, os pixels transparentes da arte continuam transparentes; apenas a
        # sobra do canvas recebe a cor de fundo opaca.
        canvas.paste(resized, (
            (target_width - new_width) // 2,
            (target_height - new_height) // 2,
        ))
    else:
        canvas = Image.new('RGB', (target_width, target_height), background)
        canvas.paste(resized, (
            (target_width - new_width) // 2,
            (target_height - new_height) // 2,
        ))
    canvas.save(path)


def _codex_pngs(base_dir, recursive=False):
    pattern = os.path.join(base_dir, '**', '*.png') if recursive else os.path.join(base_dir, '*.png')
    return [
        path for path in glob.glob(pattern, recursive=recursive)
        if os.path.basename(path).startswith(('ig_', 'call_'))
    ]


@contextmanager
def codex_lock():
    '''Serializa a captura dos PNGs produzidos por chamadas concorrentes.'''
    descriptor = os.open(GERAR_LOCK, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def codex_logged_in():
    '''Retorna True somente quando o status do Codex confirma uma sessao.'''
    if shutil.which('codex') is None:
        return False
    try:
        status = subprocess.run(
            ['codex', 'login', 'status'],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    combined = ((status.stdout or '') + ' ' + (status.stderr or '')).lower()
    return status.returncode == 0 and 'logged in' in combined


def gen_image2(prompt, output, size, quality, json_mode):
    '''Gera via Codex CLI e tool nativa image_gen (gpt-image-2).'''
    if shutil.which('codex') is None:
        raise RuntimeError('codex CLI nao instalado')
    if not codex_logged_in():
        raise RuntimeError('codex nao esta logado')

    output = os.path.abspath(output)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    if os.path.exists(output):
        os.remove(output)

    instructions = (
        f'Use case: photorealistic-natural\n'
        f'Primary request: {prompt}\n'
        f'Quality: {quality}. Target size: {size}.\n'
        f'Use the built-in image_gen tool (gpt-image-2). Generate ONE image. '
        f'Save the final PNG to {output}. Do not create SVG or vector; it must be raster. '
        f'At the end print just the absolute path of the saved PNG.'
    )

    with codex_lock():
        before_dirs = set()
        if os.path.isdir(CODEX_GEN_DIR):
            before_dirs = {
                entry for entry in os.listdir(CODEX_GEN_DIR)
                if os.path.isdir(os.path.join(CODEX_GEN_DIR, entry))
            }
        before_pngs = set(_codex_pngs(CODEX_GEN_DIR, recursive=True))
        log('[image2] chamando codex exec...', json_mode)
        try:
            process = subprocess.run(
                ['codex', 'exec', '--skip-git-repo-check', '-c', 'mcp_servers={}', instructions],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=240,
            )
        except subprocess.SubprocessError as error:
            raise RuntimeError(f'codex exec falhou: {_redact(error)}')

        if process.returncode != 0:
            tail = _redact((process.stderr or '')[-400:])
            raise RuntimeError(f'codex exec falhou: {tail}')

        if not os.path.exists(output):
            combined = (process.stdout or '') + '\n' + (process.stderr or '')
            source = None
            match = re.search(r'session id:\s*([0-9a-f-]{36})', combined, re.IGNORECASE)
            if match:
                session_dir = os.path.join(CODEX_GEN_DIR, match.group(1))
                session_files = _codex_pngs(session_dir)
                if session_files:
                    source = max(session_files, key=os.path.getmtime)

            if source is None and os.path.isdir(CODEX_GEN_DIR):
                after_dirs = {
                    entry for entry in os.listdir(CODEX_GEN_DIR)
                    if os.path.isdir(os.path.join(CODEX_GEN_DIR, entry))
                }
                new_dirs = sorted(
                    after_dirs - before_dirs,
                    key=lambda entry: os.path.getmtime(os.path.join(CODEX_GEN_DIR, entry)),
                    reverse=True,
                )
                for entry in new_dirs:
                    files = _codex_pngs(os.path.join(CODEX_GEN_DIR, entry))
                    if files:
                        source = max(files, key=os.path.getmtime)
                        break

            if source is None:
                after_pngs = set(_codex_pngs(CODEX_GEN_DIR, recursive=True))
                new_files = sorted(
                    after_pngs - before_pngs,
                    key=os.path.getmtime,
                    reverse=True,
                )
                if new_files:
                    source = new_files[0]

            if source is None:
                raise RuntimeError(
                    'codex executou mas nao foi encontrado PNG gerado; '
                    f'stdout tail: {_redact((process.stdout or '')[-300:])}'
                )
            shutil.copyfile(source, output)

    try:
        resize_png(output, size)
    except Exception as error:
        _remove(output)
        raise RuntimeError(f'resize do Codex falhou: {_redact(error)}')
    return 'image2'


def _google_key():
    key = load_env_key('GEMINI_API_KEY') or load_env_key('GOOGLE_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY nao encontrada no ambiente nem em ~/.operacao-ia/config/*.env')
    return key


def _save_bytes(data, output):
    if isinstance(data, str):
        data = base64.b64decode(data)
    if not data:
        return False
    with open(output, 'wb') as image_file:
        image_file.write(bytes(data))
    return True


def _save_gemini_part(part, output):
    inline_data = getattr(part, 'inline_data', None)
    if inline_data is not None:
        data = getattr(inline_data, 'data', None)
        if data is not None and _save_bytes(data, output):
            return True
    as_image = getattr(part, 'as_image', None)
    if callable(as_image):
        image = as_image()
        if image is not None and callable(getattr(image, 'save', None)):
            image.save(output)
            return True
    return False


def _genai_client():
    try:
        from google import genai
    except ImportError as error:
        raise RuntimeError(
            'pacote google-genai nao instalado; instale-o para usar Gemini/Imagen'
        ) from error
    return genai.Client(api_key=_google_key())


def gen_gemini(prompt, output, size, model=GEMINI_MODEL, json_mode=False):
    '''Gera uma imagem usando o modelo Gemini via Google GenAI SDK.'''
    from google.genai import types

    client = _genai_client()
    log(f'[{model}] chamando Google GenAI generate_content...', json_mode)
    config = types.GenerateContentConfig(response_modalities=['IMAGE'])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    for candidate in getattr(response, 'candidates', []) or []:
        content = getattr(candidate, 'content', None)
        for part in getattr(content, 'parts', []) or []:
            if _save_gemini_part(part, output):
                resize_png(output, size)
                return 'gemini'
    raise RuntimeError('Gemini nao retornou dados de imagem')


def gen_imagen(prompt, output, size, model=IMAGEN_MODEL, json_mode=False):
    '''Gera uma imagem usando Imagen via Google GenAI SDK.'''
    from google.genai import types

    client = _genai_client()
    log(f'[{model}] chamando Google GenAI generate_images...', json_mode)
    config = types.GenerateImagesConfig(number_of_images=1, output_mime_type='image/png')
    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=config,
    )
    generated_images = getattr(response, 'generated_images', []) or []
    if not generated_images:
        raise RuntimeError('Imagen nao retornou imagens')

    image = getattr(generated_images[0], 'image', None)
    if image is None:
        raise RuntimeError('Imagen retornou um item sem imagem')
    if callable(getattr(image, 'save', None)):
        image.save(output)
    else:
        data = getattr(image, 'image_bytes', None) or getattr(image, 'data', None)
        if not _save_bytes(data, output):
            raise RuntimeError('Imagen retornou imagem em formato desconhecido')
    resize_png(output, size)
    return 'imagen'


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--size', default='1024x1024')
    parser.add_argument(
        '--provider', default='auto',
        choices=['auto', 'image2', 'gemini', 'imagen'],
    )
    parser.add_argument('--quality', default='high', choices=['high', 'medium', 'low'])
    parser.add_argument('--json', action='store_true', help='imprime JSON em stdout')
    args = parser.parse_args()

    if args.size not in VALID_SIZES:
        print(
            f"ERRO: size '{args.size}' invalido. Use: {sorted(VALID_SIZES)}",
            file=sys.stderr,
        )
        sys.exit(2)

    if ANTI_DISTORCAO.strip() not in args.prompt:
        args.prompt = args.prompt.rstrip() + ANTI_DISTORCAO
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or '.', exist_ok=True)

    if args.provider == 'auto':
        # Gemini e o primeiro provider. Imagen permanece no caminho padrao; Codex so
        # e acrescentado depois da falha do Gemini e de uma verificacao de login.
        chain = [
            ('gemini', lambda: gen_gemini(
                args.prompt, args.output, args.size, GEMINI_MODEL, args.json
            )),
        ]
    elif args.provider == 'gemini':
        chain = [('gemini', lambda: gen_gemini(
            args.prompt, args.output, args.size, GEMINI_MODEL, args.json
        ))]
    elif args.provider == 'imagen':
        chain = [('imagen', lambda: gen_imagen(
            args.prompt, args.output, args.size, IMAGEN_MODEL, args.json
        ))]
    else:
        chain = [('image2', lambda: gen_image2(
            args.prompt, args.output, args.size, args.quality, args.json
        ))]

    errors = []
    started = time.time()
    used = None
    auto_codex_checked = False

    index = 0
    while index < len(chain):
        name, function = chain[index]
        index += 1
        try:
            used = function()
            break
        except Exception as error:
            message = _redact(error)
            errors.append(f'{name}: {message}')
            log(f'[{name}] falhou: {message}', args.json)

            if args.provider == 'auto' and name == 'gemini' and not auto_codex_checked:
                auto_codex_checked = True
                chain.append(('imagen', lambda: gen_imagen(
                    args.prompt, args.output, args.size, IMAGEN_MODEL, args.json
                )))
                if codex_logged_in():
                    log('[auto] Codex logado; upgrade image2 habilitado.', args.json)
                    chain.append(('image2', lambda: gen_image2(
                        args.prompt, args.output, args.size, args.quality, args.json
                    )))

    elapsed = round(time.time() - started, 1)
    if used is None:
        result = {'ok': False, 'errors': errors, 'elapsed_s': elapsed}
        if args.json:
            print(json.dumps(result))
        else:
            print('FALHA — todos os providers falharam:', file=sys.stderr)
            for error in errors:
                print(f'  - {_redact(error)}', file=sys.stderr)
        sys.exit(1)

    try:
        size_bytes = os.path.getsize(args.output)
    except OSError as error:
        print(f'ERRO: provider concluiu sem PNG valido: {_redact(error)}', file=sys.stderr)
        sys.exit(1)

    result = {
        'ok': True,
        'provider': used,
        'output': os.path.abspath(args.output),
        'size_bytes': size_bytes,
        'elapsed_s': elapsed,
    }
    if args.json:
        print(json.dumps(result))
    else:
        print(
            f'OK — provider={used} path={args.output} '
            f'bytes={size_bytes} elapsed={elapsed}s'
        )


if __name__ == '__main__':
    main()
