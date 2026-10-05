#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/strength-map-controls.js');

const failures = [];
const functions = [
  'encodeRegionMaskRLE',
  'hasAnyRegionMasks',
  'toggleStrengthMap',
  'strengthMapRedraw',
  'strengthMapStartPaint',
  'strengthMapPaint',
  'strengthMapStopPaint',
  'strengthMapFill',
  'strengthMapGradient',
  'encodeStrengthMapRLE',
];

if (!(html.indexOf('js/zones/strength-map-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: strength-map controls must load before zones installer');
}
if (!zones.includes('SPBZoneStrengthMapControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing strength-map installer bridge');
}
if (!zones.includes('triggerPreviewRender')) {
  failures.push('paint-booth-2-state-zones.js: installer bridge must inject triggerPreviewRender');
}
if (!moduleSource.includes('global.SPBZoneStrengthMapControls = {')) {
  failures.push('strength-map controls module: export missing');
}
if (!moduleSource.includes('var STRENGTH_MAP_SIZE = 256')) {
  failures.push('strength-map controls module: expected 256px working map constant missing');
}
if (!moduleSource.includes('_strengthMapBrushSize') || !moduleSource.includes('_strengthMapBrushValue') || !moduleSource.includes('_strengthMapPainting')) {
  failures.push('strength-map controls module: brush globals must stay initialized by the module');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`global.${fn} = function ${fn}`)) {
    failures.push(`js/zones/strength-map-controls.js: missing ${fn} install`);
  }
}

if (failures.length) {
  console.error('Zone strength-map controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone strength-map controls guard passed (region mask RLE and pattern strength-map canvas controls extracted).');
