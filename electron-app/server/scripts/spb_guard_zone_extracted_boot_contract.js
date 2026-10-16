#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function assert(condition, message) {
  if (!condition) {
    console.error(message);
    process.exit(1);
  }
}

function indexOf(haystack, needle, label) {
  const index = haystack.indexOf(needle);
  assert(index >= 0, `${label} missing ${needle}`);
  return index;
}

const htmlFile = 'paint-booth-v2.html';
const zonesFile = 'paint-booth-2-state-zones.js';
const manifestFile = 'scripts/runtime-sync-manifest.json';
const mirrorRoot = path.join('electron-app', 'server');
const html = read(htmlFile);
const zones = read(zonesFile);
const manifestFiles = new Set(JSON.parse(read(manifestFile)).files || []);
const zoneScripts = Array.from(
  html.matchAll(/src="(js\/zones\/[^"?]+\.js)\?v=([^"&]+)"/g),
  (match) => ({ src: match[1], token: match[2], index: match.index })
);

assert(zoneScripts.length >= 20, `${htmlFile} has unexpectedly few extracted zone scripts`);
assert(new Set(zoneScripts.map(({ src }) => src)).size === zoneScripts.length, `${htmlFile} loads an extracted zone script more than once`);
zoneScripts.forEach(({ src, token, index }) => {
  assert(token.trim(), `${src} is missing its cache token`);
  assert(index < indexOf(html, zonesFile, htmlFile), `${src} must load before ${zonesFile}`);
  assert(fs.existsSync(src), `${htmlFile} references missing extracted module ${src}`);
  assert(manifestFiles.has(src), `${src} is not covered by ${manifestFile}`);
  assert(fs.existsSync(path.join(mirrorRoot, src)), `${src} is missing its runtime mirror`);
});

[htmlFile, zonesFile].forEach((src) => {
  assert(manifestFiles.has(src), `${src} is not covered by ${manifestFile}`);
});
assert(
  html.includes('paint-booth-2-state-zones.js?v=spb-recovery-workflow-session-router-20260823a'),
  `${zonesFile} script cache token must identify the current recovery/workflow bridge`
);

// Loaded modules are staged extraction seams; these four are the current runtime
// owners. Keep this list explicit so a loaded-but-inactive module is not mistaken
// for an installed owner and a second implementation cannot silently return.
[
  ['js/zones/source-color-apply-controls.js', 'window.SPBZoneSourceColorApplyControls.install', '__spbSourceColorApplyInstalled'],
  ['js/zones/zone-base-overlay-hsb-controls.js', 'window.SPBZoneBaseOverlayHsbControls.install', '__spbZoneBaseOverlayHsbInstalled'],
  ['js/zones/zone-thumbnail-controls.js', 'window.SPBZoneThumbnailControls.install', '__spbZoneThumbnailInstalled'],
  ['js/zones/workflow-controls.js', 'window.SPBZoneWorkflowControls.install', '__spbZoneWorkflowInstalled'],
].forEach(([src, installer, flag]) => {
  assert(indexOf(html, src, htmlFile) < indexOf(html, zonesFile, htmlFile), `${src} must load before ${zonesFile}`);
  indexOf(zones, installer, zonesFile);
  indexOf(zones, flag, zonesFile);
});

['async function refreshThumbnails() {', 'async function checkThumbnailStatus() {'].forEach((needle) => {
  assert(!zones.includes(needle), `${zonesFile} still owns extracted thumbnail helper ${needle}`);
});
assert(!/^\s*(?:openFilePicker|getPaintCanvas),\s*$/m.test(zones), `${zonesFile} passes an unsafe shorthand workflow dependency`);
indexOf(zones, 'zoneHasAnyMaterial: (zone) => zoneHasAnyMaterial(zone)', zonesFile);
indexOf(zones, 'maskAny: (mask) => _maskAny(mask)', zonesFile);

console.log('Zone extracted boot contract guard passed (staged runtime-owner contract).');
