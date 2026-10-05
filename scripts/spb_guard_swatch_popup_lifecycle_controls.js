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

const moduleFile = 'js/zones/swatch-popup-lifecycle-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

assert(mod.includes('SPBSwatchPopupLifecycleControls'), `${moduleFile} missing installer namespace`);
assert(mod.includes('function closeSwatchPicker'), `${moduleFile} missing closeSwatchPicker`);
assert(mod.includes('wireSwatchPopupLifecycleEvents'), `${moduleFile} missing event wiring helper`);
assert(mod.includes('__spbSwatchPopupLifecycleEventsWired'), `${moduleFile} missing duplicate-listener guard`);
assert(mod.includes("e.key === 'Escape'"), `${moduleFile} missing Escape close handler`);
assert(mod.includes('filterSwatchPopup(searchInput.value)'), `${moduleFile} missing type-to-search routing`);
assert(mod.includes('resetSwatchPopupState();'), `${moduleFile} missing state reset`);
assert(mod.includes('Object.assign(global, { closeSwatchPicker: closeSwatchPicker })'), `${moduleFile} does not export closeSwatchPicker`);

assert(
  html.indexOf('js/zones/swatch-popup-selection-controls.js') < html.indexOf('js/zones/swatch-popup-lifecycle-controls.js') &&
    html.indexOf('js/zones/swatch-popup-lifecycle-controls.js') < html.indexOf('js/zones/swatch-popup-filter-controls.js') &&
    html.indexOf('js/zones/swatch-popup-filter-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'swatch popup lifecycle module must load after selection, before filters, and before paint-booth-2-state-zones.js'
);

[
  'window.SPBSwatchPopupLifecycleControls.install',
  'getSwatchPopupState: () => swatchPopupState',
  'resetSwatchPopupState: () =>',
  'toggleSwatchLowScorePanel: (force) => { if (typeof window.toggleSwatchLowScorePanel === \'function\') window.toggleSwatchLowScorePanel(force); }',
  'disconnectSwatchPopupLazyLoader: () => _disconnectSwatchPopupLazyLoader()',
  'setPickerActiveLaneContext: (lane, item, context) => _safeSetPickerActiveLaneContext(lane, item, context)',
  'filterSwatchPopup: (query) => filterSwatchPopup(query)'
].forEach((needle) => assert(zones.includes(needle), `zones swatch-popup lifecycle bridge missing ${needle}`));

assert(!zones.includes('function closeSwatchPicker'), `closeSwatchPicker should not remain in ${zonesFile}`);
assert(!zones.includes("!popup.contains(e.target) && !e.target.closest('.swatch-trigger')"), `swatch outside-click close logic should be extracted from ${zonesFile}`);
assert(!zones.includes("e.key === 'Escape' && swatchPopupState.open"), `swatch Escape close logic should be extracted from ${zonesFile}`);
assert(!zones.includes('filterSwatchPopup(searchInput.value);'), `swatch type-to-search logic should be extracted from ${zonesFile}`);

console.log('Swatch popup lifecycle guard passed (close/reset/listeners extracted).');
