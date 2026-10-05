import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const EASY_SRC = readFileSync(join(REPO, 'js', 'spb-easy-mode.js'), 'utf8');
const API_RENDER_SRC = readFileSync(join(REPO, 'paint-booth-5-api-render.js'), 'utf8');

function extractTopLevelFunction(src, funcName) {
  const needle = `function ${funcName}(`;
  const start = src.indexOf(needle);
  if (start === -1) throw new Error(`function not found: ${funcName}`);
  let depth = 0;
  let inFunction = false;
  let quote = null;
  let escaped = false;
  let lineComment = false;
  let blockComment = false;
  for (let i = start; i < src.length; i += 1) {
    const c = src[i];
    const next = src[i + 1];
    if (lineComment) {
      if (c === '\n') lineComment = false;
      continue;
    }
    if (blockComment) {
      if (c === '*' && next === '/') {
        blockComment = false;
        i += 1;
      }
      continue;
    }
    if (quote) {
      if (escaped) escaped = false;
      else if (c === '\\') escaped = true;
      else if (c === quote) quote = null;
      continue;
    }
    if (c === '/' && next === '/') {
      lineComment = true;
      i += 1;
      continue;
    }
    if (c === '/' && next === '*') {
      blockComment = true;
      i += 1;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      quote = c;
      continue;
    }
    if (c === '{') {
      depth += 1;
      inFunction = true;
    } else if (c === '}') {
      depth -= 1;
      if (inFunction && depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error(`unbalanced braces in ${funcName}`);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function makeElement() {
  const listeners = {};
  return {
    hidden: false,
    textContent: '',
    addEventListener(type, callback) { listeners[type] = callback; },
    fire(type) {
      if (!listeners[type]) throw new Error(`missing ${type} listener`);
      listeners[type]({ target: this });
    },
  };
}

const changeButton = makeElement();
const elements = { spbEasyRecolor: changeButton };
const zone = {
  pickerColor: '#101010',
  base: null,
  finish: null,
  baseColorMode: null,
  baseColor: null,
  baseColorSource: null,
};
let repaintRequests = 0;
let railRenders = 0;
const stageToggles = {};
const context = {
  console: { log() {}, warn() {}, error() {} },
  Math,
  Number,
  Array,
  Object,
  String,
  JSON,
  _built: true,
  _active: true,
  state: { view: 'bycolor' },
  zones: [zone],
  bc: { phase: 'color', zoneIdx: 0, pickerFor: 'finish' },
  $: (id) => elements[id] || null,
  wireTolSlider() {},
  armLazyThumbs() {},
  renderRail() { railRenders += 1; },
  refreshZonesUI() {},
  undoPush() {},
  kickPreview() { repaintRequests += 1; },
  kickPreviewDebounced() { repaintRequests += 1; },
  idIsValid: () => true,
  currentCarRecord: () => ({ name: 'test-car' }),
  finishInfo: (key) => (
    key === 'base:gloss'
      ? { key, id: 'gloss', type: 'base', name: 'Gloss' }
      : null
  ),
  paintLoaded: () => true,
  detectWholeApplied: () => null,
  easyColorZones: () => context.zones.map((z, i) => ({ z, i })),
  ensureSourceCanvas: (callback) => callback(true),
  renderWholeMaterialPreview() {},
  syncSpecProof() {},
  setPickMode() {},
  els: {
    stage: { classList: { toggle(name, value) { stageToggles[name] = value; } } },
    liveCanvas: { hidden: true },
    previewImg: { hidden: true },
    pickCanvas: { hidden: true },
    stageHint: { textContent: '' },
  },
};

vm.createContext(context);
vm.runInContext([
  extractTopLevelFunction(EASY_SRC, 'setZoneRecolor'),
  extractTopLevelFunction(EASY_SRC, 'setZoneFinish'),
  extractTopLevelFunction(EASY_SRC, 'saveBlockReason'),
  extractTopLevelFunction(EASY_SRC, 'wireColorPhase'),
  extractTopLevelFunction(EASY_SRC, 'syncStage'),
].join('\n\n'), context, { filename: 'easy_by_color_live_recolor.runtime.js' });

// Merely opening the Change Color controls is navigation, not a paint edit.
context.wireColorPhase();
changeButton.fire('click');
context.syncStage();
const passiveEntry = {
  zone: plain(zone),
  repaintRequests,
  railRenders,
  liveCanvasHidden: context.els.liveCanvas.hidden,
  previewImageHidden: context.els.previewImg.hidden,
};

// A deliberate replacement-color choice must repaint immediately even though
// no base/spec finish has been chosen yet.
context.setZoneRecolor(0, '#33cc88');
context.syncStage();
const explicitChoice = {
  zone: plain(zone),
  repaintRequests,
  liveCanvasHidden: context.els.liveCanvas.hidden,
  previewImageHidden: context.els.previewImg.hidden,
  proofSurfaceOn: stageToggles['spb-easy-proof-on'],
};

const unfinishedSaveReason = context.saveBlockReason();

context.setZoneRecolor(0, null);
const clearedChoice = { zone: plain(zone), repaintRequests };

context.setZoneRecolor(0, '#33cc88');
context.setZoneFinish(0, 'base:gloss');
const finishedChoice = { zone: plain(zone), repaintRequests };

const anchorContext = {
  _zoneHasActiveBaseOverlay: () => false,
};
vm.createContext(anchorContext);
vm.runInContext(
  extractTopLevelFunction(API_RENDER_SRC, '_zoneNeedsNeutralBaseAnchor'),
  anchorContext,
  { filename: 'easy_by_color_neutral_anchor.runtime.js' },
);
const neutralAnchor = {
  pendingOnly: anchorContext._zoneNeedsNeutralBaseAnchor({
    base: null,
    finish: null,
    _easyPendingColorPreview: true,
  }),
  pendingWithBase: anchorContext._zoneNeedsNeutralBaseAnchor({
    base: 'gloss',
    finish: null,
    _easyPendingColorPreview: true,
  }),
  pendingWithFinish: anchorContext._zoneNeedsNeutralBaseAnchor({
    base: null,
    finish: 'chrome',
    _easyPendingColorPreview: true,
  }),
  noMarker: anchorContext._zoneNeedsNeutralBaseAnchor({
    base: null,
    finish: null,
  }),
};

const payloadBlock = [
  extractTopLevelFunction(API_RENDER_SRC, '_applyBaseColorBranch'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneShouldFitIntoApplyArea'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasActiveBaseOverlay'),
  extractTopLevelFunction(API_RENDER_SRC, '_normalizeZoneMaterialStack'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasMaterialStack'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyZoneMaterialStack'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneNeedsNeutralBaseAnchor'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasImportedSpecSource'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneSpecSourceStrength'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyZoneSpecSource'),
  extractTopLevelFunction(API_RENDER_SRC, '_zoneHasRenderableMaterial'),
  extractTopLevelFunction(API_RENDER_SRC, '_applyBaseColorMode'),
  extractTopLevelFunction(API_RENDER_SRC, 'buildServerZonesForRender'),
].join('\n\n');
const payloadContext = {
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
  BASES_BY_ID: { chrome: {}, gloss: {} },
  MONOLITHICS_BY_ID: {},
  formatColorForServer: (color) => color,
  _applyCustomIntensity() {},
  _mapPatternStack: () => null,
  _resolveFinishColors: () => null,
  _applySpecMaterialRemap() {},
  _applySpecMaterialOverride() {},
  _applySpecLightingMask() {},
  _applyAllSpecPatternStacks() {},
  _applyBlendBaseOverlay() {},
  _applyAllExtraBaseOverlays() {},
  _encodeZoneApplyMasks() {},
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
vm.createContext(payloadContext);
vm.runInContext(payloadBlock, payloadContext, {
  filename: 'easy_by_color_canonical_payload.runtime.js',
});
const canonicalPayload = payloadContext.buildServerZonesForRender([
  {
    name: 'Existing completed color',
    color: { color_rgb: [0, 0, 0], tolerance: 10 },
    intensity: '100',
    base: 'chrome',
    finish: null,
    pattern: 'none',
    baseColorMode: 'source',
  },
  {
    name: 'New pending recolor',
    color: { color_rgb: [16, 16, 16], tolerance: 10 },
    intensity: '100',
    base: null,
    finish: null,
    pattern: 'none',
    baseColorMode: 'solid',
    baseColor: '#336699',
    baseColorStrength: 1,
    _easyPendingColorPreview: true,
  },
]);

let nextTimerId = 40;
let queuedCallback = null;
const clearedTimers = [];
let immediateKicks = 0;
const raceContext = {
  window: { spbKickLivePreview() { immediateKicks += 1; } },
  _kickTimer: null,
  PREVIEW_DEBOUNCE_MS: 90,
  setTimeout(callback) {
    queuedCallback = callback;
    nextTimerId += 1;
    return nextTimerId;
  },
  clearTimeout(timerId) { clearedTimers.push(timerId); },
};
vm.createContext(raceContext);
vm.runInContext([
  extractTopLevelFunction(EASY_SRC, 'kickPreview'),
  extractTopLevelFunction(EASY_SRC, 'kickPreviewDebounced'),
].join('\n\n'), raceContext, {
  filename: 'easy_by_color_preview_race.runtime.js',
});
raceContext.kickPreviewDebounced();
const queuedTimerId = raceContext._kickTimer;
raceContext.kickPreview();
const immediateKickRace = {
  queuedTimerId,
  queuedCallbackType: typeof queuedCallback,
  clearedTimers,
  timerAfterImmediateKick: raceContext._kickTimer,
  immediateKicks,
};

console.log(JSON.stringify({
  passiveEntry,
  explicitChoice,
  unfinishedSaveReason,
  clearedChoice,
  finishedChoice,
  neutralAnchor,
  canonicalPayload,
  immediateKickRace,
}));
