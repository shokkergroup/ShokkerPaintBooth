'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');
let epoch=1,resolveShot,shots=0;const feedback=[],undone=[];
const w={console,Promise,Date,setTimeout:()=>0,clearTimeout(){},_gen:0,_snapGen:0,_activeId:'old',RECENT:[],_advUsed:{req:'same',keys:['gold']},_advRejected:[],
 SpbConversationScope:{stamp:()=>epoch,current:x=>x===epoch},
 SpbIntentReport:{since:()=>[{eid:12,t:Date.now(),verdict:'ok',line:'Done — navy changed'}]},
 SpbConvo:{undone:id=>undone.push(id)},SpbFeedback:{send:v=>feedback.push(v)},
 Z:{whenSettled:()=>new Promise(resolve=>{resolveShot=resolve;})},
 undoRestore:()=>true,restorePartRegistryUndo(){},rshotGrab:()=>shots++,render(){}};w.window=w;vm.createContext(w);
for(const f of ['js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','js/spb-encyclopedia-data.js'])vm.runInContext(read(f),w);
vm.runInContext(read('mcp/chatgpt/candidates/spb-offline-builder.js').replace('W.SpbOfflineBuilder = {','W.SpbOfflineBuilder = { _testHtml:builderHtml,'),w);
const ai=read('mcp/chatgpt/candidates/spb-pro-ai.js'),start=ai.indexOf('    function doUndo(entry) {'),end=ai.indexOf('    function refine(entry) {',start);assert.ok(start>=0&&end>start);vm.runInContext(ai.slice(start,end),w);
const B=w.SpbOfflineBuilder;
(async()=>{
 B.state().ran={at:Date.now()-100};B.state().steps=[];
 assert.equal(B._undoChanged({id:11}),false);assert.equal(B.state().ran.undone,undefined);
 w.doUndo({id:12,request:'same',text:'Done',undoable:true,fbSent:true});
 assert.equal(B.state().ran.undone,true);assert.match(B._testHtml(),/Not kept:/);assert.doesNotMatch(B._testHtml(),/✓ Done:/);assert.match(B._testHtml(),/Undone: the preview/);assert.match(B._testHtml(),/data-ob="undo" disabled/);
 assert.match(w.RECENT[0],/buyer/);assert.equal(feedback[0].undo.undone_by_button,true);assert.ok(w._advRejected.includes('gold'));
 epoch++;resolveShot();await Promise.resolve();assert.equal(shots,0,'An old Undo settling callback must not populate the next document image cache');
 w._advUsed={req:'same',keys:['chrome']};const reportEntry={id:12,request:'same',text:'Done',undoable:true,fbSent:true,undoneByCheck:true};
 w.doUndo(reportEntry);assert.match(w.RECENT[1],/verifier/);assert.doesNotMatch(w.RECENT[1],/buyer/);assert.equal(feedback[1].undo.undone_by_button,false);assert.ok(!w._advRejected.includes('chrome'),'Technical verification is not customer taste feedback');
 resolveShot();await Promise.resolve();assert.equal(shots,1);assert.deepEqual(undone,[12,12]);
 console.log('PASS actual Undo path: builder matches chat, unrelated entries ignored, verifier rollback is not buyer feedback, old settling callback cannot capture the next document');
})().catch(e=>{console.error(e);process.exitCode=1;});
