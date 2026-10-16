'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),core=require('./core.js');
function load(directory=path.join(__dirname,'build')){try{
  const manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'),'utf8'));
  const raw=fs.readFileSync(path.join(directory,'knowledge.json'));
  if(manifest.schema!=='spb-car-build/1'||crypto.createHash('sha256').update(raw).digest('hex')!==manifest.outputs['knowledge.json'])return null;
  return JSON.parse(raw);
}catch{return null;}}
module.exports={...core,load,lookup:(args,data)=>core.lookup(args,data||load()),fromContext:(query,status,state,data)=>core.fromContext(query,status,state,data||load())};
