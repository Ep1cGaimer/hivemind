"""Independent real-Git fixture; expectations never enter runtime inputs."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from hivemind.auth import AuthManager, Identity
from hivemind.bridge import LocalBridge, git, history_mapping, serve_mcp
from hivemind.client_adapters import hook, install
from hivemind.domain import GitRecord
from hivemind.git_memory import GitMemory
from hivemind.git_graph import RepositoryGraph
from hivemind.store import InMemoryGraphStore, ImmutableConflictError
from hivemind.workspace import ProjectWorkspace


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'fixture'
        self.root.mkdir()
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.email', 'fixture@example.test')
        git(self.root, 'config', 'user.name', 'Fixture')
        (self.root / 'guide.txt').write_text('Validate the reserved queue before release.\n')
        self.commit('Initial guide')
        self.store = self.make_store()
        self.auth = AuthManager({'HIVEMIND_USERS': 'owner=pw,editor=pw,viewer=pw'}, store=self.store)
        self.owner = Identity('owner', 'Owner')
        self.editor = Identity('editor', 'Editor')
        self.viewer = Identity('viewer', 'Viewer')
        self.projects = ProjectWorkspace(self.store, self.auth)
        self.project = self.projects.create_project(self.owner, 'Git fixture')['project']['id']
        self.projects.add_member(self.owner, self.project, 'editor', 'editor')
        self.projects.add_member(self.owner, self.project, 'viewer', 'viewer')
        self.service = GitMemory(self.store, self.projects)
        result = self.service.register(self.owner, self.project, {'remote': 'example.test/fixture', 'root_commit': git(self.root, 'rev-parse', 'HEAD')})
        self.repo = result['repo_id']
        self.bridge = LocalBridge(self.root, config={'repo_id': self.repo, 'project_id': self.project, 'url': 'http://unused', 'connector_id': 'fixture-local'})
        self.bridge.set('watched_paths', ['guide.txt'])
        self.main = self.sync()

    def make_store(self):
        return InMemoryGraphStore()

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, message, filename=None, text=None):
        if filename:
            (self.root / filename).write_text(text)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', message, '--allow-empty')
        return git(self.root, 'rev-parse', 'HEAD')

    def sync(self, **overrides):
        payload = self.bridge.observe(['guide.txt'])
        payload.update(overrides)
        result = self.service.sync(self.owner, self.project, payload)
        self.assertTrue(result.get('ok'), result)
        branches = self.bridge.get('branches', {})
        branches[payload['ref']] = result['branch_id']
        self.bridge.set('branches', branches)
        self.bridge.set('context', result)
        return result

    def save(self, ctx=None, event=None, session='writer', **kwargs):
        args = dict(context_id=(ctx or self.bridge.get('context'))['context_id'], title='Release prerequisite',
                    body='Validate the reserved queue before release; shared queues remain untested.', paths=['guide.txt'],
                    session=session, event_id=event or secrets.token_hex(8))
        args.update(kwargs)
        result = self.service.save(self.owner, self.project, args)
        self.assertTrue(result['ok'], result)
        return result['memory']

    def recall(self, ctx=None):
        return self.service.recall(self.owner, self.project, {'context_id': (ctx or self.bridge.get('context'))['context_id']})

    def ids(self, result):
        return {m['id'] for m in result['findings']}

    def test_same_commit_branches_and_same_branch_teammate_wip(self):
        git(self.root, 'switch', '-c', 'feature')
        feature = self.sync()
        memory = self.save(feature)
        self.assertIn(memory['id'], self.ids(self.recall(feature)))
        self.assertNotIn(memory['id'], self.ids(self.recall(self.main)))
        (self.root / 'guide.txt').write_text('Unfinished change on a teammate checkout.\n')
        teammate = self.sync(connector_id='teammate-123', previous_context=None)
        recalled = self.recall(teammate)
        self.assertEqual(recalled['findings'][0]['applicability'], 'wip_requires_verification')
        self.assertEqual(teammate['branch_id'], feature['branch_id'])

    def test_fast_forward_and_normal_merge_publish_once(self):
        git(self.root, 'switch', '-c', 'feature')
        feature = self.sync()
        first = self.save(feature)
        self.commit('Feature implementation', 'feature.txt', 'Implementation.\n')
        feature_tip = self.sync()
        second = self.save(feature_tip)
        git(self.root, 'switch', 'main')
        main_before = self.sync()
        self.assertNotIn(first['id'], self.ids(self.recall()))
        git(self.root, 'merge', '--ff-only', 'feature')
        merged = self.sync()
        self.assertTrue({first['id'], second['id']} <= self.ids(self.recall(merged)))
        explanation = self.service.explain(self.owner, self.project, {'context_id': merged['context_id'], 'memory_id': second['id']})
        self.assertTrue(explanation['inheritance_path'])
        # New learning at the old feature tip is not retroactively integrated.
        git(self.root, 'switch', 'feature')
        self.sync()
        later = self.save()
        git(self.root, 'switch', 'main')
        self.sync()
        self.assertNotIn(later['id'], self.ids(self.recall()))
        self.commit('Main diverges', 'main.txt', 'Main.\n')
        self.sync()
        git(self.root, 'switch', 'feature')
        self.commit('Feature advances', 'feature.txt', 'Next feature.\n')
        self.sync()
        normal = self.save()
        git(self.root, 'switch', 'main')
        self.sync()
        git(self.root, 'merge', '--no-ff', 'feature', '-m', 'Verified integration')
        merged = self.sync()
        self.assertIn(normal['id'], self.ids(self.recall(merged)))

    def test_immutable_scoped_revisions_conflicts_and_checkpoints(self):
        base = self.save(event='one')
        with self.assertRaises(TypeError):
            self.store.get_node(base['id']).data['body'] = 'Mutated audit record'
        self.assertEqual(base, self.save(event='one'))
        with self.assertRaises(ImmutableConflictError):
            self.save(event='one', body='Changed immutable event')
        git(self.root, 'switch', '-c', 'correction')
        ctx = self.sync()
        one = self.save(ctx, supersedes_id=base['id'], body='First qualified correction.')
        two = self.save(ctx, supersedes_id=base['id'], body='Conflicting correction.')
        recalled = self.recall(ctx)
        self.assertEqual(self.ids(recalled), {one['id'], two['id']})
        self.assertEqual(len(recalled['conflicts']), 1)
        self.assertIn(base['id'], self.ids(self.recall(self.main)))
        for session in ('task-a', 'task-b'):
            args = dict(context_id=ctx['context_id'], title=session, body='Work remains; next run validation.', paths=[], session=session, event_id='checkpoint')
            result = self.service.save(self.owner, self.project, args, checkpoint=True)
            self.assertTrue(result['ok'], result)
        self.assertEqual(len(self.recall(ctx)['checkpoints']), 2)

    def test_concurrent_delivery_is_one_revision_and_concurrent_edits_conflict(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            repeated = list(pool.map(lambda _: self.save(event='duplicate'), range(2)))
        self.assertEqual(repeated[0]['id'], repeated[1]['id'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            revisions = list(pool.map(lambda i: self.save(event='edit-' + str(i), supersedes_id=repeated[0]['id'], body='Concurrent interpretation ' + str(i)), range(2)))
        result = self.recall()
        self.assertEqual(self.ids(result), {m['id'] for m in revisions})
        self.assertEqual(len(result['conflicts']), 1)

    def test_sources_change_without_erasing_history_and_shallow_coverage(self):
        memory = self.save()
        self.commit('Change source', 'guide.txt', 'New guidance replaces old behavior.\n')
        current = self.sync(history_complete=False, shallow=True)
        result = self.recall(current)
        self.assertEqual(result['findings'][0]['applicability'], 'historical_source_changed')
        self.assertFalse(result['completeness']['history_complete'])
        self.assertIsNotNone(self.store.get_node(memory['id']))

    def test_rebase_and_squash_require_matching_sources_and_unique_mapping(self):
        git(self.root, 'switch', '-c', 'feature')
        self.commit('Feature A', 'feature.txt', 'A\n')
        source = self.sync()
        memory = self.save()
        source_record = self.store.get_node(source['context_id'])
        source_data = {'id': source_record.id, 'head': source_record.head}
        git(self.root, 'switch', 'main')
        self.commit('Unrelated main', 'main.txt', 'main\n')
        self.sync()
        git(self.root, 'switch', 'feature')
        git(self.root, 'rebase', 'main')
        mapping = history_mapping(self.root, source_data, git(self.root, 'rev-parse', 'HEAD'))
        rebased = self.sync(mappings=[mapping])
        self.assertIn(memory['id'], self.ids(self.recall(rebased)))
        self.assertTrue(any(t['status'] == 'published' for t in rebased['transfers']))
        git(self.root, 'switch', '-c', 'squash-source', 'main')
        self.commit('Squash A', 'a.txt', 'a\n')
        self.commit('Squash B', 'b.txt', 'b\n')
        source = self.sync()
        squashed_memory = self.save()
        git(self.root, 'switch', 'main')
        self.sync()
        git(self.root, 'merge', '--squash', 'squash-source')
        self.commit('Aggregate feature')
        mapping = history_mapping(self.root, {'id': source['context_id'], 'head': source['head']}, git(self.root, 'rev-parse', 'HEAD'))
        self.assertEqual(mapping['method'], 'squash')
        integrated = self.sync(mappings=[mapping])
        self.assertIn(squashed_memory['id'], self.ids(self.recall(integrated)))

    def test_promotion_needs_human_and_preserves_conditions(self):
        memory = self.save()
        args = {'context_id': self.main['context_id'], 'memory_id': memory['id']}
        self.assertTrue(self.service.operation(self.owner, self.project, 'propose', args)['ok'])
        self.assertEqual(self.service.operation(self.owner, self.project, 'accept', args)['error']['code'], 'FORBIDDEN')
        self.assertTrue(self.service.operation(self.owner, self.project, 'accept', args, human=True)['ok'])
        git(self.root, 'switch', '-c', 'other')
        other = self.sync()
        self.assertEqual(self.recall(other)['findings'][0]['collection'], 'conventions')
        self.assertIn('shared queues remain untested', self.recall(other)['findings'][0]['body'])

    def test_permissions_revocation_and_model_context_rejection(self):
        token, record = self.auth.create_agent_token(self.viewer, 'viewer client', self.project)
        restarted = AuthManager({'HIVEMIND_USERS': 'owner=pw,editor=pw,viewer=pw'}, store=self.store)
        self.assertIsNotNone(restarted.authenticate_agent_context(token))
        self.assertFalse(self.service.operation(self.viewer, self.project, 'finding', {'context_id': self.main['context_id']})['ok'])
        self.auth.revoke(self.owner, record.token_id, self.project)
        self.assertIsNone(restarted.authenticate_agent_context(token))
        messages = io.StringIO(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'recall_context', 'arguments': {'branch': 'main'}}}) + '\n')
        output = io.StringIO()
        serve_mcp(self.bridge, messages, output)
        self.assertTrue(json.loads(output.getvalue())['result']['isError'])

    def test_hooks_continue_once_and_do_not_capture_transcripts(self):
        with patch.object(self.bridge, 'call', return_value={'ok': True, 'context_id': 'ctx'}):
            for client in ('codex', 'claude'):
                session = client + '-session'
                start = hook(self.bridge, client, {'hook_event_name': 'UserPromptSubmit', 'session_id': session, 'prompt': 'Ordinary task'})
                self.assertEqual(start['hookSpecificOutput']['hookEventName'], 'UserPromptSubmit')
                first = hook(self.bridge, client, {'hook_event_name': 'Stop', 'session_id': session})
                self.assertEqual(first['decision'], 'block')
                again = hook(self.bridge, client, {'hook_event_name': 'Stop', 'session_id': session, 'stop_hook_active': True})
                self.assertNotIn('decision', again)
                self.assertIn('systemMessage', again)
        with patch('hivemind.client_adapters.shutil.which', return_value=None):
            installed = install(self.bridge, 'both')
        self.assertEqual(len(installed), 2)
        config = json.loads((self.root / '.claude/settings.local.json').read_text())
        self.assertEqual(set(config['hooks']), {'SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop'})

    def test_private_paths_and_credentials_are_excluded(self):
        (self.root / '.env').write_text('PASSWORD=secretstuff')
        self.assertFalse(self.bridge.allowed('.env'))
        self.assertFalse(self.bridge.allowed('../outside.txt'))
        rejected = self.service.operation(self.owner, self.project, 'finding', dict(context_id=self.main['context_id'], title='Secret', body='api_key=shouldneverbesaved', paths=['guide.txt'], event_id='secret', session='s'))
        self.assertEqual(rejected['error']['code'], 'PRIVATE_CONTENT')

    def test_relationship_ablation_removes_inheritance_explanation(self):
        git(self.root, 'switch', '-c', 'feature')
        self.sync()
        self.commit('Feature', 'feature.txt', 'Feature\n')
        self.sync()
        memory = self.save()
        git(self.root, 'switch', 'main')
        self.sync()
        git(self.root, 'merge', '--ff-only', 'feature')
        integrated = self.sync()
        self.assertIn(memory['id'], self.ids(self.recall()))
        self.store._edges = {k: e for k, e in self.store._edges.items() if e.edge_type not in {'PUBLISHES', 'PARENT'}}
        self.assertNotIn(memory['id'], self.ids(self.recall()))
        result = self.service.explain(self.owner, self.project, {'context_id': integrated['context_id'], 'memory_id': memory['id']})
        self.assertIsNone(result['inheritance_path'])

    def test_ambiguous_mapping_stays_local_and_ref_recreation_keeps_history(self):
        git(self.root, 'switch', '-c', 'feature')
        self.commit('Feature change', 'feature.txt', 'Feature\n')
        source = self.sync()
        memory = self.save()
        git(self.root, 'switch', 'main')
        self.commit('Destination change', 'main.txt', 'Main\n')
        self.sync()
        git(self.root, 'cherry-pick', source['head'])
        mapping = history_mapping(self.root, {'id': source['context_id'], 'head': source['head']}, git(self.root, 'rev-parse', 'HEAD'))
        self.assertTrue(mapping['entries'])
        for entry in mapping['entries']:
            entry['new_matches'] = 2
        destination = self.sync(mappings=[mapping])
        self.assertNotIn(memory['id'], self.ids(self.recall(destination)))
        self.assertTrue(any(t['status'] == 'needs_review' for t in destination['transfers']))
        git(self.root, 'branch', '-D', 'feature')
        self.bridge.observe()
        git(self.root, 'switch', '-c', 'feature')
        recreated = self.sync()
        self.assertNotEqual(recreated['branch_id'], source['branch_id'])
        self.assertIsNotNone(self.store.get_node(memory['id']))

    def test_real_shallow_clone_can_deepen_without_rewriting_commit_metadata(self):
        for i in range(2):
            self.commit('History ' + str(i), 'history.txt', str(i) + '\n')
        clone = Path(self.temp.name) / 'shallow'
        subprocess.run(['git', 'clone', '--depth', '1', self.root.as_uri(), str(clone)], check=True, capture_output=True)
        bridge = LocalBridge(clone, config={**self.bridge.config, 'connector_id': 'shallow-fixture'})
        first = self.service.sync(self.owner, self.project, bridge.observe(['guide.txt']))
        self.assertTrue(first['ok'], first)
        self.assertFalse(first['completeness']['history_complete'])
        bridge.set('branches', {'refs/heads/main': first['branch_id']})
        bridge.set('context', first)
        git(clone, 'fetch', '--unshallow')
        second = self.service.sync(self.owner, self.project, bridge.observe(['guide.txt']))
        self.assertTrue(second['ok'], second)
        self.assertTrue(second['completeness']['history_complete'])

    def test_context_budget_includes_metadata_and_explicit_exclusions(self):
        for i in range(10):
            self.save(title='Queue detail ' + str(i), body='Qualified queue observation. ' * 80)
        recalled = self.recall()
        self.assertLessEqual(len(json.dumps(recalled, ensure_ascii=False)), 8000)
        self.assertLessEqual(len(recalled['findings']), 8)
        self.assertTrue(recalled['completeness']['context_truncated'])
        self.assertGreater(recalled['exclusion_counts']['context_budget'], 0)


if __name__ == '__main__':
    unittest.main()
