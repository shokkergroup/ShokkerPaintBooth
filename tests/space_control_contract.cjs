const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const handlerStart=source.indexOf("document.addEventListener('keydown', (e) => {",source.indexOf('function _activeToolConsumesHardnessShortcut'));
const first=source.slice(handlerStart,source.indexOf('// Escape: deselect layer',handlerStart))+"});";
const cursorStart=source.indexOf("document.addEventListener('keydown', function (e) {",source.indexOf('[27] PAN cursor feedback'));
const second=source.slice(cursorStart,source.indexOf("document.addEventListener('keyup'",cursorStart));
function run(code,tag,editable=false){
 const viewport={style:{cursor:'paint'}},canvas={style:{cursor:'paint'}},callbacks=[];
 const ctx={spaceHeld:false,document:{activeElement:{tagName:tag,isContentEditable:editable},
 getElementById:id=>id==='canvasViewport'?viewport:canvas,addEventListener:(name,fn)=>callbacks.push(fn)}};
 vm.runInNewContext(code,ctx);
 let prevented=false;callbacks[0]({code:'Space',repeat:false,defaultPrevented:false,preventDefault:()=>{prevented=true;}});
 return {held:ctx.spaceHeld,prevented,viewport:viewport.style.cursor,canvas:canvas.style.cursor};
}
for(const tag of ['BUTTON','SUMMARY','INPUT','SELECT','TEXTAREA']){
 assert.deepEqual(run(first,tag),{held:false,prevented:false,viewport:'paint',canvas:'paint'},tag+' retains native Space');
 assert.equal(run(second,tag).canvas,'paint',tag+' does not flash pan cursor');
}
assert.equal(run(first,'DIV',true).prevented,false,'contenteditable retains spaces');
assert.equal(run(second,'DIV',true).canvas,'paint');
assert.deepEqual(run(first,'CANVAS'),{held:true,prevented:true,viewport:'grab',canvas:'paint'},'canvas Space still holds pan');
assert.equal(run(second,'CANVAS').canvas,'grab');
console.log('Space: production pan handlers preserve native buttons/forms/editing and retain canvas pan.');
