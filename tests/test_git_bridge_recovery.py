"""Real HTTP failure recovery: live service errors are outages, not bad notes."""
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from hivemind.store import StoreError
import test_git_bridge_http as fixtures


class BridgeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        self.bridge.sync(['code.txt'])

    def test_http_503_queues_and_recovery_updates_visible_capture_status(self):
        outage = {'ok': False, 'error': {'code': 'STORAGE_UNAVAILABLE', 'message': 'Synthetic database outage'}}
        with patch.object(self.fixture.runtime.git_memory, 'operation', return_value=outage):
            capture = self.bridge.call('finding', {'title': 'Queue bound', 'body': 'Use bounded queues.', 'paths': ['code.txt']})
        self.assertTrue(capture['queued'])
        self.assertEqual(self.bridge.get('capture_status:' + self.bridge.session), 'queued')
        self.bridge.sync(['code.txt'])
        self.assertEqual(self.bridge.get('capture_status:' + self.bridge.session), 'saved')
        with self.bridge.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone()[0], 0)
        self.assertIn('Queue bound', [m['title'] for m in self.bridge.call('recall', {})['findings']])

    def test_authentication_storage_failure_returns_503_without_granting_access(self):
        request = Request(self.fixture.base + '/api/projects/' + self.fixture.project + '/git/overview',
                          headers={'Authorization': 'Bearer ' + self.fixture.token})
        with patch.object(self.fixture.runtime.store, 'get_node', side_effect=StoreError('synthetic outage')):
            with self.assertRaises(HTTPError) as result:
                urlopen(request, timeout=3)
            self.assertEqual(result.exception.code, 503)
            response = json.load(result.exception)
            self.assertEqual(response['error']['code'], 'STORAGE_UNAVAILABLE')
            self.assertNotIn('observation', response)

    def test_rejected_queued_capture_exposes_failed_status(self):
        self.bridge.enqueue('finding', {'context_id': self.bridge.get('context')['context_id'],
            'session': self.bridge.session, 'event_id': 'rejected-recovery',
            'title': 'Queue bound', 'body': 'Use bounded queues.', 'paths': ['code.txt']})
        with patch.object(self.bridge, 'request', side_effect=ValueError('synthetic permanent rejection')):
            with self.assertRaisesRegex(ValueError, 'quarantined'):
                self.bridge.flush()
        self.assertEqual(self.bridge.get('capture_status:' + self.bridge.session), 'failed')
        self.assertIn('quarantined', self.bridge.get('capture_warning'))


if __name__ == '__main__':
    unittest.main()
