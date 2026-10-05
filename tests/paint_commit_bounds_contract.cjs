const assert=require('node:assert/strict');
const api=require('../js/canvas/layer/paint-commit-bounds.js');
let seed=937;
const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
function img(w,h){return {width:w,height:h,data:new Uint8ClampedArray(w*h*4)};}
// Compare optimized bounds against a brute-force alpha merge, including empty
// surfaces, off-canvas art, negative offsets, and layers entirely off-sheet.
for(let n=0;n<500;n++){
 const w=2+Math.floor(rand()*14),h=2+Math.floor(rand()*14),o=img(1+Math.floor(rand()*20),1+Math.floor(rand()*20)),a=img(w,h);
 const ox=Math.floor(rand()*30)-15,oy=Math.floor(rand()*30)-15;
 for(const im of [a,o])for(let i=3;i<im.data.length;i+=4)im.data[i]=rand()<.3?Math.ceil(rand()*255):0;
 if(n%7===0)a.data.fill(0);if(n%13===0)o.data.fill(0);
 const x0=Math.min(0,ox),y0=Math.min(0,oy),m=img(Math.max(w,ox+o.width)-x0,Math.max(h,oy+o.height)-y0);
 for(let y=0;y<o.height;y++)for(let x=0;x<o.width;x++)m.data[((y+oy-y0)*m.width+x+ox-x0)*4+3]=o.data[(y*o.width+x)*4+3];
 for(let y=0;y<h;y++)for(let x=0;x<w;x++)m.data[((y-y0)*m.width+x-x0)*4+3]=a.data[(y*w+x)*4+3];
 assert.deepEqual(api.unionOffCanvas(api.alphaBounds(a),o,ox,oy,w,h),api.alphaBounds(m,x0,y0));
}
console.log('Paint commit bounds: 500 seeded merges match brute-force alpha bounds.');
