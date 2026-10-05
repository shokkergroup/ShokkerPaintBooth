const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_swatch_popup_ranking_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/swatch-popup-ranking-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBSwatchPopupRankingControls = {',
  'function _getSwatchItemById(id, typeHint)',
  'function _catalogRankingForItem(item, type)',
  'function _renderCatalogRankChips(item, type, precomputedRank)',
  'function _swatchPickerSearchText(item, type, groupName)',
  'function _renderSwatchPickerCard(item, type, currentId, selectValue, groupName)',
  'function _renderSwatchFavoritesGroup(kind, currentId)',
  'global._getSwatchItemById = _getSwatchItemById',
  'global._catalogRankingForItem = _catalogRankingForItem',
  'global._swatchPickerSearchText = _swatchPickerSearchText',
  'global._renderSwatchPickerCard = _renderSwatchPickerCard',
  'global._renderSwatchFavoritesGroup = _renderSwatchFavoritesGroup'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBSwatchPopupRankingControls.install',
  'getBases: () => (typeof BASES !== \'undefined\' ? BASES : [])',
  'getMonolithics: () => (typeof MONOLITHICS !== \'undefined\' ? MONOLITHICS : [])',
  'getPatterns: () => (typeof PATTERNS !== \'undefined\' ? PATTERNS : [])',
  'getCatalogScorecardMetrics: () => (typeof CATALOG_SCORECARD_METRICS !== \'undefined\'',
  'getLibrarySearchText: (item, type) => (typeof _getLibrarySearchText === \'function\' ? _getLibrarySearchText(item, type) : \'\')',
  'renderSwatchSquare: (finishId, fallbackColor, title, colorHex, forceType) => renderSwatchSquare(finishId, fallbackColor, title, colorHex, forceType)'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function _getSwatchItemById(id, typeHint) {',
  'function _rankClamp(value, min, max) {',
  'function _catalogRankingForItem(item, type) {',
  'function _renderSwatchPickerCard(item, type, currentId, selectValue, groupName) {',
  'function _renderSwatchFavoritesGroup(kind, currentId) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const renderScript = indexOf(htmlSource, 'js/zones/swatch-popup-render-controls.js', htmlFile);
const rankingScript = indexOf(htmlSource, 'js/zones/swatch-popup-ranking-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/swatch-popup-preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(renderScript < rankingScript, 'ranking module must load after swatch render controls');
assert(rankingScript < previewScript, 'ranking module must load before swatch preview controls');
assert(rankingScript < zonesScript, 'ranking module must load before the zone monster script');

console.log('[spb_guard_swatch_popup_ranking_controls] ok');
