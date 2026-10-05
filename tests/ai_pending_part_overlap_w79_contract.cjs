'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const helper=fs.readFileSync('tests/ai_source_bytes_part_memory_w76_review_contract.cjs','utf8');
const start=helper.indexOf('function extractFunction('),end=helper.indexOf('\nconst canvas=',start);
const extract=vm.runInNewContext(helper.slice(start,end)+'\nextractFunction',{assert});
const candidatePath=process.argv[2]||'_easy_claude_work/ai14h_generation3_candidate/w79_overlap/js/spb-pro-ai.js';
const candidate=fs.readFileSync(candidatePath,'utf8'),baseline=fs.readFileSync('_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-ai.js','utf8');
const cases=[
 {id:'saved-upper-request-whole',old:{part:'roof',portion:'upper'},now:{part:'roof'},blocked:true},
 {id:'saved-whole-request-upper',old:{part:'roof'},now:{part:'roof',portion:'upper'},blocked:true},
 {id:'different-band-unproved',old:{part:'roof',band:{from:0,to:.4}},now:{part:'roof',band:{from:.7,to:1}},blocked:true},
 {id:'different-color-unproved',old:{part:'roof',colors:['#ff0000']},now:{part:'roof',colors:['#00ff00']},blocked:true},
 {id:'different-layer-unproved',old:{part:'roof',layers:['old-body']},now:{part:'roof',layers:['new-body']},blocked:true},
 {id:'array-part-intersection',old:{part:['roof','hood']},now:{part:'roof'},blocked:true},
 {id:'island-part-alias',old:{island:'roof',portion:'upper'},now:{part:'roof'},blocked:true},
 {id:'sides-left-intersection',old:{part:'both sides'},now:{part:'left'},blocked:true},
 {id:'normalized-spaces-intersection',old:{part:'LEFT_SIDE',portion:'front'},now:{part:'left side'},blocked:true},
 {id:'unrelated-part-allowed',old:{part:'hood'},now:{part:'roof'},blocked:false},
 {id:'opposite-side-allowed',old:{part:'left side'},now:{part:'right side'},blocked:false},
 {id:'explicit-color-command-allowed',old:{part:'roof',portion:'upper'},now:{part:'roof'},color:'#123456',blocked:false}
];
function run(source,c){
 const code=['partRegionKey','editKey','hasPriorPartIdentity','queueEditZones'].map(n=>extract(source,'function '+n+'(')).join('\n');
 const ctx=vm.createContext({Object,String,RegExp,JSON,Array,Number,Math,Error,Uint8Array});
 vm.runInContext(code+`\nvar zones=[{id:'saved-part',name:'Saved part',muted:false,useRegion:true,regionMask:new Uint8Array([1]),_spbAIPartMemoryPending:{provenance:{r:${JSON.stringify(JSON.stringify(c.old))}}}}];var _editReg={},_editRegSig='car',_editRegPendingBefore={};var CAR={},window={},adds=[];function carSig(){return 'car';}function scopedPartProofAt(){return null;}function scopedPartProofMatches(){return false;}function friendlyZoneError(e){return String(e);}function editPlural(){return false;}function add(spec){adds.push(spec);return {region_check:{share_pct:40}};}function edit(){return {};};this.run=function(){return queueEditZones({zones:[{name:'Requested part',region:${JSON.stringify(c.now)},color:${JSON.stringify(c.color||'source')},_meta:{label:'part',kind:'colour'}}]},add,edit,{});};this.out=function(){return {adds:adds,pending:zones[0]._spbAIPartMemoryPending};};`,ctx);
 const before=JSON.stringify(ctx.out().pending),result=ctx.run(),out=ctx.out();assert.equal(JSON.stringify(out.pending),before,'pending ownership must stay inert');return {queued:out.adds.length,errors:result.errs};
}
const rows=cases.map(c=>{const old=run(baseline,c),now=run(candidate,c);assert.equal(now.queued,c.blocked?0:1,c.id);assert.equal(now.errors.length,c.blocked?1:0,c.id);return {id:c.id,baselineQueued:old.queued,candidateQueued:now.queued,verdict:'PASS'};});
assert.equal(rows.length,12);assert(rows.some(x=>x.baselineQueued!==x.candidateQueued),'must expose baseline failure');
console.log(JSON.stringify({status:'PASS_WITH_LIMITS',cases:rows.length,candidatePath,candidateSha256:crypto.createHash('sha256').update(fs.readFileSync(candidatePath)).digest('hex'),rows,limitation:'Actual queue function with controlled handlers, no renderer/mask overlap proof/native/provider'},null,2));
