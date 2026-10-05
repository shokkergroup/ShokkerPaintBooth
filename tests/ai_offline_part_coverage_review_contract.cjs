'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
// Fresh semantic oracle authored before reviewing offlinePartCoverage source.
// The frozen oracle records requested target/scope/color/finish facts. Its
// complex forms expect null unless every fact fits a complete structured plan.
const ORACLES = [
  { id: 'single-directional-part', text: 'Could you paint the left door panel satin teal?', must: ['left door panel', 'left', 'teal', 'satin'] },
  { id: 'two-parts-independent-looks', text: 'Make the hood candy red and the roof matte black.', must: ['hood', 'roof', 'candy red', 'matte black'] },
  { id: 'passenger-rocker-only', text: 'Set only the passenger-side rocker to silver chrome.', must: ['passenger', 'rocker', 'silver', 'chrome', 'only'] },
  { id: 'rear-wing-racing-green', text: 'Could you give the rear wing British racing green with a metallic finish?', must: ['rear wing', 'British racing green', 'metallic'] },
  { id: 'grille-plus-preserved-roof', text: 'Please make the grille orange pearl, preserving the black roof.', must: ['grille', 'orange', 'pearl', 'preserv', 'black roof'] },
  { id: 'mirrors-only-preserve-body', text: 'Keep the body blue and just paint the mirrors bright white gloss.', must: ['body blue', 'mirrors', 'bright white', 'gloss', 'just'] },
  { id: 'driver-doors-rest-untouched', text: 'Could you make the driver-side doors purple candy, with the rest untouched?', must: ['driver', 'doors', 'purple', 'candy', 'rest untouched'] },
  { id: 'left-right-fender-color-distinction', text: 'Make the left front fender bright red and the right front fender deep blue.', must: ['left front fender', 'bright red', 'right front fender', 'deep blue'] },
  { id: 'quarter-and-spoiler-exception', text: 'Turn the right rear quarter orange; leave the rear spoiler matte black.', must: ['right rear quarter', 'orange', 'rear spoiler', 'matte black', 'leave'] },
  { id: 'filler-and-preservation-tail', text: 'If you would, maybe turn the hood a deep emerald with a satin coat, and keep my wheels exactly as they are.', must: ['hood', 'deep emerald', 'satin', 'wheels', 'exactly as they are'] },
  { id: 'negative-target-trunk-lid', text: 'Do not change the decklid; instead set the trunk lid to champagne gold pearl.', must: ['decklid', 'do not change', 'trunk lid', 'champagne gold', 'pearl'] },
  { id: 'whole-body-scope', text: 'Give every body panel a charcoal metallic look.', must: ['every', 'body panel', 'charcoal', 'metallic'] },
  { id: 'side-bodywork-direction', text: 'Apply dark charcoal metallic to all the side bodywork.', must: ['side', 'bodywork', 'dark charcoal', 'metallic'] },
  { id: 'hood-only-preserve-base', text: 'Keep the base paint as it is except make the hood gloss red.', must: ['base paint', 'as it is', 'hood', 'gloss', 'red', 'except'] },
  { id: 'bonnet-negation-roof-target', text: 'Not the bonnet this time; make the roof pale yellow pearl.', must: ['bonnet', 'not', 'roof', 'pale yellow', 'pearl'] },
  { id: 'door-pair-color-and-finish-split', text: 'Use the same red on both doors, but make only the left one matte; keep the right one metallic.', must: ['both doors', 'same red', 'left', 'matte', 'right', 'metallic'] },
  { id: 'bumper-grille-same-color-distinct-finish', text: 'Paint the front bumper and grille lime green, with a matte bumper and glossy grille.', must: ['front bumper', 'grille', 'lime green', 'matte bumper', 'glossy grille'] },
  { id: 'door-opposite-preservation', text: 'Leave the passenger door unchanged; make the driver door royal purple with a satin finish.', must: ['passenger door', 'unchanged', 'driver door', 'royal purple', 'satin'] },
  { id: 'color-descriptor-cobalt-satin', text: 'Set just the rear deck to rich cobalt blue in satin.', must: ['rear deck', 'rich cobalt blue', 'satin', 'just'] },
  { id: 'color-descriptor-warm-pearl', text: 'Make the front fascia a warm ivory pearl while leaving the side skirts alone.', must: ['front fascia', 'warm ivory', 'pearl', 'side skirts', 'alone'] }
];

const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');
const root = path.resolve(__dirname, '..');
const world = H.load();
vm.runInContext(fs.readFileSync(path.join(root, 'js', 'spb-pro-design.js'), 'utf8'), world, { filename: 'js/spb-pro-design.js' });
assert.equal(typeof world.SpbProDesign?.offlinePartCoverage, 'function', 'coverage helper export missing');
const parentCounterexamples = [
  { id: 'owner-counterexample-explicit-negation', text: 'Do not make the hood red.', expected: null },
  { id: 'owner-counterexample-preservation-before-second-edit', text: 'Make the hood red, leave all other panels alone and make the roof blue.', expected: {
    parts: ['hood', 'roof'], finish: 'base::gloss', zones: [
      { part: 'hood', color: '#c8102e', finish: 'base::gloss' },
      { part: 'roof', color: '#1450b4', finish: 'base::gloss' }
    ]
  } }
];
const safePositiveProbes = [
  { id: 'safe-positive-hood-simple', text: 'Make my hood blue, please.', expected: { parts: ['hood'], finish: 'base::gloss', zones: [{ part: 'hood', color: '#1450b4', finish: 'base::gloss' }] } },
  { id: 'safe-positive-roof-finish', text: 'Turn the roof matte red.', expected: { parts: ['roof'], finish: 'base::matte', zones: [{ part: 'roof', color: '#c8102e', finish: 'base::matte' }] } },
  { id: 'safe-positive-side-finish', text: 'Set the left side satin green.', expected: { parts: ['left side'], finish: 'base::satin', zones: [{ part: 'left side', color: '#1f8a3b', finish: 'base::satin' }] } },
  { id: 'safe-positive-rear-end-alias', text: 'Paint the rear end black.', expected: { parts: ['rear bumper'], finish: 'base::gloss', zones: [{ part: 'rear bumper', color: '#111113', finish: 'base::gloss' }] } },
  { id: 'safe-positive-bonnet-alias', text: 'Make the bonnet silver.', expected: { parts: ['hood'], finish: 'base::gloss', zones: [{ part: 'hood', color: '#c3c7cc', finish: 'base::gloss' }] } },
  { id: 'safe-positive-trunk', text: 'Change the trunk to gold.', expected: { parts: ['trunk'], finish: 'base::gloss', zones: [{ part: 'trunk', color: '#d7a72b', finish: 'base::gloss' }] } },
  { id: 'safe-positive-two-colors', text: 'Paint the hood gold and roof blue.', expected: null },
  { id: 'safe-positive-both-sides', text: 'Make both sides red.', expected: null, offlinePartExpected: {
    parts: ['left side', 'right side'], finish: 'gloss', zones: [
      { part: 'left side', color: '#c8102e', finish: 'base::gloss' },
      { part: 'right side', color: '#c8102e', finish: 'base::gloss' }
    ]
  } },
  { id: 'safe-positive-two-named-directions', text: 'Paint roof blue, hood gold, and leave the other panels unchanged.', expected: {
    parts: ['hood', 'roof'], finish: 'base::gloss', zones: [
      { part: 'hood', color: '#d7a72b', finish: 'base::gloss' },
      { part: 'roof', color: '#1450b4', finish: 'base::gloss' }
    ]
  } },
  { id: 'same-color-repeated-targets', text: 'Make the hood and roof both red, with all other panels unchanged.', expected: null, offlinePartExpected: {
    parts: ['hood', 'roof'], finish: 'gloss', zones: [
      { part: 'hood', color: '#c8102e', finish: 'base::gloss' },
      { part: 'roof', color: '#c8102e', finish: 'base::gloss' }
    ]
  } },
  { id: 'same-color-targets-distinct-finish', text: 'Paint the roof matte blue and the hood satin blue.', expected: null }
];
const cases = ORACLES.map(x => ({ id: x.id, text: x.text, expected: null })).concat(parentCounterexamples, safePositiveProbes);
const failures = [], rows = [];
function projectPlan(result) {
  if (!result) return null;
  const zones = [];
  result.zones.forEach(z => zones.push({ part: z.region && z.region.part, color: String(z.color || '').toLowerCase(), finish: z.finish }));
  return {
    parts: Array.from(result.parts),
    finish: result.finish,
    zones
  };
}
for (const c of cases) {
  const actual = projectPlan(world.SpbProDesign.offlinePartCoverage(c.text));
  try { assert.deepStrictEqual(actual, c.expected, `${c.id}: incomplete, false, or semantically different plan`); }
  catch (e) { failures.push(`${c.id}: ${e.message}`); }
  if (c.offlinePartExpected) {
    const lowerLevel = projectPlan(world.SpbProDesign.offlinePart(c.text));
    try { assert.deepStrictEqual(lowerLevel, c.offlinePartExpected, `${c.id}: underlying offlinePart plan changed`); }
    catch (e) { failures.push(`${c.id} underlying offlinePart: ${e.message}`); }
  }
  const frozen = ORACLES.find(x => x.id === c.id);
  rows.push({ id: c.id, group: frozen ? 'frozen-fresh-oracle' : (parentCounterexamples.some(x => x.id === c.id) ? 'parent-supplied-counterexample' : 'coverage-control'), intentFacts: frozen && frozen.must, expected: c.expected, actual, verdict: JSON.stringify(actual) === JSON.stringify(c.expected) ? 'pass' : 'fail' });
}
console.log(`${failures.length ? 'FAIL' : 'PASS'} offline part coverage review: ${cases.length - failures.length}/${cases.length}; fresh=${ORACLES.length}, supplied-counterexamples=${parentCounterexamples.length}, controls=${safePositiveProbes.length}`);
console.log(JSON.stringify(rows.filter(r => r.verdict === 'fail'), null, 2));
if (failures.length) { console.error(failures.join('\n')); process.exitCode = 1; }
