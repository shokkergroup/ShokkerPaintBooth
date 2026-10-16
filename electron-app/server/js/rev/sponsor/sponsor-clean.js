/* sponsor-clean.js - [SPB-REV-SPONSOR 2026-10-10] CLEAN: take the white box (or any flat box) and the JPEG halo off a ripped logo.
 *
 * Why it is not just "magic wand + delete": a wand leaves a ring of light-grey / off-white pixels around every letter (anti-aliasing and JPEG ringing
 * are mixes of logo colour and box colour). On a yellow car that ring is a visible white outline. This module
 *   1. finds the box colour from the image border (or, if the image already has a transparent border, uses that),
 *   2. floods the box from the outside with the SAME wand maths the Wand tool uses (SPBPcSelection.wandRegion, contiguous, tolerance in levels),
 *      so white that is INSIDE the logo (fingers of a hand, counters of an O) is kept unless "Clear Enclosed Areas" is on,
 *   3. un-mixes the edge band: for every pixel within `halo` px of the removed box the logo's own colour F is taken from the most box-different pixel nearby
 *      and the pixel becomes colour F with alpha = how far it sits from the box colour towards F. White fringes turn into a clean anti-aliased edge,
 *   4. drops stray specks, trims to the logo.
 * Pure functions on RGBA arrays (no DOM) so it can be unit-tested in Node. Browser helpers (decode PNG / JPG / SVG, read a layer) are at the bottom.
 * Kill switch: window.SPB_REV_SPONSOR_OFF (checked by core / ui, not here).
 */
(function (root, factory) {
    var api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SpbRevSponsorClean = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';
    var VER = 'sc1.0';

    function wandApi(opts) {
        if (opts && opts.wand) return opts.wand;
        if (root && root.SPBPcSelection && root.SPBPcSelection.wandRegion) return root.SPBPcSelection;
        try { if (typeof require === 'function') return require('../../canvas/pc-selection-core.js'); } catch (e) {}
        return null;
    }
    function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

    // ---------------------------------------------------------------- 1. what is the box
    /** Border statistics: transparent border share, dominant opaque border colour, how flat it is. */
    function borderProbe(d, w, h) {
        var t = Math.max(1, Math.min(3, Math.round(Math.min(w, h) / 200))), n = 0, tr = 0, hist = new Uint32Array(32768), idx = [], x, y;
        function take(i) {
            var o = i * 4; n++;
            if (d[o + 3] < 40) { tr++; return; }
            var b = ((d[o] >> 3) << 10) | ((d[o + 1] >> 3) << 5) | (d[o + 2] >> 3); hist[b]++; idx.push(i);
        }
        for (y = 0; y < h; y++) {
            var edgeRow = y < t || y >= h - t;
            for (x = 0; x < w; x++) { if (edgeRow || x < t || x >= w - t) take(y * w + x); }
        }
        var best = -1, bc = 0; for (var b2 = 0; b2 < 32768; b2++) if (hist[b2] > bc) { bc = hist[b2]; best = b2; }
        var out = { n: n, transFrac: n ? tr / n : 0, bg: null, flat: 0, sigma: 0 };
        if (best < 0) return out;
        var sr = 0, sg = 0, sb = 0, m = 0, i;
        for (i = 0; i < idx.length; i++) { var o2 = idx[i] * 4, bb = ((d[o2] >> 3) << 10) | ((d[o2 + 1] >> 3) << 5) | (d[o2 + 2] >> 3); if (bb === best) { sr += d[o2]; sg += d[o2 + 1]; sb += d[o2 + 2]; m++; } }
        var G = [Math.round(sr / m), Math.round(sg / m), Math.round(sb / m)], near = 0, v0 = 0, v1 = 0, v2 = 0;
        for (i = 0; i < idx.length; i++) {
            var o3 = idx[i] * 4, dr = d[o3] - G[0], dg = d[o3 + 1] - G[1], db = d[o3 + 2] - G[2];
            if (Math.abs(dr) <= 30 && Math.abs(dg) <= 30 && Math.abs(db) <= 30) { near++; v0 += dr * dr; v1 += dg * dg; v2 += db * db; }
        }
        out.bg = G; out.flat = near / Math.max(1, n); out.sigma = near ? Math.sqrt(Math.max(v0, v1, v2) / near) : 0;
        return out;
    }

    // ---------------------------------------------------------------- 2. flood the box with the Wand maths
    function floodBox(rgba, w, h, G, tol, contiguous, wand) {
        var pw = w + 2, ph = h + 2, p = new Uint8ClampedArray(pw * ph * 4), x, y, i;
        for (i = 0; i < pw * ph; i++) { p[i * 4] = G[0]; p[i * 4 + 1] = G[1]; p[i * 4 + 2] = G[2]; p[i * 4 + 3] = 255; }
        for (y = 0; y < h; y++) p.set(rgba.subarray(y * w * 4, (y + 1) * w * 4), ((y + 1) * pw + 1) * 4);
        var r = wand.wandRegion(p, pw, ph, 0, 0, { tolerance: tol, contiguous: contiguous, antiAlias: false, target: { r: G[0], g: G[1], b: G[2], a: 255 } });
        var B = new Uint8Array(w * h);
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) B[y * w + x] = r.core[(y + 1) * pw + x + 1] ? 1 : 0;
        return B;
    }
    function floodAlpha(d, w, h, tol, wand) {
        var pw = w + 2, ph = h + 2, p = new Uint8ClampedArray(pw * ph * 4), x, y;
        for (y = 0; y < h; y++) p.set(d.subarray(y * w * 4, (y + 1) * w * 4), ((y + 1) * pw + 1) * 4);
        var r = wand.wandRegion(p, pw, ph, 0, 0, { tolerance: tol, contiguous: true, antiAlias: false, target: { r: 0, g: 0, b: 0, a: 0 }, alphaZeroEqual: true });
        // wandRegion with alphaZeroEqual treats every alpha-0 pixel as the same; alpha 1..tol also counts (same rule as the Wand tool)
        var B = new Uint8Array(w * h);
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) B[y * w + x] = (r.core[(y + 1) * pw + x + 1] && d[(y * w + x) * 4 + 3] <= tol) ? 1 : 0;
        return B;
    }

    // ---------------------------------------------------------------- 3. the edge band
    var DX8 = [-1, 0, 1, -1, 1, -1, 0, 1], DY8 = [-1, -1, -1, 0, 0, 1, 1, 1];
    /** Chebyshev distance (1..cap) from the box for the non-box pixels next to it; 0 elsewhere. */
    function bandDist(B, w, h, cap) {
        var dist = new Uint8Array(w * h), q = new Int32Array(w * h), qh = 0, qt = 0, x, y, k, i;
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
            i = y * w + x; if (!B[i]) continue;
            for (k = 0; k < 8; k++) { var nx = x + DX8[k], ny = y + DY8[k]; if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue; var j = ny * w + nx; if (!B[j] && !dist[j]) { dist[j] = 1; q[qt++] = j; } }
        }
        while (qh < qt) {
            i = q[qh++]; var dv = dist[i]; if (dv >= cap) continue; x = i % w; y = (i / w) | 0;
            for (k = 0; k < 8; k++) { var nx2 = x + DX8[k], ny2 = y + DY8[k]; if (nx2 < 0 || ny2 < 0 || nx2 >= w || ny2 >= h) continue; var j2 = ny2 * w + nx2; if (!B[j2] && !dist[j2]) { dist[j2] = dv + 1; q[qt++] = j2; } }
        }
        return dist;
    }

    /** Remove small opaque islands (JPEG noise that escaped the tolerance). Returns pixels dropped. */
    function dropSpecks(A, w, h, minArea) {
        var lab = new Int32Array(w * h), st = new Int32Array(w * h), cur = 0, dropped = 0, i;
        for (i = 0; i < w * h; i++) {
            if (!A[i] || lab[i]) continue; cur++;
            var sp = 0, cnt = 0, members = []; st[sp++] = i; lab[i] = cur;
            while (sp) {
                var q = st[--sp]; cnt++; if (cnt <= minArea) members.push(q);
                var qx = q % w, qy = (q / w) | 0;
                if (qx > 0 && A[q - 1] && !lab[q - 1]) { lab[q - 1] = cur; st[sp++] = q - 1; }
                if (qx < w - 1 && A[q + 1] && !lab[q + 1]) { lab[q + 1] = cur; st[sp++] = q + 1; }
                if (qy > 0 && A[q - w] && !lab[q - w]) { lab[q - w] = cur; st[sp++] = q - w; }
                if (qy < h - 1 && A[q + w] && !lab[q + w]) { lab[q + w] = cur; st[sp++] = q + w; }
            }
            if (cnt < minArea) { for (var m = 0; m < members.length; m++) A[members[m]] = 0; dropped += cnt; }
        }
        return dropped;
    }

    // ---------------------------------------------------------------- the clean
    /**
     * @param src RGBA bytes (w*h*4), not modified
     * @param opts { tol: 0 = auto | 1..80 levels, halo: 0..4 px (default 2), enclosed: bool (clear enclosed box-coloured areas), bg: [r,g,b] to force the box colour, trim: bool (default true), wand }
     * @returns { data, w, h, info }  info.mode = 'colour' | 'alpha' | 'none', info.reason explains 'none'
     */
    function clean(src, w, h, opts) {
        opts = opts || {};
        var wand = wandApi(opts), halo = clamp(opts.halo == null ? 2 : Math.round(opts.halo), 0, 4), info = { v: VER, mode: 'none', bg: null, tol: 0, halo: halo, removed: 0, band: 0, specks: 0, enclosed: 0, box: null, reason: '' };
        if (!wand) { info.reason = 'The selection core is not loaded.'; return { data: new Uint8ClampedArray(src), w: w, h: h, info: info }; }
        var probe = borderProbe(src, w, h), G = null, mode = 'none', i, k, x, y;
        if (opts.bg && opts.bg.length === 3) { G = [opts.bg[0] | 0, opts.bg[1] | 0, opts.bg[2] | 0]; mode = 'colour'; }
        else if (probe.transFrac >= 0.6) { mode = 'alpha'; }
        else if (probe.bg && probe.flat >= 0.55) { G = probe.bg; mode = 'colour'; }
        else if (probe.bg && probe.transFrac < 0.05 && probe.flat >= 0.35 && Math.min(probe.bg[0], probe.bg[1], probe.bg[2]) > 225) { G = probe.bg; mode = 'colour'; }   // a white box with a busy edge
        if (mode === 'none') {
            info.reason = 'No plain background was found around the edge. Click the background in the left picture to pick its colour.';
            return { data: new Uint8ClampedArray(src), w: w, h: h, info: info };
        }
        var tol = opts.tol > 0 ? clamp(Math.round(opts.tol), 1, 80) : clamp(Math.round(2.6 * probe.sigma + 10), 12, 46);
        info.tol = tol; info.bg = G;
        var out = new Uint8ClampedArray(w * h * 4), N = w * h, B, flat = src;

        if (mode === 'colour') {
            // semi-transparent pixels are mixed with the box colour first, so every pixel is one flat colour
            var needFlat = false; for (i = 3; i < src.length; i += 4) if (src[i] < 255) { needFlat = true; break; }
            if (needFlat) {
                flat = new Uint8ClampedArray(src.length);
                for (i = 0; i < N; i++) { var a = src[i * 4 + 3] / 255; for (k = 0; k < 3; k++) flat[i * 4 + k] = Math.round(src[i * 4 + k] * a + G[k] * (1 - a)); flat[i * 4 + 3] = 255; }
            }
            B = floodBox(flat, w, h, G, tol, true, wand);
            if (opts.enclosed) { var B2 = floodBox(flat, w, h, G, tol, false, wand); for (i = 0; i < N; i++) if (B2[i] && !B[i]) { B[i] = 1; info.enclosed++; } }
        } else {
            B = floodAlpha(src, w, h, 8, wand);
        }
        var cnt = 0; for (i = 0; i < N; i++) if (B[i]) cnt++;
        info.removed = cnt;
        if (cnt < N * 0.01) { info.reason = 'The background looks too small or too detailed to remove (' + cnt + ' px matched).'; return { data: new Uint8ClampedArray(src), w: w, h: h, info: info }; }
        if (cnt > N * 0.995) { info.reason = 'Everything matched the background colour: lower the Tolerance.'; return { data: new Uint8ClampedArray(src), w: w, h: h, info: info }; }

        var cap = Math.max(1, halo), dist = bandDist(B, w, h, cap), R = halo + 1, band = 0;
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
            i = y * w + x; var o = i * 4;
            if (B[i]) continue;                                                       // box: transparent (left zero)
            var dv = dist[i], cr = flat[o], cg = flat[o + 1], cb = flat[o + 2], ca = mode === 'alpha' ? src[o + 3] : 255;
            if (!dv || halo === 0) { out[o] = cr; out[o + 1] = cg; out[o + 2] = cb; out[o + 3] = ca; continue; }
            band++;
            if (mode === 'colour') {
                // F = the most box-different pixel of the logo near this one = the logo's own colour for this stretch of edge
                var fb = -1, fr = cr, fg = cg, fbl = cb;
                for (var yy = Math.max(0, y - R); yy <= Math.min(h - 1, y + R); yy++) for (var xx = Math.max(0, x - R); xx <= Math.min(w - 1, x + R); xx++) {
                    var j = yy * w + xx; if (B[j]) continue; var oj = j * 4, dr = flat[oj] - G[0], dg = flat[oj + 1] - G[1], db = flat[oj + 2] - G[2], dd = dr * dr + dg * dg + db * db;
                    if (dd > fb) { fb = dd; fr = flat[oj]; fg = flat[oj + 1]; fbl = flat[oj + 2]; }
                }
                var vr = fr - G[0], vg = fg - G[1], vb = fbl - G[2], vv = vr * vr + vg * vg + vb * vb, al;
                if (vv < 40 * 40 * 3 / 3) {                                            // logo colour too close to the box colour to un-mix: keep, but fade by distance to the box
                    al = Math.max(Math.abs(cr - G[0]), Math.abs(cg - G[1]), Math.abs(cb - G[2])) <= tol * 0.6 ? 0 : 1;
                } else {
                    al = ((cr - G[0]) * vr + (cg - G[1]) * vg + (cb - G[2]) * vb) / vv;
                    // a pixel that is not on the box->logo line (a real outline colour, not a mix) stays itself
                    var ex = G[0] + al * vr - cr, ey = G[1] + al * vg - cg, ez = G[2] + al * vb - cb;
                    if (Math.sqrt(ex * ex + ey * ey + ez * ez) > 34 + 0.22 * Math.sqrt(vv)) al = 1;
                }
                al = clamp(al, 0, 1);
                if (al < 0.04) { out[o + 3] = 0; }
                else if (al > 0.96) { out[o] = cr; out[o + 1] = cg; out[o + 2] = cb; out[o + 3] = 255; }
                else { out[o] = fr; out[o + 1] = fg; out[o + 2] = fbl; out[o + 3] = Math.round(al * 255); }
            } else {
                // transparent-border image: a light matte on a semi-transparent edge pixel takes the nearest solid logo colour
                if (ca < 250 && Math.min(cr, cg, cb) >= 205) {
                    var best = -1, bdist = 1e9;
                    for (var y3 = Math.max(0, y - R); y3 <= Math.min(h - 1, y + R); y3++) for (var x3 = Math.max(0, x - R); x3 <= Math.min(w - 1, x + R); x3++) {
                        var j3 = y3 * w + x3, o3 = j3 * 4; if (B[j3] || src[o3 + 3] < 250 || Math.min(src[o3], src[o3 + 1], src[o3 + 2]) >= 205) continue;
                        var d2 = (x3 - x) * (x3 - x) + (y3 - y) * (y3 - y); if (d2 < bdist) { bdist = d2; best = o3; }
                    }
                    if (best >= 0) { out[o] = src[best]; out[o + 1] = src[best + 1]; out[o + 2] = src[best + 2]; out[o + 3] = ca; }
                    else { out[o] = cr; out[o + 1] = cg; out[o + 2] = cb; out[o + 3] = ca; }
                } else { out[o] = cr; out[o + 1] = cg; out[o + 2] = cb; out[o + 3] = ca; }
            }
        }
        info.band = band;
        // specks + trim
        var A = new Uint8Array(N); for (i = 0; i < N; i++) A[i] = out[i * 4 + 3] > 8 ? 1 : 0;
        var minA = Math.max(6, Math.round(N * 0.00004));
        info.specks = dropSpecks(A, w, h, minA);
        if (info.specks) for (i = 0; i < N; i++) if (!A[i] && out[i * 4 + 3] > 0 && out[i * 4 + 3] <= 255) { var oo = i * 4; if (out[oo + 3] > 8) { out[oo] = out[oo + 1] = out[oo + 2] = out[oo + 3] = 0; } }
        var x0 = w, y0 = h, x1 = -1, y1 = -1;
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) if (out[(y * w + x) * 4 + 3] > 8) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        if (x1 < 0) { info.mode = 'none'; info.reason = 'Nothing was left after removing the background: raise the Tolerance only if the logo is the same colour as the box.'; return { data: new Uint8ClampedArray(src), w: w, h: h, info: info }; }
        info.mode = mode;
        if (opts.trim === false) { info.box = [0, 0, w, h]; return { data: out, w: w, h: h, info: info }; }
        var pad = 2, X0 = Math.max(0, x0 - pad), Y0 = Math.max(0, y0 - pad), X1 = Math.min(w - 1, x1 + pad), Y1 = Math.min(h - 1, y1 + pad), nw = X1 - X0 + 1, nh = Y1 - Y0 + 1, tr = new Uint8ClampedArray(nw * nh * 4);
        for (y = 0; y < nh; y++) tr.set(out.subarray(((Y0 + y) * w + X0) * 4, ((Y0 + y) * w + X0 + nw) * 4), y * nw * 4);
        info.box = [X0, Y0, X1 + 1, Y1 + 1];
        return { data: tr, w: nw, h: nh, info: info };
    }

    // ---------------------------------------------------------------- measuring the "white junk"
    /** Count of near-white (all channels >= lim) visible pixels in a ring of `ringPx` around the logo's solid pixels.
     *  Works on a canvas-like RGBA array of the LOGO ALONE (alpha defines the logo). Used by the proof and the dialog's before/after note. */
    function whiteEdge(d, w, h, ringPx, lim) {
        ringPx = ringPx || 6; lim = lim || 235; var N = w * h, solid = new Uint8Array(N), i, n = 0;
        for (i = 0; i < N; i++) solid[i] = d[i * 4 + 3] > 128 ? 1 : 0;
        var dist = new Uint8Array(N), q = new Int32Array(N), qh = 0, qt = 0, x, y, k;
        for (i = 0; i < N; i++) if (solid[i]) { dist[i] = 0; q[qt++] = i; } else dist[i] = 255;
        while (qh < qt) { i = q[qh++]; var dv = dist[i]; if (dv >= ringPx) continue; x = i % w; y = (i / w) | 0;
            for (k = 0; k < 8; k++) { var nx = x + DX8[k], ny = y + DY8[k]; if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue; var j = ny * w + nx; if (dist[j] === 255) { dist[j] = dv + 1; q[qt++] = j; } } }
        for (i = 0; i < N; i++) { if (dist[i] >= 1 && dist[i] <= ringPx) { var o = i * 4; if (d[o + 3] > 16 && d[o] >= lim && d[o + 1] >= lim && d[o + 2] >= lim) n++; } }
        return n;
    }

    // ---------------------------------------------------------------- browser helpers: decode a file / read a layer
    var MAXW = 1600;
    function readFile(file) {
        return new Promise(function (res, rej) { var fr = new FileReader(); fr.onload = function () { res(fr.result); }; fr.onerror = function () { rej(new Error('Could not read the file.')); }; fr.readAsDataURL(file); });
    }
    function loadImg(url) { return new Promise(function (res, rej) { var im = new Image(); im.onload = function () { res(im); }; im.onerror = function () { rej(new Error('This image could not be opened.')); }; im.src = url; }); }
    function toCanvas(im, w, h) {
        var cv = root.document.createElement('canvas'), s = Math.min(1, MAXW / Math.max(w, h)); cv.width = Math.max(1, Math.round(w * s)); cv.height = Math.max(1, Math.round(h * s));
        var g = cv.getContext('2d', { willReadFrequently: true }); g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(im, 0, 0, cv.width, cv.height); return cv;
    }
    /** File (PNG / JPG / SVG / GIF / WebP) or data URL -> { canvas, name, kind, w, h } (long side capped at 1600). */
    function decode(file) {
        var name = (file && file.name) || 'Logo', isSvg = /svg/i.test((file && file.type) || '') || /\.svg$/i.test(name);
        var p = typeof file === 'string' ? Promise.resolve(file) : readFile(file);
        return p.then(function (url) {
            if (isSvg && typeof file !== 'string') {
                return fetch(url).then(function (r) { return r.text(); }).then(function (txt) {
                    var m = /viewBox\s*=\s*["']\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)/i.exec(txt), wm = /<svg[^>]*\swidth\s*=\s*["']([\d.]+)/i.exec(txt), hm = /<svg[^>]*\sheight\s*=\s*["']([\d.]+)/i.exec(txt);
                    var w0 = wm ? +wm[1] : (m ? +m[1] : 1024), h0 = hm ? +hm[1] : (m ? +m[2] : 1024), s = 1280 / Math.max(w0, h0, 1);
                    var t2 = txt;
                    if (!/<svg[^>]*\swidth\s*=/i.test(t2)) t2 = t2.replace(/<svg/i, '<svg width="' + Math.round(w0 * s) + '" height="' + Math.round(h0 * s) + '"');
                    else t2 = t2.replace(/(<svg[^>]*\s)width\s*=\s*["'][^"']*["']/i, '$1width="' + Math.round(w0 * s) + '"').replace(/(<svg[^>]*\s)height\s*=\s*["'][^"']*["']/i, '$1height="' + Math.round(h0 * s) + '"');
                    return loadImg('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(t2)).then(function (im) { return { canvas: toCanvas(im, im.naturalWidth || Math.round(w0 * s), im.naturalHeight || Math.round(h0 * s)), name: name, kind: 'svg' }; });
                });
            }
            return loadImg(url).then(function (im) { return { canvas: toCanvas(im, im.naturalWidth || im.width, im.naturalHeight || im.height), name: name, kind: /jpe?g/i.test((file && file.type) || name) ? 'jpg' : 'png' }; });
        });
    }
    /** A paint layer (img + bbox) -> canvas of its visible pixels, tight to the non-transparent area. */
    function fromLayer(layer) {
        var img = layer && layer.img, w = img && (img.naturalWidth || img.width), h = img && (img.naturalHeight || img.height); if (!w || !h) return null;
        var cv = root.document.createElement('canvas'); cv.width = w; cv.height = h; var g = cv.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
        var d = g.getImageData(0, 0, w, h).data, x0 = w, y0 = h, x1 = -1, y1 = -1, x, y;
        for (y = 0; y < h; y++) for (x = 0; x < w; x++) if (d[(y * w + x) * 4 + 3] > 8) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        if (x1 < 0) return null;
        var nw = x1 - x0 + 1, nh = y1 - y0 + 1, s = Math.min(1, MAXW / Math.max(nw, nh)), out = root.document.createElement('canvas'); out.width = Math.max(1, Math.round(nw * s)); out.height = Math.max(1, Math.round(nh * s));
        var og = out.getContext('2d', { willReadFrequently: true }); og.imageSmoothingQuality = 'high'; og.drawImage(cv, x0, y0, nw, nh, 0, 0, out.width, out.height);
        return { canvas: out, name: String(layer.name || 'Layer'), kind: 'layer' };
    }
    /** canvas -> canvas, cleaned. */
    function cleanCanvas(cv, opts) {
        var g = cv.getContext('2d', { willReadFrequently: true }), id = g.getImageData(0, 0, cv.width, cv.height), r = clean(id.data, cv.width, cv.height, opts);
        var out = root.document.createElement('canvas'); out.width = r.w; out.height = r.h; var og = out.getContext('2d'); og.putImageData(new ImageData(r.data, r.w, r.h), 0, 0);
        return { canvas: out, info: r.info, data: r.data, w: r.w, h: r.h };
    }
    function probeCanvas(cv) {
        var g = cv.getContext('2d', { willReadFrequently: true }), d = g.getImageData(0, 0, cv.width, cv.height).data; return borderProbe(d, cv.width, cv.height);
    }

    return { version: VER, clean: clean, borderProbe: borderProbe, whiteEdge: whiteEdge, decode: decode, fromLayer: fromLayer, cleanCanvas: cleanCanvas, probeCanvas: probeCanvas, MAXW: MAXW };
});
