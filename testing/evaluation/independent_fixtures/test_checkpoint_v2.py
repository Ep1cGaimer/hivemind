"""Private fixture/probe regression tests; no native model or service calls."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import checkpoint_v2 as fixture
import suite
from evidence_tools import source_snapshot


REFERENCE = {
    'stock_reader.py': '''
        import csv, re
        def read_stock(path):
            result={}
            with open(path,encoding='utf-8',newline='') as f:
                rows=csv.DictReader(f)
                if rows.fieldnames != ['warehouse','sku','quantity']: raise ValueError('header')
                for row in rows:
                    if set(row) != {'warehouse','sku','quantity'} or any(v is None for v in row.values()): raise ValueError('columns')
                    key=(row['warehouse'],row['sku'])
                    if not all(key) or key in result or not re.fullmatch('[0-9]+',row['quantity']): raise ValueError('row')
                    result[key]=int(row['quantity'])
            return result
    ''',
    'sku_aliases.py': '''
        import json
        def read_aliases(path):
            data=json.load(open(path,encoding='utf-8'))
            if not isinstance(data,dict) or not all(isinstance(k,str) and k and isinstance(v,str) and v for k,v in data.items()): raise ValueError('alias mapping')
            return data
        def resolve(sku,aliases):
            seen=set()
            while sku in aliases:
                if sku in seen: raise ValueError('cycle')
                seen.add(sku); sku=aliases[sku]
            return sku
    ''',
    'movement_plan.py': '''
        from sku_aliases import resolve
        def plan(before,after,aliases):
            for key in aliases: resolve(key,aliases)
            def canonical(data):
                out={}
                for (warehouse,sku),qty in data.items():
                    key=warehouse,resolve(sku,aliases)
                    out[key]=out.get(key,0)+qty
                return out
            a,b=canonical(before),canonical(after)
            return [dict(warehouse=w,sku=s,before=a.get((w,s),0),after=b.get((w,s),0),delta=b.get((w,s),0)-a.get((w,s),0))
                    for w,s in sorted(a.keys()|b.keys()) if a.get((w,s),0)!=b.get((w,s),0)]
    ''',
    'stock_report.py': '''
        def report(changes):
            return {'changes':changes,'summary':{'increased_units':sum(max(c['delta'],0) for c in changes),
                    'decreased_units':sum(max(-c['delta'],0) for c in changes),'net_units':sum(c['delta'] for c in changes)}}
    ''',
    'reconcile.py': '''
        import argparse,json,sys
        from stock_reader import read_stock
        from sku_aliases import read_aliases
        from movement_plan import plan
        from stock_report import report
        def run(before_path,after_path,aliases_path=None):
            return report(plan(read_stock(before_path),read_stock(after_path),read_aliases(aliases_path) if aliases_path else {}))
        if __name__=='__main__':
            p=argparse.ArgumentParser(); p.add_argument('before'); p.add_argument('after'); p.add_argument('--aliases'); p.add_argument('--output')
            a=p.parse_args()
            try:
                text=json.dumps(run(a.before,a.after,a.aliases),ensure_ascii=False,separators=(',',':'))+'\\n'
                if a.output:
                    with open(a.output,'w',encoding='utf-8',newline='') as f: f.write(text)
                else: sys.stdout.write(text)
            except (ValueError,OSError) as e:
                print('error: '+str(e),file=sys.stderr); sys.exit(2)
    ''',
}


class CheckpointV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='checkpoint-fixture-test-')
        self.run=Path(self.temp.name)/'run'
        self.state=fixture.prepare(NS(dest=str(self.run)))
        self.repo=self.run/'repo'

    def tearDown(self):
        self.temp.cleanup()

    def implement(self, files=None):
        for name,content in (files or REFERENCE).items():
            suite.write(self.repo,name,content)

    def test_stub_and_comment_only_are_not_meaningful_partial(self):
        result=fixture.assess(self.repo,self.state)
        self.assertFalse(result['eligible'])
        with (self.repo/'stock_reader.py').open('a') as f: f.write('# Work started\n')
        self.assertFalse(fixture.assess(self.repo,self.state)['meaningful_reader_ast_change'])

    def test_real_parser_only_partial_qualifies_and_probes_preserve_source(self):
        self.implement({'stock_reader.py':REFERENCE['stock_reader.py']})
        before=source_snapshot(self.repo,fixture.RUNTIME_PATHS)
        result=fixture.assess(self.repo,self.state)
        self.assertTrue(result['parser']['passed'],result)
        self.assertFalse(result['full']['passed'])
        self.assertTrue(result['eligible'])
        self.assertEqual(before,source_snapshot(self.repo,fixture.RUNTIME_PATHS))

    def test_completed_application_passes_but_is_invalid_checkpoint_premise(self):
        self.implement()
        result=fixture.assess(self.repo,self.state)
        self.assertTrue(result['full']['passed'],result['full'])
        self.assertTrue(result['writer_already_complete'])
        self.assertFalse(result['eligible'])
        with self.assertRaisesRegex(ValueError,'unfinished'): fixture.advance(NS(run=str(self.run)))

    def test_unicode_digit_and_unused_alias_cycle_are_not_weakened(self):
        self.implement()
        text=(self.repo/'stock_reader.py').read_text().replace("re.fullmatch('[0-9]+',row['quantity'])","row['quantity'].isdecimal()")
        (self.repo/'stock_reader.py').write_text(text,encoding='utf-8')
        self.assertFalse(fixture.probe(self.repo,fixture.PARSER_PROBE)['passed'])
        self.implement()
        text=(self.repo/'movement_plan.py').read_text().replace('for key in aliases: resolve(key,aliases)','pass')
        (self.repo/'movement_plan.py').write_text(text,encoding='utf-8')
        self.assertFalse(fixture.probe(self.repo,fixture.FULL_PROBE)['passed'])

    def test_contract_change_rejected_and_frozen_conditions_identical(self):
        self.implement({'stock_reader.py':REFERENCE['stock_reader.py']})
        (self.repo/'CONTRACT.md').write_text('Changed requirements\n',encoding='utf-8')
        self.assertFalse(fixture.assess(self.repo,self.state)['eligible'])
        suite.write(self.repo,'CONTRACT.md',fixture.CONTRACT)
        fixture.advance(NS(run=str(self.run)))
        expected=source_snapshot(self.repo,fixture.RUNTIME_PATHS)
        for name in ('source_only','source_linked_notes','hivemind'):
            dest=Path(self.temp.name)/name
            with contextlib.redirect_stdout(io.StringIO()): fixture.materialize(NS(run=str(self.run),dest=str(dest)))
            self.assertEqual(expected['source_snapshot_sha256'],source_snapshot(dest/'repo',fixture.RUNTIME_PATHS)['source_snapshot_sha256'])
            self.assertEqual(fixture.check(NS(run=str(dest))),1)


if __name__=='__main__':
    unittest.main()
