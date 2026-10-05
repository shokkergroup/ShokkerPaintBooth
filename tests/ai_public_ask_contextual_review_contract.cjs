'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const base = '_easy_claude_work/ai14h_generation3_candidate/integration18/js/';
const oraclePath = '_easy_claude_work/ai14h_w116_review/fresh-oracle.json';
const files = {
  pro: base + 'spb-pro-ai.js', selfhelp: base + 'spb-self-help.js',
  receipt: base + 'spb-ai-receipt-explainer.js', intent: base + 'spb-ai-instruction-intent-guard.js',
  oracle: oraclePath
};
const src = Object.fromEntries(Object.entries(files).map(([k, p]) => [k, fs.readFileSync(path.join(root, p), 'utf8')]));
const sha = s => crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
const proSha = sha(src.pro);
assert.equal(proSha, 'F88C962C94887D63C93AB775FE0B5AE3418A97F0AD0CC35A4C95A739719BEF4B', 'integration18 controller pin');
assert.equal(sha(src.oracle), '41FFE664AB09C9B9B6250C96A910AB6B6E91B78033C7F29CB3D07442C2EA08A0', 'frozen W116 oracle pin');

function extract(source, name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `${name} exists`);
  const brace = source.indexOf('{', start); let depth = 0, quote = null, line = false, block = false, esc = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw Error(`unterminated ${name}`);
}

function fixture() {
  const bodyClasses = { contains: () => false };
  const w = {
    console, Promise, Date, Math, JSON, Object, Array, String, Number, RegExp, Error,
    document: { body: { classList: bodyClasses }, getElementById: () => null },
    zones: [], _psdLayers: [], paintImageData: null, selectedZoneIndex: -1,
    zoneSourceLayerIds: () => [], _spbLayerRev: 0, _spbOperationRevision: 1,
    SpbProCar: { roles: () => [], map: () => null, missing: () => [] },
    SpbAI: { cached: () => ({ configured: false }) },
    SpbAiLease: { internal: () => true }
  };
  w.window = w; vm.createContext(w);
  vm.runInContext(src.selfhelp, w, { filename: files.selfhelp });
  vm.runInContext(src.receipt, w, { filename: files.receipt });
  vm.runInContext(src.intent, w, { filename: files.intent });
  Object.assign(w, {
    _log: [], _busy: false, _ctl: null, _envMemo: null, _panel: null,
    operationCurrent: t => !!t && t.ok === true,
    operationTicket: v => v && v._spbOperation || null,
    operationManager: () => ({ sameDocument: t => !!t && t.document && t.document.sourceGeneration === 7, ready() {}, owns: () => true }),
    operationRevision: () => 1, operationRelease() {}, operationBind: v => v,
    operationStart: () => ({ ok: true, document: { sourceGeneration: 7 }, revision: 1, collection: 1 }),
    operationCanceled: () => ({ cancelled: true, stale: true, queue: [] }),
    offlineInstructionPreflight: null,
    offlineAsk: () => Promise.resolve({ offline: true, queue: [], text: 'actual offline route sentinel' }),
    askForTicket: null
  });
  for (const name of ['normalizeOfflineInstruction', 'selfHelpResult', 'unexecutedSuggestionReply', 'contextualHelpReply', 'offlineInstructionPreflight', 'ask']) {
    vm.runInContext(extract(src.pro, name), w, { filename: files.pro });
  }
  // This is the exact exported ask function body from the pinned controller; the
  // surrounding full IIFE is not booted because it requires the desktop DOM.
  w.spbProAI = { ask: w.ask };
  const actionCalls = [];
  w.askForTicket = (text, options) => {
    actionCalls.push({ text, options });
    return Promise.resolve({ offline: true, text: 'controlled offline action handoff', queue: [] });
  };
  return { w, actionCalls };
}

(async () => {
  const oracle = JSON.parse(src.oracle), rows = [], issues = [];
  for (const c of oracle.cases) {
    const { w, actionCalls } = fixture();
    const result = await w.spbProAI.ask(c.input, { offline: true });
    const text = String(result && result.text || '');
    const isHelp = c.kind === 'help';
    rows.push({ id: c.id, kind: c.kind, howto: !!(result && result.howto), queue: (result && result.queue || []).length, delegated: actionCalls.length, model: result && result.model, text: text.slice(0, 420) });
    if (isHelp) {
      if (!result || !result.howto || actionCalls.length || (result.queue || []).length) issues.push(`${c.id}: public ask did not return local read-only guidance`);
      if (result && result.usage && result.usage.cost !== 0) issues.push(`${c.id}: nonzero usage on source-less offline help`);
      if (c.id === 'source-less-getting-started' && !/paint|source|load|file/i.test(text)) issues.push(`${c.id}: setup answer lacks source/load guidance`);
      if (c.id === 'saved-pixels-no-mark' && !/pixel|raster/i.test(text)) issues.push(`${c.id}: saved-pixel answer omits pixel payload`);
      if (c.id === 'undo-location-no-mark' && (!/undo/i.test(text) || /verified apply receipt/i.test(text))) issues.push(`${c.id}: Undo location was diverted to receipt status`);
    } else {
      if (result && result.howto) issues.push(`${c.id}: actionable imperative diverted to help`);
      if (actionCalls.length !== 1 || actionCalls[0].text !== c.input) issues.push(`${c.id}: public ask did not delegate once to offline action planner`);
      if ((result && result.queue || []).length) issues.push(`${c.id}: controlled action adapter unexpectedly returned queue`);
    }
  }
  const report = {
    work_item: 'W116 actual public spbProAI.ask contextual-help route acceptance',
    status: issues.length ? 'REVIEW_GAPS' : 'PASS_PRIVATE_PIN',
    source: { path: files.pro, sha256: proSha, exportPresence: /window\.spbProAI\s*=\s*\{[\s\S]*?\bask:\s*ask\s*[,}]/.test(src.pro) },
    oracle: { path: oraclePath, sha256: sha(src.oracle), frozenBeforeReplay: true, cases: oracle.cases.length },
    rows, issues,
    limits: ['Executed the exact extracted ask(), normalizeOfflineInstruction(), offlineInstructionPreflight(), and contextualHelpReply() bodies from the pinned controller. The desktop IIFE/DOM was not booted; for imperative controls askForTicket was a controlled offline-only handoff sentinel, so downstream planners/application were not claimed. No provider, native app, browser, save, or paint apply call occurred.'],
    counts: { cases: rows.length, guidanceCases: oracle.cases.filter(x => x.kind === 'help').length, actionControls: oracle.cases.filter(x => x.kind === 'action').length, failures: issues.length, providerCalls: 0, nativeCalls: 0, applyCalls: 0 }
  };
  assert.equal(report.source.exportPresence, true, 'pinned source exports this ask() function publicly');
  const out = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_PUBLIC_ASK_W116_REVIEW_2026-10-04.json');
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  if (issues.length) process.exitCode = 1;
})().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
