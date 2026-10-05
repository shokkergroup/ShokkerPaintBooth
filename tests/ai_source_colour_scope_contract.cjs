'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const w = { console }; w.window = w; vm.createContext(w);
for (const f of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), w, { filename: f });
}
const env = { palette: [{ hex: '#1347a8', share_pct: 30 }, { hex: '#141416', share_pct: 70 }], layers: [] };
const panelCases = [
  ['Change the roof from blue to red; keep everything else untouched.', 'roof'],
  ['Change only the hood from blue to red.', 'hood'],
  ['Recolour the roof from blue to gold, leave everything else unchanged!', 'roof'],
  ['Change the hood from blue into red; the rest stays the same.', 'hood']
];
for (const [text, part] of panelCases) {
  const p = w.SpbProEdit.plan(text, env);
  assert(p && p.kind === 'ops', `source-to-destination correction must retain a scoped owner: ${text}`);
  assert.equal(p.ops.length, 1, `source colour/preservation tail must not become a second job: ${text}`);
  assert.equal(p.ops[0].target.kind, 'part');
  assert.equal(p.ops[0].target.part, part);
  const compiled = w.SpbProEdit.compile(p, env);
  assert.equal(compiled.zones.length, 1);
  assert.equal(compiled.zones[0].region.part, part);
  assert(!compiled.zones[0].region.colors, 'whole-panel correction must not add a global source-colour region');
  assert.equal(compiled.missing.length, 0);
}
const broad = w.SpbProEdit.compile(w.SpbProEdit.plan('Change the blue to red.', env), env);
assert.equal(broad.zones.length, 1);
assert.equal(broad.zones[0].region.colors[0], '#1347a8');
assert(!broad.zones[0].region.part, 'an explicitly colour-wide request must remain colour-wide');
const intersection = w.SpbProEdit.compile(w.SpbProEdit.plan('Make the blue on the roof red.', env), env);
assert.equal(intersection.zones.length, 1);
assert.equal(intersection.zones[0].region.colors[0], '#1347a8');
assert.equal(intersection.zones[0].region.part, 'roof', 'on-panel colour request must retain both selectors');
console.log(`source-colour scope contract passed (${panelCases.length} panel corrections; broad and intersection controls)`);
