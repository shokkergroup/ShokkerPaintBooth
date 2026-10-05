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

const moduleFile = 'js/zones/swatch-popup-current-selection-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

assert(mod.includes('SPBSwatchPopupCurrentSelectionControls'), `${moduleFile} missing installer namespace`);
assert(mod.includes('function getCurrentSwatchPickerId'), `${moduleFile} missing current selection resolver`);
assert(mod.includes("if (type === 'base') return zone.finish ? ('mono:' + zone.finish) : (zone.base || '');"), `${moduleFile} missing base/mono resolver`);
assert(mod.includes("if (type === 'layerSpecialPaint')"), `${moduleFile} missing layer special paint resolver`);
assert(mod.includes('const specialId = getLayerPaintSpecialId();'), `${moduleFile} must resolve layer special paint through injected dependency`);
assert(mod.includes('Object.assign(global, { getCurrentSwatchPickerId: getCurrentSwatchPickerId })'), `${moduleFile} does not export getCurrentSwatchPickerId`);

assert(
  html.indexOf('js/zones/swatch-popup-selection-controls.js') < html.indexOf('js/zones/swatch-popup-current-selection-controls.js') &&
    html.indexOf('js/zones/swatch-popup-current-selection-controls.js') < html.indexOf('js/zones/swatch-popup-open-controls.js') &&
    html.indexOf('js/zones/swatch-popup-open-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'current-selection module must load after selection, before open, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupCurrentSelectionControls.install',
  "getLayerPaintSpecialId: () => (typeof getLayerPaintSpecialId === 'function' ? getLayerPaintSpecialId() : '')",
  'const currentId = getCurrentSwatchPickerId({ zone, type, layerIndex });'
].forEach((needle) => assert(zones.includes(needle), `zones current-selection bridge missing ${needle}`));

[
  "let currentId = '';",
  "currentId = zone.finish ? ('mono:' + zone.finish) : (zone.base || '');",
  "currentId = zone.fifthBaseColorSource || '';",
  "currentId = specialId ? ('mono:' + specialId) : '';"
].forEach((needle) => assert(!zones.includes(needle), `${needle} should be extracted from ${zonesFile}`));

console.log('Swatch popup current-selection guard passed (current id resolver extracted).');
