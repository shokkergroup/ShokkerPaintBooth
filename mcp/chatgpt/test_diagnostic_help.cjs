'use strict';
// Exercise the shipped native capability APIs and actual Offline routing.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),storage=new Map();
const w={console,document:{readyState:'loading',addEventListener(){},querySelector(){return null},getElementById(){return null}},localStorage:{getItem:k=>storage.get(k)||null,setItem(){throw Error('Read-only help wrote a setting');}},setTimeout(){throw Error('Read-only help scheduled work');},setInterval(){throw Error('Read-only help scheduled work');},_psdLayers:[]};
w.window=w;w.addEventListener=()=>{};vm.createContext(w);
function load(file){vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w,{filename:file});}
for(const f of ['js/rev/doctor/doctor-core.js','js/rev/doctor/doctor-ui.js','js/rev/seam/seam.js','mcp/chatgpt/editor-capabilities.js'])load(f);
for(const key of ['run','fix','open','_renderFull'])w.SPBRevDoctor[key]=()=>{throw Error('Reader invoked Doctor '+key);};
for(const key of ['ensure','renderField','setOn'])w.SpbRevSeam[key]=()=>{throw Error('Reader invoked Edge Bleed '+key);};
const api=w.SpbEditorCapabilities;
assert.equal(api.read().spec_doctor.enabled,true);
assert.equal(api.read().edge_bleed.on,false);
assert.equal(api.read().edge_bleed.extension_px,16);
const questions=['What does Spec Doctor check?','Why are my sponsor decals shiny?','How does Edge Bleed work?','How do I fix fringes around panel edges?','Does Spec Doctor fix shimmer in the spec?'];
for(const q of questions){const a=api.answer(q);assert.ok(a,q);assert.equal(a.answer.actions.length,0);assert.equal(a.answer.how.length,0);assert.match(a.answer.text,/No (?:scan|setting)/);}
assert.match(api.answer(questions[1]).answer.text,/symptom alone does not identify/);
assert.match(api.answer('How does Edge Bleed work?').answer.text,/does not align a stripe/);
w.SPB_REV_DOCTOR_OFF=true;assert.equal(api.read().spec_doctor.enabled,false);assert.match(api.answer(questions[0]).answer.text,/currently disabled/);delete w.SPB_REV_DOCTOR_OFF;
storage.set('SPB_REV_SEAM_OFF','1');assert.equal(api.read().edge_bleed.enabled,false);assert.match(api.answer(questions[2]).answer.text,/currently disabled/);storage.clear();
for(const q of ['What is Spec Doctor? Run it now','What is Spec Doctor and fix my paint','Can you run Spec Doctor?','How does Edge Bleed work? Then enable it','What is Spec Doctor? Export my paint','Why are my decals shiny? Make them matte'])assert.equal(api.answer(q),null,q);
for(const f of ['mcp/chatgpt/candidates/spb-offline-builder.js','mcp/chatgpt/candidates/spb-offline-answer.js'])load(f);
for(const q of questions){const a=w.SpbOfflineAnswer.route(q,{layers:[],palette:[],zoneColours:[]});assert.equal(a.answer.id,'assistant.live_editor_capabilities',q);assert.equal(a.answer.actions.length,0);}
// Disabled initial module is a boolean-off stub, not the normal off() API.
w.SPBRevDoctor={off:true};assert.equal(api.read().spec_doctor.enabled,false);
w.SpbRevSeam.status=()=>{throw Error('Unreadable cache');};assert.equal(api.read().edge_bleed.on,null);
w.SPBRevDoctor=undefined;w.SpbRevSeam=undefined;
assert.equal(api.read().spec_doctor.installed,false);assert.equal(api.read().edge_bleed.installed,false);
assert.match(api.answer(questions[0]).answer.text,/unavailable/);
console.log(JSON.stringify({pass:true,native_APIs:true,actual_offline_route:true,read_only:true,unavailable_disabled_unknown:true,mixed_edit_requests_preserved:true}));
