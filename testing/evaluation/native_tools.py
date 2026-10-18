"""Evaluation-only isolated execution. No product code or model is used here."""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import secrets
import subprocess
import sys
import time


def safe_path(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Use a repository-relative path with forward slashes')
    parts = PurePosixPath(value)
    if parts.is_absolute() or any(p in {'.git', '.opencode', '..'} for p in parts.parts) or ':' in value:
        raise ValueError('Path is outside the public fixture source')
    return value


def git(root, *args):
    result = subprocess.run(['git', '--no-pager', *args], cwd=root, capture_output=True,
                            encoding='utf-8', errors='replace', timeout=10)
    if result.returncode:
        raise ValueError('Requested Git source is unavailable')
    return result.stdout.strip()


def execute(root, event, image='python:3.12-slim'):
    args = event.get('args', {})
    if event.get('tool') == 'fixture_history':
        if set(args) - {'commit', 'path'}:
            raise ValueError('Unknown history arguments')
        commit = args.get('commit')
        if commit is not None:
            if not re.fullmatch(r'[0-9a-f]{40,64}', commit):
                raise ValueError('Select a full commit hash from the history listing')
            if args.get('path'):
                return {'commit': commit, 'path': safe_path(args['path']),
                        'text': git(root, 'show', commit + ':' + safe_path(args['path']))}
            return {'commit': commit, 'files': git(root, 'ls-tree', '-r', '--name-only', commit)}
        return {'head': git(root, 'rev-parse', 'HEAD'), 'branch': git(root, 'branch', '--show-current'),
                'refs': git(root, 'show-ref'), 'status': git(root, 'status', '--short'),
                'history': git(root, 'log', '--all', '--format=%H %P %s', '-64')}
    if event.get('tool') != 'fixture_python' or set(args) - {'code', 'file', 'args'}:
        raise ValueError('Unknown fixture operation')
    if bool(args.get('code')) == bool(args.get('file')):
        raise ValueError('Provide either code or a relative Python file')
    tail = args.get('args', [])
    if not isinstance(tail, list) or len(tail) > 20 or any(not isinstance(a, str) for a in tail):
        raise ValueError('Use at most 20 string script arguments')
    if len(args.get('code', '')) > 32000:
        raise ValueError('Python snippet is too large')
    # Native read/edit permissions separately exclude these paths. The container
    # overlays prevent Python from reading tokens or changing client permissions.
    container = 'hivemind-eval-' + secrets.token_hex(12)
    command = ['docker', 'run', '--name', container, '--rm', '--network', 'none', '--read-only',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--pids-limit', '64', '--memory', '256m', '--cpus', '1',
               '--mount', 'type=bind,source=' + str(root) + ',target=/work',
               '--tmpfs', '/work/.git:rw,noexec,nosuid,size=1m',
               '--tmpfs', '/work/.opencode:rw,noexec,nosuid,size=1m',
               '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m',
               '--mount', 'type=bind,source=' + str(root / 'opencode.json') + ',target=/work/opencode.json,readonly',
               '--workdir', '/work', image, 'python', '-B']
    command += ['-c', args['code']] if args.get('code') else [safe_path(args['file'])]
    command += tail
    start = time.perf_counter()
    try:
        result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace', timeout=30)
        return {'exit_code': result.returncode, 'stdout': result.stdout[-16000:], 'stderr': result.stderr[-8000:],
                'seconds': time.perf_counter() - start, 'runtime': image, 'network': 'none'}
    except subprocess.TimeoutExpired:
        raise ValueError('Isolated Python execution exceeded 30 seconds')
    finally:
        # A killed Docker client can leave its container running. This exact
        # random name belongs only to this invocation; never enumerate/remove
        # any other container or pre-existing service.
        subprocess.run(['docker', 'rm', '--force', container], capture_output=True, timeout=10)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--log', required=True)
    parser.add_argument('--image', default='python:3.12-slim')
    args=parser.parse_args()
    event=json.load(sys.stdin)
    start=time.perf_counter()
    try:
        result=execute(Path(args.repo).resolve(), event, args.image)
    except Exception as error:
        result={'error':str(error)}
    with Path(args.log).open('a',encoding='utf-8') as log:
        log.write(json.dumps({'event':event,'result':result,'seconds':time.perf_counter()-start})+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
