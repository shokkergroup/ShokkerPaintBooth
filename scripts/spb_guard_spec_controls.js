#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const sourcePath = path.join(root, 'paint-booth-2-state-zones.js');
const source = fs.readFileSync(sourcePath, 'utf8');

const setters = [
  'setSpecPatternLayerProp',
  'setOverlaySpecPatternLayerProp',
  'setThirdOverlaySpecPatternLayerProp',
  'setFourthOverlaySpecPatternLayerProp',
  'setFifthOverlaySpecPatternLayerProp',
];

function functionSlice(name) {
  const start = source.indexOf(`function ${name}(`);
  if (start < 0) return '';
  const next = source.indexOf('\nfunction ', start + 1);
  return source.slice(start, next < 0 ? source.length : next);
}

const failures = [];
for (const setter of setters) {
  const body = functionSlice(setter);
  if (!body) {
    failures.push(`${setter}: missing`);
    continue;
  }
  if (!body.includes('_setSpecPatternStackProp(')) failures.push(`${setter}: missing shared spec-stack setter`);
}

const shared = functionSlice('_setSpecPatternStackProp');
const scheduler = functionSlice('_scheduleSpecPatternLivePreview');
if (!shared.includes('if (live)') || !shared.includes('_scheduleSpecPatternLivePreview(); return;')) failures.push('shared setter: missing live drag branch');
if (!shared.includes('renderZones();')) failures.push('shared setter: missing commit renderZones()');
if (!shared.includes('triggerPreviewRender();')) failures.push('shared setter: missing commit triggerPreviewRender()');
if (shared.indexOf('if (live)') > shared.indexOf('renderZones();')) failures.push('shared setter: live branch must avoid renderZones()');
if (!scheduler.includes('setTimeout') || !scheduler.includes('triggerPreviewRender();')) failures.push('live scheduler: missing debounced preview render');
if (!source.includes("oninput=\"setSpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value), true)")) failures.push('primary opacity slider: missing live setter mode');
if (!source.includes("oninput=\"setSpecPatternLayerProp(${i}, ${si}, 'range', parseInt(this.value), true)")) failures.push('primary range slider: missing live setter mode');
if (!source.includes("onchange=\"setSpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value))")) failures.push('primary opacity slider: missing commit onchange');
if (!source.includes("onchange=\"${setterName}(${zoneIdx}, ${layerIdx}, '${prop}', ${valueExpr})\"")) failures.push('overlay numeric sliders: missing commit onchange');

if (failures.length) {
  console.error('Spec overlay control guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Spec overlay control guard passed (${setters.length} setters share live-drag debounce + commit redraw).`);
