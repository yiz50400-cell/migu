#!/usr/bin/env python3
"""Remake-plan and delivery acceptance checks. Generation success is not completion."""
from __future__ import annotations

import hashlib
from pathlib import Path

USUAL_MAX_SHOTS = 6
HARD_MAX_SHOTS = 20
ACCEPTANCE_ITEMS = (
    ('cuts', '实际切镜'),
    ('continuity', '穿帮'),
    ('target_language', '对应国家语言'),
    ('packaging_text', '视频包装与需复刻的画面文字'),
    ('subtitles', '字幕'),
    ('export', '最终导出'),
)


class PlanError(ValueError):
    pass


def finite_number(value, name):
    if type(value) not in (float, int) or value != value or abs(value) == float('inf'):
        raise PlanError(name + ' must be a finite number')
    return float(value)


def check_shot_count(required, allow_more=False):
    if not isinstance(required, list) or not required:
        raise PlanError('required_shots must be nonempty')
    if not all(isinstance(x, str) and x.strip() for x in required):
        raise PlanError('invalid required shot id')
    if len(set(required)) != len(required):
        raise PlanError('duplicate required shot id')
    count = len(required)
    if count >= HARD_MAX_SHOTS:
        raise PlanError('too many real shots (%s); avoid twenty or more, usual max is %s' % (count, USUAL_MAX_SHOTS))
    if count > USUAL_MAX_SHOTS and not allow_more:
        raise PlanError('usual remake uses at most %s real shots, got %s' % (USUAL_MAX_SHOTS, count))
    return count


def check_duration_fields(shot, media_duration=None):
    if not isinstance(shot, dict):
        raise PlanError('invalid shot record')
    requested = finite_number(shot.get('requested_duration'), 'requested_duration')
    start = finite_number(shot.get('in'), 'usable range in')
    end = finite_number(shot.get('out'), 'usable range out')
    output = finite_number(shot.get('output_duration'), 'output_duration')
    if requested <= 0:
        raise PlanError('requested_duration must be set from the shot action and be positive')
    if not (0 <= start < end):
        raise PlanError('usable range must satisfy 0 <= in < out')
    if media_duration is not None and end > media_duration + 0.05:
        raise PlanError('unusable time range: out exceeds media duration')
    if output <= 0 or output > (end - start) + 0.05:
        raise PlanError('output_duration must be positive and within the usable range')
    return {
        'requested_duration': requested,
        'usable_in': start,
        'usable_out': end,
        'output_duration': output,
    }


def check_acceptance(acceptance):
    if not isinstance(acceptance, dict):
        raise PlanError('delivery acceptance must be an object')
    if acceptance.get('verdict') != 'pass':
        raise PlanError('delivery acceptance is not pass; generation success is not completion')
    for key, label in ACCEPTANCE_ITEMS:
        item = acceptance.get(key)
        if not isinstance(item, dict) or item.get('checked') is not True:
            raise PlanError('delivery acceptance missing checked item: ' + label)
        notes = item.get('notes')
        if notes is not None and (not isinstance(notes, str) or not notes.strip()):
            raise PlanError('acceptance notes for %s must be text' % label)
    if acceptance.get('generation_success_is_complete') is True:
        raise PlanError('generation success is not completion')
    return True


SCENE_REFERENCE_SOURCES = ('image2.5flare', 'accepted_still')
IDENTITY_ROLES = frozenset({
    'actor', 'person', 'face', 'product', 'pack', 'identity',
    'talent', 'sku', 'actor_identity', 'product_pack',
})


def _ref_record(value, name):
    if isinstance(value, str) and value.strip():
        return {'path': value.strip()}
    if not isinstance(value, dict):
        raise PlanError(name + ' must be an object or path')
    path = value.get('path')
    if not isinstance(path, str) or not path.strip():
        raise PlanError(name + ' missing path')
    return value


def _normalized_path(path, root=None):
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and root is not None:
        candidate = Path(root) / candidate
    if candidate.is_absolute() or root is not None:
        return str(candidate.resolve())
    return str(Path(path))


def _file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_reference_file(record, root, name='reference'):
    record = _ref_record(record, name)
    path = Path(record['path']).expanduser()
    if not path.is_absolute():
        if root is None:
            raise PlanError(name + ' needs a project root to resolve a relative path')
        path = Path(root) / path
    if not path.is_file() or path.stat().st_size == 0:
        raise PlanError('missing or empty file: ' + path.name)
    digest = _file_digest(path)
    expected = record.get('sha256')
    if not isinstance(expected, str) or not expected.strip():
        raise PlanError(name + ' missing sha256')
    if digest != expected:
        raise PlanError('hash mismatch: ' + path.name)
    return path, digest


def _identity_keys(record, root=None):
    record = _ref_record(record, 'identity reference')
    keys = set()
    keys.add(('path', _normalized_path(record['path'], root)))
    sha = record.get('sha256')
    if isinstance(sha, str) and sha.strip():
        keys.add(('sha256', sha.strip()))
    return keys


def _is_identity_role(record):
    role = record.get('role') if isinstance(record, dict) else None
    if not isinstance(role, str):
        return False
    return role.strip().lower() in IDENTITY_ROLES


def collect_shared_identity_keys(shared_identity_references, shots, root=None):
    keys = set()
    if shared_identity_references is not None:
        if not isinstance(shared_identity_references, list):
            raise PlanError('shared_identity_references must be an array')
        for item in shared_identity_references:
            keys.update(_identity_keys(item, root))
    if not isinstance(shots, list):
        return keys
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        extra = shot.get('identity_references')
        if extra is None:
            continue
        if not isinstance(extra, list):
            sid = shot.get('id') or 'shot'
            raise PlanError(str(sid) + ': identity_references must be an array')
        for item in extra:
            keys.update(_identity_keys(item, root))
    return keys


def _listed_video_references(shot):
    collected = []
    for key in ('video_references', 'references'):
        value = shot.get(key)
        if value is None:
            continue
        if isinstance(value, dict) and value.get('primary') is not None:
            collected.append((key + '.primary', value.get('primary')))
            additional = value.get('additional') or value.get('identity') or []
            if additional and not isinstance(additional, list):
                raise PlanError((shot.get('id') or 'shot') + ': ' + key + ' additional refs must be an array')
            for index, item in enumerate(additional):
                collected.append((key + '.additional[%s]' % index, item))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collected.append((key + '[%s]' % index, item))
        else:
            raise PlanError((shot.get('id') or 'shot') + ': ' + key + ' must be an array or an object with primary')
    return collected


def _explicit_primary(shot):
    for key in ('primary_reference', 'video_primary_reference', 'first_frame_reference'):
        if shot.get(key) is not None:
            return key, shot.get(key)
    for key in ('video_references', 'references'):
        value = shot.get(key)
        if isinstance(value, dict) and value.get('primary') is not None:
            return key + '.primary', value.get('primary')
        if isinstance(value, list) and value:
            return key + '[0]', value[0]
    return None, None


def _same_reference(left, right, root=None):
    left = _ref_record(left, 'reference')
    right = _ref_record(right, 'reference')
    if _normalized_path(left['path'], root) == _normalized_path(right['path'], root):
        return True
    left_sha = left.get('sha256')
    right_sha = right.get('sha256')
    return (
        isinstance(left_sha, str) and left_sha.strip()
        and isinstance(right_sha, str) and right_sha.strip()
        and left_sha.strip() == right_sha.strip()
    )


def _overlaps_identity(record, identity_keys, root=None):
    record = _ref_record(record, 'reference')
    path_key = ('path', _normalized_path(record['path'], root))
    if path_key in identity_keys:
        return True
    sha = record.get('sha256')
    if isinstance(sha, str) and sha.strip() and ('sha256', sha.strip()) in identity_keys:
        return True
    return _is_identity_role(record) and record.get('source') not in SCENE_REFERENCE_SOURCES


def _verify_identity_files(shared_identity_references, shots, root, identity_keys):
    if shared_identity_references:
        for index, item in enumerate(shared_identity_references):
            path, digest = verify_reference_file(item, root, 'shared_identity_references[%s]' % index)
            identity_keys.add(('path', str(path.resolve())))
            identity_keys.add(('sha256', digest))
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        extra = shot.get('identity_references') or []
        if not extra:
            continue
        if not isinstance(extra, list):
            sid = shot.get('id') or 'shot'
            raise PlanError(str(sid) + ': identity_references must be an array')
        sid = shot.get('id') or 'shot'
        for index, item in enumerate(extra):
            path, digest = verify_reference_file(item, root, str(sid) + ' identity_references[%s]' % index)
            identity_keys.add(('path', str(path.resolve())))
            identity_keys.add(('sha256', digest))


def check_scene_references(shots, shared_identity_references=None, root=None, require_files=False):
    if not isinstance(shots, list) or not shots:
        raise PlanError('shots must be a nonempty array')
    identity_keys = collect_shared_identity_keys(shared_identity_references, shots, root)
    if require_files:
        _verify_identity_files(shared_identity_references, shots, root, identity_keys)
    for shot in shots:
        if not isinstance(shot, dict):
            raise PlanError('invalid shot record')
        sid = shot.get('id')
        if not isinstance(sid, str) or not sid.strip():
            sid = 'shot'
        scene = shot.get('scene_reference')
        if scene is None:
            raise PlanError(
                sid + ': missing scene reference still; shared actor/product images cannot replace a per-shot scene still'
            )
        scene = _ref_record(scene, sid + ' scene_reference')
        source = scene.get('source')
        if source not in SCENE_REFERENCE_SOURCES:
            raise PlanError(
                sid + ': scene_reference source must be image2.5flare or an accepted_still of matching composition'
            )
        if require_files:
            path, digest = verify_reference_file(scene, root, sid + ' scene_reference')
            scene = dict(scene)
            scene['sha256'] = digest
            scene['path'] = str(path)
        if _overlaps_identity(scene, identity_keys, root):
            raise PlanError(
                sid + ': scene_reference is a shared actor/product image; it cannot replace a shot-matched scene still'
            )
        primary_name, primary = _explicit_primary(shot)
        if primary is not None:
            primary = _ref_record(primary, sid + ' ' + primary_name)
            if not _same_reference(primary, scene, root) or _overlaps_identity(primary, identity_keys, root):
                raise PlanError(
                    sid + ': video primary/first-frame reference must be the shot scene still, not an identity or product image'
                )
        listed = _listed_video_references(shot)
        if listed:
            if not any(_same_reference(item, scene, root) for _, item in listed):
                raise PlanError(
                    sid + ': video references do not include the shot scene still; shared actor/product images cannot be the main reference'
                )
            first_name, first = listed[0]
            if first_name.endswith('[0]') or first_name.endswith('.primary'):
                if not _same_reference(first, scene, root):
                    raise PlanError(
                        sid + ': video primary/first-frame reference must be the shot scene still, not an identity or product image'
                    )
    return True
