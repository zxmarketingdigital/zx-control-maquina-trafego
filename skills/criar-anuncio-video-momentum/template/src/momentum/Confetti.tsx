import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { theme } from '../theme';
import { seeded } from './util';

// Explosão de confete determinística — dispara em `atFrame`, cai com gravidade.
export const Confetti: React.FC<{ atFrame: number; count?: number }> = ({ atFrame, count = 60 }) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const t = (frame - atFrame) / fps; // segundos desde a explosão
  if (t < 0) return null;

  const colors = [theme.amber, theme.amberLight, '#FCD34D', '#ffffff', theme.green];
  return (
    <>
      {Array.from({ length: count }).map((_, i) => {
        const ang = seeded(i + 1) * Math.PI * 2;
        const speed = 500 + seeded(i + 7) * 900;
        const vx = Math.cos(ang) * speed;
        const vy = Math.sin(ang) * speed - 700; // impulso pra cima
        const g = 1500;
        const x = width / 2 + vx * t;
        const y = height * 0.42 + vy * t + 0.5 * g * t * t;
        const rot = seeded(i + 3) * 360 + t * 400;
        const size = 12 + seeded(i + 11) * 18;
        const op = Math.max(0, 1 - t / 2.2);
        if (op <= 0) return null;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: size,
              height: size * 0.55,
              background: colors[i % colors.length],
              transform: `rotate(${rot}deg)`,
              opacity: op,
              borderRadius: 2,
              zIndex: 70,
            }}
          />
        );
      })}
    </>
  );
};
