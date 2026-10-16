'use strict';
// Local install integrity/readability check. This is not authentication,
// listening, model entitlement, geometry calibration or an action receipt.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function failure(status,code,message,details=[]){return{schema:'spb-knowledge-readiness/1',ready:false,status,code,message,details:details.slice(0,8),read_only:true};}
function within(root,relative){
 if(typeof relative!=='string'||!relative||relative.includes('\\')||path.isAbsolute(relative)||relative.split('/').some(x=>x==='..'||x==='.'||!x))throw Error('Invalid install-relative path');
 const file=path.resolve(root,relative),r=path.relative(root,file);
 if(r.startsWith('..'+path.sep)||r==='..'||path.isAbsolute(r))throw Error('Outside install path');
 if(fs.existsSync(file)){const real=fs.realpathSync(file),rr=path.relative(root,real);if(rr.startsWith('..'+path.sep)||rr==='..'||path.isAbsolute(rr))throw Error('Outside install link');}
 return file;
}
async function inspect(mcpDirectory){
 if(process.env.SPB_MCPKNOW_OFF||process.env.SPB_FRESH_KNOWLEDGE_OFF)return failure('disabled','knowledge_delivery_disabled','SPB’s bundled AI knowledge is disabled in this installation. Restore normal SPB settings before reconnecting.');
 const started=Date.now(),root=fs.realpathSync(path.resolve(mcpDirectory,'..'));
 const manifestFile=path.join(root,'mcp/runtime-knowledge-manifest.json');
 if(!fs.existsSync(manifestFile))return failure('missing','knowledge_manifest_missing','SPB’s AI knowledge files need an update. Update or repair SPB, then reconnect.');
 let manifest;
 try{if(fs.statSync(manifestFile).size>262144)throw Error('Manifest too large');manifest=JSON.parse(fs.readFileSync(manifestFile,'utf8'));}
 catch{return failure('invalid','knowledge_manifest_invalid','SPB could not read its AI knowledge package. Repair or update SPB.');}
 try{
  if(manifest.schema!=='spb-runtime-knowledge-manifest/1'||!Array.isArray(manifest.files)||!manifest.files.length||manifest.files.length>2000)throw Error('Invalid manifest schema');
  if(!/^sha256:[a-f0-9]{64}$/.test(manifest.expected?.knowledge_version||''))throw Error('Missing knowledge version');
  const files=new Map(),problems=[];
  for(const item of manifest.files){
   if(!item||files.has(item.path)||!/^[a-f0-9]{64}$/.test(item.sha256)||!Number.isSafeInteger(item.bytes)||item.bytes<0||item.bytes>32*1024*1024)throw Error('Invalid manifest file');
   const file=within(root,item.path);files.set(item.path,file);
   if(!fs.existsSync(file))problems.push({file:item.path,reason:'missing'});
   else if(fs.statSync(file).size!==item.bytes||hash(fs.readFileSync(file))!==item.sha256)problems.push({file:item.path,reason:'changed'});
  }
  if(problems.length)return failure(problems.every(x=>x.reason==='missing')?'missing':'outdated','knowledge_files_mismatch','SPB’s AI knowledge package is incomplete or from a different update. Repair or update SPB.',problems);
  for(const key of ['entry','app_knowledge','delivery','context','car_lookup','car_bundle','encyclopedia'])if(!files.has(manifest.roles?.[key]))throw Error('Required knowledge role missing: '+key);
  // Disable networking before loading hash-checked runtime modules.
  const deny=()=>{throw Error('Knowledge readiness is offline');};
  for(const name of ['http','https']){const mod=require(name);mod.get=deny;mod.request=deny;}
  require('node:net').Socket.prototype.connect=deny;global.fetch=deny;
  const knowledge=require(files.get(manifest.roles.app_knowledge)),delivery=require(files.get(manifest.roles.delivery));
  const packet=delivery.packet(knowledge,'Help me understand SPB',manifest.server_version);
  if(!packet.available||packet.knowledge_version!==manifest.expected.knowledge_version||packet.delivery_version!==manifest.expected.delivery_version)throw Error('Knowledge version or delivery policy mismatch');
  const lookup=require(files.get(manifest.roles.car_lookup)),cars=lookup.load();
  if(!cars||!Array.isArray(cars.cars))throw Error('Car reference bundle unavailable');
  const facts=cars.cars.reduce((n,c)=>n+(c.facts||[]).length,0);
  if(cars.cars.length!==manifest.expected.cars||facts!==manifest.expected.facts)throw Error('Car reference counts mismatch');
  const context=require(files.get(manifest.roles.context));
  const result=await context.build({query:'What can SPB help me do?',include_paint:false},{history:async()=>({ok:true,messages:[]}),tools:()=>[],call:async()=>({isError:true,content:[{type:'text',text:'No live app reads during local readiness.'}]}),appKnowledge:query=>delivery.packet(knowledge,query,manifest.server_version)});
  if(result.app_knowledge?.knowledge_version!==packet.knowledge_version||!result.app_knowledge?.available)throw Error('Context cannot deliver bundled knowledge');
  let documents=0;
  for(const [name,file] of files)if(name.startsWith('data/encyclopedia/')&&name.endsWith('.json')){JSON.parse(fs.readFileSync(file,'utf8'));documents++;}
  if(documents!==manifest.expected.encyclopedia_json_files)throw Error('Encyclopedia file count mismatch');
  return{schema:'spb-knowledge-readiness/1',ready:true,status:'ready',code:'knowledge_ready',message:'SPB’s bundled AI knowledge is ready.',knowledge_version:packet.knowledge_version,delivery_version:packet.delivery_version,server_version:manifest.server_version,checked_files:files.size,cars:cars.cars.length,facts,encyclopedia_json_files:documents,elapsed_ms:Date.now()-started,read_only:true,scope:'Local knowledge integrity and context delivery only; sign-in, plan availability and listening are separate checks.'};
 }catch(e){return failure('invalid','knowledge_validation_failed','SPB’s AI knowledge could not be validated. Repair or update SPB.',[{reason:String(e.message).slice(0,180)}]);}
}
if(require.main===module){
 const directory=process.argv[2];
 if(!directory){console.log(JSON.stringify(failure('invalid','missing_install_path','SPB install path is missing.')));process.exitCode=1;}
 else inspect(directory).then(r=>{console.log(JSON.stringify(r));process.exitCode=r.ready?0:1;}).catch(()=>{console.log(JSON.stringify(failure('unavailable','knowledge_check_failed','SPB’s knowledge check could not run.')));process.exitCode=1;});
}
module.exports={inspect,within};
