const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const api = require('../js/canvas/render-source-readiness.js');
const pixels = {width: 2, height: 2, data: new Uint8ClampedArray(16)};
assert(api.reasonFor({loading: true, pixels}).includes('still loading'));
assert(api.reasonFor({pixels: null}));
assert(api.reasonFor({pixels: {...pixels, data: new Uint8Array(12)}}));
assert(api.reasonFor({pixels, canvas: {width: 300, height: 150}}));
assert.equal(api.reasonFor({pixels, canvas: {width: 2, height: 2}}), '');

let terminate = false;
const button = {disabled: false, innerHTML: '<b>RENDER</b>', title: 'Render spec map',
    classList: {contains: () => terminate}};
const ctx = {window: {_spbPsdImportInFlight: true}, paintImageData: pixels,
    document: {getElementById: id => id === 'btnRender' ? button : {width: 2, height: 2}},
    showToast: message => { ctx.message = message; }};
vm.createContext(ctx);
let previewRetries = 0;
ctx.window.spbKickLivePreview = () => { previewRetries++; };
vm.runInContext(fs.readFileSync('js/canvas/render-source-readiness.js', 'utf8'), ctx);
const live = ctx.window.SPBRenderReadiness;
live.refresh();
assert.equal(button.disabled, true);
assert.equal(button.textContent, 'LOADING PAINT…');
live.refresh(); // repeated refresh must not replace the original button state
ctx.window._spbPsdImportInFlight = false;
live.refresh();
assert.equal(button.disabled, false);
assert.equal(button.innerHTML, '<b>RENDER</b>');
assert.equal(button.title, 'Render spec map');
assert.equal(previewRetries, 1);
live.refresh();
assert.equal(previewRetries, 1, 'ready refresh does not repeatedly enqueue previews');
ctx.window._spbPsdImportInFlight = true;
terminate = true;
live.refresh();
assert.equal(button.disabled, false, 'existing cancel action stays available');
terminate = false;

// Execute the actual command front door, not a duplicate of its guard.
const renderSource = fs.readFileSync('paint-booth-5-api-render.js', 'utf8');
const start = renderSource.indexOf('async function doRender() {');
const end = renderSource.indexOf('    // [SPB DOUBLE-RENDER', start);
assert(end > start);
vm.runInContext(renderSource.slice(start, end) + '\nwindow.started = true;\n}', ctx);
(async () => {
    await ctx.doRender();
    assert.equal(ctx.window.started, undefined);
    assert(ctx.message.includes('still loading'));
    ctx.window._spbPsdImportInFlight = false;
    ctx.paintImageData = null;
    await ctx.doRender();
    assert.equal(ctx.window.started, undefined, 'failed initial import cannot render a placeholder');
    ctx.paintImageData = pixels;
    await ctx.doRender();
    assert.equal(ctx.window.started, true);
    const canvas = fs.readFileSync('paint-booth-3-canvas.js', 'utf8').replace(/\r\n/g, '\n');
    const importStart = canvas.indexOf('async function _doPSDImport(psdPath, importOptions)');
    const importer = canvas.slice(importStart, canvas.indexOf('function countLayers(layers)', importStart));
    assert(importer.includes('_spbPsdImportInFlight = true;\n    if (window.SPBRenderReadiness) window.SPBRenderReadiness.refresh();'));
    assert(importer.includes('_spbPsdImportInFlight = window._spbPsdImportCount > 0;\n        if (window.SPBRenderReadiness) window.SPBRenderReadiness.refresh();'));
    const previewStart = canvas.indexOf('async function doPreviewRender(zoneHash, previewScale, options) {');
    const previewEnd = canvas.indexOf('            const opts = options || {};', previewStart);
    assert(previewEnd > previewStart);
    vm.runInContext(canvas.slice(previewStart, previewEnd) + '\nwindow.previewStarted = true;\n}', ctx);
    ctx.window._spbPsdImportInFlight = true;
    await ctx.doPreviewRender();
    assert.equal(ctx.window.previewStarted, undefined);
    ctx.window._spbPsdImportInFlight = false;
    await ctx.doPreviewRender();
    assert.equal(ctx.window.previewStarted, true);
    console.log('Render readiness: loading/empty/stale pixels blocked, published pixels admitted, actual command guard and button/cancel lifecycle pass.');
})().catch(error => { console.error(error); process.exitCode = 1; });
