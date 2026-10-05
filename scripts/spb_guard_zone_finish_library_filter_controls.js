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

const moduleFile = 'js/zones/finish-library-filter-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryFilterControls',
  'function _filterBasesByFamily',
  'function _filterBasesByFeaturedCollection',
  'function _filterBasesByQuality',
  'function _filterSpecialsByQuality',
  'function _filterPatternsByGuidance',
  'function _filterByBrowseMode',
  'function _sortByMetadata',
  'function _sortPatternsForZoneContext',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_filterBasesByFamily: _filterBasesByFamily',
  '_filterBasesByFeaturedCollection: _filterBasesByFeaturedCollection',
  '_filterBasesByQuality: _filterBasesByQuality',
  '_filterSpecialsByQuality: _filterSpecialsByQuality',
  '_filterPatternsByGuidance: _filterPatternsByGuidance',
  '_filterByBrowseMode: _filterByBrowseMode',
  '_sortByMetadata: _sortByMetadata',
  '_sortPatternsForZoneContext: _sortPatternsForZoneContext'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-filter-controls.js') &&
    html.indexOf('js/zones/finish-library-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library filter module must load before paint-booth-2-state-zones.js'
);

assert(
  zones.includes('window.SPBZoneFinishLibraryFilterControls.install') &&
    zones.includes('getLibraryBaseFamilyFilter: () => _libraryBaseFamilyFilter') &&
    zones.includes('getLibraryFeaturedCollectionFilter: () => _libraryFeaturedCollectionFilter') &&
    zones.includes('getLibraryBaseQualityFilter: () => _libraryBaseQualityFilter') &&
    zones.includes('getLibrarySpecialQualityFilter: () => _librarySpecialQualityFilter') &&
    zones.includes('getLibraryPatternFilter: () => _libraryPatternFilter') &&
    zones.includes('getLibraryBrowseMode: () => _libraryBrowseMode'),
  'zones installer bridge missing finish library filter dependencies'
);

[
  'function _filterBasesByFamily',
  'function _filterBasesByFeaturedCollection',
  'function _filterBasesByQuality',
  'function _filterSpecialsByQuality',
  'function _filterPatternsByGuidance',
  'function _filterByBrowseMode',
  'function _sortByMetadata',
  'function _sortPatternsForZoneContext'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  'var _libraryBaseFamilyFilter',
  'var _libraryBaseQualityFilter',
  'var _librarySpecialQualityFilter',
  'var _libraryFeaturedCollectionFilter',
  'var _libraryPatternFilter',
  'var _libraryBrowseMode'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} should keep shared state ${needle}`));

console.log('Zone finish library filter guard passed (filter/sort helpers extracted).');
