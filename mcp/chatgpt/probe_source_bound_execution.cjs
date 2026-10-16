'use strict';
// Direct local bridge calls exercise the page-side guard, bypassing the broker preflight.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const binding=require('./source-bound-execution.cjs'),root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const token=fs.readFileSync(path.join(dir,'pairing/token.txt'),'utf8').trim();
async function call(tool,args){const r=await fetch('http://127.0.0.1:59910/api/mcp/call',{method:'POST',headers:{'Content-Type':'application/json','X-SPB-MCP-Token':token,'X-SPB-MCP-Client':'codex-source-bound-page-probe'},body:JSON.stringify({tool,args,timeout:30}),signal:AbortSignal.timeout(45000)});assert.equal(r.status,200);return r.json();}
const keys=['layers','zones','selected_zone','paint_colours','pending_changes','recent_changes','saved_design_brief','convo','template_identity'];
const select=s=>Object.fromEntries(keys.map(k=>[k,s[k]===undefined?null:s[k]]));
function picture(r){assert.equal(r.ok,true);const im=(r.images||r.result&&r.result.images||[]).find(x=>x.data_url);assert.ok(im,'Preview image unavailable');return crypto.createHash('sha256').update(Buffer.from(im.data_url.split(',')[1],'base64')).digest('hex');}
(async()=>{
 const first=await call('get_state',{});assert.equal(first.ok,true);const proof=first.result.execution_source;assert.ok(binding.valid(proof),'Current source proof unavailable');
 const before=select(first.result),validRead=await call('get_state',{_spb_expected_source:proof});assert.equal(validRead.ok,true);
 const attempts=[];for(const delta of [{sourceGeneration:proof.sourceGeneration+1},{committedPath:proof.committedPath+'.older'},{committedFingerprint:proof.committedFingerprint+'different'},{documentScope:proof.documentScope+'.older-page'}]){
   const response=await call('edit_layer',{layer:'Base Paint',opacity:50,buyer_said:'make Base Paint half opacity',_spb_expected_source:{...proof,...delta}});
   assert.equal(response.ok,false);assert.match(response.error,/no changes were applied/);attempts.push({delta,response});
 }
 const after=select((await call('get_state',{})).result);assert.deepEqual(after,before);
 let roundtrip=null;
 if(process.argv.includes('--roundtrip')){
   const bodies=first.result.layers.filter(x=>x.name==='Base Paint'&&x.role==='body paint');assert.equal(bodies.length,1);
   const layerId=bodies[0].id;assert.equal(first.result.layers.filter(x=>x.id===layerId).length,1);
   const preview_before=picture(await call('preview',{_spb_expected_source:proof}));
   const changed=await call('edit_layer',{layer:layerId,opacity:50,buyer_said:'make the Base Paint body layer half opacity',_spb_expected_source:proof});assert.equal(changed.ok,true,changed.error);
   const during=(await call('get_state',{})).result;
   assert.notDeepEqual(during.layers,first.result.layers,'No layer edit happened');
   const undone=await call('undo',{steps:1,_spb_expected_source:proof});assert.equal(undone.ok,true,undone.error);
   const final=(await call('get_state',{})).result;
   for(const k of ['layers','zones','selected_zone','paint_colours','template_identity'])assert.deepEqual(final[k],first.result[k],k+' did not restore');
   const preview_after=picture(await call('preview',{_spb_expected_source:proof}));assert.equal(preview_after,preview_before);
   const restored_fields=['layers','zones','selected_zone','paint_colours','template_identity'];
   roundtrip={exact_layer:layerId,changed:changed.result,undone:undone.result,restored_fields,
     initial_fields:Object.fromEntries(restored_fields.map(k=>[k,first.result[k]===undefined?null:first.result[k]])),
     final_fields:Object.fromEntries(restored_fields.map(k=>[k,final[k]===undefined?null:final[k]])),during_layers:during.layers,preview_before,preview_after,
     limits:'Encoded preview equality and exposed state; not full native layer pixel or simulator/installer proof.'};
 }
 const checked_at=new Date().toISOString(),receipt='source-bound-page-'+checked_at.replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(dir,receipt),JSON.stringify({checked_at,proof,valid_read:true,attempts,before,after,roundtrip,limits:'Real page entry guard against four controlled stale identities; no actual document switch mid-edit, kit calibration or shared adoption. Positive exact-layer roundtrip only when explicitly present.'},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({receipt,page_refusals:attempts.length,fresh_bound_read:true,preserved_fields:keys.length,roundtrip:!!roundtrip}));
})().catch(e=>{console.error(e.message);process.exitCode=1});
