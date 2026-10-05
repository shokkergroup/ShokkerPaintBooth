'use strict';
// W120 oracle is frozen in _easy_claude_work/ai14h_mcp_bridge_review/fresh-oracle.json.
// Uses the pinned Runtime12 dispatcher and in-memory HTTP adapter; no MCP process,
// backend, browser, native app, provider, customer source, or paint apply is used.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'), runtime=path.join(root,'_easy_claude_work/ai14h_generation3_runtime12');
const files={
 ai:path.join(runtime,'js/spb-pro-ai.js'), bridge:path.join(root,'js/spb-mcp-bridge.js'),
 server:path.join(root,'mcp/server/index.js'), tools:path.join(root,'mcp/server/tools.json'),
 route:path.join(root,'server_routes/mcp_bridge_routes.py'), operation:path.join(runtime,'js/spb-ai-operation.js'),
 lease:path.join(runtime,'js/spb-ai-lease.js')
};
const pins={
 ai:'FB63F5906E1C9FC9D49150F571D64FDE640E0A4630319C418FE4F9C2E7E5413A',
 bridge:'687A34025D594DF81EF0A2B95BCA4FAC567B48B646B6653008D0CEBAA75848E6',
 server:'3937E7D63FC0E1F40DFED7988F6ED0520DA2F840405849D1B05A18A01C736860', tools:'E6D52D6824D526536CDDBB67DE980C99531A6FD14D3E7712DB2D6D2AC6A103D2', route:'B1B469DB429D4F65F36023E4D0AA8F5DF44C9119561D9F1A845BAE50FBBB4E69',
 operation:'47587A1A53A35CE7E58825BAC864BD75C2421D26C19791957F57BB199A7000C6',
 lease:'DE276372A763310EC051DB141F C B1D601E11DBF193843E2B21A405226F782134'.replace(/ /g,'')
};
function hash(b){return crypto.createHash('sha256').update(b).digest('hex').toUpperCase();}
for(const [k,p] of Object.entries(files)){const h=hash(fs.readFileSync(p));if(pins[k])assert.equal(h,pins[k],`${k} frozen bytes`);else pins[k]=h;}
const oracle=JSON.parse(fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_mcp_bridge_review/fresh-oracle.json'),'utf8'));
assert.equal(oracle.cases.length,15);
function extract(src,name){
 let start=src.indexOf(`async function ${name}(`);if(start<0)start=src.indexOf(`function ${name}(`);assert(start>=0,`actual ${name}`);const brace=src.indexOf('{',start);let d=0,q=null,line=false,block=false,esc=false;
 for(let i=brace;i<src.length;i++){const c=src[i],n=src[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc){esc=false;continue;}if(c==='\\'){esc=true;continue;}if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')d++;if(c==='}'&&--d===0)return src.slice(start,i+1);}
 throw Error('unterminated '+name);
}
const ai=fs.readFileSync(files.ai,'utf8'), operation=fs.readFileSync(files.operation,'utf8'), lease=fs.readFileSync(files.lease,'utf8');
const server=fs.readFileSync(files.server,'utf8');
function makeWorld(){
 const w={console,Promise,Date,Math,JSON,Object,Array,String,Number,RegExp,Error,AbortController,document:{getElementById:id=>id==='paintCanvas'?w.paintCanvas:null},paintCanvas:{width:2048,height:2048},_psdLayers:[],_spbLayerRev:1,_busy:false,_ctl:null,_progress:'',_log:[],_serial:0,_envMemo:null,_orig:null,_last:null,_reqText:'',_specOnlyReq:false,_editReg:{},_editRegPendingBefore:{},_editRegSig:'car',_skipParts:true,_absent:{},_extra:{cost:0,calls:0,models:{}},_offlineLast:null,_advLast:null,_activeId:null,_noCheck:false,_elemRunIdentity:null,_layerUndoStack:[],writes:[],sourceGeneration:2,sourcePath:'A.psd',fingerprint:'file-sha256:A',revisionHash:'zones-A',
  zones:[{id:'roof-1',name:'Roof base',color:'#204060',finish:'base::f_soft_gloss',region:{part:'roof'},muted:false}],
  layerList:[{id:'paint-layer',name:'Car Paint',visible:true,locked:false,opacity:255,blendMode:'source-over',img:{}}]};w.window=w;
 w.SPBSourceLoadTransaction={getGeneration:()=>w.sourceGeneration,getCommittedGeneration:()=>w.sourceGeneration,getCommittedPath:()=>w.sourcePath,getCommittedFingerprint:()=>w.fingerprint,isLoading:()=>false,isCommitted:()=>true};
 w.getZoneConfigHash=()=>w.revisionHash;w._getZoneConfigHashUncached=()=>w.revisionHash;w.SpbAiOperation=require('../js/spb-ai-operation.js');
 w.index=()=>[];w.specProps=()=>({});w.layersInfo=()=>w.layerList.map(l=>({name:l.name,locked:!!l.locked,hidden:l.visible===false}));
 w.zonesForModel=()=>JSON.parse(JSON.stringify(w.zones));w.state=()=>({paint_colours:[{hex:'#204060',cells:1}],layers:w.layersInfo()});w.MEM_KEY='';
 w.Z={zonesForModel:w.zonesForModel,validate:()=>({errors:[]}),probeRegion:()=>({share_pct:20}),catchAll:()=>null,findLayer:n=>w.layerList.find(l=>l.name===n||l.id===n)||null,quiet:fn=>fn(),whenSettled:()=>Promise.resolve(),previewImage:()=>null,specPreviewImage:()=>null};
 w.CAR=null;w.D={summarise:()=>[],COLOURS:{}};w.NLU={};w.AI={cached:()=>({configured:false})};w.K={search:()=>({results:[]})};w.window.SpbMcpBridge={stats:()=>({enabled:true})};w.SpbMcpBridge=w.window.SpbMcpBridge;
 w.normaliseSpec=a=>{const o={};for(const k of ['name','color','colour','finish','region','gradient','pattern','spec_patterns','second_base','strength','spec_shift','muted','priority','opacity','blend','visible'])if(a[k]!==undefined)o[k]=a[k];if(o.colour!==undefined&&!o.color)o.color=o.colour;return o;};
 w.strip=a=>{const o={...a};for(const k of ['zone','zone_id','zone_name','expect_name','_spbPartRegKey','_spbPartOwnerName','_spbPartForgetKey','_spbScopedPartProof'])delete o[k];return o;};
 w.keepOwnColour=()=>{};w.specOnlyGuard=()=>null;w.partScopeGuard=()=>null;w.protectDecals=()=>null;w.hasSelector=r=>!!(r&&(r.part||r.island||r.layers||r.remaining));w.wantsDecalsToo=()=>false;w.bodyLayerNames=()=>['Car Paint'];w.scopedPartProofAt=()=>null;w.scopedPartProofMatches=()=>false;w.partOwnerCurrent=()=>false;
 w.editKey=()=>'';w.kitGuard=()=>null;w.catchAllGuard=()=>null;w._spbPartMemory=null;w.render=()=>{};w.undoDepth=()=>w.writes.length;w.undoSeal=()=>{};w.undoTrim=()=>{};w.rshotWatch=()=>{};w.diagnose=()=>[];w.mcpImages=()=>[];w.zoneColourProblems=()=>Promise.resolve([]);w.previewPalette=()=>Promise.resolve({});
 w.applyQueue=(q,label)=>{w.writes.push({generation:w.sourceGeneration,path:w.sourcePath,queue:JSON.parse(JSON.stringify(q)),label});w._spbLayerRev++;w.revisionHash+='!';return{lines:q.map((_,i)=>'applied '+i),failed:[],results:[],maskUndo:[],layerUndo:0,undoSnap:{before:1,after:2},partRegUndo:null};};
 w._layerUndoStack=[];w.toggleLayerVisible=()=>{};w.setLayerOpacity=()=>{};w.setLayerBlendMode=()=>{};w.lsGet=()=>null;w.lsSet=()=>{};w.memAdd=()=>true;w.memClear=()=>{};w.finish=()=>{};w.operationRefreshDocument=()=>{};w.SpbMcpBridge=w.window.SpbMcpBridge;
 vm.createContext(w);
 vm.runInContext(operation,w,{filename:'runtime12 operation module'});vm.runInContext(lease,w,{filename:'runtime12 lease module'});
 vm.runInContext('var _aiOperation=null,_operationRevisionFailureSerial=0;',w);
 const names=['operationDocument','operationRevision','operationManager','operationStart','operationCurrent','operationTicket','operationBind','operationRelease','operationPublish','operationTools','makeTools','mcpApply','mcpCall','mcpCallCore'];
 for(const name of names)vm.runInContext(extract(ai,name),w,{filename:'runtime12#'+name});
 // Exact production write classification; the source declares this adjacent to mcpApply.
 const mw=ai.match(/var MCP_WRITE\s*=\s*(\{[^;]+\});/);assert(mw,'MCP_WRITE declaration');w.MCP_WRITE=vm.runInContext('('+mw[1]+')',w);
 w.SpbAiLease.release();
 return w;
}
const rows=[], findings=[];function pass(id,detail={}){rows.push({id,status:'PASS',...detail});}
function refusal(id,result){assert.equal(result.ok,false);pass(id,{error:result.error});}
async function run(){
 const w=makeWorld();
 // Actual page dispatcher exposes the data-driven schema list. The bundled MCP server's aliases are checked separately below.
 const listed=await w.mcpCall('list_tools',{});assert.equal(listed.ok,true,JSON.stringify(listed));const appTools=listed.result.tools;assert(appTools.length>=15);pass('actual-page-list-tools',{count:appTools.length});
 // The real page bridge owns async completion and translates errors into a
 // single post. Execute its actual handler with an in-memory post sink.
 const bridgeSrc=fs.readFileSync(files.bridge,'utf8'), bridgeFn=extract(bridgeSrc,'handle'), posted=[], bridge={window:{spbProAI:{mcpCall:(tool,args)=>w.mcpCall(tool,args)}},Promise,stats:{calls:0,lastTool:'',connected:false},enabled:true,emit(){},post(id,res){posted.push({id,res});return Promise.resolve();}};
 vm.createContext(bridge);vm.runInContext(bridgeFn,bridge,{filename:'actual page bridge handle'});await bridge.handle({id:'review-1',tool:'get_help',args:{query:'How do I save this project?'}});assert.equal(posted.length,1);assert.equal(posted[0].id,'review-1');assert.equal(posted[0].res.ok,true);assert.equal(w.writes.length,0);pass('actual-page-bridge-posts-readonly-result-once');
 let r=await w.mcpCall('edit_zone',{zone_id:'absent',color:'#aa0000'});refusal('unknown-stable-zone-id',r);assert.equal(w.writes.length,0);
 w.zones.push({...w.zones[0],name:'duplicate roof',id:'roof-1'});r=await w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#aa0000'});refusal('duplicate-stable-id-refuses-ambiguity',r);assert.equal(w.writes.length,0);w.zones.pop();
 w.zones.push({...w.zones[0],name:'Roof base',id:'roof-2'});r=await w.mcpCall('edit_zone',{zone_name:'Roof base',color:'#aa0000'});refusal('duplicate-zone-name-refuses-ambiguity',r);assert.equal(w.writes.length,0);w.zones.pop();
 r=await w.mcpCall('edit_zone',{zone:0,expect_name:'Some other zone',color:'#aa0000'});refusal('stale-index-name-guard',r);assert.equal(w.writes.length,0);
 r=await w.mcpCall('edit_zone',{zone_id:'roof-1',expect_name:'Roof base',color:'#aa0000'});assert.equal(r.ok,true);assert.deepEqual(w.writes.at(-1).queue[0].spec.color,'#aa0000');assert.equal(r.result.applied.length,1);pass('valid-current-id-queues-applies-and-receipts',{applied:r.result.applied.length});
 const nBefore=w.writes.length;w.layerList[0].locked=true;r=await w.mcpCall('edit_layer',{layer:'Car Paint',visible:false});refusal('locked-layer-rejected',r);assert.equal(w.writes.length,nBefore);w.layerList[0].locked=false;
 // Frozen oracle requires hidden layers not to be edited. Test actual behavior,
 // retaining this as a finding if exact-name dispatch still queues the edit.
 w.layerList[0].visible=false;const beforeHidden=w.writes.length;r=await w.mcpCall('edit_layer',{layer:'Car Paint',opacity:80});w.layerList[0].visible=true;
 if(r.ok&&w.writes.length>beforeHidden){const actualLayer=w.writes.at(-1).queue[0].layer;findings.push({id:'hidden-layer-explicit-target-is-editable',severity:'P2',observedLayer:actualLayer,expected:'reject or ask; no write'});rows.push({id:'hidden-layer-target-safety',status:'FAIL',observed:'explicitly named hidden layer queued',queuedLayer:actualLayer});}else pass('hidden-layer-target-safety',{refused:!r.ok});
 const before=w.writes.length;const stale=w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#bb0000'});w.sourceGeneration++;w.fingerprint='file-sha256:B';r=await stale;refusal('source-replaced-before-dispatch',r);assert.equal(w.writes.length,before);w.sourceGeneration++;w.fingerprint='file-sha256:C';
 const samePath=w.sourcePath, samePathWrites=w.writes.length, samePathCall=w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#bc0000'});w.fingerprint='file-sha256:replacement-at-same-path';r=await samePathCall;refusal('same-path-replaced-bytes-before-apply',r);assert.equal(w.sourcePath,samePath);assert.equal(w.writes.length,samePathWrites);w.fingerprint='file-sha256:C';
 // Mutate committed source inside actual validation, after ticket start but during handler publication.
 const valid=w.Z.validate;w.Z.validate=()=>{w.sourceGeneration++;w.fingerprint='file-sha256:D';return{errors:[]};};const beforeRace=w.writes.length;r=await w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#cc0000'});refusal('source-changed-during-handler-before-apply',r);assert.equal(w.writes.length,beforeRace);w.Z.validate=valid;w.sourceGeneration++;w.fingerprint='file-sha256:E';
 // A caller-provided stale owner proof cannot survive current proof revalidation.
 r=await w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#dd0000',_spbPartRegKey:'roof',_spbPartOwnerName:'Roof base',_spbScopedPartProof:{id:'roof-1',key:'roof',name:'Roof base',part:'roof'}});refusal('stale-scoped-owner-proof',r);assert.equal(w.writes.length,beforeRace);
 // Empty/missing read-only help is informational and cannot apply.
 r=await w.mcpCall('get_help',{query:'How do I save this project?'});assert.equal(r.ok,true);assert.equal(w.writes.length,beforeRace);pass('manual-guidance-is-read-only',{writeCount:w.writes.length});
 // A preview is labeled as preview and does not create an applied receipt.
 r=await w.mcpCall('preview',{parts:false});assert.equal(r.ok,true);assert.equal(w.writes.length,beforeRace);pass('preview-no-apply',{images:(r.images||[]).length});
 // A native dispatch response reports applied only from actual applyQueue return lines.
 w.applyQueue=()=>({lines:[],failed:['Roof base: test failure'],results:[],maskUndo:[],layerUndo:0});r=await w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#ee0000'});assert.equal(r.ok,true);assert.equal(r.result.applied.length,0);assert.equal(r.result.failed.length,1);pass('partial-or-failed-application-is-explicit',{applied:r.result.applied.length,failed:r.result.failed.length});
 // Disable during a queued action is checked before apply.
 w.applyQueue=(q)=>{w.writes.push({queue:q});return{lines:['applied'],failed:[],results:[],maskUndo:[],layerUndo:0,undoSnap:{}};};const oldStats=w.SpbMcpBridge.stats;w.SpbMcpBridge.stats=()=>({enabled:false});const beforeOff=w.writes.length;r=await w.mcpCall('edit_zone',{zone_id:'roof-1',color:'#ef0000'});assert.equal(r.ok,false);assert.equal(w.writes.length,beforeOff);pass('bridge-disabled-before-apply',{error:r.error});w.SpbMcpBridge.stats=oldStats;
 // Schema-to-dispatch binding uses the actual bundled MCP server's alias and function body.
 const idx=fs.readFileSync(files.server,'utf8'), indexPrefix=idx.slice(0,idx.indexOf('function allTools()'))+extract(idx,'allTools');
 const external={require,console,process,__dirname:path.dirname(files.server),setTimeout,URL,Buffer};vm.createContext(external);vm.runInContext(indexPrefix,external,{filename:'actual mcp/server/index prefix'});
 external.BLIND_TOOLS=new Set();external.isBlindClient=()=>false;external.toContent=({result})=>[{type:'text',text:JSON.stringify(result)}];external.timeoutFor=()=>120;external.friendly=r=>String(r.json&&r.json.error||'error');
 external.httpJson=async(method,url,body)=>({status:200,json:await w.mcpCall(body.tool,body.args)});
 vm.runInContext(extract(idx,'callTool'),external,{filename:'actual MCP callTool'});
 const publicTools=external.allTools();const map=vm.runInContext('NAME_MAP',external);assert(publicTools.every(t=>!!map[t.name]),'advertised schema has executable name mapping');
 const schemaEdit=publicTools.find(t=>t.name==='spb_edit_zone');assert(schemaEdit&&schemaEdit.inputSchema.properties.zone_id,'stable zone_id is advertised');
 const oldGen=w.sourceGeneration;w.sourceGeneration++;w.fingerprint='file-sha256:F';const publicResult=await external.callTool('spb_edit_zone',{zone_id:'nope',color:'#123456'});assert.equal(publicResult.isError,true);assert.equal(w.writes.length,beforeRace);w.sourceGeneration=oldGen;pass('bundled-mcp-alias-dispatches-and-refuses-invalid-target',{advertised:publicTools.length,appTool:map.spb_edit_zone});
 // Data inventory for cross-layer schema completeness.
 const stored=JSON.parse(fs.readFileSync(files.tools,'utf8'));const storedNames=new Set(stored.map(t=>t.name));const runtimeNames=new Set(appTools.map(t=>t.name));const absent=[...runtimeNames].filter(n=>!storedNames.has(n)&&!['spb_status','spb_get_zones','spb_preview','spb_request_parts','spb_undo'].includes(n));
 function stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])]));return v;}
 const aliasSrc=ai.match(/var MAPT\s*=\s*(\{[^;]+?\}),\s*lt\s*=\s*\[\]/);assert(aliasSrc,'actual MCP schema alias map');const aliases=vm.runInContext('('+aliasSrc[1]+')',w);const schemaMismatches=[];for(const t of appTools){const ext=t.name;if(!Object.values(aliases).includes(ext))continue;const bundled=stored.find(x=>x.name===ext),pageRequired=(t.inputSchema.required||[]).slice().sort(),bundleRequired=((bundled&&bundled.inputSchema.required)||[]).slice().sort(),pageProperties=Object.keys(t.inputSchema.properties||{}).sort(),bundleProperties=Object.keys(bundled&&bundled.inputSchema.properties||{}).sort();if(!bundled||JSON.stringify(stable(t.inputSchema))!==JSON.stringify(stable(bundled.inputSchema)))schemaMismatches.push({name:ext,pageRequired,bundleRequired,pageProperties,bundleProperties});}
 pass('runtime-list-schema-vs-bundled-tools-json',{runtimeNames:runtimeNames.size,storedNames:storedNames.size,generatedNamesMissingFromBundle:absent,inputSchemaMismatches:schemaMismatches});
 if(schemaMismatches.some(x=>['spb_edit_zone','spb_add_zone','spb_duplicate_zone'].includes(x.name)))findings.push({id:'runtime-page-write-schemas-omit-payloads',severity:'P2',tools:schemaMismatches.filter(x=>['spb_edit_zone','spb_add_zone','spb_duplicate_zone'].includes(x.name)).map(x=>x.name),expected:'page tool schemas and bundled MCP schemas expose the same write payload'});
 const writes=publicTools.filter(t=>!t.annotations.readOnlyHint);const unsafeHints=writes.filter(t=>t.annotations.destructiveHint===false);pass('mcp-annotations-inventory',{writeTools:writes.length,writeToolsIncorrectlyMarkedNondestructive:unsafeHints.map(t=>t.name)});
 if(unsafeHints.length)findings.push({id:'mutating-tools-advertised-nondestructive',severity:'P2',tools:unsafeHints.map(t=>t.name),expected:'mutating/state-changing tools are not marked destructiveHint=false'});
 return {rows,findings};
}
run().then(({rows,findings})=>{console.log(JSON.stringify({status:findings.length?'REVIEW_FINDINGS':'PASS_WITH_LIMITS',oracleHash:hash(fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_mcp_bridge_review/fresh-oracle.json'))),sourcePins:pins,caseCount:oracle.cases.length,executed:rows.length,rows,findings,customerFilesTouched:false,providers:0,nativeCalls:0},null,2));}).catch(e=>{console.error(e.stack||e);process.exitCode=1;});
