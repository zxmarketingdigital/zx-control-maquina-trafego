---
name: meta-metrics-fetcher
description: "Coleta métricas das campanhas Meta ADS via MCP oficial e atualiza o JSON do dashboard local. Lê o perfil do aluno (~/.operacao-ia/config/meta_perfil.json) para puxar APENAS os KPIs configurados (CPL, CPA, ROAS, custo/msg, CPM, CTR, etc.) — nada genérico, nada hardcoded. Use SEMPRE que o aluno disser: atualizar metricas meta, sync metricas, baixar metricas meta, atualizar dashboard meta, refresh meta, refresh dashboard, fetch meta, atualizar trafego pago."
model: sonnet
effort: high
---

# Meta Metrics Fetcher

Coleta métricas Meta ADS adaptadas ao perfil do aluno e atualiza o JSON do dashboard.

## Pré-requisitos

- `~/.operacao-ia/config/meta_perfil.json` existe.
- MCP `mcp__meta-official__*` está autenticado.

## Fluxo

1. Ler `meta_perfil.json` e extrair `kpis`, `windows`, `ad_account_id` e `objectives`.
2. Para cada janela em `windows` (ex: 4, 7, 14, 30 dias):
   - Calcular `time_range = {since: hoje-N, until: hoje}`.
   - Determinar os campos `fields` necessários usando o mapeamento abaixo.
   - Chamar `mcp__meta-official__ads_insights_*` com `level=ad`, `time_range`, `fields` e `filtering=[{field:'effective_status',operator:'IN',value:['ACTIVE','PAUSED']}]`.
   - Se `objectives` inclui `LEAD_GENERATION`, também chamar `ads_get_ad_entities` para enriquecer os dados com leads.
3. Calcular cada KPI por ad usando o mapeamento abaixo.
4. Aplicar `decide()` por ad, lendo `scale_at` e `kill_at` de cada KPI no perfil.
5. Agregar os dados em ad → adset → campaign → conta.
6. Calcular `kpis_summary` no topo: média ponderada por spend, comparação versus target e status verde/amarelo/vermelho.
7. Gravar `~/.operacao-ia/dashboards/paid-traffic-{N}d.json` para cada janela.
8. Reportar ao aluno: linhas processadas, status por KPI e próxima execução automática, se houver agendamento configurado.

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

- MCP não autenticado → orientar: "rode `python3 setup/setup_meta_oauth.py` para reconectar".
- `meta_perfil.json` não existe → informar: "rode Etapa 2 do Setup primeiro".
- Conta sem dados na janela → gravar JSON com `campaigns:[]` e mensagem "sem campanhas ativas na janela".
- KPI, target ou limiar ausente no perfil → não inventar configuração; registrar o campo ausente e continuar apenas com os KPIs válidos.
