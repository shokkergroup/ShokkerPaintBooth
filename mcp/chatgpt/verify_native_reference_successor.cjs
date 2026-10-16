'use strict';
// Verify real read-only subscription delivery and its native pre/post receipts.
// The earlier wrong-variant model receipt remains unchanged.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const names={model:'context-session-probe-2026-10-09T23-36-19-939Z.json',pre:'paint-arca-reference-successor-pre-2026-10-09T23-36-14-834Z.json',post:'paint-arca-reference-successor-post-2026-10-09T23-37-32-192Z.json'};
const read=n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8')),model=read(names.model),pre=read(names.pre),post=read(names.post);
const digest=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const state=r=>JSON.parse(r.calls.find(c=>c.tool==='spb_get_state').text);
const a=state(pre),b=state(post);assert.equal(a.layers.length,42);assert.equal(a.zones.length,5);
assert.deepEqual(a.layers,b.layers,'Readonly inference must preserve actual layer records');assert.deepEqual(a.zones,b.zones);
const images=r=>r.images.map(i=>({name:i.name,sha256:digest(path.join(dir,i.file))}));assert.deepEqual(images(pre),images(post),'Returned native preview bytes must remain identical');
assert.equal(model.authentication,'ChatGPT');assert.equal(model.apiFallback,false);assert.equal(model.exitCode,0);assert.deepEqual(model.errors,[]);
const allowed=new Set(['spb_assistant_context','spb_wait_for_message','spb_reply','spb_get_state','spb_status','spb_car_knowledge','spb_encyclopedia']);
assert.ok(model.calls.every(c=>allowed.has(c.tool)&&c.status==='completed'));
const contextCall=model.calls.find(c=>c.tool==='spb_assistant_context'),context=JSON.parse(contextCall.result.content.find(c=>c.type==='text').text),reference=context.car_reference;
assert.equal(reference.match_reason,'source-name-recognition-conflict');assert.equal(reference.resolved,false);assert.equal(reference.identity_conflict,true);
assert.deepEqual(reference.candidates.map(c=>c.id).sort(),['stockcars-chevyss','stockcars2-arcachevy25']);assert.equal(reference.identity_evidence.current_file_verified,false);
const replies=model.calls.filter(c=>c.tool==='spb_reply');assert.equal(replies.length,1);const reply=replies[0].arguments.text;
for(const id of ['psd_0','psd_37','psd_38','psd_40'])assert.ok(reply.includes(id));
assert.match(reply,/cannot verify the exact car variant/i);assert.match(reply,/UV positions/);assert.match(reply,/reference labels do not prove/i);
const checked_at=new Date().toISOString(),receipt='arca-reference-model-successor-'+checked_at.replace(/[:.]/g,'-')+'.json';
const report={pass:true,checked_at,receipts:names,authentication:'ChatGPT',api_fallback:false,readonly_calls:model.calls.length,replies:1,
  actual_layers:42,actual_zones:5,layer_zone_records_unchanged:true,returned_preview_bytes_unchanged:true,preview:images(post),
  car_identity_conflict:'unresolved; ARCA and Legacy Cup candidates',source_proof_after_reload:false,uv_verified:false,
  evidence_limits:'No paint edit, full-resolution source-buffer comparison, failed Open rollback, production installation or Claude model parity is proved.',
  verification_source_hashes:Object.fromEntries(['assistant-context.cjs','car-knowledge/core.js','car-knowledge/offline-answer.js'].map(f=>[f,digest(path.join(__dirname,f))]))};
fs.writeFileSync(path.join(dir,receipt),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({pass:true,receipt,authentication:report.authentication,api_fallback:false,actual_layers:42,readonly_preview_unchanged:true,identity_conflict:'unresolved'}));
