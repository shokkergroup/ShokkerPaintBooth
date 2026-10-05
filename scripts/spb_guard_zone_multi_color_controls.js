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

const moduleFile = 'js/zones/zone-multi-color-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneMultiColorControls = { install: install }',
  'function getColorStatusText(zone)',
  'function renderMultiColorChips(zone, zoneIndex)',
  'function addColorToZoneFromPicker(zoneIndex)',
  'function removeColorFromZone(zoneIndex, colorIndex)',
  'function updateColorTolerance(zoneIndex, colorIndex, value)',
  'function clearZoneColors(zoneIndex)'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'getZones',
  'getLastEyedropperColor',
  'pushZoneUndo',
  'renderZones',
  'triggerPreviewRender',
  'showToast',
  'escapeHtml'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

requireIncludes(zonesSource, 'window.SPBZoneMultiColorControls.install({', zonesFile);
requireIncludes(zonesSource, 'document: document', zonesFile);
requireIncludes(zonesSource, 'getZones: () => zones', zonesFile);
requireIncludes(zonesSource, "getLastEyedropperColor: () => (typeof lastEyedropperColor !== 'undefined' ? lastEyedropperColor : null)", zonesFile);
requireIncludes(zonesSource, 'pushZoneUndo: (label, isDrag) => pushZoneUndo(label, isDrag)', zonesFile);
requireIncludes(zonesSource, 'triggerPreviewRender: () => { if (typeof triggerPreviewRender === \'function\') triggerPreviewRender(); }', zonesFile);
requireIncludes(zonesSource, 'escapeHtml: (value) => escapeHtml(value)', zonesFile);

[
  'function getColorStatusText(',
  'function renderMultiColorChips(',
  'function addColorToZoneFromPicker(',
  'function removeColorFromZone(',
  'function updateColorTolerance(',
  'function clearZoneColors('
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-multi-color-controls.js');
const zonesIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-multi-color-controls script tag`);
if (moduleIndex >= zonesIndex) fail(`${htmlFile}: zone-multi-color-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone multi-color controls guard passed.');
