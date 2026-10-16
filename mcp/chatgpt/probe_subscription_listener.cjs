'use strict';
// Actual private HTTP claim -> durable checkpoint -> new-process read-only model
// reply. This bypasses customer Send UI; it must not be called native Send proof.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910'),journal=path.join(dir,'subscription-pending.json');
const executable=process.argv[2];assert.ok(executable&&fs.existsSync(executable));
const token=fs.readFileSync(path.join(dir,'pairing/token.txt'),'utf8').trim();
const env={...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')};
const mcp=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env,windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map();
mcp.stdout.setEncoding('utf8');mcp.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let r;try{r=JSON.parse(line);}catch{continue;}if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id);}}});mcp.stderr.on('data',()=>{});
const timer=setTimeout(()=>{mcp.kill();console.error('Read-only listener proof timed out');process.exit(1);},300000);
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);mcp.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n');});}
async function call(name,args={}){const r=await rpc('tools/call',{name,arguments:args});assert.ok(r.result&&!r.result.isError,JSON.stringify(r.error||r.result));return JSON.parse(r.result.content[0].text);}
async function http(route,body){const r=await fetch('http://127.0.0.1:59910'+route,{method:body?'POST':'GET',headers:{'X-SPB-MCP-Token':token,'X-SPB-MCP-Client':'codex-spb-listener',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});const data=await r.json();assert.equal(r.status,200,JSON.stringify(data));return data;}
const keys=['layers','zones','selected_zone','paint_colours','pending_changes','recent_changes','saved_design_brief','template_identity'];
const select=s=>Object.fromEntries(keys.map(k=>[k,s[k]===undefined?null:s[k]]));
const fixtureDir=path.resolve(__dirname,'../../_release_evidence/chatgpt-dev/59910/projects');
const fixtures=()=>Object.fromEntries(fs.readdirSync(fixtureDir).filter(n=>n.endsWith('.spbproj')).sort().map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(fixtureDir,n))).digest('hex')]));
function controller(flags,onWaiting){return new Promise((resolve,reject)=>{
 const child=spawn(process.execPath,[path.join(__dirname,'subscription-listener.cjs'),'--codex',executable,'--model','gpt-6.1-sol','--service-tier','fast','--duration-seconds','210','--wait-seconds','2','--batches','1',...flags],{windowsHide:true,stdio:['ignore','pipe','pipe']});
 let text='',buf='',triggered=false,error=null;const events=[];
 child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{text+=chunk;buf+=chunk;let i;while((i=buf.indexOf('\n'))>=0){const line=buf.slice(0,i);buf=buf.slice(i+1);let e;try{e=JSON.parse(line);}catch{continue;}events.push(e);if(!triggered&&e.state==='waiting_without_inference'&&onWaiting){triggered=true;onWaiting().catch(e=>{error=e;child.kill();});}}});
 child.stderr.on('data',()=>{});child.on('error',reject);child.on('close',code=>error?reject(error):resolve({code,events}));
});}
(async()=>{
 assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-listener-read-probe',version:'1'}})).result);
 await call('spb_status');const before=select(await call('spb_get_state')),saved=fixtures();assert.equal(Object.keys(saved).length,2);
 const convo=await http('/api/mcp/conversation');assert.ok(convo.document_scope);
 const status=await http('/api/mcp/status?helper=chatgpt');assert.equal(status.inbox,0);assert.equal(status.inflight,0,'Do not take another test/session pending question.');
 if(fs.existsSync(journal))assert.notEqual(JSON.parse(fs.readFileSync(journal,'utf8')).state,'pending','Do not replace a pending question.');
 const query='What does Base Paint do in this open template, and which copy is for body colour? Advice only; do not change anything.';
 let posted;
 const received=await controller(['--receive-only'],async()=>{posted=await http('/api/mcp/inbox',{helper:'chatgpt',document_scope:convo.document_scope,text:query});});
 assert.equal(received.code,0);assert.equal(received.events.at(-1).stopped,'pending_checkpoint');assert.equal(received.events.at(-1).model_inferences_started,0);
 const checkpoint=JSON.parse(fs.readFileSync(journal,'utf8'));assert.equal(checkpoint.messages.at(-1).seq,posted.seq);assert.equal(checkpoint.state,'pending');
 const blocked=await controller([]);assert.equal(blocked.code,1);assert.equal(blocked.events.at(-1).stopped,'pending_requires_explicit_recovery');assert.equal(blocked.events.at(-1).model_inferences_started,0);
 const recovered=await controller(['--recover-pending']);assert.equal(recovered.code,0,JSON.stringify(recovered));assert.equal(recovered.events.at(-1).handled,1);assert.equal(recovered.events.at(-1).model_inferences_started,1);
 const afterConvo=await http('/api/mcp/conversation'),answer=afterConvo.turns.find(e=>e.role==='assistant'&&e.reply_to===posted.seq);assert.ok(answer?.text);assert.equal(afterConvo.document_scope,convo.document_scope);
 const after=select(await call('spb_get_state'));assert.deepEqual(after,before);assert.deepEqual(fixtures(),saved);
 // Controlled receipt-loss case: model already replied, durable terminal write
 // was lost. Recovery checks transcript and starts zero new model inference.
 fs.writeFileSync(journal,JSON.stringify(checkpoint,null,2)+'\n');
 const settled=await controller(['--recover-pending']);assert.equal(settled.code,0);assert.equal(settled.events.at(-1).stopped,'already_replied');assert.equal(settled.events.at(-1).model_inferences_started,0);
 const receipt='subscription-listener-recovery-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(dir,receipt),JSON.stringify({checked_at:new Date().toISOString(),executable,model:'gpt-6.1-sol',port:59910,apiFallback:false,received,blocked,recovered,settled,checkpoint,answer,before,after,fixture_hashes:saved,limits:['Actual local inbox/controller and installed subscription model; customer Send UI not exercised.','Eight exposed paint fields and two fixture hashes; not full raster equality.','Receive-only checkpoint and controlled lost terminal journal write; no arbitrary mid-edit crash or persistent unattended availability.','Read-only worker; paint-writing recovery remains withheld.']},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({pass:true,receipt,exact_reply_to:posted.seq,model_inferences:1,idle_checkpoint_blocked_and_settled_inferences:0,preserved_paint_fields:keys.length,retained_original_fixtures:2}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(()=>{clearTimeout(timer);mcp.stdin.end();mcp.kill();});
