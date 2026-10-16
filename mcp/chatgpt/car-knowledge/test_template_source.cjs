'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..'),core=require('./core.js'),data=require('./lookup.cjs').load();assert.ok(data);
const arca=data.cars.find(c=>c.id==='stockcars2-arcachevy25'),hash=arca.template_metadata[0].sha256;
let tx={path:'C:/private/generated-preview.tga',fingerprint:'committed-preview-1',generation:1},active='C:/private/ARCA Chevy SS.psd';
const w={Date,document:{getElementById:()=>null},getCurrentSourcePaintFile:()=>active,SPBSourceLoadTransaction:{getCommittedPath:()=>tx.path,getCommittedFingerprint:()=>tx.fingerprint,getGeneration:()=>tx.generation}};w.window=w;vm.createContext(w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'live-identity.js'),'utf8'),w);
const I=w.SpbTemplateIdentity,project={sourcePaintFile:active,sourceFingerprint:{algorithm:'sha256',sha256:hash,size:34691247}},status={requestedPath:active,exists:true,matchesSavedFingerprint:true,legacyUnverified:false,current:{...project.sourceFingerprint}};
assert.equal(I.read().source_reference,null,'Filename alone is not proof');assert.equal(I.sourceVerified(project,status),true);
let observed=I.read();assert.equal(observed.current_file_verified,false);assert.equal(observed.source_reference.sha256,hash);
const result=core.fromContext('What template is this?',null,{template_identity:observed},data);assert.equal(result.resolved,true);assert.equal(result.car.id,arca.id);assert.equal(result.template_match.exact_variant,true);assert.equal(result.template_match.can_target_panels,false);assert.equal(result.identity_evidence.current_file_verified,false);
const broadRecognition=core.fromContext('Explain these Base Paint layers',null,{template_identity:{...observed,recognized_layout:'NASCAR Cup Chevrolet SS (recognised by layout)'}},data);assert.equal(broadRecognition.car.id,arca.id,'Verified original bytes outrank the generic layout recognizer');assert.equal(broadRecognition.identity_conflict,undefined);
const other=core.fromContext('What template is this?',null,{template_identity:{...observed,configured_paint_folder:'ferrari296gt3'}},data);assert.equal(other.identity_conflict,true);assert.equal(other.resolved,false);
const named=core.fromContext('Tell me about the Ferrari 296 GT3 template',null,{template_identity:observed},data);assert.equal(named.car.id,'ferrari296gt3');
const backup=I.captureSession();tx={...tx,generation:2};assert.equal(I.read().source_reference,null,'Same-file reload retires proof');assert.equal(I.restoreSession(backup),true,'Exact rollback may restore original source ancestry');
tx={path:'C:/private/other.tga',fingerprint:'different',generation:3};assert.equal(I.read().source_reference,null);assert.equal(I.restoreSession(backup),false);
tx={...backup.bound,generation:4};active=project.sourcePaintFile;
for(const changed of [{...status,matchesSavedFingerprint:false},{...status,legacyUnverified:true},{...status,current:{...status.current,sha256:'0'.repeat(64)}},{...status,requestedPath:'C:/private/other.psd'}])assert.equal(I.sourceVerified(project,changed),false);
assert.equal(I.sourceVerified(project,status),true);observed=I.read();
const mismatch=core.selectContext('What template is this?',{template_identity:{...observed,source_reference:{...observed.source_reference,sha256:'0'.repeat(64)}}},{template_identity:observed},data);assert.equal(mismatch.identity_conflict,true);assert.equal(mismatch.definite,false);
let tested=0,exact=0,shared=0;
for(const digest of new Set(data.cars.flatMap(c=>c.template_metadata.map(m=>m.sha256)))){
 const picked=core.templateSource([{source_reference:{schema:'spb-template-source/1',sha256:digest}}],data);
 assert.equal(picked.template_match.matched,true);assert.equal(picked.template_match.can_target_panels,false);assert.equal(picked.template_match.uv_geometry_verified,false);assert.equal(picked.identity_evidence.current_file_verified,false);
 tested++;if(picked.definite)exact++;else shared++;
}
// Browser reader uses the same core and returns action-free identity guidance.
w.SpbCarKnowledge=core;w.SpbTemplateIdentity={read:()=>observed};
vm.runInContext(fs.readFileSync(path.join(__dirname,'offline-answer.js'),'utf8'),w);
const list=JSON.parse(fs.readFileSync(path.join(__dirname,'build/cars.json'),'utf8')).articles;w.SpbCarReferenceAnswer.index(list);
const answer=w.SpbCarReferenceAnswer.contextQuestion('What car is my current template for?');assert.ok(answer);assert.match(answer.answer.text,/matches.*SHA256/);assert.equal(answer.answer.actions.length,0);assert.match(answer.answer.text,/UV panel positions remain unverified/);
// Actual native source replacement: new verified ORA, no inspected car match,
// while the app's broad recognition still suggests the Legacy Cup layout.
observed={...observed,source_paint_name:'layered-protection-a.tga',recognized_layout:'NASCAR Cup Chevrolet SS (recognised by layout)',source_reference:{...observed.source_reference,sha256:'4a6363ea51bbfb5f0747c0165d7ea61e0ffa8f1fcd928632143a56d3e455552a',source_name:'layered-protection-a.ora'}};
const unknown=w.SpbCarReferenceAnswer.readOnlyQuestion('Which car is this template for? Do not change anything.');assert.equal(unknown.answer.id,'cars.reading_sheet');assert.match(unknown.answer.text,/hash has no match/);assert.match(unknown.answer.text,/cannot verify the exact car variant/);assert.equal(unknown.answer.actions.length,0);
console.log(JSON.stringify({pass:true,inspected_hashes:tested,unique_exact_variant:exact,shared_or_unverified_variant:shared,lifecycle:'new file, same-file commit, conflict, legacy and rollback',browser_actions:answer.answer.actions.length}));
