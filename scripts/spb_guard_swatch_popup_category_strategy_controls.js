const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_swatch_popup_category_strategy_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/swatch-popup-category-strategy-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBSwatchPopupCategoryStrategyControls = {',
  'function collectPickerCategoryStrategyRows(scopeTypes, limit)',
  'function collectPickerConsolidatedCategoryProposal(scopeTypes)',
  'function _renderCategoryStrategySummary(scopeTypes, label)',
  'function _downloadPickerJson(payload, filename)',
  'function toggleSwatchCategoryStrategyPanel(force)',
  'function focusSwatchCategoryStrategyLane(lane, event, category)',
  'global.collectPickerCategoryStrategyRows = collectPickerCategoryStrategyRows',
  'global.exportPickerConsolidatedCategoryProposal = exportPickerConsolidatedCategoryProposal'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBSwatchPopupCategoryStrategyControls.install',
  'collectPickerRankingRows: () => (typeof window.collectPickerRankingRows === \'function\'',
  'swatchReviewAllowedTypes: () => (typeof window._swatchReviewAllowedTypes === \'function\'',
  'setPickerActiveLaneContext: (gridId, groupName, context) => _safeSetPickerActiveLaneContext(gridId, groupName, context)',
  'pickerLaneContextFromStrategy: (row, category, lane, gridId) => _pickerLaneContextFromStrategy(row, category, lane, gridId)',
  'toggleSwatchCategoryStrategyPanel: (force) => { if (typeof window.toggleSwatchCategoryStrategyPanel === \'function\')'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function collectPickerCategoryStrategyRows(scopeTypes, limit) {',
  'function collectPickerConsolidatedCategoryProposal(scopeTypes) {',
  'function _renderCategoryStrategySummary(scopeTypes, label) {',
  'function _downloadPickerJson(payload, filename) {',
  'function toggleSwatchCategoryStrategyPanel(force) {',
  'function focusSwatchCategoryStrategyLane(lane, event, category) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const reviewScript = indexOf(htmlSource, 'js/zones/swatch-popup-review-controls.js', htmlFile);
const strategyScript = indexOf(htmlSource, 'js/zones/swatch-popup-category-strategy-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/swatch-popup-preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(reviewScript < strategyScript, 'category strategy module must load after swatch review controls');
assert(strategyScript < previewScript, 'category strategy module must load before swatch preview controls');
assert(strategyScript < zonesScript, 'category strategy module must load before the zone monster script');

console.log('[spb_guard_swatch_popup_category_strategy_controls] ok');
