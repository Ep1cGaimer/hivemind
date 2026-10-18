"""Refresh the capable flat-notes control from the public synthetic checkout.

Evaluation-only: no product recall, database, model, or answer-key imports.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).parent / 'independent_fixtures'))
from notes_control import NotesIndex


def git(root, *args, data=None):
    result = subprocess.run(['git', *args], cwd=root, input=data, capture_output=True, timeout=10)
    if result.returncode:
        raise ValueError('Notes control could not observe the public checkout')
    return result.stdout


def observe(root, inventory, context):
    paths = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').decode('utf-8').split('\0')
    paths = sorted({p for p in paths if p and p != 'opencode.json' and not p.startswith(('.git/', '.opencode/')) and (root / p).is_file()})
    if len(paths) > 128 or any((root / p).stat().st_size > 1000000 for p in paths):
        raise ValueError('Synthetic notes-control source bound exceeded')
    payload = ''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in paths).encode()
    object_ids = git(root, 'hash-object', '--stdin-paths', data=payload).splitlines() if paths else []
    if len(paths) != len(object_ids):
        raise ValueError('Notes-control source observation incomplete')
    sources = {p: hashlib.sha256(b'git-blob:' + oid).hexdigest() for p, oid in zip(paths, object_ids)}
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    ref = git(root, 'symbolic-ref', '-q', 'HEAD').decode().strip()
    dirty = bool(git(root, 'status', '--porcelain'))
    result = dict(context, head=head, sources=sources, dirty=dirty, manifest_complete=True)
    if context.get('ref') and context['ref'] != ref:
        result['branch_id'] = None
        result['branch_warning'] = 'Different ref: recorded branch identity has not been verified for this checkout.'
    snapshots = [n for n in inventory['records'] if n['kind'] == 'snapshot' and n.get('head') == head
                 and n['data'].get('sources') == sources and bool(n['data'].get('dirty')) == dirty]
    if snapshots:
        result['snapshot_id'] = snapshots[0]['id']
    else:
        result['snapshot_id'] = 'notes-current:' + hashlib.sha256(json.dumps([head, sources, dirty], sort_keys=True).encode()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'inventory', 'context', 'log'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    event = json.load(sys.stdin)
    started = time.perf_counter()
    inventory = json.loads(Path(args.inventory).read_text(encoding='utf-8'))
    context = json.loads(Path(args.context).read_text(encoding='utf-8'))
    context = observe(Path(args.repo).resolve(), inventory, context)
    index = NotesIndex(inventory, context)
    action = event.get('action')
    if action == 'recall':
        result = index.retrieve(str(event.get('query', ''))[:1000])
    elif action == 'inspect':
        result = index.inspect(event['memory_id'])
    elif action == 'search':
        result = index.search(str(event.get('query', ''))[:1000])
    else:
        raise ValueError('Unknown notes-control action')
    with Path(args.log).open('a', encoding='utf-8') as log:
        log.write(json.dumps({'action': action, 'seconds': time.perf_counter() - started, 'context': context,
                              'result': result}, ensure_ascii=False) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
