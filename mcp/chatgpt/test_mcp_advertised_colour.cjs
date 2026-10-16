'use strict';
// Query real JSON-RPC servers. No inference and no tools/call requests.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
async function list(file){
 const child=spawn(process.execPath,[file],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
 let id=0,buffer='';const pending=new Map();
 child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const r=JSON.parse(line);if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id);}}catch{}}});child.stderr.on('data',()=>{});
 function rpc(method,params){return new Promise((resolve,reject)=>{const n=++id,t=setTimeout(()=>{pending.delete(n);reject(Error('MCP schema query timed out'));},10000);pending.set(n,r=>{clearTimeout(t);resolve(r);});child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:n,method,params})+'\n');});}
 try {
  const init=await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'spb-schema-acceptance',version:'1'}});assert.ok(init.result);
  const r=await rpc('tools/list',{});assert.ok(Array.isArray(r.result?.tools));return {tools:r.result.tools,instructions:init.result.instructions};
 } finally {child.stdin.end();child.kill();}
}
(async()=>{
 const [candidate,shared]=await Promise.all([list(path.join(__dirname,'candidate-server.cjs')),list(path.join(root,'mcp/server/index.js'))]);
 function report(server){const tools=server.tools,layer=tools.find(t=>t.name==='spb_edit_layer'),p=layer?.inputSchema?.properties||{};return {tool_count:tools.length,has_layer_tool:!!layer,native_colour:!!p.colour,source_colour:!!p.source_colour,inspect_layer:tools.some(t=>t.name==='spb_inspect_layer'),online_kits:tools.some(t=>t.name==='spb_kit'),fixed_2048_template_claim:/ONE flat 2048x2048/.test(server.instructions||'')};}
 const result={at:new Date().toISOString(),method:'Actual MCP initialize and tools/list; zero tools/call and no inference',candidate:report(candidate),shared:report(shared)};
 assert.equal(result.candidate.native_colour,true);assert.equal(result.candidate.source_colour,true);assert.equal(result.candidate.inspect_layer,true);
 const t=candidate.tools.find(x=>x.name==='spb_edit_layer');assert.equal(t.inputSchema.properties.colour.pattern,'^#[0-9a-fA-F]{6}$');assert.equal(t.inputSchema.properties.replace_tolerance.maximum,255);
 assert.equal(result.candidate.fixed_2048_template_claim,false);assert.match(candidate.instructions,/Resolution, panel layout and available parts vary/);assert.match(candidate.instructions,/never infer coordinates from a car name/);
 fs.writeFileSync(path.join(dir,'advertised-colour-acceptance.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1;});
