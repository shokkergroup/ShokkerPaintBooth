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

const moduleFile = 'js/zones/swatch-popup-grid-builder-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBSwatchPopupGridBuilderControls',
  'function buildSwatchPickerGridHtml',
  'function buildBaseSections',
  'function buildSpecialSections',
  'function buildPatternSections',
  'Object.assign(global, { buildSwatchPickerGridHtml: buildSwatchPickerGridHtml })'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  'getBaseGroups',
  'getPatternGroups',
  'getSpecialGroups',
  'pickerCatalogItemType',
  'pickerSelectValueForItem',
  'renderSwatchSquare'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing dependency ${needle}`));

assert(
  html.indexOf('js/zones/swatch-popup-current-selection-controls.js') < html.indexOf('js/zones/swatch-popup-grid-builder-controls.js') &&
    html.indexOf('js/zones/swatch-popup-grid-builder-controls.js') < html.indexOf('js/zones/swatch-popup-open-controls.js') &&
    html.indexOf('js/zones/swatch-popup-open-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'grid-builder module must load after current-selection, before open, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupGridBuilderControls.install',
  'const html = buildSwatchPickerGridHtml({ type, currentId });',
  "getBaseGroups: () => (typeof BASE_GROUPS !== 'undefined' ? BASE_GROUPS : {})",
  "getSpecialsSections: () => (typeof SPECIALS_SECTIONS !== 'undefined' ? SPECIALS_SECTIONS : {})",
  'renderSwatchSquare: (finishId, fallbackColor, title, colorHex, forceType) => renderSwatchSquare(finishId, fallbackColor, title, colorHex, forceType)'
].forEach((needle) => assert(zones.includes(needle), `zones grid-builder bridge missing ${needle}`));

[
  'const _nameSort = (a, b)',
  'const baseGroupedIds = new Set();',
  'function renderGroupSection(groups, sectionLabel, sectionIcon)',
  'Object.keys(PATTERN_GROUPS).sort'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should be extracted from ${zonesFile}`));

console.log('Swatch popup grid-builder guard passed (picker grid HTML extracted).');
