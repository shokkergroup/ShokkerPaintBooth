'use strict';
// Exercise the real report formatter and MCP adapter against the native failure.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
function load(report){
 const w={console,Date,Promise,Uint8Array,Uint8ClampedArray,document:{addEventListener(){}},SPB_REP_NOR12:true};w.window=w;vm.createContext(w);
 let src=fs.readFileSync(path.join(root,report),'utf8');
 src=src.replace('W.SpbIntentReport = {','W.testClaimLine = claimLine; W.SpbIntentReport = {');
 vm.runInContext(src,w);vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates/spb-mcp-frames.js'),'utf8'),w);
 return w;
}
const original=load('js/spb-intent-report.js'),candidate=load('mcp/chatgpt/candidates/spb-intent-report.js');
const sc={parts:[],layers:[],protectKinds:['logos'],whole:false},M={partCells:{},paintable:50000,protect:['Car_Decal'],decalMin:150,coverageUnit:'preview'};
function line(w,decal,undid=false){return w.testClaimLine({changed:20000,paint:20000,surfacePaint:20000,surfaceChanged:20000,spec:0,decal,parts:{},layers:{},sum:[0,0,0],sn:0},undid?{...sc,parts:['hood']}:sc,M,'Change red to gold',{undid});}
assert.match(line(original,18),/logos are untouched/,'Preserve the source negative control below the tolerance');
for(const undid of [false,true]){
 for(const cells of [1,18,149]){
  const native=line(candidate,cells,undid);assert.doesNotMatch(native,/untouched/);assert.match(native,/preservation is unverified/);
  const m=candidate.SpbMcpFrames.measuredOf({verdict:'ok',changed:20000,paint:20000,decal:cells,findings:[],protect:['Car_Decal'],line:native},{dims:()=>[2048,2048]});
  assert.doesNotMatch(m.line,/untouched|Only \d+ px at the edges/);assert.equal((m.line.match(/preservation is unverified/g)||[]).length,cells<20?1:0);
 }
 assert.match(line(candidate,0,undid),/found no change.*does not verify every pixel/);
}
const missing=candidate.SpbMcpFrames.measuredOf(null,{});assert.equal(missing.verdict,'not_measured');
console.log(JSON.stringify({pass:true,source_false_preservation_reproduced:true,native_and_MCP_honest:true,zero_not_exact_proof:true,missing_measurement_not_pass:true,native:false}));
