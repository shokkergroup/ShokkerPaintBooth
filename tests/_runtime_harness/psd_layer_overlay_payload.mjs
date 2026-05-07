import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const API_RENDER_SRC = readFileSync(join(REPO, 'paint-booth-5-api-render.js'), 'utf8');

function extractTopLevelFunction(src, funcName) {
  const needle = `function ${funcName}(`;
  const start = src.indexOf(needle);
  if (start === -1) throw new Error(`function not found: ${funcName}`);
  let depth = 0;
  let inFunc = false;
  for (let i = start; i < src.length; i += 1) {
    const c = src[i];
    if (c === '{') {
      depth += 1;
      inFunc = true;
    } else if (c === '}') {
      depth -= 1;
      if (inFunc && depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error(`unbalanced braces in ${funcName}`);
}

const block = [
  extractTopLevelFunction(API_RENDER_SRC, '_mapSpecPatternEntry'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyBaseColorBranch'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneShouldPreserveScopedBrushExactColorPayload'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyBlendBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyExtraBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyAllExtraBaseOverlays'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasActiveBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneNeedsNeutralBaseAnchor'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasImportedSpecSource'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneSpecSourceStrength'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyZoneSpecSource'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasRenderableMaterial'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyBaseColorMode'),
  'const SPEC_PATTERN_STACK_TIERS = [["specPatternStack","spec_pattern_stack"],["overlaySpecPatternStack","overlay_spec_pattern_stack"],["thirdOverlaySpecPatternStack","third_overlay_spec_pattern_stack"],["fourthOverlaySpecPatternStack","fourth_overlay_spec_pattern_stack"],["fifthOverlaySpecPatternStack","fifth_overlay_spec_pattern_stack"]];',
  extractTopLevelFunction(API_RENDER_SRC, '_applyAllSpecPatternStacks'),
  extractTopLevelFunction(API_RENDER_SRC, 'buildServerZonesForRender'),
].join('\n\n');

const drawCalls = [];
const ctx = {
  window: {
    getLayerVisibleContributionMask(layer, w, h) {
      assert.equal(layer.id, 'psd-layer-main');
      assert.equal(w, 8);
      assert.equal(h, 4);
      const mask = new Uint8Array(w * h);
      mask.fill(1);
      return mask;
    },
  },
  document: {
    getElementById: (id) => {
      if (id === 'paintCanvas') return { width: 8, height: 4 };
      return null;
    },
    createElement: () => ({
      width: 0,
      height: 0,
      getContext: () => ({
        clearRect() {},
        drawImage(img, x, y) {
          drawCalls.push({ id: img.id, x, y });
        },
      }),
      toDataURL: () => 'data:image/png;base64,layer-rgb-png',
    }),
  },
  console: { log() {}, warn() {}, error() {} },
  showToast() {},
  formatColorForServer: (color, zone) => {
    if (zone && zone.colorMode === 'multi') return zone.colors || [];
    return color;
  },
  _applyCustomIntensity() {},
  _mapPatternStack: (stack) => (stack || []).map((layer) => ({ id: layer.id || layer.pattern, blend_mode: layer.blendMode || 'normal' })),
  _resolveFinishColors: () => null,
  encodeStrengthMapRLE: () => 'strength-map',
  encodeRegionMaskRLE: (mask, w, h) => `rle:${w}x${h}:${Array.from(mask).reduce((acc, value) => acc + Number(value || 0), 0)}`,
  _psdLayers: [
    { id: 'psd-layer-main', name: 'Main Logos', bbox: [2, 1, 6, 3], img: { id: 'layer-img-main' } },
  ],
  Uint8Array,
  Array,
  Object,
  Number,
  JSON,
  Math,
  parseInt,
};

vm.createContext(ctx);
vm.runInContext(block, ctx, { filename: 'psd_layer_overlay_payload.runtime.js' });

const zone = {
  name: 'PSD Matrix Zone',
  colorMode: 'picker',
  color: { color_rgb: [255, 255, 255], tolerance: 9 },
  pickerColor: '#ffffff',
  intensity: '100',
  sourceLayer: 'psd-layer-main',
  base: 'gloss',
  baseColorMode: 'solid',
  baseColor: '#fefefe',
  pattern: 'checker_warp',
  patternStack: [{ id: 'data_mesh', blendMode: 'multiply' }],
  specPatternStack: [{ pattern: 'crushed_glass', opacity: 80, channels: 'MR', scale: 1.25 }],
  overlaySpecPatternStack: [{ pattern: 'sparkle_galaxy_swirl', opacity: 45, channels: 'M', rotation: 15 }],
  thirdOverlaySpecPatternStack: [{ pattern: 'radiator_grille_mesh', opacity: 30, channels: 'R', offsetX: 0.2 }],
  fourthOverlaySpecPatternStack: [{ pattern: 'spec_carbon_weave', opacity: 55, channels: 'G', scale: 0.75 }],
  fifthOverlaySpecPatternStack: [{ pattern: 'spec_diffraction_grating', opacity: 25, channels: 'C', rotation: -22 }],
  secondBase: 'mono:firefly_glow',
  secondBaseColor: '#88cc22',
  secondBaseStrength: 0.8,
  secondBaseSpecStrength: 0.7,
  secondBaseColorSource: 'overlay',
  secondBaseBlendMode: 'pattern-vivid',
  secondBasePattern: 'hex_grid',
  secondBaseHueShift: 12,
  secondBaseSaturation: 8,
  secondBaseBrightness: -4,
  thirdBase: 'f_metallic',
  thirdBaseColor: '#ffffff',
  thirdBaseStrength: 0.5,
  thirdBaseColorSource: 'mono:firefly_glow',
  thirdBaseBlendMode: 'tint',
  fourthBase: 'gloss',
  fourthBaseColor: '#223344',
  fourthBaseStrength: 0.35,
  fourthBaseColorSource: 'solid',
  fourthBaseBlendMode: 'noise',
  fourthBasePattern: 'speed_lines',
  fourthBasePatternOpacity: 65,
  fourthBasePatternScale: 1.4,
  fourthBasePatternFlipH: true,
  fifthBase: 'f_metallic',
  fifthBaseColor: '#ffffff',
  fifthBaseStrength: 0.25,
  fifthBaseColorSource: 'mono:firefly_glow',
  fifthBaseBlendMode: 'pattern-vivid',
  fifthBaseHueShift: -18,
  fifthBaseSaturation: 11,
  fifthBaseBrightness: 7,
};

const [payload] = ctx.buildServerZonesForRender([zone]);
const plain = (value) => JSON.parse(JSON.stringify(value));

assert.equal(payload.source_layer_mask, 'rle:8x4:32');
assert.equal(payload.source_layer_rgb_png, 'layer-rgb-png');
assert.deepEqual(drawCalls, [{ id: 'layer-img-main', x: 2, y: 1 }]);

assert.equal(payload.base, 'gloss');
assert.equal(payload.base_color_mode, 'solid');
assert.deepEqual(plain(payload.base_color), [254 / 255, 254 / 255, 254 / 255]);
assert.equal(payload.pattern, 'checker_warp');
assert.deepEqual(plain(payload.pattern_stack), [{ id: 'data_mesh', blend_mode: 'multiply' }]);

assert.equal(payload.spec_pattern_stack[0].pattern, 'crushed_glass');
assert.equal(payload.spec_pattern_stack[0].opacity, 0.8);
assert.equal(payload.spec_pattern_stack[0].scale, 1.25);
assert.equal(payload.overlay_spec_pattern_stack[0].pattern, 'sparkle_galaxy_swirl');
assert.equal(payload.overlay_spec_pattern_stack[0].channels, 'M');
assert.equal(payload.third_overlay_spec_pattern_stack[0].pattern, 'radiator_grille_mesh');
assert.equal(payload.third_overlay_spec_pattern_stack[0].channels, 'R');
assert.equal(payload.fourth_overlay_spec_pattern_stack[0].pattern, 'spec_carbon_weave');
assert.equal(payload.fourth_overlay_spec_pattern_stack[0].channels, 'G');
assert.equal(payload.fifth_overlay_spec_pattern_stack[0].pattern, 'spec_diffraction_grating');
assert.equal(payload.fifth_overlay_spec_pattern_stack[0].channels, 'C');

assert.equal(payload.second_base, 'mono:firefly_glow');
assert.equal(payload.second_base_color_source, 'overlay');
assert.equal(payload.second_base_blend_mode, 'pattern-vivid');
assert.equal(payload.second_base_pattern, 'hex_grid');
assert.equal(payload.second_base_hue_shift, 12);
assert.equal(payload.second_base_saturation, 8);
assert.equal(payload.second_base_brightness, -4);

assert.equal(payload.third_base, 'f_metallic');
assert.equal(payload.third_base_color_source, 'mono:firefly_glow');
assert.equal(payload.third_base_blend_mode, 'tint');
assert.equal(payload.third_base_pattern, '__none__');
assert.equal(payload.fourth_base, 'gloss');
assert.equal(payload.fourth_base_color_source, 'solid');
assert.equal(payload.fourth_base_blend_mode, 'noise');
assert.equal(payload.fourth_base_pattern, 'speed_lines');
assert.equal(payload.fourth_base_pattern_opacity, 0.65);
assert.equal(payload.fourth_base_pattern_scale, 1.4);
assert.equal(payload.fourth_base_pattern_flip_h, true);
assert.equal(payload.fifth_base, 'f_metallic');
assert.equal(payload.fifth_base_color_source, 'mono:firefly_glow');
assert.equal(payload.fifth_base_blend_mode, 'pattern-vivid');
assert.equal(payload.fifth_base_pattern, '__none__');
assert.equal(payload.fifth_base_hue_shift, -18);
assert.equal(payload.fifth_base_saturation, 11);
assert.equal(payload.fifth_base_brightness, 7);

console.log(JSON.stringify({ ok: true, payload }));
