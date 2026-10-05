// SPB-93: material master roles change content authority, never member frames.
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBZoneMaterialInstanceMasters=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const same=(a,b)=>!!a&&!!b&&['x1','y1','x2','y2'].every(k=>a[k]===b[k]);
 const copy=value=>JSON.parse(JSON.stringify(value));
 const pending=new WeakSet();
 function group(zone,state) {
  const records=(zone?.patternInstances||[]).filter(r=>r?.version===2&&!r.detached);
  const selected=state?.target?.startsWith('zone_instance:')?records.find(r=>String(r.id)===state.target.slice(14)):null;
  const rect=selected?.sourceBbox||state?.subRect;
  if(!rect)return null;
  const members=records.filter(r=>same(r.sourceBbox,rect));
  if(!members.length)return null;
  const masterId=members.find(r=>r.masterId)?.masterId||null;
  return {members,selected,master:masterId?members.find(r=>r.id===masterId):null,rect};
 }
 function sync(zone,state,options) {
  const g=group(zone,state);if(!g)return false;
  const targets=g.members.filter(r=>r!==g.master&&r.frozenMaterial);
  if(!targets.length){options.refresh();options.notify('These copies already follow the current master.');return true;}
  options.pushUndo(options.label||'Sync Zone material instances');
  targets.forEach(r=>delete r.frozenMaterial);
  options.applyFrame?.();
  options.finish();options.notify('Copies now follow the current master; their positions are preserved.');return true;
 }
 async function promote(zone,state,options) {
  const g=group(zone,state);if(!g)return false;
  const record=g.selected;
  if(!record||record===g.master){options.notify('This piece is already the master.');return true;}
  if(pending.has(zone))return true;
  pending.add(zone);
  const before=JSON.stringify(zone.patternInstances);
  try {
   const material=await options.capture(record.id);
   if(!material||material.format!=='spb-zone-material/1')throw Error('Material changed or is not ready. Try Promote again.');
   if(JSON.stringify(zone.patternInstances)!==before||!options.isCurrent())throw Error('The selected group changed. Try Promote again.');
   const members=g.members.slice();
   let source=members.find(r=>r.isSource);
   if(!source){
    source={version:2,id:options.newId(),sourceTarget:record.sourceTarget,sourceBbox:copy(record.sourceBbox),
     renderSourceBbox:copy(record.renderSourceBbox||record.sourceBbox),instanceBbox:copy(record.sourceBbox),
     documentWidth:record.documentWidth,documentHeight:record.documentHeight,rotation:0,isSource:true};
    members.push(source);
   }
   options.pushUndo('Promote Zone material master');
   if(!zone.patternInstances.includes(source))zone.patternInstances.push(source);
   members.forEach(r=>{r.masterId=record.id;if(r!==record)delete r.frozenMaterial;});
   record.frozenMaterial=material;
   options.applyFrame?.();options.finish();options.notify('This copy is now the master. All linked pieces keep their positions.');
   return true;
  } finally {pending.delete(zone);}
 }
 async function appearance(zone,state,mode,options) {
  const names={tint:'Apply master color tint',hue:'Hue match from master',saturation:'Saturation-only match',vibrance:'Vibrance from master'};
  const g=group(zone,state);if(!g||!names[mode])return false;
  const targets=g.members.filter(r=>r!==g.master&&!r.muted);
  if(!targets.length){options.notify('There are no visible linked copies to update.');return true;}
  if(pending.has(zone))return true;
  pending.add(zone);
  const before=JSON.stringify(zone.patternInstances);
  try {
   // One native/preview capture pair for the whole group, not one render per copy.
   const materials=await options.capture(targets.map(r=>r.id),mode);
   if(!materials||targets.some(r=>materials[r.id]?.format!=='spb-zone-material/1'||materials[r.id]?.operation?.mode!==mode))
    throw Error('Material changed or is not ready. Try the color action again.');
   if(JSON.stringify(zone.patternInstances)!==before||!options.isCurrent())throw Error('The selected group changed. Try the color action again.');
   const changes=targets.filter(r=>materials[r.id].operation.changedPixels||materials[r.id].operation.previewChangedPixels);
   if(!changes.length){
    const noPaint=targets.every(r=>!materials[r.id].operation.ownedPaintPixels||!materials[r.id].operation.masterPaintPixels);
    options.notify(noPaint?'This material is spec-only. Choose a material with paint color to use color matching.':'The copies already match this color setting.');
    return true;
   }
   options.pushUndo('Zone '+names[mode]);
   changes.forEach(r=>{const {operation,...content}=materials[r.id];r.frozenMaterial=content;});
   options.applyFrame?.();options.finish();options.notify(names[mode]+' applied; spec and placement are preserved.');return true;
  } finally {pending.delete(zone);}
 }
 return Object.freeze({same,group,sync,promote,appearance});
});
