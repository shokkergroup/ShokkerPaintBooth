'use strict';

const assert = require('node:assert/strict');
require('../js/spb-pro-elements.js');

const elements = global.SpbProElements;
const width = 128;
const height = 128;
const resolution = 32;
const numberOffset = resolution * resolution;
const paint = new Uint8ClampedArray(width * height * 4);
const probabilities = new Float32Array(5 * resolution * resolution);
const oldProposal = [0.08, 0.08, 0.2, 0.2];
const currentNumber = [0.375, 0.375, 0.5, 0.5];

for (let i = 0; i < width * height; i++) {
  const offset = i * 4;
  paint[offset] = 30;
  paint[offset + 1] = 30;
  paint[offset + 2] = 30;
  paint[offset + 3] = 255;
}

// The current paint has number pixels at a new location; its detector also points there.
for (let y = 48; y < 64; y++) {
  for (let x = 48; x < 64; x++) {
    const offset = (y * width + x) * 4;
    paint[offset] = 245;
    paint[offset + 1] = 245;
    paint[offset + 2] = 245;
  }
}
for (let y = 12; y < 16; y++) {
  for (let x = 12; x < 16; x++) {
    probabilities[numberOffset + y * resolution + x] = 0.95;
  }
}

function inspect(learned) {
  return elements.summarise(paint, width, height, probabilities, resolution, null, learned);
}

function detectorState(result) {
  const numbers = result.result.kinds.numbers;
  return {
    found: numbers.found,
    share: numbers.share,
    groups: numbers.groups,
    boxes: numbers.boxes,
    colours: numbers.colours,
    conf: numbers.conf,
    mask: Array.from(result.masks.numbers),
  };
}

// A remembered box from another paint remains an explicit proposal and cannot create a find.
const noCurrentNumbers = new Float32Array(probabilities.length);
const absent = elements.summarise(paint, width, height, noCurrentNumbers, resolution, null, {
  numbers: { boxes: [oldProposal], how: 'server' },
});
assert.equal(absent.result.kinds.numbers.found, false);
assert.equal(absent.result.kinds.numbers.conf, 0);
assert.equal(absent.result.kinds.numbers.groups, 0);
assert.deepEqual(absent.result.kinds.numbers.boxes, []);
assert.deepEqual(absent.result.kinds.numbers.proposals, [{ box: oldProposal, provenance: 'server' }]);
assert.equal(absent.masks.numbers.some(Boolean), false);

// When the current paint has moved numbers, only the current detector box contributes to its mask.
const relocated = inspect({ numbers: { boxes: [oldProposal], how: 'confirm' } });
assert.equal(relocated.result.kinds.numbers.found, true);
assert.deepEqual(relocated.result.kinds.numbers.boxes, [currentNumber]);
assert.deepEqual(relocated.result.kinds.numbers.proposals[0].box, oldProposal);
const oldX = Math.floor(oldProposal[0] * width);
const oldY = Math.floor(oldProposal[1] * height);
assert.equal(relocated.masks.numbers[oldY * width + oldX], 0);
assert.ok(relocated.masks.numbers.some(Boolean));

// Other element kinds cannot inherit number-layout proposals.
const changedKind = inspect({ sponsors: { boxes: [oldProposal], how: 'confirm' } });
assert.deepEqual(changedKind.result.kinds.numbers.proposals, []);
assert.equal(changedKind.result.kinds.numbers.learned, false);

// Rejection removes the proposal without affecting the current-paint detector result.
const rejected = inspect({ numbers: { boxes: [oldProposal], how: 'confirm', status: 'rejected' } });
assert.deepEqual(rejected.result.kinds.numbers.proposals, []);
assert.deepEqual(detectorState(rejected), detectorState(inspect(null)));

// Repeated analysis of the unchanged paint preserves the same current-paint facts and proposal.
const repeated = inspect({ numbers: { boxes: [oldProposal], how: 'confirm' } });
assert.deepEqual(detectorState(repeated), detectorState(relocated));
assert.deepEqual(repeated.result.kinds.numbers.proposals, relocated.result.kinds.numbers.proposals);

console.log('AI element provenance contract passed (absent, relocated, kind change, rejection, unchanged paint).');
