const assert=require('node:assert/strict');
const preview=require('../js/canvas/layer/transform-preview.js');
const geometry=require('../js/canvas/layer/element-transform-state.js');
const raster=require('../js/canvas/layer/layer-transform-raster.js');
let allocations=0,resizes=0,composites=0,lastLayers;
function createCanvas(w,h){
    allocations++;let width=w,height=h;
    const canvas={style:{visibility:''},get width(){return width;},set width(v){width=v;resizes++;},
        get height(){return height;},set height(v){height=v;resizes++;}};
    const ctx={canvas,setTransform(){},clearRect(){},save(){},restore(){},translate(){},scale(){},rotate(){},drawImage(){}};
    canvas.getContext=()=>ctx;return canvas;
}
const source={width:100,height:100};
const layer={id:'art',img:source,bbox:[0,0,100,100],opacity:137,blendMode:'multiply',groupChain:[{key:'group'}]};
const below={id:'below'},above={id:'above'};const layers=[below,layer,above];
const state={target:'layer',layerId:'art',origImg:source,origBbox:layer.bbox.slice(),scaleX:1,scaleY:1,rotation:0};
geometry.initialize(state,{x1:10,y1:10,x2:30,y2:30});state.centerX+=5;geometry.syncFrame(state);
const options={layers,width:100,height:100,revision:1,geometry,raster,createCanvas,
    compose(ctx,stack){composites++;lastLayers=stack;return {ok:true};}};
const first=preview.render(state,options);
assert.equal(preview.peek(state),first);assert.equal(allocations,3);
assert.equal(lastLayers[0],below);assert.equal(lastLayers[2],above);
assert.notEqual(lastLayers[1],layer);assert.equal(lastLayers[1].opacity,137);
assert.equal(lastLayers[1].blendMode,'multiply');assert.equal(lastLayers[1].groupChain,layer.groupChain);
assert.equal(layer.img,source);assert.deepEqual(layer.bbox,[0,0,100,100]);
assert.equal(preview.render(state,options),first);assert.equal(composites,1,'unchanged handle redraw reuses composite');
state.centerX+=5;geometry.syncFrame(state);preview.render(state,options);
assert.equal(composites,2);assert.equal(allocations,3,'move reuses all session buffers');
assert.equal(resizes,0,'stable-size moves never reset canvas storage');
preview.render(state,{...options,revision:2});assert.equal(composites,3);
const sourceCanvas={style:{visibility:'visible'}};
preview.show(sourceCanvas);preview.show(sourceCanvas);assert.equal(sourceCanvas.style.visibility,'hidden');
preview.restore(sourceCanvas);assert.equal(sourceCanvas.style.visibility,'visible');
preview.restore(sourceCanvas);assert.equal(sourceCanvas.style.visibility,'visible');
const whole={...state,origSubRect:undefined,sourceMembers:undefined,boxW:40,boxH:20,rotation:90};
assert.ok(preview.render(whole,options));
assert.equal(layer.img,source,'whole preview also leaves committed pixel storage alone');
assert.throws(()=>preview.render(state,{...options,revision:3,compose:()=>({ok:false,issues:[{reason:'unsupported group'}]})}),/unsupported group/);
assert.equal(preview.peek(state),null,'failed composite must not be reported as a valid transparent preview');
const lifted={id:'selxform_test',sourceLayerId:layer.id,img:{width:20,height:20},bbox:[10,10,30,30]};
const liftedState={target:'layer',layerId:lifted.id,origImg:lifted.img,origBbox:lifted.bbox,
    centerX:30,centerY:30,origCenterX:20,origCenterY:20,boxW:20,boxH:20,origBoxW:20,origBoxH:20,rotation:15,scaleX:1,scaleY:1};
preview.render(liftedState,{...options,layers:[below,layer,lifted,above]});
assert.equal(lastLayers.length,3,'a lifted selection previews merged back into its source');
assert.equal(lastLayers[1].id,layer.id);assert.equal(lastLayers[1].opacity,137);
assert.equal(lastLayers[1].blendMode,'multiply');assert.notEqual(lastLayers[1].img,source);
assert.equal(layer.img,source);assert.equal(lifted.img,liftedState.origImg);
console.log('Transform preview: immutable layers/order/material flags; pooled moves with no resize; revision-aware memo; source visibility restored.');
