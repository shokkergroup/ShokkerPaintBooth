'use strict';
// W80 independent review: actual Runtime3 E planner/compiler plus the W79
// queueEditZones implementation, with a manually authored green roof zone.
// No add/edit handler applies pixels; the test observes the proposal only.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const oraclePath='_easy_claude_work/ai14h_w80_review/fresh-oracle.json';
const oracleBytes=fs.readFileSync(path.join(root,oraclePath));
const oracle=JSON.parse(oracleBytes.toString('utf8'));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(digest(oracleBytes),'773912FBA0EF84D428CFBE20E21302DB11A9F3D6F7194810DB952113468D06EB');
assert.equal(oracle.cases.length,12);
const proPath='_easy_claude_work/ai14h_generation3_candidate/w79_overlap/js/spb-pro-ai.js';
const ePath='_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-edit.js';
const dPath='_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-design.js';
const pro=fs.readFileSync(path.join(root,proPath),'utf8'), eBytes=fs.readFileSync(path.join(root,ePath)), dBytes=fs.readFileSync(path.join(root,dPath));
assert.equal(digest(fs.readFileSync(path.join(root,proPath))),'B4A519D02419F6E5B21A9BC0DE6488C3124D7F3FC1BB2B52738F27B2F0617D1E','W79 candidate source unchanged');
const H=require('../_easy_claude_work/stack_h.js'),w=H.load();
vm.runInContext(dBytes.toString('utf8'),w,{filename:dPath});
vm.runInContext(eBytes.toString('utf8'),w,{filename:ePath});
const E=w.SpbProEdit; assert(E&&typeof E.plan==='function'&&typeof E.compile==='function');
const env={palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#eeeeee',share_pct:11}],layers:[],zoneColours:[{hex:'#168a45',zone_id:'manual-green-roof',zone:'Roof green',index:1,share_pct:12,selects_pct:12,finish:'base::gloss',layers:[]}]};
const asks=[
 'Make only the roof chrome, keep its current paint.',
 'Make the roof chrome while keeping its current paint.',
 'Make only the roof chrome.',
 'Make only the roof blue.'
];
const planned=asks.map(ask=>{const p=E.plan(ask,env),c=p&&p.kind==='ops'?E.compile(p,env):null;return {ask,plan:p,compiled:c};});
for(const i of [0,1]){
 const z=planned[i].compiled.zones[0];
 assert.equal(planned[i].plan.exactPart,true,asks[i]);
 assert.equal(z.region.part,'roof');
 assert.equal(z.color,'source','preservation phrase currently compiles to source-color part zone');
 assert.equal(z.finish,'base::f_chrome');
 assert.equal(z._meta.zoneEdit,undefined,'manual existing zone is not selected as a zoneEdit');
 assert.equal(!!z._meta.partZoneProof,false,'no verified helper owner proof is attached');
}
// Execute the real W79 queue function over the real compiled zone proposal.
// addFn is a boundary recorder, so nothing is applied or rendered.
const start=pro.indexOf('    function partRegionKey('),end=pro.indexOf('\n    // ------------------------------------------------------------------ NUMBERS ON A FLAT PAINT',start);
assert(start>=0&&end>start,'W79 part/queue function slice exists');
const queueSource=pro.slice(start,end);
const qctx=vm.createContext({Object,String,RegExp,JSON,Array,Number,Math,Error,Uint8Array,console});
vm.runInContext(queueSource+`\nvar zones=[{id:'manual-green-roof',name:'Roof green',muted:false,baseColorMode:'solid',baseColor:'#168a45',base:'base::gloss',useRegion:true,regionMask:new Uint8Array([1,1,1,1])},{id:'manual-side',name:'Side white',muted:false,baseColorMode:'solid',baseColor:'#eeeeee',useRegion:true,regionMask:new Uint8Array([0,1,0,1])}];
var _editReg={},_editRegSig='car-A',_editRegPendingBefore={},CAR={},window={},added=[],edited=[];
function carSig(){return 'car-A';} function normaliseSpec(s){return s;} function protectDecals(){return null;}
function friendlyZoneError(e){return String(e);} function editPlural(){return false;}
function scopedPartProofAt(){return null;} function scopedPartProofMatches(){return false;}
function addFn(s){added.push(JSON.parse(JSON.stringify(s)));return {region_check:{share_pct:12}};}
function editFn(s){edited.push(JSON.parse(JSON.stringify(s)));return {};}
this.runQueue=function(zs){return queueEditZones({zones:zs},addFn,editFn,{});};
this.out=function(){return {added:added,edited:edited};};`,qctx);
const queueResult=qctx.runQueue([planned[0].compiled.zones[0]]),qout=qctx.out();
assert.equal(queueResult.errs.length,0);
assert.equal(qout.added.length,1,'real W79 queue selects add path when manual roof lacks registry/provenance');
assert.equal(qout.edited.length,0,'manual zone is not silently adopted as helper owner');
assert.equal(qout.added[0].region.part,'roof');
assert.equal(qout.added[0].color,'source');
assert.equal(qout.added[0].finish,'base::f_chrome');
// Explicit recolor is a positive control: it names a new desired color, so
// source paint cannot be mistaken for preservation of authored green.
assert.equal(planned[3].compiled.zones[0].color,'#1450b4');
assert.equal(planned[3].compiled.zones[0].region.part,'roof');
const result={
 status:'FINDING_SOURCE_COLOR_PRESERVATION_UNPROVEN',
 oracle:{path:oraclePath,sha256:digest(oracleBytes),cases:oracle.cases.length},
 sourcePins:{w79ProAi:{path:proPath,sha256:digest(Buffer.from(pro))},runtime3ProEdit:{path:ePath,sha256:digest(eBytes)},runtime3ProDesign:{path:dPath,sha256:digest(dBytes)}},
 exercised:{planner:'actual Runtime3 SpbProEdit.plan/compile',queue:'actual queueEditZones extracted from pinned W79 proAI',manualFixture:'unique manually authored solid-green roof zone, no _aiPartProv or edit registry; unrelated manual side zone present',application:'not applied; add/edit callbacks only record proposed specs',providerCalls:0,nativeCalls:0},
 observations:asks.slice(0,3).map((ask,i)=>({ask,plan:planned[i].plan&&planned[i].plan.kind,exactPart:!!(planned[i].plan&&planned[i].plan.exactPart),compiled:planned[i].compiled&&planned[i].compiled.zones.map(z=>({color:z.color,finish:z.finish,region:z.region,zoneEdit:z._meta.zoneEdit||null,partZoneProof:!!z._meta.partZoneProof}))})),
 queue:{errors:queueResult.errs,addCount:qout.added.length,editCount:qout.edited.length,proposed:qout.added.map(z=>({name:z.name,color:z.color,finish:z.finish,region:z.region}))},
 control:{ask:asks[3],compiledColor:planned[3].compiled.zones[0].color,part:planned[3].compiled.zones[0].region.part},
 limits:['This proves the helper queue proposes a new Foundation/source-color roof zone despite the request to keep current paint; it does not render or apply that zone, so no pixel-level outcome is claimed.','The W79 queue does not adopt the manual zone, which is correct for ownership. The unresolved issue is that the compiled source-color addition can still be queued without proving preservation of the manual authored color.','A narrower safe behavior is to refuse/ask when an explicit keep-current-paint instruction targets a part with no unique verified current owner, rather than adopting arbitrary manual zones or adding source-color overlay.','The weaker-save/reopen variant remains in scope: without durable helper ownership and fresh geometry/source proof, authored color still exists but must not be treated as a verified reusable helper owner.']
};
console.log(JSON.stringify(result,null,2));
