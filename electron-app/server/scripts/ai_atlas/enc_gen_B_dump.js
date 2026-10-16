/* enc_gen_B_dump.js - helper for enc_gen_B.py (Encyclopedia v2, lane B, 2026-10-04).
   Loads the shipped JS DATA files in a vm (read-only) and writes ONE json dump of what the generator needs:
   patterns + groups, spec patterns + groups, base / monolithic group membership, atlas items + shelves, finish cards (decoded).
   Usage: node enc_gen_B_dump.js <out.json> */
'use strict';
const vm = require('vm'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..', '..');
const out = process.argv[2] || path.join(ROOT, 'data', 'encyclopedia', '_drafts', '_dumpB.json');
const ctx = { console: { log() {}, warn() {}, error() {} }, setTimeout() {}, document: undefined }; ctx.window = ctx; vm.createContext(ctx);
const errs = [];
['paint-booth-0-finish-data.js', 'paint-booth-0-finish-metadata.js', 'js/spb-ai-atlas-data.js', 'js/spb-ai-cards-data.js'].forEach(f => {
    try { vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx, { filename: f }); } catch (e) { errs.push(f + ': ' + String(e.message).slice(0, 100)); }
});
function ev(expr) { try { return vm.runInContext('(function(){try{return ' + expr + '}catch(e){return undefined}})()', ctx); } catch (e) { return undefined; } }
const r = { errors: errs };
const slim = a => (a || []).map(x => ({ id: x.id, name: x.name, desc: x.desc, swatch: x.swatch, category: x.category, defaults: x.defaults, defaultChannels: x.defaultChannels }));
r.patterns = slim(ev('PATTERNS'));
r.pattern_groups = ev('PATTERN_GROUPS') || {};
r.spec_patterns = slim(ev('SPEC_PATTERNS'));
r.spec_pattern_groups = ev('SPEC_PATTERN_GROUPS') || {};
r.bases = slim(ev('BASES'));
r.monolithics = slim(ev('MONOLITHICS'));
r.base_groups = ev('BASE_GROUPS') || {};
r.monolithic_groups = ev('MONOLITHIC_GROUPS') || {};
const a = ctx.SPB_ATLAS_DATA || {};
r.atlas = { sections: a.sections, sizes: a.sectionSize, blurbs: a.blurbs, groups: a.groups, items: a.items };
const cd = ctx.SPB_CARDS_DATA || {};
r.cards = { moods: cd.moods, eras: cd.eras, uses: cd.uses, fits: cd.fits, cards: cd.cards };
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(r));
console.log('dumpB OK errors=' + errs.length + ' patterns=' + r.patterns.length + ' spec=' + r.spec_patterns.length + ' bases=' + r.bases.length + ' monos=' + r.monolithics.length + ' atlas=' + (a.items || []).length + ' cards=' + Object.keys(cd.cards || {}).length + ' ' + errs.join('; '));
