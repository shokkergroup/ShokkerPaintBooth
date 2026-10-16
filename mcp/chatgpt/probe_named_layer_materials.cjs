'use strict';
// Read-only native acceptance companion. Browser Send is exercised separately.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const phase=process.argv[2];assert.ok(['before','after'].includes(phase));
const arca=process.argv[3]==='arca',label=process.argv[4]||'';
assert.ok(!label||/^[a-z0-9-]{1,40}$/.test(label));
const prefix='named-material-native-'+(arca?'arca-':'')+(label?label+'-':'');
const receipt=path.join(dir,prefix+phase+'.json');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let seq=0,buffer='';const pending=new Map();
const timer=setTimeout(()=>{child.kill();console.error('Named-material MCP read timed out');process.exitCode=1;},45000);
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let n;while((n=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,n);buffer=buffer.slice(n+1);let r;try{r=JSON.parse(line);}catch{continue;}if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id);}}});child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const id=++seq;pending.set(id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});}
async function call(name,args={}){const r=await rpc('tools/call',{name,arguments:args});assert.ok(r.result&&!r.result.isError,JSON.stringify(r.error||r.result));return JSON.parse(r.result.content[0].text);}
function fixtures(){const p=path.resolve(__dirname,'../../_release_evidence/chatgpt-dev/59910/projects');return Object.fromEntries(fs.readdirSync(p).filter(n=>n.endsWith('.spbproj')).map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(p,n))).digest('hex')]));}
const keys=['layers','zones','selected_zone','paint_colours','pending_changes','recent_changes','saved_design_brief','template_identity'];
(async()=>{
 assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'private-named-material-native-proof',version:'1'}})).result);
 await call('spb_status');
 const query=arca?'What material is on Base Paint?':'What material is on Sponsors?';
 const state=await call('spb_get_state',{editor_query:query});
 const focused=state.editor_capabilities?.layer_materials?.named_layers;
 assert.ok(focused,'Current page must expose the new focused caller, not merely the standalone module');
 assert.equal(focused.matched_layers,arca?4:1);assert.equal(focused.records[0].name,arca?'Base Paint':'Sponsors');
 if(arca){assert.equal(focused.ambiguous,true);assert.ok(focused.records.some(r=>r.id==='psd_0'&&r.group==='Paintable Area'));assert.equal(focused.records.filter(r=>r.visible===false).length,3);}else assert.equal(focused.records[0].id,'psd_1');
 assert.ok(focused.records.every(r=>r.state==='none'));
 const context=await call('spb_assistant_context',{query,include_paint:true});
 assert.deepEqual(context.editor_capabilities.layer_materials.named_layers,focused);
 const out={checked_at:new Date().toISOString(),phase,query,port:59910,paint:Object.fromEntries(keys.map(k=>[k,state[k]])),focused,context_focused:context.editor_capabilities.layer_materials.named_layers,fixture_hashes:fixtures(),limits:['Current page MCP reads; native Send captured separately.','Eight exposed paint fields/two fixture hashes; not full raster equality or packaged adoption.']};
 assert.equal(Object.keys(out.fixture_hashes).length,2);
 if(phase==='after'){const before=JSON.parse(fs.readFileSync(path.join(dir,prefix+'before.json'),'utf8'));assert.deepEqual(out.paint,before.paint);assert.deepEqual(out.fixture_hashes,before.fixture_hashes);}
 fs.writeFileSync(receipt,JSON.stringify(out,null,2)+'\n');
 console.log(JSON.stringify({pass:true,receipt:path.basename(receipt),named_target:focused.target,exact_layer:focused.records[0].id,fields:keys.length,retained_fixtures:2,model_inferences:0}));
})().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill();});
