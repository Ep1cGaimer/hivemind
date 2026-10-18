"""Synthetic helper tests; no entries here are actual writer evidence."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import evidence_tools as ev
import suite
from test_suite import REFERENCE


def inventory(records=None, links=None):
    return {'records': records or [], 'links': links or [],
            'inventory': {'complete': True, 'all_kinds': True,
                          'filters': {'project_id': 'synthetic-project', 'repo_id': 'synthetic-repo'}}}


class EvidenceHelpersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='evidence-helper-', dir=suite.HERE)
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def test_full_export_retains_revisions_conflicts_exclusions_and_unknown_fields(self):
        records = [
            {'id': 'old', 'kind': 'finding', 'session': 's1', 'branch_id': 'partner', 'head': 'old-head', 'snapshot_id': 'old-snapshot',
             'data': {'body': 'Old claim', 'classification': 'historical', 'qualifications': ['stale', 'wrong-branch'], 'conflicts': ['new'], 'sources': [{'source_id': 'src', 'path': 'slug.py'}]}},
            {'id': 'new', 'kind': 'finding', 'data': {'body': 'Conflicting claim', 'supersedes_id': 'old', 'exclusions': ['not current on main']}},
            {'id': 'cp', 'kind': 'checkpoint', 'data': {'body': 'Done parsing; next implement CLI; quantity validation open'}},
            {'id': 'src', 'kind': 'source', 'data': {'path': 'slug.py', 'clean_hash': 'source-hash'}},
            {'id': 'obs', 'kind': 'observation', 'data': {'head': 'old-head'}},
            {'id': 'pub', 'kind': 'publication', 'data': {'commit': 'old-head'}},
        ]
        links = [{'edge_type': 'REVISES', 'from_id': 'new', 'to_id': 'old', 'properties': {'scope': 'partner'}},
                 {'edge_type': 'SUPPORTED_BY', 'from_id': 'old', 'to_id': 'src', 'properties': {}}]
        raw = inventory(records, links)
        raw['future_schema_metadata'] = {'retained': True, 'source_history': ['v1', 'v2']}
        raw['observed_recall'] = {'findings': ['new'], 'excluded': ['old']}
        result = ev.notes_export(raw)
        self.assertEqual(result['full_inventory'], raw)
        self.assertEqual(result['index_ids_by_kind']['finding'], ['old', 'new'])
        self.assertEqual(result['sanitization']['redactions'], [])

    def test_recall_incomplete_filtered_and_dangling_inputs_rejected(self):
        inputs = [{'findings': [], 'checkpoints': []}, inventory()]
        inputs[1]['inventory']['complete'] = False
        filtered = inventory(); filtered['inventory']['filters']['branch_id'] = 'main'; inputs.append(filtered)
        dangling = inventory([{'id': 'a', 'kind': 'finding'}], [{'edge_type': 'SUPPORTED_BY', 'from_id': 'a', 'to_id': 'missing', 'properties': {}}]); inputs.append(dangling)
        for payload in inputs:
            with self.subTest(payload=payload), self.assertRaises(ValueError): ev.notes_export(payload)

    def test_sanitization_is_narrow_and_retains_qualifications_and_ids(self):
        payload = inventory([{'id': 'f', 'kind': 'finding', 'branch_id': 'same-branch',
                              'data': {'body': 'stale: secretvalue-123; see private/data.key before retry',
                                       'classification': 'conflicted', 'sources': [{'source_id': 'same-source', 'path': 'public.py'}],
                                       'tokens': {'input': 31}, 'authorization': 'Bearer actual-auth-value'}}])
        payload['records'].append({'id': 'private-source', 'kind': 'source', 'data': {'path': 'private/data.key', 'text': 'private source content'}})
        result = ev.notes_export(payload, {'secret_values': ['secretvalue-123'], 'private_prefixes': ['private']})
        serialized = json.dumps(result)
        for value in ('secretvalue-123', 'actual-auth-value', 'private/data.key', 'private source content'):
            self.assertNotIn(value, serialized)
        finding = result['full_inventory']['records'][0]
        self.assertEqual(finding['data']['tokens'], {'input': 31})
        self.assertEqual(finding['branch_id'], 'same-branch')
        self.assertEqual(finding['data']['sources'][0]['source_id'], 'same-source')
        self.assertIn('stale:', finding['data']['body'])
        self.assertEqual(finding['data']['classification'], 'conflicted')

    def make_run(self, case):
        dest = self.root / case
        suite.prepare(NS(case=case, dest=str(dest)))
        return dest, dest / 'repo'

    def test_clone_source_snapshot_equal_and_runtime_exclusions_explicit(self):
        dest, repo = self.make_run('no_history')
        clone = self.root / 'clone'
        suite.materialize(NS(run=str(dest), dest=str(clone)))
        a = ev.source_snapshot(repo)
        b = ev.source_snapshot(clone / 'repo')
        self.assertEqual(a['source_snapshot_sha256'], b['source_snapshot_sha256'])
        suite.write(clone / 'repo', 'opencode.json', '{"session":"different-runtime"}\n')
        self.assertNotEqual(a['source_snapshot_sha256'], ev.source_snapshot(clone / 'repo')['source_snapshot_sha256'])
        self.assertEqual(a['source_snapshot_sha256'], ev.source_snapshot(clone / 'repo', ['opencode.json'])['source_snapshot_sha256'])
        with self.assertRaises(ValueError): ev.source_snapshot(repo, ['stats.py'])
        with (clone / 'repo' / 'stats.py').open('a') as f: f.write('\n# source changed\n')
        self.assertNotEqual(a['source_snapshot_sha256'], ev.source_snapshot(clone / 'repo', ['opencode.json'])['source_snapshot_sha256'])

    def test_native_event_parser_does_not_treat_narration_or_completion_as_exit_zero(self):
        events = [
            {'type': 'text', 'sessionID': 's', 'part': {'text': 'Tests passed; schema generated'}},
            {'type': 'tool_use', 'sessionID': 's', 'part': {'id': 't1', 'tool': 'bash', 'state': {'status': 'completed', 'input': {'command': 'python tools/build.py'}, 'output': 'schema generated', 'time': {}}}},
            {'type': 'tool_use', 'sessionID': 's', 'part': {'id': 't2', 'tool': 'bash', 'state': {'status': 'completed', 'input': {'command': 'python demo.py'}, 'output': '99.00', 'metadata': {'exit': 0}, 'time': {}}}},
        ]
        path = self.root / 'actual-format-synthetic.jsonl'
        path.write_text('\n'.join(json.dumps(e) for e in events), encoding='utf-8')
        tools, sessions, files = ev.native_tools([path])
        self.assertEqual(len(tools), 2)
        self.assertIsNone(tools[0]['exit_code'])
        self.assertEqual(tools[1]['exit_code'], 0)
        self.assertEqual(sessions, {'s'})
        self.assertTrue(files[0]['sha256'])

    def test_negative_case_eligibility_and_no_history_invention(self):
        dest, _ = self.make_run('no_history')
        self.assertEqual(ev.writer_audit(dest, [], inventory())['status'], 'passed')
        self.assertEqual(ev.writer_audit(dest, [], inventory([{'id': 'f', 'kind': 'finding'}]))['status'], 'failed')
        failed, repo = self.make_run('failed_approach')
        p = repo / 'catalog.py'
        p.write_text(p.read_text().replace('sku LIKE ? ORDER BY price DESC', 'sku = ?'), encoding='utf-8')
        suite.advance(NS(run=str(failed), variant='default'))
        result = ev.writer_audit(failed, [], inventory())
        self.assertTrue(result['checks']['frozen_writer_functional_probe'])
        self.assertFalse(result['checks']['actual_native_session_ids_present'])
        self.assertFalse(result['checks']['writer_memory_records_present'])
        self.assertEqual(result['status'], 'untested')

    def test_advance_observer_runs_before_policy_change_and_failure_reuses_freeze(self):
        dest, repo = self.make_run('stale_guidance')
        suite.write(repo, 'display.py', 'def display_amount(v):\n    return v\n')
        observed = []
        def fail_once(path, tip):
            observed.append(tip)
            self.assertEqual(suite.git(path, 'rev-parse', 'HEAD'), tip)
            self.assertEqual(json.loads((path / 'money_policy.json').read_text())['rounding'], 'ROUND_HALF_UP')
            raise RuntimeError('synthetic observer failure')
        with self.assertRaises(RuntimeError): suite.advance(NS(run=str(dest), variant='default'), after_freeze=fail_once)
        state = ev.load(dest / 'state.json')
        self.assertEqual(state['phase'], 'writer')
        self.assertEqual(state['events'][-1]['event'], 'writer_frozen')
        suite.advance(NS(run=str(dest), variant='default'), after_freeze=lambda path, tip: observed.append(tip))
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(len([e for e in ev.load(dest / 'state.json')['events'] if e['event'] == 'writer_frozen']), 1)
        self.assertEqual(json.loads((repo / 'money_policy.json').read_text())['rounding'], 'ROUND_HALF_EVEN')

    def test_finished_writer_cannot_qualify_as_partial_checkpoint(self):
        dest, repo = self.make_run('unfinished_checkpoint')
        for name, code in REFERENCE['unfinished_checkpoint'].items(): suite.write(repo, name, code)
        suite.advance(NS(run=str(dest), variant='default'))
        result = ev.writer_audit(dest, [], inventory())
        self.assertTrue(result['checks']['frozen_writer_functional_probe'])
        self.assertFalse(result['checks']['writer_partial_not_finished'])
        self.assertEqual(result['status'], 'untested')


if __name__ == '__main__': unittest.main()
