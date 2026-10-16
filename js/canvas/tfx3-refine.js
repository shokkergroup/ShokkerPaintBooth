/* [SPB-TFX3 2026-10-10 PORT-3 Refine Edge ("Select and Mask"), lane TOOLS-FIX-3]
 * Port of PhotoCraft crates/algo/src/matting.rs (edge refinement + colour decontamination) to the SPB selection.
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0 (MIT elected). Modified: rewritten in JavaScript for SPB's
 * Uint8 (0..255) selection masks, tiled around the selection edge so the cost follows the edge length, not the canvas area.
 * Cites (as PhotoCraft does): K. He, J. Sun, X. Tang, "Guided Image Filtering" (ECCV 2010 / PAMI 2013) for the edge-aware part;
 * Felzenszwalb & Huttenlocher, "Distance Transforms of Sampled Functions" (2012) for the band distance.
 *
 * BEFORE (measured, fix3/refine_before.json): a selection could only be grown / shrunk / feathered / smoothed as a blind, edge-ignorant blur. A Wand or
 * Lasso selection through the soft rim of a sponsor logo was either a hard stair-step or a uniform blur that ate the logo and kept the background
 * colour in the fringe. The copy / cut-out of it carried the old background colour around the edge.
 * AFTER: Mask > "Refine Edge..." opens a panel with live preview. The selection snaps to the real edge of the picture (edge detection radius,
 * optional smart radius), then Smooth, Feather, Contrast and Shift Edge as in Photoshop's Select and Mask; viewed as red overlay / on white /
 * on black / mask only; applied back to the selection, or as a NEW LAYER cut-out whose edge colours are cleaned (decontaminate).
 * Kill switch: window.SPB_TFX3_OFF (menu button hidden, nothing else changes).
 */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBTfx3RefineCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';
    var EPS = 1e-4, INF = 1e20;

    // ------------------------------------------------------------------ filters (all on Float32Array w*h, row-major)
    function boxMean(src, w, h, r) {
        var tmp = new Float32Array(w * h), out = new Float32Array(w * h), pre = new Float64Array(Math.max(w, h) + 1), x, y;
        for (y = 0; y < h; y++) {
            var o = y * w;
            for (x = 0; x < w; x++) pre[x + 1] = pre[x] + src[o + x];
            for (x = 0; x < w; x++) {
                var lo = x - r < 0 ? 0 : x - r, hi = x + r + 1 > w ? w : x + r + 1;
                tmp[o + x] = (pre[hi] - pre[lo]) / (hi - lo);
            }
        }
        var acc = new Float64Array(w), lo2 = 0, hi2 = Math.min(h, r + 1);
        for (y = 0; y < hi2; y++) for (x = 0; x < w; x++) acc[x] += tmp[y * w + x];
        for (y = 0; y < h; y++) {
            var nlo = y - r < 0 ? 0 : y - r, nhi = y + r + 1 > h ? h : y + r + 1;
            while (hi2 < nhi) { for (x = 0; x < w; x++) acc[x] += tmp[hi2 * w + x]; hi2++; }
            while (lo2 < nlo) { for (x = 0; x < w; x++) acc[x] -= tmp[lo2 * w + x]; lo2++; }
            var n = hi2 - lo2, oo = y * w;
            for (x = 0; x < w; x++) out[oo + x] = acc[x] / n;
        }
        return out;
    }

    function gaussianBlur(src, w, h, sigma) {
        if (!(sigma >= 0.1)) return src.slice();
        var r = Math.ceil(sigma * 3), k = new Float32Array(2 * r + 1), s = 0, i, x, y;
        for (i = -r; i <= r; i++) { k[i + r] = Math.exp(-(i * i) / (2 * sigma * sigma)); s += k[i + r]; }
        for (i = 0; i < k.length; i++) k[i] /= s;
        var tmp = new Float32Array(w * h), out = new Float32Array(w * h);
        for (y = 0; y < h; y++) {
            var o = y * w;
            for (x = 0; x < w; x++) {
                var a = 0;
                if (x >= r && x + r < w) { for (i = 0; i < k.length; i++) a += src[o + x + i - r] * k[i]; }
                else { for (i = 0; i < k.length; i++) { var xx = x + i - r; xx = xx < 0 ? 0 : (xx > w - 1 ? w - 1 : xx); a += src[o + xx] * k[i]; } }
                tmp[o + x] = a;
            }
        }
        for (y = 0; y < h; y++) {
            for (x = 0; x < w; x++) {
                var b = 0;
                if (y >= r && y + r < h) { for (i = 0; i < k.length; i++) b += tmp[(y + i - r) * w + x] * k[i]; }
                else { for (i = 0; i < k.length; i++) { var yy = y + i - r; yy = yy < 0 ? 0 : (yy > h - 1 ? h - 1 : yy); b += tmp[yy * w + x] * k[i]; } }
                out[y * w + x] = b;
            }
        }
        return out;
    }

    // grey dilation / erosion by ~r px: alternating 3x3 square and cross steps (an octagonal structuring element), like PhotoCraft's morph()
    function morph(src, w, h, r, grow) {
        var cur = src.slice(), nxt = new Float32Array(w * h), x, y, k;
        for (k = 0; k < r; k++) {
            var square = (k % 2) === 0;
            for (y = 0; y < h; y++) {
                for (x = 0; x < w; x++) {
                    var i = y * w + x, v = cur[i], c;
                    if (x > 0) { c = cur[i - 1]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                    if (x + 1 < w) { c = cur[i + 1]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                    if (y > 0) { c = cur[i - w]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                    if (y + 1 < h) { c = cur[i + w]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                    if (square) {
                        if (x > 0 && y > 0) { c = cur[i - w - 1]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                        if (x + 1 < w && y > 0) { c = cur[i - w + 1]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                        if (x > 0 && y + 1 < h) { c = cur[i + w - 1]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                        if (x + 1 < w && y + 1 < h) { c = cur[i + w + 1]; v = grow ? (c > v ? c : v) : (c < v ? c : v); }
                    }
                    nxt[i] = v;
                }
            }
            var t = cur; cur = nxt; nxt = t;
        }
        return cur;
    }

    // running max / min over a (2r+1) square, separable, monotonic deque (O(n) whatever the radius)
    function slidingExtreme(src, w, h, r, isMax) {
        var tmp = new Float32Array(w * h), out = new Float32Array(w * h), dq = new Int32Array(Math.max(w, h) + 2), x, y;
        function line(get, set, n) {
            var head = 0, tail = 0, i, nextIn = 0;
            for (i = 0; i < n; i++) {
                var hiIdx = i + r < n - 1 ? i + r : n - 1;
                while (nextIn <= hiIdx) {
                    var v = get(nextIn);
                    while (tail > head && (isMax ? get(dq[tail - 1]) <= v : get(dq[tail - 1]) >= v)) tail--;
                    dq[tail++] = nextIn; nextIn++;
                }
                while (dq[head] < i - r) head++;
                set(i, get(dq[head]));
            }
        }
        for (y = 0; y < h; y++) { (function (yy) { line(function (i) { return src[yy * w + i]; }, function (i, v) { tmp[yy * w + i] = v; }, w); })(y); }
        for (x = 0; x < w; x++) { (function (xx) { line(function (i) { return tmp[i * w + xx]; }, function (i, v) { out[i * w + xx] = v; }, h); })(x); }
        return out;
    }

    // per-pixel transition width of the picture's luminance: local range / local max gradient (a sharp step gives ~2 px, a ramp of width L gives ~L)
    function edgeWidth(R, G, B, w, h, r) {
        var n = w * h, Y = new Float32Array(n), g = new Float32Array(n), x, y, i;
        for (i = 0; i < n; i++) Y[i] = 0.299 * R[i] + 0.587 * G[i] + 0.114 * B[i];
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
            var xl = x > 0 ? x - 1 : 0, xr = x + 1 < w ? x + 1 : w - 1, yu = y > 0 ? y - 1 : 0, yd = y + 1 < h ? y + 1 : h - 1;
            var gx = (Y[y * w + xr] - Y[y * w + xl]) / 2, gy = (Y[yd * w + x] - Y[yu * w + x]) / 2;
            g[y * w + x] = Math.sqrt(gx * gx + gy * gy);
        }
        var gm = slidingExtreme(g, w, h, r, true), hi = slidingExtreme(Y, w, h, r, true), lo = slidingExtreme(Y, w, h, r, false), out = new Float32Array(n);
        for (i = 0; i < n; i++) out[i] = (hi[i] - lo[i]) / Math.max(gm[i], 1e-4);
        return out;
    }

    // Euclidean distance to the nearest boundary pixel (Felzenszwalb & Huttenlocher), boundary = Uint8Array(0/1)
    function edt(boundary, w, h) {
        var n = w * h, f = new Float64Array(Math.max(w, h)), d = new Float64Array(Math.max(w, h)), v = new Int32Array(Math.max(w, h) + 1), z = new Float64Array(Math.max(w, h) + 2);
        var grid = new Float64Array(n), x, y, q;
        function dt1(len) {
            var k = 0; v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
            for (q = 1; q < len; q++) {
                var s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
                while (s <= z[k]) { k--; s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
                k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
            }
            k = 0;
            for (q = 0; q < len; q++) { while (z[k + 1] < q) k++; var dq = q - v[k]; d[q] = dq * dq + f[v[k]]; }
        }
        for (x = 0; x < w; x++) {
            for (y = 0; y < h; y++) f[y] = boundary[y * w + x] ? 0 : INF;
            dt1(h); for (y = 0; y < h; y++) grid[y * w + x] = d[y];
        }
        var out = new Float32Array(n);
        for (y = 0; y < h; y++) {
            for (x = 0; x < w; x++) f[x] = grid[y * w + x];
            dt1(w); for (x = 0; x < w; x++) out[y * w + x] = Math.sqrt(d[x]);
        }
        return out;
    }

    // guided filter with a colour guide (He et al. Eq. 19-21: a_k = (Sigma_k + eps U)^-1 cov_k(I, p)); R,G,B,p in 0..1
    function guidedFilterColor(R, G, B, p, w, h, r, eps) {
        var n = w * h, ch = [R, G, B], i, c;
        var m = ch.map(function (a) { return boxMean(a, w, h, r); });
        var mp = boxMean(p, w, h, r);
        var prod = function (a, b) { var o = new Float32Array(n); for (var j = 0; j < n; j++) o[j] = a[j] * b[j]; return o; };
        var mip = ch.map(function (a) { return boxMean(prod(a, p), w, h, r); });
        var pairs = [[0, 0], [0, 1], [0, 2], [1, 1], [1, 2], [2, 2]];
        var mii = pairs.map(function (pr) { return boxMean(prod(ch[pr[0]], ch[pr[1]]), w, h, r); });
        var a0v = new Float32Array(n), a1v = new Float32Array(n), a2v = new Float32Array(n), bv = new Float32Array(n);
        for (i = 0; i < n; i++) {
            var mu0 = m[0][i], mu1 = m[1][i], mu2 = m[2][i], e = eps;
            var rr = mii[0][i] - mu0 * mu0 + e, rg = mii[1][i] - mu0 * mu1, rb = mii[2][i] - mu0 * mu2;
            var gg = mii[3][i] - mu1 * mu1 + e, gb = mii[4][i] - mu1 * mu2, bb = mii[5][i] - mu2 * mu2 + e;
            var c0 = mip[0][i] - mu0 * mp[i], c1 = mip[1][i] - mu1 * mp[i], c2 = mip[2][i] - mu2 * mp[i];
            var i00 = gg * bb - gb * gb, i01 = gb * rb - rg * bb, i02 = rg * gb - gg * rb, i11 = rr * bb - rb * rb, i12 = rb * rg - rr * gb, i22 = rr * gg - rg * rg;
            var det = rr * i00 + rg * i01 + rb * i02, a0 = 0, a1 = 0, a2 = 0;
            if (Math.abs(det) >= 1e-30) {
                a0 = (i00 * c0 + i01 * c1 + i02 * c2) / det;
                a1 = (i01 * c0 + i11 * c1 + i12 * c2) / det;
                a2 = (i02 * c0 + i12 * c1 + i22 * c2) / det;
            }
            a0v[i] = a0; a1v[i] = a1; a2v[i] = a2;
            bv[i] = mp[i] - a0 * mu0 - a1 * mu1 - a2 * mu2;
        }
        var ma0 = boxMean(a0v, w, h, r), ma1 = boxMean(a1v, w, h, r), ma2 = boxMean(a2v, w, h, r), mb = boxMean(bv, w, h, r), out = new Float32Array(n);
        for (i = 0; i < n; i++) out[i] = ma0[i] * R[i] + ma1[i] * G[i] + ma2[i] * B[i] + mb[i];
        return out;
    }

    // ------------------------------------------------------------------ parameters (Photoshop units)
    function norm(p) {
        p = p || {};
        var num = function (v, lo, hi, d) { v = Number(v); if (!isFinite(v)) v = d; return Math.max(lo, Math.min(hi, v)); };
        return { radius: num(p.radius, 0, 64, 0), smartRadius: !!p.smartRadius, smooth: num(p.smooth, 0, 100, 0), feather: num(p.feather, 0, 250, 0), contrast: num(p.contrast, 0, 100, 0), shiftEdge: num(p.shiftEdge, -100, 100, 0) };
    }
    function gfRadius(p) { return Math.max(1, Math.min(64, Math.ceil(p.radius))); }
    function smoothSigma(p) { return p.smooth / 100 * 4; }
    function featherSigma(p) { return Math.max(0, p.feather) / 2; }
    function shiftPx(p) { return Math.max(-64, Math.min(64, Math.round(p.shiftEdge / 100 * Math.max(p.radius, 4)))); }
    function halo(p) {
        var g = gfRadius(p), edge = p.radius > 0 ? Math.max(Math.ceil(p.radius), 2 * g + (p.smartRadius ? g + 1 : 0)) : 0;
        return edge + Math.ceil(3 * smoothSigma(p)) + Math.ceil(3 * featherSigma(p)) + Math.abs(shiftPx(p)) + 2;
    }
    function spread(p) { return (p.radius > 0 ? Math.ceil(p.radius) : 0) + Math.ceil(3 * smoothSigma(p)) + Math.ceil(3 * featherSigma(p)) + Math.max(0, shiftPx(p)) + 1; }

    // refine one soft mask buffer m (0..1, w*h) with the picture (R,G,B 0..1) as guide; PhotoCraft refine_buffer
    function refineBuffer(R, G, B, m, w, h, p) {
        var n = w * h, a = m.slice(), i, x, y;
        if (p.radius > 0 && R) {
            var bin = new Uint8Array(n), boundary = new Uint8Array(n), any = false;
            for (i = 0; i < n; i++) bin[i] = m[i] >= 0.5 ? 1 : 0;
            for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
                i = y * w + x; var v = bin[i];
                var diff = (x > 0 && bin[i - 1] !== v) || (x + 1 < w && bin[i + 1] !== v) || (y > 0 && bin[i - w] !== v) || (y + 1 < h && bin[i + w] !== v);
                if (diff) { boundary[i] = 1; any = true; }
            }
            if (any) {
                var dist = edt(boundary, w, h), r = gfRadius(p), q = guidedFilterColor(R, G, B, m, w, h, r, EPS);
                var widths = p.smartRadius ? edgeWidth(R, G, B, w, h, r) : null;
                for (i = 0; i < n; i++) {
                    var reff = widths ? Math.max(1.5, Math.min(Math.max(p.radius, 1.5), widths[i])) : p.radius;
                    var wgt = reff + 1 - dist[i]; wgt = wgt < 0 ? 0 : (wgt > 1 ? 1 : wgt);
                    if (wgt > 0) { var qq = q[i] < 0 ? 0 : (q[i] > 1 ? 1 : q[i]); a[i] = m[i] + (qq - m[i]) * wgt; }
                }
            }
        }
        var ss = smoothSigma(p);
        if (ss >= 0.3) {
            a = gaussianBlur(a, w, h, ss);
            var gain = 1 + ss;
            for (i = 0; i < n; i++) { var t = (a[i] - 0.5) * gain + 0.5; a[i] = t < 0 ? 0 : (t > 1 ? 1 : t); }
        }
        a = gaussianBlur(a, w, h, featherSigma(p));
        if (p.contrast > 0) {
            var g2 = 1 / (1 - 0.99 * p.contrast / 100);
            for (i = 0; i < n; i++) { var t2 = (a[i] - 0.5) * g2 + 0.5; a[i] = t2 < 0 ? 0 : (t2 > 1 ? 1 : t2); }
        }
        var d = shiftPx(p);
        if (d !== 0) a = morph(a, w, h, Math.abs(d), d > 0);
        return a;
    }

    function bounds(mask, W, H) {
        var x0 = W, y0 = H, x1 = -1, y1 = -1, x, y;
        for (y = 0; y < H; y++) {
            var o = y * W, hit = false;
            for (x = 0; x < W; x++) if (mask[o + x]) { hit = true; if (x < x0) x0 = x; break; }
            if (!hit) continue;
            for (x = W - 1; x >= 0; x--) if (mask[o + x]) { if (x > x1) x1 = x; break; }
            if (y < y0) y0 = y; if (y > y1) y1 = y;
        }
        return x1 < 0 ? null : { x0: x0, y0: y0, x1: x1 + 1, y1: y1 + 1 };
    }

    // Refines a selection (Uint8Array W*H 0..255) using the picture (RGBA Uint8ClampedArray W*H*4, may be null when radius = 0).
    // Tiled: only tiles around the selection edge are processed; returns { mask, win:{x0,y0,x1,y1}, changed, soft, tiles, ms }.
    function refineMask(base, W, H, rgba, params) {
        var t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
        var p = norm(params), bb = bounds(base, W, H);
        if (!bb) return { mask: base.slice(), win: null, changed: 0, soft: 0, tiles: 0, ms: 0 };
        var hl = halo(p), sp = spread(p);
        var win = { x0: Math.max(0, bb.x0 - sp), y0: Math.max(0, bb.y0 - sp), x1: Math.min(W, bb.x1 + sp), y1: Math.min(H, bb.y1 + sp) };
        // ext tile ~ (core+2*halo)^2: core = 4x halo keeps the overhead ~2.25x while interior tiles are skipped fast
        var out = base.slice(), core = Math.max(64, Math.min(512, hl * 4)), tiles = 0, tx, ty, x, y;
        var useImg = p.radius > 0 && !!rgba;
        for (ty = win.y0; ty < win.y1; ty += core) {
            for (tx = win.x0; tx < win.x1; tx += core) {
                var cx0 = tx, cy0 = ty, cx1 = Math.min(win.x1, tx + core), cy1 = Math.min(win.y1, ty + core);
                var ex0 = Math.max(0, cx0 - hl), ey0 = Math.max(0, cy0 - hl), ex1 = Math.min(W, cx1 + hl), ey1 = Math.min(H, cy1 + hl);
                var ew = ex1 - ex0, eh = ey1 - ey0, n = ew * eh;
                var m = new Float32Array(n), vmin = 255, vmax = 0, i = 0;
                for (y = ey0; y < ey1; y++) { var o = y * W; for (x = ex0; x < ex1; x++, i++) { var v = base[o + x]; m[i] = v / 255; if (v < vmin) vmin = v; if (v > vmax) vmax = v; } }
                if (vmin === vmax && (vmax === 0 || vmax === 255)) continue;   // nothing to refine in this tile (all in or all out)
                var R = null, G = null, B = null;
                if (useImg) {
                    R = new Float32Array(n); G = new Float32Array(n); B = new Float32Array(n); i = 0;
                    for (y = ey0; y < ey1; y++) { var o4 = y * W * 4; for (x = ex0; x < ex1; x++, i++) { var q = o4 + x * 4; R[i] = rgba[q] / 255; G[i] = rgba[q + 1] / 255; B[i] = rgba[q + 2] / 255; } }
                }
                var res = refineBuffer(R, G, B, m, ew, eh, p);
                for (y = cy0; y < cy1; y++) {
                    var ro = (y - ey0) * ew - ex0, oo = y * W;
                    for (x = cx0; x < cx1; x++) { var rv = res[ro + x]; out[oo + x] = rv <= 0 ? 0 : (rv >= 1 ? 255 : Math.round(rv * 255)); }
                }
                tiles++;
            }
        }
        var changed = 0, soft = 0;
        for (y = win.y0; y < win.y1; y++) { var o2 = y * W; for (x = win.x0; x < win.x1; x++) { var ov = out[o2 + x]; if (ov !== base[o2 + x]) changed++; if (ov > 0 && ov < 255) soft++; } }
        return { mask: out, win: win, changed: changed, soft: soft, tiles: tiles, ms: (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0 };
    }

    // Decontaminate colours in the soft fringe of `alpha` (Uint8Array w*h 0..255) over the picture (RGBA w*h*4): fringe colours move towards the average
    // colour of nearby FULLY selected pixels (normalised convolution, box radius max(radius,3), widened x4 where none is near). Returns new RGBA.
    function decontaminate(rgba, alpha, w, h, radius, amount) {
        var out = new Uint8ClampedArray(rgba), rad = Math.max(3, Math.ceil(radius || 3)), hl = rad * 4, am = Math.max(0, Math.min(100, amount == null ? 100 : amount)) / 100;
        var soft = function (a) { return a > 0.02 && a < 0.98; }, T = 192, tx, ty, x, y;
        if (am <= 0) return out;
        for (ty = 0; ty < h; ty += T) for (tx = 0; tx < w; tx += T) {
            var cx1 = Math.min(w, tx + T), cy1 = Math.min(h, ty + T), any = false;
            for (y = ty; y < cy1 && !any; y++) for (x = tx; x < cx1; x++) if (soft(alpha[y * w + x] / 255)) { any = true; break; }
            if (!any) continue;
            var ex0 = Math.max(0, tx - hl), ey0 = Math.max(0, ty - hl), ex1 = Math.min(w, cx1 + hl), ey1 = Math.min(h, cy1 + hl), ew = ex1 - ex0, eh = ey1 - ey0, n = ew * eh;
            var wts = new Float32Array(n), vr = new Float32Array(n), vg = new Float32Array(n), vb = new Float32Array(n), i = 0;
            for (y = ey0; y < ey1; y++) for (x = ex0; x < ex1; x++, i++) {
                var a = alpha[y * w + x] / 255, q = (y * w + x) * 4;
                if (a >= 0.98) { var wt = rgba[q + 3] / 255; wts[i] = wt; vr[i] = wt * rgba[q]; vg[i] = wt * rgba[q + 1]; vb[i] = wt * rgba[q + 2]; }
            }
            var den = boxMean(wts, ew, eh, rad), den2 = boxMean(wts, ew, eh, rad * 4);
            var nr = boxMean(vr, ew, eh, rad), nr2 = boxMean(vr, ew, eh, rad * 4), ng = boxMean(vg, ew, eh, rad), ng2 = boxMean(vg, ew, eh, rad * 4), nb = boxMean(vb, ew, eh, rad), nb2 = boxMean(vb, ew, eh, rad * 4);
            for (y = ty; y < cy1; y++) for (x = tx; x < cx1; x++) {
                var al = alpha[y * w + x] / 255; if (!soft(al)) continue;
                var k = am * Math.max(0, Math.min(1, (1 - al) * 4)); if (k === 0) continue;
                var j = (y - ey0) * ew + (x - ex0), qo = (y * w + x) * 4, fr, fg, fb;
                if (den[j] > 1e-4) { fr = nr[j] / den[j]; fg = ng[j] / den[j]; fb = nb[j] / den[j]; }
                else if (den2[j] > 1e-4) { fr = nr2[j] / den2[j]; fg = ng2[j] / den2[j]; fb = nb2[j] / den2[j]; }
                else continue;
                out[qo] = rgba[qo] + (fr - rgba[qo]) * k; out[qo + 1] = rgba[qo + 1] + (fg - rgba[qo + 1]) * k; out[qo + 2] = rgba[qo + 2] + (fb - rgba[qo + 2]) * k;
            }
        }
        return out;
    }

    return { version: 'tfx3-2026-10-10', boxMean: boxMean, gaussianBlur: gaussianBlur, morph: morph, slidingExtreme: slidingExtreme, edgeWidth: edgeWidth, edt: edt,
        guidedFilterColor: guidedFilterColor, refineBuffer: refineBuffer, refineMask: refineMask, decontaminate: decontaminate, norm: norm, halo: halo, spread: spread, bounds: bounds };
});

// ====================================================================================== UI (browser only)
(function () {
    'use strict';
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (window.SPBTfx3Refine) return;
    var core = window.SPBTfx3RefineCore;
    function off() { return window.SPB_TFX3_OFF === true; }
    function toast(m, k) { try { if (typeof showToast === 'function') showToast(m, k); } catch (_e) { } }
    var DEF = { radius: 10, smartRadius: true, smooth: 0, feather: 0, contrast: 0, shiftEdge: 0 };
    var S = { open: false, params: Object.assign({}, DEF), view: 'overlay', output: 'selection', decon: true, deconAmt: 100 };
    var pop = null, ov = null, ui = {}, base = null, baseRef = null, zoneIdx = -1, W = 0, H = 0, guide = null, guideInfo = null, cur = null, timer = 0, watch = 0, heavy = false;

    function ensureStyle() {
        if (document.getElementById('spbTfx3RefineStyle')) return;
        var st = document.createElement('style'); st.id = 'spbTfx3RefineStyle';
        st.textContent = [
            '#spbTfx3RefinePop{position:fixed;z-index:100060;top:132px;right:22px;width:304px;max-height:calc(100vh - 150px);overflow:auto;padding:10px 12px;border:1px solid var(--border,#3a3d45);border-radius:8px;background:var(--bg-panel,#16181d);color:var(--text,#d7d9de);box-shadow:0 10px 30px rgba(0,0,0,.55);font-size:11px;display:none}',
            '#spbTfx3RefinePop h4{margin:0 0 2px;font-size:12px;font-weight:600}',
            '#spbTfx3RefinePop .sub{color:var(--text-dim,#9aa0aa);font-size:10px;margin-bottom:6px;line-height:1.35}',
            '#spbTfx3RefinePop .grp{margin-top:8px;font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-dim,#9aa0aa)}',
            '#spbTfx3RefinePop .seg{display:flex;gap:4px;flex-wrap:wrap;margin-top:4px}',
            '#spbTfx3RefinePop .seg button{padding:2px 7px;font-size:10px;border:1px solid var(--border,#3a3d45);border-radius:4px;background:var(--bg-input,#1c1e24);color:inherit;cursor:pointer}',
            '#spbTfx3RefinePop .seg button.on{border-color:var(--accent,#6ea8fe);box-shadow:0 0 0 1px var(--accent,#6ea8fe)}',
            '#spbTfx3RefinePop .sl{display:grid;grid-template-columns:116px 1fr 40px;align-items:center;gap:6px;margin-top:6px}',
            '#spbTfx3RefinePop .sl input[type=range]{width:100%;margin:0}',
            '#spbTfx3RefinePop .sl output{text-align:right;color:var(--text-dim,#9aa0aa);font-variant-numeric:tabular-nums}',
            '#spbTfx3RefinePop label.ck{display:flex;gap:6px;align-items:center;margin-top:6px;cursor:pointer}',
            '#spbTfx3RefinePop .btns{display:flex;gap:6px;margin-top:10px}',
            '#spbTfx3RefinePop .btns button{flex:1;padding:5px 6px;font-size:11px;border:1px solid var(--border,#3a3d45);border-radius:5px;background:var(--bg-input,#1c1e24);color:inherit;cursor:pointer}',
            '#spbTfx3RefinePop .btns button.pri{background:var(--accent,#6ea8fe);color:#0b0d12;border-color:var(--accent,#6ea8fe);font-weight:600}',
            '#spbTfx3RefinePop .info{margin-top:8px;color:var(--text-dim,#9aa0aa);font-size:10px;min-height:14px}'
        ].join('\n');
        document.head.appendChild(st);
    }
    function sliderRow(label, key, min, max, step, unit) {
        return '<div class="sl"><span>' + label + '</span><input type="range" data-k="' + key + '" min="' + min + '" max="' + max + '" step="' + step + '"><output data-o="' + key + '"></output></div>';
    }
    function build() {
        if (pop) return;
        ensureStyle();
        pop = document.createElement('div'); pop.id = 'spbTfx3RefinePop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', 'Refine Edge');
        pop.innerHTML = '<h4>Refine Edge</h4><div class="sub">Make the selection follow the real edge of a logo or number. Changes show live; nothing is final until you press Apply.</div>' +
            '<div class="grp">View</div><div class="seg" id="spbTfx3RefView"><button data-v="overlay">Red overlay</button><button data-v="white">On white</button><button data-v="black">On black</button><button data-v="mask">Mask only</button></div>' +
            '<div class="grp">Edge</div>' +
            sliderRow('Edge radius', 'radius', 0, 64, 1) +
            '<label class="ck"><input type="checkbox" data-k="smartRadius"> Smart radius (soft and sharp edges)</label>' +
            '<div class="grp">Adjust</div>' +
            sliderRow('Smooth', 'smooth', 0, 100, 1) + sliderRow('Feather', 'feather', 0, 100, 0.5) + sliderRow('Contrast', 'contrast', 0, 100, 1) + sliderRow('Shift edge', 'shiftEdge', -100, 100, 1) +
            '<div class="grp">Apply to</div><div class="seg" id="spbTfx3RefOut"><button data-o="selection">Selection</button><button data-o="layer">New layer (cut-out)</button></div>' +
            '<label class="ck" id="spbTfx3RefDeconL"><input type="checkbox" id="spbTfx3RefDecon"> Clean the edge colours of the cut-out</label>' +
            '<div class="btns"><button type="button" id="spbTfx3RefReset">Reset</button><button type="button" id="spbTfx3RefCancel">Cancel</button><button type="button" class="pri" id="spbTfx3RefApply">Apply</button></div>' +
            '<div class="info" id="spbTfx3RefInfo"></div>';
        document.body.appendChild(pop);
        ui.info = pop.querySelector('#spbTfx3RefInfo');
        Array.prototype.forEach.call(pop.querySelectorAll('input[type=range]'), function (el) {
            var evn = 'input';
            el.addEventListener(evn, function () { S.params[el.dataset.k] = Number(el.value); syncOut(); if (!heavy) schedule(); });
            el.addEventListener('change', function () { S.params[el.dataset.k] = Number(el.value); syncOut(); recalc(); });
        });
        pop.querySelector('input[data-k=smartRadius]').addEventListener('change', function (e) { S.params.smartRadius = !!e.target.checked; recalc(); });
        pop.querySelector('#spbTfx3RefView').addEventListener('click', function (e) { var b = e.target.closest('button[data-v]'); if (!b) return; S.view = b.dataset.v; syncUi(); draw(); });
        pop.querySelector('#spbTfx3RefOut').addEventListener('click', function (e) { var b = e.target.closest('button[data-o]'); if (!b) return; S.output = b.dataset.o; syncUi(); });
        pop.querySelector('#spbTfx3RefDecon').addEventListener('change', function (e) { S.decon = !!e.target.checked; });
        pop.querySelector('#spbTfx3RefReset').addEventListener('click', function () { S.params = Object.assign({}, DEF); syncUi(); recalc(); });
        pop.querySelector('#spbTfx3RefCancel').addEventListener('click', cancel);
        pop.querySelector('#spbTfx3RefApply').addEventListener('click', apply);
        pop.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); cancel(); } else if (e.key === 'Enter' && e.target.tagName !== 'BUTTON') { e.stopPropagation(); apply(); } });
    }
    function syncOut() {
        Array.prototype.forEach.call(pop.querySelectorAll('output[data-o]'), function (o) { var k = o.dataset.o, v = S.params[k]; o.textContent = (k === 'feather' ? v + ' px' : (k === 'radius' ? v + ' px' : v + (k === 'shiftEdge' || k === 'smooth' || k === 'contrast' ? '%' : ''))); });
    }
    function syncUi() {
        Array.prototype.forEach.call(pop.querySelectorAll('input[type=range]'), function (el) { el.value = S.params[el.dataset.k]; });
        pop.querySelector('input[data-k=smartRadius]').checked = !!S.params.smartRadius;
        Array.prototype.forEach.call(pop.querySelectorAll('#spbTfx3RefView button'), function (b) { b.classList.toggle('on', b.dataset.v === S.view); });
        Array.prototype.forEach.call(pop.querySelectorAll('#spbTfx3RefOut button'), function (b) { b.classList.toggle('on', b.dataset.o === S.output); });
        pop.querySelector('#spbTfx3RefDecon').checked = S.decon;
        pop.querySelector('#spbTfx3RefDeconL').style.display = S.output === 'layer' ? 'flex' : 'none';
        syncOut();
    }

    // ------------------------------------------------------------------ overlay
    function pcv() { return document.getElementById('paintCanvas'); }
    function overlay() {
        var pc = pcv(); if (!pc) return null;
        if (!ov) {
            var tc = document.getElementById('transformCanvas'), host = (tc && tc.parentNode) || pc.parentNode; if (!host) return null;
            ov = document.createElement('canvas'); ov.id = 'spbTfx3RefinePrev'; ov.setAttribute('aria-hidden', 'true');
            ov.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:15;display:none;';
            host.appendChild(ov);
        }
        if (ov.width !== pc.width) ov.width = pc.width; if (ov.height !== pc.height) ov.height = pc.height;
        ov.style.width = pc.style.width; ov.style.height = pc.style.height;
        return ov;
    }
    function hideOverlay() { if (ov) { ov.style.display = 'none'; try { ov.getContext('2d').clearRect(0, 0, ov.width, ov.height); } catch (_e) { } } }
    function draw() {
        var o = overlay(); if (!o || !cur || !cur.win) return;
        var x = o.getContext('2d'), w = cur.win, ww = w.x1 - w.x0, wh = w.y1 - w.y0, m = cur.mask, img = x.createImageData(ww, wh), d = img.data, i = 0, X, Y;
        x.clearRect(0, 0, o.width, o.height);
        var G = guide, v = S.view;
        if (v === 'overlay') { x.fillStyle = 'rgba(255,40,40,0.5)'; x.fillRect(0, 0, o.width, o.height); }
        else { x.fillStyle = v === 'white' ? '#fff' : '#000'; x.fillRect(0, 0, o.width, o.height); }
        var bgc = v === 'white' ? 255 : 0;
        for (Y = w.y0; Y < w.y1; Y++) for (X = w.x0; X < w.x1; X++, i += 4) {
            var mv = m[Y * W + X] / 255;
            if (v === 'overlay') { d[i] = 255; d[i + 1] = 40; d[i + 2] = 40; d[i + 3] = Math.round(127.5 * (1 - mv)); }
            else if (v === 'mask') { var g = Math.round(255 * mv); d[i] = d[i + 1] = d[i + 2] = g; d[i + 3] = 255; }
            else {
                var q = (Y * W + X) * 4, ga = G ? G[q + 3] / 255 * mv : mv;
                d[i] = G ? G[q] * ga + bgc * (1 - ga) : 128; d[i + 1] = G ? G[q + 1] * ga + bgc * (1 - ga) : 128; d[i + 2] = G ? G[q + 2] * ga + bgc * (1 - ga) : 128; d[i + 3] = 255;
            }
        }
        if (v === 'overlay') x.clearRect(w.x0, w.y0, ww, wh);   // the window is drawn per pixel below
        x.putImageData(img, w.x0, w.y0);
        o.style.display = 'block';
    }

    // ------------------------------------------------------------------ compute
    function schedule() { if (timer) clearTimeout(timer); timer = setTimeout(function () { timer = 0; recalc(); }, 70); }
    function recalc() {
        if (!S.open || !base) return;
        if (timer) { clearTimeout(timer); timer = 0; }
        try {
            cur = core.refineMask(base, W, H, guide, S.params);
            S.last = { changed: cur.changed, soft: cur.soft, ms: Math.round(cur.ms), tiles: cur.tiles, win: cur.win };
            var ww = cur.win ? cur.win.x1 - cur.win.x0 : 0, wh = cur.win ? cur.win.y1 - cur.win.y0 : 0;
            if (ui.info) ui.info.textContent = ww + ' x ' + wh + ' px area, ' + cur.soft.toLocaleString() + ' soft edge pixels, ' + Math.round(cur.ms) + ' ms';
            draw();
        } catch (e) { if (ui.info) ui.info.textContent = 'Could not refine this selection'; try { console.warn('[refine]', e); } catch (_e) { } }
    }

    // ------------------------------------------------------------------ open / close / apply
    function captureGuide() {
        var pc = pcv(); guide = null; guideInfo = { sourceTarget: 'composite', sourceLayerId: null };
        try {
            var info = (typeof _getActiveSelectionInfo === 'function') ? _getActiveSelectionInfo() : null;
            if (info && typeof _getSelectionSourceData === 'function') {
                var src = _getSelectionSourceData(info);
                if (src && src.sourceData) { guide = src.sourceData; guideInfo = { sourceTarget: src.sourceTarget, sourceLayerId: src.sourceLayer ? src.sourceLayer.id : null }; return; }
            }
        } catch (_e) { }
        try { var x = pc.getContext('2d', { willReadFrequently: true }); guide = x.getImageData(0, 0, pc.width, pc.height).data; } catch (_e2) { guide = null; }
    }
    function open() {
        if (off()) return false;
        var pc = pcv(), z = (typeof zones !== 'undefined' && typeof selectedZoneIndex === 'number') ? zones[selectedZoneIndex] : null;
        if (!pc || !z || !z.regionMask) { toast('Make a selection first (Wand, Lasso or Marquee), then choose Refine Edge', 'info'); return false; }
        if (S.open) close(true);
        build();
        zoneIdx = selectedZoneIndex; baseRef = z.regionMask; base = new Uint8Array(z.regionMask); W = pc.width; H = pc.height;
        if (!core.bounds(base, W, H)) { toast('The selection is empty', 'info'); return false; }
        captureGuide();
        var bb = core.bounds(base, W, H), area = (bb.x1 - bb.x0) * (bb.y1 - bb.y0);
        heavy = area > 1500000;   // very large selections refine on release instead of on every slider move
        S.open = true; S.params = Object.assign({}, DEF); syncUi();
        pop.style.display = 'block';
        recalc();
        clearInterval(watch);
        watch = setInterval(function () {
            if (!S.open) return;
            var zz = (typeof zones !== 'undefined') ? zones[zoneIdx] : null;
            if (!zz || zz.regionMask !== baseRef || (typeof selectedZoneIndex === 'number' && selectedZoneIndex !== zoneIdx)) { close(true); toast('The selection changed, so Refine Edge was closed', 'info'); }
        }, 400);
        return true;
    }
    function close(silent) {
        S.open = false; clearInterval(watch); watch = 0; if (timer) { clearTimeout(timer); timer = 0; }
        if (pop) pop.style.display = 'none';
        hideOverlay(); cur = null; base = null; baseRef = null; guide = null;
    }
    function cancel() { close(true); }
    function cutoutLayer(res) {
        var w = res.win, bb = core.bounds(res.mask, W, H); if (!bb) return null;
        var cw = bb.x1 - bb.x0, ch = bb.y1 - bb.y0, rgba = new Uint8ClampedArray(cw * ch * 4), al = new Uint8Array(cw * ch), x, y;
        for (y = 0; y < ch; y++) for (x = 0; x < cw; x++) {
            var s = ((y + bb.y0) * W + (x + bb.x0)) * 4, d = (y * cw + x) * 4;
            rgba[d] = guide[s]; rgba[d + 1] = guide[s + 1]; rgba[d + 2] = guide[s + 2]; rgba[d + 3] = guide[s + 3];
            al[y * cw + x] = res.mask[(y + bb.y0) * W + (x + bb.x0)];
        }
        var cl = S.decon ? core.decontaminate(rgba, al, cw, ch, Math.max(3, S.params.radius), S.deconAmt) : rgba;
        for (var i = 0; i < cw * ch; i++) cl[i * 4 + 3] = Math.round(rgba[i * 4 + 3] * al[i] / 255);
        return { width: cw, height: ch, imageData: new ImageData(cl, cw, ch), offsetX: bb.x0, offsetY: bb.y0, sourceTarget: guideInfo.sourceTarget, sourceLayerId: guideInfo.sourceLayerId };
    }
    function apply() {
        if (!S.open || !cur) return false;
        var res = cur, out = S.output, ok = false;
        if (out === 'layer') {
            if (typeof _createLayerFromClipboardData !== 'function') { toast('Cut-out is not available here', 'warn'); return false; }
            var data = cutoutLayer(res);
            if (!data) { toast('Nothing is left after refining', 'info'); return false; }
            var nm = (typeof _nextUniqueLayerName === 'function') ? _nextUniqueLayerName('Cut-out') : 'Cut-out';
            var L = _createLayerFromClipboardData(data, { name: nm, idPrefix: 'refine_', undoLabel: 'refine edge cut-out', insertAboveSource: true });
            ok = !!L;
            if (ok) toast('Cut-out layer added with a clean edge (' + data.width + ' x ' + data.height + ' px)');
        } else {
            if (typeof window.__tfx3RefineCommit !== 'function') { toast('Refine Edge could not reach the selection', 'warn'); return false; }
            ok = !!window.__tfx3RefineCommit(res.mask, 'Refined the selection edge · ' + res.soft.toLocaleString() + ' soft edge pixels');
        }
        S.lastApplied = { output: out, ok: ok, changed: res.changed, soft: res.soft };
        if (ok) close(true);
        return ok;
    }

    // the Mask menu is rebuilt at load (tool-workflow.js): Grow / Shrink / Feather / Smooth sit in a visible "Modify selection" group and the original buttons
    // are folded away. Put Refine edge next to Smooth edges so it is as easy to reach as they are.
    function syncMenu() {
        try {
            var b = document.getElementById('vtRefineEdge'); if (!b) return;
            if (off()) b.style.setProperty('display', 'none', 'important'); else b.style.removeProperty('display');   // .vtool-btn can carry display:flex !important
            if (off()) { if (S.open) close(true); return; }
            var lab = Array.prototype.find.call(document.querySelectorAll('.spb-tb-pop-label'), function (l) { return l.textContent.trim() === 'Modify selection'; });
            if (!lab) return;
            var pop = lab.parentNode, sm = Array.prototype.find.call(pop.children, function (e) { return e.tagName === 'BUTTON' && /^Smooth edges/.test(e.textContent.trim()); });
            if (sm && (b.parentNode !== pop || sm.nextSibling !== b)) { b.textContent = 'Refine edge…'; b.removeAttribute('aria-label'); pop.insertBefore(b, sm.nextSibling); }
        } catch (_e) { }
    }
    syncMenu(); setInterval(syncMenu, 1500);
    window.SPBTfx3Refine = {
        open: open, close: cancel, apply: apply,
        set: function (o) { if (!S.open) return false; Object.keys(o || {}).forEach(function (k) { if (k === 'view' || k === 'output' || k === 'decon' || k === 'deconAmt') S[k] = o[k]; else S.params[k] = o[k]; }); syncUi(); recalc(); draw(); return true; },
        state: function () { return { open: S.open, params: Object.assign({}, S.params), view: S.view, output: S.output, decon: S.decon, last: S.last || null, lastApplied: S.lastApplied || null, heavy: heavy }; },
        result: function () { return cur; }, guide: function () { return guide; }, base: function () { return base; }
    };
})();
