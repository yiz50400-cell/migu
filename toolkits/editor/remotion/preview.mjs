// Local synthetic previews through the production composition; never a delivery.
import {mkdir, readFile, rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderStill, renderMedia, selectComposition} from '@remotion/renderer';

const root = path.dirname(fileURLToPath(import.meta.url));
const {templates} = JSON.parse(await readFile(path.join(root, 'templates.json'), 'utf8'));
const args = process.argv.slice(2);
const destination = path.resolve(args.find((arg) => !arg.startsWith('--')) ?? path.join(root, 'previews'));
const videos = args.includes('--videos');
const bundleDir = path.join(os.tmpdir(), `product-preview-${process.pid}`);
await mkdir(destination, {recursive: true});
try {
  const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts'), outDir: bundleDir});
  const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE || null;
  for (const template of templates) {
    const inputProps = {templateId: template.id, previewDemo: true, video: 'base.mp4',
      durationInFrames: 150, fps: 30, audioMode: 'silent', title: 'Detalles que importan',
      cta: 'Descubre cada detalle', accentColor: '#FFD54A',
      cards: [{text: 'Muestra el uso real', start: 0, end: 2},
        {text: 'Cada detalle cuenta', start: 2, end: 5}],
      captions: [{text: 'Vista de ejemplo · material sintético', startMs: 0, endMs: 5000,
        timestampMs: null, confidence: null}]};
    const composition = await selectComposition({serveUrl, id: 'ProductPackaging', inputProps, browserExecutable});
    await renderStill({serveUrl, composition, inputProps, browserExecutable,
      frame: 75, output: path.join(destination, `${template.id}.png`), imageFormat: 'png'});
    if (videos) {
      await renderMedia({serveUrl, composition, inputProps, browserExecutable,
        codec: 'h264', pixelFormat: 'yuv420p', colorSpace: 'bt709', imageFormat: 'png',
        muted: true, concurrency: 2, crf: 18, overwrite: false,
        outputLocation: path.join(destination, `${template.id}.mp4`)});
    }
    console.log(`Preview: ${template.id}`);
  }
} finally {
  await rm(bundleDir, {recursive: true, force: true});
}
