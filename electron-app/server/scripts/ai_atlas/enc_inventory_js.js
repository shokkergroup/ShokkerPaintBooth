/* enc_inventory_js.js - helper for enc_inventory.py (2026-10-04). Loads the shipped JS DATA files in a vm (read-only) and prints ONE json dump:
   catalogue groups/counts, atlas shelves, car atlas, cards count. Usage: node enc_inventory_js.js <out.json> */
'use strict';
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const out = process.argv[2] || path.join(ROOT, '_easy_claude_work', 'enc', 'inv_js.json');
const ctx = { console: { log() {}, warn() {}, error() {} }, setTimeout() {}, document: undefined }; ctx.window = ctx; vm.createContext(ctx);
const errs = [];
['paint-booth-0-finish-data.js', 'paint-booth-0-finish-metadata.js', 'js/spb-ai-atlas-data.js', 'js/spb-car-atlas-data.js', 'js/spb-ai-cards-data.js'].forEach(f => {
    try { vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx, { filename: f }); } catch (e) { errs.push(f + ': ' + String(e.message).slice(0, 100)); }
});
function ev(expr) { try { return vm.runInContext('(function(){try{return ' + expr + '}catch(e){return undefined}})()', ctx); } catch (e) { return undefined; } }
function groupCounts(name) { const g = ev(name); if (!g) return null; const o = {}; Object.keys(g).forEach(k => { o[k] = Array.isArray(g[k]) ? g[k].length : 0; }); return o; }
const r = { errors: errs };
r.counts = { BASES: ev('BASES.length'), MONOLITHICS: ev('MONOLITHICS.length'), PATTERNS: ev('PATTERNS.length'), SPEC_PATTERNS: ev('SPEC_PATTERNS.length') };
r.base_groups = groupCounts('BASE_GROUPS'); r.monolithic_groups = groupCounts('MONOLITHIC_GROUPS');
r.pattern_groups = groupCounts('PATTERN_GROUPS'); r.spec_pattern_groups = groupCounts('SPEC_PATTERN_GROUPS');
r.finish_categories = ev('FINISH_CATEGORIES') || {};
const a = ctx.SPB_ATLAS_DATA || {};
r.atlas = { count: a.count, sections: a.sections, sizes: a.sectionSize, blurbs: a.blurbs, groups: a.groups };
r.cars = ((ctx.SPB_CAR_ATLAS || {}).cars || []).map(c => ({ id: c.id, name: c.name, folders: c.folders }));
const cd = ctx.SPB_CARDS_DATA || {}; r.cards = { n: cd.n, moods: cd.moods, eras: cd.eras, uses: cd.uses, fits: cd.fits };
// per-pattern / spec-pattern group member names (ids) -> only first 3 per group, for examples
function sample(name) { const g = ev(name); if (!g) return {}; const o = {}; Object.keys(g).forEach(k => { o[k] = (g[k] || []).slice(0, 3); }); return o; }
r.pattern_sample = sample('PATTERN_GROUPS'); r.spec_pattern_sample = sample('SPEC_PATTERN_GROUPS'); r.base_sample = sample('BASE_GROUPS');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(r));
console.log('inv_js OK errors=' + errs.length + ' bases=' + r.counts.BASES + ' monos=' + r.counts.MONOLITHICS + ' patterns=' + r.counts.PATTERNS + ' spec=' + r.counts.SPEC_PATTERNS + ' cars=' + r.cars.length);
