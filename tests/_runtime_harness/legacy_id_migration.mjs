// HEENAN HP-MIGRATE runtime ratchet — Codex hotfix.
//
// What this proves: a saved zone config object that was created BEFORE the
// HP1-HP4 + HB2 cross-registry rename pass loads cleanly into the current
// build. Each legacy id (acid_rain monolithic, shokk_cipher pattern,
// carbon_weave spec layer, diffraction_grating spec layer) gets rewritten
// to its new canonical id by `_migrateZoneFinishIds` before the renderer
// sees it.
//
// Pre-fix: any such id reached `_applyExtraBaseOverlay` / spec-pattern
// dispatch and produced an orphaned lookup → invisible finish.
// Post-fix: the migration map silently rewrites and the painter's prior
// work renders the same as before the rename.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

// Extract just the migration map + helper. We don't need to load the entire
// state-zones module (that pulls in DOM helpers and engine globals).
function extractRange(src, startMarker, endMarker) {
    const s = src.indexOf(startMarker);
    if (s === -1) throw new Error('start marker not found: ' + startMarker);
    const e = src.indexOf(endMarker, s);
    if (e === -1) throw new Error('end marker not found: ' + endMarker);
    return src.slice(s, e + endMarker.length);
}

// Pull from the migration block start through the closing `}` of the
// `if (typeof window !== 'undefined') { ... }` exposure block. Matched on
// the exact end-marker line in source.
const helperStart = STATE_SRC.indexOf('const _SPB_LEGACY_ID_MIGRATIONS');
const exposeLine  = STATE_SRC.indexOf('window._migrateZoneFinishIds = _migrateZoneFinishIds;', helperStart);
const helperEnd   = STATE_SRC.indexOf('}', exposeLine) + 1;
if (helperStart === -1 || exposeLine === -1) {
    throw new Error('Could not locate migration helper block in state-zones.js');
}
const helperBlock = STATE_SRC.slice(helperStart, helperEnd);

// Sandbox: provide a stub `window` so the helper attaches.
const ctx = {
    window: {},
    Object: Object,
    Array: Array,
};
vm.createContext(ctx);
vm.runInContext(helperBlock, ctx, { filename: 'migration_helper.runtime.js' });

// Build a zone-shaped object that uses every legacy id we expect to migrate.
// Coverage: HP1-HP4 + HB2 (prior shift) + H4HR-1..H4HR-8 (4-hour run).
const preRenameZone = {
    name: 'Hood',
    finish: 'acid_rain',           // HP1 — MONOLITHICS rename → acid_rain_drip
    pattern: 'shokk_cipher',       // HB2 — PATTERNS rename → shokk_cipher_pattern
    patternStack: [
        { id: 'shokk_cipher', opacity: 100 },        // HB2 stack entry
        { id: 'dragonfly_wing', opacity: 90 },       // H4HR-1 → dragonfly_wing_pattern
        { id: 'carbon_weave', opacity: 85 },         // H4HR-2 → carbon_weave_pattern
        { id: 'carbon_fiber', opacity: 80 },         // unrelated, must NOT change
    ],
    specPatternStack: [
        { id: 'carbon_weave', strength: 50 },           // HP2 → spec_carbon_weave
        { id: 'diffraction_grating', strength: 30 },    // HP3 → spec_diffraction_grating_cd
        { id: 'oil_slick', strength: 40 },              // H4HR-4 → spec_oil_slick
        { id: 'gravity_well', strength: 35 },           // H4HR-5 → spec_gravity_well
        { id: 'sparkle_constellation', strength: 25 },  // H4HR-6 → spec_sparkle_constellation
        { id: 'sparkle_firefly', strength: 22 },        // H4HR-7 → spec_sparkle_firefly
        { id: 'sparkle_champagne', strength: 18 },      // H4HR-8 → spec_sparkle_champagne
        { id: 'spec_kevlar_weave', strength: 20 },      // unrelated, must NOT change
    ],
    overlaySpecPatternStack: [
        { id: 'carbon_weave', strength: 25 },           // HP2 in overlay 2
    ],
    fifthOverlaySpecPatternStack: [
        { id: 'diffraction_grating', strength: 10 },    // HP3 in overlay 5
    ],
};

// Also test the H4HR-3 monolithic rename (z.finish = 'crystal_lattice').
const preRenameZone2 = {
    name: 'Roof',
    finish: 'crystal_lattice',      // H4HR-3 → crystal_lattice_mono
    pattern: 'none',
};

const before = JSON.parse(JSON.stringify(preRenameZone));
const changedCount = vm.runInContext(
    '_migrateZoneFinishIds(' + JSON.stringify(preRenameZone) + ')',
    ctx
);

// Re-run with a mutable reference (vm.runInContext copy returns the count
// but mutates our stringified copy — for the actual migration result we
// need to pass via the context).
ctx.__zone = preRenameZone;
const real_changed = vm.runInContext('_migrateZoneFinishIds(__zone)', ctx);
const after = ctx.__zone;

// H4HR-3 monolithic rename
ctx.__zone2 = preRenameZone2;
const zone2_changed = vm.runInContext('_migrateZoneFinishIds(__zone2)', ctx);
const zone2_after = ctx.__zone2;

// Also test a fresh zone without any legacy ids — should not change.
ctx.__cleanZone = {
    name: 'Trunk', finish: null, pattern: 'none',
    patternStack: [{ id: 'carbon_fiber', opacity: 100 }],
    specPatternStack: [{ id: 'spec_kevlar_weave', strength: 50 }],
};
const cleanZoneBefore = JSON.parse(JSON.stringify(ctx.__cleanZone));
const cleanChanged = vm.runInContext('_migrateZoneFinishIds(__cleanZone)', ctx);
const cleanZoneAfter = ctx.__cleanZone;

console.log(JSON.stringify({
    preRename_changed_count: real_changed,
    preRename_zone_after: after,
    preRename_zone_before: before,
    h4hr3_zone2_changed: zone2_changed,
    h4hr3_zone2_finish: zone2_after.finish,
    clean_zone_changed: cleanChanged,
    clean_zone_unchanged: JSON.stringify(cleanZoneBefore) === JSON.stringify(cleanZoneAfter),
    migrations_visible: vm.runInContext('Object.keys(_SPB_LEGACY_ID_MIGRATIONS)', ctx),
    migration_map_full: vm.runInContext('JSON.parse(JSON.stringify(_SPB_LEGACY_ID_MIGRATIONS))', ctx),
}, null, 2));
