'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = process.cwd();
const oraclePath = '_easy_claude_work/ai14h_w120_part_memory_source_identity/fresh-oracle.json';
const oracleText = fs.readFileSync(oraclePath, 'utf8').replace(/^\uFEFF/, '');
const oracle = JSON.parse(oracleText);
const base = '_easy_claude_work/ai14h_generation3_audit/frozen-runtime11/';
const proPath = base + 'js/spb-pro-ai.js';
const memPath = base + 'js/spb-ai-part-memory.js';
const projectPath = base + 'js/spb-ai-part-memory-project.js';
const canvasPath = base + 'paint-booth-3-canvas.js';
const read = p => fs.readFileSync(p, 'utf8');
const hashFile = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').toUpperCase();
const pro = read(proPath), mem = require(path.resolve(memPath)), projectSrc = read(projectPath), canvas = read(canvasPath);
function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `${name} exists`);
  const brace = source.indexOf('{', start); let depth = 0, quote = null, esc = false, line = false, block = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}
const guardFn = extractFunction(pro, 'durablePartMemorySourceIdentityCurrent');
const guardCtx = vm.createContext({ String, RegExp });
vm.runInContext(`${guardFn}; this.guard=durablePartMemorySourceIdentityCurrent;`, guardCtx);
const guard = guardCtx.guard;
const projectCtx = vm.createContext({ Object, Array, String, JSON, isFinite, console });
vm.runInContext(projectSrc, projectCtx, { filename: projectPath });
const makeHash = b => crypto.createHash('sha256').update(String(b)).digest('hex');
const mask = [7, 1, 2, 9];
const maskHash = '4:abc';
const baseProv = { r: JSON.stringify({ part: 'roof', layers: ['Car Paint'] }), z: maskHash, p: maskHash, l: 'Car Paint', e: '' };
function exercise(c, afterCapture) {
  const live = { kind: c.kind, path: c.path, fingerprint: c.fingerprint, width: 2048, height: 2048, generation: 12, committed: true };
  const tx = { getCommittedPath: () => live.path, getCommittedFingerprint: () => live.fingerprint, getGeneration: () => live.generation, getCommittedKind: () => live.kind };
  const bridge = projectCtx.SpbAIPartMemoryProject.createRuntime(mem, {
    transaction: tx,
    dimensions: () => ({ width: live.width, height: live.height }),
    isCommitted: (p, fp, g) => p === live.path && fp === live.fingerprint && g === live.generation && guard(live.kind, fp),
    sameSourcePath: (a, b) => String(a).toLowerCase() === String(b).toLowerCase(),
    editKey: r => JSON.stringify({ part: r.part || r.island || '', layers: r.layers || [] }),
    hashMask: m => m && m.length === 4 ? maskHash : '',
    CAR: { maskFor: () => ({ mask: mask.slice() }) },
    countOwners: () => 1,
    selectorLayerIds: () => ['layer-1'],
    partOwnerCurrent: () => true,
    registerOwner: () => true
  });
  const zone = { id: 'zone-roof-1', name: 'AI Roof', muted: false, useRegion: true, regionMask: mask.slice(), sourceLayer: 'layer-1', sourceLayerBindings: { 'layer-1': { label: 'Paintable Area / Car Paint' } }, _aiPartProv: Object.assign({}, baseProv) };
  const saved = bridge.capture(zone);
  let rebound = 0, rejected = 0;
  if (saved) {
    if (afterCapture) Object.assign(live, afterCapture);
    const reopened = Object.assign({}, zone, { _aiPartProv: undefined, _spbAIPartMemoryPending: null });
    bridge.stage(reopened, saved);
    const result = bridge.rebindAfterCommit([reopened]);
    rebound = result.rebound; rejected = result.rejected;
  }
  return { capture: !!saved, schemaHasOnlyPathFingerprintDims: !!saved && Object.keys(saved.source).sort().join(',') === 'fingerprint,height,path,width', restore: rebound === 1, rejected, returnedFingerprint: saved && saved.source.fingerprint || null };
}
const cases = [
  {id:'layered-psd-file-sha', kind:'layered', path:'C:/paint/car.psd', fingerprint:'file-sha256:' + 'a'.repeat(64), policy:'allow'},
  {id:'layered-psd-composite-only', kind:'layered', path:'C:/paint/car.psd', fingerprint:'composite-sha256:' + 'b'.repeat(64), policy:'deny'},
  {id:'flat-tga-new-header-attested', kind:'flat', path:'C:/paint/car.tga', fingerprint:'file-sha256:' + 'c'.repeat(64), policy:'allow'},
  {id:'browser-flat-file-attested', kind:'flat-file', path:'browser-file:car.tga', fingerprint:'file-sha256:' + 'd'.repeat(64), policy:'allow'},
  {id:'flat-url-cached-composite', kind:'flat-url', path:'https://example.invalid/car.tga', fingerprint:'composite-sha256:' + 'e'.repeat(64), policy:'deny'},
  {id:'bare-png-composite', kind:'flat', path:'C:/paint/car.png', fingerprint:'composite-sha256:' + 'f'.repeat(64), policy:'deny'},
  {id:'legacy-composite-hash-shaped', kind:'legacy-composite', path:'C:/paint/car.tga', fingerprint:'file-sha256:' + '1'.repeat(64), policy:'deny'},
  {id:'ora-lazy-path-digest', kind:'layered', path:'C:/paint/car.ora', fingerprint:'file-sha256:' + '2'.repeat(64), policy:'deny'},
  {id:'xcf-lazy-path-digest', kind:'layered', path:'C:/paint/car.xcf', fingerprint:'file-sha256:' + '3'.repeat(64), policy:'deny'},
  {id:'unknown-kind-digest', kind:'mystery-format', path:'C:/paint/car.bin', fingerprint:'file-sha256:' + '4'.repeat(64), policy:'deny'},
  {id:'unsupported-psb-digest', kind:'layered', path:'C:/paint/car.psb', fingerprint:'file-sha256:' + '5'.repeat(64), policy:'deny'},
  {id:'different-bytes-same-path', kind:'flat-file', path:'browser-file:car.tga', fingerprint:'file-sha256:' + '6'.repeat(64), restoreFingerprint:'file-sha256:' + '7'.repeat(64), capturePolicy:'allow', policy:'deny'}
];
const rows = cases.map(c => Object.assign({ id: c.id, kind: c.kind, path: c.path, fingerprintPrefix: c.fingerprint.slice(0, 24), expectedPolicy: c.policy, guardAllows: guard(c.kind, c.fingerprint) }, exercise(c, c.restoreFingerprint ? { fingerprint: c.restoreFingerprint } : null)));
const byId = Object.fromEntries(rows.map(r => [r.id, r]));
const expectedAllowed = c => c.policy === 'allow';
const mismatches = rows.filter(r => { const c = cases.find(q => q.id === r.id); return r.capture !== (c.capturePolicy ? c.capturePolicy === 'allow' : expectedAllowed(c)) || r.restore !== expectedAllowed(c); });
const report = {
  workItem: 'W120 independent durable part-memory source identity audit',
  status: mismatches.length ? 'CONFIRMED_KIND_OR_BYTE_PROVENANCE_GAPS' : 'PASS_PRIVATE_CONTRACT',
  sourcePins: {
    proAI: { path: proPath, sha256: hashFile(proPath), guard: 'durablePartMemorySourceIdentityCurrent(kind, fingerprint)' },
    partMemory: { path: memPath, sha256: hashFile(memPath) },
    partMemoryProject: { path: projectPath, sha256: hashFile(projectPath) },
    canvas: { path: canvasPath, sha256: hashFile(canvasPath), sourceKindGetter: /getCommittedKind:\s*function/.test(canvas), fileByteMarker: /file\.arrayBuffer\(\)/.test(canvas) }
  },
  oracle: { path: oraclePath, sha256: crypto.createHash('sha256').update(oracleText).digest('hex').toUpperCase(), cases: oracle.cases.length, frozenBeforeDynamicReplay: true },
  exercise: 'Extracted actual Runtime11 durable source gate; executed actual frozen PartMemoryProject.createRuntime + capture/stage/rebindAfterCommit and real part-memory saveRecord/prepareRestore with controlled valid unique-owner/current-mask proof. I/O and app UI were not called.',
  summary: { cases: rows.length, captured: rows.filter(r => r.capture).length, restored: rows.filter(r => r.restore).length, policyMismatches: mismatches.length, currentSessionEditGateNotExercised: true, providers: 0, native: 0, serverWrites: 0 },
  rows,
  changedSamePathBytesControl: { id: 'different-bytes-same-path', capturedFingerprint: cases[cases.length - 1].fingerprint, restoreFingerprint: cases[cases.length - 1].restoreFingerprint, samePath: true, result: byId['different-bytes-same-path'], interpretation: 'The actual saved record refuses a changed current fingerprint at the same path; this audits the consumer compare, not whether a production loader recomputes bytes instead of returning a stale cached digest.' },
  findings: [
    'The current predicate grants durable eligibility to every non-layered kind and to any file-sha256-shaped fingerprint for layered input; it does not whitelist kind/path pairs.',
    'The actual saved record contains only path, fingerprint, width and height; it does not persist or independently validate source kind or byte-digest provenance.',
    'For byte-attested PSD/TGA/browser-file cases, the helper can only be as trustworthy as the producer of fingerprint and committed-kind metadata. Cache/header correctness and raw bytes must be checked by the loader/backend contract.',
    'ORA/XCF actual W94 adapters preserve a composite identity because they parse from lazy paths; a synthetic layered+file-sha value was accepted here by the generic guard, even though that is not the W94 adapter’s actual output.',
    'A denial of durable rebind is not a denial of current-session editing; this harness only exercises durable capture/rebind.'
  ],
  limitations: ['The real source transaction was read-only inspected, not booted. The capture/rebind harness controls its transaction metadata and CAR proof, so it demonstrates consumer policy, not real TGA import cache freshness.', 'The same-path/different-byte case is represented by a different supplied fingerprint; it is not a native modified-TGA replacement trial.', 'The test uses a valid synthetic roof-zone fixture and does not claim any specific current vehicle has a current saveable owner.']
};
fs.writeFileSync(path.join(root, 'docs/handoff_reports/AI_HELPER_14H_DURABLE_PART_MEMORY_IDENTITY_W120_REVIEW_2026-10-04.json'), JSON.stringify(report, null, 2) + '\n');
assert.equal(rows.length, 12);
assert(byId['layered-psd-file-sha'].restore, 'expected valid PSD byte-digest control to capture/rebind');
assert(byId['flat-tga-new-header-attested'].restore, 'characterize current guard for proposed flat TGA byte digest');
assert(byId['browser-flat-file-attested'].restore, 'characterize current guard for proposed browser-file byte digest');
assert.equal(byId['different-bytes-same-path'].restore, false, 'a record captured from bytes A must not rebind to different bytes B at the same path');
console.log(JSON.stringify({ status: report.status, cases: rows.length, captures: report.summary.captured, restores: report.summary.restored, mismatches: mismatches.map(r => r.id), report: 'docs/handoff_reports/AI_HELPER_14H_DURABLE_PART_MEMORY_IDENTITY_W120_REVIEW_2026-10-04.json' }, null, 2));
