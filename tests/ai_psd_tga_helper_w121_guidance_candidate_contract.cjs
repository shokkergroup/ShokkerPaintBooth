'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),base='_easy_claude_work/ai14h_generation3_audit/frozen-runtime11/js/';
const files={pro:'_easy_claude_work/ai14h_w121_guidance_candidate/spb-pro-ai.js',selfhelp:base+'spb-self-help.js',receipt:base+'spb-ai-receipt-explainer.js',intent:base+'spb-ai-instruction-intent-guard.js'};
const oraclePath='_easy_claude_work/ai14h_w121_psd_tga_helper_scenarios/fresh-oracle.json',manifestPath='_easy_claude_work/ai14h_customer_psd_tga_inventory/manifest.json';
const src=Object.fromEntries(Object.entries(files).map(([k,p])=>[k,fs.readFileSync(path.join(root,p),'utf8')])),oracleText=fs.readFileSync(path.join(root,oraclePath),'utf8'),oracle=JSON.parse(oracleText),manifestText=fs.readFileSync(path.join(root,manifestPath),'utf8'),manifest=JSON.parse(manifestText),sha=s=>crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
assert.equal(sha(src.pro),'884FE1E2A8F039021D3E202ED0876F81F1BD866541DC1B38A065BD4E5E117C77','pinned W121 private candidate');
assert.equal(sha(src.selfhelp),'E230A121127FC6B32C451C630028D3D2D10461B67819BF50F2B148195DB8DF4D','pinned self-help');
assert.equal(sha(src.receipt),'25ABA5EE85E9C9FB7EFE3603FCE22B140CCB09D2CBD09A9303AC6AB00530EAC3','pinned receipt helper');
assert.equal(sha(src.intent),'3267DC263CF85BCB34B55588997ACBA737F4A47E7BDDE490FACE4D9D6271FB60','pinned intent guard');
assert.equal(sha(manifestText),oracle.sourceFixtureManifestSha256,'fixture manifest pin');
assert.equal(sha(oracleText),'BD73219E143CC2B62E0053F67144C4CE19F4C4BC4FF5759D767A47C922809049','fresh oracle pin');
function extract(s,n){const a=s.indexOf(`function ${n}(`);assert(a>=0,`${n} exists`);const b=s.indexOf('{',a);let d=0,q=null,ln=false,bl=false,esc=false;for(let i=b;i<s.length;i++){const c=s[i],x=s[i+1];if(ln){if(c==='\n')ln=false;continue;}if(bl){if(c==='*'&&x==='/'){bl=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&x==='/'){ln=true;i++;continue;}if(c==='/'&&x==='*'){bl=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;if(c==='}'&&--d===0)return s.slice(a,i+1);}throw Error(`unterminated ${n}`);}
function fixture(c){
 const st=c.state||{},gen=Number(st.sourceGeneration||9),source=String(st.source||'none');
 let layers=[];
 if(Array.isArray(st.layers))layers=st.layers.map((x,i)=>({id:'fixture-'+i,name:x.name||('Layer '+i),visible:x.visible!==false,locked:!!x.locked,children:x.children||[],img:{width:2048,height:2048}}));
 else if(source==='layered')layers=[{id:'paint',name:'Car Paint',visible:true,img:{width:2048,height:2048}},{id:'template',name:'Wire',visible:false,img:{width:2048,height:2048}}];
 const isFlat=/tga|flat/.test(source),isLoaded=source!=='none';
 const w={console,Promise,Date,Math,JSON,Object,Array,String,Number,RegExp,Error,Uint8Array,
   document:{body:{classList:{contains:()=>false}},getElementById:()=>null},zones:[],_psdLayers:layers,
   paintImageData:isFlat?{width:2048,height:2048,data:new Uint8Array(4)}:null,_psdPath:source==='layered'?(st.sourcePath||(c.fixture&&c.fixture.path)||'C:/fixture/current.psd'):null,
   selectedZoneIndex:-1,zoneSourceLayerIds:()=>[],_spbLayerRev:0,
   SpbProCar:{roles:()=>[],map:()=>null,missing:()=>[]},
   SpbAI:{cached:()=>({configured:!!c.configured,provider:c.configured?'mcp-test':null,model:c.configured?'blocked-test':null})},
   SpbAiLease:{internal:()=>true},
   SPBSourceLoadTransaction:{getGeneration:()=>gen,getCommittedGeneration:()=>isLoaded?gen:0,getCommittedKind:()=>source==='layered'?'layered':isFlat?'flat':'',getCommittedPath:()=>isLoaded?(st.sourcePath||(c.fixture&&c.fixture.path)||'C:/fixture/current.tga'):'',getCommittedFingerprint:()=>isLoaded?'file-sha256:'+String(gen).padStart(64,'0'):'',isLoading:()=>false,isCommitted:()=>isLoaded},
   fetch:undefined
 };
 w.window=w;vm.createContext(w);
 for(const k of ['selfhelp','receipt','intent'])vm.runInContext(src[k],w,{filename:files[k]});
 const log=[];if(st.receipt){const op=st.receipt;log.push({role:'ai',lines:op.lines||[],text:(op.lines||[]).join('\n'),notes:[],_spbOperation:{ok:true,document:{sourceGeneration:Number(op.sourceGeneration||gen)},revision:1,collection:1},...(op.status==='undone'?{undone:true}:{})});}
 Object.assign(w,{_log:log,_busy:false,_ctl:null,_envMemo:null,_partMemoryWarmAttemptTicket:null,
   operationCurrent:t=>!!t&&t.ok===true&&(!t.document||t.document.sourceGeneration===gen),
   operationTicket:v=>v&&v._spbOperation||null,
   operationManager:()=>({sameDocument:t=>!!t&&t.document&&t.document.sourceGeneration===gen,ready(){},owns:()=>true,owner:()=>null}),
   operationRevision:()=>1,operationRelease(){},operationBind:v=>v,
   operationStart:()=>({ok:true,document:{sourceGeneration:gen},revision:1,collection:1}),
   operationCanceled:()=>({cancelled:true,stale:true,queue:[]}),
   offlineAsk:()=>Promise.resolve({offline:true,queue:[],text:'controlled offline fallback',howto:true})});
 for(const n of ['normalizeOfflineInstruction','selfHelpResult','unexecutedSuggestionReply','w121PsdTgaHelp','contextualHelpReply','offlineInstructionPreflight','ask'])vm.runInContext(extract(src.pro,n),w,{filename:files.pro});
 w.spbProAI={ask:w.ask};let providerAttempts=0;w.askCore=()=>{providerAttempts++;throw new Error('provider path blocked by W121 harness');};let askForTicketCalls=[];
 w.askForTicket=(text,opts)=>{askForTicketCalls.push({text,options:opts});return Promise.resolve({offline:true,text:'controlled downstream local route; no paint applied',queue:[],usage:{cost:0},calls:0,model:'test-stub'});};
 return {w,askForTicketCalls,get providerAttempts(){return providerAttempts},loaded:isLoaded};
}
const semanticReview={
 'offline-capability-no-provider':['useful','Supported local how-to/edit boundary; no provider required for supported local work.'],
 'online-vs-offline-boundary':['useful','Distinguishes external MCP routing/charges from supported local help and edits.'],
 'unknown-flat-car-identification':['useful','Says no named-part proof exists, offers manual current-image selection only if controls support it; no geometry claim.'],
 'teach-part-howto':['useful','Truthfully frames manual zone/selection and visual-mask inspection without asserting learned geometry.'],
 'unknown-finish-lookup':['useful','Refuses to invent an unknown catalog look and directs catalog search.'],
 'unknown-color-source-inference':['useful','Does not claim color from file metadata; says no visual inspection was performed.'],
 'question-hypothetical-no-execute':['useful','Read-only hypothetical; no downstream action.'],
 'explicit-action-control-owner':['useful','Polite imperative reaches exactly one controlled local handoff; no apply/provider.'],
 'explicit-action-refuse-unknown-part':['useful','Refuses unverified roof action and states current part map is needed; no handoff.'],
 'grouped-layer-discovery':['useful','Gives parent/child expansion, visibility, and optional filter guidance without changing state.'],
 'hidden-layer-selectability':['useful','Explains hidden ancestor/child visibility and lock/selection checks; no state changes.'],
 'imported-spec-map-identification':['useful','Directs user to inspect imported layers and actual spec previews; no claim that import mapping is known.'],
 'tga-alpha-is-not-spec-proof':['useful','Clearly separates alpha/header metadata from verified material-channel meaning.'],
 'rle-alpha-uncertainty':['useful','Does not guarantee loader or alpha semantics from RLE/header metadata.'],
 'saved-raster-vs-original-psd':['useful','Distinguishes project pixels/layers from original PSD bytes and path.'],
 'unsaved-edit-receipt-vs-durable':['partial','Explains unsaved project versus source file but does not verify the actual controlled applied receipt.'],
 'changed-source-stale-owner':['useful','Treats old-source region as inert pending current-source/mask proof.'],
 'missing-source-location':['useful','States path cannot be read from answer and gives Source Paint load controls.'],
 'cold-reopen-layer-state':['useful','Distinguishes embedded project layer state from original PSD bytes and current proof.'],
 'latest-actual-completion-after-source-change':['partial','Question goes through controlled downstream stub; real receipt-helper stale source behavior is not demonstrated here.']
};
(async()=>{
 const rows=[],routeIssues=[];
 for(const c of oracle.cases){const f=fixture(c);const result=await f.w.spbProAI.ask(c.input,{offline:true});const row={id:c.id,input:c.input,configured:c.configured,state:c.state,fixture:c.fixture||null,howto:!!(result&&result.howto),selfHelpTopic:result&&result.selfHelp&&result.selfHelp.topic||'',queue:(result&&result.queue||[]).length,askForTicketCalls:f.askForTicketCalls.length,providerAttempts:f.providerAttempts,error:result&&result.error&&result.error.message||'',text:String(result&&result.text||'').slice(0,1400),semanticGrade:semanticReview[c.id][0],semanticNote:semanticReview[c.id][1]};rows.push(row);
   if(row.queue||row.providerAttempts)routeIssues.push(c.id+': unexpected queue or provider attempt');
   if(c.id==='question-hypothetical-no-execute'&&row.askForTicketCalls)routeIssues.push(c.id+': hypothetical escaped read-only help into downstream local route');
   if(c.id==='explicit-action-control-owner'&&(row.queue||row.providerAttempts||row.askForTicketCalls!==1))routeIssues.push(c.id+': expected one controlled local action handoff, zero paint/provider effects');
   if(row.providerAttempts)routeIssues.push(c.id+': provider path was attempted despite the harness block');
 }
 const counts={cases:rows.length,useful:rows.filter(r=>r.semanticGrade==='useful').length,partial:rows.filter(r=>r.semanticGrade==='partial').length,failure:rows.filter(r=>r.semanticGrade==='failure').length,howto:rows.filter(r=>r.howto).length,nonemptyQueues:rows.filter(r=>r.queue).length,askForTicketCalls:rows.reduce((n,r)=>n+r.askForTicketCalls,0),providerAttempts:rows.reduce((n,r)=>n+r.providerAttempts,0),controlledEffects:0,routeIssues:routeIssues.length};
 const report={workItem:'W121 customer PSD/TGA contextual helper route replay',status:routeIssues.length?'ROUTE_GAPS':'SEMANTIC_REVIEW_COMPLETE_WITH_GAPS',source:{controller:files.pro,sha256:sha(src.pro),selfHelp:sha(src.selfhelp),receipt:sha(src.receipt),intentGuard:sha(src.intent),designBaseline:'_easy_claude_work/ai14h_generation3_audit/frozen-runtime11/js/spb-pro-design.js',designBaselineSha256:'4648DE3231015497CC9FF816612A542097A1AD14038A7210753F6CDBFD88D832'},oracle:{path:oraclePath,sha256:sha(oracleText),cases:oracle.cases.length,frozenBeforeAnswers:true},fixtureManifest:{path:manifestPath,sha256:sha(manifestText),selectedSamples:manifest.samples.length},counts,rows,routeIssues,limits:['Actual W119 public ask() and its contextual/preflight dependencies are extracted and run in a VM; provider/config metadata is controlled false/true. Provider-facing askCore is blocked by a throwing stub; askForTicket is a controlled downstream local-route stub that never invokes a provider or applies paint. Handoff counts therefore show public dispatch, not successful offline planning or action.','Customer fixtures are metadata only (PSD layer counts and TGA headers); state and receipts are controlled fixtures. No source bytes, masks, spec maps, CAR part geometry, save/open or pixel semantics are inferred from the inventory.','No provider, native application, HTTP server, browser or paint application was called.']};
 const out='docs/handoff_reports/AI_HELPER_14H_PSD_TGA_HELPER_W121_CANDIDATE_REPLAY_2026-10-04.json';fs.writeFileSync(path.join(root,out),JSON.stringify(report,null,2)+'\n');
 assert.equal(rows.length,20); console.log(JSON.stringify({status:report.status,cases:rows.length,grades:{useful:counts.useful,partial:counts.partial,failure:counts.failure},howto:counts.howto,askForTicketCalls:counts.askForTicketCalls,providerAttempts:counts.providerAttempts,routeIssues,report:out},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
