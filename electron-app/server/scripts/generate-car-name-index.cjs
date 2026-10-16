'use strict';
// Proposed scripts/generate-car-name-index.cjs. Names only, never facts/geometry.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
function generate(raw){
  const articles=JSON.parse(raw).articles;
  if(!Array.isArray(articles))throw Error('Missing compiled car articles');
  const cars=articles.filter(a=>a.car_reference).map(a=>Object.fromEntries(
    ['id','name','aliases','paint_folder'].map(k=>[k,a.car_reference[k]??null])));
  if(!cars.length||new Set(cars.map(c=>c.id)).size!==cars.length||cars.some(c=>!c.id||!c.name))
    throw Error('Empty, duplicate or invalid compiled identities');
  const catalog={schema:'spb-car-name-index/1',source_cars_sha256:crypto.createHash('sha256').update(raw).digest('hex'),cars};
  return '// Generated exact identity hints only. No facts, template verification or geometry.\n(function(W){W.SpbCarReferenceNames='+
    JSON.stringify(catalog).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029')+';})(window);\n';
}
module.exports={generate};
if(require.main===module){
  try{
    if(process.argv.length!==4)throw Error('Usage: generate-car-name-index.cjs COMPILED_CARS_JSON OUTPUT_JS');
    const source=path.resolve(process.argv[2]),target=path.resolve(process.argv[3]);
    if(source===target)throw Error('Index output cannot overwrite compiled corpus');
    const script=generate(fs.readFileSync(source));
    fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,script);
  }catch(e){console.error(e.message);process.exitCode=1;}
}
