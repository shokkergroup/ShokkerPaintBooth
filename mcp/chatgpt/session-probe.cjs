'use strict';
// Runs the buyer's installed Codex client as a bounded integration test.
// No authentication implementation, API client or persistent Codex setting writes.
const {spawn, spawnSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const args = process.argv.slice(2);
function option(name, fallback) { const i=args.indexOf(name); return i < 0 ? fallback : args[i+1]; }
const executable = option('--codex');
const serviceTier=option('--service-tier');
const isolatedSubscription=args.includes('--subscription-isolated');
const preflightOnly=args.includes('--preflight-only');
const chosenModel=option('--model');
if(chosenModel&&!/^[a-zA-Z0-9._-]{1,80}$/.test(chosenModel))throw Error('Invalid model name.');
if(serviceTier&&!['fast','flex'].includes(serviceTier))throw Error('Use an installed-client supported fast or flex service tier.');
const clientOverrides=serviceTier?['-c','service_tier='+JSON.stringify(serviceTier)]:[];
const port = Number(option('--port','59910'));
const count = Number(option('--messages','2'));
const contextMode = args.includes('--context');
const editMode = args.includes('--edit-acceptance');
const arcaMode = args.includes('--arca-edit-acceptance');
const journeyMode = args.includes('--journey-acceptance');
const recoveryMode = args.includes('--result-recovery');
if(recoveryMode&&(!contextMode||journeyMode||arcaMode||editMode||port!==59910||count!==1))throw Error('Result recovery is one read-only context message on private59910.');
if(journeyMode && (arcaMode || editMode || !contextMode || port!==59910))throw Error('Journey acceptance requires context and the isolated59910 document, without another edit mode.');
if(arcaMode && (editMode || !contextMode || count!==2 || port!==59910))throw Error('ARCA acceptance requires two context-enabled messages on private59910 only.');
if(editMode && (!contextMode || count!==1 || port!==59910)) throw Error('Edit acceptance is one context-enabled message on private59910 only.');
if (!Number.isInteger(count) || count < 1 || count > 4) throw new Error('Use 1–4 bounded messages.');
if (!executable || !fs.existsSync(executable) || port < 59910 || port > 59999 || !Number.isInteger(port)) {
  throw new Error('Supply --codex <installed executable> and an isolated --port in 59910..59999.');
}
const root=path.resolve(__dirname,'../..');
const state=path.join(root,'_codex_mcp_work','chatgpt-dev',String(port));
const token=path.join(state,'pairing','token.txt');
if (!fs.existsSync(token)) throw new Error('Enable the AI bridge on the isolated SPB page first.');
const clientPolicy=require('./subscription-client.cjs');
const env=clientPolicy.cleanEnvironment(process.env);
const auth=spawnSync(executable,[...clientOverrides,'login','status'],{env,encoding:'utf8',windowsHide:true,timeout:20000});
if (auth.error || auth.status !== 0) {
  throw new Error('Installed Codex client could not complete login status. Check that client configuration/version before changing authentication. No API fallback.');
}
if (!/Logged in using ChatGPT/i.test(auth.stdout+auth.stderr)) {
  throw new Error('This test requires the installed Codex client to be signed in with ChatGPT. No API fallback.');
}
if(preflightOnly){console.log(JSON.stringify({ready:true,readiness:'authenticated_not_listening',authentication:'ChatGPT',apiFallback:false,listening:false,inferenceStarted:false,modelVerified:false,requestedModel:chosenModel||null,port,temporaryServiceTier:serviceTier||null,configurationChanged:false}));process.exit(0);}
if(isolatedSubscription&&(!contextMode||editMode||arcaMode||journeyMode||recoveryMode||port!==59910||!chosenModel))throw Error('Isolated subscription proof requires private59910, context, 1–4 bounded read-only messages and an explicit account-supported model.');
const tools=isolatedSubscription?['spb_wait_for_message','spb_assistant_context','spb_reply']:['spb_status','spb_wait_for_message','spb_reply','spb_encyclopedia','spb_get_state'];
if(contextMode&&!isolatedSubscription)tools.push('spb_assistant_context','spb_car_knowledge','spb_inspect_layer');
if(recoveryMode)tools.push('spb_preview','spb_check');
let fixtureReceipt=null;
if(editMode){
  const pre=spawnSync(process.execPath,[path.join(__dirname,'capture_paint_receipt.cjs'),'online-layer-preflight'],{cwd:root,env,encoding:'utf8',windowsHide:true,timeout:60000});
  if(pre.status!==0)throw Error('Live read-only fixture preflight failed; no edit session launched.');
  const meta=JSON.parse(pre.stdout.trim()); fixtureReceipt=meta.receipt;
  const receipt=JSON.parse(fs.readFileSync(path.join(state,fixtureReceipt),'utf8'));
  const paint=JSON.parse(receipt.calls.find(c=>c.tool==='spb_get_state').text);
  if(!JSON.stringify(paint.template_identity).includes('layered-protection-a.tga') || JSON.stringify((paint.layers||[]).map(l=>l.name).sort())!==JSON.stringify(['Body','Numbers','Sponsors']) || paint.zones?.length!==5)
    throw Error('Edit acceptance requires the untouched three-layer synthetic fixture with five baseline zones.');
  tools.push('spb_do','spb_preview','spb_check');
}
if(arcaMode||journeyMode){
 const pre=spawnSync(process.execPath,[path.join(__dirname,'capture_paint_receipt.cjs'),'online-arca-preflight','--spec'],{cwd:root,env,encoding:'utf8',windowsHide:true,timeout:60000});
 if(pre.status!==0)throw Error('ARCA live read-only preflight failed; no model launched.');
 fixtureReceipt=JSON.parse(pre.stdout.trim()).receipt;
 const receipt=JSON.parse(fs.readFileSync(path.join(state,fixtureReceipt),'utf8'));
 const paint=JSON.parse(receipt.calls.find(c=>c.tool==='spb_get_state').text);
 const wanted={'psd_0':'Paintable Area','psd_37':'Custom Spec Map / Blue Channel Clearcoat','psd_38':'Custom Spec Map / Green Channel Roughness','psd_40':'Custom Spec Map / Red Channel Metallic'};
 if(paint.template_identity?.source_paint_name!=='ARCA Chevy SS.tga'||paint.layers?.length!==42||paint.zones?.length!==5||Object.entries(wanted).some(([id,g])=>!paint.layers.some(l=>l.id===id&&l.name==='Base Paint'&&l.group===g))||paint.layers.find(l=>l.id==='psd_0')?.colour_overlay?.enabled)
  throw Error('ARCA acceptance requires the untouched private42-layer/5-zone baseline with four current exact Base Paint identities.');
 tools.push('spb_edit_layer','spb_preview','spb_check');
 if(journeyMode)tools.push('spb_do','spb_describe_paint','spb_get_car_map','spb_undo');
}
const server=contextMode?path.join(__dirname,'candidate-server.cjs'):path.join(root,'mcp','server','index.js');
const config='mcp_servers={shokker-paint-booth={command='+JSON.stringify(process.execPath)+
  ',args=['+JSON.stringify(server)+'],env={SPB_PORT="'+port+
  '",SPB_MCP_TOKEN_FILE='+JSON.stringify(token)+'},enabled_tools='+JSON.stringify(tools)+
  ',required=true,startup_timeout_sec=20,tool_timeout_sec=200}}';
const prompt='This is an owner-authorized integration test of the isolated SPB chat box. '+
  'Use only Shokker MCP tools. Do not read files, run shell commands, or use other services. '+
  (isolatedSubscription?'First wait for the fresh incoming buyer message. Then read spb_assistant_context with its exact text as query and include_paint true. ':contextMode?'Read spb_assistant_context with query "Resume the paint-design conversation" and include_paint true. Use the returned history to understand earlier options and buyer constraints. ':'Read spb_status. ')+
  'Use spb_wait_for_message timeout_s 170 and answer the buyer through spb_reply. '+
  'Do not post an unsolicited greeting. If spb_reply supports reply_to, copy the latest returned buyer message seq. '+
  'Follow the MCP server instructions. '+
  (contextMode?'For a named-car or template-reference question, use spb_car_knowledge for that exact variant. Keep inspected reference labels separate from actually loaded layers, cite its source when useful, and do not claim UV positions or latest-file compatibility without evidence. ':'')+
  (journeyMode ? 'This tests a real design conversation on the isolated ARCA42-layer document. Follow the incoming buyer messages and actual saved discussion; the harness does not prescribe a target, colour or expected response. Read current state and actual previews before editing. Resolve missing choices without guessing. Apply supported, fully specified requests through the available scoped tools, preserve the stated constraints and other artwork, and inspect the result. Do not save, export, delete, or replace the source. If the source or layer identities change, stop. Keep historical proposals separate from fresh permission to edit. Describe unsupported parts precisely and do not claim they were completed. ' :
  arcaMode ? 'This is the real ARCA42-layer template acceptance. The first incoming message is ambiguous: inspect the actual current layers and ask one short group/layer clarification; do not change anything. After the second incoming message explicitly selects the body paint layer, apply only its requested full-layer colour with spb_edit_layer, using the exact current Paintable Area / Base Paint identity and colour #c8102e. Inspect spb_preview before and after and read current state. Preserve every other layer, control mask, material channel and existing zone. Do not use add_zone or do for this entire-layer colour. Do not export, change visibility, or claim verified UV geometry. Reply truthfully with what changed and stop after two buyer messages. ' :
  editMode ? 'This bounded acceptance permits only one explicit incoming Body-layer recolour on the synthetic layered-protection-a.tga fixture. Read current state and inspect spb_preview before acting. If the source or layer identities changed, refuse and stop. Preserve Numbers and Sponsors layers, including their matching navy pixels. Pass the complete buyer words to spb_do; use at most one write call with an explicit Body layer target, never a whole-car or colour-only target. No output rendering, exporting, saving, deleting or filesystem tools. Inspect spb_check and actual preview afterward; report success only if the change stayed applied with correct scope and preserved artwork. Advice does not authorize a write. ' :
  'There are no paint-writing tools in this test. Discuss paint-design questions naturally from the context and guidance, preserve buyer constraints, explain tradeoffs, and answer hypothetical questions without applying anything. For a vague edit request ask one short clarification. ')+
  'Handle exactly '+count+' incoming buyer messages, then stop. '+
  'A message is handled only after spb_reply confirms shown_in_app:true for its reply_to. An edit, preview, check or final answer in this Codex session is not a delivered SPB reply. After checking an edit, reply in SPB with what actually happened, measured warnings and available recovery before ending or waiting again. If delivery fails, do not replay the paint operation; inspect delivery/connection status and report that limitation. '+
  'If the bridge is disabled, stop immediately. Do not keep waiting after the requested messages.';
const record={port,clientExecutable:executable,contextMode,editMode,arcaMode,journeyMode,recoveryMode,fixtureReceipt,started:new Date().toISOString(),authentication:'ChatGPT',apiFallback:false,calls:[],messages:[],errors:[]};
record.temporaryServiceTier=serviceTier||null;
record.candidateManifest=contextMode?JSON.parse(fs.readFileSync(path.join(__dirname,'candidates/sources.json'),'utf8')):null;
const launchArgs=clientPolicy.execArguments({isolated:isolatedSubscription,overrides:clientOverrides,model:chosenModel,config,prompt});
record.isolatedSubscription=isolatedSubscription;record.chosenModel=chosenModel||null;record.userConfigIgnored=isolatedSubscription;
const child=spawn(executable,launchArgs,{cwd:__dirname,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
let buffer='';
child.stdout.setEncoding('utf8');
child.stdout.on('data',data=>{buffer+=data;let i;while((i=buffer.indexOf('\n'))>=0){
  const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let event;try{event=JSON.parse(line);}catch{continue;}
  const item=event.item;
  if(event.type==='item.completed' && item?.type==='mcp_tool_call'){
    const entry={tool:item.tool,status:item.status,arguments:item.arguments,result:item.result,error:item.error};
    record.calls.push(entry);console.log(item.tool+': '+item.status);
  }else if(event.type==='item.completed'&&item?.type==='agent_message'){record.messages.push(item.text);console.log(item.text);}
  else if(event.type==='error'||event.type==='turn.failed'){record.errors.push(event.message||event.error?.message||'turn failed');}
}});
child.stderr.on('data',data=>{record.clientDiagnostic=(record.clientDiagnostic||'').concat(String(data)).slice(-3000);});
child.on('error',err=>record.errors.push(err.message));
const timer=setTimeout(()=>{record.errors.push('Bounded test timed out');child.kill();},360000);
child.on('close',code=>{clearTimeout(timer);record.exitCode=code;record.ended=new Date().toISOString();
  record.delivery=require('./session-delivery.cjs')(record.calls,count);
  if(!record.delivery.pass)record.errors.push('Customer reply delivery incomplete: '+JSON.stringify(record.delivery));
  const receipt=(editMode?'layered-model-probe-':contextMode?'context-session-probe-':'session-probe-')+record.started.replace(/[:.]/g,'-')+'.json';
  fs.writeFileSync(path.join(state,receipt),JSON.stringify(record,null,2)+'\n',{flag:'wx'});
  console.log('Receipt '+receipt);
  console.log('Session test exit '+code);process.exitCode=code|| (record.errors.length?1:0);
});
