#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/zone-data-repair-controls.js');

const failures = [];

if (!(html.indexOf('js/zones/zone-data-repair-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: zone data repair controls must load before zones installer');
}
if (!zones.includes('SPBZoneDataRepairControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing zone data repair installer bridge');
}
for (const dep of [
  'getZones: () => zones',
  'renderZones',
  'showToast',
  'getSpecPatternLayerDefaults: (pattern) => _getSpecPatternLayerDefaults(pattern)'
]) {
  if (!zones.includes(dep)) failures.push(`paint-booth-2-state-zones.js: zone data repair bridge missing ${dep}`);
}
if (!moduleSource.includes('global.SPBZoneDataRepairControls = { install: install }')) {
  failures.push('zone data repair controls module: export missing');
}
for (const api of [
  '_SPB_LEGACY_ID_MIGRATIONS',
  'global._migrateZoneFinishIds = _migrateZoneFinishIds',
  'global._normalizeLegacySpecPatternChannels = _normalizeLegacySpecPatternChannels',
  'global.repairZoneData = repairZoneData'
]) {
  if (!moduleSource.includes(api)) failures.push(`zone data repair controls module: missing ${api}`);
}
for (const fn of ['_migrateZoneFinishIds', '_normalizeLegacySpecPatternChannels', 'repairZoneData']) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`function ${fn}(`)) failures.push(`js/zones/zone-data-repair-controls.js: missing ${fn}`);
}
if (!moduleSource.includes('var defaults = getSpecPatternLayerDefaults(entry.pattern)')) {
  failures.push('zone data repair controls module: spec channel defaults must use injected resolver');
}
if (!moduleSource.includes('var zones = getZones()')) {
  failures.push('zone data repair controls module: repairZoneData must use injected zone getter');
}
if (!moduleSource.includes('setTimeout(function()')) {
  failures.push('zone data repair controls module: auto-repair timer missing');
}

if (failures.length) {
  console.error('Zone data repair controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone data repair controls guard passed (legacy migration and zone repair island extracted).');
