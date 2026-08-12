# SPEC — Setup 15: Máquina de Tráfego com Claude Code

> ZX Control 5.0 Traffic · turma Agosto/2026 · call de lançamento 12/Ago/26
> Repo público que o aluno clona: `zxmarketingdigital/zx-control-maquina-trafego`

---

## 1. O contrato com o aluno

A LP de venda (`zxcontrol-5-launch`) já vendeu, literalmente:

> "o setup novo **Máquina de Tráfego com Claude Code**: criativos com IA (imagem e vídeo),
> tráfego pago avançado, tráfego orgânico/blog SEO e tracking"

Os 6 passos anunciados na seção "O que muda na 5.0 TRAFFIC" são o escopo obrigatório:

| # | Passo (copy da LP) | Selo |
|---|---|---|
| 01 | 🎨 Criativos com IA — imagem (variações de ângulo, texto nítido, sem designer) | Skill de imagem |
| 02 | 🎬 Criativos com IA — vídeo (narração e legenda, pronto pra subir) | Skill de vídeo |
| 03 | 🎯 Tráfego pago avançado (estrutura de campanha, matriz de ângulos, CBO, escala, leitura de métrica) | Meta + Google Ads |
| 04 | 🌱 Tráfego orgânico + Blog SEO (**agente que produz conteúdo** e blog que rankeia) | SEO / orgânico |
| 05 | 📊 Tracking & mensuração (pixel/CAPI, tracking de canal, atribuição) | Dados que decidem |
| 06 | ⚙️ A Máquina rodando no automático (criativo → tráfego → captura → venda) | Aquisição contínua |

**Cronograma vendido:** call ao vivo na 2ª quinzena · semanas 3 e 4 = suporte de instalação · acesso vitalício.

**Decisão de escopo (Rafael, 11/Ago):** as 8 etapas entram já no lançamento, mesmo que cruas.

### Fora do escopo desta versão

**ChatGPT Ads.** A API existe (`api.ads.openai.com/v1`, CRUD de campanhas/ad groups/ads/reporting,
bidding por impressão/clique/conversão) e o Brasil entrou na lista de países disponíveis em
10/Ago/26. Mas a chave só é emitida **após aprovação manual** de conta (verificação Persona +
fila de review, sem SLA e sem possibilidade de expedite). Decisão do Rafael: **não anunciar na
call**; ele abre a conta agora, e quando aprovar e ele validar rodando de verdade, entra como
bônus para a turma. Não criar promessa antes disso.

---

## 2. Princípio de projeto: custo de entrada zero

O aluno não pode bater em paywall no meio da instalação. A esteira que o Rafael usa hoje
depende de HiggsField (plano pago de 600 créditos/mês), da voz clonada dele no ElevenLabs e das
contas de anúncio da ZX LAB — nada disso é portável.

| Necessidade | Caminho padrão do aluno | Custo | Upgrade opcional |
|---|---|---|---|
| Imagem de anúncio | `gerar-imagem` com provider **Gemini** | R$ 0 (free tier) | HiggsField gpt_image_2 |
| Vídeo de anúncio | `criar-anuncio-video-html` / `-momentum` (HTML/Remotion → Chrome → ffmpeg, local) | R$ 0 | — |
| Vídeo com cena real | `criar-anuncio-video-gemini-omni` (API, chave própria) | free tier | HiggsField Kling/Seedance |
| QA de criativo | `zx-safezone` (Python + PIL, offline) | R$ 0 | — |
| Briefing de copy | `meta-creative-brief` | R$ 0 | — |
| Conteúdo do blog | agente com chave Gemini ou Claude do aluno | free tier / centavos | — |

**Regra:** toda etapa deve concluir com sucesso usando apenas contas gratuitas. Qualquer
dependência paga é degradação graciosa — o script avisa, marca no checkpoint e segue.

---

## 3. Arquitetura do repositório

Herda o molde maduro do Setup 6 (`zx-control-trafego-pago`), que já resolveu os problemas
difíceis: autoload do roteiro, idempotência, checkpoint, auditoria com auto-fix, desinstalador.

```
zx-control-maquina-trafego/
├── CLAUDE.md                    # roteiro guiado — o "produto". Boas-vindas + 8 etapas
├── README.md                    # pré-requisitos + comando de clone
├── SPEC.md                      # este documento (interno)
├── .claude/launch.json          # {"load": ["./CLAUDE.md"]}
├── .env.template
├── setup/                       # 1 script Python idempotente por etapa
│   ├── setup_base_s15.py        # Etapa 0 — diagnóstico, cria ~/.operacao-ia/
│   ├── setup_chaves.py          # Etapa 1 — Gemini (obrigatória) + opcionais
│   ├── setup_criativos_imagem.py# Etapa 2
│   ├── setup_criativos_video.py # Etapa 3
│   ├── setup_pago_meta.py       # Etapa 4a — reusa Setup 6 se presente
│   ├── setup_pago_google.py     # Etapa 4b
│   ├── setup_tracking.py        # Etapa 5
│   ├── setup_blog.py            # Etapa 6 — nicho/tema + fila + deploy + agendamento
│   ├── setup_maquina.py         # Etapa 7 — orquestrador
│   ├── setup_audit.py           # Etapa 8 — checks com auto-fix + fecha phase_completed
│   └── setup_uninstall.py
├── skills/                      # copiadas para ~/.claude/skills/ (com backup se customizada)
├── scripts/                     # operação do dia a dia do aluno
├── blog/                        # motor do blog (portado)
│   ├── generator/               # build.js · template.js · validate.js
│   ├── agente/                  # NOVO — cérebro de conteúdo
│   └── content/articles/
├── docs/                        # glossário + templates de dashboard
└── launchagents/                # plists com placeholders {HOME}/{PYTHON}
```

### Convenções herdadas (não reinventar)

- **Estado do aluno** vive em `~/.operacao-ia/` (`config/`, `scripts/`, `dashboards/`, `logs/`),
  nunca dentro do repo clonado.
- **Checkpoint** por etapa em `~/.operacao-ia/config/setup15_progress.json`; `phase_completed`
  global em `config.json` usa `max(atual, 15)` — nunca retrocede.
- **Skills** são copiadas (não symlink), com `filecmp.dircmp` antes: idêntico → pula;
  customizado pelo aluno → backup em `.s15-backup-{slug}-{ts}/` antes de sobrescrever.
- **Segredos** só em `~/.operacao-ia/config/*.env` com `chmod 600`. Nunca imprimir token
  completo — sempre `token[:8] + "…" + token[-4:]`.
- **LaunchAgents** com placeholders, detecção de conflito antes de instalar, `unload` antes de
  `load`.
- Toda etapa é **pulável** ("pular" → marca no checkpoint e avança) e **idempotente**.

### Regras de comportamento do roteiro (CLAUDE.md)

Copiar o padrão do Setup 6: bloco de boas-vindas em blockquote instruindo o Claude a **não
executar nada** até o aluno digitar `INICIAR SETUP 15`; 8 regras invioláveis (execute você
mesmo, uma etapa por vez, erros são seus, explique antes de instalar, progress bar
`[███░░░░░░░] Etapa N de 8`, nunca mostrar token completo); cada etapa com as subseções fixas
*O que é · Para que serve · Como você vai usar no dia a dia · Instalação*.

---

## 4. As 8 etapas

### Etapa 0 — Base e diagnóstico
Verifica Python ≥3.9 (bloqueia), Node + Chrome + ffmpeg (necessários para vídeo local; avisa),
`gh` CLI (avisa). Cria a árvore `~/.operacao-ia/`. Imprime o plano das 8 etapas.
**Não exige Setup anterior** — o Setup 15 é autossuficiente; se detectar `phase_completed >= 6`
apenas reaproveita o que já existe.

### Etapa 1 — Chaves e contas
Guia a criação da `GEMINI_API_KEY` (aistudio.google.com/apikey, ~2 min, grátis) — **única
obrigatória**. Opcionais com degradação graciosa: HiggsField, conta Meta Ads, Google Ads,
Cloudflare (para o blog). Grava em `~/.operacao-ia/config/maquina.env` (chmod 600) e valida
cada chave com uma chamada real antes de marcar como OK.

### Etapa 2 — Criativos com IA: imagem
Instala `gerar-imagem` (cascata de providers, Gemini como degrau padrão), `zx-safezone`,
`criar-thumbnail`, `meta-creative-brief`, e uma versão **genérica** de `criar-arte-oferta` cujo
`data.json` o aluno preenche com a própria oferta (o catálogo de produtos e a prova social da
ZX LAB saem).
Porta `formatos.json` como **dados** (é o banco de layouts visuais; não contém nada da ZX LAB).
Teste de aceitação: gerar 1 arte da oferta do aluno em 1:1 e 9:16 e passar no `zx-safezone`.

### Etapa 3 — Criativos com IA: vídeo
Instala `criar-anuncio-video-html` (padrão, custo zero), `criar-anuncio-video-momentum`
(Remotion) e `gerar-video-mp4`. `criar-anuncio-video-gemini-omni` entra como caminho de cena
real via API com chave do aluno.
Teste de aceitação: renderizar 1 MP4 9:16 localmente e aprovar no `zx-safezone --modo stories`.

### Etapa 4 — Tráfego pago avançado
**4a — Meta.** Se o Setup 6 já estiver instalado, reaproveita token e perfil. Senão instala o
núcleo: OAuth do MCP oficial (com fallback de System User Token), `meta-metrics-fetcher` e
`meta-performance-analyzer` (ambos já são "aluno-shaped": leem `meta_perfil.json` com contas,
KPIs, `scale_at`/`kill_at` por aluno).
**4b — Google Ads.** Conecta a conta e instala o núcleo de campanha equivalente.
Herdar o aviso do Setup 6: `cpa`/`roas` vêm do **pixel**, que pode contar PIX gerado e não pago
— cruzar sempre com venda paga real antes de cortar budget.

### Etapa 5 — Tracking e mensuração
Instala `zx-tracking.js` na LP do aluno, cria o schema de canal
(`channel, traffic_source, utm_*, gclid, referrer_host`) e o classificador em cascata
**sck > gclid > utm > referrer**. Instala o `preflight_guardian.py` generalizado — o gate que
**bloqueia a subida de campanha sem rastreamento**. CAPI de refund entra parametrizado por
`PIXEL_ID` do aluno.
Fica de fora: `zx_creative_roas_dashboard.py` (3 contas da ZX LAB hardcoded + conectores
Hotmart/Greenn próprios) — reescrito do zero em versão enxuta sobre as fontes do aluno.

### Etapa 6 — Tráfego orgânico + Blog SEO ⭐ construção real

O motor existente é portado quase inteiro: `build.js`, `template.js` (mesmo design system âmbar
do blog ZX LAB), `validate.js` com os 24 checks, o pipeline `daily_publish.js`
(fila → gate de conteúdo → safety-check de 16 frases banidas → build → validate → publish, com
reprovado indo para `drafts/`), deploy `wrangler pages deploy` e o padrão de killswitch.

**O que não existe e precisa ser construído — `blog/agente/`:**

O blog da ZX LAB roda com `generator.provider = "manual"`; os artigos são escritos à mão. A LP
promete "agente que produz conteúdo". O agente novo faz:

1. **Nicho e tema pelo aluno.** Na instalação ele responde nicho, público, tom e produto que
   quer vender. Isso vira `blog/config.json` (mesma forma do config da ZX LAB: `site`,
   `products`, `generator`, `analytics` com beacon config-driven e token vazio no commit).
2. **Fila de keywords hub-and-spoke.** A partir do nicho, gera `queue.json` no schema existente
   (`id, keyword, slug, produto, tier: pillar|cluster, volume_mes, cpc_top_brl, intencao,
   spoke_of, status`), com pillars e clusters ligados.
3. **Artigo no schema canônico** `content/articles/<slug>.json`:
   `slug, keyword, title, description, produto, proofPoint, sections[{h2, points[]}], faq[{q,a}]`.
   Provider = Gemini (free tier) por padrão, Claude opcional; chave lida do ambiente, **nunca
   embutida**.
4. **Publicação diária agendada.** LaunchAgent no padrão do `com.zxlab.blog-daily` (08h00) →
   pega a próxima keyword `pending`, gera o artigo se faltar, roda os 24 checks, publica só com
   24/24 e deploya. Killswitch por arquivo.

**Requisito explícito do Rafael:** mesmo processo e mesmo design do blog da ZX LAB. O que muda
é apenas o conteúdo do `config.json` (nicho, produtos, domínio do aluno).

*Efeito colateral desejado:* este agente resolve também o blog da ZX LAB, que hoje é manual.

### Etapa 7 — A Máquina no automático

A Máquina tem duas camadas que já existem e se chamam entre si — é isso que fecha o ciclo
"criativo → tráfego → captura → venda":

**Camada de DECISÃO — `meta-estrategista-zxlab`.** Lê a conta ao vivo (CPM trend, campeões vs
famintos, lances, frequência) e decide o que pausar, escalar e testar; inclui a varredura diária
de conjuntos zumbi (parados ≥4 dias gastando quase nada). Ela **sempre recomenda, nunca executa
sem OK** — comportamento que se preserva no setup do aluno. Quando a decisão é "testar", ela
aciona a camada de execução.

**Camada de EXECUÇÃO — `meta-campaign-zxlab`.** `rotina_artes_diaria.py` gera os criativos,
`build_campaign.py` monta campanha/conjunto/anúncios via Graph API com SCK por anúncio,
`preflight_guardian.py` barra o que estiver sem rastreamento, `add_image_ad.py` acrescenta arte a
conjunto no ar, `build_video_campaign.py` faz a variante em vídeo.

Do estrategista, generalizar significa manter as regras **universais** de operação (conferir
`effective_status` ao vivo antes de recomendar pausar algo que já está pausado; nunca ler
performance por média sem olhar a distribuição por dia; cruzar pixel com venda paga real antes de
cortar budget) e tirar as regras que são **calibração da ZX LAB** (produtos e ofertas específicos,
SCK líquido do funil próprio, janelas e order bumps das plataformas do Rafael).

Generalizar significa: contas e produtos vêm do perfil do aluno (hoje são 3 contas e 2 produtos da
ZX LAB hardcoded); o banco de copies e os 5 públicos de lista viram templates vazios; a origem dos
vídeos deixa de ser o grupo WhatsApp do Rafael e passa a ser uma pasta local.

Preservar, porque é o que dá qualidade: o QA de safe-zone obrigatório **antes** da galeria de
aprovação, a galeria em dois momentos (gate antes / confirmação depois), subir sempre os dois
tamanhos (4:5 + 9:16) e o ledger que vincula arte → `ad_id`.

### Etapa 8 — Auditoria e fechamento
`setup_audit.py` no padrão do Setup 6: checks por etapa com **auto-fix** antes de reportar
(chaves válidas, skills instaladas, blog buildando, LaunchAgents carregados, tracking
respondendo, dashboards gerados). Marca `phase_completed = 15` e imprime o resumo do que ficou
no ar.

---

## 5. O que sai da esteira do Rafael

Cortado (branding ou infra intransferível): `gerar-arte-zxcontrol`, `expandir-formatos-arte`
(vira metodologia em `docs/`, sem scripts), `swipe-criativos` (depende do grupo WhatsApp +
Evolution), o bloco de vendas orgânicas do `blog_metrics.py` (bate no Supabase CRM da ZX LAB) e
`roas-funil-completo`.

Reescrito com a fonte trocada: `criar-arte-animada-anuncio` e `montar-criativo-screencast` — o
motor de animação/legenda é portável, mas "achar a arte campeã nas contas do Rafael" e "subir
campanha automático" saem; a fonte passa a ser uma pasta local do aluno.

Da esteira de vídeo do HiggsField sai a voz clonada do Rafael (`iCHZPlI7FznXTV6z9sry`) — o aluno
usa preset genérico ou clona a própria.

---

## 6. Critérios de aceitação

O setup está pronto quando, numa máquina limpa com **apenas uma chave Gemini gratuita**:

1. As 8 etapas completam sem erro, cada uma idempotente (rodar 2× não duplica nada).
2. O aluno termina com: 1 arte aprovada no safe-zone, 1 MP4 renderizado, o blog publicado no
   domínio dele com pelo menos 1 artigo gerado pelo agente passando em 24/24 checks, o
   LaunchAgent diário carregado, e o tracking respondendo.
3. `setup_audit.py` sai com 0 falhas.
4. Nenhum token aparece completo em log ou mensagem.
5. `setup_uninstall.py` reverte sem deixar resíduo.
6. Nenhum caminho absoluto de `/Users/rcastrodigital`, nenhuma conta/ID da ZX LAB e nenhum
   segredo no repo — ele é **público**.

---

## 7. Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Escopo grande para uma noite | A LP vende call amanhã + 2 semanas de instalação; etapas cruas amadurecem na janela vendida |
| Aluno sem Node/Chrome/ffmpeg trava no vídeo | Etapa 0 detecta e instrui; etapa de vídeo é pulável |
| Agente de conteúdo gerar artigo raso e reprovar nos 24 checks | Reprovado vai para `drafts/`, nunca publica; o gate existente já protege |
| Repo público vazar segredo | `zx-repo-nascer` varre o histórico por valor antes de criar; `.env` gitignored |
| Google Ads menos maduro que Meta no arsenal | Entregar o núcleo de conexão + leitura; escala fica no Meta |
