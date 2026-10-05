const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_swatch_popup_action_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/swatch-popup-action-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);

[
  'global.SPBSwatchPopupActionControls = {',
  'function toggleSwatchLowScorePanel(force)',
  'function focusSwatchReviewCandidate(id, event, filterName)',
  'function toggleSwatchPickerFavorite(finishId, event)',
  'function _enhanceSwatchPopupCards(currentId, pickerType)',
  'global.toggleSwatchLowScorePanel = toggleSwatchLowScorePanel',
  'global._enhanceSwatchPopupCards = _enhanceSwatchPopupCards'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBSwatchPopupActionControls.install',
  'getFavoriteFinishes: () => _favoriteFinishes',
  'renderSwatchFavoritesGroup: (kind, currentId) => (typeof window._renderSwatchFavoritesGroup === \'function\'',
  'enhanceSwatchPopupCards: (currentId, type) => { if (typeof window._enhanceSwatchPopupCards === \'function\')',
  'toggleSwatchLowScorePanel: (force) => { if (typeof window.toggleSwatchLowScorePanel === \'function\')'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function toggleSwatchLowScorePanel(force) {',
  'function focusSwatchReviewCandidate(id, event, filterName) {',
  'function toggleSwatchPickerFavorite(finishId, event) {',
  'function _enhanceSwatchPopupCards(currentId, pickerType) {'
].forEach((needle) => {
  assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted helper ${needle}`);
});

const strategyScript = indexOf(htmlSource, 'js/zones/swatch-popup-category-strategy-controls.js', htmlFile);
const actionScript = indexOf(htmlSource, 'js/zones/swatch-popup-action-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/swatch-popup-preview-controls.js', htmlFile);
const openScript = indexOf(htmlSource, 'js/zones/swatch-popup-open-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(strategyScript < actionScript, 'action module must load after category strategy controls');
assert(actionScript < previewScript, 'action module must load before swatch preview controls');
assert(actionScript < openScript, 'action module must load before swatch open controls');
assert(actionScript < zonesScript, 'action module must load before the zone monster script');

console.log('[spb_guard_swatch_popup_action_controls] ok');
