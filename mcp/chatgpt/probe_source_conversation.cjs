'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
let source={path:'C:/isolated/car-a.psd',fingerprint:'hash-a',generation:1};
const w={console,Date,Set,Map,localStorage:{getItem:()=>null},spbProAI:{log:()=>[]},
 SPBSourceLoadTransaction:{getCommittedPath:()=>source.path,getCommittedFingerprint:()=>source.fingerprint,getGeneration:()=>source.generation}};
w.window=w;vm.createContext(w);
vm.runInContext(fs.readFileSync(path.join(root,'js/spb-convo-state.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'conversation-scope.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'design-brief.js'),'utf8'),w);
const C=w.SpbConvo;
C.turn('Make the hood blue');
C.commit({said:'Make the hood blue',targets:[{kind:'part',part:'hood'}],zone_ids:['car-a-zone'],undo_id:'car-a-undo',editCtx:{target:{part:'hood'}}});
C.offer({kind:'options',items:['Pearl blue','Satin gold'],for:[{kind:'part',part:'hood'}]});
const before=C.view('the second option');
const canvas=fs.readFileSync(path.join(__dirname,'candidates/paint-booth-3-canvas.js'),'utf8');
const start=canvas.indexOf('        function _spbSourceLoadResult('),end=canvas.indexOf('        async function _spbFingerprintBytes(',start);
assert.ok(start>=0&&end>start);
source={path:'C:/isolated/car-b.psd',fingerprint:'hash-b',generation:2};
w._spbSourceLoadGeneration=2;w._spbCommittedSourcePath=source.path;w._spbCommittedSourceFingerprint=source.fingerprint;w._psdPath='';
vm.runInContext(canvas.slice(start,end),w);w._spbSourceLoadResult(null,true,{});
const after=C.view('the second option');
const result={schema:'spb-source-conversation-probe/1',tested_at:new Date().toISOString(),scope:'Actual conversation store and private source-result hook; no browser or paint actions',
 before,after,stale_offer:!!after.last_offer,stale_undo:after.last_change&&after.last_change.undo_id==='car-a-undo'};
const file=path.join(root,'_codex_mcp_work/chatgpt-dev/59910','source-conversation-probe-'+Date.now()+'.json');
fs.writeFileSync(file,JSON.stringify(result,null,2),{flag:'wx'});
console.log(JSON.stringify({receipt:file,stale_offer:result.stale_offer,stale_undo:result.stale_undo}));
