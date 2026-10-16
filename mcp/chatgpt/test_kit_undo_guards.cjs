'use strict';
// Actual shared OA2 module, then exact review proposal. No native app writes.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),cp=require('node:child_process');
const root=path.resolve(__dirname,'../..'),file=path.join(root,'js/spb-online-kits.js');
const original=fs.readFileSync(file,'utf8');
const patched=cp.execFileSync('C:/Python313/python.exe',[path.join(__dirname,'kit_undo_edits.py'),file],{encoding:'utf8'});
function harness(source){
 let allowed=true,undo=0,begin=0,end=0,finish;
 const finding={key:'test',title:'Test',fixes:[{id:'fix',label:'Fix'}]};
 const w={console,Promise,Date,JSON,Set,Map,_psdLayers:[{id:'body',name:'Body'}],zones:[],_layerUndoStack:[],localStorage:{getItem:()=>null},document:{getElementById:()=>null},spbProAI:{mcpCall:()=>({ok:true})}};
 w.window=w;w.SpbAiLease={begin:()=>{begin++;return allowed;},end:()=>{end++;}};
 w.undoDrawStroke=()=>{undo++;w._layerUndoStack.pop();};
 w.SPBRevDoctor={result:()=>({findings:[finding]}),fix:async()=>{w._layerUndoStack.push({});return {ok:true,gone:true};},run:()=>new Promise(r=>{finish=r;})};
 vm.runInNewContext(source,w,{filename:file});
 return {w,run:a=>w.spbProAI.mcpCall('kit',a),deny:()=>{allowed=false;},allow:()=>{allowed=true;},finish:()=>finish({findings:[]}),stats:()=>({undo,begin,end})};
}
async function seed(h){const r=await h.run({kit:'spec',action:'fix',finding:'test',fix:'fix'});assert.equal(r.result.changed,true);}
(async()=>{
 const old=harness(original);await seed(old);old.deny();const unsafe=await old.run({action:'undo'});assert.equal(unsafe.result.changed,true);assert.equal(old.stats().undo,1,'Reproduce missing lease check in current shared source');
 const h=harness(patched);await seed(h);h.deny();const denied=await h.run({action:'undo'});assert.equal(denied.ok,false);assert.match(denied.error,/owns editing/);assert.equal(h.stats().undo,0);assert.equal(h.stats().end,1,'Denied lease must not release another owner');
 h.allow();const pending=h.run({kit:'spec',action:'check'});const busy=await h.run({action:'undo'});assert.equal(busy.ok,false);assert.match(busy.error,/still running/);assert.equal(h.stats().undo,0);h.finish();await pending;
 const done=await h.run({action:'undo'});assert.equal(done.result.changed,true);assert.equal(h.stats().undo,1);assert.equal(h.stats().end,2,'Accepted Undo releases its lease');
 const empty=await h.run({action:'undo'});assert.equal(empty.result.changed,false);assert.equal(h.stats().undo,1);assert.equal(h.stats().end,3);
 h.w.SPB_ONLINE_KITS_OFF=true;const off=await h.w.SpbOnlineKits.run({action:'undo'});assert.equal(off.ok,false);assert.equal(h.stats().undo,1);
 console.log('PASS: reproduced shared kit Undo ownership bypass; exact proposal blocks denied lease and busy work, permits one valid Undo, releases ownership and preserves no-op/off behavior. Component evidence only.');
})().catch(e=>{console.error(e);process.exitCode=1;});
