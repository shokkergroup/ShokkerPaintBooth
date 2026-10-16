'use strict';
// Exercise the actual event-binding function with replaced DOM textboxes.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
function run(file,off=false){
 const s=fs.readFileSync(file,'utf8'),start=s.indexOf('    function attach() {'),end=s.indexOf('    function markTyped(',start);
 assert.ok(start>=0&&end>start);const events={},seen=[],state={termPin:false};
 function textbox(value){return {value,events:{},addEventListener(name,fn){this.events[name]=fn;}};}
 const first=textbox('first request');let live=first;
 const panel={querySelector:()=>live,addEventListener(name,fn){(events[name]||=[]).push(fn);}};
 const c={W:{SPB_CX3_OFF:off},S:state,panel:()=>panel,dock:()=>null,offlineMode:()=>true,draw(){},flag:t=>[t],clearTimeout(){},setTimeout:()=>0,
  markTyped(value,src){if(value.trim())seen.push({value,src});}};
 vm.createContext(c);vm.runInContext(s.slice(start,end)+'\nattach();',c);
 function emit(name,ev){for(const fn of events[name]||[])fn(ev);}
 const send={closest:sel=>sel==='[data-act="send"]'?{}:null};
 emit('click',{target:send});assert.equal(seen[0].value,'first request');
 first.value='';live=textbox('the body one');vm.runInContext('attach();',c);
 emit('click',{target:send});const sendFollow=seen.some(x=>x.value==='the body one'&&x.src==='send');
 emit('keydown',{target:live,key:'Enter'});const enterFollow=seen.some(x=>x.value==='the body one'&&x.src==='enter');
 live.value='new visible words';emit('input',{target:live});const liveFlags=state.liveText==='new visible words';
 const before=seen.length;emit('keydown',{target:live,key:'Enter',shiftKey:true});assert.equal(seen.length,before,'Shift+Enter stays multiline');
 const current=state.liveText;emit('input',{target:textbox('unrelated')});assert.equal(state.liveText,current,'Other controls cannot overwrite chat flags');
 assert.equal(events.click.length,2,'Reattach does not duplicate Send/chip handlers');
 return {sendFollow,enterFollow,liveFlags};
}
const root=path.resolve(__dirname,'../..');
assert.deepEqual(run(path.join(root,'js/spb-offline-builder.js'),true),{sendFollow:false,enterFollow:false,liveFlags:false},'Owner kill path preserves the original three rerender failures');
assert.deepEqual(run(path.join(root,'js/spb-offline-builder.js')),{sendFollow:true,enterFollow:true,liveFlags:true},'Owner adopted current-textbox delegation');
assert.deepEqual(run(path.join(__dirname,'candidates/spb-offline-builder.js')),{sendFollow:true,enterFollow:true,liveFlags:true});
assert.deepEqual(run(path.join(__dirname,'candidates/spb-offline-builder.js'),true),{sendFollow:false,enterFollow:false,liveFlags:false});
console.log('PASS shared and candidate input binding; owner kill path retained; current textbox without duplicate handlers');
