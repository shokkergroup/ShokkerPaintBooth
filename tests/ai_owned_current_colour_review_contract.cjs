// W22 frozen owned-current-colour review. Uses actual E.plan/E.compile with
// source-paint palette and the zoneColours shape returned by pro-ai.js.
// It does not sample a native preview or mutate a live zone.
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('../_easy_claude_work/stack_h.js');

const ROOT = path.resolve(__dirname, '..');
const cases = [
  { id: 'OC01', ask: 'Change the blue on the roof to pale red.', expected: 'resolve-blue-against-owned-roof-current-color; update same zone color' },
  { id: 'OC02', ask: 'Change the blue on the roof to dark blue.', expected: 'resolve-blue-against-owned-roof-current-color; preserve finish and update same zone color' },
  { id: 'OC03', ask: 'Change the red on the roof to pale red.', expected: 'resolve-red-against-owned-roof-current-color; update same zone color' },
  { id: 'OC04', ask: 'Change the current roof color from blue to pale red.', expected: 'explicit-current-color wording resolves against owned zone, not source palette' },
  { id: 'OC05', ask: 'Make the roof a lighter version of its current blue.', expected: 'preserve ownership and finish; use supported relative-lightening semantics or clarify' },
  { id: 'OC06', ask: 'Make only the roof blue.', expected: 'separate native-confirmed base case; same owned roof zone' },
  { id: 'OC07', ask: 'Make only the roof chrome.', expected: 'separate native-confirmed finish-only case; preserve current blue' },
  { id: 'OC08', ask: 'Change the original cyan source layer, not the blue roof repaint.', expected: 'do not mutate owned blue roof as if cyan were current; clarify or target source layer' },
  { id: 'OC09', ask: 'Change the blue on the roof and the cyan on the side to pale red.', expected: 'mixed current/source colors and scopes must not be conflated; clarify or preserve distinct targets' },
  { id: 'OC10', ask: 'Change any blue on the car to pale red.', expected: 'no exact owned-part scope; no automatic roof-zone mutation' }
];
const frozenCasesSha256 = '518d0159b6c585959570bf698755edb83591d78719f12b2d277cafe1d10af78d';
assert.strictEqual(cases.length, 10);
assert.strictEqual(crypto.createHash('sha256').update(JSON.stringify(cases)).digest('hex'), frozenCasesSha256,
  'W22 frozen prompts changed after source inspection');

const w = H.load();
for (const rel of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, rel), 'utf8'), w, { filename: rel });
}
const E = w.SpbProEdit;
assert(E && typeof E.plan === 'function' && typeof E.compile === 'function', 'actual edit planner/compiler failed to load');
const sourceEnv = {
  palette: [
    { hex: '#111111', share_pct: 42 }, { hex: '#00b8d4', share_pct: 27 },
    { hex: '#eeeeee', share_pct: 11 }, { hex: '#e7c547', share_pct: 6 },
    { hex: '#42934a', share_pct: 2 }
  ],
  layers: [], zoneColours: []
};
const owner = { hex: '#1450b4', zone: 'Blue roof', zone_id: 'roof-uuid', index: 2, share_pct: 18, layers: [] };
const ownedEnv = Object.assign({}, sourceEnv, { zoneColours: [owner] });
function observe(ask, env) {
  const plan = E.plan(ask, env);
  const compiled = plan && plan.kind === 'ops' ? E.compile(plan, env) : null;
  return {
    planKind: plan && plan.kind,
    planAsk: plan && plan.text,
    compileAsk: compiled && compiled.ask && compiled.ask.text,
    missing: compiled && (compiled.missing || []).map(m => m.why),
    zones: compiled && (compiled.zones || []).map(z => ({
      name: z.name, color: z.color, finish: z.finish, region: z.region,
      zoneEdit: z._meta && z._meta.zoneEdit,
      finishExplicit: z._meta && z._meta.finishExplicit
    }))
  };
}
const results = cases.map(c => ({
  id: c.id, ask: c.ask, expected: c.expected,
  sourceOnly: observe(c.ask, sourceEnv),
  ownedRoof: observe(c.ask, ownedEnv)
}));

for (const id of ['OC01', 'OC02']) {
  const row = results.find(r => r.id === id);
  assert(row.sourceOnly.compileAsk && /do not see any blue/i.test(row.sourceOnly.compileAsk), `${id}: source-only palette should not invent current blue`);
  assert.strictEqual(row.sourceOnly.zones.length, 0, `${id}: source-only parse must not queue a mutation`);
  assert.strictEqual(row.ownedRoof.compileAsk, null, `${id}: current owned-blue zone should resolve`);
  assert.strictEqual(row.ownedRoof.zones.length, 1, `${id}: expected exactly one existing-owner edit`);
  assert.strictEqual(row.ownedRoof.zones[0].zoneEdit.zone_id, 'roof-uuid', `${id}: must edit the existing owner`);
  assert.strictEqual(row.ownedRoof.zones[0].region, undefined, `${id}: update must preserve existing region/mask`);
  assert.strictEqual(row.ownedRoof.zones[0].finish, undefined, `${id}: color-only change must preserve existing finish`);
}
assert.strictEqual(results.find(r => r.id === 'OC01').ownedRoof.zones[0].color, '#e88797', 'pale-red target should use the planner-resolved color');
assert.strictEqual(results.find(r => r.id === 'OC02').ownedRoof.zones[0].color, '#0b2350', 'dark-blue target should use the planner-resolved color');
assert.strictEqual(results.find(r => r.id === 'OC06').ownedRoof.zones[0].region.part, 'roof', 'native-confirmed base case remains a named-part addition plan');
assert.strictEqual(results.find(r => r.id === 'OC07').ownedRoof.zones[0].color, 'source', 'native-confirmed finish-only case preserves base paint');

const proAiSource = fs.readFileSync(path.join(ROOT, 'js/spb-pro-ai.js'), 'utf8');
function sliceFunction(source, startText, endText, label) {
  const start = source.indexOf(startText), end = source.indexOf(endText, start);
  assert(start >= 0 && end > start, `could not extract ${label}`);
  return source.slice(start, end);
}
const applyQueueSource = sliceFunction(proAiSource, '    function applyQueue(queue, label, noUndo, elementIdentity) {', '\n    function partRegHas', 'applyQueue');
const editEnvSource = sliceFunction(proAiSource, '    function editEnv() {', '\n    // COPILOT-FIX 2026-10-04', 'editEnv');
const zoneColoursSource = sliceFunction(proAiSource, '    function zoneColours() {', '\n    // how much of each flattened-paint colour', 'zoneColours');
const hashes = {};
for (const rel of ['js/spb-pro-ai.js', 'js/spb-pro-edit.js', 'js/spb-pro-design.js', 'js/spb-pro-zone-kit.js']) {
  hashes[rel] = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, rel))).digest('hex');
}
const report = {
  title: 'W22 owned current-color follow-up review',
  generated_at: new Date().toISOString(),
  mode: 'read-only parser/compiler and source audit; no native paint sampling, provider, browser, or queue application',
  frozen_cases_sha256: frozenCasesSha256,
  cases_count: cases.length,
  source_hashes: hashes,
  native_confirmed_parent_evidence: [
    'Make only the roof blue: one owned roof zone updated to #1450b4.',
    'Make only the roof chrome: preserved the blue base on the roof.'
  ],
  production_source_slices: {
    editEnv_sha256: crypto.createHash('sha256').update(editEnvSource).digest('hex'),
    zoneColours_sha256: crypto.createHash('sha256').update(zoneColoursSource).digest('hex'),
    applyQueue_sha256: crypto.createHash('sha256').update(applyQueueSource).digest('hex'),
    editEnv_memo_ms: 2500,
    applyQueue_invalidates_editEnv_memo: /_envMemo\s*=\s*null/.test(applyQueueSource),
    details: 'editEnv memoizes source palette and zoneColours for 2.5 seconds. applyQueue does not invalidate that memo after successful zone mutation. An immediate cross-route edit can therefore observe the pre-edit source palette with no owned-blue row; this is a code-supported race hypothesis, not native runtime proof.'
  },
  actual_edit_module_observations: {
    source_only_OC01_OC02: 'E.plan/E.compile ask which source color is intended and queue no edit because blue is absent from the supplied source palette.',
    owned_zone_OC01_OC02: 'With the actual production zoneColours record shape, E.compile emits one zoneEdit for roof-uuid, changes the requested color, omits finish and region so the existing finish and mask remain owned by that zone.',
    current_color_phrases: 'OC04/OC05 do not parse reliably: the planner treats current/version as unsupported looks and asks; no mutation is compiled.',
    broader_scope: 'OC08–OC10 surfaced source-layer and ambiguous-scope limitations; per-case parser/compiler outcomes are recorded below and are not accepted behavior.'
  },
  lowest_risk_candidate: 'Invalidate the short editEnv memo after successful queue application that can change zones, then rebuild the E environment before compiling the next user turn. A broader current-color resolver would need exact owner, exact named-part, unique helper-owned zone, and user-spoken source/current disambiguation; do not infer source cyan is roof paint. Validate on native preview with the same exact prompts before production integration.',
  limits: [
    'The current-zone record is synthetic but uses the exact compact fields produced by pro-ai.js zoneColours(); it is not sampled from the reported native zone.',
    'No change was made to production files. This review does not verify the native generation-2 prompt routing, visible render, Undo, or zone mask bytes.',
    'OC01/OC02 demonstrate existing compiler support conditional on current zoneColours being fresh; they do not prove the stale memo caused the reported native miss.'
  ],
  cases: results
};
const out = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_OWNED_CURRENT_COLOUR_REVIEW_2026-10-03.json');
fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
console.log(`W22 review recorded ${cases.length} frozen prompts; OC01/OC02 current-zone contract passed; report=${path.relative(ROOT, out)}`);
