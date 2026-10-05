// Isolated event-contract test; real browser drags are verified separately.
import fs from 'node:fs';
import assert from 'node:assert/strict';
const js = new URL('../demo/frontend/js/', import.meta.url);
const asModule = source => 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
const geometry = asModule(fs.readFileSync(new URL('exclude-mask.js', js), 'utf8'));
const { decodeExclusion } = await import(geometry);
class Element {
  constructor(id) { this.id=id; this.handlers={}; this.style={}; this.dataset={}; this.hidden=false; this.value='4'; this.classList={toggle(){}}; }
  addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }
  emit(type, values={}) { const e={target:this,button:0,pointerId:1,isPrimary:true,clientX:216,clientY:116,shiftKey:false,preventDefault(){},...values}; for(const fn of this.handlers[type]||[]) fn(e); }
  closest() { return null; }
  focus() {}
  getBoundingClientRect() { return this.id.startsWith('live') ? {left:500,top:300,width:32,height:16} : {left:200,top:100,width:64,height:32}; }
  setPointerCapture(id) { this.capture=id; }
  hasPointerCapture(id) { return this.capture===id; }
  releasePointerCapture() { this.capture=null; this.emit('lostpointercapture'); }
  getContext() { return {createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData(){},drawImage(){}}; }
}
const elements = new Map();
globalThis.document = new Element('document');
document.getElementById = id => { if(!elements.has(id)) elements.set(id,new Element(id)); return elements.get(id); };
document.querySelector = () => null;
globalThis.window = new Element('window');
globalThis.ResizeObserver = class { observe(){} };
let frames=[];
globalThis.requestAnimationFrame = fn => { frames.push(fn); return frames.length; };
const flush=()=>{while(frames.length){ const next=frames;frames=[];next.forEach(fn=>fn()); }};
const source = fs.readFileSync(new URL('exclude-brush.js',js),'utf8').replace("'./exclude-mask.js'",JSON.stringify(geometry));
const {installExcludeBrush}=await import(asModule(source));
const zone={id:'one',spatialMask:null};
let context={zone,width:32,height:16,key:'doc'},commits=0;
const brush=installExcludeBrush({getContext:()=>context,isActive:()=>true,onCommit:()=>commits++,onStatus:()=>{}});
const el=id=>document.getElementById(id);
const src=el('sourceCanvas'),live=el('liveCanvas');
const pixels=()=>decodeExclusion(zone.spatialMask,32,16);
brush.refresh();flush();
src.emit('pointerdown');src.emit('pointermove',{clientX:240});
assert.equal(zone.spatialMask,null,'one transaction: no mask stored until release');
src.emit('pointerup',{clientX:240});flush();
assert.equal(commits,1);assert.equal(pixels()[8*32+14],2);
assert.equal(el('excludeCursor').style.left,'240px');
assert.equal(el('excludeCursor').style.width,'8px','source cursor uses 2x displayed scale');
const before=JSON.stringify(zone.spatialMask);
live.emit('pointerdown',{clientX:514,clientY:308,shiftKey:true});
document.emit('keydown',{key:'Escape'});flush();
assert.equal(JSON.stringify(zone.spatialMask),before,'Escape rolls back a restore stroke');
assert.equal(commits,1);
live.emit('pointerdown',{clientX:514,clientY:308,shiftKey:true});
live.emit('pointerup',{clientX:514,clientY:308,shiftKey:true});flush();
assert.equal(pixels()[8*32+14],0,'Shift restores the same native pixel on LIVE');
assert.equal(el('excludeCursor').style.width,'4px','LIVE cursor uses its own display scale');
assert.equal(commits,2);
document.emit('keydown',{key:'z',ctrlKey:true});flush();
assert.equal(JSON.stringify(zone.spatialMask),before,'Ctrl+Z restores the whole prior mask');
for(const cancelType of ['pointercancel','lostpointercapture']) {
  src.emit('pointerdown',{clientX:250,clientY:110});src.emit(cancelType);flush();
  assert.equal(JSON.stringify(zone.spatialMask),before,cancelType+' must roll back');
}
src.emit('pointerdown',{clientX:250,clientY:110});window.emit('blur');flush();
assert.equal(JSON.stringify(zone.spatialMask),before,'focus loss must roll back');
const other={id:'two',spatialMask:null};
src.emit('pointerdown',{clientX:250,clientY:110});context={...context,zone:other};
src.emit('pointerup',{clientX:252,clientY:110});flush();
assert.equal(JSON.stringify(zone.spatialMask),before,'switching zones cannot commit stale target');
assert.equal(other.spatialMask,null);
context={...context,zone};el('excludeClear').emit('click');flush();
assert.equal(zone.spatialMask,null);el('excludeUndo').emit('click');flush();
assert.equal(JSON.stringify(zone.spatialMask),before,'Clear is undoable');
el('excludeSizeValue').value='160';el('excludeSizeValue').emit('input');
assert.equal(Number(el('excludeSize').value),160,'typed size immediately changes active brush');
el('excludeSizeValue').value='';el('excludeSizeValue').emit('input');
assert.equal(el('excludeSizeValue').value,'','typing an empty intermediate value is allowed');
el('excludeSizeValue').value='999';el('excludeSizeValue').emit('change');
assert.equal(Number(el('excludeSize').value),512,'size clamps to safe maximum');
const priorCommits=commits;src.emit('pointerdown',{button:2});src.emit('pointerup');flush();
assert.equal(commits,priorCommits,'right button does not paint');
console.log(JSON.stringify({transaction:true,sourceAndLive:true,restore:true,escape:true,pointerCancel:true,focusLoss:true,zoneSwitch:true,undo:true,clearUndo:true,numericSize:true}));
