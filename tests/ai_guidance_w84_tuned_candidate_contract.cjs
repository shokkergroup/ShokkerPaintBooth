'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const candidate='_easy_claude_work/ai14h_w84_review/tuned_candidate/spb-self-help.js';
const knowledge='_easy_claude_work/ai14h_generation3_audit/frozen-runtime1/js/spb-ai-knowledge.js';
const baseline='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-self-help.js';
const controller='_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-pro-ai.js';
const oracle='_easy_claude_work/ai14h_w84_guidance_fresh_oracle.json';
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const sha=p=>digest(fs.readFileSync(path.join(root,p)));
assert.equal(sha(baseline),'a25febd091b6d13ee2b3aaf3713f21a2fa720c0f240a6b042cd6defd023cf783','keep the reviewed integration9 helper immutable');
assert.equal(sha(controller),'aae99cdd02b00bdd78d1f02fed85c18bc72b82cab9a66ceb7e0e3590ec3e8790','run the actual reviewed controller hook');
assert.equal(sha(oracle),'f9ee48e767fc6d2808fa0c9e341fbafc03fe60cf675e515cca315d4491e87436','keep the pre-inspection oracle immutable');
const cases=JSON.parse(fs.readFileSync(path.join(root,oracle),'utf8')).cases;
assert.equal(cases.length,20);
let providerCalls=0;
const w={console,fetch(){providerCalls++;throw Error('provider forbidden');},_spbLayerRev:3,selectedZoneIndex:0,_psdLayers:[],paintImageData:{width:8,height:8},zones:[],document:{body:{classList:{contains(){return false;}}}}};w.window=w;
w.SPBSourceLoadTransaction={getGeneration:()=>5,getCommittedGeneration:()=>5,isLoading:()=>false,isCommitted:()=>true,getCommittedPath:()=> 'C:/paint/car.psd',getCommittedFingerprint:()=> 'file-sha256:'+ 'a'.repeat(64)};
w.SpbProCar={map:()=>({}),missing:()=>[],signature:()=> 'layout-5'};
vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(root,knowledge),'utf8'),w);vm.runInContext(fs.readFileSync(path.join(root,candidate),'utf8'),w);
const controllerText=fs.readFileSync(path.join(root,controller),'utf8');
function extract(name,next){const start=controllerText.indexOf('function '+name+'(');assert(start>=0,'missing controller '+name);const end=controllerText.indexOf('function '+next+'(',start+1);assert(end>start,'missing controller marker '+next);return controllerText.slice(start,end);}
vm.runInContext(`var window=globalThis,SH=window.SpbSelfHelp,SH_FIRST_RE=/^(?:how|what|where|which|can|tell me|show me how)/i,START_OVER_RE=/$a/,CHECK_AGAIN_RE=/$a/,_advLast=null,E=null,D=null;function elemOwnsText(){return false}function complaintOf(){return false}function supportClass(){return null}function advisorIntent(){return false}\n`+extract('selfHelpClaim','selfHelpResult')+extract('selfHelpResult','selfHelpSig')+`this.claim=selfHelpClaim;this.helpResult=selfHelpResult;`,w);
const rules={
 'G01':[/flattened means|combined into one image/i,/separate editable layers/i],
 'G02':[/still edit|edit the flattened image/i,/single composite/i,/layered source/i],
 'G03':[/cannot|not contain enough information/i,/reconstruct/i,/layered source|original layered PSD/i],
 'G04':[/number layer/i,/LAYERS/i], 'G05':[/eye control|show or hide/i],
 'G06':[/clearcoat/i,/blue B \/ COAT/i,/R \/ METAL/i,/G \/ ROUGH/i],
 'G09':[/built-in helper/i,/API key/i,/Undo/i], 'G10':[/scoped paint edits/i,/material-channel/i,/external AI/i],
 'G11':[/Save \/ Open/i,/source-paint path/i,/does not bundle the original PSD/i],
 'G12':[/source-paint path/i,/moved/i,/where the project expects/i],
 'G13':[/does not guarantee a separate approval-preview step/i,/exact part or area/i,/manual zone controls/i],
 'G14':[/selected zone|hood|area/i,/only|one part/i],
 'G15':[/does not guarantee automatic tracing/i,/transparent|clean image/i],
 'G16':[/image file|image layer/i,/Move|scale|rotate/i],
 'G17':[/authored base-color/i,/Use solid color/i,/Use source paint \(spec only\)/i],
 'G18':[/AI answer Undo/i,/later manual same-zone mask edit/i,/skips fields changed afterward/i,/separate from Ctrl\+Z or History/i,/does not establish behavior for every layer-pixel or transform edit/i],
 'G19':[/Ctrl\+Z|History/i]
};
const rows=[];
for(const c of cases){
  const cls=w.SpbSelfHelp.classify(c.input), answer=w.SpbSelfHelp.answer(c.input,{paint:'psd',layers:[{name:'Body'}],zones:[{name:'Roof'}],selected:0,mode:'pro'});
  if(['G07','G08','G20'].includes(c.id)){
    assert.equal(cls,null,c.id+' is an action/ambiguous mutation and must stay with the edit owner');
    assert.equal(answer,null,c.id+' must not be claimed as passive help');
    assert.equal(w.claim(c.input),null,c.id+' must be declined by actual controller selfHelpClaim');
    rows.push({id:c.id,pass:true,route:'edit-owner',queue:0});
    continue;
  }
  assert.ok(cls,c.id+' should classify as guidance'); assert.ok(answer,c.id+' should return guidance');
  const text=String(answer.text||'');
  const need=rules[c.id]||[];
  assert.ok(need.length,c.id+' has an explicit semantic assertion');
  for(const re of need) assert.match(text,re,c.id+' answer missing '+re);
  assert.equal(answer.doIt,null,c.id+' guidance must remain passive');
  assert.ok(Array.isArray(answer.steps));
  const claimed=w.claim(c.input);assert.ok(claimed&&claimed.text,c.id+' actual controller hook should claim passive guidance');
  const routed=w.helpResult(claimed);assert.equal(routed.queue.length,0);assert.equal(routed.calls,0);assert.equal(routed.tools[0],'self_help');
  rows.push({id:c.id,pass:true,route:'actual-selfHelpClaim/selfHelpResult',queue:routed.queue.length,text:text.slice(0,220)});
}
const fresh=[
  {input:'How do I make clearcoat stronger without changing metal or roughness?',need:[/blue B \/ COAT/i,/leave R \/ METAL and G \/ ROUGH unchanged/i]},
  {input:'Can I get app help and local finish suggestions without an API key?',need:[/without an API key/i,/optional/i]},
  {input:'Paint only the roof green',action:true},
  {input:'Make the hood chrome',action:true},
  {input:'What does a flattened PSD lose?',need:[/separate editable layers/i]}
];
for(const c of fresh){const cls=w.SpbSelfHelp.classify(c.input), a=w.SpbSelfHelp.answer(c.input,{paint:'psd',layers:[],zones:[],selected:-1,mode:'pro'});if(c.action){assert.equal(cls,null,c.input);assert.equal(a,null,c.input);assert.equal(w.claim(c.input),null,c.input+' actual controller hook');}else{assert.ok(cls&&a,c.input);for(const re of c.need)assert.match(a.text,re,c.input);assert.equal(a.doIt,null);const routed=w.helpResult(w.claim(c.input));assert.equal(routed.queue.length,0,c.input);assert.equal(routed.calls,0,c.input);}rows.push({fresh:true,input:c.input,pass:true,route:c.action?'edit-owner':'actual-selfHelpClaim/selfHelpResult',queue:0});}
assert.equal(providerCalls,0);
console.log(JSON.stringify({status:'TUNED_PRIVATE_CANDIDATE_PASS',frozenOracleCases:20,passed:rows.length,semanticClaims:rows.filter(r=>r.route==='actual-selfHelpClaim/selfHelpResult').length,imperativesLeftToEditOwner:rows.filter(r=>r.route==='edit-owner').length,rows,controllerSha256:sha(controller),baselineSha256:sha(baseline),candidateSha256:sha(candidate),oracleSha256:sha(oracle),providerCalls,nativeCalls:0,limit:'Actual selfHelpClaim/selfHelpResult functions were executed with unrelated controller dependencies stubbed. Retained W74 actual offlineAskCore route contract was also run; no UI/native painting or provider effects.'},null,2));
