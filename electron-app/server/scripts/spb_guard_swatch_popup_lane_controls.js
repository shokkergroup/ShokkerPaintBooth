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

const moduleFile = 'js/zones/swatch-popup-lane-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBSwatchPopupLaneControls',
  'function _renderSwatchPopupFilterControls',
  'function _swatchCurationLaneMatch',
  'function _swatchCurationLaneDefinitions',
  'function _renderSwatchCurationLanes',
  'function _updateSwatchCurationLaneCounts',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_renderSwatchPopupFilterControls: _renderSwatchPopupFilterControls',
  '_swatchCurationLaneMatch: _swatchCurationLaneMatch',
  '_swatchCurationLaneDefinitions: _swatchCurationLaneDefinitions',
  '_renderSwatchCurationLanes: _renderSwatchCurationLanes',
  '_updateSwatchCurationLaneCounts: _updateSwatchCurationLaneCounts'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/swatch-popup-lane-controls.js') &&
    html.indexOf('js/zones/finish-library-search-controls.js') < html.indexOf('js/zones/swatch-popup-lane-controls.js') &&
    html.indexOf('js/zones/swatch-popup-lane-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup lane module must load after smart search helpers, before swatch filters, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupLaneControls.install',
  'getSwatchPopupState: () => swatchPopupState',
  'internalReviewUiEnabled: PICKER_INTERNAL_REVIEW_UI_ENABLED',
  'escapeHtml'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup lane bridge missing ${needle}`));

[
  'function _renderSwatchPopupFilterControls',
  'function _swatchCurationLaneMatch',
  'function _swatchCurationLaneDefinitions',
  'function _renderSwatchCurationLanes',
  'function _updateSwatchCurationLaneCounts'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  '_renderSwatchPopupFilterControls(type)',
  '_renderSwatchCurationLanes(type)',
  '_swatchCurationLaneMatch(card, lane)',
  '_updateSwatchCurationLaneCounts(grid)'
].forEach((needle) => assert(mod.includes(needle) || zones.includes(needle), `expected swatch lane call missing: ${needle}`));

console.log('Swatch popup lane guard passed (lane/filter chrome extracted).');
