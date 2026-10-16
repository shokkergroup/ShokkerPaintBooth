'use strict';
// Private native lifecycle probe: hold one real chat message across a native Open.
// No model inference. A stale edit must be refused before reaching the new project.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const stamp=new Date().toISOString().replace(/[:.]/g,'-');
const prefix='document-change-'+stamp,ready=path.join(dir,prefix+'-ready.json'),go=path.join(dir,prefix+'-continue');
const runtime=JSON.parse(fs.readFileSync(path.join(dir,'server.json'),'utf8'));
assert.equal(runtime.port,59910);assert.equal(runtime.host,'127.0.0.1');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{
 env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map(),calls=[];
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const r=JSON.parse(line),accept=pending.get(r.id);if(accept){pending.delete(r.id);accept(r);}}catch{}}});
child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n');});}
async function call(tool,args){const raw=await rpc('tools/call',{name:tool,arguments:args});const result=raw.result;calls.push({tool,args,result,error:raw.error});assert.ok(result,JSON.stringify(raw));return result;}
function textOf(result){return (result.content||[]).filter(c=>c.type==='text').map(c=>c.text).join('\n');}
const timeout=setTimeout(()=>{child.kill();console.error('Lifecycle probe expired; no late edit sent.');process.exit(1);},480000);
(async()=>{
 await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-document-change-acceptance',version:'1'}});
 console.log('Waiting for one native ChatGPT-mode test request.');
 const incoming=await call('spb_wait_for_message',{timeout_s:170});assert.ok(!incoming.isError,textOf(incoming));
 const msg=JSON.parse(textOf(incoming)),buyer=msg.messages?.at(-1);
 assert.ok(buyer?.document_scope && buyer.text.includes('DOCUMENT-SWITCH TEST'), 'Use the designated private fixture request only.');
 console.log('Native message received; reading its bound document before Open.');
 const state=await call('spb_get_state',{});assert.ok(!state.isError,textOf(state));
 const actual=JSON.parse(textOf(state));assert.equal(actual.layers.length,42);
 assert.ok(actual.layers.some(l=>l.id==='psd_0'&&l.name==='Base Paint'&&l.group==='Paintable Area'));
 fs.writeFileSync(ready,JSON.stringify({schema:'spb-native-document-change-ready/1',origin_scope:buyer.document_scope,buyer_seq:buyer.seq,continue_file:go,receipt:prefix+'.json'},null,2)+'\n',{flag:'wx'});
 console.log('Captured request and original42-layer document. Native Open may now replace the private project.');
 console.log('Continue file: '+go);
 while(!fs.existsSync(go))await new Promise(r=>setTimeout(r,500));
 const edit=await call('spb_edit_layer',{layer:'psd_0',colour:'#224466',buyer_said:buyer.text});
 assert.ok(edit.isError,'A stale edit unexpectedly succeeded. Inspect and Undo in the private fixture.');
 assert.match(textOf(edit),/paint changed|document.*changed|fresh buyer message/i);
 const reply=await call('spb_reply',{reply_to:buyer.seq,text:'This old-document response must never appear in the newly opened project.'});
 assert.ok(reply.isError,'A stale reply unexpectedly appeared in the new project.');
 const output={schema:'spb-native-document-change/1',started:stamp,finished:new Date().toISOString(),privateRuntime:runtime,candidateManifest:JSON.parse(fs.readFileSync(path.join(__dirname,'candidates/sources.json'),'utf8')),
  origin_scope:buyer.document_scope,stale_edit_refused:true,stale_reply_refused:true,calls,
  limits:['Native chat/Open/MCP boundary proof; no provider inference and no automatic raw-layer pixel verification.']};
 fs.writeFileSync(path.join(dir,prefix+'.json'),JSON.stringify(output,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({pass:true,receipt:prefix+'.json',stale_edit_refused:true,stale_reply_refused:true}));
})().catch(e=>{fs.writeFileSync(path.join(dir,prefix+'-failed.json'),JSON.stringify({error:e.message,calls},null,2)+'\n');console.error(e.message);process.exitCode=1;}).finally(()=>{clearTimeout(timeout);child.stdin.end();child.kill();});
