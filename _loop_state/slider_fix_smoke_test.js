// Slider Fix Smoke Test (2026-05-27, Tick 2)
// Verifies the 6 new setters + the SCALE_BASE_MIN=0.05 floor.
//
// Strategy: paint-booth-2-state-zones.js is a browser script with many
// globals (DOM, renderZones, triggerPreviewRender, pushZoneUndo, etc.).
// We can't `require` it. Instead we extract the relevant function source
// + constants via regex and eval them into a sandbox with stubs.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(
    path.join(__dirname, '..', 'paint-booth-2-state-zones.js'),
    'utf8'
);

function extractRegion(src, startMarker, endMarker) {
    const s = src.indexOf(startMarker);
    if (s < 0) throw new Error('start marker not found: ' + startMarker);
    const e = src.indexOf(endMarker, s);
    if (e < 0) throw new Error('end marker not found: ' + endMarker);
    return src.slice(s, e);
}

// Pull constants line
const constLine = SRC.match(/const SCALE_PATTERN_MIN[^\n]+\nconst SCALE_BASE_MIN[^\n]+\nconst SCALE_OVERLAY_MIN[^\n]+\n/);
if (!constLine) throw new Error('constants block not found');

// Pull roundToStep
const roundFn = SRC.match(/function roundToStep\([^)]*\)[^}]+\}/);
if (!roundFn) throw new Error('roundToStep not found');

// Pull each setter/stepper/resetter
function pullFn(name) {
    const re = new RegExp('function ' + name + '\\([^)]*\\) \\{[\\s\\S]*?\\n\\}', 'm');
    const m = SRC.match(re);
    if (!m) throw new Error('Could not extract ' + name);
    return m[0];
}

const fns = [
    'setZoneBaseScale', 'stepZoneBaseScale', 'resetZoneBaseScale',
    'setZoneBaseColorScale', 'stepZoneBaseColorScale', 'resetZoneBaseColorScale',
    'setZoneSpecScale', 'stepZoneSpecScale', 'resetZoneSpecScale',
].map(pullFn).join('\n\n');

// Build sandbox
const callLog = [];
const undoLog = [];
const sandbox = {
    zones: [
        { baseScale: 1.0, baseColorScale: 1.0, specScale: 1.0, name: 'A' },
        { baseScale: 1.0, baseColorScale: 1.0, specScale: 1.0, name: 'B' },
    ],
    document: {
        getElementById: () => null,
        querySelectorAll: () => ({ forEach: () => {} }),
    },
    console,
    pushZoneUndo: (msg, coalesce) => { undoLog.push({ msg, coalesce: !!coalesce }); },
    triggerPreviewRender: () => { callLog.push('triggerPreviewRender'); },
    renderZones: () => { callLog.push('renderZones'); },
    applyPlacementPatternTransform: () => {},
    isNaN: globalThis.isNaN,
    parseFloat: globalThis.parseFloat,
    parseInt: globalThis.parseInt,
    Math: globalThis.Math,
};
vm.createContext(sandbox);
vm.runInContext(constLine[0] + '\n' + roundFn[0] + '\n' + fns, sandbox);

// ---- Tests ----
const results = [];
function assert(name, cond, detail) {
    results.push({ name, pass: !!cond, detail });
}
function reset(z) {
    sandbox.zones[0].baseScale = 1.0; sandbox.zones[0].baseColorScale = 1.0; sandbox.zones[0].specScale = 1.0;
    sandbox.zones[1].baseScale = 1.0; sandbox.zones[1].baseColorScale = 1.0; sandbox.zones[1].specScale = 1.0;
}

const inputs = [0.25, 0.50, 0.75, 1.0, 1.5, 2.0];
const setters = [
    ['setZoneBaseScale', 'baseScale'],
    ['setZoneBaseColorScale', 'baseColorScale'],
    ['setZoneSpecScale', 'specScale'],
];

// Test 1: each setter lands the value on the right zone field, NOT a global.
for (const [setterName, field] of setters) {
    reset();
    const before = Object.keys(sandbox).filter(k => k.toLowerCase().includes(field.toLowerCase()) && typeof sandbox[k] !== 'function');
    for (const val of inputs) {
        sandbox[setterName](0, val);
        const got = sandbox.zones[0][field];
        const expected = Math.round(val / 0.05) * 0.05;
        assert(`${setterName}(0, ${val}) -> zones[0].${field} ≈ ${expected.toFixed(2)} (got ${got.toFixed(4)})`,
            Math.abs(got - expected) < 1e-9);
    }
    const after = Object.keys(sandbox).filter(k => k.toLowerCase().includes(field.toLowerCase()) && typeof sandbox[k] !== 'function');
    assert(`${setterName} did NOT create a global '${field}'`,
        before.length === after.length && !sandbox[field]);
}

// Test 2: sub-1.0 values are NOT clamped to 1.0
for (const [setterName, field] of setters) {
    reset();
    sandbox[setterName](0, 0.05);
    assert(`${setterName}(0, 0.05) -> zones[0].${field} == 0.05 (NOT clamped to 1.0)`,
        Math.abs(sandbox.zones[0][field] - 0.05) < 1e-9,
        `got ${sandbox.zones[0][field]}`);
    sandbox[setterName](0, 0.25);
    assert(`${setterName}(0, 0.25) -> zones[0].${field} == 0.25 (NOT clamped to 1.0)`,
        Math.abs(sandbox.zones[0][field] - 0.25) < 1e-9,
        `got ${sandbox.zones[0][field]}`);
}

// Test 3: setting on zone A does not affect zone B
for (const [setterName, field] of setters) {
    reset();
    sandbox[setterName](0, 0.50);
    assert(`${setterName}(0, 0.50) leaves zones[1].${field} == 1.0`,
        Math.abs(sandbox.zones[1][field] - 1.0) < 1e-9,
        `zones[1].${field} = ${sandbox.zones[1][field]}`);
    sandbox[setterName](1, 1.75);
    assert(`${setterName}(1, 1.75) leaves zones[0].${field} == 0.50 (was set above)`,
        Math.abs(sandbox.zones[0][field] - 0.50) < 1e-9,
        `zones[0].${field} = ${sandbox.zones[0][field]}`);
    assert(`${setterName}(1, 1.75) lands on zones[1].${field}`,
        Math.abs(sandbox.zones[1][field] - 1.75) < 1e-9,
        `zones[1].${field} = ${sandbox.zones[1][field]}`);
}

// Test 4: reset puts it back to 1.0
const resetters = [
    ['resetZoneBaseColorScale', 'baseColorScale'],
    ['resetZoneSpecScale', 'specScale'],
];
for (const [r, field] of resetters) {
    sandbox.zones[0][field] = 0.25;
    sandbox[r](0);
    assert(`${r}(0) -> zones[0].${field} == 1.0`,
        Math.abs(sandbox.zones[0][field] - 1.0) < 1e-9,
        `got ${sandbox.zones[0][field]}`);
}

// Test 5: step deltas walk the value
reset();
sandbox.zones[0].baseColorScale = 1.0;
sandbox.stepZoneBaseColorScale(0, -1);
assert(`stepZoneBaseColorScale(0, -1) from 1.0 -> 0.95`,
    Math.abs(sandbox.zones[0].baseColorScale - 0.95) < 1e-9,
    `got ${sandbox.zones[0].baseColorScale}`);
sandbox.zones[0].specScale = 0.10;
sandbox.stepZoneSpecScale(0, -1);
assert(`stepZoneSpecScale(0, -1) from 0.10 -> 0.05`,
    Math.abs(sandbox.zones[0].specScale - 0.05) < 1e-9,
    `got ${sandbox.zones[0].specScale}`);

// ---- Report ----
const passCount = results.filter(r => r.pass).length;
const failCount = results.length - passCount;
const lines = [];
lines.push('Slider Fix Smoke Test — ' + new Date().toISOString());
lines.push('=================================================');
lines.push(`Total: ${results.length}  PASS: ${passCount}  FAIL: ${failCount}`);
lines.push('');
for (const r of results) {
    lines.push(`[${r.pass ? 'PASS' : 'FAIL'}] ${r.name}${r.detail && !r.pass ? '  -- ' + r.detail : ''}`);
}
lines.push('');
lines.push('SCALE_BASE_MIN constant (extracted):');
lines.push(constLine[0].trim());

const out = lines.join('\n');
console.log(out);
fs.writeFileSync(path.join(__dirname, 'slider_fix_smoke_test_results.txt'), out, 'utf8');
process.exit(failCount === 0 ? 0 : 1);
