'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const commit = require('../js/canvas/source-file-commit.js').run;
const transition = require('../js/canvas/zone/source-mask-transition.js');
const geometry = require('../js/canvas/zone/canvas-mask-geometry.js');

function harness(failAt) {
    const calls = [];
    const pixels = Uint8ClampedArray.from({ length: 16 }, (_, i) => i * 10);
    const initialMask = Uint8Array.from([0, 64, 128, 255]);
    const initialLayer = { name: 'Original', pixels: pixels.slice() };
    let state = { pixels, zones: [{ regionMask: initialMask }], undo: [{ prevMask: initialMask }], redo: [], layer: initialLayer };
    function step(label) { calls.push(label); if (failAt === label) throw Error('synthetic ' + label); }
    const ctx = { getImageData() { step('readback'); return { data: state.pixels.slice() }; } };
    const canvas = { width: 2, height: 2, getContext() { return ctx; } };
    const deps = {
        canvas,
        settle() { step('settle'); },
        capture() { step('capture'); return { state, width: canvas.width, height: canvas.height }; },
        resizeMasks(ow, oh, w, h) {
            step('masks');
            state = Object.assign({}, state, transition.stage(state, ow, oh, w, h, geometry, {}));
        },
        publish(data) { step('publish'); state.pixels = data.data; },
        clearPSD() { state.layer = null; step('clearPSD'); },
        restore(previous) { step('restore'); state = previous.state; canvas.width = previous.width; canvas.height = previous.height; }
    };
    return { deps, calls, initialMask, initialLayer, initialPixels: pixels.slice(), state: () => state,
        draw() { step('draw'); state.pixels = new Uint8ClampedArray(64).fill(77); } };
}
for (const fault of ['masks', 'draw', 'readback', 'publish', 'clearPSD']) {
    const h = harness(fault);
    assert.throws(() => commit(h.deps, 4, 4, h.draw), new RegExp(fault));
    assert.deepEqual(h.state().pixels, h.initialPixels);
    assert.strictEqual(h.state().zones[0].regionMask, h.initialMask);
    assert.strictEqual(h.state().undo[0].prevMask, h.initialMask);
    assert.strictEqual(h.state().layer, h.initialLayer);
    assert.deepEqual([h.deps.canvas.width, h.deps.canvas.height], [2, 2]);
    assert.equal(h.calls.at(-1), 'restore');
}
for (const keepLayers of [false, true]) {
    const h = harness();
    commit(h.deps, 4, 4, h.draw, !keepLayers);
    assert.equal(h.state().zones[0].regionMask.length, 16);
    assert.equal(h.state().undo[0].prevMask.length, 16);
    assert(h.state().pixels.every(v => v === 77));
    assert.strictEqual(h.state().layer, keepLayers ? h.initialLayer : null);
    assert(h.calls.indexOf('publish') > h.calls.indexOf('draw'));
    if (!keepLayers) assert(h.calls.indexOf('clearPSD') > h.calls.indexOf('publish'));
}

// Execute the actual decoded-TGA entry point and application facade, including
// publication failure. UI methods are inert; actual mask/commit modules run.
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const generation = source.slice(source.indexOf('var _spbSourceLoadGeneration = 0;'), source.indexOf('async function _spbFingerprintBytes('));
const dataSource = fs.readFileSync('paint-booth-1-data.js', 'utf8');
const facade = source.slice(source.indexOf('function _spbCommitSourceFile('), source.indexOf('function _spbTransitionSourceMasks('));
const decoded = dataSource.slice(dataSource.indexOf('function loadDecodedImageToCanvas('), dataSource.indexOf('// =============================================================================', dataSource.indexOf('function loadDecodedImageToCanvas(')));
for (const fault of [undefined, 'draw']) {
    const h = harness(fault);
    const elements = new Map();
    h.deps.canvas.getContext().putImageData = () => h.draw();
    const context = {
        window: { SPBSourceFileCommit: { run: commit } },
        document: { getElementById(id) { if (id === 'paintCanvas') return h.deps.canvas; if (!elements.has(id)) elements.set(id, { style: {}, value: '' }); return elements.get(id); } },
        _settleActiveLayerStrokeBeforeTargetChange: h.deps.settle,
        _spbCaptureSourceDocumentState: h.deps.capture,
        _spbRestoreSourceDocumentState: h.deps.restore,
        _spbTransitionSourceMasks: h.deps.resizeMasks,
        clearPSDDocumentState: h.deps.clearPSD,
        setupCanvasHandlers() {}, canvasZoom() {}, showToast() {},
        ImageData: class { constructor(data, width, height) { Object.assign(this, { data, width, height }); } }
    };
    vm.createContext(context);
    vm.runInContext(facade + decoded, context);
    if (fault) {
        assert.throws(() => context.loadDecodedImageToCanvas(4, 4, new Uint8ClampedArray(64), 'test.tga'), /synthetic draw/);
        assert.strictEqual(h.state().layer, h.initialLayer);
        assert.strictEqual(h.state().zones[0].regionMask, h.initialMask);
    } else {
        context.loadDecodedImageToCanvas(4, 4, new Uint8ClampedArray(64), 'test.tga');
        assert.equal(context.paintImageData.data.length, 64);
        assert.equal(h.state().zones[0].regionMask.length, 16);
    }
}
for (const name of ['browsePaintFile(input)', 'loadPaintImage(input)', 'loadPaintImageFromFile(file)', 'loadPaintImageFromFileAsync(file, sourceTransaction)']) {
    const a = source.indexOf('        function ' + name);
    const end = source.indexOf('\n        function ', a + 20);
    const body = source.slice(a, end);
    assert(body.includes('_spbCommitSourceFile(img.width, img.height,'), name);
    assert(!body.includes('clearPSDDocumentState('), name + ': premature Layer cleanup');
    assert(body.indexOf('loadDecodedImageToCanvas(') < body.indexOf("markFlatPaintLiveSource(file,"), name + ': premature source identity');
}
async function checkFileCallbacks() {
    let cases = 0;
    for (const name of ['browsePaintFile', 'loadPaintImage', 'loadPaintImageFromFile', 'loadPaintImageFromFileAsync']) {
        for (const extension of ['png', 'tga']) {
            for (const fault of [undefined, 'draw']) {
                const h = harness(fault);
                let marked = false;
                const toasts = [];
                const element = { style: {}, value: '', files: [] };
                h.deps.canvas.getContext().putImageData = h.draw;
                h.deps.canvas.getContext().drawImage = h.draw;
                const context = {
                    window: { SPBSourceFileCommit: { run: commit } },
                    document: { getElementById(id) { return id === 'paintCanvas' ? h.deps.canvas : element; } },
                    _settleActiveLayerStrokeBeforeTargetChange: h.deps.settle,
                    _spbCaptureSourceDocumentState: h.deps.capture,
                    _spbRestoreSourceDocumentState: h.deps.restore,
                    _spbTransitionSourceMasks: h.deps.resizeMasks,
                    clearPSDDocumentState: h.deps.clearPSD,
                    setupCanvasHandlers() {}, canvasZoom() {}, validatePaintPath() {},
                    showToast(message, error) { toasts.push({ message, error }); },
                    markFlatPaintLiveSource() { marked = true; }, clearFlatPaintLiveSource() {},
                    setTimeout() {}, splitViewActive: true,
                    ImageData: class { constructor(data, width, height) { Object.assign(this, { data, width, height }); } },
                    decodeTGA() { return { width: 4, height: 4, rgba: new Uint8ClampedArray(64).fill(77) }; },
                    FileReader: class {
                        readAsDataURL() { this.onload({ target: { result: 'decoded-fixture' } }); }
                        readAsArrayBuffer() { this.onload({ target: { result: new ArrayBuffer(64) } }); }
                    },
                    Image: class { constructor() { this.width = 4; this.height = 4; } set src(value) { this.onload(); } }
                };
                const start = source.indexOf('        function ' + name + '(');
                const end = source.indexOf('\n        function ', start + 20);
                vm.createContext(context);
                vm.runInContext(generation + facade + decoded + source.slice(start, end), context);
                const file = { name: 'fixture.' + extension };
                const argument = ['browsePaintFile', 'loadPaintImage'].includes(name) ? { files: [file] } : file;
                let rejected = false;
                try { await context[name](argument); } catch (error) { rejected = true; assert(fault, error.message); }
                if (fault) {
                    assert.strictEqual(h.state().layer, h.initialLayer, name);
                    assert.strictEqual(h.state().zones[0].regionMask, h.initialMask, name);
                    assert(!marked, name + ': failed pixels cannot publish live-source identity');
                    assert(rejected || toasts.some(t => t.error), name + ': failure must be visible');
                } else {
                    assert.equal(context.paintImageData.data.length, 64, name);
                    assert.equal(h.state().zones[0].regionMask.length, 16, name);
                    assert.equal(h.state().undo[0].prevMask.length, 16, name);
                    assert(marked, name);
                }
                cases++;
            }
        }
    }
    console.log(`Direct source commit: ${cases} actual PNG/TGA file callbacks, five injected transaction failures, decoded publication and preserve-Layers option pass.`);
}
checkFileCallbacks().catch(error => { console.error(error); process.exitCode = 1; });
