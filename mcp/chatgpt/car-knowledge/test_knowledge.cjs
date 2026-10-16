'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const K=require('./lookup.cjs'),data=JSON.parse(fs.readFileSync(path.join(__dirname,'build/knowledge.json'),'utf8'));
const checks=[];
function test(name,fn){fn();checks.push(name);console.log('PASS '+name);}
test('Every canonical ID resolves; a shared paint folder preserves the variant choice',()=>{
  for(const c of data.cars){
    assert.equal(K.lookup({car_id:c.id},data).car.id,c.id);
    if(c.paint_folder){
      const r=K.lookup({paint_folder:c.paint_folder},data),siblings=data.cars.filter(x=>K.norm(x.paint_folder)===K.norm(c.paint_folder));
      if(siblings.length===1)assert.equal(r.car.id,c.id);
      else{assert.equal(r.resolved,false);assert.ok(r.candidates.some(x=>x.id===c.id));}
    }
  }
});
test('Unknown IDs never fall through to a guessed car',()=>{
  const r=K.lookup({car_id:'not-a-car',query:'Dallara IR18'},data);
  assert.equal(r.resolved,false);assert.equal(r.candidates.length,0);
});
test('Gen4 standard and superspeedway metadata stay attached to their exact variants',()=>{
  for(const model of ['chevymontecarlo03','fordtaurus03']){
    const standard=K.lookup({car_id:'stockcars-'+model},data).car;
    const ss=K.lookup({car_id:'stockcars-'+model+'-superspeedway'},data).car;
    assert.ok(standard.template_metadata.length);assert.ok(ss.template_metadata.length);
    assert.ok(standard.template_metadata.every(m=>!/ SS\.psd$/i.test(m.file)));
    assert.ok(ss.template_metadata.every(m=>/ SS\.psd$/i.test(m.file)));
  }
});
test('Multiple explicit models and partial model families require a choice',()=>{
  for(const query of ['BMW M4','Dallara IR18 or Aston Martin Valkyrie AMR-LMH']){
    const r=K.lookup({query},data);assert.equal(r.resolved,false,query);assert.ok(r.candidates.length>=2,query);
  }
});
test('An ambiguous question does not silently select the current car',()=>{
  const r=K.fromContext('BMW M4',{car:'Dallara IR18'},null,data);
  assert.equal(r.resolved,false);assert.ok(r.candidates.length>=2);
});
test('Explicit model questions resolve; current recognition is a separate evidence source',()=>{
  assert.equal(K.lookup({query:'What changed in the Dallara IR18 template?'},data).car.id,'dallarair18');
  const r=K.fromContext('Can you explain this scheme?',{car:'Dallara IR18'},null,data);
  assert.equal(r.car.id,'dallarair18');assert.match(r.identity_source,/live app recognition/);
});
test('Every fact cites existing source data; metadata never grants geometry or edit permission',()=>{
  for(const c of data.cars){
    assert.equal(c.can_target_panels,false);
    for(const f of c.facts){assert.ok(f.text && f.source_ids.length);for(const id of f.source_ids)assert.ok(data.sources[id]);}
    for(const m of c.template_metadata){assert.equal(m.uv_mapping_verified,false);assert.ok(m.width>0&&m.height>0);assert.ok(!('bbox' in m));}
    assert.ok(c.unknowns.length>=2);
    for(const r of c.local_layout_references){assert.equal(r.current_file_verified,false);if(r.guess)assert.equal(r.evidence_level,'local-draft');}
  }
});
test('One-car packets remain bounded and contain source links',()=>{
  for(const c of data.cars){const r=K.lookup({car_id:c.id},data);assert.ok(JSON.stringify(r).length<32000,c.id);assert.ok(Object.keys(r.car.sources).length);}
});
test('Bad arguments rejected, including oversized or nontext values',()=>{
  for(const args of [{query:'x'.repeat(1001)},{car_id:1},{paint_folder:{} }])assert.throws(()=>K.lookup(args,data));
});
const root=path.resolve(__dirname,'../../..'),w={console,setTimeout(){},setInterval(){}};w.window=w;vm.createContext(w);
vm.runInContext(fs.readFileSync(path.join(root,'js/spb-enc-search.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(root,'js/spb-encyclopedia-data.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'core.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'offline-answer.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../candidates/spb-offline-answer.js'),'utf8'),w);
const A=w.SpbOfflineAnswer;
(async()=>{
  await A.load(async file=>{try{return JSON.parse(fs.readFileSync(file==='cars.json'?path.join(__dirname,'build/cars.json'):path.join(root,'data/encyclopedia',file),'utf8'));}catch{return null;}});
  const queries=[['What changed in the Dallara IR18 template?','dallarair18'],['What template does the Aston Martin Valkyrie AMR-LMH use?','amvalkyriegtp'],['Can I add sponsors to the Mercedes-AMG W12 E Performance?','mercedesw12']];
  const evidence=[];
  for(const [query,id] of queries){
    const hits=A.search(query,3),top=hits[0];
    assert.equal(top.id,'cars.reference.'+id,query);
    const answer=A.answerOf(top,query);
    assert.equal(answer.actions.length,0,'Reference advice must not create a paint action');
    if(id==='dallarair18')assert.match(JSON.stringify(answer),/2026 S1|2026 Season 1/,'A change-history question needs actual changes, not just a filename');
    evidence.push({query,top:top.id,score:top.score,cov:top.cov,answer});
  }
  console.log('PASS Offline Helper ranks exact model questions to the shared evidence, with no paint action');
  const successor=JSON.parse(fs.readFileSync(path.join(__dirname,'research/road_successor/runtime_facts.json'),'utf8')).facts;
  for(const fact of successor){
    const car=data.cars.find(c=>c.id===fact.car_ids[0]),query='What is unusual about the '+car.name+' template?';
    const top=A.search(query,3)[0];assert.equal(top.id,'cars.reference.'+car.id);
    const answer=A.answerOf(top,query);assert.equal(answer.actions.length,0);
    assert.ok(JSON.stringify(answer).includes(fact.text),'Offline answer must actually deliver the new qualified metadata: '+car.id);
  }
  const gapQuery='What is unusual about the Formula Renault 3.5 template?';
  const gap=A.answerOf(A.search(gapQuery,3)[0],gapQuery);
  assert.match(gap.text,/Color Change Logos.*visible group/);
  assert.match(gap.text,/Base with a trailing space/);
  assert.match(gap.text,/latest simulator availability remain unverified/);
  assert.equal(gap.actions.length,0);
  assert.ok(gap.sources.some(s=>/Formula Renault 3\.5 official template/.test(s.label)));
  const frRevisionQuery='What changed in the Formula Renault 3.5 template?';
  const frRevision=A.answerOf(A.search(frRevisionQuery,3)[0],frRevisionQuery);
  assert.match(frRevision.text,/No verified template revision history/);
  const revisionQuery='What changed in the Kia Optima template?';
  const revision=A.answerOf(A.search(revisionQuery,3)[0],revisionQuery);
  assert.match(revision.text,/No verified template revision history/);
  assert.doesNotMatch(revision.text,/extends beyond/,'Observed layer structure must not masquerade as revision history');
  console.log('PASS seven metadata observations reach actual Offline answers with their limitations and no actions');
  for(const query of ["What changed in the Legends Ford '34 Coupe - Rookie template recently?", "What dimensions is the Legends Ford '34 Coupe - Rookie template?"]){
    const top=A.search(query,3)[0];assert.equal(top.id,'cars.reference.legends-ford34c-rookie');
    const answer=A.answerOf(top,query);
    assert.match(answer.text,/retired from painting/i);
    assert.doesNotMatch(answer.text,/its current official template|before changing that area/i);
    assert.match(answer.text,/does not establish matching paint files or UVs/);
    assert.equal(answer.actions.length,0);assert.ok(answer.sources.length);
    evidence.push({query,id:top.id,answer});
  }
  console.log('PASS retired historical-detail answers do not suggest a current painting workflow');
  fs.writeFileSync(path.join(__dirname,'build/lookup-verification.json'),JSON.stringify({checks,offline:evidence,coverage:data.coverage},null,2)+'\n');
})().catch(e=>{console.error(e);process.exitCode=1});
