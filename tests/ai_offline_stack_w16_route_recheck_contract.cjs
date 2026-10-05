'use strict';
// W14 independent oracle was frozen before reading current production sources.
const crypto = require('node:crypto');
const cases = [
  { id: 'W14-01', text: 'Put a matte black base on only the hood, then layer silver pearl flakes over it.', expected: 'complete hood stack: matte black base plus silver pearl-flake overlay; no other part' },
  { id: 'W14-02', text: 'On the roof, apply a navy metallic base and a fine silver flake layer above it.', expected: 'complete roof stack: navy metallic base plus silver-flake overlay' },
  { id: 'W14-03', text: 'Make the left side gloss red and put a subtle pearl-flake effect over the red.', expected: 'complete left-side stack: gloss red base plus pearl-flake overlay' },
  { id: 'W14-04', text: 'Make both sides satin blue with silver flake, leaving the hood and roof unchanged.', expected: 'complete left+right side stacks with satin blue and silver flake; hood and roof untouched, or ask without mutation' },
  { id: 'W14-05', text: 'Recolor only the hood green, keeping its current chrome finish.', expected: 'hood color-only update; preserve current chrome finish' },
  { id: 'W14-06', text: "Keep the roof's current navy color; change only its finish to satin.", expected: 'roof finish-only update; preserve current navy color' },
  { id: 'W14-07', text: 'Make the hood blue matte, the roof gold gloss, and keep every other panel untouched.', expected: 'two separate scoped jobs; no body zone; ask rather than partial if safe ownership cannot be proven' },
  { id: 'W14-08', text: "Apply black matte paint to the entire body, except keep the roof's existing carbon finish.", expected: 'clarify or prove explicit body-minus-roof selection; never silently repaint roof' },
  { id: 'W14-09', text: 'Change the whole car to gloss red while leaving the hood exactly as it is.', expected: 'clarify or prove explicit whole-body exclusion for hood; no implicit whole-car zone' },
  { id: 'W14-10', text: 'Add pearl flakes to the existing hood without changing its color or finish.', expected: 'texture-only overlay on hood if supported; otherwise truthful ask and no queue' },
  { id: 'W14-11', text: 'Make the roof matte black with a gold carbon-weave overlay, but keep its current paint color.', expected: 'clarify conflicting matte-black base and keep-current-color constraints; no partial queue' },
  { id: 'W14-12', text: 'Make only the right side blue and add a silver stripe across the hood.', expected: 'complete independent side recolor and hood stripe, or ask without partially applying either action' },
  { id: 'W14-13', text: 'Give the hood a satin gold base with pearl flakes, and add a chrome pinstripe along the roof.', expected: 'complete hood stack plus roof pinstripe, or ask without dropping a requested action' },
  { id: 'W14-14', text: 'Add a gloss clearcoat to the current matte black roof while keeping the black paint.', expected: 'roof clearcoat/material-channel operation preserving black base, or truthful ask with no queue' }
];
const knownEarlier = { id: 'W14-KNOWN', text: 'Make only the hood matte black base with silver pearl flakes on top.', expected: 'complete hood matte-black base plus silver pearl-flake overlay, or truthful ask without applying only the base' };
const canonical = JSON.stringify({ cases, knownEarlier });
const oracleHash = crypto.createHash('sha256').update(canonical).digest('hex').toUpperCase();
if (process.argv.includes('--freeze-only')) { console.log(JSON.stringify({ fresh: cases.length, knownEarlier: knownEarlier.id, oracleHash, cases, knownEarlier }, null, 2)); process.exit(0); }

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `production ${name} exists`);
  const brace = source.indexOf('{', start); let depth = 0, quote = null, lineComment = false, blockComment = false, escaped = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (lineComment) { if (c === '\n') lineComment = false; continue; }
    if (blockComment) { if (c === '*' && n === '/') { blockComment = false; i++; } continue; }
    if (quote) { if (escaped) { escaped = false; continue; } if (c === '\\') { escaped = true; continue; } if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { lineComment = true; i++; continue; }
    if (c === '/' && n === '*') { blockComment = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated production function ${name}`);
}
const w = { console, Promise, document: {} }; w.window = w; vm.createContext(w);
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
const D = w.SpbProDesign, E = w.SpbProEdit;
const env = { palette: [
  { hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 },
  { hex: '#f1f1ee', share_pct: 14 }, { hex: '#1347a8', share_pct: 5 }
], layers: [] };
const aiSnapshot = '_easy_claude_work/ai14h_generation2_sources/js/spb-pro-ai.js';
const aiSource = fs.readFileSync(path.join(root, aiSnapshot), 'utf8');
const route = {
  window: Object.assign(w, { SpbMaterialControls: undefined, SpbProElements: undefined }), console, Promise, D, E,
  AI: { cached: () => ({ configured: false }) }, _busy: false, _skipParts: true, _absent: {}, CAR: null,
  _offlineLast: null, _advLast: null, _advRejected: [], _advDislikes: [], _forcedIdeaCols: null, _reqText: '', _specOnlyReq: false,
  _beforeImg: null, _progress: '', _editReg: {}, _editRegPendingBefore: {}, _editRegSig: 'stack-car', zones: [],
  captureOriginal() {}, intentSpecOnly: () => false, editYieldsToStack: () => false, elementRunCurrent: () => true,
  elementPaintChangedResult: () => ({ cancelled: true }), offlineFirst: () => true, selfHelpClaim: () => null, selfHelpResult: x => x,
  advisorIntent: () => null, advisorEnv: () => ({}), advisorReply() { throw new Error('advisor must not own a concrete stack edit'); },
  START_OVER_RE: /^\s*(?:start over|new design)\b/i, SMALL_HELLO_RE: /^\s*(hi|hello)\b/i, SMALL_THANKS_RE: /^\s*thanks\b/i,
  CANT_RE: /$a/, NUM_FIX_RE: /$a/, NOT_ELEM_RE: /$a/, layerVisRequest: () => null, lookEntry: () => null, offlineCannot: () => null,
  offlineHowtoPeek: () => false, offlineHowto: () => null,
  offlineSpecAsk: () => Promise.resolve({ route: 'ask', text: 'I could not verify the requested finish scope, so nothing was changed.', queue: [] }),
  offlinePartAsk: () => Promise.resolve({ route: 'ask', text: 'I could not verify the requested part scope, so nothing was changed.', queue: [] }),
  warm: () => Promise.resolve(), render() {}, prepEnv: () => Promise.resolve(env), resolveLook: () => Promise.resolve(null), elementKinds: () => [],
  exclTargets: () => [], markPartFollowupQueue() {}, editOverlapNote: () => '', editOverlapKinds: () => [], exclNotes: () => [],
  layersInfo: () => [],
  _panel: null, _log: [], TEACH_RE: /never-match/, QUESTION_RE: /$a/, CHECK_AGAIN_RE: /$a/, elemCurrentCard: () => null,
  elementPaintSig: () => '', elementRunIdentity: () => null, elemReplyAction: () => null, runElemAction: () => false,
  elemOwnsText: () => false, carSig: () => 'stack-car', partRegHas: (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key),
  normaliseSpec: spec => spec, protectDecals() {}, friendlyZoneError: msg => String(msg || ''),
  editPlural: label => /(numbers|sponsors|stripes|logos|decals|lines|bands|accents|panels|parts|bumpers)$/.test(String(label)),
  failPart: null, committed: [],
  editPlan: text => E.plan(text, env),
  makeTools(queue) { return [
    { name: 'add_zone', handler(spec) { const item = { kind: 'add', spec: JSON.parse(JSON.stringify(spec)) }; queue.push(item); route.committed.push(item); return {}; } },
    { name: 'edit_zone', handler(args) { const spec = {}; Object.keys(args || {}).forEach(k => { if (!['zone','zone_id','zone_name','expect_name','_spbPartRegKey','_spbPartOwnerName','_spbPartForgetKey'].includes(k)) spec[k] = args[k]; }); const item = { kind: 'edit', zone: Number(args.zone) || 0, spec, _spbPartRegKey: args._spbPartRegKey || null, _spbPartOwnerName: args._spbPartOwnerName || null, args }; queue.push(item); route.committed.push(item); return {}; } }
  ]; },
  editReply(text, chips, options) { return { route: options && options.queue ? 'edit' : 'ask', text, chips: chips || [], queue: options && options.queue || [], tools: options && options.tools || [] }; },
  askCore() { throw new Error('provider call prohibited in stack review'); }
};
vm.createContext(route);
const hashMask = mask => { let h = 2166136261; for (const b of mask) h = Math.imul(h ^ (Number(b) & 255), 16777619); return mask.length + ':' + (h >>> 0).toString(36); };
function seedOwned(part, finish, color) {
  const region = { part }, key = route.editKey(region), mask = new Uint8Array([11, 22, 33]), name = `Owned ${part}`;
  route.zones = [{ id: `z-${part}`, name, muted: false, regionMask: mask, useRegion: true, finishKey: finish, colour: color, _aiPartProv: { r: JSON.stringify(region), z: hashMask(mask), l: '', e: '' } }];
  route._editReg = { [key]: name }; route._editRegPendingBefore = {}; route._editRegSig = 'stack-car';
}
function clearState() { route.zones = []; route._editReg = {}; route._editRegPendingBefore = {}; route._editRegSig = 'stack-car'; route.committed = []; route._offlineLast = null; route._advLast = null; route._busy = false; }
function partsOf(result) { return Array.from(result && result.queue || [], q => q.kind === 'add' ? q.spec.region && q.spec.region.part : q.spec && q.spec.region && q.spec.region.part || q._spbPartRegKey && JSON.parse(q._spbPartRegKey).p).filter(Boolean).sort(); }
for (const name of ['partRegionKey','editKey','editPlural','offlineScopeReply','offlineMaterialPlan','offlineMaterialAsk','offlineLookAsk','queueEditZones','offlineCoveredPartAsk','offlineEditAsk','offlineElementAsk','offlineSpecAsk','offlinePartAsk','offlineCanHandle','offlineAsk','offlineAskCore']) {
  vm.runInContext(extractFunction(aiSource, name), route, { filename: `js/spb-pro-ai.js#${name}` });
}

const expectations = {
  'W14-01': { parts: ['hood'], stack: ['pearl','flake'] },
  'W14-02': { parts: ['roof'], stack: ['flake'] },
  'W14-03': { parts: ['left side'], stack: ['pearl','flake'] },
  'W14-04': { parts: ['left side','right side'], preserve: ['hood','roof'], stack: ['flake'] },
  'W14-05': { parts: ['hood'], preserveFinish: 'base::chrome' },
  'W14-06': { parts: ['roof'], preserveColor: '#1347a8' },
  'W14-07': { parts: ['hood','roof'], requireAll: true },
  'W14-08': { parts: ['body'], preserve: ['roof'], requireAskUnlessExclusion: true },
  'W14-09': { parts: ['body'], preserve: ['hood'], requireAskUnlessExclusion: true },
  'W14-10': { parts: ['hood'], preserveBase: true, stack: ['pearl','flake'] },
  'W14-11': { parts: ['roof'], requireAsk: true },
  'W14-12': { parts: ['right side','hood'], requireAll: true },
  'W14-13': { parts: ['hood','roof'], requireAll: true, stack: ['pearl','flake','pinstripe'] },
  'W14-14': { parts: ['roof'], preserveBase: true, requireAskUnlessClearcoat: true },
  'W14-KNOWN': { parts: ['hood'], stack: ['pearl','flake'] }
};
function compactPlan(plan) {
  if (!plan) return null;
  const zones = plan.zones || plan.ops || [];
  return { kind: plan.kind || null, exactPart: !!plan.exactPart, complete: plan.complete, unknown: plan.unknown || [], text: plan.text || '', zones: Array.from(zones, z => ({
    part: z.region && z.region.part || z.target && (z.target.part || z.target.word) || null,
    color: z.color || z.colour && z.colour.hex || null,
    finish: z.finish || z.look && (z.look.id || z.look.label) || null,
    materialKeys: Object.keys(z).filter(k => /pattern|flake|spec|layer|overlay|clearcoat/i.test(k)),
    materialText: JSON.stringify(z).match(/pearl|flake|carbon|weave|clearcoat|pinstripe/ig) || []
  })) };
}
function materialSatisfied(serialized, required) { return required.every(word => new RegExp(word, 'i').test(serialized)); }
(async () => {
  const results = [];
  for (const item of [...cases, knownEarlier]) {
    clearState();
    if (item.id === 'W14-05') seedOwned('hood', 'base::chrome', '#141416');
    if (item.id === 'W14-06') seedOwned('roof', 'base::gloss', '#1347a8');
    const compound = D.compoundPlan(item.text);
    const parsed = E.plan(item.text, env);
    const compiled = parsed && parsed.kind === 'ops' ? E.compile(parsed, env) : null;
    let response;
    try { response = await route.offlineAsk(item.text, { noAdvisor: true }); }
    catch (e) { response = { error: String(e && e.stack || e), queue: [] }; }
    const queue = response && response.queue || [];
    const serialized = JSON.stringify({ compound, parsed, compiled, queue, responseText: response && response.text });
    const actualParts = partsOf(response);
    const expected = expectations[item.id];
    const allParts = expected.parts.every(p => actualParts.includes(p));
    const noUnknownPart = actualParts.every(p => expected.parts.includes(p));
    const noDuplicateParts = new Set(actualParts).size === actualParts.length;
    const exactPartSet = actualParts.length === expected.parts.length && allParts && noUnknownPart && noDuplicateParts;
    const stackTerms = expected.stack ? materialSatisfied(serialized, expected.stack) : true;
    const preservationAsk = queue.length === 0 && response && !response.error;
    let unsafe = false, full = false;
    if (expected.requireAsk) unsafe = queue.length > 0;
    else if (expected.requireAskUnlessExclusion) unsafe = queue.length > 0 && !expected.preserve.every(p => new RegExp(p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(serialized));
    else if (expected.requireAll) unsafe = queue.length > 0 && !(exactPartSet && stackTerms);
    else if (queue.length > 0) unsafe = !exactPartSet || !stackTerms;
    if (queue.length && !unsafe && exactPartSet && stackTerms && !response.error) full = true;
    results.push({ id: item.id, text: item.text, expected: item.expected, compound: compactPlan(compound), edit: compactPlan(parsed), compiled: compactPlan(compiled), route: queue.length ? (unsafe ? 'partial-edit' : 'edit') : (response && response.error ? 'error' : 'ask'), parts: actualParts, duplicateParts: !noDuplicateParts, exactPartSet, queuedCount: queue.length, reply: response && response.text || '', error: response && response.error || '', preservationAsk, full, unsafe, rawQueue: queue });
  }
  const sourceHashes = {};
  for (const f of ['js/spb-pro-ai.js','js/spb-pro-edit.js','js/spb-pro-design.js']) sourceHashes[f] = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, f === 'js/spb-pro-ai.js' ? aiSnapshot : f))).digest('hex').toUpperCase();
  const supported = results.filter(r => r.full).length, unsafe = results.filter(r => r.unsafe).length, asked = results.filter(r => r.preservationAsk).length;
  const report = {
    review: 'W16 parent unchanged W14-oracle replay against gen2 proAI snapshot and repaired D/current E', date: '2026-10-04',
    status: unsafe ? 'BLOCKED_UNSAFE_PARTIAL' : (supported ? 'MIXED_SAFE_INCOMPLETE' : 'SAFE_BUT_INCOMPLETE'),
    frozen_oracle: { hash: oracleHash, fresh_cases: cases.length, separately_kept_known_case: knownEarlier.id, cases: [...cases, knownEarlier] },
    production_freeze: {
      requested_frozen_hashes: { 'js/spb-pro-ai.js': '115F602D49E465B6F49530B07A4C2E4B81E8D6089C2D8204BCAE9D57807690D4', 'js/spb-pro-edit.js': 'D4CDD87EFC9A0FFAB5AA923134C13BCBA722E68FB91F1F4899EA16D61B204F0C', 'js/spb-pro-design.js': '0F5A99F5ECCA374C955DF54AE31E6B1E4F4B5EA559284C396C84BF0C38BB2D7B' },
      observed_during_review: sourceHashes,
      source_path: aiSnapshot, drift: 'Parent intentionally replayed unchanged W14 oracle against frozen gen2 proAI115f and current repaired D0533/Ea328; no moving proAI used.'
    },
    production_hashes_sha256: sourceHashes,
    counts: { total: results.length, full_executable_requests: supported, conservative_asks_or_no_queue: asked, unsafe_partial_applications: unsafe, errors: results.filter(r => r.route === 'error').length },
    results,
    source_hotspots: [
      { file: 'js/spb-pro-design.js', line: 280, note: 'offlineSpec recognizes spec-only looks; it relies on compoundPlan(text) to decline compound requests before making a spec-only plan.' },
      { file: 'js/spb-pro-design.js', line: 678, note: 'compoundPlan returns null for W14-11 even though it contains multiple/conflicting paint/material instructions.' },
      { file: 'js/spb-pro-ai.js', line: 985, note: 'offlineSpecAsk applies each parsed spec zone; W14-11 reaches this path with only the matte look extracted and the black/carbon-weave/preserve-color clauses omitted.' },
      { file: 'js/spb-pro-ai.js', line: 1904, note: 'offlineAskCore falls through to the compound/edit/looks routes after the compound planner misses W14-11.' }
    ],
    external_post_freeze_observation: {
      credit: 'Parent-reported native gen2 case only; not part of the frozen oracle and not executed by this reviewer.',
      request: 'Make only the roof chrome and keep its red paint color.',
      observed_by_parent: 'Added a Chrome Cross Colors roof zone with a Cross Colors pattern (7 total zones and a new UUID) instead of editing the existing six-zone/UUID owner with chrome only.',
      expected: 'Reuse the existing roof owner; preserve red paint and add only chrome finish, with no new pattern or zone.'
    },
    next_fixes: [],
    limits: ['No renderer, provider, native application, or browser was run. The real planner, editor compiler, and offline route were invoked; queue handlers are mocks, so route queue output is not a rendered or applied paint.', 'A safe ask/no queue is recorded as incomplete support, not as successful stack accuracy.', 'Unknown arbitrary graphic artwork is not considered complete unless the actual queue fully represents every requested action.']
  };
  if (results.some(r => r.id === 'W14-KNOWN' && !r.full && !r.unsafe)) report.next_fixes.push('Known prior hood matte-black base + silver pearl-flake wording is still incomplete: preserve all material clauses or ask before applying any subset.');
  if (results.some(r => r.id === 'W14-05' && !r.full && !r.unsafe)) report.next_fixes.push('Current-finish roof/hood color-only requests should remain editable while preserving the owned finish; record preservation in the edit rather than broadening to a repaint.');
  if (results.some(r => ['W14-08','W14-09'].includes(r.id) && r.unsafe)) report.next_fixes.push('Whole-body assignment with a named preserved panel must be represented with a verified native exclusion, or clarified before queueing.');
  if (results.some(r => r.id === 'W14-11' && r.unsafe)) report.next_fixes.push('Do not let offlineSpec consume just “matte” from a compound/conflicting request. W14-11 queues a matte spec-only roof zone while dropping black base, gold carbon weave, and explicit keep-current-color; make the composition owner return a clarification/no-op unless every clause is covered.');
  if (results.some(r => r.unsafe)) report.next_fixes.push('Any request combining multiple independent parts or material layers must not queue a proper subset when a later action is absent/unsupported.');
  const reportPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_W16_STACK_ROUTE_RECHECK_2026-10-03.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, counts: report.counts, next_fixes: report.next_fixes, sourceHashes }, null, 2));
  if (unsafe) process.exitCode = 2;
})().catch(err => { console.error(err); process.exitCode = 1; });


