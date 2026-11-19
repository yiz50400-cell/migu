// Adapted from MotionGit 385712 basic.js B2/B4, MIT © 2026 MotionGit contributors.
// See ../third-party/motiongit-385712/LICENSE and provenance.json.
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {Captions, Footage, type ProductProps} from './Composition';
import {fitLines} from './text-layout';

const blue = '#7DB2FF';
const metal: React.CSSProperties = {background: 'linear-gradient(180deg,#ffffff,#abbdd3)',
  backgroundClip: 'text', WebkitTextFillColor: 'transparent'};

const Panel: React.FC<{text: string; index: number; accent: string}> = ({text, index, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = interpolate(frame, [0, .55 * fps], [0, 1],
    {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const fitted = fitLines(text, 640, 44, 34, 3);
  const color = index % 2 ? accent : blue;
  return <div style={{position: 'absolute', top: 1000, left: 80, right: 160,
    borderRadius: 13, padding: '22px 25px', display: 'flex', alignItems: 'center', gap: 24,
    border: '1px solid rgba(175,200,235,.3)', borderLeft: `3px solid ${color}`,
    background: 'linear-gradient(120deg,rgba(28,45,72,.94),rgba(8,14,25,.94))',
    boxShadow: '0 18px 60px #0006', color: '#E9ECEF', opacity: progress,
    transform: `translateX(${100 * (1 - progress)}px)`}}>
    <span style={{fontSize: 40, color, fontFamily: 'monospace'}}>{String(index + 1).padStart(2, '0')}</span>
    <span style={{fontSize: fitted.fontSize, fontWeight: 600, lineHeight: 1.12,
      whiteSpace: 'pre'}}>{fitted.text}</span>
  </div>;
};

const Heading: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const fitted = fitLines(text, 824, 72, 44, 3);
  return <div style={{position: 'absolute', top: 190, left: 80, right: 160,
    fontSize: fitted.fontSize, lineHeight: 1.12, fontWeight: 800, whiteSpace: 'pre'}}>
    {fitted.text.split('\n').map((line, i) => {
      const p = interpolate(frame, [i * 2, i * 2 + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
      return <div key={i} style={{...metal, opacity: p, transform: `translateY(${24 * (1 - p)}px)`}}>{line}</div>;
    })}
  </div>;
};

const Closing: React.FC<{text: string; accent: string}> = ({text, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fitted = fitLines(text, 824, 46, 32, 2);
  const line = interpolate(frame, [0, .55 * fps], [0, 1],
    {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  return <div style={{position: 'absolute', left: 80, right: 160, bottom: 210}}>
    <div style={{height: 3, background: `linear-gradient(90deg,${accent},${blue})`,
      boxShadow: '0 0 20px #7db2ff50', transformOrigin: 'left', transform: `scaleX(${line})`}} />
    <div style={{...metal, paddingTop: 28, fontSize: fitted.fontSize, fontWeight: 700,
      lineHeight: 1.2, whiteSpace: 'pre', opacity: line,
      transform: `translateY(${20 * (1 - line)}px)`}}>{fitted.text}</div>
  </div>;
};

export const KineticProduct: React.FC<ProductProps> = (props) => {
  const {fps, durationInFrames} = useVideoConfig();
  return <AbsoluteFill style={{background: '#050607', fontFamily: 'Arial, sans-serif'}}>
    <Footage {...props} />
    <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(5,6,7,.9),transparent 32%,transparent 50%,rgba(5,6,7,.96) 88%)'}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 15% 80%,rgba(32,47,73,.35),transparent 65%)'}} />
    {props.title ? <Sequence durationInFrames={Math.min(3 * fps, durationInFrames)}><Heading text={props.title} /></Sequence> : null}
    {props.cards.map((card, i) => <Sequence key={i} from={Math.round(card.start * fps)}
      durationInFrames={Math.round(card.end * fps) - Math.round(card.start * fps)}>
      <Panel text={card.text} index={i} accent={props.accentColor} />
    </Sequence>)}
    <Captions captions={props.captions} />
    {props.cta ? <Sequence from={Math.max(0, durationInFrames - 3 * fps)}>
      <Closing text={props.cta} accent={props.accentColor} />
    </Sequence> : null}
  </AbsoluteFill>;
};
