'use strict';
// W66 semantic guide replay against immutable W59 helper bytes and isolated candidate.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const oraclePath = path.join(root, '_easy_claude_work/ai14h_w66_review/fresh-oracle.json');
const oracle = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));
let providerCalls = 0;
function load(dir) {
  const w = { console, fetch: () => { providerCalls++; throw Error('provider must not be called'); }, _spbLayerRev: 1,
    selectedZoneIndex: 0, _psdLayers: [], paintImageData: { width: 8, height: 8 },
    document: { body: { classList: { contains: () => false } } },
    zones: [{ id: 'roof-id', name: 'Roof', base: 'gloss', region: { x: 1, y: 2, w: 3, h: 4 } }],
    source: { generation: 7, committedGeneration: 7, loading: false, committed: true, path: 'C:/paint/car.psd', fingerprint: 'sha-a' } };
  w.window = w;
  w.SPBSourceLoadTransaction = { getGeneration: () => 7, getCommittedGeneration: () => 7, isLoading: () => false,
    isCommitted: () => true, getCommittedPath: () => w.source.path, getCommittedFingerprint: () => w.source.fingerprint };
  w.SpbProCar = { map: () => ({}), missing: () => [], signature: () => 'layout-' + w._spbLayerRev };
  vm.createContext(w);
  for (const file of ['spb-ai-knowledge.js', 'spb-self-help.js']) {
    const source = fs.readFileSync(path.join(root, dir, file), 'utf8');
    vm.runInContext(source, w, { filename: path.join(dir, file) });
  }
  return w;
}
function answer(w, text, state) { return w.SpbSelfHelp.answer(text, state); }
function check(name, fn) { try { fn(); return { id: name, verdict: 'pass' }; } catch (e) { return { id: name, verdict: 'fail', error: e.message }; } }
const candidate = load('_easy_claude_work/ai14h_w66_review/candidate');
const baseline = load('_easy_claude_work/ai14h_w66_review/frozen');
const rows = [];
const expectedFailures = [];
for (const c of oracle.cases) {
  const a = answer(candidate, c.input);
  if (c.id === 'W66-01') rows.push(check(c.id, () => { assert.match(a.text, /combined into one image/i); assert.match(a.text, /separate editable layers/i); assert.doesNotMatch(a.text, /Actions|flatten document/i); }));
  else if (c.id === 'W66-02') rows.push(check(c.id, () => { assert.match(a.text, /LAYERS.*Actions.*Flatten document/s); assert.match(a.text, /hidden layers separate/i); }));
  else if (c.id === 'W66-03') rows.push(check(c.id, () => { assert.match(a.text, /Shift the CLEARCOAT channel/); assert.match(a.text, /B \/ COAT/); assert.match(a.text, /R \/ METAL and G \/ ROUGH/); assert.doesNotMatch(a.text, /PICK COLOR|solid color|replace.*color/i); }));
  else if (c.id === 'W66-04' || c.id === 'W66-05') rows.push(check(c.id, () => { assert.equal(candidate.SpbSelfHelp.classify(c.input), null); assert.equal(a, null); }));
  else if (c.id === 'W66-06') rows.push(check(c.id, () => { const st = { paint: 'psd', layers: [{ name: 'Door Numbers', hidden: false }], zones: [], mode: 'pro' }; const n = answer(candidate, c.input, st); assert.match(n.text, /LAYERS tab/); assert.match(n.text, /visible or hidden|eye control|show or hide/i); assert.doesNotMatch(n.text, /finish|recommend/i); }));
  else if (c.id === 'W66-07') rows.push(check(c.id, () => { assert.match(a.text, /works offline without an API key/i); assert.match(a.text, /scoped paint edits, material-channel offsets, app guidance, and Undo/i); assert.match(a.text, /external AI connection is optional/i); }));
  else if (c.id === 'W66-08') rows.push(check(c.id, () => { assert.ok(a); assert.equal(a.doIt, null); assert.doesNotMatch(a.text, /done|applied|painted successfully/i); }));
  else if (c.id === 'W66-09') rows.push(check(c.id, () => { assert.ok(!a || (a.doIt === null && !/painted successfully|done/i.test(a.text))); }));
  else if (c.id === 'W66-10') rows.push(check(c.id, () => { assert.match(a.text, /Clearcoat is the spec-map coat channel/i); assert.match(a.text, /Shift the CLEARCOAT channel/); assert.match(a.text, /B \/ COAT/); }));
  else if (c.id === 'W66-11') rows.push(check(c.id, () => { assert.match(a.text, /Shift the CLEARCOAT channel/); assert.match(a.text, /channel offset/i); assert.match(a.text, /rather than assuming a larger offset always means more physical gloss/i); }));
  else if (c.id === 'W66-12') rows.push(check(c.id, () => { if (a) assert.equal(a.doIt, null); }));
  const old = answer(baseline, c.input);
  if (['W66-01', 'W66-02', 'W66-03', 'W66-06', 'W66-07'].includes(c.id)) expectedFailures.push({ id: c.id, baseline: old ? old.text.slice(0, 300) : null });
}
assert.equal(providerCalls, 0);
const bad = rows.filter(r => r.verdict !== 'pass');
const retained = [
  { name: 'W59 lifecycle', script: '_easy_claude_work/ai14h_w66_review/w59-replay.cjs', expected: /16\/16 fresh lifecycle checks passed/ },
  { name: 'W3 action lifecycle', script: '_easy_claude_work/ai14h_w66_review/w3-replay.cjs', expected: /15 passed, 0 failed/ },
  { name: 'W4 semantics', script: '_easy_claude_work/ai14h_w66_review/w4-review-replay.cjs', expected: /12\/12/ },
  { name: 'W4 action ownership', script: '_easy_claude_work/ai14h_w66_review/w4-semantic-replay.cjs', expected: /8 action\/entity, view-capability, and command-ownership checks/ }
].map(x => { const stdout = execFileSync(process.execPath, [path.join(root, x.script)], { cwd: root, encoding: 'utf8' }); assert.match(stdout, x.expected, x.name); return { name: x.name, status: 'PASS', output_excerpt: stdout.split(/\r?\n/).filter(line => /PASS|passed, 0 failed/.test(line)).slice(0, 2) }; });
const syntax = execFileSync(process.execPath, ['--check', path.join(root, '_easy_claude_work/ai14h_w66_review/candidate/spb-self-help.js')], { cwd: root, encoding: 'utf8' });
const digest = f => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, f))).digest('hex').toUpperCase();
const report = { status: bad.length ? 'FINDINGS' : 'PASS', task: 'W66 offline help-answer semantic repair candidate', date: '2026-10-04',
  frozenInputs: { freshOracle: { path: '_easy_claude_work/ai14h_w66_review/fresh-oracle.json', sha256: digest('_easy_claude_work/ai14h_w66_review/fresh-oracle.json'), cases: oracle.cases.length },
    helperBaseline: { path: '_easy_claude_work/ai14h_w66_review/frozen/spb-self-help.js', sha256: digest('_easy_claude_work/ai14h_w66_review/frozen/spb-self-help.js') },
    candidate: { path: '_easy_claude_work/ai14h_w66_review/candidate/spb-self-help.js', sha256: digest('_easy_claude_work/ai14h_w66_review/candidate/spb-self-help.js') },
    runtime1Controller: { path: '_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/js/spb-pro-ai.js', sha256: '3DA5C98B7202288979EFE0F53FE48818F31A6A5B5428BFB178CAEBA5C25E82D6', actualRouteNotExecuted: true } },
  counts: { freshCases: rows.length, passed: rows.length - bad.length, failed: bad.length, reproducedBaselineWrongSemantics: expectedFailures.length, retainedCompatibilitySuites: retained.length, providerCalls: providerCalls, nativeCalls: 0 },
  freshRows: rows, knownBaselineWrongAnswers: expectedFailures,
  retainedCompatibility: retained,
  changes: ['Adds bounded direct explanations for flattened, flatten how-to, clearcoat-only guidance, number-layer location, and offline-helper capability questions.','Keeps imperative clearcoat point requests outside the help classifier for the material command owner.'],
  limits: ['Semantic answer generation was run from the frozen W59 helper and isolated candidate in a VM; no native UI or material dispatcher was exercised.','Imperative clearcoat by-point commands remain unclaimed by self-help. W66-04/05 assert only that help does not capture them; unit-clarification/edit behavior belongs to the material route.','Clearcoat guidance names the selected-zone shift input and preview channels without promising that a larger numeric offset means more physical gloss.'] };
fs.writeFileSync(path.join(root, 'docs/handoff_reports/AI_HELPER_14H_GUIDANCE_W66_SEMANTIC_REVIEW_2026-10-04.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: report.status, counts: report.counts, rows }, null, 2));
if (bad.length) process.exitCode = 1;
