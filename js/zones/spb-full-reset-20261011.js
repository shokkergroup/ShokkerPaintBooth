/* [SPB-FULL-RESET 2026-10-11] Reset All Zones = the WHOLE canvas back to how the car loaded.
 *
 * WHY (owner, 2026-10-11): "the SPEC BRUSH is STAYING over the number where I brushed it no matter what" — after a server
 * restart, Reset All Zones AND a hard reload. Root cause: the brushed material / spec layer (Material Brush, Spec Brush,
 * Wear Brush, Spec Sculpt 2) lives OUTSIDE the zones and is autosaved to IndexedDB `spb_rev_material_v1` keyed by the car
 * file (js/rev/material/rev-material-persist.js), then restored on every load. Reset All Zones only replaced the zones.
 * Owner rule: "Reset All Zones should reset the entire canvas - back to normal. Where EVERYTHING ELSE is gloss. Nothing else
 * on the car is selected. All Layers go back to normal."
 *
 * WHAT spbResetCanvasExtras() clears (each step guarded; a missing tool is skipped):
 *   1. brushed material / spec / wear strokes + the Spec Sculpt look (SPBRevMaterial.clearAll(): one undo step; the autosave
 *      then writes "empty", which DELETES the stored record, so a reload no longer brings it back)
 *   2. Race Wear and Car-Space Fade (restore(null) = the "document without wear / fade" path those tools already use)
 *   3. Colourway variants (its helper layer removed)
 *   4. Layer materials (layer.spbMaterial, undoable through the layer stack)
 *   5. layer visibility back to how the file loaded (importVisible)
 * Only the Reset All Zones BUTTON calls this (resetAllZonesToDefaults); the AI's zone reset does not touch the buyer's brush work.
 * Kill switch: window.SPB_FULL_RESET_OFF = true or localStorage SPB_FULL_RESET_OFF = '1' -> Reset All Zones resets zones only (old behaviour).
 */
(function (root) {
    'use strict';
    if (!root) return;
    function off() {
        try { if (root.SPB_FULL_RESET_OFF) return true; } catch (_) {}
        try { return root.localStorage.getItem('SPB_FULL_RESET_OFF') === '1'; } catch (_) { return false; }
    }
    function layers() { try { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; } catch (_) { return []; } }
    function step(out, name, fn) {
        try { const r = fn(); if (r) out.cleared.push(name); } catch (e) { out.errors.push(name + ': ' + (e && e.message || e)); console.warn('[SPB-FULL-RESET]', name, e); }
    }
    function spbResetCanvasExtras() {
        const out = { cleared: [], errors: [], off: off() };
        if (out.off) return out;
        step(out, 'brushed material / spec', function () {
            const M = root.SPBRevMaterial; if (!M || (M.off && M.off()) || M.isEmpty()) return false;
            return M.clearAll();
        });
        step(out, 'race wear', function () {
            const W = root.SpbRevWearUI; if (!W || !W.serialize || !W.serialize()) return false;
            W.restore(null); return true;
        });
        step(out, 'fade', function () {
            const F = root.SpbRevFadeUI; if (!F || !F.state || !(F.state.recs || []).length) return false;
            F.restore(null); return true;
        });
        step(out, 'colourway', function () {
            const C = root.SPBRevColourway; if (!C || C.off || !C.isCw) return false;
            const had = layers().some(function (l) { return C.isCw(l); }) || (C.active && C.active());
            if (!had) return false;
            if (C.active && C.active()) C.close(false);
            C.restore({ layer: null });
            return true;
        });
        step(out, 'layer materials', function () {
            const LM = root.SPBRevLayerMat; if (!LM || (LM.off && LM.off())) return false;
            const ids = layers().filter(function (l) { return l && l[LM.FIELD]; }).map(function (l) { return l.id; });
            if (!ids.length) return false;
            const r = LM.assign(ids, null, { label: 'Reset All Zones: layer materials' });
            return !!(r && r.changed);
        });
        step(out, 'layer visibility', function () {
            let n = 0;
            layers().forEach(function (l) {
                if (!l || typeof l.importVisible !== 'boolean') return;
                if (l.visible !== l.importVisible) { l.visible = l.importVisible; n++; }
            });
            if (!n) return false;
            root._spbLayerRev = (root._spbLayerRev | 0) + 1;
            try { if (typeof root.renderLayerPanel === 'function') root.renderLayerPanel(); } catch (_) {}
            try { if (typeof root.recompositeFromLayers === 'function') root.recompositeFromLayers(); } catch (_) {}
            return true;
        });
        try { if (typeof root.triggerPreviewRender === 'function') root.triggerPreviewRender(); } catch (_) {}
        root.__spbLastFullReset = out;
        return out;
    }
    root.spbResetCanvasExtras = spbResetCanvasExtras;
    root.spbFullResetOff = off;
})(typeof window !== 'undefined' ? window : null);
