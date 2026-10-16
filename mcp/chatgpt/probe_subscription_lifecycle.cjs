'use strict';
// Private59910 idle process acceptance: no question, model or paint mutation.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process'),control=require('./subscription-control.cjs');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const executable=process.argv[2];if(!executable||!fs.existsSync(executable))throw Error('Supply the installed Codex executable.');
const paths=control.paths(dir);if(fs.existsSync(paths.lock))throw Error('An existing lock needs review; this probe never removes it.');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const fixtureDir=path.join(root,'_release_evidence/chatgpt-dev/59910/projects');
function preserved(){const names=fs.readdirSync(fixtureDir).filter(n=>n.endsWith('.spbproj')).sort();assert.equal(names.length,2);return{pending:hash(path.join(dir,'subscription-pending.json')),fixtures:Object.fromEntries(names.map(n=>[n,hash(path.join(fixtureDir,n))]))};}
async function phase(previous){
 const record={events:[],old_stop_ignored:false};
 return await new Promise((resolve,reject)=>{
  let buffer='',waits=0,failed=null;
  const child=spawn(process.execPath,[path.join(__dirname,'subscription-listener.cjs'),'--codex',executable,'--model','gpt-6.1-sol','--duration-seconds','45','--wait-seconds','2','--batches','1'],{cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe']});
  const timer=setTimeout(()=>{failed=Error('Lifecycle proof deadline');child.kill();},55000);
  child.stdout.setEncoding('utf8');child.stderr.on('data',()=>{});child.on('error',e=>{failed=e;});
  child.stdout.on('data',chunk=>{
   buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let event;try{event=JSON.parse(line);}catch{continue;}
    record.events.push(event);
    try{
     assert.equal(event.model_inferences_started,0);
     if(event.state==='waiting_without_inference'){
      waits++;
      if(waits===1){record.running=control.status(dir);assert.equal(record.running.process_present,true);assert.equal(record.running.availability,'unverified');
       if(previous){assert.notEqual(previous.instance,record.running.instance);fs.writeFileSync(paths.stop,JSON.stringify({...previous,requested_at:Date.now()})+'\n');}
      }
      if(waits===2){record.before_stop=control.status(dir);if(previous){assert.equal(record.before_stop.stop_requested,false);record.old_stop_ignored=true;}record.stop=control.requestStop(dir);assert.equal(record.stop.ok,true);record.after_request=control.status(dir);assert.equal(record.after_request.stop_requested,true);}
     }
    }catch(e){failed=e;child.kill();}
   }
  });
  child.on('close',code=>{
   clearTimeout(timer);if(failed)return reject(failed);
   try{record.exitCode=code;record.terminal=control.status(dir);assert.equal(code,0);assert.equal(record.terminal.state,'owner_stop');assert.equal(record.terminal.active,false);assert.equal(record.terminal.last.model_inferences_started,0);assert.equal(fs.existsSync(paths.lock),false);assert.equal(fs.existsSync(paths.stop),false);assert.ok(waits>=2);resolve(record);}catch(e){reject(e);}
  });
 });
}
(async()=>{
 const before=preserved(),first=await phase(),second=await phase(first.running),after=preserved();assert.deepEqual(after,before);
 const artifact_hashes=Object.fromEntries(['subscription-control.cjs','subscription-listener.cjs','subscription-listener-core.cjs','test_subscription_control.cjs','test_subscription_listener.cjs','probe_subscription_lifecycle.cjs'].map(n=>[n,hash(path.join(__dirname,n))]));
 const record={schema:'spb-subscription-lifecycle-acceptance/1',time:new Date().toISOString(),port:59910,pass:true,model_inferences_started:0,apiFallback:false,first,second,before,after,artifact_hashes,limits:['Idle real-process stop/restart only; busy stop is component tested.','Process/journal status does not certify MCP, model or commercial readiness.','Not installed as a customer startup service; no arbitrary crash recovery or editing replay.']};
 const receipt=path.join(dir,'subscription-lifecycle-acceptance.json');fs.writeFileSync(receipt,JSON.stringify(record,null,2)+'\n');console.log(JSON.stringify({pass:true,real_idle_stops:2,restart_instance_changed:true,old_stop_ignored:true,model_inferences_started:0,pending_and_two_fixtures_unchanged:true,receipt:path.basename(receipt)}));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
