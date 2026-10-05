'use strict';
const assert=require('node:assert/strict');
const api=require('../js/canvas/layer/element-instances.js');
class Canvas {
 constructor(w,h){this.width=w;this.height=h;this.pixels=new Uint8ClampedArray(w*h*4);}
 getContext(){const c=this;return{
  getImageData:()=>({data:c.pixels.slice()}),
  clearRect(x,y,w,h){for(let j=y;j<y+h;j++)for(let i=x;i<x+w;i++)if(i>=0&&j>=0&&i<c.width&&j<c.height)c.pixels.fill(0,(j*c.width+i)*4,(j*c.width+i+1)*4);},
  drawImage(src,...a){let sx=0,sy=0,sw=src.width,sh=src.height,dx=0,dy=0,dw=sw,dh=sh;if(a.length===2)[dx,dy]=a;else [sx,sy,sw,sh,dx,dy,dw,dh]=a;
   for(let y=0;y<dh;y++)for(let x=0;x<dw;x++){const ax=Math.floor(sx+x*sw/dw),ay=Math.floor(sy+y*sh/dh),bx=dx+x,by=dy+y;if(ax<0||ay<0||ax>=src.width||ay>=src.height||bx<0||by<0||bx>=c.width||by>=c.height)continue;const si=(ay*src.width+ax)*4,di=(by*c.width+bx)*4;if(src.pixels[si+3])c.pixels.set(src.pixels.slice(si,si+4),di);}
  }
 };}
 toDataURL(){return 'data:image/png;base64,'+Buffer.from(this.pixels).toString('base64');}
}
const make=(w,h)=>new Canvas(w,h);
for(const [ox,oy] of [[40,30],[0,0],[-10,-20]]){
 const src=make(100,100);for(let y=25;y<45;y++)for(let x=20;x<40;x++)src.pixels.set([20,50,150,128],(y*100+x)*4);
 const rect={x1:ox+20,y1:oy+25,x2:ox+40,y2:oy+45};
 const legacy={sourceBbox:rect,instanceBbox:rect};
 const layer={img:src,bbox:[ox,oy,ox+100,oy+100],elementInstances:[legacy]};const before=src.pixels.slice();
 const result=api.prepare(layer,rect,300,300,make);assert.ok(result);assert.deepEqual(src.pixels,before);assert.equal(layer.elementInstances.length,1);
 assert.equal(result.instances.length,1);assert.ok(!api.same(result.instances[0].sourceBbox,result.instances[0].instanceBbox));
 const snapshot=Buffer.from(result.instances[0].sourcePixelSnapshot.split(',')[1],'base64');assert.equal(snapshot.length,20*20*4);for(let i=0;i<snapshot.length;i+=4)assert.deepEqual([...snapshot.slice(i,i+4)],[20,50,150,128]);
 let visible=0;for(let i=3;i<result.canvas.pixels.length;i+=4)if(result.canvas.pixels[i])visible++;assert.equal(visible,800);
 assert.equal(api.prepare({...layer,locked:true},rect,300,300,make),null);
}
assert.equal(api.freePosition({x1:0,y1:0,x2:20,y2:20},100,100,()=>true),null);
console.log('Instance preparation: exact cropped alpha/RGB, source immutability, non-overlapping visible copy, legacy self-link migration, off-canvas origins, lock and no-space cases pass.');

const a={x1:0,y1:0,x2:20,y2:20},b={x1:40,y1:0,x2:60,y2:20},c={x1:80,y1:0,x2:100,y2:20};
const links={elementInstances:[{sourceBbox:{...a},instanceBbox:{...b}},{sourceBbox:{...a},instanceBbox:{...c}}]};
assert.equal(api.linked(links,b).length,2);
api.relocate(links,[{from:a,to:b},{from:b,to:a}]);
assert.deepEqual(links.elementInstances[0].sourceBbox,b);assert.deepEqual(links.elementInstances[0].instanceBbox,a);
assert.deepEqual(links.elementInstances[1].sourceBbox,b);assert.deepEqual(links.elementInstances[1].instanceBbox,c);
console.log('Instance links: member lookup and simultaneous master/copy relocation retain independent positions.');

// Live master has changed since creation; its transparent hole must erase old ink.
for(const [ox,oy] of [[40,30],[-10,-20]]) {
 const src=make(100,60),source={x1:ox+2,y1:oy+3,x2:ox+12,y2:oy+13};
 const target={x1:ox+65,y1:oy+20,x2:ox+75,y2:oy+30};
 for(let y=3;y<13;y++)for(let x=2;x<12;x++)src.pixels.set([231,51,80,128],(y*100+x)*4);
 src.pixels.fill(0,(6*100+5)*4,(6*100+6)*4);
 for(let y=20;y<30;y++)for(let x=65;x<75;x++)src.pixels.set([1,2,3,255],(y*100+x)*4);
 src.pixels.set([5,7,11,37],(50*100+80)*4);
 const layer={img:src,bbox:[ox,oy,ox+100,oy+60],elementInstances:[{sourceBbox:source,instanceBbox:target,sourcePixelSnapshot:'stale'}]};
 const before=src.pixels.slice(),metadata=JSON.stringify(layer.elementInstances);
 for(const picked of [source,target]) {
  const out=api.prepareSync(layer,picked,make);assert.equal(out.count,1);assert.deepEqual(out.bbox,layer.bbox);
  for(let y=0;y<10;y++)for(let x=0;x<10;x++)assert.deepEqual(out.canvas.pixels.slice(((y+20)*100+x+65)*4,((y+20)*100+x+66)*4),src.pixels.slice(((y+3)*100+x+2)*4,((y+3)*100+x+3)*4));
  for(let y=0;y<60;y++)for(let x=0;x<100;x++)if(!(x>=65&&x<75&&y>=20&&y<30))assert.deepEqual(out.canvas.pixels.slice((y*100+x)*4,(y*100+x+1)*4),src.pixels.slice((y*100+x)*4,(y*100+x+1)*4));
  assert.notEqual(out.instances[0].sourcePixelSnapshot,'stale');assert.deepEqual(src.pixels,before);assert.equal(JSON.stringify(layer.elementInstances),metadata);
 }
 assert.equal(api.prepareSync({...layer,locked:true},source,make),null);
 assert.equal(api.prepareSync({...layer,visible:false},source,make),null);
}
console.log('Instance sync: current master RGB/alpha, transparent holes, independent placement, cropped/off-canvas origins, read-only candidate and lock/hidden guards pass.');
// Promotion/unlink preserve pixels, independent placements and other groups.
{
 const rects=[0,30,60,90].map(x=>({x1:x,y1:0,x2:x+20,y2:20}));
 const source=make(120,30);source.pixels.fill(123);
 const ownRecords=[1,2].map(n=>({sourceBbox:{...rects[0]},instanceBbox:{...rects[n]},sourceToInstance:[1,0,0,1,n*30,0]}));
 const foreign={sourceBbox:{...rects[3]},instanceBbox:{x1:90,y1:25,x2:110,y2:45}};
 const layer={img:source,bbox:[0,0,120,30],elementInstances:ownRecords.concat(foreign)},before=JSON.stringify(layer.elementInstances),pixels=source.pixels.slice();
 const promoted=api.prepareLinks(layer,rects[1],'promote',make);
 assert.equal(promoted.instances.length,3);assert.deepEqual(promoted.instances[0],foreign);
 const oldMaster=promoted.instances.find(i=>api.same(i.instanceBbox,rects[0]));
 const sibling=promoted.instances.find(i=>api.same(i.instanceBbox,rects[2]));
 assert.deepEqual(oldMaster.sourceBbox,rects[1]);assert.deepEqual(sibling.sourceBbox,rects[1]);
 assert.deepEqual(oldMaster.sourceToInstance.map(n=>n+0),[1,0,0,1,-30,0]);assert.deepEqual(sibling.sourceToInstance,[1,0,0,1,30,0]);
 assert.equal(JSON.stringify(layer.elementInstances),before);assert.deepEqual(source.pixels,pixels);
 const childBroken=api.prepareLinks(layer,rects[1],'break',make);assert.equal(childBroken.instances.length,2);assert.deepEqual(childBroken.instances,[ownRecords[1],foreign]);
 const masterBroken=api.prepareLinks(layer,rects[0],'break',make);assert.equal(masterBroken.instances.length,2);
 assert.deepEqual(masterBroken.instances[1].sourceBbox,rects[1]);assert.deepEqual(masterBroken.instances[1].instanceBbox,rects[2]);assert.deepEqual(masterBroken.instances[1].sourceToInstance,[1,0,0,1,30,0]);
 assert.equal(api.prepareLinks({...layer,locked:true},rects[1],'promote',make),null);
 assert.equal(api.prepareLinks({...layer,visible:false},rects[1],'break',make),null);
 assert.equal(api.prepareLinks(layer,rects[0],'promote',make),null);
 const two={...layer,elementInstances:[ownRecords[0]]};assert.deepEqual(api.prepareLinks(two,rects[0],'break',make).instances,[]);
 console.log('Link changes: promotion rebases siblings, child/master break retains remaining relationships, pixels/source metadata immutable, unrelated groups preserved, lock/hidden/no-op guards pass.');
}
