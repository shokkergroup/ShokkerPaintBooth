(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBBrushFootprint = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // SPB-93 tick 38 (2026-07-16), owner verdict: tools still feel "jinky/off"
    // and should behave more like painters expect. Source/live audit found 10
    // advertised brush-family kernels with private or round-only footprints.
    // Contract movement: 10 shape-divergent kernels -> one shared footprint.
    const VALID_SHAPES = new Set(['round', 'square', 'diamond', 'slash', 'noise']);

    function normalizeShape(value) {
        const normalized = String(value || 'round').toLowerCase();
        return VALID_SHAPES.has(normalized) ? normalized : 'round';
    }

    function create(shapeValue, radiusValue, randomFn) {
        const shape = normalizeShape(shapeValue);
        const radius = Math.max(1, Math.abs(Number(radiusValue) || 1));
        const radiusSquared = radius * radius;
        const random = typeof randomFn === 'function' ? randomFn : Math.random;

        function distanceSquared(dxValue, dyValue) {
            const dx = Number(dxValue) || 0;
            const dy = Number(dyValue) || 0;
            const ax = Math.abs(dx);
            const ay = Math.abs(dy);
            if (shape === 'square') {
                const distance = Math.max(ax, ay);
                return distance * distance;
            }
            if (shape === 'diamond') {
                const distance = ax + ay;
                return distance * distance;
            }
            if (shape === 'slash') {
                const along = Math.max(ax, ay);
                const across = Math.abs(dx - dy) / 0.3;
                const distance = Math.max(along, across);
                return distance * distance;
            }
            return dx * dx + dy * dy;
        }

        function contains(dxValue, dyValue, euclideanSquared) {
            const dx = Number(dxValue) || 0;
            const dy = Number(dyValue) || 0;
            const ax = Math.abs(dx);
            const ay = Math.abs(dy);
            const dist2 = Number.isFinite(euclideanSquared)
                ? euclideanSquared
                : dx * dx + dy * dy;
            if (ax > radius || ay > radius) return false;
            if (shape === 'square') return true;
            if (shape === 'diamond') return ax + ay <= radius;
            if (shape === 'slash') return Math.abs(dx - dy) <= radius * 0.3;
            if (dist2 > radiusSquared) return false;
            return shape !== 'noise' || random() <= 0.6;
        }

        function tracePath(ctx, cx, cy) {
            if (!ctx || typeof ctx.beginPath !== 'function') return false;
            ctx.beginPath();
            if (shape === 'square') {
                ctx.rect(cx - radius, cy - radius, radius * 2, radius * 2);
            } else if (shape === 'diamond') {
                ctx.moveTo(cx, cy - radius);
                ctx.lineTo(cx + radius, cy);
                ctx.lineTo(cx, cy + radius);
                ctx.lineTo(cx - radius, cy);
                ctx.closePath();
            } else if (shape === 'slash') {
                const thickness = radius * 0.3;
                ctx.moveTo(cx - radius, cy - radius);
                ctx.lineTo(cx - radius, cy - radius + thickness);
                ctx.lineTo(cx + radius - thickness, cy + radius);
                ctx.lineTo(cx + radius, cy + radius);
                ctx.lineTo(cx + radius, cy + radius - thickness);
                ctx.lineTo(cx - radius + thickness, cy - radius);
                ctx.closePath();
            } else {
                // Noise has a round outer envelope; its granular inclusion is
                // supplied by contains() in pixel kernels.
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
            }
            return true;
        }

        return Object.freeze({
            shape,
            radius,
            radiusSquared,
            contains,
            distanceSquared,
            tracePath
        });
    }

    function currentShape(documentLike, shapeOverride) {
        if (shapeOverride) return normalizeShape(shapeOverride);
        const documentRef = documentLike || (typeof document !== 'undefined' ? document : null);
        return normalizeShape(documentRef?.getElementById?.('brushShape')?.value);
    }

    function createCurrent(radius, shapeOverride, documentLike, randomFn) {
        return create(currentShape(documentLike, shapeOverride), radius, randomFn);
    }

    // SPB-93 Pass 108 (2026-07-17): Photoshop-style hardness is the radius of
    // the full-strength core, not a Gaussian sigma that shrinks the whole dab
    // toward a pinprick as Hardness rises. Feather only the remaining band.
    function softFalloff(distanceSquaredValue, radiusValue, hardnessValue) {
        const radius = Math.max(1e-6, Math.abs(Number(radiusValue) || 1));
        const distance = Math.sqrt(Math.max(0, Number(distanceSquaredValue) || 0));
        const normalized = distance / radius;
        const hardness = Math.max(0, Math.min(1, Number(hardnessValue) || 0));
        if (normalized > 1) return 0;
        if (hardness >= 0.999 || normalized <= hardness) return 1;
        const t = Math.max(0, Math.min(1, (normalized - hardness) / Math.max(1e-6, 1 - hardness)));
        return 1 - t * t * (3 - 2 * t);
    }

    // Canvas2D radial gradients interpolate linearly between color stops. A
    // sampled stop table lets the fast round-tip path follow the exact same
    // smooth hardness curve as pixel, shaped, and retouch kernels.
    function radialFalloffStops(hardnessValue, featherSamplesValue) {
        const hardness = Math.max(0, Math.min(1, Number(hardnessValue) || 0));
        const featherSamples = Math.max(2, Math.min(16,
            Math.round(Number(featherSamplesValue) || 6)));
        if (hardness >= 0.999) return [[0, 1], [1, 1]];
        const stops = [[0, 1]];
        if (hardness > 0) stops.push([hardness, 1]);
        for (let index = 1; index <= featherSamples; index++) {
            const position = hardness + (1 - hardness) * index / featherSamples;
            stops.push([position, softFalloff(position * position, 1, hardness)]);
        }
        return stops;
    }

    return Object.freeze({
        VALID_SHAPES: Object.freeze(Array.from(VALID_SHAPES)),
        normalizeShape,
        currentShape,
        create,
        createCurrent,
        softFalloff,
        radialFalloffStops
    });
});
