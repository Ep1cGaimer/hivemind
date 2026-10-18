"""OpenCode 2 plugin installation and trusted lifecycle bridge.

The plugin uses the current assistant model. This module never invokes a model,
stores a transcript, changes client permissions, or accepts model Git context.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from .bridge import TOOL_ACTIONS, tool_definitions
from .git_memory import SECRET, digest


PASS_PREFIX = 'HiveMind automatic memory pass'
VALIDATION_LABEL = '\n\nValidation statements are agent-reported; no independent execution receipt is attached.'


def executable():
    program = os.environ.get('HIVEMIND_OPENCODE_BIN') or shutil.which('opencode.exe') or shutil.which('opencode.cmd') or shutil.which('opencode')
    if program and Path(program).suffix.lower() in {'.cmd', '.bat', '.ps1'}:
        # Invoke the installed native binary directly. Terminating an npm cmd
        # shim on Windows leaves its server child alive.
        native = Path(program).parent / 'node_modules' / '@opencode' / 'cli' / 'bin' / 'opencode.exe'
        if native.is_file():
            program = str(native)
    return program


def install(bridge, command):
    program = executable()
    if not program:
        raise ValueError('OpenCode is missing. Install OpenCode 2, then repeat connect --client opencode.')
    version = subprocess.run([program, '--version'], capture_output=True, text=True, timeout=10).stdout.strip()
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
    if not match or int(match[1]) != 2:
        raise ValueError('This adapter requires OpenCode 2 (verified API: 2.0.29/2.0.32); found ' + version)
    definitions = []
    for tool in tool_definitions():
        if tool['name'] in {'list_memories', 'create_memory', 'edit_memory'}:
            continue
        schema = json.loads(json.dumps(tool['inputSchema']))
        for field in ('session', 'event_id'):
            schema['properties'].pop(field, None)
        definitions.append({**tool, 'inputSchema': schema})
    path = bridge.root / '.opencode' / 'plugins' / 'hivemind.js'
    original = path.read_text(encoding='utf-8') if path.exists() else ''
    if original and '// HiveMind managed adapter' not in original:
        raise ValueError('Existing .opencode/plugins/hivemind.js is not managed by HiveMind; rename it before connecting.')
    source = Path(__file__).with_name('opencode_plugin.mjs').read_text(encoding='utf-8')
    source = source.replace('__HIVEMIND_COMMAND__', json.dumps(command + ['opencode-event', '--repo', str(bridge.root)]))
    source = source.replace('__HIVEMIND_TOOLS__', json.dumps(definitions))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding='utf-8')
    return [{'client': 'opencode', 'version': version, 'plugin': '.opencode/plugins/hivemind.js',
             'transport': 'native session-bound tools through the shared Git/HTTP bridge',
             'permissions': 'Unchanged. Review project plugin and tool permissions in OpenCode.'}]


def handle(bridge, event):
    session, turn = event.get('session'), event.get('turn')
    if not isinstance(session, str) or not 1 <= len(session) <= 150 or not isinstance(turn, str) or not 1 <= len(turn) <= 150:
        raise ValueError('OpenCode must supply its actual session and prompt message IDs')
    bridge.session = session
    key = 'opencode:' + session
    state = bridge.get(key, {})
    name = event.get('type')
    if name == 'prompt':
        if state.get('turn') != turn:
            state = {'turn': turn, 'host_id': event.get('host_id'), 'continuation_requested': False}
            bridge.set(key, state)
            bridge.set('capture:' + session, [])
            bridge.set('capture_status:' + session, 'pending')
        return {'ok': True}
    if state.get('turn') != turn:
        if name == 'call':
            raise ValueError('This tool call belongs to an earlier prompt; submit it in the current turn')
        return {'ok': True, 'ignored': 'earlier_turn'}
    if name == 'context':
        query = str(event.get('query', ''))[:1000]
        if SECRET.search(query):
            query = ''
        result = bridge.call('recall', {'query': query})
        if state.get('continuation_requested'):
            state['capture_pass_started'] = True
            state.setdefault('capture_pass_started_at', time.time() * 1000)
        changed = bool(state.get('loaded') and state['loaded'] != result.get('context_id'))
        state['loaded'] = result.get('context_id')
        state['delivered_memory_ids'] = [m['id'] for group in ('findings', 'checkpoints') for m in result.get(group, [])]
        bridge.set(key, state)
        return {'ok': True, 'context_changed': changed, 'recall': result,
                'capture': bridge.get('capture_status:' + session, 'pending')}
    if name == 'call':
        tool, args = event.get('tool'), event.get('arguments', {})
        capture = TOOL_ACTIONS.get(tool) in {'finding', 'checkpoint', 'no-change'}
        try:
            definition = next((d for d in tool_definitions() if d['name'] == tool), None)
            if not definition or not isinstance(args, dict):
                raise ValueError('Unknown HiveMind tool')
            allowed = set(definition['inputSchema']['properties']) - {'session', 'event_id'}
            if set(args) - allowed or any(p not in args for p in definition['inputSchema']['required']):
                raise ValueError('Unsupported or missing arguments; session and Git context are supplied by OpenCode')
            args = dict(args)
            if TOOL_ACTIONS[tool] in {'finding', 'checkpoint'}:
                args['body'] = str(args.get('body', '')) + VALIDATION_LABEL
            args['event_id'] = digest([session, turn, event.get('call_id'), tool])
            result = bridge.call(TOOL_ACTIONS[tool], args)
        except Exception:
            if capture:
                # Keep failed attempts independently of successful/no-change
                # receipts. Never persist rejected payloads or exception text.
                failure = {'turn': turn, 'tool': tool, 'call_id': event.get('call_id'),
                           'message': 'Capture failed; inspect the native tool result and retry in a new turn.'}
                bridge.set('capture_failure:' + session + ':' + digest([turn, event.get('call_id')]), failure)
                bridge.set('capture_status:' + session, 'failed')
                bridge.set('capture_warning', failure['message'])
                state = bridge.get(key, {})
                if state.get('turn') == turn:
                    state['capture_failed'] = True
                    bridge.set(key, state)
            raise
        if capture and bridge.get(key, {}).get('capture_failed'):
            # A no-change declaration cannot repair a failed write. Retain the
            # successfully persisted result while exposing the incomplete turn.
            bridge.set('capture_status:' + session, 'failed')
        return result
    if name == 'tool':
        # Bounded native receipts contain no commands, output, prompts or paths.
        receipt = {'id': str(event.get('call_id', ''))[:150], 'tool': str(event.get('tool', ''))[:100],
                   'status': str(event.get('status', 'unknown'))[:20]}
        with bridge.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM state WHERE key=?', (key + ':tools',)).fetchone()
            receipts = json.loads(row[0]) if row else []
            if receipt not in receipts:
                db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key + ':tools', json.dumps((receipts + [receipt])[-20:])))
        return {'ok': True}
    if name == 'complete':
        # Claim continuation atomically across repeated idle/status deliveries.
        with bridge.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
            state = json.loads(row[0]) if row else {}
            if state.get('turn') != turn:
                return {'ok': True, 'ignored': 'earlier_turn'}
            if not event.get('check_only'):
                state['completion_observed'] = True
                created = event.get('event_created')
                # A delayed first terminal receipt must not close the extra
                # pass. Native events carry their creation time from this same
                # local host, independently of bridge delivery latency.
                after_pass_start = (created >= state.get('capture_pass_started_at', float('inf'))
                                    if isinstance(created, (int, float)) else
                                    event.get('event_id') != state.get('continuation_trigger_event'))
                if state.get('capture_pass_started') and after_pass_start:
                    state['capture_pass_finished'] = True
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(state)))
            if state.get('capture_failed') or bridge.get('capture_status:' + session) == 'failed':
                return {'ok': True, 'capture': 'failed', 'warning': bridge.get('capture_warning')}
            if bridge.get('capture:' + session, []):
                db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_warning', 'null'))
                return {'ok': True, 'capture': bridge.get('capture_status:' + session)}
            if state.get('continuation_requested'):
                if event.get('check_only') or not state.get('capture_pass_finished'):
                    return {'ok': True, 'waiting': True, 'capture': 'pending'}
                warning = 'HiveMind capture did not finish. Inspect bridge status and retry the failed save; no further automatic pass will run.'
                db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_warning', json.dumps(warning)))
                db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_status:' + session, json.dumps('failed')))
                return {'ok': True, 'capture': 'failed', 'warning': warning}
            state['continuation_requested'] = True
            state['continuation_trigger_event'] = event.get('event_id')
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps(state)))
        interrupted = event.get('terminal_type') == 'session.execution.interrupted'
        instruction = (PASS_PREFIX + ': do not edit, create, delete, or execute project files during this pass. '
            + ('The task was interrupted after a source edit. Save exactly one separate resumable checkpoint now with the completed progress, unresolved questions, and concrete next steps; do not save a durable finding unless it was already independently completed before interruption. '
               if interrupted else
               'Review the current turn and use only the HiveMind tools to save useful source-linked learning and a separate checkpoint if work remains. ')
            + 'Use the HiveMind tools. If nothing useful changed, call hivemind_record_no_change. Do not repeat work or request another pass.')
        return {'ok': True, 'continue': True, 'instruction': instruction}
    raise ValueError('Unsupported OpenCode lifecycle event')
