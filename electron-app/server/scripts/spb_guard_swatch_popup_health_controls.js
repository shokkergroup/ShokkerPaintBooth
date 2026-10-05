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

const moduleFile = 'js/zones/swatch-popup-health-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

const helperNeedles = [
  'function _pickerGroupHealthSummary',
  'function _groupHealthLabel',
  'function _renderGroupHealthBadge',
  'function _pickerCategoryStrategyForGroup',
  'function _renderCategoryPlanBadgeElement',
  'function _wireCategoryPlanBadgeAction'
];

[
  'SPBSwatchPopupHealthControls',
  'Object.assign(global'
].concat(helperNeedles).forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_pickerGroupHealthSummary: _pickerGroupHealthSummary',
  '_groupHealthLabel: _groupHealthLabel',
  '_renderGroupHealthBadge: _renderGroupHealthBadge',
  '_pickerCategoryStrategyForGroup: _pickerCategoryStrategyForGroup',
  '_renderCategoryPlanBadgeElement: _renderCategoryPlanBadgeElement',
  '_wireCategoryPlanBadgeAction: _wireCategoryPlanBadgeAction'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.indexOf('js/zones/swatch-popup-lane-controls.js') < html.indexOf('js/zones/swatch-popup-health-controls.js') &&
    html.indexOf('js/zones/swatch-popup-health-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup health module must load after lanes, before filters, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupHealthControls.install',
  'collectPickerCategoryStrategyRows: (types) => collectPickerCategoryStrategyRows(types)',
  'pickerStrategyBucketId: (row) => _pickerStrategyBucketId(row)',
  'pickerStrategyBucketLabel: (bucket) => _pickerStrategyBucketLabel(bucket)',
  'pickerLaneForStrategyBucket: (bucket) => _pickerLaneForStrategyBucket(bucket)',
  'escapeHtml'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup health bridge missing ${needle}`));

helperNeedles.forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  '_pickerGroupHealthSummary(cards, _swatchCurationLaneMatch)',
  "_renderGroupHealthBadge(summary, 'swatch-group-health')",
  "_renderCategoryPlanBadgeElement(strategyRow, 'swatch-group-plan')"
].forEach((needle) => assert(zones.includes(needle), `expected swatch health call missing: ${needle}`));

console.log('Swatch popup health guard passed (group health and plan badges extracted).');
