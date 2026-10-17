import json
import os
import threading
import unittest
from contextlib import closing
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.fixture import BASE_MEMORY_ID, SHARED_SCOPE_ID
from hivemind.gateway import HiveMindGateway
from hivemind.mcp_server import MCPServer
from hivemind.fixture import seed_demo_store


class HttpAndMcpTests(unittest.TestCase):
    def setUp(self):
        # Keep external credentials from changing the offline suite's baseline;
        # the auth behavior is exercised explicitly in its own test.
        self._api_key_patcher = patch.dict(os.environ, {"HIVEMIND_API_KEY": ""}, clear=False)
        self._api_key_patcher.start()
        # Keep the offline contract suite deterministic even when a caller's
        # shell exports an unsupported backend for a separate startup test.
        runtime = HiveMindRuntime(environ={"HIVEMIND_BACKEND": "memory"})
        self.server = HiveMindHTTPServer(("127.0.0.1", 0), runtime=runtime)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self._api_key_patcher.stop()

    def request(self, path, method="GET", payload=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(self.base + path, data=body, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())

    def test_health_and_state_report_the_selected_memory_backend(self):
        status, health = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["backend"], "memory")

        status, state = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(state["ok"])
        self.assertEqual(state["backend"], "memory")
        self.assertEqual(state["state"]["backend"], "memory")
        self.assertEqual(state["integration"]["backend"], "memory")

    def test_state_and_demo_expose_real_evidence_and_cold_receipt(self):
        status, state = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(state["ok"])
        self.assertTrue(state["memory_versions"])
        self.assertTrue(state["evidence"]["path"])
        self.assertEqual(
            [node["kind"] for node in state["evidence"]["path"]],
            ["MemoryVersion", "Claim", "SupportProposal", "SourcePassage"],
        )

        status, demo = self.request("/api/demo", method="POST", payload={})
        self.assertEqual(status, 200)
        self.assertTrue(demo["ok"])
        self.assertEqual(demo["steps"][-1]["step"], "scope_isolation_check")
        self.assertTrue(demo["assertions"]["correction_recalled_after_cold_restart"])
        status, after = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(after.get("draft", {}).get("draft"))

    def test_mutations_require_optional_api_key(self):
        with patch.dict(os.environ, {"HIVEMIND_API_KEY": "local-test-key"}):
            status, _ = self.request("/api/reset", method="POST", payload={}, headers={"X-HiveMind-Key": "local-test-key"})
            self.assertEqual(status, 200)
            with self.assertRaises(HTTPError) as context:
                self.request("/api/reset", method="POST", payload={})
            self.assertEqual(context.exception.code, 401)

    def test_mcp_registry_and_notifications_are_bounded(self):
        server = MCPServer(HiveMindGateway(seed_demo_store()))
        initialized = server.dispatch(
            {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
        )
        self.assertEqual(initialized["result"]["serverInfo"]["backend"], "memory")
        self.assertIsNone(server.dispatch({"jsonrpc": "2.0", "method": "tools/list", "params": {}}))
        listed = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertIn("record_exposure", names)
        recalled = server.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "recall_context", "arguments": {"scope_id": SHARED_SCOPE_ID}},
            }
        )
        self.assertFalse(recalled["result"]["isError"])
        structured = recalled["result"]["structuredContent"]
        self.assertTrue(structured["ok"])
        self.assertTrue(structured["support_paths"])


if __name__ == "__main__":
    unittest.main()
