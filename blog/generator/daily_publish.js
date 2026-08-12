#!/usr/bin/env node
// Pipeline diário de geração, validação e publicação do blog.
'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const os = require('os');

const GENERATOR = path.resolve(__dirname);
const ROOT = path.resolve(__dirname, '..');
const QUEUE = path.join(ROOT, 'queue.json');
const KW_DIR = path.join(ROOT, 'content', 'keywords');
const ARTICLES_DIR = path.join(ROOT, 'content', 'articles');
const PUBLIC = path.join(ROOT, 'public');
const DRAFTS = path.join(PUBLIC, 'drafts');
const KILLSWITCH = path.join(os.homedir(), '.operacao-ia', 'config', '.blog-killswitch');
const STATUS_FILE = path.join(PUBLIC, 'blog-status.json');
const AGENT = path.join(ROOT, 'agente', 'gerar_artigo.py');

let CONFIG = {};
try { CONFIG = JSON.parse(fs.readFileSync(path.join(ROOT, 'config.json'), 'utf8')); } catch (_) { CONFIG = {}; }

const args = process.argv.slice(2);
const DRY_RUN = args.includes('--dry-run');
const slugIndex = args.indexOf('--slug');
const FORCE_SLUG = slugIndex >= 0 ? args[slugIndex + 1] : null;
const LIST_MODE = args.includes('--list');

function log(message) { console.log(`[blog] ${message}`); }
function warn(message) { console.warn(`[blog][warn] ${message}`); }
function err(message) { console.error(`[blog][erro] ${message}`); }
function readQueue() {
  try { return JSON.parse(fs.readFileSync(QUEUE, 'utf8')); }
  catch (e) { throw new Error(`não foi possível ler queue.json: ${e.message}`); }
}
function writeQueue(queue) {
  if (DRY_RUN) { log('(dry-run) queue.json NÃO atualizado'); return; }
  fs.writeFileSync(QUEUE, JSON.stringify(queue, null, 2), 'utf8');
}
function writeStatus(data) {
  if (DRY_RUN) { log('(dry-run) blog-status.json NÃO atualizado'); return; }
  fs.mkdirSync(PUBLIC, { recursive: true });
  fs.writeFileSync(STATUS_FILE, JSON.stringify({ ...data, ts: new Date().toISOString(), dry_run: DRY_RUN }, null, 2), 'utf8');
}

const BANNED_PHRASES = [
  'ganhe dinheiro', 'renda garantida', 'dinheiro fácil',
  'lucro garantido', 'fature 5 dígitos', 'r$500+', 'retorno garantido',
  'rico com ia', 'enriqueça com ia', 'riqueza garantida', 'resultado garantido',
  'ganhos assegurados', 'renda passiva garantida', 'aposentado com ia',
  'aposentado financeiramente', 'retirado financeiramente'
];
function contentSafetyCheck(value) {
  const lower = String(value || '').toLowerCase();
  const hits = BANNED_PHRASES.filter(phrase => lower.includes(phrase));
  return { pass: hits.length === 0, hits };
}
function articleFilePath(slug) { return path.join(ARTICLES_DIR, `${slug}.json`); }
function hasArticleContent(slug) { return fs.existsSync(articleFilePath(slug)); }

function generateMissingArticle(target) {
  if (hasArticleContent(target.slug)) return true;
  if (DRY_RUN) {
    log(`(dry-run) python3 ../agente/gerar_artigo.py --slug ${target.slug} seria executado`);
    return false;
  }
  if (!fs.existsSync(AGENT)) {
    err(`agente de geração não encontrado: ${AGENT}`);
    return false;
  }
  log(`conteúdo ausente; gerando artigo com Gemini para ${target.slug}...`);
  let result;
  try {
    result = spawnSync('python3', [AGENT, '--slug', target.slug], { cwd: ROOT, encoding: 'utf8', timeout: 180000 });
  } catch (e) {
    err(`não foi possível iniciar o agente: ${e.message}`);
    return false;
  }
  if (result.stdout) console.log(result.stdout.trim());
  if (result.stderr) console.error(result.stderr.trim());
  if (result.error) { err(`agente de geração falhou: ${result.error.message}`); return false; }
  if (result.status !== 0) { err(`agente de geração retornou exit ${result.status == null ? 'indefinido' : result.status}`); return false; }
  if (!hasArticleContent(target.slug)) { err(`agente terminou sem criar content/articles/${target.slug}.json`); return false; }
  log(`artigo gerado: content/articles/${target.slug}.json`);
  return true;
}

function validateArticleShape(article, slug) {
  const problems = [], warnings = [];
  if (!article || typeof article !== 'object') return { problems: ['JSON raiz não é objeto'], warnings };
  if (!article.title || typeof article.title !== 'string') problems.push('title ausente/inválido');
  else if (article.title.length > 60) warnings.push(`title > 60 chars (${article.title.length}) — sufixo do site será omitido`);
  if (!article.description || typeof article.description !== 'string') problems.push('description ausente/inválido');
  else if (article.description.length > 165) problems.push(`description > 165 chars (${article.description.length})`);
  else if (article.description.length > 155) warnings.push(`description > 155 chars (${article.description.length})`);
  if (!article.keyword || typeof article.keyword !== 'string') problems.push('keyword ausente');
  if (!article.proofPoint || typeof article.proofPoint !== 'string') problems.push('proofPoint ausente');
  const products = Object.keys(CONFIG.products || {});
  if (!article.produto || typeof article.produto !== 'string') problems.push('produto inválido');
  else if (products.length && !products.includes(article.produto)) problems.push(`produto inválido (${article.produto})`);
  if (!Array.isArray(article.sections) || article.sections.length < 1) problems.push('sections vazio');
  else article.sections.forEach((section, index) => {
    if (!section || !section.h2) problems.push(`sections[${index}].h2 ausente`);
    if (!Array.isArray(section.points) || section.points.length < 1) problems.push(`sections[${index}].points vazio`);
  });
  if (!Array.isArray(article.faq) || article.faq.length < 1) problems.push('faq vazio');
  else article.faq.forEach((item, index) => { if (!item || !item.q || !item.a) problems.push(`faq[${index}] incompleto`); });
  if (article.slug && article.slug !== slug) problems.push(`slug do JSON (${article.slug}) difere do slug da fila (${slug})`);
  return { problems, warnings };
}

function loadArticleBriefing(keyword) {
  let article;
  try { article = JSON.parse(fs.readFileSync(articleFilePath(keyword.slug), 'utf8')); }
  catch (e) { throw new Error(`content/articles/${keyword.slug}.json com JSON inválido: ${e.message}`); }
  const result = validateArticleShape(article, keyword.slug);
  if (result.problems.length) throw new Error(`content/articles/${keyword.slug}.json reprovado no shape: ${result.problems.join('; ')}`);
  result.warnings.forEach(item => warn(`${keyword.slug}: ${item}`));
  return { keyword: article.keyword, slug: keyword.slug, produto: article.produto || keyword.produto, tier: keyword.tier, title: article.title, description: article.description, ogImage: `/assets/og-${keyword.slug}.png`, proofPoint: article.proofPoint, sections: article.sections, faq: article.faq, related: Array.isArray(article.related) ? article.related.slice() : [] };
}

function toYaml(frontmatter) {
  function scalar(value) {
    if (typeof value !== 'string') return JSON.stringify(value);
    return JSON.stringify(value);
  }
  function list(values, indent) {
    return values.map(item => {
      if (typeof item === 'string') return `${indent}- ${scalar(item)}`;
      const keys = Object.keys(item), first = keys[0];
      let output = `${indent}- ${first}: ${scalar(item[first])}`;
      keys.slice(1).forEach(key => { output += Array.isArray(item[key]) ? `\n${indent}  ${key}:\n${list(item[key], indent + '    ')}` : `\n${indent}  ${key}: ${scalar(item[key])}`; });
      return output;
    }).join('\n');
  }
  const lines = ['---'];
  Object.entries(frontmatter).forEach(([key, value]) => { if (Array.isArray(value)) { lines.push(`${key}:`); lines.push(list(value, '  ')); } else lines.push(`${key}: ${scalar(value)}`); });
  lines.push('---');
  return `${lines.join('\n')}\n`;
}
function xmlEsc(value) { return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function generateOgImage(keyword, frontmatter) {
  const site = CONFIG.site || {};
  const name = xmlEsc(site.name || 'Blog');
  const tagline = xmlEsc(site.tagline || 'Conteúdo educativo');
  const title = xmlEsc(frontmatter.title.length > 50 ? `${frontmatter.title.slice(0, 47)}...` : frontmatter.title);
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='630' viewBox='0 0 1200 630'><rect width='1200' height='630' fill='#0D0D0D'/><rect width='1200' height='4' fill='#D97706'/><text x='600' y='260' font-family='Arial,sans-serif' font-size='56' font-weight='800' fill='#FFFFFF' text-anchor='middle'>${title}</text><text x='600' y='350' font-family='Arial,sans-serif' font-size='28' fill='#D97706' text-anchor='middle'>${xmlEsc(keyword.keyword)}</text><text x='600' y='430' font-family='Arial,sans-serif' font-size='22' fill='#6B7280' text-anchor='middle'>${name} — ${tagline}</text></svg>`;
  const assets = path.join(PUBLIC, 'assets'), svgPath = path.join(assets, `og-${keyword.slug}.svg`), pngPath = path.join(assets, `og-${keyword.slug}.png`);
  fs.mkdirSync(assets, { recursive: true });
  if (DRY_RUN) { log(`(dry-run) OG image seria gerada: assets/og-${keyword.slug}.png`); return true; }
  fs.writeFileSync(svgPath, svg, 'utf8');
  const result = spawnSync('rsvg-convert', ['-w', '1200', '-h', '630', svgPath, '-o', pngPath], { encoding: 'utf8', timeout: 15000 });
  if (result.error || result.status !== 0 || !fs.existsSync(pngPath)) {
    fs.rmSync(pngPath, { force: true });
    warn(`rsvg-convert indisponível ou falhou (exit ${result.status == null ? 'indefinido' : result.status}) — OG image não gerada; instale rsvg-convert para publicar com imagem OG`);
    return false;
  }
  log(`OG image gerada: assets/og-${keyword.slug}.png`);
  return true;
}
function generateThumbnail(keyword, frontmatter) {
  const dir = path.join(PUBLIC, 'assets', 'thumbs'), output = path.join(dir, `${keyword.slug}.webp`), temporary = path.join(dir, `.${keyword.slug}.tmp.png`);
  if (fs.existsSync(output)) { log(`thumbnail já existe: assets/thumbs/${keyword.slug}.webp`); return; }
  if (!fs.existsSync(path.join(GENERATOR, 'thumb_prompt.js'))) { log('geração de thumbnail não incluída nesta instalação — seguindo sem imagem'); return; }
  if (DRY_RUN) { log(`(dry-run) thumbnail seria gerada: assets/thumbs/${keyword.slug}.webp`); return; }
  try {
    const promptModule = require('./thumb_prompt.js');
    const prompt = promptModule.buildThumbPrompt({ title: frontmatter.title, keyword: keyword.keyword, tier: frontmatter.tier });
    const script = path.join(os.homedir(), '.claude', 'skills', 'gerar-imagem', 'scripts', 'gerar.py');
    const optimizer = path.join(GENERATOR, 'optimize_thumb.py');
    if (!fs.existsSync(script) || !fs.existsSync(optimizer)) { warn('gerador de thumbnail não disponível — seguindo sem imagem'); return; }
    fs.mkdirSync(dir, { recursive: true });
    const generated = spawnSync('python3', [script, '--prompt', prompt, '--output', temporary, '--size', '1280x720', '--provider', 'auto', '--json'], { encoding: 'utf8', timeout: 200000 });
    if (generated.status !== 0 || !fs.existsSync(temporary)) { warn(`thumbnail não gerada (exit ${generated.status}) — seguindo sem imagem`); return; }
    const optimized = spawnSync('python3', [optimizer, '--in', temporary, '--out', output], { encoding: 'utf8', timeout: 30000 });
    fs.rmSync(temporary, { force: true });
    if (optimized.status === 0 && fs.existsSync(output)) log(`thumbnail gerada: assets/thumbs/${keyword.slug}.webp`);
    else warn('otimização da thumbnail falhou — seguindo sem imagem');
  } catch (e) { fs.rmSync(temporary, { force: true }); warn(`thumbnail falhou (${e.message}) — seguindo sem imagem`); }
}
function runValidate(slug) {
  const result = spawnSync('node', [path.join(GENERATOR, 'validate.js'), slug], { encoding: 'utf8', cwd: ROOT, timeout: 30000 });
  const output = (result.stdout || '') + (result.stderr || '');
  console.log(output);
  const match = output.match(/(\d+)\/(\d+) checks passaram/);
  return { pass: result.status === 0, score: match ? Number(match[1]) : 0, total: match ? Number(match[2]) : 23 };
}
function markStatus(queue, slug, status) { const item = queue.keywords.find(entry => entry.slug === slug); if (item) { item.status = status; item._published_at = new Date().toISOString(); } }
function moveToDraft(slug, reason) {
  const source = path.join(PUBLIC, 'blog', slug), destination = path.join(DRAFTS, slug);
  if (fs.existsSync(source) && !DRY_RUN) { fs.mkdirSync(destination, { recursive: true }); fs.cpSync(source, destination, { recursive: true }); fs.rmSync(source, { recursive: true, force: true }); warn(`artigo movido para drafts/${slug}: ${reason}`); }
}

function main() {
  const logDir = path.join(__dirname, 'logs'), logFiles = [path.join(logDir, 'blog-daily.log'), path.join(logDir, 'blog-daily-err.log')], limit = 5 * 1024 * 1024;
  logFiles.forEach(file => { try { if (fs.existsSync(file) && fs.statSync(file).size > limit) { const backup = `${file}.1`; if (fs.existsSync(backup)) fs.unlinkSync(backup); fs.renameSync(file, backup); } } catch (_) {} });
  log(`=== Blog Daily Publish ${DRY_RUN ? '[DRY-RUN]' : '[PRODUÇÃO]'} ===`);
  if (fs.existsSync(KILLSWITCH)) { log(`Killswitch ativo (${KILLSWITCH}). Abortando publicação.`); writeStatus({ last_run: new Date().toISOString(), killswitch_active: true, articles_published: 0, last_error: null }); return 2; }

  const initialQueue = readQueue();
  const missing = initialQueue.keywords.filter(item => item.status === 'done' && !fs.existsSync(path.join(PUBLIC, 'blog', item.slug, 'index.html'))).map(item => item.slug);
  if (missing.length) { warn(`artigo(s) órfão(s): ${missing.join(', ')}`); writeStatus({ last_run: new Date().toISOString(), missing_articles: missing, articles_published: 0, last_error: null }); }
  if (LIST_MODE) {
    const pending = initialQueue.keywords.filter(item => item.status === 'pending'), done = initialQueue.keywords.filter(item => item.status === 'done'), drafts = initialQueue.keywords.filter(item => item.status === 'draft');
    console.log(`\nFila de keywords (${initialQueue.keywords.length} total):`); console.log(`  pending: ${pending.length} | done: ${done.length} | draft: ${drafts.length}\n`); console.log('PRÓXIMAS (pending):'); pending.slice(0, 5).forEach(item => console.log(`  [${item.id}] ${item.slug} — tier: ${item.tier}`)); console.log('\nCONCLUÍDOS (done):'); done.forEach(item => console.log(`  [${item.id}] ${item.slug}`)); if (drafts.length) { console.log('\nREPROVADOS (draft):'); drafts.forEach(item => console.log(`  [${item.id}] ${item.slug}`)); } return 0;
  }

  const queue = initialQueue;
  let target;
  if (FORCE_SLUG) { target = queue.keywords.find(item => item.slug === FORCE_SLUG); if (!target) throw new Error(`slug não encontrado na fila: ${FORCE_SLUG}`); }
  else { target = queue.keywords.find(item => item.status === 'pending'); if (!target) { log('Nenhuma keyword pendente. Fila completa.'); writeStatus({ last_run: new Date().toISOString(), queue_empty: true, articles_published: 0, last_error: null }); return 0; } }
  log(`Keyword alvo: ${target.keyword} (${target.slug}) [tier: ${target.tier}]`);

  if (!hasArticleContent(target.slug) && !generateMissingArticle(target)) {
    const reason = DRY_RUN ? 'awaiting_content' : `generation_fail: ${target.slug}`;
    log(DRY_RUN ? `aguardando conteúdo: ${target.slug}` : `geração falhou para ${target.slug}. Nada publicado.`);
    writeStatus({ last_run: new Date().toISOString(), articles_published: 0, awaiting_content: target.slug, last_error: reason });
    return 3;
  }
  if (!hasArticleContent(target.slug)) { writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `generation_fail: ${target.slug}` }); return 3; }

  const articleDir = path.join(PUBLIC, 'blog', target.slug);
  if (fs.existsSync(path.join(articleDir, 'index.html')) && !FORCE_SLUG) { log(`Artigo já existe em public/blog/${target.slug}/ — confirmando rebuild antes de marcar done.`); if (!DRY_RUN) { const rebuild = spawnSync('node', [path.join(GENERATOR, 'build.js')], { encoding: 'utf8', cwd: ROOT, timeout: 60000 }); if (rebuild.stdout) console.log(rebuild.stdout); if (rebuild.stderr) console.error(rebuild.stderr); if (rebuild.error || rebuild.status !== 0) { err(`rebuild index/sitemap falhou (exit ${rebuild.status == null ? 'indefinido' : rebuild.status})`); writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `rebuild_fail: ${target.slug}` }); return 9; } markStatus(queue, target.slug, 'done'); writeQueue(queue); } writeStatus({ last_run: new Date().toISOString(), articles_published: 0, skipped: target.slug, last_error: null }); return 0; }
  log('Fase 1: carregando conteúdo gerado...');
  let frontmatter;
  try { frontmatter = loadArticleBriefing(target); } catch (e) { err(`Conteúdo inválido para ${target.slug}: ${e.message}. Nada publicado.`); writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `content_invalid: ${target.slug}` }); return 4; }
  const have = new Set(frontmatter.related.map(item => item.slug));
  const addRelated = (slug, title) => { if (slug && slug !== target.slug && !have.has(slug)) { frontmatter.related.push({ slug, title }); have.add(slug); } };
  const spokes = queue.keywords.filter(item => (item.spoke_of === target.id || item.spoke_of === target.slug) && item.status === 'done').slice(0, 3);
  const parent = target.spoke_of ? queue.keywords.find(item => (item.id === target.spoke_of || item.slug === target.spoke_of) && item.status === 'done') : null;
  if (parent) addRelated(parent.slug, `Guia: ${parent.keyword}`);
  spokes.forEach(item => addRelated(item.slug, item.keyword));
  if (!frontmatter.related.length) queue.keywords.filter(item => item.status === 'done' && item.slug !== target.slug).slice(0, 2).forEach(item => addRelated(item.slug, item.keyword));

  log('Fase 2: content safety check...');
  const yaml = toYaml(frontmatter), safety = contentSafetyCheck(yaml);
  if (!safety.pass) { err(`SAFETY GATE: artigo ${target.slug} reprovado. Frases proibidas: ${safety.hits.join(', ')}`); if (!DRY_RUN) { fs.mkdirSync(DRAFTS, { recursive: true }); fs.writeFileSync(path.join(DRAFTS, `${target.slug}.md`), yaml, 'utf8'); markStatus(queue, target.slug, 'draft'); writeQueue(queue); } writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `safety_fail: ${target.slug}`, safety_hits: safety.hits }); return 5; }
  log('Safety OK — sem frases proibidas.');
  log('Fase 3: gravando briefing + OG image...');
  if (!DRY_RUN) { fs.mkdirSync(KW_DIR, { recursive: true }); fs.writeFileSync(path.join(KW_DIR, `${target.slug}.md`), yaml, 'utf8'); } else log(`(dry-run) briefing NÃO gravado em content/keywords/${target.slug}.md`);
  if (!generateOgImage(target, frontmatter)) { writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `og_image_fail: ${target.slug}` }); return 6; }
  generateThumbnail(target, frontmatter);
  log('Fase 4: buildando HTML...');
  if (!DRY_RUN) { const build = spawnSync('node', [path.join(GENERATOR, 'build.js'), target.slug], { encoding: 'utf8', cwd: ROOT, timeout: 60000 }); if (build.stdout) console.log(build.stdout); if (build.stderr) console.error(build.stderr); if (build.status !== 0) { err(`build.js falhou (exit ${build.status})`); writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `build_fail: ${target.slug}` }); return 7; } } else log(`(dry-run) node generator/build.js ${target.slug} NÃO executado`);
  log('Fase 5: quality gate — validate.js...');
  if (!DRY_RUN) { const validation = runValidate(target.slug); if (!validation.pass) { err(`Quality gate REPROVADO: ${validation.score}/${validation.total} checks. Movendo para drafts.`); moveToDraft(target.slug, `validate: ${validation.score}/${validation.total}`); markStatus(queue, target.slug, 'draft'); writeQueue(queue); writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `validate_fail: ${validation.score}/${validation.total}`, target: target.slug }); return 8; } log(`Quality gate APROVADO: ${validation.score}/${validation.total}`); } else log(`(dry-run) validate.js ${target.slug} NÃO executado`);
  log('Fase 6: rebuild index/sitemap antes de marcar done...');
  if (!DRY_RUN) { const rebuild = spawnSync('node', [path.join(GENERATOR, 'build.js')], { encoding: 'utf8', cwd: ROOT, timeout: 60000 }); if (rebuild.stdout) console.log(rebuild.stdout); if (rebuild.stderr) console.error(rebuild.stderr); if (rebuild.error || rebuild.status !== 0) { err(`rebuild index/sitemap falhou (exit ${rebuild.status == null ? 'indefinido' : rebuild.status})`); writeStatus({ last_run: new Date().toISOString(), articles_published: 0, last_error: `rebuild_fail: ${target.slug}` }); return 9; } markStatus(queue, target.slug, 'done'); writeQueue(queue); } else log('(dry-run) rebuild e queue não executados');
  const pending = queue.keywords.filter(item => item.status === 'pending').length, done = queue.keywords.filter(item => item.status === 'done').length;
  log(`Publicação concluída: ${target.slug}`); log(`Fila: ${done} done, ${pending} pending`);
  writeStatus({ last_run: new Date().toISOString(), articles_published: DRY_RUN ? 0 : 1, last_published: target.slug, queue_pending: pending, queue_done: done, last_error: null });
  return 0;
}

try { process.exitCode = main(); } catch (e) { err(`erro não tratado: ${e.message}`); process.exit(99); }
