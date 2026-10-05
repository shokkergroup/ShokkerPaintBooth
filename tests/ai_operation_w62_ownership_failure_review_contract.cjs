'use strict';
// W62 executes actual extracted controller functions plus the shared operation manager.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const sourcePath = path.join(root, '_easy_claude_work/ai14h_w62_candidate/js/spb-pro-ai.js');
const operationPath = path.join(root, 'js/spb-ai-operation.js');
const operation = require(operationPath);
const source = fs.readFileSync(sourcePath, 'utf8');
const { cases } = require('./ai_operation_w62_ownership_failure_contract.cjs');

function extract(src, name) {
  const start = src.indexOf(`function ${name}(`); assert(start >= 0, `missing ${name}`);
  const open = src.indexOf('{', start); let depth = 0, quote = null, escaped = false, line = false, block = false;
  for (let i = open; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (escaped) escaped = false; else if (c === '\\') escaped = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}
function world(opts = {}) {
  const w = { console, _spbLayerRev: 4, paintCanvas: { width: 64, height: 64 }, _psdLayers: [],
    paintImageData: { width: 64, height: 64 }, zones: [{ id: 'roof-1', name: 'Roof', color: 'blue' }],
    zoneUndoStack: [], _layerUndoStack: [], _editReg: {}, _editRegSig: '', _gen: 0,
    applyCalls: 0, zoneHash: 'zone-A', cachedHash: 'zone-A', source: { generation: 3, committedGeneration: 3, loading: false, committed: true, path: 'C:/paint/car.tga', fingerprint: 'sha-A' } };
  w.window = w;
  w.document = { getElementById: id => id === 'paintCanvas' ? w.paintCanvas : null };
  w.SPBSourceLoadTransaction = {
    getGeneration: () => w.source.generation,
    getCommittedGeneration: () => w.source.committedGeneration,
    getCommittedPath: () => w.source.path,
    getCommittedFingerprint: () => w.source.fingerprint,
    isLoading: () => w.source.loading,
    isCommitted: () => w.source.committed
  };
  w._getZoneConfigHashUncached = () => { if (opts.hashMode === 'throw') throw new Error('controlled hash failure'); if (opts.hashMode === 'missing') return ''; return w.zoneHash; };
  w.getZoneConfigHash = () => { if (opts.cachedMode === 'throw') throw new Error('cached hash failure'); return w.cachedHash; };
  w.Z = { batch: ops => { w.applyCalls++; return ops.map((q, i) => ({ ok: true, applied: ['updated'], index: q.zone, name: w.zones[q.zone] && w.zones[q.zone].name })); } };
  w.undoSnapTake = () => null;
  w.zoneHashNow = () => w.zoneHash;
  w.rshotFor = () => null;
  w.partRegistryState = () => ({});
  w.registerAppliedPartZones = () => {};
  w.reconcilePartRegistry = () => {};
  w.clearPartRegistryPending = () => {};
  w.rollbackPendingPartRegistry = () => {};
  w.undoPushedSince = () => false;
  w.operationDocument = null; w.operationRevision = null; w.applyQueue = null;
  vm.createContext(w);
  const declarations = ['operationDocument', 'operationRevision', 'applyQueue'].map(n => extract(source, n)).join('\n');
  vm.runInContext(`var _operationRevisionFailureSerial = 0;\n${declarations}\nthis.operationDocument = operationDocument; this.operationRevision = operationRevision; this.applyQueue = applyQueue;`, w);
  w.manager = operation.create(w.operationDocument, w.operationRevision);
  w.queue = [{ kind: 'edit', zone: 0, spec: { color: '#ff0000' } }];
  return w;
}
function apply(w) { return w.applyQueue(w.queue, 'W62 edit', true, null); }
function check(name, fn) { try { fn(); return { name, pass: true }; } catch (e) { return { name, pass: false, error: e.message }; } }
const results = [];

results.push(check('hash getter throws repeatedly after manual zone change', () => {
  const w = world({ hashMode: 'throw' }), t = w.manager.start();
  w.zones[0].color = 'manual-green';
  assert.equal(w.manager.current(t), false, 'failed fresh revision must not remain a stable ticket');
  assert.equal(w.manager.current(t), false, 'repeated failures must not reuse an authorizing empty-hash revision');
  apply(w); assert.equal(w.applyCalls, 0);
}));
results.push(check('uncached hash getter missing refuses actual queue', () => {
  const w = world(), t = w.manager.start(); delete w._getZoneConfigHashUncached;
  w.zones[0].color = 'manual-green';
  assert.equal(w.manager.current(t), true, 'cached fallback remains available for the historical positive ownership oracle');
  apply(w); assert.equal(w.applyCalls, 0, 'mutation boundary requires a fresh uncached proof');
}));
results.push(check('both zone hash getters missing refuses actual queue', () => {
  const w = world(), t = w.manager.start(); delete w._getZoneConfigHashUncached; delete w.getZoneConfigHash;
  w.zones[0].color = 'manual-green'; assert.equal(w.manager.current(t), false); apply(w); assert.equal(w.applyCalls, 0);
}));
results.push(check('failed replacement retains committed A for a fresh diagnosis', () => {
  const w = world(); w.source.generation = 4; w.source.committedGeneration = 4; w.source.loading = false; w.source.committed = true;
  const doc = w.operationDocument(); assert.equal(doc.sourceLoading, false); assert.equal(doc.sourceReady, true);
  const t = w.manager.start(); assert.equal(w.manager.current(t), true);
  const r = apply(w); assert.equal(w.applyCalls, 1); assert.equal(r.results[0].ok, true);
}));
results.push(check('post-draw reset with empty source fingerprint is uncommitted', () => {
  const w = world(); w.source.generation = 4; w.source.committedGeneration = 3; w.source.loading = false;
  w.source.committed = false; w.source.fingerprint = '';
  const doc = w.operationDocument(); assert.equal(doc.sourceLoading, false); assert.equal(doc.sourceReady, false);
  const t = w.manager.start(); assert.equal(w.manager.current(t), true, 'passive operation ownership may still inspect retained state');
  apply(w); assert.equal(w.applyCalls, 0, 'uncommitted post-draw reset cannot reach the controller');
}));
results.push(check('source is loading', () => {
  const w = world(); w.source.generation = 4; w.source.loading = true; w.source.committed = false;
  apply(w); assert.equal(w.applyCalls, 0);
}));
results.push(check('source ready with current uncached hash applies once', () => {
  const w = world(), t = w.manager.start(); assert.equal(w.manager.current(t), true);
  const r = apply(w); assert.equal(w.applyCalls, 1); assert.equal(r.results[0].ok, true);
}));
results.push(check('manual edit changes fresh operation revision', () => {
  const w = world(), t = w.manager.start(); w.zoneHash = 'zone-B';
  assert.equal(w.manager.current(t), false);
}));
results.push(check('owned publication stays current across later display-cache refresh', () => {
  const w = world(), t = w.manager.start();
  const p = w.manager.publish(t, () => { w.zoneHash = 'zone-B'; });
  assert.equal(p.refused, false); assert.equal(w.manager.current(t), true);
  w.cachedHash = 'display-cache-later-value'; assert.equal(w.manager.current(t), true);
}));
results.push(check('source generation swap invalidates prior document ticket', () => {
  const w = world(), t = w.manager.start(); w.source.generation++; w.source.committedGeneration = w.source.generation;
  w.source.fingerprint = 'sha-B'; assert.equal(w.manager.current(t), false);
}));
results.push(check('whole-body document swap invalidates prior ticket', () => {
  const w = world(), t = w.manager.start(); w.paintCanvas = { width: 128, height: 64 };
  assert.equal(w.manager.current(t), false);
}));
results.push(check('non-edit queue still does not fabricate an apply', () => {
  const w = world(); w.queue = []; const r = apply(w); assert.equal(w.applyCalls, 0); assert.deepEqual(r.results, []);
}));
results.push(check('passive no-paint help remains available', () => {
  const w = world(); w.paintImageData = null; w.paintCanvas = { width: 0, height: 0 }; w._psdLayers = [];
  const helpPath = path.join(root, '_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/js/spb-self-help.js');
  const knowPath = path.join(root, '_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/js/spb-ai-knowledge.js');
  vm.runInContext(fs.readFileSync(knowPath, 'utf8'), w);
  vm.runInContext(fs.readFileSync(helpPath, 'utf8'), w);
  const a = w.SpbSelfHelp.answer('How do I add a metallic finish?');
  assert.ok(a && a.text && a.text.length); assert.equal(w.applyCalls, 0);
}));

assert.equal(cases.length, 12, 'frozen W62 oracle remains unchanged');
const bad = results.filter(x => !x.pass);
console.log(`W62 actual-controller harness: ${results.length - bad.length}/${results.length} focused checks passed`);
for (const x of results) console.log(`${x.pass ? 'PASS' : 'FAIL'} ${x.name}${x.error ? ` — ${x.error}` : ''}`);
if (bad.length) process.exitCode = 1;
