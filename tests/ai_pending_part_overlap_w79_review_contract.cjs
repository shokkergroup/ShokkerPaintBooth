'use strict';
// Independent W79 review. The frozen input oracle is outside this test and was
// written before the candidate source was opened.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const freeze = path.join(root, '_easy_claude_work/ai14h_w79_review/frozen');
const files = {
  proAI: path.join(freeze, 'spb-pro-ai.js'),
  edit: path.join(freeze, 'spb-pro-edit.js'),
  design: path.join(freeze, 'spb-pro-design.js'),
  zoneKit: path.join(freeze, 'spb-pro-zone-kit.js')
};
const pins = {
  proAI: 'b4a519d02419f6e5b21a9bc0de6488c3124d7f3fc1bb2b52738f27b2f0617d1e',
  edit: '99703873013e198857d9aceaa334821098e53dcaa9d55e14dbd1ec50e58604de',
  design: '0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8',
  zoneKit: 'ea9e169b909a30a6431f7fd48b87658b8258d480f165d304cb0ca5dac8983af7'
};
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
for (const [name, file] of Object.entries(files)) assert.equal(sha(file), pins[name], `${name} pinned source changed`);
function extract(source, name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `function ${name} exists`);
  const brace = source.indexOf('{', start); let depth = 0, q = null, line = false, block = false, esc = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (q) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === q) q = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}
const ai = fs.readFileSync(files.proAI, 'utf8');
const dctx = { console, Promise, document: {} }; dctx.window = dctx; vm.createContext(dctx);
vm.runInContext(fs.readFileSync(files.design, 'utf8'), dctx, { filename: files.design });
vm.runInContext(fs.readFileSync(files.edit, 'utf8'), dctx, { filename: files.edit });
const D = dctx.SpbProDesign, E = dctx.SpbProEdit;
const oracle = JSON.parse(fs.readFileSync(path.join(root, '_easy_claude_work/ai14h_w79_review/fresh-desired-oracle.json'), 'utf8'));
assert.equal(oracle.frozen_before_candidate_inspection, true);

function route(text, oldRegion = { part: 'roof' }) {
  const queued = [], env = { palette: [{ hex: '#1f8a3b', share_pct: 24 }, { hex: '#00f', share_pct: 18 }, { hex: '#e22', share_pct: 12 }], layers: [] };
  const ctx = {
    D, E, window: dctx, console, Promise, JSON, Object, Array, String, Number, Math, RegExp, Error, Uint8Array,
    _busy: false, _progress: '', _skipParts: true, _absent: {}, CAR: null, zones: [], _editReg: {}, _editRegPendingBefore: {}, _editRegSig: 'car',
    START_OVER_RE: /^\s*(?:start over|new design)\b/i,
    operationCurrent: t => !!t && t.ok === true, operationCanceled: () => ({ cancelled: true }), operationRelease() {},
    operationPublish: (t, fn) => fn(), operationTools: ts => ts,
    offlineInstructionPreflight: () => null, elementRunCurrent: () => true, elementPaintChangedResult: () => ({ cancelled: true }),
    editPlan: t => E.plan(t, env), offlineMaterialPlan: () => null, advisorOwns: () => false, captureOriginal() {},
    intentSpecOnly: () => false, editYieldsToStack: () => false,
    editEnv: () => env, advisorIntent: () => null, offlineIdeas: () => null, _offlineLast: null,
    offlineCannot: () => null, layerVisRequest: () => null, NUM_FIX_RE: /$a/, NOT_ELEM_RE: /$a/,
    offlineLookAsk() {}, offlineSpecAsk() {}, offlinePartAsk: null, offlineElementAsk() {}, offlineStartOver() {}, offlineUndo() {},
    prepEnv: () => Promise.resolve(env), resolveLook: () => Promise.resolve(null), elementKinds: () => [], exclTargets: () => [],
    editOverlapNote: () => '', editOverlapKinds: () => [], exclNotes: () => [],
    elementRunCurrent: () => true, _elemCache: null, _elemOk: {}, _taughtNow: {},
    editReply: (text, chips, opts) => ({ offline: true, text, queue: (opts && opts.queue) || [] }),
    offlineRefineAsk() {}, offlineHowto() {}, offlineScopeReply: () => ({ offline: true, text: 'Nothing was changed.', queue: [] }),
    selfHelpClaim: () => null, selfHelpResult: x => x, START_OVER_RE: /^\s*(?:start over|new design)\b/i,
    _reqText: '', _specOnlyReq: false, _beforeImg: null, _advLast: null, _forcedIdeaCols: null,
    render() {}, warm: () => Promise.resolve(), markPartFollowupQueue() {}, friendlyZoneError: e => String(e),
    editPlural: () => false, normaliseSpec: x => x, CAR: { missing: () => [] },
    makeTools() { return [
      { name: 'add_zone', handler(spec) { queued.push({ kind: 'add', spec: JSON.parse(JSON.stringify(spec)) }); return {}; } },
      { name: 'edit_zone', handler(args) { queued.push({ kind: 'edit', args: JSON.parse(JSON.stringify(args)) }); return {}; } }
    ]; },
    _spbSourceLoadGeneration: 3,
    currentPartZoneOwners: () => [],
    carSig: () => 'car',
    scopedPartSourceNow: () => ({ sourceGeneration: 3, committedGeneration: 3, path: 'A.psd', fingerprint: 'file-sha256:a', width: 100, height: 100, sourceCommitted: true, sourceReady: true, sourceLoading: false }),
    queued
  };
  // A stale durable owner from source generation 2. It remains present after a
  // failed load; the route must not synthesize a fresh source-colour overlay.
  ctx.zones = [{ id: 'saved-roof', name: 'Saved roof', muted: false, regionMask: new Uint8Array([1, 0]), useRegion: true,
    _aiPartProv: { r: JSON.stringify(oldRegion), z: '2:1', l: '', e: '' },
    _aiPartSource: { path: 'A.psd', fingerprint: 'file-sha256:a', generation: 2, width: 100, height: 100 } }];
  vm.createContext(ctx);
  for (const n of ['partRegionKey', 'editKey', 'editPlural', 'hasPriorPartIdentity', 'offlinePartAsk', 'offlineCoveredPartAsk', 'offlineEditAsk', 'offlineAskCore', 'queueEditZones']) vm.runInContext(extract(ai, n), ctx, { filename: `pinned#${n}` });
  return Promise.resolve(ctx.offlineAskCore(text, { _spbOperation: { ok: true, collection: 1 }, noAdvisor: true })).then(result => ({ result, queued }));
}

(async () => {
  // The parent-provided stale-generation failure is explicitly separate from
  // the fresh oracle and receives no fresh-case credit.
  const repro = await route('Make the green on the roof blue');
  assert.equal(repro.queued.length, 0, 'stale roof source paint must not be queued');
  const staleFollowup = await route('Make the green on the roof lighter');
  assert.equal(staleFollowup.queued.length, 0, 'stale source-color follow-up must also refuse');
  const rows = [];
  // Exercise each fresh prompt through actual offlineAskCore -> parser -> route
  // handler, recording exact queue targets. Some inputs are safe asks; an exact
  // semantic interpretation may vary, so only immutable oracle invariants are
  // asserted here.
  for (const c of oracle.cases) {
    const r = await route(c.input);
    rows.push({ id: c.id, queueCount: r.queued.length, ops: r.queued.map(q => ({ kind: q.kind, region: q.spec && q.spec.region || null, color: q.spec && q.spec.color || null, finish: q.spec && q.spec.finish || null, zone_id: q.args && q.args.zone_id || null })), route: r.result && r.result.text ? String(r.result.text).slice(0, 130) : null });
  }
  const freshCovered = await route('Make the roof and hood blue');
  // Preserve the observed route outcome even when it violates the oracle;
  // this is a review harness, not a candidate conformance test.
  const explicit = await route('Make the owned roof bright red');
  // Explicit color commands are separately reviewed: a current proven owner may
  // be edited, but this stale fixture must still fail closed.
  // Explicit color against a stale owner is not treated as a fresh-owner proof.
  const unrelated = await route('Make the hood yellow');
  console.log(JSON.stringify({ status: 'REVIEW_FINDINGS', candidate: files.proAI, candidateSha256: sha(files.proAI), separateParentRegression: { queued: repro.queued.length, reply: repro.result && repro.result.text }, staleSourceColorFollowup: { queued: staleFollowup.queued.length, reply: staleFollowup.result && staleFollowup.result.text }, unrelatedPartControl: { queued: unrelated.queued.length, regions: unrelated.queued.map(q => q.spec && q.spec.region) }, freshRows: rows, staleMultiTargetQueued: freshCovered.queued.length, staleExplicitColorQueued: explicit.queued.length,
    limits: ['Route executes actual offlineAskCore, offlinePartAsk/offlineCoveredPartAsk, actual E/D parsers and W79 queueEditZones. Tool, renderer, source transaction, zone state and effects are local fakes; not native or applied PSD evidence.', 'The fake source transaction reproduces generation-2 provenance against current generation 3 but does not invoke actual failed PSD loader.'] }, null, 2));
})().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
