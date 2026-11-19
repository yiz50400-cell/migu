"""Portable local tests. All receipts/reviews are synthetic, never production evidence."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/migu/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


handoff = load('check_handoff')
preflight = load('preflight')
FFMPEG = os.environ.get('MIGU_TEST_FFMPEG') or shutil.which('ffmpeg')


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / 'handoff.json'
        self.data = self.fixture(b'SYNTHETIC MEDIA: unit tests inject an inspector')

    def record(self, name, content):
        p = self.root / name
        p.write_bytes(content)
        return {'path': name, 'sha256': handoff.digest(p)}

    def fixture(self, media):
        asset = self.record('clip.mp4', media)
        asset.update(id='a1', build_id='TEST-BUILD', output_name='TEST-OUTPUT')
        asset['receipt'] = self.record('receipt.txt', b'SYNTHETIC TEST FIXTURE: TEST-BUILD TEST-OUTPUT')
        review = {'media_sha256': asset['sha256'], 'verdict': 'pass',
                  'observed_motion': 'SYNTHETIC TEST FIXTURE', 'method': 'test fixture only',
                  'reviewed_at': '2000-01-01T00:00:00Z'}
        asset['review'] = self.record('review.json', json.dumps(review).encode())
        return {'required_shots': ['s1'], 'assets': [asset],
                'shots': [{'id': 's1', 'asset_id': 'a1', 'in': 0, 'out': 0.8}]}

    def validate(self, data=None):
        self.manifest.write_text(json.dumps(self.data if data is None else data))
        return handoff.validate(self.manifest, inspector=lambda _: 1.0)

    def test_valid_evidence(self):
        self.assertEqual(self.validate()['covered_shots'], 1)

    def test_missing_receipt(self):
        del self.data['assets'][0]['receipt']
        with self.assertRaisesRegex(handoff.Invalid, 'file record'):
            self.validate()

    def test_missing_required_shot(self):
        self.data['required_shots'].append('s2')
        with self.assertRaisesRegex(handoff.Invalid, 'missing required shots'):
            self.validate()

    def test_changed_video(self):
        (self.root / 'clip.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(handoff.Invalid, 'hash mismatch'):
            self.validate()

    def test_stale_review(self):
        asset = self.data['assets'][0]
        review = json.loads((self.root / 'review.json').read_text())
        review['media_sha256'] = 'stale'
        asset['review'] = self.record('review.json', json.dumps(review).encode())
        with self.assertRaisesRegex(handoff.Invalid, 'stale review'):
            self.validate()

    def test_failed_visual_review(self):
        asset = self.data['assets'][0]
        review = json.loads((self.root / 'review.json').read_text())
        review['verdict'] = 'fail'
        asset['review'] = self.record('review.json', json.dumps(review).encode())
        with self.assertRaisesRegex(handoff.Invalid, 'unapproved visual review'):
            self.validate()

    def test_wrong_build_receipt(self):
        self.data['assets'][0]['receipt'] = self.record('receipt.txt', b'WRONG TEST-BUILD-ID AND NO OUTPUT')
        with self.assertRaisesRegex(handoff.Invalid, 'receipt not linked'):
            self.validate()

    def test_invalid_time_ranges(self):
        for start, end in [(0, 2), (-1, .8), (.8, .2), (0, float('nan')), (0, float('inf')), (True, .8)]:
            with self.subTest(start=start, end=end):
                self.data['shots'][0].update({'in': start, 'out': end})
                with self.assertRaises(handoff.Invalid):
                    self.validate()

    def test_duplicate_records(self):
        for field in ['required_shots', 'assets', 'shots']:
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data[field].append(copy.deepcopy(data[field][0]))
                with self.assertRaises(handoff.Invalid):
                    self.validate(data)

    def test_unknown_asset(self):
        self.data['shots'][0]['asset_id'] = 'missing'
        with self.assertRaisesRegex(handoff.Invalid, 'unknown asset'):
            self.validate()

    def test_empty_or_missing_media(self):
        for content in [b'', None]:
            p = self.root / 'clip.mp4'
            if content is None:
                p.unlink()
            else:
                p.write_bytes(content)
            with self.assertRaisesRegex(handoff.Invalid, 'missing or empty'):
                self.validate()

    def test_cli_reports_bad_json_without_traceback(self):
        self.manifest.write_text('{')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'check_handoff.py'), str(self.manifest)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)['status'], 'BLOCKED')


@unittest.skipUnless(FFMPEG, 'Set MIGU_TEST_FFMPEG or install ffmpeg for real media tests')
class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def make_clip(self, extra=()):
        path = self.root / 'clip.mp4'
        subprocess.run([FFMPEG, '-v', 'error', '-nostdin', '-f', 'lavfi', '-i',
                        'testsrc2=size=64x64:rate=10', '-t', '1', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', *extra, str(path)], check=True, capture_output=True, timeout=60)
        return path

    def test_real_motion_decode(self):
        duration = handoff.probe(self.make_clip(), None, FFMPEG)
        self.assertAlmostEqual(duration, 1.0, delta=.11)

    def test_offset_timestamps_normalized(self):
        duration = handoff.probe(self.make_clip(('-output_ts_offset', '5')), None, FFMPEG)
        self.assertAlmostEqual(duration, 1.0, delta=.11)

    def test_fake_mp4_rejected(self):
        path = self.root / 'fake.mp4'
        path.write_bytes(b'This is not a video.')
        with self.assertRaises(handoff.Invalid):
            handoff.probe(path, None, FFMPEG)

    def test_single_frame_rejected(self):
        path = self.root / 'still.png'
        subprocess.run([FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'color=red:size=64x64',
                        '-frames:v', '1', str(path)], check=True, capture_output=True, timeout=60)
        with self.assertRaisesRegex(handoff.Invalid, 'multi-frame'):
            handoff.probe(path, None, FFMPEG)

    def test_truncated_video_rejected(self):
        path = self.make_clip()
        path.write_bytes(path.read_bytes()[:100])
        with self.assertRaises(handoff.Invalid):
            handoff.probe(path, None, FFMPEG)

    def test_looped_image_is_not_a_visual_verdict(self):
        # Technical validation intentionally cannot determine semantic motion.
        path = self.root / 'loop.mp4'
        subprocess.run([FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'color=red:size=64x64:rate=10',
                        '-t', '1', '-c:v', 'libx264', str(path)], check=True, capture_output=True, timeout=60)
        self.assertGreater(handoff.probe(path, None, FFMPEG), 0)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'installation.json'
        self.skills = self.root / 'skills'

    def assess(self, route, config=None, which=lambda _: None):
        if config is not None:
            self.config.write_text(json.dumps(config))
        return preflight.assess(self.config, self.skills, route, which=which)

    def touch(self, root, rel):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('SYNTHETIC TEST FIXTURE')

    def test_analysis_needs_no_production_dependencies(self):
        self.assertEqual(self.assess('analyze')['status'], 'PASS_LOCAL_ONLY')

    def test_missing_generation_dependencies(self):
        result = self.assess('generate')
        self.assertEqual(set(result['missing']), {'hypit CLI', 'hypit skill', 'ffmpeg'})

    def test_generation_dependencies_present(self):
        self.touch(self.skills, 'hypit/SKILL.md')
        self.assertEqual(self.assess('generate', which=lambda _: 'synthetic-launcher')['status'], 'PASS_LOCAL_ONLY')

    def test_configured_hypit_launcher(self):
        self.touch(self.skills, 'hypit/SKILL.md')
        executable=self.root/'hypit'
        executable.write_text('synthetic executable')
        executable.chmod(0o700)
        config={'schema_version':1,'hypit_path':str(executable)}
        result=self.assess('generate',config,which=lambda n:'ffmpeg' if n=='ffmpeg' else None)
        self.assertEqual(result['status'],'PASS_LOCAL_ONLY')
        executable.unlink()
        self.assertIn('hypit CLI',self.assess('generate',which=lambda n:'ffmpeg' if n=='ffmpeg' else None)['missing'])

    def test_bad_config(self):
        for value in [[], {'schema_version': 2}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.assess('generate', value)

    def test_relative_paths_rejected(self):
        for route, key in [('discover', 'collection_root'), ('edit', 'editor_toolkit_root'), ('generate', 'ffmpeg_path')]:
            with self.subTest(route=route), self.assertRaises(ValueError):
                self.assess(route, {'schema_version': 1, key: 'relative/path'})

    def test_full_local_structure(self):
        collector, editor = self.root / 'collector', self.root / 'editor'
        for rel in ['workflow/unattended/evil_discovery.py', 'workflow/collection/collector.py', '.venv/bin/yt-dlp']:
            self.touch(collector, rel)
        for rel in ['scripts/package_remotion.py', 'scripts/deliver_video.py', 'docs/local-editing-workflow.md',
                    'docs/chatcut-remotion-workflow.md', 'remotion/package.json']:
            self.touch(editor, rel)
        for rel in ['hypit/SKILL.md', 'tiktok-product-video-editor/SKILL.md']:
            self.touch(self.skills, rel)
        config = {'schema_version': 1, 'collection_root': str(collector), 'editor_toolkit_root': str(editor)}
        result = self.assess('full', config, which=lambda n: 'synthetic-launcher' if n != 'yt-dlp' else None)
        self.assertEqual(result['status'], 'PASS_LOCAL_ONLY')
        (editor / 'scripts/deliver_video.py').unlink()
        result = self.assess('full', which=lambda _: 'synthetic-launcher')
        self.assertIn('editor toolkit: scripts/deliver_video.py', result['missing'])

    def test_private_unknown_fields_not_echoed(self):
        config = {'schema_version': 1, 'private_field': 'SYNTHETIC-PRIVATE-VALUE'}
        self.assertNotIn('SYNTHETIC-PRIVATE-VALUE', json.dumps(self.assess('analyze', config)))

    def test_cli_bad_config_returns_json(self):
        self.config.write_text('{')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'preflight.py'), '--config', str(self.config)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)['status'], 'INVALID_LOCAL_CONFIGURATION')


if __name__ == '__main__':
    unittest.main()
