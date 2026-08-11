// Configs das variações do anúncio. Cada uma muda ângulo/headline/ordem das cenas.
// A ordem define qual cena ocupa cada slot de tempo (0-6s, 6-12s, 12-18s, 18-22s).
// O áudio (digitação/caixa) é derivado da ordem pelo render.mjs.
//
// ===== CAMPOS QUE DEVEM SER TROCADOS POR PRODUTO =====
// kick       : linha pequena acima da headline (ex: '// com [PRODUTO]')
// big        : headline principal — HTML permitido, <b> em âmbar (ex: 'Fature <b>5 dígitos</b>...')
// headlineSize: tamanho em px (64 = 1 linha curta; 56 = 1-2 linhas; 48 = 2-3 linhas)
// scene1sub  : subtítulo exibido NA CENA DO TERMINAL especificamente (slot onde 'terminal' estiver)
//              se a order mudar, o subtítulo ainda renderiza no slot correto — mas o texto deve
//              fazer sentido pro contexto do terminal (o que a IA faz)
// order      : ordem das 4 cenas fixas ['terminal','whatsapp','offer','cta'] — permutável
//
// ATENÇÃO: este arquivo controla APENAS headline/ordem/ângulo.
// Os textos de conteúdo (balões WhatsApp, bullets da oferta, preços, logo, CTA)
// ficam em ad.html (seção marcada com "CONTEÚDO DO PRODUTO — EDITAR TUDO ABAIXO")
// e DEVEM ser editados separadamente para cada produto.
//
// As 4 cenas (terminal/whatsapp/offer/cta) e os 4 slots de 6s cada são FIXOS no motor.
// Não é possível remover ou adicionar cenas sem refatorar ad.html e render.mjs.
// Sempre usar todas as 4 na order, mesmo que a cena de terminal precise ser adaptada
// para outro tipo de UI (ex: mock de dashboard).
// ======================================================

// Exemplo com placeholders para novo produto:
// { id:'a', angulo:'aspiração', kick:'// com [PRODUTO]', big:'[HEADLINE DO PRODUTO]',
//   headlineSize:64, order:['terminal','whatsapp','offer','cta'],
//   scene1sub:'[O que a IA faz — subtítulo da cena terminal]' }

export const VARIANTS = [
  {
    id: 'a',
    angulo: 'aspiração',
    kick: '// com [PRODUTO]',           // EDITAR: ex '// com Claude Code'
    big: '[HEADLINE DO PRODUTO]',        // EDITAR: ex 'Fature <b>5 dígitos</b> com sua Agência de IA'
    headlineSize: 64,
    order: ['terminal', 'whatsapp', 'offer', 'cta'],
    scene1sub: '[Subtítulo da cena terminal]', // EDITAR: ex 'Uma automação que você <b>vende</b> — pronta em minutos'
  },
  {
    id: 'b',
    angulo: 'resultado-primeiro (hook dinheiro)',
    kick: '// com [PRODUTO]',
    big: '[HEADLINE VARIAÇÃO B — resultado em destaque]',
    headlineSize: 56,
    order: ['whatsapp', 'terminal', 'offer', 'cta'],
    scene1sub: '[Subtítulo da cena terminal — variação B]',
  },
  {
    id: 'c',
    angulo: 'quebra de objeção',
    kick: '// com [PRODUTO]',
    big: '[HEADLINE VARIAÇÃO C — quebra de objeção]',
    headlineSize: 56,
    order: ['terminal', 'whatsapp', 'offer', 'cta'],
    scene1sub: '[Subtítulo da cena terminal — variação C]',
  },
];
