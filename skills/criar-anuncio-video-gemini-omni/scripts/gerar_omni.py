#!/usr/bin/env python3
'''Gera vídeo(s) de anúncio Meta com Gemini Omni Flash (Interactions API).

Uso:
  # 1 vídeo por prompt inline
  python3 gerar_omni.py --prompt 'cena ...' --out ~/.operacao-ia/scripts/video-omni/ad1.mp4

  # lote: 1 prompt por linha num arquivo (gera NNN_<slug>.mp4)
  python3 gerar_omni.py --prompts-file prompts.txt --outdir ~/.operacao-ia/scripts/video-omni/

Opções:
  --aspect 9:16|16:9   (default 9:16 — vertical Meta)
  --model MODEL        (default gemini-omni-flash-preview)

Requisitos: google-genai>=2.10 (interactions API). Chave em
~/.operacao-ia/config/gemini.env (GEMINI_API_KEY). COBRA por uso na API.
'''
import argparse
import os
import pathlib
import re
import sys
import time


def load_key():
    path = os.path.expanduser('~/.operacao-ia/config/gemini.env')
    if os.path.exists(path):
        for raw_line in open(path, encoding='utf-8'):
            line = raw_line.strip()
            match = re.match(r'^\s*GEMINI_API_KEY=(.+)$', line)
            if match:
                key = match.group(1).strip().strip('"').strip("'")
                if key:
                    return key
    sys.exit('ERRO: nenhuma GEMINI_API_KEY preenchida em ~/.operacao-ia/config/gemini.env')


def slug(value, n=32):
    value = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return (value[:n] or 'video').rstrip('-')


def gen_one(client, model, prompt, aspect, out_path):
    from google import genai  # noqa: F401

    t0 = time.time()
    print(f'[gerar] {out_path.name} — criando interaction...', flush=True)
    interaction = client.interactions.create(
        model=model,
        input=prompt,
        response_format={'type': 'video', 'aspect_ratio': aspect, 'delivery': 'uri'},
    )
    video = interaction.output_video
    file_id = re.search(r'/files/([^:/?]+)', video.uri).group(1)
    while True:
        state = client.files.get(name=f'files/{file_id}').state.name
        if state == 'ACTIVE':
            break
        if state == 'FAILED':
            raise RuntimeError(f'geração FAILED ({out_path.name})')
        if time.time() - t0 > 480:
            raise TimeoutError(f'timeout 8min ({out_path.name})')
        time.sleep(6)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(client.files.download(file=f'files/{file_id}'))
    print(f'[ok] {out_path} — {out_path.stat().st_size} bytes ({int(time.time() - t0)}s)', flush=True)
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt')
    parser.add_argument('--prompts-file')
    parser.add_argument('--out')
    parser.add_argument('--outdir')
    parser.add_argument('--aspect', default='9:16', choices=['9:16', '16:9'])
    parser.add_argument('--model', default='gemini-omni-flash-preview')
    args = parser.parse_args()

    from google import genai

    client = genai.Client(api_key=load_key())

    jobs = []
    default_outdir = os.path.expanduser('~/.operacao-ia/scripts/video-omni/')
    if args.prompt:
        output = pathlib.Path(args.out or os.path.join(default_outdir, 'omni_ad.mp4')).expanduser()
        jobs.append((args.prompt, output))
    elif args.prompts_file:
        output_dir = pathlib.Path(args.outdir or default_outdir).expanduser()
        lines = [
            line.strip()
            for line in open(os.path.expanduser(args.prompts_file), encoding='utf-8')
            if line.strip() and not line.startswith('#')
        ]
        for i, prompt in enumerate(lines, 1):
            jobs.append((prompt, output_dir / f'{i:02d}_{slug(prompt)}.mp4'))
    else:
        sys.exit('passe --prompt ou --prompts-file')

    print(f'== {len(jobs)} vídeo(s) | modelo {args.model} | {args.aspect} ==', flush=True)
    ok, fail = [], []
    for prompt, output in jobs:
        try:
            gen_one(client, args.model, prompt, args.aspect, output)
            ok.append(output)
        except Exception as error:
            print(f'[FALHOU] {output.name}: {type(error).__name__}: {str(error)[:200]}', flush=True)
            fail.append(output.name)
    print(f'\n== FIM: {len(ok)} ok, {len(fail)} falha(s) ==')
    for output in ok:
        print('  ✔', output)
    if fail:
        print('  x falhas:', ', '.join(fail))
        sys.exit(1)


if __name__ == '__main__':
    main()
