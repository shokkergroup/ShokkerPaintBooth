'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const proBasePath='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-pro-ai.js';
const proCandidatePath='_easy_claude_work/ai14h_w85_review/candidate/spb-pro-ai.js';
const designBasePath='_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-design.js';
const designCandidatePath='_easy_claude_work/ai14h_w85_review/candidate/spb-pro-design.js';
const editPath='_easy_claude_work/ai14h_generation3_runtime3/js/spb-pro-edit.js';
const proBase=fs.readFileSync(path.join(root,proBasePath),'utf8'),proCandidate=fs.readFileSync(path.join(root,proCandidatePath),'utf8');
const designBase=fs.readFileSync(path.join(root,designBasePath),'utf8'),designCandidate=fs.readFileSync(path.join(root,designCandidatePath),'utf8'),edit=fs.readFileSync(path.join(root,editPath),'utf8');
const oracleBytes=fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_w85_review/fresh-oracle.json'));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(digest(oracleBytes),'DED5D8A5C249024DEF2043F671D5E13498C33E4720E49ABE45BEB78F94B44971');
assert.equal(digest(Buffer.from(proBase)),'AAE99CDD02B00BDD78D1F02FED85C18BC72B82CAB9A66CEB7E0E3590EC3E8790');
assert.equal(digest(Buffer.from(proCandidate)),'E7ECEAF11B2BFC1A39E48C86A07F8DAB95EC046C678087A8168B6E8CC016F70E');
assert.equal(digest(Buffer.from(designBase)),'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8');
assert.equal(digest(Buffer.from(designCandidate)),'4648DE3231015497CC9FF816612A542097A1AD14038A7210753F6CDBFD88D832');
assert.equal(digest(Buffer.from(edit)),'99703873013E198857D9ACEAA334821098E53DCAA9D55E14DBD1EC50E58604DE');
function extract(source,name){const start=source.indexOf(`function ${name}(`);assert(start>=0,`function ${name} exists`);const brace=source.indexOf('{',start);let depth=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw new Error('unterminated '+name);}
function route(pro,designSource,text,staleRoof=false){
 const queued=[], env={palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#168a45',share_pct:10}],layers:[],zoneColours:[]};
 const dctx={console,Promise,document:{}};dctx.window=dctx;vm.createContext(dctx);vm.runInContext(designSource,dctx);vm.runInContext(edit,dctx);const D=dctx.SpbProDesign,E=dctx.SpbProEdit;
 const ctx={D,E,window:dctx,console,Promise,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,
  _busy:false,_progress:'',_skipParts:true,_absent:{},CAR:{missing:()=>[],layoutSig:()=>''},zones:[],_editReg:{},_editRegPendingBefore:{},_editRegSig:'car',
  START_OVER_RE:/^\s*(?:start over|new design)\b/i,operationCurrent:t=>!!t&&t.ok===true,operationCanceled:()=>({cancelled:true}),operationRelease(){},operationPublish:(t,fn)=>fn(),operationTools:ts=>ts,
  offlineInstructionPreflight:()=>null,elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),editPlan:t=>E.plan(t,env),offlineMaterialPlan:()=>null,advisorOwns:()=>false,captureOriginal(){},intentSpecOnly:()=>false,editYieldsToStack:()=>false,
  editEnv:()=>env,advisorIntent:()=>null,offlineIdeas:()=>null,_offlineLast:null,offlineCannot:()=>null,layerVisRequest:()=>null,NUM_FIX_RE:/$a/,NOT_ELEM_RE:/$a/,
  offlineLookAsk(){},offlineSpecAsk(){},offlinePartAsk:null,offlineElementAsk(){},offlineStartOver(){},offlineUndo(){},prepEnv:()=>Promise.resolve(env),resolveLook:()=>Promise.resolve(null),elementKinds:()=>[],exclTargets:()=>[],
  editOverlapNote:()=>'',editOverlapKinds:()=>[],exclNotes:()=>[],_elemCache:null,_elemOk:{},_taughtNow:{},editReply:(text,chips,opts)=>({offline:true,text,queue:(opts&&opts.queue)||[],tools:(opts&&opts.tools)||[]}),
  offlineRefineAsk(){},offlineHowto(){},offlineScopeReply:()=>({offline:true,text:'Nothing was changed. Please name exact supported parts.',queue:[]}),selfHelpClaim:()=>null,selfHelpResult:x=>x,
  _reqText:'',_specOnlyReq:false,_beforeImg:null,_advLast:null,_forcedIdeaCols:null,render(){},warm:()=>Promise.resolve(),markPartFollowupQueue(){},friendlyZoneError:e=>String(e),editPlural:()=>false,
  normaliseSpec:x=>x,protectDecals(){},makeTools(){return [{name:'add_zone',handler(spec){queued.push({kind:'add',spec:JSON.parse(JSON.stringify(spec))});return {region_check:{share_pct:35}};}},{name:'edit_zone',handler(args){queued.push({kind:'edit',args:JSON.parse(JSON.stringify(args))});return {};} }];},
  scopedPartProofAt:()=>null,scopedPartProofMatches:()=>false,partOwnerCurrent:()=>false,carSig:()=> 'car',scopedPartSourceNow:()=>({generation:3,committedGeneration:3,path:'A.psd',fingerprint:'file-sha256:a',width:100,height:100})
 };
 if(staleRoof)ctx.zones=[{id:'saved-roof',name:'Saved roof',muted:false,regionMask:new Uint8Array([1,0]),useRegion:true,_aiPartProv:{r:JSON.stringify({part:'roof'}),z:'2:1',l:'',e:''},_aiPartSource:{path:'A.psd',fingerprint:'file-sha256:a',generation:2,width:100,height:100}}];
 vm.createContext(ctx);
 for(const n of ['partRegionKey','editKey','editPlural','hasPriorPartIdentity','offlinePartAsk','offlineCoveredPartAsk','offlineEditAsk','offlineAskCore','queueEditZones'])vm.runInContext(extract(pro,n),ctx,{filename:'W85#'+n});
 return Promise.resolve(ctx.offlineAskCore(text,{_spbOperation:{ok:true,collection:1},noAdvisor:true})).then(result=>({result,queued,D,E}));
}
(async()=>{
const oracle=JSON.parse(oracleBytes.toString('utf8')), rows=[];
for(const c of oracle.cases.slice(0,9)){
 const before=await route(proBase,designBase,c.request),after=await route(proCandidate,designCandidate,c.request);
 assert.equal(after.queued.length,0,c.id+' ambiguous scope must not queue');
 rows.push({id:c.id,request:c.request,baselineQueue:before.queued.map(q=>q.spec&&q.spec.region),candidateQueue:after.queued.map(q=>q.spec&&q.spec.region),candidateReply:String(after.result&&after.result.text||'').slice(0,130)});
}
for(const c of [oracle.cases[9],oracle.cases[11]]){
 const after=await route(proCandidate,designCandidate,c.request);
 assert.equal(after.queued.length,1,c.id+' explicit whole-car control should remain supported');
 assert.deepEqual(after.queued[0].spec.region,{everything:true},c.id);
 rows.push({id:c.id,request:c.request,queue:after.queued.map(q=>q.spec.region),reply:String(after.result&&after.result.text||'').slice(0,100)});
}
const everythingChrome=await route(proCandidate,designCandidate,oracle.cases[10].request);
assert.equal(everythingChrome.queued.length,0,'the local parser does not support this finish-only wording; it remains safe and is not counted as a positive control');
rows.push({id:oracle.cases[10].id,request:oracle.cases[10].request,queue:everythingChrome.queued.length,note:'unsupported by the offline part-color route; no queue'});
const everythingColor=await route(proCandidate,designCandidate,'Make everything blue');
assert.equal(everythingColor.queued.length,1,'explicit everything-color positive control');assert.deepEqual(everythingColor.queued[0].spec.region,{everything:true});
const staleBase=await route(proBase,designBase,oracle.cases[12].request,true),staleCandidate=await route(proCandidate,designCandidate,oracle.cases[12].request,true);
assert.equal(staleBase.queued.length,2,'baseline fresh route exposes the stale roof + hood additions');
assert.equal(staleBase.queued.find(q=>q.spec.region.part==='roof').spec.finish,'base::gloss','baseline concretely replaces roof finish with default gloss');
assert.equal(staleCandidate.queued.length,0,'candidate refuses stale multi-part color changes atomically');
rows.push({id:'W85-13',request:oracle.cases[12].request,baseline:staleBase.queued.map(q=>({region:q.spec.region,finish:q.spec.finish,color:q.spec.color})),candidateQueue:staleCandidate.queued.length,candidateReply:String(staleCandidate.result&&staleCandidate.result.text||'').slice(0,150)});
console.log(JSON.stringify({status:'PASS_WITH_LIMITS',frozenCases:oracle.cases.length,ambiguousRefusals:9,wholeCarColorControls:3,everythingColorControl:everythingColor.queued.length,everythingChromeQueue:everythingChrome.queued.length,staleMultiPartBaselineQueue:staleBase.queued.length,staleMultiPartCandidateQueue:staleCandidate.queued.length,sourceHashes:{integration9ProAI:digest(Buffer.from(proBase)),w85ProAI:digest(Buffer.from(proCandidate)),runtime3Design:digest(Buffer.from(designBase)),w85Design:digest(Buffer.from(designCandidate)),runtime3Edit:digest(Buffer.from(edit))},rows,providerCalls:0,nativeCalls:0,limits:['Actual offlineAskCore, offlinePartAsk/offlineCoveredPartAsk, D/E planners and queueEditZones run with mocked source/zones/tool effects; nothing is applied or rendered.','The stale-owner fixture models old provenance against current generation 3; no failed PSD load is run.','The W85-11 finish-only phrase is unsupported by the exercised offline route; it safely queues nothing and is not credited as a whole-car positive.','The verified-owner reuse branch is outside this W85 route test; W80 has a separate controlled positive.']},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
