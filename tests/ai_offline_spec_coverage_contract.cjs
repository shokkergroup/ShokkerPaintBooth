'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');
// W16 frozen before inspection of js/spb-pro-design.js. These are fresh
// mixed/contradictory spec-ownership counterexamples, separate from supplied P1.
const FROZEN_FRESH = [
  { id: 'black-weave-preserve', text: 'Make the hood matte black with a red carbon-weave overlay, but keep its current paint color.' },
  { id: 'base-plus-overlay-preserve', text: 'Make the roof satin blue with a gold weave overlay while keeping its present color.' },
  { id: 'recolor-plus-spec-preserve', text: 'Turn the trunk white and add a metallic flake overlay, but do not change the trunk paint.' },
  { id: 'contradict-color', text: 'Make the hood blue, and leave its existing color exactly as it is.' },
  { id: 'pattern-and-color-preserve', text: 'Give the spoiler a red base and a black carbon pattern while preserving its current color.' },
  { id: 'finish-and-extra-zone', text: 'Make only the roof matte, and add a gold pinstripe down the hood.' },
  { id: 'mixed-part-stack', text: 'Make the left side black with a red band, keep the paint colors, and put chrome on the spoiler.' },
  { id: 'finish-only-plus-recolor-tail', text: 'Change clearcoat on the hood and make its color bright yellow.' },
  { id: 'pattern-only-plus-paint-instruction', text: 'Add a pearl pattern to the roof, but repaint the body dark green without changing the roof color.' },
  { id: 'preserve-plus-color-palette', text: 'Keep the car colors unchanged; make the hood gloss black with a silver metallic stripe.' },
  { id: 'spec-overlay-with-source-color-conflict', text: 'Put a gold carbon overlay on the roof and make the roof red, while keeping its paint as-is.' },
  { id: 'single-target-plus-unowned-action', text: 'Make the hood satin and add black carbon weave to the roof, keeping the hood color.' },
  { id: 'recolor-with-explicit-keep', text: 'Paint the left side orange and add matte clearcoat, while keeping the left side its current color.' },
];

// Parent-supplied native C07 reproduction remains an independent fixture.
const OWNER_P1 = 'Make the roof matte black with a gold carbon-weave overlay, but keep its current paint color.';

assert.ok(FROZEN_FRESH.length >= 12, 'freeze at least twelve fresh cases before source inspection');
assert.ok(!FROZEN_FRESH.some(c => c.text === OWNER_P1), 'the owner-supplied P1 is separate from fresh cases');

const w = H.load();
const source = fs.readFileSync(path.join(__dirname, '..', 'js', 'spb-pro-design.js'), 'utf8');
vm.runInContext(source, w, { filename: 'js/spb-pro-design.js' });
const D = w.SpbProDesign;
assert.ok(D && typeof D.offlineSpec === 'function' && typeof D.compoundPlan === 'function');

const failures = [];
for (const c of FROZEN_FRESH) if (D.offlineSpec(c.text) !== null) failures.push(c.id);
if (D.offlineSpec(OWNER_P1) !== null) failures.push('owner-p1');

const finishOnly = D.offlineSpec('Make the roof matte.');
assert.ok(finishOnly && finishOnly.zones.length === 1, 'legitimate single finish-only ask stays supported');
assert.equal(finishOnly.zones[0].region.part, 'roof');
assert.equal(finishOnly.zones[0].color, 'source');
assert.equal(finishOnly.zones[0].finish, 'base::f_soft_matte');

const stackText = 'matte black on the roof only with a fine hex texture';
const fullStack = D.compoundPlan(stackText);
assert.ok(fullStack && fullStack.zones && fullStack.zones.length, 'a complete base-plus-spec stack stays with the compound planner');
assert.equal(D.offlineSpec(stackText), null, 'spec-only parser does not steal a full base-plus-spec stack');
assert.deepEqual(failures, [], `incomplete or contradictory instructions were claimed as spec-only: ${failures.join(', ')}`);

module.exports = { FROZEN_FRESH, OWNER_P1 };
console.log(`PASS ${FROZEN_FRESH.length} frozen mixed instructions, separate P1, finish-only, and full-stack ownership`);
