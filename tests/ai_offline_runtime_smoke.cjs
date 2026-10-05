'use strict';
/* Installed-runtime smoke gate for the offline AI helper modules. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const args=process.argv.slice(2);let appRoot=path.resolve(__dirname,'..');
for(let i=0;i<args.length;i++){if(args[i]==='--root'){if(!args[i+1]){console.error('--root requires an app directory');process.exit(2);}appRoot=path.resolve(args[++i]);}else{console.error('Unknown argument: '+args[i]);process.exit(2);}}
const htmlPath=path.join(appRoot,'paint-booth-v2.html'), paths={
 intent:'js/spb-ai-instruction-intent-guard.js', materials:'js/spb-ai-material-controls.js', memory:'js/spb-ai-part-memory.js',
 projectBridge:'js/spb-ai-part-memory-project.js', receipt:'js/spb-ai-receipt-explainer.js', completeGuard:'js/spb-ai-complete-instruction-guard.js',
 operation:'js/spb-ai-operation.js', lease:'js/spb-ai-lease.js', controller:'js/spb-pro-ai.js'
};
const checks=[],failures=[],hashes={};
function check(id,ok,detail){const row={id,ok:!!ok,detail:detail||''};checks.push(row);if(!ok)failures.push(row);}
function hash(p){try{return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').toUpperCase();}catch(e){return null;}}
function read(p){try{return fs.readFileSync(p,'utf8');}catch(e){return null;}}
const html=read(htmlPath);check('runtime-html-present',!!html,htmlPath);
let scriptRefs=[];
if(html){const re=/<script\b[^>]*\bsrc\s*=\s*(["'])(.*?)\1[^>]*>/gi;let m;while((m=re.exec(html)))scriptRefs.push(String(m[2]).split('?')[0].replace(/\\/g,'/'));}
const scriptCount=rel=>scriptRefs.filter(x=>x===rel).length;
for(const [key,rel] of Object.entries(paths)){const full=path.join(appRoot,rel);hashes[key]=hash(full);check('file-'+key,!!hashes[key],hashes[key]?'sha256='+hashes[key]:rel+' missing');if(html&&key!=='controller')check('html-script-'+key,scriptCount(rel)===1,'count='+scriptCount(rel)+' path='+rel);}
if(html){check('html-script-controller',scriptCount(paths.controller)===1,'count='+scriptCount(paths.controller));const controllerIndex=scriptRefs.indexOf(paths.controller);for(const key of ['intent','materials','memory','projectBridge','receipt','completeGuard','operation','lease']){const i=scriptRefs.indexOf(paths[key]);check('dependency-before-controller-'+key,i>=0&&controllerIndex>=0&&i<controllerIndex,paths[key]+' index='+i+' controller='+controllerIndex);}const memoryIndex=scriptRefs.indexOf(paths.memory),bridgeIndex=scriptRefs.indexOf(paths.projectBridge);check('part-memory-before-project-bridge',memoryIndex>=0&&bridgeIndex>=0&&memoryIndex<bridgeIndex,paths.memory+' index='+memoryIndex+' projectBridge index='+bridgeIndex);}

const intentPath=path.join(appRoot,paths.intent),intentSource=read(intentPath);
if(intentSource){const w={};w.window=w;vm.createContext(w);vm.runInContext(intentSource,w,{filename:intentPath});const I=w.SpbAIInstructionIntentGuard;
 check('intent-api',!!I&&typeof I.inspect==='function'&&typeof I.normalize==='function','SpbAIInstructionIntentGuard inspect/normalize');
 if(I){const input='Do not apply this request: Make only the roof blue.';let result=null;try{result=I.inspect(input);}catch(e){}check('intent-read-only-kind',!!result&&result.kind==='read_only',JSON.stringify(result));check('intent-read-only-preserved',I.normalize(input)===input,'normalizer must preserve the no-execution utterance verbatim');const hypothetical='What would happen if I changed only the roof to blue? Do not apply it.';result=I.inspect(hypothetical);check('intent-hypothetical-read-only',!!result&&result.kind==='read_only',JSON.stringify(result));}
}

const materialPath=path.join(appRoot,paths.materials);if(hashes.materials){let M;try{M=require(materialPath);}catch(e){check('material-module-load',false,String(e));}
 if(M){check('material-api',typeof M.parse==='function'&&typeof M.buildEdit==='function',M.contract||'missing parser/buildEdit');
  const positive=M.parse('Increase clearcoat on the roof by 20 points');check('material-relative-part-channel',positive&&positive.kind==='edit'&&positive.channel==='clearcoat'&&positive.part==='roof'&&positive.delta===20&&positive.amountUnit==='points',JSON.stringify(positive));
  const zone={id:'roof-7',name:'Roof',specShiftR:12,specShiftG:-8,specShiftB:3},built=M.buildEdit(zone,positive);check('material-preserves-other-channels',built&&built.kind==='edit'&&built.zone_id==='roof-7'&&built.spec_shift.metal===12&&built.spec_shift.rough===-8&&built.spec_shift.clearcoat===23,JSON.stringify(built));
  const percent=M.parse('Increase clearcoat on the roof by 20%');check('material-percent-refused',!!percent&&percent.kind!=='edit',JSON.stringify(percent));
  const conflict=M.parse('Increase clearcoat and roughness on the roof by 20 points');check('material-mixed-channel-refused',!!conflict&&conflict.kind!=='edit',JSON.stringify(conflict));
  const nonChannel=M.parse('Make the roof metallic');check('material-finish-delegates',!!nonChannel&&nonChannel.kind!=='edit',JSON.stringify(nonChannel));
 }
}

const memoryPath=path.join(appRoot,paths.memory);if(hashes.memory){let P;try{P=require(memoryPath);}catch(e){check('memory-module-load',false,String(e));}
 if(P){check('memory-factory-api',P.schema==='spb-ai-part-memory/1'&&typeof P.saveRecord==='function'&&typeof P.sanitizeRecord==='function'&&typeof P.prepareRestore==='function','schema='+P.schema+' exports='+Object.keys(P).join(','));}
}

const optionalContracts={operation:'tests/ai_operation_contract.cjs',lease:'tests/ai_lease_generation_contract.cjs',source:'tests/ai_source_transaction_w53_completion_contract.cjs',partMemory:'tests/ai_part_memory_integrated_runtime_contract.cjs',material:'tests/ai_material_controls_contract.cjs'};
const contractMap={};for(const[k,rel]of Object.entries(optionalContracts))contractMap[k]={path:rel,present:fs.existsSync(path.join(__dirname,'..',rel))};
const report={work_item:'W115 installed offline AI runtime smoke',appRoot,html:htmlPath,htmlSha256:html?hash(htmlPath):null,sources:hashes,scriptRefs:scriptRefs.filter(x=>Object.values(paths).includes(x)),checks,failures,optionalContracts:contractMap,counts:{checks:checks.length,failures:failures.length}};
console.log(JSON.stringify(report,null,2));if(failures.length)process.exitCode=1;
