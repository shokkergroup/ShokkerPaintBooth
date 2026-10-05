'use strict';
// Executes the frozen W59 self-help body with the current source-load interface
// represented by controlled generation/path/fingerprint services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const frozen = path.join(root, '_easy_claude_work/ai14h_w59_candidate/js');

function load() {
  const w = { console, _spbLayerRev: 1, selectedZoneIndex: 1, _psdLayers: [],
    paintImageData: { width: 8, height: 8 },
    document: { body: { classList: { contains: () => false } } },
    zones: [{ id: 'body-id', name: 'Body', base: 'gloss' },
      { id: 'hood-id', name: 'Hood', base: 'gloss', muted: true, region: { x: 1, y: 2, w: 3, h: 4 } }],
    calls: { mute: [], select: [], refresh: 0 }, source: { generation: 7, committedGeneration: 7, loading: false, committed: true,
      path: 'C:/paint/car.tga', fingerprint: 'sha-a' } };
  w.window = w;
  w.SPBSourceLoadTransaction = {
    begin(requestedPath) { w.source.generation++; w.source.loading = true; w.source.committed = false; return { requestedPath, generation: w.source.generation }; },
    isCurrent(tx) { return !!tx && tx.generation === w.source.generation; },
    getGeneration: () => w.source.generation,
    getCommittedGeneration: () => w.source.committedGeneration,
    isLoading: () => w.source.loading,
    isCommitted: () => w.source.committed,
    getCommittedPath: () => w.source.path,
    getCommittedFingerprint: () => w.source.fingerprint
  };
  w.SpbProCar = { map: () => ({}), missing: () => [], signature: () => 'layout-' + w._spbLayerRev };
  w.selectZone = i => { w.calls.select.push(i); w.selectedZoneIndex = i; };
  w.toggleZoneMute = i => { w.calls.mute.push(i); w.zones[i].muted = !w.zones[i].muted; };
  w.triggerPreviewRender = () => { w.calls.refresh++; };
  vm.createContext(w);
  for (const f of ['spb-ai-knowledge.js', 'spb-self-help.js']) {
    const p = path.join(f === 'spb-ai-knowledge.js' ? frozen : frozen, f);
    vm.runInContext(fs.readFileSync(p, 'utf8'), w, { filename: p });
  }
  return w;
}
function offeredMute(w) {
  const a = w.SpbSelfHelp.answer('Why is my hood not changing colour?');
  assert.equal(a && a.doIt && a.doIt.act, 'unmute_zone', 'actual diagnosis offers target mutation');
  return a.doIt.label;
}
function check(name, fn) { try { fn(); return { name, pass: true }; } catch (e) { return { name, pass: false, error: e.message }; } }
const results = [];

results.push(check('source begins loading after action offer', () => {
  const w = load(), label = offeredMute(w); w.SPBSourceLoadTransaction.begin(w.source.path);
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0, 'old target must not mutate while a new source transaction is pending');
  assert.equal(r.done, false);
}));
results.push(check('source still loading when action is offered', () => {
  const w = load(); w.SPBSourceLoadTransaction.begin(w.source.path);
  const label = offeredMute(w);
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('failed load leaves original document at fresh generation', () => {
  const w = load(), label = offeredMute(w), oldPath = w.source.path, oldFp = w.source.fingerprint;
  const tx = w.SPBSourceLoadTransaction.begin('C:/paint/bad.tga');
  w.source.loading = false; w.source.committed = true; w.source.committedGeneration = tx.generation;
  const failed = { ok: false, generation: tx.generation, committedPath: oldPath, fingerprint: oldFp };
  assert.equal(failed.ok, false);
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0, 'action from before the failed-load generation must be invalidated');
  assert.equal(r.done, false);
  const fresh = offeredMute(w), ok = w.SpbSelfHelp.runDoIt(fresh);
  assert.equal(ok.done, true, 'same retained source can be acted on after a fresh diagnosis');
}));
results.push(check('same-path bytes replaced', () => {
  const w = load(), label = offeredMute(w); w.source.generation++; w.source.committedGeneration = w.source.generation; w.source.fingerprint = 'sha-b';
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0); assert.equal(r.done, false);
}));
results.push(check('legacy transaction without readiness cannot authorize a mutation', () => {
  const w = load(), label = offeredMute(w);
  w.SPBSourceLoadTransaction = { getGeneration: () => 7, getCommittedPath: () => w.source.path, getCommittedFingerprint: () => w.source.fingerprint };
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('target geometry moved in place', () => {
  const w = load(), label = offeredMute(w); w.zones[1].region.x = 99;
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(w.calls.mute.length, 0); assert.equal(r.done, false);
}));
results.push(check('target renamed', () => {
  const w = load(), label = offeredMute(w); w.zones[1].name = 'Rear wing';
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('target removed', () => {
  const w = load(), label = offeredMute(w); w.zones.splice(1, 1);
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('W3-compatible in-place reorder follows the same stable target', () => {
  const w = load(), label = offeredMute(w), hood = w.zones[1]; w.zones.reverse();
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, true); assert.equal(hood.muted, false); assert.deepEqual(w.calls.mute, [0]);
}));
results.push(check('W3-compatible same-ID Undo clone resolves safely', () => {
  const w = load(), label = offeredMute(w); w.zones[1] = { ...w.zones[1] };
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, true); assert.equal(w.zones[1].muted, false);
}));
results.push(check('duplicate stable ID while original object remains', () => {
  const w = load(), label = offeredMute(w); w.zones[0].id = 'hood-id';
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('missing stable ID', () => {
  const w = load(), label = offeredMute(w); delete w.zones[1].id;
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('manual layer visibility changes in place', () => {
  const w = load(); w._psdLayers = [{ id: 'body', name: 'Body', img: {}, visible: true }];
  const label = offeredMute(w); w._psdLayers[0].visible = false;
  assert.equal(w.SpbSelfHelp.runDoIt(label).done, false); assert.deepEqual(w.calls.mute, []);
}));
results.push(check('valid same-document target acts only after confirmed controller mutation', () => {
  const w = load(), label = offeredMute(w), r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, true); assert.deepEqual(w.calls.mute, [1]); assert.equal(w.zones[1].muted, false);
}));
results.push(check('passive guidance remains available before paint', () => {
  const w = load(); w.paintImageData = null; w.zones = []; w._psdLayers = [];
  assert.equal(w.SpbSelfHelp.state().paint, 'none');
  const a = w.SpbSelfHelp.answer('How do I add a metallic finish?');
  assert.ok(a && a.text && a.text.length > 0); assert.ok(Array.isArray(a.steps));
}));
results.push(check('controller failure never claims applied change', () => {
  const w = load(), label = offeredMute(w);
  w.toggleZoneMute = () => { throw new Error('controller rejected'); };
  const r = w.SpbSelfHelp.runDoIt(label);
  assert.equal(r.done, false); assert.match(r.text, /could not do that one myself/i);
}));

const bad = results.filter(x => !x.pass);
console.log(`W59 frozen helper: ${results.length - bad.length}/${results.length} fresh lifecycle checks passed`);
for (const x of results) console.log(`${x.pass ? 'PASS' : 'FAIL'} ${x.name}${x.error ? ` — ${x.error}` : ''}`);
if (bad.length) process.exitCode = 1;
