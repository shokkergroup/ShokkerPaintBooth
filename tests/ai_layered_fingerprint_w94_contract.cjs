/* Source identity adapter review: immutable PSD snapshots authorize durable
 * binding; path-backed ORA/XCF sources retain session-only composite identity. */
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const crypto = require('crypto');
const input = process.argv[2] || path.resolve(__dirname, '../_easy_claude_work/ai14h_generation3_candidate/integration12/paint-booth-3-canvas.js');
const source = fs.readFileSync(input, 'utf8');
const start = source.indexOf('function _spbLayeredSourceFingerprint(');
const end = source.indexOf('function _spbDecodeImage(', start);
assert(start >= 0 && end > start);
const ctx = {};
vm.createContext(ctx);
vm.runInContext(source.slice(start, end), ctx);
const digest = 'a'.repeat(64), composite = 'b'.repeat(64);
const f = ctx._spbLayeredSourceFingerprint;
for (const ext of ['psd', 'PSB']) assert.equal(f({psd_path: 'C:/fixture.' + ext, sourceBytesSha256: digest}, composite), 'file-sha256:' + digest);
for (const ext of ['ora', 'XCF']) assert.equal(f({psd_path: 'C:/fixture.' + ext, sourceBytesSha256: digest}, composite), 'composite-sha256:' + composite);
assert.equal(f({psd_path: 'C:/fixture.ora', sourceBytesSha256: digest}, 'fnv1a32-ab12cd34-42'), 'composite-fnv1a32:fnv1a32-ab12cd34-42');
assert.equal(f({psd_path: 'C:/fixture.xcf', sourceBytesSha256: digest}, null), '');
assert.equal(f({}, composite), 'composite-sha256:' + composite);
assert.throws(() => f({sourceBytesSha256: 'malformed'}, composite), /invalid source byte fingerprint/);
console.log(JSON.stringify({status:'PASS', cases:8, input, sha256:crypto.createHash('sha256').update(source).digest('hex'), providers:0, scope:'Actual fingerprint function; no parser/import/native claim'}));
