"""Artifact-wide private-capture regression checks."""
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from urllib.error import URLError

from hivemind.domain import GitRecord
import test_git_bridge_http as fixtures


class PrivacyArtifactTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        self.canary = "HM_PRIVATE_CANARY_20261018_UNIQUE"
        (self.fixture.root / "secret.txt").write_text(self.canary, encoding="utf-8")
        self.bridge.config["private_paths"] = ["secret.txt"]
        self.bridge.config_path.write_text(json.dumps(self.bridge.config), encoding="utf-8")

    def scan(self):
        haystacks = []
        for path in self.fixture.root.rglob("*"):
            if path.is_file() and path.name not in {"secret.txt", "config.json"}:
                try:
                    haystacks.append((str(path), path.read_bytes()))
                except OSError:
                    pass
        for node in self.fixture.runtime.store.nodes("GitRecord"):
            haystacks.append(("store:" + node.id, json.dumps(node.__dict__, default=str).encode()))
        for path in Path(self.bridge.directory).glob("*.sqlite3"):
            db = sqlite3.connect(path)
            for table in ("state", "outbox"):
                for row in db.execute("SELECT * FROM " + table):
                    haystacks.append((str(path) + ":" + table, repr(row).encode()))
            db.close()
        return [(name, data) for name, data in haystacks if self.canary.encode() in data or b"secret.txt" in data]

    def test_online_and_offline_capture_surfaces_contain_no_private_canary(self):
        for action in ("finding", "checkpoint", "no-change"):
            with self.subTest(action=action):
                payload = {"title": "Private boundary", "body": "Do not persist private material.",
                           "paths": ["secret.txt"], "session": "privacy-" + action}
                with self.assertRaisesRegex(ValueError, "private"):
                    self.bridge.call(action, payload)
        with patch.object(self.bridge, "request", side_effect=URLError("offline")):
            with self.assertRaisesRegex(ValueError, "private"):
                self.bridge.call("finding", {"title": "Private text", "body": self.canary,
                                               "paths": ["code.txt"], "session": "privacy-text"})
        self.assertEqual(self.scan(), [])


if __name__ == "__main__":
    unittest.main()
