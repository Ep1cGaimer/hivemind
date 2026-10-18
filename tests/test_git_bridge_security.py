"""Adversarial Git bridge regressions using real Git and authenticated HTTP.

These independently stated assertions cover branch identity across retries and
credential rejection before a request can enter the local retry queue.
"""
import io
import json
import os
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch
from urllib.error import URLError

from hivemind.bridge import LocalBridge, git, serve_mcp
import test_git_bridge_http as fixtures


class GitBridgeSecurityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.bridge = self.fixture.bridge
        self.bridge.sync(['code.txt'])

    def test_offline_deleted_branch_is_not_retargeted_to_recreated_ref(self):
        git(self.fixture.root, 'switch', '-c', 'transient')
        with patch.object(self.bridge, 'request', side_effect=URLError('synthetic outage')):
            queued = self.bridge.call('finding', {
                'title': 'Original transient branch finding',
                'body': 'This observation belongs to the original transient branch.',
                'paths': ['code.txt'], 'session': 'adversarial-writer',
                'event_id': 'original-transient-finding',
            })
        self.assertTrue(queued['queued'])
        git(self.fixture.root, 'switch', 'main')
        git(self.fixture.root, 'branch', '-D', 'transient')
        git(self.fixture.root, 'switch', '-c', 'transient')
        replacement = self.bridge.sync(['code.txt'])
        recalled = self.bridge.call('recall', {})
        self.assertNotIn('Original transient branch finding',
                         [m['title'] for m in recalled['findings']],
                         'A queued finding was retargeted onto the replacement ref identity')
        findings = [n for n in self.fixture.runtime.store.nodes('GitRecord')
                    if n.kind == 'finding']
        self.assertEqual(len(findings), 1, 'Original queued history must remain preserved')
        self.assertNotEqual(findings[0].branch_id, replacement['branch_id'])

    def test_credential_fixture_is_rejected_before_offline_queue(self):
        credential_fixture = 'sk-' + 'SYNTHETICNOTAREALCREDENTIAL123456'
        captured_error = None
        with patch.object(self.bridge, 'request', side_effect=URLError('synthetic outage')):
            try:
                self.bridge.call('finding', {
                    'title': 'Synthetic credential rejection test',
                    'body': credential_fixture,
                    'paths': ['code.txt'], 'session': 'adversarial-writer',
                    'event_id': 'synthetic-private-content',
                })
            except ValueError as exc:
                captured_error = exc
        with self.bridge.db() as db:
            persisted = json.dumps(db.execute('SELECT action,payload FROM outbox').fetchall())
        self.assertFalse(credential_fixture in persisted,
                         'Credential fixture reached the SQLite retry payload')
        self.assertIsNotNone(captured_error, 'Reject private content before queuing it')
        self.assertIn('PRIVATE_CONTENT', str(captured_error))

    def test_replayed_initial_branch_observation_preserves_identity(self):
        git(self.fixture.root, 'switch', '-c', 'first-sync-retry')
        observation = self.bridge.observe(['code.txt'])
        self.assertIsNone(observation['branch_id'])
        # A response may be lost after persistence, before the client updates its
        # local mapping. Replaying exactly the same observation must be safe.
        first = self.bridge.request('sync', observation)
        repeated = self.bridge.request('sync', observation)
        self.assertEqual(first['branch_id'], repeated['branch_id'],
                         'An identical connector observation created a second branch identity')
        self.assertEqual(first['context_id'], repeated['context_id'])

    def test_model_cannot_impersonate_another_task_session_to_replace_checkpoint(self):
        original = self.bridge.call('checkpoint', {
            'title': 'Task A checkpoint', 'body': 'Task A needs validation.',
            'paths': ['code.txt'], 'event_id': 'task-a-checkpoint',
        })['memory']
        other = LocalBridge(self.fixture.root, config=self.bridge.config)
        self.assertNotEqual(self.bridge.session, other.session)
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
            'name': 'save_checkpoint', 'arguments': {
                'title': 'Task B replaces task A', 'body': 'Task A abandoned.',
                'paths': ['code.txt'], 'event_id': 'task-b-checkpoint',
                'session': original['session'], 'supersedes_id': original['id'],
            },
        }}
        output = io.StringIO()
        serve_mcp(other, io.StringIO(json.dumps(request) + '\n'), output)
        result = json.loads(output.getvalue())['result']
        self.assertTrue(result.get('isError'),
                        'Model-supplied session impersonated another task and revised its checkpoint')
        recalled = self.bridge.call('recall', {})
        self.assertIn(original['id'], [m['id'] for m in recalled['checkpoints']])

    def test_concurrent_first_sync_retries_preserve_one_branch_identity(self):
        git(self.fixture.root, 'switch', '-c', 'concurrent-first-sync')
        observation = self.bridge.observe(['code.txt'])
        barrier = threading.Barrier(4)

        def send(_):
            barrier.wait(timeout=5)
            return self.bridge.request('sync', observation)

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(send, range(4)))
        self.assertEqual(len({r['branch_id'] for r in responses}), 1)
        self.assertEqual(len({r['context_id'] for r in responses}), 1)

    def test_same_second_same_head_ref_recreation_does_not_reuse_identity(self):
        with patch.dict(os.environ, {'GIT_COMMITTER_DATE': '2026-01-01T00:00:00+0000'}):
            git(self.fixture.root, 'switch', '-c', 'same-reflog')
            original = self.bridge.sync(['code.txt'])
            log = Path(git(self.fixture.root, 'rev-parse', '--path-format=absolute',
                           '--git-path', 'logs/refs/heads/same-reflog'))
            first_line = log.read_bytes().splitlines()[0]
            saved = self.bridge.call('finding', {
                'title': 'Original ref incarnation only', 'body': 'Keep this branch-local.',
                'paths': ['code.txt'], 'event_id': 'old-ref-incarnation',
            })['memory']
            git(self.fixture.root, 'switch', 'main')
            git(self.fixture.root, 'branch', '-D', 'same-reflog')
            git(self.fixture.root, 'switch', '-c', 'same-reflog')
            self.assertEqual(first_line, log.read_bytes().splitlines()[0],
                             'Fixture must reproduce an identical Git reflog birth line')
            replacement = self.bridge.sync(['code.txt'])
        self.assertNotEqual(original['branch_id'], replacement['branch_id'])
        self.assertNotIn(saved['id'], [m['id'] for m in self.bridge.call('recall', {})['findings']])

    def test_source_edit_after_hash_stage_is_rejected_or_reobserved(self):
        original_git = git

        def change_after_hash(root, *args, **kwargs):
            if args and args[0] == 'status':
                (self.fixture.root / 'code.txt').write_text('Changed after source hashing.\n')
            return original_git(root, *args, **kwargs)

        try:
            with patch('hivemind.bridge.git', side_effect=change_after_hash):
                observation = self.bridge.observe(['code.txt'])
        except ValueError as exc:
            self.assertRegex(str(exc).lower(), 'chang|retry|observ')
            return
        current = self.bridge.observe(['code.txt'])
        self.assertEqual(observation['sources'], current['sources'],
                         'Bridge returned old source hashes mixed with the new working-tree status')

    def test_private_file_text_and_path_metadata_do_not_enter_retry_payload(self):
        private = self.fixture.root / 'private'
        private.mkdir()
        canary = 'SYNTHETIC_PRIVATE_PLAN_CANARY_2026'
        (private / 'plan.txt').write_text(canary)
        self.bridge.config['private_paths'] = ['private/**']
        self.assertNotIn('private/plan.txt', self.bridge.observe(['private/plan.txt'])['sources'])
        with patch.object(self.bridge, 'request', side_effect=URLError('synthetic outage')):
            try:
                self.bridge.call('finding', {
                    'title': 'Decision from private/plan.txt', 'body': canary,
                    'classification': 'decision', 'paths': [], 'event_id': 'private-path-text',
                })
            except ValueError:
                pass
        with self.bridge.db() as db:
            persisted = json.dumps(db.execute('SELECT action,payload FROM outbox').fetchall())
        self.assertFalse(canary in persisted, 'Configured private file contents entered retry storage')
        self.assertFalse('private/plan.txt' in persisted, 'Configured private path metadata entered retry storage')

    def test_permanent_delivery_rejection_is_durably_marked(self):
        # A previously queued request can become invalid under a later policy,
        # authorization change, or conflicting replay. Quarantine it durably.
        self.bridge.enqueue('finding', {
            'context_id': self.bridge.get('context')['context_id'],
            'title': 'Queued observation', 'body': 'Synthetic queued observation.',
            'paths': ['code.txt'], 'session': self.bridge.session,
            'event_id': 'permanently-rejected-delivery',
        })
        with patch.object(self.bridge, 'request', side_effect=ValueError('SYNTHETIC_PERMANENT_REJECTION')):
            try:
                self.bridge.flush()
            except ValueError:
                pass
        with self.bridge.db() as db:
            statuses = db.execute('SELECT status FROM outbox').fetchall()
        self.assertEqual(statuses, [('rejected',)],
                         'The exception rolled back quarantine and left a permanently failing request pending')

    def test_source_change_between_content_read_and_stat_cannot_bypass_privacy(self):
        source = self.fixture.root / 'code.txt'
        original_read = Path.read_bytes
        changed = False

        def change_after_read(path):
            nonlocal changed
            content = original_read(path)
            if path == source and not changed:
                changed = True
                path.write_text('api_key=SYNTHETIC_NOT_A_REAL_API_KEY_2026')
            return content

        try:
            with patch.object(Path, 'read_bytes', change_after_read):
                observation = self.bridge.observe(['code.txt'])
        except ValueError as exc:
            self.assertRegex(str(exc).lower(), 'chang|retry|observ')
            return
        self.assertNotIn('code.txt', observation['sources'],
                         'Credential-bearing source was hashed after checking different public bytes')

    def _private_capture_fixture(self):
        directory = self.fixture.root / 'private'
        directory.mkdir()
        canary = 'SYNTHETIC_PRIVATE_CANARY_NO_TOKEN_PATTERN_2026'
        source = directory / 'plan.txt'
        source.write_text(canary)
        self.bridge.config['private_paths'] = ['private/**']
        return source, canary

    def _assert_text_stays_private_online_and_offline(self, body, event):
        for offline in (False, True):
            with self.subTest(delivery='offline' if offline else 'online'):
                payload = {'title': 'Private capture boundary test', 'body': body,
                           'classification': 'decision', 'paths': [],
                           'event_id': event + ('-offline' if offline else '-online')}
                rejected = False
                try:
                    if offline:
                        with patch.object(self.bridge, 'request', side_effect=URLError('synthetic outage')):
                            self.bridge.call('finding', payload)
                    else:
                        self.bridge.call('finding', payload)
                except ValueError:
                    rejected = True
                if offline:
                    with self.bridge.db() as db:
                        captured = [json.loads(raw) for (raw,) in
                                    db.execute("SELECT payload FROM outbox WHERE action='finding'").fetchall()]
                    present = any(p.get('body') == body for p in captured)
                    self.assertFalse(present, 'Private text entered the offline retry payload')
                else:
                    records = self.fixture.runtime.store.nodes('GitRecord')
                    present = any(n.kind == 'finding' and n.data.get('body') == body for n in records)
                    self.assertFalse(present, 'Private text reached the shared memory graph')
                self.assertTrue(rejected, 'Excluded private text should be rejected visibly')

    def test_windows_private_path_reference_cannot_enter_captures(self):
        self._private_capture_fixture()
        self._assert_text_stays_private_online_and_offline(
            r'Please preserve the rule in private\plan.txt', 'windows-private-reference')

    def test_absolute_private_path_reference_cannot_enter_captures(self):
        source, _ = self._private_capture_fixture()
        self._assert_text_stays_private_online_and_offline(
            'Please preserve the rule in ' + str(source), 'absolute-private-reference')

    def test_private_canary_content_without_path_cannot_enter_captures(self):
        _, canary = self._private_capture_fixture()
        self._assert_text_stays_private_online_and_offline(canary, 'private-content-no-reference')

    def test_same_size_source_edit_with_preserved_mtime_is_not_a_coherent_snapshot(self):
        source = self.fixture.root / 'code.txt'
        before = source.stat()
        original_git = git
        changed = False

        def preserving_metadata_edit(root, *args, **kwargs):
            nonlocal changed
            if args and args[0] == 'status' and not changed:
                changed = True
                source.write_bytes(source.read_bytes().replace(b'bounded', b'unbound'))
                os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
            return original_git(root, *args, **kwargs)

        try:
            with patch('hivemind.bridge.git', side_effect=preserving_metadata_edit):
                observation = self.bridge.observe(['code.txt'])
        except ValueError as exc:
            self.assertRegex(str(exc).lower(), 'chang|retry|observ')
            return
        current = self.bridge.observe(['code.txt'])
        self.assertEqual(observation['sources'], current['sources'],
                         'Metadata-preserving edit evaded validation and returned old source hashes')


if __name__ == '__main__':
    unittest.main()
