'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
function setup(){
 const store=new Map(),claims=[],enabled=[];
 const w={crypto:{randomUUID:()=> '12345678-1234-1234-1234-123456789abc'},SpbMcpBridge:{setEnabled:x=>enabled.push(x)}};
 const c={window:w,localStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)},document:{readyState:'loading',addEventListener(){}},Promise,Error,JSON,String,encodeURIComponent,setTimeout(){},setInterval(){},fetch(url,opt){
  if(url==='/api/mcp/document')return new Promise(resolve=>claims.push({body:JSON.parse(opt.body),resolve}));
  if(url.startsWith('/api/mcp/status'))return Promise.resolve({json:()=>Promise.resolve({ok:true,enabled:true})});
  return new Promise(()=>{});
 }};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates/spb-ai-connect.js'),'utf8'),c);
 const accept=i=>{const x=claims[i];x.resolve({json:()=>Promise.resolve({ok:true,document_scope:x.body.page+':'+x.body.epoch,seq:0})});};
 return {api:w.SpbAiConnect,claims,enabled,accept};
}
(async()=>{
 const s=setup();s.api.setMode('chatgpt');assert.deepEqual(s.enabled,[false]);assert.equal(s.claims[0].body.epoch,1);
 s.accept(0);await flush();assert.deepEqual(s.enabled,[false,true]);
 s.api.setMode('claude');assert.equal(s.claims[1].body.epoch,2);s.api.setMode('offline');s.accept(1);await flush();
 assert.deepEqual(s.enabled,[false,true,false],'late registration must not enable a provider the user left');
 s.api.setMode('chatgpt');s.api.setMode('claude');s.accept(2);await flush();assert.equal(s.enabled.at(-1),false);
 s.accept(3);await flush();assert.equal(s.enabled.at(-1),true);assert.equal(s.api.mode(),'claude');
 console.log('PASS explicit document reclaim precedes polling; stale provider/scope completions cannot enable it');
})().catch(e=>{console.error(e);process.exitCode=1});
