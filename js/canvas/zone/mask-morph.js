/* ============================================================================
 * SPB MASK MORPH — grow / shrink a zone mask  (2026-07-30, Claude)
 *
 * The last gap in the Grab Object workflow. The live preview now shows exactly
 * what a click will take, so when it is a few pixels short you can SEE it — but
 * seeing it was no use without a way to fix it, and the only options were to
 * change Tolerance and re-grab, or trace by hand. Both are the meticulous work
 * the owner asked to be rid of.
 *
 * This is Photoshop's Expand/Contract Selection: one keystroke each way.
 *   >  grow the selection by 1px      <  shrink it by 1px
 *
 * Two details that matter:
 *  - 8-CONNECTED. A 4-connected grow leaves diagonal staircase notches on the
 *    curves of a glyph, which then show as jagged edges in the render. 8-connected
 *    follows a diagonal cleanly.
 *  - OUT-OF-BOUNDS COUNTS AS SET when shrinking. Treating it as empty would erode
 *    a decal that runs to the edge of the sheet inward from that edge, silently
 *    trimming artwork that is perfectly fine.
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBMaskMorph = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function onePassGrow(src, dst, width, height) {
        dst.set(src);
        for (let y = 0; y < height; y++) {
            const row = y * width;
            for (let x = 0; x < width; x++) {
                const i = row + x;
                if (src[i]) continue;
                const up = y > 0, dn = y < height - 1;
                const lf = x > 0, rt = x < width - 1;
                if ((lf && src[i - 1]) || (rt && src[i + 1]) ||
                    (up && src[i - width]) || (dn && src[i + width]) ||
                    (up && lf && src[i - width - 1]) || (up && rt && src[i - width + 1]) ||
                    (dn && lf && src[i + width - 1]) || (dn && rt && src[i + width + 1])) {
                    dst[i] = 255;
                }
            }
        }
    }

    function onePassShrink(src, dst, width, height) {
        dst.set(src);
        for (let y = 0; y < height; y++) {
            const row = y * width;
            for (let x = 0; x < width; x++) {
                const i = row + x;
                if (!src[i]) continue;
                const up = y > 0, dn = y < height - 1;
                const lf = x > 0, rt = x < width - 1;
                // Out of bounds reads as SET, so a decal touching the sheet edge is
                // not eroded inward from that edge.
                const n = [
                    lf ? src[i - 1] : 255,
                    rt ? src[i + 1] : 255,
                    up ? src[i - width] : 255,
                    dn ? src[i + width] : 255,
                    (up && lf) ? src[i - width - 1] : 255,
                    (up && rt) ? src[i - width + 1] : 255,
                    (dn && lf) ? src[i + width - 1] : 255,
                    (dn && rt) ? src[i + width + 1] : 255
                ];
                for (let k = 0; k < 8; k++) {
                    if (!n[k]) { dst[i] = 0; break; }
                }
            }
        }
    }

    /**
     * @param mask   Uint8Array of width*height, 0 or 255
     * @param pixels positive to grow, negative to shrink
     * @returns { mask, changed } — a NEW array; the input is never mutated so the
     *          caller can push it onto the undo stack first.
     */
    function morph(mask, width, height, pixels) {
        const steps = Math.min(64, Math.abs(Math.round(Number(pixels) || 0)));
        if (!steps || !(mask instanceof Uint8Array) || mask.length !== width * height) {
            return { mask: mask, changed: 0 };
        }
        const grow = pixels > 0;
        let src = mask;
        let dst = new Uint8Array(mask.length);
        for (let s = 0; s < steps; s++) {
            if (grow) onePassGrow(src, dst, width, height);
            else onePassShrink(src, dst, width, height);
            const swap = src === mask ? new Uint8Array(mask.length) : src;
            src = dst;
            dst = swap;
        }
        let changed = 0;
        for (let i = 0; i < mask.length; i++) if ((mask[i] ? 1 : 0) !== (src[i] ? 1 : 0)) changed++;
        return { mask: src, changed: changed };
    }

    function count(mask) {
        let n = 0;
        for (let i = 0; i < mask.length; i++) if (mask[i]) n++;
        return n;
    }

    return { morph: morph, count: count };
});
