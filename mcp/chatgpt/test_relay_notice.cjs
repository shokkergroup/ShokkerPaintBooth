'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(path.join(__dirname,'candidates/spb-ai-connect.js'),'utf8');
const pro=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
async function harness(provider){
 const log=[],requests=[],store=new Map([['spb_ai_helper',provider]]);
 const window={crypto:{randomUUID:()=>provider+'-page'},spbProAI:{_push:e=>log.push(e),log:()=>log.slice(),refresh:()=>{}}};
 const ctx={window,localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},document:{readyState:'loading',addEventListener:()=>{},createElement:()=>({}),head:{appendChild:()=>{}}},fetch:(url,opt)=>new Promise((resolve,reject)=>requests.push({url,opt,resolve,reject})),setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,Date,Promise,Math,isFinite,encodeURIComponent};
 vm.createContext(ctx);vm.runInContext(src,ctx);const a=window.SpbAiConnect;
 function find(route){const i=requests.findIndex(r=>r.url.startsWith(route));assert.ok(i>=0,'Pending '+route);return requests.splice(i,1)[0];}
 async function resolve(route,json){find(route).resolve({json:()=>Promise.resolve(json)});await tick();}
 a._sourceChanged();let doc=find('/api/mcp/document');const b=JSON.parse(doc.opt.body),scope=b.page+':'+b.epoch;
 doc.resolve({json:()=>Promise.resolve({ok:true,document_scope:scope,seq:1})});await tick();
 const send=async(seq,text='Question')=>{const p=a.relay(text);await tick();await resolve('/api/mcp/inbox',{ok:true,seq,listening:false});await p;return log.filter(e=>e.role==='note').at(-1);};
 const answer=async(reply,extra={})=>resolve('/api/mcp/chat?',{ok:true,listening:false,entries:[{role:'assistant',text:'Answer '+reply,seq:reply+1,reply_to:reply,document_scope:scope,...extra}]});
 return {a,window,ctx,store,log,requests,scope,find,resolve,send,answer};
}
(async()=>{
 for(const provider of ['chatgpt','claude']){
  const h=await harness(provider),n=await h.send(10);
  assert.equal(h.a.hideRelayNotice(n),false,'Unanswered warning visible');
  await h.answer(10);assert.equal(h.a.hideRelayNotice(n),true,'Matching actual answer retires waiting UI');
  assert.ok(h.log.includes(n),'History retained');assert.equal(h.a.hideRelayNotice({...n}),false,'Restored/copied note has no local lifecycle');
  const n2=await h.send(20),n3=await h.send(30);await h.answer(20);
  assert.equal(h.a.hideRelayNotice(n2),true);assert.equal(h.a.hideRelayNotice(n3),false,'Later unanswered request survives');
  await h.answer(30,{document_scope:'old-paint'});assert.equal(h.a.hideRelayNotice(n3),false,'Different paint cannot retire a warning');
  await h.answer(30,{helper:provider==='chatgpt'?'claude':'chatgpt'});assert.equal(h.a.hideRelayNotice(n3),false,'Other provider cannot retire a warning');
  await h.answer(30,{reply_to:'30'});assert.equal(h.a.hideRelayNotice(n3),false,'No string coercion');
  await h.answer(30,{reply_to:null});assert.equal(h.a.hideRelayNotice(n3),false,'Missing acknowledgement preserves warning');
  await h.answer(30);assert.equal(h.a.hideRelayNotice(n3),true);
  const count=h.log.filter(e=>e.role==='note').length,p=h.a.relay('Fast answer');await tick();
  await h.answer(40);await h.resolve('/api/mcp/inbox',{ok:true,seq:40,listening:false});await p;
  assert.equal(h.log.filter(e=>e.role==='note').length,count,'Answer arriving before POST acknowledgement never adds stale warning');
  const n4=await h.send(50);h.window.SPB_CX3_OFF=true;await h.answer(50);assert.equal(h.a.hideRelayNotice(n4),false,'Kill switch preserves original visible warning');h.window.SPB_CX3_OFF=false;
  const q=h.a.relay('Switch before acknowledgement');await tick();h.a.setMode('offline');await h.resolve('/api/mcp/inbox',{ok:true,seq:60,listening:false});await q;
  assert.equal(h.log.filter(e=>e.role==='note').length,count+1,'Switched provider cannot add old warning');
  const error={role:'err',text:'Connection failed'},ordinary={role:'note',text:'Remember to save'},user={role:'user',text:'My words'},ai={role:'ai',text:'Model answer'};
  [error,ordinary,user,ai].forEach(e=>assert.equal(h.a.hideRelayNotice(e),false));
  h.store.set('spb_ai_helper',provider);
  // Execute the actual render predicate; hidden warnings do not remove any other role.
  const start=pro.indexOf('        _log.forEach(function (m) {\n            if (window.SpbAiConnect && SpbAiConnect.hideRelayNotice'),end=pro.indexOf("            if (m.role === 'user')",start);
  assert.ok(start>=0&&end>start);const visible=[];
  h.ctx.SpbAiConnect=h.a;h.ctx._log=[n,n3,n4,error,ordinary,user,ai];h.ctx.visible=visible;
  vm.runInContext(pro.slice(start,end)+'            visible.push(m);\n        });',h.ctx);
  assert.deepEqual(visible,[n4,error,ordinary,user,ai]);
  // New document invalidates a pending old POST and keeps its answer from hiding a new note.
  const old=h.a.relay('Old paint request');await tick();h.a._sourceChanged();await h.resolve('/api/mcp/inbox',{ok:true,seq:70,listening:false});await old;
  assert.equal(h.log.filter(e=>e.role==='note').length,count+1);
 }
 console.log(JSON.stringify({pass:true,providers:2,actual_candidate_poll_relay_render:true,matching_message_only:true,unanswered_preserved:true,document_and_provider_races:true,post_ack_race:true,restored_notes_not_authority:true,errors_and_history_preserved:true,kill_switch:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
