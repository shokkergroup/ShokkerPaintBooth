'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),state=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(state,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map();
const timer=setTimeout(()=>{child.kill();console.error('Car reference MCP probe timed out');process.exitCode=1},55000);
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let r;try{r=JSON.parse(line)}catch{continue}const resolve=pending.get(r.id);if(resolve){pending.delete(r.id);resolve(r)}}});
child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n')})}
async function call(name,args){const response=await rpc('tools/call',{name,arguments:args});assert.ok(response.result&&!response.result.isError,JSON.stringify(response.error||response.result));return JSON.parse(response.result.content[0].text);}
(async()=>{
 assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-legacy-geometry-read-probe',version:'1'}})).result);
 const listing=await rpc('tools/list',{});
 if(process.argv.includes('--baseline'))assert.ok(!listing.result.tools.some(t=>/Library recognition is heuristic/.test(t.description)),'Baseline capture requires the unqualified candidate; do not relabel guarded responses');
 const calls=[];for(const name of ['spb_status','spb_get_state','spb_get_car_map']){const data=await call(name,{});calls.push({tool:name,data});}
 if(!process.argv.includes('--baseline'))for(const c of calls){
  assert.equal(c.data.library_parts_withheld,8);assert.ok(c.data.parts_needing_confirmation.includes('hood'));
  assert.ok(!c.data.parts||!c.data.parts.length);assert.ok(!c.data.car||!c.data.car.parts||!c.data.car.parts.length);
  assert.match(listing.result.tools.find(t=>t.name===c.tool).description,/Library recognition is heuristic/);
 }
 const result={checked_at:new Date().toISOString(),calls,tool_descriptions:listing.result.tools.filter(t=>calls.some(c=>c.tool===t.name))};
 const name='legacy-geometry-'+(process.argv.includes('--baseline')?'baseline-':'qualified-')+result.checked_at.replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(state,name),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({receipt:name,calls:calls.map(c=>({tool:c.tool,keys:Object.keys(c.data),car_type:typeof c.data.car,car_keys:c.data.car&&typeof c.data.car==='object'?Object.keys(c.data.car):[],part_count:Array.isArray(c.data.parts)?c.data.parts.length:null}))}));
})().catch(e=>{console.error(e.message);process.exitCode=1}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill()});
