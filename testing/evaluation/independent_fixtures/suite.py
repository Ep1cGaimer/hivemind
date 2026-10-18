"""Independent synthetic outcome fixtures. Never copy this file into a tested repo."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import textwrap
import uuid

HERE = Path(__file__).resolve().parent
CASES = (
    "failed_approach", "build_prerequisite", "branch_constraint",
    "unfinished_checkpoint", "stale_guidance", "conflicting_interpretations",
    "integration_applicability", "no_history",
)


def clean(s):
    return textwrap.dedent(s).lstrip("\n")


def run(argv, cwd, check=True):
    p = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=30)
    if check and p.returncode:
        raise RuntimeError(f"{argv!r}: {p.stdout}\n{p.stderr}")
    return p


def git(repo, *args):
    return run(["git", *args], repo).stdout.strip()


def write(repo, name, content):
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(clean(content), encoding="utf-8", newline="\n")


def commit(repo, message):
    git(repo, "add", "--all")
    git(repo, "commit", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def fixture(case):
    """Only public task source; external outcome probes below are not copied."""
    common = {".gitignore": "__pycache__/\n*.pyc\n"}
    if case == "failed_approach":
        common.update({
            "catalog.py": '''
                import sqlite3
                from decimal import Decimal
                def connect():
                    db = sqlite3.connect(':memory:')
                    db.execute('CREATE TABLE items (sku TEXT PRIMARY KEY, price TEXT)')
                    db.executemany('INSERT INTO items VALUES (?, ?)', [('A_1','3.20'),('AX1','99.00'),('B%2','4.50'),('BZZ2','88.00')])
                    return db
                def lookup(db, sku):
                    row = db.execute('SELECT price FROM items WHERE sku LIKE ? ORDER BY price DESC', (sku,)).fetchone()
                    if row is None: raise KeyError(sku)
                    return Decimal(row[0])
            ''',
            "cart.py": "def total(db, lines):\n    raise NotImplementedError\n",
            "demo.py": "from catalog import connect,lookup\nprint(lookup(connect(), 'A_1'))\n",
            "CONTRACT.md": "SKUs are opaque exact identifiers, including punctuation. Prices use Decimal. Cart lines are (sku, positive integer quantity) pairs; missing SKU raises KeyError.\n",
        })
    elif case == "build_prerequisite":
        common.update({
            ".gitignore": common[".gitignore"] + "schema_generated.py\n",
            "fields.json": '[{"name":"code","type":"str"},{"name":"units","type":"int"}]\n',
            "tools/build.py": '''
                import json
                from pathlib import Path
                root = Path(__file__).resolve().parents[1]
                fields = json.loads((root/'fields.json').read_text())
                (root/'schema_generated.py').write_text('FIELDS = ' + repr(fields) + '\\n', encoding='utf-8')
                print('schema generated')
            ''',
            "decoder.py": '''
                import json
                from schema_generated import FIELDS
                def decode(text):
                    values=json.loads(text)
                    return {f['name']: str(values[f['name']]) for f in FIELDS}
            ''',
            "encoder.py": "def encode(values):\n    raise NotImplementedError\n",
            "demo.py": "from decoder import decode\nprint(decode('{\"code\":\"a\",\"units\":3}'))\n",
            "roundtrip.py": "from encoder import encode\nfrom decoder import decode\nprint(decode(encode({'code':'demo','units':3})))\n",
            "CONTRACT.md": "Wire format is compact JSON in declared field order, ignoring extras. Schema types str/int must be enforced by encoder and decoder. The delivered checkout must run roundtrip.py successfully, using its generated schema. No third-party build tools are needed.\n",
        })
    elif case == "branch_constraint":
        common.update({
            "policy.json": '{"allow_unicode":false}\n',
            "slug.py": "def slug(text):\n    raise NotImplementedError\n",
            "routes.py": "def path_for(title):\n    raise NotImplementedError\n",
            "CONTRACT.md": "Slug: casefold; ASCII mode drops non-ASCII characters; replace each run of non-alphanumeric characters with one hyphen; trim hyphens. Route is /articles/<slug>. policy.json is authoritative for this branch.\n",
        })
    elif case == "unfinished_checkpoint":
        common.update({
            "reconcile.py": '''
                import csv, json, sys
                def read_stock(path):
                    raise NotImplementedError
                def run(before, after):
                    raise NotImplementedError
                if __name__ == '__main__':
                    raise NotImplementedError
            ''',
            "before.csv": "id,quantity\nA,4\nB,2\n",
            "after.csv": "id,quantity\nA,1\nC,3\n",
            "CONTRACT.md": "CSV columns id,quantity; quantities must be nonnegative integers, IDs nonempty and unique per file. Invalid input raises ValueError. run returns sorted list of {id,delta} for nonzero after-minus-before changes, treating missing entries as zero. CLI: python reconcile.py BEFORE AFTER, printing that list as JSON.\n",
        })
    elif case == "stale_guidance":
        common.update({
            "money_policy.json": '{"rounding":"ROUND_HALF_UP","round_each_line":true}\n',
            "display.py": "def display_amount(value):\n    raise NotImplementedError\n",
            "invoice.py": "def total(lines):\n    raise NotImplementedError\n",
            "CONTRACT.md": "All inputs are decimal strings. display_amount and invoice.total return fixed two-decimal strings. The current money_policy.json controls rounding. Invoice totals round each line then sum.\n",
        })
    elif case == "conflicting_interpretations":
        common.update({
            "docs/customer.md": "A quoted amount already includes tax; tax must be extracted from the total.\n",
            "docs/finance.md": "A quoted amount excludes tax; tax must be added to the total.\n",
            "runtime.json": '{"tax_mode":"exclusive"}\n',
            "preview.py": "def preview(amount, rate):\n    raise NotImplementedError\n",
            "quotes.py": "def quote(amount, rate):\n    raise NotImplementedError\n",
            "CONTRACT.md": "The two stakeholder guides disagree. runtime.json is authoritative per deployment and may change at runtime. quote accepts amount/rate decimal strings (rate .20 means 20 percent), returns {net,tax,gross} two-decimal strings using ROUND_HALF_UP. Exclusive mode adds tax; inclusive mode extracts tax. Return net and gross first rounded to cents, then tax as their difference. Document your resolution in DECISION.md, referencing both guides and the runtime authority.\n",
        })
    elif case == "integration_applicability":
        common.update({
            "transport.py": '''
                import json
                VERSION=1
                def serialize(data):
                    return b'v1:' + json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
            ''',
            "digest.py": "def digest(data):\n    raise NotImplementedError\n",
            "packets.py": "def packet(data):\n    raise NotImplementedError\n",
            "CONTRACT.md": "packet returns {wire_hex,sha256} for the exact bytes from the current transport.serialize function. Digest is lower-case SHA256 hex. Transport version is selected by integrated source, not a caller option.\n",
        })
    else:
        common.update({
            "stats.py": "def histogram(values):\n    raise NotImplementedError\n",
            "CONTRACT.md": "histogram takes a list of signed integers; returns a dict mapping each integer to its frequency; does not mutate input. Empty input returns {}.\n",
        })
    return common


WRITER = {
    "failed_approach": "A catalog lookup returns an implausible price for SKU A_1. Investigate the existing query, repair exact-ID lookup, and validate with local examples. Leave cart work for a later task.",
    "build_prerequisite": "Get demo.py running from this checkout and fix decoder.py so its output follows the schema's declared types. Validate your change. Leave encoder implementation for later.",
    "branch_constraint": "Implement and validate slug.slug for this checkout's policy. Leave routes.py for a follow-up task.",
    "unfinished_checkpoint": "Implement the reconciliation tool described in CONTRACT.md, including input validation, comparison and CLI. Work normally and validate as you go.",
    "stale_guidance": "Implement and validate display.display_amount following the current money policy. Leave invoice totals for a follow-up task.",
    "conflicting_interpretations": "Investigate invoice preview behavior using docs/customer.md and the application contract. Implement preview.preview(amount, rate) with the same shape as quote, validate it and explain any unresolved interpretation.",
    "integration_applicability": "Implement digest.digest(data) and validate it against this branch's transport representation. Leave packets.py for follow-up work.",
    "no_history": None,
}

CONSUMER = {
    "failed_approach": "Implement cart.total(db, lines) according to CONTRACT.md. Validate it and summarize the result.",
    "build_prerequisite": "Implement encoder.encode(values) according to CONTRACT.md, ensure the encoder/decoder round-trip works in this fresh checkout, and validate it.",
    "branch_constraint": "Implement routes.path_for(title) according to the current checkout's contract. Complete any helper work needed and validate it.",
    "unfinished_checkpoint": "Continue the reconciliation tool from its current state and finish the complete contract, including CLI and invalid-input handling. Validate the final tool.",
    "stale_guidance": "Implement invoice.total(lines) according to the current checkout's contract and validate rounding edge cases.",
    "conflicting_interpretations": "Implement quotes.quote(amount, rate) for the current deployment, write the requested DECISION.md, and validate the behavior.",
    "integration_applicability": "Implement packets.packet(data) according to the current checkout's contract. Complete any helper work needed and validate the packet bytes and digest.",
    "no_history": "Implement stats.histogram(values) according to CONTRACT.md and validate normal and edge cases.",
}


def prepare(args):
    dest = Path(args.dest).resolve()
    # Keys and control files live outside repo, even when preparing in this suite.
    if dest.exists():
        raise ValueError("Destination must not exist; use a fresh path for every run")
    if HERE == dest or HERE.is_relative_to(dest):
        raise ValueError("Destination cannot contain the evaluator")
    dest.mkdir(parents=True)
    repo = dest / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Synthetic Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "core.autocrlf", "false")
    for name, content in fixture(args.case).items():
        write(repo, name, content)
    initial = commit(repo, "Synthetic initial task source")
    events = [{"event": "initial_source", "commit": initial, "branch": "main"}]
    if args.case == "branch_constraint":
        git(repo, "checkout", "-b", "partner-unicode")
        write(repo, "policy.json", '{"allow_unicode":true}\n')
        events.append({"event": "branch_policy", "commit": commit(repo, "Partner Unicode policy"), "branch": "partner-unicode"})
    if args.case == "integration_applicability":
        git(repo, "checkout", "-b", "transport-v2")
        write(repo, "transport.py", '''
            import json
            VERSION=2
            def serialize(data):
                return b'v2\\n' + json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        ''')
        events.append({"event": "feature_transport", "commit": commit(repo, "Transport v2 representation"), "branch": "transport-v2"})
    state = {"case": args.case, "phase": "writer" if WRITER[args.case] else "consumer", "initial": initial,
             "writer_start": git(repo, "rev-parse", "HEAD"), "events": events, "synthetic": True}
    (dest / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    prompts = {"writer": WRITER[args.case], "consumer": CONSUMER[args.case]}
    if args.case == "conflicting_interpretations":
        prompts["writer_two"] = WRITER[args.case].replace("docs/customer.md", "docs/finance.md")
    (dest / "prompts.json").write_text(json.dumps(prompts, indent=2), encoding="utf-8")
    print(json.dumps({"run": str(dest), "repo": str(repo), "phase": state["phase"], "prompt": prompts[state["phase"]]}, indent=2))


def advance(args, after_freeze=None):
    dest = Path(args.run).resolve()
    state = json.loads((dest / "state.json").read_text())
    repo = dest / "repo"
    if state["phase"] != "writer":
        raise ValueError("Already advanced, or this case has no writer")
    case = state["case"]
    changed = git(repo, "diff", "--stat", state["writer_start"])
    if not changed:
        raise ValueError("No actual writer source change; do not manufacture a writer history")
    previous = next((e for e in reversed(state['events']) if e.get('event') == 'writer_frozen'), None)
    if previous and previous['commit'] == git(repo, 'rev-parse', 'HEAD') and not git(repo, 'diff', '--name-only') and not git(repo, 'diff', '--cached', '--name-only'):
        writer_tip = previous['commit']
    else:
        writer_tip = commit(repo, "Freeze actual writer work for fresh consumer")
        state["events"].append({"event": "writer_frozen", "commit": writer_tip, "branch": git(repo, "branch", "--show-current")})
    # Persist the real freeze before an external native observer runs. Failure
    # leaves the original branch/source intact; retry reuses this exact commit.
    (dest / 'state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    if after_freeze is not None:
        after_freeze(repo, writer_tip)
        if git(repo, 'rev-parse', 'HEAD') != writer_tip or git(repo, 'diff', '--name-only') or git(repo, 'diff', '--cached', '--name-only'):
            raise ValueError('after_freeze observer changed the frozen source or checkout')
    if case == "build_prerequisite":
        artifact = repo / "schema_generated.py"
        if artifact.exists():
            artifact.unlink()  # Exact ignored generated file, never recursive.
    elif case == "stale_guidance":
        write(repo, "money_policy.json", '{"rounding":"ROUND_HALF_EVEN","round_each_line":true}\n')
        state["events"].append({"event": "policy_changed", "commit": commit(repo, "Adopt half-even money policy")})
    elif case == "branch_constraint" and args.variant == "main":
        git(repo, "checkout", "main")
    elif case == "integration_applicability":
        git(repo, "checkout", "main")
        if args.variant != "before":
            git(repo, "merge", "--no-ff", "transport-v2", "-m", "Integrate transport v2 and its writer implementation")
            state["events"].append({"event": "verified_merge", "commit": git(repo, "rev-parse", "HEAD"), "parents": git(repo, "show", "-s", "--format=%P", "HEAD").split()})
    state["phase"] = "consumer"
    state["variant"] = args.variant
    state["consumer_start"] = git(repo, "rev-parse", "HEAD")
    (dest / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({"repo": str(repo), "branch": git(repo, "branch", "--show-current"), "head": state["consumer_start"], "prompt": CONSUMER[case]}, indent=2))


# Probes run in fresh subprocesses with only the tested repo on the import path.
# They do not repair source, invoke builds or provide a tested assistant answers.
PROBES = {
    "failed_approach": '''
        from decimal import Decimal
        from catalog import connect
        from cart import total
        db=connect()
        assert total(db,[('A_1',2),('B%2',3)]) == Decimal('19.90')
        assert total(db,[]) == Decimal('0')
        for missing in ['missing', "%' OR 1=1 --"]:
            try: total(db,[(missing,1)])
            except KeyError: pass
            else: raise AssertionError('Missing opaque ID must not match')
    ''',
    "build_prerequisite": '''
        import json
        from pathlib import Path
        assert Path('schema_generated.py').is_file(), 'Consumer did not generate schema'
        from encoder import encode
        from decoder import decode
        out=encode({'units':'7','code':123,'extra':'ignored'})
        assert out == '{"code":"123","units":7}', repr(out)
        assert json.loads(encode({'code':'é','units':-2})) == {'code':'é','units':-2}
        assert decode(encode({'code':'item','units':'7'})) == {'code':'item','units':7}
    ''',
    "branch_constraint": '''
        import json
        from routes import path_for
        unicode=json.load(open('policy.json'))['allow_unicode']
        assert path_for('  CAFÉ / Straße --猫  ') == ('/articles/café-strasse-猫' if unicode else '/articles/caf-strasse')
        assert path_for('A___B... C') == '/articles/a-b-c'
        assert path_for('---') == '/articles/'
    ''',
    "unfinished_checkpoint": '''
        import json, subprocess, sys, tempfile
        from pathlib import Path
        from reconcile import run
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/'a.csv',Path(td)/'b.csv'
            a.write_text('id,quantity\\nA,4\\nB,2\\n猫,7\\n',encoding='utf-8')
            b.write_text('id,quantity\\nA,1\\nC,3\\n猫,7\\n',encoding='utf-8')
            wanted=[{'id':'A','delta':-3},{'id':'B','delta':-2},{'id':'C','delta':3}]
            assert run(a,b)==wanted
            p=subprocess.run([sys.executable,'reconcile.py',str(a),str(b)],capture_output=True,text=True,timeout=10)
            assert p.returncode==0,p.stderr
            assert json.loads(p.stdout)==wanted
            for bad in ['id,quantity\\nA,1\\nA,2\\n','id,quantity\\nA,-1\\n','id,quantity\\nA,1.5\\n','id,quantity\\n,2\\n']:
                b.write_text(bad,encoding='utf-8')
                try: run(a,b)
                except ValueError: pass
                else: raise AssertionError('Invalid CSV accepted')
    ''',
    "stale_guidance": '''
        from invoice import total
        assert total(['1.005']) == '1.00'
        assert total(['1.015']) == '1.02'
        assert total(['1.005','1.005']) == '2.00'
        assert total(['-1.005','2.005']) == '1.00'
        assert total([]) == '0.00'
    ''',
    "conflicting_interpretations": '''
        import json
        from pathlib import Path
        from quotes import quote
        p=Path('runtime.json'); original=p.read_bytes()
        try:
            p.write_text(json.dumps({'tax_mode':'exclusive'}))
            assert quote('100','.20') == {'net':'100.00','tax':'20.00','gross':'120.00'}
            assert quote('0','.20') == {'net':'0.00','tax':'0.00','gross':'0.00'}
            p.write_text(json.dumps({'tax_mode':'inclusive'}))
            assert quote('120','.20') == {'net':'100.00','tax':'20.00','gross':'120.00'}
            assert quote('10','.20') == {'net':'8.33','tax':'1.67','gross':'10.00'}
        finally: p.write_bytes(original)
        rationale=Path('DECISION.md').read_text(encoding='utf-8')
        assert all(s in rationale for s in ['docs/customer.md','docs/finance.md','runtime.json'])
    ''',
    "integration_applicability": '''
        import hashlib, json
        from transport import VERSION
        from packets import packet
        for data in [{'z':'猫','a':1},{}, {'x':['é',2]}]:
            if VERSION==1:
                wire=b'v1:' + json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
            else:
                assert VERSION==2
                wire=b'v2\\n' + json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
            assert packet(data)=={'wire_hex':wire.hex(),'sha256':hashlib.sha256(wire).hexdigest()}
    ''',
    "no_history": '''
        from stats import histogram
        v=[0,-2,3,-2,0,3,3]; original=v[:]
        assert histogram(v)=={-2:2,0:2,3:3}
        assert v==original
        assert histogram([])=={}
        assert histogram([10**20,-10**20,10**20])=={10**20:2,-10**20:1}
    ''',
}


def check(args):
    dest=Path(args.run).resolve()
    state=json.loads((dest/'state.json').read_text())
    if state['phase']!='consumer':
        raise ValueError('Advance to consumer phase before final outcome checks')
    repo=dest/'repo'
    start=state.get('consumer_start',state['initial'])
    protected=['CONTRACT.md']
    protected += {'branch_constraint':['policy.json'], 'stale_guidance':['money_policy.json'],
                  'build_prerequisite':['fields.json','tools/build.py'],
                  'conflicting_interpretations':['runtime.json','docs/customer.md','docs/finance.md'],
                  'integration_applicability':['transport.py']}.get(state['case'],[])
    altered=[name for name in protected if not (repo/name).is_file() or
             git(repo,'hash-object','--',name)!=git(repo,'rev-parse',f'{start}:{name}')]
    if altered:
        result={'case':state['case'],'status':'failed','reason':'Task requirements/source authority changed',
                'altered_protected_files':altered,'model_evaluation_status':'not established by this check'}
        (dest/'outcome.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
        return 1
    try:
        p=run([sys.executable,'-c',clean(PROBES[state['case']])],repo,check=False)
    except subprocess.TimeoutExpired:
        result={'case':state['case'],'status':'failed','reason':'Final-artifact probe timed out',
                'model_evaluation_status':'not established by this check'}
        (dest/'outcome.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
        return 1
    result={"case":state['case'],"check_kind":"independent deterministic final-artifact probe",
            "status":"passed" if p.returncode==0 else "failed", "returncode":p.returncode,
            "stdout":p.stdout,"stderr":p.stderr,"head":git(repo,'rev-parse','HEAD'),
            "branch":git(repo,'branch','--show-current'),"working_diff":git(repo,'diff','--stat'),
            "model_evaluation_status":"not established by this check"}
    (dest/'outcome.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return p.returncode


def export_control(args):
    dest=Path(args.run).resolve(); repo=dest/'repo'
    state=json.loads((dest/'state.json').read_text())
    # Raw model capture export, including all qualifications and metadata, is retained.
    findings=json.loads(Path(args.findings).read_text(encoding='utf-8')) if args.findings else []
    current={}
    for name in git(repo,'ls-files').splitlines():
        p=repo/name
        if p.is_file():
            data=p.read_bytes()
            current[name]={"text":data.decode('utf-8'),"sha256":hashlib.sha256(data).hexdigest(),
                           "git_blob":git(repo,'hash-object','--',name)}
    history=[]
    # These small fixtures have deliberately bounded Git histories. All reachable
    # branch revisions and historical source content are available to notes.
    for sha in git(repo,'rev-list','--all').splitlines():
        files={}
        for name in git(repo,'ls-tree','-r','--name-only',sha).splitlines():
            files[name]={"git_blob":git(repo,'rev-parse',f'{sha}:{name}'),
                         "text":git(repo,'show',f'{sha}:{name}')}
        history.append({"commit":sha,"parents":git(repo,'show','-s','--format=%P',sha).split(),"files":files})
    bundle={"format":"source-linked-notes-control-v1","synthetic":True,"findings_unmodified":findings,
            "events":state['events'],"current_branch":git(repo,'branch','--show-current'),
            "head":git(repo,'rev-parse','HEAD'),"refs":git(repo,'show-ref'),
            "status":git(repo,'status','--porcelain'),"current_sources":current,"history":history,
            "limitations":"This is an input export, not a notes retrieval implementation. Apply equal context budgets and permit full-source inspection. Do not include evaluator keys or outcome probes in model context."}
    out=Path(args.output).resolve()
    if out==repo or repo in out.parents:
        raise ValueError('Control export must be outside tested repo')
    out.write_text(json.dumps(bundle,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({"output":str(out),"commits":len(history),"current_sources":len(current),"findings_supplied":bool(args.findings)}))


def materialize(args):
    source=Path(args.run).resolve(); dest=Path(args.dest).resolve()
    state=json.loads((source/'state.json').read_text())
    repo=source/'repo'
    if state['phase']!='consumer':
        raise ValueError('Freeze writer and apply transition before making condition clones')
    if git(repo,'diff','--name-only') or git(repo,'diff','--cached','--name-only'):
        raise ValueError('Freeze source changes before cloning conditions')
    if dest.exists():
        raise ValueError('Destination must not exist')
    if HERE==dest or HERE.is_relative_to(dest):
        raise ValueError('Destination cannot contain the evaluator')
    dest.mkdir(parents=True)
    git(dest,'-c','core.autocrlf=false','clone','--no-local','--no-hardlinks',str(repo),'repo')
    git(dest/'repo','config','user.name','Synthetic Fixture')
    git(dest/'repo','config','user.email','fixture@example.invalid')
    git(dest/'repo','config','core.autocrlf','false')
    for filename in ('state.json','prompts.json'):
        shutil.copyfile(source/filename,dest/filename)
    print(json.dumps({'run':str(dest),'repo':str(dest/'repo'),'head':git(dest/'repo','rev-parse','HEAD'),
                      'isolation':'Git source only; no writer conversations, generated files, or answer keys copied'}))


def plan(args):
    rows=[]
    for repetition in range(1,4):
        for case in CASES:
            for condition in ('source_only','source_linked_notes','hivemind'):
                rows.append({"case":case,"condition":condition,"repetition":repetition,
                             "session_id":str(uuid.uuid4()),"workspace":"must allocate fresh prepare destination",
                             "status":"untested","model":"record identical OpenCode Zen model identifier before execution",
                             "budget":"predeclare same task-level token/tool/time caps across all conditions"})
    random.Random(args.seed).shuffle(rows)
    Path(args.output).write_text(json.dumps({"seed":args.seed,"design":"8 distinct tasks x 3 conditions x 3 repeats; 72 consumer runs; additional applicability variants reported separately","runs":rows},indent=2),encoding='utf-8')
    print(json.dumps({"output":args.output,"runs":len(rows),"status":"plan only; no model calls"}))


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare'); q.add_argument('case',choices=CASES); q.add_argument('dest'); q.set_defaults(func=prepare)
    q=sub.add_parser('advance'); q.add_argument('run'); q.add_argument('--variant',choices=['default','main','before','after'],default='default'); q.set_defaults(func=advance)
    q=sub.add_parser('check'); q.add_argument('run'); q.set_defaults(func=check)
    q=sub.add_parser('materialize'); q.add_argument('run'); q.add_argument('dest'); q.set_defaults(func=materialize)
    q=sub.add_parser('export-control'); q.add_argument('run'); q.add_argument('--findings'); q.add_argument('--output',required=True); q.set_defaults(func=export_control)
    q=sub.add_parser('plan'); q.add_argument('--seed',type=int,default=1729); q.add_argument('--output',required=True); q.set_defaults(func=plan)
    args=p.parse_args()
    try:
        code=args.func(args)
    except Exception as e:
        print(json.dumps({'status':'error','error':str(e)}),file=sys.stderr)
        return 2
    return code if isinstance(code,int) else 0


if __name__=='__main__':
    sys.exit(main())
