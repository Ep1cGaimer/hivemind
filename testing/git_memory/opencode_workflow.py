"""Real OpenCode 2/Zen workflow on an isolated live FalkorDB project.

Never substitutes deterministic writes for automatic capture. Failed model runs
remain failed artifacts. No global OpenCode configuration or credentials change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, connect, git
from hivemind.opencode_adapter import executable
from hivemind.opencode_runner import OpenCodeHost
from opencode_probe import environment
from worker_plan import check as check_worker_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Load the real plugin without making a model request')
    parser.add_argument('--model', default=os.environ.get('HIVEMIND_OPENCODE_MODEL', 'opencode/deepseek-v4.1-flash-free'))
    parser.add_argument('--standalone', action='store_true', help='Exercise a short-lived client host (capture shutdown regression)')
    args = parser.parse_args()
    def implementation():
        files = [p for p in (ROOT / 'hivemind').rglob('*') if p.suffix in {'.py', '.mjs'}]
        return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    source_manifest = implementation()
    if '/' not in args.model or not all(args.model.split('/', 1)):
        parser.error('The model must be selected as provider/model')
    program = executable()
    if not program:
        parser.error('Install OpenCode 2 before running the workflow')
    run = ROOT / '.local/git-memory/opencode-runs' / str(time.time_ns())
    root = run / 'repo'
    root.mkdir(parents=True)
    git(root, 'init', '-b', 'main')
    git(root, 'config', 'user.email', 'native-fixture@example.test')
    git(root, 'config', 'user.name', 'HiveMind native fixture')
    (root / 'worker.py').write_text('MAX_BATCH = 32\n\ndef process(items):\n    if len(items) > MAX_BATCH:\n        raise ValueError("one worker accepts at most 32 items")\n    return list(items)\n')
    (root / 'test_worker.py').write_text('from worker import process\nassert len(process(range(32))) == 32\ntry:\n    process(range(33))\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError("worker bound missing")\n')
    git(root, 'add', '.')
    git(root, 'commit', '-m', 'Independent bounded-worker fixture')
    password = secrets.token_hex(16)
    runtime = HiveMindRuntime({**os.environ, 'HIVEMIND_BACKEND': 'falkordb', 'FALKORDB_HOST': '127.0.0.1',
        'FALKORDB_PORT': '6380', 'FALKORDB_GRAPH': 'hivemind_opencode_acceptance', 'HIVEMIND_USERS': 'native=' + password})
    owner = runtime.auth.login('native', password)[1]
    project = runtime.projects.create_project(owner, 'OpenCode acceptance ' + run.name)['project']['id']
    token, _ = runtime.auth.create_agent_token(owner, 'native fixture', project)
    server = HiveMindHTTPServer(('127.0.0.1', 0), runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    prior = os.environ.get('HIVEMIND_AGENT_TOKEN')
    host = None
    try:
        os.environ['HIVEMIND_AGENT_TOKEN'] = token
        connection = connect(SimpleNamespace(repo=str(root), url='http://127.0.0.1:' + str(server.server_port),
            project=project, remote='fixture.invalid/opencode-' + run.name, repository_id=None, branch_id=None, client='opencode'))
        env = environment(run / 'client')
        # The bridge uses the private worktree token. Do not copy it to model env.
        env.pop('HIVEMIND_AGENT_TOKEN', None)
        config = {'$schema': 'https://opencode.ai/config.json', 'model': args.model,
                  'share': 'disabled', 'update': 'disable',
                   'policies': [{'action': 'provider.use', 'resource': '*', 'effect': 'deny'},
                                {'action': 'provider.use', 'resource': args.model.split('/', 1)[0], 'effect': 'allow'}],
                  'permissions': [
                      {'action': '*', 'resource': '*', 'effect': 'deny'},
                      {'action': 'read', 'resource': '*', 'effect': 'allow'},
                      {'action': 'read', 'resource': '.git/**', 'effect': 'deny'},
                      {'action': 'read', 'resource': '.opencode/**', 'effect': 'deny'},
                      {'action': 'hivemind', 'resource': '*', 'effect': 'allow'},
                  ]}
        (root / 'opencode.json').write_text(json.dumps(config, indent=2))
        server_args = ['--standalone']
        if not args.standalone and not args.probe:
            host = OpenCodeHost(LocalBridge(root), env=env, model=args.model)
            host.__enter__()
            env = host.env
            server_args = ['--server', host.address]
        runs = []
        prompts = [('writer', 'Review worker.py for batch-size edge cases. Explain the important constraint and how a caller should handle a list of 70 items. Do not edit files.'),
                   ('consumer', 'Plan a caller that sends 70 items through this worker. Return a JSON plan with item_count, batch_sizes, preserves_order, and source (cite the relevant source or team finding). Do not edit files.')]
        if args.probe:
            prompts = [('plugin-load', None)]
        for name, prompt in prompts:
            command = ([program, 'api', 'session.create', '--standalone', '--data', '{}'] if prompt is None else
                       [program, 'run', *server_args, '--format', 'json', '--model', args.model, prompt])
            start = time.perf_counter()
            try:
                with (run / (name + '.jsonl')).open('w', encoding='utf-8') as out, (run / (name + '.stderr')).open('w', encoding='utf-8') as err:
                    completed = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=err, timeout=180)
                runs.append({'role': name, 'exit_code': completed.returncode, 'seconds': time.perf_counter() - start})
                events = [json.loads(line) for line in (run / (name + '.jsonl')).read_text(encoding='utf-8').splitlines() if line]
                sessions = sorted({e['sessionID'] for e in events if 'sessionID' in e})
                runs[-1]['session_ids'] = sessions
                if completed.returncode == 0 and prompt is not None and sessions:
                    local = LocalBridge(root)
                    if host is not None:
                        try:
                            host.drain(timeout=60)
                        except ValueError as error:
                            runs[-1]['capture_error'] = str(error)
                    runs[-1]['capture_status'] = local.get('capture_status:' + sessions[0], 'pending')
            except subprocess.TimeoutExpired:
                runs.append({'role': name, 'timeout': True, 'seconds': time.perf_counter() - start})
            if runs[-1].get('exit_code') != 0 or runs[-1].get('capture_error'):
                break
        bridge = LocalBridge(root)
        recalled = bridge.call('recall', {})
        consumer_path = run / 'consumer.jsonl'
        consumer_events = [json.loads(line) for line in consumer_path.read_text(encoding='utf-8').splitlines() if line] if consumer_path.exists() else []
        answer = '\n'.join(e.get('part', {}).get('text', '') for e in consumer_events if e['type'] == 'text')
        writer_sessions = runs[0].get('session_ids', []) if runs else []
        consumer_sessions = runs[1].get('session_ids', []) if len(runs) > 1 else []
        checks = {
            'ordinary_writer_prompt': not args.probe and all('memory' not in p.lower() for _, p in prompts if p),
            'fresh_sessions': bool(writer_sessions and consumer_sessions and not set(writer_sessions) & set(consumer_sessions)),
            'both_clients_succeeded': len(runs) == 2 and all(r.get('exit_code') == 0 for r in runs),
            'automatic_capture': any(m.get('session') in writer_sessions for m in recalled.get('findings', [])),
            'automatic_recall_before_model': any(m['id'] in bridge.get('opencode:' + consumer_sessions[0], {}).get('delivered_memory_ids', [])
                for m in recalled.get('findings', [])) if consumer_sessions else False,
            'consumer_cites_saved_revision': any(m['id'] in answer for m in recalled.get('findings', [])),
            'consumer_preserves_bound': check_worker_plan(answer),
        }
        result = {'mode': 'real installed-client probe' if args.probe else 'real OpenCode/Zen sessions',
                  'project_id': project, 'repo_id': connection['repo_id'] if 'repo_id' in connection else bridge.config['repo_id'],
                  'adapter': connection['adapters'], 'model': args.model, 'runs': runs,
                  'automatic_findings': len(recalled.get('findings', [])),
                  'memory_ids': [m['id'] for m in recalled.get('findings', [])],
                  'checks': checks, 'handoff_proven': all(checks.values()), 'artifact_directory': str(run),
                  'implementation_manifest': source_manifest,
                  'implementation_id': hashlib.sha256(json.dumps(source_manifest, sort_keys=True).encode()).hexdigest(),
                  'implementation_unchanged': source_manifest == implementation(),
                  'installed_plugin_sha256': hashlib.sha256((root / '.opencode/plugins/hivemind.js').read_bytes()).hexdigest()}
        # Retrieval alone does not prove the consumer used a finding correctly.
        (run / 'result.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        try:
            if host is not None:
                host.__exit__(None, None, None)
                (run / 'host.json').write_text(host.manifest.read_text(encoding='utf-8'))
        finally:
            if prior is None:
                os.environ.pop('HIVEMIND_AGENT_TOKEN', None)
            else:
                os.environ['HIVEMIND_AGENT_TOKEN'] = prior
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    main()
