// Evaluation-only. No context injection, permission changes or memory writes.
// Official @opencode/plugin + @opencode/schema 2.0.29: execute.after,
// session.tool.success, session.interrupt({sessionID,resume:false}).
import {appendFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
const command = __BOUNDARY_COMMAND__;
const nativeLog = __NATIVE_EVENT_LOG__;
function record(value) {appendFileSync(nativeLog, JSON.stringify({observed_ms:Date.now(), ...value})+'\n');}
function assess(event) {
  return new Promise((resolve,reject)=>{
    const child=spawn(command[0],command.slice(1),{stdio:['pipe','pipe','pipe'],windowsHide:true});
    let out='',err='';
    const timer=setTimeout(()=>{child.kill();reject(new Error('Private checkpoint boundary check exceeded 35 seconds'));},35000);
    child.stdout.on('data',x=>{out+=x;});
    child.stderr.on('data',x=>{err=(err+x).slice(-2000);});
    child.on('error',e=>{clearTimeout(timer);reject(e);});
    child.on('close',code=>{clearTimeout(timer);if(code)return reject(new Error(err||'Private checkpoint check failed'));try{resolve(JSON.parse(out));}catch(e){reject(e);}});
    child.stdin.on('error',()=>{});
    child.stdin.end(JSON.stringify(event));
  });
}
export default {id:'hivemind.evaluation-checkpoint-boundary',async setup(ctx){
  const abort=new AbortController();
  const successes=new Map();
  let selected,interruptStarted=false,checkpointStopStarted=false;
  async function interruptIfReady(resume=true){
    if(!selected||(!resume&&checkpointStopStarted)|| (resume&&interruptStarted)||!successes.has(selected.id))return;
    if(resume) interruptStarted=true; else checkpointStopStarted=true;
    record({kind:'interrupt_request',sessionID:selected.sessionID,call_id:selected.id});
    try {
      const result=await ctx.session.interrupt({sessionID:selected.sessionID,resume});
      record({kind:'interrupt_result',sessionID:selected.sessionID,result});
    } catch(error) {record({kind:'interrupt_error',sessionID:selected.sessionID,error:String(error)});}
  }
  const after=await ctx.tool.hook('execute.after',async event=>{
    record({kind:'execute_after',event:{sessionID:event.sessionID,id:event.id,tool:event.tool,status:event.status,messageID:event.messageID}});
    if(event.status!=='completed')return;
    const toolName=String(event.tool||'');
    if(selected && /checkpoint/i.test(toolName) && !checkpointStopStarted){
      setTimeout(()=>{void interruptIfReady(false);},0);
      return;
    }
    if(selected)return;
    const result=await assess({sessionID:event.sessionID,id:event.id,tool:event.tool,
      messageID:event.messageID,status:event.status});
    if(result.stop){
      selected={sessionID:event.sessionID,id:event.id};
      // Let execute.after return before cancelling. A matching durable success
      // must actually exist; a selected private snapshot alone is not evidence.
      setTimeout(()=>{void interruptIfReady();},0);
    }
  });
  const pump=(async()=>{
    for await(const event of ctx.event.subscribe({signal:abort.signal})){
      if(['session.tool.success','session.execution.interrupted','session.execution.succeeded',
          'session.execution.failed','session.synthetic'].includes(event.type))record({kind:'native_event',event});
      if(event.type==='session.tool.success'){
        successes.set(event.data.id,event);
        // No actor-visible result or private test detail is injected.
        void interruptIfReady();
      }
    }
  })().catch(error=>{if(!abort.signal.aborted)record({kind:'observer_error',error:String(error)});});
  return async()=>{abort.abort();await after.dispose();await pump;};
}};
