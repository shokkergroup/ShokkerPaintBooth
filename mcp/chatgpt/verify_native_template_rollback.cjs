'use strict';
// Read-only verification of the native refused stale-binding project restore.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),K=require('./car-knowledge/lookup.cjs');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const pre='paint-arca-rollback-pre-2026-10-09T23-40-35-368Z.json',post='paint-arca-rollback-post-2026-10-09T23-42-20-492Z.json';
const receipts=[pre,post].map(f=>JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')));
const states=receipts.map(r=>JSON.parse(r.calls.find(c=>c.tool==='spb_get_state').text));
assert.equal(states[0].layers.length,42);assert.equal(states[0].zones.length,5);
assert.deepEqual(states[0].layers,states[1].layers);assert.deepEqual(states[0].zones,states[1].zones);
const hashes=receipts.map(r=>r.images.map(i=>crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,i.file))).digest('hex')));
assert.deepEqual(hashes[0],hashes[1]);
const proof=states[0].template_identity.source_reference;assert.ok(proof);
assert.equal(proof.sha256,'232e7d9c446e8681d1393f123463449043fc1e2058bc6cc5565190271b2ba093');
assert.deepEqual(proof,states[1].template_identity.source_reference,'Rollback must retain only the prior legitimate proof');
const lookup=K.fromContext('Which car is this template for?',null,states[1]);
assert.equal(lookup.car.id,'stockcars2-arcachevy25');assert.equal(lookup.resolved,true);assert.equal(lookup.template_match.can_target_panels,false);assert.equal(lookup.identity_evidence.current_file_verified,false);
const checked_at=new Date().toISOString(),receipt='arca-native-rollback-verification-'+checked_at.replace(/[:.]/g,'-')+'.json';
const report={pass:true,checked_at,receipts:{pre,post},actual_layers:42,actual_zones:5,layer_zone_metadata_unchanged:true,returned_preview_bytes_unchanged:true,previous_source_reference_unchanged:true,
  matched_car:lookup.car.id,current_file_verified:false,uv_verified:false,
  native_observation:'UI refused Body layer recoloured red -> missing Body binding and reported previous document restored. Subsequent native Offline question identified verified original ARCA ancestry and unverified UV.',
  limits:'One native stale zone-to-layer restore refusal; not all load failures, source replacement, raw source-buffer preservation, actual paint editing or Undo.'};
fs.writeFileSync(path.join(dir,receipt),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({pass:true,receipt,previous_reference_preserved:true,native_preview_unchanged:true,matched_car:lookup.car.id}));
