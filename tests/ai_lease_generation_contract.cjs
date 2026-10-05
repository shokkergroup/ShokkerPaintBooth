/* W36 frozen oracle: do not edit its cases while evaluating the candidate. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

const ROOT = path.resolve(__dirname, '..');
const CAND = path.join(ROOT, '_easy_claude_work', 'ai14h_w36_candidate');
const ORACLE = Object.freeze([
  'successful-begin-owns-unique-generation',
  'rejected-begin-does-not-own',
  'generation-matched-end',
  'stale-same-owner-end-cannot-release-successor',
  'mismatched-end-does-not-refresh-idle',
  'unscoped-legacy-end-compatibility',
  'holdInternal-captures-own-generation',
  'core-success-release-own-generation',
  'core-error-abort-release-own-generation',
  'active-internal-owner-no-overlap'
]);
const ORACLE_SHA256 = '61998ECA962627CE0BC505762196DFBE609523F4839EF5652C6C75D0213AB904';
const oracleHash = crypto.createHash('sha256').update(ORACLE.join('\n') + '\n').digest('hex').toUpperCase();
if (oracleHash !== ORACLE_SHA256) throw new Error('Frozen W36 oracle changed: ' + oracleHash);

function runtime(fetchImpl) {
  let now = 1000;
  function FakeDate() {}
  FakeDate.now = () => now;
  const ctx = { console, Promise, Date: FakeDate, fetch: fetchImpl || (() => Promise.reject(new Error('unexpected fetch'))), AbortController, setTimeout, clearTimeout };
  ctx.window = ctx;
  vm.createContext(ctx);
  return { ctx, setNow: n => { now = n; } };
}
function load(ctx, name) { vm.runInContext(fs.readFileSync(path.join(CAND, name), 'utf8'), ctx, { filename: name }); }
function jsonResponse(value) { return { text: () => Promise.resolve(JSON.stringify(value)) }; }
async function flush() { await Promise.resolve(); await Promise.resolve(); await new Promise(resolve => setImmediate(resolve)); }

async function main() {
  const checks = [];
  const add = (name, fn) => { fn(); checks.push(name); };

  const leaseRt = runtime(); load(leaseRt.ctx, 'spb-ai-lease.generation-candidate.js');
  const L = leaseRt.ctx.SpbAiLease;
  let g1, g2;
  add('successful-begin-owns-unique-generation', () => {
    assert.equal(L.begin('external'), true); g1 = L.generation();
    assert.ok(g1 > 0); assert.equal(L.begin('external'), false);
  });
  add('rejected-begin-does-not-own', () => {
    assert.equal(L.begin('internal'), false); assert.equal(L.generation(), g1);
  });
  add('generation-matched-end', () => {
    assert.equal(L.end(g1), true); assert.equal(L.generation(), 0);
  });
  add('stale-same-owner-end-cannot-release-successor', () => {
    assert.equal(L.begin('external'), true); g2 = L.generation(); assert.ok(g2 > g1);
    assert.equal(L.end(g1), false); assert.equal(L.generation(), g2); assert.equal(L.owner(), 'external');
  });
  add('mismatched-end-does-not-refresh-idle', () => {
    assert.equal(L.end(g2), true); leaseRt.setNow(100000); assert.equal(L.end(g1), false);
    leaseRt.setNow(121000); assert.equal(L.owner(), '');
  });
  add('unscoped-legacy-end-compatibility', () => {
    assert.equal(L.begin('external'), true); assert.equal(L.end(), true);
    assert.equal(L.owner(), 'external'); assert.equal(L.generation(), 0);
    assert.equal(L.begin('external'), true); const g = L.generation(); assert.equal(L.end(g), true);
  });
  add('holdInternal-captures-own-generation', () => {
    leaseRt.setNow(300000);
    assert.equal(L.internal(), true); assert.equal(L.holdInternal(), true);
    const held = L.generation(); assert.ok(held > 0); assert.equal(L.holdInternal(), false);
    assert.equal(L.end(held), true);
  });
  add('active-internal-owner-no-overlap', () => {
    assert.equal(L.holdInternal(), true); const held = L.generation();
    assert.equal(L.holdInternal(), false); assert.equal(L.generation(), held); assert.equal(L.end(held), true);
  });

  // Exercise the actual candidate core module with only its fetch boundary controlled.
  let resolveFetch, fetchMode = 'success';
  const coreRt = runtime(() => {
    if (fetchMode === 'deferred') return new Promise(resolve => { resolveFetch = resolve; });
    if (fetchMode === 'abort') { const e = new Error('cancelled'); e.name = 'AbortError'; return Promise.reject(e); }
    if (fetchMode === 'offline') return Promise.reject(new Error('offline'));
    return Promise.resolve(jsonResponse({ ok: true, message: { content: 'done' }, model: 'stub' }));
  });
  load(coreRt.ctx, 'spb-ai-lease.generation-candidate.js');
  load(coreRt.ctx, 'spb-ai-core.generation-candidate.js');
  const CL = coreRt.ctx.SpbAiLease, AI = coreRt.ctx.SpbAI;
  const opts = { system: 'test', user: 'test', tools: [], maxSteps: 1 };

  CL.internal();
  const success = AI.run(opts);
  await success;
  assert.equal(CL.generation(), 0);
  checks.push('core-success-release-own-generation');

  fetchMode = 'offline';
  const offline = await AI.run(opts);
  assert.ok(offline.error); assert.equal(CL.generation(), 0);
  fetchMode = 'abort';
  const aborted = await AI.run(opts);
  assert.ok(aborted.error); assert.equal(CL.generation(), 0);
  checks.push('core-error-abort-release-own-generation');

  // Simulate A being retired and a same-owner B being acquired while A awaits.
  fetchMode = 'deferred';
  const lateA = AI.run(opts);
  await flush();
  const genA = CL.generation(); assert.ok(genA > 0); assert.equal(typeof resolveFetch, 'function');
  assert.equal(CL.end(genA), true);
  assert.equal(CL.begin('internal'), true); const genB = CL.generation(); assert.ok(genB > genA);
  resolveFetch(jsonResponse({ ok: true, message: { content: 'A done' }, model: 'stub' }));
  await lateA;
  assert.equal(CL.generation(), genB); assert.equal(CL.owner(), 'internal');
  assert.equal(CL.end(genB), true);
  checks.push('late-core-completion-cannot-release-successor');

  // Candidate core's synchronous throw path is also wrapped and releases its token.
  let threw = false;
  try { await AI.run(null); } catch (_) { threw = true; }
  assert.equal(threw, true); assert.equal(CL.generation(), 0);
  checks.push('core-synchronous-throw-releases-own-generation');

  console.log(JSON.stringify({ ok: true, frozenOracleSha256: ORACLE_SHA256, checks }, null, 2));
}
main().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
