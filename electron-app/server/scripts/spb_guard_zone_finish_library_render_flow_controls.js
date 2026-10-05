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

const moduleFile = 'js/zones/finish-library-render-flow-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);

[
  'SPBZoneFinishLibraryRenderFlowControls',
  'function _getFinishLibraryGroupNames',
  'function _applyFinishLibraryDefaultGroups',
  'function _finishLibraryFinalizeRender',
  'function filterFinishes',
  'function toggleCategory',
  'Object.assign(global'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  '_getFinishLibraryGroupNames: _getFinishLibraryGroupNames',
  '_applyFinishLibraryDefaultGroups: _applyFinishLibraryDefaultGroups',
  '_finishLibraryFinalizeRender: _finishLibraryFinalizeRender',
  'filterFinishes: filterFinishes',
  'toggleCategory: toggleCategory'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} does not export ${needle}`));

assert(
  html.includes('js/zones/finish-library-render-flow-controls.js') &&
    html.indexOf('js/zones/finish-library-guided-catalog-controls.js') < html.indexOf('js/zones/finish-library-render-flow-controls.js') &&
    html.indexOf('js/zones/finish-library-render-flow-controls.js') < html.indexOf('js/zones/finish-library-panel-controls.js') &&
    html.indexOf('js/zones/finish-library-render-flow-controls.js') < html.indexOf('paint-booth-2-state-zones.js'),
  'finish library render-flow module must load after guided catalog and before panel/zones'
);

[
  'window.SPBZoneFinishLibraryRenderFlowControls.install',
  'getLastLibraryTabForDefaults: () => _lastLibraryTabForDefaults',
  'setLastLibraryTabForDefaults: (value) => { _lastLibraryTabForDefaults = value; }',
  'getExpandedGroups: () => _expandedGroups',
  'getCategoryCollapsed: () => categoryCollapsed'
].forEach((needle) => assert(zones.includes(needle), `zones render-flow bridge missing ${needle}`));

[
  'const groupNames = _getFinishLibraryGroupNames(activeLibraryTab, groupMap);',
  '_applyFinishLibraryDefaultGroups(activeLibraryTab, groupNames);',
  '_finishLibraryFinalizeRender({ container, html, activeTab, groupMap, groupNames, activeTabId: activeLibraryTab, itemType: activeTab.type });'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} renderFinishLibrary does not use extracted flow helper ${needle}`));

[
  'function filterFinishes',
  'function toggleCategory',
  'const baseGroupOrder =',
  'renderSmartFilterChips(catalogResults)'
].forEach((needle) => assert(!zones.includes(needle), `${needle} should not remain in ${zonesFile}`));

console.log('Zone finish library render-flow guard passed (group/default/finalize handlers extracted).');
