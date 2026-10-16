'use strict';
// Run the real queue prefix through its before-shot and layer dispatch boundaries.
// This checks ordering; it does not substitute for native preview measurements.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function run(file,{synced=true,layer=true,zone=false}={}){
 const source=fs.readFileSync(file,'utf8'),start=source.indexOf('    function applyQueue('),end=source.indexOf('        var slines =',start);
 assert.ok(start>=0&&end>start);
 const events=[],shot={p:'before paint',s:'before spec'};
 const w={_gen:0,window:{},zones:zone?[{id:'zone-1'}]:[],zoneUndoStack:[],_layerUndoStack:[],
  undoSnapTake:()=>({}),zoneHashNow:()=>{events.push('hash');return 'before';},rshotFor:()=>{events.push('complaint-shot');return 'before';},
  previewSynced:()=>synced,SpbIntentReport:{snap:()=>{events.push('report-shot');return shot;}},
  applyLayerOps:()=>{events.push('layer-edit');synced=false;return {lines:['applied'],failed:[],undoSteps:1};},
  zsnap:z=>({...z})};
 w.window.SpbIntentReport=w.SpbIntentReport;
 vm.createContext(w);vm.runInContext(source.slice(start,end)+'return {zdiff:zdiff,lres:lres};\n}',w);
 const q=[];if(layer)q.push({kind:'layer'});if(zone)q.push({kind:'edit',zone:0});
 const result=w.applyQueue(q,'test',false);
 return {result,events,shot};
}
const original=run('js/spb-pro-ai.js');assert.equal(original.result.zdiff.s3b,undefined,'Negative control: layer invalidates preview before old capture');
const candidate='mcp/chatgpt/candidates/spb-pro-ai.js';
for(const zone of [false,true]){
 const r=run(candidate,{zone});assert.equal(r.result.zdiff.s3b,r.shot);
 assert.ok(r.events.indexOf('report-shot')<r.events.indexOf('layer-edit'));
 assert.equal(r.events.filter(x=>x==='layer-edit').length,1);
}
const stale=run(candidate,{synced:false});assert.equal(stale.result.zdiff.s3b,undefined,'Unsynced preview cannot become a before shot');
assert.ok(!stale.events.includes('report-shot'));
const zonesOnly=run(candidate,{layer:false,zone:true});assert.equal(zonesOnly.result.zdiff.s3b,zonesOnly.shot);
assert.ok(!zonesOnly.events.includes('layer-edit'));
console.log(JSON.stringify({pass:true,actual_queue_prefix:true,original_missing_shot:true,layer_and_mixed_queue_capture_before_edit:true,stale_preview_refused:true,native_measurement:false}));
