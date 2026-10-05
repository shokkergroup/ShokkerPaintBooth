const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const api=require('../js/canvas/zone/material-instance-transform.js');
const model=require('../js/canvas/zone/material-instance-model.js');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const record=model.create({}, {x1:20,y1:10,x2:60,y2:30},200,100,'base','copy');
const sibling={...JSON.parse(JSON.stringify(record)),id:'sibling',instanceBbox:{x1:120,y1:60,x2:160,y2:80}};
const zone={id:'zone',baseOffsetX:.5,baseOffsetY:.5,patternInstances:[record,sibling]};
assert.equal(api.hit(zone,{x:96,y:20},200,100),api.targetFor(record));
assert.equal(api.hit(zone,{x:140,y:70},200,100),api.targetFor(sibling));
assert.equal(api.hit(zone,{x:199,y:99},200,100),null);
let history=[],renders=0;
const pc={width:200,height:100,style:{},getBoundingClientRect:()=>({left:0,top:0,width:200,height:100})};
const c={window:{SPBZoneMaterialInstanceTransform:api},zones:[zone],selectedZoneIndex:0,freeTransformState:null,layerSubRectDragActive:false,
 document:{getElementById:()=>pc,querySelectorAll:()=>[]},
 _setLayerTransformToolActive(){},updateDrawZoneIndicator(){},_hideLayerTransformQuickbar(){},_hideTransformCanvas(){},
 _showZoneTransformNumericPanel(){},_refreshZoneTransformNumericPanel(){},drawTransformHandles(){},renderContextActionBar(){},renderZones(){},
 onTransformMouseDown(){},onTransformMouseMove(){},onTransformMouseUp(){},
 triggerPreviewRender(){renders++;},pushZoneUndo(label){history.push({label,zone:JSON.parse(JSON.stringify(zone))});},showToast(){},
 activateLayerTransform(){assert.fail('instance routed to Layer');}};
vm.createContext(c);
function load(name,next){const a=source.indexOf('function '+name+'('),b=source.indexOf('function '+next+'(',a);assert(a>=0&&b>a);vm.runInContext(source.slice(a,b),c);}
load('_isZoneFreeTransformTarget','_getZoneFreeTransformTargetState');
load('_getZoneFreeTransformTargetState','_setZoneFreeTransformTargetState');
load('_zoneTransformTargetLabel','activateFreeTransform');
load('activateFreeTransform','deactivateFreeTransform');
load('deactivateFreeTransform','drawTransformHandles');
load('setZoneTransformUniformScale','setZoneTransformPosition');
c.activateFreeTransform(api.targetFor(record));
assert.equal(c.freeTransformState.centerX,96);assert.equal(c.freeTransformState.centerY,20);
assert.equal(c.freeTransformState.boxW,40);assert.equal(c.freeTransformState.boxH,20);assert.equal(c.freeTransformState.scaleX,1);
const before=JSON.parse(JSON.stringify(zone));
Object.assign(c.freeTransformState,{centerX:110,centerY:45,boxW:20,boxH:10,scaleX:.5,scaleY:.5,rotation:90});
c.deactivateFreeTransform(true);
assert.equal(history.length,1);assert.deepEqual(history[0].zone,before);
assert.deepEqual(record.instanceBbox,{x1:100,y1:40,x2:120,y2:50});assert.equal(record.rotation,90);
assert.deepEqual(record.sourceBbox,before.patternInstances[0].sourceBbox);assert.deepEqual(sibling,before.patternInstances[1]);
assert.equal(zone.baseOffsetX,.5);assert.equal(zone.baseOffsetY,.5);assert.equal(c.freeTransformState,null);
assert.equal(api.hit(zone,{x:110,y:54},200,100),api.targetFor(record));
assert.equal(api.hit(zone,{x:119,y:45},200,100),null,'rotated narrow side bounds');
c.activateFreeTransform(api.targetFor(record));
assert.equal(c.freeTransformState.scaleX,.5);c.setZoneTransformUniformScale(50,true);
assert.equal(c.freeTransformState.boxW,20,'50% after re-pick is stable');c.deactivateFreeTransform(true);assert.equal(history.length,1,'unchanged Apply skips history');
const committed=JSON.parse(JSON.stringify(zone));c.activateFreeTransform(api.targetFor(record));c.freeTransformState.centerX+=30;c.deactivateFreeTransform(false);
assert.deepEqual(zone,committed);assert.equal(history.length,1);assert(renders>=3,'Apply/no-op/Cancel refresh final preview');
let calls=[];const ctx={save(){calls.push('save');},restore(){calls.push('restore');},translate(...a){calls.push(a);},rotate(){},drawImage(...a){calls.push(a);}};
api.draw(ctx,{target:api.targetFor(record),centerX:110,centerY:45,boxW:20,boxH:10,rotation:90},zone,200,100,{naturalWidth:100,naturalHeight:50});
assert.equal(calls[0],'save');assert.equal(calls.at(-1),'restore');assert.deepEqual(calls.find(x=>Array.isArray(x)&&x.length===9).slice(1,5),[10,5,20,10]);
console.log('Actual Zone instance activation/Apply/Cancel/scale: correct independent frame, exact history, unchanged source/siblings, stable re-pick scale and cropped ghost pass.');
