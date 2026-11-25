#!/usr/bin/env python3
"""Remake-plan and delivery acceptance checks. Generation success is not completion."""
from __future__ import annotations

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
