/* Guard: every populated finish category must be REACHABLE in the picker.
 *
 * Owner, 2026-08-31: "A couple of the fractured categories you rebuilt last
 * night no longer show up in the ZONE POPOUT picker."
 *
 * A category disappears from the picker in four different ways, and none of
 * them is a crash — the app boots clean and the shelf is simply not there:
 *
 *   1. ORPHANED   the group exists in SPECIAL_GROUPS but is named in no
 *                 SPECIALS_SECTIONS entry. The builder walks
 *                 SPECIALS_SECTION_ORDER -> SPECIALS_SECTIONS[section] -> group,
 *                 so an unreferenced group is never rendered at all. This has
 *                 already cost 77 finishes once (see spb-finish-atlas.js, which
 *                 re-injects three of them at runtime).
 *   2. DANGLING   a section names a group that does not exist — usually a
 *                 rename where one of the two sides was missed.
 *   3. HOLLOW     every id in the group is missing from MONOLITHICS or is on
 *                 REMOVED_SPECIAL_IDS, so the group renders as a bare header.
 *   4. EMOJI      the section list holds a literal "\U0001F9E0 FRACTURED MINDS"
 *                 — a Python-style escape pasted into JS. It never matches the
 *                 real key and the category silently vanishes. This one is in
 *                 the git history.
 *
 * Run: node tests/guard_picker_categories_reachable.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const CATALOG = path.join(ROOT, 'paint-booth-0-finish-data.js');

/* Known and DELIBERATE: pulled from the picker for Alpha because their engine
 * renderers are mid-rebuild and the tiles would 404 (see the comments beside
 * SPECIALS_SECTIONS in the catalog). js/spb-finish-atlas.js re-injects the first
 * two at runtime. Listing them here is a decision with a reason attached — the
 * guard's whole point is that a category never goes missing by accident. Delete
 * an entry when its renderer lands. */
// [2026-09-05 RETIRED LEDGER] 'Chromatic Flake' and 'Atelier — Ultra Detail' are no longer
// "orphans to be re-injected": they are RETIRED (scripts/retired_catalog.json, owner "hide both")
// and js/spb-retired-catalog.js removes them at parse time, so they never reach this guard.
const ALLOWED_ORPHANS = {
    'Wave & Flow': 'no section since the Material World reorg; renderers unverified',
};

function load(file) {
    // Evaluate the retirement ledger FIRST, exactly as paint-booth-v2.html does, so the
    // parse-end prune runs and the tables below are what the picker really builds from.
    const ledgerFile = path.join(ROOT, 'js', 'spb-retired-catalog.js');
    const ledger = fs.existsSync(ledgerFile) ? fs.readFileSync(ledgerFile, 'utf8') : '';
    if (typeof globalThis.window === 'undefined') globalThis.window = globalThis;
    const src = ledger + ';\n' + fs.readFileSync(file, 'utf8');
    const g = {};
    // The catalog is a plain script; evaluate it and lift the four structures
    // the picker actually walks.
    new Function('g', src + `
        ;g.SPECIAL_GROUPS = SPECIAL_GROUPS;
        g.SPECIALS_SECTIONS = SPECIALS_SECTIONS;
        g.SPECIALS_SECTION_ORDER = SPECIALS_SECTION_ORDER;
        g.MONOLITHICS = MONOLITHICS;
        g.BASES = BASES;
        g.REMOVED_SPECIAL_IDS = REMOVED_SPECIAL_IDS;
    `)(g);
    return g;
}

function main() {
    const g = load(CATALOG);
    const { SPECIAL_GROUPS, SPECIALS_SECTIONS, SPECIALS_SECTION_ORDER,
            MONOLITHICS, BASES, REMOVED_SPECIAL_IDS } = g;

    // A shelf can be satisfied from EITHER array: MORTAL SHOKK, MONEY SHOKK,
    // PRISM FORGE, Shokk Series and the Insects all live in BASES even though
    // they appear in the specials picker.
    const known = new Set([...MONOLITHICS, ...BASES].map(m => m.id));
    const reachable = new Set();
    const failures = [];
    const allowed = [];

    for (const section of SPECIALS_SECTION_ORDER) {
        const names = SPECIALS_SECTIONS[section];
        if (!names) {
            failures.push(`SECTION "${section}" is in SPECIALS_SECTION_ORDER but has no SPECIALS_SECTIONS entry`);
            continue;
        }
        for (const name of names) {
            reachable.add(name);
            if (/\\[uU]|\\U0001/.test(name)) {
                failures.push(`EMOJI  "${name}" is a literal escape sequence, not the character — it can never match a group key`);
            }
            // SHOKK DROP is a deliberate placeholder: the lane exists so user
            // imports have a home, and is absent until the first import lands.
            if (!SPECIAL_GROUPS[name] && name !== "SHOKK DROP") {
                failures.push(`DANGLING  section "${section}" names "${name}", which is not a group in SPECIAL_GROUPS`);
            }
        }
    }

    for (const [name, ids] of Object.entries(SPECIAL_GROUPS)) {
        if (!ids || !ids.length) continue;           // deliberately retired: fine
        if (!reachable.has(name)) {
            if (ALLOWED_ORPHANS[name]) {
                allowed.push(`${name} [${ids.length}] — ${ALLOWED_ORPHANS[name]}`);
                continue;
            }
            failures.push(`ORPHANED  "${name}" holds ${ids.length} finishes but is in NO section — invisible in the picker`);
            continue;
        }
        const live = ids.filter(id => known.has(id) && !REMOVED_SPECIAL_IDS.has(id));
        if (!live.length) {
            failures.push(`HOLLOW  "${name}" is reachable but none of its ${ids.length} ids resolve to a MONOLITHICS entry — renders as a bare header`);
        } else if (live.length < ids.length * 0.5) {
            failures.push(`HALF-EMPTY  "${name}" resolves only ${live.length}/${ids.length} ids`);
        }
    }

    const populated = Object.keys(SPECIAL_GROUPS).filter(k => (SPECIAL_GROUPS[k] || []).length);
    console.log(`sections ${SPECIALS_SECTION_ORDER.length} · groups populated ${populated.length} · reachable ${[...reachable].filter(n => (SPECIAL_GROUPS[n] || []).length).length}`);

    if (allowed.length) {
        console.log('\nknown orphans (deliberate, see ALLOWED_ORPHANS):');
        allowed.forEach(a => console.log('  - ' + a));
    }

    if (failures.length) {
        console.log('');
        failures.forEach(f => console.log('  ' + f));
        console.log(`\nRESULT: FAIL - ${failures.length} category visibility problem(s)`);
        process.exit(1);
    }
    console.log('RESULT: OK - every populated category is reachable and resolves');
}

main();
