const assert=require('node:assert/strict'),rect=require('../js/canvas/zone/rect-marquee.js');
const ref=(a,b)=>{let n=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i])n++;return n;};
let seed=713;function random(n){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;}
for(let trial=0;trial<1600;trial++){const n=random(1100),oa=trial%4,ob=(trial>>2)%4;const A=trial%2?Uint8Array:Uint8ClampedArray;const a=new A(new ArrayBuffer(n+oa),oa,n),b=new Uint8Array(new ArrayBuffer(n+ob),ob,n);for(let i=0;i<n;i++){a[i]=random(256);b[i]=trial%3===0?a[i]:random(256);}assert.equal(rect.countDifferences(a,b),ref(a,b));assert.equal(rect.countDifferences(a,a),0);}
for(let channel=0;channel<4;channel++){const a=new Uint8Array(8),b=a.slice();b[channel]=128;assert.equal(rect.countDifferences(a,b),1);}
assert.equal(rect.countDifferences([256,-1,2],[0,255,2]),2);assert.equal(rect.countDifferences(new Int8Array([-1]),new Uint8Array([255])),1);assert.equal(rect.countDifferences(null,[]),Infinity);assert.equal(rect.countDifferences([1],[]),Infinity);
console.log('Mask difference:1600 aligned/unaligned/soft/tail cases; signed high byte, no-op, generic fallback and invalid inputs pass.');
