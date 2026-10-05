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
  extractTopLevelFunction(API_RENDER_SRC, '_normalizeZoneMaterialStack'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasMaterialStack'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyZoneMaterialStack'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasRenderableMaterial'),
  extractTopLevelFunction(API_RENDER_SRC, 'buildServerZonesForRender'),
].join('\n\n');

const ctx = {
  window: {},
  document: {
    getElementById: () => null,
    createElement: () => ({
      width: 0,
      height: 0,
      getContext: () => ({ clearRect() {}, drawImage() {} }),
      toDataURL: () => 'data:image/png;base64,stub',
    }),
  },
  console: { log() {}, warn() {}, error() {} },
  BASES_BY_ID: { chrome: {}, matte: {}, gloss: {} },
  MONOLITHICS_BY_ID: { acid_etched_glass: {}, acid_trip: {} },
  formatColorForServer: (color) => color,
  _applyCustomIntensity() {},
  _mapPatternStack: () => null,
  _resolveFinishColors: () => null,
  _zoneNeedsNeutralBaseAnchor: () => false,
  _zoneHasImportedSpecSource: () => false,
  _applyZoneSpecSource() {},
  _applySpecMaterialRemap() {},
  _applySpecMaterialOverride() {},
  _applySpecLightingMask() {},
  _applyBaseColorMode() {},
  _applyAllSpecPatternStacks() {},
  _applyBlendBaseOverlay() {},
  _applyAllExtraBaseOverlays() {},
  _encodeZoneApplyMasks() {},
  _zoneShouldFitIntoApplyArea: () => false,
  _psdLayers: [],
  encodeStrengthMapRLE: () => 'strength-rle',
  encodeRegionMaskRLE: () => 'region-rle',
  Uint8Array,
  Array,
  Object,
  Number,
  JSON,
  String,
  Math,
  parseInt,
};
vm.createContext(ctx);
vm.runInContext(block, ctx, { filename: 'easy_whole_car_material_stack_payload.runtime.js' });

const clientZone = {
  name: 'Whole Car Material Mix',
  color: 'everything',
  intensity: '100',
  materialStack: [
    // Mix shares are one exact 100% recipe. Overall strength is a separate
    // master control and must never be inferred from these row sliders.
    { id: 'chrome', registryType: 'base', weight: 60 },
    { id: 'acid_trip', registryType: 'monolithic', weight: 40 },
  ],
  materialStackAmount: 0.5,
  materialScale: 0.5,
};

function captureError(fn) {
  try {
    fn();
    return null;
  } catch (error) {
    return String(error && error.message ? error.message : error);
  }
}

const result = {
  normalized: ctx._normalizeZoneMaterialStack(clientZone),
  payload: ctx.buildServerZonesForRender([clientZone]),
  quarter_amount_payload: ctx.buildServerZonesForRender([{
    ...clientZone,
    materialStack: [{ id: 'chrome', registryType: 'base', weight: 100 }],
    materialStackAmount: 0.25,
  }])[0],
  full_amount_payload: ctx.buildServerZonesForRender([{
    ...clientZone,
    materialStack: [
      { id: 'chrome', registryType: 'base', weight: 60 },
      { id: 'acid_trip', registryType: 'monolithic', weight: 40 },
    ],
    materialStackAmount: 1.0,
  }])[0],
  legacy_inferred_payload: ctx.buildServerZonesForRender([{
    ...clientZone,
    materialStack: [
      { id: 'chrome', registryType: 'base', weight: 30 },
      { id: 'acid_trip', registryType: 'monolithic', weight: 20 },
    ],
    materialStackAmount: undefined,
  }])[0],
  over_four_error: captureError(() => ctx._normalizeZoneMaterialStack({
    ...clientZone,
    materialStack: [
      ...clientZone.materialStack,
      { id: 'matte', registryType: 'base', weight: 10 },
      { id: 'gloss', registryType: 'base', weight: 10 },
      { id: 'acid_etched_glass', registryType: 'monolithic', weight: 10 },
    ],
  })),
  typed_mismatch_error: captureError(() => ctx._normalizeZoneMaterialStack({
    ...clientZone,
    materialStack: [{ id: 'chrome', registryType: 'monolithic', weight: 100 }],
  })),
};

console.log(JSON.stringify(result));
