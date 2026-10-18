"""Declared repeated smoke workload, not independent usefulness use cases.

Runs independent projects and fresh writer/consumer processes on the same Zen
model. Keeps every run, failure and latency; never retries a failed cycle away.
"""
import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.cycles <= 100:
        parser.error('Choose 1–100 cycles')
    root = Path(__file__).resolve().parents[2]
    output = root / '.local/git-memory/reliability' / str(time.time_ns())
    output.mkdir(parents=True)
    def manifest():
        files = list((root / 'hivemind').rglob('*.py')) + list((root / 'hivemind').rglob('*.mjs'))
        files += [root / 'testing/git_memory' / name for name in ('opencode_workflow.py', 'opencode_probe.py', 'worker_plan.py')]
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    frozen_manifest = manifest()
    declaration = {'cycles': args.cycles, 'model': os.environ.get('HIVEMIND_OPENCODE_MODEL', 'opencode/deepseek-v4.1-flash-free'),
        'workload': 'Repeated bounded-worker review and fresh planning handoff; one underlying use case.',
        'expected': 'Each independent writer automatically saves source-linked learning; a fresh consumer receives it and plans correct batching.',
        'success_rule': 'Both clients exit successfully, distinct sessions, automatic writer finding, automatic consumer delivery, exact JSON batching plan, capture lifecycle completed, owned host stopped, unchanged declared implementation.',
        'source_manifest': frozen_manifest,
        'target': 'At least 19/20 successful cycles; every failure retained without replacement.'}
    (output / 'declaration.json').write_text(json.dumps(declaration, indent=2))
    cycles = []
    for index in range(args.cycles):
        start = time.perf_counter()
        returncode = None
        try:
            with (output / f'{index+1:02}.stdout').open('w', encoding='utf-8') as out, (output / f'{index+1:02}.stderr').open('w', encoding='utf-8') as err:
                process = subprocess.Popen([sys.executable, str(root / 'testing/git_memory/opencode_workflow.py')],
                    cwd=root, stdout=out, stderr=err, start_new_session=os.name != 'nt',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                try:
                    returncode = process.wait(timeout=500)
                except subprocess.TimeoutExpired:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
                    else:
                        os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=10)
                    raise
        except subprocess.TimeoutExpired:
            # Retain a timed-out cycle; do not silently replace it with another.
            pass
        try:
            result = json.loads((output / f'{index+1:02}.stdout').read_text(encoding='utf-8'))
        except ValueError:
            result = {'error': 'Workflow did not return JSON; inspect retained stdout/stderr'}
        required = ['ordinary_writer_prompt', 'fresh_sessions', 'both_clients_succeeded', 'automatic_capture',
                    'automatic_recall_before_model', 'consumer_preserves_bound']
        checks = result.get('checks', {})
        host_path = Path(result.get('artifact_directory', output)) / 'host.json'
        stopped = host_path.is_file() and json.loads(host_path.read_text()).get('stopped') is True
        stable = frozen_manifest == manifest() and result.get('implementation_unchanged') is True
        lifecycle = bool(result.get('runs')) and all(r.get('capture_status') in {'saved', 'no_change', 'queued'}
            and not r.get('capture_error') for r in result.get('runs', []))
        passed = returncode == 0 and all(checks.get(k, False) for k in required) and stopped and stable and lifecycle
        result['batch_checks'] = {'owned_host_stopped': stopped, 'frozen_implementation': stable, 'completed_capture_lifecycle': lifecycle}
        cycle = {'index': index+1, 'passed': passed, 'seconds': time.perf_counter()-start, 'result': result}
        cycles.append(cycle)
        summary = {'declaration': declaration, 'completed': len(cycles), 'passed': sum(c['passed'] for c in cycles),
                   'cycles': cycles, 'artifact_directory': str(output)}
        (output / 'result.json').write_text(json.dumps(summary, indent=2))
        print(json.dumps({'completed': len(cycles), 'passed': summary['passed'], 'cycle_passed': passed,
                          'artifact_directory': str(output)}), flush=True)
        if frozen_manifest != manifest():
            print('Declared implementation changed. Batch is incomplete; remaining runs were not executed.', file=sys.stderr)
            return 2
    return 0 if sum(c['passed'] for c in cycles) >= (19 if args.cycles == 20 else args.cycles) else 1


if __name__ == '__main__':
    raise SystemExit(main())
