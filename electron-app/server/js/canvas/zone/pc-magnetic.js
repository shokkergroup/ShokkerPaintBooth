/* ============================================================================
 * SPB PC MAGNETIC LASSO  (lane PORT-W4, 2026-10-09)
 *
 * Algorithm ported from PhotoCraft crates/algo/src/magnetic.rs (edge field,
 * live-wire path search, snap, simplify) and the pointer/anchor logic of
 * crates/ui-egui/src/magnetic_lasso_ui.rs (fastening points, Frequency
 * spacing, closing, remove-last).
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0
 * (MIT elected) - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript. Pixels come from SPB's paint buffer
 * (paintImageData RGBA); the edge field (Sobel on premultiplied channels,
 * non-maximum suppression, sub-pixel offset) is computed lazily per 128 px
 * tile and kept in typed arrays; the live-wire search runs in a window around
 * the pointer path with a binary heap (no per-pixel closures in hot loops).
 * Cites (as PhotoCraft does): Mortensen & Barrett, "Intelligent Scissors for
 * Image Composition" (SIGGRAPH 1995); Ramer-Douglas-Peucker simplification.
 *
 * Owner verdict 2026-10-09: "our tools basically SUCK". SPB's Lasso had no
 * edge awareness at all (freehand / polygon only). This adds Photoshop's
 * Magnetic Lasso as an OPTION of the existing Lasso tool (Width / Contrast /
 * Frequency), no new toolbar button.
 *
 * Disable with  window.SPB_PC_W4_OFF = true  (the Magnetic option disappears
 * from use and the Lasso behaves exactly as before).
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcMagnetic = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const BLOCK = 128;
    const PIECE = 256;
    const MAX_GUIDE_LENGTH = 262144;
    const W_CENTRE = 0.43, W_STRENGTH = 0.43, W_DIRECTION = 0.14, W_LENGTH = 0.02, W_GUIDE = 0.4;
    const NEUTRAL_DIRECTION = 2 / 3;
    const SQRT2 = Math.SQRT2;
    const DX = [1, 1, 0, -1, -1, -1, 0, 1];
    const DY = [0, 1, 1, 1, 0, -1, -1, -1];

    const DEFAULTS = { width: 10, contrast: 10, frequency: 57 };

    function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

    // Detection settings: width px 1..256, contrast 0.01..1 (UI percent / 100).
    function makeSettings(width, contrast) {
        const w = Number.isFinite(width) ? clamp(width, 1, 256) : DEFAULTS.width;
        const c = Number.isFinite(contrast) ? clamp(contrast, 0.01, 1) : DEFAULTS.contrast / 100;
        return { width: w, contrast: c };
    }

    // ------------------------------------------------------------ geometry
    function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1]); }

    function dist2Segment(px, py, a, b) {
        const vx = b[0] - a[0], vy = b[1] - a[1];
        const l2 = vx * vx + vy * vy;
        const t = l2 > 0 ? clamp(((px - a[0]) * vx + (py - a[1]) * vy) / l2, 0, 1) : 0;
        const dx = px - (a[0] + t * vx), dy = py - (a[1] + t * vy);
        return dx * dx + dy * dy;
    }

    function length(p) {
        let s = 0;
        for (let i = 1; i < p.length; i++) s += dist(p[i - 1], p[i]);
        return s;
    }

    // Ramer-Douglas-Peucker: drops points within tol of the line through their neighbours.
    function simplify(p, tol) {
        const n = p.length;
        if (n < 3) return p.slice();
        const keep = new Uint8Array(n);
        keep[0] = 1; keep[n - 1] = 1;
        const tol2 = tol * tol;
        const stack = [[0, n - 1]];
        while (stack.length) {
            const ab = stack.pop();
            const a = ab[0], b = ab[1];
            if (b <= a + 1) continue;
            let farD = 0, farK = a;
            for (let k = a + 1; k < b; k++) {
                const d2 = dist2Segment(p[k][0], p[k][1], p[a], p[b]);
                if (d2 > farD) { farD = d2; farK = k; }
            }
            if (farD > tol2) { keep[farK] = 1; stack.push([a, farK], [farK, b]); }
        }
        const out = [];
        for (let i = 0; i < n; i++) if (keep[i]) out.push(p[i]);
        return out;
    }

    // The polyline g cut into pieces at most `piece` long; each starts where the last ended.
    function split(g, piece) {
        if (!g.length) return [];
        const out = [];
        let cur = [g[0]];
        let acc = 0;
        for (let i = 0; i + 1 < g.length; i++) {
            let a = g[i];
            const b = g[i + 1];
            let seg = dist(a, b);
            while (acc + seg > piece && seg > 0) {
                const t = clamp((piece - acc) / seg, 0, 1);
                const m = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
                cur.push(m);
                out.push(cur);
                cur = [m];
                a = m;
                seg = dist(a, b);
                acc = 0;
            }
            cur.push(b);
            acc += seg;
        }
        out.push(cur);
        return out;
    }

    // ----------------------------------------------------------- binary heap
    let hk = new Float32Array(4096), hv = new Int32Array(4096), hn = 0;
    function heapPush(k, v) {
        if (hn === hk.length) {
            const nk = new Float32Array(hn * 2); nk.set(hk); hk = nk;
            const nv = new Int32Array(hn * 2); nv.set(hv); hv = nv;
        }
        let i = hn++;
        while (i > 0) {
            const p = (i - 1) >> 1;
            if (hk[p] <= k) break;
            hk[i] = hk[p]; hv[i] = hv[p]; i = p;
        }
        hk[i] = k; hv[i] = v;
    }
    let popK = 0, popV = 0;
    function heapPop() {
        popK = hk[0]; popV = hv[0];
        hn--;
        if (hn > 0) {
            const k = hk[hn], v = hv[hn];
            let i = 0;
            for (;;) {
                let c = 2 * i + 1;
                if (c >= hn) break;
                if (c + 1 < hn && hk[c + 1] < hk[c]) c++;
                if (hk[c] >= k) break;
                hk[i] = hk[c]; hv[i] = hv[c]; i = c;
            }
            hk[i] = k; hv[i] = v;
        }
    }

    // ---------------------------------------------------------------- tracer
    // rgba: Uint8ClampedArray/Uint8Array straight RGBA, w*h*4.
    function createTracer(rgba, w, h) {
        const N = w * h;
        const strength = new Float32Array(N);   // steepest-channel Sobel / 4, capped at 1
        const gdx = new Int8Array(N);           // unit gradient * 127
        const gdy = new Int8Array(N);
        const ridge = new Uint8Array(N);        // strongest across its edge
        const offx = new Int8Array(N);          // sub-pixel offset to the edge centre * 254
        const offy = new Int8Array(N);
        const tilesX = Math.ceil(w / BLOCK), tilesY = Math.ceil(h / BLOCK);
        const tileDone = new Uint8Array(tilesX * tilesY);

        function computeTile(tx, ty) {
            const ax0 = tx * BLOCK, ay0 = ty * BLOCK;
            const ax1 = Math.min(w, ax0 + BLOCK), ay1 = Math.min(h, ay0 + BLOCK);
            // g1 = area inflated by 1 inside the image (gradients), pixel patch = g1 inflated by 1 (clamped).
            const gx0 = Math.max(0, ax0 - 1), gy0 = Math.max(0, ay0 - 1);
            const gx1 = Math.min(w, ax1 + 1), gy1 = Math.min(h, ay1 + 1);
            const gw = gx1 - gx0, gh = gy1 - gy0;
            const pw = gw + 2, ph = gh + 2;
            // premultiplied channels of the patch (clamped to the image like Rust's `at`)
            const pr = new Float32Array(pw * ph), pg = new Float32Array(pw * ph),
                pb = new Float32Array(pw * ph), pa = new Float32Array(pw * ph);
            for (let y = 0; y < ph; y++) {
                const sy = clamp(gy0 - 1 + y, 0, h - 1);
                for (let x = 0; x < pw; x++) {
                    const sx = clamp(gx0 - 1 + x, 0, w - 1);
                    const o = (sy * w + sx) * 4;
                    const a = rgba[o + 3] / 255;
                    const j = y * pw + x;
                    const k = a / 255;
                    pr[j] = rgba[o] * k; pg[j] = rgba[o + 1] * k; pb[j] = rgba[o + 2] * k; pa[j] = a;
                }
            }
            const S = new Float32Array(gw * gh), GX = new Float32Array(gw * gh), GY = new Float32Array(gw * gh);
            const chans = [pr, pg, pb, pa];
            for (let y = 0; y < gh; y++) {
                for (let x = 0; x < gw; x++) {
                    // patch coords of the centre pixel: (x+1, y+1)
                    const c = (y + 1) * pw + (x + 1);
                    const nw = c - pw - 1, n = c - pw, ne = c - pw + 1, we = c - 1, e = c + 1,
                        sw = c + pw - 1, so = c + pw, se = c + pw + 1;
                    let bestM2 = 0, bgx = 0, bgy = 0;
                    for (let ch = 0; ch < 4; ch++) {
                        const q = chans[ch];
                        const sx = (q[ne] + 2 * q[e] + q[se]) - (q[nw] + 2 * q[we] + q[sw]);
                        const sy = (q[sw] + 2 * q[so] + q[se]) - (q[nw] + 2 * q[n] + q[ne]);
                        const m2 = sx * sx + sy * sy;
                        if (m2 > bestM2) { bestM2 = m2; bgx = sx; bgy = sy; }
                    }
                    const mag = Math.sqrt(bestM2);
                    const i = y * gw + x;
                    S[i] = Math.min(mag / 4, 1);
                    if (mag > 1e-6) { GX[i] = bgx / mag; GY[i] = bgy / mag; }
                }
            }
            const sAt = function (x, y) {
                if (x < gx0 || y < gy0 || x >= gx1 || y >= gy1) return 0;
                return S[(y - gy0) * gw + (x - gx0)];
            };
            for (let y = ay0; y < ay1; y++) {
                for (let x = ax0; x < ax1; x++) {
                    const li = (y - gy0) * gw + (x - gx0);
                    const s0 = S[li];
                    const gi = y * w + x;
                    strength[gi] = s0;
                    const g0 = GX[li], g1v = GY[li];
                    gdx[gi] = Math.round(g0 * 127);
                    gdy[gi] = Math.round(g1v * 127);
                    if (g0 === 0 && g1v === 0) continue;
                    const dx = Math.abs(g0) >= 0.4142 * Math.abs(g1v) ? (g0 < 0 ? -1 : 1) : 0;
                    const dy = Math.abs(g1v) >= 0.4142 * Math.abs(g0) ? (g1v < 0 ? -1 : 1) : 0;
                    const sm = sAt(x - dx, y - dy), sp = sAt(x + dx, y + dy);
                    if (s0 > 0 && s0 >= sm && s0 >= sp) {
                        ridge[gi] = 1;
                        const denom = sm - 2 * s0 + sp;
                        const t = denom < -1e-6 ? clamp(0.5 * (sm - sp) / denom, -0.5, 0.5) : 0;
                        offx[gi] = Math.round(t * dx * 254);
                        offy[gi] = Math.round(t * dy * 254);
                    }
                }
            }
        }

        function ensure(x0, y0, x1, y1) {
            const bx0 = Math.floor(Math.max(0, x0) / BLOCK), by0 = Math.floor(Math.max(0, y0) / BLOCK);
            const bx1 = Math.floor((Math.min(w, x1) - 1) / BLOCK), by1 = Math.floor((Math.min(h, y1) - 1) / BLOCK);
            for (let by = by0; by <= by1; by++) {
                for (let bx = bx0; bx <= bx1; bx++) {
                    const ti = by * tilesX + bx;
                    if (!tileDone[ti]) { computeTile(bx, by); tileDone[ti] = 1; }
                }
            }
        }

        function clampPoint(p) {
            if (!w || !h || !Number.isFinite(p[0]) || !Number.isFinite(p[1])) return null;
            return [clamp(p[0], 0, w), clamp(p[1], 0, h)];
        }
        function pixelOf(p) {
            const f = function (v, hi) { return Number.isFinite(v) ? clamp(Math.floor(v), 0, Math.max(0, hi - 1)) : 0; };
            return [f(p[0], w), f(p[1], h)];
        }
        function pointAtIndex(gi, x, y, contrast) {
            const onEdge = ridge[gi] === 1 && strength[gi] >= contrast;
            const ox = onEdge ? offx[gi] / 254 : 0, oy = onEdge ? offy[gi] / 254 : 0;
            return [x + 0.5 + ox, y + 0.5 + oy];
        }

        // Where a fastening point near p goes: the centre of the most prominent edge within the
        // detection width, or p itself when no edge there reaches the contrast.
        function snap(pIn, sIn) {
            const s = makeSettings(sIn.width, sIn.contrast);
            const p = clampPoint(pIn);
            if (!p) return null;
            const r = s.width;
            const pxy = pixelOf(p);
            const ri = Math.ceil(r) + 1;
            const x0 = Math.max(0, pxy[0] - ri), y0 = Math.max(0, pxy[1] - ri);
            const x1 = Math.min(w, pxy[0] + ri + 1), y1 = Math.min(h, pxy[1] + ri + 1);
            if (x1 <= x0 || y1 <= y0) return p;
            ensure(x0, y0, x1, y1);
            let bestScore = -1, best = null;
            for (let y = y0; y < y1; y++) {
                for (let x = x0; x < x1; x++) {
                    const gi = y * w + x;
                    const st = strength[gi];
                    if (st < s.contrast || !ridge[gi]) continue;
                    const d = Math.hypot(x + 0.5 - p[0], y + 0.5 - p[1]);
                    if (d > r) continue;
                    const score = st * (1 - 0.25 * (d / r));
                    if (score > bestScore) { bestScore = score; best = pointAtIndex(gi, x, y, s.contrast); }
                }
            }
            return best || p;
        }

        // Squared distance of each window pixel centre to the guide polyline (Infinity beyond rad).
        function corridor(win, guide, rad) {
            const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
            const near = new Float32Array(ww * wh).fill(Infinity);
            const r2 = rad * rad;
            const segs = guide.length === 1 ? [guide[0], guide[0]] : guide;
            for (let si = 0; si + 1 < segs.length; si++) {
                const a = segs[si], b = segs[si + 1];
                const lx = Math.max(win.x0, Math.floor(Math.min(a[0], b[0]) - rad));
                const ly = Math.max(win.y0, Math.floor(Math.min(a[1], b[1]) - rad));
                const hx = Math.min(win.x1, Math.ceil(Math.max(a[0], b[0]) + rad) + 1);
                const hy = Math.min(win.y1, Math.ceil(Math.max(a[1], b[1]) + rad) + 1);
                for (let y = ly; y < hy; y++) {
                    for (let x = lx; x < hx; x++) {
                        const d2 = dist2Segment(x + 0.5, y + 0.5, a, b);
                        if (d2 <= r2) {
                            const li = (y - win.y0) * ww + (x - win.x0);
                            if (d2 < near[li]) near[li] = d2;
                        }
                    }
                }
            }
            return near;
        }

        function tracePiece(a, b, guide, s) {
            const rad = s.width + 1.5;
            const A = pixelOf(a), B = pixelOf(b);
            let bx0 = Math.min(A[0], B[0]), by0 = Math.min(A[1], B[1]);
            let bx1 = Math.max(A[0], B[0]) + 1, by1 = Math.max(A[1], B[1]) + 1;
            for (let i = 0; i < guide.length; i++) {
                const q = pixelOf(guide[i]);
                if (q[0] < bx0) bx0 = q[0]; if (q[1] < by0) by0 = q[1];
                if (q[0] + 1 > bx1) bx1 = q[0] + 1; if (q[1] + 1 > by1) by1 = q[1] + 1;
            }
            const inf = Math.ceil(rad) + 1;
            const win = {
                x0: Math.max(0, bx0 - inf), y0: Math.max(0, by0 - inf),
                x1: Math.min(w, bx1 + inf), y1: Math.min(h, by1 + inf),
            };
            const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
            if (ww <= 0 || wh <= 0) return [a, b];
            ensure(win.x0, win.y0, win.x1, win.y1);
            const near = corridor(win, guide, rad);
            const start = (A[1] - win.y0) * ww + (A[0] - win.x0);
            const goal = (B[1] - win.y0) * ww + (B[0] - win.x0);
            if (A[0] < win.x0 || A[0] >= win.x1 || A[1] < win.y0 || A[1] >= win.y1 ||
                B[0] < win.x0 || B[0] >= win.x1 || B[1] < win.y0 || B[1] >= win.y1) return [a, b];
            near[start] = 0; near[goal] = 0;
            const cells = search(win, ww, wh, near, rad * rad, start, goal, s.contrast);
            if (!cells) return [a, b];
            const pts = new Array(cells.length);
            for (let k = 0; k < cells.length; k++) {
                const li = cells[k];
                const x = (li % ww) + win.x0, y = ((li / ww) | 0) + win.y0;
                pts[k] = pointAtIndex(y * w + x, x, y, s.contrast);
            }
            if (pts.length < 2) return [a, b];
            pts[0] = a; pts[pts.length - 1] = b;
            return pts;
        }

        function search(win, ww, wh, near, rad2, start, goal, contrast) {
            const n = ww * wh;
            const node = new Float32Array(n).fill(Infinity);
            const tx = new Float32Array(n), ty = new Float32Array(n);
            const rr = Math.max(rad2, 1);
            const cden = Math.max(contrast, 0.02);
            for (let i = 0; i < n; i++) {
                const d2 = near[i];
                if (d2 === Infinity) continue;
                const x = (i % ww) + win.x0, y = ((i / ww) | 0) + win.y0;
                const gi = y * w + x;
                const st = strength[gi];
                const onEdge = st >= contrast && ridge[gi] === 1;
                const good = clamp((st - contrast) / cden, 0, 1) * (0.6 + 0.4 * Math.min(st, 1));
                const pull = Math.min(Math.sqrt(d2 / rr), 1);
                node[i] = W_CENTRE * (onEdge ? 0 : 1) + W_STRENGTH * (1 - good) + W_LENGTH + W_GUIDE * pull;
                if (st >= 0.5 * contrast) {
                    const g0 = gdx[gi] / 127, g1v = gdy[gi] / 127;
                    tx[i] = g1v; ty[i] = -g0;
                }
            }
            const dst = new Float32Array(n).fill(Infinity);
            const from = new Uint8Array(n).fill(255);
            dst[start] = 0;
            hn = 0;
            heapPush(0, start);
            while (hn > 0) {
                heapPop();
                const d = popK, i = popV;
                if (d > dst[i]) continue;
                if (i === goal) break;
                const x = i % ww, y = (i / ww) | 0;
                const tpx = tx[i], tpy = ty[i];
                for (let k = 0; k < 8; k++) {
                    const nx = x + DX[k], ny = y + DY[k];
                    if (nx < 0 || ny < 0 || nx >= ww || ny >= wh) continue;
                    const j = ny * ww + nx;
                    const cost = node[j];
                    if (cost === Infinity) continue;
                    const len = (DX[k] !== 0 && DY[k] !== 0) ? SQRT2 : 1;
                    const nd = d + cost * len + W_DIRECTION * directionCost(tpx, tpy, tx[j], ty[j], DX[k], DY[k], len);
                    if (nd < dst[j]) { dst[j] = nd; from[j] = k; heapPush(nd, j); }
                }
            }
            if (dst[goal] === Infinity) return null;
            const cells = [goal];
            let cur = goal;
            while (cur !== start && cells.length <= n) {
                const k = from[cur];
                if (k === 255) return null;
                const x = (cur % ww) - DX[k], y = ((cur / ww) | 0) - DY[k];
                if (x < 0 || y < 0) return null;
                cur = y * ww + x;
                cells.push(cur);
            }
            cells.reverse();
            return cells;
        }

        // The border from `from` to `to` along the edges near `guide`.
        function trace(fromIn, toIn, guide, sIn) {
            const s = makeSettings(sIn.width, sIn.contrast);
            const from = clampPoint(fromIn), to = clampPoint(toIn);
            if (!from || !to) return [];
            let g = [from];
            for (let i = 0; i < guide.length; i++) { const q = clampPoint(guide[i]); if (q) g.push(q); }
            g.push(to);
            g = simplify(g, 0.5);
            if (length(g) > MAX_GUIDE_LENGTH) return g;
            const pieces = split(g, PIECE);
            const out = [from];
            let cur = from;
            const last = pieces.length - 1;
            for (let k = 0; k <= last; k++) {
                const piece = pieces[k];
                let target = to;
                if (k !== last) { target = snap(piece[piece.length - 1], s) || to; }
                const seg = tracePiece(cur, target, piece, s);
                for (let i = 1; i < seg.length; i++) out.push(seg[i]);
                cur = target;
            }
            return simplify(out, 0.5);
        }

        return { w: w, h: h, rgba: rgba, snap: snap, trace: trace, ensure: ensure,
            field: { strength: strength, ridge: ridge, offx: offx, offy: offy, gdx: gdx, gdy: gdy } };
    }

    function directionCost(tpx, tpy, tqx, tqy, dx, dy, len) {
        if ((tpx === 0 && tpy === 0) || (tqx === 0 && tqy === 0)) return NEUTRAL_DIRECTION;
        let lx = dx / len, ly = dy / len;
        if (tpx * lx + tpy * ly < 0) { lx = -lx; ly = -ly; }
        const dp = clamp(tpx * lx + tpy * ly, -1, 1);
        const dq = clamp(lx * tqx + ly * tqy, -1, 1);
        return 2 / (3 * Math.PI) * (Math.acos(dp) + Math.acos(dq));
    }

    // ------------------------------------------------------ pointer controller
    // Port of magnetic_lasso_ui.rs: fastening points, live segment, Frequency
    // spacing, close, remove-last. Host supplies image + scale + commit.
    const ctl = {
        host: null,
        tracer: null,
        tracerKey: null,
        m: null,            // { path, anchors, trail, live, freehand }
        lastMoveMs: 0,
        overlay: null,
        stats: { lastTraceMs: 0, maxTraceMs: 0, traces: 0 },
    };

    function opt(id, d) {
        try {
            const el = typeof document !== 'undefined' && document.getElementById(id);
            const v = el ? parseFloat(el.value) : NaN;
            return Number.isFinite(v) ? v : d;
        } catch (e) { return d; }
    }
    function settings() {
        return makeSettings(opt('spbMagneticWidth', DEFAULTS.width), opt('spbMagneticContrast', DEFAULTS.contrast) / 100);
    }
    function scale() { // canvas pixels per screen pixel
        const s = ctl.host && ctl.host.scale ? ctl.host.scale() : 1;
        return s > 0 && Number.isFinite(s) ? s : 1;
    }
    function spacing() {
        const f = clamp(opt('spbMagneticFrequency', DEFAULTS.frequency), 0, 100);
        return (8 + (100 - f) * 0.9) * scale();
    }
    function closeRadius() { return 8 * scale(); }

    function enabled() {
        if (typeof window !== 'undefined' && window.SPB_PC_W4_OFF) return false;
        if (!ctl.host) return false;
        try {
            const el = document.getElementById('spbMagneticOn');
            return !!(el && el.checked);
        } catch (e) { return false; }
    }
    function active() { return !!(ctl.m && ctl.m.path.length); }

    function getTracer(fresh) {
        const img = ctl.host.getImage(!!fresh);
        if (!img) return null;
        const key = img.data;
        if (fresh || !ctl.tracer || ctl.tracerKey !== key || ctl.tracer.w !== img.w || ctl.tracer.h !== img.h) {
            ctl.tracer = createTracer(img.data, img.w, img.h);
            ctl.tracerKey = key;
        }
        return ctl.tracer;
    }

    function snapP(p, s) {
        const t = getTracer();
        return (t && t.snap(p, s)) || p;
    }
    function traceP(from, to, guide, s) {
        const t = getTracer();
        const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        const r = t ? t.trace(from, to, guide, s) : [];
        const dt = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0;
        ctl.stats.lastTraceMs = dt; ctl.stats.traces++;
        if (dt > ctl.stats.maxTraceMs) ctl.stats.maxTraceMs = dt;
        return r.length ? r : [from, to];
    }

    function extendTrail(q, s) {
        const gap = clamp(s.width / 4, 1, 8);
        const t = ctl.m.trail, n = t.length;
        if (n >= 2 && dist(t[n - 2], q) < gap) t[n - 1] = q; else t.push(q);
    }

    // The polyline p up to `len` along it and the point, when more than a pixel lies beyond.
    function cut(p, len) {
        if (length(p) < len + 1) return null;
        const head = [];
        let acc = 0;
        for (let i = 0; i + 1 < p.length; i++) {
            const a = p[i], b = p[i + 1];
            head.push(a);
            const d = dist(a, b);
            if (acc + d >= len && d > 0) {
                const t = (len - acc) / d;
                const point = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
                head.push(point);
                return { head: head, point: point };
            }
            acc += d;
        }
        return null;
    }

    function follow(q, s, fasten) {
        const m = ctl.m;
        extendTrail(q, s);
        const target = snapP(q, s);
        const every = spacing();
        for (let guard = 0; guard < 64; guard++) {
            const from = m.path[m.path.length - 1];
            if (!from) return;
            const live = traceP(from, target, m.trail.slice(), s);
            const c = fasten ? cut(live, every) : null;
            if (c) {
                for (let i = 1; i < c.head.length; i++) m.path.push(c.head[i]);
                m.anchors.push(m.path.length - 1);
                let near = 0, nd = Infinity;
                for (let i = 0; i < m.trail.length; i++) {
                    const d = dist(m.trail[i], c.point);
                    if (d < nd) { nd = d; near = i; }
                }
                m.trail = [c.point].concat(m.trail.slice(near + 1));
            } else {
                m.live = live;
                return;
            }
        }
    }

    function fastenLive() {
        const m = ctl.m;
        const live = m.live; m.live = [];
        const before = m.path.length;
        for (let i = 1; i < live.length; i++) {
            const last = m.path[m.path.length - 1];
            if (!last || dist(last, live[i]) > 1e-9) m.path.push(live[i]);
        }
        if (m.path.length > before) m.anchors.push(m.path.length - 1);
        const end = m.path[m.path.length - 1];
        if (end) m.trail = [end];
    }

    function nearStart(p) {
        const m = ctl.m;
        const r = closeRadius();
        return m.path.length > 0 && dist(m.path[0], p) <= r && length(m.path) + length(m.live) > 2 * r;
    }

    function commit() {
        const m = ctl.m;
        ctl.m = null;
        render();
        if (!m || m.path.length < 3) return false;
        return ctl.host.commit(m.path, ctl.lastEvent);
    }

    function down(pos, e) {
        ctl.lastEvent = e;
        const p = [pos.x + 0.5, pos.y + 0.5];
        const s = settings();
        const alt = !!(e && e.altKey);
        if (!active()) {
            const t = getTracer(true);
            if (!t) { if (ctl.host.toast) ctl.host.toast('Magnetic Lasso: load a paint image first'); return false; }
            const start = snapP(p, s);
            ctl.m = { path: [start], anchors: [0], trail: [p], live: [], freehand: false };
            render();
            return true;
        }
        const m = ctl.m;
        if (e && e.detail >= 2 && m.path.length > 2) { return close(false, e); }
        if (nearStart(p)) {
            const last = m.path[m.path.length - 1], first = m.path[0];
            const closing = alt ? [last, first] : traceP(last, first, m.trail.slice(), s);
            for (let i = 1; i < closing.length; i++) m.path.push(closing[i]);
            m.live = [];
            return commit();
        }
        if (alt) {
            const last = m.path[m.path.length - 1];
            if (!last || dist(last, p) > 1e-9) { m.path.push(p); m.anchors.push(m.path.length - 1); }
            m.live = []; m.trail = [p]; m.freehand = true;
            render();
            return true;
        }
        follow(p, s, false);
        fastenLive();
        render();
        return true;
    }

    function move(pos, e) {
        if (!active()) return false;
        ctl.lastEvent = e;
        const m = ctl.m;
        const p = [pos.x + 0.5, pos.y + 0.5];
        if (m.freehand) {
            const last = m.path[m.path.length - 1];
            if (!last || dist(last, p) >= 0.5) m.path.push(p);
            m.trail = [p];
            render();
            return true;
        }
        const s = settings();
        const step = Math.max(spacing() / 2, 1);
        const last = m.trail[m.trail.length - 1] || p;
        const n = clamp(Math.ceil(dist(last, p) / step), 1, 256);
        for (let k = 1; k <= n; k++) {
            const t = k / n;
            follow([last[0] + (p[0] - last[0]) * t, last[1] + (p[1] - last[1]) * t], s, true);
        }
        render();
        return true;
    }

    function up() {
        if (!active()) return false;
        const m = ctl.m;
        if (m.freehand) {
            m.freehand = false;
            if (m.anchors.length && m.anchors[m.anchors.length - 1] + 1 < m.path.length) m.anchors.push(m.path.length - 1);
            render();
        }
        return true;
    }

    // Enter: the live segment fastens, then the last point joins the first (along edges, or
    // straight with `straight`).
    function close(straight, e) {
        if (!active()) return false;
        if (e) ctl.lastEvent = e;
        up();
        fastenLive();
        const m = ctl.m;
        const first = m.path[0], last = m.path[m.path.length - 1];
        if (!straight && first && last) {
            const closing = traceP(last, first, [], settings());
            closing.pop();
            for (let i = 1; i < closing.length; i++) m.path.push(closing[i]);
        }
        return commit();
    }

    function removeLast() {
        if (!active()) return false;
        up();
        const m = ctl.m;
        if (m.anchors.length <= 1) { cancel(); return true; }
        m.anchors.pop();
        const keep = m.anchors.length ? m.anchors[m.anchors.length - 1] + 1 : 1;
        m.path.length = keep;
        m.live = [];
        const pointer = m.trail[m.trail.length - 1];
        m.trail = m.path.length ? [m.path[m.path.length - 1]] : [];
        if (pointer) follow(pointer, settings(), false);
        render();
        return true;
    }

    function cancel() {
        const had = active();
        ctl.m = null;
        render();
        return had;
    }

    // -------------------------------------------------------------- overlay
    function ensureOverlay() {
        if (typeof document === 'undefined') return null;
        let ov = ctl.overlay;
        const rc = document.getElementById('regionCanvas');
        const pc = document.getElementById('paintCanvas');
        if (!rc || !pc) return null;
        if (!ov || !ov.parentNode) {
            ov = document.createElement('canvas');
            ov.id = 'spbMagneticOverlay';
            ov.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:3;';
            rc.parentNode.insertBefore(ov, rc.nextSibling);
            ctl.overlay = ov;
        }
        if (ov.width !== pc.width) ov.width = pc.width;
        if (ov.height !== pc.height) ov.height = pc.height;
        ov.style.width = rc.style.width || pc.style.width || (rc.offsetWidth + 'px');
        ov.style.height = rc.style.height || pc.style.height || (rc.offsetHeight + 'px');
        return ov;
    }

    function render() {
        const ov = ensureOverlay();
        if (!ov) return;
        const ctx = ov.getContext('2d');
        ctx.clearRect(0, 0, ov.width, ov.height);
        const m = ctl.m;
        if (!m || !m.path.length) return;
        const sc = scale();
        const lw = Math.max(1.25, 1.1 * sc);
        const poly = m.path.concat(m.live.slice(1));
        ctx.save();
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(poly[0][0], poly[0][1]);
        for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i][0], poly[i][1]);
        ctx.strokeStyle = 'rgba(0,0,0,0.85)'; ctx.lineWidth = lw * 2.4; ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(m.path[0][0], m.path[0][1]);
        for (let i = 1; i < m.path.length; i++) ctx.lineTo(m.path[i][0], m.path[i][1]);
        ctx.strokeStyle = 'rgba(255,230,0,1)'; ctx.lineWidth = lw; ctx.stroke();
        if (m.live.length > 1) {
            ctx.beginPath();
            ctx.moveTo(m.live[0][0], m.live[0][1]);
            for (let i = 1; i < m.live.length; i++) ctx.lineTo(m.live[i][0], m.live[i][1]);
            ctx.strokeStyle = 'rgba(0,229,255,1)'; ctx.lineWidth = lw; ctx.stroke();
        }
        const sq = Math.max(2.5, 3 * sc);
        ctx.fillStyle = 'rgba(255,255,255,1)'; ctx.strokeStyle = 'rgba(0,0,0,1)'; ctx.lineWidth = Math.max(1, sc * 0.8);
        for (let i = 0; i < m.anchors.length; i++) {
            const a = m.path[m.anchors[i]];
            if (!a) continue;
            ctx.beginPath();
            if (i === 0) {
                ctx.arc(a[0], a[1], sq * 1.6, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(80,255,120,0.9)';
            } else {
                ctx.rect(a[0] - sq, a[1] - sq, sq * 2, sq * 2);
                ctx.fillStyle = 'rgba(255,255,255,1)';
            }
            ctx.fill(); ctx.stroke();
        }
        ctx.restore();
    }

    function setHost(h) { ctl.host = h; }

    return {
        version: 'w4-2026-10-09',
        createTracer: createTracer, simplify: simplify, split: split, length: length,
        makeSettings: makeSettings, DEFAULTS: DEFAULTS,
        setHost: setHost, enabled: enabled, active: active,
        down: down, move: move, up: up, close: close, removeLast: removeLast, cancel: cancel,
        stats: ctl.stats, _ctl: ctl,
    };
});
