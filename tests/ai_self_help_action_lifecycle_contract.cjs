'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
function load() {
  const w = { console, _spbLayerRev: 1, selectedZoneIndex: 1, _psdLayers: [],
    paintImageData: { width: 8, height: 8 }, document: { body: { classList: { contains: () => false } } },
    zones: [{ name: 'Body', base: 'gloss', colorMode: 'special', baseColorMode: 'solid' },
      { name: 'Hood', base: 'gloss', colorMode: 'special', baseColorMode: 'solid', muted: true }],
    calls: { select: [], mute: [], refresh: 0 } };
  w.window = w;
  w.SpbProCar = { map: () => ({}), missing: () => [], signature: () => 'paint-' + w._spbLayerRev };
  w.selectZone = i => { w.calls.select.push(i); w.selectedZoneIndex = i; };
  w.toggleZoneMute = i => { w.calls.mute.push(i); w.zones[i].muted = !w.zones[i].muted; };
  w.triggerPreviewRender = () => { w.calls.refresh++; };
  vm.createContext(w);
  for (const f of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), w, { filename: f });
  }
  return w;
}
function unmuteQuestion(w) {
  const answer = w.SpbSelfHelp.answer('Why is my hood not changing colour?');
  assert.equal(answer.doIt.act, 'unmute_zone', 'actual diagnosis offers unmute');
  return answer.doIt.label;
}
const failures = [];
function check(name, fn) { try { fn(); } catch (e) { failures.push(name + ': ' + e.message); } }
check('valid current-paint unmute', () => {
  const w = load(), label = unmuteQuestion(w), r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, true); assert.equal(w.zones[1].muted, false);
  assert.equal(w.calls.mute.length, 1);
});
check('old action after document replacement', () => {
  const w = load(), label = unmuteQuestion(w);
  w.zones = [{ name: 'New body' }, { name: 'New sponsors', muted: true }];
  w.paintImageData = { width: 8, height: 8 }; w._spbLayerRev++;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0, 'must not toggle the new document at the old index');
  assert.equal(r.done, false, 'must explain that the old action is unavailable');
});
check('old action after target removal', () => {
  const w = load(), label = unmuteQuestion(w); w.zones.splice(1, 1);
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0);
  assert.equal(r.done, false, 'a missing zone cannot be reported as switched on');
});
check('old action after zone reorder', () => {
  const w = load(), label = unmuteQuestion(w), hood = w.zones[1];
  w.zones.reverse(); w.zones[1].muted = true;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.zones[1].muted, true, 'must not unmute a different zone at the old index');
  assert.equal(r.done, true, 'an object-identical target may be safely resolved after an in-place reorder');
  assert.equal(hood.muted, false, 'a resolved action must act on its original target');
  assert.deepEqual(w.calls.mute, [0], 'the moved target current index is passed to the controller');
});
check('old action after target rename', () => {
  const w = load(), label = unmuteQuestion(w); w.zones[1].name = 'Rear wing';
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0, 'a renamed target no longer matches the offered action');
  assert.equal(r.done, false);
});
check('unmute action without controller', () => {
  const w = load(), label = unmuteQuestion(w); delete w.toggleZoneMute;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.zones[1].muted, true);
  assert.equal(r.done, false, 'a missing callback cannot be reported as an unmute');
});
check('selection action without controller', () => {
  const w = load(); w.selectedZoneIndex = -1;
  const answer = w.SpbSelfHelp.answer('How do I change the order or priority of zones?');
  assert.equal(answer.doIt.act, 'select_zone'); delete w.selectZone;
  const r = w.SpbSelfHelp.runDoIt(answer.doIt.label);
  assert.equal(w.selectedZoneIndex, -1); assert.equal(r.done, false);
});
check('refresh action without controller', () => {
  const w = load(), answer = w.SpbSelfHelp.answer('How do I refresh the preview?');
  delete w.triggerPreviewRender;
  const r = w.SpbSelfHelp.runDoIt(answer.doIt.label);
  assert.equal(w.calls.refresh, 0); assert.equal(r.done, false);
});
check('refresh action refused by controller', () => {
  const w = load(), answer = w.SpbSelfHelp.answer('How do I refresh the preview?');
  w.triggerPreviewRender = () => { w.calls.refresh++; return false; };
  const r = w.SpbSelfHelp.runDoIt(answer.doIt.label);
  assert.equal(w.calls.refresh, 1); assert.equal(r.done, false, 'an explicit controller refusal cannot be reported as a refresh');
});
check('non-help input invalidates a pending action', () => {
  const w = load(), answer = w.SpbSelfHelp.answer('Why is my hood not changing colour?');
  assert.equal(w.SpbSelfHelp.answer('Make the body silver.'), null);
  assert.equal(w.SpbSelfHelp.runDoIt(answer.doIt.label), null, 'a prior help action cannot survive a newer non-help input');
});
check('refresh action after paint disappears', () => {
  const w = load(); w.zones[1].muted = false;
  const answer = w.SpbSelfHelp.answer('How do I refresh the preview?');
  assert.equal(answer.doIt.act, 'refresh_preview', 'actual help offers refresh');
  w.paintImageData = null; w._spbLayerRev++;
  const r = w.SpbSelfHelp.runDoIt(answer.doIt.label);
  assert.equal(w.calls.refresh, 0, 'must not promise preview work on the departed paint');
  assert.equal(r.done, false);
});
assert.deepEqual(failures, [], 'self-help action lifecycle violations:\n' + failures.join('\n'));
console.log('PASS self-help actions: current target, replacement, removal/rename, reorder, missing paint/callback and one-shot cleanup');
