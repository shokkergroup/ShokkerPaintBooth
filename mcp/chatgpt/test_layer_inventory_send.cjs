'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910'),L=require('./car-knowledge/layer-reading.js'),D=require('./design-intent.js');
const rows=JSON.parse(JSON.parse(fs.readFileSync(path.join(dir,'paint-arca-builder-receipt-pre-2026-10-10T01-03-00-207Z.json'),'utf8')).calls[0].text).layers;
const old=JSON.parse(fs.readFileSync(path.join(dir,'inventory-send-baseline.json'),'utf8')).function;
const source=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8'),a=source.indexOf('    function send(text, o) {'),m=source.slice(a+1).match(/^    function \w+\(/m),current=source.slice(a,a+1+m.index);
function load(code,online=false){
 const cards=[],input={value:'question'},w={console,Promise,_busy:false,_log:[],_panel:{querySelector:()=>input},SpbConversationScope:{observe(){}},SpbDesignBrief:{observe(){}},SpbAiConnect:{relaying:()=>online},SpbDesignIntent:D,SpbTemplateLayers:L,SpbOfflineBuilder:{offlineMode:()=>!online,showAnswer:p=>cards.push(p)},SpbCarReferenceAnswer:{isReferenceQuestion:q=>L.inventoryQuestion(q),readOnlyQuestion:q=>{const answer=L.answer(q,rows);return answer?{cls:'ANSWER',hits:[],answer}:null;}},finish:r=>r};w.window=w;vm.createContext(w);
 assert.ok(code.includes('// CAR-KNOWLEDGE:'));vm.runInContext(code.replace('// CAR-KNOWLEDGE:',"throw Error('legacy shortcut reached'); // CAR-KNOWLEDGE:"),w);return {w,cards,input};
}
const question='Show my layers. Do not change anything.';
assert.throws(()=>load(old).w.send(question),/legacy shortcut reached/,'Actual previous Send bypasses the common inventory reader');
for(const q of [question,'Show my layers','List loaded layers']){
 const c=load(current),r=c.w.send(q);assert.equal(c.cards[0].answer.title,'Your loaded layers');assert.match(c.cards[0].answer.text,/42 loaded/);assert.ok(Array.isArray(r.queue)&&r.queue.length===0);assert.ok(Array.isArray(r.tools)&&r.tools.length===0);assert.equal(c.input.value,'');assert.match(r.text,/Loaded layers/);
}
assert.throws(()=>load(current).w.send('Show my layers then make the body red'),/legacy shortcut reached/,'Editing tail is not silently converted to a read-only answer');
assert.throws(()=>load(current,true).w.send('Show my layers'),/legacy shortcut reached/,'Connected assistant keeps its online routing');
const advice=load(current),r=advice.w.send('Advice only: would matte black and satin gold look good?');assert.equal(advice.cards[0].answer.id,'assistant.design_advice');assert.match(r.text,/Design advice/);
console.log(JSON.stringify({pass:true,original_shortcut_bypass:true,actual_Send_inventory:true,no_queue_or_tools:true,online_route_preserved:true,design_advice_preserved:true,native:false}));
