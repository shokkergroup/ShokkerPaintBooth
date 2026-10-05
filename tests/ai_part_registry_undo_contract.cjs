'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const ai = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const zone = fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8');
function extract(src, name) { const start=src.indexOf(`function ${name}(`); assert(start>=0,name); const open=src.indexOf('{',start); let d=0,q=null,e=false,l=false,b=false; for(let i=open;i<src.length;i++){const c=src[i],n=src[i+1]; if(l){if(c==='\n')l=false;continue;} if(b){if(c==='*'&&n==='/'){b=false;i++;}continue;} if(q){if(e)e=false;else if(c==='\\')e=true;else if(c===q)q=null;continue;} if(c==='/'&&n==='/'){l=true;i++;continue;} if(c==='/'&&n==='*'){b=true;i++;continue;} if(c==='"'||c==="'"||c==='`'){q=c;continue;} if(c==='{')d++;else if(c==='}'&&--d===0)return src.slice(start,i+1);} throw Error(name); }
function cloneZone(z) { const c=Object.assign({},z); ['regionMask','spatialMask','patternStrengthMap'].forEach(k=>{if(z[k]&&typeof z[k].length==='number')c[k]=new Uint8Array(z[k]);}); return c; }
function harness() {
  const zones=[], undo=[], state={car:'car-a',layout:'layout-a',elements:'elements-a'}, ctx={console,Uint8Array,Float32Array,Date,Math,JSON,isFinite,parseInt,zones,selectedZoneIndex:0,
    BASES:[{id:'gloss'},{id:'chrome'},{id:'matte'}],MONOLITHICS:[],PATTERNS:[],SPEC_PATTERNS:[],_psdLayers:[{id:'body',name:'Body Paint',img:{}}],
    document:{getElementById:()=>({width:32,height:32})},addZone(){zones.push({id:`z${zones.length+1}`,name:'New zone',colorMode:'none',color:'source',colors:[]});},
    assignFinishToSelected(id){const z=zones[ctx.selectedZoneIndex];if(z)z.base=id;},setZoneSourceLayer(i,id){zones[i].sourceLayerIds=id?[id]:[];},toggleZoneSourceLayer(i,id,on){const z=zones[i],a=z.sourceLayerIds||(z.sourceLayerIds=[]),n=a.indexOf(id);if(on&&n<0)a.push(id);if(!on&&n>=0)a.splice(n,1);},
    pushZoneUndo(){undo.push(zones.map(cloneZone));},undoZoneChange(){const prior=undo.pop();if(prior){zones.splice(0,zones.length,...prior.map(cloneZone));}},renderZones(){},triggerPreviewRender(){},render(){},
    SpbProCar:{findIsland:n=>({id:String(n),name:String(n),front:true,up:true}),parts:()=>['roof'],canon:n=>String(n),signature:()=>state.car,layoutSig:()=>state.layout,missing:()=>[],roles:()=>[{id:'body',name:'Body Paint',role:'body paint',visible:true}],maskFor(n){const m=new Uint8Array(1024);for(let i=0;i<512;i++)m[i]=255;return{mask:m,island:{name:String(n)},islands:[{name:String(n)}]};}},
    SpbProElements:{sig:()=>state.elements},CAR:null,_busy:false,_progress:'',_absent:{},_skipParts:true,_gen:0,_snapGen:0,_activeId:null,RECENT:[],_advUsed:null,_advRejected:[],_log:[],_layerUndoStack:[],
    carSig(){return state.car;},editPlural:()=>false,friendlyZoneError:String,warm:()=>Promise.resolve(),D:null,applyLayerOps:()=>({lines:[],failed:[],undoSteps:0}),
    zonesRef:zones};
  ctx.CAR=ctx.SpbProCar;ctx._psdLayers=ctx._psdLayers;ctx.window=ctx;vm.createContext(ctx);vm.runInContext(zone,ctx,{filename:'real-zone-kit'});
  ctx.Z=ctx.SpbProZone;
  const names=['normaliseSpec','bodyLayerNames','wantsDecalsToo','protectDecals','partRegionKey','editKey','markPartFollowupQueue','partOwnerCurrent','registerAppliedPartZones','partRegHas','partRegistryState','rollbackPendingPartRegistry','clearPartRegistryPending','reconcilePartRegistry','mergePartRegistryUndo','restorePartRegistryUndo','applyQueue','queueEditZones','offlineElementAsk','doUndo'];
  vm.runInContext(`${names.map(n=>extract(ai,n)).join('\n')}\nvar _editReg={},_editRegSig=null,_editRegPendingBefore={},_reqText='',_specOnlyReq=false;this.api={mark:markPartFollowupQueue,apply:applyQueue,queue:queueEditZones,undo:doUndo,registry:()=>_editReg,pending:()=>_editRegPendingBefore,editQ:function(args){var i=zones.findIndex(function(z){return z.id===args.zone_id;}),s=Object.assign({},args),q={kind:'edit',zone:i,spec:s};delete q.spec.zone_id;delete q.spec._spbPartRegKey;delete q.spec._spbPartOwnerName;delete q.spec._spbPartForgetKey;if(args._spbPartRegKey){q._spbPartRegKey=args._spbPartRegKey;q._spbPartOwnerName=args._spbPartOwnerName;}if(args._spbPartForgetKey)q._spbPartForgetKey=args._spbPartForgetKey;return q;}};`,ctx,{filename:'real-ai-part-undo'});
  ctx.D={offlineElement:()=>({zones:[{name:'Red roof',region:{part:'roof'},color:'#c8102e',finish:'base::gloss'}],parts:['roof'],label:'roof',colour:'red',skipped:[]})};
  ctx.makeTools=queue=>[{name:'add_zone',handler(spec){const s=ctx.normaliseSpec(JSON.parse(JSON.stringify(spec)));ctx.protectDecals(s);queue.push({kind:'add',spec:s});return{ok:true};}}];
  ctx.add=spec=>ctx.SpbProZone.add(spec);
  return {ctx,zones,undo,state};
}
async function main(){
 const {ctx,zones,undo}=harness();
 const route=await ctx.offlineElementAsk('Make the roof bright red',{});
 assert.ok(route.queue[0]._spbPartFollowupOwner,'the actual offlineElementAsk route opts its real part addition into committed ownership');
 assert.deepEqual(route.queue[0].spec.region.layers,['Body Paint'],'the real decal guard restricts it to the body-paint layer');
 const initial=ctx.api.apply(route.queue,'red roof helper route');
 assert.equal(zones.length,1,JSON.stringify({initial,queue:route.queue})); assert.ok(zones[0]._aiPartProv); assert.deepEqual(Array.from(zones[0].regionMask).filter(Boolean).length>0,true);
 assert.equal(ctx.api.registry()[ctx.editKey({part:'roof',layers:['Body Paint']})],'Red roof');
 const beforeColor=zones[0].baseColor;
 const editOps=[];
 const finishOnly={zones:[{name:'Roof chrome',region:{part:'roof'},color:'source',finish:'base::chrome',_meta:{label:'roof',kind:'finish',finishExplicit:true}}]};
 const key=ctx.editKey({part:'roof',layers:['Body Paint']}), abandoned=[];
 ctx.api.queue(finishOnly,ctx.add,args=>{abandoned.push(ctx.api.editQ(args));return{ok:true};});
 assert.equal(ctx.api.registry()[key],'Red roof','an un-applied plan cannot project its proposed name into committed ownership');
 assert.equal(Object.keys(ctx.api.pending()).length,0,'part plans have no global pending projection');
 const repeated=[];const repeatedPlan=ctx.api.queue(finishOnly,ctx.add,args=>{repeated.push(ctx.api.editQ(args));return{ok:true};});
 assert.equal(repeatedPlan.merged,1,'repeating an abandoned plan still resolves the committed helper owner');
 assert.equal(repeated.length,1);assert.equal(repeated[0]._spbPartOwnerName,'Red roof');
 const finishQueue=ctx.api.queue(finishOnly,ctx.add,args=>{editOps.push(ctx.api.editQ(args));return{ok:true};});
 assert.equal(finishQueue.merged,1); const entry={undoable:true,undone:false,maskUndo:[],zoneUndo:true};
 const committed=ctx.api.apply(editOps,'finish-only follow-up');entry._partRegUndo=committed.partRegUndo;
 assert.equal(zones.length,1);assert.equal(zones[0].baseColor,beforeColor,'finish-only application leaves the red paint intact');
 assert.equal(ctx.api.registry()[ctx.editKey({part:'roof',layers:['Body Paint']})],'Roof chrome');
 assert.ok(undo.length>=2,'real ZoneKit batches pushed undo snapshots');
 ctx.api.undo(entry);
 assert.equal(zones.length,1);assert.notEqual(zones[0],entry.zone,'undo restored cloned zone state');
 assert.equal(zones[0].name,'Red roof');
 assert.equal(ctx.api.registry()[ctx.editKey({part:'roof',layers:['Body Paint']})],'Red roof','undo restored the committed helper owner name');
 const retryOps=[];const retry=ctx.api.queue(finishOnly,ctx.add,args=>{retryOps.push(ctx.api.editQ(args));return{ok:true};});
 assert.equal(retry.merged,1,'retry after undo reuses the restored owner');assert.equal(retryOps.length,1);assert.equal(retryOps[0].kind,'edit');
 const staleRun=harness(),staleRoute=await staleRun.ctx.offlineElementAsk('Make the roof bright red',{});staleRun.ctx.api.apply(staleRoute.queue,'red roof');
 const staleOld=[];staleRun.ctx.api.queue(finishOnly,staleRun.ctx.add,args=>{staleOld.push(staleRun.ctx.api.editQ(args));return{ok:true};});
 const laterPlan={zones:[{name:'Roof matte',region:{part:'roof'},color:'source',finish:'base::matte',_meta:{label:'roof',kind:'finish',finishExplicit:true}}]},later=[];
 staleRun.ctx.api.queue(laterPlan,staleRun.ctx.add,args=>{later.push(staleRun.ctx.api.editQ(args));return{ok:true};});
 const laterApply=staleRun.ctx.api.apply(later,'later queued commit');assert.ok(laterApply.results[0].ok);
 const staleApply=staleRun.ctx.api.apply(staleOld,'old abandoned plan');
 assert.ok(staleApply.failed.some(s=>/changed after this plan/.test(s)),'an abandoned older plan is refused after ownership changes');
 assert.equal(staleRun.zones[0].name,'Roof matte');assert.equal(staleRun.ctx.api.registry()[key],'Roof matte');
 const colorRun=harness(), colorRoute=await colorRun.ctx.offlineElementAsk('Make the roof bright red',{}); colorRun.ctx.api.apply(colorRoute.queue,'red roof');
 const oldFinish=colorRun.zones[0].base, colorOps=[];
 const colorOnly={zones:[{name:'Roof blue',region:{part:'roof'},color:'#2244cc',finish:'base::matte',_meta:{label:'roof',kind:'colour',finishExplicit:false}}]};
 const colorResult=colorRun.ctx.api.queue(colorOnly,colorRun.ctx.add,args=>{colorOps.push(colorRun.ctx.api.editQ(args));return{ok:true};});
 assert.equal(colorResult.merged,1,'plain colour-only route reuses the helper-owned part');
 colorRun.ctx.api.apply(colorOps,'colour-only follow-up');
 assert.equal(colorRun.zones.length,1);assert.equal(colorRun.zones[0].baseColor,'#2244cc');assert.equal(colorRun.zones[0].base,oldFinish,'color-only follow-up omits the fallback finish and retains existing material');
 const failedRun=harness(), failedRoute=await failedRun.ctx.offlineElementAsk('Make the roof bright red',{});failedRun.ctx.api.apply(failedRoute.queue,'red roof');
 const badOps=[], badEdit={zones:[{name:'Roof unavailable',region:{part:'roof'},color:'source',finish:'base::missing-finish',_meta:{label:'roof',kind:'finish',finishExplicit:true}}]};
 failedRun.ctx.api.queue(badEdit,failedRun.ctx.add,args=>{badOps.push(failedRun.ctx.api.editQ(args));return{ok:true};});
 const failedApply=failedRun.ctx.api.apply(badOps,'failed edit');
 assert.ok(failedApply.failed.length,'ZoneKit rejects an invalid material');
 assert.equal(failedRun.ctx.api.registry()[failedRun.ctx.editKey({part:'roof',layers:['Body Paint']})],'Red roof','failed commit discards the compiled rename and keeps the previously committed owner');
 console.log('PASS actual offline route, body guard, commit-only registry, abandoned/stale plan guards, ZoneKit apply/undo clone/retry, color-only finish preservation and failed-commit registry rollback');
}
main().catch(e=>{console.error(e);process.exitCode=1;});




