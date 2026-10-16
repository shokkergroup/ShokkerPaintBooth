'use strict';
// Actual compositor-mask function + actual report grid/measurement functions.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const read=f=>fs.readFileSync(path.join(__dirname,'candidates',f),'utf8');
const layer={id:'art',name:'Numbers',img:{}},above={id:'top',name:'Top',img:{}};
const rgba=alphas=>Uint8ClampedArray.from(alphas.flatMap(a=>[255,255,255,a]));
let compositeCalls=0;
const w={console,Promise,Date,Uint8Array,Uint8ClampedArray,Map,_psdLayers:[layer,above],_psdLayersLoaded:true,_layerCompositeRevision:1,_layerVisibleContributionCache:new Map(),_layerAtIndexCanComposite:()=>true,
 document:{addEventListener(){},createElement:()=>({getContext:()=>({data:null,getImageData(){return {data:this.data};}})})},
 _spbCompositeLayerStack:(ctx,ls,opts)=>{compositeCalls++;ctx.data=opts.includeLayer(layer,0)?rgba([255,254,128,127]):rgba([0,0,1,255]);return {ok:true,drawn:true};}};
w.window=w;vm.createContext(w);
const source=read('paint-booth-3-canvas.js'),start=source.indexOf('function getLayerVisibleContributionMask('),end=source.indexOf('// ===== LAYER EFFECTS RENDERER',start);assert.ok(start>0&&end>start);vm.runInContext(source.slice(start,end),w);
const normal=w.getLayerVisibleContributionMask(layer,4,1);assert.deepEqual(Array.from(normal),[255,255,255,0]);
assert.deepEqual(Array.from(w.getLayerOpaqueContributionMask(layer,4,1)),[255,0,0,0]);assert.equal(compositeCalls,4);
assert.equal(w.getLayerVisibleContributionMask(layer,4,1),normal);assert.equal(compositeCalls,4,'Separate opaque cache does not overwrite painting ownership');
const full=new Uint8Array(512*512);for(let y=80;y<240;y++)for(let x=80;x<240;x++)full[y*512+x]=255;
w.SpbProZone={findLayer:()=>layer};w.getLayerOpaqueContributionMask=()=>full;
vm.runInContext(read('spb-intent-report.js').replace('W.SpbIntentReport = {','W.testArtwork = {grid:grid,opaque:opaqueArtworkGrid,measure:measure}; W.SpbIntentReport = {'),w);
const g=w.testArtwork.opaque('Numbers',512,512);assert.ok(g&&g.cells>0);assert.equal(g.mask[40*256+40],0);assert.equal(g.mask[50*256+50],1);
const partly=new Uint8Array(512*512).fill(255);partly[1]=0;assert.equal(w.testArtwork.grid(partly,512,512,'solid')[0],0,'Solid check samples every source pixel, including odd coordinates');
const A=new Uint8ClampedArray(256*256*4),B=A.slice(),m={part:{},layer:{},layerNames:[],decal:g.mask};
for(let x=40;x<120;x++)B[(40*256+x)*4]=200;assert.equal(w.testArtwork.measure(A,B,null,null,m).decal,0,'Changed antialiased border is outside interior proof');
for(let y=60;y<80;y++)for(let x=60;x<80;x++)B[(y*256+x)*4]=200;assert.equal(w.testArtwork.measure(A,B,null,null,m).decal,400,'Real opaque artwork damage remains detected');
w.getLayerOpaqueContributionMask=()=>new Uint8Array(512*512);assert.equal(w.testArtwork.opaque('Numbers',512,512),null,'No solid coverage must fall back, never claim a pass');
w.SPB_AI_OPAQUE_CHECK_OFF=true;assert.equal(w.testArtwork.opaque('Numbers',512,512),null);
console.log('PASS opaque artwork diagnostics: unchanged painting masks/cache, full-alpha threshold, above-layer exclusion, all-pixel sampling, filter margin, real interior corruption detected, empty/disabled fallback. Native preview acceptance separate.');
