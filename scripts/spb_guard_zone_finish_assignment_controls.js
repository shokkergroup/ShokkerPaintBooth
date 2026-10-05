const fs = require('fs');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_finish_assignment_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(haystack, needle, label) {
  const index = haystack.indexOf(needle);
  assert(index >= 0, `${label} missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-finish-assignment-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = read(manifestFile);

[
  'global.SPBZoneFinishAssignmentControls = { install: install }',
  'function assignFinishToSelected(finishId)',
  'function applyPickedBaseToZone(zone, baseId)',
  'function applyPickedMonolithicToZone(zone, monoId)',
  'function maybeShowAlbedoHint(finishId, zone)',
  'global.assignFinishToSelected = assignFinishToSelected',
  'global._spbApplyPickedBaseToZone = applyPickedBaseToZone'
].forEach((needle) => indexOf(mod, needle, moduleFile));

[
  'window.SPBZoneFinishAssignmentControls.install',
  'const assignFinishToSelected = _zoneFinishAssignmentControls',
  'const _spbApplyPickedBaseToZone = _zoneFinishAssignmentControls',
  'window.assignFinishToSelected = assignFinishToSelected'
].forEach((needle) => indexOf(zones, needle, zonesFile));

[
  'function assignFinishToSelected(',
  'function _spbApplyPickedBaseToZone(',
  'function _spbApplyPickedMonolithicToZone(',
  'function _maybeShowAlbedoHint(',
  'const _ALBEDO_HINT_KEY'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted helper ${needle}`));

indexOf(manifest, moduleFile, manifestFile);
const toastIndex = indexOf(html, 'js/zones/zone-toast-notification-controls.js', htmlFile);
const finishIndex = indexOf(html, moduleFile, htmlFile);
const autosaveIndex = indexOf(html, 'js/zones/zone-autosave-controls.js', htmlFile);
const zonesIndex = indexOf(html, zonesFile, htmlFile);
assert(toastIndex < finishIndex, 'finish assignment controls must load after toast controls');
assert(finishIndex < autosaveIndex, 'finish assignment controls must load before autosave controls');
assert(autosaveIndex < zonesIndex, 'autosave controls must load before the zone monster bridge');

console.log('[spb_guard_zone_finish_assignment_controls] OK');
