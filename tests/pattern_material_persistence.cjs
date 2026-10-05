const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sandbox = {console, Uint8Array, Array, Math, structuredClone};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('js/zones/zone-config-zone-map-controls.js','utf8'), sandbox);
const config = sandbox.SPBZoneConfigZoneMapControls.install({});
const original = {name:'Pattern controls',base:'metallic',pattern:'decade_80s_leg_warmer',
  patternHueShift:125,patternSaturation:-65,patternSpecOpacity:50,patternPaintMode:'blend',
  patternStack:[{id:'decade_70s_funk_zigzag',hueShift:-75,saturation:80,specOpacity:100,opacity:40}]};
const restored = config.hydrateZones(JSON.parse(JSON.stringify(config.serializeZones([original]))))[0];
for(const key of ['patternHueShift','patternSaturation','patternSpecOpacity','patternPaintMode'])
  assert.equal(restored[key],original[key],key);
for(const key of ['hueShift','saturation','specOpacity','opacity'])
  assert.equal(restored.patternStack[0][key],original.patternStack[0][key],key);
const old = config.hydrateZones([{name:'Old recipe',base:'metallic',pattern:'checker_warp'}])[0];
assert.equal(old.patternSpecOpacity,0);assert.equal(old.patternHueShift,0);assert.equal(old.patternSaturation,0);
const api = fs.readFileSync('paint-booth-5-api-render.js','utf8');
function func(name){const a=api.indexOf('function '+name+'(');return api.slice(a,api.indexOf('\nfunction ',a+10));}
vm.runInContext(func('_mapPatternStackEntry'),sandbox);
const encoded = sandbox._mapPatternStackEntry(original.patternStack[0]);
assert.equal(encoded.spec_opacity,1);assert.equal(encoded.hue_shift,-75);assert.equal(encoded.saturation,80);
const controls = func('_applyPatternMaterialControls');
vm.runInContext(controls,sandbox);
const material = {};
sandbox._applyPatternMaterialControls(material, original);
assert.deepEqual(material,{pattern_paint_mode:'blend',pattern_hue_shift:125,pattern_saturation:-65,pattern_spec_opacity:.5});
// Checking an unused extracted helper previously concealed the real defect.
assert(func('buildServerZonesForRender').includes('_applyPatternMaterialControls(zoneObj, z)'));
assert.equal(api.split('_applyPatternMaterialControls(zoneObj, z);').length-1,4);
for(const file of ['paint-booth-2-state-zones.js','js/zones/zone-config-zone-map-controls.js']){
  const source=fs.readFileSync(file,'utf8');
  const modeMaps=(source.match(/patternPaintMode: z.patternPaintMode/g)||[]).length;
  for(const property of ['patternSpecOpacity','patternHueShift','patternSaturation'])
    assert.equal((source.match(new RegExp(property+': z.'+property,'g'))||[]).length,modeMaps,file+':'+property);
}
console.log('PASS: production save/load, legacy zero defaults, stacked fields and all five persistence maps.');
