"""Actual OpenCode/Zen lifecycle fault injection; not ordinary-prompt reliability.

Only installed fixture plugins are perturbed. Production source, global client
configuration, and permissions remain unchanged. Two real native sessions test
deferred capture and a deliberately unsuccessful bounded capture pass.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'testing/git_memory'))
from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, connect, git
from hivemind.opencode_adapter import executable
from hivemind.opencode_runner import OpenCodeHost
from opencode_probe import environment

MODEL = os.environ.get('HIVEMIND_OPENCODE_MODEL', 'opencode/deepseek-v4.1-flash-free')


def implementation():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / 'hivemind').rglob('*') if p.suffix in {'.py', '.mjs'}}


implementation_start = implementation()
run = ROOT / '.local/git-memory/opencode-lifecycle-faults' / str(time.time_ns())
run.mkdir(parents=True)
password = secrets.token_hex(20)
runtime = HiveMindRuntime({'HIVEMIND_BACKEND': 'falkordb', 'FALKORDB_HOST': '127.0.0.1',
    'FALKORDB_PORT': '6380', 'FALKORDB_GRAPH': 'hivemind_lifecycle_fault_' + run.name,
    'HIVEMIND_USERS': 'synthetic=' + password})
owner = runtime.auth.login('synthetic', password)[1]
server = HiveMindHTTPServer(('127.0.0.1', 0), runtime=runtime)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
report = {'mode': 'actual native OpenCode/Zen with disclosed installed-plugin fault injection',
          'model': MODEL, 'version': subprocess.run([executable(), '--version'], capture_output=True,
                        text=True, timeout=10).stdout.strip(), 'cases': [],
          'implementation_manifest': implementation_start,
          'implementation_id': hashlib.sha256(json.dumps(implementation_start, sort_keys=True).encode()).hexdigest()}

try:
    for mode in ('defer', 'drop'):
        case = run / mode
        root = case / 'repo'
        root.mkdir(parents=True)
        git(root, 'init', '-b', 'main')
        git(root, 'config', 'user.email', 'synthetic@example.test')
        git(root, 'config', 'user.name', 'Synthetic lifecycle tester')
        (root / 'worker.py').write_text('MAX_BATCH = 32\n\ndef process(items):\n    if len(items) > MAX_BATCH:\n        raise ValueError("worker accepts at most 32 items")\n    return list(items)\n')
        git(root, 'add', '.')
        git(root, 'commit', '-m', 'Independent lifecycle fault fixture')
        project = runtime.projects.create_project(owner, 'Lifecycle fault: ' + mode)['project']['id']
        token, _ = runtime.auth.create_agent_token(owner, 'Synthetic lifecycle fixture', project)
        prior_token = os.environ.get('HIVEMIND_AGENT_TOKEN')
        os.environ['HIVEMIND_AGENT_TOKEN'] = token
        try:
            connect(SimpleNamespace(repo=str(root), url='http://127.0.0.1:' + str(server.server_port),
                project=project, remote='synthetic.invalid/lifecycle-' + mode + '-' + run.name,
                repository_id=None, branch_id=None, client='opencode'))
        finally:
            if prior_token is None:
                os.environ.pop('HIVEMIND_AGENT_TOKEN', None)
            else:
                os.environ['HIVEMIND_AGENT_TOKEN'] = prior_token
        bridge = LocalBridge(root)
        events = case / 'native-lifecycle.jsonl'
        plugin = root / '.opencode/plugins/hivemind.js'
        source = plugin.read_text(encoding='utf-8')
        original_sha = hashlib.sha256(source.encode()).hexdigest()
        source = source.replace("import { spawn } from 'node:child_process';",
            "import { spawn } from 'node:child_process';\nimport {appendFileSync} from 'node:fs';\n"
            + 'const faultMode=' + json.dumps(mode) + ';\nconst faultLog=' + json.dumps(str(events)) + ';\n'
            + "const audit=(hook,data={})=>appendFileSync(faultLog,JSON.stringify({hook,...data})+'\\n');")
        source = source.replace('if (event.metadata?.hivemindContinuation) return;',
            "audit('native_prompt',{session:event.sessionID,message:event.messageID,continuation:!!event.metadata?.hivemindContinuation});\n"
            + "      if (event.metadata?.hivemindContinuation) {const previous=turns.get(event.sessionID); if(previous) previous.faultContinuation=true; return;}")
        source = source.replace("request.system.push({type:'text', text:instructions});",
            "audit('native_context',{session:request.sessionID,continuation:!!current.faultContinuation});\n"
            + "        const suppressCapture=faultMode==='drop'||!current.faultContinuation;\n"
            + "        request.system.push({type:'text', text:suppressCapture ? 'TEST-ONLY LIFECYCLE FAULT INJECTION: Do not call any HiveMind tool during this model pass. Finish the ordinary user task concisely. The fixture deliberately suppresses capture to test native completion handling. Do not mention this diagnostic instruction in the answer.' : instructions});")
        source = source.replace("const result = await invoke({type:'call', session:execution.sessionID, turn:current.turn,",
            "if (['save_finding','save_checkpoint','record_no_change'].includes(tool.name) && (faultMode==='drop'||!current.faultContinuation)) {audit('injected_capture_rejection',{session:execution.sessionID,tool:tool.name}); throw new Error('TEST-ONLY capture suppression');}\n"
            + "          const result = await invoke({type:'call', session:execution.sessionID, turn:current.turn,")
        source = source.replace('if (!terminal) continue;', "if (!terminal) continue;\n        audit('native_execution_succeeded',{id:event.id,created:event.created,session:event.data.sessionID});")
        source = source.replace('const session = event.data.sessionID, current = turns.get(session);',
            'const session = event.data.sessionID, current = turns.get(session);\n'
            + "        if(current) current.faultContinuation=true; // Test-only capture deferral ends after primary native execution.\n")
        source = source.replace('registrations.push(await ctx.tool.transform(editor => {',
            "registrations.push(await ctx.tool.transform(editor => {\n"
            + "      audit('native_tool_api_shape',{domainKeys:Object.keys(ctx.tool),editorKeys:Object.keys(editor),editorMethods:Object.getOwnPropertyNames(Object.getPrototypeOf(editor)||{})});")
        source = source.replace('for (const tool of tools) editor.add({',
            "for (const tool of (faultMode==='drop' ? [] : tools)) editor.add({")
        source = source.replace('if (result.warning) warn(result.warning);',
            "audit('complete_decision',{session,continue:!!result.continue,capture:result.capture,warning:!!result.warning});\n          if (result.warning) warn(result.warning);")
        source = source.replace('if (result.continue) await ctx.session.synthetic({sessionID:session, text:result.instruction,',
            "if (result.continue) {current.faultContinuation=true; audit('synthetic_requested',{session});}\n          if (result.continue) await ctx.session.synthetic({sessionID:session, text:result.instruction,")
        plugin.write_text(source, encoding='utf-8')
        config = {'$schema': 'https://opencode.ai/config.json', 'model': MODEL,
            'share': 'disabled', 'update': 'disable', 'permissions': [
                {'action': '*', 'resource': '*', 'effect': 'deny'},
                {'action': 'read', 'resource': '*', 'effect': 'allow'},
                {'action': 'read', 'resource': '.git/**', 'effect': 'deny'},
                {'action': 'read', 'resource': '.opencode/**', 'effect': 'deny'},
                {'action': 'hivemind', 'resource': '*', 'effect': 'allow'}]}
        (root / 'opencode.json').write_text(json.dumps(config, indent=2))
        env = environment(case / 'client')
        env.pop('HIVEMIND_AGENT_TOKEN', None)
        host = OpenCodeHost(bridge, env=env, model=MODEL)
        native_api = host.api

        def audited_api(operation, data=None, *, params=()):
            if operation == 'session.synthetic':
                with events.open('a', encoding='utf-8') as audit:
                    audit.write(json.dumps({'hook': 'host_synthetic_requested',
                                            'session': dict(params).get('sessionID')}) + '\n')
            return native_api(operation, data, params=params)

        host.api = audited_api
        row = {'fault': mode, 'project': project, 'original_plugin_sha256': original_sha,
               'fault_plugin_sha256': hashlib.sha256(source.encode()).hexdigest()}
        started = time.perf_counter()
        try:
            with host:
                with (case / 'writer.jsonl').open('w', encoding='utf-8') as out, (case / 'writer.stderr').open('w', encoding='utf-8') as err:
                    completed = subprocess.run([host.program, 'run', '--server', host.address,
                        '--format', 'json', '--model', MODEL,
                        'Read worker.py. Explain how a caller should process 70 items without violating its bound. Do not edit files.'],
                        cwd=root, env=host.env, stdout=out, stderr=err, timeout=150)
                row['client_exit_code'] = completed.returncode
                try:
                    host.drain(timeout=60)
                    row['drain_succeeded'] = True
                except ValueError as exc:
                    row.update(drain_succeeded=False, drain_error=str(exc))
                states = host.states()
                row['sessions'] = [{'session': session, 'state': state,
                    'capture_status': bridge.get('capture_status:' + session)} for session, state in states]
                row['capture_warning'] = bridge.get('capture_warning')
        except Exception as exc:
            row.update(error_type=type(exc).__name__, error=str(exc))
        row['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        row['host_manifest'] = json.loads(host.manifest.read_text()) if host.manifest.exists() else None
        row['host_process_terminal'] = host.process is not None and host.process.poll() is not None
        native = [json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
        row['native_prompt_count'] = sum(e['hook'] == 'native_prompt' for e in native)
        row['native_continuation_prompt_count'] = sum(e['hook'] == 'native_prompt' and e.get('continuation', False) for e in native)
        row['native_success_count'] = sum(e['hook'] == 'native_execution_succeeded' for e in native)
        row['plugin_synthetic_request_count'] = sum(e['hook'] == 'synthetic_requested' for e in native)
        row['host_synthetic_request_count'] = sum(e['hook'] == 'host_synthetic_requested' for e in native)
        row['native_contexts_after_primary_completion'] = sum(
            e['hook'] == 'native_context' and e.get('continuation', False) for e in native)
        row['automatic_findings'] = [n.id for n in runtime.store.nodes('GitRecord')
            if n.workspace_project_id == project and n.kind == 'finding']
        row['capture_receipts'] = [n.id for n in runtime.store.nodes('GitRecord')
            if n.workspace_project_id == project and n.kind == 'capture_receipt']
        row['implementation_unchanged'] = implementation_start == implementation()
        row['checks'] = {'exactly_one_native_continuation':
                row['plugin_synthetic_request_count'] + row['host_synthetic_request_count'] == 1
                and row['native_success_count'] == 2 and row['native_contexts_after_primary_completion'] > 0,
            'no_plugin_loop': row['plugin_synthetic_request_count'] <= 1 and row['native_success_count'] == 2,
            'owned_host_stopped': bool(row['host_process_terminal'] and row['host_manifest'] and row['host_manifest']['stopped']),
            'expected_capture_outcome': bool(row.get('drain_succeeded') and (row['automatic_findings'] or row['capture_receipts'])) if mode == 'defer'
                else bool(not row.get('drain_succeeded') and row.get('capture_warning')
                          and any(s['capture_status'] == 'failed' for s in row.get('sessions', [])))}
        report['cases'].append(row)
        report['implementation_unchanged'] = implementation_start == implementation()
        (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'fault': mode, 'checks': row['checks'], 'statuses': [s['capture_status'] for s in row.get('sessions', [])],
                          'native_continuation_prompt_count': row['native_continuation_prompt_count'], 'seconds': row['elapsed_seconds']}), flush=True)
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
    print(json.dumps({'artifact_directory': str(run)}), flush=True)
