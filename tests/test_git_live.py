"""Run the independent Git contract against the pinned FalkorDB server."""
import os
import unittest
import test_git_memory
from hivemind.backend import create_store


@unittest.skipUnless(os.environ.get('HIVEMIND_LIVE_TESTS') == '1', 'Set HIVEMIND_LIVE_TESTS=1 and isolated FALKORDB_* settings')
class GitFalkorDBTests(test_git_memory.GitFixture):
    def make_store(self):
        return create_store({**os.environ, 'HIVEMIND_BACKEND': 'falkordb'})

    def test_synthetic_merge_dag_uses_reachability_without_counting_all_paths(self):
        """Synthetic graph history: 79 commits, 2**26 ancestry routes.

        This exercises real FalkorDB retrieval, not real Git merge observation.
        A source-supported base publication must be inherited at the final tip;
        unrelated and unpublished branch findings must retain their scopes.
        """
        import hashlib
        import secrets

        memory = self.save(self.main, event='synthetic-dag-base-publication')
        graph = self.service.graph(self.project, self.repo)
        base_id = self.service.commit_id(self.project, self.repo, self.main['head'])
        previous = graph.get(base_id)
        self.service.edge('PUBLISHES', base_id, memory['id'], reason='synthetic_live_regression')
        run = secrets.token_hex(8)

        def oid(label):
            return hashlib.sha1((run + label).encode()).hexdigest()

        for depth in range(26):
            left_oid, right_oid, merge_oid = [oid(str(depth) + part) for part in ('left', 'right', 'merge')]
            left = self.service.record(self.project, self.repo, 'commit', left_oid,
                                       {'oid': left_oid, 'parents': [previous.head]}, head=left_oid)
            right = self.service.record(self.project, self.repo, 'commit', right_oid,
                                        {'oid': right_oid, 'parents': [previous.head]}, head=right_oid)
            merged = self.service.record(self.project, self.repo, 'commit', merge_oid,
                                         {'oid': merge_oid, 'parents': [left_oid, right_oid]}, head=merge_oid)
            self.service.edge('PARENT', left, previous)
            self.service.edge('PARENT', right, previous)
            self.service.edge('PARENT', merged, left)
            self.service.edge('PARENT', merged, right)
            previous = merged

        branch = self.service.record(self.project, self.repo, 'branch', 'synthetic-consumer-' + run,
                                      {'initial_ref': 'refs/heads/synthetic-consumer', 'initial_head': previous.head})
        original_snapshot = graph.get(self.main['snapshot_id'])
        snapshot = self.service.record(self.project, self.repo, 'snapshot', 'synthetic-consumer-' + run,
                                       dict(original_snapshot.data), head=previous.head)
        for _, source_id, _ in graph.links('HAS_SOURCE', from_id=original_snapshot.id):
            self.service.edge('HAS_SOURCE', snapshot, source_id)
        observation = self.service.record(self.project, self.repo, 'observation', 'synthetic-consumer-' + run,
            {'connector_id': 'synthetic-consumer-connector', 'ref': 'refs/heads/synthetic-consumer',
             'history_complete': True, 'manifest_complete': True, 'shallow': False, 'previous_context': None},
            branch=branch.id, head=previous.head, snapshot=snapshot.id, author=self.owner.user_id)
        self.service.edge('OBSERVED', branch, observation)
        self.service.edge('AT_COMMIT', observation, previous)
        context = {'context_id': observation.id}

        recalled = self.recall(context)
        inherited = next(m for m in recalled['findings'] if m['id'] == memory['id'])
        self.assertEqual(inherited['applicability'], 'applicable')
        self.assertEqual(inherited['collection'], 'inherited')
        explanation = self.service.explain(self.owner, self.project,
                                            {'context_id': observation.id, 'memory_id': memory['id']})
        path = explanation['inheritance_path']
        self.assertEqual(len(path), 54)
        self.assertEqual(path[0], previous.id)
        self.assertEqual(path[-1], memory['id'])
        for index, (start, end) in enumerate(zip(path, path[1:])):
            edge_type = 'PUBLISHES' if index == len(path) - 2 else 'PARENT'
            self.assertTrue(graph.links(edge_type, from_id=start, to_id=end))

        # Publication existence must handle both a zero-length ancestry path and
        # NULL publication endpoints without dropping branch-local candidates.
        self.assertEqual(graph.path(base_id, base_id), [base_id])
        local = self.save(context, event='synthetic-branch-only', session='synthetic-consumer')
        self.assertIn(local['id'], self.ids(self.recall(context)))
        local_explanation = self.service.explain(self.owner, self.project,
                                                 {'context_id': observation.id, 'memory_id': local['id']})
        self.assertIsNone(local_explanation['inheritance_path'])
        self.assertTrue(local_explanation['branch_path'])

        excluded = self.save(self.main, event='synthetic-unreachable-publication')
        unrelated_oid = oid('unrelated')
        unrelated = self.service.record(self.project, self.repo, 'commit', unrelated_oid,
                                        {'oid': unrelated_oid, 'parents': []}, head=unrelated_oid)
        self.service.edge('PUBLISHES', unrelated, excluded['id'], reason='synthetic_unreachable_publication')
        self.assertNotIn(excluded['id'], self.ids(self.recall(context)))

    def test_relationship_ablation_removes_inheritance_explanation(self):
        from hivemind.bridge import git
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
        # This fixture owns a newly created project in the explicitly selected test
        # graph. Removing relationships retains all facts/metadata for the ablation.
        self.store._graph.query('MATCH (a:GitRecord)-[r:PARENT|PUBLISHES]->(b:GitRecord) WHERE a.workspace_project_id=$p AND a.repo_id=$repo DELETE r', {'p': self.project, 'repo': self.repo})
        self.assertNotIn(memory['id'], self.ids(self.recall()))
        explanation = self.service.explain(self.owner, self.project, {'context_id': integrated['context_id'], 'memory_id': memory['id']})
        self.assertIsNone(explanation['inheritance_path'])

    def test_restart_preserves_memory_and_revocation(self):
        from hivemind.auth import AuthManager
        from hivemind.git_memory import GitMemory
        from hivemind.workspace import ProjectWorkspace
        memory = self.save()
        token, record = self.auth.create_agent_token(self.owner, 'durability', self.project)
        self.auth.revoke(self.owner, record.token_id, self.project)
        second = self.make_store()
        auth = AuthManager({'HIVEMIND_USERS': 'owner=pw,editor=pw,viewer=pw'}, store=second)
        service = GitMemory(second, ProjectWorkspace(second, auth))
        recalled = service.recall(self.owner, self.project, {'context_id': self.main['context_id']})
        self.assertIn(memory['id'], self.ids(recalled))
        self.assertIsNone(auth.authenticate_agent_context(token))
