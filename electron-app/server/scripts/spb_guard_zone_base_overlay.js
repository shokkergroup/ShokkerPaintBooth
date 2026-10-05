#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = relPath => fs.readFileSync(path.join(root, relPath), 'utf8');

const html = read('paint-booth-v2.html');
const zones = read('paint-booth-2-state-zones.js');
const overlayModule = read('js/zones/base-overlay-controls.js');

const failures = [];
const suffixes = ['Second', 'Third', 'Fourth', 'Fifth'];
const scaleKinds = ['BaseScale', 'BaseColorScale', 'BaseSpecScale'];
const extractedSetterKinds = ['Base', 'BasePattern', 'BaseBlendMode', 'BaseColorSource', 'BaseColorSourceToOverlay', 'BaseColor'];
const extractedStepperKinds = ['BaseStrength', 'BaseFractalScale'];
const patternSetterKinds = [
  'BasePatternOpacity',
  'BasePatternScale',
  'BasePatternRotation',
  'BasePatternStrength',
  'BasePatternInvert',
  'BasePatternHarden',
  'BasePatternOffsetX',
  'BasePatternOffsetY',
];
const patternStepperKinds = ['BasePatternOpacity', 'BasePatternScale', 'BasePatternRotation', 'BasePatternStrength'];
const alignKinds = ['BaseOverlayWithSelectedPattern'];

if (!(html.indexOf('js/zones/base-overlay-controls.js') < html.indexOf('paint-booth-2-state-zones.js'))) {
  failures.push('paint-booth-v2.html: base overlay controls must load before zones installer');
}
if (!zones.includes('SPBZoneBaseOverlayControls.install')) failures.push('paint-booth-2-state-zones.js: missing base overlay installer bridge');
for (const suffix of suffixes) {
  if (!overlayModule.includes(`${suffix}:`)) failures.push(`js/zones/base-overlay-controls.js: missing ${suffix} tier config`);
  for (const prefix of ['setZone', 'stepZone']) {
    const specFn = `${prefix}${suffix}BaseSpecStrength`;
    if (zones.includes(`function ${specFn}(`)) failures.push(`paint-booth-2-state-zones.js: ${specFn} still lives in monster file`);
    for (const scaleKind of scaleKinds) {
      const scaleFn = `${prefix}${suffix}${scaleKind}`;
      if (zones.includes(`function ${scaleFn}(`)) failures.push(`paint-booth-2-state-zones.js: ${scaleFn} still lives in monster file`);
    }
    for (const kind of extractedStepperKinds) {
      const fn = `${prefix}${suffix}${kind}`;
      if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
    }
    for (const kind of patternStepperKinds) {
      const fn = `${prefix}${suffix}${kind}`;
      if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
    }
    if (prefix === 'setZone') {
      for (const kind of extractedSetterKinds) {
        const fn = `${prefix}${suffix}${kind}`;
        if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
      }
      for (const kind of patternSetterKinds) {
        const fn = `${prefix}${suffix}${kind}`;
        if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
      }
    }
  }
  for (const kind of alignKinds) {
    const fn = `align${suffix}${kind}`;
    if (zones.includes(`function ${fn}(`)) failures.push(`paint-booth-2-state-zones.js: ${fn} still lives in monster file`);
  }
}
if (!overlayModule.includes("window['setZone' + suffix + 'BaseSpecStrength']")) failures.push('base overlay module: dynamic setter install missing');
if (!overlayModule.includes("window['stepZone' + suffix + 'BaseSpecStrength']")) failures.push('base overlay module: dynamic stepper install missing');
if (!overlayModule.includes('OVERLAY_SPEC_TIERS')) failures.push('base overlay module: tier map missing');
if (!overlayModule.includes('OVERLAY_SCALE_TIERS')) failures.push('base overlay module: scale tier map missing');
if (!overlayModule.includes('OVERLAY_BASIC_TIERS')) failures.push('base overlay module: basic tier map missing');
if (!overlayModule.includes('OVERLAY_COLOR_TIERS')) failures.push('base overlay module: color tier map missing');
if (!overlayModule.includes('OVERLAY_PATTERN_TIERS')) failures.push('base overlay module: pattern tier map missing');
if (!overlayModule.includes('OVERLAY_ALIGN_TIERS')) failures.push('base overlay module: align tier map missing');
if (!overlayModule.includes("window['setZone' + suffix + 'Base']")) failures.push('base overlay module: dynamic base selector install missing');
if (!overlayModule.includes("window['setZone' + suffix + 'BasePattern']")) failures.push('base overlay module: dynamic base pattern selector install missing');
if (!overlayModule.includes("window['align' + suffix + 'BaseOverlayWithSelectedPattern']")) failures.push('base overlay module: dynamic align helper install missing');
if (!overlayModule.includes("window['setZone' + suffix + name]")) failures.push('base overlay module: dynamic scale setter install missing');
if (!zones.includes('pushZoneUndoCoalesced') || !zones.includes('propagateToLinkedZones')) failures.push('paint-booth-2-state-zones.js: installer must pass scale deps');
if (!zones.includes('autoAttachOverlayPatternForBlend: _autoAttachOverlayPatternForBlend')) failures.push('paint-booth-2-state-zones.js: installer must pass blend deps');
if (!zones.includes('defaultOverlayReactPatternToIndependent: _defaultOverlayReactPatternToIndependent')) failures.push('paint-booth-2-state-zones.js: installer must pass overlay defaulting dep');
if (!zones.includes('normalizeOverlayReactPatternValue: _normalizeOverlayReactPatternValue')) failures.push('paint-booth-2-state-zones.js: installer must pass overlay pattern normalization dep');
if (!zones.includes('markUserEdit: _markZoneBaseOverlayUserEdit') || !zones.includes('getOverlayBaseDisplay')) failures.push('paint-booth-2-state-zones.js: installer must pass color deps');

if (failures.length) {
  console.error('Zone base overlay guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Zone base overlay guard passed (overlay base selectors, pattern selectors, align helpers, pattern controls, color, basic, spec-strength, and scale handlers extracted).');
