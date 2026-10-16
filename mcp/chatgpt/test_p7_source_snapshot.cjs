'use strict';
// Execute actual P7 snapshot/cache functions with controlled image data, not native renders.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
function load(file){
 let epoch=1,tier='';const pixels=v=>new Uint8ClampedArray(256*256*4).fill(v);
 const paint={complete:true,naturalWidth:256,src:'live-paint',px:pixels(11)},spec={complete:true,naturalWidth:256,src:'live-spec',px:pixels(22)};
 const w={console,Date,Promise,Uint8Array,Uint8ClampedArray,__spbPaintSig:'paint-1',__spbSpecSig:'spec-1',lastPreviewZoneHash:'preview-1',localStorage:{getItem:()=>tier},SpbConversationScope:{stamp:()=>epoch,current:s=>s===epoch},document:{addEventListener(){},getElementById:id=>id==='livePreviewImg'?paint:id==='livePreviewSpecImg'?spec:null,createElement:()=>{let drawn;return {getContext:()=>({drawImage:img=>drawn=img,getImageData:()=>({data:drawn.px.slice()})})};}}};
 w.window=w;vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w);
 return {w,R:w.SpbIntentReport,paint,spec,retire:()=>epoch++,off:()=>tier='1',full(){w.__spbFullPane={p:'full-paint',s:'full-spec'};paint.src='full-paint';spec.src='full-spec';paint.px=pixels(33);spec.px=pixels(44);}};
}
const old=load('js/spb-intent-report.js');assert.equal(old.R.snap().p[0],11);old.full();assert.equal(old.R.snap().p[0],11,'Source-owner P7 preserves the actual live baseline after a full pane');old.retire();assert.ok(old.R.snap(),'Original P7 cache survives into the next document');
const c=load('mcp/chatgpt/candidates/spb-intent-report.js');assert.equal(c.R.snap().documentStamp,1);c.full();const remembered=c.R.snap();assert.equal(remembered.p[0],11);assert.equal(remembered.s[0],22);assert.equal(remembered.p7,'last-live');assert.equal(remembered.documentStamp,1);c.retire();assert.equal(c.R.snap(),null,'A retired native baseline is never relabelled as current');
const reset=load('mcp/chatgpt/candidates/spb-intent-report.js');reset.R.snap();reset.full();reset.R._reset();assert.equal(reset.R.snap(),null,'Source reset drops full-pane cached ancestry');
const stale=load('mcp/chatgpt/candidates/spb-intent-report.js');stale.R.snap();stale.full();stale.w.__spbPaintSig='paint-2';stale.w.lastPreviewZoneHash='preview-2';assert.equal(stale.R.snap(),null,'Claude P7c still rejects a preview from before the latest paint edit');
const specStale=load('mcp/chatgpt/candidates/spb-intent-report.js');specStale.R.snap();specStale.full();specStale.w.__spbSpecSig='spec-2';const specOnly=specStale.R.snap();assert.equal(specOnly.p[0],11);assert.equal(specOnly.s,null,'P7c drops only the stale spec side');
const off=load('mcp/chatgpt/candidates/spb-intent-report.js');off.R.snap();off.full();off.off();const bypass=off.R.snap();assert.equal(bypass.p[0],33);assert.equal(bypass.documentStamp,1,'P7 diagnostic kill switch retains its source behaviour with a current stamp');
console.log(JSON.stringify({pass:true,source_owner_P7_preserved:true,original_retired_cache_reproduced:true,current_live_baseline_preserved:true,retired_cache_refused:true,source_reset_clears_cache:true,kill_switch_preserved:true,native:false}));
