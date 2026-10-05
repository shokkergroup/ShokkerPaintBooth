#!/usr/bin/env node
const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_finish_library_shell_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/finish-library-shell-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneFinishLibraryShellControls = { install: install }',
  'function getFinishQualityFlags(id)',
  'function getMetadata(id)',
  'function getFinishLibraryZoneContext()',
  'function renderFinishLibrary()',
  'renderFinishLibrary: renderFinishLibrary'
].forEach((needle) => indexOf(mod, needle, moduleFile));

[
  'window.SPBZoneFinishLibraryShellControls.install',
  'const getFinishQualityFlags = _finishLibraryShellControls',
  'const _getMetadata = _finishLibraryShellControls',
  'const _getFinishLibraryZoneContext = _finishLibraryShellControls',
  'const renderFinishLibrary = _finishLibraryShellControls',
  'window.renderFinishLibrary = renderFinishLibrary'
].forEach((needle) => indexOf(zones, needle, zonesFile));

[
  'function getFinishQualityFlags(id) {',
  'function _getMetadata(id) {',
  'function _getFinishLibraryZoneContext() {',
  'function renderFinishLibrary() {',
  'const FINISH_BROWSER_QUALITY_FLAGS = {'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted shell helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} missing from ${manifestFile}`);
const filterIndex = indexOf(html, 'js/zones/finish-library-filter-controls.js', htmlFile);
const shellIndex = indexOf(html, moduleFile, htmlFile);
const zonesIndex = indexOf(html, zonesFile, htmlFile);
assert(filterIndex < shellIndex, 'finish library shell must load after filter helpers');
assert(shellIndex < zonesIndex, 'finish library shell must load before the zone bridge');

console.log('[spb_guard_zone_finish_library_shell_controls] OK');
