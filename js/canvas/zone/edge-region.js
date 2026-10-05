(function (root, factory) {
    let maskMath = root && root.SPBWandSelection;
    if (!maskMath && typeof module === 'object' && module.exports) {
        maskMath = require('./wand-selection.js');
    }
    const api = factory(maskMath);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBEdgeRegion = api;
})(typeof window !== 'undefined' ? window : globalThis, function (maskMath) {
    'use strict';

    if (!maskMath) throw new Error('SPBEdgeRegion requires SPBWandSelection');

    function clampInt(value, min, max) {
        return Math.max(min, Math.min(max, Math.round(Number(value) || 0)));
    }

    function pixelDistance(rgba, leftIndex, rightIndex) {
        const left = leftIndex * 4;
        const right = rightIndex * 4;
        return Math.max(
            Math.abs(rgba[left] - rgba[right]),
            Math.abs(rgba[left + 1] - rgba[right + 1]),
            Math.abs(rgba[left + 2] - rgba[right + 2]),
            Math.abs(rgba[left + 3] - rgba[right + 3])
        );
    }

    function edgeStrengthAt(rgba, width, height, position) {
        const x = position % width;
        const y = (position - x) / width;
        let strength = 0;
        if (x > 0) strength = Math.max(strength, pixelDistance(rgba, position, position - 1));
        if (x < width - 1) strength = Math.max(strength, pixelDistance(rgba, position, position + 1));
        if (y > 0) strength = Math.max(strength, pixelDistance(rgba, position, position - width));
        if (y < height - 1) strength = Math.max(strength, pixelDistance(rgba, position, position + width));
        return strength;
    }

    function buildEdgeMap(rgba, width, height, toleranceValue) {
        const tolerance = clampInt(toleranceValue, 0, 255);
        const map = new Uint8Array(width * height);
        for (let position = 0; position < map.length; position++) {
            if (edgeStrengthAt(rgba, width, height, position) > tolerance) map[position] = 255;
        }
        return map;
    }

    // SPB-93 tick 25, owner verdict: tools still feel "jinky/off." The legacy
    // path duplicated grayscale Sobel code for Add and Subtract, ignored alpha
    // and equal-luminance chromatic edges, mutated the current Zone while it
    // searched, and pushed history even when the seed was an edge. Served after:
    // tolerance 10 vs 80 produced 718 vs 743 bounded pixels and the shared
    // 2048 preview completed in 296 ms. This pure RGBA boundary candidate is
    // shared by every composition mode and preview.
    function buildRegion(rgba, width, height, seedXValue, seedYValue, toleranceValue) {
        const seedX = clampInt(seedXValue, 0, width - 1);
        const seedY = clampInt(seedYValue, 0, height - 1);
        const tolerance = clampInt(toleranceValue, 0, 255);
        const size = width * height;
        const candidate = new Uint8Array(size);
        const edgeState = new Uint8Array(size); // 0 unknown, 1 clear, 2 edge

        function isEdge(position) {
            if (edgeState[position]) return edgeState[position] === 2;
            const edge = edgeStrengthAt(rgba, width, height, position) > tolerance;
            edgeState[position] = edge ? 2 : 1;
            return edge;
        }

        const seed = seedY * width + seedX;
        if (isEdge(seed)) {
            return {
                valid: false,
                reason: 'Clicked on an edge - click inside a bounded region',
                regionMask: candidate,
                candidatePixels: 0,
                tolerance,
            };
        }

        const queue = new Int32Array(size);
        let head = 0, tail = 0, candidatePixels = 0;
        queue[tail++] = seed;
        candidate[seed] = 255;
        while (head < tail) {
            const position = queue[head++];
            candidatePixels++;
            const x = position % width;
            const y = (position - x) / width;
            if (x > 0) visit(position - 1);
            if (x < width - 1) visit(position + 1);
            if (y > 0) visit(position - width);
            if (y < height - 1) visit(position + width);
        }

        function visit(position) {
            if (candidate[position] || edgeState[position] === 2) return;
            if (isEdge(position)) return;
            candidate[position] = 255;
            queue[tail++] = position;
        }

        return { valid: true, reason: '', regionMask: candidate, candidatePixels, tolerance };
    }

    function select(rgba, width, height, seedX, seedY, currentMask, options) {
        const opts = options || {};
        const built = buildRegion(rgba, width, height, seedX, seedY, opts.tolerance);
        if (!built.valid) return built;
        return Object.assign(
            built,
            maskMath.composeMask(currentMask, built.regionMask, opts.mode)
        );
    }

    return { pixelDistance, edgeStrengthAt, buildEdgeMap, buildRegion, select };
});
