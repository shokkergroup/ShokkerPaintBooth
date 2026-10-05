#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/advanced-workflow-controls.js');

const failures = [];
const functions = [
  'getZoneSummary',
  'previewImportedConfig',
  'showConfigImportPreview',
  'bringZoneToFront',
  'sendZoneToBack',
  'getSpecialColorExplanation',
  'getZoneRenderOrder',
  'invertAllZoneMutes',
  'setZoneTag',
  'getZonesByTag',
  'suggestSmartTolerance',
  'duplicateZoneWithColor',
  'getSuggestedPatternsForBase',
  'getUnrenderableZoneCount',
  'touchZoneTimestamp',
  'getZoneAge',
  'bulkShiftMultiColors',
  'previewImportedZone',
];

if (!(html.indexOf('js/zones/advanced-workflow-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: advanced workflow controls must load before zones installer');
}
if (!zones.includes('SPBZoneAdvancedWorkflowControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing advanced workflow installer bridge');
}
if (!moduleSource.includes('window.SPBZoneAdvancedWorkflowControls = { install, BASE_PATTERN_SUGGESTIONS }')) {
  failures.push('advanced workflow controls module: export missing');
}
if (!moduleSource.includes('BASE_PATTERN_SUGGESTIONS')) {
  failures.push('advanced workflow controls module: base pattern suggestions missing');
}
if (!moduleSource.includes('spbZoneFlashCSS')) {
  failures.push('advanced workflow controls module: zone flash CSS injection missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`window.${fn} = function ${fn}`)) {
    failures.push(`js/zones/advanced-workflow-controls.js: missing ${fn} install`);
  }
}

if (failures.length) {
  console.error('Zone advanced workflow controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone advanced workflow controls guard passed (summary/import/order/mute/tag/tolerance/duplicate/shift utilities extracted).');
