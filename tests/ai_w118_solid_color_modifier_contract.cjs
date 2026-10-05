'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),srcPath='_easy_claude_work/ai14h_w118_solid_color_modifier/candidate/spb-pro-design.js',oraclePath='_easy_claude_work/ai14h_w118_solid_color_modifier/fresh-oracle.json';
const src=fs.readFileSync(path.join(root,srcPath),'utf8'),oracleText=fs.readFileSync(path.join(root,oraclePath),'utf8'),oracle=JSON.parse(oracleText),sha=s=>crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
assert.equal(sha(oracleText),'E8D00ACDA0FDCC114B028FF25586EFCBE2D6859F9893E552315DF60C09FB2E8D','frozen five-case W118 oracle');
assert.equal(sha(src),'13E8C48134B4E3649D914EA1D1C1AAECC92D1728DA2A8C80C5826386DC14357C','private W118 candidate source pin');
const w={};vm.runInNewContext(src,{window:w,console});const D=w.SpbProDesign;assert(D,'actual public SpbProDesign API loaded');
const rows=[];
for(const c of oracle.cases){const row={id:c.id};
 if(c.id==='solid-red-direct'){
  row.look=D.lookRequest(c.utterance);row.coverage=D.offlinePartCoverage(c.utterance);row.part=D.offlinePart(c.utterance);
  assert.equal(row.look,null,'solid color modifier must not become a catalogue look');assert(row.coverage&&row.coverage.zones.length===1,'complete part-color coverage must authorize downstream consideration');assert.deepEqual(Array.from(row.coverage.zones[0].region.part? [row.coverage.zones[0].region.part]:[]),['roof']);assert.equal(row.coverage.zones[0].color,'#c8102e');
 } else if(c.id==='matte-red-finish-and-color'||c.id==='flat-red-finish-and-color'){
  row.look=D.lookRequest(c.utterance);row.plan=D.compoundPlan(c.utterance);row.element=D.offlineElement(c.utterance);assert.equal(row.look,null);assert(row.element&&row.element.kind==='compound');assert.equal(row.element.zones.length,1);assert.equal(row.element.zones[0].region.part,'roof');assert.equal(row.element.zones[0].color,'#c8102e');assert.equal(row.element.zones[0].finish,'base::matte');
 } else if(c.id==='quoted-solid-red-explanation'){
  row.look=D.lookRequest(c.utterance);row.coverage=D.offlinePartCoverage(c.utterance);row.element=D.offlineElement(c.utterance);assert.equal(row.look,null);assert.equal(row.coverage,null);assert.equal(row.element,null);
 } else if(c.id==='matte-source-paint-preservation'){
  row.look=D.lookRequest(c.utterance);row.spec=D.offlineSpec(c.utterance);row.coverage=D.offlinePartCoverage(c.utterance);assert(row.spec&&row.spec.zones.length===1);assert.equal(row.spec.zones[0].region.part,'roof');assert.equal(row.spec.zones[0].color,'source');assert.equal(row.spec.zones[0].finish,'base::f_soft_matte');assert.equal(row.coverage,null);
 }
 rows.push(row);
}
console.log(JSON.stringify({status:'PASS_PRIVATE_E_CLASSIFIER',cases:rows.length,sourceSha256:sha(src),oracleSha256:sha(oracleText),rows},null,2));
