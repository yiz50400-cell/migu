import {Composition} from 'remotion';
import {type ProductProps} from './Composition';
import {TemplatePackaging} from './TemplatePackaging';

const defaults: ProductProps = {
  video: 'base.mp4', durationInFrames: 150, fps: 30, audioMode: 'silent',
  title: '', cta: '', accentColor: '#FFD54A', captions: [], cards: [],
};

export const RemotionRoot: React.FC = () => <Composition
  id="ProductPackaging" component={TemplatePackaging} width={1080} height={1920}
  fps={30} durationInFrames={150} defaultProps={defaults}
  calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames, fps: props.fps})}
/>;
