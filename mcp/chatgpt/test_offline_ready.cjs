'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const w={setTimeout,clearTimeout,Promise};w.window=w;vm.createContext(w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'offline-ready.js'),'utf8'),w);
const R=w.SpbOfflineReady;
(async()=>{
  assert.equal(R.wait(null),null);assert.equal(R.wait({ready:()=>true,load:()=>{throw Error('unnecessary load')}}),null);
  let ready=false,count=0;
  await R.wait({ready:()=>ready,load:()=>{count++;ready=true;}},500);
  assert.equal(count,1);assert.equal(ready,true);
  await assert.rejects(R.wait({ready:()=>false,load:()=>Promise.resolve()},500),/could not load/);
  await assert.rejects(R.wait({ready:()=>false,load:()=>Promise.reject(Error('network'))},500),/could not load/);
  await assert.rejects(R.wait({ready:()=>false,load:()=>new Promise(()=>{})},15),/still loading/);
  console.log('PASS warm knowledge skips loading; cold knowledge waits; failed, empty and stalled loads produce an honest retry message');
  const source=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
  const start=source.indexOf('    function send(text, o) {'),end=source.indexOf('        // APPCHAT ',start);
  assert.ok(start>=0&&end>start);
  for(const scenario of ['normal','cancel','changed-paint-edit','changed-paint-question','changed-helper']){
    let release,loaded=false,identity=1,online=false;
    const gate={console,Promise,setTimeout,clearTimeout,_busy:false,_progress:'',_cancelOpts:false,_log:[],completed:[],
      SpbOfflineReady:R,SpbOfflineAnswer:{ready:()=>loaded,load:()=>new Promise(resolve=>{release=()=>{loaded=true;resolve();};}),kind:()=>scenario.endsWith('question')?'question':'edit'},
      SpbAiConnect:{relaying:()=>online},elementRunIdentity:()=>identity,elementRunCurrent:x=>x===identity,render(){}};
    gate.window=gate;vm.createContext(gate);
    vm.runInContext(source.slice(start,end)+' completed.push(text); }',gate);
    const pending=gate.send('test request');await Promise.resolve();
    if(scenario==='cancel')gate._cancelOpts=true;
    if(scenario.startsWith('changed-paint'))identity=2;
    if(scenario==='changed-helper')online=true;
    release();await pending;
    assert.equal(gate.completed.length,['normal','changed-paint-question'].includes(scenario)?1:0,scenario);
    assert.equal(gate._busy,false,scenario);
  }
  console.log('PASS actual send boundary resumes once, honors Cancel/helper changes, rechecks edit identity and permits questions during file loading');
})().catch(e=>{console.error(e);process.exitCode=1});
