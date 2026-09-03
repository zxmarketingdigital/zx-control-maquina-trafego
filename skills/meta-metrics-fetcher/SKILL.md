---
name: meta-metrics-fetcher
description: "Coleta métricas das campanhas Meta ADS via Graph API direta e atualiza o JSON do dashboard local. Lê o perfil do aluno (~/.operacao-ia/config/meta_perfil.json) para puxar APENAS os KPIs configurados (CPL, CPA, ROAS, custo/msg, CPM, CTR, etc.) — nada genérico, nada hardcoded. Use SEMPRE que o aluno disser: atualizar metricas meta, sync metricas, baixar metricas meta, atualizar dashboard meta, refresh meta, refresh dashboard, fetch meta, atualizar trafego pago."
model: sonnet
effort: high
---

# Meta Metrics Fetcher

Coleta métricas Meta ADS adaptadas ao perfil do aluno e atualiza o JSON do dashboard.

## Pré-requisitos

- `~/.operacao-ia/config/meta_perfil.json` existe.
- `~/.operacao-ia/config/meta.env` tem `META_ACCESS_TOKEN` — um token de usuário do
  sistema (System User) do Business Manager, com estas permissões:
  `ads_read`, `ads_management`, `business_management`, `read_insights`,
  `leads_retrieval` (só é usado se `objectives` incluir `LEAD_GENERATION`),
  `pages_read_engagement` (necessário para o KPI `cost_per_msg`, ligado à Page
  do anúncio).

> Não existe conector MCP oficial da Meta disponível hoje — o registro de
> conectores não retorna nada para Meta Ads/Marketing API. Este skill fala
> direto com a Graph API (`https://graph.facebook.com/v21.0`), que é estável,
> documentada e não depende de nenhum MCP de terceiros.

## Fluxo

1. Ler `meta_perfil.json` e extrair `kpis`, `windows`, `ad_account_id` e `objectives`.
2. Ler `META_ACCESS_TOKEN` de `~/.operacao-ia/config/meta.env` (nunca imprimir o valor
   completo — mascarar como `primeiros caracteres…últimos 4`).
3. Para cada janela em `windows` (ex: 4, 7, 14, 30 dias):
   - Calcular `time_range = {since: hoje-N, until: hoje}`.
   - Determinar os campos `fields` necessários usando o mapeamento abaixo.
   - Chamar `GET /{ad_account_id}/insights` com `level=ad`, `time_range`, `fields`
     — **sem** o parâmetro `filtering`. `effective_status` não é um campo de filtro
     válido no endpoint de insights (a API responde `(#100) Filtering field
     effective_status is invalid`); ele só existe em `/ads` e `/adsets`.
   - Para saber o status ao vivo de cada ad (necessário antes de recomendar pausar
     algo, já que o `meta-estrategista` exige isso), chamar separadamente
     `GET /{ad_account_id}/ads?fields=id,name,effective_status` e cruzar pelo `id`.
   - Se `objectives` inclui `LEAD_GENERATION`, também chamar
     `GET /{ad_id}/leads` (ou o endpoint de leadgen forms equivalente) para
     enriquecer os dados com leads.
4. Calcular cada KPI por ad usando o mapeamento abaixo.
5. Aplicar `decide()` por ad, lendo `scale_at` e `kill_at` de cada KPI no perfil.
6. Agregar os dados em ad → adset → campaign → conta.
7. Calcular `kpis_summary` no topo: média ponderada por spend, comparação versus target e status verde/amarelo/vermelho.
8. Gravar `~/.operacao-ia/dashboards/paid-traffic-{N}d.json` para cada janela.
9. Reportar ao aluno: linhas processadas, status por KPI e próxima execução automática, se houver agendamento configurado.

## Mapeamento KPI → fields da API + cálculo

> 🔴 **`cpa` e `roas` dependem do PIXEL — e o pixel pode não estar contando venda paga.**
> Se o checkout usa PIX ou boleto, o evento de conversão pode disparar na geração do pagamento, e não na confirmação do pagamento. Isso subestima o `cpa` e superestima o `roas` quando há pagamentos iniciados e não concluídos; também pode fazer uma campanha boa parecer pior quando o evento está configurado de forma inconsistente.
> Antes de aplicar corte ou realocação de budget com base nesses KPIs, cruzar os eventos com a fonte de vendas efetivamente pagas disponível no ambiente do aluno e verificar a configuração do evento e a janela de atribuição. Essa validação é necessária para qualquer conta que use um checkout com PIX ou boleto configurado dessa forma.

| KPI key | Campos pedidos | Cálculo |
|---|---|---|
| `cpl` | `spend`, `actions{type:lead}` | `spend / leads` |
| `cpa` | `spend`, `actions{type:purchase}` | `spend / purchases` ⚠️ depende do evento do pixel |
| `roas` | `spend`, `action_values{type:purchase}` | `purchase_value / spend` ⚠️ depende do evento do pixel |
| `cost_per_msg` | `spend`, `actions{type:onsite_conversion.messaging_conversation_started_7d}` | `spend / msgs` |
| `cpm` | `cpm` | direto |
| `ctr` | `ctr` | direto |
| `cpc` | `cpc` | direto |
| `frequency` | `frequency` | direto |
| `cost_per_install` | `spend`, `actions{type:mobile_app_install}` | `spend / installs` |

Tratar divisão por zero como `null` e registrar a ausência de conversões sem inventar valor.

## decide() por ad

Dado o KPI primário do perfil:

- **better=lower**: SCALE se `value ≤ target × scale_at` **e** `spend ≥ target × 1.2`; KILL se `value > target × kill_at` **ou** (`spend > target × 3` e zero conversões); senão KEEP.
- **better=higher**: SCALE se `value ≥ target × (2 - scale_at)`; KILL se `value < target × (2 - kill_at)`; senão KEEP.

Incluir `decide_reason` legível, por exemplo: "CPL 28% abaixo da meta + amostra suficiente". Se não houver valor ou amostra suficiente, não forçar SCALE/KILL: usar KEEP com motivo explícito.

## Schema de saída

Ver `PLAN.md`, seção "Schema paid-traffic-{N}d.json", e respeitar exatamente o schema existente. Preservar identificadores e nomes retornados pela API, sem substituir por valores hardcoded.

## Output ao aluno

Usar um resumo equivalente a:

```
✅ Métricas atualizadas

Janelas: 4d, 7d, 14d, 30d
Conta: {ad_account_id}
Ads processados: {count}

Status geral (janela 7d):
  {KPI_1}: {valor}  (meta {target})   {status} {delta}
  {KPI_2}: {valor}  (meta {target})   {status} {delta}
  {KPI_3}: {valor}  (meta {target})   {status} {delta}

Próxima atualização automática: {data/hora ou não configurada}

Abra o dashboard: {URL local configurada}
```

Sempre avisar quando `cpa` ou `roas` estiverem sujeitos à validação de pagamento confirmado.

## Erros

- `META_ACCESS_TOKEN` ausente ou a Graph API recusar o token (HTTP 401/190) → orientar:
  "gere um novo token de usuário do sistema no Business Manager (Configurações do
  Negócio → Usuários → Usuários do sistema) com as permissões `ads_read`,
  `ads_management`, `business_management`, `read_insights`, `leads_retrieval` e
  `pages_read_engagement`, e rode `python3 setup/setup_pago_meta_google.py` de
  novo para reconectar".
- `meta_perfil.json` não existe → informar: "rode a Etapa 4 do Setup primeiro".
- Conta sem dados na janela → gravar JSON com `campaigns:[]` e mensagem "sem campanhas ativas na janela".
- KPI, target ou limiar ausente no perfil → não inventar configuração; registrar o campo ausente e continuar apenas com os KPIs válidos.
