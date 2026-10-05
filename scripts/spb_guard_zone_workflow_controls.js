#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/workflow-controls.js');

const failures = [];
const functions = [
  'getZoneStatus',
  'getZoneStatusBadgeHTML',
  'getZoneDiagnostic',
  'pushPerZoneUndo',
  'undoPerZone',
  'sortZoneColorsByHue',
  'trackRecentFinishOnZone',
  'getRecentFinishesForZone',
  'getLocalStorageUsage',
  'checkLocalStorageQuota',
  'buildExportFilename',
  'promptForAutoRestore',
  'detectZoneOverlaps',
  'checkOverlapsBeforeRender',
  'getCombinedZoneWarnings',
  'showCombinedWarnings',
  'suggestClaimableColors',
  'applySuggestedColorToZone',
  'setZoneIntensityNumeric',
  'suggestColorHarmony',
  'focusZone',
  'getEmptyStateGuide',
  'markDirty',
  'markClean',
  'getLastAutoSaveTime',
  'updateAutoSaveBadge',
  'checkZoneLimitWarning',
  'getLayerThumbnailUrl',
  'soloZone',
  'unmuteAllZones',
  'resetZone',
  'cloneZoneNTimes',
  'filterZonesByStatus',
  'showOnlyProblemZones',
  'showAllZones',
];

if (!(html.indexOf('js/zones/workflow-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: workflow controls must load before zones installer');
}
if (!zones.includes('SPBZoneWorkflowControls.install')) failures.push('paint-booth-2-state-zones.js: missing workflow installer bridge');
if (!zones.includes('pushZoneUndoCoalesced')) failures.push('paint-booth-2-state-zones.js: undo coalescer must stay available for extracted modules');
if (!moduleSource.includes('window.SPBZoneWorkflowControls = { install, state, perZoneUndoStacks, perZoneRecentFinishes }')) {
  failures.push('workflow controls module: export missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`window.${fn} = function ${fn}`)) failures.push(`js/zones/workflow-controls.js: missing ${fn} install`);
}
if (!moduleSource.includes("document.addEventListener('keydown'")) failures.push('workflow controls module: keyboard shortcut listener missing');

if (failures.length) {
  console.error('Zone workflow controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone workflow controls guard passed (status, validation, shortcuts, and workflow utilities extracted).');
