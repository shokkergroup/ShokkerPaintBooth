// SPB-93: a Zone instance owns its frame; the source material/other copies do not move.
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBZoneMaterialInstanceTransform=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const prefix='zone_instance:';
 const isTarget=target=>typeof target==='string'&&target.startsWith(prefix);
 const targetFor=record=>prefix+record.id;
 const resolve=(zone,target)=>isTarget(target)?(zone?.patternInstances||[]).find(r=>r?.version===2&&String(r.id)===target.slice(prefix.length)):null;
 function frame(record,width,height) {
  const r=record?.instanceBbox;if(!r||!record.documentWidth||!record.documentHeight)return null;
  const x=width/record.documentWidth,y=height/record.documentHeight;
  const source=record.renderSourceBbox||record.sourceBbox;
  return {offsetX:(r.x1+r.x2)/(2*record.documentWidth),offsetY:(r.y1+r.y2)/(2*record.documentHeight),
   boxW:(r.x2-r.x1)*x,boxH:(r.y2-r.y1)*y,scale:(r.x2-r.x1)/Math.max(1,source.x2-source.x1),rotation:record.rotation||0};
 }
 function hit(zone,point,width,height) {
  for(const record of [...(zone?.patternInstances||[])].reverse()) {
   if(record?.version!==2||record.muted)continue;
   const f=frame(record,width,height);if(!f)continue;
   const angle=-f.rotation*Math.PI/180,dx=point.x-f.offsetX*width,dy=point.y-f.offsetY*height;
   const x=dx*Math.cos(angle)-dy*Math.sin(angle),y=dx*Math.sin(angle)+dy*Math.cos(angle);
   if(Math.abs(x)<=f.boxW/2&&Math.abs(y)<=f.boxH/2)return targetFor(record);
  }
  return null;
 }
 function prepare(record,state,width,height) {
  if(!record||![state.centerX,state.centerY,state.boxW,state.boxH,state.rotation,width,height].every(Number.isFinite)
   ||state.boxW<=0||state.boxH<=0||width<=0||height<=0)return null;
  const x=record.documentWidth/width,y=record.documentHeight/height;
  return {...record,instanceBbox:{x1:(state.centerX-state.boxW/2)*x,y1:(state.centerY-state.boxH/2)*y,
   x2:(state.centerX+state.boxW/2)*x,y2:(state.centerY+state.boxH/2)*y},rotation:((state.rotation%360)+360)%360};
 }
 function changed(a,b) {
  return !!b&&(Math.abs((a.rotation||0)-b.rotation)>1e-7||['x1','y1','x2','y2'].some(k=>Math.abs(a.instanceBbox[k]-b.instanceBbox[k])>1e-7));
 }
 function finish(zone,state,commit,width,height,pushUndo) {
  const record=resolve(zone,state.target),next=record&&prepare(record,state,width,height);
  if(!commit||!record||!changed(record,next))return false;
  pushUndo('Transform Zone material instance');
  Object.assign(record,{instanceBbox:next.instanceBbox,rotation:next.rotation});return true;
 }
 function draw(ctx,state,zone,width,height,img) {
  const record=resolve(zone,state.target);
  const material=record?.frozenMaterial||zone?.patternInstances?.find(r=>r.id===record?.masterId&&!r.detached)?.frozenMaterial;
  if(material) {
   const canvas=globalThis.SPBZoneMaterialInstanceCommands?.preview({frozenMaterial:material},()=>globalThis.drawTransformHandles?.());
   if(!canvas)return false;
   ctx.save();
   try {ctx.translate(state.centerX,state.centerY);ctx.rotate(state.rotation*Math.PI/180);ctx.globalAlpha=.8;
    ctx.drawImage(canvas,0,0,canvas.width,canvas.height,-state.boxW/2,-state.boxH/2,state.boxW,state.boxH);
   } finally {ctx.restore();}
   return true;
  }
  if(!record||!img?.naturalWidth||!img.naturalHeight)return false;
  const r=record.renderSourceBbox||record.sourceBbox,x=img.naturalWidth/record.documentWidth,y=img.naturalHeight/record.documentHeight;
  ctx.save();
  try {
   ctx.translate(state.centerX,state.centerY);ctx.rotate(state.rotation*Math.PI/180);
   ctx.globalAlpha=.8;
   ctx.drawImage(img,r.x1*x,r.y1*y,(r.x2-r.x1)*x,(r.y2-r.y1)*y,-state.boxW/2,-state.boxH/2,state.boxW,state.boxH);
  } finally {ctx.restore();}
  return true;
 }
 return Object.freeze({isTarget,targetFor,resolve,frame,hit,prepare,changed,finish,draw});
});
