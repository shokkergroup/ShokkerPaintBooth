(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSelectionMove = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function analyzeMask(mask, width, height) {
        const size = Math.max(0, width * height);
        let count = 0;
        let minX = width, minY = height, maxX = -1, maxY = -1;
        for (let index = 0; index < size; index++) {
            if (!mask || mask[index] <= 0) continue;
            count++;
            const x = index % width;
            const y = (index - x) / width;
            if (x < minX) minX = x; if (y < minY) minY = y;
            if (x > maxX) maxX = x; if (y > maxY) maxY = y;
        }
        // SPB-93 tick 27, owner verdict: tools still felt "jinky/off."
        // On the 1,002,001-pixel served QA selection, dynamic Array.push plus
        // typed-array conversion cost 73-93 ms in isolation. Two bounded typed
        // passes measured 18-32 ms and avoid million-entry temporary JS arrays.
        const indices = new Int32Array(count);
        const values = new Uint8Array(count);
        let cursor = 0;
        for (let index = 0; index < size; index++) {
            const value = mask ? mask[index] : 0;
            if (value <= 0) continue;
            indices[cursor] = index;
            values[cursor] = value;
            cursor++;
        }
        return {
            indices,
            values,
            count,
            bounds: count ? { minX, minY, maxX, maxY } : null,
        };
    }

    function resolveOffset(start, current, eventLike) {
        let dx = Math.round((current?.x || 0) - (start?.x || 0));
        let dy = Math.round((current?.y || 0) - (start?.y || 0));
        if (eventLike && eventLike.shiftKey) {
            if (Math.abs(dx) >= Math.abs(dy)) dy = 0;
            else dx = 0;
        }
        return { dx, dy };
    }

    // SPB-93 tick 26, owner verdict: Move Border still felt "jinky/off."
    // The old preview scanned all 4,194,304 mask cells on every pointer event.
    // Served before -> after: six-point move 1,566 -> 583 ms; away-and-back
    // 1,371 -> 187 ms with no history. Analyze once, then move a compact GPU
    // ghost and translate selected entries only at commit.
    function translationStats(analysis, width, height, dxValue, dyValue) {
        const dx = Math.round(Number(dxValue) || 0);
        const dy = Math.round(Number(dyValue) || 0);
        let movedPixels = 0, clippedPixels = 0;
        if (!analysis || !analysis.indices || !analysis.count) {
            return { dx, dy, movedPixels, clippedPixels };
        }
        const bounds = analysis.bounds;
        if (bounds && bounds.minX + dx >= 0 && bounds.maxX + dx < width &&
                bounds.minY + dy >= 0 && bounds.maxY + dy < height) {
            // SPB-93 tick 27: the common in-bounds nudge needs no per-pixel
            // clipping scan. Bounds prove every compact entry remains valid;
            // on the million-pixel QA mask this removes a full pass per repeat.
            return { dx, dy, movedPixels: analysis.count, clippedPixels: 0 };
        }
        for (let cursor = 0; cursor < analysis.count; cursor++) {
            const index = analysis.indices[cursor];
            const x = index % width;
            const y = (index - x) / width;
            const nextX = x + dx;
            const nextY = y + dy;
            if (nextX < 0 || nextX >= width || nextY < 0 || nextY >= height) clippedPixels++;
            else movedPixels++;
        }
        return { dx, dy, movedPixels, clippedPixels };
    }

    function translate(analysis, width, height, dxValue, dyValue) {
        const dx = Math.round(Number(dxValue) || 0);
        const dy = Math.round(Number(dyValue) || 0);
        const shifted = new Uint8Array(width * height);
        if (!analysis || !analysis.indices || !analysis.count) {
            return {
                mask: shifted,
                analysis: { indices: new Int32Array(0), values: new Uint8Array(0), count: 0, bounds: null },
                dx, dy, movedPixels: 0, clippedPixels: 0,
            };
        }
        const nextIndices = new Int32Array(analysis.count);
        const nextValues = new Uint8Array(analysis.count);
        let minX = width, minY = height, maxX = -1, maxY = -1;
        let movedPixels = 0, clippedPixels = 0;
        for (let cursor = 0; cursor < analysis.count; cursor++) {
            const index = analysis.indices[cursor];
            const x = index % width;
            const y = (index - x) / width;
            const nextX = x + dx;
            const nextY = y + dy;
            if (nextX < 0 || nextX >= width || nextY < 0 || nextY >= height) {
                clippedPixels++;
                continue;
            }
            const nextIndex = nextY * width + nextX;
            const value = analysis.values[cursor];
            shifted[nextIndex] = value;
            nextIndices[movedPixels] = nextIndex;
            nextValues[movedPixels] = value;
            minX = Math.min(minX, nextX); minY = Math.min(minY, nextY);
            maxX = Math.max(maxX, nextX); maxY = Math.max(maxY, nextY);
            movedPixels++;
        }
        return {
            mask: shifted,
            analysis: {
                indices: nextIndices.slice(0, movedPixels),
                values: nextValues.slice(0, movedPixels),
                count: movedPixels,
                bounds: movedPixels ? { minX, minY, maxX, maxY } : null,
            },
            dx, dy, movedPixels, clippedPixels,
        };
    }

    function countDifferences(left, right) {
        if (!left || !right || left.length !== right.length) return Infinity;
        let changed = 0;
        for (let index = 0; index < left.length; index++) {
            if (left[index] !== right[index]) changed++;
        }
        return changed;
    }

    function hasMeaningfulChange(analysis, dxValue, dyValue) {
        return !!(analysis && analysis.count > 0 &&
            (Math.round(Number(dxValue) || 0) !== 0 || Math.round(Number(dyValue) || 0) !== 0));
    }

    return { analyzeMask, resolveOffset, translationStats, translate, countDifferences, hasMeaningfulChange };
});
