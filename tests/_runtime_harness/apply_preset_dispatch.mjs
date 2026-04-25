// HEENAN 5H OVERNIGHT — iter 1 runtime proof for the applyPreset fix.
//
// Pre-fix state: paint-booth-2-state-zones.js defined `applyPreset` twice.
// The ID-form at ~line 8801 was shadowed by the object-form at ~line 9598
// (JS function-declaration hoisting). Gallery clicks sending a string ID
// were dispatched into the object-form function, which threw TypeError on
// `preset.zones.map(...)`. The preset gallery was silently broken.
//
// Post-fix: a single polymorphic `applyPreset(arg)` dispatcher routes by
// typeof arg to one of two internal helpers:
//   - _applyPresetById(presetId)     for gallery cards
//   - _applyPresetFromObject(preset) for .shokker file imports
// Additionally, _applyPresetFromObject now uses `??` (nullish coalesce)
// instead of `||` for numeric/boolean persistence fields so values like
// `pickerTolerance: 0` round-trip faithfully.
//
// This harness executes the actual source by extracting just the preset
// dispatch block plus its dependencies, running it in a stubbed sandbox,
// and driving behavioural assertions. Output is JSON for the pytest
// harness to consume.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

// --- Extract the preset dispatcher + helpers from the live source ---
// We grab from the `// ===== PRESETS =====` marker through the end of
// _applyPresetById (the short helper), then separately grab the
// _applyPresetFromObject body so we can isolate the two codepaths.
function sliceBetween(src, startMarker, endMarker, fromIdx = 0) {
    const s = src.indexOf(startMarker, fromIdx);
    if (s === -1) throw new Error('start marker not found: ' + startMarker);
    const e = src.indexOf(endMarker, s);
    if (e === -1) throw new Error('end marker not found: ' + endMarker);
    return { body: src.slice(s, e), end: e };
}

// Dispatcher + _applyPresetById live between the "===== PRESETS =====" banner
// and the "===== TOAST =====" banner.
const presetBlock = sliceBetween(STATE_SRC, '// ===== PRESETS =====', '// ===== TOAST =====').body;

// _applyPresetFromObject is a standalone top-level function. Grab it from
// its name to the closing brace before the next `function ` at column 0.
function extractTopLevelFunction(src, funcName) {
    const needle = `function ${funcName}(`;
    const start = src.indexOf(needle);
    if (start === -1) throw new Error('function not found: ' + funcName);
    // Walk to find matching closing brace at the same indent level.
    let depth = 0;
    let inFunc = false;
    for (let i = start; i < src.length; i++) {
        const c = src[i];
        if (c === '{') { depth += 1; inFunc = true; }
        else if (c === '}') {
            depth -= 1;
            if (inFunc && depth === 0) {
                return src.slice(start, i + 1);
            }
        }
    }
    throw new Error('unbalanced braces in ' + funcName);
}
const applyFromObjectFn = extractTopLevelFunction(STATE_SRC, '_applyPresetFromObject');

// --- Build the sandbox with stubs for every referenced global ---
let toastCaptured = [];
let renderZonesCalls = 0;
let triggerPreviewRenderCalls = 0;
let autoSaveCalls = 0;
let renderCount = 0;
let confirmReturn = true;

const ctx = {
    // DOM stubs
    document: {
        getElementById: () => null,
        createElement: () => ({ click: () => {}, addEventListener: () => {} }),
    },
    window: {},
    confirm: (_msg) => confirmReturn,
    alert: () => {},
    console: { log: () => {}, warn: (...a) => { ctx._consoleWarn.push(a); }, error: () => {} },
    _consoleWarn: [],

    // SPB globals referenced by the helpers
    zones: [],
    selectedZoneIndex: 0,
    PRESETS: {
        // Minimal realistic built-in preset used by the gallery path.
        my_test_preset: {
            name: 'Test Preset',
            zones: [
                { name: 'Zone A', color: null, base: 'gloss', pattern: 'none',
                  finish: null, intensity: '100' },
                { name: 'Zone B', color: 'dark', base: 'matte', pattern: 'carbon_fiber',
                  finish: null, intensity: '80' },
            ],
        },
    },
    SPECIAL_COLORS: [{ value: 'dark' }],
    QUICK_COLORS: [],
    _newZoneId: (() => { let n = 0; return () => `id-${++n}`; })(),
    renderZones: () => { renderZonesCalls += 1; },
    triggerPreviewRender: () => { triggerPreviewRenderCalls += 1; },
    autoSave: () => { autoSaveCalls += 1; },
    showToast: (msg) => { toastCaptured.push(msg); },
    updateWearDisplay: () => {},
    toggleNightBoostSlider: () => {},
    parseFloat: parseFloat,

    // Needed by _applyPresetFromObject's spread
    Array: Array,
    Object: Object,
};
vm.createContext(ctx);

// Load the _applyPresetFromObject helper FIRST so the dispatcher can see it.
vm.runInContext(applyFromObjectFn, ctx, { filename: 'apply_preset_object.runtime.js' });
vm.runInContext(presetBlock, ctx, { filename: 'apply_preset_dispatch.runtime.js' });

// --- Drive the behavioural assertions ---
const results = {};

// A. Gallery path: applyPreset('my_test_preset') must load zones.
try {
    ctx.zones = [];
    ctx.applyPreset('my_test_preset');
    results.gallery_loads_zones = ctx.zones.length;  // expect 2
    results.gallery_zone_names = ctx.zones.map(z => z.name);
    results.gallery_throw = null;
} catch (e) {
    results.gallery_throw = String(e);
}

// B. Gallery path: unknown id must be a silent no-op (no throw).
try {
    ctx.zones = [{ name: 'existing' }];  // should remain untouched
    ctx.applyPreset('nonexistent_preset_id');
    results.unknown_id_throw = null;
    results.unknown_id_zones_after = ctx.zones.length;  // expect 1 (unchanged)
} catch (e) {
    results.unknown_id_throw = String(e);
}

// C. Object path: applyPreset({zones:[...]}) must load zones.
try {
    ctx.zones = [];
    ctx.applyPreset({
        name: 'Imported',
        zones: [
            { name: 'Full Zone', base: 'gloss', pattern: 'none',
              pickerTolerance: 0,   // <-- key test: falsy but legitimate
              scale: 1.0,
              wear: 0,              // <-- key test: falsy, legitimate
              muted: false,         // <-- key test: falsy, legitimate
              intensity: '100',
            },
        ],
    });
    results.object_loads_zones = ctx.zones.length;
    const z = ctx.zones[0] || {};
    results.object_tolerance_preserved = z.pickerTolerance;  // expect 0
    results.object_wear_preserved = z.wear;                   // expect 0
    results.object_muted_preserved = z.muted;                 // expect false
    results.object_scale_preserved = z.scale;                 // expect 1.0
    results.object_throw = null;
} catch (e) {
    results.object_throw = String(e);
}

// D. Object path with empty zones array — still dispatches (object-shape check).
try {
    ctx.zones = [];
    ctx.applyPreset({ name: 'Empty', zones: [] });
    results.empty_object_throw = null;
} catch (e) {
    results.empty_object_throw = String(e);
}

// E. Undefined/null input — silent no-op.
try {
    ctx.applyPreset(undefined);
    ctx.applyPreset(null);
    results.null_undefined_throw = null;
    results.null_undefined_warn_count = ctx._consoleWarn.length; // expect ≥2
} catch (e) {
    results.null_undefined_throw = String(e);
}

// F. Integer input (nonsense) — silent no-op, not a crash.
try {
    ctx.applyPreset(42);
    results.int_throw = null;
} catch (e) {
    results.int_throw = String(e);
}

// G. Regression check: confirm the pre-fix bug would have manifested.
// We simulate the old shadow behavior — the object-form was being called
// with a STRING. Without the dispatcher, we should observe a crash on
// `preset.zones.map` when given a string. This proves the bug was real.
try {
    // Call the internal object-form directly with a bad shape (bypass dispatcher).
    ctx._applyPresetFromObject('my_test_preset');
    results.prefix_sim_threw = false;
} catch (e) {
    results.prefix_sim_threw = true;
    results.prefix_sim_error = String(e);
}

console.log(JSON.stringify(results, null, 2));
