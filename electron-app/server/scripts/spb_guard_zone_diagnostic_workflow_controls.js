#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/diagnostic-workflow-controls.js');

const failures = [];
const functions = [
  'validateZonesBeforeRender',
  'showZoneValidationWarnings',
  'getZoneStatistics',
  'zoneHasMissingSourceLayer',
  '_trackRecentFinishV2',
  'getRecentFinishesV2',
  'isolateAndEditZone',
  '_spbShouldAutoFillByName',
  'setAllZonesTolerance',
  '_enhanceUndoLabel',
  'getZoneEffectiveTargetCount',
  'getZoneColorPillHTML',
  'getZoneWorkflowHelp',
];

if (!(html.indexOf('js/zones/diagnostic-workflow-controls.js') < html.indexOf('js/zones/workflow-controls.js'))) {
  failures.push('paint-booth-v2.html: diagnostic workflow controls must load before workflow controls');
}
if (!(html.indexOf('js/zones/diagnostic-workflow-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: diagnostic workflow controls must load before zones installer');
}
if (!zones.includes('SPBZoneDiagnosticWorkflowControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing diagnostic workflow installer bridge');
}
if (!zones.includes('validateZonesBeforeRender: window.validateZonesBeforeRender')) {
  failures.push('paint-booth-2-state-zones.js: workflow bridge must use window validate hook');
}
if (!zones.includes('zoneHasMissingSourceLayer: window.zoneHasMissingSourceLayer')) {
  failures.push('paint-booth-2-state-zones.js: workflow bridge must use window missing-layer hook');
}
if (!moduleSource.includes('window.SPBZoneDiagnosticWorkflowControls = { install, recentFinishesV2 }')) {
  failures.push('diagnostic workflow controls module: export missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`window.${fn} = function ${fn}`)) {
    failures.push(`js/zones/diagnostic-workflow-controls.js: missing ${fn} install`);
  }
}

if (failures.length) {
  console.error('Zone diagnostic workflow controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone diagnostic workflow controls guard passed (validation, statistics, recent finishes, isolate/edit, tolerance, and helper tail extracted).');
