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

const moduleFile = 'js/zones/swatch-popup-render-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

const helperNeedles = [
  'function getOverlayBaseDisplay',
  'function _pickerSwatchFinishKey',
  'function _pickerCatalogItemType',
  'function _pickerSelectValueForItem',
  'function getFinishType',
  'function _normalizeSwatchTintHex',
  'function getSwatchUrl',
  'function getOverlaySpecialPickerHtml',
  'function renderSwatchSquare',
  'function renderSwatchDot',
  'function getSwatchColor',
  'function getPatternSwatchColor'
];

[
  'SPBSwatchPopupRenderControls',
  'Object.assign(global'
].concat(helperNeedles).forEach((needle) => {
  assert(mod.includes(needle), `${moduleFile} missing ${needle}`);
});

[
  'getOverlayBaseDisplay: getOverlayBaseDisplay',
  '_pickerSwatchFinishKey: _pickerSwatchFinishKey',
  '_pickerCatalogItemType: _pickerCatalogItemType',
  '_pickerSelectValueForItem: _pickerSelectValueForItem',
  'getFinishType: getFinishType',
  '_normalizeSwatchTintHex: _normalizeSwatchTintHex',
  'getSwatchUrl: getSwatchUrl',
  'getOverlaySpecialPickerHtml: getOverlaySpecialPickerHtml',
  'renderSwatchSquare: renderSwatchSquare',
  'renderSwatchDot: renderSwatchDot',
  'getSwatchColor: getSwatchColor',
  'getPatternSwatchColor: getPatternSwatchColor'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.indexOf('js/zones/finish-library-search-controls.js') < html.indexOf('js/zones/swatch-popup-render-controls.js') &&
    html.indexOf('js/zones/swatch-popup-render-controls.js') < html.indexOf('js/zones/swatch-popup-preview-controls.js') &&
    html.indexOf('js/zones/swatch-popup-preview-controls.js') < html.indexOf('js/zones/swatch-popup-lane-controls.js') &&
    html.indexOf('js/zones/swatch-popup-lane-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup render module must load before preview/lane/filter modules and paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupRenderControls.install',
  "getBases: () => (typeof BASES !== 'undefined' ? BASES : [])",
  "getPatterns: () => (typeof PATTERNS !== 'undefined' ? PATTERNS : [])",
  "getMonolithics: () => (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : [])",
  "getFinishTypeById: () => (typeof FINISH_TYPE_BY_ID !== 'undefined' ? FINISH_TYPE_BY_ID : {})",
  'escapeHtml'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup render bridge missing ${needle}`));

assert(
  zones.indexOf('window.SPBSwatchPopupRenderControls.install') < zones.indexOf('window.SPBZoneBaseOverlayControls.install') &&
    zones.indexOf('window.SPBSwatchPopupRenderControls.install') < zones.indexOf('getOverlayBaseDisplay:'),
  'swatch popup render installer must run before base-overlay installer consumes getOverlayBaseDisplay'
);

helperNeedles.forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  'renderSwatchDot(zone.finish',
  "getOverlaySpecialPickerHtml(zone, i, 'second')",
  'renderSwatchSquare(b.id, b.swatch',
  'function getSwatchUrl(finishId, colorHex, forceSplit, size, forceType)'
].forEach((needle) => {
  assert(mod.includes(needle) || zones.includes(needle), `expected swatch render call missing: ${needle}`);
});

console.log('Swatch popup render guard passed (render/type helpers extracted).');
