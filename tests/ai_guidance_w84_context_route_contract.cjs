'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const helperPath='_easy_claude_work/ai14h_w84_review/tuned_candidate/spb-self-help.js';
const knowledgePath='_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/js/spb-ai-knowledge.js';
const controllerBase='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-pro-ai.js';
const controllerPath='_easy_claude_work/ai14h_w84_review/controller_candidate/spb-pro-ai.js';
const oraclePath='_easy_claude_work/ai14h_w84_review/fresh-context-oracle.json';
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex').toUpperCase();
assert.equal(sha(controllerBase),'AAE99CDD02B00BDD78D1F02FED85C18BC72B82CAB9A66CEB7E0E3590EC3E8790');
assert.equal(sha(oraclePath),'6C020BAEEF37E72A0153437BA6CE66CD399319BF6810A50515462997675EE34A');
function extract(sourceText,name){const start=sourceText.indexOf(`function ${name}(`);assert(start>=0,`function ${name} exists`);const brace=sourceText.indexOf('{',start);let depth=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<sourceText.length;i++){const c=sourceText[i],n=sourceText[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return sourceText.slice(start,i+1);}throw Error('unterminated '+name);}
const oracle=JSON.parse(fs.readFileSync(path.join(root,oraclePath),'utf8'));
const frozenPro=fs.readFileSync(path.join(root,controllerPath),'utf8');
const basePro=fs.readFileSync(path.join(root,controllerBase),'utf8');
async function run(routeName,input,mode,proText=frozenPro){
  const zones=[{id:'roof',name:'Roof',base:'f_chrome',finish:'f_chrome',baseColorMode:mode,baseColor:mode==='solid'?'#1f8a3b':null,regionMask:new Uint8Array([1,0]),useRegion:true}];
  const w={console,fetch(){throw Error('provider call forbidden');},_spbLayerRev:3,selectedZoneIndex:0,_psdLayers:[{id:'base',name:'Paint',img:{},visible:true},{id:'number',name:'Numbers',img:{},visible:true}],paintImageData:{width:8,height:8},zones,document:{body:{classList:{contains(){return false;}}}},SpbProCar:{roles:()=>[],map:()=>({}),missing:()=>[]},SpbProZone:{catchAll:()=>false}};w.window=w;
  vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(root,knowledgePath),'utf8'),w);vm.runInContext(fs.readFileSync(path.join(root,helperPath),'utf8'),w);
  const actualSH=w.SpbSelfHelp,events=[];
  const stubD={offlinePartCoverage(t){events.push('offlinePartCoverage');return null;},compoundPlan(t){events.push('compoundPlan');return null;},refine(){return null;},offlineIdeas(){return null;},lookRequest(){events.push('lookRequest');return null;},offlineSpec(){return null;},offlinePart(){return null;},offlineElement(){return null;},offlinePlan(){return null;}};
  const c={window:w,console,Promise,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,D:stubD,E:null,zones,_busy:false,_progress:'',_advLast:null,_offlineLast:null,_forcedIdeaCols:null,_advRejected:[],_advDislikes:[],_reqText:'',_specOnlyReq:false,_beforeImg:null,
    START_OVER_RE:/^\s*(?:start over|new design)\b/i,CHECK_AGAIN_RE:/$a/,NOT_ELEM_RE:/$a/,NUM_FIX_RE:/$a/,SH_FIRST_RE:/^(?:how|what|where|which|can|tell me|show me how)/i,
    offlineInstructionPreflight:()=>null,operationCurrent:t=>!!(t&&t.ok),operationCanceled:()=>({cancelled:true}),elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),
    editPlan:()=>{events.push('editPlan');return null;},advisorOwns:()=>{events.push('advisorOwns');return false;},advisorIntent:()=>{events.push('advisorIntent');return null;},offlineMaterialPlan:()=>null,intentSpecOnly:()=>false,editYieldsToStack:()=>false,
    offlineEditAsk:()=>({offline:true,text:'edit-path',queue:[]}),offlineCoveredPartAsk:()=>({offline:true,text:'covered-path',queue:[]}),offlineLookAsk:()=>({offline:true,text:'look-path',queue:[]}),offlineSpecAsk:()=>({offline:true,text:'spec-path',queue:[]}),offlinePartAsk:()=>({offline:true,text:'part-path',queue:[]}),offlineElementAsk:()=>({offline:true,text:'element-path',queue:[]}),offlineScopeReply:()=>({offline:true,text:'scope-fallback',queue:[]}),offlineCannot:()=>null,layerVisRequest:()=>null,offlineRefineAsk:()=>({offline:true,text:'refine',queue:[]}),offlineIdeasAsk:()=>null,offlineHowto:()=>null,offlineStartOver:()=>null,offlineUndo:()=>null,offlineNumbersAsk:()=>null,offlineElemWrong:()=>null,
    captureOriginal(){},render(){},operationPublish:(t,fn)=>fn(),warm:()=>Promise.resolve(),operationRelease(){},prepEnv:()=>Promise.resolve({}),elementKinds:()=>[],
    selfHelpClaim:t=>{events.push('selfHelpClaim');return actualSH.handle(t);},selfHelpResult:r=>({offline:true,text:r.text,queue:[],calls:0,tools:['self_help'],howto:true})};
  vm.createContext(c);
  for(const n of ['selfHelpResult','offlineAsk','offlineAskCore'])vm.runInContext(extract(proText,n),c,{filename:'W84#'+n});
  const fn=routeName==='public'?c.offlineAsk:c.offlineAskCore;
  const result=await fn(input,{_spbOperation:{ok:true,collection:1},noAdvisor:true});
  return {result,events,classification:actualSH.classify(input)};
}
(async()=>{
 const rows=[];
 for(const id of ['C01','C02']){
   const c=oracle.cases.find(x=>x.id===id),baseCore=await run('core',c.input,c.state.colourMode,basePro),basePublic=await run('public',c.input,c.state.colourMode,basePro);
   assert.ok(baseCore.events.includes('advisorOwns')&&baseCore.events.includes('compoundPlan'),id+' baseline core reaches broad fallbacks before late help');
   assert.ok(basePublic.events.includes('advisorOwns')&&basePublic.events.includes('compoundPlan'),id+' baseline public route does not prioritize W84 tag');
   rows.push({id:id+'-BASELINE-ROUTE',baselineCoreFallbacks:baseCore.events,baselinePublicFallbacks:basePublic.events,note:'The original integration9 controller has only W66/W74 early tags; W84 is answered only after broad offline fallbacks.'});
 }
 for(const x of oracle.cases){
   const m=x.state.colourMode, out=await run('core',x.input,m),r=out.result,text=String(r&&r.text||'');
   assert.ok(out.classification&&out.classification.w84,x.id+' must be claimed by W84 classification');
   assert.ok(r&&r.queue&&r.queue.length===0,x.id+' passive route queue must remain empty');
   assert.equal(r.calls,0,x.id+' must use built-in path');
   if(x.id==='C01'||x.id==='C02'||x.id==='C05'){
     assert.match(text,/Use solid color/i,x.id+' must describe solid-mode retention when actual selected zone is solid');
     assert.match(text,/#1f8a3b/i,x.id+' must preserve current selected solid hex');
     assert.match(text,/original imported.*colors|original imported paint image/i,x.id+' must distinguish source pixels from authored solid color');
   }
   if(x.id==='C03')assert.match(text,/original imported source-image colors/i);
   if(x.id==='C04'||x.id==='C06'){
     assert.match(text,/AI answer Undo/i);assert.match(text,/later manual same-zone mask edit/i);assert.match(text,/Ctrl\+Z or History/i);assert.match(text,/does not establish behavior for every layer-pixel or transform edit/i);
   }
   assert.ok(!out.events.includes('advisorOwns')&&!out.events.includes('compoundPlan')&&!out.events.includes('lookRequest'),x.id+' W84 passive answer must win before material/design/advisor routing');
   const publicOut=await run('public',x.input,m);
   assert.equal(publicOut.result.queue.length,0,x.id+' public offlineAsk route stays passive');
   assert.ok(!publicOut.events.includes('advisorOwns')&&!publicOut.events.includes('compoundPlan'),x.id+' public offlineAsk must dispatch W84 before broad routes');
   rows.push({id:x.id,classification:out.classification.w84,coreEvents:out.events,publicEvents:publicOut.events,reply:text.slice(0,260)});
 }
 for(const t of ['Paint only the roof green.','Make the hood chrome.']){
   const out=await run('core',t,'solid');assert.notEqual(out.result&&out.result.tools&&out.result.tools[0],'self_help','imperative edit must not be claimed as help');
 }
 const solid=await run('core','What does Use Source Paint mean for this roof?','solid');
 const source=await run('core','What does Use Source Paint mean for this roof?','source');
 assert.match(solid.result.text,/Use solid color.*#1f8a3b/i);assert.match(source.result.text,/already in source-paint mode/i);
 console.log(JSON.stringify({status:'PASS_PRIVATE_W84_CONTEXT_AND_ROUTE',freshCases:oracle.cases.length,actualOfflineAskCoreCases:rows.length,actualPublicOfflineAskCases:rows.length,selectedSolidState:'#1f8a3b',sourceModeVariant:true,imperativeControls:2,queueEffects:0,providerCalls:0,nativeCalls:0,helperSha256:sha(helperPath),controllerBaseSha256:sha(controllerBase),controllerCandidateSha256:sha(controllerPath),oracleSha256:sha(oraclePath),rows,limits:['Controller source is an isolated private copy of integration9; no live client was edited or run.','The helper obtains its selected-zone state from controlled VM globals mirroring the actual state fields; no DOM/canvas/native interaction occurred.','AI Undo semantics are bounded to the separately reported combined W57 per-field mask behavior; layer pixels and transforms were not exercised here.']},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
