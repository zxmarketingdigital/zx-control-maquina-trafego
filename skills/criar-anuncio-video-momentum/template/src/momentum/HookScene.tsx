import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { theme, interFamily, monoFamily } from '../theme';
import { content } from '../content';

// Tipografia cinética: cada palavra entra com spring (escala + slide), palavra-chave em âmbar.
export const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        fontFamily: interFamily,
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 90px',
        flexDirection: 'column',
        gap: 18,
      }}
    >
      <div
        style={{
          fontFamily: monoFamily,
          fontSize: 30,
          color: theme.amber,
          letterSpacing: 6,
          marginBottom: 30,
          opacity: interpolate(frame, [2, 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
        }}
      >
        {content.brandKicker}
      </div>
      {content.hookLines.map((l, i) => {
        const delay = 8 + i * 9;
        const s = spring({ frame: frame - delay, fps, config: { damping: 13, stiffness: 140, mass: 0.7 } });
        return (
          <div
            key={i}
            style={{
              fontSize: 92,
              fontWeight: 900,
              lineHeight: 1.02,
              letterSpacing: -2,
              textAlign: 'center',
              color: l.amber ? theme.amber : theme.text,
              opacity: s,
              transform: `translateY(${(1 - s) * 60}px) scale(${0.7 + s * 0.3})`,
              textShadow: l.amber ? '0 0 60px rgba(217,119,6,0.5)' : 'none',
            }}
          >
            {l.t}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
