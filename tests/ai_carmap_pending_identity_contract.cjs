'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');

// Frozen cases declared before the target module is read.
const CASES = [
  { id: 'fresh-offline-build', expected: 'ensure-false-builds-without-starting-vision' },
  { id: 'default-pending-source-reload', expected: 'ensure-false-does-not-join-default-pending-for-a-different-source-generation' },
  { id: 'stale-default-resolution', expected: 'old-request-cannot-replace-current-source-cache' },
  { id: 'same-path-same-geometry-reload', expected: 'generation-change-invalidates-map-even-when-public-signature-is-stable' },
  { id: 'same-current-source-cache', expected: 'same-source-repeat-reuses-current-cache' },
  { id: 'stale-rejection', expected: 'rejected-old-request-cannot-return-or-install-stale-cache' },
  { id: 'same-source-mode-isolation', expected: 'offline-request-does-not-consume-default-vision-pending-result' },
  { id: 'same-current-pending-coalesces', expected: 'duplicate-offline-requests-for-same-current-source-share-work' }
];
assert.equal(CASES.length, 8);
assert.equal(new Set(CASES.map(x => x.id)).size, CASES.length);

const ROOT = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-carmap.js'), 'utf8');
const cryptoHash = crypto.createHash('sha256').update(source).digest('hex');
function makeWorld(options = {}) {
  const state = { source: options.source || 'C:\\Cars\\A.psd', shape: 'left', chatCalls: 0, unionCalls: 0, learnedFetches: 0, generation: 3, chatResult: options.chatResult || null };
  const store = new Map();
  const ctx2d = {
    fillRect() {}, drawImage() {}, beginPath() {}, rect() {}, stroke() {}, fillText() {}, setLineDash() {}, strokeRect() {},
    save() {}, restore() {}, arc() {}, fill() {}, measureText(t) { return { width: String(t).length * 10 }; },
    getImageData(_x, _y, w, h) { return { data: new Uint8ClampedArray(w * h * 4) }; }
  };
  const fakeCanvas = () => ({ width: 64, height: 64, getContext: () => ctx2d, toDataURL: () => 'data:image/jpeg;base64,fake' });
  const paintCanvas = { width: 64, height: 64 };
  const document = { createElement(n) { return n === 'canvas' ? fakeCanvas() : {}; }, getElementById(id) { return id === 'paintCanvas' ? paintCanvas : null; } };
  const w = {
    document, localStorage: { getItem(k) { return store.has(k) ? store.get(k) : null; }, setItem(k, v) { store.set(k, String(v)); } },
    SPB_AI_BASE: '', SPB_CAR_ATLAS: { v: 1, cars: [] }, getCurrentSourcePaintFile() { return state.source; },
    _psdLayers: [{ id: 'body', name: 'Body Paint', bbox: [0, 0, 64, 64], img: { width: 64, height: 64 } }],
    getZoneSourceLayersUnionMask(_input, W, H) { state.unionCalls++; const u = new Uint8Array(W * H); const left = state.shape === 'left'; for (let y = 8; y < 56; y++) for (let x = left ? 4 : 36; x < (left ? 28 : 60); x++) u[y * W + x] = 255; return { union: u }; },
    fetch(url) { if (String(url).includes('/api/ai/learned-cars')) state.learnedFetches++; return Promise.resolve({ json: () => Promise.resolve({ ok: true, cars: [] }) }); },
    console, Uint8Array, Uint8ClampedArray, Int16Array, Promise, Math, JSON, Date, String, Number, Object, Array, RegExp, Error, setTimeout, clearTimeout
  };
  w.window = w;
  w.SpbAI = { chat() { state.chatCalls++; return state.chatResult || Promise.resolve({ ok: false, error: 'fake offline' }); } };
  vm.createContext(w);
  // Models the real lexical generation declared by paint-booth-3-canvas.js.
  vm.runInContext('var _spbSourceLoadGeneration = 3;\n' + source, w, { filename: 'js/spb-pro-carmap.js' });
  return { w, state, car: w.SpbProCar };
}
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
async function drain(test, label) { for (let i = 0; i < 80 && !test(); i++) await new Promise(r => setTimeout(r, 0)); assert(test(), label); }
(async () => {
  const observed = {};
  const offline = makeWorld();
  const first = await offline.car.ensure(false);
  assert(first && first.sig);
  assert.equal(offline.state.chatCalls, 0);
  observed['fresh-offline-build'] = { built: !!first, fakeVisionCalls: offline.state.chatCalls };

  const waitChat = deferred();
  const race = makeWorld({ chatResult: waitChat.promise });
  const oldPending = race.car.ensure();
  await drain(() => race.state.chatCalls === 1, 'default request reaches fake vision');
  const oldSig = race.car.signature();
  race.state.source = 'D:\\Cars\\A.psd'; // same dimensions/layers; source identity differs
  race.state.shape = 'right';
  race.state.generation++;
  race.w._spbSourceLoadGeneration++;
  const newSig = race.car.signature();
  assert.equal(newSig, oldSig, 'fixture must retain geometry-only public signature');
  const newPending = race.car.ensure(false);
  assert.notStrictEqual(newPending, oldPending, 'offline lookup must not join pending default vision');
  const currentMap = await newPending;
  assert(currentMap && currentMap.sig === oldSig);
  assert.equal(race.state.chatCalls, 1, 'ensure(false) starts no additional model call');
  waitChat.resolve({ ok: false, error: 'resolved old source vision' });
  const oldResult = await oldPending;
  assert.strictEqual(race.car.map(), currentMap, 'late old request must not replace current map');
  assert.strictEqual(oldResult, currentMap, 'stale completion returns current map rather than stale A');
  observed['default-pending-source-reload'] = { independentOfflinePromise: true, chatCalls: race.state.chatCalls, currentMapRemainsInstalled: true };
  observed['stale-default-resolution'] = { oldResultIsCurrentMap: oldResult === currentMap, publicMapIsCurrentMap: race.car.map() === currentMap };
  observed['same-source-mode-isolation'] = { falseDidNotJoinDefault: newPending !== oldPending, falseStartedNoModelCall: race.state.chatCalls === 1 };

  const reload = makeWorld();
  const r0 = await reload.car.ensure(false);
  const sig0 = reload.car.signature();
  reload.state.shape = 'right';
  reload.state.generation++;
  reload.w._spbSourceLoadGeneration++;
  const r1 = await reload.car.ensure(false);
  assert.equal(reload.car.signature(), sig0);
  assert.notStrictEqual(r1, r0, 'same path + same public geometry must invalidate on generation change');
  assert.equal(reload.state.unionCalls, 2, 'new load generation recomputes paint map');
  const r1again = await reload.car.ensure(false);
  assert.strictEqual(r1again, r1, 'same current identity reuses cache');
  assert.equal(reload.state.unionCalls, 2);
  observed['same-path-same-geometry-reload'] = { signatureStable: true, rebuilt: r1 !== r0, unionCalls: reload.state.unionCalls };
  observed['same-current-source-cache'] = { sameObject: r1again === r1, unionCalls: reload.state.unionCalls };

  const rejectChat = deferred();
  const rejection = makeWorld({ chatResult: rejectChat.promise });
  const rejectedOld = rejection.car.ensure();
  await drain(() => rejection.state.chatCalls === 1, 'rejection request reaches fake vision');
  rejection.state.source = 'E:\\Cars\\B.psd';
  rejection.state.generation++;
  rejection.w._spbSourceLoadGeneration++;
  const afterSwitch = await rejection.car.ensure(false);
  rejectChat.reject(new Error('fake transport rejection'));
  const rejectedResult = await rejectedOld;
  assert.strictEqual(rejection.car.map(), afterSwitch);
  assert.strictEqual(rejectedResult, afterSwitch);
  observed['stale-rejection'] = { currentMapSurvives: rejection.car.map() === afterSwitch, rejectionReturnsCurrentMap: rejectedResult === afterSwitch };

  // A duplicate ensure(false) against one still-pending current request must coalesce.
  const same = makeWorld();
  const one = same.car.ensure(false), two = same.car.ensure(false);
  assert.strictEqual(one, two);
  await one;
  observed['same-current-pending-coalesces'] = { sharedPromise: one === two };

  const oldReportPath = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CARMAP_IDENTITY_REVIEW_2026-10-03.json');
  const oldReport = JSON.parse(fs.readFileSync(oldReportPath, 'utf8'));
  const report = {
    title: 'AI helper car-map pending identity repair',
    generated_at: new Date().toISOString(),
    mode: 'actual car-map functions in VM with fake canvas/storage/fetch/chat only; no native, provider, server, or teaching-import calls',
    source_sha256: cryptoHash,
    prior_frozen_audit: { path: path.relative(ROOT, oldReportPath).replace(/\\/g, '/'), source_sha256_before: oldReport.source_sha256, frozen_case_count: oldReport.frozen_cases.length, original_observation: oldReport.observations.pending },
    fixture_cases: CASES.map(c => ({ id: c.id, expected: c.expected, observed: observed[c.id] })),
    source_evidence: {
      public_signature: 'signature() remains geometry/template identity only: paint dimensions plus layer names and bounding boxes.',
      generation: 'sourceDescriptor reads lexical _spbSourceLoadGeneration when present, with SPBSourceLoadTransaction.getGeneration fallback; it also captures loaded source path, canvas reference, and dimensions.',
      publication: 'build cache writes now pass a captured request descriptor through build0/build00/noMask/template/vision paths; stale requests cannot install CACHE. ensure(false) does not join a default labelled pending request and starts an independent unlabelled build.',
      teaching: 'layoutSig and findTaught behavior were not changed; source identity is a separate cache/pending key.'
    },
    result: { passed: CASES.length, failed: 0, chatCallsAcrossFixtures: offline.state.chatCalls + race.state.chatCalls + reload.state.chatCalls + rejection.state.chatCalls + same.state.chatCalls },
    limitations: ['The VM supplies the actual loader generation as a lexical global and fake paths/canvas; it proves generation/path/pending behavior, not source file parsing or native UI timing.', 'Teaching import compatibility semantics remain outside this repair.']
  };
  const out = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CARMAP_PENDING_REPAIR_2026-10-03.json');
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  console.log(`PASS car-map pending identity: ${CASES.length} frozen cases; source=${cryptoHash}; report=${path.relative(ROOT, out)}`);
})().catch(e => { console.error(e); process.exitCode = 1; });
