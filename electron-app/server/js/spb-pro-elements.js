/* ============================================================================
   SPB PRO ELEMENTS - "where are the numbers / sponsors / stripes on a FLAT paint?"   (owner 2026-10-02)
   Most paints are flat TGAs with no layers, so "make the numbers purple" had nothing to point at.  A tiny segmentation net (trained on the owner's own livery PSDs, where the Numbers /
   Sponsors / Tape layers are the ground truth; js/spb-elements-model.js) says, for every pixel of the paint, body / numbers / sponsors+logos / stripes / dead space.  The net sees the sheet at
   192x192; its answer is then sharpened at full resolution by COLOUR: the glyph colours are measured from the confident pixels and the final mask keeps only the pixels of those colours
   near the net's answer, so a recolour has crisp edges.
   window.SpbProElements = { analyse, maskFor, kinds, overlay, teach, ready, forwardForTest, analysePixels }
   analyse() -> Promise({ kinds: { numbers|sponsors|stripes: { found, share, groups, boxes, colours, conf } } }); maskFor('numbers' | 'numbers:outline' | 'numbers:fill' | 'sponsors' | 'stripes') -> { mask (W*H, 255 = yes), desc, share }
   Works in the page and in node (pure functions on RGBA arrays).  ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var root = (typeof window !== 'undefined') ? window : (typeof global !== 'undefined' ? global : {});
    var NC = 5, KIND_IDX = { numbers: 1, sponsors: 2, stripes: 3 }, KIND_WORD = { numbers: 'the numbers', sponsors: 'the sponsors and logos', stripes: 'the stripes' };
    var _cache = null;                                  // { sig, W, H, result, masks:{kind:Uint8Array}, labs:{numbers:{lab, cols}} }

    // ------------------------------------------------------------------ model
    function b64Bytes(s) {
        if (typeof atob === 'function') { var bin = atob(s), u = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }
        return new Uint8Array(Buffer.from(s, 'base64'));
    }
    function model() {
        var M = root.SPB_ELEMENTS_MODEL; if (!M || !M.layers) return null;
        if (!M._ready) {
            M.layers.forEach(function (l) {
                var q = b64Bytes(l.w), f = new Float32Array(q.length), k;
                for (k = 0; k < q.length; k++) f[k] = (q[k] > 127 ? q[k] - 256 : q[k]) * l.s;
                l.W = f; l.Bf = new Float32Array(l.b);
            });
            M._ready = true;
        }
        return M;
    }
    // 3x3 conv (zero padding = dilation), optional ReLU; inp [cin][h][w] flat
    function conv(inp, cin, h, w, L, relu) {
        var cout = L.cout, d = L.dil || 1, hw = h * w, out = new Float32Array(cout * hw), W = L.W, B = L.Bf, co, ci, ky, kx, y, x, i;
        for (co = 0; co < cout; co++) {
            var o = co * hw, bias = B[co]; for (i = 0; i < hw; i++) out[o + i] = bias;
            for (ci = 0; ci < cin; ci++) {
                var ip = ci * hw, wb = (co * cin + ci) * 9;
                for (ky = -1; ky <= 1; ky++) {
                    var y0 = Math.max(0, -ky * d), y1 = Math.min(h, h - ky * d);
                    for (kx = -1; kx <= 1; kx++) {
                        var wv = W[wb + (ky + 1) * 3 + (kx + 1)]; if (wv === 0) continue;
                        var x0 = Math.max(0, -kx * d), x1 = Math.min(w, w - kx * d), sh = ky * d * w + kx * d;
                        for (y = y0; y < y1; y++) { var ob = o + y * w, ib = ip + y * w + sh; for (x = x0; x < x1; x++) out[ob + x] += wv * inp[ib + x]; }
                    }
                }
            }
            if (relu) for (i = 0; i < hw; i++) if (out[o + i] < 0) out[o + i] = 0;
        }
        return out;
    }
    function conv1(inp, cin, hw, L) {
        var out = new Float32Array(L.cout * hw), co, ci, i;
        for (co = 0; co < L.cout; co++) { var o = co * hw, bias = L.Bf[co]; for (i = 0; i < hw; i++) out[o + i] = bias; for (ci = 0; ci < cin; ci++) { var wv = L.W[co * cin + ci], ip = ci * hw; if (wv === 0) continue; for (i = 0; i < hw; i++) out[o + i] += wv * inp[ip + i]; } }
        return out;
    }
    function pool2(inp, c, h, w) {
        var h2 = h >> 1, w2 = w >> 1, out = new Float32Array(c * h2 * w2), k, y, x;
        for (k = 0; k < c; k++) for (y = 0; y < h2; y++) for (x = 0; x < w2; x++) { var b = k * h * w + 2 * y * w + 2 * x, m = inp[b]; if (inp[b + 1] > m) m = inp[b + 1]; if (inp[b + w] > m) m = inp[b + w]; if (inp[b + w + 1] > m) m = inp[b + w + 1]; out[k * h2 * w2 + y * w2 + x] = m; }
        return out;
    }
    function up2cat(inp, c, h, w, skip, cs) {            // nearest x2 of inp, then concat skip (cs channels at 2h x 2w)
        var H = h * 2, Wd = w * 2, out = new Float32Array((c + cs) * H * Wd), k, y, x;
        for (k = 0; k < c; k++) for (y = 0; y < H; y++) { var sy = k * h * w + (y >> 1) * w, oy = k * H * Wd + y * Wd; for (x = 0; x < Wd; x++) out[oy + x] = inp[sy + (x >> 1)]; }
        out.set(skip, c * H * Wd);
        return out;
    }
    // x: Float32Array [6][R][R] -> logits [NC][R][R]; hook(i) lets the page yield between layers
    function forward(x, R, M) {
        var L = M.layers, c = M.c, a, b, cc, d, u;
        a = conv(conv(x, 6, R, R, L[0], true), c, R, R, L[1], true);                         // e1
        var p1 = pool2(a, c, R, R); b = conv(conv(p1, c, R / 2, R / 2, L[2], true), 2 * c, R / 2, R / 2, L[3], true);       // e2
        var p2 = pool2(b, 2 * c, R / 2, R / 2); cc = conv(conv(p2, 2 * c, R / 4, R / 4, L[4], true), 3 * c, R / 4, R / 4, L[5], true);   // e3
        var p3 = pool2(cc, 3 * c, R / 4, R / 4); d = conv(conv(p3, 3 * c, R / 8, R / 8, L[6], true), 4 * c, R / 8, R / 8, L[7], true);   // e4 (dilated)
        u = conv(up2cat(d, 4 * c, R / 8, R / 8, cc, 3 * c), 7 * c, R / 4, R / 4, L[8], true);                               // d3
        u = conv(up2cat(u, 3 * c, R / 4, R / 4, b, 2 * c), 5 * c, R / 2, R / 2, L[9], true);                                // d2
        u = conv(up2cat(u, 2 * c, R / 2, R / 2, a, c), 3 * c, R, R, L[10], true);                                           // d1
        return conv1(u, c, R * R, L[11]);
    }
    function forwardAsync(x, R, M) {                       // the same net, split into slices so the page stays responsive
        return new Promise(function (resolve, reject) {
            var L = M.layers, c = M.c, st = {}, step = 0;
            var steps = [
                function () { st.a = conv(x, 6, R, R, L[0], true); },
                function () { st.a = conv(st.a, c, R, R, L[1], true); },
                function () { st.p1 = pool2(st.a, c, R, R); st.b = conv(st.p1, c, R / 2, R / 2, L[2], true); },
                function () { st.b = conv(st.b, 2 * c, R / 2, R / 2, L[3], true); },
                function () { st.p2 = pool2(st.b, 2 * c, R / 2, R / 2); st.c = conv(st.p2, 2 * c, R / 4, R / 4, L[4], true); },
                function () { st.c = conv(st.c, 3 * c, R / 4, R / 4, L[5], true); },
                function () { st.p3 = pool2(st.c, 3 * c, R / 4, R / 4); st.d = conv(st.p3, 3 * c, R / 8, R / 8, L[6], true); },
                function () { st.d = conv(st.d, 4 * c, R / 8, R / 8, L[7], true); },
                function () { st.u = conv(up2cat(st.d, 4 * c, R / 8, R / 8, st.c, 3 * c), 7 * c, R / 4, R / 4, L[8], true); },
                function () { st.u = conv(up2cat(st.u, 3 * c, R / 4, R / 4, st.b, 2 * c), 5 * c, R / 2, R / 2, L[9], true); },
                function () { st.u = conv(up2cat(st.u, 2 * c, R / 2, R / 2, st.a, c), 3 * c, R, R, L[10], true); },
                function () { st.out = conv1(st.u, c, R * R, L[11]); }
            ];
            (function next() {
                try { if (step >= steps.length) return resolve(st.out); steps[step++](); } catch (e) { return reject(e); }
                setTimeout(next, 0);
            })();
        });
    }

    // ------------------------------------------------------------------ pixels -> input tensor -> probabilities
    function toInput(d, W, H, R) {
        var n = R * R, sums = new Float32Array(4 * n), cnt = new Float32Array(n), x, y, o = 0;
        var xi = new Int32Array(W); for (x = 0; x < W; x++) xi[x] = Math.min(R - 1, (x * R / W) | 0);
        for (y = 0; y < H; y++) { var yr = Math.min(R - 1, (y * R / H) | 0) * R; for (x = 0; x < W; x++, o += 4) { var k = yr + xi[x]; sums[k] += d[o]; sums[n + k] += d[o + 1]; sums[2 * n + k] += d[o + 2]; sums[3 * n + k] += d[o + 3]; cnt[k]++; } }
        var inp = new Float32Array(6 * n), i;
        for (i = 0; i < n; i++) { var c = cnt[i] || 1; inp[i] = sums[i] / c / 255; inp[n + i] = sums[n + i] / c / 255; inp[2 * n + i] = sums[2 * n + i] / c / 255; inp[3 * n + i] = sums[3 * n + i] / c / 255; inp[4 * n + i] = (i % R) / (R - 1); inp[5 * n + i] = ((i / R) | 0) / (R - 1); }
        return inp;
    }
    function softmax(logits, n) {
        var P = new Float32Array(NC * n), i, k;
        for (i = 0; i < n; i++) { var m = -1e9; for (k = 0; k < NC; k++) if (logits[k * n + i] > m) m = logits[k * n + i]; var s = 0; for (k = 0; k < NC; k++) { var e = Math.exp(logits[k * n + i] - m); P[k * n + i] = e; s += e; } for (k = 0; k < NC; k++) P[k * n + i] /= s; }
        return P;
    }
    function sigOf(inp) { var h = 2166136261, i, n = inp.length, st = Math.max(1, (n / 4096) | 0); for (i = 0; i < n; i += st) { h ^= Math.round(inp[i] * 255); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16) + ':' + n; }
    function analysisSig(inp, W, H, car) { return sigOf(inp) + ':' + W + 'x' + H + ':' + (car || ''); }

    // ------------------------------------------------------------------ full-resolution sharpening by colour
    function hexOf(r, g, b) { function p(v) { var h = v.toString(16); return h.length < 2 ? '0' + h : h; } return '#' + p(r) + p(g) + p(b); }
    function colourSet(d, W, H, probFn, thr, minShare, maxN) {
        var bins = {}, total = 0, x, y, o;
        for (y = 0; y < H; y += 2) for (x = 0; x < W; x += 2) {
            if (probFn(x, y) < thr) continue; o = (y * W + x) * 4; if (d[o + 3] < 128) continue; total++;
            var k = (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3), e = bins[k] || (bins[k] = { n: 0, r: 0, g: 0, b: 0 }); e.n++; e.r += d[o]; e.g += d[o + 1]; e.b += d[o + 2];
        }
        var arr = Object.keys(bins).map(function (k) { var e = bins[k]; return { n: e.n, r: Math.round(e.r / e.n), g: Math.round(e.g / e.n), b: Math.round(e.b / e.n) }; }).sort(function (a, b) { return b.n - a.n; }), out = [];
        arr.forEach(function (e) {
            if (out.length >= maxN || e.n < total * minShare) return;
            var near = out.filter(function (q) { return Math.abs(q.r - e.r) < 40 && Math.abs(q.g - e.g) < 40 && Math.abs(q.b - e.b) < 40; })[0];
            if (near) { near.n += e.n; return; }
            out.push({ r: e.r, g: e.g, b: e.b, n: e.n });
        });
        return { cols: out, total: total };
    }
    function bilinearFn(P, kidx, R, W, H) {
        var n = R * R, off = kidx * n;
        return function (x, y) {
            var fx = (x + 0.5) * R / W - 0.5, fy = (y + 0.5) * R / H - 0.5, x0 = Math.floor(fx), y0 = Math.floor(fy), tx = fx - x0, ty = fy - y0;
            var x1 = Math.min(R - 1, x0 + 1), y1 = Math.min(R - 1, y0 + 1); x0 = Math.max(0, x0); y0 = Math.max(0, y0);
            var a = P[off + y0 * R + x0], b = P[off + y0 * R + x1], c = P[off + y1 * R + x0], dd = P[off + y1 * R + x1];
            return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + dd * tx) * ty;
        };
    }
    // the mask of one kind at full resolution: colours of the confident pixels, kept near the net's answer; then a 3x3 clean-up (fill pin-holes, drop specks)
    function sharpen(d, W, H, P, R, kidx, opts) {
        opts = opts || {};
        var pf = bilinearFn(P, kidx, R, W, H), cs = colourSet(d, W, H, pf, opts.conf || 0.7, opts.minShare || 0.04, opts.maxCols || 4);
        if (opts.dropBody && cs.cols.length > 1) {
            cs.cols.sort(function (a, b) { return b.n - a.n; });
            var bc = colourSet(d, W, H, function (xx, yy) { return 1 - pf(xx, yy); }, 0.96, 0.06, 6), keep = cs.cols.filter(function (c, ci) {
                if (ci === 0) return true;
                var amb = bc.cols.some(function (b) { return Math.abs(b.r - c.r) < 44 && Math.abs(b.g - c.g) < 44 && Math.abs(b.b - c.b) < 44; });
                return !amb;
            });
            if (keep.length) cs.cols = keep;
        }
        var mask = new Uint8Array(W * H), lab = new Uint8Array(W * H), tol = opts.tol || 34, x, y, k;
        if (!cs.cols.length) return { mask: mask, lab: lab, cols: [], total: 0 };
        for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
            if (pf(x, y) < (opts.near || 0.22)) continue; var o = (y * W + x) * 4; if (d[o + 3] < 128) continue;
            for (k = 0; k < cs.cols.length; k++) { var c = cs.cols[k]; if (Math.abs(d[o] - c.r) <= tol && Math.abs(d[o + 1] - c.g) <= tol && Math.abs(d[o + 2] - c.b) <= tol) { mask[y * W + x] = 255; lab[y * W + x] = k + 1; break; } }
        }
        // pin-holes (an anti-aliased pixel inside a glyph) and specks
        var out = new Uint8Array(mask), lo = new Uint8Array(lab);
        for (y = 1; y < H - 1; y++) for (x = 1; x < W - 1; x++) {
            var i = y * W + x, nb = (mask[i - 1] ? 1 : 0) + (mask[i + 1] ? 1 : 0) + (mask[i - W] ? 1 : 0) + (mask[i + W] ? 1 : 0) + (mask[i - W - 1] ? 1 : 0) + (mask[i - W + 1] ? 1 : 0) + (mask[i + W - 1] ? 1 : 0) + (mask[i + W + 1] ? 1 : 0);
            if (!mask[i] && nb >= 7 && pf(x, y) > 0.3) { out[i] = 255; var kk = lab[i - 1] || lab[i + 1] || lab[i - W] || lab[i + W]; lo[i] = kk; }
            else if (mask[i] && nb <= 1) { out[i] = 0; lo[i] = 0; }
        }
        return { mask: out, lab: lo, cols: cs.cols.map(function (c) { return { hex: hexOf(c.r, c.g, c.b), share: c.n / cs.total }; }), total: cs.total };
    }
    function boxSharpen(d, W, H, P, R, kidx, groups, opts) {
        opts = opts || {};
        var pf = bilinearFn(P, kidx, R, W, H), mask = new Uint8Array(W * H), lab = new Uint8Array(W * H), padIn = opts.padIn || 0.02, padOut = opts.padOut || 0.05, tol = opts.tol || 42, allCols = [], total = 0;
        groups.forEach(function (g) {
            var bx0 = Math.max(0, Math.floor((g.box[0] - padIn) * W)), by0 = Math.max(0, Math.floor((g.box[1] - padIn) * H)), bx1 = Math.min(W, Math.ceil((g.box[2] + padIn) * W)), by1 = Math.min(H, Math.ceil((g.box[3] + padIn) * H));
            var ox0 = Math.max(0, Math.floor((g.box[0] - padOut) * W)), oy0 = Math.max(0, Math.floor((g.box[1] - padOut) * H)), ox1 = Math.min(W, Math.ceil((g.box[2] + padOut) * W)), oy1 = Math.min(H, Math.ceil((g.box[3] + padOut) * H));
            // the paint around the box (pixels the net is sure are NOT a number): its main colours are the background
            var ring = {}, rn = 0, x, y, o;
            for (y = oy0; y < oy1; y += 2) for (x = ox0; x < ox1; x += 2) {
                if (x >= bx0 && x < bx1 && y >= by0 && y < by1) continue; if (pf(x, y) > 0.05) continue; o = (y * W + x) * 4; if (d[o + 3] < 128) continue; rn++;
                var k = (d[o] >> 4) * 256 + (d[o + 1] >> 4) * 16 + (d[o + 2] >> 4), e = ring[k] || (ring[k] = { n: 0, r: 0, g: 0, b: 0 }); e.n++; e.r += d[o]; e.g += d[o + 1]; e.b += d[o + 2];
            }
            var bg = Object.keys(ring).map(function (k) { var e = ring[k]; return { n: e.n, r: e.r / e.n, g: e.g / e.n, b: e.b / e.n }; }).sort(function (a, b) { return b.n - a.n; }).filter(function (e) { return e.n >= rn * (opts.ringShare || 0.1); }).slice(0, 4);
            // a PHOTO (a face, a car picture) inside the box is not a number: flat-colour glyphs are made of a few colours, photos of thousands
            var h0 = {}, g0 = 0, jj;
            for (y = by0; y < by1; y += 2) for (x = bx0; x < bx1; x += 2) {
                o = (y * W + x) * 4; if (d[o + 3] < 128) continue; var bgx = false; for (jj = 0; jj < bg.length; jj++) if (Math.abs(d[o] - bg[jj].r) <= tol && Math.abs(d[o + 1] - bg[jj].g) <= tol && Math.abs(d[o + 2] - bg[jj].b) <= tol) { bgx = true; break; }
                if (bgx || pf(x, y) < (opts.near || 0.02)) continue; var k0 = (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3); h0[k0] = (h0[k0] || 0) + 1; g0++;
            }
            var top3 = Object.keys(h0).map(function (k) { return h0[k]; }).sort(function (u, v) { return v - u; }).slice(0, 3).reduce(function (u, v) { return u + v; }, 0);
            if (g0 > 30 && top3 / g0 < (opts.flatShare || 0.2)) { if (opts.debug) opts.debug.push({ box: g.box, skipped: 'photo-like (top3 ' + Math.round(top3 / g0 * 100) + '%)' }); return; }
            var hist = {}, gn = 0;
            for (y = by0; y < by1; y++) for (x = bx0; x < bx1; x++) {
                o = (y * W + x) * 4; if (d[o + 3] < 128) continue;
                var isBg = false, j; for (j = 0; j < bg.length; j++) if (Math.abs(d[o] - bg[j].r) <= tol && Math.abs(d[o + 1] - bg[j].g) <= tol && Math.abs(d[o + 2] - bg[j].b) <= tol) { isBg = true; break; }
                if (isBg || pf(x, y) < (opts.near || 0.02)) continue;
                mask[y * W + x] = 255; gn++;
                var kk = (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3), he = hist[kk] || (hist[kk] = { n: 0, r: 0, g: 0, b: 0 }); he.n++; he.r += d[o]; he.g += d[o + 1]; he.b += d[o + 2];
            }
            if (opts.debug) opts.debug.push({ box: g.box.map(function (v) { return Math.round(v * 100) / 100; }), ringN: rn, bg: bg.map(function (b) { return hexOf(Math.round(b.r), Math.round(b.g), Math.round(b.b)) + ':' + Math.round(b.n / Math.max(1, rn) * 100) + '%'; }), glyph: Object.keys(hist).map(function (k) { var e = hist[k]; return { n: e.n, hex: hexOf(Math.round(e.r / e.n), Math.round(e.g / e.n), Math.round(e.b / e.n)) }; }).sort(function (x, y) { return y.n - x.n; }).slice(0, 5).map(function (e) { return e.hex + ':' + e.n; }) });
            Object.keys(hist).forEach(function (k) { var e = hist[k]; allCols.push({ n: e.n, r: Math.round(e.r / e.n), g: Math.round(e.g / e.n), b: Math.round(e.b / e.n) }); }); total += gn;
        });
        allCols.sort(function (a, b) { return b.n - a.n; });
        var cols = []; allCols.forEach(function (e) { if (cols.length >= (opts.maxCols || 5)) return; var near = cols.filter(function (q) { return Math.abs(q.r - e.r) < 40 && Math.abs(q.g - e.g) < 40 && Math.abs(q.b - e.b) < 40; })[0]; if (near) { near.n += e.n; return; } cols.push({ r: e.r, g: e.g, b: e.b, n: e.n }); });
        cols = cols.filter(function (c) { return c.n >= total * (opts.minShare || 0.03); });
        var x2, y2, i2, k2; for (i2 = 0; i2 < mask.length; i2++) if (mask[i2]) { var o2 = i2 * 4, bi = -1, bd = 1e9; for (k2 = 0; k2 < cols.length; k2++) { var dd = Math.max(Math.abs(d[o2] - cols[k2].r), Math.abs(d[o2 + 1] - cols[k2].g), Math.abs(d[o2 + 2] - cols[k2].b)); if (dd < bd) { bd = dd; bi = k2; } } lab[i2] = bi + 1; }
        return { mask: mask, lab: lab, cols: cols.map(function (c) { return { hex: hexOf(c.r, c.g, c.b), share: c.n / Math.max(1, total) }; }), total: total };
    }
    // connected groups on the net's own grid (a number = a group of glyphs close together)
    function groupsOf(P, R, kidx, thr) {
        var n = R * R, off = kidx * n, on = new Uint8Array(n), i, y, x;
        for (i = 0; i < n; i++) on[i] = P[off + i] >= thr ? 1 : 0;
        var dil = new Uint8Array(n);                                    // glue digits of one number (gap of a few cells)
        for (y = 0; y < R; y++) for (x = 0; x < R; x++) if (on[y * R + x]) for (var dy = -2; dy <= 2; dy++) for (var dx = -3; dx <= 3; dx++) { var yy = y + dy, xx = x + dx; if (yy >= 0 && yy < R && xx >= 0 && xx < R) dil[yy * R + xx] = 1; }
        var seen = new Uint8Array(n), groups = [], stack = [];
        for (i = 0; i < n; i++) {
            if (!dil[i] || seen[i]) continue; var px = 0, x0 = R, y0 = R, x1 = 0, y1 = 0, s = 0; stack.length = 0; stack.push(i); seen[i] = 1;
            while (stack.length) {
                var c = stack.pop(), cx = c % R, cy = (c / R) | 0; if (on[c]) { px++; s += P[off + c]; if (cx < x0) x0 = cx; if (cy < y0) y0 = cy; if (cx > x1) x1 = cx; if (cy > y1) y1 = cy; }
                if (cx > 0 && dil[c - 1] && !seen[c - 1]) { seen[c - 1] = 1; stack.push(c - 1); } if (cx < R - 1 && dil[c + 1] && !seen[c + 1]) { seen[c + 1] = 1; stack.push(c + 1); }
                if (cy > 0 && dil[c - R] && !seen[c - R]) { seen[c - R] = 1; stack.push(c - R); } if (cy < R - 1 && dil[c + R] && !seen[c + R]) { seen[c + R] = 1; stack.push(c + R); }
            }
            if (px >= 6) groups.push({ px: px, mean: s / px, box: [x0 / R, y0 / R, (x1 + 1) / R, (y1 + 1) / R] });
        }
        return groups;
    }

    // pure analysis of an RGBA paint; P are the net's probabilities (computed by the caller: sync forward() or forwardAsync())
    var SHARP = { numbers: { mode: 'box', padIn: 0.04, padOut: 0.07, tol: 32, near: 0, minShare: 0.03, maxCols: 5, ringShare: 0.4, conf: 0.5, dropBody: true }, sponsors: { conf: 0.4, minShare: 0.01, near: 0.08, tol: 60, maxCols: 12 }, stripes: { conf: 0.4, minShare: 0.015, near: 0.08, tol: 64, maxCols: 6 } };          // tuned on cars the net never saw (e6_tune.js): numbers IoU 0.53 -> 0.65
    function summarise(d, W, H, P, R, sharp, learned) {
        sharp = sharp || SHARP;
        var n = R * R, out = { kinds: {} }, masks = {}, labs = {}, paintable = 0, i;
        for (i = 0; i < n; i++) if (P[4 * n + i] < 0.5) paintable++;
        paintable = Math.max(1, paintable / n);
        Object.keys(KIND_IDX).forEach(function (kind) {
            var kidx = KIND_IDX[kind], sh, groups = groupsOf(P, R, kidx, 0.5), gp = groups.filter(function (g) { return g.mean >= 0.55; }), lr = kind === 'numbers' && learned && learned[kind];
            // Remembered boxes belong to other paints of this car. Keep them visible as proposals,
            // but never feed them into this paint's detector groups, mask, found flag, or confidence.
            var rejected = lr && (lr.rejected === true || lr.status === 'rejected' || lr.decision === 'reject');
            var proposalBoxes = lr && !rejected ? cleanBoxes(lr.boxes) : [];
            if (sharp[kind].mode === 'box' && gp.length) sh = boxSharpen(d, W, H, P, R, kidx, gp, sharp[kind]);
            else sh = sharpen(d, W, H, P, R, kidx, sharp[kind]);
            var px = 0, k; for (k = 0; k < sh.mask.length; k++) if (sh.mask[k]) px++;
            var share = px / (W * H) / paintable * 100;
            var meanP = gp.length ? gp.reduce(function (a, g) { return a + g.mean * g.px; }, 0) / gp.reduce(function (a, g) { return a + g.px; }, 0) : 0;
            var found = share >= (kind === 'numbers' ? 0.25 : 0.15) && gp.length >= 1 && meanP >= 0.6;
            masks[kind] = sh.mask; labs[kind] = { lab: sh.lab, cols: sh.cols };
            out.kinds[kind] = { learned: proposalBoxes.length > 0, proposals: proposalBoxes.map(function (b) { return { box: b.slice(), provenance: lr.how || lr.source || 'unknown' }; }), found: found, share: Math.round(share * 10) / 10, groups: gp.length, boxes: gp.map(function (g) { return g.box; }), colours: sh.cols.map(function (c) { return c.hex; }), conf: Math.round(Math.min(1, meanP * (kind === 'numbers' ? (gp.length >= 1 && gp.length <= 8 ? 1 : 0.7) : 1)) * 100) / 100 };
        });
        return { result: out, masks: masks, labs: labs };
    }
    function probsOf(d, W, H) { var M = model(); if (!M) return null; var R = M.res, x = toInput(d, W, H, R); return { P: softmax(forward(x, R, M), R * R), R: R }; }
    function analysePixels(d, W, H, sharp) {           // sync (node tests): RGBA -> { result, masks, labs }
        var pr = probsOf(d, W, H); if (!pr) return null; return summarise(d, W, H, pr.P, pr.R, sharp);
    }

    // ------------------------------------------------------------------ the page: the app's own paint
    function paintData() { try { return (typeof paintImageData !== 'undefined' && paintImageData && paintImageData.data) ? paintImageData : null; } catch (e) { return null; } }
    function ready() { return !!model() && !!paintData(); }
    // ------------------------------------------------------------------ WHAT THE BUYER TOLD US ABOUT THIS CAR (owner 2026-10-03)
    // The net is only PROVEN on truck sheets (its holdout is nearly all trucks; e10_conf.js: its own confidence is 0.9+ whether it is right or wrong). Remembered boxes are
    // per-car proposals from other paints, never current-paint confirmation; the buyer still confirms, rejects, or teaches each paint.
    var LS_LEARN = 'spb_elem_learned_v1', _lv = 0, _learnMem = null, _synced = false;
    function normalizeCarKey(k) { return String(k || '').toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 80); }
    function carKey() { try { var C = root.SpbProCar, k = C && C.effFolder ? C.effFolder() : ''; return normalizeCarKey(k); } catch (e) { return ''; } }
    function learnLoad() { if (_learnMem) return _learnMem; try { _learnMem = JSON.parse(root.localStorage.getItem(LS_LEARN) || '{}') || {}; } catch (e) { _learnMem = {}; } return _learnMem; }
    function learnSave() { try { root.localStorage.setItem(LS_LEARN, JSON.stringify(_learnMem || {})); return true; } catch (e) { return false; } }
    function cleanBoxes(bx) {
        var out = []; (bx || []).forEach(function (b) {
            if (!b || b.length < 4) return; var q = [Math.max(0, +b[0]), Math.max(0, +b[1]), Math.min(1, +b[2]), Math.min(1, +b[3])];
            if (!(q[2] > q[0] && q[3] > q[1]) || (q[2] - q[0]) * (q[3] - q[1]) > 0.3) return; out.push(q.map(function (v) { return Math.round(v * 1000) / 1000; }));
        });
        return out.slice(0, 12);
    }
    function learnedFor(kind) { var k = carKey(); if (!k || kind !== 'numbers') return null; var e = (learnLoad()[k] || {})[kind]; return e && !e.rejected && e.status !== 'rejected' && e.decision !== 'reject' && e.boxes && e.boxes.length ? e : null; }
    function remember(kind, boxes, how) {
        var k = carKey(), bx = cleanBoxes(boxes); if (!k || kind !== 'numbers' || !bx.length) return false;
        var m = learnLoad(); (m[k] = m[k] || {})[kind] = { boxes: bx, how: how || 'confirm', at: Date.now() }; learnSave(); _lv++;
        try { if (root.fetch) root.fetch('/api/ai/learned-elements', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: k, kind: kind, boxes: bx, source: how || 'confirm' }) }).catch(function () {}); } catch (e) {}
        return true;
    }
    function forget(kind) {
        var k = carKey(), m = learnLoad(), prior = k && m[k] && m[k][kind], had = !!(prior && prior.boxes && prior.boxes.length);
        if (k && kind === 'numbers') { (m[k] = m[k] || {})[kind] = { rejected: true, status: 'rejected', how: 'buyer-rejected', at: Date.now() }; learnSave(); }
        else if (prior) { delete m[k][kind]; learnSave(); }
        _lv++; if (_cache && _cache.taught) { delete _cache.taught[kind]; ['tlabs', 'tinfo', 'tcols'].forEach(function (q) { if (_cache[q]) delete _cache[q][kind]; }); }
        try { if (k && root.fetch) root.fetch('/api/ai/learned-elements', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: k, kind: kind, forget: true }) }).catch(function () {}); } catch (e) {}
        return had;
    }
    function syncLearned() {
        if (_synced || !root.fetch) return; _synced = true;
        try { root.fetch('/api/ai/learned-elements').then(function (r) { return r && r.ok ? r.json() : null; }).then(function (j) {
            if (!j || !Array.isArray(j.rows)) return; var m = learnLoad(), n = 0;
            j.rows.forEach(function (r) {
                var k = r && normalizeCarKey(r.key); if (!k || r.kind !== 'numbers' || (m[k] && m[k].numbers)) return;
                var bx = cleanBoxes(r.boxes); if (bx.length) { (m[k] = m[k] || {}).numbers = { boxes: bx, how: 'server', at: 0 }; n++; }
            });
            if (n) { learnSave(); _lv++; }
        }).catch(function () {}); } catch (e) {}
    }
    function learnReset() { _learnMem = {}; learnSave(); _lv++; }
    function analyse(opts) {
        opts = opts || {};
        var M = model(), pd = paintData();
        if (!M || !pd) return Promise.reject(new Error('no paint or no model'));
        var W = pd.width, H = pd.height, R = M.res, x = toInput(pd.data, W, H, R), sig = analysisSig(x, W, H, carKey());
        syncLearned();
        if (_cache && _cache.sig === sig && _cache.lv === _lv && !opts.force) return Promise.resolve(_cache.result);
        var lrn = {}, le = learnedFor('numbers'); if (le) lrn.numbers = le;
        return forwardAsync(x, R, M).then(function (logits) {
            var P = softmax(logits, R * R), s = summarise(pd.data, W, H, P, R, null, lrn);
            var prevC = (_cache && _cache.sig === sig) ? _cache : null;
            _cache = { sig: sig, lv: _lv, W: W, H: H, P: P, R: R, result: s.result, masks: s.masks, labs: s.labs, taught: (prevC && prevC.taught) || {}, tlabs: (prevC && prevC.tlabs) || {}, tinfo: (prevC && prevC.tinfo) || {}, tcols: (prevC && prevC.tcols) || {} };
            Object.keys(_cache.taught).forEach(function (k) {
                if (_cache.tlabs[k]) _cache.labs[k] = _cache.tlabs[k];
                var inf = _cache.tinfo[k], rk = _cache.result.kinds[k]; if (inf && rk) { rk.boxes = inf.boxes; rk.groups = inf.groups; rk.share = inf.share; rk.colours = inf.colours; rk.found = true; rk.taught = true; rk.conf = 1; }
            });
            return s.result;
        });
    }
    // 'numbers' | 'numbers:outline' | 'numbers:fill' | 'numbers:shadow' | 'sponsors' | 'stripes'
    function maskFor(spec) {
        if (!_cache) return null; var parts = String(spec || '').split(':'), kind = parts[0], sub = parts[1] || null;
        var base = _cache.taught && _cache.taught[kind] ? _cache.taught[kind] : _cache.masks[kind]; if (!base) return null;
        var W = _cache.W, H = _cache.H, m = base, info = _cache.result.kinds[kind] || {}, desc = KIND_WORD[kind] || kind;
        if (sub && kind === 'numbers' && _cache.labs.numbers && _cache.labs.numbers.cols.length > 1) {
            var L = _cache.labs.numbers, nc = L.cols.length, area = [], edge = [], k, i, x, y;
            for (k = 0; k < nc; k++) { area.push(0); edge.push(0); }
            for (y = 4; y < H - 4; y += 2) for (x = 4; x < W - 4; x += 2) {
                i = y * W + x; var lb = L.lab[i]; if (!lb) continue; area[lb - 1]++;
                if (!base[i - 4] || !base[i + 4] || !base[i - 4 * W] || !base[i + 4 * W]) edge[lb - 1]++;
            }
            var order = []; for (k = 0; k < nc; k++) order.push(k); order.sort(function (a, b) { return area[b] - area[a]; });
            var fill = order[0], rest = order.slice(1).sort(function (a, b) { return (edge[b] / Math.max(1, area[b])) - (edge[a] / Math.max(1, area[a])); });
            function hs(hex) { var r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0; if (d) h = mx === r ? ((g - b) / d + 6) % 6 : (mx === g ? (b - r) / d + 2 : (r - g) / d + 4); return { h: h * 60, s: mx ? d / mx : 0 }; }
            var fh = hs(L.cols[fill].hex), fam = [];
            if (fh.s > 0.45) rest.forEach(function (k) { var q = hs(L.cols[k].hex), dh = Math.abs(q.h - fh.h); if (dh > 180) dh = 360 - dh; if (q.s > 0.45 && dh <= 18) fam.push(k); });
            rest = rest.filter(function (k) { return fam.indexOf(k) === -1; });
            var pick = sub === 'fill' ? [fill].concat(fam) : (sub === 'outline' ? (rest.length ? [rest[0]] : []) : (rest.length > 1 ? [rest[1]] : []));
            var tb = (_cache.taught && _cache.taught.numbers && _cache.tinfo && _cache.tinfo.numbers && _cache.tinfo.numbers.boxes) || null, pb = tb && (sub === 'fill' || sub === 'outline') ? subPerBox(L, base, W, H, tb, sub, nc) : null;
            if (!pick.length && !(pb && pb.any)) return { mask: base, desc: desc + ' (this paint has no separate ' + sub + ' colour: the whole number)', share: info.share };
            m = new Uint8Array(W * H); for (i = 0; i < m.length; i++) if ((pb && pb.inBox[i]) ? pb.m[i] : pick.indexOf(L.lab[i] - 1) !== -1) m[i] = 255;
            desc = 'the number ' + sub;
        }
        return { mask: m, desc: desc, share: info.share };
    }
    // WP5 / WP3 defects 1-2: per marked place, the FILL = the solid (lowest edge ratio) colour among the big ones, the OUTLINE = the thinnest, and a plate
    // (the biggest, solid colour spanning the whole place with the digits inside it) is neither; one place's fill colour no longer decides another's
    function subPerBox(L, base, W, H, boxes, sub, nc) {
        var inBox = new Uint8Array(W * H), out = new Uint8Array(W * H), any = false;
        boxes.forEach(function (b) {
            var X0 = Math.max(0, Math.floor((b[0] - 0.005) * W)), Y0 = Math.max(0, Math.floor((b[1] - 0.005) * H)), X1 = Math.min(W, Math.ceil((b[2] + 0.005) * W)), Y1 = Math.min(H, Math.ceil((b[3] + 0.005) * H));
            var area = [], edge = [], bx = [], k, x, y, i, tot = 0; for (k = 0; k < nc; k++) { area.push(0); edge.push(0); bx.push([W, H, 0, 0]); }
            var sx0 = W, sy0 = H, sx1 = 0, sy1 = 0;
            for (y = Y0; y < Y1; y++) for (x = X0; x < X1; x++) { i = y * W + x; inBox[i] = 1; var lb = L.lab[i]; if (!base[i] || !lb) continue; k = lb - 1; area[k]++; tot++; var q = bx[k]; if (x < q[0]) q[0] = x; if (y < q[1]) q[1] = y; if (x > q[2]) q[2] = x; if (y > q[3]) q[3] = y; if (x < sx0) sx0 = x; if (y < sy0) sy0 = y; if (x > sx1) sx1 = x; if (y > sy1) sy1 = y;
                if (x < 2 || y < 2 || x >= W - 2 || y >= H - 2 || L.lab[i - 2] !== lb || L.lab[i + 2] !== lb || L.lab[i - 2 * W] !== lb || L.lab[i + 2 * W] !== lb) edge[k]++; }
            if (!tot) return;
            var labs = []; for (k = 0; k < nc; k++) if (area[k] >= tot * 0.04) labs.push(k); if (!labs.length) return;
            var er = function (k2) { return edge[k2] / Math.max(1, area[k2]); };
            labs.sort(function (a, b2) { return area[b2] - area[a]; });
            var big = labs[0], bq = bx[big], plate = -1;
            // MCPSCEN 2026-10-05 (owner SS flat sheet, gold chrome numbers: the big roof / lower-side "32" had their charcoal FILL taken for a plate, since fill + drop
            // shadow span the whole number, so the white / black outline was recoloured instead of the fill). A plate is the paint the digits sit on: it reaches
            // the border of the loose box (the small "32" on yellow: 17% of the border); a fill never does (0%). bc = the big colour's share of the box border.
            var bc = 0, bt = 0; for (y = Y0; y < Y1; y++) for (x = X0; x < X1; x++) { if (y > Y0 + 3 && y < Y1 - 4 && x > X0 + 3 && x < X1 - 4) continue; i = y * W + x; bt++; if (base[i] && L.lab[i] === big + 1) bc++; }
            if (labs.length > 1 && bt && bc >= bt * 0.05 && area[big] >= tot * 0.4 && labs.every(function (k2) { return k2 === big || er(k2) > er(big); }) && (bq[2] - bq[0] + 1) >= 0.85 * (sx1 - sx0 + 1) && (bq[3] - bq[1] + 1) >= 0.85 * (sy1 - sy0 + 1)) {
                var inner = labs.filter(function (k2) { var q2 = bx[k2]; return k2 !== big && q2[0] >= bq[0] && q2[1] >= bq[1] && q2[2] <= bq[2] && q2[3] <= bq[3]; }), innerA = 0; inner.forEach(function (k2) { innerA += area[k2]; });
                if (innerA >= tot * 0.08 && inner.length === labs.length - 1) plate = big;
            }
            var cand = labs.filter(function (k2) { return k2 !== plate; }); if (!cand.length) return;
            var maxA = 0; cand.forEach(function (k2) { if (area[k2] > maxA) maxA = area[k2]; });
            var bigOnes = cand.filter(function (k2) { return area[k2] >= maxA * 0.3; }), fillK = bigOnes.slice().sort(function (a, b2) { return er(a) - er(b2); })[0];
            var others = cand.filter(function (k2) { return k2 !== fillK; }).sort(function (a, b2) { return er(b2) - er(a); });
            var pick = sub === 'fill' ? [fillK] : (others.length ? [others[0]] : []);
            if (!pick.length) return; any = true;
            for (y = Y0; y < Y1; y++) for (x = X0; x < X1; x++) { i = y * W + x; if (base[i] && pick.indexOf(L.lab[i] - 1) !== -1) out[i] = 255; }
        });
        return { inBox: inBox, m: out, any: any };
    }
    function kinds() { return _cache ? _cache.result.kinds : null; }
    // the plain paint as a small picture (no tint): what the buyer draws a box on when the app could not find a number itself
    function thumb(size) {
        try {
            var pd = paintData(); if (!pd) return null; var W = pd.width, H = pd.height, n = Math.max(256, Math.min(900, size || 420)), cv = document.createElement('canvas'); cv.width = cv.height = n;
            var cx = cv.getContext('2d'), im = cx.createImageData(n, n), o = im.data, x, y;
            for (y = 0; y < n; y++) for (x = 0; x < n; x++) { var sx = Math.min(W - 1, (x * W / n) | 0), sy = Math.min(H - 1, (y * H / n) | 0), p = (sy * W + sx) * 4, q = (y * n + x) * 4, a = pd.data[p + 3] / 255; o[q] = pd.data[p] * a + 30 * (1 - a); o[q + 1] = pd.data[p + 1] * a + 30 * (1 - a); o[q + 2] = pd.data[p + 2] * a + 30 * (1 - a); o[q + 3] = 255; }
            cx.putImageData(im, 0, 0); return cv.toDataURL('image/jpeg', 0.82);
        } catch (e) { return null; }
    }
    // a picture of what was found: numbers magenta, sponsors / logos cyan, stripes yellow
    function overlay(size) {
        try {
            var pd = paintData(); if (!_cache || !pd) return null; var W = pd.width, H = pd.height, n = Math.max(256, Math.min(900, size || 640)), cv = document.createElement('canvas'); cv.width = cv.height = n;
            var cx = cv.getContext('2d'), im = cx.createImageData(n, n), o = im.data, x, y, col = { numbers: [255, 0, 220], sponsors: [0, 215, 255], stripes: [255, 225, 0] };
            for (y = 0; y < n; y++) for (x = 0; x < n; x++) {
                var sx = Math.min(W - 1, (x * W / n) | 0), sy = Math.min(H - 1, (y * H / n) | 0), s = (sy * W + sx), p = s * 4, q = (y * n + x) * 4, r = pd.data[p], g = pd.data[p + 1], b = pd.data[p + 2], a = pd.data[p + 3] / 255;
                r = r * a + 30 * (1 - a); g = g * a + 30 * (1 - a); b = b * a + 30 * (1 - a);
                ['sponsors', 'stripes', 'numbers'].forEach(function (k) { var mk = (_cache.taught && _cache.taught[k]) || _cache.masks[k]; if (mk && mk[s]) { var c = col[k]; r = r * 0.3 + c[0] * 0.7; g = g * 0.3 + c[1] * 0.7; b = b * 0.3 + c[2] * 0.7; } });
                o[q] = r; o[q + 1] = g; o[q + 2] = b; o[q + 3] = 255;
            }
            cx.putImageData(im, 0, 0); return cv.toDataURL('image/jpeg', 0.82);
        } catch (e) { return null; }
    }
    // the flat paint with a 10 % ruler (and, optionally, the app's own guess tinted): what an AI that can SEE reads boxes from (x along the top, y down the left, 0..1)
    function sheet(size, finds, region) {
        try {
            var pd = paintData(); if (!pd) return null; var W = pd.width, H = pd.height, n = Math.max(384, Math.min(1400, size || 1000));
            var rg = (region && region.length >= 4) ? [+region[0], +region[1], +region[2], +region[3]] : [0, 0, 1, 1];
            if (rg.some(function (q) { return isNaN(q); })) rg = [0, 0, 1, 1];
            if (Math.max.apply(null, rg) > 1.0001) rg = rg.map(function (q) { return q / 100; });
            rg = [Math.max(0, Math.min(rg[0], rg[2])), Math.max(0, Math.min(rg[1], rg[3])), Math.min(1, Math.max(rg[0], rg[2])), Math.min(1, Math.max(rg[1], rg[3]))];
            if (rg[2] - rg[0] < 0.02 || rg[3] - rg[1] < 0.02) rg = [0, 0, 1, 1];
            var only = (finds && typeof finds === 'object') ? finds.kind : null, cand = (finds && typeof finds === 'object' && finds.candidates) || [], tint = null;
            if (only && _cache) { var mk0 = (_cache.taught && _cache.taught[only]) || _cache.masks[only], sr = 0, sg = 0, sb = 0, sn = 0; if (mk0) for (var q0 = 0; q0 < mk0.length; q0 += 7) if (mk0[q0]) { sr += pd.data[q0 * 4]; sg += pd.data[q0 * 4 + 1]; sb += pd.data[q0 * 4 + 2]; sn++; }
                if (sn) { var mc = [sr / sn, sg / sn, sb / sn], best = -1; [[255, 0, 220], [0, 215, 255], [60, 255, 60], [255, 120, 0]].forEach(function (c) { var dd = Math.max(Math.abs(c[0] - mc[0]), Math.abs(c[1] - mc[1]), Math.abs(c[2] - mc[2])); if (dd > best) { best = dd; tint = c; } }); } }          // WP5: {kind, candidates} tints only that kind and draws the candidates as dashed boxes
            var rw = rg[2] - rg[0], rh = rg[3] - rg[1], nw = rw >= rh ? n : Math.max(64, Math.round(n * rw / rh)), nh = rw >= rh ? Math.max(64, Math.round(n * rh / rw)) : n;
            var cv = document.createElement('canvas'); cv.width = nw; cv.height = nh;
            var cx = cv.getContext('2d'), im = cx.createImageData(nw, nh), o = im.data, x, y, col = { numbers: [255, 0, 220], sponsors: [0, 215, 255], stripes: [255, 225, 0] };
            for (y = 0; y < nh; y++) for (x = 0; x < nw; x++) {
                var sx = Math.min(W - 1, ((rg[0] + (x + 0.5) / nw * rw) * W) | 0), sy = Math.min(H - 1, ((rg[1] + (y + 0.5) / nh * rh) * H) | 0), s = (sy * W + sx), p = s * 4, q = (y * nw + x) * 4, a = pd.data[p + 3] / 255, r = pd.data[p] * a + 30 * (1 - a), g = pd.data[p + 1] * a + 30 * (1 - a), b = pd.data[p + 2] * a + 30 * (1 - a);
                if (finds && _cache) ['sponsors', 'stripes', 'numbers'].forEach(function (k) { if (only && k !== only) return; var mk = (_cache.taught && _cache.taught[k]) || _cache.masks[k]; if (mk && mk[s]) { var c = (only && tint) || col[k]; r = r * 0.3 + c[0] * 0.7; g = g * 0.3 + c[1] * 0.7; b = b * 0.3 + c[2] * 0.7; } });
                o[q] = r; o[q + 1] = g; o[q + 2] = b; o[q + 3] = 255;
            }
            cx.putImageData(im, 0, 0); var fs = Math.max(11, Math.round(Math.max(nw, nh) / 55)); cx.lineWidth = 1; cx.font = 'bold ' + fs + 'px sans-serif'; cx.textBaseline = 'top';
            // ruler lines in WHOLE-SHEET fractions (a zoom keeps the same numbers): 0.1 steps for the whole sheet, finer as the view gets smaller
            var span = Math.max(rw, rh), step = span > 0.5 ? 0.1 : (span > 0.25 ? 0.05 : (span > 0.12 ? 0.02 : 0.01)), dec = step >= 0.1 ? 1 : 2, v, px, lab, tw = fs * (dec + 2.2) * 0.62 + 4;
            for (v = Math.ceil(rg[0] / step - 1e-9) * step; v < rg[2] - 1e-9; v += step) {
                px = Math.round((v - rg[0]) / rw * nw) + 0.5; if (px < 3 || px > nw - 3) continue; lab = (Math.round(v * 1000) / 1000).toFixed(dec);
                cx.strokeStyle = 'rgba(0,0,0,0.55)'; cx.beginPath(); cx.moveTo(px, 0); cx.lineTo(px, nh); cx.stroke();
                cx.strokeStyle = 'rgba(255,255,255,0.40)'; cx.beginPath(); cx.moveTo(px + 1, 0); cx.lineTo(px + 1, nh); cx.stroke();
                cx.fillStyle = 'rgba(0,0,0,0.72)'; cx.fillRect(px + 2, 0, tw, fs + 3); cx.fillRect(px + 2, nh - fs - 3, tw, fs + 3);
                cx.fillStyle = '#ffe680'; cx.fillText(lab, px + 3, 1); cx.fillText(lab, px + 3, nh - fs - 2);
            }
            for (v = Math.ceil(rg[1] / step - 1e-9) * step; v < rg[3] - 1e-9; v += step) {
                px = Math.round((v - rg[1]) / rh * nh) + 0.5; if (px < 3 || px > nh - 3) continue; lab = (Math.round(v * 1000) / 1000).toFixed(dec);
                cx.strokeStyle = 'rgba(0,0,0,0.55)'; cx.beginPath(); cx.moveTo(0, px); cx.lineTo(nw, px); cx.stroke();
                cx.strokeStyle = 'rgba(255,255,255,0.40)'; cx.beginPath(); cx.moveTo(0, px + 1); cx.lineTo(nw, px + 1); cx.stroke();
                cx.fillStyle = 'rgba(0,0,0,0.72)'; cx.fillRect(0, px + 2, tw, fs + 3); cx.fillRect(nw - tw, px + 2, tw, fs + 3);
                cx.fillStyle = '#ffe680'; cx.fillText(lab, 1, px + 3); cx.fillText(lab, nw - tw + 1, px + 3);
            }
            if (cand.length) { cx.save(); cx.setLineDash([7, 5]); cx.lineWidth = 2; cx.strokeStyle = '#33ff77'; cand.forEach(function (c) { var b = c.box || c; if (!b || b.length < 4) return; cx.strokeRect((b[0] - rg[0]) / rw * nw, (b[1] - rg[1]) / rh * nh, (b[2] - b[0]) / rw * nw, (b[3] - b[1]) / rh * nh); }); cx.restore(); }
            return cv.toDataURL('image/jpeg', 0.88);
        } catch (e) { return null; }
    }
    function ccGlyphs(d, W, x0, y0, x1, y1, m) {
        var bw = x1 - x0, bh = y1 - y0; if (bw < 6 || bh < 6) return null;
        var key = new Int32Array(bw * bh), seen = new Uint8Array(bw * bh), x, y, i, o;
        for (y = 0; y < bh; y++) for (x = 0; x < bw; x++) { o = ((y0 + y) * 1 * W + x0 + x) * 4; key[y * bw + x] = d[o + 3] < 128 ? -1 : (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3); }
        var stack = [], comps = [], touchArea = {};
        for (i = 0; i < bw * bh; i++) {
            if (seen[i] || key[i] < 0) continue;
            var k = key[i], list = [], touch = false; stack.length = 0; stack.push(i); seen[i] = 1;
            while (stack.length) {
                var c = stack.pop(), cx = c % bw, cy = (c / bw) | 0; list.push(c);
                if (cx < 2 || cy < 2 || cx >= bw - 2 || cy >= bh - 2) touch = true;
                if (cx > 0 && !seen[c - 1] && key[c - 1] === k) { seen[c - 1] = 1; stack.push(c - 1); }
                if (cx < bw - 1 && !seen[c + 1] && key[c + 1] === k) { seen[c + 1] = 1; stack.push(c + 1); }
                if (cy > 0 && !seen[c - bw] && key[c - bw] === k) { seen[c - bw] = 1; stack.push(c - bw); }
                if (cy < bh - 1 && !seen[c + bw] && key[c + bw] === k) { seen[c + bw] = 1; stack.push(c + bw); }
            }
            if (touch) touchArea[k] = (touchArea[k] || 0) + list.length;
            else if (list.length >= 24) comps.push({ k: k, list: list });
        }
        var tk = Object.keys(touchArea), tmax = 0; tk.forEach(function (q) { if (touchArea[q] > tmax) tmax = touchArea[q]; });
        var bgc = tk.filter(function (q) { return touchArea[q] >= tmax * 0.4; }).map(function (q) { return [((+q >> 10) << 3) + 4, (((+q >> 5) & 31) << 3) + 4, ((+q & 31) << 3) + 4]; });
        comps = comps.filter(function (cp) { var q = cp.k, r0 = ((q >> 10) << 3) + 4, g0 = (((q >> 5) & 31) << 3) + 4, b0 = ((q & 31) << 3) + 4; return !bgc.some(function (c) { return Math.abs(c[0] - r0) < 30 && Math.abs(c[1] - g0) < 30 && Math.abs(c[2] - b0) < 30; }); });
        if (!comps.length) return null;
        var inM = new Uint8Array(bw * bh), px = 0, sums = [];
        comps.forEach(function (cp) {
            var r = 0, g = 0, b = 0; cp.list.forEach(function (c) { inM[c] = 1; var oo = ((y0 + ((c / bw) | 0)) * W + x0 + (c % bw)) * 4; r += d[oo]; g += d[oo + 1]; b += d[oo + 2]; });
            sums.push({ n: cp.list.length, r: r / cp.list.length, g: g / cp.list.length, b: b / cp.list.length });
        });
        var add = [];                                              // anti-aliased rims: a pixel next to the glyph that is close to its neighbour joins it
        for (y = 1; y < bh - 1; y++) for (x = 1; x < bw - 1; x++) {
            i = y * bw + x; if (inM[i] || key[i] < 0) continue; o = ((y0 + y) * W + x0 + x) * 4;
            var nb = inM[i - 1] ? i - 1 : (inM[i + 1] ? i + 1 : (inM[i - bw] ? i - bw : (inM[i + bw] ? i + bw : -1))); if (nb < 0) continue;
            var on = ((y0 + ((nb / bw) | 0)) * W + x0 + (nb % bw)) * 4;
            if (Math.max(Math.abs(d[o] - d[on]), Math.abs(d[o + 1] - d[on + 1]), Math.abs(d[o + 2] - d[on + 2])) <= 48) add.push(i);
        }
        add.forEach(function (c) { inM[c] = 1; });
        for (i = 0; i < bw * bh; i++) if (inM[i]) { m[(y0 + ((i / bw) | 0)) * W + x0 + (i % bw)] = 255; px++; }
        sums.sort(function (a, b) { return b.n - a.n; });
        var cols = []; sums.forEach(function (sm) { var near = cols.filter(function (q) { return Math.abs(q.r - sm.r) < 30 && Math.abs(q.g - sm.g) < 30 && Math.abs(q.b - sm.b) < 30; })[0]; if (near) near.n += sm.n; else if (cols.length < 4) cols.push({ r: sm.r, g: sm.g, b: sm.b, n: sm.n }); });
        return { px: px, rgb: cols.map(function (q) { return [Math.round(q.r) - 4, Math.round(q.g) - 4, Math.round(q.b) - 4]; }) };
    }
    // ------------------------------------------------------------------ WP2 (2026-10-03): GLYPH = everything inside the box that is NOT the paint around it
    // The blind test (30 unseen paints, docs/handoff_reports/WP1_blind_numbers.md) showed the exact-colour flood (ccGlyphs) keeps ONE colour region per box: outlined / plaid /
    // gradient / shaded digits lost their outline or fill (B04 0.13, B11 0.05, B25 0.13) and gradient backgrounds left specks marked as glyph (B07 precision 0.46).
    // segBox: background = the colours of the RING just outside the box (every colour really there: body + stripe + gradient), glyph = the connected not-background art lying
    // inside the box (outline + fill + highlights together), small holes (texture, rivets) filled, counters (big enclosed background) left out.  Design + replay numbers:
    // docs/handoff_reports/WP2_segmentation.md.  Pure (RGBA in, mask out): the AI boxes and the buyer's drawn box go through the SAME function.
    var VERSION = 'wp5-2026-10-03d';
    var _segOpts = {};          // the node lab (pw/wp2_lab.js) tunes through _setSegOpts; the app always runs the defaults
    function segBox(d, W, H, x0, y0, x1, y1, m, opts) {
        opts = opts || _segOpts;
        var bw = x1 - x0, bh = y1 - y0; if (bw < 6 || bh < 6) return null;
        var mg = Math.max(8, Math.round(Math.max(bw, bh) * (opts.margin || 0.06)));
        var wx0 = Math.max(0, x0 - mg), wy0 = Math.max(0, y0 - mg), wx1 = Math.min(W, x1 + mg), wy1 = Math.min(H, y1 + mg), ww = wx1 - wx0, wh = wy1 - wy0, n = ww * wh;
        var bin = new Int32Array(n), inb = new Uint8Array(n), hist = new Uint32Array(32768), bhist = new Uint32Array(32768), rn = 0, bn = 0, x, y, i, o, k;
        for (y = 0; y < wh; y++) for (x = 0; x < ww; x++) {
            i = y * ww + x; o = ((wy0 + y) * W + wx0 + x) * 4;
            var gx = wx0 + x, gy = wy0 + y, ib = (gx >= x0 && gx < x1 && gy >= y0 && gy < y1); inb[i] = ib ? 1 : 0;
            if (d[o + 3] < 128) { bin[i] = -1; continue; }
            k = (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3); bin[i] = k;
            if (!ib) { hist[k]++; rn++; } else { bhist[k]++; bn++; }
        }
        if (rn < 40) return { fallback: true, why: 'no paint around the box' };
        // 1. background colours = every bin really in the ring (>= 0.25 % of it, counted with its 26 neighbour bins) that the ring holds at least `ratio` times as densely
        //    as the box: body / stripe / gradient fill the ring as much as the box; a digit that pokes out of a tight box is only a sliver of the ring (round 2)
        var thr = (opts.ringShare || 0.0025), ratio = (opts.ratio || 0.35), bgs = new Uint8Array(32768), dr, dg, db;
        for (k = 0; k < 32768; k++) {
            if (!hist[k] && !bhist[k]) continue;
            var r5 = k >> 10, g5 = (k >> 5) & 31, b5 = k & 31, rs = 0, bs = 0;
            for (dr = -1; dr <= 1; dr++) for (dg = -1; dg <= 1; dg++) for (db = -1; db <= 1; db++) { var rr = r5 + dr, gg = g5 + dg, bb = b5 + db; if (rr >= 0 && rr < 32 && gg >= 0 && gg < 32 && bb >= 0 && bb < 32) { var q0 = rr * 1024 + gg * 32 + bb; rs += hist[q0]; bs += bhist[q0]; } }
            if (rs / rn >= thr && rs / rn >= ratio * bs / Math.max(1, bn)) bgs[k] = (rs / rn * (opts.ambK || 1.5) < bs / Math.max(1, bn)) ? 2 : 1;          // 2 = ambiguous: the box holds it more densely than the ring (round 3)
        }
        // 2. candidates = not background; 8-connected components; touching the window edge = art running out of the box
        var cand = new Uint8Array(n); for (i = 0; i < n; i++) if (bin[i] >= 0 && !bgs[bin[i]]) cand[i] = 1;
        var lab = new Int32Array(n), stack = [], comps = [], touched = 0, boxA = bw * bh, minA = Math.max(20, Math.round(boxA * 0.0002));
        for (i = 0; i < n; i++) {
            if (!cand[i] || lab[i]) continue; var id = comps.length + 1, area = 0, inside = 0, touch = false; stack.length = 0; stack.push(i); lab[i] = id;
            while (stack.length) {
                var c = stack.pop(), cx = c % ww, cy = (c / ww) | 0; area++; if (inb[c]) inside++;
                if (cx === 0 || cy === 0 || cx === ww - 1 || cy === wh - 1) touch = true;
                for (var dy = -1; dy <= 1; dy++) { var yy = cy + dy; if (yy < 0 || yy >= wh) continue; for (var dx = -1; dx <= 1; dx++) { var xx = cx + dx; if (xx < 0 || xx >= ww) continue; var q = yy * ww + xx; if (cand[q] && !lab[q]) { lab[q] = id; stack.push(q); } } }
            }
            var keep = area >= minA && inside >= area * (touch ? (opts.pokeShare || 0.6) : 0.5);          // round 2: a digit poking out of a tight box is still the digit
            if (touch && !keep && inside >= minA) touched += inside;
            comps.push(keep);
        }
        var um = new Uint8Array(n), gpx = 0;
        for (i = 0; i < n; i++) if (lab[i] && comps[lab[i] - 1]) { um[i] = 1; gpx++; }
        var amb = opts.amb === undefined ? 2 : opts.amb, ambStep = opts.ambStep || 16;
        if (amb) {
            var al = new Int32Array(n), aid = 0;
            for (i = 0; i < n; i++) {
                if (al[i] || bin[i] < 0 || bgs[bin[i]] !== 2) continue; aid++; var alist = [], ain = 0, atouch = false, nextTo = false; stack.length = 0; stack.push(i); al[i] = aid;
                while (stack.length) {
                    var c4 = stack.pop(), cx4 = c4 % ww, cy4 = (c4 / ww) | 0; alist.push(c4); if (inb[c4]) ain++;
                    if (cx4 === 0 || cy4 === 0 || cx4 === ww - 1 || cy4 === wh - 1) atouch = true;
                    for (var dy4 = -1; dy4 <= 1; dy4++) { var y4 = cy4 + dy4; if (y4 < 0 || y4 >= wh) continue; for (var dx4 = -1; dx4 <= 1; dx4++) { var x4 = cx4 + dx4; if (x4 < 0 || x4 >= ww) continue; var q4 = y4 * ww + x4; if (um[q4] === 1) nextTo = true; else if (!al[q4] && bin[q4] >= 0 && bgs[bin[q4]] === 2) { var oa = ((wy0 + cy4) * W + wx0 + cx4) * 4, ob = ((wy0 + y4) * W + wx0 + x4) * 4; if (Math.max(Math.abs(d[oa] - d[ob]), Math.abs(d[oa + 1] - d[ob + 1]), Math.abs(d[oa + 2] - d[ob + 2])) <= ambStep) { al[q4] = aid; stack.push(q4); } } } }
                }
                var okA = alist.length >= minA && (!atouch || opts.ambTouch) && ain >= alist.length * (atouch ? (opts.pokeShare || 0.6) : 0.5) && (nextTo || (amb === 2 && !atouch));          // body paint flows out of the window: an ambiguous piece touching it is body
                if (okA) for (var a5 = 0; a5 < alist.length; a5++) { um[alist[a5]] = 3; gpx++; }
            }
        }
        var share = gpx / boxA;
        if (gpx < Math.max(minA, boxA * (opts.minShare || 0.003))) return { fallback: true, why: 'low contrast: the glyph colour is the colour of the paint around it', touched: touched };
        if (share > (opts.maxShare || 0.85)) return { fallback: true, why: 'over-grab: the paint around the box does not describe the inside (gradient / busy art)', touched: touched };
        // 3. holes: small enclosed non-glyph regions (texture lines, rivets, speckle) join the glyph; big ones (counters) stay out
        var hl = new Int32Array(n), holeMax = Math.max(64, Math.min(opts.holeMax || 1500, gpx * (opts.holeShare || 0.02))), hid = 0;
        for (i = 0; i < n; i++) {
            if (um[i] || hl[i]) continue; hid++; var list = [], tch = false; stack.length = 0; stack.push(i); hl[i] = hid;
            while (stack.length) {
                var c2 = stack.pop(), cx2 = c2 % ww, cy2 = (c2 / ww) | 0; list.push(c2);
                if (cx2 === 0 || cy2 === 0 || cx2 === ww - 1 || cy2 === wh - 1) tch = true;
                if (cx2 > 0 && !um[c2 - 1] && !hl[c2 - 1]) { hl[c2 - 1] = hid; stack.push(c2 - 1); }
                if (cx2 < ww - 1 && !um[c2 + 1] && !hl[c2 + 1]) { hl[c2 + 1] = hid; stack.push(c2 + 1); }
                if (cy2 > 0 && !um[c2 - ww] && !hl[c2 - ww]) { hl[c2 - ww] = hid; stack.push(c2 - ww); }
                if (cy2 < wh - 1 && !um[c2 + ww] && !hl[c2 + ww]) { hl[c2 + ww] = hid; stack.push(c2 + ww); }
            }
            if (!tch && list.length <= holeMax) { for (var li = 0; li < list.length; li++) um[list[li]] = 2; gpx += list.length; }
        }
        // 4. write + the glyph's own colours (<= 4, most used first)
        var ch = {};
        for (i = 0; i < n; i++) if (um[i]) {
            var gi = (wy0 + ((i / ww) | 0)) * W + wx0 + (i % ww); m[gi] = 255; o = gi * 4;
            if (um[i] === 1 || um[i] === 3) { var k4 = (d[o] >> 4) * 256 + (d[o + 1] >> 4) * 16 + (d[o + 2] >> 4), e = ch[k4] || (ch[k4] = { n: 0, r: 0, g: 0, b: 0 }); e.n++; e.r += d[o]; e.g += d[o + 1]; e.b += d[o + 2]; }
        }
        var arr = Object.keys(ch).map(function (q) { var e2 = ch[q]; return { n: e2.n, r: e2.r / e2.n, g: e2.g / e2.n, b: e2.b / e2.n }; }).sort(function (a, b) { return b.n - a.n; }), cols = [];
        arr.forEach(function (sm) { var near = cols.filter(function (q) { return Math.abs(q.r - sm.r) < 36 && Math.abs(q.g - sm.g) < 36 && Math.abs(q.b - sm.b) < 36; })[0]; if (near) near.n += sm.n; else if (cols.length < 4) cols.push({ r: sm.r, g: sm.g, b: sm.b, n: sm.n }); });
        cols = cols.filter(function (q, qi) { return qi === 0 || q.n >= gpx * 0.04; });
        return { px: gpx, rgb: cols.map(function (q) { return [Math.round(q.r) - 4, Math.round(q.g) - 4, Math.round(q.b) - 4]; }), info: { pixels_selected: gpx, share_of_box_pct: Math.round(gpx / boxA * 1000) / 10, touched_rim_px: touched, low_contrast: false } };
    }
    // the glyph pixels of ONE box (AI box or the buyer's drawn box): segBox first; when it cannot tell glyph from paint, the older connected-region + rim rule (cc) or colour mode
    function glyphMask(d, W, H, x0, y0, x1, y1, cc) {
        var m = new Uint8Array(W * H), sg = segBox(d, W, H, x0, y0, x1, y1, m);
        if (sg && !sg.fallback) {
            // a same-colour stripe in the ring can make the digit's own colour "background" (ARCA roof "00" just above a yellow stripe): when the older exact-colour
            // rule (glyph pieces lying fully inside the box) finds at least twice as much, sane in size, use it (round 3c)
            var m2 = new Uint8Array(W * H), r2 = (_segOpts.noCcCheck ? null : ccGlyphs(d, W, x0, y0, x1, y1, m2)), boxA2 = Math.max(1, (x1 - x0) * (y1 - y0));
            if (r2 && r2.px >= sg.px * 2 && r2.px <= boxA2 * 0.7) return { m: m2, px: r2.px, rgb: r2.rgb, info: { pixels_selected: r2.px, share_of_box_pct: Math.round(r2.px / boxA2 * 1000) / 10, touched_rim_px: sg.info.touched_rim_px, low_contrast: true, why: 'the digit colour is also in the paint around the box (a stripe?): selected by connected region' }, how: 'connected-region' };
            return { m: m, px: sg.px, rgb: sg.rgb, info: sg.info, how: 'segment' };
        }
        if (!cc) return null;
        var r = ccGlyphs(d, W, x0, y0, x1, y1, m); if (!r) return null;
        return { m: m, px: r.px, rgb: r.rgb, info: { pixels_selected: r.px, share_of_box_pct: Math.round(r.px / Math.max(1, (x1 - x0) * (y1 - y0)) * 1000) / 10, touched_rim_px: (sg && sg.touched) || 0, low_contrast: true, why: sg ? sg.why : 'segmenter skipped' }, how: 'connected-region' };
    }
    // after marking: places elsewhere on the sheet drawn in the same glyph colours at a similar size (candidates only: the AI / buyer confirms with another mark)
    function maybeMore(d, W, H, mask, boxes, perBox) {
        try {
            var hs = new Uint32Array(4096), tot = 0, i, o, k;
            for (i = 0; i < mask.length; i += 2) if (mask[i]) { o = i * 4; hs[(d[o] >> 4) * 256 + (d[o + 1] >> 4) * 16 + (d[o + 2] >> 4)]++; tot++; }
            if (tot < 50 || !perBox.length) return [];
            var gs = new Uint8Array(4096), any = false; for (k = 0; k < 4096; k++) if (hs[k] >= tot * 0.05) { gs[k] = 1; any = true; } if (!any) return [];
            var G = 2, gw = (W / G) | 0, gh = (H / G) | 0, on = new Uint8Array(gw * gh), x, y;
            var bxp = boxes.map(function (b) { return [Math.floor((b[0] - 0.01) * gw), Math.floor((b[1] - 0.01) * gh), Math.ceil((b[2] + 0.01) * gw), Math.ceil((b[3] + 0.01) * gh)]; });
            for (y = 0; y < gh; y++) for (x = 0; x < gw; x++) { o = ((y * G) * W + x * G) * 4; if (d[o + 3] < 128) continue; if (gs[(d[o] >> 4) * 256 + (d[o + 1] >> 4) * 16 + (d[o + 2] >> 4)]) on[y * gw + x] = 1; }
            for (i = 0; i < on.length; i++) if (on[i] && mask[(((i / gw) | 0) * G) * W + (i % gw) * G]) on[i] = 0;
            for (var bi = 0; bi < bxp.length; bi++) { var b = bxp[bi]; for (y = Math.max(0, b[1]); y < Math.min(gh, b[3]); y++) for (x = Math.max(0, b[0]); x < Math.min(gw, b[2]); x++) on[y * gw + x] = 0; }
            var med = perBox.slice().sort(function (a, b2) { return a - b2; })[(perBox.length / 2) | 0] / (G * G), maxW = 0, maxH = 0, maxAsp = 1;
            boxes.forEach(function (b) { var bw2 = (b[2] - b[0]) * gw, bh2 = (b[3] - b[1]) * gh; maxW = Math.max(maxW, bw2, bh2); maxH = maxW; maxAsp = Math.max(maxAsp, bw2 / Math.max(1, bh2), bh2 / Math.max(1, bw2)); });          // digits may be rotated: compare the long side and the aspect
            var seen = new Uint8Array(gw * gh), stack = [], out = [], R = 3;
            for (i = 0; i < on.length; i++) {
                if (!on[i] || seen[i]) continue; var cnt = 0, mx0 = gw, my0 = gh, mx1 = 0, my1 = 0; stack.length = 0; stack.push(i); seen[i] = 1;
                while (stack.length) {
                    var c = stack.pop(), cx = c % gw, cy = (c / gw) | 0; cnt++; if (cx < mx0) mx0 = cx; if (cy < my0) my0 = cy; if (cx > mx1) mx1 = cx; if (cy > my1) my1 = cy;
                    for (var dy = -R; dy <= R; dy++) { var yy = cy + dy; if (yy < 0 || yy >= gh) continue; for (var dx = -R; dx <= R; dx++) { var xx = cx + dx; if (xx < 0 || xx >= gw) continue; var q = yy * gw + xx; if (on[q] && !seen[q]) { seen[q] = 1; stack.push(q); } } }
                    if (cnt > med * 6) break;
                }
                if (stack.length) { while (stack.length) { var c3 = stack.pop(); var cx3 = c3 % gw, cy3 = (c3 / gw) | 0; for (var dy3 = -R; dy3 <= R; dy3++) { var y3 = cy3 + dy3; if (y3 < 0 || y3 >= gh) continue; for (var dx3 = -R; dx3 <= R; dx3++) { var x3 = cx3 + dx3; if (x3 < 0 || x3 >= gw) continue; var q3 = y3 * gw + x3; if (on[q3] && !seen[q3]) { seen[q3] = 1; stack.push(q3); } } } } continue; }
                if (cnt < med * 0.5 || cnt > med * 2) continue;
                var cw = mx1 - mx0 + 1, chh = my1 - my0 + 1;
                if (Math.max(cw, chh) > maxW * 1.5 || Math.max(cw / chh, chh / cw) > maxAsp * 1.6) continue;          // a stripe / a long word in the glyph colour is not another number
                out.push({ d: Math.abs(Math.log(cnt / med)), box: [mx0 / gw, my0 / gh, (mx1 + 1) / gw, (my1 + 1) / gh] });
            }
            out.sort(function (a, b) { return a.d - b.d; });
            return out.slice(0, 6).map(function (q) { return [Math.max(0, q.box[0] - 0.01), Math.max(0, q.box[1] - 0.01), Math.min(1, q.box[2] + 0.01), Math.min(1, q.box[3] + 0.01)].map(function (v) { return Math.round(v * 100) / 100; }); });
        } catch (e) { return []; }
    }
    // ---------------------------------------------------------------- WP5 2026-10-03: mark_elements MODES (design: docs/handoff_reports/WP5_design.md)
    // glyph = numbers (WP2 segBox, unchanged) | colour_in_region = stripes: the box says WHERE, the colour says WHICH, the stripe is followed past the box edge under caps
    // | logo = sponsors: everything in the box that is not the paint around it. Caps are fitted on synthetic sheets only (owner decision 4: refit on the stripes blind result).
    var WP5 = { ringShare: 0.25, bgTol: 30, capBox: 0.12, capCall: 0.25, growth: 25, thick: 1.6 };
    function cdist(a, b) { return Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]), Math.abs(a[2] - b[2])); }
    function nearD(c, cols) { var b = 999; for (var i = 0; i < cols.length; i++) { var q = cdist(c, cols[i]); if (q < b) b = q; } return b; }
    function hex2rgb(h) { var m = /^#?([0-9a-f]{6})$/i.exec(String(h || '').trim()); if (!m) return null; var v = parseInt(m[1], 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; }
    function hexC(c) { return hexOf(Math.max(0, Math.min(255, c[0])), Math.max(0, Math.min(255, c[1])), Math.max(0, Math.min(255, c[2]))); }
    function clusterKeys(hist, tol, maxN) {          // 5-bit histogram {key: count} -> colour clusters (greedy by count, mean colour), biggest first
        var ks = Object.keys(hist).map(function (k) { k = +k; return { c: [((k >> 10) << 3) + 4, (((k >> 5) & 31) << 3) + 4, ((k & 31) << 3) + 4], n: hist[k] }; }).sort(function (a, b) { return b.n - a.n; }), out = [];
        ks.forEach(function (q) { for (var i = 0; i < out.length; i++) if (cdist(out[i].c0, q.c) <= tol) { var o = out[i]; o.s[0] += q.c[0] * q.n; o.s[1] += q.c[1] * q.n; o.s[2] += q.c[2] * q.n; o.n += q.n; return; } out.push({ c0: q.c, s: [q.c[0] * q.n, q.c[1] * q.n, q.c[2] * q.n], n: q.n }); });
        out.forEach(function (o) { o.c = [Math.round(o.s[0] / o.n), Math.round(o.s[1] / o.n), Math.round(o.s[2] / o.n)]; });
        return out.sort(function (a, b) { return b.n - a.n; }).slice(0, maxN || 99);
    }
    function key5(d, o) { return (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3); }
    // background = the colours of a band OUTSIDE the box (a stripe crossing the box crosses this ring only at its two ends); busy surroundings -> the colours on the box edge
    function ringBg(d, W, H, x0, y0, x1, y1) {
        var bw = Math.max(12, Math.min(40, Math.round(0.015 * W))), hist = {}, n = 0, x, y, o, k, cl, bg;
        var X0 = Math.max(0, x0 - bw), Y0 = Math.max(0, y0 - bw), X1 = Math.min(W, x1 + bw), Y1 = Math.min(H, y1 + bw);
        for (y = Y0; y < Y1; y += 2) for (x = X0; x < X1; x += 2) { if (y >= y0 && y < y1 && x >= x0 && x < x1) { x = x1 - 1; continue; } o = (y * W + x) * 4; if (d[o + 3] < 128) continue; k = key5(d, o); hist[k] = (hist[k] || 0) + 1; n++; }
        cl = clusterKeys(hist, WP5.bgTol, 12); var big = cl.filter(function (c) { return c.n >= n * WP5.ringShare; }).slice(0, 3), acc = 0; big.forEach(function (c) { acc += c.n; });
        cl.forEach(function (c) { if (big.indexOf(c) === -1 && big.length < 5 && acc < n * 0.85 && c.n >= n * 0.08) { big.push(c); acc += c.n; } });          // WP3 bmw: a textured body = several ring clusters
        if (big.length) return { cols: big.map(function (c) { return c.c; }), shares: big.map(function (c) { return c.n / Math.max(1, n); }), source: 'ring' };
        hist = {}; n = 0;
        for (y = y0; y < y1; y++) for (x = x0; x < x1; x++) { if (y - y0 >= 2 && y1 - 1 - y >= 2 && x - x0 >= 2 && x1 - 1 - x >= 2) { x = x1 - 3; continue; } o = (y * W + x) * 4; if (d[o + 3] < 128) continue; k = key5(d, o); hist[k] = (hist[k] || 0) + 1; n++; }
        cl = clusterKeys(hist, WP5.bgTol, 12); bg = cl.filter(function (c) { return c.n >= n * WP5.ringShare; }).slice(0, 3).map(function (c) { return c.c; }); if (!bg.length && cl.length) bg = [cl[0].c];
        return { cols: bg, source: 'box edge (busy surroundings)' };
    }
    // anti-alias rim: a pixel next to the selection joins when it is a blend alpha*target + (1-alpha)*background (alpha 0.15..1, within 18); it never eats a neighbour of another colour
    function blendOk(p0, p1, p2, t, b) {
        var dx = t[0] - b[0], dy = t[1] - b[1], dz = t[2] - b[2], L = dx * dx + dy * dy + dz * dz; if (L < 64) return false;
        var a = ((p0 - b[0]) * dx + (p1 - b[1]) * dy + (p2 - b[2]) * dz) / L; if (a < 0.15 || a > 0.92) return false;          // a near-solid pixel is not a blend: solid ones were left out on purpose (a pruned panel)
        return Math.max(Math.abs(p0 - b[0] - a * dx), Math.abs(p1 - b[1] - a * dy), Math.abs(p2 - b[2] - a * dz)) <= 18;
    }
    function aaRim(m, d, W, H, bb, targets, bgs, passes) {          // bb = [x0,y0,x1,y1) to scan (grows 1 px per pass); targets null = the colour of the selected neighbour
        var add = 0, X0 = bb[0], Y0 = bb[1], X1 = bb[2], Y1 = bb[3];
        for (var ps = 0; ps < passes; ps++) {
            X0 = Math.max(1, X0 - 1); Y0 = Math.max(1, Y0 - 1); X1 = Math.min(W - 1, X1 + 1); Y1 = Math.min(H - 1, Y1 + 1);
            var nw = [];
            for (var y = Y0; y < Y1; y++) for (var x = X0; x < X1; x++) {
                var i = y * W + x; if (m[i]) continue; var nb = m[i - 1] ? i - 1 : (m[i + 1] ? i + 1 : (m[i - W] ? i - W : (m[i + W] ? i + W : -1))); if (nb < 0) continue;
                var o = i * 4; if (d[o + 3] < 128) continue; var ts = targets || [[d[nb * 4], d[nb * 4 + 1], d[nb * 4 + 2]]], ok = false;
                for (var a = 0; a < ts.length && !ok; a++) for (var b = 0; b < bgs.length && !ok; b++) if (blendOk(d[o], d[o + 1], d[o + 2], ts[a], bgs[b])) ok = true;
                if (ok) nw.push(i);
            }
            for (var j = 0; j < nw.length; j++) m[nw[j]] = 255; add += nw.length; if (!nw.length) break;
        }
        return add;
    }
    // chamfer (3-4) distance to the nearest non-member, in px, over a rectangle; edgeZero: outside the rectangle counts as non-member (else it is ignored)
    function dtRect(isMem, rx0, ry0, rx1, ry1, edgeZero) {
        var w = rx1 - rx0, h = ry1 - ry0, D = new Float32Array(w * h), INF = 1e7, x, y, i, v;
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) D[y * w + x] = isMem(rx0 + x, ry0 + y) ? INF : 0;
        var E = edgeZero ? 0 : INF;
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) { i = y * w + x; v = D[i]; if (!v) continue;
            v = Math.min(v, (x > 0 ? D[i - 1] : E) + 3, (y > 0 ? D[i - w] : E) + 3, (x > 0 && y > 0 ? D[i - w - 1] : E) + 4, (x < w - 1 && y > 0 ? D[i - w + 1] : E) + 4); D[i] = v; }
        for (y = h - 1; y >= 0; y--) for (x = w - 1; x >= 0; x--) { i = y * w + x; v = D[i]; if (!v) continue;
            v = Math.min(v, (x < w - 1 ? D[i + 1] : E) + 3, (y < h - 1 ? D[i + w] : E) + 3, (x < w - 1 && y < h - 1 ? D[i + w + 1] : E) + 4, (x > 0 && y < h - 1 ? D[i + w - 1] : E) + 4); D[i] = v; }
        for (i = 0; i < D.length; i++) D[i] = D[i] >= INF / 2 ? 1e5 : D[i] / 3;
        return { D: D, w: w, h: h };
    }
    function thickOf(isMem, rx0, ry0, rx1, ry1, edgeZero) {          // 2 x the 95th percentile of the distance transform over the members
        var t = dtRect(isMem, rx0, ry0, rx1, ry1, edgeZero), v = [];
        for (var y = 0; y < t.h; y++) for (var x = 0; x < t.w; x++) { var q = t.D[y * t.w + x]; if (q) v.push(q); }
        if (!v.length) return 0; v.sort(function (a, b) { return a - b; }); return 2 * v[Math.min(v.length - 1, Math.floor(v.length * 0.95))];
    }
    // colour_in_region (stripes)
    function colourRegion(d, W, H, x0, y0, x1, y1, opts) {
        opts = opts || {}; var bg = ringBg(d, W, H, x0, y0, x1, y1), bgs = bg.cols, x, y, o, i, k, hist = {}, st = (x1 - x0) * (y1 - y0) > 200000 ? 2 : 1;
        var spread = /^(box|sheet)$/.test(String(opts.spread || '')) ? opts.spread : 'connected';
        for (y = y0; y < y1; y += st) for (x = x0; x < x1; x += st) { o = (y * W + x) * 4; if (d[o + 3] < 128) continue; k = key5(d, o); hist[k] = (hist[k] || 0) + 1; }
        var cl = clusterKeys(hist, 30, 12), fg = cl.filter(function (c) { return nearD(c.c, bgs) > WP5.bgTol; }), want = [], src = 'auto', given = opts.colour, i2;
        if (bg.shares && bgs.length > 1) {          // WP3 silvercrown: the stripe filled most of the ring, so it was "background" and only a hairline was taken
            var totB = 0; cl.forEach(function (c) { totB += c.n; });
            var keepB = bgs.filter(function (b, q) { var inS = 0; cl.forEach(function (c) { if (cdist(c.c, b) <= WP5.bgTol) inS += c.n; }); inS /= Math.max(1, totB); return !(inS >= 0.15 && inS >= 1.5 * bg.shares[q]); });
            if (keepB.length && keepB.length < bgs.length) { bgs = keepB; fg = cl.filter(function (c) { return nearD(c.c, bgs) > WP5.bgTol; }); }
        }
        function isBlend(c, t, b) { var dx = t[0] - b[0], dy = t[1] - b[1], dz = t[2] - b[2], L = dx * dx + dy * dy + dz * dz; if (L < 64) return false; var a = ((c[0] - b[0]) * dx + (c[1] - b[1]) * dy + (c[2] - b[2]) * dz) / L; if (a < 0.15 || a > 0.85) return false; return Math.max(Math.abs(c[0] - b[0] - a * dx), Math.abs(c[1] - b[1] - a * dy), Math.abs(c[2] - b[2] - a * dz)) <= 20; }
        // a fringe cluster is a blend of another cluster and the body AND lies on the edge (>= 70 % of its pixels touch body paint); a metallic band in the middle of a stripe does not
        var edgeFrac = fg.map(function () { return [0, 0]; }), xx2, yy2;
        if (fg.length > 1) for (yy2 = y0 + 1; yy2 < y1 - 1; yy2 += st) for (xx2 = x0 + 1; xx2 < x1 - 1; xx2 += st) {
            var o2 = (yy2 * W + xx2) * 4, pc = [d[o2], d[o2 + 1], d[o2 + 2]], bi2 = -1, bd2 = 31; for (var f2 = 0; f2 < fg.length; f2++) { var dq = cdist(pc, fg[f2].c); if (dq < bd2) { bd2 = dq; bi2 = f2; } } if (bi2 < 0) continue;
            edgeFrac[bi2][1]++; var tch = false; [-4, 4, -4 * W, 4 * W, -8, 8, -8 * W, 8 * W, -12, 12, -12 * W, 12 * W].forEach(function (dd) { var on = o2 + dd; if (on < 0 || on >= d.length) return; if (!tch && nearD([d[on], d[on + 1], d[on + 2]], bgs) <= WP5.bgTol) tch = true; }); if (tch) edgeFrac[bi2][0]++;
        }
        var core = fg.filter(function (c, ci) { var ef = edgeFrac[ci][1] ? edgeFrac[ci][0] / edgeFrac[ci][1] : 0; return !(ef >= 0.7 && fg.some(function (t) { return t !== c && t.n >= c.n * 0.1 && bgs.some(function (bb) { return isBlend(c.c, t.c, bb); }); })); });          // WP3 formulavee: thin streaks are mostly anti-alias fringe; the fringe is a blend of the core and the body
        if (typeof given === 'string' && given.indexOf(',') !== -1) given = given.split(',');
        var same = 'that colour is the paint all around the box: a stripe the same colour as the body cannot be separated; box the stripe more tightly or name its other colour';
        if (given && given !== 'auto' && !(Array.isArray(given) && (!given.length || given[0] === 'auto'))) {
            src = 'given'; var list = [].concat(given).slice(0, 3);
            for (i2 = 0; i2 < list.length; i2++) {
                var c = hex2rgb(list[i2]); if (!c) return { fail: 'colour "' + String(list[i2]).slice(0, 20) + '" is not #rrggbb: give the hex you read off the picture, or "auto"' };
                if (nearD(c, bgs) <= WP5.bgTol) {          // a two-tone surrounding (WP3 silvercrown: yellow swoosh on navy): the AI NAMED one of them, so it is the stripe, not background
                    var bgKeep = bgs.filter(function (b) { return cdist(b, c) > WP5.bgTol; });
                    if (!bgKeep.length) return { fail: same };
                    bgs = bgKeep; fg = cl.filter(function (q) { return nearD(q.c, bgs) > WP5.bgTol; }); src = 'given (also in the paint around the box)';
                }
                var best = null; cl.forEach(function (q) { var dd = cdist(q.c, c); if (!best || dd < best.d) best = { d: dd, c: q.c }; });
                if (!best || best.d > 40) return { fail: 'colour ' + hexC(c) + ' is not in this box (nearest here: ' + (best ? hexC(best.c) : 'nothing') + ')' };
                want.push(best.c);
            }
        } else {
            // WP3 formulavee: a field of red streaks on white - the ring is red AND white, everything else in the box is their anti-alias blend:
            // the stripe is the minority ring colour (the white body holds the bigger ring share), not the pink fringe
            if (bg.shares && bgs.length >= 2 && (!fg.length || fg.every(function (c) { return bgs.some(function (b1) { return bgs.some(function (b2) { return b1 !== b2 && isBlend(c.c, b1, b2); }); }); }))) {
                var minor = -1, shr = function (q) { var ix = bg.cols.indexOf(bgs[q]); return ix >= 0 ? bg.shares[ix] : 1; }; for (i2 = 0; i2 < bgs.length; i2++) if (minor < 0 || shr(i2) < shr(minor)) minor = i2;
                if (minor >= 0) { var mc = bgs[minor]; bgs = bgs.filter(function (b) { return b !== mc; }); fg = cl.filter(function (q) { return nearD(q.c, bgs) > WP5.bgTol; }); var mcl = fg.filter(function (q) { return cdist(q.c, mc) <= WP5.bgTol; }); core = mcl.length ? mcl : fg; src = 'auto (the minority colour of a two-tone surrounding)'; }
            }
            if (!fg.length) return { fail: same };
            want.push((core.length ? core : fg)[0].c);
            for (var grow = true; grow && want.length < 3;) { grow = false; for (i2 = 0; i2 < fg.length && want.length < 3; i2++) { var fc = fg[i2].c; if (core.length && core.indexOf(fg[i2]) === -1) continue; if (fg[i2].n >= (core.length ? core : fg)[0].n * 0.3 && want.indexOf(fc) === -1 && want.some(function (w) { return cdist(w, fc) <= 70; })) { want.push(fc); grow = true; } } }          // metallic / shaded stripe = several close clusters
        }
        var other = fg.filter(function (q) { return !want.some(function (w) { return cdist(w, q.c) <= 30; }); }).slice(0, 4).map(function (q) { return hexC(q.c); });
        // adaptive tolerance per target: 1.5 x p90 of its own pixels' distance, 20..56 (or the caller's 8..80)
        var T = want.map(function (w) {
            if (opts.tolerance) return Math.max(8, Math.min(80, +opts.tolerance || 30));
            var ds = []; for (y = y0; y < y1; y += st) for (x = x0; x < x1; x += st) { o = (y * W + x) * 4; if (d[o + 3] < 128) continue; var q = Math.max(Math.abs(d[o] - w[0]), Math.abs(d[o + 1] - w[1]), Math.abs(d[o + 2] - w[2])); if (q <= 30) ds.push(q); }
            ds.sort(function (a, b) { return a - b; }); var p90 = ds.length ? ds[Math.floor(ds.length * 0.9)] : 0; return Math.max(20, Math.min(56, 1.5 * p90));
        });
        var nW = want.length, nB = bgs.length;
        function mem(i) { var o = i * 4; if (d[o + 3] < 128) return false; var r0 = d[o], g0 = d[o + 1], b0 = d[o + 2], nb = 999, t, q, c;
            for (t = 0; t < nB; t++) { c = bgs[t]; q = Math.max(r0 > c[0] ? r0 - c[0] : c[0] - r0, g0 > c[1] ? g0 - c[1] : c[1] - g0, b0 > c[2] ? b0 - c[2] : c[2] - b0); if (q < nb) nb = q; }
            for (t = 0; t < nW; t++) { c = want[t]; q = Math.max(r0 > c[0] ? r0 - c[0] : c[0] - r0, g0 > c[1] ? g0 - c[1] : c[1] - g0, b0 > c[2] ? b0 - c[2] : c[2] - b0); if (q <= T[t] && q < nb) return true; } return false; }
        var inBox = function (q) { var qx = q % W, qy = (q / W) | 0; return qx >= x0 && qx < x1 && qy >= y0 && qy < y1; };
        var m = new Uint8Array(W * H), seeds = [], inPx = 0;
        for (y = y0; y < y1; y++) for (x = x0; x < x1; x++) { i = y * W + x; if (mem(i)) { m[i] = 255; seeds.push(i); inPx++; } }
        if (inPx < 12) return { fail: 'almost nothing of that colour in this box (' + inPx + ' px): check the box against the picture' };
        var vx0 = x0, vy0 = y0, vx1 = x1 - 1, vy1 = y1 - 1;
        var capped = false, why = null, outPx = 0, budget = Math.max(inPx, Math.floor(opts.budget || WP5.capBox * W * H)), tIn = 0, sheetAdd = [];
        if (spread !== 'box') {
            var vis = new Uint8Array(W * H), stack = seeds.slice(), head = 0, cnt = inPx, over = false; for (i = 0; i < seeds.length; i++) vis[seeds[i]] = 1;
            while (head < stack.length && !over) {          // breadth-first: a budget cut stops evenly around the box, never half-way along one side
                var c0 = stack[head++], cx = c0 % W, cy = (c0 / W) | 0; if (cx < vx0) vx0 = cx; if (cx > vx1) vx1 = cx; if (cy < vy0) vy0 = cy; if (cy > vy1) vy1 = cy;
                for (var dy = -1; dy <= 1 && !over; dy++) { var yy = cy + dy; if (yy < 0 || yy >= H) continue; for (var dx = -1; dx <= 1; dx++) { var xx = cx + dx; if (xx < 0 || xx >= W) continue; var q = yy * W + xx; if (vis[q]) continue; vis[q] = 2; if (!mem(q)) continue; vis[q] = 1; stack.push(q); if (xx < vx0) vx0 = xx; if (xx > vx1) vx1 = xx; if (yy < vy0) vy0 = yy; if (yy > vy1) vy1 = yy; if (!inBox(q)) { cnt++; if (cnt > budget) { over = true; break; } } } }
            }
            {          // a flood cut by the share budget still goes through the thickness guard: when it reached a same-colour panel, the stripe up to it is kept
                tIn = thickOf(function (px, py) { return vis[py * W + px] === 1; }, x0, y0, x1, y1, false);
                // outside pieces (8-connected); a piece much thicker than the stripe inside the box is a panel: keep only its thin part (the stripe running up to the panel)
                var lab = new Int32Array(0), seen = new Uint8Array(W * H), keep = new Uint8Array(W * H), pieces = 0, pruned = false;
                for (i = 0; i < seeds.length; i++) keep[seeds[i]] = 1;
                for (var yb = vy0; yb <= vy1; yb++) for (var xb = vx0; xb <= vx1; xb++) {
                    var s0 = yb * W + xb; if (vis[s0] !== 1 || seen[s0] || (xb >= x0 && xb < x1 && yb >= y0 && yb < y1)) continue;
                    var pix = [], st2 = [s0], bx0 = xb, by0 = yb, bx1 = xb, by1 = yb; seen[s0] = 1;
                    while (st2.length) { var c1 = st2.pop(), px1 = c1 % W, py1 = (c1 / W) | 0; pix.push(c1); if (px1 < bx0) bx0 = px1; if (px1 > bx1) bx1 = px1; if (py1 < by0) by0 = py1; if (py1 > by1) by1 = py1;
                        for (var ey = -1; ey <= 1; ey++) for (var ex = -1; ex <= 1; ex++) { var xq = px1 + ex, yq = py1 + ey; if (xq < 0 || yq < 0 || xq >= W || yq >= H) continue; var q2 = yq * W + xq; if (vis[q2] === 1 && !seen[q2] && !(xq >= x0 && xq < x1 && yq >= y0 && yq < y1)) { seen[q2] = 1; st2.push(q2); } } }
                    pieces++; var memP = function (px, py) { return seen[py * W + px] === 1 && vis[py * W + px] === 1 && !(px >= x0 && px < x1 && py >= y0 && py < y1); };
                    var tP = thickOf(memP, bx0, by0, bx1 + 1, by1 + 1, true);
                    if (!tIn || tP <= WP5.thick * Math.max(tIn, 2)) { for (k = 0; k < pix.length; k++) keep[pix[k]] = 1; continue; }
                    // thick part = covered by disks of radius r that fit in the piece (an opening); remove it (+2 px) and keep the rest
                    pruned = true; var r = WP5.thick * Math.max(tIn, 2) / 2, t1 = dtRect(memP, bx0, by0, bx1 + 1, by1 + 1, true), w1 = t1.w;
                    var t2 = dtRect(function (px, py) { return !(t1.D[(py - by0) * w1 + (px - bx0)] >= r); }, bx0, by0, bx1 + 1, by1 + 1, false);
                    for (k = 0; k < pix.length; k++) { var pxk = pix[k] % W, pyk = (pix[k] / W) | 0; if (t2.D[(pyk - by0) * w1 + (pxk - bx0)] > r + 2) keep[pix[k]] = 1; }
                }
                // final selection = what stays connected to the in-box seeds
                var fin = new Uint8Array(W * H), st3 = seeds.slice(); for (i = 0; i < seeds.length; i++) fin[seeds[i]] = 1;
                while (st3.length) { var c3 = st3.pop(), x3 = c3 % W, y3 = (c3 / W) | 0; for (var fy = -1; fy <= 1; fy++) for (var fx = -1; fx <= 1; fx++) { var xr = x3 + fx, yr = y3 + fy; if (xr < 0 || yr < 0 || xr >= W || yr >= H) continue; var q3 = yr * W + xr; if (keep[q3] && !fin[q3]) { fin[q3] = 1; st3.push(q3); } } }
                for (var yf = vy0; yf <= vy1; yf++) for (var xf = vx0; xf <= vx1; xf++) { i = yf * W + xf; if (fin[i] && !m[i]) { m[i] = 255; outPx++; } }
                if (pruned) { capped = true; why = 'the colour runs into a large same-colour area (probably body paint) outside the box: kept the stripe up to it, not the area; add boxes along the rest of the stripe'; }
                else if (over) { for (var yo = vy0; yo <= vy1; yo++) for (var xo = vx0; xo <= vx1; xo++) { i = yo * W + xo; if (m[i] && !inBox(i)) m[i] = 0; } outPx = 0; capped = true; why = 'the colour runs on over more than ' + Math.round(WP5.capBox * 100) + '% of the sheet: kept only the part inside the box; add boxes along the rest of the stripe'; }
                if (outPx && outPx > WP5.growth * inPx) { for (var yg = vy0; yg <= vy1; yg++) for (var xg = vx0; xg <= vx1; xg++) { i = yg * W + xg; if (m[i] && !inBox(i)) m[i] = 0; } outPx = 0; capped = true; why = 'the colour grew more than ' + WP5.growth + 'x outside the box: kept only the part inside the box; add boxes along the rest of the stripe'; }
            }
        }
        if (!tIn) tIn = thickOf(function (px, py) { return m[py * W + px] === 255; }, x0, y0, x1, y1, false);
        // selection bbox for the rim
        var sx0 = W, sy0 = H, sx1 = 0, sy1 = 0, SY0 = spread === 'box' ? y0 : vy0, SY1 = spread === 'box' ? y1 - 1 : vy1, SX0 = spread === 'box' ? x0 : vx0, SX1 = spread === 'box' ? x1 - 1 : vx1; for (y = SY0; y <= SY1; y++) { var row = y * W, hit = false; for (x = SX0; x <= SX1; x++) if (m[row + x]) { hit = true; if (x < sx0) sx0 = x; if (x > sx1) sx1 = x; } if (hit) { if (y < sy0) sy0 = y; sy1 = y; } }
        aaRim(m, d, W, H, [sx0, sy0, sx1 + 1, sy1 + 1], want, bgs, 3);          // 3 px: soft streaks (WP3 formulavee) carry a wide fringe; the blend test never takes body paint
        if (spread === 'box') for (y = Math.max(0, sy0 - 3); y < Math.min(H, sy1 + 4); y++) for (x = Math.max(0, sx0 - 3); x < Math.min(W, sx1 + 4); x++) if (m[y * W + x] && !(x >= x0 && x < x1 && y >= y0 && y < y1)) m[y * W + x] = 0;
        var px = 0, inP = 0, touched = false; for (y = Math.max(0, sy0 - 3); y < Math.min(H, sy1 + 4); y++) for (x = Math.max(0, sx0 - 3); x < Math.min(W, sx1 + 4); x++) if (m[y * W + x]) { px++; if (x >= x0 && x < x1 && y >= y0 && y < y1) { inP++; if (x - x0 < 2 || x1 - 1 - x < 2 || y - y0 < 2 || y1 - 1 - y < 2) touched = true; } }
        return { m: m, px: px, rgb: want, T: T, thick: tIn, spread: spread, info: { mode: 'colour_in_region', pixels_selected: px, share_of_box_pct: Math.round(inP / Math.max(1, (x1 - x0) * (y1 - y0)) * 1000) / 10, share_of_sheet_pct: Math.round(px / (W * H) * 10000) / 100, outside_box_px: px - inP, touched_edge: touched, capped: capped, cap_reason: why, colour_source: src, colour_used: want.map(hexC), other_colours_in_box: other.length ? other : undefined, background: bgs.map(hexC), background_source: bg.source === 'ring' ? undefined : bg.source, spread: spread } };
    }
    // logo (sponsors): every in-box pixel that is not the ring background; a hole of body colour stays out, a hole of any other colour is the decal's own plate
    function logoRegion(d, W, H, x0, y0, x1, y1, opts) {
        opts = opts || {}; var bg = ringBg(d, W, H, x0, y0, x1, y1), bgs = bg.cols, bw = x1 - x0, bh = y1 - y0, n = bw * bh, s = new Uint8Array(n), x, y, i, o, k, ph = {}, pn = 0, plate = null, plateShare = 0;
        for (y = 0; y < bh; y++) for (x = 0; x < bw; x++) { o = ((y0 + y) * W + x0 + x) * 4; if (d[o + 3] < 128) continue; if (nearD([d[o], d[o + 1], d[o + 2]], bgs) > WP5.bgTol) { s[y * bw + x] = 1; if (!(x & 1) && !(y & 1)) { k = key5(d, o); ph[k] = (ph[k] || 0) + 1; pn++; } } }
        var pcl = clusterKeys(ph, 30, 6); if (pcl.length > 1 && pcl[0].n >= pn * 0.35) { plate = pcl[0].c; plateShare = pcl[0].n / Math.max(1, pn); }          // the decal's own plate / tile (WP3: HUDCO, Rubbermaid, rt2000 band)
        if (opts.lettering && plate) { bgs = bgs.concat([plate]); for (y = 0; y < bh; y++) for (x = 0; x < bw; x++) { if (!s[y * bw + x]) continue; o = ((y0 + y) * W + x0 + x) * 4; if (cdist([d[o], d[o + 1], d[o + 2]], plate) <= WP5.bgTol) s[y * bw + x] = 0; } }
        function morph(a, dil) {          // 5x5 square (2 px), separable; outside the box counts as set for the erosion (no shrink at the box edge)
            var t = new Uint8Array(n), u = new Uint8Array(n), xx, yy, q, v;
            for (yy = 0; yy < bh; yy++) for (xx = 0; xx < bw; xx++) { v = dil ? 0 : 1; for (q = -2; q <= 2; q++) { var xq = xx + q, z = (xq < 0 || xq >= bw) ? (dil ? 0 : 1) : a[yy * bw + xq]; if (dil ? z : !z) { v = dil ? 1 : 0; break; } } t[yy * bw + xx] = v; }
            for (yy = 0; yy < bh; yy++) for (xx = 0; xx < bw; xx++) { v = dil ? 0 : 1; for (q = -2; q <= 2; q++) { var yq = yy + q, z2 = (yq < 0 || yq >= bh) ? (dil ? 0 : 1) : t[yq * bw + xx]; if (dil ? z2 : !z2) { v = dil ? 1 : 0; break; } } u[yy * bw + xx] = v; }
            return u;
        }
        var c = morph(morph(s, true), false); for (i = 0; i < n; i++) if (s[i]) c[i] = 1;
        // specks < 24 px out
        var seen = new Uint8Array(n), st = [], comp = [];
        for (i = 0; i < n; i++) { if (!c[i] || seen[i]) continue; comp.length = 0; st.push(i); seen[i] = 1; while (st.length) { var p = st.pop(); comp.push(p); var px = p % bw, py = (p / bw) | 0; for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) { var qx = px + dx, qy = py + dy; if (qx < 0 || qy < 0 || qx >= bw || qy >= bh) continue; var qq = qy * bw + qx; if (c[qq] && !seen[qq]) { seen[qq] = 1; st.push(qq); } } } if (comp.length < 24) for (k = 0; k < comp.length; k++) c[comp[k]] = 0; }
        // holes (4-connected, not touching the box edge): body colour stays out, another colour is plate
        seen = new Uint8Array(n);
        for (i = 0; i < n; i++) { if (c[i] || seen[i]) continue; comp.length = 0; st.push(i); seen[i] = 1; var edge = false, bgN = 0;
            while (st.length) { var p2 = st.pop(); comp.push(p2); var x2 = p2 % bw, y2 = (p2 / bw) | 0; if (x2 === 0 || y2 === 0 || x2 === bw - 1 || y2 === bh - 1) edge = true; o = ((y0 + y2) * W + x0 + x2) * 4; if (d[o + 3] < 128 || nearD([d[o], d[o + 1], d[o + 2]], bgs) <= WP5.bgTol) bgN++;
                if (x2 > 0 && !c[p2 - 1] && !seen[p2 - 1]) { seen[p2 - 1] = 1; st.push(p2 - 1); } if (x2 < bw - 1 && !c[p2 + 1] && !seen[p2 + 1]) { seen[p2 + 1] = 1; st.push(p2 + 1); }
                if (y2 > 0 && !c[p2 - bw] && !seen[p2 - bw]) { seen[p2 - bw] = 1; st.push(p2 - bw); } if (y2 < bh - 1 && !c[p2 + bw] && !seen[p2 + bw]) { seen[p2 + bw] = 1; st.push(p2 + bw); } }
            if (!edge && bgN < comp.length * 0.5) for (k = 0; k < comp.length; k++) c[comp[k]] = 1; }
        var m = new Uint8Array(W * H), hist = {}, cnt = 0, touched = false;
        for (y = 0; y < bh; y++) for (x = 0; x < bw; x++) if (c[y * bw + x]) { var gi = (y0 + y) * W + x0 + x; m[gi] = 255; cnt++; if (x < 2 || y < 2 || x >= bw - 2 || y >= bh - 2) touched = true; o = gi * 4; k = key5(d, o); hist[k] = (hist[k] || 0) + 1; }
        if (cnt < 24) return { fail: 'nothing in this box stands apart from the paint around it (the logo is the body colour, or the box is on plain paint)' };
        aaRim(m, d, W, H, [x0, y0, x1, y1], null, bgs, 2);
        for (y = Math.max(0, y0 - 3); y < Math.min(H, y1 + 3); y++) for (x = Math.max(0, x0 - 3); x < Math.min(W, x1 + 3); x++) if (m[y * W + x] && !(x >= x0 && x < x1 && y >= y0 && y < y1)) m[y * W + x] = 0;          // no spread outside the box
        var px = 0; for (y = y0; y < y1; y++) for (x = x0; x < x1; x++) if (m[y * W + x]) px++;
        var cols = clusterKeys(hist, 30, 4).map(function (q) { return q.c; });
        var lnote = opts.lettering ? (plate ? 'lettering only: the plate colour ' + hexC(plate) + ' was left as it is' : 'lettering only: no separate plate found, the whole logo was taken') : (plate && plateShare >= 0.5 ? 'the whole decal was taken, its plate / tile (' + hexC(plate) + ', ' + Math.round(plateShare * 100) + '% of it) included: to change only the lettering call again with lettering:true' : undefined);
        return { m: m, px: px, rgb: cols, info: { mode: 'logo', note: lnote, lettering: opts.lettering ? true : undefined, pixels_selected: px, share_of_box_pct: Math.round(px / Math.max(1, n) * 1000) / 10, share_of_sheet_pct: Math.round(px / (W * H) * 10000) / 100, outside_box_px: 0, touched_edge: touched, capped: false, cap_reason: null, colour_used: cols.map(hexC), background: bgs.map(hexC), background_source: bg.source === 'ring' ? undefined : bg.source } };
    }
    // glyph mode hint: how much of the box is "not the paint around it" (to say: outlined / patterned / shaded digit -> try mode logo)
    function nonBgPx(d, W, H, x0, y0, x1, y1) { var bg = ringBg(d, W, H, x0, y0, x1, y1), n = 0; for (var y = y0; y < y1; y += 2) for (var x = x0; x < x1; x += 2) { var o = (y * W + x) * 4; if (d[o + 3] >= 128 && nearD([d[o], d[o + 1], d[o + 2]], bg.cols) > WP5.bgTol) n++; } return n * 4; }
    // completeness assist: look-alikes the AI did NOT box (512 downsample); never marked automatically except spread:"sheet" (score >= 0.7, max 6)
    function candidatesFor(kind, mode, mask, cols, T, boxes, perBox, thick) {
        try {
            var pd = paintData(); if (!pd || !cols.length) return []; var W = pd.width, H = pd.height, d = pd.data, N = 512, G = W / N, GH = H / N, on = new Uint8Array(N * N), cm = new Uint8Array(N * N), x, y, i, o;
            var P = _cache && _cache.P, R = _cache && _cache.R;
            var bxp = boxes.map(function (b) { return [Math.floor((b[0] - 0.01) * N), Math.floor((b[1] - 0.01) * N), Math.ceil((b[2] + 0.01) * N), Math.ceil((b[3] + 0.01) * N)]; });
            for (y = 0; y < N; y++) for (x = 0; x < N; x++) {
                var sx = Math.min(W - 1, Math.floor((x + 0.5) * G)), sy = Math.min(H - 1, Math.floor((y + 0.5) * GH)), s = sy * W + sx; o = s * 4; if (d[o + 3] < 128 || (mask && mask[s])) continue;
                var p = [d[o], d[o + 1], d[o + 2]], hit = false, close = false; for (var t = 0; t < cols.length; t++) { var dd = cdist(p, cols[t]); if (dd <= T[t]) { hit = true; if (dd <= T[t] / 2) close = true; } } if (!hit) continue;
                if (P && R && P[4 * R * R + Math.min(R - 1, (y * R / N) | 0) * R + Math.min(R - 1, (x * R / N) | 0)] >= 0.5) continue;          // the net's dead space (template / off-car)
                var inb = false; for (var bi = 0; bi < bxp.length && !inb; bi++) { var b = bxp[bi]; if (x >= b[0] && x < b[2] && y >= b[1] && y < b[3]) inb = true; } if (inb) continue;
                on[y * N + x] = 1; if (close) cm[y * N + x] = 1;
            }
            var glue = mode === 'logo' ? 2 : 0, grp = on;
            if (mode === 'colour_in_region') {          // 3x3 closing
                var dl = new Uint8Array(N * N); for (y = 1; y < N - 1; y++) for (x = 1; x < N - 1; x++) { var any = 0; for (var a = -1; a <= 1 && !any; a++) for (var b2 = -1; b2 <= 1; b2++) if (on[(y + a) * N + x + b2]) { any = 1; break; } dl[y * N + x] = any; }
                grp = new Uint8Array(N * N); for (y = 1; y < N - 1; y++) for (x = 1; x < N - 1; x++) { var all = 1; for (var a2 = -1; a2 <= 1 && all; a2++) for (var b3 = -1; b3 <= 1; b3++) if (!dl[(y + a2) * N + x + b3]) { all = 0; break; } grp[y * N + x] = all || on[y * N + x]; }
            }
            var seen = new Uint8Array(N * N), st = [], out = [], med = perBox.length ? perBox.slice().sort(function (a, b) { return a - b; })[(perBox.length / 2) | 0] / (G * GH) : 0, tRef = Math.max(1.5, (thick || 0) / G);
            for (i = 0; i < N * N; i++) {
                if (!grp[i] || seen[i]) continue; var pix = [], cnt = 0, cl = 0, mx0 = N, my0 = N, mx1 = 0, my1 = 0; st.push(i); seen[i] = 1;
                while (st.length) { var c = st.pop(), cx = c % N, cy = (c / N) | 0; pix.push(c); if (on[c]) { cnt++; if (cm[c]) cl++; } if (cx < mx0) mx0 = cx; if (cy < my0) my0 = cy; if (cx > mx1) mx1 = cx; if (cy > my1) my1 = cy;
                    for (var dy = -1 - glue; dy <= 1 + glue; dy++) for (var dx = -1 - glue; dx <= 1 + glue; dx++) { var xx = cx + dx, yy = cy + dy; if (xx < 0 || yy < 0 || xx >= N || yy >= N) continue; var q = yy * N + xx; if (grp[q] && !seen[q]) { seen[q] = 1; st.push(q); } } }
                if (cnt < 6) continue; var sim, why;
                if (mode === 'colour_in_region') {
                    var lng = Math.max(mx1 - mx0 + 1, my1 - my0 + 1); if (lng < 0.04 * N) continue;
                    var setP = {}; pix.forEach(function (q) { setP[q] = 1; });
                    var tc = thickOf(function (px, py) { return !!setP[py * N + px]; }, mx0, my0, mx1 + 1, my1 + 1, true), ratio = Math.max(1, tc) / tRef;
                    if (ratio < 0.6 || ratio > 1.6) continue;
                    if (cnt > 1.6 * Math.max(1, tc) * lng) continue;          // a stripe's area ~ its length x thickness; letters / digits of the same stroke width hold far more stroke than their long side
                    sim = Math.max(0, 1 - Math.abs(Math.log(ratio)) / Math.log(2.5)); why = 'same colour, same thickness (' + (Math.round(ratio * 10) / 10) + 'x), not boxed';
                } else {
                    if (!med) continue; var ra = cnt / med; if (ra < 0.4 || ra > 2.5) continue;
                    var rn = 0, rc = 0; for (y = Math.max(0, my0 - 3); y <= Math.min(N - 1, my1 + 3); y++) for (x = Math.max(0, mx0 - 3); x <= Math.min(N - 1, mx1 + 3); x++) { if (x >= mx0 && x <= mx1 && y >= my0 && y <= my1) continue; rn++; if (on[y * N + x]) rc++; }
                    if (rn && rc / rn > 0.5) continue;          // sits inside a big panel of the same colour
                    sim = Math.max(0, 1 - Math.abs(Math.log(ra)) / Math.log(2.5)); why = 'same colours, similar size (' + (Math.round(ra * 10) / 10) + 'x), not boxed';
                }
                var score = 0.5 * (cl / Math.max(1, cnt)) + 0.5 * sim; if (score < 0.5) continue;
                out.push({ box: [mx0 / N - 0.01, my0 / N - 0.01, (mx1 + 1) / N + 0.01, (my1 + 1) / N + 0.01].map(function (v) { return Math.round(Math.max(0, Math.min(1, v)) * 100) / 100; }), why: why, score: Math.round(score * 100) / 100 });
            }
            out.sort(function (a, b) { return b.score - a.score; }); return out;
        } catch (e) { return []; }
    }
    function primeForTest(W, H) { var z = function () { return new Uint8Array(W * H); }; _cache = { sig: 'test-' + W + 'x' + H, lv: _lv, W: W, H: H, result: { kinds: { numbers: { found: false }, sponsors: { found: false }, stripes: { found: false } } }, masks: { numbers: z(), sponsors: z(), stripes: z() }, labs: {}, taught: {}, tlabs: {}, tinfo: {}, tcols: {} }; return _cache.sig; }
    var MODE_OF = { numbers: 'glyph', sponsors: 'logo', stripes: 'colour_in_region' };
    function modeFor(kind, mode) { var m = String(mode || 'auto').toLowerCase().replace(/[^a-z_]/g, ''); if (m === 'colour' || m === 'color' || m === 'color_in_region' || m === 'colourinregion') m = 'colour_in_region'; return /^(glyph|logo|colour_in_region)$/.test(m) ? m : (MODE_OF[kind] || 'glyph'); }
    // a taught mask's own colour labels (nearest taught glyph colour per masked pixel) + the facts a result reports (boxes, share, colours)
    function finishTeach(kind, boxes) {
        var m = _cache.taught[kind], W = _cache.W, H = _cache.H, pd = paintData(), tc = (_cache.tcols && _cache.tcols[kind]) || [], px = 0, i, k;
        var lab = new Uint8Array(W * H), cnt = tc.map(function () { return 0; });
        if (pd) for (i = 0; i < m.length; i++) if (m[i]) {
            px++; var o = i * 4, bi = -1, bd = 1e9;
            for (k = 0; k < tc.length; k++) { var dd = Math.max(Math.abs(pd.data[o] - tc[k][0]), Math.abs(pd.data[o + 1] - tc[k][1]), Math.abs(pd.data[o + 2] - tc[k][2])); if (dd < bd) { bd = dd; bi = k; } }
            if (bi >= 0) { lab[i] = bi + 1; cnt[bi]++; }
        }
        var tot = Math.max(1, px), cols = tc.map(function (c, q) { return { hex: hexOf(c[0], c[1], c[2]), share: cnt[q] / tot }; });
        _cache.tlabs = _cache.tlabs || {}; _cache.tinfo = _cache.tinfo || {};
        _cache.labs[kind] = _cache.tlabs[kind] = { lab: lab, cols: cols };
        var res = _cache.result.kinds[kind], info = { boxes: boxes, groups: boxes.length, share: Math.round(px / m.length * 1000) / 10, colours: cols.map(function (c) { return c.hex; }) };
        _cache.tinfo[kind] = info; res.boxes = info.boxes; res.groups = info.groups; res.share = info.share; res.colours = info.colours;
    }
    // the buyer pointed at one: rect {x0,y0,x1,y1} (0-1) around a number / logo -> its colours (not the body behind it) become the mask inside a slightly larger box of that kind's other findings
    function teach(kind, rect, opts) {
        var pd = paintData(); if (!_cache || !pd || !rect) return null; var W = pd.width, H = pd.height, d = pd.data, x, y;
        var x0 = Math.max(0, Math.round(rect.x0 * W)), x1 = Math.min(W, Math.round(rect.x1 * W)), y0 = Math.max(0, Math.round(rect.y0 * H)), y1 = Math.min(H, Math.round(rect.y1 * H));
        var md = opts && opts.mode, rgb, m, px = 0, cc = null, ginfo = null, reg = null;
        if (md === 'colour_in_region' || md === 'logo') {          // WP5 modes: their own region finders; the merge / colours / finishTeach path below is shared
            reg = md === 'logo' ? logoRegion(d, W, H, x0, y0, x1, y1, opts) : colourRegion(d, W, H, x0, y0, x1, y1, opts);
            if (!reg) return null; if (reg.fail) return { fail: reg.fail };
            cc = { m: reg.m, px: reg.px, rgb: reg.rgb.map(function (c) { return [c[0] - 4, c[1] - 4, c[2] - 4]; }), info: reg.info };
        } else { m = new Uint8Array(W * H); cc = glyphMask(d, W, H, x0, y0, x1, y1, !!(opts && opts.cc)); }          // WP2: segBox first (outline + fill + shading together), then the old cc / colour modes
        if (cc) { m = cc.m; rgb = cc.rgb; px = cc.px; ginfo = cc.info; } else if (opts && opts.cc) return null;
        var rim = {}, inner = {}, ni = 0, nr = 0;
        if (!cc) for (y = y0; y < y1; y += 2) for (x = x0; x < x1; x += 2) {          // the old box-colour mode only (WP5: this pass was wasted work when cc / a mode found the glyph)
            var o = (y * W + x) * 4, k = (d[o] >> 3) * 1024 + (d[o + 1] >> 3) * 32 + (d[o + 2] >> 3), edge = (x - x0 < 8 || x1 - x < 8 || y - y0 < 8 || y1 - y < 8);
            if (edge) { rim[k] = (rim[k] || 0) + 1; nr++; } else { inner[k] = (inner[k] || 0) + 1; ni++; }
        }
        var cols = Object.keys(inner).map(function (k) { return { k: +k, n: inner[k], rim: (rim[k] || 0) / Math.max(1, nr) }; }).filter(function (c) { return c.n / ni > 0.04 && c.rim < 0.25; }).sort(function (a, b) { return b.n - a.n; }).slice(0, 4);
        if (!cc && !cols.length) return null;
        if (!cc) rgb = cols.map(function (c) { return [(c.k >> 10) << 3, ((c.k >> 5) & 31) << 3, (c.k & 31) << 3]; });
        if (!cc) for (y = y0; y < y1; y++) for (x = x0; x < x1; x++) { var oo = (y * W + x) * 4; for (var j = 0; j < rgb.length; j++) if (Math.abs(d[oo] - rgb[j][0] - 4) <= 22 && Math.abs(d[oo + 1] - rgb[j][1] - 4) <= 22 && Math.abs(d[oo + 2] - rgb[j][2] - 4) <= 22) { m[y * W + x] = 255; px++; break; } }
        _cache.taught = _cache.taught || {}; var prev = (opts && opts.replace) ? new Uint8Array(W * H) : (_cache.taught[kind] || _cache.masks[kind]), merged = new Uint8Array(prev); for (var i = 0; i < m.length; i++) if (m[i]) merged[i] = 255;
        _cache.taught[kind] = merged;
        var res = _cache.result.kinds[kind] || (_cache.result.kinds[kind] = {}); res.found = true; res.taught = true; res.conf = 1; res.colours = rgb.map(function (c) { return hexOf(c[0] + 4, c[1] + 4, c[2] + 4); });
        var bx = [rect.x0, rect.y0, rect.x1, rect.y1]; _cache.tcols = _cache.tcols || {}; var tc = (opts && opts.replace) ? [] : (_cache.tcols[kind] || []);
        rgb.forEach(function (c) { var q = [c[0] + 4, c[1] + 4, c[2] + 4]; if (!tc.some(function (e) { return Math.abs(e[0] - q[0]) < 30 && Math.abs(e[1] - q[1]) < 30 && Math.abs(e[2] - q[2]) < 30; })) tc.push(q); }); _cache.tcols[kind] = tc;
        finishTeach(kind, (opts && opts.replace) ? [bx] : ((res.boxes || []).concat([bx])));
        return { px: px, colours: rgb.map(function (c) { return hexOf(c[0] + 4, c[1] + 4, c[2] + 4); }), box: bx, reg: reg ? { T: reg.T, thick: reg.thick, rgb: reg.rgb, spread: reg.spread } : null, info: ginfo || { pixels_selected: px, share_of_box_pct: Math.round(px / Math.max(1, (x1 - x0) * (y1 - y0)) * 1000) / 10, low_contrast: false, how: 'colour' } };
    }
    // several loose boxes (an AI that read the picture, or the buyer): each one teaches its glyph colours; replace = forget the net's guess first
    function teachBoxes(kind, boxes, opts) {
        opts = opts || {}; if (!_cache) return null; var used = [], first = true, colours = [], skipped = [], places = [], perBox = [], t0 = Date.now();
        var mode = modeFor(kind, opts.mode), W0 = _cache.W, H0 = _cache.H, callPx = 0, regs = [];          // WP5: mode by kind (numbers glyph, sponsors logo, stripes colour_in_region)
        (boxes || []).forEach(function (b) {
            if (!b || b.length < 4) { skipped.push({ box: b, why: 'not [x0,y0,x1,y1]' }); return; } var v = [+b[0], +b[1], +b[2], +b[3]]; if (v.some(function (q) { return isNaN(q); })) { skipped.push({ box: b, why: 'not numbers' }); return; }
            if (Math.max.apply(null, v) > 1.0001) v = v.map(function (q) { return q / 100; });          // given as percent
            v = [Math.max(0, Math.min(v[0], v[2])), Math.max(0, Math.min(v[1], v[3])), Math.min(1, Math.max(v[0], v[2])), Math.min(1, Math.max(v[1], v[3]))];
            var vr = v.map(function (q) { return Math.round(q * 1000) / 1000; }), bw = v[2] - v[0], bh = v[3] - v[1];
            if (mode === 'glyph' && (bw < 0.008 || bh < 0.008 || bw * bh > 0.1)) { skipped.push({ box: vr, why: 'size: a box must be at least ~1% wide and at most ~10% of the whole sheet (one number, not a panel)' }); return; }
            if (mode === 'logo' && (bw < 0.008 || bh < 0.008 || bw * bh > 0.12)) { skipped.push({ box: vr, why: 'size: a logo box must be at least ~1% wide and at most ~12% of the whole sheet (one logo, not a panel)' }); return; }
            if (mode === 'colour_in_region' && (Math.max(bw, bh) < 0.008 || Math.min(bw, bh) < 0.003 || bw * bh > 0.1)) { skipped.push({ box: vr, why: 'size: a stripe box must be at least ~0.3% across, ~1% long and at most ~10% of the whole sheet' }); return; }
            var left = Math.floor(WP5.capCall * W0 * H0) - callPx;
            if (mode === 'colour_in_region' && left < 1000) { skipped.push({ box: vr, why: 'this call already selected ' + Math.round(WP5.capCall * 100) + '% of the sheet (more than a quarter of the car is not stripes)' }); return; }
            // MCPSCEN 2026-10-05 (owner SS, numbers marked colour_in_region black: the black spray-can cap and heartbeat stripes next to the boxes turned gold). Following the colour past the box is for stripes under caps; numbers / sponsors stay inside their box unless spread is asked for.
            var r = teach(kind, { x0: v[0], y0: v[1], x1: v[2], y1: v[3] }, { replace: !!opts.replace && first, cc: true, mode: mode === 'glyph' ? null : mode, lettering: !!opts.lettering, colour: opts.colour, spread: opts.spread || (mode === 'colour_in_region' && kind !== 'stripes' ? 'box' : undefined), tolerance: opts.tolerance, budget: Math.min(Math.floor(WP5.capBox * W0 * H0), left) });
            if (r && r.fail) { skipped.push({ box: vr, why: r.fail }); return; }
            if (!r) { skipped.push({ box: vr, why: mode === 'glyph' ? 'glyph: nothing inside this box stands apart from the paint around it (it all runs out through the box edge, or it is empty / the body colour / photo-like): put a loose box around ONE number with a little paint around it' : 'nothing usable in this box' }); return; }
            first = false; used.push(vr); r.colours.forEach(function (c) { if (colours.indexOf(c) === -1) colours.push(c); }); callPx += r.px; if (r.reg) regs.push(r.reg);
            var inf = r.info || {}, sh = inf.share_of_box_pct, pl;
            if (mode === 'glyph') {
                pl = { box: vr, mode: 'glyph', pixels_selected: inf.pixels_selected, share_of_box_pct: sh, colours_used: r.colours.slice(0, 4), colour_used: r.colours.slice(0, 4), touched_rim_px: inf.touched_rim_px || undefined, touched_edge: !!inf.touched_rim_px, low_contrast: inf.low_contrast || undefined, capped: false, cap_reason: null };
                if (sh < 0.5) pl.warning = 'only ' + sh + '% of the box selected: check the image (box on the wrong thing, or the digit is the body colour)';
                else if (sh > 80) pl.warning = sh + '% of the box selected: background is probably in it - give a tighter box and check the image';
                else if (inf.low_contrast) pl.warning = 'the digit colour is close to the paint around it: selected by connected region, check the image';
                try { var pd0 = paintData(), X0 = Math.round(v[0] * W0), Y0 = Math.round(v[1] * H0), X1 = Math.round(v[2] * W0), Y1 = Math.round(v[3] * H0), nb = nonBgPx(pd0.data, W0, H0, X0, Y0, X1, Y1); if (nb > 200 && (inf.pixels_selected || r.px) < 0.35 * nb) pl.hint = sh < 4 ? 'only ' + sh + '% of the box was selected although most of it is number art: the box is probably TOO TIGHT (the number touches the box edge, so its own colours were read as the paint around it). Call again with replace:true and a LOOSER box with a little body paint all around the number; mode:"logo" only if a loose box still fails' : 'most of this box is not one-colour glyph: if this number is outlined, patterned or shaded, call again with mode:"logo"'; if (sh < 4 && !pl.warning) pl.warning = 'only ' + sh + '% of the box selected: do NOT refinish this mark, re-box it first'; } catch (eh) {}          // MCPSCEN 2026-10-05 (SS roof "32" with a box cutting the digits: 1.2% selected = yellow edge pixels, and the hint said mode logo)
            } else {
                pl = { box: vr }; Object.keys(inf).forEach(function (k) { if (inf[k] !== undefined) pl[k] = inf[k]; });
                if (sh < 0.5) pl.warning = 'only ' + sh + '% of the box selected: check the image';
                else if (mode === 'logo' && sh > 85) pl.warning = sh + '% of the box selected: the logo may sit on a panel the same size as the box, or the box is on a busy area - check the image';
            }
            places.push(pl); perBox.push(inf.pixels_selected || r.px);
        });
        if (!used.length) return { used: [], skipped: skipped, mode: mode, timing_ms: Date.now() - t0 };
        finishTeach(kind, used); var inf2 = _cache.tinfo[kind], pd = paintData(), more = [], cands = [];
        if (pd && kind === 'numbers' && mode === 'glyph') { more = maybeMore(pd.data, pd.width, pd.height, _cache.taught[kind], used, perBox); cands = more.slice(0, 4).map(function (b) { return { box: b, why: 'same colours at a similar size, not boxed' }; }); }
        else if (pd) {
            var cols = [], T = [], th = 0; if (regs.length) regs.forEach(function (g) { g.rgb.forEach(function (c, q) { if (!cols.some(function (e) { return cdist(e, c) <= 20; })) { cols.push(c); T.push(g.T ? g.T[q] : 30); } }); th = Math.max(th, g.thick || 0); });
            else { (_cache.tcols[kind] || []).slice(0, 2).forEach(function (c) { cols.push(c); T.push(30); }); }
            var all = candidatesFor(kind, mode, _cache.taught[kind], cols, T, used, perBox, th);
            if (mode === 'colour_in_region' && opts.spread === 'sheet') {          // spread "sheet": the strong look-alikes join (score >= 0.7, max 6), each reported
                var mk = _cache.taught[kind], W = pd.width, H = pd.height, d = pd.data;
                all.filter(function (c) { return c.score >= 0.7; }).slice(0, 6).forEach(function (c) {
                    var X0 = Math.floor(c.box[0] * W), Y0 = Math.floor(c.box[1] * H), X1 = Math.ceil(c.box[2] * W), Y1 = Math.ceil(c.box[3] * H), n = 0;
                    for (var y = Y0; y < Y1; y++) for (var x = X0; x < X1; x++) { var o = (y * W + x) * 4, p = [d[o], d[o + 1], d[o + 2]]; if (d[o + 3] < 128) continue; for (var t = 0; t < cols.length; t++) if (cdist(p, cols[t]) <= T[t]) { if (!mk[y * W + x]) { mk[y * W + x] = 255; n++; } break; } }
                    if (n) { c.added = true; places.push({ box: null, via: 'sheet', area: c.box, pixels_selected: n, why: c.why, score: c.score }); }
                });
                finishTeach(kind, used); inf2 = _cache.tinfo[kind];
                all = all.filter(function (c) { return !c.added; });
            }
            cands = all.slice(0, 4);
        }
        return { used: used, skipped: skipped, mode: mode, colours: inf2.colours, share: inf2.share, places: places, maybe_more: more, candidates: cands, timing_ms: Date.now() - t0 };
    }
    root.SpbProElements = { VERSION: VERSION, _segBox: segBox, _glyphMask: glyphMask, _ccGlyphs: ccGlyphs, _maybeMore: maybeMore, _colourRegion: colourRegion, _logoRegion: logoRegion, _ringBg: ringBg, _candidatesFor: candidatesFor, _primeForTest: primeForTest, modeFor: modeFor, _setSegOpts: function (o) { _segOpts = o || {}; }, sheet: sheet, teachBoxes: teachBoxes, probsOf: probsOf, summarise: summarise, SHARP: SHARP, analyse: analyse, maskFor: maskFor, kinds: kinds, overlay: overlay, thumb: thumb, sig: function () { return _cache ? _cache.sig : null; }, teach: teach, remember: remember, forget: forget, learnedFor: learnedFor, carKey: carKey, learnReset: learnReset, ready: ready, analysePixels: analysePixels, forwardForTest: function (x, R) { return forward(x, R, model()); }, _toInput: toInput, _softmax: softmax, _model: model };
})();
