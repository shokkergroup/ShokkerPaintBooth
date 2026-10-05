const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=src.indexOf('function _resetAdjustmentPreviewCandidate('),end=src.indexOf('function adjustBrightnessContrast(',start);
function canvas(bytes){const c={width:2,height:1,bytes:new Uint8ClampedArray(bytes)};
 const ctx={createImageData:(w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)}),putImageData:f=>{c.bytes=new Uint8ClampedArray(f.data);}};
 c.getContext=()=>ctx;return c;}
function fixture(isLayer){
 const pixels=[50,100,150,77,20,40,60,91],original=canvas(pixels),candidate=canvas(pixels),destination=canvas(pixels),layer={img:original};
 const target={isLayer,layer,canvas:candidate,ctx:candidate.getContext(),compositeCanvas:destination,sourcePixels:new Uint8ClampedArray(pixels)};
 let workerOptions,stopped=false,commits=0;
 const c={Uint8ClampedArray,ImageData:class {constructor(data,width,height){Object.assign(this,{data,width,height});}},
  document:{getElementById:()=>destination},_getAdjustmentTarget:()=>target,
  _getAdjustmentPreviewMutator:()=>require('../js/canvas/layer/adjustment-preview.js').applyBrightnessContrast,
  SPBAdjustmentWorker:{create(options){workerOptions=options;return {request:()=>true,dispose(){stopped=true;}};}},
  recompositeFromLayers(){destination.bytes=layer.img.bytes.slice();c._spbLayerRev=(c._spbLayerRev||0)+1;},
  triggerPreviewRender(){c.previewRev=c._spbLayerRev;},
  _commitAdjustment(t){assert(stopped,'Apply must stop worker first');if(isLayer)assert.equal(layer.img,original,'restore original before history commit');commits++;if(isLayer)layer.img=t.canvas;else destination.bytes=t.canvas.bytes.slice();return true;}};
 c.window=c;vm.createContext(c);vm.runInContext(src.slice(start,end),c);
 const session=c._createAdjustmentPreviewSession('brightness','applyBrightnessContrast');
 return {c,session,layer,original,destination,target,worker:()=>workerOptions,commits:()=>commits,stopped:()=>stopped};
}
for(const isLayer of [true,false]){
 let f=fixture(isLayer);f.session.preview([20,0]);const changed=f.target.sourcePixels.slice();require('../js/canvas/layer/adjustment-preview.js').applyBrightnessContrast(changed,20,0);
 f.worker().onFrame(changed);assert.equal(f.destination.bytes[0],70);
 const previewRev=f.c.previewRev;assert(previewRev>0,'preview publication invalidates paint cache');
 f.session.cancel();assert(f.stopped());assert.equal(f.destination.bytes[0],50);assert(f.c.previewRev>previewRev,'Cancel invalidates preview cache');
 f.worker().onFrame(changed);assert.equal(f.destination.bytes[0],50,'late worker response cannot repaint after Cancel');assert.equal(f.commits(),0);
 f=fixture(isLayer);f.session.preview([20,0]);f.session.commit([35,0]);assert.equal(f.commits(),1);assert.equal((isLayer?f.layer.img:f.destination).bytes[0],85);
 f.worker().onFrame(changed);assert.equal((isLayer?f.layer.img:f.destination).bytes[0],85,'late response cannot overwrite Apply');
}
console.log('Adjustment sessions: exact Apply values, original restoration, no Cancel history, flat-cache revision and late-frame isolation pass.');
