#!/usr/bin/env node

const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

const moduleFile = 'js/zones/swatch-popup-open-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

assert(mod.includes('SPBSwatchPopupOpenControls'), `${moduleFile} missing installer namespace`);
assert(mod.includes('function renderAndShowSwatchPicker'), `${moduleFile} missing renderAndShowSwatchPicker`);
assert(mod.includes('function openSwatchPicker'), `${moduleFile} missing openSwatchPicker`);
assert(mod.includes('grid.innerHTML = args.html'), `${moduleFile} missing grid commit`);
assert(mod.includes('triggerEl.getBoundingClientRect()'), `${moduleFile} missing trigger positioning`);
assert(mod.includes('searchInput.placeholder'), `${moduleFile} missing search-input setup`);
assert(mod.includes('filterSwatchPopup(\'\')'), `${moduleFile} missing filter reset`);
assert(mod.includes('scrollSwatchPickerToSelection();'), `${moduleFile} missing selected-item scroll`);
assert(mod.includes('getSwatchPopupState'), `${moduleFile} missing injected popup state getter`);
assert(mod.includes('setSwatchPopupState'), `${moduleFile} missing injected popup state setter`);
assert(mod.includes('getCurrentSwatchPickerId({ zone: zone, type: type, layerIndex: layerIndex })'), `${moduleFile} missing current selection resolver`);
assert(mod.includes('buildSwatchPickerGridHtml({ type: type, currentId: currentId })'), `${moduleFile} missing grid builder call`);
assert(mod.includes('openSwatchPicker: openSwatchPicker'), `${moduleFile} does not export openSwatchPicker`);

assert(
  html.indexOf('js/zones/swatch-popup-selection-controls.js') < html.indexOf('js/zones/swatch-popup-open-controls.js') &&
    html.indexOf('js/zones/swatch-popup-open-controls.js') < html.indexOf('js/zones/swatch-popup-lifecycle-controls.js') &&
    html.indexOf('js/zones/swatch-popup-lifecycle-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup open module must load after selection, before lifecycle/filter, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupOpenControls.install',
  'enhanceSwatchPopupCards: (currentId, type) => { if (typeof window._enhanceSwatchPopupCards === \'function\') window._enhanceSwatchPopupCards(currentId, type); }',
  'renderSwatchPopupFilterControls: (type) => _renderSwatchPopupFilterControls(type)',
  'renderSwatchCurationLanes: (type) => _renderSwatchCurationLanes(type)',
  'renderSwatchLowScorePanel: (limit) => _renderSwatchLowScorePanel(limit)',
  'installSwatchPopupLazyLoader: () => _installSwatchPopupLazyLoader()',
  'filterSwatchPopup: (query) => filterSwatchPopup(query)',
  'scrollSwatchPickerToSelection: () => _scrollSwatchPickerToSelection()',
  'getSwatchPopupState: () => swatchPopupState',
  'setSwatchPopupState: (nextState) => { swatchPopupState = nextState; }',
  'getZones: () => zones',
  'getCurrentSwatchPickerId: (args) => getCurrentSwatchPickerId(args)',
  'buildSwatchPickerGridHtml: (args) => buildSwatchPickerGridHtml(args)',
  'closeSwatchPicker: () => (typeof closeSwatchPicker === \'function\' ? closeSwatchPicker() : null)'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup open bridge missing ${needle}`));

[
  'const popupW = Math.min(1500, Math.max(1040, window.innerWidth - 10));',
  'searchInput.title = \'Search finish names, descriptions, ids, metadata, aliases, and hashtag-style terms such as #chrome, #weathered, #carbon, #matte, or #spec\';',
  'function openSwatchPicker(triggerEl, type, zoneIndex, layerIndex) {',
  'swatchPopupState = { open: true, type, zoneIndex, layerIndex: layerIndex ?? -1, triggerEl, filter: \'all\', sort: \'default\' };'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should be extracted from ${zonesFile}`));

console.log('Swatch popup open guard passed (opener/grid commit/show/focus extracted).');
