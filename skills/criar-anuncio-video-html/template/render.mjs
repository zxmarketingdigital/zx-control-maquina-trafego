// Renderiza TODAS as variações: frames determinísticos por variante + timings.sh (áudio).
import puppeteer from 'puppeteer-core';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync, rmSync, writeFileSync } from 'fs';
import { VARIANTS } from './variants.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
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
    await page.goto('file://' + join(__dirname, 'ad.html'), { waitUntil: 'networkidle0' });
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
console.log('Frames + timings.sh prontos:\n' + sh);
