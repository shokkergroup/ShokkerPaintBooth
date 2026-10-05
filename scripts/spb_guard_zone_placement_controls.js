const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_placement_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-placement-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZonePlacementControls = { install: install }',
  'function setPlacementLayer(layer)',
  'function getPlacementMode(zone, target)',
  'function renderPlacementModeControls(index, target, options)',
  'function applyPlacementPatternTransform()',
  'function updatePlacementBanner()',
  'function setupPlacementOverlayDrag()',
  'function stepZoneSecondBasePatternOffset(index, axis, delta)',
  'function stepZoneNthBasePatternOffset(index, nth, axis, delta)',
  'function stepZoneBaseOffset(index, axis, delta)',
  'function setZoneSecondBasePatternOffsetX(index, value)',
  'function setZoneFifthBasePatternOffsetY(index, value)'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZonePlacementControls.install',
  'getPlacementLayer: () => placementLayer',
  'setPlacementLayerValue: (value) => { placementLayer = value; }',
  'activateManualPlacement: (index, target) => (typeof activateManualPlacement === \'function\' ? activateManualPlacement(index, target) : null)',
  'deactivateManualPlacement: () => (typeof deactivateManualPlacement === \'function\' ? deactivateManualPlacement() : null)'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function _isPlacementLayerTarget(layer) {',
  'function setPlacementLayer(layer) {',
  'function renderPlacementModeControls(index, target, options) {',
  'function applyPlacementPatternTransform() {',
  'function updatePlacementBanner() {',
  'function setupPlacementOverlayDrag() {',
  'function stepZoneSecondBasePatternOffset(index, axis, delta) {',
  'function stepZoneNthBasePatternOffset(index, nth, axis, delta) {',
  'function stepZoneBaseOffset(index, axis, delta) {'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted placement helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const overlayHsbScript = indexOf(htmlSource, 'js/zones/zone-base-overlay-hsb-controls.js', htmlFile);
const placementScript = indexOf(htmlSource, 'js/zones/zone-placement-controls.js', htmlFile);
const legacyScript = indexOf(htmlSource, 'js/zones/legacy-zone-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(overlayHsbScript < placementScript, 'placement module must load after overlay HSB controls');
assert(placementScript < legacyScript, 'placement module must load before legacy controls');
assert(placementScript < zonesScript, 'placement module must load before the zone monster script');

console.log('[spb_guard_zone_placement_controls] ok');
