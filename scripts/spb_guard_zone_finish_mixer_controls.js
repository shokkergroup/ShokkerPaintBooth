#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/finish-mixer-controls.js');

const failures = [];
const functions = [
  'openFinishMixer',
  'closeMixerPanel',
  '_mixerSlotChange',
  '_mixerWeightChange',
  '_mixerAddSlot',
  '_mixerRemoveSlot',
  '_mixerOpenPicker',
  '_mixerClosePicker',
  '_mixerFilterBases',
  '_mixerSetCategory',
  '_renderMixerBasePicker',
  '_mixerPreview',
  '_mixerApplyDirect',
  '_mixerSave',
  '_mixerDeleteCustom',
  '_renderMixerPanel',
  '_loadCustomFinishes',
];

if (!(html.indexOf('js/zones/finish-mixer-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: finish mixer controls must load before zones installer');
}
if (!zones.includes('SPBZoneFinishMixerControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing finish mixer installer bridge');
}
for (const dep of ['getZones: () => zones', 'showToast', 'updateZonePanel']) {
  if (!zones.includes(dep)) failures.push(`paint-booth-2-state-zones.js: finish mixer bridge missing ${dep}`);
}
if (!moduleSource.includes('global.SPBZoneFinishMixerControls = { install: install }')) {
  failures.push('finish mixer controls module: export missing');
}
for (const endpoint of ['/api/mix-paint-preview', '/api/save-custom-finish', '/api/delete-custom-finish', '/api/custom-finishes']) {
  if (!moduleSource.includes(endpoint)) failures.push(`finish mixer controls module: missing ${endpoint}`);
}
if (!moduleSource.includes('global._mixerState = _mixerState') || !moduleSource.includes('global._customMixFinishes = _customMixFinishes')) {
  failures.push('finish mixer controls module: inline handler compatibility globals missing');
}
if (!moduleSource.includes('var zones = getZones()')) {
  failures.push('finish mixer controls module: zone mutations/lookups must use injected getter');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`function ${fn}(`) || !moduleSource.includes(`global.${fn} = ${fn}`)) {
    failures.push(`js/zones/finish-mixer-controls.js: missing ${fn} install/export`);
  }
}

if (failures.length) {
  console.error('Zone finish mixer controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone finish mixer controls guard passed (mixer UI/API/custom loader island extracted).');
