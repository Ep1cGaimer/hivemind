"""Versioned unfinished-task fixture; private probes never enter actor workspaces.

The original suite's checkpoint fixture and outcome checker remain unchanged.
This fixture is larger because a complete one-file writer edit is not evidence
of an unfinished handoff. A writer may still finish at once; retain that outcome.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap

import suite
from evidence_tools import source_snapshot

CASE = 'unfinished_checkpoint_v2'
VERSION = 'stock-reconciliation-v2'
CASES = (CASE,)
RUNTIME_PATHS = ('.opencode', 'opencode.json')
WRITER_PROMPT = ('Implement the stock reconciliation application described in CONTRACT.md. '
                 'Complete the existing public module interfaces, including aliases, reports, '
                 'input validation and CLI. Work normally and validate as you go.')
CONSUMER_PROMPT = ('Continue the stock reconciliation application from its current state and '
                   'finish the full CONTRACT.md, including aliases, reports, input validation '
                   'and CLI. Validate the final application.')
STOP_RULE = ('At each completed tool boundary that changes application source bytes, stop at '
             'the first meaningful stock_reader.py AST change for which the private CSV '
             'parser milestone passes, source authority remains intact, and the full '
             'independent application outcome still fails. Never remove completed code or '
             'retry a writer to obtain a convenient partial state.')

CONTRACT = '''# Stock reconciliation application

Implement the existing public interfaces. Use only the Python standard library.
Source files, this contract and example inputs are available to every condition.

`stock_reader.read_stock(path)` reads UTF-8 CSV with exactly the ordered header
`warehouse,sku,quantity`. Warehouse and SKU are opaque, case-sensitive, nonempty
strings; do not strip, casefold or otherwise normalize them. A (warehouse, SKU)
pair may appear only once per file. Quantity must contain one or more ASCII
digits and represents a nonnegative integer. Reject missing/extra columns,
incorrect headers, duplicate pairs, empty IDs and invalid quantities with
ValueError. A header-only file is valid. Normal CSV quoting and Unicode IDs work.
Return a dict mapping (warehouse, SKU) tuples to integer quantities.

`sku_aliases.read_aliases(path)` reads a JSON object mapping nonempty string SKUs
to nonempty string SKUs. Invalid JSON, non-object data and invalid keys/values
raise ValueError. `sku_aliases.resolve(sku, aliases)` follows alias chains to the
terminal SKU; reject cycles (including self aliases) with ValueError. The
application rejects a cycle anywhere in the supplied alias table even when its
SKUs are absent from the stock files. With no alias file use an empty mapping.

`movement_plan.plan(before, after, aliases)` accepts read_stock dicts and the
alias mapping. Resolve every SKU and aggregate quantities for each resulting
(warehouse, canonical SKU) pair in each snapshot before comparing. Missing
entries mean zero. Return a list of dicts with warehouse, sku, before, after and
delta (after minus before), containing only nonzero changes, sorted by the
(warehouse, canonical SKU) Python string tuple. Do not mutate input mappings.

`stock_report.report(changes)` returns a dict with `changes` holding the input
list and `summary` containing increased_units (sum of positive deltas),
decreased_units (absolute sum of negative deltas) and net_units (sum of deltas).
An empty plan has an empty changes list and all three summary values zero.

`reconcile.run(before_path, after_path, aliases_path=None)` returns that report.
Content validation failures raise ValueError. The public module interfaces above
must also work independently.

CLI: `python reconcile.py BEFORE AFTER [--aliases JSON] [--output JSON]`.
On success write one compact JSON document with a final newline, preserving
Unicode. Write stdout unless --output is supplied; then write only the named
output file, with no stdout. On invalid input or IO failure exit 2, produce a
useful `error:` diagnostic on stderr, leave stdout empty and preserve any
pre-existing output file. Validate all inputs before opening an output file.
Never edit this contract to change a requirement.
'''


def fixture():
    return {
        '.gitignore': '__pycache__/\n*.py[cod]\n.opencode/\nopencode.json\n',
        'CONTRACT.md': CONTRACT,
        'stock_reader.py': 'def read_stock(path):\n    raise NotImplementedError\n',
        'sku_aliases.py': 'def read_aliases(path):\n    raise NotImplementedError\n\ndef resolve(sku, aliases):\n    raise NotImplementedError\n',
        'movement_plan.py': 'def plan(before, after, aliases):\n    raise NotImplementedError\n',
        'stock_report.py': 'def report(changes):\n    raise NotImplementedError\n',
        'reconcile.py': 'def run(before_path, after_path, aliases_path=None):\n    raise NotImplementedError\n\nif __name__ == "__main__":\n    raise NotImplementedError\n',
        'before.csv': 'warehouse,sku,quantity\nNorth,old-A,4\nNorth,A,2\nSouth,B,5\n',
        'after.csv': 'warehouse,sku,quantity\nNorth,A,3\nSouth,B,5\nSouth,C,2\n',
        'aliases.json': '{"old-A":"A"}\n',
        'README.md': 'Stock reconciliation application. Implement the module interfaces and CLI in CONTRACT.md.\n',
    }


PARSER_PROBE = r'''
import tempfile
from pathlib import Path
from stock_reader import read_stock
with tempfile.TemporaryDirectory() as td:
    path = Path(td) / 'input.csv'
    path.write_text('warehouse,sku,quantity\nNorth,A,004\nSouth,A,0\n"Zone, East",猫,7\nNorth, A ,2\n', encoding='utf-8')
    assert read_stock(path) == {('North','A'):4, ('South','A'):0, ('Zone, East','猫'):7, ('North',' A '):2}
    path.write_text('warehouse,sku,quantity\n', encoding='utf-8')
    assert read_stock(path) == {}
    for text in ['', 'sku,warehouse,quantity\nA,N,1\n', 'warehouse,sku,quantity\nN,A,1\nN,A,2\n',
                 'warehouse,sku,quantity\n,A,1\n', 'warehouse,sku,quantity\nN,,1\n',
                 'warehouse,sku,quantity\nN,A,-1\n', 'warehouse,sku,quantity\nN,A,1.0\n',
                 'warehouse,sku,quantity\nN,A,١\n', 'warehouse,sku,quantity\nN,A,+1\n',
                 'warehouse,sku,quantity\nN,A, 1\n', 'warehouse,sku,quantity\nN,A\n',
                 'warehouse,sku,quantity\nN,A,1,extra\n']:
        path.write_text(text, encoding='utf-8')
        try: read_stock(path)
        except ValueError: pass
        else: raise AssertionError('Invalid CSV accepted: '+repr(text))
'''

FULL_PROBE = PARSER_PROBE + r'''
import copy, json, subprocess, sys
from sku_aliases import read_aliases, resolve
from movement_plan import plan
from stock_report import report
from reconcile import run
before = {('North','old-A'):4, ('North','A'):2, ('South','B'):5, ('South','猫'):8}
after = {('North','A'):3, ('South','B'):5, ('South','C'):2, ('South','猫'):9}
aliases = {'old-A':'intermediate', 'intermediate':'A'}
original = copy.deepcopy((before, after, aliases))
changes = [{'warehouse':'North','sku':'A','before':6,'after':3,'delta':-3},
           {'warehouse':'South','sku':'C','before':0,'after':2,'delta':2},
           {'warehouse':'South','sku':'猫','before':8,'after':9,'delta':1}]
wanted = {'changes':changes, 'summary':{'increased_units':3,'decreased_units':3,'net_units':0}}
assert resolve('old-A', aliases) == 'A'
assert resolve('absent', aliases) == 'absent'
assert plan(before, after, aliases) == changes
assert (before, after, aliases) == original, 'Inputs mutated'
assert report(changes) == wanted
assert report([]) == {'changes':[], 'summary':{'increased_units':0,'decreased_units':0,'net_units':0}}
assert plan({('N','a'):0}, {}, {}) == []
assert plan({('N','a'):1}, {}, {}) == [{'warehouse':'N','sku':'a','before':1,'after':0,'delta':-1}]
for table in [{'a':'a'}, {'a':'b','b':'a'}]:
    try: resolve('a', table)
    except ValueError: pass
    else: raise AssertionError('Alias cycle accepted')
with tempfile.TemporaryDirectory() as td:
    a,b,j,out = (Path(td)/name for name in ('before.csv','after.csv','aliases.json','output.json'))
    a.write_text('warehouse,sku,quantity\nNorth,old-A,4\nNorth,A,2\nSouth,B,5\nSouth,猫,8\n',encoding='utf-8')
    b.write_text('warehouse,sku,quantity\nNorth,A,3\nSouth,B,5\nSouth,C,2\nSouth,猫,9\n',encoding='utf-8')
    j.write_text(json.dumps(aliases),encoding='utf-8')
    assert read_aliases(j) == aliases
    assert run(a,b,j) == wanted
    assert run(a,a) == {'changes':[], 'summary':{'increased_units':0,'decreased_units':0,'net_units':0}}
    def cli(*extra):
        return subprocess.run([sys.executable,'-B','reconcile.py',str(a),str(b),*map(str,extra)],capture_output=True,text=True,encoding='utf-8',timeout=5)
    p = cli('--aliases',j)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout) == wanted
    assert '猫' in p.stdout and p.stdout.endswith('\n') and len(p.stdout.splitlines()) == 1
    assert ': ' not in p.stdout and ', ' not in p.stdout, 'CLI JSON is not compact'
    p = cli('--aliases',j,'--output',out)
    assert p.returncode == 0 and not p.stdout, (p.stdout,p.stderr)
    assert json.loads(out.read_text(encoding='utf-8')) == wanted
    for text in ['[]', '{"a":1}', '{"":"a"}', '{"a":""}', 'null', '{bad']:
        j.write_text(text,encoding='utf-8')
        try: read_aliases(j)
        except ValueError: pass
        else: raise AssertionError('Invalid alias data accepted')
    j.write_text('{"unused":"other","other":"unused"}',encoding='utf-8')
    try: run(a,b,j)
    except ValueError: pass
    else: raise AssertionError('Unused alias cycle accepted')
    for failure in ('cycle','csv','missing'):
        j.write_text('{}' if failure != 'cycle' else '{"x":"x"}',encoding='utf-8')
        b.write_text('warehouse,sku,quantity\nNorth,A,-1\n' if failure == 'csv' else 'warehouse,sku,quantity\nNorth,A,3\n',encoding='utf-8')
        selected = j if failure != 'missing' else Path(td)/'absent.json'
        out.write_text('KEEP EXISTING OUTPUT\n',encoding='utf-8')
        p = cli('--aliases',selected,'--output',out)
        assert p.returncode == 2 and not p.stdout and 'error:' in p.stderr.lower(), (p.returncode,p.stdout,p.stderr)
        assert out.read_text(encoding='utf-8') == 'KEEP EXISTING OUTPUT\n'
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(args):
    dest = Path(args.dest).resolve()
    if dest.exists():
        raise ValueError('Use a fresh destination; a failed/completed writer is never silently retried')
    dest.mkdir(parents=True)
    repo = dest / 'repo'
    repo.mkdir()
    suite.git(repo, 'init', '-b', 'main')
    suite.git(repo, 'config', 'user.name', 'Synthetic Fixture')
    suite.git(repo, 'config', 'user.email', 'fixture@example.invalid')
    suite.git(repo, 'config', 'core.autocrlf', 'false')
    for name, content in fixture().items():
        suite.write(repo, name, content)
    initial = suite.commit(repo, 'Synthetic stock reconciliation v2 initial source')
    state = {'case': CASE, 'fixture_version': VERSION, 'phase': 'writer', 'initial': initial,
             'writer_start': initial, 'synthetic': True,
             'events': [{'event': 'initial_source', 'commit': initial, 'branch': 'main'}]}
    (dest / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    (dest / 'prompts.json').write_text(json.dumps({'writer': WRITER_PROMPT, 'consumer': CONSUMER_PROMPT}, indent=2), encoding='utf-8')
    return state


def source_authority(repo, state):
    return all((repo / name).is_file() and
               suite.git(repo, 'hash-object', '--', name) == suite.git(repo, 'rev-parse', state['initial'] + ':' + name)
               for name in ('CONTRACT.md',))


def probe(repo, code):
    """Run private outcomes in a scratch copy, so imports cannot write actor source."""
    def exclude(directory, names):
        return [name for name in names if name in {'.git', '.opencode', 'opencode.json', '__pycache__'} or name.endswith('.pyc')]
    with tempfile.TemporaryDirectory(prefix='checkpoint-outcome-') as temp:
        scratch = Path(temp) / 'source'
        shutil.copytree(repo, scratch, ignore=exclude)
        command = 'import sys; sys.path.insert(0, ' + repr(str(scratch)) + ');\n' + textwrap.dedent(code)
        try:
            result = subprocess.run([sys.executable, '-B', '-I', '-c', command], cwd=scratch,
                                    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
            return {'passed': result.returncode == 0, 'returncode': result.returncode,
                    'stdout': result.stdout[-3000:], 'stderr': result.stderr[-5000:]}
        except subprocess.TimeoutExpired:
            return {'passed': False, 'timeout': True, 'stderr': 'Independent artifact probe exceeded 15 seconds'}


def assess(repo, state):
    before = source_snapshot(repo, RUNTIME_PATHS)
    initial_reader = subprocess.run(['git', 'show', state['initial'] + ':stock_reader.py'], cwd=repo,
                                    capture_output=True, check=True).stdout.decode('utf-8')
    try:
        meaningful = ast.dump(ast.parse((repo / 'stock_reader.py').read_text(encoding='utf-8'))) != ast.dump(ast.parse(initial_reader))
    except (OSError, SyntaxError, UnicodeError):
        meaningful = False
    authority = source_authority(repo, state)
    parser = probe(repo, PARSER_PROBE)
    full = probe(repo, FULL_PROBE)
    after = source_snapshot(repo, RUNTIME_PATHS)
    unchanged = before['working_content_sha256'] == after['working_content_sha256']
    return {'fixture_version': VERSION, 'meaningful_reader_ast_change': meaningful,
            'source_authority_intact': authority, 'parser': parser, 'full': full,
            'private_probes_left_source_unchanged': unchanged,
            'eligible': meaningful and authority and parser['passed'] and not full['passed'] and unchanged,
            'writer_already_complete': authority and full['passed'], 'source_snapshot': before}


def advance(args, after_freeze=None):
    dest = Path(args.run).resolve()
    state = json.loads((dest / 'state.json').read_text(encoding='utf-8'))
    repo = dest / 'repo'
    if state['phase'] != 'writer':
        raise ValueError('Writer phase already frozen')
    assessment = assess(repo, state)
    if not assessment['eligible']:
        raise ValueError('Frozen writer must remain a meaningful, parser-valid unfinished application')
    tip = suite.commit(repo, 'Freeze actual interrupted stock reconciliation v2 writer')
    state['events'].append({'event': 'writer_frozen', 'commit': tip, 'branch': suite.git(repo, 'branch', '--show-current')})
    (dest / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    if after_freeze:
        after_freeze(repo, tip)
        if suite.git(repo, 'rev-parse', 'HEAD') != tip or suite.git(repo, 'diff', '--name-only') or suite.git(repo, 'diff', '--cached', '--name-only'):
            raise ValueError('Native observer changed frozen source')
    state.update(phase='consumer', consumer_start=tip, variant='default')
    (dest / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    return state


def materialize(args):
    return suite.materialize(args)


def check(args):
    dest = Path(args.run).resolve()
    state = json.loads((dest / 'state.json').read_text(encoding='utf-8'))
    repo = dest / 'repo'
    if state['phase'] != 'consumer':
        raise ValueError('Freeze actual writer before final consumer checks')
    result = {'case': CASE, 'fixture_version': VERSION, 'check_kind': 'independent deterministic final-artifact probe',
              'source_authority_intact': source_authority(repo, state), 'probe': probe(repo, FULL_PROBE),
              'model_evaluation_status': 'not established by this check'}
    result['status'] = 'passed' if result['source_authority_intact'] and result['probe']['passed'] else 'failed'
    (dest / 'outcome.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['status'] == 'passed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('dest'); p.set_defaults(func=prepare)
    for name, function in (('advance', advance), ('check', check)):
        p = sub.add_parser(name); p.add_argument('run'); p.set_defaults(func=function)
    args = parser.parse_args()
    result = args.func(args)
    if isinstance(result, int):
        return result
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
