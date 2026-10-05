'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'), dir='_easy_claude_work/ai14h_negation_history_guard_20261004_a/';
const oraclePath=dir+'fresh-oracle.json', oracleText=fs.readFileSync(path.join(root,oraclePath),'utf8'), oracle=JSON.parse(oracleText);
const candidate=dir+'candidate/spb-pro-ai.js', baseline='_easy_claude_work/ai14h_generation3_runtime12/js/spb-pro-ai.js';
const files={pro:process.argv.includes('--baseline')?baseline:candidate,selfhelp:dir+'candidate/spb-self-help.js',receipt:dir+'candidate/spb-ai-receipt-explainer.js',intent:dir+'candidate/spb-ai-instruction-intent-guard.js'};
const source=Object.fromEntries(Object.entries(files).map(([k,p])=>[k,fs.readFileSync(path.join(root,p),'utf8')]));
const sha=s=>crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
const expected={proBaseline:'FB63F5906E1C9FC9D49150F571D64FDE640E0A4630319C418FE4F9C2E7E5413A',oracle:'39874C8E17BCE9050E63F88CD3BDE2B6FAF2FE126FBCC08B9909FF2BA6AD8387'};
assert.equal(sha(source.pro),process.argv.includes('--baseline')?expected.proBaseline:'FA2179B83BE1F94DB70101421121050B2F7558262D15FAD254AFA2F98CC84C58','pinned controller source');assert.equal(sha(oracleText),expected.oracle,'frozen oracle source');
function extract(s,n){const a=s.indexOf(`function ${n}(`);assert(a>=0,`${n} exists`);const b=s.indexOf('{',a);let d=0,q=null,ln=false,bl=false,esc=false;for(let i=b;i<s.length;i++){const c=s[i],x=s[i+1];if(ln){if(c==='\n')ln=false;continue;}if(bl){if(c==='*'&&x==='/'){bl=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&x==='/'){ln=true;i++;continue;}if(c==='/'&&x==='*'){bl=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;if(c==='}'&&--d===0)return s.slice(a,i+1);}throw Error(`unterminated ${n}`);}
function fixture(){
 const w={console,Promise,Date,Math,JSON,Object,Array,String,Number,RegExp,Error,setTimeout,document:{body:{classList:{contains:()=>false}},getElementById:()=>null},zones:[],_psdLayers:[],paintImageData:null,selectedZoneIndex:-1,zoneSourceLayerIds:()=>[],_spbLayerRev:0,SpbProCar:{roles:()=>[],map:()=>null,missing:()=>[]},SpbAiLease:{internal:()=>true}};w.window=w;vm.createContext(w);
 for(const k of ['selfhelp','receipt','intent'])vm.runInContext(source[k],w,{filename:files[k]});
 const item={role:'ai',id:7,request:'Make roof red',lines:['Changed roof to red'],notes:[],_spbOperation:{ok:true,document:{sourceGeneration:12},revision:4,collection:1},undoable:true,undone:false};
 Object.assign(w,{_log:[item],_busy:false,_ctl:null,_envMemo:null,operationCurrent:t=>!!t&&t.ok===true,operationTicket:v=>v&&v._spbOperation||null,operationManager:()=>({sameDocument:t=>!!t&&t.document&&t.document.sourceGeneration===12,ready(){},owns:()=>true}),operationRevision:()=>4,operationRelease(){},operationBind:v=>v,operationStart:()=>({ok:true,document:{sourceGeneration:12},revision:4,collection:1}),operationCanceled:()=>({cancelled:true,stale:true,queue:[]}),AI:{cached:()=>({configured:false})},offlineFirst:()=>true,offlineCanHandle:()=>true,selfHelpClaim:()=>null});
 for(const n of ['normalizeOfflineInstruction','selfHelpResult','unexecutedSuggestionReply','contextualHelpReply','offlineInstructionPreflight','askForTicket','ask'])vm.runInContext(extract(source.pro,n),w,{filename:files.pro});if(!process.argv.includes('--baseline'))vm.runInContext(extract(source.pro,'negatedHistoryActionReply'),w,{filename:files.pro});else w.negatedHistoryActionReply=()=>null;
 const dispatched=[];w.offlineAsk=(text,o)=>{dispatched.push({text,opts:o});return Promise.resolve({offline:true,queue:[],text:'controlled action handoff'});};w.spbProAI={ask:w.ask};return{w,dispatched};
}
(async()=>{const results=[],issues=[];for(const c of oracle.cases){const {w,dispatched}=fixture();const r=await w.spbProAI.ask(c.text,{offline:true}),text=String(r&&r.text||''),q=(r&&r.queue||[]).length;const explicit=['explicit-undo-last','explicit-undo-roof','explicit-dislike-undo','explicit-undo-then-stop'].includes(c.id);const conflict=c.id==='conflicting-negated-undo';
 results.push({id:c.id,howto:!!(r&&r.howto),topic:r&&r.selfHelp&&r.selfHelp.topic,dispatches:dispatched.length,queue:q,text:text.slice(0,350)});
 if(explicit){if(dispatched.length!==1||r&&r.howto)issues.push(c.id+': explicit undo did not remain eligible for the controlled action handoff');if(q)issues.push(c.id+': controlled sink unexpectedly queued');continue;}
 if(dispatched.length||q)issues.push(c.id+': negated/question/conflicting request reached action sink or returned queue');
 if(!r||!r.howto||!text)issues.push(c.id+': no useful read-only response');
 if(c.id==='dont-change-explain-satin'&&!/satin/i.test(text))issues.push(c.id+': omitted satin explanation');
 if(c.id==='question-about-undo'&&!/Undo|undo/i.test(text))issues.push(c.id+': omitted Undo guidance');
 if(conflict&&!/mixed instruction|explicitly want|Nothing was changed/i.test(text))issues.push(c.id+': did not clarify contradictory instruction');
 if(c.id!=='question-about-previous-effect'&&/\bDone\b|switched off|changed roof/i.test(text))issues.push(c.id+': reply falsely implies a completed edit/undo');if(c.id==='question-about-previous-effect'&&!/last verified applied changes were: Changed roof to red/i.test(text))issues.push(c.id+': failed to preserve current-source receipt explanation');
 }
 console.log(JSON.stringify({controller:files.pro,controllerSha256:sha(source.pro),oracle:oraclePath,oracleSha256:sha(oracleText),cases:results.length,pass:results.length-issues.length,issues,results},null,2));if(issues.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});



