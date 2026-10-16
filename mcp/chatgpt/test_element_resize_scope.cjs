'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const query='Make the sponsor logos on the Contingency Decals layer 10 percent smaller without moving their centres.';
const raw=[{id:'decal',name:'Car_Decal'},{id:'logos',name:'Color Change Logos'},{id:'contingency',name:'Contingency Decals'}].map(l=>({...l,groupName:'Paintable Area',visible:true,locked:false,img:{width:100,height:100}}));
function harness(candidate){
 const layers=raw.map(l=>({...l})),roles=()=>layers.map(l=>({...l,role:'decals / logos',group:l.groupName}));
 const w={console,Promise,Set,Map,Date,Uint8Array,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},localStorage:{getItem:()=>null,setItem(){}},document:{readyState:'loading',addEventListener(){},getElementById:()=>null},_psdLayers:layers};w.window=w;vm.createContext(w);
 const load=f=>vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w,{filename:f});
 for(const f of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','js/spb-encyclopedia-data.js',candidate?'mcp/chatgpt/candidates/spb-offline-builder.js':'js/spb-offline-builder.js','js/spb-enc-search.js',candidate?'mcp/chatgpt/candidates/spb-offline-answer.js':'js/spb-offline-answer.js'])load(f);
 if(candidate)load('mcp/chatgpt/element-resize-scope.js');
 let epoch=1;w.SpbConversationScope={observe(){},stamp:()=>epoch,current:x=>x===epoch};w.SpbProCar={roles};
 const source=fs.readFileSync(path.join(root,candidate?'mcp/chatgpt/candidates/spb-offline-builder.js':'js/spb-offline-builder.js'),'utf8');
 // Invoke the actual selector and run dispatcher, replacing only pixel writes.
 const a=source.indexOf('    var W20_KRX ='),b=source.indexOf('    var W20_SHEET',a);
 const c=source.indexOf('    function w20xRunSteps()'),d=source.indexOf('    // ===== SPB_W20X-END',c);
 vm.runInContext(source.slice(a,b)+source.slice(c,d),w);w.W=w;
 const ai=fs.readFileSync(path.join(root,'mcp/chatgpt/candidates/spb-pro-ai.js'),'utf8');
 const push=ai.match(/_push:\s*(function\s*\(e\)\s*\{.*?\})\s*\/\* APPCHAT/);assert.ok(push,'Actual chat push API found');
 Object.assign(w,{_aicSeq:0,_log:[],render(){}});w.spbProAI={_push:vm.runInContext('('+push[1]+')',w)};
 const ua=source.indexOf('    function undoChanged('),ub=source.indexOf('    function sourceChanged(',ua);
 vm.runInContext(source.slice(ua,ub),w);w.s3Ran=()=>null;
 const writes=[];Object.assign(w,{S:{steps:[],msg:''},readAs:()=>query,tlStart(){},draw(){},w20xScaleLayer:(l)=>{writes.push(l.id);return {changed:true,pieces:1};},w20xRestoreLayer:l=>{writes.push(l.id);return 'ok';}});
 return {w,layers,writes,roles,epoch:()=>{epoch++;},route:text=>w.SpbOfflineAnswer.route(text,{layers:roles(),palette:[],zoneColours:[]}),run:r=>{w.S.steps=r.steps;return w.w20xRunSteps();}};
}
const old=harness(false),oldPlan=old.route(query);assert.equal(oldPlan.cls,'DO',JSON.stringify(oldPlan));old.run(oldPlan);assert.deepEqual(old.writes,['decal','logos','contingency'],'Reproduce explicit target widening in the actual original executor');
const h=harness(true),plan=h.route(query);assert.equal(plan.cls,'DO',JSON.stringify(plan));assert.deepEqual(Array.from(plan.steps[0].extra.w20x.layer_ids),['contingency']);assert.match(plan.steps[0].extra.s5g,/Contingency Decals layer/);h.run(plan);assert.deepEqual(h.writes,['contingency']);
assert.equal(h.w.S.ran.eid,h.w._log[0].id);assert.ok(h.w.S.ran.eid);
assert.equal(h.w.undoChanged({id:h.w.S.ran.eid+1}),false);
assert.equal(h.w.undoChanged(h.w._log[0]),true);assert.equal(h.w.S.ran.undone,true);
const locked=harness(true),lockedPlan=locked.route(query);locked.layers[2].locked=true;locked.run(lockedPlan);assert.equal(locked.writes.length,0);assert.match(locked.w.S.msg,/locked/);assert.equal(locked.route(query).cls,'ASK');
const missing=harness(true),missingPlan=missing.route(query);missing.layers.pop();missing.run(missingPlan);assert.equal(missing.writes.length,0);assert.match(missing.w.S.msg,/missing/);
const changed=harness(true),changedPlan=changed.route(query);changed.epoch();changed.run(changedPlan);assert.equal(changed.writes.length,0);assert.match(changed.w.S.msg,/paint changed/);
const all=harness(true),allPlan=all.route('Make all the logos 10 percent smaller');all.layers[1].locked=true;all.run(allPlan);assert.equal(all.writes.length,0,'Batch lock refusal precedes every write');
const duplicate=harness(true);duplicate.layers.push({...duplicate.layers[2],id:'other',groupName:'Other'});assert.equal(duplicate.route(query).cls,'ASK');
const exact=duplicate.route('Make the sponsor logos on the Paintable Area / Contingency Decals layer 10 percent smaller');assert.equal(exact.cls,'DO',JSON.stringify(exact));duplicate.run(exact);assert.deepEqual(duplicate.writes,['contingency']);
assert.equal(h.route('Make the sponsor logos on the Missing layer 10 percent smaller').cls,'ASK');
const source=fs.readFileSync(path.join(root,'js/spb-offline-builder.js'),'utf8').replace(/\r\n/g,'\n'),candidate=fs.readFileSync(path.join(__dirname,'candidates/spb-offline-builder.js'),'utf8');
for(const [start,end] of [['    function w20xScaleGroupsPx','    var W20_ORIG'],['    function w20xScaleLayer','    function w20xRestoreLayer']])assert.ok(source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start)))===candidate.slice(candidate.indexOf(start),candidate.indexOf(end,candidate.indexOf(start))),'Shared resize raster algorithm must remain untouched');
// Exercise the actual funnel draw prefix through its hide decision.
const pbn=fs.readFileSync(path.join(__dirname,'candidates/spb-pbn.js'),'utf8');
const pa=pbn.indexOf('    function draw()'),pb=pbn.indexOf('        var en = env()',pa);
function funnel(state,kill=false){const dock={},c={W:{SPB_CX3_OFF:kill},S:{text:query},CUR:{old:true},ensureDock:()=>dock,OB:()=>({offlineMode:()=>true,state:()=>state}),builderBusy:()=>false};vm.createContext(c);vm.runInContext(pbn.slice(pa,pb)+'}',c);c.draw();return dock.hidden;}
const ready={text:query,steps:plan.steps};assert.equal(funnel(ready),true);
for(const changedState of [{...ready,text:'Older request'},{...ready,liveText:'New request'},{...ready,msg:'Locked'},{...ready,steps:[]}])assert.equal(funnel(changedState),false);
assert.equal(funnel(ready,true),false,'Existing CX3 kill switch preserved');
console.log('PASS actual original vs candidate Offline route/executor: named-layer resize narrowed from3 layers to1; full-group ambiguity, missing target, locks before any batch write, and changed document refuse. Raster kernel unchanged; native pixels remain a separate gate.');
