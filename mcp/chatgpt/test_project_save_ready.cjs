'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
async function exercise(candidate,mode){
 const file=candidate?'mcp/chatgpt/candidates/spb-projects.js':'js/features/spb-projects.js';
 const source=fs.readFileSync(path.join(root,file),'utf8');
 const a=source.indexOf('    function buildProjectPayload('),b=source.indexOf('    async function _saveProjectEnvelope(',a);
 const c=source.indexOf('    async function saveSpbProject()'),d=source.indexOf('    // ------------------------------------------------------------------ load',c);
 assert.ok(a>=0&&b>a&&c>b&&d>c);
 const events=[],w={_spbPsdImportInFlight:mode==='pending',getConfig:()=>({sourcePaintFile:'car.psd'}),SPBProjectNameDialog:{open:async()=>{events.push('dialog');if(mode==='starts-during-dialog')w._spbPsdImportInFlight=true;return 'Test';}}};
 const ctx={window:w,document:{getElementById:()=>({width:2048,height:2048})},Set,Date,Array,SCHEMA_VERSION:2,_currentSource:()=> 'car.psd',_newProjectId:()=> 'test',_toast:t=>events.push(t),_serializeLayerState:()=>{events.push('capture');return {layers:[],errors:[]};},_revMaterialForSave(){},_revFadeForSave(){},_revWearForSave(){},_persistForSave(){},_saveProjectEnvelope:async(n,p)=>{events.push('upload:'+p.layers.length);return {res:{status:200},out:{ok:true,file:'test',bytes:1}};}};
 vm.createContext(ctx);vm.runInContext(source.slice(a,b)+source.slice(c,d),ctx);const saved=await ctx.saveSpbProject();return {saved,events};
}
(async()=>{
 const old=await exercise(false,'pending');assert.equal(old.saved,true);assert.ok(old.events.includes('upload:0'),'Original reproduces empty save during import');
 for(const mode of ['pending','starts-during-dialog']){const result=await exercise(true,mode);assert.equal(result.saved,false);assert.ok(!result.events.includes('capture'));assert.ok(result.events.some(e=>/still loading/.test(e)));if(mode==='pending')assert.ok(!result.events.includes('dialog'));}
 const ready=await exercise(true,'ready');assert.equal(ready.saved,true);assert.ok(ready.events.includes('upload:0'),'A legitimate flat paint may have zero layers');
 console.log('PASS actual Save functions: original imports save0layers; candidate refuses before dialog and capture after dialog, while ready flat paints remain saveable. Native pending-import UI proof separate.');
})().catch(e=>{console.error(e);process.exitCode=1;});
