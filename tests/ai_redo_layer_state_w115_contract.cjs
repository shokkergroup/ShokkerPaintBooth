'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const beforePath='_easy_claude_work/ai14h_generation3_candidate/integration18/js/spb-pro-ai.js';
const afterPath='_easy_claude_work/ai14h_generation3_candidate/integration19/js/spb-pro-ai.js';
const oraclePath='_easy_claude_work/ai14h_w115_review/fresh-oracle.json';
const expected={before:'F88C962C94887D63C93AB775FE0B5AE3418A97F0AD0CC35A4C95A739719BEF4B',after:'1C178D2717D0ED654C1840AA01452F03322CFB9F3BA4716E2FE333F48D079430'};
const sha=s=>crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
const before=fs.readFileSync(path.join(root,beforePath),'utf8'),after=fs.readFileSync(path.join(root,afterPath),'utf8'),oracle=JSON.parse(fs.readFileSync(path.join(root,oraclePath),'utf8'));
assert.equal(sha(before),expected.before,'pre-fix integration18 snapshot pin');assert.equal(sha(after),expected.after,'integration19 snapshot pin');assert.equal(oracle.case_count,7);
function extract(source,name){const start=source.indexOf(`function ${name}(`);assert(start>=0,`actual ${name} exists`);const brace=source.indexOf('{',start);let depth=0,q=null,line=false,block=false,esc=false;for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw Error('unterminated '+name);}
const helpers=['ukOf','maskSig','undoMaskProof','zoneSig','layerState','layerSame','undoSigNow','undoSameZones','undoSameLayers','redoLast'];
function run(source,id){
 const layers=[{id:'paint-a',visible:true,opacity:100,blendMode:'source-over'},{id:'paint-b',visible:false,opacity:72,blendMode:'multiply'}];
 const zones=[{id:'roof-1',name:'Roof',baseColor:'#123456',regionMask:new Uint8Array([1,1,0,0]),useRegion:true}];
 const ctx={console,JSON,Object,Array,String,Number,Math,RegExp,Error,Uint8Array,ArrayBuffer,DataView,_ukSerial:0,zones,_psdLayers:layers,selectedZoneIndex:0,_log:[],_busy:false,_gen:0,_snapGen:0,_activeId:null,zoneUndoStack:[],_layerUndoStack:[],RECENT:{push(){}},operationEntryDocumentCurrent:()=>true,undoSnapTake:()=>({zones:ctx.undoSigNow().zones,layers:ctx.undoSigNow().layers}),undoDropPushed(){},undoApply(){ctx.applied++;},undoPushedSince:()=>[],undoSeal(){},render(){},applied:0,pushes:0};
 ctx.window={pushZoneUndo(){ctx.pushes++;}};vm.createContext(ctx);for(const n of helpers)vm.runInContext(extract(source,n),ctx,{filename:id+':'+n});
 const entry={role:'ai',undone:true,redoable:true,undoable:false,request:'Make the roof chrome',redoSnap:{zones:[],layers:[]},redoGuard:ctx.undoSigNow()};ctx._log.push(entry);
 if(id==='manual-visible-change')layers[0].visible=false;
 if(id==='manual-opacity-change')layers[0].opacity=64;
 if(id==='manual-blend-change')layers[0].blendMode='multiply';
 if(id==='zone-conflict')zones[0].baseColor='#c8102e';
 if(id==='layer-reordered')layers.reverse();
 if(id==='layer-removed')layers.pop();
 const value=ctx.redoLast();return {id,result:value,applied:ctx.applied,pushes:ctx.pushes,layerState:ctx.undoSigNow().layers,zones:ctx.undoSigNow().zones};
}
const beforeRows=oracle.cases.map(c=>run(before,c.id)),afterRows=oracle.cases.map(c=>run(after,c.id));
assert.equal(beforeRows[0].applied,1,'baseline unchanged redo succeeds');
for(const id of ['manual-visible-change','manual-opacity-change','manual-blend-change','layer-reordered','layer-removed'])assert.equal(beforeRows.find(x=>x.id===id).applied,1,'baseline demonstrates blind layer redo: '+id);
assert.equal(beforeRows.find(x=>x.id==='zone-conflict').applied,0,'baseline zone conflict already refuses');
assert.equal(afterRows.find(x=>x.id==='unchanged-layer-state').applied,1,'fixed unchanged redo still succeeds');
for(const id of ['manual-visible-change','manual-opacity-change','manual-blend-change','zone-conflict','layer-reordered','layer-removed']){const r=afterRows.find(x=>x.id===id);assert.equal(r.applied,0,'fixed redo refuses '+id);assert.equal(r.pushes,0,'fixed refusal must not push undo stack '+id);}
assert.equal(afterRows.find(x=>x.id==='unchanged-layer-state').pushes,1,'positive redo pushes exactly one stack step');
const report={work_item:'W115 independent Redo layer-state guard review',status:'PASS_WITH_LIMITS',oracle:{path:oraclePath,sha256:sha(fs.readFileSync(path.join(root,oraclePath),'utf8')),cases:oracle.case_count,frozenBeforeIntegration19Read:true},sources:{before:{path:beforePath,sha256:sha(before)},after:{path:afterPath,sha256:sha(after)}},beforeRows,afterRows,findings:[],limits:['Executed actual undoSameLayers, layerSame, undoSigNow, undoSameZones, and redoLast bodies in an isolated VM. Zone restore, snapshot capture, stack, render, and document ownership services were instrumented adapters; no canvas/app mutation was performed.','The baseline source reproduces the defect: post-Undo layer visibility, opacity, blend, reorder, and removal changes still invoke undoApply and push. Integration19 refuses each, while preserving unchanged Redo and existing zone-conflict refusal.','Pixel-buffer and transform preservation are outside this contract: these fields are not in layerState/undoApply, and the probe covers presentation flags, layer membership/order, and zone signatures only.'],counts:{cases:oracle.case_count,beforeDefectCases:5,afterPassed:afterRows.length,providerCalls:0,nativeCalls:0,canvasApplyCalls:0}};
fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_REDO_LAYER_STATE_W115_REVIEW_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
