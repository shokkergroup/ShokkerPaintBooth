(function () {
    'use strict';

    // PORT-W1 (2026-10-09, owner: "our tools basically SUCK"): Fill Bucket now
    // shares the Magic Wand's region maths - SPBPcSelection.wandRegion, ported
    // from PhotoCraft crates/algo/src/selection.rs (span flood fill, Chebyshev
    // R,G,B,A <= tolerance, 4-connected) - so the same click + tolerance picks
    // the same pixels in both tools (the old bucket used a Euclidean-RGB radius of
    // tolerance*sqrt3 and ignored alpha differences). The wand's 3x3 geometric edge
    // anti-alias (honouring the shared Anti-alias checkbox, default on) softens the
    // fill rim. window.SPB_PC_W1_OFF = true restores the legacy Euclidean flood.
    const pcAA = new WeakMap(); // matches array -> { mask, box } coverage of the fill
    function pcCore() {
        if (window.SPB_PC_W1_OFF) return null;
        return window.SPBPcSelection || null;
    }

    function emptyResult(pixelCount) {
        return {
            matches: new Uint8Array(Math.max(0, pixelCount || 0)),
            count: 0,
            minX: -1,
            minY: -1,
            maxX: -1,
            maxY: -1
        };
    }

    function collectMatches(data, width, height, startX, startY, tolerance, contiguous) {
        const pixelCount = width * height;
        const result = emptyResult(pixelCount);
        if (!data || width <= 0 || height <= 0 || data.length < pixelCount * 4) return result;

        const seedX = Math.floor(startX);
        const seedY = Math.floor(startY);
        if (seedX < 0 || seedX >= width || seedY < 0 || seedY >= height) return result;

        const pc = pcCore();
        if (pc) {
            const aaBox = document.getElementById('wandAntiAlias');
            const region = pc.wandRegion(data, width, height, seedX, seedY, {
                tolerance: Number.isFinite(Number(tolerance)) ? Number(tolerance) : 0,
                contiguous: contiguous !== false,
                antiAlias: aaBox ? aaBox.checked !== false : true,
            });
            if (region.coreBox) {
                const cb = region.coreBox;
                for (let y = cb.y0; y < cb.y1; y++) {
                    const row = y * width;
                    for (let x = cb.x0; x < cb.x1; x++) {
                        if (region.core[row + x]) { result.matches[row + x] = 2; result.count++; }
                    }
                }
                result.minX = cb.x0; result.minY = cb.y0; result.maxX = cb.x1 - 1; result.maxY = cb.y1 - 1;
                if (region.mask !== region.core) pcAA.set(result.matches, { mask: region.mask, box: region.bbox, rowWidth: width });
            }
            return result;
        }

        const seedPixel = seedY * width + seedX;
        const seedOffset = seedPixel * 4;
        const seedR = data[seedOffset];
        const seedG = data[seedOffset + 1];
        const seedB = data[seedOffset + 2];
        const seedTransparent = data[seedOffset + 3] === 0;
        const safeTolerance = Math.max(0, Number.isFinite(Number(tolerance)) ? Number(tolerance) : 0);
        const toleranceSquared = safeTolerance * safeTolerance * 3;

        function isMatch(pixelIndex) {
            const offset = pixelIndex * 4;
            const candidateTransparent = data[offset + 3] === 0;
            // SPB-93 tick 17, owner verdict "jinky/off": transparent padding
            // must not join opaque black artwork merely because hidden RGB is black.
            if (candidateTransparent !== seedTransparent) return false;
            if (seedTransparent) return true;
            const dr = data[offset] - seedR;
            const dg = data[offset + 1] - seedG;
            const db = data[offset + 2] - seedB;
            return dr * dr + dg * dg + db * db <= toleranceSquared;
        }

        function accept(pixelIndex) {
            result.matches[pixelIndex] = 2;
            result.count++;
            const x = pixelIndex % width;
            const y = (pixelIndex - x) / width;
            if (result.minX < 0 || x < result.minX) result.minX = x;
            if (result.maxX < 0 || x > result.maxX) result.maxX = x;
            if (result.minY < 0 || y < result.minY) result.minY = y;
            if (result.maxY < 0 || y > result.maxY) result.maxY = y;
        }

        if (contiguous !== false) {
            const seen = new Uint8Array(pixelCount);
            const queue = new Int32Array(pixelCount);
            let head = 0;
            let tail = 0;
            queue[tail++] = seedPixel;
            seen[seedPixel] = 1;
            while (head < tail) {
                const pixelIndex = queue[head++];
                if (!isMatch(pixelIndex)) continue;
                accept(pixelIndex);
                const x = pixelIndex % width;
                const y = (pixelIndex - x) / width;
                if (x > 0 && !seen[pixelIndex - 1]) {
                    seen[pixelIndex - 1] = 1;
                    queue[tail++] = pixelIndex - 1;
                }
                if (x < width - 1 && !seen[pixelIndex + 1]) {
                    seen[pixelIndex + 1] = 1;
                    queue[tail++] = pixelIndex + 1;
                }
                if (y > 0 && !seen[pixelIndex - width]) {
                    seen[pixelIndex - width] = 1;
                    queue[tail++] = pixelIndex - width;
                }
                if (y < height - 1 && !seen[pixelIndex + width]) {
                    seen[pixelIndex + width] = 1;
                    queue[tail++] = pixelIndex + width;
                }
            }
        } else {
            for (let pixelIndex = 0; pixelIndex < pixelCount; pixelIndex++) {
                if (isMatch(pixelIndex)) accept(pixelIndex);
            }
        }

        return result;
    }

    // SPB-93 browser gauntlet (2026-08-08), owner verdict: tools "NEED to
    // feel more Photoshop like and WORK." Layer brush commits keep a tight
    // content bbox for speed, but the document remains the editable surface.
    // Before: a 278 ms transparent-area click changed 0 pixels with no feedback.
    // After: the same case filled 4,029,285 pixels in 539 ms and round-tripped
    // through Ctrl+Z / Ctrl+Shift+Z. Clicks inside retain the smaller fast path.
    function resolveWorkingRaster(documentWidth, documentHeight,
            layerX, layerY, layerWidth, layerHeight, startX, startY) {
        const dw = Math.max(0, Math.floor(Number(documentWidth) || 0));
        const dh = Math.max(0, Math.floor(Number(documentHeight) || 0));
        const lx = Math.round(Number(layerX) || 0);
        const ly = Math.round(Number(layerY) || 0);
        const lw = Math.max(0, Math.floor(Number(layerWidth) || 0));
        const lh = Math.max(0, Math.floor(Number(layerHeight) || 0));
        const sx = Math.floor(Number(startX));
        const sy = Math.floor(Number(startY));
        if (!dw || !dh || sx < 0 || sx >= dw || sy < 0 || sy >= dh) return null;
        const insideLayer = sx >= lx && sx < lx + lw && sy >= ly && sy < ly + lh;
        return insideLayer
            ? { originX: lx, originY: ly, width: lw, height: lh, expanded: false }
            : { originX: 0, originY: 0, width: dw, height: dh, expanded: true };
    }

    function blendSolidFill(data, matches, fillR, fillG, fillB, opacity, apply) {
        const amount = Math.max(0, Math.min(1, Number(opacity) || 0));
        const sourceOverPixel = window.SPBRgbaBlend?.sourceOverPixel;
        if (typeof sourceOverPixel !== 'function') return false;
        let changed = false;
        const aa = pcAA.get(matches);
        if (aa) {
            // Wand-consistent fill: core + 3x3 anti-aliased rim (coverage scales the opacity).
            const box = aa.box;
            const rowWidth = aa.rowWidth;
            for (let y = box.y0; y < box.y1; y++) {
                for (let x = box.x0; x < box.x1; x++) {
                    const pixelIndex = y * rowWidth + x;
                    const coverage = aa.mask[pixelIndex];
                    if (!coverage) continue;
                    const offset = pixelIndex * 4;
                    if (sourceOverPixel(data, offset, fillR, fillG, fillB, 255, amount * coverage / 255, apply)) changed = true;
                }
            }
            return changed;
        }
        for (let pixelIndex = 0; pixelIndex < matches.length; pixelIndex++) {
            if (matches[pixelIndex] !== 2) continue;
            const offset = pixelIndex * 4;
            // SPB-93 Pass 55 (2026-07-17), owner verdict: no jinky tools.
            // Before: 25%-opacity red on empty pixels became [64,0,0,64]
            // (dark fringe). After: [255,0,0,64], with dry-run parity.
            if (sourceOverPixel(data, offset, fillR, fillG, fillB, 255, amount, apply)) changed = true;
        }
        return changed;
    }

    function wouldSolidFillChange(data, matches, fillR, fillG, fillB, opacity) {
        return blendSolidFill(data, matches, fillR, fillG, fillB, opacity, false);
    }

    function applySolidFill(data, matches, fillR, fillG, fillB, opacity) {
        return blendSolidFill(data, matches, fillR, fillG, fillB, opacity, true);
    }

    function hasMaskedDifference(before, after, matches) {
        if (!before || !after || before.length !== after.length) return false;
        for (let pixelIndex = 0; pixelIndex < matches.length; pixelIndex++) {
            if (matches[pixelIndex] !== 2) continue;
            const offset = pixelIndex * 4;
            if (before[offset] !== after[offset] || before[offset + 1] !== after[offset + 1] ||
                before[offset + 2] !== after[offset + 2] || before[offset + 3] !== after[offset + 3]) {
                return true;
            }
        }
        return false;
    }

    window.SPBFillBucket = Object.freeze({
        collectMatches,
        resolveWorkingRaster,
        wouldSolidFillChange,
        applySolidFill,
        hasMaskedDifference
    });
})();
