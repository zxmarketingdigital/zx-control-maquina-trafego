// ⭐ ÚNICO ARQUIVO QUE VOCÊ EDITA por anúncio. Troque a copy/oferta e renderize.
// NUNCA inventar bullets ou preço — puxar da LP / CLAUDE.md do produto.
export type Seg = { t: string; amber?: boolean; b?: boolean };

// 🔴 Os valores abaixo são placeholders DELIBERADAMENTE FALSOS (não são número/preço real).
// Edite TODOS antes de renderizar — não publique este vídeo com esses valores.
export const content = {
  // Cena 1 — hook (tipografia cinética). Uma linha por item; amber destaca.
  brandKicker: '// [PREENCHA]',
  hookLines: [
    { t: '[EDITE ESTA' },
    { t: 'LINHA]', amber: true },
    { t: '[COM SUA' },
    { t: 'PROMESSA REAL]' },
  ] as { t: string; amber?: boolean }[],

  // Cena 2 — contador + gráfico crescendo (data-driven). NÃO renderize com este número —
  // ele não é um resultado real, é só a demonstração do efeito visual do contador.
  counter: {
    label: '[SUA MÉTRICA AQUI]',
    target: 0, // 🔴 substitua por um número REAL antes de renderizar — 0 não anima o contador
    bars: [
      { m: 'JAN', v: 0.18 },
      { m: 'FEV', v: 0.34 },
      { m: 'MAR', v: 0.55 },
      { m: 'ABR', v: 0.78 },
      { m: 'MAI', v: 1.0 }, // a última barra é a destacada (âmbar)
    ] as { m: string; v: number }[],
  },

  // Cena 3 — oferta + confete. Preço âncora (riscado) → preço final.
  offer: {
    pre: [{ t: 'Você recebe ' }, { t: 'tudo isso', amber: true }, { t: ' por' }] as Seg[],
    oldPrice: 'R$[PREÇO_DE]',
    newPrice: 'R$[PREÇO_POR]',
    chips: ['[item 1]', '[item 2]', '[item 3]', '[item 4]'],
  },

  // Cena 4 — CTA. NÃO desenhar botão real na base — o botão "Saiba mais" é do Meta.
  cta: {
    headline: [{ t: 'Comece ' }, { t: 'hoje', amber: true }, { t: ' por R$[PREÇO_POR]' }] as Seg[],
    button: '[Texto do seu CTA]',
    hint: [{ t: 'Clique em ' }, { t: '"Saiba mais"', b: true }, { t: ' aqui embaixo' }] as Seg[],
  },
};
