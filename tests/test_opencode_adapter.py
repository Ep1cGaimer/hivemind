"""Trusted OpenCode bridge contracts; these are not real model-session proof."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import URLError

from hivemind import client_adapters
from hivemind.opencode_adapter import handle
import test_git_bridge_http as fixtures


class OpenCodeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        self.base = {'session': 'native-session-A', 'turn': 'native-prompt-1'}
        handle(self.bridge, {**self.base, 'type': 'prompt'})

    def event(self, kind, **values):
        return handle(self.bridge, {**self.base, 'type': kind, **values})

    def test_model_cannot_supply_authoritative_context_or_session(self):
        for key in ('session', 'context_id', 'branch_id', 'head', 'event_id'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Unsupported'):
                self.event('call', tool='save_finding', call_id='forged', arguments={
                    'title': 'Bounded queues', 'body': 'Use bounded queues.', 'paths': ['code.txt'], key: 'forged'})

    def test_finding_checkpoint_and_no_change_use_native_session(self):
        self.event('context', query='queue bounds')
        finding = self.event('call', tool='save_finding', call_id='f1', arguments={
            'title': 'Queue bound', 'body': 'Queue bounds need explicit verification.', 'paths': ['code.txt']})
        checkpoint = self.event('call', tool='save_checkpoint', call_id='c1', arguments={
            'title': 'Queue review', 'body': 'Next: validate the shared queue.', 'paths': ['code.txt']})
        self.assertNotEqual(finding['memory']['id'], checkpoint['memory']['id'])
        self.assertEqual(finding['memory']['session'], self.base['session'])
        self.assertIn('agent-reported', finding['memory']['data']['body'])
        self.assertEqual(self.event('complete')['capture'], 'saved')
        self.assertFalse(self.event('complete').get('continue', False))
        self.base['turn'] = 'native-prompt-2'
        self.event('prompt')
        self.event('call', tool='record_no_change', call_id='n1', arguments={})
        self.assertEqual(self.event('complete')['capture'], 'no_change')

    def test_duplicate_delivery_is_one_revision(self):
        args = {'title': 'Queue bound', 'body': 'Use a bounded queue.', 'paths': ['code.txt']}
        first = self.event('call', tool='save_finding', call_id='same-call', arguments=args)
        second = self.event('call', tool='save_finding', call_id='same-call', arguments=args)
        self.assertEqual(first['memory']['id'], second['memory']['id'])
        self.assertEqual(first['memory']['created_at'], second['memory']['created_at'])

    def test_completion_requests_one_pass_and_exposes_failure(self):
        self.assertTrue(self.event('complete', event_id='completion-1')['continue'])
        self.assertTrue(self.event('complete', event_id='completion-1')['waiting'])
        self.event('context')  # Native model request starts the one capture pass.
        second = self.event('complete', event_id='completion-2')
        self.assertEqual(second['capture'], 'failed')
        self.assertNotIn('continue', second)
        self.assertIn('no further', second['warning'])
        self.assertEqual(self.bridge.get('capture_warning'), second['warning'])

    def test_queued_capture_has_explicit_status(self):
        self.event('context')
        with patch.object(self.bridge, 'request', side_effect=URLError('synthetic outage')):
            saved = self.event('call', tool='save_checkpoint', call_id='offline', arguments={
                'title': 'Review in progress', 'body': 'Next: validate queue bounds.', 'paths': ['code.txt']})
        self.assertTrue(saved['queued'])
        self.assertEqual(self.event('complete')['capture'], 'queued')

    def test_installer_preserves_client_config_and_is_idempotent(self):
        root = self.fixture.root
        config = root / 'opencode.json'
        config.write_text('{"model":"opencode/example","mcp":{"servers":{"existing":{}}}}')
        original = config.read_bytes()
        with patch('hivemind.opencode_adapter.shutil.which', return_value='opencode'), patch(
                'hivemind.opencode_adapter.subprocess.run', return_value=SimpleNamespace(stdout='opencode v2.0.29')):
            first = client_adapters.install(self.bridge, 'opencode')
            path = root / '.opencode/plugins/hivemind.js'
            content = path.read_bytes()
            client_adapters.install(self.bridge, 'opencode')
        self.assertEqual(path.read_bytes(), content)
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(len(list(path.parent.glob('hivemind.*'))), 1)
        self.assertFalse(self.bridge.allowed('.opencode/plugins/hivemind.js'))
        self.assertFalse(self.bridge.allowed('opencode.json'))
        self.assertEqual(first[0]['client'], 'opencode')
        self.assertNotIn(self.fixture.token.encode(), content)

    def test_installer_rejects_unknown_version_and_foreign_plugin(self):
        with patch('hivemind.opencode_adapter.shutil.which', return_value='opencode'), patch(
                'hivemind.opencode_adapter.subprocess.run', return_value=SimpleNamespace(stdout='1.19.3')):
            with self.assertRaisesRegex(ValueError, 'requires OpenCode 2'):
                client_adapters.install(self.bridge, 'opencode')
        path = self.fixture.root / '.opencode/plugins/hivemind.js'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('export default {id:"someone-else"};')
        with patch('hivemind.opencode_adapter.shutil.which', return_value='opencode'), patch(
                'hivemind.opencode_adapter.subprocess.run', return_value=SimpleNamespace(stdout='opencode v2.0.29')):
            with self.assertRaisesRegex(ValueError, 'not managed'):
                client_adapters.install(self.bridge, 'opencode')
        self.assertEqual(path.read_text(), 'export default {id:"someone-else"};')


if __name__ == '__main__':
    unittest.main()
