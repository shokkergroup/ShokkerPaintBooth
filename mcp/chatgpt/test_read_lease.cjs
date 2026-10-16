'use strict';
// Real mcpCall boundary with stubs: proves lease behavior, not painting correctness.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const start=source.indexOf('    function mcpCall(tool, args) {'),end=source.indexOf('    // MCP-RENDER',start);
assert.ok(start>=0&&end>start);
async function run(tool,allowed=true,busy=false){
  const counts={begin:0,end:0,core:0};
  const c={Promise,_busy:busy,window:{SpbAiLease:{begin(){counts.begin++;return allowed},end(){counts.end++}}},render(){},mcpCaptureContext(){return{}},mcpStaleResult(){return null},MCP_WRITE:{},mcpCallCore(){counts.core++;return {ok:true}},mcpNamesIn:r=>r};
  vm.createContext(c);vm.runInContext(source.slice(start,end),c);
  const result=await c.mcpCall(tool,{});return{result,counts};
}
(async()=>{
  const readers=['status','get_state','zones','list_tools','encyclopedia','get_car_map','preview','design_recipes','suggest_finishes','find_finishes','finish_details','compare_finishes','browse_catalog','find_patterns','find_spec_patterns','get_help','check_setup','describe_paint','look_at_paint','check'];
  for(const tool of readers){const r=await run(tool,false);assert.equal(r.result.ok,true,tool);assert.deepEqual(r.counts,{begin:0,end:0,core:1});}
  let r=await run('edit_zone');assert.equal(r.result.ok,true);assert.deepEqual(r.counts,{begin:1,end:1,core:1});
  r=await run('edit_zone',false);assert.equal(r.result.ok,false);assert.equal(r.counts.core,0);
  r=await run('status',true,true);assert.equal(r.result.ok,false);assert.equal(r.counts.core,0);
  for(const tool of ['do','undo','render','mark_elements','request_parts','unknown_tool']){const r=await run(tool,false);assert.equal(r.result.ok,false,tool);assert.equal(r.counts.core,0);}
  console.log('Read/write lease boundary:20 readers skip the editing lease; writes, unknown tools and busy guards retain it');
})().catch(e=>{console.error(e);process.exitCode=1});
