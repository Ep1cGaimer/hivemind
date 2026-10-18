"""Reproducible deterministic Git demonstration and equal-information control.

This measures retrieval, not model behavior. Native-client proof is a separate run.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import secrets
import statistics
import tempfile
import time

from .auth import AuthManager, Identity
from .backend import create_store
from .bridge import LocalBridge, git
from .domain import record_to_dict
from .git_memory import GitMemory
from .workspace import ProjectWorkspace


class SourceLinkedNotes:
    """Capable notes control with equal records, metadata, edges, and traversal.

    Its explicit provenance index gives it the same evidence capabilities. This
    is a valid control, and parity is expected; no weakened baseline is used.
    """
    def __init__(self, records, edges):
        self.records = {n['id']: n for n in records}
        self.edges = edges

    def reachable(self, start, target):
        todo, seen = deque([start]), set()
        while todo:
            node = todo.popleft()
            if node == target: return True
            if node in seen: continue
            seen.add(node)
            todo.extend(e['to_id'] for e in self.edges if e['from_id'] == node and e['edge_type'] == 'PARENT')
        return False

    def recall(self, branch, head, snapshot):
        sources = {e['to_id'] for e in self.edges if e['from_id'] == snapshot and e['edge_type'] == 'HAS_SOURCE'}
        applicable = []
        for n in self.records.values():
            if n['kind'] != 'finding': continue
            branch_local = any(e['edge_type'] == 'BRANCH_MEMORY' and e['from_id'] == branch and e['to_id'] == n['id'] for e in self.edges)
            published = any(e['edge_type'] == 'PUBLISHES' and e['to_id'] == n['id'] and self.reachable(head, e['from_id']) for e in self.edges)
            required = {e['to_id'] for e in self.edges if e['from_id'] == n['id'] and e['edge_type'] == 'SUPPORTED_BY'}
            if (branch_local or published) and required <= sources:
                applicable.append(n['id'])
        return sorted(applicable)


def run(environ=None):
    store = create_store(environ)
    auth = AuthManager({}, store=store)
    owner = Identity('operator', 'Operator', 'operator')
    projects = ProjectWorkspace(store, auth)
    project = projects.create_project(owner, 'Git demonstration ' + secrets.token_hex(3))['project']['id']
    service = GitMemory(store, projects)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        git(root, 'init', '-b', 'main')
        git(root, 'config', 'user.email', 'demo@example.test')
        git(root, 'config', 'user.name', 'Demo')
        (root / 'guide.txt').write_text('Reserved queues require a rehearsal. Shared queues are untested.\n')
        git(root, 'add', '.')
        git(root, 'commit', '-m', 'Initial qualified guidance')
        repo = service.register(owner, project, {'remote': 'fixture.invalid/git-demo', 'root_commit': git(root, 'rev-parse', 'HEAD')})['repo_id']
        bridge = LocalBridge(root, config={'repo_id': repo, 'project_id': project, 'url': 'http://unused', 'connector_id': 'deterministic-demo'})
        def sync():
            observation = bridge.observe(['guide.txt'])
            result = service.sync(owner, project, observation)
            if not result['ok']: raise RuntimeError(result)
            branches = bridge.get('branches', {})
            branches[observation['ref']] = result['branch_id']
            bridge.set('branches', branches)
            bridge.set('context', result)
            return result
        main = sync()
        git(root, 'switch', '-c', 'queue-feature')
        feature = sync()
        memory = service.save(owner, project, {'context_id': feature['context_id'], 'title': 'Queue rehearsal prerequisite',
            'body': 'Reserved queues require a rehearsal. Shared queues remain untested.', 'paths': ['guide.txt'], 'session': 'deterministic-writer', 'event_id': 'learning'})['memory']
        before = service.recall(owner, project, {'context_id': main['context_id']})
        git(root, 'commit', '--allow-empty', '-m', 'Author feature work')
        sync()
        git(root, 'switch', 'main')
        sync()
        git(root, 'merge', '--ff-only', 'queue-feature')
        integrated = sync()
        after = service.recall(owner, project, {'context_id': integrated['context_id']})
        graph = service.graph(project, repo)
        records, complete = graph.list()
        if not complete: raise RuntimeError('Fixture is incomplete')
        edges = []
        for relation in ('PARENT', 'PUBLISHES', 'BRANCH_MEMORY', 'SUPPORTED_BY', 'HAS_SOURCE'):
            edges.extend({'from_id': a, 'to_id': b, 'edge_type': relation, 'properties': p} for a, b, p in graph.links(relation))
        notes = SourceLinkedNotes([record_to_dict(n) for n in records], edges)
        cases = [(main, False), (feature, True), (integrated, True)]
        correctness = {'hivemind': 0, 'source_linked_notes': 0}
        latency = {'hivemind': [], 'source_linked_notes': []}
        for context, expected in cases:
            args = (context['branch_id'], service.commit_id(project, repo, context['head']), context['snapshot_id'])
            for _ in range(5):
                start = time.perf_counter()
                result = service.recall(owner, project, {'context_id': context['context_id']})
                latency['hivemind'].append((time.perf_counter() - start) * 1000)
                start = time.perf_counter()
                baseline = notes.recall(*args)
                latency['source_linked_notes'].append((time.perf_counter() - start) * 1000)
            correctness['hivemind'] += ((memory['id'] in [m['id'] for m in result['findings']]) == expected)
            correctness['source_linked_notes'] += ((memory['id'] in baseline) == expected)
        explanation = service.explain(owner, project, {'context_id': integrated['context_id'], 'memory_id': memory['id']})
        def comparable(ids):
            return [{'revision_id': mid, 'title': notes.records[mid]['data']['title'],
                     'body': notes.records[mid]['data']['body'], 'paths': notes.records[mid]['data']['paths'],
                     'source_commit': notes.records[mid]['head'], 'branch_id': notes.records[mid]['branch_id']}
                    for mid in sorted(ids)]
        comparable_context = {'hivemind': len(json.dumps(comparable([m['id'] for m in after['findings']]))),
                              'source_linked_notes': len(json.dumps(comparable(baseline)))}
        return {'ok': True, 'mode': 'deterministic retrieval; no model calls', 'backend': store.backend_name,
                'same_commit_branch_isolated': not before['findings'], 'after_integration_recalled': memory['id'] in [m['id'] for m in after['findings']],
                'explanation': explanation, 'comparison': {'cases': len(cases), 'correct_cases': correctness,
                'median_retrieval_ms': {name: round(statistics.median(values), 3) for name, values in latency.items()},
                'equal_information': {'records': len(records), 'relationships': len(edges)},
                'model_calls': {'hivemind': 0, 'source_linked_notes': 0},
                'context_characters': len(json.dumps(after)), 'approximate_context_tokens': after['budget']['approximate_tokens'],
                'same_format_selected_context_characters': comparable_context,
                'preparation': 'Both receive the same automatically generated facts and provenance. Human preparation time was not measured.',
                'limitations': 'Three deterministic cases, warm local calls, no model-quality or product-superiority claim. Notes control implements a provenance index and traversal.'}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = run()
    raw = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw + '\n', encoding='utf-8')
    print(raw)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
