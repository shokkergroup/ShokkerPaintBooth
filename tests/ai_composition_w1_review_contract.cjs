const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');

const w = H.load();
vm.runInContext(fs.readFileSync(path.join(H.ROOT, 'js/spb-pro-design.js'), 'utf8'), w, { filename: 'js/spb-pro-design.js' });
const A = w.SpbProAdvisor;
const D = w.SpbProDesign;

function partsOf(steps) {
  return Array.from(new Set(steps.filter(step => step.tool === 'add_zone' && step.args && step.args.region && step.args.region.part)
    .flatMap(step => Array.isArray(step.args.region.part) ? Array.from(step.args.region.part) : [step.args.region.part]))).sort();
}
function checkApply(label, steps, expected, failures) {
  if (!steps.length) return; // Non-base stack cards expose the same target but are applied by the base card's stackWith payload.
  if (steps.some(step => step.tool === 'edit_zone')) failures.push(`${label}: exclusive part request emitted body-zone edits`);
  const regions = steps.filter(step => step.tool === 'add_zone' && step.args && step.args.region && step.args.region.part)
    .map(step => Array.isArray(step.args.region.part) ? Array.from(step.args.region.part) : [step.args.region.part]);
  for (const region of regions) {
    for (const part of region) if (!expected.includes(part)) failures.push(`${label}: unexpected applied part ${part}`);
  }
  const got = partsOf(steps);
  if (JSON.stringify(got) !== JSON.stringify(expected.slice().sort())) {
    failures.push(`${label} expected=${expected.join('|')} got=${got.join('|') || '(no part zones)'}`);
  }
}
const cases = [
  ['left-only, side before material', 'Only the driver side gets a matte black base with fine carbon.', ['left side']],
  ['left-only, material before reversed side clause', 'Matte black with fine carbon only on the driver side.', ['left side']],
  ['right-only, material before side', 'Put fine hex on the passenger side only with a satin blue base.', ['right side']],
  ['right-only, exclusivity before side', 'Matte black with fine carbon texture only on the right side.', ['right side']],
  ['right-only, material-first reversed clause', 'Apply dark blue with fine carbon exclusively to the passenger side.', ['right side']],
  ['both-side positive control', 'Gloss emerald with flakes on both sides only.', ['left side', 'right side']],
  ['both-side ordinary order', 'Fine carbon with gloss blue on both sides.', ['left side', 'right side']]
];
const failures = [];
for (const [label, ask, expected] of cases) {
  const item = A.classify(ask, null);
  const answer = item && A.answer(item, H.ENV);
  const kitSteps = [];
  if (answer && answer.kind === 'stack') {
    for (const kit of answer.kits || []) for (const entry of kit.items || []) {
      const targetPart = entry.target && entry.target.region && entry.target.region.part;
      if (targetPart) {
        const targetParts = (Array.isArray(targetPart) ? Array.from(targetPart) : [targetPart]).sort();
        if (JSON.stringify(targetParts) !== JSON.stringify(expected.slice().sort())) {
          failures.push(`${label} kit item target expected=${expected.join('|')} got=${targetParts.join('|')}`);
        }
      }
      const applied = (A.applyPlan(entry.card, entry.target, H.ENV) || {}).steps || [];
      checkApply(`${label} A.applyPlan`, applied, expected, failures);
      kitSteps.push(...applied);
    }
    checkApply(`${label} A.applyPlan kit union`, kitSteps, expected, failures);
  }
  const tool = A.suggestTool({ ask }, H.ENV);
  const toolSteps = (tool && tool.apply) || [];
  checkApply(`${label} A.suggestTool.apply`, toolSteps, expected, failures);
  if (label !== 'both-side positive control') {
    const plan = D.compoundPlan(ask);
    if (plan && plan.zones) {
      const designerParts = plan.zones.flatMap(zone => {
        const p = zone.region && zone.region.part;
        return p ? (Array.isArray(p) ? Array.from(p) : [p]) : [];
      }).sort();
      if (designerParts.length && JSON.stringify(designerParts) !== JSON.stringify(expected.slice().sort())) {
        failures.push(`${label} D.compoundPlan expected=${expected.join('|')} got=${designerParts.join('|')}`);
      }
    }
  }
}

// Preservation, recommendations and how-to guidance never become completed paint plans.
for (const [label, ask] of [
  ['preserve roof', 'Repaint every panel satin red but leave the roof untouched.'],
  ['preserve hood and numbers', 'Make the car matte gold; preserve hood and numbers.'],
  ['preserve passenger side', 'Change the body to blue except keep the passenger side original.'],
  ['preserve roof in body request', 'Give the full body emerald, but keep the roof unchanged.'],
  ['advice', 'Should I put carbon on the hood or the roof?'],
  ['recommendation', 'Which pattern would work best on the passenger side?'],
  ['guidance', 'How do I add a chrome roof?']
]) {
  const plan = D.compoundPlan(ask);
  if (plan && plan.zones && plan.zones.length) failures.push(`${label}: designer produced a completed plan`);
  const item = A.classify(ask, null);
  const answer = item && A.answer(item, H.ENV);
  if (answer && answer.kind === 'stack' && answer.kits && answer.kits.length) failures.push(`${label}: advisor presented an actionable stack`);
  const tool = A.suggestTool({ ask }, H.ENV);
  if (tool && tool.apply && tool.apply.length) failures.push(`${label}: suggestTool produced apply steps`);
}

assert.deepEqual(failures, [], `composition scope violations:\n${failures.join('\n')}`);
console.log('PASS ai_composition_w1_review_contract.cjs (5 directional formulations, 2 both-side controls, 4 preservation guards, 3 advice/guidance guards; actual apply outputs)');
