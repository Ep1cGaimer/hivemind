"""Deterministic harness verification only; these are not model evaluations."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import suite


REFERENCE = {
    'failed_approach': {'cart.py': '''
        from decimal import Decimal
        from catalog import lookup
        def total(db,lines):
            return sum((lookup(db,sku)*qty for sku,qty in lines),Decimal(0))
    '''},
    'build_prerequisite': {'encoder.py': '''
        import json
        from schema_generated import FIELDS
        def encode(values):
            return json.dumps({f['name']:(int if f['type']=='int' else str)(values[f['name']]) for f in FIELDS},separators=(',',':'))
    '''},
    'branch_constraint': {'routes.py': '''
        import json,re
        def path_for(title):
            text=title.casefold()
            if not json.load(open('policy.json'))['allow_unicode']:
                text=text.encode('ascii','ignore').decode('ascii')
            return '/articles/'+slug(text)
        def slug(text):
            return re.sub(r'-+','-', ''.join(c if c.isalnum() else '-' for c in text)).strip('-')
    '''},
    'unfinished_checkpoint': {'reconcile.py': '''
        import csv,json,sys
        def read_stock(path):
            result={}
            with open(path,encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f):
                    key=row['id']; quantity=row['quantity']
                    if not key or key in result or not quantity.isdecimal(): raise ValueError('invalid input')
                    result[key]=int(quantity)
            return result
        def run(before,after):
            a,b=read_stock(before),read_stock(after)
            return [{'id':k,'delta':b.get(k,0)-a.get(k,0)} for k in sorted(a.keys()|b.keys()) if b.get(k,0)!=a.get(k,0)]
        if __name__=='__main__': print(json.dumps(run(*sys.argv[1:])))
    '''},
    'stale_guidance': {'invoice.py': '''
        import json,decimal
        def total(lines):
            mode=getattr(decimal,json.load(open('money_policy.json'))['rounding'])
            return format(sum((decimal.Decimal(v).quantize(decimal.Decimal('.01'),rounding=mode) for v in lines),decimal.Decimal(0)),'.2f')
    '''},
    'conflicting_interpretations': {'quotes.py': '''
        import json
        from decimal import Decimal,ROUND_HALF_UP
        def quote(amount,rate):
            a,r=Decimal(amount),Decimal(rate)
            net,gross=(a,a*(1+r)) if json.load(open('runtime.json'))['tax_mode']=='exclusive' else (a/(1+r),a)
            net,gross=(v.quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for v in (net,gross))
            return {'net':format(net,'.2f'),'tax':format(gross-net,'.2f'),'gross':format(gross,'.2f')}
    ''', 'DECISION.md':'docs/customer.md and docs/finance.md conflict; runtime.json is authoritative.\n'},
    'integration_applicability': {'packets.py': '''
        import hashlib
        from transport import serialize
        def packet(data):
            wire=serialize(data)
            return {'wire_hex':wire.hex(),'sha256':hashlib.sha256(wire).hexdigest()}
    '''},
    'no_history': {'stats.py': '''
        from collections import Counter
        def histogram(values): return dict(Counter(values))
    '''},
}


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fixture-harness-',dir=suite.HERE)
        self.root=Path(self.temp.name)
        self.output=io.StringIO()
        self.quiet=contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None,None,None)
        self.temp.cleanup()

    def setup_case(self,case,variant='default'):
        dest=self.root/(case+'-'+variant)
        suite.prepare(NS(case=case,dest=str(dest)))
        repo=dest/'repo'
        if case!='no_history':
            # This explicit synthetic marker tests transition machinery only.
            # It is not used as evidence of an actual writer or useful finding.
            chosen=next(n for n in suite.fixture(case) if n.endswith('.py'))
            with (repo/chosen).open('a',encoding='utf-8') as f:
                f.write('\n# deterministic harness transition marker\n')
            if case=='failed_approach':
                p=repo/'catalog.py'
                p.write_text(p.read_text().replace('sku LIKE ? ORDER BY price DESC','sku = ?'),encoding='utf-8')
            if case=='build_prerequisite':
                p=repo/'decoder.py'
                p.write_text(p.read_text().replace("str(values[f['name']])", "(int if f['type']=='int' else str)(values[f['name']])"),encoding='utf-8')
            suite.advance(NS(run=str(dest),variant=variant))
        return dest,repo

    def test_all_stubs_fail_and_reference_artifacts_pass(self):
        for case in suite.CASES:
            with self.subTest(case=case):
                dest,repo=self.setup_case(case)
                self.assertNotEqual(suite.check(NS(run=str(dest))),0)
                for name,code in REFERENCE[case].items():
                    suite.write(repo,name,code)
                if case=='build_prerequisite':
                    self.assertNotEqual(suite.check(NS(run=str(dest))),0,'Checker must not build on behalf of consumer')
                    suite.run([suite.sys.executable,'tools/build.py'],repo)
                self.assertEqual(suite.check(NS(run=str(dest))),0,self.output.getvalue())

    def test_wrong_branch_and_preintegration_variants(self):
        for case,variant in [('branch_constraint','main'),('integration_applicability','before')]:
            with self.subTest(case=case):
                dest,repo=self.setup_case(case,variant)
                for name,code in REFERENCE[case].items(): suite.write(repo,name,code)
                self.assertEqual(suite.check(NS(run=str(dest))),0,self.output.getvalue())

    def test_policy_tampering_rejected(self):
        dest,repo=self.setup_case('branch_constraint')
        for name,code in REFERENCE['branch_constraint'].items(): suite.write(repo,name,code)
        suite.write(repo,'policy.json','{"allow_unicode":false}\n')
        self.assertEqual(suite.check(NS(run=str(dest))),1)
        self.assertIn('altered_protected_files',json.loads((dest/'outcome.json').read_text()))

    def test_control_export_and_fresh_materialization(self):
        dest,repo=self.setup_case('integration_applicability')
        finding={'text':'synthetic metadata preservation test, not a model finding','qualifications':['WIP'],
                 'sources':[{'path':'transport.py','commit':'opaque-source-id'}],'revision':'opaque-revision'}
        facts=self.root/'facts.json'; facts.write_text(json.dumps([finding]),encoding='utf-8')
        output=self.root/'notes.json'
        suite.export_control(NS(run=str(dest),findings=str(facts),output=str(output)))
        bundle=json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(bundle['findings_unmodified'],[finding])
        self.assertTrue(any(len(c['parents'])==2 for c in bundle['history']))
        self.assertNotIn('suite.py',bundle['current_sources'])
        self.assertNotIn('EXPECTED_OUTCOMES.json',bundle['current_sources'])
        clone=self.root/'fresh'
        suite.materialize(NS(run=str(dest),dest=str(clone)))
        self.assertEqual(suite.git(repo,'rev-parse','HEAD'),suite.git(clone/'repo','rev-parse','HEAD'))
        self.assertFalse((clone/'repo'/'outcome.json').exists())

    def test_plan_has_balanced_conditions_and_distinct_sessions(self):
        out=self.root/'plan.json'
        suite.plan(NS(seed=1729,output=str(out)))
        rows=json.loads(out.read_text())['runs']
        self.assertEqual(len(rows),72)
        self.assertEqual(len({r['session_id'] for r in rows}),72)
        for case in suite.CASES:
            self.assertEqual(sum(r['case']==case for r in rows),9)


if __name__=='__main__': unittest.main()
