const fs = require('fs');

function read(file) { return fs.readFileSync(file, 'utf8'); }
function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_state_shape_controls] ${message}`);
    process.exit(1);
  }
}
function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-state-shape-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';
const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneStateShapeControls = { install: install }',
  'function newZoneId()',
  'function cloneZoneState(zone, options)',
  'function ensureZoneShape(zone, options)',
  'function sanitizeZonesInPlace(zoneList, source)',
  'global._sanitizeZonesInPlace = sanitizeZonesInPlace'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneStateShapeControls.install',
  'const _newZoneId = _zoneStateShapeControls.newZoneId',
  'const _cloneZoneState = _zoneStateShapeControls.cloneZoneState',
  'const _sanitizeZonesInPlace = _zoneStateShapeControls.sanitizeZonesInPlace'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function _newZoneId(',
  'function _cloneUint8ArrayLike(',
  'function _cloneZoneState(',
  'function _ensureZoneShape(',
  'function _sanitizeZonesInPlace('
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted state-shape helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const renderChromeScript = indexOf(htmlSource, 'js/zones/zone-render-chrome-controls.js', htmlFile);
const stateShapeScript = indexOf(htmlSource, 'js/zones/zone-state-shape-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(renderChromeScript < stateShapeScript, 'state-shape module should load after render chrome controls');
assert(stateShapeScript < previewScript, 'state-shape module must load before preview controls');
assert(stateShapeScript < zonesScript, 'state-shape module must load before the zone monster script');

console.log('[spb_guard_zone_state_shape_controls] ok');
