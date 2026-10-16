'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const binding=require('./source-bound-execution.cjs');
const geometry=require('./geometry-authority.cjs');
const proof={sourceGeneration:3,committedPath:'synthetic.psd',committedFingerprint:'synthetic',documentScope:'synthetic:3'};
const good=async()=>({status:200,json:{ok:true,result:{execution_source:proof}}});
// Extract the real generated page entry and existing source guard functions.
const text=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const slice=(a,b)=>{const i=text.indexOf(a),j=text.indexOf(b,i);assert.ok(i>=0&&j>i);return text.slice(i,j);};
const helpers=slice('    function mcpCaptureContext(', '    function mcpResolveLayerExact(');
const entry=slice('    function mcpCall(tool, args) {', '    // MCP-RENDER');
let current={...proof},loadingSwitch=false;const effects=[];
const sandbox={window:{SPBSourceLoadTransaction:{getGeneration:()=>current.sourceGeneration,getCommittedPath:()=>current.committedPath,getCommittedFingerprint:()=>current.committedFingerprint},
  SpbAiConnect:{documentScope:()=>current.documentScope},SpbAiLease:{begin:()=>{effects.push('lease');return true;},end:()=>effects.push('release')}},
 _busy:false,MCP_WRITE:{edit_layer:1},CAR:{ensure:async()=>{if(loadingSwitch)current={...current,sourceGeneration:current.sourceGeneration+1};}},
 mcpCallCore:async(tool,args)=>{effects.push('core');assert.equal(args._spb_expected_source,undefined);return {ok:true,result:{changed:true}};},
 mcpNamesIn:r=>r,render:()=>{},Promise,Object};
vm.createContext(sandbox);vm.runInContext(helpers+entry,sandbox);
(async()=>{
 assert.equal(geometry.qualifyLegacyTool('spb_get_state',{execution_source:proof}).execution_source,undefined);
 assert.equal(proof.committedPath,'synthetic.psd');
 const a={layer:'Exact decal',opacity:50};const prepared=await binding.prepare('edit_layer',a,good);
 assert.deepEqual(prepared.args._spb_expected_source,proof);assert.ok(!a._spb_expected_source);
 for(const read of [async()=>{throw Error('offline')},async()=>({status:503,json:{result:{execution_source:proof}}}),async()=>({status:200,json:{result:{}}})])assert.ok((await binding.prepare('edit_layer',a,read)).blocked);
 const stale={...proof,sourceGeneration:2};assert.ok((await binding.prepare('edit_layer',{...a,_spb_expected_source:stale},good)).blocked);
 for(const changes of [{sourceGeneration:4},{committedPath:'other.psd'},{committedFingerprint:'different'},{documentScope:'different-page:3'}]){
   current={...proof,...changes};const r=await sandbox.mcpCall('edit_layer',prepared.args);assert.equal(r.ok,false);assert.deepEqual(effects.splice(0),[]);assert.equal(sandbox._busy,false);
 }
 current={...proof};assert.equal((await sandbox.mcpCall('edit_layer',prepared.args)).ok,true);assert.deepEqual(effects.splice(0),['lease','core','release']);
 current={...proof};loadingSwitch=true;assert.equal((await sandbox.mcpCall('edit_layer',prepared.args)).ok,false);assert.deepEqual(effects.splice(0),['lease','release']);assert.equal(sandbox._busy,false);
 assert.ok(text.includes('s.execution_source = mcpCaptureContext(false)'));
 console.log('PASS broker read binding and actual generated executor: path/fingerprint/generation/page changes refuse before lease; fresh synthetic target passes; source change during preparation refuses before core.');
})().catch(e=>{console.error(e);process.exitCode=1});
