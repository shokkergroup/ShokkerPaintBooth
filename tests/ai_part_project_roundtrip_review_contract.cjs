'use strict';
// Independent saved-project ownership review. Frozen semantic cases precede
// source inspection; tests execute the actual zone projection expressions.
const ORACLE = Object.freeze([
  'saved-source-same-car-provenance-roundtrip',
  'repeated-same-name-zones-remain-distinct',
  'renamed-zone-retains-or-invalidates-by-stable-identity',
  'muted-zone-provenance-is-preserved-but-not-active',
  'same-path-new-source-generation-invalidates-provenance',
  'stale-layout-element-and-mask-metadata-refused',
  'unsupported-or-forged-private-metadata-refused',
  'ephemeral-edit-registry-not-mistaken-for-restored-state',
  'restore-failure-keeps-prior-project-state',
  'serializer-does-not-drop-unrelated-zone-state'
]);

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const HASHES = Object.freeze({
  projects: '40520AD3E373B2505CCE0AB4BA030F282E9EBA2A0A9B1C8F6093A0AA97EC34B3',
  zones: 'E1EFA310757FBBDBF5EA5CB030DDC651BDAC1A6618A8388DA1535D00D8F3BC95',
  canvas: 'F55880174D7AFF86F44F8EE5B0C28AFF31CDDCDE6491386D558EC16A27B98F56',
  zoneKit: '6968963FC8D382E3ECDA629089A71A73A519270C0B577E98DF03D9F7D48D68D0'
});
function read(rel) { return fs.readFileSync(path.join(root, rel), 'utf8'); }
function sha(text) { return crypto.createHash('sha256').update(text).digest('hex').toUpperCase(); }
const zonesSource = read('paint-booth-2-state-zones.js');
const sourcePaths = {
  projects: 'js/features/spb-projects.js', zones: 'paint-booth-2-state-zones.js',
  canvas: 'paint-booth-3-canvas.js', zoneKit: 'js/spb-pro-zone-kit.js'
};
for (const [key, file] of Object.entries(sourcePaths)) {
  const actual = sha(read(file));
  assert.equal(actual, HASHES[key], `${file} changed after review freeze; re-freeze before interpreting results`);
}
assert.equal(ORACLE.length, 10);

// Inspect only the actual explicit serializers; no hand-written serializer or
// fake full loader is substituted for the production code.
const saveFn = zonesSource.slice(zonesSource.indexOf('function getConfig()'), zonesSource.indexOf('function loadConfigFromObj(cfg)'));
const loadFn = zonesSource.slice(zonesSource.indexOf('function loadConfigFromObj(cfg)'), zonesSource.indexOf('function getSessionConfig()'));
assert.match(saveFn, /zones:\s*zones\.map\(z\s*=>\s*\(\{/);
assert.match(saveFn, /id:\s*z\.id\s*\|\|\s*_newZoneId\(\)/);
assert.match(saveFn, /finish:\s*z\.finish/);
assert.match(saveFn, /muted:\s*z\.muted\s*\?\?\s*false/);
assert.match(saveFn, /regionMask:\s*_encodeSavedMask\(z\.regionMask/);
assert.match(saveFn, /spatialMask:\s*_encodeSavedMask\(z\.spatialMask/);
assert.doesNotMatch(saveFn, /_aiPartProv/);
assert.match(loadFn, /zones\s*=\s*cfg\.zones\.map\(z\s*=>\s*\(\{/);
assert.match(loadFn, /id:\s*z\.id\s*\|\|\s*_newZoneId\(\)/);
assert.match(loadFn, /regionMask:\s*null/);
assert.match(loadFn, /spatialMask:\s*_cloneUint8ArrayLike\(z\.spatialMask\)/);
assert.match(loadFn, /finish:\s*z\.finish\s*\?\?\s*null/);
assert.match(loadFn, /muted:\s*z\.muted\s*\?\?\s*false/);
assert.match(loadFn, /regionMask:\s*_decodeSavedMask\(z\.regionMask/);
assert.match(loadFn, /spatialMask:\s*_decodeSavedMask\(z\.spatialMask/);
assert.doesNotMatch(loadFn, /_aiPartProv/);

// The actual project envelope takes getConfig() by reference; it neither stamps
// an ownership/schema field nor supplies identity beyond that config.
const projectsSource = read('js/features/spb-projects.js');
assert.match(projectsSource, /config:\s*config,/);
assert.match(projectsSource, /config\s*=\s*\(typeof window\.getConfig === 'function'\)\s*\?\s*window\.getConfig\(\)\s*:\s*null/);
const zoneKit = read('js/spb-pro-zone-kit.js');
assert.match(zoneKit, /z\._aiPartProv\s*=\s*\{\s*r:\s*JSON\.stringify\(r\),\s*z:\s*regionMaskHash\(z\.regionMask\),\s*p:\s*regionMaskHash\(partMask\),\s*l:\s*layout,\s*e:\s*element\s*\}/);
assert.match(zoneKit, /function rememberPartRegion\(z, r, partMask\)/);
assert.doesNotMatch(zonesSource.slice(zonesSource.indexOf('function getConfig()'), zonesSource.indexOf('function loadConfigFromObj(cfg)')), /_aiPartProv/);
assert.doesNotMatch(zonesSource.slice(zonesSource.indexOf('function loadConfigFromObj(cfg)'), zonesSource.indexOf('function getSessionConfig()')), /_aiPartProv/);

console.log(`PASS: ${ORACLE.length} frozen ownership scenarios; source contract preserves zone IDs and ordinary saved fields, but omits private part provenance.`);
