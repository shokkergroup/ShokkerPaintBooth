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

const moduleFile = 'js/zones/zone-detail-polish-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneDetailPolishControls = { install: install }',
  'function groupAdvancedOverlays(container)',
  'function celebrateZoneFinishChoice(zoneIndex)',
  'function enhanceFinishChoiceRows(container)',
  'function elevateChoiceSurfaces(container)',
  'function injectZoneHeartbeat(container, zoneIndex)',
  'function pulsePreviewFrame(state, duration)'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'document: document',
  'getZones: () => zones',
  'getSelectedZoneIndex: () => selectedZoneIndex',
  "getFinishType: (value) => (typeof getFinishType === 'function' ? getFinishType(value) : null)",
  "getMetadata: (value) => (typeof _getMetadata === 'function' ? _getMetadata(value) : null)"
].forEach((needle) => requireIncludes(zonesSource, needle, zonesFile));

requireIncludes(zonesSource, 'window.SPBZoneDetailPolishControls.install({', zonesFile);

[
  '// ===== OVERLAY STUDIO GROUPING (Run 22) =====',
  'function groupAdvancedOverlays(container)',
  'function celebrateZoneFinishChoice(zoneIndex)',
  'function enhanceFinishChoiceRows(container)',
  'function elevateChoiceSurfaces(container)',
  'function injectZoneHeartbeat(container, zoneIndex)',
  'function pulsePreviewFrame(state ='
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-detail-polish-controls.js');
const cardIndex = htmlSource.indexOf('js/zones/zone-card-render-controls.js');
const zonesIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-detail-polish-controls script tag`);
if (moduleIndex >= cardIndex) fail(`${htmlFile}: zone-detail-polish-controls should load before zone-card-render-controls`);
if (moduleIndex >= zonesIndex) fail(`${htmlFile}: zone-detail-polish-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone detail polish controls guard passed.');
