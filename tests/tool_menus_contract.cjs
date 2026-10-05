// SPB-93: execute menu event handlers, including protection of canvas Escape.
const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const listeners = {};
const document = {activeElement:null, addEventListener(type, fn, capture){listeners[type]=fn; if(type==='keydown') assert.equal(capture,true);}};
const style = {removeProperty(key){delete this[key];}};
const popup = {style, getBoundingClientRect:()=>({left:1000,right:1210,top:120})};
const menu = {open:false,matches:()=>true,querySelector:q=>q==='summary'?summary:popup,querySelectorAll:()=>buttons};
const summary = {closest:()=>menu,matches:()=>false,focus(){document.activeElement=this;}};
const buttons = Array.from({length:3}, (_,i)=>({
    id:i, closest:()=>menu, matches:()=>false, getClientRects:()=>[{}],
    focus(){document.activeElement=this;},scrollIntoView(){}
}));
const bar = {
    querySelectorAll:()=>menu.open?[menu]:[],querySelector:()=>menu.open?menu:null,
    contains:target=>target===menu||target===summary||buttons.includes(target),
    addEventListener(type,fn){listeners['bar:'+type]=fn;}
};
document.getElementById=()=>bar;
const window = {innerWidth:1100,innerHeight:900,addEventListener(type,fn){listeners['window:'+type]=fn;}};
vm.runInNewContext(fs.readFileSync('js/canvas/tool-menus.js','utf8'),{document,window,getComputedStyle:()=>({visibility:'visible'})});
function key(key, target=document.activeElement, extra={}) {
    const event={key,target,preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;},...extra};
    listeners.keydown(event); return event;
}
summary.focus();
let event=key('ArrowDown');
assert.equal(menu.open,true); assert.equal(document.activeElement,buttons[0]);
assert.equal(style.transform,'translateX(-118px)'); assert.equal(style.maxHeight,'772px');
assert.ok(event.prevented&&event.stopped);
key('End'); assert.equal(document.activeElement,buttons[2]);
key('ArrowDown'); assert.equal(document.activeElement,buttons[0]);
key('ArrowUp'); assert.equal(document.activeElement,buttons[2]);
key('Home'); assert.equal(document.activeElement,buttons[0]);
event=key('Escape'); assert.equal(menu.open,false); assert.equal(document.activeElement,summary);
assert.ok(event.prevented&&event.stopped, 'Menu Escape must never reach a canvas cancel handler');
event=key('Escape'); assert.equal(event.stopped,undefined,'Canvas Escape stays available with no open menu');
const input={closest:()=>menu,matches:()=>true};
event=key('ArrowDown',input); assert.equal(event.prevented,undefined,'Leave native form navigation alone');
event=key('ArrowDown',summary,{ctrlKey:true}); assert.equal(event.prevented,undefined);
menu.open=true; listeners.click({target:{}}); assert.equal(menu.open,false);
menu.open=true; listeners['bar:click']({target:{closest:()=>({closest:()=>menu})}}); assert.equal(menu.open,false);
console.log('Menu navigation, viewport clamp, Escape isolation, native input and closing contracts passed');
