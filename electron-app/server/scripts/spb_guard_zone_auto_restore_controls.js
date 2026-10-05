const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_auto_restore_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-auto-restore-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneAutoRestoreControls = { install: install }',
  'async function fetchDefaultAssets()',
  'function autoLoadPaintFile(filePath)',
  'async function restorePreferredPaintFile(cfg, opts)',
  'function autoRestore()',
  '_spbFetchDefaultAssets: fetchDefaultAssets',
  '_spbAutoLoadPaintFile: autoLoadPaintFile',
  'autoRestore: autoRestore'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneAutoRestoreControls.install',
  'getAutosaveKey: () => AUTOSAVE_KEY',
  'loadConfigFromObj: (cfg) => loadConfigFromObj(cfg)',
  'loadPaintPreviewFromServer: (path) => (typeof window.loadPaintPreviewFromServer === \'function\' ? window.loadPaintPreviewFromServer(path) : false)'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  "const SPB_LAST_FILE_KEY = 'spb_last_paint_file';",
  'async function _spbFetchDefaultAssets()',
  'function _spbAutoLoadPaintFile(filePath)',
  'function autoRestore() {'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted auto-restore helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const sourceScript = indexOf(htmlSource, 'js/zones/source-color-apply-controls.js', htmlFile);
const autoRestoreScript = indexOf(htmlSource, 'js/zones/zone-auto-restore-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(sourceScript < autoRestoreScript, 'auto-restore module must load after source/apply controls');
assert(autoRestoreScript < zonesScript, 'auto-restore module must load before the zone monster script');

console.log('[spb_guard_zone_auto_restore_controls] ok');
