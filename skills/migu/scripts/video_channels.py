#!/usr/bin/env python3
"""Video channel registry and failover. Never stores secrets or submits paid jobs."""
from __future__ import annotations

ALLOWED_KINDS = ('api', 'hypit')
IMAGE_MODEL = 'image2.5flare'


class ChannelError(ValueError):
    pass


class NoAvailableChannel(ChannelError):
    pass


def configured_image_model(config=None):
    """Images always use the configured API's image2.5flare model."""
    config = config or {}
    declared = config.get('image_model')
    if declared not in (None, '', IMAGE_MODEL):
        raise ChannelError('image model is fixed to %s, not %s' % (IMAGE_MODEL, declared))
    return IMAGE_MODEL


def credential_present(record):
    """Report only whether a credential exists, never its value."""
    if not isinstance(record, dict):
        return False
    if 'credential_present' in record:
        return bool(record.get('credential_present'))
    length = record.get('credential_length')
    return isinstance(length, int) and length > 0


def _clean_channel(raw, index):
    if not isinstance(raw, dict):
        raise ChannelError('video_channels[%s] must be an object' % index)
    ident = raw.get('id')
    kind = raw.get('kind')
    if not isinstance(ident, str) or not ident.strip():
        raise ChannelError('video_channels[%s] needs a non-empty id' % index)
    if kind not in ALLOWED_KINDS:
        raise ChannelError('video_channels[%s] kind must be api or hypit' % ident)
    enabled = raw.get('enabled', True)
    if enabled not in (True, False):
        raise ChannelError('video_channels[%s] enabled must be a boolean' % ident)
    label = raw.get('label') or ident
    if not isinstance(label, str) or not label.strip():
        raise ChannelError('video_channels[%s] label must be a string' % ident)
    account_ref = raw.get('account_ref')
    if account_ref is not None and (not isinstance(account_ref, str) or not account_ref.strip()):
        raise ChannelError('video_channels[%s] account_ref must be a name, not a secret' % ident)
    channel = {
        'id': ident.strip(),
        'kind': kind,
        'label': label.strip(),
        'enabled': bool(enabled),
        'account_ref': account_ref.strip() if isinstance(account_ref, str) else None,
        'endpoint_name': _optional_name(raw.get('endpoint_name'), ident, 'endpoint_name'),
        'hypit_path': _optional_name(raw.get('hypit_path'), ident, 'hypit_path'),
        'credential_present': credential_present(raw),
    }
    if kind == 'api' and not channel['endpoint_name']:
        raise ChannelError('api channel %s needs endpoint_name' % ident)
    return channel


def _optional_name(value, ident, field):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not value.strip():
        raise ChannelError('video_channels[%s] %s must be a name or path, not a secret' % (ident, field))
    return value.strip()


def load_channels(config):
    config = config or {}
    raw = config.get('video_channels')
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ChannelError('video_channels must be an array')
    channels = []
    seen = set()
    for index, item in enumerate(raw):
        channel = _clean_channel(item, index)
        if channel['id'] in seen:
            raise ChannelError('duplicate video channel id: ' + channel['id'])
        seen.add(channel['id'])
        channels.append(channel)
    return channels


def has_api_video_route(config):
    return any(channel['kind'] == 'api' and channel['enabled'] for channel in load_channels(config))


def has_hypit_channel(config):
    return any(channel['kind'] == 'hypit' and channel['enabled'] for channel in load_channels(config))


def video_route_requires_hypit(config):
    """API video routes do not depend on Hypit Runtime. Legacy installs still may."""
    channels = load_channels(config)
    if not channels:
        return True
    return not has_api_video_route(config)


def available_channels(channels, unavailable=None, health=None):
    unavailable = set(unavailable or ())
    ready = []
    for channel in channels:
        if not channel['enabled'] or channel['id'] in unavailable:
            continue
        if health is not None and not health(channel):
            continue
        ready.append(channel)
    return ready


def select_channel(channels, *, preferred=None, unavailable=None, health=None):
    """Pick a usable channel, failing over when one is unavailable."""
    ready = available_channels(channels, unavailable=unavailable, health=health)
    if preferred:
        for channel in ready:
            if channel['id'] == preferred:
                return channel
    if not ready:
        raise NoAvailableChannel('no video channel is currently available; configure or switch accounts')
    return ready[0]


def next_channel(channels, current_id, *, unavailable=None, health=None):
    blocked = set(unavailable or ())
    if current_id:
        blocked.add(current_id)
    return select_channel(channels, unavailable=blocked, health=health)
