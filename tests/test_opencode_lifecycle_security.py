"""Independent lifecycle failure/isolation regressions; no model requests."""
import json
import unittest
from unittest.mock import patch

from hivemind.opencode_adapter import handle
from hivemind.opencode_runner import OpenCodeHost
import test_git_bridge_http as fixtures


class OpenCodeLifecycleSecurityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        with patch('hivemind.opencode_runner.executable', return_value='opencode'):
            self.host = OpenCodeHost(self.bridge, model='opencode/synthetic-test-model')
        self.event = {'session': 'owned-session', 'turn': 'turn-1', 'host_id': self.host.host_id}
        handle(self.bridge, {**self.event, 'type': 'prompt'})

    def send(self, kind, **values):
        return handle(self.bridge, {**self.event, 'type': kind, **values})

    def failures(self):
        with self.bridge.db() as db:
            return [json.loads(raw) for (raw,) in db.execute(
                "SELECT value FROM state WHERE key LIKE 'capture_failure:%'").fetchall()]

    def test_failed_capture_is_not_hidden_by_later_no_change(self):
        with self.assertRaises(ValueError):
            self.send('call', tool='save_finding', call_id='rejected-write', arguments={
                'title': 'Private source rejected', 'body': 'A useful observation was attempted.',
                'paths': ['.env']})
        self.send('call', tool='record_no_change', call_id='later-no-change', arguments={})
        done = self.send('complete', event_id='complete-1')
        self.assertEqual(done['capture'], 'failed')
        self.assertTrue(done['warning'])
        self.assertEqual(self.bridge.get('capture_status:owned-session'), 'failed')
        failures = self.failures()
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]['call_id'], 'rejected-write')
        self.assertFalse('A useful observation was attempted.' in json.dumps(failures),
                         'Failure metadata must not retain rejected capture content')

    def test_invalid_capture_schema_cannot_be_hidden_by_no_change(self):
        with self.assertRaises(ValueError):
            self.send('call', tool='save_finding', call_id='invalid-schema',
                      arguments={'title': 'Missing required body'})
        self.send('call', tool='record_no_change', call_id='later-no-change', arguments={})
        done = self.send('complete', event_id='complete-1')
        self.assertEqual(done['capture'], 'failed')
        self.assertTrue(done['warning'])
        self.assertEqual(len(self.failures()), 1)

    def test_earlier_turn_events_cannot_mutate_current_turn_capture(self):
        self.send('prompt', turn='turn-2')
        before = self.bridge.get('opencode:owned-session')
        with self.assertRaisesRegex(ValueError, 'earlier prompt'):
            self.send('call', tool='save_finding', call_id='old-call', arguments={
                'title': 'Old turn observation', 'body': 'Do not bind an old interpretation to a new turn.',
                'paths': ['code.txt']})
        with patch.object(self.bridge, 'call', wraps=self.bridge.call) as calls:
            self.assertEqual(self.send('context')['ignored'], 'earlier_turn')
            self.assertEqual(self.send('tool', tool='read', call_id='old-tool', status='success')['ignored'], 'earlier_turn')
            self.assertEqual(self.send('complete')['ignored'], 'earlier_turn')
        self.assertFalse(calls.called)
        self.assertEqual(self.bridge.get('opencode:owned-session'), before)
        self.assertEqual(self.bridge.get('capture_status:owned-session'), 'pending')
        self.assertEqual(self.failures(), [])

    def test_missing_prompt_context_does_not_create_a_failure_for_a_future_turn(self):
        unknown = {**self.event, 'session': 'unknown-session'}
        with self.assertRaises(ValueError):
            handle(self.bridge, {**unknown, 'type': 'call', 'tool': 'record_no_change',
                                 'call_id': 'without-prompt', 'arguments': {}})
        self.assertIsNone(self.bridge.get('capture_status:unknown-session'))
        self.assertEqual(self.failures(), [])

    def test_host_timeout_marks_only_its_owned_pending_sessions_failed(self):
        foreign = {'session': 'foreign-session', 'turn': 'foreign-turn', 'host_id': 'foreign-host'}
        handle(self.bridge, {**foreign, 'type': 'prompt'})
        with patch.object(self.host, 'api', return_value={'ok': True}) as native:
            with self.assertRaisesRegex(ValueError, 'timed out'):
                self.host.drain(timeout=.001)
        self.assertEqual(native.call_count, 1)
        self.assertEqual(self.bridge.get('capture_status:owned-session'), 'failed')
        self.assertEqual(self.bridge.get('capture_status:foreign-session'), 'pending')
        self.assertTrue(self.bridge.get('capture_warning'))
        with patch.object(self.host, 'api') as retry:
            with self.assertRaisesRegex(ValueError, 'capture failed'):
                self.host.drain(timeout=.001)
        self.assertFalse(retry.called, 'Timeout retry must not start a second native continuation')

    def test_native_continuation_api_failure_is_visible_and_not_retried(self):
        with patch.object(self.host, 'api', side_effect=ValueError('Synthetic native API rejection')) as native:
            with self.assertRaisesRegex(ValueError, 'Synthetic native API rejection'):
                self.host.drain(timeout=.001)
        self.assertEqual(native.call_count, 1)
        self.assertEqual(self.bridge.get('capture_status:owned-session'), 'failed')
        self.assertTrue(self.bridge.get('capture_warning'))
        with patch.object(self.host, 'api') as retry:
            with self.assertRaisesRegex(ValueError, 'capture failed'):
                self.host.drain(timeout=.001)
        self.assertFalse(retry.called)

    def test_new_turn_can_retry_without_erasing_historical_failure(self):
        with self.assertRaises(ValueError):
            self.send('call', tool='save_finding', call_id='rejected-write', arguments={
                'title': 'Rejected source', 'body': 'Prior turn failed.', 'paths': ['.env']})
        self.send('prompt', turn='turn-2')
        self.send('call', turn='turn-2', tool='record_no_change', call_id='new-turn-no-change', arguments={})
        done = self.send('complete', turn='turn-2', event_id='complete-2')
        self.assertEqual(done['capture'], 'no_change')
        self.assertEqual(len(self.failures()), 1)

    def test_saved_receipt_does_not_close_an_active_native_capture_pass(self):
        self.assertTrue(self.send('complete', event_id='primary-terminal', event_created=1)['continue'])
        self.send('context')
        started = self.bridge.get('opencode:owned-session')['capture_pass_started_at']
        self.send('call', tool='save_finding', call_id='extra-pass-save', arguments={
            'title': 'Captured before native terminal', 'body': 'The native pass is still running.',
            'paths': ['code.txt']})
        self.assertEqual(self.bridge.get('capture_status:owned-session'), 'saved')
        self.assertTrue(self.host.unfinished('owned-session', self.bridge.get('opencode:owned-session')))

        def finish_native_pass(_):
            self.send('complete', event_id='extra-pass-terminal', event_created=started + 1)

        with patch.object(self.host, 'api') as native, patch(
                'hivemind.opencode_runner.time.sleep', side_effect=finish_native_pass) as wait:
            self.host.drain(timeout=2)
        self.assertTrue(wait.called, 'Host returned before the active capture pass produced a terminal event')
        self.assertFalse(native.called, 'The existing native pass must not start another continuation')
        self.assertTrue(self.bridge.get('opencode:owned-session')['capture_pass_finished'])

    def test_delayed_primary_terminal_does_not_close_the_extra_capture_pass(self):
        self.assertTrue(self.send('complete', event_id='primary-terminal', event_created=1)['continue'])
        self.send('context')
        started = self.bridge.get('opencode:owned-session')['capture_pass_started_at']
        self.send('call', tool='record_no_change', call_id='extra-pass-no-change', arguments={})
        self.send('complete', event_id='delayed-primary-receipt', event_created=started - 1)
        state = self.bridge.get('opencode:owned-session')
        self.assertFalse(state.get('capture_pass_finished', False))
        self.assertTrue(self.host.unfinished('owned-session', state))
        self.send('complete', event_id='extra-pass-terminal', event_created=started + 1)
        self.assertTrue(self.bridge.get('opencode:owned-session')['capture_pass_finished'])


if __name__ == '__main__':
    unittest.main()
