"""Cross-session handoff creates lineage without taking over another task."""
import unittest

from hivemind.opencode_adapter import handle
import test_git_bridge_http as fixtures


class CheckpointResumptionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge

    def prompt(self, session, turn):
        event = {'session': session, 'turn': turn}
        handle(self.bridge, dict(event, type='prompt'))
        return event

    def checkpoint(self, event, call, **extra):
        return handle(self.bridge, dict(event, type='call', tool='save_checkpoint', call_id=call,
            arguments={'title': 'Queue task', 'body': 'Completed queue inspection. Next: validate the shared queue.',
                       'paths': ['code.txt'], **extra}))

    def test_new_session_resumes_immutable_checkpoint_without_superseding_it(self):
        first = self.prompt('original-session', 'turn-a')
        original = self.checkpoint(first, 'original')['memory']
        fresh = self.prompt('fresh-session', 'turn-b')
        resumed = self.checkpoint(fresh, 'resume', resumes_id=original['id'])['memory']
        self.assertNotEqual(original['id'], resumed['id'])
        self.assertEqual(resumed['session'], 'fresh-session')
        self.assertEqual(resumed['data']['resumes_id'], original['id'])
        self.assertIsNone(resumed['data']['supersedes_id'])
        inspection = self.bridge.call('explain', {'memory_id': resumed['id']})
        self.assertEqual([(a, b) for a, b, _ in inspection['resumption']], [(resumed['id'], original['id'])])
        self.assertEqual(self.bridge.call('explain', {'memory_id': original['id']})['memory'], original)
        self.assertEqual(handle(self.bridge, dict(fresh, type='complete', event_id='terminal'))['capture'], 'saved')

    def test_resumption_does_not_authorize_cross_session_checkpoint_revision(self):
        first = self.prompt('original-session', 'turn-a')
        original = self.checkpoint(first, 'original')['memory']
        fresh = self.prompt('fresh-session', 'turn-b')
        with self.assertRaisesRegex(ValueError, 'Concurrent tasks'):
            self.checkpoint(fresh, 'takeover', resumes_id=original['id'], supersedes_id=original['id'])
        self.assertEqual(self.bridge.call('explain', {'memory_id': original['id']})['memory'], original)

    def test_unknown_or_noncheckpoint_resumption_is_rejected(self):
        event = self.prompt('current-session', 'turn-a')
        finding = handle(self.bridge, dict(event, type='call', tool='save_finding', call_id='finding',
            arguments={'title': 'Queue bound', 'body': 'Observe queue bounds.', 'paths': ['code.txt']}))['memory']
        for memory_id in ('revision:missing', finding['id']):
            with self.subTest(memory_id=memory_id), self.assertRaisesRegex(ValueError, 'INVALID_RESUMPTION'):
                self.checkpoint(event, 'invalid-' + memory_id, resumes_id=memory_id)


if __name__ == '__main__':
    unittest.main()
