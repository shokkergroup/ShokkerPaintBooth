(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBClipboardLayer = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // SPB-93 tick 40 (2026-07-16), owner verdict: tools feel "jinky/off".
    // Before: every layer-origin copy inherited sourceLayerId, so Paste/Ctrl+J
    // could masquerade as a temporary Transform Selection lift. After: only an
    // explicit linkSourceLayer request can create that destructive bake-back link.
    function linkedSourceLayerId(data, options) {
        if (!data || options?.linkSourceLayer !== true) return null;
        const id = data.sourceLayerId;
        return typeof id === 'string' && id ? id : null;
    }

    // SPB-93 tick 44 (2026-07-16), owner verdict: tools must feel Photoshop-quality.
    // Normal Paste targets the active selection center, then the visible canvas
    // center. Paste in Place remains explicit and exact for livery alignment.
    function resolvePastePlacement(data, context) {
        if (!data) return null;
        const ctx = context || {};
        const width = Math.max(1, Math.floor(Number(data.width) || 0));
        const height = Math.max(1, Math.floor(Number(data.height) || 0));
        const canvasWidth = Math.max(1, Math.floor(Number(ctx.canvasWidth) || width));
        const canvasHeight = Math.max(1, Math.floor(Number(ctx.canvasHeight) || height));
        const mode = String(ctx.mode || 'auto').toLowerCase();

        if (mode === 'in-place') {
            return {
                x: Math.round(Number(data.offsetX) || 0),
                y: Math.round(Number(data.offsetY) || 0),
                reason: 'in-place',
            };
        }

        let centerX;
        let centerY;
        let reason;
        const selection = ctx.selection;
        if (selection && Number.isFinite(Number(selection.minX)) && Number.isFinite(Number(selection.maxX)) &&
            Number.isFinite(Number(selection.minY)) && Number.isFinite(Number(selection.maxY))) {
            centerX = (Number(selection.minX) + Number(selection.maxX) + 1) / 2;
            centerY = (Number(selection.minY) + Number(selection.maxY) + 1) / 2;
            reason = 'selection';
        } else if (ctx.viewportCenter && Number.isFinite(Number(ctx.viewportCenter.x)) && Number.isFinite(Number(ctx.viewportCenter.y))) {
            centerX = Number(ctx.viewportCenter.x);
            centerY = Number(ctx.viewportCenter.y);
            reason = 'viewport';
        } else {
            centerX = canvasWidth / 2;
            centerY = canvasHeight / 2;
            reason = 'canvas';
        }

        let x = Math.round(centerX - width / 2);
        let y = Math.round(centerY - height / 2);
        x = width <= canvasWidth ? Math.max(0, Math.min(canvasWidth - width, x)) : 0;
        y = height <= canvasHeight ? Math.max(0, Math.min(canvasHeight - height, y)) : 0;
        return { x, y, reason };
    }

    return Object.freeze({ linkedSourceLayerId, resolvePastePlacement });
});
