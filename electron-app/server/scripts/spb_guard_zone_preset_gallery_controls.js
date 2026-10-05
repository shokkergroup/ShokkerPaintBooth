#!/usr/bin/env node
const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_preset_gallery_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-preset-gallery-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZonePresetGalleryControls = { install: install }',
  'function toggleSection(id)',
  'function applyPreset(arg)',
  'function applyPresetById(presetId)',
  '_applyPresetFromObject',
  '_applyPresetById: applyPresetById'
].forEach((needle) => indexOf(mod, needle, moduleFile));

[
  'window.SPBZonePresetGalleryControls.install',
  'const toggleSection = _zonePresetGalleryControls',
  'const applyPreset = _zonePresetGalleryControls',
  'window.applyPreset = applyPreset',
  'window._applyPresetById = _applyPresetById'
].forEach((needle) => indexOf(zones, needle, zonesFile));

[
  'function toggleSection(id) {',
  'function applyPreset(arg) {',
  'function _applyPresetById(presetId) {'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted preset/gallery helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} missing from ${manifestFile}`);
const configIndex = indexOf(html, 'js/zones/zone-config-preset-controls.js', htmlFile);
const presetIndex = indexOf(html, moduleFile, htmlFile);
const zonesIndex = indexOf(html, zonesFile, htmlFile);
assert(configIndex < presetIndex, 'preset-gallery controls should load after config-preset controls');
assert(presetIndex < zonesIndex, 'preset-gallery controls must load before the zone bridge');

console.log('[spb_guard_zone_preset_gallery_controls] OK');
