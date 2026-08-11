// Renderiza as artes de oferta (quadrado 1:1 + story 9:16) a partir de um data.json.
// Uso: node render.mjs <dir-do-projeto>
// Espera <dir>/data.json: { '<chave>': { slug, wordmark, badge, promessa, items[], ... } }
// Escreve <dir>/<slug>-oferta-quadrado.png (2160x2160) e <dir>/<slug>-oferta-story.png (2160x3840)
import { chromium } from 'playwright';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const skillDir = new URL('..', import.meta.url).pathname;
const dir = resolve(process.argv[2] || process.cwd()) + '/';
const cardHtml = skillDir + 'assets/card.html';

if (!existsSync(dir + 'data.json')) {
  console.error(`ERRO: não achei ${dir}data.json`);
  process.exit(1);
}
const data = JSON.parse(readFileSync(dir + 'data.json', 'utf8'));

const jobs = [];
for (const [chave, prod] of Object.entries(data)) {
  const slug = prod.slug || chave;
  jobs.push([chave, 'square', `${slug}-oferta-quadrado.png`]);
  jobs.push([chave, 'story',  `${slug}-oferta-story.png`]);
}

const browser = await chromium.launch({ channel: 'chrome' });
for (const [p, f, out] of jobs) {
  const w = 1080, h = f === 'story' ? 1920 : 1080;
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.addInitScript((d) => { window.__CARD_DATA__ = d; }, data);
  await page.goto('file://' + cardHtml + '?p=' + p + '&f=' + f, { waitUntil: 'load' });
  try {
    await page.waitForFunction(() => window.__READY__ === true, { timeout: 20000 });
  } catch {
    const erroNaPagina = await page.$eval('.wrap', el => el.textContent?.trim() || '').catch(() => '');
    console.error(`ERRO: "${p}" (${f}) não ficou pronto em 20s. Página diz: ${erroNaPagina || '(vazio)'}`);
    await browser.close();
    process.exit(1);
  }
  await page.waitForTimeout(500);
  if (await page.evaluate(() => window.__FIT_OVERFLOW__ === true)) {
    console.warn(`AVISO: "${p}" (${f}) ainda transborda no menor tamanho — o PNG pode sair cortado. Reduza itens ou encurte rótulos.`);
  }
  const el = await page.$('#card');
  await el.screenshot({ path: dir + out });
  console.log('ok →', out);
  await ctx.close();
}
await browser.close();
console.log('render completo');
