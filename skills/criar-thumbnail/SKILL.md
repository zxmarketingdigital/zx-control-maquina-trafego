---
name: criar-thumbnail
description: "Gera 3 variantes de thumbnail YouTube (1280x720) via skill `gerar-imagem` (gpt-image-2 preferido, Gemini Nano Banana / Imagen 4 como fallback). Variantes: A (rosto+texto), B (conceitual), C (comparação/antes-depois). Lê DESIGN.md para manter identidade visual. Use SEMPRE que o aluno disser: criar thumbnail, gerar thumb, thumb yt, thumbnail youtube, capa do video, capa youtube, thumbnail, miniatura youtube."
model: sonnet
effort: low
---

# Criar Thumbnail YouTube

Gera 3 thumbnails YouTube (1280×720) em estilos diferentes para o aluno escolher ou testar A/B. Usa `gerar-imagem` como gateway único, escolhendo automaticamente o melhor provider disponível.

## Carregamento de contexto

- `~/.operacao-ia/config/marca.json`
- `~/.operacao-ia/data/social-media/DESIGN.md`

## Inputs obrigatórios

1. **Título do vídeo** — ex: "Eu testei uma nova rotina por 30 dias — esse foi o resultado"
2. **Tipo de vídeo** — `tutorial`, `vlog`, `analise`, `entrevista`, `comparacao`. Default: `tutorial`
3. **Texto curto para thumb** — 3-5 palavras no máximo (default: extrair do título). Ex: "30 DIAS DE TESTE"
4. **Output dir** — `~/.operacao-ia/data/social-media/output/thumbs/YYYY-MM-DD_<slug>/`

## Fluxo

### 1. Definir as 3 variantes

| Variante | Conceito | Prompt-base |
|---|---|---|
| A | Rosto expressivo + texto grande | "close-up portrait, surprised/intrigued expression, bold text overlay '<texto>'" |
| B | Conceitual/metáfora visual | "metaphorical visual representing '<tema>', no faces, strong visual hook" |
| C | Comparação/contraste | "split composition: before vs after / problem vs solution, visual contrast" |

Use a seção "Para geração de imagem" do DESIGN.md como base estética. Se DESIGN.md tem apenas seção "Para Higgsfield", reusar — o prompt é genérico o suficiente.

### 2. Geração via skill `gerar-imagem`

Para cada variante, chame o helper diretamente, pois ele escolhe automaticamente o melhor provider disponível:

```bash
python3 ~/.claude/skills/gerar-imagem/scripts/gerar.py \
  --prompt "<prompt completo da variante>" \
  --output "<output_dir>/thumb-<A|B|C>-<conceito>.png" \
  --size 1280x720 \
  --quality high \
  --json
```

Formato do prompt completo (substituir `<...>`):

```
{base_estetica_do_DESIGN.md}, YouTube thumbnail 1280x720,
{conceito_da_variante}, text "<texto>" rendered bold and readable,
high contrast, attention-grabbing, no embedded watermarks
```

O helper imprime JSON com `provider` usado e `elapsed_s`. Registrar isso no resumo para o aluno saber qual provider entregou cada imagem.

**Se gerar-imagem falhar em todos os providers** (sem Codex logado, sem `GEMINI_API_KEY` e sem fallback disponível), orientar o aluno:

1. Opção rápida — criar uma chave Gemini em `https://aistudio.google.com/apikey` e exportar `GEMINI_API_KEY=...` em `~/.operacao-ia/config/gemini.env`.
2. Opção robusta — fazer login no Codex CLI com `codex login`, usando uma assinatura compatível.

### 2.5. Ranquear variantes com VidiQ (opcional)

As ferramentas VidiQ são MCP **deferred**: carregá-las via `ToolSearch` com a query `vidiq` (max_results 15) ou `select:<nome>` ANTES de chamar; nunca chamar diretamente. Cada chamada paga pode consumir créditos; consultar `vidiq_balance` antes de lotes.

O VidiQ entra de duas formas, dependendo de já existir um vídeo no YouTube:

**A) Há `videoId` (vídeo já subido, inclusive unlisted ou privado) — ranquear e entregar a campeã:**

1. Carregar o schema: `ToolSearch` query `select:vidiq_score_thumbnail,vidiq_balance`.
2. Consultar `vidiq_balance` para confirmar créditos.
3. Para cada variante (A, B, C), chamar `vidiq_score_thumbnail` com:
   - `videoId` = ID do vídeo no YouTube;
   - `title` = título do vídeo;
   - `image` = **URL pública** da variante. Subir a PNG em um host acessível e passar a URL, pois a ferramenta não aceita arquivo local.
4. Ordenar pelo score retornado e marcar a campeã no README/resumo. A recomendação de A/B deve seguir o ranking VidiQ, em vez de uma ordem fixa.

**B) Não há `videoId` ainda — o vídeo não foi subido:**

`vidiq_score_thumbnail` exige `videoId` e não pontua uma thumb solta. Usar o VidiQ somente como apoio criativo:

- `vidiq_generate_thumbnail` — gerar referências/conceitos para inspirar as variantes, sem substituir `gerar-imagem`;
- `vidiq_refine_thumbnail` — refinar a direção de uma variante já gerada.

Deixar o scoring para quando existir um `videoId`. Orientar honestamente que o ranqueamento real só acontece quando o vídeo estiver no YouTube, mesmo que unlisted.

Se o VidiQ estiver indisponível ou sem créditos, seguir o fluxo normal de geração e A/B manual sem bloquear a entrega.

### 3. Output

Salvar:

```
output/thumbs/<YYYY-MM-DD>_<slug>/thumb-A-rosto.png
output/thumbs/<YYYY-MM-DD>_<slug>/thumb-B-conceitual.png
output/thumbs/<YYYY-MM-DD>_<slug>/thumb-C-comparacao.png
output/thumbs/<YYYY-MM-DD>_<slug>/README.txt   # explicação das variantes, recomendação A/B e provider usado em cada
```

Se algum PNG vier em tamanho diferente de 1280×720, fazer resize com Pillow e validar:

```python
from PIL import Image
img = Image.open('raw.png')
img.thumbnail((1280, 720), Image.LANCZOS)
canvas = Image.new('RGB', (1280, 720), (0, 0, 0))
x = (1280 - img.width) // 2
y = (720 - img.height) // 2
canvas.paste(img, (x, y))
canvas.save('thumb-A.png', 'PNG', optimize=True)
```

### 4. Atualizar galeria

Ler `~/.operacao-ia/data/social-media/gallery.json`, fazer append em `data["items"]` e escrever de volta. Item:

```json
{ "type": "thumbnail", "title": "<título do vídeo>", "path": "output/thumbs/<dir>/", "providers": ["image2", "gemini"], "created_at": "<ISO>" }
```

### 5. Resumo

- Mostrar os 3 paths e o provider que gerou cada uma.
- Explicar brevemente cada estilo.
- **Se ranqueou via VidiQ:** mostrar o score de cada variante e recomendar a campeã pelo ranking.
- **Se não ranqueou:** sugerir A/B manual e oferecer o ranqueamento quando houver vídeo no YouTube: começar com A (rosto), trocar por B se o CTR ficar abaixo de 3% em 24h e ranquear as três quando o vídeo estiver subido, mesmo unlisted.
- Lembrar que o tamanho final deve ser ≤2MB para subir no YouTube; se ultrapassar, comprimir com `pngquant` ou salvar novamente com Pillow e `optimize=True`.

## Não fazer

- Não chamar Higgsfield diretamente — usar sempre `gerar-imagem`.
- Não usar Puppeteer ou HTML para compor — a thumbnail deve ser geração nativa de imagem.
- Não gerar thumbnail com o rosto real de uma pessoa sem permissão explícita.
- Não usar textos longos na thumb, acima de 5-6 palavras.
