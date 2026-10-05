'use strict';
// Focused W4 semantic disambiguation and edit-command ownership checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
let providerCalls = 0;
const world = { console, fetch: () => { providerCalls++; throw new Error('offline helper attempted fetch'); } };
world.window = world; world.document = {}; world.XMLHttpRequest = function () { providerCalls++; throw new Error('offline helper attempted XHR'); };
vm.createContext(world);
for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), world, { filename: file });
}
function deepFreeze(value) {
  Object.freeze(value);
  Object.keys(value).forEach(key => { const next = value[key]; if (next && typeof next === 'object' && !Object.isFrozen(next)) deepFreeze(next); });
  return value;
}
function state(kind = 'flat') {
  const psd = kind === 'psd';
  return deepFreeze({
    paint: psd ? 'psd' : 'flat',
    layers: psd ? [{ id: 'body', name: 'Body' }, { id: 'numbers', name: 'Numbers' }, { id: 'sponsors', name: 'Sponsors' }] : [{ id: 'body', name: 'Body' }],
    zones: [{ i: 0, name: 'Body', muted: false, base: 'Gloss', finish: 'Gloss', colourMode: 'finish', pattern: 'Flames', patternMode: 'overlay', spec: 1, layers: [], intensity: 100 }],
    selected: 0, carMap: { known: true, missing: [] }, mode: 'pro', last: null
  });
}
const helpCases = [
  ['How can I increase the height and width of my number artwork?', 'psd', 'hdi.move_logo', /resize|transform|scale|larger|size/i, /recolour the numbers|make the numbers purple/i],
  ['Is there a way to view the other side of the car by rotating the preview?', 'flat', 'hdi.not_in_shokker', /not available|not in shokker/i, /rotate a pattern|zoom and move around/i],
  ['Can I zoom in on the flat-preview display without altering the saved paint?', 'flat', 'hdi.preview_bigger', /preview/i, /3d view is not available/i],
  ['My saved finish looks washed out in iRacing; what should I inspect?', 'flat', 'hdi.look_differs', /iracing|sim|sun|shadow|spec|render/i, /custom gradient|add a new logo/i],
  ['Is a 3D view of the complete vehicle available here, or is it a flat sheet?', 'flat', 'hdi.not_in_shokker', /not available|not in shokker/i, /zoom and move around|see the spec map/i],
  ['How can I turn the carbon pattern so the weave runs vertically?', 'flat', 'hdi.rotate_pattern', /rotate|rotation/i, /3d view is not available/i]
];
let checkCount = 0;
for (const [question, kind, cite, need, forbid] of helpCases) {
  const supplied = state(kind), before = JSON.stringify(supplied);
  const answer = world.SpbSelfHelp.handle(question, supplied);
  assert.ok(answer && answer.cites.includes(cite), `${question} should cite ${cite}; got ${answer && answer.cites}`);
  assert.match(answer.text, need, `${question} lacks its requested guidance`);
  assert.doesNotMatch(answer.text, forbid, `${question} received neighboring guidance`);
  assert.equal(JSON.stringify(supplied), before, 'supplied state stays untouched');
  checkCount++;
}
for (const command of [
  'Everything looks glossy; lower clearcoat on the roof only.',
  'I checked the finish. Reduce clearcoat on just the roof.'
]) {
  assert.equal(world.SpbSelfHelp.handle(command, state()), null, `edit command should remain with the action owner: ${command}`);
  checkCount++;
}
assert.equal(providerCalls, 0, 'all new cases remain offline');
console.log(`PASS W4 semantic contract: ${checkCount} action/entity, view-capability, and command-ownership checks`);
