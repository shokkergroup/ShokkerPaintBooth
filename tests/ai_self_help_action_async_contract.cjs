'use strict';
// Isolated action lifecycle edges: clone identity fallback and async refresh replies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function load() {
  const w = {
    console, _spbLayerRev: 1, selectedZoneIndex: 1, _psdLayers: [],
    paintImageData: { width: 8, height: 8 },
    document: { body: { classList: { contains: () => false } } },
    zones: [
      { id: 'body-id', name: 'Body', muted: false },
      { id: 'hood-id', name: 'Hood', muted: true }
    ], calls: { mute: [], refresh: 0 }
  };
  w.window = w;
  w.SpbProCar = { map: () => ({}), missing: () => [], signature: () => 'paint-' + w._spbLayerRev };
  w.toggleZoneMute = i => { w.calls.mute.push(i); w.zones[i].muted = !w.zones[i].muted; };
  w.triggerPreviewRender = () => { w.calls.refresh++; };
  vm.createContext(w);
  for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
  }
  return w;
}
function offeredMute(w) {
  const a = w.SpbSelfHelp.answer('Why is my hood not changing colour?');
  assert.equal(a?.doIt?.act, 'unmute_zone');
  return a.doIt.label;
}
function offeredRefresh(w) {
  const a = w.SpbSelfHelp.answer('How do I refresh the preview?');
  assert.equal(a?.doIt?.act, 'refresh_preview');
  return a.doIt.label;
}

const w = load(), label = offeredMute(w), hoodClone = { ...w.zones[1] };
w.zones[1] = hoodClone;
w.zones.reverse();
const cloneResult = w.SpbSelfHelp.runDoIt(label);
assert.equal(cloneResult.done, true, 'unique UUID and expected name identify the replacement clone');
assert.equal(hoodClone.muted, false, 'the replacement clone is the object mutated');
assert.equal(w.zones[0], hoodClone, 'the identity-resolved target follows its new position');
assert.deepEqual(w.calls.mute, [0], 'controller receives the clone current index');

const ambiguous = load(), ambiguousLabel = offeredMute(ambiguous);
ambiguous.zones[1] = { ...ambiguous.zones[1] };
ambiguous.zones[0].id = 'hood-id';
const ambiguousResult = ambiguous.SpbSelfHelp.runDoIt(ambiguousLabel);
assert.equal(ambiguousResult.done, false, 'duplicate UUIDs cannot identify one target safely');
assert.deepEqual(ambiguous.calls.mute, [], 'ambiguous target does not reach the controller');

async function checkAsync(labelKind, settle) {
  const w = load(), label = offeredRefresh(w);
  let finish;
  w.triggerPreviewRender = () => {
    w.calls.refresh++;
    return new Promise((resolve, reject) => { finish = { resolve, reject }; });
  };
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false, labelKind + ' must not produce a synchronous Done result');
  assert.equal(r.pending, true, labelKind + ' must be represented as pending');
  assert.match(r.text, /cannot confirm when it finishes/i);
  assert.equal(w.calls.refresh, 1, 'the async callback is invoked once');
  settle(finish);
  await new Promise(resolve => setImmediate(resolve));
}

async function main() {
  const unhandled = [];
  const onUnhandled = reason => unhandled.push(reason);
  process.on('unhandledRejection', onUnhandled);
  try {
    await checkAsync('resolved-false callback', p => p.resolve(false));
    await checkAsync('rejected callback', p => p.reject(new Error('preview refused')));
    await checkAsync('resolved-success callback', p => p.resolve(true));
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(unhandled, [], 'thenable outcomes are consumed without unhandled rejections');
  } finally {
    process.removeListener('unhandledRejection', onUnhandled);
  }
  console.log('PASS self-help action async contract: clone reorder, ambiguous identity, and promise false/reject/success remain safe');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
