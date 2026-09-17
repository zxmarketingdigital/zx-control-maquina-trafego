// Renderiza TODAS as variações: frames determinísticos por variante + timings.json (áudio).
import puppeteer from 'puppeteer-core';
import { fileURLToPath, pathToFileURL } from 'url';
import { delimiter, dirname, join, win32 } from 'path';
import { accessSync, constants, existsSync, mkdirSync, rmSync, writeFileSync } from 'fs';
import { spawnSync } from 'child_process';
import { VARIANTS } from './variants.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
function resolveChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  if (process.platform === 'darwin') return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (process.platform === 'win32') {
    const bases = [process.env.PROGRAMFILES, process.env['PROGRAMFILES(X86)'], process.env.LOCALAPPDATA].filter(Boolean);
    for (const base of bases) {
      const exe = win32.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe');
      if (existsSync(exe)) return exe;
    }
  } else {
    for (const nome of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
      for (const dir of (process.env.PATH || '').split(delimiter).filter(Boolean)) {
        const exe = join(dir, nome);
        try { accessSync(exe, constants.X_OK); return exe; } catch { /* segue procurando */ }
      }
    }
  }
  throw new Error('Chrome não encontrado. Instale o Google Chrome ou defina CHROME_PATH com o caminho do executável.');
}
const CHROME = resolveChrome();
const FPS = 30, END = 22000, TOTAL = Math.round(END / 1000 * FPS);
const pad = n => String(n).padStart(4, '0');
const only = process.argv[2]; // opcional: renderizar só uma variante (id)

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--no-sandbox', '--force-color-profile=srgb', '--hide-scrollbars', '--disable-lcd-text'],
});

const timings = [];
for (const v of VARIANTS) {
  if (only && v.id !== only) continue;
  const dir = join(__dirname, `frames-${v.id}`);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });

  const page = await browser.newPage();
  page.setDefaultTimeout(10000);
  try {
    await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
    await page.evaluateOnNewDocument(vv => { window.__VARIANT = vv; }, v);
    await page.goto(pathToFileURL(join(__dirname, 'ad.html')).href, { waitUntil: 'networkidle0' });
    await page.evaluate(async () => {
      await document.fonts.ready;
      document.body.classList.add('norulers');
      window.__capture = true;
    });
    const audio = await page.evaluate(() => window.__audio());
    timings.push({ id: v.id, ...audio });
    await new Promise(r => setTimeout(r, 250));

    console.log(`[${v.id}] ${v.angulo} — ${TOTAL} frames`);
    for (let i = 0; i < TOTAL; i++) {
      await page.evaluate(ms => window.seek(ms), i * (1000 / FPS));
      await page.screenshot({ path: join(dir, `f${pad(i)}.png`), type: 'png' });
      if (i % 120 === 0) console.log(`   ${i}/${TOTAL}`);
    }
  } finally {
    await page.close();
  }
}
await browser.close();

// timings.sh — usado pelo build.sh (segundos)
const ids = timings.map(t => t.id).join(' ');
let sh = `# gerado por render.mjs — tempos de áudio por variante (segundos)\nVARIANTS="${ids}"\n`;
for (const t of timings) {
  sh += `TYPING_${t.id}=${(t.typingStart / 1000).toFixed(3)}; CASH_${t.id}=${(t.cashTime / 1000).toFixed(3)}\n`;
}
writeFileSync(join(__dirname, 'timings.sh'), sh);

// timings.json — usado pelo build.mjs (roda igual no Windows, macOS e Linux)
const json = { variants: timings.map(t => ({ id: t.id, typing: +(t.typingStart / 1000).toFixed(3), cash: +(t.cashTime / 1000).toFixed(3) })) };
writeFileSync(join(__dirname, 'timings.json'), JSON.stringify(json, null, 2) + '\n');
console.log('Frames + timings.json prontos:\n' + sh);
