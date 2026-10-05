#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/preview-controls.js');

const failures = [];

if (!(html.indexOf('js/zones/preview-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: preview controls must load before zones installer');
}
if (!zones.includes('SPBZonePreviewControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing preview controls installer bridge');
}
for (const dep of ['showToast', 'validatePaintPath', 'isTextEntryTarget: _isTextEntryTargetForGlobalUndo']) {
  if (!zones.includes(dep)) failures.push(`paint-booth-2-state-zones.js: preview bridge missing ${dep}`);
}
if (!zones.includes("activeSpecChannel: (typeof window !== 'undefined' && window.activeSpecChannel) || 'all'")) {
  failures.push('paint-booth-2-state-zones.js: getConfig must read extracted activeSpecChannel mirror');
}
if (!moduleSource.includes('global.SPBZonePreviewControls = { install: install }')) {
  failures.push('preview controls module: export missing');
}
for (const api of [
  'global.addRecentPath = addRecentPath',
  'global.showRecentPaths = showRecentPaths',
  'global.setSpecChannel = setSpecChannel',
  'global.openSpecMapInspector = openSpecMapInspector',
  'global.captureBeforeImage = captureBeforeImage',
  'global.toggleBeforeAfter = toggleBeforeAfter'
]) {
  if (!moduleSource.includes(api)) failures.push(`preview controls module: missing ${api}`);
}
for (const marker of [
  'RECENT_PATHS_KEY',
  'livePreviewSpecImg',
  'specMapInspectorModal',
  'beforeAfterActive',
  'beforeImageCaptured',
  'hookSpecImageLoad'
]) {
  if (!moduleSource.includes(marker)) failures.push(`preview controls module: missing ${marker}`);
}
for (const fn of [
  'getRecentPaths',
  'addRecentPath',
  'showRecentPaths',
  'toggleSpecInset',
  'setSpecChannel',
  'openSpecMapInspector',
  'captureBeforeImage',
  'toggleBeforeAfter'
]) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
}
for (const oldMarker of [
  'RECENT PAINT PATHS',
  'LIVE PREVIEW (PAINT + SPEC INSET)',
  'SPEC MAP INSPECTOR',
  'BEFORE/AFTER COMPARISON'
]) {
  if (zones.includes(oldMarker)) failures.push(`paint-booth-2-state-zones.js: old preview marker still lives in monster file: ${oldMarker}`);
}

if (failures.length) {
  console.error('Zone preview controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone preview controls guard passed (recent paths, spec preview, inspector, before/after extracted).');
