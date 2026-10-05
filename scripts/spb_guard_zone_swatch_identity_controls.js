const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_swatch_identity_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-swatch-identity-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneSwatchIdentityControls = {',
  'function getZoneColorHex(zone)',
  'function getBaseName(zone)',
  'function getPatternName(patternId)',
  'global.getZoneColorHex = getZoneColorHex',
  'global.getBaseName = getBaseName',
  'global.getPatternName = getPatternName'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneSwatchIdentityControls.install',
  "getBases: () => (typeof BASES !== 'undefined' ? BASES : [])",
  "getMonolithics: () => (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : [])",
  "getPatterns: () => (typeof PATTERNS !== 'undefined' ? PATTERNS : [])"
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function getZoneColorHex(zone) {',
  'function getBaseName(zone) {',
  'function getPatternName(patternId) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const defaultRestoreScript = indexOf(htmlSource, 'js/zones/zone-default-restore-controls.js', htmlFile);
const swatchIdentityScript = indexOf(htmlSource, 'js/zones/zone-swatch-identity-controls.js', htmlFile);
const createDuplicateScript = indexOf(htmlSource, 'js/zones/zone-create-duplicate-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(defaultRestoreScript < swatchIdentityScript, 'swatch identity module must load after default restore controls');
assert(swatchIdentityScript < createDuplicateScript, 'swatch identity module must load before create/duplicate controls');
assert(swatchIdentityScript < zonesScript, 'swatch identity module must load before the zone monster script');

console.log('[spb_guard_zone_swatch_identity_controls] ok');
