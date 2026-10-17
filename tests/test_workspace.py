import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.auth import AuthManager
from hivemind.fixture import seed_demo_store
from hivemind.gateway import HiveMindGateway
from hivemind.mcp_server import MCPServer
from hivemind.workspace import MemoryWorkspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        runtime = HiveMindRuntime(
            environ={
                "HIVEMIND_BACKEND": "memory",
                "HIVEMIND_USERS": "operator=secret,alice=alice-secret",
            }
        )
        self.server = HiveMindHTTPServer(("127.0.0.1", 0), runtime=runtime)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path, method="GET", payload=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read()), dict(response.headers)

    def login(self):
        status, payload, headers = self.request(
            "/api/auth/login",
            method="POST",
            payload={"username": "operator", "password": "secret"},
        )
        self.assertEqual(status, 200)
        return headers["Set-Cookie"].split(";", 1)[0]

    def test_memory_workspace_requires_identity_and_supports_create_edit_readback(self):
        with self.assertRaises(HTTPError) as context:
            self.request("/api/workspace")
        self.assertEqual(context.exception.code, 401)

        cookie = self.login()
        status, created, _ = self.request(
            "/api/memories",
            method="POST",
            payload={"title": "Release checklist", "body": "Run the staging checks first.", "tags": ["release", "staging"]},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        self.assertTrue(created["created"])
        memory = created["memory"]
        self.assertEqual(memory["version"], 1)

        status, edited, _ = self.request(
            f"/api/memories/{memory['id']}",
            method="PATCH",
            payload={"body": "Run the staging checks, then ask the owner to review.", "tags": ["release"]},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        self.assertEqual(edited["memory"]["version"], 2)
        self.assertEqual(edited["memory"]["supersedes_id"], memory["id"])

        status, workspace, _ = self.request("/api/workspace", headers={"Cookie": cookie})
        self.assertEqual(status, 200)
        self.assertEqual(workspace["count"], 1)
        self.assertEqual(workspace["memories"][0]["body"], "Run the staging checks, then ask the owner to review.")

    def test_agent_token_can_connect_to_workspace_without_a_browser_session(self):
        cookie = self.login()
        status, token_payload, _ = self.request(
            "/api/agents",
            method="POST",
            payload={"label": "Test coding agent"},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        token = token_payload["token"]
        status, created, _ = self.request(
            "/api/memories",
            method="POST",
            payload={"title": "Agent note", "body": "The agent can write here."},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(created["memory"]["owner_user_id"], "operator")

    def test_mcp_workspace_tools_require_and_accept_agent_identity(self):
        auth = AuthManager({"HIVEMIND_OPERATOR_PASSWORD": "secret"})
        login = auth.login("operator", "secret")
        self.assertIsNotNone(login)
        token, _ = auth.create_agent_token(login[1], "unit test agent")
        gateway = HiveMindGateway(seed_demo_store())

        unauthenticated = MCPServer(gateway=gateway)
        denied = unauthenticated.dispatch(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_memories", "arguments": {}}}
        )
        self.assertTrue(denied["result"]["isError"])
        self.assertEqual(denied["result"]["structuredContent"]["error"]["code"], "AUTH_REQUIRED")

        connected = MCPServer(gateway=gateway, auth=auth, agent_token=token)
        created = connected.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "create_memory", "arguments": {"title": "MCP note", "body": "Created through the agent connection."}},
            }
        )
        self.assertFalse(created["result"]["isError"])
        listed = connected.dispatch(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_memories", "arguments": {}}}
        )
        self.assertEqual(listed["result"]["structuredContent"]["count"], 1)

    def test_projects_scope_memories_graph_members_and_agent_tokens(self):
        cookie = self.login()
        status, created, _ = self.request(
            "/api/projects",
            method="POST",
            payload={"name": "Platform migration", "description": "Shared rollout context."},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        project_id = created["project"]["id"]

        status, member, _ = self.request(
            f"/api/projects/{project_id}/members",
            method="POST",
            payload={"user_id": "alice", "role": "editor"},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        self.assertEqual(member["member"]["user_id"], "alice")

        status, memory, _ = self.request(
            f"/api/projects/{project_id}/memories",
            method="POST",
            payload={"title": "Migration constraint", "body": "Keep the queue qualifier in rollout plans.", "tags": ["rollout"]},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        memory_id = memory["memory"]["id"]

        status, graph, _ = self.request(f"/api/projects/{project_id}/graph", headers={"Cookie": cookie})
        self.assertEqual(status, 200)
        self.assertTrue(any(node["id"] == memory_id for node in graph["nodes"]))
        self.assertTrue(any(node["type"] == "person" for node in graph["nodes"]))

        status, token_payload, _ = self.request(
            f"/api/projects/{project_id}/agents",
            method="POST",
            payload={"label": "Project coding agent"},
            headers={"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        self.assertEqual(token_payload["agent"]["project_id"], project_id)


class WorkspaceServiceTests(unittest.TestCase):
    def test_versioned_memory_is_persistent_through_the_store_contract(self):
        store = seed_demo_store()
        workspace = MemoryWorkspace(store)
        identity = AuthManager().login("operator", "operator")[1]
        created = workspace.create(identity, "A useful note", "Keep this context.", ["team"])
        edited = workspace.edit(identity, created["memory"]["id"], None, "Keep this context current.")
        self.assertTrue(edited["ok"])
        listed = workspace.list_memories()
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["memories"][0]["version"], 2)


if __name__ == "__main__":
    unittest.main()
