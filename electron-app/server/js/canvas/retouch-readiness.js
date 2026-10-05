/* SPB-93 / 2026-09-07 — owner: tools should work like Photoshop.
 * Menu guidance shares activation authority with dispatch. Opening a menu must
 * never mutate the document; recovery must verify its result before claiming it.
 */
(function () {
    'use strict';
    window.spbRetouchGateState = function () {
        const activation = typeof getToolbarToolActivation === 'function'
            ? getToolbarToolActivation('colorbrush') : null;
        if (activation && activation.allowed) return { ok: true, why: '' };
        const selected = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
        const reason = selected && selected.locked
            ? 'The selected layer is locked. Unlock it or select an unlocked layer to retouch its pixels.'
            : 'Select an editable layer in Layers, or open a layered paint file, to retouch existing pixels.';
        return { ok: false, why: reason + ' A blank layer is for new Color Brush painting; it has no pixels to Recolor, Heal, Smudge or Burn.' };
    };

    window.spbUpdateRetouchGate = function () {
        const menu = document.getElementById('spbRetouchMenu');
        const gate = document.getElementById('spbRetouchGate');
        const why = document.getElementById('spbRetouchGateWhy');
        if (!menu || !gate || !why) return;
        const state = window.spbRetouchGateState();
        gate.style.display = state.ok ? 'none' : '';
        menu.classList.toggle('spb-gate-blocked', !state.ok);
        why.textContent = state.why;
    };

    window.spbRetouchGateFix = function () {
        // The labeled action is explicit: create new paint, never silently
        // unlock, replace or flatten the selected artwork.
        const layer = typeof addBlankLayer === 'function' ? addBlankLayer() : null;
        if (layer && typeof setCanvasMode === 'function') setCanvasMode('colorbrush');
        window.spbUpdateRetouchGate();
        const ready = !!layer && window.spbRetouchGateState().ok && window.canvasMode === 'colorbrush';
        if (typeof showToast === 'function') showToast(ready
            ? 'Color Brush ready on the new blank layer. Drag on SOURCE to paint.'
            : 'Color Brush is not ready. Select an unlocked layer with loaded pixels and try again.', !ready);
        if (ready) {
            const menu = document.getElementById('spbRetouchMenu');
            if (menu) menu.open = false;
        }
        return ready;
    };
}());
