#!/usr/bin/env node
'use strict';

const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_base_overlay_state_controls] ${message}`);
    process.exit(1);
  }
}

const moduleFile = 'js/zones/zone-base-overlay-state-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneBaseOverlayStateControls = { install: install }',
  'function setZoneBaseOverlayEnabled',
  'function normalizeOverlayReactPatternValue',
  'function autoAttachOverlayPatternForBlend',
  'function allocateUnusedPatternForOverlay',
  'renderEnableToggle: renderEnableToggle'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  'window.SPBZoneBaseOverlayStateControls.install',
  'const _markZoneBaseOverlayUserEdit = _zoneBaseOverlayStateControls',
  'const _normalizeOverlayReactPatternValue = _zoneBaseOverlayStateControls',
  'const _autoAttachOverlayPatternForBlend = _zoneBaseOverlayStateControls',
  'const allocateUnusedPatternForOverlay = _zoneBaseOverlayStateControls',
  'autoAttachOverlayPatternForBlend: _autoAttachOverlayPatternForBlend',
  'defaultOverlayReactPatternToIndependent: _defaultOverlayReactPatternToIndependent',
  'normalizeOverlayReactPatternValue: _normalizeOverlayReactPatternValue',
  'markUserEdit: _markZoneBaseOverlayUserEdit'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} missing ${needle}`));

[
  'function _markZoneBaseOverlayUserEdit',
  'function setZoneBaseOverlayEnabled',
  'function _normalizeOverlayReactPatternValue',
  'function _autoAttachOverlayPatternForBlend',
  'function allocateUnusedPatternForOverlay'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted ${needle}`));

const stateScript = html.indexOf(moduleFile);
const baseOverlayScript = html.indexOf('js/zones/base-overlay-controls.js');
const zonesScript = html.indexOf(zonesFile);
assert(stateScript >= 0, `${htmlFile} missing ${moduleFile}`);
assert(stateScript < baseOverlayScript, `${moduleFile} must load before base overlay controls`);
assert(baseOverlayScript < zonesScript, 'base overlay controls must load before the zone bridge');
assert((manifest.files || []).includes(moduleFile), `${moduleFile} missing from ${manifestFile}`);

console.log('[spb_guard_zone_base_overlay_state_controls] OK');
