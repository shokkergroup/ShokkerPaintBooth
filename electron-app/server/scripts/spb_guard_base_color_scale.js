#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function functionSlice(source, name) {
  const start = source.indexOf(`function ${name}(`);
  if (start < 0) return '';
  const next = source.indexOf('\nfunction ', start + 1);
  return source.slice(start, next < 0 ? source.length : next);
}

const zones = read('paint-booth-2-state-zones.js');
const html = read('paint-booth-v2.html');
const baseMaterial = read('js/zones/base-material-controls.js');
const canvas = read('paint-booth-3-canvas.js');
const api = read('paint-booth-5-api-render.js');
const engine = read('shokker_engine_v2.py');
const compose = read('engine/compose.py');

const failures = [];

for (const fn of ['setZoneBaseRotation', 'stepZoneBaseRotation', 'resetZoneBaseRotation', 'setZoneBaseScale', 'stepZoneBaseScale', 'resetZoneBaseScale', 'setZoneBaseColorScale', 'stepZoneBaseColorScale', 'resetZoneBaseColorScale', 'setZoneBaseColorRotation', 'resetZoneBaseColorRotation']) {
  if (!baseMaterial.includes(`window.${fn}`)) failures.push(`js/zones/base-material-controls.js: missing extracted ${fn}()`);
}
for (const fn of ['setZoneBaseOffsetX', 'setZoneBaseOffsetY', 'setZoneBaseFlipH', 'setZoneBaseFlipV']) {
  if (!baseMaterial.includes(`window.${fn}`)) failures.push(`js/zones/base-material-controls.js: missing extracted ${fn}()`);
  if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: duplicate ${fn} still lives in monster file`);
}
for (const fn of ['setZoneSpecRotation', 'resetZoneSpecRotation', 'setZoneSpecScale', 'stepZoneSpecScale', 'resetZoneSpecScale', 'matchZoneSpecToBase', 'matchZoneColorToBase', 'matchZoneAllTransformsToBase', 'matchZoneSpecToColor']) {
  if (!baseMaterial.includes(`window.${fn}`)) failures.push(`js/zones/base-material-controls.js: missing extracted ${fn}()`);
}
if (!zones.includes('id="detBaseColorScaleVal${i}"')) failures.push('paint-booth-2-state-zones.js: missing Color Scale value pill');
if (!zones.includes('id="detBaseColorRotVal${i}"')) failures.push('paint-booth-2-state-zones.js: missing Color Rotate value input');
if ((zones.match(/function setZoneBaseRotation\(/g) || []).length) failures.push('paint-booth-2-state-zones.js: duplicate setZoneBaseRotation still lives in monster file');
if (!(html.indexOf('js/zones/base-material-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) failures.push('paint-booth-v2.html: base material controls must load before zones installer');
if (!zones.includes('SPBZoneBaseMaterialControls.install')) failures.push('paint-booth-2-state-zones.js: missing base material control installer bridge');
if (!baseMaterial.includes('window.setZoneBaseStrength') || !baseMaterial.includes('window.setZoneBaseSpecBlendMode')) failures.push('js/zones/base-material-controls.js: missing extracted primary base material handlers');
if (!zones.includes("((zone.baseColorMode || 'source') !== 'source' || !!zone.baseColorSource)")) failures.push('paint-booth-2-state-zones.js: Color Rotate/Scale hidden for saved special color source');
if (!(zones.indexOf('Base Scale') < zones.indexOf('Color Rotate') && zones.indexOf('Color Rotate') < zones.indexOf('Color Scale') && zones.indexOf('Color Scale') < zones.indexOf('Spec Rotate'))) failures.push('paint-booth-2-state-zones.js: transform stack order is not Base -> Color -> Spec');
if (!(zones.indexOf('Brightness') < zones.indexOf('Base Strength') && zones.indexOf('Base Strength') < zones.indexOf('Spec Blend') && zones.indexOf('Spec Blend') < zones.indexOf('Base Rotate'))) failures.push('paint-booth-2-state-zones.js: Base/Spec Strength and Spec Blend must stay under Brightness, before transform controls');
if (!zones.includes('Base -> Color') || !zones.includes('Color -> Spec')) failures.push('paint-booth-2-state-zones.js: transform align buttons missing readable labels');
if (!zones.includes('baseColorScale: 1')) failures.push('paint-booth-2-state-zones.js: missing baseColorScale default');
if (!zones.includes('baseColorRotation: 0')) failures.push('paint-booth-2-state-zones.js: missing baseColorRotation default');
if (!zones.includes("'baseColorScale'")) failures.push('paint-booth-2-state-zones.js: missing baseColorScale linked/DNA key');
if (!zones.includes("'baseColorRotation'")) failures.push('paint-booth-2-state-zones.js: missing baseColorRotation linked/DNA key');

if (!api.includes('zoneObj.base_color_scale')) failures.push('paint-booth-5-api-render.js: API helper does not serialize base_color_scale');
if (!api.includes('zoneObj.base_color_rotation')) failures.push('paint-booth-5-api-render.js: API helper does not serialize base_color_rotation');
if (!canvas.includes('zoneObj.base_color_scale')) failures.push('paint-booth-3-canvas.js: direct canvas payload does not serialize base_color_scale');
if (!canvas.includes('zoneObj.base_color_rotation')) failures.push('paint-booth-3-canvas.js: direct canvas payload does not serialize base_color_rotation');
if (!engine.includes('zone.get("base_color_scale", zone.get("baseColorScale", 1.0))')) {
  failures.push('shokker_engine_v2.py: does not read snake/camel base color scale payload');
}
if (!engine.includes('zone.get("base_color_rotation", zone.get("baseColorRotation"')) {
  failures.push('shokker_engine_v2.py: does not read snake/camel base color rotation payload');
}
if (!engine.includes('"base_color_scale": _v6kw.get("base_color_scale", 1.0)')) {
  failures.push('shokker_engine_v2.py: v6 paint payload does not forward base_color_scale');
}
if (!engine.includes('"base_color_rotation": _v6kw.get("base_color_rotation", 0)')) {
  failures.push('shokker_engine_v2.py: v6 paint payload does not forward base_color_rotation');
}
if ((engine.match(/"monolithic_registry": _v6kw\.get\("monolithic_registry"\)/g) || []).length < 2) {
  failures.push('shokker_engine_v2.py: duplicate v6 paint paths do not forward monolithic_registry for From Special color sources');
}
if (!compose.includes('base_color_scale=1.0')) failures.push('engine/compose.py: compose_paint_mod lacks base_color_scale parameter');
if (!compose.includes('base_color_rotation=None')) failures.push('engine/compose.py: compose_paint_mod lacks base_color_rotation parameter');
if (!compose.includes('base_color_scale = float(kwargs.pop("base_color_scale", 1.0))')) {
  failures.push('engine/compose.py: stacked compose does not consume base_color_scale kwarg');
}
if (!compose.includes('base_color_rotation = kwargs.pop("base_color_rotation", None)')) {
  failures.push('engine/compose.py: stacked compose does not consume base_color_rotation kwarg');
}
if (!compose.includes('base_scale=base_color_scale')) {
  failures.push('engine/compose.py: base color override is still coupled to base_scale');
}

if (failures.length) {
  console.error('Base color scale guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Base color scale guard passed (UI -> payload -> engine path intact).');
