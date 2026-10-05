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

const moduleFile = 'js/zones/finish-library-guided-catalog-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryGuidedCatalogControls',
  'function _cleanLibraryGroupLabel',
  'function _getLibrarySearchText',
  'function _libraryItemMatchesSearch',
  'function _getLibrarySearchQuery',
  'function _getLibraryGroupPurpose',
  'function _getLibraryFeaturedItems',
  'function _setLibraryActiveGroup',
  'function _renderLibraryRailButton',
  'function _renderGuidedFinishCatalog',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_cleanLibraryGroupLabel: _cleanLibraryGroupLabel',
  '_getLibrarySearchText: _getLibrarySearchText',
  '_libraryItemMatchesSearch: _libraryItemMatchesSearch',
  '_getLibrarySearchQuery: _getLibrarySearchQuery',
  '_getLibraryGroupPurpose: _getLibraryGroupPurpose',
  '_getLibraryFeaturedItems: _getLibraryFeaturedItems',
  '_setLibraryActiveGroup: _setLibraryActiveGroup',
  '_renderLibraryRailButton: _renderLibraryRailButton',
  '_renderGuidedFinishCatalog: _renderGuidedFinishCatalog'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-guided-catalog-controls.js') &&
    html.indexOf('js/zones/finish-library-guided-catalog-controls.js') < html.indexOf('js/zones/finish-library-render-item-controls.js') &&
    html.indexOf('js/zones/finish-library-guided-catalog-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'guided catalog module must load before render-item module and paint-booth-2-state-zones.js'
);

assert(
  zones.indexOf('window.SPBZoneFinishLibraryGuidedCatalogControls.install') >= 0 &&
    zones.indexOf('window.SPBZoneFinishLibraryGuidedCatalogControls.install') < zones.indexOf('window.SPBZoneFinishLibraryRenderItemControls.install'),
  'guided catalog installer must run before render-item installer'
);

[
  'getLibrarySearchQuery: () => _librarySearchQuery',
  'setLibrarySearchQuery: (value) => { _librarySearchQuery = value || \'\'; }',
  'getFavoriteFinishes: () => _favoriteFinishes',
  'getRecentFinishes: () => _recentFinishes',
  'getLibraryActiveGroupByTab: () => _libraryActiveGroupByTab',
  'renderFinishItem: (item, itemType) =>'
].forEach((needle) => assert(zones.includes(needle), `zones installer bridge missing ${needle}`));

[
  'function _cleanLibraryGroupLabel',
  'function _getLibrarySearchText',
  'function _libraryItemMatchesSearch',
  'function _getLibrarySearchQuery',
  'function _getLibraryGroupPurpose',
  'function _getLibraryFeaturedItems',
  'function _setLibraryActiveGroup',
  'function _renderLibraryRailButton',
  'function _renderGuidedFinishCatalog'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  'var _librarySearchQuery',
  'var _libraryActiveGroupByTab',
  'let activeLibraryTab',
  'var _recentFinishes',
  'let _favoriteFinishes'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} should keep shared state ${needle}`));

console.log('Zone finish library guided catalog guard passed (search/category rail helpers extracted).');
