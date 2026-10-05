// SPB-93 09-08: execute the live save/load maps; delegated-only checks missed
// the native Chrome remap loss. JSON is the real persistence boundary.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('paint-booth-2-state-zones.js', 'utf8');
const saveStart = source.indexOf('zones: zones.map(z => ({', source.indexOf('function getConfig()'));
const saveEnd = source.indexOf('})),', saveStart);
const save = source.slice(saveStart + 'zones: '.length, saveEnd + 3);
const loadStart = source.indexOf('zones = cfg.zones.map(z => ({');
const loadEnd = source.indexOf('}));', loadStart);
const load = source.slice(loadStart, loadEnd + 4);
assert(saveStart > 0 && saveEnd > saveStart && loadStart > 0 && loadEnd > loadStart);
const ctx = {window: {SPBSourceLayerLinks: require('../js/canvas/zone/source-layer-links.js')}, SPECIAL_COLORS: [], QUICK_COLORS: [],
  _newZoneId: () => 'restored', _savedCfgSize: {w: 2, h: 1}, _loadCfgSize: {w: 2, h: 1},
  _encodeSavedMask: x => x == null ? null : Array.from(x),
  _decodeSavedMask: x => x == null ? null : Uint8Array.from(x),
  _cloneUint8ArrayLike: x => x == null ? null : Uint8Array.from(x)};
vm.createContext(ctx);
const controls = {
  specMaterialRemap: {m: {low: 20, high: 100}, r: {low: 80, high: 160}, cc: {low: 150, high: 220}},
  specMaterialOverride: {m: 0, r: 80, cc: 255, a: 255},
  specLightingMask: 0
};
for (const fields of [controls, {specMaterialRemap: null, specMaterialOverride: null, specLightingMask: null}, {}]) {
  ctx.zones = [{id: 'zone', name: 'Paint', base: 'f_chrome', useRegion: true,
    regionMask: Uint8Array.from([0, 255]), ...fields}];
  ctx.cfg = JSON.parse(JSON.stringify({zones: vm.runInContext(save, ctx)}));
  vm.runInContext(load, ctx);
  for (const key of Object.keys(controls)) {
    assert.deepEqual(JSON.parse(JSON.stringify(ctx.zones[0][key] ?? null)), fields[key] ?? null, key + ' survives actual maps');
  }
  assert.equal(ctx.zones[0].base, 'f_chrome');
  assert.equal(ctx.zones[0].useRegion, true);
  assert.deepEqual(Array.from(ctx.zones[0].regionMask), [0, 255]);
}
console.log('Live Spec save/load JSON: remap, sampled material, lighting alpha, explicit clears and legacy absence pass.');

const presetSaveStart = source.indexOf('zones: zones.map(z => ({', source.indexOf('function exportPreset()'));
const presetSaveEnd = source.indexOf('})),', presetSaveStart);
const presetLoadStart = source.indexOf('zones = preset.zones.map(z => ({', source.indexOf('function _applyPresetFromObject(preset)'));
const presetLoadEnd = source.indexOf('}));', presetLoadStart);
assert(presetSaveStart > 0 && presetSaveEnd > presetSaveStart && presetLoadStart > 0 && presetLoadEnd > presetLoadStart);
ctx.zones = [{name: 'Paint', base: 'f_chrome', ...controls}];
ctx.preset = JSON.parse(JSON.stringify({zones: vm.runInContext(source.slice(presetSaveStart + 'zones: '.length, presetSaveEnd + 3), ctx)}));
vm.runInContext(source.slice(presetLoadStart, presetLoadEnd + 4), ctx);
for (const key of Object.keys(controls)) assert.deepEqual(JSON.parse(JSON.stringify(ctx.zones[0][key])), controls[key], key + ' survives shareable presets');
console.log('Shareable preset save/load maps preserve the same authored Spec settings.');
