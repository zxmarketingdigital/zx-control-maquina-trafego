import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { theme, interFamily, monoFamily } from '../theme';
import { brl } from './util';
import { content } from '../content';

// Contador de faturamento animado + gráfico de barras crescendo (data-driven).
const BARS = content.counter.bars;
const TARGET = content.counter.target;

export const CounterScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // número sobe de 0 → TARGET com easing
  const p = spring({ frame: frame - 6, fps, config: { damping: 200, stiffness: 40, mass: 1 } });
  const value = p * TARGET;

  return (
    <AbsoluteFill
      style={{ fontFamily: interFamily, alignItems: 'center', justifyContent: 'center', flexDirection: 'column', padding: '0 80px' }}
    >
      <div
        style={{
          fontFamily: monoFamily,
          fontSize: 34,
          color: theme.textDim,
          letterSpacing: 2,
          opacity: interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
        }}
      >
        {content.counter.label}
      </div>
      <div
        style={{
          fontFamily: monoFamily,
          fontSize: 150,
          fontWeight: 700,
          color: theme.amber,
          lineHeight: 1,
          margin: '14px 0 60px',
          textShadow: '0 0 60px rgba(217,119,6,0.45)',
        }}
      >
        {brl(value)}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 26, height: 460, width: '100%', justifyContent: 'center' }}>
        {BARS.map((b, i) => {
          const grow = spring({ frame: frame - (18 + i * 8), fps, config: { damping: 14, stiffness: 120, mass: 0.6 } });
          const h = b.v * 420 * grow;
          const last = i === BARS.length - 1;
          return (
            <div key={b.m} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, width: 120 }}>
              <div
                style={{
                  width: '100%',
                  height: h,
                  borderRadius: 14,
                  background: last
                    ? `linear-gradient(180deg, ${theme.amberLight}, ${theme.amber})`
                    : 'linear-gradient(180deg, #3a2a12, #241a0c)',
                  border: `1px solid ${last ? theme.amber : theme.line}`,
                  boxShadow: last ? '0 0 40px rgba(217,119,6,0.5)' : 'none',
                }}
              />
              <div style={{ fontFamily: monoFamily, fontSize: 26, color: last ? theme.amber : theme.textDim, fontWeight: 700 }}>{b.m}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
