"""Provisioning invariants; synthetic service, no real accounts or generation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repair_evil', ROOT/'scripts/repair_evil.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class Service:
    def __init__(self, initialized=False):
        self.initialized = initialized
        self.calls = []

    def request(self, path, data=None, key=None):
        self.calls.append((path, data, key))
        if path == '/api/setup/status':
            return {'initialized': self.initialized}
        if path == '/api/v1/auth/me':
            if key != 'synthetic-key':
                raise repair.RepairError('invalid key')
            return {'user': {'scopes': ['tiktok:read']}}
        if path == '/api/v1/auth/login':
            return {'user': {'role': 'admin'}}
        if path == '/api/v1/admin/api-keys':
            return {'key': 'synthetic-key'}
        raise AssertionError(path)


class EvilRepairTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.admin = self.root/'admin.json'
        self.key = self.root/'key.txt'
        self.service = Service()
        self.created = []

    def create_admin(self, username, password):
        # Recovery credentials must be durably saved before the server mutates.
        saved = json.loads(self.admin.read_text(encoding='utf-8'))
        self.assertEqual(saved['password'], password)
        self.created.append(username)
        self.service.initialized = True

    def provision(self, **kwargs):
        return repair.provision(self.service, admin_path=self.admin, key_path=self.key,
                                instance='synthetic-instance', create_admin=self.create_admin,
                                **kwargs)

    def test_fresh_setup_creates_read_key_and_second_run_reuses_it(self):
        self.provision()
        self.assertEqual(self.key.read_text().strip(), 'synthetic-key')
        calls = [c for c in self.service.calls if c[0] == '/api/v1/admin/api-keys']
        self.assertEqual(calls[0][1]['scopes'], ['tiktok:read'])
        self.provision()
        self.assertEqual(len(self.created), 1)
        self.assertEqual(len([c for c in self.service.calls if c[0].endswith('/api-keys')]), 1)

    def test_existing_key_does_not_create_or_reset_admin(self):
        self.service.initialized = True
        self.key.write_text('synthetic-key')
        self.provision()
        self.assertFalse(self.created)
        self.assertFalse(self.admin.exists())
        self.assertFalse(any(c[1] is not None for c in self.service.calls))

    def test_existing_user_without_credentials_is_not_reset(self):
        self.service.initialized = True
        with self.assertRaises(repair.RepairError):
            self.provision()
        self.assertFalse(self.created)
        self.assertFalse(self.admin.exists())

    def test_different_instance_never_receives_saved_password(self):
        self.service.initialized = True
        self.admin.write_text(json.dumps({'instance': 'other', 'password': 'private'}))
        with self.assertRaises(repair.RepairError):
            self.provision()
        self.assertFalse(any(c[1] is not None for c in self.service.calls))

    def test_invalid_existing_key_is_preserved(self):
        self.service.initialized = True
        self.key.write_text('do-not-overwrite')
        with self.assertRaises(repair.RepairError):
            self.provision()
        self.assertEqual(self.key.read_text(), 'do-not-overwrite')

    def test_uninitialized_service_is_not_claimed_without_local_container(self):
        with self.assertRaises(repair.RepairError):
            repair.provision(self.service, admin_path=self.admin, key_path=self.key,
                             instance=None, create_admin=None)
        self.assertFalse(self.admin.exists())

    def test_remote_base_refused_before_sending_credentials(self):
        for base in ('http://example.com:8000', 'http://127.0.0.1:8000@evil.example',
                     'http://127.0.0.1:8000/path', 'http://127.0.0.1:8000?token=x'):
            with self.subTest(base=base), self.assertRaises(repair.RepairError):
                repair.Client(base)


class SearchReadinessTests(unittest.TestCase):
    def run_repair(self, *, required=True, authenticated=0, eligible=0, verify=False, videos=None):
        pool = {'active': 8, 'live': 8, 'authenticated': authenticated,
                'search_login_candidates': eligible,
                'search_login_policy': 'required' if required else 'preferred'}
        def command(args, **kwargs):
            if args[-1] == repair.BROWSER_PROBE:
                return json.dumps({'status': 'ok'})
            if args[-1] == repair.POOL_PROBE:
                return json.dumps(pool)
            raise AssertionError('Unexpected mutation: '+repr(args[:5]))
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(repair.Path, 'home', return_value=Path(folder)), \
             patch.object(repair.Client, 'request', return_value={}), \
             patch.object(repair, 'provision', return_value={'credentials': 'reused'}), \
             patch.object(repair, 'find_container', return_value=('api', 'local')), \
             patch.object(repair, 'quiet_run', side_effect=command):
            if verify:
                with patch.object(repair, 'verify_search', return_value=videos):
                    return repair.repair(docker='docker', env={'VW_EVIL_API_KEY': 'fixture'},
                                         verify_keyword='coffee')
            return repair.repair(docker='docker', env={'VW_EVIL_API_KEY': 'fixture'})

    def test_guests_do_not_satisfy_required_search_login(self):
        result = self.run_repair()
        self.assertEqual(result['status'], 'TIKTOK_LOGIN_REQUIRED')
        self.assertTrue(result['pending'])
        self.assertFalse(result['search_verified'])

    def test_reserved_or_cooling_login_does_not_satisfy_search(self):
        result = self.run_repair(authenticated=1, eligible=0)
        self.assertEqual(result['status'], 'TIKTOK_LOGIN_UNAVAILABLE')
        self.assertTrue(result['pending'])

    def test_old_guest_capable_version_still_requires_real_search_acceptance(self):
        result = self.run_repair(required=False)
        self.assertEqual(result['status'], 'SEARCH_UNVERIFIED')
        self.assertTrue(result['pending'])

    def test_login_marker_alone_is_not_search_success(self):
        result = self.run_repair(authenticated=1, eligible=1)
        self.assertEqual(result['status'], 'SEARCH_UNVERIFIED')
        self.assertFalse(result['search_verified'])

    def test_real_empty_search_is_not_reported_as_ready(self):
        result = self.run_repair(authenticated=1, eligible=1, verify=True, videos=[])
        self.assertEqual(result['status'], 'SEARCH_EMPTY')
        self.assertFalse(result['search_verified'])
        self.assertTrue(result['pending'])

    def test_real_video_search_makes_search_ready(self):
        result = self.run_repair(required=False, verify=True,
                                 videos=[{'url': 'https://www.tiktok.com/@fixture/video/123456789'}])
        self.assertEqual(result['status'], 'SEARCH_VERIFIED')
        self.assertTrue(result['search_verified'])
        self.assertEqual(result['video_count'], 1)
        self.assertFalse(result['pending'])


if __name__ == '__main__':
    unittest.main()
