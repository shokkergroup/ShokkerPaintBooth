/* ============================================================================
 * SPB OBJECT GRAB — 2026-07-30 (Claude)
 *
 * Owner, 2026-07-29: "the tools that people use in this app MOSTLY what we need
 * to work the BEST is where if people ONLY have a TGA/JPG file and not a PSD
 * file with Layers is they need to be able to draw and mask out parts they want
 * to either include or exclude ... if you want to grab a number without having
 * to color it perfectly - to grab that number and make it part of an exclude
 * zone or grab this logo and exclude the logo only without having to do a
 * perfect meticulous drawing. That's the MOST IMPORTANT part of the tools -
 * period."
 *
 * WHY THE MAGIC WAND CANNOT DO THIS.
 *   The wand floods by COLOUR similarity to the clicked pixel. A race number is
 *   not one colour — a "55" is a yellow fill PLUS a black outline PLUS often a
 *   white inner stroke and a drop shadow. Clicking the yellow grabs the yellow
 *   and stops dead at the outline, so the painter has to shift-click every shade
 *   or trace the glyph by hand. That is exactly the meticulous drawing the owner
 *   is asking to be rid of.
 *
 * WHAT THIS DOES INSTEAD — flood by "NOT BACKGROUND".
 *   1. Take an adaptive window around the click.
 *   2. Estimate the local BACKGROUND from the colours around the window's border
 *      ring (mode of a coarse colour histogram — robust to noise and gradients).
 *   3. Flood 8-connected from the click over every pixel that is NOT the
 *      background. Fill, outline, stroke and shadow are all "not background", so
 *      they come as ONE piece.
 *   4. If the flood reaches the window border the object is bigger than the
 *      window, so double the window and try again. This is what removes the
 *      "how big is my brush" guesswork.
 *   5. Fill enclosed holes (the counters of a 5, 6, 8, A...) so an excluded
 *      number excludes its whole footprint rather than leaving specks behind.
 *
 * Same module contract as SPBEdgeRegion so the app wraps it identically:
 *   select(rgba, w, h, seedX, seedY, currentMask, {tolerance, mode})
 *     -> { valid, reason, regionMask, candidatePixels, ...composeMask(...) }
 * ==========================================================================*/
(function (root, factory) {
    let maskMath = root && root.SPBWandSelection;
    if (!maskMath && typeof module === 'object' && module.exports) {
        maskMath = require('./wand-selection.js');
    }
    const api = factory(maskMath);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBObjectGrab = api;
})(typeof window !== 'undefined' ? window : globalThis, function (maskMath) {
    'use strict';

    if (!maskMath) throw new Error('SPBObjectGrab requires SPBWandSelection');

    // ---- tuning -------------------------------------------------------------
    const ABSORB_ROUNDS = 3;         // fill -> outline -> inner stroke / shadow
    const ABSORB_RATIO = 1.25;       // a part bigger than this x the CLICKED patch is not trim
    const TOTAL_GROWTH_LIMIT = 4.0;  // finished object <= this x the clicked patch
    const MAX_PARTS = 24;            // generous: THICKNESS is the real discriminator
    const MAX_TRIM_THICKNESS = 14;   // px average width of a band we call "trim"
    const ESCAPE_MARGIN = 10;        // px of slack before a neighbour counts as escaping
    const MAX_AREA_FRACTION = 0.06;  // a decal is a few percent of the sheet, not a quarter
    // How far past the cap a refused grab is still worth DRAWING as a warning.
    // Between the cap and this, the painter probably meant it (a wide stripe) and
    // deserves to see the shape; beyond it, it is open bodywork and we stay quiet.
    const PREVIEW_SHOW_LIMIT = 0.12;
    const PATCH_CEILING = 400000;    // clearly bodywork, stop early

    // One reusable visited buffer. Cleared by reallocation only when the canvas
    // size changes; each call fills it fresh via the stamp trick below.
    let _visited = null, _visitedLen = 0;
    function scratchVisited(len) {
        if (!_visited || _visitedLen !== len) {
            _visited = new Uint8Array(len);
            _visitedLen = len;
        } else {
            _visited.fill(0);
        }
        return _visited;
    }

    function clampInt(v, min, max) {
        return Math.max(min, Math.min(max, Math.round(Number(v) || 0)));
    }

    function colourKey(rgba, idx) {
        const p = idx * 4;
        return ((rgba[p] >> 4) << 8) | ((rgba[p + 1] >> 4) << 4) | (rgba[p + 2] >> 4);
    }

    function chebyshev(rgba, a, b) {
        const p = a * 4, q = b * 4;
        return Math.max(
            Math.abs(rgba[p] - rgba[q]),
            Math.abs(rgba[p + 1] - rgba[q + 1]),
            Math.abs(rgba[p + 2] - rgba[q + 2])
        );
    }

    /**
     * Flood the connected same-colour patch containing seed, bounded to box.
     * `escaped` is the key output: it means the patch reached the limit box, i.e.
     * it runs off into open paint. That is what separates a decal outline from
     * the bodywork, and it needs no guess about object size.
     */
    function patchAt(rgba, width, height, seed, tolerance, box, claimed) {
        // `contact` counts how many of this patch's pixels touch the already-claimed
        // object. area/contact is the patch's average thickness along that contact,
        // which is what tells an outline apart from open bodywork.
        let contact = 0;
        const pixels = [];
        // A Uint8Array scratch beats a Set here by a wide margin: hover preview
        // runs this on every pointer move, and a Set of a quarter-million ints is
        // not interactive. Reused across calls to avoid re-allocating 4MB a frame.
        const visited = scratchVisited(width * height);
        const stack = [seed];
        let escaped = false;
        let minX = width, maxX = -1, minY = height, maxY = -1;

        while (stack.length) {
            const pos = stack.pop();
            if (visited[pos]) continue;
            visited[pos] = 1;
            const x = pos % width;
            const y = (pos - x) / width;
            if (x < box.x0 || x > box.x1 || y < box.y0 || y > box.y1) { escaped = true; continue; }
            if (chebyshev(rgba, pos, seed) > tolerance) continue;
            if (claimed && claimed[pos]) continue;
            pixels.push(pos);
            if (claimed) {
                if ((x > 0 && claimed[pos - 1]) || (x < width - 1 && claimed[pos + 1]) ||
                    (y > 0 && claimed[pos - width]) || (y < height - 1 && claimed[pos + width])) {
                    contact++;
                }
            }
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
            if (x > 0) stack.push(pos - 1);
            if (x < width - 1) stack.push(pos + 1);
            if (y > 0) stack.push(pos - width);
            if (y < height - 1) stack.push(pos + width);
            if (pixels.length > PATCH_CEILING) { escaped = true; break; }
        }
        return { pixels, escaped, contact, minX, maxX, minY, maxY };
    }

    /** Pixels touching the mask but not in it, grouped by coarse colour. */
    function neighbourGroups(rgba, width, height, mask, bounds) {
        const groups = new Map();
        const y0 = Math.max(0, bounds.minY - 2), y1 = Math.min(height - 1, bounds.maxY + 2);
        const x0 = Math.max(0, bounds.minX - 2), x1 = Math.min(width - 1, bounds.maxX + 2);
        for (let y = y0; y <= y1; y++) {
            for (let x = x0; x <= x1; x++) {
                const idx = y * width + x;
                if (mask[idx]) continue;
                const touches =
                    (x > 0 && mask[idx - 1]) || (x < width - 1 && mask[idx + 1]) ||
                    (y > 0 && mask[idx - width]) || (y < height - 1 && mask[idx + width]);
                if (!touches) continue;
                const k = colourKey(rgba, idx);
                let g = groups.get(k);
                if (!g) { g = { count: 0, seed: idx }; groups.set(k, g); }
                g.count++;
            }
        }
        return groups;
    }

    /**
     * Fill holes fully enclosed by the object - the counters of 5/6/8/A/O and the
     * gap between a glyph and its outline. Without this, excluding a number leaves
     * background-coloured specks inside it that still take the finish.
     */
    function fillEnclosedHoles(width, height, mask, bounds) {
        const x0 = Math.max(0, bounds.minX - 1), x1 = Math.min(width - 1, bounds.maxX + 1);
        const y0 = Math.max(0, bounds.minY - 1), y1 = Math.min(height - 1, bounds.maxY + 1);
        const outside = new Uint8Array(width * height);
        const queue = [];
        const push = (idx) => {
            if (mask[idx] || outside[idx]) return;
            outside[idx] = 1;
            queue.push(idx);
        };
        for (let x = x0; x <= x1; x++) { push(y0 * width + x); push(y1 * width + x); }
        for (let y = y0; y <= y1; y++) { push(y * width + x0); push(y * width + x1); }
        while (queue.length) {
            const pos = queue.pop();
            const x = pos % width, y = (pos - x) / width;
            if (x > x0) push(pos - 1);
            if (x < x1) push(pos + 1);
            if (y > y0) push(pos - width);
            if (y < y1) push(pos + width);
        }
        let filled = 0;
        for (let y = y0; y <= y1; y++) {
            for (let x = x0; x <= x1; x++) {
                const idx = y * width + x;
                if (!mask[idx] && !outside[idx]) { mask[idx] = 255; filled++; }
            }
        }
        return filled;
    }

    /**
     * Grab the whole object under (seedX, seedY) by REGION MERGING.
     *
     * v1 flooded "everything that is not the window-border colour". On real
     * liveries that failed badly: as the window grew, its border landed on the
     * image margin, so background became the margin and the ENTIRE CAR counted as
     * object - measured 2,188,486px (52% of a 2048x2048 canvas) on 77-Chilis.
     *
     * v2 never asks what the background is globally. It starts from the clicked
     * colour patch and repeatedly asks of each touching neighbour: are you a thin
     * bounded band (outline, inner stroke, shadow) or do you run off into open
     * paint (the body)? Bounded neighbours are absorbed; escaping ones mark the
     * edge of the decal. That is the distinction a painter makes by eye, and it
     * needs no window-size guess.
     */
    function buildObject(rgba, width, height, seedX, seedY, options) {
        const opts = options || {};
        const cx = clampInt(seedX, 0, width - 1);
        const cy = clampInt(seedY, 0, height - 1);
        const tol = clampInt(opts.tolerance == null ? 30 : opts.tolerance, 4, 200);
        const total = width * height;
        const seed = cy * width + cx;

        const mask = new Uint8Array(total);
        const whole = { x0: 0, y0: 0, x1: width - 1, y1: height - 1 };
        const first = patchAt(rgba, width, height, seed, tol, whole, null);
        if (!first.pixels.length) return { valid: false, reason: 'Nothing to grab at that point' };
        if (first.pixels.length > total * MAX_AREA_FRACTION) {
            // Refused, but hand back the draft anyway when it is only somewhat too big.
            // The hover preview draws it in WARNING colour instead of showing nothing:
            // silence made a wide stripe a dead zone — hover, see nothing, no reason
            // given. Past PREVIEW_SHOW_LIMIT it is unmistakably open bodywork, and
            // washing 2M pixels on every pointer move is not worth the frame.
            if (first.pixels.length <= total * PREVIEW_SHOW_LIMIT) {
                for (let i = 0; i < first.pixels.length; i++) mask[first.pixels[i]] = 255;
                return {
                    valid: false, oversize: true, regionMask: mask,
                    bounds: { minX: first.minX, maxX: first.maxX,
                              minY: first.minY, maxY: first.maxY },
                    candidatePixels: first.pixels.length,
                    reason: 'That is open paint, not a decal - click a number, logo or stripe'
                };
            }
            return { valid: false,
                     reason: 'That is open paint, not a decal - click a number, logo or stripe' };
        }
        for (let i = 0; i < first.pixels.length; i++) mask[first.pixels[i]] = 255;

        const bounds = { minX: first.minX, maxX: first.maxX, minY: first.minY, maxY: first.maxY };
        const seedArea = first.pixels.length;      // the budget anchor: what was clicked
        let objectPixels = seedArea;
        let parts = 0;

        for (let round = 0; round < ABSORB_ROUNDS; round++) {
            const groups = neighbourGroups(rgba, width, height, mask, bounds);
            if (!groups.size) break;
            let tookAny = false;

            // A genuine outline or shadow stays within a small margin of the
            // object. Anything reaching the edge of this box is open bodywork.
            const limit = {
                x0: Math.max(0, bounds.minX - ESCAPE_MARGIN),
                x1: Math.min(width - 1, bounds.maxX + ESCAPE_MARGIN),
                y0: Math.max(0, bounds.minY - ESCAPE_MARGIN),
                y1: Math.min(height - 1, bounds.maxY + ESCAPE_MARGIN)
            };

            const candidates = [];
            groups.forEach((g) => { if (g.count >= 3) candidates.push(g); });

            for (let ci = 0; ci < candidates.length; ci++) {
                if (parts >= MAX_PARTS) break;
                const g = candidates[ci];
                if (mask[g.seed]) continue;
                const cand = patchAt(rgba, width, height, g.seed, tol, limit, mask);
                if (!cand.pixels.length) continue;
                if (cand.escaped) continue;                                    // open paint
                // THE THICKNESS TEST: trim hugs the glyph in a narrow band. Bodywork
                // is thick. This is what makes absorption converge on its own.
                const thickness = cand.contact > 0 ? (cand.pixels.length / cand.contact) : Infinity;
                if (thickness > MAX_TRIM_THICKNESS) continue;
                // Budgets against the CLICKED patch so absorption cannot compound.
                if (cand.pixels.length > seedArea * ABSORB_RATIO) continue;     // too big for trim
                if (objectPixels + cand.pixels.length > seedArea * TOTAL_GROWTH_LIMIT) continue;
                for (let i = 0; i < cand.pixels.length; i++) mask[cand.pixels[i]] = 255;
                objectPixels += cand.pixels.length;
                bounds.minX = Math.min(bounds.minX, cand.minX);
                bounds.maxX = Math.max(bounds.maxX, cand.maxX);
                bounds.minY = Math.min(bounds.minY, cand.minY);
                bounds.maxY = Math.max(bounds.maxY, cand.maxY);
                parts++;
                tookAny = true;
            }
            if (!tookAny) break;
        }

        // NOTE 2026-07-30: these two messages used to say "raise Tolerance", which is
        // backwards and actively unhelpful — `chebyshev(...) > tolerance` SKIPS a pixel,
        // so a HIGHER tolerance matches more loosely and grabs MORE. A painter who has
        // just over-grabbed and follows that advice makes it worse. Lower it.
        if (objectPixels > total * MAX_AREA_FRACTION) {
            return {
                valid: false,
                oversize: objectPixels <= total * PREVIEW_SHOW_LIMIT,
                regionMask: mask, bounds: bounds, candidatePixels: objectPixels,
                reason: 'That grabbed too much — lower Tolerance, or click the number itself'
            };
        }

        // Enclosed holes are the counters of glyphs — small. Two guards:
        //  1. holes bigger than the object mean the "hole" was the rest of the car
        //     (v2 produced 667,913 hole pixels doing exactly that);
        //  2. holes must not push the FINAL size past the decal cap. This second
        //     one was the bug behind both remaining over-grabs: the bare object
        //     measured 5.99% and 5.22%, passed the only check, and then hole
        //     filling added 102,644px and 71,453px to land at 8.43% and 6.93%.
        //     The cap has to be applied to the finished mask, not the draft.
        const before = mask.slice();
        const holes = fillEnclosedHoles(width, height, mask, bounds);
        let holesKept = holes;
        const cap = total * MAX_AREA_FRACTION;
        if (holes > objectPixels || objectPixels + holes > cap) {
            mask.set(before);                       // implausible: keep the object only
            holesKept = 0;
        }
        if (objectPixels + holesKept > cap) {
            return {
                valid: false,
                oversize: (objectPixels + holesKept) <= total * PREVIEW_SHOW_LIMIT,
                regionMask: mask, bounds: bounds,
                candidatePixels: objectPixels + holesKept,
                reason: 'That grabbed too much of the car — click the number or logo itself, ' +
                        'or lower Tolerance'
            };
        }

        return {
            valid: true,
            reason: '',
            regionMask: mask,
            candidatePixels: objectPixels + holesKept,
            objectPixels: objectPixels,
            holePixels: holesKept,
            absorbedParts: parts,
            bounds: bounds,
            tolerance: tol
        };
    }

    function select(rgba, width, height, seedX, seedY, currentMask, options) {
        const opts = options || {};
        const built = buildObject(rgba, width, height, seedX, seedY, opts);
        if (!built.valid) return built;
        return Object.assign(built, maskMath.composeMask(currentMask, built.regionMask, opts.mode));
    }

    return { chebyshev, colourKey, patchAt, buildObject, select };
});
