'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),state=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(state,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map();
const timer=setTimeout(()=>{child.kill();console.error('Context probe timed out');process.exitCode=1},60000);
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let r;try{r=JSON.parse(line)}catch{continue}const resolve=pending.get(r.id);if(resolve){pending.delete(r.id);resolve(r)}}});
child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n')})}
(async()=>{
  const init=await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-context-probe',version:'1'}});assert.ok(init.result);
  const list=await rpc('tools/list',{});assert.equal(list.result.tools.find(t=>t.name==='spb_assistant_context').annotations.readOnlyHint,true);
  const response=await rpc('tools/call',{name:'spb_assistant_context',arguments:{query:'matte black satin gold no glitter readable numbers',include_paint:true}});
  assert.ok(response.result&&!response.result.isError,JSON.stringify(response.error||response.result));
  const packet=JSON.parse(response.result.content[0].text);
  assert.equal(packet.schema,'spb-assistant-context/1');assert.equal(packet.paint.status.available,true);assert.equal(packet.paint.state.available,true);assert.equal(packet.conversation.available,true);
  fs.writeFileSync(path.join(state,'context-client-probe.json'),JSON.stringify(packet,null,2)+'\n');
  console.log(JSON.stringify({tools:packet.capabilities.length,history_turns:packet.conversation.turns.length,articles:packet.knowledge.data?.articles?.length,paint_available:true,characters:response.result.content[0].text.length}));
})().catch(e=>{console.error(e.message);process.exitCode=1}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill()});
