'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const names=process.argv.slice(2);assert.equal(names.length,2,'Supply unverified-reload and verified-open receipt filenames');
for(const n of names)assert.match(n,/^paint-identity-welcome-[\w-]+\.json$/);
const receipts=names.map(n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8')));
const data=(r,t)=>JSON.parse(r.calls.find(c=>c.tool===t).text),states=receipts.map(r=>data(r,'spb_get_state'));
const summaries=receipts.map(r=>data(r,'spb_assistant_context').car_reference.live_identity_summary);
assert.equal(summaries[0].status,'conflict');assert.equal(summaries[1].status,'verified-source');
assert.equal(states[0].template_identity.source_reference,null);
assert.equal(states[1].template_identity.source_reference.sha256,'232e7d9c446e8681d1393f123463449043fc1e2058bc6cc5565190271b2ba093');
for(const summary of summaries)assert.equal(summary.can_target_panels,false);
assert.match(summaries[1].text,/ARCA Chevrolet SS/);
for(let i=0;i<2;i++){
 const text=fs.readFileSync(path.join(dir,i?'identity-welcome-verified.txt':'identity-welcome-unverified.txt'),'utf8');
 assert.ok(text.includes(summaries[i].text),'Visible welcome agrees with actual MCP context');
 assert.doesNotMatch(text,/I recognise your car: NASCAR Cup|I know where its hood/);
}
assert.equal(states[0].layers.length,42);assert.equal(states[0].zones.length,5);
assert.deepEqual(states[1].layers,states[0].layers);assert.deepEqual(states[1].zones,states[0].zones);
assert.deepEqual(receipts[1].images.map(i=>[i.name,i.sha256]),receipts[0].images.map(i=>[i.name,i.sha256]));
assert.deepEqual(receipts[1].candidateManifest,receipts[0].candidateManifest);assert.deepEqual(receipts[1].ownedModules,receipts[0].ownedModules);
const baseline=fs.readFileSync(path.join(dir,'identity-welcome-original.txt'),'utf8');assert.match(baseline,/NASCAR Cup Chevrolet SS.*I know where its hood/);
const at=new Date().toISOString(),file='native-identity-welcome-'+at.replace(/[:.]/g,'-')+'.json';
const result={pass:true,checked_at:at,receipts:names,original_false_Cup_and_geometry_claim_retained:true,unverified_conflict_and_verified_ARCA_native:true,actual_MCP_same_identity_summary:true,unchanged_layer_records:42,unchanged_zones:5,returned_paint_spec_bytes_exact:true,screenshots:['identity-welcome-unverified.png','identity-welcome-verified.png'],limits:'Private59910 welcome and read-only context. Not actual provider reasoning, shared-runtime adoption, UV geometry or full-resolution/export verification.'};
fs.writeFileSync(path.join(dir,file),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({pass:true,receipt:file,scope:result.limits}));
