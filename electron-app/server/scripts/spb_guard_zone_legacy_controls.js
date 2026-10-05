#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const legacyModule = read('js/zones/legacy-zone-controls.js');

const failures = [];
const functions = [
  'setZoneCCQuality',
  'resetZoneCCQuality',
  'setZoneBlendBase',
  'setZoneBlendDir',
  'setZoneBlendAmount',
  'setZonePaintReactiveColor',
  'setZoneUsePaintReactive',
];

if (!(html.indexOf('js/zones/legacy-zone-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: legacy zone controls must load before zones installer');
}
if (!zones.includes('SPBZoneLegacyControls.install')) failures.push('paint-booth-2-state-zones.js: missing legacy controls installer bridge');
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!legacyModule.includes(`window.${fn} = function ${fn}`)) failures.push(`js/zones/legacy-zone-controls.js: missing ${fn} install`);
}
if (!legacyModule.includes('window.SPBZoneLegacyControls = { install }')) failures.push('legacy zone controls module: export missing');

if (failures.length) {
  console.error('Zone legacy controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone legacy controls guard passed (legacy v6 setters extracted).');
