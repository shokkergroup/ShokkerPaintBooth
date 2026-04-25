// Runtime harness for the apply* family of functions in paint-booth-6-ui-boot.js
//
// What this proves vs. a structural ratchet:
//   structural ratchet = "the string 'triggerPreviewRender' appears in the source body"
//   THIS harness       = "when the function is actually executed end-to-end against
//                          stubbed but realistic dependencies, the triggerPreviewRender
//                          spy gets called as part of the natural code flow."
//
// Both passes ⇒ the function ships preview refresh. Only the second ⇒ runtime trust.
//
// We extract function bodies textually (the originals live inside an IIFE so we
// cannot import them directly), then evaluate each in a fresh closure with stubs.
//
// Output: JSON to stdout summarizing which apply* functions called triggerPreviewRender.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-6-ui-boot.js'), 'utf8');

// ── extract one IIFE-scoped function body by name ────────────────────────────
// The functions live at indent 8 inside an IIFE; the next "        function "
// or end-of-IIFE bounds the body.
function extractFunction(name) {
    const needle = '        function ' + name + '(';
    const start = SRC.indexOf(needle);
    if (start === -1) throw new Error('Could not locate function ' + name);
    // Walk forward to the matching `}` at indent 8.
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    if (i >= SRC.length) throw new Error('Could not find closing brace for ' + name);
    return SRC.slice(start, i + 1);
}

// ── shared stub factory ──────────────────────────────────────────────────────
function makeContext(initialZones) {
    const calls = {
        triggerPreviewRender: 0,
        renderZones: 0,
        pushZoneUndo: 0,
        showToast: [],
        addRecentFinish: [],
        closeFinishBrowser: 0,
        hideFinishTooltip: 0,
        addZone: 0,
    };
    const ctx = {
        // collection state
        zones: initialZones,
        selectedZoneIndex: 0,
        finishBrowserTargetZone: 0,

        // spies
        triggerPreviewRender: function () { calls.triggerPreviewRender++; },
        renderZones: function () { calls.renderZones++; },
        pushZoneUndo: function () { calls.pushZoneUndo++; },
        showToast: function (msg, isError) { calls.showToast.push([msg, !!isError]); },
        addRecentFinish: function (id) { calls.addRecentFinish.push(id); },
        closeFinishBrowser: function () { calls.closeFinishBrowser++; },
        hideFinishTooltip: function () { calls.hideFinishTooltip++; },
        addZone: function () { calls.addZone++; ctx.zones.push({ name: 'New', color: null, finish: null, base: null, pattern: 'none' }); },

        // catalog stubs (apply* functions look these up)
        BASES: [{ id: 'chrome', name: 'Chrome', swatch: '#cccccc' }, { id: 'metallic', name: 'Metallic' }],
        PATTERNS: [{ id: 'carbon_fiber', name: 'Carbon Fiber' }],
        MONOLITHICS: [{ id: 'piano_black', name: 'Piano Black' }],
        QUICK_COLORS: [{ value: 'red' }],
        LIVERY_TEMPLATES: [],

        // colorMode helpers (used by applyChatZones)
        chatHexToRgb: function (hex) { return [255, 0, 0]; },

        // openDualShiftModal etc. — not invoked in our scenarios
        openDualShiftModal: function () {},

        // misc
        confirm: function () { return true; },
        autoSave: function () {},
        _spbShouldAutoFillBaseColor: function () { return false; },

        // localStorage / combo store stubs (applyCombo)
        getComboStore: function () {
            return {
                'My Combo': { finish: null, base: 'metallic', pattern: 'carbon_fiber', intensity: '80', scale: 1.5 },
                'Mono Combo': { finish: 'piano_black', intensity: '100', scale: 1.0 },
            };
        },

        // for applyFinishFromBrowser
        // (no extras needed beyond the above)
    };
    // expose calls so the test can read them
    ctx._calls = calls;
    return ctx;
}

// ── runner ───────────────────────────────────────────────────────────────────
function runOne(name, callExpr, initialZones) {
    let body;
    try { body = extractFunction(name); }
    catch (e) { return { name, ok: false, error: 'extract: ' + e.message }; }

    const ctx = makeContext(initialZones);
    const script = body + '\n;' + callExpr + ';';
    try {
        vm.createContext(ctx);
        vm.runInContext(script, ctx, { filename: name + '.runtime.js', timeout: 2000 });
        return {
            name,
            ok: true,
            triggered_preview_render: ctx._calls.triggerPreviewRender > 0,
            preview_call_count: ctx._calls.triggerPreviewRender,
            rendered_zones: ctx._calls.renderZones,
            pushed_undo: ctx._calls.pushZoneUndo,
            toasts: ctx._calls.showToast,
            zone_state_after: ctx.zones.map(z => ({
                name: z.name, color: z.color, finish: z.finish, base: z.base, pattern: z.pattern,
                colorMode: z.colorMode, pickerColor: z.pickerColor,
                intensity: z.intensity, scale: z.scale,
            })),
        };
    } catch (e) {
        return { name, ok: false, error: 'execute: ' + e.message, stack: e.stack };
    }
}

// Scenario: apply a base+pattern from the finish browser to the first zone.
const sFinish = runOne(
    'applyFinishFromBrowser',
    "applyFinishFromBrowser('chrome', 'carbon_fiber', null)",
    [{ name: 'Hood', color: null, finish: null, base: null, pattern: null }]
);

// Scenario: apply a saved combo to the selected zone.
const sCombo = runOne(
    'applyCombo',
    "applyCombo('My Combo')",
    [{ name: 'Roof', color: null, finish: null, base: null, pattern: null }]
);

// Scenario: apply a chat-driven configuration that mutates one zone.
const sChat = runOne(
    'applyChatZones',
    "applyChatZones([{ name: 'ChatHood', color: 'red', finish: 'piano_black' }])",
    [{ name: 'Existing', color: null, finish: null, base: null, pattern: null,
       colorMode: 'none', colors: [], lockBase: false, lockPattern: false,
       lockIntensity: false, lockColor: false, scale: 1.0, patternOpacity: 100,
       patternStack: [], wear: 0, muted: false, pickerColor: '#3366ff',
       pickerTolerance: 40, regionMask: null, customSpec: null, customPaint: null,
       customBright: null }]
);

// Scenario: apply a harmony color from zone 0 to (auto-target) zone 1.
const sHarmony = runOne(
    'applyHarmonyColor',
    "applyHarmonyColor(0, '#ff8800')",
    [
        { name: 'Source', colorMode: 'picker', color: { color_rgb: [10,20,30], tolerance: 40 }, colors: [], pickerColor: '#0a141e', pickerTolerance: 40 },
        { name: 'Empty', colorMode: 'none', color: null, colors: [], pickerColor: '#3366ff', pickerTolerance: 40 },
    ]
);

console.log(JSON.stringify({
    finish_from_browser: sFinish,
    combo: sCombo,
    chat_zones: sChat,
    harmony: sHarmony,
}, null, 2));
