const fs = require('fs');
function reach(path) {
  const src = fs.readFileSync(path, 'utf8');
  const g = {};
  new Function('g', src + '\n;g.SG=SPECIAL_GROUPS;g.SS=SPECIALS_SECTIONS;g.SO=SPECIALS_SECTION_ORDER;')(g);
  const seen = new Set();
  for (const s of g.SO) for (const n of (g.SS[s]||[])) if ((g.SG[n]||[]).length) seen.add(n);
  // the Atlas also injects three groups at runtime; count anything populated
  const populated = Object.keys(g.SG).filter(k => (g.SG[k]||[]).length);
  return { reachable: seen, populated: new Set(populated), sizes: Object.fromEntries(populated.map(k=>[k,g.SG[k].length])) };
}
const A = reach('_wealth_work/head-finish-data.js');   // last commit
const B = reach('paint-booth-0-finish-data.js');       // working tree
const gone = [...A.reachable].filter(k => !B.reachable.has(k));
const added = [...B.reachable].filter(k => !A.reachable.has(k));
console.log('HEAD reachable %d  ->  NOW reachable %d', A.reachable.size, B.reachable.size);
console.log('\nGONE from the picker since the last commit:');
gone.forEach(k => console.log('   %s   was [%d]', k, A.sizes[k]));
console.log('\nNEW in the picker:');
added.forEach(k => console.log('   %s   now [%d]', k, B.sizes[k]));
console.log('\nRESIZED:');
[...B.reachable].filter(k=>A.sizes[k] && A.sizes[k]!==B.sizes[k])
  .forEach(k => console.log('   %-30s %d -> %d', k, A.sizes[k], B.sizes[k]));
