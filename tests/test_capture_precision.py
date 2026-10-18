"""Privacy must reject private references without rejecting ordinary prose."""
import unittest
from unittest.mock import patch
from urllib.error import URLError

import test_git_bridge_http as fixtures


class CapturePrecisionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge

    def test_ellipsis_is_saved_and_queued_as_prose(self):
        for offline in (False, True):
            with self.subTest(offline=offline):
                payload = {'title': 'Preserve SQL placeholders', 'body': 'Use SELECT ... with exact matching. Keep the condition ... and validate code.txt.',
                           'paths': ['code.txt'], 'event_id': 'ellipsis-' + str(offline)}
                if offline:
                    with patch.object(self.bridge, 'request', side_effect=URLError('synthetic outage')):
                        result = self.bridge.call('finding', payload)
                    self.assertTrue(result['queued'])
                else:
                    result = self.bridge.call('finding', payload)
                    self.assertEqual(result['memory']['data']['body'], payload['body'])

    def test_punctuation_does_not_hide_a_private_reference(self):
        for body in ('Do not copy .env...', 'See key.pem...', 'Never bind ../outside.txt...'):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, 'PRIVATE_CONTENT'):
                self.bridge.check_capture_privacy({'body': body})


if __name__ == '__main__':
    unittest.main()
