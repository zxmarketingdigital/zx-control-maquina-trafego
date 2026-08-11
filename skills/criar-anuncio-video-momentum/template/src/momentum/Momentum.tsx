import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { TransitionSeries, springTiming, linearTiming } from '@remotion/transitions';
import { slide } from '@remotion/transitions/slide';
import { wipe } from '@remotion/transitions/wipe';
import { fade } from '@remotion/transitions/fade';
import { theme, interFamily } from '../theme';
import { HookScene } from './HookScene';
import { CounterScene } from './CounterScene';
import { OfferScene } from './OfferScene';
import { CtaScene } from './CtaScene';

// duração jogável = soma das sequências - soma das transições
// 120+150+165+140 = 575 ; transições 18+15+12 = 45 ; total = 530
export const MOMENTUM_FRAMES = 530;

const AnimatedBg: React.FC = () => {
  const frame = useCurrentFrame();
  const x = 50 + Math.sin(frame / 60) * 12;
  const y = 30 + Math.cos(frame / 80) * 10;
  const glow = interpolate(Math.sin(frame / 40), [-1, 1], [0.1, 0.22]);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        backgroundImage: `radial-gradient(1300px 900px at ${x}% ${y}%, rgba(217,119,6,${glow}), transparent 62%),
          radial-gradient(900px 700px at 50% 100%, rgba(217,119,6,0.06), transparent 60%)`,
      }}
    >
      <AbsoluteFill
        style={{
          opacity: 0.3,
          backgroundImage: `linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)`,
          backgroundSize: '70px 70px',
        }}
      />
    </AbsoluteFill>
  );
};

export const Momentum: React.FC = () => {
  return (
    <AbsoluteFill style={{ fontFamily: interFamily, color: theme.text }}>
      <AnimatedBg />
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={120}>
          <HookScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={slide({ direction: 'from-bottom' })} timing={springTiming({ config: { damping: 200 }, durationInFrames: 18 })} />
        <TransitionSeries.Sequence durationInFrames={150}>
          <CounterScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={wipe({ direction: 'from-right' })} timing={linearTiming({ durationInFrames: 15 })} />
        <TransitionSeries.Sequence durationInFrames={165}>
          <OfferScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 12 })} />
        <TransitionSeries.Sequence durationInFrames={140}>
          <CtaScene />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
