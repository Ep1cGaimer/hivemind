"""Lifecycle ownership and shutdown controls, without pretending to run a model."""
import unittest
from unittest.mock import patch

from hivemind.opencode_adapter import handle
from hivemind.opencode_runner import OpenCodeHost
import test_git_bridge_http as fixtures


class OpenCodeRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        with patch('hivemind.opencode_runner.executable', return_value='opencode'):
            self.host = OpenCodeHost(self.bridge, model='opencode/example')
        self.event = {'session': 'this-host-session', 'turn': 'turn-1', 'host_id': self.host.host_id}
        handle(self.bridge, {**self.event, 'type': 'prompt'})

    def test_shutdown_pass_is_scoped_to_owned_sessions_and_is_one_pass(self):
        foreign = {'session': 'another-host-session', 'turn': 'foreign-turn', 'host_id': 'another-host'}
        handle(self.bridge, {**foreign, 'type': 'prompt'})
        calls = []
        def api(operation, data, *, params):
            calls.append((operation, params))
            handle(self.bridge, {**self.event, 'type': 'context'})
            handle(self.bridge, {**self.event, 'type': 'call', 'tool': 'record_no_change', 'call_id': 'no-change', 'arguments': {}})
            handle(self.bridge, {**self.event, 'type': 'complete', 'event_id': 'extra-pass-terminal'})
            return {'ok': True}
        with patch.object(self.host, 'api', side_effect=api):
            self.host.drain(timeout=3)
            self.host.drain(timeout=3)
        self.assertEqual(calls, [('session.synthetic', [('sessionID', self.event['session'])])])
        self.assertFalse(self.bridge.get('opencode:' + foreign['session'])['continuation_requested'])
        self.assertEqual(self.bridge.get('capture_status:' + self.event['session']), 'no_change')

    def test_unfinished_capture_times_out_without_another_continuation(self):
        with patch.object(self.host, 'api', return_value={'ok': True}) as native:
            with self.assertRaisesRegex(ValueError, 'timed out'):
                self.host.drain(timeout=.01)
        self.assertEqual(native.call_count, 1)
        self.assertIn('no additional pass', self.bridge.get('capture_warning'))

    def test_missing_plugin_event_is_a_visible_failure(self):
        self.host.host_id = 'host-without-native-events'
        with self.assertRaisesRegex(ValueError, 'no native prompt event'):
            self.host.drain(timeout=.01)

    def test_interrupted_foreground_task_still_drains_capture(self):
        calls = []
        fake = type('FakeHost', (), {
            'program': 'opencode', 'address': 'http://127.0.0.1:1', 'env': {},
            '__enter__': lambda instance: instance,
            '__exit__': lambda instance, *args: None,
            'drain': lambda instance: calls.append('drained'),
        })()
        with patch.object(self.host, 'drain', side_effect=lambda: calls.append('unused')):
            with patch('hivemind.opencode_runner.subprocess.run', return_value=type('Result', (), {'returncode': 130})()):
                from hivemind.opencode_runner import run
                args = type('Args', (), {'model': 'opencode/example', 'prompt': ['interrupted'], 'format': 'json'})()
                # Use a small local substitute so this test exercises the
                # non-zero drain rule without starting a native process.
                with patch('hivemind.opencode_runner.OpenCodeHost', return_value=fake):
                    self.assertEqual(run(self.bridge, args), 130)
        self.assertEqual(calls, ['drained'])


if __name__ == '__main__':
    unittest.main()
