'use strict';
// Real Offline route and builder: preservation must survive exact layer scope.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const w={console,Map,Set,Date,Promise,Uint8Array,document:{getElementById:()=>null,readyState:'loading',addEventListener(){}},localStorage:{getItem:()=>null},setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},addEventListener(){}};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','js/spb-encyclopedia-data.js','mcp/chatgpt/candidates/spb-offline-builder.js','js/spb-enc-search.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(read(f),w,{filename:f});
const E=w.SpbProEdit,B=w.SpbOfflineBuilder,A=w.SpbOfflineAnswer;
vm.runInContext(read('mcp/chatgpt/native-layer-colour.js'),w);
const env={palette:[{hex:'#ff0000',share_pct:55},{hex:'#00ff00',share_pct:40},{hex:'#0000ff',share_pct:5}],layers:[{id:'psd_23',name:'car_pattern_001.tga',group:'Paintable Area / Car Patterns'},{id:'logo',name:'Logo',role:'sponsors'}],zoneColours:[]};
env.sourceLayerPixels=id=>({status:'pixels-present',layer:{id},palette:env.palette.map(p=>({colour:p.hex,share_of_nontransparent_pixels_pct:p.share_pct}))});
(async()=>{
 await A.load(async name=>{try{return JSON.parse(read('data/encyclopedia/'+name));}catch{return null;}});
 for(const shade of ['gold','muted gold']){
  const text='Make the red in the Paintable Area / Car Patterns / car_pattern_001.tga layer '+shade+'. Keep the green and blue unchanged.';
  const p=E.plan(text,env);assert.equal(p.ops.length,1);assert.equal(p.ops[0].target.kind,'colour');assert.equal(p.ops[0].target.word,'red');assert.deepEqual(Array.from(p.ops[0].target.layers),['car_pattern_001.tga']);assert.deepEqual(Array.from(p.preserved_colour_words).sort(),['blue','green']);assert.equal(p.unknown.length,0);
  const r=A.route(text,env);assert.equal(r.via,'exact-layer-scope');assert.equal(r.steps.length,shade==='gold'?1:2);
  assert.equal(r.steps[0].what.tg.word,'red');assert.equal(r.steps[0].what.tg.kind,'colour');assert.deepEqual(Array.from(r.steps[0].what.tg.layers),['car_pattern_001.tga']);assert.equal(r.steps.filter(s=>s.act==='recolour').length,1);
  if(r.steps.length===2)assert.equal(r.steps[1].what.ref,r.steps[0].id,'Shade applies to the requested recolour result, never green/blue or whole layer');
  const ready=B.toPlan(r.steps,text);assert.equal(ready.ok,true);assert.equal(ready.ed.ops.length,1);
  const compiled=E.compile(ready.ed,env);assert.equal(compiled.zones.length,1);assert.equal(compiled.ask,null);
  assert.deepEqual(Array.from(compiled.zones[0].region.layers),['car_pattern_001.tga']);assert.deepEqual(Array.from(compiled.zones[0].region.colors),['#ff0000']);
 }
 const conflict='Make the red in the Paintable Area / Car Patterns / car_pattern_001.tga layer gold. Keep red unchanged.';
 assert.equal(E.plan(conflict,env).prohibited_edit,true);assert.equal(B.fromText(conflict,env).steps.length,0);assert.equal(A.route(conflict,env).cls,'ASK');
 const extra='Make the red in the Paintable Area / Car Patterns / car_pattern_001.tga layer gold. Keep green unchanged and paint blue black.';
 assert.equal(E.plan(extra,env).preserved_colour_words,undefined,'Extra edit text is never silently consumed as preservation');
 const natural='Make only the red areas in car_pattern_001.tga #b39a58. Keep the green and blue unchanged.';
 const naturalPlan=E.plan(natural,env),naturalRoute=A.route(natural,env);
 assert.equal(naturalPlan.ops.length,1);assert.equal(naturalPlan.ops[0].target.word,'red');
 assert.deepEqual(Array.from(naturalPlan.preserved_colour_words).sort(),['blue','green']);
 assert.equal(naturalRoute.via,'exact-layer-scope');assert.equal(naturalRoute.steps.length,1);
 assert.equal(naturalRoute.steps[0].what.tg.word,'red');
 const builtNatural=B.toPlan(naturalRoute.steps,natural);
 const queuedNatural=w.SpbNativeLayerColour.queue(builtNatural.ed,env);
 assert.ok(queuedNatural && queuedNatural.queue,'Builder must retain native source-colour routing: '+JSON.stringify(builtNatural.ed));
 assert.equal(queuedNatural.queue.length,1);assert.equal(queuedNatural.queue[0].sourceColour,'#ff0000');
 // The real native Run bridge used to let the generic planner preempt this queue.
 function runBridge(file) {
  const src=read(file),start=src.indexOf('run: function (text, ed, ob) {'),end=src.indexOf('\n        } }; } catch (eOB)',start);
  assert.ok(start>=0&&end>start);
  return vm.runInContext('('+src.slice(start+5,end)+'\n})',w);
 }
 let plannerCalls=0;
 Object.assign(w,{_busy:false,_log:[],captureOriginal(){},rshotGrab(){},editEnv:()=>env,intentSpecOnly:()=>false,render(){},
  s5RunReply(){plannerCalls++;return {legacyPlanner:true};},finish:(r,t,a,o)=>({...r,receipt:o&&o.builderRunReceipt})});
 const bridgeOptions={s5frame:{steps:[]},runReceipt:'actual-run-id'};
 assert.equal((await runBridge('js/spb-pro-ai.js')(natural,builtNatural.ed,bridgeOptions)).legacyPlanner,true);
 plannerCalls=0;
 const nativeRun=await runBridge('mcp/chatgpt/candidates/spb-pro-ai.js')(natural,builtNatural.ed,bridgeOptions);
 assert.equal(plannerCalls,0);assert.equal(nativeRun.queue[0].sourceColour,'#ff0000');assert.equal(nativeRun.receipt,'actual-run-id');
 await runBridge('mcp/chatgpt/candidates/spb-pro-ai.js')(natural,builtNatural.ed,{...bridgeOptions,specOnly:true});
 assert.equal(plannerCalls,1,'Spec-only path is not reinterpreted as source paint');
 const aiSource=read('mcp/chatgpt/candidates/spb-pro-ai.js'),s5Start=aiSource.indexOf('    function s5RunReply('),s5End=aiSource.indexOf('    function offlineEditAsk(',s5Start);
 w.planOff=()=>false;w._specOnlyReq=false;w.E=E;w.editReply=(text,chips,extra)=>({text,...extra});
 w.SpbIntentPlan={plan(){plannerCalls++;return null;},live:()=>env};
 B.state=()=>({steps:naturalRoute.steps});
 const nativeS5=vm.runInContext('('+aiSource.slice(s5Start,s5End)+')',w);
 plannerCalls=0;
 const fromPlannerCard=nativeS5(natural,null,{steps:[]});
 assert.equal(fromPlannerCard.queue[0].sourceColour,'#ff0000');assert.equal(plannerCalls,0,'s5only card must also reach the native adapter');
 assert.equal(nativeS5(natural.replace('#b39a58','#abcdef'),builtNatural.ed,{steps:[]}).cannot,true,'Disagreeing typed request and card cannot use native shortcut');
 assert.equal(plannerCalls,0,'Unsupported native replacement must not fall back to flattened recolour');
 assert.equal(w.SpbNativeLayerColour.queue({...builtNatural.ed,ops:builtNatural.ed.ops.map(o=>({...o,_box:{x0:0,y0:0,x1:1,y1:1}}))},env),null,'Box post-processing must not be dropped');
 const liveReceipt=JSON.parse(read('_codex_mcp_work/chatgpt-dev/59910/paint-helper-replace-card-before-2026-10-10T05-58-06-691Z.json'));
 const liveState=JSON.parse(liveReceipt.calls.find(c=>c.tool==='spb_get_state').text);
 const livePixels=JSON.parse(liveReceipt.calls.find(c=>c.tool==='spb_inspect_layer').text.split('\nimage:')[0]);
 const realPaletteEnv={...env,palette:liveState.paint_colours,sourceLayerPixels:id=>{assert.equal(id,'psd_23');return livePixels;}};
 const realPalettePlan=E.plan(natural,realPaletteEnv),realCompiled=E.compile(realPalettePlan,realPaletteEnv);
 assert.equal(realCompiled.zones[0].region.colors.length,2,'Flattened palette includes a second red from foreground art');
 const rawResolved=w.SpbNativeLayerColour.queue(realPalettePlan,realPaletteEnv);
 assert.equal(rawResolved.queue.length,1);assert.equal(rawResolved.queue[0].sourceColour,'#ff0000','Source layer alone supplies red; artwork above is excluded');
 let flattenedFits=0;w.SpbProZone={edgeFit(){flattenedFits++;return {colors:['#ff0000','#aa1f2d'],tols:[40,40],tolerance:40};}};
 assert.equal(w.SpbNativeLayerColour.queue(realPalettePlan,realPaletteEnv).queue[0].sourceColour,'#ff0000');
 assert.equal(flattenedFits,0,'Source replacement never invokes the flattened-image edge fitter');
 delete w.SpbProZone;
 assert.ok(w.SpbNativeLayerColour.queue(realPalettePlan,{...realPaletteEnv,sourceLayerPixels:undefined}).error);
 assert.ok(w.SpbNativeLayerColour.queue(realPalettePlan,{...realPaletteEnv,sourceLayerPixels:()=>({error:'Busy stroke'})}).error);
 assert.ok(w.SpbNativeLayerColour.queue(realPalettePlan,{...realPaletteEnv,sourceLayerPixels:()=>({...livePixels,layer:{id:'wrong'}})}).error);
 console.log(JSON.stringify({raw_source_palette_resolves_actual_failure:true,flattened_sources:Array.from(realCompiled.zones[0].region.colors),native_source:rawResolved.queue[0].sourceColour}));
 const duplicateEnv={...env,layers:[...env.layers,{id:'other',name:'car_pattern_001.tga',group:'Other'}]};
 assert.equal(E.plan(natural,duplicateEnv).kind,'ask');
 const exact='Make the red in the Paintable Area / Car Patterns / car_pattern_001.tga layer #b39a58. Keep the green and blue unchanged.';
 const exactPlan=E.plan(exact,env),native=w.SpbNativeLayerColour.queue(exactPlan,env);
 assert.equal(native.queue.length,1);assert.equal(native.queue[0].layer,'psd_23');assert.equal(native.queue[0].sourceColour,'#ff0000');assert.equal(native.queue[0].colour,'#b39a58');
 assert.equal(w.SpbNativeLayerColour.queue(E.plan(exact.replace('#b39a58','muted gold'),env),env),null,'Do not turn a shade-preserving operation into a solid replacement');
 console.log('PASS actual parser/builder/Offline route: exact-layer colour scope and preservation survive; muted shade stays attached; conflicts and added commands are not hidden. Execution/pixel preservation still requires native proof.');
})().catch(e=>{console.error(e);process.exitCode=1;});
