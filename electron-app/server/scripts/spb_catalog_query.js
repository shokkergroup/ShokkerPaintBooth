// Read-only inspector for the static catalog (SPECIAL_GROUPS / MONOLITHICS /
// BASES / SPECIALS_SECTIONS) without booting the Python engine.
//
//   node scripts/spb_catalog_query.js groups <substr> [<substr> ...]   group sizes + sample names
//   node scripts/spb_catalog_query.js ids <groupSubstr>                every id in the matching group(s)
//   node scripts/spb_catalog_query.js dump <groupSubstr>               id, name and desc as JSON
//   node scripts/spb_catalog_query.js sections                         section -> group list
//
// Written as a FILE because the same query inline through a shell heredoc kept
// mangling quotes and unicode escapes.
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const sb = {
  console: { log() {}, warn() {}, error() {} },
  document: {
    addEventListener() {}, querySelector() { return null; }, getElementById() { return null; },
    createElement() { return { style: {}, classList: { add() {}, remove() {} }, appendChild() {} }; },
  },
  localStorage: { getItem() { return null; }, setItem() {} },
  navigator: { userAgent: 'node' },
  setTimeout, clearTimeout,
  fetch: () => Promise.reject(new Error('no net')),
  OUT: {},
};
sb.window = sb; sb.globalThis = sb;
vm.createContext(sb);
vm.runInContext(
  fs.readFileSync(path.join(ROOT, 'paint-booth-0-finish-data.js'), 'utf8') +
  '\nOUT.SG = SPECIAL_GROUPS; OUT.M = MONOLITHICS; OUT.B = BASES;' +
  ' OUT.SS = SPECIALS_SECTIONS; OUT.BG = BASE_GROUPS;',
  sb, { filename: 'finish-data' });

const { SG, M, B, SS, BG } = sb.OUT;
const entry = (id) => M.find((x) => x.id === id) || B.find((x) => x.id === id) || null;
const match = (needles) => Object.keys(SG).filter(
  (g) => needles.some((n) => g.toUpperCase().includes(n.toUpperCase())));

const cmd = process.argv[2];
const args = process.argv.slice(3);

if (cmd === 'groups') {
  for (const g of match(args)) {
    const names = SG[g].map((i) => (entry(i) || {}).name).filter(Boolean);
    console.log(`${g}  [${SG[g].length}]  unresolved=${SG[g].length - names.length}`);
    console.log('    ' + names.slice(0, 6).join(' | '));
  }
} else if (cmd === 'ids') {
  for (const g of match(args)) console.log(SG[g].join(','));
} else if (cmd === 'dump') {
  const out = [];
  for (const g of match(args)) {
    for (const id of SG[g]) {
      const e = entry(id) || {};
      out.push({ group: g, id, name: e.name || null, desc: e.desc || null, swatch: e.swatch || null });
    }
  }
  console.log(JSON.stringify(out, null, 1));
} else if (cmd === 'sections') {
  for (const [k, v] of Object.entries(SS)) console.log(`${k}: ${v.length} groups`);
  console.log('--- base groups ---');
  for (const [k, v] of Object.entries(BG)) console.log(`${k}: ${(v || []).length}`);
} else {
  console.log('usage: groups|ids|dump <substr...>  |  sections');
}
