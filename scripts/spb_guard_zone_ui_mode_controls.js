const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_ui_mode_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-ui-mode-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneUiModeControls = { install: install }',
  'function toggleUIMode()',
  'function setUIScale(direction)',
  'global.toggleEasyMode = toggleUIMode',
  'global.setUIScale = setUIScale'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneUiModeControls.install',
  'requestAnimationFrame: requestAnimationFrame',
  'renderZones: () => renderZones()'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'let _uiMode =',
  'window.toggleUIMode = function',
  'let _uiScale =',
  'window.setUIScale = function'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted UI mode helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const thumbnailScript = indexOf(htmlSource, 'js/zones/zone-thumbnail-controls.js', htmlFile);
const uiModeScript = indexOf(htmlSource, 'js/zones/zone-ui-mode-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(thumbnailScript < uiModeScript, 'ui-mode module must load after thumbnail controls');
assert(uiModeScript < previewScript, 'ui-mode module must load before preview controls');
assert(uiModeScript < zonesScript, 'ui-mode module must load before the zone monster script');

console.log('[spb_guard_zone_ui_mode_controls] ok');
