"""Channel and image-model tests never read or write secrets, and never submit jobs."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/migu/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


channels = load('video_channels')


def api(ident='api-main', **extra):
    data = {'id': ident, 'kind': 'api', 'endpoint_name': 'configured-video', 'account_ref': 'acct-a',
            'credential_present': True}
    data.update(extra)
    return data


def hypit(ident='hypit-default', **extra):
    data = {'id': ident, 'kind': 'hypit', 'hypit_path': '/opt/hypit', 'account_ref': 'acct-b',
            'credential_present': True}
    data.update(extra)
    return data


class VideoChannelTests(unittest.TestCase):
    def test_image_model_is_fixed(self):
        self.assertEqual(channels.configured_image_model({}), 'image2.5flare')
        self.assertEqual(channels.configured_image_model({'image_model': 'image2.5flare'}), 'image2.5flare')
        with self.assertRaisesRegex(channels.ChannelError, 'image2.5flare'):
            channels.configured_image_model({'image_model': 'other-model'})

    def test_load_and_failover(self):
        loaded = channels.load_channels({'video_channels': [api(), hypit()]})
        first = channels.select_channel(loaded)
        self.assertEqual(first['id'], 'api-main')
        second = channels.next_channel(loaded, 'api-main')
        self.assertEqual(second['id'], 'hypit-default')

    def test_skip_unavailable_and_unhealthy(self):
        loaded = channels.load_channels({'video_channels': [api(), hypit()]})
        chosen = channels.select_channel(
            loaded,
            unavailable={'api-main'},
            health=lambda ch: ch['id'] != 'unused',
        )
        self.assertEqual(chosen['id'], 'hypit-default')
        with self.assertRaises(channels.NoAvailableChannel):
            channels.select_channel(loaded, health=lambda ch: False)

    def test_disabled_channel_is_skipped(self):
        loaded = channels.load_channels({'video_channels': [api(enabled=False), hypit()]})
        self.assertEqual(channels.select_channel(loaded)['id'], 'hypit-default')

    def test_api_route_does_not_require_hypit(self):
        config = {'video_channels': [api()]}
        self.assertTrue(channels.has_api_video_route(config))
        self.assertFalse(channels.video_route_requires_hypit(config))
        self.assertTrue(channels.video_route_requires_hypit({}))
        self.assertTrue(channels.video_route_requires_hypit({'video_channels': [hypit()]}))

    def test_credential_reported_as_presence_or_length_only(self):
        self.assertTrue(channels.credential_present({'credential_present': True}))
        self.assertTrue(channels.credential_present({'credential_length': 32}))
        self.assertFalse(channels.credential_present({'credential_length': 0}))
        self.assertFalse(channels.credential_present({}))

    def test_rejects_secret_like_blank_account_ref(self):
        with self.assertRaises(channels.ChannelError):
            channels.load_channels({'video_channels': [api(account_ref='   ')]})


if __name__ == '__main__':
    unittest.main()
