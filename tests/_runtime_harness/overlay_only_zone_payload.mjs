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
      if (inFunc && depth === 0) {
        return src.slice(start, i + 1);
      }
    }
  }
  throw new Error(`unbalanced braces in ${funcName}`);
}

const block = [
  extractTopLevelFunction(API_RENDER_SRC, '_applyBaseColorBranch'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneShouldPreserveScopedBrushExactColorPayload'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyBlendBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyExtraBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyAllExtraBaseOverlays'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasActiveBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneNeedsNeutralBaseAnchor'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasRenderableMaterial'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyBaseColorMode'),
  extractTopLevelFunction(API_RENDER_SRC, 'buildServerZonesForRender'),
].join('\n\n');

const ctx = {
  window: {},
  document: {
    getElementById: (id) => {
      if (id === 'paintCanvas') return { width: 2048, height: 1024 };
      return null;
    },
    createElement: () => ({
      width: 0,
      height: 0,
      getContext: () => ({ clearRect() {}, drawImage() {} }),
      toDataURL: () => 'data:image/png;base64,stub',
    }),
  },
  console: { log() {}, warn() {}, error() {} },
  showToast() {},
  formatColorForServer: (color, zone) => {
    if (zone && zone.colorMode === 'multi') return zone.colors || [];
    return color;
  },
  _applyCustomIntensity() {},
  _mapPatternStack: () => null,
  _resolveFinishColors: () => null,
  _applyAllSpecPatternStacks() {},
  encodeStrengthMapRLE: () => 'strength-map',
  encodeRegionMaskRLE: () => 'region-rle',
  _psdLayers: [],
  Uint8Array,
  Array,
  Object,
  Number,
  JSON,
  parseInt,
};
vm.createContext(ctx);
vm.runInContext(block, ctx, { filename: 'overlay_only_zone_payload.runtime.js' });

const overlayOnlyZone = {
  name: 'Zone 2',
  color: 'remaining',
  intensity: '100',
  secondBase: 'gloss',
  secondBaseColor: '#ff0000',
  secondBaseStrength: 1.0,
  secondBaseSpecStrength: 1.0,
  secondBaseColorSource: 'overlay',
  secondBaseBlendMode: 'tint',
};

const overlayColorSourceOnlyZone = {
  name: 'Zone 3',
  color: 'remaining',
  intensity: '100',
  secondBase: '',
  secondBaseColor: '#00ff00',
  secondBaseStrength: 1.0,
  secondBaseSpecStrength: 0.5,
  secondBaseColorSource: 'overlay',
  secondBaseBlendMode: 'pattern-vivid',
};

const scopedWhiteSpecialOverlayZone = {
  name: 'White Logos',
  colorMode: 'picker',
  color: { color_rgb: [255, 255, 255], tolerance: 8 },
  pickerColor: '#ffffff',
  intensity: '100',
  sourceLayer: 'layer-white',
  spatialMask: [1, 0, 0, 0],
  _scopedBrushAutoBaseColor: true,
  base: 'gloss',
  baseColorMode: 'solid',
  baseColor: '#ffffff',
  secondBase: 'mono:firefly_glow',
  secondBaseColor: '#88cc22',
  secondBaseStrength: 1.0,
  secondBaseSpecStrength: 1.0,
  secondBaseColorSource: 'overlay',
  secondBaseBlendMode: 'pattern-vivid',
};

const specialOverlaySolidColorZone = {
  name: 'Special base solid overlay color',
  color: 'remaining',
  intensity: '100',
  secondBase: 'mono:firefly_glow',
  secondBaseColor: '#2244ff',
  secondBaseStrength: 1.0,
  secondBaseColorSource: 'solid',
  secondBaseHueShift: 42,
  secondBaseSaturation: 18,
  secondBaseBrightness: -12,
};

const legacySpecialOverlaySolidColorZone = {
  name: 'Legacy special base solid overlay color',
  color: 'remaining',
  intensity: '100',
  secondBase: 'mono:firefly_glow',
  secondBaseColor: '#2244ff',
  secondBaseStrength: 1.0,
  secondBaseColorSource: null,
};

const regularOverlaySpecialColorZone = {
  name: 'Regular base special overlay color',
  color: 'remaining',
  intensity: '100',
  secondBase: 'f_metallic',
  secondBaseColor: '#ffffff',
  secondBaseStrength: 1.0,
  secondBaseColorSource: 'mono:firefly_glow',
};

const fifthLayerSpecialColorZone = {
  name: 'Fifth layer special color',
  color: 'remaining',
  intensity: '100',
  fifthBase: 'f_metallic',
  fifthBaseColor: '#ffffff',
  fifthBaseStrength: 0.75,
  fifthBaseColorSource: 'mono:firefly_glow',
  fifthBaseHueShift: -35,
  fifthBaseSaturation: 22,
  fifthBaseBrightness: 9,
};

const emptyZone = {
  name: 'Empty',
  color: 'remaining',
  intensity: '100',
};

const result = {
  overlay_only: ctx.buildServerZonesForRender([overlayOnlyZone]),
  overlay_color_source_only: ctx.buildServerZonesForRender([overlayColorSourceOnlyZone]),
  scoped_white_special_overlay: ctx.buildServerZonesForRender([scopedWhiteSpecialOverlayZone]),
  special_overlay_solid_color: ctx.buildServerZonesForRender([specialOverlaySolidColorZone]),
  legacy_special_overlay_solid_color: ctx.buildServerZonesForRender([legacySpecialOverlaySolidColorZone]),
  regular_overlay_special_color: ctx.buildServerZonesForRender([regularOverlaySpecialColorZone]),
  fifth_layer_special_color: ctx.buildServerZonesForRender([fifthLayerSpecialColorZone]),
  empty_zone_count: ctx.buildServerZonesForRender([emptyZone]).length,
};

console.log(JSON.stringify(result, null, 2));
