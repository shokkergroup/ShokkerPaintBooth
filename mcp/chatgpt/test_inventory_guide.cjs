'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const dir=path.join(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const old=JSON.parse(fs.readFileSync(path.join(dir,'inventory-guide-baseline.json'),'utf8'));
const builder=fs.readFileSync(path.join(__dirname,'candidates/spb-offline-builder.js'),'utf8');
const show=builder.slice(builder.indexOf('    function showAnswer(')).split('\n')[0];
const pbn=fs.readFileSync(path.join(__dirname,'candidates/spb-pbn.js'),'utf8'),a=pbn.indexOf('    function draw()'),b=pbn.indexOf('        var en = env()',a);
function answer(code){const c={S:{steps:[{kind:'paint'}],ran:null},draw(){}};vm.createContext(c);vm.runInContext(code,c);c.showAnswer({answer:{id:'assistant.template_layers'}},'Show my layers');return c.S;}
assert.equal(answer(old.showAnswer).steps.length,1,'Actual old answer leaves stale pending steps');
assert.equal(answer(show).steps.length,0);assert.equal(answer(show).liveText,'');
function draw(code,state){const d={hidden:false,innerHTML:'generic guide'},c={W:{},S:{text:''},CUR:{},ensureDock:()=>d,OB:()=>({offlineMode:()=>true,state:()=>state}),builderBusy:()=>false};vm.createContext(c);vm.runInContext(code+"throw Error('guide continued'); }",c);let continued=false;try{c.draw();}catch(e){assert.match(e.message,/guide continued/);continued=true;}return {d,continued};}
const readonly={answer:{answer:{id:'assistant.template_layers'}},liveText:'',steps:[]};
assert.equal(draw(old.draw_prefix,readonly).continued,true,'Actual old guide ignores factual answer');
const current=pbn.slice(a,b),r=draw(current,readonly);assert.equal(r.continued,false);assert.equal(r.d.hidden,true);assert.equal(r.d.innerHTML,'');
for(const state of [{...readonly,liveText:'Make the body red'},{...readonly,steps:[{kind:'paint'}]},{answer:null,liveText:'',steps:[]}])assert.equal(draw(current,state).continued,true);
const design={answer:{via:'design-advice',answer:{id:'assistant.design_advice'}},liveText:'',steps:[]};
assert.equal(draw(current,design).d.hidden,true,'A resolved saved-option explanation suppresses unrelated suit/helmet recommendations');
assert.equal(draw(current,{...design,liveText:'Make the body red'}).continued,true,'New typing restores the ordinary guide');
console.log(JSON.stringify({pass:true,original_stale_steps:true,original_guide_conflict:true,actual_factual_answer_clears_steps:true,actual_guide_suppression:true,new_typing_preserved:true,native:false}));
