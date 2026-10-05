'use strict';

// Independent integration probe: the existing follow-up contract gives its
// fake add callback a `region` field, but Pro's real zone kit may store masks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const zoneSource = fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8');

function extractFunction(source, name) {
  const marker = `function ${name}(`;
  const start = source.indexOf(marker);
  assert(start >= 0, `${name} exists`);
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

function makeRealZoneKit() {
  const zones = [];
  const fingerprint = { car: 'review-car-layout', layout: 'review-layout-a', elements: 'review-element-paint' };
  const context = {
    console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt,
    zones, selectedZoneIndex: 0,
    BASES: [], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [],
    document: { getElementById: () => ({ width: 32, height: 32 }) },
    addZone() {
      zones.push({ id: `zone-${zones.length + 1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] });
    },
    SpbProCar: {
      findIsland: name => ({ id: String(name), name: String(name), front: true, up: true }),
      parts: () => ['hood'], canon: name => String(name),
      signature: () => fingerprint.car, layoutSig: () => fingerprint.layout,
      maskFor: name => ({ mask: new Uint8Array(32 * 32), island: { name: String(name) }, islands: [{ name: String(name) }] })
    },
    SpbProElements: { sig: () => fingerprint.elements }
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(zoneSource, context, { filename: 'js/spb-pro-zone-kit.js' });
  return { context, api: context.SpbProZone, fingerprint };
}

function makeQueue(realKit) {
  const context = {
    console, Uint8Array, Float32Array, JSON, Math, isFinite,
    zones: realKit.context.zones,
    carSig: () => realKit.context.SpbProCar.signature(),
    editPlural: label => /(numbers|sponsors|stripes|logos|decals|lines|bands|accents|panels|parts|bumpers)$/.test(String(label)),
    friendlyZoneError: String,
    calls: { add: 0, edit: 0 },
    SpbProCar: realKit.context.SpbProCar,
    SpbProElements: realKit.context.SpbProElements,
    _gen: 0, applyLayerOps: () => ({ lines: [], failed: [], undoSteps: 0 }),
    Z: { batch: (ops, label, opts) => realKit.api.batch(ops, label, opts) }
  };
  context.window = context;
  context.CAR = context.SpbProCar;
  const declarations = ['partRegionKey', 'editKey', 'partRegHas', 'partOwnerCurrent', 'partRegistryState', 'rollbackPendingPartRegistry', 'clearPartRegistryPending', 'reconcilePartRegistry', 'registerAppliedPartZones', 'markPartFollowupQueue', 'applyQueue', 'queueEditZones'].map(name => extractFunction(aiSource, name)).join('\n');
  vm.createContext(context);
  vm.runInContext(`${declarations}\nvar _editReg = {}, _editRegSig = null, _editRegPendingBefore = {}; this.api = { queue: queueEditZones, mark: markPartFollowupQueue, commit: applyQueue, registry: function(){return _editReg;} };`, context,
    { filename: 'js/spb-pro-ai.js#queueEditZones+applyQueue' });
  context.add = spec => { context.calls.add++; context.ops.push({ kind: 'add', spec }); return { ok: true }; };
  context.edit = args => {
    context.calls.edit++;
    const target = context.zones.find(z => z.id === args.zone_id);
    if (!target) return { error: 'missing zone' };
    const index = context.zones.indexOf(target), update = Object.assign({}, args); delete update.zone_id;
    const op = { kind: 'edit', zone: index, spec: update };
    for (const key of ['_spbPartRegKey', '_spbPartOwnerName', '_spbPartForgetKey']) if (update[key]) { op[key] = update[key]; delete update[key]; }
    context.ops.push(op); return { ok: true };
  };
  context.plan = spec => { context.ops = []; const compiled = context.api.queue({ zones: [spec] }, context.add, context.edit); return { compiled, ops: context.ops }; };
  context.commit = plan => { context.api.mark(plan.ops); return context.api.commit(plan.ops, 'review contract'); };
  context.apply = spec => { const plan = context.plan(spec); plan.commit = context.commit(plan); return plan.compiled; };
  return context;
}

const kit = makeRealZoneKit();
const queue = makeQueue(kit);
const spec = color => ({ name: 'Hood repaint', region: { part: 'hood', portion: 'upper' }, color,
  _meta: { label: 'hood', kind: 'colour', finishExplicit: false } });

const initialPlan = queue.plan(spec('#aa2200'));
assert.equal(kit.context.zones.length, 0, 'compiling does not mutate the real ZoneKit');
assert.equal(Object.keys(queue.api.registry()).length, 0, 'part ownership is not registered before ZoneKit commit');
const initialCommit = queue.commit(initialPlan);
assert.equal(initialCommit.results[0].ok, true);
assert.equal(kit.context.zones.length, 1, 'the first same-part request creates one real Pro zone');
assert.equal(kit.context.zones[0].region, undefined,
  'real Pro zones store regionMask/useRegion/_regionDesc, not the input region object');
assert.ok(kit.context.zones[0].regionMask instanceof Uint8Array,
  'the named-part selector was applied to the actual zone mask');
const provenance = kit.context.zones[0]._aiPartProv;
assert.ok(provenance, 'the actual zone receives compact ownership provenance');
assert.deepEqual(Object.keys(provenance).sort(), ['e', 'l', 'p', 'r', 'z'],
  'provenance stores selector and fingerprints, not full pixel buffers');
assert.equal(typeof provenance.r, 'string');
assert.equal(typeof provenance.z, 'string');
assert.equal(typeof provenance.p, 'string');
assert.ok(JSON.stringify(provenance).length < 512, 'provenance stays compact and serializable');
assert.equal(kit.context.SpbProCar.signature(), 'review-car-layout',
  'the car signature is a stable value, not a fresh per-call token');

const committedKey = Object.keys(queue.api.registry())[0], committedName = queue.api.registry()[committedKey];
const abandonedOne = queue.plan(spec('#1188aa'));
const abandonedTwo = queue.plan(spec('#aa7722'));
assert.equal(abandonedOne.compiled.merged, 1); assert.equal(abandonedTwo.compiled.merged, 1);
assert.equal(abandonedOne.ops[0]._spbPartOwnerName, committedName);
assert.equal(abandonedTwo.ops[0]._spbPartOwnerName, committedName);
assert.equal(queue.api.registry()[committedKey], committedName, 'both abandoned plans preserve the committed map');
assert.equal(kit.context.zones[0].baseColor, '#aa2200', 'abandoned plans leave the real zone pixels/material untouched');

const editCallsBeforeCommit = queue.calls.edit;
queue.apply(spec('#2244cc'));
assert.equal(queue.calls.edit, editCallsBeforeCommit + 1, 'a later matching part request edits the real zone');
assert.equal(queue.calls.add, 1, 'a later matching part request does not create a duplicate real zone');
assert.equal(kit.context.zones.length, 1, 'same-part follow-up remains one zone in Pro storage');
assert.equal(kit.context.zones[0].baseColor, '#2244cc', 'the actual Pro zone receives the new colour');
assert.equal(queue.api.registry()[committedKey], committedName, 'a successful same-name update keeps its committed owner');

const failedPlan = queue.plan({ name: 'Rejected hood finish', region: { part: 'hood', portion: 'upper' }, color: 'source', finish: 'base::missing-finish',
  _meta: { label: 'hood', kind: 'finish', finishExplicit: true } });
const failedCommit = queue.commit(failedPlan);
assert.equal(failedCommit.results[0].ok, false, 'real ZoneKit rejects an unknown finish');
assert.equal(queue.api.registry()[committedKey], committedName, 'failed ZoneKit result cannot register the planned rename');
assert.equal(kit.context.zones[0].name, committedName);

// A same selector is rejected after the live element paint identity changes.
{
  const changedKit = makeRealZoneKit();
  const changedQueue = makeQueue(changedKit);
  changedQueue.apply(spec('#aa2200'));
  changedKit.fingerprint.elements = 'review-element-paint-2';
  changedQueue.apply(spec('#2244cc'));
  assert.equal(changedQueue.calls.edit, 0, 'an element-paint change invalidates old part provenance');
  assert.equal(changedQueue.calls.add, 2);
}
console.log('PASS independent staged actual-zone follow-up review (commit-only registration, abandoned plans, failed results, reuse and stale identity)');
