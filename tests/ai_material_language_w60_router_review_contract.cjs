'use strict';
// W60 fresh cases are written before candidate source bytes are read.
const FRESH_ORACLE = Object.freeze([
  {id:'left-side-panel-clearcoat-synonym',text:'Increase clear coat on the left side panel by 14 points.',kind:'edit',part:'left side',channel:'clearcoat',delta:14},
  {id:'boot-metallic-channel-synonyms',text:'Reduce metallic channel on the boot by 7 points.',kind:'edit',part:'trunk',channel:'metalness',delta:-7},
  {id:'truck-bed-roughness',text:'Raise roughness on the truck bed by 20 points.',kind:'edit',part:'bed',channel:'roughness',delta:20},
  {id:'unitless-retains-clearcoat-roof',text:'Increase clearcoat on the roof by 20.',kind:'clarify',part:'roof',channel:'clearcoat',question:/clearcoat.*roof.*points/i},
  {id:'clearcoat-hood-positive-synonym',text:'Increase clear coat on the hood by 20 points.',kind:'edit',part:'hood',channel:'clearcoat',delta:20},
  {id:'material-channel-with-exact-target-asks-channel',text:'Raise material channel on spoiler by 12 points.',kind:'clarify',question:/which material channel|which channel/i},
  {id:'comparative-shinier-preserve-roughness',text:'Make clearcoat on the roof shinier while keeping roughness unchanged.',kind:'clarify'},
  {id:'explicit-preservation-ambiguity',text:'Raise clearcoat on the roof by 10 points, but preserve metalness.',kind:'clarify'},
  {id:'negated-clearcoat-is-no-op',text:"Don't increase clearcoat on the roof.",kind:'clarify'},
  {id:'extra-paint-action-is-no-op',text:'Increase clearcoat on the roof by 10 points and make the hood red.',kind:'clarify'},
  {id:'two-channel-actions-are-no-op',text:'Increase clearcoat on the roof by 10 points and raise hood roughness by 5 points.',kind:'clarify'},
  {id:'relative-edit-with-preserved-roughness-clarifies',text:'Raise clearcoat on roof by 10 points and keep roughness unchanged.',kind:'clarify'},
  {id:'right-side-panel-target-alias',text:'Increase clearcoat on the right side panel by 6 points.',kind:'edit',part:'right side',channel:'clearcoat',delta:6},
  {id:'bonnet-target-alias',text:'Lower clearcoat on the bonnet by 5 points.',kind:'edit',part:'hood',channel:'clearcoat',delta:-5},
  {id:'specular-channel-stays-ambiguous',text:'Raise specular channel on the spoiler by 20 points.',kind:'clarify',question:/which material channel|which channel/i}
]);

const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..'),w54root=path.join(root,'_easy_claude_work/ai14h_w54_candidate');
const candidateAI=path.join(w54root,'js/spb-pro-ai.js'),candidateControls=path.join(w54root,'js/spb-ai-material-controls.js');
const manifestPath=path.join(root,'_easy_claude_work/ai14h_generation3_runtime1/source-freeze.json');
const auditManifestPath=path.join(root,'_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/audit-manifest.json');
const priorReport=JSON.parse(fs.readFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_MATERIAL_LANGUAGE_W54_CANDIDATE_2026-10-04.json'),'utf8'));
const runtimeManifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
const auditManifest=JSON.parse(fs.readFileSync(auditManifestPath,'utf8'));
function sha(file){return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase();}
assert.equal(sha(auditManifestPath),'C6EF714541E85A12CD913E2D8FBBFD9EF6411599EDFE7AA8AA46F44365E5CDBC','frozen runtime1 audit manifest changed');
assert.equal(auditManifest.generation,'gen3-runtime1');
assert.equal(runtimeManifest.hashes['js/spb-pro-ai.js'],priorReport.frozen_source.pro_ai_sha256.toLowerCase());
assert.equal(sha(candidateAI),priorReport.candidate.pro_ai_sha256);
assert.equal(sha(candidateControls),priorReport.candidate.material_controls_sha256);
const source=fs.readFileSync(candidateAI,'utf8'),controlSource=fs.readFileSync(candidateControls,'utf8');
const controls=require(candidateControls);
function extractFunction(src,name){const at=src.indexOf('function '+name+'(');assert(at>=0,'missing '+name);const open=src.indexOf('{',at);let d=0,q=null,esc=false,line=false,block=false;for(let i=open;i<src.length;i++){const c=src[i],n=src[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;else if(c==='}'&&--d===0)return src.slice(at,i+1);}throw Error('unterminated '+name);}
const baseline=cp.spawnSync(process.execPath,[path.join(w54root,'tests/ai_material_language_w54_candidate_contract.cjs')],{encoding:'utf8'});
assert.equal(baseline.status,0,'unchanged W54 oracle contract: '+baseline.stderr);
assert.match(baseline.stdout,/PASS 21 W54 frozen-oracle\/material-route checks/);

function routerWorld(part){
  const replies=[],queued=[],zone={id:'fixture-'+part,name:'helper '+part,specShiftR:13,specShiftG:27,specShiftB:31,color:'#123456',finish:'fixture'};
  const route={window:{SpbMaterialControls:controls},String,RegExp,Promise,Object,Number,Math,console,
    _spbOperation:{collection:1},_busy:false,_progress:'',_advLast:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,
    offlineInstructionPreflight:()=>null,operationCurrent:()=>true,operationCanceled:()=>({cancelled:true}),operationRelease:()=>{},
    editPlan:()=>null,advisorOwns:()=>false,captureOriginal:()=>{},
    editReply:(text,chips,extra)=>{const out={text,chips:chips||null,...(extra||{})};if(extra&&Array.isArray(extra.queue))queued.push(...extra.queue);replies.push(out);return out;},
    render:()=>{},warm:()=>Promise.resolve(),editEnv:()=>({}),
    E:{plan:text=>{const m=/make only the (.+) blue/i.exec(text);return m?{kind:'ops',exactPart:true,ops:[{target:{kind:'part',part:m[1]}}]}:null;}},
    normaliseSpec:x=>x,protectDecals:()=>{},editKey:r=>r.part,carSig:()=> 'car-fixture',_editRegSig:'car-fixture',
    _editReg:{},zones:[zone],partOwnerCurrent:()=>true,operationTools:tools=>tools,
    makeTools:queue=>[{name:'edit_zone',handler:edit=>{queue.push(edit);return {ok:true};}}]};
  route._editReg[part]=zone.name;
  vm.createContext(route);
  const actual=extractFunction(source,'offlineMaterialPlan')+'\n'+extractFunction(source,'offlineMaterialAsk')+'\n'+extractFunction(source,'offlineAsk')+'\nthis.routeAsk=offlineAsk;';
  vm.runInContext(actual,route);
  return {route,zone,replies,queued};
}

async function run(){
 const results=[];
 for(const c of FRESH_ORACLE){
  const part=c.part||'roof',w=routerWorld(part),before=JSON.parse(JSON.stringify(w.zone));
  const result=await w.route.routeAsk(c.text,{_spbOperation:w.route._spbOperation});
  if(c.kind==='edit'){
    assert.equal(w.queued.length,1,c.id+' queues exactly one material edit');
    const queued=w.queued[0];assert.equal(queued.zone_id,w.zone.id,c.id+' targets exact current helper zone');
    assert.equal(queued._spbPartRegKey,c.part,c.id+' keeps exact part key');
    const expected={metal:before.specShiftR,rough:before.specShiftG,clearcoat:before.specShiftB},slot=c.channel==='metalness'?'metal':c.channel==='roughness'?'rough':'clearcoat';expected[slot]+=c.delta;
    assert.deepEqual(queued.spec_shift,expected,c.id+' changes only requested channel');
    assert.deepEqual(w.zone,before,c.id+' queues but does not partially mutate source zone');
    assert.match(result.text,new RegExp(c.part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'i'));
    assert.match(result.text,new RegExp(c.channel,'i'));
    results.push({id:c.id,pass:true,kind:'queued-single-channel',queueCount:w.queued.length,part:c.part,channel:c.channel,delta:c.delta});
  } else {
    assert.equal(w.queued.length,0,c.id+' must not queue on ambiguity');
    assert.deepEqual(w.zone,before,c.id+' must not mutate zone before clarification');
    assert(result && result.text,c.id+' returns an actual router reply');
    if(c.question) assert.match(result.text,c.question,c.id+' retains useful exact clarification');
    results.push({id:c.id,pass:true,kind:'clarify-no-queue',queueCount:0,reply:result.text});
  }
 }
 const report={status:'PASS',task:'W60 independent actual material-router review',candidate:{path:'_easy_claude_work/ai14h_w54_candidate/js/spb-pro-ai.js',sha256:sha(candidateAI),controlsPath:'_easy_claude_work/ai14h_w54_candidate/js/spb-ai-material-controls.js',controlsSha256:sha(candidateControls),installed:false},frozenRuntime1:{manifestPath:'_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/audit-manifest.json',manifestSha256:sha(auditManifestPath),manifestProAISha256:runtimeManifest.hashes['js/spb-pro-ai.js'],runtime1ProAISha256:runtimeManifest.hashes['js/spb-pro-ai.js']},unchangedW54Oracle:{status:'PASS 21 W54 frozen-oracle/material-route checks',exitCode:baseline.status,stdout:baseline.stdout.trim()},freshOracle:FRESH_ORACLE,results,counts:{passed:results.length,total:results.length,providerCalls:0,nativeCalls:0,serverCalls:0},limits:['Runs actual offlineAsk, offlineMaterialPlan, offlineMaterialAsk, parse and buildEdit from the frozen W54 candidate in VM; only the edit-zone tool handler is a controlled queue sink.','Does not invoke native renderer, actual source zones, provider, server or browser. Clarifications and queue construction are verified; installation/runtime acceptance is separate.','No unit-policy relaxation; all positive changes use explicit relative points and one channel.']};
 fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_MATERIAL_LANGUAGE_W60_REVIEW_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,baseline:baseline.stdout.trim(),passed:results.length,total:results.length,failures:results.filter(x=>!x.pass)},null,2));
}
run().catch(e=>{console.error(e);process.exitCode=1;});
