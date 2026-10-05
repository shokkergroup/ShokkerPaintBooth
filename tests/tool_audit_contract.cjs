const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const {difference,maskDifference}=require('../js/canvas/tool-audit.js');
assert.deepEqual(maskDifference(null,new Uint8Array([0,1,64,255]),2,2),{changedPixels:3,selectedPixels:3,minValue:1,maxValue:255,distinctNonzeroValues:3,bounds:[0,0,1,1]});
assert.deepEqual(maskDifference(new Uint8Array([1,0,0,0]),null,2,2),{changedPixels:1,selectedPixels:0,minValue:0,maxValue:0,distinctNonzeroValues:0,bounds:null});
const a={width:2,height:2,data:new Uint8ClampedArray(16)};
let b={...a,data:new Uint8ClampedArray(16)};
assert.deepEqual(difference(a,b),{changedPixels:0,alphaChanged:0,maxDelta:0,bounds:null});
b.data[4]=200;b.data[15]=90;
assert.deepEqual(difference(a,b),{changedPixels:2,alphaChanged:1,maxDelta:200,bounds:[1,0,1,1]});
assert.deepEqual(difference(a,{...b,width:1}),{dimensionsChanged:true});
for(const [hostname,search] of [['localhost',''],['example.com','?spb-tool-audit=1']]){
 const c={document:{addEventListener(){throw Error('Normal sessions must install no listeners');}},location:{hostname,search},URLSearchParams};
 c.window=c;vm.runInNewContext(fs.readFileSync('js/canvas/tool-audit.js','utf8'),c);
}
console.log('Tool audit: exact pixel differences and disabled-by-default/local-only gates pass.');
