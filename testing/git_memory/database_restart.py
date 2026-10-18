"""Actual owned FalkorDB crash/recreation durability proof, without model calls.

Creates a unique container and named volume, uses real authenticated HTTP and a
real Git fixture, kills only the owned database with SIGKILL, and starts a fresh
service/client. Then recreates the owned container on the same retained volume.
Existing containers, volumes, and graphs are never restarted or removed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hivemind.bridge import LocalBridge, git
from redis import Redis


def main():
    run_id = str(time.time_ns()) + '-' + secrets.token_hex(3)
    run = ROOT / '.local/git-memory/database-restarts' / run_id
    root = run / 'repo'
    root.mkdir(parents=True)
    image = 'falkordb/falkordb:6.0.2'
    original_name = 'hivemind-durability-' + run_id
    recreated_name = original_name + '-recreated'
    volume = original_name + '-data'
    owned_names = {original_name, recreated_name}
    owned_created = set()
    graph = 'hivemind_durability_' + run_id.replace('-', '_')
    report = {'run_id': run_id, 'mode': 'deterministic actual database/service crash proof; no model calls',
              'image': image, 'owned_volume': volume, 'graph': graph, 'stages': []}
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT / 'hivemind').rglob('*') if p.suffix in {'.py', '.mjs'}}
    report['source_head'] = git(ROOT, 'rev-parse', 'HEAD')
    report['source_dirty'] = bool(git(ROOT, 'status', '--porcelain'))
    report['implementation_manifest'] = manifest
    report['implementation_id'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    service = None
    service_logs = []
    password = secrets.token_hex(20)
    service_base = None
    active_token = revoked_token = None

    def save_report():
        (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    def docker(*args, timeout=30):
        completed = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)
        if completed.returncode:
            raise RuntimeError('Owned-container Docker operation failed: ' + ' '.join(args[:2])
                               + ': ' + completed.stderr.strip()[:500])
        return completed.stdout.strip()

    def inspected(name):
        if name not in owned_names:
            raise RuntimeError('Refusing to operate on a container outside this test')
        value = json.loads(docker('inspect', name))[0]
        if value['Config']['Labels'].get('hivemind.test.run') != run_id:
            raise RuntimeError('Owned-container label verification failed')
        return value

    def db_start(name, *, create):
        if create:
            docker('run', '--detach', '--name', name,
                   '--label', 'hivemind.test=database_restart', '--label', 'hivemind.test.run=' + run_id,
                   '--publish', '127.0.0.1::6379',
                   '--mount', 'type=volume,src=' + volume + ',dst=/var/lib/falkordb/data',
                   '--env', 'BROWSER=0', '--env', 'REDIS_ARGS=--appendonly yes --appendfsync always', image)
            owned_created.add(name)
        else:
            inspected(name)
            docker('start', name)
        inspection = inspected(name)
        binding = inspection['NetworkSettings']['Ports']['6379/tcp'][0]
        if binding['HostIp'] != '127.0.0.1':
            raise RuntimeError('Durability fixture must publish only on loopback')
        port = int(binding['HostPort'])
        deadline = time.monotonic() + 30
        while True:
            try:
                client = Redis(host='127.0.0.1', port=port, socket_connect_timeout=1,
                               socket_timeout=2, decode_responses=True)
                if client.ping():
                    break
            except Exception:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Owned database did not become ready within30seconds')
                time.sleep(.1)
        config = {key: client.config_get(key).get(key) for key in ('appendonly', 'appendfsync', 'dir')}
        mounts = [{'type': m['Type'], 'name': m.get('Name'), 'destination': m['Destination']}
                  for m in inspection['Mounts']]
        if config != {'appendonly': 'yes', 'appendfsync': 'always', 'dir': '/var/lib/falkordb/data'}:
            raise RuntimeError('Durability configuration differs from the tested profile')
        if not any(m['name'] == volume and m['destination'] == config['dir'] for m in mounts):
            raise RuntimeError('Actual Redis persistence directory is not the owned mounted volume')
        return port, {'container': name, 'container_id': inspection['Id'], 'image_id': inspection['Image'],
                      'port': port, 'redis_config': config, 'mounts': mounts,
                      'aof_enabled': client.info('persistence')['aof_enabled']}

    def http(path, payload=None, *, token=None, cookie=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if cookie:
            headers['Cookie'] = cookie
        request = Request(service_base + path, data=None if payload is None else json.dumps(payload).encode(),
                          headers=headers, method='GET' if payload is None else 'POST')
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as response:
            return response.code, json.load(response), response.headers
        with response:
            return response.status, json.load(response), response.headers

    def service_start(db_port, stage):
        nonlocal service, service_base
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        env = dict(os.environ)
        env.pop('HIVEMIND_AUTH_SECRET', None)
        env.pop('HIVEMIND_AGENT_TOKEN', None)
        env.update(HIVEMIND_BACKEND='falkordb', FALKORDB_HOST='127.0.0.1', FALKORDB_PORT=str(db_port),
                   FALKORDB_GRAPH=graph, HIVEMIND_USERS='synthetic=' + password)
        out = (run / (stage + '.stdout')).open('w', encoding='utf-8')
        err = (run / (stage + '.stderr')).open('w', encoding='utf-8')
        service_logs.extend([out, err])
        service = subprocess.Popen([sys.executable, '-u', '-m', 'hivemind', '--host', '127.0.0.1', '--port', str(port)],
            cwd=ROOT, env=env, stdout=out, stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        service_base = 'http://127.0.0.1:' + str(port)
        deadline = time.monotonic() + 30
        while True:
            if service.poll() is not None:
                raise RuntimeError('Owned service exited during startup; inspect retained ' + stage + '.stderr')
            try:
                status, health, _ = http('/health')
                if status == 200 and health.get('backend') == 'falkordb':
                    return {'pid': service.pid, 'port': port, 'backend': health['backend']}
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError('Owned service did not become healthy within30seconds')
            time.sleep(.1)

    def service_kill():
        nonlocal service
        if service is not None and service.poll() is None:
            service.kill()
            service.wait(timeout=10)
        service = None

    def db_crash(name, stage):
        inspected(name)
        docker('kill', '--signal', 'KILL', name)
        state = inspected(name)['State']
        if state['Running'] or state['ExitCode'] != 137:
            raise RuntimeError('Expected an actual owned-container SIGKILL exit137')
        (run / (stage + '-database.log')).write_text(docker('logs', name), encoding='utf-8')
        return {'container': name, 'signal': 'SIGKILL', 'exit_code': state['ExitCode'],
                'running': state['Running'], 'save_command_issued': False}

    expected = {}

    def verify_fresh(stage, db_port):
        service_info = service_start(db_port, stage)
        config_path = bridge.directory / 'config.json'
        config = json.loads(config_path.read_text())
        config['url'] = service_base
        config_path.write_text(json.dumps(config, indent=2))
        cold = LocalBridge(root)
        # Direct authenticated HTTP bypasses every local recall cache.
        synchronized = cold.sync(['guide.txt'])
        status, recalled, _ = http('/api/projects/' + project + '/git/recall',
            {'context_id': synchronized['context_id']}, token=active_token)
        checks = {'live_backend': service_info['backend'] == 'falkordb', 'active_token_still_valid': status == 200}
        all_memories = recalled.get('findings', []) + recalled.get('checkpoints', [])
        for kind in ('finding', 'checkpoint'):
            revision = expected[kind]
            checks[kind + '_recalled_exact_id'] = any(m['id'] == revision['id'] for m in all_memories)
            explain_status, explanation, _ = http('/api/projects/' + project + '/git/explain',
                {'context_id': synchronized['context_id'], 'memory_id': revision['id']}, token=active_token)
            checks[kind + '_immutable_record_unchanged'] = explain_status == 200 and explanation.get('memory') == revision
        revoked_status, revoked_response, _ = http('/api/projects/' + project + '/git/recall',
            {'context_id': synchronized['context_id']}, token=revoked_token)
        checks['revocation_survived'] = revoked_status == 401 and revoked_response.get('error', {}).get('code') == 'AUTH_REQUIRED'
        report['stages'].append({'stage': stage, 'service': service_info, 'checks': checks})
        save_report()
        if not all(checks.values()):
            raise AssertionError('Crash durability checks failed for ' + stage)

    try:
        report['image_id'] = docker('image', 'inspect', image, '--format', '{{.Id}}')
        docker('volume', 'create', '--label', 'hivemind.test=database_restart',
               '--label', 'hivemind.test.run=' + run_id, volume)
        db_port, db_info = db_start(original_name, create=True)
        report['initial_database'] = db_info
        report['initial_service'] = service_start(db_port, 'initial-service')
        _, login, headers = http('/api/auth/login', {'username': 'synthetic', 'password': password})
        if not login.get('ok'):
            raise AssertionError('Synthetic human fixture login failed')
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        _, project_response, _ = http('/api/projects', {'name': 'Actual owned database crash proof'}, cookie=cookie)
        project = project_response['project']['id']
        _, active, _ = http('/api/projects/' + project + '/agents', {'label': 'Durable active fixture'}, cookie=cookie)
        _, revoked, _ = http('/api/projects/' + project + '/agents', {'label': 'Durable revoked fixture'}, cookie=cookie)
        active_token, revoked_token = active['token'], revoked['token']
        git(root, 'init', '-b', 'main')
        git(root, 'config', 'user.email', 'durability@example.test')
        git(root, 'config', 'user.name', 'Synthetic durability fixture')
        (root / 'guide.txt').write_text('Verify the reserved queue before release.\n')
        git(root, 'add', '.')
        git(root, 'commit', '-m', 'Independent database crash fixture')
        _, registered, _ = http('/api/projects/' + project + '/git/register',
            {'remote': 'synthetic.invalid/durability-' + run_id, 'root_commit': git(root, 'rev-parse', 'HEAD')}, token=active_token)
        bridge = LocalBridge(root, config={'url': service_base, 'project_id': project, 'repo_id': registered['repo_id'],
                                          'connector_id': 'durability-connector-' + run_id})
        bridge.config_path.write_text(json.dumps(bridge.config, indent=2))
        (bridge.directory / 'token').write_text(active_token)
        (bridge.directory / 'token').chmod(0o600)
        for kind, title, body in [('finding', 'Durable release prerequisite', 'Verify the reserved queue before release.'),
                                  ('checkpoint', 'Durable unfinished task', 'Next: validate queue behavior before releasing.')]:
            response = bridge.call(kind, {'title': title, 'body': body, 'paths': ['guide.txt'],
                                          'event_id': 'acknowledged-' + kind})
            if not response.get('ok') or response.get('queued'):
                raise AssertionError('Initial memory was not acknowledged by the live service')
            expected[kind] = response['memory']
        _, revocation, _ = http('/api/projects/' + project + '/agents/' + revoked['agent']['token_id'], {}, cookie=cookie)
        if not revocation.get('revoked'):
            raise AssertionError('Revocation was not acknowledged before the crash')
        report.update(project_id=project, repo_id=registered['repo_id'],
                      acknowledged_revision_ids={kind: value['id'] for kind, value in expected.items()},
                      revoked_token_id=revoked['agent']['token_id'])
        save_report()

        report['first_crash'] = db_crash(original_name, 'first-crash')
        service_kill()
        db_port, report['same_container_restart'] = db_start(original_name, create=False)
        verify_fresh('fresh-service-after-sigkill', db_port)

        report['second_crash'] = db_crash(original_name, 'second-crash')
        service_kill()
        inspected(original_name)
        docker('rm', original_name)
        owned_created.remove(original_name)
        db_port, report['recreated_database'] = db_start(recreated_name, create=True)
        verify_fresh('fresh-service-after-volume-reattach', db_port)
        report['passed'] = True
    except Exception as exc:
        report.update(passed=False, error_type=type(exc).__name__, error=str(exc))
    finally:
        service_kill()
        for name in sorted(owned_created):
            try:
                info = inspected(name)
                if info['State']['Running']:
                    docker('stop', '--time', '3', name)
                report.setdefault('cleanup', []).append({'container': name, 'stopped': not inspected(name)['State']['Running']})
                (run / (name + '.database.log')).write_text(docker('logs', name), encoding='utf-8')
            except Exception as exc:
                report.setdefault('cleanup_errors', []).append(str(exc))
        for stream in service_logs:
            stream.close()
        report['volume_retained'] = True
        current = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (ROOT / 'hivemind').rglob('*') if p.suffix in {'.py', '.mjs'}}
        report['implementation_unchanged'] = manifest == current
        save_report()
        print(json.dumps({'passed': report.get('passed'), 'implementation_unchanged': report['implementation_unchanged'],
                          'artifact_directory': str(run), 'owned_volume': volume,
                          'checks': [stage['checks'] for stage in report['stages']],
                          'error': report.get('error')}, indent=2))
    return 0 if report.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
