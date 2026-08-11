#!/usr/bin/env node
// build.js — gera o blog estático a partir dos briefings em content/keywords/*.md
//
// Uso:
//   node generator/build.js                 # todos os artigos + índice + sitemap
//   node generator/build.js <slug>          # um artigo e índice/sitemap completos
//
// Provider de texto (config.json -> generator.provider):
//   manual    : usa o briefing markdown como fonte (default, custo zero, sem credencial)
//   claude-api: reservado para futura expansão via API; a chave vem do ambiente
//   codex-cli : reservado para futura expansão usando a sessão autenticada
//
// O build gera em public/ e mantém briefings separados da saída publicada. Isso permite que
// um pipeline posterior valide um artigo antes de colocá-lo no diretório servido pelo site.
"use strict";

const fs = require("fs");
const path = require("path");
const {
  renderArticle, css, esc, cfBeacon, salesCss, promoBar, productShowcase,
  joinUrl, trimSlash
} = require("./template");

const ROOT = path.resolve(__dirname, "..");
const CFG = JSON.parse(fs.readFileSync(path.join(ROOT, "config.json"), "utf8"));
const KW_DIR = path.join(ROOT, "content", "keywords");
const OUT = path.join(ROOT, "public");
const BLOG_OUT = path.join(OUT, "blog");
const NOW = new Date().toISOString();
const BLOG_PATH = CFG.site.blogPath || "/blog/";
const ASSETS_PATH = CFG.site.assetsPath || "/assets/";
const FAVICON = CFG.site.favicon || CFG.site.logo;
const TRACKING_SCRIPT = CFG.site.trackingScript || "/tracking.js";

// --- mini YAML front-matter parser (suficiente para os briefings do motor) ---
function parseFrontMatter(raw) {
  const m = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!m) throw new Error("Briefing sem front-matter YAML");
  return parseYaml(m[1]);
}

// Parser YAML enxuto: escalares, listas de escalares e listas de objetos (h2/points, q/a).
function parseYaml(text) {
  const lines = text.split("\n");
  const root = {};
  const stack = [{ indent: -1, container: root, key: null }];

  function unquote(v) {
    v = v.trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      return v.slice(1, -1).replace(/\\"/g, '"');
    }
    return v;
  }

  for (const line of lines) {
    if (!line.trim()) continue;
    const indent = line.match(/^\s*/)[0].length;
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop();
    const top = stack[stack.length - 1];
    const trimmed = line.trim();

    if (trimmed.startsWith("- ")) {
      const rest = trimmed.slice(2);
      let arr = top.container[top.key];
      if (!Array.isArray(arr)) { arr = []; top.container[top.key] = arr; }
      const kv = rest.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
      if (kv) {
        const obj = {};
        obj[kv[1]] = kv[2] === "" ? null : unquote(kv[2]);
        arr.push(obj);
        stack.push({ indent, container: obj, key: null });
      } else {
        arr.push(unquote(rest));
      }
      continue;
    }

    const kv = trimmed.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!kv) continue;
    const key = kv[1];
    const val = kv[2];
    if (val === "") {
      // O pai pode receber uma lista nas linhas seguintes.
      top.container[key] = top.container[key] || null;
      top.key = key;
      stack.push({ indent, container: top.container, key });
    } else {
      top.container[key] = unquote(val);
    }
  }
  return root;
}

function ensureDir(d) { fs.mkdirSync(d, { recursive: true }); }
function slugFromFile(f) { return f.replace(/\.md$/, ""); }
function assetUrl(name) { return String(ASSETS_PATH).replace(/\/+$/, "") + "/" + String(name).replace(/^\/+/, ""); }
function blogUrl(slug) { return String(BLOG_PATH).replace(/\/+$/, "") + "/" + String(slug).replace(/^\/+/, "") + "/"; }

function loadBriefing(file) {
  const raw = fs.readFileSync(path.join(KW_DIR, file), "utf8");
  const fm = parseFrontMatter(raw);
  fm.slug = fm.slug || slugFromFile(file);
  fm.datePublished = fm.datePublished || NOW;
  fm.dateModified = NOW;
  fm.ogImage = fm.ogImage || CFG.site.defaultOgImage;
  return fm;
}

function articleSummary(fm) {
  return { slug: fm.slug, title: fm.title, description: fm.description,
    lastmod: fm.dateModified, tier: fm.tier, keyword: fm.keyword };
}

function buildArticle(fm) {
  if ((CFG.generator && CFG.generator.provider || "manual") !== "manual") {
    console.warn(`[aviso] provider="${CFG.generator.provider}" não implementado no MVP; usando briefing manual como fonte.`);
  }
  const html = renderArticle(fm, CFG);
  const dir = path.join(BLOG_OUT, fm.slug);
  ensureDir(dir);
  fs.writeFileSync(path.join(dir, "index.html"), html, "utf8");
  console.log(`[ok] artigo -> ${blogUrl(fm.slug)}index.html (${html.length} bytes)`);
  return articleSummary(fm);
}

// Categoria editorial derivada do tier + heurística de keyword/título.
function categoriaDe(a) {
  const s = ((a.keyword || "") + " " + (a.title || "")).toLowerCase();
  if (a.tier === "pillar") return "Guia";
  if (/\bvs\b|\bou\b|alternativa|comparativo|melhor(es)? /.test(s)) return "Comparativo";
  if (/como |passo a passo|tutorial|configurar|criar |montar |instalar/.test(s)) return "Tutorial";
  return "Artigo";
}

function buildIndex(articles) {
  const ordered = articles.slice().sort((a, b) => {
    const pa = a.tier === "pillar" ? 0 : 1, pb = b.tier === "pillar" ? 0 : 1;
    if (pa !== pb) return pa - pb;
    return String(b.lastmod || "").localeCompare(String(a.lastmod || ""));
  });
  const catCount = {};
  for (const a of ordered) { const c = categoriaDe(a); catCount[c] = (catCount[c] || 0) + 1; }
  const cats = ["Guia", "Tutorial", "Comparativo", "Artigo"].filter(c => catCount[c]);
  const chips = [`<button class="chip active" data-cat="all">Todos <span class="n">${ordered.length}</span></button>`]
    .concat(cats.map(c => `<button class="chip" data-cat="${esc(c)}">${esc(c)} <span class="n">${catCount[c]}</span></button>`))
    .join("\n      ");

  const cards = ordered.map(a => {
    const cat = categoriaDe(a);
    const hay = esc(((a.title || "") + " " + (a.keyword || "") + " " + (a.description || "")).toLowerCase());
    return `
      <a class="post" href="${esc(blogUrl(a.slug))}" data-cat="${esc(cat)}" data-search="${hay}">
        <span class="thumb">
          <img src="${esc(assetUrl("thumbs/" + a.slug + ".webp"))}" alt="" loading="lazy" width="400" height="225"
               onerror="this.closest('.thumb').classList.add('noimg')">
          <span class="ph" aria-hidden="true"><span class="ph-k">${esc(cat)}</span></span>
        </span>
        <span class="body">
          <span class="t">${esc(cat)}</span>
          <h2>${esc(a.title)}</h2>
          <p>${esc(a.description)}</p>
          <span class="more">ler &rarr;</span>
        </span>
      </a>`;
  }).join("\n");

  const site = CFG.site;
  const homeUrl = site.homeUrl || site.baseUrl;
  const html = `<!DOCTYPE html>
<html lang="${esc(site.lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(site.name)} — ${esc(site.tagline)}</title>
<meta name="description" content="${esc(site.tagline)}">
<link rel="canonical" href="${esc(joinUrl(trimSlash(site.baseUrl), BLOG_PATH))}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(site.name)}">
<meta property="og:description" content="${esc(site.tagline)}">
<meta property="og:url" content="${esc(joinUrl(trimSlash(site.baseUrl), BLOG_PATH))}">
<meta property="og:image" content="${esc(joinUrl(trimSlash(site.baseUrl), site.defaultOgImage))}">
<link rel="icon" href="${esc(FAVICON)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>${css()}
.hero{text-align:center;padding:60px 0 20px}
.hero .eyebrow{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;color:var(--primary-light)}
.hero h1{font-size:2.7rem;max-width:720px;margin:16px auto 14px;line-height:1.1}
.hero h1 .amber{background:linear-gradient(135deg,var(--primary),var(--primary-bright));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero p{color:var(--text-2);max-width:560px;margin:0 auto;font-size:1.05rem}
.toolbar{position:sticky;top:64px;z-index:9;background:linear-gradient(var(--bg) 70%,transparent);padding:18px 0 14px;margin-top:8px}
.search{position:relative;max-width:520px;margin:0 auto 16px}
.search input{width:100%;background:var(--surface);border:1px solid var(--border-light);border-radius:12px;color:var(--text);font-family:'Inter',sans-serif;font-size:.98rem;padding:14px 18px 14px 44px;outline:none;transition:border-color .15s,box-shadow .15s}
.search input:focus{border-color:rgba(217,119,6,.5);box-shadow:0 0 0 3px rgba(217,119,6,.12)}
.search .ic{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--text-muted);font-family:'JetBrains Mono',monospace}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.chip{background:var(--surface);border:1px solid var(--border-light);color:var(--text-2);font-family:'JetBrains Mono',monospace;font-size:.76rem;letter-spacing:.03em;padding:8px 14px;border-radius:100px;cursor:pointer;transition:.15s;display:inline-flex;align-items:center;gap:7px}
.chip:hover{border-color:rgba(217,119,6,.35);color:var(--text)}
.chip.active{background:rgba(217,119,6,.15);border-color:rgba(217,119,6,.5);color:var(--primary-bright)}
.chip .n{font-size:.68rem;opacity:.7}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;margin:24px 0}
a.post{display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--border-light);border-radius:16px;overflow:hidden;transition:transform .15s,border-color .15s,box-shadow .15s;color:var(--text)}
a.post:hover{transform:translateY(-3px);border-color:rgba(217,119,6,.3);box-shadow:0 8px 30px rgba(217,119,6,.1);color:var(--text)}
a.post .thumb{position:relative;display:block;aspect-ratio:16/9;background:var(--surface2);overflow:hidden}
a.post .thumb img{width:100%;height:100%;object-fit:cover;display:block}
a.post .thumb .ph{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:radial-gradient(120% 120% at 20% 0%,rgba(217,119,6,.14),transparent 60%),linear-gradient(135deg,#161310,#1f1a14)}
a.post .thumb .ph:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(217,119,6,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(217,119,6,.05) 1px,transparent 1px);background-size:22px 22px}
a.post .thumb .ph .ph-k{position:relative;font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--primary-light);border:1px solid rgba(217,119,6,.35);border-radius:100px;padding:6px 14px;background:rgba(13,13,13,.5)}
a.post .thumb.noimg img{display:none}
a.post .thumb.noimg .ph{display:flex}
a.post .body{padding:20px 22px 22px;display:flex;flex-direction:column;flex:1}
a.post .t{font-family:'JetBrains Mono',monospace;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--primary-light)}
a.post h2{font-size:1.16rem;color:#fff;margin:9px 0 8px;font-weight:800;line-height:1.25}
a.post p{color:var(--text-2);font-size:.9rem;margin:0 0 16px;flex:1}
a.post .more{font-family:'JetBrains Mono',monospace;font-size:.8rem;color:var(--primary-light)}
.empty{grid-column:1/-1;text-align:center;color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:.9rem;padding:48px 0}
@media(max-width:600px){.hero h1{font-size:2rem}.toolbar{top:56px}}
${salesCss()}
</style>
</head>
<body>
${promoBar(CFG.products && CFG.products[Object.keys(CFG.products || {})[0]], Object.keys(CFG.products || {})[0], CFG)}
<header class="site">
  <div class="wrap-wide">
    <a class="brand" href="${esc(BLOG_PATH)}"><img src="${esc(site.logo)}" alt="${esc(site.name)}" width="26" height="26"><span>${esc(site.name)}</span><span class="dot" title="online"></span></a>
    <nav style="font-family:'JetBrains Mono',monospace;font-size:.78rem"><a href="${esc(homeUrl)}">${esc(site.homeLabel || "site principal")}</a></nav>
  </div>
</header>
<main>
  <div class="wrap-wide">
    <section class="hero">
      <span class="eyebrow">${esc(site.heroEyebrow || "Biblioteca de conteúdo")}</span>
      <h1>${esc(site.heroTitle || site.name)}<br><span class="amber">${esc(site.heroAccent || site.tagline)}</span></h1>
      <p>${esc(site.heroDescription || site.tagline)}</p>
    </section>
    ${productShowcase(CFG.products, { title: site.productShowcaseTitle }, CFG)}
    <div class="toolbar">
      <div class="search">
        <span class="ic">/</span>
        <input type="search" id="q" placeholder="${esc(site.searchPlaceholder || "Buscar por tema ou palavra-chave…")}" autocomplete="off" aria-label="Buscar artigos">
      </div>
      <div class="chips" id="chips">
      ${chips}
      </div>
    </div>
    <section class="grid" id="grid">
${cards}
      <div class="empty" id="empty" hidden>Nenhum artigo encontrado. Tente outro termo.</div>
    </section>
  </div>
</main>
<footer class="site">
  <div class="wrap-wide">
    <span class="mono">${esc(site.footerText || site.name)}</span>
    <span class="mono"><a href="/sitemap.xml">sitemap</a> · <a href="${esc(homeUrl)}">${esc(site.homeLabel || "início")}</a></span>
  </div>
</footer>
<script>
(function(){
  var grid = document.getElementById('grid');
  var q = document.getElementById('q');
  var chipsEl = document.getElementById('chips');
  var empty = document.getElementById('empty');
  var cards = Array.prototype.slice.call(grid.querySelectorAll('a.post'));
  var cat = 'all';
  function norm(s){ return (s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,''); }
  function apply(){
    var term = norm(q.value.trim());
    var shown = 0;
    cards.forEach(function(c){
      var okCat = cat === 'all' || c.getAttribute('data-cat') === cat;
      var okTerm = !term || norm(c.getAttribute('data-search')).indexOf(term) !== -1;
      var vis = okCat && okTerm;
      c.style.display = vis ? '' : 'none';
      if(vis) shown++;
    });
    empty.hidden = shown !== 0;
  }
  q.addEventListener('input', apply);
  chipsEl.addEventListener('click', function(e){
    var b = e.target.closest('.chip'); if(!b) return;
    cat = b.getAttribute('data-cat');
    chipsEl.querySelectorAll('.chip').forEach(function(x){ x.classList.toggle('active', x===b); });
    apply();
  });
})();
</script>
<script src="${esc(TRACKING_SCRIPT)}" defer></script>
${cfBeacon(CFG)}
</body>
</html>
`;
  ensureDir(BLOG_OUT);
  fs.writeFileSync(path.join(BLOG_OUT, "index.html"), html, "utf8");
  console.log(`[ok] index -> ${BLOG_PATH}index.html (${articles.length} artigos)`);
}

function buildSitemap(articles) {
  const base = trimSlash(CFG.site.baseUrl);
  const urls = [joinUrl(base, BLOG_PATH)].concat(articles.map(a => joinUrl(base, blogUrl(a.slug))));
  const body = urls.map((u, i) => {
    const lastmod = i === 0 ? NOW : (articles[i - 1].lastmod || NOW);
    const pri = i === 0 ? "0.8" : "0.7";
    return `  <url>\n    <loc>${esc(u)}</loc>\n    <lastmod>${lastmod}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>${pri}</priority>\n  </url>`;
  }).join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
  fs.writeFileSync(path.join(OUT, "sitemap.xml"), xml, "utf8");
  console.log(`[ok] sitemap -> sitemap.xml (${urls.length} urls)`);

  // robots e llms são regenerados junto com o sitemap para nunca apontarem para conteúdo antigo.
  const robots = `User-agent: *\nAllow: /\n\nSitemap: ${joinUrl(base, "/sitemap.xml")}\n`;
  fs.writeFileSync(path.join(OUT, "robots.txt"), robots, "utf8");
  const llms = `# ${CFG.site.name}\n\n> ${CFG.site.tagline}\n\n## Artigos\n` +
    articles.map(a => `- [${a.title}](${joinUrl(base, blogUrl(a.slug))}): ${a.description}`).join("\n") + "\n";
  fs.writeFileSync(path.join(OUT, "llms.txt"), llms, "utf8");
  console.log(`[ok] robots.txt + llms.txt`);
}

function main() {
  ensureDir(BLOG_OUT);
  const only = process.argv[2];
  const files = fs.readdirSync(KW_DIR).filter(f => f.endsWith(".md"));
  if (only) {
    const want = only.replace(/\.md$/, "") + ".md";
    if (!files.includes(want)) { console.error(`Briefing não encontrado: ${want}`); process.exit(1); }
  }

  // Carrega todos para manter índice/sitemap completos mesmo em build incremental.
  const all = files.map(loadBriefing);
  const existing = new Set(all.map(a => a.slug));
  for (const fm of all) {
    if (Array.isArray(fm.related)) fm.related = fm.related.filter(r => existing.has(r.slug));
  }
  const articles = [];
  for (const fm of all) {
    if (only && fm.slug !== only.replace(/\.md$/, "")) {
      // Build incremental não reescreve os demais HTML, mas os mantém no índice.
      articles.push(articleSummary(fm));
      continue;
    }
    articles.push(buildArticle(fm));
  }
  buildIndex(articles);
  buildSitemap(articles);
  console.log(`\n✓ build concluído — ${articles.length} artigo(s). Saída em: ${OUT}`);
}

main();
