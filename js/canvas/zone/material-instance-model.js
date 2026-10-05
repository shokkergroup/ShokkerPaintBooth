// SPB-93: Zone material links describe rendered content, not Layer paint rasters.
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBZoneMaterialInstanceModel=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const copy=x=>JSON.parse(JSON.stringify(x));
 const overlap=(a,b)=>a.x1<b.x2&&a.x2>b.x1&&a.y1<b.y2&&a.y2>b.y1;
 function create(zone,rect,width,height,target,id) {
  if(!zone||!rect||![width,height,rect.x1,rect.y1,rect.x2,rect.y2].every(Number.isFinite))return null;
  const source={x1:Math.floor(rect.x1),y1:Math.floor(rect.y1),x2:Math.ceil(rect.x2),y2:Math.ceil(rect.y2)};
  const w=source.x2-source.x1,h=source.y2-source.y1,gap=16;
  if(w<=0||h<=0||source.x1<0||source.y1<0||source.x2>width||source.y2>height)return null;
  const records=Array.isArray(zone.patternInstances)?zone.patternInstances:[];
  const occupied=[source,...records.filter(r=>r?.version===2).flatMap(r=>[r.instanceBbox,r.sourceBbox]).filter(Boolean)];
  const candidates=[[source.x2+gap,source.y1],[source.x1,source.y2+gap],[source.x1-w-gap,source.y1],[source.x1,source.y1-h-gap]];
  for(let y=0;y+h<=height;y+=h+gap)for(let x=0;x+w<=width;x+=w+gap)candidates.push([x,y]);
  for(const [x,y] of candidates) {
   const dest={x1:x,y1:y,x2:x+w,y2:y+h};
   if(x<0||y<0||dest.x2>width||dest.y2>height||occupied.some(r=>overlap(dest,r)))continue;
   return {version:2,id:String(id),sourceTarget:target,sourceBbox:source,renderSourceBbox:copy(source),instanceBbox:dest,
    documentWidth:width,documentHeight:height,rotation:0};
  }
  return null;
 }
 function duplicate(zone,record,id) {
  if(!record||record.version!==2||record.detached)return null;
  const placed=create(zone,record.instanceBbox,record.documentWidth,record.documentHeight,record.sourceTarget,id);
  if(!placed)return null;
  const result={...copy(record),id:String(id),instanceBbox:placed.instanceBbox};
  delete result.isSource;
  return result;
 }
 return Object.freeze({create,duplicate});
});
