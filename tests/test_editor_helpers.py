"""Smoke checks for the companion skill's standalone helpers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/tiktok-product-video-editor/scripts'


class EditorHelperTests(unittest.TestCase):
    def test_all_helpers_start(self):
        for name in ('probe_video_materials.py', 'prepare_video_assets.py', 'make_video_run_manifest.py'):
            with self.subTest(name=name):
                result = subprocess.run([sys.executable, str(SCRIPTS / name), '--help'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_binds_source_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script, clip, output = root / 'script.txt', root / 'clip.mp4', root / 'manifest.json'
            script.write_text('Synthetic copy', encoding='utf-8')
            # This helper hashes arbitrary bytes; media decoding is tested separately.
            clip.write_bytes(b'SYNTHETIC CONTENT FOR HASH TEST')
            command = [sys.executable, str(SCRIPTS / 'make_video_run_manifest.py'), '--market', 'TEST',
                       '--script-file', str(script), '--clip', str(clip), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            first = json.loads(output.read_text())
            self.assertEqual(first['clips'][0]['sha256'], hashlib.sha256(clip.read_bytes()).hexdigest())
            self.assertEqual(first['script_sha256'], hashlib.sha256(script.read_bytes()).hexdigest())
            clip.write_bytes(b'CHANGED SYNTHETIC CONTENT')
            subprocess.run(command, check=True, capture_output=True, text=True)
            second = json.loads(output.read_text())
            self.assertNotEqual(first['render_cache_key'], second['render_cache_key'])
            self.assertEqual(first['tts_cache_key'], second['tts_cache_key'])


if __name__ == '__main__':
    unittest.main()
