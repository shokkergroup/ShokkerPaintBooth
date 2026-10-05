const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_base_overlay_hsb_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-base-overlay-hsb-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneBaseOverlayHsbControls = {',
  'const OVERLAY_BASE_HSB_FIELDS = {',
  'function setZoneOverlayBaseHsb(index, layer, kind, val, ev)',
  'function stepZoneOverlayBaseHsb(index, layer, kind, direction, ev)',
  'function commitZoneOverlayBaseHsb(index, ev)',
  'function stopOverlayBaseHsbPointer(ev)',
  'global.setZoneOverlayBaseHsb = setZoneOverlayBaseHsb',
  'global.stepZoneOverlayBaseHsb = stepZoneOverlayBaseHsb',
  'global.commitZoneOverlayBaseHsb = commitZoneOverlayBaseHsb',
  'global.stopOverlayBaseHsbPointer = stopOverlayBaseHsbPointer'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneBaseOverlayHsbControls.install',
  'getZones: () => zones',
  'renderZones: () => renderZones()',
  'triggerPreviewRender: () => (typeof triggerPreviewRender === \'function\' ? triggerPreviewRender() : null)'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'const OVERLAY_BASE_HSB_FIELDS = {',
  'function _formatOverlayBaseHsbValue(kind, val) {',
  'function _overlayBaseHsbClamp(kind, val) {',
  'function _updateOverlayBaseHsbLabel(ev, kind, val) {',
  'function setZoneOverlayBaseHsb(index, layer, kind, val, ev) {',
  'function stepZoneOverlayBaseHsb(index, layer, kind, direction, ev) {',
  'function commitZoneOverlayBaseHsb(index, ev) {',
  'function stopOverlayBaseHsbPointer(ev) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const baseOverlayScript = indexOf(htmlSource, 'js/zones/base-overlay-controls.js', htmlFile);
const overlayHsbScript = indexOf(htmlSource, 'js/zones/zone-base-overlay-hsb-controls.js', htmlFile);
const legacyScript = indexOf(htmlSource, 'js/zones/legacy-zone-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(baseOverlayScript < overlayHsbScript, 'overlay HSB module must load after base-overlay controls');
assert(overlayHsbScript < legacyScript, 'overlay HSB module must load before legacy controls');
assert(overlayHsbScript < zonesScript, 'overlay HSB module must load before the zone monster script');

console.log('[spb_guard_zone_base_overlay_hsb_controls] ok');
