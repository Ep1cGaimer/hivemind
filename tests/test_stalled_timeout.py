"""Real local stalled HTTP dependency remains bounded and visibly queued."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import unittest

import test_git_bridge_http as fixtures
from hivemind.bridge import LocalBridge


class StalledHandler(BaseHTTPRequestHandler):
    delay = 21

    def do_GET(self):
        time.sleep(self.delay)

    def do_POST(self):
        time.sleep(self.delay)

    def log_message(self, *_args):
        pass


class StalledTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        self.bridge.sync(["code.txt"])
        self.stalled = ThreadingHTTPServer(("127.0.0.1", 0), StalledHandler)
        self.addCleanup(self.stalled.server_close)
        self.addCleanup(self.stalled.shutdown)
        self.thread = threading.Thread(target=self.stalled.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(lambda: self.thread.join(timeout=3))
        self.bridge.config["url"] = "http://127.0.0.1:" + str(self.stalled.server_port)
        self.bridge.config_path.write_text(json.dumps(self.bridge.config), encoding="utf-8")

    def test_stalled_dependency_times_out_without_false_save(self):
        started = time.monotonic()
        self.bridge.session = "stalled-session"
        result = self.bridge.call("finding", {"title": "Stalled dependency", "body": "Retry later.",
                                               "paths": ["code.txt"], "session": "stalled-session"})
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 25)
        self.assertTrue(result.get("queued"))
        self.assertEqual(self.bridge.get("capture_status:stalled-session"), "queued")
        self.assertNotEqual(self.bridge.get("capture_status:stalled-session"), "saved")


if __name__ == "__main__":
    unittest.main()
