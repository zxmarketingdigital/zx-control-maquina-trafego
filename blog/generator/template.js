// template.js — componentes HTML do gerador, sem dependências externas.
"use strict";

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function blogPath(cfg) {
  return ((cfg && cfg.site && cfg.site.blogPath) || "/blog").replace(/\/+$/, "") || "/blog";
}

function absoluteUrl(cfg, value) {
  var base = ((cfg && cfg.site && cfg.site.baseUrl) || "").replace(/\/+$/, "");
  var item = String(value || "");
  if (/^https?:\/\//i.test(item)) return item;
  return base + "/" + item.replace(/^\/+/, "");
}

// O beacon é opcional para que o build local e instalações sem analytics continuem funcionando.
function cfBeacon(cfg) {
  var token = ((cfg && cfg.analytics && cfg.analytics.cfBeaconToken) || "").trim();
  if (!token) return "";
  return '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" ' +
    'data-cf-beacon=\' {"token":"' + esc(token) + '"}\'></script>'.replace("\' {", "\'{");
}

function css() {
  return `
:root{--primary:#D97706;--primary-light:#F59E0B;--primary-bright:#FCD34D;--primary-dark:#92400e;--bg:#0D0D0D;--bg-alt:#0A0A0A;--surface:#1A1A1A;--surface2:#222;--footer:#080808;--text:#E2E8F0;--text-2:#9CA3AF;--text-muted:#6B7280;--border:#2A2A2A;--border-light:#333;--green:#4ADE80}
*{box-sizing:border-box;margin:0;padding:0}html{scroll-behavior:smooth}body{font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased;background-image:linear-gradient(rgba(217,119,6,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(217,119,6,.025) 1px,transparent 1px);background-size:60px 60px}a{color:var(--primary-light);text-decoration:none}a:hover{color:var(--primary-bright)}.wrap{max-width:760px;margin:0 auto;padding:0 20px}.wrap-wide{max-width:1100px;margin:0 auto;padding:0 20px}header.site{border-bottom:1px solid var(--border);background:var(--bg-alt);position:sticky;top:0;z-index:10;backdrop-filter:blur(8px)}header.site .wrap-wide{display:flex;align-items:center;justify-content:space-between;height:64px}.brand{display:flex;align-items:center;gap:10px;font-family:'JetBrains Mono',monospace;font-weight:700;letter-spacing:.08em;color:var(--text);font-size:.95rem}.brand img{height:26px;width:26px}.brand .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px rgba(74,222,128,.6)}main{padding:48px 0 0}.badge{display:inline-block;background:rgba(217,119,6,.15);border:1px solid rgba(217,119,6,.3);color:var(--primary-light);border-radius:100px;font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:6px 16px}.crumb{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--text-muted);margin:18px 0 8px}nav.crumb a{color:var(--text-2)}h1{font-size:2.4rem;font-weight:800;line-height:1.15;margin:14px 0 16px;color:#fff}.meta-line{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--text-muted);margin-bottom:32px;display:flex;gap:16px;flex-wrap:wrap}.tldr{background:var(--surface);border:1px solid var(--border-light);border-left:3px solid var(--primary);border-radius:14px;padding:20px 24px;margin:0 0 36px}.tldr .label,.proof .label,.cta-card .k,.related .label{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:var(--primary-light);text-transform:uppercase;display:block;margin-bottom:8px}.tldr p{color:var(--text);font-size:1rem}article h2{font-size:1.6rem;font-weight:800;color:#fff;margin:40px 0 14px}article h3{font-size:1.1rem;font-weight:800;color:var(--text);margin:24px 0 8px}article p{margin:0 0 16px;color:var(--text-2)}article ul{margin:0 0 20px;padding-left:0;list-style:none}article ul li{position:relative;padding:8px 0 8px 28px;color:var(--text-2);border-bottom:1px solid var(--border)}article ul li:before{content:"";position:absolute;left:6px;top:16px;width:7px;height:7px;border-radius:2px;background:var(--primary)}.proof{background:linear-gradient(135deg,rgba(217,119,6,.08),rgba(217,119,6,.02));border:1px solid rgba(217,119,6,.3);border-radius:16px;padding:24px;margin:32px 0;box-shadow:0 0 60px rgba(217,119,6,.08)}.proof p{color:var(--text);margin:0;font-weight:500}.cta-card{background:var(--surface);border:1px solid rgba(217,119,6,.3);border-radius:24px;padding:32px;margin:44px 0;text-align:center;box-shadow:0 0 60px rgba(217,119,6,.1);position:relative;overflow:hidden}.cta-card:before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--primary-dark),var(--primary),var(--primary-light))}.cta-card h3{font-size:1.4rem;color:#fff;margin:10px 0 8px;font-weight:800}.cta-card p{color:var(--text-2);margin:0 auto 22px;max-width:480px}.btn{display:inline-block;background:var(--primary);color:#000;font-weight:800;font-size:1rem;border-radius:12px;padding:16px 36px;transition:transform .15s,background .15s}.btn:hover{transform:translateY(-2px);background:var(--primary-light);color:#000}.price{font-family:'JetBrains Mono',monospace;color:var(--primary-bright);font-weight:700;margin-top:12px;display:block;font-size:.85rem}.faq{margin:44px 0}.faq h2{margin-bottom:8px}details{background:var(--surface);border:1px solid var(--border-light);border-radius:12px;margin:10px 0}details summary{cursor:pointer;padding:18px 22px;font-weight:700;color:var(--text);list-style:none;display:flex;justify-content:space-between;align-items:center}details summary::-webkit-details-marker{display:none}details summary:after{content:"+";font-family:'JetBrains Mono',monospace;color:var(--primary-light);font-size:1.3rem}details[open] summary:after{content:"−"}details .a{padding:0 22px 18px;color:var(--text-2)}.related{margin:48px 0;border-top:1px solid var(--border);padding-top:28px}.related a{display:block;background:var(--surface);border:1px solid var(--border-light);border-radius:14px;padding:16px 20px;margin:8px 0;color:var(--text);font-weight:600}.related a:hover{transform:translateY(-3px);border-color:rgba(217,119,6,.3);color:var(--text)}footer.site{border-top:1px solid var(--border);background:var(--footer);margin-top:64px;padding:36px 0;color:var(--text-muted);font-size:.82rem}footer.site .wrap-wide{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}footer.site .mono{font-family:'JetBrains Mono',monospace}@media(max-width:600px){h1{font-size:1.8rem}article h2{font-size:1.35rem}}
`;
}

function promoBar(product) {
  if (!product) return "";
  return '<div class="promo" style="background:#17120b;border-bottom:1px solid rgba(217,119,6,.25);padding:8px 20px;text-align:center;font:12px JetBrains Mono,monospace;color:#FCD34D">' +
    esc(product.name) + ' · <a href="' + esc(product.lp || "#") + '" rel="nofollow sponsored">saiba mais</a></div>';
}

function productShowcase(products, options) {
  var entries = Object.keys(products || {}).map(function (key) { return { key: key, product: products[key] }; });
  if (options && options.only && products[options.only]) entries = [{ key: options.only, product: products[options.only] }];
  if (!entries.length) return "";
  var e = entries[0], p = e.product;
  return '<aside class="showcase" style="background:var(--surface);border:1px solid rgba(217,119,6,.3);border-radius:16px;padding:22px;margin:24px 0;text-align:center">' +
    '<small style="font:11px JetBrains Mono,monospace;color:var(--primary-light);text-transform:uppercase">' + esc((options && options.title) || "Produto em destaque") + '</small>' +
    '<h2 style="font-size:1.3rem;color:#fff;margin:8px 0">' + esc(p.name) + '</h2><p style="color:var(--text-2);margin:0 0 14px">' + esc(p.pitch) + '</p>' +
    '<a class="btn" href="' + esc(p.lp || "#") + '" rel="nofollow sponsored">' + esc(p.cta || "Conhecer produto") + '</a></aside>';
}

function renderSections(sections) {
  return (sections || []).map(function (s) {
    var li = (s.points || []).map(function (p) { return "      <li>" + esc(p) + "</li>"; }).join("\n");
    return "    <h2>" + esc(s.h2) + "</h2>\n    <ul>\n" + li + "\n    </ul>";
  }).join("\n\n");
}

function renderFaq(faq) {
  if (!faq || !faq.length) return "";
  var items = faq.map(function (f) { return '    <details>\n      <summary>' + esc(f.q) + '</summary>\n      <div class="a">' + esc(f.a) + '</div>\n    </details>'; }).join("\n");
  return '  <section class="faq">\n    <h2>Perguntas frequentes</h2>\n' + items + "\n  </section>";
}

function renderRelated(related, cfg) {
  if (!related || !related.length) return "";
  var path = blogPath(cfg);
  var links = related.map(function (r) { return '    <a href="' + path + '/' + esc(r.slug) + '/">' + esc(r.title) + "</a>"; }).join("\n");
  return '  <section class="related">\n    <span class="label">Continue lendo</span>\n' + links + "\n  </section>";
}

function jsonLd(fm, cfg, url) {
  var base = (cfg.site.baseUrl || "").replace(/\/+$/, "");
  var graph = [{
    "@type":"Article","headline":fm.title,"description":fm.description,"inLanguage":cfg.site.lang,
    "datePublished":fm.datePublished,"dateModified":fm.dateModified,
    "author":{"@type":"Organization","name":cfg.site.author},
    "publisher":{"@type":"Organization","name":cfg.site.publisher,"logo":{"@type":"ImageObject","url":absoluteUrl(cfg,cfg.site.logo)}},
    "mainEntityOfPage":{"@type":"WebPage","@id":url},"image":absoluteUrl(cfg,fm.ogImage || cfg.site.defaultOgImage)
  }, {"@type":"BreadcrumbList","itemListElement":[
    {"@type":"ListItem","position":1,"name":"Blog","item":base + blogPath(cfg) + "/"},
    {"@type":"ListItem","position":2,"name":fm.title,"item":url}
  ]}];
  if (fm.faq && fm.faq.length) graph.push({"@type":"FAQPage","mainEntity":fm.faq.map(function(f){return {"@type":"Question","name":f.q,"acceptedAnswer":{"@type":"Answer","text":f.a}};})});
  return JSON.stringify({"@context":"https://schema.org","@graph":graph}, null, 2).replace(/</g,"\\u003c");
}

function renderArticle(fm, cfg) {
  var product = cfg.products && cfg.products[fm.produto];
  var base = (cfg.site.baseUrl || "").replace(/\/+$/, "");
  var path = blogPath(cfg);
  var url = base + path + "/" + fm.slug + "/";
  var ogImg = absoluteUrl(cfg, fm.ogImage || cfg.site.defaultOgImage);
  var suffix = fm.title + " | " + cfg.site.name;
  var seoTitle = suffix.length <= 60 ? suffix : (fm.title.length <= 60 ? fm.title : fm.title.slice(0,57).replace(/\s+\S*$/, "") + "…");
  var ctaHtml = product ? '<aside class="cta-card"><span class="k">Produto recomendado</span><h3>' + esc(product.name) + '</h3><p>' + esc(product.pitch) + '</p><a class="btn" href="' + esc(product.lp || "#") + '" rel="nofollow sponsored">' + esc(product.cta || "Conhecer produto") + '</a>' + (product.price ? '<span class="price">' + esc(product.price) + '</span>' : '') + '</aside>' : "";
  var tracking = (cfg.site.trackingScript || "/tracking.js");
  return `<!DOCTYPE html>
<html lang="${esc(cfg.site.lang)}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(seoTitle)}</title><meta name="description" content="${esc(fm.description)}"><link rel="canonical" href="${url}"><meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="article"><meta property="og:title" content="${esc(fm.title)}"><meta property="og:description" content="${esc(fm.description)}"><meta property="og:url" content="${url}"><meta property="og:image" content="${ogImg}"><meta property="og:site_name" content="${esc(cfg.site.name)}"><meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${esc(fm.title)}"><meta name="twitter:description" content="${esc(fm.description)}"><meta name="twitter:image" content="${ogImg}">
<link rel="icon" href="${esc(cfg.site.favicon || "/assets/favicon-32.png")}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet"><style>${css()}</style>
<script type="application/ld+json">${jsonLd(fm,cfg,url)}</script>${cfBeacon(cfg)}
</head><body>${promoBar(product)}
<header class="site"><div class="wrap-wide"><a class="brand" href="${path}/"><img src="${esc(cfg.site.logo)}" alt="${esc(cfg.site.name)}" width="26" height="26"><span>${esc(cfg.site.name)}</span><span class="dot" title="online"></span></a><nav style="font-family:'JetBrains Mono',monospace;font-size:.78rem"><a href="${path}/">blog</a></nav></div></header>
<main><div class="wrap"><nav class="crumb"><a href="${path}/">~/blog</a> / ${esc(fm.slug)}</nav><span class="badge">${esc(fm.tier === "pillar" ? "Guia completo" : "Artigo")}</span><h1>${esc(fm.title)}</h1>
<div class="meta-line"><span>${esc(cfg.site.author)}</span><span>Atualizado: ${esc(String(fm.dateModified).slice(0,10))}</span><span>Palavra-chave: ${esc(fm.keyword)}</span></div><div class="tldr"><span class="label">Resumo citável</span><p>${esc(fm.description)}</p></div><article>
${renderSections(fm.sections)}
<div class="proof"><span class="label">// Evidência própria</span><p>${esc(fm.proofPoint)}</p></div>${ctaHtml}</article>${renderFaq(fm.faq)}${renderRelated(fm.related,cfg)}</div></main>
<footer class="site"><div class="wrap-wide"><span class="mono">${esc(cfg.site.name)} — ${esc(cfg.site.tagline)}</span><span class="mono"><a href="/sitemap.xml">sitemap</a> · <a href="${esc(base)}">site principal</a></span></div></footer>
<script src="${esc(tracking)}" defer></script></body></html>`;
}

module.exports = { renderArticle, css, esc, cfBeacon, promoBar, productShowcase, absoluteUrl, blogPath }; 
