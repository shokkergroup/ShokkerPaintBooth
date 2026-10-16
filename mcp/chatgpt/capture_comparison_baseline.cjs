'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const out=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910'),bundle=path.join(out,'template-download-native-bundle');
const w={console};w.window=w;vm.createContext(w);
for(const file of ['core.js','offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(bundle,file),'utf8'),w,{filename:'historical/'+file});
const articles=JSON.parse(fs.readFileSync(path.join(bundle,'cars.json'),'utf8')).articles;
w.SpbCarReferenceAnswer.index(articles);
const query='Do Mini Stock and Dirt Mini Stock share the same template?',selection=w.SpbCarKnowledge.select({cars:articles.filter(a=>a.car_reference).map(a=>a.car_reference)},{query});
assert.deepEqual(Array.from(selection.matches,c=>c.id),['dirtministock']);
const answer=w.SpbCarReferenceAnswer.readOnlyQuestion(query);assert.ok(answer);
const result={checked_at:new Date().toISOString(),query,selection:{ids:Array.from(selection.matches,c=>c.id),definite:selection.definite,reason:selection.reason},answer:answer.answer,
 historical_sources:Object.fromEntries(['core.js','offline-answer.js','cars.json'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(bundle,n))).digest('hex')])),
 native:false,limits:['Component reproduction using exact archived originally measured sources; not a native before screenshot.']};
fs.writeFileSync(path.join(out,'comparison-identity-component-before.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({pass:true,historical_before_ids:result.selection.ids,native:false}));
