"""Evaluator-private boundary probe for a real OpenCode2 interrupted writer.

This file never writes a memory, fabricates a tool result, or supplies its private
outcomes to the actor. The installed hook returns only a stop boolean. Use the
normal HiveMind host/capture lifecycle; failure to capture remains a failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import os

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'independent_fixtures'))
import checkpoint_v2 as fixture
from evidence_tools import source_snapshot

MODEL = os.environ.get('HIVEMIND_OPENCODE_MODEL', 'opencode/deepseek-v4.1-flash-free')


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declare(run):
    run = Path(run).resolve()
    state = json.loads((run / 'state.json').read_text(encoding='utf-8'))
    if state.get('fixture_version') != fixture.VERSION or state.get('phase') != 'writer':
        raise ValueError('Prepare a new versioned checkpoint writer first')
    path = run / 'checkpoint-predeclaration.json'
    if path.exists():
        raise ValueError('Never replace a writer predeclaration; retain every attempt')
    repo = run / 'repo'
    initial = source_snapshot(repo, fixture.RUNTIME_PATHS)
    if fixture.suite.git(repo, 'diff', '--name-only') or fixture.suite.git(repo, 'diff', '--cached', '--name-only'):
        raise ValueError('Predeclare before the writer changes source')
    value = {'fixture_version': fixture.VERSION, 'created_ns': time.time_ns(), 'rule': fixture.STOP_RULE,
             'model': MODEL, 'max_writer_attempts': 1, 'writer_wall_limit_seconds': 180,
             'capture_pass_limit_seconds': 60, 'capture_extra_pass_limit': 1,
             'repo': str(repo), 'initial_source': initial,
             'private_checker_sha256': digest(Path(fixture.__file__)),
             'boundary_probe_sha256': digest(Path(__file__)),
             'outcome_definitions_sha256': hashlib.sha256((fixture.PARSER_PROBE + fixture.FULL_PROBE).encode()).hexdigest(),
             'one_edit_completion': 'Retain as invalid checkpoint premise; do not truncate or retry',
             'semantic_review': 'Independent simulated reviewer must inspect the actual checkpoint body against frozen source; no schema/keyword claim establishes actionability.'}
    save(path, value)
    save(run / 'checkpoint-boundary-state.json', {'last_working_content_sha256': initial['working_content_sha256']})
    return value


def boundary(run, event):
    run = Path(run).resolve()
    declaration_path = run / 'checkpoint-predeclaration.json'
    declaration = json.loads(declaration_path.read_text(encoding='utf-8'))
    if digest(Path(fixture.__file__)) != declaration['private_checker_sha256'] or digest(Path(__file__)) != declaration['boundary_probe_sha256']:
        raise ValueError('Predeclared evaluator changed after writer launch')
    repo = run / 'repo'
    state = json.loads((run / 'state.json').read_text(encoding='utf-8'))
    previous_path = run / 'checkpoint-boundary-state.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    snapshot = source_snapshot(repo, fixture.RUNTIME_PATHS)
    if event.get('status') != 'completed' or not all(event.get(k) for k in ('sessionID', 'id', 'tool')):
        return {'stop': False}
    if (run / 'checkpoint-stop-selection.json').exists():
        return {'stop': False}
    changed = snapshot['working_content_sha256'] != previous['last_working_content_sha256']
    save(previous_path, {'last_working_content_sha256': snapshot['working_content_sha256']})
    if not changed:
        return {'stop': False}
    result = fixture.assess(repo, state)
    receipt = {'created_ns': time.time_ns(), 'predeclaration_sha256': digest(declaration_path),
               'actual_tool_boundary': event, 'assessment': result}
    with (run / 'checkpoint-boundaries.jsonl').open('a', encoding='utf-8') as log:
        log.write(json.dumps(receipt, ensure_ascii=False) + '\n')
    if result['eligible']:
        save(run / 'checkpoint-stop-selection.json', receipt)
        return {'stop': True}
    if result['writer_already_complete']:
        # A fully complete writer cannot subsequently become our partial premise.
        save(run / 'checkpoint-completed-writer.json', receipt)
    return {'stop': False}


def install(run):
    run = Path(run).resolve()
    if not (run / 'checkpoint-predeclaration.json').is_file():
        raise ValueError('Predeclare before installing a boundary hook')
    repo = run / 'repo'
    target = repo / '.opencode/plugins/checkpoint-boundary.js'
    target.parent.mkdir(parents=True, exist_ok=True)
    source = (HERE / 'checkpoint_probe.mjs').read_text(encoding='utf-8')
    source = source.replace('__BOUNDARY_COMMAND__', json.dumps([sys.executable, str(Path(__file__).resolve()), 'boundary', '--run', str(run)]))
    source = source.replace('__NATIVE_EVENT_LOG__', json.dumps(str(run / 'checkpoint-native-events.jsonl')))
    target.write_text(source, encoding='utf-8')
    return {'plugin': str(target), 'kind': 'evaluation-only native tool boundary observer', 'model_calls': 0}


def verify(run, inventory=None):
    """Verify machine anchors, leaving semantic actionability to actual review."""
    run = Path(run).resolve()
    selected_path = run / 'checkpoint-stop-selection.json'
    if not selected_path.is_file():
        return {'status': 'invalid_checkpoint_premise', 'reason': 'No qualifying actual completed-tool boundary',
                'completed_writer_retained': (run / 'checkpoint-completed-writer.json').is_file()}
    selected = json.loads(selected_path.read_text(encoding='utf-8'))
    event = selected['actual_tool_boundary']
    actual = [json.loads(line) for line in (run / 'checkpoint-native-events.jsonl').read_text(encoding='utf-8').splitlines() if line]
    native = [row['event'] for row in actual if row.get('kind') == 'native_event']
    successes = [e for e in native if e.get('type') == 'session.tool.success' and e.get('data', {}).get('id') == event['id'] and e.get('data', {}).get('sessionID') == event['sessionID']]
    interruptions = [e for e in native if e.get('type') == 'session.execution.interrupted' and e.get('data', {}).get('sessionID') == event['sessionID']]
    acknowledgments = [row for row in actual if row.get('kind') == 'interrupt_result' and row.get('sessionID') == event['sessionID']]
    synthetic = [e for e in native if e.get('type') == 'session.synthetic' and e.get('data', {}).get('sessionID') == event['sessionID'] and e.get('data', {}).get('metadata', {}).get('hivemindContinuation') is True]
    after = source_snapshot(run / 'repo', fixture.RUNTIME_PATHS)
    before_hash = selected['assessment']['source_snapshot']['working_content_sha256']
    checks = {'predeclaration_file_unchanged': digest(run / 'checkpoint-predeclaration.json') == selected['predeclaration_sha256'],
              'selected_boundary_after_predeclaration': selected['created_ns'] > json.loads((run / 'checkpoint-predeclaration.json').read_text())['created_ns'],
              'completed_native_tool_event': len(successes) == 1,
              'actual_native_interruption': bool(interruptions),
              'native_interrupt_acknowledged': any(row.get('result', {}).get('interrupted') is True for row in acknowledgments),
              'source_unchanged_across_interrupt_and_capture': before_hash == after['working_content_sha256'],
              'at_most_one_product_synthetic_pass': len(synthetic) <= 1}
    checkpoints = []
    if inventory:
        payload = json.loads(Path(inventory).read_text(encoding='utf-8'))
        checkpoints = [r for r in payload.get('records', []) if r.get('kind') == 'checkpoint' and r.get('session') == event['sessionID']]
        checks['separate_actual_checkpoint_record'] = bool(checkpoints)
    return {'status': 'mechanically_established_semantic_review_pending' if all(checks.values()) and inventory else 'unestablished',
            'checks': checks, 'session_id': event['sessionID'], 'actual_stop_event_part_id': event['id'],
            'source_digest_before_capture': before_hash, 'source_digest_after_capture': after['working_content_sha256'],
            'checkpoint_ids': [r['id'] for r in checkpoints],
            'semantic_review_questions': ['Does the actual checkpoint accurately state completed progress?',
                'Does it name remaining work and relevant unresolved questions without inventing discoveries?',
                'Are its next steps concrete and executable from this frozen source?',
                'Is this checkpoint separate from any durable findings, with actual session/source binding?'],
            'limitations': ['This private verifier cannot authenticate a caller-supplied inventory or establish semantic actionability.',
                            'Record actual host capture status/lifecycle, full inventory, writer costs, freeze commit and all three matching starting-source digests separately.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('declare', 'install', 'boundary', 'verify'))
    parser.add_argument('--run', required=True)
    parser.add_argument('--inventory')
    args = parser.parse_args()
    if args.command == 'boundary':
        value = boundary(args.run, json.load(sys.stdin))
    elif args.command == 'verify':
        value = verify(args.run, args.inventory)
        save(Path(args.run) / 'checkpoint-machine-evidence.json', value)
    else:
        value = {'declare': declare, 'install': install}[args.command](args.run)
    print(json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
