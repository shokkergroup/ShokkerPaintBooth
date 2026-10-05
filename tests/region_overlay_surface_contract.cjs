const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const surface = require('../js/canvas/zone/region-overlay-surface.js');
const source = fs.readFileSync(require.resolve('../paint-booth-3-canvas.js'), 'utf8');
const start = source.indexOf('        function _doRenderRegionOverlay() {');
const fn = source.slice(start, source.indexOf('        // ===== UNDO SYSTEM =====', start));
let seed = 930908;
const random = n => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed % n; };
function bounds(mask, width) {
    let minX = width, minY = mask.length / width, maxX = -1, maxY = -1;
    mask.forEach((v, i) => { if (v) { const x = i % width, y = Math.floor(i / width); minX = Math.min(minX,x); minY=Math.min(minY,y); maxX=Math.max(maxX,x);maxY=Math.max(maxY,y); } });
    return { any: maxX >= 0, minX, minY, maxX, maxY };
}
function draw(width, height, zone, cropped) {
    const pixels = new Uint8ClampedArray(width * height * 4).fill(37);
    const allocations = [];
    let contextRefreshes = 0;
    const ctx = {
        clearRect() { pixels.fill(0); },
        createImageData(w,h) { allocations.push(w*h*4); return {width:w,height:h,data:new Uint8ClampedArray(w*h*4)}; },
        putImageData(img,x,y) { for(let row=0;row<img.height;row++) pixels.set(img.data.subarray(row*img.width*4,(row+1)*img.width*4),((row+y)*width+x)*4); },
    };
    const paint = {width,height,style:{width:'100px',height:'100px'}};
    const overlay = {width,height,style:{},getContext:()=>ctx};
    const env = {
        window: { SPBMaskStats: {bounds}, ...(cropped ? {SPBRegionOverlaySurface:surface} : {}) },
        document:{getElementById:id=>id==='paintCanvas'?paint:overlay},
        zones:[zone], selectedZoneIndex:0, ZONE_OVERLAY_COLORS:[[90,180,70,160]], overlayOpacityMultiplier:0.7,
        renderContextActionBar() { contextRefreshes++; },
    };
    vm.createContext(env); vm.runInContext(fn,env); env._doRenderRegionOverlay();
    assert.equal(contextRefreshes,1);
    return {pixels,allocations};
}
for(let trial=0;trial<900;trial++) {
    const width=5+random(45), height=5+random(40), n=width*height;
    const region=new Uint8Array(n), spatial=new Uint8Array(n);
    const x=random(width), y=random(height), right=Math.min(width-1,x+random(8)), bottom=Math.min(height-1,y+random(8));
    for(let row=y;row<=bottom;row++)for(let col=x;col<=right;col++) {
        region[row*width+col]=[0,1,80,255][random(4)];
        spatial[row*width+col]=random(4);
    }
    if(trial%4===0)for(let row=height-3;row<height;row++)for(let col=width-3;col<width;col++)spatial[row*width+col]=1+random(2);
    const zone={regionMask:trial%5?region:null,spatialMask:trial%3?spatial:null};
    const old=draw(width,height,zone,false), next=draw(width,height,zone,true);
    assert.deepEqual(next.pixels,old.pixels,'native fill, spatial precedence, white edges and cleared prior overlay');
    assert.ok(next.allocations[0]<=old.allocations[0]);
}
const allocation = surface.create({createImageData:(width,height)=>({width,height})},4096,4096,[{any:true,minX:574,minY:595,maxX:1474,maxY:1495}]);
assert.deepEqual(allocation.imageData,{width:901,height:901});
assert.equal(allocation.index(595*4096+574),0);
console.log('Region overlay:900 native renderer cases match full-canvas fallback exactly;901px selection allocates3.1MiB instead of64MiB.');
