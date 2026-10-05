'use strict';
const FRESH_ORACLE = Object.freeze([
  {id:'pos-roof-clearcoat-after-target',text:'Increase the roof clearcoat by 20 points',kind:'edit',part:'roof',channel:'clearcoat',delta:20},
  {id:'pos-hood-roughness-after-target',text:'Lower the hood roughness by 12 points',kind:'edit',part:'hood',channel:'roughness',delta:-12},
  {id:'pos-roof-metallic-after-target',text:'Raise roof metallic by 7 points',kind:'edit',part:'roof',channel:'metalness',delta:7},
  {id:'pos-channel-before-target-cc',text:'Increase clearcoat on the roof by 20 points',kind:'edit',part:'roof',channel:'clearcoat',delta:20},
  {id:'pos-channel-before-target-r',text:'Reduce roughness on the hood by 8 points',kind:'edit',part:'hood',channel:'roughness',delta:-8},
  {id:'pos-negative-explicit',text:'Decrease the roof clearcoat by 15 points',kind:'edit',part:'roof',channel:'clearcoat',delta:-15},
  {id:'pos-current-value-and-delta',text:'The roof is at 40 clearcoat points; add 10 points',kind:'clarify'},
  {id:'preservation-cc-only',text:'Add 20 clearcoat points to the roof',kind:'edit',part:'roof',channel:'clearcoat',delta:20},
  {id:'preservation-roughness-only',text:'Set hood roughness down 10 points',kind:'edit',part:'hood',channel:'roughness',delta:-10},
  {id:'clarify-no-unit',text:'Increase roof clearcoat by 20',kind:'clarify'},
  {id:'clarify-no-amount',text:'Increase the roof clearcoat',kind:'clarify'},
  {id:'reject-percent',text:'Increase the roof clearcoat by 20 percent',kind:'clarify'},
  {id:'reject-absolute',text:'Set roof clearcoat to 80 points',kind:'clarify'},
  {id:'reject-unknown-channel',text:'Increase roof sparkle by 20 points',kind:'clarify'},
  {id:'reject-mixed-channels',text:'Increase roof clearcoat by 20 points and lower roughness by 5 points',kind:'clarify'},
  {id:'reject-conflicting-direction',text:'Increase and decrease hood roughness by 10 points',kind:'clarify'},
  {id:'reject-prohibition',text:'Do not increase roof clearcoat by 20 points',kind:'delegate'},
  {id:'positive-ordinary-guidance-unaffected',text:'How do I adjust clearcoat on a roof?',kind:'delegate'}
]);
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'_easy_claude_work/ai14h_w101_review');
const oraclePath=path.join(dir,'fresh_oracle.json'),frozenModule=path.join(dir,'spb-ai-material-controls.baseline.js'),controllerFrozenPath=path.join(dir,'spb-pro-ai.frozen.js'),controllerPath=path.join(dir,'spb-pro-ai.candidate.js'),candidatePath=path.join(dir,'spb-ai-material-controls.candidate.js');
function sha(file){return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase();}
const oracleDoc=JSON.parse(fs.readFileSync(oraclePath,'utf8'));assert.equal(sha(oraclePath),'E4A84B29C4C9B2A00B25F3777E635B70A37529463F5F5E448BFF19AD532FBCAA','fresh oracle pin changed');
assert.equal(sha(frozenModule),'A6F50C22C2D3A4F6F9707505D66C6C30B9D2CC0E04D78F00F0D103F38A49919D','Runtime5 material parser pin changed');
assert.equal(sha(controllerFrozenPath),'60AE271C62D697AB31B9F2EED47B841A6038755DB8F319507E38D03185EE3A21','Runtime5 controller pin changed');assert.equal(sha(controllerPath),'D05FD03D8E50151F7888D7E32C0D92AC661864EB989A3B7F9F9541C7692AE4E2','isolated controller routing candidate changed');
assert.equal(oracleDoc.cases.length,FRESH_ORACLE.length,'oracle case count is pinned');assert.deepEqual(FRESH_ORACLE.map(c=>c.text),oracleDoc.cases.map(c=>c.input),'fresh test inputs must exactly match pre-inspection oracle');
const source=fs.readFileSync(controllerPath,'utf8');
function extractFunction(src,name){const at=src.indexOf('function '+name+'(');assert(at>=0,'missing '+name);const open=src.indexOf('{',at);let d=0,q=null,esc=false,line=false,block=false;for(let i=open;i<src.length;i++){const c=src[i],n=src[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;else if(c==='}'&&--d===0)return src.slice(at,i+1);}throw Error('unterminated '+name);}
function routerWorld(part,controls){
 const queued=[],zone={id:'fixture-'+part,name:'helper '+part,specShiftR:13,specShiftG:27,specShiftB:31,color:'#123456',finish:'fixture'};
 const route={window:{SpbMaterialControls:controls},String,RegExp,Promise,Object,Number,Math,console,_spbOperation:{collection:1},_busy:false,_progress:'',_advLast:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,
  offlineInstructionPreflight:()=>null,operationCurrent:()=>true,operationCanceled:()=>({cancelled:true}),operationRelease:()=>{},editPlan:()=>null,advisorOwns:()=>false,captureOriginal:()=>{},
  editReply:(text,chips,extra)=>{if(extra&&Array.isArray(extra.queue))queued.push(...extra.queue);return {text,chips:chips||null,...(extra||{})};},render:()=>{},warm:()=>Promise.resolve(),editEnv:()=>({}),
  E:{plan:text=>{const m=/make only the (.+) blue/i.exec(text);return m?{kind:'ops',exactPart:true,ops:[{target:{kind:'part',part:m[1]}}]}:null;}},normaliseSpec:x=>x,protectDecals:()=>{},editKey:r=>r.part,carSig:()=> 'car-fixture',_editRegSig:'car-fixture',_editReg:{},zones:[zone],partOwnerCurrent:(z,key)=>!!z&&key===part&&z.name===('helper '+part),operationTools:tools=>tools,
  makeTools:queue=>[{name:'edit_zone',handler:edit=>{queue.push(JSON.parse(JSON.stringify(edit)));return {ok:true};}}]};
 route._editReg[part]=zone.name;vm.createContext(route);
 const actual=[extractFunction(source,'normalizeOfflineInstruction'),'function offlineInstructionPreflight(text){return null;}',...['offlineMaterialPlan','offlineMaterialAsk','offlineAsk'].map(n=>extractFunction(source,n))].join('\n')+'\nthis.routeAsk=offlineAsk;this.materialPlan=offlineMaterialPlan;this.materialAsk=offlineMaterialAsk;';vm.runInContext(actual,route);
 return {route,zone,queued};
}
function parserResult(controls,c){return controls.parse(c.text);}
async function main(){
 const baseline=require(frozenModule),candidate=require(candidatePath),results=[];
 const baselineNewOrder=FRESH_ORACLE.slice(0,3).map(c=>({id:c.id,kind:parserResult(baseline,c).kind,reason:parserResult(baseline,c).reason||null}));
 const baselineCanonical=FRESH_ORACLE.slice(3,5).map(c=>({id:c.id,kind:parserResult(baseline,c).kind,part:parserResult(baseline,c).part,channel:parserResult(baseline,c).channel}));assert(baselineCanonical.every(x=>x.kind==='edit'),'baseline channel-first controls remain supported');
 assert(baselineNewOrder.some(x=>x.kind!=='edit'),'baseline must characterize the channel-after-target gap');
 for(const c of FRESH_ORACLE){
  const parsed=parserResult(candidate,c);
  assert.equal(parsed.kind,c.kind,c.id+' parser classification');
  if(c.kind==='edit'){
   assert.equal(parsed.part,c.part,c.id+' preserves exact part');assert.equal(parsed.channel,c.channel,c.id+' selects exact channel');assert.equal(parsed.delta,c.delta,c.id+' relative delta/sign');
   const before={metal:13,rough:27,clearcoat:31},slot=c.channel==='metalness'?'metal':c.channel==='roughness'?'rough':'clearcoat';
   const built=candidate.buildEdit({id:'fixture-zone',name:'owner roof',specShiftR:before.metal,specShiftG:before.rough,specShiftB:before.clearcoat},parsed);
   assert.equal(built.kind,'edit',c.id+' builds edit');const expected={...before};expected[slot]=Math.max(-127,Math.min(127,before[slot]+c.delta));assert.deepEqual(built.spec_shift,expected,c.id+' preserves unmentioned channels');
   const w=routerWorld(c.part,candidate),zoneBefore=JSON.parse(JSON.stringify(w.zone));let reply;try{reply=await w.route.routeAsk(c.text,{_spbOperation:w.route._spbOperation});}catch(e){throw new Error(c.id+' route failure: '+e.message)}
   assert.equal(w.queued.length,1,c.id+' actual offline controller queues one edit; reply='+JSON.stringify(reply));assert.equal(w.queued[0].zone_id,w.zone.id,c.id+' queues exact verified fixture zone');assert.equal(w.queued[0]._spbPartRegKey,c.part,c.id+' carries exact part ownership key');assert.deepEqual(w.queued[0].spec_shift,expected,c.id+' controller changes only requested channel');assert.deepEqual(w.zone,zoneBefore,c.id+' queues without eager source mutation');assert.match(reply.text,/points/i,c.id+' reports units');
   results.push({id:c.id,pass:true,parser:'edit',route:'one exact queue edit',channel:c.channel,part:c.part,delta:c.delta});
  }else{
   assert(parsed.kind==='clarify'||parsed.kind==='delegate',c.id+' is non-actionable without an edit');
   const w=routerWorld('roof',candidate),before=JSON.parse(JSON.stringify(w.zone));let reply=null;
   const planned=w.route.materialPlan(c.text);
   if(parsed.kind==='delegate'&&parsed.reason==='question-or-howto') assert.equal(planned,null,c.id+' remains outside material-edit ownership');
   else if(planned&&planned.kind==='clarify') reply=await w.route.materialAsk(c.text,planned,{_spbOperation:w.route._spbOperation}); else assert.equal(planned,null,c.id+' unsupported wording is not claimed as a material edit');
   assert.equal(w.queued.length,0,c.id+' actual material route queues nothing');assert.deepEqual(w.zone,before,c.id+' does not eagerly mutate fixture');if(planned&&planned.kind==='clarify')assert(reply&&reply.text,c.id+' has an actual controller clarification');
   results.push({id:c.id,pass:true,parser:parsed.kind,route:planned&&planned.kind==='clarify'?'actual material clarification; no queue':'not claimed as a material edit; no queue',reason:parsed.reason||null,reply:reply&&reply.text||null});
  }
 }
 // Separate root-requested controls, outside fresh-oracle credit.
 const bare=routerWorld('roof',candidate);assert.equal(candidate.parse('make roof metallic').kind,'delegate','bare look wording is not a channel edit');assert.equal(bare.route.materialPlan('make roof metallic'),null,'bare metallic look remains available to the finish planner');results.push({id:'supplemental-bare-metallic-look',pass:true,parser:'delegate',route:'not claimed as material edit; no queue'});
 const compactPercent=routerWorld('roof',candidate),compactParsed=candidate.parse('Increase the roof clearcoat by 20%');assert.equal(compactParsed.kind,'clarify','compact percent cannot become points');const compactPlan=compactPercent.route.materialPlan('Increase the roof clearcoat by 20%');assert(compactPlan&&compactPlan.kind==='clarify','controller retains a clarification for compact percent');assert.equal(compactPercent.queued.length,0);results.push({id:'supplemental-compact-percent-refused',pass:true,parser:'clarify',route:'actual material clarification; no queue'});
 // Boundary checks: each channel clamps independently and preserves the other two.
 for(const [channel,zone,delta,want] of [['clearcoat',{id:'z',specShiftR:5,specShiftG:-4,specShiftB:120},20,{metal:5,rough:-4,clearcoat:127}],['roughness',{id:'z',specShiftR:5,specShiftG:-120,specShiftB:9},-20,{metal:5,rough:-127,clearcoat:9}]]){
  const built=candidate.buildEdit(zone,{kind:'edit',channel,delta});assert.deepEqual(built.spec_shift,want,'clamp '+channel+' only');
 }
 const report={status:'PASS',task:'W101 isolated material grammar candidate',installed:false,oracle:{path:'_easy_claude_work/ai14h_w101_review/fresh_oracle.json',sha256:sha(oraclePath),count:FRESH_ORACLE.length,frozenBeforeCandidateBehaviorInspection:true},sources:{runtime5MaterialControls:{path:'_easy_claude_work/ai14h_generation3_runtime5/js/spb-ai-material-controls.js',sha256:sha(frozenModule)},runtime5Controller:{path:'_easy_claude_work/ai14h_generation3_runtime5/js/spb-pro-ai.js',sha256:sha(controllerFrozenPath)},isolatedControllerRoutingCandidate:{path:'_easy_claude_work/ai14h_w101_review/spb-pro-ai.candidate.js',sha256:sha(controllerPath),change:'Adds standalone metallic to the offlineMaterialPlan ownership prefilter so the parser-supported “roof metallic” form reaches the existing material route.'},candidateMaterialControls:{path:'_easy_claude_work/ai14h_w101_review/spb-ai-material-controls.candidate.js',sha256:sha(candidatePath)}},baselineGap:{cases:baselineNewOrder,canonicalControls:baselineCanonical,note:'Pinned parser did not recognize the frozen channel-after-target positive requests; existing channel-first behavior remains the positive control.'},results,counts:{passed:results.length,total:results.length,frozenOraclePassed:FRESH_ORACLE.length,supplementalControlsPassed:results.length-FRESH_ORACLE.length,parseAndBuild:results.filter(x=>x.parser==='edit').length,actualOfflineAskCases:8,offlineMaterialPlanCases:results.length,queuedPositiveEdits:results.filter(x=>x.route&&x.route.startsWith('one')).length,clarificationOrGuidanceNoQueue:results.filter(x=>x.route&&x.route!=='one exact queue edit').length,providerCalls:0,nativeCalls:0,serverCalls:0,paintApplications:0},limits:['Uses actual pinned Runtime5 material parser, buildEdit and controller offlineMaterialPlan/offlineMaterialAsk/offlineAsk function bodies in a VM; the current-part owner registry match, E-plan, warmup and edit_zone sink are explicit controlled fixtures.','Verifies parse, build plan and queue construction only. No paint application, native UI, provider, server, or live files were invoked.','Candidate broadens material grammar for the alternate part-then-channel wording and two pre-frozen single-channel relative shorthands. A one-token private controller prefilter extension is needed for standalone “metallic” to reach the parser. All ownership callbacks stay unchanged; edits remain exact-part, one-channel, points-only relative shifts with the existing clamp.']};
 fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_MATERIAL_GRAMMAR_W101_CANDIDATE_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,total:results.length,baselineGap:baselineNewOrder,failures:[]},null,2));
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;});



