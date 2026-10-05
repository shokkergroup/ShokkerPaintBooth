/* SPB-93 2026-09-08: Zone materials persist one uniform scale.
 * Every handle must resize that same material frame, including vertical edges.
 * Opposite side anchors normally; Alt anchors the center. Layer stretch is separate. */
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBZoneTransformScale = api;
})(typeof window === 'object' ? window : globalThis, function() {
    'use strict';
    function apply(s, dx, dy, modifiers) {
        if (!s || s.target === 'layer' || !/^(n|s|e|w|ne|nw|se|sw)$/.test(s.dragging)) return false;
        const hx = s.dragging.includes('e') ? 1 : s.dragging.includes('w') ? -1 : 0;
        const hy = s.dragging.includes('s') ? 1 : s.dragging.includes('n') ? -1 : 0;
        const rad = s.dragStartRot * Math.PI / 180, cos = Math.cos(rad), sin = Math.sin(rad);
        const x = dx * cos + dy * sin, y = -dx * sin + dy * cos;
        const w = s.dragStartBoxW, h = s.dragStartBoxH;
        if (!(w > 0 && h > 0)) return false;
        const centered = !!modifiers.altKey, multiplier = centered ? 2 : 1;
        const factor = hx && hy
            ? 1 + multiplier * (hx * x * w + hy * y * h) / (w * w + h * h)
            : 1 + multiplier * (hx ? hx * x / w : hy * y / h);
        const bounded = Math.max(factor, 10 / w, 10 / h);
        const newW = w * bounded, newH = h * bounded;
        const ox = centered ? 0 : hx * (newW - w) / 2;
        const oy = centered ? 0 : hy * (newH - h) / 2;
        s.centerX = s.dragStartCX + ox * cos - oy * sin;
        s.centerY = s.dragStartCY + ox * sin + oy * cos;
        s.boxW = newW; s.boxH = newH; s.constrained = true;
        s.scaleX = (s.origScaleX || 1) * newW / (s.origBoxW || w);
        s.scaleY = (s.origScaleY || 1) * newH / (s.origBoxH || h);
        if (s.subRect) s.subRect = {x1:s.centerX-newW/2,y1:s.centerY-newH/2,x2:s.centerX+newW/2,y2:s.centerY+newH/2};
        return true;
    }
    return Object.freeze({apply});
});
