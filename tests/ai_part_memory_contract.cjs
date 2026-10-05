'use strict';
// Frozen W26 schema oracle, written before creating the proposed module.
const ORACLE = Object.freeze([
  'valid-live-provenance-bound-to-verified-committed-source-and-dimensions',
  'same-canonical-source-path-and-same-fingerprint-may-rebind-new-runtime-generation',
  'same-path-with-different-source-fingerprint-is-rejected',
  'missing-or-unverified-source-fingerprint-is-rejected',
  'missing-current-runtime-generation-is-rejected',
  'saved-old-generation-is-never-reused-as-current-generation',
  'source-dimension-change-is-rejected',
  'stale-region-mask-hash-is-rejected',
  'stale-part-mask-hash-is-rejected',
  'stale-layout-signature-is-rejected',
  'stale-element-signature-is-rejected',
  'zone-id-or-material-owner-identity-mismatch-is-rejected',
  'duplicate-or-ambiguous-owner-is-rejected',
  'unknown-schema-version-is-rejected',
  'malformed-or-forged-private-record-is-rejected',
  'private-record-never-serializes-raw-masks-or-region-vectors',
  'sanitizer-does-not-mutate-zone-or-live-provenance-input',
  'absence-of-proof-returns-no-ownership-and-requires-explicit-ask'
]);

if (require.main === module) {
  const assert = require('node:assert/strict');
  const fs = require('node:fs');
  const path = require('node:path');
  const root = path.resolve(__dirname, '..');
  const Memory = require(path.join(root, 'js/spb-ai-part-memory.js'));
  const kit = fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8');
  const hashMatch = kit.match(/function regionMaskHash\(mask\)\s*\{[\s\S]*?\n\s{4}\}/);
  assert.ok(hashMatch, 'actual ZoneKit regionMaskHash helper is available');
  const regionMaskHash = new Function(`return (${hashMatch[0]});`)();
  let checks = 0;
  assert.equal(ORACLE.length, 18);
  const current = { committed: true, path: 'C:/paint/cup.tga', fingerprint: 'sha256:source-A', width: 2048, height: 1024, generation: 11 };
  const region = { part: 'roof', portion: 'whole', colors: [], layers: [] };
  const regionMask = new Uint8Array([1, 0, 1, 0]);
  const partMask = new Uint8Array([0, 1, 0, 1]);
  const liveProv = { r: JSON.stringify(region), z: regionMaskHash(regionMask), p: regionMaskHash(partMask), l: 'layout-A', e: 'element-A' };
  const owner = { id: 'zone-7', name: 'Roof', muted: false, useRegion: true, regionMask, _aiPartProv: liveProv };
  const keyFor = r => `part:${r.part}:${r.portion}`;
  function proof(options = {}) {
    const o = options;
    return {
      isCommittedSource: source => source.committed === true && !!source.fingerprint && Number.isInteger(source.generation) && source.generation > 0,
      sameSourcePath: (a, b) => String(a).replace(/\\/g, '/').toLowerCase() === String(b).replace(/\\/g, '/').toLowerCase(),
      editKey: keyFor,
      partOwnerCurrent(z, p, key, source) {
        const r = JSON.parse(p.r);
        return z.useRegion === true && !z.muted && z.id === 'zone-7' && z.name === 'Roof' && key === keyFor(r) &&
          p.z === regionMaskHash(z.regionMask) && p.p === regionMaskHash(o.partMask || partMask) &&
          p.l === (o.layout || 'layout-A') && p.e === (o.element || 'element-A') && !!source.committed;
      },
      partMaskCurrent(z, p) { return p.p === regionMaskHash(o.partMask || partMask); },
      countOwners: () => o.ownerCount == null ? 1 : o.ownerCount
    };
  }
  const beforeZone = JSON.stringify(owner);
  const saved = Memory.saveRecord(owner, current, proof());
  assert.ok(saved, 'a live, uniquely proven named-part owner is serializable'); checks++;
  assert.equal(JSON.stringify(owner), beforeZone, 'save sanitizer does not mutate live zone/provenance'); checks++;
  assert.equal(saved.schema, Memory.schema);
  assert.equal(saved.owner.zoneId, owner.id);
  assert.equal(saved.owner.name, owner.name);
  assert.equal(saved.owner.key, keyFor(region)); checks++;
  assert.deepEqual(Object.keys(saved.source).sort(), ['fingerprint', 'height', 'path', 'width']); checks++;
  assert.deepEqual(Object.keys(saved.provenance).sort(), ['e', 'l', 'p', 'r', 'z']); checks++;
  assert.equal(Object.hasOwn(saved, 'generation'), false);
  assert.doesNotMatch(JSON.stringify(saved), /regionMask|spatialMask|pixeldata|imagedata/i); checks++;

  const restoredZone = { id: 'zone-7', name: 'Roof', muted: false, useRegion: true, regionMask: new Uint8Array(regionMask) };
  const newLoad = Object.assign({}, current, { generation: 24 });
  const recordBeforeRestore = JSON.stringify(saved), zoneBeforeRestore = JSON.stringify(restoredZone);
  const rebound = Memory.prepareRestore(JSON.parse(JSON.stringify(saved)), newLoad, restoredZone, proof());
  assert.ok(rebound && rebound.authorizedByCurrentOwnerProof);
  assert.equal(rebound.runtimeBinding.generation, 24, 'runtime generation is rebound from the verified current source');
  assert.equal(Object.hasOwn(rebound.provenance, 'generation'), false);
  assert.equal(rebound.provenance.z, regionMaskHash(regionMask)); checks++;
  assert.equal(JSON.stringify(saved), recordBeforeRestore);
  assert.equal(JSON.stringify(restoredZone), zoneBeforeRestore); checks++;

  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { path: 'c:/PAINT/CUP.TGA' }), restoredZone, proof())?.ok, true, 'same path spelling/case is delegated to caller path comparison'); checks++;
  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { path: 'C:/paint/other.tga' }), restoredZone, proof()), null);
  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { fingerprint: 'sha256:source-B' }), restoredZone, proof()), null); checks++;
  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { committed: false }), restoredZone, proof()), null); checks++;
  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { fingerprint: '' }), restoredZone, proof()), null); checks++;
  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { generation: undefined }), restoredZone, proof()), null); checks++;
  assert.equal(Memory.prepareRestore(saved, Object.assign({}, newLoad, { width: 1024 }), restoredZone, proof()), null); checks++;

  let altered = JSON.parse(JSON.stringify(saved)); altered.provenance.z = regionMaskHash(new Uint8Array([1, 1, 1, 1]));
  assert.equal(Memory.prepareRestore(altered, newLoad, restoredZone, proof()), null, 'changed current region mask fails live proof'); checks++;
  altered = JSON.parse(JSON.stringify(saved)); altered.provenance.p = regionMaskHash(new Uint8Array([1, 1, 1, 1]));
  assert.equal(Memory.prepareRestore(altered, newLoad, restoredZone, proof()), null, 'changed part mask fails live proof'); checks++;
  assert.equal(Memory.prepareRestore(saved, newLoad, restoredZone, proof({ layout: 'layout-B' })), null);
  assert.equal(Memory.prepareRestore(saved, newLoad, restoredZone, proof({ element: 'element-B' })), null); checks++;

  assert.equal(Memory.prepareRestore(saved, newLoad, Object.assign({}, restoredZone, { id: 'zone-8' }), proof()), null);
  assert.equal(Memory.prepareRestore(saved, newLoad, Object.assign({}, restoredZone, { name: 'Old Roof' }), proof()), null);
  altered = JSON.parse(JSON.stringify(saved)); altered.owner.key = 'forged-owner';
  assert.equal(Memory.prepareRestore(altered, newLoad, restoredZone, proof()), null); checks++;
  assert.equal(Memory.prepareRestore(saved, newLoad, restoredZone, proof({ ownerCount: 2 })), null, 'ambiguous duplicate owner fails closed'); checks++;
  assert.equal(Memory.prepareRestore(saved, newLoad, restoredZone, {}), null, 'absence of actual current-owner validators fails closed'); checks++;
  assert.equal(Memory.prepareRestore(saved, newLoad, Object.assign({}, restoredZone, { muted: true }), proof()), null); checks++;

  altered = JSON.parse(JSON.stringify(saved)); altered.schema = 'spb-ai-part-memory/99';
  assert.equal(Memory.sanitizeRecord(altered), null);
  altered = JSON.parse(JSON.stringify(saved)); altered.generation = current.generation;
  assert.equal(Memory.sanitizeRecord(altered), null);
  altered = JSON.parse(JSON.stringify(saved)); altered.provenance.r = '{bad';
  assert.equal(Memory.sanitizeRecord(altered), null);
  altered = JSON.parse(JSON.stringify(saved)); altered.provenance.r = JSON.stringify({ part: 'roof', mask: [1, 0, 1] });
  assert.equal(Memory.sanitizeRecord(altered), null); checks++;

  assert.equal(Memory.saveRecord(owner, current, {}), null);
  const unverifiedSourceProof = proof(); delete unverifiedSourceProof.isCommittedSource;
  assert.equal(Memory.saveRecord(owner, current, unverifiedSourceProof), null);
  assert.equal(Memory.prepareRestore(saved, newLoad, restoredZone, unverifiedSourceProof), null);
  assert.equal(Memory.saveRecord(Object.assign({}, owner, { id: 'zone-7', _aiPartProv: { r: JSON.stringify({ part: 'roof', mask: [1] }), z: liveProv.z, p: liveProv.p, l: liveProv.l, e: liveProv.e } }), current, proof()), null); checks++;
  assert.equal(Memory.saveRecord(owner, Object.assign({}, current, { generation: 0 }), proof()), null);
  assert.equal(Memory.saveRecord(Object.assign({}, owner, { regionMask: null }), current, proof()), null);
  assert.equal(Memory.saveRecord(Object.assign({}, owner, { muted: true }), current, proof()), null); checks++;

  console.log(`PASS W26 part-memory prototype contract: frozen ${ORACLE.length}-case schema oracle; candidate helper is uninstalled.`);
}
module.exports = { ORACLE };
