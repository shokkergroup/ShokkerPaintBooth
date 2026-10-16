'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),C=require('./assistant-context.cjs');
const root=path.resolve(__dirname,'../..');
let identity={path:'fixture.psd',fingerprint:'first',generation:1};
const w={console,Date,Math,JSON,Set,Map,setTimeout(){},setInterval(){},document:{readyState:'loading',addEventListener(){},querySelector(){return null},getElementById(){return null}},localStorage:{getItem:k=>k==='SPB_CONVO'?'1':null,setItem(){}},SPBSourceLoadTransaction:{getCommittedPath:()=>identity.path,getCommittedFingerprint:()=>identity.fingerprint,getGeneration:()=>identity.generation},zones:[{id:'z1',name:'Everything Else',pattern:'checker',scale:.465,sourceLayers:['body']}],_psdLayers:[{id:'body',name:'Body',groupName:'Paintable Area',visible:true},{id:'numbers',name:'Numbers',visible:true}],PATTERNS:[{id:'checker',name:'Diner Checkerboard'}]};
w.window=w;vm.createContext(w);
for(const f of ['js/spb-convo-state.js','mcp/chatgpt/conversation-scope.js','mcp/chatgpt/editor-capabilities.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w,{filename:f});
const api=w.SpbEditorCapabilities,plain=x=>JSON.parse(JSON.stringify(x)),before=JSON.stringify({zones:w.zones,layers:w._psdLayers});
assert.equal(api.read().recent_change.available,false);
assert.match(api.answer('What did you just change?').answer.text,/No change is recorded/);
w.SpbConvo.fromEntry({id:'u1',role:'ai',request:'Make it a little finer.',lines:['Edited pattern'],zdiff:{added:[],edited:[{id:'z1',name:'Everything Else'}]}},{offline:true,queue:[{kind:'edit',zone:'z1',spec:{pattern:{id:'checker',scale:.465}}}]},'Make it a little finer.');
assert.equal(w.SpbConvo.view().last_change.targets,'','Actual edit adapter retains zone IDs but has no region-derived target label');
let e=api.read().recent_change;
assert.equal(e.record.request,'Make it a little finer.');assert.equal(e.record.marked_undone,false);assert.equal(e.zones[0].current_name,'Everything Else');assert.equal(e.zones[0].current_source_layers[0].current_name,'Body');assert.equal(e.zones[0].current_primary_pattern.scale,.465);
w.SPB_CONVO='0';assert.equal(api.read().recent_change.available,false);assert.match(api.answer('What did you just change?').answer.text,/unavailable or disabled/);w.SPB_CONVO='1';
assert.match(api.answer('What was the latest edit? Explain only.').answer.text,/Everything Else[\s\S]*Paintable Area \/ Body[\s\S]*scale 0.465[\s\S]*does not supply before\/after/);
assert.match(api.answer('What was the latest edit?').answer.text,/Diner Checkerboard/);assert.ok(!api.answer('What was the latest edit?').answer.text.includes('[z1]'),'Internal IDs belong to evidence, not customer wording');
for(const q of ['What did you just change? Then paint the car red.','What did you just change and undo it','Undo that','Make it finer','Which zone did that affect? Then delete it','What is my last change? Apply it again.'])assert.equal(api.answer(q),null,q);
assert.equal(JSON.stringify({zones:w.zones,layers:w._psdLayers}),before);
// Names are explicitly current; the historical record and request stay intact.
w.zones[0].name='Renamed zone';w._psdLayers[0].name='Renamed Body';w.zones[0].muted=true;w.zones[0].locked=true;
e=api.read().recent_change;assert.equal(e.zones[0].current_name,'Renamed zone');assert.equal(e.zones[0].current_source_layers[0].current_name,'Renamed Body');assert.equal(e.record.request,'Make it a little finer.');assert.match(api.answer('What did that change?').answer.text,/currently muted and locked/);
w.SpbConvo.undone('u1');w.zones[0].scale=.6;e=api.read().recent_change;assert.equal(e.record.marked_undone,true);assert.equal(e.zones[0].current_primary_pattern.scale,.6);assert.match(api.answer('Was that undone?').answer.text,/marked undone/);w.SpbConvo.redone('u1');assert.equal(api.read().recent_change.record.marked_undone,false);
const realZone=w.zones[0];w.zones.push({...realZone,name:'Duplicate'});assert.equal(api.read().recent_change.zones[0].resolution,'ambiguous');assert.match(api.answer('Which zone did that affect?').answer.text,/cannot name/);w.zones=[];assert.equal(api.read().recent_change.zones[0].resolution,'missing');
w.zones=Array.from({length:1001},(_,i)=>({id:'other'+i}));w.zones[1000]=realZone;assert.equal(api.read().recent_change.zones[0].resolution,'not_found_in_bounded_inventory');
w.zones=[realZone];w._psdLayers.push({...w._psdLayers[0]});assert.equal(api.read().recent_change.zones[0].current_source_layers[0].resolution,'ambiguous');w._psdLayers=[];assert.equal(api.read().recent_change.zones[0].current_source_layers[0].resolution,'missing');
// Long names and many exact selectors cannot overwhelm common retrieval.
w._psdLayers=Array.from({length:8},(_,i)=>({id:'l'+i,name:'N'.repeat(100),groupName:'G'.repeat(100)}));
w.zones=Array.from({length:6},(_,i)=>({id:'wide'+i,name:'Z'.repeat(200),sourceLayers:w._psdLayers.map(l=>l.id)}));
w.SpbConvo.commit({said:'A recorded edit',zone_ids:w.zones.map(z=>z.id)});
const bounded=api.read().recent_change;assert.ok(bounded.omitted_zone_records>0);assert.ok(JSON.stringify(bounded.zones).length<5100);assert.match(api.answer('What was the latest edit?').answer.text,/omitted/);
// Real committed-document invalidation resets the shared log, even if IDs recur.
identity={path:'another.psd',fingerprint:'second',generation:2};w.SpbConversationScope.sourceCommitted();assert.equal(api.read().recent_change.available,false);assert.match(api.answer('What did you just change?').answer.text,/No change is recorded/);
w.SPB_CX3_OFF=true;assert.equal(api.answer('What did you just change?'),null);assert.equal(api.read().recent_change.available,false);w.SPB_CX3_OFF=false;
// Failed binding is not allowed to leak a matching historical ID.
w.SpbConvo.commit({said:'Previous edit',zone_ids:['z1'],undo_id:'u2'});w.spbProAI={};identity={path:'third.psd',fingerprint:'third',generation:3};w.SpbConversationScope.sourceCommitted();assert.equal(api.read().recent_change.available,false);assert.match(api.read().recent_change.reason,/binding is unavailable/);
async function main(){
 const data={editor_capabilities:{recent_change:e},convo:{last_change:{targets:'',zone_ids:['z1']}}},response=x=>({content:[{type:'text',text:JSON.stringify(x)}]});
 const packet=await C.build({query:'What did you just change?',include_paint:true},{history:async()=>({}),tools:()=>[],call:async(name)=>response(name==='spb_get_state'?data:{})});
 assert.deepEqual(packet.editor_capabilities.recent_change,plain(e));assert.match(packet.guidance.join(' '),/Never replay a recorded request/);
 console.log('PASS actual blank-label log resolved by exact current IDs; Undo/rename/missing/duplicate/bounded/document-reset/kill guards; no mutation or edit authority; common MCP context retains evidence.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
