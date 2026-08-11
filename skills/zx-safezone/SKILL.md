---
name: zx-safezone
description: "QA de safe-zone para qualquer criativo de anúncio Meta — estático, animado ou vídeo. Audita se headline, preço e CTA sobrevivem ao corte entre proporções e ao overlay que o Meta desenha por cima (perfil no topo, legenda + botão na base). Use SEMPRE antes de aprovar ou subir um criativo de anúncio: gerar imagem de anúncio, checar safe-zone, validar criativo, aprovar arte de anúncio, derivar stories, normalizar arte."
model: sonnet
effort: low
---

# zx-safezone — QA de safe-zone de criativo de anúncio

## Por que existe

O Meta faz duas coisas com todo criativo, e as duas destroem informação se você não contar
com elas:

1. **Corta entre proporções** — um 4:5 vira 1:1 no Feed/Explore e é recortado para 9:16 em
   Stories/Reels, comendo as laterais.
2. **Desenha por cima** — foto/nome do perfil nos **14% do topo**, legenda + botão de CTA nos
   **25% da base**, em Stories/Reels. Headline ou preço que caem nessas faixas somem.

Rodar este QA **antes** de aprovar ou subir qualquer criativo é o que evita anúncio bom no
Feed e ilegível em Stories.

## Uso

```bash
python3 scripts/zx-safezone.py <arte>.png --derivar   # rotina padrão: audita o master 4:5 e
                                                          # gera o 9:16 encaixado na faixa segura
python3 scripts/zx-safezone.py <arte>.png --normalizar # encaixa o master inteiro num 1080x1350
python3 scripts/zx-safezone.py <arte>.png               # só audita (asset único p/ todos os
                                                          # posicionamentos)
python3 scripts/zx-safezone.py <arte>.png --modo stories
python3 scripts/zx-safezone.py <video>.mp4 --modo stories  # amostra frames ao longo do vídeo
python3 scripts/zx-safezone.py *.png --json
```

Exit codes: `0` = aprovado · `1` = violação (não subir, regenerar) · `2` = erro de uso/arquivo.

## Estratégia recomendada

- **Master 4:5 não muda** — vai inteiro pro Feed, como sempre. `--derivar` gera o `<arte>-9x16.png`
  correspondente, encaixando a arte entre 14% e 75% da altura. **Suba os dois assets** no anúncio.
- **Quando o helper imprimir "DERIVAÇÃO NÃO SERVE aqui"** (a arte ocupa menos de 72% do espaço
  seguro, ou o derivado reprova no QA) — não insista ajustando a derivação. Gere o 9:16 nativo
  do zero, já pensado para 1080×1920.
- **Exit 1 = não mostrar nem subir a arte** — regenerar antes de qualquer aprovação.
- O overlay `<arte>.safezone.png` desenha as faixas mortas sobre o criativo — abra com a tool
  Read quando precisar entender exatamente o que violou. O número decide; o overlay explica.

## Quando chamar

- Depois de gerar qualquer imagem com `gerar-imagem`, antes de aprovar como criativo de anúncio.
- Depois de renderizar qualquer vídeo com `criar-anuncio-video-html` ou `gerar-video-mp4`
  destinado a Meta Ads.
- Sempre antes de subir arte ou vídeo via `meta-campaign` (Etapa 7).

## Dependências

Python 3 + Pillow (`PIL`) + `numpy`. Sem chamada de rede — roda 100% local. Para vídeo, precisa
de `ffmpeg` no PATH (amostragem de frames).
