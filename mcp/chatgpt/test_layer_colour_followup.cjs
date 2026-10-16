'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const layer={id:'body',name:'Base Paint',groupName:'Paintable Area',visible:true,img:{width:50,height:50},effects:{colorOverlay:{enabled:true,color:'#c8102e',opacity:1,blendMode:'source-over'}}};
const w={console,Promise,Set,Map,Date,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},document:{readyState:'loading',addEventListener(){},getElementById:()=>null},localStorage:{getItem:()=>null,setItem(){}},_psdLayers:[layer]};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','mcp/chatgpt/native-layer-colour.js','mcp/chatgpt/layer-colour-followup.js'])vm.runInContext(read(f),w,{filename:f});
let epoch=1;w.SpbConversationScope={observe(){},stamp:()=>epoch,current:x=>x===epoch};
const E=w.SpbProEdit,N=w.SpbNativeLayerColour,F=w.SpbLayerColourFollowup,env={layers:[{...layer,group:layer.groupName,role:'body paint'}],palette:[{hex:'#c8102e',share_pct:90}],zoneColours:[]};
for(const f of ['mcp/chatgpt/candidates/spb-offline-builder.js','js/spb-encyclopedia-data.js','js/spb-enc-search.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(read(f),w,{filename:f});
const initial=E.plan('Make the Paintable Area / Base Paint layer red',env),queue=N.queue(initial,env).queue;
// Actual native reply expression, not a test-created context object.
const ai=read('mcp/chatgpt/candidates/spb-pro-ai.js');
const line=ai.split('\n').find(l=>l.includes('if (nativeColour) return Promise.resolve'));
Object.assign(w,{ed:initial,E,nativeColour:{queue,text:'Colour'},editReply:()=>({failed:true})});
vm.runInContext('async function actualReply(){'+line+'}',w);
(async()=>{
 const reply=await w.actualReply();assert.ok(reply.editCtx.native_layer_colour);env.last=reply.editCtx;
 for(const name of ['nativeBuilder','nativeFrame']){
  w[name]={queue,text:'Colour'};
  const object=ai.match(new RegExp('\\{offline:true,text:'+name+'\\.text,.*?tools:\\[\'edit_layer\'\\]\\}'));
  assert.ok(object,name+' actual reply');const built=vm.runInContext('('+object[0]+')',w);
  assert.equal(built.editCtx.native_layer_colour.id,'body',name+' retains context in actual return expression');
 }
 for(const words of ['A darker red, please.','Make it darker.','A little darker again.','Lighter red please']){
  const p=E.plan(words,env);assert.equal(p.kind,'ops',JSON.stringify(p));assert.deepEqual(Array.from(p.ops[0].target.layers),['body']);
  const q=N.queue(p,env);assert.equal(q.queue[0].layer,'body');assert.notEqual(q.queue[0].colour,'#c8102e');assert.equal(q.queue[0].kind,'layer');
 }
 const darker=E.plan('A darker red, please.',env);assert.equal(darker.ops[0].colour.hex,E.shadeColour('#c8102e','darker'));
 const routed=w.SpbOfflineAnswer.route('A darker red, please.',env);assert.equal(routed.cls,'DO',JSON.stringify(routed));assert.deepEqual(Array.from(routed.steps[0].what.layers),['body'],JSON.stringify(routed));
 assert.ok(routed.steps[0].extra._nativeColourRefinement,'Actual Offline route retains refinement precondition');
 const steps=w.SpbOfflineBuilder.fromText('A darker red, please.',env).steps,reviewed=w.SpbOfflineBuilder.toPlan(steps,'A darker red, please.').ed;
 assert.ok(reviewed.ops[0]._nativeColourRefinement);assert.ok(N.queue(reviewed,env).queue);
 layer.effects.colorOverlay.color='#00ff00';assert.match(N.queue(reviewed,env).error,/changed after/,'Manual change after plan creation blocks actual Run queue');layer.effects.colorOverlay.color='#c8102e';
 epoch++;assert.match(N.queue(reviewed,env).error,/paint changed/);epoch=1;
 assert.equal(E.plan('A darker blue, please.',env).kind,'ask','Different colour cannot silently retarget');
 for(const change of [()=>layer.locked=true,()=>layer.visible=false,()=>layer.effects.colorOverlay.color='#00ff00',()=>epoch++]){
  const saved=JSON.stringify(layer);change();assert.equal(E.plan('Make it darker',env).kind,'ask');Object.assign(layer,JSON.parse(saved));epoch=1;
 }
 assert.equal(F.plan('Make the roof darker',env),null,'Explicit different scope remains with normal parser');
 assert.equal(F.plan('Make it chrome',env),null,'Material requests remain with normal parser');
 assert.equal(F.plan('Make it darker',{...env,last:null}),null,'No remembered layer invented');
 const collision={...layer,id:'other',name:'body'};w._psdLayers=[collision];assert.equal(E.plan('Make it darker',env).kind,'ask','An old ID must not fall back to a different layer whose name matches it');w._psdLayers=[layer];
 w.SPB_CX3_OFF=true;assert.notEqual(E.plan('A darker red, please.',env).ops[0].target.kind,'layer','Existing kill switch bypasses the added resolver');w.SPB_CX3_OFF=false;
 console.log('PASS actual native reply retains exact context; actual parser/compiler refine current layer colour; different colour, lock, hidden, manual colour change and document change refuse. Native UI still separate.');
})().catch(e=>{console.error(e);process.exitCode=1;});
