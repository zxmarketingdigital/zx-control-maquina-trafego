#!/usr/bin/env bash
# Monta os MP4 de TODAS as variações: SFX (1x) + vídeo por variante + mix de áudio.
# Tempos de digitação/caixa vêm de timings.sh (gerado pelo render.mjs).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MUSIC="$SCRIPT_DIR/../assets/trilhas-cc0/arcade-funk.mp3"
[ -f "$MUSIC" ] || { echo "ERRO: trilha não encontrada em $MUSIC. Edite a variável MUSIC no build.sh."; exit 1; }
[ -f timings.sh ] || { echo "ERRO: timings.sh não encontrado. Rode 'node render.mjs' primeiro."; exit 1; }
AUD=audio; mkdir -p "$AUD"

# --- SFX (sintetizados uma vez, reusados por todas as variações) ---
if [ ! -f "$AUD/sfx-typing.wav" ]; then
  echo "SFX digitação"
  ffmpeg -y -v error -f lavfi \
    -i "aevalsrc='(2*random(0)-1)*exp(-mod(t,0.11)*80)*lt(mod(t,0.11),0.045)':d=6:s=44100" \
    -af "highpass=f=1100,lowpass=f=7000,volume=0.55" "$AUD/sfx-typing.wav"
fi
if [ ! -f "$AUD/sfx-caixa.wav" ]; then
  echo "SFX caixa registradora"
  ffmpeg -y -v error -f lavfi \
    -i "aevalsrc='(0.5*(2*random(0)-1)*exp(-t*45))*lt(t,0.06) + (sin(2*PI*1319*t)+0.4*sin(2*PI*2638*t))*exp(-t*8)*0.6*lt(t,0.55) + (sin(2*PI*1760*(t-0.12))+0.4*sin(2*PI*3520*(t-0.12)))*exp(-(t-0.12)*8)*0.6*gt(t,0.12)':d=0.8:s=44100" \
    -af "volume=0.95" "$AUD/sfx-caixa.wav"
fi

# shellcheck disable=SC1091
source ./timings.sh

for id in $VARIANTS; do
  tvar="TYPING_$id"; cvar="CASH_$id"
  TYP="${!tvar}"; CASH="${!cvar}"
  TYP_MS=$(awk "BEGIN{printf \"%.0f\", $TYP*1000}")
  CASH_MS=$(awk "BEGIN{printf \"%.0f\", $CASH*1000}")
  TYP_FADE=$(awk "BEGIN{printf \"%.2f\", $TYP+2.5}")
  echo "== variação $id (digitação @${TYP}s, caixa @${CASH}s) =="

  ffmpeg -y -v error -framerate 30 -i "frames-$id/f%04d.png" \
    -c:v libx264 -pix_fmt yuv420p -crf 18 -preset medium "mudo-$id.mp4"

  ffmpeg -y -v error -i "mudo-$id.mp4" -i "$MUSIC" -i "$AUD/sfx-typing.wav" -i "$AUD/sfx-caixa.wav" \
    -filter_complex "\
     [1:a]atrim=0:22,aformat=channel_layouts=stereo:sample_rates=44100,volume=0.26,afade=t=in:st=0:d=0.4,afade=t=out:st=20.3:d=1.7[mus];\
     [2:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay=${TYP_MS}|${TYP_MS},volume=0.5,afade=t=out:st=${TYP_FADE}:d=0.5[ty];\
     [3:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay=${CASH_MS}|${CASH_MS},volume=0.72[ka];\
     [mus][ty][ka]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "anuncio-$id.mp4"

  rm -f "mudo-$id.mp4"
  echo "   -> anuncio-$id.mp4"
done
echo "OK — variações: $VARIANTS"
