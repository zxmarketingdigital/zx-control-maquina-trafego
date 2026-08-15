---
name: google-campaign
model: sonnet
effort: high
description: Planeja e valida campanhas Google Ads Search para o aluno, acionada por gatilhos como 'subir campanha google', 'criar campanha search', 'anunciar no google' e 'montar campanha google ads'. Monta o plano para execução via MCP Pipedream; nunca publica diretamente nem ativa campanhas.
---

# Google Campaign

## Papel desta skill

Esta skill é a camada operacional de Google Ads Search. Ela valida o produto, a copy, o orçamento e a conta do aluno; gera um plano completo dos sete passos; e registra os IDs retornados pelo MCP Pipedream no ledger. O script Python é planejador, validador e ledger: ele não faz HTTP e não chama ferramentas MCP.

A execução real acontece na conversa, usando as tools `google_ads-*` do MCP Pipedream, sempre depois de o aluno revisar o plano e responder sim.

## Contrato do que preservar

1. **Conta do aluno sempre.** O customer ID vem de `--conta` ou de `GOOGLE_ADS_CUSTOMER_ID` em `~/.operacao-ia/config/google_ads.env`. Nunca usar conta padrão, conta interna ou ID hardcoded. O ID pode vir com hífens, mas precisa resultar em exatamente dez dígitos. Se não houver ID, parar e orientar o aluno a conectar a conta na Etapa 4.
2. **A campanha nasce PAUSED.** Campanha, grupo de anúncios e anúncio devem ter `status: PAUSED`. O aluno revisa e ativa manualmente no painel do Google Ads.
3. **Geo e idioma são obrigatórios e FIXOS.** O passo de critérios sempre inclui Brasil `geoTargetConstants/2076` e Português `languageConstants/1014`. Eles **não são sobrescrevíveis pelo perfil**: um `google_perfil.json` que traga outro valor faz o planejador parar com erro, em vez de aceitar em silêncio. Sem geo e idioma a campanha roda no mundo inteiro; com o geo errado ela roda no país errado — nos dois casos quem paga é o aluno.
4. **Keywords são PHRASE e sequenciais.** Cada keyword recebe seu próprio passo `google_ads-create-or-update-keywords`, com match type `PHRASE` e `sequencial: true`. Não mandar um lote de keywords: a operação real pode retornar `CONCURRENT_MODIFICATION`.
5. **O ledger liga campanha, grupo e anúncio.** O `campaign_key` é derivado por SHA256 de produto, keywords, budget canonizado em micros e **customer id** — o mesmo produto em duas contas do aluno é operação diferente. Cada planejamento também recebe um `attempt_id` aleatório, que identifica **aquela tentativa** e não a chave. O plano é registrado como `planned`; depois da execução via MCP, `--registrar` só aceita IDs numéricos positivos. Com campanha, grupo e anúncio registrados, a entrada vira `created`; faltando algum, vira `partial` com a pendência escrita. Um passo que falhou não deve ser registrado.
6. **REGRA DE OURO DA COPY: nenhuma promessa de ganho.** São proibidos em títulos e descrições os radicais `ganhe`, `ganha`, `ganhar`, `ganho`, `ganhos`, além de `fature`, `faturamento`, `faturar`, `lucro`, `lucrar`, `lucre`, `renda`, `4 dígitos`, `5 dígitos`, `6 dígitos`, `7 dígitos`, `retorno garantido`, `receba por`, `dinheiro no bolso` e qualquer valor monetário que não seja o preço do produto. A validação usa palavras inteiras, portanto `aprenda` não é confundido com `renda`. **Mesmo o preço correto reprova quando vem com cadência** (`por dia`, `ao mês`, `por venda`…): `Ganhe R$37 por dia` é promessa de renda, não preço. São permitidos características e habilidades reais, como `curso prático`, `domine automação`, `crie agentes de IA`, `trabalhe com IA`, `sem código`, `sem N8N`, `white label`, `15 min` e `Claude Code`, além do preço do próprio produto. Já houve reprovação real por promessa de ganho; o gate é fail-closed de propósito — não contornar com variações ou pontuação.

## Fluxo obrigatório

1. Conferir o produto em `~/.operacao-ia/config/produtos/<slug>.json`. O JSON precisa conter `nome`, `preco`, `link_checkout`, `google_titulos`, `google_descricoes` e `google_keywords`. A skill não inventa títulos, descrições ou keywords.
2. Rodar o planejador em modo seguro, sem MCP e sem tocar no ledger:

   ```bash
   python3 skills/google-campaign/scripts/build_campaign_google.py \
     --produto <slug> --budget <reais> --dry-run
   ```

   Quando necessário, informar `--conta <customer-id>` e `--cpc-bid <reais>`. O lance padrão é 20% do budget diário.
3. Ler o JSON completo, confirmar que a conta é a do aluno, e mostrar o plano antes de qualquer mutação. O `--dry-run` deve funcionar mesmo quando o MCP estiver indisponível.
4. Com o OK explícito do aluno, executar os sete passos via MCP Pipedream, na ordem apresentada pelo plano. Cada `instruction` termina com `EXECUTE NOW (perform the mutate).`.
5. Conferir os retornos. Se houver IDs, registrar o resultado:

   ```bash
   python3 skills/google-campaign/scripts/build_campaign_google.py \
     --registrar --campaign-key <K> --campaign-id <ID> \
     [--ad-group-id <ID>] [--ad-id <ID>] [--attempt-id <A>]
   ```

   O `--attempt-id` é **obrigatório** quando a chave já foi replanejada com `--forcar`: sem ele não há como saber se os IDs vieram da tentativa viva ou de um retorno atrasado do MCP referente à tentativa substituída. Use o `attempt_id` impresso no plano que você acabou de executar.

6. Informar os IDs e lembrar que a campanha, o grupo e o anúncio continuam pausados.
7. O aluno revisa e ativa manualmente no painel do Google Ads.

## Flags do planejador

- `--produto <slug>`: obrigatório; identifica o JSON em `produtos`.
- `--budget <reais>`: obrigatório; orçamento diário em reais.
- `--conta <customer-id>`: customer ID da conta do aluno; aceita hífens.
- `--login-conta <customer-id>`: login customer ID da MCC, quando a conta do aluno está sob uma. Vem de `GOOGLE_ADS_LOGIN_CUSTOMER_ID` quando não é informado. Ele **autentica**; quem opera continua sendo a conta de `--conta`. Sem ele, uma conta sob MCC pode falhar com `CUSTOMER_NOT_FOUND` ou erro de permissão.
- `--cpc-bid <reais>`: lance CPC em reais; padrão de 20% do budget diário.
- `--dry-run`: gera e imprime o plano inteiro em JSON legível, sem MCP e sem escrever no ledger.
- `--forcar`: replaneja uma chave já existente. Ele **substitui** a tentativa anterior em vez de anexar uma segunda entrada — duas entradas com a mesma chave deixariam o `--registrar` sem saber onde gravar os IDs. O que existia antes fica preservado no campo `substituiu`.
- `--registrar --campaign-key K --campaign-id ID`: fecha o ciclo do ledger após a execução; aceita também `--ad-group-id ID` e `--ad-id ID`. Todos os IDs precisam ser numéricos positivos. A entrada só vira `created` com os três IDs presentes; com apenas parte deles fica `partial` e guarda a pendência. Registrar um `campaign-id` diferente do que já estava gravado **limpa** o grupo e o anúncio anteriores: eles pertencem à campanha antiga, e misturá-los montaria um registro que parece completo sem ser.

Sem `--dry-run`, o planejador imprime o plano e grava uma entrada `status: planned`. Uma chave já existente interrompe a operação com código 1 quando `--forcar` não foi informado. O ledger tem no máximo uma entrada por `campaign_key`, e toda leitura-modificação-escrita é serializada por lock de arquivo — escrita atômica sozinha evita arquivo pela metade, mas não evita perder uma entrada quando dois planejamentos rodam ao mesmo tempo.

## Os sete passos do plano

1. `google_ads-create-or-update-campaign-budget`: cria ou atualiza o budget com `amount_micros` convertido de reais por `1_000_000`, `delivery_method: STANDARD` e `explicitly_shared: false`.
2. `google_ads-create-or-update-campaign`: cria a campanha Search com `advertising_channel_type: SEARCH`, `status: PAUSED`, `manual_cpc: {}` e apenas Google Search: `target_google_search: true`, `target_search_network: false`, `target_content_network: false` e `target_partner_search_network: false`. Também declara `contains_eu_political_advertising: DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING`.
3. `google_ads-create-or-remove-campaign-criteria`: adiciona obrigatoriamente Brasil `geoTargetConstants/2076` e Português `languageConstants/1014`. Esse passo não é opcional: sem geo e idioma a campanha pode rodar mundialmente. Os `0` de `campaign_id` nos passos encadeados são **placeholders** e cada passo traz a nota dizendo qual ID substituir; executar com `0` é erro, não atalho.
4. `google_ads-create-or-update-ad-group`: cria o grupo com `type: SEARCH_STANDARD`, `status: PAUSED` e `cpc_bid_micros`.
5. `google_ads-create-or-update-keywords`: cria uma keyword por passo, com match `PHRASE` e `sequencial: true`. Lotes podem disparar `CONCURRENT_MODIFICATION`; se isso ocorrer, conferir a listagem e repetir somente o item necessário.
6. `google_ads-create-responsive-search-ad`: cria o RSA com `status: PAUSED`, `final_urls` contendo a URL rastreada, títulos e descrições validados. O `ad_group_id` precisa ser numérico, não resource name. Não usar `path1` nem `path2`.
7. `google_ads-create-or-remove-campaign-criteria`: adiciona negativas com `negative: true` e match `BROAD`, usando as negativas padrão e as `google_negativas_extra` opcionais do produto.

A URL final preserva a query existente e recebe parâmetros no formato:

```text
<link_checkout>?sck=google-<slug>&utm_source=google&utm_medium=cpc&utm_campaign=<slug>-<run_stamp>&utm_content=<slug>-<run_stamp>-ad<N>
```

Se o link já possuir query string, os parâmetros são mesclados sem apagar os existentes.

## Gate de copy e validações

Todos os títulos e descrições passam pelo gate antes da emissão do plano. A quantidade deve estar entre 3 e 15 títulos, com no máximo 30 caracteres cada, e entre 2 e 4 descrições, com no máximo 90 caracteres cada. Deve existir ao menos uma keyword não vazia. O checkout precisa usar HTTP ou HTTPS.

Cadência acompanhada de **qualquer número** reprova mesmo sem símbolo de moeda: `Receba 100 por dia` e `Receba 100/dia` são promessa de ganho igual a `Ganhe R$100 por dia`, e exigir a moeda deixaria a forma mais comum passar. O efeito colateral é conhecido e aceito: `15 min por dia` também reprova. Reescrever um título custa um minuto; um anúncio reprovado custa a conta do aluno.

O preço pode aparecer como valor monetário somente quando for igual ao campo `preco` do produto **e em reais**. Por exemplo, `R$37` e `37 reais` passam com `preco: 37`; `R$500`, `US$37`, `€37` e `$37` reprovam — moeda estrangeira nunca é o preço do produto. O preço correto **também reprova** quando acompanhado de cadência — `Ganhe R$37 por dia`, `R$37/mês` e `R$37 mensalmente` descrevem renda recorrente, não preço. A mensagem de falha lista cada texto e o termo detectado e cita a política de ganhos não confiáveis do Google.

O customer id é aceito apenas como dez dígitos (`1234567890`) ou no formato `123-456-7890`. Um valor como `1234567890x` é recusado em vez de limpo, porque limpar caracteres esconderia um erro de digitação e mandaria a operação para outra conta.

## Gotchas do Pipedream

- Retornos vazios são intermitentes: conferir via `list` e reexecutar somente depois da conferência. Nunca duplicar sem checar.
- RSA não edita in-place: para alterar, remover o anterior e criar um novo.
- Listagens podem não filtrar por campanha e podem não trazer `policy_summary`; o motivo de reprovação aparece no painel do Google Ads.
- Keywords devem ser enviadas uma a uma para evitar `CONCURRENT_MODIFICATION`.
- O anúncio recebe `ad_group_id` numérico, não um resource name.

## O que esta versão NÃO inclui

- Não pesquisa keywords automaticamente nem inventa keywords ausentes no produto.
- Não faz HTTP para a API do Google Ads e não executa tools MCP a partir do Python.
- Não ativa campanhas, grupos ou anúncios automaticamente.
- Não otimiza lances de forma automática.
- Não promete resultado, venda, retorno ou qualquer ganho.
- Não substitui a revisão do aluno no painel nem a conferência da política e da página de destino.
