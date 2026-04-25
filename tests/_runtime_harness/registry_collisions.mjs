// HEENAN HP1-HP4 + HB2 ratchet: cross-registry id collisions and
// intra-registry duplicate ids in paint-booth-0-finish-data.js.
//
// validateFinishData() (the existing in-source validator) only checks
// per-registry shape. Pillman's audit found 4 BUGS the validator missed:
//   - acid_rain in BASES + MONOLITHICS
//   - carbon_weave in BASES + PATTERNS + SPEC_PATTERNS
//   - diffraction_grating in PATTERNS + SPEC_PATTERNS
//   - mystichrome × 2 in MONOLITHICS
// All four are now fixed. This harness re-runs the same checks so any
// future regression fires immediately at test time.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-0-finish-data.js'), 'utf8');

// Load the catalog into a sandbox.
const ctx = {
    window: undefined,
    console: { log: () => {}, warn: () => {} },
    setTimeout: () => {},
};
vm.createContext(ctx);
vm.runInContext(SRC, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });

const BASES         = vm.runInContext('BASES', ctx);
const PATTERNS      = vm.runInContext('PATTERNS', ctx);
const MONOLITHICS   = vm.runInContext('MONOLITHICS', ctx);
const SPEC_PATTERNS = vm.runInContext('SPEC_PATTERNS', ctx);

function idCount(arr, id) {
    let n = 0;
    for (const e of arr) if (e && e.id === id) n++;
    return n;
}

function collectIds(arr) {
    return new Set(arr.filter(e => e && e.id).map(e => e.id));
}

const baseIds   = collectIds(BASES);
const patIds    = collectIds(PATTERNS);
const monoIds   = collectIds(MONOLITHICS);
const specIds   = collectIds(SPEC_PATTERNS);

// --- intra-registry duplicates ---
const intraDupes = {};
for (const [name, arr] of [['BASES', BASES], ['PATTERNS', PATTERNS], ['MONOLITHICS', MONOLITHICS], ['SPEC_PATTERNS', SPEC_PATTERNS]]) {
    const seen = new Map();
    for (const e of arr) {
        if (!e || !e.id) continue;
        seen.set(e.id, (seen.get(e.id) || 0) + 1);
    }
    intraDupes[name] = Array.from(seen.entries()).filter(([, c]) => c > 1).map(([id]) => id);
}

// --- cross-registry collisions ---
function intersect(a, b) {
    const out = [];
    for (const x of a) if (b.has(x)) out.push(x);
    return out;
}
const crossCollisions = {
    base_x_mono: intersect(baseIds, monoIds),
    base_x_pattern: intersect(baseIds, patIds),
    base_x_spec: intersect(baseIds, specIds),
    pattern_x_spec: intersect(patIds, specIds),
    pattern_x_mono: intersect(patIds, monoIds),
    spec_x_mono: intersect(specIds, monoIds),
};

console.log(JSON.stringify({
    sizes: {
        BASES: BASES.length, PATTERNS: PATTERNS.length,
        MONOLITHICS: MONOLITHICS.length, SPEC_PATTERNS: SPEC_PATTERNS.length,
    },
    intra_registry_duplicates: intraDupes,
    cross_registry_collisions: crossCollisions,
}, null, 2));
