const fs = require('fs');

function read(file) { return fs.readFileSync(file, 'utf8'); }
function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_toast_notification_controls] ${message}`);
    process.exit(1);
  }
}
function indexOf(source, needle, file) {
  const index = source.indexOf(needle);
  assert(index >= 0, `${file} is missing ${needle}`);
  return index;
}

const moduleFile = 'js/zones/zone-toast-notification-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';
const moduleSource = read(moduleFile);
const zonesSource = read(zonesFile);
const htmlSource = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneToastNotificationControls = { install: install }',
  'function showToast(msg, isError, details)',
  'var renderNotify = {',
  'onRenderComplete: function (success, elapsed, zoneCount)',
  'global.showToast = showToast',
  'global.RenderNotify = renderNotify'
].forEach((needle) => indexOf(moduleSource, needle, moduleFile));

[
  'window.SPBZoneToastNotificationControls.install',
  'function showToast(msg, isError, details)',
  'RenderNotify = _zoneToastNotificationControls.RenderNotify'
].forEach((needle) => indexOf(zonesSource, needle, zonesFile));

[
  "const RenderNotify = {",
  "showToast._timer",
  "toast.innerHTML = ''",
  "new Notification(title",
  "Notification.requestPermission();"
].forEach((needle) => assert(!zonesSource.includes(needle), `${zonesFile} still owns extracted toast/notification code ${needle}`));

assert((manifest.files || []).includes(moduleFile), `${moduleFile} is not in ${manifestFile}`);
const stateShapeScript = indexOf(htmlSource, 'js/zones/zone-state-shape-controls.js', htmlFile);
const toastScript = indexOf(htmlSource, 'js/zones/zone-toast-notification-controls.js', htmlFile);
const autosaveScript = indexOf(htmlSource, 'js/zones/zone-autosave-controls.js', htmlFile);
const zonesScript = indexOf(htmlSource, 'paint-booth-2-state-zones.js', htmlFile);
assert(stateShapeScript < toastScript, 'toast module should load after state-shape controls');
assert(toastScript < autosaveScript, 'toast module should load before autosave controls');
assert(toastScript < zonesScript, 'toast module must load before the zone monster script');

console.log('[spb_guard_zone_toast_notification_controls] ok');
