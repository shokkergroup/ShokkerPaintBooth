'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const names=process.argv.slice(2);assert.equal(names.length,3);
for(const n of names)assert.match(n,/^paint-recovered-visibility-[\w-]+\.json$/);
const records=names.map(n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8')));
const state=records.map(r=>JSON.parse(r.calls.find(c=>c.tool==='spb_get_state').text));
assert.equal(state[0].layers.length,42);assert.equal(state[0].zones.length,5);
const changed=state[0].layers.filter((l,i)=>JSON.stringify(l)!==JSON.stringify(state[1].layers[i])).map(l=>l.id);
assert.deepEqual(changed,['psd_23']);assert.deepEqual(state[0].layers,state[2].layers);
for(const s of state){assert.deepEqual(s.zones,state[0].zones);assert.deepEqual(s.template_identity,state[0].template_identity);}
assert.equal(state[0].template_identity.source_reference.sha256,'232e7d9c446e8681d1393f123463449043fc1e2058bc6cc5565190271b2ba093');
const images=records.map(r=>r.images.map(i=>[i.name,i.sha256]));
assert.deepEqual(images[0],images[2]);assert.notDeepEqual(images[0][0],images[1][0]);assert.deepEqual(images[0].at(-1),images[1].at(-1));
(async()=>{
const response=await fetch('http://127.0.0.1:59910/js/canvas/layer/clipping-mask.js');assert.equal(response.status,200);
const hash=crypto.createHash('sha256').update(Buffer.from(await response.arrayBuffer())).digest('hex');
for(const r of records)assert.equal(hash,r.privateRuntime.layer_visibility_candidate.candidate_sha256);
const result={pass:true,checked_at:new Date().toISOString(),receipts:names,only_changed_layer:'psd_23',all_42_layer_records_restored:true,five_zones_and_spec_preview_unchanged:true,returned_paint_preview_changed_and_exactly_restored:true,original_source_reference_preserved:true,served_compositor_sha256:hash,scope:'Actual native Show and toolbar Undo on recovered ARCA project. Visually inspected pattern appears. Not provider inference, completed black/gold design, full-resolution export, verified UV geometry or old-project automatic recovery.'};
fs.writeFileSync(path.join(dir,'native-recovered-visibility.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1;});
