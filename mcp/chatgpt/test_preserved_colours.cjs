'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),w={console};w.window=w;vm.createContext(w);
for(const f of ['mcp/chatgpt/preserved-colours.js','js/spb-pro-design.js','mcp/chatgpt/candidates/spb-pro-edit.js','js/spb-encyclopedia-data.js','mcp/chatgpt/candidates/spb-offline-builder.js'])vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),w);
const E=w.SpbProEdit,B=w.SpbOfflineBuilder,env={palette:[{hex:'#19376e',share_pct:91},{hex:'#e6e6e6',share_pct:5},{hex:'#ffffff',share_pct:4}],layers:[],zoneColours:[]};
for(const text of ['Change the navy areas to red. Keep the off white and white marks unchanged.','Make blue gold; leave white alone.','Make navy red and keep white untouched.']){
 const p=E.plan(text,env);assert.equal(p.kind,'ops',text);assert.equal(p.ops.length,1,text);assert.ok(p.preserved_colour_words);assert.equal(p.raw,text);
 const r=B.fromText(text,env);assert.equal(r.steps.length,1,text);assert.equal(r.steps[0].what.k,'colour');assert.notEqual(r.steps[0].what.tg.word,'white');
}
const contradictory='Make white red. Keep white unchanged.';
assert.equal(E.plan(contradictory,env).prohibited_edit,true);const stopped=B.fromText(contradictory,env);assert.equal(stopped.steps.length,0);assert.match(stopped.blocked,/same colour/);
const negative=B.fromText('Do not paint the white red.',env);assert.equal(negative.steps.length,0);assert.ok(negative.blocked);
for(const text of ['Make blue red and white gold.','Keep the white pearl.','Make navy red. Keep white unchanged and make blue green.','Make the whole car red. Keep white unchanged.']){
 assert.ok(!E.plan(text,env)?.preserved_colour_words,'Only a complete, single-colour assignment with an understood preservation tail gets the repair: '+text);
}
console.log('PASS actual edit parser and builder: protection tail is retained verbatim, no false white edit, contradictory/negative commands cannot fall through to keyword steps; other command forms preserve their existing path');
