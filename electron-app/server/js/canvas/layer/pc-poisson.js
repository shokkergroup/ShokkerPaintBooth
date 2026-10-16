/* Algorithm ported from PhotoCraft crates/algo/src/poisson.rs
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0 - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript (Float32Array). Lane PORT-W2 (strokes), 2026-10-09.
 *
 * Gradient-domain ("Poisson") blending for the Healing Brush: P. Perez, M. Gangnet, A. Blake, "Poisson Image Editing",
 * SIGGRAPH 2003. With the guidance field v = grad(src) the solution is f = src + h where h is the harmonic
 * ("membrane") interpolant of the boundary mismatch (dst - src); solved by cascadic multigrid + SOR.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcPoisson = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const TOL = 2e-5;
    const FINE_ITERS = 30;
    const FINE_OMEGA = 1.7;

    // unknown: Uint8Array(w*h) (1 = unknown), v: Float32Array(w*h) known values in, solution out
    function solveMembrane(w, h, unknown, v) { solveRec(w, h, unknown, v, 0); }

    function solveRec(w, h, unknown, v, depth) {
        let nUnknown = 0, nKnown = 0, sumKnown = 0;
        for (let i = 0; i < unknown.length; i++) {
            if (unknown[i]) nUnknown++; else { nKnown++; sumKnown += v[i]; }
        }
        if (nUnknown === 0 || nKnown === 0) return;
        if (w >= 8 && h >= 8 && nUnknown > 64 && depth < 16) {
            const cw = (w + 1) >> 1, ch = (h + 1) >> 1;
            const cu = new Uint8Array(cw * ch).fill(1);
            const cv = new Float32Array(cw * ch);
            for (let cy = 0; cy < ch; cy++) {
                for (let cx = 0; cx < cw; cx++) {
                    let s = 0, n = 0;
                    for (let k = 0; k < 4; k++) {
                        const x = cx * 2 + (k & 1), y = cy * 2 + (k >> 1);
                        if (x < w && y < h && !unknown[y * w + x]) { s += v[y * w + x]; n++; }
                    }
                    if (n > 0) { cu[cy * cw + cx] = 0; cv[cy * cw + cx] = s / n; }
                }
            }
            solveRec(cw, ch, cu, cv, depth + 1);
            for (let y = 0; y < h; y++) {
                let fy = (y + 0.5) / 2 - 0.5; fy = fy < 0 ? 0 : (fy > ch - 1 ? ch - 1 : fy);
                const y0 = Math.floor(fy), y1 = Math.min(y0 + 1, ch - 1), ty = fy - y0;
                for (let x = 0; x < w; x++) {
                    if (!unknown[y * w + x]) continue;
                    let fx = (x + 0.5) / 2 - 0.5; fx = fx < 0 ? 0 : (fx > cw - 1 ? cw - 1 : fx);
                    const x0 = Math.floor(fx), x1 = Math.min(x0 + 1, cw - 1), tx = fx - x0;
                    const a = cv[y0 * cw + x0] + (cv[y0 * cw + x1] - cv[y0 * cw + x0]) * tx;
                    const b = cv[y1 * cw + x0] + (cv[y1 * cw + x1] - cv[y1 * cw + x0]) * tx;
                    v[y * w + x] = a + (b - a) * ty;
                }
            }
            sor(w, h, unknown, v, FINE_ITERS, FINE_OMEGA);
        } else {
            const mean = sumKnown / nKnown;
            for (let i = 0; i < v.length; i++) if (unknown[i]) v[i] = mean;
            sor(w, h, unknown, v, 2000, 1.85);
        }
    }

    function sor(w, h, unknown, v, maxIter, omega) {
        let count = 0;
        for (let i = 0; i < unknown.length; i++) if (unknown[i]) count++;
        const idx = new Int32Array(count), mask = new Uint8Array(count);
        let c = 0;
        for (let i = 0; i < unknown.length; i++) {
            if (!unknown[i]) continue;
            const x = i % w, y = (i / w) | 0;
            idx[c] = i;
            mask[c] = (x > 0 ? 1 : 0) | (x + 1 < w ? 2 : 0) | (y > 0 ? 4 : 0) | (y + 1 < h ? 8 : 0);
            c++;
        }
        for (let it = 0; it < maxIter; it++) {
            let maxD = 0;
            for (let k = 0; k < count; k++) {
                const i = idx[k], m = mask[k];
                let s, n;
                if (m === 15) { s = v[i - 1] + v[i + 1] + v[i - w] + v[i + w]; n = 4; }
                else {
                    s = 0; n = 0;
                    if (m & 1) { s += v[i - 1]; n++; }
                    if (m & 2) { s += v[i + 1]; n++; }
                    if (m & 4) { s += v[i - w]; n++; }
                    if (m & 8) { s += v[i + w]; n++; }
                    if (n === 0) continue;
                }
                const d = omega * (s / n - v[i]);
                v[i] += d;
                const ad = d < 0 ? -d : d;
                if (ad > maxD) maxD = ad;
            }
            if (maxD < TOL) break;
        }
    }

    return Object.freeze({ solveMembrane });
});
