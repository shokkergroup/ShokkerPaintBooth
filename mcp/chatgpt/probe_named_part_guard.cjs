'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'_codex_mcp_work/chatgpt-dev/59910');
const child=spawn(process.execPath,[path.join(__dirname,'candidate-server.cjs')],{env:{...process.env,SPB_PORT:'59910',SPB_MCP_TOKEN_FILE:path.join(dir,'pairing/token.txt')},windowsHide:true,stdio:['pipe','pipe','pipe']});
let id=0,buffer='';const pending=new Map();
const timer=setTimeout(()=>{child.kill();console.error('Named-part MCP probe timed out');process.exitCode=1},55000);
child.stdout.setEncoding('utf8');child.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);let r;try{r=JSON.parse(line)}catch{continue}const resolve=pending.get(r.id);if(resolve){pending.delete(r.id);resolve(r)}}});
child.stderr.on('data',()=>{});
function rpc(method,params){return new Promise(resolve=>{const next=++id;pending.set(next,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:next,method,params})+'\n')})}
async function call(name,args){const r=await rpc('tools/call',{name,arguments:args});assert.ok(r.result&&!r.result.isError,JSON.stringify(r.error||r.result));return JSON.parse(r.result.content[0].text);}
const fields=['layers','zones','selected_zone','paint_colours','pending_changes','recent_changes','saved_design_brief','convo','template_identity'];
const select=s=>Object.fromEntries(fields.map(k=>[k,s[k]===undefined?null:s[k]]));
function fixtures(){const d=path.join(root,'_release_evidence/chatgpt-dev/59910/projects');const names=fs.readdirSync(d).filter(n=>n.endsWith('.spbproj')).sort();assert.equal(names.length,2);return names.map(name=>({name,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(d,name))).digest('hex')}));}
(async()=>{
 assert.ok((await rpc('initialize',{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'codex-named-part-preflight-probe',version:'1'}})).result);
 const listing=await rpc('tools/list',{});assert.match(listing.result.tools.find(t=>t.name==='spb_kit').description,/placement is withheld/);
 const before=select(await call('spb_get_state',{})),originals=fixtures();
 const requests=[
  ['spb_add_zone',{name:'preflight must not create',region:{part:'hood'},color:'#00ff00',buyer_said:'paint the hood green'}],
  ['spb_do',{text:'make both doors green',frame:{v:1,act:'change',ops:[{verb:'recolour',target:{kind:'part',parts:['both doors']},look:{colour:{hex:'#00ff00'}}}]}}],
  ['spb_kit',{kit:'sponsor',action:'place',parts:['hood'],logo_layer:'Car_Decal',buyer_said:'put my logo on the hood'}],
  ['spb_kit',{kit:'number',action:'place',number:'32',places:['both doors','roof'],buyer_said:'put number 32 on both doors and roof'}],
 ];
 const calls=[];for(const [tool,args]of requests){const result=await call(tool,args);assert.equal(result.changed,false);assert.equal(result.refused,true);assert.ok(result.reason==='part_geometry_unconfirmed'||result.reason==='kit_geometry_unverified');calls.push({tool,args,result});}
 const after=select(await call('spb_get_state',{}));assert.deepEqual(after,before);assert.deepEqual(fixtures(),originals);
 const checked_at=new Date().toISOString(),receipt='named-part-preflight-'+checked_at.replace(/[:.]/g,'-')+'.json';
 fs.writeFileSync(path.join(dir,receipt),JSON.stringify({checked_at,calls,before,after,fixtures:originals,limits:'Actual private app RPC refusal and exposed state preservation. No positive native taught target, pixel equality, installed model inference, atomic source-switch guard or shared adoption proof.'},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({receipt,refused_calls:calls.length,preserved_fields:fields.length,fixture_count:originals.length,limits:'native positive/atomic source-switch/downstream consumption open'}));
})().catch(e=>{console.error(e.message);process.exitCode=1}).finally(()=>{clearTimeout(timer);child.stdin.end();child.kill()});
