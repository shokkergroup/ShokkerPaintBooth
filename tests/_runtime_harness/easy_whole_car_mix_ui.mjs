import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const EASY_SRC = readFileSync(join(REPO, 'js', 'spb-easy-mode.js'), 'utf8');

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

const catalog = new Map([
  ['base:chrome', { key: 'base:chrome', id: 'chrome', type: 'base', name: 'Chrome' }],
  ['base:matte', { key: 'base:matte', id: 'matte', type: 'base', name: 'Matte' }],
  ['base:gloss', { key: 'base:gloss', id: 'gloss', type: 'base', name: 'Gloss' }],
  ['monolithic:acid_trip', { key: 'monolithic:acid_trip', id: 'acid_trip', type: 'monolithic', name: 'Acid Trip' }],
]);

function finishKey(type, id) {
  return `${type}:${id}`;
}

function finishInfo(key, type) {
  const raw = String(key || '');
  const resolved = raw.includes(':') ? raw : finishKey(type || 'base', raw);
  return catalog.get(resolved) || null;
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

const shared = {
  console: { log() {}, warn() {}, error() {} },
  Math,
  Number,
  Array,
  Object,
  String,
  JSON,
  Uint8ClampedArray,
  finishKey,
  finishInfo,
};

function buildMixContext() {
  const ctx = {
    ...shared,
    state: { view: 'whole', wholeStack: [], wholeAmount: 1, wholeScale: 1 },
    zones: [],
    $: () => null,
    undoPush() {},
    applyWholeStack() {},
    renderRail() {},
  };
  vm.createContext(ctx);
  vm.runInContext([
    extractTopLevelFunction(EASY_SRC, 'normalizedWholeStack'),
    extractTopLevelFunction(EASY_SRC, 'allocateWholeShares'),
    extractTopLevelFunction(EASY_SRC, 'normalizeWholeShares'),
    extractTopLevelFunction(EASY_SRC, 'rebalanceWholeShare'),
    extractTopLevelFunction(EASY_SRC, 'wholeEffectAmount'),
    extractTopLevelFunction(EASY_SRC, 'readWholeMaterialPlan'),
    extractTopLevelFunction(EASY_SRC, 'hydrateWholeState'),
    extractTopLevelFunction(EASY_SRC, 'addWholeMaterial'),
  ].join('\n\n'), ctx, { filename: 'easy_whole_car_mix_ui.runtime.js' });
  return ctx;
}

function row(key, weight) {
  const info = catalog.get(key);
  return { key, id: info.id, registryType: info.type, weight };
}

const mix = buildMixContext();
const normalizations = {
  one: plain(mix.normalizeWholeShares([row('base:chrome', 7)])),
  two: plain(mix.normalizeWholeShares([
    row('base:chrome', 70),
    row('base:matte', 30),
  ])),
  three_tie: plain(mix.normalizeWholeShares([
    row('base:chrome', 1),
    row('base:matte', 1),
    row('base:gloss', 1),
  ])),
  four: plain(mix.normalizeWholeShares([
    row('base:chrome', 25),
    row('base:matte', 25),
    row('base:gloss', 25),
    row('monolithic:acid_trip', 25),
  ])),
};

const rebalances = {
  proportional: plain(mix.rebalanceWholeShare([
    row('base:chrome', 50),
    row('base:matte', 30),
    row('base:gloss', 20),
  ], 0, 80)),
  two_clamped: plain(mix.rebalanceWholeShare([
    row('base:chrome', 50),
    row('base:matte', 50),
  ], 0, 100)),
  four_clamped: plain(mix.rebalanceWholeShare([
    row('base:chrome', 25),
    row('base:matte', 25),
    row('base:gloss', 25),
    row('monolithic:acid_trip', 25),
  ], 2, 100)),
};

const additions = [];
for (const key of ['base:chrome', 'base:matte', 'base:gloss', 'monolithic:acid_trip']) {
  mix.addWholeMaterial(key);
  additions.push(plain(mix.state.wholeStack));
}

mix.state = {
  view: 'whole',
  wholeStack: [row('base:chrome', 99), row('base:matte', 1)],
  wholeAmount: 0.93,
  wholeScale: 0.95,
};
mix.zones = [{
  color: 'everything',
  materialStack: [
    { id: 'chrome', registryType: 'base', weight: 20 },
    { id: 'acid_trip', registryType: 'monolithic', weight: 80 },
  ],
  materialStackAmount: 0,
  materialScale: 0.35,
}];
const activePlan = mix.readWholeMaterialPlan();
const hydrated = mix.hydrateWholeState(activePlan);

function buildControlContext() {
  const ctx = {
    ...shared,
    state: {
      view: 'whole',
      wholeStack: [row('base:chrome', 65), row('monolithic:acid_trip', 35)],
      wholeAmount: 0.4,
      wholeScale: 0.55,
    },
    zones: [{ color: 'everything', materialStack: [{ id: 'chrome', registryType: 'base', weight: 100 }] }],
    hasWholeMaterialZone: () => true,
  };
  vm.createContext(ctx);
  vm.runInContext([
    extractTopLevelFunction(EASY_SRC, 'wholeEffectAmount'),
    extractTopLevelFunction(EASY_SRC, 'syncWholeZoneFromState'),
  ].join('\n\n'), ctx, { filename: 'easy_whole_car_controls.runtime.js' });
  return ctx;
}

const controls = buildControlContext();
controls.syncWholeZoneFromState();
const controlInitial = plain(controls.zones[0]);
controls.state.wholeAmount = 0.15;
controls.syncWholeZoneFromState();
const afterStrength = plain(controls.zones[0]);
controls.state.wholeScale = 0.3;
controls.syncWholeZoneFromState();
const afterDetail = plain(controls.zones[0]);

function simulateMaterialPreview(specRgb) {
  const source = new Uint8ClampedArray([100, 120, 140, 255]);
  let rendered = null;
  const outContext = {
    clearRect() {},
    drawImage() {},
    getImageData() { return { data: new Uint8ClampedArray(source) }; },
    putImageData(image) { rendered = Array.from(image.data); },
  };
  const specContext = {
    drawImage() {},
    getImageData() { return { data: new Uint8ClampedArray([...specRgb, 255]) }; },
  };
  const specImage = { complete: true, naturalWidth: 1, naturalHeight: 1 };
  const ctx = {
    ...shared,
    _active: true,
    state: { view: 'whole' },
    hasWholeMaterialZone: () => true,
    detectWholeApplied: () => 'base:chrome',
    $: () => specImage,
    els: {
      sourceCanvas: {},
      liveCanvas: {
        width: 0,
        height: 0,
        hidden: true,
        getContext: () => outContext,
      },
      previewImg: { hidden: false },
    },
    ensureSourceCanvas: (callback) => callback(true),
    document: {
      createElement: () => ({
        width: 0,
        height: 0,
        getContext: () => specContext,
      }),
    },
  };
  vm.createContext(ctx);
  vm.runInContext(
    extractTopLevelFunction(EASY_SRC, 'renderWholeMaterialPreview'),
    ctx,
    { filename: 'easy_whole_car_material_preview.runtime.js' },
  );
  ctx.renderWholeMaterialPreview(specImage);
  return {
    source: Array.from(source),
    rendered,
    canvasHidden: ctx.els.liveCanvas.hidden,
    imageHidden: ctx.els.previewImg.hidden,
  };
}

console.log(JSON.stringify({
  normalizations,
  rebalances,
  additions,
  hydration: {
    hydrated,
    state: plain(mix.state),
  },
  controls: {
    initial: controlInitial,
    afterStrength,
    afterDetail,
  },
  preview: {
    bright: simulateMaterialPreview([255, 0, 255]),
    dark: simulateMaterialPreview([0, 255, 0]),
  },
}));
