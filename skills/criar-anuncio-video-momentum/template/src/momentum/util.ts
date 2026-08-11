// PRNG determinístico (seed → sempre o mesmo valor, estável entre frames no render)
export function seeded(seed: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

// formata número como moeda BRL sem centavos
export function brl(n: number): string {
  return 'R$' + Math.round(n).toLocaleString('pt-BR');
}
