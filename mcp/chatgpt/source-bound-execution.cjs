'use strict';
const parts=require('./named-part-guard.cjs');
const valid=s=>!!s&&!s.sourceIdentityUnavailable&&Number.isFinite(s.sourceGeneration)&&
  typeof s.committedPath==='string'&&!!s.committedPath&&typeof s.committedFingerprint==='string'&&
  typeof s.documentScope==='string'&&!!s.documentScope;
const same=(a,b)=>valid(a)&&valid(b)&&['sourceGeneration','committedPath','committedFingerprint','documentScope'].every(k=>a[k]===b[k]);
const refused=()=>({changed:false,refused:true,reason:'source_identity_unavailable_or_changed',
  rule:'Nothing was changed. The paint is loading, unavailable or changed since this request was prepared. Wait for the current file to finish loading, read its state again, and ask the painter before retrying an edit.'});
async function prepare(app,args,readState){
  let state=null;
  try{const r=await readState();if(r&&r.status<400&&r.json&&r.json.ok!==false)state=r.json.result;}catch(_){}
  const blocked=parts.check(app,args,state);if(blocked)return {blocked};
  const proof=state&&state.execution_source;
  if(!valid(proof)||(Object.prototype.hasOwnProperty.call(args,'_spb_expected_source')&&!same(args._spb_expected_source,proof)))return {blocked:refused()};
  return {args:{...args,_spb_expected_source:{sourceGeneration:proof.sourceGeneration,
    committedPath:proof.committedPath,committedFingerprint:proof.committedFingerprint,documentScope:proof.documentScope}}};
}
module.exports={prepare,valid,same};
