// Runtime harness for TF18 + TF19: layer-fx mutators must push a layer
// stack undo entry so the painter can Ctrl+Z to revert.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-layer-flow.js'), 'utf8');

// Extract a function defined inside the IIFE (4-space indent).
function extract(name) {
    const needle = '    function ' + name + '(';
    const start = SRC.indexOf(needle);
    if (start === -1) throw new Error('Could not find ' + name);
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    return SRC.slice(start, i + 1);
}

function makeContext({ presetName }) {
    const calls = {
        _pushLayerStackUndo: [],
        recompositeFromLayers: 0,
        triggerPreviewRender: 0,
        safeToast: [],
        showToast: [],
    };
    const ctx = {
        _psdLayers: [
            { id: 'L1', name: 'Sponsor', effects: { dropShadow: { enabled: true, dx: 1 } } },
        ],
        _fxClipboard: { dropShadow: { enabled: true, dx: 99, dy: 99, blur: 0, opacity: 1, color: '#ff00ff' } },
        QUICK_FX_PRESETS: {
            'Drop Shadow': { dropShadow: { enabled: true, dx: 4, dy: 6, blur: 8, opacity: 0.55, color: '#000000' } },
        },
        _pushLayerStackUndo: function (label) { calls._pushLayerStackUndo.push(label); },
        recompositeFromLayers: function () { calls.recompositeFromLayers++; },
        triggerPreviewRender: function () { calls.triggerPreviewRender++; },
        safeToast: function (msg, isError) { calls.safeToast.push([msg, !!isError]); },
        showToast: function (msg, isError) { calls.showToast.push([msg, !!isError]); },
        JSON: JSON,
    };
    ctx._calls = calls;
    return ctx;
}

const results = {};

{
    const ctx = makeContext({});
    vm.createContext(ctx);
    const body = extract('pasteLayerFx');
    const beforeFx = JSON.stringify(ctx._psdLayers[0].effects);
    vm.runInContext(body + ";\nvar _r = pasteLayerFx('L1');", ctx, { filename: 'pasteLayerFx.runtime.js' });
    const afterFx = JSON.stringify(ctx._psdLayers[0].effects);
    results.tf18_paste_layer_fx = {
        ok: true,
        return_value: vm.runInContext('_r', ctx),
        layer_stack_undo_pushed: ctx._calls._pushLayerStackUndo.length === 1,
        undo_label: ctx._calls._pushLayerStackUndo[0],
        recomposite_called: ctx._calls.recompositeFromLayers === 1,
        preview_triggered: ctx._calls.triggerPreviewRender === 1,
        effects_changed: beforeFx !== afterFx,
    };
}

{
    const ctx = makeContext({ presetName: 'Drop Shadow' });
    vm.createContext(ctx);
    const body = extract('applyQuickFx');
    vm.runInContext(body + ";\napplyQuickFx('L1', 'Drop Shadow');", ctx, { filename: 'applyQuickFx.runtime.js' });
    results.tf19_apply_quick_fx = {
        ok: true,
        layer_stack_undo_pushed: ctx._calls._pushLayerStackUndo.length === 1,
        undo_label: ctx._calls._pushLayerStackUndo[0],
        recomposite_called: ctx._calls.recompositeFromLayers === 1,
        preview_triggered: ctx._calls.triggerPreviewRender === 1,
        toast_fired: ctx._calls.safeToast.some(t => /Drop Shadow/i.test(t[0])),
    };
}

console.log(JSON.stringify(results, null, 2));
