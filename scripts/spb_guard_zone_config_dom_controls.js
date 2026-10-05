#!/usr/bin/env node
const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_config_dom_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-config-dom-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneConfigDomControls = { install: install }',
  'function getConfigShell()',
  'function applyConfigShell(cfg)',
  'function restoreSpecMapUi(cfg)',
  '_restoreConfigSpecMapUi: restoreSpecMapUi'
].forEach((needle) => indexOf(mod, needle, moduleFile));

[
  'window.SPBZoneConfigDomControls.install',
  'const _getConfigShell = _zoneConfigDomControls',
  'const _applyConfigShell = _zoneConfigDomControls',
  'const _restoreConfigSpecMapUi = _zoneConfigDomControls',
  'const cfgShell = _getConfigShell()',
  '_applyConfigShell(cfg);',
  '_restoreConfigSpecMapUi(cfg);'
].forEach((needle) => indexOf(zones, needle, zonesFile));

[
  'const canonicalSourcePaintFile =',
  "if (cfg.driverName !== undefined)",
  "if (cfg.importedSpecMapPath) {"
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted config DOM shell ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} missing from ${manifestFile}`);
const sourceIndex = indexOf(html, 'js/zones/source-color-apply-controls.js', htmlFile);
const domIndex = indexOf(html, moduleFile, htmlFile);
const configIndex = indexOf(html, 'js/zones/zone-config-preset-controls.js', htmlFile);
const zonesIndex = indexOf(html, zonesFile, htmlFile);
assert(sourceIndex < domIndex, 'config DOM controls should load after source/apply controls');
assert(domIndex < configIndex, 'config DOM controls should load before config/preset controls');
assert(domIndex < zonesIndex, 'config DOM controls must load before the zone bridge');

console.log('[spb_guard_zone_config_dom_controls] OK');
