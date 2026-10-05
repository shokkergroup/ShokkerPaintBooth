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

const moduleFile = 'js/zones/finish-library-state-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryStateControls',
  'function _trackRecentFinish',
  'function renderQuickAccessBar',
  'function toggleFavorite',
  'function isFavorite',
  'function toggleFavoritesOnly',
  'function toggleLibraryGroup',
  'function expandAllLibraryGroups',
  'function collapseAllLibraryGroups',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_trackRecentFinish: _trackRecentFinish',
  'renderQuickAccessBar: renderQuickAccessBar',
  'toggleFavorite: toggleFavorite',
  'isFavorite: isFavorite',
  'toggleFavoritesOnly: toggleFavoritesOnly',
  'toggleLibraryGroup: toggleLibraryGroup',
  'expandAllLibraryGroups: expandAllLibraryGroups',
  'collapseAllLibraryGroups: collapseAllLibraryGroups'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-state-controls.js') &&
    html.indexOf('js/zones/finish-library-state-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library state module must load before paint-booth-2-state-zones.js'
);

assert(
  zones.includes('window.SPBZoneFinishLibraryStateControls.install') &&
    zones.includes('getRecentFinishes: () => _recentFinishes') &&
    zones.includes('getFavoriteFinishes: () => _favoriteFinishes') &&
    zones.includes('getExpandedGroups: () => _expandedGroups'),
  'zones installer bridge missing finish library state dependencies'
);

[
  'function _trackRecentFinish',
  'function renderQuickAccessBar',
  'function toggleFavorite',
  'function isFavorite',
  'function toggleFavoritesOnly',
  'function toggleLibraryGroup',
  'function expandAllLibraryGroups',
  'function collapseAllLibraryGroups'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  'var _recentFinishes',
  'let _favoriteFinishes',
  'let _showFavoritesOnly',
  'const _expandedGroups'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} should keep shared state ${needle}`));

console.log('Zone finish library state guard passed (recent/favorites/group helpers extracted).');
