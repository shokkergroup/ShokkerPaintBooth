#!/usr/bin/env node

const fs = require('fs');
const { countFileLines } = require('./spb_line_count');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

const moduleFile = 'js/zones/finish-library-panel-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryPanelControls',
  'function _renderFinishLibraryPanelHtml',
  'MATERIAL QUICK-PICK',
  'FEATURED COLLECTIONS',
  'QUALITY SIGNALS',
  'SPECIALS HEALTH',
  'MATERIAL FAMILIES',
  'PATTERN FILTERS',
  'PATTERN ADVISOR',
  '_renderFinishLibraryPanelHtml: _renderFinishLibraryPanelHtml'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

assert(
  html.includes('js/zones/finish-library-panel-controls.js') &&
    html.indexOf('js/zones/finish-library-guided-catalog-controls.js') < html.indexOf('js/zones/finish-library-panel-controls.js') &&
    html.indexOf('js/zones/finish-library-panel-controls.js') < html.indexOf('js/zones/finish-library-render-item-controls.js') &&
    html.indexOf('js/zones/finish-library-panel-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library panel module must load after guided catalog and before render-item/zones'
);

assert(
  zones.includes('window.SPBZoneFinishLibraryPanelControls.install') &&
    zones.includes('_renderFinishLibraryPanelHtml({') &&
    zones.includes('libraryZoneContext: _libraryZoneContext'),
  'zones installer bridge/render context missing finish library panel dependencies'
);

[
  'MATERIAL QUICK-PICK',
  'FEATURED COLLECTIONS',
  'QUALITY SIGNALS',
  'SPECIALS HEALTH',
  'MATERIAL FAMILIES',
  'PATTERN FILTERS',
  'PATTERN ADVISOR',
  'const _activeItemOrder'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

const zoneLines = countFileLines(zonesFile);
assert(zoneLines <= 12000, `${zonesFile} line count ${zoneLines} exceeds 12000 panel extraction target`);

console.log(`Zone finish library panel guard passed (${moduleFile} extracted, ${zonesFile} ${zoneLines} lines).`);
