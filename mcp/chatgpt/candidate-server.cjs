'use strict';
// Development launcher only: retain the production module's relative resources.
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const port=Number(process.env.SPB_PORT);
if(!Number.isInteger(port)||port<59910||port>59999)throw new Error('Candidate MCP requires a private port in 59910..59999');
// A reviewed one-car corpus successor preserves frozen predecessor receipts.
function reviewedCorpusDigest(expected){
 if(process.env.SPB_DIRTSTREETSTOCK_REVIEW!=='1')return expected;
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/dirtstreetstock-evidence-review');
 const stage=JSON.parse(fs.readFileSync(path.join(dir,'proof.json'))),installed=JSON.parse(fs.readFileSync(path.join(dir,'private-install-proof.json'))),checked=JSON.parse(fs.readFileSync(path.join(dir,'installed-component-proof.json')));
 const actual=crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json'))).digest('hex');
 let finalKnowledgeDigest=installed.knowledge_sha256;
 if(process.env.SPB_DIRTUMP_REVIEW==='1'){const updir=path.join(__dirname,'car-knowledge/dirtump-evidence-review'),up=JSON.parse(fs.readFileSync(path.join(updir,'private-install-proof.json'))),base=JSON.parse(fs.readFileSync(path.join(updir,'proof.json'))),checkedUp=JSON.parse(fs.readFileSync(path.join(updir,'installed-component-proof.json')));if(!up.pass||up.new_facts!==1||up.neighbor_records_unchanged!==191||base.status!=='PASS'||base.baseline_sha256!==installed.knowledge_sha256||!checkedUp.pass||!checkedUp.installed_corpus||checkedUp.export_packets_unchanged!==374||checkedUp.unrelated_history_packets_unchanged!==191)throw Error('UMP successor evidence missing');finalKnowledgeDigest=up.knowledge_sha256;}
 if(port!==59910||stage.status!=='PASS'||!installed.pass||!checked.pass||!checked.installed_corpus||installed.new_facts!==1||installed.neighbor_records_unchanged!==191||checked.unrelated_history_packets_unchanged!==191||checked.export_packets_unchanged!==374||expected!==stage.baseline_sha256||actual!==finalKnowledgeDigest)throw Error('Dirt Street Stock reviewed corpus successor mismatch');
 return actual;
}
if(process.env.SPB_CONTROL_LABEL_REVIEW==='1'){
 if(port!==59910)throw Error('Control-label review is restricted to private59910');
 const crypto=require('node:crypto'),directory=path.join(__dirname,'car-knowledge/control-label-review');
 const proof=JSON.parse(fs.readFileSync(path.join(directory,'stage-proof.json')));
 const checks=JSON.parse(fs.readFileSync(path.join(directory,'component-proof.json')));
 if(!checks.pass||checks.template_control_cases!==328||checks.negative_controls!==9)throw Error('Control-label component evidence missing');
 let exportOverride=null;
 if(process.env.SPB_EXPORT_REFERENCE_REVIEW==='1'){
  const exportDirectory=path.join(__dirname,'car-knowledge/export-reference-review');
  const exportProof=JSON.parse(fs.readFileSync(path.join(exportDirectory,'stage-proof.json')));
  const exportChecks=JSON.parse(fs.readFileSync(path.join(exportDirectory,'component-proof.json')));
  if(!exportProof.pass||!exportProof.apply_pass||!exportProof.syntax_pass||!exportChecks.pass||exportChecks.export_questions!==374||exportChecks.exact_car_records!==187||exportChecks.negative_controls!==7)throw Error('Export-reference review evidence missing');
  if(crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json'))).digest('hex')!==reviewedCorpusDigest(exportChecks.knowledge_sha256))throw Error('Export-reference corpus drift');
  exportOverride={source:path.join(exportDirectory,'layer-reading.js'),expected:exportProof.files.find(f=>f.file==='mcp/chatgpt/car-knowledge/layer-reading.js')};
  if(!exportOverride.expected||exportOverride.expected.candidate_sha256!==exportChecks.helper_sha256)throw Error('Export-reference candidate/proof disagreement');
 }
 // Compile only the two reviewed owned helpers at their canonical module paths;
 // lookup.cjs keeps the real corpus loader. Shared files are never overwritten.
 for(const name of ['layer-reading.js','core.js']){
  const target=path.join(__dirname,'car-knowledge',name),override=name==='layer-reading.js'&&exportOverride;
  const source=override?override.source:path.join(directory,name),raw=fs.readFileSync(source);
  const expected=override?override.expected:proof.files.find(f=>f.file==='mcp/chatgpt/car-knowledge/'+name);
  if(!expected||crypto.createHash('sha256').update(raw).digest('hex')!==expected.candidate_sha256)throw Error('Control-label source drift: '+name);
  const replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));
  replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
 }
}
if(process.env.SPB_FOCUSED_HISTORY_REVIEW==='1'||process.env.SPB_SHARED_HISTORY_REVIEW==='1'){
 if(port!==59910)throw Error('Focused-history review requires private59910');
 const shared=process.env.SPB_SHARED_HISTORY_REVIEW==='1',crypto=require('node:crypto'),dir=path.join(__dirname,shared?'car-knowledge/shared-history-evidence-review':'car-knowledge/focused-history-review');
 const stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),source=path.join(dir,'core.js'),raw=fs.readFileSync(source),row=stage.files.find(x=>x.name==='core.js');
 if(!stage.pass||!stage.apply||!stage.syntax||!proof.pass||proof.focused_cases!==9||proof.export_cases!==374||shared&&proof.exact_car_scope_cases!==192||crypto.createHash('sha256').update(raw).digest('hex')!==row.candidate_sha256)throw Error('Focused/shared-history evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_HISTORY_LANGUAGE_REVIEW==='1'){
 if(port!==59910)throw Error('History-language review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/history-language-review');
 const stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),row=stage.files.find(x=>x.name==='core.js');
 const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.files.every(r=>r.apply&&r.syntax)||!proof.pass||proof.history_cases.length!==8||proof.edit_guards!==8||proof.export_cases!==374||proof.exact_car_scope_checks!==192||digest(raw)!==row.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('History-language evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_CONTINGENCY_HISTORY_REVIEW==='1'){
 if(port!==59910)throw Error('Contingency-history review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/contingency-history-review');
 const stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),row=stage.files.find(r=>r.name==='core.js'),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.files.every(r=>r.apply&&r.syntax)||!proof.pass||proof.positive_queries.length!==4||proof.edit_guards!==6||proof.export_packets_unchanged!==374||proof.exact_car_scope_checks!==192||digest(raw)!==row.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('Contingency-history evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_TEMPLATE_UNAVAILABLE_REVIEW==='1'){
 if(port!==59910)throw Error('Template-unavailable review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/template-unavailable-review'),stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.apply||!stage.syntax||!proof.pass||proof.non_target_car_packets_unchanged!==191||!proof.offline_shared_guidance_parity||digest(raw)!==stage.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('Unavailable-template evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_VARIANT_LAYER_REVIEW==='1'){
 if(port!==59910)throw Error('Variant-layer review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/variant-layer-review'),stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),row=stage.files.find(r=>r.name==='core.js'),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.files.every(r=>r.apply&&r.syntax)||!proof.pass||proof.positive_queries.length!==4||proof.edit_guards!==4||proof.export_packets_unchanged!==374||proof.overview_packets_unchanged!==192||digest(raw)!==row.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('Variant-layer evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_VARIANT_COVERAGE_REVIEW==='1'){
 if(port!==59910)throw Error('Variant-coverage review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/variant-coverage-review'),stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),row=stage.files.find(r=>r.name==='core.js'),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.files.every(r=>r.apply&&r.syntax)||!proof.pass||proof.positive_queries.length!==22||proof.exact_models!==11||proof.existing_answers_unchanged!==4||proof.missing_fact_guards!==11||proof.missing_label_guards!==19||proof.edit_guards!==4||proof.export_packets_unchanged!==374||proof.overview_packets_unchanged!==192||digest(raw)!==row.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('Variant-coverage evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_FIRST_PAINT_WORKFLOW_REVIEW==='1'){
 if(port!==59910)throw Error('First-paint-workflow review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/first-paint-workflow-review'),stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),row=stage.files.find(r=>r.name==='core.js'),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.files.every(r=>r.apply&&r.syntax)||!proof.pass||proof.positive_queries.length!==9||proof.restricted_car_guards!==4||proof.mixed_edit_guards!==3||!proof.ambiguous_car_guard||proof.export_packets_unchanged!==374||proof.overview_packets_unchanged!==192||digest(raw)!==row.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('First-paint-workflow evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_FIRST_PAINT_HISTORY_REVIEW==='1'){
 if(port!==59910)throw Error('First-paint history scope requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/first-paint-workflow-review/history-restriction-fix'),stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.apply||!stage.syntax||!proof.pass||proof.fixed_arca_workflows!==3||proof.neighbor_workflow_packets_unchanged!==189||proof.restricted_packets!==4||proof.exact_car_workflow_packets!==192||digest(raw)!==stage.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('First-paint history evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_CURRENT_CAR_START_REVIEW==='1'){
 if(port!==59910)throw Error('Current car starting review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/current-car-start-review'),stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json'))),raw=fs.readFileSync(path.join(dir,'core.js')),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.syntax_pass||!proof.pass||proof.shared_exact_id_workflows!==192||proof.restricted_workflows!==4||proof.neighbor_shared_packets_unchanged!==384||proof.offline_export_packets_unchanged!==374||digest(raw)!==stage.candidate_sha256||digest(fs.readFileSync(path.join(__dirname,'car-knowledge/build/knowledge.json')))!==reviewedCorpusDigest(proof.knowledge_sha256))throw Error('Current car starting evidence drift');
 const target=path.join(__dirname,'car-knowledge/core.js'),replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
if(process.env.SPB_REFERENCE_VERSION_REVIEW==='1'){
 if(port!==59910)throw Error('Reference-version review requires private59910');
 const crypto=require('node:crypto'),dir=path.join(__dirname,'car-knowledge/reference-version-review');
 const stage=JSON.parse(fs.readFileSync(path.join(dir,'stage-proof.json'))),proof=JSON.parse(fs.readFileSync(path.join(dir,'component-proof.json')));
 const target=path.join(__dirname,'car-knowledge/lookup.cjs'),source=path.join(dir,'lookup.cjs'),raw=fs.readFileSync(source),digest=b=>crypto.createHash('sha256').update(b).digest('hex');
 if(!stage.pass||!stage.apply||!stage.syntax||!proof.pass||proof.cases!==8||digest(raw)!==stage.candidate_sha256||digest(fs.readFileSync(target))!==stage.parent_sha256)throw Error('Reference-version proposal evidence or parent drift');
 const replacement=new Module(target,module);replacement.filename=target;replacement.paths=Module._nodeModulePaths(path.dirname(target));replacement._compile(raw.toString('utf8'),target);replacement.loaded=true;require.cache[target]=replacement;
}
const filename=path.resolve(__dirname,'../server/index.js');
const mod=new Module(filename,module);mod.filename=filename;mod.paths=Module._nodeModulePaths(path.dirname(filename));
mod._compile(fs.readFileSync(path.join(__dirname,'candidates/index.js'),'utf8'),filename);
