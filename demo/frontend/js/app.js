import {
  getJSON, postJSON, postForm, postImage, normalizeManifest, normalizePreview,
  selectSourceFile, selectIRacingFolder, openExternal, revealPath,
} from './api.js';
import {
  flattenLayerTree, attachRasterizedLayers, composeLayers, paintCanvasFrom,
  paintCanvasFromUrl, canvasPoint, samplePixel, hitTestLayers, hexToRgb, loadImage,
  drawChannel, makeSwatchCanvas, encodeSourceLayerScope, clearImageCache,
} from './canvas.js';
import {
  calculateViewportAnchor, clampViewportZoom, stepViewportZoom, wheelViewportZoom,
} from './preview-interactions.js?v=demo5-20260903a';
import { installExcludeBrush } from './exclude-brush.js?v=demo12-20260904a';
import { prepareImportedZoneScopes } from './exclude-mask.js';

let excludeBrush = null;

// v2 deliberately keeps demo.3+ on the restored five-Zone contract instead
// of reviving demo.1/demo.2's single-Zone localStorage payload.
const STORAGE_KEY = 'shokk_demo_session_v2';
const SAFE_PAYHIP = 'https://payhip.com/b/AHgpV';
const SAFE_DISCORD = 'https://discord.gg/GwXxyhwtDu';
const MAX_ZONES = 24;
const MAX_SPEC_STRENGTH_PERCENT = 300;

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  manifest: { finishes: [], baseColorSources: [], fractureFinishId: 'fs_core_emerald', links: { payhip: SAFE_PAYHIP, discord: SAFE_DISCORD } },
  source: { path: '', width: 2048, height: 2048, compositeUrl: '', composed: null, dataUrl: '', token: '' },
  layers: [],
  zones: [],
  selectedZoneId: '',
  selectedLayerId: '',
  tool: 'pick',
  pickIntent: 'item',
  viewportZoom: { source: 1, live: 1 },
  hoveredMap: '',
  liveDisplayGeneration: 0,
  channelInspectKey: '',
  channelInspectGeneration: 0,
  outputFolder: '',
  previewTimer: 0,
  composeTimer: 0,
  composeGeneration: 0,
  previewGeneration: 0,
  isPreviewing: false,
  previewQueued: false,
  isRendering: false,
  lastPreview: null,
  finishFilter: 'ALL',
  finishPickerMode: 'material',
  layerMaskCache: new Map(),
  layerMaskRevision: 0,
  startedAt: performance.now(),
};

const MAP_CHANNELS = {
  combined: { label: 'COMBINED', resultKey: 'combined', canvasId: 'combinedCanvas' },
  metal: { label: 'R METAL', resultKey: 'metal', canvasId: 'metalCanvas' },
  rough: { label: 'G ROUGH', resultKey: 'rough', canvasId: 'roughCanvas' },
  clearcoat: { label: 'B COAT / CLEARCOAT', resultKey: 'clearcoat', canvasId: 'clearcoatCanvas' },
};

const sliderDefinitions = [
  { key: 'baseHueOffset', label: 'Hue Shift', min: -180, max: 180, step: 1, unit: '°', reset: 0 },
  { key: 'baseSaturationAdjust', label: 'Saturation', min: -100, max: 100, step: 1, unit: '', reset: 0 },
  { key: 'baseBrightnessAdjust', label: 'Brightness', min: -100, max: 200, step: 1, unit: '', reset: 0 },
  { key: 'baseStrength', label: 'Base Strength', min: 0, max: 100, step: 5, unit: '%', reset: 100, payloadScale: .01 },
  { key: 'baseSpecStrength', label: 'Spec Strength', min: 0, max: MAX_SPEC_STRENGTH_PERCENT, step: 5, unit: '%', reset: 100, payloadScale: .01 },
  { key: 'baseScale', label: 'Base Scale', min: .05, max: 5, step: .05, unit: 'x', reset: 1, digits: 2 },
  { key: 'baseRotation', label: 'Base Rotation', min: 0, max: 355, step: 5, unit: '°', reset: 0 },
  { key: 'baseColorScale', label: 'Color Scale', min: .05, max: 5, step: .05, unit: 'x', reset: 1, digits: 2 },
  { key: 'baseColorRotation', label: 'Color Rotation', min: 0, max: 355, step: 5, unit: '°', reset: 0 },
  { key: 'baseColorDepth', label: 'Color Depth', min: 0, max: 100, step: 5, unit: '%', reset: 0, payloadScale: .01 },
  { key: 'baseColorFlip', label: 'Color Flip', min: 0, max: 355, step: 5, unit: '°', reset: 0 },
  { key: 'baseColorUnderglow', label: 'Underglow', min: 0, max: 100, step: 5, unit: '%', reset: 0, payloadScale: .01 },
  { key: 'specScale', label: 'Spec Scale', min: .05, max: 5, step: .05, unit: 'x', reset: 1, digits: 2 },
  { key: 'specRotation', label: 'Spec Rotation', min: 0, max: 355, step: 5, unit: '°', reset: 0 },
  { key: 'specShiftR', label: 'R Metal', min: -127, max: 127, step: 1, unit: '', reset: 0, className: 'metal' },
  { key: 'specShiftG', label: 'G Rough', min: -127, max: 127, step: 1, unit: '', reset: 0, className: 'rough' },
  { key: 'specShiftB', label: 'B Coat', min: -127, max: 127, step: 1, unit: '', reset: 0, className: 'coat' },
];

function manifestFinish(id) {
  return [...state.manifest.finishes, ...(state.manifest.baseColorSources || [])].find((finish) => finish.id === id) || null;
}

function createZone(index = state.zones.length, overrides = {}) {
  const finish = manifestFinish(overrides.finishId || '');
  const zone = {
    id: crypto.randomUUID ? crypto.randomUUID() : `zone-${Date.now()}-${Math.random()}`,
    name: `Zone ${index + 1}`,
    hint: '',
    finishId: finish?.id || '',
    finishName: finish?.name || '',
    color: '#3366FF',
    coverageMode: 'colors',
    pickerTolerance: 40,
    colors: [],
    exclusions: [],
    sourceLayers: isSingleFlatSource() ? [String(state.layers[0].id)] : [],
    sourceLayer: null,
    spatialMask: null,
    intensity: 100,
    baseColorMode: 'finish',
    baseColor: finish?.swatch || '#FFFFFF',
    baseColorSource: '',
    lockBaseColor: false,
    baseColorStrength: 100,
    gradientStops: [
      { position: 0, color: '#000000' },
      { position: 1, color: '#FFFFFF' },
    ],
    gradientDirection: 'horizontal',
    baseHueOffset: 0,
    baseSaturationAdjust: 0,
    baseBrightnessAdjust: 0,
    baseStrength: 100,
    baseSpecStrength: 100,
    baseScale: 1,
    baseRotation: 0,
    baseColorScale: 1,
    baseColorRotation: 0,
    baseColorLabEnabled: false,
    baseColorDepth: 0,
    baseColorFlip: 0,
    baseColorUnderglow: 0,
    specScale: 1,
    specRotation: 0,
    // Linked to Base Scale / Base Rotation by default, exactly like the paid app.
    specScaleMode: 'match',
    specBlendMode: 'normal',
    specShiftR: 0,
    specShiftG: 0,
    specShiftB: 0,
    enabled: true,
  };
  const created = { ...zone, ...overrides, colors: overrides.colors || zone.colors, exclusions: overrides.exclusions || zone.exclusions, sourceLayers: overrides.sourceLayers || zone.sourceLayers, gradientStops: overrides.gradientStops || zone.gradientStops };
  created.baseSpecStrength = normalizeSpecStrengthPercent(created.baseSpecStrength);
  // [SPB-DEMO-COLOR 2026-09-03] Legacy defaults silently blended Zones 4/5 at
  // 80%/50%, although the only visible Base Strength dial read 100%. No demo
  // control edits these extra multipliers. Normalize restored sessions too;
  // the visible Base Strength remains the user's deliberate blending control.
  created.intensity = 100;
  created.baseColorStrength = 100;
  return created;
}

function createDefaultZones() {
  return [
    createZone(0, { name: 'Zone 1', hint: 'Pick your primary body color from the SOURCE paint.' }),
    createZone(1, { name: 'Zone 2', color: '#FFCC00', hint: 'Pick a second body color, or leave this Zone empty.' }),
    createZone(2, { name: 'Zone 3', color: '#FFAA00', pickerTolerance: 35, hint: 'Use for numbers or a third paint color.' }),
    createZone(3, { name: 'Zone 4', color: '#FFFFFF', pickerTolerance: 30, hint: 'Use for sponsors, accents, or artwork.' }),
    createZone(4, {
      name: 'Everything Else',
      hint: 'Safety net: Gloss catches every source pixel not claimed by Zones above.',
      finishId: 'gloss',
      finishName: manifestFinish('gloss')?.name || 'Gloss',
      color: '#888888',
      coverageMode: 'remaining',
      baseColorMode: 'source',
    }),
  ];
}

function activeZone() { return state.zones.find((zone) => zone.id === state.selectedZoneId) || state.zones[0] || null; }
function activeLayer() { return state.layers.find((layer) => layer.id === state.selectedLayerId) || null; }
function isSingleFlatSource() { return state.source.isFlat && state.layers.length === 1; }
function selectedFinish(zone = activeZone()) { return manifestFinish(zone?.finishId) || { id: '', name: 'Choose Base Material', collection: '29 demo materials', swatch: '#30394A' }; }

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

function clamp(value, min, max) { return Math.max(min, Math.min(max, Number(value))); }

function normalizeSpecStrengthPercent(value) {
  const numeric = Number(value);
  return clamp(Number.isFinite(numeric) ? numeric : 100, 0, MAX_SPEC_STRENGTH_PERCENT);
}

function showToast(message, isError = false) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.toggle('error', isError);
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 3500);
}

function setBusy(busy, label = '') {
  $('#app').setAttribute('aria-busy', busy ? 'true' : 'false');
  if (label) $('#renderState').textContent = label.toUpperCase();
}

function basename(path) { return String(path || '').split(/[\\/]/).pop() || ''; }

function versionedAssetUrl(url) {
  const value = String(url || '');
  if (!value) return value;
  const version = encodeURIComponent(state.manifest.version || 'demo');
  return `${value}${value.includes('?') ? '&' : '?'}v=${version}`;
}

function saveSession() {
  const payload = {
    schemaVersion: 2,
    sourcePath: state.source.path,
    outputFolder: state.outputFolder,
    zones: state.zones,
    selectedZoneId: state.selectedZoneId,
    iracingId: $('#iracingId').value.trim(),
    carNumber: $('#carNumber').value.trim(),
    numberMode: $('input[name="number-mode"]:checked')?.value || 'custom',
  };
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(payload)); } catch (_) { /* local storage is optional */ }
}

function readSession() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); }
  catch (_) { return null; }
}

function restoreControls(session) {
  if (!session) return;
  if (session.iracingId) $('#iracingId').value = String(session.iracingId);
  if (session.carNumber) $('#carNumber').value = String(session.carNumber);
  const mode = session.numberMode === 'sim' ? $('#simNumberMode') : $('#customNumberMode');
  if (mode) mode.checked = true;
  if (session.outputFolder) {
    state.outputFolder = session.outputFolder;
    $('#outputPath').textContent = session.outputFolder;
    $('#outputPath').title = session.outputFolder;
  }
  if (Array.isArray(session.zones) && session.zones.length) {
    state.zones = session.zones.slice(0, MAX_ZONES).map((saved, index) => {
      const zone = createZone(index, saved);
      if (!zone.id) zone.id = createZone(index).id;
      if (!manifestFinish(zone.finishId)) { zone.finishId = ''; zone.finishName = ''; }
      if (zone.baseColorSource && !state.manifest.baseColorSources.some((finish) => finish.id === zone.baseColorSource)) zone.baseColorSource = '';
      zone.coverageMode = zone.coverageMode === 'remaining' ? 'remaining' : 'colors';
      zone.colors = Array.isArray(zone.colors) ? zone.colors : [];
      zone.exclusions = Array.isArray(zone.exclusions) ? zone.exclusions : [];
      zone.sourceLayers = Array.isArray(zone.sourceLayers) ? [...new Set(zone.sourceLayers.map(String))] : [];
      zone.sourceLayer = zone.sourceLayers[0] || null;
      zone.gradientStops = normalizeGradientStops(zone);
      zone.baseSpecStrength = normalizeSpecStrengthPercent(zone.baseSpecStrength);
      return zone;
    });
    state.selectedZoneId = state.zones.some((zone) => zone.id === session.selectedZoneId) ? session.selectedZoneId : state.zones[0].id;
  }
}

function renderZones() {
  const list = $('#zoneList');
  list.replaceChildren();
  state.zones.forEach((zone, index) => {
    const card = document.createElement('article');
    card.className = `zone-card${zone.id === state.selectedZoneId ? ' active' : ''}`;
    card.style.setProperty('--zone', zone.color || '#2bd57d');
    card.dataset.zoneId = zone.id;
    const count = zone.colors?.length || 0;
    const coverage = zone.coverageMode === 'remaining'
      ? 'REMAINING'
      : `${count} picked color${count === 1 ? '' : 's'}`;
    const restricted = (zone.sourceLayers || []).length;
    card.innerHTML = `<header><span class="zone-index">${index + 1}</span><span class="zone-dot"></span><strong>${escapeHtml(zone.name)}</strong></header><p>${escapeHtml(zone.finishName || selectedFinish(zone).name)}</p><small>${escapeHtml(coverage)}${restricted ? ` · ${restricted} layer${restricted === 1 ? '' : 's'}` : ' · all layers'}</small><footer><button data-zone-action="toggle" title="${zone.enabled ? 'Disable' : 'Enable'} zone">${zone.enabled ? '◉' : '○'}</button><button data-zone-action="up" title="Move zone up"${index === 0 ? ' disabled' : ''}>↑</button><button data-zone-action="down" title="Move zone down"${index === state.zones.length - 1 ? ' disabled' : ''}>↓</button><button data-zone-action="duplicate" title="Duplicate zone">▣</button><button data-zone-action="delete" title="Delete zone">×</button></footer>`;
    list.append(card);
  });
  $('#zoneCount').textContent = state.zones.length;
}

function formatSlider(definition, value) {
  const digits = definition.digits ?? 0;
  return `${Number(value).toFixed(digits)}${definition.unit}`;
}

function hydrateFinishVisual(canvas, finish) {
  makeSwatchCanvas(canvas, finish);
  if (!finish?.id) return;
  const url = finish.thumbnail || `/demo-assets/thumbnails/${encodeURIComponent(finish.id)}.png`;
  const image = new Image();
  image.className = canvas.className;
  image.alt = '';
  image.onload = () => { if (canvas.isConnected) canvas.replaceWith(image); };
  image.src = versionedAssetUrl(url);
}

// [SPB-DEMO-SCALE 2026-09-03 — owner: "the BASE and SPEC SCALES ARE SUPPOSED TO STAY IN
// LOCKSTEP UNLESS WE USE THE CHECKBOX ON SPEC SCALE"] Same contract as the paid app's
// _spbResolveSpecScale: spec follows base unless the zone is explicitly independent.
// The demo used to hardcode specScaleMode 'independent' in every payload.
function specIndependent(zone) {
  return (zone && zone.specScaleMode) === 'independent';
}
function resolveSpecScale(zone) {
  return specIndependent(zone) ? Number(zone.specScale ?? 1) : Number(zone.baseScale ?? 1);
}
function resolveSpecRotation(zone) {
  return specIndependent(zone) ? Number(zone.specRotation ?? 0) : Number(zone.baseRotation ?? 0);
}

function sliderRow(definition, zone) {
  // Spec Scale / Rotation mirror the base dials while linked, so the slider shows the
  // value that will actually render instead of a stale, disabled 1.00x.
  if (!specIndependent(zone) && (definition.key === 'specScale' || definition.key === 'specRotation')) {
    const linked = definition.key === 'specScale' ? resolveSpecScale(zone) : resolveSpecRotation(zone);
    return `<div class="slider-row ${definition.className || ''} linked" data-slider-row="${definition.key}"><label title="Follows ${definition.key === 'specScale' ? 'Base Scale' : 'Base Rotation'} — tick Independent to unlink">${escapeHtml(definition.label)}</label><button type="button" disabled>−</button><input type="range" data-zone-slider="${definition.key}" min="${definition.min}" max="${definition.max}" step="${definition.step}" value="${linked}" disabled><button type="button" disabled>+</button><output>${formatSlider(definition, linked)}</output><button type="button" title="Linked to base" disabled>🔗</button></div>`;
  }
  const rawValue = zone[definition.key] ?? definition.reset;
  const value = definition.key === 'baseSpecStrength' ? normalizeSpecStrengthPercent(rawValue) : rawValue;
  return `<div class="slider-row ${definition.className || ''}" data-slider-row="${definition.key}"><label title="${escapeHtml(definition.label)}">${escapeHtml(definition.label)}</label><button data-step="-1" type="button">−</button><input type="range" data-zone-slider="${definition.key}" min="${definition.min}" max="${definition.max}" step="${definition.step}" value="${value}"><button data-step="1" type="button">+</button><output>${formatSlider(definition, value)}</output><button data-reset-slider="${definition.key}" type="button" title="Reset">↻</button></div>`;
}

function colorLabActive(zone) {
  return zone.baseColorLabEnabled === true && ['solid', 'special', 'gradient'].includes(zone.baseColorMode);
}

function renderColorChips(zone, root) {
  const holder = $('.color-chips', root);
  holder.replaceChildren();
  (zone.coverageMode === 'remaining' ? [] : (zone.colors || [])).forEach((entry, index) => {
    const chip = document.createElement('div');
    chip.className = 'color-chip';
    chip.style.setProperty('--chip', entry.hex);
    chip.innerHTML = `<div class="color-chip-head"><i></i><strong>${escapeHtml(entry.hex)}</strong><button type="button" data-remove-color="${index}" aria-label="Remove ${escapeHtml(entry.hex)}">×</button></div><label class="tolerance-control" title="Exact grabs only this color; Loose also grabs nearby shades."><span>Exact</span><input type="range" min="0" max="100" step="1" value="${clamp(entry.tolerance ?? 40, 0, 100)}" data-color-tolerance="${index}"><span>Loose</span><output>±${clamp(entry.tolerance ?? 40, 0, 100)}</output></label>`;
    holder.append(chip);
  });
  (zone.exclusions || []).forEach((entry, index) => {
    const chip = document.createElement('div');
    chip.className = 'color-chip exclusion';
    chip.style.setProperty('--chip', entry.hex);
    chip.innerHTML = `<div class="color-chip-head"><i></i><strong>EXCLUDE ${escapeHtml(entry.hex)}</strong><button type="button" data-remove-exclusion="${index}" aria-label="Remove exclusion">×</button></div>`;
    holder.append(chip);
  });
}

function renderLayerRestriction(zone) {
  if (!state.layers.length) return '';
  if (isSingleFlatSource()) return `<section class="restriction-box"><header><strong>FLAT IMAGE — AUTOMATIC</strong></header><label class="restriction-layer"><input type="checkbox" checked disabled><span>${escapeHtml(state.layers[0].name)}</span></label><small>The whole image is selected. No layer selection needed.</small></section>`;
  const selected = new Set((zone.sourceLayers || []).map(String));
  const rows = state.layers.map((layer) => `<label class="restriction-layer${layer.visible ? '' : ' hidden-layer'}"><input type="checkbox" data-zone-layer="${escapeHtml(layer.id)}"${selected.has(String(layer.id)) ? ' checked' : ''}><span>${escapeHtml(layer.name)}</span>${layer.visible ? '' : '<em>HIDDEN</em>'}</label>`).join('');
  const selectedLayers = state.layers.filter((layer) => selected.has(String(layer.id)));
  const missing = [...selected].filter((id) => !state.layers.some((layer) => String(layer.id) === id));
  const hidden = selectedLayers.filter((layer) => !layer.visible);
  const status = !selected.size
    ? 'All layers (no restriction)'
    : missing.length
      ? `Missing ${missing.length} saved layer${missing.length === 1 ? '' : 's'}`
      : `Restricted to ${selectedLayers.length} layer${selectedLayers.length === 1 ? '' : 's'}${hidden.length ? ` · ${hidden.length} hidden (not painting)` : ''}`;
  return `<section class="restriction-box"><header><strong>RESTRICT TO LAYERS</strong>${selected.size ? '<button id="clearLayerRestriction" type="button">CLEAR</button>' : ''}</header><div class="restriction-list">${rows}</div><small class="${missing.length || hidden.length ? 'warning' : ''}">${escapeHtml(status)}</small></section>`;
}

function normalizeGradientStops(zone) {
  const raw = Array.isArray(zone.gradientStops) ? zone.gradientStops : [];
  const stops = raw.map((stop, index) => ({
    position: clamp(stop?.position ?? stop?.pos ?? index / Math.max(1, raw.length - 1), 0, 1),
    color: hexToRgb(stop?.color) ? String(stop.color).toUpperCase() : '#FFFFFF',
  })).sort((a, b) => a.position - b.position);
  return stops.length >= 2 ? stops : [{ position: 0, color: '#000000' }, { position: 1, color: '#FFFFFF' }];
}

function renderGradientEditor(zone) {
  const stops = normalizeGradientStops(zone);
  zone.gradientStops = stops;
  return `<div class="gradient-editor"><div class="gradient-stops">${stops.map((stop, index) => `<div class="gradient-stop"><input type="color" value="${escapeHtml(stop.color)}" data-gradient-color="${index}" aria-label="Gradient stop ${index + 1} color"><input type="range" min="0" max="100" step="1" value="${Math.round(stop.position * 100)}" data-gradient-position="${index}" aria-label="Gradient stop ${index + 1} position"><output>${Math.round(stop.position * 100)}%</output><button type="button" data-remove-gradient-stop="${index}"${stops.length <= 2 ? ' disabled' : ''} aria-label="Remove gradient stop">×</button></div>`).join('')}</div><div class="gradient-actions"><button id="addGradientStop" type="button"${stops.length >= 10 ? ' disabled' : ''}>＋ ADD STOP</button><label>Direction <select id="gradientDirection">${[['horizontal','Horizontal'],['vertical','Vertical'],['diagonal_down','Diagonal ↘'],['diagonal_up','Diagonal ↗'],['radial','Radial'],['angular','Angular']].map(([value,label]) => `<option value="${value}"${zone.gradientDirection === value ? ' selected' : ''}>${label}</option>`).join('')}</select></label></div></div>`;
}

function renderBaseColorControls(zone) {
  const mode = ['finish', 'source', 'solid', 'special', 'gradient'].includes(zone.baseColorMode) ? zone.baseColorMode : 'finish';
  const source = manifestFinish(zone.baseColorSource);
  let detail = '';
  if (mode === 'finish') detail = `<p class="mode-note">Uses <strong>${escapeHtml(selectedFinish(zone).name)}</strong> paint color. Base Material still supplies its spec.</p>`;
  else if (mode === 'source') detail = '<p class="mode-note">Keeps the SOURCE livery color and applies only the Base Material/spec behavior.</p>';
  else if (mode === 'solid') detail = `<div class="color-row base-color-solid"><label>COLOR</label><input id="baseColorPicker" type="color" value="${escapeHtml(zone.baseColor || '#FFFFFF')}"><input id="baseColorText" type="text" value="${escapeHtml(zone.baseColor || '#FFFFFF')}" maxlength="7"></div>`;
  else if (mode === 'special') detail = `<button id="specialColorTrigger" class="finish-trigger special-trigger" type="button"><canvas id="specialColorSwatch"></canvas><span><strong>${escapeHtml(source?.name || 'Choose from all 30')}</strong><small>${escapeHtml(source?.collection || 'Demo color sources')}</small></span><i>CHANGE ›</i></button>`;
  else detail = renderGradientEditor(zone);
  return `<section class="base-color-box"><header><div><strong>BASE COLOR</strong><small>Independent from Base Material</small></div><label class="lock-color"><input id="lockBaseColor" type="checkbox"${zone.lockBaseColor ? ' checked' : ''}> 🔒 LOCK</label></header><select id="baseColorMode"><option value="finish"${mode === 'finish' ? ' selected' : ''}>Use finish's own color</option><option value="source"${mode === 'source' ? ' selected' : ''}>Use source paint (spec only)</option><option value="solid"${mode === 'solid' ? ' selected' : ''}>Use solid color</option><option value="special"${mode === 'special' ? ' selected' : ''}>From special</option><option value="gradient"${mode === 'gradient' ? ' selected' : ''}>Custom gradient</option></select>${detail}</section>`;
}

function renderZoneEditor() {
  excludeBrush?.refresh();
  const root = $('#zoneEditor');
  const zone = activeZone();
  if (!zone) {
    root.innerHTML = '<p class="zone-note">Add a zone to start painting.</p>';
    return;
  }
  const finish = selectedFinish(zone);
  const colorCount = (zone.colors || []).length;
  root.innerHTML = `
    ${renderLayerRestriction(zone)}
    <section class="coverage-box">
      <strong>WHAT PIXELS DOES THIS ZONE COVER?</strong>
      <div class="coverage-options" role="radiogroup" aria-label="Zone coverage">
        <label><input type="radio" name="coverage-mode" value="colors"${zone.coverageMode !== 'remaining' ? ' checked' : ''}> COLORS</label>
        <label><input type="radio" name="coverage-mode" value="remaining"${zone.coverageMode === 'remaining' ? ' checked' : ''}> REMAINING</label>
      </div>
      ${zone.coverageMode === 'remaining'
        ? '<p class="mode-note">Catches every source pixel not claimed by a Zone above it.</p>'
        : `<div class="color-tools"><button id="addColorPick" class="btn" type="button">＋ ADD COLOR FROM SOURCE</button><button id="clearPickedColors" class="btn ghost-btn" type="button"${colorCount ? '' : ' disabled'}>CLEAR COLORS</button></div><div class="color-chips"></div><p class="mode-note">Pick multiple colors. Every color has its own Exact ↔ Loose tolerance.</p>`}
      ${zone.coverageMode === 'remaining' ? '<div class="color-chips exclusions-only"></div>' : ''}
    </section>
    <div class="selected-finish">
      <span>BASE MATERIAL</span>
      <button id="finishTrigger" class="finish-trigger" type="button"><canvas id="selectedFinishSwatch"></canvas><span><strong>${escapeHtml(finish.name)}</strong><small>${escapeHtml(finish.collection)}</small></span><i>CHANGE ›</i></button>
    </div>
    ${renderBaseColorControls(zone)}
    ${zone.hint ? `<p class="zone-note">${escapeHtml(zone.hint)}</p>` : ''}
    <div class="section-heading">MATERIAL + COLOR</div>
    <div class="slider-stack">${sliderDefinitions.slice(0, 9).map((definition) => sliderRow(definition, zone)).join('')}</div>
    <label class="spec-link-row" title="Optional candy-color effects. Leave off to preserve the selected color.">
      <input type="checkbox" id="baseColorLabEnabled"${zone.baseColorLabEnabled === true ? ' checked' : ''}>
      <span>Enable Color Lab effects</span>
    </label>
    <p class="zone-note">${colorLabActive(zone) ? 'All three at 0 preserves the selected color. Color Depth adds darker candy coats; Flip and Underglow alter the result. HSB and strength still apply.' : 'Color Lab effects inactive — HSB, strength and scale controls still apply.'}</p>
    <fieldset class="color-lab-controls"${colorLabActive(zone) ? '' : ' disabled'} aria-label="Optional Color Lab effects">
      <div class="slider-stack">${sliderDefinitions.slice(9, 12).map((definition) => sliderRow(definition, zone)).join('')}</div>
    </fieldset>
    <div class="slider-stack">${sliderDefinitions.slice(12, 14).map((definition) => sliderRow(definition, zone)).join('')}</div>
    <div class="select-row"><label>Spec Blend</label><select id="specBlendMode">
      ${['normal','ghost_carve','chrome_inlay','frost_etch','angle_flip','ember_gate','depth_press','multiply','screen','overlay','hardlight','softlight'].map((mode) => `<option value="${mode}"${zone.specBlendMode === mode ? ' selected' : ''}>${mode.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>`).join('')}
    </select></div>
    <div class="section-heading">SPEC SLIDERS</div>
    <label class="spec-link-row" title="Off: Spec Scale and Rotation follow Base Scale and Base Rotation, like the full app. On: set them independently.">
      <input type="checkbox" id="specScaleIndependent"${specIndependent(zone) ? ' checked' : ''}>
      <span>Independent spec scale / rotation</span>
    </label>
    <div class="slider-stack">${sliderDefinitions.slice(14).map((definition) => sliderRow(definition, zone)).join('')}</div>
  `;
  hydrateFinishVisual($('#selectedFinishSwatch'), finish);
  const special = manifestFinish(zone.baseColorSource);
  if ($('#specialColorSwatch') && special) hydrateFinishVisual($('#specialColorSwatch'), special);
  renderColorChips(zone, root);
}

function renderFinishFilters() {
  const catalog = state.finishPickerMode === 'special' ? state.manifest.baseColorSources : state.manifest.finishes;
  const groups = ['ALL', ...new Set(catalog.map((finish) => finish.collection))];
  const root = $('#finishGroups');
  root.replaceChildren();
  groups.forEach((group) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = group;
    button.classList.toggle('active', state.finishFilter === group);
    button.addEventListener('click', () => { state.finishFilter = group; renderFinishFilters(); renderFinishGrid(); });
    root.append(button);
  });
}

function renderFinishGrid() {
  const root = $('#finishGrid');
  const query = $('#finishSearch').value.trim().toLowerCase();
  const current = state.finishPickerMode === 'special' ? activeZone()?.baseColorSource : activeZone()?.finishId;
  const catalog = state.finishPickerMode === 'special' ? state.manifest.baseColorSources : state.manifest.finishes;
  const finishes = catalog.filter((finish) => {
    if (state.finishFilter !== 'ALL' && finish.collection !== state.finishFilter) return false;
    return !query || `${finish.name} ${finish.collection} ${finish.description} ${finish.id}`.toLowerCase().includes(query);
  });
  root.replaceChildren();
  finishes.forEach((finish, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `finish-card${finish.id === current ? ' selected' : ''}`;
    button.dataset.finishId = finish.id;
    const canvas = document.createElement('canvas');
    makeSwatchCanvas(canvas, finish, index + 1);
    const url = finish.thumbnail || `/demo-assets/thumbnails/${encodeURIComponent(finish.id)}.png`;
    const image = new Image();
    image.alt = '';
    image.onload = () => { if (canvas.isConnected) canvas.replaceWith(image); };
    image.src = versionedAssetUrl(url);
    button.append(canvas);
    const strong = document.createElement('strong');
    strong.textContent = finish.name;
    const small = document.createElement('small');
    small.textContent = finish.collection;
    button.append(strong, small);
    button.addEventListener('click', () => state.finishPickerMode === 'special' ? chooseBaseColorSource(finish) : chooseFinish(finish));
    root.append(button);
  });
}

function openFinishPicker(mode = 'material') {
  state.finishPickerMode = mode === 'special' ? 'special' : 'material';
  state.finishFilter = 'ALL';
  $('#finishSearch').value = '';
  $('#finishDialogTitle').textContent = state.finishPickerMode === 'special' ? 'CHOOSE BASE COLOR SOURCE' : 'CHOOSE A DEMO FINISH';
  $('#finishDialogSubtitle').textContent = state.finishPickerMode === 'special'
    ? 'All 30 demo-renderable finishes · color only; Base Material/spec stays unchanged'
    : '29 hand-picked materials from the full Shokker library';
  $('#finishSearch').placeholder = state.finishPickerMode === 'special' ? 'Search 30 color sources…' : 'Search finishes or collections…';
  renderFinishFilters();
  renderFinishGrid();
  $('#finishDialog').showModal();
}

function chooseFinish(finish, options = {}) {
  const zone = activeZone();
  if (!zone) return;
  zone.finishId = finish.id;
  zone.finishName = finish.name;
  if (!zone.lockBaseColor) {
    // SPB-DEMO-COLOR 2026-09-06: owner saw Cherry Polka crushed by the
    // former 65% candy-depth default. A fresh unlocked material gets its
    // authored special color, with neutral effects even if Color Lab is on.
    // Locked color AND its effects remain untouched. HSB/strength stay explicit.
    zone.baseColorMode = options.useFinishColor ? 'finish' : 'special';
    zone.baseColorSource = options.useFinishColor ? '' : finish.id;
    zone.baseColorDepth = 0;
    zone.baseColorFlip = 0;
    zone.baseColorUnderglow = 0;
    if (finish.swatch) zone.baseColor = finish.swatch;
  }
  renderZones();
  renderZoneEditor();
  if ($('#finishDialog').open) $('#finishDialog').close();
  schedulePreview();
  saveSession();
  showToast(`${zone.name}: ${finish.name}`);
}

function chooseBaseColorSource(finish) {
  const zone = activeZone();
  if (!zone) return;
  zone.baseColorMode = 'special';
  zone.baseColorSource = finish.id;
  if (finish.swatch) zone.baseColor = finish.swatch;
  renderZoneEditor();
  if ($('#finishDialog').open) $('#finishDialog').close();
  schedulePreview();
  saveSession();
  showToast(`${zone.name} color source: ${finish.name} · material unchanged`);
}

async function sourceLayerScopeFor(zone) {
  if (isSingleFlatSource()) return { mask: null, rgbPng: '' };
  const ids = [...new Set((zone.sourceLayers || []).map(String))].sort();
  if (!ids.length) return { mask: null, rgbPng: '' };
  const includeRgb = zone.coverageMode !== 'remaining';
  const key = `${state.layerMaskRevision}:${state.source.width}x${state.source.height}:${includeRgb ? 'rgb' : 'mask'}:${ids.join('|')}`;
  if (!state.layerMaskCache.has(key)) {
    const pending = encodeSourceLayerScope(state.layers, ids, state.source.width, state.source.height, { includeRgb })
      .catch((error) => { state.layerMaskCache.delete(key); throw error; });
    state.layerMaskCache.set(key, pending);
    while (state.layerMaskCache.size > 8) state.layerMaskCache.delete(state.layerMaskCache.keys().next().value);
  } else {
    const cached = state.layerMaskCache.get(key);
    state.layerMaskCache.delete(key);
    state.layerMaskCache.set(key, cached);
  }
  return state.layerMaskCache.get(key);
}

function sourceLayerScopeIdentity(zone) {
  if (isSingleFlatSource()) return '';
  const ids = [...new Set((zone.sourceLayers || []).map(String))].sort();
  if (!ids.length) return '';
  const includeRgb = zone.coverageMode !== 'remaining';
  return `${state.layerMaskRevision}:${state.source.width}x${state.source.height}:${includeRgb ? 'rgb' : 'mask'}:${ids.join('|')}`;
}

async function zoneToPayload(zone, sharedScope = null) {
  const finish = manifestFinish(zone.finishId);
  const colors = (zone.colors || []).map((entry) => ({
    hex: entry.hex,
    color_rgb: entry.rgb || Object.values(hexToRgb(entry.hex) || { r: 255, g: 0, b: 255 }),
    tolerance: clamp(entry.tolerance ?? 40, 0, 100),
  }));
  const color = hexToRgb(zone.baseColor) || { r: 255, g: 255, b: 255 };
  const coverageMode = zone.coverageMode === 'remaining' ? 'remaining' : 'colors';
  const sourceLayerScope = sharedScope?.scope || await sourceLayerScopeFor(zone);
  const sourceLayerMask = sourceLayerScope.mask;
  const gradientStops = normalizeGradientStops(zone);
  const baseSpecStrength = normalizeSpecStrengthPercent(zone.baseSpecStrength) / 100;
  return {
    name: zone.name,
    enabled: zone.enabled,
    intensity: Number(zone.intensity ?? 100),
    finish_id: zone.finishId,
    finish: zone.finishId,
    base: finish?.kind === 'monolithic' ? `mono:${zone.finishId}` : zone.finishId,
    coverageMode,
    coverage_mode: coverageMode,
    coverageColors: colors,
    coverage_colors: colors,
    colorMode: coverageMode === 'remaining' ? 'special' : 'multi',
    color_mode: coverageMode === 'remaining' ? 'special' : 'multi',
    color: coverageMode === 'remaining' ? 'remaining' : colors,
    colors,
    exclusions: (zone.exclusions || []).map((entry) => ({ ...entry, color_rgb: entry.rgb || Object.values(hexToRgb(entry.hex) || {}) })),
    spatial_mask: zone.spatialMask || null,
    baseColor: [color.r / 255, color.g / 255, color.b / 255],
    sourceLayers: isSingleFlatSource() ? [] : [...(zone.sourceLayers || [])],
    source_layers: isSingleFlatSource() ? [] : [...(zone.sourceLayers || [])],
    source_layer_scope_id: sharedScope?.id || undefined,
    source_layer_mask: sharedScope ? undefined : sourceLayerMask,
    source_layer_rgb_png: sharedScope ? undefined : (sourceLayerScope.rgbPng || null),
    baseColorHex: zone.baseColor,
    baseColorMode: zone.baseColorMode || 'finish',
    baseColorSource: zone.baseColorSource || null,
    lockBaseColor: Boolean(zone.lockBaseColor),
    base_color: [color.r / 255, color.g / 255, color.b / 255],
    base_color_hex: zone.baseColor,
    base_color_mode: zone.baseColorMode || 'finish',
    base_color_source: zone.baseColorSource || null,
    lock_base_color: Boolean(zone.lockBaseColor),
    baseColorStrength: Number(zone.baseColorStrength ?? 100) / 100,
    base_color_strength: Number(zone.baseColorStrength ?? 100) / 100,
    gradientStops,
    gradient_stops: gradientStops,
    gradientDirection: zone.gradientDirection || 'horizontal',
    gradient_direction: zone.gradientDirection || 'horizontal',
    baseHueOffset: Number(zone.baseHueOffset) || 0,
    base_hue_offset: Number(zone.baseHueOffset) || 0,
    baseSaturationAdjust: Number(zone.baseSaturationAdjust) || 0,
    base_saturation_adjust: Number(zone.baseSaturationAdjust) || 0,
    baseBrightnessAdjust: Number(zone.baseBrightnessAdjust) || 0,
    base_brightness_adjust: Number(zone.baseBrightnessAdjust) || 0,
    baseStrength: Number(zone.baseStrength) / 100,
    base_strength: Number(zone.baseStrength) / 100,
    baseSpecStrength,
    base_spec_strength: baseSpecStrength,
    baseScale: Number(zone.baseScale) || 1,
    base_scale: Number(zone.baseScale) || 1,
    baseRotation: Number(zone.baseRotation) || 0,
    base_rotation: Number(zone.baseRotation) || 0,
    baseColorScale: Number(zone.baseColorScale) || 1,
    base_color_scale: Number(zone.baseColorScale) || 1,
    baseColorRotation: Number(zone.baseColorRotation) || 0,
    base_color_rotation: Number(zone.baseColorRotation) || 0,
    baseColorLabEnabled: colorLabActive(zone),
    base_color_lab_enabled: colorLabActive(zone),
    baseColorDepth: colorLabActive(zone) ? Number(zone.baseColorDepth) / 100 : null,
    base_color_depth: colorLabActive(zone) ? Number(zone.baseColorDepth) / 100 : null,
    baseColorFlip: Number(zone.baseColorFlip) || 0,
    base_color_flip: Number(zone.baseColorFlip) || 0,
    baseColorUnderglow: Number(zone.baseColorUnderglow) / 100,
    base_color_underglow: Number(zone.baseColorUnderglow) / 100,
    // Send the RESOLVED values plus the mode, so a linked zone renders spec at Base Scale
    // rather than the stale 1.00x the slider happens to hold.
    specScale: resolveSpecScale(zone),
    spec_scale: resolveSpecScale(zone),
    specScaleMode: specIndependent(zone) ? 'independent' : 'match',
    spec_scale_mode: specIndependent(zone) ? 'independent' : 'match',
    specRotation: resolveSpecRotation(zone),
    spec_rotation: resolveSpecRotation(zone),
    baseSpecBlendMode: zone.specBlendMode || 'normal',
    base_spec_blend_mode: zone.specBlendMode || 'normal',
    specShiftR: Number(zone.specShiftR) || 0,
    specShiftG: Number(zone.specShiftG) || 0,
    specShiftB: Number(zone.specShiftB) || 0,
    spec_channel_shift: [Number(zone.specShiftR) || 0, Number(zone.specShiftG) || 0, Number(zone.specShiftB) || 0],
  };
}

async function buildRenderPayload(preview = false) {
  const renderableZones = state.zones.filter((zone) => zone.enabled && zone.finishId && (
    zone.coverageMode === 'remaining' || (Array.isArray(zone.colors) && zone.colors.length > 0)
  ));
  // A 2048² restricted-layer RGB carrier can be several megabytes. Reuse one
  // top-level scope for Zones with the same restriction instead of duplicating
  // that base64 payload once per Zone.
  const scopeRecords = new Map();
  for (const zone of renderableZones) {
    const identity = sourceLayerScopeIdentity(zone);
    if (!identity || scopeRecords.has(identity)) continue;
    scopeRecords.set(identity, {
      id: `scope-${scopeRecords.size + 1}`,
      promise: sourceLayerScopeFor(zone),
      scope: null,
    });
  }
  await Promise.all([...scopeRecords.values()].map(async (record) => { record.scope = await record.promise; }));
  const zones = await Promise.all(renderableZones.map((zone) => {
    const record = scopeRecords.get(sourceLayerScopeIdentity(zone));
    return zoneToPayload(zone, record || null);
  }));
  const sourceLayerScopes = Object.fromEntries([...scopeRecords.values()].map((record) => [record.id, {
    source_layer_mask: record.scope.mask,
    ...(record.scope.rgbPng ? { source_layer_rgb_png: record.scope.rgbPng } : {}),
  }]));
  return {
    product: 'shokk-demo',
    paint_file: state.source.path,
    source_data_url: state.source.token ? undefined : (state.source.dataUrl || state.source.compositeUrl),
    paint_source_token: state.source.token || undefined,
    zones,
    source_layer_scopes: sourceLayerScopes,
    iracing_id: $('#iracingId').value.trim(),
    car_number: $('#carNumber').value.trim(),
    custom_number: $('#customNumberMode').checked,
    use_custom_number: $('#customNumberMode').checked,
    sim_stamped_number: $('#simNumberMode').checked,
    iracing_car_folder: state.outputFolder,
    output_folder: state.outputFolder,
    output_dir: state.outputFolder,
    seed: 24,
    preview,
    preview_size: preview ? 1024 : undefined,
    preview_scale: preview ? 0.5 : 1,
  };
}

function renderLayerList() {
  const root = $('#layerList');
  root.replaceChildren();
  state.layers.forEach((layer) => {
    const card = document.createElement('article');
    card.className = `layer-card${layer.id === state.selectedLayerId ? ' active' : ''}${layer.visible ? '' : ' muted'}`;
    card.dataset.layerId = layer.id;
    card.innerHTML = `<button class="layer-eye" data-layer-eye="${escapeHtml(layer.id)}" type="button" title="Toggle visibility">${layer.visible ? '◉' : '○'}</button><img class="layer-thumb" alt="" src="${escapeHtml(layer.rasterUrl)}"><div><strong>${escapeHtml(layer.name)}</strong><small>${Math.round(layer.opacity * 100)}% · ${escapeHtml(layer.blendMode)}</small></div>`;
    root.append(card);
  });
  $('#layerCount').textContent = state.layers.length;
}

function layerSlider(key, label, min, max, step, value, unit = '') {
  return `<label class="layer-slider"><span>${label}</span><input type="range" data-layer-slider="${key}" min="${min}" max="${max}" step="${step}" value="${value}"><output>${value}${unit}</output></label>`;
}

function renderLayerControls() {
  const root = $('#layerControls');
  const layer = activeLayer();
  if (!layer) {
    root.className = 'layer-controls empty';
    root.textContent = 'Select a layer with PICK or click a layer card.';
    return;
  }
  root.className = 'layer-controls';
  root.innerHTML = `
    <input id="layerName" type="text" value="${escapeHtml(layer.name)}" maxlength="80" aria-label="Layer name">
    ${layerSlider('opacity', 'Opacity', 0, 100, 1, Math.round(layer.opacity * 100), '%')}
    <label class="layer-slider"><span>Blend</span><select id="layerBlend"><option>normal</option>${['multiply','screen','overlay','darken','lighten','color-dodge','color-burn','hard-light','soft-light','difference','exclusion','hue','saturation','color','luminosity'].map((mode) => `<option value="${mode}"${layer.blendMode === mode ? ' selected' : ''}>${mode}</option>`).join('')}</select><output></output></label>
    ${layerSlider('hue', 'Hue', -180, 180, 1, layer.hue, '°')}
    ${layerSlider('saturation', 'Sat', -100, 100, 1, layer.saturation)}
    ${layerSlider('brightness', 'Bright', -100, 200, 1, layer.brightness)}
    <label class="layer-slider"><span>Overlay</span><input id="layerOverlayColor" type="color" value="${escapeHtml(layer.overlayColor || '#ffffff')}"><output></output></label>
    ${layerSlider('overlayOpacity', 'Overlay', 0, 100, 1, Math.round(layer.overlayOpacity * 100), '%')}
    <div class="layer-control-grid">
      <button data-layer-action="duplicate" type="button">DUPE</button><button data-layer-action="up" type="button">UP</button><button data-layer-action="down" type="button">DOWN</button><button data-layer-action="solo" type="button">SOLO</button>
      <button data-layer-action="flipH" type="button">FLIP H</button><button data-layer-action="flipV" type="button">FLIP V</button><button data-layer-action="rotate" type="button">ROT 90</button><button data-layer-action="delete" type="button">DELETE</button>
    </div>`;
}

async function recomposeSource({ preview = true } = {}) {
  if (!state.layers.length || !state.source.width || !state.source.height) return;
  const generation = ++state.composeGeneration;
  setBusy(true, 'COMPOSING');
  try {
    const composed = await composeLayers(state.layers, state.source.width, state.source.height);
    if (generation !== state.composeGeneration) return;
    state.source.composed = composed;
    state.source.dataUrl = composed.toDataURL('image/png');
    state.source.token = '';
    drawSourceCanvas();
    if (!state.lastPreview) seedMapCanvases(composed);
    renderLiveViewport().catch(() => {});
    if (preview) schedulePreview();
  } catch (error) {
    showToast(`Layer compose failed: ${error.message}`, true);
  } finally {
    if (generation === state.composeGeneration) setBusy(false, 'READY');
  }
}

function scheduleCompose() {
  state.layerMaskRevision += 1;
  state.layerMaskCache.clear();
  clearTimeout(state.composeTimer);
  state.composeTimer = setTimeout(() => recomposeSource(), 130);
}

function previewBounds(stage, zoom = 1) {
  const rect = stage.getBoundingClientRect();
  return { width: Math.max(180, (rect.width - 12) * zoom), height: Math.max(180, (rect.height - 12) * zoom) };
}

function viewportElements(kind) {
  return {
    stage: $(`#${kind}Stage`),
    canvas: $(`#${kind}Canvas`),
    output: $(`#${kind}ZoomValue`),
  };
}

function captureViewportAnchor(kind, event = null) {
  const { stage, canvas } = viewportElements(kind);
  if (!stage || !canvas || !canvas.width || !canvas.height) return null;
  const stageRect = stage.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  const clientX = event ? event.clientX : stageRect.left + stageRect.width / 2;
  const clientY = event ? event.clientY : stageRect.top + stageRect.height / 2;
  return calculateViewportAnchor(stageRect, canvasRect, clientX, clientY);
}

function restoreViewportAnchor(kind, anchor) {
  if (!anchor) return;
  const { stage, canvas } = viewportElements(kind);
  const stageRect = stage.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();
  const anchoredX = canvasRect.left + canvasRect.width * anchor.imageX;
  const anchoredY = canvasRect.top + canvasRect.height * anchor.imageY;
  stage.scrollLeft += anchoredX - (stageRect.left + anchor.localX);
  stage.scrollTop += anchoredY - (stageRect.top + anchor.localY);
}

function updateViewportZoomChrome(kind) {
  const { stage, output } = viewportElements(kind);
  const zoom = state.viewportZoom[kind];
  output.textContent = `${Math.round(zoom * 100)}%`;
  output.title = zoom === 1 ? 'Fit to view' : `${Math.round(zoom * 100)}% of fitted size`;
  stage.classList.toggle('is-zoomed', zoom > 1.001);
}

function drawSourceCanvas(anchor = null) {
  if (!state.source.composed) return;
  const bounds = previewBounds($('#sourceStage'), state.viewportZoom.source);
  paintCanvasFrom(state.source.composed, $('#sourceCanvas'), bounds.width, bounds.height);
  restoreViewportAnchor('source', anchor);
}

function seedMapCanvases(source) {
  const targets = ['combinedCanvas', 'metalCanvas', 'roughCanvas', 'clearcoatCanvas'];
  targets.forEach((id) => {
    const canvas = $(`#${id}`);
    const rect = canvas.parentElement.getBoundingClientRect();
    paintCanvasFrom(source, canvas, Math.max(60, rect.width), Math.max(60, rect.height));
  });
}

async function displayPreview(result) {
  state.lastPreview = result;
  if (result.sourceToken) state.source.token = result.sourceToken;
  const maps = [
    ['combinedCanvas', result.combined], ['metalCanvas', result.metal],
    ['roughCanvas', result.rough], ['clearcoatCanvas', result.clearcoat],
  ];
  for (const [id, url] of maps) {
    if (!url) continue;
    const canvas = $(`#${id}`);
    const rect = canvas.parentElement.getBoundingClientRect();
    await paintCanvasFromUrl(url, canvas, Math.max(60, rect.width), Math.max(60, rect.height));
  }
  if (result.combined) {
    const combined = $('#combinedCanvas');
    if (!result.metal) drawChannel(combined, $('#metalCanvas'), 0, [255, 50, 50]);
    if (!result.rough) drawChannel(combined, $('#roughCanvas'), 1, [40, 255, 90]);
    if (!result.clearcoat) drawChannel(combined, $('#clearcoatCanvas'), 2, [50, 100, 255]);
  }
  await renderLiveViewport();
  $('#previewNotice').textContent = result.elapsedMs ? `${(result.elapsedMs / 1000).toFixed(1)}s` : 'updated';
}

async function resolveMapVisual(key) {
  const channel = MAP_CHANNELS[key];
  if (!channel) return null;
  const url = state.lastPreview?.[channel.resultKey] || '';
  if (url) return loadImage(url);
  const canvas = $(`#${channel.canvasId}`);
  return canvas?.width && canvas?.height ? canvas : null;
}

async function renderLiveViewport(anchor = null) {
  const generation = ++state.liveDisplayGeneration;
  let visual = null;
  if (state.hoveredMap) visual = await resolveMapVisual(state.hoveredMap);
  else if (state.lastPreview?.paint) visual = await loadImage(state.lastPreview.paint);
  else visual = state.source.composed;
  if (generation !== state.liveDisplayGeneration || !visual) return;
  const bounds = previewBounds($('#liveStage'), state.viewportZoom.live);
  paintCanvasFrom(visual, $('#liveCanvas'), bounds.width, bounds.height);
  restoreViewportAnchor('live', anchor);
}

function setHoveredMap(key = '') {
  state.hoveredMap = MAP_CHANNELS[key] ? key : '';
  $$('.map-card').forEach((card) => card.classList.toggle('previewing', card.dataset.map === state.hoveredMap));
  const channel = MAP_CHANNELS[state.hoveredMap];
  $('#livePreviewLabel').textContent = channel ? `${channel.label} · HOVER PREVIEW` : 'LIVE PREVIEW';
  $('.preview-label.live').classList.toggle('channel-peek', Boolean(channel));
  renderLiveViewport().catch((error) => showToast(`Preview display: ${error.message}`, true));
}

async function drawChannelInspector() {
  const dialog = $('#channelInspectDialog');
  const key = state.channelInspectKey;
  if (!dialog.open || !MAP_CHANNELS[key]) return;
  const generation = ++state.channelInspectGeneration;
  const visual = await resolveMapVisual(key);
  if (!visual || generation !== state.channelInspectGeneration || !dialog.open) return;
  const stage = $('#channelInspectStage');
  const rect = stage.getBoundingClientRect();
  paintCanvasFrom(visual, $('#channelInspectCanvas'), Math.max(180, rect.width - 28), Math.max(180, rect.height - 28));
}

function openChannelInspector(key) {
  const channel = MAP_CHANNELS[key];
  if (!channel) return;
  setHoveredMap('');
  state.channelInspectKey = key;
  $('#channelInspectTitle').textContent = channel.label;
  const dialog = $('#channelInspectDialog');
  if (!dialog.open) dialog.showModal();
  requestAnimationFrame(() => drawChannelInspector().catch((error) => showToast(`Map inspection: ${error.message}`, true)));
}

function setViewportZoom(kind, nextZoom, event = null) {
  const anchor = captureViewportAnchor(kind, event);
  state.viewportZoom[kind] = clampViewportZoom(nextZoom);
  updateViewportZoomChrome(kind);
  if (kind === 'source') drawSourceCanvas(anchor);
  else renderLiveViewport(anchor).catch((error) => showToast(`Preview zoom: ${error.message}`, true));
}

function schedulePreview(delay = 320) {
  clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(previewNow, delay);
}

async function previewNow() {
  if (state.isPreviewing) { state.previewQueued = true; return; }
  if (!state.source.composed || !state.zones.length) return;
  state.isPreviewing = true;
  state.previewQueued = false;
  const generation = ++state.previewGeneration;
  $('#previewSpinner').hidden = false;
  $('#previewNotice').textContent = 'rendering…';
  try {
    const raw = await postJSON('/preview-render', await buildRenderPayload(true));
    if (generation !== state.previewGeneration) return;
    await displayPreview(normalizePreview(raw));
  } catch (error) {
    $('#previewNotice').textContent = 'preview unavailable';
    showToast(`Live preview: ${error.message}`, true);
  } finally {
    if (generation === state.previewGeneration) {
      state.isPreviewing = false;
      $('#previewSpinner').hidden = true;
      if (state.previewQueued) schedulePreview(30);
    }
  }
}

async function installImportedSource(raw, requestedPath = '') {
  const composite = raw.composite || raw.composite_data_url || raw.image || raw.preview || raw.data_url;
  if (!composite) throw new Error('The source importer did not return a composite image.');
  clearImageCache();
  const image = await new Promise((resolve, reject) => {
    const item = new Image(); item.onload = () => resolve(item); item.onerror = () => reject(new Error('The source composite could not be decoded.')); item.src = composite;
  });
  const nextPath = raw.psd_path || raw.paint_file || raw.path || requestedPath;
  const changedDocument = Boolean(state.source.path &&
    (state.source.path !== nextPath || state.source.compositeUrl !== composite));
  excludeBrush?.reset();
  // Supersede any in-flight render of the outgoing document before publishing
  // the new source. Its late preview/token must not replace this import.
  state.previewGeneration += 1;
  state.isPreviewing = false;
  state.previewQueued = false;
  clearTimeout(state.previewTimer);
  state.source.path = nextPath;
  state.source.isFlat = !/\.(psd|psb)$/i.test(nextPath);
  state.source.width = Number(raw.width) || image.naturalWidth;
  state.source.height = Number(raw.height) || image.naturalHeight;
  state.source.compositeUrl = composite;
  state.source.dataUrl = '';
  state.source.token = '';
  state.viewportZoom.source = 1;
  state.viewportZoom.live = 1;
  updateViewportZoomChrome('source');
  updateViewportZoomChrome('live');
  $('#sourcePath').textContent = basename(state.source.path) || 'Imported source';
  $('#sourcePath').title = state.source.path;
  $('#sourceDimensions').textContent = `${state.source.width} × ${state.source.height}`;

  const flat = flattenLayerTree(raw.layers || []);
  let rasterized = {};
  if (flat.length && state.source.path) {
    try { rasterized = await postJSON('/api/psd-rasterize-all', { psd_path: state.source.path }); }
    catch (error) { showToast(`Loaded composite; editable layers were unavailable: ${error.message}`, true); }
  }
  state.layers = attachRasterizedLayers(flat, rasterized, composite, state.source.width, state.source.height);
  state.layerMaskRevision += 1;
  state.layerMaskCache.clear();
  state.selectedLayerId = state.layers[0]?.id || '';
  state.lastPreview = null;
  renderLayerList();
  renderLayerControls();
  await recomposeSource({ preview: false });

  if (!activeZone()) {
    state.zones = createDefaultZones();
    state.selectedZoneId = state.zones[0].id;
  }
  prepareImportedZoneScopes(state.zones, state.layers, state.source.isFlat, changedDocument);
  // A saved mask cannot be resized behind the cursor's back if a file changed.
  state.zones.forEach((zone) => {
    if (zone.spatialMask && (zone.spatialMask.width !== state.source.width || zone.spatialMask.height !== state.source.height)) zone.spatialMask = null;
  });
  renderZones();
  renderZoneEditor();
  drawSourceCanvas();
  schedulePreview(50);
  saveSession();
}

async function importSourcePath(path) {
  if (!path) return;
  setBusy(true, 'LOADING SOURCE');
  try {
    const extension = (path.split('.').pop() || '').toLowerCase();
    let raw;
    if (['psd', 'psb'].includes(extension)) {
      raw = await postJSON('/api/psd-import', { psd_path: path, thumbnail_size: 160 });
    } else {
      raw = await postImage('/preview-tga', { path, paint_file: path });
      raw.path = path;
    }
    await installImportedSource(raw, path);
    showToast(`Loaded ${basename(path)}`);
  } finally {
    setBusy(false, 'READY');
  }
}

async function importBrowserFile(file) {
  if (!file) return;
  setBusy(true, 'UPLOADING');
  try {
    const extension = (file.name.split('.').pop() || '').toLowerCase();
    if (['png', 'jpg', 'jpeg'].includes(extension)) {
      const dataUrl = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file); });
      await installImportedSource({ composite: dataUrl, width: 0, height: 0, path: file.name }, file.name);
    } else {
      const form = new FormData(); form.append('file', file); form.append('thumbnail_size', '160');
      const endpoint = ['psd', 'psb'].includes(extension) ? '/api/psd-import' : '/preview-tga';
      const raw = endpoint === '/preview-tga' ? await postImage(endpoint, form) : await postForm(endpoint, form);
      await installImportedSource(raw, file.name);
    }
  } finally {
    setBusy(false, 'READY');
  }
}

async function loadInitialSource(session) {
  let path = session?.sourcePath || '';
  if (path) {
    try {
      const check = await postJSON('/check-file', { path }, 10_000);
      if (!(check.is_file || check.exists)) path = '';
    } catch (_) { path = ''; }
  }
  if (!path) {
    const defaults = await getJSON('/api/default-assets');
    const assets = defaults.assets || defaults;
    path = assets.starter_psd || assets.source || assets.paint_file || '';
  }
  if (!path) throw new Error('The bundled ARCA Chevy starter PSD is missing.');
  // Saved brush coordinates belong to the saved document, not a fallback car.
  if (session?.sourcePath && session.sourcePath !== path) {
    state.zones.forEach((zone) => { zone.spatialMask = null; });
  }
  await importSourcePath(path);
}

function setTool(tool, intent = tool === 'pick' ? 'item' : 'exclude') {
  excludeBrush?.cancel();
  state.tool = tool;
  state.pickIntent = intent;
  $('#pickTool').classList.toggle('active', tool === 'pick');
  $('#excludeTool').classList.toggle('active', tool === 'exclude');
  $('#pickTool').setAttribute('aria-pressed', tool === 'pick');
  $('#excludeTool').setAttribute('aria-pressed', tool === 'exclude');
  $('#toolHint').textContent = tool === 'exclude'
    ? 'Draw on SOURCE or LIVE. Shift = restore. [ ] = size. Ctrl+Z = undo. Esc = cancel stroke.'
    : intent === 'color' ? 'Add Color is armed: click the source paint.' : 'Pick Item: click the source to select a PSD layer. Use + Add Color to build a paint zone.';
  $('#pickReticle').hidden = true;
  excludeBrush?.refresh();
}

function addZoneColor(zone, pixel, exclusion = false) {
  const collection = exclusion ? (zone.exclusions ||= []) : (zone.colors ||= []);
  if (collection.some((entry) => entry.hex === pixel.hex)) {
    showToast(`${pixel.hex} is already ${exclusion ? 'excluded' : 'in this zone'}.`, true);
    return;
  }
  collection.push({ hex: pixel.hex, rgb: [pixel.r, pixel.g, pixel.b], tolerance: zone.pickerTolerance ?? 40 });
  if (!exclusion) { zone.color = pixel.hex; zone.coverageMode = 'colors'; }
  renderZones();
  renderZoneEditor();
  schedulePreview();
  saveSession();
  showToast(`${exclusion ? 'Excluded' : 'Added'} ${pixel.hex} ${exclusion ? 'from' : 'to'} ${zone.name}`);
}

function rleMaskContains(mask, x, y) {
  if (!mask || !Array.isArray(mask.runs)) return true;
  const target = Math.max(0, Math.min(mask.width * mask.height - 1, Math.floor(y) * mask.width + Math.floor(x)));
  let cursor = 0;
  for (const run of mask.runs) {
    cursor += Number(run[1]) || 0;
    if (target < cursor) return Number(run[0]) > 0;
  }
  return false;
}

async function onSourcePointer(event) {
  if (!state.source.composed || state.tool === 'exclude' || event.button !== 0) return;
  const displayCanvas = $('#sourceCanvas');
  const point = canvasPoint(event, displayCanvas, state.source.width, state.source.height);
  const pixel = samplePixel(state.source.composed, point.x, point.y);
  const reticle = $('#pickReticle');
  reticle.hidden = false;
  reticle.style.left = `${event.clientX}px`;
  reticle.style.top = `${event.clientY}px`;
  const zone = activeZone();
  if (state.pickIntent === 'color') {
    if (zone) {
      addZoneColor(zone, pixel, false);
      if ((zone.sourceLayers || []).length) {
        const scope = await sourceLayerScopeFor(zone);
        if (!rleMaskContains(scope.mask, point.x, point.y)) {
          showToast(`Color added, but that spot is outside ${zone.name}'s selected layers and will not paint there.`, true);
        }
      }
    }
    setTool('pick', 'item');
    return;
  }
  const layer = hitTestLayers(state.layers, point.x, point.y);
  if (layer) {
    state.selectedLayerId = layer.id;
    renderLayerList();
    renderLayerControls();
    $('#selectionStatus').textContent = `Layer: ${layer.name} · ${pixel.hex}`;
    showToast(`Picked layer: ${layer.name}`);
  } else {
    $('#selectionStatus').textContent = `Source color: ${pixel.hex}`;
  }
}

async function doRender() {
  if (state.isRendering || !state.source.composed) return;
  if (!state.outputFolder) {
    showToast('Choose your iRacing Car Folder before rendering.', true);
    await chooseOutputFolder();
    if (!state.outputFolder) return;
  }
  state.isRendering = true;
  $('#renderButton').disabled = true;
  const started = performance.now();
  setBusy(true, 'RENDERING');
  try {
    const raw = await postJSON('/render', await buildRenderPayload(false));
    const result = normalizePreview(raw);
    await displayPreview(result);
    const elapsed = result.elapsedMs || (performance.now() - started);
    $('#renderTime').textContent = `${(elapsed / 1000).toFixed(1)} seconds`;
    $('#renderState').textContent = 'COMPLETE';
    const downloads = $('#renderDownloads');
    downloads.replaceChildren();
    Object.entries(result.downloadUrls || {}).forEach(([label, url]) => {
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = '';
      anchor.textContent = `Download ${label.replaceAll('_', ' ')}`;
      downloads.append(anchor);
    });
    $('#renderResultText').textContent = result.outputPath
      ? `Saved to ${result.outputPath}`
      : 'Your paint and material maps are ready in the selected iRacing folder.';
    $('#renderDialog').showModal();
    showToast('Render complete — your SHOKK paint is ready.');
    saveSession();
  } catch (error) {
    $('#renderState').textContent = 'FAILED';
    showToast(`Render failed: ${error.message}`, true);
  } finally {
    state.isRendering = false;
    $('#renderButton').disabled = false;
    setBusy(false);
  }
}

async function chooseSource() {
  try {
    const path = await selectSourceFile();
    if (path) await importSourcePath(path);
    else if (!window.shokkDemo) $('#browserSourceInput').click();
  } catch (error) { showToast(error.message, true); }
}

async function chooseOutputFolder() {
  try {
    const path = await selectIRacingFolder();
    if (!path) return;
    state.outputFolder = path;
    $('#outputPath').textContent = path;
    $('#outputPath').title = path;
    saveSession();
    showToast('iRacing output folder set.');
  } catch (error) { showToast(error.message, true); }
}

function mutateLayer(action) {
  const layer = activeLayer();
  if (!layer) return;
  const index = state.layers.indexOf(layer);
  if (action === 'duplicate') {
    const duplicate = { ...layer, id: crypto.randomUUID ? crypto.randomUUID() : `${layer.id}-copy-${Date.now()}`, name: `${layer.name} Copy`, _surface: null };
    state.layers.splice(index, 0, duplicate);
    state.selectedLayerId = duplicate.id;
  } else if (action === 'up' && index > 0) {
    [state.layers[index - 1], state.layers[index]] = [state.layers[index], state.layers[index - 1]];
  } else if (action === 'down' && index < state.layers.length - 1) {
    [state.layers[index + 1], state.layers[index]] = [state.layers[index], state.layers[index + 1]];
  } else if (action === 'solo') {
    const onlyThis = state.layers.some((entry) => entry.id !== layer.id && entry.visible);
    state.layers.forEach((entry) => { entry.visible = onlyThis ? entry.id === layer.id : true; });
  } else if (action === 'flipH') layer.flipH = !layer.flipH;
  else if (action === 'flipV') layer.flipV = !layer.flipV;
  else if (action === 'rotate') layer.rotation = ((Number(layer.rotation) || 0) + 90) % 360;
  else if (action === 'delete' && state.layers.length > 1) {
    state.layers.splice(index, 1);
    state.selectedLayerId = state.layers[Math.min(index, state.layers.length - 1)]?.id || '';
  }
  renderLayerList();
  renderLayerControls();
  renderZoneEditor();
  scheduleCompose();
}

function wireEvents() {
  excludeBrush = installExcludeBrush({
    getContext: () => state.source.composed && activeZone() ? {
      zone: activeZone(), width: state.source.width, height: state.source.height,
      key: state.source.path + ':' + state.source.width + 'x' + state.source.height,
    } : null,
    isActive: () => state.tool === 'exclude',
    onCommit: () => { schedulePreview(30); saveSession(); },
    onStatus: showToast,
  });
  $('#pickTool').addEventListener('click', () => setTool('pick', 'item'));
  $('#excludeTool').addEventListener('click', () => setTool('exclude'));
  $('#sourceCanvas').addEventListener('pointerdown', onSourcePointer);
  $('#chooseSource').addEventListener('click', chooseSource);
  $('#sourcePath').addEventListener('click', chooseSource);
  $('#chooseOutput').addEventListener('click', chooseOutputFolder);
  $('#outputPath').addEventListener('click', chooseOutputFolder);
  $('#renderButton').addEventListener('click', doRender);
  $('#browserSourceInput').addEventListener('change', (event) => importBrowserFile(event.target.files?.[0]).catch((error) => showToast(error.message, true)));
  $('#finishSearch').addEventListener('input', renderFinishGrid);
  $('#unlockButton').addEventListener('click', () => openExternal(state.manifest.links.payhip || SAFE_PAYHIP).catch((error) => showToast(error.message, true)));
  $('#dialogUnlock').addEventListener('click', () => openExternal(state.manifest.links.payhip || SAFE_PAYHIP).catch((error) => showToast(error.message, true)));
  $('#renderUnlock').addEventListener('click', () => openExternal(state.manifest.links.payhip || SAFE_PAYHIP).catch((error) => showToast(error.message, true)));
  $('#discordButton').addEventListener('click', () => openExternal(state.manifest.links.discord || SAFE_DISCORD).catch((error) => showToast(error.message, true)));
  $('#renderDiscord').addEventListener('click', () => openExternal(state.manifest.links.discord || SAFE_DISCORD).catch((error) => showToast(error.message, true)));
  $('#closeRenderDialog').addEventListener('click', () => $('#renderDialog').close());
  $('#renderDialog').addEventListener('click', (event) => { if (event.target === $('#renderDialog')) $('#renderDialog').close(); });
  $('#closeChannelInspect').addEventListener('click', () => $('#channelInspectDialog').close());
  $('#channelInspectDialog').addEventListener('click', (event) => { if (event.target === $('#channelInspectDialog')) event.target.close(); });
  $('#channelInspectDialog').addEventListener('cancel', (event) => {
    event.preventDefault();
    event.currentTarget.close();
  });
  $('#channelInspectDialog').addEventListener('close', () => {
    state.channelInspectGeneration += 1;
    state.channelInspectKey = '';
  });
  window.addEventListener('keydown', (event) => {
    if (['Escape', 'Esc', 'ESC'].includes(event.key) && $('#channelInspectDialog').open) $('#channelInspectDialog').close();
  });
  $('#reloadLayers').addEventListener('click', () => state.source.path && importSourcePath(state.source.path).catch((error) => showToast(error.message, true)));
  $('#outputPath').addEventListener('contextmenu', (event) => { event.preventDefault(); if (state.outputFolder) revealPath(state.outputFolder); });

  $('#addZone').addEventListener('click', () => {
    if (state.zones.length >= MAX_ZONES) return showToast(`The demo supports up to ${MAX_ZONES} zones.`, true);
    const zone = createZone();
    const catchAll = state.zones.findIndex((entry) => entry.coverageMode === 'remaining');
    state.zones.splice(catchAll >= 0 ? catchAll : state.zones.length, 0, zone);
    state.selectedZoneId = zone.id; renderZones(); renderZoneEditor(); saveSession();
  });
  $('#resetZones').addEventListener('click', () => {
    excludeBrush?.reset();
    state.zones = createDefaultZones(); state.selectedZoneId = state.zones[0].id; renderZones(); renderZoneEditor(); schedulePreview(); saveSession();
  });
  $('#resetZone').addEventListener('click', () => {
    const zone = activeZone(); if (!zone) return;
    excludeBrush?.reset();
    const index = state.zones.indexOf(zone);
    const fresh = createDefaultZones()[index] || createZone(index);
    Object.assign(zone, fresh, { id: zone.id, name: zone.name });
    renderZones(); renderZoneEditor(); schedulePreview(); saveSession();
  });

  $('#zoneList').addEventListener('click', (event) => {
    const card = event.target.closest('.zone-card'); if (!card) return;
    const zone = state.zones.find((entry) => entry.id === card.dataset.zoneId); if (!zone) return;
    const action = event.target.closest('[data-zone-action]')?.dataset.zoneAction;
    if (action === 'toggle') zone.enabled = !zone.enabled;
    else if (action === 'up') {
      const index = state.zones.indexOf(zone); if (index > 0) [state.zones[index - 1], state.zones[index]] = [state.zones[index], state.zones[index - 1]];
    } else if (action === 'down') {
      const index = state.zones.indexOf(zone); if (index < state.zones.length - 1) [state.zones[index + 1], state.zones[index]] = [state.zones[index], state.zones[index + 1]];
    }
    else if (action === 'duplicate') {
      const duplicate = { ...structuredClone(zone), id: crypto.randomUUID ? crypto.randomUUID() : `${zone.id}-copy-${Date.now()}`, name: `${zone.name} Copy` };
      const zoneIndex = state.zones.indexOf(zone);
      state.zones.splice(zone.coverageMode === 'remaining' ? zoneIndex : zoneIndex + 1, 0, duplicate); state.selectedZoneId = duplicate.id;
    } else if (action === 'delete' && state.zones.length > 1) {
      const index = state.zones.indexOf(zone); state.zones.splice(index, 1); state.selectedZoneId = state.zones[Math.min(index, state.zones.length - 1)].id;
    } else state.selectedZoneId = zone.id;
    renderZones(); renderZoneEditor(); schedulePreview(); saveSession();
  });

  $('#zoneEditor').addEventListener('click', (event) => {
    const zone = activeZone(); if (!zone) return;
    if (event.target.closest('#finishTrigger')) { openFinishPicker('material'); return; }
    if (event.target.closest('#specialColorTrigger')) { openFinishPicker('special'); return; }
    if (event.target.closest('#addColorPick')) { setTool('pick', 'color'); showToast('Click a color on the SOURCE paint.'); return; }
    if (event.target.closest('#clearPickedColors')) { zone.colors = []; renderZones(); renderZoneEditor(); schedulePreview(); saveSession(); return; }
    if (event.target.closest('#clearLayerRestriction')) { zone.sourceLayers = []; zone.sourceLayer = null; renderZones(); renderZoneEditor(); schedulePreview(); saveSession(); showToast('Zone restriction removed — applies to all layers.'); return; }
    if (event.target.closest('#addGradientStop')) {
      const stops = normalizeGradientStops(zone);
      if (stops.length >= 10) return;
      let insertAt = 1; let widest = -1;
      for (let index = 1; index < stops.length; index += 1) {
        const gap = stops[index].position - stops[index - 1].position;
        if (gap > widest) { widest = gap; insertAt = index; }
      }
      const before = stops[insertAt - 1]; const after = stops[insertAt];
      zone.gradientStops = [...stops.slice(0, insertAt), { position: (before.position + after.position) / 2, color: before.color }, ...stops.slice(insertAt)];
      renderZoneEditor(); schedulePreview(); saveSession(); return;
    }
    const colorIndex = event.target.closest('[data-remove-color]')?.dataset.removeColor;
    if (colorIndex != null) { zone.colors.splice(Number(colorIndex), 1); renderZones(); renderZoneEditor(); schedulePreview(); saveSession(); return; }
    const exclusionIndex = event.target.closest('[data-remove-exclusion]')?.dataset.removeExclusion;
    if (exclusionIndex != null) { zone.exclusions.splice(Number(exclusionIndex), 1); renderZoneEditor(); schedulePreview(); saveSession(); return; }
    const stopIndex = event.target.closest('[data-remove-gradient-stop]')?.dataset.removeGradientStop;
    if (stopIndex != null && normalizeGradientStops(zone).length > 2) { zone.gradientStops.splice(Number(stopIndex), 1); renderZoneEditor(); schedulePreview(); saveSession(); return; }
    const row = event.target.closest('[data-slider-row]');
    if (row && event.target.dataset.step) {
      const definition = sliderDefinitions.find((item) => item.key === row.dataset.sliderRow);
      zone[definition.key] = clamp(Number(zone[definition.key]) + Number(event.target.dataset.step) * definition.step, definition.min, definition.max);
      renderZoneEditor(); schedulePreview(); saveSession();
    }
    const resetKey = event.target.dataset.resetSlider;
    if (resetKey) {
      const definition = sliderDefinitions.find((item) => item.key === resetKey); zone[resetKey] = definition.reset;
      renderZoneEditor(); schedulePreview(); saveSession();
    }
  });

  $('#zoneEditor').addEventListener('input', (event) => {
    const zone = activeZone(); if (!zone) return;
    if (event.target.matches('[data-zone-slider]')) {
      const key = event.target.dataset.zoneSlider; const definition = sliderDefinitions.find((item) => item.key === key);
      zone[key] = key === 'baseSpecStrength' ? normalizeSpecStrengthPercent(event.target.value) : Number(event.target.value); event.target.closest('.slider-row').querySelector('output').textContent = formatSlider(definition, zone[key]); schedulePreview();
    } else if (event.target.matches('[data-color-tolerance]')) {
      const entry = zone.colors[Number(event.target.dataset.colorTolerance)];
      if (entry) { entry.tolerance = Number(event.target.value); event.target.closest('.tolerance-control').querySelector('output').textContent = `±${entry.tolerance}`; schedulePreview(); }
    } else if (event.target.id === 'baseColorPicker' || event.target.id === 'baseColorText') {
      const value = event.target.value.toUpperCase();
      if (hexToRgb(value)) {
        zone.baseColor = value;
        zone.baseColorMode = 'solid';
        const other = event.target.id === 'baseColorPicker' ? $('#baseColorText') : $('#baseColorPicker');
        if (other) other.value = value;
        schedulePreview();
      }
    } else if (event.target.matches('[data-gradient-color]')) {
      const stop = zone.gradientStops[Number(event.target.dataset.gradientColor)];
      if (stop) { stop.color = event.target.value.toUpperCase(); schedulePreview(); }
    } else if (event.target.matches('[data-gradient-position]')) {
      const stop = zone.gradientStops[Number(event.target.dataset.gradientPosition)];
      if (stop) { stop.position = Number(event.target.value) / 100; event.target.closest('.gradient-stop').querySelector('output').textContent = `${event.target.value}%`; schedulePreview(); }
    }
  });
  $('#zoneEditor').addEventListener('change', (event) => {
    const zone = activeZone(); if (!zone) return;
    if (event.target.id === 'baseColorLabEnabled') { zone.baseColorLabEnabled = event.target.checked; renderZoneEditor(); schedulePreview(); }
    else if (event.target.id === 'specBlendMode') { zone.specBlendMode = event.target.value; schedulePreview(); }
    else if (event.target.name === 'coverage-mode') { zone.coverageMode = event.target.value === 'remaining' ? 'remaining' : 'colors'; renderZoneEditor(); schedulePreview(); }
    else if (event.target.matches('[data-zone-layer]')) {
      const id = event.target.dataset.zoneLayer;
      zone.sourceLayers = (zone.sourceLayers || []).filter((entry) => String(entry) !== id);
      if (event.target.checked) zone.sourceLayers.push(id);
      zone.sourceLayer = zone.sourceLayers[0] || null;
      renderZones(); renderZoneEditor(); schedulePreview();
    } else if (event.target.id === 'baseColorMode') {
      zone.baseColorMode = event.target.value;
      if (zone.baseColorMode !== 'special') zone.baseColorSource = '';
      renderZoneEditor(); schedulePreview();
    } else if (event.target.id === 'specScaleIndependent') {
      // Unlinking seeds the spec dials from the base ones, so the first render after the
      // tick looks identical and the sliders start from where the eye already is.
      if (event.target.checked) {
        zone.specScale = resolveSpecScale(zone);
        zone.specRotation = resolveSpecRotation(zone);
        zone.specScaleMode = 'independent';
      } else {
        zone.specScaleMode = 'match';
      }
      renderZoneEditor(); schedulePreview();
    } else if (event.target.id === 'lockBaseColor') zone.lockBaseColor = event.target.checked;
    else if (event.target.id === 'gradientDirection') { zone.gradientDirection = event.target.value; schedulePreview(); }
    renderZones(); saveSession();
  });

  $('#fractureButton').addEventListener('click', () => {
    const fracture = { id: state.manifest.fractureFinishId, name: 'Soul Core Emerald / Pink Flash', collection: 'Fractured Souls', swatch: '#18d98b' };
    // FRACTURE is a real material selection: unlocked Base Color follows its
    // Emerald/Pink paint, while the owner's explicit Base Color lock is honored.
    // The shortcut fractures the existing artwork; keep its source-responsive
    // finish path. Ordinary Base Material picks use their matching special.
    chooseFinish(fracture, { useFinishColor: true });
    showToast(`Fractured ${activeZone()?.name || 'paint'} — Soul Core Emerald / Pink Flash`);
  });

  $('#layerList').addEventListener('click', (event) => {
    const card = event.target.closest('.layer-card'); if (!card) return;
    const layer = state.layers.find((entry) => entry.id === card.dataset.layerId); if (!layer) return;
    if (event.target.closest('[data-layer-eye]')) { layer.visible = !layer.visible; renderZoneEditor(); scheduleCompose(); }
    state.selectedLayerId = layer.id; renderLayerList(); renderLayerControls();
  });
  $('#layerControls').addEventListener('click', (event) => { const action = event.target.closest('[data-layer-action]')?.dataset.layerAction; if (action) mutateLayer(action); });
  $('#layerControls').addEventListener('input', (event) => {
    const layer = activeLayer(); if (!layer) return;
    if (event.target.matches('[data-layer-slider]')) {
      const key = event.target.dataset.layerSlider; const value = Number(event.target.value);
      layer[key] = ['opacity', 'overlayOpacity'].includes(key) ? value / 100 : value;
      event.target.closest('.layer-slider').querySelector('output').textContent = `${value}${['opacity','overlayOpacity'].includes(key) ? '%' : key === 'hue' ? '°' : ''}`;
      if (key === 'opacity') renderLayerList();
      scheduleCompose();
    } else if (event.target.id === 'layerName') { layer.name = event.target.value; renderLayerList(); }
    else if (event.target.id === 'layerOverlayColor') { layer.overlayColor = event.target.value; scheduleCompose(); }
  });
  $('#layerControls').addEventListener('change', (event) => {
    const layer = activeLayer(); if (!layer) return;
    if (event.target.id === 'layerBlend') { layer.blendMode = event.target.value; renderLayerList(); scheduleCompose(); }
    else if (event.target.id === 'layerName') renderZoneEditor();
  });

  ['source', 'live'].forEach((kind) => {
    $(`#${kind}ZoomIn`).addEventListener('click', () => setViewportZoom(kind, stepViewportZoom(state.viewportZoom[kind], 1)));
    $(`#${kind}ZoomOut`).addEventListener('click', () => setViewportZoom(kind, stepViewportZoom(state.viewportZoom[kind], -1)));
    $(`#${kind}ZoomFit`).addEventListener('click', () => setViewportZoom(kind, 1));
    $(`#${kind}Stage`).addEventListener('wheel', (event) => {
      event.preventDefault();
      setViewportZoom(kind, wheelViewportZoom(state.viewportZoom[kind], event.deltaY), event);
    }, { passive: false });
    updateViewportZoomChrome(kind);
  });
  $$('.map-card').forEach((card) => {
    card.addEventListener('mouseenter', () => setHoveredMap(card.dataset.map));
    card.addEventListener('mouseleave', () => { if (state.hoveredMap === card.dataset.map) setHoveredMap(''); });
    card.addEventListener('click', () => openChannelInspector(card.dataset.map));
  });
  window.addEventListener('resize', () => {
    drawSourceCanvas();
    renderLiveViewport().catch(() => {});
    if ($('#channelInspectDialog').open) drawChannelInspector().catch(() => {});
  });
  ['iracingId','carNumber','customNumberMode','simNumberMode'].forEach((id) => $(`#${id}`).addEventListener('change', saveSession));
}

async function init() {
  wireEvents();
  setBusy(true, 'STARTING');
  try {
    const [health, manifestRaw] = await Promise.all([getJSON('/api/demo/health'), getJSON('/api/demo-manifest')]);
    if (health.product !== 'shokk-demo') throw new Error('Refusing to connect to a non-demo render server.');
    state.manifest = normalizeManifest(manifestRaw);
    state.manifest.links.payhip = SAFE_PAYHIP;
    state.manifest.links.discord = SAFE_DISCORD;
    if (state.manifest.finishes.length !== 29) throw new Error(`Demo catalog integrity check failed: expected 29 finishes, received ${state.manifest.finishes.length}.`);
    if (state.manifest.baseColorSources.length !== 30) throw new Error(`Demo color-source integrity check failed: expected 30 choices, received ${state.manifest.baseColorSources.length}.`);
    const session = readSession();
    state.zones = createDefaultZones();
    state.selectedZoneId = state.zones[0].id;
    restoreControls(session);
    renderZones(); renderZoneEditor(); renderFinishFilters(); renderFinishGrid();
    await loadInitialSource(session);
    $('#app').setAttribute('aria-busy', 'false');
    $('#renderState').textContent = 'READY';
    $('#renderTime').textContent = `Demo ${state.manifest.version}`;
  } catch (error) {
    console.error(error);
    $('#renderState').textContent = 'START FAILED';
    showToast(error.message, true);
    const notice = $('#previewNotice'); if (notice) notice.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

init();
