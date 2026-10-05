'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),base='_easy_claude_work/ai14h_generation3_runtime3/js/';
const original='_easy_claude_work/ai14h_generation3_candidate/w79_overlap/js/spb-pro-ai.js';
const candidate=process.argv[2]||'_easy_claude_work/ai14h_w80_review/candidate/spb-pro-ai.js';
const proBase=fs.readFileSync(path.join(root,original),'utf8'),proCandidate=fs.readFileSync(path.join(root,candidate),'utf8');
const oracleBytes=fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_w80_review/fresh-oracle.json'));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(digest(oracleBytes),'773912FBA0EF84D428CFBE20E21302DB11A9F3D6F7194810DB952113468D06EB');
assert.equal(digest(Buffer.from(proBase)),'B4A519D02419F6E5B21A9BC0DE6488C3124D7F3FC1BB2B52738F27B2F0617D1E','W79 base pin');
if(!process.argv[2]) assert.equal(digest(Buffer.from(proCandidate)),'3AD59719F47562ECC36C1C18FCD517D45F46ED28D79B6141BEBB9D86ABC8EAD9','W80 candidate pin');
function extract(source,signature){const start=source.indexOf(signature);assert(start>=0,'missing '+signature);const brace=source.indexOf('{',start);let depth=0,q=null,esc=false,line=false,block=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;else if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw Error('unterminated '+signature);}
const H=require('../_easy_claude_work/stack_h.js');
const design=fs.readFileSync(path.join(root,base+'spb-pro-design.js'),'utf8'),edit=fs.readFileSync(path.join(root,base+'spb-pro-edit.js'),'utf8');
assert.equal(digest(Buffer.from(design)),'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8','Runtime3 design pin');
assert.equal(digest(Buffer.from(edit)),'99703873013E198857D9ACEAA334821098E53DCAA9D55E14DBD1EC50E58604DE','Runtime3 edit pin');
const runtime=H.load();vm.runInContext(design,runtime);vm.runInContext(edit,runtime);const E=runtime.SpbProEdit;
const qNames=['partRegionKey','editKey','hasPriorPartIdentity','queueEditZones'];
function run(source,ask,opts={}){
 const zone=opts.zone||{id:'manual-green-roof',name:'Roof green',muted:false,baseColorMode:'solid',baseColor:'#168a45',base:'base::gloss',useRegion:true,regionMask:new Uint8Array([1,1,1,1])};
 const _reg=opts.registry||{};const context=vm.createContext({Object,String,RegExp,JSON,Array,Number,Math,Error,Uint8Array,Promise,console:{warn(){}},E,env:null});
 const qCode=qNames.map(n=>extract(source,'function '+n+'(')).join('\n');
 const selected=source===proCandidate?['explicitCurrentPaintRequest','currentPartOwnerVerifiedForRegion','unprovedCurrentPaintPartAdd','offlineEditAsk','offlineAskCore']:['offlineEditAsk','offlineAskCore'];
 const routeCode=(source.includes('function normalizeOfflineInstruction(')?['normalizeOfflineInstruction']:[]).concat(selected).map(n=>extract(source,'function '+n+'(')).join('\n');
 const env={palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#eeeeee',share_pct:11}],layers:[],zoneColours:[{hex:'#168a45',zone_id:String(zone.id),zone:String(zone.name),index:0,share_pct:12,selects_pct:12,finish:'base::gloss',layers:[]}],currentPartZoneOwners:opts.currentPartZoneOwners||(()=>[])};
 const prelude=`var D={},window={SpbProElements:{sig:function(){return 'elements';}}},zones=[${JSON.stringify(Object.assign({},zone,{regionMask:null}))}],_editReg=${JSON.stringify(_reg)},_editRegSig='car-A',_editRegPendingBefore={},CAR={missing:function(){return [];},layoutSig:function(){return 'layout';}},_psdLayers=[],_busy=false,_progress='',_reqText='',_specOnlyReq=false,_beforeImg=null,_advLast=null,_forcedIdeaCols=null,_advRejected=[],_advDislikes=[],_offlineLast=null,_absent={},_skipParts=false;
function carSig(){return 'car-A';} function operationCurrent(){return true;} function operationCanceled(){return {offline:true,queue:[],text:'canceled'};} function operationRelease(){} function render(){} function captureOriginal(){} function elementRunCurrent(){return true;} function offlineInstructionPreflight(){return null;} function advisorOwns(){return false;} function offlineMaterialPlan(){return null;} function intentSpecOnly(){return false;} function editPlan(t){return E.plan(t,editEnv());} function editEnv(){return env;} function prepEnv(){return Promise.resolve(env);} function warm(){return Promise.resolve();} function elementKinds(){return [];} function exclTargets(){return [];} function editReply(text,chips,extra){return Object.assign({offline:true,text,queue:[],tools:[]},extra||{});} function operationTools(_,queue){return [{name:'add_zone',handler:function(spec){queue.push({kind:'add',spec:JSON.parse(JSON.stringify(spec))});return {region_check:{share_pct:12}};}},{name:'edit_zone',handler:function(spec){queue.push({kind:'edit',spec:JSON.parse(JSON.stringify(spec))});return {};} }];} function makeTools(){return [];} function markPartFollowupQueue(){} function friendlyZoneError(e){return String(e);} function editPlural(){return false;} function editOverlapNote(){return '';} function editOverlapKinds(){return [];} function exclNotes(){return [];} function elementPaintChangedResult(){return {offline:true,queue:[]};} function selfHelpClaim(){return null;} function selfHelpResult(){return null;} function offlineHowto(){return null;} function offlineScopeReply(){return {offline:true,text:'clarify',queue:[]};}
function normaliseSpec(s){return s;} function protectDecals(){} function scopedPartProofAt(){return null;} function scopedPartProofMatches(a,b){return JSON.stringify(a)===JSON.stringify(b);} function partOwnerCurrent(z,key){return ${opts.ownerVerified?'!!(z&&z.id===\'verified-roof\')':'false'};}
`;
 context.env=env;
 vm.runInContext(qCode+'\n'+routeCode+'\n'+prelude+`\nthis.run=function(){return Promise.resolve(offlineAskCore(${JSON.stringify(ask)},{_spbOperation:{collection:{}}}));};`,context);
 context.zones[0].regionMask=new Uint8Array(zone.regionMask||[1,1,1,1]);
 const out=context.run();return Promise.resolve(out).then(result=>({result,zone,context}));
}
(async()=>{
 const ask='Make only the roof chrome, keep its current paint.';
 const base=await run(proBase,ask),candidateResult=await run(proCandidate,ask);
 assert.equal(base.result.queue.length,1,'W79 baseline routes to one queued source-color part add');
 assert.equal(base.result.queue[0].spec.color,'source');
 assert.equal(candidateResult.result.queue.length,0,'candidate refuses when no unique current helper owner is verified');
 assert.match(candidateResult.result.text,/cannot verify|original paint|not queued/i);
 const noPreserve=await run(proCandidate,'Make only the roof chrome.');
 assert.equal(noPreserve.result.queue.length,1,'guard does not block an otherwise supported finish request');
 const explicitColor=await run(proCandidate,'Make only the roof blue.');
 assert.equal(explicitColor.result.queue.length,1,'explicit color edit remains delegated');
 assert.equal(explicitColor.result.queue[0].spec.color,'#1450b4');
 const mask=new Uint8Array([1,1,1,1]);let h=2166136261;for(let i=0;i<mask.length;i++)h=Math.imul(h^(Number(mask[i])&255),16777619);const zone={id:'verified-roof',name:'Owned Roof',muted:false,useRegion:true,regionMask:mask,_aiPartProv:{r:JSON.stringify({part:'roof'}),z:mask.length+':'+(h>>>0).toString(36),l:'layout',e:'elements'}};
 const key='{"x":[],"c":[],"l":[],"p":"roof","e":false,"el":"","pr":"{}"}';
 const validOwner=await run(proCandidate,ask,{zone,registry:{[key]:'Owned Roof'},ownerVerified:true});
 assert.equal(validOwner.result.queue.length,1,'verified registered-owner positive control remains editable: '+JSON.stringify(validOwner.result));
 assert.equal(validOwner.result.queue[0].kind,'edit');
 assert.equal(validOwner.result.queue[0].spec.zone_id,'verified-roof');
 assert.equal(validOwner.result.queue[0].spec.color,undefined,'source-color followup omits color on an owned zone');
 assert.equal(validOwner.result.queue[0].spec.finish,'base::f_chrome');
 console.log(JSON.stringify({status:'PASS_WITH_CONSERVATIVE_REFUSAL',frozenCases:12,routeCases:4,baselineManualKeepQueued:base.result.queue.length,manualKeepCandidateQueue:candidateResult.result.queue.length,manualKeepReply:candidateResult.result.text,ordinaryFinishQueue:noPreserve.result.queue.length,explicitColorQueue:explicitColor.result.queue.length,verifiedOwnerQueue:validOwner.result.queue.length,verifiedOwnerOperation:validOwner.result.queue[0],sourceHash: digest(Buffer.from(proCandidate)),providerCalls:0,nativeCalls:0},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
