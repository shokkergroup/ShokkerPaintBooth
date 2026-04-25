// HEENAN 5H OVERNIGHT — iter 4 behavioral proof for loadConfigFromObj.
//
// Replaces / supplements the 19 parametric source-text `??` pins in
// `tests/test_regression_save_load_repair_integrity.py` with a real
// run of the live zone-mapping block. Source pins can only catch a
// `||`-vs-`??` switch AT THAT LINE; they miss:
//   - a later re-assignment elsewhere in the function,
//   - a migration helper that overrides values after mapping,
//   - a post-load normalization that resets picker fields,
//   - a `repairZoneData` quirk that defaults fields that were valid
//     but happened to trip a type-check.
//
// This harness extracts the live `zones = cfg.zones.map(z => ({ ... }))`
// block from paint-booth-2-state-zones.js and runs it against a
// saved-config shape where every field tested by the 19-way pytest
// parametric is set to its FALSY legitimate value (tolerance=0,
// scale=0, wear=0, muted=false, flipH=false, etc.). After mapping,
// the test asserts each field survived bit-for-bit.
//
// Output: JSON with the post-mapping zone and pass/fail flags so the
// pytest wrapper can diff field-by-field.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

// --- Extract the zones.map block from the live source ---
// We grab the substring starting at `zones = cfg.zones.map(z => ({`
// and track brace/paren depth until matching `}));`.
const marker = 'zones = cfg.zones.map(z => ({';
const start = STATE_SRC.indexOf(marker);
if (start < 0) {
    console.error('Could not locate zones.map block — loadConfigFromObj may have been restructured');
    process.exit(1);
}

// Walk forward from `(` of `map(` counting parens until balanced.
// The `map(...)` open paren is just before `z =>`.
const mapOpenParen = STATE_SRC.lastIndexOf('(', start + marker.length - 1);
let parenDepth = 0;
let pos = mapOpenParen;
let mapClose = -1;
while (pos < STATE_SRC.length) {
    const c = STATE_SRC[pos];
    if (c === '(') parenDepth++;
    else if (c === ')') {
        parenDepth--;
        if (parenDepth === 0) { mapClose = pos; break; }
    }
    pos++;
}
if (mapClose < 0) {
    console.error('unbalanced parens in zones.map');
    process.exit(1);
}
// Include the `;` at the end.
const blockEnd = STATE_SRC.indexOf(';', mapClose) + 1;
const mapBlock = STATE_SRC.slice(start, blockEnd);
// mapBlock now is: `zones = cfg.zones.map(z => ({ ... }));`

// --- Sandbox setup ---
let idCounter = 0;
const ctx = {
    // The local helpers the mapping references
    _newZoneId: () => `new-id-${++idCounter}`,
    _cloneUint8ArrayLike: (x) => (x == null ? null : x),
    // The two state vars being written to
    zones: null,
    cfg: null,
    // Object/Array/JSON are needed for spread/literals
    Object, Array, JSON, Math, Number, Uint8Array,
    console,
};
vm.createContext(ctx);

// --- Build a realistic falsy-value saved-config ---
// Every ??-default field in the mapping block is set to its falsy
// legitimate value. If the mapping honors `??`, every field survives.
// If the mapping regresses to `||`, falsy values get overwritten.
ctx.cfg = {
    zones: [
        {
            id: 'zone-1',
            name: 'TestZone',
            color: null,
            base: null,
            pattern: 'none',
            finish: null,
            intensity: '100',
            customSpec: null,
            customPaint: null,
            customBright: null,
            colorMode: 'none',
            pickerColor: '#3366ff',
            pickerTolerance: 0,       // FALSY — must survive (explicit exact-match selector)
            colors: [],
            spatialMask: null,
            scale: 0,                 // FALSY — must survive (degenerate, but painter-valid)
            rotation: 0,              // FALSY — survives (but also the default)
            patternOpacity: 0,        // FALSY — must survive
            patternOffsetX: 0,
            patternOffsetY: 0,
            patternStack: [],
            specPatternStack: [],
            overlaySpecPatternStack: [],
            thirdOverlaySpecPatternStack: [],
            fourthOverlaySpecPatternStack: [],
            fifthOverlaySpecPatternStack: [],
            patternIntensity: '0',    // FALSY-like string
            wear: 0,                  // FALSY — survives (but also default)
            muted: false,             // FALSY — must survive (explicit unmuted)
            linkGroup: null,
            baseStrength: 0,          // FALSY — must survive (no base influence)
            baseSpecStrength: 0,      // FALSY
            patternSpecMult: 0,       // FALSY
            patternFlipH: false,      // FALSY — must survive
            patternFlipV: false,      // FALSY
            baseOffsetX: 0,
            baseOffsetY: 0,
            baseRotation: 0,
            baseFlipH: false,         // FALSY — must survive
            baseFlipV: false,
            baseScale: 0,             // FALSY — must survive
            baseColorMode: 'source',
            baseColor: '#ffffff',
            baseColorSource: null,
            baseColorStrength: 0,     // FALSY
            baseColorFitZone: false,
            gradientStops: null,
            gradientDirection: 'horizontal',
            baseHueOffset: 0,
            baseSaturationAdjust: 0,
            baseBrightnessAdjust: 0,
            // Mirror pairs for secondBase* / thirdBase* / fourthBase* / fifthBase*
            // are also in the mapping — the block reads whatever is passed,
            // so omitted fields resolve to null/default via `??`.
        },
    ],
};

// --- Run the mapping in the sandbox ---
try {
    vm.runInContext(mapBlock, ctx, { filename: 'zones_map.runtime.js' });
} catch (e) {
    console.error('mapping threw:', e);
    process.exit(2);
}

const z = ctx.zones[0];
const expected = ctx.cfg.zones[0];

// --- Field-by-field comparison for ??-preservation ---
// Each entry: [field, expectedValue, whyItMatters]
const checks = [
    ['pickerTolerance', 0,        'tolerance=0 = exact-match color selector'],
    ['pickerColor',     '#3366ff', 'explicit hex preserved'],
    ['scale',           0,        'scale=0 = degenerate but painter-valid'],
    ['rotation',        0,        'rotation=0 = default'],
    ['patternOpacity',  0,        'opacity=0 = hidden-but-present pattern'],
    ['patternIntensity','0',      'intensity string "0"'],
    ['wear',            0,        'wear=0 = new paint'],
    ['muted',           false,    'explicit unmuted state'],
    ['baseStrength',    0,        'baseStrength=0 = no base influence'],
    ['baseSpecStrength',0,        'baseSpecStrength=0'],
    ['patternSpecMult', 0,        'patternSpecMult=0'],
    ['patternFlipH',    false,    'explicit no-flip'],
    ['patternFlipV',    false,    'explicit no-flip'],
    ['baseRotation',    0,        'baseRotation=0 = default'],
    ['baseFlipH',       false,    'explicit no-flip'],
    ['baseFlipV',       false,    'explicit no-flip'],
    ['baseScale',       0,        'baseScale=0'],
    ['baseHueOffset',   0,        'hue offset=0 = neutral'],
    ['baseSaturationAdjust', 0,   'sat adjust=0 = neutral'],
    ['baseBrightnessAdjust', 0,   'brightness adjust=0 = neutral'],
];

const results = {
    zone_count: ctx.zones.length,
    id: z.id,
    field_checks: {},
    failures: [],
};
for (const [field, expectedVal, reason] of checks) {
    const got = z[field];
    const ok = Object.is(got, expectedVal);
    results.field_checks[field] = { expected: expectedVal, got, ok, reason };
    if (!ok) results.failures.push(`${field}: expected ${JSON.stringify(expectedVal)} got ${JSON.stringify(got)} (${reason})`);
}

// Also assert non-falsy fields came through unchanged.
const structural = [
    ['name', 'TestZone'],
    ['id', 'zone-1'],
    ['pattern', 'none'],
    ['colorMode', 'none'],
];
results.structural_checks = {};
for (const [field, expectedVal] of structural) {
    const got = z[field];
    const ok = got === expectedVal;
    results.structural_checks[field] = { expected: expectedVal, got, ok };
    if (!ok) results.failures.push(`structural ${field}: expected ${JSON.stringify(expectedVal)} got ${JSON.stringify(got)}`);
}

// --- Negative control: mutate the block to use `||` instead of `??`
// on pickerTolerance and re-run. The harness must DETECT the regression
// (pickerTolerance=0 gets replaced by 40). This proves the test isn't a
// source-pin wearing behavioral clothing — it really runs the code.
const mutatedBlock = mapBlock.replace(
    'pickerTolerance: z.pickerTolerance ?? 40',
    'pickerTolerance: z.pickerTolerance || 40',
);
if (mutatedBlock === mapBlock) {
    results.negative_control = {
        ran: false,
        error: "Couldn't find the `pickerTolerance ?? 40` literal to mutate. " +
               "Either the field default changed or the block structure shifted. " +
               "Update the mutation site in this harness.",
    };
} else {
    // Run the mutated block in a FRESH sandbox (don't pollute ctx).
    const mutCtx = {
        _newZoneId: () => 'mut-id',
        _cloneUint8ArrayLike: (x) => (x == null ? null : x),
        zones: null,
        cfg: { zones: [{ pickerTolerance: 0 }] },
        Object, Array, JSON, Math, Number, Uint8Array,
        console,
    };
    vm.createContext(mutCtx);
    try {
        vm.runInContext(mutatedBlock, mutCtx, { filename: 'mutated.runtime.js' });
        const mutTol = mutCtx.zones[0].pickerTolerance;
        results.negative_control = {
            ran: true,
            mutation: 'pickerTolerance: ?? → ||',
            passed_through: mutTol,
            expected_regression: 40,
            caught_regression: mutTol === 40,
        };
    } catch (e) {
        results.negative_control = { ran: true, threw: String(e) };
    }
}

console.log(JSON.stringify(results, null, 2));
process.exit(results.failures.length > 0 ? 3 : 0);
