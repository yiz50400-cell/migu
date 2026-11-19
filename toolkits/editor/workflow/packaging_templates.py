"""The local template catalogue shared with Remotion."""
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / 'remotion/templates.json'


def list_templates():
    return json.loads(CATALOG.read_text(encoding='utf-8'))['templates']


def template_info(template_id='classic'):
    for template in list_templates():
        if template['id'] == template_id:
            return template
    raise ValueError(f'未知包装模板：{template_id}')
