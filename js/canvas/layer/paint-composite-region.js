/* SPB-93: exact cropped composites for a simple stack. Complex semantics keep
   the authoritative full path. Baselines belong to one stroke only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBPaintCompositeRegion=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 function eligible(layers) {
  return Array.isArray(layers)&&layers.every(l=>l&&!l.isGroup&&!l.clippingMask&&!(l.groupChain?.length)
   &&(!l.blendMode||l.blendMode==='source-over')&&!Number(l.adjHue)&&!Number(l.adjSat)&&!Number(l.adjBri)
   &&!Object.values(l.effects||{}).some(fx=>fx?.enabled)
   &&(!l.bbox||l.bbox.every(Number.isInteger)));
 }
 const key=l=>JSON.stringify([l.id,l.visible,l.opacity,l.blendMode,l.clippingMask,l.groupChain,l.effects,l.adjHue,l.adjSat,l.adjBri]);
 function capture(layers,id,pixels,revision) {
  if(!eligible(layers)||!pixels?.data||!layers.some(l=>l.id===id))return null;
  return {id,pixels,revision,layers:layers.map(l=>({ref:l,img:l.img,bbox:JSON.stringify(l.bbox),key:key(l)}))};
 }
 function valid(base,layers,width,height,revision) {
  return !!base&&base.revision===revision&&base.pixels.width===width&&base.pixels.height===height
   &&base.pixels.data.length===width*height*4&&eligible(layers)&&layers.length===base.layers.length
   &&layers.every((l,i)=>{const old=base.layers[i];return l===old.ref&&key(l)===old.key
    &&(l.id===base.id||(l.img===old.img&&JSON.stringify(l.bbox)===old.bbox));});
 }
 function bounds(rect,width,height) {
  if(!rect||![rect.x,rect.y,rect.width,rect.height].every(Number.isFinite)||rect.width<=0||rect.height<=0)return null;
  const x=Math.max(0,Math.floor(rect.x)),y=Math.max(0,Math.floor(rect.y));
  const right=Math.min(width,Math.ceil(rect.x+rect.width)),bottom=Math.min(height,Math.ceil(rect.y+rect.height));
  return right>x&&bottom>y ? {x,y,width:right-x,height:bottom-y}:null;
 }
 function afterHistory(base,layers,width,height,before,after) {
  return after===before+1 && valid(base,layers,width,height,before) ? {...base,revision:after} : null;
 }
 function patch(width,height,rect,compose,createCanvas) {
  const region=bounds(rect,width,height);if(!region)return null;
  const canvas=createCanvas();canvas.width=region.width;canvas.height=region.height;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.translate(-region.x,-region.y);
  const result=compose(ctx);if(!result.ok)return {result};
  return {result,region,pixels:ctx.getImageData(0,0,region.width,region.height)};
 }
 function publish(base,width,height,rect,compose,createCanvas) {
  const part=patch(width,height,rect,compose,createCanvas);if(!part||!part.result.ok)return part;
  const canvas=createCanvas();canvas.width=width;canvas.height=height;
  const ctx=canvas.getContext('2d',{willReadFrequently:true}),pixels=ctx.createImageData(width,height);
  pixels.data.set(base.pixels.data);
  const r=part.region;
  for(let row=0;row<r.height;row++)pixels.data.set(part.pixels.data.subarray(row*r.width*4,(row+1)*r.width*4),((row+r.y)*width+r.x)*4);
  ctx.putImageData(pixels,0,0);
  return {result:part.result,canvas,pixels};
 }
 return Object.freeze({eligible,capture,valid,afterHistory,bounds,patch,publish});
});
