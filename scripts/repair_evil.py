#!/usr/bin/env python3
"""Provision the local Evil dependency using its supported CLI and authenticated API.

No credentials are printed. Existing users/keys are never reset or replaced.
Default is read-only; --apply permits first-instance provisioning and one guest mint.
Protocol source: Evil commit 3c045e11aecd58ab076562f1246931b9dd5d909b.
"""
import argparse
import http.cookiejar
import json
import re
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request


class RepairError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RepairError('Local service redirected; no credentials forwarded.')


class Client:
    def __init__(self, base):
        parts = urllib.parse.urlsplit(base)
        if (parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parts.username or parts.password or parts.path not in ('', '/')
                or parts.query or parts.fragment):
            raise RepairError('Automatic provisioning supports only a loopback HTTP endpoint.')
        self.base = base.rstrip('/')
        self.port = parts.port or 80
        self.key_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, data=None, key=None, *, envelope=False, timeout=30):
        headers = {'Accept': 'application/json'}
        if key:
            headers['X-API-Key'] = key
        body = None
        if data is not None:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(self.base+path, data=body, headers=headers)
        try:
            with (self.key_opener if key else self.opener).open(request, timeout=timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            code = ''
            try:
                detail = json.loads(error.read(65536)).get('error', {})
                candidate = detail.get('code', '') if isinstance(detail, dict) else ''
                if isinstance(candidate, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{1,63}', candidate):
                    code = ' / '+candidate
            except (OSError, ValueError, AttributeError):
                pass
            raise RepairError(f'Evil {path}: HTTP {error.code}{code}; response body withheld.') from None
        except (OSError, ValueError) as error:
            raise RepairError(f'Evil {path}: {type(error).__name__}; no secrets logged.') from None
        if not isinstance(payload, dict) or payload.get('success') is False:
            raise RepairError(f'Evil {path}: unexpected response; body withheld.')
        return payload if envelope else payload.get('data', payload)


def quiet_run(args, *, input=None, timeout=60, env=None):
    """Capture even failure output: upstream logs may include setup URLs or secrets."""
    try:
        result = subprocess.run([str(x) for x in args], input=input, capture_output=True,
                                text=True, encoding='utf-8', errors='replace',
                                timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError) as error:
        raise RepairError(f'Local provisioning command: {type(error).__name__}; output withheld.') from None
    if result.returncode:
        raise RepairError(f'Local provisioning command exited {result.returncode}; output withheld.')
    return result.stdout.strip()


def private_write(path, value):
    """Write atomically; set current-user-only ACL before storing secrets on Windows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.migu-secret-')
    os.close(fd)
    try:
        if os.name == 'nt':
            account = quiet_run(['whoami'])
            quiet_run(['icacls', temporary, '/inheritance:r', '/grant:r', account+':F'])
        else:
            os.chmod(temporary, 0o600)
        with open(temporary, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_key(client, key):
    data = client.request('/api/v1/auth/me', key=key)
    scopes = data.get('user', {}).get('scopes', [])
    if not any(scope in scopes for scope in ('tiktok:read', 'admin')):
        raise RepairError('Existing API key lacks tiktok:read; original key preserved.')


def provision(client, *, admin_path, key_path, instance, create_admin, existing_key=None,
              apply=True):
    if existing_key is None and key_path.is_file():
        existing_key = key_path.read_text(encoding='utf-8-sig').strip()
        if not existing_key:
            raise RepairError('Existing key file is empty; preserved for repair.')
    initialized = client.request('/api/setup/status').get('initialized')
    if not isinstance(initialized, bool):
        raise RepairError('Setup status missing initialized boolean; no changes made.')
    if existing_key:
        if not initialized:
            raise RepairError('Configured key belongs to an initialized service; verify the endpoint.')
        validate_key(client, existing_key)
        return {'credentials': 'reused'}
    if not apply:
        raise RepairError('No usable key found; run --apply to provision this local instance.')
    if not instance or create_admin is None:
        raise RepairError('Local Evil API container not identified; no accounts changed.')
    if admin_path.is_file():
        credentials = json.loads(admin_path.read_text(encoding='utf-8'))
        if credentials.get('instance') != instance:
            raise RepairError('Saved credentials belong to another instance; preserved, not sent.')
    elif initialized:
        raise RepairError('Instance already initialized: locate its existing local API key or administrator '
                          'credentials; no account reset. See docs/WINDOWS-REPAIR.md.')
    else:
        credentials = {'instance': instance, 'username': 'migu-local',
                       'password': secrets.token_urlsafe(36)}
        private_write(admin_path, json.dumps(credentials)+'\n')
    if not initialized:
        create_admin(credentials['username'], credentials['password'])
        if client.request('/api/setup/status').get('initialized') is not True:
            raise RepairError('Administrator creation not confirmed; credentials retained for recovery.')
    client.request('/api/v1/auth/login', {
        'username': credentials['username'], 'password': credentials['password']})
    # Persist uncertainty before a non-idempotent API request. A timeout must not
    # silently create a second key on the next run.
    pending = key_path.with_suffix('.pending.json')
    if pending.exists():
        raise RepairError('Previous key issuance is unresolved; inspect the saved pending record '
                          'and admin key list before retrying (docs/WINDOWS-REPAIR.md).')
    name = 'migu-local-'+secrets.token_hex(6)
    private_write(pending, json.dumps({'instance': instance, 'name': name})+'\n')
    key = client.request('/api/v1/admin/api-keys', {
        'name': name, 'scopes': ['tiktok:read'], 'rate_limit': 60}).get('key')
    if not isinstance(key, str) or not key:
        raise RepairError('API key creation returned no key; pending record retained.')
    private_write(key_path, key+'\n')
    pending.unlink()
    validate_key(client, key)
    return {'credentials': 'created', 'admin_file': str(admin_path)}


def find_container(docker, port, env=None):
    ids = quiet_run([docker, 'ps', '--filter', f'publish={port}', '--format', '{{.ID}}'], env=env).splitlines()
    matches = []
    for identifier in ids:
        rows = json.loads(quiet_run([docker, 'inspect', identifier], env=env))
        row = rows[0]
        labels = row.get('Config', {}).get('Labels') or {}
        ports = row.get('NetworkSettings', {}).get('Ports') or {}
        binding = any(p.get('HostPort') == str(port) and p.get('HostIp') in ('127.0.0.1', '::1')
                      for p in ports.get('8000/tcp', []) or [])
        if labels.get('com.docker.compose.service') == 'api' and binding:
            # Container IDs change on recreation; compose project+working directory do not.
            instance = labels.get('com.docker.compose.project', '')+'|'+labels.get('com.docker.compose.project.working_dir', '')
            matches.append((identifier, instance))
    if len(matches) != 1:
        return None, None
    return matches[0]


POOL_PROBE = '''import json
from dtk.cli import runtime
from dtk.db.repositories import IdentityRepository
from dtk.core.types import Platform, IdentityState
from dtk.platforms.tiktok.endpoints import ENDPOINTS, SEARCH_POSTS
async def inspect(ctx):
    rows = await IdentityRepository(ctx.session).list_by_state(
        platform=Platform.TIKTOK, states=tuple(IdentityState))
    live = [r for r in rows if r.state != 'retired']
    ready = [r for r in live if r.state in ('active', 'degraded')]
    return {'active': len(ready), 'live': len(live),
            'authenticated': sum(r.authenticated for r in live),
            'search_login_candidates': sum(r.authenticated and
                (r.rotation_endpoints is None or SEARCH_POSTS in r.rotation_endpoints)
                for r in ready),
            'search_login_policy': ENDPOINTS[SEARCH_POSTS].login.value}
print(json.dumps(runtime.with_context(inspect)))
'''
BROWSER_PROBE = '''import json, os, urllib.request
base = os.environ.get('DTK_BROWSER_RPC_URL', '').rstrip('/')
if not base: raise SystemExit(2)
with urllib.request.urlopen(base+'/rpc/health', timeout=10) as response:
    print(json.dumps({'status': json.load(response).get('status')}))
'''


def verify_search(client, key, keyword):
    # Use the shipped collector's real parsing/polling; never return raw service bodies.
    import importlib.util
    source = Path(__file__).resolve().parents[1]/'toolkits/collector/workflow/unattended/evil_discovery.py'
    spec = importlib.util.spec_from_file_location('migu_search_check', source)
    discovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(discovery)

    def get(url, *, api_key, timeout):
        prefix = client.base+'/'
        if not url.startswith(prefix):
            raise RepairError('Search check refused a different API origin.')
        return client.request('/'+url[len(prefix):], key=api_key,
                              envelope=True, timeout=min(timeout, 40))

    return discovery.search_keyword_urls(keyword, base=client.base, api_key=key,
                                         count=5, wait=10, timeout=45, getter=get)


def repair(*, base='http://127.0.0.1:8000', docker=None, env=None, apply=False,
           verify_keyword=None):
    env = os.environ if env is None else env
    client = Client(base)
    client.request('/readyz')
    folder = Path.home()/'.config/video-workflow'
    key_path = Path(env.get('VW_EVIL_API_KEY_FILE') or folder/'dtk_api_key.txt').expanduser()
    existing_key = env.get('VW_EVIL_API_KEY', '').strip() or None
    if not existing_key and not key_path.exists() and not env.get('VW_EVIL_API_KEY_FILE'):
        legacy = Path.home()/'.config/dtk/api_key.txt'
        if legacy.is_file():
            key_path = legacy
    if env.get('VW_EVIL_API_KEY_FILE') and not key_path.is_file():
        raise RepairError('Explicit VW_EVIL_API_KEY_FILE is missing; locate it before provisioning.')
    docker = docker or shutil.which('docker', path=env.get('PATH'))
    container, instance = find_container(docker, client.port, env) if docker else (None, None)

    def command(*args, input=None, timeout=60):
        return quiet_run([docker, 'exec', '-i', container, *args], input=input,
                         timeout=timeout, env=env)

    result = provision(client, admin_path=folder/'migu-evil-admin.json', key_path=key_path,
                       instance=instance, existing_key=existing_key, apply=apply,
                       create_admin=(lambda name, password: command(
                           'dtk', 'user', 'create', name, '--stdin', input=password+'\n')) if container else None)
    result.update(api_base=base, api_key_file=str(key_path) if key_path.is_file() else None,
                  status='AUTHENTICATED', pending=[], search_verified=False)
    if not container:
        result['pending'].append('API key verified; local browser/identity pool not inspected (container not identified).')
        return result
    browser = json.loads(command('python', '-c', BROWSER_PROBE))
    if browser.get('status') != 'ok':
        raise RepairError('Browser RPC not healthy; credentials preserved. Inspect browser service.')
    pool = json.loads(command('python', '-c', POOL_PROBE))
    if not pool['live'] and apply and pool['search_login_policy'] != 'required':
        command('dtk', 'identity', 'mint', '--platform', 'tiktok', '--count', '1', timeout=240)
        pool = json.loads(command('python', '-c', POOL_PROBE))
    result.update(browser='healthy', active_identities=pool['active'],
                  login_identities=pool['authenticated'],
                  search_login_candidates=pool['search_login_candidates'],
                  search_login_policy=pool['search_login_policy'])
    if pool['search_login_policy'] == 'required' and not pool['search_login_candidates']:
        result['status'] = 'TIKTOK_LOGIN_UNAVAILABLE' if pool['authenticated'] else 'TIKTOK_LOGIN_REQUIRED'
        result['pending'].append(
            'Running DTK requires TikTok login for the first search page. '
            + ('Existing login identities are cooling or excluded from search rotation; inspect them without resetting. '
               if pool['authenticated'] else
               'Import the customer-authorized TikTok session using its matching browser fingerprint and egress. ')
            + 'DTK administrator login and minted guests do not supply this session. See docs/WINDOWS-REPAIR.md.')
        return result
    if not pool['active']:
        result['status'] = 'IDENTITY_UNAVAILABLE'
        result['pending'].append('No active/degraded TikTok identity. Preserve the pool and diagnose network/browser; no repeated minting.')
        return result
    result['status'] = 'SEARCH_UNVERIFIED'
    if not verify_keyword:
        result['pending'].append('Real search not tested. Run scripts/repair_evil.py --verify-search with a representative keyword.')
        return result
    key = existing_key or key_path.read_text(encoding='utf-8-sig').strip()
    try:
        videos = verify_search(client, key, verify_keyword)
    except (RepairError, OSError, RuntimeError, ValueError) as error:
        result['status'] = 'SEARCH_FAILED'
        result['pending'].append(str(error) if isinstance(error, RepairError)
                                 else 'Real search failed: '+type(error).__name__+'; response withheld.')
        return result
    result.update(video_count=len(videos), search_keyword=verify_keyword,
                  search_verified=bool(videos),
                  status='SEARCH_VERIFIED' if videos else 'SEARCH_EMPTY')
    if not videos:
        result['pending'].append('Real search returned no video URLs; acquisition is not accepted yet.')
    return result


def locked_repair(**kwargs):
    if not kwargs.get('apply'):
        return repair(**kwargs)
    # Use the same OS-backed lock as the editor. Process exit releases it.
    import importlib.util
    source = Path(__file__).resolve().parents[1]/'toolkits/editor/workflow/platforms/locks.py'
    spec = importlib.util.spec_from_file_location('migu_provision_lock', source)
    locks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(locks)
    folder = Path.home()/'.config/video-workflow'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder/'migu-setup.lock').open('a+b') as stream:
        try:
            locks.acquire(stream, blocking=False)
        except BlockingIOError:
            raise RepairError('Another local repair is running; resume when it completes.') from None
        try:
            return repair(**kwargs)
        finally:
            locks.release(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--base', default=os.environ.get('VW_EVIL_API_BASE', 'http://127.0.0.1:8000'))
    parser.add_argument('--verify-search', metavar='KEYWORD', help='Run one real search; output counts only, no cookies.')
    args = parser.parse_args()
    try:
        result = locked_repair(base=args.base, apply=args.apply, verify_keyword=args.verify_search)
    except (RepairError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, RepairError) else type(error).__name__
        print(json.dumps({'status': 'ACTION_REQUIRED', 'reason': message}, ensure_ascii=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 2 if result['pending'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
