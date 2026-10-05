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

const moduleFile = 'js/zones/zone-link-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneLinkControls = { install: install }',
  'LINK_FINISH_PROPS',
  'function linkZones(indices)',
  'function unlinkZone(index)',
  'function linkSelectedToZone(targetIndex)',
  'function propagateToLinkedZones(sourceIndex, props)',
  'function promptLinkZone(index)'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'getZones',
  'getSelectedZoneIndex',
  'allocateLinkGroupId',
  'pushZoneUndo',
  'renderZones',
  'showToast',
  'triggerPreviewRender',
  'promptUser'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

requireIncludes(zonesSource, 'window.SPBZoneLinkControls.install({', zonesFile);
requireIncludes(zonesSource, "allocateLinkGroupId: () => 'link_' + (nextLinkGroupId++)", zonesFile);
requireIncludes(zonesSource, 'pushZoneUndo: (label) => pushZoneUndo(label)', zonesFile);
requireIncludes(zonesSource, 'renderZones: () => renderZones()', zonesFile);
requireIncludes(zonesSource, 'showToast: (message, isError, details) => showToast(message, isError, details)', zonesFile);
requireIncludes(zonesSource, "triggerPreviewRender: () => (typeof triggerPreviewRender === 'function' ? triggerPreviewRender() : null)", zonesFile);
requireIncludes(zonesSource, "promptUser: (message) => (typeof window.prompt === 'function' ? window.prompt(message) : null)", zonesFile);

[
  'const LINK_FINISH_PROPS =',
  'function linkZones(',
  'function unlinkZone(',
  'function linkSelectedToZone(',
  'function propagateToLinkedZones(',
  'function promptLinkZone('
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-link-controls.js');
const zonesIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-link-controls script tag`);
if (moduleIndex >= zonesIndex) fail(`${htmlFile}: zone-link-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone link controls guard passed.');
