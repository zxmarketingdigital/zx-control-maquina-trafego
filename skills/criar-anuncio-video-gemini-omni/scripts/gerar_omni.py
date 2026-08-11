#!/usr/bin/env python3
"""
Gera vídeo(s) de anúncio Meta com Gemini Omni Flash (Interactions API).

Uso:
  # 1 vídeo por prompt inline
  python3 gerar_omni.py --prompt "cena ..." --out ~/.operacao-ia/scripts/video-omni/ad1.mp4

  # lote: 1 prompt por linha num arquivo (gera NNN_<slug>.mp4)
  python3 gerar_omni.py --prompts-file prompts.txt --outdir ~/.operacao-ia/scripts/video-omni/

Opções:
  --aspect 9:16|16:9   (default 9:16 — vertical Meta)
  --model MODEL        (default gemini-omni-flash-preview)

Requisitos: google-genai>=2.10 (interactions API). Chave em
~/.operacao-ia/config/gemini.env (GEMINI_API_KEY). COBRA por uso na API.
"""
import os, re, sys, time, argparse, pathlib


def load_key():
    path = os.path.expanduser("~/.operacao-ia/config/gemini.env")
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r'^\s*GEMINI_API_KEY=(.+)$', line.strip())
            if m:
                k = m.group(1).strip().strip('"').strip("'")
                if k:
                    return k
    sys.exit("ERRO: nenhuma GEMINI_API_KEY preenchida em ~/.operacao-ia/config/gemini.env")


def slug(s, n=32):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return (s[:n] or "video").rstrip('-')


def gen_one(client, model, prompt, aspect, out_path):
    from google import genai  # noqa
    t0 = time.time()
    print(f"[gerar] {out_path.name} — criando interaction...", flush=True)
    it = client.interactions.create(
        model=model,
        input=prompt,
        response_format={"type": "video", "aspect_ratio": aspect, "delivery": "uri"},
    )
    vo = it.output_video
    fid = re.search(r'/files/([^:/?]+)', vo.uri).group(1)
    while True:
        st = client.files.get(name=f"files/{fid}").state.name
        if st == "ACTIVE":
            break
        if st == "FAILED":
            raise RuntimeError(f"geração FAILED ({out_path.name})")
        if time.time() - t0 > 480:
            raise TimeoutError(f"timeout 8min ({out_path.name})")
        time.sleep(6)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(client.files.download(file=f"files/{fid}"))
    print(f"[ok] {out_path} — {out_path.stat().st_size} bytes ({int(time.time()-t0)}s)", flush=True)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompts-file")
    ap.add_argument("--out")
    ap.add_argument("--outdir")
    ap.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    ap.add_argument("--model", default="gemini-omni-flash-preview")
    a = ap.parse_args()

    from google import genai
    client = genai.Client(api_key=load_key())

    jobs = []
    if a.prompt:
        out = pathlib.Path(a.out or os.path.expanduser("~/.operacao-ia/scripts/video-omni/omni_ad.mp4")).expanduser()
        jobs.append((a.prompt, out))
    elif a.prompts_file:
        outdir = pathlib.Path(a.outdir or os.path.expanduser("~/.operacao-ia/scripts/video-omni/")).expanduser()
        lines = [l.strip() for l in open(os.path.expanduser(a.prompts_file)) if l.strip() and not l.startswith("#")]
        for i, p in enumerate(lines, 1):
            jobs.append((p, outdir / f"{i:02d}_{slug(p)}.mp4"))
    else:
        sys.exit("passe --prompt ou --prompts-file")

    print(f"== {len(jobs)} vídeo(s) | modelo {a.model} | {a.aspect} ==", flush=True)
    ok, fail = [], []
    for prompt, out in jobs:
        try:
            gen_one(client, a.model, prompt, a.aspect, out)
            ok.append(out)
        except Exception as e:
            print(f"[FALHOU] {out.name}: {type(e).__name__}: {str(e)[:200]}", flush=True)
            fail.append(out.name)
    print(f"\n== FIM: {len(ok)} ok, {len(fail)} falha(s) ==")
    for o in ok:
        print("  ✔", o)
    if fail:
        print("  x falhas:", ", ".join(fail))
        sys.exit(1)


if __name__ == "__main__":
    main()
