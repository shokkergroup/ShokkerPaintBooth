'use strict';
// One guarded synthetic-fixture MCP edit. No inference, full render or export.
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
assert.equal(JSON.parse(fs.readFileSync(path.join(dir,'server.json'),'utf8')).port,59910);
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buf='';const waiting=new Map(),record={started:new Date().toISOString(),port:59910,model_inference:false,calls:[]};
child.stdout.setEncoding('utf8');child.stdout.on('data',s=>{buf+=s;let i;while((i=buf.indexOf('\n'))>=0){const line=buf.slice(0,i);buf=buf.slice(i+1);try{const r=JSON.parse(line);if(waiting.has(r.id)){waiting.get(r.id)(r);waiting.delete(r.id);}}catch{}}});child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{waiting.set(++id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
async function call(tool,args){const r=(await rpc('tools/call',{name:tool,arguments:args})).result;const text=(r?.content||[]).filter(b=>b.type==='text').map(b=>b.text).join('\n');record.calls.push({tool,args,text,isError:!!r?.isError});assert.ok(r&&!r.isError,text);for(const b of r.content||[]){if(b.type==='text')try{return JSON.parse(b.text);}catch{}}throw Error('No JSON result');}
const timer=setTimeout(()=>{record.error='Timed out: inspect current state before any repeat edit';finish();process.exitCode=1;},60000);
let finished=false;function finish(){if(finished)return;finished=true;clearTimeout(timer);record.finished=new Date().toISOString();const name='frame-native-colour-'+record.started.replace(/[:.]/g,'-')+'.json';fs.writeFileSync(path.join(dir,name),JSON.stringify(record,null,2)+'\n',{flag:'wx'});child.stdin.end();child.kill();console.log(JSON.stringify({receipt:name,pass:record.pass,error:record.error}));}
(async()=>{
 await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-frame-native-colour-acceptance',version:'1'}});
 const before=await call('spb_get_state',{});assert.equal(before.layers.length,3);assert.equal(before.zones.length,5);assert.deepEqual(before.layers.map(l=>l.name),['Body','Numbers','Sponsors']);assert.equal(before.layers[0].id,'psd_0');assert.ok(!before.layers[0].locked&&!before.layers[0].colour_overlay?.enabled);
 const args={text:'Make only the Body layer #B49A55. Keep the Numbers and Sponsors layers exactly unchanged.',frame:{v:1,act:'change',decals:'protect',ops:[{verb:'recolour',target:{kind:'layer',layers:['psd_0']},look:{colour:{hex:'#B49A55'}}}]}};
 const dry=await call('spb_do',{...args,dry_run:true});assert.match(dry.applied_as,/native layer colour/);assert.equal(dry.changed,false);
 const edit=await call('spb_do',args);assert.equal(edit.changed,true);assert.match(edit.applied_as,/native layer colour/);
 const after=await call('spb_get_state',{});assert.equal(after.zones.length,5);assert.equal(after.layers[0].colour_overlay.colour,'#b49a55');assert.deepEqual(after.layers.slice(1),before.layers.slice(1));
 const checked=await call('spb_check',{fresh:false});record.measured=checked.measured;record.pass=true;
})().catch(e=>{record.error=e.message;process.exitCode=1;}).finally(finish);
