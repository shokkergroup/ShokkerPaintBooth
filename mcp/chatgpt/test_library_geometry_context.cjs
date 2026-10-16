 'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),C=require('./assistant-context.cjs');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const receipt=JSON.parse(fs.readFileSync(path.join(dir,'paint-subscription-multiturn-after-2026-10-10T21-46-41-064Z.json'),'utf8'));
const original=JSON.parse(receipt.calls.find(c=>c.tool==='spb_get_state').text),saved=JSON.stringify(original);
const response=data=>({content:[{type:'text',text:JSON.stringify(data)}]});
async function main(){
 const packet=await C.build({query:'Where is the hood on this ARCA paint?',include_paint:true},{history:async()=>({turns:[]}),tools:()=>[],call:async name=>response(name==='spb_encyclopedia'?{}:original)});
 assert.equal(packet.editor_capabilities.panel_locations.parts.length,0,'Native legacy library boxes cannot become exact geometry');
 assert.ok(packet.editor_capabilities.panel_locations.withheld_library_parts>0);
 assert.equal(JSON.stringify(original),saved,'The shared source receipt is never changed');
 const small={car:original.car,parts:original.car.parts,template_identity:original.template_identity};
 const compact=await C.build({query:'Which car is open?',include_paint:true},{history:async()=>({turns:[]}),tools:()=>[],call:async name=>response(name==='spb_encyclopedia'?{}:small)});
 for(const snapshot of [compact.paint.status.data,compact.paint.state.data]){
  assert.equal(snapshot.car.geometry_verified,false);assert.equal(snapshot.car.identity_verified,false);assert.equal(snapshot.car.parts,undefined);
  assert.deepEqual(snapshot.parts,[]);assert.equal(snapshot.library_parts_withheld,original.car.parts.length);
  assert.equal(snapshot.template_identity.recognized_layout,undefined);assert.equal(snapshot.template_identity.heuristic_layout.identity_verified,false);
  assert.equal(snapshot.template_identity.source_reference.sha256,original.template_identity.source_reference.sha256,'Exact source evidence remains intact');
 }
 const taught={editor_capabilities:{panel_locations:{status:'current',parts:[{name:'hood',bbox:[.1,.2,.3,.4],evidence:'buyer-taught box'},{name:'roof',bbox:[.4,.5,.6,.7],evidence:'confirmed island label'},{name:'door',bbox:[0,0,1,1],evidence:'active car-library box'}]}}};
 const qualified=await C.build({query:'Where is the hood?',include_paint:true},{history:async()=>({turns:[]}),tools:()=>[],call:async name=>response(name==='spb_encyclopedia'?{}:taught)});
 assert.deepEqual(qualified.editor_capabilities.panel_locations.parts.map(p=>p.name),['hood','roof']);
 assert.equal(qualified.editor_capabilities.panel_locations.withheld_library_parts,1);
 for(const snapshot of [qualified.paint.status.data,qualified.paint.state.data])assert.deepEqual(snapshot.editor_capabilities.panel_locations.parts.map(p=>p.name),['hood','roof'],'Nested paint snapshots cannot bypass geometry qualification');
 console.log('PASS actual ARCA receipt: legacy library coordinates withheld, heuristic identity qualified, exact source hash retained, buyer-confirmed current extents preserved, input immutable.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
