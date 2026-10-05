const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const geometry = require('../js/canvas/layer/element-transform-state.js');
const raster = require('../js/canvas/layer/layer-transform-raster.js');
const source = fs.readFileSync(require.resolve('../paint-booth-3-canvas.js'), 'utf8');
function body(name) {
    const start = source.indexOf(`function ${name}(`);
    assert.ok(start >= 0);
    const open = source.indexOf('{', start); let depth=1, end=open+1;
    while(depth && end<source.length) { if(source[end]==='{')depth++;else if(source[end]==='}')depth--;end++; }
    return source.slice(start,end);
}
const picked = {x1:865,y1:1730,x2:1250,y2:1990};
const layer={id:'numbers',name:'Numbers',bbox:[100,200,1700,2200],img:{width:1600,height:2000}};
const docCanvas={width:2048,height:2048,style:{}};
let cancels=0, draws=0;
const env={
    window:{SPBElementTransformState:geometry,SPBLayerTransformRaster:raster,_spbLastPickedElementBbox:{layerId:layer.id,...picked}},
    document:{getElementById:()=>docCanvas},getSelectedLayer:()=>layer,_psdLayers:[layer],
    _pendingLayerTransformMeta:null,freeTransformState:null,layerSubRectDragActive:false,
    _getElementInstances:()=>[],_setLayerTransformToolActive(){},_showLayerTransformQuickbar(){},
    drawTransformHandles(){draws++;},showToast(){},renderContextActionBar(){},
    cancelLayerTransform(){cancels++;},
};
vm.createContext(env);
for(const name of ['_getLayerElementGroup','activateLayerTransform','setLayerTransformPositionAxis','setLayerTransformUniformScale','commitLayerTransform']) vm.runInContext(body(name),env);
assert.equal(env.activateLayerTransform(),true);
const state=env.freeTransformState;
assert.equal(state.centerX,1057.5);assert.equal(state.centerY,1860);
assert.equal(state.boxW,385);assert.equal(state.boxH,260);
assert.equal(state.origImageW,1600);assert.equal(state.origImageH,2000);
assert.deepEqual({...state.origSubRect},picked);
assert.equal(env.commitLayerTransform(),false,'unchanged Apply must finish without a raster/history mutation');
assert.equal(cancels,1);assert.equal(layer.img,state.origImg);
state.sessionUndoMode='captured-stack';
assert.equal(env.commitLayerTransform(),false,'unchanged temporary-selection Apply must restore its capture through Cancel');
assert.equal(cancels,2);
state.sessionUndoMode='restore';
assert.equal(geometry.unchanged({...state,origSubRect:null}),true,'whole-layer unchanged Apply also skips rasterization');

env.setLayerTransformPositionAxis('x',1157.5,true);
assert.equal(state.subRect.x1,965);assert.equal(state.subRect.y1,1730);
assert.deepEqual({...state.origSubRect},picked,'moving must retain the original pixel crop');
env.setLayerTransformUniformScale(50,true);
assert.equal(state.subRect.x2-state.subRect.x1,192.5);
assert.equal(state.subRect.y2-state.subRect.y1,130);
assert.equal(geometry.unchanged(state),false);
const calls=[];
const ctx={save(){},restore(){},translate(){},scale(){},rotate(){},drawImage(...args){calls.push(args);}};
raster.drawTransformedSource(ctx,layer.img,state);
assert.deepEqual(calls[0],[layer.img,765,1530,385,260,-96.25,-65,192.5,130],'preview samples only the immutable picked pixels');
state.centerY+=70;state.boxW=770;state.boxH=520;state.scaleX=-1;
geometry.syncFrame(state);
assert.equal(state.scaleX,-2);assert.equal(state.scaleY,2);
assert.equal(state.subRect.y1,1670);assert.deepEqual({...state.origSubRect},picked);
assert.ok(draws>=3);
geometry.initialize(state,picked);
state.dragging='move';state.dragStartX=0;state.dragStartY=0;
state.dragStartCX=state.centerX;state.dragStartCY=state.centerY;
env._transformGetPixel=e=>({x:e.x,y:e.y});
env._isZoneFreeTransformTarget=()=>false;
vm.runInContext(body('onTransformMouseMove'),env);
assert.equal(env.onTransformMouseMove({x:100,y:-80,preventDefault(){}}),true);
assert.equal(state.centerX,1157.5);assert.equal(state.centerY,1780);
assert.equal(state.subRect.x1,965);assert.equal(state.subRect.y1,1650);
assert.deepEqual({...state.origSubRect},picked,'pointer move must not change the source crop used by Apply');
console.log('Element transform: actual activation uses picked center; unchanged Apply skips raster/history; position/scale update destination only; preview crops immutable source pixels.');

env.window.SPBLayerSelectionPlacement=require('../js/canvas/layer/selection-placement.js');
let toolbarMode='zone', switches=0, activeSelection={minX:100,minY:200,maxX:499,maxY:599};
env.isLayerToolbarMode=()=>toolbarMode==='layer';
env.window.setToolbarEditMode=(mode,options)=>{assert.equal(options.preserveTool,true);toolbarMode=mode;switches++;};
env.getSelectedEditableLayer=()=>layer;
env._getActiveSelectionInfo=()=>activeSelection;
env.freeTransformState=null;
vm.runInContext(body('fitLayerToZoneSelection'),env);
assert.equal(env.fitLayerToZoneSelection(),true);
assert.equal(toolbarMode,'layer');assert.equal(switches,1);
assert.equal(env.freeTransformState.centerX,300);assert.equal(env.freeTransformState.centerY,400);
assert.equal(env.freeTransformState.boxW,282);assert.equal(env.freeTransformState.boxH,352);
assert.equal(env.freeTransformState.subRect,undefined,'Fit routes the whole selected layer');
env.freeTransformState=null;toolbarMode='zone';activeSelection=null;
assert.equal(env.fitLayerToZoneSelection(),false);assert.equal(toolbarMode,'zone');assert.equal(switches,1);
env.getSelectedEditableLayer=()=>null;
assert.equal(env.fitLayerToZoneSelection(),false);assert.equal(switches,1);
console.log('Fit Layer: valid Zone target autoroutes through dispatch; missing selection/layer preserves mode and artwork.');

env._selectedLayerId=layer.id;env._psdLayersLoaded=true;
env.zones=[{base:'test_base',pattern:'none'}];env.selectedZoneIndex=0;env.placementLayer='none';
env.getSelectedEditableLayer=()=>layer;env.freeTransformState=null;
let layerActivations=0;const zoneTargets=[];
env.activateLayerTransform=()=>{layerActivations++;return true;};
env.activateFreeTransform=target=>{zoneTargets.push(target);return true;};
for(const name of ['_isZoneFreeTransformTarget','requestContextTransform','activateZoneTransform','activateLayerContextTransform','spbSmartTransform']) vm.runInContext(body(name),env);
toolbarMode='zone';
assert.equal(env.spbSmartTransform(),true);assert.deepEqual(zoneTargets,['base']);assert.equal(layerActivations,0);
env.zones[0].pattern='stripes';
assert.equal(env.requestContextTransform('auto'),true);assert.deepEqual(zoneTargets,['base','pattern']);
toolbarMode='layer';
assert.equal(env.spbSmartTransform(),true);assert.equal(layerActivations,1);assert.equal(zoneTargets.length,2);
env.getSelectedEditableLayer=()=>null;
assert.equal(env.spbSmartTransform(),false,'missing Layer target must not fall through to Zone mutation');
assert.equal(zoneTargets.length,2);
console.log('Transform routing: visible Zone mode wins over background Layer selection; explicit Layer mode never falls through to Zone.');

// Execute the real Shift-click handler, including its state declaration order.
env.freeTransformState={target:'layer',subRect:{...picked},origSubRect:{...picked}};
geometry.initialize(env.freeTransformState,picked);
env.hitTestTransformHandle=()=>null;
const sibling={layerId:layer.id,x1:300,y1:400,x2:500,y2:700};
env.selectConnectedLayerPixelsAtPoint=()=>{env.window._spbLastPickedElementBbox={...sibling};return true;};
for(const name of ['_getLayerElementGroup','onTransformMouseDown']) vm.runInContext(body(name),env);
for(const button of [1,2]) {
    const before=JSON.stringify(env.freeTransformState);
    assert.equal(env.onTransformMouseDown({button,detail:2,x:-10000,y:-10000}),false);
    assert.equal(JSON.stringify(env.freeTransformState),before);
}
assert.equal(env.onTransformMouseDown({x:400,y:500,shiftKey:true,detail:1}),true);
assert.equal(layer.elementLinkGroups.length,1);
assert.equal(layer.elementLinkGroups[0].length,2);
assert.equal(env.onTransformMouseDown({x:400,y:500,shiftKey:true,detail:1}),true);
assert.equal(layer.elementLinkGroups[0].length,2,'Shift-click must not add the same member twice');
env.freeTransformState.subRect={x1:965,y1:1730,x2:1350,y2:1990};
assert.equal(env.onTransformMouseDown({x:400,y:500,shiftKey:true,detail:1}),true);
assert.equal(layer.elementLinkGroups.length,1,'a moved preview still belongs to its immutable source group');
console.log('Linked selection: real Shift-click initializes state, deduplicates members and retains source identity after a preview move.');

const short={x1:0,y1:0,x2:100,y2:40},tall={x1:200,y1:100,x2:240,y2:260};
const groupState={target:'layer',scaleX:1,scaleY:1,rotation:0};
geometry.initialize(groupState,short);geometry.setMembers(groupState,[short,tall]);
assert.equal(groupState.centerX,120);assert.equal(groupState.centerY,130);
groupState.boxW*=.75;groupState.boxH*=.75;geometry.syncFrame(groupState);
let a=geometry.item(groupState,short),b=geometry.item(groupState,tall);
assert.equal(a.width,75);assert.equal(a.height,30);assert.equal(b.width,30);assert.equal(b.height,120);
assert.equal(a.centerX,67.5);assert.equal(a.centerY,47.5);assert.equal(b.centerX,195);assert.equal(b.centerY,167.5);
groupState.rotation=90;
a=geometry.item(groupState,short);b=geometry.item(groupState,tall);
assert.ok(Math.abs(a.centerX-202.5)<1e-7);assert.ok(Math.abs(a.centerY-77.5)<1e-7);
assert.ok(Math.abs(b.centerX-82.5)<1e-7);assert.ok(Math.abs(b.centerY-205)<1e-7);
const grouped={elementLinkGroups:[[short,tall]]};const capture=geometry.captureLinks(grouped);
grouped.elementLinkGroups[0][0].x1=999;geometry.restoreLinks(grouped,capture);
assert.equal(grouped.elementLinkGroups[0][0].x1,0);grouped.elementLinkGroups[0][0].x1=888;
assert.equal(capture.elementLinkGroups[0][0].x1,0,'history must own independent member bounds');
console.log('Group frame: shared center/rotation with independent member proportions; link history owns immutable copies.');

env._layerUndoStack=[];env._layerRedoStack=[];env._effectsSessionUndoPushed=false;
env._trimLayerUndoHistory=()=>{};env.recompositeFromLayers=()=>{};env.renderLayerPanel=()=>{};
for(const name of ['_pushLayerUndo','undoLayerEdit','redoLayerEdit']) vm.runInContext(body(name),env);
layer.elementLinkGroups=[];const originalImg=layer.img;
env._pushLayerUndo(layer,'linked transform');
layer.elementLinkGroups=[[{x1:10,y1:20,x2:40,y2:80}]];
layer.img={width:1600,height:2000,edited:true};const editedImg=layer.img;
assert.equal(env.undoLayerEdit(),true);assert.equal(layer.img,originalImg);assert.equal(layer.elementLinkGroups.length,0);
assert.equal(env.redoLayerEdit(),true);assert.equal(layer.img,editedImg);assert.equal(layer.elementLinkGroups[0][0].x1,10);
layer.elementLinkGroups[0][0].x1=99;
assert.equal(env.undoLayerEdit(),true);assert.equal(layer.elementLinkGroups.length,0);
assert.equal(env.redoLayerEdit(),true);assert.equal(layer.elementLinkGroups[0][0].x1,99);
assert.equal(geometry.memberAt(layer,100,30),null);
assert.equal(geometry.memberAt({elementLinkGroups:[[{x1:10,y1:20,x2:40,y2:80}]]},20,30).x1,10);
console.log('Production image-history Undo/Redo restores pixels and independent link metadata together.');

const memberA={x1:0,y1:0,x2:100,y2:40},memberB={x1:200,y1:100,x2:240,y2:260};
const memberState={target:'layer',scaleX:1,scaleY:1,rotation:0};
geometry.initialize(memberState,memberA);geometry.setMembers(memberState,[memberA,memberB]);
memberState.boxW*=.75;memberState.boxH*=.75;memberState.rotation=30;geometry.syncFrame(memberState);
const transformedB=geometry.item(memberState,memberB);
assert.equal(geometry.transformedMemberAt(memberState,[memberA,memberB],transformedB.centerX,transformedB.centerY),memberB);
memberState.scaleX=-1;
const flippedB=geometry.item(memberState,memberB);
assert.equal(geometry.transformedMemberAt(memberState,[memberA,memberB],flippedB.centerX,flippedB.centerY),memberB);
layer.elementLinkGroups=[[memberA,memberB]];env.freeTransformState=memberState;
let settledGroups=0;
env.commitLayerTransform=()=>{settledGroups++;env.freeTransformState=null;return true;};
vm.runInContext(body('activateLayerTransform'),env);
assert.equal(env.onTransformMouseDown({detail:2,x:flippedB.centerX,y:flippedB.centerY}),true);
assert.equal(settledGroups,1);assert.equal(env.freeTransformState.singleGroupMember,true);
assert.equal(env.freeTransformState.centerX,220);assert.equal(env.freeTransformState.centerY,180);
assert.equal(env.freeTransformState.boxW,40);assert.equal(env.freeTransformState.boxH,160);
assert.equal(env.freeTransformState.sourceMembers,undefined,'single-member session must not expand back to the group frame');
console.log('Double-click member: inverse live matrix picks the right sibling and starts its individual frame after group settlement.');

const candidateStop=new Error('candidate captured');let candidateItems;
env.window.SPBLayerTransformRaster={...raster,composeElementTransforms(options){candidateItems=options.items;throw candidateStop;}};
env.freeTransformState.boxW*=.5;env.freeTransformState.boxH*=.5;
geometry.syncFrame(env.freeTransformState);
vm.runInContext(body('commitLayerTransform'),env);
assert.throws(()=>env.commitLayerTransform(),error=>error===candidateStop);
assert.equal(candidateItems.length,1,'individual member Apply must not rasterize its sibling');
assert.equal(candidateItems[0].sourceRect.x1,memberB.x1);
assert.equal(candidateItems[0].groupRefs[0],memberB,'only the selected committed link bounds advance');
console.log('Production member Apply builds exactly one source crop and retains its matching link record.');

env.document.createElement=()=>({width:0,height:0,getContext:()=>({putImageData(){}})});
env.selectPSDLayer=id=>{env._selectedLayerId=id;};env.drawLayerBounds=()=>{};
layer.groupChain=[{key:'paint-area',blendMode:'pass-through',opacity:255}];layer.groupName='Paintable Area';
vm.runInContext(body('_createLayerFromClipboardData'),env);
const liftedLayer=env._createLayerFromClipboardData({width:20,height:20,offsetX:10,offsetY:10,imageData:{},sourceLayerId:layer.id},
    {idPrefix:'selxform_',insertAboveSource:true,skipUndo:true,linkSourceLayer:true});
assert.equal(env._psdLayers[1],liftedLayer);assert.equal(liftedLayer.sourceLayerId,layer.id);
assert.deepEqual(JSON.parse(JSON.stringify(liftedLayer.groupChain)),layer.groupChain);
assert.notEqual(liftedLayer.groupChain,layer.groupChain);assert.notEqual(liftedLayer.groupChain[0],layer.groupChain[0]);
assert.equal(liftedLayer.groupName,'Paintable Area');
console.log('Selection lift: inserted above source inside an independent copy of its PSD group chain.');
// Actual Pick Item identity path must finish before any alpha read/selection lift.
{
 const linkedRect={x1:1198,y1:995,x2:1542,y2:1286};
 const masterRect={x1:824,y1:971,x2:1111,y2:1311};
 const linkedLayer={id:'linked',img:{},bbox:[400,300,1600,2000],elementInstances:[{sourceBbox:masterRect,instanceBbox:linkedRect}]};
 let activations=0;
 const pickEnv={window:{SPBElementTransformState:geometry},getLayerById:()=>linkedLayer,_selectedLayerId:'linked',activateLayerTransform(){activations++;return true;}};
 vm.createContext(pickEnv);vm.runInContext(body('selectConnectedLayerPixelsAtPoint'),pickEnv);
 for(const [x,y,r] of [[1200,997,linkedRect],[900,1000,masterRect]]) {
  assert.equal(pickEnv.selectConnectedLayerPixelsAtPoint('linked',x,y,{autoTransform:true}),true);
  assert.deepEqual(JSON.parse(JSON.stringify(pickEnv.window._spbLastPickedElementBbox)),{...r,layerId:'linked'});
 }
 assert.equal(activations,2);linkedLayer.locked=true;
 assert.equal(pickEnv.selectConnectedLayerPixelsAtPoint('linked',1200,997,{autoTransform:true}),false);assert.equal(activations,2);
 console.log('Linked Pick Item: actual master/copy path preserves saved padded bounds without pixel lift; lock guard wins.');
}
// The production link command settles geometry, records old links, then publishes.
{
 const originalLinks=[{sourceBbox:{x1:0,y1:0,x2:20,y2:20},instanceBbox:{x1:30,y1:0,x2:50,y2:20}}];
 const target={id:'links',img:{immutable:true},bbox:[0,0,80,40],elementInstances:originalLinks};
 let records=0,renders=0;const candidate=[];
 const linkEnv={freeTransformState:{target:'layer',origSubRect:originalLinks[0].instanceBbox},getSelectedLayer:()=>target,
  window:{SPBElementTransformState:{item:()=>({})},SPBLayerTransformRaster:{transformedAabb:()=>originalLinks[0].instanceBbox},SPBElementInstances:{prepareLinks:()=>({instances:candidate})}},
  commitLayerTransform(){linkEnv.freeTransformState=null;},_pushLayerUndo(l,label){assert.equal(l.elementInstances,originalLinks);assert.equal(label,'break instance link');records++;},
  renderLayerPanel(){renders++;}};
 vm.createContext(linkEnv);vm.runInContext(body('_ctxUpdateInstanceLinks'),linkEnv);
 linkEnv._ctxUpdateInstanceLinks('break');assert.equal(records,1);assert.equal(renders,1);assert.equal(target.elementInstances,candidate);assert.deepEqual(target.img,{immutable:true});
 target.locked=true;linkEnv.freeTransformState={target:'layer',origSubRect:originalLinks[0].instanceBbox};linkEnv._ctxUpdateInstanceLinks('break');assert.equal(records,1);
 console.log('Link command transaction: actual entry settles transform, snapshots before metadata, retains raster and honors lock.');
}
// Transform ownership must be released before a subsequent paint drag.
{
 const releaseEnv={window:{},freeTransformState:{target:'layer',layerId:'gone'},layerSubRectDragActive:true,_psdLayers:[],_setLayerTransformToolActive(){},_hideLayerTransformQuickbar(){},_hideTransformCanvas(){},drawLayerBounds(){}};
 vm.createContext(releaseEnv);vm.runInContext(body('cancelLayerTransform'),releaseEnv);releaseEnv.cancelLayerTransform();assert.equal(releaseEnv.layerSubRectDragActive,false);assert.equal(releaseEnv.freeTransformState,null);
 assert.match(body('commitLayerTransform'),/freeTransformState = null;\s*layerSubRectDragActive = false;/);
 const start=source.indexOf('canvas.onmousemove = function (e) {');const end=source.indexOf('// Pan mode',start);
 const guard=source.slice(start,end)+'moved++;};';const moveEnv={canvas:{},layerSubRectDragActive:true,freeTransformState:null,moved:0};vm.createContext(moveEnv);vm.runInContext(guard,moveEnv);moveEnv.canvas.onmousemove({});assert.equal(moveEnv.moved,1,'stale owner without transform must not swallow brush movement');moveEnv.freeTransformState={target:'layer'};moveEnv.canvas.onmousemove({});assert.equal(moveEnv.moved,1,'active element still owns its movement');
 console.log('Transform release: actual Cancel clears ownership; committed cleanup clears flag; stale owner no longer swallows paint movement.');
}
