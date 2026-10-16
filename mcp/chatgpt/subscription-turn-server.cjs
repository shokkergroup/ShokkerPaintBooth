'use strict';
// Private read-only worker adapter. Reuses the existing chatTool handoff so its
// scope/advice guards remain intact, without claiming the inbox a second time.
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const core=require('./subscription-listener-core.cjs');
const port=Number(process.env.SPB_PORT);
if(port!==59910)throw Error('Subscription worker adapter is private59910 only.');
const handoff=path.resolve(process.env.SPB_SUBSCRIPTION_HANDOFF||'');
const allowedDir=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
if(path.dirname(handoff)!==allowedDir||path.basename(handoff)!=='subscription-pending.json')throw Error('Use the dedicated private pending handoff.');
const pending=JSON.parse(fs.readFileSync(handoff,'utf8'));
const source=fs.readFileSync(path.join(__dirname,'candidates/index.js'),'utf8');
function replaceOnce(s,a,b){if(s.split(a).length!==2)throw Error('Worker adapter source anchor changed; review before running.');return s.replace(a,b);}
let changed=replaceOnce(source,"  const secs = Math.max(10, Math.min(590, Number(args && args.timeout_s) || 170));",`  if (globalThis.__spbHandoffUsed) return {isError:true,content:[{type:'text',text:'This worker handles its single claimed batch only. Stop; the local listener owns the next wait.'}]};
  globalThis.__spbHandoffUsed = true;
  const secs = Math.max(10, Math.min(590, Number(args && args.timeout_s) || 170));`);
changed=replaceOnce(changed,"await httpJson('GET', '/api/mcp/inbox/wait?timeout=' + secs, null, (secs + 20) * 1000)",`await globalThis.__spbClaimedBatch(async function(){ return await httpJson('GET','/api/mcp/conversation',null,15000); })`);
changed=replaceOnce(changed,"case 'tools/list': return reply(id, { tools: allTools() });","case 'tools/list': return reply(id, { tools: allTools().filter(t=>['spb_wait_for_message','spb_assistant_context','spb_reply'].includes(t.name)) });");
changed=replaceOnce(changed,"case 'tools/call': { const out = await callTool(params && params.name, params && params.arguments); return reply(id, out); }",`case 'tools/call': {
        if(!['spb_wait_for_message','spb_assistant_context','spb_reply'].includes(params && params.name))return fail(id,-32602,'Read-only conversation worker: unavailable tool.');
        if(params.name==='spb_reply'&&params.arguments?.reply_to!==globalThis.__spbPending.messages.at(-1).seq)return fail(id,-32602,'Reply must acknowledge the exact claimed batch.');
        if(params.name!=='spb_wait_for_message'&&!globalThis.__spbHandoffUsed)return fail(id,-32602,'Receive the scoped handoff before reading context or replying.');
        if(params.name==='spb_assistant_context'&&(params.arguments?.query!==globalThis.__spbPending.messages.at(-1).text||params.arguments?.include_paint!==true))return fail(id,-32602,'Read fresh paint context with the exact current buyer query.');
        if(params.name==='spb_reply'&&!globalThis.__spbContextRead)return fail(id,-32602,'Read fresh current context before replying.');
        const live=await httpJson('GET','/api/mcp/conversation',null,15000);
        const check=globalThis.__spbVerify(globalThis.__spbPending,live.json);
        if(!check.ok)return fail(id,-32602,'Current message/document validation failed: '+check.reason);
        const out=await callTool(params.name,params.arguments);
        if(params.name==='spb_assistant_context'&&!out.isError)globalThis.__spbContextRead=true;
        return reply(id,out);
      }`);
globalThis.__spbPending=pending;
globalThis.__spbVerify=core.verify;
globalThis.__spbClaimedBatch=async read=>{
  const live=await read(),check=core.verify(pending,live.json);
  return check.ok?{status:200,json:{ok:true,messages:check.messages}}:{status:409,json:{ok:false,message:'Claimed message recovery stopped: '+check.reason}};
};
const filename=path.resolve(__dirname,'../server/index.js');
const mod=new Module(filename,module);mod.filename=filename;mod.paths=Module._nodeModulePaths(path.dirname(filename));
mod._compile(changed,filename);
