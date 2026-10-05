#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/spec-map-controls.js');

const failures = [];
const functions = [
  'importSpecMapFromFile',
  'importSpecMapFromDrop',
  'clearImportedSpecMap',
  'importZoneSpecMapFromFile',
  'copyImportedSpecMapToZone',
  'clearZoneSpecMap',
  'setZoneSpecMapStrength',
  'stepZoneSpecMapStrength',
];

if (!(html.indexOf('js/zones/spec-map-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: spec map controls must load before zones installer');
}
if (!zones.includes('SPBZoneSpecMapControls.install')) failures.push('paint-booth-2-state-zones.js: missing spec map installer bridge');
if (!zones.includes('getActiveImportedSpecMapPath: _getActiveImportedSpecMapPath')) failures.push('paint-booth-2-state-zones.js: missing imported spec getter dep');
if (!zones.includes('setImportedSpecMapPath: (path) =>')) failures.push('paint-booth-2-state-zones.js: missing imported spec setter dep');
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  const directWindowInstall = moduleSource.includes(`window.${fn} = function ${fn}`);
  const namedFunctionExport = moduleSource.includes(`function ${fn}(`) && moduleSource.includes(`window.${fn} = ${fn}`);
  if (!directWindowInstall && !namedFunctionExport) failures.push(`js/zones/spec-map-controls.js: missing ${fn} install`);
}
if (!moduleSource.includes('window._getActiveImportedSpecMapPath = getActiveImportedSpecMapPath')) failures.push('spec map controls module: imported spec getter export missing');
if (!moduleSource.includes('window.clearImportedSpec = clearImportedSpecMap')) failures.push('spec map controls module: legacy clearImportedSpec alias missing');
if (zones.includes('function clearImportedSpecMap(')) failures.push('paint-booth-2-state-zones.js: clearImportedSpecMap still lives in monster file');
if (zones.includes('function clearImportedSpec(')) failures.push('paint-booth-2-state-zones.js: legacy clearImportedSpec duplicate still lives in monster file');
if (!moduleSource.includes('window.SPBZoneSpecMapControls = { install }')) failures.push('spec map controls module: export missing');
if (!moduleSource.includes('/upload-spec-map')) failures.push('spec map controls module: upload endpoint missing');

if (failures.length) {
  console.error('Zone spec map controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone spec map controls guard passed (global and zone spec-map handlers extracted).');
