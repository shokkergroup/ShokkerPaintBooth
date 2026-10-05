const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={console,Uint8Array,Array,Math,structuredClone};ctx.window=ctx;vm.createContext(ctx);
const api=fs.readFileSync('paint-booth-5-api-render.js','utf8');
const a=api.indexOf('function _applyBaseColorMode('), b=api.indexOf('\nif (typeof window',a);
vm.runInContext(`function _zoneHasRenderableMaterial(){return true} function _zoneShouldFitIntoApplyArea(){return false} function _applyBaseColorBranch(){}`+api.slice(a,b),ctx);
for(const mode of [undefined,'source','finish','special','solid','gradient']){
 const out={};ctx._applyBaseColorMode(out,{base:'gloss',baseColorMode:mode});
 assert.equal(out.base_color_mode,mode||'source');assert.equal(out.base_color_explicit,true);
}
vm.runInContext(fs.readFileSync('js/zones/zone-config-zone-map-controls.js','utf8'),ctx);
const cfg=ctx.SPBZoneConfigZoneMapControls.install({});
for(const mode of ['source','finish']){
 const z={base:'chrome',baseColorMode:mode,baseColorModeExplicit:true};
 const back=cfg.hydrateZones(JSON.parse(JSON.stringify(cfg.serializeZones([z]))))[0];
 assert.equal(back.baseColorMode,mode);assert.equal(back.baseColorModeExplicit,true);
}
let zones=[{base:'chrome'}];vm.runInContext(fs.readFileSync('js/zones/zone-base-color-controls.js','utf8'),ctx);
ctx.SPBZoneBaseColorControls.install({getZones:()=>zones});
ctx.setZoneBaseColorMode(0,'finish');assert.equal(zones[0].baseColorMode,'finish');assert.equal(zones[0].baseColorModeExplicit,true);
const canvas=fs.readFileSync('paint-booth-3-canvas.js','utf8');
assert(canvas.includes('zoneObj.base_color_explicit = true; // 2026-09-09'));
console.log('Base mode payload/defaults/controller/save-load PASS');
