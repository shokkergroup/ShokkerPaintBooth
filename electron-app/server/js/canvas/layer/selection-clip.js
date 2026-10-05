/* SPB-93 Pass 94: pure global-selection -> offset-Layer pixel clipping. */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.SPBSelectionClip = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function restoreOutsideMask(candidate, original, layerWidth, layerHeight,
            originX, originY, mask, maskWidth, maskHeight) {
        const lw = Math.max(0, Math.floor(Number(layerWidth) || 0));
        const lh = Math.max(0, Math.floor(Number(layerHeight) || 0));
        const mw = Math.max(0, Math.floor(Number(maskWidth) || 0));
        const mh = Math.max(0, Math.floor(Number(maskHeight) || 0));
        const required = lw * lh * 4;
        if (!candidate || !original || candidate.length < required || original.length < required) {
            throw new TypeError('Selection clip requires complete candidate and original RGBA buffers');
        }
        if (!mask) return 0;
        if (!mw || !mh || mask.length < mw * mh) {
            throw new TypeError('Selection clip requires a complete global mask');
        }
        const ox = Math.round(Number(originX) || 0);
        const oy = Math.round(Number(originY) || 0);
        let restored = 0;
        for (let y = 0; y < lh; y++) {
            const gy = oy + y;
            for (let x = 0; x < lw; x++) {
                const gx = ox + x;
                const selected = gx >= 0 && gx < mw && gy >= 0 && gy < mh
                    && mask[gy * mw + gx] > 0;
                if (selected) continue;
                const i = (y * lw + x) * 4;
                candidate[i] = original[i];
                candidate[i + 1] = original[i + 1];
                candidate[i + 2] = original[i + 2];
                candidate[i + 3] = original[i + 3];
                restored++;
            }
        }
        return restored;
    }

    // SPB-93 Pass 102 (2026-07-17): feathered selections attenuate edits,
    // not merely admit every nonzero mask pixel at full strength. Interpolate
    // original -> candidate in premultiplied-alpha space so translucent decal
    // edges keep clean color while selection coverage fades naturally.
    function applyMask(candidate, original, layerWidth, layerHeight,
            originX, originY, mask, maskWidth, maskHeight) {
        const lw = Math.max(0, Math.floor(Number(layerWidth) || 0));
        const lh = Math.max(0, Math.floor(Number(layerHeight) || 0));
        const mw = Math.max(0, Math.floor(Number(maskWidth) || 0));
        const mh = Math.max(0, Math.floor(Number(maskHeight) || 0));
        const required = lw * lh * 4;
        if (!candidate || !original || candidate.length < required || original.length < required) {
            throw new TypeError('Selection mask requires complete candidate and original RGBA buffers');
        }
        if (!mask) return 0;
        if (!mw || !mh || mask.length < mw * mh) {
            throw new TypeError('Selection mask requires a complete global mask');
        }
        const ox = Math.round(Number(originX) || 0);
        const oy = Math.round(Number(originY) || 0);
        let attenuated = 0;
        for (let y = 0; y < lh; y++) {
            const gy = oy + y;
            for (let x = 0; x < lw; x++) {
                const gx = ox + x;
                const maskValue = gx >= 0 && gx < mw && gy >= 0 && gy < mh
                    ? mask[gy * mw + gx]
                    : 0;
                if (maskValue >= 255) continue;
                const i = (y * lw + x) * 4;
                if (maskValue <= 0) {
                    candidate[i] = original[i];
                    candidate[i + 1] = original[i + 1];
                    candidate[i + 2] = original[i + 2];
                    candidate[i + 3] = original[i + 3];
                    attenuated++;
                    continue;
                }
                const coverage = maskValue / 255;
                const originalAlpha = original[i + 3] / 255;
                const candidateAlpha = candidate[i + 3] / 255;
                const outputAlpha = originalAlpha + (candidateAlpha - originalAlpha) * coverage;
                if (outputAlpha <= 0) {
                    candidate[i] = candidate[i + 1] = candidate[i + 2] = candidate[i + 3] = 0;
                    attenuated++;
                    continue;
                }
                for (let channel = 0; channel < 3; channel++) {
                    const originalPremul = original[i + channel] * originalAlpha;
                    const candidatePremul = candidate[i + channel] * candidateAlpha;
                    const outputPremul = originalPremul + (candidatePremul - originalPremul) * coverage;
                    candidate[i + channel] = Math.round(outputPremul / outputAlpha);
                }
                candidate[i + 3] = Math.round(outputAlpha * 255);
                attenuated++;
            }
        }
        return attenuated;
    }

    // SPB-93 browser gauntlet (2026-08-08), owner verdict: tools "NEED to
    // feel more Photoshop like and WORK." Before: an 80 px Layer Brush drag
    // over 11 pointer samples took 361 ms, painted 0 visible pixels, and made
    // 0 undo entries because an inactive empty Zone mask clipped every dab.
    // After: the identical drag took 472 ms, added 1,396 visible magenta
    // screenshot pixels, and round-tripped through Ctrl+Z / Ctrl+Shift+Z.
    // Decide whether a mask is active in O(1); alpha lock still takes priority,
    // while Layer tools only honor a Zone selection that is explicitly active.
    function resolveActiveMask(options) {
        const opts = options || {};
        const expectedLength = Math.max(0, Math.floor(Number(opts.expectedLength) || 0));
        const alphaLockMask = opts.alphaLockMask;
        if (alphaLockMask && alphaLockMask.length === expectedLength) return alphaLockMask;
        const regionMask = opts.regionMask;
        if (!regionMask || regionMask.length !== expectedLength) return null;
        if (opts.layerMode && opts.useRegion !== true) return null;
        return regionMask;
    }

    return { restoreOutsideMask, applyMask, resolveActiveMask };
});
