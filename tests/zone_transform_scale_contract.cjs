'use strict';
const assert=require('node:assert/strict');
const scale=require('../js/canvas/zone/transform-scale.js');
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8, `${a} != ${b}`);
let count=0;
for(const dragging of ['n','s','e','w','ne','nw','se','sw'])for(const rotation of [0,30,90,173])for(const centered of [false,true]) {
 const hx=dragging.includes('e')?1:dragging.includes('w')?-1:0,hy=dragging.includes('s')?1:dragging.includes('n')?-1:0;
 const c=Math.cos(rotation*Math.PI/180),sn=Math.sin(rotation*Math.PI/180);
 const s={target:'base',dragging,dragStartRot:rotation,dragStartBoxW:400,dragStartBoxH:200,dragStartCX:600,dragStartCY:500,origBoxW:400,origBoxH:200,origScaleX:0.7,origScaleY:0.7,subRect:{}};
 const x=30*hx,y=20*hy;assert.equal(scale.apply(s,x*c-y*sn,x*sn+y*c,{altKey:centered}),true);
 near(s.boxW/s.boxH,2);near(s.scaleX,s.scaleY);
 if(centered){near(s.centerX,600);near(s.centerY,500);}
 else {near(s.centerX-hx*s.boxW/2*c+hy*s.boxH/2*sn,600-hx*200*c+hy*100*sn);near(s.centerY-hx*s.boxW/2*sn-hy*s.boxH/2*c,500-hx*200*sn-hy*100*c);}
 near(s.subRect.x2-s.subRect.x1,s.boxW);near(s.subRect.y2-s.subRect.y1,s.boxH);count++;
}
const vertical={target:'base',dragging:'s',dragStartRot:0,dragStartBoxW:1433.6,dragStartBoxH:1433.6,dragStartCX:1024,dragStartCY:1024,origBoxW:1433.6,origBoxH:1433.6};
scale.apply(vertical,0,150,{});near(vertical.boxW/2048,0.7732421875);near(vertical.centerY,1099);
assert.equal(scale.apply({...vertical,target:'layer'},0,150,{}),false);
console.log(`${count} Zone handle cases: uniform material ratio, opposite anchor/Alt center, rotated axes, sub-piece frame; vertical commit scale positive; Layer rejected.`);
