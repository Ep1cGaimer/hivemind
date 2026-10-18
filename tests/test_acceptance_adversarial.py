"""Independent acceptance probes; no model calls or existing graph resets.

Expected outcomes come from goal.md, not from the implementation's output.
The optional live class uses a unique new graph and never clears a graph.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hivemind.auth import AuthManager
from hivemind.bridge import LocalBridge, git, history_mapping
from hivemind.store import InMemoryGraphStore, StoreError
import test_git_memory
import test_git_bridge_http


class AdversarialCoreTests(unittest.TestCase):
    def make_store(self):
        return InMemoryGraphStore()

    def setUp(self):
        self.fixture = test_git_memory.GitFixture()
        self.fixture.make_store = self.make_store
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_failed_partial_source_save_is_not_visible_as_verified(self):
        """G5/D14/E3: an interrupted two-source claim cannot become one-source truth."""
        f = self.fixture
        f.commit('Second required source', 'second.txt', 'Both files constrain this claim.\n')
        ctx = f.sync()
        args = dict(context_id=ctx['context_id'], title='Two required sources',
                    body='Both guide.txt and second.txt are required for this finding.',
                    paths=['guide.txt', 'second.txt'], session='fault-writer',
                    event_id='interrupted-two-source-save')
        original = f.store.add_edge
        source_writes = 0

        def crash_on_second_source(kind, *positional, **kwargs):
            nonlocal source_writes
            if kind == 'SUPPORTED_BY':
                source_writes += 1
                if source_writes == 2:
                    raise StoreError('Injected interruption before second source relationship')
            return original(kind, *positional, **kwargs)

        with patch.object(f.store, 'add_edge', side_effect=crash_on_second_source):
            rejected = f.service.operation(f.owner, f.project, 'finding', args)
        self.assertFalse(rejected['ok'])
        self.assertEqual(rejected['error']['code'], 'STORAGE_UNAVAILABLE')
        incomplete_recall = f.recall(ctx)
        # A Git synchronization can run while capture waits for its retry. It
        # must not publish an inactive, partially linked record from list(kind).
        f.commit('Commit while interrupted capture waits', 'unrelated.txt', 'Unrelated authored successor.\n')
        advanced = f.sync()
        after_sync_recall = f.recall(advanced)
        replayed = f.service.operation(f.owner, f.project, 'finding', args)
        self.assertTrue(replayed['ok'], replayed)
        memory_id = replayed['memory']['id']
        self.assertEqual(len(f.service.graph(f.project, f.repo).links('SUPPORTED_BY', from_id=memory_id)), 2)
        for stage, recalled in [('immediate', incomplete_recall), ('after_git_sync', after_sync_recall)]:
            with self.subTest(stage=stage):
                partial = next((m for m in recalled['findings'] if m['id'] == memory_id), None)
                self.assertTrue(partial is None or partial['applicability'] != 'applicable',
                                'An unacknowledged partial save appeared as applicable before retry repaired its required sources')

    def test_reset_source_branch_does_not_publish_abandoned_commit_learning(self):
        """D7/D9: integrating C must not inherit a finding observed only on abandoned B."""
        f = self.fixture
        git(f.root, 'switch', '-c', 'feature-reset')
        f.commit('Abandoned implementation B', 'abandoned.txt', 'B was investigated.\n')
        source = f.sync()
        memory = f.save(source, event='abandoned-B', body='The abandoned implementation B has this constraint.')
        git(f.root, 'reset', '--hard', 'main')
        f.commit('Replacement implementation C', 'replacement.txt', 'C replaces B.\n')
        replacement = f.sync()
        self.assertNotEqual(replacement['head'], source['head'])
        self.assertNotIn(source['head'], git(f.root, 'rev-list', replacement['head']).splitlines())
        git(f.root, 'switch', 'main')
        f.sync()
        git(f.root, 'merge', '--ff-only', 'feature-reset')
        integrated = f.sync()
        self.assertNotIn(memory['id'], f.ids(f.recall(integrated)),
                         'Matching unchanged source text must not publish learning from an unintegrated abandoned commit')

    def test_cherry_pick_transfers_only_uniquely_mapped_commit_learning(self):
        """D10: replaying C does not import a separate finding authored at B."""
        f = self.fixture
        git(f.root, 'switch', '-c', 'cherry-source')
        f.commit('Unpicked B', 'unpicked.txt', 'B remains outside destination history.\n')
        b_context = f.sync()
        unpicked = f.save(b_context, event='unpicked-B')
        f.commit('Picked C', 'picked.txt', 'C is the only replayed commit.\n')
        c_context = f.sync()
        picked = f.save(c_context, event='picked-C')
        git(f.root, 'switch', 'main')
        f.commit('Independent destination commit', 'main.txt', 'Destination diverges.\n')
        f.sync()
        git(f.root, 'cherry-pick', c_context['head'])
        destination_head = git(f.root, 'rev-parse', 'HEAD')
        self.assertNotIn(b_context['head'], git(f.root, 'rev-list', destination_head).splitlines())
        mapping = history_mapping(f.root, {'id': c_context['context_id'], 'head': c_context['head']}, destination_head)
        destination = f.sync(mappings=[mapping])
        ids = f.ids(f.recall(destination))
        self.assertIn(picked['id'], ids)
        self.assertNotIn(unpicked['id'], ids)

    def test_linked_worktrees_have_separate_snapshots_and_branch_context(self):
        """B5/D1/D4: Git's common directory must not collapse worktree state."""
        f = self.fixture
        linked = Path(f.temp.name) / 'linked'
        git(f.root, 'worktree', 'add', '-b', 'linked-feature', str(linked))
        other = LocalBridge(linked, config={**f.bridge.config, 'connector_id': 'linked-fixture'})
        self.assertNotEqual(other.directory, f.bridge.directory)
        (linked / 'guide.txt').write_text('Unfinished linked-worktree guide.\n')
        observation = other.observe(['guide.txt'])
        result = f.service.sync(f.owner, f.project, observation)
        self.assertTrue(result['ok'], result)
        memory = f.save(result, event='linked-only')
        self.assertNotEqual(result['branch_id'], f.main['branch_id'])
        self.assertNotEqual(result['snapshot_id'], f.main['snapshot_id'])
        self.assertNotIn(memory['id'], f.ids(f.recall(f.main)))
        self.assertIn(memory['id'], f.ids(f.recall(result)))

    def test_partial_required_source_change_never_reports_fully_applicable(self):
        """D14/E3: one unchanged required source cannot mask another changed one."""
        f = self.fixture
        f.commit('Second source', 'second.txt', 'Required source version one.\n')
        f.sync()
        memory = f.save(event='two-source-baseline', paths=['guide.txt', 'second.txt'])
        f.commit('Change only second required source', 'second.txt', 'Required source version two.\n')
        ctx = f.sync()
        current = next(m for m in f.recall(ctx)['findings'] if m['id'] == memory['id'])
        self.assertEqual(current['source_count'], 2)
        self.assertEqual(current['source_matches'], 1)
        self.assertEqual(current['applicability'], 'historical_source_changed')

    def test_source_relationship_ablation_cannot_turn_partial_support_into_truth(self):
        """E3/E5: keep facts/metadata, remove one actual required support relationship."""
        f = self.fixture
        f.commit('Second ablation source', 'second.txt', 'Second required source.\n')
        ctx = f.sync()
        memory = f.save(event='support-edge-ablation', paths=['guide.txt', 'second.txt'])
        graph = f.service.graph(f.project, f.repo)
        support = graph.links('SUPPORTED_BY', from_id=memory['id'])
        self.assertEqual(len(support), 2)
        removed_source = support[0][1]
        if getattr(f.store, 'backend_name', '') == 'falkordb':
            f.store._graph.query(
                'MATCH (m:GitRecord)-[r:SUPPORTED_BY]->(s:GitRecord) '
                'WHERE m.workspace_project_id=$project AND m.repo_id=$repo AND m.id=$memory AND s.id=$source DELETE r',
                {'project': f.project, 'repo': f.repo, 'memory': memory['id'], 'source': removed_source})
        else:
            f.store._edges = {key: edge for key, edge in f.store._edges.items()
                              if not (edge.edge_type == 'SUPPORTED_BY' and edge.from_id == memory['id']
                                      and edge.to_id == removed_source)}
        self.assertIsNotNone(graph.get(memory['id']))
        self.assertIsNotNone(graph.get(removed_source))
        self.assertEqual(len(graph.get(memory['id']).data['paths']), 2)
        current = next((m for m in f.recall(ctx)['findings'] if m['id'] == memory['id']), None)
        self.assertTrue(current is None or current['applicability'] != 'applicable',
                        'Deleting a required support edge made partial evidence appear fully applicable')

    def test_lf_crlf_checkouts_share_canonical_source_identity(self):
        """D20 (line endings only): Git's explicit text rule defines identity."""
        f = self.fixture
        f.commit('Declare canonical line endings', '.gitattributes', 'guide.txt text eol=lf\n')
        f.sync()
        source = f.root / 'guide.txt'
        text = b'Validate the reserved queue before release.\n'
        source.write_bytes(text)
        lf = f.bridge.observe(['guide.txt'])
        source.write_bytes(text.replace(b'\n', b'\r\n'))
        crlf = f.bridge.observe(['guide.txt'])
        self.assertEqual(lf['sources']['guide.txt'], crlf['sources']['guide.txt'])
        head_sources = next(c['sources'] for c in crlf['commits'] if c['oid'] == crlf['head'])
        self.assertEqual(head_sources['guide.txt'], crlf['sources']['guide.txt'])


class AuthenticationStartupRaceTests(unittest.TestCase):
    def test_concurrent_first_startup_converges_on_durable_signing_secret(self):
        """G4/G7: concurrent services sharing a new durable store can both start."""
        store = InMemoryGraphStore()
        get_node = store.get_node
        gate = threading.Barrier(2)

        def both_read_absent(key):
            value = get_node(key)
            if key == 'auth:signing-secret' and value is None:
                gate.wait(timeout=5)
            return value

        def start():
            try:
                return AuthManager({'HIVEMIND_USERS': 'owner=pw'}, store=store)
            except Exception as exc:
                return exc

        with patch.object(store, 'get_node', side_effect=both_read_absent):
            with ThreadPoolExecutor(max_workers=2) as pool:
                starts = list(pool.map(lambda _: start(), range(2)))
        self.assertTrue(all(isinstance(result, AuthManager) for result in starts),
                        'Concurrent first startup rejected one process: ' + repr(starts))
        self.assertEqual(starts[0].secret, starts[1].secret)


class PrivateBasenameTests(unittest.TestCase):
    def test_configured_private_root_basename_stays_out_of_graph_and_retry_payload(self):
        """F6: a private filename is excluded metadata even without a slash."""
        f = test_git_bridge_http.BridgeHTTPTests()
        f.setUp()
        self.addCleanup(f.tearDown)
        bridge = f.bridge
        bridge.sync(['code.txt'])
        (f.root / 'plan.txt').write_text('SYNTHETIC PRIVATE BODY NOT COPIED INTO THE CLAIM 2026')
        bridge.config['private_paths'] = ['plan.txt']
        for offline in (False, True):
            with self.subTest(offline=offline):
                body = 'Follow plan.txt before doing the release. Delivery offline=' + str(offline) + '.'
                error = None
                payload = dict(title='Private basename reference', body=body, paths=[],
                               classification='decision', event_id='basename-' + str(offline))
                try:
                    if offline:
                        with patch.object(bridge, 'request', side_effect=URLError('Injected outage')):
                            bridge.call('finding', payload)
                    else:
                        bridge.call('finding', payload)
                except ValueError as exc:
                    error = exc
                with bridge.db() as db:
                    queued = db.execute("SELECT payload FROM outbox WHERE action='finding'").fetchall()
                graph_text = [n.data.get('body') for n in f.runtime.store.nodes('GitRecord') if n.kind == 'finding']
                # Collect both persistence surfaces before the expected assertion,
                # so the failing test reports the full privacy boundary.
                self.assertFalse(body in graph_text or any(body in raw for (raw,) in queued),
                                 'Configured private basename reached graph or retry payload')
                self.assertIsNotNone(error, 'Private filename references must fail before delivery')


class BoundaryHTTPTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_git_bridge_http.BridgeHTTPTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def request(self, path, token, payload=None, cookie=None):
        headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
        if cookie:
            headers['Cookie'] = cookie
        request = Request(self.fixture.base + path,
                          data=None if payload is None else json.dumps(payload).encode(), headers=headers)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    def test_project_token_cannot_distinguish_foreign_project_existence(self):
        """F1/F9: foreign existing and absent IDs get the same authorization result."""
        f = self.fixture
        other = f.runtime.projects.create_project(f.owner, 'Foreign private project')['project']['id']
        for suffix, payload in [('', None), ('/git/overview', None), ('/graph', None),
                                ('/memories', None), ('/git/explain', {'memory_id': 'private-id'}),
                                ('/git/sync', {}), ('/memories', {'title': 'Attempt', 'body': 'Attempt'})]:
            with self.subTest(suffix=suffix, mutation=payload is not None):
                real = self.request('/api/projects/' + other + suffix, f.token, payload)
                absent = self.request('/api/projects/project:absent-audit-fixture' + suffix, f.token, payload)
                self.assertEqual(real[0], 403)
                self.assertEqual(real, absent)
        _, listing = self.request('/api/projects', f.token)
        self.assertEqual([p['id'] for p in listing['projects']], [f.project])

    def test_viewer_write_aliases_and_agent_human_boundary_remain_closed(self):
        """F2/F4/F9: invalid payloads cannot bypass checks before validation."""
        f = self.fixture
        viewer = f.runtime.auth.login('viewer', 'pw')[1]
        token, _ = f.runtime.auth.create_agent_token(viewer, 'viewer boundary fixture', f.project)
        paths = ['/api/projects/' + f.project + '/git/' + operation for operation in
                 ('register', 'sync', 'finding', 'checkpoint', 'no-change', 'propose', 'accept')]
        paths += ['/api/projects/' + f.project + '/memories', '/api/memories',
                  '/api/projects/' + f.project + '/agents', '/api/agents', '/api/projects']
        for path in paths:
            with self.subTest(path=path):
                status, result = self.request(path, token, {'project_id': f.project})
                self.assertEqual(status, 403, result)
        session = f.runtime.auth.login('operator', 'pw')[0]
        # A bearer agent cannot become a human by including a human cookie or a
        # human=true payload alongside its own project-scoped authorization.
        status, result = self.request('/api/projects/' + f.project + '/git/accept', f.token,
                                      {'human': True}, 'hivemind_session=' + session)
        self.assertEqual(status, 403, result)

    def test_concurrent_bridge_tasks_preserve_their_own_checkpoint_revisions(self):
        """G4: two independent transports share SQLite without losing task checkpoints."""
        f = self.fixture
        f.bridge.sync(['code.txt'])
        bridges = [LocalBridge(f.root, config=f.bridge.config, session='parallel-task-' + str(i)) for i in range(2)]
        gate = threading.Barrier(2)

        def save(index, old=None):
            gate.wait(timeout=10)
            payload = dict(title='Parallel task ' + str(index), body='Run independent task validation.',
                           paths=['code.txt'], event_id='revised' if old else 'initial')
            if old:
                payload['supersedes_id'] = old[index]['memory']['id']
            return bridges[index].call('checkpoint', payload)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = list(pool.map(save, range(2)))
        with ThreadPoolExecutor(max_workers=2) as pool:
            second = list(pool.map(lambda index: save(index, first), range(2)))
        expected = {r['memory']['id'] for r in second}
        self.assertEqual(len(expected), 2)
        recalled = f.bridge.call('recall', {})
        self.assertEqual({m['id'] for m in recalled['checkpoints']}, expected)
        self.assertEqual({m['session'] for m in recalled['checkpoints']}, {b.session for b in bridges})


@unittest.skipUnless(os.environ.get('HIVEMIND_LIVE_TESTS') == '1', 'Explicit live audit opt-in required')
class AdversarialLiveCoreTests(AdversarialCoreTests):
    @classmethod
    def setUpClass(cls):
        cls.graph_name = 'hivemind_core_audit_' + secrets.token_hex(12)
        print('Independent live core audit graph: ' + cls.graph_name, flush=True)

    def make_store(self):
        from hivemind.backend import create_store
        return create_store({**os.environ, 'HIVEMIND_BACKEND': 'falkordb',
                             'FALKORDB_GRAPH': self.graph_name})


if __name__ == '__main__':
    unittest.main()
