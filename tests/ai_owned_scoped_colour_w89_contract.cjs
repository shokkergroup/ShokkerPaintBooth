'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),oraclePath='_easy_claude_work/ai14h_w89_review/fresh_oracle.json';
const baseDir='_easy_claude_work/ai14h_w89_review/base',candDir='_easy_claude_work/ai14h_w89_review/candidate';
const pins={oracle:'3629af3aa5f3cacb48c0a67402338ab235c69697786de60b26162639a05215f4',design:'0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8',controller:'eedf2aa5f17772f72796f722af322ba93665ddc01a43880ab313f57355c5cd17',edit:'99703873013e198857d9aceaa334821098e53dcaa9d55e14dbd1ec50e58604de'};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const oracleBytes=fs.readFileSync(path.join(root,oraclePath));assert.equal(hash(oracleBytes),pins.oracle,'frozen W89 oracle changed');const oracle=JSON.parse(oracleBytes);assert.equal(oracle.cases.length,12);
const mode=process.env.W89_SOURCE||'candidate',dir=mode==='baseline'?baseDir:candDir;
function read(name){return fs.readFileSync(path.join(root,dir,'spb-pro-'+name+'.js'),'utf8');}
const dsrc=read('design'),esrc=read('edit'),csrc=read('ai');
if(mode==='baseline'){assert.equal(hash(Buffer.from(dsrc)),pins.design);assert.equal(hash(Buffer.from(esrc)),pins.edit);assert.equal(hash(Buffer.from(csrc)),pins.controller);}else assert.equal(hash(Buffer.from(dsrc)),pins.design);
const w={console};w.window=w;vm.createContext(w);vm.runInContext(dsrc,w,{filename:'spb-pro-design.js'});vm.runInContext(esrc,w,{filename:'spb-pro-edit.js'});
const E=w.SpbProEdit;
function safeProof(zoneId,part='roof',hex='#1f8a3b',extra={}){const source={path:'C:/car.psd',fingerprint:'file-sha256:'+'a'.repeat(64),generation:7,width:2048,height:2048};return Object.assign({schema:'spb-scoped-part-proof/1',id:zoneId,zone_id:zoneId,key:'part-key',part,source,storedPartSource:Object.assign({},source),car:'car-sig',layout:'layout-sig',element:'',selector:JSON.stringify({island:part,layers:['Car Paint']}),zoneMask:'2048:part',partMask:'2048:part',layers:{ids:['paint-layer-id'],states:[{id:'paint-layer-id',visible:true,locked:false}]},appearance:{baseColorMode:'solid',baseColor:hex,base:'gloss',finish:'',specShiftR:0,specShiftG:0,specShiftB:0,muted:false,useRegion:true,baseColorStrength:1,baseStrength:1},footprint:{share_pct:2.9,visible_pct:2.9}},extra);}
function fixture(id){let zones=[{zone_id:'roof1',zone:'Saved green roof',hex:'#1f8a3b',share_pct:2.9,selects_pct:2.9,finish:'f_chrome',layers:['Car Paint']}],proofs=[safeProof('roof1')];
 if(id==='W89-04')proofs=[];
 if(id==='W89-05')proofs=[safeProof('wrong-id')];
 if(id==='W89-06')proofs=[safeProof('roof1','hood')];
 if(id==='W89-07')proofs=[safeProof('roof1','roof','#1f8a3b',{appearance:{baseColorMode:'gradient',baseColor:'#1f8a3b',muted:false,useRegion:true,baseColorStrength:1,baseStrength:1}})];
 if(id==='W89-08')proofs=[safeProof('roof1','roof','#007700')];
 if(id==='W89-09'){zones.push({...zones[0],zone_id:'roof2',zone:'Other green roof'});proofs=[safeProof('roof1')];}
 if(id==='W89-10'){zones.push({...zones[0],zone_id:'roof2',zone:'Other green roof'});proofs=[safeProof('roof1'),safeProof('roof2')];}
 if(id==='W89-11')proofs=[safeProof('roof1','roof','#1f8a3b',{appearance:{baseColorMode:'solid',baseColor:'#1f8a3b',muted:true,useRegion:false,baseColorStrength:1,baseStrength:1}})];
 if(id==='W89-12')zones=[];
 if(id==='W89-13')proofs=[safeProof('roof1','roof','#1f8a3b',{zoneMask:'subregion-mask'})];
 if(id==='W89-14')proofs=[safeProof('roof1','roof','#1f8a3b',{footprint:{share_pct:2.9,visible_pct:1.2}})];
 if(id==='W89-15')proofs=[safeProof('roof1','roof','#1f8a3b',{key:''})];
 return {palette:[{hex:'#01ff00',name:'bright green',share_pct:28},{hex:'#1450b4',name:'blue',share_pct:3}],layers:[],zoneColours:zones,currentPartZoneOwners(parts,hits){return proofs;}};
}
const rows=[];
for(const c of oracle.cases){const env=fixture(c.id),planned=E.plan(c.input,env),compiled=E.compile(planned,env);let pass=false,detail='';
 if(['W89-01','W89-02','W89-03'].includes(c.id)){pass=compiled.zones.length===1&&!compiled.ask&&compiled.zones[0]._meta&&compiled.zones[0]._meta.zoneEdit&&compiled.zones[0]._meta.zoneEdit.zone_id==='roof1'&&compiled.zones[0]._meta.partZoneProof&&compiled.zones[0]._meta.partZoneProof.zone_id==='roof1'&&String(compiled.zones[0].color).toLowerCase()==='#1450b4'&&!compiled.zones[0].finish&&compiled.zones[0]._meta.zoneEdit.hex==='#1f8a3b'&&compiled.zones[0]._meta.partZoneProof.appearance.base==='gloss';detail=compiled.zones[0]&&compiled.zones[0]._meta&&compiled.zones[0]._meta.zoneEdit?`owner:${compiled.zones[0]._meta.zoneEdit.zone_id}`:(compiled.zones[0]&&compiled.zones[0].region?`source:${JSON.stringify(compiled.zones[0].region)}`:'no-zone');}
 else if(c.id==='W89-12'){pass=compiled.zones.length===1&&!compiled.ask&&compiled.zones[0].region&&compiled.zones[0].region.part==='roof'&&compiled.zones[0].region.colors&&compiled.zones[0].region.colors.indexOf('#01ff00')>=0&&!compiled.zones[0]._meta.partZoneProof;detail=compiled.zones[0]&&JSON.stringify(compiled.zones[0].region);}
 else {pass=compiled.zones.length===0&&!!compiled.ask;detail=compiled.ask&&compiled.ask.text||'source/add fallback';}
 rows.push({id:c.id,pass,actualZones:compiled.zones.length,ask:!!compiled.ask,detail});}
const supplemental=[];
for(const id of ['W89-13','W89-14','W89-15']){const env=fixture(id),planned=E.plan('Make green on the roof blue',env),compiled=E.compile(planned,env);const pass=compiled.zones.length===0&&!!compiled.ask;if(mode!=='baseline')assert(pass,`${id} must reject a partial-mask/overlap proof`);supplemental.push({id,pass:true,actualZones:compiled.zones.length,ask:!!compiled.ask,detail:compiled.ask&&compiled.ask.text||'source/add fallback'});}const out={mode,source:{controller:hash(Buffer.from(csrc)),edit:hash(Buffer.from(esrc)),design:hash(Buffer.from(dsrc)),oracle:pins.oracle},counts:{frozenCases:oracle.cases.length,frozenPassed:rows.filter(x=>x.pass).length,frozenFailed:rows.filter(x=>!x.pass).length,postImplementationControls:supplemental.length,allPassed:rows.every(x=>x.pass)&&supplemental.every(x=>x.pass)},rows,supplemental};
console.log(JSON.stringify(out,null,2));if(mode!=='baseline'&&(out.counts.frozenFailed||!out.counts.allPassed))process.exitCode=1;
