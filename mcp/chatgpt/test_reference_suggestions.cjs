'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const here=__dirname,src=n=>fs.readFileSync(path.join(here,'candidates',n),'utf8');
const K=require('./car-knowledge/core.js'),articles=require('./car-knowledge/build/cars.json').articles;
const DATA={cars:articles.filter(a=>a.car_reference).map(a=>a.car_reference)};
const generic={id:'cars.choosing_template',type:'article',title:'Choosing the right template for your car'};
const mini={id:'cars.reference.ministock',type:'article',title:'Mini Stock — template reference'};
const dirt={id:'cars.reference.dirtministock',type:'article',title:'Dirt Mini Stock — template reference'};
const raw=[dirt,mini,generic],original=JSON.stringify(raw);
const brain=src('spb-offline-answer.js'),a=brain.indexOf('    function filterReferenceArticles('),b=brain.indexOf('    var FW',a);
assert.ok(a>=0&&b>a);const W={SpbCarKnowledge:K},c={W,CAR_ARTICLE_DATA:DATA,CAR_ARTICLE_SCOPES:{'car_pages.mini-stock':'dirtministock'}};vm.createContext(c);vm.runInContext(brain.slice(a,b),c);
const pages=require('../../data/encyclopedia/car_pages.json').articles;
c.list=pages;vm.runInContext(brain.split('\n').find(line=>line.includes('CAR_ARTICLE_SCOPES = {}; list.forEach')),c);
assert.equal(c.CAR_ARTICLE_SCOPES['car_pages.mini-stock'],'dirtministock','Actual indexed legacy source folder');
const filter=(q,hits=raw)=>c.filterReferenceArticles(q,hits),ids=list=>Array.from(list,x=>x.id);
assert.deepEqual(ids(filter('Where can I download the Mini Stock template?')),[mini.id,generic.id]);
assert.deepEqual(ids(filter('Dirt Mini Stock template')),[dirt.id,generic.id]);
const legacy={id:'car_pages.mini-stock',type:'article',title:'Mini Stock: parts and folder',summary:'mini stock checked layout 7 named parts folder dirtministock'};
assert.deepEqual(ids(filter('Mini Stock template',[mini,legacy,generic])),[mini.id,generic.id],'Legacy page is dirt by its explicit folder, despite its title');
assert.deepEqual(ids(filter('Dirt Mini Stock template',[dirt,legacy,generic])),[dirt.id,legacy.id,generic.id]);
assert.deepEqual(ids(filter('Ferrari F999 template',[legacy,generic])),[generic.id]);
c.CAR_ARTICLE_SCOPES={};assert.deepEqual(ids(filter('Mini Stock template',[legacy,generic])),[generic.id],'PBN-only legacy explicit summary folder');
assert.deepEqual(ids(filter('Mini Stock vs Dirt Mini Stock')),ids(raw),'Comparison alternatives retained');
assert.deepEqual(ids(filter('What does roughness mean?')),ids(raw),'General guidance retains search behavior');
assert.deepEqual(ids(filter('Ferrari F999 template')),[generic.id],'Unknown model code never suggests a sibling reference');
for(const car of DATA.cars){
 const own={id:'cars.reference.'+car.id},wrong={id:'cars.reference.fictional'},hits=[wrong,own,generic];
 const picked=K.select(DATA,{query:car.paint_folder});
 if(picked.definite&&picked.matches.length===1)assert.deepEqual(ids(filter(car.paint_folder,hits)),[own.id,generic.id],car.id);
}
const mustang=[{id:'cars.reference.fordmustanggt4'},{id:'cars.reference.fordmustanggt3'},generic];
assert.deepEqual(ids(filter('Ford Mustang GT3 template',mustang)),['cars.reference.fordmustanggt3',generic.id]);
const bmw=[{id:'cars.reference.bmwm4evogt4'},{id:'cars.reference.bmwm4gt4'},generic];
assert.deepEqual(ids(filter('BMW M4 GT4',bmw)),ids(bmw),'Unqualified generation stays ambiguous');
assert.equal(JSON.stringify(raw),original,'No mutation');
W.SPB_REFERENCE_SUGGESTIONS_OFF=true;assert.equal(filter('Mini Stock template'),raw);W.SPB_REFERENCE_SUGGESTIONS_OFF=false;
c.CAR_ARTICLE_DATA={cars:[]};assert.equal(filter('Mini Stock template'),raw,'Cold index changes no identity');c.CAR_ARTICLE_DATA=DATA;
assert.deepEqual(ids(filter('Mini Stock template',[{id:'ideas.dirt'},generic])),['ideas.dirt',generic.id],'Non-reference ideas remain');

// Actual PBN caller: raw cache cannot preserve old unscoped picks after warm-up.
const pbn=src('spb-pbn.js'),pa=pbn.indexOf('    var ART_MEMO = {}'),pb=pbn.indexOf('    function showQuery(',pa);
let searches=0;c.W.SpbOfflineAnswer={filterReferenceArticles:(q,h)=>filter(q,h)};c.W.SpbEncyclopedia={search(){searches++;return raw;}};
vm.runInContext(pbn.slice(pa,pb),c);c.CAR_ARTICLE_DATA={cars:[]};assert.deepEqual(ids(c.articles('Mini Stock template',3)),ids(raw));
c.CAR_ARTICLE_DATA=DATA;assert.deepEqual(ids(c.articles('Mini Stock template',3)),[mini.id,generic.id]);assert.equal(searches,1,'Re-filter cache without new search');
assert.deepEqual(ids(c.articles('Mini Stock template',1)),[mini.id],'Wrong first hit filtered before limit');
for(let i=0;i<40;i++)c.articles('cache-bound-'+i,3);
assert.equal(Object.keys(c.ART_MEMO).length,1,'Forty-query bound resets raw search cache');
assert.ok(Object.values(c.ART_MEMO).every(h=>h.length<=30&&h.every(x=>String(x.summary).length<=110)));

// Actual connected encSearch caller: both cached and fetched results re-scope.
const editor=src('spb-pro-ai.js'),ea=editor.indexOf('    function scopedEncArticles('),eb=editor.indexOf('    function encFacts(',ea);
const ctx={window:{SpbOfflineAnswer:c.W.SpbOfflineAnswer},_encCache:{},Promise,setTimeout,clearTimeout,fetch:async()=>({ok:true,json:async()=>({ok:true,results:raw})})};
vm.createContext(ctx);vm.runInContext(editor.slice(ea,eb),ctx);
(async()=>{
 assert.deepEqual(ids(await ctx.encSearch('Mini Stock template',4)),[mini.id,generic.id]);
 c.CAR_ARTICLE_DATA={cars:[]};assert.deepEqual(ids(await ctx.encSearch('Mini Stock template',4)),ids(raw));
 c.CAR_ARTICLE_DATA=DATA;assert.deepEqual(ids(await ctx.encSearch('Mini Stock template',4)),[mini.id,generic.id]);
 console.log(JSON.stringify({pass:true,records:DATA.cars.length,actual_pbn_and_connected_callers:true,exact_and_ambiguous_identities:true,cache_rescoped_without_fetch:true,paint_actions:0}));
})().catch(e=>{console.error(e);process.exitCode=1;});
