'use strict';
// Native in-app acceptance: one persistent MCP client, private 59910 only.
// No model/API invocation. Commands are explicit JSON on this process's stdin.
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path'),readline=require('node:readline');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
if(JSON.parse(fs.readFileSync(path.join(dir,'server.json'),'utf8')).port!==59910)throw Error('Private port mismatch');
const allowed=new Set(['spb_wait_for_message','spb_assistant_context','spb_get_state','spb_reply','spb_find_finishes','spb_finish_details','spb_edit_zone','spb_do','spb_tweak','spb_undo','spb_render','describe_tools']);
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let serial=0,buf='',queue=Promise.resolve();const waiting=new Map();
child.stdout.setEncoding('utf8');child.stdout.on('data',s=>{buf+=s;let i;while((i=buf.indexOf('\n'))>=0){const line=buf.slice(0,i);buf=buf.slice(i+1);try{const r=JSON.parse(line),entry=waiting.get(r.id);if(entry){clearTimeout(entry.timer);waiting.delete(r.id);entry.resolve(r);}}catch{}}});
child.stderr.on('data',()=>{});
child.on('exit',(code)=>{console.log(JSON.stringify({mcp_terminal:true,code}));for(const entry of waiting.values()){clearTimeout(entry.timer);entry.reject(Error('MCP process exited'));}waiting.clear();});
function rpc(method,params){return new Promise((resolve,reject)=>{const id=++serial,timer=setTimeout(()=>{waiting.delete(id);reject(Error('MCP response observation timed out; inspect the existing process before retrying'));},70000);waiting.set(id,{resolve,reject,timer});child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
const initialized=rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-private-native-chat',version:'1'}}).then(r=>{if(r.error)throw Error('Initialize failed');console.log(JSON.stringify({ready:true,port:59910,persistent_client:true,no_api_calls:true}));});
const input=readline.createInterface({input:process.stdin});
input.on('line',line=>{queue=queue.then(async()=>{
 const command=JSON.parse(line);if(!allowed.has(command.tool)||!/^[a-z0-9-]{1,80}$/.test(command.label||''))throw Error('Tool or receipt label is not allowed');
 if(command.tool==='spb_wait_for_message' && Number(command.arguments?.timeout_s)>45)throw Error('Use a bounded wait');
 await initialized;
 const result=command.tool==='describe_tools'?{tools:((await rpc('tools/list',{})).result?.tools||[]).filter(t=>Array.isArray(command.arguments?.names)&&command.arguments.names.includes(t.name)&&allowed.has(t.name))}:(await rpc('tools/call',{name:command.tool,arguments:command.arguments||{}})).result;
 const file=command.label+'-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(dir,file),JSON.stringify({at:new Date().toISOString(),port:59910,tool:command.tool,arguments:command.arguments||{},result},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({receipt:file,tool:command.tool,isError:!!result?.isError,textBlocks:(result?.content||[]).filter(x=>x.type==='text').length}));
}).catch(e=>console.error(JSON.stringify({error:e.message})));});
input.on('close',()=>queue.finally(()=>{child.stdin.end();child.kill();}));
process.on('SIGINT',()=>{input.close();child.kill();process.exit(0);});
