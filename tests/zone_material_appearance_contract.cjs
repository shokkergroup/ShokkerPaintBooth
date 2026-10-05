const assert=require('node:assert/strict');
const api=require('../js/canvas/zone/material-instance-masters.js');
(async()=>{
 const rect={x1:0,y1:0,x2:20,y2:20};
 const make=id=>({version:2,id,sourceBbox:rect,instanceBbox:{x1:30,y1:0,x2:50,y2:20},rotation:30,masterId:'master'});
 const zone={patternInstances:['master','a','b','muted'].map(make)};
 zone.patternInstances[3].muted=true;
 const state={target:'zone_instance:a'},history=[],messages=[];
 let captures=0,frames=0,finishes=0;
 const material=(mode,changedPixels=10)=>({format:'spb-zone-material/1',width:20,height:20,data:'paint-and-spec',operation:{mode,changedPixels,ownedPaintPixels:20,masterPaintPixels:20}});
 const options={capture:async(ids,mode)=>{captures++;assert.deepEqual(ids,['a','b']);return Object.fromEntries(ids.map(id=>[id,material(mode)]));},isCurrent:()=>true,pushUndo:()=>history.push(structuredClone(zone)),applyFrame:()=>frames++,finish:()=>finishes++,notify:m=>messages.push(m)};
 for(const mode of ['tint','hue','saturation','vibrance']){
  const before=structuredClone(zone),count=history.length;
  assert(await api.appearance(zone,state,mode,options));
  assert.equal(history.length,count+1);assert.deepEqual(history.at(-1),before);
  assert.deepEqual(zone.patternInstances[0],before.patternInstances[0]);assert.deepEqual(zone.patternInstances[3],before.patternInstances[3]);
  for(const member of zone.patternInstances.slice(1,3)){
   assert.equal(member.frozenMaterial.operation,undefined);
   assert.deepEqual(member.instanceBbox,before.patternInstances[1].instanceBbox);assert.equal(member.rotation,30);
  }
 }
 assert.equal(captures,4);assert.equal(frames,4);assert.equal(finishes,4);
 const stable=structuredClone(zone);
 for(const result of [null,{a:material('tint')},{a:material('hue'),b:material('hue')}]){
  await assert.rejects(api.appearance(zone,state,'tint',{...options,capture:async()=>result}),/not ready/);
  assert.deepEqual(zone,stable);assert.equal(history.length,4);
 }
 await assert.rejects(api.appearance(zone,state,'tint',{...options,isCurrent:()=>false}),/selected group changed/);
 assert.deepEqual(zone,stable);
 await api.appearance(zone,state,'tint',{...options,capture:async()=>({a:material('tint',0),b:material('tint',0)})});
 assert.match(messages.at(-1),/already match/);assert.equal(history.length,4);assert.equal(finishes,4);
 const noPaint=()=>{const m=material('tint',0);m.operation.ownedPaintPixels=0;return m;};
 await api.appearance(zone,state,'tint',{...options,capture:async()=>({a:noPaint(),b:noPaint()})});
 assert.match(messages.at(-1),/spec-only/);assert.deepEqual(zone,stable);assert.equal(history.length,4);
 let release;
 const pending=api.appearance(zone,state,'tint',{...options,capture:()=>new Promise(resolve=>{release=resolve;})});
 await api.appearance(zone,state,'tint',options);assert.equal(history.length,4,'duplicate pending action is ignored');
 zone.patternInstances[1].rotation=45;
 release({a:material('tint'),b:material('tint')});
 await assert.rejects(pending,/selected group changed/);assert.equal(history.length,4);
 // The pending lock must clear after rejection so retry is possible.
 await api.appearance(zone,state,'tint',options);assert.equal(history.length,5);
 console.log('Zone appearance: batched capture, atomic one-step history, frame/spec payload retention, no-op, spec-only, stale capture and retry pass.');
})().catch(error=>{console.error(error);process.exitCode=1;});
