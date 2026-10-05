'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const proBasePath='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-pro-ai.js';
const proPath='_easy_claude_work/ai14h_w90_review/route_candidate/spb-pro-ai.js';
const priorW85ProPath='_easy_claude_work/ai14h_w85_review/candidate/spb-pro-ai.js';
const designBasePath='_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-design.js';
const designPath='_easy_claude_work/ai14h_w85_review/candidate/spb-pro-design.js';
const editPath='_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-edit.js';
const priorOraclePath='_easy_claude_work/ai14h_w85_review/fresh-oracle.json';
const oraclePath='_easy_claude_work/ai14h_w90_review/fresh-oracle.json';
const digest=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const source={proBase:read(proBasePath),priorW85Pro:read(priorW85ProPath),pro:read(proPath),designBase:read(designBasePath),design:read(designPath),edit:read(editPath)};
const hashes=Object.fromEntries(Object.entries(source).map(([k,v])=>[k,digest(Buffer.from(v))]));
assert.equal(hashes.proBase,'AAE99CDD02B00BDD78D1F02FED85C18BC72B82CAB9A66CEB7E0E3590EC3E8790');
assert.equal(hashes.priorW85Pro,'E7ECEAF11B2BFC1A39E48C86A07F8DAB95EC046C678087A8168B6E8CC016F70E');
assert.equal(hashes.pro,'731DE3916044C61F0277DCFE0FDB412EB313C600221229F5498A28205F3F317B');
assert.equal(hashes.designBase,'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8');
assert.equal(hashes.design,'4648DE3231015497CC9FF816612A542097A1AD14038A7210753F6CDBFD88D832');
assert.equal(hashes.edit,'99703873013E198857D9ACEAA334821098E53DCAA9D55E14DBD1EC50E58604DE');
const oracleBytes=fs.readFileSync(path.join(root,oraclePath));
assert.equal(digest(oracleBytes),'9A970B1A02E1E7F034F0BBAA2B075FA8E5EC9F620A3CBCC8889FED1B68DDCD82','W90 oracle was frozen before source inspection');
const wxBytes=fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_w90_review/supplemental-whole-exclusion-oracle.json'));
assert.equal(digest(wxBytes),'FEEEC3849C125EAF844CC03FED40AB6705F1DB097C03E7F33081CBE65EFC85CF','supplemental whole-exclusion oracle frozen before guard adjustment');
assert.equal(digest(fs.readFileSync(path.join(root,priorOraclePath))),'DED5D8A5C249024DEF2043F671D5E13498C33E4720E49ABE45BEB78F94B44971','W85 producer oracle remains unchanged');
function extract(sourceText,name){const start=sourceText.indexOf(`function ${name}(`);assert(start>=0,`function ${name} exists`);const brace=sourceText.indexOf('{',start);let depth=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<sourceText.length;i++){const c=sourceText[i],n=sourceText[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return sourceText.slice(start,i+1);}throw new Error('unterminated '+name);}
function route(pro,designSource,text,staleRoof=false,resolveLookHit=false,publicAsk=false){
  const queued=[],events=[],env={palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#168a45',share_pct:10}],layers:[],zoneColours:[]};
  const dctx={console,Promise,document:{}};dctx.window=dctx;vm.createContext(dctx);vm.runInContext(designSource,dctx);vm.runInContext(source.edit,dctx);const D=dctx.SpbProDesign,E=dctx.SpbProEdit;
  const ctx={D,E,window:dctx,console,Promise,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,
    _busy:false,_progress:'',_skipParts:true,_absent:{},CAR:{missing:()=>[],layoutSig:()=>''},zones:[],_editReg:{},_editRegPendingBefore:{},_editRegSig:'car',
    START_OVER_RE:/^\s*(?:start over|new design)\b/i,operationCurrent:t=>{events.push('operation:'+!!t+':'+(t&&t.ok));return !!t&&t.ok===true;},operationCanceled:()=>({cancelled:true}),operationRelease(){},operationPublish:(t,fn)=>fn(),operationTools:ts=>ts,
    offlineInstructionPreflight:()=>null,elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),editPlan:t=>{events.push('editPlan');return E.plan(t,env);},offlineMaterialPlan:()=>null,advisorOwns:()=>false,captureOriginal(){},intentSpecOnly:()=>false,editYieldsToStack:()=>false,
    editEnv:()=>env,advisorIntent:()=>{events.push('advisorIntent');return null;},offlineIdeas:()=>null,_offlineLast:null,offlineCannot:()=>null,layerVisRequest:()=>null,NUM_FIX_RE:/$a/,NOT_ELEM_RE:/$a/,
    offlineSpecAsk(){events.push('offlineSpecAsk');},offlineElementAsk(){events.push('offlineElementAsk');},offlineStartOver(){},offlineUndo(){},prepEnv:()=>Promise.resolve(env),resolveLook:()=>{events.push('resolveLook');return Promise.resolve(resolveLookHit?{label:'Controlled catalog hit',zone:{finish:'base::gloss'},colourFrom:'zone'}:null);},elementKinds:()=>[],exclTargets:()=>[],
    editOverlapNote:()=>'',editOverlapKinds:()=>[],exclNotes:()=>[],_elemCache:null,_elemOk:{},_taughtNow:{},editReply:(reply,chips,opts)=>{events.push('editReply');return {offline:true,text:reply,queue:(opts&&opts.queue)||[],tools:(opts&&opts.tools)||[]};},
    offlineRefineAsk(){events.push('offlineRefineAsk');},offlineHowto(){events.push('offlineHowto');},offlineIdeasAsk(){events.push('offlineIdeasAsk');},offlineScopeReply:()=>{events.push('scopeReply');return {offline:true,text:'Nothing was changed. Please name exact supported parts.',queue:[]};},selfHelpClaim:()=>null,selfHelpResult:x=>x,
    _reqText:'',_specOnlyReq:false,_beforeImg:null,_advLast:null,_forcedIdeaCols:null,render(){},warm:()=>Promise.resolve(),markPartFollowupQueue(){},friendlyZoneError:e=>String(e),editPlural:()=>false,
    normaliseSpec:x=>x,protectDecals(){},makeTools(){return [{name:'add_zone',handler(spec){queued.push({kind:'add',spec:JSON.parse(JSON.stringify(spec))});return {region_check:{share_pct:35}};}},{name:'edit_zone',handler(args){queued.push({kind:'edit',args:JSON.parse(JSON.stringify(args))});return {};} }];},
    scopedPartProofAt:()=>null,scopedPartProofMatches:()=>false,partOwnerCurrent:()=>false,carSig:()=> 'car',scopedPartSourceNow:()=>({generation:3,committedGeneration:3,path:'A.psd',fingerprint:'file-sha256:a',width:100,height:100})
  };
  if(staleRoof)ctx.zones=[{id:'saved-roof',name:'Saved roof',muted:false,regionMask:new Uint8Array([1,0]),useRegion:true,_aiPartProv:{r:JSON.stringify({part:'roof'}),z:'2:1',l:'',e:''},_aiPartSource:{path:'A.psd',fingerprint:'file-sha256:a',generation:2,width:100,height:100}}];
  vm.createContext(ctx);for(const n of ['partRegionKey','editKey','editPlural','hasPriorPartIdentity','offlinePartAsk','offlineCoveredPartAsk','offlineEditAsk','offlineLookAsk','relativeBodyScopePreflight','offlineAsk','offlineAskCore','queueEditZones'])if(pro.includes('function '+n+'('))vm.runInContext(extract(pro,n),ctx,{filename:'W90#'+n});
  ctx._events=events;
  return Promise.resolve((publicAsk?ctx.offlineAsk:ctx.offlineAskCore)(text,{_spbOperation:{ok:true,collection:1},noAdvisor:true})).then(result=>({result,queued,D,E,events,env}));
}
(async()=>{
  const oracle=JSON.parse(oracleBytes.toString('utf8')),rows=[];
  for(const c of oracle.cases.slice(0,12)){
    const out=await route(source.pro,source.design,c.input);
    assert.equal(out.queued.length,0,c.id+' relative body/extent must not queue');
    const reply=String(out.result&&out.result.text||'');
    assert.ok(reply&&/clarif|exact|nothing was changed|cannot safely|supported part|name/i.test(reply),c.id+' must return a truthful noncompletion/clarification: '+JSON.stringify({result:out.result,queue:out.queued,events:out.events,part:out.D.offlinePart(c.input),plan:out.D.offlinePlan(c.input),ideas:out.D.offlineIdeas(c.input,false),look:out.D.lookRequest(c.input),spec:out.D.offlineSpec(c.input),element:out.D.offlineElement(c.input),compound:out.D.compoundPlan(c.input),edit:out.E.plan(c.input,out.env)}));
    assert.doesNotMatch(reply,/\bDone\b|\bnow (?:red|blue|gold|black|white|green)\b/i,c.id+' must not report an ambiguous whole-body completion');
    rows.push({id:c.id,queue:0,route:c.id==='U06'?'shared-preflight-refusal':'safe-ask/refusal',reply:reply.slice(0,160)});
  }
  const sectionHitBefore=await route(source.priorW85Pro,source.design,oracle.cases[5].input,false,true);
  assert.ok(sectionHitBefore.queued.some(q=>q.spec&&q.spec.region&&q.spec.region.everything===true),'unpatched W85 route plus controlled look hit demonstrates whole-car target amplification');
  const sectionHitAfter=await route(source.pro,source.design,oracle.cases[5].input,false,true);
  assert.equal(sectionHitAfter.queued.length,0,'W90 shared dispatch guard must refuse before a controlled generic look resolution');
  assert.match(String(sectionHitAfter.result&&sectionHitAfter.result.text||''),/cannot safely infer|name a supported part/i);
  rows.push({id:'U06-CONTROLLED-LOOK-HIT',before:{queue:sectionHitBefore.queued.length,regions:sectionHitBefore.queued.map(q=>q.spec&&q.spec.region)},after:{queue:sectionHitAfter.queued.length,reply:String(sectionHitAfter.result&&sectionHitAfter.result.text||'').slice(0,180)},note:'The known catalog hit is controlled, not evidence of a particular live-catalog match. It proves the old fallback used whole:true as everything; the shared preflight now stops it before look resolution.'});
  const publicBefore=await route(source.priorW85Pro,source.design,oracle.cases[5].input,false,true,true);
  assert.ok(publicBefore.queued.some(q=>q.spec&&q.spec.region&&q.spec.region.everything===true),'actual public offlineAsk before shared guard can reach the controlled whole-car look resolver');
  const publicAfter=await route(source.pro,source.design,oracle.cases[5].input,false,true,true);
  assert.equal(publicAfter.queued.length,0,'actual public offlineAsk must stop relative extents before advisor/designer/look fallbacks');
  assert.ok(!publicAfter.events.includes('advisorIntent')&&!publicAfter.events.includes('resolveLook'),'shared guard runs before advisor/look fallback ownership');
  assert.match(String(publicAfter.result&&publicAfter.result.text||''),/cannot safely infer|name a supported part/i);
  rows.push({id:'PUBLIC-OFFLINEASK-CONTROLLED-LOOK-HIT',before:{queue:publicBefore.queued.length,regions:publicBefore.queued.map(q=>q.spec&&q.spec.region)},after:{queue:publicAfter.queued.length,reply:String(publicAfter.result&&publicAfter.result.text||'').slice(0,180),events:publicAfter.events},note:'This invokes the real offlineAsk dispatcher with controlled catalog success; the old route queues an everything region, while shared preflight returns before advisorIntent or resolveLook.'});
  const positives=[];
  for(const c of oracle.cases.slice(12,15)){
    const out=await route(source.pro,source.design,c.input), regions=out.queued.map(q=>q.spec&&q.spec.region).filter(Boolean);
    assert.ok(regions.length>0,c.id+' exact named part should remain eligible');
    assert.ok(regions.every(r=>r&&r.part&&!r.everything),c.id+' must stay part-scoped');
    const expected=c.id==='U13'?'front bumper':c.id==='U14'?'hood':'roof';
    assert.ok(regions.some(r=>String(r.part).toLowerCase()===expected),c.id+' expected named target '+expected);
    positives.push({id:c.id,regions});
  }
  const whole=[];
  for(const c of oracle.cases.slice(15,18)){
    const out=await route(source.pro,source.design,c.input), regions=out.queued.map(q=>q.spec&&q.spec.region).filter(Boolean);
    if(c.id==='U17'&&!regions.some(r=>r&&r.everything===true)){
      assert.equal(out.queued.length,0,'unsupported entire-vehicle synonym must not be narrowed or falsely completed');
      assert.match(String(out.result&&out.result.text||''),/do not know a look called|cannot safely|nothing was changed/i);
      const resolved=await route(source.pro,source.design,c.input,false,true),resolvedRegions=resolved.queued.map(q=>q.spec&&q.spec.region).filter(Boolean);
      assert.ok(resolvedRegions.some(r=>r&&r.everything===true),'when the whole-scope look route resolves, it must retain entire-vehicle scope');
      whole.push({id:c.id,regions:[],note:'No-hit route safely declines this explicit entire-vehicle synonym; controlled resolve proves successful look route retains everything scope.',resolvedRegions});
    } else {
      assert.ok(regions.some(r=>r&&r.everything===true),c.id+' explicit whole-vehicle wording should remain whole vehicle');
      whole.push({id:c.id,regions});
    }
  }
  const wholeBodySupplement=await route(source.pro,source.design,'Paint the whole body blue.');
  const allPanelsSupplement=await route(source.pro,source.design,'Make all panels blue.');
  const roofChromeSupplement=await route(source.pro,source.design,'Make the roof chrome.');
  for(const [id,out] of [['S01-whole-body',wholeBodySupplement],['S02-all-panels',allPanelsSupplement],['S03-roof-chrome',roofChromeSupplement]]){
    const regions=out.queued.map(q=>q.spec&&q.spec.region).filter(Boolean);
    if(id==='S03-roof-chrome'&&regions.length)assert.ok(regions.every(r=>r&&r.part==='roof'),id+' must retain roof target');
    else if(regions.length)assert.ok(regions.every(r=>r&&r.everything===true),id+' explicit all/body scope may not narrow to a guessed subset');
    else assert.match(String(out.result&&out.result.text||''),/cannot safely|nothing was changed|clarif|do not know/i,id+' unsupported scope must remain a no-op/ask');
    rows.push({id,postInspectionSupplement:true,regions,reply:String(out.result&&out.result.text||'').slice(0,180)});
  }
  const wxCases=JSON.parse(wxBytes.toString('utf8')).cases,wxRows=[];
  for(const c of wxCases.slice(0,3)){
    const out=await route(source.pro,source.design,c.input,false,true,true);
    assert.equal(out.queued.length,0,c.id+' unsupported exclusion must block all whole-car application');
    assert.match(String(out.result&&out.result.text||''),/cannot safely infer|name a supported part/i,c.id+' should explain the unsupported relative exclusion');
    assert.ok(!out.events.includes('advisorIntent')&&!out.events.includes('resolveLook'),c.id+' must stop before broad fallbacks');
    wxRows.push({id:c.id,queue:0,events:out.events,reply:String(out.result&&out.result.text||'').slice(0,180)});
  }
  for(const c of wxCases.slice(3)){
    const out=await route(source.pro,source.design,c.input,false,true,true),regions=out.queued.map(q=>q.spec&&q.spec.region).filter(Boolean);
    assert.ok(regions.some(r=>r&&r.everything===true),c.id+' ordinary explicit whole-car/body request remains eligible');
    wxRows.push({id:c.id,regions});
  }
  const staleMulti=await route(source.pro,source.design,oracle.cases[18].input,true);
  const staleSingle=await route(source.pro,source.design,oracle.cases[19].input,true);
  assert.equal(staleMulti.queued.length,0,'stale roof in roof+hood request must block all requested zones');
  assert.equal(staleSingle.queued.length,0,'stale roof alone must not create a replacement zone');
  for(const [id,out] of [['U19',staleMulti],['U20',staleSingle]]) assert.match(String(out.result&&out.result.text||''),/clarif|exact|nothing was changed|cannot safely|supported part|name|stale|did not add/i,id+' stale owner needs honest refusal/ask copy: '+JSON.stringify({result:out.result,queued:out.queued}));
  const baseStale=await route(source.proBase,source.designBase,oracle.cases[18].input,true);
  assert.ok(baseStale.queued.length>0,'baseline comparator should expose pre-fix stale-target behavior');
  console.log(JSON.stringify({status:'PASS_WITH_LIMITS_PRIVATE_W90_SHARED_SCOPE_GUARD',frozenCases:oracle.cases.length,supplementalWholeExclusionCases:wxCases.length,ambiguousRefusals:12,exactPartPositiveControls:positives.length,explicitWholeCarControls:whole.filter(x=>x.regions.length).length,explicitWholeCarSynonymSafeNoOp:whole.some(x=>x.id==='U17'&&!x.regions.length),staleAtomicCases:2,staleBaselineQueue:baseStale.queued.length,staleCandidateQueues:[staleMulti.queued.length,staleSingle.queued.length],preGuardControlledWholeCarQueue:sectionHitBefore.queued.length,postGuardQueue:sectionHitAfter.queued.length,sourceHashes:hashes,oracleSha256:digest(oracleBytes),supplementalOracleSha256:digest(wxBytes),rows,wholeExclusions:wxRows,exactParts:positives,wholeCar:whole,providerCalls:0,nativeCalls:0,limits:['Actual W85 controller/D/E planning and queue functions ran with controlled source identity, fixtures, and tool callbacks; no zone mutation, mask proof, renderer, provider, or native application was performed.','The unpatched W85 public route was given a controlled successful look resolution; this demonstrates routing behavior, not that the live catalog contains a matching look for “section”. The W90 shared guard blocks before that resolver.','Stale-owner checks use the W85 generation-mismatch fixture; no failed source load was executed.','Whole-car positive controls verify explicit scope classification/queue target only, not geometry coverage.','W80 merge changes are outside these pinned isolated W85 inputs and remain unreviewed here.']},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});

