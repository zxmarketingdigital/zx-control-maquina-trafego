---
name: criar-anuncio-video-momentum
description: "Cria anúncio em VÍDEO no formato 'Momentum' — 9:16 (1080x1920) pro Meta, feito em Remotion (React→MP4). Formato com MOVIMENTO: tipografia cinética (palavras entrando com spring), contador de faturamento animado (R$ subindo), gráfico de barras crescendo data-driven, confete/partículas e transições reais entre cenas (slide/wipe/fade). Config-driven: edita 1 arquivo (src/content.ts) com a copy/oferta e renderiza. Use SEMPRE que o Rafael disser: criar anúncio momentum, anúncio no formato momentum, vídeo de anúncio com contador/gráfico animado, anúncio kinetic, anúncio com número subindo, vídeo de anúncio com transições, anúncio com dados crescendo, criar anúncio remotion, vídeo de anúncio com movimento. NÃO usar quando o Rafael quer telas de UI roteirizadas tipo terminal/WhatsApp (isso é criar-anuncio-video-html) nem vídeo com pessoa/narração falada (isso é criar-anuncio-video-gemini-omni)."
model: sonnet
effort: medium
---

# Criar Anúncio em Vídeo — Formato "Momentum" (Remotion → MP4 9:16)

Gera criativo de tráfego Meta no formato **Momentum**: um anúncio **animado** feito em **Remotion** (React renderizado pra MP4 1080×1920). É o formato "dashboard vivo / número subindo / dado crescendo" — a linguagem que **HTML+ffmpeg faz mal e o Remotion faz bem**.

O template é um motor genérico e data-driven: a copy e a oferta ficam concentradas em `src/content.ts`, enquanto as cenas, transições e animações permanecem reutilizáveis.

## Quando usar (e quando NÃO)

- **USAR:** anúncio com **movimento** — contador de faturamento subindo, gráfico crescendo, tipografia cinética, confete, transições entre cenas. Bom pra hook aspiracional e prova de resultado.
- **NÃO usar** → outra skill:
  - Telas de UI roteirizadas (terminal digitando, mock de WhatsApp, oferta em lista) → `criar-anuncio-video-html`.
  - Vídeo com pessoa / avatar / narração falada → `criar-anuncio-video-gemini-omni`.

## As 4 cenas (fixas, com transições)

1. **Hook** — tipografia cinética, palavras entrando com spring, linha-chave em âmbar.
2. **Counter** — "FATURAMENTO / MÊS" com número animado (0 → target) + gráfico de barras crescendo (última barra destacada).
3. **Offer** — preço âncora riscado → preço final gigante estourando + **confete** + chips de bônus deslizando.
4. **CTA** — headline + botão pulsando + seta ▼ apontando pro botão "Saiba mais" do Meta.

Transições: Hook→Counter (slide de baixo), Counter→Offer (wipe), Offer→CTA (fade). Fundo com gradiente âmbar em movimento. Duração ~17,7s (530 frames @30fps).

## Pré-requisitos

- Node.js instalado.
- Dependências npm instaladas dentro da pasta do template com `npm install`.
- TypeScript 5.x. O TS 7.x quebra o bundler do Remotion (`ts.sys` undefined); o `package.json` já pina `typescript@^5.9` — se `npm install` puxar 7, rodar `npm i -D typescript@5`.
- ffmpeg/ffprobe disponíveis no sistema para o render do Remotion.

## Pipeline

1. **Copiar o template** pra dentro da pasta do produto (ou uma pasta nova):
   ```bash
   cp -R ~/.claude/skills/criar-anuncio-video-momentum/template ~/projetos/{slug}/momentum-ad
   cd ~/projetos/{slug}/momentum-ad && npm install
   ```
2. **Editar SÓ `src/content.ts`** — hook (4 linhas), contador (label/target/barras), oferta (pre/preço âncora/preço final/chips), CTA (headline/botão/hint). **NUNCA inventar bullets ou preço** — puxar da LP / `CLAUDE.md` do produto. Se não achar, perguntar ao Rafael.
3. **Preview no Studio** (opcional, recomendado):
   ```bash
   ./node_modules/.bin/remotion studio   # localhost:3000 — scrub na timeline pra ver o movimento
   ```
4. **Renderizar:**
   ```bash
   PATH="/opt/homebrew/bin:$PATH" ./node_modules/.bin/remotion render Momentum out/momentum.mp4
   ```
5. **QA de safe-zone — gate programático, não 1 frame no olho:**
   ```bash
   zx-safezone out/momentum.mp4 --modo stories   # exit 0 = aprovado · exit 1 = violação
   ```
   O helper global `~/bin/zx-safezone` amostra 12 frames ao longo da timeline — essencial aqui, porque as 4 cenas têm layouts diferentes e elementos que ENTRAM em movimento (spring, confete, contador): um frame só nunca prova o vídeo inteiro. Gera `out/momentum.safezone.png` pra abrir com Read quando reprovar.
   ⚠️ As constantes `SAFE_TOP = 0.14` / `SAFE_BOTTOM = 0.75` em `src/theme.ts` **declaram a intenção** e devem ser respeitadas ao posicionar as cenas — mas quem **verifica** o MP4 renderizado é o helper. Elemento animado pode invadir a faixa morta mesmo com as constantes certas no theme. Exit 1 → ajustar a cena e re-renderizar antes de subir.
6. **Subir no Meta** seguindo o fluxo de publicação e rastreamento de campanhas do projeto.

## Variações A/B (opcional)

Pra testar ângulos: duplicar a pasta com `content.ts` diferente (muda hook/headline), OU parametrizar via `inputProps` + `--props` (registrar a composition recebendo props). Mesma oferta, hook diferente = isola a variável.

## Gotchas (aprendidos na construção — NÃO repetir)

- **TypeScript tem que ser 5.x.** O TS 7.x (compilador nativo novo) quebra o bundler do Remotion (`ts.sys` undefined). O `package.json` já pina `typescript@^5.9` — se `npm install` puxar 7, rodar `npm i -D typescript@5`.
- **Nunca criar 2 arquivos com nome que só difere no case** (ex: `Captions.tsx` × `captions.ts`). O filesystem do macOS é case-insensitive → os dois resolvem pro mesmo arquivo e o import vira `undefined` (React error #130). Por isso o helper é `Segments.tsx`, dados em `content.ts`.
- **`npx` é reescrito pelo hook RTK** ("Missing script") → sempre chamar `./node_modules/.bin/remotion`.
- **ffmpeg/ffprobe:** usar `/opt/homebrew/bin` direto (RTK às vezes engole a saída).
- **Fontes:** já carregadas via `@remotion/google-fonts` (Inter + JetBrains Mono) — garante `fonts.ready` no render headless, não precisa `<link>`.
- **Confete é determinístico** (PRNG por índice em `util.ts`) — estável entre frames; não usar `Math.random` por partícula.

## Design System

Âmbar `#D97706` + Inter + JetBrains Mono. Os tokens ficam em `src/theme.ts` — não inventar cor/fonte.

## Estrutura do template

- `src/content.ts` — **o único arquivo que você edita** (copy/oferta)
- `src/Root.tsx` / `src/index.ts` — registra a composition `Momentum`
- `src/theme.ts` — tokens + fontes
- `src/momentum/Momentum.tsx` — monta as cenas + transições + fundo animado
- `src/momentum/{HookScene,CounterScene,OfferScene,CtaScene}.tsx` — as 4 cenas
- `src/momentum/Confetti.tsx` · `Segments.tsx` · `util.ts` — helpers
