const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_config_preset_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-config-preset-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneConfigPresetControls = { install: install }',
  'function getSessionConfig()',
  'function applySessionConfig(cfg)',
  'function saveConfig()',
  'function exportPreset()',
  'function importPreset()',
  'function _applyPresetFromObject(preset)',
  'function loadConfig()',
  '_applyPresetFromObject: _applyPresetFromObject'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneConfigPresetControls.install',
  'setZones: (nextZones) => { zones = nextZones; }',
  'getConfig: () => getConfig()',
  'loadConfigFromObj: (cfg) => loadConfigFromObj(cfg)',
  'getRegistries: () => ({ bases: BASES, patterns: PATTERNS, monolithics: MONOLITHICS })'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function getSessionConfig() {',
  'function saveConfig() {',
  'function exportPreset() {',
  'function buildPresetDescription() {',
  'function importPreset() {',
  'function _applyPresetFromObject(preset) {',
  'function loadConfig() {'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted config/preset helper ${needle}`));

assert(zonesSource.includes('window._applyPresetFromObject'), 'applyPreset object branch must use extracted window._applyPresetFromObject');
assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const sourceScript = indexOf(htmlSource, 'js/zones/source-color-apply-controls.js', htmlFile);
const configScript = indexOf(htmlSource, 'js/zones/zone-config-preset-controls.js', htmlFile);
const autoRestoreScript = indexOf(htmlSource, 'js/zones/zone-auto-restore-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(sourceScript < configScript, 'config/preset module must load after source/apply controls');
assert(configScript < autoRestoreScript, 'config/preset module must load before auto-restore controls');
assert(configScript < zonesScript, 'config/preset module must load before the zone monster script');

console.log('[spb_guard_zone_config_preset_controls] ok');
