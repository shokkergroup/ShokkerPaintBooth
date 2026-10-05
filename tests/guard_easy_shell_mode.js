#!/usr/bin/env node
'use strict';

// Focused regression guard for the shared-state main-app Easy shell.
// Intentionally dependency-free: it exercises the controller in a tiny VM DOM
// and statically checks the HTML/CSS presentation contract.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const controllerPath = path.join(ROOT, 'js', 'spb-focus-mode.js');
const cssPath = path.join(ROOT, 'css', 'spb-focus-mode-20260827.css');
const mirrorControllerPath = path.join(ROOT, 'electron-app', 'server', 'js', 'spb-focus-mode.js');
const mirrorCssPath = path.join(ROOT, 'electron-app', 'server', 'css', 'spb-focus-mode-20260827.css');
const htmlPath = path.join(ROOT, 'paint-booth-v2.html');
const statePath = path.join(ROOT, 'paint-booth-2-state-zones.js');
const mirrorStatePath = path.join(ROOT, 'electron-app', 'server', 'paint-booth-2-state-zones.js');
const controller = fs.readFileSync(controllerPath, 'utf8');
const css = fs.readFileSync(cssPath, 'utf8');
const html = fs.readFileSync(htmlPath, 'utf8');
const state = fs.readFileSync(statePath, 'utf8');

assert.strictEqual(fs.readFileSync(mirrorControllerPath, 'utf8'), controller, 'Easy controller runtime mirror drift');
assert.strictEqual(fs.readFileSync(mirrorCssPath, 'utf8'), css, 'Easy CSS runtime mirror drift');
assert.strictEqual(fs.readFileSync(mirrorStatePath, 'utf8'), state, 'Zone-card runtime mirror drift');

assert(!/\b(?:zones|layers)\s*\[/.test(controller), 'presentation controller must not mutate Zone/Layer arrays');
assert(!/regionMask|spatialMask/.test(controller), 'presentation controller must not mutate mask state');

function fakeClassList(initial = []) {
  const values = new Set(initial);
  return {
    add(...names) { names.forEach((name) => values.add(name)); },
    remove(...names) { names.forEach((name) => values.delete(name)); },
    contains(name) { return values.has(name); },
    toggle(name, force) {
      const enabled = force === undefined ? !values.has(name) : Boolean(force);
      if (enabled) values.add(name); else values.delete(name);
      return enabled;
    },
  };
}

function buildHarness(savedMode) {
  const values = new Map();
  if (savedMode !== undefined) values.set('spb_view_mode', savedMode);
  const listeners = new Map();
  const makeButton = () => ({
    classList: fakeClassList(),
    attrs: {},
    setAttribute(name, value) { this.attrs[name] = value; },
  });
  const proButton = makeButton();
  const easyButton = makeButton();
  const body = {
    classList: fakeClassList(),
    contains() { return false; },
  };
  const elements = {
    spbModeProBtn: proButton,
    spbModeEasyBtn: easyButton,
  };
  const document = {
    readyState: 'loading',
    body,
    activeElement: null,
    addEventListener(name, fn, capture) {
      const bucket = listeners.get(name) || [];
      bucket.push({ fn, capture: Boolean(capture) });
      listeners.set(name, bucket);
    },
    removeEventListener(name, fn) {
      listeners.set(name, (listeners.get(name) || []).filter((item) => item.fn !== fn));
    },
    getElementById(id) { return elements[id] || null; },
  };
  const calls = [];
  const localStorage = {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
  };
  function MutationObserver() { this.observe = function () {}; }
  const window = {
    document,
    localStorage,
    MutationObserver,
    setToolbarEditMode(value) { calls.push(['toolbar', value]); },
    setCanvasMode(value) { calls.push(['canvas', value]); },
  };
  const context = {
    window,
    document,
    localStorage,
    MutationObserver,
    setTimeout() { return 1; },
    clearTimeout() {},
  };
  vm.runInNewContext(controller, context, { filename: controllerPath });
  return { window, document, values, listeners, calls, proButton, easyButton };
}

// Migration must happen during evaluation, before the legacy controller's
// delayed +450 ms boot can see the retired `easy` value.
for (const retired of ['easy', 'focus']) {
  const harness = buildHarness(retired);
  assert.strictEqual(harness.values.get('spb_view_mode'), 'easy-shell', `${retired} should migrate synchronously`);
}
assert.strictEqual(buildHarness(undefined).values.get('spb_view_mode'), 'easy-shell', 'Fresh installs must start in Easy');
assert.strictEqual(buildHarness('pro').values.get('spb_view_mode'), 'pro', 'Pro persistence must remain untouched');

const harness = buildHarness('pro');
const api = harness.window.spbEasyShell;
assert(api && typeof api.enter === 'function' && typeof api.exit === 'function', 'Easy-shell API must be exported');

api.enter();
assert(harness.document.body.classList.contains('spb-focus-on'), 'Easy must enable the scoped presentation class');
assert(harness.document.body.classList.contains('spb-easy-shell-on'), 'Easy must expose its truthful shell state');
assert.strictEqual(harness.values.get('spb_view_mode'), 'easy-shell');
assert.deepStrictEqual(harness.calls.slice(-2), [['toolbar', 'zone'], ['canvas', 'eyedropper']], 'Easy should land on Zone + Pick without copying project state');
assert(harness.easyButton.classList.contains('on'));
assert.strictEqual(harness.easyButton.attrs['aria-pressed'], 'true');
assert.strictEqual(harness.proButton.attrs['aria-pressed'], 'false');

// The legacy module boots 70 ms first and may briefly resync the shared pill.
// A repeated enter during our boot must repair that label without changing data.
harness.easyButton.classList.remove('on');
harness.proButton.classList.add('on');
api.enter();
assert(harness.easyButton.classList.contains('on'), 're-enter must repair a startup pill race');
assert(!harness.proButton.classList.contains('on'));

const keydown = (harness.listeners.get('keydown') || []).find((item) => item.capture);
assert(keydown, 'Easy must install its capture-phase ghost-shortcut guard');
function dispatchKey(key, extras = {}) {
  const event = Object.assign({
    key,
    target: null,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    shiftKey: false,
    prevented: false,
    stopped: false,
    preventDefault() { this.prevented = true; },
    stopImmediatePropagation() { this.stopped = true; },
  }, extras);
  keydown.fn(event);
  return event;
}
for (const key of ['p', 'w', 'l', 'o', 'b', 'k', 'e']) {
  assert(!dispatchKey(key).prevented, `visible Easy tool shortcut ${key.toUpperCase()} must remain available`);
}
for (const key of ['a', 'r', 'c', 'q', 'j', 'y', 'v', 'm', 'x', 'g', 't', 'u', 'n', 's', 'i', 'd', 'f', 'h', '/', '?']) {
  assert(dispatchKey(key).prevented, `hidden tool/command shortcut ${key.toUpperCase()} must be blocked`);
}
assert(dispatchKey('t', { ctrlKey: true }).prevented, 'hidden Transform shortcut must be blocked');

api.exit();
assert(!harness.document.body.classList.contains('spb-focus-on'));
assert(!harness.document.body.classList.contains('spb-easy-shell-on'));
assert.strictEqual(harness.values.get('spb_view_mode'), 'pro');
assert(harness.proButton.classList.contains('on'));
assert.strictEqual(harness.proButton.attrs['aria-pressed'], 'true');
assert(!dispatchKey('c').prevented, 'Easy shortcut filter must become inert in Pro');

// The header routes to the shared-state shell, never the legacy parallel Easy
// overlay. No user-facing Focus chip survives.
assert(html.includes('onclick="if(window.spbEasyShell)window.spbEasyShell.exit()">PRO</button>'));
assert(html.includes('onclick="if(window.spbEasyShell)window.spbEasyShell.enter()">&#10024; EASY</button>'));
assert(!html.includes('id="spbFocusExitChip"'));

// The two exposed toolbar clusters contain exactly the owner's eight controls.
function idsIn(fragment) {
  return [...fragment.matchAll(/id="(vtMode[^"]+)"/g)].map((match) => match[1]);
}
const selectCluster = html.match(/<div class="spb-tb-cluster" id="spbToolClusterSelect">([\s\S]*?)<\/div>/);
const paintCluster = html.match(/<div class="spb-tb-cluster">\s*<button id="vtModeBrush"([\s\S]*?)<\/div>/);
assert(selectCluster && paintCluster, 'expected Easy toolbar cluster structure is missing');
assert.deepStrictEqual(idsIn(selectCluster[1]), [
  'vtModeEyedropper', 'vtModeSpatialExcludeTop', 'vtModeWand', 'vtModeLasso', 'vtModeRect',
]);
assert.deepStrictEqual(['vtModeBrush', ...idsIn(paintCluster[1])], [
  'vtModeBrush', 'vtModeFill', 'vtModeErase',
]);

// Easy-only hide and visual-language contracts.
for (const required of [
  'body.spb-focus-on #spbModePill',
  'body.spb-focus-on #spbTopToolbar > #spbToolClusterSelect',
  'body.spb-focus-on #spbTopToolbar > .spb-tb-cluster:has(> #vtModeBrush)',
  'body.spb-focus-on #vtModeEyedropper',
  'body.spb-focus-on #vtModeSpatialExcludeTop',
  'body.spb-focus-on #vtModeWand',
  'body.spb-focus-on #vtModeLasso',
  'body.spb-focus-on #vtModeRect',
  'body.spb-focus-on #vtModeBrush',
  'body.spb-focus-on #vtModeFill',
  'body.spb-focus-on #vtModeErase',
  'body.spb-focus-on [id^="sectionPattern"]',
  'body.spb-focus-on [id^="sectionSpecPatterns"]',
  'body.spb-focus-on [id^="sectionZoneSpecSource"]',
  'body.spb-focus-on [id^="sectionOverlays"]',
  ':has(> label[title^="BASE MATERIAL"])',
  ':has(select[onchange^="setZoneBaseColorMode"])',
  '.zone-base-color-card-head',
  '.zone-base-color-source-trigger',
  'body:not(.spb-easy-on) .zone-detail-body .stack-control-group:has(input[type="range"])',
]) assert(css.includes(required), `missing Easy CSS contract: ${required}`);
const sharedSliderPrefix = 'body:not(.spb-easy-on) .zone-detail-body .stack-control-group:has(input[type="range"])';
const sharedSliderBlockStart = css.indexOf(`${sharedSliderPrefix} {`);
const sharedSliderBlock = css.slice(sharedSliderBlockStart, css.indexOf('}', sharedSliderBlockStart) + 1);
assert(/min-height:\s*28px\s*!important/.test(sharedSliderBlock), 'Easy and Pro slider rows must use the same compact height');
assert(/padding:\s*2px 5px\s*!important/.test(sharedSliderBlock), 'Easy and Pro slider rows must keep thin vertical padding');
assert(!css.includes('body:not(.spb-focus-on):not(.spb-easy-on) .zone-detail-body .stack-control-group'), 'Pro must not override the shared Easy slider design');
const materialSwatchPrefix = 'body:not(.spb-easy-on) .zone-detail-body .zone-finish-row:has(> label[title^="BASE MATERIAL"]) > .swatch-trigger > .swatch-dot';
const materialSwatchStart = css.indexOf(`${materialSwatchPrefix} {`);
const materialSwatchBlock = css.slice(materialSwatchStart, css.indexOf('}', materialSwatchStart) + 1);
assert(/width:\s*68px\s*!important/.test(materialSwatchBlock) && /height:\s*68px\s*!important/.test(materialSwatchBlock), 'Base Material preview must be a true square');
const colorSwatchPrefix = 'body:not(.spb-easy-on) .zone-detail-body .zone-base-color-source-trigger .swatch-dot';
const colorSwatchStart = css.indexOf(`${colorSwatchPrefix} {`);
const colorSwatchBlock = css.slice(colorSwatchStart, css.indexOf('}', colorSwatchStart) + 1);
assert(/width:\s*68px\s*!important/.test(colorSwatchBlock) && /height:\s*68px\s*!important/.test(colorSwatchBlock), 'Base Color preview must match the Base Material square');
assert(css.includes('body:not(.spb-easy-on) #zoneEditorFloat.zone-editor-float'), 'Pro and Easy must share the wider Zone popout geometry');
assert(css.includes('width: clamp(340px, 29vw, 460px) !important;'), 'shared Zone popout must provide room for full names and slider tracks');
assert(css.includes('text-overflow: clip !important;') && css.includes('overflow-wrap: anywhere;'), 'finish names must wrap instead of truncating');
assert(state.includes('zone-base-color-card-head') && state.includes('zone-base-color-source-trigger'), 'Base Color must render a dedicated header and source card');
assert(state.indexOf('zone-base-color-title') < state.indexOf('zone-base-color-mode'), 'Base Color label/Lock must remain directly before its mode picker');
assert(/body\.spb-focus-on\s+#spbModePill\s*\{[^}]*display:\s*inline-flex\s*!important/s.test(css), 'mode pill must remain visible in Easy');
assert(!/body\.spb-focus-on\s+#spbModePill\s*[,\{][^}]*display:\s*none/s.test(css), 'Easy must never hide its mode pill');
assert(/body\.spb-focus-on\s+#spbTopToolbar\s*>\s*\*\s*\{\s*display:\s*none\s*!important/s.test(css), 'Easy must hide every toolbar control by default');
assert(css.includes("content: 'COLOR'"));
assert(!css.includes("content: 'PICK'"));
assert(css.includes("content: 'EXCLUDE'"));
assert(controller.includes("dst.classList.toggle('active', src.classList.contains('active'))"), 'promoted Easy Exclude must mirror the real tool active state');
assert(/^#vtModeSpatialExcludeTop\s*\{\s*display:\s*none\s*!important;\s*\}/m.test(css), 'promoted Easy Exclude must remain hidden in Pro despite toolbar !important rules');

// The promoted duplicate Exclude button stays hidden globally. Material cards
// panel/card and slider rules deliberately share one Main App selector across Easy + Pro;
// all other hiding remains behind the Easy body class.
const cssWithoutComments = css.replace(/\/\*[\s\S]*?\*\//g, '');
const unscoped = cssWithoutComments
  .split(/(?<=\})/)
  .map((block) => block.trim())
  .filter(Boolean)
  .filter((block) => block !== '}') // closing braces from nested @media blocks
  .filter((block) => !block.startsWith('@media'))
  .filter((block) => !block.startsWith('body.spb-focus-on'))
  .filter((block) => !block.startsWith('body:not(.spb-easy-on) #zoneEditorFloat'))
  .filter((block) => !block.startsWith('body:not(.spb-easy-on) .zone-editor-float'))
  .filter((block) => !block.startsWith('body:not(.spb-easy-on) .zone-detail-body'))
  .filter((block) => !/^#vtModeSpatialExcludeTop\s*\{\s*display:\s*none\s*!important;\s*\}$/.test(block));
assert.deepStrictEqual(unscoped, [], `unexpected Pro-affecting CSS: ${unscoped.join('\n')}`);

console.log('easy-shell guard: PASS');
