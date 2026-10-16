'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..'),state=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'../candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(state,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map();
const timer=setTimeout(()=>{child.kill();console.error('Car reference MCP probe timed out');process.exitCode=1},55000);
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let r;try{r=JSON.parse(line)}catch{continue}const resolve=pending.get(r.id);if(resolve){pending.delete(r.id);resolve(r)}}});
child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n')})}
async function call(name,args){const response=await rpc('tools/call',{name,arguments:args});assert.ok(response.result&&!response.result.isError,JSON.stringify(response.error||response.result));return JSON.parse(response.result.content[0].text);}
(async()=>{
  assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-car-knowledge-probe',version:'1'}})).result);
  const list=await rpc('tools/list',{});assert.equal(list.result.tools.find(t=>t.name==='spb_car_knowledge').annotations.readOnlyHint,true);
  if(process.argv.includes('--comparison-only')){
    const query='Do Mini Stock and Dirt Mini Stock share the same template?',direct=await call('spb_car_knowledge',{query}),context=await call('spb_assistant_context',{query});
    assert.equal(direct.resolved,false);assert.equal(direct.comparison.complete,true);
    assert.deepEqual(direct.comparison.references.map(c=>c.id),['ministock','dirtministock']);
    assert.deepEqual(context.car_reference.comparison,direct.comparison);assert.equal(context.paint.available,false);
    const unknown=await call('spb_car_knowledge',{query:'Are Mini Stock and Ferrari F999 templates the same?'});
    assert.equal(unknown.comparison.complete,false);assert.deepEqual(unknown.candidates.map(c=>c.id),['ministock']);
    const result={checked_at:new Date().toISOString(),port:59910,query,direct,context,unknown,paint_reads:0,model_inferences:0,apiFallback:false};
    fs.writeFileSync(path.join(state,'comparison-identity-mcp.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify({pass:true,receipt:'comparison-identity-mcp.json',both_references_in_shared_context:true,unknown_identity_preserved:true,paint_reads:0,model_inferences:0}));return;
  }
  if(process.argv.includes('--template-download-only')){
    const query='Where can I get the latest Mini Stock template?',direct=await call('spb_car_knowledge',{query}),context=await call('spb_assistant_context',{query});
    assert.equal(direct.car.id,'ministock');assert.equal(context.car_reference.car.id,'ministock');assert.deepEqual(context.car_reference.car.template_download,direct.car.template_download);
    assert.equal(direct.car.template_download.available,true);assert.equal(direct.car.template_download.latest_revision_verified,false);assert.equal(context.paint.available,false);
    assert.ok(context.guidance.some(s=>s.includes('template-download questions')));
    const history=await call('spb_car_knowledge',{car_id:'ministock',query:'What changed in rear sponsor artwork?'}),dirt=await call('spb_car_knowledge',{car_id:'dirtministock',query:'What changed in rear sponsor artwork?'});
    const id='ministock-2024-s4-p2-rear-sponsor-artwork-history';assert.ok(history.car.facts.some(f=>f.id===id&&f.template_revision_verified===false));assert.ok(!dirt.car.facts.some(f=>f.id===id));
    const result={checked_at:new Date().toISOString(),port:59910,query,direct,context,history,dirt,paint_reads:0,model_inferences:0,apiFallback:false};
    const receipt='template-download-mcp-'+result.checked_at.replace(/[:.]/g,'-')+'.json';fs.writeFileSync(path.join(state,receipt),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify({pass:true,receipt,exact_archive_in_shared_context:true,history_exact_asphalt:true,dirt_excluded:true,paint_reads:0,model_inferences:0}));return;
  }
  const exact=await call('spb_car_knowledge',{query:'What changed in the Dallara IR18 template?'});
  assert.equal(exact.car.id,'dallarair18');assert.ok(exact.car.facts.length);assert.equal(exact.car.can_target_panels,false);
  const ambiguous=await call('spb_car_knowledge',{query:'BMW M4'});assert.equal(ambiguous.resolved,false);
  const layers=await call('spb_car_knowledge',{car_id:'stockcars2-arcachevy25',query:'Explain metallic template layers'});
  assert.ok(layers.car.template_layer_guides.length);assert.equal(layers.car.template_layer_guides[0].current_file_verified,false);assert.equal(layers.car.template_layer_guides[0].can_target_panels,false);assert.equal(layers.car.template_layer_guides[0].actions.length,0);
  const context=await call('spb_assistant_context',{query:'Can I change sponsors on the Mercedes-AMG W12 E Performance?'});
  assert.equal(context.car_reference.car.id,'mercedesw12');assert.equal(context.paint.available,false);
  const live=process.argv.includes('--live')?await call('spb_assistant_context',{query:'What changed in my current template?',include_paint:true}):null;
  if(live){
    const status=live.paint.status;
    assert.ok(status.omitted||status.data,'Live status unavailable: '+String(status.error||status.reason||'No parsed status').slice(0,300));
    if(status.data){
      assert.ok(status.data.template_identity,'Status must include the visible identity evidence');
      assert.equal(status.data.template_identity.current_file_verified,false);
      assert.ok(!/[/\\]/.test(status.data.template_identity.source_paint_name||''),'Only the basename leaves the app');
    }
    if(live.template_layers.available){assert.equal(live.template_layers.actions.length,0);assert.equal(live.template_layers.can_target_panels,false);}
    assert.ok(live.car_reference.identity_source || (!live.car_reference.resolved && live.car_reference.match_reason),'Context must explain its selected identity or unresolved model');
  }
  if(process.argv.includes('--expect-saved-brief')){
    assert.ok(live&&live.saved_design_brief.available,'The native reopened project must expose its saved discussion through actual MCP context');
    assert.equal(live.saved_design_brief.historical,true);
    assert.match(JSON.stringify(live.saved_design_brief.turns),/no glitter/i);
    assert.equal(live.project_design_context.context.last_change,null,'The saved discussion must not revive an old executable change');
  }
  const successor=[];
  if(process.argv.includes('--road-successor')){
    const facts=JSON.parse(fs.readFileSync(path.join(__dirname,'research/road_successor/runtime_facts.json'),'utf8')).facts;
    for(const fact of facts){
      const response=await call('spb_car_knowledge',{car_id:fact.car_ids[0],query:'What is unusual about this template structure?'});
      assert.equal(response.car.id,fact.car_ids[0]);assert.equal(response.car.can_target_panels,false);
      assert.ok(response.car.facts.some(f=>f.id===fact.id&&f.text===fact.text));
      successor.push(response);
    }
  }
  const artwork=await call('spb_car_knowledge',{car_id:'ferrari296gt3',query:'What changed in the body vinyl artwork?'});
  assert.ok(artwork.car.facts.some(f=>f.id==='ferrari296gt3-body-vinyl-artwork-update-2024-s3'&&f.template_revision_verified===false&&f.uv_mapping_verified===false));
  const artworkContext=await call('spb_assistant_context',{query:'What changed in the Ferrari 296 GT3 body vinyl artwork?'});
  assert.equal(artworkContext.car_reference.car.id,'ferrari296gt3');
  assert.ok(artworkContext.car_reference.car.facts.some(f=>f.id==='ferrari296gt3-body-vinyl-artwork-update-2024-s3'));
  const gt4=await call('spb_car_knowledge',{car_id:'mercedesamggt4',query:'What changed in the paint scheme artwork?'});
  assert.ok(gt4.car.facts.some(f=>f.id==='mercedesamggt4-iwc-paint-scheme-logos-2023-s3'&&f.template_revision_verified===false&&f.uv_mapping_verified===false));
  const gt4Context=await call('spb_assistant_context',{query:'What changed in the Mercedes-AMG GT4 paint scheme artwork?'});
  assert.equal(gt4Context.car_reference.car.id,'mercedesamggt4');assert.ok(gt4Context.car_reference.car.facts.some(f=>f.id==='mercedesamggt4-iwc-paint-scheme-logos-2023-s3'));
  const bmw=await call('spb_car_knowledge',{car_id:'bmwm4gt4',query:'What changed in the Paint Shop preview?'});
  assert.ok(bmw.car.facts.some(f=>f.id==='bmwm4gt4-f82-rear-windshield-paintshop-flicker-repair-2024-s3-p1'&&f.topic==='paint-preview-history'&&f.template_revision_verified===false));
  assert.ok(bmw.car.facts.some(f=>f.id==='bmwm4gt4-f82-pattern0-asymmetry-repair-2021-s2-p1'&&f.topic==='paint-artwork-history'));
  const bmwContext=await call('spb_assistant_context',{query:'What changed in the BMW M4 F82 GT4 Paint Shop preview?'});
  assert.equal(bmwContext.car_reference.car.id,'bmwm4gt4');assert.equal(bmwContext.car_reference_request.question,true);
  assert.ok(bmwContext.car_reference.car.facts.some(f=>f.id==='bmwm4gt4-f82-rear-windshield-paintshop-flicker-repair-2024-s3-p1'));
  const bmwG82=await call('spb_car_knowledge',{car_id:'bmwm4evogt4',query:'What changed in its artwork?'});
  assert.ok(!bmwG82.car.facts.some(f=>f.id.startsWith('bmwm4gt4-f82-')));
  const dirt358=await call('spb_car_knowledge',{car_id:'dirtmodified-358',query:'What changed in its artwork?'});
  assert.ok(dirt358.car.facts.some(f=>f.id==='dirtmodified-358-all-variants-2021-wo-o-contingency-update'&&f.applicability.variant_exclusive===false&&f.template_revision_verified===false));
  const dirt358Context=await call('spb_assistant_context',{query:'What changed in the Dirt 358 Modified artwork?'});
  assert.equal(dirt358Context.car_reference.car.id,'dirtmodified-358');assert.equal(dirt358Context.car_reference_request.question,true);
  assert.ok(dirt358Context.car_reference.car.facts.some(f=>f.id==='dirtmodified-358-all-variants-2021-wo-o-contingency-update'));
  const limited=await call('spb_car_knowledge',{car_id:'dirtlatemodel-350',query:'What changed in its artwork?'});
  assert.ok(limited.car.facts.some(f=>f.id==='dirtlatemodel-350-all-family-2019-woo-decal-history'&&f.applicability.variant_exclusive===false&&f.template_revision_verified===false));
  const limitedContext=await call('spb_assistant_context',{query:'What changed in the Dirt Late Model Limited artwork?'});
  assert.equal(limitedContext.car_reference.car.id,'dirtlatemodel-350');
  assert.ok(limitedContext.car_reference.car.facts.some(f=>f.id==='dirtlatemodel-350-all-family-2019-woo-decal-history'));
  const result={tools:list.result.tools.length,exact,ambiguous,context,layers,live,successor,artwork,artworkContext,gt4,gt4Context,bmw,bmwContext,bmwG82,dirt358,dirt358Context,limited,limitedContext,checked_at:new Date().toISOString()};
  const receipt=(live?'car-knowledge-live-context-':'car-knowledge-mcp-')+result.checked_at.replace(/[:.]/g,'-')+'.json';
  fs.writeFileSync(path.join(state,receipt),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({receipt,tools:result.tools,car:exact.car.id,facts:exact.car.facts.length,ambiguous_candidates:ambiguous.candidates.length,context_car:context.car_reference.car.id,paint_reads:live?2:0,live_identity:live&&(live.car_reference.identity_source||live.car_reference.match_reason),live_conflict:live&&live.car_reference.identity_conflict,saved_brief:live&&live.saved_design_brief.available}));
})().catch(e=>{console.error(e.message);process.exitCode=1}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill()});
