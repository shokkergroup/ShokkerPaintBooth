'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),w={console,Promise,Set,Map,Date,Uint8Array,setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},localStorage:{getItem:()=>null,setItem(){}},document:{readyState:'loading',addEventListener(){},getElementById:()=>null}};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','js/spb-encyclopedia-data.js','mcp/chatgpt/candidates/spb-offline-builder.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w);
const E=w.SpbProEdit,B=w.SpbOfflineBuilder,env={palette:[{hex:'#19376e',share_pct:95}],layers:[{name:'Body',role:'bodypaint'},{name:'Numbers',role:'numbers'},{name:'Sponsors',role:'sponsors'}],zoneColours:[]};
for(const text of ['Make only the Body layer #B49A55. Keep the Numbers and Sponsors layers exactly unchanged.','Make only the Body layer red. Keep the Numbers and Sponsors layers unchanged.','Make the Body layer red and leave Numbers layer and Sponsors layer untouched.','Make the navy in the Body layer red; keep Numbers, Sponsors layers as is.']) {
 const p=E.plan(text,env);assert.equal(p.kind,'ops',text);assert.equal(p.ops.length,1,text);assert.deepEqual(Array.from(p.ops[0].target.layers),['Body']);assert.deepEqual(Array.from(p.preserved_layers),['Numbers','Sponsors']);assert.equal(p.raw,text);
 const b=B.fromText(text,env);assert.equal(b.steps.length,1,text);assert.deepEqual(Array.from(b.steps[0].what.tg.layers),['Body']);
}
for(const text of ['Make the Body layer red. Keep Body layer exactly unchanged.','Make the Body layer red. Keep Missing layer exactly untouched.','Make the Body layer red. Keep Body layer unchanged.','Make the Body layer red. Keep Missing layer untouched.','Make the whole car red. Keep Numbers and Sponsors layers unchanged.','Make the Body layer red. Keep Numbers and Sponsors layers unchanged and make them blue.']) {
 const p=E.plan(text,env);
 assert.equal(p.prohibited_edit,true,text);const b=B.fromText(text,env);assert.equal(b.steps.length,0,text);assert.ok(b.blocked);
}
const duplicate={...env,layers:env.layers.concat({name:'Numbers'})};assert.equal(E.plan('Make Body layer red. Keep Numbers layer untouched.',duplicate).prohibited_edit,true);
w.SpbProCar={roles:()=>env.layers};
vm.runInContext(fs.readFileSync(path.join(root,'mcp/chatgpt/candidates/spb-intent-report.js'),'utf8'),w);
const measuredScope=w.SpbIntentReport.scopeOf('Make only the Body layer #B49A55. Keep the Numbers and Sponsors layers exactly unchanged.',{queue:[{kind:'add',spec:{region:{everything:true,layers:['Body']}}}]},{});
assert.equal(measuredScope.whole,false);assert.deepEqual(Array.from(measuredScope.layers),['Body']);assert.deepEqual(Array.from(measuredScope.protect).sort(),['Numbers','Sponsors']);
console.log('PASS actual parser + builder: explicit layer protection creates one scoped operation; conflicts, unknown/duplicate names and whole-car targets cannot fall through.');
for(const f of ['js/spb-enc-search.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w);
(async()=>{
 await w.SpbOfflineAnswer.load(async name=>{try{return JSON.parse(fs.readFileSync(path.join(root,'data/encyclopedia',name),'utf8'));}catch{return null;}});
 const text='Make only the Body layer red. Keep the Numbers and Sponsors layers unchanged.';
 const r=w.SpbOfflineAnswer.route(text,env);assert.equal(r.via,'protected-layer-scope');assert.equal(r.steps.length,1);assert.deepEqual(Array.from(r.steps[0].what.layers),['Body']);
 const blocked=w.SpbOfflineAnswer.route('Make the whole car red. Keep Numbers layer untouched.',env);assert.equal(blocked.cls,'ASK');assert.equal(blocked.steps.length,0);
 console.log('PASS actual Offline route: preservation sentences cannot enter compound9 or acquire a whole-car step.');
})().catch(e=>{console.error(e);process.exitCode=1;});
