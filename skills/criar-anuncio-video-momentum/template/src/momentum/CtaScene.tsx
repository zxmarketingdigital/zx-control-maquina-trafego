import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { theme, interFamily } from '../theme';
import { content } from '../content';
import { Segments } from './Segments';

export const CtaScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const head = spring({ frame: frame - 4, fps, config: { damping: 14, stiffness: 130, mass: 0.6 } });
  const btn = spring({ frame: frame - 16, fps, config: { damping: 9, stiffness: 150, mass: 0.6 } });
  const pulse = 1 + Math.sin(t * 6) * 0.03; // botão pulsando
  const arrowBounce = Math.abs(Math.sin(t * 4)) * 16;

  return (
    <AbsoluteFill style={{ fontFamily: interFamily, alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 40, padding: '0 80px' }}>
      <div
        style={{
          fontSize: 72,
          fontWeight: 900,
          textAlign: 'center',
          lineHeight: 1.08,
          opacity: head,
          transform: `translateY(${(1 - head) * 40}px)`,
        }}
      >
        <Segments segs={content.cta.headline} />
      </div>

      <div
        style={{
          background: theme.amber,
          color: '#0a0a0a',
          fontWeight: 900,
          fontSize: 52,
          padding: '32px 80px',
          borderRadius: 22,
          opacity: interpolate(frame, [16, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          transform: `scale(${(0.6 + btn * 0.4) * pulse})`,
          boxShadow: '0 20px 60px rgba(217,119,6,0.5)',
        }}
      >
        {content.cta.button}
      </div>

      <div style={{ fontSize: 80, color: theme.amber, transform: `translateY(${arrowBounce}px)`, opacity: interpolate(frame, [22, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
        ▼
      </div>
      <div style={{ fontSize: 34, color: theme.textDim, textAlign: 'center', opacity: interpolate(frame, [24, 32], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
        <Segments segs={content.cta.hint} />
      </div>
    </AbsoluteFill>
  );
};
