'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'_easy_claude_work/ai14h_w101_review'),oraclePath=path.join(root,'_easy_claude_work/ai14h_w106_review/fresh-oracle.json');
const oracleBytes=fs.readFileSync(oraclePath),oracle=JSON.parse(oracleBytes),sha=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(sha(oracleBytes),'75F2F276159DB73956FED6431570B3A036736F82A78BF8BAB1FEF6554A54DDC4');assert.equal(oracle.cases.length,16);
const modulePath=path.join(dir,'spb-ai-material-controls.candidate.js'),controllerPath=path.join(dir,'spb-pro-ai.candidate.js'),selfHelpPath=path.join(root,'_easy_claude_work/ai14h_generation3_runtime5/js/spb-self-help.js');
assert.equal(sha(fs.readFileSync(modulePath)),'30B18516A3F13DD7854F6EF36FDF5EB7A37985537E63C4C6405FEFA690C6BAEC');assert.equal(sha(fs.readFileSync(controllerPath)),'D05FD03D8E50151F7888D7E32C0D92AC661864EB989A3B7F9F9541C7692AE4E2');const selfHelpBytes=fs.readFileSync(selfHelpPath),selfHelpSha=sha(selfHelpBytes);
const source=fs.readFileSync(controllerPath,'utf8');
function extractFunction(src,name){const at=src.indexOf('function '+name+'(');assert(at>=0,'missing '+name);const open=src.indexOf('{',at);let d=0,q=null,esc=false,line=false,block=false;for(let i=open;i<src.length;i++){const c=src[i],n=src[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;else if(c==='}'&&--d===0)return src.slice(at,i+1);}throw Error('unterminated '+name);}
function routerWorld(part,controls){
 const queued=[],zone={id:'fixture-'+part,name:'helper '+part,specShiftR:13,specShiftG:27,specShiftB:31,color:'#123456',finish:'fixture'};
 const route={window:{SpbMaterialControls:controls},document:{getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]},localStorage:{getItem:()=>null,setItem:()=>{}},sessionStorage:{getItem:()=>null,setItem:()=>{}},String,RegExp,Promise,Object,Number,Math,console,_spbOperation:{collection:1},_busy:false,_progress:'',_advLast:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,
  offlineInstructionPreflight:()=>null,operationCurrent:()=>true,operationCanceled:()=>({cancelled:true}),operationRelease:()=>{},editPlan:()=>null,advisorOwns:()=>false,captureOriginal:()=>{},
  editReply:(text,chips,extra)=>{if(extra&&Array.isArray(extra.queue))queued.push(...extra.queue);return {text,chips:chips||null,...(extra||{})};},render:()=>{},warm:()=>Promise.resolve(),editEnv:()=>({}),
  E:{plan:text=>{const m=/make only the (.+) blue/i.exec(text);return m?{kind:'ops',exactPart:true,ops:[{target:{kind:'part',part:m[1]}}]}:null;}},normaliseSpec:x=>x,protectDecals:()=>{},editKey:r=>r.part,carSig:()=> 'car-fixture',_editRegSig:'car-fixture',_editReg:{},zones:[zone],partOwnerCurrent:(z,key)=>!!z&&key===part&&z.name===('helper '+part),operationTools:tools=>tools,
  makeTools:queue=>[{name:'edit_zone',handler:edit=>{queue.push(JSON.parse(JSON.stringify(edit)));return {ok:true};}}]};
 route._editReg[part]=zone.name;vm.createContext(route);vm.runInContext(selfHelpBytes.toString('utf8'),route,{filename:selfHelpPath});
 const actual=[extractFunction(source,'normalizeOfflineInstruction'),'function offlineInstructionPreflight(text){return null;}',extractFunction(source,'offlineMaterialPlan'),extractFunction(source,'offlineMaterialAsk'),extractFunction(source,'offlineAsk'),extractFunction(source,'selfHelpResult')].join('\n')+'\nthis.routeAsk=offlineAsk;this.materialPlan=offlineMaterialPlan;this.materialAsk=offlineMaterialAsk;';vm.runInContext(actual,route);
 return {route,zone,queued};
}
const controls=require(modulePath),expected={
 'W106-01':{kind:'edit',part:'roof',channel:'clearcoat',delta:20},
 'W106-02':{kind:'edit',part:'roof',channel:'clearcoat',delta:20},
 'W106-03':{kind:'edit',part:'roof',channel:'clearcoat',delta:20},
 'W106-04':{kind:'edit',part:'roof',channel:'clearcoat',delta:-20},
 'W106-05':{kind:'clarify'},'W106-06':{kind:'clarify'},'W106-07':{kind:'clarify'},'W106-08':{kind:'clarify'},'W106-09':{kind:'clarify'},
 'W106-10':{kind:'clarify'},'W106-11':{kind:'clarify'},'W106-12':{kind:'delegate'},'W106-13':{kind:'clarify'},'W106-14':{kind:'clarify'},'W106-15':{kind:'delegate'},'W106-16':{kind:'delegate'}
};
async function main(){
 const rows=[];
 for(const c of oracle.cases){
  const exp=expected[c.id],parsed=controls.parse(c.text),world=routerWorld(exp.part||'roof',controls),before=JSON.parse(JSON.stringify(world.zone));
  let reply=null,routePlan=world.route.materialPlan(c.text);
  if(routePlan&&routePlan.kind==='edit')reply=await world.route.routeAsk(c.text,{_spbOperation:world.route._spbOperation});
  else if(['W106-15','W106-16'].includes(c.id))reply=await world.route.routeAsk(c.text,{_spbOperation:world.route._spbOperation});
  else if(routePlan&&routePlan.kind==='clarify')reply=await world.route.materialAsk(c.text,routePlan,{_spbOperation:world.route._spbOperation});
  let pass=parsed.kind===exp.kind;
  if(exp.kind==='edit'){
   pass=pass&&parsed.part===exp.part&&parsed.channel===exp.channel&&parsed.delta===exp.delta&&routePlan&&routePlan.kind==='edit'&&world.queued.length===1&&world.queued[0].zone_id===world.zone.id&&world.queued[0]._spbPartRegKey===exp.part;
   const wanted={metal:13,rough:27,clearcoat:31},slot=exp.channel==='clearcoat'?'clearcoat':exp.channel==='roughness'?'rough':'metal';wanted[slot]=Math.max(-127,Math.min(127,wanted[slot]+exp.delta));
   if(pass){assert.deepEqual(world.queued[0].spec_shift,wanted,c.id+' changes only the requested channel');assert.deepEqual(world.zone,before,c.id+' queues without eager mutation');}
  } else if(exp.kind==='clarify') pass=pass&&routePlan&&routePlan.kind==='clarify'&&!!reply&&world.queued.length===0;
  else pass=pass&&routePlan===null&&world.queued.length===0;
  if(exp.kind!=='edit')assert.deepEqual(world.zone,before,c.id+' leaves current zone unchanged');
  rows.push({id:c.id,pass,parsed:{kind:parsed.kind,reason:parsed.reason||null,part:parsed.part||null,channel:parsed.channel||null,delta:parsed.delta==null?null:parsed.delta},route:routePlan&&routePlan.kind||null,queued:world.queued.length,reply:reply&&reply.text||null});
 }
 const out={oracleSha256:sha(oracleBytes),moduleSha256:sha(fs.readFileSync(modulePath)),controllerSha256:sha(fs.readFileSync(controllerPath)),selfHelpSha256:selfHelpSha,counts:{cases:rows.length,passed:rows.filter(x=>x.pass).length,failed:rows.filter(x=>!x.pass).length},rows,effects:{providerCalls:0,nativeCalls:0,serverCalls:0,paintApplications:0}};
 console.log(JSON.stringify(out,null,2));if(out.counts.failed)process.exitCode=1;
}main().catch(e=>{console.error(e.stack||e);process.exitCode=1;});






