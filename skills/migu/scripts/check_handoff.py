#!/usr/bin/env python3
"""Validate local generation handoff evidence; does not certify visual truth."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from acceptance import check_acceptance, check_duration_fields, check_scene_references, check_shot_count


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verified_file(record, root):
    require(isinstance(record, dict), 'file record must be an object')
    name = record.get('path')
    require(isinstance(name, str) and name.strip(), 'missing local file path')
    path = Path(name).expanduser()
    if not path.is_absolute():
        path = root / path
    require(path.is_file() and path.stat().st_size > 0, f'missing or empty file: {path.name}')
    require(digest(path) == record.get('sha256'), f'hash mismatch: {path.name}')
    return path


def number(value):
    require(type(value) in (float, int) and math.isfinite(value), 'time must be a finite number')
    return float(value)


def run(command, timeout):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0, 'media tool failed: ' + result.stderr[-500:])
    return result.stdout


def probe(path, ffprobe, ffmpeg):
    duration = None
    if ffprobe:
        data = json.loads(run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], 60))
        streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')]
        require(bool(streams), f'no video stream: {path.name}')
        stream = streams[0]
        require(stream.get('width', 0) > 0 and stream.get('height', 0) > 0, 'invalid video dimensions')
        duration = float(stream.get('duration') or data.get('format', {}).get('duration') or 0)
        require(math.isfinite(duration) and duration > 0, 'invalid video duration')
    # Decode the whole file and count decoded frames, rather than trusting an extension.
    progress = run([ffmpeg, '-v', 'error', '-xerror', '-nostdin', '-i', str(path), '-map', '0:V:0', '-vf', 'setpts=PTS-STARTPTS', '-an', '-progress', 'pipe:1', '-f', 'null', '-'], 600)
    frames = [int(line.split('=', 1)[1]) for line in progress.splitlines() if line.startswith('frame=')]
    require(frames and max(frames) > 1, 'not a multi-frame decoded video')
    if duration is None:
        times = [int(line.split('=', 1)[1]) for line in progress.splitlines() if line.startswith('out_time_us=') and line.split('=', 1)[1].lstrip('-').isdigit()]
        require(times and max(times) > 0, 'missing decoded media duration')
        duration = max(times) / 1000000
    return duration


def validate(manifest_path, ffprobe=None, ffmpeg='ffmpeg', inspector=None):
    root = manifest_path.resolve().parent
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(isinstance(data, dict), 'manifest must be an object')
    required = data.get('required_shots')
    allow_more = data.get('allow_more_than_usual_shots') is True
    if allow_more:
        reason = data.get('allow_more_than_usual_shots_reason')
        require(isinstance(reason, str) and reason.strip(), 'allow_more_than_usual_shots needs a reason')
    try:
        check_shot_count(required, allow_more=allow_more)
    except ValueError as exc:
        raise Invalid(str(exc)) from exc
    assets = data.get('assets')
    require(isinstance(assets, list) and assets, 'no generated assets')
    durations = {}
    inspect_media = inspector or (lambda path: probe(path, ffprobe, ffmpeg))
    for asset in assets:
        require(isinstance(asset, dict), 'invalid asset record')
        ident = asset.get('id')
        require(isinstance(ident, str) and ident.strip() and ident not in durations, 'invalid/duplicate asset id')
        path = verified_file(asset, root)
        for key in ('build_id', 'output_name'):
            require(isinstance(asset.get(key), str) and asset[key].strip(), f'missing {key}: {ident}')
        receipt = verified_file(asset.get('receipt'), root).read_text(encoding='utf-8')
        require(asset['build_id'] in receipt and asset['output_name'] in receipt, f'receipt not linked to build/output: {ident}')
        review_path = verified_file(asset.get('review'), root)
        review = json.loads(review_path.read_text(encoding='utf-8'))
        require(isinstance(review, dict), 'invalid review')
        require(review.get('media_sha256') == asset['sha256'], f'stale review: {ident}')
        require(review.get('verdict') == 'pass', f'unapproved visual review: {ident}')
        for key in ('observed_motion', 'method', 'reviewed_at'):
            require(isinstance(review.get(key), str) and review[key].strip(), f'missing review {key}: {ident}')
        durations[ident] = number(inspect_media(path))
        require(durations[ident] > 0, 'nonpositive media duration')
    shots = data.get('shots')
    require(isinstance(shots, list), 'shots must be an array')
    try:
        check_scene_references(
            shots,
            data.get('shared_identity_references'),
            root=root,
            require_files=True,
        )
    except ValueError as exc:
        raise Invalid(str(exc)) from exc
    covered = set()
    for shot in shots:
        require(isinstance(shot, dict), 'invalid shot record')
        sid, aid = shot.get('id'), shot.get('asset_id')
        require(isinstance(sid, str) and sid in required and sid not in covered, 'unknown/duplicate shot id')
        require(isinstance(aid, str) and aid in durations, f'unknown asset: {sid}')
        try:
            durations_fields = check_duration_fields(shot, durations[aid])
        except ValueError as exc:
            raise Invalid(f'{sid}: {exc}') from exc
        start, end = durations_fields['usable_in'], durations_fields['usable_out']
        require(0 <= start < end <= durations[aid] + 0.05, f'unusable time range: {sid}')
        covered.add(sid)
    require(covered == set(required), 'missing required shots: ' + ', '.join(sorted(set(required)-covered)))
    delivery = data.get('delivery')
    if delivery is not None:
        require(isinstance(delivery, dict), 'delivery must be an object')
        verified_file(delivery, root)
        delivery_duration = number(delivery.get('duration'))
        require(delivery_duration > 0, 'delivery duration must be a positive 成片时长')
        try:
            check_acceptance(delivery.get('acceptance'))
        except ValueError as exc:
            raise Invalid(str(exc)) from exc
    return {'status': 'TECHNICAL_EVIDENCE_VALID', 'assets': len(assets), 'covered_shots': len(covered),
            'usual_shot_limit': 6, 'delivery_reviewed': delivery is not None,
            'limit': 'Does not independently authenticate generation receipts or verify visual review claims. Generation success is not completion.'}



def validate_ready_for_video(manifest_path):
    """Block video submit when a shot has only shared identity/product images."""
    root = manifest_path.resolve().parent
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(isinstance(data, dict), 'manifest must be an object')
    required = data.get('required_shots')
    allow_more = data.get('allow_more_than_usual_shots') is True
    if allow_more:
        reason = data.get('allow_more_than_usual_shots_reason')
        require(isinstance(reason, str) and reason.strip(), 'allow_more_than_usual_shots needs a reason')
    try:
        check_shot_count(required, allow_more=allow_more)
    except ValueError as exc:
        raise Invalid(str(exc)) from exc
    shots = data.get('shots')
    require(isinstance(shots, list), 'shots must be an array')
    covered = set()
    for shot in shots:
        require(isinstance(shot, dict), 'invalid shot record')
        sid = shot.get('id')
        require(isinstance(sid, str) and sid in required and sid not in covered, 'unknown/duplicate shot id')
        covered.add(sid)
    require(covered == set(required), 'missing required shots: ' + ', '.join(sorted(set(required) - covered)))
    try:
        check_scene_references(
            shots,
            data.get('shared_identity_references'),
            root=root,
            require_files=True,
        )
    except ValueError as exc:
        raise Invalid(str(exc)) from exc
    return {
        'status': 'READY_FOR_VIDEO_SUBMIT',
        'covered_shots': len(covered),
        'limit': 'Does not submit generation. Shared actor/product images cannot replace a per-shot scene still.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--ready-for-video', action='store_true',
                        help='Check per-shot scene stills before video submit; does not submit generation')
    parser.add_argument('--ffprobe', help='Optional ffprobe binary for additional stream metadata checks')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    try:
        if args.ready_for_video:
            result = validate_ready_for_video(args.manifest)
        else:
            result = validate(args.manifest, args.ffprobe, args.ffmpeg)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
