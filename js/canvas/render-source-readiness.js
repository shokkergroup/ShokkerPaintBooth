(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBRenderReadiness = api;
    if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
        const initialize = function () {
            api.refresh();
            const canvas = document.getElementById('paintCanvas');
            if (canvas && typeof MutationObserver !== 'undefined') {
                // Source publication resizes the canvas synchronously before
                // publishing ImageData. Observe dimensions, never brush pixels.
                new MutationObserver(api.refresh).observe(canvas, {attributes: true, attributeFilter: ['width', 'height']});
            }
        };
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
        else initialize();
    }
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    // SPB-93 09-08: early Render after reopen sent a 300x150 placeholder
    // against a 2048x2048 selection. Check published pixels before serialization.
    function reasonFor(state) {
        if (state.loading) return 'Paint is still loading. Render will be ready when loading finishes.';
        const pixels = state.pixels;
        if (!pixels || !Number.isInteger(pixels.width) || !Number.isInteger(pixels.height)
                || pixels.width < 1 || pixels.height < 1
                || !pixels.data || pixels.data.length !== pixels.width * pixels.height * 4
                || (state.canvas && (state.canvas.width !== pixels.width || state.canvas.height !== pixels.height))) {
            return 'Open a source paint file and wait for it to finish loading before rendering.';
        }
        return '';
    }

    function reason() {
        return reasonFor({
            loading: root._spbPsdImportInFlight === true,
            pixels: typeof paintImageData !== 'undefined' ? paintImageData : null,
            canvas: typeof document !== 'undefined' ? document.getElementById('paintCanvas') : null
        });
    }

    const heldButtons = new WeakMap();
    function refresh() {
        if (typeof document === 'undefined') return;
        const button = document.getElementById('btnRender');
        if (!button || button.classList.contains('terminate-mode')) return;
        const message = reason();
        if (message) {
            if (!heldButtons.has(button)) heldButtons.set(button, {
                disabled: button.disabled, html: button.innerHTML, title: button.title
            });
            button.disabled = true;
            const path = document.getElementById('paintFile');
            button.textContent = root._spbPsdImportInFlight === true || (path && path.value)
                ? 'LOADING PAINT…' : 'OPEN PAINT FIRST';
            button.title = message;
        } else if (heldButtons.has(button)) {
            const previous = heldButtons.get(button);
            button.disabled = previous.disabled;
            button.innerHTML = previous.html;
            button.title = previous.title;
            heldButtons.delete(button);
            // A preview skipped during import gets one normal debounced retry.
            if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview();
        }
    }

    function allowRender() {
        const message = reason();
        if (!message) return true;
        if (typeof showToast === 'function') showToast(message, true);
        refresh();
        return false;
    }
    return { reasonFor, reason, refresh, allowRender };
});
