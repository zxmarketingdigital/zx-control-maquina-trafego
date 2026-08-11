---
name: gerar-imagem
description: 'Gera imagens PNG usando Gemini Nano Banana e Imagen 4 via Google GenAI SDK, com Codex image_gen como upgrade opcional. Use sempre que o usuario disser: gerar imagem, criar thumbnail, gerar thumb, criar imagem, gerar foto, criar arte, gerar criativo, fazer thumbnail, image2, gpt-image, nano banana. Outras skills devem invocar este helper em vez de chamar um gerador diretamente.'
model: sonnet
effort: medium
---

# /gerar-imagem — Gerador de Imagens

Helper unico para geracao de imagem. Cobre dois casos:

1. **Chamada interativa** pelo usuario (`/gerar-imagem ...`) → roda o script `scripts/gerar.py` com os args.
2. **Chamada programatica** por outras skills → executa `python3 ~/.claude/skills/gerar-imagem/scripts/gerar.py ...` diretamente.

## Cadeia de providers

Gemini e o caminho padrao porque a chave Gemini e o unico requisito garantido e possui free tier. Imagen 4 e o fallback padrao da mesma integracao Google. Codex e somente um upgrade opcional: so entra no modo automatico depois de uma falha do Gemini e se `codex login status` confirmar uma sessao logada.

| Ordem | Provider | Como | Custo |
|-------|----------|------|-------|
| **1** | **gemini-3.1-flash-image-preview** (Nano Banana) | Google GenAI SDK | Free tier / chave Gemini |
| **2** | **imagen-4.0-ultra-generate-001** | Google GenAI SDK | Free tier / chave Gemini |
| **3** | **gpt-image-2** | Codex CLI com a tool nativa `image_gen`, somente se logado | Upgrade opcional / cota da conta Codex |

No `--provider auto`, o script tenta Gemini primeiro. Se Gemini falhar, tenta Imagen 4 e verifica a sessao do Codex antes de incluir o provider opcional. Uma sessao Codex ausente nunca impede a geracao pelo caminho Google.

**Anti-distorcao embutida:** `gerar.py` anexa automaticamente a constante `ANTI_DISTORCAO` a todo prompt. A instrucao impede que pessoas, rostos, mockups, logos, texto ou outros elementos sejam esticados para preencher o formato. Skills que chamam este helper ja estao cobertas e nao precisam repetir a regra no proprio prompt.

## Quando chamar

- Usuario pede: gerar uma imagem de X, thumbnail para Y ou criativo Z
- Outra skill precisa de imagem para thumbnail, banner ou anuncio
- Um script Python precisa gerar PNG

Nao usar para: logos vetoriais com texto preciso, edicao de imagem existente ou video.

## Uso

```bash
python3 ~/.claude/skills/gerar-imagem/scripts/gerar.py --prompt 'professional youtube thumbnail, robot mascot coral orange, dark background' --output /tmp/thumb.png --size 1280x720
```

Flags:

- `--prompt` (obrigatorio) — descricao da imagem
- `--output` (obrigatorio) — caminho do PNG final
- `--size` — `1024x1024` (default), `1280x720`, `720x1280`, `1792x1024`, `1024x1792`, `1536x1024`, `1024x1536`, `1080x1080`, `1080x1350`, `1080x1920`, `1920x1080`
- `--provider` — `auto` (default), `image2`, `gemini`, `imagen`
- `--quality` — `high` (default), `medium`, `low`
- `--json` — imprime somente o resultado JSON em stdout; logs ficam silenciosos em stderr

Output: imprime o path do PNG salvo, o provider usado e o tempo. Retorna exit 0 em sucesso.

## Gate de safe-zone para anuncios

Se a imagem for criativo de anuncio Meta, rode o gate depois de gerar:

```bash
zx-safezone <arte>.png --derivar
```

O Meta desenha o perfil nos 14% do topo e legenda + CTA nos 25% da base em Stories e Reels. Headline ou preco nessas faixas podem desaparecer. Exit 1 significa que a arte nao deve ser mostrada nem publicada: regenere-a. A regra completa esta na skill `zx-safezone`.

## Cabling com outras skills

Uma skill que precise de uma thumbnail pode chamar:

```python
import json
import os
import subprocess

result = subprocess.run([
    'python3', os.path.expanduser('~/.claude/skills/gerar-imagem/scripts/gerar.py'),
    '--prompt', THUMB_PROMPT,
    '--output', '/tmp/thumb.png',
    '--size', '1280x720',
    '--json',
], capture_output=True, text=True, check=True)
info = json.loads(result.stdout)
print(f"Thumb gerada via {info['provider']} em {info['elapsed_s']}s")
```

## Detalhes tecnicos

- **Gemini:** usa `GEMINI_API_KEY` ou `GOOGLE_API_KEY` do ambiente e tambem procura essas chaves em `~/.operacao-ia/config/*.env`. A chamada usa o Google GenAI SDK.
- **Imagen 4:** usa o mesmo cliente Google GenAI SDK e a mesma chave. O resultado e normalizado para o tamanho solicitado.
- **Codex:** `codex exec` usa a tool nativa `image_gen` e exige login ChatGPT. O script verifica `codex login status` antes de considera-lo no modo automatico. A imagem pode sair em dimensao diferente da solicitada e e ajustada com pad-fit.
- **Pad-fit sem distorcao:** o gpt-image-2 pode ignorar `--size` e devolver uma dimensao diferente. Redimensionar com `sips -z` cru forca a dimensao e estica o conteudo; por isso o script usa contain, preserva a proporcao e preenche a sobra com a cor de fundo amostrada da propria arte. O fallback sem Pillow usa `sips` apenas depois de calcular dimensoes proporcionais.
- **Modo silencioso:** em `--json`, nenhum log de progresso vai para stdout, para que o chamador possa usar `json.loads(result.stdout)` sem tratamento extra.
