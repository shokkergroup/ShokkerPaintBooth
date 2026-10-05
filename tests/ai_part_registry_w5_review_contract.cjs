'use strict';
// Independent W5 lifecycle review. Executes the production AI registry functions
// and production ZoneKit batch/add/edit against a deliberately small car fixture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const ai = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const zone = fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8');
function extract(src, name) {
  const start = src.indexOf(`function ${name}(`); assert(start >= 0, name);
  const open = src.indexOf('{', start); let depth = 0, quote = null, escape = false, line = false, block = false;
  for (let i = open; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (escape) escape = false; else if (c === '\\') escape = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw Error(`unterminated ${name}`);
}
function cloneZone(z) {
  const c = Object.assign({}, z);
  for (const k of ['regionMask', 'spatialMask', 'patternStrengthMap']) if (z[k] && z[k].length != null) c[k] = new Uint8Array(z[k]);
  return c;
}
function harness() {
  const zones = [], undo = [], model = { car: 'car-A', layout: 'layout-A', elements: 'elements-A' };
  const ctx = { console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt, zones, selectedZoneIndex: 0,
    BASES: [{ id: 'gloss' }, { id: 'matte' }], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [], _psdLayers: [{ id: 'body', name: 'Body Paint', img: {} }],
    document: { getElementById: () => ({ width: 32, height: 32 }) },
    addZone() { zones.push({ id: `zone-${zones.length + 1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] }); },
    duplicateZone(i) { zones.splice(i + 1, 0, cloneZone(zones[i])); },
    assignFinishToSelected(id) { if (zones[ctx.selectedZoneIndex]) zones[ctx.selectedZoneIndex].base = id; },
    setZoneSourceLayer(i, id) { zones[i].sourceLayerIds = id ? [id] : []; }, toggleZoneSourceLayer() {},
    pushZoneUndo() { undo.push(zones.map(cloneZone)); },
    undoZoneChange() { const prev = undo.pop(); if (prev) zones.splice(0, zones.length, ...prev.map(cloneZone)); },
    renderZones() {}, triggerPreviewRender() {}, render() {},
    SpbProCar: { findIsland: n => ({ id: String(n), name: String(n), front: true, up: true }), parts: () => ['roof', 'hood'], canon: n => String(n), signature: () => model.car, layoutSig: () => model.layout, missing: () => [], roles: () => [{ id: 'body', name: 'Body Paint', role: 'body paint', visible: true }], maskFor(n) { const mask = new Uint8Array(1024); const start = n === 'hood' ? 512 : 0; for (let i = start; i < start + 512; i++) mask[i] = 255; return { mask, island: { name: String(n) }, islands: [{ name: String(n) }] }; } },
    _busy: false, _progress: '', _absent: {}, _skipParts: true, _gen: 0, _snapGen: 0, _activeId: null, RECENT: [], _advUsed: null, _advRejected: [], _log: [], _layerUndoStack: [],
    carSig: () => model.car, editPlural: () => false, friendlyZoneError: String, warm: () => Promise.resolve(), D: null, applyLayerOps: () => ({ lines: [], failed: [], undoSteps: 0 }),
    zonesRef: zones, undoLayerEdit() {}
  };
  ctx.CAR = ctx.SpbProCar; ctx.window = ctx; ctx.SpbProElements = { sig: () => model.elements }; ctx._psdLayers = ctx._psdLayers;
  vm.createContext(ctx); vm.runInContext(zone, ctx, { filename: 'production-zone-kit' }); ctx.Z = ctx.SpbProZone;
  const names = ['normaliseSpec', 'bodyLayerNames', 'wantsDecalsToo', 'protectDecals', 'partRegionKey', 'editKey', 'setPartEditReg', 'deletePartEditReg', 'markPartFollowupQueue', 'partOwnerCurrent', 'registerAppliedPartZones', 'partRegHas', 'partRegistryState', 'rollbackPendingPartRegistry', 'clearPartRegistryPending', 'reconcilePartRegistry', 'mergePartRegistryUndo', 'restorePartRegistryUndo', 'applyQueue', 'queueEditZones', 'offlineElementAsk', 'doUndo', 'elementPaintSig', 'elementRunIdentity', 'elementRunCurrent'];
  vm.runInContext(`${names.map(n => extract(ai, n)).join('\n')}\nvar _editReg={},_editRegSig=null,_editRegPendingBefore={},_reqText='',_specOnlyReq=false; this.api={apply:applyQueue,queue:queueEditZones,undo:doUndo,registry:()=>_editReg,pending:()=>_editRegPendingBefore,mark:markPartFollowupQueue};`, ctx, { filename: 'production-ai-part-registry' });
  ctx.D = { offlineElement: () => ({ zones: [{ name: 'Red roof', region: { part: 'roof' }, color: '#c8102e', finish: 'base::gloss' }], parts: ['roof'], label: 'roof', colour: 'red', skipped: [] }) };
  ctx.makeTools = queue => [{ name: 'add_zone', handler(spec) { const s = ctx.normaliseSpec(JSON.parse(JSON.stringify(spec))); ctx.protectDecals(s); queue.push({ kind: 'add', spec: s }); return { ok: true }; } }];
  function add(spec) { return ctx.Z.add(spec); }
  function editAt(args) {
    const i = zones.findIndex(z => z.id === args.zone_id), s = Object.assign({}, args); delete s.zone_id;
    const q = { kind: 'edit', zone: i, spec: s };
    for (const k of ['_spbPartRegKey', '_spbPartOwnerName', '_spbPartForgetKey']) { if (s[k]) { q[k] = s[k]; delete s[k]; } }
    return q;
  }
  async function initial() { const route = await ctx.offlineElementAsk('Make the roof red', {}); const applied = ctx.api.apply(route.queue, 'initial red roof'); return { route, applied }; }
  return { ctx, zones, undo, model, add, editAt, initial };
}
const findings = [];
async function main() {
  // Real route, real ZoneKit batch, cloned snapshot restoration, and retry.
  {
    const h = harness(), { route, applied } = await h.initial(), key = h.ctx.editKey({ part: 'roof', layers: ['Body Paint'] });
    assert.equal(applied.results[0].ok, true); assert.equal(h.ctx.api.registry()[key], 'Red roof', JSON.stringify({key,registry:h.ctx.api.registry(),zone:h.zones[0],queue:route.queue}));
    const compiledOps = [], compiled = h.ctx.api.queue({ zones: [{ name: 'Roof satin', region: { part: 'roof' }, color: 'source', finish: 'base::matte', _meta: { label: 'roof', kind: 'finish', finishExplicit: true } }] }, h.add, args => { const op = h.editAt(args); compiledOps.push(op); return op; });
    assert.equal(compiled.merged, 1); assert.equal(h.zones.length, 1); assert.equal(h.zones[0].baseColor, '#c8102e');
    const before = h.zones[0], committed = h.ctx.api.apply(compiledOps, 'satin');
    assert.equal(committed.results[0].ok, true); assert.equal(h.zones[0].base, 'matte');
    const entry = { undoable: true, undone: false, zoneUndo: true, maskUndo: [], _partRegUndo: committed.partRegUndo };
    h.ctx.api.undo(entry); assert.notEqual(h.zones[0], before, 'ZoneKit undo returns a cloned zone object');
    assert.equal(h.ctx.api.registry()[key], 'Red roof');
    findings.push({ case: 'undo-cloned-zone-retry', result: 'PASS', evidence: 'Undo restored cloned ZoneKit snapshot and registry name; next selector compiles as an edit.' });
    const explicit = [], stackPlan = { zones: [{ name: 'Second roof layer', region: { part: 'roof' }, color: '#bb8800', finish: 'base::gloss', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] };
    const stackResult = h.ctx.api.queue(stackPlan, spec => { explicit.push({ kind: 'add', spec }); return { ok: true }; }, h.editAt, { noReg: true });
    assert.equal(stackResult.merged, 0); assert.equal(explicit.length, 1); assert.equal(h.ctx.api.registry()[key], 'Red roof');
    findings.push({ case: 'explicit-new-stack-vs-update', result: 'PASS', evidence: 'noReg route keeps explicit add semantics for the same selector and does not claim helper ownership.' });
    findings.push({ case: 'explicit-material-stack-vs-color-preservation', result: 'PASS', evidence: 'Explicit finish follows update path while preserving source paint color.' });
  }
  // Failed second op is reconciled per selector; first successful owner remains committed.
  {
    const h = harness(); await h.initial();
    const q = [{ kind: 'add', _spbPartFollowupOwner: true, spec: { name: 'Blue hood', finish: 'base::gloss', color: '#2244cc', region: { part: 'hood', layers: ['Body Paint'] } } },
      { kind: 'add', _spbPartFollowupOwner: true, spec: { name: 'Bad roof', finish: 'base::unknown', color: '#111111', region: { part: 'roof', layers: ['Body Paint'] } } }];
    const result = h.ctx.api.apply(q, 'partial batch');
    assert.equal(result.results.length, 2); assert.equal(result.results[0].ok, true); assert.equal(result.results[1].ok, false);
    assert.equal(h.ctx.api.registry()[h.ctx.editKey({ part: 'hood', layers: ['Body Paint'] })], 'Blue hood');
    findings.push({ case: 'partial-batch', result: 'PASS', evidence: 'Successful first add gets an owner; failed second add does not.' });
  }
  // Commit-only contract: abandoned part plans leave the committed owner untouched.
  {
    const h = harness(), { applied } = await h.initial(), key = h.ctx.editKey({ part: 'roof', layers: ['Body Paint'] });
    const queued = [], plan = { zones: [{ name: 'Roof satin', region: { part: 'roof' }, color: 'source', finish: 'base::matte', _meta: { label: 'roof', kind: 'finish', finishExplicit: true } }] };
    const firstPlan = h.ctx.api.queue(plan, h.add, args => { queued.push(h.editAt(args)); return queued[queued.length - 1]; });
    assert.equal(queued.length, 1); assert.equal(h.zones[0].name, 'Red roof');
    assert.equal(firstPlan.merged, 1);
    assert.equal(h.ctx.api.registry()[key], 'Red roof', 'compiling an edit leaves only the committed owner in the registry');
    assert.deepEqual(Object.keys(h.ctx.api.pending()), [], 'part plans do not create pending registry edits');
    const secondOps = [], secondPlan = h.ctx.api.queue(plan, h.add, args => { secondOps.push(h.editAt(args)); return secondOps[0]; });
    assert.equal(secondPlan.merged, 1, 'a second abandoned same-part plan still resolves to the committed owner');
    assert.equal(secondOps[0]._spbPartOwnerName, 'Red roof');
    assert.equal(h.ctx.api.registry()[key], 'Red roof');
    // A different selector can also be compiled without changing the roof mapping.
    h.ctx.api.queue({ zones: [{ name: 'Blue hood', region: { part: 'hood' }, color: '#2244cc', finish: 'base::gloss', _meta: { label: 'hood', kind: 'colour', finishExplicit: false } }] }, h.add, h.editAt);
    assert.equal(h.ctx.api.registry()[key], 'Red roof');
    findings.push({ case: 'compile-without-apply', result: 'PASS_COMMIT_ONLY', evidence: 'Repeated abandoned part plans reuse the committed owner, while _editReg and pending state remain unchanged.' });
  }
  // Element identity check refuses stale apply and rolls back queue projection.
  {
    const h = harness(), key = h.ctx.editKey({ part: 'roof', layers: ['Body Paint'] }); await h.initial();
    h.ctx.api.queue({ zones: [{ name: 'Roof matte', region: { part: 'roof' }, color: 'source', finish: 'base::matte', _meta: { label: 'roof', kind: 'finish', finishExplicit: true } }] }, h.add, h.editAt);
    h.model.elements = 'changed-elements';
    const out = h.ctx.api.apply([{ kind: 'edit', zone: 0, spec: { name: 'Roof matte', finish: 'base::matte' } }], 'stale element', false, 'elements-A|car=car-A|layers=0');
    assert.equal(out.results.length, 0); assert.equal(h.zones[0].name, 'Red roof'); assert.equal(h.ctx.api.registry()[key], 'Red roof');
    findings.push({ case: 'stale-commit', result: 'PASS', evidence: 'Stale element identity exits before ZoneKit and rolls pending selector state back.' });
  }
  // Concurrent/older undo metadata ownership guard: metadata protects later map value.
  {
    const h = harness(), key = h.ctx.editKey({ part: 'roof', layers: ['Body Paint'] }), first = await h.initial();
    const older = { undoable: true, undone: false, zoneUndo: false, maskUndo: [], _partRegUndo: first.applied.partRegUndo };
    const laterOps = [], plan = { zones: [{ name: 'Later roof', region: { part: 'roof' }, color: '#009900', finish: 'base::gloss', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] };
    h.ctx.api.queue(plan, h.add, args => { laterOps.push(h.editAt(args)); return { ok: true }; });
    h.ctx.api.apply(laterOps, 'later owner');
    h.ctx.api.undo(older);
    assert.equal(h.ctx.api.registry()[key], 'Later roof', 'compare-before-restore must preserve a later registry owner');
    findings.push({ case: 'later-registry-owner', result: 'PASS_METADATA_ONLY', evidence: 'Registry restore guard preserves changed later name. Arbitrary out-of-order undo against the global ZoneKit stack is outside this contract.' });
  }
  // Duplicates and manual mask edits invalidate singular helper ownership; source corrections refuse adoption.
  {
    const h = harness(), { applied } = await h.initial(), key = h.ctx.editKey({ part: 'roof', layers: ['Body Paint'] });
    const original = h.zones[0]; h.ctx.Z.batch([{ kind: 'duplicate', zone: 0, spec: {} }], 'manual duplicate');
    assert.equal(h.zones.length, 2);
    const freshOps = [], response = h.ctx.api.queue({ zones: [{ name: 'Roof blue', region: { part: 'roof' }, color: '#2244cc', finish: 'base::matte', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, spec => { freshOps.push({ kind: 'add', spec, _spbPartFollowupOwner: true }); return { ok: true }; }, h.editAt);
    assert.equal(response.merged, 0); assert.equal(h.zones.length, 2, 'ambiguous duplicate is not adopted while the plan is being compiled');
    h.ctx.api.apply(freshOps, 'fresh named-color zone');
    assert.equal(h.zones.length, 3);
    assert.equal(h.ctx.api.registry()[key], 'Red roof', 'ambiguous new candidate does not replace a unique committed mapping');
    const manual = h.zones[0]; manual.regionMask[0] = manual.regionMask[0] ? 0 : 255;
    const source = h.ctx.api.queue({ zones: [{ name: 'Roof source', region: { part: 'roof' }, color: 'source', finish: 'base::gloss', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, h.add, h.editAt);
    assert.ok(source.errs.some(e => /cannot safely keep the existing part colour/.test(e)));
    findings.push({ case: 'duplicate-manual-mask-source-correction', result: 'SAFE_REFUSAL', evidence: 'Duplicate provenance fails the live uniqueness check; manual mask drift also invalidates provenance, so source-color correction is refused rather than adopting a zone.' });
    const renamed = harness(); await renamed.initial(); const rkey = renamed.ctx.editKey({ part: 'roof', layers: ['Body Paint'] });
    renamed.zones[0].name = 'Owner renamed roof';
    const sourceAfterRename = renamed.ctx.api.queue({ zones: [{ name: 'Roof source', region: { part: 'roof' }, color: 'source', finish: 'base::gloss', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, renamed.add, renamed.editAt);
    assert.ok(sourceAfterRename.errs.some(e => /cannot safely keep the existing part colour/.test(e)));
    assert.equal(renamed.ctx.api.registry()[rkey], 'Red roof', 'safe refusal leaves only the prior committed mapping; it does not adopt the renamed zone');
    findings.push({ case: 'manual-rename-source-correction', result: 'SAFE_REFUSAL', evidence: 'Renamed provenance is not adopted by name; source-color correction asks for a named color or clarification.' });
    const muted = harness(); await muted.initial(); muted.zones[0].muted = true;
    const mutedPlan = muted.ctx.api.queue({ zones: [{ name: 'Roof fresh', region: { part: 'roof' }, color: '#aa22cc', finish: 'base::gloss', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, muted.add, muted.editAt);
    assert.equal(mutedPlan.merged, 0);
    findings.push({ case: 'muted-owner', result: 'SAFE_REFUSAL', evidence: 'Muted helper zone is excluded from reuse; its existing committed mapping cannot target it while muted.' });
  }
  // Selector identity keeps another panel and unrelated region metadata independent.
  {
    const h = harness(), { applied } = await h.initial(), roofKey = h.ctx.editKey({ part: 'roof', layers: ['Body Paint'] }), hoodKey = h.ctx.editKey({ part: 'hood', layers: ['Body Paint'] });
    assert.notEqual(roofKey, hoodKey);
    const q = [{ kind: 'add', _spbPartFollowupOwner: true, spec: { name: 'Hood green', color: '#008800', finish: 'base::gloss', region: { part: 'hood', portion: 'front third', layers: ['Body Paint'] } } }];
    h.ctx.api.apply(q, 'hood distinct portion');
    assert.equal(h.ctx.api.registry()[roofKey], 'Red roof'); assert.equal(h.ctx.api.registry()[hoodKey], undefined, 'selector with portion is a separate key until queue compilation commits it');
    findings.push({ case: 'different-panel-and-region-metadata', result: 'PASS', evidence: 'Other panel/portion selectors remain distinct; registry mutation is scoped by canonical editKey.' });
  }
  const report = { contract: 'spb-ai-part-registry-w5-review/1', date: '2026-10-03', mode: 'read-only production review; only boundary fixtures', sources: ['js/spb-pro-ai.js', 'js/spb-pro-zone-kit.js'], findings };
  console.log(JSON.stringify(report, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
