'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '..', 'js', 'spb-pro-ai.js'), 'utf8');
const zoneSource = fs.readFileSync(require('node:path').join(__dirname, '..', 'js', 'spb-pro-zone-kit.js'), 'utf8');
function extract(name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `${name} exists`);
  const open = source.indexOf('{', start); let depth = 0, quote = null, escaped = false, line = false, block = false;
  for (let i = open; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (escaped) escaped = false; else if (c === '\\') escaped = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++; else if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`Could not extract ${name}`);
}
function extractFrom(src, name) {
  const start = src.indexOf(`function ${name}(`); assert(start >= 0, `${name} exists`);
  const open = src.indexOf('{', start); let depth = 0, quote = null, escaped = false, line = false, block = false;
  for (let i = open; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (escaped) escaped = false; else if (c === '\\') escaped = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++; else if (c === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`Could not extract ${name}`);
}
const ctx = {
  Promise, JSON, String, Array, Object, Math, _busy: false, _progress: '', _skipParts: true, _absent: {},
  render() {}, warm: () => Promise.resolve(), CAR: { missing: () => [] }, friendlyZoneError: String,
  D: { offlineElement: () => ({ zones: [{ name: 'Roof red', region: { part: 'roof' }, color: '#c8102e' }], parts: ['roof'], label: 'red layer', colour: 'red', skipped: [] }) },
  makeTools: queue => [{ name: 'add_zone', handler(spec) { queue.push({ kind: 'add', spec }); return { ok: true, queued: spec.name }; } }]
};
vm.createContext(ctx);
vm.runInContext(`${extract('markPartFollowupQueue')}\n${extract('offlineElementAsk')}\nthis.run=offlineElementAsk;`, ctx);
ctx.run('Make only the roof bright red.', null, { noPreflight: true }).then(result => {
  assert.equal(result.queue.length, 1);
  assert.equal(result.queue[0]._spbPartFollowupOwner, true, 'real compound-element route marks its part add for post-apply registration');
  assert.equal(result.queue[0].spec.region.part, 'roof');
  console.log('PASS actual offlineElementAsk route marks part owner before apply');
}).then(() => {
  // Cross-route consumer case: real ZoneKit stores the normalized selector in
  // provenance after body-layer protection; follow-up compiler starts with the
  // raw {part} selector, so queueEditZones must normalize/protect it first.
  const zones = [], fp = { car: 'review-car', layout: 'layout-a', elements: 'elements-a' };
  const kit = {
    console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt, zones, selectedZoneIndex: 0,
    BASES: [{ id: 'gloss' }, { id: 'chrome' }], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [],
    _psdLayers: [{ id: 'body', name: 'Car Paint', img: {} }],
    document: { getElementById: () => ({ width: 32, height: 32 }) },
    addZone() { zones.push({ id: `z${zones.length + 1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] }); },
    assignFinishToSelected(id) { if (zones[this.selectedZoneIndex]) zones[this.selectedZoneIndex].base = id; },
    setZoneSourceLayer() {}, toggleZoneSourceLayer() {},
    SpbProCar: { findIsland: n => ({ id: String(n), name: String(n), front: true, up: true }), parts: () => ['roof'], canon: String,
      signature: () => fp.car, layoutSig: () => fp.layout, roles: () => [{ role: 'body paint', visible: true, name: 'Car Paint' }],
      maskFor(n) { const m = new Uint8Array(1024); for (let i = 0; i < 512; i++) m[i] = 255; return { mask: m, island: { name: String(n) }, islands: [{ name: String(n) }] }; } },
    SpbProElements: { sig: () => fp.elements }
  };
  kit.window = kit; vm.createContext(kit); vm.runInContext(zoneSource, kit);
  const ownerRegion = { part: 'roof', layers: ['Car Paint'] };
  const added = kit.SpbProZone.add({ name: 'Red roof', region: ownerRegion, color: '#c8102e', finish: 'base::gloss' });
  assert.equal(added.ok, true, JSON.stringify(added.warnings)); assert.ok(zones[0]._aiPartProv, 'owner provenance came from actual ZoneKit.setRegion');
  const ai = {
    console, JSON, Math, isFinite, zones, window: kit, CAR: kit.SpbProCar, SpbProElements: kit.SpbProElements,
    carSig: () => fp.car, editPlural: () => false, friendlyZoneError: String, _reqText: 'Make only the roof chrome',
    bodyLayerNames: undefined, wantsDecalsToo: undefined, protectDecals: undefined, normaliseSpec: undefined
  };
  vm.createContext(ai);
  const decl = ['partRegionKey', 'editKey', 'normaliseSpec', 'bodyLayerNames', 'wantsDecalsToo', 'protectDecals', 'queueEditZones'].map(extract).join('\n');
  vm.runInContext(`${decl}\nvar _editReg={},_editRegSig=null; this.editKeyFn=editKey; this.queueFn=queueEditZones;`, ai);
  const key = ai.editKeyFn(ownerRegion); ai._editReg[key] = zones[0].name; ai._editRegSig = fp.car;
  let edited = 0, addedAgain = 0;
  const candidate = { zones: [{ name: 'Roof chrome', region: { part: 'roof' }, color: 'source', finish: 'base::chrome', _meta: { label: 'roof', kind: 'finish', finishExplicit: true } }] };
  const merged = ai.queueFn(candidate, () => { addedAgain++; return { ok: true }; }, () => { edited++; return { ok: true }; });
  assert.equal(merged.merged, 1, 'the direct-edit route normalized its selector before matching the actual protected owner');
  assert.equal(edited, 1); assert.equal(addedAgain, 0);
  console.log('PASS real protected part provenance is reused by normalized direct-edit selector');
  // The actual batch registrar only adopts applied, successful marked adds;
  // partial batches register the surviving unique owner, not the failed row.
  const zones2 = [], paintState = { car: 'batch-car', layout: 'batch-layout', elements: 'batch-elements' };
  const kit2 = {
    console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt, zones: zones2, selectedZoneIndex: 0,
    BASES: [{ id: 'gloss' }], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [], document: { getElementById: () => ({ width: 32, height: 32 }) },
    addZone() { zones2.push({ id: `b${zones2.length + 1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] }); },
    assignFinishToSelected(id) { const z = zones2[0]; if (z) z.base = id; },
    SpbProCar: { findIsland: n => ({ id: String(n), name: String(n), front: true, up: true }), parts: () => ['roof'], canon: String,
      signature: () => paintState.car, layoutSig: () => paintState.layout, maskFor(n) { const m = new Uint8Array(1024); m.fill(255); return { mask: m, island: { name: String(n) }, islands: [{ name: String(n) }] }; } },
    SpbProElements: { sig: () => paintState.elements },
    duplicateZone(i) { const z = Object.assign({}, zones2[i], { id: `copy-${zones2.length + 1}`, regionMask: zones2[i].regionMask && new Uint8Array(zones2[i].regionMask) }); zones2.splice(i + 1, 0, z); }
  };
  kit2.window = kit2; vm.createContext(kit2); vm.runInContext(zoneSource, kit2);
  const zoneUndo = [];
  const regCtx = { console, Uint8Array, JSON, Math, isFinite, zones: kit2.zones, window: kit2, CAR: kit2.SpbProCar, _psdLayers: kit2._psdLayers,
    SpbProElements: kit2.SpbProElements, carSig: () => paintState.car, _gen: 0, applyLayerOps: () => ({ lines: [], failed: [], undoSteps: 0 }),
    Z: { batch: (ops, label, opts) => kit2.SpbProZone.batch(ops, label, opts) }, _reqText: 'Make the roof red', _specOnlyReq: false, editPlural: () => false,
    undoZoneChange() { const prior = zoneUndo.pop(); if (prior) kit2.zones.splice(0, kit2.zones.length, ...prior.map(z => Object.assign({}, z, { regionMask: z.regionMask && new Uint8Array(z.regionMask) }))); },
    pushZoneUndo() { zoneUndo.push(kit2.zones.map(z => Object.assign({}, z, { regionMask: z.regionMask && new Uint8Array(z.regionMask) }))); },
    renderZones() {}, triggerPreviewRender() {}, render() {}, RECENT: [], _log: [], _advUsed: null, _advRejected: [], _snapGen: 0, _activeId: null };
  kit2.pushZoneUndo = regCtx.pushZoneUndo; kit2.undoZoneChange = regCtx.undoZoneChange; kit2.selectedZoneIndex = 0;
  vm.createContext(regCtx);
  const regFns = ['partRegionKey', 'editKey', 'partRegHas', 'partOwnerCurrent', 'partRegistryState', 'rollbackPendingPartRegistry', 'clearPartRegistryPending', 'reconcilePartRegistry', 'restorePartRegistryUndo', 'registerAppliedPartZones', 'markPartFollowupQueue', 'applyQueue', 'doUndo', 'setPartEditReg', 'deletePartEditReg', 'normaliseSpec', 'bodyLayerNames', 'wantsDecalsToo', 'protectDecals', 'queueEditZones'].map(n => extractFrom(source, n)).join('\n');
  vm.runInContext(`${regFns}\nvar _editReg={},_editRegSig=null,_editRegPendingBefore={}; this.reg={mark:markPartFollowupQueue,apply:applyQueue,queue:queueEditZones,owners:()=>_editReg,pending:()=>_editRegPendingBefore,undo:doUndo};`, regCtx);
  const mixed = [
    { kind: 'add', spec: { name: 'Good roof', region: { part: 'roof' }, color: '#c8102e', finish: 'base::gloss' } },
    { kind: 'add', spec: { name: 'Rejected roof', region: { part: 'roof' }, color: '#c8102e', finish: 'not-a-real-finish' } }
  ];
  mixed.forEach(q => { q.spec = regCtx.normaliseSpec(q.spec); regCtx.protectDecals(q.spec); });
  regCtx.reg.mark(mixed);
  const applied = regCtx.reg.apply(mixed, 'partial cross-route batch');
  assert.equal(applied.results[0].ok, true, JSON.stringify(applied.results)); assert.equal(applied.results[1].ok, false);
  assert.equal(kit2.zones.length, 1); assert.equal(Object.keys(regCtx.reg.owners()).length, 1, 'partial batch registers only the one actually committed, unique owner');
  console.log('PASS real batch failure/partial registration follows committed result rows');
  const editBuilder = args => {
    const zoneIndex = kit2.zones.findIndex(z => z.id === args.zone_id), spec = Object.assign({}, args); delete spec.zone_id;
    const op = { kind: 'edit', zone: zoneIndex, spec };
    for (const k of ['_spbPartRegKey', '_spbPartOwnerName', '_spbPartForgetKey']) if (spec[k]) { op[k] = spec[k]; delete spec[k]; }
    return op;
  };
  const roofKey = Object.keys(regCtx.reg.owners())[0], plan = name => ({ zones: [{ name, region: { part: 'roof' }, color: 'source', finish: 'base::matte', _meta: { label: 'roof', kind: 'finish', finishExplicit: true } }] });
  const firstQueue = [], firstPlan = regCtx.reg.queue(plan('Roof matte (old plan)'), spec => { firstQueue.push({ kind: 'add', spec, _spbPartFollowupOwner: true }); return { ok: true }; }, args => { firstQueue.push(editBuilder(args)); return { ok: true }; });
  assert.equal(firstPlan.merged, 1); assert.equal(regCtx.reg.owners()[roofKey], 'Good roof');
  assert.deepEqual(Object.keys(regCtx.reg.pending()), [], 'a compiled part update does not project pending ownership');
  const secondQueue = [], secondPlan = regCtx.reg.queue({ zones: [{ name: 'Roof blue', region: { part: 'roof' }, color: '#2244cc', finish: 'base::matte', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, spec => { secondQueue.push({ kind: 'add', spec, _spbPartFollowupOwner: true }); return { ok: true }; }, args => { secondQueue.push(editBuilder(args)); return { ok: true }; });
  assert.equal(secondPlan.merged, 1, 'a second no-apply part plan resolves to the same committed owner');
  assert.equal(secondQueue[0]._spbPartOwnerName, 'Good roof'); assert.equal(regCtx.reg.owners()[roofKey], 'Good roof');
  const freshCommit = regCtx.reg.apply(secondQueue, 'apply newer color-only update');
  assert.equal(freshCommit.results[0].ok, true); assert.equal(kit2.zones[0].name, 'Roof blue');
  assert.equal(kit2.zones[0].base, 'gloss', 'color-only update retains existing material'); assert.equal(kit2.zones[0].baseColor, '#2244cc');
  assert.equal(regCtx.reg.owners()[roofKey], 'Roof blue');
  const stale = regCtx.reg.apply(firstQueue, 'apply stale earlier plan');
  assert.equal(stale.results[0].ok, false, 'older queued edit refuses a changed owner'); assert.equal(kit2.zones[0].name, 'Roof blue');
  console.log('PASS two abandoned plans leave committed owner intact; current color-only commit preserves finish; stale queued update is refused');
  const undoEntry = { undoable: true, undone: false, zoneUndo: true, maskUndo: [], _partRegUndo: freshCommit.partRegUndo }, editedRef = kit2.zones[0];
  regCtx.reg.undo(undoEntry);
  assert.notEqual(kit2.zones[0], editedRef, 'real ZoneKit stack undo replaces the zone with a clone');
  assert.equal(kit2.zones[0].name, 'Good roof'); assert.equal(regCtx.reg.owners()[roofKey], 'Good roof');
  const retryQueue = [], retry = regCtx.reg.queue(plan('Roof retry'), spec => { retryQueue.push({ kind: 'add', spec, _spbPartFollowupOwner: true }); return { ok: true }; }, args => { retryQueue.push(editBuilder(args)); return { ok: true }; });
  assert.equal(retry.merged, 1); assert.equal(retryQueue[0]._spbPartOwnerName, 'Good roof');
  console.log('PASS same-car Undo restores registry against cloned zones and retry routes to owner');
  const compileSource = () => regCtx.reg.queue({ zones: [{ name: 'Roof source correction', region: { part: 'roof' }, color: 'source', finish: 'base::gloss', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, () => ({ ok: true }), () => ({ ok: true }));
  paintState.layout = 'layout-changed';
  const layoutDrift = compileSource(); assert.ok(layoutDrift.errs.some(e => /cannot safely keep the existing part colour/.test(e)));
  paintState.layout = 'batch-layout';
  const originalMask = new Uint8Array(kit2.zones[0].regionMask); kit2.zones[0].regionMask[0] = kit2.zones[0].regionMask[0] ? 0 : 255;
  const maskDrift = compileSource(); assert.ok(maskDrift.errs.some(e => /cannot safely keep the existing part colour/.test(e)));
  kit2.zones[0].regionMask = originalMask;
  kit2.zones[0].name = 'Manual roof rename';
  const renameDrift = compileSource(); assert.ok(renameDrift.errs.some(e => /cannot safely keep the existing part colour/.test(e)));
  kit2.zones[0].name = 'Good roof';
  kit2.zones[0].muted = true;
  const mutedPlan = regCtx.reg.queue({ zones: [{ name: 'Roof named blue', region: { part: 'roof' }, color: '#2255aa', finish: 'base::matte', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, () => ({ ok: true }), () => ({ ok: true }));
  assert.equal(mutedPlan.merged, 0, 'muted owner cannot be reused'); kit2.zones[0].muted = false;
  kit2.SpbProZone.batch([{ kind: 'duplicate', zone: 0, spec: {} }], 'manual duplicate');
  const duplicatePlan = regCtx.reg.queue({ zones: [{ name: 'Roof another blue', region: { part: 'roof' }, color: '#2255aa', finish: 'base::matte', _meta: { label: 'roof', kind: 'colour', finishExplicit: false } }] }, () => ({ ok: true }), () => ({ ok: true }));
  assert.equal(duplicatePlan.merged, 0, 'duplicate provenance makes owner ambiguous');
  console.log('PASS source-color correction safely refuses layout, mask and manual-rename drift; muted and duplicate provenance never reuse');
}).catch(err => { console.error(err); process.exitCode = 1; });
