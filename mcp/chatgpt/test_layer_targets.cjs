'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const imported=JSON.parse(JSON.parse(fs.readFileSync(path.join(root,'_codex_mcp_work/chatgpt-dev/59910/paint-official-arca-import-2026-10-09T22-26-30-056Z.json'),'utf8')).calls[0].text).layers;
// These IDs are a controlled current-document fixture, not IDs observed by the
// prior native receipt (that receipt omitted IDs). Names/groups are actual import.
const layers=imported.map((r,i)=>({...r,id:i,groupName:r.group,visible:!r.hidden,img:{width:2048,height:2048}}));
const w={console,Set,Map,Date,Promise,Uint8Array,document:{readyState:'loading',addEventListener(){},getElementById:()=>null},localStorage:{getItem:()=>null,setItem(){}},setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},addEventListener(){},_psdLayers:layers};w.window=w;vm.createContext(w);
function load(file){vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w,{filename:file});}
for(const file of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/car-knowledge/layer-reading.js','mcp/chatgpt/candidates/spb-pro-carmap.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','mcp/chatgpt/candidates/spb-pro-zone-kit.js'])load(file);
const T=w.SpbLayerTargets,E=w.SpbProEdit,Z=w.SpbProZone,roles=w.SpbProCar.roles(),body=roles.find(l=>l.role==='body paint'),spec=roles.find(l=>l.name==='Base Paint'&&/Red Channel Metallic/.test(l.group));
const duplicates=w.SpbTemplateLayers.read(roles).duplicate_names.find(d=>d.name==='Base Paint');assert.equal(duplicates.current_matches.find(l=>l.group==='Paintable Area').id,0,'Bounded context keeps exact live IDs even when the larger snapshot is omitted');
assert.ok(body&&spec);assert.equal(T.resolve('Base Paint',roles).ok,false);assert.equal(Z.findLayer('Base Paint'),null,'Ambiguous direct tool names must not use the first PSD match');
assert.equal(T.resolve('Paintable Area / Base Paint',roles).selector,body.id);assert.equal(Z.findLayer(body.id).groupName,'Paintable Area');assert.equal(Z.findLayer(spec.id).groupName,spec.group);
const env={layers:roles,palette:[{hex:'#19376e',share_pct:95}],zoneColours:[]};
if(process.argv.includes('--inspect-plan')){const p=E.plan('Make the Paintable Area / Base Paint layer red',env);console.log(JSON.stringify({plan:p,compiled:E.compile(p,env)}));}
for(const text of ['Make the body layer red','Make only the Paintable Area / Base Paint layer red','Make the Paintable Area/Base Paint layer red','Make the Base Paint layer in Paintable Area red','Make the Base Paint layer from the Paintable Area group red']){
 const plan=E.plan(text,env);assert.equal(plan.kind,'ops',text+' '+JSON.stringify(plan)+' scope='+JSON.stringify(T.scope(text,roles)));assert.equal(plan.ops[0].target.layers[0],body.id,text);
 const compiled=E.compile(plan,env);assert.equal(compiled.zones.length,1,text);assert.equal(compiled.zones[0].region.layers[0],body.id,text);assert.equal(Z.findLayer(compiled.zones[0].region.layers[0]).id,body.id);
}
const ambiguous=E.plan('Make the Base Paint layer red',env);assert.equal(ambiguous.kind,'ask');
const aiSource=fs.readFileSync(path.join(root,'mcp/chatgpt/candidates/spb-pro-ai.js'),'utf8');
const serializer=aiSource.match(/^    function layersInfo\(\).*$/m);assert.ok(serializer);w.CAR=w.SpbProCar;
const snapshot=vm.runInContext(serializer[0]+'\nlayersInfo()',w);assert.equal(snapshot.find(l=>l.name==='Base Paint'&&l.group==='Paintable Area').id,body.id,'Actual model snapshot must retain the current ID and group');
const resolver=aiSource.slice(aiSource.indexOf('    function mcpResolveLayerExact('),aiSource.indexOf('    var MCP_WRITE'));
const mcpLayer=vm.runInContext(resolver+'\nmcpResolveLayerExact("Paintable Area / Base Paint")',w);assert.equal(mcpLayer.layer.id,body.id,'Actual MCP edit_layer exact resolver supports the full group path');
const noIds=roles.map(({id,...rest})=>rest),noIdEnv={...env,layers:noIds};
const recovered=E.plan('Make the body layer red',noIdEnv);assert.equal(recovered.kind,'ops');assert.equal(recovered.ops[0].target.layers[0],body.id,'Owner recovery requires a unique current name/group match');assert.equal(E.compile(recovered,noIdEnv).zones[0].region.layers[0],body.id,'Recovered identity survives actual compilation');
const liveCar=w.SpbProCar;w.SpbProCar={roles:()=>[]};assert.equal(E.plan('Make the body layer red',noIdEnv).kind,'ask','Missing IDs without a current map must still ask');
w.SpbProCar={roles:()=>roles.concat({...body,id:'second-current-body'})};assert.equal(E.plan('Make the body layer red',noIdEnv).kind,'ask','An ambiguous current name/group mapping cannot recover an ID');w.SpbProCar=liveCar;
const protectedText='Make the Paintable Area / Base Paint layer red. Keep the Custom Spec Map / Red Channel Metallic / Base Paint layer unchanged.';
const protectedPlan=E.plan(protectedText,env);assert.equal(protectedPlan.kind,'ops');assert.equal(protectedPlan.ops[0].target.layers[0],body.id);assert.equal(protectedPlan.preserved_layers[0],spec.id);
load('mcp/chatgpt/candidates/spb-intent-report.js');
const reportScope=w.SpbIntentReport.scopeOf(protectedText,{queue:[{kind:'add',spec:{region:{everything:true,layers:[body.id]}}}]},{});
assert.equal(reportScope.whole,false);assert.equal(reportScope.layers[0],body.id,'Actual measured report preserves an ID of zero and does not classify Base Paint as whole car');
assert.equal(E.plan('Make the Paintable Area / Base Paint layer red. Keep the Paintable Area / Base Paint layer unchanged.',env).prohibited_edit,true);
const collision=[{id:'Body',name:'Logo',img:{}},{id:'actual-body',name:'Body',img:{}}];
assert.equal(T.select(collision[1],collision).selector,'actual-body');w._psdLayers=collision;assert.equal(Z.findLayer('Body').name,'Logo','An exact ID outranks a different row whose name equals that ID');assert.equal(Z.findLayer('actual-body').name,'Body');
w._psdLayers=[{id:1,name:'Number Fill',img:{}},{id:2,name:'Number Outline',img:{}}];assert.equal(Z.findLayer('Number'),null);assert.equal(Z.findLayer('Outline').id,2);
w._psdLayers=layers;
for(const file of ['mcp/chatgpt/candidates/spb-offline-builder.js','js/spb-encyclopedia-data.js','js/spb-enc-search.js','mcp/chatgpt/candidates/spb-offline-answer.js'])load(file);
(async()=>{
 await w.SpbOfflineAnswer.load(async name=>{try{return JSON.parse(fs.readFileSync(path.join(root,'data/encyclopedia',name),'utf8'));}catch{return null;}});
 for(const text of ['Make the body layer red','Make the Paintable Area / Base Paint layer red','Make the Base Paint layer in Paintable Area red',protectedText]){
  const built=w.SpbOfflineBuilder.fromText(text,env);assert.equal(built.steps.length,1,text);assert.equal(built.steps[0].what.tg.layers[0],body.id,text);
  const routed=w.SpbOfflineAnswer.route(text,env);assert.equal(routed.cls,'DO',text+' '+JSON.stringify(routed));assert.equal(routed.steps.length,1);assert.equal(routed.steps[0].what.layers[0],body.id,text);
 }
 const denied=w.SpbOfflineAnswer.route('Make the Base Paint layer red',env);assert.equal(denied.cls,'ASK');assert.equal(denied.steps.length,0);
 const bare=E.plan('Make Base Paint red.',env);assert.equal(bare.kind,'ask');assert.equal(bare.layer_target_question,true);assert.equal(bare.chips.length,4);
 assert.equal(w.SpbOfflineAnswer.route('Make Base Paint red.',env).cls,'ASK');
 assert.equal(T.scope('Why is Base Paint red?',roles),null,'A question about a duplicate name is not an edit');
 assert.equal(denied.ask.chips.length,4,'All four current duplicate groups are named');
 assert.equal(E.plan('Make the Base Paint layer red',env).layer_target_question,true);
 const picked=denied.ask.chips.find(c=>c.includes('Paintable Area / Base Paint'));
 assert.equal(picked,'Make the Paintable Area / Base Paint layer red','Choice retains the requested operation');
 const pickedRoute=w.SpbOfflineAnswer.route(picked,env);assert.equal(pickedRoute.cls,'DO');assert.equal(pickedRoute.steps[0].what.layers[0],body.id);
 assert.equal(pickedRoute.steps.length,1);
 for(const follow of ['the body one','Paintable Area','I mean the body one','The body paint one.']){
  const r=w.SpbOfflineAnswer.route(follow,{...env,chips:denied.ask.chips});
  assert.equal(r.cls,'DO',follow);assert.equal(r.steps.length,1);assert.equal(r.steps[0].what.layers[0],body.id,follow);
 }
 assert.equal(T.choose('the other one',denied.ask.chips,roles),null);
 assert.equal(T.choose('body',denied.ask.chips,roles.filter(r=>r.id!==body.id)),null,'Missing chosen current layer cannot reuse a pending choice');
 assert.equal(T.choose('body',['Make it red'],roles),null,'Unrelated conversational choices are not layer choices');

 const missingScope=w.SpbLayerTargets.scope('Make the Base Paint layer red',roles.map(({id,...r})=>r));
 assert.equal(missingScope.ask.chips.length,0,'Missing current IDs never produce executable choices');

 const result={pass:true,actual_import_label_records:imported.length,fixture_ids:true,duplicate_name:'ask',role_body:'exact-id',full_group_path:'exact-id',natural_group_phrase:'pass',protected_spec:'exact-id',backend_id_precedence:'pass',offline_routing:'pass',snapshot_identity:'pass',mcp_group_resolver:'pass',measured_report_identity:'pass',native_pixels:false};
 if(process.argv.includes('--record')){
  const crypto=require('node:crypto');result.checked_at=new Date().toISOString();result.source_hashes={};
  for(const file of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/preserved-colours.js','mcp/chatgpt/car-knowledge/layer-reading.js','mcp/chatgpt/candidates/spb-pro-edit.js','mcp/chatgpt/candidates/spb-pro-ai.js','mcp/chatgpt/candidates/spb-pro-zone-kit.js','mcp/chatgpt/candidates/spb-intent-report.js','mcp/chatgpt/candidates/spb-offline-answer.js'])result.source_hashes[file]=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');
  const receipt='layer-targets-component-'+result.checked_at.replace(/[:.]/g,'-')+'.json';fs.writeFileSync(path.join(root,'_codex_mcp_work/chatgpt-dev/59910',receipt),JSON.stringify(result,null,2)+'\n',{flag:'wx'});result.receipt=receipt;
 }
 console.log(JSON.stringify({...result,source_hashes:undefined}));
})().catch(e=>{console.error(e);process.exitCode=1;});
