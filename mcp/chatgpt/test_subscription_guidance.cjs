'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const w={localStorage:{getItem(){throw Error('Setup guidance must not inspect credentials');}},document:{}};w.window=w;
vm.createContext(w);vm.runInContext(fs.readFileSync(path.join(__dirname,'editor-capabilities.js'),'utf8'),w);
for(const q of ['Do I need a ChatGPT subscription or API credits to use Offline Helper?','How do I connect ChatGPT using my existing plan?','Can I use Codex without API billing?','What happens when my ChatGPT allowance runs out?','Does Offline Helper work without internet?','Can I use a banked reset for ChatGPT?']){
 const r=w.SpbEditorCapabilities.answer(q);assert.equal(r.cls,'ANSWER');assert.equal(r.answer.id,'assistant.subscription_connection');assert.equal(r.answer.live_context,false);assert.equal(r.answer.actions.length,0);
 assert.match(r.answer.text,/without an AI subscription/);assert.match(r.answer.text,/API-key sign-in uses separate API billing/);assert.match(r.answer.text,/does not prove/);assert.match(r.answer.text,/cannot inspect account allowance/);assert.equal(r.answer.sources[0].url,'https://learn.chatgpt.com/docs/auth');
}
for(const q of ['Can you connect ChatGPT to my subscription?','Can you use my ChatGPT banked reset?','How do I connect ChatGPT? Then connect it for me.','How does my ChatGPT subscription work and paint the body red?','Can you apply this finish using my ChatGPT plan?'])assert.equal(w.SpbEditorCapabilities.answer(q),null,q);
assert.equal(w.SpbEditorCapabilities.answer('Can I make the sponsor look like an old telephone?'),null);
console.log('PASS factual Offline subscription guidance: no credentials/account claims/actions, no mixed-request shortcut, qualified billing/listening/limits and existing-plan setup.');
