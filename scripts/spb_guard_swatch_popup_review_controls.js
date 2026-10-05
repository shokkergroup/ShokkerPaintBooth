const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_swatch_popup_review_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/swatch-popup-review-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBSwatchPopupReviewControls = {',
  'function collectPickerRankingRows(limit)',
  'function collectPickerOwnerDisagreementRows(limit)',
  'function collectPickerOwnerRatingReviewRows(scopeTypes, limit)',
  'function exportPickerRatingReview(event, scopeName)',
  'function _swatchReviewAllowedTypes()',
  'function _renderSwatchLowScorePanel(limit)',
  'global.collectPickerRankingRows = collectPickerRankingRows',
  'global._renderSwatchLowScorePanel = _renderSwatchLowScorePanel'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBSwatchPopupReviewControls.install',
  'getSpecPatterns: () => (typeof SPEC_PATTERNS !== \'undefined\' ? SPEC_PATTERNS : [])',
  'rankSpecPatternForPicker: (item, category) => (typeof _rankSpecPatternForPicker === \'function\'',
  'catalogRankingForItem: (item, type) => _catalogRankingForItem(item, type)',
  'getSwatchPopupState: () => swatchPopupState'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function collectPickerRankingRows(limit) {',
  'function collectPickerOwnerDisagreementRows(limit) {',
  'function collectPickerOwnerRatingReviewRows(scopeTypes, limit) {',
  'function exportPickerRatingReview(event, scopeName) {',
  'function _swatchReviewAllowedTypes() {',
  'function _renderSwatchLowScorePanel(limit) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const rankingScript = indexOf(htmlSource, 'js/zones/swatch-popup-ranking-controls.js', htmlFile);
const reviewScript = indexOf(htmlSource, 'js/zones/swatch-popup-review-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/swatch-popup-preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(rankingScript < reviewScript, 'review module must load after swatch ranking controls');
assert(reviewScript < previewScript, 'review module must load before swatch preview controls');
assert(reviewScript < zonesScript, 'review module must load before the zone monster script');

console.log('[spb_guard_swatch_popup_review_controls] ok');
