'use strict';
// Proposed scripts/offline-reference-payload-gate.cjs for the full Electron server tree.
// Static prerequisites only. Clean packaged-browser acceptance is still required.
const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto');
const assets=['mcp/chatgpt/car-knowledge/core.js','mcp/chatgpt/car-knowledge/live-identity.js','mcp/chatgpt/conversation-scope.js','mcp/chatgpt/car-knowledge/offline-answer.js','mcp/chatgpt/offline-ready.js','mcp/chatgpt/car-knowledge/layer-reading.js','mcp/chatgpt/colour-report-scope.js','mcp/chatgpt/design-brief.js','mcp/chatgpt/design-intent.js','mcp/chatgpt/editor-capabilities.js','mcp/chatgpt/element-resize-scope.js','mcp/chatgpt/layer-colour-followup.js','mcp/chatgpt/layer-targets.js','mcp/chatgpt/native-layer-colour.js','mcp/chatgpt/panel-location.js','mcp/chatgpt/preserved-colours.js'];
const hooks={'js/spb-pro-ai.js':['SpbCarReferenceAnswer','SpbOfflineReady'],'js/spb-offline-answer.js':['SpbCarReferenceAnswer','SpbCarReferenceAnswer.index'],
 'paint-booth-3-canvas.js':['SpbConversationScope.sourceCommitted'], 'js/features/spb-projects.js':['SpbTemplateIdentity.sourceVerified']};
function checkBase(root){
 root=fs.realpathSync(root);const errors=[],hashes={};
 function read(file){const p=path.join(root,file);if(!fs.existsSync(p)){errors.push('Missing '+file);return null;}
  const real=fs.realpathSync(p),rel=path.relative(root,real);if(rel.startsWith('..')||path.isAbsolute(rel)){errors.push('Outside prepared tree '+file);return null;}
  const raw=fs.readFileSync(real);hashes[file]=crypto.createHash('sha256').update(raw).digest('hex');return raw.toString('utf8');}
 for(const file of assets){const source=read(file);if(source!==null)try{new vm.Script(source,{filename:file});}catch{errors.push('Invalid script '+file);}}
 for(const [file,symbols] of Object.entries(hooks)){const source=read(file);if(source!==null)for(const symbol of symbols)if(!source.includes(symbol))errors.push('Missing caller prerequisite '+file+':'+symbol);}
 const manifest=read('mcp/chatgpt/car-knowledge/build/manifest.json'),articles=read('data/encyclopedia/cars.json');
 if(manifest!==null&&articles!==null){try{const m=JSON.parse(manifest),a=JSON.parse(articles);
  if(m.schema!=='spb-car-build/1'||m.outputs?.['cars.json']!==hashes['data/encyclopedia/cars.json'])errors.push('Compiled car article overlay does not match build manifest');
  if(!Array.isArray(a.articles)||!a.articles.some(x=>x&&x.car_reference))errors.push('Compiled car references are absent from browser articles');
 }catch{errors.push('Invalid compiled car article manifest or JSON');}}
 const html=read('paint-booth-v2.html'),scripts=[];
 if(html!==null){for(const match of html.matchAll(/<script\b[^>]*\bsrc\s*=\s*(['"])(.*?)\1[^>]*>/gi)){const src=match[2].split(/[?#]/)[0].replace(/^\.\//,'').replace(/^\//,'');scripts.push(src);}
  for(const asset of assets)if(!scripts.includes(asset))errors.push('Missing explicit browser load '+asset);
  const core=scripts.indexOf(assets[0]),answer=scripts.indexOf(assets[3]);if(core>=0&&answer>=0&&core>answer)errors.push('Car core must load before Offline car answer');
 }
 return{schema:'spb-offline-reference-payload-gate/1',pass:errors.length===0,errors,asset_sha256:hashes,
  scope:'Full prepared Electron tree: dependency presence, containment, syntax, explicit script loading and caller marker prerequisites. Marker presence is not execution proof; alternative bundled loaders need an equivalent reviewed contract. No MCPB-only gate or live-browser acceptance claim.'};
}

const rel='mcp/chatgpt/car-knowledge/identity-index.js';
function verify(raw,html,answer,cars){const errors=[];let index;
 try{const w={};vm.runInNewContext(raw,{window:w},{timeout:100});index=w.SpbCarReferenceNames;}catch{errors.push('Invalid identity bootstrap script');return errors;}
 const expected=JSON.parse(cars).articles.filter(a=>a.car_reference).map(a=>Object.fromEntries(['id','name','aliases','paint_folder'].map(k=>[k,a.car_reference[k]??null])));
 const digest=crypto.createHash('sha256').update(cars).digest('hex');
 if(index?.schema!=='spb-car-name-index/1'||index?.source_cars_sha256!==digest)errors.push('Identity bootstrap corpus version mismatch');
 if(JSON.stringify(index?.cars)!==JSON.stringify(expected))errors.push('Identity names differ from compiled corpus or contain extra fields');
 const scripts=Array.from(html.matchAll(/<script\b[^>]*src=["']([^"']+)/g),m=>m[1].split('?')[0].replace(/^\//,''));
 const before=scripts.indexOf(rel),core=scripts.indexOf('mcp/chatgpt/car-knowledge/core.js');
 if(before<0||core<0||before>=core)errors.push('Identity bootstrap must load before car core');
 if(!answer.includes("W.SpbCarReferenceNames.schema==='spb-car-name-index/1'"))errors.push('Reference caller lacks names-before-facts recognition');
 return errors;
}
function check(root){
 const result=checkBase(root);
 try{
  const resolved=fs.realpathSync(root);
  const read=n=>{const target=fs.realpathSync(path.join(resolved,n));const relative=path.relative(resolved,target);
   if(relative.startsWith('..')||path.isAbsolute(relative))throw Error('Outside prepared tree '+n);
   return fs.readFileSync(target,'utf8');};
  result.errors.push(...verify(read(rel),read('paint-booth-v2.html'),read('mcp/chatgpt/car-knowledge/offline-answer.js'),read('data/encyclopedia/cars.json')));
 }catch(e){result.errors.push('Missing/invalid identity bootstrap: '+e.message);}
 result.schema='spb-offline-reference-payload-gate/2';result.pass=result.errors.length===0;
 result.scope+=' Exact names-only bootstrap/corpus version and load-before-core required.';
 return result;
}

if(require.main===module){try{if(process.argv.length!==3)throw Error('Usage: offline-reference-payload-gate.cjs PREPARED_FULL_SERVER');const result=check(process.argv[2]);console.log(JSON.stringify(result));if(!result.pass)process.exitCode=1;}catch(e){console.error(e.message);process.exitCode=1;}}
module.exports={check,assets,hooks,verify};
