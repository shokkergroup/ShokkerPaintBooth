// SPB-93: only real rendered-material records enter the engine, never old paint snapshots.
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBZoneMaterialInstancePayload=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const fields=['version','id','sourceTarget','sourceBbox','renderSourceBbox','instanceBbox','documentWidth','documentHeight','rotation','muted','detached','frozenMaterial','masterId','isSource'];
 function apply(payload,zone) {
  const records=(Array.isArray(zone?.patternInstances)?zone.patternInstances:[]).filter(r=>r&&r.version===2&&(!r.muted||r.isSource));
  if(!records.length)return;
  payload.material_instances=records.map(r=>JSON.parse(JSON.stringify(Object.fromEntries(fields.filter(k=>r[k]!==undefined).map(k=>[k,r[k]])))));
 }
 return Object.freeze({apply});
});
