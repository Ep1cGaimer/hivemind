"""HTTP/bridge/outage acceptance with a real local server and Git clone."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, git, serve_mcp
from hivemind.domain import GitRecord


class BridgeHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.email', 'fixture@example.test')
        git(self.root, 'config', 'user.name', 'Fixture')
        (self.root / 'code.txt').write_text('Use bounded queues.\n')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'Initial')
        self.runtime = HiveMindRuntime({'HIVEMIND_USERS': 'operator=pw,viewer=pw'})
        self.owner = self.runtime.auth.login('operator', 'pw')[1]
        self.project = self.runtime.projects.create_project(self.owner, 'HTTP fixture')['project']['id']
        self.runtime.projects.add_member(self.owner, self.project, 'viewer', 'viewer')
        self.token, self.token_record = self.runtime.auth.create_agent_token(self.owner, 'bridge fixture', self.project)
        self.server = HiveMindHTTPServer(('127.0.0.1', 0), runtime=self.runtime)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)
        repo = self.runtime.git_memory.register(self.owner, self.project, {'remote': 'fixture.invalid/http', 'root_commit': git(self.root, 'rev-parse', 'HEAD')})['repo_id']
        self.bridge = LocalBridge(self.root, config={'url': self.base, 'project_id': self.project, 'repo_id': repo, 'connector_id': 'http-fixture'})
        (self.bridge.directory / 'token').write_text(self.token)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def test_cross_client_cold_mcp_recall_and_revocation(self):
        saved = self.bridge.call('finding', {'title': 'Queue rule', 'body': 'Use bounded queues.', 'paths': ['code.txt'], 'session': 'codex-writer'})
        cold = LocalBridge(self.root, config=self.bridge.config)
        output = io.StringIO()
        serve_mcp(cold, io.StringIO(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'recall_context', 'arguments': {'query': 'queue', 'session': 'claude-reader'}}}) + '\n'), output)
        self.assertIn(saved['memory']['id'], output.getvalue())
        reverse = cold.call('finding', {'title': 'Review rule', 'body': 'Validate queue bounds after edits.', 'paths': ['code.txt'], 'session': 'claude-writer'})
        self.assertIn(reverse['memory']['id'], json.dumps(LocalBridge(self.root, config=self.bridge.config).call('recall', {'session': 'codex-reader'})))
        self.runtime.auth.revoke(self.owner, self.token_record.token_id, self.project)
        with self.assertRaisesRegex(ValueError, 'AUTH_REQUIRED'):
            self.bridge.call('recall', {})

    def test_offline_capture_retry_keeps_original_branch_and_snapshot(self):
        self.bridge.sync(['code.txt'])
        git(self.root, 'switch', '-c', 'unfinished')
        (self.root / 'code.txt').write_text('Unfinished bounded-queue experiment.\n')
        with patch.object(self.bridge, 'request', side_effect=URLError('offline')):
            queued = self.bridge.call('finding', {'title': 'WIP queue experiment', 'body': 'The bounded-queue experiment still needs validation.', 'paths': ['code.txt'], 'session': 'offline-session'})
        self.assertTrue(queued['queued'])
        (self.root / 'code.txt').write_text('Use bounded queues.\n')
        git(self.root, 'switch', 'main')
        self.bridge.sync(['code.txt'])
        memories = [n for n in self.runtime.store.nodes('GitRecord') if isinstance(n, GitRecord) and n.kind == 'finding']
        self.assertEqual(len(memories), 1)
        memory = memories[0]
        observations = [n for n in self.runtime.store.nodes('GitRecord') if isinstance(n, GitRecord) and n.kind == 'observation' and n.branch_id == memory.branch_id]
        self.assertTrue(any(o.data['ref'] == 'refs/heads/unfinished' for o in observations))
        recalled = self.bridge.call('recall', {})
        self.assertNotIn(memory.id, [m['id'] for m in recalled['findings']])
        self.bridge.flush()
        self.assertEqual(len([n for n in self.runtime.store.nodes('GitRecord') if isinstance(n, GitRecord) and n.kind == 'finding']), 1)

    def test_viewer_and_project_scoping_apply_to_legacy_and_git_endpoints(self):
        viewer = self.runtime.auth.login('viewer', 'pw')[1]
        token, _ = self.runtime.auth.create_agent_token(viewer, 'viewer', self.project)
        request = Request(self.base + '/api/memories', data=json.dumps({'title': 'Forbidden', 'body': 'Viewer write'}).encode(), headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)
        other = self.runtime.projects.create_project(self.owner, 'Other project')['project']['id']
        request = Request(self.base + '/api/projects/' + other + '/git/overview', headers={'Authorization': 'Bearer ' + self.token})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)
        request = Request(self.base + '/api/projects', headers={'Authorization': 'Bearer ' + self.token})
        with urlopen(request) as response:
            self.assertEqual([p['id'] for p in json.load(response)['projects']], [self.project])


if __name__ == '__main__':
    unittest.main()
