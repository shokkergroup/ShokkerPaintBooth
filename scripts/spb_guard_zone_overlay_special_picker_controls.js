const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_overlay_special_picker_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-overlay-special-picker-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneOverlaySpecialPickerControls = { install: install }',
  'function setOverlaySpecialPickerExpanded(zoneIndex, layer)',
  'function toggleOverlaySpecialPicker(zoneIndex, layer)',
  'global.setOverlaySpecialPickerExpanded = setOverlaySpecialPickerExpanded',
  'global.toggleOverlaySpecialPicker = toggleOverlaySpecialPicker'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneOverlaySpecialPickerControls.install',
  'renderZoneDetail: (index) => renderZoneDetail(index)',
  "setOverlaySpecialPickerExpanded(${i}, 'second')",
  "setOverlaySpecialPickerExpanded(${i}, 'third')",
  "setOverlaySpecialPickerExpanded(${i}, 'fourth')",
  "setOverlaySpecialPickerExpanded(${i}, 'fifth')"
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'let _overlaySpecialPickerExpanded',
  'function toggleOverlaySpecialPicker(',
  '_overlaySpecialPickerExpanded ='
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted overlay-special state ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const uiModeScript = indexOf(htmlSource, 'js/zones/zone-ui-mode-controls.js', htmlFile);
const overlayScript = indexOf(htmlSource, 'js/zones/zone-overlay-special-picker-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(uiModeScript < overlayScript, 'overlay-special module should load after UI mode controls');
assert(overlayScript < previewScript, 'overlay-special module must load before preview controls');
assert(overlayScript < zonesScript, 'overlay-special module must load before the zone monster script');

console.log('[spb_guard_zone_overlay_special_picker_controls] ok');
