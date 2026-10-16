'use strict';
// Replay the observed small-window geometry through the actual owner functions.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
function run(file,{band=139,saved=false,off=false}={}){
 const src=fs.readFileSync(path.resolve(__dirname,file),'utf8'), styles={},attrs={},boxes={header:{left:0,right:968,top:0,bottom:65,width:968,height:65},'#spbTopToolbar':{left:0,right:968,top:65,bottom:119,width:968,height:54},'#splitSource':{left:212,right:470,top:490,bottom:727,width:258,height:237},'#splitPreview':{left:485,right:735,top:490,bottom:727,width:250,height:237},'#canvasViewport':{left:203,right:735,top:200,bottom:735+band+8,width:532,height:600}};
 const doc={body:{classList:{contains:()=>false}},querySelector:s=>boxes[s]?{getBoundingClientRect:()=>boxes[s]}:null};
 const w={doc,localStorage:{getItem:key=>key==='spb_nuq_dock_user'&&saved?'1':null},SPB_NUQ_OFF:off,innerWidth:968,innerHeight:930,getComputedStyle:()=>({display:'block',visibility:'visible'})};w.window=w;vm.createContext(w);vm.runInContext("var UKEY='spb_nuq_dock_user';",w);
 for(const name of ['off','rect','savedGeom','inEditor','placeDock']){const start=src.indexOf('    function '+name+'('),end=src.indexOf('\n    function ',start+1);assert.ok(start>=0&&end>start);vm.runInContext(src.slice(start,end),w);}
 w.placeDock({hidden:false,style:{setProperty:(k,v)=>{styles[k]=v;}},setAttribute:(k,v)=>{attrs[k]=v;}});return {styles,attrs};
}
const original=run('../../js/ui/spb-nuq-fix.js');assert.equal(original.styles.height,'139px','Retain the native tiny-log reproduction');
const fixed=run('candidates/spb-nuq-fix.js');assert.equal(fixed.styles.width,'392px');assert.ok(parseInt(fixed.styles.height)>=360);assert.equal(fixed.styles.top,'127px','Drawer stays below toolbars');
assert.equal(run('candidates/spb-nuq-fix.js',{band:400}).styles.height,'400px','Keep free-band placement when it is actually readable');
assert.deepEqual(run('candidates/spb-nuq-fix.js',{saved:true}).styles,{},'Leave buyer-dragged placement untouched');assert.deepEqual(run('candidates/spb-nuq-fix.js',{off:true}).styles,{});
console.log('PASS actual dock: observed139px regression reproduced, readable drawer fallback, large free-band retained, user placement and kill switch preserved.');
