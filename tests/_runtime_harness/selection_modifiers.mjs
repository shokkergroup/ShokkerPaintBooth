// Runtime harness for selection modifier family TF9-TF11:
//   growSelection / shrinkSelection / smoothSelection
//
// Pre-fix: each called pushUndo() — a function that does NOT exist in the
// canonical 3-copy build (only in the legacy paint-booth-app.js bundle).
// The typeof-guard masked the missing reference, so selection grow/shrink/
// smooth were SILENTLY UNREVERTABLE.
//
// Fix: replaced with pushZoneUndo (which IS defined in state-zones.js
// and is what every sister selection mutator uses).
//
// Two scenarios per function:
//   pushUndo_only_defined  — sets pushUndo as a spy, leaves pushZoneUndo undefined.
//                             Pre-fix: would push to pushUndo. Post-fix: must push to
//                             pushZoneUndo (which doesn't exist) so NO undo fires.
//                             We assert the post-fix behavior: pushUndo NOT called,
//                             zone mask still mutated.
//   pushZoneUndo_defined   — defines pushZoneUndo as the spy. Verify the post-fix
//                             call lands on pushZoneUndo, not pushUndo.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-3-canvas.js'), 'utf8');

function extractTopLevelFunction(name) {
    const needle = '\nfunction ' + name + '(';
    const start = SRC.indexOf(needle) + 1;
    if (start === 0) throw new Error('Could not locate function ' + name);
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    return SRC.slice(start, i + 1);
}

function makeContext({ provideZoneUndo, provideLegacyPushUndo }) {
    const W = 8, H = 8;
    const calls = {
        showToast: [],
        pushZoneUndo: [],
        pushUndo: [],
    };
    // Build a 3x3 selection in the middle of the 8x8 mask so grow/shrink/smooth
    // have something to operate on.
    const mask = new Uint8Array(W * H);
    for (let y = 3; y < 6; y++) {
        for (let x = 3; x < 6; x++) {
            mask[y * W + x] = 255;
        }
    }
    const ctx = {
        document: {
            getElementById: function (id) {
                if (id === 'paintCanvas') return { width: W, height: H };
                return null;
            },
        },
        showToast: function (msg, isError) { calls.showToast.push([msg, !!isError]); },
        zones: [{ name: 'Hood', regionMask: mask }],
        selectedZoneIndex: 0,
        renderRegionOverlay: function () {},
    };
    if (provideZoneUndo) ctx.pushZoneUndo = function (label) { calls.pushZoneUndo.push(label); };
    if (provideLegacyPushUndo) ctx.pushUndo = function (label) { calls.pushUndo.push(label); };
    ctx._calls = calls;
    ctx._mask = mask;
    return ctx;
}

function snapshotMask(mask) { return Array.from(mask); }

function runOne(funcName, scenario) {
    let opts;
    if (scenario === 'pushZoneUndo_defined') opts = { provideZoneUndo: true, provideLegacyPushUndo: true };
    else if (scenario === 'only_legacy_push_undo') opts = { provideZoneUndo: false, provideLegacyPushUndo: true };
    else opts = { provideZoneUndo: true, provideLegacyPushUndo: false };

    const ctx = makeContext(opts);
    const before = snapshotMask(ctx._mask);
    const body = extractTopLevelFunction(funcName);
    const script = body + '\n;' + funcName + '(' + (funcName === 'smoothSelection' ? '' : '2') + ');';
    let error = null;
    try {
        vm.createContext(ctx);
        vm.runInContext(script, ctx, { filename: funcName + '.runtime.js', timeout: 2000 });
    } catch (e) {
        error = { message: e.message };
    }
    const after = snapshotMask(ctx._mask);
    return {
        func: funcName,
        scenario,
        ok: error === null,
        error,
        pushZoneUndo: ctx._calls.pushZoneUndo,
        legacy_pushUndo: ctx._calls.pushUndo,
        showToast: ctx._calls.showToast,
        mask_changed: JSON.stringify(before) !== JSON.stringify(after),
    };
}

const FUNCS = ['growSelection', 'shrinkSelection', 'smoothSelection'];
const SCENARIOS = ['pushZoneUndo_defined', 'only_legacy_push_undo'];
const results = {};
for (const f of FUNCS) {
    results[f] = {};
    for (const s of SCENARIOS) {
        results[f][s] = runOne(f, s);
    }
}
console.log(JSON.stringify(results, null, 2));
