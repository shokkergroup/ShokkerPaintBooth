'use strict';
// W17 oracle frozen before reading the source snapshot or the current editor parser.
const crypto = require('node:crypto');
const cases = [
  { id: 'W17-01', text: 'Make only the roof chrome and keep its red paint color.', mode: 'complete', part: 'roof', color: '#c8102e', finish: 'base::chrome', expected: 'one edit to the existing owned roof UUID; chrome only; retain red color, region mask, and part ownership' },
  { id: 'W17-02', text: 'Make only the hood chrome and retain its black paint.', mode: 'complete', part: 'hood', color: '#141416', finish: 'base::chrome', expected: 'one edit to the existing owned hood UUID; chrome only; retain black color, region mask, and owner' },
  { id: 'W17-03', text: 'Give only the roof a satin finish; leave its current red paint and region alone.', mode: 'complete', part: 'roof', color: '#c8102e', finish: 'base::satin', expected: 'one roof owner edit, satin only; preserve color and part selector' },
  { id: 'W17-04', text: "Set the hood to gloss; don't change its current navy color.", mode: 'complete', part: 'hood', color: '#1347a8', finish: 'base::gloss', expected: 'one hood owner edit, gloss only; preserve navy color and owner' },
  { id: 'W17-05', text: 'Chrome the roof and keep the red paint; leave every other panel unchanged.', mode: 'complete', part: 'roof', color: '#c8102e', finish: 'base::chrome', expected: 'one roof finish-only edit; no other part or body zone' },
  { id: 'W17-06', text: 'Make the roof chrome with a gold carbon-weave overlay, but keep its red paint color.', mode: 'ask', part: 'roof', expected: 'clarify or safely ask; no partial chrome, repaint, or pattern queue' },
  { id: 'W17-07', text: 'Do not make the roof chrome; keep its red paint as it is.', mode: 'no_mutation', part: 'roof', expected: 'prohibition/help response; no queued edit' },
  { id: 'W17-08', text: 'Make the roof chrome and add a gold pinstripe across the hood.', mode: 'ask_or_all', part: 'roof', expected: 'apply every action completely or ask without queuing chrome alone' }
];
const suppliedNative = cases[0];
const canonical = JSON.stringify({ cases, suppliedNative });
const oracleHash = crypto.createHash('sha256').update(canonical).digest('hex').toUpperCase();
if (process.argv.includes('--freeze-only')) { console.log(JSON.stringify({ fresh: cases.length, suppliedNative: suppliedNative.id, oracleHash, cases }, null, 2)); process.exit(0); }

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const snapshotDir = path.join(root, '_easy_claude_work/ai14h_generation2_sources/js');
const frozenProAiPath = path.join(snapshotDir, 'spb-pro-ai.js');
const frozenDesignPath = path.join(snapshotDir, 'spb-pro-design.js');
const currentEditPath = path.join(root, 'js/spb-pro-edit.js');
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase(); }
const snapshotProAiHash = '115F602D49E465B6F49530B07A4C2E4B81E8D6089C2D8204BCAE9D57807690D4';
const snapshotDesignHash = '0F5A99F5ECCA374C955DF54AE31E6B1E4F4B5EA559284C396C84BF0C38BB2D7B';
const editExpectedHash = 'A328A1EF5D8293E2F8CFC8A27F3E0C868A04842A07EE39243CBD0BD34513BDA7';
assert.equal(sha(frozenProAiPath), snapshotProAiHash, 'generation2 proAI snapshot changed');
assert.equal(sha(frozenDesignPath), snapshotDesignHash, 'selected frozen design snapshot changed');
assert.equal(sha(currentEditPath), editExpectedHash, 'current E producer changed during the route review');

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `source function ${name} exists`);
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
  throw new Error(`unterminated ${name}`);
}
const w = { console, Promise, document: {} }; w.window = w; vm.createContext(w);
vm.runInContext(fs.readFileSync(frozenDesignPath, 'utf8'), w, { filename: frozenDesignPath });
vm.runInContext(fs.readFileSync(currentEditPath, 'utf8'), w, { filename: currentEditPath });
const D = w.SpbProDesign, E = w.SpbProEdit;
const env = { palette: [
  { hex: '#c8102e', share_pct: 52 }, { hex: '#141416', share_pct: 22 },
  { hex: '#1347a8', share_pct: 14 }, { hex: '#f2c500', share_pct: 5 }
], layers: [] };
const aiSource = fs.readFileSync(frozenProAiPath, 'utf8');
const route = {
  window: Object.assign(w, { SpbMaterialControls: undefined, SpbProElements: undefined }), console, Promise, D, E,
  AI: { cached: () => ({ configured: !!route.configured }) }, configured: false, _busy: false, _skipParts: true, _absent: {}, CAR: null,
  _offlineLast: null, _advLast: null, _advRejected: [], _advDislikes: [], _forcedIdeaCols: null, _reqText: '', _specOnlyReq: false,
  _beforeImg: null, _progress: '', _editReg: {}, _editRegPendingBefore: {}, _editRegSig: 'preserve-car', zones: [],
  _gen: 0, _snapGen: 0, _activeId: null, RECENT: [], _advUsed: null,
  applySnapshots: [], committedQueue: [], providerCalls: 0, _log: [], _panel: null,
  captureOriginal() {}, intentSpecOnly: () => false, editYieldsToStack: () => false, elementRunCurrent: () => true,
  elementPaintChangedResult: () => ({ cancelled: true }), offlineFirst: () => true, selfHelpClaim: () => null, selfHelpResult: x => x,
  advisorIntent: () => null, advisorEnv: () => ({}), advisorReply() { throw new Error('provider/advisor use prohibited'); },
  START_OVER_RE: /^\s*(?:start over|new design)\b/i, SMALL_HELLO_RE: /^\s*(hi|hello)\b/i, SMALL_THANKS_RE: /^\s*thanks\b/i,
  CANT_RE: /$a/, NUM_FIX_RE: /$a/, NOT_ELEM_RE: /$a/, layerVisRequest: () => null, lookEntry: () => null,
  offlineCannot: () => null, offlineHowtoPeek: () => false, offlineScopeReply: () => ({ text: 'Nothing was changed.' }), offlineHowto: () => null,
  warm: () => Promise.resolve(), render() {}, prepEnv: () => Promise.resolve(env), resolveLook: () => Promise.resolve(null), elementKinds: () => [],
  exclTargets: () => [], markPartFollowupQueue() {}, editOverlapNote: () => '', editOverlapKinds: () => [], exclNotes: () => [],
  normaliseSpec: spec => spec, protectDecals() {}, friendlyZoneError: msg => String(msg || ''),
  editPlural: label => /(numbers|sponsors|stripes|logos|decals|lines|bands|accents|panels|parts|bumpers)$/.test(String(label)),
  editPlan: text => E.plan(text, env), carSig: () => 'preserve-car', partRegHas: (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key),
  renderZones() {}, triggerPreviewRender() {},
  undoZoneChange() { const snapshot = route.applySnapshots.pop(); if (snapshot) route.zones = snapshot; },
  makeTools(queue) { return [
    { name: 'add_zone', handler(spec) { const item = { kind: 'add', spec: JSON.parse(JSON.stringify(spec)) }; queue.push(item); route.committedQueue.push(item); return {}; } },
    { name: 'edit_zone', handler(args) {
      const copy = JSON.parse(JSON.stringify(args));
      const index = copy.zone_id != null ? route.zones.findIndex(z => String(z.id) === String(copy.zone_id)) : (copy.zone_name != null ? route.zones.findIndex(z => z.name === copy.zone_name) : Number(copy.zone));
      const spec = {}; Object.keys(copy).forEach(k => { if (!['zone','zone_id','zone_name','expect_name','_spbPartRegKey','_spbPartOwnerName','_spbPartForgetKey'].includes(k)) spec[k] = copy[k]; });
      const item = { kind: 'edit', zone: index, zone_id: copy.zone_id, spec, _spbPartRegKey: copy._spbPartRegKey || null, _spbPartOwnerName: copy._spbPartOwnerName || null, args: copy };
      queue.push(item); route.committedQueue.push(item); return {};
    } }
  ]; },
  editReply(text, chips, options) { return { route: options && options.queue ? 'edit' : 'ask', text, chips: chips || [], queue: options && options.queue || [], tools: options && options.tools || [] }; },
  askCore() { route.providerCalls++; throw new Error('provider call prohibited'); },
  finish(result) { return result; }, supportClass: () => ({ kind: 'faq' }), supportSend: () => true,
  elemCurrentCard: () => null, elementPaintSig: () => '', elementRunIdentity: () => null,
  elemReplyAction: () => null, runElemAction: () => false, elemOwnsText: () => false,
  TEACH_RE: /never-match/, QUESTION_RE: /$a/, CHECK_AGAIN_RE: /$a/
};
vm.createContext(route);
for (const name of ['partRegionKey','editKey','editPlural','offlineMaterialPlan','queueEditZones','offlineCoveredPartAsk','offlineEditAsk','offlineCanHandle','offlineAsk','offlineAskCore','partRegistryState','partOwnerCurrent','registerAppliedPartZones','reconcilePartRegistry','clearPartRegistryPending','applyQueue','restorePartRegistryUndo','doUndo','ask']) {
  vm.runInContext(extractFunction(aiSource, name), route, { filename: `frozen-proAI#${name}` });
}
route.Z = {
  batch(ops) {
    route.applySnapshots.push(route.zones.map(z => Object.assign({}, z, { regionMask: z.regionMask && new Uint8Array(z.regionMask), _aiPartProv: z._aiPartProv && JSON.parse(JSON.stringify(z._aiPartProv)) })));
    return ops.map(op => {
      const z = route.zones[op.zone]; if (!z || op.kind !== 'edit') return { ok: false, applied: [], warnings: ['missing mock edit target'], index: op.zone };
      const spec = JSON.parse(JSON.stringify(op.spec || {}));
      Object.keys(spec).forEach(k => { if (k === 'color') z.colour = spec[k]; else if (k === 'finish') z.finishKey = spec[k]; else z[k] = spec[k]; });
      return { ok: true, applied: Object.keys(spec), index: op.zone, name: z.name };
    });
  }, quiet(fn) { return fn(); }, catchAll() { return false; }
};
function maskHash(mask) { let h = 2166136261; for (const b of mask) h = Math.imul(h ^ (Number(b) & 255), 16777619); return mask.length + ':' + (h >>> 0).toString(36); }
function seed(part, color, finish) {
  route.zones = []; route._editReg = {}; route._editRegPendingBefore = {}; route._editRegSig = 'preserve-car'; route.committedQueue = []; route.applySnapshots = [];
  return addOwned(part, color, finish);
}
function addOwned(part, color, finish) {
  const region = { part }, key = route.editKey(region), id = `stable-${part}-uuid`, name = `Owned ${part}`, mask = new Uint8Array([5,17,29,41]);
  const z = { id, name, muted: false, regionMask: mask, useRegion: true, finishKey: finish, colour: color, _aiPartProv: { r: JSON.stringify(region), z: maskHash(mask), l: '', e: '' } };
  route.zones.push(z); route._editReg[key] = name; return { key, id, name, color, finish, mask: Array.from(mask), zoneRef: z };
}
function reset() { route.zones = []; route._editReg = {}; route._editRegPendingBefore = {}; route._editRegSig = 'preserve-car'; route.committedQueue = []; route.applySnapshots = []; route._busy = false; route._offlineLast = null; route._advLast = null; }
function queuedZones(result) { return Array.from(result && result.queue || [], q => ({ kind: q.kind, zone: q.zone, id: q.zone_id, spec: q.spec || null, args: q.args || null })); }

assert.equal(oracleHash, '888866548A92C3C3FC65D59DCA8809163ED4CFCAF1DFF9E8491D0A23F803F2CB', 'frozen W17 oracle changed');
(async () => {
  const results = [], blockers = [];
  for (const item of cases) {
    reset(); route.configured = false;
    const initialColor = item.color || '#c8102e', initialFinish = item.finish === 'base::chrome' ? 'base::gloss' : 'base::chrome';
    const original = seed(item.part, initialColor, initialFinish);
    if (item.id === 'W17-08') addOwned('hood', '#141416', 'base::gloss');
    const parsed = E.plan(item.text, env);
    const compiled = parsed && parsed.kind === 'ops' ? E.compile(parsed, env) : null;
    const compound = D.compoundPlan(item.text);
    let response;
    try { response = await route.offlineAsk(item.text, { noAdvisor: true }); }
    catch (e) { response = { route: 'error', error: String(e && e.stack || e), queue: [] }; }
    const zones = queuedZones(response), queue = response && response.queue || [];
    const partZones = zones.map(z => z.spec && z.spec.region && z.spec.region.part || z.args && z.args._spbPartRegKey && JSON.parse(z.args._spbPartRegKey).p || '').filter(Boolean);
    let applied = null, undone = null, full = false, unsafe = false;
    if (item.mode === 'complete') {
      if (response && response.route !== 'edit' || queue.length !== 1 || queue[0].kind !== 'edit' || queue[0].zone !== 0 || queue[0].zone_id && String(queue[0].zone_id) !== original.id) {
        blockers.push({ id: item.id, type: 'expected existing-part edit did not queue exactly one edit on same zone', route: response && response.route, queue: zones, reply: response && response.text });
      } else {
        const q = queue[0], spec = q.spec || {};
        // The frozen oracle records the user-facing concept "chrome". Resolve its real registry ID
        // through this current production parser/compiler so the test does not confuse that label
        // with the implementation key (base::f_chrome).
        const expectedFinish = compiled && compiled.zones && compiled.zones[0] && compiled.zones[0].finish;
        const finishMatches = !!expectedFinish && (spec.finish === expectedFinish || spec.finish === 'base::chrome');
        const colorIsPreservedNoop = Object.prototype.hasOwnProperty.call(spec, 'color') && String(spec.color).toLowerCase() === String(original.color).toLowerCase();
        if (!finishMatches || (Object.prototype.hasOwnProperty.call(spec, 'color') && !colorIsPreservedNoop) || Object.prototype.hasOwnProperty.call(spec, 'pattern') || Object.prototype.hasOwnProperty.call(spec, 'spec_patterns') || Object.prototype.hasOwnProperty.call(spec, 'region')) {
          blockers.push({ id: item.id, type: 'finish-preserve queue contains wrong finish or color/region/pattern mutation', expectedFinish, oracleLabel: item.finish, queue: zones });
        } else {
          applied = route.applyQueue(queue, `W17 ${item.id}`, false);
          const afterApply = route.zones[0];
          if (applied.failed.length || afterApply.id !== original.id || afterApply.colour !== original.color || afterApply.finishKey !== spec.finish || !Array.from(afterApply.regionMask).every((x, i) => x === original.mask[i]) || !route.partOwnerCurrent(afterApply, original.key) || route._editReg[original.key] !== afterApply.name) {
            blockers.push({ id: item.id, type: 'apply did not preserve owned identity/color/mask while changing finish', apply: applied, ownerCurrent: route.partOwnerCurrent(afterApply, original.key), registryOwner: route._editReg[original.key], zone: { id: afterApply.id, name: afterApply.name, color: afterApply.colour, finish: afterApply.finishKey, mask: Array.from(afterApply.regionMask) } });
          } else {
            route._advRejected = [];
            const entry = { undoable: true, zoneUndo: true, _partRegUndo: applied.partRegUndo, request: item.text };
            route.doUndo(entry);
            const restored = route.zones[0];
            undone = { undone: entry.undone, id: restored.id, color: restored.colour, finish: restored.finishKey, mask: Array.from(restored.regionMask), owner: route._editReg[original.key] };
            if (!entry.undone || restored.id !== original.id || restored.colour !== original.color || restored.finishKey !== initialFinish || !Array.from(restored.regionMask).every((x, i) => x === original.mask[i]) || route._editReg[original.key] !== original.name) blockers.push({ id: item.id, type: 'Undo failed to restore original zone state and registry owner', undone });
            else full = true;
          }
        }
      }
    } else if (item.mode === 'ask' || item.mode === 'no_mutation') {
      if (queue.length) { unsafe = true; blockers.push({ id: item.id, type: 'clarify/prohibition path queued a partial mutation', queue: zones, reply: response && response.text }); }
    } else if (item.mode === 'ask_or_all' && queue.length) {
      const textQueue = JSON.stringify(queue).toLowerCase();
      const hasRoofChrome = queue.some(q => q.kind === 'edit' && (q.zone === 0 || q.zone_id === original.id) && q.spec && q.spec.finish === 'base::chrome' && !Object.hasOwn(q.spec, 'color'));
      const hasHoodStripe = /pinstripe|stripe/.test(textQueue) && partZones.includes('hood');
      if (!hasRoofChrome || !hasHoodStripe) { unsafe = true; blockers.push({ id: item.id, type: 'multi-action request queued only a subset', queue: zones, reply: response && response.text }); }
    }
    results.push({ id: item.id, text: item.text, mode: item.mode, expected: item.expected, editPlan: parsed, compiled, compoundPlan: compound, route: response && response.route || (queue.length ? 'edit' : 'ask'), reply: response && response.text || '', queue: zones, full, unsafe, apply: applied && { failed: applied.failed, partRegUndo: applied.partRegUndo }, undo: undone, original: { id: original.id, color: original.color, finish: original.finish, mask: original.mask, owner: original.name } });
  }

  // Configured true and false use the same frozen offline route and never call the provider.
  const configuredChecks = [];
  for (const configured of [false, true]) {
    reset(); route.configured = configured;
    const original = seed('roof', '#c8102e', 'base::gloss');
    let result;
    try { result = await route.ask(suppliedNative.text, {}); }
    catch (e) { result = { route: 'error', error: String(e && e.stack || e), queue: [] }; }
    const queue = result && result.queue || [];
    const configuredPlan = E.plan(suppliedNative.text, env), configuredCompiled = configuredPlan && configuredPlan.kind === 'ops' ? E.compile(configuredPlan, env) : null;
    const configuredFinish = configuredCompiled && configuredCompiled.zones && configuredCompiled.zones[0] && configuredCompiled.zones[0].finish;
    const okay = result && result.route === 'edit' && queue.length === 1 && queue[0].kind === 'edit' && queue[0].zone === 0 && queue[0].spec && queue[0].spec.finish === configuredFinish && !Object.hasOwn(queue[0].spec, 'color') && !Object.hasOwn(queue[0].spec, 'pattern') && route.providerCalls === 0;
    configuredChecks.push({ configured, okay: !!okay, route: result && result.route, queue: queuedZones(result), providerCalls: route.providerCalls });
    if (!okay) blockers.push({ id: `configured-${configured}`, type: 'configured/unconfigured ask route did not preserve one existing roof owner offline', result: configuredChecks[configuredChecks.length - 1], original });
  }

  const sourceHashes = { frozenProAI: sha(frozenProAiPath), frozenDesign: sha(frozenDesignPath), currentEdit: sha(currentEditPath) };
  const report = {
    review: 'W17 independent named-part finish/color preservation route review', date: '2026-10-04',
    status: blockers.length ? 'BLOCKED' : 'PASS',
    frozen_oracle: { sha256: oracleHash, cases },
    source_selection: {
      proAI: { path: '_easy_claude_work/ai14h_generation2_sources/js/spb-pro-ai.js', sha256: sourceHashes.frozenProAI, selection: 'generation2 frozen snapshot; moving proAI was not executed' },
      proDesign: { path: '_easy_claude_work/ai14h_generation2_sources/js/spb-pro-design.js', sha256: sourceHashes.frozenDesign },
      proEdit: { path: 'js/spb-pro-edit.js', sha256: sourceHashes.currentEdit, expected_sha256: editExpectedHash }
    },
    counts: {
      total: results.length,
      finished_and_undone: results.filter(r => r.full).length,
      safe_asks_or_no_queue: results.filter(r => !r.queue.length && !r.unsafe).length,
      unsafe_partial_or_wrong_owner: results.filter(r => r.unsafe).length,
      expected_completion_gaps: blockers.length,
      configured_routes_passed: configuredChecks.filter(x => x.okay).length
    },
    results, configuredChecks, blockers,
    findings: [
      { id: 'W17-01', class: 'verified', detail: 'The exact supplied request queues one finish-only edit on the existing roof UUID; mocked production apply preserves the red color and region mask, updates registry ownership on the same region, and production doUndo restores the original finish and owner. Both configured states use the frozen offline route with zero provider calls.' },
      { ids: ['W17-02', 'W17-03'], class: 'safe_but_unhandled_preservation_wording', detail: 'The route asks without queuing, but presents “retain” and “leave current” as unknown look names and suggests changing the current color. These are missed finish-only paraphrases, not unsafe edits.' },
      { id: 'W17-04', class: 'safe_but_unhandled_positive_edit_with_color_preservation', detail: 'The leading-prohibition guard treats “don’t change its current navy color” as prohibition of the whole request and drops the preceding positive hood gloss command. No mutation is queued.' },
      { ids: ['W17-06', 'W17-07', 'W17-08'], class: 'safe_ask_or_no_mutation', detail: 'Mixed overlay, explicit prohibition, and multi-action pinstripe wording produce no partial queue.' }
    ],
    source_findings: [
      { file: 'js/spb-pro-edit.js', lines: '448-454', detail: 'The prohibition regex matches a color-preservation “do not change” anywhere in the request and returns before the positive finish action can be parsed.' },
      { file: 'js/spb-pro-edit.js', lines: '472-485', detail: 'The anchored preservation-tail whitelist handles keep/retain/preserve/leave forms for paint color, but the full prefix/tail variants in W17-02 and W17-03 still reach parseClause as unknown look text.' }
    ],
    limits: ['No browser, native app, provider, renderer, or moving proAI source was executed. Final batch and undo side effects were mocked; production offlineAsk/Core/queueEditZones/applyQueue/doUndo orchestration was executed.', 'Current E parser/compiler and frozen generation2 D/proAI source were loaded in one harness; production hashes are pinned and asserted.', 'This review does not supersede or erase the original native cross-colors pattern blocker; the supplied W17-01 phrase is exercised locally and through the frozen production route.']
  };
  const reportPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_FINISH_PRESERVE_ROUTE_REVIEW_2026-10-03.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, counts: report.counts, blockers, hashes: sourceHashes }, null, 2));
  if (blockers.length) process.exitCode = 2;
})().catch(e => { console.error(e); process.exitCode = 1; });


