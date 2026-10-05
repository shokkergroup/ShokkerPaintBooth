'use strict';
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '..'), base = '_easy_claude_work/ai14h_generation3_runtime9/js/';
const cand = '_easy_claude_work/ai14h_w116_successor/spb-pro-ai.js', oraclePath = '_easy_claude_work/ai14h_w116_successor/fresh-oracle.json';
const files = { pro:cand, baseline:base+'spb-pro-ai.js', selfhelp:base+'spb-self-help.js', receipt:base+'spb-ai-receipt-explainer.js', intent:base+'spb-ai-instruction-intent-guard.js' };
const src = Object.fromEntries(Object.entries(files).map(([k,p])=>[k,fs.readFileSync(path.join(root,p),'utf8')]));
const oracleText=fs.readFileSync(path.join(root,oraclePath),'utf8'), oracle=JSON.parse(oracleText);
const sha=s=>crypto.createHash('sha256').update(s).digest('hex').toUpperCase(), sourceSha=sha(src.pro), oracleSha=sha(oracleText);
assert.equal(sha(src.baseline),'1C178D2717D0ED654C1840AA01452F03322CFB9F3BA4716E2FE333F48D079430','immutable Runtime9 baseline pin');
assert.equal(oracleSha,'AF9F528F6A9F101601D4003A20007BE7A0E9C09DAC35BB8A832DC6EA1E880F39','frozen W116b holdout pin');
function extract(s,n){const a=s.indexOf(`function ${n}(`);assert(a>=0,n+' exists');const b=s.indexOf('{',a);let d=0,q=null,ln=false,bl=false,esc=false;for(let i=b;i<s.length;i++){const c=s[i],x=s[i+1];if(ln){if(c==='\n')ln=false;continue;}if(bl){if(c==='*'&&x==='/'){bl=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&x==='/'){ln=true;i++;continue;}if(c==='/'&&x==='*'){bl=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;if(c==='}'&&--d===0)return s.slice(a,i+1);}throw Error('unterminated '+n);}
function fixture(seed=[]){
  const w={console,Promise,Date,Math,JSON,Object,Array,String,Number,RegExp,Error,document:{body:{classList:{contains:()=>false}},getElementById:()=>null},zones:[],_psdLayers:[],paintImageData:null,selectedZoneIndex:-1,zoneSourceLayerIds:()=>[],_spbLayerRev:0,SpbProCar:{roles:()=>[],map:()=>null,missing:()=>[]},SpbAI:{cached:()=>({configured:false})},SpbAiLease:{internal:()=>true}};w.window=w;vm.createContext(w);
  for(const k of ['selfhelp','receipt','intent'])vm.runInContext(src[k],w,{filename:files[k]});
  Object.assign(w,{_log:seed.slice(),_busy:false,_ctl:null,_envMemo:null,operationCurrent:t=>!!t&&t.ok===true,operationTicket:v=>v&&v._spbOperation||null,operationManager:()=>({sameDocument:t=>!!t&&t.document&&t.document.sourceGeneration===9,ready(){},owns:()=>true}),operationRevision:()=>1,operationRelease(){},operationBind:v=>v,operationStart:()=>({ok:true,document:{sourceGeneration:9},revision:1,collection:1}),operationCanceled:()=>({cancelled:true,stale:true,queue:[]}),offlineAsk:()=>Promise.resolve({offline:true,queue:[],text:'offline route sentinel'})});
  for(const n of ['normalizeOfflineInstruction','selfHelpResult','unexecutedSuggestionReply','contextualHelpReply','offlineInstructionPreflight','ask'])vm.runInContext(extract(src.pro,n),w,{filename:files.pro});
  w.spbProAI={ask:w.ask};const calls=[];w.askForTicket=(text,opts)=>{calls.push({text,opts});return Promise.resolve({offline:true,text:'controlled offline action handoff',queue:[]});};return {w,calls};
}
function seeded(kind){if(kind==='none')return[];const e={role:'ai',lines:['Changed roof to blue'],notes:[],_spbOperation:{ok:true,document:{sourceGeneration:9},revision:1}};if(kind==='undone')e.undone=true;return[e];}
(async()=>{
 const parentCases=[
  {id:'parent-coat-controls',input:'Which slider changes coat while leaving metal and roughness alone?',topic:'channel-definition'},
  {id:'parent-offline-credits',input:'Do I need AI credits to change finishes locally?',topic:'offline-credits'},
  {id:'parent-authored-color-retain',input:'How do I leave the green roof I just made alone and only change its finish?',topic:'keep-authored-solid-color'},
  {id:'parent-mask-undo',input:'How does Undo affect a mask I drew after the AI change?',topic:'undo-mask-conflict'},
  {id:'parent-blue-coat-no-punctuation',input:'How could I change the blue coat channel only',topic:'channel-definition'},
  {id:'parent-blue-material-channel',input:'How do I adjust only the blue material channel and leave the paint color and roughness alone?',topic:'channel-definition'},
  {id:'parent-latest-receipt-current',input:'What is the latest change actually completed? Do not guess if there is no receipt.',topic:'receipt'},
  {id:'parent-latest-receipt-empty',input:'What is the latest change actually completed? Do not guess if there is no receipt.',topic:'receipt'}
 ];
 const rows=[],issues=[];
 for(const c of oracle.cases.concat(parentCases)){const seed=c.id==='recent-sheet-receipt'||c.id==='parent-latest-receipt-current'?seeded('applied'):c.id==='receipt-after-undo'?seeded('undone'):seeded('none');const {w,calls}=fixture(seed);const r=await w.spbProAI.ask(c.input,{offline:true}),t=String(r&&r.text||'');rows.push({id:c.id,howto:!!(r&&r.howto),queue:(r&&r.queue||[]).length,delegated:calls.length,topic:r&&r.selfHelp&&r.selfHelp.topic,text:t.slice(0,420)});
  if(c.topic==='action-control'){if(r&&r.howto||calls.length!==1||calls[0].text!==c.input)issues.push(c.id+': action diverted or not delegated once');}
  else if(c.topic==='no-execution'){if(!r||!r.howto||calls.length||(r.queue||[]).length)issues.push(c.id+': no-execution request left read-only route');}
  else {if(!r||!r.howto||calls.length||(r.queue||[]).length)issues.push(c.id+': expected read-only contextual answer');}
  if(c.topic==='channel-definition'&&!(/clear ?coat/i.test(t)&&/B channel|blue channel|slider/i.test(t)))issues.push(c.id+': blue-coat phrasing did not explain clearcoat channel');
  if(c.topic==='logo-limits'&&!(/cannot|not (?:reliably|guarantee|confirm)|inspect|check|confirm/i.test(t)&&!/sponsor.{0,30}(?:red|blue|chrome)|pick a look|tell me a colour/i.test(t)))issues.push(c.id+': logo answer lacks a grounded limit/inspection cue or diverts to recolor chips');
  if(c.id==='recent-sheet-receipt'&&!/verified applied changes were: Changed roof to blue/i.test(t))issues.push(c.id+': current receipt was not read by recent-sheet wording');
  if(c.id==='receipt-after-undo'&&!/undone|replaced|cannot determine|do not have a current/i.test(t))issues.push(c.id+': undone edit presented as current success');
  if(c.topic==='save-layer-payload'&&!(/raster pixel payload|current raster pixel/i.test(t)&&/(?:original PSD bytes are not embedded|does not bundle the original PSD)/i.test(t)&&/adjustment-layer semantics are not guaranteed/i.test(t)))issues.push(c.id+': omitted an essential saved-project/source distinction');
  if(c.topic==='current-state-limits'&&!/not (?:confirmed|proof)|cannot confirm|not confirm|current (?:paint|source)|inspect|check/i.test(t))issues.push(c.id+': prior number memory could be mistaken for current-paint confirmation');
  if(c.topic==='offline-credits'&&!/without an AI provider key|without .*paid model|locally/i.test(t))issues.push(c.id+': local supported edits/optional provider charges not explained');
  if(c.topic==='keep-authored-solid-color'&&!/Solid color/i.test(t)||c.topic==='keep-authored-solid-color'&&!/leave its current color value unchanged|keep its current color value/i.test(t))issues.push(c.id+': does not clearly preserve authored Solid color while changing finish only');
  if(c.topic==='undo-mask-conflict'&&!/mask/i.test(t)||c.topic==='undo-mask-conflict'&&!/manual mask is kept|conflicting manual mask is kept/i.test(t))issues.push(c.id+': does not explain later mask conflict protection');
  if(c.id==='parent-blue-material-channel'&&!/clearcoat|clear coat/i.test(t))issues.push(c.id+': explicit blue material channel did not identify Clearcoat');
  if(c.id==='parent-latest-receipt-current'&&!/verified applied changes were: Changed roof to blue/i.test(t))issues.push(c.id+': current receipt not returned for latest completed change');
  if(c.id==='parent-latest-receipt-empty'&&!/current, verified apply receipt/i.test(t))issues.push(c.id+': absent receipt did not receive honest no-guess answer');
 }
 const report={work_item:'W116b Runtime9 contextual-help successor holdout',status:issues.length?'REVIEW_GAPS':'PASS_PRIVATE_CANDIDATE',source:{path:cand,sha256:sourceSha,baseRuntime9:'_easy_claude_work/ai14h_generation3_runtime9/js/spb-pro-ai.js',baseSha256:'1C178D2717D0ED654C1840AA01452F03322CFB9F3BA4716E2FE333F48D079430',publicAskExport:/window\.spbProAI\s*=\s*\{[\s\S]*?\bask:\s*ask\s*[,}]/.test(src.pro)},oracle:{path:oraclePath,sha256:oracleSha,frozenBeforeSourceInspection:true,cases:oracle.cases.length},parentSuppliedPostFreezeCases:parentCases.map(x=>x.id),sourcePaintDescriptionAudit:{status:'ACCURATE_WITH_CAVEAT',evidence:'Runtime9 system rule 16c says color "source" preserves paint when editing an existing zone and warns that a new source-colored zone can reveal original template art; spb-pro-edit parser comments describe the existing-zone case. No prompt-copy change made. Authored Solid color remains a separate zone color mode.'},counts:{frozenCases:oracle.cases.length,parentSuppliedSupplementalCases:parentCases.length,totalChecks:rows.length,failedChecks:issues.length,providerCalls:0,nativeCalls:0,queueApplications:0},rows,issues,limits:['The test executes exact extracted contextualHelpReply(), offlineInstructionPreflight(), and ask() bodies, plus the actual receipt/self-help/intent modules from frozen Runtime9. The desktop IIFE is not booted. Provider and action downstream are controlled off-line; no native app, provider, save, queue-apply, or backend action occurred.']};
 fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_CONTEXTUAL_RUNTIME9_W116B_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(issues.length)process.exitCode=1;
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
