---
name: meta-performance-analyzer
description: "Analisa performance das campanhas Meta usando o decide() personalizado do aluno (limiares scale_at/kill_at do perfil) e retorna ranking de ações: top 3 SCALE, top 3 KILL, top KEEP a monitorar. Lê paid-traffic-{N}d.json e meta_perfil.json. Use SEMPRE que o aluno disser: analisar campanhas meta, performance da semana, qual ad escalar, qual matar, relatorio meta, analise meta, analise trafego pago, performance meta ads."
model: sonnet
effort: high
---

# Meta Performance Analyzer

Diagnóstico semanal de tráfego pago Meta com decisões prontas, sempre baseado nos limiares configurados no perfil do aluno.

## Inputs

1. Perguntar ao aluno qual janela analisar (default: 7d). Se disser "essa semana", usar 7d; se disser "mês", usar 30d; e assim por diante.
2. Ler:
   - `~/.operacao-ia/dashboards/paid-traffic-{N}d.json`
   - `~/.operacao-ia/config/meta_perfil.json`

Se o JSON não existir, orientar a rodar `meta-metrics-fetcher` primeiro. Se a janela pedida não estiver disponível, informar as janelas existentes e não substituir silenciosamente por outra.

## Análise

1. Para cada ad no JSON, ler `decide` e `decide_reason`, já calculados pelo fetcher.
2. Agrupar por decisão: SCALE / KILL / KEEP.
3. Ordenar cada grupo por `spend` desc, dando prioridade aos maiores gastos.
4. Comparar o KPI primário com `target` por ad e calcular o percentual de delta.
5. Identificar padrões por campanha, adset, placement, público, formato e criativo quando esses campos existirem: por exemplo, públicos semelhantes com melhor CPL ou Reels com CTR superior ao Feed.
6. Verificar a amostra: se `spend < target × 1.2` para um ad, marcar como "amostra insuficiente" e não classificá-lo como SCALE ou KILL, mesmo que o valor observado pareça bom ou ruim.
7. Se `decide_enabled: false` no perfil, fazer somente análise descritiva, sem recomendar SCALE, KILL, pausa ou aumento de budget.
8. Para `cpa` e `roas`, lembrar que a qualidade do diagnóstico depende do evento do pixel. Se houver checkout com PIX ou boleto, recomendar cruzamento com vendas pagas antes de tomar decisão financeira.

## Output (markdown)

```markdown
# 📊 Análise Meta ADS — janela {N}d

**Conta:** {ad_account_id}
**Período:** {since} → {until}
**Spend total:** {spend_total}
**KPI primário:** {primary_kpi} (meta {target})

## Status global do KPI primário
{primary_kpi}: {value} vs meta {target} — {🟢 / 🟡 / 🔴} ({delta_pct}%)

---

## 🟢 TOP 3 SCALE (escalar agora)

| Ad | Spend | {KPI} | vs meta | Razão |
|---|---:|---:|---:|---|
| {ad_name 1} ({id_curto}) | {spend} | {kpi} | {delta} | {reason} |
| ... | ... | ... | ... | ... |

## 🔴 TOP 3 KILL (pausar)

| Ad | Spend | {KPI} | vs meta | Razão |
|---|---:|---:|---:|---|
| {ad_name 1} ({id_curto}) | {spend} | {kpi} | {delta} | {reason} |
| ... | ... | ... | ... | ... |

## 🟡 KEEP (manter monitorando)

{lista resumida de 5-10 ads, incluindo amostra insuficiente quando aplicável}

---

## Padrões observados

- {insight 1, com números}
- {insight 2, com números}
- {insight 3, com números}

---

## Próximas ações sugeridas

1. {ação baseada nos dados, com número}
2. {ação baseada nos dados, com número}
3. {padrão a testar em novos criativos ou conjuntos}
```

Quando `decide_enabled: false`, trocar os blocos de veredito por "Melhores desempenhos", "Piores desempenhos" e "Itens para monitorar", deixando claro que são observações e não decisões automáticas.

## Regras

- Nunca recomendar ação sem mostrar o número que a sustenta.
- Não classificar ad com amostra insuficiente como SCALE ou KILL.
- Incluir sempre o nome real do ad e seu ID curto, formado pelos últimos 8 dígitos quando o ID estiver disponível.
- Não inventar spend, KPI, target, conversões, padrões ou economia estimada.
- Ao sugerir pausa ou aumento, indicar que a execução da alteração depende de confirmação do aluno e das permissões disponíveis.
- Considerar `better=lower` ou `better=higher` conforme a definição do KPI no perfil, não presumir que todo KPI deve ser menor.
