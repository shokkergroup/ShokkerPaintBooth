'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const connector=fs.readFileSync(path.join(__dirname,'candidates/spb-ai-connect.js'),'utf8');
const editor=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const begin=editor.indexOf('        if (window.SpbAiConnect && SpbAiConnect.relaying()) {\n            text = String(text'),end=editor.indexOf('        if (window.SpbAiLease',begin);
assert.ok(begin>=0&&end>begin);
const branch=editor.slice(begin,end),tick=async()=>{for(let i=0;i<25;i++)await Promise.resolve();};
const response=j=>({json:()=>Promise.resolve(j)});
function setup(options={}){
 let mode=options.helper||'chatgpt',scope='',seq=0,input={value:'Discuss blue and gold.'},pendingInbox,pendingDocument;
 const inbox=[],shown=[],timers=new Map(),statuses=[],polls=[];let timerSeq=0;
 const w={crypto:require('node:crypto').webcrypto,spbProAI:{refresh(){},_push(e){shown.push(e);},log:()=>shown,_cards:()=>[{name:'Satin',hex:'#aa8844'}]}};
 const c={window:w,console,Promise,_panel:{querySelector:s=>s==='.spb-pai-input'?input:null},_log:[],_relaySending:false,_composerHeldDraft:false,composerSync(){},render(){input={value:input.value};},localStorage:{getItem:()=>mode,setItem:(k,v)=>{mode=v;}},document:{readyState:'loading',addEventListener(){},createElement:()=>({}),head:{appendChild(){}}},
  setTimeout(fn,ms){const id=++timerSeq;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id),setInterval(){},
  fetch(url,opt){
   if(url==='/api/mcp/document'){const b=JSON.parse(opt.body);scope=b.page+':'+b.epoch;const j={ok:true,document_scope:scope,seq};if(options.holdDocument)return new Promise(resolve=>{pendingDocument=()=>resolve(response(j));});return Promise.resolve(response(j));}
   if(url.startsWith('/api/mcp/status')){if(options.holdStatus)return new Promise(resolve=>statuses.push(j=>resolve(response(j))));return Promise.resolve(response({ok:true,enabled:true,listening:false,client:''}));}
   if(url.startsWith('/api/mcp/chat'))return new Promise(resolve=>polls.push(j=>resolve(response(j))));
   if(url==='/api/mcp/inbox'){inbox.push(JSON.parse(opt.body));return new Promise((resolve,reject)=>{pendingInbox={accept:j=>resolve(response(j||{ok:true,seq:++seq,listening:false})),reject};});}
   throw Error(url);
  }};
 vm.createContext(c);vm.runInContext(connector,c);c.SpbAiConnect=w.SpbAiConnect;
 vm.runInContext('function sendBranch(text){'+branch+'}',c);
 return {c,A:w.SpbAiConnect,inbox,shown,polls,statuses,get input(){return input;},send:t=>c.sendBranch(t||'Discuss blue and gold.'),accept:j=>pendingInbox.accept(j),reject:()=>pendingInbox.reject(new Error('Local connection dropped')),document:()=>pendingDocument(),timeout(){const t=[...timers.values()].find(t=>t.ms===15000);assert.ok(t);t.fn();},draft:s=>{input.value=s;}};
}
(async()=>{
 let s,p;
 for(const helper of ['chatgpt','claude']){s=setup({helper});p=s.send();await tick();assert.equal(s.input.value,'Discuss blue and gold.');assert.equal(s.c._relaySending,true);assert.equal(s.inbox.length,1);assert.equal(s.inbox[0].helper,helper);assert.equal(s.send(),undefined,'Duplicate Send suppressed during delivery');s.accept();assert.equal((await p).ok,true);assert.equal(s.input.value,'');assert.equal(s.c._relaySending,false);}
 for(const kind of ['rejected','no-sequence','network']){s=setup();p=s.send();await tick();if(kind==='network')s.reject();else s.accept(kind==='rejected'?{ok:false,message:'No current document'}:{ok:true,listening:false});const r=await p;assert.equal(r.ok,false);assert.equal(s.input.value,'Discuss blue and gold.');assert.equal(s.c._relaySending,false);assert.equal(s.inbox.length,1,'No retry');}
 s=setup();p=s.send();await tick();s.draft('Keep the number readable.');s.accept();await p;assert.equal(s.input.value,'Keep the number readable.','Newly typed follow-up retained');assert.equal(s.c._composerHeldDraft,true);
 s=setup();s.draft('My unsent separate question');p=s.send('Use satin gold');await tick();s.accept();await p;assert.equal(s.input.value,'My unsent separate question','A card/data-say request cannot clear an unrelated draft');
 for(const change of ['source','provider']){s=setup();p=s.send();await tick();if(change==='source')s.A._sourceChanged();else s.A.click('aic-offline');await tick();s.accept();const r=await p;assert.equal(r.ok,false);assert.equal(s.input.value,'Discuss blue and gold.');assert.equal(s.inbox.length,1);}
 s=setup();p=s.send();await tick();s.timeout();assert.equal((await p).ok,false);assert.equal(s.input.value,'Discuss blue and gold.');s.accept();await tick();assert.equal(s.input.value,'Discuss blue and gold.','Late receipt cannot clear timed-out draft');assert.equal(s.inbox.length,1);
 s=setup({holdDocument:true});p=s.send();await tick();s.timeout();assert.equal((await p).ok,false);s.document();await tick();assert.equal(s.inbox.length,0,'Late document registration cannot send timed-out text');assert.equal(s.input.value,'Discuss blue and gold.');
 s=setup({holdStatus:true});p=s.A.refresh();await tick();s.A._sourceChanged();await tick();s.statuses[0]({ok:true,enabled:true,listening:true,client:'codex-old-document'});assert.equal(await p,null,'Stale status cannot claim current connectivity');
 s=setup();p=s.send();await tick();s.accept();await p;
 s.polls[0]({ok:true,entries:[{seq:4,role:'assistant',text:'Choose satin',finishes:[{key:'base::satin'}]}],listening:true,client:'codex-test'});await tick();const card=s.shown.find(e=>e.text==='Choose satin');assert.ok(card);card.id='visible-finish-message';
 const prior=s.inbox.length;s.A.click('aic-more',{getAttribute:()=>card.id});await tick();assert.equal(s.inbox.length,prior+1,'Current Show more sends one question');s.A.click('aic-more',{getAttribute:()=>card.id});s.A.useCard(card,0);await tick();assert.equal(s.inbox.length,prior+1,'Card clicks cannot race another inbox delivery');s.accept();await tick();
 s.A.click('aic-offline');const n=s.inbox.length,users=s.shown.filter(e=>e.role==='user').length;s.A.useCard(card,0);await tick();assert.equal(s.inbox.length,n);assert.equal(s.shown.filter(e=>e.role==='user').length,users,'Old connected card cannot send through Offline');
 s.A.click('aic-more',{getAttribute:()=>card.id});await tick();assert.equal(s.inbox.length,n,'Old Show more card cannot send through Offline');
 s.A.click('aic-claude');s.A.useCard(card,0);s.A.click('aic-more',{getAttribute:()=>card.id});await tick();assert.equal(s.inbox.length,n,'Other-provider card cannot send to the current helper even without a bridge');
 s.A.click('aic-chatgpt');await tick();s.A.useCard(card,0);s.A.click('aic-more',{getAttribute:()=>card.id});await tick();assert.equal(s.inbox.length,n,'Switching back cannot revive an old provider card without a bridge');
 assert.ok(editor.includes('data-act="aic-more" data-id="\' + m.id + \'">Show me more'),'Actual render binds More to its exact entry');
 console.log(JSON.stringify({pass:true,providers_acknowledged:2,actual_generated_send_branch:true,acknowledged_only_clear:true,failed_and_changed_scope_drafts:'retained',new_and_unrelated_drafts:'retained',delivery_timeout_ms:15000,late_registration_sends:0,automatic_retries:0,stale_status:'ignored',offline_card_and_more:'inert'}));
})().catch(e=>{console.error(e);process.exitCode=1;});
