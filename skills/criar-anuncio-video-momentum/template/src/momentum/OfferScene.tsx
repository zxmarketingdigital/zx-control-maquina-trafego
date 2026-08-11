import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { theme, interFamily, monoFamily } from '../theme';
import { Confetti } from './Confetti';
import { content } from '../content';
import { Segments } from './Segments';

const CHIPS = content.offer.chips;

export const OfferScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const priceIn = spring({ frame: frame - 20, fps, config: { damping: 10, stiffness: 150, mass: 0.6 } });
  const oldFade = interpolate(frame, [8, 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ fontFamily: interFamily, alignItems: 'center', justifyContent: 'center', flexDirection: 'column', padding: '0 80px' }}>
      <div
        style={{
          fontSize: 46,
          fontWeight: 800,
          textAlign: 'center',
          opacity: interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          transform: `translateY(${interpolate(frame, [0, 12], [24, 0], { extrapolateRight: 'clamp' })}px)`,
        }}
      >
        <Segments segs={content.offer.pre} />
      </div>

      {/* preço âncora ACIMA do preço final (evita colisão do R$XX gigante) */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '18px 0 40px' }}>
        <span style={{ fontSize: 56, color: '#777', textDecoration: 'line-through', opacity: oldFade }}>{content.offer.oldPrice}</span>
        <span
          style={{
            fontFamily: monoFamily,
            fontSize: 200,
            fontWeight: 700,
            color: theme.amber,
            lineHeight: 0.9,
            marginTop: 6,
            opacity: interpolate(frame, [20, 23], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
            transform: `scale(${0.5 + priceIn * 0.5})`,
            textShadow: '0 0 80px rgba(217,119,6,0.6)',
          }}
        >
          {content.offer.newPrice}
        </span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, justifyContent: 'center', maxWidth: 900 }}>
        {CHIPS.map((c, i) => {
          const chip = spring({ frame: frame - (30 + i * 6), fps, config: { damping: 14, stiffness: 130, mass: 0.6 } });
          return (
            <div
              key={c}
              style={{
                fontSize: 30,
                fontWeight: 700,
                color: theme.text,
                background: theme.amberSoft,
                border: `1px solid ${theme.amber}`,
                borderRadius: 40,
                padding: '14px 28px',
                opacity: chip,
                transform: `translateY(${(1 - chip) * 30}px) scale(${0.8 + chip * 0.2})`,
              }}
            >
              ✓ {c}
            </div>
          );
        })}
      </div>

      <Confetti atFrame={22} />
    </AbsoluteFill>
  );
};
