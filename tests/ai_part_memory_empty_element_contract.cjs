'use strict';
// Native roof provenance legitimately has e:'' when no element map is active.
// An absent element signature must still be rejected; this does not verify project hooks.
const assert=require('node:assert/strict');
const M=require('../js/spb-ai-part-memory.js');
const source={committed:true,path:'C:/fixture/truck.psd',fingerprint:'source-content-hash',width:2048,height:2048,generation:2};
const zone={id:'roof-id',name:'Roof blue',muted:false,useRegion:true,regionMask:new Uint8Array([1,0]),_aiPartProv:{r:JSON.stringify({layers:['Car Paint'],island:'roof'}),z:'2:abc',p:'2:abc',l:'current-layout',e:''}};
const proofs={isCommittedSource:s=>s===source,sameSourcePath:(a,b)=>a===b,editKey:r=>r.island,partOwnerCurrent:(z,p)=>p.e===''&&p.z==='2:abc',partMaskCurrent:()=>true,countOwners:()=>1};
const saved=M.saveRecord(zone,source,proofs);assert.ok(saved);assert.equal(saved.provenance.e,'');
assert.ok(M.prepareRestore(saved,source,{...zone,_aiPartProv:undefined},proofs));
const absent=JSON.parse(JSON.stringify(saved));delete absent.provenance.e;assert.equal(M.sanitizeRecord(absent),null);
const nullSig=JSON.parse(JSON.stringify(saved));nullSig.provenance.e=null;assert.equal(M.sanitizeRecord(nullSig),null);
const stale={...proofs,partOwnerCurrent:()=>false};assert.equal(M.prepareRestore(saved,source,zone,stale),null);
console.log('PASS empty current element signature5 checks; project/native integration not claimed');
