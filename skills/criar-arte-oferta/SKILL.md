---
name: criar-arte-oferta
description: 'Gera uma arte de oferta com ancoragem de valor, checklist de entregas, preço parcelado em destaque, garantia, escassez e CTA, em formatos quadrado e story, além do texto pronto para WhatsApp e e-mail a partir de um data.json único.'
model: sonnet
effort: medium
---

# /criar-arte-oferta — peça de oferta em imagem + texto

Esta skill produz uma peça de ancoragem de valor para qualquer produto, em todas as superfícies necessárias: LP, checkout, WhatsApp, e-mail, anúncio e material comercial. Imagens e textos são gerados a partir de uma única fonte de verdade: o `data.json`.

## Regras invioláveis

1. **Fonte única de verdade.** O preço, a lista de entregas, o parcelado, a garantia, o acesso, a escassez e o CTA devem vir do mesmo `data.json` usado para gerar as artes e o texto.
2. **Parcelado em destaque.** Para produtos acima de R$97, o parcelado deve ser o maior elemento de preço da peça. O valor à vista entra como linha secundária. Se o checkout cobra juros no parcelado, use a taxa real do SEU gateway; nunca dividir preço÷12 sem juros se o cliente paga juros de verdade — isso subestima a parcela.
3. **Item em destaque sempre em primeiro lugar.** O carro-chefe da oferta ocupa a primeira posição da lista e, no quadrado, a linha inteira.
4. **Todo item leva seu valor de.** Em produtos high ou mid ticket, cada entrega deve ter um valor defensável riscado. A soma dos itens é a âncora. Se remover ou alterar um item, recalcule a âncora e o percentual do badge. **Exceção low ticket (R$17–R$97):** não exibir valor por item nem linha de valor total; usar apenas a ancoragem geral, como `De R$97 por R$37`, e a lista de entregas sem coluna de preço.
5. **Nenhum item pode quebrar linha ou ser cortado em reticências.** O cliente precisa conseguir ler tudo o que está levando. O template faz o auto-ajuste para preservar os rótulos.
6. **CTA âmbar chapado.** O botão não deve usar glow, sombra ou gradiente.
7. **Tudo que faz parte da oferta deve estar visível.** Se é entregue — suporte, grupo, bônus, acesso ou material — deve ser tratado como item e participar da ancoragem. A linha `incluso` é para observação de escopo, não para esconder entregáveis.
8. **Escopo de acesso explícito.** Acesso vitalício com escopo limitado deve informar exatamente o que está incluído. O mesmo vale para o prazo de suporte: suporte por 30 dias não é suporte vitalício.
9. **Prova social real.** Se a peça levar depoimento, nome, selo, número ou resultado, ele tem que ser REAL do seu negócio — nunca invente citação nem número. Se você não tem depoimento ainda, não inclua o elemento.

## Motor de imagem e QA

O caminho DEFAULT é o HTML→PNG determinístico de `scripts/render.mjs`, mais confiável para preço denso, listas e valores que precisam bater exatamente com o `data.json`.

Como variação opcional, use o gerador generalizado de imagem do repositório:

```bash
python3 skills/gerar-imagem/scripts/gerar.py --prompt '...' --output X.png
```

Esse gerador usa Gemini como padrão do projeto e pode ser usado quando a peça se beneficiar de uma direção visual mais livre. Em qualquer imagem gerada, faça QA visual obrigatório: abra o PNG e confira dígito por dígito o preço, o percentual do badge, a acentuação em português, a posição do parcelado, a ordem dos itens e a ausência de texto inventado. Se o QA reprovar ou a peça tiver uma lista densa que precise ser exata, use o caminho HTML→PNG.

## Anatomia da oferta

| # | Elemento | Campo no `data.json` |
|---|---|---|
| 1 | Wordmark + badge de desconto ou turma | `wordmark`, `badge` |
| 2 | Promessa ou headline curta | `promessa` |
| 3 | Checklist, com o primeiro item em destaque | `items[]` (`label`, `price`, `highlight`) |
| 4 | Inclusos sem preço, em linha corrida | `incluso` |
| 5 | Valor original riscado, com âncora igual à soma | `anchor` |
| 6 | Parcelado dominante | `parcelado` |
| 7 | À vista e prazo de acesso | `avista`, `acesso` |
| 8 | Garantia, acesso e escassez | `garantia`, `acesso`, `escassez` |
| 9 | CTA e rodapé | `cta`, `checkout`, `rodape` |

Campos extras: `slug` define os nomes dos arquivos; `theme` aceita `amber` ou `amber-blue`; `bg` define o fundo.

## Inputs

Se o usuário não trouxer as informações, pergunte antes de gerar:

- Produto, preço à vista e **parcelado real**, conferido no checkout.
- Lista de itens incluídos com o valor de cada item, quando for high ou mid ticket. Se os valores ainda não existirem, sinalize claramente quais foram arbitrados para aprovação.
- Qual é o item em destaque.
- Garantia, prazo e escopo de acesso.
- Escassez com data ou condição real, nunca falsa.
- Qualquer depoimento, nome, número ou resultado que o usuário queira usar, acompanhado da fonte real do negócio.

## Fluxo

1. Crie uma pasta de projeto com um `data.json` no formato de `references/data-exemplo.json`.
2. Gere as imagens:

   ```bash
   node skills/criar-arte-oferta/scripts/render.mjs <dir-do-projeto>
   ```

3. Gere o texto:

   ```bash
   node skills/criar-arte-oferta/scripts/gerar-texto.mjs <dir-do-projeto>
   ```

4. Faça QA visual em cada PNG: preços corretos, zero reticências, zero corte ou quebra indevida, sem buraco preto, parcelado dominante, destaque em primeiro e badge coerente com âncora ÷ preço.
5. Se a arte for virar criativo de anúncio Meta, execute o gate de safe-zone antes de mostrar a peça para aprovação.
6. Entregue as imagens e o Markdown gerados. Não edite o Markdown manualmente; altere o `data.json` e regenere.

## Safe-zone para anúncios Meta

O Meta pode sobrepor elementos nos 14% superiores e nos 25% inferiores de Stories e Reels. Mantenha headline, preço e CTA na área segura.

Para auditar um master quadrado e derivar o story:

```bash
zx-safezone <slug>-oferta-quadrado.png --derivar
```

Suba o master e o derivado quando a derivação for aprovada. Se o helper informar `DERIVAÇÃO NÃO SERVE aqui`, gere o 9:16 nativamente, com o layout pensado para 1080×1920 e os elementos principais entre 14% e 75% da altura. Um Exit 1 significa que a peça não deve ser mostrada nem publicada: regenere e rode o QA novamente. Abra o overlay `<arte>.safezone.png` para identificar violações.

Para vídeo ou animação:

```bash
zx-safezone <arquivo>.mp4 --modo stories
```

## Saídas

Na pasta do projeto, gere:

- `<slug>-oferta-quadrado.png` — 2160×2160, para feed, LP, checkout e WhatsApp.
- `<slug>-oferta-story.png` — 2160×3840, para Stories e status.
- `<slug>-oferta.md` — texto pronto com bloco WhatsApp e bloco de e-mail, além da referência das artes.

## Como o auto-ajuste funciona

O template escala todos os blocos por uma variável CSS `--k` e busca o maior valor que ainda cabe. O algoritmo é bidirecional: cresce quando há espaço e encolhe quando há overflow. Assim, evita tanto o corte quanto o buraco preto no story.

A função `semQuebra()` interrompe apenas o crescimento quando algum rótulo passaria de uma linha. Ela não governa o encolhimento inteiro, porque um rótulo comprido não deve derrubar a escala até o mínimo. O encolhimento possui um piso para tentar desquebrar os rótulos e, se necessário, aceitar duas linhas sem colapsar toda a composição.

O preço é medido no próprio elemento `.parcelado`, que usa `nowrap` e pode transbordar para dentro do padding sem alterar o `scrollWidth` do card. Por isso, não use apenas o `scrollWidth` do card nem testes com uma margem fixa: um filho full-width já ocupa toda a largura e produziria uma medição falsa.

A folga vertical é distribuída com `justify-content: space-between` no `.wrap`. O CTA não usa `margin-top: auto`, pois isso absorveria toda a sobra e impediria a distribuição equilibrada entre os blocos.

No quadrado, o template usa uma coluna automática quando há até 10 itens, favorecendo a leitura integral dos rótulos.

## Dependências

- Playwright para JavaScript.
- Google Chrome instalado, pois o template usa `channel: 'chrome'`.
- Fontes Inter e JetBrains Mono. O render pode precisar de rede para carregá-las.

Instale a dependência na própria pasta da skill:

```bash
npm install playwright
```

## Não fazer

- Não editar os arquivos `.md` gerados à mão.
- Não inventar depoimentos, alunos, números, resultados ou datas de escassez.
- Não publicar uma arte com preço estimado sem avisar que é estimativa.
- Não deixar a âncora divergente da soma dos itens.
- Não esconder entregáveis na linha de observação.

## Gate de qualidade da copy

A checagem é técnica, não editorial. Confirme:

1. O preço aparece junto de uma âncora clara, por exemplo `R$97 (de R$997 — 90% OFF)`.
2. Nenhuma frase anula a própria escassez.
3. Existe uma ponte lógica entre o que o cliente já comprou, o que falta e o que a oferta resolve.
4. O fechamento informa a redução de risco, como garantia e prazo de acesso.
5. O prazo da mensagem é o mesmo prazo usado na página ou no checkout.
6. Todo preço citado é o preço vivo da oferta.
7. Toda prova social usada é real e verificável.
