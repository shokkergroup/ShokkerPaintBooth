#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
function read(file) { return fs.readFileSync(file, 'utf8'); }
function assert(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}
function indexOf(haystack, needle, label) {
  const index = haystack.indexOf(needle);
  assert(index >= 0, `${label} missing ${needle}`);
  return index;
}
function escapeRegex(value) { return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
const htmlFile = 'paint-booth-v2.html';
const zonesFile = 'paint-booth-2-state-zones.js';
const manifestFile = 'scripts/runtime-sync-manifest.json';
const html = read(htmlFile);
const zones = read(zonesFile);
const manifest = JSON.parse(read(manifestFile));
const manifestFiles = new Set(manifest.files || []);
const zoneModuleRegex = /src="(js\/zones\/[^"?]+\.js)\?v=([^"]+)"/g;
const zoneScripts = [];
let match;
while ((match = zoneModuleRegex.exec(html)) !== null) {
  zoneScripts.push({ src: match[1], token: match[2], index: match.index });
}

assert(zoneScripts.length >= 20, `${htmlFile} has unexpectedly few extracted zone scripts`);
zoneScripts.forEach(({ src }) => {
  assert(fs.existsSync(src), `${htmlFile} references missing extracted module ${src}`);
  assert(manifestFiles.has(src), `${src} is not covered by ${manifestFile}`);
});

['paint-booth-v2.html', 'paint-booth-2-state-zones.js'].forEach((src) => {
  assert(manifestFiles.has(src), `${src} is not covered by ${manifestFile}`);
});

const orderNeedles = [
  'js/zones/base-material-controls.js',
  'js/zones/zone-base-color-controls.js',
  'js/zones/pattern-transform-controls.js',
  'js/zones/zone-base-overlay-state-controls.js',
  'js/zones/zone-material-assignment-controls.js',
  'js/zones/base-overlay-controls.js',
  'js/zones/zone-base-overlay-hsb-controls.js',
  'js/zones/zone-placement-controls.js',
  'js/zones/zone-intensity-controls.js',
  'js/zones/zone-undo-history-controls.js',
  'js/zones/zone-detail-polish-controls.js',
  'js/zones/zone-quick-view-source-controls.js',
  'js/zones/zone-list-action-controls.js',
  'js/zones/zone-default-restore-controls.js',
  'js/zones/zone-swatch-identity-controls.js',
  'js/zones/zone-create-duplicate-controls.js',
  'js/zones/zone-card-render-controls.js',
  'js/zones/zone-multi-color-controls.js',
  'js/zones/zone-link-controls.js',
  'js/zones/zone-thumbnail-controls.js',
  'js/zones/zone-ui-mode-controls.js',
  'js/zones/zone-overlay-special-picker-controls.js',
  'js/zones/zone-render-chrome-controls.js',
  'js/zones/zone-state-shape-controls.js',
  'js/zones/zone-toast-notification-controls.js',
  'js/zones/zone-finish-assignment-controls.js',
  'js/zones/zone-autosave-controls.js',
  'js/zones/zone-config-zone-map-controls.js',
  'js/zones/zone-config-dom-controls.js',
  'js/zones/zone-config-preset-controls.js',
  'js/zones/zone-preset-gallery-controls.js',
  'js/zones/zone-auto-restore-controls.js',
  'js/zones/finish-library-search-controls.js',
  'js/zones/swatch-popup-render-controls.js',
  'js/zones/swatch-popup-ranking-controls.js',
  'js/zones/swatch-popup-review-controls.js',
  'js/zones/swatch-popup-category-strategy-controls.js',
  'js/zones/swatch-popup-action-controls.js',
  'js/zones/swatch-popup-preview-controls.js',
  'js/zones/swatch-popup-lane-controls.js',
  'js/zones/swatch-popup-health-controls.js',
  'js/zones/swatch-popup-status-controls.js',
  'js/zones/swatch-popup-group-controls.js',
  'js/zones/swatch-popup-selection-controls.js',
  'js/zones/swatch-popup-current-selection-controls.js',
  'js/zones/swatch-popup-grid-builder-controls.js',
  'js/zones/swatch-popup-open-controls.js',
  'js/zones/swatch-popup-lifecycle-controls.js',
  'js/zones/swatch-popup-filter-controls.js',
  'js/zones/finish-library-shell-controls.js',
  'paint-booth-2-state-zones.js'
];
const orderIndexes = orderNeedles.map((needle) => indexOf(html, needle, htmlFile));
for (let i = 1; i < orderIndexes.length; i += 1) {
  assert(orderIndexes[i - 1] < orderIndexes[i], `${orderNeedles[i - 1]} must load before ${orderNeedles[i]}`);
}
assert(html.includes('paint-booth-2-state-zones.js?v=spb-zone-boot-bridge-3-20260522'), `${zonesFile} script cache token must include the zone boot-bridge hotfix`);

const renderInstaller = indexOf(zones, 'window.SPBSwatchPopupRenderControls.install', zonesFile);
const rankingInstaller = indexOf(zones, 'window.SPBSwatchPopupRankingControls.install', zonesFile);
const reviewInstaller = indexOf(zones, 'window.SPBSwatchPopupReviewControls.install', zonesFile);
const categoryStrategyInstaller = indexOf(zones, 'window.SPBSwatchPopupCategoryStrategyControls.install', zonesFile);
const actionInstaller = indexOf(zones, 'window.SPBSwatchPopupActionControls.install', zonesFile);
const previewInstaller = indexOf(zones, 'window.SPBSwatchPopupPreviewControls.install', zonesFile);
const currentSelectionInstaller = indexOf(zones, 'window.SPBSwatchPopupCurrentSelectionControls.install', zonesFile);
const gridBuilderInstaller = indexOf(zones, 'window.SPBSwatchPopupGridBuilderControls.install', zonesFile);
const openInstaller = indexOf(zones, 'window.SPBSwatchPopupOpenControls.install', zonesFile);
const lifecycleInstaller = indexOf(zones, 'window.SPBSwatchPopupLifecycleControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneBaseColorControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneBaseOverlayHsbControls.install', zonesFile);
indexOf(zones, 'window.SPBZonePlacementControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneIntensityControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneUndoHistoryControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneDetailPolishControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneQuickViewSourceControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneListActionControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneDefaultRestoreControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneSwatchIdentityControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneCreateDuplicateControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneCardRenderControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneMultiColorControls.install', zonesFile);
indexOf(zones, 'window.SPBZoneLinkControls.install', zonesFile);
[
  'BaseOverlayState', 'MaterialAssignment', 'Thumbnail', 'UiMode', 'OverlaySpecialPicker', 'RenderChrome', 'StateShape', 'ToastNotification',
  'FinishAssignment', 'Autosave', 'ConfigZoneMap', 'ConfigDom', 'ConfigPreset', 'PresetGallery', 'AutoRestore', 'FinishLibraryShell'
].forEach((name) => indexOf(zones, `window.SPBZone${name}Controls.install`, zonesFile));
assert(renderInstaller < indexOf(zones, 'window.SPBZoneBaseOverlayControls.install', zonesFile), 'render installer must precede base-overlay installer');
assert(renderInstaller < indexOf(zones, 'getOverlayBaseDisplay:', zonesFile), 'render installer must precede getOverlayBaseDisplay dependency injection');
assert(renderInstaller < rankingInstaller, 'render installer must precede ranking installer');
assert(rankingInstaller < reviewInstaller, 'ranking installer must precede review installer');
assert(reviewInstaller < categoryStrategyInstaller, 'review installer must precede category-strategy installer');
assert(categoryStrategyInstaller < actionInstaller, 'category-strategy installer must precede action installer');
assert(actionInstaller < previewInstaller, 'action installer must precede preview installer');
assert(categoryStrategyInstaller < previewInstaller, 'category-strategy installer must precede preview installer');
assert(reviewInstaller < gridBuilderInstaller, 'review installer must precede grid-builder installer');
assert(categoryStrategyInstaller < gridBuilderInstaller, 'category-strategy installer must precede grid-builder installer');
assert(actionInstaller < openInstaller, 'action installer must precede open installer');
assert(actionInstaller < lifecycleInstaller, 'action installer must precede lifecycle installer');
assert(rankingInstaller < gridBuilderInstaller, 'ranking installer must precede grid-builder installer');
assert(previewInstaller < openInstaller, 'preview installer must precede open installer');
assert(currentSelectionInstaller < openInstaller, 'current-selection installer must precede open installer');
assert(gridBuilderInstaller < openInstaller, 'grid-builder installer must precede open installer');
assert(openInstaller < lifecycleInstaller, 'open installer must precede lifecycle installer');
assert(lifecycleInstaller < indexOf(zones, 'window.SPBSwatchPopupSelectionControls.install', zonesFile), 'lifecycle installer must precede selection installer bridge');
['openFilePicker,', 'getPaintCanvas: () => paintCanvas'].forEach((needle) => {
  assert(!zones.includes(needle), `${zonesFile} has unsafe installer dependency shorthand ${needle}`);
});

['getOverlayBaseDisplay', 'triggerPreviewRender', 'soloZone', 'enhanceLibraryCards', 'validatePaintPath', 'assignFinishToSelected', 'renderFinishLibrary'].forEach((name) => {
  assert(!new RegExp(`^\\s+${name},\\s*$`, 'm').test(zones), `${zonesFile} has unsafe installer dependency shorthand ${name}`);
});
[
  'setPickerActiveLaneContext: (gridId, groupName, context) => _setPickerActiveLaneContext',
  'setPickerActiveLaneContext: (lane, item, context) => _setPickerActiveLaneContext',
  'typeof renderFinishLibrary === \'function\''
].forEach((needle) => {
  assert(!zones.includes(needle), `${zonesFile} has boot-unsafe early bridge reference ${needle}`);
});
[
  'function _safeSetPickerActiveLaneContext',
  'function _safeRenderFinishLibrary',
  'function _safeAssignFinishToSelected'
].forEach((needle) => indexOf(zones, needle, zonesFile));

const undeclaredShorthands = Array.from(zones.matchAll(/^\s{8,}([A-Za-z_$][A-Za-z0-9_$]*),\s*$/gm))
  .map((hit) => hit[1])
  .filter((name, index, names) => names.indexOf(name) === index)
  .filter((name) => !new RegExp(`(?:function|const|let|var)\\s+${escapeRegex(name)}\\b`).test(zones));
assert(undeclaredShorthands.length === 0, `${zonesFile} has undeclared installer-style shorthand(s): ${undeclaredShorthands.join(', ')}`);

assert(indexOf(zones, 'const _getFinishLibraryZoneContext = _finishLibraryShellControls', zonesFile) < indexOf(zones, 'const renderFinishLibrary = _finishLibraryShellControls', zonesFile), '_getFinishLibraryZoneContext bridge must be defined before renderFinishLibrary bridge');

[
  'function getOverlayBaseDisplay',
  'function _getSwatchItemById',
  'function collectPickerRankingRows',
  'function _disconnectSwatchPopupLazyLoader',
  'function closeSwatchPicker',
  'function _renderFinishItem',
  'function toggleSection',
  'function applyPreset',
  'function _applyPresetById',
  'function _markZoneBaseOverlayUserEdit',
  'function _normalizeOverlayReactPatternValue',
  'function allocateUnusedPatternForOverlay',
  'function setZoneBase',
  'function setZonePattern',
  'function setZoneWear',
  'function getZonePatternReactOptions',
  'function getOverlayReactToSelectValue'
].forEach((needle) => {
  assert(!zones.includes(needle), `${needle} should stay extracted from ${zonesFile}`);
});

zoneScripts.forEach(({ src }) => {
  [path.join('electron-app/server', src), path.join('electron-app/server/pyserver/_internal', src)]
    .forEach((target) => assert(fs.existsSync(target), `${src} missing runtime mirror ${target}`));
});

console.log('Zone extracted boot contract guard passed.');
