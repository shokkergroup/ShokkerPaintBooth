#!/usr/bin/env node
const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_config_zone_map_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-config-zone-map-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneConfigZoneMapControls = { install: install }',
  'function serializeZones(zones)',
  'function hydrateZones(cfgZones)',
  '_serializeConfigZones: serializeZones',
  '_hydrateConfigZones: hydrateZones'
].forEach((needle) => indexOf(mod, needle, moduleFile));

[
  'window.SPBZoneConfigZoneMapControls.install',
  'const _serializeConfigZones = _zoneConfigZoneMapControls',
  'const _hydrateConfigZones = _zoneConfigZoneMapControls',
  'zones: _serializeConfigZones(zones)',
  'zones = _hydrateConfigZones(cfg.zones);'
].forEach((needle) => indexOf(zones, needle, zonesFile));

[
  'zones: zones.map(z => ({',
  'zones = cfg.zones.map(z => ({',
  'patternStrengthMap: (z.patternStrengthMap && z.patternStrengthMap.data) ?'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted config zone map ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} missing from ${manifestFile}`);
const sourceIndex = indexOf(html, 'js/zones/source-color-apply-controls.js', htmlFile);
const mapIndex = indexOf(html, moduleFile, htmlFile);
const domIndex = indexOf(html, 'js/zones/zone-config-dom-controls.js', htmlFile);
const zonesIndex = indexOf(html, zonesFile, htmlFile);
assert(sourceIndex < mapIndex, 'config zone-map controls should load after source/apply controls');
assert(mapIndex < domIndex, 'config zone-map controls should load before config DOM controls');
assert(mapIndex < zonesIndex, 'config zone-map controls must load before the zone bridge');

console.log('[spb_guard_zone_config_zone_map_controls] OK');
