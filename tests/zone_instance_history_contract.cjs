// SPB-93: history/persistence foundation only. Material rendering remains a separate gate.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('paint-booth-2-state-zones.js','utf8');
const canvas=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const plain=x=>JSON.parse(JSON.stringify(x));
const record={sourceBbox:{x1:10,y1:20,x2:30,y2:40},instanceBbox:{x1:50,y1:20,x2:70,y2:40},sourcePixelSnapshot:'data:image/png;base64,fixture',sourceTarget:'base',appearance:{hue:0}};
const c={window:{SPBSourceLayerLinks:require('../js/canvas/zone/source-layer-links.js'),SPBZoneMaterialInstanceModel:require('../js/canvas/zone/material-instance-model.js')},SPECIAL_COLORS:[],QUICK_COLORS:[],
 _newZoneId:()=> 'restored',_savedCfgSize:{w:2,h:1},_loadCfgSize:{w:2,h:1},
 _encodeSavedMask:x=>x==null?null:Array.from(x),_decodeSavedMask:x=>x==null?null:Uint8Array.from(x),
 _cloneUint8ArrayLike:x=>x==null?null:Uint8Array.from(x),_clonePatternStrengthMap:x=>x};
vm.createContext(c);
for(const [saveName,loadName,object] of [['function getConfig()','zones = cfg.zones.map(z => ({','cfg'],['function exportPreset()','zones = preset.zones.map(z => ({','preset']]) {
 const a=source.indexOf('zones: zones.map(z => ({',source.indexOf(saveName)),b=source.indexOf('})),',a);
 const d=source.indexOf(loadName,object==='preset'?source.indexOf('function _applyPresetFromObject(preset)'):0),e=source.indexOf('}));',d);
 assert(a>0&&b>a&&d>0&&e>d);
 for(const links of [undefined,[],[record]]) {
  c.zones=[{id:'zone',name:'Paint',base:'f_chrome',patternInstances:plain(links||[]),regionMask:Uint8Array.from([0,255])}];
  if(links===undefined)delete c.zones[0].patternInstances;
  const saved=vm.runInContext(source.slice(a+'zones: '.length,b+3),c);
  if(links?.length){c.zones[0].patternInstances[0].appearance.hue=90;assert.equal(saved[0].patternInstances[0].appearance.hue,0);}
  c[object]=plain({zones:saved});vm.runInContext(source.slice(d,e+4),c);
  assert.deepEqual(plain(c.zones[0].patternInstances),links||[]);
  if(links?.length){c[object].zones[0].patternInstances[0].appearance.hue=45;assert.equal(c.zones[0].patternInstances[0].appearance.hue,0);}
 }
}
const cloneStart=source.indexOf('function _cloneZoneState('),cloneEnd=source.indexOf('\nfunction _ensureZoneShape',cloneStart);
vm.runInContext(source.slice(cloneStart,cloneEnd),c);
let snapshots=[];
Object.assign(c,{selectedZoneIndex:0,freeTransformState:{target:'base',subRect:plain(record.sourceBbox)},
 document:{getElementById:()=>({width:2048,height:2048}),createElement:()=>({getContext:()=>({drawImage(){}}),toDataURL:()=> 'data:image/png;base64,new'})},
 _isZoneFreeTransformTarget:t=>t==='base',
 drawTransformHandles(){},renderContextActionBar(){},showToast(){},setTimeout(){},
 _getZonePatternInstances:z=>z.patternInstances||[],
 pushZoneUndo(label){snapshots.push({label,zone:c._cloneZoneState(c.zones[0],{preserveId:true})});}});
const start=canvas.indexOf('window._ctxCreateZonePatternInstance ='),end=canvas.indexOf('// v123: Zone Pattern Color Tint',start);
vm.runInContext(canvas.slice(start,end),c);
for(const fn of ['_ctxCreateZonePatternInstance','_ctxSyncZonePatternInstance','_ctxReapplyZonePatternSource','_ctxPromoteZoneToMaster','_ctxBreakZonePatternInstanceLink']) {
 c.zones=[{id:'zone',base:'f_chrome',patternInstances:fn==='_ctxCreateZonePatternInstance'?[]:[plain(record)]}];
 const before=plain(c.zones[0]);snapshots=[];c.window[fn]();
 assert.equal(snapshots.length,1,fn+' has one transaction');
 assert.deepEqual(plain(snapshots[0].zone.patternInstances),before.patternInstances,fn+' captures topology before mutation');
 if(c.zones[0].patternInstances[0])c.zones[0].patternInstances[0].sourceBbox.x1=999;
 assert.deepEqual(plain(snapshots[0].zone.patternInstances),before.patternInstances,fn+' snapshot remains independent');
}
c.zones=[{id:'zone',patternInstances:[]}];snapshots=[];
for(const fn of ['_ctxSyncZonePatternInstance','_ctxReapplyZonePatternSource','_ctxPromoteZoneToMaster','_ctxBreakZonePatternInstanceLink'])c.window[fn]();
assert.equal(snapshots.length,0,'missing links do not create fake history');
console.log('Zone instance foundation: actual save/load and preset maps, independent nested records, five command history boundaries and no-link no-ops pass. Rendering is not covered.');
