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

const moduleFile = 'js/zones/swatch-popup-preview-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBSwatchPopupPreviewControls',
  'function _disconnectSwatchPopupLazyLoader',
  'function _hydrateDeferredSwatchImage',
  'function _scrollSwatchPickerToSelection',
  'function _installSwatchPopupLazyLoader',
  'function openSwatchPreviewFromPicker',
  'function openSwatchPreviewModal',
  'function closeSwatchPreviewModal',
  'async function runSwatchPreviewOnPaint',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_disconnectSwatchPopupLazyLoader: _disconnectSwatchPopupLazyLoader',
  '_hydrateDeferredSwatchImage: _hydrateDeferredSwatchImage',
  '_scrollSwatchPickerToSelection: _scrollSwatchPickerToSelection',
  '_installSwatchPopupLazyLoader: _installSwatchPopupLazyLoader',
  'openSwatchPreviewFromPicker: openSwatchPreviewFromPicker',
  'openSwatchPreviewModal: openSwatchPreviewModal',
  'closeSwatchPreviewModal: closeSwatchPreviewModal',
  'runSwatchPreviewOnPaint: runSwatchPreviewOnPaint'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/swatch-popup-preview-controls.js') &&
    html.indexOf('js/zones/finish-library-search-controls.js') < html.indexOf('js/zones/swatch-popup-preview-controls.js') &&
    html.indexOf('js/zones/swatch-popup-preview-controls.js') < html.indexOf('js/zones/swatch-popup-lane-controls.js') &&
    html.indexOf('js/zones/swatch-popup-lane-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup preview module must load before lane/filter modules and paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupPreviewControls.install',
  'showToast',
  "getFinishType: (id) => (typeof getFinishType === 'function' ? getFinishType(id) : 'base')",
  "getMonolithics: () => (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : [])",
  "getBases: () => (typeof BASES !== 'undefined' ? BASES : [])"
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup preview bridge missing ${needle}`));

assert(
  zones.indexOf('window.SPBSwatchPopupPreviewControls.install') < zones.indexOf('function closeSwatchPicker') &&
    zones.indexOf('window.SPBSwatchPopupPreviewControls.install') < zones.indexOf('_disconnectSwatchPopupLazyLoader();'),
  'swatch popup preview installer must run before closeSwatchPicker can call _disconnectSwatchPopupLazyLoader'
);

[
  'function _disconnectSwatchPopupLazyLoader',
  'function _hydrateDeferredSwatchImage',
  'function _scrollSwatchPickerToSelection',
  'function _installSwatchPopupLazyLoader',
  'function openSwatchPreviewFromPicker',
  'function openSwatchPreviewModal',
  'function closeSwatchPreviewModal',
  'async function runSwatchPreviewOnPaint',
  'let swatchPreviewState'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  '_installSwatchPopupLazyLoader()',
  '_scrollSwatchPickerToSelection()',
  '_disconnectSwatchPopupLazyLoader()',
  "fetch(getServerBase() + '/preview-render'"
].forEach((needle) => assert(mod.includes(needle) || zones.includes(needle), `expected swatch preview/lazy-load call missing: ${needle}`));

console.log('Swatch popup preview guard passed (lazy-load and preview modal extracted).');
