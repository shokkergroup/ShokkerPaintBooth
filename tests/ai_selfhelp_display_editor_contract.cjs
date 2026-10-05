'use strict';
// Frozen W20 query/display oracle. Added before reading self-help source.
const ORACLE = Object.freeze([
  { q: 'How can I put one finish on just a single door?', class: 'documented-local-edit', display: 'direct actionable answer; no search metadata' },
  { q: 'Where do I change the color of a selected panel?', class: 'documented-local-edit', display: 'direct answer; retain actual control names only if sourced' },
  { q: 'What is the safest way to save my current paint project?', class: 'documented-project-workflow', display: 'direct answer; distinguish project save from output export' },
  { q: 'Can I keep the chat visible while I work on the full editor?', class: 'full-editor-guidance', display: 'explain only documented Chat Studio/full-editor behavior' },
  { q: 'How do I switch from the chat experience to the full editor without losing my place?', class: 'full-editor-guidance', display: 'handoff guidance only; no invented buttons or persistence guarantees' },
  { q: 'I am using the full editor: how do I ask AI a follow-up about the finish?', class: 'full-editor-guidance', display: 'describe documented in-chat teaching versus editor-only controls' },
  { q: 'Can AI answer a question while I keep editing the car?', class: 'full-editor-guidance', display: 'answer only if manual describes current supported interaction' },
  { q: 'How do I undo the last zone change?', class: 'documented-edit-workflow', display: 'direct answer; no alias text' },
  { q: 'Why did my chosen finish affect more than one surface?', class: 'documented-zone-workflow', display: 'direct answer bounded to documented zone-selection behavior' },
  { q: 'Where can I review or change the export settings?', class: 'documented-export-workflow', display: 'direct answer; no fabricated navigation' },
  { q: 'Does the helper keep my conversation when I reload a different car?', class: 'uncertain-or-unsupported', display: 'safe limitation if manuals do not specify it' },
  { q: 'What exact hidden AI controls are available in the editor?', class: 'uncertain-or-unsupported', display: 'do not invent undocumented controls' },
  { q: 'How can I chat with AI while using the full editor?', class: 'supplied-native-regression', display: 'keep in-chat help distinct from controls that require full editor' }
]);
const DISPLAY_ORACLE = Object.freeze({
  aliases: 'Index/search metadata may contain alternate phrasings but rendered human answer must not expose alias-only text.',
  editor: 'Chat Studio and full-editor guidance must use only documented labels, current UI states, and supported handoff behavior.',
  helpfulness: 'A result must be relevant to the query and cite a useful topic; arbitrary nonempty text does not count as an answer.'
});
if (require.main === module) {
  const assert = require('node:assert/strict');
  const crypto = require('node:crypto');
  const fs = require('node:fs');
  const path = require('node:path');
  const vm = require('node:vm');
  const root = path.resolve(__dirname, '..');
  const sourcePath = path.join(root, 'js/spb-self-help.js');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const hash = crypto.createHash('sha256').update(source).digest('hex').toUpperCase();
  assert.equal(hash, 'B860C0ACC0AB442F7B6477853C4438AB0B9E74E94FD87904E356768D2F97F7B2', 'self-help source changed after this test freeze; update hash after review');
  let networkAttempts = 0;
  const world = { console, fetch() { networkAttempts++; throw new Error('network is outside this offline test'); } };
  world.window = world; world.document = {};
  world.XMLHttpRequest = function () { networkAttempts++; throw new Error('network is outside this offline test'); };
  vm.createContext(world);
  for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), world, { filename: file });
  }
  function state(mode) {
    return {
      paint: 'flat', layers: [{ id: 'body', name: 'Body' }],
      zones: [{ i: 0, name: 'Left Door', muted: false, base: 'Gloss', finish: 'Gloss', colourMode: 'finish', pattern: 'Flames', patternMode: 'overlay', spec: 1, layers: [], intensity: 100, regionMask: [1], selects: true }],
      selected: 0, carMap: { known: true, missing: [] }, mode: mode || 'pro', last: null
    };
  }
  const cases = [
    [ORACLE[0].q, 'pro', 'hdi.finish_one_part'],
    [ORACLE[1].q, 'pro', 'hdi.finish_colour'],
    [ORACLE[2].q, 'pro', 'hdi.save_project'],
    [ORACLE[3].q, 'pro', 'hdi.use_chat'],
    [ORACLE[4].q, 'chat', 'hdi.use_chat'],
    [ORACLE[5].q, 'pro', 'hdi.use_chat'],
    [ORACLE[6].q, 'pro', null],
    [ORACLE[7].q, 'pro', 'hdi.undo'],
    [ORACLE[8].q, 'pro', null],
    [ORACLE[9].q, 'pro', 'hdi.export_iracing'],
    [ORACLE[10].q, 'pro', null],
    [ORACLE[11].q, 'pro', 'unsupported-hidden-controls']
  ];
  let checks = 0;
  for (const [question, mode, expectedCite] of cases) {
    const suppliedState = state(mode), before = JSON.stringify(suppliedState);
    const result = world.SpbSelfHelp.handle(question, suppliedState);
    if (expectedCite === null) {
      assert.equal(result, null, `${question}: unsupported behavior stays unclaimed`);
      checks++;
      continue;
    }
    if (expectedCite === 'unsupported-hidden-controls') {
      assert.ok(result && result.cites.includes('ai_limits'));
      assert.match(result.text, /do not have a verified list of hidden controls/i);
      assert.doesNotMatch(result.text, /click|press|open the/i);
      checks++;
      continue;
    }
    assert.ok(result && result.cites.includes(expectedCite), `${question}: expected relevant citation ${expectedCite}, got ${result && result.cites}`);
    assert.doesNotMatch(result.text, /Also asked as\s*:/i, `${question}: search aliases leaked into the answer`);
    assert.ok(result.text.length > 40, `${question}: answer lacks useful guidance`);
    if (expectedCite === 'hdi.use_chat' && mode === 'chat') assert.match(result.text, /Chat Studio, type your question.*chat on the left/i);
    if (expectedCite === 'hdi.use_chat' && mode === 'pro') {
      assert.match(result.text, /AI button at the bottom right/i);
      assert.match(result.text, /Tell me what you want/i);
      assert.doesNotMatch(result.text, /click CHAT in the pill/i);
    }
    assert.equal(JSON.stringify(suppliedState), before, `${question}: answer mutated supplied state`);
    checks++;
  }
  assert.equal(world.SpbSelfHelp.classify('How do I talk to the AI?').howto[0].h.id, 'hdi.use_chat', 'search alias remains useful for indexing');
  assert.match(world.SpbSelfHelp.classify('How do I talk to the AI?').howto[0].h.note, /Also asked as:/, 'alias remains in private source metadata');
  checks += 2;

  const query = 'How do I chat with AI while using the full editor?'; // supplied native regression, counted separately from fresh holdouts
  const inEditor = world.SpbSelfHelp.handle(query, state('pro'));
  assert.ok(inEditor && inEditor.cites.includes('hdi.use_chat'));
  assert.match(inEditor.text, /full editor/i);
  assert.match(inEditor.text, /AI button at the bottom right/i);
  assert.match(inEditor.text, /Tell me what you want/i);
  assert.doesNotMatch(inEditor.text, /Also asked as\s*:/i);
  assert.doesNotMatch(inEditor.text, /click CHAT in the pill/i);
  checks++;
  const inStudio = world.SpbSelfHelp.handle(query, state('chat'));
  assert.ok(inStudio && inStudio.cites.includes('hdi.use_chat'));
  assert.match(inStudio.text, /Chat Studio, type your question.*chat on the left/i);
  assert.match(inStudio.text, /Full editor →/);
  assert.match(inStudio.text, /AI button at the bottom right/);
  assert.doesNotMatch(inStudio.text, /Also asked as\s*:/i);
  checks++;
  const unsupported = world.SpbSelfHelp.handle('Will chat survive a car change?', state('pro'));
  assert.equal(unsupported, null, 'unsupported transcript-persistence claim stays unclaimed');
  const hiddenControls = world.SpbSelfHelp.handle('What exact hidden AI controls are available?', state('pro'));
  assert.ok(hiddenControls && hiddenControls.cites.includes('ai_limits'));
  assert.match(hiddenControls.text, /do not have a verified list of hidden controls/i);
  assert.doesNotMatch(hiddenControls.text, /click|press|open the/i, 'unknown controls get no fabricated steps');
  assert.equal(networkAttempts, 0, 'helpers remain offline; VM test uses no provider or native service');
  checks += 5;
  console.log(`PASS W20 self-help presentation/editor contract: ${checks} assertions, ${cases.length} frozen fresh questions, one separately labeled supplied regression.`);
}
module.exports = { ORACLE, DISPLAY_ORACLE };
