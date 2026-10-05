const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.join(__dirname, '..');
const window = { console };
vm.createContext(window);
window.window = window;
window.document = {};
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), window, { filename: file });
}

const E = window.SpbProEdit;
const D = window.SpbProDesign;
const env = {
  palette: [
    { hex: '#141416', share_pct: 52 },
    { hex: '#f2c500', share_pct: 22 },
    { hex: '#f1f1ee', share_pct: 14 },
    { hex: '#1347a8', share_pct: 5 }
  ],
  layers: []
};

const mustClarify = [
  'Make the entire car teal metallic except the hood, leave that unchanged.',
  'Leave the hood carbon and turn only the roof bright gold.',
  'Make the whole car matte, excluding the roof.',
  'Turn the paint silver apart from the hood.',
  'Make everything teal without touching the hood.',
  'Change the base to gold but keep the hood carbon.',
  'Make everything teal but do not change the left side.',
  'Make the paint silver but do not touch the passenger door.',
  'Change the body to gold and keep the passenger door as it is.'
];

for (const text of mustClarify) {
  const planned = E.plan(text, env);
  assert(planned && planned.kind === 'ask', `expected a safety clarification for: ${text}`);
  assert(!planned.ops, `preservation clarification must not carry executable ops: ${text}`);
  assert(/can.t safely|safely combine|clarify the scope/i.test(planned.text), `clarification should explain the scope limit: ${text}`);
}

// Exercise the actual top-level offlineAsk implementation. Only application effects
// (queue/edit UI, catalogue warmup and reply rendering) are stubbed; D/E are real.
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, `could not find ${name} in the actual AI router`);
  const brace = source.indexOf('{', start);
  let depth = 0, quote = null, lineComment = false, blockComment = false, escaped = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (lineComment) { if (c === '\n') lineComment = false; continue; }
    if (blockComment) { if (c === '*' && n === '/') { blockComment = false; i++; } continue; }
    if (quote) {
      if (escaped) { escaped = false; continue; }
      if (c === '\\') { escaped = true; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === '/' && n === '/') { lineComment = true; i++; continue; }
    if (c === '/' && n === '*') { blockComment = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name} in the actual AI router`);
}

const called = { edit: 0, advisor: 0, core: 0 };
const routeContext = {
  window: Object.assign(window, { SpbProAdvisor: { answer() { called.advisor++; return null; } } }),
  console,
  D,
  E,
  START_OVER_RE: /^\s*(?:start over|new design)\b/i,
  _offlineLast: null,
  _advLast: null,
  _reqText: '',
  _specOnlyReq: false,
  _beforeImg: null,
  _busy: false,
  _progress: '',
  editPlan(text) { return E.plan(text, env); },
  editYieldsToStack() { return false; },
  captureOriginal() {},
  intentSpecOnly() { return false; },
  offlineEditAsk(text, planned) { called.edit++; return Promise.resolve({ route: 'edit', kind: planned.kind, text: planned.text, queue: [] }); },
  advisorIntent() { called.advisor++; return { kind: 'should-not-run' }; },
  offlineAskCore(text) { called.core++; return Promise.resolve({ route: 'core', compound: !!D.compoundPlan(text) }); },
  render() {},
  warm() { return Promise.resolve(); },
  advisorEnv() { return {}; },
  advisorReply() { throw new Error('Advisor must not answer a preservation clarification'); }
};
vm.createContext(routeContext);
vm.runInContext(extractFunction(aiSource, 'offlineMaterialPlan') + '\n' + extractFunction(aiSource, 'offlineAsk'), routeContext, { filename: 'js/spb-pro-ai.js#offlineAsk' });

(async () => {
  const route = vm.runInContext('offlineAsk', routeContext);
  for (const text of mustClarify.slice(0, 2)) {
    called.edit = called.advisor = called.core = 0;
    const result = await route(text, {});
    assert.strictEqual(result.route, 'edit', `preservation ask should stay in the edit clarification path: ${text}`);
    assert.strictEqual(result.kind, 'ask');
    assert.strictEqual(called.edit, 1);
    assert.strictEqual(called.advisor, 0, 'preservation ask must not fall through to Advisor');
    assert.strictEqual(called.core, 0, 'preservation ask must not fall through to legacy offline routing');
  }

  called.edit = called.advisor = called.core = 0;
  const compoundText = 'matte black with orange pearl flakes';
  assert(D.compoundPlan(compoundText), 'positive compound baseline must remain recognized by the real designer');
  const compoundResult = await route(compoundText, {});
  assert.deepStrictEqual({ route: compoundResult.route, compound: compoundResult.compound }, { route: 'core', compound: true });
  assert.strictEqual(called.edit, 0, 'positive compound request must not be captured by the preservation edit guard');
  assert.strictEqual(called.advisor, 0);
  assert.strictEqual(called.core, 1);
  console.log(`offline named-panel preservation contract passed (${mustClarify.length} parser blocks; actual offlineAsk dispatch verified)`);
})().catch(err => { console.error(err); process.exitCode = 1; });

// Negating “leave/keep” means the part was not requested to stay unchanged.
const negated = E.plan("Don't leave the hood carbon; make the hood gold.", env);
assert(!negated || negated.kind !== 'ask', 'a negated preservation phrase must not be mistaken for a keep-out instruction');

// A positive assignment to an excepted panel is a separate requested edit, not a keep-out.
const assigned = E.plan('Make the whole car matte except the roof should be glossy.', env);
assert(!assigned || assigned.kind !== 'ask', 'an explicit finish assignment after except must not become a preservation clarification');

