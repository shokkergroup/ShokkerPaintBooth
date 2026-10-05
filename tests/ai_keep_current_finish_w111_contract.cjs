'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'), oraclePath='_easy_claude_work/ai14h_w111_review/fresh-oracle.json';
const oracleBytes=fs.readFileSync(path.join(root,oraclePath)),oracle=JSON.parse(oracleBytes),hash=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(hash(oracleBytes),'10D0007038371B9630A0DC641F2B59DB5C77521A0B06B7A9E82B90C427CF0545');assert.equal(oracle.cases.length,12);
const controllerPath='_easy_claude_work/ai14h_w111_candidate/spb-pro-ai.js',designPath='_easy_claude_work/ai14h_generation3_candidate/integration16/js/spb-pro-design.js',editPath='_easy_claude_work/ai14h_generation3_candidate/integration16/js/spb-pro-edit.js';
const src=fs.readFileSync(path.join(root,controllerPath),'utf8'),ds=fs.readFileSync(path.join(root,designPath),'utf8'),es=fs.readFileSync(path.join(root,editPath),'utf8');
assert.equal(hash(Buffer.from(src)),'C479E300EF64EF0EF710CCFE7036795F41682CA73911E6E0BC5352A53923DF35');assert.equal(hash(Buffer.from(ds)),'4648DE3231015497CC9FF816612A542097A1AD14038A7210753F6CDBFD88D832');assert.equal(hash(Buffer.from(es)),'7D063444021F8F4144B96130800BADFE62741CDEFC9104417F3E99AF65270767');
function extract(source,name){const start=source.indexOf('function '+name+'(');assert(start>=0,'missing '+name);const brace=source.indexOf('{',start);let depth=0,q=null,esc=false,line=false,block=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;else if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw Error('unterminated '+name);}
const H=require('../_easy_claude_work/stack_h.js');
const helperNames=['scopedPartSourceNow','scopedPartLayersNow','scopedPartSelectorLayerIds','scopedPartAppearance','scopedPartJson','partOwnerCurrent','scopedPartProofCurrent','scopedPartProofMatches','scopedPartProofAt','currentPartZoneOwners','bodyLayerNames','partRegionKey','editKey','hasPriorPartIdentity','semanticPartOf','currentWholePartOwner','requestedPartSelectorMatchesProof','queueEditZones','explicitCurrentPaintRequest','currentPartOwnerVerifiedForRegion','unprovedCurrentPaintPartAdd'];
function fnv(a){let h=2166136261>>>0;for(const x of a)h=Math.imul(h^(Number(x)&255),16777619)>>>0;return a.length+':'+h.toString(36);}
function run(c){
 const Hctx=H.load();vm.runInContext(ds,Hctx);vm.runInContext(es,Hctx);const E=Hctx.SpbProEdit;
 const mask=new Uint8Array([1,0,1,0]),source={generation:8,path:'C:/cars/owned.psd',fingerprint:'file-sha256:'+'a'.repeat(64),width:2048,height:2048};
 const part=c.id==='W111-03'?'hood':'roof',layer={id:'paint-layer-id',name:'Car Paint',visible:true,locked:false,opacity:100},other={id:'number-layer-id',name:'Number Paint',visible:true,locked:false,opacity:100};
 const selector={island:part,layers:['Car Paint']},key=JSON.stringify({x:[],c:[],l:['Car Paint'],p:part,e:false,el:'',pr:'{}'});
 const zone={id:'zone-'+part,name:'Owned '+part,region:selector,regionMask:new Uint8Array(mask),useRegion:true,muted:false,baseColorMode:'solid',baseColor:c.id==='W111-03'?'#143c82':'#168a45',base:'base::gloss',finish:'base::gloss',baseColorStrength:1,baseStrength:1,specShiftR:0,specShiftG:0,specShiftB:0};
 const prov={r:JSON.stringify(selector),z:fnv(mask),p:fnv(mask),l:'layout-current',e:'element-current',car:'car-current',s:source,layers:['paint-layer-id'],layerState:[{id:'paint-layer-id',visible:true,locked:false,opacity:100}]};zone._aiPartProv=prov;zone._aiPartSource=Object.assign({},source);
 const zones=[zone],reg={[key]:zone.name};
 const tx={isCommitted:()=>true,getGeneration:()=>8,getCommittedGeneration:()=>8,getCommittedPath:()=>source.path,getCommittedFingerprint:()=>source.fingerprint,getCommittedKind:()=> 'psd'};
 const ctx={console,Promise,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,ArrayBuffer,Date,window:null,document:{getElementById:()=>({width:2048,height:2048})},_psdLayers:[layer,other],_psdPath:source.path,zones,_editReg:reg,_editRegPendingBefore:{},_editRegSig:'car-current',_busy:false,CAR:{layoutSig:()=> 'layout-current',roles:()=>[{role:'body paint',name:'Car Paint',visible:true}],maskFor:()=>({mask:new Uint8Array(mask)}),missing:()=>[]},Z:{footprint:()=>({share_pct:4.2,visible_pct:4.2}),findLayer:n=>String(n)==='Car Paint'||String(n)==='paint-layer-id'?layer:(String(n)==='Number Paint'||String(n)==='number-layer-id'?other:null),validate:()=>({errors:[]}),catchAll:()=>null},SPBSourceLoadTransaction:tx,getCurrentSourcePaintFile:()=>source.path,SpbProElements:{sig:()=> 'element-current'},zoneSourceLayerIds:()=>['paint-layer-id'],carSig:()=> 'car-current',normaliseSpec:x=>x,protectDecals(){},editPlural:()=>false,friendlyZoneError:e=>String(e),window:null};
 ctx.window=ctx;vm.createContext(ctx);vm.runInContext(ds,ctx);vm.runInContext(es,ctx);
 if(c.id==='W111-04'){zone._aiPartProv=null;zone._aiPartSource=null;reg[key]=undefined;}
 if(c.id==='W111-05'){ctx.Z.footprint=()=>({share_pct:4.2,visible_pct:2.1});}
 if(c.id==='W111-06'){zone._aiPartProv.r=JSON.stringify({island:part,layers:['Number Paint']});zone.region={island:part,layers:['Number Paint']};}
 if(c.id==='W111-08'){zone.regionMask[0]=0;}
 if(c.id==='W111-09'){tx.getGeneration=()=>9;}
 if(c.id==='W111-10'){const dup=JSON.parse(JSON.stringify(zone));dup.id='duplicate-zone';dup.regionMask=new Uint8Array(mask);zones.push(dup);}
 if(c.id==='W111-11'){zone._spbAIPartMemoryPending={provenance:prov};zone._aiPartProv=null;zone._aiPartSource=null;}
 const srcFns=helperNames.map(n=>extract(src,n));srcFns.forEach(f=>vm.runInContext(f,ctx));
 const ownerStateBefore={id:zone.id,name:zone.name,baseColorMode:zone.baseColorMode,baseColor:zone.baseColor,baseColorStrength:zone.baseColorStrength,baseStrength:zone.baseStrength,finish:zone.finish,source:Object.assign({},zone._aiPartSource),provenance:JSON.parse(JSON.stringify(zone._aiPartProv)),mask:Array.from(zone.regionMask)};
 const text=c.text,env={palette:[{hex:'#168a45',name:'green',share_pct:4.2},{hex:'#143c82',name:'navy',share_pct:4.2}],layers:[layer,other],zoneColours:[]};
 const planned=E.plan(text,env);let compiled=planned&&planned.kind==='ops'?E.compile(planned,env):null;
 let blocked=null,queued={errs:[]},added=[],edited=[];
 if(compiled){blocked=ctx.unprovedCurrentPaintPartAdd({zones:compiled.zones},text);if(!blocked&&!(compiled.ask||compiled.missing&&compiled.missing.length))queued=ctx.queueEditZones({zones:compiled.zones},spec=>{added.push(JSON.parse(JSON.stringify(spec)));return{ok:true,index:0,name:spec.name||'New'};},spec=>{edited.push(JSON.parse(JSON.stringify(spec)));return{ok:true};});}
 const ownerStateAfter={id:zone.id,name:zone.name,baseColorMode:zone.baseColorMode,baseColor:zone.baseColor,baseColorStrength:zone.baseColorStrength,baseStrength:zone.baseStrength,finish:zone.finish,source:Object.assign({},zone._aiPartSource),provenance:JSON.parse(JSON.stringify(zone._aiPartProv)),mask:Array.from(zone.regionMask)};return {id:c.id,planned,compiled,blocked,queued,added,edited,zone,zones,ownerStateBefore,ownerStateAfter,proofOk:!!ctx.currentWholePartOwner(part)};
}
const output=[];
for(const c of oracle.cases){const r=run(c);let pass=false,why='';const positive=['W111-01','W111-02','W111-03'].includes(c.id);
 if(positive){pass=!!r.planned&&r.planned.kind==='ops'&&r.queued.errs.length===0&&r.edited.length===1&&r.added.length===0&&String(r.edited[0].zone_id)==='zone-'+(c.id==='W111-03'?'hood':'roof')&&!Object.prototype.hasOwnProperty.call(r.edited[0],'color')&&!!r.edited[0]._spbScopedPartProof&&JSON.stringify(r.ownerStateBefore)===JSON.stringify(r.ownerStateAfter)&&r.edited[0]._spbScopedPartProof.source.path==='C:/cars/owned.psd'&&r.edited[0]._spbScopedPartProof.source.generation===8;why=JSON.stringify({plan:r.planned&&r.planned.kind,block:r.blocked,errors:r.queued.errs,edits:r.edited.map(x=>({id:x.zone_id,finish:x.finish,color:x.color,proof:!!x._spbScopedPartProof})),adds:r.added.length});}
 else {pass=(!r.planned||r.planned.kind!=='ops'||!!r.blocked||r.queued.errs.length>0)&&r.edited.length===0&&r.added.length===0;why=JSON.stringify({plan:r.planned&&r.planned.kind,block:r.blocked,errors:r.queued.errs,edits:r.edited.length,adds:r.added.length,proof:r.proofOk});}
 output.push({id:c.id,pass,detail:why});}
console.log(JSON.stringify({oracleSha256:hash(oracleBytes),candidateSha256:hash(Buffer.from(src)),designSha256:hash(Buffer.from(ds)),editSha256:hash(Buffer.from(es)),counts:{cases:output.length,passed:output.filter(x=>x.pass).length,failed:output.filter(x=>!x.pass).length},results:output,effects:{applyCalls:0,providerCalls:0,nativeCalls:0}},null,2));if(output.some(x=>!x.pass))process.exitCode=1;


