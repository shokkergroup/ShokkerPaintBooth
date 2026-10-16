'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const api=require('./candidates/clipping-mask.js');
const base=require('../../js/canvas/layer/clipping-mask.js');
const saved=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj'),'utf8'));
const rows=saved.layers.map(l=>({...l,img:{id:l.id}}));
const context={canvas:{width:2048,height:2048}};
function draw(which,layers){const drawn=[];const result=which.composeLayerStack(context,layers,{drawLayer:(ctx,l)=>{drawn.push(l.id);return true;}});assert.ok(result.ok,JSON.stringify(result));return drawn;}
const clean=JSON.stringify(rows),original=draw(base,rows);assert.deepEqual(draw(api,rows),original);
const target=rows.find(l=>l.id==='psd_23');target.visible=true;
assert.ok(!draw(base,rows).includes(target.id),'Reproduce actual hidden-parent veto');
assert.deepEqual(draw(api,rows),rows.filter(l=>original.includes(l.id)||l.id===target.id).map(l=>l.id));
assert.equal(draw(api,rows).filter(id=>/^psd_(?:[1-9]|1\d|2[0-4])$/.test(id)).length,1,'Only the selected pattern becomes visible');
target.visible=false;assert.equal(JSON.stringify(rows),clean);assert.deepEqual(draw(api,rows),original,'Visibility Undo restores the original draw set');
// A visible child without an explicit hidden-import baseline does not unlock
// an arbitrary hidden group. Nested parents require the same explicit evidence.
const groups=[{key:'a',name:'Outer',mode:'pass-through',visible:false,ownVisible:false},{key:'b',name:'Inner',mode:'pass-through',visible:false,ownVisible:false}];
const nested=[{id:'n',img:{},visible:true,groupChain:groups}];
assert.deepEqual(draw(api,nested),[]);nested[0].importVisible=false;assert.deepEqual(draw(api,nested),['n']);
const snapshot=JSON.stringify(nested);draw(api,nested);assert.equal(JSON.stringify(nested),snapshot);
const commits=[];
function ctx(){return {canvas:{width:8,height:8},save(){},restore(){},setTransform(){},clearRect(){},drawImage(){commits.push([this.globalAlpha,this.globalCompositeOperation]);}};}
global.document={createElement(){const c=ctx();return {...c.canvas,getContext(){return c;}};}};
const isolated=[{id:'isolated',img:{},visible:true,importVisible:false,groupChain:[{key:'iso',mode:'isolated',visible:false,ownVisible:false,opacity:102,blendMode:'multiply'}]}];
assert.ok(api.composeLayerStack(ctx(),isolated,{drawLayer(){return true;}}).ok);
assert.deepEqual(commits,[[0.4,'multiply']],'The revealed group still applies its opacity and blend exactly once');
console.log('PASS actual42-layer composition: selected hidden-import leaf, sibling preservation, nested groups, exact visibility Undo, immutable source metadata.');
