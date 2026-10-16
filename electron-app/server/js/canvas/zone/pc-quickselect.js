/* ============================================================================
 * SPB PC QUICK SELECT  (lane PORT-W6, 2026-10-09)
 *
 * Algorithm ported from PhotoCraft crates/algo/src/segment/quick.rs (stroke
 * seeds, GMM colour model, geodesic background sampling, contrast-sensitive
 * graph cut), segment/gmm.rs (k-means++ / EM Gaussian mixtures),
 * segment/maxflow.rs (Boykov-Kolmogorov min-cut) and segment/mod.rs
 * (grid_cut, contrast_beta, keep_seeded, finish_region / refine_band,
 * antialias_u8, trim_region).
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0
 * (MIT elected) - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript on typed arrays; RGB read from SPB's
 * paint buffer (paintImageData RGBA, transparent composited over mid gray as
 * PhotoCraft does); xorshift replaced by mulberry32 for k-means++ seeding;
 * rayon parallelism dropped (single thread). Live drag updates run at a
 * smaller working resolution (WORK_LIVE); the commit on mouse-up runs at the
 * PhotoCraft budget (160 000 px) and re-cuts the boundary at full resolution.
 * Cites (as PhotoCraft does): Boykov & Jolly 2001; Boykov & Kolmogorov 2004;
 * Criminisi, Sharp & Blake "GeoS" 2008; Liu, Sun & Shum "Paint Selection" 2009.
 *
 * Owner verdict 2026-10-09: "our tools basically SUCK". SPB had no brush-like
 * smart selection. This adds Photoshop's Quick Selection as an OPTION of the
 * Wand (checkbox "Quick" + brush Size + Enhance), no new toolbar button.
 * Shift adds, Alt subtracts (same as the Wand). Output is the standard SPB
 * region mask (Uint8Array w*h, 0..255) so Feather / Grow / Fill / Undo work.
 *
 * Disable with  window.SPB_PC_W6_OFF = true  (the Quick option is ignored and
 * the Wand behaves exactly as before).
 * ==========================================================================*/
(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcQuick = api;
})(typeof window !== 'undefined' ? window : globalThis, function (G) {
    'use strict';

    const QREG = 6e-4;          // covariance ridge for the (tiny) stroke sample
    const EDGE = 0.06;          // geodesic distance that counts as "behind an edge"
    const MIN_STEP = 0.03;      // neighbour colour steps below this never count as edges
    const KAPPA = 2.0;          // data-term weight of the geodesic distance
    const GAMMA = 50.0;
    const WORK_PX = 200000;     // PhotoCraft default is 160000; W6 raises the final cut slightly for crisper edges
    const WORK_LIVE = 70000;    // smaller budget while the pointer is still moving
    let PRIOR = 0.15;   // W6: weaker pull to the coarse label (PhotoCraft 0.4) so full-res colour edges win
    const FREE = 0, HARD_FG = 1, HARD_BG = 2;
    // PORT-W5B (2026-10-09, flag SPB_W5B_OFF): soft-gradient panels.  Measured on 6 car-side fixtures (tools_port/w5b/test_quick_grad.js)
    // the old code covered 21-60 % of a panel with ONE stroke: (1) the work window was stroke bbox +-512 px, so a long panel was cut at
    // the window edge; (2) the foreground GMM is fitted to the stroke pixels only, so colours further along a gradient had a huge FG cost
    // and the cut stopped / grew in steps (a second Shift stroke widened the model).  Fixes: a continuity (minimax-path) FG prior, an FG
    // refit from the first cut, and window growth while the selection still touches the window border.
    const CONT_T0_MIN = 0.012;  // smallest colour step per working px that counts as a real colour change
    const CONT_BASE = -12;      // FG cost of a pixel reachable from the stroke through smooth steps only (strongly FG: beats the BG-GMM density, which can reach -8)
    const CONT_HI = 50;         // ... rising to this when the smoothest path crosses a step >= CONT_UP * t0
    const CONT_EDGE_SCALE = 0.15;         // pairwise weight kept across the border of the continuity set (it is a real colour step by construction)
    const CONT_T0_FLOOR = 0.006, CONT_T0_SLOPE = 0.0015;
    const CONT_LO = 2.2, CONT_UP = 3.0;   // see contCost()
    const MAX_GROW = 3;         // window growth passes (final commit)
    const MAX_GROW_LIVE = 2;    // ... while the pointer is still moving (keeps the preview responsive; the commit grows fully)
    function w5bOff() { return !!(G && G.SPB_W5B_OFF); }
    // [SPB-TFX1 2026-10-09 TA-015] Quick Select cost (real car, 2048): every drag step ran the whole graph-cut pipeline at 70 000 working px ON THE MAIN THREAD
    // (p50 ~300 ms / move) and the commit re-grew the window from scratch (1.3-1.5 s).  Now: the live steps run in a Web Worker (the main thread only
    // posts the points and draws a low-res label map scaled over its window), the commit starts from the window margin the live passes found, reuses
    // the last live cut when nothing changed since, works at the live budget and only post-processes the selected bbox (bit-identical finish).
    // Kill switch: window.SPB_TFX1_OFF = true restores the W5B behaviour; no Worker -> the old in-thread path.
    function tfxOff() { return !!(G && G.SPB_TFX1_OFF); }
    const WORK_FINAL = 70000, BAND_T = 192;
    const SELF_SRC = (G && G.document && G.document.currentScript && G.document.currentScript.src) || '';
    const SQ2 = Math.SQRT2;

    // ------------------------------------------------------------ helpers
    function scaleFor(w, h, maxPx) {
        return Math.max(1, Math.ceil(Math.sqrt((w * h) / Math.max(1, maxPx))));
    }

    function mulberry32(a) {
        return function () {
            a |= 0; a = (a + 0x6D2B79F5) | 0;
            let t = Math.imul(a ^ (a >>> 15), 1 | a);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }

    // RGB image: Float32Array(3*w*h), samples 0..1.
    function makeImg(w, h) { return { w, h, px: new Float32Array(w * h * 3) }; }

    // Box-averaged RGB over rect {x0,y0,x1,y1} of an RGBA source, step >= 1.
    // Transparent pixels are composited over mid gray (PhotoCraft RgbImage::from_rgba).
    function rgbScaled(src, rect, step, stride) {
        stride = stride || 1;   // [SPB-TFX1 2026-10-09 TA-015] big working steps (>= 8 canvas px) average a sparse sample grid instead of every source pixel
        const rw = rect.x1 - rect.x0, rh = rect.y1 - rect.y0;
        const ow = Math.ceil(rw / step), oh = Math.ceil(rh / step);
        const out = makeImg(ow, oh); out.step = step;   // PORT-W5B: working scale, needed by the gradient prior
        const d = src.data, sw = src.w, op = out.px;
        for (let oy = 0; oy < oh; oy++) {
            const ya = rect.y0 + oy * step, yb = Math.min(ya + step, rect.y1);
            for (let ox = 0; ox < ow; ox++) {
                const xa = rect.x0 + ox * step, xb = Math.min(xa + step, rect.x1);
                let r = 0, g = 0, b = 0, n = 0;
                for (let y = ya; y < yb; y += stride) {
                    let p = (y * sw + xa) * 4;
                    for (let x = xa; x < xb; x += stride, p += 4 * stride) {
                        const a = d[p + 3] / 255, ia = 0.5 * (1 - a);
                        r += d[p] / 255 * a + ia;
                        g += d[p + 1] / 255 * a + ia;
                        b += d[p + 2] / 255 * a + ia;
                        n++;
                    }
                }
                const o = (oy * ow + ox) * 3;
                op[o] = r / n; op[o + 1] = g / n; op[o + 2] = b / n;
            }
        }
        return out;
    }

    function d2px(p, i, j) {
        const x = p[i] - p[j], y = p[i + 1] - p[j + 1], z = p[i + 2] - p[j + 2];
        return x * x + y * y + z * z;
    }

    // ------------------------------------------------------------ GMM (gmm.rs)
    function makeComponent(weight, mean, cov, reg) {
        const c = [cov[0].slice(), cov[1].slice(), cov[2].slice()];
        for (let i = 0; i < 3; i++) c[i][i] += reg;
        const det = c[0][0] * (c[1][1] * c[2][2] - c[1][2] * c[2][1])
            - c[0][1] * (c[1][0] * c[2][2] - c[1][2] * c[2][0])
            + c[0][2] * (c[1][0] * c[2][1] - c[1][1] * c[2][0]);
        if (!(det > 1e-30) || !(weight > 0)) return null;
        const inv = [
            (c[1][1] * c[2][2] - c[1][2] * c[2][1]) / det, (c[0][2] * c[2][1] - c[0][1] * c[2][2]) / det, (c[0][1] * c[1][2] - c[0][2] * c[1][1]) / det,
            (c[1][2] * c[2][0] - c[1][0] * c[2][2]) / det, (c[0][0] * c[2][2] - c[0][2] * c[2][0]) / det, (c[0][2] * c[1][0] - c[0][0] * c[1][2]) / det,
            (c[1][0] * c[2][1] - c[1][1] * c[2][0]) / det, (c[0][1] * c[2][0] - c[0][0] * c[2][1]) / det, (c[0][0] * c[1][1] - c[0][1] * c[1][0]) / det,
        ];
        const logNorm = Math.log(weight) - 0.5 * Math.log(det) - 1.5 * Math.log(2 * Math.PI);
        return { weight, mean, inv, logNorm };
    }

    function logWeighted(c, z0, z1, z2) {
        const d0 = z0 - c.mean[0], d1 = z1 - c.mean[1], d2 = z2 - c.mean[2], m = c.inv;
        const q = d0 * (m[0] * d0 + m[1] * d1 + m[2] * d2)
            + d1 * (m[3] * d0 + m[4] * d1 + m[5] * d2)
            + d2 * (m[6] * d0 + m[7] * d1 + m[8] * d2);
        return c.logNorm - 0.5 * q;
    }

    // Accumulator -> component.
    function accComponent(a, total, reg) {
        if (a.n <= 0) return null;
        const m = [a.s[0] / a.n, a.s[1] / a.n, a.s[2] / a.n];
        const c = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
        for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) c[i][j] = a.ss[i][j] / a.n - m[i] * m[j];
        return makeComponent(a.n / total, m, c, reg);
    }
    function newAcc() { return { n: 0, s: [0, 0, 0], ss: [[0, 0, 0], [0, 0, 0], [0, 0, 0]] }; }
    function accAdd(a, z, w) {
        a.n += w;
        for (let i = 0; i < 3; i++) {
            a.s[i] += w * z[i];
            for (let j = 0; j < 3; j++) a.ss[i][j] += w * z[i] * z[j];
        }
    }

    // samples: flat Float32Array (n*3).
    function nearestCenter(centers, z0, z1, z2) {
        let best = 0, bd = Infinity;
        for (let i = 0; i < centers.length; i++) {
            const c = centers[i], x = c[0] - z0, y = c[1] - z1, z = c[2] - z2, d = x * x + y * y + z * z;
            if (d < bd) { bd = d; best = i; }
        }
        return best;
    }

    function kmeans(S, n, k, iters) {
        const rng = mulberry32(0x5EED + n);
        const pick0 = Math.min(n - 1, Math.floor(rng() * n));
        let centers = [[S[pick0 * 3], S[pick0 * 3 + 1], S[pick0 * 3 + 2]]];
        const dist = new Float64Array(n);
        for (let i = 0; i < n; i++) {
            const x = S[i * 3] - centers[0][0], y = S[i * 3 + 1] - centers[0][1], z = S[i * 3 + 2] - centers[0][2];
            dist[i] = x * x + y * y + z * z;
        }
        while (centers.length < k) {
            let total = 0;
            for (let i = 0; i < n; i++) total += dist[i];
            if (total <= 1e-12) break;
            let t = rng() * total, pick = n - 1;
            for (let i = 0; i < n; i++) { t -= dist[i]; if (t <= 0) { pick = i; break; } }
            const c = [S[pick * 3], S[pick * 3 + 1], S[pick * 3 + 2]];
            centers.push(c);
            for (let i = 0; i < n; i++) {
                const x = S[i * 3] - c[0], y = S[i * 3 + 1] - c[1], z = S[i * 3 + 2] - c[2];
                const d = x * x + y * y + z * z;
                if (d < dist[i]) dist[i] = d;
            }
        }
        for (let it = 0; it < iters; it++) {
            const sums = centers.map(function () { return [0, 0, 0, 0]; });
            for (let i = 0; i < n; i++) {
                const j = nearestCenter(centers, S[i * 3], S[i * 3 + 1], S[i * 3 + 2]);
                sums[j][0] += S[i * 3]; sums[j][1] += S[i * 3 + 1]; sums[j][2] += S[i * 3 + 2]; sums[j][3]++;
            }
            const nc = [];
            for (let j = 0; j < sums.length; j++) {
                if (sums[j][3] > 0) nc.push([sums[j][0] / sums[j][3], sums[j][1] / sums[j][3], sums[j][2] / sums[j][3]]);
            }
            let same = nc.length === centers.length;
            if (same) for (let j = 0; j < nc.length && same; j++) for (let q = 0; q < 3; q++) if (nc[j][q] !== centers[j][q]) { same = false; break; }
            centers = nc;
            if (same) break;
        }
        return centers;
    }

    function gmmFromLabels(S, n, labels, k, reg) {
        const acc = []; for (let i = 0; i < k; i++) acc.push(newAcc());
        for (let i = 0; i < n; i++) accAdd(acc[labels[i]], [S[i * 3], S[i * 3 + 1], S[i * 3 + 2]], 1);
        const comps = [];
        for (let i = 0; i < k; i++) { const c = accComponent(acc[i], n, reg); if (c) comps.push(c); }
        return comps.length ? { comps, reg } : null;
    }

    function gmmEm(g, S, n) {
        const k = g.comps.length, acc = []; for (let i = 0; i < k; i++) acc.push(newAcc());
        const lw = new Float64Array(k);
        for (let i = 0; i < n; i++) {
            const z0 = S[i * 3], z1 = S[i * 3 + 1], z2 = S[i * 3 + 2];
            let mx = -Infinity;
            for (let c = 0; c < k; c++) { lw[c] = logWeighted(g.comps[c], z0, z1, z2); if (lw[c] > mx) mx = lw[c]; }
            let sum = 0;
            for (let c = 0; c < k; c++) { lw[c] = Math.exp(lw[c] - mx); sum += lw[c]; }
            for (let c = 0; c < k; c++) { const r = lw[c] / sum; if (r > 1e-6) accAdd(acc[c], [z0, z1, z2], r); }
        }
        const comps = [];
        for (let c = 0; c < k; c++) { const cm = accComponent(acc[c], n, g.reg); if (cm) comps.push(cm); }
        return comps.length ? { comps, reg: g.reg } : null;
    }

    function gmmFit(S, n, k, reg) {
        if (n <= 0) return null;
        k = Math.max(1, Math.min(k, n));
        const centers = kmeans(S, n, k, 10);
        const labels = new Int32Array(n);
        for (let i = 0; i < n; i++) labels[i] = nearestCenter(centers, S[i * 3], S[i * 3 + 1], S[i * 3 + 2]);
        let g = gmmFromLabels(S, n, labels, centers.length, reg);
        if (!g) return null;
        for (let it = 0; it < 3; it++) g = gmmEm(g, S, n) || g;
        return g;
    }

    function gmmLogProb(g, z0, z1, z2) {
        const cs = g.comps, n = Math.min(cs.length, 16);
        let mx = -Infinity;
        const v = gmmLogProb._v || (gmmLogProb._v = new Float64Array(16));
        for (let i = 0; i < n; i++) { v[i] = logWeighted(cs[i], z0, z1, z2); if (v[i] > mx) mx = v[i]; }
        let s = 0;
        for (let i = 0; i < n; i++) s += Math.exp(v[i] - mx);
        return mx + Math.log(s);
    }
    function gmmNegLog(g, z0, z1, z2) {
        const v = -gmmLogProb(g, z0, z1, z2);
        return v < -50 ? -50 : (v > 200 ? 200 : v);
    }

    function broadModel() {
        const S = new Float32Array(24);
        for (let i = 0; i < 8; i++) { S[i * 3] = i & 1; S[i * 3 + 1] = (i >> 1) & 1; S[i * 3 + 2] = (i >> 2) & 1; }
        return gmmFit(S, 8, 1, 0);
    }

    // ------------------------------------------------------------ max-flow (maxflow.rs, Boykov-Kolmogorov)
    const NONE = -1, TERMINAL = -2, ORPHAN = -3, INF_DIST = 0x7fffffff, EPS = 1e-5;

    function Graph(nodes, edges) {
        this.n = nodes;
        this.first = new Int32Array(nodes).fill(NONE);
        this.trCap = new Float64Array(nodes);
        this.parent = new Int32Array(nodes).fill(NONE);
        this.isSink = new Uint8Array(nodes);
        this.ts = new Int32Array(nodes);
        this.dist = new Int32Array(nodes);
        this.active = new Uint8Array(nodes);
        const arcs = edges * 2 + 4;
        this.head = new Int32Array(arcs);
        this.next = new Int32Array(arcs);
        this.rCap = new Float64Array(arcs);
        this.na = 0;
        this.flow = 0;
    }
    Graph.prototype.addTweights = function (i, capSource, capSink) {
        const delta = this.trCap[i];
        let s = capSource, t = capSink;
        if (delta > 0) s += delta; else t -= delta;
        this.flow += Math.min(s, t);
        this.trCap[i] = s - t;
    };
    Graph.prototype.addEdge = function (i, j, cap, rev) {
        const a = this.na;
        this.head[a] = j; this.next[a] = this.first[i]; this.rCap[a] = cap; this.first[i] = a;
        this.head[a + 1] = i; this.next[a + 1] = this.first[j]; this.rCap[a + 1] = rev; this.first[j] = a + 1;
        this.na += 2;
    };
    Graph.prototype.inSource = function (i) { return this.parent[i] !== NONE && !this.isSink[i]; };
    Graph.prototype.maxflow = function () {
        const n = this.n, first = this.first, trCap = this.trCap, parent = this.parent, isSink = this.isSink;
        const ts = this.ts, dist = this.dist, active = this.active, head = this.head, next = this.next, rCap = this.rCap;
        const cap = n + 2;
        const q = new Int32Array(cap);
        let qh = 0, qt = 0, qn = 0;
        const pushBack = function (v) { q[qt] = v; qt = (qt + 1) % cap; qn++; };
        const pushFront = function (v) { qh = (qh - 1 + cap) % cap; q[qh] = v; qn++; };
        const popFront = function () { const v = q[qh]; qh = (qh + 1) % cap; qn--; return v; };
        const orphans = []; let oh = 0;
        for (let i = 0; i < n; i++) {
            active[i] = 0; ts[i] = 0;
            if (Math.abs(trCap[i]) > EPS) {
                isSink[i] = trCap[i] < 0 ? 1 : 0;
                parent[i] = TERMINAL; dist[i] = 1; active[i] = 1; pushBack(i);
            } else parent[i] = NONE;
        }
        let time = 0;
        const self = this;
        while (qn > 0) {
            const i = popFront();
            active[i] = 0;
            if (parent[i] === NONE) continue;
            let contact = NONE;
            const sink = isSink[i];
            let a = first[i];
            while (a !== NONE) {
                const j = head[a];
                const c = sink ? rCap[a ^ 1] : rCap[a];
                if (c > EPS) {
                    if (parent[j] === NONE) {
                        isSink[j] = sink; parent[j] = a ^ 1; ts[j] = ts[i]; dist[j] = dist[i] + 1;
                        if (!active[j]) { active[j] = 1; pushBack(j); }
                    } else if (isSink[j] !== sink) {
                        contact = sink ? (a ^ 1) : a;
                        break;
                    } else if (ts[j] <= ts[i] && dist[j] > dist[i]) {
                        parent[j] = a ^ 1; ts[j] = ts[i]; dist[j] = dist[i] + 1;
                    }
                }
                a = next[a];
            }
            if (contact === NONE) continue;
            if (!active[i]) { active[i] = 1; pushFront(i); }
            time++;
            orphans.length = 0; oh = 0;
            self._augment(contact, orphans);
            while (oh < orphans.length) {
                const o = orphans[oh++];
                self._adopt(o, time, orphans, pushBack);
            }
        }
        return this.flow;
    };
    Graph.prototype._augment = function (m, orphans) {
        const head = this.head, parent = this.parent, rCap = this.rCap, trCap = this.trCap;
        const u = head[m ^ 1], v = head[m];
        let b = rCap[m], x = u;
        for (;;) { const a = parent[x]; if (a === TERMINAL) break; b = Math.min(b, rCap[a ^ 1]); x = head[a]; }
        b = Math.min(b, trCap[x]);
        x = v;
        for (;;) { const a = parent[x]; if (a === TERMINAL) break; b = Math.min(b, rCap[a]); x = head[a]; }
        b = Math.min(b, -trCap[x]);
        rCap[m ^ 1] += b; rCap[m] -= b;
        x = u;
        for (;;) {
            const a = parent[x]; if (a === TERMINAL) break;
            rCap[a] += b; rCap[a ^ 1] -= b;
            const up = head[a];
            if (rCap[a ^ 1] <= EPS) { parent[x] = ORPHAN; orphans.push(x); }
            x = up;
        }
        trCap[x] -= b;
        if (trCap[x] <= EPS) { parent[x] = ORPHAN; orphans.push(x); }
        x = v;
        for (;;) {
            const a = parent[x]; if (a === TERMINAL) break;
            rCap[a ^ 1] += b; rCap[a] -= b;
            const up = head[a];
            if (rCap[a] <= EPS) { parent[x] = ORPHAN; orphans.push(x); }
            x = up;
        }
        trCap[x] += b;
        if (trCap[x] >= -EPS) { parent[x] = ORPHAN; orphans.push(x); }
        this.flow += b;
    };
    Graph.prototype._adopt = function (i, time, orphans, pushBack) {
        const head = this.head, next = this.next, rCap = this.rCap, parent = this.parent, isSink = this.isSink;
        const ts = this.ts, dist = this.dist, active = this.active, first = this.first;
        const sink = isSink[i];
        let best = NONE, dMin = INF_DIST, a = first[i];
        while (a !== NONE) {
            const c = sink ? rCap[a] : rCap[a ^ 1];
            const j = head[a];
            if (c > EPS && isSink[j] === sink && parent[j] !== NONE) {
                let d = 0, k = j;
                for (;;) {
                    if (ts[k] === time) { d = Math.min(INF_DIST, d + dist[k]); break; }
                    const pa = parent[k];
                    d++;
                    if (pa === TERMINAL) { ts[k] = time; dist[k] = 1; break; }
                    if (pa === ORPHAN) { d = INF_DIST; break; }
                    k = head[pa];
                }
                if (d < INF_DIST) {
                    if (d < dMin) { best = a; dMin = d; }
                    k = j; let dd = d;
                    while (ts[k] !== time) { ts[k] = time; dist[k] = dd; dd--; k = head[parent[k]]; }
                }
            }
            a = next[a];
        }
        if (best !== NONE) { parent[i] = best; ts[i] = time; dist[i] = dMin + 1; return; }
        parent[i] = NONE;
        a = first[i];
        while (a !== NONE) {
            const j = head[a], pj = parent[j];
            if (isSink[j] === sink && pj !== NONE) {
                const c = sink ? rCap[a] : rCap[a ^ 1];
                if (c > EPS && !active[j]) { active[j] = 1; pushBack(j); }
                if (pj !== TERMINAL && pj !== ORPHAN && head[pj] === i) { parent[j] = ORPHAN; orphans.push(j); }
            }
            a = next[a];
        }
    };

    // ------------------------------------------------------------ segment/mod.rs
    // 8-connected forward neighbours: (dx, dy, length)
    const NB = [[1, 0, 1], [0, 1, 1], [1, 1, SQ2], [-1, 1, SQ2]];

    function contrastBeta(img, stride) {
        const w = img.w, h = img.h, p = img.px;
        stride = stride || 1;   // [SPB-TFX1 2026-10-09 TA-015] refine tiles sample every 2nd pixel (the mean colour step of a 216x216 tile is very stable)
        let sum = 0, n = 0;
        for (let y = 0; y < h; y += stride) {
            for (let x = 0; x < w; x += stride) {
                const i = (y * w + x) * 3;
                for (let k = 0; k < 4; k++) {
                    const nx = x + NB[k][0], ny = y + NB[k][1];
                    if (nx >= 0 && nx < w && ny < h) { sum += d2px(p, i, (ny * w + nx) * 3); n++; }
                }
            }
        }
        return (n === 0 || sum <= 1e-12) ? 0 : n / (2 * sum);
    }

    // Binary labelling by one min cut. costFg/costBg per pixel, fixed[] FREE/HARD_FG/HARD_BG.
    function gridCut(img, costFg, costBg, fixed, gamma, beta, cont) {   // cont (PORT-W5B, optional): 1 = smoothly connected to the stroke; the boundary of that set is a real edge -> cheap to cut
        const w = img.w, h = img.h, n = w * h, p = img.px;
        const idx = new Int32Array(n).fill(-1);
        let count = 0;
        for (let i = 0; i < n; i++) if (fixed[i] === FREE) idx[i] = count++;
        const out = new Uint8Array(n);
        for (let i = 0; i < n; i++) out[i] = fixed[i] === HARD_FG ? 1 : 0;
        if (count === 0) return out;
        const g = new Graph(count, count * 4);
        for (let i = 0; i < n; i++) if (idx[i] >= 0) g.addTweights(idx[i], costBg[i], costFg[i]);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const i = y * w + x;
                for (let k = 0; k < 4; k++) {
                    const nx = x + NB[k][0], ny = y + NB[k][1];
                    if (nx < 0 || nx >= w || ny >= h) continue;
                    const j = ny * w + nx;
                    const ii = idx[i], jj = idx[j];
                    if (ii < 0 && jj < 0) continue;
                    let wt = gamma * Math.exp(-beta * d2px(p, i * 3, j * 3)) / NB[k][2];
                    if (cont && cont[i] !== cont[j]) wt *= CONT_EDGE_SCALE;
                    if (ii >= 0 && jj >= 0) g.addEdge(ii, jj, wt, wt);
                    else if (ii >= 0) { if (fixed[j] === HARD_FG) g.addTweights(ii, wt, 0); else g.addTweights(ii, 0, wt); }
                    else { if (fixed[i] === HARD_FG) g.addTweights(jj, wt, 0); else g.addTweights(jj, 0, wt); }
                }
            }
        }
        g.maxflow();
        for (let i = 0; i < n; i++) if (idx[i] >= 0) out[i] = g.inSource(idx[i]) ? 1 : 0;
        return out;
    }

    function components(mask, w, h) {
        const lab = new Int32Array(w * h), sizes = [0], stack = [];
        for (let s = 0; s < w * h; s++) {
            if (!mask[s] || lab[s] !== 0) continue;
            const l = sizes.length; sizes.push(0); lab[s] = l; stack.push(s);
            while (stack.length) {
                const i = stack.pop(); sizes[l]++;
                const x = i % w, y = (i - x) / w;
                for (let dy = -1; dy <= 1; dy++) {
                    const ny = y + dy; if (ny < 0 || ny >= h) continue;
                    for (let dx = -1; dx <= 1; dx++) {
                        const nx = x + dx; if (nx < 0 || nx >= w) continue;
                        const j = ny * w + nx;
                        if (mask[j] && lab[j] === 0) { lab[j] = l; stack.push(j); }
                    }
                }
            }
        }
        return { lab, sizes };
    }

    function keepSeeded(mask, seeds, w, h) {
        const c = components(mask, w, h), keep = new Uint8Array(c.sizes.length);
        for (let i = 0; i < c.lab.length; i++) if (seeds[i] && c.lab[i] !== 0) keep[c.lab[i]] = 1;
        const out = new Uint8Array(w * h);
        for (let i = 0; i < out.length; i++) out[i] = (c.lab[i] !== 0 && keep[c.lab[i]]) ? 1 : 0;
        return out;
    }

    // mask: Uint8Array 0/255 -> soft 3x3 edge (PhotoCraft antialias_u8)
    function antialiasU8(mask, w, h) {
        const src = new Uint8Array(mask);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const v = src[y * w + x];
                let sum = 0, edge = false;
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        const xx = x + dx, yy = y + dy;
                        const nv = (xx < 0 || yy < 0 || xx >= w || yy >= h) ? v : src[yy * w + xx];
                        if (nv !== v) edge = true;
                        sum += nv;
                    }
                }
                if (edge) {
                    const avg = sum / (9 * 255);
                    const f = v > 127 ? 0.5 + 0.5 * avg : 0.5 * avg;
                    mask[y * w + x] = Math.round(f * 255);
                }
            }
        }
    }

    function trimRegion(bbox, mask) {
        const w = bbox.x1 - bbox.x0, h = mask.length / w;
        let x0 = Infinity, y0 = Infinity, x1 = 0, y1 = 0;
        for (let y = 0; y < h; y++) {
            let a = -1, b = -1;
            for (let x = 0; x < w; x++) if (mask[y * w + x]) { if (a < 0) a = x; b = x; }
            if (a >= 0) { if (a < x0) x0 = a; if (b + 1 > x1) x1 = b + 1; if (y < y0) y0 = y; y1 = y + 1; }
        }
        if (x0 === Infinity) return null;
        const nw = x1 - x0, out = new Uint8Array(nw * (y1 - y0));
        for (let y = y0; y < y1; y++) out.set(mask.subarray(y * w + x0, y * w + x1), (y - y0) * nw);
        return { bbox: { x0: bbox.x0 + x0, y0: bbox.y0 + y0, x1: bbox.x0 + x1, y1: bbox.y0 + y1 }, mask: out };
    }

    // Full-resolution graph cut inside the band blocks (refine_band).
    function refineBand(src, win, step, low, band, lw, lh, fg, bg, mask, sub) {
        sub = sub || win;   // [SPB-TFX1 2026-10-09 TA-015] mask covers only `sub` (a tile-aligned part of the window) when given
        const T = BAND_T, HALO = 12, w = sub.x1 - sub.x0;
        const block = function (x, y) {
            return Math.min(Math.floor((y - win.y0) / step), lh - 1) * lw + Math.min(Math.floor((x - win.x0) / step), lw - 1);
        };
        for (let ty = sub.y0; ty < sub.y1; ty += T) {
            for (let tx = sub.x0; tx < sub.x1; tx += T) {
                const t = { x0: tx, y0: ty, x1: Math.min(tx + T, win.x1), y1: Math.min(ty + T, win.y1) };
                const bx0 = Math.floor((t.x0 - win.x0) / step), by0 = Math.floor((t.y0 - win.y0) / step);
                const bx1 = Math.min(Math.floor((t.x1 - 1 - win.x0) / step), lw - 1), by1 = Math.min(Math.floor((t.y1 - 1 - win.y0) / step), lh - 1);
                let any = false;
                for (let by = by0; by <= by1 && !any; by++) for (let bx = bx0; bx <= bx1; bx++) if (band[by * lw + bx]) { any = true; break; }
                if (!any) continue;
                const r = { x0: Math.max(t.x0 - HALO, win.x0), y0: Math.max(t.y0 - HALO, win.y0), x1: Math.min(t.x1 + HALO, win.x1), y1: Math.min(t.y1 + HALO, win.y1) };
                const img = rgbScaled(src, r, 1);
                const rw = r.x1 - r.x0, rh = r.y1 - r.y0;
                const fixed = new Uint8Array(rw * rh), cfg = new Float32Array(rw * rh), cbg = new Float32Array(rw * rh);
                let fx0 = rw, fy0 = rh, fx1 = -1, fy1 = -1;
                let lp0 = -1, lp1 = -1, lp2 = -1, lnf = 0, lnb = 0;   // [SPB-TFX1 2026-10-09 TA-015] same colour as the previous band pixel -> same model costs (exact, flat paint repeats a lot)
                for (let yy = 0; yy < rh; yy++) {
                    for (let xx = 0; xx < rw; xx++) {
                        const i = yy * rw + xx, b = block(r.x0 + xx, r.y0 + yy), lab = low[b];
                        if (!band[b]) { fixed[i] = lab ? HARD_FG : HARD_BG; continue; }
                        if (xx < fx0) fx0 = xx; if (xx > fx1) fx1 = xx; if (yy < fy0) fy0 = yy; fy1 = yy;
                        const o = i * 3, p0 = img.px[o], p1 = img.px[o + 1], p2 = img.px[o + 2];
                        if (p0 !== lp0 || p1 !== lp1 || p2 !== lp2) { lp0 = p0; lp1 = p1; lp2 = p2; lnf = gmmNegLog(fg, p0, p1, p2); lnb = gmmNegLog(bg, p0, p1, p2); }
                        cfg[i] = lnf + (lab ? 0 : PRIOR);
                        cbg[i] = lnb + (lab ? PRIOR : 0);
                    }
                }
                let cut;
                if (tfxOff()) cut = gridCut(img, cfg, cbg, fixed, 50, contrastBeta(img));
                else if (fx1 < 0) { cut = new Uint8Array(rw * rh); for (let i = 0; i < cut.length; i++) cut[i] = fixed[i] === HARD_FG ? 1 : 0; }
                else {   // [SPB-TFX1 2026-10-09 TA-015] graph over the band pixels' bbox (+1 px so their fixed neighbours stay in) instead of the whole 216x216 tile
                    const beta = contrastBeta(img, 2);
                    const cx0 = Math.max(0, fx0 - 1), cy0 = Math.max(0, fy0 - 1), cx1 = Math.min(rw, fx1 + 2), cy1 = Math.min(rh, fy1 + 2);
                    const cw2 = cx1 - cx0, ch2 = cy1 - cy0;
                    const cimg = { w: cw2, h: ch2, px: new Float32Array(cw2 * ch2 * 3) };
                    const cfix = new Uint8Array(cw2 * ch2), ccf = new Float32Array(cw2 * ch2), ccb = new Float32Array(cw2 * ch2);
                    for (let yy = 0; yy < ch2; yy++) {
                        const si = (cy0 + yy) * rw + cx0, di = yy * cw2;
                        cimg.px.set(img.px.subarray(si * 3, (si + cw2) * 3), di * 3);
                        cfix.set(fixed.subarray(si, si + cw2), di); ccf.set(cfg.subarray(si, si + cw2), di); ccb.set(cbg.subarray(si, si + cw2), di);
                    }
                    const sc = gridCut(cimg, ccf, ccb, cfix, 50, beta);
                    cut = new Uint8Array(rw * rh);
                    for (let i = 0; i < cut.length; i++) cut[i] = fixed[i] === HARD_FG ? 1 : 0;
                    for (let yy = 0; yy < ch2; yy++) for (let xx = 0; xx < cw2; xx++) cut[(cy0 + yy) * rw + cx0 + xx] = sc[yy * cw2 + xx];
                }
                const cw = t.x1 - t.x0, ch = t.y1 - t.y0;
                for (let yy = 0; yy < ch; yy++) {
                    const sy = t.y0 - r.y0 + yy, sx = t.x0 - r.x0;
                    const o = (t.y0 - sub.y0 + yy) * w + (t.x0 - sub.x0);
                    for (let xx = 0; xx < cw; xx++) mask[o + xx] = cut[sy * rw + sx + xx] ? 255 : 0;
                }
            }
        }
    }

    // [SPB-TFX1 2026-10-09 TA-015] same output as finishRegionOld, but only the selected bbox (+ band) is upscaled / re-cut / antialiased / trimmed instead of the whole
    // work window (up to ~2000x2000 px of zeros), and the band is a separable min/max instead of a (2*BR+1)^2 scan per working px.
    function finishRegionFast(src, win, step, low, lw, lh, models, refine, BR) {
        BR = BR || 2;
        let lx0 = lw, ly0 = lh, lx1 = -1, ly1 = -1;
        for (let y = 0; y < lh; y++) {
            const o = y * lw;
            for (let x = 0; x < lw; x++) if (low[o + x]) { if (x < lx0) lx0 = x; if (x > lx1) lx1 = x; if (y < ly0) ly0 = y; ly1 = y; }
        }
        if (lx1 < 0) return null;
        const T = BAND_T;
        const bx0 = Math.max(0, lx0 - BR - 1), bx1 = Math.min(lw, lx1 + BR + 2), by0 = Math.max(0, ly0 - BR - 1), by1 = Math.min(lh, ly1 + BR + 2);
        const rx0 = win.x0 + bx0 * step, ry0 = win.y0 + by0 * step, rx1 = Math.min(win.x1, win.x0 + bx1 * step), ry1 = Math.min(win.y1, win.y0 + by1 * step);
        const sub = {
            x0: win.x0 + Math.floor((rx0 - win.x0) / T) * T, y0: win.y0 + Math.floor((ry0 - win.y0) / T) * T,
            x1: Math.min(win.x1, win.x0 + Math.ceil((rx1 - win.x0) / T) * T), y1: Math.min(win.y1, win.y0 + Math.ceil((ry1 - win.y0) / T) * T),
        };
        const sw = sub.x1 - sub.x0, sh = sub.y1 - sub.y0, n = lw * lh;
        const hmax = new Uint8Array(n), hmin = new Uint8Array(n), band = new Uint8Array(n);
        for (let y = 0; y < lh; y++) {
            const o = y * lw;
            for (let x = 0; x < lw; x++) {
                const a = Math.max(0, x - BR), b = Math.min(lw - 1, x + BR);
                let mx = 0, mn = 255;
                for (let q = a; q <= b; q++) { const v = low[o + q]; if (v > mx) mx = v; if (v < mn) mn = v; }
                hmax[o + x] = mx; hmin[o + x] = mn;
            }
        }
        for (let y = 0; y < lh; y++) {
            const a = Math.max(0, y - BR), b = Math.min(lh - 1, y + BR);
            for (let x = 0; x < lw; x++) {
                let mx = 0, mn = 255;
                for (let q = a; q <= b; q++) { const i = q * lw + x; if (hmax[i] > mx) mx = hmax[i]; if (hmin[i] < mn) mn = hmin[i]; }
                if (mx !== mn) band[y * lw + x] = 1;
            }
        }
        const mask = new Uint8Array(sw * sh), xi = new Int32Array(sw);
        for (let x = 0; x < sw; x++) xi[x] = Math.min(Math.floor((sub.x0 - win.x0 + x) / step), lw - 1);
        for (let y = 0; y < sh; y++) {
            const row = Math.min(Math.floor((sub.y0 - win.y0 + y) / step), lh - 1) * lw, mo = y * sw;
            for (let x = 0; x < sw; x++) mask[mo + x] = low[row + xi[x]] ? 255 : 0;
        }
        if (models && refine) refineBand(src, win, step, low, band, lw, lh, models[0], models[1], mask, sub);
        antialiasU8(mask, sw, sh);
        return trimRegion(sub, mask);
    }
    function finishRegion(src, win, step, low, lw, lh, models, refine, BR) {
        if (!tfxOff() && step > 1) return finishRegionFast(src, win, step, low, lw, lh, models, refine, BR);
        return finishRegionOld(src, win, step, low, lw, lh, models, refine, BR);
    }
    function finishRegionOld(src, win, step, low, lw, lh, models, refine, BR) {
        BR = BR || 2;   // W6: band 2 working px each side (PhotoCraft uses 1) so the full-res re-cut can move further to the real edge
        const w = win.x1 - win.x0, h = win.y1 - win.y0;
        const mask = new Uint8Array(w * h);
        if (step <= 1) {
            for (let i = 0; i < mask.length; i++) mask[i] = low[i] ? 255 : 0;
        } else {
            const band = new Uint8Array(lw * lh);
            for (let y = 0; y < lh; y++) {
                for (let x = 0; x < lw; x++) {
                    const v = low[y * lw + x];
                    let hit = false;
                    for (let dy = -BR; dy <= BR && !hit; dy++) {
                        const ny = y + dy; if (ny < 0 || ny >= lh) continue;
                        for (let dx = -BR; dx <= BR; dx++) {
                            const nx = x + dx;
                            if (nx >= 0 && nx < lw && low[ny * lw + nx] !== v) { hit = true; break; }
                        }
                    }
                    if (hit) band[y * lw + x] = 1;
                }
            }
            for (let y = 0; y < h; y++) {
                const ly = Math.min(Math.floor(y / step), lh - 1);
                for (let x = 0; x < w; x++) mask[y * w + x] = low[ly * lw + Math.min(Math.floor(x / step), lw - 1)] ? 255 : 0;
            }
            if (models && refine) refineBand(src, win, step, low, band, lw, lh, models[0], models[1], mask);
        }
        antialiasU8(mask, w, h);
        return trimRegion(win, mask);
    }

    // ------------------------------------------------------------ quick.rs
    function strokeMask(pts, radius, w, h) {
        const m = new Uint8Array(w * h);
        const segs = [];
        if (pts.length === 1) segs.push([pts[0], pts[0]]);
        else for (let i = 0; i + 1 < pts.length; i++) segs.push([pts[i], pts[i + 1]]);
        for (const s of segs) {
            const a = s[0], b = s[1];
            const x0 = Math.max(0, Math.floor(Math.min(a[0], b[0]) - radius));
            const y0 = Math.max(0, Math.floor(Math.min(a[1], b[1]) - radius));
            const x1 = Math.min(w, Math.max(0, Math.ceil(Math.max(a[0], b[0]) + radius)));
            const y1 = Math.min(h, Math.max(0, Math.ceil(Math.max(a[1], b[1]) + radius)));
            const dx = b[0] - a[0], dy = b[1] - a[1], len2 = dx * dx + dy * dy, r2 = radius * radius;
            for (let y = y0; y < y1; y++) {
                for (let x = x0; x < x1; x++) {
                    const px = x + 0.5, py = y + 0.5;
                    let t = len2 > 0 ? ((px - a[0]) * dx + (py - a[1]) * dy) / len2 : 0;
                    t = t < 0 ? 0 : (t > 1 ? 1 : t);
                    const qx = a[0] + t * dx - px, qy = a[1] + t * dy - py;
                    if (qx * qx + qy * qy <= r2) m[y * w + x] = 1;
                }
            }
        }
        for (const p of pts) {
            if (p[0] >= 0 && p[1] >= 0 && p[0] < w && p[1] < h) m[Math.floor(p[1]) * w + Math.floor(p[0])] = 1;
        }
        return m;
    }

    function blur3(img) {
        const w = img.w, h = img.h, p = img.px, tmp = new Float32Array(p.length), out = new Float32Array(p.length);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const l = (y * w + Math.max(0, x - 1)) * 3, r = (y * w + Math.min(w - 1, x + 1)) * 3, c = (y * w + x) * 3;
                tmp[c] = (p[l] + p[c] + p[r]) / 3; tmp[c + 1] = (p[l + 1] + p[c + 1] + p[r + 1]) / 3; tmp[c + 2] = (p[l + 2] + p[c + 2] + p[r + 2]) / 3;
            }
        }
        for (let y = 0; y < h; y++) {
            const yu = Math.max(0, y - 1), yd = Math.min(h - 1, y + 1);
            for (let x = 0; x < w; x++) {
                const u = (yu * w + x) * 3, d = (yd * w + x) * 3, c = (y * w + x) * 3;
                out[c] = (tmp[u] + tmp[c] + tmp[d]) / 3; out[c + 1] = (tmp[u + 1] + tmp[c + 1] + tmp[d + 1]) / 3; out[c + 2] = (tmp[u + 2] + tmp[c + 2] + tmp[d + 2]) / 3;
            }
        }
        return { w, h, px: out };
    }

    function geodesic(img, seeds) {
        const w = img.w, h = img.h, n = w * h;
        const sm = blur3(blur3(img)), sp = sm.px;
        const near = new Uint8Array(n);
        for (let i = 0; i < n; i++) {
            if (!seeds[i]) continue;
            const x = i % w, y = (i - x) / w;
            for (let yy = Math.max(0, y - 2); yy < Math.min(h, y + 3); yy++) {
                for (let xx = Math.max(0, x - 2); xx < Math.min(w, x + 3); xx++) near[yy * w + xx] = 1;
            }
        }
        const g = new Float32Array(n);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const l = (y * w + Math.max(0, x - 1)) * 3, r = (y * w + Math.min(w - 1, x + 1)) * 3;
                const u = (Math.max(0, y - 1) * w + x) * 3, d = (Math.min(h - 1, y + 1) * w + x) * 3;
                let a = 0, b = 0;
                for (let k = 0; k < 3; k++) { const t = sp[l + k] - sp[r + k], s = sp[u + k] - sp[d + k]; a += t * t; b += s * s; }
                g[y * w + x] = Math.sqrt((a + b) * 0.25);
            }
        }
        let cnt = 0;
        for (let i = 0; i < n; i++) if (near[i]) cnt++;
        let tau = 0;
        if (cnt) {
            const diffs = new Float32Array(cnt); let k = 0;
            for (let i = 0; i < n; i++) if (near[i]) diffs[k++] = g[i];
            diffs.sort();
            tau = diffs[Math.floor(cnt / 2)];
        }
        const thr = Math.max(2 * tau, MIN_STEP);
        const e = new Float32Array(n);
        for (let i = 0; i < n; i++) e[i] = Math.max(0, g[i] - thr);
        const d = new Float32Array(n);
        for (let i = 0; i < n; i++) d[i] = seeds[i] ? 0 : Infinity;
        const cost = function (a, b, len) { return len * (0.5 * (e[a] + e[b]) + 1e-6); };
        for (let it = 0; it < 2; it++) {
            for (let y = 0; y < h; y++) {
                for (let x = 0; x < w; x++) {
                    const i = y * w + x; let v = d[i];
                    if (x > 0) v = Math.min(v, d[i - 1] + cost(i, i - 1, 1));
                    if (y > 0) {
                        v = Math.min(v, d[i - w] + cost(i, i - w, 1));
                        if (x > 0) v = Math.min(v, d[i - w - 1] + cost(i, i - w - 1, SQ2));
                        if (x + 1 < w) v = Math.min(v, d[i - w + 1] + cost(i, i - w + 1, SQ2));
                    }
                    d[i] = v;
                }
            }
            for (let y = h - 1; y >= 0; y--) {
                for (let x = w - 1; x >= 0; x--) {
                    const i = y * w + x; let v = d[i];
                    if (x + 1 < w) v = Math.min(v, d[i + 1] + cost(i, i + 1, 1));
                    if (y + 1 < h) {
                        v = Math.min(v, d[i + w] + cost(i, i + w, 1));
                        if (x + 1 < w) v = Math.min(v, d[i + w + 1] + cost(i, i + w + 1, SQ2));
                        if (x > 0) v = Math.min(v, d[i + w - 1] + cost(i, i + w - 1, SQ2));
                    }
                    d[i] = v;
                }
            }
        }
        return d;
    }

    // PORT-W5B3: minimax-path colour step from the stroke seeds: d[i] = min over paths of the LARGEST single colour step on the path.
    // A soft gradient (a car side with a reflection) is a chain of tiny steps -> small d everywhere on the panel; a seam / paint edge is one
    // big step -> d jumps there and stays high behind it.  Returns { d, t0 } (t0 = noise-scaled threshold).
    // (A second-difference version was tried and rejected: it forgives any smooth-looking profile, and a path that slices diagonally through
    // a blurred rounded corner sees one, so it leaked out of a low-contrast rounded rect - tools_port/w6 test_quick.js "rounded rect, low contrast".)
    function bottleneck(img, seeds) {
        const w = img.w, h = img.h, n = w * h, p = blur3(img).px;
        const st = function (i, j) { return Math.sqrt(d2px(p, i * 3, j * 3)); };
        // noise level: median 4-neighbour step inside the seeded area
        const samp = [];
        for (let i = 0; i < n; i++) {
            if (!seeds[i]) continue;
            const x = i % w, y = (i - x) / w;
            if (x + 1 < w) samp.push(st(i, i + 1));
            if (y + 1 < h) samp.push(st(i, i + w));
        }
        samp.sort(function (a, b) { return a - b; });
        const med = samp.length ? samp[samp.length >> 1] : 0;
        // t0 = the colour step per working px that still counts as 'the same smooth surface'.  A gradient's step per working px grows with the
        // working scale (a body-side reflection peaks at ~0.0024 per canvas px) while a real edge's does not, so the floor follows the scale;
        // 1.5 * median seed step adds the local noise/slope.  (Measured on the owner's car: a soft-edged decal steps 0.006 per canvas px.)
        const t0 = Math.max(CONT_T0_FLOOR, CONT_T0_SLOPE * (img.step || 8), 1.5 * med);
        const d = new Float32Array(n);
        for (let i = 0; i < n; i++) d[i] = seeds[i] ? 0 : Infinity;
        const relax = function (i, j) { const v = Math.max(d[j], st(i, j)); if (v < d[i]) d[i] = v; };
        for (let it = 0; it < 3; it++) {
            for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
                const i = y * w + x;
                if (x > 0) relax(i, i - 1);
                if (y > 0) { relax(i, i - w); if (x > 0) relax(i, i - w - 1); if (x + 1 < w) relax(i, i - w + 1); }
            }
            for (let y = h - 1; y >= 0; y--) for (let x = w - 1; x >= 0; x--) {
                const i = y * w + x;
                if (x + 1 < w) relax(i, i + 1);
                if (y + 1 < h) { relax(i, i + w); if (x + 1 < w) relax(i, i + w + 1); if (x > 0) relax(i, i + w - 1); }
            }
        }
        return { d, t0 };
    }
    // Measured separation (working px, blur3 applied): the steepest legitimate gradient (a reflection band at the coarse live scale) peaks at
    // ~2.0 * t0 per step; the weakest edge that must stay sealed (36-level rounded rect) has a largest step of 3.3 * t0 (any edge of height H has
    // a largest step >= H/3 after the 3x3 blur).  So: fully connected up to CONT_LO * t0, sealed from CONT_UP * t0.
    function contCost(db, t0) {
        const lo = CONT_LO * t0, up = CONT_UP * t0;
        if (db <= lo) return CONT_BASE;
        if (db >= up) return CONT_HI;
        const t = (db - lo) / (up - lo);
        return CONT_BASE + (CONT_HI - CONT_BASE) * t * t;
    }

    function subsampleIdx(list, max) {
        if (list.length <= max) return list;
        const k = Math.ceil(list.length / max), out = [];
        for (let i = 0; i < list.length; i += k) out.push(list[i]);
        return out;
    }

    function gather(px, idxs) {
        const S = new Float32Array(idxs.length * 3);
        for (let i = 0; i < idxs.length; i++) { const o = idxs[i] * 3; S[i * 3] = px[o]; S[i * 3 + 1] = px[o + 1]; S[i * 3 + 2] = px[o + 2]; }
        return S;
    }

    // Working-resolution segmentation: { fg, bg, low (Uint8 labels) }.
    // PORT-W5B4: the continuity prior is only switched on when the ORIGINAL cut is demonstrably suspect.  Measured (tools_port/w5b/dbg_weak.js)
    // on 20 fixtures: when the cut sits on a real paint edge, 0 % of its boundary pixels have a colour step below 1.5 * t0 (12/12 flat-object
    // fixtures + the flat control; the weakest edge, a 36-level rounded rect, sits at 4.0 * t0); when it stops inside a soft gradient 24-48 %
    // of the boundary is that weak (7/7 gradient fixtures).  So flat objects keep the old, proven behaviour bit for bit.
    const WEAK_STEP = 1.5, WEAK_FRAC = 0.08;
    function weakBoundary(img, low, seeds) {
        const w = img.w, h = img.h, n = w * h, p = blur3(img).px;
        const st = function (i, j) { return Math.sqrt(d2px(p, i * 3, j * 3)); };
        const samp = [];
        for (let i = 0; i < n; i++) {
            if (!seeds[i]) continue;
            const x = i % w, y = (i - x) / w;
            if (x + 1 < w) samp.push(st(i, i + 1));
            if (y + 1 < h) samp.push(st(i, i + w));
        }
        samp.sort(function (a, b) { return a - b; });
        const t0 = Math.max(CONT_T0_MIN, 3 * (samp.length ? samp[samp.length >> 1] : 0));
        let nb = 0, weak = 0;
        const nbr = [-1, 1, -w, w, -w - 1, -w + 1, w - 1, w + 1];
        for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
            const i = y * w + x;
            if (!low[i] || (low[i - 1] && low[i + 1] && low[i - w] && low[i + w])) continue;
            nb++;
            let m = 0;
            for (let k = 0; k < 8; k++) { const v = st(i, i + nbr[k]); if (v > m) m = v; }
            if (m < WEAK_STEP * t0) weak++;
        }
        return nb >= 40 ? weak / nb : 0;
    }
    function segment(img, seeds) {
        const r1 = segmentCore(img, seeds, null);
        if (w5bOff()) return r1;
        if (weakBoundary(img, r1.low, seeds) < WEAK_FRAC) return r1;
        return segmentCore(img, seeds, bottleneck(img, seeds));   // PORT-W5B continuity prior
    }
    function segmentCore(img, seeds, bn) {
        const w = img.w, h = img.h, n = w * h, px = img.px;
        const geo = geodesic(img, seeds);
        const fIdx = [], bIdx = [];
        for (let i = 0; i < n; i++) { if (seeds[i]) fIdx.push(i); if (geo[i] > EDGE && (!bn || bn.d[i] > CONT_LO * bn.t0)) bIdx.push(i); }   // PORT-W5B: pixels smoothly connected to the stroke are never background samples (a gradient's far end would train the BG model)
        const fs = subsampleIdx(fIdx, 20000), bs = subsampleIdx(bIdx, 20000);
        const fg = gmmFit(gather(px, fs), fs.length, Math.max(1, Math.min(4, Math.floor(fs.length / 40))), QREG) || broadModel();
        const bgm = bs.length >= 30 ? gmmFit(gather(px, bs), bs.length, 6, QREG) : null;
        const cf = new Float32Array(n), cb = new Float32Array(n);
        for (let i = 0; i < n; i++) {
            const o = i * 3, p0 = px[o], p1 = px[o + 1], p2 = px[o + 2];
            let gf = gmmNegLog(fg, p0, p1, p2);
            if (bn) gf = contCost(bn.d[i], bn.t0);   // PORT-W5B: in the gradient pass membership = smooth connection to the stroke (the stroke-only GMM is exactly what fails on a gradient, and a broad refit would swallow decals of similar luminance)
            cf[i] = gf + KAPPA * Math.min(geo[i] / EDGE, 4);
            cb[i] = bgm ? -Math.log(0.85 * Math.exp(gmmLogProb(bgm, p0, p1, p2)) + 0.15) : 0;
        }
        const fixed = new Uint8Array(n);
        for (let i = 0; i < n; i++) fixed[i] = seeds[i] ? HARD_FG : FREE;
        let contSet = null;   // PORT-W5B: pixels whose smoothest path from the stroke never crosses a real colour step
        if (bn) { contSet = new Uint8Array(n); const lim = CONT_LO * bn.t0; for (let i = 0; i < n; i++) if (bn.d[i] <= lim) contSet[i] = 1; }
        const cut = gridCut(img, cf, cb, fixed, GAMMA, contrastBeta(img), contSet);
        const low = keepSeeded(cut, seeds, w, h);
        let fgOut = fg;
        if (bn) { // PORT-W5B: the full-res band re-cut must judge boundary pixels with a model of everything selected, not just the stroke colours
            const sel = [];
            for (let i = 0; i < n; i++) if (low[i]) sel.push(i);
            if (sel.length > fIdx.length * 1.5) {
                const ss = subsampleIdx(sel, 20000);
                const m2 = gmmFit(gather(px, ss), ss.length, Math.max(1, Math.min(6, Math.floor(ss.length / 60))), QREG);
                if (m2) fgOut = m2;
            }
        }
        return { fg: fgOut, bg: bgm || broadModel(), low };
    }

    // src: {data: RGBA bytes, w, h}; points: [[x,y]...] in image pixels; size: brush diameter.
    // opts: { workPx, refine }. Returns { bbox:{x0,y0,x1,y1}, mask:Uint8Array(bw*bh) } or null.
    function quickSelect(src, points, size, opts) {
        opts = opts || {};
        if (!points || !points.length) return null;
        size = Math.max(1, size || 1);
        const r = size / 2;
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        for (const p of points) { x0 = Math.min(x0, p[0] - r); y0 = Math.min(y0, p[1] - r); x1 = Math.max(x1, p[0] + r); y1 = Math.max(y1, p[1] + r); }
        const bb = { x0: Math.max(0, Math.floor(x0)), y0: Math.max(0, Math.floor(y0)), x1: Math.min(src.w, Math.ceil(x1) + 1), y1: Math.min(src.h, Math.ceil(y1) + 1) };
        if (bb.x1 <= bb.x0 || bb.y1 <= bb.y0) return null;
        let margin = Math.floor(Math.max(size * 6, 512));
        const fastQ = !tfxOff();
        if (fastQ && opts.marginHint > margin) margin = Math.floor(opts.marginHint);   // [SPB-TFX1 2026-10-09 TA-015] start from the margin an earlier pass of this stroke needed
        for (let grow = 0; ; grow++) {
            const win = { x0: Math.max(0, bb.x0 - margin), y0: Math.max(0, bb.y0 - margin), x1: Math.min(src.w, bb.x1 + margin), y1: Math.min(src.h, bb.y1 + margin) };
            const step = scaleFor(win.x1 - win.x0, win.y1 - win.y0, opts.workPx || WORK_PX);
            const img = rgbScaled(src, win, step, (fastQ && step >= 8) ? Math.floor(step / 4) : 1);
            const lw = img.w, lh = img.h, st = step;
            const pts = points.map(function (p) { return [(p[0] - win.x0) / st, (p[1] - win.y0) / st]; });
            const seeds = strokeMask(pts, Math.max(r / st, 0.75), lw, lh);
            let any = false; for (let i = 0; i < seeds.length; i++) if (seeds[i]) { any = true; break; }
            if (!any) return null;
            const seg = segment(img, seeds);
            let low = false; for (let i = 0; i < seg.low.length; i++) if (seg.low[i]) { low = true; break; }
            if (!low) return null;
            // PORT-W5B: the selection still touches a window side that is not the canvas edge -> the panel continues beyond the window: grow it
            if (grow < (opts.refine === false ? MAX_GROW_LIVE : MAX_GROW) && !w5bOff()) {
                let touch = false;
                const L = win.x0 > 0, R = win.x1 < src.w, T = win.y0 > 0, B = win.y1 < src.h;
                if (L) for (let y = 0; y < lh && !touch; y++) if (seg.low[y * lw]) touch = true;
                if (R) for (let y = 0; y < lh && !touch; y++) if (seg.low[y * lw + lw - 1]) touch = true;
                if (T) for (let x = 0; x < lw && !touch; x++) if (seg.low[x]) touch = true;
                if (B) for (let x = 0; x < lw && !touch; x++) if (seg.low[(lh - 1) * lw + x]) touch = true;
                if (touch) { margin *= 2; continue; }
            }
            if (fastQ && opts.live) return { live: true, win, lw, lh, step, low: seg.low, fg: seg.fg, bg: seg.bg, margin, passes: grow + 1 };
            const reg = finishRegion(src, win, step, seg.low, lw, lh, [seg.fg, seg.bg], opts.refine !== false, opts.bandR);
            if (reg) { reg.margin = margin; reg.passes = grow + 1; }
            return reg;
        }
    }

    // ------------------------------------------------------------ UI controller
    const ctl = { host: null, stroke: null, preview: null, timer: 0, busy: false, lastMs: 0, lastLiveMs: 0, ringPos: null, worker: null, workerBad: false, inFlight: false, seq: 0, reqN: 0 };

    function flagOff() { return !!(G && G.SPB_PC_W6_OFF); }
    function readOpts() {
        const doc = G.document;
        const on = !!(doc && doc.getElementById('spbQuickOn') && doc.getElementById('spbQuickOn').checked);
        const size = Math.max(2, Math.min(600, parseInt(doc && doc.getElementById('spbQuickSize') && doc.getElementById('spbQuickSize').value, 10) || 40));
        const enhEl = doc && doc.getElementById('spbQuickEnhance');
        const enh = !!(enhEl && enhEl.checked);
        return { on, size, enhance: enh };
    }

    function previewCanvas() {
        const doc = G.document, host = doc.getElementById('canvasInner'), paint = doc.getElementById('paintCanvas');
        if (!host || !paint) return null;
        let cv = ctl.preview;
        if (cv && cv.parentNode === host && cv.width === paint.width && cv.height === paint.height) return cv;
        if (cv && cv.parentNode) cv.parentNode.removeChild(cv);
        cv = doc.createElement('canvas');
        cv.id = 'spbQuickPreview';
        cv.width = paint.width; cv.height = paint.height;
        cv.style.cssText = 'position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; z-index:6;';
        host.appendChild(cv);
        ctl.preview = cv; ctl._drawn = null;
        return cv;
    }
    function clearPreview() {
        const cv = ctl.preview; if (!cv) return;
        cv.getContext('2d').clearRect(0, 0, cv.width, cv.height);
        ctl._drawn = null;
    }
    function drawRing(pos, size) {
        const cv = previewCanvas(); if (!cv) return;
        const ctx = cv.getContext('2d');
        if (ctl._ring) ctx.clearRect(ctl._ring.x, ctl._ring.y, ctl._ring.w, ctl._ring.h);
        const r = size / 2, pad = 4;
        ctl._ring = { x: Math.floor(pos.x - r - pad), y: Math.floor(pos.y - r - pad), w: Math.ceil(size + 2 * pad), h: Math.ceil(size + 2 * pad) };
        ctx.save();
        ctx.lineWidth = Math.max(1, cv.width / 1100);
        ctx.strokeStyle = 'rgba(255,255,255,0.95)';
        ctx.beginPath(); ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = 'rgba(0,0,0,0.6)';
        ctx.beginPath(); ctx.arc(pos.x, pos.y, r + ctx.lineWidth, 0, Math.PI * 2); ctx.stroke();
        ctx.restore();
    }
    // [SPB-TFX1 2026-10-09 TA-015] low-res live preview: the working-res label map is painted into a tiny canvas and drawn scaled over its window
    // (no full-res mask, no putImageData of a ~2000x2000 window per step).
    function drawLow(region, mode) {
        const cv = previewCanvas(); if (!cv) return;
        const ctx = cv.getContext('2d');
        if (ctl._drawn) { const d = ctl._drawn; ctx.clearRect(d.x0 - 2, d.y0 - 2, d.x1 - d.x0 + 4, d.y1 - d.y0 + 4); }
        const lw = region.lw, lh = region.lh, win = region.win, doc = G.document;
        let off = ctl._off;
        if (!off || off.width !== lw || off.height !== lh) { off = ctl._off = doc.createElement('canvas'); off.width = lw; off.height = lh; ctl._offCtx = off.getContext('2d'); }
        const id = ctl._offCtx.createImageData(lw, lh), o = id.data, m = region.low;
        const col = mode === 'subtract' ? [255, 70, 70] : [60, 170, 255];
        for (let i = 0; i < m.length; i++) {
            if (!m[i]) continue;
            o[i * 4] = col[0]; o[i * 4 + 1] = col[1]; o[i * 4 + 2] = col[2]; o[i * 4 + 3] = 115;
        }
        ctl._offCtx.putImageData(id, 0, 0);
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(off, 0, 0, lw, lh, win.x0, win.y0, win.x1 - win.x0, win.y1 - win.y0);
        ctl._drawn = { x0: win.x0, y0: win.y0, x1: win.x1, y1: win.y1 };
    }
    function drawRegion(region, mode) {
        if (region && region.live) return drawLow(region, mode);
        const cv = previewCanvas(); if (!cv) return;
        const ctx = cv.getContext('2d');
        if (ctl._drawn) { const d = ctl._drawn; ctx.clearRect(d.x0 - 2, d.y0 - 2, d.x1 - d.x0 + 4, d.y1 - d.y0 + 4); }
        if (!region) { ctl._drawn = null; return; }
        const b = region.bbox, w = b.x1 - b.x0, h = b.y1 - b.y0;
        const id = ctx.createImageData(w, h), o = id.data, m = region.mask;
        const col = mode === 'subtract' ? [255, 70, 70] : [60, 170, 255];
        for (let i = 0; i < m.length; i++) {
            if (!m[i]) continue;
            o[i * 4] = col[0]; o[i * 4 + 1] = col[1]; o[i * 4 + 2] = col[2]; o[i * 4 + 3] = Math.round(m[i] * 0.45);
        }
        ctx.putImageData(id, b.x0, b.y0);
        ctl._drawn = b;
    }

    function setHost(h) { ctl.host = h; }

    function compute(final) {
        const s = ctl.stroke; if (!s) return null;
        const img = ctl.host.getImage(!s.fetched);
        s.fetched = true;
        if (!img) return null;
        const t0 = (G.performance || Date).now();
        const fast = !tfxOff();
        let region;
        const lv = s.live;
        if (fast && final && lv && liveCovers(s, lv)) {   // [SPB-TFX1 2026-10-09 TA-015] the worker's last cut already covers the whole stroke: only the full-res band re-cut is left
            region = finishRegion(img, lv.win, lv.step, lv.low, lv.lw, lv.lh, [lv.fg, lv.bg], true);
            if (region) { region.margin = lv.margin; s.cached = true; }
        } else if (fast) {
            region = quickSelect(img, s.points, s.size, { workPx: final ? WORK_FINAL : WORK_LIVE, refine: final, marginHint: s.margin });
        } else {
            region = quickSelect(img, s.points, s.size, { workPx: final ? WORK_PX : WORK_LIVE, refine: final });
        }
        if (region && fast && region.margin) s.margin = region.margin;
        if (region && s.enhance && G.SPBPcSelection && G.SPBPcSelection.smooth) {
            // Auto-enhance: round jagged / blocky boundary (PhotoCraft selection smooth on the region window).
            const w = region.bbox.x1 - region.bbox.x0, h = region.bbox.y1 - region.bbox.y0;
            try {
                const sm = G.SPBPcSelection.smooth(region.mask, w, h, final ? 2 : 1);
                if (sm && sm.length === region.mask.length) region = { bbox: region.bbox, mask: sm };
            } catch (e) { /* keep unsmoothed */ }
        }
        const ms = ((G.performance || Date).now()) - t0;
        if (final) ctl.lastMs = ms; else ctl.lastLiveMs = ms;
        return region;
    }

    // the live cut is reusable when every stroke point added after it was requested already lies inside the selected area (the stroke only
    // wandered over what is selected anyway), so the colour model and the cut would not change
    function liveCovers(s, lv) {
        if (s.liveN === s.points.length) return true;
        if (!(s.liveN > 0) || s.liveN > s.points.length) return false;
        const win = lv.win;
        for (let i = s.liveN; i < s.points.length; i++) {
            const p = s.points[i];
            const lx = Math.floor((p[0] - win.x0) / lv.step), ly = Math.floor((p[1] - win.y0) / lv.step);
            if (lx < 0 || ly < 0 || lx >= lv.lw || ly >= lv.lh || !lv.low[ly * lv.lw + lx]) return false;
        }
        return true;
    }

    // ---- [SPB-TFX1 2026-10-09 TA-015] live steps in a Web Worker (this same file is the worker script; see workerMain at the bottom)
    function ensureWorker() {
        if (tfxOff() || ctl.workerBad) return null;
        if (ctl.worker) return ctl.worker;
        try {
            if (!SELF_SRC || typeof G.Worker !== 'function') throw new Error('no worker');
            const w = new G.Worker(SELF_SRC);
            w.onmessage = onWorkerMsg;
            w.onerror = function () { ctl.workerBad = true; ctl.worker = null; ctl.inFlight = false; if (ctl.stroke) { ctl.stroke.imgSent = false; schedule(); } };
            ctl.worker = w;
            return w;
        } catch (e) { ctl.workerBad = true; ctl.worker = null; return null; }
    }
    function dropWorker(keep) {   // stroke over: free the worker's image copy, or kill it if a cut is still running
        const w = ctl.worker; if (!w) return;
        if (ctl.inFlight) { try { w.terminate(); } catch (e) { } ctl.worker = null; ctl.inFlight = false; }
        else if (keep !== true) { try { w.postMessage({ t: 'free' }); } catch (e) { } }
    }
    function requestLive() {
        const s = ctl.stroke, w = ctl.worker; if (!s || !w) return;
        if (ctl.inFlight) { s.dirty = true; return; }
        if (!s.imgSent) {
            const img = ctl.host.getImage(!s.fetched);
            s.fetched = true;
            if (!img) return;
            w.postMessage({ t: 'img', data: img.data, w: img.w, h: img.h });
            s.imgSent = true;
        }
        ctl.inFlight = true; ctl.reqN = s.points.length;
        w.postMessage({ t: 'live', seq: ++ctl.seq, points: s.points.slice(), size: s.size, workPx: WORK_LIVE, marginHint: s.margin || 0 });
    }
    function onWorkerMsg(e) {
        const m = e.data; if (!m || m.t !== 'live') return;
        if (m.seq !== ctl.seq) return;
        ctl.inFlight = false;
        const s = ctl.stroke; if (!s) return;
        if (m.err) { ctl.workerBad = true; try { ctl.worker.terminate(); } catch (er) { } ctl.worker = null; s.imgSent = false; schedule(); return; }
        ctl.lastWorkerMs = m.ms;
        if (m.res) { s.live = m.res; s.liveN = ctl.reqN; s.margin = m.res.margin; s.region = m.res; drawRegion(m.res, s.mode); }
        if (s.dirty) { s.dirty = false; requestLive(); }
    }

    function liveUpdate() {
        ctl.timer = 0;
        const s = ctl.stroke; if (!s) return;
        if (ensureWorker()) { requestLive(); return; }
        if (ctl.busy) return;
        ctl.busy = true;
        try {
            s.region = compute(false);
            drawRegion(s.region, s.mode);
        } finally { ctl.busy = false; }
        if (s.dirty) { s.dirty = false; schedule(); }
    }
    function schedule() {
        if (ctl.timer || !ctl.stroke) return;
        ctl.timer = G.setTimeout(liveUpdate, 0);
    }

    function enabled() {
        if (flagOff() || !ctl.host) return false;
        return readOpts().on;
    }
    function active() { return !!ctl.stroke; }

    function down(pos, ev) {
        const o = readOpts();
        ctl.stroke = {
            points: [[pos.x, pos.y]], size: o.size, enhance: o.enhance,
            mode: ctl.host.resolveMode(ev), fetched: false, region: null, dirty: false,
        };
        drawRing(pos, o.size);
        liveUpdate();
    }
    function move(pos) {
        const s = ctl.stroke;
        if (!s) { hover(pos); return; }
        const last = s.points[s.points.length - 1];
        if (Math.hypot(pos.x - last[0], pos.y - last[1]) < Math.max(1.5, s.size / 12)) return;
        s.points.push([pos.x, pos.y]);
        s.dirty = true;
        schedule();
    }
    function hover(pos) {
        if (flagOff() || !ctl.host || !readOpts().on) return;
        ctl.ringPos = pos;
        drawRing(pos, readOpts().size);
    }
    function up(ev) {
        const s = ctl.stroke; if (!s) return false;
        if (ctl.timer) { G.clearTimeout(ctl.timer); ctl.timer = 0; }
        ctl.stroke = null;
        let region = null;
        s.fetched = true;
        ctl.stroke = s;
        try { region = compute(true); } finally { ctl.stroke = null; }
        ctl.lastCached = !!s.cached;
        dropWorker();
        clearPreview();
        if (!region) { ctl.host.toast('Quick Select: nothing found - paint inside the area you want'); return false; }
        return ctl.host.commit(region, s.mode, ev);
    }
    function cancel() {
        const had = !!ctl.stroke;
        if (ctl.timer) { G.clearTimeout(ctl.timer); ctl.timer = 0; }
        ctl.stroke = null;
        dropWorker();
        if (ctl.preview) clearPreview();
        return had;
    }
    function leave() { if (!ctl.stroke && ctl.preview) clearPreview(); }

    // Keyboard (capture phase, only while the Wand is active with Quick ticked): [ ] change the
    // brush size, Esc cancels the stroke in progress. Never fires while typing in a field.
    if (G && G.document && G.document.addEventListener && !G.__spbPcQuickKeys) {
        G.__spbPcQuickKeys = true;
        G.document.addEventListener('keydown', function (e) {
            if (flagOff() || !ctl.host || G.canvasMode !== 'wand') return;
            const t = e.target, tag = t && t.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return;
            if (e.ctrlKey || e.metaKey || e.altKey) return;
            if (e.key === 'Escape' && ctl.stroke) { cancel(); e.preventDefault(); e.stopImmediatePropagation(); return; }
            if ((e.key === '[' || e.key === ']') && readOpts().on) {
                const el = G.document.getElementById('spbQuickSize');
                const cur = readOpts().size, step = Math.max(2, Math.round(cur * 0.15));
                const nv = Math.max(2, Math.min(600, cur + (e.key === ']' ? step : -step)));
                if (el) { el.value = nv; try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch (er) { } }
                if (ctl.ringPos) drawRing(ctl.ringPos, nv);
                if (ctl.stroke) ctl.stroke.size = nv;
                e.preventDefault(); e.stopImmediatePropagation();
            }
        }, true);
    }

    // [SPB-TFX1 2026-10-09 TA-015] worker side: this file doubles as the Web Worker script (the UMD wrapper sets SPBPcQuick on the worker global, the DOM bits are guarded).
    function workerMain() {
        let SRC = null;
        G.onmessage = function (e) {
            const m = e.data;
            if (!m) return;
            if (m.t === 'img') { SRC = { data: m.data, w: m.w, h: m.h }; return; }
            if (m.t === 'free') { SRC = null; return; }
            if (m.t === 'live') {
                let res = null, err = null;
                const t0 = G.performance.now();
                try { if (SRC) res = quickSelect(SRC, m.points, m.size, { workPx: m.workPx, refine: false, live: true, marginHint: m.marginHint }); } catch (ex) { err = String((ex && ex.message) || ex); }
                G.postMessage({ t: 'live', seq: m.seq, res: res, err: err, ms: G.performance.now() - t0 }, res ? [res.low.buffer] : []);
            }
        };
    }
    if (typeof G.importScripts === 'function' && !G.document) workerMain();

    return {
        version: 'w6-2026-10-09',
        quickSelect, segment, geodesic, bottleneck, gmmFit, gridCut, Graph, rgbScaled, scaleFor, strokeMask, finishRegion,
        WORK_PX, WORK_LIVE, WORK_FINAL,
        setPrior(v) { PRIOR = v; },
        setHost, enabled, active, down, move, up, cancel, hover, leave, readOpts,
        _ctl: ctl,
    };
});
