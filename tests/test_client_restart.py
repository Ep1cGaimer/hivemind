"""Abrupt local bridge restart preserves and flushes pending capture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

import test_git_bridge_http as fixtures
from hivemind.bridge import LocalBridge
from hivemind.domain import GitRecord


class ClientRestartTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge

    def test_pending_capture_survives_abrupt_child_exit_and_flushes_once(self):
        payload = {"title": "Restarted client finding", "body": "Retry after a local process restart.",
                   "paths": ["code.txt"], "session": "restart-session"}
        self.bridge.sync(["code.txt"])
        script = textwrap.dedent(r'''
            import json, os, sys
            from urllib.error import URLError
            from hivemind.bridge import LocalBridge
            root, config_path, payload = sys.argv[1:]
            payload = json.loads(payload)
            bridge = LocalBridge(root, config=json.loads(open(config_path, encoding='utf-8').read()))
            bridge.session = payload['session']
            def offline(*args, **kwargs):
                raise URLError('synthetic client outage')
            bridge.request = offline
            bridge.call('finding', payload)
            os._exit(0)
        ''')
        config = self.bridge.directory / "restart-config.json"
        config.write_text(json.dumps(self.bridge.config), encoding="utf-8")
        child = subprocess.run([sys.executable, "-c", script, str(self.fixture.root), str(config), json.dumps(payload)],
                               cwd=self.fixture.root, capture_output=True, text=True, timeout=30,
                               env={**os.environ, "PYTHONPATH": os.pathsep.join([
                                   str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)
                               ])})
        self.assertEqual(child.returncode, 0, child.stderr)
        fresh = LocalBridge(self.fixture.root, config=self.bridge.config)
        fresh.flush()
        memories = [node for node in self.fixture.runtime.store.nodes("GitRecord")
                     if isinstance(node, GitRecord) and node.kind == "finding"]
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].data["body"], payload["body"])
        self.assertEqual(fresh.get("capture_status:restart-session"), "saved")
        with fresh.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outbox WHERE status='pending'").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
