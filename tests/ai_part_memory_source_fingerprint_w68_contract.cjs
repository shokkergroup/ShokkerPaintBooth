'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const { TextEncoder } = require('node:util');
const root = process.cwd();
const freezePath = '_easy_claude_work/ai14h_w68_review/frozen/source-freeze.json';
const freeze = JSON.parse(fs.readFileSync(freezePath, 'utf8'));
function shaFile(p) { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'); }
for (const [p, expected] of Object.entries(freeze.hashes)) assert.equal(shaFile(p), expected, `frozen source drift: ${p}`);
assert.equal(shaFile('SPB Chevy Truck Starting Example PSD.psd'), freeze.fixturePsdSha256);
const canvas = fs.readFileSync('_easy_claude_work/ai14h_w68_review/frozen/paint-booth-3-canvas.js', 'utf8');
function extractFunction(name) {
  const marker = `async function ${name}(`;
  const start = canvas.indexOf(marker);
  assert(start >= 0, `missing ${name}`);
  const brace = canvas.indexOf('{', start);
  let depth = 0, quote = null, escape = false;
  for (let i = brace; i < canvas.length; i++) {
    const c = canvas[i];
    if (quote) { if (escape) escape = false; else if (c === '\\') escape = true; else if (c === quote) quote = null; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return canvas.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}
const hashFns = `${extractFunction('_spbFingerprintBytes')}\n${extractFunction('_spbFingerprintText')}\n`;
const ctx = vm.createContext({ crypto: crypto.webcrypto, TextEncoder, Uint8Array, Array, Math, String, Object, Promise });
vm.runInContext(`${hashFns}; this.fpText = _spbFingerprintText; this.fpBytes = _spbFingerprintBytes;`, ctx);
const fpText = (s) => ctx.fpText(s);
(async () => {
  const helper = require(path.resolve('_easy_claude_work/ai14h_w68_review/frozen/spb-ai-part-memory.js'));
  const aComposite = '<composite-pixels:unchanged-visible-image>';
  const fp = await fpText(aComposite);
  assert.equal(fp, await fpText(aComposite), 'same composite bytes should hash stably');
  assert.notEqual(fp, await fpText(aComposite + '|different-visible-pixel'), 'changed composite should change fingerprint');
  const bytesA = Buffer.from('fixture PSD bytes A');
  const bytesB = Buffer.from('fixture PSD bytes B');
  const rawA = crypto.createHash('sha256').update(bytesA).digest('hex');
  const rawB = crypto.createHash('sha256').update(bytesB).digest('hex');
  assert.notEqual(rawA, rawB);
  const sourceA = { committed:true, path:'C:/paint/car.psd', fingerprint:fp, width:1024, height:1024, generation:2 };
  const sourceB = { ...sourceA, generation:3 };
  const zone = { id:'zone-7', name:'Roof', muted:false, useRegion:true, regionMask:{ opaque:'mask' }, _aiPartProv:{ r:'{"part":"roof"}', z:'1:root', p:'2:roof', l:'Car Paint', e:'' } };
  const proof = {
    isCommittedSource: () => true,
    sameSourcePath: (a,b) => a === b,
    editKey: () => 'car|roof|Car Paint',
    partOwnerCurrent: () => true,
    partMaskCurrent: () => true,
    countOwners: () => 1
  };
  const saved = helper.saveRecord(zone, sourceA, proof);
  assert(saved, 'valid current owner should save');
  const restoredSameVisibleComposite = helper.prepareRestore(saved, sourceB, zone, proof);
  assert.equal(restoredSameVisibleComposite && restoredSameVisibleComposite.ok, true,
    'current helper accepts same path/dimensions/composite fingerprint after generation rebinding');
  assert.deepEqual(JSON.parse(JSON.stringify(restoredSameVisibleComposite.runtimeBinding)), { sourcePath:sourceB.path, fingerprint:fp, generation:3 });
  assert.notEqual(rawA, rawB, 'counterfactual source bytes differ despite identical supplied composite fingerprint');
  assert.equal(Object.hasOwn(saved.source, 'rawFingerprint'), false, 'saved source schema has no raw-file digest');
  assert.equal(helper.sanitizeRecord({ ...saved, source:{ ...saved.source, rawFingerprint:rawA } }), null,
    'unknown raw-file digest is rejected rather than silently consumed');
  const control = (source, changes={}) => helper.prepareRestore(saved, source, { ...zone, ...changes }, proof);
  assert.equal(control({ ...sourceB, fingerprint:await fpText(aComposite+' changed') }), null, 'changed composite fp rejects');
  assert.equal(control({ ...sourceB, width:2048 }), null, 'changed dimensions reject');
  assert.equal(control(sourceB, { id:'zone-other' }), null, 'changed owner id rejects');
  assert.equal(helper.prepareRestore(saved, { ...sourceB, committed:false }, zone, proof), null, 'uncommitted source rejects');
  assert.equal(helper.prepareRestore(saved, sourceB, zone, { ...proof, partMaskCurrent:() => false }), null, 'failed current mask proof rejects');
  console.log(JSON.stringify({ status:'PASS_WITH_LIMITS', checks:11, fpAlgorithm:fp.startsWith('fnv1a32-')?'legacy-fallback':'SHA-256/WebCrypto', fixturePsdSha256:freeze.fixturePsdSha256, nativeReportedCompositeFingerprint:freeze.nativeReportedCompositeFingerprint, finding:'synthetic same-composite/different-raw-byte scenario is accepted by current saved-memory interface; this establishes an interface gap, not a real modified-PSD native reproduction' }, null, 2));
})().catch(e => { console.error(e); process.exitCode = 1; });
