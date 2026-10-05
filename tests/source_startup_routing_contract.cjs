const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync('paint-booth-2-state-zones.js','utf8');
const start=src.indexOf('function _spbAutoLoadPaintFile('),end=src.indexOf('window._spbAutoLoadPaintFile =',start);
const live=src.slice(start,end);
function rootLoader(source,layered=true) {
 const calls=[];const c={window:{loadPaintPreviewFromServer:p=>{calls.push(['flat',p]);return Promise.resolve({ok:true});}}};
 if(layered)c.window.importPSDFromPath=p=>{calls.push(['layered',p]);return Promise.resolve({ok:true});};
 vm.createContext(c);vm.runInContext(source,c);return {load:c._spbAutoLoadPaintFile,calls};
}
const delegatedSource=fs.readFileSync('js/zones/zone-auto-restore-controls.js','utf8');
function delegatedLoader() {
 const calls=[],c={};vm.createContext(c);vm.runInContext(delegatedSource,c);
 c.SPBZoneAutoRestoreControls.install({importPSDFromPath:p=>{calls.push(['layered',p]);return Promise.resolve({ok:true});},loadPaintPreviewFromServer:p=>{calls.push(['flat',p]);return Promise.resolve({ok:true});}});
 return {load:c._spbAutoLoadPaintFile,calls};
}
for(const setup of [()=>rootLoader(live),delegatedLoader]) {
 for(const ext of ['psd','PSD','ora','ORA','xcf','XcF','tga','PNG','jpg','bmp']) {
  const {load,calls}=setup();const path='C:\\folder.psd\\my art.'+ext;
  assert.equal(load(path),true);
  assert.deepEqual(calls,[[['psd','ora','xcf'].includes(ext.toLowerCase())?'layered':'flat',path]]);
 }
 const empty=setup();assert.equal(empty.load(''),false);assert.deepEqual(empty.calls,[]);
}
const unavailable=rootLoader(live,false);assert.equal(unavailable.load('source.ora'),false);assert.deepEqual(unavailable.calls,[],'never flatten layered input when importer unavailable');
const before=rootLoader(live.replace("['psd', 'ora', 'xcf'].includes(ext)","ext === 'psd'"));before.load('source.ora');assert.equal(before.calls[0][0],'flat','negative control reproduces observed startup misroute');
// Exercise the actual native startup facade after asynchronous path lookup.
const restore=src.slice(src.indexOf('function _spbRestorePaintFile('),src.indexOf('function autoRestore()'));
(async()=>{
 for(const path of ['source.ora','source.xcf','source.psd','source.tga']) {
  const calls=[],saved=[],c={window:{importPSDFromPath:p=>calls.push(['layered',p]),loadPaintPreviewFromServer:p=>calls.push(['flat',p])},_spbSetPaintHeaderPath(){},validatePaintPath(){},_spbResolveRestorePaintFile:async()=>path,localStorage:{setItem:(k,p)=>saved.push(p)},SPB_LAST_FILE_KEY:'last',showToast(){}};
  vm.createContext(c);vm.runInContext(restore,c);assert.equal(await c._spbRestorePreferredPaintFile({}),true);assert.deepEqual(saved,[path]);assert.equal(calls.length,1);assert.equal(calls[0][0],path.endsWith('.tga')?'flat':'layered');
 }
 console.log('Startup routing: live and delegated PSD/ORA/XCF/case variants, flat formats, no flatten fallback, old-code negative control and real async restore facade pass.');
})().catch(e=>{console.error(e);process.exitCode=1;});
