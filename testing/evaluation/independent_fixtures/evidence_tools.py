"""Test-only full-memory control export and conservative writer-evidence audits.

This module neither imports HiveMind nor calls a provider/service. Inputs must be
actual evaluator-recorded inventories and native OpenCode tool events. Never
mount this evaluator or its private probes into a tested assistant workspace.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SECRET_KEYS = frozenset({
    'token', 'agent_token', 'access_token', 'refresh_token', 'authorization',
    'password', 'secret', 'api_key', 'apikey', 'client_secret', 'credential',
    'credentials', 'private_key', 'cookie', 'set-cookie',
})
CONTENT_KEYS = frozenset({'body', 'text', 'content', 'raw_content', 'excerpt', 'title'})
SAFE_FILTERS = frozenset({'project_id', 'workspace_project_id', 'repo_id', 'tenant_id'})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')


def validate_inventory(payload):
    """Reject a recall response or an incomplete/current-only inventory."""
    if not isinstance(payload, dict) or not isinstance(payload.get('records'), list):
        raise ValueError('Expected full inventory records[], not recall findings/checkpoints')
    info = payload.get('inventory', {})
    if info.get('complete') is not True or info.get('all_kinds') is not True:
        raise ValueError('Inventory must declare complete=true and all_kinds=true after pagination')
    if not isinstance(info.get('filters', {}), dict) or set(info.get('filters', {})) - SAFE_FILTERS:
        raise ValueError('Only project/repository/tenant scope filters are allowed; no applicability filters')
    if not isinstance(payload.get('links'), list):
        raise ValueError('Full scoped relationship inventory links[] is required')
    ids = set()
    for record in payload['records']:
        if not isinstance(record, dict) or not record.get('id') or not record.get('kind'):
            raise ValueError('Each full GitRecord needs id and kind')
        if record['id'] in ids:
            raise ValueError('Duplicate record ID: resolve pagination overlap without losing revisions')
        ids.add(record['id'])
    for link in payload['links']:
        if not isinstance(link, dict):
            raise ValueError('Normalize links to {edge_type,from_id,to_id,properties}')
        if not all(link.get(k) for k in ('edge_type', 'from_id', 'to_id')):
            raise ValueError('Incomplete relationship record')
        if link['from_id'] not in ids or link['to_id'] not in ids:
            raise ValueError('Relationship endpoint absent: full related-record inventory is incomplete')
    return info


class Sanitizer:
    """Preserve all nonprivate fields; never rank, merge, summarize or qualify."""
    def __init__(self, policy=None):
        policy = policy or {}
        self.secret_values = list(dict.fromkeys(policy.get('secret_values', [])))
        if any(not isinstance(v, str) or len(v) < 6 for v in self.secret_values):
            raise ValueError('Explicit secret values must be strings of at least six characters')
        self.private_prefixes = [str(p).replace('\\', '/').rstrip('/') for p in policy.get('private_prefixes', [])]
        if any(not p or p in ('.', '/') for p in self.private_prefixes):
            raise ValueError('Private prefixes must name specific paths')
        self.redactions = []

    def private(self, text):
        normalized = text.replace('\\', '/')
        return any(normalized == p or normalized.startswith(p + '/') for p in self.private_prefixes)

    def redact(self, pointer, reason, replacement='<redacted>'):
        self.redactions.append({'pointer': pointer, 'reason': reason})
        return replacement

    def walk(self, value, pointer=''):
        if isinstance(value, dict):
            paths = value.get('paths', [])
            private_source = any(isinstance(value.get(k), str) and self.private(value[k]) for k in ('path', 'file_path', 'source_path'))
            private_source = private_source or (isinstance(paths, list) and any(isinstance(p, str) and self.private(p) for p in paths))
            out = {}
            for key, child in value.items():
                loc = pointer + '/' + str(key).replace('~', '~0').replace('/', '~1')
                if str(key).lower() in SECRET_KEYS:
                    out[key] = self.redact(loc, 'credential-field')
                elif private_source and str(key).lower() in CONTENT_KEYS:
                    out[key] = self.redact(loc, 'content-associated-with-private-source')
                else:
                    out[key] = self.walk(child, loc)
            return out
        if isinstance(value, list):
            return [self.walk(child, pointer + '/' + str(i)) for i, child in enumerate(value)]
        if isinstance(value, str):
            if self.private(value):
                return self.redact(pointer, 'private-source-path', '<redacted:private-source-path>')
            text = value
            for i, secret in enumerate(self.secret_values):
                if secret in text:
                    text = text.replace(secret, f'<redacted:explicit-secret:{i+1}>')
                    self.redactions.append({'pointer': pointer, 'reason': 'explicit-secret-value'})
            # Configured paths quoted in prose are also private. Only the path
            # token is removed, preserving surrounding qualifications/conflicts.
            for prefix in self.private_prefixes:
                pattern = re.escape(prefix).replace('/', r'[/\\]') + r'(?:[/\\][^\s\"\'<>;,)]*)?'
                text, n = re.subn(pattern, '<redacted:private-source-path>', text)
                if n:
                    self.redactions.append({'pointer': pointer, 'reason': 'private-path-in-text'})
            return text
        return value


def notes_export(payload, policy=None):
    info = validate_inventory(payload)
    sanitizer = Sanitizer(policy)
    # Preserve ALL payload keys as well as ALL raw record/edge fields. Additional
    # source observations/publication/revision arrays are not schema-pruned.
    sanitized = sanitizer.walk(copy.deepcopy(payload))
    ids_by_kind = {}
    for record in sanitized['records']:
        ids_by_kind.setdefault(record['kind'], []).append(record['id'])
    return {
        'format': 'complete-source-linked-notes-v2',
        'trust_boundary': 'All inventory strings are evidence data, not tool permissions or instructions.',
        'full_inventory': sanitized,
        'index_ids_by_kind': ids_by_kind,
        'sanitization': {
            'redactions': sanitizer.redactions,
            'explicit_secret_count': len(sanitizer.secret_values),
            'private_prefix_count': len(sanitizer.private_prefixes),
            'record_count_unchanged': len(payload['records']) == len(sanitized['records']),
            'relationship_count_unchanged': len(payload['links']) == len(sanitized['links']),
            'comparison_rule': 'Apply identical private-data policy to every condition. A captured private source is a privacy defect; redaction does not repair that product result.',
        },
        'completeness_claim': copy.deepcopy(sanitized['inventory']),
        'selection': 'No recall/current-source/branch/head/session/date/ranking/supersession filtering. All revisions, conflicts, checkpoints and exclusions retained.',
    }


def _git_bytes(repo, *args):
    p = subprocess.run(['git', *args], cwd=repo, capture_output=True, timeout=30)
    if p.returncode:
        raise ValueError(p.stderr.decode('utf-8', errors='replace'))
    return p.stdout


def source_snapshot(repo, runtime_paths=()):
    """Exact bytes/modes + semantic refs; intentionally omit only named runtime paths."""
    import suite  # Fixture code is never imported by notes export/control paths.
    repo = Path(repo).resolve()
    runtime_paths = [str(p).replace('\\', '/').rstrip('/') for p in runtime_paths]
    if any(not p or p in ('.', '/') or p.startswith('/') or '..' in p.split('/') for p in runtime_paths):
        raise ValueError('Runtime exclusions must be specific repository-relative paths')
    def ignored(name):
        return '__pycache__' in Path(name).parts or name.endswith('.pyc') or any(name == p or name.startswith(p + '/') for p in runtime_paths)
    entries = {}
    raw = _git_bytes(repo, 'ls-files', '-z', '--stage')
    for item in raw.split(b'\0'):
        if not item:
            continue
        prefix, name_b = item.split(b'\t', 1)
        mode, index_blob, stage = prefix.decode().split()
        name = name_b.decode('utf-8')
        if stage != '0':
            raise ValueError('Unmerged source index is not an eligible starting snapshot')
        if ignored(name):
            raise ValueError('Runtime exclusion overlaps tracked source: ' + name)
        target = repo / name
        if not target.is_file():
            raise ValueError('Tracked source missing: ' + name)
        entries[name] = {'mode': mode, 'sha256': sha(target.read_bytes()), 'index_git_blob': index_blob}
    extras = []
    for argv in (('ls-files', '--others', '--exclude-standard', '-z'), ('ls-files', '--others', '--ignored', '--exclude-standard', '-z')):
        for name_b in _git_bytes(repo, *argv).split(b'\0'):
            if name_b:
                name = name_b.decode('utf-8')
                if not ignored(name):
                    target = repo / name
                    if target.is_file():
                        extras.append({'path': name, 'sha256': sha(target.read_bytes())})
    refs = {}
    for line in suite.git(repo, 'for-each-ref', '--format=%(refname) %(objectname)').splitlines():
        ref, value = line.split()
        if ref.startswith('refs/heads/'):
            refs[ref[len('refs/heads/'):]] = value
        elif ref.startswith('refs/remotes/origin/') and not ref.endswith('/HEAD'):
            refs.setdefault(ref[len('refs/remotes/origin/'):], value)
    semantic = {'head': suite.git(repo, 'rev-parse', 'HEAD'),
                'branch': suite.git(repo, 'branch', '--show-current'),
                'files': entries, 'other_source_files': sorted(extras, key=lambda e: e['path']),
                'branch_tips': refs, 'reachable_commits': sorted(suite.git(repo, 'rev-list', '--all').splitlines())}
    content = {'files': {name: {key: value for key, value in metadata.items() if key != 'index_git_blob'} for name, metadata in entries.items()},
               'other_source_files': semantic['other_source_files']}
    return {'format': 'fair-starting-source-v1', 'semantic': semantic,
            'source_snapshot_sha256': sha(json.dumps(semantic, sort_keys=True, separators=(',', ':')).encode()),
            'working_content_sha256': sha(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()),
            'runtime_exclusions': runtime_paths,
            'limitations': 'Runtime configuration/model/provider/budget equality and memory scope are separately audited; this digest proves only declared source equality.'}


def native_tools(paths, receipt_paths=()):
    tools, sessions, files = [], set(), []
    receipts = {}
    for path in receipt_paths:
        raw = Path(path).read_bytes()
        files.append({'file': str(Path(path).resolve()), 'sha256': sha(raw), 'kind': 'external_execution_receipt'})
        for lineno, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
            if not line.strip():
                continue
            receipt = json.loads(line)
            event, result = receipt.get('event', {}), receipt.get('result')
            if not isinstance(result, dict) or not event.get('session') or not event.get('call_id'):
                raise ValueError('External execution receipt lacks event/session/call_id/result')
            key = (event['session'], event['call_id'])
            normalized = {'event': event, 'result': result, 'file': str(Path(path).resolve()), 'line': lineno}
            if key in receipts and (receipts[key]['event'] != event or receipts[key]['result'] != result):
                raise ValueError('Conflicting independent execution receipts for the same actual call')
            receipts[key] = normalized
    for path in paths:
        raw = Path(path).read_bytes()
        files.append({'file': str(Path(path).resolve()), 'sha256': sha(raw), 'kind': 'native_log'})
        for lineno, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get('sessionID'):
                sessions.add(event['sessionID'])
            if event.get('type') != 'tool_use':
                continue
            part, state = event.get('part', {}), event.get('part', {}).get('state', {})
            if state.get('status') != 'completed':
                continue
            metadata = state.get('metadata', {})
            exit_code = next((v for v in [metadata.get('exit'), metadata.get('exit_code'), metadata.get('exitCode'), state.get('exit_code')] if isinstance(v, int) and not isinstance(v, bool)), None)
            data = state.get('input', {})
            command = data.get('command', '') if isinstance(data, dict) else ''
            output, structured, receipt_match, receipt_ref = state.get('output', ''), None, None, None
            if part.get('tool') == 'fixture_python':
                try:
                    structured = json.loads(output) if isinstance(output, str) else output
                except (ValueError, TypeError):
                    structured = None
                if isinstance(structured, dict) and isinstance(structured.get('exit_code'), int) and not isinstance(structured['exit_code'], bool):
                    exit_code = structured['exit_code']
                    output = str(structured.get('stdout', '')) + str(structured.get('stderr', ''))
                else:
                    exit_code = None
                command = 'python ' + str(data.get('file', '<inline>')) + '\n' + str(data.get('code', '')) + '\n' + ' '.join(str(v) for v in data.get('args', []))
                if receipt_paths:
                    match = receipts.get((event.get('sessionID'), part.get('id')))
                    receipt_match = bool(match and match['event'].get('tool') == part.get('tool') and
                                         match['event'].get('args') == data and match['result'] == structured)
                    if receipt_match:
                        receipt_ref = {'file': match['file'], 'line': match['line']}
                    else:
                        exit_code = None
            tools.append({'session': event.get('sessionID'), 'tool': part.get('tool'),
                          'part_id': part.get('id'), 'input': data, 'command': command,
                          'output': output, 'exit_code': exit_code,
                          'external_receipt_match': receipt_match, 'external_receipt': receipt_ref,
                          'structured_execution_result': structured,
                          'time': state.get('time', {}), 'file': str(Path(path).resolve()), 'line': lineno})
    return tools, sessions, files


WRITER_PROBES = {
    'failed_approach': "from decimal import Decimal\nfrom catalog import connect,lookup\ndb=connect()\nassert lookup(db,'A_1')==Decimal('3.20')\nassert lookup(db,'B%2')==Decimal('4.50')\n",
    'build_prerequisite': "from decoder import decode\nassert decode('{\"code\":123,\"units\":\"7\"}')=={'code':'123','units':7}\n",
    'branch_constraint': "from slug import slug\nassert slug('  CAFÉ / Straße --猫  ')=='café-strasse-猫'\n",
    'unfinished_checkpoint': "from reconcile import read_stock\nassert read_stock('before.csv')=={'A':4,'B':2}\n",
    'stale_guidance': "from display import display_amount\nassert display_amount('1.005')=='1.01'\nassert display_amount('-1.005')=='-1.01'\n",
    'conflicting_interpretations': "from preview import preview\nassert preview('100','.20')=={'net':'100.00','tax':'20.00','gross':'120.00'}\n",
    'integration_applicability': "import hashlib\nfrom digest import digest\nfrom transport import serialize,VERSION\nassert VERSION==2\nassert digest({'x':'猫'})==hashlib.sha256(serialize({'x':'猫'})).hexdigest()\n",
}


def writer_artifacts(repo, state):
    import suite
    event = next((e for e in reversed(state['events']) if e.get('event') == 'writer_frozen'), None)
    if not event:
        return {'passed': False, 'reason': 'No frozen actual writer source recorded'}
    tip, case = event['commit'], state['case']
    authority = ['CONTRACT.md'] + {
        'branch_constraint': ['policy.json'], 'stale_guidance': ['money_policy.json'],
        'build_prerequisite': ['fields.json', 'tools/build.py'],
        'conflicting_interpretations': ['runtime.json', 'docs/customer.md', 'docs/finance.md'],
        'integration_applicability': ['transport.py'],
    }.get(case, [])
    altered = [name for name in authority if _git_bytes(repo, 'show', f'{tip}:{name}') != _git_bytes(repo, 'show', f"{state['writer_start']}:{name}")]
    if altered:
        return {'passed': False, 'writer_commit': tip, 'reason': 'Writer changed source authority or requirements', 'altered_files': altered}
    with tempfile.TemporaryDirectory(prefix='independent-writer-probe-', dir=suite.HERE) as td:
        root = Path(td)
        for name in suite.git(repo, 'ls-tree', '-r', '--name-only', tip).splitlines():
            target = root / name
            if root not in target.resolve().parents:
                raise ValueError('Unsafe source path in fixture tree')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_git_bytes(repo, 'show', f'{tip}:{name}'))
        # Evaluator setup permits testing the frozen decoder semantics. This is
        # expressly NOT evidence that the writer discovered or ran the build.
        setup = None
        if case == 'build_prerequisite':
            setup = suite.run([sys.executable, 'tools/build.py'], root, check=False).returncode
        try:
            p = suite.run([sys.executable, '-c', WRITER_PROBES[case]], root, check=False)
            result = {'passed': p.returncode == 0, 'returncode': p.returncode,
                      'stdout': p.stdout, 'stderr': p.stderr, 'writer_commit': tip}
        except subprocess.TimeoutExpired:
            result = {'passed': False, 'reason': 'Frozen writer artifact probe timed out', 'writer_commit': tip}
        if setup is not None:
            result['evaluator_build_setup_returncode'] = setup
        if case == 'unfinished_checkpoint':
            try:
                full = suite.run([sys.executable, '-c', suite.clean(suite.PROBES[case])], root, check=False)
                result['full_consumer_outcome_passed'] = full.returncode == 0
                result['full_consumer_outcome_stderr'] = full.stderr
            except subprocess.TimeoutExpired:
                result['full_consumer_outcome_passed'] = False
                result['full_consumer_outcome_stderr'] = 'timeout'
            before = _git_bytes(repo, 'show', f"{state['writer_start']}:reconcile.py").decode('utf-8')
            after = (root / 'reconcile.py').read_text(encoding='utf-8')
            result['meaningful_ast_change'] = ast.dump(ast.parse(before), include_attributes=False) != ast.dump(ast.parse(after), include_attributes=False)
        return result


def writer_audit(run_dir, logs, inventory, receipt=None, execution_receipts=()):
    import suite
    validate_inventory(inventory)
    run_dir = Path(run_dir).resolve()
    state = load(run_dir / 'state.json')
    case, repo = state['case'], run_dir / 'repo'
    tools, sessions, log_files = native_tools(logs, execution_receipts)
    checks, evidence = {}, {}
    memories = [r for r in inventory['records'] if r.get('kind') in ('finding', 'checkpoint')]
    writer_memories = [r for r in memories if r.get('session') in sessions]
    if case == 'no_history':
        checks['no_writer_log_or_session'] = not logs and not sessions
        checks['no_historical_findings_or_checkpoints'] = not memories
        return {'case': case, 'status': 'passed' if all(checks.values()) else 'failed',
                'checks': checks, 'scope': 'Negative-case starting-history eligibility only; consumer correctness/overhead separate'}
    checks['actual_native_session_ids_present'] = bool(sessions)
    checks['writer_memory_records_present'] = bool(writer_memories)
    artifact = writer_artifacts(repo, state)
    checks['frozen_writer_functional_probe'] = artifact['passed']
    evidence['writer_artifact_probe'] = artifact
    evidence['writer_session_ids'] = sorted(sessions)
    evidence['writer_memory_ids'] = [r['id'] for r in writer_memories]
    evidence['log_files'] = log_files
    def matching(label, predicate):
        selected = [t for t in tools if predicate(t)]
        evidence[label] = [{k: t[k] for k in ('session', 'part_id', 'tool', 'file', 'line', 'exit_code', 'time', 'external_receipt_match', 'external_receipt')} for t in selected]
        checks[label] = bool(selected)
        return selected
    def successful(t):
        return executed(t) and t['exit_code'] == 0
    def executed(t):
        if t['tool'] == 'fixture_python':
            return isinstance(t.get('structured_execution_result'), dict) and t.get('external_receipt_match') is not False
        return t['tool'] in {'bash', 'shell', 'powershell', 'terminal', 'exec', 'exec_command'} and isinstance(t['command'], str) and re.search(r'\b(?:python(?:3(?:\.\d+)?)?|py|pytest)(?:\.exe)?\b', t['command'], re.I) is not None
    def validates(t, tokens):
        return successful(t) and any(tok in t['command'] for tok in tokens)
    def memory_mentions(path):
        # Path may be in a related source node rather than embedded in finding.
        by_id = {r['id']: r for r in inventory['records']}
        for record in writer_memories:
            related = []
            for link in inventory['links']:
                if link['from_id'] == record['id'] and link['edge_type'] == 'SUPPORTED_BY':
                    related.append(by_id[link['to_id']])
            for source in record.get('data', {}).get('sources', []):
                if isinstance(source, dict) and any(source.get(k) for k in ('id', 'source_id', 'git_blob', 'clean_hash', 'content_hash', 'blob_hash')):
                    related.append(source)
                elif isinstance(source, str) and source in by_id:
                    related.append(by_id[source])
            if path in json.dumps(related, ensure_ascii=False):
                return True
        return False
    manual_review = []
    if case == 'failed_approach':
        def wrong_lookup(t):
            if not executed(t):
                return False
            command, output = t['command'], str(t['output'])
            direct_wrong = ('demo.py' in command or ('lookup' in command and 'A_1' in command)) and re.fullmatch(r'\s*99\.00\s*', output) is not None
            demonstrated_like_collision = 'LIKE' in command and 'sqlite3' in command and re.search(r"['\"]A_1['\"]\s*->[^\n]*\('AX1',\s*'99\.00'\)", output) is not None
            failing_assertion = t['exit_code'] is not None and t['exit_code'] != 0 and 'AssertionError' in output and all(v in command for v in ('lookup', 'A_1', '3.20'))
            return direct_wrong or demonstrated_like_collision or failing_assertion
        bad = matching('observed_wrong_lookup_output', wrong_lookup)
        good = matching('actual_lookup_validation_exit_zero', lambda t: validates(t, ('lookup', 'test_catalog', 'test_lookup')) or (successful(t) and 'demo.py' in t['command'] and re.fullmatch(r'\s*3\.20\s*', str(t['output'])) is not None))
        checks['bad_observation_precedes_successful_validation'] = bool(bad and good and tools.index(bad[0]) < tools.index(good[-1]))
        checks['source_linked_lookup_finding'] = memory_mentions('catalog.py')
        manual_review.append('Finding explains the actually observed failed exact-ID approach, not merely the final fixed API.')
    elif case == 'build_prerequisite':
        missing = matching('actual_missing_schema_import', lambda t: executed(t) and 'schema_generated' in str(t['output']) and 'ModuleNotFoundError' in str(t['output']))
        built = matching('actual_build_exit_zero', lambda t: successful(t) and re.search(r'tools[/\\]build\.py', t['command']) is not None and 'schema generated' in str(t['output']))
        valid = matching('actual_decoder_validation_exit_zero', lambda t: validates(t, ('decode', 'demo.py', 'test_decoder')))
        checks['failure_build_validation_order'] = bool(missing and built and valid and tools.index(missing[0]) < tools.index(built[-1]) < tools.index(valid[-1]))
        checks['source_linked_build_finding'] = memory_mentions('tools/build.py') or memory_mentions('decoder.py')
        manual_review.append('Finding records the discovered clean-checkout build prerequisite and its validation, with agent-report/evidence qualification intact.')
    elif case == 'branch_constraint':
        matching('actual_slug_validation_exit_zero', lambda t: validates(t, ('slug',)))
        checks['source_linked_branch_policy_finding'] = memory_mentions('policy.json')
        writer_tip = artifact.get('writer_commit', state['writer_start'])
        checks['writer_unicode_policy'] = json.loads(_git_bytes(repo, 'show', f'{writer_tip}:policy.json'))['allow_unicode'] is True
        manual_review.append('Finding retains partner branch identity and Unicode qualification; main must not silently inherit it.')
    elif case == 'unfinished_checkpoint':
        checkpoints = [r for r in writer_memories if r['kind'] == 'checkpoint']
        checks['separate_checkpoint_record'] = bool(checkpoints)
        checks['writer_partial_not_finished'] = artifact.get('full_consumer_outcome_passed') is False
        checks['meaningful_source_change'] = artifact.get('meaningful_ast_change') is True
        stop = (receipt or {}).get('checkpoint_stop', {})
        checks['predeclared_stop_recorded'] = bool(stop.get('rule') and stop.get('declared_before_writer') is True and stop.get('actual_stop_event_part_id'))
        checks['stop_event_in_actual_logs'] = any(t['part_id'] == stop.get('actual_stop_event_part_id') for t in tools)
        checks['frozen_snapshot_matches_stop_receipt'] = stop.get('writer_frozen_commit') == artifact.get('writer_commit') and bool(artifact.get('writer_commit'))
        checks['no_source_change_during_capture_declared'] = stop.get('source_digest_before_capture') == stop.get('source_digest_after_capture') and bool(stop.get('source_digest_before_capture'))
        manual_review.append('Separate checkpoint names concrete completed work, remaining work, open questions and executable next steps, matching the interrupted snapshot.')
    elif case == 'stale_guidance':
        matching('actual_display_validation_exit_zero', lambda t: validates(t, ('display',)))
        checks['source_linked_old_money_policy'] = memory_mentions('money_policy.json')
        checks['consumer_policy_changed_to_half_even'] = json.loads(_git_bytes(repo, 'show', f"{state['consumer_start']}:money_policy.json"))['rounding'] == 'ROUND_HALF_EVEN'
        manual_review.append('Finding retains its old half-up source binding and is not rewritten as current half-even knowledge.')
    elif case == 'conflicting_interpretations':
        checks['two_distinct_writer_sessions'] = len({r.get('session') for r in writer_memories}) >= 2
        checks['customer_guide_source_retained'] = memory_mentions('docs/customer.md')
        checks['finance_guide_source_retained'] = memory_mentions('docs/finance.md')
        matching('actual_preview_validation_exit_zero', lambda t: validates(t, ('preview',)))
        manual_review.append('Two actual independently captured stakeholder interpretations remain visible with incompatible tax meanings and their qualifications; resolution follows runtime authority, not timestamp.')
    elif case == 'integration_applicability':
        matching('actual_digest_validation_exit_zero', lambda t: validates(t, ('digest',)))
        checks['source_linked_transport_finding'] = memory_mentions('transport.py')
        tip = artifact.get('writer_commit')
        consumer = state.get('consumer_start')
        integrated = bool(tip and consumer and suite.run(['git', 'merge-base', '--is-ancestor', tip, consumer], repo, check=False).returncode == 0)
        if state.get('variant') == 'before':
            checks['feature_not_integrated_before_consumer'] = not integrated
        else:
            checks['feature_integrated_before_consumer'] = integrated
            checks['real_merge_commit'] = len(suite.git(repo, 'show', '-s', '--format=%P', consumer).split()) == 2
        manual_review.append('Actual saved transport guidance has the original branch/source/observation identity; before/after applicability and graph path need separate live checks.')
    review = (receipt or {}).get('independent_review', {})
    review_ids = set(review.get('record_ids', []))
    reviewed = (review.get('kind') == 'independent_simulated_review' and
                review.get('reviewer_id') and review.get('reviewer_id') not in sessions and
                review.get('all_listed_questions_satisfied') is True and
                set(evidence['writer_memory_ids']).issubset(review_ids))
    checks['independent_semantic_review_recorded'] = bool(reviewed)
    return {'case': case, 'status': 'passed' if all(checks.values()) else 'untested',
            'mechanical_status': 'passed' if all(v for k, v in checks.items() if k != 'independent_semantic_review_recorded') else 'unestablished',
            'checks': checks, 'evidence': evidence, 'independent_review_questions': manual_review,
            'limits': 'Missing evidence remains unestablished. Keyword/command anchors are not proof of reasoning or authenticity. Shell completion without a recorded exit code never establishes success. Log/backend authenticity and log completeness are native-runner responsibilities. No history is fabricated or inferred from final correctness.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('notes'); q.add_argument('--input', required=True); q.add_argument('--output', required=True); q.add_argument('--policy')
    q = sub.add_parser('snapshot'); q.add_argument('--repo', required=True); q.add_argument('--output', required=True); q.add_argument('--runtime-path', action='append', default=[])
    q = sub.add_parser('audit-writer'); q.add_argument('--run', required=True); q.add_argument('--log', action='append', default=[]); q.add_argument('--inventory', required=True); q.add_argument('--receipt'); q.add_argument('--execution-receipt', action='append', default=[]); q.add_argument('--output', required=True)
    args = p.parse_args()
    try:
        if args.command == 'notes':
            payload = load(args.input)
            result = notes_export(payload, load(args.policy) if args.policy else None)
            result['input_file_sha256'] = sha(Path(args.input).read_bytes())
        elif args.command == 'snapshot':
            result = source_snapshot(args.repo, args.runtime_path)
        else:
            result = writer_audit(args.run, args.log, load(args.inventory), load(args.receipt) if args.receipt else None, args.execution_receipt)
        save(args.output, result)
        print(json.dumps({'output': str(Path(args.output).resolve()), 'format': result.get('format'), 'status': result.get('status', 'exported')}))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'error', 'error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
