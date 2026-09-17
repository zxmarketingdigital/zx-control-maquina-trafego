---
name: gerar-video-mp4
description: "Gera vídeo MP4 a partir de animação HTML via pipeline puppeteer + Chrome headless + ffmpeg. Use SEMPRE que o usuário disser: gerar video, criar mp4, exportar mp4, render mp4, animação para reels, hero animation, criativo animado, video para anuncio, video para feed, video stories, animação produto, video promocional, animar landing page, animar lp, criar criativo video, gerar criativo, mp4 instagram, video tiktok, video youtube short, animação curso, video curso, vídeo demo."
model: sonnet
effort: medium
---

# Render de Vídeo MP4 a partir de HTML Animado

Gera vídeo visual gráfico a partir de uma animação HTML usando Puppeteer, Chrome headless e ffmpeg. É apropriado para Reels, Stories, TikTok, Feed, YouTube, hero de landing page, criativos de anúncio e demos de produto.

## Quando usar

Sempre que o usuário pedir vídeo MP4 visual gráfico, incluindo:

- Reels ou Feed vertical;
- Stories ou TikTok;
- YouTube hero ou animação em 16:9;
- Hero animation para landing page;
- Criativo de anúncio;
- Demo de produto.

## Não usar quando

- Animação terminal ASCII com spinners ou progress bars → usar `/criar-demo-skill`.
- Vídeo de pessoa falando ou screen recording → usar `/video-use`.
- Cortes de masterclass ou reunião → usar a skill específica de cortes disponível no ambiente.

## Pipeline obrigatório

### 1. Setup da pasta do projeto

```bash
PROJ=~/projetos/<slug>/<subpasta>  # ou ~/projetos/<slug>-video/
mkdir -p "$PROJ"/{frames,out,assets}
```

Se houver mockups, screenshots ou imagens reais relacionadas, copiá-los para `$PROJ/assets/`. **Anti-AI-slop:** nunca recriar produtos ou UIs com CSS/SVG quando houver JPG/PNG real disponível.

### 2. Criar `scene.html`

Estrutura obrigatória do HTML:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>...</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  /* DIMENSÃO FIXA — usar a dimensão alvo */
  html, body { width:1080px; height:1350px; overflow:hidden; }
  /* Design system do projeto ou DESIGN.md local */
</style>
</head>
<body>
<div id="stage">
  <!-- cenas com .scene -->
</div>
<script>
const DURATION = 10.0;  // segundos
const scenes = [...];

window.SET_TIME = function(t) {
  // Controla TODAS as animações baseado em t (0..DURATION)
  // CSS keyframes/transitions não funcionam no render headless
  // Tudo via JS, ajustando opacity, transform etc.
};

if (!window.HEADLESS) {
  let start = performance.now();
  function loop(now) {
    let t = ((now - start) / 1000) % DURATION;
    window.SET_TIME(t);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
}
window.SET_TIME(0);
</script>
</body>
</html>
```

**Regras críticas do HTML:**

- `window.SET_TIME(t)` deve controlar todo movimento; não usar `@keyframes` ou `transition`, pois não são confiáveis na captura frame a frame.
- Definir funções de easing inline, como `easeOutCubic = x => 1 - Math.pow(1-x, 3)`.
- Fazer stagger reveals com `.forEach((el, i) => { delay = i*0.16 })`.
- Definir `window.HEADLESS = true` via Puppeteer para desligar o loop de `requestAnimationFrame`.
- Ao usar fontes Google, aguardar 2s no render para não capturar fontes fallback.

### 3. Criar `render.mjs`

```js
import { fileURLToPath, pathToFileURL } from 'url';
import { createRequire } from 'module';
import { spawnSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// puppeteer-core: usa o diretório compartilhado do setup quando existir; senão, o do projeto.
async function loadPuppeteer() {
  const shared = path.join(os.homedir(), '.operacao-ia', 'tools', 'puppeteer', 'package.json');
  if (fs.existsSync(shared)) {
    const entry = createRequire(shared).resolve('puppeteer-core');
    return (await import(pathToFileURL(entry).href)).default;
  }
  return (await import('puppeteer-core')).default;
}

// Chrome por sistema: CHROME_PATH > macOS > Windows > Linux.
function resolveChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  if (process.platform === 'darwin') return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (process.platform === 'win32') {
    const bases = [process.env.PROGRAMFILES, process.env['PROGRAMFILES(X86)'], process.env.LOCALAPPDATA].filter(Boolean);
    for (const base of bases) {
      const exe = path.win32.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe');
      if (fs.existsSync(exe)) return exe;
    }
  } else {
    for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
      for (const dir of (process.env.PATH || '').split(path.delimiter).filter(Boolean)) {
        const exe = path.join(dir, name);
        try { fs.accessSync(exe, fs.constants.X_OK); return exe; } catch { /* segue procurando */ }
      }
    }
  }
  throw new Error('Chrome não encontrado. Instale o Google Chrome ou defina CHROME_PATH.');
}

const puppeteer = await loadPuppeteer();
const CHROME = resolveChrome();
const HTML = pathToFileURL(path.join(__dirname, 'scene.html')).href;
const FRAMES_DIR = path.join(__dirname, 'frames');
const FPS = 30;
const DURATION = 10.0;
const W = 1080, H = 1350;

if (!fs.existsSync(FRAMES_DIR)) fs.mkdirSync(FRAMES_DIR, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--hide-scrollbars', '--font-render-hinting=none', '--disable-gpu-vsync', '--force-device-scale-factor=1'],
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await page.evaluateOnNewDocument(() => { window.HEADLESS = true; });
await page.goto(HTML, { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 2000));  // aguardar fontes Google

const total = Math.floor(DURATION * FPS);
console.log(`Rendering ${total} frames at ${W}x${H}...`);
const t0 = Date.now();
for (let i = 0; i < total; i++) {
  const t = i / FPS;
  await page.evaluate((t) => window.SET_TIME(t), t);
  await page.screenshot({
    path: path.join(FRAMES_DIR, `f${String(i).padStart(4, '0')}.png`),
    type: 'png'
  });
  if (i % 30 === 0) {
    process.stdout.write(`\r[${i}/${total}] ${((Date.now()-t0)/1000).toFixed(1)}s`);
  }
}
console.log(`\nDone in ${((Date.now()-t0)/1000).toFixed(1)}s`);
await browser.close();
```

Ajustar `W`, `H` e `DURATION` para o destino escolhido, mantendo os mesmos valores no HTML e no script de renderização.

### 4. Instalar puppeteer-core uma vez

O `render.mjs` já usa o diretório compartilhado `~/.operacao-ia/tools/puppeteer/` quando ele existe
(sem link simbólico, então funciona igual no Windows, macOS e Linux). Se ele não existir, instalar
no próprio projeto:

```bash
cd "$PROJ"
npm install --no-save puppeteer-core
```

Confirmar que o módulo está resolvendo antes de renderizar.

### 5. Renderizar frames

```bash
cd "$PROJ"
node render.mjs
```

Timings aproximados (medidos em Apple M-series; varia conforme a máquina):

- 1080×1350 · 10s @ 30fps (300 frames): ~42s;
- 1080×1350 · 12s @ 30fps (360 frames): ~52s;
- 1920×1080 · 10s @ 30fps: ~50s.

### 6. Codificar MP4 H.264

Usar o ffmpeg encontrado no sistema, sem assumir uma versão específica. Os blocos `bash` desta skill rodam no terminal do Claude Code (Git Bash no Windows, shell padrão no macOS/Linux). No PowerShell, rode o `ffmpeg` numa linha só (sem as `\` de continuação) e confira o arquivo com `Get-Item out/video.mp4` no lugar de `ls -lh`.

```bash
ffmpeg -y -framerate 30 -i frames/f%04d.png \
  -c:v libx264 -pix_fmt yuv420p \
  -crf 17 -preset slow \
  -movflags +faststart \
  out/video.mp4
```

**Referência de CRF:**

- 17 = alta qualidade;
- 18 = padrão recomendado;
- 23 = qualidade média e arquivo menor.

### 7. Validar

```bash
ls -lh out/video.mp4
safezone out/video.mp4 --modo stories   # gate de safe-zone — exit 0 = ok · exit 1 = violação
```

O `--modo` acompanha o **destino** do vídeo, não apenas a resolução:

| Destino | Comando | Gate |
|---|---|---|
| **9:16 de anúncio** (1080×1920, Stories/Reels pagos) | `safezone out/video.mp4 --modo stories` | **BLOQUEIA** — exit 1 não sobe; há elementos de interface no topo e na parte inferior |
| Feed 4:5 de anúncio (1080×1350) | `safezone out/video.mp4 --modo feed` | bloqueia se a informação crítica estiver fora da área segura |
| Peça orgânica, hero de LP ou YouTube 1920×1080 | `safezone out/video.mp4` (modo universal) | informativo — revisar o overlay, sem bloqueio automático |

Se reprovar, abrir `out/video.safezone.png`, trazer a informação crítica para a faixa 14%-75% e re-renderizar.

## Padrões de cena (template de 5 atos · 10s)

Para vídeos promocionais, usar esta estrutura como ponto de partida:

| Cena | Duração | Conteúdo |
|---|---|---|
| 1. Hook | 2-2.5s | Pergunta provocativa, dado verificável ou situação anterior |
| 2. Problema | 2-2.5s | Método antigo riscado ou dor concreta |
| 3. Solução | 2-3s | Demonstração do produto, processo ou resultado com comandos e outputs reais quando aplicável |
| 4. Prova | 1.5-2s | Mockups, screenshots ou evidências reais, sem recriação enganosa |
| 5. CTA | 1.5-2s | Headline de impacto, botão e URL fornecidos pelo aluno |

## Anti-AI-slop checklist

Antes de finalizar, verificar:

- [ ] Mockups e screenshots reais usados quando disponíveis, copiados para `assets/`, em vez de shapes CSS.
- [ ] Comandos e outputs reais, sem placeholders como `cmd1 cmd2 cmd3`.
- [ ] Tipografia Inter + JetBrains Mono ou o sistema definido pelo projeto.
- [ ] Cores e fundos derivados do DESIGN.md local ou do briefing do aluno.
- [ ] Sem partículas genéricas, orbs ou gradientes flat sem função.
- [ ] Sem emoji decorativo, exceto quando fizer parte da identidade da marca.
- [ ] Stagger reveals sutis, com fade e translateY de 30-40px, sem movimento bouncy/cartoon.
- [ ] Easing easeOutQuart/Cubic, não linear.
- [ ] Todo texto está legível e dentro da safe zone do destino.

## Variantes de output

Após gerar uma versão, oferecer:

- GIF com palette otimizada (`ffmpeg -vf palettegen` → palette → palette use);
- versão em 60fps interpolada;
- versão muted ou com áudio, usando um script de música disponível no ambiente quando houver;
- resoluções alternativas, como Stories 9:16 e YouTube 16:9.

## Adicionar ao launcher (opcional)

Se o vídeo for um hero para uma landing page local, criar um link no diretório de sites local configurado pelo projeto, adicionar um card ao launcher correspondente e validar com uma requisição HTTP. Não assumir nome de domínio, diretório ou alias: perguntar ou ler a configuração existente.

## Tools e paths

- `ffmpeg`: usar `command -v ffmpeg`, sem hardcode de versão do brew.
- Chrome: resolvido por `resolveChrome()` (`CHROME_PATH`; macOS em `/Applications`; Windows em `%ProgramFiles%`, `%ProgramFiles(x86)%` ou `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`; Linux via `google-chrome`/`chromium` no PATH). Se nada for achado, informar o erro e pedir `CHROME_PATH`.
- `puppeteer-core`: preferir `~/.operacao-ia/tools/puppeteer/node_modules`.
- Design system: usar `DESIGN.md` local do projeto; na ausência, seguir o briefing e uma composição visual consistente.
