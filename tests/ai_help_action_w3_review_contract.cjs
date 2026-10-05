'use strict';
// Independent W3 review: executes the real helper in a small VM app boundary.
// This deliberately covers cases not asserted by the producer lifecycle contract.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function load(opts = {}) {
  const classes = new Set(opts.classes || []);
  const w = {
    console, _spbLayerRev: 1, selectedZoneIndex: 1, _psdLayers: [],
    paintImageData: { width: 8, height: 8 },
    document: { body: { classList: { contains: name => classes.has(name) } } },
    zones: [
      { id: 'body-id', name: 'Body', base: 'gloss', colorMode: 'special', baseColorMode: 'solid' },
      { id: 'hood-id', name: 'Hood', base: 'gloss', colorMode: 'special', baseColorMode: 'solid', muted: true }
    ],
    calls: { mute: [], select: [], refresh: 0 }
  };
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
function offeredMute(w) {
  const a = w.SpbSelfHelp.answer('Why is my hood not changing colour?');
  assert.equal(a?.doIt?.act, 'unmute_zone');
  return a.doIt.label;
}
function offeredRefresh(w) {
  const a = w.SpbSelfHelp.answer('How do I fix a stuck or blank preview?');
  assert.equal(a?.doIt?.act, 'refresh_preview');
  return a.doIt.label;
}
const passed = [];
const failures = [];
function check(name, fn) { try { fn(); passed.push(name); } catch (e) { failures.push(name + ': ' + e.message); } }

check('reordered object identity resolves current index', () => {
  const w = load(), label = offeredMute(w), hood = w.zones[1];
  w.zones.reverse();
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, true); assert.equal(hood.muted, false);
  assert.deepEqual(w.calls.mute, [0]);
});
check('same-UUID same-name replacement clone is treated as Undo-restored target', () => {
  const w = load(), label = offeredMute(w);
  w.zones[1] = { ...w.zones[1] };
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, true); assert.equal(w.zones[1].muted, false);
  assert.deepEqual(w.calls.mute, [1]);
});
check('identity-free replacement clone is rejected', () => {
  const w = load(), label = offeredMute(w), hood = { name: 'Hood', muted: true };
  w.zones[1] = hood;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.equal(hood.muted, true);
  assert.deepEqual(w.calls.mute, []);
});
check('document replacement invalidates the offered action', () => {
  const w = load(), label = offeredMute(w);
  w.zones = [{ name: 'New body', muted: false }, { name: 'New hood', muted: true }];
  w.paintImageData = { width: 8, height: 8 }; w._spbLayerRev++;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.equal(w.zones[1].muted, true);
  assert.deepEqual(w.calls.mute, []);
});
check('removed target is rejected', () => {
  const w = load(), label = offeredMute(w);
  w.zones.splice(1, 1);
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.deepEqual(w.calls.mute, []);
});
check('renamed target is rejected', () => {
  const w = load(), label = offeredMute(w);
  w.zones[1].name = 'Rear wing';
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.equal(w.zones[1].muted, true);
  assert.deepEqual(w.calls.mute, []);
});
check('duplicate UUID ambiguity is rejected', () => {
  const w = load(), label = offeredMute(w);
  w.zones[0].id = 'hood-id';
  w.zones[1] = { ...w.zones[1] };
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.deepEqual(w.calls.mute, []);
});
check('successful callback cannot be replayed', () => {
  const w = load(), label = offeredMute(w);
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, true);
  assert.equal(w.SpbSelfHelp.runDoIt(label), null);
  assert.deepEqual(w.calls.mute, [1]);
});
check('throwing callback is reported as unconfirmed and one-shot', () => {
  const w = load(), label = offeredMute(w);
  w.toggleZoneMute = () => { throw new Error('controller failed'); };
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.match(r.text, /could not do that one myself/);
  assert.equal(w.SpbSelfHelp.runDoIt(label), null);
});
check('missing action callback is reported as unavailable', () => {
  const w = load(), label = offeredMute(w);
  delete w.toggleZoneMute;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.equal(w.zones[1].muted, true);
});
check('explicit preview refusal is not reported as success', () => {
  const w = load(), label = offeredRefresh(w);
  w.triggerPreviewRender = () => { w.calls.refresh++; return false; };
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.equal(w.calls.refresh, 1);
});
check('new non-help input invalidates old action', () => {
  const w = load(), label = offeredMute(w);
  assert.equal(w.SpbSelfHelp.answer('Make the body silver.'), null);
  assert.equal(w.SpbSelfHelp.runDoIt(label), null);
  assert.deepEqual(w.calls.mute, []);
});
check('mixed Chat Studio and Easy body classes retain Easy state precedence', () => {
  const w = load({ classes: ['spb-chat-studio', 'spb-easy-on'] });
  assert.equal(w.SpbSelfHelp.state().mode, 'easy');
});
check('Chat Studio Pro HOWTO offers visible Full editor handoff', () => {
  const w = load({ classes: ['spb-chat-studio'] });
  const a = w.SpbSelfHelp.answer('How do I see the keyboard shortcuts?');
  assert.match(a.text, /Full editor →/);
  assert.match(a.text, /Settings|Keyboard Shortcuts|\?/);
});
check('Chat Studio selected-zone overview teaches both handoff and in-chat change', () => {
  const w = load({ classes: ['spb-chat-studio'] });
  const a = w.SpbSelfHelp.handle('What can I do with this zone?');
  assert.match(a.text, /Full editor →/);
  assert.match(a.text, /tell me \("make this zone candy red"/);
});

// A promise-returning renderer is an important async boundary. Record actual
// behavior as a diagnostic so the report can distinguish expectation from code.
{
  const w = load(), label = offeredRefresh(w);
  let rejectRefresh;
  w.triggerPreviewRender = () => { w.calls.refresh++; return new Promise(resolve => { rejectRefresh = resolve; }); };
  const r = w.SpbSelfHelp.runDoIt(label);
  const earlyDone = r.done === true;
  rejectRefresh(false);
  console.log('ASYNC_PROBE ' + JSON.stringify({ earlyDone, text: r.text, promiseSettledFalse: true }));
}

console.log((failures.length ? 'FAIL' : 'PASS') + ' independent W3 review cases: ' + passed.length + ' passed, ' + failures.length + ' failed');
console.log(passed.map(x => ' - ' + x).join('\n'));
if (failures.length) {
  console.error(failures.map(x => ' - ' + x).join('\n'));
  process.exitCode = 1;
}
