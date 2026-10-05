#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const patternModule = read('js/zones/pattern-transform-controls.js');

const failures = [];
const fns = [
  'setZonePatternSpecMult', 'stepZonePatternSpecMult',
  'setZonePatternOpacity', 'stepZonePatternOpacity',
  'setZonePatternOffsetX', 'setZonePatternOffsetY',
  'stepZonePatternOffsetX', 'stepZonePatternOffsetY',
  'setZonePatternFlipH', 'setZonePatternFlipV',
  'setZoneScale', 'stepZoneScale', 'resetZoneScale',
  'setZoneRotation', 'stepZoneRotation', 'resetZoneRotation',
  'addPatternLayer', 'removePatternLayer', 'setPatternLayerId',
  'setPatternLayerOpacity', 'stepPatternLayerOpacity',
  'setPatternLayerScale', 'stepPatternLayerScale',
  'setPatternLayerRotation', 'stepPatternLayerRotation',
  'setPatternLayerBlend',
];

if (!(html.indexOf('js/zones/pattern-transform-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: pattern transform controls must load before zones installer');
}
if (!zones.includes('SPBZonePatternTransformControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing pattern transform installer bridge');
}
for (const fn of fns) {
  if (!patternModule.includes(`window.${fn}`)) failures.push(`js/zones/pattern-transform-controls.js: missing ${fn}()`);
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
}
if (!patternModule.includes('applyPlacementPatternTransform')) failures.push('pattern transform module: placement preview hook missing');
if (!patternModule.includes('Pattern opacity')) failures.push('pattern transform module: pattern opacity undo label missing');
if (!zones.includes('pushZoneUndoCoalesced') || !zones.includes('showToast')) failures.push('paint-booth-2-state-zones.js: installer must pass pattern-stack deps');

if (failures.length) {
  console.error('Zone pattern transform guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone pattern transform guard passed (primary transforms + pattern-stack controls extracted).');
