'use strict';
// Actual model normalizer, frame validator, planner, text reader and MCP dispatcher.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),w={console,Promise,Set,Map,Date,Uint8Array,localStorage:{getItem:()=>null},document:{getElementById:()=>null}};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','mcp/chatgpt/native-layer-colour.js','mcp/chatgpt/candidates/spb-intent-frame.js','mcp/chatgpt/candidates/spb-intent-plan.js','mcp/chatgpt/candidates/spb-intent-model.js','mcp/chatgpt/candidates/spb-mcp-frames.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w,{filename:f});
const layers=[{id:'psd_0',name:'Body',role:'bodypaint'},{id:'psd_1',name:'Numbers',role:'numbers'},{id:'psd_2',name:'Sponsors',role:'sponsors'}];
w.SpbProCar={roles:()=>layers,parts:()=>[]};
const frame=()=>({v:1,act:'change',decals:'protect',ops:[{verb:'recolour',target:{kind:'layer',layers:['psd_0']},look:{colour:{hex:'#B49A55'}}}]});
const text='Make only the Body layer #B49A55. Keep the Numbers and Sponsors layers exactly unchanged.';
let writes=0,actual;
const host={layers:()=>layers,planRun:true,apply:q=>{writes++;actual=q;return Promise.resolve({ok:true,result:{applied:['Body colour']}});}};
(async()=>{
 const dry=await w.SpbMcpFrames.doCall({text,frame:frame(),dry_run:true},host);
 assert.equal(dry.ok,true,JSON.stringify(dry));assert.match(dry.result.applied_as,/native layer/);assert.equal(writes,0);
 const applied=await w.SpbMcpFrames.doCall({text,frame:frame()},host);
 assert.equal(applied.ok,true,JSON.stringify(applied));assert.equal(writes,1);assert.equal(actual.length,1);assert.equal(actual[0].kind,'layer');assert.equal(actual[0].layer,'psd_0');assert.equal(actual[0].colour,'#b49a55');assert.equal(actual._s5plan,undefined);assert.match(applied.result.applied_as,/native layer/);
 for(const words of ['Make the Body layer #000000.','Make the Sponsors layer #B49A55.','Make Body layer #B49A55. Keep Body layer exactly unchanged.','Make Body layer #B49A55. Keep Missing layer exactly unchanged.']){
  const r=await w.SpbMcpFrames.doCall({text:words,frame:frame()},host);assert.equal(r.ok,false,words);assert.equal(writes,1);
 }
 layers[0].locked=true;const locked=await w.SpbMcpFrames.doCall({text,frame:frame()},host);assert.equal(locked.ok,false);assert.match(locked.error,/locked/);assert.equal(writes,1);layers[0].locked=false;
 const mixed=frame();mixed.ops[0].look.finish={family:'chrome'};assert.equal(w.SpbNativeLayerColour.frameQueue(mixed,text,{layers}),null,'Material requests keep the material planner');
 const keep=frame();keep.keep=[{kind:'part',parts:['roof']}];assert.equal(w.SpbNativeLayerColour.frameQueue(keep,text,{layers}),null,'Never drop geometric exclusions');
 const subset=frame();subset.ops[0].target.kind='colour';assert.equal(w.SpbNativeLayerColour.frameQueue(subset,text,{layers}),null);
 w.SPB_CX3_OFF=true;const killed=await w.SpbMcpFrames.doCall({text,frame:frame(),dry_run:true},host);assert.match(killed.result.applied_as,/planner run/);assert.equal(writes,1);
 w.SPB_CX3_OFF=false;let entry=null,undoCalls=0,seen=[];w.SPB_AI_REPORT='enforce';
 w.SpbIntentReport={check:(e,t,r,ctx)=>{seen.push({text:t,queue:r.queue,mode:w.SPB_AI_REPORT});ctx.undo();return Promise.resolve({v:1,verdict:'reported',changed:100,paint:100,decal:2,layers:['Body'],whole:false,findings:[],line:'Preview differences need review.'});}};
 const measuredHost={...host,last:()=>entry,log:()=>entry?[entry]:[],ctx:()=>({undo:()=>{undoCalls++;}}),apply:q=>{entry={role:'ai',id:12,lines:['Body colour'],zdiff:{s3b:{}},undoable:true};return Promise.resolve({ok:true,result:{applied:['Body colour']}});}};
 const measured=await w.SpbMcpFrames.doCall({text,frame:frame()},measuredHost);
 assert.equal(measured.result.changed,true);assert.ok(measured.result.measured.decal_px>0);assert.equal(measured.result.measured.scope.whole_car,false);assert.equal(undoCalls,0);assert.equal(seen[0].mode,'warn');assert.equal(seen[0].text,text);assert.equal(seen[0].queue[0].kind,'layer');assert.equal(w.SPB_AI_REPORT,'enforce');
 await w.SpbMcpFrames.checkCall({fresh:true},measuredHost);assert.equal(seen[1].text,text);assert.equal(seen[1].queue[0].layer,'psd_0');assert.equal(undoCalls,0);
 console.log('PASS actual MCP native layer frame: dry-run, exact ID/colour, text agreement, preserved-layer conflict, missing layer, lock, material/subset/exclusion routing, kill switch. Native pixels tested separately.');
})().catch(e=>{console.error(e);process.exitCode=1;});
