'use strict';
// One explicitly scoped private test edit; no model, save, export or replay.
const {spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const E=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
assert.equal(JSON.parse(fs.readFileSync(path.join(E,'server.json'),'utf8')).port,59910);
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(E,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let seq=0,buffer='';const pending=new Map();
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const r=JSON.parse(line);if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id);}}catch{}}});
child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const id=++seq;pending.set(id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
const evidence={started:new Date().toISOString(),port:59910,model_inference:false,calls:[]};
async function call(name,args){const r=(await rpc('tools/call',{name,arguments:args})).result;assert.ok(r&&!r.isError,JSON.stringify(r));const blocks=(r.content||[]).filter(c=>c.type==='text');const text=blocks.map(c=>c.text).join('\n');evidence.calls.push({tool:name,args,text});for(const block of blocks){try{return JSON.parse(block.text);}catch{}}throw Error('Tool returned no structured JSON text: '+name);}
const timer=setTimeout(()=>{child.kill();console.error('Timed out; do not retry the edit without reading current state.');process.exitCode=1;},60000);
(async()=>{
 await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-measurement-notice-acceptance',version:'1'}});
 const s=await call('spb_get_state',{});
 assert.equal(s.template_identity.source_paint_name,'ARCA Chevy SS.tga');assert.equal(s.layers.length,42);assert.equal(s.zones.length,5);
 const layer=s.layers.find(l=>l.id==='psd_0');assert.equal(layer.group,'Paintable Area');assert.equal(layer.name,'Base Paint');assert.ok(!layer.colour_overlay?.enabled);
 const applied=await call('spb_edit_layer',{layer:'Paintable Area / Base Paint',colour:'#101010'});
 const checked=await call('spb_check',{fresh:false});
 assert.deepEqual(checked.measured.scope.layers,['psd_0']);assert.ok(checked.measured.line);
 const fresh=await call('spb_check',{fresh:true});
 assert.deepEqual(fresh.measured.scope.layers,checked.measured.scope.layers);
 assert.deepEqual(fresh.measured.scope.parts,[]);
 assert.equal(fresh.measured.decal_px,checked.measured.decal_px);
 assert.ok(!fresh.measured.findings.some(f=>/unasked-whole/.test(f)));
 evidence.fresh_scope_preserved=true;
 evidence.finished=new Date().toISOString();const file='native-measurement-notice-'+evidence.started.replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(E,file),JSON.stringify(evidence,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({receipt:file,applied:applied.applied,measured:checked.measured,undo:checked.undo}));
})().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill();});
