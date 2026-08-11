import React from 'react';
import { Composition } from 'remotion';
import { Momentum, MOMENTUM_FRAMES } from './momentum/Momentum';
import { FPS, WIDTH, HEIGHT } from './theme';

export const RemotionRoot: React.FC = () => {
  return <Composition id="Momentum" component={Momentum} durationInFrames={MOMENTUM_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />;
};
