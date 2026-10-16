'use strict';
// Read-only native MCP state receipt. No model, edits, renders or project saves.
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910'),label=process.argv[2];
if(!label||!/^[a-z0-9-]{1,80}$/.test(label))throw Error('Provide a short receipt label');
if(JSON.parse(fs.readFileSync(path.join(dir,'server.json'),'utf8')).port!==59910)throw Error('Private port mismatch');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buf='';const waiting=new Map();
child.stdout.setEncoding('utf8');child.stdout.on('data',s=>{buf+=s;let i;while((i=buf.indexOf('\n'))>=0){const line=buf.slice(0,i);buf=buf.slice(i+1);try{const r=JSON.parse(line);if(waiting.has(r.id)){waiting.get(r.id)(r);waiting.delete(r.id);}}catch{}}});child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{waiting.set(++id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
const timer=setTimeout(()=>{console.error('Read-only snapshot timed out; no edits attempted');child.kill();process.exitCode=1;},45000);
(async()=>{
 await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-private-state-receipt',version:'1'}});
 const r=(await rpc('tools/call',{name:'spb_get_state',arguments:{}})).result;
 if(!r||r.isError)throw Error('Native state unavailable: '+(r&&r.content||[]).filter(b=>b.type==='text').map(b=>b.text).join(' ').slice(0,500));
 const text=(r.content||[]).filter(b=>b.type==='text').map(b=>b.text).join('\n'),state=JSON.parse(text);
 const file=label+'-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(dir,file),JSON.stringify({at:new Date().toISOString(),port:59910,read_only:true,state},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({file,layers:(state.layers||[]).length,zones:(state.zones||[]).length}));
})().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill();});
