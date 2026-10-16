'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const c={console};c.window=c;vm.createContext(c);
for(const file of ['layer-targets.js','candidates/spb-intent-frame.js','candidates/spb-intent-plan.js','candidates/spb-intent-model.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,file),'utf8'),c,{filename:file});
const layers=[{id:'psd_0',name:'Body',role:'body paint'},{id:'psd_1',name:'Numbers',role:'numbers'},
 {id:'psd_2',name:'Sponsors',group:'Decals',role:'sponsors'},
 {id:'psd_3',name:'Base Paint',group:'Paint',role:'body paint'},
 {id:'psd_4',name:'Base Paint',group:'Spec / Metallic',role:'metallic'},
 {id:'psd_5',name:'Sponsors',group:'Backup',role:'sponsors'}];
const env={layers,text:'Make only the Body layer #B49A55.'};
const make=ref=>({v:1,act:'change',decals:'protect',ops:[{verb:'recolour',target:{kind:'layer',layers:[ref]},look:{colour:{hex:'#B49A55'}}}]});
const norm=ref=>c.SpbIntentModel.fromCall({frame:make(ref)},env);
const a=norm('psd_0');assert.equal(a.frame.ops[0].target.layers[0],'Body');
assert.equal(c.SpbIntentFrame.validate(a.frame,env).ok,true);
const duplicate=norm('psd_3');assert.equal(duplicate.frame.ops[0].target.layers[0],'psd_3');
assert.equal(c.SpbIntentFrame.validate(duplicate.frame,env).ok,true);
assert.equal(norm('Spec / Metallic / Base Paint').frame.ops[0].target.layers[0],'psd_4');
assert.equal(c.SpbIntentFrame.validate(make('Base Paint'),env).ok,false);
assert.equal(c.SpbIntentFrame.validate(make('psd_missing'),env).ok,false);
assert.ok(norm('Base Paint').repairs.some(x=>x.includes('unknown layer')));
const p=c.SpbIntentPlan.plan(duplicate.frame,env);assert.equal(p.act,'change');
assert.ok(JSON.stringify(p).includes('psd_3'));
const sponsor=c.SpbIntentPlan._regionFor({kind:'layer',layers:['psd_2']},c.SpbIntentPlan._normEnv(env),{parts:[],elements:[],layers:[],objects:[]},'protect');
assert.equal(sponsor.scope.decals,'named');
const collision={layers:[{id:'psd_0',name:'Body'},{id:'other',name:'psd_0'}]};
assert.equal(c.SpbLayerTargets.resolve('psd_0',collision.layers).row.name,'Body');
c.SpbProCar={roles:()=>layers,parts:()=>[]};
assert.equal(c.SpbIntentPlan.live().layers[3].id,'psd_3');
assert.equal(c.SpbIntentPlan.live().layers[3].group,'Paint');
vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates/spb-mcp-frames.js'),'utf8'),c);
const prepared=c.SpbMcpFrames.prepare({text:env.text,frame:make('psd_0')},{layers:()=>layers});
assert.equal(prepared.ok,true,JSON.stringify(prepared));
assert.ok(prepared.flat.length>0,'real MCP preparation must produce a queue');
assert.equal(prepared.frame.ops[0].target.layers[0],'Body');
const repeated=c.SpbMcpFrames.prepare({text:'Make only the Paint / Base Paint layer #B49A55.',frame:make('psd_3')},{layers:()=>layers});
assert.equal(repeated.ok,true,JSON.stringify(repeated));
assert.equal(repeated.frame.ops[0].target.layers[0],'psd_3');
assert.ok(JSON.stringify(repeated.flat).includes('psd_3'));
for(const bad of ['Base Paint','psd_missing']){
 const result=c.SpbMcpFrames.prepare({text:env.text,frame:make(bad)},{layers:()=>layers});
 assert.equal(result.ok,false,bad+' must not be turned into a broader operation');
 assert.equal(result.flat,undefined);
}
// Replay the actual model's failed call against its recorded native layer inventory.
// This verifies planning only; it does not substitute for a live edit/Undo test.
const evidence=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const actualRun=JSON.parse(fs.readFileSync(path.join(evidence,'layered-model-probe-2026-10-10T09-14-00-939Z.json'),'utf8'));
const actualCall=actualRun.calls.find(x=>x.tool==='spb_do');assert.ok(actualCall);
const captured=JSON.parse(fs.readFileSync(path.join(evidence,'paint-frame-id-pre-2026-10-10T09-24-37-160Z.json'),'utf8'));
const nativeLayers=JSON.parse(captured.calls.find(x=>x.tool==='spb_get_state').text).layers;
c.SpbProCar={roles:()=>nativeLayers,parts:()=>[]};
const actualArgs=typeof actualCall.arguments==='string'?JSON.parse(actualCall.arguments):actualCall.arguments;
assert.equal(actualArgs.frame.ops[0].target.layers[0],'psd_0');
const replay=c.SpbMcpFrames.prepare(actualArgs,{layers:()=>nativeLayers});
assert.equal(replay.ok,true,JSON.stringify(replay));assert.ok(replay.flat.length);
assert.equal(replay.frame.ops[0].target.layers[0],'Body');
assert.ok(!JSON.stringify(replay.flat).includes('psd_1')&&!JSON.stringify(replay.flat).includes('psd_2'));
console.log('PASS frame IDs, qualified groups, ambiguity refusal, role protection and live identity');
if(process.argv.includes('--record')){
 const crypto=require('node:crypto'),checked=new Date().toISOString();
 const files=['frame_layer_edits.py','layer-targets.js','candidates/spb-intent-model.js','candidates/spb-intent-frame.js','candidates/spb-intent-plan.js','candidates/spb-mcp-frames.js'];
 const hashes=Object.fromEntries(files.map(file=>[file,crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,file))).digest('hex')]));
 const receipt=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910/frame-layer-components-'+checked.replace(/[:.]/g,'-')+'.json');
 fs.writeFileSync(receipt,JSON.stringify({pass:true,checked,source_hashes:hashes,native_edit:false,native_undo:false},null,2)+'\n',{flag:'wx'});
 console.log(path.basename(receipt));
}
