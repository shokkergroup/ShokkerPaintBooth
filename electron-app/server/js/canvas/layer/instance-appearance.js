/* SPB-93: current-master appearance operations on one immutable Layer source.
   Preparation is synchronous and read-only; caller owns one history publication. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBInstanceAppearance=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 // Module-local conversions: global rgbToHsl is later replaced by an object-returning helper.
function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;
    if (max === min) { h = s = 0; }
    else {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }
    return [h * 360, s, l];
}
function hslToRgb(h, s, l) {
    h /= 360;
    let r, g, b;
    if (s === 0) { r = g = b = l; }
    else {
        const hue2rgb = (p, q, t) => {
            if (t < 0) t += 1; if (t > 1) t -= 1;
            if (t < 1/6) return p + (q - p) * 6 * t;
            if (t < 1/2) return q;
            if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
            return p;
        };
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        r = hue2rgb(p, q, h + 1/3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1/3);
    }
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}
 function statistics(data,width,height,rect,ox,oy,toHsl) {
  let sin=0,cos=0,saturation=0,weight=0,hueWeight=0;
  for(let y=Math.max(0,Math.floor(rect.y1-oy));y<Math.min(height,Math.ceil(rect.y2-oy));y++)
   for(let x=Math.max(0,Math.floor(rect.x1-ox));x<Math.min(width,Math.ceil(rect.x2-ox));x++) {
    const i=(y*width+x)*4,a=data[i+3]/255;if(!a)continue;
    const [h,s]=toHsl(data[i],data[i+1],data[i+2]);
    sin+=Math.sin(h*Math.PI/180)*a*s;cos+=Math.cos(h*Math.PI/180)*a*s;hueWeight+=a*s;
    saturation+=s*a;weight+=a;
   }
  return weight ? {hue:(Math.atan2(sin,cos)*180/Math.PI+360)%360,saturation:saturation/weight,hasHue:hueWeight>1e-8} : null;
 }
 function match(rgb,mode,master,toHsl,fromHsl) {
  let [h,s,l]=toHsl(...rgb);
  if(mode==='hue') {
   if(master.hasHue) h=(h+((((master.hue-h)%360)+540)%360-180)*0.85+360)%360;
   s+=(master.saturation-s)*0.6;
  } else s+=(master.saturation-s)*(mode==='vibrance'?(1-s)*0.9:0.85);
  return fromHsl(h,Math.max(0,Math.min(1,s)),l);
 }
 function prepare(layer,rect,mode,options) {
  const {instances:api,createCanvas}=options;
  const toHsl=rgbToHsl,fromHsl=hslToRgb;
  if(!layer?.img||layer.locked||layer.visible===false||!Array.isArray(layer.bbox))return null;
  const group=api.linked(layer,rect);if(!group.length)return null;
  if(mode==='finish'||mode==='replace')return api.prepareSync(layer,rect,createCanvas);
  if(!['tint','hue','saturation','vibrance'].includes(mode))return null;
  const [ox,oy,x2,y2]=layer.bbox,w=x2-ox,h=y2-oy,master=group[0].sourceBbox;
  const canvas=createCanvas(w,h),ctx=canvas.getContext('2d',{willReadFrequently:true});
  ctx.drawImage(layer.img,0,0,layer.img.width,layer.img.height,0,0,w,h);
  const pixels=ctx.getImageData(0,0,w,h),original=pixels.data.slice();
  const stats=statistics(original,w,h,master,ox,oy,toHsl);if(!stats)return null;
  let aligned=null,alignedData=null;
  if(mode==='tint') {
   aligned=api.prepareSync(layer,rect,createCanvas);if(!aligned)return null;
   alignedData=aligned.canvas.getContext('2d',{willReadFrequently:true}).getImageData(0,0,aligned.canvas.width,aligned.canvas.height).data;
  }
  const visited=new Uint8Array(w*h);let changed=0;
  for(const record of group) {
   const r=record.instanceBbox;if(api.same(r,master))continue;
   for(let y=Math.max(0,Math.floor(r.y1-oy));y<Math.min(h,Math.ceil(r.y2-oy));y++)
    for(let x=Math.max(0,Math.floor(r.x1-ox));x<Math.min(w,Math.ceil(r.x2-ox));x++) {
     const index=y*w+x,i=index*4,dx=x+ox,dy=y+oy;
     if(visited[index]||!original[i+3]||(dx>=master.x1&&dx<master.x2&&dy>=master.y1&&dy<master.y2))continue;
     visited[index]=1;
     let rgb;
     if(mode==='tint') {
      const ai=((dy-aligned.bbox[1])*aligned.canvas.width+dx-aligned.bbox[0])*4;
      const amount=alignedData[ai+3]/255*0.5;
      rgb=[0,1,2].map(c=>Math.round(original[i+c]*(1-amount)+alignedData[ai+c]*amount));
     } else rgb=match([original[i],original[i+1],original[i+2]],mode,stats,toHsl,fromHsl);
     if(rgb.some((value,c)=>value!==original[i+c]))changed++;
     pixels.data[i]=rgb[0];pixels.data[i+1]=rgb[1];pixels.data[i+2]=rgb[2];
    }
  }
  if(!changed)return {unchanged:true,count:group.length};
  ctx.putImageData(pixels,0,0);
  const records=JSON.parse(JSON.stringify(layer.elementInstances));
  const now=Date.now(),field={tint:'lastColorTintAt',hue:'lastHueMatchAt',saturation:'lastSaturationMatchAt',vibrance:'lastVibranceMatchAt'}[mode];
  layer.elementInstances.forEach((record,i)=>{if(group.includes(record))records[i][field]=now;});
  return {canvas,bbox:layer.bbox.slice(),instances:records,count:group.length,changedPixels:changed};
 }
 return Object.freeze({statistics,match,prepare,rgbToHsl,hslToRgb});
});
