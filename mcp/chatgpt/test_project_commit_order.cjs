'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
async function run(file,expectEarlyAbort){
 const source=fs.readFileSync(path.join(root,file),'utf8');
 const start=source.indexOf('    async function _saveProjectEnvelope('),end=source.indexOf('    async function saveSpbProject()',start);
 assert.ok(start>=0&&end>start);
 const events=[];let live=true,release,startedResolve;const started=new Promise(r=>startedResolve=r);
 const w={Blob,JSON,encodeURIComponent,API:'/api/projects',INLINE_SAVE_BYTES:0,DEFAULT_CHUNK_BYTES:1000000,_jsonHeaders:()=>({}),_toast(){},
 _fetchJson:async url=>{if(url.endsWith('/start'))return {out:{ok:true,uploadId:'owned',chunkBytes:1000000}};if(url.includes('/chunk/'))return {out:{ok:true}};if(url.includes('/commit/')){events.push('commit-start');startedResolve();return new Promise(r=>{release=()=>{events.push('commit-finish');r({out:live?{ok:true}:{error:'upload_not_found'}});};});}throw Error(url);},
 fetch:async()=>{events.push('abort');live=false;return {};}};
 vm.createContext(w);vm.runInContext(source.slice(start,end),w);
 const result=w._saveProjectEnvelope('test',{hello:'world'});await started;await new Promise(r=>setImmediate(r));
 assert.equal(events.includes('abort'),expectEarlyAbort);
 release();const value=await result;
 assert.equal(value.out.ok===true,!expectEarlyAbort);assert.equal(events.at(-1),expectEarlyAbort?'commit-finish':'abort');
 return events;
}
(async()=>{const original=await run('js/features/spb-projects.js',true),candidate=await run('mcp/chatgpt/candidates/spb-projects.js',false);console.log(JSON.stringify({pass:true,actual_save_function:true,original,candidate}));})().catch(e=>{console.error(e);process.exitCode=1});
