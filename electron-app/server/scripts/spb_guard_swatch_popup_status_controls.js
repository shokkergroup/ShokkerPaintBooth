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

const moduleFile = 'js/zones/swatch-popup-status-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

const helperNeedles = [
  'function _pickerLaneDisplay',
  'function _pickerLaneContextFromStrategy',
  'function _pickerContextUsesCategory',
  'function _pickerCardMatchesContextCategory',
  'function _setPickerActiveLaneContext',
  'function setMainPickerLaneScope',
  'function resetSwatchPickerGuidedContext',
  'function _pickerFindPlanRow',
  'function _highlightPickerPlanRow',
  'function openSwatchActiveLanePlan',
  'function _updateSwatchActiveLaneStatus'
];

[
  'SPBSwatchPopupStatusControls',
  'Object.assign(global'
].concat(helperNeedles).forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_pickerLaneDisplay: _pickerLaneDisplay',
  '_pickerLaneContextFromStrategy: _pickerLaneContextFromStrategy',
  '_pickerContextUsesCategory: _pickerContextUsesCategory',
  '_pickerCardMatchesContextCategory: _pickerCardMatchesContextCategory',
  '_setPickerActiveLaneContext: _setPickerActiveLaneContext',
  'setMainPickerLaneScope: setMainPickerLaneScope',
  'resetSwatchPickerGuidedContext: resetSwatchPickerGuidedContext',
  '_pickerFindPlanRow: _pickerFindPlanRow',
  '_highlightPickerPlanRow: _highlightPickerPlanRow',
  'openSwatchActiveLanePlan: openSwatchActiveLanePlan',
  '_updateSwatchActiveLaneStatus: _updateSwatchActiveLaneStatus'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.indexOf('js/zones/swatch-popup-health-controls.js') < html.indexOf('js/zones/swatch-popup-status-controls.js') &&
    html.indexOf('js/zones/swatch-popup-status-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup status module must load after health, before filters, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupStatusControls.install',
  'getSwatchPopupState: () => swatchPopupState',
  'getPickerActiveLaneContext: () => pickerActiveLaneContext',
  'setMainPickerActiveLaneContext: (context) => { pickerActiveLaneContext.main = context || null; }',
  'setSpecPickerActiveLaneContext: (gridId, context) => {',
  'swatchCurationLaneDefinitions: (type) => _swatchCurationLaneDefinitions(type)',
  'specCurationLaneDefinitions: () => _specCurationLaneDefinitions()',
  'filterSwatchPopup: (query) => filterSwatchPopup(query)',
  'toggleSwatchCategoryStrategyPanel: (force) => toggleSwatchCategoryStrategyPanel(force)',
  'escapeHtml'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup status bridge missing ${needle}`));

helperNeedles.forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  "_setPickerActiveLaneContext('spec', gridId, null)",
  '_pickerFindPlanRow(panel, context && context.category, context && context.lane)',
  '_highlightPickerPlanRow(row)'
].forEach((needle) => assert(zones.includes(needle), `expected spec status call missing: ${needle}`));

console.log('Swatch popup status guard passed (active-lane context/status extracted).');
