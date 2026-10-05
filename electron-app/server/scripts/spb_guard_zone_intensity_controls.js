const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_intensity_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-intensity-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneIntensityControls = { install: install }',
  'function setZoneFinish(index, finishId)',
  'function setZoneIntensity(index, intensity, fromSlider)',
  'function tickZoneIntensity(index, delta)',
  'function setZonePatternIntensity(index, value)',
  'function getIntensityMultiplier(zone)',
  'function setCustomIntensity(index, param, value)',
  'function toggleIntensitySliders(index)',
  'global.setZoneFinish = setZoneFinish',
  'global.toggleIntensitySliders = toggleIntensitySliders'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneIntensityControls.install',
  'getIntensityValues: () => INTENSITY_VALUES',
  'propagateToLinkedZones: (index, fields) => propagateToLinkedZones(index, fields)',
  'pushZoneUndoCoalesced: (label, windowMs) => pushZoneUndoCoalesced(label, windowMs)',
  'autoSave: () => (typeof autoSave === \'function\' ? autoSave() : null)'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function setZoneFinish(index, finishId) {',
  'function setZoneIntensity(index, intensity, fromSlider) {',
  'function tickZoneIntensity(index, delta) {',
  'function setZonePatternIntensity(index, value) {',
  'function getIntensityMultiplier(zone) {',
  'function setCustomIntensity(index, param, value) {',
  'function toggleIntensitySliders(index) {'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted intensity helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const placementScript = indexOf(htmlSource, 'js/zones/zone-placement-controls.js', htmlFile);
const intensityScript = indexOf(htmlSource, 'js/zones/zone-intensity-controls.js', htmlFile);
const legacyScript = indexOf(htmlSource, 'js/zones/legacy-zone-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(placementScript < intensityScript, 'intensity module must load after placement controls');
assert(intensityScript < legacyScript, 'intensity module must load before legacy controls');
assert(intensityScript < zonesScript, 'intensity module must load before the zone monster script');

console.log('[spb_guard_zone_intensity_controls] ok');
