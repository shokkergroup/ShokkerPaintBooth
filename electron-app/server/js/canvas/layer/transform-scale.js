/* SPB-93 2026-09-08 — Photoshop-like Layer handle scaling.
   Ordinary drags anchor the opposite edge/corner; Alt anchors the center.
   Geometry is always derived from the drag start so modifier changes do not drift. */
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLayerTransformScale = api;
})(typeof window === 'object' ? window : globalThis, function() {
    'use strict';
    function apply(s, dx, dy, modifiers) {
        if (s?.target !== 'layer' || !/^(n|s|e|w|ne|nw|se|sw)$/.test(s.dragging)) return false;
        const hx = s.dragging.includes('e') ? 1 : s.dragging.includes('w') ? -1 : 0;
        const hy = s.dragging.includes('s') ? 1 : s.dragging.includes('n') ? -1 : 0;
        const rad = s.dragStartRot * Math.PI / 180, cos = Math.cos(rad), sin = Math.sin(rad);
        const localX = dx * cos + dy * sin, localY = -dx * sin + dy * cos;
        const w = s.dragStartBoxW, h = s.dragStartBoxH;
        const centered = !!modifiers.altKey, multiplier = centered ? 2 : 1;
        let newW = w + hx * localX * multiplier, newH = h + hy * localY * multiplier;
        s.constrained = !!(hx && hy && (modifiers.shiftKey || s.aspectLocked));
        if (s.constrained) {
            // Project the drag onto the aspect-locked corner's diagonal.
            const factor = (newW * w + newH * h) / (w * w + h * h);
            const bounded = Math.max(factor, 10 / w, 10 / h);
            newW = w * bounded; newH = h * bounded;
        } else { newW = Math.max(10, newW); newH = Math.max(10, newH); }
        const offsetX = centered ? 0 : hx * (newW - w) / 2;
        const offsetY = centered ? 0 : hy * (newH - h) / 2;
        s.centerX = s.dragStartCX + offsetX * cos - offsetY * sin;
        s.centerY = s.dragStartCY + offsetX * sin + offsetY * cos;
        s.boxW = newW; s.boxH = newH;
        s.scaleX = (s.dragStartSX < 0 ? -1 : 1) * newW / s.origBoxW;
        s.scaleY = (s.dragStartSY < 0 ? -1 : 1) * newH / s.origBoxH;
        if (s.subRect) s.subRect = {x1:s.centerX-newW/2,y1:s.centerY-newH/2,x2:s.centerX+newW/2,y2:s.centerY+newH/2};
        return true;
    }
    return Object.freeze({apply});
});
