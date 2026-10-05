const assert = require('node:assert/strict');
const display = require('../js/canvas/layer/brush-display-patch.js');
const writes = [], children = [];
const parent = {append(c) {children.push(c);}};
const source = {width:4096,height:4096,style:{},parentElement:parent,
 ownerDocument:{createElement() {return {style:{},setAttribute(){},
  getContext(){return {putImageData(p,x,y){writes.push([p,x,y]);}};},
  remove(){children.splice(children.indexOf(this),1);}};}}};
const pixels = {width:20,height:10,data:new Uint8ClampedArray(20*10*4).fill(255)};
assert(display.show(pixels,{x:100,y:200,width:20,height:10},source));
assert.equal(children.length,1); assert.equal(writes.length,1);
assert.equal(children[0].width,20); assert.equal(children[0].style.left,'2.44140625%');
const expanded = display.expand({x:110,y:190,width:30,height:10});
assert.deepEqual(expanded,{x:100,y:190,width:40,height:20});
// A partially transparent update cannot cover old opaque source pixels.
pixels.data[3]=0;
assert.equal(display.show(pixels,expanded,source),false);
assert.equal(writes.length,1);
// The controller must publish the expanded region before clearing the surface.
assert.deepEqual(display.expand({x:110,y:190,width:30,height:10}),expanded);
display.clear(); assert.equal(children.length,0);
assert.deepEqual(display.expand({x:1,y:2,width:3,height:4}),{x:1,y:2,width:3,height:4});
assert.equal(display.expand(null),null);
pixels.data[3]=255; source.style.opacity='0';
assert.equal(display.show(pixels,expanded,source),false);
source.style.opacity=''; source.parentElement=null;
assert.equal(display.show(pixels,expanded,source),false);
console.log('Brush display: small surface, accumulated region, transparent fallback, hidden source and cleanup pass.');
