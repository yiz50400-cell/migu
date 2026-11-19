"""Plan local shots before ChatCut; bind packaging to that immutable plan.

Checks timing and lineage, not whether a product claim is true or an editor
actually used the planned shots. Those still require real visual review.
"""
from copy import deepcopy
import math
from pathlib import Path
import re
import shutil
import tempfile

from workflow.analysis.core import probe
from workflow.desktop_delivery import digest, local_file
from workflow.packaging_templates import template_info
from workflow.platforms.files import atomic_json
from workflow.store import Asset


def contract(request):
    """Normalize only fields that must agree between plan and packaging."""
    return {**{k: request[k] for k in ('job_id', 'ordinal', 'sources', 'audio_mode',
                                     'delivery_explanation_zh', 'delivery_text_zh')},
            'template_id': request.get('template_id', 'classic'),
            'title': request.get('title', ''), 'cta': request.get('cta', ''),
            'accent_color': request.get('accent_color', '#FFD54A'),
            'cards': request.get('cards', []),
            'srt_sha256': digest(local_file(request['srt_path'], '.srt'))
            if request.get('srt_path') else None}


def plan_storyboard(request, output, data, sessions):
    from workflow.remotion_bridge import captions_from_srt, check_job, fingerprint, text_field
    required = {'schema_version', 'job_id', 'ordinal', 'sources', 'audio_mode', 'shots',
                'delivery_explanation_zh', 'delivery_text_zh'}
    allowed = required | {'template_id', 'srt_path', 'title', 'cta', 'accent_color'}
    if not isinstance(request, dict) or required - set(request) or set(request) - allowed:
        raise ValueError('对应表请求字段缺失或存在未知字段')
    if request['schema_version'] != 1:
        raise ValueError('对应表schema_version须为1')
    if not isinstance(request['job_id'], str) or not re.fullmatch(r'job_[A-Za-z0-9_-]+', request['job_id']):
        raise ValueError('任务ID无效')
    check_job(request, data, sessions)
    template = template_info(request.get('template_id', 'classic'))
    if request['audio_mode'] not in ('silent', 'narration'):
        raise ValueError('音频模式须为silent或narration')
    if request['audio_mode'] == 'narration' and not request.get('srt_path'):
        raise ValueError('口播须提供SRT')
    for name, maximum in [('title', 80), ('cta', 60)]:
        text_field(request.get(name, ''), name, maximum, empty=True)
    for name in ('delivery_explanation_zh', 'delivery_text_zh'):
        if not re.search(r'[\u4e00-\u9fff]', text_field(request[name], name, 5000)):
            raise ValueError('交付说明和文案须包含中文')
    if not re.fullmatch('#[a-fA-F0-9]{6}', str(request.get('accent_color', '#FFD54A'))):
        raise ValueError('accent_color须为六位十六进制颜色')
    shots = deepcopy(request['shots'])
    if not isinstance(shots, list) or not 1 <= len(shots) <= 100:
        raise ValueError('对应表需要1–100个镜头')
    durations = {}
    with sessions() as session:
        for source in request['sources']:
            asset = session.get(Asset, source['asset_id'])
            durations[asset.id] = probe(Path(data).resolve() / 'media' / asset.media_path)['duration_seconds']
    previous = 0
    used = set()
    cards = []
    for shot in shots:
        fields = {'asset_id', 'source_start', 'source_end', 'start', 'end', 'purpose', 'visual', 'message'}
        if not isinstance(shot, dict) or fields - set(shot) or set(shot) - fields - {'card'}:
            raise ValueError('镜头字段无效')
        if not isinstance(shot['asset_id'], str) or shot['asset_id'] not in durations:
            raise ValueError('镜头素材不属于本次任务来源')
        a, b, start, end = [shot[k] for k in ('source_start', 'source_end', 'start', 'end')]
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (a, b, start, end))
                or not 0 <= a < b <= durations[shot['asset_id']]
                or not 0 <= start < end <= 180
                or abs(start - previous) > .001 or abs((b - a) - (end - start)) > .001
                or round(start * 30) >= round(end * 30)):
            raise ValueError('镜头越界、时间轴不连续或不是等速剪辑')
        for key in ('purpose', 'visual', 'message'):
            text_field(shot[key], key, 500)
        if 'card' in shot:
            cards.append({'text': text_field(shot['card'], '卖点卡', 80), 'start': start, 'end': end})
        previous = end
        used.add(shot['asset_id'])
    if used != set(durations) or len(cards) > 20:
        raise ValueError('来源须全部用于对应表且最多20张卖点卡')
    srt = local_file(request['srt_path'], '.srt') if request.get('srt_path') else None
    captions = captions_from_srt(srt, previous) if srt else []
    animations = [{'kind': 'card', **c} for c in cards]
    if request.get('title'):
        animations.append({'kind': 'title', 'text': request['title'], 'start': 0, 'end': min(3, previous)})
    if request.get('cta'):
        animations.append({'kind': 'cta', 'text': request['cta'], 'start': max(0, previous - 3), 'end': previous})
    for shot in shots:
        shot['animations'] = [a for a in animations if a['start'] < shot['end'] and a['end'] > shot['start']]
        shot['captions'] = [c for c in captions if c['startMs'] < shot['end'] * 1000
                            and c['endMs'] > shot['start'] * 1000]
    draft = {k: deepcopy(v) for k, v in request.items() if k != 'shots'}
    draft.update(cards=cards, base_subtitles_burned_in=False)
    record = {'schema_version': 1, 'status': 'PLANNED_PENDING_CHATCUT', 'template': template,
              'duration': previous, 'shots': shots, 'contract': contract(draft)}
    record['fingerprint'] = fingerprint(record)
    output = Path(output).resolve()
    draft['storyboard_path'] = str(output / 'storyboard.json')
    # Rendering/approval IDs deliberately have no placeholders in this draft.
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', '<br>')
    lines = [f'# {template["name"]} · 镜头对应表', '',
             '计划待 ChatCut 执行；画面/商品事实须人工核实。本表不证明底片符合计划。', '',
             '| 成片秒 | 素材 / 源秒 | 用途 / 画面观察 | 文案要点 | 字幕（原cue时间） | 动画 |',
             '|---|---|---|---|---|---|']
    for shot in shots:
        cues = '; '.join(f'{c["startMs"] / 1000:g}–{c["endMs"] / 1000:g}: {c["text"]}'
                         for c in shot['captions'])
        values = [f'{shot["start"]:g}–{shot["end"]:g}',
                  f'{shot["asset_id"]} / {shot["source_start"]:g}–{shot["source_end"]:g}',
                  f'{shot["purpose"]} / {shot["visual"]}', shot['message'], cues,
                  '; '.join(f'{template["id"]}/{a["kind"]} {a["start"]:g}–{a["end"]:g}: {a["text"]}'
                            for a in shot['animations']) or '无包装动画']
        lines.append('| ' + ' | '.join(map(cell, values)) + ' |')
    markdown = '\n'.join(lines) + '\n'
    if output.exists():
        from workflow.remotion_bridge import load
        if (load(output / 'storyboard.json') != record
                or load(output / 'package-request.draft.json') != draft
                or (output / 'storyboard.md').read_text(encoding='utf-8') != markdown):
            raise ValueError('对应表目录已存在或已变化，请使用新目录')
        return record
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.storyboard-', dir=output.parent))
    try:
        atomic_json(temporary / 'storyboard.json', record)
        atomic_json(temporary / 'package-request.draft.json', draft)
        (temporary / 'storyboard.md').write_text(markdown, encoding='utf-8')
        check_job(request, data, sessions)
        if contract(draft) != record['contract']:
            raise ValueError('对应表输入在准备期间变化')
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return record


def validate_storyboard_binding(path, request, duration):
    from workflow.remotion_bridge import fingerprint, load
    record = load(local_file(str(path), '.json'))
    if (not isinstance(record, dict) or record.get('schema_version') != 1
            or record.get('fingerprint') != fingerprint({k: v for k, v in record.items() if k != 'fingerprint'})
            or record.get('contract') != contract(request)
            or record.get('template') != template_info(request.get('template_id', 'classic'))
            or type(record.get('duration')) not in (int, float)
            or not math.isfinite(record['duration']) or abs(record['duration'] - duration) > 1 / 30):
        raise ValueError('对应表已变化或与模板、字幕、文案、素材、底片时长不匹配')
    return record
