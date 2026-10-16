'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),pro=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8'),articles=require('./car-knowledge/build/cars.json').articles;
function fixture(){
 const input={value:''},button={disabled:false,setAttribute(){}},w={console,Date,JSON,Math,Set,Map,setTimeout:()=>1,clearTimeout(){},setInterval(){},document:{readyState:'loading',addEventListener(){},querySelector(){return null},getElementById(){return null}},localStorage:{getItem:k=>k==='SPB_CONVO'?'1':null,setItem(){}}};w.window=w;vm.createContext(w);
 for(const f of ['js/spb-convo-state.js','mcp/chatgpt/car-knowledge/core.js','mcp/chatgpt/car-knowledge/offline-answer.js','mcp/chatgpt/offline-ready.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w,{filename:f});
 let ready=false,epoch=1,card={},loads=0;const outputs=[];
 Object.assign(w,{zones:[{id:'z1',pattern:'checker',scale:.6,sourceLayers:['body']}],_psdLayers:[{id:'body',name:'Body'}],_busy:false,_progress:'',_cancelOpts:true,_log:[],_panel:{setAttribute(){},querySelectorAll:()=>[],querySelector:s=>s==='.spb-pai-input'?input:s==='[data-act="send"]'?button:null},SpbConversationScope:{observe(){},stamp:()=>epoch,current:x=>x===epoch},SpbAiConnect:{relaying:()=>false},SpbDesignIntent:require('./design-intent.js'),SpbEditorCapabilities:{answer:()=>null,previousFrom:()=>null},namedPatternAdvice:()=>null,SpbPbn:{draw(){}},SpbOfflineBuilder:{offlineMode:()=>true,state:()=>card,showAnswer:(r,text)=>{card={answer:r,text};}},SpbOfflineAnswer:{ready:()=>ready,load:()=>{loads++;return Promise.resolve().then(()=>{w.SpbCarReferenceAnswer.index(articles);ready=true;});}},render(){}});
 const marker='try { if (window.SpbConvo && SpbConvo.on()) SpbConvo.fromEntry(entry, r, text); } catch (eCV5) {}';assert.ok(pro.includes(marker));
 w.finish=(r,text,kind)=>{outputs.push(r);const entry={id:outputs.length,role:'ai',kind,lines:[],notes:[]};Object.assign(w,{entry,r,text});vm.runInContext(marker,w);return r;};
 const c=pro.indexOf('    var _composerFinishing = 0'),e=pro.indexOf('    function finish(',c);vm.runInContext(pro.slice(c,e),w);
 const start=pro.indexOf('    function send(text, o) {'),next=pro.slice(start+1).match(/^    function \w+\(/m);vm.runInContext(pro.slice(start,start+1+next.index).replace('// CAR-KNOWLEDGE:',"throw Error('legacy route'); // CAR-KNOWLEDGE:"),w);
 return {w,input,button,outputs,get loads(){return loads;},bump:()=>epoch++,cold:()=>{ready=false;},setReady:()=>{ready=true;}};
}
async function main(){
 const f=fixture(),q='Anything unusual about the Skip Barber template? Explain only.',paint=JSON.stringify({zones:f.w.zones,layers:f.w._psdLayers});f.input.value=q;
 const pending=f.w.send(q);assert.ok(pending&&typeof pending.then==='function');assert.equal(f.w._busy,true);assert.equal(f.button.disabled,true);assert.equal(f.outputs.length,0);assert.equal(f.w._cancelOpts,false,'New Send starts a fresh local read');
 f.input.value='I may want a finer checker next.';
 const answer=await pending;assert.equal(f.loads,1);assert.match(answer.text,/2048[\s\S]*simulator artwork/);assert.equal(answer.queue.length,0);assert.equal(answer.tools.length,0);assert.equal(answer.asked,undefined);assert.equal(f.w.SpbConvo.pending(),null);assert.equal(f.w.SpbConvo.view().history.at(-1).act,'answer');assert.equal(f.input.value,'I may want a finer checker next.');assert.equal(f.w._composerHeldDraft,true);assert.equal(f.button.disabled,false);assert.equal(JSON.stringify({zones:f.w.zones,layers:f.w._psdLayers}),paint);
 const other=fixture();other.input.value=q;const changed=other.w.send(q);other.bump();await changed;assert.equal(other.outputs.length,0);assert.equal(other.w._busy,false);assert.match(other.w._log.at(-1).text,/open document changed/);assert.equal(other.input.value,q);
 const provider=fixture();provider.input.value=q;const switched=provider.w.send(q);provider.w.SpbOfflineBuilder.offlineMode=()=>false;await switched;assert.equal(provider.outputs.length,0);assert.equal(provider.w._busy,false);
 const failure=fixture();failure.w.SpbOfflineAnswer.load=()=>Promise.reject(Error('network unavailable'));failure.input.value=q;await failure.w.send(q);assert.equal(failure.outputs.length,0);assert.equal(failure.w._busy,false);assert.match(failure.w._log.at(-1).text,/could not load/);assert.equal(failure.input.value,q);
 const killed=fixture();killed.w.SPB_CX3_OFF=true;assert.throws(()=>killed.w.send(q),/legacy route/);assert.equal(killed.loads,0);
 const mixed=fixture();mixed.setReady();assert.throws(()=>mixed.w.send('What is unusual about the Skip Barber template? Then paint Body red.'),/legacy route/);assert.equal(mixed.outputs.length,0);
 console.log(JSON.stringify({pass:true,actual_generated_Send:true,actual_local_readiness_helper:true,compiled_car_facts:true,cold_load_once:true,unsent_draft_retained:true,document_provider_failure_kill_guards:true,completed_answer_not_pending:true,no_paint_changes_or_tools:true}));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
