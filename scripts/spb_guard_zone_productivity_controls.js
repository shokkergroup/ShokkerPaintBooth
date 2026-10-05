#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/productivity-controls.js');

const failures = [];
const functions = [
  'toggleLock',
  'zoneCoverageEstimate',
  'toggleBulkSelect',
  'clearBulkSelection',
  'bulkSelectAll',
  'bulkApplyFinish',
  'bulkSetIntensity',
  'bulkSetTolerance',
  'bulkMute',
  'bulkUnmute',
  'bulkDelete',
  'saveZonePreset',
  'loadZonePreset',
  'deleteZonePreset',
  'listZonePresets',
  'duplicateZoneWithHueOffset',
  'propagateIntensityToLinked',
  'unlinkAllZones',
  'copyZoneToClipboard',
  'pasteZoneFromClipboard',
  'pasteZoneAsNew',
  'exportSingleZone',
  'importZoneFromFile',
  'setZoneSearchQuery',
  'clearZoneSearch',
  'collapseAllZones',
  'expandAllZones',
  'suggestZoneName',
  'autoNameZone',
  'autoNameAllZones',
  'setTolerancePreset',
  'renumberZones',
];

if (!(html.indexOf('js/zones/productivity-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: productivity controls must load before zones installer');
}
if (!zones.includes('SPBZoneProductivityControls.install')) failures.push('paint-booth-2-state-zones.js: missing productivity installer bridge');
if (!zones.includes('var _bulkSelectedZones')) failures.push('paint-booth-2-state-zones.js: missing bulk selection bridge for renderZones');
if (!zones.includes('var _zoneSearchQuery')) failures.push('paint-booth-2-state-zones.js: missing search query bridge for renderZones');
if (!moduleSource.includes('window.SPBZoneProductivityControls = { install, selection: bulkSelectedZones, state }')) {
  failures.push('productivity controls module: export missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`window.${fn} = function ${fn}`)) failures.push(`js/zones/productivity-controls.js: missing ${fn} install`);
}

if (failures.length) {
  console.error('Zone productivity controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone productivity controls guard passed (bulk, preset, copy/paste, search, naming, and tolerance controls extracted).');
