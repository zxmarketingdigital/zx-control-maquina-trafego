// Monta os MP4 de TODAS as variações: SFX (1x) + vídeo por variante + mix de áudio.
// Tempos de digitação/caixa vêm de timings.json (gerado pelo render.mjs).
// Roda igual no Windows (PowerShell), macOS e Linux: `node build.mjs`.
import { spawnSync } from 'child_process';
import { existsSync, mkdirSync, readFileSync, rmSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
process.chdir(SCRIPT_DIR);

const MUSIC = join(SCRIPT_DIR, 'assets', 'trilhas-cc0', 'arcade-funk.mp3');
if (!existsSync(MUSIC)) {
  console.log(`ERRO: trilha não encontrada em ${MUSIC}. Edite a constante MUSIC no build.mjs.`);
  process.exit(1);
}
if (!existsSync('timings.json')) {
  console.log("ERRO: timings.json não encontrado. Rode 'node render.mjs' primeiro.");
  process.exit(1);
}
const AUD = 'audio';
mkdirSync(AUD, { recursive: true });

function ffmpeg(args) {
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', ...args], { stdio: 'inherit' });
  if (r.error) {
    console.log(`ERRO: não consegui rodar o ffmpeg (${r.error.message}). Instale e deixe no PATH.`);
    process.exit(1);
  }
  if (r.status !== 0) process.exit(1);
}

// --- SFX (sintetizados uma vez, reusados por todas as variações) ---
const typingWav = join(AUD, 'sfx-typing.wav');
if (!existsSync(typingWav)) {
  console.log('SFX digitação');
  ffmpeg(['-f', 'lavfi',
    '-i', "aevalsrc='(2*random(0)-1)*exp(-mod(t,0.11)*80)*lt(mod(t,0.11),0.045)':d=6:s=44100",
    '-af', 'highpass=f=1100,lowpass=f=7000,volume=0.55', typingWav]);
}
const caixaWav = join(AUD, 'sfx-caixa.wav');
if (!existsSync(caixaWav)) {
  console.log('SFX caixa registradora');
  ffmpeg(['-f', 'lavfi',
    '-i', "aevalsrc='(0.5*(2*random(0)-1)*exp(-t*45))*lt(t,0.06) + (sin(2*PI*1319*t)+0.4*sin(2*PI*2638*t))*exp(-t*8)*0.6*lt(t,0.55) + (sin(2*PI*1760*(t-0.12))+0.4*sin(2*PI*3520*(t-0.12)))*exp(-(t-0.12)*8)*0.6*gt(t,0.12)':d=0.8:s=44100",
    '-af', 'volume=0.95', caixaWav]);
}

const { variants } = JSON.parse(readFileSync('timings.json', 'utf8'));
for (const { id, typing, cash } of variants) {
  const typMs = Math.round(typing * 1000);
  const cashMs = Math.round(cash * 1000);
  const typFade = (typing + 2.5).toFixed(2);
  console.log(`== variação ${id} (digitação @${typing}s, caixa @${cash}s) ==`);

  const mudo = `mudo-${id}.mp4`;
  ffmpeg(['-framerate', '30', '-i', `frames-${id}/f%04d.png`,
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', mudo]);

  const filtro = [
    '[1:a]atrim=0:22,aformat=channel_layouts=stereo:sample_rates=44100,volume=0.26,afade=t=in:st=0:d=0.4,afade=t=out:st=20.3:d=1.7[mus]',
    `[2:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay=${typMs}|${typMs},volume=0.5,afade=t=out:st=${typFade}:d=0.5[ty]`,
    `[3:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay=${cashMs}|${cashMs},volume=0.72[ka]`,
    '[mus][ty][ka]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[a]',
  ].join(';');
  ffmpeg(['-i', mudo, '-i', MUSIC, '-i', typingWav, '-i', caixaWav,
    '-filter_complex', filtro,
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', `anuncio-${id}.mp4`]);

  rmSync(mudo, { force: true });
  console.log(`   -> anuncio-${id}.mp4`);
}
console.log(`OK — variações: ${variants.map(v => v.id).join(' ')}`);
