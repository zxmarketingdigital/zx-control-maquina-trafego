// Gera o texto da oferta em MD (WhatsApp + e-mail) a partir do MESMO data.json
// que alimenta as artes. Fonte única: mudou o preço no data.json, arte e texto
// saem atualizados juntos — nunca divergem.
// Uso: node gerar-texto.mjs <dir-do-projeto>
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const dir = resolve(process.argv[2] || process.cwd()) + '/';
if (!existsSync(dir + 'data.json')) {
  console.error(`ERRO: não achei ${dir}data.json`);
  process.exit(1);
}
const data = JSON.parse(readFileSync(dir + 'data.json', 'utf8'));

// Valida tudo antes de escrever qualquer arquivo, evitando uma mistura de
// textos novos e antigos quando há mais de um produto no data.json.
const OBRIGATORIOS = ['wordmark','badge','promessa','items','anchor','parcelado','avista',
                      'garantia','acesso','escassez','cta','rodape'];
const problemas = [];
for (const [chave, prod] of Object.entries(data)) {
  for (const campo of OBRIGATORIOS) {
    if (prod[campo] === undefined || prod[campo] === null || prod[campo] === '') {
      problemas.push(`${chave}: campo obrigatório ausente → ${campo}`);
    }
  }
  if (prod.items !== undefined && !Array.isArray(prod.items)) {
    problemas.push(`${chave}: items precisa ser lista`);
  } else if (Array.isArray(prod.items)) {
    prod.items.forEach((it, i) => {
      if (!it?.label) problemas.push(`${chave}: items[${i}] sem label`);
      if (!it?.price) problemas.push(`${chave}: items[${i}] sem price`);
    });
  }
}
if (problemas.length) {
  console.error('ERRO: data.json inválido — nada foi escrito.');
  problemas.forEach(p => console.error('  · ' + p));
  process.exit(1);
}

const arquivos = Object.fromEntries(
  Object.entries(data).map(([chave, prod]) => [chave, prod.slug || chave])
);

// WhatsApp usa *negrito* com UM asterisco e ~riscado~ com til
const wpp = d => {
  const L = [];
  L.push(`*${d.wordmark}*`);
  L.push(`_${d.badge}_`);
  L.push('');
  L.push(d.promessa);
  L.push('');
  L.push('*O QUE VOCÊ RECEBE:*');
  for (const it of d.items) {
    const nome = it.highlight ? `*${it.label}*` : it.label;
    L.push(`✅ ${nome} — ~${it.price}~`);
  }
  if (d.incluso) { L.push(''); L.push(d.incluso); }
  L.push('');
  L.push(`Valor total: ~${d.anchor.replace(/^De /, '')}~`);
  L.push(`👉 *${d.parcelado}*`);
  L.push(d.avista.replace(/^ou /, 'ou ').trim());
  L.push('');
  L.push(`🛡️ ${d.garantia}`);
  L.push(`⏳ ${d.acesso}`);
  L.push(`⚡ ${d.escassez}`);
  L.push('');
  L.push(`${d.cta}: ${d.checkout || 'https://' + d.rodape}`);
  return L.join('\n');
};

const email = d => {
  const L = [];
  L.push(`**Assunto:** ${d.wordmark} — ${d.parcelado} (${d.badge.split('·')[0].trim()})`);
  L.push('');
  L.push(`## ${d.wordmark}`);
  L.push('');
  L.push(`_${d.badge}_`);
  L.push('');
  L.push(d.promessa);
  L.push('');
  L.push('### O que está incluso');
  L.push('');
  L.push('| | Item | Valor |');
  L.push('|---|---|---|');
  for (const it of d.items) {
    const nome = it.highlight ? `**${it.label}**` : it.label;
    L.push(`| ✅ | ${nome} | ~~${it.price}~~ |`);
  }
  L.push(`| | **Valor total** | **~~${d.anchor.replace(/^De /, '')}~~** |`);
  if (d.incluso) { L.push(''); L.push(d.incluso); }
  L.push('');
  L.push(`### ${d.parcelado}`);
  L.push('');
  L.push(d.avista);
  L.push('');
  L.push(`- 🛡️ ${d.garantia}`);
  L.push(`- ⏳ ${d.acesso}`);
  L.push(`- ⚡ ${d.escassez}`);
  L.push('');
  L.push(`**[${d.cta}](${d.checkout || 'https://' + d.rodape})**`);
  return L.join('\n');
};

for (const [chave, slug] of Object.entries(arquivos)) {
  const d = data[chave];
  if (!d) continue;
  const md = [
    `# Oferta — ${d.wordmark}`,
    '',
    ' > Gerado de `data.json`. Não edite este arquivo à mão: altere o data.json e rode `node gerar-texto.mjs`.',
    '',
    '## WhatsApp (copiar e colar)',
    '',
    '```',
    wpp(d),
    '```',
    '',
    '## E-mail',
    '',
    email(d),
    '',
    '## Artes',
    '',
    `- Quadrado 1:1 — \`${slug}-oferta-quadrado.png\` (2160×2160)`,
    `- Story 9:16 — \`${slug}-oferta-story.png\` (2160×3840)`,
    '',
  ].join('\n');
  const out = `${slug}-oferta.md`;
  writeFileSync(dir + out, md);
  console.log('ok →', out);
}
console.log('textos gerados');
