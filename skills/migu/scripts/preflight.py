#!/usr/bin/env python3
"""Read-only local dependency checks. Never authenticates or submits jobs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROUTES = ('analyze', 'generate', 'discover', 'edit', 'full')


def assess(config_path, skills_dir, route, which=shutil.which):
    if route not in ROUTES:
        raise ValueError('unknown route')
    config = {}
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if not isinstance(config, dict):
            raise ValueError('local configuration must be an object')
        if config.get('schema_version') != 1:
            raise ValueError('local configuration requires schema_version 1')
    checks = []
    def add(name, ok):
        checks.append({'name': name, 'present': bool(ok)})
    def folder(key):
        value = config.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(key + ' must be an absolute directory path or null')
        p = Path(value).expanduser()
        if not p.is_absolute():
            raise ValueError(key + ' must be an absolute directory path or null')
        return p
    if route in ('generate', 'full'):
        add('hypit CLI', which('hypit'))
        add('hypit skill', (skills_dir/'hypit/SKILL.md').is_file())
    if route in ('discover', 'full'):
        p = folder('collection_root')
        add('collection discovery adapter', p and (p/'workflow/unattended/evil_discovery.py').is_file())
        add('collection downloader adapter', p and (p/'workflow/collection/collector.py').is_file())
        # yt-dlp may be in the collection project's venv; imports are checked at runtime.
        add('yt-dlp launcher', which('yt-dlp') or (p and any((p/q).is_file() for q in ('.venv/bin/yt-dlp', '.venv/Scripts/yt-dlp.exe'))))
    if route in ('edit', 'full'):
        p = folder('editor_toolkit_root')
        add('editor skill', (skills_dir/'tiktok-product-video-editor/SKILL.md').is_file())
        for rel in ('scripts/package_remotion.py', 'scripts/deliver_video.py', 'docs/local-editing-workflow.md', 'docs/chatcut-remotion-workflow.md', 'remotion/package.json'):
            add('editor toolkit: ' + rel, p and (p/rel).is_file())
    if route != 'analyze':
        value = config.get('ffmpeg_path')
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError('ffmpeg_path must be an absolute executable path or null')
        exe = Path(value).expanduser() if value else None
        if exe and not exe.is_absolute():
            raise ValueError('ffmpeg_path must be absolute')
        add('ffmpeg', (exe.is_file() and os.access(exe, os.X_OK)) if exe else which('ffmpeg'))
    missing = [x['name'] for x in checks if not x['present']]
    return {'status': 'MISSING_LOCAL_DEPENDENCIES' if missing else 'PASS_LOCAL_ONLY', 'route': route,
            'checks': checks, 'missing': missing,
            'limit': 'Files and launchers only. Does not verify accounts, services, models, MCP connectivity, or generation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--route', choices=ROUTES, default='generate')
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1]/'installation.json')
    parser.add_argument('--skills-dir', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))/'skills')
    args = parser.parse_args()
    try:
        result = assess(args.config.expanduser(), args.skills_dir.expanduser(), args.route)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'PASS_LOCAL_ONLY' else 1
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'INVALID_LOCAL_CONFIGURATION', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
