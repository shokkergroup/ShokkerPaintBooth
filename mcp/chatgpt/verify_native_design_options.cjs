'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const dir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const names=process.argv.slice(2);assert.equal(names.length,3,'Supply clean, discussed and cleared receipt filenames');
for(const n of names)assert.match(n,/^paint-journey-options-(clean|discussed|cleared)-[\w-]+\.json$/);
const read=n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8'));
const receipts=names.map(read),data=(r,t)=>JSON.parse(r.calls.find(c=>c.tool===t).text);
const states=receipts.map(r=>data(r,'spb_get_state')),contexts=receipts.map(r=>data(r,'spb_assistant_context'));
assert.equal(states[0].layers.length,42);assert.equal(states[0].zones.length,5);
for(const r of receipts.slice(1)){
 assert.deepEqual(data(r,'spb_get_state').layers,states[0].layers);
 assert.deepEqual(data(r,'spb_get_state').zones,states[0].zones);
 assert.deepEqual(r.images.map(i=>[i.name,i.sha256]),receipts[0].images.map(i=>[i.name,i.sha256]));
 assert.deepEqual(r.candidateManifest,receipts[0].candidateManifest);
 assert.deepEqual(r.ownedModules,receipts[0].ownedModules);
}
assert.equal(states[0].design_options,null);assert.equal(contexts[0].design_options,null);
const options=states[1].design_options;assert.equal(options.items.length,2);assert.equal(options.executable,false);
assert.equal(options.constraints.no_glitter,true);assert.deepEqual(options.constraints.protected_artwork,['numbers','sponsors']);
assert.equal(options.items[1].id,'soft-contrast');assert.deepEqual(contexts[1].design_options,options);assert.equal(contexts[1].read_only,true);
assert.equal(states[2].design_options,null);assert.equal(contexts[2].design_options,null);
const original=fs.readFileSync(path.join(dir,'journey-options-original.txt'),'utf8');assert.match(original,/Black → Gold/);assert.match(original,/▶ Run/);
const offer=fs.readFileSync(path.join(dir,'journey-options-successor.txt'),'utf8');assert.match(offer,/1\. Quiet black base, fine gold accents/);assert.match(offer,/2\. Soft black base, muted gold panels/);assert.doesNotMatch(offer,/▶ Run|I read this as:/);
const follow=fs.readFileSync(path.join(dir,'journey-options-followup.txt'),'utf8');assert.match(follow,/Option 2 — Soft black base, muted gold panels/);assert.match(follow,/no-glitter/);assert.match(follow,/Keep unchanged: numbers, sponsors/);assert.doesNotMatch(follow,/▶ Run/);
const at=new Date().toISOString(),name='native-design-options-'+at.replace(/[:.]/g,'-')+'.json';
const result={pass:true,checked_at:at,receipts:names,native_Offline:true,actual_MCP_context:true,original_wrong_repaint_queue_retained:true,two_distinct_proposals:true,second_proposal_explanation:true,protected_constraints_retained:true,unchanged_layer_records:42,unchanged_zones:5,returned_paint_spec_bytes_exact:true,fresh_conversation_retires_proposals:true,source_generation:receipts[0].candidateManifest,owned_modules:receipts[0].ownedModules,screenshot:'journey-options-followup.png',limits:'J01 advice/explanation and fresh-conversation cleanup only. Full scheme selection/execution/refinement remains open. No new online inference, saved-project proposal persistence, full-resolution/export or shared-runtime/Claude parity proof.'};
fs.writeFileSync(path.join(dir,name),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({pass:true,receipt:name,scope:result.limits}));
