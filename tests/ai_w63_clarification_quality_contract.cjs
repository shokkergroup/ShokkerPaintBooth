'use strict';
// W63 route-level replay on isolated parser/controller copies; W58 cases are retained unchanged.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const fixture = path.join(root, '_easy_claude_work/ai14h_w63_candidate/fixture');
const candidateDir = path.join(root,'_easy_claude_work/ai14h_w63_candidate/candidate');
const files = {
  'spb-pro-ai.js':path.join(candidateDir,'spb-pro-ai.js'),
  'spb-pro-design.js':path.join(fixture,'spb-pro-design.js'),
  'spb-pro-edit.js':path.join(candidateDir,'spb-pro-edit.js'),
  'spb-ai-complete-instruction-guard.js':path.join(fixture,'spb-ai-complete-instruction-guard.js')
};
const candidateProAiPath=files['spb-pro-ai.js'];
const expected = {
  'spb-pro-ai.js':'9de25e728583b2d4c0b9854529c3ebfa0e9639d71a4a6e535827c8e3d9a6950b',
  'spb-pro-design.js':'0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8',
  'spb-pro-edit.js':'14dd5696cbb33f2c2a956ded4419637191bb446162ce5a2f96558792f2c5bb87',
  'spb-ai-complete-instruction-guard.js':'ba0af1f9e217695ed733dde81c8dec1a735dd1f052e8c06b3098866d392a551c'
};
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
for (const [n,p] of Object.entries(files)) assert.equal(sha(p), expected[n], `${n} frozen input changed`);
const w58Cases = [
  {id:'R58-P01-ON', text:'The hood should be chrome while keeping its red paint.', configured:true, expect:'complete'},
  {id:'R58-P01-OFF', text:'The hood should be chrome while keeping its red paint.', configured:false, expect:'complete'},
  {id:'R58-N06-ON', text:'The hood should be chrome while keeping its red paint and adding a gold carbon weave.', configured:true, expect:'ask', extra:'gold carbon weave', part:'hood'},
  {id:'R58-N06-OFF', text:'The hood should be chrome while keeping its red paint and adding a gold carbon weave.', configured:false, expect:'ask', extra:'gold carbon weave', part:'hood'},
  {id:'R58-P02-ON', text:'Make only the roof satin; keep its current red paint.', configured:true, expect:'complete'},
  {id:'R58-N07-ON', text:'The roof should be satin while keeping its current blue paint and adding a gold carbon weave.', configured:true, expect:'ask', extra:'gold carbon weave', part:'roof'}
];
const w63OraclePath=path.join(root,'_easy_claude_work/ai14h_w63_candidate/oracle.json');
const w63OracleBytes=fs.readFileSync(w63OraclePath);
assert.equal(sha(w63OraclePath),'60bf5b7656be0ed877badaf2d33877b67b89e59919582a05070d85b61d68e7e5','W63 frozen oracle changed');
const w58TestPath=path.join(root,'tests/ai_w58_route_atomicity_review_contract.cjs');
assert.equal(sha(w58TestPath),'349ec8cced76dca2f67f843ca26e558c03002db7d8c087775ed0867675aa2b31','W58 route oracle/test changed');
const w63Oracle=JSON.parse(w63OracleBytes.toString('utf8'));
const freshCases=w63Oracle.fresh_cases.map(c=>({id:c.id,text:c.text,configured:!c.expected.includes('question'),expect:c.expected.includes('positive')?'complete':'ask',extra:/gold carbon weave|pearl flake texture|silver grain|violet carbon weave|red pinstripe texture/i.exec(c.expected)?(c.expected.match(/gold carbon weave|pearl flake texture|silver grain|violet carbon weave|red pinstripe texture/i)||[])[0]:null,part:(c.text.match(/\b(hood|roof|trunk|left side|right side)\b/i)||[])[1]}));
const cases=w58Cases.concat(freshCases);
const oracleSha = crypto.createHash('sha256').update(JSON.stringify({w58Cases,freshCases})).digest('hex');
assert.equal(sha(candidateProAiPath),expected['spb-pro-ai.js'],'isolated controller candidate changed');
const aiSource=fs.readFileSync(candidateProAiPath,'utf8');
const w={console,Promise,document:{},SpbAiOperation:{create:()=>({start:()=>({collection:{} }),current:()=>true,bind(){},ready(){},release(){},owns:()=>true,publish:(t,fn)=>({value:fn()}),collecting:()=>true,ticketOf:()=>null})}}; w.window=w;
vm.createContext(w);
vm.runInContext(fs.readFileSync(files['spb-pro-design.js'],'utf8'),w,{filename:files['spb-pro-design.js']});
vm.runInContext(fs.readFileSync(files['spb-pro-edit.js'],'utf8'),w,{filename:files['spb-pro-edit.js']});
vm.runInContext(fs.readFileSync(files['spb-ai-complete-instruction-guard.js'],'utf8'),w,{filename:files['spb-ai-complete-instruction-guard.js']});
const D=w.SpbProDesign,E=w.SpbProEdit;
const env={palette:[{hex:'#c8102e',share_pct:52},{hex:'#141416',share_pct:22},{hex:'#1347a8',share_pct:14},{hex:'#f2c500',share_pct:5}],layers:[]};
const w52OraclePath=path.join(root,'_easy_claude_work/ai14h_w52_candidate/oracle.json');
const w52OracleBytes=fs.readFileSync(w52OraclePath);
assert.equal(sha(w52OraclePath),'916b77ee479a4cc9465b0104a9194efdf84b372aa0f500e1b520b87278e3372a','W52 parser oracle changed');
const w52Oracle=JSON.parse(w52OracleBytes.toString('utf8'));
const w52ParserResults=w52Oracle.fresh_cases.map(c=>{
  const plan=E.plan(c.text,env), compiled=plan&&plan.kind==='ops'?E.compile(plan,env):null;
  const positive=/W52-P0[1-4]/.test(c.id);
  if(positive){const op=plan&&plan.ops&&plan.ops[0],zone=compiled&&compiled.zones&&compiled.zones[0];assert(plan&&plan.kind==='ops'&&plan.exactPart===true&&plan.ops.length===1&&op&&op.target.part===c.expectedPart&&!op.colour&&!plan.unknown.length,c.id+' parser positive');assert(compiled&&!compiled.ask&&compiled.zones.length===1&&zone.region.part===c.expectedPart&&zone.color==='source',c.id+' compile positive');}
  else {assert(!(plan&&plan.exactPart===true),c.id+' must not claim exact executable scope');assert(!compiled||!compiled.zones||compiled.zones.length===0,c.id+' must not compile partial edits');assert(!compiled||!!compiled.ask||plan&&plan.kind==='ask',c.id+' must remain a clarification/help route');}
  return {id:c.id,kind:plan&&plan.kind,exactPart:!!(plan&&plan.exactPart),zones:compiled&&compiled.zones&&compiled.zones.length||0,ask:!!(compiled&&compiled.ask)};
});
const route={window:Object.assign(w,{SpbMaterialControls:undefined,SpbProElements:undefined}),console,Promise,D,E,
  AI:{cached:()=>({configured:!!route.configured})},configured:false,_busy:false,_skipParts:true,_absent:{},CAR:null,_offlineLast:null,_advLast:null,_advRejected:[],_advDislikes:[],_forcedIdeaCols:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,_progress:'',_editReg:{},_editRegPendingBefore:{},_editRegSig:'w58-car',zones:[],_gen:0,_snapGen:0,_activeId:null,RECENT:[],_advUsed:null,_log:[],_panel:null,_serial:0,_progAI:false,_progT0:0,_progK:0,_progEnd:0,_pendingCard:null,
  providerCalls:0,finishCalls:[],captureOriginal(){},intentSpecOnly:()=>false,editYieldsToStack:()=>false,elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),offlineFirst:()=>true,selfHelpClaim:()=>null,selfHelpResult:x=>x,advisorIntent:()=>null,advisorOwns:()=>false,advisorEnv:()=>({}),advisorReply(){throw Error('advisor prohibited')},
  START_OVER_RE:/^$a/,SMALL_HELLO_RE:/^$a/,SMALL_THANKS_RE:/^$a/,CANT_RE:/$a/,NUM_FIX_RE:/$a/,NOT_ELEM_RE:/$a/,layerVisRequest:()=>null,lookEntry:()=>null,offlineCannot:()=>null,offlineHowtoPeek:()=>false,offlineScopeReply:()=>({text:'Nothing was changed.'}),offlineHowto:()=>null,warm:()=>Promise.resolve(),render(){},prepEnv:()=>Promise.resolve(env),resolveLook:()=>Promise.resolve(null),elementKinds:()=>[],exclTargets:()=>[],markPartFollowupQueue(){},editOverlapNote:()=>'',editOverlapKinds:()=>[],exclNotes:()=>[],normaliseSpec:s=>s,protectDecals(){},friendlyZoneError:x=>String(x||''),
  editPlural:()=>false,editPlan:text=>E.plan(text,env),editEnv:()=>env,carSig:()=>'w58-car',partRegHas:(o,k)=>Object.prototype.hasOwnProperty.call(o||{},k),renderZones(){},triggerPreviewRender(){},undoZoneChange(){},
  makeTools(queue){return [{name:'add_zone',handler(spec){const q={kind:'add',spec:JSON.parse(JSON.stringify(spec))};queue.push(q);return{};}},{name:'edit_zone',handler(args){const cp=JSON.parse(JSON.stringify(args));const ix=cp.zone_id!=null?route.zones.findIndex(z=>String(z.id)===String(cp.zone_id)):Number(cp.zone);const spec={};Object.keys(cp).forEach(k=>{if(!['zone','zone_id','zone_name','expect_name','_spbPartRegKey','_spbPartOwnerName','_spbPartForgetKey'].includes(k))spec[k]=cp[k];});const q={kind:'edit',zone:ix,zone_id:cp.zone_id,spec,args:cp};queue.push(q);return{};}}];},
  editReply(text,chips,options){return{route:options&&options.queue?'edit':'ask',text,chips:chips||[],queue:options&&options.queue||[],tools:options&&options.tools||[]};},
  operationStart(){return{collection:{id:1}}},operationCurrent:()=>true,operationRelease(){},operationCanceled:()=>({cancelled:true,queue:[]}),operationBind:r=>r,operationManager:()=>({ready(){}}),operationPublish:(t,fn)=>fn(),operationTools:(t)=>t,operationRefreshDocument(){},
  askCore(){route.providerCalls++;return Promise.resolve({offline:false,route:'provider-stub',queue:[],calls:1});},
  finish(r){route.finishCalls.push(r);return r;},supportClass:()=>null,supportSend:()=>false,elemCurrentCard:()=>null,elementPaintSig:()=>'',elementRunIdentity:()=>null,elemReplyAction:()=>null,runElemAction:()=>false,elemOwnsText:()=>false,TEACH_RE:/never/,QUESTION_RE:/$a/,CHECK_AGAIN_RE:/$a/,
  offlineInstructionPreflight:()=>null,offlineComplaint:()=>null,offlineMaterialPlan:()=>null,offlineCoveredPartAsk:null,offlinePartCoverage:()=>null,offlineGaveUp:()=>false,logMiss(){},gearModel:()=> 'stub',
  rshotGrab(){},complaintChip:()=>false,complaintOf:()=>null,kitAsk:()=>false,advisorPick(){},offlineComplaint:()=>null,advisorIntent:()=>null,teachAll:()=>null,selfHelpClaim:()=>null,offlineHowto:()=>null,offlineScopeReply:()=>({text:'Nothing was changed.'}),offlineHowtoPeek:()=>false
};
vm.createContext(route);
function extract(name){const start=aiSource.indexOf(`function ${name}(`);assert(start>=0,`function ${name} found`);if(name==='send'){const end=aiSource.indexOf('function mergeMaskUndo(',start);assert(end>start);return aiSource.slice(start,end).trim();}const b=aiSource.indexOf('{',start);let depth=0,q=null,esc=false,line=false,block=false;for(let i=b;i<aiSource.length;i++){const c=aiSource[i],n=aiSource[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return aiSource.slice(start,i+1);}throw Error('unclosed '+name);}
for(const n of ['partRegionKey','editKey','editPlural','offlineMaterialPlan','queueEditZones','offlineEditAsk','offlineCanHandle','offlineAsk','offlineAskCore','ask','askForTicket','send','offlineInstructionPreflight'])vm.runInContext(extract(n),route,{filename:`frozen-proAI#${n}`});
route.Z={batch(){return[]},quiet:fn=>fn(),catchAll:()=>false};
async function run(){
 const results=[],blockers=[];
 for(const c of cases){route.configured=c.configured;route.providerCalls=0;route.finishCalls=[];route._busy=false;route._offlineLast=null;route._advLast=null;route.committedQueue=[];route._log=[];
   const ed=E.plan(c.text,env), compiled=ed&&ed.kind==='ops'?E.compile(ed,env):null;
   const direct=ed?await route.offlineEditAsk(c.text,ed,{noAdvisor:true,_spbOperation:{collection:{id:1}}}):route.offlineInstructionPreflight(c.text); const directQueue=direct&&direct.queue||[];
   route._busy=false;let coreResult;try{coreResult=await route.offlineAskCore(c.text,{noAdvisor:true,_spbOperation:{collection:{id:1}}});}catch(e){coreResult={error:String(e),queue:[]};}
   route._busy=false;let offlineResult;try{offlineResult=await route.offlineAsk(c.text,{noAdvisor:true,_spbOperation:{collection:{id:1}}});}catch(e){offlineResult={error:String(e),queue:[]};}
   route.providerCalls=0;route._busy=false;let askResult;try{askResult=await route.ask(c.text,{});}catch(e){askResult={error:String(e),queue:[]};}
   const askQueue=askResult&&askResult.queue||[];const askProviders=route.providerCalls;
   route.providerCalls=0;route.finishCalls=[];route._busy=false;let sendError=null;try{route.send(c.text,{});}catch(e){sendError=String(e);}await new Promise(resolve=>setTimeout(resolve,0));const sent=route.finishCalls.at(-1)||null;const sendQueue=sent&&sent.queue||[];const sendProviders=route.providerCalls;
   const expectedPart=c.part||((c.id.includes('P02')||c.id.includes('N07'))?'roof':'hood');const isAsk=c.expect==='ask';
   const validComplete=r=>r&&r.route==='edit'&&r.queue&&r.queue.length===1&&['edit','add'].includes(r.queue[0].kind)&&r.queue[0].spec&&r.queue[0].spec.region&&r.queue[0].spec.region.part===expectedPart&&r.queue[0].spec.color==='source'&&!r.queue[0].spec.pattern;
   const validAsk=r=>r&&(r.route==='ask'||r.offline===true)&&(!r.queue||r.queue.length===0)&&/clarif|safely|nothing was changed|could not/i.test(String(r.text||''));
   const routeResults=[direct,coreResult,offlineResult,askResult,sent];
   const quality=!c.extra||routeResults.every(r=>{const t=String(r&&r.text||'').toLowerCase();return t.includes(String(c.extra).toLowerCase())&&/nothing was changed/i.test(t)&&(/which part|names .* as its destination/i.test(t))&&/(layer over|replace it|separate change)/i.test(t);});
   const okay=isAsk?((!ed||validAsk(direct))&&validAsk(coreResult)&&validAsk(offlineResult)&&validAsk(askResult)&&validAsk(sent)&&askProviders===0&&sendProviders===0&&quality):([direct,coreResult,offlineResult,askResult,sent].every(validComplete)&&askProviders===0&&sendProviders===0);
   const rec={id:c.id,text:c.text,configured:c.configured,expected:c.expect,extra:c.extra||null,quality,editPlan:ed,compile:compiled&&{zones:compiled.zones,ask:compiled.ask,missing:compiled.missing},offlineCanHandle:route.offlineCanHandle(c.text),direct:{route:direct&&direct.route,text:direct&&direct.text,queue:directQueue},offlineAsk:{value:offlineResult,route:offlineResult&&offlineResult.route,text:offlineResult&&offlineResult.text,queue:offlineResult&&offlineResult.queue||[]},offlineAskCore:{value:coreResult,route:coreResult&&coreResult.route,text:coreResult&&coreResult.text,queue:coreResult&&coreResult.queue||[]},ask:{value:askResult,route:askResult&&askResult.route,text:askResult&&askResult.text,queue:askQueue,providerCalls:askProviders},send:{error:sendError,route:sent&&sent.route,text:sent&&sent.text,queue:sendQueue,providerCalls:sendProviders},okay};results.push(rec);if(!okay)blockers.push(rec);
 }
 const priorOraclePath=path.join(root,'_easy_claude_work/ai14h_w52_candidate/oracle.json');
 const report={review:'W63 actual-route clarification quality for unsupported preservation compounds',date:'2026-10-04',status:blockers.length?'BLOCKED':'PASS',oracle:{sha256:oracleSha,w58Cases,w63Oracle:freshCases},priorW52ParserOracle:{path:'_easy_claude_work/ai14h_w52_candidate/oracle.json',sha256:sha(priorOraclePath),unchanged:true,cases:w52Oracle.fresh_cases.length,results:w52ParserResults},priorW58RouteOracle:{path:'tests/ai_w58_route_atomicity_review_contract.cjs',sha256:sha(w58TestPath),candidateBaseSha256:'c191d049dde8d2f89eec5f62f12fb16053bedd2ba9217a03879a5f4e9f9421e2',cases:w58Cases.length,unchanged:true},baseHashes:{parser:'0dcf869f92ca3d33f194113f8bb7115d8461fd6f09aac6b6031d68a5766eac48',controller:'c191d049dde8d2f89eec5f62f12fb16053bedd2ba9217a03879a5f4e9f9421e2'},sourceHashes:{candidate:Object.fromEntries(Object.entries(files).map(([n,p])=>[n,sha(p)])),w63Oracle:sha(w63OraclePath),reviewTest:sha(__filename)},counts:{total:results.length,passed:results.filter(x=>x.okay).length,failed:blockers.length,providerCalls:results.reduce((n,x)=>n+x.ask.providerCalls+x.send.providerCalls,0)},results,blockers,limits:['Actual frozen W58 controller and isolated W63 parser/controller candidate functions were executed in a VM; zone batch, operation lifecycle and provider effects were mocked. No provider or native calls occurred.','This confirms parser/compiler copy and route text/queue behavior only; no live application or canvas paint was exercised.','The added parser branch only clarifies when preservation wording co-occurs with an unsupported second action and existing parser uncertainty. It does not claim to support or apply texture actions.']};
 fs.mkdirSync(path.join(root,'docs/handoff_reports'),{recursive:true});fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_W63_CLARIFICATION_QUALITY_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,counts:report.counts,blockers:blockers.map(b=>({id:b.id,configured:b.configured,quality:b.quality,ask:b.ask,send:b.send}))},null,2));if(blockers.length)process.exitCode=2;
}
run().catch(e=>{console.error(e);process.exitCode=1;});
