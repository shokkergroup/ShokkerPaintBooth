// HEENAN 5H OVERNIGHT — iter 9 runtime proof for the DNA-strip fix
// in `_extractZoneDNA` (paint-booth-2-state-zones.js ~line 12052).
//
// Pre-fix state: the strip step removed any `val === 0` OR `val === false`.
// That silently erased painter intent on fields where 0 is NOT the
// canonical load-default — `baseColorStrength=0` (load-default 1),
// `baseStrength=0`, `baseSpecStrength=0`, `patternSpecMult=0`, and the
// *Scale families (load-default 1.0). Copy DNA → Paste DNA silently
// failed to transfer these values.
//
// Post-fix: per-field `_DNA_DEFAULTS` lookup; a value is stripped only
// when it equals the field's canonical default. `baseColorStrength=0`
// is NOT stripped (0 ≠ default 1).
//
// This harness extracts the live strip block and runs it against two
// realistic zone states: one with "painter explicitly set strength=0"
// and one where the strength matches the default. Asserts correct
// strip/keep behavior for both.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

// Extract the entire `_extractZoneDNA` function body — we'll just
// invoke it with a synthetic zone.
const fnAnchor = 'function _extractZoneDNA(zoneIndex) {';
const fnStart = STATE_SRC.indexOf(fnAnchor);
if (fnStart < 0) {
    console.error('could not locate _extractZoneDNA');
    process.exit(1);
}
// Walk braces to find end of function.
let depth = 0;
let inFunc = false;
let fnEnd = -1;
for (let i = fnStart; i < STATE_SRC.length; i++) {
    const c = STATE_SRC[i];
    if (c === '{') { depth++; inFunc = true; }
    else if (c === '}') {
        depth--;
        if (inFunc && depth === 0) { fnEnd = i + 1; break; }
    }
}
if (fnEnd < 0) {
    console.error('unbalanced braces in _extractZoneDNA');
    process.exit(1);
}
const fnSrc = STATE_SRC.slice(fnStart, fnEnd);

// Sandbox.
const ctx = {
    zones: null,
    Array, Object,
    console,
};
vm.createContext(ctx);
// Load the function definition into the sandbox.
vm.runInContext(fnSrc, ctx, { filename: '_extractZoneDNA.runtime.js' });

// --- Case A: painter explicitly set falsy fields that DO exist in
// the DNA object literal. Note: baseStrength / baseSpecStrength /
// patternSpecMult are not captured by _extractZoneDNA (by design —
// those live in the main save/load path, not DNA); scaled-secondary-
// base fields and baseColorStrength ARE captured.
ctx.zones = [{
    name: 'painter-set-zero',
    base: 'gloss',
    baseColorStrength: 0,   // explicit: no base-color overlay (default=1)
    scale: 0,               // explicit degenerate (default=1.0)
    secondBaseScale: 0,     // (default=1.0, NOT in dna pre-fix because || clobbered)
    secondBaseFractalScale: 0, // (default=24)
}];
let dna_A;
try {
    dna_A = ctx._extractZoneDNA(0);
} catch (e) {
    console.error('call A threw:', e);
    process.exit(2);
}

// --- Case B: same fields at DEFAULT values (should be stripped) ---
ctx.zones = [{
    name: 'defaults',
    base: 'gloss',
    baseColorStrength: 1,   // default
    baseStrength: 1,        // default
    baseSpecStrength: 1,    // default
    patternSpecMult: 1,     // default
}];
let dna_B;
try {
    dna_B = ctx._extractZoneDNA(0);
} catch (e) {
    console.error('call B threw:', e);
    process.exit(2);
}

// --- Case C: field at an arbitrary non-default value (must be kept) ---
ctx.zones = [{
    name: 'custom',
    baseColorStrength: 0.5,
    baseStrength: 0.7,
    scale: 2.0,
}];
let dna_C;
try {
    dna_C = ctx._extractZoneDNA(0);
} catch (e) {
    console.error('call C threw:', e);
    process.exit(2);
}

const results = {
    case_A_painter_zero: {
        // Bug-fix verification: these MUST be present in DNA after fix.
        baseColorStrength_present: 'baseColorStrength' in dna_A,
        baseColorStrength_value: dna_A.baseColorStrength,
        scale_present: 'scale' in dna_A,
        scale_value: dna_A.scale,
        secondBaseScale_present: 'secondBaseScale' in dna_A,
        secondBaseFractalScale_present: 'secondBaseFractalScale' in dna_A,
    },
    case_B_defaults: {
        // These equal their defaults; SHOULD be stripped.
        baseColorStrength_stripped: !('baseColorStrength' in dna_B),
        scale_stripped: !('scale' in dna_B),
    },
    case_C_custom: {
        baseColorStrength_kept: 'baseColorStrength' in dna_C && dna_C.baseColorStrength === 0.5,
        scale_kept: 'scale' in dna_C && dna_C.scale === 2.0,
    },
    dna_A_keys_count: Object.keys(dna_A).length,
    dna_B_keys_count: Object.keys(dna_B).length,
};

// Validate
const failures = [];
const A = results.case_A_painter_zero;
if (!A.baseColorStrength_present)
    failures.push('case A: baseColorStrength=0 STRIPPED from DNA (the bug)');
if (A.baseColorStrength_value !== 0)
    failures.push(`case A: baseColorStrength stored as ${A.baseColorStrength_value} not 0`);
if (!A.scale_present)
    failures.push('case A: scale=0 STRIPPED (bug — scale default is 1.0)');
if (A.scale_value !== 0)
    failures.push(`case A: scale stored as ${A.scale_value} not 0`);
if (!A.secondBaseScale_present)
    failures.push('case A: secondBaseScale=0 STRIPPED (bug — default is 1.0)');
if (!A.secondBaseFractalScale_present)
    failures.push('case A: secondBaseFractalScale=0 STRIPPED (bug — default is 24)');
if (!results.case_B_defaults.baseColorStrength_stripped)
    failures.push('case B: baseColorStrength=1 should be stripped (= default) but was kept');
if (!results.case_B_defaults.scale_stripped)
    failures.push('case B: scale=1.0 should be stripped (= default) but was kept');
if (!results.case_C_custom.baseColorStrength_kept)
    failures.push('case C: baseColorStrength=0.5 not round-tripped');
if (!results.case_C_custom.scale_kept)
    failures.push('case C: scale=2.0 not round-tripped');

results.failures = failures;
console.log(JSON.stringify(results, null, 2));
process.exit(failures.length > 0 ? 3 : 0);
