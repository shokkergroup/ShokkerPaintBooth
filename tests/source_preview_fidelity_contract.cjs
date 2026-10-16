// Owner 2026-10-14: retain car artwork, align coverage and never resample on zoom.
// Runs the installed functions, not copies. Native visual checks are separate.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const render = read('paint-booth-5-api-render.js');
const block = render.slice(render.indexOf('function _nuqOff()'), render.indexOf('async function doRender()'));
const folder = 'Turn Off Before Exporting TGA';
const layers = ['Base Paint', 'Car Mandatory', 'Headlight Artwork', 'Wire', 'Mask', 'Number Blocks', 'Sponsor Blocks'].map((name, id) => ({id, name, groupName: id ? folder : 'Paintable Area', img: {}, visible: true}));
const live = {width: 2048, height: 2048};
let drawn = [], overrides = [];
const ctx = {
    window: {buildLivePaintCompositeCanvas: () => live}, localStorage: {getItem: () => null},
    document: {getElementById: () => live, createElement: () => ({getContext: () => ({})})},
    _psdLayersLoaded: true, _psdLayers: layers, performance: {now: () => 1000}, console: {log() {}, warn() {}},
    _activeLayerCanvas: null, getSelectedLayer: () => layers[1],
    _spbCompositeLayerStack: (_, stack, options) => {
        drawn = stack.filter(l => l.visible !== false && options.includeLayer(l)).map(l => l.name);
        overrides = stack.map(l => options.sourceOverrideFor(l));
        return {ok: true};
    }
};
vm.createContext(ctx); vm.runInContext(block, ctx);
for (const name of ['Wire','Wireframe','UV Wire','Mask','Number Blocks','Sponsor Blocks']) {
    assert.equal(ctx._nuqIsGuideLayer({name, groupName:folder}), true, name);
    assert.equal(ctx._nuqIsGuideLayer({name, groupName:'My Artwork'}), false, 'ordinary artwork: '+name);
}
for (const name of ['Car Mandatory','Headlights','Grille','Taillights','Unknown art','Wire logo']) {
    assert.equal(ctx._nuqIsGuideLayer({name, groupName:folder}), false, 'preserve '+name);
}
assert.equal(ctx._nuqIsGuideLayer({path:folder+'/Wire'}), true);
assert.equal(ctx._nuqIsGuideLayer({name:'Mask',groupChain:[{name:folder}]}), true);
const before = JSON.stringify(layers);
for (const fn of ['_nuqRenderComposite','_nuqPreviewComposite']) {
    const result = ctx[fn]();
    assert.deepEqual(drawn, ['Base Paint','Car Mandatory','Headlight Artwork'], fn);
    assert.equal(result.width, 2048); assert.equal(result.height, 2048);
}
assert.equal(JSON.stringify(layers), before, 'composites must not toggle source eyes');
layers[1].visible = false; ctx._nuqPreviewComposite();
assert(!drawn.includes('Car Mandatory'), 'explicit eye-off still respected');
layers[1].visible = true;
ctx._activeLayerCanvas = {activeEdit: true}; ctx._nuqPreviewComposite();
assert.equal(overrides[1], ctx._activeLayerCanvas, 'active car-art edit included');
ctx.window.SPB_NUQ_OFF = true;
assert.equal(ctx._nuqRenderComposite(), live); assert.equal(ctx._nuqPreviewComposite(), live);

// No backing-size assignments, redraws or resampling are allowed during view zoom.
function nativeCanvas() {
    const c = {style: {}};
    for (const key of ['width','height']) Object.defineProperty(c,key,{get:()=>2048,set:()=>{throw Error('Zoom changed native '+key);}});
    c.getContext = () => {throw Error('Zoom touched source pixels');};
    return c;
}
const nodes = {paintCanvas:nativeCanvas(),regionCanvas:nativeCanvas(),canvasInner:{style:{}},canvasViewport:{style:{}},zoomLevel:{},splitViewContainer:{}};
const zoomCtx = {document:{getElementById:id=>nodes[id]||null},window:{}, currentZoom:1,
    getScrollContainer:()=>({clientWidth:560,clientHeight:560}),_updateViewTransform(){},_pinUnifiedPreviewViewport(){},spaceHeld:false,isPanning:false,canvasMode:'eyedropper'};
vm.createContext(zoomCtx);
const canvasSource = read('paint-booth-3-canvas.js');
const begin = canvasSource.indexOf('        function applyZoom() {');
const end = canvasSource.indexOf('\n        }', begin) + 10;
vm.runInContext(canvasSource.slice(begin,end),zoomCtx);
for (let cycle=0;cycle<20;cycle++) for (const z of [0.17,0.26,0.64,1,2,8,32,1,0.26]) {
    zoomCtx.currentZoom=z;zoomCtx.applyZoom();
    const w=Math.round(2048*z)+'px';
    assert.equal(nodes.paintCanvas.style.width,w);
    assert.equal(nodes.canvasInner.style.width,w);
    assert.equal(nodes.regionCanvas.style.width,w);
    assert.equal(nodes.paintCanvas.style.imageRendering,z>=1?'pixelated':'auto');
}
// Runtime + packaging must receive the exact files tested here.
for (const name of ['paint-booth-3-canvas.js','paint-booth-5-api-render.js','paint-booth-2-state-zones.js','paint-booth-v2.html','css/ui-modernization-20260510-early.css','js/canvas/pc-zoneclip.js']) {
    assert.equal(read(name),read('electron-app/server/'+name),'mirror drift: '+name);
}
console.log('PASS: guide/art policy; render/preview parity; eye and active-edit safety; 180 native-preserving zoom transitions; runtime mirror parity.');
