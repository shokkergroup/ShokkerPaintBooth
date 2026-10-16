'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
let mode='chatgpt',activeScope='',seq=0;
const polls=[],inbox=[],shown=[];
const response=j=>({json:()=>Promise.resolve(j)});
const w={crypto:require('node:crypto').webcrypto,
 spbProAI:{refresh(){},_push(e){shown.push(e);},_cards:()=>[{name:'Satin',hex:'#aa8844'}]}};
const context={window:w,localStorage:{getItem:()=>mode,setItem:(k,v)=>mode=v},
 document:{readyState:'loading',addEventListener(){},createElement:()=>({}),head:{appendChild(){}}},
 setTimeout(){},clearTimeout(){},setInterval(){},fetch(url,opt){
  if(url==='/api/mcp/document') {const b=JSON.parse(opt.body);activeScope=b.page+':'+b.epoch;return Promise.resolve(response({ok:true,document_scope:activeScope,seq}));}
  if(url.startsWith('/api/mcp/status'))return Promise.resolve(response({ok:true,enabled:true,listening:true,client:'codex-test'}));
  if(url.startsWith('/api/mcp/chat'))return new Promise(resolve=>polls.push({url,finish:j=>resolve(response(j))}));
  if(url==='/api/mcp/inbox'){const b=JSON.parse(opt.body);inbox.push(b);return Promise.resolve(response({ok:b.document_scope===activeScope,seq:++seq,listening:true}));}
  throw Error('Unexpected request '+url);
 }};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates/spb-ai-connect.js'),'utf8'),context);
const A=w.SpbAiConnect,tick=async()=>{for(let i=0;i<15;i++)await Promise.resolve();};
(async()=>{
 await A.relay('Discuss blue and gold. Advice only.');await tick();
 assert.equal(inbox.length,1);const oldScope=inbox[0].document_scope;
 assert.equal(oldScope,activeScope);assert.ok(polls.length);const oldPoll=polls.shift();
 A._sourceChanged();await tick();assert.notEqual(activeScope,oldScope);
 oldPoll.finish({ok:true,entries:[{seq:2,role:'assistant',text:'OLD PAINT REPLY',finishes:[{key:'base::satin'}]}],client:'codex-test',listening:true});
 await tick();assert.ok(!shown.some(x=>x.text==='OLD PAINT REPLY'));
 await A.relay('Discuss the red paint.');await tick();
 assert.equal(inbox[1].document_scope,activeScope);assert.equal(inbox[1].text,'Discuss the red paint.');
 const freshPoll=polls.shift();assert.ok(freshPoll.url.includes(encodeURIComponent(activeScope)));
 freshPoll.finish({ok:true,entries:[{seq:3,role:'assistant',text:'CURRENT PAINT REPLY',finishes:[{key:'base::satin'}]}],client:'codex-test',listening:true});
 await tick();const card=shown.find(x=>x.text==='CURRENT PAINT REPLY');assert.ok(card);assert.equal(card.documentScope,activeScope);
 A._sourceChanged();await tick();const before=inbox.length;A.useCard(card,0);await tick();assert.equal(inbox.length,before,'An old Use card cannot compose a new edit request after a document change');
 console.log('PASS actual relay: registration precedes send, source change scopes the next message, stale long-poll reply/card rejected, fresh reply shown, expired Use card inert');
})().catch(e=>{console.error(e);process.exitCode=1;});
