---
name: criar-arte-oferta
description: "Gera a arte de oferta de qualquer produto no formato validado (ancoragem de valor + checklist com valor de cada item + valor original riscado + parcelado dominante + garantia/prazo + escassez + CTA), em 2 formatos de imagem (quadrado 1:1 2160x2160 e story 9:16 2160x3840), mais texto pronto em Markdown para WhatsApp e e-mail — tudo a partir de um data.json único. Use quando o usuário pedir arte de oferta, banner de oferta, arte com preço, arte de ancoragem, criativo de oferta, arte para comercial, banner de checkout, arte para LP com preço, oferta visual ou texto de oferta para WhatsApp/e-mail."
model: sonnet
effort: medium
---

# /criar-arte-oferta — peça-mãe da oferta em imagem + texto

Esta skill produz a peça canônica de ancoragem de valor para LP, checkout, WhatsApp,
e-mail e anúncios a partir de uma única fonte de verdade: `data.json`. O motor
HTML→PNG é determinístico e é o caminho padrão para listas e preços densos; o gerador
de imagem pode criar uma variação visual opcional.

## Regras invioláveis

1. **MOTOR: HTML→PNG é o DEFAULT.** Use `scripts/render.mjs`, que renderiza o card com
   preço e texto exatamente como estão no `data.json`. Para uma variação visual, use o
   helper generalizado do repositório:
   `python3 skills/gerar-imagem/scripts/gerar.py --prompt "..." --output X.png`.
   O helper usa Gemini como caminho padrão e possui fallbacks configurados no próprio
   script; `gpt-image-2` pode ser uma opção quando estiver disponível, mas não é
   requisito.
   - Faça QA visual obrigatório em cada PNG, conferindo preço dígito por dígito,
     percentual do badge e acentuação em português.
   - Prefira HTML→PNG quando a peça tiver tabela/lista longa, exigir correspondência
     exata com `data.json` ou for uma regeneração em que só o preço mudou.
2. **O parcelado é o maior elemento do card.** Para produto acima de R$97, destaque o
   parcelado, não o à vista. O à vista fica como linha secundária. Se o checkout cobra
   juros no parcelado, use a taxa real do SEU gateway; nunca dividir preço÷12 sem juros
   se o cliente paga juros de verdade — isso subestima a parcela.
3. **Item em destaque SEMPRE em 1º lugar** na lista, ocupando a linha inteira no
   quadrado. É o carro-chefe da oferta.
4. **Todo item leva seu valor de “de” riscado** em produto high/mid ticket. Exceção:
   produto de entrada (R$17–R$97) não leva valor por item; a ancoragem fica somente em
   `De R$97 por R$37`, com a lista de entregas sem coluna de preço e sem linha de valor
   total. No padrão high/mid ticket, a soma dos itens é a âncora. Se remover um item,
   recalcule a âncora e o percentual do badge.
5. **Nenhum item pode quebrar linha ou cortar em “…”** — o cliente precisa ler tudo que
   está levando. O template faz o auto-ajuste.
6. **Botão CTA âmbar chapado**, sem glow, sombra ou gradiente.
7. **Nada que faz parte da oferta fica sem preço.** Se é entregue, é item e soma na
   âncora: comunidade, suporte, bônus e acesso entram como entregas explícitas. A linha
   discreta abaixo da lista é para observação de escopo, não para esconder entregável.
8. **Acesso vitalício com escopo limitado exige observação explícita.** Diga exatamente
   qual versão, conteúdo ou período está incluído. Faça o mesmo para o prazo do suporte.
9. **Prova social é sempre REAL.** Se a peça levar depoimento, nome, selo, número de
   alunos ou resultado, ele tem que ser real do seu negócio — nunca invente citação nem
   número. Se você não tem depoimento ainda, não inclua o elemento.

## Anatomia (9 elementos, nesta ordem)

| # | Elemento | Campo no `data.json` |
|---|---|---|
| 1 | Wordmark + badge (desconto/turma) | `wordmark`, `badge` |
| 2 | Promessa (headline curta) | `promessa` |
| 3 | Checklist — 1º item = destaque | `items[]` (`label`, `price`, `highlight`) |
| 4 | Inclusos sem preço (linha corrida) | `incluso` |
| 5 | Valor original riscado (âncora = soma) | `anchor` |
| 6 | **Parcelado (DOMINANTE)** | `parcelado` |
| 7 | À vista + prazo de acesso | `avista` |
| 8 | Garantia · acesso · escassez | `garantia`, `acesso`, `escassez` |
| 9 | CTA + rodapé (domínio) | `cta`, `checkout`, `rodape` |

Extras: `slug` (nome dos arquivos), `theme` (`amber` ou `amber-blue`) e `bg`.

## Inputs

Se o usuário não trouxer, pergunte antes de gerar:

- produto, preço à vista e **parcelado real** (conferido no gateway, não estimado);
- lista de itens inclusos com o valor “de” de cada um;
- item em destaque, garantia, prazo de acesso e escassez com data real;
- checkout, domínio/rodapé e CTA.

Se precisar montar a lista de itens, deixe claro quais valores foram arbitrados para
aprovação. Não invente data de escassez nem publique preço estimado sem avisar.

## Fluxo

1. Crie uma pasta de projeto com `data.json` no formato de
   `references/data-exemplo.json`.
2. Gere as duas imagens:
   `node ~/.claude/skills/criar-arte-oferta/scripts/render.mjs <dir-do-projeto>`.
3. Gere o texto da mesma fonte:
   `node ~/.claude/skills/criar-arte-oferta/scripts/gerar-texto.mjs <dir-do-projeto>`.
4. Faça QA visual obrigatório em **cada** PNG: preços corretos, zero “…” inesperado,
   zero quebra de linha, sem buraco preto, parcelado dominante, destaque em 1º e badge
   coerente com âncora ÷ preço.
5. Se a arte virar criativo de anúncio Meta, rode o gate de safe-zone antes de mostrar
   para aprovação.

## Safe-zone — QA antes de mostrar um criativo Meta

O Meta sobrepõe elementos no topo e na base de Stories/Reels. Rode:

```bash
zx-safezone <slug>-oferta-quadrado.png --derivar
```

Audite o master e o derivado. Se o helper informar `DERIVAÇÃO NÃO SERVE aqui`, gere o
9:16 nativo, com tudo entre 14% e 75% da altura. `Exit 1` significa não mostrar nem
publicar: regenere a peça. Para vídeo, use `zx-safezone <arquivo>.mp4 --modo stories`.

## Saídas

Na pasta do projeto:

- `<slug>-oferta-quadrado.png` — 2160×2160;
- `<slug>-oferta-story.png` — 2160×3840;
- `<slug>-oferta.md` — bloco WhatsApp (`*negrito*`, `~riscado~`, emojis), bloco de
  e-mail e referência das artes.

## Como o auto-ajuste funciona

O template escala tudo por `--k` e busca o maior valor que ainda cabe. O ajuste é
bidirecional: cresce e encolhe para preencher a altura sem cortar conteúdo.

- `semQuebra()` trava apenas o crescimento quando um rótulo passaria de uma linha; no
  encolhimento há um piso para rótulos longos não derrubarem a escala inteira.
- O preço é medido no próprio `.parcelado`, que usa `nowrap` e pode transbordar para
  dentro do padding sem alterar `card.scrollWidth`.
- Não use `scrollWidth <= clientWidth - N`: um filho full-width já ocupa toda a largura
  e faria a escala colapsar no mínimo.
- A folga vertical é distribuída com `justify-content: space-between` no `.wrap`; não
  use `margin-top:auto` no CTA.

No quadrado, até 10 itens usam coluna única automática para manter rótulos legíveis.

## Dependências

- Playwright (JS) e Google Chrome instalado; o template usa `channel: 'chrome'`.
- Instale a dependência na própria pasta da skill: `npm install playwright`.
- Fontes Inter e JetBrains Mono via Google Fonts (rede necessária no render).

## Não fazer

- Não edite o `.md` gerado à mão; altere `data.json` e regenere arte e texto.
- Não invente depoimento, aluno, número, resultado ou data de escassez.
- Não deixe a âncora divergente da soma dos itens.
- Não publique arte com preço estimado sem avisar que é estimativa.
