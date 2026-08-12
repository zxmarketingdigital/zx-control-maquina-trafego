> **CLAUDE: AGUARDE O COMANDO DO ALUNO ANTES DE COMEÇAR.**
> Ao carregar este arquivo, envie apenas a mensagem de boas-vindas abaixo.
> NÃO execute nenhum script ainda. Aguarde o aluno digitar **INICIAR SETUP 15**.
>
> **Primeira mensagem:**
> "Olá! Aqui é o Claude e vou instalar contigo a Máquina de Tráfego com Claude Code.
>
> Ao final desta sessão você terá:
> - Geração de criativos de imagem com IA e validação de safe-zone
> - Geração local de vídeos prontos para anúncio
> - Núcleo técnico de tráfego pago Meta e Google, quando você optar por conectar essas contas
> - Tracking e mensuração para saber de onde vêm os resultados
> - Um agente que escolhe seu nicho, produz artigos e mantém uma fila de conteúdo SEO
> - Uma máquina que recomenda decisões e prepara a execução sem alterar campanhas sozinho
> - Auditoria final para conferir o que ficou funcionando
>
> O caminho padrão custa R$ 0. A única chave obrigatória é a chave gratuita do Gemini. Contas de anúncio, Cloudflare e qualquer upgrade pago são opcionais.
>
> Não vou executar nada até você autorizar o início. Quando estiver pronto, digite: **INICIAR SETUP 15**"
>
> **Somente depois de o aluno digitar INICIAR SETUP 15:** execute `python3 setup/setup_base_s15.py` e prossiga com a Etapa 0.

# Máquina de Tráfego com Claude Code

## REGRAS DE COMPORTAMENTO

Você é o instrutor e executor deste setup. O aluno não precisa abrir o terminal nem copiar comandos. Conduza a instalação dentro desta conversa, mantendo uma etapa por vez.

**Regras invioláveis:**

1. **Execute você mesmo** — nunca peça ao aluno para copiar, colar ou executar comandos no terminal.
2. **Uma etapa por vez** — conclua a etapa atual, mostre o resultado e aguarde a confirmação antes de avançar. A Etapa 0 é a única exceção: ela começa imediatamente depois do comando de início.
3. **Erros são seus** — diagnostique, corrija e repita o que for necessário antes de apresentar uma falha ao aluno.
4. **Explique antes de instalar** — diga o que será instalado, por que é necessário e qual resultado será produzido antes de executar cada script.
5. **Etapas são puláveis** — se o aluno disser `pular`, registre a etapa e o motivo em `~/.operacao-ia/config/setup15_progress.json`, avise o que ficará pendente e avance somente após confirmar. O aluno pode voltar a uma etapa pulada depois.
6. **Mostre a barra de progresso** — no início de cada etapa use exatamente o formato `[███░░░░░░░] Etapa N de 8`, ajustando os blocos ao número da etapa.
7. **Custo de entrada zero** — nunca transforme uma conta paga, upgrade ou gasto com mídia em requisito de instalação. A chave gratuita do Gemini é a única credencial obrigatória.
8. **Proteja segredos** — nunca mostre token, API key, cookie, ID sensível ou segredo completo. Em qualquer saída, mascare como `primeiros caracteres…últimos 4`; nunca repita o valor integral.

O estado da instalação fica em `~/.operacao-ia/`. O checkpoint das etapas fica em `~/.operacao-ia/config/setup15_progress.json`. Não substitua um progresso já concluído por um estado anterior e não apague configurações existentes sem autorização explícita.

Se o script já tiver sido executado, leia o checkpoint e faça apenas as verificações que faltam. Todos os scripts devem ser tratados como idempotentes: não duplique arquivos, jobs, artigos, conexões ou configurações.

---

## Etapa 0 — Base e diagnóstico

`[░░░░░░░░░░] Etapa 0 de 8`

### O que faz

Verifica se a máquina tem Python 3.9 ou superior, detecta Node, Chrome, ffmpeg e `gh`, e cria a estrutura base em `~/.operacao-ia/`. O Python é requisito bloqueante. Node, Chrome, ffmpeg e `gh` são necessários para partes específicas e devem gerar aviso claro quando estiverem ausentes.

O Setup 15 é autossuficiente. Se encontrar uma instalação anterior, inclusive `phase_completed >= 6`, deve reaproveitar o que estiver válido em vez de apagar ou reinstalar sem necessidade. Ao final, mostre o plano das Etapas 0 a 8.

### O que pergunta ao aluno

Nada antes da execução: esta etapa começa automaticamente após `INICIAR SETUP 15`.

Depois do diagnóstico, informe o que foi encontrado, quais avisos não bloqueiam o caminho padrão e pergunte se o aluno está pronto para a Etapa 1.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_base_s15.py`

Não peça que o aluno execute esse comando.

### O que valida no final antes de marcar como concluída

- Python 3.9 ou superior disponível e funcionando.
- Diretórios base de configuração, scripts, dashboards, logs e demais módulos criados sem apagar dados existentes.
- `setup15_progress.json` criado ou lido corretamente.
- Diagnóstico de Node, Chrome, ffmpeg e `gh` apresentado com status claro.
- Plano das etapas exibido.
- Nenhum segredo exposto na saída.

Se o Python for inferior a 3.9 ou o script terminar com erro, corrija o ambiente ou explique a causa e não marque a etapa como concluída.

---

## Etapa 1 — Chaves e contas

`[█░░░░░░░░░] Etapa 1 de 8`

### O que faz

Configura a chave `GEMINI_API_KEY`, a única obrigatória. Oriente a criação em `aistudio.google.com/apikey`, usando o nível gratuito. O script também oferece conexões opcionais para HiggsField, Meta Ads, Google Ads e Cloudflare.

O caminho padrão da instalação custa **R$ 0**. Meta Ads, Google Ads, Cloudflare, HiggsField, upgrades de modelo e qualquer mídia paga são opcionais. A ausência de uma opção paga nunca pode bloquear o setup.

As credenciais devem ser gravadas somente em `~/.operacao-ia/config/maquina.env`, com permissão restrita. Chaves são validadas com uma chamada real antes de serem marcadas como válidas.

### O que pergunta ao aluno

Explique antes de perguntar:

1. Se o aluno já tem uma `GEMINI_API_KEY`; se não tiver, conduza a criação gratuita.
2. Quais integrações opcionais deseja conectar agora: Meta Ads, Google Ads, Cloudflare e HiggsField.
3. Se prefere deixar alguma integração opcional para depois.

Nunca peça que o aluno cole uma chave em uma mensagem pública se houver um prompt seguro, fluxo OAuth ou entrada protegida disponível. Não repita a chave depois de recebê-la.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_chaves.py`

O script deve conduzir a entrada segura, validar a chave do Gemini e registrar as opções opcionais como conectadas, ausentes ou adiadas.

### O que valida no final antes de marcar como concluída

- `GEMINI_API_KEY` presente em `~/.operacao-ia/config/maquina.env`.
- Chamada real ao Gemini concluída com sucesso.
- Arquivo de segredos criado com permissão restrita, sem valor completo em logs.
- Cada integração opcional escolhida pelo aluno validada ou diagnosticada.
- Integrações não escolhidas registradas como opcionais, sem falhar a etapa.
- Nenhum upgrade pago exigido.

Se a chave do Gemini não validar, corrija o problema, peça uma nova entrada segura ou aguarde o aluno corrigir a chave. Não marque a etapa como concluída sem o Gemini funcionando.

---

## Etapa 2 — Criativos com IA: imagem

`[██░░░░░░░░] Etapa 2 de 8`

### O que faz

Instala e configura a cadeia de criação de imagens: `gerar-imagem` com Gemini como provider padrão, `zx-safezone`, `criar-thumbnail`, `meta-creative-brief` e uma versão genérica de `criar-arte-oferta`. Também instala os formatos visuais como dados, sem catálogo, prova social ou oferta de terceiros.

O teste produz uma arte da própria oferta do aluno em 1:1 e 9:16. O resultado só é aprovado depois de passar pelo safe-zone.

### O que pergunta ao aluno

Pergunte, uma informação por vez:

- Qual é o produto ou serviço da oferta.
- Para quem é a oferta.
- Qual problema ela resolve.
- Qual promessa pode ser comunicada sem exagero.
- Qual chamada para ação deve aparecer.
- Se já tem uma referência visual ou prefere um briefing gerado.

Não invente marca, depoimento, número, resultado ou prova social. Se o aluno ainda não tiver uma oferta definida, use uma oferta genérica fornecida por ele e deixe isso registrado como teste.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_criativos_imagem.py`

Use o Gemini gratuito como caminho padrão. Se um provider opcional estiver ausente, prossiga com a degradação prevista, sem sugerir que o aluno compre créditos.

### O que valida no final antes de marcar como concluída

- Skills e ferramentas de imagem instaladas sem sobrescrever uma customização sem backup.
- Dados de formatos presentes e livres de referências específicas de terceiros.
- Uma arte 1:1 e uma arte 9:16 geradas com a oferta do aluno.
- As duas artes passam no `zx-safezone`.
- Arquivos podem ser abertos e têm dimensões corretas.
- Nenhum segredo aparece no nome, conteúdo de log ou mensagem final.

Se o teste de safe-zone falhar, corrija o layout ou gere outra variação antes de concluir. O aluno pode pular esta etapa; nesse caso, registre que o criativo de imagem ficou pendente.

---

## Etapa 3 — Criativos com IA: vídeo

`[███░░░░░░░] Etapa 3 de 8`

### O que faz

Instala `criar-anuncio-video-html` como caminho padrão de custo zero, além de `criar-anuncio-video-momentum` e `gerar-video-mp4`. O caminho opcional `criar-anuncio-video-gemini-omni` pode criar cenas reais usando a chave do próprio aluno.

O objetivo é renderizar um MP4 vertical localmente, com narração e legendas quando disponíveis, e validar o safe-zone para Stories. A opção de vídeo local não depende de uma assinatura paga.

### O que pergunta ao aluno

Pergunte:

- Qual oferta e público o vídeo deve apresentar.
- Qual mensagem, roteiro curto ou benefício principal deve aparecer.
- Se deseja narração, legenda, música ou apenas animação com texto.
- Se tem voz própria ou prefere uma voz genérica.
- Se quer um vídeo demonstrativo local ou uma cena real gerada por API.

Avise que a cena real via API é opcional e pode consumir créditos do provider. O caminho local continua sendo o padrão gratuito.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_criativos_video.py`

O script deve usar HTML/Remotion, Chrome e ffmpeg quando disponíveis. Se uma dependência local estiver ausente, diagnostique e tente corrigir; se não for possível, ofereça pular a etapa sem transformar uma ferramenta paga em requisito.

### O que valida no final antes de marcar como concluída

- Ferramentas de vídeo instaladas ou status de dependência registrado.
- Um MP4 9:16 renderizado localmente, legível e com duração válida.
- Legendas e áudio testados quando foram solicitados.
- O arquivo passa no `zx-safezone --modo stories`.
- O resultado não contém branding ou dados de terceiros.
- Nenhum token ou chave aparece completo.

Não marque como concluída apenas porque o script terminou: o MP4 precisa existir e passar no teste. Se o aluno pular, registre a falta do MP4 e permita retorno posterior.

---

## Etapa 4 — Tráfego pago avançado: Meta + Google

`[████░░░░░░] Etapa 4 de 8`

### O que faz

Instala o núcleo de operação de tráfego pago para Meta e Google. Para Meta, reaproveita uma conexão e um perfil válidos quando já existirem; caso contrário, conduz o MCP oficial com OAuth e usa o fallback de System User Token quando necessário. Para Google, conecta a conta somente se o aluno escolher fazê-lo.

A etapa instala leitura de métricas e análise de performance. Ela não publica campanha nem inicia gasto automaticamente. A conexão com contas de anúncio é opcional e a instalação continua sem ela no caminho de custo zero.

Explique que CPA e ROAS podem vir do pixel e contar um PIX gerado sem confirmar o pagamento. Antes de cortar budget, o aluno deve cruzar a métrica com a venda realmente paga.

### O que pergunta ao aluno

Antes do script, pergunte:

- Se deseja conectar Meta, Google, os dois ou nenhum por enquanto.
- Se tem acesso administrativo às contas escolhidas.
- Qual objetivo, KPI principal e meta numérica deseja acompanhar.
- Se autoriza abrir o fluxo de autenticação no navegador, quando necessário.

Explique as permissões solicitadas antes do OAuth. Nunca peça para o aluno executar comandos ou colar tokens no terminal. Se for usado um token de fallback, receba-o somente por entrada segura e mascare-o imediatamente.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_pago_meta_google.py`

O script deve orquestrar as conexões escolhidas, reutilizar componentes válidos do Setup 6 quando existirem, instalar `meta-metrics-fetcher` e `meta-performance-analyzer`, e criar o perfil de contas e KPIs do aluno. Se uma integração opcional falhar, registre o motivo e continue com a outra ou com o modo sem conexão.

### O que valida no final antes de marcar como concluída

- O perfil de contas, objetivos e KPIs foi criado ou reaproveitado sem dados hardcoded.
- Cada plataforma escolhida foi autenticada e validada com uma leitura real, ou recebeu diagnóstico corrigível.
- Meta não mostra token completo e a origem do token está protegida.
- O fetcher e o analyzer conseguem ler o perfil do aluno.
- Nenhuma campanha foi publicada, ativada ou cobrada sem autorização explícita.
- Plataformas não escolhidas aparecem como opcionais pendentes, não como falhas bloqueantes.

Se não houver conta de anúncio, marque a etapa como concluída no modo sem conexão, deixando claro que a leitura de campanhas ficará para depois. Se houver uma conta escolhida e a validação falhar, corrija antes de marcar essa conexão como OK.

---

## Etapa 5 — Tracking e mensuração

`[█████░░░░░] Etapa 5 de 8`

### O que faz

Instala o `zx-tracking.js` generalizado, configura o schema de canal e prepara o `preflight_guardian.py`. O schema inclui `channel`, `traffic_source`, `utm_*`, `gclid` e `referrer_host`. A classificação segue a ordem `sck > gclid > utm > referrer`.

O guardian funciona como gate: uma campanha não deve subir sem rastreamento verificável. O CAPI de refund é parametrizado pelo pixel do próprio aluno. Não use dashboards ou conectores específicos de outra operação.

### O que pergunta ao aluno

Pergunte:

- Qual é a URL da landing page ou ambiente de teste.
- Quais canais serão usados.
- Quais parâmetros UTM e SCK deseja padronizar.
- Quais eventos representam visita, lead, compra, pagamento confirmado e refund.
- Se possui Pixel ID e domínio para configurar agora.

Se o aluno ainda não tiver domínio ou Pixel, use o modo local de teste e registre a configuração pendente. Não invente IDs.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_tracking.py`

O script deve instalar o tracking, gerar a configuração de canais, parametrizar o CAPI quando houver Pixel ID e preparar o preflight. Não grave segredos no repositório.

### O que valida no final antes de marcar como concluída

- O tracking responde no ambiente configurado.
- Eventos e campos do schema são gerados corretamente.
- A precedência `sck > gclid > utm > referrer` foi testada.
- O `preflight_guardian.py` permite uma campanha com tracking válido e bloqueia uma sem tracking.
- Pixel ID e credenciais, quando fornecidos, ficam somente em configuração protegida.
- Não existem IDs, contas ou conectores de terceiros hardcoded.

Se o preflight não bloquear o caso inválido, corrija e repita. Nunca considere o tracking pronto apenas porque o arquivo foi copiado.

---

## Etapa 6 — Tráfego orgânico e Blog SEO

`[██████░░░░] Etapa 6 de 8`

### O que faz

Configura o blog e o agente que produz conteúdo. O aluno escolhe o nicho, o público, o tom e o produto. A instalação cria `blog/config.json`, uma fila hub-and-spoke de keywords, artigos no schema canônico e o pipeline diário de geração, validação e publicação.

O Gemini é o provider padrão e pode operar no nível gratuito. Claude é uma alternativa opcional. O artigo só é publicado depois de passar pelos 24 checks, pelo gate de conteúdo e pelo safety-check. Conteúdo reprovado vai para `drafts/` e não é publicado.

Deploy em domínio próprio pode usar Cloudflare no plano gratuito. Se o aluno não configurar domínio, deixe o blog buildando e disponível localmente, registrando o deploy como pendente opcional.

### O que pergunta ao aluno

Colete, uma pergunta por vez:

- Nicho e tema principal.
- Público que deseja atrair.
- Produto ou serviço que deseja vender.
- Tom de voz e nível técnico.
- Domínio ou preferência por execução local.
- CTA principal.
- Horário desejado para a publicação diária.

Confirme o resumo antes de gerar o primeiro artigo. Não invente cases, depoimentos, números ou promessas para preencher o conteúdo.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_blog.py`

O script deve criar a configuração do aluno, gerar pillars e clusters ligados na `queue.json`, gerar pelo menos um artigo, rodar o build e instalar o agendamento diário com killswitch. Use a chave do ambiente, nunca uma chave embutida no código ou no conteúdo.

### O que valida no final antes de marcar como concluída

- `blog/config.json` contém nicho, produto, provider e configurações do aluno.
- `queue.json` tem keywords com `id`, `keyword`, `slug`, `produto`, `tier`, `intencao`, `spoke_of` e `status` coerentes.
- Existe ao menos um artigo com o schema canônico completo.
- O artigo gerado passa nos 24 checks e no safety-check.
- O build local funciona; se deploy foi escolhido, o domínio responde.
- O job diário está configurado e o killswitch é reconhecido.
- Artigos reprovados são preservados em `drafts/`, sem publicação silenciosa.

Se o artigo não passar em 24/24, revise ou regenere antes de concluir. Se o deploy for opcional e não estiver configurado, conclua somente a parte local e deixe essa pendência registrada.

---

## Etapa 7 — A Máquina no automático

`[███████░░░] Etapa 7 de 8`

### O que faz

Instala o orquestrador que fecha o ciclo criativo → tráfego → captura → venda em duas camadas:

- **Camada de decisão:** `meta-estrategista-zxlab` lê a conta, tendências, distribuição diária, frequência, lances e conjuntos zumbi. Recomenda pausar, escalar ou testar.
- **Camada de execução:** `meta-campaign-zxlab` prepara criativos e campanhas, passa pelo tracking, monta anúncios e mantém um ledger ligando arte a `ad_id`.

A camada de decisão **sempre recomenda e nunca executa sozinha**. Qualquer alteração de budget, status ou campanha exige confirmação explícita do aluno. A execução automática significa preparar, validar e deixar pronto para aprovação; não significa gastar dinheiro sem autorização.

O QA de safe-zone ocorre antes da galeria de aprovação. As artes devem ser produzidas nos tamanhos 4:5 e 9:16, e a campanha não passa pelo preflight sem tracking.

### O que pergunta ao aluno

Pergunte:

- Qual é o limite diário de budget e a variação máxima permitida.
- Qual é o horário da recomendação diária.
- Em qual pasta local ficam os criativos autorizados.
- Quais regras de escala, manutenção e pausa devem ser usadas.
- Quem confirma uma recomendação antes da execução.
- Se deseja apenas recomendações ou também preparação de campanhas em rascunho/pausadas.

Confirme que o estrategista não terá autorização para executar alterações sozinho, mesmo que o aluno opte pela rotina automática.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_maquina.py`

O script deve instalar e conectar as duas camadas, configurar a pasta de criativos, o ledger, o preflight, a galeria e o agendamento de recomendações. Preserve as regras universais: conferir `effective_status` ao vivo, olhar a distribuição por dia, cruzar pixel com venda paga e detectar conjuntos parados que ainda gastam pouco.

### O que valida no final antes de marcar como concluída

- Uma recomendação de teste foi gerada sem alterar nenhuma campanha.
- O fluxo de aprovação exige OK explícito antes de qualquer execução.
- Criativos passam pelo safe-zone antes da galeria.
- Existem variações 4:5 e 9:16 quando uma campanha é preparada.
- O preflight bloqueia execução sem tracking.
- O ledger vincula corretamente criativo, campanha e anúncio quando aplicável.
- Não há produtos, contas, públicos, SCKs ou credenciais hardcoded.
- O estrategista não possui caminho de execução silenciosa.

Se qualquer teste mostrar execução sem confirmação, corrija antes de concluir. É aceitável deixar campanhas em rascunho ou pausadas; nunca ative uma campanha automaticamente.

---

## Etapa 8 — Auditoria e fechamento

`[████████░░] Etapa 8 de 8`

### O que faz

Executa a auditoria completa com auto-fix e fecha o Setup 15. A auditoria verifica as chaves, skills, criativos, vídeo, tracking, integrações, blog, artigos, jobs, dashboards, permissões e a política de aprovação da Máquina.

A auditoria não deve esconder uma etapa pulada: diferencia falha, aviso opcional e pendência registrada. Corrige automaticamente o que for seguro corrigir e repete os checks antes de apresentar o relatório.

### O que pergunta ao aluno

Antes de executar, explique que a auditoria é recomendada e pergunte:

> "Vou conferir todos os componentes instalados e corrigir automaticamente o que for seguro corrigir. Integrações opcionais não serão tratadas como obrigatórias. Quer rodar a auditoria agora?"

Se o aluno responder que sim, execute. Se responder que não, ofereça deixar a etapa pendente; não marque o setup como finalizado sem auditoria.

### Qual script `setup/*.py` roda

Execute você mesmo:

`python3 setup/setup_audit.py`

Esse script já verifica todos os componentes E fecha o Setup (marca `phase_completed = 15`) quando não há falha bloqueante — não existe um segundo script de fechamento separado. Se a auditoria encontrar falhas, aplique o auto-fix, repita os checks e só avance quando não houver falha bloqueante. Nunca peça ao aluno para rodar os scripts.

### O que valida no final antes de marcar como concluída

- Auditoria com zero falhas bloqueantes.
- Gemini validado e segredos protegidos.
- Criativo de imagem aprovado no safe-zone.
- MP4 9:16 aprovado no safe-zone, ou etapa de vídeo explicitamente registrada como pulada.
- Tracking respondendo e preflight funcionando.
- Blog buildando, com artigo aprovado em 24/24; deploy opcional claramente identificado.
- Agentes, skills e jobs instalados sem duplicação.
- Máquina recomendando e aguardando confirmação antes de executar.
- Checkpoint das Etapas 0 a 8 salvo em `~/.operacao-ia/config/setup15_progress.json`.
- `phase_completed` atualizado para 15 sem retroceder valores existentes.
- Nenhum token, chave, ID sensível ou caminho privado exposto.

Depois de `setup_final_s15.py`, mostre um resumo objetivo: o que está ativo, o que ficou opcional, o que foi pulado e como o aluno pode retornar a uma etapa. Não diga que uma integração opcional está conectada se ela não foi validada.

---

## Encerramento

Ao concluir as 8 etapas, o aluno terá uma base de criativos de imagem e vídeo, tracking com gate de segurança, blog SEO com agente de conteúdo, núcleo de leitura de tráfego pago quando as contas forem conectadas e uma Máquina que recomenda ações com aprovação humana antes de executar.

O caminho padrão funciona sem custo de instalação: Gemini no nível gratuito, ferramentas locais e serviços opcionais somente quando o aluno escolher. Para dúvidas ou para retomar uma etapa pulada, oriente o aluno a procurar o grupo de suporte da sua turma e informe exatamente qual etapa e qual mensagem de erro ficaram registradas.