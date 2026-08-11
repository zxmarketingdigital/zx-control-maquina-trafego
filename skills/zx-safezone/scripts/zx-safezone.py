#!/usr/bin/env python3
"""
zx-safezone — QA de SAFE-ZONE para QUALQUER criativo de anúncio (estático, animado ou vídeo).

Por que existe: o Meta recorta o criativo entre proporções (4:5 → 1:1, 4:5 → 9:16) e
INJETA elementos por cima dele (nome/foto do perfil no topo; legenda + botão "Saiba mais"
na base). Quem sobe UM asset para todos os posicionamentos perde qualquer informação que
esteja fora da interseção segura — headline cortada, preço coberto, CTA escondido.

Este helper vale para TODO tipo de anúncio — imagem estática, animada ou vídeo.

Uso:
  zx-safezone arte.png --derivar            # ROTINA PADRÃO: master 4:5 + gera o 9:16 de Stories
  zx-safezone arte.png --normalizar         # encaixa o master inteiro num PNG 1080x1350
  zx-safezone arte.png                      # só audita, modo universal (1 asset p/ todos placements)
  zx-safezone arte.png --modo feed          # asset dedicado a Feed (sem overlay de Stories)
  zx-safezone arte.png --modo stories       # asset dedicado a Stories/Reels
  zx-safezone video.mp4                     # amostra frames ao longo do vídeo
  zx-safezone *.png --json                  # saída estruturada
  zx-safezone arte.png --no-overlay         # não gera o PNG de inspeção visual

Exit: 0 = todas aprovadas · 1 = alguma violação · 2 = erro de uso/arquivo

Estratégia recomendada (validada empiricamente contra artes reais de anúncio):
o master 4:5 NÃO se altera — ele vai pro Feed inteiro, como sempre — e o 9:16 de
Stories/Reels é DERIVADO por script, encaixando a arte inteira entre 14% e 75% da
altura. Nada é cortado nem coberto, as artes campeãs com preço queimado sobrevivem
intactas e a rotina de criação não muda. Desenhar os dois do zero entregaria o mesmo
resultado em Stories (o gargalo é a altura da faixa segura, não a largura) pelo dobro
do custo de geração.

O overlay `<nome>.safezone.png` desenha as faixas mortas sobre o criativo — abrir com Read
para a conferência visual. O número decide; o overlay explica.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
except ImportError:
    sys.stderr.write("erro: requer Pillow e numpy (pip3 install pillow numpy)\n")
    sys.exit(2)


# ── Modelo de safe-zone ──────────────────────────────────────────────────────
#
# Frações da dimensão do asset que ficam MORTAS (nada de informação crítica ali).
#
# Vertical (vale para todo asset destinado a Meta):
#   topo 14%  → foto/nome do perfil que o Meta desenha por cima em Stories/Reels
#   base 25%  → legenda + botão de CTA que o Meta injeta
#
# Horizontal: depende da razão do asset, porque o corte para 9:16 come as LATERAIS de
# qualquer asset mais largo. Largura preservada num cover para 9:16 = altura × 0.5625.
#   4:5  (0.800) → sobra 70.3% da largura → ~15% morto de cada lado
#   1:1  (1.000) → sobra 56.2% da largura → ~22% morto de cada lado
#   16:9 (1.778) → sobra 31.6% da largura → ~34% morto de cada lado
#   9:16 (0.5625)→ nada é cortado; 6% de margem só por estética/bordas de device
#
# O corte 4:5 → 1:1 (Feed do FB, Explore, Marketplace) tira 10% em cima e 10% embaixo —
# já coberto pelos 14%/25% verticais, que são mais rígidos.

TARGET_RATIO_916 = 9 / 16  # 0.5625
TARGET_RATIO_45 = 4 / 5    # 0.8000 — limite mais alto que o Feed aceita sem cortar
# Exportadores e metadados podem arredondar um ou dois pixels. A folga de 0,01 aceita
# razões até 0,790 sem acusar falso positivo, mas ainda separa com muita margem os masters
# medidos em produção: 997x1577 = 0,632 e 864x1821 = 0,474.
TOLERANCIA_RATIO_45 = 0.01

MODOS = {
    # modo:      (topo, base, extra_lateral_minimo, considera_crop_916, bloqueia)
    #
    # `bloqueia=False` = a faixa só some em posicionamento SECUNDÁRIO (o corte 4:5 → 1:1
    # de Explore/Marketplace). O Feed principal mostra o 4:5 inteiro, então reprovar aí
    # mataria toda arte campeã que usa a base pro preço. Reporta como aviso e passa.
    "universal": (0.14, 0.25, 0.06, True,  True),   # 1 asset servindo TODOS os posicionamentos
    "feed":      (0.10, 0.10, 0.06, False, False),  # master de Feed — Meta não cobre nada aqui
    "stories":   (0.14, 0.25, 0.06, False, True),   # asset 9:16 — o Meta desenha por cima
}

# Fração de pixels "com conteúdo" tolerada dentro de uma faixa morta.
# Calibrado contra artes reais de anúncio (medições na banda mais densa da faixa):
# texto/preço/selo dá 3,8-5,1% · fundo liso/pontilhado 0,00% · cena de vídeo com
# contorno grosso 1,8%. O limite fica no meio dessa separação.
LIMIAR_DENSIDADE = 0.025
# Intensidade de gradiente (0-255) para o pixel contar como "conteúdo". Alto de propósito:
# texto sobre fundo é transição extrema (200+), enquanto foto, gradiente e textura ficam
# na faixa média. Com 34 o helper reprovava qualquer vídeo com cena cheia.
LIMIAR_GRADIENTE = 90
# Faixa morta menor que isto (em px) não é avaliada — ruído de borda.
MIN_FAIXA_PX = 8
# Espessura da banda de medição. Texto ocupa poucas linhas, então a média da faixa inteira
# o dilui; medir banda a banda e ficar com a pior preserva a sensibilidade a uma única
# linha de legenda sem acusar conteúdo distribuído uniformemente.
BANDA_PX = 48
# Quando a faixa morta tem densidade parecida com a do MIOLO do criativo, o que está ali
# é a própria cena/fundo sangrando (vídeo de cena cheia, foto de fundo), não um texto
# destacado. Nesse caso o número não decide — vira aviso e o veredito é a conferência
# visual do overlay. Razão faixa/miolo acima disto = elemento destacado = bloqueio.
RAZAO_DESTAQUE = 1.35

# Ocupação mínima do espaço seguro pela arte derivada antes de valer mais a pena desenhar
# o 9:16 do zero. É medida como FRAÇÃO do espaço disponível (não como escala aplicada ao
# master), porque a escala varia com a resolução de exportação e a ocupação não: a mesma
# arte 4:5 em 1080x1350 ou em 2160x2700 gera pixels idênticos no canvas final.
# Master 4:5 ocupa ~0,99 · 1:1 ~0,81 · 16:9 ~0,46 (aí o nativo ganha).
OCUPACAO_MINIMA_DERIVACAO = 0.72

EXT_VIDEO = {".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv"}
FRAMES_VIDEO = 12  # amostras ao longo do vídeo


def _abrir_rgb(caminho: str) -> "Image.Image":
    """Abre a imagem já normalizada: orientação EXIF aplicada e alpha achatado.

    Sem o EXIF, JPEG de celular (foto gravada com a câmera do celular) é medido nos
    eixos trocados. Sem achatar o alpha, `convert("RGB")` descarta a transparência e um
    PNG RGBA com elemento sobre fundo transparente mede densidade zero — falso negativo,
    o pior modo de falha deste gate.
    """
    img = ImageOps.exif_transpose(Image.open(caminho))
    return _achatar(img)


def _achatar(img: "Image.Image") -> "Image.Image":
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        fundo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(fundo, rgba).convert("RGB")
    return img.convert("RGB")


def margens(w: int, h: int, modo: str):
    """Devolve (top, bottom, left, right) em PIXELS mortos para o asset dado."""
    topo_f, base_f, lat_min_f, considera_crop, _ = MODOS[modo]

    lat_f = lat_min_f
    if considera_crop:
        razao = w / h
        if razao > TARGET_RATIO_916:
            # asset mais LARGO que 9:16 → o cover corta as laterais
            lat_f = max(lat_min_f, (1 - TARGET_RATIO_916 / razao) / 2)
        elif razao < TARGET_RATIO_916:
            # asset mais ESTREITO que 9:16 → o cover corta topo e base ANTES do overlay,
            # então as faixas mortas verticais crescem pelo tanto que foi recortado
            v = razao / TARGET_RATIO_916
            corte = (1 - v) / 2
            topo_f = corte + topo_f * v
            base_f = corte + base_f * v

    return round(h * topo_f), round(h * base_f), round(w * lat_f), round(w * lat_f)


def densidade(px: "np.ndarray", eixo: str = "h") -> float:
    """Densidade de conteúdo da banda mais carregada da faixa.

    Mede o gradiente no canal RGB de maior variação, não na luminância: texto vermelho
    sobre verde de luminância equivalente vira cinza uniforme em escala de cinza e
    desapareceria da medição.

    `eixo='h'` para faixas horizontais (topo/base) → bandas em linhas;
    `eixo='v'` para laterais → bandas em colunas.
    """
    if px.size == 0 or px.shape[0] < 3 or px.shape[1] < 3:
        return 0.0
    g = px.astype(np.int16)
    if g.ndim == 2:
        g = g[:, :, None]
    dx = np.abs(np.diff(g, axis=1))[:-1, :, :]
    dy = np.abs(np.diff(g, axis=0))[:, :-1, :]
    forte = (dx + dy).max(axis=2) >= LIMIAR_GRADIENTE

    n = forte.shape[0] if eixo == "h" else forte.shape[1]
    passo = min(max(BANDA_PX, 1), n)
    pior = 0.0
    for i in range(0, n, passo):
        banda = forte[i:i + passo, :] if eixo == "h" else forte[:, i:i + passo]
        if banda.size:
            pior = max(pior, float(banda.mean()))
    return pior


def analisar_imagem(img: "Image.Image", modo: str, permitir_cena: bool = False):
    """Mede as 4 faixas mortas. Devolve (violacoes, medidas, geometria).

    `permitir_cena` só é ligado para VÍDEO, onde o quadro inteiro é imagem e a cena
    naturalmente ocupa as bordas. Em arte estática de oferta a faixa morta deve conter
    só fundo, então qualquer conteúdo ali é defeito — inclusive numa arte de miolo denso,
    que é justamente onde a comparação faixa-vs-miolo se perderia.
    """
    rgb = _achatar(img)
    w, h = rgb.size
    px = np.asarray(rgb)
    top, bottom, left, right = margens(w, h, modo)

    faixas = {
        "topo":     (px[:top, :, :],            top,    "h"),
        "base":     (px[h - bottom:, :, :],     bottom, "h"),
        "esquerda": (px[:, :left, :],           left,   "v"),
        "direita":  (px[:, w - right:, :],      right,  "v"),
    }

    miolo = densidade(px[top:h - bottom, left:w - right, :], "h")

    medidas, violacoes = {}, []
    cena_cheia = False
    for nome, (recorte, espessura, eixo) in faixas.items():
        if espessura < MIN_FAIXA_PX:
            medidas[nome] = 0.0
            continue
        d = densidade(recorte, eixo)
        medidas[nome] = round(d, 5)
        if d > LIMIAR_DENSIDADE:
            if permitir_cena and miolo > 0 and (d / miolo) < RAZAO_DESTAQUE:
                cena_cheia = True  # é a cena sangrando, não um texto solto
            else:
                violacoes.append(nome)

    geo = {
        "largura": w, "altura": h,
        "razao": round(w / h, 4),
        "morto_px": {"topo": top, "base": bottom, "esquerda": left, "direita": right},
        "area_util": f"{w - left - right}x{h - top - bottom}",
        "densidade_miolo": round(miolo, 5),
        "cena_cheia": cena_cheia,
    }
    return violacoes, medidas, geo


def gerar_overlay(img: "Image.Image", modo: str, destino: str):
    """Desenha as faixas mortas sobre o criativo, para inspeção visual com Read."""
    base = img.convert("RGB")
    w, h = base.size
    top, bottom, left, right = margens(w, h, modo)

    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    vermelho = (220, 38, 38, 110)
    for box in [
        (0, 0, w, top),
        (0, h - bottom, w, h),
        (0, 0, left, h),
        (w - right, 0, w, h),
    ]:
        d.rectangle(box, fill=vermelho)

    ambar = (217, 119, 6, 255)  # cor de destaque do contorno no overlay de conferência
    d.rectangle((left, top, w - right - 1, h - bottom - 1), outline=ambar, width=max(3, w // 300))

    out = Image.alpha_composite(base.convert("RGBA"), camada).convert("RGB")
    out.save(destino)
    return destino


# ── Derivação do asset 9:16 a partir do master ───────────────────────────────
# Variação de cor a partir da qual a borda conta como "complexa" e pede desfoque em vez
# de cor sólida. Fundo liso/pontilhado fica em ~2-14; borda com banner colorido, mockup
# escuro ou foto sangrando passa de 20. Calibrado empiricamente sobre artes reais.
LIMIAR_BORDA_LISA = 18.0


def _perfil_borda(rgb: "Image.Image", lado: str):
    """Devolve (é_lisa, cor_média) da borda superior ou inferior."""
    w, h = rgb.size
    faixa = max(8, round(h * 0.03))
    a = np.asarray(rgb, dtype=np.float32)
    amostra = (a[:faixa, :, :] if lado == "topo" else a[h - faixa:, :, :]).reshape(-1, 3)
    lisa = float(amostra.std(axis=0).mean()) < LIMIAR_BORDA_LISA
    cor = tuple(int(round(c)) for c in amostra.mean(axis=0))
    return lisa, cor


def _cor_fundo(rgb: "Image.Image"):
    """Cor dominante das bordas laterais — o fundo real da arte, não o do banner do topo.

    Usa a moda de uma paleta quantizada em vez da média: média entre creme e um banner
    preto devolve cinza, que não é a cor de fundo de arte nenhuma.
    """
    w, h = rgb.size
    faixa = max(8, round(w * 0.04))
    a = np.asarray(rgb, dtype=np.uint8)
    px = np.concatenate([a[:, :faixa, :].reshape(-1, 3), a[:, w - faixa:, :].reshape(-1, 3)])
    q = (px // 16).astype(np.int32)
    chaves = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    dominante = np.bincount(chaves).argmax()
    sel = px[chaves == dominante]
    return tuple(int(round(c)) for c in sel.mean(axis=0))


def _preencher(destino: "Image.Image", master: "Image.Image", box, lado: str, fundo):
    """Preenche uma sobra (topo ou base) do canvas 9:16.

    A sobra inteira é a cor de fundo da arte — assim as duas pontas do canvas combinam
    entre si. Se AQUELA borda for complexa (banner, mockup, foto sangrando), uma faixa
    curta de transição junto à arte dissolve o conteúdo até o fundo, para não deixar
    corte seco. A decisão é por borda porque é ali que a emenda aparece.
    """
    x0, y0, x1, y1 = box
    lw, lh = x1 - x0, y1 - y0
    if lw <= 0 or lh <= 0:
        return "—"
    destino.paste(Image.new("RGB", (lw, lh), fundo), (x0, y0))

    lisa, _ = _perfil_borda(master, lado)
    if lisa:
        return "cor sólida"

    trans_h = min(lh, max(24, round(lh * 0.38)))
    faixa_h = max(12, round(master.height * 0.10))
    recorte = (master.crop((0, 0, master.width, faixa_h)) if lado == "topo"
               else master.crop((0, master.height - faixa_h, master.width, master.height)))
    borrado = recorte.resize((lw, trans_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))

    # esmaece do fundo (longe da arte) até o conteúdo borrado (colado nela)
    # composite usa a 1a imagem onde a mascara e BRANCA. O gradiente nasce preto no topo
    # e branco na base, entao para a faixa do TOPO ele ja poe o fundo longe da arte e o
    # borrado colado nela -- e para a BASE precisa inverter.
    grad = Image.linear_gradient("L").resize((lw, trans_h))
    if lado == "topo":
        grad = grad.transpose(Image.FLIP_TOP_BOTTOM)
    mistura = Image.composite(Image.new("RGB", (lw, trans_h), fundo), borrado, grad)
    destino.paste(mistura, (x0, y1 - trans_h if lado == "topo" else y0))
    return "desfoque"


def derivar_stories(caminho: str, destino: str | None = None):
    """Gera o asset 9:16 de Stories/Reels a partir do master, sem cortar nada.

    A arte inteira entra entre 14% e 75% da altura — exatamente a faixa que o Meta não
    cobre com o perfil (topo) nem com legenda/botão (base). As sobras são preenchidas
    borda a borda.
    """
    master = _abrir_rgb(caminho)
    cw, ch = 1080, 1920
    topo_f, base_f, lat_f, _, _ = MODOS["stories"]
    top, bottom = round(ch * topo_f), round(ch * base_f)
    util_h = ch - top - bottom
    # a arte também não pode invadir a margem lateral que o modo stories reserva
    util_w = cw - 2 * round(cw * lat_f)

    k = min(util_w / master.width, util_h / master.height)
    nova = master.resize((max(1, round(master.width * k)), max(1, round(master.height * k))),
                         Image.LANCZOS)
    ax = (cw - nova.width) // 2
    ay = top + (util_h - nova.height) // 2

    fundo = _cor_fundo(master)
    canvas = Image.new("RGB", (cw, ch), fundo)
    t = _preencher(canvas, master, (0, 0, cw, ay), "topo", fundo)
    b = _preencher(canvas, master, (0, ay + nova.height, cw, ch), "base", fundo)
    canvas.paste(nova, (ax, ay))

    # OCUPAÇÃO, não a escala `k`: k depende da RESOLUÇÃO do master (a mesma arte 4:5
    # exportada em 1080x1350 e em 2160x2700 gera pixels idênticos no canvas, mas k cai
    # de 0,87 para 0,43). O que diz se a derivação serviu é quanto do espaço disponível
    # a arte preenche — isso é invariante à resolução.
    ocupacao = min(nova.width / util_w, nova.height / util_h)

    destino = destino or (os.path.splitext(caminho)[0] + "-9x16.png")
    canvas.save(destino)
    return destino, f"topo {t} · base {b}", round(ocupacao, 3)


def normalizar_4x5(caminho: str, destino: str | None = None):
    """Encaixa o master inteiro num canvas 1080x1350, sem crop e sem sobrescrevê-lo.

    Um crop de 997x1577 para 4:5 descartaria 21% da altura — justamente onde preço e CTA
    costumam estar. O fit usa o menor fator de escala, centraliza a arte e reaproveita o
    mesmo preenchimento adaptativo do 9:16: cor sólida em borda lisa, transição desfocada
    quando banner, mockup ou foto encostam na emenda.
    """
    master = _abrir_rgb(caminho)
    razao = master.width / master.height
    if abs(razao - TARGET_RATIO_45) <= TOLERANCIA_RATIO_45:
        return None, "já estava em 4:5", round(razao, 4)

    cw, ch = 1080, 1350
    k = min(cw / master.width, ch / master.height)
    nova = master.resize((max(1, round(master.width * k)), max(1, round(master.height * k))),
                         Image.LANCZOS)
    ax = (cw - nova.width) // 2
    ay = (ch - nova.height) // 2

    fundo = _cor_fundo(master)
    canvas = Image.new("RGB", (cw, ch), fundo)
    t = _preencher(canvas, master, (0, 0, cw, ay), "topo", fundo)
    b = _preencher(canvas, master, (0, ay + nova.height, cw, ch), "base", fundo)

    # Masters altos deixam sobra nas LATERAIS. Girar temporariamente canvas e master
    # permite usar `_preencher` sem duplicar sua decisão calibrada — e `_preencher`, por
    # sua vez, consulta `_perfil_borda` para escolher cor sólida ou desfoque. Depois da
    # volta, o "topo" girado é a direita original e a "base" é a esquerda.
    girado = canvas.transpose(Image.Transpose.ROTATE_90)
    master_girado = master.transpose(Image.Transpose.ROTATE_90)
    margem_direita = cw - ax - nova.width
    d = _preencher(girado, master_girado, (0, 0, ch, margem_direita),
                   "topo", fundo)
    e = _preencher(girado, master_girado, (0, cw - ax, ch, cw),
                   "base", fundo)
    canvas = girado.transpose(Image.Transpose.ROTATE_270)
    canvas.paste(nova, (ax, ay))

    destino = destino or (os.path.splitext(caminho)[0] + "-4x5.png")
    canvas.save(destino)
    preenchimento = f"topo {t} · base {b} · esquerda {e} · direita {d}"
    return destino, preenchimento, round(razao, 4)


def frames_do_video(caminho: str, tmpdir: str):
    """Extrai amostras uniformes do vídeo. Devolve lista de (rotulo, Image)."""
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg/ffprobe não encontrados no PATH")
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", caminho],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        dur = float(dur)
    except ValueError:
        raise RuntimeError("não consegui ler a duração do vídeo")

    saida = []
    for i in range(FRAMES_VIDEO):
        t = dur * (i + 0.5) / FRAMES_VIDEO
        png = os.path.join(tmpdir, f"f{i:02d}.png")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", caminho,
             "-frames:v", "1", "-y", png],
            check=True,
        )
        if os.path.exists(png):
            saida.append((f"t={t:.1f}s", Image.open(png)))
    return saida


def checar(caminho: str, modo: str, overlay: bool):
    e_video = os.path.splitext(caminho)[1].lower() in EXT_VIDEO

    piores, geo, violado = {}, None, set()
    overlay_path = None

    if e_video:
        with tempfile.TemporaryDirectory() as tmp:
            frames = frames_do_video(caminho, tmp)
            if not frames:
                raise RuntimeError("nenhum frame extraído")
            pior_frame, pior_score = None, -1.0
            for rotulo, img in frames:
                v, m, g = analisar_imagem(img, modo, permitir_cena=True)
                geo = geo or g
                violado |= set(v)
                for k, val in m.items():
                    if val > piores.get(k, -1):
                        piores[k] = val
                score = max(m.values()) if m else 0
                if score > pior_score:
                    pior_score, pior_frame = score, (rotulo, img.copy())
            if overlay and pior_frame:
                overlay_path = os.path.splitext(caminho)[0] + ".safezone.png"
                gerar_overlay(pior_frame[1], modo, overlay_path)
    else:
        img = _abrir_rgb(caminho)
        v, piores, geo = analisar_imagem(img, modo)
        violado = set(v)
        if overlay:
            overlay_path = os.path.splitext(caminho)[0] + ".safezone.png"
            gerar_overlay(img, modo, overlay_path)

    bloqueia = MODOS[modo][4]
    # Proporção é um eixo independente da densidade. Em especial, `feed` mantém
    # `bloqueia=False` para não matar arte campeã com preço na base, mas um master mais
    # alto que 4:5 é cortado pelo próprio Feed e precisa falhar mesmo assim. Vídeo e
    # Stories ficam fora: 9:16 é legítimo nos dois casos.
    checa_proporcao = not e_video and modo in ("feed", "universal")
    razao_exata = geo["largura"] / geo["altura"]
    proporcao_ok = (razao_exata >= TARGET_RATIO_45 - TOLERANCIA_RATIO_45
                    if checa_proporcao else None)
    violacao_proporcao = None
    if proporcao_ok is False:
        violacao_proporcao = {
            "razao_encontrada": round(razao_exata, 4),
            "razao_esperada": TARGET_RATIO_45,
            "tolerancia": TOLERANCIA_RATIO_45,
            "dimensao_atual": f"{geo['largura']}x{geo['altura']}",
        }
    bloqueia_proporcao = proporcao_ok is False and modo == "feed"
    return {
        "arquivo": caminho,
        "tipo": "video" if e_video else "imagem",
        "modo": modo,
        "ok": not ((violado and bloqueia) or bloqueia_proporcao),
        "severidade": "bloqueio" if bloqueia else "aviso",
        "violacoes": sorted(violado),
        "proporcao_ok": proporcao_ok,
        "violacao_proporcao": violacao_proporcao,
        "severidade_proporcao": ("bloqueio" if bloqueia_proporcao
                                 else "aviso" if proporcao_ok is False else None),
        "densidade": piores,
        "limiar": LIMIAR_DENSIDADE,
        "geometria": geo,
        "overlay": overlay_path,
    }


def main():
    p = argparse.ArgumentParser(
        description="QA de safe-zone de criativo de anúncio (Meta) — estático, animado ou vídeo.",
        epilog="Faixas mortas: topo 14%% (perfil) · base 25%% (legenda + CTA) · laterais conforme o corte 9:16.",
    )
    p.add_argument("arquivos", nargs="+", help="PNG/JPG/MP4 a verificar")
    p.add_argument("--modo", choices=sorted(MODOS), default="universal",
                   help="universal (default): 1 asset p/ todos os posicionamentos · "
                        "feed: asset dedicado a Feed · stories: asset nativo 9:16")
    p.add_argument("--derivar", action="store_true",
                   help="gerar o asset 9:16 de Stories/Reels a partir do master "
                        "(a arte inteira entra na faixa segura; nada é cortado)")
    p.add_argument("--normalizar", action="store_true",
                   help="encaixar a imagem inteira num PNG 1080x1350, sem crop; "
                        "não sobrescreve o master")
    p.add_argument("--json", action="store_true", help="saída JSON")
    p.add_argument("--no-overlay", action="store_true", help="não gerar o PNG de inspeção")
    args = p.parse_args()

    # Com --derivar ou --normalizar, o master 4:5 é auditado como asset de FEED (é o que
    # ele vai ser) e o 9:16 nasce já dentro da faixa segura — auditar esse master como
    # universal reprovaria justamente as artes campeãs que a rotina existe para preservar.
    def modo_de(caminho):
        # As flags só rebaixam o modo de IMAGEM. Vídeo não é derivado nem normalizado,
        # então rebaixá-lo para `feed` — que não bloqueia densidade — deixaria passar
        # violação real num glob misto de png e mp4.
        if args.modo != "universal" or not (args.derivar or args.normalizar):
            return args.modo
        ext = os.path.splitext(caminho)[1].lower()
        return args.modo if ext in EXT_VIDEO else "feed"

    resultados, falhou = [], False
    for caminho in args.arquivos:
        if not os.path.exists(caminho):
            sys.stderr.write(f"erro: arquivo não encontrado: {caminho}\n")
            sys.exit(2)
        try:
            fonte = caminho
            normalizado, preenchimento_4x5, razao_original = None, None, None
            if args.normalizar:
                if os.path.splitext(caminho)[1].lower() in EXT_VIDEO:
                    raise RuntimeError("--normalizar aceita apenas imagens")
                normalizado, preenchimento_4x5, razao_original = normalizar_4x5(caminho)
                fonte = normalizado or caminho

            r = checar(fonte, modo_de(fonte), not args.no_overlay)
            if args.normalizar:
                r.update({
                    "arquivo_original": caminho,
                    "normalizado_4x5": normalizado,
                    "normalizacao_gerada": normalizado is not None,
                    "preenchimento_4x5": preenchimento_4x5,
                    "razao_original": razao_original,
                })
            if args.derivar and r["tipo"] == "imagem":
                # Quando as duas flags são usadas, `fonte` já aponta para o 4:5. Assim o
                # 9:16 nunca nasce do master alto que o Feed cortaria.
                destino, preenchimento, ocupacao = derivar_stories(fonte)
                d = checar(destino, "stories", False)
                # Cascata A → C: a derivação é o caminho barato, mas não serve a qualquer
                # master. Se o 9:16 derivado reprova no QA, ou se coube tão apertado que o
                # texto ficaria ilegível, o certo é desenhar o 9:16 do zero em vez de
                # gastar tentativa atrás de tentativa ajustando a derivação.
                apertado = ocupacao < OCUPACAO_MINIMA_DERIVACAO
                r.update({
                    "derivado_916": destino,
                    "preenchimento": preenchimento,
                    "ocupacao_derivacao": ocupacao,
                    "derivado_ok": d["ok"] and not apertado,
                    "gerar_nativo": (not d["ok"]) or apertado,
                    "motivo_nativo": ("derivado reprovou no QA" if not d["ok"]
                                      else f"arte ocupa só {ocupacao:.0%} do espaço seguro — texto "
                                           "perde legibilidade" if apertado else None),
                })
                falhou = falhou or r["gerar_nativo"]
        except Exception as e:  # noqa: BLE001 — qualquer falha de leitura reprova, não passa batido
            sys.stderr.write(f"erro ao analisar {caminho}: {e}\n")
            sys.exit(2)
        resultados.append(r)
        falhou = falhou or not r["ok"]

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    else:
        for r in resultados:
            g = r["geometria"]
            nome = os.path.basename(r["arquivo"])
            cab = f"[{g['largura']}x{g['altura']}, modo={r['modo']}]"
            if r["violacao_proporcao"]:
                vp = r["violacao_proporcao"]
                marca = "❌" if r["severidade_proporcao"] == "bloqueio" else "⚠️ "
                print(f"{marca} {nome}  {cab} proporção {vp['razao_encontrada']:.3f} "
                      f"em {vp['dimensao_atual']}; esperado 4:5 "
                      f"({vp['razao_esperada']:.3f}, tolerância {vp['tolerancia']:.3f})")
                print(f"     → rode: zx-safezone {r['arquivo']} --normalizar")
            if not r["violacoes"] and not r["violacao_proporcao"]:
                print(f"✅ {nome}  {cab} área útil {g['area_util']}")
                if g.get("cena_cheia"):
                    print("     ⚠️  cena/fundo ocupa a faixa morta — nenhum texto solto "
                          "detectado, mas confira o overlay para garantir")
            elif r["violacoes"]:
                marca = "❌" if r["severidade"] == "bloqueio" else "⚠️ "
                onde = ("faixa que o Meta cobre/corta" if r["severidade"] == "bloqueio"
                        else "faixa cortada só no crop 1:1 (Explore/Marketplace)")
                print(f"{marca} {nome}  {cab} conteúdo em {onde}: "
                      f"{', '.join(r['violacoes'])}")
                for faixa in r["violacoes"]:
                    px = g["morto_px"][faixa]
                    print(f"     · {faixa}: densidade {r['densidade'][faixa]:.3%} "
                          f"(limite {r['limiar']:.1%}) — {px}px")
            if "normalizacao_gerada" in r:
                if r["normalizacao_gerada"]:
                    print(f"     ✅ 4:5 normalizado: {r['normalizado_4x5']} "
                          f"(1080x1350; {r['preenchimento_4x5']})")
                else:
                    print(f"     ✅ 4:5: o master já está correto "
                          f"(proporção {r['razao_original']:.3f}); nenhum arquivo gerado")
            if r.get("derivado_916"):
                marca = "✅" if r.get("derivado_ok") else "❌"
                print(f"     {marca} 9:16 de Stories: {r['derivado_916']} "
                      f"({r['preenchimento']}, ocupa {r['ocupacao_derivacao']:.0%})")
                if r.get("gerar_nativo"):
                    print(f"     → DERIVAÇÃO NÃO SERVE aqui ({r['motivo_nativo']}). "
                          "Gerar o 9:16 NATIVO do zero, com o layout pensado para "
                          "1080x1920 e tudo entre 14% e 75% da altura.")
            if r["overlay"]:
                print(f"     overlay: {r['overlay']}")
        bloqueio_proporcao = any(
            r["violacao_proporcao"] and r["severidade_proporcao"] == "bloqueio"
            for r in resultados
        )
        if falhou and bloqueio_proporcao:
            print("\nO Feed corta assets mais altos que 4:5. Rodar --normalizar para "
                  "preservar todo o conteúdo em 1080x1350 — não subir assim.")
        elif falhou:
            print("\nO Meta cobre ou corta essas faixas. Regerar com a informação crítica "
                  "dentro do retângulo âmbar do overlay — não subir assim.")

    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
