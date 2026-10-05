// Which SPECIAL_GROUPS does the picker actually reach? The zone popout walks
// SPECIALS_SECTION_ORDER -> SPECIALS_SECTIONS[section] -> group name, so a group
// that exists but is named in no section is invisible even though it is loaded.
const fs = require('fs');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const sandbox = {};
new Function('g', src + '\n;g.SPECIAL_GROUPS=SPECIAL_GROUPS;g.SPECIALS_SECTIONS=SPECIALS_SECTIONS;'
  + 'g.SPECIALS_SECTION_ORDER=SPECIALS_SECTION_ORDER;g.MONOLITHICS=MONOLITHICS;'
  + 'g.REMOVED_SPECIAL_IDS=REMOVED_SPECIAL_IDS;')(sandbox);
const {SPECIAL_GROUPS, SPECIALS_SECTIONS, SPECIALS_SECTION_ORDER, MONOLITHICS, REMOVED_SPECIAL_IDS} = sandbox;

const reached = new Set();
for (const sec of SPECIALS_SECTION_ORDER) for (const g of (SPECIALS_SECTIONS[sec] || [])) reached.add(g);
const defined = Object.keys(SPECIAL_GROUPS);
const known = new Map(MONOLITHICS.map(m => [m.id, m]));

console.log('sections in order :', SPECIALS_SECTION_ORDER.length);
console.log('groups defined    :', defined.length);
console.log('groups reachable  :', reached.size);

const orphan = defined.filter(g => !reached.has(g) && (SPECIAL_GROUPS[g] || []).length);
console.log('\nORPHANED (defined + populated, but in NO section -> invisible in the picker):');
for (const g of orphan) console.log('   %s  [%d]', g, SPECIAL_GROUPS[g].length);

const dangling = [...reached].filter(g => !SPECIAL_GROUPS[g]);
console.log('\nDANGLING (named by a section, but no such group):');
for (const g of dangling) console.log('   ' + g);

const empty = [...reached].filter(g => SPECIAL_GROUPS[g] && !SPECIAL_GROUPS[g].length);
console.log('\nEMPTY (reachable but zero cards -> renders a bare header):');
for (const g of empty) console.log('   ' + g);

console.log('\nUNRESOLVED ids per reachable group (id in group, no MONOLITHICS entry, or purged):');
for (const g of reached) {
  const ids = SPECIAL_GROUPS[g] || [];
  const bad = ids.filter(i => !known.has(i) || REMOVED_SPECIAL_IDS.has(i));
  if (bad.length) console.log('   %-34s %d/%d bad  e.g. %s', g, bad.length, ids.length, bad.slice(0,4).join(', '));
}
