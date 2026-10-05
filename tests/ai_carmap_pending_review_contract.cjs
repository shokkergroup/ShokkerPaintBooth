'use strict';
// SOL xhigh W13 independent review: scenario oracle frozen before source reads.
// Actual-function harness and fake I/O are added after inspecting bounded source.
const ORACLE = Object.freeze({
  sourceSha256: 'bb9e05373c11550d59155fc680d3771c8ca31de555726bb1219125159be505ce',
  scenarios: Object.freeze([
    { id: 'old-mask-after-new-source', expect: 'A mask response cannot replace B current mask or metadata' },
    { id: 'vision-pending-versus-offline-ensure', expect: 'ensure(false) never treats an unproved pending vision guess as installed current map' },
    { id: 'same-path-generation-reload', expect: 'a new source-load generation invalidates a same-path pending request' },
    { id: 'old-failure-after-new-install', expect: 'A failure does not clear or demote installed B state' },
    { id: 'layer-recomposite-same-source', expect: 'same-generation same-path layered recompositing remains the same source for pending layout work' },
    { id: 'matching-pending-request-reuse', expect: 'same-source compatible ensures share pending work without duplicate installation' },
    { id: 'explicit-layout-teaching-reuse', expect: 'intentional teaching/layout reuse remains available without stale automatic publication' }
  ])
});
module.exports.ORACLE = ORACLE;

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const SOURCE_PATH = path.join(ROOT, 'js', 'spb-pro-carmap.js');
const REPORT_PATH = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CARMAP_PENDING_REVIEW_2026-10-03.json');
const digest = text => crypto.createHash('sha256').update(text).digest('hex');
const source = fs.readFileSync(SOURCE_PATH, 'utf8');
assert.equal(digest(source), ORACLE.sourceSha256, 'production source matches independently pinned promotion input');
assert.equal(new Set(ORACLE.scenarios.map(x => x.id)).size, 7);

function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
async function drain(predicate, label) { for (let i = 0; i < 80 && !predicate(); i++) await new Promise(r => setTimeout(r, 0)); assert(predicate(), label); }

function world({ template = false } = {}) {
  const state = { path: 'C:\\Review\\A.psd', shape: 'left', generation: 31, unionCalls: 0, learnedCalls: 0, chatCalls: 0, masks: [], images: [], chat: deferred() };
  const store = new Map();
  function canvas() {
    const out = { width: 64, height: 64 };
    let drawn = null;
    const cx = {
      drawImage(image) { drawn = image; }, fillRect() {}, beginPath() {}, rect() {}, stroke() {}, fillText() {},
      setLineDash() {}, strokeRect() {}, save() {}, restore() {}, arc() {}, fill() {}, measureText(t) { return { width: String(t).length * 10 }; },
      getImageData(_x, _y, W, H) {
        const data = new Uint8ClampedArray(W * H * 4);
        if (drawn && drawn.payload) {
          const left = drawn.payload === 'mask-A';
          for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
            const inner = y > H * 0.12 && y < H * 0.88 && x > W * (left ? 0.08 : 0.58) && x < W * (left ? 0.38 : 0.88);
            const n = (y * W + x) * 4; data[n] = data[n + 1] = data[n + 2] = inner ? 0 : 255; data[n + 3] = 255;
          }
        }
        return { data };
      }
    };
    out.getContext = () => cx; out.toDataURL = () => 'data:image/jpeg;base64,review';
    return out;
  }
  const paintCanvas = canvas();
  const body = { id: 'body', name: 'Body Paint', bbox: [0, 0, 64, 64], img: { width: 64, height: 64 } };
  const layers = template ? [body, { id: 'mask', name: 'Mask', bbox: [0, 0, 64, 64], img: { width: 64, height: 64 } }] : [body];
  function FakeImage() { this.width = this.height = 256; }
  Object.defineProperty(FakeImage.prototype, 'src', { set(value) { this.payload = String(value).split(',').pop(); state.images.push(this); } });
  const w = {
    console, Uint8Array, Uint8ClampedArray, Int16Array, Float32Array, Promise, Math, JSON, Date, String, Number, Object, Array, RegExp, Error, setTimeout, clearTimeout,
    Image: FakeImage, document: { createElement: n => n === 'canvas' ? canvas() : {}, getElementById: id => id === 'paintCanvas' ? paintCanvas : null },
    localStorage: { getItem: k => store.get(k) || null, setItem: (k, v) => store.set(k, String(v)) },
    SPB_AI_BASE: '', SPB_CAR_ATLAS: { v: 1, cars: [] }, _psdLayers: layers, _psdPath: state.path,
    paintImageData: { width: 64, height: 64, data: new Uint8ClampedArray(64 * 64 * 4) }, _spbLayerRev: 1,
    getCurrentSourcePaintFile: () => state.path,
    getZoneSourceLayersUnionMask(_input, W, H) {
      state.unionCalls++; const union = new Uint8Array(W * H); const left = state.shape === 'left';
      for (let y = 8; y < 56; y++) for (let x = left ? 4 : 36; x < (left ? 28 : 60); x++) union[y * W + x] = 255;
      return { union };
    },
    fetch(url) {
      if (String(url).includes('/api/ai/template-mask')) { const req = deferred(); state.masks.push({ url, req }); return req.promise; }
      if (String(url).includes('/api/ai/learned-cars')) { state.learnedCalls++; return Promise.resolve({ json: () => Promise.resolve({ ok: true, cars: [] }) }); }
      throw new Error('unexpected fake fetch: ' + url);
    },
    SpbAI: { chat() { state.chatCalls++; return state.chat.promise; } }
  };
  w.window = w; vm.createContext(w);
  // Execute the complete actual production module unchanged. I/O surfaces alone are fake.
  vm.runInContext('var _spbSourceLoadGeneration = 31;\n' + source, w, { filename: 'actual-spb-pro-carmap.js' });
  return {
    w, state, car: w.SpbProCar,
    switchSource(pathValue = 'C:\\Review\\B.psd') { state.path = pathValue; w._psdPath = pathValue; state.shape = 'right'; state.generation++; w._spbSourceLoadGeneration++; },
    replyMask(index, payload) { state.masks[index].req.resolve({ json: () => Promise.resolve({ ok: true, found: { mask: true, wire: false }, mask: payload }) }); },
    async decode(payload) { await drain(() => state.images.some(i => i.payload === payload), 'fake decoder requested ' + payload); const image = state.images.find(i => i.payload === payload); image.onload(); }
  };
}

async function main() {
  const rows = [];
  async function scenario(id, run) { try { rows.push({ id, verdict: 'pass', ...await run() }); } catch (error) { rows.push({ id, verdict: 'fail', error: String(error.stack || error) }); } }

  await scenario('old-mask-after-new-source', async () => {
    const h = world({ template: true }); const A = h.car.ensure(false);
    await drain(() => h.state.masks.length === 1, 'A mask request begins'); h.replyMask(0, 'mask-A');
    await drain(() => h.state.images.some(i => i.payload === 'mask-A'), 'A decoder remains pending');
    h.switchSource(); const B = h.car.ensure(false); await drain(() => h.state.masks.length === 2, 'B mask request begins');
    h.replyMask(1, 'mask-B'); await h.decode('mask-B'); const mapB = await B;
    assert(mapB && mapB.islands.length > 0, 'B real mask decoder/build installed islands');
    const bin = Array.from(h.car._paintable() || []); assert(bin.some(Boolean), 'B paintable state is nonempty');
    await h.decode('mask-A'); const oldReturn = await A;
    assert.strictEqual(h.car.map(), mapB); assert.strictEqual(oldReturn, mapB);
    assert.deepEqual(Array.from(h.car._paintable() || []), bin, 'late A decode cannot replace B paintable mask');
    return { fakeMaskRequests: h.state.masks.length, fakeImageDecodes: h.state.images.length, currentMapPreserved: true, currentMaskPreserved: true };
  });

  await scenario('vision-pending-versus-offline-ensure', async () => {
    const h = world(); const A = h.car.ensure(); await drain(() => h.state.chatCalls === 1, 'default ensure reaches fake vision');
    const B = h.car.ensure(false); assert.notStrictEqual(A, B); const map = await B;
    assert(map && map.labelled === false, 'offline result remains unlabelled'); assert.equal(h.state.chatCalls, 1);
    h.state.chat.resolve({ ok: false, error: 'fake no labels' }); await A;
    return { distinctPromise: true, offlineUnlabelled: true, additionalFakeVisionCalls: 0 };
  });

  await scenario('same-path-generation-reload', async () => {
    const h = world(); const A = h.car.ensure(); await drain(() => h.state.chatCalls === 1, 'A pending vision');
    const sig = h.car.signature(); h.switchSource(h.state.path); const mapB = await h.car.ensure(false);
    assert.equal(h.car.signature(), sig, 'geometry signature unchanged'); assert.equal(h.state.unionCalls, 2, 'generation forces new build');
    h.state.chat.resolve({ ok: false, error: 'old same-path response' }); assert.strictEqual(await A, mapB); assert.strictEqual(h.car.map(), mapB);
    return { generationInvalidatesPending: true, publicSignatureStable: true, currentMapPreserved: true };
  });

  await scenario('old-failure-after-new-install', async () => {
    const h = world({ template: true }); const A = h.car.ensure(false); await drain(() => h.state.masks.length === 1, 'A failing mask pending');
    h.switchSource(); const B = h.car.ensure(false); await drain(() => h.state.masks.length === 2, 'B mask pending');
    h.replyMask(1, 'mask-B'); await h.decode('mask-B'); const mapB = await B; const bin = Array.from(h.car._paintable() || []);
    h.state.masks[0].req.reject(new Error('fake A fetch rejected')); assert.strictEqual(await A, mapB);
    assert.strictEqual(h.car.map(), mapB); assert.deepEqual(Array.from(h.car._paintable() || []), bin);
    return { lateFailurePreservesMapAndMask: true };
  });

  await scenario('layer-recomposite-same-source', async () => {
    const h = world(); const A = h.car.ensure(); await drain(() => h.state.chatCalls === 1, 'vision starts before recomposite');
    h.w.paintImageData = { width: 64, height: 64, data: new Uint8ClampedArray(64 * 64 * 4) }; h.w._spbLayerRev++;
    const same = h.car.ensure(); assert.strictEqual(same, A, 'legitimate same-source recomposite retains pending identity');
    h.state.chat.resolve({ ok: false, error: 'fake vision unavailable' }); const map = await A;
    assert(map && h.car.map() === map); assert.equal(h.state.unionCalls, 1); assert.equal(h.state.chatCalls, 1);
    return { compositeReferenceIgnoredForSourceIdentity: true, layerRevisionIgnoredForSourceIdentity: true, sharedPendingRetained: true };
  });

  await scenario('matching-pending-request-reuse', async () => {
    const h = world(); const first = h.car.ensure(false), second = h.car.ensure(false); assert.strictEqual(first, second);
    const map = await first; assert.strictEqual(await second, map); assert.equal(h.state.unionCalls, 1); assert.equal(h.state.chatCalls, 0);
    return { matchingPendingShared: true, duplicateBuilds: 0, fakeVisionCalls: 0 };
  });

  await scenario('explicit-layout-teaching-reuse', async () => {
    const h = world(); const oldMap = await h.car.ensure(false); const sig = h.car.signature();
    assert.equal(h.car.setBox('hood', [0.12, 0.18, 0.42, 0.52], 'left', 'up'), true);
    const taught = JSON.stringify(oldMap.boxes.hood); h.switchSource(); const currentMap = await h.car.ensure(false);
    assert.notStrictEqual(currentMap, oldMap); assert.equal(h.car.signature(), sig);
    assert.equal(JSON.stringify(currentMap.boxes.hood), taught, 'explicit teaching survives intentional signature reuse');
    return { newSourceRebuilt: true, signatureContractIntact: true, explicitTaughtBoxRetained: true };
  });

  const finalHash = digest(fs.readFileSync(SOURCE_PATH, 'utf8')); assert.equal(finalHash, ORACLE.sourceSha256, 'production input remained frozen');
  assert.equal(rows.length, ORACLE.scenarios.length);
  const failed = rows.filter(r => r.verdict === 'fail');
  const report = {
    schema: 'spb-carmap-pending-independent-review/1', date: '2026-10-03', reviewer: 'GPT-6.1 SOL xhigh',
    scope: 'Read-only production; seven oracle cases frozen before source reads. Complete actual source module executed unchanged in VM, fake fetch/Image/canvas/model I/O only.',
    oracle_initial_file_sha256: 'ca299c3007cb8b27423a4733313016d0606bac2cbc5e7bb44743c2476e65d80e',
    source_sha256_before: digest(source), source_sha256_after: finalHash,
    test: 'node tests/ai_carmap_pending_review_contract.cjs', result: { passed: rows.length - failed.length, failed: failed.length, scenarios: rows.length },
    promotion_assessment: failed.length ? 'Block on the listed independently exercised failures.' : 'No blocker found within the seven frozen cases; this is controlled lifecycle/cache evidence, not native or real-car quality certification.',
    source_review: ['sourceDescriptor compares actual lexical source-load generation, path, dimensions and canvas; it does not compare paintImageData or layer revision, so legitimate layered recompositing is not classified as a source switch.', 'ensure segregates vision/default pending work from ensure(false), and clears pending ownership only when its record still owns PENDING.', 'prefetchServerMask checks currentSource before response handling, before decoded-grid installation and on rejection. Explicit teaching persists through the separate geometry signature contract.'],
    findings: failed.map(r => ({ priority: 'P1', id: r.id, error: r.error })), rows,
    harness_correction: 'Initial fake template-mask response used found:true; corrected to the actual documented server schema found:{mask:true,wire:false}. Scenario oracle and production source remained unchanged. Initial two decoder-not-started failures were fixture errors, not production defects.',
    limits: ['Fake I/O supplies synthetic grids and layered documents; no actual provider/native/server calls.', 'Whole-source execution proves cache/pending/mask/teaching behavior in the controlled VM, not native loader parsing or real car-map quality.', 'The actual template-mask fetch/decode/build pipeline is exercised; compressed learned-island DecompressionStream I/O and real learned-cars payload parsing are not independently certified here.', 'Layer recomposite identity probe changes actual VM paintImageData and layer revision under stable source generation/path/canvas; it does not measure composite pixels.', 'Existing worker eight-case and prior twelve-case identity audits remain unmodified. Broader teaching import/library semantics and packaging are outside this review.'],
    owned_artifacts: ['tests/ai_carmap_pending_review_contract.cjs', 'docs/handoff_reports/AI_HELPER_14H_CARMAP_PENDING_REVIEW_2026-10-03.json']
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ passed: report.result.passed, failed: failed.length, scenarios: rows.length, sourceFrozen: finalHash === ORACLE.sourceSha256, failures: failed.map(r => ({ id: r.id, error: r.error.split('\n')[0] })) }));
  if (failed.length) process.exitCode = 1;
}
if (require.main === module) main().catch(e => { console.error(String(e.stack || e)); process.exitCode = 1; });
