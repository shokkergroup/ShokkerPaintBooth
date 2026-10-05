(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBWandSelection = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function clampInt(value, min, max) {
        return Math.max(min, Math.min(max, Math.round(Number(value) || 0)));
    }

    // SPB-93 tick 23, owner verdict: tools still feel "jinky/off." The old
    // Wand advertised 3x3/5x5/11x11 sampling and Anti-alias but always sampled
    // one RGB pixel and always dilated with tolerance*5. Served after: Point vs
    // 11x11 produced 144 vs 160 candidates; Contiguous ON vs OFF produced 137
    // vs 1,387,074 at the same source point. This pure path makes the controls
    // real and keeps history after exact comparison.
    function sampleColor(rgba, width, height, xValue, yValue, sampleSizeValue) {
        const x = clampInt(xValue, 0, width - 1);
        const y = clampInt(yValue, 0, height - 1);
        const size = [1, 3, 5, 11].includes(Number(sampleSizeValue)) ? Number(sampleSizeValue) : 1;
        const radius = Math.floor(size / 2);
        let r = 0, g = 0, b = 0, a = 0, count = 0;
        for (let sy = Math.max(0, y - radius); sy <= Math.min(height - 1, y + radius); sy++) {
            for (let sx = Math.max(0, x - radius); sx <= Math.min(width - 1, x + radius); sx++) {
                const pi = (sy * width + sx) * 4;
                r += rgba[pi]; g += rgba[pi + 1]; b += rgba[pi + 2]; a += rgba[pi + 3]; count++;
            }
        }
        return {
            r: Math.round(r / Math.max(1, count)),
            g: Math.round(g / Math.max(1, count)),
            b: Math.round(b / Math.max(1, count)),
            a: Math.round(a / Math.max(1, count)),
            count,
        };
    }

    function colorDistance(rgba, pixelIndex, sample) {
        const pi = pixelIndex * 4;
        return Math.max(
            Math.abs(rgba[pi] - sample.r),
            Math.abs(rgba[pi + 1] - sample.g),
            Math.abs(rgba[pi + 2] - sample.b),
            Math.abs(rgba[pi + 3] - sample.a)
        );
    }

    function resolveMode(uiModeValue, eventLike) {
        if (eventLike && eventLike.altKey) return 'subtract';
        if (eventLike && eventLike.shiftKey) return 'add';
        return uiModeValue === 'add' || uiModeValue === 'subtract' ? uiModeValue : 'replace';
    }

    function buildRegion(rgba, width, height, seedXValue, seedYValue, options) {
        const opts = options || {};
        const seedX = clampInt(seedXValue, 0, width - 1);
        const seedY = clampInt(seedYValue, 0, height - 1);
        const tolerance = clampInt(opts.tolerance, 0, 255);
        const sample = sampleColor(rgba, width, height, seedX, seedY, opts.sampleSize);
        const region = new Uint8Array(width * height);
        const matches = function (index) { return colorDistance(rgba, index, sample) <= tolerance; };

        if (opts.contiguous !== false) {
            const seed = seedY * width + seedX;
            const queue = new Int32Array(width * height);
            let head = 0, tail = 0;
            queue[tail++] = seed;
            region[seed] = 255;
            while (head < tail) {
                const pos = queue[head++];
                const x = pos % width;
                const y = (pos - x) / width;
                if (x > 0) visit(pos - 1);
                if (x < width - 1) visit(pos + 1);
                if (y > 0) visit(pos - width);
                if (y < height - 1) visit(pos + width);
            }
            function visit(index) {
                if (region[index] || !matches(index)) return;
                region[index] = 255;
                queue[tail++] = index;
            }
        } else {
            for (let i = 0; i < region.length; i++) if (matches(i)) region[i] = 255;
            region[seedY * width + seedX] = 255;
        }

        if (opts.antiAlias !== false) {
            const softened = new Uint8Array(region);
            const edgeBand = Math.max(4, Math.min(32, Math.round(tolerance * 0.5) || 4));
            for (let pos = 0; pos < region.length; pos++) {
                if (region[pos]) continue;
                const x = pos % width;
                const y = (pos - x) / width;
                const touches = (x > 0 && region[pos - 1]) ||
                    (x < width - 1 && region[pos + 1]) ||
                    (y > 0 && region[pos - width]) ||
                    (y < height - 1 && region[pos + width]);
                if (!touches) continue;
                const distance = colorDistance(rgba, pos, sample);
                if (distance <= tolerance || distance > tolerance + edgeBand) continue;
                const coverage = 1 - (distance - tolerance) / (edgeBand + 1);
                softened[pos] = Math.max(1, Math.min(192, Math.round(coverage * 192)));
            }
            return { regionMask: softened, sample, tolerance };
        }
        return { regionMask: region, sample, tolerance };
    }

    function countDifferences(a, b) {
        if (!a || !b || a.length !== b.length) return Infinity;
        let changed = 0;
        for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) changed++;
        return changed;
    }

    function composeMask(currentMask, candidateMask, modeValue) {
        const current = currentMask instanceof Uint8Array
            ? currentMask
            : new Uint8Array(candidateMask ? candidateMask.length : 0);
        const candidate = candidateMask instanceof Uint8Array
            ? candidateMask
            : new Uint8Array(current.length);
        const mode = modeValue === 'subtract' || modeValue === 'replace' ? modeValue : 'add';
        const next = mode === 'replace' ? new Uint8Array(candidate) : new Uint8Array(current);
        let candidatePixels = 0;
        for (let i = 0; i < candidate.length; i++) {
            const value = candidate[i];
            if (value > 0) candidatePixels++;
            if (mode === 'add') next[i] = Math.max(next[i], value);
            else if (mode === 'subtract') next[i] = Math.max(0, next[i] - value);
        }
        let selectedPixels = 0;
        for (let i = 0; i < next.length; i++) if (next[i] > 0) selectedPixels++;
        return {
            nextMask: next,
            candidatePixels,
            selectedPixels,
            changedPixels: countDifferences(current, next),
        };
    }

    function select(rgba, width, height, seedX, seedY, currentMask, options) {
        const opts = options || {};
        const built = buildRegion(rgba, width, height, seedX, seedY, opts);
        const composed = composeMask(currentMask, built.regionMask, opts.mode);
        return Object.assign({ sample: built.sample, candidateMask: built.regionMask }, composed);
    }

    function selectGlobal(rgba, width, height, seedX, seedY, currentMask, options) {
        // SPB-93 tick 24, owner verdict: color tools still felt "jinky/off."
        // Served before -> after at one source point: ignored sample sizes ->
        // Point 1,387,074 vs 11x11 1,308,538 candidates; unconditional hard
        // edge -> Anti-alias OFF 1,330,578 vs ON 1,387,074. Global matching is
        // forced here so the Select All Color contract cannot drift with UI state.
        return select(
            rgba, width, height, seedX, seedY, currentMask,
            Object.assign({}, options || {}, { contiguous: false })
        );
    }

    return { sampleColor, colorDistance, resolveMode, buildRegion, composeMask, countDifferences, select, selectGlobal };
});
