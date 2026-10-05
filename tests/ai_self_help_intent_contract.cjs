const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const world = { console };
vm.createContext(world);
world.window = world;
world.document = {};
for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), world, { filename: file });
}

const state = {
  paint: 'flat', layers: [], zones: [], selected: -1,
  carMap: { known: false, missing: [] }, mode: 'pro', last: null
};
const help = (question) => world.SpbSelfHelp.handle(question, state);
const commandState = {
  ...state,
  zones: [{ name: 'Body', base: 'gloss', colourMode: 'solid', colour: '#cc0000', muted: false }],
  selected: 0,
  carMap: { known: true, missing: [] }
};
const has = (answer, id) => answer && answer.cites.includes(id);

const cases = [
  ['Why do the shades look faded once I load the car in iRacing?', 'hdi.look_differs'],
  ["Why doesn't the live preview resemble my paint in the sim?", 'hdi.look_differs'],
  ['The number on my livery vanished after export.', 'hdi.number_type'],
  ['The render control is disabled.', 'hdi.render_wont_start'],
  ['How can I add a metallic fleck shimmer?', ['hdi.spec_overlay', 'zone_spec_pattern_stack']],
  ["I'd like my base to be matte black.", 'hdi.make_matte'],
  ['How can I reopen a saved paint file?', 'hdi.load_flat'],
  ['Can I recover a layer I removed by accident?', 'hdi.undo'],
  ['Why is this finish texture much too large?', ['hdi.pattern_finer', 'zone_pattern_scale', 'zone_base_scale']],
  ['My car appears black once it is in the sim.', 'hdi.not_in_iracing'],
  ['Can the assistant create a complete livery?', 'hdi.design_from_words']
];

for (const [question, expected] of cases) {
  const answer = help(question);
  const options = Array.isArray(expected) ? expected : [expected];
  assert.ok(answer && options.some((id) => has(answer, id)), `${question} should cite one of ${options.join(', ')}; got ${JSON.stringify(answer && answer.cites)}`);
}

const threeD = help('Can I see this car as a 3D model here?');
assert.ok(threeD && /not available in Shokker today/i.test(threeD.text), '3D requests should get a truthful limitation and next step');
assert.ok(/3D car view/i.test(threeD.text));
assert.ok(has(threeD, 'hdi.not_in_shokker'));

for (const order of ['make the hood black', 'matte black with orange pearl flakes']) {
  assert.equal(help(order), null, `self-help must leave this action/advisor phrase to its owner: ${order}`);
}
for (const correction of [
  'The first answer missed the point. Make the sponsors silver instead.',
  'No, I meant silver sponsors, not a red body.'
]) {
  assert.equal(world.SpbSelfHelp.handle(correction, commandState), null, `correction-plus-command must return to the action owner: ${correction}`);
}
assert.ok(world.SpbSelfHelp.handle('Why did my body turn red when I changed the sponsor finish?', commandState), 'a troubleshooting question without a correction command should remain help-owned');

assert.equal(help('The whole app slows down while I paint.'), null, 'do not present preview-refresh steps as a performance fix');
assert.equal(help('My sponsor logo looks pixelated.'), null, 'do not present spec rescue as an image-resolution fix');

console.log(`AI self-help intent contract: ${cases.length + 1} guidance checks and 4 routing boundaries passed.`);
