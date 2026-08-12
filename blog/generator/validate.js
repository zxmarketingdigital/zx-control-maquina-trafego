#!/usr/bin/env node
// validate.js — checklist SEO/técnico do artigo gerado. Sem dependências externas.
"use strict";
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "public");
const CFG = JSON.parse(fs.readFileSync(path.join(ROOT,"config.json"),"utf8"));
const BLOG_PATH = ((CFG.site && CFG.site.blogPath) || "/blog").replace(/\/+$/, "") || "/blog";
if (!process.argv[2]) { console.error("[validate] erro: slug obrigatório. Uso: node validate.js <slug>"); process.exit(1); }
const slug = process.argv[2];
const file = path.join(OUT, BLOG_PATH.replace(/^\/+/,""), slug, "index.html");
if (!fs.existsSync(file)) { console.error(`[validate] artigo não encontrado: ${file}`); process.exit(1); }
const html = fs.readFileSync(file,"utf8"), checks = [];
function check(name,pass,detail){checks.push({name,pass:!!pass,detail:detail||""});}

const h1s=(html.match(/<h1[\s>]/gi)||[]).length;
check("Exatamente 1 <h1>",h1s===1,`${h1s} encontrado(s)`);
const title=(html.match(/<title>([^<]+)<\/title>/i)||[])[1];
check("<title> presente e <=60 chars",!!title&&title.length<=60,title?`"${title}" (${title.length} chars)`:"ausente");
const desc=(html.match(/<meta name="description" content="([^"]+)"/i)||[])[1];
check("meta description presente (50-160)",desc&&desc.length>=50&&desc.length<=165,desc?`${desc.length} chars`:"ausente");
const canon=(html.match(/<link rel="canonical" href="([^"]+)"/i)||[])[1];
check("canonical presente",!!canon,canon||"ausente");
const ogTitle=/<meta property="og:title"/.test(html),ogImg=(html.match(/<meta property="og:image" content="([^"]+)"/i)||[])[1];
check("Open Graph (og:title + og:image)",ogTitle&&!!ogImg,ogImg||"");
check("Twitter card",/<meta name="twitter:card"/.test(html),"");
let ld=null,ldOk=false,types=[];const ldMatch=html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/i);
if(ldMatch)try{ld=JSON.parse(ldMatch[1]);ldOk=true;types=(ld["@graph"]||[ld]).map(g=>g["@type"])}catch(e){ldOk=false;}
check("JSON-LD válido (parse)",ldOk,ldOk?`tipos: ${types.join(", ")}`:"parse falhou");
check("Schema Article presente",types.includes("Article"),"");
check("Schema FAQPage presente",types.includes("FAQPage"),"");
check("Schema BreadcrumbList presente",types.includes("BreadcrumbList"),"");
const h2s=(html.match(/<h2[\s>]/gi)||[]).length;
check("Headings hierárquicos (>=2 <h2>)",h2s>=2,`${h2s} <h2>`);
const internalLinks=[...html.matchAll(/href="(\/[^"#]*?)"/g)].map(m=>m[1]),uniq=[...new Set(internalLinks)],broken=[];
for(const href of uniq){let p=path.join(OUT,href);if(href.endsWith("/"))p=path.join(p,"index.html");if(!fs.existsSync(p))broken.push(href);}
check("Links internos resolvem",broken.length===0,broken.length?`quebrados: ${broken.join(", ")}`:`${uniq.length} ok`);
const blogLinks=internalLinks.filter(l=>l.startsWith(BLOG_PATH+"/")&&l!==BLOG_PATH+"/"&&l!==BLOG_PATH+"/"+slug+"/");
const blogDir=path.join(OUT,BLOG_PATH.replace(/^\/+/,""));
let siblingCount=0;
try{siblingCount=fs.readdirSync(blogDir,{withFileTypes:true}).filter(d=>d.isDirectory()&&d.name!==slug&&fs.existsSync(path.join(blogDir,d.name,"index.html"))).length;}catch(e){siblingCount=0;}
check("Ao menos 1 link interno para outro artigo",siblingCount===0?true:blogLinks.length>=1,siblingCount===0?"não aplicável: nenhum outro artigo publicado ainda":(blogLinks.length?`${blogLinks.length}: ${blogLinks.slice(0,2).join(", ")}`:"nenhum"));
const products=Object.values(CFG.products||{}),lpProducts=products.filter(p=>p&&p.lp);
const hasCta=lpProducts.some(p=>html.includes(p.lp));
check("CTA com LP de produto presente",hasCta,"");
check("CTA externo com rel nofollow sponsored",/rel="nofollow sponsored"/.test(html),"");
check("Cor de acento âmbar #D97706 presente",/#D97706/.test(html),"");
check("Fontes Inter + JetBrains Mono",/Inter/.test(html)&&/JetBrains\+?Mono/.test(html),"");
const tracking=(CFG.site&&CFG.site.trackingScript)||"/tracking.js";
const trackingLocal=!/^https?:\/\//i.test(tracking)?fs.existsSync(path.join(OUT,tracking.replace(/^\/+/,""))):true;
check("Script de tracking embutido",html.includes(tracking)&&trackingLocal,"");
check("Resumo citável (TL;DR) presente",/Resumo citável/.test(html),"");
const banned=["ganhe dinheiro","renda garantida","dinheiro fácil","lucro garantido","fature 5 dígitos","r$500+"];const hits=banned.filter(b=>html.toLowerCase().includes(b));
check("Sem promessa de ganhos (política Google)",hits.length===0,hits.length?`proibidos: ${hits.join(", ")}`:"limpo");
const ogPath=ogImg?path.join(OUT,ogImg.replace(/^https?:\/\/[^/]+/,"")):null;let ogOk=false,ogDetail=ogPath?path.basename(ogPath):"";
if(ogPath&&fs.existsSync(ogPath)){const buf=fs.readFileSync(ogPath,"utf8").slice(0,20),isSvg=buf.includes("<svg")||buf.includes("<?xml");ogOk=!isSvg;ogDetail+=isSvg?" [ERRO: é SVG, não PNG/JPG]":" [PNG/JPG ok]";}
check("OG image existe e é PNG/JPG (não SVG)",ogOk,ogDetail);
check("sitemap.xml gerado",fs.existsSync(path.join(OUT,"sitemap.xml")),"");
check("robots.txt gerado",fs.existsSync(path.join(OUT,"robots.txt")),"");
check("llms.txt gerado (GEO)",fs.existsSync(path.join(OUT,"llms.txt")),"");
let passed=0;console.log(`\nCHECKLIST SEO — ${slug}\n${"=".repeat(50)}`);for(const c of checks){const mark=c.pass?"✓":"✗";if(c.pass)passed++;console.log(`${mark} ${c.name}${c.detail?"  ·  "+c.detail:""}`);}console.log("=".repeat(50));console.log(`${passed}/${checks.length} checks passaram`);process.exit(passed===checks.length?0:1);
