const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const scale=require('../js/canvas/layer/transform-scale.js');
const geometry=require('../js/canvas/layer/element-transform-state.js');
const near=(a,b)=>assert(Math.abs(a-b)<1e-7,`${a} != ${b}`);
function anchor(s,hx,hy,start=false){const r=s.dragStartRot*Math.PI/180,c=Math.cos(r),n=Math.sin(r),w=start?s.dragStartBoxW:s.boxW,h=start?s.dragStartBoxH:s.boxH,x=-hx*w/2,y=-hy*h/2;return [(start?s.dragStartCX:s.centerX)+x*c-y*n,(start?s.dragStartCY:s.centerY)+x*n+y*c];}
let count=0;
for(const handle of ['n','s','e','w','ne','nw','se','sw'])for(const rot of [0,17,90,137,270])for(const alt of [false,true])for(const shift of [false,true])for(const sign of [-1,1]){
 const s={target:'layer',dragging:handle,dragStartRot:rot,rotation:rot,dragStartCX:500,dragStartCY:600,dragStartBoxW:180,dragStartBoxH:310,origBoxW:240,origBoxH:400,dragStartSX:sign,dragStartSY:1};
 const hx=handle.includes('e')?1:handle.includes('w')?-1:0,hy=handle.includes('s')?1:handle.includes('n')?-1:0;
 const expected=anchor(s,hx,hy,true);scale.apply(s,25,-15,{altKey:alt,shiftKey:shift});
 if(alt){near(s.centerX,500);near(s.centerY,600);}else anchor(s,hx,hy).forEach((v,i)=>near(v,expected[i]));
 if(shift&&hx&&hy)near(s.boxW/s.boxH,180/310);
 assert.equal(Math.sign(s.scaleX),sign);
 // Returning to the exact drag origin cancels geometry, even after modifiers change.
 scale.apply(s,0,0,{});near(s.boxW,180);near(s.boxH,310);near(s.centerX,500);near(s.centerY,600);count++;
}
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const begin=source.indexOf('function onTransformMouseMove(e) {'),end=source.indexOf('function onTransformMouseUp(e)',begin);
const move=source.slice(begin,end);
function run(code){const s={target:'layer',dragging:'e',dragStartX:0,dragStartY:0,dragStartCX:200,dragStartCY:200,centerX:200,centerY:200,dragStartBoxW:100,dragStartBoxH:80,boxW:100,boxH:80,origBoxW:100,origBoxH:80,origScaleX:1,origScaleY:1,dragStartRot:0,rotation:0,dragStartSX:1,dragStartSY:1,origSubRect:{x1:150,y1:160,x2:250,y2:240},subRect:{x1:150,y1:160,x2:250,y2:240}};
 const c={freeTransformState:s,window:{SPBLayerTransformScale:scale,SPBElementTransformState:geometry},_transformGetPixel:e=>({x:e.x,y:e.y}),drawTransformHandles(){},document:{getElementById:()=>({width:512,height:512})},_isZoneFreeTransformTarget:()=>false};vm.createContext(c);vm.runInContext(code,c);c.onTransformMouseMove({x:30,y:0,preventDefault(){}});return s;}
const actual=run(move);near(actual.boxW,130);near(actual.centerX-actual.boxW/2,150);near(actual.subRect.x1,150);near(actual.subRect.x2,280);
const old=run(move.replace("s.target === 'layer' && window.SPBLayerTransformScale","false"));near(old.boxW,160);assert.notEqual(old.centerX-old.boxW/2,150,'old-code negative control moves opposite edge');
assert.equal(scale.apply({target:'zone-base',dragging:'e'},10,0,{}),false);
console.log(`Layer scale: ${count} rotated/modifier/flip anchor cases, return-to-origin, real mousemove/element frame and old doubled-center negative control pass.`);
