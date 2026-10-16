'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'design-brief.js'),'utf8');
let source={path:'C:/paints/a.psd',fingerprint:'hash-a',generation:1},messages=[],actions=0;
const w={console,Set,Map,Date,Uint8Array,document:{getElementById:id=>id==='paintCanvas'?{width:2,height:2}:null},
 spbProAI:{log:()=>messages.slice()},crypto:{randomUUID:()=> 'saved-project-id'},
 SPBSourceLoadTransaction:{getCommittedPath:()=>source.path,getCommittedFingerprint:()=>source.fingerprint,getGeneration:()=>source.generation},
 getCurrentSourcePaintFile:()=>source.path,getConfig:()=>({sourcePaintFile:source.path,zones:[]}),
 _psdLayers:[],_selectedLayerId:null,_selectedLayerIds:new Set(),_settleActiveLayerStrokeBeforeTargetChange(){},
 fetch(){throw Error('No network or tool actions should run in this test');},execute(){actions++;}};
w.window=w;vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(__dirname,'design-intent.js'),'utf8'),w);vm.runInContext(code,w);
const B=w.SpbDesignBrief;
messages.push({role:'user',text:'Keep blue and sponsors. No glitter.'},{role:'ai',text:'Two directions: pearl or satin gold.',options:[{name:'Understated pearl',queue:[{write:'not saved'}]},{name:'Satin gold'}],undo_id:'old-undo'},{role:'picture',src:'private-image-data'},{role:'user',text:'Discuss the second option, but do not apply it.'});
const structured=w.SpbDesignIntent.answer('Give me two blue and gold directions. No glitter; keep numbers and sponsors.').answer.design_proposals;
messages[1].design_proposals={...structured,queue:[{write:'not saved'}],target_id:'old-target',approved:true};
const brief=B.capture('project-a');
assert.equal(brief.turns.length,3);assert.match(brief.turns[1].text,/Proposal 2: Satin gold/);
assert.equal(brief.turns[1].design_proposals.items[1].id,'soft-contrast');assert.ok(!JSON.stringify(brief).includes('old-target'));
assert.ok(!JSON.stringify(brief).includes('old-undo'));assert.ok(!JSON.stringify(brief).includes('private-image-data'));assert.ok(!JSON.stringify(brief).includes('not saved'));
source={path:'C:/paints/b.psd',fingerprint:'hash-b',generation:2};B.sourceCommitted();
assert.equal(B.view().available,false);assert.equal(B.capture('project-b'),null);
assert.equal(B.restore(brief,'project-b',true),false);assert.equal(B.restore(brief,'project-a',false),false);
source={path:'C:/paints/a.psd',fingerprint:'hash-a',generation:3};B.sourceCommitted();
assert.equal(B.restore(JSON.parse(JSON.stringify(brief)),'project-a',true),true);
assert.equal(B.view().historical,true);assert.match(B.recall('What did we discuss in my saved design brief?').text,/No glitter/);
assert.equal(B.recall('Make the hood gold'),null);assert.equal(B.recall('Would satin look better?'),null);
assert.equal(B.capture('save-as-new-id').project_id,'save-as-new-id');
const session=B.captureSession();
source.generation++;B.observe(); // A started/failed load has not committed another source.
assert.equal(B.view().available,true);
source={path:'C:/paints/b.psd',fingerprint:'hash-b',generation:5};B.sourceCommitted();
assert.equal(B.view().available,false);
source={path:'C:/paints/a.psd',fingerprint:'hash-a',generation:6};B.restoreSession(session);
assert.equal(B.view().available,true);assert.match(B.view().turns[0].text,/Keep blue/);
source.generation++;B.sourceCommitted();assert.equal(B.view().available,false,'Successful reopening clears old discussion until a verified project restores its own');
B.restore(brief,'project-a',true);B.forget();assert.equal(B.capture('project-a'),null);
assert.equal(B.restore({...brief,turns:Array(1000).fill({role:'user',text:'oversized'})},'project-a',true),false);
messages.push({role:'user',text:'Preserve my first colour instruction.'});
for(let i=0;i<80;i++)messages.push({role:'ai',text:'Proposal '+i+' '+ 'x'.repeat(2000)});
messages.push({role:'user',text:'Latest correction: keep red instead of blue.'});
const long=B.capture('long-project');assert.ok(long.omitted_turns>0);assert.ok(long.turns.length<=60);assert.ok(long.turns.reduce((n,r)=>n+r.text.length,0)<=24000);assert.match(long.turns.at(-1).text,/Latest correction/);
const structuredRows=Array.from({length:60},()=>({role:'assistant',text:'Design options',design_proposals:structured}));
B.restore({schema:'spb-design-brief/1',project_id:'bounded-options',turns:structuredRows},'bounded-options',true);
const small=B.view();assert.ok(small.omitted_turns>0);assert.ok(small.turns.reduce((n,r)=>n+r.text.length+(r.design_proposals?JSON.stringify(r.design_proposals).length:0),0)<=8000,'Structured descriptions count toward the context budget');
B.restore(long,'long-project',true);assert.match(B.view().turns.at(-1).text,/Latest correction/);
w.SPB_DESIGN_BRIEF_OFF=true;assert.equal(B.capture('disabled'),null);assert.equal(B.recall('What is my saved design brief?'),null);source.generation++;B.sourceCommitted();w.SPB_DESIGN_BRIEF_OFF=false;
assert.equal(B.view().available,false,'Re-enabling after another source commit cannot revive old notes');B.restore(long,'long-project',true);

// Exercise the actual staged project serializer, not a mirrored implementation.
const projectSource=fs.readFileSync(path.join(__dirname,'candidates/spb-projects.js'),'utf8');
vm.runInContext(projectSource.replace('window.SPBProjects = Object.freeze({','window.SPBProjects = Object.freeze({_testCapture: _captureProjectOpenState, _testRestore: _restoreProjectOpenState,'),w);
const payload=w.SPBProjects.buildProjectPayload('Brief round trip');
assert.equal(payload.projectId,'saved-project-id');assert.equal(payload.assistantBrief.project_id,payload.projectId);
const reopened=JSON.parse(JSON.stringify(payload));
assert.equal(B.restore(reopened.assistantBrief,reopened.projectId,true),true);
assert.match(B.view().turns.at(-1).text,/Latest correction/);assert.equal(actions,0);
B.restore(brief,'project-a',true);
const optionsPayload=JSON.parse(JSON.stringify(w.SPBProjects.buildProjectPayload('Saved directions')));
assert.deepEqual(optionsPayload.assistantBrief.turns[1].design_proposals,JSON.parse(JSON.stringify(structured)));
assert.equal(B.restore(optionsPayload.assistantBrief,optionsPayload.projectId,true),true);
assert.match(B.recall('What did we discuss in my saved brief?').text,/2\. Soft blue base, muted gold panels/);
assert.equal(B.explain('Use the second option'),null);
B.restore(reopened.assistantBrief,reopened.projectId,true);
w.SPBSourceLoadTransaction.captureDocumentState=()=>({source:{...source}});
w.SPBSourceLoadTransaction.restoreDocumentState=snapshot=>{source={...snapshot.source,generation:source.generation+1};B.sourceCommitted();};
w.loadConfigFromObj=()=>{};
const projectSession=w.SPBProjects._testCapture();assert.equal(projectSession.ok,true);
source={path:'C:/paints/b.psd',fingerprint:'hash-b',generation:12};B.sourceCommitted();
assert.equal(w.SPBProjects._testRestore(projectSession).ok,true);assert.equal(B.view().available,true);
source={path:'C:/paints/b.psd',fingerprint:'hash-b',generation:14};B.sourceCommitted();
w.SPBSourceLoadTransaction.restoreDocumentState=()=>{throw Error('rollback unavailable');};
assert.equal(w.SPBProjects._testRestore(projectSession).ok,false);assert.equal(B.view().available,false,'Failed document rollback must never attach A discussion to B');
source={path:'C:/paints/a.psd',fingerprint:'hash-a',generation:15};B.restore(reopened.assistantBrief,reopened.projectId,true);

// Run the real source-result boundary; failed source loads must not clear notes.
const canvas=fs.readFileSync(path.join(__dirname,'candidates/paint-booth-3-canvas.js'),'utf8');
const begin=canvas.indexOf('        function _spbSourceLoadResult('),end=canvas.indexOf('        async function _spbFingerprintBytes(',begin);
assert.ok(begin>=0&&end>begin);
w._spbSourceLoadGeneration=source.generation;w._spbCommittedSourcePath=source.path;w._spbCommittedSourceFingerprint=source.fingerprint;w._psdPath='';
vm.runInContext(canvas.slice(begin,end),w);
source.generation++;w._spbSourceLoadGeneration=source.generation;
w._spbSourceLoadResult(null,false,{error:'read failed'});assert.equal(B.view().available,true);
w._spbSourceLoadResult(null,true,{});assert.equal(B.view().available,false);
console.log('PASS saved discussion: source/project isolation, verified reopen, failure rollback, bounded first/latest quotes, forgotten notes, disabled mode, actual project serializer and source commit hooks; zero actions');
const root=path.resolve(__dirname,'../..');
w.setTimeout=()=>{};w.setInterval=()=>{};w.clearTimeout=()=>{};
for(const file of ['js/spb-enc-search.js','js/spb-encyclopedia-data.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w);
(async()=>{
 await w.SpbOfflineAnswer.load(async name=>{try{return JSON.parse(fs.readFileSync(path.join(root,'data/encyclopedia',name),'utf8'));}catch{return null;}});
 B.restore(brief,'project-a',true);
 const answer=w.SpbOfflineAnswer.route('What did we agree on in my saved brief?',{});
 assert.equal(answer.cls,'ANSWER');assert.match(answer.answer.text,/Keep blue and sponsors/);assert.match(answer.answer.text,/Proposal 2: Satin gold/);assert.match(answer.answer.text,/not approval/);assert.equal(answer.answer.actions.length,0);
 assert.equal(answer.answer.project_discussion,true);assert.ok(!w.SpbOfflineAnswer.cardHtml(answer).includes('data-ob="aread"'),'Saved quotes must not link to an unrelated car article');
 vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates/spb-offline-builder.js'),'utf8'),w);
 w.SpbOfflineBuilder.markTyped('What did we discuss in my saved design brief?','saved-discussion');
 const claimed=w.SpbOfflineAnswer.claim('What did we discuss in my saved design brief?');
 assert.ok(claimed,'The actual front door must claim recall after its input marker');assert.match(claimed.text,/Saved design discussion/);assert.equal(claimed.queue.length,0);
 B.forget();const empty=w.SpbOfflineAnswer.route('What did we discuss in the saved brief?',{});
 assert.match(empty.answer.text,/no saved design discussion/);assert.equal(empty.answer.actions.length,0);
 console.log('PASS actual Offline route recalls saved buyer quotes and proposals, reports missing notes and creates no actions');
})().catch(e=>{console.error(e);process.exitCode=1;});
