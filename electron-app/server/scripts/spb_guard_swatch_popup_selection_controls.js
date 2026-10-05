#!/usr/bin/env node

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

const moduleFile = 'js/zones/swatch-popup-selection-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

assert(mod.includes('SPBSwatchPopupSelectionControls'), `${moduleFile} missing installer namespace`);
assert(mod.includes('function selectSwatchItem'), `${moduleFile} missing selectSwatchItem`);
assert(mod.includes('selectSwatchItem: selectSwatchItem'), `${moduleFile} does not export selectSwatchItem`);
assert(
  html.indexOf('js/zones/swatch-popup-group-controls.js') < html.indexOf('js/zones/swatch-popup-selection-controls.js') &&
    html.indexOf('js/zones/swatch-popup-selection-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup selection module must load after group, before filters, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupSelectionControls.install',
  'getSwatchPopupState: () => swatchPopupState',
  'closeSwatchPicker: () => closeSwatchPicker()',
  'openDualShiftModal: (zoneIndex) => { if (typeof openDualShiftModal === \'function\') openDualShiftModal(zoneIndex); }',
  'setZoneBase: (zoneIndex, id) => { if (typeof setZoneBase === \'function\') setZoneBase(zoneIndex, id); }',
  'setZonePattern: (zoneIndex, id) => { if (typeof setZonePattern === \'function\') setZonePattern(zoneIndex, id); }',
  'setPatternLayerId: (zoneIndex, layerIndex, id) => { if (typeof setPatternLayerId === \'function\') setPatternLayerId(zoneIndex, layerIndex, id); }',
  'setZoneSecondBase: (zoneIndex, id) => { if (typeof setZoneSecondBase === \'function\') setZoneSecondBase(zoneIndex, id); }',
  'setZoneThirdBase: (zoneIndex, id) => { if (typeof setZoneThirdBase === \'function\') setZoneThirdBase(zoneIndex, id); }',
  'setZoneFourthBase: (zoneIndex, id) => { if (typeof setZoneFourthBase === \'function\') setZoneFourthBase(zoneIndex, id); }',
  'setZoneFifthBase: (zoneIndex, id) => { if (typeof setZoneFifthBase === \'function\') setZoneFifthBase(zoneIndex, id); }',
  'setZoneBaseColorSource: (zoneIndex, id) => { if (typeof window !== \'undefined\' && typeof window.setZoneBaseColorSource === \'function\') window.setZoneBaseColorSource(zoneIndex, id); }',
  'setZoneSecondBaseColorSource: (zoneIndex, id) => { if (typeof setZoneSecondBaseColorSource === \'function\') setZoneSecondBaseColorSource(zoneIndex, id); }',
  'setZoneSecondBaseColor: (zoneIndex, color) => { if (typeof setZoneSecondBaseColor === \'function\') setZoneSecondBaseColor(zoneIndex, color); }',
  'setZoneThirdBaseColorSource: (zoneIndex, id) => { if (typeof setZoneThirdBaseColorSource === \'function\') setZoneThirdBaseColorSource(zoneIndex, id); }',
  'setZoneFourthBaseColorSource: (zoneIndex, id) => { if (typeof setZoneFourthBaseColorSource === \'function\') setZoneFourthBaseColorSource(zoneIndex, id); }',
  'setZoneFifthBaseColorSource: (zoneIndex, id) => { if (typeof setZoneFifthBaseColorSource === \'function\') setZoneFifthBaseColorSource(zoneIndex, id); }',
  'setZoneSecondBasePattern: (zoneIndex, id) => { if (typeof setZoneSecondBasePattern === \'function\') setZoneSecondBasePattern(zoneIndex, id); }',
  'setZoneThirdBasePattern: (zoneIndex, id) => { if (typeof setZoneThirdBasePattern === \'function\') setZoneThirdBasePattern(zoneIndex, id); }',
  'setLayerPaintSpecial: (id) => { if (typeof setLayerPaintSpecial === \'function\') setLayerPaintSpecial(id); }'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup selection bridge missing ${needle}`));

assert(!zones.includes('function selectSwatchItem'), `selectSwatchItem should not remain in ${zonesFile}`);

[
  "id === 'dualshift_custom'",
  "type === 'overlayBaseColor'",
  "type === 'layerSpecialPaint'",
  'closeSwatchPicker();'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing route behavior ${needle}`));

console.log('Swatch popup selection guard passed (selection routing extracted).');
