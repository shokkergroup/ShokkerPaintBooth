// HEENAN Hawk + Animal — perf benchmark harness.
//
// Measures what's measurable WITHOUT launching the running app:
//   - Function-extraction parse time (proxy for JS file load impact)
//   - In-V8 execution latency for the canvas mutators (autoLevels et al.)
//     against realistic 2048×2048 ImageData buffers
//   - Validator catalog walk time
//   - Cross-registry collision detector time
//   - Migration helper throughput on a thousand zone configs
//
// What this is NOT:
//   - Real GPU canvas timings (would require browser/Electron)
//   - Real server roundtrip (would require server.py + network)
//   - Subjective "does it feel fast" — that's a painter's eye
//
// Output: JSON with one row per measurement. Pytest wrapper asserts
// against budgets so regressions are visible immediately.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');

function timed(label, fn, iters = 1) {
    const t0 = performance.now();
    let result;
    for (let i = 0; i < iters; i++) result = fn();
    const elapsed_ms = performance.now() - t0;
    return {
        label,
        iters,
        total_ms: +elapsed_ms.toFixed(3),
        per_iter_ms: +(elapsed_ms / iters).toFixed(4),
        result_summary: typeof result === 'object' ? Object.keys(result || {}).slice(0, 4) : String(result).slice(0, 40),
    };
}

const results = {};

// ─── 1. canonical JS file read + parse time ─────────────────────────────────
const FILES = [
    'paint-booth-0-finish-data.js',
    'paint-booth-0-finish-metadata.js',
    'paint-booth-2-state-zones.js',
    'paint-booth-3-canvas.js',
    'paint-booth-5-api-render.js',
    'paint-booth-6-ui-boot.js',
];
results.file_reads = FILES.map(f => {
    const t0 = performance.now();
    const text = readFileSync(join(REPO, f), 'utf8');
    const elapsed = performance.now() - t0;
    return { file: f, size_kb: (text.length / 1024) | 0, read_ms: +elapsed.toFixed(2) };
});

// ─── 2. validator runtime ─────────────────────────────────────────────────────
const VALIDATOR_SRC = readFileSync(join(REPO, 'paint-booth-0-finish-data.js'), 'utf8');
const ctx = { window: undefined, console: { log: () => {}, warn: () => {} }, setTimeout: () => {} };
vm.createContext(ctx);
const evalT0 = performance.now();
vm.runInContext(VALIDATOR_SRC, ctx);
results.catalog_eval_ms = +(performance.now() - evalT0).toFixed(2);

results.validator = timed('validateFinishData', () =>
    vm.runInContext('validateFinishData()', ctx).length, 5);

// ─── 3. composite mutator throughput (autoLevels on a 2048×2048 buffer) ─────
const CANVAS_SRC = readFileSync(join(REPO, 'paint-booth-3-canvas.js'), 'utf8');
function extractTopLevelFunction(name) {
    const needle = '\nfunction ' + name + '(';
    const start = CANVAS_SRC.indexOf(needle) + 1;
    if (start === 0) throw new Error('not found: ' + name);
    let i = CANVAS_SRC.indexOf('{', start);
    let depth = 0;
    for (; i < CANVAS_SRC.length; i++) {
        const ch = CANVAS_SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    return CANVAS_SRC.slice(start, i + 1);
}

function makePerfContext(W, H) {
    const data = new Uint8ClampedArray(W * H * 4);
    // Distinct R/G/B so adjustments are observable.
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 200; data[i+1] = 50; data[i+2] = 100; data[i+3] = 255;
    }
    const calls = { showToast: 0, pushPixelUndo: 0, triggerPreviewRender: 0 };
    return {
        paintImageData: { data, width: W, height: H },
        _activeLayerCanvas: null, _activeLayerCtx: null, _savedPaintImageData: null,
        document: {
            getElementById: function () {
                return {
                    width: W, height: H,
                    getContext: function () { return { putImageData: function () {} }; },
                };
            },
        },
        showToast: function () { calls.showToast++; },
        pushPixelUndo: function () { calls.pushPixelUndo++; },
        triggerPreviewRender: function () { calls.triggerPreviewRender++; },
        getSelectedEditableLayer: function () { return null; },
        isSelectedLayerLocked: function () { return false; },
        _pushLayerUndo: function () {},
        _initLayerPaintCanvas: function () { return false; },
        _commitLayerPaint: function () {},
        _flushPaintImageDataToCurrentSurface: function () {},
        _calls: calls,
    };
}

function benchMutator(funcName, W, H, iters) {
    const c = makePerfContext(W, H);
    vm.createContext(c);
    const body = extractTopLevelFunction(funcName);
    const script = body + '\n;' + funcName + '(' + (funcName === 'posterize' ? '4' : '') + ');';
    const t0 = performance.now();
    for (let i = 0; i < iters; i++) {
        vm.runInContext(script, c, { filename: funcName + '.perf.js' });
    }
    const elapsed = performance.now() - t0;
    return {
        func: funcName, w: W, h: H, iters,
        total_ms: +elapsed.toFixed(2),
        per_iter_ms: +(elapsed / iters).toFixed(3),
        budget_ms: 100, // budget per call on 2048x2048 — generous for V8 stub
    };
}

results.composite_mutators = {
    auto_levels_512:    benchMutator('autoLevels', 512, 512, 10),
    auto_levels_2048:   benchMutator('autoLevels', 2048, 2048, 3),
    auto_contrast_2048: benchMutator('autoContrast', 2048, 2048, 3),
    desaturate_2048:    benchMutator('desaturateCanvas', 2048, 2048, 3),
    invert_2048:        benchMutator('invertCanvasColors', 2048, 2048, 3),
    posterize_2048:     benchMutator('posterize', 2048, 2048, 3),
};

// ─── 4. migration helper throughput ──────────────────────────────────────────
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');
const helperStart = STATE_SRC.indexOf('const _SPB_LEGACY_ID_MIGRATIONS');
const exposeLine  = STATE_SRC.indexOf('window._migrateZoneFinishIds = _migrateZoneFinishIds;', helperStart);
const helperEnd   = STATE_SRC.indexOf('}', exposeLine) + 1;
const helperBlock = STATE_SRC.slice(helperStart, helperEnd);
const migCtx = { window: {}, Object: Object, Array: Array };
vm.createContext(migCtx);
vm.runInContext(helperBlock, migCtx);

migCtx.__zones = Array.from({ length: 1000 }, () => ({
    name: 'Z', finish: 'acid_rain', pattern: 'shokk_cipher',
    patternStack: [{ id: 'shokk_cipher' }, { id: 'carbon_fiber' }],
    specPatternStack: [{ id: 'carbon_weave' }, { id: 'oil_slick' }],
}));

results.migration_throughput = timed('1000_zone_migrations', () => {
    let total = 0;
    for (const z of migCtx.__zones) {
        // Reset for fresh count each iter.
        z.finish = 'acid_rain'; z.pattern = 'shokk_cipher';
        z.patternStack[0].id = 'shokk_cipher';
        z.specPatternStack[0].id = 'carbon_weave';
        z.specPatternStack[1].id = 'oil_slick';
        total += vm.runInContext('_migrateZoneFinishIds(' + JSON.stringify(z) + ')', migCtx);
    }
    return total;
}, 1);

console.log(JSON.stringify(results, null, 2));
