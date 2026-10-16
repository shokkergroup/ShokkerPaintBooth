'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8'),start=src.indexOf('    function mcpRender() {'),end=src.indexOf('    function mcpCallCore(',start);
assert.ok(start>0&&end>start);
async function run({open=false,ok=true,changed=false,killed=false,running=false,throws=false,replace=false}={}){
 let now=10,closed=0,rendered=0,epoch=1,panel={open,getClientRects(){return this.open?[{}]:[];}};
 const originalPanel=panel,w={Promise,Date:{now:()=>now},document:{getElementById:()=>panel},Z:{whenSettled:()=>Promise.resolve()},ShokkerAPI:{_renderInProgress:running},SpbConversationScope:{stamp:()=>epoch,current:s=>s===epoch},SPB_CX3_OFF:killed,showToast(){},closeRenderResults(){closed++;panel.open=false;},safeDoRender(){rendered++;if(throws)throw Error('render failure');panel.open=true;now++;w._spbRenderOutcome={ok,at:now,elapsed:0.2,zones:1,saved:0,iracing:false,error:'render error'};if(changed)epoch++;if(replace)panel={open:true,getClientRects:()=>[{}]};}};
 w.window=w;vm.createContext(w);vm.runInContext(src.slice(start,end),w);
 const result=await w.mcpRender();return {closed,rendered,result,open:panel.open,same:panel===originalPanel};
}
(async()=>{
 const fresh=await run();assert.equal(fresh.closed,1);assert.equal(fresh.open,false);assert.equal(fresh.result.result.rendered,true);assert.equal(fresh.result.result.files_saved,0);
 for(const opts of [{open:true},{ok:false},{changed:true},{killed:true},{running:true},{throws:true},{replace:true}]){const r=await run(opts);assert.equal(r.closed,0,JSON.stringify(opts));}
 console.log(JSON.stringify({pass:true,actual_generated_mcp_render:true,successful_new_results_modal_closed:true,manual_existing_dialog_failure_document_replacement_and_kill_preserved:true,outcome_and_saving_fields_unchanged:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
