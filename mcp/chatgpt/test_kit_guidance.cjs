'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
let touched=0,epoch=1;
const forbidden=()=>{touched++;throw Error('Guidance must not open, measure or edit a kit');};
const w={console,document:{readyState:'loading',addEventListener(){},querySelector(){return {closest:()=>({querySelector:()=>({textContent:'Car ▾'})})};}},localStorage:{getItem(){return null}},setTimeout(){},setInterval(){},_psdLayers:[],SpbConversationScope:{observe(){},stamp:()=>epoch,current:s=>s===epoch},SpbRevSponsorClean:{},SpbRevSponsor:{off:()=>false,begin:forbidden,measure:forbidden},SpbRevNumbers:{off:()=>false,begin:forbidden,measure:forbidden},SpbRevSponsorUI:{open:forbidden},SpbRevNumbersUI:{open:forbidden}};
w.window=w;vm.createContext(w);
for(const file of ['mcp/chatgpt/editor-capabilities.js','mcp/chatgpt/candidates/spb-offline-builder.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w,{filename:file});
const api=w.SpbEditorCapabilities;
for(const question of ['How does Sponsor Kit work?','How does Number Kit work?','How do I put my logo on both doors?','How can I add a number to the roof?']) {
 const r=w.SpbOfflineAnswer.route(question,{layers:[],palette:[],zoneColours:[]});
 assert.equal(r.cls,'ANSWER',question);assert.equal(r.answer.id,'assistant.live_editor_capabilities');
 assert.match(r.answer.text,/Car > (Sponsor|Number) Kit/);assert.match(r.answer.text,/not verified UV geometry/);
 assert.equal(r.answer.actions.length,0);assert.ok(!r.steps||r.steps.length===0);
}
let sponsor=api.answer('How does Sponsor Kit work?');
assert.match(sponsor.answer.text,/Clear Inside.*inside letters/);
assert.match(api.answer('Where is that?',sponsor).answer.text,/Car > Sponsor Kit/);
epoch++;assert.equal(api.answer('Where is that?',sponsor),null);
assert.equal(api.answer('Where is that?',api.answer('What are Sponsor Kit and Number Kit?')),null);
for(const question of ['Can you place a Sponsor Kit on my car?','Can you open Number Kit?','How does Sponsor Kit work? Then place it on both doors','What is Number Kit and add 32 to my doors','Where is Sponsor Kit? Delete my old logo'])assert.equal(api.answer(question),null,question);
assert.equal(api.read().kits.sponsor.placement_verified,false);
w.SpbRevSponsor.off=()=>true;assert.match(api.answer('What is Sponsor Kit?').answer.text,/disabled/);
w.SpbRevSponsor.off=()=>{throw Error('unreadable');};assert.match(api.answer('What is Sponsor Kit?').answer.text,/could not be confirmed/);
w.SpbRevSponsor.off=()=>false;delete w.SpbRevSponsorUI;assert.match(api.answer('What is Sponsor Kit?').answer.text,/could not be confirmed/);
delete w.SpbRevSponsor;assert.match(api.answer('What is Sponsor Kit?').answer.text,/unavailable/);
w.document.querySelector=()=>null; assert.match(api.answer('Where is Number Kit?').answer.text,/menu location could not be read/);
assert.equal(touched,0);
console.log(JSON.stringify({pass:true,actual_offline_route:true,current_availability:true,no_geometry_claim:true,no_kit_mutations:true,followup_scope:true,mixed_requests_preserved:true}));

