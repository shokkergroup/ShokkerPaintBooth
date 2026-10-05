const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_thumbnail_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-thumbnail-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneThumbnailControls = { install: install }',
  'async function refreshThumbnails()',
  'async function checkThumbnailStatus()',
  'global.refreshThumbnails = refreshThumbnails',
  'global.checkThumbnailStatus = checkThumbnailStatus'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneThumbnailControls.install',
  'getApiBase: () => ((typeof ShokkerAPI',
  'getZones: () => zones',
  'getSelectedZoneIndex: () => selectedZoneIndex',
  'installLazyLoader: () => { if (typeof _installSwatchPopupLazyLoader ==='
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'async function refreshThumbnails() {',
  'async function checkThumbnailStatus() {'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted thumbnail helper ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const thumbnailScript = indexOf(htmlSource, 'js/zones/zone-thumbnail-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(thumbnailScript < previewScript, 'thumbnail module must load before preview controls');
assert(thumbnailScript < zonesScript, 'thumbnail module must load before the zone monster script');

console.log('[spb_guard_zone_thumbnail_controls] ok');
