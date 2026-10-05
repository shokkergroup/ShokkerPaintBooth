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

const moduleFile = 'js/zones/zone-card-render-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneCardRenderControls = { install: install }',
  'function renderZoneCardHtml(zone, i)',
  'function zoneCardFinishName(zone)',
  'function zoneCardDot(zone)',
  'function regionBadgeHtml(zone)',
  'function swatchStripHtml(zone, dotColor)'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'getZones',
  'getSelectedZoneIndex',
  'getBulkSelectedZones',
  'getMonolithics',
  'getBases',
  'getPatterns',
  'getIntensityOptions',
  'getQuickColors',
  'getZoneStatusBadgeHTML',
  'getZoneDiagnostic',
  'escapeHtml'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

requireIncludes(zonesSource, 'window.SPBZoneCardRenderControls.install({', zonesFile);
requireIncludes(zonesSource, 'getZones: () => zones', zonesFile);
requireIncludes(zonesSource, 'getSelectedZoneIndex: () => selectedZoneIndex', zonesFile);
requireIncludes(zonesSource, "getBulkSelectedZones: () => (typeof _bulkSelectedZones !== 'undefined' ? _bulkSelectedZones : null)", zonesFile);
requireIncludes(zonesSource, "getMonolithics: () => (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : [])", zonesFile);
requireIncludes(zonesSource, "getBases: () => (typeof BASES !== 'undefined' ? BASES : [])", zonesFile);
requireIncludes(zonesSource, "getPatterns: () => (typeof PATTERNS !== 'undefined' ? PATTERNS : [])", zonesFile);
requireIncludes(zonesSource, "getIntensityOptions: () => (typeof INTENSITY_OPTIONS !== 'undefined' ? INTENSITY_OPTIONS : [])", zonesFile);
requireIncludes(zonesSource, "getQuickColors: () => (typeof QUICK_COLORS !== 'undefined' ? QUICK_COLORS : [])", zonesFile);
requireIncludes(zonesSource, 'html += renderZoneCardHtml(zone, i);', zonesFile);

[
  'const accordionClass =',
  'const summaryHtml = `<span class="zone-summary">',
  'let dotColor;',
  'const regionBadge = hasRegion',
  '<!-- Living visual strip: source colors + mini EKG'
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-card-render-controls.js');
const zonesIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-card-render-controls script tag`);
if (moduleIndex >= zonesIndex) fail(`${htmlFile}: zone-card-render-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone card render controls guard passed.');
