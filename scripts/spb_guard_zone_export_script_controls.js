#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/export-script-controls.js');

const failures = [];
const functions = [
  'exportJSON',
  'openModal',
  'closeModal',
  'copyScript',
  'saveScriptFile',
  'saveBatLauncher',
  'getAutoScriptName',
];

if (!(html.indexOf('js/zones/export-script-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: export/script controls must load before zones installer');
}
if (!zones.includes('SPBZoneExportScriptControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing export/script installer bridge');
}
if (!moduleSource.includes('window.SPBZoneExportScriptControls = { install }')) {
  failures.push('export/script controls module: export missing');
}
if (!moduleSource.includes('RUN_${baseName}.bat')) {
  failures.push('export/script controls module: robust BAT launcher filename logic missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`window.${fn} = function ${fn}`)) {
    failures.push(`js/zones/export-script-controls.js: missing ${fn} install`);
  }
}

if (failures.length) {
  console.error('Zone export/script controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone export/script controls guard passed (JSON export, modal, clipboard, Python save, BAT launcher, and auto-name extracted).');
