const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8').replace(/\r\n/g, '\n');
const start = source.indexOf('            if (mMinX === 0 && mMinY === 0');
const end = source.indexOf('\n        }\n    }\n    _activeLayerCanvas', start);
assert(start > 0 && end > start);
const commit = source.slice(start, end);
let seed = 947;
const rand = n => { seed = (Math.imul(seed,1664525)+1013904223)>>>0; return seed%n; };
for (let trial = 0; trial < 400; trial++) {
    const mW = 2+rand(30), mH = 2+rand(30), merged = {width:mW,height:mH,pixels:new Uint8ClampedArray(mW*mH*4)};
    for(let i=0;i<merged.pixels.length;i++) merged.pixels[i]=rand(256);
    const mMinX = trial%2 ? rand(mW) : 0, mMinY = trial%2 ? rand(mH) : 0;
    const mcW = trial%2 ? 1+rand(mW-mMinX) : mW, mcH = trial%2 ? 1+rand(mH-mMinY) : mH;
    const ox0=-rand(40),oy0=-rand(40),original=merged.pixels.slice();
    let copies=0;
    const context = {merged,mW,mH,mMinX,mMinY,mcW,mcH,ox0,oy0,layer:{},document:{createElement(tag){
        assert.equal(tag,'canvas');copies++;
        const canvas={getContext(type,options){assert.equal(type,'2d');assert.equal(options.willReadFrequently,true);return {drawImage(src,x,y,w,h,dx,dy,dw,dh){
            assert.equal(src,merged);assert.equal(dx,0);assert.equal(dy,0);assert.equal(dw,w);assert.equal(dh,h);
            canvas.pixels=new Uint8ClampedArray(w*h*4);
            for(let row=0;row<h;row++)canvas.pixels.set(src.pixels.subarray(((y+row)*mW+x)*4,((y+row)*mW+x+w)*4),row*w*4);
        }};}};return canvas;
    }}};
    vm.runInNewContext(commit,context);
    const full=mMinX===0&&mMinY===0&&mcW===mW&&mcH===mH;
    assert.equal(copies,full?0:1);assert.equal(context.layer.img===merged,full);
    assert.deepEqual(Array.from(context.layer.bbox),[ox0+mMinX,oy0+mMinY,ox0+mMinX+mcW,oy0+mMinY+mcH]);
    const expected=new Uint8ClampedArray(mcW*mcH*4);
    for(let y=0;y<mcH;y++)for(let x=0;x<mcW;x++)for(let c=0;c<4;c++)expected[(y*mcW+x)*4+c]=original[((y+mMinY)*mW+x+mMinX)*4+c];
    assert.deepEqual(context.layer.img.pixels,expected);assert.deepEqual(merged.pixels,original);
}
console.log('Layer merge reuse: 400 exact RGBA/bbox cases; full bounds allocate no duplicate canvas.');
