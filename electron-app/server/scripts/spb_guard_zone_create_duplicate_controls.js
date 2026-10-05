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

const moduleFile = 'js/zones/zone-create-duplicate-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneCreateDuplicateControls = {',
  'function addZone(skipUndo)',
  'function duplicateZone(index)',
  'function applyFinishToAllZones()',
  'baseColorScale: 1',
  'fifthBaseSpecScale: 1.0'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'const MAX_ZONES = 50;',
  'window.SPBZoneCreateDuplicateControls.install({',
  'maxZones: MAX_ZONES',
  'newZoneId: () => _newZoneId()',
  'cloneZoneState: (zone, options) => _cloneZoneState(zone, options)',
  'addZone: (skipUndo) => window.addZone(skipUndo)',
  'duplicateZone: (index) => window.duplicateZone(index)',
  'applyFinishToAllZones: () => window.applyFinishToAllZones()'
].forEach((needle) => requireIncludes(zonesSource, needle, zonesFile));

[
  'function addZone(skipUndo) {',
  'if (typeof window !== \'undefined\') { window.addZone = addZone; }',
  'function duplicateZone(index) {',
  'function applyFinishToAllZones() {'
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-create-duplicate-controls.js');
const listActionIndex = htmlSource.indexOf('js/zones/zone-list-action-controls.js');
const cardIndex = htmlSource.indexOf('js/zones/zone-card-render-controls.js');
const zonesIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-create-duplicate-controls script tag`);
if (moduleIndex <= listActionIndex) fail(`${htmlFile}: zone-create-duplicate-controls should load after zone-list-action-controls`);
if (moduleIndex >= cardIndex) fail(`${htmlFile}: zone-create-duplicate-controls should load before zone-card-render-controls`);
if (moduleIndex >= zonesIndex) fail(`${htmlFile}: zone-create-duplicate-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone create/duplicate controls guard passed.');
