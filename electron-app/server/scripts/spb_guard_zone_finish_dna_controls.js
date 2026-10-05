#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/finish-dna-controls.js');

const failures = [];
const functions = [
  '_extractZoneDNA',
  'copyZoneDNA',
  '_parseDNAString',
  'pasteZoneDNA',
  'handleDNAPaste',
];

if (!(html.indexOf('js/zones/finish-dna-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: finish DNA controls must load before zones installer');
}
if (!zones.includes('SPBZoneFinishDnaControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing finish DNA installer bridge');
}
for (const dep of ['getZones: () => zones', 'pushZoneUndo', 'renderZones', 'renderZoneDetail', 'triggerPreviewRender', 'showToast']) {
  if (!zones.includes(dep)) failures.push(`paint-booth-2-state-zones.js: finish DNA bridge missing ${dep}`);
}
if (!moduleSource.includes('global.SPBZoneFinishDnaControls = { install: install }')) {
  failures.push('finish DNA controls module: export missing');
}
if (!moduleSource.includes('var zones = getZones()')) {
  failures.push('finish DNA controls module: handlers must resolve zones through injected getter');
}
if (!moduleSource.includes('SHOKK:v1:')) {
  failures.push('finish DNA controls module: DNA prefix handling missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`function ${fn}(`) || !moduleSource.includes(`global.${fn} = ${fn}`)) {
    failures.push(`js/zones/finish-dna-controls.js: missing ${fn} install/export`);
  }
}

if (failures.length) {
  console.error('Zone finish DNA controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone finish DNA controls guard passed (extract/copy/parse/paste/input handlers extracted).');
