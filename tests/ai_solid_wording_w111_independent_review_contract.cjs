'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const candidatePath='_easy_claude_work/ai14h_solid_wording_successor/candidate/spb-pro-design.js';
const runtime='_easy_claude_work/ai14h_generation3_runtime11';
const guardPath='_easy_claude_work/ai14h_final_source_identity_candidate/browser-file-v2/spb-pro-ai.js';
const controllerPath='_easy_claude_work/ai14h_solid_wording_successor/candidate/spb-pro-ai.js';
const freshPath='_easy_claude_work/ai14h_w111_independent_review/solid-oracle.json';
const w118Path='_easy_claude_work/ai14h_w118_solid_color_modifier_review/fresh-oracle.json';
const read=p=>fs.readFileSync(path.join(root,p),'utf8'),sha=s=>crypto.createHash('sha256').update(s).digest('hex');
const design=read(candidatePath),baseController=read(runtime+'/js/spb-pro-ai.js'),controller=read(controllerPath),guard=read(guardPath),fresh=read(freshPath),prior=read(w118Path);
const freshOracle=JSON.parse(fresh), priorOracle=JSON.parse(prior);
assert.equal(sha(fresh),'bd0319f32fc013025a40b053ab872460de1f89241bbcc8ebf7811a447d27f93f','fresh oracle pin');
assert.equal(sha(prior),'337743318f206f4a9843233b9b45a8d2e5c2be a20295ceb44f99e29ecc988d48'.replace(/ /g,''),'W118 rejected review oracle remains frozen');
assert.equal(sha(baseController),'aea057cb2965b714700304ca598c0e59ab25e02fffb5575d5d29fc36ccd5ff76','Runtime11 controller base pin');
assert.equal(sha(guard),'fb63f5906e1c9fc9d49150f571d64fde640e0a4630319c418fe4f9c2e7e5413a','source-identity guard v2 pin');

function extract(source,name){const start=source.indexOf(`function ${name}(`);assert(start>=0,`missing ${name}`);const brace=source.indexOf('{',start);let depth=0,q='',esc=false,line=false,block=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q='';continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;else if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw Error('unterminated '+name);}
function loadDesign(){const w={};vm.runInNewContext(design,{window:w,console});return w.SpbProDesign;}
function harness(){
 const w={console,Promise,Date,Math,JSON,Object,Array,String,Number,RegExp,Error,Set,Map,parseInt,parseFloat,document:{body:{classList:{contains:()=>false}},getElementById:()=>null},zones:[],_psdLayers:[],paintImageData:null,selectedZoneIndex:-1,zoneSourceLayerIds:()=>[],_spbLayerRev:0,_spbOperationRevision:1,SpbProCar:{roles:()=>[],map:()=>null,missing:()=>[]},SpbAiLease:{internal:()=>true},SpbAI:{cached:()=>({configured:false})}};w.window=w;vm.createContext(w);
 const load=(p)=>vm.runInContext(read(p),w,{filename:p});
 load(runtime+'/js/spb-ai-instruction-intent-guard.js');load(runtime+'/js/spb-ai-complete-instruction-guard.js');
 w.D=loadDesign(); w.E=null; w.AI=w.SpbAI; w.CAR=null; w._skipParts=false; w._absent={}; w._offlineLast=null; w._advLast=null; w._advRejected=[];w._advDislikes=[];w._advUsed=null;w._busy=false;w._log=[];w._serial=0;w._forcedIdeaCols=null;w._envMemo=null;w._partMemoryWarmAttemptTicket=null;w.START_OVER_RE=/^start over$/i;w.NUM_FIX_RE=/^\s*$/;w.NOT_ELEM_RE=/$a/;
 let activeTicket={ok:true,id:1}; const sinks=[];
 Object.assign(w,{
  normalizeOfflineInstruction:null,offlineInstructionPreflight:null,relativeBodyScopePreflight:null,
  operationCurrent:t=>!!t&&t.ok===true,operationCanceled:()=>({offline:true,queue:[],cancelled:true}),operationStart:()=>activeTicket,
  operationRelease(){},operationBind:r=>r,operationManager:()=>({ready(){},sameDocument:()=>true}),operationPublish:(_t,fn)=>fn(),
  operationTicket:()=>null,operationTools:()=>[],operationRevision:()=>1,elementRunCurrent:()=>true,
  contextualHelpReply:()=>null,selfHelpClaim:()=>null,selfHelpResult:r=>({offline:true,queue:[],howto:true,text:r.text}),
  advisorOwns:()=>false,advisorIntent:()=>null,offlineMaterialPlan:()=>null,editPlan:()=>null,editYieldsToStack:()=>false,
  pendingNamedPartWarmTarget:()=>null,warm:()=>Promise.resolve(),hydratePartMemory(){},
  captureOriginal(){},render(){},intentSpecOnly:()=>false,
  offlineCoveredPartAsk:(text,proof)=>{sinks.push({kind:'covered',text,proof});return Promise.resolve({offline:true,queue:[],route:'covered',proof});},
  offlineLookAsk:(text,look)=>{sinks.push({kind:'look',text,look});return Promise.resolve({offline:true,queue:[],route:'look-clarification',text:'I could not verify that exact solid-color scope. Please choose one exact part or finish.'});},
  offlinePartAsk:(text,plan)=>{sinks.push({kind:'part',text,plan});return Promise.resolve({offline:true,queue:[],route:'part',plan});},
  offlineSpecAsk:(text,plan)=>{sinks.push({kind:'spec',text,plan});return Promise.resolve({offline:true,queue:[],route:'spec',plan});},
  offlineElementAsk:(text,plan)=>{sinks.push({kind:'element',text,plan});return Promise.resolve({offline:true,queue:[],route:'element',plan});},
  offlineIdeasAsk:()=>null,offlineCannot:()=>null,layerVisRequest:()=>null,offlineNumbersAsk:()=>null,
  offlineElemWrong:()=>null,offlineRefineAsk:()=>null,offlineStartOver:()=>({offline:true,queue:[]}),offlineUndo:()=>({offline:true,queue:[]}),
  offlineScopeReply:()=>({offline:true,queue:[],route:'scope-ask'}),preflightTeach:()=>({offline:true,queue:[],route:'teach-ask'}),
  offlineHowto:()=>null,operationFailure:()=>({offline:true,queue:[]}),offlineGaveUp:()=>true,offlineCanHandle:()=>true,
  logMiss(){},askCore:()=>Promise.resolve({offline:true,queue:[]}),
  offlineInstructionPreflight:null
 });
 // Controller-v2 normalization/preflight functions run with the frozen Runtime11
 // intent/complete guards, while routing and Design remain the pinned Runtime11 stack.
 w.normalizeOfflineInstruction=vm.runInContext('('+extract(controller,'normalizeOfflineInstruction')+')',w);
 w.offlineInstructionPreflight=vm.runInContext('('+extract(guard,'offlineInstructionPreflight')+')',w);
 w.relativeBodyScopePreflight=vm.runInContext('('+extract(guard,'relativeBodyScopePreflight')+')',w);
 for(const n of ['offlineAsk','offlineAskCore','askForTicket','ask']) vm.runInContext(extract(controller,n),w,{filename:'private-controller:'+n});
 return {w,sinks};
}

async function coveredConsumerMetadata(proof){
 const w={Promise,JSON,String,Array,Error,D:loadDesign(),_absent:{},_skipParts:false,_busy:false,_progress:'',_spbOperationRevision:1};
 const ticket={ok:true,id:7},captured={zones:null,reply:null};
 Object.assign(w,{operationCurrent:t=>t===ticket,operationCanceled:()=>({queue:[],cancelled:true}),operationRelease(){},warm:()=>Promise.resolve(),render(){},CAR:{missing:()=>[]},preflightTeach:()=>Promise.resolve({queue:[]}),makeTools:q=>q,operationTools:()=>[{name:'add_zone',handler(){}},{name:'edit_zone',handler(){}}],queueEditZones(cm){captured.zones=cm.zones;return {errs:[],lines:cm.zones.map(z=>'updated '+z.region.part),merged:true};},editReply(text,buttons,opts){captured.reply={text,buttons,opts};return {offline:true,queue:opts&&opts.queue||[],text};},markPartFollowupQueue(){}});
 vm.createContext(w);vm.runInContext(extract(controller,'offlineCoveredPartAsk'),w);
 const result=await w.offlineCoveredPartAsk('make requested parts',proof,{_spbOperation:ticket});
 return {captured,result};
}

(async()=>{
 const rows=[],issues=[];let totalSinks=0;
 for(const c of freshOracle.cases){const {w,sinks}=harness();const result=await w.ask(c.input,{offline:true});const sink=sinks[sinks.length-1]||null;const row={id:c.id,route:result.route|| (sink&&sink.kind)||'guard-or-other',queue:(result.queue||[]).length,howto:!!result.howto,zonePlans:sink&&sink.proof?sink.proof.zones.map(z=>({part:z.region.part||'body',color:z.color,finish:z.finish})):sink&&sink.plan?sink.plan.zones.map(z=>({part:z.region.part||'body',color:z.color,finish:z.finish})):[],text:String(result.text||'').slice(0,170)};rows.push(row);
  const noQueue=()=>{if((result.queue||[]).length)issues.push(c.id+': queue was nonempty');}; if((result.queue||[]).length)issues.push(c.id+': unexpected direct queue in private harness');
  if(['roof-solid-red','two-target-two-color','solid-roof-plus-matte-hood','implicit-solid-alias'].includes(c.id)){
   if(!sink||sink.kind!=='covered')issues.push(c.id+': public ask did not reach complete covered-part route');
   if(c.id==='roof-solid-red'&&!(row.zonePlans.length===1&&row.zonePlans[0].part==='roof'&&row.zonePlans[0].color==='#c8102e'))issues.push(c.id+': roof solid red plan incomplete or mis-scoped');
   if(c.id==='two-target-two-color'&&!(row.zonePlans.length===2&&row.zonePlans.some(z=>z.part==='roof'&&z.color==='#c8102e')&&row.zonePlans.some(z=>z.part==='hood'&&z.color==='#1450b4')))issues.push(c.id+': a target/color clause was dropped or crossed');
   if(c.id==='solid-roof-plus-matte-hood'&&!(row.zonePlans.length===2&&row.zonePlans.some(z=>z.part==='roof'&&z.finish==='base::gloss'&&z.color==='#c8102e')&&row.zonePlans.some(z=>z.part==='hood'&&z.finish==='base::matte'&&z.color==='#1450b4')))issues.push(c.id+': per-clause finish/color association lost');
   noQueue();
  } else if(['roof-or-hood-ambiguity','roof-black-ice-nebula','whole-body-with-hood-exception'].includes(c.id)){
   if(!sink||sink.kind==='covered'||sink.kind==='part')issues.push(c.id+': ambiguous/unsupported request reached an executable part route');noQueue();
  } else if(c.id==='whole-body-control'){
   if(!sink||sink.kind!=='part'||!(row.zonePlans.length===1&&row.zonePlans[0].part==='body'))issues.push(c.id+': explicit whole-body solid recolor was lost or redirected');
  } else if(c.id==='solid-as-material-qualifier'){
   if((result.queue||[]).length||!sink||sink.kind==='covered'||sink.kind==='part')issues.push(c.id+': base+flake stack was partially claimed instead of held for stack clarification');
  } else if(c.id==='known-finish-control'){
   if(!sink||!['element','spec','part','covered','look'].includes(sink.kind))issues.push(c.id+': ordinary matte-black routing was suppressed');noQueue();
  } else if(['informational-solid-question','quoted-solid-example'].includes(c.id)){
   if((result.queue||[]).length||sink&&['covered','part','spec','element'].includes(sink.kind))issues.push(c.id+': read-only/quoted example entered an edit route');
  } else if(c.id==='prohibited-solid-action'){
   if((result.queue||[]).length||sink&&['covered','part','spec','element'].includes(sink.kind))issues.push(c.id+': prohibited action entered an edit route');
  } else if(c.id==='hood-matte-blue'){
   if((result.queue||[]).length||!sink||!['element','spec','part','covered','look'].includes(sink.kind))issues.push(c.id+': ordinary matte-blue target was stranded without a safe route');
  }
  totalSinks+=sinks.length;
 }
 const D=loadDesign();
 // Replay the eight rejected W118 cases without changing their frozen oracle.
 const priorRows=priorOracle.cases.map(c=>{const q=c.input||c.utterance;const cov=D.offlinePartCoverage(q),look=D.lookRequest(q),part=D.offlinePart(q),spec=D.offlineSpec(q);return {id:c.id,coverageComplete:!!(cov&&cov.complete),zones:cov&&cov.zones.map(z=>({part:z.region.part||'body',color:z.color,finish:z.finish})),look:look&&look.query,partZones:part&&part.zones.map(z=>({part:z.region.part||'body',color:z.color,finish:z.finish})),spec:spec&&spec.zones.map(z=>({part:z.region.part,color:z.color,finish:z.finish}))};});
 const mixed=priorRows.find(x=>x.id==='mixed-two-part-different-finishes');assert(mixed.coverageComplete&&mixed.zones.length===2&&mixed.zones.some(z=>z.part==='roof'&&z.finish==='base::gloss'&&z.color==='#c8102e')&&mixed.zones.some(z=>z.part==='hood'&&z.finish==='base::matte'&&z.color==='#1450b4'),'prior mixed-clauses must preserve each target finish');
 const splitProof=D.offlinePartCoverage('Make only roof solid red and hood matte blue');
 assert(splitProof&&splitProof.finish==='mixed'&&splitProof.finishExplicitByPart.roof===false&&splitProof.finishExplicitByPart.hood===true,'per-part finish explicitness must distinguish solid-color clause from matte clause');
 const consumed=await coveredConsumerMetadata(splitProof), consumedZones=consumed.captured.zones;
 assert.equal(consumedZones.length,2,'covered consumer must forward both part plans');
 const roofMeta=consumedZones.find(z=>z.region.part==='roof')._meta, hoodMeta=consumedZones.find(z=>z.region.part==='hood')._meta;
 assert.deepEqual(Array.from(roofMeta.what),['red'],'solid roof clause must not inherit global mixed finish label');
 assert.equal(roofMeta.finishExplicit,false,'solid roof clause must preserve existing owner finish');
 assert.deepEqual(Array.from(hoodMeta.what),['blue','matte'],'hood clause must carry its explicit matte finish');
 assert.equal(hoodMeta.finishExplicit,true,'hood clause must apply its explicit matte finish');
 assert(!consumed.captured.reply.text.includes('mixed'),'visible copy must not label red/mixed as a finish');
 for(const id of ['solid-unknown-look-token','solid-ambiguous-part-scope','unknown-solid-word']){const r=priorRows.find(x=>x.id===id);assert(r&&!r.coverageComplete&&r.look,'old unknown/ambiguous solid request must not gain whole/black coverage');}
 const source=priorRows.find(x=>x.id==='source-paint-color-retain');assert(source&&source.spec&&source.spec.some(z=>z.color==='source'),'source-paint finish-only behavior must remain intact');
 const byId=id=>rows.find(x=>x.id===id);
 const expectPlans=(id,pred,why)=>{const x=byId(id);if(!x||!pred(x.zonePlans))issues.push(id+': '+why);};
 expectPlans('roof-chrome-hood-matte',z=>z.length===2&&z.some(a=>a.part==='roof'&&a.finish==='base::f_chrome')&&z.some(a=>a.part==='hood'&&a.finish==='base::f_soft_matte'),'roof chrome and hood matte must stay attached to their named parts');
 expectPlans('roof-red-hood-matte',z=>z.length===2&&z.some(a=>a.part==='roof'&&a.color==='#1450b4')&&z.some(a=>a.part==='hood'&&a.finish==='base::f_soft_matte'),'blue roof and matte hood clauses must remain distinct');
 const conflict=byId('same-target-conflicting-finish'); if(conflict&&['element','spec','part','covered'].includes(conflict.route))issues.push('same-target-conflicting-finish: contradictory roof finishes compiled into executable route '+JSON.stringify(conflict.zonePlans));
 const readOnlyIds=['quoted-finish-name','question-roof-matte'];for(const id of readOnlyIds){const x=byId(id);if(!x||x.queue||['element','spec','part','covered'].includes(x.route))issues.push(id+': read-only query reached executable plan');}
 const preserve=byId('roof-color-only-preserve-finish');if(preserve&&(!preserve.queue&&preserve.route==='look-clarification')){ /* safe refusal; reported partial */ }else if(preserve)issues.push('roof-color-only-preserve-finish: could not confirm safe preserve-current-finish behavior');
 const baselineReview=JSON.parse(fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_w111_independent_review/solid-conflict-baseline-result.json'),'utf8')); const baselineSame=baselineReview.row&&byId('same-target-conflicting-finish')&&JSON.stringify(baselineReview.row.zonePlans)===JSON.stringify(byId('same-target-conflicting-finish').zonePlans);
 const report={work_item:'Independent solid wording successor public-route review',status:issues.length?(baselineSame?'BASELINE_GAP_REPRODUCED_NOT_SUCCESSOR_REGRESSION':'REVIEW_GAPS'):'PASS_PRIVATE_ROUTE',pins:{baseDesign:'_easy_claude_work/ai14h_generation3_runtime11/js/spb-pro-design.js',candidate:candidatePath,candidateSha256:sha(design),baseController:runtime+'/js/spb-pro-ai.js',baseControllerSha256:sha(baseController),privateController:controllerPath,privateControllerSha256:sha(controller),guard:guardPath,freshOracle:freshPath,w118Oracle:w118Path},baselineComparison:{path:'_easy_claude_work/ai14h_w111_independent_review/solid-conflict-baseline-result.json',sameConflictingPlan:baselineSame},freshOracle:{sha256:sha(fresh),cases:freshOracle.cases.length},w118Oracle:{sha256:sha(prior),cases:priorOracle.cases.length,replayed:priorRows},rows,issues,counts:{fresh:rows.length,publicAskCases:rows.length,routeSinkCases:totalSinks,consumerMetadataCases:1,providerCalls:0,nativeCalls:0,applyCalls:0},reviewNotes:['Verified per-clause plan association for roof-chrome/hood-matte and roof-blue/hood-matte in the actual public ask route. The existing consumer contract also passed its explicit finishExplicit metadata and buyer-copy assertion for solid-red roof plus matte-blue hood. The same-target matte-and-chrome phrase was miscompiled as a body-chrome plus roof-matte plan and reached the element action route; it should be clarified/refused atomically. Color-only keep-finish could only be safely clarified in this harness. Color/source plans remain provisional without a real owner/current authored-color fixture.'],limits:['Executed the actual exported ask(), askForTicket(), offlineAsk(), offlineAskCore(), Design classifiers, and offlineCoveredPartAsk consumer from pinned source bytes in a VM. Route sinks for covered edits/look clarification and queueEditZones were controlled boundary stubs, so queued/applied pixels, current-zone proof, and native UI behavior are not claimed. The W118 oracle and source files were read-only.']};
 fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_W111_SOLID_SUCCESSOR_INDEPENDENT_REVIEW_2026-10-04.json'),JSON.stringify(report,null,2)+'\n'); console.log(JSON.stringify(report,null,2));if(issues.length)process.exitCode=1;
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
