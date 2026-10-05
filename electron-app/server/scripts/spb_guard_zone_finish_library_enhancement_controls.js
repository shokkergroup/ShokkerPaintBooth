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

const moduleFile = 'js/zones/finish-library-enhancement-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryEnhancementControls',
  'function enhanceLibraryCards',
  'function addInspireButtonToActiveFinishRow',
  'function inspireFromCurrentZone',
  'function attachZoneFinishHoverPreview',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  'enhanceLibraryCards: enhanceLibraryCards',
  'addInspireButtonToActiveFinishRow: addInspireButtonToActiveFinishRow',
  'inspireFromCurrentZone: inspireFromCurrentZone',
  'attachZoneFinishHoverPreview: attachZoneFinishHoverPreview'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-enhancement-controls.js') &&
    html.indexOf('js/zones/finish-library-enhancement-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library enhancement module must load before paint-booth-2-state-zones.js'
);

assert(
  zones.includes('window.SPBZoneFinishLibraryEnhancementControls.install') &&
    zones.includes('getSelectedZoneIndex: () => selectedZoneIndex') &&
    zones.includes('getZoneColorHex: (zone) =>'),
  'zones installer bridge missing finish library enhancement dependencies'
);

[
  'function enhanceLibraryCards',
  'function addInspireButtonToActiveFinishRow',
  'function inspireFromCurrentZone',
  'function attachZoneFinishHoverPreview',
  'RICHER LIBRARY CARDS (Run 15)'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

console.log('Zone finish library enhancement guard passed (library card/hover helper island extracted).');
