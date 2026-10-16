'use strict';
// Process success is not evidence that the buyer received a response.
function payload(call) {
  const texts=(call.result?.content||[]).filter(c=>c.type==='text');
  for (const c of texts) { try { return JSON.parse(c.text); } catch {} }
  return null;
}
module.exports=function delivery(calls,expected) {
  const received=new Set(),shown=new Set();
  for(const call of calls||[]) {
    if(call.status!=='completed'||call.result?.isError)continue;
    const data=payload(call);
    if(call.tool==='spb_wait_for_message'&&data?.messages?.length&&data.reply_to!=null)received.add(data.reply_to);
    if(call.tool==='spb_reply'&&data?.shown_in_app===true&&String(call.arguments?.text||'').trim())shown.add(call.arguments.reply_to);
  }
  const missing=[...received].filter(id=>!shown.has(id));
  return {pass:received.size===expected&&!missing.length,expected,received:received.size,delivered:[...received].filter(id=>shown.has(id)).length,missing_reply_to:missing};
};
