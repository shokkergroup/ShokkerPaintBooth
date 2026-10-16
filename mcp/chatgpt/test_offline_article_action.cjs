'use strict';
// Exercise the real answer-card -> builder boundary, without renderer or DOM writes.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const source=process.argv.includes('--baseline')?path.join(root,'js'):path.join(__dirname,'candidates');
const questions=[
  'How do I make the hood chrome without changing the colours?',
  'How can I make only the roof satin?',
  'How do I make everything chrome except the hood?',
  'What is chrome?',
];
let passed=0,failed=0;
for(const question of questions){
  const w={setTimeout(){},setInterval(){},console,document:{createElement(){return{}},querySelector(){return null},getElementById(){return null}}};
  w.window=w;vm.createContext(w);
  for(const name of ['spb-offline-builder.js','spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(source,name),'utf8'),w,{filename:name});
  const B=w.SpbOfflineBuilder,A=w.SpbOfflineAnswer;
  const s=B.state();s.text=question;s.answer={answer:{actions:[{do:'finish',id:'base::f_chrome',label:'Chrome'}]}};
  // Prior builder work must not silently become this question's target either.
  if(question.includes('roof'))s.steps.push(B.newStep({what:{k:'body'},act:'finish'}));
  try{
    assert.equal(A.onAction('adoit',{getAttribute(){return'0'}},s),true);
    const step=s.steps.at(-1);
    assert.equal(step.what,null,'question action must require an explicit target');
    assert.ok(step.note.includes(question),'keep the buyer question visible');
    const result=B.toPlan(s.steps,question);
    assert.equal(result.ok,false,'Run must be blocked before target selection');
    assert.ok(result.problems.some(p=>p.includes('WHAT')),'explain the missing target');
    passed++;console.log('PASS '+question);
  }catch(e){failed++;console.log('FAIL '+question+': '+e.message);}
}
console.log(`Offline article action: ${passed}/${questions.length} pass`);
process.exitCode=failed?1:0;
