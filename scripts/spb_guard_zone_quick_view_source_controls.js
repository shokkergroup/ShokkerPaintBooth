#!/usr/bin/env node

const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function fail(message) {
  console.error(message);
  process.exitCode = 1;
}

function requireIncludes(text, needle, label) {
  if (!text.includes(needle)) fail(`${label}: missing ${needle}`);
}

function requireAbsent(text, needle, label) {
  if (text.includes(needle)) fail(`${label}: stale inline code still contains ${needle}`);
}

const moduleFile = 'js/zones/zone-quick-view-source-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneQuickViewSourceControls = { install: install }',
  'function renderZoneQuickView()',
  'function zoneSpecSourceDisplayName(zone)',
  'function renderZoneSpecSourceSection(i, zone)'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'getZones: () => zones',
  'getSelectedZoneIndex: () => selectedZoneIndex',
  "getOverlayColors: () => (typeof ZONE_OVERLAY_COLORS !== 'undefined' ? ZONE_OVERLAY_COLORS : [])",
  "getMonolithics: () => (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : [])",
  "getBases: () => (typeof BASES !== 'undefined' ? BASES : [])",
  'getActiveImportedSpecMapPath: () => _getActiveImportedSpecMapPath()',
  'escapeHtml: (value) => escapeHtml(value)'
].forEach((needle) => requireIncludes(zonesSource, needle, zonesFile));

requireIncludes(zonesSource, 'window.SPBZoneQuickViewSourceControls.install({', zonesFile);

[
  'function renderZoneQuickView()',
  'function _zoneSpecSourceDisplayName(zone)',
  'function renderZoneSpecSourceSection(i, zone)',
  'const OVERLAY_COLORS =',
  'const globalAvailable = _getActiveImportedSpecMapPath();'
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-quick-view-source-controls.js');
const cardIndex = htmlSource.indexOf('js/zones/zone-card-render-controls.js');
const zonesIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-quick-view-source-controls script tag`);
if (moduleIndex >= cardIndex) fail(`${htmlFile}: zone-quick-view-source-controls should load before zone-card-render-controls`);
if (moduleIndex >= zonesIndex) fail(`${htmlFile}: zone-quick-view-source-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone quick-view/source controls guard passed.');
