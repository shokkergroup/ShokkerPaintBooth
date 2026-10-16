'use strict';
// Local process ownership only. No credentials, paint commands or inference.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const SCHEMA='spb-subscription-controller/1';
function read(file){try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch{return null;}}
function atomic(file,value){const temp=file+'.'+crypto.randomUUID()+'.tmp';try{fs.writeFileSync(temp,JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});fs.renameSync(temp,file);}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}}
function paths(dir){return{lock:path.join(dir,'subscription-listener.lock.json'),status:path.join(dir,'subscription-controller-status.json'),stop:path.join(dir,'subscription-controller-stop.json')};}
function valid(v){return v?.schema===SCHEMA&&v.port===59910&&Number.isSafeInteger(v.pid)&&v.pid>0&&typeof v.instance==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v.instance);}
function acquire(dir,{pid=process.pid,now=Date.now()}={}){
 const p=paths(dir),owner={schema:SCHEMA,port:59910,pid,instance:crypto.randomUUID(),started_at:now};
 fs.writeFileSync(p.lock,JSON.stringify(owner)+'\n',{flag:'wx',mode:0o600});
 let telemetry={};
 const owns=()=>{const current=read(p.lock);return valid(current)&&current.instance===owner.instance&&current.pid===owner.pid;};
 function publish(state,extra={}){if(!owns())throw Error('Controller ownership changed; stop without replacing another controller.');telemetry={...telemetry,...extra};atomic(p.status,{...telemetry,...owner,state,active:true,updated_at:Date.now()});}
 function stopRequested(){if(!owns())return true;const request=read(p.stop);return valid(request)&&request.instance===owner.instance&&request.pid===owner.pid;}
 function release(state='stopped'){
  if(!owns())return false;
  atomic(p.status,{...telemetry,...owner,state,active:false,updated_at:Date.now()});
  const request=read(p.stop);if(valid(request)&&request.instance===owner.instance&&request.pid===owner.pid)fs.unlinkSync(p.stop);
  fs.unlinkSync(p.lock);return true;
 }
 try{publish('starting');}catch(e){if(owns())fs.unlinkSync(p.lock);throw e;}
 return{owner,owns,publish,stopRequested,release};
}
function requestStop(dir){const p=paths(dir),owner=read(p.lock);if(!valid(owner))return{ok:false,reason:fs.existsSync(p.lock)?'unrecognized_lock':'not_running'};atomic(p.stop,{...owner,requested_at:Date.now()});return{ok:true,instance:owner.instance,pid:owner.pid,mode:'cooperative',note:'Stops idle waits; an active read-only answer may finish before the bounded worker exits. No new turn starts after this request.'};}
function status(dir,alive=pid=>{try{process.kill(pid,0);return true;}catch(e){return e.code==='ESRCH'?false:null;}}){
 const p=paths(dir),owner=read(p.lock),latest=read(p.status);
 if(!owner&&!fs.existsSync(p.lock))return{active:false,state:latest?.state||'not_running',last:latest};
 if(!valid(owner))return{active:null,state:'unrecognized_lock',requires_review:true};
 const live=alive(owner.pid),matching=valid(latest)&&latest.instance===owner.instance&&latest.pid===owner.pid;
 const request=read(p.stop),exactStop=valid(request)&&request.instance===owner.instance&&request.pid===owner.pid;
 // A PID can be reused; even a fresh journal is not an MCP/model readiness check.
 return{...owner,active:live===false?false:null,process_present:live,
  reported_active:matching?latest.active===true:null,
  state:live===false?'stale_lock':live===null?'process_unconfirmed':matching?latest.state:'starting',
  updated_at:matching?latest.updated_at:null,
  model_inferences_started:matching&&Number.isSafeInteger(latest.model_inferences_started)?latest.model_inferences_started:null,
  requires_review:live!==true||!matching,stop_requested:exactStop,
  availability:'unverified',note:'Local process/journal observation only; does not confirm listener ownership, MCP readiness or subscription/model availability.'};
}
module.exports={SCHEMA,acquire,requestStop,status,paths};
if(require.main===module){const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910'),mode=process.argv[2];if(!['status','stop'].includes(mode))throw Error('Use status or stop for the private59910 controller.');console.log(JSON.stringify(mode==='stop'?requestStop(dir):status(dir)));}
