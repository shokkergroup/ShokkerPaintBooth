const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const client=require('../js/canvas/layer/adjustment-worker-client.js');
const mutators=require('../js/canvas/layer/adjustment-preview.js');
class Worker {
 constructor(){this.sent=[];this.stopped=0;Worker.last=this;}
 postMessage(m){this.sent.push(m);}
 terminate(){this.stopped++;}
 result(id,pixels=new Uint8ClampedArray(4).buffer){this.onmessage({data:{id,pixels}});}
}
function fixture(){const frames=[],errors=[],source=new Uint8ClampedArray(4*1024*1024);source[0]=17;
 const c=client.create({source,mutator:'applyBrightnessContrast',WorkerType:Worker,onFrame:p=>frames.push(p),onError:v=>errors.push(v)});
 return {c,w:Worker.last,frames,errors,source};}
let f=fixture();assert.equal(f.source[0],17);assert.notEqual(f.w.sent[0].source,f.source.buffer);
f.c.request([10]);f.c.request([20]);f.c.request([30]);assert.equal(f.w.sent.length,2);
f.w.result(1);assert.equal(f.frames.length,1);assert.deepEqual(f.w.sent[2].values,[30]);
f.w.result(1);assert.equal(f.frames.length,1,'ignore stale replies');f.w.result(2);assert.equal(f.frames.length,2);
f.c.dispose();f.w.result(2);assert.equal(f.frames.length,2);assert.equal(f.c.request([40]),false);assert.equal(f.w.stopped,1);
f=fixture();f.c.request([10]);f.c.request([99]);f.w.onerror({preventDefault(){}});assert.deepEqual(f.errors,[[99]]);assert.equal(f.c.request([1]),false);
assert.equal(client.create({source:new Uint8ClampedArray(4),WorkerType:Worker}),null);
// Execute the actual worker handler and compare all eight algorithms with Apply.
const cases={applyBrightnessContrast:[21,-15],applyHueSaturation:[47,25,-8],applyVibrance:[60],applyColorTemperature:[-30],applyDesaturate:[70],applyInvert:[80],applyGradientMap:['#173a5f','#ef9b31'],applyColorReplace:['#204060','#e03090',60]};
let seed=123;const source=new Uint8ClampedArray(4096);for(let i=0;i<source.length;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;source[i]=seed>>>24;}
for(const [name,values] of Object.entries(cases)){
 let reply;const env={Uint8ClampedArray,importScripts(){},SPBAdjustmentPreview:mutators,postMessage:m=>reply=m};env.self=env;
 vm.runInNewContext(fs.readFileSync('js/canvas/layer/adjustment-worker.js','utf8'),env);
 env.onmessage({data:{type:'init',mutator:name,source:source.buffer.slice(0)}});
 env.onmessage({data:{type:'preview',id:7,values}});
 const expected=source.slice();mutators[name](expected,...values);
 assert.deepEqual(new Uint8ClampedArray(reply.pixels),expected,name+' worker/Apply parity');
}
console.log('Adjustment worker: coalescing, source ownership, cancel/stale/error fallback and 8-method exact parity pass.');
