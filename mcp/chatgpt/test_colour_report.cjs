'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),N=256;
let epoch=1,after,undo=0,render=0,wait=()=>Promise.resolve(),surface=null;
const before=new Uint8ClampedArray(N*N*4);
for(let i=0;i<N*N;i++)before.set(i<60000?[25,55,110,255]:[255,255,255,255],i*4);
const img={complete:true,naturalWidth:256},w={console,Promise,Date,Uint8Array,Uint8ClampedArray,
 document:{getElementById:id=>id==='paintCanvas'?{width:N,height:N}:id==='livePreviewImg'?img:null,
 createElement:()=>({getContext:()=>({drawImage(){},getImageData:()=>({data:after.slice()})})})},
 SpbConversationScope:{stamp:()=>epoch,current:s=>s===epoch},
 SpbProCar:{roles:()=>[],paintableMask:()=>surface,maskFor:()=>null},
 SpbProZone:{whenSettled:()=>wait()},zones:[]};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/layer-targets.js','mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','mcp/chatgpt/colour-report-scope.js','mcp/chatgpt/candidates/spb-intent-report.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w);
const R=w.SpbIntentReport,text='Change the navy areas to red. Keep the off white and white marks unchanged.';
function entry(id=1){return {id,lines:['Navy shifted to red'],text:'Done — navy shifted to red.',zdiff:{s3b:{p:before,s:null,documentStamp:epoch}}};}
function ctx(e){return {synced:()=>true,undo(){undo++;e.undone=true;},reseal(){},render(){render++;}};}
function red(spill=false){after=before.slice();for(let i=0;i<(spill?N*N:60000);i++)after.set([220,25,35,255],i*4);}
(async()=>{
 red();let e=entry(),r=await R.check(e,text,{offline:true,queue:[]},ctx(e));
 assert.equal(r.verdict,'ok');assert.equal(undo,0);assert.equal(r.colour_target,'navy');assert.equal(r.outside,0);assert.equal(r.coverage_unit,'preview');assert.equal(r.coverage_cells,N*N);assert.ok(r.paint<=r.coverage_cells);assert.match(r.line,/navy areas changed to red/);assert.match(r.line,/preview/);
 assert.equal(w.SpbColourReportScope.read('Make the hood red',before),null);
 assert.equal(w.SpbColourReportScope.read('Make the whole car red',before),null);
 assert.equal(w.SpbColourReportScope.read('Do not paint navy red',before),null);
 assert.equal(w.SpbColourReportScope.read('Make white red. Keep white unchanged.',before),null);
 R._reset();red(true);e=entry(2);r=await R.check(e,text,{offline:true,queue:[]},ctx(e));
 assert.equal(r.verdict,'undo-ask');assert.equal(undo,1);assert.ok(r.findings.some(x=>x.code==='spill'));assert.equal(e.undone,true);
 // A part/object request with the same large coverage keeps the original gate.
 R._reset();red();e=entry(3);r=await R.check(e,'Tint the windshield blue chrome',{offline:true,queue:[]},ctx(e));
 assert.ok(r.findings.some(x=>x.code==='unasked-whole'));assert.equal(r.verdict,'undo-ask');assert.ok(!r.findings.some(x=>x.pct>100));
 // Known paintable coverage counts only changes inside that same surface.
 R._reset();surface=new Uint8Array(N*N);surface.fill(1,0,10000);red();e=entry(4);r=await R.check(e,text,{offline:true,queue:[]},ctx(e));
 assert.equal(r.coverage_cells,10000);assert.equal(r.surface_paint,10000);assert.match(r.line,/100%/);surface=null;
 // Old settling callbacks cannot undo, rewrite, log or consume a new pending check.
 R._reset();let oldResolve,newResolve;wait=()=>new Promise(resolve=>{oldResolve=resolve;});red();const old=entry(5),oldText=old.text;
 const pOld=R.check(old,'Tint the windshield blue chrome',{offline:true,queue:[]},ctx(old));assert.equal(R.pending(),1);
 epoch++;R._reset();wait=()=>new Promise(resolve=>{newResolve=resolve;});const newer=entry(6),pNew=R.check(newer,text,{offline:true,queue:[]},ctx(newer));
 const priorUndo=undo,priorRender=render;oldResolve();const stale=await pOld;assert.equal(stale.verdict,'skip');assert.equal(old.text,oldText);assert.equal(undo,priorUndo);assert.equal(render,priorRender);assert.equal(R.since(0).length,0);assert.equal(R.pending(),1);
 newResolve();assert.equal((await pNew).verdict,'ok');assert.equal(R.pending(),0);assert.equal(R.since(0).length,1);
 // Actual subscription edit_layer omitted buyer_said: the executed target still exists.
 const fixture=JSON.parse(fs.readFileSync(path.join(root,'_codex_mcp_work/chatgpt-dev/59910/paint-source-report-preflight-2026-10-10T06-47-49-632Z.json'),'utf8'));
 const rows=JSON.parse(fixture.calls[0].text).layers;
 w.SpbProCar.roles=()=>rows;w.SpbProZone.findLayer=id=>rows.find(l=>l.id===id);
 w.getZoneSourceLayersUnionMask=q=>({union:Uint8Array.from({length:N*N},()=>q.sourceLayer==='psd_23'?255:0)});
 const q=[{kind:'layer',layer:'psd_23',colour:'#b39a58',sourceColour:'#ff0000'}];
 let scoped=R.scopeOf('',{queue:q},entry(7));assert.equal(scoped.src,'plan');assert.deepEqual(Array.from(scoped.layers),['psd_23']);assert.equal(scoped.parts.length,0);
 assert.equal(R.scopeOf('',{queue:[{...q[0],layer:'missing'}]},entry(7)).src,null,'Missing identity cannot grant report scope');
 R._reset();wait=()=>Promise.resolve();red();e=entry(7);r=await R.check(e,'',{offline:false,queue:q},ctx(e));
 assert.equal(r.verdict,'ok');assert.deepEqual(Array.from(r.layers),['psd_23']);assert.match(r.line,/car_pattern_001\.tga layer/);assert.doesNotMatch(r.line,/hood|roof|both sides|whole car/);
 // A valid native target is not blanket permission for changes outside its mask.
 w.getZoneSourceLayersUnionMask=q=>({union:Uint8Array.from({length:N*N},(_,i)=>q.sourceLayer==='psd_23'&&i<10000?255:0)});
 R._reset();red();e=entry(8);r=await R.check(e,'',{offline:false,queue:q},ctx(e));
 assert.ok(r.findings.some(f=>f.code==='spill'));assert.ok(r.findings.some(f=>f.code==='unasked-whole'));assert.equal(r.verdict,'undo-ask');
 // Rechecking must retain the executed native scope, not invent unasked-whole.
 w.getZoneSourceLayersUnionMask=()=>({union:Uint8Array.from({length:N*N},()=>255)});
 async function freshRound(file){
  vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w);
  R._reset();red();const e9=entry(9);e9.role='ai';
  const ops=[{kind:'layer',layer:'psd_23',colour:'#b39a58',sourceColour:'#ff0000'}];
  const host={ctx:()=>ctx(e9),log:()=>[e9]};
  const first=await w.SpbMcpFrames.measureOnly(e9,'',ops,host);
  assert.deepEqual(Array.from(first.scope.layers),['psd_23']);
  ops[0].layer='psd_38'; // A later caller mutation cannot change stored evidence.
  return (await w.SpbMcpFrames.checkCall({fresh:true},host)).result.measured;
 }
 assert.equal((await freshRound('js/spb-mcp-frames.js')).scope.layers.length,0,'Original recheck drops executed target');
 const rechecked=await freshRound('mcp/chatgpt/candidates/spb-mcp-frames.js');
 assert.deepEqual(Array.from(rechecked.scope.layers),['psd_23']);
 assert.match(rechecked.line,/car_pattern_001\.tga layer/);
 assert.ok(!rechecked.findings.some(f=>/unasked-whole/.test(f)));
 // Root negative control drops that same exact native queue target.
 vm.runInContext(fs.readFileSync(path.join(root,'js/spb-intent-report.js'),'utf8'),w);
 assert.equal(w.SpbIntentReport.scopeOf('',{queue:q},entry(7)).layers.length,0);
 console.log('PASS actual S3 verifier: explicit dominant-colour request survives; off-target spill still undoes; unknown coverage uses preview; known coverage cannot exceed100%; retired async check cannot alter/log/undo the next document');
})().catch(e=>{console.error(e);process.exitCode=1;});
