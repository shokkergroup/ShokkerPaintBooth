'use strict';
// Actual parser, compiler, serializer and layer dispatcher; controlled native setters.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const original=JSON.parse(JSON.parse(read('_codex_mcp_work/chatgpt-dev/59910/paint-arca-native-overlay-pre-2026-10-10T00-30-04-188Z.json')).calls[0].text).layers;
const layers=original.map(l=>({...l,groupName:l.group,visible:!l.hidden,img:{width:2048,height:2048}}));
const w={console,Set,Map,Date,Promise,Uint8Array,document:{readyState:'loading',addEventListener(){},getElementById:()=>null},localStorage:{getItem:()=>null,setItem(){}},setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},addEventListener(){},_psdLayers:layers};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/car-knowledge/layer-reading.js','mcp/chatgpt/candidates/spb-pro-carmap.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','mcp/chatgpt/native-layer-colour.js'])vm.runInContext(read(f),w,{filename:f});
const E=w.SpbProEdit,N=w.SpbNativeLayerColour,roles=w.SpbProCar.roles(),body=layers.find(l=>l.id==='psd_0');
const env={layers:roles,palette:[{hex:'#19376e',share_pct:95}],zoneColours:[]};
env.sourceLayerPixels=id=>({status:'pixels-present',layer:{id},palette:[{colour:'#19376e',share_of_nontransparent_pixels_pct:95}]});
const p=E.plan('Make the Paintable Area / Base Paint layer red',env),q=N.queue(p,env);
assert.equal(q.queue.length,1);assert.equal(q.queue[0].kind,'layer');assert.equal(q.queue[0].layer,'psd_0');assert.equal(q.queue[0].colour,'#c8102e');
assert.equal(N.queue(E.plan('Make the navy in the Paintable Area / Base Paint layer red',env),env),null,'Hue-preserving word-colour requests retain their existing semantics');
const subset=N.queue(E.plan('Make the navy in the Paintable Area / Base Paint layer #b39a58',env),env);assert.equal(subset.queue[0].layer,'psd_0');assert.equal(subset.queue[0].sourceColour,'#19376e');assert.equal(subset.queue[0].colour,'#b39a58','Exact colour subset uses native replacement, not a whole-layer overlay');
assert.equal(N.queue(E.plan('Make the Paintable Area / Base Paint layer chrome',env),env),null,'Finish remains a material route');
assert.match(N.queue(E.plan('Make the Custom Spec Map / Red Channel Metallic / Base Paint layer red',env),env).error,/material/);
assert.ok(N.patch('red').error);assert.ok(N.patch('#ff0000','100').error);assert.ok(N.patch('#ff0000',101).error);
let begins=0;w._layerUndoStack=[];w.Z={quiet:f=>f(),findLayer:id=>layers.find(l=>l.id===id)};w.mcpDocumentMismatch=()=>null;
w.beginLayerAdjustGesture=id=>{begins++;w._layerUndoStack.push({id});return true;};
w.setLayerColorOverlay=(id,patch)=>{const l=layers.find(l=>l.id===id);l.effects={...(l.effects||{}),colorOverlay:{enabled:patch.enabled,color:patch.color,opacity:patch.opacity/100,blendMode:'source-over'}};return true;};
w.endLayerAdjustGesture=()=>true;
function applyFunction(source){const start=source.indexOf('    function applyLayerOps('),end=source.indexOf('    function hasQ(',start);assert.ok(start>=0&&end>start);vm.runInContext(source.slice(start,end),w);}
w.ops=q.queue;
applyFunction(read('js/spb-pro-ai.js'));vm.runInContext('applyLayerOps(ops)',w);assert.equal(begins,1,'Claude adopted the native colour dispatcher');assert.equal(body.effects.colorOverlay.color,'#c8102e');
delete body.effects;begins=0;w._layerUndoStack=[];
applyFunction(read('mcp/chatgpt/candidates/spb-pro-ai.js'));vm.runInContext('applyLayerOps(ops)',w);assert.equal(begins,1);assert.equal(body.effects.colorOverlay.color,'#c8102e');
const offlineNoop=vm.runInContext('applyLayerOps(ops)',w);
assert.equal(offlineNoop.lines.length,0,'Offline no-op must not claim an applied change or earn an Undo');
assert.equal(offlineNoop.undoSteps,0);assert.equal(offlineNoop.colourOutcomes[0].status,'unchanged');
assert.equal(offlineNoop.colourOutcomes[0].render_verified,false);
assert.equal(layers.filter(l=>l.effects).length,1,'Only exact current body layer receives effect');
const serializer=read('mcp/chatgpt/candidates/spb-pro-ai.js').match(/^    function layersInfo\(\).*$/m);assert.ok(serializer);w.CAR=w.SpbProCar;
const state=vm.runInContext(serializer[0]+'\nlayersInfo()',w);assert.equal(state.find(l=>l.id==='psd_0').colour_overlay.colour,'#c8102e');
const before=JSON.stringify(body.effects);body.locked=true;vm.runInContext('applyLayerOps(ops)',w);assert.equal(begins,1);assert.equal(JSON.stringify(body.effects),before);body.locked=false;
w.ops=[{...q.queue[0],colour:'#00ff00',_mcpTarget:{ref:body,id:body.id}}];w.mcpDocumentMismatch=()=>'changed document';vm.runInContext('applyLayerOps(ops,{})',w);assert.equal(begins,1);assert.equal(JSON.stringify(body.effects),before);
w.mcpDocumentMismatch=()=>null;vm.runInContext('applyLayerOps(ops,{})',w);assert.equal(begins,2);assert.equal(body.effects.colorOverlay.color,'#00ff00');
const mcpNoop=vm.runInContext('applyLayerOps(ops,{})',w);
assert.equal(mcpNoop.lines.length,0,'MCP no-op applied list must be empty');
assert.equal(mcpNoop.undoSteps,0);assert.equal(mcpNoop.colourOutcomes[0].status,'unchanged');
assert.match(mcpNoop.colourOutcomes[0].line,/no colour change/);
assert.equal(N.outcome({layer:'psd_0',name:'Base Paint',sourceColour:'#ff0000',colour:'#000000'},{error:'Locked'}).status,'failed');
const tools=JSON.parse(read('mcp/server/tools.json'));const t=N.tool(tools.find(t=>t.name==='spb_edit_layer'));assert.equal(t.inputSchema.properties.colour.pattern,'^#[0-9a-fA-F]{6}$');
// Execute the real exact-Undo functions, including the original false-success case.
function undoFunctions(source){
 for(const name of ['layerState','layerSame','undoApply']){
  const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    function ',start+1);
  assert.ok(start>=0&&end>start);vm.runInContext(source.slice(start,end),w);
 }
}
w.zones=[];w.undoZoneFrom=()=>{throw Error('This fixture has no zones');};w.selectedZoneIndex=0;w.renderZones=()=>{};w.triggerPreviewRender=()=>{};w._finishLayerVisibilityChange=()=>{};
delete body.effects;undoFunctions(read('js/spb-pro-ai.js'));
w.snap={zones:[],layers:vm.runInContext('layerState()',w)};
N.apply(q.queue[0],body);w.aft={zones:[],layers:vm.runInContext('layerState()',w)};
vm.runInContext('undoApply(snap,aft,true,true)',w);assert.equal(body.effects,undefined,'Claude adopted the colour-effect Undo fix');
delete body.effects;undoFunctions(read('mcp/chatgpt/candidates/spb-pro-ai.js'));
w.snap={zones:[],layers:vm.runInContext('layerState()',w)};N.apply(q.queue[0],body);w.aft={zones:[],layers:vm.runInContext('layerState()',w)};
vm.runInContext('undoApply(snap,aft,true,true)',w);assert.equal(body.effects,undefined,'Candidate restores original absence of effects');
body.effects={colorOverlay:{enabled:true,color:'#123456',opacity:.4},stroke:{enabled:true,width:3}};
w.snap={zones:[],layers:vm.runInContext('layerState()',w)};const oldEffects=JSON.stringify(body.effects);
N.apply(q.queue[0],body);w.aft={zones:[],layers:vm.runInContext('layerState()',w)};
vm.runInContext('undoApply(snap,aft,true,true)',w);assert.equal(JSON.stringify(body.effects),oldEffects,'Nested effects are copied and restored');
N.apply(q.queue[0],body);w.aft={zones:[],layers:vm.runInContext('layerState()',w)};body.effects.stroke.width=8;
vm.runInContext('undoApply(snap,aft,true,false)',w);assert.equal(body.effects.stroke.width,8,'Later effect ownership stays intact');
console.log(JSON.stringify({pass:true,actual_id:'psd_0',native_colour_queue:true,shared_native_colour_and_undo_adopted:true,offline_and_mcp_dispatch:true,lock_and_document_guards:true,live_effect_snapshot:true,subset_and_material_routes_preserved:true,native_pixels:false}));
