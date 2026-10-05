// SPB-93: legacy API through the current shared Mask engine, with real history.
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
const require=createRequire(import.meta.url);
const source=readFileSync(new URL('../../paint-booth-3-canvas.js',import.meta.url),'utf8');
const refine=require('../../js/canvas/zone/selection-refine.js');
function extract(name){
 const start=source.indexOf('function '+name+'(');
 if(start<0)throw Error('Missing '+name);
 let i=source.indexOf('{',start),depth=0;
 for(;i<source.length;i++){if(source[i]==='{')depth++;else if(source[i]==='}'&&!--depth)break;}
 return source.slice(start,i+1);
}
const names=['_selectionRefineContext','_commitSelectionRefine','growRegionMask','shrinkRegionMask','smoothRegionMask','growSelection','shrinkSelection','smoothSelection'];
const script=names.map(extract).join('\n');
const results={};
for(const name of ['growSelection','shrinkSelection','smoothSelection']){
 results[name]={};
 for(const scenario of ['changed','empty']){
  const mask=new Uint8Array(64);
  if(scenario==='changed')for(let y=2;y<6;y++)for(let x=2;x<6;x++)mask[y*8+x]=255;
  if(scenario==='changed')mask[2*8+6]=255;
  const before=Array.from(mask),history=[],wrongHistory=[];
  const canvas={width:8,height:8,dataset:{}};
  const context={window:{SPBSelectionRefine:refine},zones:[{regionMask:mask}],selectedZoneIndex:0,
   document:{getElementById:()=>canvas},performance,showToast(){},_refreshZoneMaskHistoryUI(){},
   pushUndo(index){history.push({index,mask:Array.from(context.zones[index].regionMask)});},
   pushZoneUndo(){wrongHistory.push('zone-config');}};
  vm.createContext(context);vm.runInContext(script,context);
  vm.runInContext(name+'(2)',context);
  const after=Array.from(context.zones[0].regionMask);
  results[name][scenario]={changed:before.some((v,i)=>v!==after[i]),history,
   original:before,wrongHistory,committed:JSON.parse(canvas.dataset.spbSelectionRefineLast).committed};
 }
}
console.log(JSON.stringify(results));
