"""Isolated installed-client probe. Makes one real Zen request; never reads auth exports."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

MODEL = os.environ.get('HIVEMIND_OPENCODE_MODEL', 'opencode/deepseek-v4.1-flash-free')


def environment(base):
    env = dict(os.environ)
    for kind in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
        env['XDG_' + kind + '_HOME'] = str(base / kind.lower())
    # Keep tests independent of an inherited custom config or attached service.
    for key in ('OPENCODE_CONFIG', 'OPENCODE_CONFIG_DIR', 'OPENCODE_CONFIG_CONTENT', 'OPENCODE_SERVER'):
        env.pop(key, None)
    return env


def main():
    base = Path('.local/git-memory/opencode-isolated' + ('-v1' if os.environ.get('HIVEMIND_PROBE_LEGACY') == '1' else '')).resolve()
    root = base / 'probe'
    root.mkdir(parents=True, exist_ok=True)
    env = environment(base)
    executable = os.environ.get('HIVEMIND_OPENCODE_BIN') or shutil.which('opencode.cmd') or shutil.which('opencode')
    if not executable:
        raise RuntimeError('Install OpenCode before running this probe')
    if not (root / '.git').exists():
        subprocess.run(['git', 'init', '-b', 'main', str(root)], check=True, capture_output=True)
    (root / 'opencode.json').write_text(json.dumps({'$schema': 'https://opencode.ai/config.json',
        'enabled_providers': [MODEL.split('/', 1)[0]], 'model': MODEL,
        'permission': {'*': 'deny'}}), encoding='utf-8')
    plugins = root / '.opencode/plugins'
    plugins.mkdir(parents=True, exist_ok=True)
    log = root / '.git/probe-events.jsonl'
    plugin = r"""import { appendFileSync } from 'node:fs';
export default {id:'hivemind.probe', setup: async (ctx) => {
 const log = (hook, data = {}) => appendFileSync(LOG, JSON.stringify({hook, ...data}) + '\n');
 log('setup', {keys: Object.keys(ctx), app:ctx.app});
 await ctx.session.hook('prompt', i => log('prompt', {keys:Object.keys(i)}));
 await ctx.session.hook('context', i => {log('context', {keys:Object.keys(i)}); i.system.push({type:'text',text:'Reply with exactly HIVEMIND_ZEN_OK.'});});
 await ctx.session.hook('http.request', i => log('http.request', {url:i.request.url,headers:Array.from(i.request.headers.keys())}));
}};
""".replace('LOG', json.dumps(str(log)))
    (plugins / 'probe.js').write_text(plugin, encoding='utf-8')
    legacy = os.environ.get('HIVEMIND_PROBE_LEGACY') == '1'
    if legacy:
        (plugins / 'probe.js').write_text('''import {appendFileSync} from 'node:fs';
export const Probe = async ctx => {
 const log = hook => appendFileSync(LOG, JSON.stringify({hook})+'\\n'); log('legacy.setup');
 return {'experimental.chat.system.transform': async (i,o) => {log('legacy.context'); o.system.push('Reply with exactly HIVEMIND_ZEN_OK.');}};
};'''.replace('LOG', json.dumps(str(log))), encoding='utf-8')
    command = [executable, 'run', '--standalone', '--format', 'json', '--model', MODEL,
               'Reply with the requested connectivity marker. Do not use tools.']
    if legacy:
        command.remove('--standalone')
    run = base / ('probe-' + str(time.time_ns()))
    run.mkdir()
    with (run / 'stdout.jsonl').open('w', encoding='utf-8') as out, (run / 'stderr.log').open('w', encoding='utf-8') as err:
        result = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=err, timeout=180)
    print(json.dumps({'exit_code': result.returncode, 'root': str(root), 'events': log.exists(),
        'artifacts': str(run), 'stdout': (run / 'stdout.jsonl').read_text(encoding='utf-8')[-3500:],
        'stderr': (run / 'stderr.log').read_text(encoding='utf-8')[-1500:]}))


if __name__ == '__main__':
    main()
