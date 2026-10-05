// Exercise real history/composite/PNG functions with a deterministic one-pixel
// canvas. The browser proof separately covers real 2048-square RGBA exports.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
function extract(name, end) {
    const start = source.indexOf('function ' + name + '(');
    assert(start >= 0, name);
    const block = source.slice(start, source.indexOf(end, start));
    return block.slice(0, block.lastIndexOf('}') + 1);
}
let encodes = 0, compositions = 0;
function canvas(value = 0) {
    const c = {width:1,height:1,pixel:value};
    const ctx = {canvas:c, clearRect(){c.pixel=0;}, drawImage(img){c.pixel=img.pixel;},
        getImageData(){return {data:new Uint8ClampedArray([c.pixel,0,0,255])};},
        createImageData(){return {data:new Uint8ClampedArray(4)};},
        putImageData(data){c.pixel=data.data[0];}};
    c.getContext=()=>ctx;
    c.toDataURL=()=>{encodes++;return 'png:'+c.pixel;};
    return c;
}
const pc=canvas(90);
// Model the native regression: an existing display surface rounds a draw,
// while a fresh composite and explicit pixel publication remain exact.
pc.getContext().drawImage=img=>{pc.pixel=img.pixel-1;};
const c = {console, performance:{now:()=>1000}, document:{
    getElementById:id=>id==='paintCanvas'?pc:null, createElement:()=>canvas()},
    _psdLayersLoaded:true, _psdLayers:[{id:1,img:canvas(90),bbox:[0,0,1,1]}],
    _activeLayerCanvas:null, _liveCompositeMemo:{}, _pngMemo:{},
    _layerUndoStack:[{type:'image',layerId:1,imgCanvas:canvas(120),bbox:[0,0,1,1],label:'Burn'}],
    _layerRedoStack:[], paintImageData:{},
    _spbInspectLayerStack:()=>({ok:true}),
    _spbCompositeLayerStack(ctx,layers){compositions++;ctx.drawImage(layers[0].img);return {ok:true};},
    invalidateLayerVisibleContributionCache(){}, _spbScheduleLayerAutosave(){},
    renderLayerPanel(){}, _trimLayerUndoHistory(){},
    triggerPreviewRender(){c.preview=c._encodedPngForCanvas(c.buildLivePaintCompositeCanvas());}
};
c.window=c; vm.createContext(c);
vm.runInContext(fs.readFileSync('js/canvas/layer/composite-publication.js','utf8'),c);
for(const [name,end] of [
    ['recompositeFromLayers','// ═══ LAYER PANEL'],
    ['buildLivePaintCompositeCanvas','window.buildLivePaintCompositeCanvas'],
    ['_encodedPngForCanvas','window._spbEncodedPngForCanvas'],
    ['undoLayerEdit','window.undoLayerEdit'],
    ['redoLayerEdit','window.redoLayerEdit'],
    ['_pushLayerUndo','// Snapshot the entire layer stack'],
    ['_restorePixelHistoryEntry','function pushPixelUndo']
]) vm.runInContext(extract(name,end),c);
const exported=()=>c.buildLivePaintCompositeCanvas().toDataURL();
assert.equal(exported(),'png:90');
assert.equal(c._encodedPngForCanvas(c.buildLivePaintCompositeCanvas()),'png:90');
const count=[compositions,encodes];
assert.equal(c._encodedPngForCanvas(c.buildLivePaintCompositeCanvas()),'png:90');
assert.deepEqual([compositions,encodes],count,'unchanged paint must reuse both caches');
const originalDrawable=c._layerUndoStack[0].imgCanvas, editedDrawable=c._psdLayers[0].img;
assert.equal(c.undoLayerEdit(),true);
assert.equal(c._psdLayers[0].img,originalDrawable,'Undo restores the exact original drawable');
assert.equal(c._layerRedoStack[0].imgCanvas,editedDrawable,'Redo snapshot must not rasterize the source again');
assert.equal(exported(),'png:120','Undo must immediately export restored pixels');
assert.equal(pc.pixel,120,'Undo SOURCE must equal the committed/export pixels');
const afterUndoCompositions=compositions;
exported();
assert.equal(compositions,afterUndoCompositions,'reuse the published composite for export');
assert.equal(c.preview,'png:120','Undo preview must invalidate PNG memo before requesting a render');
assert.equal(c.redoLayerEdit(),true);
assert.equal(c._psdLayers[0].img,editedDrawable,'Redo restores the exact edited drawable');
assert.equal(exported(),'png:90'); assert.equal(c.preview,'png:90');
assert.equal(pc.pixel,90,'Redo SOURCE must equal the committed/export pixels');
// Repeated slider/effects edits can share one undo entry. Publication, rather
// than history-stack growth, must invalidate their cached paint too.
c._psdLayers[0].img=canvas(75); c.recompositeFromLayers({readback:false});
assert.equal(exported(),'png:75');
assert.equal(c._encodedPngForCanvas(c.buildLivePaintCompositeCanvas()),'png:75');
// Flat document Undo has no layer recomposite path.
c._psdLayersLoaded=false;
assert(c._restorePixelHistoryEntry({data:new Uint8ClampedArray([44,0,0,255]),width:1,height:1}));
assert.equal(c.preview,'png:44'); assert.equal(exported(),'png:44');
c._pushLayerUndo(c._psdLayers[0],'reference proof');
assert.equal(c._layerUndoStack.at(-1).imgCanvas,c._psdLayers[0].img,'First snapshot must retain source identity');
console.log('Paint cache history: immediate Undo/Redo, preview, repeated edits, flat restore and cache reuse pass.');
