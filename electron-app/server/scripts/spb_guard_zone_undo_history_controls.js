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

const moduleFile = 'js/zones/zone-undo-history-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBZoneUndoHistoryControls = { install: install }',
  'function pushZoneUndo(label, isDrag)',
  'function undoZoneChange()',
  'function redoZoneChange()',
  'function jumpToUndoState(index)',
  'function renderUndoHistoryPanel()',
  'function toggleUndoHistoryPanel()',
  'function clearUndoHistory()',
  'function isTextEntryTargetForGlobalUndo(target)'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

[
  'getZones',
  'getSelectedZoneIndex',
  'setSelectedZoneIndex',
  'zoneUndoStack',
  'zoneRedoStack',
  'cloneZoneState',
  'ensureZoneShape',
  'cloneUint8ArrayLike',
  'clearAllRedos',
  'recordUndoAction',
  'getDrawUndoStack',
  'getDrawRedoStack'
].forEach((needle) => requireIncludes(moduleSource, needle, moduleFile));

requireIncludes(zonesSource, 'window.SPBZoneUndoHistoryControls.install({', zonesFile);
requireIncludes(zonesSource, 'document: document', zonesFile);
requireIncludes(zonesSource, 'zoneUndoStack: zoneUndoStack', zonesFile);
requireIncludes(zonesSource, 'zoneRedoStack: zoneRedoStack', zonesFile);
requireIncludes(zonesSource, 'cloneZoneState: _cloneZoneState', zonesFile);
requireIncludes(zonesSource, 'ensureZoneShape: _ensureZoneShape', zonesFile);
requireIncludes(zonesSource, 'cloneUint8ArrayLike: _cloneUint8ArrayLike', zonesFile);

[
  'let undoActiveDragTimer',
  'function pushZoneUndo(',
  'function undoZoneChange(',
  'function redoZoneChange(',
  'function jumpToUndoState(',
  'function renderUndoHistoryPanel(',
  'function toggleUndoHistoryPanel(',
  'function clearUndoHistory(',
  'function _isTextEntryTargetForGlobalUndo('
].forEach((needle) => requireAbsent(zonesSource, needle, zonesFile));

const moduleIndex = htmlSource.indexOf('js/zones/zone-undo-history-controls.js');
const zoneIndex = htmlSource.indexOf('paint-booth-2-state-zones.js');
if (moduleIndex < 0) fail(`${htmlFile}: missing zone-undo-history-controls script tag`);
if (moduleIndex >= zoneIndex) fail(`${htmlFile}: zone-undo-history-controls must load before paint-booth-2-state-zones.js`);

if (!process.exitCode) console.log('Zone undo history controls guard passed.');
