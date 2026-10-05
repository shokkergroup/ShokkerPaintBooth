// Actual direct-ask routing with the real offline helper; no provider or browser required.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
function slice(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, 'production function boundaries exist');
  return source.slice(a, b);
}
const w = { console, Promise, document: {}, _busy: false, _skipParts: true, CAR: null,
  E: null, D: null, START_OVER_RE: /^start over$/i, CHECK_AGAIN_RE: /^check again$/i,
  SH_FIRST_RE: /^(?:why|nothing happened|i am stuck)/i,
  elemOwnsText: () => false, supportClass: () => null, advisorIntent: () => null,
  offlineFirst: () => true, offlineCanHandle: () => false,
  elementRunCurrent: () => true, elementPaintChangedResult: () => ({ cancelled: true }),
  configured: false, parsed: 0, provider: 0 };
w.window = w; vm.createContext(w);
for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
}
const state = { paint: 'psd', layers: [{ id: 'n', name: 'Numbers', role: 'numbers' }],
  zones: [{ i: 0, name: 'Body', base: 'gloss', colourMode: 'source' }],
  selected: 0, carMap: { known: true, missing: [] }, mode: 'pro', last: null };
const handle = w.SpbSelfHelp.handle;
w.SpbSelfHelp.handle = q => handle(q, state);
w.SpbAiLease = { internal: () => true };
w.AI = { cached: () => ({ configured: w.configured }) };
w.offlineAsk = () => { w.parsed++; return Promise.resolve({ queue: ['would mutate'], calls: 0 }); };
w.askCore = () => { w.provider++; return Promise.resolve({ queue: [], calls: 1 }); };
vm.runInContext(slice('function selfHelpClaim(text)', 'function selfHelpResult(r)') +
  slice('function selfHelpResult(r)', 'function selfHelpSig()') +
  slice('function ask(text, o)', '// ---- what colours'), w);

(async () => {
  const questions = [
    'What does it mean when a paint is flattened instead of layered?',
    'Can you explain how I make chrome without wiping out my paint colours?',
    'How do I save my work?', 'How do I hide a layer?', 'What is a spec map?',
    'How do I add a logo?', 'How do I teach the app where the numbers are?',
    'How do I make a gradient?', 'How do I change zone priority?',
    'How do I turn on the tutorial?', 'Where is the render button?',
    'How do I switch to Pro mode?'
  ];
  let claimed = 0;
  for (const configured of [false, true]) {
    w.configured = configured;
    for (const q of questions) {
      const help = w.selfHelpClaim(q);
      if (!help) continue;
      claimed++;
      const before = [w.parsed, w.provider];
      const result = await w.ask(q, {});
      assert.equal(result.howto, true, q);
      assert.equal(result.selfHelp.topic, help.topic, q);
      assert.equal(result.queue.length, 0, q + ' has no mutation plan');
      assert.equal(result.calls, 0, q + ' costs no provider call');
      assert.deepEqual([w.parsed, w.provider], before, q + ' bypasses design parsing');
    }
  }
  assert(claimed >= 20, 'nonempty real helper coverage');
  w.configured = false;
  for (const q of ['Make the numbers white', 'Make the hood chrome', 'Show me chrome finishes']) {
    const before = w.parsed;
    await w.ask(q, {});
    assert.equal(w.parsed, before + 1, q + ' remains a command');
  }
  for (const opts of [{ forceAI: true }, { image: 'attached' }, { reference: 'attached' }]) {
    const before = w.provider;
    await w.ask(questions[0], opts);
    assert.equal(w.provider, before + 1, 'explicit provider/image request keeps its route');
  }
  w.elementRunCurrent = () => false;
  assert.equal((await w.ask(questions[0], { elementRunIdentity: {} })).cancelled, true);
  w.elementRunCurrent = () => true;
  w._busy = true;
  assert.match((await w.ask(questions[0], {})).error.message, /Still working/);
  w._busy = false; w.SpbAiLease.internal = () => false;
  assert.match((await w.ask(questions[0], {})).error.message, /external AI/);
  console.log('PASS direct help routing: ' + claimed + ' real helper claims, commands, overrides and ownership guards');
})().catch(e => { console.error(e); process.exitCode = 1; });
