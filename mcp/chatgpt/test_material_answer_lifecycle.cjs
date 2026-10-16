'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const w={window:null,console,Date,Math,JSON,Set,Map,WeakSet,localStorage:{getItem:k=>k==='SPB_CONVO'?'1':null},document:{addEventListener(){}},setInterval(){},setTimeout(){}};w.window=w;vm.createContext(w);
const pro=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates/spb-convo-state.js'),'utf8'),w);
const helperStart=pro.indexOf('    var _completedMaterialFacts'),helperEnd=pro.indexOf('    function composerPending()',helperStart);assert.ok(helperStart>0&&helperEnd>helperStart);
vm.runInContext('var _completedReadOnlyAnswers=new WeakSet();\n'+pro.slice(helperStart,helperEnd),w);
const terminal=pro.split('\n').find(l=>l.includes('catch (eCV5)')&&l.includes('completeMaterialAnswer'));assert.ok(terminal);
const call=terminal.slice(0,terminal.indexOf('/*'));
const q='Can I keep my sponsors matte while the body stays chrome? Please explain only.';
function finish(text,r,id,registered){
 w.SpbConvo.turn(text,{producer:'offline',turn:'t-'+id});w.SpbConvo.noteRoute({cls:'ANSWER',topic:'assistant.live_editor_capabilities'},text);
 Object.assign(w,{entry:{id,role:'ai',lines:[],notes:[]},r,text});if(registered){w._completedReadOnlyAnswers.add(r);if(r.enc?.editor_topic==='material')w._completedMaterialFacts.set(r,{topic:r.enc.id,stamp:r.enc.document_stamp});}vm.runInContext(call,w);
}
const payload=()=>({offline:true,enc:{id:'assistant.live_editor_capabilities',editor_topic:'material'}});
finish(q,payload(),1,true);assert.equal(w.SpbConvo.pending(),null);assert.equal(w.SpbConvo.view().last_target,null);assert.equal(w.SpbConvo.view().history.at(-1).act,'answer');assert.equal(w.SpbConvo.view().history.at(-1).look,undefined);assert.equal(w.SpbConvo.changes().length,0);
finish(q,payload(),2,false);assert.ok(w.SpbConvo.pending(),'Model or restored payload has no local producer identity');
const stale={offline:true,enc:{id:'assistant.live_editor_capabilities',editor_topic:'material',document_stamp:1}};w.SpbConversationScope={current:()=>false};finish(q,stale,22,true);assert.ok(w.SpbConvo.pending(),'Stale local completion cannot retire the new document state');delete w.SpbConversationScope;
finish('What material is on the selected layer? Explain only.',payload(),3,true);assert.equal(w.SpbConvo.pending(),null,'A later completed material fact retires the older soft slot');
const unrelated={offline:true,enc:{id:'other',editor_topic:'doctor'}};finish(q,unrelated,4,true);assert.ok(w.SpbConvo.pending(),'Only the reviewed material topic changes behavior');
w.SPB_CX3_OFF=true;finish(q,payload(),5,true);assert.ok(w.SpbConvo.pending(),'Kill switch retains original conversation semantics');w.SPB_CX3_OFF=false;
w.SpbConvo.turn('Which layer?',{turn:'ask'});w.SpbConvo.note({act:'ask',missing:['target'],asked:'Which layer?'});assert.equal(w.SpbConvo.completeReadOnly('Which layer?',5,'x'),false);assert.deepEqual(Array.from(w.SpbConvo.pending().missing),['target']);
assert.equal(w.SpbConvo.completeReadOnly('old document',5,'x'),false);
w.SpbConvo.reset();assert.equal(w.SpbConvo.completeReadOnly(q,1,'x'),false,'Entry from old document cannot complete the reset store');
// Real edits/Undo/Redo/offer still retain their target and look semantics.
w.SpbConvo.turn('Make the body chrome',{turn:'edit'});const ch=w.SpbConvo.commit({targets:[{kind:'layer',layers:['Body']}],look:{finish_class:'chrome'},undo_id:'u',source:'offline'});assert.equal(w.SpbConvo.completeReadOnly('Make the body chrome',99,'x'),false);assert.equal(w.SpbConvo.changes().length,1);w.SpbConvo.undone('u');assert.equal(w.SpbConvo.changes()[0].undone,true);w.SpbConvo.redone('u');assert.equal(w.SpbConvo.changes()[0].undone,false);
w.SpbConvo.turn('Show options',{turn:'options'});w.SpbConvo.offer({kind:'options',items:[{label:'Matte'},{label:'Chrome'}]});assert.equal(w.SpbConvo.completeReadOnly('Show options',99,'x'),false);assert.ok(w.SpbConvo.view().last_offer);
console.log(JSON.stringify({pass:true,actual_candidate_kernel_and_terminal_caller:true,material_fact_no_inferred_chrome_or_soft_ask:true,local_identity_only:true,genuine_ask_edit_offer_undo_redo_preserved:true,document_and_kill_guards:true}));
