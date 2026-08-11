// QA de safe-zone p/ todas as variações: nada pode cruzar topo 14% (269px) nem base 75% (1440px).
// Varre a timeline inteira e considera a opacidade efetiva (herdada da cena).
import puppeteer from 'puppeteer-core';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { VARIANTS } from './variants.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const TOP = 268.8, BOT = 1440;
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--hide-scrollbars'] });

let anyFail = false;
for (const v of VARIANTS) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  await page.evaluateOnNewDocument(vv => { window.__VARIANT = vv; }, v);
  await page.goto('file://' + join(__dirname, 'ad.html'), { waitUntil: 'networkidle0' });
  await page.evaluate(async () => { await document.fonts.ready; window.__capture = true; document.body.classList.add('norulers'); });

  let worstTop = 9999, worstBot = 0, violations = [];
  for (let t = 0; t <= 22000; t += 100) {
    await page.evaluate(ms => window.seek(ms), t);
    const rects = await page.evaluate(() => {
      const eff = el => {
        let o = 1, n = el;
        while (n && n.id !== 'stage') {
          const cs = getComputedStyle(n);
          if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
          o *= parseFloat(cs.opacity);
          n = n.parentElement;
        }
        return o;
      };
      const out = [];
      document.querySelectorAll('#stage *').forEach(el => {
        if (el.classList.contains('safe') || el.classList.contains('bg')) return;
        if (eff(el) < 0.06) return;
        const cs = getComputedStyle(el);
        const txt = el.childElementCount === 0 ? el.textContent.trim() : '';
        const hasBox = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || cs.borderTopWidth !== '0px';
        if (!txt && !hasBox) return;
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) return;
        out.push({ tag: el.id || el.className, top: Math.round(r.top), bottom: Math.round(r.bottom), txt: txt.slice(0, 22) });
      });
      return out;
    });
    for (const r of rects) {
      worstTop = Math.min(worstTop, r.top); worstBot = Math.max(worstBot, r.bottom);
      if (r.top < TOP - 1 || r.bottom > BOT + 1) violations.push({ t, ...r });
    }
  }
  await page.close();
  const ok = violations.length === 0;
  anyFail = anyFail || !ok;
  console.log(`[${v.id}] topo-mais-alto=${worstTop} (>=${TOP})  base-mais-baixa=${worstBot} (<=${BOT})  ${ok ? '✅ OK' : '❌ ' + violations.length + ' violações'}`);
  if (!ok) violations.slice(0, 6).forEach(x => console.log('    ', x));
}
await browser.close();
process.exit(anyFail ? 1 : 0);
