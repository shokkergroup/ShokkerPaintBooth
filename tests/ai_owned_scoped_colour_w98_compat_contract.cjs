'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const designPath='_easy_claude_work/ai14h_w89_review/base/spb-pro-design.js';
const oldEditPath='_easy_claude_work/ai14h_w89_review/candidate/spb-pro-edit.js';
const editPath='_easy_claude_work/ai14h_w98_review/candidate/spb-pro-edit.js';
const controllerPath='_easy_claude_work/ai14h_w89_review/candidate/spb-pro-ai.js';
const canvasPath='_easy_claude_work/ai14h_w76_review/frozen/paint-booth-3-canvas.js';
const oraclePath='_easy_claude_work/ai14h_w98_review/fresh-oracle.json';
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex').toUpperCase();
assert.equal(sha(designPath),'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8');
assert.equal(sha(oldEditPath),'3696CF6C9BDF9A28A056EBF90A9DDD23CFE290134943C11BEB4C7EC5485A173A');
assert.equal(sha(controllerPath),'FA51053AD77409AA677A9E2D8EF633FD6D6BCD20E5DCDF5628AF40C65B37DC59');
assert.equal(sha(canvasPath),'1BD43BAF7D1BDAC1E07417D6FF6B30F71E78F1FF9169987C03198DD63DC2D4DA');
assert.equal(sha(oraclePath),'15413B4795CE8759B6A4CB15AAC6CED628B6089C757EFCE99B481E20430F67B1');
const oracle=JSON.parse(fs.readFileSync(path.join(root,oraclePath),'utf8'));
function loadEdit(p){const w={console};w.window=w;vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(root,designPath),'utf8'),w);vm.runInContext(fs.readFileSync(path.join(root,p),'utf8'),w);return w.SpbProEdit;}
const oldE=loadEdit(oldEditPath),E=loadEdit(editPath);
function safeProof(zoneId,part='roof',hex='#1f8a3b',fp='file-sha256:'+'a'.repeat(64),extra={}){
 const source={path:'C:/car.psd',fingerprint:fp,generation:7,width:2048,height:2048};
 return Object.assign({schema:'spb-scoped-part-proof/1',id:zoneId,zone_id:zoneId,key:'roof-key',part,source,storedPartSource:{...source},car:'car-sig',layout:'layout-sig',element:'',selector:JSON.stringify({island:part,layers:['Car Paint']}),zoneMask:'2048:part-mask',partMask:'2048:part-mask',layers:{ids:['paint-layer-id'],states:[{id:'paint-layer-id',visible:true,locked:false}]},appearance:{baseColorMode:'solid',baseColor:hex,base:'f_chrome',finish:'',specShiftR:0,specShiftG:0,specShiftB:0,muted:false,useRegion:true,baseColorStrength:1,baseStrength:1},footprint:{share_pct:2.9,visible_pct:2.9}},extra);
}
function fixture(proof,opts={}){
 const zoneColours=opts.noOwner?[]:[{zone_id:'roof1',zone:'Saved green roof',hex:'#1f8a3b',share_pct:2.9,selects_pct:2.9,finish:'f_chrome',layers:['Car Paint']}];
 return {palette:[{hex:'#01ff00',name:'bright green',share_pct:28},{hex:'#1450b4',name:'blue',share_pct:3}],layers:[],zoneColours,currentPartZoneOwners(parts,hits){return proof?(opts.duplicateProof?[proof,opts.duplicateProof]:[proof]):[];}};
}
function compile(Engine,proof,opts={},text='Make green on the roof blue'){const env=fixture(proof,opts),plan=Engine.plan(text,env);return Engine.compile(plan,env);}
function accepted(c,id){assert.equal(c.ask,null,id+' should compile without clarification');assert.equal(c.zones.length,1,id+' edits only the proven owner');const z=c.zones[0];assert.equal(z._meta.zoneEdit.zone_id,'roof1');assert.equal(z._meta.partZoneProof.zone_id,'roof1');assert.equal(String(z.color).toLowerCase(),'#1450b4');assert.equal(z.finish,undefined,'existing finish is preserved');assert.equal(z._meta.zoneEdit.hex,'#1f8a3b','proof continues to bind to the existing solid hex');}
function refused(c,id){assert.equal(c.zones.length,0,id+' must not fall through to source-region paint');assert.ok(c.ask,id+' must ask when proof is unusable');}
const rows=[];
// Verify the reported regression against the unchanged W89 validator and the
// candidate behavior against the exact accepted current-client fingerprints.
const fileProof=safeProof('roof1');accepted(compile(E,fileProof),'W98-10-file-sha256');
const fpSha='composite-sha256:'+'b'.repeat(64),shaProof=safeProof('roof1','roof','#1f8a3b',fpSha);
refused(compile(oldE,shaProof),'baseline-composite-sha256');accepted(compile(E,shaProof),'candidate-composite-sha256');
const fpFnv='composite-fnv1a32:fnv1a32-1a47e90b-3',fnvProof=safeProof('roof1','roof','#1f8a3b',fpFnv);
refused(compile(oldE,fnvProof),'baseline-composite-fnv1a32');accepted(compile(E,fnvProof),'candidate-composite-fnv1a32');
rows.push({id:'W98-01',baseline:'refused composite-sha256',candidate:'exact owner recolor',fingerprint:fpSha});
rows.push({id:'W98-02',baseline:'refused composite-fnv1a32',candidate:'exact owner recolor',fingerprint:fpFnv});
rows.push({id:'W98-10',candidate:'exact owner recolor',fingerprint:fileProof.source.fingerprint});
const negatives=[
 ['W98-03-missing-fingerprint',safeProof('roof1','roof','#1f8a3b','')],
 ['W98-03-unrecognized-fingerprint',safeProof('roof1','roof','#1f8a3b','browser-file:C:/car.psd')],
 ['W98-04-stale-generation',safeProof('roof1','roof','#1f8a3b',fpSha,{storedPartSource:{path:'C:/car.psd',fingerprint:fpSha,generation:6,width:2048,height:2048}})],
 ['W98-04-pending-zero-generation',safeProof('roof1','roof','#1f8a3b',fpSha,{source:{path:'C:/car.psd',fingerprint:fpSha,generation:0,width:2048,height:2048}})],
 ['W98-05-mask-mismatch',safeProof('roof1','roof','#1f8a3b',fpSha,{zoneMask:'changed',partMask:'2048:part-mask'})],
 ['W98-05-layout-missing',safeProof('roof1','roof','#1f8a3b',fpSha,{layout:''})],
 ['W98-05-car-signature-missing',safeProof('roof1','roof','#1f8a3b',fpSha,{car:''})],
 ['W98-04-source-path-mismatch',safeProof('roof1','roof','#1f8a3b',fpSha,{storedPartSource:{path:'C:/other.psd',fingerprint:fpSha,generation:7,width:2048,height:2048}})],
 ['W98-04-source-dimensions-mismatch',safeProof('roof1','roof','#1f8a3b',fpSha,{storedPartSource:{path:'C:/car.psd',fingerprint:fpSha,generation:7,width:1024,height:2048}})],
 ['W98-04-stored-fingerprint-mismatch',safeProof('roof1','roof','#1f8a3b',fpSha,{storedPartSource:{path:'C:/car.psd',fingerprint:'composite-sha256:'+'f'.repeat(64),generation:7,width:2048,height:2048}})],
 ['W98-05-empty-layer-ids',safeProof('roof1','roof','#1f8a3b',fpSha,{layers:{ids:[],states:[{id:'paint-layer-id',visible:true,locked:false}]}})],
 ['W98-05-empty-layer-states',safeProof('roof1','roof','#1f8a3b',fpSha,{layers:{ids:['paint-layer-id'],states:[]}})],
 ['W98-06-proof-zone-id-mismatch',safeProof('roof1','roof','#1f8a3b',fpSha,{zone_id:'roof2',id:'roof2'})],
 ['W98-06-duplicate-proofs',safeProof('roof1','roof','#1f8a3b',fpSha),{duplicateProof:safeProof('roof1','roof','#1f8a3b',fpSha)}],
 ['W98-06-partial-footprint',safeProof('roof1','roof','#1f8a3b',fpSha,{footprint:{share_pct:2.9,visible_pct:1.2}})],
 ['W98-06-strength-mismatch',safeProof('roof1','roof','#1f8a3b',fpSha,{appearance:{baseColorMode:'solid',baseColor:'#1f8a3b',base:'f_chrome',finish:'',muted:false,useRegion:true,baseColorStrength:0.8,baseStrength:1}})]
];
for(const entry of negatives){const [id,p,opts={}]=entry;refused(compile(E,p,opts),id);rows.push({id,queueZones:0,clarification:true});}
// Newly-created owners and normal no-owner source-region behavior remain distinct.
accepted(compile(E,safeProof('roof1','roof','#1f8a3b',fpSha)),'W98-07-new-current-owner');
rows.push({id:'W98-07',candidate:'proof-backed newly registered owner recolor',fingerprint:fpSha});
const sourceOnly=compile(E,null,{noOwner:true});assert.equal(sourceOnly.zones.length,1);assert.equal(sourceOnly.zones[0].region.part,'roof');assert.ok(!sourceOnly.zones[0]._meta.partZoneProof);
rows.push({id:'W98-source-only',candidate:'existing source-color part route preserved',region:sourceOnly.zones[0].region});
const pendingMemoryAsk=compile(E,null,{},'Make green on the roof blue while keeping the original source paint');
assert.equal(pendingMemoryAsk.zones.length,0,'unresolved keep-original-source-paint request cannot queue a partial recolor');
assert.ok(pendingMemoryAsk.ask,'pending memory/source-paint ambiguity must be clarified');
rows.push({id:'W98-09',candidate:'zero-zone clarification when current proof is unavailable during pending keep-original-source-paint',text:pendingMemoryAsk.ask.text});
// The durable memory identity gate remains stronger for layered-source rebind.
const csrc=fs.readFileSync(path.join(root,controllerPath),'utf8'),canvasSrc=fs.readFileSync(path.join(root,canvasPath),'utf8');
function extractFrom(src,name){const start=src.indexOf('function '+name+'(');assert(start>=0);const brace=src.indexOf('{',start);let depth=0,q=null,esc=false;for(let i=brace;i<src.length;i++){const ch=src[i];if(q){if(esc)esc=false;else if(ch==='\\')esc=true;else if(ch===q)q=null;continue;}if(ch==='"'||ch==="'")q=ch;else if(ch==='{')depth++;else if(ch==='}'&&--depth===0)return src.slice(start,i+1);}throw Error('unterminated '+name);}
const dctx=vm.createContext({String});vm.runInContext(extractFrom(csrc,'durablePartMemorySourceIdentityCurrent')+';this.durable=durablePartMemorySourceIdentityCurrent;',dctx);
assert.equal(dctx.durable('layered',fpSha),false,'durable layered memory must reject composite digest');
assert.equal(dctx.durable('layered',fpFnv),false,'durable layered memory must reject FNV composite digest');
assert.equal(dctx.durable('layered',fileProof.source.fingerprint),true,'durable layered memory still accepts strong file SHA identity');
const fctx=vm.createContext({Object,String});vm.runInContext(extractFrom(canvasSrc,'_spbLayeredSourceFingerprint')+';this.fingerprint=_spbLayeredSourceFingerprint;',fctx);
const clientStrong=fctx.fingerprint({sourceBytesSha256:'c'.repeat(64)},'d'.repeat(64));
const clientCompositeSha=fctx.fingerprint({},'b'.repeat(64));
const clientCompositeFnv=fctx.fingerprint({},'fnv1a32-1a47e90b-3');
assert.equal(clientStrong,'file-sha256:'+'c'.repeat(64));assert.equal(clientCompositeSha,fpSha);assert.equal(clientCompositeFnv,fpFnv);
assert.throws(()=>fctx.fingerprint({sourceBytesSha256:'C'.repeat(64)},'e'.repeat(64)),/invalid source byte fingerprint/);
rows.push({id:'W98-08',durableLayeredCompositeSha:'reject',durableLayeredCompositeFnv:'reject',durableLayeredFileSha:'accept'});
rows.push({id:'W98-client-source-format',clientStrong,clientCompositeSha,clientCompositeFnv,malformedStrongRejected:true});
console.log(JSON.stringify({status:'PASS_WITH_LIMITS_PRIVATE_W98_COMPATIBILITY',oracleCases:oracle.cases.length,oracleSha256:sha(oraclePath),baselineCompositeCasesRejected:2,candidateCompositeCurrentSessionCasesAccepted:2,candidateFileShaCaseAccepted:1,negativeProofControls:negatives.length,sourceOnlyControl:1,pendingMemoryClarification:1,durableMemoryFileGate:'PASS',rows,pins:{design:{path:designPath,sha256:sha(designPath)},editBase:{path:oldEditPath,sha256:sha(oldEditPath)},editCandidate:{path:editPath,sha256:sha(editPath)},controllerDurableGate:{path:controllerPath,sha256:sha(controllerPath)},currentClientFingerprint:{path:canvasPath,sha256:sha(canvasPath)}},limits:['Actual frozen SpbProEdit.plan/compile and the W89 proof-shape validator run. currentPartZoneOwners is represented by a controlled callback returning proof objects; this is not a native currentPartZoneOwners/apply test.','Current source/generation/mask/layout/layer/owner/strength/footprint fields remain required and are mismatch-tested at E.compile. The parent W89 current-owner proof logic remains responsible for proving those fields against live committed state.','The pending keep-original-source-paint case models unresolved proof as an empty current-owner result at the actual compile boundary; it does not execute the project-memory load lifecycle or native route.','The durable identity predicate is extracted from frozen W89 controller code and tested for layered records only; no save/load or durable project round-trip occurred.','No source was written/applied, no provider, server, native app, or renderer was invoked.']},null,2));
