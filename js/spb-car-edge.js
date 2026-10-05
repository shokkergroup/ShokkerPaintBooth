/* spb-car-edge.js - recognise WHICH iRacing car a finished paint belongs to, from the paint itself (SPB-AI 2026-10-02).
   Most real paints (about 7 in 10) have overwritten the template's brown dead space, so the layout fingerprint has nothing to read. What every paint of one car still shares is WHERE the panel
   outlines are: a strong colour edge falls along them in nearly every livery. js/spb-car-edge-data.js holds, per iRacing car folder, the probability of an edge at each 64x64 cell, learned from
   thousands of real driver paints (scripts: _easy_claude_work/corpus/s14_export_edge.py; no artwork is stored). The query paint's own edge map is scored against every folder with a naive-Bayes
   log-likelihood, Z-normalised per car by the scores OTHER cars' paints get against it (a broad fingerprint otherwise 'wins' for cars it has never seen). Measured on held-out paints (50 car folders,
   2,295 paints): the right car family is on top 95.3% of the time; at z >= 4 it accepts 87.1% of known cars' paints (85.1% with the right family) and wrongly accepts 10.2% of paints of cars that are
   NOT in the model, so the caller treats a recognition that nothing else corroborates as a PROPOSAL the buyer confirms, never as silent knowledge.
   window.SpbCarEdge = { recognize(canvas), ready(), KNOWN_T }.  ES5. */
(function () {
    'use strict';
    var S = 256, M = null;

    function build() {
        if (M) return M;
        var raw = window.SPB_CAR_EDGE; if (!raw || !raw.folders || !raw.folders.length) return null;
        var R = raw.res, N = R * R, F = [], nullP = new Float32Array(N), i;
        raw.folders.forEach(function (f) {
            var bin = atob(f.p), l1 = new Float32Array(N), l0 = new Float32Array(N), p;
            for (i = 0; i < N; i++) { p = bin.charCodeAt(i) / 255; p = Math.min(1 - raw.eps, Math.max(raw.eps, p)); nullP[i] += p; l1[i] = Math.log(p); l0[i] = Math.log(1 - p); }
            F.push({ k: f.k, name: f.name, n: f.n, fam: f.fam, l1: l1, l0: l0, mu: f.mu, sd: f.sd });
        });
        var n1 = new Float32Array(N), n0 = new Float32Array(N);
        for (i = 0; i < N; i++) { var q = Math.min(1 - raw.eps, Math.max(raw.eps, nullP[i] / F.length)); n1[i] = Math.log(q); n0[i] = Math.log(1 - q); }
        M = { R: R, N: N, tau: raw.tau, F: F, n1: n1, n0: n0, knownZ: raw.knownZ || 4 };
        return M;
    }

    // the paint at 256x256 (successive halving ~ box average, like the corpus cache), as luminance
    function luminance(src) {
        var w = src.width, h = src.height, cur = src, c, cx;
        while (w > S * 2 || h > S * 2) {
            var nw = Math.max(S, Math.floor(w / 2)), nh = Math.max(S, Math.floor(h / 2));
            c = document.createElement('canvas'); c.width = nw; c.height = nh; cx = c.getContext('2d', { willReadFrequently: true }); cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = 'high'; cx.drawImage(cur, 0, 0, nw, nh); cur = c; w = nw; h = nh;
        }
        c = document.createElement('canvas'); c.width = c.height = S; cx = c.getContext('2d', { willReadFrequently: true }); cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = 'high'; cx.drawImage(cur, 0, 0, S, S);
        var px = cx.getImageData(0, 0, S, S).data, L = new Float32Array(S * S), i, a;
        for (i = 0; i < S * S; i++) { a = px[i * 4 + 3] / 255; L[i] = (0.3 * px[i * 4] + 0.59 * px[i * 4 + 1] + 0.11 * px[i * 4 + 2]) * a + 0.0 * (1 - a); }
        return L;
    }

    function edgeBits(L, R, tau) {
        var bits = new Uint8Array(R * R), k = S / R, x, y, gx, gy, at = function (xx, yy) { xx = xx < 0 ? 0 : (xx > S - 1 ? S - 1 : xx); yy = yy < 0 ? 0 : (yy > S - 1 ? S - 1 : yy); return L[yy * S + xx]; }, lim = tau * 8, lim2 = lim * lim, n = 0;
        for (y = 0; y < S; y++) for (x = 0; x < S; x++) {
            gx = (at(x + 1, y - 1) + 2 * at(x + 1, y) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x - 1, y) + at(x - 1, y + 1));
            gy = (at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x, y - 1) + at(x + 1, y - 1));
            if (gx * gx + gy * gy > lim2) { bits[Math.floor(y / k) * R + Math.floor(x / k)] = 1; n++; }
        }
        return { bits: bits, n: n };
    }

    function recognize(src) {
        var m = build(); if (!m || !src || !src.width) return null;
        var eb; try { eb = edgeBits(luminance(src), m.R, m.tau); } catch (e) { return null; }
        if (eb.n < 100) return null;                                    // a flat / empty sheet has no outlines to read
        var bits = eb.bits, N = m.N, i, nul = 0, res = [];
        for (i = 0; i < N; i++) nul += bits[i] ? m.n1[i] : m.n0[i];
        m.F.forEach(function (f) { var ll = 0; for (i = 0; i < N; i++) ll += bits[i] ? f.l1[i] : f.l0[i]; var llr = (ll - nul) / N; res.push({ k: f.k, name: f.name, n: f.n, fam: f.fam, llr: llr, z: (llr - f.mu) / f.sd }); });
        res.sort(function (a, b) { return b.z - a.z; });
        var best = res[0], second = null, j;
        for (j = 1; j < res.length; j++) if (res[j].fam !== best.fam) { second = res[j]; break; }        // the runner-up from ANOTHER family (twin folders share one UV layout)
        var twins = res.filter(function (r) { return r.fam === best.fam; }).map(function (r) { return r.k; });
        return { key: best.k, name: best.name, fam: best.fam, z: best.z, llr: best.llr, margin: second ? best.z - second.z : 0, known: best.z >= m.knownZ, twins: twins, top: res.slice(0, 3).map(function (r) { return { name: r.name, z: Math.round(r.z * 10) / 10 }; }), edges: eb.n };
    }

    window.SpbCarEdge = { recognize: recognize, ready: function () { return !!build(); }, knownZ: function () { var m = build(); return m ? m.knownZ : null; } };
})();
