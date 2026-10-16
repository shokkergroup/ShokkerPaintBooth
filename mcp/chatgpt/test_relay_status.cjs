'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(path.join(__dirname,'candidates/spb-ai-connect.js'),'utf8'),a=src.indexOf('    function recentReply()'),b=src.indexOf('    function copy(',a);
assert.ok(a>0&&b>a);
for(const provider of ['chatgpt','claude']){
 const S={waiting:'working',listening:false,lastSent:1,lastReply:0,step:true,status:{enabled:true,lastCallAgo:100}},ctx={S,window:{},Date:{now:()=>100000},LISTEN_LINE:'Listen to my Shokker chat',mode:()=>provider,name:()=>provider==='chatgpt'?'ChatGPT':'Claude',relaying:()=>true,esc:String,cx2:()=>true,stepsHtml:()=>'<ol>setup</ol>'};vm.createContext(ctx);vm.runInContext(src.slice(a,b),ctx);
 assert.match(ctx.statusLine(provider),/received your message/);assert.doesNotMatch(ctx.statusLine(provider),/connected and listening|follow the steps/);
 assert.doesNotMatch(ctx.cardHtml(true),/<details[^>]* open>/,'Received work does not expand setup instructions');
 assert.match(ctx.tailHtml(),/answer has not returned/);assert.doesNotMatch(ctx.tailHtml(),/closed or restarted/);
 S.waiting=false;S.lastReply=99999;assert.match(ctx.statusLine(provider),/Last answer received/);assert.doesNotMatch(ctx.cardHtml(true),/<details[^>]* open>/);
 S.status.enabled=false;assert.match(ctx.statusLine(provider),/Not connected/,'A prior answer is not live-connection proof');
 S.status.enabled=true;S.lastReply=0;S.waiting='sent';assert.match(ctx.statusLine(provider),/Waiting for/);assert.match(ctx.tailHtml(),/hasn’t answered yet/,'Undelivered messages retain recovery guidance');
 S.waiting=false;S.listening=true;assert.match(ctx.statusLine(provider),/connected and listening/);
}
console.log(JSON.stringify({pass:true,chatgpt_and_claude:true,received_work_not_disconnected:true,no_false_live_listener_claim:true,setup_collapsed_during_work:true,undelivered_recovery_retained:true}));
