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

const moduleFile = 'js/zones/swatch-popup-group-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

const helperNeedles = [
  'function activateSwatchGroupPlanBadge',
  'function _updateSwatchGroupHealthBadges'
];

[
  'SPBSwatchPopupGroupControls',
  'Object.assign(global'
].concat(helperNeedles).forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  'activateSwatchGroupPlanBadge: activateSwatchGroupPlanBadge',
  '_updateSwatchGroupHealthBadges: _updateSwatchGroupHealthBadges'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.indexOf('js/zones/swatch-popup-status-controls.js') < html.indexOf('js/zones/swatch-popup-group-controls.js') &&
    html.indexOf('js/zones/swatch-popup-group-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup group module must load after status, before filters, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupGroupControls.install',
  'internalReviewUiEnabled: PICKER_INTERNAL_REVIEW_UI_ENABLED',
  'pickerLaneForStrategyBucket: (bucket) => _pickerLaneForStrategyBucket(bucket)',
  'setSwatchPopupFilter: (lane, context) => setSwatchPopupFilter(lane, context)',
  'pickerGroupHealthSummary: (cards, matchFn) => _pickerGroupHealthSummary(cards, matchFn)',
  'swatchCurationLaneMatch: (card, lane) => _swatchCurationLaneMatch(card, lane)',
  'pickerCategoryStrategyForGroup: (types, category) => _pickerCategoryStrategyForGroup(types, category)',
  'pickerStrategyBucketId: (row) => _pickerStrategyBucketId(row)',
  'renderGroupHealthBadge: (summary, className) => _renderGroupHealthBadge(summary, className)',
  'renderCategoryPlanBadgeElement: (row, className) => _renderCategoryPlanBadgeElement(row, className)',
  'wireCategoryPlanBadgeAction: (badge, handler) => _wireCategoryPlanBadgeAction(badge, handler)',
  'pickerLaneContextFromStrategy: (row, category, lane, scope) => _pickerLaneContextFromStrategy(row, category, lane, scope)'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup group bridge missing ${needle}`));

helperNeedles.forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  'updateSwatchGroupHealthBadges: (grid) => _updateSwatchGroupHealthBadges(grid)',
  'activateSwatchGroupPlanBadge(planBadge.dataset.planBucket, event, context)'
].forEach((needle) => assert(mod.includes(needle) || zones.includes(needle), `expected group call missing: ${needle}`));

console.log('Swatch popup group guard passed (group plan action and health badge updater extracted).');
