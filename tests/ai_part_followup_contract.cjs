'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const aiSource = fs.readFileSync(path.join(root, 'js', 'spb-pro-ai.js'), 'utf8');
const zoneSource = fs.readFileSync(path.join(root, 'js', 'spb-pro-zone-kit.js'), 'utf8');

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists in production source`);
  const open = source.indexOf('{', start);
  let depth = 0, quote = null, escaped = false, lineComment = false, blockComment = false;
  for (let i = open; i < source.length; i++) {
    const ch = source[i], next = source[i + 1];
    if (lineComment) { if (ch === '\n') lineComment = false; continue; }
    if (blockComment) { if (ch === '*' && next === '/') { blockComment = false; i++; } continue; }
    if (quote) { if (escaped) escaped = false; else if (ch === '\\') escaped = true; else if (ch === quote) quote = null; continue; }
    if (ch === '/' && next === '/') { lineComment = true; i++; continue; }
    if (ch === '/' && next === '*') { blockComment = true; i++; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue; }
    if (ch === '{') depth++;
    else if (ch === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`Could not find end of ${name}`);
}

function harness(signature = 'car-a') {
  const zones = [];
  const calls = { add: 0, edit: 0 };
  const context = {
    console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt,
    zones, selectedZoneIndex: 0, currentSignature: signature, layoutVersion: 'layout-a', elementVersion: 'paint-a',
    editPlural: label => /(numbers|sponsors|stripes|logos|decals|lines|bands|accents|panels|parts|bumpers)$/.test(String(label)),
    friendlyZoneError: String,
    carSig: () => context.SpbProCar.signature(),
    BASES: [{ id: 'gloss' }, { id: 'matte' }], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [],
    _psdLayers: [{ id: 'body', name: 'Body', img: {} }, { id: 'trim', name: 'Trim', img: {} }],
    document: { getElementById: id => id === 'paintCanvas' ? { width: 32, height: 32 } : null },
    addZone() { zones.push({ id: `zone-${zones.length + 1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] }); },
    assignFinishToSelected(id) { if (zones[context.selectedZoneIndex]) zones[context.selectedZoneIndex].base = id; },
    setZoneSourceLayer(i, id) { zones[i].sourceLayerIds = id ? [id] : []; },
    toggleZoneSourceLayer(i, id, on) {
      const list = zones[i].sourceLayerIds || (zones[i].sourceLayerIds = []);
      const at = list.indexOf(id); if (on && at < 0) list.push(id); else if (!on && at >= 0) list.splice(at, 1);
    },
    SpbProCar: {
      findIsland: name => ({ id: String(name), name: String(name), front: true, up: true }),
      parts: () => ['hood', 'roof', 'left side'], canon: name => String(name),
      signature: () => context.currentSignature, layoutSig: () => context.layoutVersion,
      maskFor(name, portion, band) {
        const mask = new Uint8Array(32 * 32);
        const ref = Array.isArray(name) ? name[0] : name;
        const xStart = ref === 'roof' ? 16 : 0;
        const xEnd = ref === 'roof' ? 32 : 16;
        let yStart = portion === 'lower' ? 16 : 0;
        let yEnd = portion === 'upper' ? 16 : 32;
        const shift = context.layoutVersion === 'layout-b' ? 1 : 0;
        for (let y = yStart; y < yEnd; y++) for (let x = xStart + shift; x < xEnd; x++) mask[y * 32 + x] = 255;
        return { mask, island: { name: String(ref) }, islands: [{ name: String(ref) }] };
      }
    },
    SpbProElements: { sig: () => context.elementVersion, maskFor: () => ({ mask: new Uint8Array(32 * 32), desc: 'test elements' }) },
    calls,
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(zoneSource, context, { filename: 'js/spb-pro-zone-kit.js' });
  context.CAR = context.SpbProCar;
  context.CAR = context.SpbProCar; context.Z = context.SpbProZone; context.applyLayerOps = () => ({ lines: [], failed: [], undoSteps: 0 }); context._gen = 0;
  const declarations = ['partRegionKey', 'editKey', 'partRegHas', 'partOwnerCurrent', 'partRegistryState', 'rollbackPendingPartRegistry', 'clearPartRegistryPending', 'reconcilePartRegistry', 'registerAppliedPartZones', 'markPartFollowupQueue', 'applyQueue', 'queueEditZones'].map(name => extractFunction(aiSource, name)).join('\n');
  vm.runInContext(`${declarations}\nvar _editReg = {}, _editRegSig = null, _editRegPendingBefore = {}; this.api = { editKey: editKey, queue: queueEditZones, mark: markPartFollowupQueue, commit: applyQueue, registry: function(){return _editReg;}, pending: function(){return _editRegPendingBefore;} };`, context,
    { filename: 'js/spb-pro-ai.js#queueEditZones+applyQueue' });
  context.add = spec => { calls.add++; context.currentOps.push({ kind: 'add', spec }); return { ok: true }; };
  context.edit = args => {
    calls.edit++;
    const target = zones.findIndex(z => z.id === args.zone_id);
    if (target < 0) return { error: 'missing zone' };
    const update = Object.assign({}, args); delete update.zone_id;
    const op = { kind: 'edit', zone: target, spec: update };
    for (const key of ['_spbPartRegKey', '_spbPartOwnerName', '_spbPartForgetKey']) if (update[key]) { op[key] = update[key]; delete update[key]; }
    context.currentOps.push(op); return { ok: true };
  };
  context.plan = (spec, opts) => { context.currentOps = []; const compiled = context.api.queue({ zones: [spec] }, context.add, context.edit, opts); return { compiled, queue: context.currentOps }; };
  context.commit = (plan, label = 'follow-up') => { if (!plan.noReg) context.api.mark(plan.queue); return context.api.commit(plan.queue, label); };
  context.apply = (spec, opts) => { const plan = context.plan(spec, opts); plan.noReg = !!(opts && opts.noReg); plan.commit = context.commit(plan); return plan.compiled; };
  return context;
}

function zone(name, region, color, finish, meta = {}) {
  return { name, region, color, finish, _meta: Object.assign({ label: 'hood', kind: 'colour', finishExplicit: true }, meta) };
}

// Recolour followed by a finish-only edit reuses the real zone; source color leaves paint intact.
{
  const h = harness();
  h.apply(zone('Hood repaint', { part: 'hood', portion: 'upper' }, '#aa2200', 'base::gloss'));
  h.apply(zone('Hood repaint', { part: 'hood', portion: 'upper' }, 'source', 'base::matte'));
  assert.equal(h.calls.add, 1);
  assert.equal(h.calls.edit, 1);
  assert.equal(h.zones.length, 1);
  assert.equal(h.zones[0].baseColor, '#aa2200', 'finish-only update preserves the earlier repaint');
  assert.equal(h.zones[0].base, 'matte');
  assert.ok(h.zones[0].regionMask instanceof Uint8Array);
  assert.equal(h.zones[0].region, undefined, 'Pro stores the mask and compact selector provenance');
}

// A color-only follow-up leaves the earlier finish intact when finishExplicit is false.
{
  const h = harness();
  h.apply(zone('Hood look', { part: 'hood', portion: 'upper' }, '#aa2200', 'base::gloss'));
  h.apply(zone('Hood look', { part: 'hood', portion: 'upper' }, '#2244cc', 'base::matte', { finishExplicit: false }));
  assert.equal(h.calls.add, 1);
  assert.equal(h.calls.edit, 1);
  assert.equal(h.zones[0].baseColor, '#2244cc');
  assert.equal(h.zones[0].base, 'gloss', 'color-only update preserves the earlier finish');
}

// Different part/mask selectors are not treated as the same zone.
for (const [firstRegion, nextRegion] of [
  [{ part: 'hood' }, { part: 'roof' }],
  [{ part: 'hood', exclude: ['numbers'] }, { part: 'hood', exclude: ['sponsors'] }],
  [{ part: 'hood', layers: ['Body'] }, { part: 'hood', layers: ['Trim'] }],
  [{ part: 'hood', portion: 'upper' }, { part: 'hood', portion: 'lower' }],
]) {
  const h = harness();
  h.apply(zone('Scoped target', firstRegion, '#aa2200', 'base::gloss'));
  h.apply(zone('Scoped target', nextRegion, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0, `${JSON.stringify(firstRegion)} and ${JSON.stringify(nextRegion)} remain distinct`);
  assert.equal(h.calls.add, 2);
}
{
  const h = harness();
  h.apply(zone('Same hood selector', { part: 'hood', layers: ['Body', 'Trim'], exclude: ['numbers', 'sponsors'] }, '#aa2200', 'base::gloss'));
  h.apply(zone('Same hood selector', { exclude: ['sponsors', 'numbers'], part: 'hood', layers: ['Trim', 'Body'] }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 1, 'normalized selector order still matches the same part region');
  assert.equal(h.calls.add, 1);
}

// Manual region or pixel-mask changes invalidate the old owner registration.
{
  const h = harness();
  h.apply(zone('Hood owner', { part: 'hood', portion: 'upper' }, '#aa2200', 'base::gloss'));
  h.SpbProZone.edit(h.zones[0], { region: { part: 'hood', portion: 'lower' } });
  h.apply(zone('Hood owner', { part: 'hood', portion: 'upper' }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0);
  assert.equal(h.calls.add, 2);
}
{
  const h = harness();
  h.apply(zone('Hood owner', { part: 'hood', portion: 'upper' }, '#aa2200', 'base::gloss'));
  h.zones[0].regionMask[0] = h.zones[0].regionMask[0] ? 0 : 255;
  h.apply(zone('Hood owner', { part: 'hood', portion: 'upper' }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0, 'in-place mask mutation is detected');
  assert.equal(h.calls.add, 2);
}
{
  const h = harness();
  h.apply(zone('Hood owner', { part: 'hood', portion: 'upper' }, '#aa2200', 'base::gloss'));
  h.layoutVersion = 'layout-b';
  h.apply(zone('Hood owner', { part: 'hood', portion: 'upper' }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0, 'a changed car-part layout invalidates old provenance');
  assert.equal(h.calls.add, 2);
}

// Missing, renamed, muted, or ambiguous live owners never receive the follow-up edit.
let staleOwnerCase = 0;
for (const mutate of [
  h => { h.zones.length = 0; },
  h => { h.zones[0].name = 'Renamed owner'; },
  h => { h.zones[0].muted = true; },
  h => { const duplicate = zone('Registered owner', { part: 'hood' }, '#aa2200', 'base::gloss'); delete duplicate._meta; h.SpbProZone.add(duplicate); },
]) {
  const h = harness();
  h.apply(zone('Registered owner', { part: 'hood' }, '#aa2200', 'base::gloss'));
  mutate(h);
  h.apply(zone('Registered owner', { part: 'hood' }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0, `stale owner case ${staleOwnerCase}`);
  assert.equal(h.calls.add, 2, `stale owner case ${staleOwnerCase}`);
  staleOwnerCase++;
}

// Registry lifetime remains car-scoped, and noReg still bypasses reuse and registration.
{
  const h = harness();
  h.apply(zone('Car A hood', { part: 'hood' }, '#aa2200', 'base::gloss'));
  h.currentSignature = 'car-b';
  h.apply(zone('Car B hood', { part: 'hood' }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0);
  assert.equal(h.calls.add, 2);
}
{
  const h = harness();
  h.apply(zone('Hood owner', { part: 'hood' }, '#aa2200', 'base::gloss'));
  h.apply(zone('Hood owner', { part: 'hood' }, '#2244cc', 'base::matte'), { noReg: true });
  assert.equal(h.calls.edit, 0);
  assert.equal(h.calls.add, 2);
  assert.equal(Object.keys(h.api.registry()).length, 1);
}

// Compiling and abandoning part plans cannot project ownership before a commit.
{
  const h = harness();
  h.apply(zone('Hood owner', { part: 'hood' }, '#aa2200', 'base::gloss'));
  const key = h.api.editKey({ part: 'hood' }), owner = h.api.registry()[key];
  const first = h.plan(zone('Hood matte plan', { part: 'hood' }, 'source', 'base::matte'));
  const second = h.plan(zone('Hood blue plan', { part: 'hood' }, '#2244cc', 'base::matte', { finishExplicit: false }));
  assert.equal(first.compiled.merged, 1); assert.equal(second.compiled.merged, 1);
  assert.equal(first.queue[0]._spbPartOwnerName, 'Hood owner');
  assert.equal(second.queue[0]._spbPartOwnerName, 'Hood owner');
  assert.equal(h.api.registry()[key], owner, 'both plans leave the last committed owner unchanged');
  assert.deepEqual(Object.keys(h.api.pending()), [], 'abandoned part plans create no pending registry state');
  assert.equal(h.zones[0].base, 'gloss'); assert.equal(h.zones[0].baseColor, '#aa2200');
}

// Failed ZoneKit results cannot commit a part rename or material change.
{
  const h = harness();
  h.apply(zone('Hood owner', { part: 'hood' }, '#aa2200', 'base::gloss'));
  const key = h.api.editKey({ part: 'hood' }), beforeOwner = h.api.registry()[key];
  const bad = h.plan(zone('Rejected hood material', { part: 'hood' }, 'source', 'base::not-a-real-finish'));
  const committed = h.commit(bad);
  assert.equal(committed.results[0].ok, false, 'real ZoneKit rejects the unknown finish');
  assert.equal(h.api.registry()[key], beforeOwner, 'failed ZoneKit result retains the prior committed owner');
  assert.equal(h.zones[0].name, 'Hood owner'); assert.equal(h.zones[0].base, 'gloss');
}

// Whole-body zones remain excluded, while existing nonpart color/layer reuse remains intact.
{
  const h = harness();
  h.apply(zone('Whole car', { everything: true }, '#aa2200', 'base::gloss'));
  h.apply(zone('Whole car', { everything: true }, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 0);
  assert.equal(h.calls.add, 2);
}
for (const region of [{ layers: ['Body'] }, { colors: ['#112233'] }]) {
  const h = harness();
  h.apply(zone('Existing selector', region, '#aa2200', 'base::gloss'));
  h.apply(zone('Existing selector', region, '#2244cc', 'base::matte'));
  assert.equal(h.calls.edit, 1, `${JSON.stringify(region)} retains existing edit reuse`);
  assert.equal(h.calls.add, 1);
}

console.log('PASS ai_part_followup_contract.cjs (real zone kit, part follow-up, mask ownership, registry guards, existing reuse)');
