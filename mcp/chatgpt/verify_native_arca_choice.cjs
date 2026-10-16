'use strict';
// Real native Ask -> Enter follow-up -> Run -> Save -> Undo -> Save receipts.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910'),projects=path.join(root,'_release_evidence/chatgpt-dev/59910/projects');
const names=['paint-arca-input-successor-pre-2026-10-10T00-21-43-396Z.json','paint-arca-input-choice-post-2026-10-10T00-22-22-495Z.json','paint-arca-body-run-post-2026-10-10T00-22-41-956Z.json','paint-arca-body-undo-post-2026-10-10T00-24-07-334Z.json'];
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),receipts=names.map(n=>read(path.join(dir,n)));
const states=receipts.map(r=>JSON.parse(r.calls.find(c=>c.tool==='spb_get_state').text));
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const images=r=>r.images.map(i=>({name:i.name,sha256:digest(path.join(dir,i.file))}));
assert.equal(states[0].layers.length,42);assert.equal(states[0].zones.length,5);
assert.deepEqual(states[0].layers,states[1].layers);assert.deepEqual(states[0].zones,states[1].zones);assert.deepEqual(images(receipts[0]),images(receipts[1]));
assert.deepEqual(states[0].layers,states[2].layers);assert.equal(states[2].zones.length,6);
assert.notEqual(images(receipts[0])[0].sha256,images(receipts[2])[0].sha256);
assert.equal(images(receipts[0]).at(-1).name,'spec_map');assert.deepEqual(images(receipts[0]).at(-1),images(receipts[2]).at(-1));
assert.deepEqual(states[0].layers,states[3].layers);assert.deepEqual(states[0].zones,states[3].zones);assert.deepEqual(images(receipts[0]),images(receipts[3]));
const projectNames=['ARCA exact-layer baseline - private59910.spbproj','ARCA body red after exact choice - private59910.spbproj','ARCA exact body choice Undo - private59910.spbproj'];
const [baseline,after,undo]=projectNames.map(n=>read(path.join(projects,n)));
assert.equal(baseline.layers.length,42);assert.deepEqual(baseline.layers,after.layers);assert.deepEqual(baseline.layers,undo.layers);
assert.equal(after.config.zones.length,6);assert.deepEqual(baseline.config.zones,undo.config.zones);
const added=after.config.zones[0];assert.equal(added.sourceLayer,'psd_0');assert.deepEqual(added.sourceLayers,['psd_0']);
assert.equal(added.sourceLayerBindings.psd_0.label,'Paintable Area / Base Paint');assert.equal(added.sourceLayerBindings.psd_0.ambiguous,false);
assert.equal(added.baseColor,'#c8102e');
const checked_at=new Date().toISOString(),file='arca-native-choice-run-undo-'+checked_at.replace(/[:.]/g,'-')+'.json';
const report={pass:true,checked_at,receipts:names,project_receipts:projectNames.map(n=>({name:n,sha256:digest(path.join(projects,n))})),actual_layers:42,
 choice_prompt:'Make the Base Paint layer red',displayed_choices:4,typed_followup:'the body one',followup_submission:'Enter',reviewed_step:'Paintable Area / Base Paint layer -> Red',
 no_edits_before_Run:true,added_zone_exact_current_ID:'psd_0',saved_42_source_rasters_and_all_settings_unchanged:true,returned_spec_preview_bytes_unchanged:true,
 native_Undo_saved_five_zones_exact:true,native_Undo_paint_spec_preview_bytes_exact:true,authentication:'Offline Helper; no model inference or API request',
 evidence_limits:'Cached previews are JPEG, not full-resolution export or edge-preservation proof. Source Base Paint includes broad canvas coverage; visible gray mask/background also recolours. Exact binding is not UV/panel-only scope proof. ChatGPT/Claude inference of this conversation, production promotion and customer52-scenario gate remain unproved.',
 source_hashes:Object.fromEntries(['layer-targets.js','builder_input_edits.py','test_builder_input.cjs','build_candidates.py'].map(n=>[n,digest(path.join(__dirname,n))]))};
fs.writeFileSync(path.join(dir,file),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({pass:true,receipt:file,source_layers_preserved:42,exact_body_ID:'psd_0',spec_preview_unchanged:true,Undo_exact:true}));
