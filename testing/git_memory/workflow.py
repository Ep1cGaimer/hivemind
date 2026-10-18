"""Prepare native clients or validate an existing OpenTelemetry checkout.

Start the service separately. Credentials and run artifacts remain in .local/.
Native hooks must be reviewed in each client; this helper never trusts them.
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.request import build_opener, HTTPCookieProcessor, Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hivemind.bridge import LocalBridge, connect, git, remote_identity


def request(base, path, payload=None, *, opener=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    with (opener or build_opener()).open(req, timeout=60) as response:
        result = json.load(response)
    if not result.get('ok'): raise ValueError(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'opentelemetry'])
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    parser.add_argument('--repo', type=Path, default=ROOT / '.local' / 'opentelemetry.io')
    args = parser.parse_args()
    state = ROOT / '.local' / 'git-memory'
    state.mkdir(parents=True, exist_ok=True)
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request(args.url, '/api/auth/login', {'username': 'operator', 'password': os.environ.get('HIVEMIND_TRIAL_PASSWORD', 'operator')}, opener=opener)
    prior_file = state / 'native-connection.json'
    if args.mode == 'prepare' and prior_file.exists():
        prior = json.loads(prior_file.read_text())
        project, token = prior['project_id'], prior['token']
        request(args.url, '/api/projects/' + project, token=token)
    else:
        project = request(args.url, '/api/projects', {'name': 'Git memory ' + args.mode, 'description': 'Isolated integration verification; native hook trust is user controlled.'}, opener=opener)['project']['id']
        token = request(args.url, '/api/projects/' + project + '/agents', {'label': 'Git workflow verification'}, opener=opener)['token']
    os.environ['HIVEMIND_AGENT_TOKEN'] = token
    if args.mode == 'prepare':
        root = state / 'native-fixture'
        root.mkdir(exist_ok=True)
        if not (root / '.git').exists():
            git(root, 'init', '-b', 'main')
            git(root, 'config', 'user.name', 'HiveMind fixture')
            git(root, 'config', 'user.email', 'fixture@example.test')
            (root / 'guide.txt').write_text('Use bounded queues. Shared queues are untested; validate them before deployment.\n')
            (root / 'worker.py').write_text('def queue_limit():\n    return 32\n')
            git(root, 'add', '.')
            git(root, 'commit', '-m', 'Independent native fixture')
        result = connect(SimpleNamespace(repo=str(root), url=args.url, project=project, remote='fixture.invalid/native', repository_id=None, branch_id=None, client='both'))
        (state / 'native-connection.json').write_text(json.dumps({'project_id': project, 'token': token, 'root': str(root)}, indent=2))
        print(json.dumps({'ok': True, 'project_id': project, 'root': str(root), 'adapters': result['adapters'],
            'next': 'Open Codex in this fixture and review /hooks. Review Claude project/MCP trust. Then use ordinary work prompts.'}, indent=2))
        return
    root = args.repo.resolve()
    before = hashlib.sha256(git(root, 'diff', '--binary', binary=True)).hexdigest()
    path = 'content/en/site/build/dependencies.md'
    text = (root / path).read_text(encoding='utf-8')
    if 'optional' not in text.lower():
        raise ValueError('Expected dependency guidance is absent; do not invent a finding')
    bridge = LocalBridge(root, config={'url': args.url, 'project_id': project, 'repo_id': '', 'connector_id': 'opentelemetry-git-validation'})
    repo = bridge.request('register', {'remote': remote_identity(git(root, 'remote', 'get-url', 'origin')), 'root_commit': git(root, 'rev-list', '--max-parents=0', 'HEAD').splitlines()[0]})['repo_id']
    bridge.config['repo_id'] = repo
    bridge.set('watched_paths', [path, 'content/en/docs/contributing/development.md'])
    memory = bridge.call('finding', {'title': 'OpenTelemetry optional build dependencies',
        'body': 'The dependency guide requires optional dependencies, including platform binaries. Keep optional dependencies enabled for this checkout; recheck if the guide changes.',
        'paths': [path], 'session': 'deterministic-otel-validation'})
    cold = LocalBridge(root, config=bridge.config)
    recalled = cold.call('recall', {'query': 'optional build dependencies', 'session': 'fresh-transport-reader'})
    after = hashlib.sha256(git(root, 'diff', '--binary', binary=True)).hexdigest()
    result = {'ok': before == after and memory['memory']['id'] in [m['id'] for m in recalled['findings']],
              'mode': 'deterministic bridge/HTTP validation; no model calls', 'project_id': project, 'repo_id': repo,
              'head': git(root, 'rev-parse', 'HEAD'), 'patch_unchanged': before == after, 'patch_sha256': before,
              'memory_id': memory['memory']['id'], 'recall': recalled}
    (state / 'opentelemetry-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
