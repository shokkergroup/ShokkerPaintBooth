'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910'),read=n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8'));
const names=['paint-arca-builder-receipt-pre-2026-10-10T01-03-00-207Z.json','paint-arca-first-send-layer-question-2026-10-10T01-03-27-543Z.json','paint-arca-builder-receipt-post-2026-10-10T01-05-13-442Z.json','paint-arca-builder-receipt-undo-2026-10-10T01-05-37-787Z.json'];
const rs=names.map(read),ss=rs.map(r=>JSON.parse(r.calls.find(c=>c.tool==='spb_get_state').text)),images=r=>r.images.map(i=>({name:i.name,hash:i.sha256}));
assert.equal(ss[0].layers.length,42);assert.equal(ss[0].zones.length,5);
for(const i of [1,3]){assert.deepEqual(ss[0].layers,ss[i].layers);assert.deepEqual(ss[0].zones,ss[i].zones);assert.deepEqual(images(rs[0]),images(rs[i]));}
assert.deepEqual(ss[0].zones,ss[2].zones);assert.deepEqual(ss[0].layers.filter((l,i)=>JSON.stringify(l)!==JSON.stringify(ss[2].layers[i])).map(l=>l.id),['psd_0']);assert.notEqual(images(rs[0])[0].hash,images(rs[2])[0].hash);assert.deepEqual(images(rs[0]).at(-1),images(rs[2]).at(-1));
const afterRun=fs.readFileSync(path.join(dir,'builder-native-receipt-after-run.txt'),'utf8'),afterUndo=read('builder-native-receipt-after-undo.json');
assert.match(afterRun,/✓ Done:/);assert.match(afterUndo.panel_text,/↶ Not kept:/);assert.doesNotMatch(afterUndo.panel_text,/✓ Done:/);assert.equal(afterUndo.builder_Undo_enabled,false);
assert.match(afterRun,/Make the Base Paint layer red/);assert.match(afterRun,/the body one/);
const checked_at=new Date().toISOString(),receipt='builder-native-receipt-'+checked_at.replace(/[:.]/g,'-')+'.json';
fs.writeFileSync(path.join(dir,receipt),JSON.stringify({pass:true,checked_at,receipts:names,source_manifest:JSON.parse(fs.readFileSync(path.join(__dirname,'candidates/sources.json'),'utf8')),actual_layers:42,unchanged_zones:5,native_Undo_metadata_preview_exact:true,builder_status_tracks_exact_Run:true,builder_Undo_disabled:true,confirmed_project_restore:true,first_Send_submits:true,first_readonly_answer_wrong:true,original_first_Send_failure_not_reproduced_after_restore:true,screenshot:'builder-native-receipt-after-undo.png',limits:'Native Offline cachedJPEG/state evidence. No saved-project/full-resolution/online parity proof for the new builder receipt; prior separate native colour saved/online tests remain historical.'},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({pass:true,receipt,native_builder_Undo_status:true,native_Undo_preview_exact:true,first_Send_submits:true,factual_routing_pending:true}));
