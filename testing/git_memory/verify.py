"""Retain reproducible functional checks. Does not close model/UI/usefulness gates."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def manifest():
    files = list((ROOT / 'hivemind').rglob('*.py')) + list((ROOT / 'hivemind').rglob('*.mjs'))
    files += list((ROOT / 'web').glob('*')) + list((ROOT / 'tests').glob('*.py'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Run live-only tests in a NEW graph on the configured FalkorDB')
    args=parser.parse_args()
    output=ROOT / '.local/verification' / str(time.time_ns())
    output.mkdir(parents=True)
    before=manifest()
    env=dict(os.environ, PYTHONUTF8='1')
    env.pop('HIVEMIND_BACKEND',None)
    env.pop('HIVEMIND_LIVE_TESTS',None)
    graph=None
    if args.live:
        graph='hivemind_verification_' + output.name
        env.update(HIVEMIND_LIVE_TESTS='1', FALKORDB_GRAPH=graph)
        if not env.get('FALKORDB_HOST') or not env.get('FALKORDB_PORT'):
            parser.error('--live requires explicit FALKORDB_HOST and FALKORDB_PORT')
        checks=[('live', [sys.executable,'-m','unittest','discover','-s','tests','-p','test*live.py','-v'])]
    else:
        checks=[('offline', [sys.executable,'-m','unittest','discover','-s','tests','-v']),
                ('independent-fixtures',[sys.executable,'-m','unittest','discover','-s','testing/evaluation/independent_fixtures','-v']),
                ('python', [sys.executable,'-m','compileall','-q','hivemind','testing']),
                ('web', ['node','--check','web/app.js']),
                ('plugin', ['node','--check','hivemind/opencode_plugin.mjs']),
                ('fixture-plugin', ['node','--check','testing/evaluation/native_tools.mjs']),
                ('compose', ['docker','compose','config','--quiet']),
                ('whitespace', ['git','diff','--check'])]
    results=[]
    for name, command in checks:
        started=time.perf_counter()
        log=output / (name+'.log')
        with log.open('w',encoding='utf-8') as stream:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
        entry={'name':name,'command':command,'returncode':result.returncode,'seconds':time.perf_counter()-started,'log':str(log)}
        results.append(entry)
        report={'mode':'deterministic functional checks, not model/UI proof','graph':graph,
                'source_manifest':before,'implementation_unchanged':before==manifest(), 'checks':results,
                'artifact_directory':str(output)}
        (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(entry),flush=True)
    return 0 if all(r['returncode']==0 for r in results) and before==manifest() else 1


if __name__=='__main__':
    raise SystemExit(main())
