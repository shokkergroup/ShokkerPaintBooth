'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Frozen identity-policy cases: written before inspecting the car-map source.
// Metadata collisions are synthetic edge cases, not claims about any real car.
const CASES = [
  { id: 'same-loaded-source-reuses-cache', input: { source: 'A.psd', bytes: 'a', width: 2048, height: 2048 }, expected: 'reuse-cache-for-same-loaded-source' },
  { id: 'different-car-same-size-generic-layers', input: { source: 'B.psd', bytes: 'b', width: 2048, height: 2048, layerNames: ['Body', 'Decals'] }, expected: 'do-not-reuse-source-A-map-by-dimensions-or-generic-layers' },
  { id: 'changed-loaded-file-metadata', input: { source: 'A.psd', bytes: 'a2', width: 2048, height: 2048, mtime: 2 }, expected: 'invalidate-or-rekey-old-source-cache' },
  { id: 'loaded-source-vs-output-folder-label', input: { source: 'LoadedCar.psd', outputFolder: 'OtherCar', width: 2048, height: 2048 }, expected: 'loaded-paint-source-is-identity-authority' },
  { id: 'map-cache-bound-to-current-source', input: { source: 'A.psd', cachedSource: 'A.psd' }, expected: 'reuse-only-if-source-identity-matches' },
  { id: 'taught-parts-bound-to-current-source', input: { source: 'B.psd', taughtFor: 'A.psd' }, expected: 'do-not-apply-source-A-teaching-to-source-B' },
  { id: 'default-ensure-may-request-vision', input: { ensureArg: undefined, mapMissing: true, configured: true }, expected: 'may-invoke-recognition-path-once' },
  { id: 'ensure-false-is-offline', input: { ensureArg: false, mapMissing: true }, expected: 'must-not-invoke-recognition-or-provider-path' },
  { id: 'warmup-resolves-after-source-switch', input: { initialSource: 'A.psd', resolveSource: 'B.psd' }, expected: 'stale-A-result-not-installable-as-B-current-map' },
  { id: 'car-library-metadata-is-not-loaded-paint-identity', input: { source: 'LoadedTruck.psd', libraryLabel: 'Chevrolet Silverado', outputFolder: 'ARCA template' }, expected: 'keep-loaded-source-identity-separate-from-label-and-folder' },
  { id: 'persisted-learning-source-match', input: { source: 'A.psd', taughtFor: 'A.psd' }, expected: 'allow-only-source-matched-teaching' },
  { id: 'same-metadata-different-content', input: { source: 'C.psd', bytes: 'different', width: 2048, height: 2048, layerNames: ['Body', 'Decals'] }, expected: 'metadata-only-collision-must-not-prove-source-equivalence' }
];
assert(CASES.length >= 10, 'identity oracle must be frozen and nonempty before source inspection');
assert.equal(new Set(CASES.map(x => x.id)).size, CASES.length, 'identity oracle IDs must be unique');

const crypto = require('node:crypto');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-carmap.js'), 'utf8');

function makeWorld(options = {}) {
  const state = {
    source: options.source || 'C:\\Cars\\A.psd',
    output: options.output || 'C:\\Paints\\ARCA',
    shape: options.shape || 'left',
    unionCalls: 0,
    chatCalls: 0,
    learnedFetches: 0,
    chatResult: options.chatResult || null
  };
  const store = new Map();
  const canvasContext = {
    fillRect() {}, drawImage() {}, beginPath() {}, rect() {}, stroke() {}, fillText() {},
    setLineDash() {}, strokeRect() {}, save() {}, restore() {}, arc() {}, fill() {},
    measureText(text) { return { width: String(text).length * 10 }; },
    getImageData(_x, _y, w, h) { return { data: new Uint8ClampedArray(w * h * 4) }; }
  };
  const fakeCanvas = () => ({ width: 64, height: 64, getContext: () => canvasContext, toDataURL: () => 'data:image/jpeg;base64,fake' });
  const paintCanvas = { width: 64, height: 64 };
  const document = {
    createElement(name) { return name === 'canvas' ? fakeCanvas() : {}; },
    getElementById(id) { return id === 'paintCanvas' ? paintCanvas : id === 'outputDir' ? { value: state.output } : null; }
  };
  const w = {
    document,
    localStorage: { getItem(k) { return store.has(k) ? store.get(k) : null; }, setItem(k, v) { store.set(k, String(v)); } },
    SPB_AI_BASE: '', SPB_CAR_ATLAS: { v: 1, cars: [] },
    getCurrentSourcePaintFile() { return state.source; },
    _psdLayers: [{ id: 'body', name: 'Body Paint', bbox: [0, 0, 64, 64], img: { width: 64, height: 64 } }],
    getZoneSourceLayersUnionMask(_input, W, H) {
      state.unionCalls++;
      const union = new Uint8Array(W * H), left = state.shape === 'left';
      for (let y = 8; y < 56; y++) for (let x = (left ? 4 : 36); x < (left ? 28 : 60); x++) union[y * W + x] = 255;
      return { union };
    },
    fetch(url) {
      if (String(url).includes('/api/ai/learned-cars')) state.learnedFetches++;
      return Promise.resolve({ json: () => Promise.resolve({ ok: true, cars: [] }) });
    },
    console,
    Uint8Array, Uint8ClampedArray, Int16Array, Promise, Math, JSON, Date, String, Number, Object, Array, RegExp, Error,
    setTimeout, clearTimeout
  };
  w.window = w;
  w.SpbAI = { chat() { state.chatCalls++; return state.chatResult || Promise.resolve({ ok: false, error: 'offline fake' }); } };
  vm.createContext(w);
  vm.runInContext(source, w, { filename: 'js/spb-pro-carmap.js' });
  return { w, state, store, car: w.SpbProCar };
}
function defer() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
}
async function drainUntil(test, label) {
  for (let i = 0; i < 60 && !test(); i++) await new Promise(resolve => setTimeout(resolve, 0));
  assert(test(), `${label} did not reach its expected fake-I/O point`);
}

(async () => {
  const observed = {};
  const offline = makeWorld();
  const aSig = offline.car.signature();
  offline.state.source = 'D:\\DifferentCar\\B.psd';
  const bSig = offline.car.signature();
  assert.equal(aSig, bSig, 'path-only source change should expose signature inputs');
  const mapA = await offline.car.ensure(false);
  const callsAfterOffline = offline.state.chatCalls;
  assert.equal(callsAfterOffline, 0, 'fresh ensure(false) must not call fake vision');
  offline.state.shape = 'right';
  offline.state.source = 'E:\\Other\\C.psd';
  const mapB = await offline.car.ensure(false);
  assert.strictEqual(mapB, mapA, 'same signature currently reuses the previously cached map');
  assert.equal(offline.state.unionCalls, 1, 'cache hit should bypass recomputation despite synthetic content change');
  assert.equal(offline.car.folderKey(), 'arca', 'folderKey reads the output-directory label');
  assert.equal(offline.car.effFolder(), 'arca', 'with a usable paint layout signature, effFolder currently prefers output-folder key');
  observed.signature = { sameDimsLayerNamesBboxesDifferentPaths: aSig === bSig, cachedObjectReusedAfterSyntheticPaintChange: mapB === mapA, cachedSignature: mapB.sig, currentSignature: offline.car.signature() };
  observed.folder = { loadedSource: offline.state.source, outputDirectory: offline.state.output, folderKey: offline.car.folderKey(), effectiveFolder: offline.car.effFolder(), identityCaveat: 'output-folder result is not itself car recognition; atlas matching uses separate layout/folder corroboration' };
  observed.ensureFalse = { fakeVisionCalls: callsAfterOffline, freshMapBuilt: !!mapA && !mapA.note };

  const sourceDifference = makeWorld();
  await sourceDifference.car.ensure(false);
  const sigBeforeLayerName = sourceDifference.car.signature();
  sourceDifference.w._psdLayers[0].name = 'Body Paint alternate';
  assert.notEqual(sourceDifference.car.signature(), sigBeforeLayerName, 'layer-name change must affect signature');
  observed.signature.inputs = 'source path, bytes/pixels, mtime, and project/car id are absent; dimensions, layer names, and bboxes are included';

  const vision = makeWorld();
  await vision.car.ensure();
  assert.equal(vision.state.chatCalls, 1, 'default ensure should reach fake island-label vision path on an uncached detected map');
  observed.ensureDefault = { fakeVisionCalls: vision.state.chatCalls, fetchedLearningIndex: vision.state.learnedFetches };

  const pendingVision = defer();
  const race = makeWorld({ chatResult: pendingVision.promise });
  const pendingA = race.car.ensure();
  await drainUntil(() => race.state.chatCalls === 1, 'default ensure chat');
  const sigA = race.car.signature();
  race.state.source = 'D:\\NewSource\\B.psd';
  race.w._psdLayers[0].name = 'Body Paint B';
  const sigB = race.car.signature();
  assert.notEqual(sigA, sigB, 'race fixture must switch to a different signature');
  const pendingFalse = race.car.ensure(false);
  assert.strictEqual(pendingFalse, pendingA, 'ensure(false) currently joins an already pending labelled build');
  pendingVision.resolve({ ok: false, error: 'fake offline vision' });
  const staleResult = await pendingFalse;
  assert.equal(staleResult.sig, sigA);
  assert.notEqual(staleResult.sig, race.car.signature(), 'old-source build remains the map after source changed during pending work');
  const repaired = await race.car.ensure(false);
  assert.equal(repaired.sig, sigB, 'a subsequent ensure rebuilds against the new signature');
  observed.pending = { sourceASignature: sigA, sourceBSignature: sigB, resultAfterSwitch: staleResult.sig, ensureFalseJoinedDefault: true, subsequentEnsureSignature: repaired.sig };

  const taughtWorld = makeWorld();
  await taughtWorld.car.ensure(false);
  assert.equal(taughtWorld.car.setBox('hood', [0.1, 0.1, 0.3, 0.3]), true);
  const exported = taughtWorld.car.exportTaught();
  assert(exported && exported.layoutSig && exported.sheet);
  taughtWorld.state.source = 'D:\\Other\\NotSameCar.psd';
  taughtWorld.w._psdLayers[0].name = 'Body Paint Different Signature';
  await taughtWorld.car.ensure(false);
  const sameLayoutTeachingReused = !!(taughtWorld.car.map().boxes.hood && taughtWorld.car.map().boxes.hood.taught);
  assert(sameLayoutTeachingReused, 'layout-matched teaching should be discovered across a different exact layer signature');
  taughtWorld.state.source = 'F:\\ThirdSource\\C.psd';
  taughtWorld.state.shape = 'right';
  taughtWorld.w._psdLayers[0].name = 'Body Paint Third Signature';
  await taughtWorld.car.ensure(false);
  assert.equal(taughtWorld.car.map().boxes.hood, undefined, 'a dissimilar layout should not receive source A teaching automatically');
  const importCount = taughtWorld.car.importTaught(exported);
  assert.equal(importCount, 1, 'manual import accepts a valid-format map without source/layout compatibility check');
  assert.equal(taughtWorld.car.map().boxes.hood.taught, true);
  observed.teaching = { exportCarries: ['car', 'layoutSig', 'folder', 'sheet'], sameLayoutAcrossSourcePathAutomaticallyReuses: sameLayoutTeachingReused, dissimilarLayoutDoesNotAutomaticallyReuse: true, importFormatChecked: true, importChecksCurrentIdentity: false, importIsExplicitUserAction: true };

  const persistence = makeWorld();
  await persistence.car.ensure(false);
  assert.equal(persistence.car.setBox('roof', [0.4, 0.1, 0.6, 0.3]), true);
  persistence.car._reset();
  const persistedMap = await persistence.car.ensure(false);
  assert(persistedMap.boxes.roof && persistedMap.boxes.roof.taught, 'same exact layer signature should reload its locally persisted taught box');
  observed.sameSignaturePersistence = { taughtRoofRestored: true, keying: 'localStorage entry uses the source signature; signature is dimensions + layer names + bboxes' };

  const aliasWorld = makeWorld();
  assert.equal(aliasWorld.car.canon('bonnet'), 'hood');
  assert.equal(aliasWorld.car.canon('passenger side'), 'right side');
  observed.canonicalAliases = { bonnet: 'hood', 'passenger side': 'right side' };

  const caseFindings = {
    'same-loaded-source-reuses-cache': 'same signature takes cache-hit path; normal behavior',
    'different-car-same-size-generic-layers': 'synthetic paths/content change with same dimensions/layer tuple yield same signature and reuse cache; proves signature behavior only, not a real-car collision',
    'changed-loaded-file-metadata': 'path, bytes, and mtime are absent from signature inputs; no real file metadata collision asserted',
    'loaded-source-vs-output-folder-label': 'folderKey reads outputDir; effFolder prefers it when layoutSig is usable, but this alone does not control atlas recognition',
    'map-cache-bound-to-current-source': 'ensure(false) reused the exact cached map after synthetic current source and mask changed with same signature',
    'taught-parts-bound-to-current-source': 'teaching is reused across distinct signatures when layoutSig similarity meets threshold; dissimilar test layout is not reused; manual import bypasses compatibility checks',
    'default-ensure-may-request-vision': 'default ensure made one call to the fake SpbAI.chat stub on a newly detected uncached map',
    'ensure-false-is-offline': 'fresh ensure(false) made zero fake SpbAI.chat calls',
    'warmup-resolves-after-source-switch': 'ensure(false) joined pending default ensure; pending result for signature A remained cached after source changed to signature B until next ensure',
    'car-library-metadata-is-not-loaded-paint-identity': 'identity fields remain separate; no real atlas/native recognition assertion was made',
    'persisted-learning-source-match': 'same exact signature reloads taught boxes from localStorage',
    'same-metadata-different-content': 'different synthetic paint-mask content under same layer tuple hit cache and skipped mask recomputation'
  };
  const cases = CASES.map(c => ({ id: c.id, expected: c.expected, observed: caseFindings[c.id] }));
  const report = {
    title: 'AI helper car-map identity review',
    generated_at: new Date().toISOString(),
    mode: 'read-only source audit and actual-function VM checks with fake canvas/storage/fetch/chat; no native application or external calls',
    source_sha256: crypto.createHash('sha256').update(source).digest('hex'),
    source_evidence: {
      signature: 'js/spb-pro-carmap.js function signature(): paint dimensions and layer name + bbox tuples; excludes source path, source bytes/pixels, modification time, and explicit vehicle id.',
      cache_hit: 'build00() reuses CACHE when CACHE.sig === signature() and labels are not required (lines 505-507 at audit time).',
      pending: 'ensure() returns PENDING before comparing current signature; a pending default labelled build is shared with ensure(false).',
      layout_and_teaching: 'layoutSig is a 32x32 thresholded paintable-area fingerprint. findTaught first uses exact layer signature, then reuses teaching at layout similarity >= 0.92. This is intentional cross-paint template reuse, not proof that two different real cars collide.',
      import_export: 'exportTaught carries car/layoutSig/folder/sheet/parts. importTaught validates only format and parts shape, then calls setBox on the current CACHE; imported maps are explicit user actions but source/layout compatibility is not checked.',
      source_loader: 'paint-booth-3-canvas.js getCurrentSourcePaintFile prefers _psdPath, then committed source path, then paintFile input. The car-map signature does not consume this value. No direct SpbProCar._reset caller was found in js/; js/spb-chat-studio.js calls ensure(false) on panel open.'
    },
    observations: observed,
    frozen_cases: cases,
    limitations: [
      'Different path/same metadata and changed synthetic mask prove the cache-key behavior, not a wrong real vehicle mask. No real Chevrolet/ARCA identity conflict is alleged; owner-confirmed Silverado recognition remains authoritative.',
      'The car atlas separately uses layout similarity and folder corroboration/proposal rules. This audit did not mutate the atlas or infer a real car from synthetic source labels.',
      'Fake vision chat only counted calls and returned a stub error; no provider was reached.'
    ]
  };
  const out = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CARMAP_IDENTITY_REVIEW_2026-10-03.json');
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  assert.equal(cases.length, CASES.length);
  console.log(`PASS car-map identity review: ${CASES.length} frozen scenarios; fake vision calls observed only on default path; report=${path.relative(ROOT, out)}`);
})().catch(e => { console.error(e); process.exitCode = 1; });
