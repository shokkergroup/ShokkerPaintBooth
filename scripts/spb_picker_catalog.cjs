// Export the actual JS picker identities/tints; runtime Python needs no Node.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const crypto = require('crypto');
const root = path.resolve(__dirname, '..');
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}
async function main() {
const source = fs.readFileSync(path.join(root, 'paint-booth-0-finish-data.js'), 'utf8');
const retirementSource = fs.readFileSync(path.join(root, 'js/spb-retired-catalog.js'), 'utf8');
const mergeSource = fs.readFileSync(path.join(root, 'paint-booth-1-data.js'), 'utf8');
const registry = JSON.parse(fs.readFileSync(path.join(root, 'thumbnails/faithful_picker_registry.json'), 'utf8'));
const warnings = [];
const ctx = { console: { log() {}, warn(...args) { warnings.push(args.join(' ')); },
  error(...args) { warnings.push(args.join(' ')); } }, navigator: {}, location: { href: '' },
  document: { getElementById: () => null, querySelectorAll: () => [], addEventListener() {},
    createElement: () => ({ style: {}, appendChild() {}, setAttribute() {} }) },
  setTimeout: () => 0, clearTimeout() {}, fetch: () => Promise.resolve({ json: () => ({}) }) };
ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
vm.runInContext(retirementSource, ctx);
vm.runInContext(source, ctx);
// Execute the actual async registry merge rather than reimplementing it. This
// includes server-only entries restored to their declared category and its tints.
const mergeStart = mergeSource.indexOf('async function _mergeFinishDataFromServer()');
const mergeEnd = mergeSource.indexOf('// ── Fire the server merge', mergeStart);
if (mergeStart < 0 || mergeEnd < 0) throw new Error('Cannot locate actual picker registry merge');
ctx.fetch = async () => ({ok:true, json:async () => registry});
await vm.runInContext(mergeSource.slice(mergeStart, mergeEnd) + '\n_mergeFinishDataFromServer();', ctx);
if (warnings.length) throw new Error('Picker export did not complete cleanly: ' + warnings.join('; '));
vm.runInContext('\n;globalThis.pickerRows = {base: BASES, pattern: PATTERNS, monolithic: MONOLITHICS};' +
  '\n;globalThis.pickerGroups = {base: BASE_GROUPS, pattern: PATTERN_GROUPS, specials: SPECIAL_GROUPS,' +
  ' sections: SPECIALS_SECTIONS, order: SPECIALS_SECTION_ORDER};', ctx);
const ledger = JSON.parse(fs.readFileSync(path.join(root, 'scripts/retired_catalog.json'), 'utf8'));
const retired = new Set(ledger.entries.filter(e => e.id && e.policy === 'hide').map(e => e.id));
// Match the real category builder: it deliberately has no orphan bucket.
// Raw arrays retain old experiments and cross-reference finishes; baking those
// would resurrect retired content or fail forever on removed engine recipes.
const groups = ctx.pickerGroups;
const activeSpecials = new Set(groups.order.flatMap(section =>
  (groups.sections[section] || []).flatMap(group => groups.specials[group] || [])));
const reachable = {
  base: new Set([...Object.values(groups.base).flat(), ...activeSpecials]),
  pattern: new Set(Object.values(groups.pattern).flat()),
  monolithic: activeSpecials
};
const items = new Map();
for (const [type, rows] of Object.entries(ctx.pickerRows)) {
  for (const row of rows || []) {
    if (!row.id || row.id === 'none' || retired.has(row.id) || !reachable[type].has(row.id)) continue;
    const kind = ctx.FINISH_TYPE_BY_ID[row.id] || (row.id.startsWith('pf_') ? 'base' : type);
    let color = String(row.swatch || '').trim().replace(/^#/, '').toLowerCase();
    if (/^[0-9a-f]{3}$/.test(color)) color = color.split('').map(c => c+c).join('');
    if (!/^[0-9a-f]{6}$/.test(color)) color = '888888';
    items.set(kind + ':' + row.id, { type: kind, id: row.id, color });
  }
}
const result = { schema: 'spb-faithful-picker-catalog/1',
  source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
  merge_source_sha256: crypto.createHash('sha256').update(mergeSource).digest('hex'),
  retirement_source_sha256: crypto.createHash('sha256').update(retirementSource).digest('hex'),
  registry_sha256: crypto.createHash('sha256').update(JSON.stringify(canonical(registry))).digest('hex'),
  items: [...items.values()].sort((a,b) => (a.type+':'+a.id).localeCompare(b.type+':'+b.id)) };
const target = path.join(root, 'thumbnails/faithful_picker_catalog.json');
const encoded = JSON.stringify(result, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== encoded) {
    console.error('Picker bake catalog is stale: run node scripts/spb_picker_catalog.cjs then python scripts/bake_faithful_picker.py');
    process.exit(1);
  }
} else {
  fs.mkdirSync(path.dirname(target), {recursive:true});
  fs.writeFileSync(target, encoded);
}
console.log(`Faithful picker catalog: ${result.items.length} identities (${process.argv.includes('--check') ? 'verified' : 'saved'}).`);
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
