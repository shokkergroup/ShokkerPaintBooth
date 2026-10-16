'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),K=require('./lookup.cjs');
const data=K.load(),factId='ministock-2024-s4-p2-rear-sponsor-artwork-history';assert.ok(data);
const asphalt=K.lookup({car_id:'ministock'},data).car,dirt=K.lookup({car_id:'dirtministock'},data).car;
const fact=asphalt.facts.find(f=>f.id===factId);assert.ok(fact);assert.equal(fact.topic,'paint-artwork-history');assert.equal(fact.release.year,2024);assert.equal(fact.template_revision_verified,false);assert.equal(fact.can_target_panels,false);assert.match(fact.text,/not Dirt Mini Stock/);assert.match(fact.text,/does not establish current/);assert.ok(!dirt.facts.some(f=>f.id===factId));
for(const id of fact.source_ids)assert.ok(asphalt.sources[id]?.url.startsWith('https://support.iracing.com/'));
const root=path.resolve(__dirname,'../../..'),w={console,setTimeout(){},setInterval(){}};w.window=w;vm.createContext(w);
for(const f of ['js/spb-enc-search.js','js/spb-encyclopedia-data.js','mcp/chatgpt/car-knowledge/core.js','mcp/chatgpt/car-knowledge/offline-answer.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w);
(async()=>{
 const A=w.SpbOfflineAnswer;await A.load(async file=>{try{return JSON.parse(fs.readFileSync(file==='cars.json'?path.join(__dirname,'build/cars.json'):path.join(root,'data/encyclopedia',file),'utf8'));}catch{return null;}});
 const history=A.route('What changed in the Mini Stock rear sponsor artwork?',{});assert.equal(history.cls,'ANSWER');assert.match(history.answer.text,/2024 Season 4 Patch 2/);assert.match(history.answer.text,/rear-sponsor/);assert.match(history.answer.text,/not Dirt Mini Stock/);assert.equal(history.answer.actions.length,0);
 const revision=A.route('What changed in the Mini Stock PSD template?',{});assert.equal(revision.cls,'ANSWER');assert.match(revision.answer.text,/No verified template revision history/);assert.doesNotMatch(revision.answer.text,/rear-sponsor artwork|rear-sponsor placement/);
 const current=A.route('Where can I get the newest Mini Stock template?',{});assert.equal(current.answer.template_download.latest_revision_verified,false);assert.match(current.answer.text,/do not certify the latest/);
 console.log(JSON.stringify({pass:true,exact_asphalt_history:true,dirt_excluded:true,history_not_psd_revision:true,latest_unverified:true,no_actions:true}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
