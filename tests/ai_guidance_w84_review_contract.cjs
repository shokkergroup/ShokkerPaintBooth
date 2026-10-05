'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const oraclePath='_easy_claude_work/ai14h_w84_guidance_fresh_oracle.json';
const controllerPath='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-pro-ai.js';
const helperPath='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-self-help.js';
const knowledgePath='_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/js/spb-ai-knowledge.js';
const pins={
  [oraclePath]:'f9ee48e767fc6d2808fa0c9e341fba fc03fe60cf675e515cca315d4491e87436'.replace(/ /g,''),
  [controllerPath]:'aae99cdd02b00bdd78d1f02fed85c18bc72b82cab9a66ceb7e0e3590ec3e8790',
  [helperPath]:'a25febd091b6d13ee2b3aaf3713f21a2fa720c0f240a6b042cd6defd023cf783'
};
function sha(file){return crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');}
for(const [file,want] of Object.entries(pins))assert.equal(sha(file),want,`pinned input changed: ${file}`);
const oracle=JSON.parse(fs.readFileSync(path.join(root,oraclePath),'utf8'));
assert.equal(oracle.cases.length,20);
const src=Object.fromEntries(['controller','helper','knowledge'].map((k,i)=>[k,fs.readFileSync(path.join(root,[controllerPath,helperPath,knowledgePath][i]),'utf8')]));
let providerCalls=0;
const w={console,fetch(){providerCalls++;throw Error('provider fetch forbidden');},XMLHttpRequest:function(){providerCalls++;throw Error('provider XHR forbidden');},_spbLayerRev:3,selectedZoneIndex:0,_psdLayers:[{id:'numbers',name:'Numbers',visible:false}],paintImageData:{width:8,height:8},zones:[{id:'roof',name:'Roof',base:'gloss'}],document:{body:{classList:{contains(){return false;}}}}};w.window=w;
w.SPBSourceLoadTransaction={getGeneration:()=>5,getCommittedGeneration:()=>5,isLoading:()=>false,isCommitted:()=>true,getCommittedPath:()=> 'C:/paint/car.psd',getCommittedFingerprint:()=> 'file-sha256:'+ 'a'.repeat(64)};
w.SpbProCar={map:()=>({}),missing:()=>[],signature:()=> 'layout-5'};
vm.createContext(w);vm.runInContext(src.knowledge,w,{filename:knowledgePath});vm.runInContext(src.helper,w,{filename:helperPath});
const claimStart=src.controller.indexOf('function selfHelpClaim('),claimEnd=src.controller.indexOf('    function selfHelpResult(',claimStart),replyEnd=src.controller.indexOf('    function selfHelpSig(',claimEnd);
assert(claimStart>=0&&claimEnd>claimStart&&replyEnd>claimEnd,'actual self-help controller hook bounds exist');
const controllerHooks=src.controller.slice(claimStart,claimEnd)+src.controller.slice(claimEnd,replyEnd);
const setup=`var window=globalThis,SH=window.SpbSelfHelp,START_OVER_RE=/^\\s*start over\\s*$/i,CHECK_AGAIN_RE=/$a/,E=null,D={compoundPlan:function(){return null;}},SH_FIRST_RE=/^(?:how|what|where|which|can|tell me|will|if)\\b/i;function elemOwnsText(){return false;}function complaintOf(){return false;}function supportClass(){return null;}function advisorIntent(){return null;}function editPlan(){return null;}\n${controllerHooks}\nthis.claim=selfHelpClaim;this.reply=selfHelpResult;`;
vm.runInContext(setup,w,{filename:'actual-integration9-self-help-claim.cjs'});
const state={paint:'psd',layers:[{name:'Numbers',hidden:true}],zones:[{i:0,name:'Roof',base:'gloss'}],selected:0,mode:'pro'};
const need={
 'G01':[/flattened means|flattening/i,/one image|combined/i,/separate editable layers/i],
 'G02':[/edit/i,/flattened|layers/i],
 'G03':[/source|layered/i,/cannot|no longer|reopen/i],
 'G04':[/LAYERS/i,/Numbers/i],
 'G05':[/eye|show|visible/i],
 'G06':[/CLEARCOAT/i,/B \/ COAT/i,/R \/ METAL/i,/G \/ ROUGH/i],
 'G09':[/without an API key/i,/optional/i],
 'G10':[/offline/i,/scoped paint edits/i,/Undo/i],
 'G11':[/Save \/ Open/i,/layer/i],
 'G12':[/source|PSD|file/i],
 'G13':[/not|clarif|name|part|scope|confirm/i],
 'G14':[/hood|part/i,/zone|apply|finish/i],
 'G15':[/trace|vector|logo|image/i],
 'G16':[/LAYERS|layer/i,/image|logo/i],
 'G17':[/source paint|own color|solid color|green/i],
 'G18':[/undo|manual|later|conflict/i],
 'G19':[/Ctrl\+Z|History|Undo/i]
};
const helpIds=new Set(Object.keys(need));
const actionIds=new Set(['G07','G08','G20']);
const rows=[];
for(const c of oracle.cases){
 const direct=w.SpbSelfHelp.answer(c.input,state);const claimed=w.claim(c.input);const result=claimed? w.reply(claimed):null;let errors=[];
 if(helpIds.has(c.id)){
   if(!direct||!direct.text)errors.push('no helper answer');
   else for(const re of need[c.id])if(!re.test(direct.text))errors.push('missing '+re);
   if(!claimed)errors.push('controller did not claim passive question');
   if(result&&((result.queue||[]).length!==0||(result.calls||0)!==0))errors.push('help route has effects');
   if(result&&!result.text)errors.push('no route text');
   if(c.id==='G11'&&/PSD included|paint.*in one file|bundles? the paint/i.test(direct&&direct.text||''))errors.push('claims the source PSD is bundled into the project');
 }
 if(actionIds.has(c.id)){if(direct!==null)errors.push('helper answer captured action');if(claimed!==null)errors.push('controller self-help captured action');}
 rows.push({id:c.id,pass:errors.length===0,helperKind:direct&&direct.intent||null,routeClaim:!!claimed,queue:result&&result.queue?result.queue.length:0,text:direct&&direct.text?direct.text.slice(0,260):null,errors});
}
assert.equal(providerCalls,0);
const fails=rows.filter(r=>!r.pass);
const retainedRouteText=execFileSync(process.execPath,['tests/ai_guidance_w74_route_review_contract.cjs',controllerPath,helperPath],{cwd:root,encoding:'utf8'});
const retainedRoute=JSON.parse(retainedRouteText);assert.equal(retainedRoute.status,'PASS');assert.equal(retainedRoute.cases,12);assert.equal(retainedRoute.failed,0);
const report={status:fails.length?'FINDINGS':'PASS_WITH_LIMITS',task:'W84 offline guidance semantics review',date:'2026-10-04',
  freshOracle:{path:oraclePath,sha256:sha(oraclePath),cases:oracle.cases.length,frozenBeforeHelperRegexInspection:true},
  pins:{controller:{path:controllerPath,sha256:sha(controllerPath)},helper:{path:helperPath,sha256:sha(helperPath)},knowledge:{path:knowledgePath,sha256:sha(knowledgePath)},projectsSource:{path:'js/features/spb-projects.js',sha256:sha('js/features/spb-projects.js')}},
  counts:{freshCases:rows.length,semanticallyMet:rows.length-fails.length,semanticGaps:fails.length,passiveHelpClaims:rows.filter(r=>r.routeClaim&&!actionIds.has(r.id)).length,actionControlsNotCaptured:rows.filter(r=>actionIds.has(r.id)&&!r.routeClaim).length,helpQueueMutations:rows.reduce((n,r)=>n+r.queue,0),providerCalls,nativeCalls:0},
  rows,
  findings:[
    {id:'G02',severity:'P2 usefulness',issue:'“Can I still edit a flattened paint?” routes to generic load-paint instructions.'},
    {id:'G03',severity:'P2 usefulness',issue:'Asking how to get separate layers back after flattening returns instructions for merging/flattening, without saying recovery requires an available layered source.'},
    {id:'G11',severity:'P1 factual accuracy',issue:'Answer says “It saves the paint (PSD included) ... in one file.” The project serializer stores sourcePaintFile as a path, while project-open checks source path availability before applying. The help claim that the PSD is included is contradicted by the project implementation.'},
    {id:'G12',severity:'P2 usefulness',issue:'No answer for whether a saved project can reopen after its source PSD moved.'},
    {id:'G13',severity:'P2 usefulness',issue:'No answer or stated limit for confirming the exact scope before apply; no self-help claim.'},
    {id:'G15',severity:'P2 usefulness',issue:'No answer about automatic logo tracing/import limits.'},
    {id:'G17',severity:'P2 semantic routing',issue:'Authored green-base versus source-paint question is answered with Custom Number versus Sim-Stamped Number guidance.'},
    {id:'G18',severity:'P2 usefulness',issue:'No answer for whether Undo preserves later manual mask edits; existing generic Undo instructions do not address the asked conflict behavior.'}
  ],
  retainedKnownFamilies:{command:'node tests/ai_guidance_w74_route_review_contract.cjs '+controllerPath+' '+helperPath,status:retainedRoute.status,cases:retainedRoute.cases,passed:retainedRoute.passed,failed:retainedRoute.failed,coverage:['layered project save','flatten definition','merge visible','clearcoat blue B channel','number layer location','offline helper/API key','logo position','imperative material/edit controls']},
  evidence:{projectSaveSource:{path:'js/features/spb-projects.js',lines:[202,224],fact:'Serialized project records sourcePaintFile as a path; it does not embed the source PSD.'},projectOpenSource:{path:'js/features/spb-projects.js',lines:[798,805],fact:'Open reads sourcePaintFile then validates source availability before applying project state.'}},
  limits:['W84 helper answers and actual controller selfHelpClaim/selfHelpResult hook were exercised with a controlled VM state. Unclaimed requests are reported as self-help gaps, not proof of the final fallback answer.','W74 is the retained actual offlineAskCore route contract for known guidance/action families; W84 tests do not exercise the full app UI or run paint actions.','Provider and native calls were zero. No production/helper edits were made.']};
fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_GUIDANCE_W84_REVIEW_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,counts:report.counts,retainedRoute:report.retainedKnownFamilies,findings:report.findings.map(x=>({id:x.id,severity:x.severity})),rows},null,2));
if(fails.length)process.exitCode=1;
