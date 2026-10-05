#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/source-color-apply-controls.js');

const failures = [];

if (!(html.indexOf('js/zones/source-color-apply-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: source/color/apply controls must load before zones installer');
}
if (!zones.includes('SPBZoneSourceColorApplyControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing source/color/apply installer bridge');
}
for (const dep of [
  'getZones: () => zones',
  'setSelectedZoneIndex: (index) => { selectedZoneIndex = index; }',
  'pushZoneUndo',
  'renderZoneDetail',
  'getPsdLayers: () =>',
  'setCanvasMode: (mode) =>',
  'getPaintCanvas: () => paintCanvas'
]) {
  if (!zones.includes(dep)) failures.push(`paint-booth-2-state-zones.js: source/color/apply bridge missing ${dep}`);
}
if (!zones.includes('setHexColor: window.setHexColor')) {
  failures.push('paint-booth-2-state-zones.js: workflow bridge must use extracted window.setHexColor');
}
if (!moduleSource.includes('global.SPBZoneSourceColorApplyControls = { install: install }')) {
  failures.push('source/color/apply controls module: export missing');
}
for (const api of [
  '_defaultZoneHardEdge',
  'buildZoneReactToLayerHtml',
  'setZoneHardEdge',
  'refreshZoneDetailIfOpen',
  'setZoneSourceLayer',
  'setQuickColor',
  'setSpecialColor',
  'setTextColor',
  'setPickerColor',
  'setPickerTolerance',
  'setHexColor',
  '_zoneShouldFitIntoApplyArea',
  'getZoneColorFilterRgb',
  'startZoneApplyAreaDraw',
  'autoActivateZoneApplyArea',
  'buildZoneApplyAreaSection'
]) {
  if (!moduleSource.includes(api)) failures.push(`source/color/apply controls module: missing ${api}`);
}
for (const fn of [
  '_defaultZoneHardEdge',
  'buildZoneReactToLayerHtml',
  'setZoneHardEdge',
  'refreshZoneDetailIfOpen',
  'setZoneSourceLayer',
  'setQuickColor',
  'setSpecialColor',
  'setTextColor',
  'setPickerColor',
  'setPickerTolerance',
  'setHexColor',
  '_zoneApplyAreaPixelCount',
  'getZoneColorFilterRgb',
  'setZoneFitIntoApplyArea',
  'activateZoneApplyArea',
  'clearZoneApplyArea',
  'startZoneApplyAreaDraw',
  'autoActivateZoneApplyArea',
  'buildZoneApplyAreaSection'
]) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
}
for (const oldMarker of ['COLOR SELECTORS', 'HEX CODE COLOR']) {
  if (zones.includes(oldMarker)) failures.push(`paint-booth-2-state-zones.js: old source/color marker still lives in monster file: ${oldMarker}`);
}

if (failures.length) {
  console.error('Zone source/color/apply controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone source/color/apply controls guard passed (color/source-layer/apply-area island extracted).');
