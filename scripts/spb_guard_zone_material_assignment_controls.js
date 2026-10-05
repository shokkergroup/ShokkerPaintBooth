#!/usr/bin/env node
'use strict';

const fs = require('fs');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(`[spb_guard_zone_material_assignment_controls] ${message}`);
    process.exit(1);
  }
}

const moduleFile = 'js/zones/zone-material-assignment-controls.js';
const zonesFile = 'paint-booth-2-state-zones.js';
const htmlFile = 'paint-booth-v2.html';
const manifestFile = 'scripts/runtime-sync-manifest.json';

const mod = read(moduleFile);
const zones = read(zonesFile);
const html = read(htmlFile);
const manifest = JSON.parse(read(manifestFile));

[
  'global.SPBZoneMaterialAssignmentControls = { install: install }',
  'function setZoneBase',
  'function setZonePattern',
  'function setZoneWear',
  'function getZonePatternReactOptions',
  'function getOverlayReactToSelectValue',
  'Spec Strength was near 0%'
].forEach((needle) => assert(mod.includes(needle), `${moduleFile} missing ${needle}`));

[
  'window.SPBZoneMaterialAssignmentControls.install',
  'const setZoneBase = _zoneMaterialAssignmentControls',
  'const setZonePattern = _zoneMaterialAssignmentControls',
  'const setZoneWear = _zoneMaterialAssignmentControls',
  'const getZonePatternReactOptions = _zoneMaterialAssignmentControls',
  'const getOverlayReactToSelectValue = _zoneMaterialAssignmentControls',
  'applyPickedBaseToZone: (zone, value) => _spbApplyPickedBaseToZone(zone, value)',
  'propagateToLinkedZones: (sourceIndex, props) => propagateToLinkedZones(sourceIndex, props)'
].forEach((needle) => assert(zones.includes(needle), `${zonesFile} missing ${needle}`));

[
  'function setZoneBase',
  'function setZonePattern',
  'function setZoneWear',
  'function getZonePatternReactOptions',
  'function getOverlayReactToSelectValue'
].forEach((needle) => assert(!zones.includes(needle), `${zonesFile} still owns extracted ${needle}`));

const stateScript = html.indexOf('js/zones/zone-base-overlay-state-controls.js');
const assignmentScript = html.indexOf(moduleFile);
const baseOverlayScript = html.indexOf('js/zones/base-overlay-controls.js');
const zonesScript = html.indexOf(zonesFile);
assert(assignmentScript >= 0, `${htmlFile} missing ${moduleFile}`);
assert(stateScript < assignmentScript, `${moduleFile} must load after overlay state controls`);
assert(assignmentScript < baseOverlayScript, `${moduleFile} must load before base overlay controls`);
assert(baseOverlayScript < zonesScript, 'base overlay controls must load before the zone bridge');
assert((manifest.files || []).includes(moduleFile), `${moduleFile} missing from ${manifestFile}`);

console.log('[spb_guard_zone_material_assignment_controls] OK');
