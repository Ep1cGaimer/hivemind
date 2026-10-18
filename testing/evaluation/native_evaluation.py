"""Actual OpenCode/Zen code-task evaluation, never a deterministic model replay.

Writer history is shared fairly across three fresh consumer conditions. The
independent fixture suite owns expected outcomes; its answers stay outside repos.
Initial runs are pilots until the whole predeclared randomized plan is executed.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import random
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'testing/git_memory'))
sys.path.insert(0, str(Path(__file__).parent / 'independent_fixtures'))
from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, connect, git
from hivemind.domain import record_to_dict
from hivemind.opencode_runner import OpenCodeHost
from opencode_probe import environment
import suite
from evidence_tools import source_snapshot

HERE = Path(__file__).parent
MODEL = os.environ.get('HIVEMIND_OPENCODE_MODEL', 'opencode/deepseek-v4.1-flash-free')
PROVIDER = MODEL.split('/', 1)[0] if '/' in MODEL else ''
CONDITIONS = ('source_only', 'source_linked_notes', 'hivemind')


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def manifest():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / 'hivemind').rglob('*') if p.suffix in {'.py', '.mjs'}}


def quietly(function, *args, **kwargs):
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def configure(repo, log, *, condition, notes_command=None):
    # Local-only adapter/config files never enter source commits or snapshots.
    with (repo / '.git/info/exclude').open('a', encoding='utf-8') as excluded:
        excluded.write('\n.opencode/\nopencode.json\n')
    permissions = [{'action': '*', 'resource': '*', 'effect': 'deny'}]
    for action in ('read', 'edit', 'fixture', 'notes'):
        permissions.append({'action': action, 'resource': '*', 'effect': 'allow'})
    if condition == 'hivemind':
        permissions.append({'action': 'hivemind', 'resource': '*', 'effect': 'allow'})
    for action in ('read', 'edit'):
        for resource in ('.git/**', '.opencode/**', 'opencode.json'):
            permissions.append({'action': action, 'resource': resource, 'effect': 'deny'})
    save(repo / 'opencode.json', {'$schema': 'https://opencode.ai/config.json', 'model': MODEL,
        'share': 'disabled', 'update': 'disable', 'permissions': permissions,
                     'policies': [{'action': 'provider.use', 'resource': '*', 'effect': 'deny'},
                      {'action': 'provider.use', 'resource': PROVIDER, 'effect': 'allow'}]})
    plugins = repo / '.opencode/plugins'
    plugins.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(HERE / 'native_tools.py'), '--repo', str(repo), '--log', str(log)]
    source = (HERE / 'native_tools.mjs').read_text(encoding='utf-8').replace('__EVALUATION_COMMAND__', json.dumps(command))
    (plugins / 'evaluation.js').write_text(source, encoding='utf-8')
    if condition != 'hivemind':
        if notes_command is None and condition == 'source_linked_notes':
            raise ValueError('The notes control must be installed before running this condition')
        if notes_command:
            source = (HERE / 'notes_plugin.mjs').read_text(encoding='utf-8').replace('__NOTES_COMMAND__', json.dumps(notes_command))
        else:
            source = "export default {id:'hivemind.evaluation-source-only',setup:async()=>{}};\n"
        # OpenCodeHost owns transport lifetime only. This neutral fixture plugin
        # does not inject HiveMind context or expose memory tools to controls.
        (plugins / 'hivemind.js').write_text(source, encoding='utf-8')


def run_model(repo, output, prompt, *, bridge=None):
    output.mkdir(parents=True, exist_ok=False)
    bridge = bridge or LocalBridge(repo, config={'url': 'fixture:control', 'project_id': 'control'})
    env = environment(output / 'client')
    env.pop('HIVEMIND_AGENT_TOKEN', None)
    started = time.perf_counter()
    result = {'prompt': prompt, 'model': MODEL, 'session_ids': [], 'status': 'failed', 'interventions': []}
    host = OpenCodeHost(bridge, env=env, model=MODEL)
    try:
        with host:
            with (output / 'native.jsonl').open('w', encoding='utf-8') as out, (output / 'native.stderr').open('w', encoding='utf-8') as err:
                process = subprocess.run([host.program, 'run', '--server', host.address,
                    '--format', 'json', '--model', MODEL, prompt], cwd=repo, env=host.env,
                    stdout=out, stderr=err, timeout=180)
            result['returncode'] = process.returncode
            events = [json.loads(line) for line in (output / 'native.jsonl').read_text(encoding='utf-8').splitlines() if line]
            result['session_ids'] = sorted({e['sessionID'] for e in events if 'sessionID' in e})
            result['status'] = 'passed' if process.returncode == 0 else 'failed'
            if bridge.config['url'] != 'fixture:control' and process.returncode == 0:
                try:
                    host.drain()
                except ValueError as error:
                    result['status'] = 'failed'
                    result['error'] = str(error)
                result['capture_status'] = {s: bridge.get('capture_status:' + s) for s in result['session_ids']}
                result['native_lifecycle'] = {s: bridge.get('opencode:' + s) for s in result['session_ids']}
            # Session.Info includes cumulative tokens/cost, including a capture
            # continuation that outlives the foreground CLI JSONL stream.
            result['native_session_info'] = []
            for session in result['session_ids']:
                result['native_session_info'].append(host.api('session.get', params=[('sessionID', session)]))
            result['foreground_tool_calls'] = sum(e.get('type') == 'tool_use' for e in events)
            result['foreground_step_usage'] = [e['part'] for e in events if e.get('type') == 'step_finish']
    except Exception as error:
        result['status'] = 'failed'
        result['error'] = str(error)
    finally:
        result['seconds'] = time.perf_counter() - started
        result['artifact_directory'] = str(output)
        if host.manifest.is_file():
            result['host'] = json.loads(host.manifest.read_text(encoding='utf-8'))
        save(output / 'result.json', result)
    return result


def inventory(runtime, project, repo):
    graph = runtime.git_memory.graph(project, repo)
    records, cursor = [], ''
    while True:
        page, complete = graph.list(cursor=cursor)
        records.extend(record_to_dict(n) for n in page)
        if complete:
            break
        cursor = page[-1].id
    links = []
    for kind in ('PARENT', 'PUBLISHES', 'BRANCH_MEMORY', 'SUPPORTED_BY', 'HAS_SOURCE',
                 'REVISES', 'RESUMES', 'ACCEPTS', 'OBSERVED', 'AT_COMMIT', 'TRANSFERRED_FROM'):
        links.extend({'from_id': a, 'to_id': b, 'edge_type': kind, 'properties': props}
                     for a, b, props in graph.links(kind))
    return {'records': records, 'links': links, 'inventory': {'complete': True, 'all_kinds': True,
            'filters': {'project_id': project, 'repo_id': repo}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=suite.CASES, required=True)
    parser.add_argument('--condition', choices=(*CONDITIONS, 'all'), default='hivemind')
    parser.add_argument('--seed', type=int, default=1729)
    parser.add_argument('--variant', choices=('default', 'main', 'before', 'after'), default='default')
    parser.add_argument('--output')
    args = parser.parse_args()
    output = Path(args.output).resolve() if args.output else ROOT / '.local/evaluation' / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    before = manifest()
    conditions = list(CONDITIONS) if args.condition == 'all' else [args.condition]
    random.Random(args.seed).shuffle(conditions)
    declaration = {'mode': 'pilot, not the complete randomized comparison', 'case': args.case,
        'condition': args.condition, 'model': MODEL, 'writer_wall_limit_seconds': 180,
        'consumer_order': conditions, 'randomization_seed': args.seed,
        'consumer_wall_limit_seconds': 180, 'capture_pass_limit_seconds': 60,
        'tools': 'Identical native read/edit plus isolated Python and read-only Git history.',
        'control_rules': 'Fresh source clones; full actual history for notes; no writer transcript; independent answers remain outside repo.',
        'product_manifest': before, 'expected_outcomes_sha256': hashlib.sha256((HERE / 'independent_fixtures/EXPECTED_OUTCOMES.json').read_bytes()).hexdigest(),
        'limitations': ['Pilot does not pass 72-run repetition/usefulness gate.',
                       'Checkpoint and conflicting-writer historical premises require additional setup and independent review.']}
    save(output / 'declaration.json', declaration)
    if args.case in {'unfinished_checkpoint', 'conflicting_interpretations'}:
        raise ValueError('This pilot does not yet implement the declared interrupted/two-writer history; use another case until that setup is complete')
    source = output / 'source'
    quietly(suite.prepare, SimpleNamespace(case=args.case, dest=str(source)))
    repo = source / 'repo'
    password = secrets.token_hex(16)
    runtime = HiveMindRuntime({**os.environ, 'HIVEMIND_BACKEND': 'falkordb', 'FALKORDB_HOST': '127.0.0.1',
        'FALKORDB_PORT': '6380', 'FALKORDB_GRAPH': 'hivemind_eval_' + output.name.replace('-', '_'),
        'HIVEMIND_USERS': 'evaluator=' + password})
    owner = runtime.auth.login('evaluator', password)[1]
    project = runtime.projects.create_project(owner, 'Independent ' + args.case)['project']['id']
    token, _ = runtime.auth.create_agent_token(owner, 'fixture', project)
    server = HiveMindHTTPServer(('127.0.0.1', 0), runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    prior = os.environ.get('HIVEMIND_AGENT_TOKEN')
    url = 'http://127.0.0.1:' + str(server.server_port)
    remote = 'fixture.invalid/evaluation-' + output.name
    def attach(target, repository_id=None, branch_id=None):
        os.environ['HIVEMIND_AGENT_TOKEN'] = token
        return connect(SimpleNamespace(repo=str(target), url=url, project=project, remote=remote,
                       repository_id=repository_id, branch_id=branch_id, client='opencode'))
    result = {'declaration': declaration, 'status': 'failed'}
    try:
        configure(repo, output / 'writer-tool-execution.jsonl', condition='hivemind')
        attached = attach(repo)
        bridge = LocalBridge(repo)
        original = git(repo, 'branch', '--show-current')
        if original != 'main':
            git(repo, 'switch', 'main')
            bridge.sync()
            git(repo, 'switch', original)
            bridge.sync()
        prompts = json.loads((source / 'prompts.json').read_text())
        if prompts['writer']:
            writer = run_model(repo, output / 'writer', prompts['writer'], bridge=bridge)
            result['writer'] = writer
            if writer['status'] != 'passed':
                raise ValueError('Writer failed; retained run cannot establish a historical premise')
            quietly(suite.advance, SimpleNamespace(run=str(source), variant=args.variant),
                    after_freeze=lambda path, tip: bridge.sync())
        context = bridge.sync()
        observation = bridge.observe()
        control_context = {**context, **{k: observation[k] for k in ('sources', 'dirty', 'history_complete', 'manifest_complete', 'ref')},
                           'workspace_project_id': project, 'repo_id': bridge.config['repo_id']}
        save(output / 'notes-context.json', control_context)
        save(output / 'full-inventory.json', inventory(runtime, project, bridge.config['repo_id']))
        save(output / 'writer-recall-after-transition.json', bridge.call('recall', {}))
        expected_snapshot = source_snapshot(repo, ('.opencode', 'opencode.json'))
        save(output / 'frozen-source-snapshot.json', expected_snapshot)
        result['consumers'] = []
        for condition in conditions:
            consumer = output / ('workspace-' + condition)
            quietly(suite.materialize, SimpleNamespace(run=str(source), dest=str(consumer)))
            target = consumer / 'repo'
            notes_command = ([sys.executable, str(HERE / 'notes_bridge.py'), '--repo', str(target),
                              '--inventory', str(output / 'full-inventory.json'), '--context', str(output / 'notes-context.json'),
                              '--log', str(output / 'notes-operations.jsonl')] if condition == 'source_linked_notes' else None)
            configure(target, output / (condition + '-tool-execution.jsonl'), condition=condition, notes_command=notes_command)
            starting_snapshot = source_snapshot(target, ('.opencode', 'opencode.json'))
            if starting_snapshot['source_snapshot_sha256'] != expected_snapshot['source_snapshot_sha256']:
                raise ValueError('Consumer source/history differs from the frozen shared writer snapshot')
            save(consumer / 'starting-source-snapshot.json', starting_snapshot)
            consumer_bridge = None
            if condition == 'hivemind':
                attach(target, repository_id=bridge.config['repo_id'], branch_id=context['branch_id'])
                consumer_bridge = LocalBridge(target)
            run = run_model(target, output / ('run-' + condition), prompts['consumer'], bridge=consumer_bridge)
            quietly(suite.check, SimpleNamespace(run=str(consumer)))
            outcome = json.loads((consumer / 'outcome.json').read_text())
            result['consumers'].append({'condition': condition, 'run': run, 'outcome': outcome,
                'source_snapshot_sha256': starting_snapshot['source_snapshot_sha256'],
                'consumer_diff': git(target, 'diff'),
                'consumer_untracked': git(target, 'ls-files', '--others', '--exclude-standard')})
            save(output / 'in-progress.json', result)
        result['status'] = ('passed' if all(c['run']['status'] == 'passed' and c['outcome']['status'] == 'passed'
                                          for c in result['consumers']) else 'failed')
    except Exception as error:
        result['error'] = str(error)
    finally:
        if prior is None:
            os.environ.pop('HIVEMIND_AGENT_TOKEN', None)
        else:
            os.environ['HIVEMIND_AGENT_TOKEN'] = prior
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        result['implementation_unchanged'] = before == manifest()
        result['artifact_directory'] = str(output)
        save(output / 'result.json', result)
        print(json.dumps({'status': result['status'], 'error': result.get('error'), 'artifact_directory': str(output)}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
