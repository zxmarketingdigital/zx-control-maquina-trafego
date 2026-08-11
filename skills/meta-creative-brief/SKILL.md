---
name: meta-creative-brief
description: "Gera briefing criativo completo para anúncio Meta (Facebook/Instagram) com 3 hooks de copy, 3 hooks visuais, CTA, ângulos psicológicos e specs técnicos por placement (Reels 9:16, Feed 1:1, Stories 9:16). Output em markdown pronto para passar ao designer ou colar em Sora/Midjourney/Leonardo. Use SEMPRE que o aluno disser: briefing criativo meta, ideia de anuncio, criar copy ad, hook de anuncio, brief para designer, copy facebook, copy instagram, criativo para anuncio, brief criativo."
model: sonnet
effort: high
---

# Meta Creative Brief

Gera briefing criativo de alta conversão para anúncios Meta.

## Inputs (perguntar ao aluno)

1. **Nicho do cliente** (ex: imobiliária, dentista estético, agência de marketing)
2. **Dor principal** (o problema agudo do público)
3. **Oferta** (o que está sendo vendido e preço ou condição)
4. **Objetivo da campanha** (lead, WhatsApp, venda, alcance)
5. **Tom de voz** (formal, casual, ousado, técnico)

## Output (markdown)

Preencher todos os campos com base nas respostas do aluno, sempre em português:

```markdown
# Briefing Criativo — {nicho}

## Persona-alvo
{1-2 frases descrevendo quem ele/ela é, idade, contexto, momento de vida}

## Ângulo central
{a virada mental / insight que faz a oferta parecer urgente}

## 3 Hooks de Copy (primeiras 3 linhas do anúncio)

### Hook 1 — Dor explícita
"{frase de impacto que nomeia a dor}"

### Hook 2 — Promessa específica
"{resultado mensurável + prazo}"

### Hook 3 — Curiosidade / quebra de padrão
"{frase que provoca leitura para descobrir o que vem depois}"

## 3 Hooks Visuais

### Visual 1 — Antes/Depois
{descrição da cena, elementos, ritmo, paleta}

### Visual 2 — Demonstração
{descrição}

### Visual 3 — UGC (parecer orgânico)
{descrição}

## Corpo do anúncio (estrutura)
1. Hook (1 linha)
2. Identificação da dor (2 linhas)
3. Apresentação da solução (2 linhas)
4. Prova / autoridade (1 linha)
5. CTA direto

## CTAs sugeridos (escolher 1-3)
- "{CTA 1 — direto}"
- "{CTA 2 — curiosidade}"
- "{CTA 3 — escassez}"

## Specs técnicos por placement

| Placement | Aspect ratio | Resolução mín | Duração (vídeo) | Texto seguro |
|---|---|---|---|---|
| Feed Facebook | 1:1 ou 4:5 | 1080×1080 | até 240s | margem 250px |
| Feed Instagram | 1:1 ou 4:5 | 1080×1080 | até 60s | margem 14% |
| Stories | 9:16 | 1080×1920 | até 60s | safe zone 14% top/bottom |
| Reels | 9:16 | 1080×1920 | até 90s | logos fora dos 14% |

## Paleta sugerida
{3-5 cores em hex baseadas no nicho}

## Tipografia
{1 família para título + 1 para corpo}

## Próximo passo
Cole esse briefing com seu designer ou em uma ferramenta de geração de imagem (Sora, Midjourney, Leonardo). Para vídeo, valide o storyboard antes de gravar.

A tabela de **specs por placement acima é CRITÉRIO DE ACEITE**, não sugestão: ela deve ser entregue a quem renderiza, e o entregável só é aceito com a safe-zone verificada — `safezone <arquivo> --modo stories` (exit 0). Uma peça com informação crítica fora da faixa 14%-75% volta para correção e não sobe.
```

## Regras

- Sempre usar português.
- Não deixar placeholders genéricos no briefing final; preencher com base no nicho, dor e oferta do aluno.
- Hooks devem caber em uma linha cada, com até 90 caracteres.
- CTAs devem ser específicos; evitar "Saiba mais".
- Não inventar prova, autoridade, preço, prazo ou escassez que o aluno não tenha informado.
