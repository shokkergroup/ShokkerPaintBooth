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

const moduleFile = 'js/zones/swatch-popup-filter-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBSwatchPopupFilterControls',
  'function _swatchPopupHayMatchesQuery',
  'function _applySwatchPopupSort',
  'function filterSwatchPopup',
  'function setSwatchSmartSearch',
  'function setSwatchPopupFilter',
  'function setSwatchPopupSort',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_swatchPopupHayMatchesQuery: _swatchPopupHayMatchesQuery',
  '_applySwatchPopupSort: _applySwatchPopupSort',
  'filterSwatchPopup: filterSwatchPopup',
  'setSwatchSmartSearch: setSwatchSmartSearch',
  'setSwatchPopupFilter: setSwatchPopupFilter',
  'setSwatchPopupSort: setSwatchPopupSort'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/finish-library-search-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup filter module must load after smart search helpers and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupFilterControls.install',
  'getSwatchPopupState: () => swatchPopupState',
  'setPickerActiveLaneContext: (lane, item, context) => _safeSetPickerActiveLaneContext(lane, item, context)',
  'swatchCurationLaneMatch: (card, lane) => _swatchCurationLaneMatch(card, lane)',
  'pickerCardMatchesContextCategory: (card, context) => _pickerCardMatchesContextCategory(card, context)',
  'installSwatchPopupLazyLoader: () => _installSwatchPopupLazyLoader()'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup bridge missing ${needle}`));

[
  'function _swatchPopupHayMatchesQuery',
  'function _applySwatchPopupSort',
  'function filterSwatchPopup',
  'function setSwatchSmartSearch',
  'function setSwatchPopupFilter',
  'function setSwatchPopupSort'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

assert(
  mod.includes("filterSwatchPopup(search ? search.value : '')") || zones.includes("filterSwatchPopup(search ? search.value : '')"),
  "expected live swatch filter call missing: filterSwatchPopup(search ? search.value : '')"
);

console.log('Swatch popup filter guard passed (filter/sort handlers extracted).');
