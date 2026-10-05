const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('paint-booth-2-state-zones.js', 'utf8');
const start = source.indexOf('function _installSwatchPopupLazyLoader() {');
const end = source.indexOf('// Resolve overlay base id', start);
const frames = [];
const images = Array.from({length: 80}, (_, index) => {
  const group = {collapsed: index >= 60, classList: {contains() {return group.collapsed;}}};
  return { group, dataset: {}, closest: () => group, getClientRects: () => [1] };
});
let hydrated = [];
const context = {
  _swatchPopupHydrateFrame: null,
  document: {getElementById: () => ({querySelectorAll: () => images})},
  _closeSwatchHoverPopout() {}, _installSwatchHoverPopout() {},
  _disconnectSwatchPopupLazyLoader() {},
  requestAnimationFrame: fn => {frames.push(fn); return frames.length;},
  cancelAnimationFrame() {},
  _hydrateDeferredSwatchImage: img => {if (!img.dataset.loaded) {hydrated.push(img); img.dataset.loaded = true;}}
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
context._installSwatchPopupLazyLoader();
assert.equal(hydrated.length, 0, 'Wait for the final category layout');
frames.shift()();
assert.equal(hydrated.length, 60, 'Every card in the open category loads, including beyond the first 24');
assert(hydrated.every(i => !i.group.collapsed), 'Collapsed categories make no requests');
images.forEach(i => {i.group.collapsed = !i.group.collapsed;});
context._installSwatchPopupLazyLoader(); frames.shift()();
assert.equal(hydrated.length, 80, 'Opening another category loads its baked cards immediately');
const urlStart = source.indexOf('function getSwatchUrl(');
const urlEnd = source.indexOf('// Resolve the cache-bust token', urlStart);
context.getFinishType = () => 'base';
context._swatchCacheToken = () => 'per-finish';
context.window = {_SHOKKER_PORT: 59876};
vm.runInContext(source.slice(urlStart, urlEnd), context);
const url = context.getSwatchUrl('finish-a', '#abc', true);
assert(url.includes('baked=1') && url.includes('color=aabbcc') && url.includes('size=256'));
assert.equal(url, context.getSwatchUrl('finish-a', '#abc', true), 'Reopening retains the immutable URL');
assert(!context.getSwatchUrl('finish-a', '#abc', false).includes('baked=1'));
const tokenStart = source.indexOf('function _swatchCacheToken(');
const tokenEnd = source.indexOf('if (typeof window', tokenStart + 50);
vm.runInContext(source.slice(tokenStart, tokenEnd), context);
assert.equal(context._swatchCacheToken('base', 'finish-a'), 'faithful-picker-v1', 'Boot fallback cannot use a timestamp');
console.log('PASS: actual picker uses stable baked-only URLs and loads the whole visible category eagerly.');
