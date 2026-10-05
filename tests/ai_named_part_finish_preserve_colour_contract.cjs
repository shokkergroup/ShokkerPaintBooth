// W17 fresh finish/preserve-current-color oracle, authored before reopening plan() source.
const FRESH_ORACLE = Object.freeze([
  { id: 'native-red-roof-chrome-preserve-red', text: 'Make only the roof chrome and keep its red paint color.', outcome: 'one exact roof chrome finish-only edit; preserve current red paint' },
  { id: 'preserve-current-paint-color', text: 'Make only the roof chrome and keep its current paint color.', outcome: 'one exact roof chrome finish-only edit' },
  { id: 'retain-existing-paint-color', text: 'Make only the roof chrome while retaining its existing paint color.', outcome: 'one exact roof chrome finish-only edit' },
  { id: 'leave-its-current-color', text: 'Change only the roof finish to chrome and leave its current color as is.', outcome: 'one exact roof chrome finish-only edit' },
  { id: 'british-colour-spelling', text: 'Make only the roof chrome and keep its current paint colour.', outcome: 'one exact roof chrome finish-only edit' },
  { id: 'hood-current-blue-preserved', text: 'Make only the hood satin and keep its current blue paint color.', outcome: 'one exact hood satin finish-only edit' },
  { id: 'unsupported-alternate-finish-verb', text: 'Apply a chrome finish only to the roof, preserving its existing red color.', outcome: 'no exactPart claim; the base imperative grammar is unsupported' },
  { id: 'paint-stays-red', text: 'Set only the roof to chrome; its paint should stay red.', outcome: 'one exact roof chrome finish-only edit' },
  { id: 'leave-current-paint-alone', text: 'Make only the roof chrome and leave its current paint alone.', outcome: 'one exact roof chrome finish-only edit' },
  { id: 'simple-finish-only-control', text: 'Make only the roof chrome.', outcome: 'one exact roof chrome finish-only edit without preservation tail' },
  { id: 'cross-part-color-preservation', text: 'Make only the hood satin and keep the roof red.', outcome: 'safe ask/reject, no exact hood claim' },
  { id: 'cross-part-finish-preservation', text: 'Make only the hood satin and keep the roof chrome.', outcome: 'safe ask/reject, no exact hood claim' },
  { id: 'contradictory-new-paint-color', text: 'Make only the roof chrome and paint it green while keeping its red paint color.', outcome: 'no exactPart claim; contradictory actions remain unclaimed' },
  { id: 'new-paint-color-with-preserve-tail', text: 'Make only the roof chrome and paint it green, keeping its current red color.', outcome: 'no exactPart claim' },
  { id: 'extra-texture-action', text: 'Make only the roof chrome and add a carbon-fiber texture.', outcome: 'no exactPart claim' },
  { id: 'extra-pattern-action', text: 'Make only the roof chrome and add a flame pattern.', outcome: 'no exactPart claim' },
  { id: 'two-part-finish-action', text: 'Make the roof chrome and the hood satin.', outcome: 'no single exactPart claim' },
  { id: 'whole-car-finish', text: 'Make the whole car chrome and keep the roof red.', outcome: 'no exactPart claim' },
  { id: 'unknown-part', text: 'Make only the windshield chrome and keep its current color.', outcome: 'no exactPart claim' },
  { id: 'question', text: 'Should I make only the roof chrome and keep its current red paint color?', outcome: 'no exactPart claim' },
  { id: 'negative', text: 'Do not make the roof chrome; keep its current red paint color.', outcome: 'no exactPart claim' },
]);
if (FRESH_ORACLE.length < 16 || new Set(FRESH_ORACLE.map(c => c.id)).size !== FRESH_ORACLE.length) {
  throw new Error('Fresh finish preservation oracle must contain at least 16 unique cases');
}

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');
const w = H.load();
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(H.ROOT, file), 'utf8'), w, { filename: file });
}
const E = w.SpbProEdit;
const env = { palette: [{ hex: '#bb201e', share_pct: 61 }, { hex: '#141416', share_pct: 17 }, { hex: '#ededeb', share_pct: 12 }, { hex: '#1354b5', share_pct: 6 }], layers: [] };
const positive = new Set([
  'native-red-roof-chrome-preserve-red', 'preserve-current-paint-color', 'retain-existing-paint-color',
  'leave-its-current-color', 'british-colour-spelling', 'hood-current-blue-preserved',
  'paint-stays-red', 'leave-current-paint-alone',
  'simple-finish-only-control',
]);
let passed = 0;
for (const c of FRESH_ORACLE) {
  const p = E.plan(c.text, env);
  if (positive.has(c.id)) {
    if (!p || p.kind !== 'ops' || p.exactPart !== true || p.ops.length !== 1) throw new Error(c.id + ': expected one exact named-part finish edit');
    const op = p.ops[0];
    if (op.target.kind !== 'part' || !['roof', 'hood'].includes(op.target.part) || !op.look || op.colour || op.rel || op.shade || op.pop || op.keep || op.recipe || op.sub || p.unknown.length) {
      throw new Error(c.id + ': must preserve current paint, not assign color or another action: ' + JSON.stringify(p));
    }
  } else if (p && p.exactPart === true) {
    throw new Error(c.id + ': unsafe exactPart claim: ' + JSON.stringify(p));
  }
  passed++;
}
console.log('named-part finish preservation: ' + passed + '/' + FRESH_ORACLE.length + ' oracle assertions passed');
module.exports = { FRESH_ORACLE };
