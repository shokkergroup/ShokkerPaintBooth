const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('js/spb-quests.js','utf8');
const start=source.indexOf('var probes = {'),end=source.indexOf('// ==========================================================================',start);
const qstart=source.indexOf('var QUESTS = ['),qend=source.indexOf('var CORE_IDS',qstart);
const ctx={window:{},zones:[],selectedZoneIndex:0,$:()=>null,document:{querySelector:()=>null},findByText:()=>null};
vm.runInNewContext(source.slice(start,end)+source.slice(qstart,qend),ctx);
const claim=ctx.QUESTS.find(q=>q.id==='q-zone'),finish=ctx.QUESTS.find(q=>q.id==='q-finish');
function check(zones,claimed,finished){ctx.zones=zones;const before=structuredClone(zones);assert.equal(!!claim.done(),claimed);assert.equal(!!finish.done(),finished);assert.deepEqual(zones,before,'guide probes never mutate Zone data');}
check([{colorMode:'special',base:'gloss'}],false,false);
check([{regionMask:new Uint8Array(8),base:'chrome'}],false,false);
check([{regionMask:new Uint8Array([0,255]),useRegion:false,base:'chrome'}],false,false);
check([{regionMask:new Uint8Array([0,128])}],true,false);
check([{regionMask:new Uint8Array([0,255]),useRegion:true,finish:'dry_brush'}],true,true);
check([{regionMask:new Uint8Array([255]),base:'none',finish:'none'}],true,false);
check([{regionMask:new Uint8Array([255])},{colorMode:'special',base:'chrome'}],true,false);
check([{colorMode:'picker',base:'chrome'}],true,true);
check([{colors:[[10,20,30]],finish:'pearl'}],true,true);
let counted=0;ctx.window.SPBMaskStats={any:mask=>{counted++;return mask.some(v=>v>0);}};
check([{regionMask:new Uint8Array([0,1]),base:'chrome'}],true,true);assert.ok(counted>0,'use shared mask stats for loaded runtime');
ctx.zones=[{regionMask:new Uint8Array(4)}];assert.equal(ctx.probes.zoneRestricted(),false,'empty mask is not a completed refine step');
assert.match(claim.body,/Rectangle/);assert.match(claim.body,/Lasso/);
console.log('Guide: actual quest completion accepts color or active drawn masks, rejects empty/default/disabled scope, requires finish on same claimed Zone, stays read-only.');

function decl(name){const start=source.indexOf('function '+name+'(');let pos=source.indexOf('{',start),depth=1,end=pos+1;for(;depth;end++){if(source[end]==='{')depth++;if(source[end]==='}')depth--;}return source.slice(start,end);}
let selectedRowClick=null,spotlights=0;
const row={getAttribute:()=> 'q-zone',addEventListener:(type,fn)=>{selectedRowClick=fn;}};
const panel={style:{},innerHTML:'',querySelectorAll:()=>[row]};
Object.assign(ctx,{state:{panelOpen:true,wheelsOn:true,questsDone:{'q-zone':true},activeQuest:'q-zone'},
 $:id=>id==='spbGuidePanel'?panel:null,questById:id=>ctx.QUESTS.find(q=>q.id===id),
 CORE_IDS:['q-load','q-zone','q-finish','q-setup','q-render'],coreComplete:()=>false,
 questRowHtml:()=>'',allComplete:()=>false,lsSave(){},render(){},api:{showMe(){spotlights++;}}});
vm.runInNewContext(decl('renderPanel'),ctx);ctx.renderPanel();
assert.match(panel.innerHTML,/Either method completes this step/);
assert.match(panel.innerHTML,/✓ done/);assert.doesNotMatch(panel.innerHTML,/I did it/,'review cannot award the same completion twice');
ctx.state.activeQuest=null;ctx.renderPanel();assert.equal(typeof selectedRowClick,'function');
selectedRowClick();assert.equal(ctx.state.activeQuest,'q-zone');assert.equal(spotlights,1);
assert.deepEqual(ctx.state.questsDone,{'q-zone':true},'review preserves completion');
console.log('Guide review: completed row opens its instructions and spotlight without resetting or recounting progress.');

const events=new Map(),frames=new Map();let frameId=0,bounds={left:100,top:400,width:200,height:30};
const target={isConnected:true,scrollIntoView(){},getBoundingClientRect:()=>bounds,focus(){}};
const spot={_ring:null,_ringTimer:null,_ringCleanup:null,setTimeout:()=>1,clearTimeout(){},
 window:{scrollX:0,scrollY:0,requestAnimationFrame:fn=>{frames.set(++frameId,fn);return frameId;},cancelAnimationFrame:id=>frames.delete(id),addEventListener:(n,fn)=>events.set(n,fn),removeEventListener:n=>events.delete(n)},
 document:{createElement:()=>({style:{},setAttribute(){}}),body:{appendChild(r){r.parentNode={removeChild(){r.parentNode=null;}};},},addEventListener:(n,fn)=>events.set(n,fn),removeEventListener:n=>events.delete(n)}};
vm.runInNewContext(decl('spotlight')+decl('clearRing'),spot);spot.spotlight(target);
assert.equal(spot._ring.style.top,'394px');bounds.top=200;events.get('scroll')();events.get('scroll')();
assert.equal(frames.size,1,'coalesce scrolling instead of measuring every event');
const callback=frames.values().next().value;frames.clear();callback();assert.equal(spot._ring.style.top,'194px','ring follows scrolled control');
events.get('resize')();spot.clearRing();assert.equal(events.size,0);assert.equal(frames.size,0);assert.equal(spot._ring,null);
console.log('Guide spotlight: follows nested scrolling, coalesces frames, releases listeners and pending work on dismissal.');

const load=ctx.QUESTS.find(q=>q.id==='q-load');
ctx.$=()=>({value:'C:/missing-paint.tga'});ctx.paintImageData=null;
ctx._psdLayers=[{img:{}}];ctx._psdLayersLoaded=false;
assert.equal(load.done(),false,'a filename or partial layer decode is not a loaded document');
ctx.paintImageData={width:2,height:2,data:new Uint8Array(8)};assert.equal(load.done(),false,'incomplete flat buffer');
ctx.paintImageData={width:2,height:2,data:new Uint8Array(16)};assert.equal(load.done(),true,'blank canvas is usable paint');
ctx.$=()=>null;assert.equal(load.done(),true,'live pixels do not require a filename');
ctx.paintImageData=null;ctx._psdLayersLoaded=true;assert.equal(load.done(),true,'completed PSD stack is usable');
ctx._psdLayers=[];assert.equal(load.done(),false,'empty loaded flag alone is insufficient');
console.log('Guide load: requires usable flat pixels or completed Layer stack; excludes stale paths and partial loads.');
