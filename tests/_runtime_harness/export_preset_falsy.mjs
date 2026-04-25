// HEENAN 5H OVERNIGHT — iter 8 runtime proof for the exportPreset
// falsy-value preservation fix.
//
// Pre-fix state: paint-booth-2-state-zones.js::exportPreset mapped
// zone → preset-entry via `zones.map(z => ({ scale: z.scale || 1.0,
// rotation: z.rotation || 0, wear: z.wear || 0, muted: z.muted || false,
// ... }))`. A painter with a zone whose `scale: 0` (degenerate but
// legitimate) would have it silently promoted to 1.0 in the exported
// .shokker file, so recipients wouldn't get the author's intended
// setup.
//
// Post-fix: the same map now uses `??` for scale/rotation/wear/muted
// — matches the `loadConfigFromObj` / `_applyPresetFromObject`
// convention. Arrays (patternStack etc.) still use `||` because an
// empty array is legitimately equivalent to a missing field.
//
// This harness extracts the live mapping block from the source,
// runs it against a zone array where every falsy-legitimate field
// is the falsy value, and asserts all values round-trip.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

// Locate `function exportPreset` first, THEN the zones.map anchor
// within its body. The anchor string `zones: zones.map(z => ({` also
// appears inside loadConfigFromObj, so scoping matters.
const fnAnchor = 'function exportPreset(';
const fnStart = STATE_SRC.indexOf(fnAnchor);
if (fnStart < 0) {
    console.error('could not locate function exportPreset');
    process.exit(1);
}
const marker = 'zones: zones.map(z => ({';
const start = STATE_SRC.indexOf(marker, fnStart);
if (start < 0) {
    console.error('could not locate zones.map anchor inside exportPreset');
    process.exit(1);
}
// Balance parens from the `(` of `.map(`. The `lastIndexOf` trick
// fails here because the marker contains TWO `(` characters (`map(`
// and `({`) and we need the outer one.
const mapOpen = STATE_SRC.indexOf('.map(', start) + '.map'.length;
let depth = 0;
let pos = mapOpen;
let mapClose = -1;
while (pos < STATE_SRC.length) {
    const c = STATE_SRC[pos];
    if (c === '(') depth++;
    else if (c === ')') {
        depth--;
        if (depth === 0) { mapClose = pos; break; }
    }
    pos++;
}
if (mapClose < 0) {
    console.error('unbalanced parens in exportPreset zones.map');
    process.exit(1);
}
// Grab just the map call as an expression, prefix with 'result = ' so
// the sandbox captures the output. The original is `zones: <expr>,`
// so we can slice just the expression part.
const mapExpr = STATE_SRC.slice(start + 'zones: '.length, mapClose + 1);
const runnable = `result = ${mapExpr};`;

// Sandbox with a stubbed `zones` array.
const ctx = {
    zones: [
        {
            name: 'Test', color: null, base: null, pattern: 'none',
            finish: null, intensity: '100',
            customSpec: null, customPaint: null, customBright: null,
            colorMode: 'none', pickerColor: '#3366ff',
            pickerTolerance: 0,    // FALSY — should survive (was already object)
            colors: [],
            scale: 0,              // FALSY — key test
            rotation: 0,           // falsy, but default is also 0
            patternOpacity: 0,     // FALSY
            patternOffsetX: 0,
            patternOffsetY: 0,
            patternStack: [],
            specPatternStack: [],
            overlaySpecPatternStack: [],
            thirdOverlaySpecPatternStack: [],
            fourthOverlaySpecPatternStack: [],
            fifthOverlaySpecPatternStack: [],
            wear: 0,               // falsy, default 0
            muted: false,          // FALSY — key test
        },
    ],
    result: null,
    Array, Object,
};
vm.createContext(ctx);

try {
    vm.runInContext(runnable, ctx, { filename: 'export_preset_map.runtime.js' });
} catch (e) {
    console.error('exportPreset mapping threw:', e);
    process.exit(2);
}

const out = (ctx.result || [])[0] || {};

const checks = [
    // Fields that matter for the fix:
    ['scale', 0, 'scale=0 must not be silently promoted to 1.0'],
    ['rotation', 0, 'rotation=0 must survive (coincidentally the default)'],
    ['wear', 0, 'wear=0 must survive'],
    ['muted', false, 'explicit muted=false must survive'],
    ['patternOpacity', 0, 'patternOpacity=0 (hidden-but-present) must survive'],
];
const results = { fields: {}, failures: [] };
for (const [field, expected, reason] of checks) {
    const got = out[field];
    const ok = Object.is(got, expected);
    results.fields[field] = { expected, got, ok, reason };
    if (!ok) results.failures.push(`${field}: expected ${JSON.stringify(expected)} got ${JSON.stringify(got)} — ${reason}`);
}

// Negative control: mutate the block to put `||` back on scale, rerun,
// verify the mutation IS detected (scale=0 → 1.0).
const mutated = runnable.replace('scale: z.scale ?? 1.0', 'scale: z.scale || 1.0');
if (mutated === runnable) {
    results.negative_control = {
        ran: false,
        error: "Could not find the 'scale: z.scale ?? 1.0' literal to mutate. " +
               "Either the field was renamed or the operator changed form — " +
               "refresh the mutation site in this harness.",
    };
} else {
    const ctx2 = {
        zones: [{ scale: 0 }],
        result: null,
        Array, Object,
    };
    vm.createContext(ctx2);
    try {
        vm.runInContext(mutated, ctx2, { filename: 'export_preset_mutated.runtime.js' });
        const mutScale = ctx2.result[0].scale;
        results.negative_control = {
            ran: true,
            mutation: 'scale: ?? → ||',
            passed_through: mutScale,
            expected_regression: 1.0,
            caught_regression: mutScale === 1.0,
        };
    } catch (e) {
        results.negative_control = { ran: true, threw: String(e) };
    }
}

console.log(JSON.stringify(results, null, 2));
process.exit(results.failures.length > 0 ? 3 : 0);
