'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const paths={
 pro:'_easy_claude_work/ai14h_generation3_candidate/integration10/js/spb-pro-ai.js',
 candidatePro:'_easy_claude_work/ai14h_w88_review/candidate/spb-pro-ai.js',
 design:'_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-design.js',
 edit:'_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-edit.js',
 materials:'_easy_claude_work/ai14h_generation3_runtime2/js/spb-ai-material-controls.js',
 guard:'_easy_claude_work/ai14h_generation3_candidate/js/spb-ai-complete-instruction-guard.js',
 intentGuard:'_easy_claude_work/ai14h_w88_review/candidate/spb-ai-instruction-intent-guard.js',
 selfhelp:'_easy_claude_work/ai14h_generation3_candidate/integration10/js/spb-self-help.js',
 operation:'_easy_claude_work/ai14h_generation3_candidate/js/spb-ai-operation.js',
 lease:'_easy_claude_work/ai14h_generation3_candidate/js/spb-ai-lease.js',
 oracle:'_easy_claude_work/ai14h_w88_review/fresh-oracle.json'
};
const src={};for(const [k,p] of Object.entries(paths))src[k]=fs.readFileSync(path.join(root,p),'utf8');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const hashes={pro:'E28770330994FFC04364D0A48E88B98B69D25F9848E23D56CC1CEA07165DA713',design:'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8',edit:'99703873013E198857D9ACEAA334821098E53DCAA9D55E14DBD1EC50E58604DE',materials:'A6F50C22C2D3A4F6F9707505D66C6C30B9D2CC0E04D78F00F0D103F38A49919D',guard:'BA0AF1F9E217695ED733DDE81C8DEC1A735DD1F052E8C06B3098866D392A551C',selfhelp:'A25FEBD091B6D13EE2B3AAF3713F21A2FA720C0F240A6B042CD6DEFD023CF783',operation:'47587A1A53A35CE7E58825BAC864BD75C2421D26C19791957F57BB199A7000C6',lease:'DE276372A763310EC051DB141FCB1D601E11DBF193843E2B21A405226F782134'};
assert.equal(sha(Buffer.from(src.oracle)),'F01122CF9DBB579B8F7D88FE142DB43D466477EE0B1613852EBC44D357653E1F');
for(const k of ['pro','design','edit','materials','guard','selfhelp','operation','lease'])assert.equal(sha(Buffer.from(src[k])),hashes[k],k+' source pin');
assert.equal(sha(Buffer.from(src.candidatePro)),'829EF29E481876DAA38585D601BC0D0FFA3BC825884F6EDEC180B671E75FBFC7','private proAI candidate pin');
assert.equal(sha(Buffer.from(src.intentGuard)),'F02093D25758FD41847A1F7D2E7CC9774A4875571885F03A6CB1DC241F0E2CB4','private intent guard candidate pin');
function extract(source,name){const start=source.indexOf(`function ${name}(`);assert(start>=0,`function ${name} exists`);if(name==='selfHelpClaim'){const end=source.indexOf('function selfHelpResult(',start);assert(end>start);return source.slice(start,end).trim();}const brace=source.indexOf('{',start);let depth=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw new Error('unterminated '+name);}
function extractSend(source){const start=source.indexOf('function send(text, o)');const end=source.indexOf('function mergeMaskUndo(',start);assert(start>=0&&end>start);return source.slice(start,end).trim();}
function route(text,state={},pro=src.pro,intentGuard=false){
 const queued=[], env={palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#168a45',share_pct:10}],layers:[],zoneColours:[]};
 const w={console,Promise,document:{}};w.window=w;vm.createContext(w);for(const k of ['design','edit','materials','guard','selfhelp'])vm.runInContext(src[k],w,{filename:paths[k]});if(intentGuard)vm.runInContext(src.intentGuard,w,{filename:paths.intentGuard});
 const D=w.SpbProDesign,E=w.SpbProEdit;
 const ctx={D,E,window:w,console,Promise,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,Date,
  _busy:false,_progress:'',_skipParts:true,_absent:{},CAR:{missing:()=>[],layoutSig:()=>'',hasParts:()=>false},zones:state.zones||[],_editReg:state.editReg||{},_editRegPendingBefore:{},_editRegSig:state.car||'car-a',
  START_OVER_RE:/^\s*(?:start over|new design)\b/i,operationCurrent:t=>!!t&&t.ok===true,operationCanceled:()=>({cancelled:true}),operationRelease(){},operationPublish:(t,fn)=>fn(),operationTools:ts=>ts,
  elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),editPlan:t=>E.plan(t,env),advisorOwns:()=>false,captureOriginal(){},intentSpecOnly:()=>false,editYieldsToStack:()=>false,
  editEnv:()=>env,advisorIntent:()=>null,offlineIdeas:()=>null,_offlineLast:null,offlineCannot:()=>null,layerVisRequest:()=>null,NUM_FIX_RE:/$a/,NOT_ELEM_RE:/$a/,
  offlineLookAsk(){},offlineSpecAsk(){},offlinePartAsk:null,offlineElementAsk(){},offlineStartOver(){},offlineUndo(){},prepEnv:()=>Promise.resolve(env),resolveLook:()=>Promise.resolve(null),elementKinds:()=>[],exclTargets:()=>[],
  editOverlapNote:()=>'',editOverlapKinds:()=>[],exclNotes:()=>[],_elemCache:null,_elemOk:{},_taughtNow:{},editReply:(text,chips,opts)=>({offline:true,text,queue:(opts&&opts.queue)||[],tools:(opts&&opts.tools)||[]}),
  offlineRefineAsk(){},offlineHowto:()=>null,offlineScopeReply:()=>({offline:true,text:'Nothing was changed. Name one exact supported part.',queue:[]}),selfHelpResult:x=>x,
  _reqText:'',_specOnlyReq:false,_beforeImg:null,_advLast:null,_forcedIdeaCols:null,render(){},warm:()=>Promise.resolve(),markPartFollowupQueue(){},friendlyZoneError:e=>String(e),editPlural:()=>false,operationRefreshDocument(){},
  normaliseSpec:x=>x,protectDecals(){},makeTools(){return [{name:'add_zone',handler(spec){queued.push({kind:'add',spec:JSON.parse(JSON.stringify(spec))});return {region_check:{share_pct:35}};}},{name:'edit_zone',handler(args){queued.push({kind:'edit',args:JSON.parse(JSON.stringify(args))});return {};}}];},
  scopedPartProofAt:()=>null,scopedPartProofMatches:()=>false,partOwnerCurrent:()=>false,carSig:()=>state.car||'car-a',scopedPartSourceNow:()=>state.source||null,
  operationDocument:()=>({ok:true}),operationAcquire:()=>({ok:true,collection:1}),operationResultCurrent:()=>true,operationRelease(){},
  _spbOperation:null
 };
 vm.createContext(ctx);
 const names=['partRegionKey','editKey','editPlural','hasPriorPartIdentity','currentPartOwnerVerifiedForRegion','explicitCurrentPaintRequest','unprovedCurrentPaintPartAdd','selfHelpClaim','offlineInstructionPreflight','offlineMaterialPlan','offlineMaterialAsk','offlinePartAsk','offlineCoveredPartAsk','offlineEditAsk','offlineAskCore','offlineAsk','queueEditZones'];
 if(pro.includes('function normalizeOfflineInstruction('))vm.runInContext(extract(pro,'normalizeOfflineInstruction'),ctx,{filename:'W88#normalizeOfflineInstruction'});else ctx.normalizeOfflineInstruction=x=>String(x||'');
 for(const n of names){try{vm.runInContext(extract(pro,n),ctx,{filename:'W88#'+n});}catch(e){if(n==='hasPriorPartIdentity'&& !pro.includes('function hasPriorPartIdentity('))continue;throw e;}}
 if(pro.includes('function send(text, o)'))vm.runInContext(extractSend(pro),ctx,{filename:'W88#typedSend'});
 return Promise.resolve(ctx.offlineAsk(text,{_spbOperation:{ok:true,collection:1},noAdvisor:true})).then(result=>({result,queued,D,E,ctx}));
}
(async()=>{
 const oracle=JSON.parse(src.oracle);assert.equal(oracle.cases.length,20);
 const rows=[];
 for(const c of oracle.cases){
  if(c.state){rows.push({id:c.id,coverage:'stateful expectation frozen, but not exercised because this harness does not emulate source/owner commit state'});continue;}
  const base=await route(c.request),candidate=await route(c.request,{},src.candidatePro,true);
  rows.push({id:c.id,baselineQueued:base.queued.length,candidateQueued:candidate.queued.length,baselineQueue:base.queued.map(q=>({kind:q.kind,region:q.spec&&q.spec.region||null,finish:q.spec&&q.spec.finish||null,shift:q.args&&q.args.spec_shift||null})),candidateQueue:candidate.queued.map(q=>({kind:q.kind,region:q.spec&&q.spec.region||null,finish:q.spec&&q.spec.finish||null,shift:q.args&&q.args.spec_shift||null})),baselineReply:String(base.result&&base.result.text||'').slice(0,180),candidateReply:String(candidate.result&&candidate.result.text||'').slice(0,180)});
 }
 const controls=[];for(const text of ['Can you make the roof blue?','Apply this request: make only the roof blue.']){const base=await route(text),got=await route(text,{},src.candidatePro,true);controls.push({request:text,baselineQueued:base.queued.length,candidateQueued:got.queued.length,regions:got.queued.map(q=>q.spec&&q.spec.region||null),reply:String(got.result&&got.result.text||'').slice(0,150)});}
 const byId=Object.fromEntries(rows.map(r=>[r.id,r]));
 assert.equal(byId['imperative-roof-color'].candidateQueued,1);assert.deepEqual(byId['imperative-roof-color'].candidateQueue[0].region,{part:'roof'});
 for(const id of ['hypothetical-if','quoted-user-ask','explicit-guide','compound-missing-target']){assert(byId[id].baselineQueued>0,id+' baseline must reproduce the route failure');assert.equal(byId[id].candidateQueued,0,id+' candidate must refuse without queuing');assert.match(byId[id].candidateReply,/Nothing was changed/);}
 assert.equal(byId['direct-clearcoat-unitless'].candidateQueued,0);assert.match(byId['direct-clearcoat-unitless'].candidateReply,/clearcoat on the roof.*points/i);
 for(const id of ['selective-roughness-lock','two-channel-two-amounts','two-channel-one-target','contradictory-channel','mixed-color-and-material','material-without-target','part-with-unknown-alias'])assert.equal(byId[id].candidateQueued,0,id+' must not partially apply unsupported material intent');
 assert(controls.every(x=>x.candidateQueued===1&&x.regions[0]&&x.regions[0].part==='roof'),'direct/explicit active controls remain scoped and actionable');
 const sendAt=src.candidatePro.indexOf('function send(text, o)'),preflightAt=src.candidatePro.indexOf('offlineInstructionPreflight(text)',sendAt),askAt=src.candidatePro.indexOf('var p = ask(text, o)',sendAt);
 assert(sendAt>=0&&preflightAt>sendAt&&askAt>preflightAt,'typed send retains the read-only preflight before ask');
 const sendRows=[];for(const id of ['hypothetical-if','quoted-user-ask','explicit-guide']){const request=oracle.cases.find(c=>c.id===id).request,probe=await route(request,{},src.candidatePro,true);let finishes=[],askCalls=0;probe.ctx.finish=(r,t,k)=>finishes.push({text:String(r&&r.text||''),input:t,kind:k});probe.ctx.ask=()=>{askCalls++;return Promise.resolve({queue:[]});};probe.ctx.send(request);assert.equal(askCalls,0,id+' typed SEND must stop before ask');assert.equal(finishes.length,1,id+' typed SEND returns one guidance response');assert.match(finishes[0].text,/Nothing was changed/);sendRows.push({id,finish:finishes[0].text,askCalls});}
 console.log(JSON.stringify({status:'PASS_WITH_LIMITS_PRIVATE_CANDIDATE',frozenCases:oracle.cases.length,routeCasesExecuted:16,statefulCasesUnexercised:4,sourceHashes:Object.fromEntries(Object.entries(paths).map(([k,p])=>[k,sha(Buffer.from(src[k]))])),rows,imperativeControls:controls,typedSendPreflightBeforeAsk:true,typedSendResults:sendRows,providerCalls:0,nativeCalls:0,limits:['Actual offlineAsk, offlineAskCore and D/E planners run with controlled terminal add/edit callbacks; no apply/render/native effects are executed.','The four source/owner state cases are not simulated by this harness and are explicitly unexercised; parent native/source acceptance remains separate.','The actual typed SEND body runs with controlled finish/ask callbacks; read-only prompts finish with guidance and never call ask.','This private candidate changes only preflight intent classification plus an explicit user authorization wrapper; unknown vehicle geometry is never inferred.']},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
