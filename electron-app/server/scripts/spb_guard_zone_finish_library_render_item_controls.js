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

const moduleFile = 'js/zones/finish-library-render-item-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryRenderItemControls',
  'function _loadRegistryStatus',
  'function _renderFinishItem',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_loadRegistryStatus: _loadRegistryStatus',
  '_renderFinishItem: _renderFinishItem'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-render-item-controls.js') &&
    html.indexOf('js/zones/finish-library-render-item-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library render-item module must load before paint-booth-2-state-zones.js'
);

assert(
  zones.includes('window.SPBZoneFinishLibraryRenderItemControls.install') &&
    zones.includes('getRegisteredFinishes: () => _registeredFinishes') &&
    zones.includes('setRegisteredFinishes: (value) => { _registeredFinishes = value; }') &&
    zones.includes('getRegistryLoadAttempted: () => _registryLoadAttempted') &&
    zones.includes('setRegistryLoadAttempted: (value) => { _registryLoadAttempted = !!value; }') &&
    zones.includes('getLibrarySearchText: (item, type) => _getLibrarySearchText(item, type)'),
  'zones installer bridge missing finish library render-item dependencies'
);

[
  'function _loadRegistryStatus',
  'function _renderFinishItem'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

[
  'var _registeredFinishes',
  'var _registryLoadAttempted',
  'function _getFinishLibraryZoneContext'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} should keep shared state ${needle}`));

console.log('Zone finish library render item guard passed (registry preload/card renderer extracted).');
