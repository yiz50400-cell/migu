// Original product layouts. No external media, fonts, audio or template engine.
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {Captions, Footage, type ProductProps} from './Composition';
import {fitLines} from './text-layout';

export type ProductVariant = 'comparison-review' | 'step-guide' | 'unboxing-reveal' | 'minimal-luxe';
type VariantProps = ProductProps & {variant: ProductVariant};
const area: React.CSSProperties = {position: 'absolute', left: 80, right: 160};
const textStyle: React.CSSProperties = {whiteSpace: 'pre', lineHeight: 1.16, fontWeight: 700};
const useEntrance = (seconds = .45) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return interpolate(frame, [0, seconds * fps], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
};

const Title: React.FC<Pick<VariantProps, 'title' | 'variant' | 'accentColor'>> = (props) => {
  const p = useEntrance();
  const fitted = fitLines(props.title, 744, props.variant === 'minimal-luxe' ? 60 : 66, 40, 3);
  const base: React.CSSProperties = {...area, top: 190, ...textStyle, fontSize: fitted.fontSize, opacity: p};
  if (props.variant === 'minimal-luxe') return <div style={{...base, textAlign: 'center',
    fontWeight: 400, color: '#202b2b', padding: '24px 40px', transform: `translateY(${12 * (1 - p)}px)`}}>
    <div style={{width: 64, height: 2, background: props.accentColor, margin: '0 auto 24px'}} />{fitted.text}
  </div>;
  if (props.variant === 'unboxing-reveal') return <div style={{...base, color: '#fff', padding: '24px 40px',
    background: '#291f32ed', borderRadius: '28px 28px 28px 0', borderBottom: `4px solid ${props.accentColor}`,
    transform: `translateY(${-25 * (1 - p)}px)`}}>{fitted.text}</div>;
  if (props.variant === 'step-guide') return <div style={{...base, color: '#fff', padding: '24px 40px',
    borderLeft: `6px solid ${props.accentColor}`, background: '#072d2aea',
    clipPath: `inset(0 ${100 * (1 - p)}% 0 0)`}}>{fitted.text}</div>;
  return <div style={{...base, color: '#fff', padding: '24px 40px', borderTop: '3px solid #a7ddd6',
    background: '#0f1f32ef', transform: `translateX(${-24 * (1 - p)}px)`}}>{fitted.text}</div>;
};

type CardProps = {text: string; index: number; total: number; accent: string; variant: ProductVariant};
const Card: React.FC<CardProps> = ({text, index, total, accent, variant}) => {
  const p = useEntrance();
  if (variant === 'comparison-review') {
    const side = index % 2;
    const fitted = fitLines(text, 340, 38, 28, 4);
    return <div style={{...area, top: 950, display: 'flex', gap: 24}}>
      {['A', 'B'].map((label, i) => <div key={label} style={{width: 408, height: 250,
        boxSizing: 'border-box', padding: 20, borderRadius: 18,
        background: i === side ? '#102a3ff5' : '#0b1524da',
        border: `2px solid ${i === side ? (side ? accent : '#8ee0d3') : '#41536a'}`}}>
        <div style={{fontSize: 30, fontWeight: 800, color: i === side ? '#fff' : '#8b9bae',
          display: 'flex', alignItems: 'center', gap: 12}}>
          <span style={{width: 10, height: 10, borderRadius: '50%', background: i === side ? accent : '#41536a'}} />{label}
        </div>
        {i === side ? <div style={{...textStyle, marginTop: 14, fontSize: fitted.fontSize, color: '#fff',
          opacity: p, transform: `translateX(${(side ? 1 : -1) * 28 * (1 - p)}px)`}}>{fitted.text}</div>
          : <div style={{width: 48, height: 2, background: '#41536a', marginTop: 42}} />}
      </div>)}
    </div>;
  }
  if (variant === 'step-guide') {
    const fitted = fitLines(text, 608, 46, 34, 3);
    return <div style={{...area, top: 1000, display: 'flex', gap: 24, alignItems: 'center', padding: 24,
      background: '#063b35f5', borderRadius: 24, border: '1px solid #3c746b',
      opacity: p, transform: `translateY(${35 * (1 - p)}px)`}}>
      <div style={{width: 112, flexShrink: 0, textAlign: 'center', color: accent}}>
        <div style={{fontSize: 64, fontWeight: 800}}>{String(index + 1).padStart(2, '0')}</div>
        <div style={{fontSize: 22, color: '#c1dcd6'}}>/ {String(total).padStart(2, '0')}</div>
      </div>
      <div style={{...textStyle, fontSize: fitted.fontSize, color: '#fff'}}>{fitted.text}</div>
    </div>;
  }
  if (variant === 'unboxing-reveal') {
    const fitted = fitLines(text, 710, 46, 34, 3);
    return <div style={{...area, top: 1010, opacity: p,
      transform: `translateY(${30 * (1 - p)}px) rotate(${-3 * (1 - p)}deg)`,
      background: '#f6eee2', color: '#30263b', borderRadius: '0 24px 24px 24px',
      boxShadow: '12px 12px 0 #1f162b80', padding: '24px 32px 24px 70px'}}>
      <div style={{position: 'absolute', top: 30, left: 26, width: 14, height: 14,
        border: '3px solid #30263b', borderRadius: '50%'}} />
      <div style={{...textStyle, fontSize: fitted.fontSize}}>{fitted.text}</div>
    </div>;
  }
  const fitted = fitLines(text, 744, 44, 32, 3);
  return <div style={{...area, top: 1010, textAlign: 'center', padding: '24px 40px',
    background: '#f8f4edee', color: '#202b2b', opacity: p, transform: `translateY(${14 * (1 - p)}px)`}}>
    <div style={{...textStyle, fontSize: fitted.fontSize, fontWeight: 400}}>{fitted.text}</div>
    <div style={{height: 1, width: 120, margin: '24px auto 0', background: accent,
      transform: `scaleX(${p})`}} />
  </div>;
};

const ProgressRail: React.FC<Pick<VariantProps, 'cards' | 'accentColor'>> = ({cards, accentColor}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return <div style={{...area, top: 490, display: 'flex', gap: 8}}>
    {cards.map((card, i) => {
      const from = Math.round(card.start * fps);
      const to = Math.round(card.end * fps);
      const amount = interpolate(frame, [from, to], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
      return <div key={i} style={{flex: 1, height: 8, background: '#315e59', borderRadius: 4}}>
        <div style={{height: '100%', background: accentColor, borderRadius: 4, width: `${amount * 100}%`}} />
      </div>;
    })}
  </div>;
};

const RevealCorners: React.FC = () => {
  const p = useEntrance(.7);
  return <div style={{...area, top: 490, height: 470, opacity: p, transform: `scale(${.94 + .06 * p})`}}>
    {[0, 1, 2, 3].map((i) => <div key={i} style={{position: 'absolute', width: 52, height: 52,
      top: i < 2 ? 0 : undefined, bottom: i > 1 ? 0 : undefined,
      left: i % 2 === 0 ? 0 : undefined, right: i % 2 ? 0 : undefined,
      borderTop: i < 2 ? '3px solid #f6eee2' : undefined,
      borderBottom: i > 1 ? '3px solid #f6eee2' : undefined,
      borderLeft: i % 2 === 0 ? '3px solid #f6eee2' : undefined,
      borderRight: i % 2 ? '3px solid #f6eee2' : undefined}} />)}
  </div>;
};

const Closing: React.FC<Pick<VariantProps, 'cta' | 'variant' | 'accentColor'>> = ({cta, variant, accentColor}) => {
  const p = useEntrance(.55);
  const fitted = fitLines(cta, 744, 44, 32, 2);
  const minimal = variant === 'minimal-luxe';
  return <div style={{...area, bottom: 210, ...textStyle, fontSize: fitted.fontSize, textAlign: 'center',
    padding: '24px 40px', opacity: p, transform: `translateY(${18 * (1 - p)}px)`,
    color: minimal ? '#202b2b' : '#fff', background: minimal ? 'transparent' : '#0a1426ed',
    borderRadius: variant === 'step-guide' ? 60 : variant === 'unboxing-reveal' ? 20 : 0,
    borderBottom: `2px solid ${accentColor}`, fontWeight: minimal ? 400 : 700}}>{fitted.text}</div>;
};

export const ProductVariants: React.FC<VariantProps> = (props) => {
  const {fps, durationInFrames} = useVideoConfig();
  const minimal = props.variant === 'minimal-luxe';
  const shade = props.variant === 'step-guide' ? '5,30,28' : props.variant === 'unboxing-reveal' ? '33,21,43' : '7,18,32';
  return <AbsoluteFill style={{fontFamily: 'Arial, sans-serif', backgroundColor: minimal ? '#f8f4ed' : '#071220'}}>
    <Footage {...props} />
    <AbsoluteFill style={{background: minimal
      ? 'linear-gradient(180deg,#f8f4ed 0%,#f8f4ed 20%,transparent 34%,transparent 46%,#f8f4ed 68%)'
      : `linear-gradient(180deg,rgba(${shade},.96),rgba(${shade},.8) 21%,transparent 36%,transparent 45%,rgba(${shade},.96) 70%)`}} />
    {props.title ? <Sequence durationInFrames={Math.min(3 * fps, durationInFrames)}><Title {...props} /></Sequence> : null}
    {props.variant === 'step-guide' && props.cards.length ? <ProgressRail {...props} /> : null}
    {props.variant === 'unboxing-reveal' ? <RevealCorners /> : null}
    {props.cards.map((card, index) => <Sequence key={index} from={Math.round(card.start * fps)}
      durationInFrames={Math.round(card.end * fps) - Math.round(card.start * fps)}>
      <Card text={card.text} index={index} total={props.cards.length} accent={props.accentColor} variant={props.variant} />
    </Sequence>)}
    <Captions captions={props.captions} light={minimal} />
    {props.cta ? <Sequence from={Math.max(0, durationInFrames - 3 * fps)}><Closing {...props} /></Sequence> : null}
  </AbsoluteFill>;
};
