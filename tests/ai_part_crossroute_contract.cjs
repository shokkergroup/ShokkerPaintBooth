'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const zoneSource = fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8');
function extract(source, name) {
  const start = source.indexOf(`function ${name}(`); assert(start >= 0, `${name} exists`);
  const open = source.indexOf('{', start); let depth = 0, quote = null, escaped = false, line = false, block = false;
  for (let i = open; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (escaped) escaped = false; else if (c === '\\') escaped = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++; else if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`Could not end ${name}`);
}
function harness() {
  const zones = [], fp = { car: 'car-a', layout: 'layout-a', elements: 'elements-a' };
  const ctx = { console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt, zones, selectedZoneIndex: 0,
    BASES: [{id:'gloss'}, {id:'chrome'}, {id:'matte'}], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [],
    document: { getElementById: () => ({ width: 32, height: 32 }) },
    addZone() { zones.push({ id: `z${zones.length+1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] }); },
    assignFinishToSelected(id) { const z=zones[this.selectedZoneIndex]; if(z) z.base=id; },
    setZoneSourceLayer() {}, toggleZoneSourceLayer() {},
    SpbProCar: { findIsland: name => ({id:String(name),name:String(name),front:true,up:true}), parts:()=>['roof','hood'], canon:x=>String(x),
      signature:()=>fp.car, layoutSig:()=>fp.layout, maskFor(name) { const m=new Uint8Array(1024); for(let i=0;i<512;i++)m[i]=255; return {mask:m,island:{name:String(name)},islands:[{name:String(name)}]}; } },
    SpbProElements: { sig:()=>fp.elements }
  };
  ctx.window=ctx; vm.createContext(ctx); vm.runInContext(zoneSource,ctx,{filename:'js/spb-pro-zone-kit.js'});
  ctx.CAR=ctx.SpbProCar; ctx._gen=0; ctx.applyLayerOps=()=>({lines:[],failed:[],undoSteps:0});
  ctx.Z={batch:(ops,label,opts)=>ctx.SpbProZone.batch(ops,label,opts)};
  ctx.carSig=()=>ctx.SpbProCar.signature(); ctx.editPlural=()=>false; ctx.friendlyZoneError=String;
  const names=['partRegionKey','editKey','markPartFollowupQueue','partOwnerCurrent','registerAppliedPartZones','partRegHas','partRegistryState','rollbackPendingPartRegistry','clearPartRegistryPending','reconcilePartRegistry','mergePartRegistryUndo','applyQueue','queueEditZones'];
  vm.runInContext(`${names.map(n=>extract(aiSource,n)).join('\n')}\nvar _editReg={},_editRegSig=null,_editRegPendingBefore={}; this.api={mark:markPartFollowupQueue,apply:applyQueue,queue:queueEditZones,registry:()=>_editReg};`,ctx,{filename:'spb-pro-ai integration'});
  ctx.add=spec=>ctx.SpbProZone.add(spec);
  ctx.edit=args=>{const z=zones.find(x=>x.id===args.zone_id); if(!z)return {error:'missing zone'}; const upd=Object.assign({},args); delete upd.zone_id; return ctx.SpbProZone.edit(z,upd);};
  return ctx;
}
function addSpec(name, color, finish='base::gloss') { return {kind:'add',spec:{name,region:{part:'roof'},color,finish}}; }
function helperApply(h, q) { h.api.mark(q); return h.api.apply(q,'local helper route'); }
{
  const h=harness(), q=[addSpec('Red roof','#c8102e')];
  helperApply(h,q);
  assert.equal(h.zones.length,1,'the committed local-route add creates a real zone');
  assert.ok(h.zones[0]._aiPartProv,'ZoneKit attached provenance to the real masked zone');
  assert.equal(Object.values(h.api.registry()).length,1,'the actual successful batch result registers the helper owner');
  const follow={zones:[{name:'Roof chrome',region:{part:'roof'},color:'source',finish:'base::chrome',_meta:{label:'roof',kind:'finish',finishExplicit:true}}]};
  const queued=h.api.queue(follow,h.add,h.edit);
  assert.equal(queued.merged,1,'the cross-route finish follow-up edits the registered zone');
  assert.equal(h.zones.length,1,'cross-route reuse avoids a second overlay');
  assert.equal(h.zones[0].baseColor,'#c8102e','finish-only follow-up preserves the earlier red paint');
  assert.ok(queued.lines.length, 'the real zone edit completed'); 
}
{
  const h=harness(); h.api.apply([addSpec('Manual roof','#c8102e')],'manual apply');
  assert.equal(Object.keys(h.api.registry()).length,0,'unmarked/manual applyQueue adds are never adopted');
}
{
  const h=harness(); helperApply(h,[addSpec('Roof base','#c8102e'),addSpec('Roof highlight','#f2f2f2')]);
  assert.equal(Object.keys(h.api.registry()).length,0,'purposeful same-selector stack adds stay unregistered/uncollapsed');
  const follow={zones:[{name:'Roof chrome',region:{part:'roof'},color:'source',finish:'base::chrome',_meta:{label:'roof',kind:'finish',finishExplicit:true}}]};
  const before=h.zones.length, result=h.api.queue(follow,h.add,h.edit);
  assert.equal(result.merged,0); assert.equal(h.zones.length,before,'ambiguous same-selector owners are never chosen arbitrarily');
}
console.log('PASS cross-route real-apply part provenance contract');






