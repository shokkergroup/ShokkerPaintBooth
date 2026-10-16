'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
const raw=new Uint8ClampedArray([255,0,0,255,0,255,0,255,0,0,255,255,255,0,0,80,255,0,0,0]);
const original={width:5,height:1,data:raw},layer={id:'pattern',name:'Pattern',groupName:'Paintable Area',img:original,bbox:[0,0,5,1]},other={id:'logos',name:'Logos',img:{width:5,height:1,data:raw.slice()},bbox:[0,0,5,1]};
let history=0,rendered=0;
function canvas(){let data;const c={width:5,height:1,getContext:()=>({drawImage:im=>{data=im.data.slice();},getImageData:()=>({data:data.slice()}),putImageData:im=>{data=im.data.slice();c.data=data;}})};return c;}
const w={console,Uint8ClampedArray,Math,document:{getElementById:id=>id==='paintCanvas'?{width:5,height:1}:null,createElement:canvas},_psdLayers:[layer,other],_psdLayersLoaded:true,_selectedLayerId:'logos',_activeSelectionMask:()=>null,_normalizeColorTolerance:(v,d)=>v==null?d:v,_normalizeAdjustmentHex:v=>v,_backgroundColor:'#000000',_foregroundColor:'#ffffff',_pushLayerUndo:()=>{history++;},recompositeFromLayers:()=>{rendered++;},showToast(){}};
w.window=w;vm.createContext(w);
function extract(file,name){const s=read(file),start=s.indexOf('function '+name+'('),end=s.indexOf('\n}',start)+2;assert.ok(start>=0&&end>start);vm.runInContext(s.slice(start,end),w);}
for(const name of ['_getAdjustmentTarget','_commitAdjustment','autoColorReplace'])extract('mcp/chatgpt/candidates/paint-booth-3-canvas.js',name);
vm.runInContext(read('mcp/chatgpt/native-layer-colour.js'),w);w.SPB_AI_EXPLICIT_COLOR_REPLACE=true;
const N=w.SpbNativeLayerColour,op={layer:'pattern',colour:'#b39a58',sourceColour:'#ff0000',replaceTolerance:0};
const applied=N.apply(op,layer),receipt=N.outcome(op,applied);
assert.equal(applied.ok,true);assert.equal(receipt.status,'applied');assert.equal(receipt.matched_pixels_before_selection,2);
assert.equal(receipt.render_verified,false);assert.equal(receipt.changed_pixels,undefined,'Native match count is not post-selection changed-pixel evidence');
assert.equal(w._selectedLayerId,'logos','Explicit target must not switch user selection');
assert.deepEqual(Array.from(layer.img.data),[179,154,88,255,0,255,0,255,0,0,255,255,179,154,88,80,255,0,0,0]);
assert.equal(layer.img===original,false);assert.deepEqual(Array.from(original.data),Array.from(raw));assert.equal(history,1);assert.equal(rendered,1);
const committed=layer.img;assert.equal(N.apply(op,layer).unchanged,true);assert.equal(history,1);assert.equal(layer.img,committed,'No match creates no image/history');
layer.locked=true;assert.match(N.apply(op,layer).error,/locked/);layer.locked=false;
assert.ok(N.apply({...op,replaceTolerance:-1},layer).error);assert.ok(N.apply({...op,colourOpacity:30},layer).error);
layer.groupName='Custom Spec Map / Red Channel';assert.match(N.apply(op,layer).error,/material/);layer.groupName='Paintable Area';
// Execute actual chat snapshot/restoration around immutable raster swaps.
const ai=read('mcp/chatgpt/candidates/spb-pro-ai.js');
for(const name of ['layerState','layerSame','undoApply']){const start=ai.indexOf('    function '+name+'('),end=ai.indexOf('\n    function ',start+1);vm.runInContext(ai.slice(start,end),w);}
w.zones=[];w.undoZoneFrom=()=>{throw Error('Fixture has no zones');};w.selectedZoneIndex=0;w.renderZones=()=>{};w._finishLayerVisibilityChange=()=>{};
layer.img=original;w.snap={zones:[],layers:vm.runInContext('layerState()',w)};N.apply(op,layer);w.aft={zones:[],layers:vm.runInContext('layerState()',w)};
vm.runInContext('undoApply(snap,aft,true,true)',w);assert.equal(layer.img,original,'Chat Undo restores the exact original drawable');
N.apply(op,layer);w.aft={zones:[],layers:vm.runInContext('layerState()',w)};const later={width:5,height:1,data:raw.slice()};layer.img=later;
vm.runInContext('undoApply(snap,aft,true,false)',w);assert.equal(layer.img,later,'A later raster edit keeps ownership');
console.log(JSON.stringify({pass:true,actual_native_kernel_and_commit:true,exact_layer_without_selection_switch:true,alpha_and_other_colours_preserved:true,no_match_no_history:true,raw_chat_undo_and_later_edit_ownership:true,native_browser:false}));
