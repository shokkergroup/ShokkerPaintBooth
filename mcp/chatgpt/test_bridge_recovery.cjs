'use strict';
// Execute the actual bridge in a controlled transport/clock. No app pixel claim.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
async function setup(file,kill=false){
 let now=0,next=0,enabled=true,ran=0,finishCall,scope='test-document:2';const timers=new Map(),polls=[],acks=[],posts=[];
 const w={SpbAiConnect:{documentScope:()=>scope},SPB_CX3_OFF:kill,spbProAI:{mcpCall(){ran++;return new Promise(r=>{finishCall=r;});}}};
 const context={window:w,document:{readyState:'complete'},Date,Math,Promise,Error,encodeURIComponent,
  AbortController,setInterval(){},clearTimeout(id){timers.delete(id);},
  setTimeout(fn,ms){const id=++next;timers.set(id,{fn,at:now+ms});return id;},
  fetch(url,opt={}){
   if(url.startsWith('/api/mcp/poll'))return new Promise(resolve=>polls.push({resolve,signal:opt.signal,url}));
   if(url==='/api/mcp/ack')return new Promise(resolve=>acks.push({resolve,body:JSON.parse(opt.body)}));
   if(url==='/api/mcp/result')posts.push(JSON.parse(opt.body));
   if(url==='/api/mcp/enable')enabled=JSON.parse(opt.body).enabled;
   return Promise.resolve({json:()=>Promise.resolve({enabled,connected:false,calls:0})});
  }};
 vm.runInNewContext(fs.readFileSync(file,'utf8'),context,{filename:file});
 async function tick(ms){const end=now+ms;for(;;){const due=[...timers].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!due)break;now=due[1].at;timers.delete(due[0]);due[1].fn();await flush();}now=end;await flush();}
 await tick(1500);
 return {polls,acks,posts,tick,scope:v=>{scope=v;},ack:async(i,j)=>{acks[i].resolve({json:()=>Promise.resolve(j)});await flush();},bridge:w.SpbMcpBridge,ran:()=>ran,finish:()=>finishCall({ok:true,result:{}}),reply:async(i,j)=>{polls[i].resolve({json:()=>Promise.resolve(j)});await flush();}};
}
(async()=>{
 const original=await setup(path.join(root,'_codex_mcp_work/chatgpt-dev/59910/bridge-recovery-original.js'));
 await original.tick(49000);assert.equal(original.polls.length,1,'negative control reproduces indefinitely pending poll');
 await original.bridge.setEnabled(false);await original.bridge.setEnabled(true);await flush();
 assert.equal(original.polls.length,1,'negative control reproduces ineffective off/on');
 const file=path.join(__dirname,'candidates/spb-mcp-bridge.js');
 const confirmed=await setup(file);assert.match(confirmed.polls[0].url,/ack=1/);
 await confirmed.reply(0,{call:{id:'ack-required',tool:'edit_layer',document_scope:'test-document:2',delivery_ack:true}});
 assert.equal(confirmed.ran(),0);assert.equal(confirmed.acks.length,1);
 await confirmed.ack(0,{ok:true,execute:true});assert.equal(confirmed.ran(),1);confirmed.finish();await flush();
 const expired=await setup(file);
 await expired.reply(0,{call:{id:'expired',tool:'edit_layer',document_scope:'test-document:2',delivery_ack:true}});
 await expired.ack(0,{ok:false,error:'expired_or_claimed_call'});assert.equal(expired.ran(),0);assert.equal(expired.posts.length,0);
 const changed=await setup(file);
 await changed.reply(0,{call:{id:'document-changed',tool:'edit_layer',document_scope:'test-document:2',delivery_ack:true}});
 changed.scope('test-document:3');await changed.ack(0,{ok:true,execute:true});
 assert.equal(changed.ran(),0);assert.equal(changed.posts.length,1);assert.equal(changed.posts[0].ok,false);
 const lostAck=await setup(file);
 await lostAck.reply(0,{call:{id:'lost-ack',tool:'edit_layer',document_scope:'test-document:2',delivery_ack:true}});
 await lostAck.tick(15000);assert.equal(lostAck.ran(),0);assert.equal(lostAck.polls.length,2);
 await lostAck.ack(0,{ok:true,execute:true});assert.equal(lostAck.ran(),0,'Late acknowledgement cannot execute after the receipt expired');
 const scoped=await setup(file);assert.match(scoped.polls[0].url,/document_scope=test-document%3A2/);
 await scoped.reply(0,{call:{id:'wrong-document',tool:'edit_layer',document_scope:'test-document:1'}});
 assert.equal(scoped.ran(),0,'A call delivered after the document changed must never execute');
 await scoped.reply(1,{call:{id:'right-document',tool:'edit_layer',document_scope:'test-document:2'}});
 assert.equal(scoped.ran(),1,'A matching document call still executes exactly once');scoped.finish();await flush();
 const a=await setup(file);assert.equal(a.polls.length,1);await a.tick(45000);
 assert.equal(a.polls[0].signal.aborted,true);await a.tick(3000);assert.equal(a.polls.length,2);
 await a.reply(0,{enabled:true,call:{id:'late',tool:'edit_layer'}});assert.equal(a.ran(),0,'timed out late response cannot execute');
 await a.reply(1,{enabled:true,call:{id:'one',tool:'edit_layer'}});assert.equal(a.ran(),1);
 await a.tick(120000);assert.equal(a.polls.length,2,'long paint handler never retried or overlapped');
 await a.bridge.setEnabled(false);await a.bridge.setEnabled(true);await flush();
 assert.equal(a.polls.length,2,'toggle during a delivered call waits for its result');
 a.finish();await flush();assert.equal(a.polls.length,3);assert.match(a.polls[2].url,/claim=1/);
 const b=await setup(file);await b.bridge.setEnabled(false);await b.bridge.setEnabled(true);await flush();
 assert.equal(b.polls.length,2);assert.equal(b.polls[0].signal.aborted,true);
 await b.reply(0,{enabled:true,call:{id:'old',tool:'edit_layer'}});assert.equal(b.ran(),0);
 await b.reply(1,{superseded:true});assert.equal(b.polls.length,2);await b.tick(90000);assert.equal(b.polls.length,2);
 await b.bridge.setEnabled(true);await flush();assert.equal(b.polls.length,3,'explicit owner reclaim resumes superseded page');
 const killed=await setup(file,true);await killed.tick(49000);assert.equal(killed.polls.length,1);assert.equal(killed.polls[0].signal,undefined,'Owner CX3 switch retains plain untimed polling');
 console.log('PASS actual bridge: baseline reproduces stall; timeout, off/on, late-call rejection, delivered-call isolation and supersession recovery');
})().catch(e=>{console.error(e);process.exitCode=1;});
