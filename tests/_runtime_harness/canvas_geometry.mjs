// Runtime harness for the canvas-geometry mutator family TF6-TF8:
//   flipCanvasH / flipCanvasV / rotateCanvas90
//
// Each is a destructive composite-only operation. With PSD layers loaded,
// recompositeFromLayers will overwrite the composite the next time it runs
// — silent data loss. The guard ships in this shift refuses the operation
// + toasts when PSD layers are loaded.
//
// Two scenarios per function:
//   no_layers ⇒ executes normally (mutates composite, fires preview)
//   psd_layers ⇒ refuses + error toast, no mutation, no undo push

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-3-canvas.js'), 'utf8');

function extractTopLevelFunction(name) {
    const needle = '\nfunction ' + name + '(';
    const start = SRC.indexOf(needle) + 1;
    if (start === 0) throw new Error('Could not locate function ' + name);
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    return SRC.slice(start, i + 1);
}

function fakeImageData(w, h) {
    const data = new Uint8ClampedArray(w * h * 4);
    for (let i = 0; i < data.length; i += 4) {
        data[i] = (i / 4) % 256; data[i+1] = 100; data[i+2] = 50; data[i+3] = 255;
    }
    return { data, width: w, height: h };
}

function makeContext({ psdLayersLoaded, psdLayerCount }) {
    const W = 4, H = 4;
    const calls = {
        showToast: [],
        pushPixelUndo: [],
        pushZoneUndo: [],
        triggerPreviewRender: 0,
    };
    const compositeData = fakeImageData(W, H);
    const ctx = {
        paintImageData: compositeData,
        document: {
            getElementById: function (id) {
                if (id === 'paintCanvas') {
                    return {
                        width: W, height: H,
                        getContext: function () {
                            return {
                                putImageData: function () {},
                                getImageData: function (x, y, w, h) { return fakeImageData(w, h); },
                                drawImage: function () {},
                                clearRect: function () {},
                                translate: function () {},
                                rotate: function () {},
                            };
                        },
                    };
                }
                if (id === 'regionCanvas') return { width: W, height: H };
                return null;
            },
            createElement: function () {
                return {
                    width: W, height: H,
                    getContext: function () {
                        return {
                            putImageData: function () {},
                            drawImage: function () {},
                        };
                    },
                };
            },
        },
        showToast: function (msg, isError) { calls.showToast.push([msg, !!isError]); },
        pushPixelUndo: function (label) { calls.pushPixelUndo.push(label); },
        pushZoneUndo: function (label) { calls.pushZoneUndo.push(label); },
        triggerPreviewRender: function () { calls.triggerPreviewRender++; },
        canvasZoom: function () {},
        _flushPaintImageDataToCurrentSurface: function () {
            const pc = ctx.document.getElementById('paintCanvas');
            if (pc) pc.getContext('2d').putImageData(ctx.paintImageData, 0, 0);
        },

        // PSD-layer state — the TF6-TF8 guards key on these
        _psdLayersLoaded: psdLayersLoaded,
        _psdLayers: Array.from({ length: psdLayerCount }, (_, i) => ({ id: 'L' + i })),

        zones: [],
    };
    ctx._calls = calls;
    return ctx;
}

function runOne(funcName, scenario) {
    const opts = scenario === 'psd_layers'
        ? { psdLayersLoaded: true, psdLayerCount: 3 }
        : { psdLayersLoaded: false, psdLayerCount: 0 };
    const ctx = makeContext(opts);
    const body = extractTopLevelFunction(funcName);
    const script = body + '\n;' + funcName + '();';
    let error = null;
    try {
        vm.createContext(ctx);
        vm.runInContext(script, ctx, { filename: funcName + '.runtime.js', timeout: 2000 });
    } catch (e) {
        error = { message: e.message };
    }
    return {
        func: funcName,
        scenario,
        ok: error === null,
        error,
        showToast: ctx._calls.showToast,
        pushPixelUndo: ctx._calls.pushPixelUndo,
        triggerPreviewRender_count: ctx._calls.triggerPreviewRender,
    };
}

const FUNCS = ['flipCanvasH', 'flipCanvasV', 'rotateCanvas90'];
const SCENARIOS = ['no_layers', 'psd_layers'];
const results = {};
for (const f of FUNCS) {
    results[f] = {};
    for (const s of SCENARIOS) {
        results[f][s] = runOne(f, s);
    }
}
console.log(JSON.stringify(results, null, 2));
