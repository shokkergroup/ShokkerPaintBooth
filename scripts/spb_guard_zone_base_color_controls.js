const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_base_color_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-base-color-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneBaseColorControls = {',
  'function setZoneBaseColorMode(index, value)',
  'function normalizeBaseGradientStopsForPayload(stops)',
  'function _buildGradientEditorHTML(zoneIdx, zone)',
  'function setGradientStopColor(zoneIdx, stopIdx, color)',
  'function setZoneBaseColor(index, val)',
  'function setZoneBaseColorSource(index, val)',
  'function setZoneBaseHueOffset(index, val)',
  'global.setZoneBaseColorMode = setZoneBaseColorMode',
  'global.normalizeBaseGradientStopsForPayload = normalizeBaseGradientStopsForPayload',
  'global._buildGradientEditorHTML = _buildGradientEditorHTML',
  'global.setZoneBaseColorSource = setZoneBaseColorSource'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneBaseColorControls.install',
  'getZones: () => zones',
  'renderZoneDetail: (zoneIndex) => renderZoneDetail(zoneIndex)',
  'triggerPreviewRender: () => (typeof triggerPreviewRender === \'function\' ? triggerPreviewRender() : null)'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function setZoneBaseColorMode(index, value) {',
  'function normalizeBaseGradientStopsForPayload(stops) {',
  'function _buildGradientEditorHTML(zoneIdx, zone) {',
  'function setGradientStopColor(zoneIdx, stopIdx, color) {',
  'function setZoneBaseColor(index, val) {',
  'function setZoneBaseColorSource(index, val) {',
  'function setZoneBaseHueOffset(index, val) {',
  'function setZoneBaseSaturation(index, val) {',
  'function setZoneBaseBrightness(index, val) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const baseMaterialScript = indexOf(htmlSource, 'js/zones/base-material-controls.js', htmlFile);
const baseColorScript = indexOf(htmlSource, 'js/zones/zone-base-color-controls.js', htmlFile);
const patternTransformScript = indexOf(htmlSource, 'js/zones/pattern-transform-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(baseMaterialScript < baseColorScript, 'base color module must load after base material controls');
assert(baseColorScript < patternTransformScript, 'base color module must load before pattern controls');
assert(baseColorScript < zonesScript, 'base color module must load before the zone monster script');

console.log('[spb_guard_zone_base_color_controls] ok');
