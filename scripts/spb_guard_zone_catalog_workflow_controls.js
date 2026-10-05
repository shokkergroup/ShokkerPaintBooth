#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const moduleSource = read('js/zones/catalog-workflow-controls.js');

const failures = [];
const functions = [
  'enhanceGuidedCatalogCards',
  'showCommandPalette',
  'hideCommandPalette',
  'renderCommandPaletteResults',
  'highlightCommandPaletteSelection',
  'executeCommandPaletteSelection',
  'renderSmartFilterChips',
  'applySmartFilterChips',
  'enhanceZoneCardsMaterial',
];

if (!(html.indexOf('js/zones/catalog-workflow-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: catalog workflow controls must load before zones installer');
}
if (!zones.includes('SPBZoneCatalogWorkflowControls.install')) {
  failures.push('paint-booth-2-state-zones.js: missing catalog workflow installer bridge');
}
if (!moduleSource.includes('window.SPBZoneCatalogWorkflowControls = { install }')) {
  failures.push('catalog workflow controls module: export missing');
}
if (!moduleSource.includes('window._activeFilterChip')) {
  failures.push('catalog workflow controls module: active filter chip must stay global for renderFinishLibrary guard');
}
if (!moduleSource.includes("e.key.toLowerCase() === 'k'")) {
  failures.push('catalog workflow controls module: Ctrl/Cmd+K command palette hotkey missing');
}
for (const fn of functions) {
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  if (!moduleSource.includes(`window.${fn} = function ${fn}`)) {
    failures.push(`js/zones/catalog-workflow-controls.js: missing ${fn} install`);
  }
}

if (failures.length) {
  console.error('Zone catalog workflow controls guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone catalog workflow controls guard passed (quick actions, command palette, filter chips, and material card polish extracted).');
