'use strict';
// Controlled MCP transport fixture, not a language-model conversation. No edit
// is allowed to reach the page; advice guard is tested with a refused write.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process'),readline=require('node:readline');
const root=path.resolve(__dirname,'../..'),state=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(state,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map(),receipt={kind:'MCP transport fixture; no model inference',started:new Date().toISOString()};
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){let line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const r=JSON.parse(line),resolve=pending.get(r.id);if(resolve){pending.delete(r.id);resolve(r);}}catch{}}});child.stderr.on('data',()=>{});
const input=readline.createInterface({input:process.stdin});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n');});}
async function call(name,args){const r=await rpc('tools/call',{name,arguments:args});assert.ok(r.result,r.error&&JSON.stringify(r.error));return r.result;}
function data(r){return JSON.parse(r.content[0].text);}
const timer=setTimeout(()=>{child.kill();input.close();console.error('Probe bounded timeout');process.exit(1);},300000);
(async()=>{
 await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-relay-scope-fixture',version:'1'}});
 const listed=(await rpc('tools/list',{})).result.tools;assert.ok(listed.find(t=>t.name==='spb_reply').inputSchema.properties.reply_to);
 console.log('WAITING: send the advice-only fixture from the private ChatGPT panel.');
 const first=data(await call('spb_wait_for_message',{timeout_s:170}));assert.ok(first.messages&&first.messages.length);
 const old=first.messages.at(-1);assert.ok(old.document_scope);assert.equal(first.request_intent.mutation_allowed,false);
 const rejected=await call('spb_reset_zones',{});assert.equal(rejected.isError,true);assert.match(rejected.content[0].text,/advice only/);
 const a=await call('spb_get_state',{});assert.ok(!a.isError);receipt.a={seq:old.seq,scope:old.document_scope,state:data(a),advice_write_refused:rejected};
 console.log('A READ PASS; ADVICE WRITE REFUSED. Switch to fixture B, then enter continue in this probe.');
 await new Promise(resolve=>input.once('line',resolve));
 const oldReply=await call('spb_reply',{reply_to:old.seq,text:'OLD FIXTURE A RESPONSE MUST NEVER APPEAR',finishes:[{key:'base::satin'}]});assert.equal(oldReply.isError,true);
 const oldRead=await call('spb_get_state',{});assert.equal(oldRead.isError,true);receipt.stale={reply:oldReply,read:oldRead};
 console.log('OLD REPLY AND OLD TOOL SCOPE REFUSED. Send a fresh question from fixture B.');
 const second=data(await call('spb_wait_for_message',{timeout_s:170}));assert.ok(second.messages&&second.messages.length);const fresh=second.messages.at(-1);assert.notEqual(fresh.document_scope,old.document_scope);
 const b=await call('spb_get_state',{});assert.ok(!b.isError);receipt.b={seq:fresh.seq,scope:fresh.document_scope,state:data(b)};
 const reply=await call('spb_reply',{reply_to:fresh.seq,text:'Private transport test: this reply belongs to the newly opened paint. No model inference or paint edit ran.'});assert.ok(!reply.isError);receipt.fresh_reply=data(reply);
 receipt.finished=new Date().toISOString();const file='native-relay-scope-'+receipt.finished.replace(/[:.]/g,'-')+'.json';fs.writeFileSync(path.join(state,file),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
 console.log('PASS native+MCP scoped relay; receipt '+file);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{clearTimeout(timer);input.close();child.stdin.end();child.kill();});
