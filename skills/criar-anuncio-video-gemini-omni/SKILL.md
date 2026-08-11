---
name: criar-anuncio-video-gemini-omni
description: Cria vídeo de anúncio para Meta Ads com o Gemini Omni Flash, motor Veo 3.1, em 9:16 e com áudio nativo. Oferece o Google Flow no navegador ou a API por script para geração em lote.
model: sonnet
effort: medium
---

# Criar anúncio em vídeo com Gemini Omni Flash

Gera criativos verticais para anúncios com o Gemini Omni Flash, incluindo cena real ou animada, música e efeitos sonoros nativos. O fluxo serve para qualquer produto ou nicho: adapte a cena, a persona, a oferta e a linguagem visual ao briefing do próprio produto.

## Regras do pipeline

1. Prefira vídeos com pelo menos 15 segundos. O Omni gera clipes de até 10 segundos; emende dois ou três clipes com parâmetros compatíveis para chegar à duração necessária.
2. Deixe a cena sem texto crítico. Headline, oferta e CTA exatos devem entrar como overlay no pós, com a tipografia e as cores da sua marca, respeitando a safe-zone.
3. Em Motion design, mostre imagens do produto funcionando: terminal, código, dashboard, notificações, fluxo de trabalho ou o equivalente visual do seu nicho. Não substitua o produto por formas abstratas.
4. No prompt, peça explicitamente que não haja texto, palavras ou letras na imagem quando a cena não precisar de texto. O modelo pode inserir palavras em inglês mesmo quando isso não foi solicitado.
5. Varie de verdade as novas versões: troque a abertura, o ângulo, o ambiente, o ritmo e os elementos de b-roll. Preserve somente a copy ou a oferta que estiver sendo testada.
6. Faça QA antes de entregar: safe-zone, texto do overlay aparecendo e áudio audível desde o início.

## Prompts padrão de roteiro

Todos os prompts abaixo são verticais 9:16. Substitua `[PERSONA]`, `[MECANISMO]` e `[RESULTADO]` pelas informações do produto e adapte a cena ao seu produto ou nicho. Quando indicado, o texto entra depois no overlay, não na geração.

### Formato 1 — Cartoon-POV

Gere dois clipes e faça concatenação para aproximadamente 15 segundos.

**Clipe A — dor para mecanismo**

> Animação cartoon 2D flat, estética de meme brasileiro viral, cores saturadas, contornos pretos grossos, formato 9:16. Mostrar dois momentos: primeiro, [PERSONA] exausto e frustrado de madrugada diante do laptop; depois, o mesmo personagem surpreso ao ver [MECANISMO, por exemplo um robô de IA fechando uma venda no WhatsApp ou um gráfico de resultado subindo]. Manter o personagem consistente. Música eletrônica animada desde o início e efeitos sonoros de pop. Deixar espaço livre no topo e na base para o overlay. Não mostrar texto, palavras ou letras na tela.

**Clipe B — resultado**

> Animação cartoon 2D flat, estética de meme brasileiro viral, cores saturadas, contornos pretos grossos, formato 9:16. O mesmo personagem está relaxado e feliz no sofá, com óculos escuros em estilo meme, enquanto [RESULTADO, por exemplo notificações de vendas aparecendo]. Clima de vitória e alívio. Música eletrônica desde o início e efeito sonoro de caixa registradora. Deixar espaço livre no topo e na base. Não mostrar texto, palavras ou letras na tela.

### Formato 2 — Motion produto

Gere dois clipes e faça concatenação para aproximadamente 15 segundos. Mostrar o produto ou o mecanismo real, sem formas abstratas.

**Clipe 1**

> Sequência cinematográfica vertical 9:16 mostrando a tela de um computador: terminal de código escuro, semelhante a um editor de desenvolvimento, com linhas de código rodando e cursor digitando sozinho; uma interface de agente de IA processa tarefas. Usar a paleta e os sinais visuais da marca do produto, com acabamento premium. Música eletrônica desde o início e sons de teclado. Não mostrar títulos, palavras ou letras adicionados pelo gerador fora das interfaces que façam parte da ação; deixar espaço para o overlay.

**Clipe 2**

> Sequência cinematográfica vertical 9:16 mostrando um dashboard de resultados com gráfico subindo, notificações de venda aparecendo e um agente de IA trabalhando em um computador. Adaptar os dados, a interface e o ambiente ao produto e ao nicho. Escritório moderno, aparência premium e a paleta da marca. Música inspiradora desde o início e efeito sonoro de caixa registradora. Não inserir texto promocional na cena; deixar espaço para o overlay.

### Formato 3 — Cinematográfico b-roll

Gere três clipes e faça concatenação para aproximadamente 24 segundos. O áudio deve ser música nativa de outro clipe Omni, em loop quando necessário, e não narração. Adicione o texto por cima no pós.

**Clipe 1**

> Plano cinematográfico vertical 9:16: [PERSONA] concentrado digitando no notebook em um home office moderno à noite, com uma tela de trabalho relacionada ao produto, iluminação quente e aparência premium. Câmera com movimento suave. Não mostrar texto promocional na imagem e deixar áreas limpas para o overlay.

**Clipe 2**

> Close-up vertical 9:16 das mãos digitando no teclado, tela de trabalho desfocada ao fundo, profundidade de campo e luz quente. Ritmo envolvente, realista e premium. Não mostrar palavras ou letras promocionais na cena.

**Clipe 3**

> Plano vertical 9:16: [PERSONA] recostado e satisfeito com uma bebida ao lado, notebook exibindo um dashboard de crescimento relacionado ao produto, iluminação quente e clima de sucesso, liberdade e resultado. Câmera com movimento suave. Não inserir texto promocional na imagem.

## Texto e overlay

Para copy oficial exata em português, renderize o texto no pós em vez de confiar no modelo generativo. Use as cores da sua marca e uma composição legível: faixa escura arredondada, barra de destaque, fonte pesada branca com sombra e fade-in. O CTA pode ser uma pílula colorida com redução automática do tamanho da fonte para caber no canvas.

Posicione headline, descrição e CTA dentro da área segura. Como referência para um canvas 720×1280, mantenha conteúdo importante longe de aproximadamente 14% do topo e 25% da base. Se a resolução ou a proporção mudar, recalcule as posições em vez de reutilizar coordenadas em pixels.

A geração pode renderizar texto nítido em interfaces, mas ainda costuma derreter texto pequeno e denso. Toda informação crítica deve ser conferida no QA e, preferencialmente, ser adicionada como overlay determinístico.

## Escolher o caminho

| | Caminho A — Google Flow no navegador | Caminho B — API por script |
|---|---|---|
| Custo | Créditos da sua própria assinatura Gemini, aproximadamente 12 por geração | Cobrança por uso na sua `GEMINI_API_KEY` |
| Forte em | Ajustar a cena por conversa, como mudar a luz ou um objeto | Gerar muitas variações e ângulos em lote |
| Quando usar | Um ou dois vídeos refinados manualmente | Esteira diária e testes A/B |

Ambos usam o mesmo motor Omni Flash. O padrão para lote é o Caminho B; para uma peça única que precisa de refinamento conversacional, use o Caminho A.

## Caminho A — Google Flow no navegador

1. Use o Chrome real já conectado à sua conta Google, não um navegador interno sem sessão. Confirme a conexão do navegador antes de começar.
2. Abra `https://labs.google/fx/tools/flow`, escolha a criação com Google Flow e faça login com a **SUA conta Google que tem o plano Gemini Pro/Ultra**.
3. Crie um projeto. Nas configurações do agente, escolha proporção 9:16 e modelo Omni Flash; salve.
4. Envie o roteiro. Quando o agente pedir confirmação sobre o custo em créditos, aprove somente depois de conferir o prompt e mantenha a confirmação manual ativada.
5. Abra o clipe gerado e use a opção de baixar no editor.

O campo de edição por conversa permite pedir alterações como deixar a luz mais quente, mudar o enquadramento ou remover um objeto. A ferramenta tenta manter a identidade da cena entre as edições.

## Caminho B — API por script

Pré-requisito: `google-genai >= 2.10`, pois a API `client.interactions` não existe em versões antigas. Instale ou atualize o SDK com:

```bash
pip3 install --upgrade 'google-genai>=2.10.0'
```

A chave deve estar em `~/.operacao-ia/config/gemini.env` como `GEMINI_API_KEY`. A API cobra por uso.

```bash
# Um vídeo: o default de saída fica em ~/.operacao-ia/scripts/video-omni/
python3 skills/criar-anuncio-video-gemini-omni/scripts/gerar_omni.py \
  --prompt '<roteiro>' \
  --out ~/.operacao-ia/scripts/video-omni/ad_aspiracao.mp4

# Lote: um prompt por linha no arquivo
python3 skills/criar-anuncio-video-gemini-omni/scripts/gerar_omni.py \
  --prompts-file ~/.operacao-ia/scripts/video-omni/prompts.txt \
  --outdir ~/.operacao-ia/scripts/video-omni/
```

O gerador chama `interactions.create` com `model=gemini-omni-flash-preview`, resposta de vídeo, proporção 9:16 e entrega por URI. Depois consulta o arquivo até o estado `ACTIVE` e faz o download. Um clipe costuma levar de 40 a 60 segundos e ter de 8 a 10 segundos, em 720×1280, com áudio AAC.

Para lotes, rode o comando em background e só consolide os resultados quando todos os arquivos MP4 chegarem. Para vídeos mais longos, concatene clipes antes de aplicar o overlay final.

## Gotchas técnicos da API

- Não use `client.models.generate_videos` com o Omni. Esse endpoint é destinado ao Veo e retorna 404 quando usado com o Omni; o Omni usa `interactions.create`.
- `veo-3.1-fast-generate-preview` pode funcionar com `generate_videos`, mas é um tier diferente e mais fraco. Não o use como substituto do Omni quando a qualidade for importante.
- Não passe `generate_audio=True`: no modo Developer API isso gera erro, pois o recurso só é suportado no ambiente Enterprise Agent Platform. O áudio do Omni já vem nativo.
- A URI do arquivo pode ter o formato `.../files/<id>:download?alt=media`. Extraia o identificador com `re.search(r'/files/([^:/?]+)', uri)`; não use apenas o último trecho separado por barra.
- O Omni produz clipes de no máximo 10 segundos. Para anúncios de 15 a 30 segundos, gere cenas complementares e concatene-as com parâmetros compatíveis.
- Música e efeitos nativos começam no clipe gerado. Verifique o início do áudio e use loop ou concatenação quando a montagem precisar de mais duração.

## Roteiro e matriz de variações

Um roteiro cinematográfico genérico que costuma funcionar:

> Vídeo vertical 9:16 de anúncio cinematográfico. Jovem empreendedor brasileiro numa mesa de home office minimalista à noite, trabalhando no notebook com o mecanismo do produto em execução. Ele se recosta relaxado com uma xícara de café e um leve sorriso. Iluminação quente, acabamento premium e câmera com push-in lento. Clima de liberdade, resultado e negócio funcionando no automático. Não inserir texto promocional na cena; reservar espaço para headline e CTA no overlay.

Para A/B, crie um prompt por linha no arquivo de lote e varie a abertura mantendo o payoff: aspiração, resultado primeiro, objeção, prova e curiosidade. Não copie apenas o mesmo fundo com uma mudança superficial.

## Depois de gerar

1. Rode o gate de safe-zone:

   ```bash
   zx-safezone <arquivo>.mp4 --modo stories
   ```

   Exit 0 significa aprovado e exit 1 indica violação. O helper amostra frames ao longo da timeline, mede a densidade nas faixas mortas do topo e da base e gera `<arquivo>.safezone.png` quando reprova. Abra a imagem para localizar o problema.

2. Se houver violação, remonte o overlay e rode o gate novamente. Confira também se o headline e o CTA aparecem nos frames iniciais e se o áudio não está mudo no começo.
3. Se necessário, faça a legendagem e o CTA no pós com uma composição determinística, sempre usando as cores e a tipografia da sua marca.
4. Concatene os clipes antes do overlay quando o anúncio precisar de mais de 10 segundos. Um exemplo de concatenação e troca de áudio é:

   ```bash
   ffmpeg -f concat -safe 0 -i concat.txt -c copy video_concat.mp4
   ffmpeg -i video_concat.mp4 -i trilha_omni.m4a -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest saida.mp4
   ```

   Use a trilha nativa do Omni em loop quando a montagem exigir uma duração maior; substitua o áudio somente quando isso fizer parte do teste aprovado.

5. Faça a revisão final do anúncio antes de publicar: safe-zone, legibilidade, correspondência entre cena e copy, continuidade entre clipes, duração e áudio.

Variação futura: animar uma arte estática que já performou bem — pede scripting adicional, não incluído nesta versão.
