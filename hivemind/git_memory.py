"""Git-aware memory service. Connector observations are provenance, not truth."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from dataclasses import replace

from .domain import GitRecord, deterministic_id, record_to_dict
from .git_graph import RepositoryGraph
from .store import StoreError, ImmutableConflictError


def fail(code, message):
    return {'ok': False, 'error': {'code': code, 'message': message}}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def safe_path(path):
    return isinstance(path, str) and bool(path) and not path.startswith(('/', '\\')) and '\\' not in path and ':' not in path and '..' not in path.split('/')


SECRET = re.compile(r'-----BEGIN .*PRIVATE KEY|(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})|(?:password|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*["\']?[^\s"\']{8,}', re.I)


class GitMemory:
    MAX_COMMITS = 256
    MAX_SOURCES = 2048

    def __init__(self, store, projects):
        self.store, self.projects = store, projects

    def graph(self, project, repo):
        return RepositoryGraph(self.store, project, repo)

    def record(self, project, repo, kind, key, data, *, branch='', head='', snapshot='', author='', session='', record_id=None):
        node_id = record_id or deterministic_id('git', project, repo, kind, key)
        old = self.graph(project, repo).get(node_id)
        # Timestamp is not part of an event's identity. Replays retain its first receipt.
        record = GitRecord(node_id, self.store.tenant_id, self.store.project_id, project, repo,
                           kind, key, branch, head, snapshot, author, session,
                           old.created_at if old else now(), data)
        try:
            return self.store.add_node(record)
        except ImmutableConflictError:
            winner = self.graph(project, repo).get(node_id)
            if winner and record_to_dict(replace(record, created_at=winner.created_at)) == record_to_dict(winner):
                return winner
            raise

    def edge(self, kind, a, b, **props):
        return self.store.add_edge(kind, a.id if isinstance(a, GitRecord) else a,
                                   b.id if isinstance(b, GitRecord) else b, props)

    def commit_id(self, project, repo, oid):
        return deterministic_id('git', project, repo, 'commit', oid)

    def register(self, identity, project, payload):
        if not self.projects.can_access(identity, project, write=True):
            return fail('FORBIDDEN', 'Project editor membership is required')
        if payload.get('repository_id'):
            repo = payload['repository_id']
            record = self.graph(project, repo).get(deterministic_id('git', project, repo, 'repository', repo))
            if not record or record.kind != 'repository':
                return fail('REPOSITORY_NOT_FOUND', 'The selected repository does not belong to this project')
            return {'ok': True, 'repository': record_to_dict(record), 'repo_id': repo}
        remote, root = payload.get('remote'), payload.get('root_commit')
        if not isinstance(remote, str) or not remote or len(remote) > 500 or '@' in remote or '?' in remote:
            return fail('INVALID_REPOSITORY', 'Use a canonical credential-free repository identity')
        if not isinstance(root, str) or not re.fullmatch('[0-9a-f]{40,64}', root):
            return fail('INVALID_REPOSITORY', 'A verified root commit is required')
        repo = deterministic_id('repository', project, remote, root)
        existing = self.graph(project, repo).get(deterministic_id('git', project, repo, 'repository', repo))
        if existing:
            return {'ok': True, 'repository': record_to_dict(existing), 'repo_id': repo}
        record = self.record(project, repo, 'repository', repo, {'remote': remote, 'root_commit': root}, author=identity.user_id)
        return {'ok': True, 'repository': record_to_dict(record), 'repo_id': repo}

    def _source(self, project, repo, path, hash_value):
        if not safe_path(path) or not isinstance(hash_value, str) or not re.fullmatch('[0-9a-f]{64}', hash_value):
            raise ValueError('Source paths must be repository-relative and hashes must be SHA-256')
        return self.record(project, repo, 'source', digest([path, hash_value]), {'path': path, 'sha256': hash_value})

    def sync(self, identity, project, payload):
        if not self.projects.can_access(identity, project, write=True):
            return fail('FORBIDDEN', 'Project editor membership is required for synchronization')
        repo, head = payload.get('repo_id'), payload.get('head')
        graph = self.graph(project, repo)
        if not any(n.kind == 'repository' for n in [graph.get(deterministic_id('git', project, repo, 'repository', repo))] if n):
            return fail('REPOSITORY_NOT_FOUND', 'Connect this repository first')
        commits, sources = payload.get('commits'), payload.get('sources')
        if not isinstance(head, str) or not re.fullmatch('[0-9a-f]{40,64}', head):
            return fail('INVALID_CONTEXT', 'HEAD must be a full Git object ID')
        if not isinstance(commits, list) or not 1 <= len(commits) <= self.MAX_COMMITS or not isinstance(sources, dict) or len(sources) > self.MAX_SOURCES:
            return fail('INVALID_CONTEXT', 'Bounded commits and source manifest are required')
        mappings = payload.get('mappings', [])
        if not isinstance(mappings, list) or len(mappings) > 32 or any(not isinstance(m, dict) or not isinstance(m.get('entries', []), list) or len(m.get('entries', [])) > 256 or any(not isinstance(e, dict) for e in m.get('entries', [])) for m in mappings):
            return fail('INVALID_MAPPING', 'History mappings must be bounded connector observations')
        connector = payload.get('connector_id')
        if not isinstance(connector, str) or not re.fullmatch('[a-zA-Z0-9_-]{8,100}', connector):
            return fail('INVALID_CONNECTOR', 'A stable local connector ID is required')
        # Validate everything before starting writes.
        try:
            for c in commits:
                if not isinstance(c, dict) or not re.fullmatch('[0-9a-f]{40,64}', c.get('oid', '')):
                    raise ValueError('Invalid commit')
                if not isinstance(c.get('parents'), list) or len(c['parents']) > 16 or any(not re.fullmatch('[0-9a-f]{40,64}', p) for p in c['parents']):
                    raise ValueError('Invalid parents')
                for path, hash_value in c.get('sources', {}).items():
                    if not safe_path(path) or not re.fullmatch('[0-9a-f]{64}', hash_value):
                        raise ValueError('Invalid commit source manifest')
            if head not in {c['oid'] for c in commits}:
                raise ValueError('HEAD is absent from the observed lineage')
            for path, hash_value in sources.items():
                if not safe_path(path) or not re.fullmatch('[0-9a-f]{64}', hash_value):
                    raise ValueError('Invalid working source manifest')
        except (ValueError, TypeError, AttributeError) as exc:
            return fail('INVALID_CONTEXT', str(exc))
        branch_id = payload.get('branch_id')
        branch = graph.get(branch_id) if branch_id else None
        if branch_id and (not branch or branch.kind != 'branch'):
            return fail('INVALID_BRANCH', 'Join a recorded branch identity or create a new one')
        ref = payload.get('ref')
        if not isinstance(ref, str) or not ref or len(ref) > 200:
            return fail('INVALID_BRANCH', 'A local Git ref observation is required')
        if not branch:
            incarnation = payload.get('branch_incarnation')
            if incarnation is not None and (not isinstance(incarnation, str) or not 1 <= len(incarnation) <= 150):
                return fail('INVALID_BRANCH', 'A bounded local branch incarnation is required')
            # A lost first response or concurrent retry must create one branch.
            # Local bridges preserve the incarnation across retries and distinguish
            # a recreated ref. Older connectors deduplicate the exact initial event.
            branch_id = deterministic_id('branch', project, repo, identity.user_id, connector,
                incarnation or [ref, payload.get('event_id'), payload.get('previous_context')])
            branch = graph.get(branch_id)
            if not branch:
                branch = self.record(project, repo, 'branch', branch_id, {'initial_ref': ref, 'initial_head': head}, record_id=branch_id, author=identity.user_id)
        previous = graph.get(payload.get('previous_context'))
        if previous and (previous.kind != 'observation' or previous.data['connector_id'] != connector or previous.author != identity.user_id):
            return fail('INVALID_CONTEXT', 'Previous context is bound to another connector')
        snap_key = digest([head, sources, payload.get('dirty_hash'), payload.get('manifest_complete', False)])
        expected_snapshot = deterministic_id('git', project, repo, 'snapshot', snap_key)
        same_coverage = previous and previous.data['history_complete'] == bool(payload.get('history_complete')) and previous.data['shallow'] == bool(payload.get('shallow'))
        if previous and same_coverage and not mappings and previous.branch_id == branch_id and previous.head == head and previous.snapshot_id == expected_snapshot and previous.data['ref'] == ref:
            return {'ok': True, 'context_id': previous.id, 'branch_id': branch_id, 'snapshot_id': previous.snapshot_id,
                    'head': head, 'transfers': [], 'completeness': dict(previous.data)}
        for c in commits:
            n = self.record(project, repo, 'commit', c['oid'], {'oid': c['oid'], 'parents': c['parents']}, head=c['oid'])
            for p in c['parents']:
                # Boundary commits stay explicitly incomplete until separately observed.
                parent_id = self.commit_id(project, repo, p)
                if graph.get(parent_id):
                    self.edge('PARENT', n, parent_id)
        # Parents may have appeared later in the batch.
        for c in commits:
            for p in c['parents']:
                parent_id = self.commit_id(project, repo, p)
                if graph.get(parent_id):
                    self.edge('PARENT', self.commit_id(project, repo, c['oid']), parent_id)
            for path, hash_value in c.get('sources', {}).items():
                self.edge('HAS_SOURCE', self.commit_id(project, repo, c['oid']), self._source(project, repo, path, hash_value))
        snapshot = self.record(project, repo, 'snapshot', snap_key, {'sources': sources, 'dirty': bool(payload.get('dirty')), 'manifest_complete': bool(payload.get('manifest_complete'))}, head=head)
        for path, hash_value in sources.items():
            self.edge('HAS_SOURCE', snapshot, self._source(project, repo, path, hash_value))
        unchanged = previous and same_coverage and previous.branch_id == branch_id and previous.head == head and previous.snapshot_id == snapshot.id and previous.data['ref'] == ref
        observation = previous if unchanged else self.record(project, repo, 'observation', digest([connector, branch_id, head, snapshot.id, payload.get('event_id'), previous.id if previous else None]),
                                  {'connector_id': connector, 'ref': ref, 'history_complete': bool(payload.get('history_complete')),
                                   'manifest_complete': bool(payload.get('manifest_complete')), 'shallow': bool(payload.get('shallow')),
                                   'previous_context': previous.id if previous else None},
                                  branch=branch_id, head=head, snapshot=snapshot.id, author=identity.user_id)
        self.edge('OBSERVED', branch, observation)
        self.edge('AT_COMMIT', observation, self.commit_id(project, repo, head))
        transfer = []
        if previous and previous.branch_id == branch_id and previous.head != head:
            transfer = self._publish(identity, project, repo, previous, observation, commits)
        for mapping in payload.get('mappings', [])[:32]:
            transfer.extend(self._map_history(identity, project, repo, observation, mapping))
        return {'ok': True, 'context_id': observation.id, 'branch_id': branch_id, 'snapshot_id': snapshot.id,
                'head': head, 'transfers': transfer, 'completeness': dict(observation.data)}

    def _map_history(self, identity, project, repo, destination, mapping):
        """Accept only connector-computed unique patch mappings plus exact sources.

        Signatures are recorded Git observations, never a model assertion. Matching
        signatures alone cannot transfer a finding whose source content changed.
        """
        graph = self.graph(project, repo)
        source = graph.get(mapping.get('source_context'))
        if not source or source.kind != 'observation':
            return [{'status': 'needs_review', 'reason': 'mapping_source_missing'}]
        entries = mapping.get('entries', [])
        if not isinstance(entries, list) or len(entries) > 256:
            return [{'status': 'needs_review', 'reason': 'mapping_incomplete'}]
        mappings = {}
        for entry in entries:
            old, new = entry.get('old'), entry.get('new')
            sig = entry.get('old_patch')
            if not isinstance(sig, str) or not re.fullmatch('[0-9a-f]{40,64}', sig) or sig != entry.get('new_patch'):
                continue
            if entry.get('old_matches') != 1 or entry.get('new_matches') != 1:
                continue
            old_id, new_id = self.commit_id(project, repo, old), self.commit_id(project, repo, new)
            if graph.path(self.commit_id(project, repo, source.head), old_id) and graph.path(self.commit_id(project, repo, destination.head), new_id):
                mappings[old] = new
        findings, complete = graph.list('finding')
        if not complete:
            return [{'status': 'needs_review', 'reason': 'mapping_findings_incomplete'}]
        frozen_id = digest([source.id, destination.branch_id, destination.head, mapping.get('method')])
        event_id = deterministic_id('git', project, repo, 'mapping', frozen_id)
        prior = graph.get(event_id)
        candidates = prior.data['candidate_ids'] if prior else [m.id for m in findings if m.branch_id == source.branch_id and m.created_at <= destination.created_at and graph.path(self.commit_id(project, repo, source.head), self.commit_id(project, repo, m.head))]
        receipt = self.record(project, repo, 'mapping', frozen_id, {'candidate_ids': candidates, 'method': mapping.get('method'), 'entries': entries}, branch=destination.branch_id, head=destination.head)
        results = []
        for memory_id in candidates:
            m = graph.get(memory_id)
            mapped = mappings.get(m.head)
            # A squash maps an entire verified source range to its integrated tip.
            if mapping.get('method') == 'squash' and mappings.get(source.head):
                mapped = mappings[source.head]
            status = 'published' if mapped and self._matches(graph, m, self.commit_id(project, repo, mapped)) and self._matches(graph, m, self.commit_id(project, repo, destination.head)) else 'needs_review'
            if status == 'published':
                self.edge('PUBLISHES', self.commit_id(project, repo, mapped), m, reason='deterministic_' + str(mapping.get('method')), observation=receipt.id)
                self.edge('TRANSFERRED_FROM', receipt, m)
            results.append({'memory_id': m.id, 'status': status, 'reason': 'source_continuity' if status == 'published' else 'ambiguous_mapping_or_source_mismatch'})
        return results

    def _matches(self, graph, memory, node_id):
        sources = graph.links('SUPPORTED_BY', from_id=memory.id)
        paths = set(memory.data.get('paths', []))
        return (bool(graph.links('BRANCH_MEMORY', from_id=memory.branch_id, to_id=memory.id))
                and bool(paths) and len(sources) == len(paths)
                and {graph.get(s).data['path'] for _, s, _ in sources} == paths
                and all(graph.links('HAS_SOURCE', from_id=node_id, to_id=s) for _, s, _ in sources))

    def _publish(self, identity, project, repo, before, after, commits):
        graph, transfers = self.graph(project, repo), []
        old_id, head_id = self.commit_id(project, repo, before.head), self.commit_id(project, repo, after.head)
        forward = graph.path(head_id, old_id)
        findings, complete = graph.list('finding')
        if not complete:
            return [{'status': 'needs_review', 'reason': 'finding_page_incomplete'}]
        if forward:
            for m in findings:
                if m.branch_id == after.branch_id:
                    for c in reversed(commits):
                        cid = self.commit_id(project, repo, c['oid'])
                        if (c.get('authored') and c['oid'] != before.head and graph.path(head_id, cid)
                                and graph.path(cid, old_id) and graph.path(cid, self.commit_id(project, repo, m.head))
                                and self._matches(graph, m, cid)):
                            self.edge('PUBLISHES', cid, m, reason='authored_commit', observation=after.id)
                            break
            # An integration event freezes its candidate revisions. An old ancestor cannot
            # retroactively publish learning saved after the integration was observed.
            branches, branches_complete = graph.list('branch', limit=128)
            observations, observations_complete = graph.list('observation')
            if not branches_complete or not observations_complete:
                return [{'status': 'needs_review', 'reason': 'integration_observations_incomplete'}]
            for b in branches:
                if b.id == after.branch_id:
                    continue
                obs = [o for o in observations if o.branch_id == b.id and o.created_at <= after.created_at]
                if not obs:
                    continue
                tip = max(obs, key=lambda o: o.created_at)
                tip_id = self.commit_id(project, repo, tip.head)
                if graph.path(head_id, tip_id) and not graph.path(old_id, tip_id):
                    for m in findings:
                        if m.branch_id == b.id and m.created_at <= after.created_at:
                            continuous = bool(graph.path(tip_id, self.commit_id(project, repo, m.head)))
                            status = 'published' if continuous and self._matches(graph, m, head_id) else 'needs_review'
                            reason = 'verified_integration' if status == 'published' else ('source_mismatch' if continuous else 'origin_not_in_integrated_history')
                            event = self.record(project, repo, 'transfer', digest([after.id, m.id]), {'memory_id': m.id, 'status': status, 'reason': reason}, branch=after.branch_id, head=after.head)
                            if status == 'published':
                                self.edge('PUBLISHES', head_id, m, reason='verified_integration', observation=event.id)
                                self.edge('TRANSFERRED_FROM', event, m)
                            transfers.append(dict(event.data))
        else:
            transfers.append({'status': 'needs_review', 'reason': 'rewritten_or_incomplete_history'})
        return transfers

    def context(self, identity, project, context_id, write=False):
        if not self.projects.can_access(identity, project, write=write):
            raise PermissionError('Project membership does not allow this operation')
        n = self.store.get_node(context_id) if isinstance(context_id, str) else None
        if not isinstance(n, GitRecord) or n.workspace_project_id != project or n.kind != 'observation':
            raise ValueError('Synchronize the local Git bridge before using memory')
        if write and n.author != identity.user_id:
            raise PermissionError('Capture must use this user\'s connector context')
        return n

    def save(self, identity, project, payload, checkpoint=False):
        ctx = self.context(identity, project, payload.get('context_id'), write=True)
        graph = self.graph(project, ctx.repo_id)
        title, body, event = payload.get('title'), payload.get('body'), payload.get('event_id')
        if not isinstance(title, str) or not 1 <= len(title) <= 140 or not isinstance(body, str) or not 1 <= len(body) <= 4000:
            return fail('INVALID_MEMORY', 'Provide a title and concise text (maximum 4,000 characters)')
        if SECRET.search(title + '\n' + body):
            return fail('PRIVATE_CONTENT', 'Capture contains a credential pattern; remove it before saving')
        if not isinstance(event, str) or not 1 <= len(event) <= 150 or not isinstance(payload.get('session'), str) or not payload['session']:
            return fail('INVALID_EVENT', 'A stable event ID and session ID are required')
        classification = payload.get('classification', 'observation')
        if classification not in {'observation', 'interpretation', 'decision'}:
            return fail('INVALID_MEMORY', 'Classification must be observation, interpretation, or decision')
        paths = payload.get('paths', [])
        if not isinstance(paths, list) or len(paths) > 20 or any(not safe_path(p) for p in paths):
            return fail('INVALID_SOURCES', 'Provide at most 20 repository-relative paths')
        if not checkpoint and classification != 'decision' and not paths:
            return fail('SOURCES_REQUIRED', 'Automatic code claims require source bindings')
        snapshot = graph.get(ctx.snapshot_id)
        if any(p not in snapshot.data['sources'] for p in paths):
            return fail('SOURCES_NOT_OBSERVED', 'A source is private, missing, or outside the observed manifest')
        base_id = payload.get('supersedes_id')
        base = graph.get(base_id) if base_id else None
        kind = 'checkpoint' if checkpoint else 'finding'
        if base_id and (not base or base.kind != kind):
            return fail('INVALID_REVISION', 'Supersede an exact revision in this repository')
        if checkpoint and base and (base.author != identity.user_id or base.session != payload['session']):
            return fail('FORBIDDEN', 'Concurrent tasks keep separate checkpoints')
        resumes_id = payload.get('resumes_id')
        resumed = graph.get(resumes_id) if resumes_id else None
        if resumes_id and (not checkpoint or not resumed or resumed.kind != 'checkpoint'):
            return fail('INVALID_RESUMPTION', 'Resume an exact checkpoint in this repository; it remains an independent immutable task record')
        key = base.key if base else payload.get('conflict_key') or digest([identity.user_id, payload['session'], event])
        if not isinstance(key, str) or len(key) > 150:
            return fail('INVALID_MEMORY', 'Conflict keys must be short text identifiers')
        data = {'title': title, 'body': body, 'paths': paths, 'classification': classification,
                'supersedes_id': base_id, 'automatic': bool(payload.get('automatic', True))}
        if resumes_id:
            data['resumes_id'] = resumes_id
        tags = payload.get('tags', [])
        if not isinstance(tags, list) or len(tags) > 12 or any(not isinstance(tag, str) or len(tag) > 40 for tag in tags):
            return fail('INVALID_TAGS', 'Use at most twelve short text tags')
        if tags:
            data['tags'] = tags
        memory = self.record(project, ctx.repo_id, kind, key, data, branch=ctx.branch_id, head=ctx.head,
                             snapshot=ctx.snapshot_id, author=identity.user_id, session=payload['session'],
                             record_id=deterministic_id('revision', project, ctx.repo_id, identity.user_id, payload['session'], event))
        for p in paths:
            self.edge('SUPPORTED_BY', memory, self._source(project, ctx.repo_id, p, snapshot.data['sources'][p]))
        if base:
            self.edge('REVISES', memory, base)
        if resumed:
            self.edge('RESUMES', memory, resumed)
        # Activate last. A retry repairs missing source/revision relationships
        # before exposing the revision; an unacknowledged node is not a finding
        # the caller can safely use yet.
        self.edge('BRANCH_MEMORY', ctx.branch_id, memory)
        return {'ok': True, 'memory': record_to_dict(memory), 'legacy': False}

    def recall(self, identity, project, payload):
        ctx = self.context(identity, project, payload.get('context_id'))
        graph = self.graph(project, ctx.repo_id)
        candidates, complete = graph.candidates(ctx.branch_id, self.commit_id(project, ctx.repo_id, ctx.head), ctx.snapshot_id)
        evaluated, applicable = [], []
        query = set(re.findall(r'[a-z0-9_]+', str(payload.get('query', '')).lower()))
        for m, total, matches, published, promoted, branch in candidates:
            expected_sources = len(set(m.data.get('paths', [])))
            if total != expected_sources:
                state = 'incomplete_source_binding'
            elif total != matches:
                original = graph.get(m.snapshot_id)
                current = graph.get(ctx.snapshot_id)
                state = 'wip_requires_verification' if branch and (original.data.get('dirty') or current.data.get('dirty')) else 'historical_source_changed'
            elif m.snapshot_id != ctx.snapshot_id and branch and not published and not promoted:
                state = 'wip_requires_verification'
            else:
                state = 'applicable'
            if state == 'applicable':
                applicable.append(m.id)
            text = (m.data['title'] + ' ' + m.data['body'] + ' ' + ' '.join(m.data['paths'])).lower()
            score = sum(token in text for token in query) + (3 if m.kind == 'checkpoint' and m.session == payload.get('session') else 0)
            evaluated.append({'id': m.id, 'key': m.key, 'kind': m.kind, **m.data,
                              'author': m.author, 'session': m.session, 'branch_id': m.branch_id,
                              'source_commit': m.head, 'snapshot_id': m.snapshot_id,
                              'applicability': state, 'collection': 'conventions' if promoted else ('branch' if branch else 'inherited'),
                              'why': 'accepted_project_convention' if promoted else ('originating_branch' if branch else 'publication_in_git_ancestry'),
                              'source_matches': matches, 'source_count': total,
                              'expected_source_count': expected_sources, '_score': score})
        superseded = graph.superseded(applicable)
        exclusions = [{'id': m['id'], 'reason': 'superseded_in_current_scope'} for m in evaluated if m['id'] in superseded]
        excluded, exclusions_complete = graph.excluded([m['id'] for m in evaluated])
        exclusions.extend({'id': mid, 'reason': 'origin_branch_has_no_publication_in_current_ancestry'} for mid in excluded)
        exclusions.extend({'id': m['id'], 'reason': m['applicability']} for m in evaluated if m['applicability'] != 'applicable')
        visible = [m for m in evaluated if m['id'] not in superseded]
        conflicts = []
        groups = {}
        for m in visible:
            if m['applicability'] == 'applicable' and m['kind'] == 'finding':
                groups.setdefault(m['key'], []).append(m['id'])
        for key, ids in groups.items():
            if len(ids) > 1:
                conflicts.append({'key': key, 'revision_ids': ids, 'resolution': 'unresolved'})
        visible.sort(key=lambda m: (m['applicability'] != 'applicable', -m['_score'], m['id']))
        findings, checkpoints, used = [], [], 0
        for m in visible:
            m.pop('_score')
            # Conservative character budget also bounds hook JSON serialization.
            cost = len(json.dumps(m, ensure_ascii=False))
            target, cap = (checkpoints, 2) if m['kind'] == 'checkpoint' else (findings, 8)
            if len(target) >= cap or used + cost > 7800:
                exclusions.append({'id': m['id'], 'reason': 'context_budget'})
                continue
            target.append(m)
            used += cost
        exclusion_counts = {}
        for exclusion in exclusions:
            reason = exclusion['reason']
            exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
        result = {'ok': True, 'context_id': ctx.id, 'branch_id': ctx.branch_id, 'head': ctx.head,
                'snapshot_id': ctx.snapshot_id, 'findings': findings, 'checkpoints': checkpoints,
                'conflicts': [{**c, 'revision_ids': c['revision_ids'][:16], 'revision_count': len(c['revision_ids'])} for c in conflicts[:8]],
                'exclusions': exclusions[:8], 'exclusion_counts': exclusion_counts,
                'completeness': {'candidates_complete': complete, 'history_complete': ctx.data['history_complete'],
                                 'exclusions_complete': exclusions_complete and len(exclusions) <= 8,
                                 'conflicts_complete': len(conflicts) <= 8 and all(len(c['revision_ids']) <= 16 for c in conflicts),
                                 'manifest_complete': ctx.data['manifest_complete'], 'ancestry_depth_limit': 256,
                                 'context_truncated': any(e['reason'] == 'context_budget' for e in exclusions)},
                'budget': {'finding_limit': 8, 'checkpoint_limit': 2, 'approximate_tokens': (used + 3) // 4}}
        while len(json.dumps(result, ensure_ascii=False)) > 7900 and (findings or checkpoints):
            (findings if findings else checkpoints).pop()
            result['completeness']['context_truncated'] = True
            result['exclusion_counts']['context_budget'] = result['exclusion_counts'].get('context_budget', 0) + 1
        result['budget']['approximate_tokens'] = (len(json.dumps(result, ensure_ascii=False)) + 3) // 4
        return result

    def explain(self, identity, project, payload):
        ctx = self.context(identity, project, payload.get('context_id'))
        graph = self.graph(project, ctx.repo_id)
        m = graph.get(payload.get('memory_id'))
        if not m or m.kind not in {'finding', 'checkpoint'}:
            return fail('MEMORY_NOT_FOUND', 'Revision was not found in this repository')
        return {'ok': True, 'memory': record_to_dict(m),
                'inheritance_path': graph.explain(self.commit_id(project, ctx.repo_id, ctx.head), m.id),
                'branch_path': graph.links('BRANCH_MEMORY', from_id=ctx.branch_id, to_id=m.id),
                'promotion_path': graph.links('ACCEPTS', to_id=m.id),
                'sources': [dict(graph.get(s).data) for _, s, _ in graph.links('SUPPORTED_BY', from_id=m.id)],
                'supersession': graph.links('REVISES', from_id=m.id),
                'resumption': graph.links('RESUMES', from_id=m.id),
                'provenance_notice': 'Recorded connector observations and agent interpretations are not proof of truth'}

    def promote(self, identity, project, payload, accept=False):
        ctx = self.context(identity, project, payload.get('context_id'), write=not accept)
        graph = self.graph(project, ctx.repo_id)
        m = graph.get(payload.get('memory_id'))
        if not m or m.kind != 'finding':
            return fail('MEMORY_NOT_FOUND', 'Choose an exact finding revision')
        if accept and self.projects.role_for(identity, project) != 'owner':
            return fail('FORBIDDEN', 'The human project owner accepts conventions')
        if accept and not graph.get(deterministic_id('git', project, ctx.repo_id, 'promotion', m.id)):
            return fail('PROPOSAL_REQUIRED', 'Propose the convention before accepting it')
        kind = 'accepted_promotion' if accept else 'promotion'
        proposal = graph.get(deterministic_id('git', project, ctx.repo_id, kind, m.id)) or self.record(project, ctx.repo_id, kind, m.id, {'memory_id': m.id, 'conditions_preserved': True}, author=identity.user_id)
        if accept:
            self.edge('ACCEPTS', proposal, m)
        return {'ok': True, 'proposal': record_to_dict(proposal)}

    def no_change(self, identity, project, payload):
        ctx = self.context(identity, project, payload.get('context_id'), write=True)
        event = payload.get('event_id')
        if not isinstance(event, str) or not event or len(event) > 150:
            return fail('INVALID_EVENT', 'An event ID is required')
        record = self.record(project, ctx.repo_id, 'capture_receipt', digest([identity.user_id, payload.get('session'), event]),
                             {'outcome': 'nothing_useful_changed'}, branch=ctx.branch_id, head=ctx.head,
                             snapshot=ctx.snapshot_id, author=identity.user_id, session=str(payload.get('session', '')))
        return {'ok': True, 'receipt_id': record.id}

    def operation(self, identity, project, action, payload, human=False):
        try:
            if action == 'register': return self.register(identity, project, payload)
            if action == 'sync': return self.sync(identity, project, payload)
            if action == 'recall': return self.recall(identity, project, payload)
            if action in {'finding', 'checkpoint'}: return self.save(identity, project, payload, action == 'checkpoint')
            if action == 'explain': return self.explain(identity, project, payload)
            if action == 'propose': return self.promote(identity, project, payload)
            if action == 'accept':
                if not human: return fail('FORBIDDEN', 'Accept conventions in a human session')
                return self.promote(identity, project, payload, accept=True)
            if action == 'no-change': return self.no_change(identity, project, payload)
            return fail('UNKNOWN_OPERATION', 'Unknown Git memory operation')
        except PermissionError as exc:
            return fail('FORBIDDEN', str(exc))
        except ImmutableConflictError:
            return fail('IMMUTABLE_CONFLICT', 'This event ID already has different content; use a new revision event')
        except StoreError:
            return fail('STORAGE_UNAVAILABLE', 'The graph operation failed; retry without changing the original event binding')
        except (ValueError, TypeError, KeyError) as exc:
            return fail('INVALID_REQUEST', str(exc))
