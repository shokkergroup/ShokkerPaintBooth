'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=require('./lookup.cjs').load(),id='dirtlatemodel-350-all-family-2019-woo-decal-history';
const cars=data.cars.filter(c=>c.facts.some(f=>f.id===id));assert.equal(cars.length,1);assert.equal(cars[0].id,'dirtlatemodel-350');
const f=cars[0].facts.find(f=>f.id===id);assert.equal(f.applicability.variant_exclusive,false);assert.match(f.applicability.source_scope,/ALL Dirt Late Model/);assert.equal(f.template_revision_verified,false);assert.equal(f.can_target_panels,false);assert.equal(f.uv_mapping_verified,false);
const w={console};w.window=w;vm.createContext(w);for(const n of ['core.js','offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,n),'utf8'),w);
w.SpbCarReferenceAnswer.index(JSON.parse(fs.readFileSync(path.join(__dirname,'build/cars.json'),'utf8')).articles);const api=w.SpbCarReferenceAnswer;
const h=api.readOnlyQuestion('What changed in the Dirt Late Model Limited artwork?');assert.ok(h);assert.match(h.answer.text,/passenger-side WOO decal/i);assert.match(h.answer.text,/2019 Season 2 Patch 2/);assert.match(h.answer.text,/not a Limited-exclusive/);assert.match(h.answer.text,/no exact printed patch event date/);assert.match(h.answer.text,/not a current instruction/);assert.equal(h.answer.actions.length,0);assert.ok(h.answer.sources.some(s=>/2019-Season-2-Patch-2.pdf$/.test(s.url)));
const t=api.readOnlyQuestion('What changed in the Dirt Late Model Limited template?');assert.ok(t);assert.doesNotMatch(t.answer.text,/passenger-side WOO decal/i);assert.match(t.answer.text,/No verified template revision history/);
for(const q of ['What changed in the Dirt Late Model Pro artwork?','What changed in the Dirt Late Model Super artwork?']){const other=api.readOnlyQuestion(q);assert.ok(other);assert.doesNotMatch(other.answer.text,/not a Limited-exclusive/);}
for(const q of ['What changed in the Dirt Late Model Limited artwork? Then move the logo upward','Move the Dirt Late Model Limited WOO decal'])assert.equal(api.readOnlyQuestion(q),null);
console.log(JSON.stringify({pass:true,exact_limited_history:1,family_scope_and_filename_date_limits:true,no_sibling_promotion:true,no_current_placement_action_or_UV:true}));
