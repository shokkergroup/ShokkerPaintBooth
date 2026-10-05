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

const flat = {
  paint: 'flat', layers: [], zones: [], selected: -1,
  carMap: { known: false, missing: [] }, mode: 'pro', last: null
};
const psd = {
  ...flat, paint: 'psd', layers: [{ name: 'Numbers' }, { name: 'Sponsors' }, { name: 'Body' }]
};
const help = (question, state = flat) => world.SpbSelfHelp.handle(question, state);
const cases = [
  ['How can I change the logo layer opacity?', psd, 'hdi.layer_opacity'],
  ['How can I scale number artwork?', psd, 'hdi.move_logo'],
  ['How do I locate Sponsors in a large PSD?', psd, 'hdi.find_layer'],
  ['How do I hide a PSD layer without deleting it?', psd, 'hdi.layer_visibility'],
  ['Where can I make the carbon texture finer?', flat, 'hdi.pattern_finer'],
  ['How can I turn the texture sideways?', flat, 'hdi.rotate_pattern'],
  ['How can I take the flame pattern off this zone?', flat, 'hdi.remove_pattern'],
  ['What does flattened paint versus a layered file mean?', flat, 'hdi.what_are_layers'],
  ['How do I put a metallic finish on the numbers?', psd, 'hdi.finish_numbers']
  ,['Could you show me the steps for opening a layered Photoshop design?', psd, 'hdi.load_psd']
  ,['Could you guide me through overlaying a second finish over the first?', flat, 'hdi.second_base']
  ,['How do I keep the wire and required guides out of my exported paint?', flat, 'hdi.template_layers_off']
];

for (const [question, state, expected] of cases) {
  const answer = help(question, state);
  assert.ok(answer && answer.cites.includes(expected), `${question} should route to ${expected}; got ${JSON.stringify(answer && answer.cites)}`);
}

const flatDefinition = help('What does flattened paint versus a layered file mean?');
assert.ok(!flatDefinition.cites.includes('hdi.merge_flatten'), 'a definition request should not give merge instructions');

const realisticState = {
  ...flat,
  zones: [{ name: 'Body', base: 'matte', colourMode: 'solid', colour: '#cc0000', muted: false }],
  selected: 0,
  carMap: { known: true, missing: [] }
};
for (const correction of [
  'The earlier answer missed the point. Make the sponsors silver instead.',
  'No, I meant silver sponsors, not a red body.'
]) {
  assert.equal(help(correction, realisticState), null, `a correction with a new desired result must return to the action owner: ${correction}`);
}

assert.equal(help('Make only the roof chrome and keep the rest as it is.', realisticState), null, 'a leading paint command must remain delegated');
assert.equal(help('Could you make the sponsors silver?', realisticState), null, 'a polite direct change request must remain delegated');
assert.equal(help('Full vehicle chrome, but do not touch the left side.', realisticState), null, 'a broad paint instruction with a protected exception must remain delegated');
assert.ok(help('Why did my body turn red when I changed the sponsor finish?', realisticState), 'a troubleshooting question without a correction command should remain help-owned');

console.log(`AI self-help semantic contract: ${cases.length + 1} intent checks and 6 command/help boundaries passed.`);
