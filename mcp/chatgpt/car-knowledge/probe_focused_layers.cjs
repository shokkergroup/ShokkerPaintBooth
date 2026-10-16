'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn}=require('node:child_process'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'../candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let seq=0,buffer='';const pending=new Map();
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let n;while((n=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,n);buffer=buffer.slice(n+1);let r;try{r=JSON.parse(line);}catch{continue;}const p=pending.get(r.id);if(p){pending.delete(r.id);p.resolve(r);}}});
child.stderr.on('data',()=>{});
const timer=setTimeout(()=>{for(const p of pending.values())p.reject(new Error('Local read probe timed out'));child.kill();},55000);
function rpc(method,params){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
async function call(name,args){const r=await rpc('tools/call',{name,arguments:args});assert.ok(r.result&&!r.result.isError,JSON.stringify(r.error||r.result));return JSON.parse(r.result.content[0].text);}
const keys=['layers','zones','selected_zone','paint_colours','pending_changes','recent_changes','saved_design_brief','convo','template_identity'];
const select=s=>Object.fromEntries(keys.map(k=>[k,s[k]===undefined?null:s[k]]));
const fixtureDir=path.join(root,'_release_evidence/chatgpt-dev/59910/projects');
function fixtures(){return Object.fromEntries(fs.readdirSync(fixtureDir).filter(x=>x.endsWith('.spbproj')).sort().map(x=>[x,crypto.createHash('sha256').update(fs.readFileSync(path.join(fixtureDir,x))).digest('hex')]));}
(async()=>{
 assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-focused-layer-read-probe',version:'1'}})).result);
 // Status prepares the existing heuristic car cache. Record that separately;
 // it is not a paint mutation or a verified identity upgrade.
 const cold_identity=(await call('spb_get_state',{})).template_identity;
 await call('spb_status',{});
 const before=select(await call('spb_get_state',{})),saved=fixtures();assert.equal(Object.keys(saved).length,2);
 const contexts=[];
 for(const query of ['What does Base Paint do?','Which Base Paint should I use for body colour?','What does Paintable Area / Base Paint do?','Explain Custom Spec Map / Red Channel Metallic / Base Paint']){
  const context=await call('spb_assistant_context',{query,include_paint:true}),focus=context.template_layers.focused_layers;
  assert.ok(focus);assert.equal(focus.observed_matches,contexts.length<2?4:1);assert.equal(focus.actions.length,0);assert.equal(focus.read_only,true);
  assert.equal(context.template_layers.can_target_panels,false);assert.equal(context.paint.state.data&&context.paint.state.data.execution_source,undefined,'Internal path proof must not reach model-facing context');
  contexts.push(context);
 }
 const after=select(await call('spb_get_state',{}));assert.deepEqual(after,before);assert.deepEqual(fixtures(),saved);
 const checked_at=new Date().toISOString(),receipt='focused-layer-context-'+checked_at.replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(dir,receipt),JSON.stringify({checked_at,cold_identity,before,after,contexts,fixture_hashes:saved,limits:'Actual MCP read context after existing status cache preparation; no installed-model inference, native customer Send or pixel edit proof.'},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({pass:true,receipt,actual_mcp_contexts:contexts.length,focused_matches:contexts.map(c=>c.template_layers.focused_layers.observed_matches),preserved_fields:keys.length,retained_original_fixtures:2}));
})().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill();});
