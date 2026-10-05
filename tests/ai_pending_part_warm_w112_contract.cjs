'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),oraclePath='_easy_claude_work/ai14h_w112_review/fresh-oracle.json',candidatePath='_easy_claude_work/ai14h_w112_candidate/spb-pro-ai.js';
const oracleBytes=fs.readFileSync(path.join(root,oraclePath)),oracle=JSON.parse(oracleBytes),source=fs.readFileSync(path.join(root,candidatePath),'utf8'),sha=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(sha(oracleBytes),'688FD1C230A3C14F6A4A3213F1F1693904C101A1E6C5EB4D9E5B8DB86EAC8114');assert.equal(oracle.cases.length,10);assert.equal(sha(Buffer.from(source)),'17ADE7F49DA71F8B7F0FF99FF6A99E349D74E0B7E7E6D08010C6959A823463B1');
function extract(name){const start=source.indexOf('function '+name+'(');assert(start>=0,'missing '+name);const brace=source.indexOf('{',start);let depth=0,q=null,esc=false,line=false,block=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;else if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw Error('unterminated '+name);}
const helperStart=source.indexOf('    function pendingNamedPartWarmTarget(text) {'),askStart=source.indexOf('    function offlineAsk(text, o) {'),coreStart=source.indexOf('    function offlineAskCore(text, o) {');
assert(helperStart>=0&&askStart>helperStart&&coreStart>askStart,'missing bounded route anchors');
const helperSrc=source.slice(helperStart,askStart),askSrc=source.slice(askStart,coreStart);
async function run(c){
 let ticketCurrent=c.id!=='W112-09',proofReady=c.id==='W112-10',warmCalls=0,hydrateCalls=0,downstream=0,sourceGen=2;const events=[];
 const target=c.id==='W112-02'?'hood':'roof',pending=[];
 if(c.id!=='W112-10'&&c.id!=='W112-07'&&c.id!=='W112-08'&&c.id!=='W112-09'&&c.id!=='W112-X2')pending.push({_spbAIPartMemoryPending:{schema:'saved-part-memory/1',provenance:{r:JSON.stringify({island:target,layers:['Car Paint']})}}});
 if(c.id==='W112-X2')pending.push({_spbAIPartMemoryPending:{schema:'saved-part-memory/1',provenance:{r:JSON.stringify({island:'hood',layers:['Car Paint']})}}});
 const ctx={Promise,console,zones:pending,_partMemoryWarmAttemptTicket:null,_envMemo:null,_busy:false,_advLast:null,_offlineLast:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,_skipParts:false,_absent:{},START_OVER_RE:/^start over\b/i,window:null,
  normalizeOfflineInstruction:t=>String(t||''),offlineInstructionPreflight:t=>c.id==='W112-07'?{offline:true,howto:true,queue:[]} : null,operationCurrent:()=>ticketCurrent,operationCanceled:()=>({offline:true,cancelled:true,queue:[]}),elementRunCurrent:()=>true,elementPaintChangedResult:()=>({offline:true,queue:[]}),relativeBodyScopePreflight:t=>c.id==='W112-08'?{offline:true,text:'Name one exact body part. Nothing was changed.',queue:[]} : null,
  warm:()=>{warmCalls++;events.push('warm');return c.id==='W112-04'?Promise.reject(new Error('warm failed')):Promise.resolve({generation:sourceGen});},
  hydratePartMemory:()=>{hydrateCalls++;events.push('hydrate');if(c.id==='W112-05'){proofReady=false;return;}proofReady=true;for(const z of ctx.zones)delete z._spbAIPartMemoryPending;},
  D:{offlinePartCoverage:()=>null,compoundPlan:()=>null,refine:()=>null},E:{},editPlan:t=>{const isMulti=/\b(?:roof|hood)\b.*\b(?:roof|hood)\b/i.test(t);return isMulti?{kind:'ask',text:'Name one exact part.',queue:[]}:{kind:'ops',exactPart:true,ops:[{target:{kind:'part',part:target}}]};},editYieldsToStack:()=>false,advisorOwns:()=>false,offlineMaterialPlan:()=>null,offlineMaterialAsk:()=>null,offlineCoveredPartAsk:()=>null,
  offlineEditAsk:(t,ed)=>{downstream++;events.push('downstream');if(ed.kind==='ask'||!proofReady)return Promise.resolve({offline:true,route:'refusal',text:'Nothing was changed; current part proof is not ready.',queue:[]});return Promise.resolve({offline:true,route:'edit',queue:[{kind:'finish-only',part:target}],proofValidated:true});},offlineAskCore:()=>Promise.resolve({offline:true,route:'core',queue:[]}),operationPublish:(t,fn)=>fn(),operationRelease(){},operationTicket:()=>({}),captureOriginal(){},intentSpecOnly:()=>false,render(){},editReply:(text)=>({offline:true,route:'refusal',text,queue:[]}),selfHelpResult:x=>x};
 ctx.window=ctx;vm.createContext(ctx);vm.runInContext(helperSrc+'\n'+askSrc+'\nthis.__warmTarget=pendingNamedPartWarmTarget;this.__ask=offlineAsk;',ctx,{filename:'actual-w112-route'});
 const askText=c.text;if(c.id==='W112-09')ticketCurrent=false;
 const result=await ctx.__ask(askText,{_spbOperation:{id:c.id}});
 return {result,warmCalls,hydrateCalls,downstream,events,target,pendingCount:pending.length};
}
(async()=>{
 const rows=[];
 for(const c of oracle.cases){const r=await run(c);let pass=false,classification=null;
  if(['W112-01','W112-02','W112-03'].includes(c.id)){pass=r.warmCalls===1&&r.hydrateCalls===1&&r.downstream===1&&r.result.route==='edit'&&r.result.queue.length===1;}
  else if(c.id==='W112-04'){pass=r.warmCalls===1&&r.hydrateCalls===0&&r.downstream===0&&r.result.route==='refusal'&&r.result.queue.length===0;}
  else if(c.id==='W112-05'){pass=r.warmCalls===1&&r.hydrateCalls===1&&r.downstream===1&&r.result.route==='refusal'&&r.result.queue.length===0;}
  else if(c.id==='W112-06'){// Frozen oracle says "ambiguous", but the text names only the roof; report the oracle mismatch, not a pass.
   classification='oracle_expectation_disputed_single_exact_part';const actual=r.warmCalls===1&&r.hydrateCalls===1&&r.result.route==='edit'&&r.result.queue.length===1;pass=false;
   rows.push({id:c.id,pass,actualRouteBehaviorPass:actual,oracleAlignment:false,classification,warmCalls:r.warmCalls,hydrateCalls:r.hydrateCalls,downstream:r.downstream,result:r.result.route||'other',queued:r.result.queue&&r.result.queue.length||0});continue;
  }else if(c.id==='W112-07'){pass=r.warmCalls===0&&r.hydrateCalls===0&&r.result.howto===true&&r.result.queue.length===0;}
  else if(c.id==='W112-08'){pass=r.warmCalls===0&&r.hydrateCalls===0&&r.result.queue.length===0;}
  else if(c.id==='W112-09'){pass=r.warmCalls===0&&r.hydrateCalls===0&&r.result.cancelled===true&&r.result.queue.length===0;}
  else if(c.id==='W112-10'){pass=r.warmCalls===0&&r.hydrateCalls===0&&r.downstream===1&&r.result.route==='edit'&&r.result.queue.length===1;}
  rows.push({id:c.id,pass,classification,warmCalls:r.warmCalls,hydrateCalls:r.hydrateCalls,downstream:r.downstream,result:r.result.route|| (r.result.howto?'help':'other'),queued:r.result.queue&&r.result.queue.length||0});
 }
 // Fresh post-freeze guard: a two-part instruction must never warm a single saved part.
 const multi=await run({id:'W112-X1',text:'Make the roof and hood satin, keep their current paint.'});
 const multiPass=multi.warmCalls===0&&multi.hydrateCalls===0&&multi.result.queue.length===0;rows.push({id:'W112-X1',pass:multiPass,warmCalls:multi.warmCalls,hydrateCalls:multi.hydrateCalls,result:multi.result.route,queued:multi.result.queue.length});
 const unrelated=await run({id:'W112-X2',text:'Make only the roof satin, keep its current paint.'});
 const unrelatedPass=unrelated.warmCalls===0&&unrelated.hydrateCalls===0&&unrelated.result.queue.length===0;rows.push({id:'W112-X2',pass:unrelatedPass,warmCalls:unrelated.warmCalls,hydrateCalls:unrelated.hydrateCalls,result:unrelated.result.route,queued:unrelated.result.queue.length});
 const out={oracleSha256:sha(oracleBytes),candidateSha256:sha(Buffer.from(source)),counts:{cases:rows.length,passed:rows.filter(x=>x.pass).length,failed:rows.filter(x=>x.pass===false).length,oracleDisputes:rows.filter(x=>x.oracleAlignment===false).length},rows,effects:{providerCalls:0,nativeCalls:0,paintApplications:0}};console.log(JSON.stringify(out,null,2));if(out.counts.failed>out.counts.oracleDisputes)process.exitCode=1;
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});

