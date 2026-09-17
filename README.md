# ZX Control — Setup 15: Máquina de Tráfego com Claude Code

Sua linha de aquisição completa, instalada no seu computador e rodando na sua conta:
**criar o criativo → subir o tráfego → atrair no orgânico → medir tudo.**

Ao final deste setup você tem:

- 🎨 **Criativos com IA — imagem**: artes de anúncio com variações de ângulo e texto nítido, sem designer
- 🎬 **Criativos com IA — vídeo**: MP4 9:16 com narração e legenda, renderizado no seu computador
- 🎯 **Tráfego pago avançado**: estrutura de campanha Meta e Google, matriz de ângulos, CBO, escala e leitura de métrica
- 🌱 **Tráfego orgânico + Blog SEO**: um agente que escreve e publica no seu blog todo dia, no seu nicho
- 📊 **Tracking & mensuração**: pixel/CAPI, tracking de canal e atribuição — você decide pelo dado, não pelo achismo
- ⚙️ **A Máquina no automático**: as peças acima orquestradas por agentes

## Custo para instalar: R$ 0

O caminho padrão usa só contas gratuitas. Você precisa de **uma chave do Google Gemini**
(criada em ~2 minutos, free tier) e o resto roda local no seu computador. Ferramentas pagas aparecem
apenas como upgrade opcional — nenhuma etapa depende delas.

> **Nome oficial:** Setup 15 — Máquina de Tráfego com Claude Code (repositório
> `zx-control-maquina-trafego`). Não confundir com o produto *Tráfego Pago Automatizado (TPA)*,
> que é outro repositório e outra instalação.

## Pré-requisitos

Funciona no **Windows 10/11, macOS e Linux**. No Windows a instalação é nativa, pelo PowerShell:
**não precisa de WSL nem de Modo de Desenvolvedor**.

- [Claude Code](https://code.claude.com/docs/en/setup) instalado
- Git e Python 3.9 ou superior
- Node.js e Google Chrome (para renderizar os vídeos localmente)
- ffmpeg (para montar o áudio dos vídeos)
- Uma chave gratuita do Gemini — o próprio setup te guia na criação

Opcional, para quem já anuncia: conta Meta Ads, conta Google Ads, conta Cloudflare (para
publicar o blog).

### Windows (PowerShell)

Abra o **PowerShell** (não precisa ser como administrador) e rode, um por vez:

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Gyan.FFmpeg -e
winget install --id Google.Chrome -e
irm https://claude.ai/install.ps1 | iex
```

Feche e abra o PowerShell de novo para ele enxergar os programas novos. Pule qualquer linha de
algo que você já tenha instalado.

> No Windows, o comando do Python é `py -3` (o `python3` do Windows costuma abrir a Microsoft
> Store). O Claude já sabe disso e usa o comando certo sozinho.

### macOS e Linux

Instale Git, Python 3, Node.js, ffmpeg e Google Chrome pelo gerenciador do seu sistema
(Homebrew no macOS, `apt`/`dnf` no Linux) e o Claude Code com:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

## Como instalar

Os comandos abaixo podem ser repetidos sem erro: se a pasta já existir, eles só atualizam.

**Windows (PowerShell):**

```powershell
cd ~
if (Test-Path zx-control-maquina-trafego) { git -C zx-control-maquina-trafego pull } else { git clone https://github.com/zxmarketingdigital/zx-control-maquina-trafego.git }
cd zx-control-maquina-trafego
claude
```

**macOS e Linux:**

```bash
cd ~
if [ -d zx-control-maquina-trafego ]; then git -C zx-control-maquina-trafego pull; else git clone https://github.com/zxmarketingdigital/zx-control-maquina-trafego.git; fi
cd zx-control-maquina-trafego
claude
```

Quando o Claude abrir, digite:

```
INICIAR SETUP 15
```

A partir daí o Claude conduz a instalação inteira — você não precisa digitar comandos no
terminal. São 8 etapas, e você pode pular qualquer uma e voltar depois: o progresso fica salvo.

## Suporte

Dúvidas no grupo da sua turma no WhatsApp. Durante as semanas de instalação da turma você tem
suporte técnico ativo do time ZX LAB.

---

ZX Control 5.0 Traffic · ZX LAB
