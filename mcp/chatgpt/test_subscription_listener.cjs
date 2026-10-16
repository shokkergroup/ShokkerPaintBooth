'use strict';
const assert=require('node:assert/strict'),core=require('./subscription-listener-core.cjs');
const messages=[{seq:7,text:'Can matte blue artwork work with a chrome body?',document_scope:'paint-a'}];
function transcript(pending,answered=false){return{ok:true,available:true,helper:'chatgpt',document_scope:'paint-a',turns:[...pending.messages.map(m=>({...m,role:'user'})),...(answered?[{role:'assistant',reply_to:7,text:'Advice.',document_scope:'paint-a'}]:[])]};}
async function scenario(opts={}){
 let pending=opts.pending||null,waits=0,inferences=0,delivered=false,saves=[],states=[],ticks=0;
 const result=await core.listen({
  wait:async()=>{waits++;ticks++;return opts.responses?.[waits-1]||{status:200,json:{ok:true,messages}};},
  runTurn:async()=>{inferences++;if(opts.throwWorker)throw Error('crash');delivered=opts.delivered!==false;return{ok:opts.workerOk!==false};},
  load:()=>pending,save:value=>{pending=structuredClone(value);saves.push(pending);},
  recover:opts.recover,receiveOnly:opts.receiveOnly,conversation:async()=>opts.conversation||transcript(pending,opts.alreadyAnswered||delivered),
  stop:()=>ticks>=(opts.stopAfter||10),pause:async()=>{},maxBatches:1,onState:s=>states.push(s)
 });
 return{result,waits,inferences,pending,saves,states};
}
(async()=>{
 const pending=core.batch(messages);
 assert.equal(core.verify(pending,transcript(pending)).ok,true);
 for(const bad of [
  {...transcript(pending),helper:'claude'}, {...transcript(pending),document_scope:'paint-b'},
  {...transcript(pending),turns:[]}, {...transcript(pending),turns:[{...messages[0],text:'changed',role:'user'}]}
 ])assert.equal(core.verify(pending,bad).ok,false);
 assert.equal(core.verify(pending,transcript(pending),pending.claimed_at+1800000).reason,'invalid_or_expired_pending');
 assert.equal(core.verify(pending,transcript(pending,true)).reason,'already_replied');
 assert.throws(()=>core.batch([{...messages[0],document_scope:undefined}]));
 assert.throws(()=>core.batch([messages[0],{...messages[0],seq:8,document_scope:'other'}]));
 assert.throws(()=>core.batch([messages[0],messages[0]]));
 let r=await scenario({responses:[{status:200,json:{ok:true,none:true}},{status:200,json:{ok:true,none:true}}],stopAfter:2});
 assert.equal(r.inferences,0);assert.equal(r.saves.length,0);assert.equal(r.result.stopped,'deadline');
 r=await scenario({stopAfter:1});assert.equal(r.inferences,0);assert.equal(r.waits,1);assert.equal(r.pending.state,'pending');assert.equal(r.result.stopped,'deadline','A stop during the claim keeps the question without starting a worker');
 r=await scenario({responses:[{status:0},{status:503},{status:200,json:{ok:true,messages}}]});
 assert.equal(r.inferences,1);assert.equal(r.waits,3);assert.equal(r.pending.state,'delivered');assert.equal(r.saves[0].state,'pending');
 assert.deepEqual(r.states.slice(0,4),['waiting_without_inference','reconnecting_without_inference','waiting_without_inference','reconnecting_without_inference']);
 r=await scenario({delivered:false,workerOk:false});assert.equal(r.inferences,1);assert.equal(r.waits,1);assert.equal(r.pending.state,'pending');assert.equal(r.result.stopped,'worker_failed_pending_preserved');
 r=await scenario({throwWorker:true});assert.equal(r.pending.state,'pending');assert.equal(r.inferences,1);
 r=await scenario({pending});assert.equal(r.waits,0);assert.equal(r.inferences,0);assert.equal(r.result.stopped,'pending_requires_explicit_recovery');
 r=await scenario({receiveOnly:true});assert.equal(r.inferences,0);assert.equal(r.pending.state,'pending');assert.equal(r.result.stopped,'pending_checkpoint');
 r=await scenario({pending,recover:true});assert.equal(r.waits,0);assert.equal(r.inferences,1);assert.equal(r.pending.state,'delivered');
 r=await scenario({pending,recover:true,alreadyAnswered:true});assert.equal(r.waits,0);assert.equal(r.inferences,0);assert.equal(r.pending.recovered_without_inference,true);
 r=await scenario({pending,recover:true,conversation:{...transcript(pending),document_scope:'paint-b'}});assert.equal(r.inferences,0);assert.equal(r.pending.state,'pending');
 r=await scenario({workerOk:false});assert.equal(r.inferences,1);assert.equal(r.pending.state,'delivered','Lost worker acknowledgement is settled by the authoritative exact transcript.');
 r=await scenario({responses:[{status:200,json:{ok:true,messages:[{...messages[0],again:true}]}}]});assert.equal(r.inferences,1);assert.equal(r.saves[0].messages[0].again,true);
 for(const response of [{status:401},{status:403},{status:404},{status:200,json:{ok:true,none:true,enabled:false}},{status:200,json:{ok:true,messages:[{seq:1,text:'no scope'}]}}]){
  r=await scenario({responses:[response]});assert.equal(r.inferences,0);
 }
 r=await scenario({responses:[{status:0},{status:0},{status:0},{status:0}]});assert.equal(r.inferences,0);assert.equal(r.waits,4);assert.equal(r.result.stopped,'app_unreachable');
 for(const delivered of [true,false]){
  let saved=null,stopped=false,waits=0,inferences=0;
  const result=await core.listen({load:()=>null,save:v=>{saved=structuredClone(v);},wait:async()=>{waits++;return{status:200,json:{ok:true,messages}};},runTurn:async()=>{inferences++;stopped=true;return{ok:delivered};},conversation:async()=>transcript(saved,stopped&&delivered),stop:()=>stopped,pause:async()=>{},maxBatches:2});
  assert.equal(waits,1);assert.equal(inferences,1);assert.equal(saved.state,delivered?'delivered':'pending');assert.equal(result.stopped,delivered?'deadline':'worker_failed_pending_preserved','Cooperative busy stop settles delivery but never starts another turn or replays');
 }
 console.log('PASS listener: zero idle/reconnect inference; durable pending before model; explicit read-only recovery; exact provider/document/text/sequence/age guards; already delivered skips inference; worker failure preserves without replay.');
})();
