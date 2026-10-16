'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
async function check(mode,client,expected){
  const context={window:{crypto:require('node:crypto').webcrypto,spbProAI:{refresh(){}}},localStorage:{getItem(){return mode},setItem(){}},
    document:{createElement(){return {}},head:{appendChild(){}}},setTimeout(){},setInterval(){},
    fetch(){return Promise.resolve({json:()=>Promise.resolve({ok:true,enabled:true,listening:true,client})});}};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates','spb-ai-connect.js'),'utf8'),context);
  await context.window.SpbAiConnect.refresh();
  assert.equal(context.window.SpbAiConnect.cardHtml(false).includes('connected and listening'),expected,mode+' / '+client);
  if(mode==='offline')assert.ok(context.window.SpbAiConnect.cardHtml(true).includes('data-act="aic-switch"'),'keep switching available after the first offline message');
}
(async()=>{
  await check('chatgpt','claude-code-watcher',false);
  await check('claude','codex-mcp-client',false);
  await check('chatgpt','codex-mcp-client',true);
  await check('claude','claude-desktop',true);
  await check('chatgpt','unknown-client',false);
  await check('offline','',false);
  console.log('Provider badge and offline switching: 6/6 pass');
})().catch(e=>{console.error(e);process.exitCode=1});
