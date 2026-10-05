'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const candidateDir = path.join(root, '_easy_claude_work/ai14h_w52_candidate');
const source = path.join(candidateDir, 'spb-pro-edit.js');
const design = path.join(candidateDir, 'spb-pro-design.js');
const oraclePath = path.join(candidateDir, 'oracle.json');
const fresh = JSON.parse(fs.readFileSync(oraclePath, 'utf8')).fresh_cases;
const candidateExpectedHash = '0dcf869f92ca3d33f194113f8bb7115d8461fd6f09aac6b6031d68a5766eac48';
assert.equal(sha(source), candidateExpectedHash, 'isolated candidate changed after review');
const w52Hash = crypto.createHash('sha256').update(fs.readFileSync(oraclePath)).digest('hex').toLowerCase();
assert.equal(w52Hash, '916b77ee479a4cc9465b0104a9194efdf84b372aa0f500e1b520b87278e3372a', 'frozen W52 oracle changed');
const runtime = require('../_easy_claude_work/ai14h_generation3_runtime1/source-freeze.json');
function sha(f){return crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').toLowerCase();}
assert.equal(sha(path.join(root, '_easy_claude_work/ai14h_generation3_runtime1/js/spb-pro-edit.js')), runtime.hashes['js/spb-pro-edit.js']);
assert.equal(sha(path.join(root, '_easy_claude_work/ai14h_generation3_runtime1/js/spb-pro-design.js')), runtime.hashes['js/spb-pro-design.js']);
const runtimeManifest = path.join(root, '_easy_claude_work/ai14h_generation3_runtime1/source-freeze.json');
assert.equal(sha(runtimeManifest), '165eafc20f1c6d0dbee4d145ee130cc62c1468c659f4193788f750ece060de4b', 'Runtime 1 manifest/source-freeze changed');
const w21Report = JSON.parse(fs.readFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_FINISH_PRESERVE_TAIL_REPAIR_2026-10-03.json'),'utf8'));
const remap = a => a.map(x=>({id:x.id,text:x.text,mode:x.mode,part:x.part,finish:x.finish}));
const w21 = {fresh:remap(w21Report.frozen_oracle.fresh),priorW17:remap(w21Report.frozen_oracle.priorW17)};
assert.equal(crypto.createHash('sha256').update(JSON.stringify(w21)).digest('hex').toUpperCase(), w21Report.frozen_oracle.sha256, 'W21 source oracle/report drifted');
const H = require('../_easy_claude_work/stack_h.js');
const w = H.load();
vm.runInContext(fs.readFileSync(design,'utf8'),w,{filename:'W52 spb-pro-design snapshot'});
vm.runInContext(fs.readFileSync(source,'utf8'),w,{filename:'W52 isolated spb-pro-edit candidate'});
const E=w.SpbProEdit, env={palette:[{hex:'#c8102e',share_pct:60},{hex:'#141416',share_pct:20},{hex:'#1347a8',share_pct:10},{hex:'#f2c500',share_pct:5}],layers:[]};
function evaluate(c){const plan=E.plan(c.text,env),compiled=plan&&plan.kind==='ops'?E.compile(plan,env):null;return {plan,compiled};}
const results=[],failures=[];
for(const c of fresh){const {plan,compiled}=evaluate(c); const positive=c.id.endsWith('P01')||c.id.endsWith('P02')||c.id.endsWith('P03')||c.id.endsWith('P04');
  if(positive){
    const op=plan&&plan.ops&&plan.ops[0], zone=compiled&&compiled.zones&&compiled.zones[0];
    if(!plan||plan.kind!=='ops'||plan.exactPart!==true||plan.ops.length!==1||!op||op.target.kind!=='part'||op.target.part!==c.expectedPart||!op.look||op.colour||plan.unknown.length)failures.push({id:c.id,reason:'not one exact named-part finish-only operation',plan});
    if(!compiled||compiled.ask||compiled.zones.length!==1||!zone||!zone.region||zone.region.part!==c.expectedPart||!zone.finish||zone.color!=='source'||zone.pattern||zone.spec_patterns)failures.push({id:c.id,reason:'compile lost the part scope or preservation-safe finish-only state',compiled});
  }else{
    if(plan&&plan.exactPart===true)failures.push({id:c.id,reason:'unsafe exactPart claim',plan});
    if(compiled&&!compiled.ask&&compiled.zones&&compiled.zones.length)failures.push({id:c.id,reason:'negative/help/conflict/extra request compiled executable zones instead of clarification',plan,compiled});
  }
  results.push({id:c.id,kind:plan&&plan.kind,exactPart:plan&&plan.exactPart,ask:!!(compiled&&compiled.ask),zones:compiled&&compiled.zones&&compiled.zones.length});
}
for(const c of w21.fresh.concat(w21.priorW17)){const {plan,compiled}=evaluate(c); if(c.mode==='one_finish'){
    const op=plan&&plan.ops&&plan.ops[0], z=compiled&&compiled.zones&&compiled.zones[0];
    if(!plan||plan.kind!=='ops'||plan.exactPart!==true||plan.ops.length!==1||!op||op.target.kind!=='part'||op.target.part!==c.part||!op.look||op.colour||op.rel||op.shade||op.pop||op.keep||op.recipe||op.sub||plan.unknown.length)failures.push({id:c.id,reason:'frozen W21/W17 expected exact finish-only scope',plan});
    if(!compiled||compiled.ask||compiled.zones.length!==1||!z||!z.region||z.region.part!==c.part||!z.finish||z.color!=='source'||z.pattern||z.spec_patterns)failures.push({id:c.id,reason:'frozen W21/W17 compile changed',compiled});
  }else{
    if(plan&&plan.exactPart===true)failures.push({id:c.id,reason:'unsafe exactPart on frozen negative',plan});
    if(compiled&&!compiled.ask&&compiled.zones&&compiled.zones.length)failures.push({id:c.id,reason:'frozen conflicting/extra/negative request compiled zones',plan,compiled});
    if(c.mode==='no_mutation'&&!(plan&&plan.kind==='ask'&&plan.prohibited_edit))failures.push({id:c.id,reason:'frozen prohibition no longer no-mutation',plan});
  }
  results.push({id:c.id,kind:plan&&plan.kind,exactPart:plan&&plan.exactPart,ask:!!(compiled&&compiled.ask),zones:compiled&&compiled.zones&&compiled.zones.length});
}
const report={review:'W52 declarative named-part finish preservation candidate',date:'2026-10-04',status:failures.length?'BLOCKED':'PASS_WITH_LIMITS',source:{path:'_easy_claude_work/ai14h_w52_candidate/spb-pro-edit.js',sha256:sha(source)},runtime_inputs:{edit_sha256:runtime.hashes['js/spb-pro-edit.js'],design_sha256:runtime.hashes['js/spb-pro-design.js'],source_freeze_sha256:sha(runtimeManifest),runtime1_unchanged:true},oracles:{w52_sha256:w52Hash,w52_fresh: fresh.length,w21_sha256:w21Report.frozen_oracle.sha256,w21_fresh:w21.fresh.length,w17_prior:w21.priorW17.length,w21_source_files_modified:false},counts:{fresh_positive:4,fresh_negative:7,w21_w17_positive:w21.fresh.filter(x=>x.mode==='one_finish').length+w21.priorW17.length,w21_negative:w21.fresh.filter(x=>x.mode!=='one_finish').length,failures:failures.length},results,failures,limits:['Actual SpbProEdit.plan/compile and frozen SpbProDesign were evaluated; this proves the isolated E parser/compiler only, not proAI routing, UI/MCP/native acceptance, actual paint application, or catalog resolution.','The positive normalizer accepts only a declarative named-part finish clause followed by a preservation tail already accepted by the existing strict same-part validator. Unknown actions, cross-part preservation, questions and prohibitions are not normalized.']};
fs.writeFileSync(path.join(root,'_easy_claude_work/ai14h_w52_candidate/review-results.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,hash:report.source.sha256,counts:report.counts,failures,results},null,2));
if(failures.length)process.exitCode=2;


