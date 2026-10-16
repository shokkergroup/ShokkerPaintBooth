/* ============================================================================
 * SPB PC SELECTION CORE  (lane PORT-W1, 2026-10-09)
 *
 * Algorithm ported from PhotoCraft crates/algo/src/selection.rs and
 * crates/algo/src/selection_blur.rs
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0
 * (MIT elected) - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript for SPB's Uint8 (0..255) zone masks;
 * heavy ops run only inside the bounding window of the work (typed arrays,
 * no per-pixel closures in the hot loops).
 * Cites (as PhotoCraft does): Felzenszwalb & Huttenlocher, "Distance
 * Transforms of Sampled Functions" (2012) for the Euclidean distance transform.
 *
 * Owner verdict 2026-10-09: "our tools basically SUCK". What this replaces:
 *   - Expand/Contract used a SQUARE structuring element (corners grow as
 *     squares) and binarised soft edges  -> true circular (Euclidean) EDT.
 *   - Feather was a 3-pass box with sigma ~= radius, capped at 12 px (and a
 *     second copy capped at 50 px) -> Gaussian sigma = radius/2, no cap.
 *   - Smooth was morphological open radius 1, UI radius ignored -> box average
 *     radius r + contrast curve (rounds corners, drops specks).
 *   - Lasso/ellipse were hard 0/255 per-pixel tests, O(pixels*verts) -> exact
 *     scanline coverage (4 sub-rows, exact horizontal coverage), AA on edges.
 *   - Wand AA was a colour-distance halo capped at alpha 192 -> geometric 3x3
 *     edge rule (0.5 + 0.5*avg), halo never leaves the 1 px edge.
 *
 * Disable everything with   window.SPB_PC_W1_OFF = true   (callers fall back
 * to their legacy engines).  All masks are Uint8Array(w*h), 0..255.
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcSelection = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const INF = 1e9;

    function clampInt(v, lo, hi) { return Math.max(lo, Math.min(hi, Math.floor(v))); }

    // ---------------------------------------------------------------- bounds
    // Bounding box (x1/y1 exclusive) of pixels with value >= minValue, or null.
    function boundsOf(m, w, h, minValue) {
        let x0 = w, y0 = h, x1 = -1, y1 = -1;
        for (let y = 0; y < h; y++) {
            const row = y * w;
            let first = -1, last = -1;
            for (let x = 0; x < w; x++) {
                if (m[row + x] >= minValue) { first = x; break; }
            }
            if (first < 0) continue;
            for (let x = w - 1; x >= first; x--) {
                if (m[row + x] >= minValue) { last = x; break; }
            }
            if (first < x0) x0 = first;
            if (last > x1) x1 = last;
            if (y < y0) y0 = y;
            y1 = y;
        }
        if (x1 < 0) return null;
        return { x0: x0, y0: y0, x1: x1 + 1, y1: y1 + 1 };
    }

    function growBox(b, g, w, h) {
        return {
            x0: Math.max(0, b.x0 - g), y0: Math.max(0, b.y0 - g),
            x1: Math.min(w, b.x1 + g), y1: Math.min(h, b.y1 + g),
        };
    }

    // ------------------------------------------------- Euclidean distance (EDT)
    // 1D squared distance transform (Felzenszwalb & Huttenlocher).
    function dt1(f, n, out, v, z) {
        let k = 0;
        v[0] = 0; z[0] = -Infinity; z[1] = Infinity;
        for (let q = 1; q < n; q++) {
            let s;
            for (;;) {
                const p = v[k];
                s = ((f[q] + q * q) - (f[p] + p * p)) / (2 * (q - p));
                if (s <= z[k]) k--; else break;
            }
            k++;
            v[k] = q; z[k] = s; z[k + 1] = Infinity;
        }
        k = 0;
        for (let q = 0; q < n; q++) {
            while (z[k + 1] < q) k++;
            const d = q - v[k];
            out[q] = d * d + f[v[k]];
        }
    }

    // Distance (px, centre to centre) from every window pixel to the nearest
    // "inside" pixel of the window. inside = inv ? (v < 128) : (v >= 128).
    // Returns Float32Array(ww*wh) or null when the window has no inside pixel.
    function distanceWindow(m, w, win, inv) {
        const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
        const g = new Float32Array(ww * wh);
        const n = Math.max(ww, wh);
        const f = new Float64Array(n), o = new Float64Array(n);
        const v = new Int32Array(n), z = new Float64Array(n + 1);
        let any = false;
        for (let y = 0; y < wh; y++) {
            const base = (win.y0 + y) * w + win.x0, gi = y * ww;
            let rowAny = false;
            for (let x = 0; x < ww; x++) {
                const val = m[base + x];
                if (inv ? val < 128 : val >= 128) { g[gi + x] = 0; rowAny = true; } else g[gi + x] = INF;
            }
            if (!rowAny) continue;
            any = true;
            for (let x = 0; x < ww; x++) f[x] = g[gi + x];
            dt1(f, ww, o, v, z);
            for (let x = 0; x < ww; x++) g[gi + x] = o[x];
        }
        if (!any) return null;
        for (let x = 0; x < ww; x++) {
            for (let y = 0; y < wh; y++) f[y] = g[y * ww + x];
            dt1(f, wh, o, v, z);
            for (let y = 0; y < wh; y++) g[y * ww + x] = Math.sqrt(o[y]);
        }
        return g;
    }

    // PhotoCraft expand(): v.max(clamp(r + 1 - d, 0, 1)). inv=true runs it on the
    // inverted mask (contract = 1 - expand(1 - m)). Returns a NEW Uint8Array.
    function growSoft(m, w, h, r, inv) {
        const out = new Uint8Array(m);
        r = Number(r);
        if (!(r > 0) || !w || !h) return out;
        const affect = boundsOf(m, w, h, inv ? 1 : 128);
        if (!affect) return out;
        const win = growBox(affect, Math.ceil(r) + 1, w, h);
        const dist = distanceWindow(m, w, win, inv);
        if (!dist) return out;
        const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
        for (let y = 0; y < wh; y++) {
            const base = (win.y0 + y) * w + win.x0, gi = y * ww;
            for (let x = 0; x < ww; x++) {
                const d = dist[gi + x];
                if (d >= r + 1) continue;
                const cov = d <= r ? 255 : Math.round((r + 1 - d) * 255);
                const idx = base + x;
                if (inv) {
                    const baseV = 255 - m[idx];
                    out[idx] = 255 - (cov > baseV ? cov : baseV);
                } else if (cov > m[idx]) out[idx] = cov;
            }
        }
        return out;
    }

    function expand(m, w, h, r) { return growSoft(m, w, h, r, false); }
    function contract(m, w, h, r) { return growSoft(m, w, h, r, true); }

    // A band of width r straddling the selection edge.
    function border(m, w, h, r) {
        const outer = expand(m, w, h, r / 2), inner = contract(m, w, h, r / 2);
        const out = new Uint8Array(m.length);
        for (let i = 0; i < out.length; i++) { const d = outer[i] - inner[i]; out[i] = d > 0 ? d : 0; }
        return out;
    }

    function invert(m) {
        const out = new Uint8Array(m.length);
        for (let i = 0; i < out.length; i++) out[i] = 255 - m[i];
        return out;
    }

    // ------------------------------------------------------- box / gaussian
    // Running-sum box blur of one line of Float32 data. replicate=true clamps the
    // edges (Smooth), false reads zeros beyond the line (Feather).
    function boxLine(src, so, dst, d0, n, r, replicate) {
        let sum = 0;
        for (let j = -r; j <= r; j++) {
            const i = j < 0 ? 0 : (j >= n ? n - 1 : j);
            sum += (replicate || (j >= 0 && j < n)) ? src[so + i] : 0;
        }
        const norm = 1 / (2 * r + 1);
        for (let x = 0; x < n; x++) {
            dst[d0 + x] = sum * norm;
            const a = x + r + 1, b = x - r;
            let add, sub;
            if (replicate) {
                add = src[so + (a >= n ? n - 1 : a)];
                sub = src[so + (b < 0 ? 0 : b)];
            } else {
                add = a < n ? src[so + a] : 0;
                sub = b >= 0 ? src[so + b] : 0;
            }
            sum += add - sub;
        }
    }

    // Vertical box pass, row by row (cache friendly): a window of rows per column.
    function boxV(src, dst, ww, wh, r, replicate) {
        const sums = new Float64Array(ww);
        for (let j = -r; j <= r; j++) {
            if (!replicate && (j < 0 || j >= wh)) continue;
            const ro = (j < 0 ? 0 : (j >= wh ? wh - 1 : j)) * ww;
            for (let x = 0; x < ww; x++) sums[x] += src[ro + x];
        }
        const norm = 1 / (2 * r + 1);
        for (let y = 0; y < wh; y++) {
            const yo = y * ww;
            for (let x = 0; x < ww; x++) dst[yo + x] = sums[x] * norm;
            const a = y + r + 1, b = y - r;
            let ao = -1, bo = -1;
            if (replicate) { ao = (a >= wh ? wh - 1 : a) * ww; bo = (b < 0 ? 0 : b) * ww; }
            else { if (a < wh) ao = a * ww; if (b >= 0) bo = b * ww; }
            if (ao >= 0) for (let x = 0; x < ww; x++) sums[x] += src[ao + x];
            if (bo >= 0) for (let x = 0; x < ww; x++) sums[x] -= src[bo + x];
        }
    }

    function boxBlurWindow(a, ww, wh, r, replicate) {
        if (r <= 0) return a;
        const t = new Float32Array(a.length), o = new Float32Array(a.length);
        for (let y = 0; y < wh; y++) boxLine(a, y * ww, t, y * ww, ww, r, replicate);
        boxV(t, o, ww, wh, r, replicate);
        return o;
    }

    // Windows may extend past the canvas (zeros there) so multi-pass blurs keep the
    // energy that a Gaussian over the zero-extended mask would carry back inside.
    function readWindow(m, w, win, h) {
        const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
        const a = new Float32Array(ww * wh);
        for (let y = 0; y < wh; y++) {
            const sy = win.y0 + y;
            if (sy < 0 || sy >= h) continue;
            const base = sy * w, yo = y * ww;
            const xa = Math.max(0, -win.x0), xb = Math.min(ww, w - win.x0);
            for (let x = xa; x < xb; x++) a[yo + x] = m[base + win.x0 + x];
        }
        return a;
    }

    function writeWindow(out, w, win, a, fn, h) {
        const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
        for (let y = 0; y < wh; y++) {
            const sy = win.y0 + y;
            if (sy < 0 || sy >= h) continue;
            const base = sy * w, yo = y * ww;
            const xa = Math.max(0, -win.x0), xb = Math.min(ww, w - win.x0);
            for (let x = xa; x < xb; x++) {
                let v = fn ? fn(a[yo + x]) : a[yo + x];
                v = v < 0.5 ? 0 : (v > 254.5 ? 255 : Math.round(v));
                out[base + win.x0 + x] = v;
            }
        }
    }

    // Smooth: box average of radius round(r) (edges replicated), then the contrast
    // curve (v - 1/2) * 4 + 1/2 that re-hardens the edge and drops specks.
    function smooth(m, w, h, r) {
        const rad = Math.max(0, Math.round(Number(r) || 0));
        const out = new Uint8Array(m.length);
        const b = boundsOf(m, w, h, 1);
        if (!b) return out;
        const win = growBox(b, rad + 1, w, h);
        const ww = win.x1 - win.x0, wh = win.y1 - win.y0;
        const blurred = boxBlurWindow(readWindow(m, w, win, h), ww, wh, rad, true);
        writeWindow(out, w, win, blurred, function (v) {
            const c = ((v / 255) - 0.5) * 4 + 0.5;
            return (c < 0 ? 0 : (c > 1 ? 1 : c)) * 255;
        }, h);
        return out;
    }

    // Box sizes whose successive blurs approximate a Gaussian of `sigma`
    // (Kutskir's "boxes for gauss", n passes).
    function boxRadiiForGauss(sigma, n) {
        const wIdeal = Math.sqrt((12 * sigma * sigma / n) + 1);
        let wl = Math.floor(wIdeal);
        if (wl % 2 === 0) wl--;
        const wu = wl + 2;
        const mIdeal = (12 * sigma * sigma - n * wl * wl - 4 * n * wl - 3 * n) / (-4 * wl - 4);
        const mm = Math.round(mIdeal);
        const radii = [];
        for (let i = 0; i < n; i++) radii.push(((i < mm ? wl : wu) - 1) / 2);
        return radii;
    }

    // Feather: Gaussian blur with sigma = radius / 2 (Photoshop / PhotoCraft),
    // zero beyond the canvas, confined to the mask's bounding window. Kernels up
    // to 12 px are an exact separable FIR (truncated at ceil(3 sigma),
    // normalised); wider ones are a 4-pass box approximation (<0.5 level error).
    function feather(m, w, h, radius) {
        let sigma = Math.max(0, Number(radius) || 0) / 2;
        const out = new Uint8Array(m);
        if (sigma < 0.1 || !w || !h) return out;
        sigma = Math.min(sigma, 5000);
        const b = boundsOf(m, w, h, 1);
        if (!b) return out;
        const kr = Math.ceil(sigma * 3);
        let a, ww, wh, win;
        if (kr <= 12) {
            win = growBox(b, kr, w, h);
            ww = win.x1 - win.x0; wh = win.y1 - win.y0;
            const k = new Float64Array(2 * kr + 1);
            let ks = 0;
            for (let j = -kr; j <= kr; j++) { k[j + kr] = Math.exp(-(j * j) / (2 * sigma * sigma)); ks += k[j + kr]; }
            for (let j = 0; j < k.length; j++) k[j] /= ks;
            const src = readWindow(m, w, win, h);
            const t = new Float32Array(src.length);
            for (let y = 0; y < wh; y++) {
                const yo = y * ww;
                for (let x = 0; x < ww; x++) {
                    let acc = 0;
                    const j0 = Math.max(-kr, -x), j1 = Math.min(kr, ww - 1 - x);
                    for (let j = j0; j <= j1; j++) acc += src[yo + x + j] * k[j + kr];
                    t[yo + x] = acc;
                }
            }
            a = new Float32Array(src.length);
            for (let y = 0; y < wh; y++) {
                const yo = y * ww;
                const j0 = Math.max(-kr, -y), j1 = Math.min(kr, wh - 1 - y);
                for (let j = j0; j <= j1; j++) {
                    const kv = k[j + kr], so = (y + j) * ww;
                    for (let x = 0; x < ww; x++) a[yo + x] += t[so + x] * kv;
                }
            }
        } else {
            const radii = boxRadiiForGauss(sigma, 4);
            let total = 0;
            for (const r of radii) total += r;
            const g = Math.ceil(total) + 2;
            win = { x0: b.x0 - g, y0: b.y0 - g, x1: b.x1 + g, y1: b.y1 + g };
            ww = win.x1 - win.x0; wh = win.y1 - win.y0;
            a = readWindow(m, w, win, h);
            for (const r of radii) a = boxBlurWindow(a, ww, wh, r, false);
        }
        writeWindow(out, w, win, a, null, h);
        return out;
    }

    // ------------------------------------------------------ polygon coverage
    // Anti-aliased even-odd polygon coverage: 4 sub-rows per pixel row (1 when
    // not anti-aliased), exact horizontal coverage inside each sub-row. Crossings
    // are bucketed per sub-row, so cost is O(vertices + crossings) - a 3000-vertex
    // freehand lasso is as fast as a triangle.
    // points: [{x,y}] or [[x,y]] in canvas pixels. Returns { mask, bbox, area }.
    function polygon(points, w, h, antiAlias) {
        const mask = new Uint8Array(w * h);
        const n = points ? points.length : 0;
        if (n < 3 || !w || !h) return { mask: mask, bbox: null, area: 0 };
        const px = new Float64Array(n), py = new Float64Array(n);
        let minY = Infinity, maxY = -Infinity, minX = Infinity, maxX = -Infinity;
        for (let i = 0; i < n; i++) {
            const p = points[i];
            const x = Array.isArray(p) ? p[0] : p.x, y = Array.isArray(p) ? p[1] : p.y;
            px[i] = x; py[i] = y;
            if (y < minY) minY = y; if (y > maxY) maxY = y;
            if (x < minX) minX = x; if (x > maxX) maxX = x;
        }
        const sub = antiAlias === false ? 1 : 4;
        const inv = 1 / sub;
        const rowLo = Math.max(0, Math.floor(minY)), rowHi = Math.min(h, Math.ceil(maxY));
        if (rowHi <= rowLo || maxX <= 0 || minX >= w) return { mask: mask, bbox: null, area: 0 };
        const kmin = rowLo * sub, kmax = rowHi * sub; // sub-row index range [kmin,kmax)
        const ks = kmax - kmin;
        const counts = new Int32Array(ks + 1);
        // pass 1: count crossings per sub-row
        for (let i = 0; i < n; i++) {
            const j = (i + 1) % n;
            const ya = py[i], yb = py[j];
            if (ya === yb) continue;
            const lo = ya < yb ? ya : yb, hi = ya < yb ? yb : ya;
            const k0 = Math.max(kmin, Math.ceil(lo * sub - 0.5)), k1 = Math.min(kmax, Math.ceil(hi * sub - 0.5));
            for (let k = k0; k < k1; k++) counts[k - kmin + 1]++;
        }
        for (let k = 0; k < ks; k++) counts[k + 1] += counts[k];
        const xs = new Float64Array(counts[ks]);
        const fillPos = new Int32Array(ks);
        // pass 2: store crossing x
        for (let i = 0; i < n; i++) {
            const j = (i + 1) % n;
            const xa = px[i], ya = py[i], xb = px[j], yb = py[j];
            if (ya === yb) continue;
            const lo = ya < yb ? ya : yb, hi = ya < yb ? yb : ya;
            const k0 = Math.max(kmin, Math.ceil(lo * sub - 0.5)), k1 = Math.min(kmax, Math.ceil(hi * sub - 0.5));
            const slope = (xb - xa) / (yb - ya);
            for (let k = k0; k < k1; k++) {
                const y = (k + 0.5) * inv;
                const kk = k - kmin;
                xs[counts[kk] + fillPos[kk]++] = xa + (y - ya) * slope;
            }
        }
        const acc = new Float32Array(w + 2), diff = new Float32Array(w + 2);
        let bx0 = w, bx1 = -1, by0 = h, by1 = -1, area = 0;
        for (let pyRow = rowLo; pyRow < rowHi; pyRow++) {
            let used = false;
            for (let s = 0; s < sub; s++) {
                const kk = (pyRow * sub + s) - kmin;
                const a0 = counts[kk], a1 = counts[kk + 1];
                if (a1 - a0 < 2) continue;
                // insertion sort (rows have few crossings)
                for (let i = a0 + 1; i < a1; i++) {
                    const v = xs[i]; let j = i - 1;
                    while (j >= a0 && xs[j] > v) { xs[j + 1] = xs[j]; j--; }
                    xs[j + 1] = v;
                }
                for (let i = a0; i + 1 < a1; i += 2) {
                    let x0 = xs[i], x1 = xs[i + 1];
                    if (x0 < 0) x0 = 0;
                    if (x1 > w) x1 = w;
                    if (x1 <= x0) continue;
                    used = true;
                    if (sub === 1) {
                        const c0 = Math.ceil(x0 - 0.5), c1 = Math.ceil(x1 - 0.5);
                        if (c1 > c0) { diff[c0] += 1; diff[c1] -= 1; }
                    } else {
                        const c0 = Math.floor(x0), c1 = Math.ceil(x1);
                        if (c1 - c0 <= 1) acc[c0] += (x1 - x0) * inv;
                        else {
                            acc[c0] += (c0 + 1 - x0) * inv;
                            acc[c1 - 1] += (x1 - (c1 - 1)) * inv;
                            if (c1 - 1 > c0 + 1) { diff[c0 + 1] += inv; diff[c1 - 1] -= inv; }
                        }
                    }
                }
            }
            if (!used) continue;
            const ro = pyRow * w;
            let run = 0, rowAny = false;
            for (let x = 0; x < w; x++) {
                run += diff[x];
                let c = acc[x] + run;
                acc[x] = 0; diff[x] = 0;
                if (c > 0.0005) {
                    if (c > 1) c = 1;
                    const b = Math.round(c * 255);
                    if (b > 0) {
                        mask[ro + x] = b; area += b;
                        if (x < bx0) bx0 = x;
                        if (x > bx1) bx1 = x;
                        rowAny = true;
                    }
                }
            }
            acc[w] = acc[w + 1] = 0; diff[w] = diff[w + 1] = 0;
            if (rowAny) { if (pyRow < by0) by0 = pyRow; by1 = pyRow; }
        }
        return {
            mask: mask,
            bbox: bx1 < 0 ? null : { x0: bx0, y0: by0, x1: bx1 + 1, y1: by1 + 1 },
            area: area / 255,
        };
    }

    // Anti-aliased ellipse (centre cx,cy radii rx,ry in pixels) via a polygon dense
    // enough that the chord error is < 0.05 px, inflated so its AREA equals the
    // true ellipse area.
    function ellipse(cx, cy, rx, ry, w, h, antiAlias) {
        rx = Math.abs(rx); ry = Math.abs(ry);
        if (!(rx > 0) || !(ry > 0)) return { mask: new Uint8Array(w * h), bbox: null, area: 0 };
        const R = Math.max(rx, ry);
        const nPts = clampInt(Math.PI / Math.acos(Math.max(0, 1 - 0.05 / Math.max(R, 0.06))), 24, 4096);
        const t = 2 * Math.PI / nPts;
        const inflate = Math.sqrt(t / Math.sin(t));
        const pts = new Array(nPts);
        for (let i = 0; i < nPts; i++) {
            const a = i * t;
            pts[i] = { x: cx + Math.cos(a) * rx * inflate, y: cy + Math.sin(a) * ry * inflate };
        }
        return polygon(pts, w, h, antiAlias);
    }

    // ---------------------------------------------------------------- wand
    // Magic wand on RGBA8: scanline span flood fill (4-connected) or global match,
    // Chebyshev distance over R,G,B,A <= tolerance (PhotoCraft wand_region), then
    // the 3x3 edge anti-alias rule on the touched bounding box only.
    // opts: tolerance (int levels), contiguous (default true), antiAlias (default
    // true), target {r,g,b,a} (default: the seed pixel), alphaZeroEqual (default
    // true: fully transparent pixels are all "the same colour").
    // Returns { core (255 where matched), mask (core + AA fringe), bbox, count }.
    function wandRegion(rgba, w, h, seedXValue, seedYValue, opts) {
        opts = opts || {};
        const sx = clampInt(Number(seedXValue) || 0, 0, w - 1), sy = clampInt(Number(seedYValue) || 0, 0, h - 1);
        const si = sy * w + sx;
        const t = opts.target || { r: rgba[si * 4], g: rgba[si * 4 + 1], b: rgba[si * 4 + 2], a: rgba[si * 4 + 3] };
        const tol = Math.max(0, Math.floor((Number(opts.tolerance) || 0) + 1e-3));
        const azEq = opts.alphaZeroEqual !== false && t.a === 0;
        const tr = t.r, tg = t.g, tb = t.b, ta = t.a;
        function sim(i) {
            const o = i << 2;
            const a = rgba[o + 3];
            if (azEq && a === 0) return true;
            let d = rgba[o] - tr; if (d < 0) d = -d; if (d > tol) return false;
            d = rgba[o + 1] - tg; if (d < 0) d = -d; if (d > tol) return false;
            d = rgba[o + 2] - tb; if (d < 0) d = -d; if (d > tol) return false;
            d = a - ta; if (d < 0) d = -d;
            return d <= tol;
        }
        const marks = new Uint8Array(w * h);
        let bx0 = w, by0 = h, bx1 = -1, by1 = -1, count = 0;
        if (opts.contiguous !== false) {
            let stack = new Int32Array(1 << 14), sp = 0;
            stack[sp++] = si;
            const push = function (i) {
                if (sp === stack.length) { const bigger = new Int32Array(stack.length * 2); bigger.set(stack); stack = bigger; }
                stack[sp++] = i;
            };
            while (sp > 0) {
                const i = stack[--sp];
                if (marks[i]) continue;
                const y = (i / w) | 0, row = y * w, x = i - row;
                let l = x, r = x;
                while (l > 0 && !marks[row + l - 1] && sim(row + l - 1)) l--;
                while (r + 1 < w && !marks[row + r + 1] && sim(row + r + 1)) r++;
                marks.fill(255, row + l, row + r + 1);
                count += r - l + 1;
                if (l < bx0) bx0 = l;
                if (r > bx1) bx1 = r;
                if (y < by0) by0 = y;
                if (y > by1) by1 = y;
                for (let d = -1; d <= 1; d += 2) {
                    const ny = y + d;
                    if (ny < 0 || ny >= h) continue;
                    const nrow = ny * w;
                    let inRun = false;
                    for (let nx = l; nx <= r; nx++) {
                        const ok = !marks[nrow + nx] && sim(nrow + nx);
                        if (ok && !inRun) push(nrow + nx);
                        inRun = ok;
                    }
                }
            }
        } else {
            for (let y = 0; y < h; y++) {
                const row = y * w;
                for (let x = 0; x < w; x++) {
                    if (sim(row + x)) {
                        marks[row + x] = 255; count++;
                        if (x < bx0) bx0 = x;
                        if (x > bx1) bx1 = x;
                        if (y < by0) by0 = y;
                        if (y > by1) by1 = y;
                    }
                }
            }
            if (!marks[si]) { marks[si] = 255; count++; bx0 = Math.min(bx0, sx); bx1 = Math.max(bx1, sx); by0 = Math.min(by0, sy); by1 = Math.max(by1, sy); }
        }
        if (bx1 < 0) return { core: marks, mask: marks, bbox: null, coreBox: null, count: 0 };
        const coreBox = { x0: bx0, y0: by0, x1: bx1 + 1, y1: by1 + 1 };
        let mask = marks;
        const pad = opts.antiAlias === false ? 0 : 1;
        const x0 = Math.max(0, bx0 - pad), y0 = Math.max(0, by0 - pad);
        const x1 = Math.min(w, bx1 + 1 + pad), y1 = Math.min(h, by1 + 1 + pad);
        if (pad) {
            mask = new Uint8Array(marks);
            for (let y = y0; y < y1; y++) {
                for (let x = x0; x < x1; x++) {
                    const v = marks[y * w + x];
                    let sum = 0, edge = false;
                    for (let dy = -1; dy <= 1; dy++) {
                        const ny = y + dy;
                        for (let dx = -1; dx <= 1; dx++) {
                            const nx = x + dx;
                            const nv = (nx < 0 || ny < 0 || nx >= w || ny >= h) ? v : marks[ny * w + nx];
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
        return { core: marks, mask: mask, bbox: { x0: x0, y0: y0, x1: x1, y1: y1 }, coreBox: coreBox, count: count };
    }

    // ------------------------------------------------------------- compose
    // Combine a coverage mask into the current selection: add = max, subtract =
    // current - coverage (soft), replace = coverage. Returns a NEW Uint8Array.
    function compose(current, cover, mode) {
        const len = cover.length;
        if (mode === 'replace') return new Uint8Array(cover);
        const out = current && current.length === len ? new Uint8Array(current) : new Uint8Array(len);
        if (mode === 'subtract') {
            for (let i = 0; i < len; i++) { const c = cover[i]; if (c) { const v = out[i] - c; out[i] = v > 0 ? v : 0; } }
        } else {
            for (let i = 0; i < len; i++) { const c = cover[i]; if (c > out[i]) out[i] = c; }
        }
        return out;
    }

    return {
        version: 'w1-2026-10-09',
        boundsOf, expand, contract, border, invert, smooth, feather,
        polygon, ellipse, wandRegion, compose, distanceWindow,
    };
});
