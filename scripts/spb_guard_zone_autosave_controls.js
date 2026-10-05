const fs = require('fs');

function read(file) { return fs.readFileSync(file, 'utf8'); }
function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_autosave_controls] ${message}`);
    process.exit(1);
  }
}
function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-autosave-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';
const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneAutosaveControls = { install: install }',
  'function autoSave()',
  'function flushAutoSave()',
  'function writeConfigNow(silentQuota)',
  'global.autoSave = autoSave',
  'global.flushAutoSave = flushAutoSave'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneAutosaveControls.install',
  'const AUTOSAVE_KEY = _zoneAutosaveControls ? _zoneAutosaveControls.autosaveKey',
  'const autoSave = _zoneAutosaveControls ? _zoneAutosaveControls.autoSave',
  'const flushAutoSave = _zoneAutosaveControls ? _zoneAutosaveControls.flushAutoSave',
  'getAutosaveKey: () => AUTOSAVE_KEY'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function autoSave(',
  'function flushAutoSave(',
  'let autosaveTimer =',
  'let _autosavePendingChanges =',
  'Periodic auto-save every 60 seconds'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted autosave helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const stateShapeScript = indexOf(htmlSource, 'js/zones/zone-state-shape-controls.js', htmlFile);
const autosaveScript = indexOf(htmlSource, 'js/zones/zone-autosave-controls.js', htmlFile);
const autoRestoreScript = indexOf(htmlSource, 'js/zones/zone-auto-restore-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(stateShapeScript < autosaveScript, 'autosave module should load after state-shape controls');
assert(autosaveScript < autoRestoreScript, 'autosave module must load before auto-restore controls');
assert(autosaveScript < zonesScript, 'autosave module must load before the zone monster script');

console.log('[spb_guard_zone_autosave_controls] ok');
