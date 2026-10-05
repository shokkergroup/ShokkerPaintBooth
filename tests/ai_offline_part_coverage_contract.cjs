// Contract for the conservative part-only eligibility proof. This is parser-only:
// no provider, browser, live canvas, or production dispatcher is invoked.
const assert = require('assert');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('../_easy_claude_work/stack_h.js');
const ROOT = path.resolve(__dirname, '..');
const w = H.load();
vm.runInContext(fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-design.js'), 'utf8'), w, { filename: 'js/spb-pro-design.js' });
const D = w.SpbProDesign;
assert(D && typeof D.offlinePartCoverage === 'function', 'coverage helper must be exported');

const cases = [
    { id: 'frozen-S01-long', ask: 'For my next track day, please paint only the hood matte blue. Leave every other panel exactly as it is because I already like the current body color and do not want the rest changed.', finishExplicit: true, canonical: 'paint the hood matte blue', expected: [{ part: 'hood', color: '#1450b4', finish: 'base::matte' }] },
    { id: 'frozen-S05-long', ask: 'Please make the roof blue and the hood gold, while leaving all other panels alone. I want those two named parts changed and the remaining body color preserved.', finishExplicit: false, canonical: 'paint the hood gold; paint the roof blue', expected: [{ part: 'hood', color: '#d7a72b', finish: 'base::gloss' }, { part: 'roof', color: '#1450b4', finish: 'base::gloss' }] },
    { id: 'positive-roof', ask: 'Paint the roof blue.', finishExplicit: false, canonical: 'paint the roof blue', expected: [{ part: 'roof', color: '#1450b4', finish: 'base::gloss' }] },
    { id: 'positive-side', ask: 'Paint the left side matte red.', finishExplicit: true, expected: [{ part: 'left side', color: '#c8102e', finish: 'base::matte' }] },
    { id: 'positive-trunk', ask: 'Make the trunk silver.', expected: [{ part: 'trunk', color: '#c3c7cc', finish: 'base::gloss' }] },
    { id: 'positive-bonnet', ask: 'Change the bonnet to matte black.', finishExplicit: true, expected: [{ part: 'hood', color: '#111113', finish: 'base::matte' }] },
    { id: 'positive-courtesy-preserve', ask: 'For the next version, turn only the hood satin green; leave every other panel as it is.', finishExplicit: true, expected: [{ part: 'hood', color: '#1f8a3b', finish: 'base::satin' }] },
    { id: 'positive-explicit-gloss', ask: 'Paint the hood glossy red.', finishExplicit: true, canonical: 'paint the hood gloss red', expected: [{ part: 'hood', color: '#c8102e', finish: 'base::gloss' }] },
    { id: 'positive-two-part', ask: 'Paint hood gold, roof blue.', expected: [{ part: 'hood', color: '#d7a72b', finish: 'base::gloss' }, { part: 'roof', color: '#1450b4', finish: 'base::gloss' }] },
    { id: 'negative-whole-car-plus-part', ask: 'Make the whole car silver and the hood blue.', reject: 'whole-car instruction mixed with part plan' },
    { id: 'negative-carbon-layer', ask: 'Make the roof matte black and add a blue carbon layer.', reject: 'additional material/layer action' },
    { id: 'negative-fine-hex', ask: 'Make the roof pearl gold with fine hex cells only there.', reject: 'unsupported finish and pattern details' },
    { id: 'negative-correction', ask: 'Turn the hood red, then correct it to matte black only.', reject: 'ordered correction cannot be represented by one plan' },
    { id: 'negative-except', ask: 'Paint the roof blue except leave the hood gold.', reject: 'positive exception needs a more complete parser' },
    { id: 'negative-conflict', ask: 'Paint the hood blue but keep it red.', reject: 'contradictory positive and preservation instructions' },
    { id: 'negative-base-plus-part', ask: 'Make the entire body matte black, then put a blue carbon layer on just the roof.', reject: 'whole-car base and part layer stack' },
    { id: 'negative-unsupported-pearl', ask: 'Paint only the roof pearl gold.', reject: 'offlinePart would lose pearl finish semantics' },
    { id: 'negative-spec-adjustment', ask: 'Make only the hood chrome and keep its paint color, changing the spec only.', reject: 'spec-only request, not a paint recolor' },
    { id: 'negative-extra-action', ask: 'Paint the hood blue and rotate the design 90 degrees.', reject: 'rotation is not covered by part recolor plan' },
    { id: 'negative-side-effect', ask: 'Paint only the roof blue and add matching stripes to the doors.', reject: 'extra stripe action' },
    { id: 'negative-unknown', ask: 'Paint only the roof blue and add a sponsor badge.', reject: 'unknown drawing/content instruction' },
    { id: 'negative-explicit-negation', ask: 'Do not make the hood red.', reject: 'explicit negative instruction' },
    { id: 'positive-preservation-before-second-edit', ask: 'Make the hood red, leave all other panels alone and make the roof blue.', finishExplicit: false, expected: [{ part: 'hood', color: '#c8102e', finish: 'base::gloss' }, { part: 'roof', color: '#1450b4', finish: 'base::gloss' }] }
];
assert(cases.length >= 14, 'include frozen examples plus a meaningful fresh holdout');
const rows = cases.map(c => {
    const result = D.offlinePartCoverage(c.ask);
    if (c.expected) {
        assert(result && result.complete === true, `${c.id}: expected a complete coverage proof`);
        assert.strictEqual(result.finishExplicit, !!c.finishExplicit, `${c.id}: explicit finish metadata differs`);
        assert.strictEqual(typeof result.canonicalText, 'string', `${c.id}: proven result needs canonical text`);
        if (c.canonical) assert.strictEqual(result.canonicalText, c.canonical, `${c.id}: canonical text semantics differ`);
        const got = JSON.parse(JSON.stringify(result.zones.map(z => ({ part: z.region.part, color: String(z.color).toLowerCase(), finish: z.finish }))));
        assert.deepStrictEqual(got, c.expected, `${c.id}: exact part/color/finish semantics differ`);
        return { id: c.id, verdict: 'proved', finishExplicit: result.finishExplicit, canonicalText: result.canonicalText, zones: got };
    }
    assert.strictEqual(result, null, `${c.id}: unsafe/partial request must fail closed (${c.reject})`);
    return { id: c.id, verdict: 'rejected', reason: c.reject };
});
const reviewPath = path.join(__dirname, 'ai_offline_part_coverage_review_contract.cjs');
const reviewOutput = execFileSync(process.execPath, [reviewPath], { encoding: 'utf8' });
assert(/PASS offline part coverage review: 33\/33\b/.test(reviewOutput), 'independent 33-case review contract must pass');
const reviewFirstLine = reviewOutput.split(/\r?\n/)[0];
assert.strictEqual(rows.filter(r => r.verdict === 'proved').length, 10);
assert.strictEqual(rows.filter(r => r.verdict === 'rejected').length, 13);
const report = {
    title: 'AI helper offline part coverage contract',
    generated_at: new Date().toISOString(),
    mode: 'diagnostic contract only; helper is not wired to routing; no provider/browser/live mutations',
    helper: 'SpbProDesign.offlinePartCoverage(text)',
    source_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-design.js'))).digest('hex'),
    prior_helper_baseline: {
        source_sha256: '5c4ec49036a67fd3f30d738e31076b44204cda942e3ddf249cadde15b139c5a3',
        contract: '20 cases: 8 proven, 12 rejected',
        independent_review: '33 cases: 31 passed, 2 failed; failure P1s were explicit-negation false acceptance and preservation-clause swallowing a following roof edit.'
    },
    current_independent_review: { file: 'tests/ai_offline_part_coverage_review_contract.cjs', result: reviewFirstLine },
    metadata_contract: {
        finishExplicit: 'true only if a supported finish word is stated; false means gloss is only the offlinePart default and must not be claimed as user intent.',
        canonicalText: 'emitted only after complete coverage proof; uses exact planned part/color and includes finish only when the source explicitly specified it.'
    },
    proven_count: rows.filter(r => r.verdict === 'proved').length,
    rejected_count: rows.filter(r => r.verdict === 'rejected').length,
    limitations: [
        'Only simple part recolours with exact region/color mapping and a uniform supported finish are proven.',
        'Ordered edits, whole-car plus part stacks, patterns/material layers, unsupported finish semantics, spec-only work, and arbitrary extras return null.',
        'Preservation text is removed only within its bounded clause; a conjunction introducing another action ends that clause. Explicit negation and unresolved residual words fail closed.',
        'finishExplicit distinguishes user-stated finishes from implicit gloss. canonicalText is emitted only after the original request passes full coverage validation.',
        'The helper deliberately leaves general routing and the existing length guard untouched.'
    ],
    cases: rows
};
const out = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_PART_COVERAGE_2026-10-03.json');
fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
console.log(`PASS part coverage contract: ${rows.length} cases (${report.proven_count} proven, ${report.rejected_count} rejected); ${reviewFirstLine}; report=${path.relative(ROOT, out)}`);
