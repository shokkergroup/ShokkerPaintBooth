'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const api=require('./subscription-control.cjs'),dir=fs.mkdtempSync(path.join(os.tmpdir(),'spb-controller-'));
try{
 const c=api.acquire(dir);assert.equal(api.status(dir,()=>true).state,'starting');assert.throws(()=>api.acquire(dir),/EEXIST/);
 c.publish('waiting_without_inference',{model_inferences_started:0});const observed=api.status(dir,()=>true);assert.equal(observed.model_inferences_started,0);assert.equal(observed.active,null);assert.equal(observed.process_present,true);assert.equal(observed.reported_active,true);assert.equal(observed.availability,'unverified');assert.equal(c.stopRequested(),false);
 const p=api.paths(dir);fs.writeFileSync(p.stop,JSON.stringify({...c.owner,instance:'00000000-0000-0000-0000-000000000000'}));assert.equal(c.stopRequested(),false,'A previous controller stop cannot stop its replacement');
 assert.equal(api.requestStop(dir).ok,true);assert.equal(c.stopRequested(),true);assert.equal(api.status(dir,()=>true).stop_requested,true);
 assert.equal(c.release('owner_stop'),true);assert.equal(api.status(dir).active,false);assert.equal(api.status(dir).state,'owner_stop');assert.equal(api.status(dir).last.model_inferences_started,0);assert.equal(fs.existsSync(p.stop),false);
 const next=api.acquire(dir);const replacement={...next.owner,instance:'00000000-0000-0000-0000-000000000000'};fs.writeFileSync(p.lock,JSON.stringify(replacement));assert.equal(next.stopRequested(),true);assert.equal(next.release(),false);assert.throws(()=>next.publish('waiting'),/ownership changed/);assert.deepEqual(JSON.parse(fs.readFileSync(p.lock)),replacement);
 assert.equal(api.status(dir,()=>true).requires_review,true,'PID presence does not prove a replacement owns the old status');assert.equal(api.status(dir,()=>false).state,'stale_lock');assert.equal(api.status(dir,()=>null).active,null);fs.writeFileSync(p.lock,'{"pid":1}');assert.equal(api.requestStop(dir).reason,'unrecognized_lock');assert.equal(api.status(dir).requires_review,true);
 fs.writeFileSync(p.lock,'broken json');assert.equal(api.requestStop(dir).reason,'unrecognized_lock');assert.equal(api.status(dir).active,null);assert.equal(api.status(dir).state,'unrecognized_lock');assert.throws(()=>api.acquire(dir),/EEXIST/,'Malformed ownership is preserved for review rather than cleared');
 console.log(JSON.stringify({pass:true,exclusive_ownership:true,stop_scoped_to_instance:true,replaced_lock_preserved:true,stale_and_unknown_require_review:true,no_inference:true}));
}finally{for(const n of fs.readdirSync(dir))fs.unlinkSync(path.join(dir,n));fs.rmdirSync(dir);}
