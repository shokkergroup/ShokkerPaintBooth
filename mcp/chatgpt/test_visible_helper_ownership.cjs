'use strict';
// Execute the actual native visible-contribution function with a tiny compositor
// fixture. Other suites cover real group composition; this checks its draw scope.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
function load(file){
 const source=fs.readFileSync(path.join(root,file),'utf8'),start=source.indexOf('function getLayerVisibleContributionMask('),end=source.indexOf('\nfunction ',start+1);assert.ok(start>=0&&end>start);
 const layers=[{id:'paint',name:'Pattern',visible:true,img:{},alpha:[255,255,255,255]},{id:'mask',name:'Mask',visible:true,img:{},alpha:[255,0,0,0]},{id:'wire',name:'Wire',visible:true,img:{},alpha:[0,255,0,0]},{id:'sponsor',name:'Sponsor',visible:true,img:{},alpha:[0,0,255,0]}];
 const w={Uint8Array,Map,_psdLayers:layers,_psdLayersLoaded:true,_layerCompositeRevision:1,_layerVisibleContributionCache:new Map(),_layerAtIndexCanComposite:(ls,i)=>ls[i].visible!==false,_spbReportGroupFidelityFailure(){throw Error('Unexpected group failure');},document:{createElement(){const ctx={pixels:new Uint8Array(16),getImageData(){return {data:this.pixels};}};return {getContext:()=>ctx};}},_drawLayerPixelContent(ctx,ls,i){ls[i].alpha.forEach((a,n)=>{ctx.pixels[n*4+3]=Math.max(ctx.pixels[n*4+3],a);});return true;},_spbCompositeLayerStack(ctx,ls,opt){let drawn=0;ls.forEach((l,i)=>{if(opt.includeLayer(l,i)){opt.drawLayer(ctx,l,i);drawn++;}});return {ok:true,drawn};}};
 vm.createContext(w);vm.runInContext(source.slice(start,end),w);
 return {layers,w,mask:exclude=>Array.from(w.getLayerVisibleContributionMask(layers[0],4,1,exclude)),invalidate(){w._layerCompositeRevision++;w._layerVisibleContributionCache.clear();}};
}
const old=load('paint-booth-3-canvas.js');assert.deepEqual(old.mask(),[255,255,0,255],'Negative control: visible Mask/Wire are ignored');
const c=load('mcp/chatgpt/candidates/paint-booth-3-canvas.js'),before=JSON.stringify(c.layers);assert.deepEqual(c.mask(),[0,0,0,255]);assert.equal(JSON.stringify(c.layers),before,'Mask measurement never mutates layer state');
assert.deepEqual(c.mask('sponsor'),[0,0,255,255],'Explicit current brush layer remains excluded from art-above ownership');
c.layers[1].visible=false;c.invalidate();assert.deepEqual(c.mask(),[255,0,0,255],'Hiding Mask exposes only its source pixels');
c.layers[2].visible=false;c.invalidate();assert.deepEqual(c.mask(),[255,255,0,255]);
c.layers[1].visible=true;c.layers[2].visible=true;c.invalidate();assert.deepEqual(c.mask(),[0,0,0,255],'Visibility Undo restores ownership');
c.layers[0].visible=false;c.invalidate();assert.equal(c.w.getLayerVisibleContributionMask(c.layers[0],4,1),null);
console.log('PASS actual native function: visible Mask/Wire/sponsors own their pixels, hidden guides expose source, brush exclusion and visibility Undo survive. Native pixel retry still required.');
