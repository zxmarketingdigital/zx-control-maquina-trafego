// template.js — renderiza o HTML de um artigo com os dados do site configurado.
// O CSS fica inline para o deploy estático não depender de build de frontend.
"use strict";

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function trimSlash(s) { return String(s || "").replace(/\/+$/, ""); }

function joinUrl(base, part) {
  if (/^https?:\/\//i.test(String(part || ""))) return String(part);
  return trimSlash(base) + "/" + String(part || "").replace(/^\/+/, "");
}

function sitePath(cfg, key, fallback) {
  return (cfg && cfg.site && cfg.site[key]) || fallback;
}

// Beacon opcional: token vazio/ausente omite a tag e não quebra o build.
// O token é preenchido somente no go-live, nunca precisa ser commitado no repositório.
function cfBeacon(cfg) {
  var token = ((cfg && cfg.analytics && cfg.analytics.cfBeaconToken) || "").trim();
  if (!token) return "";
  return '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" ' +
    'data-cf-beacon=\'{"token":"' + esc(token) + '"}\'></script>';
}

// CSS do design system âmbar, inline para manter o motor autossuficiente.
function css() {
  return `
:root{
  --primary:#D97706;--primary-light:#F59E0B;--primary-bright:#FCD34D;--primary-dark:#92400e;
  --bg:#0D0D0D;--bg-alt:#0A0A0A;--surface:#1A1A1A;--surface2:#222222;--footer:#080808;
  --text:#E2E8F0;--text-2:#9CA3AF;--text-muted:#6B7280;--border:#2A2A2A;--border-light:#333333;
  --green:#4ADE80;--red:#EF4444;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);
  line-height:1.7;-webkit-font-smoothing:antialiased;
  background-image:linear-gradient(rgba(217,119,6,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(217,119,6,.025) 1px,transparent 1px);
  background-size:60px 60px;
}
a{color:var(--primary-light);text-decoration:none}
a:hover{color:var(--primary-bright)}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}
.wrap-wide{max-width:1100px;margin:0 auto;padding:0 20px}
header.site{border-bottom:1px solid var(--border);background:var(--bg-alt);position:sticky;top:0;z-index:10;backdrop-filter:blur(8px)}
header.site .wrap-wide{display:flex;align-items:center;justify-content:space-between;height:64px}
.brand{display:flex;align-items:center;gap:10px;font-family:'JetBrains Mono',monospace;font-weight:700;letter-spacing:.08em;color:var(--text);font-size:.95rem}
.brand img{height:26px;width:26px}
.brand .dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px rgba(74,222,128,.6)}
main{padding:48px 0 0}
.badge{display:inline-block;background:rgba(217,119,6,.15);border:1px solid rgba(217,119,6,.3);color:var(--primary-light);border-radius:100px;font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:6px 16px;font-family:'Inter',sans-serif}
nav.crumb{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--text-muted);margin:18px 0 8px}
nav.crumb a{color:var(--text-2)}
h1{font-family:'Inter',sans-serif;font-size:2.4rem;font-weight:800;letter-spacing:-.01em;line-height:1.15;margin:14px 0 16px;color:#fff}
.meta-line{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--text-muted);margin-bottom:32px;display:flex;gap:16px;flex-wrap:wrap}
.tldr{background:var(--surface);border:1px solid var(--border-light);border-left:3px solid var(--primary);border-radius:14px;padding:20px 24px;margin:0 0 36px}
.tldr .label{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:var(--primary-light);text-transform:uppercase;display:block;margin-bottom:8px}
.tldr p{color:var(--text);font-size:1rem}
article h2{font-family:'Inter',sans-serif;font-size:1.6rem;font-weight:800;color:#fff;margin:40px 0 14px;letter-spacing:-.01em}
article h3{font-size:1.1rem;font-weight:800;color:var(--text);margin:24px 0 8px}
article p{margin:0 0 16px;color:var(--text-2)}
article ul{margin:0 0 20px;padding-left:0;list-style:none}
article ul li{position:relative;padding:8px 0 8px 28px;color:var(--text-2);border-bottom:1px solid var(--border)}
article ul li:before{content:"";position:absolute;left:6px;top:16px;width:7px;height:7px;border-radius:2px;background:var(--primary)}
.proof{background:linear-gradient(135deg,rgba(217,119,6,.08),rgba(217,119,6,.02));border:1px solid rgba(217,119,6,.3);border-radius:16px;padding:24px;margin:32px 0;box-shadow:0 0 60px rgba(217,119,6,.08)}
.proof .label{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:var(--primary-bright);text-transform:uppercase;display:block;margin-bottom:8px}
.proof p{color:var(--text);margin:0;font-weight:500}
.cta-card{background:var(--surface);border:1px solid rgba(217,119,6,.3);border-radius:24px;padding:32px;margin:44px 0;text-align:center;box-shadow:0 0 60px rgba(217,119,6,.1);position:relative;overflow:hidden}
.cta-card:before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--primary-dark),var(--primary),var(--primary-light))}
.cta-card .k{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:var(--primary-light);text-transform:uppercase}
.cta-card h3{font-size:1.4rem;color:#fff;margin:10px 0 8px;font-weight:800}
.cta-card p{color:var(--text-2);margin:0 auto 22px;max-width:480px}
.btn{display:inline-block;background:var(--primary);color:#000;font-weight:800;font-size:1rem;border-radius:12px;padding:16px 36px;letter-spacing:.01em;transition:transform .15s,background .15s}
.btn:hover{transform:translateY(-2px);background:var(--primary-light);color:#000}
.price{font-family:'JetBrains Mono',monospace;color:var(--primary-bright);font-weight:700;margin-top:12px;display:block;font-size:.85rem}
.faq{margin:44px 0}
.faq h2{margin-bottom:8px}
details{background:var(--surface);border:1px solid var(--border-light);border-radius:12px;margin:10px 0;padding:0}
details summary{cursor:pointer;padding:18px 22px;font-weight:700;color:var(--text);list-style:none;display:flex;justify-content:space-between;align-items:center}
details summary::-webkit-details-marker{display:none}
details summary:after{content:"+";font-family:'JetBrains Mono',monospace;color:var(--primary-light);font-size:1.3rem}
details[open] summary:after{content:"\\2212"}
details .a{padding:0 22px 18px;color:var(--text-2)}
.related{margin:48px 0;border-top:1px solid var(--border);padding-top:28px}
.related .label{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:var(--primary-light);text-transform:uppercase;display:block;margin-bottom:14px}
.related a{display:block;background:var(--surface);border:1px solid var(--border-light);border-radius:14px;padding:16px 20px;margin:8px 0;color:var(--text);font-weight:600;transition:transform .15s,border-color .15s}
.related a:hover{transform:translateY(-3px);border-color:rgba(217,119,6,.3);color:var(--text)}
footer.site{border-top:1px solid var(--border);background:var(--footer);margin-top:64px;padding:36px 0;color:var(--text-muted);font-size:.82rem}
footer.site .wrap-wide{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
footer.site .mono{font-family:'JetBrains Mono',monospace}
@media (max-width:600px){h1{font-size:1.8rem}article h2{font-size:1.35rem}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
`;
}

// Componentes de oferta. Eles substituem a dependência específica do projeto original;
// os textos, URLs e preços vêm exclusivamente do objeto products do config.json.
function salesCss() {
  return `
.promo{background:linear-gradient(90deg,rgba(217,119,6,.18),rgba(217,119,6,.06));border-bottom:1px solid rgba(217,119,6,.25);padding:10px 20px;text-align:center;font-size:.84rem}
.promo a{font-weight:700;margin-left:8px}
.showcase{margin:28px 0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.showcase-title{grid-column:1/-1;font-family:'JetBrains Mono',monospace;color:var(--primary-light);font-size:.75rem;letter-spacing:.1em;text-transform:uppercase}
.showcase-card{background:var(--surface);border:1px solid rgba(217,119,6,.25);border-radius:16px;padding:18px;display:flex;flex-direction:column}
.showcase-card h3{font-size:1.05rem;color:#fff;margin:0 0 8px}
.showcase-card p{color:var(--text-2);font-size:.88rem;margin:0 0 14px;flex:1}
.showcase-card .btn{font-size:.85rem;padding:10px 16px;text-align:center}
@media(max-width:600px){.showcase{grid-template-columns:1fr}}
`;
}

function promoBar(product, key, cfg) {
  if (!product || !product.lp) return "";
  var label = sitePath(cfg, "productLabel", "Oferta recomendada");
  return '<div class="promo">' + esc(label) + ': <strong>' + esc(product.name) + '</strong>' +
    ' <a href="' + esc(product.lp) + '" rel="nofollow sponsored">' + esc(product.cta || "Saiba mais") + ' →</a></div>';
}

function productShowcase(products, options, cfg) {
  var entries = Object.keys(products || {}).map(function (key) {
    return { key: key, product: products[key] };
  }).filter(function (entry) { return entry.product && entry.product.name && entry.product.lp; });
  if (!entries.length) return "";
  var title = (options && options.title) || sitePath(cfg, "productShowcaseTitle", "Conheça as ofertas");
  var cards = entries.map(function (entry) {
    var p = entry.product;
    return '<article class="showcase-card">' +
      '<h3>' + esc(p.name) + '</h3>' +
      '<p>' + esc(p.pitch || "") + '</p>' +
      '<a class="btn" href="' + esc(p.lp) + '" rel="nofollow sponsored">' + esc(p.cta || "Saiba mais") + '</a>' +
      '</article>';
  }).join("\n");
  return '<section class="showcase"><span class="showcase-title">' + esc(title) + '</span>' + cards + '</section>';
}

function renderSections(sections) {
  return (sections || []).map(function (s) {
    var li = (s.points || []).map(function (p) { return "      <li>" + esc(p) + "</li>"; }).join("\n");
    return "    <h2>" + esc(s.h2) + "</h2>\n    <ul>\n" + li + "\n    </ul>";
  }).join("\n\n");
}

function renderFaq(faq) {
  if (!faq || !faq.length) return "";
  var items = faq.map(function (f) {
    return '    <details>\n      <summary>' + esc(f.q) + '</summary>\n      <div class="a">' + esc(f.a) + '</div>\n    </details>';
  }).join("\n");
  return '  <section class="faq">\n    <h2>Perguntas frequentes</h2>\n' + items + "\n  </section>";
}

function renderRelated(related, blogPath) {
  if (!related || !related.length) return "";
  var base = String(blogPath || "/blog/").replace(/\/+$/, "");
  var links = related.map(function (r) {
    return '    <a href="' + base + "/" + esc(r.slug) + '/">' + esc(r.title) + "</a>";
  }).join("\n");
  return '  <section class="related">\n    <span class="label">Continue lendo</span>\n' + links + "\n  </section>";
}

// JSON-LD: Article + FAQPage + BreadcrumbList num único @graph.
function jsonLd(fm, cfg, url) {
  var site = cfg.site;
  var base = trimSlash(site.baseUrl);
  var blogPath = sitePath(cfg, "blogPath", "/blog/");
  var image = joinUrl(base, fm.ogImage || site.defaultOgImage);
  var graph = [
    {
      "@type": "Article",
      "headline": fm.title,
      "description": fm.description,
      "inLanguage": site.lang,
      "datePublished": fm.datePublished,
      "dateModified": fm.dateModified,
      "author": { "@type": "Organization", "name": site.author },
      "publisher": {
        "@type": "Organization", "name": site.publisher,
        "logo": { "@type": "ImageObject", "url": joinUrl(base, site.logo) }
      },
      "mainEntityOfPage": { "@type": "WebPage", "@id": url },
      "image": image
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "position": 1, "name": "Blog", "item": joinUrl(base, blogPath) },
        { "@type": "ListItem", "position": 2, "name": fm.title, "item": url }
      ]
    }
  ];
  if (fm.faq && fm.faq.length) {
    graph.push({
      "@type": "FAQPage",
      "mainEntity": fm.faq.map(function (f) {
        return { "@type": "Question", "name": f.q, "acceptedAnswer": { "@type": "Answer", "text": f.a } };
      })
    });
  }
  return JSON.stringify({ "@context": "https://schema.org", "@graph": graph }, null, 2);
}

function renderArticle(fm, cfg) {
  var site = cfg.site;
  var base = trimSlash(site.baseUrl);
  var blogPath = sitePath(cfg, "blogPath", "/blog/");
  var homeUrl = sitePath(cfg, "homeUrl", site.baseUrl);
  var favicon = sitePath(cfg, "favicon", site.logo);
  var trackingScript = sitePath(cfg, "trackingScript", "/tracking.js");
  var prod = cfg.products && cfg.products[fm.produto];
  var url = joinUrl(base, blogPath + String(fm.slug).replace(/^\/+/, "") + "/");
  var ogImg = joinUrl(base, fm.ogImage || site.defaultOgImage);
  // O <title> da SERP é limitado sem alterar H1, Open Graph ou JSON-LD.
  var withSuffix = fm.title + " | " + site.name;
  var seoTitle = withSuffix.length <= 60 ? withSuffix
    : (fm.title.length <= 60 ? fm.title : fm.title.slice(0, 57).replace(/\s+\S*$/, "") + "…");
  var ctaHtml = prod ? (
    '  <aside class="cta-card">\n' +
    '    <span class="k">' + esc(site.productLabel || "Oferta recomendada") + '</span>\n' +
    "    <h3>" + esc(prod.name) + "</h3>\n" +
    "    <p>" + esc(prod.pitch || "") + "</p>\n" +
    '    <a class="btn" href="' + esc(prod.lp) + '" rel="nofollow sponsored">' + esc(prod.cta || "Saiba mais") + "</a>\n" +
    (prod.price ? '    <span class="price">' + esc(prod.price) + "</span>\n" : "") +
    "  </aside>"
  ) : "";

  return `<!DOCTYPE html>
<html lang="${esc(site.lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(seoTitle)}</title>
<meta name="description" content="${esc(fm.description)}">
<link rel="canonical" href="${esc(url)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="article">
<meta property="og:title" content="${esc(fm.title)}">
<meta property="og:description" content="${esc(fm.description)}">
<meta property="og:url" content="${esc(url)}">
<meta property="og:image" content="${esc(ogImg)}">
<meta property="og:site_name" content="${esc(site.name)}">
<meta property="og:locale" content="${esc(site.locale || site.lang)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(fm.title)}">
<meta name="twitter:description" content="${esc(fm.description)}">
<meta name="twitter:image" content="${esc(ogImg)}">
<link rel="icon" href="${esc(favicon)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>${css()}${salesCss()}</style>
<script type="application/ld+json">
${jsonLd(fm, cfg, url)}
</script>
${cfBeacon(cfg)}
</head>
<body>
${prod ? promoBar(prod, fm.produto, cfg) : ""}
<header class="site">
  <div class="wrap-wide">
    <a class="brand" href="${esc(blogPath)}"><img src="${esc(site.logo)}" alt="${esc(site.name)}" width="26" height="26"><span>${esc(site.name)}</span><span class="dot" title="online"></span></a>
    <nav style="font-family:'JetBrains Mono',monospace;font-size:.78rem"><a href="${esc(blogPath)}">blog</a></nav>
  </div>
</header>
<main>
  <div class="wrap">
    <nav class="crumb"><a href="${esc(blogPath)}">~/blog</a> / ${esc(fm.slug)}</nav>
    <span class="badge">${esc(fm.tier === "pillar" ? "Guia completo" : "Artigo")}</span>
    <h1>${esc(fm.title)}</h1>
    <div class="meta-line">
      <span>${esc(site.author)}</span>
      <span>Atualizado: ${esc(String(fm.dateModified || "").slice(0, 10))}</span>
      <span>Palavra-chave: ${esc(fm.keyword)}</span>
    </div>
    <div class="tldr">
      <span class="label">Resumo citável</span>
      <p>${esc(fm.description)}</p>
    </div>
    <article>
${renderSections(fm.sections)}

      <div class="proof">
        <span class="label">// Dado próprio</span>
        <p>${esc(fm.proofPoint)}</p>
      </div>
${ctaHtml}
    </article>
${renderFaq(fm.faq)}
${renderRelated(fm.related, blogPath)}
  </div>
</main>
<footer class="site">
  <div class="wrap-wide">
    <span class="mono">${esc(site.footerText || site.name)}</span>
    <span class="mono"><a href="/sitemap.xml">sitemap</a> · <a href="${esc(homeUrl)}">${esc(site.homeLabel || "início")}</a></span>
  </div>
</footer>
<script src="${esc(trackingScript)}" defer></script>
</body>
</html>
`;
}

module.exports = { renderArticle, css, esc, cfBeacon, salesCss, promoBar, productShowcase, joinUrl, trimSlash };
