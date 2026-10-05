const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_render_chrome_controls] ${message}`);
    process.exit(1);
  }
}

function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-render-chrome-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneRenderChromeControls = { install: install }',
  'function startRenderTimer()',
  'function stopRenderTimer()',
  'function updateOutputPath()',
  'global.startRenderTimer = startRenderTimer',
  'global.stopRenderTimer = stopRenderTimer',
  'global.updateOutputPath = updateOutputPath'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneRenderChromeControls.install',
  'setInterval: setInterval',
  'clearInterval: clearInterval',
  'updateOutputPath();'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  'function startRenderTimer(',
  'function stopRenderTimer(',
  'function updateOutputPath(',
  'let renderStartTime',
  'const BASE_DRIVER_PATH'
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted render chrome ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const overlayScript = indexOf(htmlSource, 'js/zones/zone-overlay-special-picker-controls.js', htmlFile);
const renderChromeScript = indexOf(htmlSource, 'js/zones/zone-render-chrome-controls.js', htmlFile);
const previewScript = indexOf(htmlSource, 'js/zones/preview-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(overlayScript < renderChromeScript, 'render chrome module should load after overlay-special controls');
assert(renderChromeScript < previewScript, 'render chrome module must load before preview controls');
assert(renderChromeScript < zonesScript, 'render chrome module must load before the zone monster script');

console.log('[spb_guard_zone_render_chrome_controls] ok');
