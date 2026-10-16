'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const input={value:''},button={setAttribute(){}},status={},docks={'.spb-pbn':{hidden:false,steps:['keep']},'.spb-ob':{hidden:false,steps:['keep']}},attrs={},listeners={};
const actions=[{disabled:false},{disabled:true}];
const panel={setAttribute(k,v){attrs[k]=v;},getAttribute(k){return attrs[k];},querySelectorAll(){return actions;},querySelector(s){return s==='.spb-pai-input'?input:s==='[data-act="send"]'?button:docks[s]||status;},addEventListener(k,f,capture){assert.equal(capture,true);listeners[k]=f;}};
const ctx={_busy:false,_panel:panel,Math,Promise,String,window:{},finishCore(){return Promise.resolve();}};vm.createContext(ctx);
let begin=src.indexOf('    var _composerFinishing = 0'),end=src.indexOf('    // ------------------------------------------------------------------ FIRSTTEST',begin);vm.runInContext(src.slice(begin,end),ctx);
begin=src.indexOf("        _panel.addEventListener('input', function (ev) {");end=src.indexOf("        _panel.addEventListener('click', function (ev) {",begin);vm.runInContext(src.slice(begin,end),ctx);
const event=(extra={})=>({target:input,stopped:false,prevented:false,stopImmediatePropagation(){this.stopped=true;},preventDefault(){this.prevented=true;},...extra});
ctx._composerFinishing=1;ctx.composerSync();input.value='A little finer again.';let ev=event();listeners.input(ev);assert.equal(ev.stopped,true);assert.equal(ctx._composerHeldDraft,true);assert.equal(attrs['data-spb-compose-hold'],'1');assert.equal(input.value,'A little finer again.');
ev=event({key:'Enter'});listeners.keydown(ev);assert.equal(ev.prevented,true);assert.equal(ev.stopped,true,'Pending Enter cannot reach builder markTyped');
ev=event({key:'Enter',shiftKey:true});listeners.keydown(ev);assert.equal(ev.prevented,false,'Multiline drafting still works');
for(const name of ['spb-pbn.js','spb-offline-builder.js']){
 const text=fs.readFileSync(path.join(__dirname,'candidates',name),'utf8'),a=text.indexOf('    function draw() {'),b=text.indexOf('\n        var ',text.indexOf("getAttribute('data-spb-compose-hold')",a)+1);
 const prefix=text.slice(a,b);const dock=docks[name==='spb-pbn.js'?'.spb-pbn':'.spb-ob'];const gate={panel:()=>panel,dock:()=>dock,ensureDock:()=>dock};vm.createContext(gate);vm.runInContext(prefix+'\nthrow new Error("normal draw");}',gate);gate.draw();assert.equal(dock.hidden,true);assert.deepEqual(dock.steps,['keep'],'Draft gate preserves prepared state');
 attrs['data-spb-compose-hold']='0';assert.throws(()=>gate.draw(),/normal draw/,'Ordinary drawing remains reachable');attrs['data-spb-compose-hold']='1';
}
assert.equal(actions[0].disabled,true);assert.equal(actions[1].disabled,true);ctx.composerSettled();assert.equal(actions[0].disabled,false);assert.equal(actions[1].disabled,true,'Pre-existing disabled actions stay disabled');assert.equal(button.disabled,false);assert.equal(attrs['data-spb-compose-hold'],'1','Draft keeps unrelated choosers silent after completion');assert.equal(input.value,'A little finer again.');
ev=event({key:'Enter'});listeners.keydown(ev);assert.equal(ev.stopped,false,'Ready Enter reaches normal typed-send listeners');
input.value='';ev=event();listeners.input(ev);assert.equal(ctx._composerHeldDraft,false);assert.equal(attrs['data-spb-compose-hold'],'0');assert.equal(ev.stopped,false,'Clearing the draft restores ordinary input guidance');
assert.ok(src.indexOf("_panel.addEventListener('keydown', function (ev) {\n            if (ev.target ===")<src.indexOf("_panel.addEventListener('click', function (ev) {"));
console.log(JSON.stringify({pass:true,generated_native_capture_handlers:true,pending_enter_does_not_mark_planner_turn:true,shift_enter_allowed:true,draft_does_not_replace_guides:true,ready_send_and_cleared_draft_restore_normal_routing:true}));
