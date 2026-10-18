"""Local Git authority, HTTP-backed MCP transport, and offline outbox.

No MCP schema accepts a branch name, hash, snapshot, or context ID from a model.
Queued captures retain the immutable observation they were originally bound to.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.request import Request, urlopen

from .git_memory import digest, SECRET, safe_path


DEFAULT_PRIVATE = ('.env', '.env.*', '**/.env', '**/.env.*', '*.pem', '**/*.pem', '*.key', '**/*.key',
                   '*credentials*', '**/*credentials*', '*secret*', '**/*secret*', '.git/**', '.local/**',
                   '.codex/**', '.claude/**', '.opencode/**', '.hivemind/**', '.mcp.json',
                   'opencode.json', 'opencode.jsonc')


def git(root, *args, check=True, binary=False):
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30)
    except FileNotFoundError:
        raise ValueError('Git is missing. Install Git, ensure it is on PATH, and retry the HiveMind command.') from None
    except subprocess.TimeoutExpired:
        raise ValueError('Git exceeded the 30-second observation limit. Finish any checkout or merge in progress, then retry.') from None
    if check and result.returncode:
        raise ValueError('Git could not read the requested repository state: ' + result.stderr.decode('utf-8', 'replace')[:200])
    return result.stdout if binary else result.stdout.decode('utf-8', 'replace').strip()


def local_dir(root):
    path = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'hivemind'))
    path.mkdir(parents=True, exist_ok=True)
    return path


def remote_identity(raw):
    if re.match(r'[^/]+@[^:]+:', raw):
        raw = 'ssh://' + raw.split('@', 1)[1].replace(':', '/', 1)
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.hostname:
        return parsed.hostname.lower() + parsed.path.removesuffix('.git').rstrip('/')
    return str(Path(raw).resolve()).replace('\\', '/').removesuffix('.git')


def blob_hashes(root, oid, paths):
    if not paths:
        return {}
    requests = b''.join((oid + ':' + p + '\n').encode('utf-8') for p in paths if '\n' not in p)
    result = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'], input=requests, capture_output=True, timeout=30)
    raw, cursor, hashes = result.stdout, 0, {}
    for path in [p for p in paths if '\n' not in p]:
        end = raw.find(b'\n', cursor)
        header = raw[cursor:end].split()
        cursor = end + 1
        if len(header) != 3 or header[1] != b'blob':
            continue
        size = int(header[2])
        content = raw[cursor:cursor + size]
        cursor += size + 1
        if size <= 1_000_000:
            # Git object IDs incorporate the canonical clean-filtered content.
            # Hash that content address so CRLF/LF checkouts share source identity.
            hashes[path] = hashlib.sha256(b'git-blob:' + header[0]).hexdigest()
    return hashes


def patch_id(root, before, after=None):
    args = ['diff', '--binary', before, after] if after else ['show', '--pretty=format:', '--binary', before]
    raw = git(root, *args, binary=True, check=False)
    result = subprocess.run(['git', 'patch-id', '--stable'], input=raw, capture_output=True, timeout=15)
    values = result.stdout.decode().split()
    return values[0] if values else None


def commit_metadata(root, oids):
    result = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'], input=('\n'.join(oids) + '\n').encode(), capture_output=True, timeout=30)
    raw, cursor, metadata = result.stdout, 0, {}
    for oid in oids:
        end = raw.find(b'\n', cursor)
        header = raw[cursor:end].split()
        cursor = end + 1
        if len(header) != 3 or header[1] != b'commit':
            raise ValueError('Git history includes an unavailable commit object')
        size = int(header[2])
        content = raw[cursor:cursor + size].decode('utf-8', 'replace').split('\n\n', 1)[0]
        cursor += size + 1
        parents = [line[7:] for line in content.splitlines() if line.startswith('parent ')]
        author = next((line for line in content.splitlines() if line.startswith('author ')), '')
        match = re.search(r'<([^>]+)>', author)
        metadata[oid] = {'parents': parents, 'email': match.group(1) if match else ''}
    return metadata


def history_mapping(root, source, destination):
    """Patch-equivalent unique replay, then exact aggregate squash mapping."""
    old_tip, new_tip = source['head'], destination
    base = git(root, 'merge-base', old_tip, new_tip, check=False)
    if not base or base == old_tip:
        return None
    old_range = git(root, 'rev-list', '--no-merges', '--max-count=257', base + '..' + old_tip, check=False).splitlines()
    new_range = git(root, 'rev-list', '--no-merges', '--max-count=257', base + '..' + new_tip, check=False).splitlines()
    if len(old_range) > 256 or len(new_range) > 256:
        return {'source_context': source['id'], 'method': 'incomplete', 'entries': []}
    old, new = {}, {}
    for oid in old_range:
        signature = patch_id(root, oid)
        if signature: old.setdefault(signature, []).append(oid)
    for oid in new_range:
        signature = patch_id(root, oid)
        if signature: new.setdefault(signature, []).append(oid)
    entries = []
    for signature in sorted(set(old) & set(new)):
        entries.append({'old': old[signature][0], 'new': new[signature][0], 'old_patch': signature, 'new_patch': signature,
                        'old_matches': len(old[signature]), 'new_matches': len(new[signature])})
    method = 'patch_id'
    old_sig, new_sig = patch_id(root, base, old_tip), patch_id(root, base, new_tip)
    if old_sig and old_sig == new_sig and len(new_range) == 1:
        method = 'squash'
        entries = [{'old': old_tip, 'new': new_tip, 'old_patch': old_sig, 'new_patch': new_sig, 'old_matches': 1, 'new_matches': 1}]
    return {'source_context': source['id'], 'method': method, 'entries': entries}


class LocalBridge:
    def __init__(self, root='.', *, config=None, session=None):
        self.root = Path(git(root, 'rev-parse', '--show-toplevel')).resolve()
        self.directory = local_dir(self.root)
        self.config_path = self.directory / 'config.json'
        if config is None and not self.config_path.is_file():
            raise ValueError('This repository is not connected. Run hivemind connect --repo ' + str(self.root) +
                             ' --url SERVICE_URL --project PROJECT_ID --client opencode using a project token. See hivemind connect --help.')
        self.config = config if config is not None else json.loads(self.config_path.read_text(encoding='utf-8'))
        self.session = session or 'mcp-' + secrets.token_hex(12)
        self.db_path = self.directory / ('cache-' + digest([self.config['url'], self.config['project_id']])[:12] + '.sqlite3')
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, action TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'pending\')')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.execute('PRAGMA busy_timeout=10000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default=None):
        with self.db() as db:
            row = db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(value)))

    def request(self, action, payload=None, *, get=False):
        token = os.environ.get('HIVEMIND_AGENT_TOKEN')
        token_path = self.directory / 'token'
        if not token and token_path.exists():
            token = token_path.read_text(encoding='utf-8').strip()
        if not token:
            raise ValueError('Set HIVEMIND_AGENT_TOKEN or reconnect with a project token')
        url = self.config['url'].rstrip('/') + '/api/projects/' + quote(self.config['project_id'], safe='') + '/git/' + action
        request = Request(url, data=None if get else json.dumps(payload or {}).encode(), method='GET' if get else 'POST',
                          headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=20) as response:
                value = json.load(response)
        except HTTPError as exc:
            if exc.code in {408, 429, 500, 502, 503, 504}:
                code = exc.code
                exc.close()
                raise URLError('HiveMind service is temporarily unavailable (HTTP ' + str(code) + '); retry when it recovers') from None
            try:
                value = json.load(exc)
            except (ValueError, OSError):
                value = {'ok': False, 'error': {'code': 'HTTP_ERROR', 'message': str(exc.code)}}
        if not value.get('ok'):
            raise ValueError(value.get('error', {}).get('code', 'REQUEST_REJECTED') + ': ' + value.get('error', {}).get('message', 'Rejected'))
        return value

    def allowed(self, path):
        patterns = list(DEFAULT_PRIVATE) + self.config.get('private_paths', [])
        ignore = self.root / '.hivemindignore'
        if ignore.is_file():
            patterns.extend(s.strip() for s in ignore.read_text(encoding='utf-8').splitlines() if s.strip() and not s.startswith('#'))
        if not safe_path(path) or any(fnmatch.fnmatch(path.lower(), p.lower()) for p in patterns):
            return False
        file = self.root / path
        try:
            file.resolve().relative_to(self.root)
        except ValueError:
            return False
        return not file.is_symlink()

    def check_capture_privacy(self, payload):
        """Reject credentials, excluded path references and literal private text.

        Content checks cover explicitly configured private files, with bounded
        local-only scanning. They are an additional guard, not a claim that
        arbitrary paraphrased sensitive information can be recognized.
        """
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for key, item in value.items():
                    yield str(key)
                    yield from strings(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    yield from strings(item)
        texts = list(strings(payload))
        if any(SECRET.search(value) for value in texts):
            raise ValueError('PRIVATE_CONTENT: Capture contains a credential pattern; remove it before saving')
        if any(not self.allowed(p) for p in payload.get('paths', [])):
            raise ValueError('PRIVATE_CONTENT: Capture references a private or unsafe source path')
        normalized = '\n'.join(value.replace('\\', '/') for value in texts)
        normalized = re.sub(re.escape(self.root.as_posix()) + '/', '', normalized, flags=re.I)
        references = re.findall(r'(?<![\w/])(?:\.[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+|[A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+)(?![\w/])', normalized)
        if any(p.rstrip('.') and not self.allowed(p.rstrip('.')) for p in references):
            raise ValueError('PRIVATE_CONTENT: Capture text references an excluded path')
        patterns = list(self.config.get('private_paths', []))
        ignore = self.root / '.hivemindignore'
        if ignore.is_file():
            patterns += [line.strip() for line in ignore.read_text(encoding='utf-8').splitlines()
                         if line.strip() and not line.startswith('#')]
        if not patterns:
            return
        visited, candidates, scanned = set(), set(), 0
        for pattern in patterns:
            # Walk only the literal directory prefix. Matching still uses fnmatch
            # semantics, where '*' may cross '/'. Never follow directory symlinks.
            prefix = re.split(r'[*?\[]', pattern.replace('\\', '/'), 1)[0]
            directory = self.root / (prefix.rsplit('/', 1)[0] if '/' in prefix else '')
            try:
                directory.resolve().relative_to(self.root)
            except ValueError:
                raise ValueError('PRIVATE_CONTENT: Private capture patterns must stay within this repository')
            for parent, dirs, files in os.walk(directory, followlinks=False):
                dirs[:] = [d for d in dirs if d != '.git' and not (Path(parent) / d).is_symlink()]
                for filename in files:
                    file = Path(parent) / filename
                    if file in visited:
                        continue
                    visited.add(file)
                    if len(visited) > 8192:
                        raise ValueError('PRIVATE_CONTENT: Private-content scan exceeds 8192 files; narrow the configured patterns before capturing')
                    relative = file.relative_to(self.root).as_posix()
                    if any(fnmatch.fnmatch(relative.lower(), p.lower()) for p in patterns):
                        candidates.add(file)
        capture = re.sub(r'\s+', ' ', '\n'.join(texts)).strip()
        for file in sorted(candidates):
            if file.is_symlink():
                continue
            relative = file.relative_to(self.root).as_posix()
            if re.search(r'(?<![\w/])' + re.escape(relative) + r'(?![\w/])', normalized, flags=re.I):
                raise ValueError('PRIVATE_CONTENT: Capture text references a configured private file')
            stat = file.stat()
            scanned += stat.st_size
            if stat.st_size > 1_000_000 or scanned > 8_000_000 or len(candidates) > 256:
                raise ValueError('PRIVATE_CONTENT: Private-content scan exceeds its local size bound; narrow the configured patterns before capturing')
            raw = file.read_text(encoding='utf-8', errors='replace')
            whole = re.sub(r'\s+', ' ', raw.strip())
            if whole and re.search(r'(?<!\w)' + re.escape(whole) + r'(?!\w)', capture):
                raise ValueError('PRIVATE_CONTENT: Capture copies text from a configured private file')
            for piece in (line.strip() for line in raw.splitlines()):
                piece = re.sub(r'\s+', ' ', piece)
                if len(piece) >= 12 and piece in capture:
                    raise ValueError('PRIVATE_CONTENT: Capture copies text from a configured private file')

    def observe(self, paths=()):
        head = git(self.root, 'rev-parse', 'HEAD')
        ref = git(self.root, 'symbolic-ref', '-q', 'HEAD', check=False) or 'detached:' + head
        known_paths = self.get('watched_paths', [])
        selected = sorted({*known_paths, *paths})
        listed = git(self.root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard', binary=True).decode('utf-8', 'replace').split('\0')
        eligible = sorted({p for p in listed if self.allowed(p)})
        selected = [p for p in selected if self.allowed(p)]
        selected += [p for p in eligible if p not in selected]
        source_limit = min(2048, max(20, int(self.config.get('source_limit', 128))))
        manifest_complete = len(selected) <= source_limit
        selected = selected[:source_limit]
        sources, source_stats = {}, {}
        for path in selected:
            file = self.root / path
            if not file.is_file():
                continue
            before_read = file.stat()
            if before_read.st_size > 1_000_000:
                manifest_complete = False
                continue
            raw = file.read_bytes()
            after_read = file.stat()
            if (before_read.st_size, before_read.st_mtime_ns, before_read.st_ino) != (after_read.st_size, after_read.st_mtime_ns, after_read.st_ino):
                raise ValueError('Sources changed during Git observation; retry the operation')
            # Only hashes travel, but credential-bearing/private files also cannot bind claims.
            if SECRET.search(raw.decode('utf-8', 'replace')):
                continue
            sources[path] = ''
            source_stats[path] = (after_read.st_size, after_read.st_mtime_ns, after_read.st_ino)
        if sources:
            ordered = sorted(sources)
            raw_paths = ''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in ordered).encode('utf-8')
            result = subprocess.run(['git', '-C', str(self.root), 'hash-object', '--stdin-paths'], input=raw_paths, capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError('Git could not compute canonical source hashes')
            ids = result.stdout.splitlines()
            if len(ids) != len(ordered):
                raise ValueError('Git source manifest was incomplete')
            sources = {path: hashlib.sha256(b'git-blob:' + oid).hexdigest() for path, oid in zip(ordered, ids)}
            for path, observed in source_stats.items():
                current = self.root / path
                stat = current.stat() if current.is_file() else None
                if stat is None or (stat.st_size, stat.st_mtime_ns, stat.st_ino) != observed:
                    raise ValueError('Sources changed during Git observation; retry the operation')
        history_limit = min(256, max(2, int(self.config.get('history_limit', 64))))
        lines = git(self.root, 'rev-list', '--parents', '--max-count=' + str(history_limit + 1), 'HEAD').splitlines()
        shallow = git(self.root, 'rev-parse', '--is-shallow-repository') == 'true'
        email = git(self.root, 'config', 'user.email', check=False)
        commits = []
        metadata = commit_metadata(self.root, [line.split()[0] for line in lines[:history_limit]])
        watched = [p for p in {*known_paths, *paths} if self.allowed(p)][:80]
        for line in reversed(lines[:history_limit]):
            parts = line.split()
            oid = parts[0]
            manifest = blob_hashes(self.root, oid, list(sources) if oid == head else watched)
            # Current HEAD's full manifest supports clean observations. Older manifests
            # only load referenced paths, keeping large repositories bounded.
            author = metadata[oid]['email']
            commits.append({'oid': oid, 'parents': metadata[oid]['parents'], 'sources': manifest, 'authored': bool(email and author == email)})
        status = git(self.root, 'status', '--porcelain=v1', '-z', '--untracked-files=normal', binary=True)
        branches = self.get('branches', {})
        present = set(git(self.root, 'for-each-ref', '--format=%(refname)', 'refs/heads').splitlines())
        births = self.get('branch_births', {})
        for recorded in list(branches):
            if recorded not in present:
                branches.pop(recorded, None)
                births.pop(recorded, None)
        if ref in present:
            reflog = Path(git(self.root, 'rev-parse', '--path-format=absolute', '--git-path', 'logs/' + ref))
            if reflog.is_file():
                with reflog.open('rb') as stream:
                    # The file identity distinguishes delete/recreate even if Git
                    # wrote identical reflog text within the same timestamp second.
                    stat = reflog.stat()
                    birth = digest([stat.st_dev, stat.st_ino, stream.readline().hex()])
                if ref in births and births[ref] != birth:
                    # Ref recreation or rewritten/expired reflog requires a new identity.
                    branches.pop(ref, None)
                births[ref] = birth
            else:
                births.setdefault(ref, secrets.token_hex(16))
        self.set('branches', branches)
        self.set('branch_births', births)
        if git(self.root, 'rev-parse', 'HEAD') != head or (git(self.root, 'symbolic-ref', '-q', 'HEAD', check=False) or 'detached:' + head) != ref:
            raise ValueError('Git checkout changed during observation; retry the operation')
        for path, observed in source_stats.items():
            file = self.root / path
            stat = file.stat() if file.is_file() else None
            if stat is None or (stat.st_size, stat.st_mtime_ns, stat.st_ino) != observed:
                raise ValueError('Sources changed during Git observation; retry the operation')
        if sources:
            # Stat checks alone miss same-size edits whose mtime was restored by
            # file synchronization. Recheck canonical content at the boundary.
            ordered = sorted(sources)
            raw_paths = ''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in ordered).encode('utf-8')
            result = subprocess.run(['git', '-C', str(self.root), 'hash-object', '--stdin-paths'], input=raw_paths, capture_output=True, timeout=30)
            latest = result.stdout.splitlines()
            if result.returncode or len(latest) != len(ordered) or any(
                    hashlib.sha256(b'git-blob:' + oid).hexdigest() != sources[path] for path, oid in zip(ordered, latest)):
                raise ValueError('Sources changed during Git observation; retry the operation')
        context = {'repo_id': self.config['repo_id'], 'connector_id': self.config['connector_id'],
                   'head': head, 'ref': ref, 'branch_id': branches.get(ref),
                   'branch_incarnation': births.get(ref) or digest([self.config['connector_id'], ref]),
                   'commits': commits, 'sources': sources,
                   'dirty': bool(status), 'dirty_hash': hashlib.sha256(status).hexdigest(),
                   'manifest_complete': manifest_complete, 'shallow': shallow,
                   'history_complete': len(lines) <= history_limit and not shallow,
                   'previous_context': self.get('context', {}).get('context_id'), 'event_id': digest([head, sources, status.hex()])}
        return context

    def sync(self, paths=()):
        try:
            watch = self.request('watch?repo_id=' + quote(self.config['repo_id']), get=True)
            self.set('watched_paths', watch['paths'])
            context = self.observe(paths)
            # Cross-branch rewriting requires a previously recorded source tip and
            # deterministic Git patch mappings; names do not establish continuity.
            before = self.get('context', {})
            if before.get('head') != context['head']:
                overview = self.request('overview?repo_id=' + quote(self.config['repo_id']), get=True)
                mappings = []
                for source in overview['observation'][:32]:
                    if source['head'] != context['head']:
                        mapping = history_mapping(self.root, source, context['head'])
                        if mapping: mappings.append(mapping)
                context['mappings'] = mappings
            response = self.request('sync', context)
            branches = self.get('branches', {})
            branches[context['ref']] = response['branch_id']
            self.set('branches', branches)
            self.set('context', response)
            self.flush()
            return response
        except (URLError, TimeoutError, ConnectionError, OSError):
            cached = self.get('context')
            if not cached:
                raise ValueError('HiveMind is offline and no prior context is cached')
            # Bind a queued observation before capture, never borrow another checkout's context.
            observation = self.observe(paths)
            ticket = 'offline:' + digest(observation)
            with self.db() as db:
                db.execute('INSERT INTO outbox(action,payload) VALUES (?,?)', ('sync', json.dumps(dict(observation, _ticket=ticket))))
            return dict(cached, context_id=ticket, offline=True, head=observation['head'])

    def enqueue(self, action, payload):
        with self.db() as db:
            db.execute('INSERT INTO outbox(action,payload) VALUES (?,?)', (action, json.dumps(payload)))

    def flush(self):
        # SQLite serializes concurrent hook/MCP processes. Network I/O is bounded.
        rejected = False
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id,action,payload FROM outbox WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
            tickets = self.get('tickets', {})
            branches = self.get('branches', {})
            for row_id, action, raw in rows:
                payload = json.loads(raw)
                ticket = payload.pop('_ticket', None)
                if str(payload.get('context_id', '')).startswith('offline:'):
                    if payload['context_id'] not in tickets:
                        break
                    payload['context_id'] = tickets[payload['context_id']]
                if action == 'sync':
                    if str(payload.get('previous_context', '')).startswith('offline:'):
                        payload['previous_context'] = tickets.get(payload['previous_context'])
                    # Never resolve an old queued ref through today's branch map.
                    # The original incarnation creates/joins its own stable identity.
                try:
                    result = self.request(action, payload)
                except ValueError:
                    db.execute("UPDATE outbox SET status='rejected' WHERE id=?", (row_id,))
                    if payload.get('session'):
                        db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_status:' + payload['session'], json.dumps('failed')))
                    db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_warning', json.dumps('A queued capture was rejected and quarantined. Inspect bridge status before retrying.')))
                    rejected = True
                    # Commit quarantine and successful earlier deliveries. Raising
                    # inside this transaction would roll all of those back.
                    continue
                except (URLError, OSError, TimeoutError):
                    break
                if ticket:
                    tickets[ticket] = result['context_id']
                if action == 'sync' and payload.get('branch_incarnation') == self.get('branch_births', {}).get(payload['ref']):
                    branches[payload['ref']] = result['branch_id']
                db.execute('DELETE FROM outbox WHERE id=?', (row_id,))
                if action in {'finding', 'checkpoint', 'no-change'} and payload.get('session'):
                    session = payload['session']
                    remaining = db.execute("SELECT status FROM outbox WHERE action IN ('finding','checkpoint','no-change') AND json_extract(payload,'$.session')=?", (session,)).fetchall()
                    statuses = {r[0] for r in remaining}
                    status = 'failed' if 'rejected' in statuses else ('queued' if 'pending' in statuses else ('no_change' if action == 'no-change' else 'saved'))
                    db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_status:' + session, json.dumps(status)))
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('tickets', json.dumps(tickets)))
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('branches', json.dumps(branches)))
        if rejected:
            raise ValueError('A queued capture was rejected and quarantined; inspect python -m hivemind.bridge status')

    def call(self, action, payload):
        # A model may request source paths; Git, never the model, supplies hashes/context.
        if action in {'finding', 'checkpoint', 'no-change'}:
            # Validate before synchronization or outbox writes. Offline delivery
            # must have the same privacy boundary as an online service save.
            self.check_capture_privacy(payload)
        context = self.sync(payload.get('paths', []))
        arguments = {**payload, 'context_id': context['context_id']}
        if action in {'finding', 'checkpoint', 'no-change'}:
            # Session ownership belongs to the local transport/adapter. A model
            # cannot impersonate a concurrent task by naming its session.
            arguments['session'] = self.session
            arguments.setdefault('event_id', digest([self.session, action, payload]))
            arguments['automatic'] = True
        if context.get('offline'):
            if action == 'recall':
                cached = self.get('recall', {})
                return {'ok': True, 'offline': True, 'warning': 'Cached context belongs to an earlier observation; verify before use', 'cached_context': cached}
            if action in {'finding', 'checkpoint', 'no-change'}:
                self.enqueue(action, arguments)
                self.set('capture:' + arguments['session'], [action])
                self.set('capture_status:' + arguments['session'], 'queued')
                return {'ok': True, 'queued': True, 'original_context': arguments['context_id']}
            raise ValueError('HiveMind must be online for this operation')
        try:
            result = self.request(action, arguments)
        except (URLError, OSError, TimeoutError):
            if action in {'finding', 'checkpoint', 'no-change'}:
                self.enqueue(action, arguments)
                self.set('capture:' + arguments['session'], sorted(set(self.get('capture:' + arguments['session'], []) + [action])))
                self.set('capture_status:' + arguments['session'], 'queued')
                return {'ok': True, 'queued': True, 'original_context': arguments['context_id']}
            raise
        if action == 'recall':
            self.set('recall', result)
        elif action in {'finding', 'checkpoint', 'no-change'}:
            key = 'capture:' + arguments['session']
            self.set(key, sorted(set(self.get(key, []) + [action])))
            self.set('capture_status:' + arguments['session'], 'no_change' if action == 'no-change' else 'saved')
        return result


TOOL_ACTIONS = {'recall_context': 'recall', 'save_finding': 'finding', 'save_checkpoint': 'checkpoint',
                'explain_memory': 'explain', 'propose_promotion': 'propose', 'record_no_change': 'no-change',
                'list_memories': 'recall', 'create_memory': 'finding', 'edit_memory': 'finding'}


def tool_definitions():
    text = {'type': 'string'}
    schemas = {
        'recall_context': ({'query': text, 'session': text}, []),
        'save_finding': ({'title': text, 'body': text, 'paths': {'type': 'array', 'items': text}, 'classification': {'enum': ['observation', 'interpretation', 'decision']}, 'supersedes_id': text, 'event_id': text, 'session': text, 'conflict_key': text}, ['title', 'body']),
        'save_checkpoint': ({'title': text, 'body': text, 'paths': {'type': 'array', 'items': text},
            'supersedes_id': {'type': 'string', 'description': 'Revise only this session\'s own checkpoint. Never supersede another session\'s checkpoint.'},
            'resumes_id': {'type': 'string', 'description': 'Exact checkpoint ID whose work this new session continues. Records lineage without changing or hiding the earlier task.'},
            'event_id': text, 'session': text}, ['title', 'body']),
        'explain_memory': ({'memory_id': text}, ['memory_id']),
        'propose_promotion': ({'memory_id': text}, ['memory_id']),
        'record_no_change': ({'event_id': text, 'session': text}, []),
    }
    schemas['list_memories'] = schemas['recall_context']
    schemas['create_memory'] = ({**schemas['save_finding'][0], 'tags': {'type': 'array', 'items': text}}, ['title', 'body'])
    schemas['edit_memory'] = ({**schemas['create_memory'][0], 'memory_id': text}, ['memory_id'])
    return [{'name': name, 'description': {'recall_context': 'Recall relevant Git-bound team findings and task checkpoints for this checkout.',
             'save_finding': 'Save concise learning with verified local source hashes. Preserve conditions and uncertainty.',
             'save_checkpoint': 'Save progress for this session: completed work, remaining questions and next steps. Use resumes_id to continue a prior session; supersedes_id is restricted to your own session.',
             'record_no_change': 'Record that the automatic memory pass found nothing useful to save.'}.get(name, name.replace('_', ' ')),
             'inputSchema': {'type': 'object', 'properties': props, 'required': required, 'additionalProperties': False}}
            for name, (props, required) in schemas.items()]


def serve_mcp(bridge, input_stream=sys.stdin, output_stream=sys.stdout):
    for line in input_stream:
        try:
            if len(line) > 1_000_000:
                raise ValueError('Request too large')
            request = json.loads(line)
            if not isinstance(request, dict) or request.get('jsonrpc') != '2.0':
                raise ValueError('Invalid JSON-RPC request')
            if 'id' not in request:
                continue
            method = request.get('method')
            if method == 'initialize':
                result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'hivemind-git-bridge', 'version': '0.2.0'}}
            elif method == 'tools/list':
                result = {'tools': tool_definitions()}
            elif method == 'tools/call':
                params = request.get('params', {})
                name, arguments = params.get('name'), params.get('arguments', {})
                definition = next((d for d in tool_definitions() if d['name'] == name), None)
                if not definition or not isinstance(arguments, dict) or set(arguments) - set(definition['inputSchema']['properties']):
                    raise ValueError('Unknown tool or unsupported arguments; Git context is supplied locally')
                if any(key not in arguments for key in definition['inputSchema']['required']):
                    raise ValueError('Required tool arguments are missing')
                if name == 'edit_memory':
                    arguments = dict(arguments)
                    revision = arguments.pop('memory_id')
                    prior = bridge.call('explain', {'memory_id': revision})['memory']['data']
                    arguments = {**{k: prior[k] for k in ('title', 'body', 'paths', 'classification')}, **arguments, 'supersedes_id': revision}
                value = bridge.call(TOOL_ACTIONS[name], arguments)
                result = {'content': [{'type': 'text', 'text': json.dumps(value)}], 'structuredContent': value, 'isError': not value.get('ok')}
            else:
                output_stream.write(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32601, 'message': 'Method not found'}}) + '\n')
                output_stream.flush()
                continue
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except Exception as exc:
            value = {'ok': False, 'error': {'code': 'BRIDGE_FAILED', 'message': str(exc)}}
            response = {'jsonrpc': '2.0', 'id': request.get('id') if isinstance(locals().get('request'), dict) else None,
                        'result': {'content': [{'type': 'text', 'text': json.dumps(value)}], 'isError': True}}
        output_stream.write(json.dumps(response) + '\n')
        output_stream.flush()


def connect(args):
    root = Path(git(args.repo, 'rev-parse', '--show-toplevel')).resolve()
    directory = local_dir(root)
    config_path = directory / 'config.json'
    config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    if config and (config['url'] != args.url or config['project_id'] != args.project):
        raise ValueError('This worktree is already connected to a different project; use a separate worktree')
    config.update(url=args.url, project_id=args.project, connector_id=config.get('connector_id', secrets.token_hex(16)))
    bridge = LocalBridge(root, config=config)
    token = os.environ.get('HIVEMIND_AGENT_TOKEN')
    if token:
        (directory / 'token').write_text(token, encoding='utf-8')
        (directory / 'token').chmod(0o600)
    raw_remote = args.remote or git(root, 'remote', 'get-url', 'origin', check=False) or str(root)
    if git(root, 'rev-parse', '--is-shallow-repository') == 'true' and not args.repository_id:
        raise ValueError('A shallow clone must join the existing repository using --repository-id, or fetch full history')
    root_commit = git(root, 'rev-list', '--max-parents=0', 'HEAD').splitlines()[0]
    result = bridge.request('register', {'remote': remote_identity(raw_remote), 'root_commit': root_commit, 'repository_id': args.repository_id})
    config['repo_id'] = result['repo_id']
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    if args.branch_id:
        ref = git(root, 'symbolic-ref', '-q', 'HEAD')
        branches = bridge.get('branches', {})
        branches[ref] = args.branch_id
        bridge.set('branches', branches)
    context = bridge.sync()
    from .client_adapters import install
    installed = install(bridge, args.client)
    return {'ok': True, **context, 'adapters': installed, 'hook_trust':
            'Review the project plugin and tool permissions in OpenCode. Existing permissions are unchanged.' if args.client == 'opencode' else
            'Review the installed definitions in the selected client. Codex: /hooks. Trust is never bypassed.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='HiveMind local Git bridge')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('connect')
    p.add_argument('--repo', default='.')
    p.add_argument('--url', required=True)
    p.add_argument('--project', required=True)
    p.add_argument('--remote')
    p.add_argument('--repository-id', help='Join an existing repository, required for shallow clones')
    p.add_argument('--branch-id', help='Explicitly join a teammate\'s recorded branch identity')
    p.add_argument('--client', choices=['opencode', 'codex', 'claude', 'both'], default='opencode')
    p = sub.add_parser('run', help='Launch native OpenCode and finish its bounded memory pass before host shutdown')
    p.add_argument('--repo', default='.')
    p.add_argument('--model')
    p.add_argument('--format', choices=['default', 'json'], default='default')
    p.add_argument('prompt', nargs='*')
    for name in ('mcp', 'status', 'sync', 'hook', 'opencode-event'):
        p = sub.add_parser(name)
        p.add_argument('--repo', default='.')
        if name == 'hook': p.add_argument('--client', choices=['codex', 'claude'], required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'connect':
            result = connect(args)
        else:
            bridge = LocalBridge(args.repo)
            if args.command == 'run':
                from .opencode_runner import run
                return run(bridge, args)
            if args.command == 'mcp':
                serve_mcp(bridge)
                return 0
            if args.command == 'hook':
                from .client_adapters import hook
                result = hook(bridge, args.client, json.load(sys.stdin))
            elif args.command == 'opencode-event':
                from .opencode_adapter import handle
                result = handle(bridge, json.load(sys.stdin))
            elif args.command == 'sync':
                result = bridge.sync()
            else:
                with bridge.db() as db:
                    queue = db.execute('SELECT id,action,status FROM outbox ORDER BY id').fetchall()
                    statuses = db.execute("SELECT key,value FROM state WHERE key LIKE 'capture_status:%' ORDER BY rowid DESC LIMIT 20").fetchall()
                    failures = db.execute("SELECT value FROM state WHERE key LIKE 'capture_failure:%' ORDER BY rowid DESC LIMIT 20").fetchall()
                result = {'ok': True, 'context': bridge.get('context'), 'outbox': queue,
                          'capture_statuses': {key.removeprefix('capture_status:'): json.loads(value) for key, value in statuses},
                          'capture_failures': [json.loads(value) for (value,) in failures],
                          'capture_warning': bridge.get('capture_warning')}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        error = {'systemMessage': 'HiveMind: ' + str(exc)} if args.command == 'hook' else {'ok': False, 'error': str(exc)}
        print(json.dumps(error), file=sys.stdout if args.command == 'hook' else sys.stderr)
        return 0 if args.command == 'hook' else 1


if __name__ == '__main__':
    raise SystemExit(main())
