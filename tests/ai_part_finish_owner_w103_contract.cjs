'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'), oraclePath='_easy_claude_work/ai14h_w97_review/fresh_oracle.json';
const basePath='_easy_claude_work/ai14h_w97_review/spb-pro-ai-integration13.js', candidatePath='_easy_claude_work/ai14h_w103_candidate/spb-pro-ai.js';
const bytes=fs.readFileSync(path.join(root,oraclePath)), hash=b=>crypto.createHash('sha256').update(b).digest('hex');
assert.equal(hash(bytes),'869a86262cdc76a794c74fb7c09ce9589ea64f9a6f3e03676c0f9e8cd8bac5de','fresh W97 oracle changed');
const oracle=JSON.parse(bytes);assert.equal(oracle.cases.length,12);
const dPath='_easy_claude_work/ai14h_generation3_candidate/integration13/js/spb-pro-design.js',ePath='_easy_claude_work/ai14h_w98_review/candidate/spb-pro-edit.js';
const dsrc=fs.readFileSync(path.join(root,dPath),'utf8'),esrc=fs.readFileSync(path.join(root,ePath),'utf8');
assert.equal(hash(Buffer.from(dsrc)),'4648de3231015497cc9ff816612a542097a1ad14038a7210753f6cdbfd88d832');
assert.equal(hash(Buffer.from(esrc)),'7d063444021f8f4144b96130800badfe62741cdefc9104417f3e99af65270767');
const mode='candidate', controllerPath='_easy_claude_work/ai14h_w103_candidate/spb-pro-ai.js';
const csrc=fs.readFileSync(path.join(root,controllerPath),'utf8');
function extract(source,name){const start=source.indexOf(`function ${name}(`);assert(start>=0,'function '+name+' exists');const brace=source.indexOf('{',start);let depth=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw Error('unterminated '+name);}
const controllerFns=['scopedPartSourceNow','scopedPartLayersNow','scopedPartSelectorLayerIds','scopedPartAppearance','scopedPartJson','partOwnerCurrent','scopedPartProofCurrent','scopedPartProofMatches','scopedPartProofAt','currentPartZoneOwners','bodyLayerNames','partRegionKey','editKey','hasPriorPartIdentity','queueEditZones'];
const results=[];
function fhash(a){let h=2166136261>>>0;for(const v of a)h=Math.imul(h^((Number(v)||0)&255),16777619)>>>0;return a.length+':'+h.toString(36);}
function run(c){
 const mask=new Uint8Array([1,0,1,0]), source={generation:8,path:'C:/cars/owned.psd',fingerprint:process.env.W103_FINGERPRINT||('file-sha256:'+'a'.repeat(64)),width:2048,height:2048};
 const part=c.id==='same-roof-alias-control'?'hood':'roof', layer={id:'paint-layer-id',name:'Car Paint',visible:true,locked:false,opacity:100};
 const selector={island:part,layers:['Car Paint']}, key=JSON.stringify({x:[],c:[],l:['Car Paint'],p:part,e:false,el:'',pr:'{}'});
 const otherLayer={id:'numbers-layer-id',name:'Number Paint',visible:true,locked:false,opacity:100}; const zone={id:'zone-'+part,name:'Helper '+part,region:selector,regionMask:new Uint8Array(mask),useRegion:true,muted:false,baseColorMode:'solid',baseColor:'#1f8a3b',base:'base::gloss',finish:'base::gloss',baseColorStrength:1,baseStrength:1,specShiftR:0,specShiftG:0,specShiftB:0};
 const provenance={r:JSON.stringify(selector),z:fhash(zone.regionMask),p:fhash(mask),l:'layout-current',e:'element-current',car:'car-current',s:source,layers:['paint-layer-id'],layerState:[{id:'paint-layer-id',visible:true,locked:false,opacity:100}]};
 zone._aiPartProv=provenance;zone._aiPartSource=Object.assign({},source);
 const zones=[zone],registry={};registry[key]=zone.name;
 const ctx={console,Promise,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,ArrayBuffer,Date,window:null,document:{getElementById:()=>({width:2048,height:2048})},_psdLayers:[layer,otherLayer],_psdPath:source.path,zones,_editReg:registry,_editRegPendingBefore:{},_editRegSig:'car-current',_busy:false,
  CAR:{layoutSig:()=> 'layout-current',roles:()=>[{role:'body paint',name:'Car Paint',visible:true}],maskFor:()=>({mask:new Uint8Array(mask)}),missing:()=>[]},
  Z:{footprint:()=>({share_pct:4.2,visible_pct:4.2}),findLayer:n=>String(n)==='Car Paint'||String(n)==='paint-layer-id'?layer:(String(n)==='Number Paint'||String(n)==='numbers-layer-id'?otherLayer:null),validate:()=>({errors:[]}),catchAll:()=>null},
  SPBSourceLoadTransaction:{isCommitted:()=>true,getGeneration:()=>8,getCommittedGeneration:()=>8,getCommittedPath:()=>source.path,getCommittedFingerprint:()=>source.fingerprint,getCommittedKind:()=> 'psd'},getCurrentSourcePaintFile:()=>source.path,
  SpbProElements:{sig:()=> 'element-current'},zoneSourceLayerIds:()=>['paint-layer-id'],carSig:()=> 'car-current',
  operationTicket:()=>({ok:true}),operationCurrent:()=>true,operationPublish:(t,fn)=>fn(),normaliseSpec:x=>x,protectDecals(){},editPlural:()=>false,friendlyZoneError:e=>String(e),wantsDecalsToo:()=>false,bodyLayerNames:null,
  _spbOperation:null
 };
 if(c.id==='partial-roof-owner')ctx.Z.footprint=()=>({share_pct:4.2,visible_pct:2.1});
 if(c.id==='stale-source-owner'){const old=Object.assign({},source,{generation:7,path:'C:/cars/old.psd'});provenance.s=old;zone._aiPartSource=old;}
 if(c.id==='duplicate-roof-owners'){const dup=JSON.parse(JSON.stringify(zone));dup.id='muted-duplicate';dup.muted=true;dup.regionMask=new Uint8Array(zone.regionMask);dup._aiPartProv=JSON.parse(JSON.stringify(provenance));dup._aiPartSource=Object.assign({},source);zones.push(dup);}
 if(c.id==='manual-roof-zone'){zones[0]._aiPartProv=null;zones[0]._aiPartSource=null;}
 if(c.id==='stale-layout-owner'){provenance.l='layout-old';}
 if(c.id==='hidden-body-layer-owner'){ctx._psdLayers[0].visible=false;ctx.CAR.roles=()=>[];}
 if(c.id==='mixed-paint-owner'){zone.baseColorMode='gradient';}
 ctx.window=ctx;vm.createContext(ctx);vm.runInContext(dsrc,ctx,{filename:dPath});vm.runInContext(esrc,ctx,{filename:ePath});
 for(const n of controllerFns)vm.runInContext(extract(csrc,n),ctx,{filename:'W97#'+n});
 const D=ctx.SpbProDesign,E=ctx.SpbProEdit,text=c.text,env={palette:[{hex:'#1f8a3b',name:'green',share_pct:4.2}],layers:[layer,otherLayer],zoneColours:[]},planned=E.plan(text,env);if(!planned)return {parseFailure:true,planned:null,compiled:null,queued:{errs:['E.plan did not recognize the frozen route case']},added:[],edited:[],zone,zones};const compiled=E.compile(planned,env); if(c.selector&&compiled.zones&&compiled.zones.length) compiled.zones[0].region=c.selector;
 const added=[],edited=[];let name='';const queued=ctx.queueEditZones({zones:compiled.zones},s=>{added.push(s);return {ok:true,index:1,name:s.name,region_check:{share_pct:4.2}};},a=>{edited.push(a);return {ok:true};});
 return {planned,compiled,queued,added,edited,zone,zones};
}
for(const c of oracle.cases){const r=run(c);let pass=false,detail='';if(c.id.includes('keep-paint')||c.id==='roof-ordinary-finish'||c.id==='same-roof-alias-control'){const part=c.id==='same-roof-alias-control'?'hood':'roof';pass=!r.parseFailure&&r.queued.errs.length===0&&r.edited.length===1&&r.added.length===0&&String(r.edited[0].zone_id)==='zone-'+part&&r.edited[0].finish&&String(r.edited[0].finish).includes(c.id.includes('satin')?'satin':c.id.includes('gloss')?'gloss':'chrome')&&!r.edited[0].color&&!!r.edited[0]._spbScopedPartProof;detail=JSON.stringify({parseFailure:!!r.parseFailure,errors:r.queued.errs,adds:r.added.length,edits:r.edited.map(e=>({id:e.zone_id,finish:e.finish,color:e.color,proof:!!e._spbScopedPartProof}))});}else{pass=!r.parseFailure&&r.queued.errs.length>0&&r.edited.length===0&&r.added.length===0;detail=JSON.stringify({parseFailure:!!r.parseFailure,errors:r.queued.errs,adds:r.added.length,edits:r.edited.length});}results.push({id:c.id,pass,detail});}
console.log(JSON.stringify({mode,sourceHashes:{controller:hash(Buffer.from(csrc)),design:hash(Buffer.from(dsrc)),edit:hash(Buffer.from(esrc)),oracle:hash(bytes)},counts:{cases:results.length,passed:results.filter(x=>x.pass).length,failed:results.filter(x=>!x.pass).length},results,effects:{applyCalls:0,providerCalls:0,nativeCalls:0}},null,2));
const supplements=[
 {id:'generic-whole-owner-layer-alias',selector:{island:'roof',layers:['Car Paint']},allow:true},
 {id:'paintable-true-body-constraint',selector:{island:'roof',paintable:true},allow:true},
 {id:'paintable-false-constraint',selector:{island:'roof',paintable:false},allow:false},
 {id:'explicit-other-layer',selector:{island:'roof',layers:['Number Paint']},allow:false},
 {id:'partial-portion',selector:{island:'roof',layers:['Car Paint'],portion:'front half'},allow:false},
 {id:'excluded-part',selector:{island:'roof',layers:['Car Paint'],exclude:['spoiler']},allow:false},
 {id:'color-limited-part',selector:{island:'roof',layers:['Car Paint'],colors:['#1f8a3b']},allow:false},
 {id:'band-limited-part',selector:{island:'roof',layers:['Car Paint'],band:{from:0.2,to:0.4}},allow:false}
];
const supplementalResults=[];
for(const s of supplements){const r=run({id:'roof-chrome-keep-paint',text:'Make only the roof chrome, keep its current paint.',selector:s.selector});const ok=r.queued.errs.length===0&&r.edited.length===1&&r.added.length===0;const pass=s.allow?ok:(!ok&&r.edited.length===0&&r.added.length===0);supplementalResults.push({id:s.id,pass,actual:{errors:r.queued.errs,adds:r.added.length,edits:r.edited.map(e=>({id:e.zone_id,region:e.region,proof:!!e._spbScopedPartProof}))}});}
const parserGeneric=run({id:'roof-chrome-keep-paint',text:'Make only the roof chrome, keep its current paint.'}); const parsedLayerCases=['Make the roof chrome on the Number Paint layer, keeping its current paint.','Make only the front half of the roof chrome, keep its current paint.'];
const parserRows=parsedLayerCases.map(text=>{const r=run({id:'roof-chrome-keep-paint',text});return {text,parsed:!r.parseFailure,kind:r.planned&&r.planned.kind,zoneCount:r.compiled&&r.compiled.zones&&r.compiled.zones.length,plannedRegion:r.compiled&&r.compiled.zones&&r.compiled.zones[0]&&r.compiled.zones[0].region,unknown:r.planned&&r.planned.unknown,errors:r.queued.errs,adds:r.added.length,edits:r.edited.length};});
console.log(JSON.stringify({actualCurrentE:{path:ePath,sha256:hash(Buffer.from(esrc)),genericWholePartRegion:parserGeneric.compiled&&parserGeneric.compiled.zones&&parserGeneric.compiled.zones[0]&&parserGeneric.compiled.zones[0].region},w103Supplemental:{counts:{cases:supplementalResults.length,passed:supplementalResults.filter(x=>x.pass).length,failed:supplementalResults.filter(x=>!x.pass).length},results:supplementalResults,actualParser:parserRows}},null,2));
if(supplementalResults.some(x=>!x.pass))process.exitCode=1;






