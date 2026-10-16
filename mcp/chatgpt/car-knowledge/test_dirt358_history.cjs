'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=require('./lookup.cjs').load(),id='dirtmodified-358-all-variants-2021-wo-o-contingency-update';
const cars=data.cars.filter(c=>c.facts.some(f=>f.id===id));assert.equal(cars.length,1);assert.equal(cars[0].id,'dirtmodified-358');
const f=cars[0].facts.find(f=>f.id===id);assert.equal(f.applicability.variant_exclusive,false);assert.match(f.applicability.source_scope,/ALL Dirt Modified/);assert.ok(f.source_ids.some(s=>s.endsWith('release_2021_s1')));
assert.equal(f.template_revision_verified,false);assert.equal(f.uv_mapping_verified,false);assert.equal(f.can_target_panels,false);
const w={console};w.window=w;vm.createContext(w);for(const n of ['core.js','offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,n),'utf8'),w);
w.SpbCarReferenceAnswer.index(JSON.parse(fs.readFileSync(path.join(__dirname,'build/cars.json'),'utf8')).articles);const api=w.SpbCarReferenceAnswer;
const history=api.readOnlyQuestion('What changed in the Dirt 358 Modified artwork?');assert.ok(history);assert.match(history.answer.text,/World of Outlaws contingency logos/);assert.match(history.answer.text,/2021 Season 3 Patch 2/);assert.match(history.answer.text,/not a 358-exclusive feature/);assert.equal(history.answer.actions.length,0);assert.ok(history.answer.sources.some(s=>/31000161288/.test(s.url)));assert.ok(history.answer.sources.some(s=>/31000158904/.test(s.url)));
const template=api.readOnlyQuestion('What changed in the Dirt 358 Modified template?');assert.ok(template);assert.doesNotMatch(template.answer.text,/World of Outlaws contingency logos/);assert.match(template.answer.text,/No verified template revision history/);
for(const q of ['What changed in the Dirt Big Block Modified artwork?','What changed in the Dirt UMP Modified artwork?']){const other=api.readOnlyQuestion(q);assert.ok(other);assert.doesNotMatch(other.answer.text,/binding the ALL statement to the 358/);}
for(const q of ['What changed in the Dirt 358 Modified artwork? Then paint Body red','Update the Dirt 358 Modified artwork'])assert.equal(api.readOnlyQuestion(q),null);
console.log(JSON.stringify({pass:true,exact_358_facts:1,family_ALL_coverage_explicit:true,no_sibling_promotion:true,artwork_template_separated:true,no_actions_or_UV:true}));
