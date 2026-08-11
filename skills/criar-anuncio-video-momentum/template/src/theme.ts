// Design System âmbar — tokens visuais do template
export const theme = {
  amber: '#D97706',
  amberLight: '#F59E0B',
  amberSoft: 'rgba(217,119,6,0.16)',
  bg: '#0a0a0a',
  surface: '#141414',
  line: '#262626',
  text: '#ffffff',
  textDim: '#b4b4b4',
  green: '#4ade80',
};

// Formato Meta 9:16
export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;

// Safe-zone Meta (Reels/Stories): topo ~14% (perfil) · base ~25% (botão "Saiba mais")
export const SAFE_TOP = 0.14;
export const SAFE_BOTTOM = 0.75;

// Fontes carregadas via @remotion/google-fonts (garante fonts.ready no render headless)
import { loadFont as loadInter } from '@remotion/google-fonts/Inter';
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono';

export const { fontFamily: interFamily } = loadInter();
export const { fontFamily: monoFamily } = loadMono();
