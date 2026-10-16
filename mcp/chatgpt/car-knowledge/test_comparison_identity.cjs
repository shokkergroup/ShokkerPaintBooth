'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const K=require('./lookup.cjs'),data=K.load(),raw=JSON.stringify(data),articles=require('./build/cars.json').articles;
const ids=r=>r.matches.map(c=>c.id),query='Do Mini Stock and Dirt Mini Stock share the same template?';
for(const q of [query,'Mini Stock vs Dirt Mini Stock template','Compare Mini Stock with Dirt Mini Stock templates','What is the difference between Mini Stock and Dirt Mini Stock templates?','Can I copy Mini Stock masks to Dirt Mini Stock?']){
 const r=K.select(data,{query:q});assert.deepEqual(ids(r),['ministock','dirtministock'],q);assert.equal(r.definite,false);assert.equal(r.comparison.complete,true);
}
const gen4=K.select(data,{query:'Compare Gen 4 Ford Taurus - 2003 and Gen 4 Ford Taurus - 2003 SS templates'});
assert.deepEqual(ids(gen4),['stockcars-fordtaurus03','stockcars-fordtaurus03-superspeedway']);assert.equal(gen4.comparison.complete,true);
const bmw=K.select(data,{query:'Compare BMW M4 F82 GT4 - 2018 and BMW M4 G82 GT4 Evo templates'});
assert.deepEqual(ids(bmw),['bmwm4gt4','bmwm4evogt4']);assert.equal(bmw.comparison.complete,true);
const ambiguous=K.select(data,{query:'Compare BMW M4 GT4 and BMW M4 G82 GT4 Evo templates'});
assert.equal(ambiguous.comparison.complete,false);assert.equal(ambiguous.comparison.mentions[0].resolved,false);
const unknown=K.fromContext('Are Mini Stock and Ferrari F999 templates the same?',{car:'Dallara IR18'},{template_identity:{configured_paint_folder:'stockcars2 arcachevy25'}},data);
assert.equal(unknown.resolved,false);assert.equal(unknown.comparison.complete,false);assert.deepEqual(unknown.candidates.map(c=>c.id),['ministock']);assert.ok(!JSON.stringify(unknown.comparison).includes('dallarair18'));
const modifier=K.select(data,{query:'Mini Stock vs Dirt Mazda MX5 template'});assert.equal(modifier.comparison.complete,false);assert.equal(modifier.comparison.mentions[1].reason,'unsupported-variant-modifier');
const negated=K.select(data,{query:'Not Mini Stock vs Dirt Mini Stock template'});assert.equal(negated.comparison.complete,false);assert.ok(!ids(negated).includes('ministock'));
for(const q of ['Compare matte vs gloss on Mini Stock','What is the difference between metallic and roughness in Mini Stock template?']){
 const r=K.select(data,{query:q});assert.equal(r.comparison,undefined,q);assert.deepEqual(ids(r),['ministock']);
}
const same=K.select(data,{query:'Mini Stock vs ministock template'});assert.equal(same.comparison.complete,true);assert.deepEqual(ids(same),['ministock']);
assert.equal(K.select(data,{query,car_id:'dallarair18'}).comparison,undefined,'Explicit ID contract unchanged');
const packet=K.lookup({query},data);assert.equal(packet.resolved,false);assert.equal(packet.comparison.complete,true);
assert.deepEqual(packet.comparison.references.map(c=>c.id),['ministock','dirtministock']);
assert.ok(packet.comparison.references.every(c=>!c.can_target_panels&&!c.compatibility_verified&&!c.loaded_file_verified&&!c.template.latest_revision_verified));
assert.ok(JSON.stringify(packet.comparison).length<15000);
assert.equal(JSON.stringify(data),raw,'Read-only shared reference');
const w={console};w.window=w;vm.createContext(w);
for(const f of ['core.js','offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,f),'utf8'),w,{filename:f});
w.SpbCarReferenceAnswer.index(articles);w.SpbTemplateIdentity={read:()=>({configured_paint_folder:'stockcars2 arcachevy25'})};
for(const q of [query,'Compare Mini Stock with Dirt Mini Stock templates']){
 const r=w.SpbCarReferenceAnswer.readOnlyQuestion(q);assert.ok(r,q);assert.equal(r.answer.title,'Compare template variants');
 assert.match(r.answer.text,/Mini Stock:/);assert.match(r.answer.text,/Dirt Mini Stock:/);assert.match(r.answer.text,/compatibility is unverified/);assert.equal(r.answer.actions.length,0);assert.equal(r.answer.reference_car_id,undefined,'Comparison cannot seed a one-car pronoun context');
}
for(const q of ['Are Mini Stock and Ferrari F999 templates the same?','Compare BMW M4 GT4 and BMW M4 G82 GT4 Evo templates','Mini Stock vs Dirt Mazda MX5 template?']){
 const named=K.select(data,{query:q}),a=articles.find(a=>a.car_reference?.id===named.matches[0].id),r=w.SpbCarReferenceAnswer.answer(a,q);
 assert.equal(r.title,'Confirm comparison identities');assert.match(r.text,/exact car\/version for each side/);assert.equal(r.actions.length,0);
}
assert.equal(w.SpbCarReferenceAnswer.readOnlyQuestion('Compare Mini Stock and Dirt Mini Stock templates and paint Body red'),null,'Mixed edit stays outside read-only route');
console.log(JSON.stringify({pass:true,independent_comparison_mentions:true,shared_lookup_and_context:true,offline_actual_reader:true,ambiguity_unknown_negation_modifier_guards:true,read_only:true,paint_actions:0}));
