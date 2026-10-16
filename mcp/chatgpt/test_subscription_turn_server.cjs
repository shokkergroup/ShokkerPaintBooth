'use strict';
// Actual MCP protocol boundary: disabled tools cannot bypass CLI allow-listing.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910'),journal=path.join(dir,'subscription-pending.json');
assert.ok(fs.existsSync(journal),'Run the actual bounded listener checkpoint proof first.');
const pendingBatch=JSON.parse(fs.readFileSync(journal,'utf8'));
const child=spawn(process.execPath,[path.join(__dirname,'subscription-turn-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt'),SPB_SUBSCRIPTION_HANDOFF:journal},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buf='';const requests=new Map();
child.stdout.setEncoding('utf8');child.stdout.on('data',c=>{buf+=c;let i;while((i=buf.indexOf('\n'))>=0){let r;try{r=JSON.parse(buf.slice(0,i));}catch{}buf=buf.slice(i+1);if(r&&requests.has(r.id)){requests.get(r.id)(r);requests.delete(r.id);}}});child.stderr.on('data',()=>{});
const timer=setTimeout(()=>{child.kill();console.error('Worker boundary test timeout');process.exit(1);},20000);
const rpc=(method,params)=>new Promise(resolve=>{const next=++id;requests.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n');});
(async()=>{
 assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-worker-boundary-test',version:'1'}})).result);
 const names=(await rpc('tools/list',{})).result.tools.map(t=>t.name).sort();assert.deepEqual(names,['spb_assistant_context','spb_reply','spb_wait_for_message'].sort());
 for(const name of ['spb_do','spb_edit_layer','spb_undo','spb_render']){const r=await rpc('tools/call',{name,arguments:{text:'Paint body red',confirm:true}});assert.equal(r.error.code,-32602);assert.match(r.error.message,/unavailable tool/);}
 const r=await rpc('tools/call',{name:'spb_reply',arguments:{text:'Wrong receipt',reply_to:pendingBatch.messages.at(-1).seq+1}});assert.equal(r.error.code,-32602);assert.match(r.error.message,/exact claimed batch/);
 for(const [name,arguments_] of [['spb_assistant_context',{query:pendingBatch.messages.at(-1).text,include_paint:true}],['spb_reply',{text:'No context',reply_to:pendingBatch.messages.at(-1).seq}]]){
  const out=await rpc('tools/call',{name,arguments:arguments_});assert.equal(out.error.code,-32602);assert.match(out.error.message,/scoped handoff/);
 }
 console.log('PASS actual worker MCP: exactly3 tools advertised; do/edit/undo/render rejected at request boundary; mismatched reply and context/reply without handoff rejected.');
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill();});
