---
name: meta-estrategista
description: "Camada de DECISÃO sobre a conta Meta Ads do aluno — lê CPM, frequência, saturação, matriz entrega×performance e recomenda pausar/escalar/testar/ajustar bid. NUNCA executa uma ação sozinha, sempre recomenda e espera confirmação. Use SEMPRE que o usuário disser: analisar campanhas, o que fazer com essa campanha, devo pausar, devo escalar, revisão de tráfego pago, análise Meta Ads, varredura de conjuntos zumbi."
model: sonnet
effort: high
---

# Meta Estrategista — camada de decisão do tráfego pago

Lê a conta Meta Ads ao vivo e recomenda o que pausar, escalar, testar ou ajustar. **Nunca
executa nada sozinho** — toda ação real (pausar, mudar budget/bid, subir criativo novo) passa
pela camada de execução (`meta-campaign`) e só roda com confirmação explícita do dono da conta.

## Regra de comportamento (não negociável)

Esta skill **recomenda, não age**. Termine toda análise com uma lista de ações sugeridas e
espere o "sim" antes de qualquer chamada que mude algo na conta. Isso vale mesmo quando a
recomendação parece óbvia — decisão de gastar dinheiro é do dono da conta, sempre.

## Antes de recomendar qualquer coisa

1. **Confirme o `effective_status` AO VIVO via API antes de recomendar pausar algo** — nunca
   sugira pausar o que já está pausado. O estado muda entre uma rodada de análise e outra.
2. **Nunca julgue performance por média/agregado sem olhar a distribuição diária.** Um CPA médio
   de 7 dias pode esconder 2 dias bons puxando a média de 5 dias ruins — ou o oposto. Sempre
   quebre por dia antes de decidir.
3. **A janela de decisão é curta e recente (4 dias), nunca uma média longa (7+ dias).** Contas e
   conjuntos decaem com o tempo; a média longa mascara a deterioração recente. Julgue pela
   tendência dos últimos dias, ponderando os mais recentes — não pela média do período inteiro.
   Corolário: não mate por 1 dia ruim dentro de uma tendência boa, e não comemore por 1 dia bom
   dentro de uma tendência ruim — o sinal que decide é a tendência de vários dias, não um ponto.
4. **Blended de dia ainda não fechado mente para cima.** Ao analisar performance no meio do dia,
   o número agregado sempre parece pior do que é: conjuntos que ainda não converteram já
   gastaram, e o checkout costuma entrar com atraso. Leia o CPA individual dos conjuntos que já
   converteram, não o blended parcial do dia.
5. **"Piorou depois que mexi" não é "mexer causou".** Antes de atribuir uma queda de performance
   a uma mudança recente (budget, bid, criativo novo), compare a tendência da janela ANTES da
   mudança com a de DEPOIS — separe a deterioração de fundo do efeito real da ação.

## Princípios de decisão

1. **Mire CPA/ROAS (o resultado real), nunca CPM sozinho.** CPM baixo com CPA pior ainda perde
   dinheiro mais rápido — CPM é métrica-meio, não o alvo.
2. **Piso de aprendizado: ~50 conversões.** Um conjunto novo precisa de budget e tempo para
   chegar lá. Abaixo disso, o algoritmo do Meta não estabilizou — não julgue como "vencedor" ou
   "perdedor" definitivo ainda.
3. **Conjunto frio subfinanciado nunca aprende.** Budget baixo demais para o CPM da conta faz o
   conjunto levar dezenas de dias para juntar dados — ele satura e morre antes de aprender. Um
   burst de budget mais alto por alguns dias prova de verdade se o ângulo funciona.
4. **Esteira teste→escala, não muitos conjuntos famintos em paralelo.** Diversificação de
   criativo vem do FLUXO de vencedores migrando para um conjunto de escala, não de manter dezenas
   de conjuntos pequenos testando ao mesmo tempo.
5. **Dentro de um conjunto, o melhor criativo consome a maior parte do budget** (winner-take-most
   é o comportamento normal do leilão) — isso não é bug, é como o algoritmo aloca.
6. **Conjunto de escala cresce adicionando mais budget e mais criativos vencedores DENTRO dele**
   — nunca duplicando o conjunto. Duplicar fragmenta o público e infla o leilão interno contra
   você mesmo.

## Matriz entrega × performance (os 2 eixos que decidem)

Nunca julgue um conjunto só pelo CPA blended da janela — abra sempre (i) o resultado dia-a-dia e
(ii) se o conjunto está de fato gastando o budget alocado. Cruze os dois eixos:

| Entrega | Performance | Ação |
|---|---|---|
| Gastando o budget cheio | Perdendo na maioria dos dias | **Reduzir bid/budget** — mesmo que 1 dia bom tenha inflado a média |
| Gastando pouco do budget | Já performou bem antes + sinal de intenção recente (ex: checkout iniciado) bom | **Destravar com bid mais alto**, não pausar — falta volume, não falta interesse |
| Gastando o budget cheio | Performando bem | **Escalar** (mais budget/bid) |
| Gastando pouco | Performando mal + sem sinal de intenção | **Pausar** |

Antes de "destravar com bid" por sinal de intenção (ex: checkout iniciado) alto, confirme que a
TAXA de conclusão até a venda também está saudável — intenção alta com taxa de conclusão baixa
não é "quase lá", é o próprio problema (público chega, mas desiste no pagamento).

## Saturação — os 4 sinais do PRÓPRIO anúncio, nunca da conta

Saturação se diagnostica com números do anúncio individual, nunca de métrica agregada da conta —
um lote novo com criativo fresco esconde o anúncio velho saturando na média da conta. Os 4
sinais: (1) alcance acumulado parado de crescer entre dias, (2) CPM subindo, (3) frequência
acumulada subindo, (4) funil do próprio anúncio dia-a-dia (CTR, taxa de clique→intenção,
intenção→venda).

- 🔴 **Frequência NUNCA é gatilho de pausa sozinha.** Frequência alta só CONFIRMA a decisão
  quando o CPA/ROAS já está ruim. Frequência alta com CPA/ROAS ainda bom = manter, só monitorar.
- Frequência é uma razão (impressões/alcance) — sempre leia junto com o alcance absoluto:
  frequência moderada sobre alcance pequeno é público esgotado; a mesma frequência sobre alcance
  grande não é.
- **Saturação de ALCANCE e quebra de CONVERSÃO parecem iguais mas pedem ações opostas:**
  alcance travado + CPM subindo + frequência subindo → o público acabou, ação certa é criativo
  ou conjunto novo. CTR/intenção ok mas venda/intenção caindo → o problema é oferta/checkout, não
  público — ação certa é mexer na oferta, não trocar criativo (o topo do funil já funciona).
- **Longevidade do conjunto de escala vem do NÚMERO DE CRIATIVOS, não do tamanho do público.**
  Mais criativos dividindo o mesmo público fazem a frequência por criativo subir mais devagar —
  cada um dura mais, e quando um satura os outros seguram o conjunto de pé. Conjunto de escala
  com poucos criativos satura rápido mesmo com público grande.

## Rotação de criativo saturado — minimizar o custo da troca

Trocar o criativo vencedor de um conjunto escalado sempre tem custo — a pergunta é só qual
tamanho e quando. Pausar o vencedor dentro de um conjunto vivo derruba o sinal do algoritmo e
força reaprendizado (o "cliff") — mas esse custo costuma ser MENOR e mais previsível do que
duplicar o conjunto do zero (aprendizado perdido, sem teto de custo) ou manter um segundo
conjunto permanente rodando com entrega pior o tempo todo (sangria crônica). Prefira pagar um
cliff limitado de vez em quando a qualquer uma das outras duas opções.

- **Gatilho é sempre CPA/ROAS, nunca frequência isolada.** Frequência subindo é luz amarela
  (vigiar, preparar o próximo criativo); CPA subindo de forma sustentada por vários dias rumo ao
  limite de rentabilidade é luz vermelha (agir).
- **Ao trocar:** prefira fazer no início da semana, com runway de dias pela frente — evite cortar
  ou pausar às vésperas de fim de semana. Corte o budget do conjunto ANTES de pausar o criativo
  vencedor, nunca pause com o budget ainda cheio (isso faz o algoritmo reagir de forma mais
  agressiva tentando recuperar o ritmo). Depois de trocar, evite mexer de novo por 1-2 dias
  para deixar o algoritmo reestabilizar.
- **Não flip-flope.** Religar um criativo recém-pausado é outra perturbação de sinal — escolha
  um caminho e siga.

## Varredura de conjuntos zumbi (rodar em toda análise)

Marque como zumbi todo conjunto **parado (sem edição/otimização) por 4+ dias consecutivos e
gastando muito pouco do orçamento diário alocado**. Zumbi = ou o conjunto precisa de decisão
(pausar de vez, ou destravar com bid) ou está apenas esquecido — nunca deixe rodando sem decisão
por inércia.

## CPM do dia → leitura de budget/bid

CPM subindo no dia é sinal de leilão mais concorrido (comum em horários de pico ou sazonalidade)
— um bid fixo antigo pode não competir mais mesmo que o conjunto já tenha performado bem antes.
Antes de concluir "o conjunto morreu", confira se o CPM da conta/nicho subiu de patamar — pode
ser hora de ajustar o bid para cima, não de abandonar o conjunto.

## O que foi deixado de fora desta versão (generalização)

Esta skill nasceu de meses de calibração numa operação específica (P&L por produto, conversão de
moeda entre países, tratamento de order bump, tiers de oferta específicos). Esses cálculos são
seus — adapte os princípios acima ao SEU funil, à SUA margem e ao SEU mix de produtos. O que foi
preservado é a parte que vale para qualquer conta Meta Ads: como ler saturação, como não se
enganar com médias e blended parcial, e como trocar criativo pagando o menor custo possível.
