"""Focused acceptance edge fixtures, specified before execution.

Real local Git is used throughout. Live opt-in creates a fresh random graph and
never clears existing data. Expected behavior is defined in each test docstring,
not supplied as instructions to a model. No model calls are made.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import unittest
from unittest.mock import patch

from hivemind.bridge import git
from hivemind.git_graph import RepositoryGraph
from hivemind.store import InMemoryGraphStore
import test_git_memory


# Keep the resource load fixed even if a future implementation raises its limit.
AUDITED_PAGE_LIMIT = 1024
OVERLOAD_FIXTURE_COUNT = 1025


class GitAcceptanceEdgeTests(unittest.TestCase):
    def make_store(self):
        return InMemoryGraphStore()

    def setUp(self):
        self.fixture = test_git_memory.GitFixture()
        self.fixture.make_store = self.make_store
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def diagnostic(self, case, **values):
        print('EDGE_EVIDENCE ' + json.dumps(dict(case=case,
              backend=getattr(self.fixture.store, 'backend_name', 'memory'),
              project=self.fixture.project, repo=self.fixture.repo, **values)), flush=True)

    def test_D2_deepening_old_common_source_does_not_publish_new_learning(self):
        """Discovering common A, whose source matches, must not publish learning from B2."""
        f = self.fixture
        common = f.commit('Unobserved common source A', 'common.txt', 'Shared source ancestor.\n')
        git(f.root, 'branch', 'old-ancestor-feature')
        f.commit('Main diverges once', 'main.txt', 'M1\n')
        f.commit('Main diverges twice', 'main.txt', 'M2\n')
        f.bridge.config['history_limit'] = 2
        main_bounded = f.sync()
        self.assertFalse(main_bounded['completeness']['history_complete'])
        graph = f.service.graph(f.project, f.repo)
        common_id = f.service.commit_id(f.project, f.repo, common)
        self.assertIsNone(graph.get(common_id), 'A must not already be known to the service')
        git(f.root, 'switch', 'old-ancestor-feature')
        f.commit('Feature diverges once', 'feature.txt', 'B1\n')
        f.commit('Feature diverges twice', 'feature.txt', 'B2\n')
        feature_bounded = f.sync()
        learning = f.save(feature_bounded, event='new-learning-old-source')
        self.assertIsNone(graph.get(common_id))
        self.assertFalse(graph.links('PUBLISHES', to_id=learning['id']))
        f.bridge.config['history_limit'] = 64
        feature_deepened = f.sync()
        self.assertEqual(feature_deepened['head'], feature_bounded['head'])
        self.assertTrue(feature_deepened['completeness']['history_complete'])
        self.assertIsNotNone(graph.get(common_id))
        original_source = graph.links('SUPPORTED_BY', from_id=learning['id'])[0][1]
        self.assertTrue(graph.links('HAS_SOURCE', from_id=common_id, to_id=original_source),
                        'Old common A must contain the exact learning source')
        git(f.root, 'switch', 'main')
        main_deepened = f.sync()
        self.assertEqual(main_deepened['head'], main_bounded['head'])
        self.assertNotIn(learning['id'], f.ids(f.recall(main_deepened)))
        self.assertFalse(graph.links('PUBLISHES', to_id=learning['id']))
        self.assertIn(learning['id'], f.ids(f.recall(feature_deepened)))
        self.diagnostic('D2', common=common, origin=feature_bounded['head'],
                        revision=learning['id'], main_context=main_deepened['context_id'])

    def test_D5_only_qualifying_authored_successor_has_exact_publication_receipt(self):
        """Foreign authors and mismatched sources cannot publish; own matching C publishes exactly C."""
        f = self.fixture
        f.commit('Second independent source', 'second.txt', 'Old second constraint.\n')
        origin = f.sync()
        matching = f.save(origin, event='matching-pending')
        mismatching = f.save(origin, event='mismatching-pending', paths=['second.txt'])
        graph = f.service.graph(f.project, f.repo)
        self.assertFalse(graph.links('PUBLISHES', to_id=matching['id']))
        git(f.root, 'commit', '--allow-empty', '-m', 'Foreign authored successor B',
            '--author=Foreign Fixture <foreign@example.test>')
        foreign = f.sync()
        for memory in (matching, mismatching):
            self.assertFalse(graph.links('PUBLISHES', to_id=memory['id']))
        own_oid = f.commit('Qualifying authored successor C', 'second.txt', 'Changed second constraint.\n')
        qualified = f.sync()
        publications = graph.links('PUBLISHES', to_id=matching['id'])
        self.assertEqual(len(publications), 1)
        start, end, props = publications[0]
        self.assertEqual(start, f.service.commit_id(f.project, f.repo, own_oid))
        self.assertEqual(end, matching['id'])
        self.assertEqual(props['reason'], 'authored_commit')
        self.assertEqual(props['observation'], qualified['context_id'])
        self.assertFalse(graph.links('PUBLISHES', to_id=mismatching['id']))
        self.assertEqual(graph.get(matching['id']).head, origin['head'],
                         'Publication must preserve the distinct original source commit')
        self.assertNotEqual(origin['head'], own_oid)
        explanation = f.service.explain(f.owner, f.project,
            dict(context_id=qualified['context_id'], memory_id=matching['id']))
        self.assertEqual(explanation['inheritance_path'], [start, matching['id']])
        self.diagnostic('D5', source=origin['head'], foreign=foreign['head'],
                        publication=own_oid, revision=matching['id'], observation=props['observation'])

    def test_D7_conflict_resolution_discarding_one_required_source_blocks_transfer(self):
        """A real merge retains one of two required sources: the finding must require review, not inherit."""
        f = self.fixture
        f.commit('Shared second constraint', 'constraint.txt', 'Shared constraint.\n')
        f.sync()
        git(f.root, 'switch', '-c', 'conflict-source')
        (f.root / 'guide.txt').write_text('Feature guide retained by merge.\n')
        f.commit('Feature conflicts in second constraint', 'constraint.txt', 'Feature constraint.\n')
        source = f.sync()
        learning = f.save(source, event='two-source-conflict-claim', paths=['guide.txt', 'constraint.txt'])
        git(f.root, 'switch', 'main')
        f.commit('Destination conflicts in second constraint', 'constraint.txt', 'Destination constraint.\n')
        f.sync()
        merged = subprocess.run(['git', '-C', str(f.root), 'merge', '--no-ff', 'conflict-source',
                                 '-m', 'Merge with deliberate source rejection'], capture_output=True)
        self.assertEqual(merged.returncode, 1, merged.stdout + merged.stderr)
        self.assertEqual(git(f.root, 'diff', '--name-only', '--diff-filter=U'), 'constraint.txt')
        git(f.root, 'checkout', '--ours', '--', 'constraint.txt')
        merge_oid = f.commit('Resolve conflict using destination constraint')
        integrated = f.sync()
        self.assertEqual(len(git(f.root, 'show', '-s', '--format=%P', merge_oid).split()), 2)
        self.assertIn(source['head'], git(f.root, 'rev-list', merge_oid).splitlines())
        graph = f.service.graph(f.project, f.repo)
        supports = graph.links('SUPPORTED_BY', from_id=learning['id'])
        matched = [sid for _, sid, _ in supports
                   if graph.links('HAS_SOURCE', from_id=integrated['snapshot_id'], to_id=sid)]
        self.assertEqual(len(supports), 2)
        self.assertEqual(len(matched), 1, 'Fixture must discard exactly one required source')
        self.assertNotIn(learning['id'], f.ids(f.recall(integrated)))
        self.assertFalse(graph.links('PUBLISHES', to_id=learning['id']))
        receipt = next(t for t in integrated['transfers'] if t['memory_id'] == learning['id'])
        self.assertEqual((receipt['status'], receipt['reason']), ('needs_review', 'source_mismatch'))
        self.assertIsNotNone(graph.get(learning['id']))
        self.diagnostic('D7', source=source['head'], merge=merge_oid,
                        revision=learning['id'], required=2, matched=1, transfer=receipt)

    def test_D13_deleting_required_source_preserves_historical_finding(self):
        """Deleting the required file leaves historical provenance, zero current matches, and no verified claim."""
        f = self.fixture
        learning = f.save(f.main, event='source-deleted-later')
        (f.root / 'guide.txt').unlink()
        deleted_oid = f.commit('Delete required guide')
        current = f.sync()
        recalled = next(m for m in f.recall(current)['findings'] if m['id'] == learning['id'])
        self.assertEqual(recalled['applicability'], 'historical_source_changed')
        self.assertEqual((recalled['expected_source_count'], recalled['source_count'], recalled['source_matches']), (1, 1, 0))
        graph = f.service.graph(f.project, f.repo)
        self.assertIsNotNone(graph.get(learning['id']))
        self.assertEqual(len(graph.links('SUPPORTED_BY', from_id=learning['id'])), 1)
        historical = next(m for m in f.recall(f.main)['findings'] if m['id'] == learning['id'])
        self.assertEqual(historical['applicability'], 'applicable')
        self.diagnostic('D13', revision=learning['id'], deletion=deleted_oid,
                        current_context=current['context_id'], applicability=recalled['applicability'])

    def test_D20_fixture_clean_filter_normalizes_non_newline_content(self):
        """Fixture-owned reversible token filter makes distinct raw bytes share HEAD's canonical source identity."""
        f = self.fixture
        script = f.root / '.git' / 'acceptance_clean_filter.py'
        script.write_text('import sys\n'
                          'raw = sys.stdin.buffer.read()\n'
                          'old, new = (b"WORKSPACE_QUEUE", b"CANONICAL_QUEUE")\n'
                          'if sys.argv[1] == "smudge": old, new = new, old\n'
                          'sys.stdout.buffer.write(raw.replace(old, new))\n', encoding='utf-8')
        command = '"' + Path(sys.executable).as_posix() + '" "' + script.as_posix() + '" '
        git(f.root, 'config', 'filter.hivemind_fixture.clean', command + 'clean')
        git(f.root, 'config', 'filter.hivemind_fixture.smudge', command + 'smudge')
        git(f.root, 'config', 'filter.hivemind_fixture.required', 'true')
        (f.root / '.gitattributes').write_text('guide.txt filter=hivemind_fixture -text\n')
        raw = b'Validate WORKSPACE_QUEUE before release.\n'
        (f.root / 'guide.txt').write_bytes(raw)
        f.commit('Canonical token source through fixture-owned filter')
        canonical = git(f.root, 'show', 'HEAD:guide.txt', binary=True)
        self.assertEqual(canonical, b'Validate CANONICAL_QUEUE before release.\n')
        self.assertNotEqual(raw, canonical)
        self.assertFalse(git(f.root, 'status', '--porcelain'))
        first = f.sync()
        learning = f.save(first, event='supported-filter-source')
        first_hash = f.bridge.observe(['guide.txt'])['sources']['guide.txt']
        expected = hashlib.sha256(b'git-blob:' + git(f.root, 'rev-parse', 'HEAD:guide.txt').encode()).hexdigest()
        self.assertEqual(first_hash, expected)
        (f.root / 'guide.txt').write_bytes(canonical)
        self.assertFalse(git(f.root, 'status', '--porcelain'))
        self.assertEqual(f.bridge.observe(['guide.txt'])['sources']['guide.txt'], first_hash)
        (f.root / 'guide.txt').unlink()
        git(f.root, 'checkout', '--', 'guide.txt')
        self.assertEqual((f.root / 'guide.txt').read_bytes(), raw, 'The configured smudge path must actually execute')
        second = f.sync()
        recalled = next(m for m in f.recall(second)['findings'] if m['id'] == learning['id'])
        self.assertEqual(recalled['applicability'], 'applicable')
        self.assertEqual(recalled['source_matches'], 1)
        self.assertEqual(first['snapshot_id'], second['snapshot_id'])
        self.diagnostic('D20', revision=learning['id'], canonical_source_sha256=first_hash,
                        snapshot=second['snapshot_id'], raw_equals_canonical=False)

    def test_E8_candidate_overload_is_bounded_and_explicitly_incomplete(self):
        """1025 eligible findings cannot be represented as complete recall; fixed live queries stay bounded."""
        f = self.fixture
        self.assertEqual(RepositoryGraph.LIMIT, AUDITED_PAGE_LIMIT,
                         'Reassess this fixed-size fixture if the product page limit changes')
        count = OVERLOAD_FIXTURE_COUNT
        for index in range(count):
            f.save(f.main, event='bounded-candidate-' + str(index),
                   title='Bounded candidate ' + str(index), body='A short independent fixture observation.')
        queries = []
        if getattr(f.store, 'backend_name', '') == 'falkordb':
            original = f.store.run_fixed

            def tracked_query(name, params):
                queries.append((name, dict(params)))
                return original(name, params)

            with patch.object(f.store, 'run_fixed', side_effect=tracked_query), \
                 patch.object(f.store, 'nodes', side_effect=AssertionError('Live recall downloaded generic nodes')), \
                 patch.object(f.store, 'edges', side_effect=AssertionError('Live recall downloaded generic edges')):
                recalled = f.recall(f.main)
            names = {name for name, _ in queries}
            self.assertTrue({'git_candidates', 'git_applicability'} <= names)
            self.assertTrue(all(name.startswith('git_') or name == 'node_lookup' for name in names), names)
            for name, params in queries:
                if name == 'node_lookup':
                    self.assertEqual(set(params), {'id'}, 'Only a singleton node read is permitted')
                    self.assertIsInstance(params['id'], str)
                if 'limit' in params:
                    self.assertLessEqual(params['limit'], RepositoryGraph.LIMIT + 1, name)
                if name == 'git_applicability':
                    self.assertLessEqual(len(params['candidate_ids']), RepositoryGraph.LIMIT)
        else:
            recalled = f.recall(f.main)
        self.assertTrue(recalled['ok'])
        self.assertFalse(recalled['completeness']['candidates_complete'])
        self.assertTrue(recalled['completeness']['context_truncated'])
        self.assertLessEqual(len(recalled['findings']), 8)
        self.assertLessEqual(len(json.dumps(recalled, ensure_ascii=False)), 8000)
        self.assertGreater(recalled['exclusion_counts']['context_budget'], 0)
        self.diagnostic('E8-candidates', fixture_findings=count,
                        returned=len(recalled['findings']), completeness=recalled['completeness'],
                        live_query_names=sorted({name for name, _ in queries}))

    def test_E8_observation_page_overload_blocks_unqualified_integration(self):
        """1025 observation records force explicit integration incompleteness and prevent new inheritance."""
        f = self.fixture
        git(f.root, 'switch', '-c', 'observation-overflow-source')
        f.commit('Feature to be integrated', 'feature.txt', 'Feature.\n')
        source = f.sync()
        learning = f.save(source, event='overload-integration-claim')
        graph = f.service.graph(f.project, f.repo)
        # Fixture-only observations represent an overloaded retained history. They
        # have no memory or publication edges and claim no additional Git commits.
        template = graph.get(source['context_id'])
        self.assertEqual(RepositoryGraph.LIMIT, AUDITED_PAGE_LIMIT,
                         'Reassess this fixed-size fixture if the product page limit changes')
        for index in range(OVERLOAD_FIXTURE_COUNT):
            f.service.record(f.project, f.repo, 'observation', 'overload-' + str(index),
                             dict(template.data), branch=source['branch_id'], head=source['head'],
                             snapshot=source['snapshot_id'], author=f.owner.user_id)
        observations, complete = graph.list('observation')
        self.assertEqual(len(observations), RepositoryGraph.LIMIT)
        self.assertFalse(complete)
        git(f.root, 'switch', 'main')
        f.sync()
        git(f.root, 'merge', '--ff-only', 'observation-overflow-source')
        integrated = f.sync()
        self.assertIn(dict(status='needs_review', reason='integration_observations_incomplete'), integrated['transfers'])
        self.assertNotIn(learning['id'], f.ids(f.recall(integrated)))
        self.assertFalse(graph.links('PUBLISHES', to_id=learning['id']))
        self.diagnostic('E8-observations', fixture_extra_observations=OVERLOAD_FIXTURE_COUNT,
                        revision=learning['id'], transfers=integrated['transfers'])


class CheckoutStageRaceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_git_memory.GitFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_D19_actual_checkout_between_observation_stages_is_rejected(self):
        """A real switch during hash/history or history/status stages cannot return a torn checkout."""
        f = self.fixture
        base = git(f.root, 'rev-parse', 'HEAD')
        git(f.root, 'switch', '-c', 'racing-other')
        changed_head = f.commit('Other branch with identical source content')
        git(f.root, 'switch', 'main')
        source_before = (f.root / 'guide.txt').read_bytes()
        for stage in ('rev-list', 'status'):
            with self.subTest(stage=stage):
                git(f.root, 'switch', 'main')
                switched = False

                def checkout_during_stage(root, *args, **kwargs):
                    nonlocal switched
                    if args and args[0] == stage and not switched:
                        switched = True
                        git(root, 'switch', 'racing-other')
                    return git(root, *args, **kwargs)

                with patch('hivemind.bridge.git', side_effect=checkout_during_stage):
                    with self.assertRaisesRegex(ValueError, 'checkout changed during observation'):
                        f.bridge.observe(['guide.txt'])
                self.assertTrue(switched)
                self.assertEqual(git(f.root, 'symbolic-ref', '--short', 'HEAD'), 'racing-other')
                self.assertEqual(git(f.root, 'rev-parse', 'HEAD'), changed_head)
                self.assertNotEqual(changed_head, base)
                self.assertEqual((f.root / 'guide.txt').read_bytes(), source_before)
        print('EDGE_EVIDENCE ' + json.dumps(dict(case='D19', stages=['rev-list', 'status'],
              initial_head=base, switched_head=changed_head, actual_checkout=True, returned_torn_observations=0)), flush=True)


@unittest.skipUnless(os.environ.get('HIVEMIND_LIVE_TESTS') == '1', 'Explicit live edge audit opt-in required')
class GitAcceptanceLiveEdgeTests(GitAcceptanceEdgeTests):
    @classmethod
    def setUpClass(cls):
        cls.graph_name = 'hivemind_git_edges_' + secrets.token_hex(12)
        print('Independent live edge graph: ' + cls.graph_name, flush=True)

    def make_store(self):
        from hivemind.backend import create_store
        return create_store({**os.environ, 'HIVEMIND_BACKEND': 'falkordb', 'FALKORDB_GRAPH': self.graph_name})


if __name__ == '__main__':
    unittest.main()
