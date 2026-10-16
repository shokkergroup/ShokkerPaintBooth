'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
async function run(relative,{stale=false,verdict='reported'}={}) {
 const source=fs.readFileSync(path.join(root,relative),'utf8');
 const start=source.indexOf('return MFm.measureOnly(entry, _mcpSaid, queue,');
 const end=source.indexOf('}, function () { return out0; });',start)+'}, function () { return out0; });'.length;
 assert.ok(start>0&&end>start);
 let rendered=0;const entry={text:'Your external AI assistant changed your paint through the AI bridge.'};
 const m={verdict,line:'Done — the Paintable Area / Base Paint layer changed. 1664 px of your numbers / logos changed: check them.'};
 const w={entry,MFm:{measureOnly:async()=>m},_mcpSaid:'',queue:[],previewSynced:()=>true,mcpContext:{},ap:{lines:['edit']},out0:{result:{note:''}},mcpStaleResult:()=>stale,render:()=>rendered++};
 vm.createContext(w);const out=await vm.runInContext('(async function(){'+source.slice(start,end)+'})()',w);
 return {entry,out,rendered};
}
(async()=>{
 const old=await run('js/spb-pro-ai.js');assert.doesNotMatch(old.entry.text,/1664/);
 const file='mcp/chatgpt/candidates/spb-pro-ai.js',live=await run(file);
 assert.match(live.entry.text,/Preview check \(estimated\).*1664/);assert.match(live.entry.text,/does not verify every source pixel/);assert.equal(live.rendered,1);
 assert.equal(live.out.result.measured.verdict,'reported');
 for(const options of [{stale:true},{verdict:'not_measured'},{verdict:'skip'}])assert.equal((await run(file,options)).rendered,0);
 console.log('PASS actual MCP callback displays measured warning without model reply; stale/unmeasured reports cannot alter chat');
})().catch(e=>{console.error(e);process.exitCode=1;});
