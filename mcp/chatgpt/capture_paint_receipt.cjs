'use strict';
// Read-only live MCP evidence. Saves returned preview pixels, never renders files.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),{spawn}=require('node:child_process');
const label=process.argv[2];if(!/^[a-z0-9-]{1,40}$/.test(label||''))throw Error('Supply a short evidence label');
const captureSpec=process.argv.includes('--spec');
const root=path.resolve(__dirname,'../..'),state=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(state,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
const receipt={label,started:new Date().toISOString(),read_only:true,capture_spec:captureSpec,candidateManifest:JSON.parse(fs.readFileSync(path.join(__dirname,'candidates/sources.json'),'utf8')),calls:[],images:[]};let id=0,buffer='';const pending=new Map();
const runtime=JSON.parse(fs.readFileSync(path.join(state,'server.json'),'utf8'));
assert.equal(runtime.port,59910);assert.equal(runtime.host,'127.0.0.1');
receipt.privateRuntime={pid:runtime.pid,port:runtime.port,psd_raster_candidate:runtime.psd_raster_candidate||null,layer_visibility_candidate:runtime.layer_visibility_candidate||null};
receipt.privateHostSources=['dev_server.py','psd_raster_candidate.py','layer_visibility_candidate.py'].map(name=>({source:'mcp/chatgpt/'+name,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,name))).digest('hex')}));
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{const r=JSON.parse(line),resolve=pending.get(r.id);if(resolve){pending.delete(r.id);resolve(r);}}catch{}}});child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n');});}
const timer=setTimeout(()=>{child.kill();console.error('Capture timed out');process.exit(1);},55000);
(async()=>{
 receipt.ownedModules=[];
 if(process.argv.includes('--reference-history')){
  assert(process.argv.includes('--concise-reference')&&process.argv.includes('--topic-readiness'),'Reference history receipt requires predecessors');
  const proof=JSON.parse(fs.readFileSync(path.join(__dirname,'body-output-consistency/reference-history/stage-proof.json'),'utf8'));
  const raw=fs.readFileSync(path.join(__dirname,'body-output-consistency/reference-history/spb-pro-ai.js'));
  let digest=crypto.createHash('sha256').update(raw).digest('hex');
  assert.equal(proof.syntax_pass,true);assert.equal(digest,proof.candidate_sha256);
  if(process.argv.includes('--reference-dock')){
   const dock=JSON.parse(fs.readFileSync(path.join(__dirname,'body-output-consistency/reference-dock/stage-proof.json'),'utf8'));
   assert.equal(dock.syntax_pass,true);assert.equal(dock.files.find(f=>f.path==='js/spb-pro-ai.js').source_sha256,digest);
   for(const row of dock.files){
    const expected=crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'body-output-consistency/reference-dock',path.basename(row.path)))).digest('hex');
    assert.equal(expected,row.candidate_sha256);assert.equal(runtime.knowledge_overlay['/'+row.path],expected);
    const res=await fetch('http://127.0.0.1:59910/'+row.path);assert.equal(res.status,200);assert.equal(crypto.createHash('sha256').update(Buffer.from(await res.arrayBuffer())).digest('hex'),expected);
   }
   digest=dock.files.find(f=>f.path==='js/spb-pro-ai.js').candidate_sha256;receipt.referenceDock=dock;
  }
  assert.equal(runtime.knowledge_overlay['/js/spb-pro-ai.js'],digest);
  const response=await fetch('http://127.0.0.1:59910/js/spb-pro-ai.js');assert.equal(response.status,200);
  assert.equal(crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex'),digest);
  receipt.referenceHistory={candidate_sha256:digest,stageProofSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'body-output-consistency/reference-history/stage-proof.json'))).digest('hex')};
 }
 let topicProof=null;
 if(process.argv.includes('--topic-readiness')){
  topicProof=JSON.parse(fs.readFileSync(path.join(__dirname,'body-output-consistency/private-topic/stage-proof.json'),'utf8'));
  assert.equal(topicProof.syntax_pass,true);
  receipt.topicOverlayProofSha256=crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'body-output-consistency/private-topic/stage-proof.json'))).digest('hex');
 }
 for(const name of ['editor-capabilities.js','car-knowledge/layer-reading.js','car-knowledge/offline-answer.js','car-knowledge/core.js','car-knowledge/live-identity.js','design-intent.js','design-brief.js','native-layer-colour.js']){
  const override=topicProof&&topicProof.files.find(item=>item.path==='mcp/chatgpt/'+name);
  let expectedPath=override?path.join(__dirname,'body-output-consistency/private-topic/assets',override.path):path.join(__dirname,name);
  let concise=null,availability=null;
  if(process.argv.includes('--concise-reference')&&name==='car-knowledge/offline-answer.js'){
   assert(override,'Concise receipt requires --topic-readiness');
   concise=JSON.parse(fs.readFileSync(path.join(__dirname,'body-output-consistency/concise-reference/stage-proof.json'),'utf8'));
   assert.equal(concise.private_baseline_sha256,override.candidate_sha256);assert.equal(concise.syntax_pass,true);
   expectedPath=path.join(__dirname,'body-output-consistency/concise-reference/offline-answer.js');
  }
  if(process.argv.includes('--paint-availability')&&name==='car-knowledge/offline-answer.js'){
   assert(concise&&process.argv.includes('--reference-history'),'Paint availability receipt requires accepted predecessors');
   availability=JSON.parse(fs.readFileSync(path.join(__dirname,'body-output-consistency/paint-availability/stage-proof.json'),'utf8'));
   assert.equal(availability.predecessors.find(p=>p.label==='private').source_sha256,concise.candidate_sha256);assert.equal(availability.syntax_pass,true);
   expectedPath=path.join(__dirname,'body-output-consistency/paint-availability/offline-answer.js');
  }
  let overview=null,nameBootstrap=null;
  if(process.argv.includes('--car-overview')&&['car-knowledge/core.js','car-knowledge/offline-answer.js'].includes(name)){
   assert(process.argv.includes('--paint-availability')&&process.argv.includes('--reference-dock'),'Overview requires accepted conversation predecessors');
   const stagePath=path.join(__dirname,'body-output-consistency/car-overview/stage-proof.json'),stage=JSON.parse(fs.readFileSync(stagePath));
   const component=JSON.parse(fs.readFileSync(path.join(__dirname,'body-output-consistency/car-overview/component-proof.json')));
   assert(stage.syntax_pass&&component.pass&&component.car_overviews===768);assert(runtime.prepared_browser?.enabled&&runtime.prepared_browser.html_injection===false);
   overview=stage.files.find(f=>path.basename(f.source)===path.basename(name));assert(overview);
   assert.equal(crypto.createHash('sha256').update(fs.readFileSync(expectedPath)).digest('hex'),overview.source_sha256);
   expectedPath=path.join(__dirname,'body-output-consistency/car-overview',path.basename(name));
   const manifestPath=path.join(__dirname,'prepared-browser/manifest.json'),manifest=JSON.parse(fs.readFileSync(manifestPath));
   assert.equal(runtime.prepared_browser.manifest_sha256,crypto.createHash('sha256').update(fs.readFileSync(manifestPath)).digest('hex'));
   if(process.argv.includes('--name-bootstrap')){
    const bootstrap=JSON.parse(fs.readFileSync(path.join(__dirname,'prepared-browser/name-bootstrap/stage-proof.json')));
    const checks=JSON.parse(fs.readFileSync(path.join(__dirname,'prepared-browser/name-bootstrap/component-proof.json')));
    assert(bootstrap.syntax_pass&&checks.pass&&checks.pre_fact_question_cases===768&&checks.names_do_not_mark_facts_ready);
    const kind=name==='car-knowledge/core.js'?'core':'answer';
    assert.equal(bootstrap['source_'+kind+'_sha256'],overview.candidate_sha256);
    expectedPath=path.join(__dirname,'prepared-browser/name-bootstrap',path.basename(name));
    nameBootstrap=bootstrap[kind+'_sha256'];assert.equal(manifest.files['mcp/chatgpt/'+name].sha256,nameBootstrap);
    receipt.nameBootstrap={stage:bootstrap,component:checks};
   }else assert.equal(manifest.files['mcp/chatgpt/'+name].sha256,overview.candidate_sha256);
   receipt.carOverview={stage,component,prepared_manifest_sha256:runtime.prepared_browser.manifest_sha256};
  }
  const expected=crypto.createHash('sha256').update(fs.readFileSync(expectedPath)).digest('hex');
  if(overview)assert.equal(expected,nameBootstrap||overview.candidate_sha256);
  if(override&&!overview){assert.equal(expected,availability?availability.candidate_sha256:concise?concise.candidate_sha256:override.candidate_sha256);assert.equal(runtime.knowledge_overlay['/'+override.path],expected);}
  const response=await fetch('http://127.0.0.1:59910/mcp/chatgpt/'+name);assert.equal(response.status,200);
  if(overview)assert.equal(response.headers.get('X-SPB-Prepared-Browser'),expected);
  const served=crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex');assert.equal(served,expected);
  receipt.ownedModules.push({source:path.relative(root,expectedPath).replace(/\\/g,'/'),source_sha256:expected,served_sha256:served});
 }
 if(process.argv.includes('--name-bootstrap')){
  assert(process.argv.includes('--car-overview')&&receipt.nameBootstrap,'Name bootstrap requires the physical overview predecessor');
  const response=await fetch('http://127.0.0.1:59910/mcp/chatgpt/car-knowledge/identity-index.js');assert.equal(response.status,200);
  const digest=crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex');
  assert.equal(digest,receipt.nameBootstrap.stage.identity_index_sha256);assert.equal(response.headers.get('X-SPB-Prepared-Browser'),digest);
 }
 await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-paint-receipt',version:'1'}});
 const prefix='paint-'+label+'-'+receipt.started.replace(/[:.]/g,'-');
 const reads=[['spb_get_state',{}],['spb_preview',{parts:false,spec:false}]];
 if(captureSpec)reads.push(['spb_preview',{parts:false,spec:true}]);
 if(process.argv.includes('--material-context'))reads.push(['spb_assistant_context',{query:'What do the metallic, roughness and clearcoat groups in my template mean?',include_paint:true}]);
 if(process.argv.includes('--editor-context'))reads.push(['spb_assistant_context',{query:'What materials are assigned to my layers, and why are guides missing from Live Preview?',include_paint:true}]);
 if(process.argv.includes('--design-context'))reads.push(['spb_assistant_context',{query:'Why would the second design option suit this car?',include_paint:true}]);
 if(process.argv.includes('--layer-inspection'))reads.push(['spb_inspect_layer',{layer:'psd_23',image:true}]);
 reads.push(['spb_check',{fresh:false}]);
 for(const [tool,args] of reads){
  const r=(await rpc('tools/call',{name:tool,arguments:args})).result;assert.ok(r&&!r.isError,JSON.stringify(r));let name='preview';
  const texts=[];
  for(const c of r.content||[]){
   if(c.type==='text'){texts.push(c.text);if(/^image: /.test(c.text))name=c.text.slice(7);}
   if(c.type==='image'){
    assert.ok(['image/png','image/jpeg'].includes(c.mimeType));const bytes=Buffer.from(c.data,'base64');
    const file=prefix+'-'+receipt.images.length+(c.mimeType==='image/png'?'.png':'.jpg');fs.writeFileSync(path.join(state,file),bytes,{flag:'wx'});
    receipt.images.push({name,file,mimeType:c.mimeType,sha256:crypto.createHash('sha256').update(bytes).digest('hex')});
   }
  }
  receipt.calls.push({tool,args,text:texts.join('\n')});
 }
 assert.ok(receipt.images.length,'The actual preview tool must return image pixels');
 receipt.finished=new Date().toISOString();const file=prefix+'.json';fs.writeFileSync(path.join(state,file),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({receipt:file,images:receipt.images.map(i=>({name:i.name,file:i.file}))}));
})().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill();});
