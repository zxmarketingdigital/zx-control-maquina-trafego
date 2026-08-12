/* zx-tracking.js — atribuição multicanal (Etapa 5 / Etapa 6 do Setup 15).
 * Captura utm/gclid/referrer na LP ou no blog, classifica o canal e injeta um `sck` (e os
 * utm_*/gclid) como query string nos links de checkout que usam esse padrão (ex.: Hotmart
 * `?sck=`). Plataformas que exigem um formato próprio de atribuição (ex.: `saleMetas` da
 * Greenn) precisam de um adaptador dedicado — este script não gera esse formato.
 *
 * REGRA DE OURO: nunca sobrescreve um sck já presente (preserva a atribuição de um anúncio
 * que já embute o próprio sck). Só gera sck quando há sinal de outro canal.
 *
 * Carregar: <script src="/tracking.js" defer></script>
 */
(function () {
  "use strict";
  var KEY = "zx_tracking";
  var p = new URLSearchParams(location.search);

  function host(u) { try { return new URL(u).hostname.toLowerCase(); } catch (e) { return ""; } }

  // Classifica o canal a partir dos sinais do clique.
  function classify(t) {
    var h = host(document.referrer);
    var sck = (t.sck || "").toLowerCase();
    if (sck.indexOf("google-") === 0) return { channel: "google_ads", source: "google" };
    if (sck.indexOf("organic-") === 0) return { channel: "organic_search", source: "google" };
    if (sck.indexOf("ia-") === 0) return { channel: "ia", source: sck.split("-")[1] || "ia" };
    if (t.gclid) return { channel: "google_ads", source: "google" };
    if ((t.utm_source || "").match(/google|adwords/) || t.utm_medium === "cpc") return { channel: "google_ads", source: "google" };
    if ((t.utm_source || "").match(/facebook|instagram|meta|^fb$|^ig$/)) return { channel: "meta_ads", source: "meta" };
    if (t.utm_source) return { channel: t.utm_source, source: t.utm_source };
    if (/chatgpt\.com|openai\.com/.test(h)) return { channel: "ia", source: "chatgpt" };
    if (/perplexity\.ai/.test(h)) return { channel: "ia", source: "perplexity" };
    if (/gemini\.google\.com/.test(h)) return { channel: "ia", source: "gemini" };
    if (/google\.|bing\.com|duckduckgo/.test(h)) return { channel: "organic_search", source: "google" };
    if (h) return { channel: "referral", source: h };
    return { channel: "direct", source: null };
  }

  var t = {
    utm_source: p.get("utm_source"), utm_medium: p.get("utm_medium"),
    utm_campaign: p.get("utm_campaign"), gclid: p.get("gclid"),
    sck: p.get("sck"), referrer: document.referrer || null,
  };
  var c = classify(t);

  // First-touch persiste; last-touch sempre atualiza.
  var stored = {};
  try { stored = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
  var now = (Date.now ? Date.now() : new Date().getTime());
  var data = {
    first: stored.first || merge({ ts: now }, t, c),
    last: merge({ ts: now }, t, c),
  };
  try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) {}

  function merge() {
    var o = {};
    for (var i = 0; i < arguments.length; i++) { var s = arguments[i]; for (var k in s) if (s.hasOwnProperty(k)) o[k] = s[k]; }
    return o;
  }

  // Gera o sck por canal (prefixo consumido pelo classificador de canal de venda).
  function buildSck(d) {
    var camp = (d.utm_campaign || "").replace(/[^a-z0-9-]/gi, "").toLowerCase();
    if (d.channel === "google_ads") return "google-" + (camp || "search");
    if (d.channel === "organic_search") return "organic-" + (d.source || "google");
    if (d.channel === "ia") return "ia-" + (d.source || "ia");
    return null; // meta_ads/direct/referral: não injeta (o anúncio já tem sck próprio)
  }

  window.zxApplyTracking = function () {
    var d = data.last;
    var links = document.querySelectorAll('a[href*="pagar.me"], a[href*="hotmart.com"], a[href*="pay.hotmart"], a[href*="greenn.com.br"], a.btn-buy');
    // Preferência do sck a injetar: sck que veio na URL da página (preserva o anúncio) > sck gerado por canal.
    var sckToInject = d.sck || buildSck(d);
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      try {
        var u = new URL(a.href, location.href);
        // NUNCA sobrescreve sck já presente no link (o anúncio pode tê-lo fixado).
        if (!u.searchParams.get("sck") && sckToInject) u.searchParams.set("sck", sckToInject);
        if (d.utm_source && !u.searchParams.get("utm_source")) u.searchParams.set("utm_source", d.utm_source);
        if (d.utm_medium && !u.searchParams.get("utm_medium")) u.searchParams.set("utm_medium", d.utm_medium);
        if (d.utm_campaign && !u.searchParams.get("utm_campaign")) u.searchParams.set("utm_campaign", d.utm_campaign);
        if (d.gclid && !u.searchParams.get("gclid")) u.searchParams.set("gclid", d.gclid);
        a.href = u.toString();
      } catch (e) {}
    }
  };

  if (document.readyState !== "loading") window.zxApplyTracking();
  else document.addEventListener("DOMContentLoaded", window.zxApplyTracking);
  // Reaplica em cliques tardios (links inseridos por JS depois do load).
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (a && /pagar\.me|hotmart\.com|pay\.hotmart|greenn\.com\.br/.test(a.href)) window.zxApplyTracking();
  }, true);
  // Reaplica quando o DOM muda (links injetados dinamicamente).
  if (typeof MutationObserver !== "undefined") {
    try { new MutationObserver(window.zxApplyTracking).observe(document.documentElement, { childList: true, subtree: true }); } catch (e) {}
  }
})();
