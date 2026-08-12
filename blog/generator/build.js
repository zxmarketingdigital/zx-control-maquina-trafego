#!/usr/bin/env node
// build.js — gera páginas estáticas a partir dos briefings em content/keywords/.
// O provider manual é deliberadamente o padrão: não exige credenciais e torna o build reproduzível.
"use strict";

const fs = require("fs");
const path = require("path");
const { renderArticle, css, esc, cfBeacon, promoBar, productShowcase } = require("./template");

const ROOT = path.resolve(__dirname, "..");
const CFG = JSON.parse(fs.readFileSync(path.join(ROOT, "config.json"), "utf8"));
const SITE = CFG.site || {};
const BASE = String(SITE.baseUrl || "").replace(/\/+$/, "");
const BLOG_PATH = (SITE.blogPath || "/blog").replace(/\/+$/, "") || "/blog";
const KW_DIR = path.join(ROOT, "content", "keywords");
const OUT = path.join(ROOT, "public");
const BLOG_OUT = path.join(OUT, BLOG_PATH.replace(/^\/+/, ""));
const NOW = new Date().toISOString();

function parseFrontMatter(raw) {
  const m = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!m) throw new Error("Briefing sem front-matter YAML");
  return parseYaml(m[1]);
}

// Parser pequeno e intencionalmente limitado ao YAML usado nos briefings: escalares,
// listas de escalares e listas de objetos. Isso evita dependência externa no instalador.
function parseYaml(text) {
  const lines = text.split("\n"), root = {}, stack = [{ indent: -1, container: root, key: null }];
  function unquote(v) {
    v = v.trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) return v.slice(1,-1).replace(/\\"/g,'"');
    return v;
  }
  for (const line of lines) {
    if (!line.trim()) continue;
    const indent = line.match(/^\s*/)[0].length;
    while (stack.length > 1 && indent <= stack[stack.length-1].indent) stack.pop();
    const top = stack[stack.length-1], trimmed = line.trim();
    if (trimmed.startsWith("- ")) {
      const rest = trimmed.slice(2), arr = Array.isArray(top.container[top.key]) ? top.container[top.key] : [];
      top.container[top.key] = arr;
      const kv = rest.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
      if (kv) { const obj = {}; obj[kv[1]] = kv[2] === "" ? null : unquote(kv[2]); arr.push(obj); stack.push({indent,container:obj,key:null}); }
      else arr.push(unquote(rest));
      continue;
    }
    const kv = trimmed.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!kv) continue;
    const key = kv[1], val = kv[2];
    if (val === "") { top.container[key] = top.container[key] || null; top.key = key; stack.push({indent,container:top.container,key}); }
    else top.container[key] = unquote(val);
  }
  return root;
}

function ensureDir(dir) { fs.mkdirSync(dir, { recursive: true }); }
function ensureFavicon() {
  const assetsDir = path.join(OUT, "assets");
  ensureDir(assetsDir);
  const dest = path.join(assetsDir, "favicon-32.png");
  if (fs.existsSync(dest)) return;
  const base64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAJUlEQVRoge3BAQ0AAADCoPdPbQ43oAAAAAAAAAAAAAAAAAAAvA0jkAAB1eKJIQAAAABJRU5ErkJggg==";
  fs.writeFileSync(dest, Buffer.from(base64, "base64"));
}
function ensureTrackingScript() {
  const source = path.resolve(ROOT, "..", "skills", "tracking-canal-vendas", "zx-tracking.js");
  const dest = path.join(OUT, "tracking.js");
  if (!fs.existsSync(source)) { console.warn(`[aviso] zx-tracking.js não encontrado em ${source}; tracking.js não copiado.`); return; }
  if (fs.existsSync(dest) && fs.readFileSync(dest, "utf8") === fs.readFileSync(source, "utf8")) return;
  fs.copyFileSync(source, dest);
}
function slugFromFile(file) { return file.replace(/\.md$/, ""); }
function absolute(value) { const item = String(value || ""); return /^https?:\/\//i.test(item) ? item : BASE + "/" + item.replace(/^\/+/, ""); }

function loadBriefing(file) {
  const fm = parseFrontMatter(fs.readFileSync(path.join(KW_DIR,file), "utf8"));
  fm.slug = fm.slug || slugFromFile(file);
  fm.datePublished = fm.datePublished || NOW;
  fm.dateModified = NOW;
  fm.ogImage = fm.ogImage || SITE.defaultOgImage;
  return fm;
}

function buildArticle(fm) {
  if ((CFG.generator || {}).provider && CFG.generator.provider !== "manual") console.warn(`[aviso] provider="${CFG.generator.provider}" não implementado; usando o briefing manual.`);
  if (!/^[a-z0-9-]+$/.test(String(fm.slug || ""))) throw new Error(`Slug inválido "${fm.slug}": use apenas letras minúsculas, números e hífens.`);
  const outputRoot = path.resolve(BLOG_OUT), dir = path.join(BLOG_OUT, fm.slug), resolvedDir = path.resolve(dir);
  if (resolvedDir !== outputRoot && !resolvedDir.startsWith(outputRoot + path.sep)) throw new Error(`Slug fora do diretório de saída: ${fm.slug}`);
  const html = renderArticle(fm, CFG);
  ensureDir(dir); fs.writeFileSync(path.join(dir,"index.html"), html, "utf8");
  console.log(`[ok] artigo -> ${BLOG_PATH}/${fm.slug}/index.html (${html.length} bytes)`);
  return articleMeta(fm);
}
function articleMeta(a) { return {slug:a.slug,title:a.title,description:a.description,lastmod:a.dateModified,tier:a.tier,keyword:a.keyword}; }

function categoriaDe(a) {
  const s = ((a.keyword || "") + " " + (a.title || "")).toLowerCase();
  if (a.tier === "pillar") return "Guia";
  if (/\bvs\b|\bou\b|alternativa|comparativo|melhor(es)? /.test(s)) return "Comparativo";
  if (/como |passo a passo|tutorial|configurar|criar |montar |instalar/.test(s)) return "Tutorial";
  return "Artigo";
}

function buildIndex(articles) {
  const ordered = articles.slice().sort((a,b) => {
    const pa = a.tier === "pillar" ? 0 : 1, pb = b.tier === "pillar" ? 0 : 1;
    return pa !== pb ? pa-pb : String(b.lastmod || "").localeCompare(String(a.lastmod || ""));
  });
  const count = {}; ordered.forEach(a => { const c = categoriaDe(a); count[c] = (count[c] || 0) + 1; });
  const cats = ["Guia","Tutorial","Comparativo","Artigo"].filter(c => count[c]);
  const chips = [`<button class="chip active" data-cat="all">Todos <span class="n">${ordered.length}</span></button>`].concat(cats.map(c => `<button class="chip" data-cat="${esc(c)}">${esc(c)} <span class="n">${count[c]}</span></button>`)).join("\n");
  const cards = ordered.map(a => { const cat = categoriaDe(a); const hay = esc(((a.title||"")+" "+(a.keyword||"")+" "+(a.description||"")).toLowerCase()); return `
<a class="post" href="${BLOG_PATH}/${esc(a.slug)}/" data-cat="${esc(cat)}" data-search="${hay}"><span class="thumb"><img src="/assets/thumbs/${esc(a.slug)}.webp" alt="" loading="lazy" width="400" height="225" onerror="this.closest('.thumb').classList.add('noimg')"><span class="ph" aria-hidden="true"><span>${esc(cat)}</span></span></span><span class="body"><span class="t">${esc(cat)}</span><h2>${esc(a.title)}</h2><p>${esc(a.description)}</p><span class="more">ler &rarr;</span></span></a>`; }).join("\n");
  const firstKey = SITE.featuredProduct || Object.keys(CFG.products || {})[0];
  const firstProduct = CFG.products && CFG.products[firstKey];
  const tracking = SITE.trackingScript || "/tracking.js";
  const html = `<!DOCTYPE html><html lang="${esc(SITE.lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(SITE.name)} — ${esc(SITE.tagline)}</title><meta name="description" content="${esc(SITE.tagline)} Guias práticos e conteúdo educativo."><link rel="canonical" href="${BASE}${BLOG_PATH}/"><meta name="robots" content="index,follow"><meta property="og:type" content="website"><meta property="og:title" content="${esc(SITE.name)}"><meta property="og:description" content="${esc(SITE.tagline)}"><meta property="og:url" content="${BASE}${BLOG_PATH}/"><meta property="og:image" content="${absolute(SITE.defaultOgImage)}"><link rel="icon" href="${esc(SITE.favicon || "/assets/favicon-32.png")}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet"><style>${css()}
.hero{text-align:center;padding:60px 0 20px}.hero .eyebrow{font:11px 'JetBrains Mono',monospace;letter-spacing:.2em;text-transform:uppercase;color:var(--primary-light)}.hero h1{font-size:2.7rem;max-width:720px;margin:16px auto 14px}.hero h1 span{color:var(--primary-bright)}.hero p{color:var(--text-2);max-width:560px;margin:auto}.toolbar{position:sticky;top:64px;z-index:9;background:linear-gradient(var(--bg) 70%,transparent);padding:18px 0 14px}.search{max-width:520px;margin:0 auto 16px}.search input{width:100%;background:var(--surface);border:1px solid var(--border-light);border-radius:12px;color:var(--text);font-size:.98rem;padding:14px 18px;outline:none}.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}.chip{background:var(--surface);border:1px solid var(--border-light);color:var(--text-2);font:12px 'JetBrains Mono',monospace;padding:8px 14px;border-radius:100px;cursor:pointer}.chip.active{background:rgba(217,119,6,.15);border-color:rgba(217,119,6,.5);color:var(--primary-bright)}.chip .n{opacity:.7}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;margin:24px 0}.post{display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--border-light);border-radius:16px;overflow:hidden;color:var(--text)}.post:hover{transform:translateY(-3px);color:var(--text)}.thumb{position:relative;display:block;aspect-ratio:16/9;background:var(--surface2);overflow:hidden}.thumb img{width:100%;height:100%;object-fit:cover}.thumb .ph{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:linear-gradient(135deg,#161310,#241b11)}.thumb .ph span{font:11px 'JetBrains Mono',monospace;color:var(--primary-light);border:1px solid rgba(217,119,6,.35);border-radius:100px;padding:6px 14px}.thumb.noimg img{display:none}.thumb.noimg .ph{display:flex}.post .body{padding:20px 22px 22px;display:flex;flex-direction:column;flex:1}.post .t{font:11px 'JetBrains Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--primary-light)}.post h2{font-size:1.16rem;color:#fff;margin:9px 0 8px}.post p{color:var(--text-2);font-size:.9rem;margin:0 0 16px;flex:1}.more{font:12px 'JetBrains Mono',monospace;color:var(--primary-light)}.empty{grid-column:1/-1;text-align:center;color:var(--text-muted);padding:48px 0}@media(max-width:600px){.hero h1{font-size:2rem}}
</style></head><body>${promoBar(firstProduct)}<header class="site"><div class="wrap-wide"><a class="brand" href="${BLOG_PATH}/"><img src="${esc(SITE.logo)}" alt="${esc(SITE.name)}" width="26" height="26"><span>${esc(SITE.name)}</span><span class="dot"></span></a><nav><a href="${esc(BASE)}">site principal</a></nav></div></header><main><div class="wrap-wide"><section class="hero"><span class="eyebrow">Biblioteca · Acesso livre</span><h1>${esc(SITE.name)}<br><span>conteúdo que ajuda.</span></h1><p>${esc(SITE.tagline)} Guias práticos, análises e explicações para aplicar o conhecimento no dia a dia.</p></section>${productShowcase(CFG.products || {},{only:firstKey,title:"Produto em destaque"})}<div class="toolbar"><div class="search"><input type="search" id="q" placeholder="Buscar por tema ou palavra-chave…" autocomplete="off" aria-label="Buscar artigos"></div><div class="chips" id="chips">${chips}</div></div><section class="grid" id="grid">${cards}<div class="empty" id="empty" hidden>Nenhum artigo encontrado. Tente outro termo.</div></section></div></main><footer class="site"><div class="wrap-wide"><span class="mono">${esc(SITE.name)} — ${esc(SITE.tagline)}</span><span class="mono"><a href="/sitemap.xml">sitemap</a> · <a href="${esc(BASE)}">site principal</a></span></div></footer><script>(function(){var g=document.getElementById('grid'),q=document.getElementById('q'),c=document.getElementById('chips'),e=document.getElementById('empty'),cards=[].slice.call(g.querySelectorAll('a.post')),cat='all';function n(s){return(s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}function apply(){var t=n(q.value.trim()),shown=0;cards.forEach(function(x){var ok=(cat==='all'||x.dataset.cat===cat)&&(!t||n(x.dataset.search).indexOf(t)>=0);x.style.display=ok?'':'none';if(ok)shown++});e.hidden=shown!==0}q.addEventListener('input',apply);c.addEventListener('click',function(x){var b=x.target.closest('.chip');if(!b)return;cat=b.dataset.cat;c.querySelectorAll('.chip').forEach(function(y){y.classList.toggle('active',y===b)});apply()})})()</script><script src="${esc(tracking)}" defer></script>${cfBeacon(CFG)}</body></html>`;
  ensureDir(BLOG_OUT); fs.writeFileSync(path.join(BLOG_OUT,"index.html"),html,"utf8"); console.log(`[ok] index -> ${BLOG_PATH}/index.html (${articles.length} artigos)`);
}

function buildSitemap(articles) {
  const urls = [`${BASE}${BLOG_PATH}/`].concat(articles.map(a => `${BASE}${BLOG_PATH}/${a.slug}/`));
  const body = urls.map((u,i) => `  <url>\n    <loc>${u}</loc>\n    <lastmod>${i===0?NOW:(articles[i-1].lastmod||NOW)}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>${i===0?"0.8":"0.7"}</priority>\n  </url>`).join("\n");
  fs.writeFileSync(path.join(OUT,"sitemap.xml"),`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`);
  fs.writeFileSync(path.join(OUT,"robots.txt"),`User-agent: *\nAllow: /\n\nSitemap: ${BASE}/sitemap.xml\n`);
  fs.writeFileSync(path.join(OUT,"llms.txt"),`# ${SITE.name}\n\n> ${SITE.tagline}\n\n## Artigos\n` + articles.map(a => `- [${a.title}](${BASE}${BLOG_PATH}/${a.slug}/): ${a.description}`).join("\n") + "\n");
  console.log(`[ok] sitemap.xml + robots.txt + llms.txt`);
}

function main() {
  ensureDir(BLOG_OUT);
  ensureFavicon();
  ensureTrackingScript();
  const only = process.argv[2];
  const files = fs.readdirSync(KW_DIR).filter(f => f.endsWith(".md"));
  if (only) { const wanted = only.replace(/\.md$/,"") + ".md"; if (!files.includes(wanted)) { console.error(`Briefing não encontrado: ${wanted}`); process.exit(1); } }
  const all = files.map(loadBriefing), existing = new Set(all.map(a => a.slug));
  for (const fm of all) if (Array.isArray(fm.related)) fm.related = fm.related.filter(r => existing.has(r.slug));
  const articles = [];
  for (const fm of all) {
    if (only && fm.slug !== only.replace(/\.md$/, "")) {
      // Ao solicitar um slug, apenas ele é reescrito; o índice continua completo para
      // não transformar a atualização de um rascunho em republicação dos demais artigos.
      articles.push(articleMeta(fm));
    } else articles.push(buildArticle(fm));
  }
  buildIndex(articles); buildSitemap(articles); console.log(`\n✓ build concluído — ${articles.length} artigo(s). Saída em: ${OUT}`);
}
main();
