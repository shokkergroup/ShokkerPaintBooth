// Frozen W34 request oracle: defined before inspecting the fallback source.
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const snap = path.join(root,'_easy_claude_work','ai14h_w34_sources','js');
const candidatePath = path.join(root,'_easy_claude_work','ai14h_w34_candidate','js');
const cases = [
  {id:'W34-01',text:'Make the roof matte black with a gold carbon-weave overlay, but keep its current paint color.',configured:false,expected:'clarify/no queue: black conflicts with preserve-color; unsupported overlay may not cause partial completion'},
  {id:'W34-02',text:'Make the roof matte black with a gold carbon-weave overlay, but keep its current paint color.',configured:true,expected:'clarify/no queue before provider or fallback'},
  {id:'W34-03',text:'Keep the roof current paint color and make it matte red.',configured:false,expected:'clarify/no queue: color contradicts preservation'},
  {id:'W34-04',text:'Keep the roof blue paint but recolor its carbon overlay gold.',configured:false,expected:'clarify/no queue unless both constrained layers are completely understood'},
  {id:'W34-05',text:'Make the roof matte and keep its current red paint.',configured:false,expected:'safe finish-only edit, no base-colour mutation'},
  {id:'W34-06',text:'Make only the roof chrome; keep its blue paint.',configured:false,expected:'safe finish-only edit, no base-colour mutation'},
  {id:'W34-07',text:'Make the roof black with a gold carbon-weave overlay.',configured:false,expected:'complete supported stack may proceed as whole atomic plan'},
  {id:'W34-08',text:'Make the roof satin and preserve the current paint color.',configured:false,expected:'safe finish-only edit'},
  {id:'W34-09',text:'Keep the current paint color; lower clearcoat on the roof by 10 points.',configured:false,expected:'delegate to supported material-channel route, not palette fallback'},
  {id:'W34-10',text:'Make the roof matte black, preserve its paint, and lower clearcoat.',configured:false,expected:'clarify/no queue: mixed contradictory color and separate material action'},
  {id:'W34-11',text:'How can I make the roof matte black with a gold carbon weave while keeping its paint color?',configured:false,expected:'answer/help or clarify; never partial mutation'},
  {id:'W34-12',text:'Make the roof matte black with a gold carbon-weave overlay, but keep its current paint color.',configured:false,expected:'repeat exact adversarial request through send-fallback route; clarify/no queue'}
];
const frozenSha='f561c10e14b68a4063474bba89dc35518fa418f789469bfc49c2956ffc2dba3c';
assert.strictEqual(crypto.createHash('sha256').update(JSON.stringify(cases)).digest('hex'),frozenSha,'W34 frozen requests changed');
const sourceHashes={'spb-pro-ai.js':'609b8ec85228f15d2cc9b3ab82cd692eb2ea90d258cf5045fd36448ad3c46c6b','spb-pro-design.js':'0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8','spb-pro-edit.js':'d940e6688b3ed5e8fa0514c8774e73a4a2b564ad723e507166248e3e97ac75d0'};
function source(name){const b=fs.readFileSync(path.join(snap,name));assert.strictEqual(crypto.createHash('sha256').update(b).digest('hex'),sourceHashes[name],name+' frozen bytes changed');return b.toString('utf8');}
const frozenAi=source('spb-pro-ai.js'), ds=source('spb-pro-design.js'), es=source('spb-pro-edit.js');
const ai=fs.readFileSync(path.join(candidatePath,'spb-pro-ai.js'),'utf8');
function extractFunction(src,name){const start=src.indexOf(`function ${name}(`);assert(start>=0,'missing actual '+name);const brace=src.indexOf('{',start);let d=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<src.length;i++){const c=src[i],n=src[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;if(c==='}'&&--d===0)return src.slice(start,i+1);}throw Error('unterminated '+name);}
const w={console,Promise,document:{}};w.window=w;vm.createContext(w);vm.runInContext(ds,w,{filename:'frozen D'});vm.runInContext(es,w,{filename:'frozen E'});vm.runInContext(fs.readFileSync(path.join(candidatePath,'spb-ai-complete-instruction-guard.js'),'utf8'),w,{filename:'W34 guard'});
const D=w.SpbProDesign,E=w.SpbProEdit,env={palette:[{hex:'#141416',share_pct:52},{hex:'#f2c500',share_pct:22},{hex:'#f1f1ee',share_pct:14},{hex:'#1347a8',share_pct:5}],layers:[]};
const route={window:w,console,Promise,D,E,AI:{cached:()=>({configured:false})},_busy:false,_skipParts:true,_absent:{},CAR:null,_offlineLast:null,_advLast:null,_advRejected:[],_advDislikes:[],_forcedIdeaCols:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,_progress:'',_editReg:{},_editRegPendingBefore:{},_editRegSig:'car',zones:[],_log:[],_progAI:false,_progT0:0,_progK:0,_progEnd:0,_panel:null,
  elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),editPlan:text=>E.plan(text,env),offlineFirst:()=>true,selfHelpClaim:()=>null,selfHelpResult:x=>x,offlineCanHandle:()=>false,offlineGaveUp:()=>false,logMiss(){},render(){},offlineAskCore(){route.fallbackCalls++;return Promise.resolve({offline:true,text:'fallback',queue:[{kind:'add'}]});},offlineInstructionPreflight:null,
  _preflightFallbackCalls:0,fallbackCalls:0,finish(r,text){route.finished={r,text};},elemCurrentCard:()=>null,elementPaintSig:()=>'',elementRunIdentity:()=>null,elemReplyAction:()=>null,runElemAction:()=>false,complaintChip:()=>false,complaintOf:()=>null,offlineComplaint:()=>null,selfHelpSig:()=>'',offlineMaterialPlan:()=>null,advisorIntent:()=>null,layerVisRequest:()=>null,offlineCannot:()=>null,NUM_FIX_RE:/$a/,NOT_ELEM_RE:/$a/,TEACH_RE:/$a/,QUESTION_RE:/^how\b/i,CHECK_AGAIN_RE:/$a/,START_OVER_RE:/^$a/,SMALL_HELLO_RE:/^$a/,SMALL_THANKS_RE:/^$a/,
  AI_cachedConfigured:false};
Object.assign(w,route);w.window=w;w.spbProAI=null;vm.createContext(route);for(const n of ['offlineInstructionPreflight','offlineAsk','offlineAskCore','offlineLookAsk','ask'])vm.runInContext(extractFunction(ai,n),route,{filename:'W34 proAI#'+n});
const sendStart=ai.indexOf('function send(text, o) {'),sendGuard=ai.indexOf("var guarded = offlineInstructionPreflight(text); if (guarded) { finish(guarded, text, 'ask'); return; }",sendStart);
assert(sendStart>=0&&sendGuard>sendStart,'actual send guard hook missing');vm.runInContext(ai.slice(sendStart,sendGuard)+"var guarded = offlineInstructionPreflight(text); if (guarded) { finish(guarded, text, 'ask'); return; }\n}",route,{filename:'W34 proAI#send-through-guard'});
const inspect=t=>w.SpbAICompleteGuard.inspect(t);
const guardedIds=new Set(['W34-01','W34-02','W34-03','W34-04','W34-10','W34-12']);
for(const c of cases){const got=inspect(c.text);assert.strictEqual(!!got,guardedIds.has(c.id),c.id+' guard classification wrong: '+JSON.stringify(got));}
async function routeCase(id,configured){const c=cases.find(x=>x.id===id);route.AI.cached=()=>({configured:!!configured});route._busy=false;route.fallbackCalls=0;let r;
 if(id==='W34-01')r=await route.offlineAskCore(c.text,{});
 else if(id==='W34-02')r=await route.ask(c.text,{});
 else if(id==='W34-03')r=await route.offlineAsk(c.text,{});
 else if(id==='W34-04')r=await route.offlineLookAsk(c.text,{query:'carbon weave',parts:['roof']},{});
 else if(id==='W34-10')r=await route.offlineAskCore(c.text,{});
 else {route.send(c.text,{});r=route.finished&&route.finished.r;}
 assert(r && Array.isArray(r.queue) && r.queue.length===0,id+' must stop with an empty queue');assert.strictEqual(route.fallbackCalls,0,id+' reached the downstream/provider fallback');return r;
}
(async()=>{
 const outputs=[];for(const id of ['W34-01','W34-03','W34-04','W34-10'])outputs.push({id,route:'actual offline entry-point guard',queue:(await routeCase(id,false)).queue.length});
 outputs.push({id:'W34-02',route:'actual ask() configured=true',queue:(await routeCase('W34-02',true)).queue.length});
 outputs.push({id:'W34-12',route:'actual send() entry point',queue:(await routeCase('W34-12',false)).queue.length});
 const valid=[];for(const id of ['W34-05','W34-06','W34-07','W34-08','W34-09','W34-11']){const c=cases.find(x=>x.id===id);valid.push({id,guard:inspect(c.text)?'blocked':'delegated'});}
 const report={id:'W34',status:'isolated-candidate-only',generated_utc:new Date().toISOString(),frozen_sources:sourceHashes,candidate_router_sha256:crypto.createHash('sha256').update(ai).digest('hex'),fresh_oracle:{count:cases.length,sha256:frozenSha,guarded_cases:Array.from(guardedIds),route_probes:outputs,nonblocking_cases:valid},candidate_module:'_easy_claude_work/ai14h_w34_candidate/js/spb-ai-complete-instruction-guard.js',expected_scope:['guard only concrete paint-color contradictions bundled with a preservation request','decline unresolved paint-preservation plus explicit overlay/weave/pattern transformations','ask before fallbacks or providers; no partial queue','questions/how-to and valid finish-only/source-color/material operations pass through'],limits:['Candidate is isolated; current live source is unchanged.','Route probes executed extracted real offlineAsk/offlineAskCore/offlineLookAsk/ask/send entry points with test dependencies, not full UI or real queue/tool integration.','No native paint, model/provider, browser, or renderer was used.','W34-07 and finish-only cases confirm the guard delegates; they do not certify the downstream result is complete.','Guard rejects the recognized contradiction and keep-color overlay ambiguity; it is not a general-purpose complete instruction parser.']};
 const out=path.join(root,'docs','handoff_reports','AI_HELPER_14H_ATOMIC_CONSTRAINTS_CANDIDATE_2026-10-03.json');fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(`W34 candidate: ${outputs.length} actual route guard probes stopped before fallback; ${valid.length} nonblocking cases delegated.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
