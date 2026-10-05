const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const H = require('../_easy_claude_work/stack_h.js');

const root = path.join(__dirname, '..');
const oraclePath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_W3_PRESERVATION_ORACLE_2026-10-03.json');
const supplementPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_W3_PRESERVATION_ROUTER_SUPPLEMENT_2026-10-03.json');
const frozenHashes = {
  [oraclePath]: '7dd0d4c6e7daaff32cc2aedae57055951e72e8d94875e319beb9063eb994ea76',
  [supplementPath]: '90752583fc83f5ce021facb61270b97865d8efebab5d754b85d35c4e75a54495'
};
for (const [file, hash] of Object.entries(frozenHashes)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'), hash, `frozen oracle changed: ${path.basename(file)}`);
}
const oracle = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));
const supplement = JSON.parse(fs.readFileSync(supplementPath, 'utf8'));
const w = H.load();
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js', 'js/spb-self-help.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
}
const D = w.SpbProDesign;
const E = w.SpbProEdit;
const A = w.SpbProAdvisor;
const SH = w.SpbSelfHelp;
const env = { palette: [
  { hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 },
  { hex: '#f1f1ee', share_pct: 14 }, { hex: '#1347a8', share_pct: 5 }
], layers: [] };
const source = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');

function extractFunction(text, name) {
  const start = text.indexOf(`function ${name}(`);
  assert(start >= 0, `missing ${name} in production router`);
  const brace = text.indexOf('{', start);
  let depth = 0, quote = null, lineComment = false, blockComment = false, escaped = false;
  for (let i = brace; i < text.length; i++) {
    const c = text[i], n = text[i + 1];
    if (lineComment) { if (c === '\n') lineComment = false; continue; }
    if (blockComment) { if (c === '*' && n === '/') { blockComment = false; i++; } continue; }
    if (quote) { if (escaped) { escaped = false; continue; } if (c === '\\') { escaped = true; continue; } if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { lineComment = true; i++; continue; }
    if (c === '/' && n === '*') { blockComment = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return text.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const calls = { edit: [], core: 0, advisor: 0, zones: [] };
const advisorForReview = {
  classify: (text, last) => A.classify(text, last),
  answer: () => null
};
const ctx = {
  window: Object.assign(w, { SpbProAdvisor: advisorForReview, SpbSelfHelp: SH }),
  console, D, E, AI: { cached: () => ({ configured: false }) },
  LOOK_CURATED: D.LOOK_CURATED, AT: null,
  _offlineLast: null, _advLast: null, _reqText: '', _specOnlyReq: false, _forcedIdeaCols: null,
  _beforeImg: null, _busy: false, _progress: '', _skipParts: false, _absent: {},
  START_OVER_RE: /^\s*(?:start over|new design)\b/i,
  SH_FIRST_RE: /\b(?:how|where|why|what|which|can|could|help|explain|stuck|confused)\b/i,
  CHECK_AGAIN_RE: /^\s*check (it |that |everything |my setup |the check )?again\s*$/i,
  SMALL_HELLO_RE: /$a/, SMALL_THANKS_RE: /$a/, CANT_RE: /$a/, NUM_FIX_RE: /$a/, NOT_ELEM_RE: /$a/,
  selfHelpClaim(text) { return SH.classify(text) ? SH.handle(text) : null; },
  selfHelpResult(result) { return { route: 'selfhelp', text: result.text || '', queue: [] }; },
  supportClass() { return null; }, elemOwnsText() { return false; },
  advisorIntent(text) { calls.advisor++; return A.classify(text, null); },
  editPlan(text) { const plan = E.plan(text, env); this._lastEditPlanKind = plan && plan.kind; return plan; }, editYieldsToStack() { return false; },
  captureOriginal() {}, intentSpecOnly() { return false; },
  offlineAskCore() { calls.core++; return Promise.resolve({ route: 'core-stub', queue: [] }); },
  editReply(text, chips, extra) { return Object.assign({ route: 'edit', kind: this._lastEditPlanKind === 'ask' ? 'ask' : 'result', text, queue: [] }, extra || {}); },
  render() {}, warm() { return Promise.resolve(); }, resolveLook() { return Promise.resolve(null); },
  prepEnv() { return Promise.resolve(env); }, editEnv() { return env; }, elementKinds() { return []; }, exclTargets() { return []; },
  CAR: null, offlineCannot() { return null; }, layerVisRequest() { return null; }, offlineHowto() { return null; },
  makeTools(queue) { return [
    { name: 'add_zone', handler(spec) { const op = { tool: 'add_zone', args: JSON.parse(JSON.stringify(spec)) }; queue.push(op); return {}; } },
    { name: 'edit_zone', handler(spec) { const op = { tool: 'edit_zone', args: JSON.parse(JSON.stringify(spec)) }; queue.push(op); return {}; } },
    { name: 'apply_scheme', handler(spec) { const op = { tool: 'apply_scheme', args: JSON.parse(JSON.stringify(spec)) }; queue.push(op); return Promise.resolve({}); } }
  ]; },
  // Queue capture only: observe the exact compiled zone specs without touching app state.
  queueEditZones(cm, addFn) {
    const lines = [];
    (cm.zones || []).forEach(z => { addFn(JSON.parse(JSON.stringify(z))); lines.push(z.name || 'zone'); calls.zones.push(z); });
    return { errs: [], lines, labels: lines.map(x => x.replace(/ .*/, '')), allSpec: false,
      anyColourTarget: (cm.zones || []).some(z => z.region && z.region.colors), merged: 0 };
  },
  markPartFollowupQueue() {}, friendlyZoneError(x) { return x; }, editOverlapNote() { return ''; },
  editOverlapKinds() { return []; }, exclNotes() { return []; }, logMiss() {},
  offlineFirst() { return true; },
  offlineScopeReply() { return { route: 'scope-reply', text: 'Nothing was changed; please clarify.', queue: [] }; }
};
vm.createContext(ctx);
for (const name of ['lookEntry', 'resolveLook', 'offlineMaterialPlan', 'offlineEditAsk', 'offlineLookAsk', 'offlinePartAsk', 'offlineAsk', 'offlineAskCore', 'offlineCanHandle', 'ask']) {
  vm.runInContext(extractFunction(source, name), ctx, { filename: `js/spb-pro-ai.js#${name}` });
}
const offlineAsk = vm.runInContext('offlineAsk', ctx);
const actualOfflineAskCore = vm.runInContext('offlineAskCore', ctx);
ctx.offlineAskCore = function (text, options) { calls.core++; return actualOfflineAskCore(text, options); };
const offlineCanHandle = vm.runInContext('offlineCanHandle', ctx);
const selfHelpClaim = text => SH.classify(text) ? SH.handle(text) : null;
const ask = vm.runInContext('ask', ctx);

function scopeOf(region) {
  if (!region) return 'none';
  if (region.everything || region.paintable) return 'body';
  if (region.part) return `part:${[].concat(region.part).join('+')}`;
  if (region.colors) return `colors:${region.colors.map(x => String(x).toLowerCase()).join('+')}`;
  return JSON.stringify(region);
}
function queuedScopes(result) {
  return ((result && result.queue) || []).filter(x => x.tool === 'add_zone').map(x => scopeOf(x.args && x.args.region));
}
function queuedMutationCount(result) { return Array.isArray(result && result.queue) ? result.queue.length : 0; }
const failures = [];

(async () => {
  // Frozen whole-body exception asks must win before designer compound, advisor, and legacy fallback ownership.
  for (const item of oracle.cases.filter(x => x.expected === 'truthful-ask')) {
    calls.edit.length = 0; calls.core = 0; calls.advisor = 0; calls.zones.length = 0;
    const e = E.plan(item.ask, env);
    const answer = await ask(item.ask, {});
    if (!e || e.kind !== 'ask' || !Array.isArray(e.protected_parts)) failures.push(`${item.id}: E did not return an explicit protected_parts ask`);
    if (!answer || answer.kind !== 'ask' || answer.route !== 'edit') failures.push(`${item.id}: full ask route did not return the clarification (route=${answer && answer.route}, kind=${answer && answer.kind})`);
    if (queuedMutationCount(answer)) failures.push(`${item.id}: queued ${queuedMutationCount(answer)} mutation(s), scopes=${queuedScopes(answer).join(', ') || 'non-zone tool'}`);
    if (calls.core || calls.advisor) failures.push(`${item.id}: ask fell through before clarification (core=${calls.core}, advisor=${calls.advisor})`);
    for (const part of item.expected_parts || []) if (!String(answer && answer.text || '').toLowerCase().includes(part)) failures.push(`${item.id}: clarification copy omitted ${part}`);
  }

  // Compound plans that contain both a protected area and a changed area must not bypass E's explicit ask.
  for (const item of supplement.cases.filter(x => x.expected === 'truthful-ask-before-compound-owner')) {
    calls.edit.length = 0; calls.core = 0; calls.advisor = 0; calls.zones.length = 0;
    const cp = D.compoundPlan(item.ask);
    const result = await ask(item.ask, {});
    const cpRegions = cp && cp.zones ? cp.zones.map(z => scopeOf(z.region)) : [];
    if (cpRegions.length && !cpRegions.some(s => item.preserved.some(p => s === `part:${p}`))) failures.push(`${item.id}: existing compound plan no longer contains the protected part (${cpRegions.join('|')})`);
    if (!result || result.kind !== 'ask' || result.route !== 'edit') failures.push(`${item.id}: E preservation ask lost to earlier route (route=${result && result.route}, kind=${result && result.kind})`);
    if (queuedMutationCount(result) || calls.zones.length) failures.push(`${item.id}: protected-panel request queued mutations (${queuedMutationCount(result)} queued; scopes=${queuedScopes(result).join(', ') || 'none'})`);
    if (calls.core || calls.advisor) failures.push(`${item.id}: protected-panel ask reached core/advisor (core=${calls.core}, advisor=${calls.advisor})`);
  }

  // Explicit active body-plus-panel exceptions must retain both assignments; the exception is not a request to repaint only that panel.
  for (const id of ['W3-08', 'W3-09']) {
    const item = oracle.cases.find(x => x.id === id);
    calls.zones.length = 0;
    const result = await ask(item.ask, {});
    const scopes = queuedScopes(result);
    const allowed = item.regions.map(x => x === 'body' ? 'body' : `part:${x}`);
    const missing = allowed.filter(x => !scopes.includes(x));
    const bad = scopes.filter(x => !allowed.includes(x));
    if (missing.length || bad.length) failures.push(`${id}: explicit active body-plus-panel request did not queue both allowed scopes (missing=${missing.join('|') || 'none'}, actual=${scopes.join('|') || 'none'}, out-of-scope=${bad.join('|') || 'none'})`);
  }

  // A local roof-only edit may ask, or may queue a roof-only zone; a color-wide zone is forbidden.
  {
    const item = supplement.cases.find(x => x.id === 'W3-R06');
    calls.edit.length = 0; calls.core = 0; calls.advisor = 0; calls.zones.length = 0;
    const result = await ask(item.ask, {});
    const scopes = queuedScopes(result);
    const bad = scopes.filter(s => !item.allowed_regions.map(x => `part:${x}`).includes(s));
    if (bad.length) failures.push(`${item.id}: roof-only correction queued out-of-scope regions ${bad.join('|')}`);
    if (result && result.kind === 'ask' && scopes.length) failures.push(`${item.id}: ask reply also carried queued mutations`);
  }

  // Local clarification language must name the local edit and preserved panel honestly.
  {
    const item = supplement.cases.find(x => x.id === 'W3-R05');
    const result = await offlineAsk(item.ask, {});
    const text = String(result && result.text || '').toLowerCase();
    if (!result || result.kind !== 'ask' || queuedMutationCount(result)) failures.push(`${item.id}: expected a no-queue local clarification`);
    if (text.includes(item.copy_must_not_claim)) failures.push(`${item.id}: copy falsely describes a whole-paint change for a roof-only request`);
    if (!text.includes('roof') || !text.includes('hood')) failures.push(`${item.id}: local clarification must name both requested roof and protected hood`);
  }

  // A roof-only request with a named hood preservation clause must not recolor the hood.
  {
    const item = supplement.cases.find(x => x.id === 'W3-R07');
    const result = await ask(item.ask, {});
    const scopes = queuedScopes(result);
    if (queuedMutationCount(result) && scopes.some(s => s !== 'part:roof')) failures.push(`${item.id}: queued mutation outside the requested roof (${scopes.join('|') || 'non-zone tool'})`);
    if (result && result.kind === 'ask' && result.route !== 'edit') failures.push(`${item.id}: safe clarification came from an unexpected route (${result.route})`);
  }

  // False-positive guards: keep-colors, quoted recipe labels, how-to questions, and color-only part changes.
  const guardProbes = [
    ['keep-colors', 'Keep the current body colors; make only the roof glossy.', ['part:roof']],
    ['recipe-keep', "Use a finish named 'Keep It Real' on the roof only.", ['part:roof']],
    ['recipe-preserve', "Use a finish called 'Preserve the Blue' on the hood only.", ['part:hood']],
    ['color-only', 'Change the hood color to blue.', ['part:hood']]
  ];
  for (const [label, text, allowed] of guardProbes) {
    calls.core = 0; calls.advisor = 0; calls.zones.length = 0;
    const e = E.plan(text, env);
    const result = await ask(text, {});
    const scopes = queuedScopes(result);
    if (e && e.kind === 'ask' && e.protected_parts) failures.push(`${label}: phrase was falsely treated as named-panel preservation`);
    if (scopes.some(s => !allowed.includes(s))) failures.push(`${label}: out-of-scope queued regions ${scopes.join('|')}`);
  }
  const howto = 'How can I keep the original hood color while repainting the body?';
  calls.core = 0; calls.advisor = 0; calls.zones.length = 0;
  const howtoResult = await ask(howto, {});
  if (queuedMutationCount(howtoResult)) failures.push('how-to preservation question queued mutations');

  // The initial self-help and advisor owners may handle questions/recommendations, never an edit plan here.
  for (const item of supplement.cases.filter(x => x.expected.startsWith('truthful-ask'))) {
    if (selfHelpClaim(item.ask)) failures.push(`${item.id}: self-help claimed an imperative preservation order before the guard`);
    const ai = A.classify(item.ask, null);
    if (ai && ai.kind === 'pick') failures.push(`${item.id}: advisor pick ownership could apply a prior stack before the guard`);
    if (!offlineCanHandle(item.ask)) failures.push(`${item.id}: offlineCanHandle would let a configured-provider route bypass the local preservation ask (E=${JSON.stringify(E.plan(item.ask, env))}, advisor=${JSON.stringify(A.classify(item.ask, null))})`);
  }

  assert.deepEqual(failures, [], `preservation-router review findings:\n${failures.join('\n')}`);
  console.log('PASS ai_preservation_review_contract.cjs (7 frozen preservation asks, 4 compound bypasses, 2 active compositions, 3 scoped/local edits, 5 false-positive/query guards; no provider calls)');
})().catch(err => { console.error(err); process.exitCode = 1; });
