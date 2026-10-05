'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const clientPath = '_easy_claude_work/ai14h_generation3_candidate/w81_source_chain/paint-booth-3-canvas.js';
const routePath = '_easy_claude_work/ai14h_w81_review/frozen/psd_import_routes.py';
const serverPath = '_easy_claude_work/ai14h_w81_review/frozen/server.py';
const expected = new Map([
  [clientPath, 'ef180b9b67b7e95c7c0a00b3932259fbb35752a4ebfd8087e5bbf592d12e5a01'],
  [routePath, 'faf99df7eddeed1623342efda2479bbd23fb1d763b5f7759df8068f63ee0d902'],
  [serverPath, '1b094f80d81582416b03b0c63f1814665fb78969f2bb1675e5219e710c522294']
]);
function readPinned(path) {
  const bytes = fs.readFileSync(path);
  const digest = crypto.createHash('sha256').update(bytes).digest('hex');
  assert.equal(digest, expected.get(path), `frozen input changed: ${path}`);
  return bytes.toString('utf8');
}
const client = readPinned(clientPath);
const route = readPinned(routePath);
readPinned(serverPath);

// Check the actual two-request protocol, not a mock alias. The backend's
// accepted request member, its response receipt, and the client's body/member
// and receipt check must all be the same exact field.
const clientRaster = client.slice(client.indexOf('// W81: bind layer pixels'), client.indexOf('if (!rasterData || !rasterData.success', client.indexOf('// W81: bind layer pixels')));
assert.match(clientRaster, /\{ sourceBytesSha256: data\.sourceBytesSha256 \}/);
assert.match(clientRaster, /rasterData\.sourceBytesSha256 !== data\.sourceBytesSha256/);
assert.doesNotMatch(clientRaster, /expectedSourceBytesSha256/);
assert.match(route, /if 'sourceBytesSha256' in data:/);
assert.match(route, /source_digest = data\.get\('sourceBytesSha256'\)/);
assert.match(route, /payload\['sourceBytesSha256'\] = source_digest/);

// Byte-bound identity is strong-only; weak legacy fingerprints remain typed
// composite identities and cannot masquerade as a source file digest.
const fingerprintStart = client.indexOf('function _spbLayeredSourceFingerprint(');
const fingerprint = client.slice(fingerprintStart, client.indexOf('\n        function _spbDecodeImage', fingerprintStart));
assert.match(fingerprint, /file-sha256:' \+ data\.sourceBytesSha256/);
assert.match(fingerprint, /composite-sha256:/);
assert.match(fingerprint, /composite-fnv1a32:/);

// Replay actual import orchestration closures with controlled effects. This
// suite intentionally stops at pixel staging; the route's separate real-PSD
// tests below exercise the backend raster receipt and replacement races.
const replay = spawnSync(process.execPath, ['tests/ai_source_chain_w81_contract.cjs', clientPath], { encoding: 'utf8' });
assert.equal(replay.status, 0, replay.stderr || replay.stdout);
const outcome = JSON.parse(replay.stdout);
assert.equal(outcome.status, 'PASS_WITH_LIMITS');
assert.equal(outcome.cases, 7);
assert.equal(outcome.sha256, expected.get(clientPath));
console.log(JSON.stringify({
  status: 'PASS_WITH_LIMITS',
  cases: 7,
  crossEndpointField: 'sourceBytesSha256',
  clientSha256: expected.get(clientPath),
  routeSha256: expected.get(routePath),
  clientReplay: outcome.rows.map(({ id, result, layerPixelStageReached, priorSourceRetained }) => ({ id, result, layerPixelStageReached, priorSourceRetained })),
  limits: [
    'Actual client closures are exercised with controlled fetch/decode/native-effect stubs and stop at layer pixel staging.',
    'Actual private Flask route is covered separately by ai_source_bytes_psd_rasterize_w81_candidate_contract.py with generated PSDs.',
    'No native app, live server, provider, or source document was changed.'
  ]
}, null, 2));
