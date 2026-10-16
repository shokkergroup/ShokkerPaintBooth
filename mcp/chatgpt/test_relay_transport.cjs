'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'candidates/spb-ai-connect.js'),'utf8');
const tick=async()=>{for(let i=0;i<35;i++)await Promise.resolve();};
const response=(j,ok=true)=>({ok,json:()=>Promise.resolve(j)});
function setup(helper,off=false){
 let mode=helper,holdStatus=false,statusFailure=false,id=0,redraws=0,initialHold=false;
 const timers=new Map(),reads=[],inbox=[],shown=[],status=[],aborted=[];
 const w={SPB_RELAY_TRANSPORT_OFF:off,crypto:require('node:crypto').webcrypto,spbProAI:{refresh(){redraws++;},_push(e){shown.push(e);},log:()=>shown},SpbMcpBridge:{setEnabled(){}}};
 const c={window:w,URL,Promise,AbortController,localStorage:{getItem:()=>mode,setItem:(k,v)=>{mode=v;}},document:{readyState:'loading',addEventListener(){},createElement:()=>({}),head:{appendChild(){}}},setInterval(){},
  setTimeout(fn,ms){const n=++id;timers.set(n,{fn,ms});return n;},clearTimeout:n=>timers.delete(n),
  fetch(url,opt={}){
   if(url==='/api/mcp/document'){const b=JSON.parse(opt.body);return Promise.resolve(response({ok:true,document_scope:b.page+':'+b.epoch,seq:0}));}
   if(url.startsWith('/api/mcp/status')){
    if(statusFailure)return Promise.reject(Error('test unreachable'));
    if(!holdStatus)return Promise.resolve(response({ok:true,enabled:true,listening:true,client:mode==='chatgpt'?'codex-test':'claude-test'}));
    return new Promise((resolve,reject)=>status.push({url,resolve:j=>resolve(response(j)),reject}));
   }
   if(url.startsWith('/api/mcp/chat')){
    if(url.includes('after=999999999')&&!initialHold)return Promise.resolve(response({ok:true,seq:0}));
    return new Promise((resolve,reject)=>{const req={url,resolve:j=>resolve(response(j)),reject};reads.push(req);if(opt.signal)opt.signal.addEventListener('abort',()=>{aborted.push(url);reject(Error('aborted'));},{once:true});});
   }
   if(url==='/api/mcp/inbox'){inbox.push(JSON.parse(opt.body));return Promise.resolve(response({ok:true,seq:1,listening:false}));}
   throw Error('Unexpected request '+url);
  }};
 vm.createContext(c);vm.runInContext(source,c);const A=w.SpbAiConnect;
 return {A,w,reads,status,inbox,shown,aborted,timers,redraws:()=>redraws,
  init:async()=>{A.setMode(helper);await tick();},holdStatus:v=>{holdStatus=v;},statusFailure:v=>{statusFailure=v;},initialHold:v=>{initialHold=v;},
  fire(ms){const pair=[...timers].find(([,v])=>v.ms===ms);assert.ok(pair,'Missing timer '+ms);timers.delete(pair[0]);pair[1].fn();},
  html:()=>A.cardHtml(true)};
}
(async()=>{
 for(const helper of ['chatgpt','claude']){
  let s=setup(helper);await s.init();assert.match(s.html(),/connected and listening/);assert.equal(s.reads.length,1);
  s.fire(35000);await tick();assert.match(s.html(),/connection to SPB could not be checked/);assert.match(s.html(),/Use Offline Helper/);assert.doesNotMatch(s.html(),/connected and listening/);assert.equal(s.aborted.length,1);assert.equal(s.inbox.length,0);
  s.reads[0].resolve({ok:true,listening:true,client:'codex-too-late',entries:[{seq:5,role:'assistant',text:'too late'}]});await tick();assert.equal(s.shown.length,0,'Expired read cannot deliver or advance sequence');
  s.fire(4000);await tick();assert.equal(s.reads.length,2);assert.match(s.reads[1].url,/after=-1/,'Expired read did not advance sequence');
  s.reads[1].resolve({ok:true,listening:true,client:helper==='chatgpt'?'codex-test':'claude-test',entries:[{seq:2,role:'assistant',text:'Recovered answer'}]});await tick();assert.equal(s.shown.filter(e=>e.text==='Recovered answer').length,1);await s.A.refresh();assert.match(s.html(),/Last answer received/);assert.doesNotMatch(s.html(),/could not be checked/);assert.equal(s.inbox.length,0,'Transport recovery never posts inbox');
  s=setup(helper);await s.init();s.holdStatus(true);let p=s.A.refresh();await tick();s.fire(8000);await p;assert.doesNotMatch(s.html(),/connected and listening/);s.status[0].resolve({ok:true,enabled:true,listening:true,client:'codex-late'});await tick();assert.match(s.html(),/could not be checked/,'Late status cannot revive badge');
  s.holdStatus(false);await s.A.refresh();assert.doesNotMatch(s.html(),/could not be checked/);
  s.statusFailure(true);await s.A.refresh();assert.match(s.html(),/could not be checked/);assert.doesNotMatch(s.html(),/connected and listening/);
  s=setup(helper);await s.init();s.holdStatus(true);p=s.A.refresh();await tick();s.A.setMode(helper==='chatgpt'?'claude':'chatgpt');await tick();s.status.at(-1).resolve({ok:true,enabled:true,listening:true,client:helper==='chatgpt'?'claude-current':'codex-current'});await tick();s.status[0].reject(Error('old helper failed'));await p;assert.doesNotMatch(s.html(),/could not be checked/,'Old-helper failure cannot clear new connectivity');
  s=setup(helper);await s.init();s.holdStatus(true);p=s.A.refresh();const newer=s.A.refresh();await tick();s.status[1].reject(Error('newest read failed'));await newer;s.status[0].resolve({ok:true,enabled:true,listening:true,client:'old-read'});await p;assert.match(s.html(),/could not be checked/,'Older successful status cannot resurrect after a newer failure');
  s=setup(helper);await s.init();const old=s.reads[0];s.A.setMode(helper==='chatgpt'?'claude':'chatgpt');await tick();old.resolve({ok:true,entries:[{seq:999,role:'assistant',text:'other helper answer'}]});await tick();assert.equal(s.reads.length,2,'Stale read loops for current helper');assert.equal(s.shown.length,0);s.reads[1].resolve({ok:true,entries:[{seq:3,role:'assistant',text:'current helper answer'}]});await tick();assert.match(s.reads.at(-1).url,/after=3/);assert.doesNotMatch(s.reads.at(-1).url,/after=999&/,'Old helper cannot skip current messages');
 }
 const s=setup('chatgpt',true);await s.init();assert.equal([...s.timers.values()].filter(t=>[8000,35000].includes(t.ms)).length,0,'Feature off restores unbounded legacy reads');
 console.log(JSON.stringify({pass:true,providers:2,read_timeouts_ms:[8000,35000],late_and_stale_results:'ignored',recovered_answers_once:true,automatic_inbox_replays:0,kill_switch:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
