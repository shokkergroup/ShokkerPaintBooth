'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),oraclePath='_easy_claude_work/ai14h_w84_sourcecolor_review/fresh-oracle.json',basePath='_easy_claude_work/ai14h_generation3_runtime9/js/spb-self-help.js',candidatePath='_easy_claude_work/ai14h_w84_sourcecolor_candidate/spb-self-help.js';
const ob=fs.readFileSync(path.join(root,oraclePath)),oracle=JSON.parse(ob),sha=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
assert.equal(sha(ob),'6460FB73D186C8D7AB211C47613FADA3683B5FE68B23CE58DAB2636359B73707');
function load(p){let providers=0;const w={console,fetch:()=>{providers++;throw Error('provider forbidden');},zones:[],selectedZoneIndex:0,_psdLayers:[],paintImageData:{width:8,height:8},document:{body:{classList:{contains:()=>false}}}};w.window=w;vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(root,p),'utf8'),w,{filename:p});return {w,providers:()=>providers,sha:sha(fs.readFileSync(path.join(root,p)))};}
const baseline=load(basePath),candidate=load(candidatePath),state={mode:'pro',paint:'psd',selected:0,zones:[{id:'roof1',name:'Roof',colourMode:'solid',colour:'#1450b4',finishKey:'base::gloss'}],layers:[],elements:null};
assert.equal(candidate.sha,'E230A121127FC6B32C451C630028D3D2D10461B67819BF50F2B148195DB8DF4D');
function check(lib,c,s=state,hex='#1450b4'){const a=lib.w.SpbSelfHelp.handle(c.text,s),text=String(a&&a.text||'');let pass=!!a&&!a.doIt&&/Use solid color/i.test(text)&&new RegExp(hex,'i').test(text)&&/original imported (?:paint )?image/i.test(text);return {id:c.id,pass,doIt:!!(a&&a.doIt),output:text.slice(0,900)};}
const rows=oracle.cases.map(c=>({id:c.id,baseline:check(baseline,c),candidate:check(candidate,c)}));
for(const [id,text,hex] of [['SRC-X1','How do I keep the current blue color while changing the metallic finish?','#1450b4'],['SRC-X2','How do I keep the current green color while making the roof chrome?','#00aa55']]){
 const s={mode:'pro',paint:'psd',selected:0,zones:[{id:'roof1',name:'Roof',colourMode:'solid',colour:hex,finishKey:'base::gloss'}],layers:[],elements:null};
 const c={id,text};rows.push({id,baseline:check(baseline,c,s,hex),candidate:check(candidate,c,s,hex)});
}
const candidatePassed=rows.filter(x=>x.candidate.pass).length,baselinePassed=rows.filter(x=>x.baseline.pass).length;
const out={oracleSha256:sha(ob),baselineSha256:baseline.sha,candidateSha256:candidate.sha,counts:{cases:rows.length,baselineSemanticPass:baselinePassed,candidateSemanticPass:candidatePassed,failed:rows.length-candidatePassed},rows,effects:{providerCalls:baseline.providers()+candidate.providers(),nativeCalls:0,paintApplications:0},limit:'Actual SpbSelfHelp.handle/classify/howtoAnswer operate on a supplied authored-solid zone state; no native app, backend, provider, or paint mutation.'};console.log(JSON.stringify(out,null,2));if(candidatePassed!==rows.length)process.exitCode=1;
