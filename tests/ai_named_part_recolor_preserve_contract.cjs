// W12 fresh recolor/preservation oracle, written before inspecting SpbProEdit.plan.
const FRESH_ORACLE = Object.freeze([
  { id: 'f07-current-chrome-rest-is-right', text: 'Recolor only the roof green and keep its current chrome finish; the rest of the car is already right.', outcome: 'one exact roof color-only edit; preserve finish' },
  { id: 'recolour-british-spelling', text: 'Recolour only the roof green; keep its current chrome finish.', outcome: 'one exact roof color-only edit; preserve finish' },
  { id: 'simple-roof-recolor', text: 'Recolor only the roof green.', outcome: 'one exact roof color-only edit' },
  { id: 'hood-recolor-preserve-satin', text: 'Recolor just the hood blue and retain its existing satin finish.', outcome: 'one exact hood color-only edit; preserve finish' },
  { id: 'roof-recolor-preserve-matte', text: 'Change the roof color to green and leave its current matte finish as is.', outcome: 'one exact roof color-only edit; preserve finish' },
  { id: 'tail-rest-of-car-right', text: 'Recolor only the roof green; the rest of the car is already right.', outcome: 'one exact roof color-only edit' },
  { id: 'leave-other-parts-alone', text: 'Recolor only the roof green and leave all other parts alone.', outcome: 'one exact roof color-only edit' },
  { id: 'other-part-preservation-tail', text: 'Recolor only the hood blue and keep the roof in its current chrome finish.', outcome: 'ask or reject conflicting cross-part preservation' },
  { id: 'mixed-finish-switch', text: 'Recolor only the roof green and change its finish to matte.', outcome: 'not exactPart color-only claim' },
  { id: 'mixed-rest-color-action', text: 'Recolor only the roof green and make the rest of the car blue.', outcome: 'not exactPart single-part claim' },
  { id: 'two-part-recolor', text: 'Recolor the roof green and the hood blue.', outcome: 'not exactPart single-part claim' },
  { id: 'unknown-subpart', text: 'Recolor only the roof spoiler lip green and keep its current chrome finish.', outcome: 'no exactPart claim' },
  { id: 'unknown-car-part', text: 'Recolor only the windshield green and keep its current finish.', outcome: 'no exactPart claim' },
  { id: 'no-part-target', text: 'Recolor it green and keep its current chrome finish.', outcome: 'no exactPart claim' },
  { id: 'whole-body-recolor', text: 'Recolor the whole car green and keep the roof chrome.', outcome: 'no exactPart claim' },
  { id: 'negative-recolor', text: 'Do not recolor the roof green; keep its current chrome finish.', outcome: 'no exactPart claim' },
  { id: 'howto-recolor', text: 'How do I recolor the roof green while keeping its current chrome finish?', outcome: 'no exactPart claim' },
  { id: 'diagnostic-no-action', text: 'The roof looks too green but keep the current chrome finish.', outcome: 'no exactPart claim' },
  { id: 'hood-positive-roof-preserved', text: 'Keep the roof chrome and recolor only the hood blue.', outcome: 'one exact hood color-only edit; preserve roof' },
  { id: 'ambiguous-owner', text: 'Recolor only the roof green and keep its current chrome finish.', setup: 'two current owners for roof', outcome: 'no unique exactPart claim' },
  { id: 'missing-owner', text: 'Recolor only the roof green and keep its current chrome finish.', setup: 'no current helper-owned roof zone', outcome: 'not an owned edit' },
]);

if (FRESH_ORACLE.length < 16 || new Set(FRESH_ORACLE.map(c => c.id)).size !== FRESH_ORACLE.length) {
  throw new Error('Fresh recolor oracle must have at least 16 unique cases');
}

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');
const root = H.ROOT;
const w = H.load();
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
}
const E = w.SpbProEdit;
const env = { palette: [{ hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 }, { hex: '#f1f1ee', share_pct: 14 }, { hex: '#148a38', share_pct: 7 }, { hex: '#1347a8', share_pct: 5 }], layers: [] };
const exactIds = new Set([
  'f07-current-chrome-rest-is-right', 'recolour-british-spelling', 'simple-roof-recolor',
  'hood-recolor-preserve-satin', 'roof-recolor-preserve-matte', 'tail-rest-of-car-right',
  'leave-other-parts-alone',
]);
let passed = 0;
for (const c of FRESH_ORACLE) {
  const p = E.plan(c.text, env);
  if (exactIds.has(c.id)) {
    if (!p || p.kind !== 'ops' || p.exactPart !== true || p.ops.length !== 1) throw new Error(`${c.id}: expected one exact named-part color edit`);
    const op = p.ops[0];
    if (op.target.kind !== 'part' || !['roof', 'hood'].includes(op.target.part) || !op.colour || op.look || op.rel || op.shade || op.pop || op.keep || op.ext || op.recipe || op.sub || p.unknown.length) {
      throw new Error(`${c.id}: plan was not a color-only named-part edit: ${JSON.stringify(p)}`);
    }
  } else if (c.id === 'ambiguous-owner' || c.id === 'missing-owner') {
    // Ownership is intentionally outside E.plan; the integrated router must reject these.
    if (!p || p.exactPart !== true) throw new Error(`${c.id}: expected a syntactic plan for parent ownership gate`);
  } else if (p && p.exactPart === true) {
    throw new Error(`${c.id}: unsafe exactPart claim: ${JSON.stringify(p)}`);
  }
  passed++;
}
console.log(`named-part recolor preservation: ${passed}/${FRESH_ORACLE.length} oracle assertions passed; exact color-only positive cases=${exactIds.size}`);
module.exports = { FRESH_ORACLE };
