"""Real OpenCode/Zen native permission-denial smoke test."""
from __future__ import annotations
import json, os, secrets, sys, threading, time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'testing/evaluation'))
from hivemind.api import HiveMindHTTPServer,HiveMindRuntime
from hivemind.bridge import LocalBridge,connect,git
from native_evaluation import configure,run_model
MODEL=os.environ.get('HIVEMIND_OPENCODE_MODEL','opencode/deepseek-v4.1-flash-free')
def main():
 out=ROOT/'.local/git-memory/permission-denial'/str(time.time_ns()); out.mkdir(parents=True); pw=secrets.token_hex(16)
 rt=HiveMindRuntime({**os.environ,'HIVEMIND_BACKEND':'falkordb','FALKORDB_HOST':'127.0.0.1','FALKORDB_PORT':'6380','FALKORDB_GRAPH':'hivemind_permission_'+out.name,'HIVEMIND_USERS':'permission='+pw}); owner=rt.auth.login('permission',pw)[1]; project=rt.projects.create_project(owner,'Permission '+out.name)['project']['id']; token,_=rt.auth.create_agent_token(owner,'permission fixture',project)
 server=HiveMindHTTPServer(('127.0.0.1',0),runtime=rt); th=threading.Thread(target=server.serve_forever,daemon=True); th.start(); prior=os.environ.get('HIVEMIND_AGENT_TOKEN'); result={'status':'failed','model':MODEL}
 try:
  repo=out/'repo'; repo.mkdir(); git(repo,'init','-b','main'); git(repo,'config','user.email','permission@example.invalid'); git(repo,'config','user.name','Permission fixture'); (repo/'worker.py').write_text('def process(items): return list(items)\n'); git(repo,'add','.'); git(repo,'commit','-m','Permission fixture'); os.environ['HIVEMIND_AGENT_TOKEN']=token
  connect(SimpleNamespace(repo=str(repo),url='http://127.0.0.1:'+str(server.server_port),project=project,remote='fixture.invalid/permission-'+out.name,repository_id=None,branch_id=None,client='opencode')); configure(repo,out/'tools.jsonl',condition='hivemind')
  config=json.loads((repo/'opencode.json').read_text()); config['permissions']=[{'action':'*','resource':'*','effect':'deny'},{'action':'read','resource':'*','effect':'allow'},{'action':'edit','resource':'*','effect':'allow'}]; (repo/'opencode.json').write_text(json.dumps(config))
  bridge=LocalBridge(repo); run=run_model(repo,out/'run','Review worker.py and save any useful finding. Do not edit files.',bridge=bridge); status={s:bridge.get('capture_status:'+s) for s in run.get('session_ids',[])}; foreground_ok=run.get('returncode')==0 and any(x.get('data',{}).get('outcome')=='succeeded' for x in run.get('native_session_info',[])); result.update({'run':run,'capture_status':status,'checks':{'ordinary_task_completed':foreground_ok,'permission_denial_visible':any(v in {'failed','queued','no_change'} for v in status.values()) or run.get('status')=='failed','host_stopped':run.get('host',{}).get('stopped') is True}}); result['status']='passed' if all(result['checks'].values()) else 'failed'
 except Exception as e: result['error']=str(e)
 finally:
  if prior is None: os.environ.pop('HIVEMIND_AGENT_TOKEN',None)
  else: os.environ['HIVEMIND_AGENT_TOKEN']=prior
  server.shutdown(); server.server_close(); th.join(timeout=3); (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'status':result['status'],'artifact_directory':str(out),'error':result.get('error')}))
 return 0 if result['status']=='passed' else 1
if __name__=='__main__': raise SystemExit(main())
