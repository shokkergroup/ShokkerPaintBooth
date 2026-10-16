'use strict';
// Execute the real launcher under controlled process boundaries: a ready login
// must not start inference; API login/config failures must never fall through.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'session-probe.cjs'),'utf8');
function run(auth,flags=['--preflight-only']) {
  const calls=[],lines=[];let exited=null,error=null;
  const mockProcess={argv:['node','probe','--codex','C:/fake/codex.exe','--port','59910',...flags],env:{Path:'keep',OPENAI_API_KEY:'not-to-be-used',codex_api_key:'not-to-be-used'},execPath:process.execPath,exit(n){exited=n;throw {exit:n};}};
  const loader=name=>name==='node:child_process'?{spawnSync(exe,args,opts){calls.push({kind:'status',exe,args,env:opts.env});return auth;},spawn(){calls.push({kind:'inference'});throw Error('Unexpected inference');}}:name==='node:fs'?{...fs,existsSync:()=>true}:name==='./subscription-client.cjs'?require('./subscription-client.cjs'):require(name);
  try{vm.runInNewContext(source,{require:loader,__dirname,process:mockProcess,console:{log:s=>lines.push(s)},setTimeout,clearTimeout});}catch(e){if(e.exit===undefined)error=e.message;}
  return {calls,lines,exited,error};
}
let r=run({status:0,stdout:'',stderr:'Logged in using ChatGPT'});
assert.equal(r.exited,0);assert.equal(r.error,null);assert.equal(r.calls.length,1);
assert(!('OPENAI_API_KEY' in r.calls[0].env));assert(!('codex_api_key' in r.calls[0].env));
const ready=JSON.parse(r.lines[0]);assert.equal(ready.ready,true);assert.equal(ready.listening,false);assert.equal(ready.inferenceStarted,false);
assert(!r.calls[0].args.some(a=>a.includes('forced_login_method')),'Read login before enforcing a method to avoid logging an API user out');
r=run({status:0,stdout:'Logged in using an API key',stderr:''});assert.match(r.error,/signed in with ChatGPT/);assert.equal(r.calls.length,1);assert.equal(r.lines.length,0);
r=run({status:1,stdout:'',stderr:'unknown configuration value'});assert.match(r.error,/configuration\/version/);assert.equal(r.calls.length,1);
r=run({status:null,error:Error('timeout'),stdout:'',stderr:''});assert.match(r.error,/could not complete login status/);assert.equal(r.calls.length,1);
r=run({status:0,stdout:'Logged in using ChatGPT',stderr:''},['--preflight-only','--service-tier','default']);assert.match(r.error,/supported fast or flex/);assert.equal(r.calls.length,0);
console.log('PASS real launcher: ChatGPT readiness starts no inference, API-auth/config/timeout/tier failures stay closed, credentials stripped, login restriction deferred until authenticated.');
