'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const oraclePath = '_easy_claude_work/ai14h_w102_review/fresh-oracle.json';
const oracleBytes = fs.readFileSync(path.join(root, oraclePath));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
assert.equal(sha(oracleBytes), '7d4d2910ad8196e62b2b355b6217ea3883e6a24eb7621f50e8cdc8b86b680b84');
assert.equal(JSON.parse(oracleBytes).cases.length, 11);
const candidatePath = '_easy_claude_work/ai14h_w97_review/candidate-spb-pro-ai.js';
const candidate = fs.readFileSync(path.join(root, candidatePath), 'utf8');
assert.equal(sha(Buffer.from(candidate)), 'e6840fc79cdcd7e0e11ccad677a34eb7ab86cd903bbe0652089769187da19909');
function run(fp) {
  const result = spawnSync(process.execPath, [path.join(__dirname, 'ai_part_finish_owner_w102_runner.cjs')], {
    cwd: root, encoding: 'utf8', env: { ...process.env, W102_FINGERPRINT: fp }
  });
  assert(result.stdout, result.stderr || `runner failed for ${fp}`);
  const out = JSON.parse(result.stdout);
  assert.equal(out.sourceHashes.controller, sha(Buffer.from(candidate)));
  assert.equal(out.effects.applyCalls, 0);
  assert.equal(out.effects.providerCalls, 0);
  assert.equal(out.effects.nativeCalls, 0);
  return out;
}
const file = run(`file-sha256:${'a'.repeat(64)}`);
const compositeSha = run(`composite-sha256:${'a'.repeat(64)}`);
const compositeFnv = run('composite-fnv1a32:fnv1a32-abcdef01-4096');
assert.deepEqual([file.counts.cases, file.counts.passed, file.counts.failed], [12, 11, 1]);
assert.deepEqual([compositeSha.counts.cases, compositeSha.counts.passed, compositeSha.counts.failed], [12, 7, 5]);
assert.deepEqual([compositeFnv.counts.cases, compositeFnv.counts.passed, compositeFnv.counts.failed], [12, 7, 5]);
for (const out of [compositeSha, compositeFnv]) {
  const failed = new Set(out.results.filter(x => !x.pass).map(x => x.id));
  for (const id of ['roof-chrome-keep-paint', 'roof-satin-keep-paint', 'roof-ordinary-finish', 'same-roof-alias-control']) assert(failed.has(id), `${id} should expose composite-fingerprint rejection`);
  for (const id of ['partial-roof-owner', 'stale-source-owner', 'duplicate-roof-owners', 'manual-roof-zone', 'stale-layout-owner', 'hidden-body-layer-owner', 'mixed-paint-owner']) assert(!failed.has(id), `${id} remains a passing refusal`);
}
const fileFailed = new Set(file.results.filter(x => !x.pass).map(x => x.id));
assert.deepEqual([...fileFailed], ['roof-gloss-keep-paint']); // parser gap explicitly out of W102 scope
const report = {
  frozenOracle: { path: oraclePath, sha256: sha(oracleBytes), cases: 11 },
  pins: { candidatePath, candidateSha256: sha(Buffer.from(candidate)), designSha256: '4648de3231015497cc9ff816612a542097a1ad14038a7210753f6cdbfd88d832', editSha256: '3696cf6c9bdf9a28a056ebf90a9ddd23cfe290134943c11beb4c7ec5485a173a' },
  results: { fileSha256: file.counts, compositeSha256: compositeSha.counts, compositeFnv1a32: compositeFnv.counts },
  compositeRefusals: ['roof-chrome-keep-paint','roof-satin-keep-paint','roof-ordinary-finish','same-roof-alias-control'],
  controls: 'Partial/stale/duplicate/manual/hidden/mixed-owner refusals still pass under all fingerprints.',
  limits: 'Producer contract harness controls CAR/Z/source callbacks and edit callback. No makeTools/applyQueue/native/provider execution.'
};
console.log(JSON.stringify(report, null, 2));
