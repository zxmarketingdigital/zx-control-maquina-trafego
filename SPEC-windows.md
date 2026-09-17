# SPEC — Setup 15 rodando nativo no Windows (17/09/26)

Nome oficial: **Setup 15 — Máquina de Tráfego com Claude Code**. NÃO é o produto
"Tráfego Pago Automatizado (TPA)" (outro repo). Repo: `zxmarketingdigital/zx-control-maquina-trafego` (PUBLIC).

## Objetivo
Todo script do repo roda em Windows 10/11 nativo (PowerShell + Claude Code + Git for Windows),
macOS e Linux, SEM WSL e SEM Modo de Desenvolvedor. Nada de symlink, sips, launchctl,
fcntl sem guarda, `/tmp` fixo, `/Applications` fixo, `/opt/homebrew`, `python3` fixo em spawn.

## Regras de código (todas as tarefas)
- Python 3.9 compatível: sem `X | None`, sem `match`. Use `Optional[...]`.
- Caminhos com `pathlib.Path` / `Path.home()`; temporário com `tempfile.gettempdir()`.
- Interpretador Python dentro de scripts Python: `sys.executable`. Em Node: função `resolvePython()`
  → `process.env.PYTHON` || (win32 ? `py` com args `['-3']` : `python3` se existir, senão `python`).
- Executáveis externos (codex, node, ffmpeg) via `shutil.which()` e chamar o caminho retornado
  (no Windows os shims do npm são `.cmd`; CreateProcess não resolve sem o caminho completo).
- Timeout de processo longo: constante no topo + env `ZX_<NOME>_TIMEOUT`, default 600;
  valor inválido/zero/negativo cai no default; logar elapsed.
- Não adicionar dependências novas além de: Pillow (opcional, já usado).
- Não mudar comportamento no macOS além do necessário.
- Mensagens ao usuário em português, neutras de plataforma.

## Módulos
1. `setup/agendador.py` (NOVO): `instalar(hora="08:00") -> dict`, `remover() -> dict`, `status() -> dict`
   para a tarefa diária do blog (`node <BLOG_DIR>/generator/daily_publish.js`, cwd BLOG_DIR,
   log em `<BLOG_DIR>/logs/blog-daily.log` e `-err.log`).
   - Darwin: plist atual (`launchagents/com.setup15.blog-daily.plist.template`, mesmos placeholders),
     `launchctl unload/load`, `launchctl list` para status. PATH do plist inclui dir do node resolvido.
   - Windows: wrapper `~/.operacao-ia/bin/blog-daily.cmd` (cd /d BLOG_DIR, `"<node>" generator\daily_publish.js >> logs\blog-daily.log 2>> logs\blog-daily-err.log`)
     + `schtasks /Create /SC DAILY /TN ZXSetup15BlogDaily /TR "\"<wrapper>\"" /ST 08:00 /F`;
     remover: `schtasks /Delete /TN ZXSetup15BlogDaily /F`; status: `schtasks /Query /TN ZXSetup15BlogDaily`.
   - Linux: crontab do usuário com linha marcada `# zx-setup15-blog-daily`; instalar substitui a linha
     marcada (idempotente); remover tira só ela; sem `crontab` → retorna ok=False com instrução.
   - Retorno: `{"ok": bool, "sistema": str, "detalhe": str}`. Nunca lança por SO não suportado.
   - `setup_blog.py` e `setup_uninstall.py` passam a usar esse módulo (import local via sys.path do dir do script).
   - `setup_blog.py`: `python_bin` = `sys.executable`; instrução de deploy sem `&&`
     (duas linhas: `cd blog` / `wrangler pages deploy public/ --project-name=<nome>`).
2. `skills/gerar-imagem/scripts/gerar.py`: lock multiplataforma (msvcrt no Windows, fcntl no Unix,
   arquivo em `tempfile.gettempdir()`); `sips` só no Darwin, fora dele sem Pillow → erro claro
   "instale Pillow: python -m pip install Pillow"; codex via `shutil.which` + prompt por stdin (`-`);
   `IMAGE2_TIMEOUT` (env `ZX_IMAGE2_TIMEOUT`, default 600) com elapsed logado.
3. `skills/google-campaign/scripts/build_campaign_google.py`: lock multiplataforma igual.
4. `blog/generator/daily_publish.js`: `resolvePython()` nos 3 spawnSync.
5. Chrome multiplataforma: `render.mjs`, `qa-bounds.mjs` (resolver inline: CHROME_PATH, darwin app,
   win32 `%ProgramFiles%`/`%ProgramFiles(x86)%`/`%LOCALAPPDATA%`\Google\Chrome\Application\chrome.exe,
   linux `google-chrome`/`google-chrome-stable`/`chromium`/`chromium-browser` no PATH);
   `file://` → `pathToFileURL(...).href`. `criar-arte-oferta/scripts/render.mjs` idem para `file://`.
   `setup_base_s15.py`: detecção de Chrome por SO.
6. `build.sh` → `build.mjs` (Node, ffmpeg via spawnSync, lê `timings.json` que `render.mjs` passa a gerar
   além do `timings.sh`). `build.sh` fica como wrapper `exec node build.mjs`.
7. SKILLs (`gerar-video-mp4`, `criar-anuncio-video-momentum`, `criar-anuncio-video-html`, `gerar-imagem`):
   sem `ln -sf`, sem `open`, sem `/opt/homebrew`, `npx remotion render`, instrução do Chrome por SO.
8. `setup/setup_maquina.py`: backup não recria symlink (copia o destino).
9. README.md + CLAUDE.md: pré-requisitos por SO, seção Windows nativo (PowerShell), regra do
   interpretador (`py -3` no Windows), nome unificado, comando de instalação idempotente.
10. `setup/check_multiplataforma.py` + `tests/test_multiplataforma.py` + `.github/workflows/multiplataforma.yml`
    (matriz windows/macos/ubuntu).

## Fora de escopo
Mudar a lógica de campanha, blog ou tracking; mudar provedores de imagem (Gemini segue padrão).
