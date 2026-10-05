#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/zone-keyboard-controls.js');

const failures = [];

if (!(html.indexOf('js/zones/zone-keyboard-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: zone keyboard controls must load before zones installer');
}
if (!zones.includes('SPBZoneKeyboardControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing zone keyboard installer bridge');
}
for (const dep of [
  'isTextEntryTarget: _isTextEntryTargetForGlobalUndo',
  'getSelectedZoneIndex: () => selectedZoneIndex',
  'getLassoPoints: () =>',
  'setLassoPoints: (points) =>',
  'closeModal'
]) {
  if (!zones.includes(dep)) failures.push(`paint-booth-2-state-zones.js: zone keyboard bridge missing ${dep}`);
}
if (!moduleSource.includes('global.SPBZoneKeyboardControls = { install: install }')) {
  failures.push('zone keyboard controls module: export missing');
}
for (const marker of [
  "e.key === 'n'",
  "e.key === 'm'",
  "e.key === 'Delete'",
  "e.key === 'Backspace'",
  "e.key === 'Escape'",
  'finishCompareOverlay',
  'finishBrowserOverlay',
  'presetGalleryOverlay'
]) {
  if (!moduleSource.includes(marker)) failures.push(`zone keyboard controls module: missing ${marker}`);
}
for (const oldMarker of [
  'IMPROVEMENT 48: keyboard shortcut',
  'Removed last vertex'
]) {
  if (zones.includes(oldMarker)) failures.push(`paint-booth-2-state-zones.js: keyboard shortcut marker still lives in monster file: ${oldMarker}`);
}

if (failures.length) {
  console.error('Zone keyboard controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone keyboard controls guard passed (zone/lasso/modal shortcut island extracted).');
