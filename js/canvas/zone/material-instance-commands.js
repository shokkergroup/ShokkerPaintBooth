// SPB-93: unlink keeps native material content and the independent frame.
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBZoneMaterialInstanceCommands=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const pending=new WeakSet(), previews=new WeakMap();
 async function detach(zone,record,options) {
  const records=(Array.isArray(record)?record:[record]).filter(r=>r?.version===2&&!r.detached);
  if(!zone||!records.length||records.some(r=>pending.has(r)))return false;
  records.forEach(r=>pending.add(r));
  const before=records.map(r=>JSON.stringify(r));
  try {
   const materials=[];
   for(const r of records) {
    const material=await options.capture(r.id);
    if(!material||material.format!=='spb-zone-material/1')throw Error('Material preview changed or is not ready. Try Break Link again.');
    materials.push(material);
   }
   if(records.some((r,i)=>!zone.patternInstances?.includes(r)||JSON.stringify(r)!==before[i])||!options.isCurrent())throw Error('The selected copy changed. Try Break Link again.');
   options.pushUndo('Break Zone material instance link');
   records.forEach((r,i)=>{
    const peers=zone.patternInstances.filter(p=>p.version===2&&!p.detached&&!records.includes(p)&&p.masterId===r.id);
    if(peers.length){
     const next=peers[0];next.frozenMaterial=materials[i];
     peers.forEach(p=>{p.masterId=next.id;});
    }
   });
   records.forEach((r,i)=>{r.frozenMaterial=materials[i];r.detached=true;});
   options.applyFrame?.();
   options.finish();return true;
  } finally {records.forEach(r=>pending.delete(r));}
 }
 function preview(record,refresh) {
  const value=record?.frozenMaterial;if(!value)return null;
  let cached=previews.get(value);
  if(cached)return cached.canvas;
  cached={canvas:null};previews.set(value,cached);
  (async()=>{
   const compressed=Uint8Array.from(atob(value.data), c=>c.charCodeAt(0));
   const bytes=new Uint8Array(await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer());
   const n=value.width*value.height;if(bytes.length!==n*15)throw Error('Invalid material preview');
   const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
   const canvas=document.createElement('canvas');canvas.width=value.width;canvas.height=value.height;
   const ctx=canvas.getContext('2d'),image=ctx.createImageData(value.width,value.height);
   for(let i=0;i<n;i++){
    image.data.set(bytes.subarray(n*3+i*4,n*3+i*4+3),i*4);
    image.data[i*4+3]=Math.round(view.getFloat32(n*7+i*4,true)*255);
   }
   ctx.putImageData(image,0,0);cached.canvas=canvas;refresh?.();
  })().catch(error=>console.warn('[Zone material preview]',error));
  return null;
 }
 return Object.freeze({detach,preview});
});
