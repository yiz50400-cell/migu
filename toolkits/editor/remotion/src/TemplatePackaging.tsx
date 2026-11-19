import {ProductPackaging, type ProductProps} from './Composition';
import {KineticProduct} from './KineticProduct';
import {ProductVariants} from './ProductVariants';
import catalog from '../templates.json';

export const TemplatePackaging: React.FC<ProductProps> = (props) => {
  const id = props.templateId ?? 'classic';
  if (!catalog.templates.some((t) => t.id === id)) throw new Error(`Unknown template: ${id}`);
  if (id === 'kinetic-product') return <KineticProduct {...props} />;
  if (id === 'classic') return <ProductPackaging {...props} />;
  if (id === 'comparison-review' || id === 'step-guide' || id === 'unboxing-reveal' || id === 'minimal-luxe') {
    return <ProductVariants {...props} variant={id} />;
  }
  throw new Error(`Template renderer not implemented: ${id}`);
};
