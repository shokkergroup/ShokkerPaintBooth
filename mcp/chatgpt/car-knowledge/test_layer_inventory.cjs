'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910'),L=require('./layer-reading.js'),old=require(path.join(dir,'layer-inventory-baseline.js'));
const rows=JSON.parse(JSON.parse(fs.readFileSync(path.join(dir,'paint-arca-builder-receipt-pre-2026-10-10T01-03-00-207Z.json'),'utf8')).calls[0].text).layers;
const question='Show my layers. Do not change anything.';assert.equal(old.answer(question,rows),null,'Actual old reader rejects the native inventory question');
const original=JSON.parse(fs.readFileSync(path.join(dir,'layer-inventory-question-baseline.json'),'utf8')).function,c={W:{SpbTemplateLayers:L}};vm.createContext(c);vm.runInContext(original,c);assert.equal(c.isReferenceQuestion(question),false);
const source=fs.readFileSync(path.join(__dirname,'offline-answer.js'),'utf8'),a=source.indexOf('    function isReferenceQuestion('),b=source.indexOf('    function readOnlyQuestion(',a);vm.runInContext(source.slice(a,b),c);assert.equal(c.isReferenceQuestion(question),true);
for(const q of [question,'Show my layers','List loaded layers','Please display my groups','List all layers. Don’t change anything.'.replace('Don’t',"Don't")]){
 const answer=L.answer(q,rows);assert.ok(answer,q);assert.match(answer.text,/42 loaded layer records/);assert.match(answer.text,/Names repeat/);assert.equal(answer.live_context,true);assert.deepEqual(answer.actions,[]);
}
for(const q of ['Show my layers then make the body red','Hide all layers','Show the Base Paint layer','List my layers and remove the wire','Show my red paint scheme'])assert.equal(L.inventoryQuestion(q),false,'Inventory must not absorb edit instructions: '+q);
const empty=L.answer(question,[]);assert.match(empty.text,/No loaded raster/);assert.deepEqual(empty.actions,[]);
const giant=L.answer('List all layers',Array.from({length:1000},(_,i)=>({name:'Layer '+i,group:'Group '+i})));assert.match(giant.text,/300 loaded/);assert.match(giant.text,/bounded overview/);assert.ok(giant.text.length<4000);
const reference=L.answerReference('List all layers',{file:'reference.psd',layer_labels:['Group','Group / Paint'],layer_groups:['Group']});assert.equal(reference.reference_context,true);assert.equal(reference.live_context,false);assert.match(reference.text,/do not verify your loaded file/);
console.log(JSON.stringify({pass:true,original_inventory_missing:true,shared_reference_gate:true,actual_loaded_records:42,no_actions:true,empty_and_bounded_reads:true,edit_tails_not_absorbed:true,native:false}));
