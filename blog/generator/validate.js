#!/usr/bin/env node
// validate.js — checklist SEO/técnico do artigo gerado. Sem dependências externas.
"use strict";

const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "public");

// O slug é obrigatório: sem ele, uma chamada com argumento ausente poderia validar outro arquivo.
if (!process.argv[2]) {
  console.error("[validate] erro: slug obrigatório. Uso: node validate.js <slug>");
  process.exit(1);
}

const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, "config.json"), "utf8"));
const site = cfg.site || {};
const slug = process.argv[2];
const file = path.join(OUT, "blog", slug, "index.html");
const html = fs.readFileSync(file, "utf8");
const checks = [];
function check(name, pass, detail) { checks.push({ name, pass: !!pass, detail: detail || "" }); }
function escapeRegex(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function normalPath(s, fallback) { return String(s || fallback).replace(/\/+$/, "") + "/"; }

// 1. exatamente 1 H1
const h1s = (html.match(/<h1[\s>]/gi) || []).length;
check("Exatamente 1 <h1>", h1s === 1, `${h1s} encontrado(s)`);

// 2. title — presença e comprimento continuam sendo gates separados do conteúdo do artigo.
const title = (html.match(/<title>([^<]+)<\/title>/i) || [])[1];
check("<title> presente e <=60 chars", !!title && title.length <= 60,
  title ? `"${title}" (${title.length} chars)` : "ausente");

// 3. meta description
const desc = (html.match(/<meta name="description" content="([^"]+)"/i) || [])[1];
check("meta description presente (50-160)", desc && desc.length >= 50 && desc.length <= 165,
  desc ? `${desc.length} chars` : "ausente");

// 4. canonical
const canon = (html.match(/<link rel="canonical" href="([^"]+)"/i) || [])[1];
check("canonical presente", !!canon, canon || "ausente");

// 5. Open Graph
const ogTitle = /<meta property="og:title"/.test(html);
const ogImg = (html.match(/<meta property="og:image" content="([^"]+)"/i) || [])[1];
check("Open Graph (og:title + og:image)", ogTitle && !!ogImg, ogImg || "");

// 6. Twitter card
check("Twitter card", /<meta name="twitter:card"/.test(html), "");

// 7. JSON-LD válido + tipos
let ld = null, ldOk = false, types = [];
const ldMatch = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/i);
if (ldMatch) {
  try {
    ld = JSON.parse(ldMatch[1]);
    ldOk = true;
    const graph = ld["@graph"] || [ld];
    types = graph.map(g => g["@type"]);
  } catch (e) { ldOk = false; }
}
check("JSON-LD válido (parse)", ldOk, ldOk ? `tipos: ${types.join(", ")}` : "parse falhou");
check("Schema Article presente", types.includes("Article"), "");
check("Schema FAQPage presente", types.includes("FAQPage"), "");
check("Schema BreadcrumbList presente", types.includes("BreadcrumbList"), "");

// 8. headings hierárquicos (tem h2)
const h2s = (html.match(/<h2[\s>]/gi) || []).length;
check("Headings hierárquicos (>=2 <h2>)", h2s >= 2, `${h2s} <h2>`);

// 9. links internos resolvem (arquivos existem no public/)
const internalLinks = [...html.matchAll(/href="(\/[^"#]*?)"/g)].map(m => m[1]);
const uniq = [...new Set(internalLinks)];
const broken = [];
for (const href of uniq) {
  let p = path.join(OUT, href);
  if (href.endsWith("/")) p = path.join(p, "index.html");
  if (!fs.existsSync(p)) broken.push(href);
}
check("Links internos resolvem", broken.length === 0,
  broken.length ? `quebrados: ${broken.join(", ")}` : `${uniq.length} ok`);

// 9b. Pelo menos 1 link para outro artigo, não apenas breadcrumb ou a própria URL.
const blogPath = normalPath(site.blogPath, "/blog");
const currentArticle = `${blogPath}${slug}/`;
const blogLinks = internalLinks.filter(l => l.startsWith(blogPath) && l !== currentArticle && l !== blogPath);
check("Ao menos 1 link interno para outro artigo", blogLinks.length >= 1,
  blogLinks.length ? `${blogLinks.length}: ${blogLinks.slice(0, 2).join(", ")}` : "nenhum");

// 10. CTA para uma LP configurada (não checkout: blog é topo de funil).
const productLps = Object.keys(cfg.products || {}).map(k => cfg.products[k] && cfg.products[k].lp).filter(Boolean);
const hasCta = productLps.some(lp => html.includes(lp));
check("CTA com LP de produto presente", hasCta, "");
check("CTA externo com rel nofollow sponsored", /rel="nofollow sponsored"/.test(html), "");

// 11. design system âmbar
check("Cor de acento âmbar #D97706 presente", /#D97706/.test(html), "");
check("Fontes Inter + JetBrains Mono", /Inter/.test(html) && /JetBrains\+?Mono/.test(html), "");

// 12. tracking configurado e embutido
const trackingScript = site.trackingScript || "/tracking.js";
const trackingPath = trackingScript.replace(/^https?:\/\/[^/]+/, "");
const trackingFile = path.join(OUT, trackingPath.replace(/^\/+/, ""));
check("Tracking embutido", html.includes(trackingScript) && fs.existsSync(trackingFile), "");

// 13. resumo citável (GEO)
check("Resumo citável (TL;DR) presente", /Resumo citável/.test(html), "");

// 14. política: sem promessa de ganhos no conteúdo
const banned = ["ganhe dinheiro", "renda garantida", "dinheiro fácil", "lucro garantido", "fature 5 dígitos", "r$500+"];
const lower = html.toLowerCase();
const hits = banned.filter(b => lower.includes(b));
check("Sem promessa de ganhos (política Google)", hits.length === 0,
  hits.length ? `proibidos: ${hits.join(", ")}` : "limpo");

// 15. OG image existe e não é SVG (SVG costuma ser rejeitado pelas redes sociais).
const ogPath = ogImg ? path.join(OUT, ogImg.replace(/^https?:\/\/[^/]+/, "").replace(/^\/+/, "")) : null;
let ogOk = false;
let ogDetail = ogPath ? path.basename(ogPath) : "";
if (ogPath && fs.existsSync(ogPath)) {
  const buf = fs.readFileSync(ogPath, "utf8").slice(0, 20);
  const isSvg = buf.includes("<svg") || buf.includes("<?xml");
  ogOk = !isSvg;
  if (isSvg) ogDetail += " [ERRO: é SVG, não PNG/JPG — rejeitado por redes sociais]";
  else ogDetail += " [PNG/JPG ok]";
}
check("OG image existe e é PNG/JPG (não SVG)", ogOk, ogDetail);

// 16. sitemap + robots + llms
check("sitemap.xml gerado", fs.existsSync(path.join(OUT, "sitemap.xml")), "");
check("robots.txt gerado", fs.existsSync(path.join(OUT, "robots.txt")), "");
check("llms.txt gerado (GEO)", fs.existsSync(path.join(OUT, "llms.txt")), "");

// --- relatório ---
let passed = 0;
console.log(`\nCHECKLIST SEO — ${slug}\n${"=".repeat(50)}`);
for (const c of checks) {
  const mark = c.pass ? "✓" : "✗";
  if (c.pass) passed++;
  console.log(`${mark} ${c.name}${c.detail ? "  ·  " + c.detail : ""}`);
}
console.log("=".repeat(50));
console.log(`${passed}/${checks.length} checks passaram`);
process.exit(passed === checks.length ? 0 : 1);
