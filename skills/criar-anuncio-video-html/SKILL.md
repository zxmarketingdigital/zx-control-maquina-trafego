---
name: criar-anuncio-video-html
description: "Cria anúncio em VÍDEO construído em HTML/CSS animado e renderizado num MP4 9:16 (1080x1920) pronto pro Meta — com telas roteirizadas (terminal/código, chat de WhatsApp, oferta, CTA), headline fixa, safe-zone garantida por QA, música de fundo + sonoplastia (digitação, caixa registradora) mixadas via ffmpeg, e suporte a MÚLTIPLAS VARIAÇÕES pra teste A/B. Use SEMPRE que o usuário pedir anúncio em vídeo HTML, vídeo animado com telas de terminal/WhatsApp/oferta, anúncio 9:16 com música e sonoplastia, ou variações de vídeo pra teste. NÃO usar quando a pessoa quer vídeo com pessoa/avatar/narração falada (isso é a skill de vídeo com HiggsField)."
model: sonnet
effort: medium
---

# Criar Anúncio em Vídeo HTML → MP4 (9:16, Meta)

Gera criativos de anúncio de vídeo **construídos em HTML/CSS/JS animado** e renderizados num **MP4 1080×1920** com áudio embutido, prontos pra subir no Meta. Ideal pra anúncios roteirizados e cheios de TEXTO (terminal/código, mock de chat de WhatsApp, oferta com lista, CTA) — onde HTML dá controle pixel-perfeito e fidelidade de texto que gerador de IA não dá. Suporta várias **variações** num único motor pra teste A/B.

## Quando usar / não usar
- **Usar:** anúncio com telas de UI/roteiro (terminal, WhatsApp, oferta, CTA), muito texto, precisa de precisão de safe-zone, teste A/B de ângulos.
- **NÃO usar:** vídeo com pessoa falando / avatar / narração com lip-sync → skill de vídeo com HiggsField. Este aqui é **sem pessoa e sem voz** (só música + SFX), salvo pedido.

## Regras inegociáveis (safe-zone)
Formato **9:16 (1080×1920)** — o posicionamento mais restritivo.
- **Headline fixa no topo de TODAS as telas**, dentro da faixa segura.
- Toda info crítica entre **~14% (269px) e ~75% (1440px)** da altura. Livres: topo ~14% (perfil) e base ~25% (legenda + botão "Saiba mais" que o Meta injeta).
- Na tela de CTA **não desenhar botão na base** — apontar (seta ▼) pro botão real do Meta.
- **QA programático OBRIGATÓRIO antes de entregar:** `node qa-bounds.mjs` tem que dar ✅ pra TODAS as variações (mede bounding box de cada elemento visível vs 269/1440). Não é opcional.
- **O `qa-bounds.mjs` continua sendo o GATE desta skill** — ele mede o bounding box real de cada elemento no DOM, com opacidade herdada, então é **mais preciso** que qualquer análise de pixel: sabe onde o elemento está mesmo quando ele é escuro, transparente ou está fora da janela. Não substituir.
- O helper global `~/bin/zx-safezone` é o gate **universal das outras skills de vídeo** (que não têm DOM pra medir). Aqui ele é opcional, como **conferência extra no MP4 final** — pega o que o DOM não vê (letterbox, escala errada no encode, legenda queimada no ffmpeg): `zx-safezone anuncio-a.mp4 --modo stories`.

## Arquitetura (por que assim)
Pipeline determinístico **HTML → frames → MP4 → mux de áudio**. NUNCA screen-record em tempo real (impreciso, quebra o QA). A animação é dirigida por um relógio virtual `window.seek(tMs)` → cada frame é exato.

| Arquivo | Papel |
|---------|-------|
| `ad.html` | Motor autocontido 1080×1920. Lê `window.__VARIANT` (headline, ordem das cenas, subtítulo). Expõe `window.seek(t)` e `window.__audio()` (tempos de digitação/caixa derivados da ordem). 4 cenas: terminal / whatsapp / offer / cta. |
| `variants.mjs` | Array de variações (id, ângulo, headline, `order`, `scene1sub`, `headlineSize`). Uma variação = um MP4. |
| `render.mjs` | Puppeteer (usa o Chrome instalado, `puppeteer-core`) captura 660 frames/variante (30fps, 22s) em `frames-<id>/` + escreve `timings.sh`. `node render.mjs <id>` renderiza só uma. |
| `build.sh` | Sintetiza SFX (digitação = cliques; caixa registradora = ka-ching de sinos) com ffmpeg, junta frames→vídeo (h264/yuv420p) e mixa música + SFX nos tempos do `timings.sh` → `anuncio-<id>.mp4`. |
| `qa-bounds.mjs` | QA de safe-zone das variações (varre a timeline, opacidade herdada). Exit 1 se violar. |

Música de fundo: coloque trilhas CC0 em `assets/trilhas-cc0/`, relativa ao diretório do `build.sh`. O arquivo padrão esperado é `arcade-funk.mp3`; para usar outro nome, troque uma linha no `build.sh` (var `MUSIC`).

## Pré-requisitos (verificar antes de começar)
- **Node >= 18**: `node --version`
- **Chrome/Chromium instalado** e acessível: `google-chrome --version` ou `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version`. Se em path não-padrão, setar `export CHROME_PATH=/caminho/para/chrome` antes de rodar render.mjs e qa-bounds.mjs.
- **ffmpeg instalado**: `ffmpeg -version`
- **Trilha CC0 disponível antes do primeiro build:** crie `assets/trilhas-cc0/` dentro da pasta da skill/template e coloque ali pelo menos um arquivo `.mp3` licenciado como CC0. É possível encontrar músicas em catálogos públicos como `freesound.org` e `incompetech.com`; confirme a licença CC0 da faixa escolhida. Se o arquivo não se chamar `arcade-funk.mp3`, edite a variável `MUSIC` no `build.sh` com o nome exato.

## Passo a passo
1. **Copiar o template** pra pasta do projeto: `cp -R <caminho-da-skill>/template/. <pasta>/` e `cd <pasta>`. Crie `assets/trilhas-cc0/` nessa pasta e adicione a trilha CC0 antes do primeiro build.
2. **Instalar o capturador** (1x por pasta): `npm init -y >/dev/null && npm i puppeteer-core@23`.
3. **Editar o conteúdo** em `ad.html` (telas: código do terminal, balões do WhatsApp, os bullets EXATOS da oferta com preço âncora→final, textos do CTA) e as **variações** em `variants.mjs` (headline/ordem/ângulo por variação). Dentro da pasta do produto, procurar `CLAUDE.md`, `README`, LP ou arquivo de copy para obter bullets e preços reais. **NUNCA inventar bullets ou preço.** Também editar a variável `MUSIC` no `build.sh` com uma trilha CC0 disponível.
4. **QA cedo (barato):** `node qa-bounds.mjs` → tem que dar ✅ em todas as variações. Se estourar, compactar a cena densa (fontes/gaps/padding) e repetir.
5. **Renderizar:** `node render.mjs` (todas) — o tempo depende da máquina e da quantidade de variações.
6. **Montar:** `./build.sh` → `anuncio-a.mp4`, `anuncio-b.mp4`, … (limpa os `mudo-*.mp4` sozinho).
7. **Verificar o MP4:** `ffprobe` (h264/yuv420p/aac, 1080×1920, 22s) + medir áudio por janela com `volumedetect` (a **caixa registradora deve ser o pico** no momento do "pagou"; digitação na cena de terminal; música com fade-out). Extrair 1 frame no momento da caixa e conferir o 💰. Lembrete: `volumedetect` só imprime sem `-v error` (sai em nível info).
8. **Entregar** os MP4s e abrir no player. **NÃO** subir campanha nem disparar nada — entrega é o arquivo pra aprovação.

## Padrão de variações pra teste A/B (bom default)
Mesma oferta/CTA, muda o ÂNGULO/hook (isola a variável): **aspiração** (headline de resultado), **resultado-primeiro** (abre no WhatsApp com a caixa registradora nos 3 primeiros segundos), **quebra de objeção** ("sem saber programar"). A ordem das cenas em `variants.mjs` também é testável — o áudio se ajusta sozinho (`window.__audio()`).

## Estrutura fixa do motor
As **4 cenas (terminal/whatsapp/offer/cta) e os 4 slots de 6s cada são fixos**. Não é possível remover ou adicionar cenas sem refatorar `ad.html` e `render.mjs`. Sempre usar todas as 4 na `order`, mesmo que a cena de terminal precise ser adaptada para outro tipo de UI (ex: mock de dashboard ou tela de app).

O campo `scene1sub` em `variants.mjs` é o subtítulo exibido **na cena do terminal especificamente** — se a `order` mudar e `terminal` não for o slot 0, o subtítulo ainda renderiza no slot correto, mas o texto deve fazer sentido pro contexto do terminal.

## Armadilhas conhecidas (já resolvidas no template)
- **zsh não faz word-split** de variável sem aspas → medir áudio com chamadas explícitas, não `set -- $x` em loop.
- **aevalsrc do ffmpeg** não aceita `<`/`>` → usar `lt()`/`gt()`.
- **Fontes:** aguardar `document.fonts.ready` antes de capturar (Google Fonts Inter + JetBrains Mono).
- **__VARIANT** tem que ser setado com `page.evaluateOnNewDocument` ANTES do `goto` (o script lê no load).
- **`-v error`** no ffmpeg suprime a saída do `volumedetect`.
- **Bullets/preço da oferta são hardcoded no ad.html** (seção s3, marcada com comentário "CONTEÚDO DO PRODUTO") — editar manualmente ao trocar de produto; variants.mjs NÃO controla esses valores.
- **MUSIC no build.sh aponta para `assets/trilhas-cc0/`**, dentro da pasta do template — verificar e ajustar o nome do arquivo antes do primeiro build; o script falha com mensagem clara se a trilha não existir.
- **QA e render precisam de Chrome** em `/Applications/Google Chrome.app/...` (macOS padrão) ou setar `CHROME_PATH` no ambiente: `export CHROME_PATH=/caminho/para/chrome`.

## Design e marca
Adapte `ad.html` às cores da SUA marca — o motor não impõe paleta.
