'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const guard=require('./named-part-guard.cjs');
const part=(name,bbox=[.1,.1,.3,.3],evidence='buyer-taught box')=>({name,bbox,evidence});
const state=(parts,status='current')=>({execution_source:{sourceGeneration:1,committedPath:'synthetic.psd',committedFingerprint:'synthetic',documentScope:'synthetic:1'},editor_capabilities:{panel_locations:{status,parts}}});
const args={region:{part:'hood'},buyer_said:'paint the hood green',color:'#00ff00'};
assert.equal(guard.check('add_zone',args,state([part('hood')])),null);
assert.equal(guard.check('add_zone',{region:{part:'bonnet'}},state([part('hood')])),null);
for(const s of [null,{},state([part('hood')],'stale'),state([part('hood')],'loading'),
  state([part('hood',[.1,.1,.1,.3])]),state([part('hood',[0,0,1,1],'car library')]),
  state([part('hood front')]),state([part('hood'),part('hood',[.5,.5,.8,.8])])]){
  const r=guard.check('add_zone',args,s);assert.ok(r.refused);assert.equal(r.changed,false);
}
assert.ok(guard.check('add_zone',{region:{part:'left door'}},state([part('left side')])));
assert.ok(guard.check('add_zone',{region:{part:'both doors'}},state([part('left door')])));
assert.equal(guard.check('add_zone',{region:{part:'both doors'}},state([part('left door'),part('right door')])),null);
assert.ok(guard.check('do',{frame:{ops:[{target:{kind:'colour',parts:['hood']}}]}},state([])));
assert.ok(guard.check('do',{frame:{ops:[{target:{kind:'body'},except:{kind:'part',parts:['hood']}}]}},state([])));
assert.ok(guard.check('do',{frame:{ops:[{target:{kind:'body'},source:{kind:'part',parts:['hood']}}]}},state([])));
assert.ok(guard.check('do',{frame:{ops:[{target:{kind:'body',between:[{kind:'part',parts:['hood']}]}}]}},state([])));
for(const a of [{kit:'sponsor',parts:['hood']},{kit:'number',places:['roof']},{kit:'number'}]){
  assert.equal(guard.check('kit',a,state([part('hood'),part('roof')])).reason,'kit_geometry_unverified');
}
assert.equal(guard.check('kit',{kit:'sponsor',action:'remove',parts:['hood']},null),null);
assert.equal(guard.check('kit',{kit:'spec',action:'propose'},null),null);
assert.equal(guard.check('edit_layer',{layer:'Hood lettering',colour:'#00ff00'},null),null);
// Exercise the actual generated broker wrapper and kit function, not a copy of the guard.
const generated=fs.readFileSync(path.join(__dirname,'candidates/index.js'),'utf8');
function between(a,b){const start=generated.indexOf(a);assert.ok(start>=0);const end=generated.indexOf(b,start+1);assert.ok(end>start);return generated.slice(start,end);}
const wire=between('async function bridgeCall(', 'async function zonesNow(');
const preflight=between('// Named targets require fresh current-source confirmation.', 'async function chatTool(');
const kit=between('async function kitTool(', 'function checkerSecond(');
const undo=between('async function oaiUndo(', '// a CHECKER draws ONE colour');
const tweak=between('async function oaiGraphicTweak(', 'async function doTweak(');
const calls=[];let current=state([part('hood')]);
const sandbox={require:p=>{if(p==='../chatgpt/source-bound-execution.cjs')return require('./source-bound-execution.cjs');assert.equal(p,'../chatgpt/named-part-guard.cjs');return guard;},
  WRITE_APPS:['add_zone','do','add_graphic'],httpJson:async(method,url,body)=>{
    calls.push(body.tool);return {status:200,json:{ok:true,result:body.tool==='get_state'?current:{changed:true}}};
  },PART_WORDS:/\bhood\b/,normSaid:s=>s.toLowerCase(),kitText:o=>({content:[{type:'text',text:JSON.stringify(o)}]}),timeoutFor:()=>30,
  KIT_SAID:{},PORT:59910,toContent:x=>[{type:'text',text:JSON.stringify(x.result)}],HIST:[],RENDER_NEXT:'render',DIRTY:false,
  tweakAmounts:()=>({f:.65}),console};
vm.createContext(sandbox);vm.runInContext(wire+preflight+kit+undo+tweak,sandbox);
(async()=>{
  const noRead=async()=>{throw Error('must not read state for exact layer target')};
  assert.equal(await guard.refusal('edit_layer',{layer:'Hood lettering'},noRead),null);
  assert.ok(await guard.refusal('add_zone',args,async()=>{throw Error('offline')}));
  assert.ok(await guard.refusal('add_zone',args,async()=>({status:503,json:{result:state([part('hood')])}})));
  assert.equal((await sandbox.bridgeCall('add_zone',args,30)).json.result.changed,true);
  assert.deepEqual(calls.splice(0),['get_state','add_zone']);
  // A consecutive document switch cannot reuse the previous hood confirmation.
  current=state([]);
  assert.equal((await sandbox.bridgeCall('add_zone',args,30)).json.result.changed,false);
  assert.deepEqual(calls.splice(0),['get_state']);
  const r=await sandbox.kitTool({kit:'sponsor',parts:['hood'],buyer_said:'put logo on hood',logo_layer:'Logo'});
  assert.equal(JSON.parse(r.content[0].text).reason,'kit_geometry_unverified');
  assert.deepEqual(calls.splice(0),['get_state']);
  const entry={restore:{args,nW:1}};sandbox.HIST.push(entry);
  const ur=await sandbox.oaiUndo({steps:1});assert.equal(JSON.parse(ur.content[0].text).changed,false);
  assert.equal(sandbox.HIST.length,1);assert.equal(sandbox.HIST[0],entry);assert.equal(sandbox.DIRTY,false);
  assert.deepEqual(calls.splice(0),['get_state']);
  const tr=await sandbox.oaiGraphicTweak({amount:'little'},{name:'graphic'},{args},'scale',false,[]);
  assert.equal(JSON.parse(tr.content[0].text).changed,false);assert.equal(sandbox.HIST.length,1);
  assert.deepEqual(calls.splice(0),['get_state']);
  assert.ok(!generated.includes('PARTS_CACHE'));
  assert.ok(generated.indexOf('if (WRITE_APPS.indexOf(app) !== -1) { const refusal')<generated.indexOf('  let baseFirst = null;'));
  console.log('PASS named-part preflight: fresh source, fail-closed, exact scope, both sides, direct broker and kit paths; confirmed synthetic positive only.');
})().catch(e=>{console.error(e);process.exitCode=1});
