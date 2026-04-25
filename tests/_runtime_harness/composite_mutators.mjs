// Runtime harness for the composite-mutator family TF1-TF5:
//   autoLevels / autoContrast / desaturateCanvas / invertCanvasColors / posterize
//
// What this proves:
//   - Locked-layer-selected ⇒ refuses with error toast, no mutation, no undo push.
//   - Editable-layer-selected ⇒ routes through layer (pushes layer undo, inits
//     layer canvas, mutates layer pixels, commits layer paint), does NOT push
//     pixel undo, does NOT trigger composite preview refresh.
//   - No layer selected ⇒ falls back to composite path (pushes pixel undo,
//     mutates composite paintImageData, fires triggerPreviewRender).
//
// We extract the function bodies textually from paint-booth-3-canvas.js (these
// are top-level functions, not inside an IIFE), then evaluate each in a fresh
// V8 context with stubbed helpers. The harness wires _initLayerPaintCanvas to
// actually swap the paintImageData binding so the mutation operates on a
// distinct layer pixel buffer — letting us prove the data divergence is
// resolved (composite stays untouched when a layer is the target).

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-3-canvas.js'), 'utf8');

function extractTopLevelFunction(name) {
    const needle = '\nfunction ' + name + '(';
    const start = SRC.indexOf(needle) + 1; // skip the leading newline
    if (start === 0) throw new Error('Could not locate top-level function ' + name);
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    return SRC.slice(start, i + 1);
}

// Build a fake ImageData-like buffer for testing. Real ImageData would come
// from canvas.getContext('2d').getImageData; here we just use a typed array
// wrapped in a tiny object so length math works.
//
// Pass an [R, G, B, A] tuple to fill each pixel with distinct channels — this
// is critical for desaturate testing (a grayscale input desaturates to itself
// so you can't observe the mutation).
function fakeImageData(w, h, rgba) {
    const data = new Uint8ClampedArray(w * h * 4);
    if (Array.isArray(rgba)) {
        for (let i = 0; i < data.length; i += 4) {
            data[i] = rgba[0]; data[i+1] = rgba[1];
            data[i+2] = rgba[2]; data[i+3] = rgba[3];
        }
    } else if (rgba !== undefined) {
        data.fill(rgba);
    }
    return { data, width: w, height: h };
}

function makeContext({ scenario, layerLocked = false }) {
    const W = 4, H = 4; // small image so mutation is observable

    // Use distinct R/G/B per buffer so any per-channel mutation is detectable.
    // Composite: warm orange-ish, layer: cool teal-ish — makes desaturate observable.
    const compositeData = fakeImageData(W, H, [200, 50, 100, 255]);
    const layerData     = fakeImageData(W, H, [50, 180, 220, 255]);

    const calls = {
        showToast: [],
        pushPixelUndo: [],
        _pushLayerUndo: [],
        _initLayerPaintCanvas: 0,
        _commitLayerPaint: 0,
        triggerPreviewRender: 0,
    };

    // The function under test will read & write `paintImageData`. We start it
    // as the composite buffer; if the function calls _initLayerPaintCanvas we
    // swap it to the layer buffer (mirroring real behavior at line 12600).
    const ctx = {
        // module-scoped state used by the function
        paintImageData: compositeData,
        _activeLayerCanvas: null,
        _activeLayerCtx: null,
        _savedPaintImageData: null,

        // helpers
        document: {
            getElementById: function (id) {
                if (id === 'paintCanvas') {
                    return {
                        width: W,
                        height: H,
                        getContext: function () {
                            return {
                                putImageData: function (data) {
                                    // Real putImageData paints to the canvas;
                                    // we just record that the function called it.
                                },
                            };
                        },
                    };
                }
                return null;
            },
        },

        showToast: function (msg, isError) { calls.showToast.push([msg, !!isError]); },
        pushPixelUndo: function (label) { calls.pushPixelUndo.push(label); },
        triggerPreviewRender: function () { calls.triggerPreviewRender++; },

        // layer-paint helpers
        getSelectedEditableLayer: function () {
            if (scenario === 'composite') return null;
            if (scenario === 'locked') return null;  // locked path returns null per real impl
            return { id: 'L1', img: { width: W, height: H }, locked: false, bbox: [0, 0, W, H] };
        },
        isSelectedLayerLocked: function () { return scenario === 'locked'; },
        _pushLayerUndo: function (layer, label) {
            calls._pushLayerUndo.push([layer && layer.id, label]);
        },
        _initLayerPaintCanvas: function () {
            calls._initLayerPaintCanvas++;
            // Mirror real behavior: swap paintImageData → layer pixels
            ctx._savedPaintImageData = ctx.paintImageData;
            ctx.paintImageData = layerData;
            ctx._activeLayerCanvas = { width: W, height: H }; // truthy
            ctx._activeLayerCtx = { putImageData: function () {} };
            return true;
        },
        _commitLayerPaint: function () {
            calls._commitLayerPaint++;
            // Restore composite binding
            if (ctx._savedPaintImageData) {
                ctx.paintImageData = ctx._savedPaintImageData;
                ctx._savedPaintImageData = null;
            }
            ctx._activeLayerCanvas = null;
            ctx._activeLayerCtx = null;
        },
        _flushPaintImageDataToCurrentSurface: function () {
            if (ctx._activeLayerCanvas && ctx._activeLayerCtx && typeof ctx._activeLayerCtx.putImageData === 'function') {
                ctx._activeLayerCtx.putImageData(ctx.paintImageData, 0, 0);
            }
            const pc = ctx.document.getElementById('paintCanvas');
            if (pc) pc.getContext('2d').putImageData(ctx.paintImageData, 0, 0);
        },
    };

    ctx._calls = calls;
    ctx._compositeData = compositeData;
    ctx._layerData = layerData;
    return ctx;
}

function snapshotPixels(d) {
    // Sample first 4 pixels (16 bytes) — enough to detect any mutation.
    return Array.from(d.slice(0, 16));
}

function runOne(funcName, scenario) {
    const ctx = makeContext({ scenario });
    const compositeBefore = snapshotPixels(ctx._compositeData.data);
    const layerBefore = snapshotPixels(ctx._layerData.data);

    const body = extractTopLevelFunction(funcName);
    // Build a one-shot script: define function body in this context, then call it.
    const script = body + '\n;' + funcName + '(' + (funcName === 'posterize' ? '4' : '') + ');';
    let error = null;
    try {
        vm.createContext(ctx);
        vm.runInContext(script, ctx, { filename: funcName + '.runtime.js', timeout: 2000 });
    } catch (e) {
        error = { message: e.message, stack: e.stack };
    }

    const compositeAfter = snapshotPixels(ctx._compositeData.data);
    const layerAfter = snapshotPixels(ctx._layerData.data);

    return {
        func: funcName,
        scenario,
        ok: error === null,
        error,
        showToast: ctx._calls.showToast,
        pushPixelUndo: ctx._calls.pushPixelUndo,
        _pushLayerUndo: ctx._calls._pushLayerUndo,
        _initLayerPaintCanvas_count: ctx._calls._initLayerPaintCanvas,
        _commitLayerPaint_count: ctx._calls._commitLayerPaint,
        triggerPreviewRender_count: ctx._calls.triggerPreviewRender,
        composite_mutated: JSON.stringify(compositeBefore) !== JSON.stringify(compositeAfter),
        layer_mutated: JSON.stringify(layerBefore) !== JSON.stringify(layerAfter),
        composite_before: compositeBefore.slice(0, 4),
        composite_after: compositeAfter.slice(0, 4),
        layer_before: layerBefore.slice(0, 4),
        layer_after: layerAfter.slice(0, 4),
    };
}

const FUNCS = ['autoLevels', 'autoContrast', 'desaturateCanvas', 'invertCanvasColors', 'posterize'];
const SCENARIOS = ['composite', 'editable_layer', 'locked'];

const results = {};
for (const f of FUNCS) {
    results[f] = {};
    for (const s of SCENARIOS) {
        results[f][s] = runOne(f, s);
    }
}

console.log(JSON.stringify(results, null, 2));
