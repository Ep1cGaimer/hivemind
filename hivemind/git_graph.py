"""Bounded project/repository graph access with equivalent offline traversal."""
from __future__ import annotations

import json
from collections import deque
from .domain import GitRecord


class RepositoryGraph:
    LIMIT = 1024

    def __init__(self, store, project_id, repo_id):
        self.store, self.project_id, self.repo_id = store, project_id, repo_id
        self.live = getattr(store, 'backend_name', '') == 'falkordb'

    def run(self, query, **params):
        result = self.store.run_fixed(query, dict(workspace_project_id=self.project_id, repo_id=self.repo_id, **params))
        return self.store._rows(result)

    def get(self, node_id):
        n = self.store.get_node(node_id) if isinstance(node_id, str) else None
        return n if isinstance(n, GitRecord) and n.workspace_project_id == self.project_id and n.repo_id == self.repo_id else None

    def list(self, kind='', cursor='', limit=LIMIT):
        limit = min(max(1, limit), self.LIMIT)
        if self.live:
            rows = self.run('git_list', kind=kind, cursor=cursor, limit=limit + 1)
            nodes = [self.store._node_from_row(r) for r in rows]
        else:
            nodes = [n for n in self.store.nodes('GitRecord') if n.workspace_project_id == self.project_id
                     and (not self.repo_id or n.repo_id == self.repo_id) and (not kind or n.kind == kind) and n.id > cursor]
            nodes.sort(key=lambda n: n.id)
        return nodes[:limit], len(nodes) <= limit

    def links(self, edge_type, from_id='', to_id=''):
        if self.live:
            rows = self.run('git_links', edge_type=edge_type, from_id=from_id, to_id=to_id, limit=self.LIMIT + 1)
            if len(rows) > self.LIMIT:
                raise ValueError('Relationship page incomplete; narrow the query')
            return [(r[0], r[1], json.loads(r[2])) for r in rows]
        return [(e.from_id, e.to_id, dict(e.properties)) for e in self.store.edges(edge_type)
                if (not from_id or e.from_id == from_id) and (not to_id or e.to_id == to_id)
                and self.get(e.from_id) and self.get(e.to_id)]

    def path(self, head_id, commit_id):
        if self.live:
            rows = self.run('git_path', head_id=head_id, commit_id=commit_id)
            return rows[0][0] if rows else None
        todo, seen = deque([(head_id, [head_id])]), set()
        while todo:
            current, path = todo.popleft()
            if current in seen or len(path) > 257:
                continue
            seen.add(current)
            if current == commit_id:
                return path
            todo.extend((b, path + [b]) for _, b, _ in self.links('PARENT', from_id=current))
        return None

    def candidates(self, branch_id, head_id, snapshot_id):
        if self.live:
            rows = self.run('git_candidates', branch_id=branch_id, head_id=head_id, snapshot_id=snapshot_id, limit=self.LIMIT + 1)
            source_rows = self.run('git_applicability', candidate_ids=[r[0] for r in rows[:self.LIMIT]], snapshot_id=snapshot_id, limit=self.LIMIT + 1) if rows else []
            counts = {r[0]: (r[1], r[2]) for r in source_rows}
            return [(self.store._node_from_row(r), *counts.get(r[0], (0, 0)), *r[7:10]) for r in rows[:self.LIMIT]], len(rows) <= self.LIMIT
        findings, complete = self.list()
        results = []
        for n in findings:
            if n.kind not in {'finding', 'checkpoint'}:
                continue
            branch = bool(self.links('BRANCH_MEMORY', from_id=branch_id, to_id=n.id))
            publication = any(self.path(head_id, a) for a, _, _ in self.links('PUBLISHES', to_id=n.id))
            promotion = bool(self.links('ACCEPTS', to_id=n.id))
            if branch or publication or promotion:
                sources = self.links('SUPPORTED_BY', from_id=n.id)
                matched = sum(bool(self.links('HAS_SOURCE', from_id=snapshot_id, to_id=s)) for _, s, _ in sources)
                results.append((n, len(sources), matched, int(publication), int(promotion), int(branch)))
        return results, complete

    def superseded(self, ids):
        if not ids:
            return set()
        if self.live:
            rows = self.run('git_revisions', applicable_ids=ids, limit=self.LIMIT + 1)
            if len(rows) > self.LIMIT:
                raise ValueError('Supersession traversal incomplete')
            return {r[1] for r in rows}
        return {b for a in ids for _, b, _ in self.links('REVISES', from_id=a) if b in ids}

    def explain(self, head_id, memory_id):
        if self.live:
            rows = self.run('git_explain', head_id=head_id, memory_id=memory_id)
            return rows[0][0] if rows else None
        for a, _, _ in self.links('PUBLISHES', to_id=memory_id):
            path = self.path(head_id, a)
            if path:
                return path + [memory_id]
        return None

    def excluded(self, candidate_ids):
        if self.live:
            rows = self.run('git_excluded', candidate_ids=candidate_ids, limit=129)
            return [r[0] for r in rows[:128]], len(rows) <= 128
        nodes, complete = self.list()
        ids = [n.id for n in nodes if n.kind in {'finding', 'checkpoint'} and n.id not in candidate_ids]
        return ids[:128], complete and len(ids) <= 128
