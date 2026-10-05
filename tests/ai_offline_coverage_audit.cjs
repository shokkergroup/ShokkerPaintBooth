// Read-only audit of the built-in-first Pro AI gate. This executes the exact
// offlineCanHandle function body with real design/edit/advisor modules and
// stable paint-state stubs. It never calls askCore or a model provider.
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('../_easy_claude_work/stack_h.js');

const ROOT = path.resolve(__dirname, '..');
const fixturePath = path.join(__dirname, 'fixtures', 'ai_offline_coverage_20261003.json');
const fixtureBytes = fs.readFileSync(fixturePath);
const fixture = JSON.parse(fixtureBytes.toString('utf8'));
const expectedFixtureSha256 = 'e8d76476621531983f0acb0154748d93cbd11ca5af78220b2ffaa15ff18f320f';
assert.strictEqual(crypto.createHash('sha256').update(fixtureBytes).digest('hex'), expectedFixtureSha256,
    'frozen coverage fixture changed; do not refresh this audit input in place');
const w = H.load();
vm.runInContext(fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-design.js'), 'utf8'), w, { filename: 'js/spb-pro-design.js' });
vm.runInContext(fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-edit.js'), 'utf8'), w, { filename: 'js/spb-pro-edit.js' });
const D = w.SpbProDesign;
const E = w.SpbProEdit;
const A = w.SpbProAdvisor;
assert(D && E && A, 'real designer, edit helper, and advisor must load');

assert(fixture.cases.length > 0, 'fixture must contain prompts');
const pairs = new Map();
fixture.cases.forEach(c => {
    const list = pairs.get(c.pair) || [];
    list.push(c);
    pairs.set(c.pair, list);
});
assert.strictEqual(pairs.size, 12, 'fixture must retain all short/long pairs');
for (const [pair, list] of pairs) {
    assert.strictEqual(list.length, 2, `${pair} must have two variants`);
    const short = list.find(c => c.variant === 'short');
    const long = list.find(c => c.variant === 'long');
    assert(short && short.word_count < 30, `${pair} short form must be below 30 words`);
    assert(long && long.word_count > 30, `${pair} long form must be above 30 words`);
    assert.strictEqual(short.intended_scope, long.intended_scope, `${pair} changes intent across variants`);
    assert.strictEqual(short.expected_capability, long.expected_capability, `${pair} changes expected capability across variants`);
}

// These inputs mirror the palette/layer shape used by the existing edit corpus.
const EDIT_ENV = {
    palette: ['#141416', '#6fb7e9', '#f26b21', '#c9a227', '#ffffff'].map(hex => ({ hex, share_pct: 20 })),
    layers: []
};
const proAiSource = fs.readFileSync(path.join(ROOT, 'js', 'spb-pro-ai.js'), 'utf8');
const materialPlanStart = proAiSource.indexOf('    function offlineMaterialPlan(text) {');
const materialPlanEnd = proAiSource.indexOf('\n    function offlineMaterialAsk', materialPlanStart);
assert(materialPlanStart >= 0 && materialPlanEnd > materialPlanStart,
    'could not extract production offlineMaterialPlan dependency');
const offlineMaterialPlanSource = proAiSource.slice(materialPlanStart, materialPlanEnd).trim();
const fnStart = proAiSource.indexOf('    function offlineCanHandle(text) {');
const fnEnd = proAiSource.indexOf('\n    function askAIInstead', fnStart);
assert(fnStart >= 0 && fnEnd > fnStart, 'could not extract production offlineCanHandle function');
const offlineCanHandleSource = proAiSource.slice(fnStart, fnEnd).trim();
const offlineAskStart = proAiSource.indexOf('    function offlineAsk(text, o) {');
const offlineAskEnd = proAiSource.indexOf('\n    function advisorPick', offlineAskStart);
assert(offlineAskStart >= 0 && offlineAskEnd > offlineAskStart, 'could not locate production offlineAsk priority function');
const offlineAskSource = proAiSource.slice(offlineAskStart, offlineAskEnd);
const noMatch = /(?!) /;
const routeContext = {
    D,
    E,
    _offlineLast: null,
    selfHelpClaim: () => null,
    advisorIntent: text => A.classify(text, null),
    editPlan: text => E.plan(text, EDIT_ENV),
    START_OVER_RE: /^\s*start over\b/i,
    SMALL_HELLO_RE: /^\s*(hi|hello|hey)\b/i,
    SMALL_THANKS_RE: /^\s*(thanks|thank you)\b/i,
    CANT_RE: /\b(?:resize|move|rotate)\b/i,
    layerVisRequest: () => false,
    NUM_FIX_RE: noMatch,
    lookEntry: query => Object.keys(D.LOOK_CURATED || {}).some(k => String(query || '').toLowerCase().includes(k)),
    console,
    window: null
};
routeContext.window = routeContext;
vm.createContext(routeContext);
const materialControlsSource = fs.readFileSync(path.join(ROOT, 'js', 'spb-ai-material-controls.js'), 'utf8');
vm.runInContext(materialControlsSource, routeContext, { filename: 'js/spb-ai-material-controls.js' });
assert(routeContext.SpbMaterialControls && typeof routeContext.SpbMaterialControls.parse === 'function',
    'actual material-controls helper did not initialize in the route context');
vm.runInContext(`${offlineMaterialPlanSource}\nthis.offlineMaterialPlan = offlineMaterialPlan;`, routeContext,
    { filename: 'offlineMaterialPlan-extracted.js' });
vm.runInContext(`${offlineCanHandleSource}\nthis.offlineCanHandle = offlineCanHandle;`, routeContext,
    { filename: 'offlineCanHandle-extracted.js' });
assert.strictEqual(typeof routeContext.offlineMaterialPlan, 'function', 'production material-plan function is unavailable');
assert.strictEqual(typeof routeContext.offlineCanHandle, 'function', 'production offline gate is unavailable');

function scopeOfRegion(region) {
    if (!region) return 'whole-body';
    if (region.part) return [].concat(region.part).join('+');
    if (region.everything || region.paintable) return 'whole-body';
    return 'unspecified';
}
function compactCompound(plan) {
    if (!plan) return null;
    return {
        kind: plan.kind,
        zones: (plan.zones || []).map(z => ({ name: z.name, scope: scopeOfRegion(z.region), finish: z.finish, pattern: z.pattern && z.pattern.id })),
        layers: (plan.layers || []).map(l => ({ layer: l.layer, name: l.name, key: l.key }))
    };
}
function compactEdit(plan) {
    if (!plan) return null;
    return {
        kind: plan.kind,
        unknown: plan.unknown || [],
        ops: (plan.ops || []).map(op => ({ action: op.action || op.op, target: op.target, property: op.property, value: op.value }))
    };
}
function applySummary(card, target) {
    let plan;
    try { plan = A.applyPlan(card, target, H.ENV); }
    catch (error) { return { error: error.message || String(error), scopes: [], steps: [] }; }
    const steps = (plan.steps || []).map(step => ({
        tool: step.tool,
        args: step.args,
        scope: step.args && step.args.region ? scopeOfRegion(step.args.region) :
            (step.args && ['z5', 'z6'].includes(step.args.zone_id) ? 'whole-body' : 'existing-zone')
    }));
    return { label: plan.label, error: plan.error, steps, scopes: [...new Set(steps.map(step => step.scope))] };
}
function compactAnswer(answer) {
    if (!answer) return null;
    return {
        kind: answer.kind,
        text: answer.text,
        target: answer.target && { id: answer.target.id, label: answer.target.label, region: answer.target.region },
        cards: (answer.cards || []).map(card => ({
            key: card.key,
            target: card.target && { id: card.target.id, label: card.target.label, region: card.target.region },
            apply: applySummary(card, card.target || answer.target || null)
        })),
        kits: (answer.kits || []).map(kit => ({
            name: kit.name,
            items: (kit.items || []).map(item => ({
                role: item.role,
                key: item.card && item.card.key,
                target: item.target && { id: item.target.id, label: item.target.label, region: item.target.region },
                apply: applySummary(item.card, item.target)
            }))
        }))
    };
}
function judgeScope(expected, part, scopes) {
    if (!scopes.length) return 'no mutation plan';
    const hasBody = scopes.includes('whole-body');
    const hasPart = scopes.includes(part);
    if (expected === 'part-only') return hasBody ? 'unsafe whole-body mutation plan' : (hasPart ? 'full part-only plan' : 'misdirected/partial plan');
    if (expected === 'whole-car') return hasBody ? 'full whole-car plan' : 'partial: whole-car base missing';
    if (expected === 'whole-car+hood') return hasBody && hasPart ? 'full body+part plan' : 'partial: body or hood scope missing';
    if (expected === 'multi-part-with-exclusion') return hasBody ? 'unsafe whole-body plan' : (scopes.includes('hood') && scopes.includes('roof') ? 'full two-part plan' : 'partial: named part missing');
    if (expected === 'correction-order-part-only' || expected === 'part-only-exclusion') return hasBody ? 'unsafe whole-body mutation plan' : (hasPart ? 'full part-only plan' : 'partial/no requested-part plan');
    if (expected === 'part-last-order') return hasBody && scopes.includes('roof') ? 'full body+part plan' : 'partial: body or roof scope missing';
    return 'scope review needed';
}
function expectedPart(intendedScope, ask) {
    // The fixture's scope category decides whether a single named part is
    // expected; use the fixture's request text only to identify that part.
    if (/^(?:part-only|correction-order-part-only|part-only-exclusion|part-last-order|whole-car\+hood|multi-part-with-exclusion)$/.test(intendedScope)) {
        if (/\bhood\b/i.test(ask)) return 'hood';
        if (/\broof\b/i.test(ask)) return 'roof';
    }
    return 'roof';
}

let providerCalls = 0;
function providerStub() { providerCalls++; throw new Error('provider calls are forbidden in this audit'); }
const cases = fixture.cases.map(c => {
    const cp = D.compoundPlan(c.ask);
    const edit = E.plan(c.ask, EDIT_ENV);
    const intent = A.classify(c.ask, null);
    const answer = intent ? A.answer(intent, H.ENV) : null;
    // Harness/extraction errors are fatal. They are not evidence that the
    // configured application would select a provider.
    const offlineEligible = routeContext.offlineCanHandle(c.ask);
    const configuredOfflineFirstRoute = offlineEligible ? 'offline' : 'provider-would-be-selected';
    // Deliberately do not call providerStub: the test observes the gate only.
    const directSignals = {
        compoundPlan: compactCompound(cp),
        editPlan: compactEdit(edit),
        advisorIntent: intent && { kind: intent.kind, stack: !!intent.stack, target: intent.target && intent.target.label },
        advisorAnswer: compactAnswer(answer),
        offlinePart: D.offlinePart(c.ask) && compactCompound({ zones: D.offlinePart(c.ask).zones || [] }),
        offlineElement: !!(D.offlineElement && D.offlineElement(c.ask)),
        offlineSpec: !!D.offlineSpec(c.ask),
        offlinePlan: !!D.offlinePlan(c.ask)
    };
    const answerSummary = compactAnswer(answer);
    let directSupport = 'unsupported/no complete offline plan demonstrated';
    let scopeJudgment = 'no mutation plan';
    if (cp && cp.zones && cp.zones.length) {
        const scopes = cp.zones.map(z => scopeOfRegion(z.region));
        scopeJudgment = judgeScope(c.intended_scope, expectedPart(c.intended_scope, c.ask), scopes);
        directSupport = scopeJudgment;
    } else if (answer && answerSummary.kits.length) {
        const scopes = answerSummary.kits[0].items.flatMap(item => item.apply.scopes);
        scopeJudgment = judgeScope(c.intended_scope, expectedPart(c.intended_scope, c.ask), scopes);
        directSupport = scopeJudgment;
    } else if (answer && answer.kind === 'recommend' && answerSummary.cards.length) {
        const scopes = answerSummary.cards.flatMap(card => card.apply.scopes);
        scopeJudgment = judgeScope(c.intended_scope, expectedPart(c.intended_scope, c.ask), scopes);
        directSupport = c.expected_capability.startsWith('offline-unsupported') || c.expected_capability.startsWith('offline-clarify')
            ? 'recommendation/clarification only; no paint action applied'
            : `recommendation-only: ${scopeJudgment}`;
    } else if (edit && edit.kind === 'ops' && (edit.unknown || []).length) {
        directSupport = `partial edit parse; unresolved terms: ${(edit.unknown || []).join(', ')}`;
    } else if (edit && edit.kind === 'ask') {
        directSupport = 'offline clarification candidate';
    } else if (edit && edit.kind === 'ops' && (edit.ops || []).length) {
        directSupport = 'edit operations candidate; scope requires operation review';
    }
    return {
        id: c.id,
        pair: c.pair,
        variant: c.variant,
        ask: c.ask,
        word_count: c.word_count,
        intended_scope: c.intended_scope,
        expected_capability: c.expected_capability,
        offlineCanHandle: !!offlineEligible,
        route_if_configured_and_offline_first: configuredOfflineFirstRoute,
        directSupport,
        scopeJudgment,
        directSignals
    };
});
assert.strictEqual(cases.length, fixture.cases.length, 'every frozen case must produce an observation');
assert.strictEqual(providerCalls, 0, 'no provider may be called');

const routeCounts = cases.reduce((out, c) => {
    const key = c.route_if_configured_and_offline_first;
    out[key] = (out[key] || 0) + 1;
    return out;
}, {});
const report = {
    title: 'AI helper offline coverage audit',
    generated_at: new Date().toISOString(),
    mode: 'diagnostic observations only; not route/native acceptance; no provider, browser, live paint, or production rebuild used',
    fixture: path.relative(ROOT, fixturePath).replace(/\\/g, '/'),
    fixture_sha256: crypto.createHash('sha256').update(fixtureBytes).digest('hex'),
    source_hashes: Object.fromEntries(['js/spb-pro-ai.js', 'js/spb-pro-edit.js', 'js/spb-pro-design.js', 'js/spb-pro-advisor.js', 'js/spb-ai-material-controls.js'].map(p => [p, crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, p))).digest('hex')])),
    routing_evidence: {
        offline_gate: 'js/spb-pro-ai.js:1365-1384',
        ask_gate: 'js/spb-pro-ai.js:1820-1822',
        extracted_function_sha256: crypto.createHash('sha256').update(offlineCanHandleSource).digest('hex'),
        extracted_material_plan_sha256: crypto.createHash('sha256').update(offlineMaterialPlanSource).digest('hex'),
        material_controls_module_sha256: crypto.createHash('sha256').update(materialControlsSource).digest('hex'),
        offline_ask_priority_function_sha256: crypto.createHash('sha256').update(offlineAskSource).digest('hex'),
        offline_ask_priority: 'Protected-part clarification first; then D.compoundPlan; then eligible E edit plan (unless editYieldsToStack); then advisor; otherwise offlineAskCore, whose order is look request, offlineSpec, offlinePart, offlineElement, offlinePlan.',
        setup_fallback: 'js/spb-pro-ai.js:1671 and :2205 tell unconfigured users to paste an OpenRouter key when no local branch claims the ask.',
        provider_calls: providerCalls
    },
    route_counts: routeCounts,
    historical_observations: {
        source_spb_pro_ai_sha256: '870b7a7b43672159df537c4f6d2e0d5dbbcd11e54cecd22651cad0d4cd20a1ca',
        route_counts: { offline: 13, 'provider-would-be-selected': 11 },
        long_requests_previously_observed_as_provider_ward_despite_local_plans: ['S01-long', 'S05-long'],
        provenance_limit: 'Historical corrected counts and the two long-request observations were reported from source 870b. Original raw audit rows are unavailable here; these are preserved historical observations, not measurements from this rerun.'
    },
    current_observations: {
        meaning: 'Fresh diagnostic observations from this rerun, using the production offlineMaterialPlan function and actual spb-ai-material-controls module before offlineCanHandle.',
        source_spb_pro_ai_sha256: crypto.createHash('sha256').update(proAiSource).digest('hex'),
        route_counts: routeCounts,
        case_count: cases.length,
        scope_oracle: 'For fixture scope categories that require a named part, the fixture ask identifies the part; S01 hood is not inferred as roof from the generic label part-only.',
        acceptance_limit: 'These are parser-gate observations only. They do not certify actual route execution, native preview behavior, or provider selection in a live session.'
    },
    notes: [
        'Harness exceptions are fatal and cannot be recorded as provider-ward routing. No provider function is called.',
        'Separate offline partials remain visible in per-case observations; offline eligibility means a local branch claims a prompt, not that its action fully satisfies intent.',
        'Fallback copy, car-map initialization, and historical coverage conclusions are context only and were not independently tested by this diagnostic rerun.',
        'This audit executes extracted production gate functions with stable helper state. It does not render paint or verify live application routing.'
    ],
    cases
};
const reportPath = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_W19_CURRENT_COVERAGE_AUDIT_2026-10-03.json');
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
assert(cases.length > 0, 'audit output must be non-empty');
console.log(`W19 diagnostic recorded ${cases.length} cases; provider calls=${providerCalls}; gate observations=${JSON.stringify(routeCounts)}; report=${path.relative(ROOT, reportPath)}`);
