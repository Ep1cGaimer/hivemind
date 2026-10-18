"""Independent synthetic contract tests for the capable notes comparator."""
import copy
import unittest

from notes_control import NotesIndex, encoded
from test_evidence_tools import inventory


def node(key, kind, data=None, **kw):
    return {'id': key, 'kind': kind, 'data': data or {}, **kw}


def edge(kind, a, b, **properties):
    return {'edge_type': kind, 'from_id': a, 'to_id': b, 'properties': properties}


def standard():
    records = [node('a', 'commit', {'oid': 'oid-a', 'parents': []}),
               node('b', 'commit', {'oid': 'oid-b', 'parents': ['oid-a']}),
               node('merge', 'commit', {'oid': 'oid-merge', 'parents': ['oid-a', 'oid-b']}),
               node('src', 'source', {'path': 'worker.py', 'sha256': 'h1'}),
               node('m', 'finding', {'title': 'Worker quota', 'body': 'A bounded worker accepts at most 32 items. Preserve Unicode labels.',
                                    'paths': ['worker.py'], 'classification': 'constraint', 'qualifications': ['Observed on feature only']},
                    branch_id='feature', snapshot_id='writer-snapshot', head='oid-b', author='writer', session='writer-session'),
               node('cp', 'checkpoint', {'title': 'Continue wrapper', 'body': 'Parsing done; next implement batching; overflow behavior unvalidated.'},
                    branch_id='feature', snapshot_id='writer-snapshot', head='oid-b')]
    links = [edge('PARENT', 'b', 'a'), edge('PARENT', 'merge', 'a'), edge('PARENT', 'merge', 'b'),
             edge('SUPPORTED_BY', 'm', 'src'), edge('SUPPORTED_BY', 'cp', 'src'),
             edge('BRANCH_MEMORY', 'feature', 'm'), edge('BRANCH_MEMORY', 'feature', 'cp'),
             edge('PUBLISHES', 'b', 'm')]
    records.append(node('feature', 'branch'))
    context = {'context_id': 'consumer-observation', 'branch_id': 'feature', 'head': 'oid-b',
               'snapshot_id': 'consumer-snapshot', 'sources': {'worker.py': 'h1'},
               'history_complete': True, 'manifest_complete': True}
    return inventory(records, links), context


class NotesControlTests(unittest.TestCase):
    def test_exact_branch_source_and_checkout_qualifications(self):
        raw, ctx = standard()
        index = NotesIndex(raw, ctx)
        result = index.retrieve('worker batching')
        self.assertEqual([e['record']['id'] for e in result['findings']], ['m'])
        self.assertEqual([e['record']['id'] for e in result['checkpoints']], ['cp'])
        finding = result['findings'][0]
        self.assertTrue(finding['assessment']['eligible'])
        self.assertEqual(finding['assessment']['source_status'], 'matched')
        self.assertFalse(finding['assessment']['wip'])
        self.assertEqual(finding['assessment']['state'], 'verified_source_match')
        self.assertTrue(result['checkpoints'][0]['assessment']['wip'])
        self.assertEqual(result['checkpoints'][0]['assessment']['state'], 'wip_requires_verification')
        self.assertEqual(finding['record']['data']['qualifications'], ['Observed on feature only'])
        self.assertEqual(index.inspect('m')['record'], raw['records'][4])

    def test_same_commit_wrong_branch_does_not_publish_new_learning(self):
        raw, ctx = standard()
        raw['links'] = [e for e in raw['links'] if e['edge_type'] != 'PUBLISHES']
        ctx['branch_id'] = 'main'
        index = NotesIndex(raw, ctx)
        self.assertEqual(index.retrieve('worker')['findings'], [])
        self.assertFalse(index.assessments['m']['eligible'])
        # Complete strong control still has all facts, including excluded ones.
        self.assertEqual(index.search('quota')['results'][0]['record']['id'], 'm')
        self.assertFalse(index.inspect('m')['assessment']['eligible'])

    def test_actual_integration_changes_reachability(self):
        raw, ctx = standard()
        ctx.update(branch_id='main', head='oid-a')
        before = NotesIndex(raw, ctx)
        self.assertEqual(before.retrieve('quota')['findings'], [])
        ctx['head'] = 'oid-merge'
        after = NotesIndex(raw, ctx)
        result = after.retrieve('quota')['findings'][0]
        self.assertEqual(result['assessment']['state'], 'verified_source_match')
        self.assertEqual(result['assessment']['publication_paths'], [['merge', 'b', 'm']])

    def test_source_mismatch_and_partial_match_are_never_fully_verified(self):
        raw, ctx = standard()
        raw['records'].append(node('second-src', 'source', {'path': 'policy.json', 'sha256': 'old'}))
        raw['links'].append(edge('SUPPORTED_BY', 'm', 'second-src'))
        ctx['sources']['policy.json'] = 'new'
        result = NotesIndex(raw, ctx).retrieve('quota')['findings'][0]
        self.assertEqual(result['assessment']['source_status'], 'mismatch')
        self.assertEqual(result['assessment']['state'], 'historical_source_changed')
        self.assertEqual([s['status'] for s in result['assessment']['sources']], ['matched', 'changed'])
        self.assertEqual(result['assessment']['sources'][1]['required_hash'], 'old')

    def test_incomplete_manifest_and_history_are_explicit(self):
        raw, ctx = standard()
        ctx.update(sources={}, manifest_complete=False, history_complete=False)
        index = NotesIndex(raw, ctx)
        self.assertEqual(index.assessments['m']['source_status'], 'unknown')
        self.assertFalse(index.retrieve()['history_complete'])
        ctx['manifest_complete'] = True
        self.assertEqual(NotesIndex(raw, ctx).assessments['m']['sources'][0]['status'], 'missing')

    def test_concurrent_revisions_remain_visible_without_timestamp_truth(self):
        raw, ctx = standard()
        for key, body, timestamp in [('r1', 'Quota is 64.', '2099'), ('r2', 'Quota is 48.', '1900')]:
            raw['records'].append(node(key, 'finding', {'title': 'Quota interpretation', 'body': body, 'supersedes_id': 'm'},
                                       branch_id='feature', snapshot_id='consumer-snapshot', created_at=timestamp))
            raw['links'].append(edge('SUPPORTED_BY', key, 'src'))
            raw['links'].append(edge('REVISES', key, 'm'))
        index = NotesIndex(raw, ctx)
        result = index.retrieve('quota')
        ids = {e['record']['id'] for e in result['findings']}
        self.assertEqual(ids, {'r1', 'r2'})
        self.assertEqual(index.assessments['r1']['conflicts_with'], ['r2'])
        self.assertEqual(index.assessments['r2']['conflicts_with'], ['r1'])
        self.assertEqual(index.inspect('m')['record']['data']['body'], raw['records'][4]['data']['body'])

    def test_stale_or_other_branch_revision_does_not_overwrite_current_finding(self):
        raw, ctx = standard()
        raw['records'].extend([node('old-src', 'source', {'path': 'worker.py', 'sha256': 'wrong-version'}),
                               node('correction', 'finding', {'body': 'An unsupported correction', 'supersedes_id': 'm'}, branch_id='feature')])
        raw['links'] += [edge('SUPPORTED_BY', 'correction', 'old-src'), edge('REVISES', 'correction', 'm')]
        index = NotesIndex(raw, ctx)
        self.assertEqual(index.assessments['m']['superseded_by'], [])
        self.assertIn('m', [e['record']['id'] for e in index.retrieve('quota')['findings']])
        raw['records'][-1]['branch_id'] = 'other'
        self.assertEqual(NotesIndex(raw, ctx).assessments['m']['superseded_by'], [])

    def test_differing_wip_revision_does_not_suppress_verified_published_base(self):
        raw, ctx = standard()
        raw['records'].append(node('wip-r', 'finding', {'body': 'Tentative new interpretation', 'supersedes_id': 'm'},
                                   branch_id='feature', snapshot_id='another-checkout'))
        raw['links'] += [edge('SUPPORTED_BY', 'wip-r', 'src'), edge('REVISES', 'wip-r', 'm')]
        index = NotesIndex(raw, ctx)
        self.assertEqual(index.assessments['m']['state'], 'verified_source_match')
        self.assertEqual(index.assessments['m']['superseded_by'], [])
        self.assertTrue(index.assessments['wip-r']['wip'])
        self.assertEqual(index.assessments['wip-r']['state'], 'wip_requires_verification')
        self.assertEqual({e['record']['id'] for e in index.retrieve()['findings']}, {'m', 'wip-r'})
        # The exact same scoped successor becomes applicable after its checkout
        # is the observed checkout, without any timestamp-based truth choice.
        raw['records'][-1]['snapshot_id'] = ctx['snapshot_id']
        self.assertEqual(NotesIndex(raw, ctx).assessments['m']['superseded_by'], ['wip-r'])

    def test_source_free_decisions_and_assumptions_are_distinct_from_missing_manifest(self):
        raw, ctx = standard()
        raw['records'] += [node('choice', 'finding', {'title': 'Use concise CLI output', 'body': 'Agreed scoped choice', 'classification': 'decision'},
                                branch_id='feature', snapshot_id=ctx['snapshot_id']),
                           node('guess', 'finding', {'title': 'Capacity estimate', 'body': 'Unmeasured assumption', 'classification': 'assumption'},
                                branch_id='feature', snapshot_id=ctx['snapshot_id']),
                           node('unbound', 'finding', {'title': 'Code fact without binding', 'body': 'Possibly true', 'paths': ['worker.py']},
                                branch_id='feature', snapshot_id=ctx['snapshot_id'])]
        index = NotesIndex(raw, ctx)
        self.assertEqual(index.assessments['choice']['state'], 'recorded_decision')
        self.assertEqual(index.assessments['choice']['source_status'], 'not_applicable')
        self.assertEqual(index.assessments['guess']['state'], 'recorded_assumption')
        self.assertEqual(index.assessments['unbound']['source_status'], 'unbound')
        self.assertNotEqual(index.assessments['unbound']['source_status'], 'unknown')

    def test_context_manifest_overrides_old_snapshot_and_budget_keeps_full_inspection(self):
        raw, ctx = standard()
        raw['records'][4]['data']['body'] = ('Large\nquoted \\" body\n' * 400)
        ctx['sources']['worker.py'] = 'new-hash'
        index = NotesIndex(raw, ctx)
        result = index.retrieve('large', max_chars=3000)
        self.assertLessEqual(len(encoded(result)), 3000)
        self.assertEqual(result['budget']['counted_chars'], len(encoded(result)))
        self.assertTrue(result['truncated'])
        self.assertEqual(index.assessments['m']['source_status'], 'mismatch')
        self.assertEqual(index.inspect('m')['record']['data']['body'], raw['records'][4]['data']['body'])

    def test_count_limits_and_empty_history_are_honest(self):
        raw, ctx = standard()
        for i in range(12):
            raw['records'].append(node('extra-' + str(i), 'finding', {'body': 'Worker quota extra '+str(i)}, branch_id='feature'))
        result = NotesIndex(raw, ctx).retrieve('quota', max_chars=7900)
        self.assertLessEqual(len(result['findings']), 8)
        self.assertLessEqual(len(result['checkpoints']), 2)
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(encoded(result)), 7900)
        empty = NotesIndex(inventory(), ctx).retrieve('histogram')
        self.assertEqual(empty['findings'], [])
        self.assertEqual(empty['checkpoints'], [])
        self.assertEqual(empty['inventory_counts']['all_memories'], 0)

    def test_scope_mismatch_rejected_and_missing_exit_not_used_as_metadata(self):
        raw, ctx = standard()
        ctx['repo_id'] = 'expected'
        raw['records'][4]['repo_id'] = 'different'
        with self.assertRaises(ValueError): NotesIndex(raw, ctx)


if __name__ == '__main__': unittest.main()
