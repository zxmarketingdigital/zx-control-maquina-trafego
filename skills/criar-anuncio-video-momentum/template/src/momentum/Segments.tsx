import React from 'react';
import { theme } from '../theme';
import type { Seg } from '../content';

// Renderiza uma copy com destaques (âmbar / bold) a partir de segmentos.
export const Segments: React.FC<{ segs: Seg[] }> = ({ segs }) => (
  <>
    {segs.map((s, i) => (
      <span key={i} style={{ color: s.amber ? theme.amber : undefined, fontWeight: s.b ? 800 : undefined }}>
        {s.t}
      </span>
    ))}
  </>
);
