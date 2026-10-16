'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const K=require('./lookup.cjs'),data=K.load(),root=path.resolve(__dirname,'../../..');
assert.ok(data);
let linked=0;
for(const c of data.cars){
 const guide=K.lookup({car_id:c.id},data).car.template_download;
 assert.equal(guide.car_id,c.id);assert.equal(guide.latest_revision_verified,false);assert.equal(guide.loaded_file_verified,false);assert.equal(guide.can_target_panels,false);
 if(guide.available){linked++;assert.equal(guide.url,c.template.url);assert.equal(guide.checked_at,c.template.http_metadata.checked_at);assert.ok(guide.inspected_documents.length<=5);assert.match(guide.guidance,/old paint\/masks are not proved compatible/);}else assert.equal(guide.url,null);
}
assert.equal(linked,188);
const c=data.cars.find(c=>c.id==='ministock');
for(const template of [{...c.template,url:'https://example.com/other.zip'},{...c.template,url:c.template.url+'?token=x'},{...c.template,http_verified:false},{...c.template,http_metadata:{status:404}}])assert.equal(K.templateDownloadGuide({...c,template}).available,false);
let identity={path:'fixture-a.spbproj',fingerprint:'a',generation:1};
const w={console,setTimeout(){},setInterval(){},SPBSourceLoadTransaction:{getCommittedPath:()=>identity.path,getCommittedFingerprint:()=>identity.fingerprint,getGeneration:()=>identity.generation}};w.window=w;vm.createContext(w);
for(const f of ['js/spb-enc-search.js','js/spb-encyclopedia-data.js','mcp/chatgpt/conversation-scope.js','mcp/chatgpt/car-knowledge/core.js','mcp/chatgpt/car-knowledge/offline-answer.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w,{filename:f});
(async()=>{
 const A=w.SpbOfflineAnswer;await A.load(async file=>{try{return JSON.parse(fs.readFileSync(file==='cars.json'?path.join(__dirname,'build/cars.json'):path.join(root,'data/encyclopedia',file),'utf8'));}catch{return null;}});
 for(const q of ['Where can I download the Mini Stock template?','Where do I get the latest Mini Stock PSD?','What is the newest Mini Stock template?']){
  const r=w.SpbCarReferenceAnswer.readOnlyQuestion(q);assert.ok(r,q);assert.equal(r.answer.reference_car_id,'ministock');assert.equal(r.answer.actions.length,0);assert.match(r.answer.text,/HTTP check 2026-10-09/);assert.match(r.answer.text,/extract it/);assert.match(r.answer.text,/do not certify the latest/);assert.equal(r.answer.sources[0].url,c.template.url);
  const routed=A.route(q,{});assert.equal(routed.cls,'ANSWER',q);assert.equal(routed.answer.template_download.url,c.template.url);assert.equal(routed.answer.actions.length,0);
 }
 const first=w.SpbCarReferenceAnswer.readOnlyQuestion('Where can I download the Mini Stock template?');
 for(const q of ['Where can I get it?','How do I open that template?']){const r=w.SpbCarReferenceAnswer.followup(q,first);assert.ok(r,q);assert.equal(r.answer.reference_car_id,'ministock');assert.equal(r.answer.template_download.url,c.template.url);assert.equal(r.answer.actions.length,0);}
 assert.equal(w.SpbCarReferenceAnswer.followup('Where can I get it? Then repaint the body.',first),null);
 assert.equal(w.SpbCarReferenceAnswer.readOnlyQuestion('Where can I download the BMW M4 template?').answer.template_download,undefined,'An ambiguous family must choose a variant before offering its archive');
 const restricted=w.SpbCarReferenceAnswer.readOnlyQuestion('Where can I download the Mercedes-AMG W12 E Performance template?');assert.ok(restricted);assert.equal(restricted.answer.template_download,undefined);assert.match(restricted.answer.text,/custom|locked|sponsor/i);
 const history=w.SpbCarReferenceAnswer.readOnlyQuestion('What changed in the Dallara IR18 template?');assert.ok(history);assert.equal(history.answer.template_download,undefined);assert.match(history.answer.text,/2026/);
 identity={path:'fixture-b.spbproj',fingerprint:'b',generation:2};w.SpbConversationScope.sourceCommitted();assert.equal(w.SpbCarReferenceAnswer.followup('Where can I get it?',first),null,'A document switch cannot borrow the old download target');
 console.log(JSON.stringify({pass:true,exact_official_links:linked,shared_online_offline_guide:true,natural_followups:true,document_switch_invalidates:true,restrictions_and_history_preserved:true,no_actions:true}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
