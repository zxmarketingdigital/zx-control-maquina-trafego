---
name: criar-anuncio-video-gemini-omni
description: "Cria vídeos verticais de anúncio para Meta com Gemini Omni Flash, motor Veo 3.1, áudio nativo e geração por cena real. Use quando alguém pedir vídeo de anúncio com Gemini Omni, vídeo com Veo, criativo em vídeo Omni, vídeo de anúncio IA do Google ou geração de vídeos em lote."
model: sonnet
effort: medium
---

# Criar anúncio em vídeo — Gemini Omni Flash

Gera criativos verticais 9:16 para anúncios, com cena real e áudio nativo (música e efeitos). O Omni Flash faz clipes de até 10 segundos; para peças mais longas, gere 2 ou 3 clipes e concatene-os.

Para uma peça oficial, aprove o roteiro e o texto das telas antes de gerar. A copy e a oferta devem vir do próprio produto e nicho do usuário; não invente prova social, números ou promessas.

## Formatos e prompts padrão

Adapte cada cena ao SEU produto/nicho. Todos os prompts devem pedir 9:16, espaço livre no topo e na base e nenhum texto escrito na imagem, porque o texto exato entra no pós. Use as cores da sua marca na composição e nos overlays.

### 1. Cartoon-POV — 2 clipes, cerca de 15 s

**Clipe A — dor → mecanismo:**

> Animação cartoon 2D flat, estética de meme brasileiro viral, cores saturadas, contornos pretos grossos, 9:16. Dois momentos: (1) [PERSONA] exausto e frustrado de madrugada no laptop; (2) o mesmo personagem surpreso ao ver [MECANISMO]. Personagem consistente. Música eletrônica animada desde o início e SFX de pop. Espaço livre no topo e na base. Absolutamente nenhum texto, palavra ou letra na tela.

**Clipe B — resultado:**

> Continuação com o mesmo personagem, agora relaxado e feliz no sofá, com clima de vitória e humor visual. Mostrar [RESULTADO]. Música eletrônica e SFX de caixa registradora desde o início. Formato vertical 9:16, personagem consistente, espaço livre no topo e na base. Absolutamente nenhum texto, palavra ou letra na tela.

### 2. Motion de produto — 2 clipes, cerca de 15 s

Não use formas abstratas: mostre o produto, sua interface ou o mecanismo funcionando.

**Clipe 1:**

> Sequência cinematográfica vertical 9:16 de uma tela de computador: terminal de código escuro estilo VS Code ou agente de programação, linhas de código rodando e cursor digitando sozinho, interface de automação processando. Adapte a tela ao produto de [NICHO]. Música eletrônica desde o início e sons de teclado. Espaço livre no topo e na base. Absolutamente nenhum texto ou palavra fora da interface essencial do produto.

**Clipe 2:**

> Continuação vertical 9:16 mostrando o resultado do produto: dashboard de crescimento com gráfico subindo, notificações de conversão e um agente de IA trabalhando no computador, em um escritório moderno. Adapte os elementos ao produto de [NICHO] e ao resultado [RESULTADO]. Música inspiradora e SFX de confirmação desde o início. Sem texto de anúncio sobreposto na cena.

### 3. Cinematográfico b-roll — 3 clipes, cerca de 24 s

Use música nativa de um clipe Omni, não narração. Cada clipe pode ser gerado separadamente e depois concatenado.

**Clipe 1:**

> Plano cinematográfico vertical 9:16: [PERSONA] concentrado digitando no notebook em um home office moderno à noite, tela relacionada ao produto, luz quente e composição premium. Câmera com movimento lento. Espaço livre no topo e na base, sem texto escrito na imagem.

**Clipe 2:**

> Close-up vertical 9:16 das mãos digitando no teclado, tela relacionada ao produto desfocada ao fundo, profundidade de campo e brilho quente. Ritmo premium, sem texto escrito na imagem.

**Clipe 3:**

> Plano vertical 9:16: [PERSONA] recostado e satisfeito com café, notebook mostrando o resultado [RESULTADO] de forma visual, luz quente e clima de sucesso e liberdade. Sem texto escrito na imagem, com espaço livre no topo e na base.

Variação futura: animar uma arte estática que já performou bem pede scripting adicional e não está incluído nesta versão.

## Texto, áudio e montagem

O modelo pode renderizar texto legível em interfaces, mas ainda pode derreter texto pequeno ou denso. Para headline, oferta e CTA exatos em português, gere a cena limpa e adicione o overlay no pós, usando as cores e fontes da sua marca. Preserve aproximadamente 14% livres no topo e 25% livres na base para a interface do Meta.

O áudio nativo é o diferencial do Omni: música e SFX já vêm no clipe. Não passe `generate_audio=True`; no modo Developer API isso dá erro. Para vídeos maiores, concatene clipes com parâmetros compatíveis e confirme que o áudio começa no primeiro frame. Se precisar substituir a trilha, faça o mux no pós e corte no menor fluxo.

## Escolha do caminho

| | Caminho A — Google Flow | Caminho B — API por script |
|---|---|---|
| Custo | Créditos da sua assinatura Gemini Pro/Ultra | Cobrança por uso na `GEMINI_API_KEY` |
| Forte em | Refinar uma cena por conversa | Gerar lotes de variações A/B |
| Quando usar | 1 ou 2 vídeos caprichados | Esteira diária e muitos ângulos |

Ambos usam o mesmo motor Omni Flash. No Flow, faça login com a SUA conta Google que tem o plano Gemini Pro/Ultra. Na API, use a chave do próprio usuário.

## Caminho A — Google Flow

1. Abra o Google Flow em um Chrome real já logado com a sua conta Google.
2. Crie um projeto e, nas configurações de geração, selecione proporção 9:16 e modelo Omni Flash.
3. Envie o roteiro aprovado. Quando o Flow pedir confirmação do custo em créditos, aprove mantendo a confirmação ativada.
4. Abra o clipe gerado e use a opção de baixar no editor.

Para editar por conversa, peça mudanças específicas como “deixe a luz mais quente” ou “remova o texto do canto”. O Omni tenta preservar personagem e cena.

## Caminho B — API por script

Pré-requisito: `google-genai >= 2.10`.

```bash
pip3 install --upgrade 'google-genai>=2.10.0'
```

A chave deve estar em `~/.operacao-ia/config/gemini.env`:

```text
GEMINI_API_KEY=sua_chave
```

Gere um vídeo:

```bash
python3 ~/.claude/skills/criar-anuncio-video-gemini-omni/scripts/gerar_omni.py \
  --prompt "<roteiro>" \
  --out ~/.operacao-ia/scripts/video-omni/ad_aspiracao.mp4
```

Gere um lote, com um prompt por linha:

```bash
python3 ~/.claude/skills/criar-anuncio-video-gemini-omni/scripts/gerar_omni.py \
  --prompts-file ~/.operacao-ia/scripts/video-omni/prompts.txt \
  --outdir ~/.operacao-ia/scripts/video-omni/
```

O script usa `interactions.create(model="gemini-omni-flash-preview", input=PROMPT, response_format={"type":"video","aspect_ratio":"9:16","delivery":"uri"})`, acompanha o processamento com `files.get` e baixa o resultado com `files.download`. Um clipe costuma levar 40–60 segundos e ter 8–10 segundos, 720×1280, com áudio AAC. Pode rodar em background quando estiver gerando um lote.

## Gotchas técnicos

- Não use `client.models.generate_videos` com Omni: o endpoint retorna 404 porque não suporta `predictLongRunning`. Omni usa `interactions.create`.
- `veo-3.1-fast-generate-preview` funciona em `generate_videos`, mas é outro tier e não é um proxy do Omni. Se precisar de Veo puro, escolha conscientemente o modelo apropriado.
- Não passe `generate_audio=True`: o áudio já vem nativo e esse parâmetro dá erro no Developer API.
- A URI do arquivo vem como `.../files/<id>:download?alt=media`; extraia o id com `re.search(r'/files/([^:/?]+)', uri)`, não com `split('/')[-1]`.
- IA generativa pode inserir palavras em inglês ou texto deformado na cena. Exija “absolutamente nenhum texto, palavra ou letra na imagem”, confira o resultado e regenere a base se aparecer texto indevido.
- O Omni gera clipes de até 10 segundos. Vídeos mais longos exigem concatenação de 2 ou 3 clipes e QA do áudio no início.

## QA obrigatório depois de gerar

Passe todo vídeo pelo gate de safe-zone antes de entregar ou subir:

```bash
zx-safezone <arquivo>.mp4 --modo stories
```

`exit 0` aprova; `exit 1` reprova. O helper amostra frames ao longo da timeline, mede densidade nas faixas mortas e gera um PNG de diagnóstico quando reprova. Se houver overlay fora da área segura, remonte-o e rode o gate novamente.

Também confira um frame inicial e um frame final: texto crítico deve aparecer, o áudio não pode estar mudo no início e não pode haver palavra indesejada assada na cena. Legendas e CTA podem ser adicionados no pós, sempre respeitando a safe-zone.

## Matriz de ângulos

Para A/B, use um prompt por linha no `--prompts-file` e varie a abertura mantendo o mesmo payoff: aspiração, resultado primeiro, objeção, prova e curiosidade. Mude de verdade a cena, o ângulo, o ritmo e os elementos de b-roll; preserve apenas a oferta e a copy aprovadas.
