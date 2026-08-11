---
name: meta-campaign
description: "Camada de EXECUÇÃO do tráfego pago Meta — monta campanha/conjunto/anúncio via Graph API com rastreamento por anúncio, barra a subida de campanha sem tracking configurado, e acrescenta arte nova a um conjunto no ar. Use SEMPRE que o usuário disser: subir campanha, criar conjunto de anúncios, subir criativo novo, publicar anúncio Meta, montar campanha de teste."
model: sonnet
effort: high
---

# Meta Campaign — camada de execução do tráfego pago

Monta campanha, conjunto de anúncios e anúncio na conta Meta Ads do aluno via Graph API, a
partir dos criativos gerados pelas skills de imagem/vídeo deste repositório. É a camada de
EXECUÇÃO — quem decide QUANDO usar esta skill é o `meta-estrategista` (ou o próprio aluno).

## Contrato — o que preservar sempre (é o que garante qualidade)

1. **QA de safe-zone é obrigatório ANTES de qualquer arte entrar na galeria de aprovação.**
   Rode `python3 ../zx-safezone/scripts/zx-safezone.py <arte> --derivar` (imagem) ou
   `--modo stories` (vídeo) e só prossiga com `exit 0`.
2. **Galeria em dois momentos.** Primeiro um "gate" mostrando os criativos que passaram no QA
   ANTES de gastar tempo montando a campanha (o aluno escolhe o que vai pra frente); depois uma
   confirmação final mostrando exatamente o que vai ser publicado (campanha, conjunto, budget,
   segmentação) antes do `POST` real na Graph API.
3. **Suba sempre os dois formatos** — 4:5 (Feed) e 9:16 (Stories/Reels) — nunca um só. O Meta
   corta um formato pro outro e perde informação quando você sobe só um.
4. **Mantenha um "ledger"** (arquivo local, ex. `~/.operacao-ia/logs/ads-ledger.json`) vinculando
   cada arte publicada ao `ad_id` que ela virou — sem isso é impossível saber depois qual arte é
   qual anúncio quando for hora de pausar, trocar ou reportar performance.
5. **Toda campanha nasce em `PAUSED`.** Nunca ativa sozinha — o aluno revisa no Ads Manager e
   ativa manualmente.
6. **Nunca suba campanha sem rastreamento configurado.** O gate de tracking (`preflight_guardian`)
   roda antes de qualquer subida e barra se o pixel/CAPI não estiver recebendo evento.

## Scripts incluídos

- `scripts/build_campaign.py` — cria campanha + conjunto + anúncio(s) via Graph API, lendo a
  configuração do PRODUTO do aluno (não um catálogo fixo) e aplicando um parâmetro de
  rastreamento (`sck`/UTM) único por anúncio. Sempre cria em `PAUSED`.
- `scripts/preflight_guardian.py` — checagem read-only: pixel do aluno está recebendo evento
  recente? Link de destino responde (HTTP 200)? Barra a subida com mensagem clara se não.

## O que esta versão NÃO inclui (generalização deliberada)

A skill original da ZX LAB tem ~65 arquivos e uma matriz de 40 layouts de criativo, um sistema de
rotação automática de artes em conjuntos vivos, e integração direta com o dashboard de métricas
da operação. Isso é o resultado de meses de iteração numa conta específica — não generaliza em
uma sessão. Esta versão cobre o **núcleo que fecha o ciclo**: gerar criativo (outras skills) →
QA de safe-zone → montar e subir campanha rastreada → registrar no ledger. Rotação automática de
criativo saturado, matriz de formatos e otimização de budget ficam como próxima iteração — até
lá, o `meta-estrategista` recomenda e você aplica manualmente pelo Ads Manager ou repetindo
`build_campaign.py` com o criativo novo.

## Fluxo

1. Gerar criativo(s) com `gerar-imagem` ou uma das skills de vídeo.
2. QA de safe-zone (`zx-safezone`) — só segue quem passar.
3. Gate 1 (galeria de aprovação) — aluno escolhe quais criativos avançam.
4. `python3 scripts/preflight_guardian.py --pixel <ID>` — confirma tracking vivo.
5. Gate 2 (confirmação final) — mostra campanha/conjunto/budget antes do POST real.
6. `python3 scripts/build_campaign.py --produto <slug> --criativo <caminho> --budget <valor>` —
   cria em `PAUSED`, grava no ledger, imprime os IDs.
7. Aluno revisa e ativa manualmente no Ads Manager.
