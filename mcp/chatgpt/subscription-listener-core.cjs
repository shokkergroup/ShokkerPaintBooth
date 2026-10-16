'use strict';
// Read-only conversation recovery. Never replays paint operations or resumes an
// arbitrary Codex session. The app's current scoped transcript is authoritative.
const SCHEMA='spb-subscription-pending/1';
function batch(messages,now=Date.now()) {
  if(!Array.isArray(messages)||!messages.length||messages.length>200)throw Error('Invalid incoming message batch.');
  let previous=0,scope=null;
  const clean=messages.map(m=>{
    if(!Number.isSafeInteger(m.seq)||m.seq<=previous||typeof m.text!=='string'||!m.text.trim()||m.text.length>4000||typeof m.document_scope!=='string'||!m.document_scope||m.document_scope.length>200)throw Error('Incoming message has no valid exact sequence/text/document scope.');
    if(scope!==null&&scope!==m.document_scope)throw Error('Incoming batch crosses documents.');
    previous=m.seq;scope=m.document_scope;
    return{seq:m.seq,text:m.text,document_scope:scope,...(m.again===true?{again:true}:{})};
  });
  return{schema:SCHEMA,helper:'chatgpt',document_scope:scope,claimed_at:now,messages:clean,state:'pending'};
}
function verify(pending,conversation,now=Date.now()) {
  if(pending?.schema!==SCHEMA||pending.helper!=='chatgpt'||pending.state!=='pending'||!Number.isFinite(pending.claimed_at)||now<pending.claimed_at||now-pending.claimed_at>=1800000)return{ok:false,reason:'invalid_or_expired_pending'};
  let valid;try{valid=batch(pending.messages,pending.claimed_at);}catch{return{ok:false,reason:'invalid_pending'};}
  if(valid.document_scope!==pending.document_scope)return{ok:false,reason:'invalid_pending_scope'};
  if(!conversation?.ok||conversation.available!==true||conversation.helper!=='chatgpt'||conversation.document_scope!==pending.document_scope||!Array.isArray(conversation.turns))return{ok:false,reason:'conversation_scope_unavailable_or_changed'};
  const newest=valid.messages.at(-1),turns=conversation.turns;
  if(turns.some(t=>t.role==='assistant'&&Number.isSafeInteger(t.reply_to)&&t.reply_to>=newest.seq&&t.document_scope===pending.document_scope))return{ok:false,reason:'already_replied',reply_to:newest.seq};
  for(const m of valid.messages){
    if(!turns.some(t=>t.role==='user'&&t.seq===m.seq&&t.text===m.text&&t.document_scope===pending.document_scope))return{ok:false,reason:'pending_message_not_in_current_transcript'};
    if(turns.some(t=>t.role==='assistant'&&t.reply_to===m.seq&&t.document_scope===pending.document_scope))return{ok:false,reason:'partially_replied_batch'};
  }
  return{ok:true,reply_to:newest.seq,messages:valid.messages};
}
async function listen({wait,runTurn,save,load,recover=false,receiveOnly=false,conversation,stop=()=>false,pause,maxBatches=1,onState=()=>{}}) {
  if(!Number.isInteger(maxBatches)||maxBatches<1||maxBatches>4)throw Error('Use one to four bounded batches.');
  let pending=await load(),handled=0,failures=0;
  if(pending?.state==='pending'&&!recover)return{stopped:'pending_requires_explicit_recovery',handled};
  if(pending?.state!=='pending')pending=null;
  while(!stop()&&handled<maxBatches){
    if(!pending){
      onState('waiting_without_inference');
      const r=await wait();
      if(r.status===401||r.status===403)return{stopped:'pairing_rejected',handled};
      if(r.status===404)return{stopped:'app_chat_unavailable',handled};
      if(r.json?.enabled===false||r.json?.error==='disabled')return{stopped:'connection_off',handled};
      if(r.status===0||r.status>=500){
        if(++failures>3)return{stopped:'app_unreachable',handled};
        onState('reconnecting_without_inference');await pause(Math.min(15000,1000*2**failures));continue;
      }
      if(r.status!==200||r.json?.ok!==true)return{stopped:'invalid_wait_response',handled};
      failures=0;
      if(r.json.none===true)continue;
      try{pending=batch(r.json.messages);}catch{return{stopped:'invalid_or_unscoped_messages',handled};}
      // Commit before inference; a crash leaves a recoverable question.
      await save(pending);
      if(stop())return{stopped:'deadline',handled};
      if(receiveOnly)return{stopped:'pending_checkpoint',handled};
    }
    const before=verify(pending,await conversation());
    if(!before.ok){
      if(before.reason==='already_replied')await save({...pending,state:'delivered',recovered_without_inference:true});
      return{stopped:before.reason,handled};
    }
    if(stop())return{stopped:'deadline',handled};
    onState('answering_read_only');
    let result;try{result=await runTurn(pending);}catch{result={ok:false};}
    // An exit code alone is not a delivered answer. If its acknowledgement was
    // lost, the exact current transcript can settle delivery without re-running.
    let after;try{after=verify(pending,await conversation());}catch{after={ok:false,reason:'delivery_unconfirmed'};}
    if(after.reason!=='already_replied')return{stopped:result?.ok?'reply_not_confirmed':'worker_failed_pending_preserved',handled};
    await save({...pending,state:'delivered',delivered_at:Date.now()});
    handled++;pending=null;onState('delivered');
  }
  return{stopped:handled===maxBatches?'batch_limit':'deadline',handled};
}
module.exports={batch,verify,listen,SCHEMA};
