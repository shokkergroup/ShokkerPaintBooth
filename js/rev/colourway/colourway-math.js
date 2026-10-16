/* [SPB-REV-COLOURWAY 2026-10-10] Colourway Studio, pure maths (no DOM, no app state): colour spaces, palette extraction,
 * harmony variants, and the PALETTE MAP that does the recolouring.
 *
 * Why a palette map: a livery is 3-6 flat colours plus anti-aliased edges and shading. A Hue/Saturation rotation moves every colour
 * the same way (the accent follows the body), and Photoshop's per-range Hue/Saturation leaves a halo on every edge pixel because an
 * edge pixel is a MIX of two palette colours. The palette map is a Gradient Map with a palette instead of a ramp: every palette
 * colour S_k is sent to its new colour T_k and everything in between follows smoothly, in sRGB (where the anti-aliasing happened):
 *       D(c) = sum_k lambda_k * |c - S_k| + A*c + b      (linear-kernel RBF with an affine term; D(S_k) = T_k - S_k exactly)
 *       out  = c + D(c)
 * A pixel half-way between yellow and black gets half-way between the new colour and the new black, a darker shade of yellow
 * gets a darker shade of the new colour, and a grey line stays a grey line when black / white map to themselves. The mapping is a
 * 33^3 LUT (trilinear), pre-seeded with the exact palette colours so a flat colour lands on its target to the level.
 *
 * Variants are made in OKLCH with a gamut-relative hue move (the colour keeps its lightness distance from the gamut cusp and its
 * relative chroma), so yellow -> blue becomes a real vivid blue and not a pale one.
 *
 * Public: window.SPBRevColourwayMath. Kill switch: SPB_REV_COLOURWAY_OFF (checked by the core; this file is inert maths).
 */
(function (root) {
    'use strict';
    if (!root || root.SPBRevColourwayMath) return;

    // ------------------------------------------------------------------ colour spaces
    function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
    function dec(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
    function enc(l) { l = l <= 0.0031308 ? 12.92 * l : 1.055 * Math.pow(l, 1 / 2.4) - 0.055; return l * 255; }
    function rgb2lab(r, g, b) {
        var R = dec(r), G = dec(g), B = dec(b);
        var l = Math.cbrt(0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B);
        var m = Math.cbrt(0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B);
        var s = Math.cbrt(0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B);
        return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
    }
    function lab2lin(L, a, b) {
        var l = L + 0.3963377774 * a + 0.2158037573 * b, m = L - 0.1055613458 * a - 0.0638541728 * b, s = L - 0.0894841775 * a - 1.2914855480 * b;
        l = l * l * l; m = m * m * m; s = s * s * s;
        return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
    }
    function inGamut(L, a, b) { var c = lab2lin(L, a, b), e = 1e-4; return c[0] >= -e && c[0] <= 1 + e && c[1] >= -e && c[1] <= 1 + e && c[2] >= -e && c[2] <= 1 + e; }
    function lab2rgb(L, a, b) { var c = lab2lin(L, a, b); return [enc(clamp(c[0], 0, 1)), enc(clamp(c[1], 0, 1)), enc(clamp(c[2], 0, 1))]; }
    function lch(L, C, h) { return [L, C * Math.cos(h), C * Math.sin(h)]; }
    function toLch(lab) { return { L: lab[0], C: Math.sqrt(lab[1] * lab[1] + lab[2] * lab[2]), h: Math.atan2(lab[2], lab[1]) }; }
    function cmax(L, h) {   // largest in-gamut chroma at this lightness and hue
        if (L <= 0 || L >= 1) return 0;
        var ca = Math.cos(h), sa = Math.sin(h), lo = 0, hi = 0.4;
        for (var i = 0; i < 18; i++) { var mid = (lo + hi) / 2; if (inGamut(L, mid * ca, mid * sa)) lo = mid; else hi = mid; }
        return lo;
    }
    var cuspCache = {};
    function cusp(h) {   // lightness where this hue is most vivid
        var k = Math.round(((h * 180 / Math.PI) % 360 + 360) % 360);
        if (cuspCache[k] != null) return cuspCache[k];
        var hh = k * Math.PI / 180, bestL = 0.6, best = -1;
        for (var L = 0.12; L <= 0.985; L += 0.02) { var c = cmax(L, hh); if (c > best) { best = c; bestL = L; } }
        return (cuspCache[k] = bestL);
    }
    function hex2rgb(h) { var n = parseInt(String(h).replace('#', ''), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
    function rgb2hex(r, g, b) { return '#' + [r, g, b].map(function (v) { return ('0' + Math.round(clamp(v, 0, 255)).toString(16)).slice(-2); }).join(''); }
    function isHex(h) { return /^#[0-9a-f]{6}$/i.test(String(h)); }
    function labDist(a, b) { var x = a[0] - b[0], y = a[1] - b[1], z = a[2] - b[2]; return Math.sqrt(x * x + y * y + z * z); }
    function hexLab(h) { var c = hex2rgb(h); return rgb2lab(c[0], c[1], c[2]); }
    /** an OKLCH colour moved into the sRGB gamut by lowering chroma only */
    function fitHex(L, C, h) {
        L = clamp(L, 0.02, 0.985);
        var m = cmax(L, h); C = Math.max(0, Math.min(C, m));
        var lab = lch(L, C, h), rgb = lab2rgb(lab[0], lab[1], lab[2]);
        return rgb2hex(rgb[0], rgb[1], rgb[2]);
    }
    var NAMES = [
        ['Black', '#101010'], ['Charcoal', '#3a3a3c'], ['Grey', '#808080'], ['Silver', '#b8b8bc'], ['White', '#f4f4f4'], ['Red', '#d41f1f'], ['Crimson', '#8c1230'],
        ['Orange', '#f08a1c'], ['Gold', '#f5b800'], ['Yellow', '#ffd400'], ['Lime', '#9bd81f'], ['Green', '#1f9d3a'], ['Forest', '#134d2b'], ['Teal', '#14a39a'],
        ['Cyan', '#17c3e6'], ['Sky', '#5ab4f0'], ['Blue', '#1f5fd6'], ['Navy', '#14285e'], ['Purple', '#6c2bd0'], ['Magenta', '#d62bb4'], ['Pink', '#f56fa8'],
        ['Brown', '#6a3f1f'], ['Tan', '#c9a473']];
    var NAME_LAB = null;
    function nameOf(hex) {
        if (!NAME_LAB) NAME_LAB = NAMES.map(function (n) { return hexLab(n[1]); });
        var lab = hexLab(hex), best = 0, bd = 9;
        for (var i = 0; i < NAMES.length; i++) { var d = labDist(lab, NAME_LAB[i]); if (d < bd) { bd = d; best = i; } }
        return NAMES[best][0];
    }

    // ------------------------------------------------------------------ palette extraction
    /** data: RGBA bytes (a downscaled sample of the composite), n pixels, keep: optional Uint8Array (0 = ignore this pixel, e.g. protected sponsor art).
     *  Returns { colours: [{hex, cov, lab, C, L, neutral, implicit, role, name}], total } ordered by role. */
    function extract(data, n, keep, opts) {
        opts = opts || {};
        var maxC = opts.max || 6, sep = opts.sep || 0.09, minCov = opts.minCov || 0.006;
        var hist = new Map(), total = 0;
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            if (data[o + 3] < 128) continue;
            if (keep && !keep[i]) continue;
            var key = (data[o] << 16) | (data[o + 1] << 8) | data[o + 2];
            hist.set(key, (hist.get(key) || 0) + 1); total++;
        }
        if (!total) return { colours: [], total: 0 };
        var keys = Array.from(hist.keys()), cnt = keys.map(function (k) { return hist.get(k); });
        var order = keys.map(function (_, i) { return i; }).sort(function (a, b) { return cnt[b] - cnt[a]; });
        var labs = new Array(keys.length);
        function labOf(idx) { return labs[idx] || (labs[idx] = rgb2lab(keys[idx] >> 16 & 255, keys[idx] >> 8 & 255, keys[idx] & 255)); }
        var seeds = [];
        for (var q = 0; q < order.length && seeds.length < maxC + 4; q++) {
            var idx = order[q]; if (cnt[idx] < total * minCov) break;
            var lb = labOf(idx), far = true;
            for (var s = 0; s < seeds.length; s++) if (labDist(lb, seeds[s].lab) < sep) { far = false; break; }
            if (far) seeds.push({ idx: idx, lab: lb, key: keys[idx], cov: 0 });
        }
        if (!seeds.length) { var t0 = order[0]; seeds.push({ idx: t0, lab: labOf(t0), key: keys[t0], cov: 0 }); }
        for (var j = 0; j < keys.length; j++) {   // coverage: every colour belongs to its nearest seed
            var lj = labOf(j), bs = 0, bd = 9;
            for (var s2 = 0; s2 < seeds.length; s2++) { var d = labDist(lj, seeds[s2].lab); if (d < bd) { bd = d; bs = s2; } }
            seeds[bs].cov += cnt[j];
        }
        seeds.sort(function (a, b) { return b.cov - a.cov; });
        // an anti-aliased edge or a smooth fade makes a colour that lies ON the line between two bigger palette colours: that is a mix, not a colour
        seeds = seeds.filter(function (sd, si) {
            if (si < 2 || sd.cov >= total * 0.04) return true;
            var c = [sd.key >> 16 & 255, sd.key >> 8 & 255, sd.key & 255];
            for (var a1 = 0; a1 < si; a1++) for (var b1 = a1 + 1; b1 < si; b1++) {
                var A1 = [seeds[a1].key >> 16 & 255, seeds[a1].key >> 8 & 255, seeds[a1].key & 255], B1 = [seeds[b1].key >> 16 & 255, seeds[b1].key >> 8 & 255, seeds[b1].key & 255];
                var ab = [B1[0] - A1[0], B1[1] - A1[1], B1[2] - A1[2]], ac = [c[0] - A1[0], c[1] - A1[1], c[2] - A1[2]], l2 = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2];
                if (l2 < 1) continue;
                var t = (ac[0] * ab[0] + ac[1] * ab[1] + ac[2] * ab[2]) / l2; if (t < 0.04 || t > 0.96) continue;
                var dx = ac[0] - t * ab[0], dy = ac[1] - t * ab[1], dz = ac[2] - t * ab[2];
                if (Math.sqrt(dx * dx + dy * dy + dz * dz) < 14) return false;
            }
            return true;
        });
        seeds = seeds.slice(0, maxC);
        var cols = seeds.map(function (sd) {
            var L = sd.lab[0], C = Math.sqrt(sd.lab[1] * sd.lab[1] + sd.lab[2] * sd.lab[2]);
            return { hex: rgb2hex(sd.key >> 16 & 255, sd.key >> 8 & 255, sd.key & 255), cov: sd.cov / total, lab: sd.lab, L: L, C: C, neutral: C < 0.045, implicit: false };
        });
        // pure black / white anchors: only when the livery has no colour of its own near them (otherwise that colour is the anchor)
        [['#000000', 'ink'], ['#ffffff', 'paper']].forEach(function (a) {
            var lab = hexLab(a[0]);
            if (!cols.some(function (c) { return labDist(c.lab, lab) < 0.13; })) cols.push({ hex: a[0], cov: 0, lab: lab, L: lab[0], C: 0, neutral: true, implicit: true });
        });
        // roles: chromatic colours ranked by coverage = main / accent / trim / detail; neutrals = ink / paper / grey
        var chroma = cols.filter(function (c) { return !c.neutral; }).sort(function (a, b) { return b.cov - a.cov; });
        var RN = ['main', 'accent', 'trim', 'detail', 'detail', 'detail'];
        chroma.forEach(function (c, i) { c.role = RN[i] || 'detail'; });
        cols.forEach(function (c) { if (c.neutral) c.role = c.L < 0.34 ? 'ink' : (c.L > 0.84 ? 'paper' : 'grey'); c.name = nameOf(c.hex); });
        var ro = { main: 0, accent: 1, trim: 2, detail: 3, ink: 4, grey: 5, paper: 6 };
        cols.sort(function (a, b) { return (ro[a.role] - ro[b.role]) || (b.cov - a.cov); });
        return { colours: cols, total: total };
    }

    // ------------------------------------------------------------------ variants (harmony rules)
    function role(pal, r) { for (var i = 0; i < pal.length; i++) if (pal[i].role === r) return i; return -1; }
    /** Move colour c (a palette entry) to a new hue, gamut-relative: same distance from the cusp, same relative chroma. */
    function moveHue(c, newH, opts) {
        opts = opts || {};
        var lab = c.lab, p = toLch(lab), cu0 = cusp(p.h), cu1 = cusp(newH);
        var rel = p.C / Math.max(cmax(p.L, p.h), 1e-4); rel = Math.min(rel, 1.0);
        var L = clamp(cu1 + (p.L - cu0) * (opts.keepL != null ? opts.keepL : 1) + (opts.dL || 0), 0.06, 0.97);
        var relC = clamp(rel * (opts.chroma != null ? opts.chroma : 1), 0, 1.0);
        return fitHex(L, relC * cmax(L, newH), newH);
    }
    function sameHue(c, dL, chromaK) {   // keep the hue, move lightness / chroma (night, tonal)
        var p = toLch(c.lab), L = clamp(p.L + dL, 0.04, 0.97);
        return fitHex(L, Math.min(p.C * (chromaK == null ? 1 : chromaK), cmax(L, p.h) * 0.98), p.h);
    }
    var TAU = Math.PI * 2;
    function rot(h, deg) { return h + deg * Math.PI / 180; }
    /** Build 8 harmony variants (+ a Team variant from the user's hex codes). Each: { id, name, harmony, to:[hex per palette entry], mats, note }. */
    function variants(pal, team, opts) {
        opts = opts || {};
        var iM = role(pal, 'main'), iA = role(pal, 'accent'), iT = role(pal, 'trim');
        var i0 = iM, out = [];
        if (i0 < 0) {   // an all-neutral livery: the biggest non-ink colour plays "main" so the harmonies still have a hue to start from
            var best = -1; for (var i = 0; i < pal.length; i++) if (!pal[i].implicit && pal[i].role !== 'ink' && (best < 0 || pal[i].cov > pal[best].cov)) best = i;
            i0 = best;
        }
        var iK = -1;   // a big neutral second colour (the black of a yellow / black car): variants may trade it or tint it
        for (var q = 0; q < pal.length; q++) { var cq = pal[q]; if (cq.neutral && !cq.implicit && cq.cov >= 0.12 && (iK < 0 || cq.cov > pal[iK].cov)) iK = q; }
        var base = pal.map(function (c) { return c.hex; });
        function make(id, name, harmony, fn, mats, note) {
            var to = base.slice(); fn(to);
            out.push({ id: id, name: name, harmony: harmony, to: to, mats: mats || {}, note: note || '' });
        }
        var hM = i0 >= 0 ? toLch(pal[i0].lab).h : 0;
        var chromatic = i0 >= 0 && !pal[i0].neutral;
        function hueFor(c, ref, deg) { return rot(ref, deg); }
        if (i0 >= 0) {
            // neutrals take a hue only in an all-neutral livery (then "main" is grey: give it a vivid hue from the start)
            var seedC = chromatic ? null : 0.12;
            function setMain(to, h, dL, ck) {
                var c = pal[i0];
                if (chromatic) to[i0] = moveHue(c, h, { dL: dL, chroma: ck });
                else to[i0] = fitHex(Math.max(0.35, c.L), seedC, h);
            }
            make('comp', 'Complementary', 'complementary', function (to) {
                setMain(to, rot(hM, 180));
                if (iA >= 0) to[iA] = moveHue(pal[iA], hM); else if (chromatic && iT >= 0) to[iT] = moveHue(pal[iT], hM);
                if (iA >= 0 && iT >= 0) to[iT] = moveHue(pal[iT], rot(hM, 180), { dL: 0.12, chroma: 0.55 });
            }, { accent: 'candy', main: 'gloss' }, (iA >= 0 || iT >= 0) ? 'The body flips to the opposite hue; the old body colour becomes the accent, so main and accent sit on opposite sides of the wheel.' : 'The body flips to the opposite side of the colour wheel. The black and white stay.');
            make('split', 'Split Complementary', 'split', function (to) {
                if (iA >= 0) to[iA] = moveHue(pal[iA], rot(hM, 150));
                if (iT >= 0) to[iT] = moveHue(pal[iT], rot(hM, 210));
                if (iA < 0 && chromatic) setMain(to, rot(hM, 150));
            }, { accent: 'candy', trim: 'chrome' }, (iA >= 0 || iT >= 0) ? 'The body stays; the accent and trim move to the two hues next to its complement (sponsor swap, same car).' : 'The body moves to a hue next to its complement: close to a complementary look but easier on the eye.');
            make('tri', 'Triadic', 'triadic', function (to) {
                setMain(to, rot(hM, 120));
                if (iA >= 0) to[iA] = moveHue(pal[iA], rot(hM, 240));
                if (iT >= 0) to[iT] = moveHue(pal[iT], hM);
            }, { accent: 'pearl', main: 'gloss' }, 'Three hues 120 degrees apart: loud and easy to tell apart from the stands.');
            make('tri2', 'Triadic Alt', 'triadic', function (to) {
                setMain(to, rot(hM, 240));
                if (iA >= 0) to[iA] = moveHue(pal[iA], rot(hM, 120));
                if (iT >= 0) to[iT] = moveHue(pal[iT], rot(hM, 0));
            }, { accent: 'candy', trim: 'satin' }, 'The same triad turned the other way round.');
            make('ana', 'Analogous', 'analogous', function (to) {
                setMain(to, rot(hM, 40));
                if (iA >= 0) to[iA] = moveHue(pal[iA], rot(hM, -30));
                if (iT >= 0) to[iT] = moveHue(pal[iT], rot(hM, 75));
            }, { main: 'pearl', accent: 'gloss' }, 'Neighbouring hues: a calm, factory-team look.');
            if (chromatic) make('tonal', 'Tonal', 'monochrome', function (to) {
                if (iA >= 0) to[iA] = sameHue(pal[i0], 0.2, 0.62);
                if (iT >= 0) to[iT] = sameHue(pal[i0], -0.2, 0.9);
                if (iA < 0 && iT < 0) to[i0] = sameHue(pal[i0], -0.08, 0.9);
            }, { accent: 'pearl', trim: 'satin' }, 'One hue: a lighter tint for the accent, a deeper shade for the trim. The black and white stay.');
            if (iA >= 0) make('swap', 'Reverse', 'swap', function (to) {
                to[i0] = base[iA]; to[iA] = base[i0];
            }, { main: 'gloss', accent: 'chrome' }, 'Body and accent trade colours; nothing new is introduced, so it is always on-brand.');
            else if (iK >= 0 && chromatic) make('swap', 'Reverse', 'swap', function (to) {
                to[i0] = base[iK]; to[iK] = base[i0];
            }, { main: 'satin', accent: 'chrome' }, 'Body and the second colour trade places: the same car, inverted. Nothing new is introduced.');
            if (iA < 0 && iT < 0 && iK >= 0 && chromatic && pal[iK].L < 0.5) make('twotone', 'Two-Tone', 'twotone', function (to) {
                setMain(to, rot(hM, 150));
                var h2 = rot(hM, 215); to[iK] = fitHex(0.3, cmax(0.3, h2) * 0.55, h2);
            }, { main: 'gloss', accent: 'candy' }, 'The black becomes a deep colour and the body takes a hue next to its complement.');
            make('night', 'Night', 'night', function (to) {
                pal.forEach(function (c, i) {
                    if (c.role === 'main' || c.role === 'detail') to[i] = sameHue(c, -c.L * 0.5, 0.92);
                    else if (c.role === 'accent') to[i] = sameHue(c, Math.min(0.1, 0.97 - c.L), 1.2);
                    else if (c.role === 'trim') to[i] = sameHue(c, Math.min(0.14, 0.97 - c.L), 1.15);
                    else if (c.role === 'ink') to[i] = sameHue(c, -c.L * 0.5, 1);
                    else if (c.role === 'paper') to[i] = sameHue(c, -0.08, 1);
                });
            }, { main: 'matte', accent: 'chrome' }, 'Darker body, brighter accents: stays readable under floodlights.');
        }
        // team colours: main / accent / trim from the typed hex codes
        var t = (team || []).filter(isHex);
        if (t.length && i0 >= 0) {
            make('team', 'Team Colours', 'team', function (to) {
                to[i0] = t[0].toLowerCase();
                if (t[1] && iA >= 0) to[iA] = t[1].toLowerCase();
                else if (t[1] && iA < 0 && iT >= 0) to[iT] = t[1].toLowerCase();
                else if (t[1] && iA < 0 && iT < 0 && iK >= 0) to[iK] = t[1].toLowerCase();
                if (t[2] && iT >= 0 && iA >= 0) to[iT] = t[2].toLowerCase();
            }, { accent: 'candy' }, 'Your hex codes in order: main, accent, trim. Black, white and the rest stay.');
        }
        // drop variants that change (almost) nothing or repeat another one; add the contrast hint
        var seen = [];
        out = out.filter(function (v) {
            var delta = 0; v.to.forEach(function (h, i) { var a = hex2rgb(h), b = hex2rgb(base[i]); delta = Math.max(delta, Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2])); });
            v.delta = delta;
            if (delta < 24) return false;
            var key = v.to.join(',');
            if (seen.indexOf(key) >= 0) return false;
            seen.push(key); return true;
        });
        out.forEach(function (v) {
            var m = i0 >= 0 ? hexLab(v.to[i0]) : null, a = iA >= 0 ? hexLab(v.to[iA]) : (iT >= 0 ? hexLab(v.to[iT]) : null);
            v.contrast = (m && a) ? labDist(m, a) : null;
            v.lowContrast = v.contrast != null && v.contrast < 0.1;
        });
        return out;
    }

    // ------------------------------------------------------------------ the palette map (RBF displacement, 33^3 LUT)
    var G = 33, GN = G * G * G;
    function solve(A, B, m, nrhs) {   // Gauss elimination, partial pivoting; A (m x m row-major), B (m x nrhs row-major); in place
        for (var c = 0; c < m; c++) {
            var p = c, mx = Math.abs(A[c * m + c]);
            for (var r = c + 1; r < m; r++) { var v = Math.abs(A[r * m + c]); if (v > mx) { mx = v; p = r; } }
            if (mx < 1e-12) continue;
            if (p !== c) {
                for (var k = 0; k < m; k++) { var t = A[c * m + k]; A[c * m + k] = A[p * m + k]; A[p * m + k] = t; }
                for (var k2 = 0; k2 < nrhs; k2++) { var t2 = B[c * nrhs + k2]; B[c * nrhs + k2] = B[p * nrhs + k2]; B[p * nrhs + k2] = t2; }
            }
            var piv = A[c * m + c];
            for (var r2 = c + 1; r2 < m; r2++) {
                var f = A[r2 * m + c] / piv; if (!f) continue;
                for (var k3 = c; k3 < m; k3++) A[r2 * m + k3] -= f * A[c * m + k3];
                for (var k4 = 0; k4 < nrhs; k4++) B[r2 * nrhs + k4] -= f * B[c * nrhs + k4];
            }
        }
        for (var c2 = m - 1; c2 >= 0; c2--) {
            for (var k5 = 0; k5 < nrhs; k5++) {
                var s = B[c2 * nrhs + k5];
                for (var j = c2 + 1; j < m; j++) s -= A[c2 * m + j] * B[j * nrhs + k5];
                B[c2 * nrhs + k5] = Math.abs(A[c2 * m + c2]) < 1e-12 ? 0 : s / A[c2 * m + c2];
            }
        }
        return B;
    }
    /** pairs: [{from, to}] -> mapper { out: Float32Array(GN*3), G, exact: [{key, packed}], map(r,g,b)->[r,g,b], D(r,g,b), identity } */
    function buildMapper(pairs) {
        var K = pairs.length, S = [], T = [], ident = true;
        for (var i = 0; i < K; i++) { S.push(hex2rgb(pairs[i].from)); T.push(hex2rgb(pairs[i].to)); if (pairs[i].from.toLowerCase() !== pairs[i].to.toLowerCase()) ident = false; }
        var M = { G: G, K: K, S: S, T: T, identity: ident, out: null, exact: [] };
        if (!K || ident) { M.identity = true; return M; }
        // Grey-ramp anchors: when the livery's neutrals (black / white / grey) stay neutral, the ramp between the darkest and the lightest one is pinned
        // as a straight line in the NEW colours too. Without them an anti-aliased grey edge picks up a tint from the colours that move (a salmon fringe
        // on a white outline). Skipped when a neutral palette colour is itself recoloured (Reverse): then the ramp must bend with it.
        var SS = S.slice(), TT = T.slice();
        (function () {
            var nIdx = [], k;
            function grey(c) { return Math.max(c[0], c[1], c[2]) - Math.min(c[0], c[1], c[2]) <= 10; }
            function luma(c) { return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]; }
            for (k = 0; k < K; k++) if (grey(S[k])) nIdx.push(k);
            if (nIdx.length < 2) return;
            var dk = nIdx[0], lt = nIdx[0];
            nIdx.forEach(function (i) { if (luma(S[i]) < luma(S[dk])) dk = i; if (luma(S[i]) > luma(S[lt])) lt = i; });
            if (luma(S[lt]) - luma(S[dk]) < 120 || !grey(T[dk]) || !grey(T[lt])) return;
            var span = luma(S[lt]) - luma(S[dk]), tSpan = luma(T[lt]) - luma(T[dk]);
            for (var q = 0; q < nIdx.length; q++) {   // every neutral palette colour must sit on the straight line between the end points in the new colours
                var i2 = nIdx[q], t2 = (luma(S[i2]) - luma(S[dk])) / span, want = luma(T[dk]) + t2 * tSpan;
                if (!grey(T[i2]) || Math.abs(luma(T[i2]) - want) > 10) return;
            }
            [0.2, 0.4, 0.6, 0.8].forEach(function (t) {
                var src = [0, 1, 2].map(function (c) { return Math.round(S[dk][c] + (S[lt][c] - S[dk][c]) * t); });
                for (var z = 0; z < SS.length; z++) if (Math.abs(src[0] - SS[z][0]) + Math.abs(src[1] - SS[z][1]) + Math.abs(src[2] - SS[z][2]) < 36) return;
                var tgt = [0, 1, 2].map(function (c) { return Math.round(T[dk][c] + (T[lt][c] - T[dk][c]) * t); });
                SS.push(src); TT.push(tgt);
            });
        })();
        var K2 = SS.length;
        var m = K2 + 4, A = new Float64Array(m * m), B = new Float64Array(m * 3);
        for (var a = 0; a < K2; a++) {
            for (var b = 0; b < K2; b++) {
                var dx = (SS[a][0] - SS[b][0]) / 255, dy = (SS[a][1] - SS[b][1]) / 255, dz = (SS[a][2] - SS[b][2]) / 255;
                A[a * m + b] = Math.sqrt(dx * dx + dy * dy + dz * dz);
            }
            A[a * m + K2] = 1; A[a * m + K2 + 1] = SS[a][0] / 255; A[a * m + K2 + 2] = SS[a][1] / 255; A[a * m + K2 + 3] = SS[a][2] / 255;
            A[K2 * m + a] = 1; A[(K2 + 1) * m + a] = SS[a][0] / 255; A[(K2 + 2) * m + a] = SS[a][1] / 255; A[(K2 + 3) * m + a] = SS[a][2] / 255;
            for (var ch = 0; ch < 3; ch++) B[a * 3 + ch] = TT[a][ch] - SS[a][ch];
        }
        for (var p = 0; p < 4; p++) A[(K2 + p) * m + (K2 + p)] = -1e-4;   // ridge on the polynomial block: stays solvable for 1-3 colours
        solve(A, B, m, 3);
        var lam = B, out = new Float32Array(GN * 3), idx = 0;
        function Dat(r, g, b2, o) {
            var x = r / 255, y = g / 255, z = b2 / 255, d0 = lam[K2 * 3] + lam[(K2 + 1) * 3] * x + lam[(K2 + 2) * 3] * y + lam[(K2 + 3) * 3] * z,
                d1 = lam[K2 * 3 + 1] + lam[(K2 + 1) * 3 + 1] * x + lam[(K2 + 2) * 3 + 1] * y + lam[(K2 + 3) * 3 + 1] * z,
                d2 = lam[K2 * 3 + 2] + lam[(K2 + 1) * 3 + 2] * x + lam[(K2 + 2) * 3 + 2] * y + lam[(K2 + 3) * 3 + 2] * z;
            for (var k = 0; k < K2; k++) {
                var ex = x - SS[k][0] / 255, ey = y - SS[k][1] / 255, ez = z - SS[k][2] / 255, rr = Math.sqrt(ex * ex + ey * ey + ez * ez);
                d0 += lam[k * 3] * rr; d1 += lam[k * 3 + 1] * rr; d2 += lam[k * 3 + 2] * rr;
            }
            o[0] = d0; o[1] = d1; o[2] = d2;
        }
        var d = [0, 0, 0], stp = 255 / (G - 1);
        for (var ri = 0; ri < G; ri++) for (var gi = 0; gi < G; gi++) for (var bi = 0; bi < G; bi++) {
            var r = ri * stp, g = gi * stp, bb = bi * stp;
            Dat(r, g, bb, d);
            out[idx++] = clamp(r + d[0], 0, 255); out[idx++] = clamp(g + d[1], 0, 255); out[idx++] = clamp(bb + d[2], 0, 255);
        }
        M.out = out;
        M.D = function (r, g, b2) { var o = [0, 0, 0]; Dat(r, g, b2, o); return o; };
        for (var e = 0; e < K; e++) M.exact.push({ key: (S[e][0] << 16) | (S[e][1] << 8) | S[e][2], packed: (T[e][0] << 16) | (T[e][1] << 8) | T[e][2] });
        M.map = function (r, g, b2) {   // exact (not LUT) mapping of one colour
            for (var q = 0; q < M.exact.length; q++) if (M.exact[q].key === ((r << 16) | (g << 8) | b2)) { var pk = M.exact[q].packed; return [pk >> 16 & 255, pk >> 8 & 255, pk & 255]; }
            var o = [0, 0, 0]; Dat(r, g, b2, o); return [clamp(r + o[0], 0, 255), clamp(g + o[1], 0, 255), clamp(b2 + o[2], 0, 255)];
        };
        return M;
    }
    /** In place on unpremultiplied RGBA bytes. sa: optional per-pixel strength bytes, k0: constant strength 0..1. */
    function applyMapper(M, d, n, sa, k0) {
        if (!M || M.identity || !M.out) return d;
        var out = M.out, scale = (G - 1) / 255, ex = M.exact, nex = ex.length, g1 = G - 1;
        var CK = new Int32Array(4096).fill(-1), CV = new Int32Array(4096), lastK = -1, lastV = 0;
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            if (d[o + 3] === 0) continue;
            var k = sa ? k0 * sa[i] / 255 : k0;
            if (k <= 0) continue;
            var R = d[o], Gc = d[o + 1], B = d[o + 2], key = (R << 16) | (Gc << 8) | B, v;
            if (key === lastK) v = lastV;
            else {
                var h = (Math.imul(key, -1640531535) >>> 20) & 4095;
                if (CK[h] === key) v = CV[h];
                else {
                    v = -1;
                    for (var q = 0; q < nex; q++) if (ex[q].key === key) { v = ex[q].packed; break; }
                    if (v < 0) {
                        var fr = R * scale, fg = Gc * scale, fb = B * scale, r0 = fr | 0, g0 = fg | 0, b0 = fb | 0;
                        if (r0 >= g1) r0 = g1 - 1; if (g0 >= g1) g0 = g1 - 1; if (b0 >= g1) b0 = g1 - 1;
                        var tr = fr - r0, tg = fg - g0, tb = fb - b0, base = ((r0 * G + g0) * G + b0) * 3, sR = G * G * 3, sG = G * 3, sB = 3, rr = 0, gg = 0, bb = 0;
                        for (var c = 0; c < 8; c++) {
                            var dr = c & 1, dg = (c >> 1) & 1, db = (c >> 2) & 1, w = (dr ? tr : 1 - tr) * (dg ? tg : 1 - tg) * (db ? tb : 1 - tb);
                            if (w === 0) continue;
                            var p = base + dr * sR + dg * sG + db * sB;
                            rr += out[p] * w; gg += out[p + 1] * w; bb += out[p + 2] * w;
                        }
                        v = ((rr + 0.5) | 0) << 16 | ((gg + 0.5) | 0) << 8 | ((bb + 0.5) | 0);
                    }
                    CK[h] = key; CV[h] = v;
                }
                lastK = key; lastV = v;
            }
            var nr = v >> 16 & 255, ng = v >> 8 & 255, nb = v & 255;
            if (k >= 0.9999) { d[o] = nr; d[o + 1] = ng; d[o + 2] = nb; }
            else { d[o] = R + (nr - R) * k; d[o + 1] = Gc + (ng - Gc) * k; d[o + 2] = B + (nb - B) * k; }
        }
        return d;
    }
    /** How much the mapping stretches distances around colour c (BT.601-weighted, the zone matcher's metric): tolerance x this keeps the same pixels. */
    function localScale(M, c) {
        if (!M || M.identity || !M.map) return 1;
        var w = [Math.sqrt(0.30), Math.sqrt(0.59), Math.sqrt(0.11)], rho = 9, tot = 0, cnt = 0, base = M.map(c[0], c[1], c[2]);
        var dirs = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], [1, 1, 0], [-1, -1, 0], [1, -1, 0], [-1, 1, 0], [0, 1, 1], [0, -1, -1], [0, 1, -1], [0, -1, 1], [1, 0, 1], [-1, 0, -1], [1, 0, -1], [-1, 0, 1]];
        dirs.forEach(function (u) {
            var nl = Math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2]);
            var p = [c[0] + rho * u[0] / nl / w[0], c[1] + rho * u[1] / nl / w[1], c[2] + rho * u[2] / nl / w[2]];
            if (p.some(function (v) { return v < 0 || v > 255; })) return;
            var q = M.map(p[0], p[1], p[2]);
            tot += Math.sqrt(0.30 * Math.pow(q[0] - base[0], 2) + 0.59 * Math.pow(q[1] - base[1], 2) + 0.11 * Math.pow(q[2] - base[2], 2)) / rho; cnt++;
        });
        return cnt ? clamp(tot / cnt, 0.4, 2.5) : 1;
    }
    /** BT.601-weighted distance in 0..255 units, the metric engine.core.build_zone_mask uses. */
    function zoneDist(a, b) { return Math.sqrt(0.30 * Math.pow(a[0] - b[0], 2) + 0.59 * Math.pow(a[1] - b[1], 2) + 0.11 * Math.pow(a[2] - b[2], 2)); }

    root.SPBRevColourwayMath = {
        version: 'cwm-1', G: G, clamp: clamp, hex2rgb: hex2rgb, rgb2hex: rgb2hex, isHex: isHex, rgb2lab: rgb2lab, hexLab: hexLab, labDist: labDist, toLch: toLch,
        fitHex: fitHex, cmax: cmax, cusp: cusp, nameOf: nameOf, extract: extract, variants: variants, buildMapper: buildMapper, applyMapper: applyMapper,
        localScale: localScale, zoneDist: zoneDist
    };
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null));
