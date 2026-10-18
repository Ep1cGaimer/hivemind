"""Own a native OpenCode host until its bounded memory pass finishes.

No permission overrides, proxy model, or transcript storage. The same native
session/model selects memories through the installed project plugin.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

from .opencode_adapter import executable, handle


class OpenCodeHost:
    def __init__(self, bridge, *, env=None, model=None):
        if model is not None and ('/' not in model or not all(model.split('/', 1))):
            raise ValueError('Select the native model as provider/model, for example opencode/deepseek-v4.1-flash-free')
        self.bridge, self.model = bridge, model
        self.program = executable()
        if not self.program:
            raise ValueError('Install OpenCode 2, then connect --client opencode before launching')
        self.env = dict(os.environ if env is None else env)
        self.host_id = secrets.token_hex(16)
        self.env['HIVEMIND_OPENCODE_HOST_ID'] = self.host_id
        self.env['OPENCODE_PASSWORD'] = secrets.token_urlsafe(32)
        self.process = None
        self.log = None
        self.manifest = bridge.directory / ('opencode-host-' + self.host_id + '.json')

    def api(self, operation, data=None, *, params=()):
        command = [self.program, 'api', operation, '--server', self.address]
        if data is not None:
            command += ['--data', json.dumps(data)]
        for key, value in params:
            command += ['--param', key + '=' + value]
        result = subprocess.run(command, cwd=self.bridge.root, env=self.env, capture_output=True,
                                encoding='utf-8', errors='replace', timeout=10)
        if result.returncode:
            raise ValueError('OpenCode API failed for ' + operation + '; inspect native client diagnostics')
        return json.loads(result.stdout)

    def __enter__(self):
        if not (self.bridge.root / '.opencode/plugins/hivemind.js').is_file():
            raise ValueError('Connect this repository with --client opencode before launching')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.address = 'http://127.0.0.1:' + str(self.port)
        self.log = (self.bridge.directory / ('opencode-host-' + self.host_id + '.stderr')).open('w', encoding='utf-8')
        try:
            self.process = subprocess.Popen([self.program, 'serve', '--hostname', '127.0.0.1', '--port', str(self.port)],
                cwd=self.bridge.root, env=self.env, stdout=subprocess.DEVNULL, stderr=self.log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self._record(False)
            deadline = time.monotonic() + 15
            while True:
                if self.process.poll() is not None:
                    raise ValueError('OpenCode host exited during startup; inspect its Git-private stderr log')
                try:
                    with urlopen(self.address, timeout=1):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ValueError('OpenCode host did not start within 15 seconds; check local ports and client installation')
                    time.sleep(.1)
            self.wait_for_model()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def wait_for_model(self):
        deadline, attempts = time.monotonic() + 20, []
        while True:
            models = self.api('model.list').get('data', [])
            present = bool(models)
            if self.model:
                provider, selected = self.model.split('/', 1)
                present = any(m.get('providerID') == provider and (m.get('id') in {selected, self.model}
                    or m.get('modelID') == selected) for m in models)
            attempts.append({'selected_present': present})
            self.bridge.set('opencode_catalog_readiness', attempts)
            if present:
                return
            if time.monotonic() >= deadline:
                raise ValueError('Selected model is absent from the native OpenCode catalog. Refresh OpenCode models or select an available model.')
            time.sleep(.25)

    def states(self):
        with self.bridge.db() as db:
            rows = db.execute("SELECT key,value FROM state WHERE key LIKE 'opencode:%'").fetchall()
        result = []
        for key, raw in rows:
            value = json.loads(raw)
            if isinstance(value, dict) and value.get('host_id') == self.host_id:
                result.append((key.removeprefix('opencode:'), value))
        return result

    def drain(self, timeout=60):
        """Only this host's sessions; one atomically claimed continuation each."""
        deadline = time.monotonic() + timeout
        notified = False
        while True:
            states = self.states()
            pending = [(session, state) for session, state in states
                       if self.unfinished(session, state)]
            if not pending:
                if not states:
                    raise ValueError('HiveMind received no native prompt event. Reconnect --client opencode and inspect plugin startup errors.')
                failures = [session for session, _ in states if self.bridge.get('capture_status:' + session) == 'failed']
                if failures:
                    raise ValueError('HiveMind capture failed. Ordinary task output is retained; inspect bridge status and retry the failed save.')
                return
            if not notified:
                print('HiveMind: finishing the automatic memory pass...', file=sys.stderr, flush=True)
                notified = True
            for session, state in pending:
                if not state.get('continuation_requested'):
                    decision = handle(self.bridge, {'type': 'complete', 'session': session, 'turn': state['turn'],
                                                   'event_id': 'launcher:' + state['turn'], 'check_only': True})
                    if decision.get('continue'):
                        try:
                            self.api('session.synthetic', {'text': decision['instruction'],
                                'description': 'HiveMind automatic memory pass', 'metadata': {'hivemindContinuation': True},
                                'delivery': 'queue', 'resume': True}, params=[('sessionID', session)])
                        except Exception:
                            self.fail_pending('HiveMind could not start its one capture pass. Inspect native client diagnostics and retry the save in a new turn.')
                            raise
            if time.monotonic() >= deadline:
                warning = 'HiveMind capture timed out after one bounded pass. Inspect bridge status; no additional pass was started.'
                self.fail_pending(warning)
                raise ValueError(warning)
            time.sleep(.2)

    def fail_pending(self, warning):
        # Update only sessions this host owns, atomically with the pending check.
        with self.bridge.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for session, state in self.states():
                key = 'capture_status:' + session
                row = db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
                if row is None or self.unfinished(session, state):
                    db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (key, json.dumps('failed')))
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?)', ('capture_warning', json.dumps(warning)))

    def unfinished(self, session, state):
        status = self.bridge.get('capture_status:' + session, 'pending')
        if status == 'failed':
            return False
        return (status == 'pending' or not state.get('completion_observed') or
                bool(state.get('continuation_requested') and not state.get('capture_pass_finished')))

    def _record(self, stopped):
        self.manifest.write_text(json.dumps({'pid': self.process.pid, 'port': self.port, 'host_id': self.host_id,
                                            'executable': self.program, 'stopped': stopped}), encoding='utf-8')

    def __exit__(self, *exception):
        try:
            if self.process is not None:
                if self.process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'], capture_output=True, timeout=10)
                    else:
                        self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
                with socket.socket() as check:
                    check.settimeout(1)
                    stopped = check.connect_ex(('127.0.0.1', self.port)) != 0
                self._record(stopped)
                if not stopped:
                    raise ValueError('The owned OpenCode host did not stop. Inspect ' + str(self.manifest))
        finally:
            if self.log is not None:
                self.log.close()


def run(bridge, args):
    with OpenCodeHost(bridge, model=args.model) as host:
        if args.prompt:
            command = [host.program, 'run', '--server', host.address, '--format', args.format]
            if args.model:
                command += ['--model', args.model]
            command += [' '.join(args.prompt)]
        else:
            command = [host.program, str(bridge.root), '--server', host.address]
            if args.model:
                command += ['--model', args.model]
        code = subprocess.run(command, cwd=bridge.root, env=host.env).returncode
        # An evaluator/user interruption can make the foreground command return
        # non-zero even though the native plugin has a valid terminal event and
        # must finish the bounded checkpoint/finding capture. Never skip drain
        # solely because the foreground task was interrupted.
        host.drain()
        return code
