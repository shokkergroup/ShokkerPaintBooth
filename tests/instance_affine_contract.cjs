'use strict';
const assert=require('node:assert/strict');
const api=require('../js/canvas/layer/element-instances.js');
const raster=require('../js/canvas/layer/layer-transform-raster.js');
const point=(m,p)=>[m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5]];
const close=(a,b)=>a.forEach((n,i)=>assert.ok(Math.abs(n-b[i])<1e-7,`${a} != ${b}`));
function expected(change,p) {
 const r=change.from,t=change.to,i=change.item;
 let x=(p[0]-(r.x1+r.x2)/2)*i.width/(r.x2-r.x1),y=(p[1]-(r.y1+r.y2)/2)*i.height/(r.y2-r.y1);
 const rad=i.rotation*Math.PI/180,c=Math.cos(rad),s=Math.sin(rad);
 return [(t.x1+t.x2)/2+(i.flipH?-1:1)*(x*c-y*s),(t.y1+t.y2)/2+(i.flipV?-1:1)*(x*s+y*c)];
}
const master={x1:31,y1:70,x2:131,y2:140},copy={x1:250,y1:270,x2:350,y2:340};
let cases=0;
for(const angle of [0,30,90,135,180,270])for(const flipH of [false,true])for(const flipV of [false,true])for(const scale of [0.6,1,1.4]) {
 const item={sourceRect:copy,centerX:300,centerY:310,width:100*scale,height:70*1.2,rotation:angle,flipH,flipV};
 const change={from:copy,to:raster.transformedAabb(item),item};
 const record={sourceBbox:{...master},instanceBbox:{...copy}},layer={elementInstances:[record]},original=api.placement(record);
 api.relocate(layer,[change]);
 for(const p of [[31,70],[81,105],[131,140],[50,128]]) close(point(api.placement(record),p),expected(change,point(original,p)));
 const mi={sourceRect:master,centerX:100,centerY:110,width:83,height:99,rotation:17,flipH:true,flipV:false};
 const mc={from:master,to:raster.transformedAabb(mi),item:mi};
 const prior=api.placement(record);api.relocate(layer,[mc]);
 for(const p of [[31,70],[81,105],[131,140]])close(point(api.placement(record),expected(mc,p)),point(prior,p));
 const serialized=JSON.parse(JSON.stringify(layer));close(api.placement(serialized.elementInstances[0]),api.placement(record));
 cases++;
}
assert.equal(api.inverse([0,0,0,0,0,0]),null);
console.log(`Instance affine placement: ${cases} rotated/flipped/nonuniform scale cases, master reorientation, raster-center parity and JSON persistence pass.`);
