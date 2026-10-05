'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const appearance=require('../js/canvas/layer/instance-appearance.js'),instances=require('../js/canvas/layer/element-instances.js');
// The live global helper returns an object; preparation must ignore it.
const source=fs.readFileSync(require.resolve('../paint-booth-3-canvas.js'),'utf8');
const env={};vm.createContext(env);vm.runInContext(source.slice(source.indexOf('function rgbToHsl('),source.indexOf('window._ctxBreakInstanceLink')),env);
class Canvas {
 constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}
 getContext(){const c=this;return {
  getImageData(){return {data:c.data.slice()};},putImageData(p){c.data.set(p.data);},
  clearRect(x,y,w,h){for(let j=y;j<y+h;j++)for(let i=x;i<x+w;i++)if(i>=0&&j>=0&&i<c.width&&j<c.height)c.data.fill(0,(j*c.width+i)*4,(j*c.width+i+1)*4);},
  drawImage(src,...args){let sx=0,sy=0,sw=src.width,sh=src.height,dx=0,dy=0,dw=sw,dh=sh;if(args.length===2)[dx,dy]=args;else[sx,sy,sw,sh,dx,dy,dw,dh]=args;for(let y=0;y<dh;y++)for(let x=0;x<dw;x++){let a=Math.floor(sx+x*sw/dw),b=Math.floor(sy+y*sh/dh),tx=x+dx,ty=y+dy;if(a<0||b<0||a>=src.width||b>=src.height||tx<0||ty<0||tx>=c.width||ty>=c.height)continue;let i=(b*src.width+a)*4;if(src.data[i+3])c.data.set(src.data.slice(i,i+4),(ty*c.width+tx)*4);}}
 };}
 toDataURL(){return 'data:image/png;base64,'+Buffer.from(this.data).toString('base64');}
}
const createCanvas=(w,h)=>new Canvas(w,h),options={instances,createCanvas,toHsl:()=>({h:0,s:0,l:0}),fromHsl:()=>{throw Error("global conversion used");}};
const hues=[...env.hslToRgb(359,1,0.5),255,...env.hslToRgb(1,1,0.5),255,0,255,0,0];
const stats=appearance.statistics(hues,3,1,{x1:0,y1:0,x2:3,y2:1},0,0,env.rgbToHsl);
assert.ok(stats.hue<1||stats.hue>359);assert.equal(stats.saturation,1);
const matched=appearance.match(env.hslToRgb(359,0.5,0.5),'hue',{hue:1,saturation:0.5,hasHue:true},env.rgbToHsl,env.hslToRgb);
const [mh]=env.rgbToHsl(...matched);assert.ok(mh<3||mh>358,'hue takes shortest path across red');
for(const mode of ['finish','replace','tint','hue','saturation','vibrance']) {
 const img=createCanvas(20,8),master={x1:40,y1:30,x2:44,y2:34},copy={x1:50,y1:30,x2:54,y2:34};
 for(let y=0;y<4;y++)for(let x=0;x<4;x++){img.data.set([220,30,30,128],(y*20+x)*4);img.data.set([80,100,140,80],(y*20+x+10)*4);}
 img.data.fill(0,0,4);img.data.set([5,10,20,71],(7*20+18)*4);
 const layer={img,bbox:[40,30,60,38],elementInstances:[{sourceBbox:master,instanceBbox:copy}]},before=img.data.slice(),links=JSON.stringify(layer.elementInstances);
 const result=appearance.prepare(layer,copy,mode,options);assert.ok(result&&!result.unchanged,mode);assert.deepEqual(img.data,before);assert.equal(JSON.stringify(layer.elementInstances),links);
 for(let y=0;y<8;y++)for(let x=0;x<20;x++) {
  const i=(y*20+x)*4,isCopy=x>=10&&x<14&&y<4;
  if(!isCopy)assert.deepEqual(result.canvas.data.slice(i,i+4),before.slice(i,i+4),mode+' outside/master');
  if(!['finish','replace'].includes(mode))assert.equal(result.canvas.data[i+3],before[i+3],mode+' alpha');
 }
 if(mode==='finish'||mode==='replace')for(let y=0;y<4;y++)for(let x=0;x<4;x++)assert.deepEqual(result.canvas.data.slice((y*20+x+10)*4,(y*20+x+11)*4),before.slice((y*20+x)*4,(y*20+x+1)*4));
 assert.equal(appearance.prepare({...layer,locked:true},copy,mode,options),null);
 assert.equal(appearance.prepare({...layer,visible:false},copy,mode,options),null);
}
console.log('Six instance appearance modes: current master from either end, alpha/holes, cropped origin, outside/master immutability, locks/hidden, circular hue and shortest hue path pass.');
