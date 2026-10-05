'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const paths={
 pro:'_easy_claude_work/ai14h_w121_guidance_successor/candidate/spb-pro-ai.js',
 selfhelp:'_easy_claude_work/ai14h_w121_guidance_candidate/spb-self-help.js',
 receipt:'_easy_claude_work/ai14h_generation3_runtime11/js/spb-ai-receipt-explainer.js',
 intent:'_easy_claude_work/ai14h_generation3_runtime11/js/spb-ai-instruction-intent-guard.js',
 complete:'_easy_claude_work/ai14h_generation3_runtime11/js/spb-ai-complete-instruction-guard.js',
 strict:'_easy_claude_work/ai14h_final_source_identity_candidate/browser-file-v2/spb-pro-ai.js',
 oracle:'_easy_claude_work/ai14h_w121_guidance_review/fresh-oracle.json'
};
const bytes=Object.fromEntries(Object.entries(paths).map(([k,p])=>[k,fs.readFileSync(path.join(root,p))]));
const src=Object.fromEntries(Object.entries(bytes).map(([k,b])=>[k,b.toString('utf8')]));
const oracleText=src.oracle,oracle=JSON.parse(oracleText),sha=s=>crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
assert.equal(sha(src.pro),'AC170B8E9DAB44F8C61B044C16A14A98974412CC403601D06196B471FF574535','W121 public controller pin');
assert.equal(sha(src.selfhelp),'E230A121127FC6B32C451C630028D3D2D10461B67819BF50F2B148195DB8DF4D','actual E230 self-help pin');
assert.equal(sha(src.receipt),'25ABA5EE85E9C9FB7EFE3603FCE22B140CCB09D2CBD09A9303AC6AB00530EAC3','receipt helper pin');
assert.equal(sha(src.intent),'3267DC263CF85BCB34B55588997ACBA737F4A47E7BDDE490FACE4D9D6271FB60','instruction intent guard pin');
assert.equal(sha(src.complete),'BA0AF1F9E217695ED733DDE81C8DEC1A735DD1F052E8C06B3098866D392A551C','complete instruction guard pin');
assert.equal(sha(src.strict),'FB63F5906E1C9FC9D49150F571D64FDE640E0A4630319C418FE4F9C2E7E5413A','strict identity/preflight baseline pin');
assert.equal(sha(oracleText),'7A190A0F670A0BDE395334B426A653DD7486B9355B642F06795BD1B575478099','fresh W121 semantic oracle pin');
assert.equal(oracle.cases.length,24);

function extract(s,n){const a=s.indexOf(`function ${n}(`);assert(a>=0,`missing ${n}`);const b=s.indexOf('{',a);let d=0,q=null,ln=false,bl=false,esc=false;for(let i=b;i<s.length;i++){const c=s[i],x=s[i+1];if(ln){if(c==='\n')ln=false;continue;}if(bl){if(c==='*'&&x==='/'){bl=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&x==='/'){ln=true;i++;continue;}if(c==='/'&&x==='*'){bl=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;else if(c==='}'&&--d===0)return s.slice(a,i+1);}throw Error('unterminated '+n);}
for(const n of ['normalizeOfflineInstruction','offlineInstructionPreflight'])assert.equal(extract(src.pro,n),extract(src.strict,n),n+' remains byte-identical to strict fb63 baseline');

function fixture(c,configured){
 const state=/^stale-receipt/.test(c.id)?'layered':/tga|flat/i.test(c.id+c.request)?'flat':/psd|hidden|nested|layer/i.test(c.id+c.request)?'layered':'none';
 const gen=23,loaded=state!=='none',layers=state==='layered'?[{id:'paint',name:'Car Paint',visible:true,img:{width:2048,height:2048}},{id:'nested',name:'Nested Group',visible:true,children:[{id:'hidden-wire',name:'Wire',visible:false}]}]:[];
 const w={console,Promise,Date,Math,JSON,Object,Array,String,Number,RegExp,Error,Uint8Array,
  document:{body:{classList:{contains:()=>false}},getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]},zones:[],_psdLayers:layers,
  paintImageData:state==='flat'?{width:2048,height:2048,data:new Uint8Array(4)}:null,_psdPath:state==='layered'?'C:/fixture/selected.psd':null,
  selectedZoneIndex:-1,zoneSourceLayerIds:()=>[],_spbLayerRev:0,SpbProCar:{roles:()=>[],map:()=>null,missing:()=>[]},
  SpbAI:{cached:()=>({configured:!!configured,provider:configured?'blocked-provider':'',model:configured?'blocked-model':''})},
  SpbAiLease:{internal:()=>true},SPBSourceLoadTransaction:{getGeneration:()=>gen,getCommittedGeneration:()=>loaded?gen:0,getCommittedKind:()=>state==='layered'?'layered':state==='flat'?'flat':'',getCommittedPath:()=>loaded?(state==='layered'?'C:/fixture/selected.psd':'C:/fixture/selected.tga'):'',getCommittedFingerprint:()=>loaded?'file-sha256:'+String(gen).padStart(64,'0'):'',isLoading:()=>false,isCommitted:()=>loaded},fetch:undefined};
 w.window=w;vm.createContext(w);
 for(const k of ['selfhelp','receipt','intent','complete'])vm.runInContext(src[k],w,{filename:paths[k]});
 const log=[];if(c.id==='stale-receipt'||c.id==='stale-receipt-retry')log.push({role:'ai',status:'applied',lines:['Edited the roof'],text:'Edited the roof',notes:[],_spbOperation:{ok:true,document:{sourceGeneration:22},revision:1,collection:1}});
 Object.assign(w,{_log:log,_busy:false,_ctl:null,_envMemo:null,_partMemoryWarmAttemptTicket:null,_absent:{},_skipParts:false,
  operationCurrent:t=>!!t&&t.ok===true&&(!t.document||t.document.sourceGeneration===gen),operationTicket:v=>v&&v._spbOperation||null,
  operationManager:()=>({sameDocument:t=>!!t&&t.document&&t.document.sourceGeneration===gen,ready(){},owns:()=>true,owner:()=>null}),operationRevision:()=>1,
  operationRelease(){},operationBind:v=>v,operationStart:()=>({ok:true,document:{sourceGeneration:gen},revision:1,collection:1}),
  operationCanceled:()=>({cancelled:true,stale:true,queue:[]}),offlineAsk:()=>Promise.resolve({offline:true,queue:[],text:'No local edit was run in this guidance harness.',howto:true}),
  editPlan:()=>null,advisorIntent:()=>null,advisorOwns:()=>false,layerVisRequest:()=>null,offlineMaterialPlan:()=>null,
  offlinePartAsk:()=>Promise.resolve({offline:true,queue:[],text:'controlled local part route'}),logMiss(){}});
 for(const n of ['normalizeOfflineInstruction','selfHelpResult','unexecutedSuggestionReply','w121PsdTgaHelp','contextualHelpReply','offlineInstructionPreflight','ask'])vm.runInContext(extract(src.pro,n),w,{filename:paths.pro+':'+n});
 w.spbProAI={ask:w.ask};let providerAttempts=0,downstreamCalls=0;
 w.askCore=()=>{providerAttempts++;throw Error('provider blocked by semantic review harness');};
 w.askForTicket=(text,opts)=>{downstreamCalls++;return Promise.resolve({offline:true,text:'controlled downstream action handoff',queue:[],calls:0,usage:{cost:0}});};
 return {w,providerAttempts:()=>providerAttempts,downstreamCalls:()=>downstreamCalls,state};
}

const forbidden={
 'flat-vs-psd-layers':[/reconstruct(?:s|ed)? (?:the )?original layers/i,/recover(?:s|ed)? (?:the )?source psd layers exactly/i],
 'flat-tga-layer-recovery':[/recover(?:s|ed)? (?:the )?original photoshop layers/i,/automatically reconstruct/i],
 'tga-alpha-intent':[/automatically (?:make|sets?) .*transparent/i,/32.bit tga means transparent/i],
 'tga-alpha-edit':[/click the alpha tool/i,/automatically edit alpha/i],
 'offline-capability':[/every feature works offline/i,/external ai is required/i],
 'hidden-psd-layers':[/hidden layers are always discarded/i,/all hidden layers are preserved/i],
 'nested-psd-groups':[/nested groups are always preserved/i,/exactly preserves nested group visibility/i],
 'missing-source':[/edit will succeed without a source/i,/source is optional/i],
 'stale-receipt':[/old receipt proves this source/i,/still verified after switching/i],
 'stale-receipt-retry':[/late result applies to the new source/i,/safe to use on the replacement source/i],
 'unknown-finish-name':[/black ice nebula is (?:a )?(?:chrome|matte|pearl|carbon)/i,/catalog item is black ice nebula/i],
 'unknown-finish-apply':[/black ice nebula was applied/i,/completed successfully/i],
 'teach-missing-roof':[/automatically detects exact roof geometry/i,/learns roof coordinates permanently/i],
 'teach-part-unverified':[/drag the roof boundary tool/i,/automatic roof boundary editor/i],
 'uv-geometry-from-flat':[/flat preview identifies exact uv boundaries/i,/automatically recover.*uv/i],
 'source-original-modification':[/edits the original psd in place/i,/changes the original tga automatically/i],
 'photoshop-automation':[/opens photoshop automatically/i,/rebuilds a layered psd for you/i],
 'automatic-verification':[/verifies every requested pixel and material/i,/all edits are pixel-perfect verified/i],
 'source-paint-meaning':[/source paint keeps your current authored solid color/i,/source paint means keep the current solid hex/i]
};

(async()=>{
 const rows=[],issues=[],semanticGaps=[];
 const grade={
  'flat-vs-psd-layers':'useful', 'flat-tga-layer-recovery':'wrong-topic', 'tga-alpha-intent':'partial-safe', 'tga-alpha-edit':'partial-safe',
  'offline-capability':'useful', 'online-vs-offline':'wrong-topic', 'hidden-psd-layers':'wrong-topic', 'nested-psd-groups':'wrong-topic',
  'missing-source':'useful', 'stale-receipt':'useful-with-stale-fixture', 'stale-receipt-retry':'safe-but-nonresponsive',
  'unknown-finish-name':'wrong-topic', 'unknown-finish-apply':'partial-safe', 'teach-missing-roof':'useful', 'teach-part-unverified':'partial-useful',
  'uv-geometry-from-flat':'partial-safe', 'source-original-modification':'possible-unsupported-export-claim', 'photoshop-automation':'partial-safe',
  'automatic-verification':'misrouted-action', 'source-paint-meaning':'useful'
 };
 for(const c of oracle.cases){
  const repeats=c.kind==='information'?[false,true]:[false];
  for(const configured of repeats){
   const f=fixture(c,configured),r=await f.w.spbProAI.ask(c.request,{offline:true}),text=String(r&&r.text||''),topic=r&&r.selfHelp&&r.selfHelp.topic||'',queue=(r&&r.queue||[]).length;
   const row={id:c.id,configured,kind:c.kind,topic,grade:grade[c.id]||'action-control',howto:!!(r&&r.howto),queue,downstreamCalls:f.downstreamCalls(),providerAttempts:f.providerAttempts(),text:text.slice(0,1100)};rows.push(row);
   if(queue||f.providerAttempts())issues.push(c.id+(configured?'/configured':'/offline')+': queue or provider attempt');
   if(c.kind==='information'){
    if(!r||!r.howto)issues.push(c.id+(configured?'/configured':'/offline')+': answer did not retain read-only classification');
    if(f.downstreamCalls())issues.push(c.id+(configured?'/configured':'/offline')+': information query reached downstream edit route');
    for(const re of forbidden[c.id]||[])if(re.test(text))issues.push(c.id+': unsupported claim matched '+re);
    if(grade[c.id]&&grade[c.id]!=='useful'&&grade[c.id]!=='useful-with-stale-fixture')semanticGaps.push(c.id+': '+grade[c.id]);
   }else{
    if(r&&r.howto)issues.push(c.id+': explicit action was turned into a guidance answer');
    if(!r||!(f.downstreamCalls()===1||queue===0&&r.text))issues.push(c.id+': action was neither safely handed off nor clarified');
   }
  }
 }
 const infoRows=rows.filter(r=>r.kind==='information'),actionRows=rows.filter(r=>r.kind==='action');
 const uniqueSemanticGaps=Array.from(new Set(semanticGaps));
 const gradeCounts={};rows.forEach(r=>{gradeCounts[r.grade]=(gradeCounts[r.grade]||0)+1;});
 const report={work_item:'W121 independent PSD/TGA guidance semantics review',status:issues.length?'BLOCKED_ROUTING_OR_UNSUPPORTED_CLAIM':uniqueSemanticGaps.length?'REVIEW_SEMANTIC_GAPS':'PASS_PRIVATE_SEMANTICS',pins:{controller:paths.pro,controllerSha256:sha(src.pro),E230SelfHelp:paths.selfhelp,E230SelfHelpSha256:sha(src.selfhelp),receipt:paths.receipt,receiptSha256:sha(src.receipt),intentGuard:paths.intent,intentGuardSha256:sha(src.intent),completeGuard:paths.complete,completeGuardSha256:sha(src.complete),strictFb63:paths.strict,strictFb63Sha256:sha(src.strict),oracle:paths.oracle,oracleSha256:sha(oracleText)},counts:{freshCases:oracle.cases.length,informationRoutes:infoRows.length,actionControls:actionRows.length,informationAnswers:infoRows.filter(r=>r.howto).length,informationDownstreamCalls:infoRows.reduce((n,r)=>n+r.downstreamCalls,0),informationQueues:infoRows.reduce((n,r)=>n+r.queue,0),providerAttempts:rows.reduce((n,r)=>n+r.providerAttempts,0),semanticGapCases:uniqueSemanticGaps.length,gradeCounts,routingOrClaimIssues:issues.length},rows,semanticGaps:uniqueSemanticGaps,issues,limits:['Runs the pinned real public ask(), W121 contextual helper and E230 self-help module in a VM. Source/layer/receipt metadata are controlled fixtures; downstream action route and provider are blocked/controlled boundaries, with no paint application.','No PSD/TGA bytes, hidden/nested group pixels, geometry detection, actual file changes, native UI, provider, or server are exercised. Report grades answers against the fresh semantic constraints; it does not claim importer support beyond pinned source/documented answer text.']};
 const out=path.join(root,'_easy_claude_work/ai14h_w121_guidance_successor/ai_w121_guidance_successor_24_contract_report.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,counts:report.counts,semanticGaps:uniqueSemanticGaps,issues,report:'_easy_claude_work/ai14h_w121_guidance_successor/ai_w121_guidance_successor_24_contract_report.json',rows:rows.map(r=>({id:r.id,configured:r.configured,grade:r.grade,topic:r.topic,howto:r.howto,downstream:r.downstreamCalls,provider:r.providerAttempts,text:r.text.slice(0,220)}))},null,2));
 if(issues.length)process.exitCode=1;
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
