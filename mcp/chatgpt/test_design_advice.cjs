'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const I=require('./design-intent.js'),root=path.resolve(__dirname,'../..');
const question='Would matte black and satin gold work here while keeping blue, white marks, and no glitter? Advice only.';
for(const q of [question,'Would satin gold look better?','Compare matte versus satin; do not apply it.','Just brainstorm a blue livery.'])assert.equal(I.classify(q).mutation_allowed,false,q);
for(const q of ['Make the body black, keep white numbers.','Paint the body blue; don\'t paint the numbers.','Would gold look better? Then paint the hood gold.','Use the second option.','How do I save my project?'])assert.equal(I.classify(q).mode,'unspecified',q);
const optionsQuestion='Give me two understated black and gold directions. No glitter; keep my numbers and sponsors.';
for(const q of [optionsQuestion,'Suggest three red and white concepts.','Show me blue and silver palette options.'])assert.equal(I.classify(q).mutation_allowed,false,q);
for(const q of ['Show me two black and gold options, then paint the hood gold.','Could you make the body blue?','Could you make the second one gold?'])assert.equal(I.classify(q).mode,'unspecified',q);
const proposed=I.answer(optionsQuestion);
const dirty=JSON.parse(JSON.stringify(proposed));dirty.answer.design_proposals.queue=[{paint:'all'}];dirty.answer.design_proposals.items[0].target_id='old-layer';dirty.answer.design_proposals.approved=true;
assert.deepEqual(I.discussion(dirty),I.discussion(proposed),'Only descriptive option fields may persist or cross contexts');
assert.equal(proposed.answer.design_proposals.items.length,2);
assert.deepEqual(proposed.answer.design_proposals.constraints,{no_glitter:true,protected_artwork:['numbers','sponsors']});
assert.equal(I.discussion(proposed).executable,false);
assert.equal(I.answer('Could you make the second one gold?',proposed),null,'A polite edit must not be swallowed as explanation');
assert.equal(I.answer('Why would the second suit this car?'),null,'No remembered proposal may be invented');
assert.equal(I.answer('Why would the second suit this car? Then paint the hood gold.',proposed),null,'Mixed instructions reach the full planner');
let network=0,edits=0,generation=1;
const w={console,Promise,Set,Map,Date,Uint8Array,AbortController,
 setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},
 localStorage:{getItem:()=>null,setItem(){}},
 document:{readyState:'loading',addEventListener(){},getElementById:()=>null},
 SpbAI:{cached:()=>({configured:false})},SpbTellNLU:{buildIndex:()=>({})},
 SpbProZone:{SCHEMA:{},zonesForModel:()=>[],paintColours:()=>[]},
 zones:[],selectedZoneIndex:-1,MAX_ZONES:40,
 SPBSourceLoadTransaction:{getCommittedPath:()=> 'C:/test/arca.psd',getCommittedFingerprint:()=> 'source-a',getGeneration:()=>generation},
 fetch(){network++;throw Error('Advice must not use the model or mutate paint');},
 SpbProEdit:{plan(){edits++;throw Error('Advice entered edit parser');}}};
w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/design-intent.js','mcp/chatgpt/candidates/spb-pro-ai.js','mcp/chatgpt/candidates/spb-offline-builder.js','mcp/chatgpt/design-brief.js','js/spb-enc-search.js','js/spb-encyclopedia-data.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w);
(async()=>{
 await w.SpbOfflineAnswer.load(async name=>{try{return JSON.parse(fs.readFileSync(path.join(root,'data/encyclopedia',name),'utf8'));}catch{return null;}});
 const B=w.SpbOfflineBuilder,O=w.SpbOfflineAnswer;
 B.markTyped(question,'typed');const claimed=O.claim(question);
 assert.ok(claimed);assert.equal(claimed.queue.length,0);assert.match(claimed.text,/Design advice/);
 const routed=O.route(question,{});assert.equal(routed.via,'design-advice');assert.equal(routed.answer.actions.length,0);assert.ok(!O.cardHtml(routed).includes('data-ob="adoit"'));
 B.state().steps=[{what:'old-step'}];B.state().ran={old:true};
 await w.spbProAI.send(question);
 assert.equal(B.state().steps.length,0,'The advice card must remove old editing steps from its dock');
 assert.equal(B.state().ran,null);assert.equal(B.state().answer.via,'design-advice');
 const log=w.spbProAI.log();assert.match(log.at(-1).text,/Nothing has been changed or queued/);assert.match(B.state().answer.answer.text,/softer sheen/);assert.match(B.state().answer.answer.text,/no-glitter/);assert.match(B.state().answer.answer.text,/not a visual assessment/);
 assert.equal(network,0);assert.equal(edits,0);
 await w.spbProAI.send(optionsQuestion);
 assert.equal(B.state().steps.length,0,'A request for alternatives must never queue a repaint');
 assert.equal(B.state().answer.answer.design_proposals.items.length,2);
 const offered=JSON.parse(JSON.stringify(B.state().answer.answer.design_proposals));
 await w.spbProAI.send('Why would the second suit this car?');
 assert.match(B.state().answer.answer.text,/Option 2 — Soft black base, muted gold panels/);
 assert.match(B.state().answer.answer.text,/no-glitter/);
 assert.match(B.state().answer.answer.text,/numbers, sponsors/);
 assert.deepEqual(JSON.parse(JSON.stringify(B.state().answer.answer.design_proposals)),offered,'The follow-up retains the actual two options and original constraints');
 assert.equal(B.state().steps.length,0);assert.equal(network,0);assert.equal(edits,0);
 const saved=JSON.parse(JSON.stringify(w.SpbDesignBrief.capture('options-project')));
 assert.deepEqual(saved.turns.at(-1).design_proposals,offered,'Actual Full Editor assistant entry saves the displayed proposals, not only its card announcement');
 B._sourceChanged();
 assert.equal(I.discussion(B.state().answer),null,'Changing the project retires the displayed proposals');
 generation++;w.SpbDesignBrief.sourceCommitted();
 assert.equal(w.SpbDesignBrief.explain('Why would the second suit this car?'),null);
 assert.equal(w.SpbDesignBrief.restore(saved,'options-project',true),true);
 await w.spbProAI.send('Why would the second suit this car?');
 assert.match(B.state().answer.answer.text,/From your saved discussion/);
 assert.match(B.state().answer.answer.text,/Option 2 — Soft black base, muted gold panels/);
 assert.match(B.state().answer.answer.text,/no-glitter/);
 assert.match(B.state().answer.answer.text,/numbers, sponsors/);
 assert.equal(I.discussion(B.state().answer),null,'Historical explanation must not resurrect live option state');
 assert.equal(w.SpbDesignBrief.explain('Use the second option'),null);
 assert.equal(w.SpbDesignBrief.explain('Could you make the second one gold?'),null);
 assert.equal(B.state().steps.length,0);assert.equal(network,0);assert.equal(edits,0);
 w.SpbDesignBrief.forget();B._sourceChanged();assert.equal(w.SpbDesignBrief.explain('Why would the second suit this car?'),null);
 console.log('PASS: shared intent, mixed question/command, protected-part commands, actual Offline claim and Full Editor send, stale step clearing; zero network/edit calls');
 console.log('PASS: actual Full Editor options-to-explanation conversation retains proposals/protected art/no-glitter, queues no edit, and retires on source change');
 console.log('PASS: actual Full Editor entries persist exact descriptive options; verified restore supports historical explanation with constraints and no live targets; Forget removes recall');
})().catch(e=>{console.error(e);process.exitCode=1;});
