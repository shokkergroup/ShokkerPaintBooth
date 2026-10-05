#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/fine-tuning-controls.js');

const failures = [];
const functions = [
  'openFineTuning',
  'closeFineTuning',
  'toggleFineTuningSection',
  '_retargetFineTuningCloneIds',
  '_buildFineTuningContent',
  '_refreshFineTuningIfOpen',
];

if (!(html.indexOf('js/zones/fine-tuning-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: fine-tuning controls must load before zones installer');
}
if (!zones.includes('SPBZoneFineTuningControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing fine-tuning installer bridge');
}
if (!zones.includes('getSelectedZoneIndex: () => selectedZoneIndex')) {
  failures.push('paint-booth-2-state-zones.js: fine-tuning bridge must inject selected zone getter');
}
if (!zones.includes('getOverlayBaseDisplay')) {
  failures.push('paint-booth-2-state-zones.js: fine-tuning bridge must inject overlay display resolver');
}
if (!moduleSource.includes('global.SPBZoneFineTuningControls = { install: install }')) {
  failures.push('fine-tuning controls module: export missing');
}
if (!moduleSource.includes('global._fineTuningOpen = false') || !moduleSource.includes('global._fineTuningZone = -1')) {
  failures.push('fine-tuning controls module: state initialization missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`global.${fn} = function ${fn}`)) {
    failures.push(`js/zones/fine-tuning-controls.js: missing ${fn} install`);
  }
}

if (failures.length) {
  console.error('Zone fine-tuning controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone fine-tuning controls guard passed (open/close/toggle/build/refresh panel island extracted).');
