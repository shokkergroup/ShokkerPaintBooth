/* Non-destructive adjustment layers for the SPB layer stack (ticket TL-16, TOOLS-LAYERS lane, 2026-10-10).
 * Maths follow PhotoCraft (crates/compose/src/adjust.rs: Hue/Saturation, modern Brightness/Contrast, Levels with the Photoshop
 * toe, Vibrance, Exposure, Invert, Posterize) - (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0
 * (THIRD_PARTY_NOTICES.md). Modified: rewritten in JavaScript for Shokker Paint Booth (8-bit RGBA, Canvas2D compositor hook,
 * immutable per-layer parameter objects, undo through the existing layer history). Owner direction: "tools feel like a feature".
 *
 * Model: layer.pcAdj = frozen { type, p: {params} }; the layer's own image is an empty (transparent) canvas-sized canvas, so zone
 * ownership / picking / export treat it as having no art. When the compositor reaches the layer it adjusts everything drawn so far
 * (backdrop) instead of drawing pixels: result = backdrop + (adjusted - backdrop) * opacity * mask * (clip base alpha).
 * The layer mask is the normal pc-layermask.js mask (white = adjustment applies). Kill switch: window.SPB_TLAY_OFF = true.
 * pca-2 (TL-18): types can be registered from other files (registerType): cpu loop, identity test, WebGL uniforms / LUT, extra card UI, JSON / colour
 * parameters. pc-adjust-more.js adds Curves, Color Balance, Black & White, Photo Filter, Threshold and Gradient Map that way.
 */
(function () {
    'use strict';
    if (window.SPBPcAdjust) return;
    var VERSION = 'pca-2';
    function off() { return window.SPB_TLAY_OFF === true; }
    var stats = { applies: 0, lastMs: 0, lastRegion: null, adds: 0 };
    var undoers = [];

    function toast(msg, kind) { try { if (typeof window.showToast === 'function') window.showToast(msg, kind); } catch (_e) {} }
    function mk(w, h) { var c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }
    function cx(c) { return c.getContext('2d', { willReadFrequently: true }); }
    function cdims() { var pc = document.getElementById('paintCanvas'); return { w: pc ? pc.width : 2048, h: pc ? pc.height : 2048 }; }
    function stack() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; }
    function byId(id) { var s = stack(); for (var i = 0; i < s.length; i++) if (s[i] && s[i].id === id) return s[i]; return null; }
    function indexOf(id) { var s = stack(); for (var i = 0; i < s.length; i++) if (s[i] && s[i].id === id) return i; return -1; }
    function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
    function freeze(o) { return Object.freeze(o); }

    // ------------------------------------------------------------------ the adjustment catalogue
    var TYPES = {
        hueSat: {
            label: 'Hue/Saturation', glyph: 'H',
            hint: 'Shift every colour below: hue turns the colour wheel, saturation and lightness as in Photoshop. Colorize paints everything in one hue.',
            params: [
                { k: 'hue', label: 'Hue', min: -180, max: 180, step: 1, def: 0, unit: '°' },
                { k: 'saturation', label: 'Saturation', min: -100, max: 100, step: 1, def: 0 },
                { k: 'lightness', label: 'Lightness', min: -100, max: 100, step: 1, def: 0 },
                { k: 'colorize', label: 'Colorize', type: 'bool', def: false }]
        },
        brightContrast: {
            label: 'Brightness/Contrast', glyph: 'B',
            hint: 'Photoshop-style Brightness and Contrast curves (black and white stay pinned).',
            params: [
                { k: 'brightness', label: 'Brightness', min: -150, max: 150, step: 1, def: 0 },
                { k: 'contrast', label: 'Contrast', min: -50, max: 100, step: 1, def: 0 }]
        },
        levels: {
            label: 'Levels', glyph: 'L',
            hint: 'Set the black point, white point and midtone gamma of everything below. Drag the markers under the histogram.',
            params: [
                { k: 'inBlack', label: 'In black', min: 0, max: 253, step: 1, def: 0 },
                { k: 'gamma', label: 'Gamma', min: -100, max: 100, step: 1, def: 0, log: true },
                { k: 'inWhite', label: 'In white', min: 2, max: 255, step: 1, def: 255 },
                { k: 'outBlack', label: 'Out black', min: 0, max: 255, step: 1, def: 0 },
                { k: 'outWhite', label: 'Out white', min: 0, max: 255, step: 1, def: 255 }]
        },
        vibrance: {
            label: 'Vibrance', glyph: 'V',
            hint: 'Vibrance lifts the dull colours and leaves the already strong ones (and skin tones) alone; Saturation moves all.',
            params: [
                { k: 'vibrance', label: 'Vibrance', min: -100, max: 100, step: 1, def: 0 },
                { k: 'saturation', label: 'Saturation', min: -100, max: 100, step: 1, def: 0 }]
        },
        exposure: {
            label: 'Exposure', glyph: 'E',
            hint: 'Exposure in stops, with offset and gamma correction (linear light, like Photoshop).',
            params: [
                { k: 'exposure', label: 'Exposure', min: -5, max: 5, step: 0.05, def: 0, dec: 2 },
                { k: 'offset', label: 'Offset', min: -0.5, max: 0.5, step: 0.005, def: 0, dec: 3 },
                { k: 'gamma', label: 'Gamma', min: -100, max: 100, step: 1, def: 0, log: true }]
        },
        invert: { label: 'Invert', glyph: 'I', hint: 'Swap every colour for its opposite.', params: [] },
        posterize: {
            label: 'Posterize', glyph: 'P',
            hint: 'Reduce every channel to a fixed number of levels.',
            params: [{ k: 'levels', label: 'Levels', min: 2, max: 32, step: 1, def: 4 }]
        }
    };
    var ORDER = ['hueSat', 'brightContrast', 'levels', 'vibrance', 'exposure', 'invert', 'posterize'];
    function deepFreeze(o) { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.keys(o).forEach(function (k) { deepFreeze(o[k]); }); Object.freeze(o); } return o; }
    function clone(o) { return o && typeof o === 'object' ? JSON.parse(JSON.stringify(o)) : o; }
    function defaults(type) { var o = {}; (TYPES[type].params || []).forEach(function (q) { o[q.k] = (q.type === 'json') ? deepFreeze(clone(q.def)) : q.def; }); return o; }
    var uiState = {};   // per-layer card state that is not part of the undo history (selected tab, selected gradient stop, ...)
    function uiOf(id) { return uiState[id] || (uiState[id] = {}); }
    // Other files add adjustment types: def = { label, glyph, hint, params, identity(p), cpu(d,n,p,sa,k0), gpu: { id, uniforms(p), lut(p) }, ui(L, rows, ctx), onSet(np, key, v) }
    function registerType(name, def, after) {
        if (!name || !def || TYPES[name]) return false;
        TYPES[name] = def;
        var at = after ? ORDER.indexOf(after) : -1;
        if (at >= 0) ORDER.splice(at + 1, 0, name); else ORDER.push(name);
        try { injectMenu(true); } catch (_e) {}
        return true;
    }
    function gammaOf(v) { return clamp(Math.pow(10, v / 100), 0.01, 9.99); }   // slider -100..100 -> 0.1..9.99 (log)

    function isIdentity(P) {
        var p = P.p, T0 = TYPES[P.type];
        if (T0 && typeof T0.identity === 'function') return !!T0.identity(p);
        switch (P.type) {
            case 'hueSat': return !p.colorize && !p.hue && !p.saturation && !p.lightness;
            case 'brightContrast': return !p.brightness && !p.contrast;
            case 'levels': return !p.inBlack && p.inWhite === 255 && !p.gamma && !p.outBlack && p.outWhite === 255;
            case 'vibrance': return !p.vibrance && !p.saturation;
            case 'exposure': return !p.exposure && !p.offset && !p.gamma;
            default: return false;
        }
    }

    // ------------------------------------------------------------------ pixel maths (PhotoCraft adjust.rs, 8-bit)
    function modernBrightness(v, b) {
        if (b === 0) return v;
        var s = Math.pow(1.375, b / 50), pw = b >= 0 ? Math.max(4.5 - 0.013 * b, 2) : 5 - 0.072 * b;
        v = clamp(v, 0, 1);
        return clamp(s * v + (1 - s) * Math.pow(v, pw), 0, 1);
    }
    function modernContrast(v, c) {
        if (c === 0) return v;
        var k = c / 128, end = 1 - k, mid = 1 + k;
        function half(t) { return end * 0.5 * (t * t * t - 2 * t * t + t) + (-2 * t * t * t + 3 * t * t) * 0.5 + mid * 0.5 * (t * t * t - t * t); }
        v = clamp(v, 0, 1);
        return v <= 0.5 ? half(v / 0.5) : 1 - half((1 - v) / 0.5);
    }
    function levelsQ(ch, v, q) {   // Photoshop Levels on whole 8-bit levels, soft toe for gamma > 1
        var range = Math.max(ch.inWhite - ch.inBlack, 1e-6), u;
        if (q >= 1) { v = Math.round(v * q) / q; u = Math.floor(clamp((v - ch.inBlack) / range, 0, 1) * q + 0.5 + 1e-3) / q; }
        else u = clamp((v - ch.inBlack) / range, 0, 1);
        var g = Math.max(ch.gamma, 0.01), t;
        if (g > 1) {
            var power = Math.pow(u, 1 / g), line = 0.93 * Math.pow(2, g) * u;
            if (power <= 1e-6 || line <= 1e-6) t = Math.min(power, line);
            else t = Math.pow(Math.pow(power, -10) + Math.pow(line, -10), -1 / 10);
        } else t = Math.pow(u, 1 / g);
        return ch.outBlack + t * (ch.outWhite - ch.outBlack);
    }
    function lutFor(type, p) {
        var lut = new Uint8Array(256), i, v, x;
        if (type === 'brightContrast') {
            for (i = 0; i < 256; i++) { v = i / 255; x = clamp(modernContrast(modernBrightness(v, p.brightness || 0), p.contrast || 0), 0, 1); lut[i] = Math.round(x * 255); }
        } else if (type === 'levels') {
            var ch = { inBlack: (p.inBlack || 0) / 255, inWhite: (p.inWhite == null ? 255 : p.inWhite) / 255, gamma: gammaOf(p.gamma || 0), outBlack: (p.outBlack || 0) / 255, outWhite: (p.outWhite == null ? 255 : p.outWhite) / 255 };
            for (i = 0; i < 256; i++) { x = clamp(levelsQ(ch, i / 255, 255), 0, 1); lut[i] = Math.round(x * 255); }
        } else if (type === 'exposure') {
            var m = Math.pow(2, p.exposure || 0), g = gammaOf(p.gamma || 0), off2 = p.offset || 0;
            for (i = 0; i < 256; i++) { var lin = Math.pow(Math.max(Math.pow(i / 255, 2.2) * m + off2, 0), 1 / g); lut[i] = Math.round(clamp(Math.pow(Math.max(lin, 0), 1 / 2.2), 0, 1) * 255); }
        } else if (type === 'invert') {
            for (i = 0; i < 256; i++) lut[i] = 255 - i;
        } else if (type === 'posterize') {
            var n = clamp(Math.round(p.levels || 4), 2, 255);
            for (i = 0; i < 256; i++) { var bin = Math.min(Math.floor(i * n / 256), n - 1); lut[i] = Math.floor(bin * 255 / (n - 1)); }
        } else for (i = 0; i < 256; i++) lut[i] = i;
        return lut;
    }
    var SRGB_DEC = new Float64Array(256), SRGB_ENC = new Float64Array(4097);
    (function () {
        var i;
        for (i = 0; i < 256; i++) { var c = i / 255; SRGB_DEC[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
        for (i = 0; i <= 4096; i++) { var l = i / 4096; SRGB_ENC[i] = l <= 0.0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - 0.055; }
    })();
    function enc(l) { if (l <= 0) return 0; if (l >= 1) return 1; var x = l * 4096, i = x | 0, f = x - i; return SRGB_ENC[i] * (1 - f) + SRGB_ENC[i + 1] * f; }

    function lutLoop(d, n, lut, sa, k0) {
        var lr = lut.r || lut, lg = lut.g || lut, lb = lut.b || lut;   // one table for every channel, or {r, g, b} (Curves)
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            if (d[o + 3] === 0) continue;
            var k = sa ? k0 * sa[i] / 255 : k0;
            if (k <= 0) continue;
            var r = d[o], g = d[o + 1], b = d[o + 2];
            if (k >= 0.9999) { d[o] = lr[r]; d[o + 1] = lg[g]; d[o + 2] = lb[b]; }
            else { d[o] = r + (lr[r] - r) * k; d[o + 1] = g + (lg[g] - g) * k; d[o + 2] = b + (lb[b] - b) * k; }
        }
    }
    function hueSatLoop(d, n, p, sa, k0) {
        var colorize = !!p.colorize, hueDeg = p.hue || 0, hue01 = hueDeg / 360, sat = clamp((p.saturation || 0) / 100, -1, 1), lig = clamp((p.lightness || 0) / 100, -1, 1);
        var colH = (((hueDeg % 360) + 360) % 360) / 360, colS = Math.max(Math.abs(sat), 0.25);
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            if (d[o + 3] === 0) continue;
            var k = sa ? k0 * sa[i] / 255 : k0;
            if (k <= 0) continue;
            var R = d[o], G = d[o + 1], B = d[o + 2], r = R / 255, g = G / 255, b = B / 255;
            var mx = r > g ? (r > b ? r : b) : (g > b ? g : b), mn = r < g ? (r < b ? r : b) : (g < b ? g : b), l = (mx + mn) / 2, h = 0, s = 0, dd = mx - mn;
            if (dd >= 1e-7) {
                s = l > 0.5 ? dd / (2 - mx - mn) : dd / (mx + mn);
                if (mx === r) h = (g - b) / dd; else if (mx === g) h = (b - r) / dd + 2; else h = (r - g) / dd + 4;
                h = (((h % 6) + 6) % 6) / 6;
            }
            var hh, ss;
            if (colorize) { hh = colH; ss = colS; }
            else { hh = ((h + hue01) % 1 + 1) % 1; ss = clamp(s * (1 + sat), 0, 1); }
            var nr, ng, nb;
            if (ss <= 0) { nr = ng = nb = l; }
            else {
                var q = l < 0.5 ? l * (1 + ss) : l + ss - l * ss, pp = 2 * l - q, t, v;
                t = (((hh + 1 / 3) % 1) + 1) % 1; v = t < 1 / 6 ? pp + (q - pp) * 6 * t : (t < 0.5 ? q : (t < 2 / 3 ? pp + (q - pp) * (2 / 3 - t) * 6 : pp)); nr = v;
                t = (((hh) % 1) + 1) % 1; v = t < 1 / 6 ? pp + (q - pp) * 6 * t : (t < 0.5 ? q : (t < 2 / 3 ? pp + (q - pp) * (2 / 3 - t) * 6 : pp)); ng = v;
                t = (((hh - 1 / 3) % 1) + 1) % 1; v = t < 1 / 6 ? pp + (q - pp) * 6 * t : (t < 0.5 ? q : (t < 2 / 3 ? pp + (q - pp) * (2 / 3 - t) * 6 : pp)); nb = v;
            }
            if (lig > 0) { nr += (1 - nr) * lig; ng += (1 - ng) * lig; nb += (1 - nb) * lig; }
            else if (lig < 0) { nr *= 1 + lig; ng *= 1 + lig; nb *= 1 + lig; }
            nr = nr < 0 ? 0 : (nr > 1 ? 255 : nr * 255); ng = ng < 0 ? 0 : (ng > 1 ? 255 : ng * 255); nb = nb < 0 ? 0 : (nb > 1 ? 255 : nb * 255);
            if (k >= 0.9999) { d[o] = nr; d[o + 1] = ng; d[o + 2] = nb; }
            else { d[o] = R + (nr - R) * k; d[o + 1] = G + (ng - G) * k; d[o + 2] = B + (nb - B) * k; }
        }
    }
    var VB = [0.5001, 0.0887, 0.4374, 0.7573, -0.8113, 0.5154, 2.8026];
    function vibranceLoop(d, n, p, sa, k0) {
        var v = clamp((p.vibrance || 0) / 100, -1, 1), s = clamp((p.saturation || 0) / 100, -1, 1);
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            if (d[o + 3] === 0) continue;
            var k = sa ? k0 * sa[i] / 255 : k0;
            if (k <= 0) continue;
            var R = d[o], G = d[o + 1], B = d[o + 2], c0 = SRGB_DEC[R], c1 = SRGB_DEC[G], c2 = SRGB_DEC[B];
            if (v !== 0) {
                var mx = c0 > c1 ? (c0 > c2 ? c0 : c2) : (c1 > c2 ? c1 : c2), mn = c0 < c1 ? (c0 < c2 ? c0 : c2) : (c1 < c2 ? c1 : c2);
                if (mx > 0 && mx - mn > 1e-9) {
                    var t = 1 - mn / mx, om = Math.max(1 - mx, 0), shape = t * (1 - t) * (2 - t + t * t) * mx * om, t2, v2;
                    if (v < 0) { var a0 = -v; t2 = t * (1 - a0 / 4) * (1 - a0 + a0 * t * (1 + t) / 2); v2 = mx - a0 * shape; }
                    else {
                        var hd = mx - mn, hu;
                        if (mx === c0) hu = (((c1 - c2) / hd) % 6 + 6) % 6; else if (mx === c1) hu = (c2 - c0) / hd + 2; else hu = (c0 - c1) / hd + 4;
                        hu *= 60;
                        var w = hu <= 30 ? 1 : (hu < 45 ? (45 - hu) / 15 : (hu < 300 ? 0 : (hu - 300) / 60));
                        var a = v * (1 - w) + 0.64 * Math.pow(v, 1.6) * w;
                        var boost = (VB[0] * a + VB[1] * a * a) * Math.pow(t, VB[2]) * Math.pow(1 - t, VB[3]) * Math.exp((VB[4] + VB[5] * a + VB[6] * (1 - t)) * om);
                        t2 = Math.min(t * (1 + boost), 1); v2 = mx + v / 4 * shape;
                    }
                    var m2 = v2 * (1 - t2), kk = (v2 - m2) / (mx - mn);
                    c0 = m2 + (c0 - mn) * kk; c1 = m2 + (c1 - mn) * kk; c2 = m2 + (c2 - mn) * kk;
                }
            }
            if (s !== 0) {
                var gr = 0.288 * c0 + 0.712 * c1;
                c0 = clamp(gr + (1 + s) * (c0 - gr), 0, 1); c1 = clamp(gr + (1 + s) * (c1 - gr), 0, 1); c2 = clamp(gr + (1 + s) * (c2 - gr), 0, 1);
            }
            var nr = enc(c0) * 255, ng = enc(c1) * 255, nb = enc(c2) * 255;
            if (k >= 0.9999) { d[o] = nr; d[o + 1] = ng; d[o + 2] = nb; }
            else { d[o] = R + (nr - R) * k; d[o + 1] = G + (ng - G) * k; d[o + 2] = B + (nb - B) * k; }
        }
    }
    // Adjust the RGB of unpremultiplied RGBA bytes in place. sa: optional per-pixel strength bytes, k0: constant factor 0..1.
    function processBytes(P, d, n, sa, k0) {
        var t = P.type, p = P.p || {}, T1 = TYPES[t];
        if (T1 && typeof T1.cpu === 'function') T1.cpu(d, n, p, sa, k0);
        else if (t === 'hueSat') hueSatLoop(d, n, p, sa, k0);
        else if (t === 'vibrance') vibranceLoop(d, n, p, sa, k0);
        else lutLoop(d, n, lutFor(t, p), sa, k0);
    }

    // ------------------------------------------------------------------ strength map (mask x clip) for a rectangle of a context
    var strengthCache = new WeakMap();
    function strengthEntry(tf, lx, ly, lw, lh, st, clip) {   // canvas whose alpha is mask x clip for the rectangle (null = full strength)
        if (!st && !clip) return null;
        var cacheable = st && !clip && !st.live;
        var key = cacheable ? [st.dx, st.dy, lx, ly, lw, lh, tf.a, tf.d, tf.e, tf.f].join('|') : null;
        var hit = cacheable ? strengthCache.get(st.A) : null;
        if (hit && hit.key === key) return hit;
        var S = mk(lw, lh), g = cx(S);
        g.setTransform(1, 0, 0, 1, 0, 0);
        if (!st) { g.fillStyle = '#fff'; g.fillRect(0, 0, lw, lh); }
        g.setTransform(tf.a, tf.b, tf.c, tf.d, tf.e - lx, tf.f - ly);
        if (st) g.drawImage(st.A, st.dx, st.dy);
        if (clip) { g.globalCompositeOperation = 'destination-in'; g.drawImage(clip.img, clip.x, clip.y); }
        var ent = { key: key, S: S, sa: null, lw: lw, lh: lh };
        if (cacheable) strengthCache.set(st.A, ent);
        return ent;
    }
    function strengthMap(tf, lx, ly, lw, lh, st, clip) {   // the same as per-pixel strength bytes (CPU path)
        var ent = strengthEntry(tf, lx, ly, lw, lh, st, clip);
        if (!ent) return null;
        if (ent.sa) return ent.sa;
        var sd = cx(ent.S).getImageData(0, 0, lw, lh).data, n = lw * lh, sa = new Uint8Array(n);
        for (var i = 0, o = 3; i < n; i++, o += 4) sa[i] = sd[o];
        ent.sa = sa;
        return sa;
    }

    // ------------------------------------------------------------------ GPU path (WebGL): the same maths over the whole 2048x2048 backdrop in a few ms
    // (CPU hue/saturation measured 713 ms per full canvas, vibrance 746 ms: unusable while dragging a slider). Falls back to the CPU loops on any failure.
    var gpu = { ok: null, c: null, gl: null, prog: null, loc: null, tSrc: null, tStr: null, tLut: null, strS: null, lutKey: '', w: 0, h: 0 };
    var VS_SRC = 'attribute vec2 p;varying vec2 v;void main(){v=p*0.5+0.5;gl_Position=vec4(p,0.,1.);}';
    var FS_SRC = [
        'precision highp float;varying vec2 v;uniform sampler2D uSrc;uniform sampler2D uStr;uniform sampler2D uLut;',
        'uniform float uType;uniform float uK;uniform float uHasStr;uniform vec4 uA;uniform vec4 uB;uniform vec4 uC;uniform vec4 uD;uniform mat3 uM;uniform float uLN;',
        'float decs(float c){return c<=0.04045?c/12.92:pow((c+0.055)/1.055,2.4);}',
        'float encs(float l){l=clamp(l,0.,1.);return l<=0.0031308?l*12.92:1.055*pow(l,1./2.4)-0.055;}',
        'float h2r(float p,float q,float t){t=fract(t);if(t<1./6.)return p+(q-p)*6.*t;if(t<.5)return q;if(t<2./3.)return p+(q-p)*(2./3.-t)*6.;return p;}',
        'vec3 hueSat(vec3 c){float mx=max(c.r,max(c.g,c.b)),mn=min(c.r,min(c.g,c.b)),l=(mx+mn)*.5,h=0.,s=0.,d=mx-mn;',
        ' if(d>=1e-7){s=l>.5?d/(2.-mx-mn):d/(mx+mn);if(mx==c.r)h=(c.g-c.b)/d;else if(mx==c.g)h=(c.b-c.r)/d+2.;else h=(c.r-c.g)/d+4.;h=mod(h,6.)/6.;}',
        ' float hh,ss;if(uA.w>.5){hh=uB.x;ss=uB.y;}else{hh=fract(h+uA.x);ss=clamp(s*(1.+uA.y),0.,1.);}',
        ' vec3 o;if(ss<=0.)o=vec3(l);else{float q=l<.5?l*(1.+ss):l+ss-l*ss,p=2.*l-q;o=vec3(h2r(p,q,hh+1./3.),h2r(p,q,hh),h2r(p,q,hh-1./3.));}',
        ' float lg=uA.z;if(lg>0.)o+=(1.-o)*lg;else if(lg<0.)o*=1.+lg;return clamp(o,0.,1.);}',
        'vec3 vibLin(vec3 c,float v){float mx=max(c.r,max(c.g,c.b)),mn=min(c.r,min(c.g,c.b));if(mx<=0.||mx-mn<=1e-9)return c;',
        ' float t=1.-mn/mx,om=max(1.-mx,0.),shape=t*(1.-t)*(2.-t+t*t)*mx*om,t2,v2;',
        ' if(v<0.){float a=-v;t2=t*(1.-a/4.)*(1.-a+a*t*(1.+t)/2.);v2=mx-a*shape;}',
        ' else{float d=mx-mn,hu;if(mx==c.r)hu=mod((c.g-c.b)/d,6.);else if(mx==c.g)hu=(c.b-c.r)/d+2.;else hu=(c.r-c.g)/d+4.;hu*=60.;',
        '  float w=hu<=30.?1.:(hu<45.?(45.-hu)/15.:(hu<300.?0.:(hu-300.)/60.));float a=v*(1.-w)+.64*pow(v,1.6)*w;',
        '  float bo=(.5001*a+.0887*a*a)*pow(t,.4374)*pow(1.-t,.7573)*exp((-.8113+.5154*a+2.8026*(1.-t))*om);t2=min(t*(1.+bo),1.);v2=mx+v/4.*shape;}',
        ' float m2=v2*(1.-t2),k=(v2-m2)/(mx-mn);return m2+(c-mn)*k;}',
        'vec3 vibrance(vec3 c){vec3 l=vec3(decs(c.r),decs(c.g),decs(c.b));if(uA.x!=0.)l=vibLin(l,uA.x);',
        ' if(uA.y!=0.){float g=.288*l.r+.712*l.g;l=clamp(g+(1.+uA.y)*(l-g),0.,1.);}return vec3(encs(l.r),encs(l.g),encs(l.b));}',
        'vec4 lutt(float c){float i=floor(clamp(c,0.,1.)*(uLN-1.)+.5);return texture2D(uLut,vec2((i+.5)/uLN,.5));}',
        'float gray(vec3 c){return dot(c,vec3(.299,.587,.114));}',
        'vec3 colorBal(vec3 c){float l=gray(c);float ws=clamp(1.-l*2.,0.,1.),wh=clamp(l*2.-1.,0.,1.),wm=1.-ws-wh;',
        ' vec3 o=clamp(c+(uA.xyz*ws+uB.xyz*wm+uC.xyz*wh)*.005,0.,1.);',
        ' if(uD.x>.5){float l1=max(gray(o),1e-6);o=clamp(o*l/l1,0.,1.);}return o;}',
        'vec3 bw(vec3 c){float mx=max(c.r,max(c.g,c.b)),mn=min(c.r,min(c.g,c.b)),md=c.r+c.g+c.b-mx-mn;',
        ' float wp=(c.r>=c.g&&c.r>=c.b)?uA.x:(c.g>=c.b?uA.z:uB.x);float wsx=(c.b<=c.r&&c.b<=c.g)?uA.y:(c.r<=c.g?uA.w:uB.y);',
        ' float g=clamp(mn+(md-mn)*wsx*.01+(mx-md)*wp*.01,0.,1.);',
        ' if(uB.z>.5)return clamp(g*uC.rgb*2.,0.,1.)*.5+g*.5;return vec3(g);}',
        'float encu(float l){l=max(l,0.);return l<=0.0031308?l*12.92:1.055*pow(l,1./2.4)-0.055;}',
        'vec3 setLum(vec3 c,float l){c+=l-dot(c,vec3(.3,.59,.11));float L=dot(c,vec3(.3,.59,.11)),n=min(c.r,min(c.g,c.b)),x=max(c.r,max(c.g,c.b));vec3 o=c;',
        ' if(n<0.){float d=L-n;o=abs(d)<1e-12?vec3(L):L+(o-L)*L/d;}',
        ' if(x>1.){float d=x-L;o=abs(d)<1e-12?vec3(L):L+(o-L)*(1.-L)/d;}return o;}',
        'vec3 photoF(vec3 c){vec3 f=uM*vec3(decs(c.r),decs(c.g),decs(c.b));f=vec3(encu(f.r),encu(f.g),encu(f.b));',
        ' if(uD.x>.5)f=setLum(f,dot(c,vec3(.3,.59,.11)));return clamp(f,0.,1.);}',
        'void main(){vec4 s=texture2D(uSrc,v);if(s.a<=0.){gl_FragColor=s;return;}float k=uK;if(uHasStr>.5)k*=texture2D(uStr,v).a;',
        ' vec3 r;if(uType<.5)r=hueSat(s.rgb);else if(uType<1.5)r=vibrance(s.rgb);else if(uType<2.5)r=vec3(lutt(s.r).r,lutt(s.g).g,lutt(s.b).b);',
        ' else if(uType<3.5)r=lutt(gray(s.rgb)).rgb;else if(uType<4.5)r=colorBal(s.rgb);else if(uType<5.5)r=bw(s.rgb);else r=photoF(s.rgb);',
        ' gl_FragColor=vec4(mix(s.rgb,r,k),s.a);}'
    ].join('\n');
    function gpuInit() {
        if (gpu.ok !== null) return gpu.ok;
        gpu.ok = false;
        try {
            var c = document.createElement('canvas'); c.width = 16; c.height = 16;
            var gl = c.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: false, depth: false, stencil: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' });
            if (!gl) return false;
            var sh = function (type, src) { var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
            var pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS_SRC)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS_SRC)); gl.linkProgram(pr);
            if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
            gl.useProgram(pr);
            var buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
            var pl = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(pl); gl.vertexAttribPointer(pl, 2, gl.FLOAT, false, 0, 0);
            var loc = {}; ['uSrc', 'uStr', 'uLut', 'uType', 'uK', 'uHasStr', 'uA', 'uB', 'uC', 'uD', 'uM', 'uLN'].forEach(function (n) { loc[n] = gl.getUniformLocation(pr, n); });
            var mkTex = function () { var t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE); return t; };
            gl.activeTexture(gl.TEXTURE0); var t0 = mkTex(); gl.activeTexture(gl.TEXTURE1); var t1 = mkTex(); gl.activeTexture(gl.TEXTURE2); var t2 = mkTex();
            var one = new Uint8Array([255, 255, 255, 255]);   // placeholders so no sampler ever points at an incomplete texture
            gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, t1); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, one);
            gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, t2); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, one);
            gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, t0); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, one);
            gl.uniform1i(loc.uSrc, 0); gl.uniform1i(loc.uStr, 1); gl.uniform1i(loc.uLut, 2);
            c.addEventListener('webglcontextlost', function (e) { e.preventDefault(); gpu.ok = false; gpu.strS = null; gpu.lutKey = ''; }, false);
            gpu.c = c; gpu.gl = gl; gpu.prog = pr; gpu.loc = loc; gpu.tSrc = t0; gpu.tStr = t1; gpu.tLut = t2; gpu.ok = true;
        } catch (e) { gpu.ok = false; try { console.warn('[pca] WebGL path off: ' + e.message); } catch (_e) {} }
        return gpu.ok;
    }
    function gpuRun(P, src, S, k0) {   // src: canvas (w x h) -> result left in the bottom-left w x h of gpu.c; S: strength canvas (w x h) or null
        if (!gpuInit()) return false;
        var gl = gpu.gl, W = src.width, H = src.height, p = P.p || {}, t = P.type, lut = null;
        if (gl.isContextLost()) { gpu.ok = false; return false; }
        if (gpu.c.width < W || gpu.c.height < H) { gpu.c.width = Math.max(W, gpu.c.width); gpu.c.height = Math.max(H, gpu.c.height); }
        gl.viewport(0, 0, W, H);   // the result sits in the BOTTOM-left W x H of the drawing buffer
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, gpu.tSrc);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
        var L = gpu.loc;
        gl.uniform1f(L.uK, k0);
        if (S) {
            gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, gpu.tStr);
            if (gpu.strS !== S) { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, S); gpu.strS = S; }
            gl.uniform1f(L.uHasStr, 1);
        } else gl.uniform1f(L.uHasStr, 0);
        var T = TYPES[t];
        gl.uniform4f(L.uC, 0, 0, 0, 0); gl.uniform4f(L.uD, 0, 0, 0, 0); gl.uniform1f(L.uLN, 256);
        if (T && T.gpu) {   // a registered type: its own shader branch id, uniforms and / or LUT row
            var u = T.gpu.uniforms ? T.gpu.uniforms(p) : null;
            gl.uniform1f(L.uType, T.gpu.id);
            gl.uniform4f(L.uA, u && u.A ? u.A[0] : 0, u && u.A ? u.A[1] : 0, u && u.A ? u.A[2] : 0, u && u.A ? u.A[3] : 0);
            gl.uniform4f(L.uB, u && u.B ? u.B[0] : 0, u && u.B ? u.B[1] : 0, u && u.B ? u.B[2] : 0, u && u.B ? u.B[3] : 0);
            if (u && u.C) gl.uniform4f(L.uC, u.C[0], u.C[1], u.C[2], u.C[3]);
            if (u && u.D) gl.uniform4f(L.uD, u.D[0], u.D[1], u.D[2], u.D[3]);
            gl.uniformMatrix3fv(L.uM, false, new Float32Array(u && u.M ? u.M : [1, 0, 0, 0, 1, 0, 0, 0, 1]));   // column-major
            if (T.gpu.lut) {
                var key2 = t + '|' + JSON.stringify(p), tex = null;
                if (gpu.lutKey !== key2) {
                    tex = T.gpu.lut(p);
                    gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, gpu.tLut);
                    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
                    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, tex.length >> 2, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, tex);
                    gpu.lutKey = key2; gpu.lutN = tex.length >> 2;
                }
                gl.uniform1f(L.uLN, gpu.lutN || 256);
            }
        } else if (t === 'hueSat') {
            var hueDeg = p.hue || 0, colH = (((hueDeg % 360) + 360) % 360) / 360, sat = clamp((p.saturation || 0) / 100, -1, 1);
            gl.uniform1f(L.uType, 0); gl.uniform4f(L.uA, hueDeg / 360, sat, clamp((p.lightness || 0) / 100, -1, 1), p.colorize ? 1 : 0); gl.uniform4f(L.uB, colH, Math.max(Math.abs(sat), 0.25), 0, 0);
        } else if (t === 'vibrance') {
            gl.uniform1f(L.uType, 1); gl.uniform4f(L.uA, clamp((p.vibrance || 0) / 100, -1, 1), clamp((p.saturation || 0) / 100, -1, 1), 0, 0);
        } else {
            gl.uniform1f(L.uType, 2);
            var key = t + '|' + JSON.stringify(p);
            if (gpu.lutKey !== key) {
                lut = lutFor(t, p); var rgba = new Uint8Array(256 * 4);
                for (var i = 0; i < 256; i++) { rgba[i * 4] = rgba[i * 4 + 1] = rgba[i * 4 + 2] = lut[i]; rgba[i * 4 + 3] = 255; }
                gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, gpu.tLut);
                gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 256, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
                gpu.lutKey = key;
            }
        }
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        var err = gl.getError();
        if (err) { stats.gpuErr = err; return false; }
        return true;
    }
    function gpuWanted() { return window.SPB_TLAY_ADJ_CPU !== true && gpu.ok !== false; }

    // ------------------------------------------------------------------ compositor hook
    var hint = null;   // dirty rectangle (canvas space) of the paint preview being drawn, from SPBPaintPreviewRegion.paint
    var histHook = null;   // [SPB-TLAY 2026-10-10 TL-20] set by pc-adjust-more.js: samples what sits below the selected Levels / Curves layer for its histogram
    var tmpC = null, regC = null;
    function drawAdj(ctx, layers, idx, L, so) {
        var P = L.pcAdj, T = TYPES[P.type];
        if (!T || L.visible === false) return true;
        if (histHook && !hint) { try { histHook(ctx, L); } catch (_e) {} }   // [SPB-TLAY 2026-10-10 TL-20] before the identity early-out: a fresh Levels layer is an identity
        var k0 = (L.opacity == null ? 255 : +L.opacity) / 255;
        if (!(k0 > 0) || isIdentity(P)) return true;
        var t0 = performance.now();
        var st = null;
        if (so) st = { A: so, dx: 0, dy: 0, live: true };
        else if (L.__pcmStrength !== undefined) st = L.__pcmStrength || null;
        else if (window.SPBPcLayerMask && typeof window.SPBPcLayerMask.strengthFor === 'function') st = window.SPBPcLayerMask.strengthFor(L);
        var clip = null;
        if (L.clippingMask) {
            var base = (typeof window._clippingBaseForLayerIndex === 'function') ? window._clippingBaseForLayerIndex(layers, idx) : (typeof _clippingBaseForLayerIndex === 'function' ? _clippingBaseForLayerIndex(layers, idx) : null);
            if (!base || base.visible === false || !base.img) return true;
            var bb = base.bbox || [0, 0];
            clip = { img: base.img, x: bb[0] | 0, y: bb[1] | 0 };
        }
        var cv = ctx.canvas, W = cv.width, H = cv.height, tf = ctx.getTransform();
        var pure = Math.abs(tf.a - 1) < 1e-6 && Math.abs(tf.d - 1) < 1e-6 && Math.abs(tf.b) < 1e-6 && Math.abs(tf.c) < 1e-6;
        var lx = 0, ly = 0, lw = W, lh = H;
        if (pure && hint) {
            lx = Math.max(0, Math.floor(hint.x + tf.e)); ly = Math.max(0, Math.floor(hint.y + tf.f));
            lw = Math.min(W, Math.ceil(hint.x + hint.width + tf.e)) - lx; lh = Math.min(H, Math.ceil(hint.y + hint.height + tf.f)) - ly;
            if (lw <= 0 || lh <= 0) return true;
        }
        var mode = L.blendMode && L.blendMode !== 'source-over' ? L.blendMode : null;
        if (mode) {   // adjusted copy blended with the native canvas blend over the untouched backdrop, then mixed by strength
            var probe = mk(1, 1).getContext('2d'); probe.globalCompositeOperation = mode;
            if (probe.globalCompositeOperation !== mode) mode = null;
        }
        if (!mode && pure && gpuWanted()) {   // no readback anywhere: canvas -> texture -> canvas (a getImageData here stalls on every pending GPU draw: 59 ms per brush move measured)
            var full = lx === 0 && ly === 0 && lw === W && lh === H, ent = strengthEntry(tf, lx, ly, lw, lh, st, clip), src = cv;
            if (!full) {
                if (!regC) regC = document.createElement('canvas');
                if (regC.width !== lw || regC.height !== lh) { regC.width = lw; regC.height = lh; }
                var rg = regC.getContext('2d'); rg.setTransform(1, 0, 0, 1, 0, 0); rg.globalAlpha = 1; rg.globalCompositeOperation = 'copy';
                rg.drawImage(cv, lx, ly, lw, lh, 0, 0, lw, lh); src = regC;
            }
            if (gpuRun(P, src, ent ? ent.S : null, k0)) {
                ctx.save();
                ctx.setTransform(1, 0, 0, 1, 0, 0);
                if (!full) { ctx.beginPath(); ctx.rect(lx, ly, lw, lh); ctx.clip(); }
                ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'copy';
                try { ctx.filter = 'none'; } catch (_e) {}
                ctx.drawImage(gpu.c, 0, gpu.c.height - lh, lw, lh, lx, ly, lw, lh);
                ctx.restore();
                stats.applies++; stats.gpuApplies = (stats.gpuApplies | 0) + 1; stats.lastMs = performance.now() - t0; stats.lastRegion = [lx, ly, lw, lh]; stats.lastPath = 'gpu';
                if (stats.trace) stats.trace.push(['gpu', lw, lh, Math.round(stats.lastMs)]);
                return true;
            }
        }
        var id;
        try { id = ctx.getImageData(lx, ly, lw, lh); } catch (_e) { return true; }
        var d = id.data, n = lw * lh, sa = (st || clip) ? strengthMap(tf, lx, ly, lw, lh, st, clip) : null;
        if (!mode) processBytes(P, d, n, sa, k0);
        else {
            var orig = new Uint8ClampedArray(d);
            processBytes(P, d, n, null, 1);
            var cB = mk(lw, lh), gB = cx(cB), cA = mk(lw, lh), gA = cx(cA), idA = gA.createImageData(lw, lh);
            gB.putImageData(new ImageData(new Uint8ClampedArray(orig), lw, lh), 0, 0);
            idA.data.set(d); gA.putImageData(idA, 0, 0);
            gB.globalCompositeOperation = mode; gB.drawImage(cA, 0, 0);
            var rd = gB.getImageData(0, 0, lw, lh).data;
            for (var i = 0, o = 0; i < n; i++, o += 4) {
                if (orig[o + 3] === 0) { d[o] = orig[o]; d[o + 1] = orig[o + 1]; d[o + 2] = orig[o + 2]; continue; }
                var kk = sa ? k0 * sa[i] / 255 : k0;
                d[o] = orig[o] + (rd[o] - orig[o]) * kk; d[o + 1] = orig[o + 1] + (rd[o + 1] - orig[o + 1]) * kk; d[o + 2] = orig[o + 2] + (rd[o + 2] - orig[o + 2]) * kk;
            }
        }
        if (!tmpC || tmpC.width !== lw || tmpC.height !== lh) tmpC = mk(lw, lh);
        var tg = tmpC.getContext('2d'); tg.putImageData(id, 0, 0);
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.beginPath(); ctx.rect(lx, ly, lw, lh); ctx.clip();
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'copy';
        try { ctx.filter = 'none'; } catch (_e) {}
        ctx.drawImage(tmpC, lx, ly);
        ctx.restore();
        stats.applies++; stats.lastMs = performance.now() - t0; stats.lastRegion = [lx, ly, lw, lh]; stats.lastPath = 'cpu';
        if (stats.trace) stats.trace.push(['cpu', lw, lh, Math.round(stats.lastMs)]);
        return true;
    }
    var prevDraw = window._drawLayerPixelContent;
    if (typeof prevDraw === 'function' && !prevDraw.__pca) {
        var wdraw = function (ctx, layers, idx, so) {
            var L = layers && layers[idx];
            if (!off() && L && L.pcAdj) return drawAdj(ctx, layers, idx, L, so);
            return prevDraw.apply(this, arguments);
        };
        wdraw.__pca = true;
        for (var kd in prevDraw) { try { if (Object.prototype.hasOwnProperty.call(prevDraw, kd)) wdraw[kd] = prevDraw[kd]; } catch (_e) {} }
        window._drawLayerPixelContent = wdraw;
        undoers.push(function () { if (window._drawLayerPixelContent === wdraw) window._drawLayerPixelContent = prevDraw; });
    }
    // the move / transform gesture caches "everything above the moving layer" on a transparent canvas: an adjustment above would see nothing
    var prevBuild = window._spbBuildGestureCache;
    if (typeof prevBuild === 'function' && !prevBuild.__pca) {
        var wbuild = function (gid) {
            if (!off()) {
                var s = stack(), k = indexOf(gid);
                for (var j = k + 1; j < s.length; j++) { var l = s[j]; if (l && l.visible !== false && l.pcAdj && !isIdentity(l.pcAdj)) return null; }
            }
            return prevBuild.apply(this, arguments);
        };
        wbuild.__pca = true;
        window._spbBuildGestureCache = wbuild;
        undoers.push(function () { if (window._spbBuildGestureCache === wbuild) window._spbBuildGestureCache = prevBuild; });
    }
    // the clipped brush preview clears + redraws only the dirty rectangle: tell the adjustment which one so it does not process 2048x2048 per mouse move
    (function () {
        var P = window.SPBPaintPreviewRegion;
        if (!P || typeof P.paint !== 'function' || P.paint.__pca) return;
        var op = P.paint;
        var np = function (ctx, region, draw) {
            var keep = hint; hint = region || null;
            try { return op.call(this, ctx, region, draw); } finally { hint = keep; }
        };
        np.__pca = true;
        var wrapped = Object.freeze(Object.assign({}, P, { paint: np }));
        window.SPBPaintPreviewRegion = wrapped;
        undoers.push(function () { if (window.SPBPaintPreviewRegion === wrapped) window.SPBPaintPreviewRegion = P; });
    })();

    // ------------------------------------------------------------------ actions (one history step each)
    function touch(structure) {
        window._spbLayerRev = (window._spbLayerRev | 0) + 1;
        if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
        if (structure && typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
        if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
    }
    function pushUndo(label) { if (typeof window._pushLayerStackUndo === 'function') window._pushLayerStackUndo(label); }
    function nextName(label) {
        var re = new RegExp('^' + label.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&') + ' (\\d+)$'), n = 0;
        stack().forEach(function (l) { var m = l && re.exec(String(l.name || '')); if (m) n = Math.max(n, +m[1]); });
        return label + ' ' + (n + 1);
    }
    function add(type) {
        if (off()) return null;
        var T = TYPES[type]; if (!T) return null;
        var s = stack(), d = cdims();
        pushUndo('add adjustment layer');
        var sel = window._selectedLayerId, at = indexOf(sel);
        var L = {
            id: 'adj_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
            name: nextName(T.label), path: '', visible: true, opacity: 255, blendMode: 'source-over', locked: false, alphaLock: false, clippingMask: false, effects: null,
            bbox: [0, 0, d.w, d.h], img: mk(d.w, d.h), pcAdj: freeze({ type: type, p: freeze(defaults(type)) })
        };
        var ref = at >= 0 ? s[at] : null;
        if (ref) { if (ref.groupName != null) L.groupName = ref.groupName; if (ref.groupChain) L.groupChain = ref.groupChain; if (ref.path) L.path = ref.path; }
        s.splice(at >= 0 ? at + 1 : s.length, 0, L);
        window._psdLayersLoaded = true;
        if (window.SPBPcLayerMask && typeof window.SPBPcLayerMask.add === 'function') window.SPBPcLayerMask.add(L.id, 'reveal', true);
        if (typeof window.selectPSDLayer === 'function') { try { window.selectPSDLayer(L.id); } catch (_e) {} }
        stats.adds++;
        touch(true);
        toast('Added ' + L.name + ' - drag the sliders; paint its mask to limit where it applies', 'info');
        return L;
    }
    var gesture = null;
    var raf = 0;
    function setParam(id, key, value, final) {
        var L = byId(id); if (!L || !L.pcAdj) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var P = L.pcAdj, T = TYPES[P.type]; if (!T) return false;
        var q = null; T.params.forEach(function (x) { if (x.k === key) q = x; });
        if (!q) return false;
        var v;
        if (q.type === 'bool') v = !!value;
        else if (q.type === 'color') { v = /^#[0-9a-f]{6}$/i.test(String(value)) ? String(value).toLowerCase() : null; if (v === null) return false; }
        else if (q.type === 'json') { v = q.clean ? q.clean(value) : value; if (v === null || v === undefined) return false; v = deepFreeze(clone(v)); }
        else { v = clamp(Number(value), q.min, q.max); if (isNaN(v)) return false; }
        var same = (q.type === 'json') ? JSON.stringify(P.p[key]) === JSON.stringify(v) : P.p[key] === v;
        if (same) { if (final) gesture = null; return true; }
        if (!gesture || gesture.id !== id || gesture.key !== key) { pushUndo('adjust ' + T.label); gesture = { id: id, key: key }; }
        var np = Object.assign({}, P.p); np[key] = v;
        if (typeof T.onSet === 'function') T.onSet(np, key, v);
        if (P.type === 'hueSat' && key === 'colorize') {   // colorize turns the hue slider into 0..360 and wants a saturation
            if (v) { np.hue = np.hue < 0 ? np.hue + 360 : np.hue; if (np.saturation <= 0) np.saturation = 25; }
            else { np.hue = np.hue > 180 ? np.hue - 360 : np.hue; }
        }
        L.pcAdj = freeze({ type: P.type, p: freeze(np) });
        schedule(final || (P.type === 'hueSat' && key === 'colorize'));
        if (final) gesture = null;
        return true;
    }
    var fastOn = false;
    function schedule(structure) {   // coalesce slider ticks into one recomposite per animation frame
        if (structure) { if (raf) { cancelAnimationFrame(raf); raf = 0; } fastOn = false; touch(true); return; }
        if (raf) return;
        raf = requestAnimationFrame(function () { raf = 0; fastTick(); });
    }
    // slider tick: the app's own move-gesture caches (everything below / above the layer, rendered once per gesture) + this adjustment re-applied,
    // no pixel readback and no panel rebuild; the full recomposite runs once when the drag ends (endFast)
    function fastTick() {
        var g = gesture;
        if (!g || typeof window.recompositeFromLayers !== 'function') { touch(false); return; }
        if (!fastOn) { window._gestureCacheStamp = (window._gestureCacheStamp | 0) + 1; fastOn = true; }
        window.recompositeFromLayers({ readback: false, gestureLayerId: g.id });
    }
    function endFast() {
        var pending = !!raf;
        if (raf) { cancelAnimationFrame(raf); raf = 0; }
        if (fastOn || pending) { fastOn = false; touch(false); }
    }
    function reset(id) {
        var L = byId(id); if (!L || !L.pcAdj) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var P = L.pcAdj, T = TYPES[P.type];
        pushUndo('reset ' + T.label);
        L.pcAdj = freeze({ type: P.type, p: freeze(defaults(P.type)) });
        gesture = null; touch(true); return true;
    }
    // Merge Down on an adjustment layer: apply it to the pixels of the layer below (that layer only, like Photoshop)
    function bakeDown(i) {
        var s = stack(), U = s[i], Lw = s[i - 1];
        if (!U || !U.pcAdj) return false;
        if (!Lw) { toast('Nothing below to apply this adjustment to', 'warn'); return false; }
        if (Lw.pcAdj) { toast('Cannot apply an adjustment onto another adjustment layer', 'warn'); return false; }
        if (Lw.locked) { toast('"' + (Lw.name || 'Layer below') + '" is locked', 'warn'); return false; }
        if (!Lw.img) return false;
        var P = U.pcAdj, k0 = (U.opacity == null ? 255 : +U.opacity) / 255;
        var w = Lw.img.naturalWidth || Lw.img.width, h = Lw.img.naturalHeight || Lw.img.height, b = Lw.bbox || [0, 0];
        var out = mk(w, h), g = cx(out); g.drawImage(Lw.img, 0, 0);
        var id = g.getImageData(0, 0, w, h), d = id.data, n = w * h;
        var st = (window.SPBPcLayerMask && window.SPBPcLayerMask.strengthFor) ? window.SPBPcLayerMask.strengthFor(U) : null;
        var tf = { a: 1, b: 0, c: 0, d: 1, e: -(b[0] | 0), f: -(b[1] | 0) };
        var sa = st ? strengthMap(tf, 0, 0, w, h, st, null) : null;
        pushUndo('apply adjustment layer');
        if (!isIdentity(P) && k0 > 0) { processBytes(P, d, n, sa, k0); g.putImageData(id, 0, 0); }
        Lw.img = out;
        s.splice(i, 1);
        if (typeof window.selectPSDLayer === 'function') { try { window.selectPSDLayer(Lw.id); } catch (_e) {} }
        touch(true);
        toast('Adjustment applied to "' + (Lw.name || 'the layer below') + '"', 'success');
        return true;
    }
    var prevMerge = window.mergeLayerDown;
    if (typeof prevMerge === 'function' && !prevMerge.__pca) {
        var wmerge = function (layerId) {
            if (!off()) {
                var i = indexOf(layerId), s = stack();
                if (i >= 0 && s[i] && s[i].pcAdj) return bakeDown(i);
                if (i > 0 && s[i - 1] && s[i - 1].pcAdj) { toast('Cannot merge a layer into an adjustment layer. Move it below the adjustment first.', 'warn'); return false; }
            }
            return prevMerge.apply(this, arguments);
        };
        wmerge.__pca = true;
        for (var km in prevMerge) { try { if (Object.prototype.hasOwnProperty.call(prevMerge, km)) wmerge[km] = prevMerge[km]; } catch (_e) {} }
        window.mergeLayerDown = wmerge;
        undoers.push(function () { if (window.mergeLayerDown === wmerge) window.mergeLayerDown = prevMerge; });
    }
    // Merge Selected would keep the adjustment object on the survivor and ignore the merged pixels: point the painter at Apply / Merge visible instead
    var prevMergeSel = window.mergeSelectedLayers;
    if (typeof prevMergeSel === 'function' && !prevMergeSel.__pca) {
        var wmsel = function () {
            if (!off()) {
                var sel = [];
                try { sel = (typeof window._spbSelectedLayers === 'function') ? window._spbSelectedLayers() : []; } catch (_e) {}
                for (var q = 0; q < sel.length; q++) if (sel[q] && sel[q].pcAdj) { toast('Merge Selected cannot include an adjustment layer. Use Apply (merge down) on it, or Merge visible.', 'warn'); return false; }
            }
            return prevMergeSel.apply(this, arguments);
        };
        wmsel.__pca = true;
        for (var kms in prevMergeSel) { try { if (Object.prototype.hasOwnProperty.call(prevMergeSel, kms)) wmsel[kms] = prevMergeSel[kms]; } catch (_e) {} }
        window.mergeSelectedLayers = wmsel;
        undoers.push(function () { if (window.mergeSelectedLayers === wmsel) window.mergeSelectedLayers = prevMergeSel; });
    }
    var prevDup = window.duplicateLayer;
    if (typeof prevDup === 'function' && !prevDup.__pca) {
        var wdup = function (layerId) {
            var src = byId(layerId);
            var r = prevDup.apply(this, arguments);
            if (!off() && r && r.id && src && src.pcAdj && !r.pcAdj) {
                r.pcAdj = src.pcAdj;
                touch(true);
            }
            return r;
        };
        wdup.__pca = true;
        for (var kdp in prevDup) { try { if (Object.prototype.hasOwnProperty.call(prevDup, kdp)) wdup[kdp] = prevDup[kdp]; } catch (_e) {} }
        window.duplicateLayer = wdup;
        undoers.push(function () { if (window.duplicateLayer === wdup) window.duplicateLayer = prevDup; });
    }

    // ------------------------------------------------------------------ persistence
    function serialize(layer) {
        var P = layer && layer.pcAdj; if (!P) return undefined;
        return { v: 1, type: P.type, p: clone(P.p) };
    }
    function deserialize(layer, rec) {
        if (!layer || !rec || !TYPES[rec.type]) return false;
        var p = Object.assign(defaults(rec.type), rec.p || {}), dflt = defaults(rec.type);
        (TYPES[rec.type].params || []).forEach(function (q) {
            if (q.type === 'json') { var c = q.clean ? q.clean(p[q.k]) : p[q.k]; p[q.k] = (c === null || c === undefined) ? dflt[q.k] : c; }
            else if (q.type === 'color' && !/^#[0-9a-f]{6}$/i.test(String(p[q.k]))) p[q.k] = q.def;
        });
        layer.pcAdj = freeze({ type: rec.type, p: deepFreeze(clone(p)) });
        return true;
    }

    // ------------------------------------------------------------------ card UI
    var BTN = 'font-size:9px;padding:2px 5px;background:#1a1a1a;color:#ccc;border:1px solid #444;border-radius:3px;cursor:pointer;line-height:1.2;';
    function el(tag, css, text, attrs) {
        var e = document.createElement(tag); if (css) e.style.cssText = css; if (text != null) e.textContent = text;
        if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
        return e;
    }
    function fmt(q, v) {
        if (q.log) return gammaOf(v).toFixed(2);
        var s = q.dec != null ? Number(v).toFixed(q.dec) : String(Math.round(v));
        return s + (q.unit || '');
    }
    function hueRange(P, q) { return (P.type === 'hueSat' && q.k === 'hue' && P.p.colorize) ? { min: 0, max: 360 } : (P.type === 'hueSat' && q.k === 'saturation' && P.p.colorize) ? { min: 0, max: 100 } : { min: q.min, max: q.max }; }
    function uiCtx(L) {
        return { el: el, BTN: BTN, clamp: clamp, ui: uiOf(L.id), set: setParam, fmt: fmt, util: util,
            end: function () { gesture = null; endFast(); },
            rerender: function () { if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel(); } };
    }
    function adjRows(L) {
        var P = L.pcAdj, T = TYPES[P.type], rows = [];
        var head = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-height:20px;', null, { 'data-pca-row': L.id });
        head.appendChild(el('span', 'font-size:8px;color:#888;flex:0 0 42px;min-width:42px;white-space:nowrap;', 'Adjust:'));
        head.appendChild(el('span', 'font-size:9px;color:#ffd86b;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', T.label));
        rows.push(head);
        var bar = el('div', 'display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;');
        var b1 = el('button', BTN, 'Reset', { type: 'button', 'class': 'layer-act-btn', 'data-pca': 'reset', 'data-pca-id': L.id, title: 'Put every slider back to its neutral position' });
        var b2 = el('button', BTN, 'Apply ↓', { type: 'button', 'class': 'layer-act-btn', 'data-pca': 'bake', 'data-pca-id': L.id, title: 'Bake this adjustment into the layer below and remove it (same as Merge Down)' });
        bar.appendChild(b1); bar.appendChild(b2); rows.push(bar);
        if (typeof T.uiTop === 'function') { try { T.uiTop(L, rows, uiCtx(L)); } catch (e) { try { console.warn('[pca] uiTop failed', e); } catch (_e) {} } }
        T.params.forEach(function (q) {
            if (q.hidden || (q.show && !q.show(P.p, uiOf(L.id)))) return;
            var r = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-width:0;');
            r.appendChild(el('span', 'font-size:8px;color:#888;flex:0 0 42px;min-width:42px;white-space:nowrap;', q.label + ':'));
            if (q.type === 'bool') {
                var cb = el('input', 'cursor:pointer;margin:0;', null, { type: 'checkbox', 'data-pca-bool': q.k, 'data-pca-id': L.id, 'aria-label': T.label + ' ' + q.label, title: q.label });
                if (P.p[q.k]) cb.checked = true;
                r.appendChild(cb); rows.push(r); return;
            }
            if (q.type === 'color') {
                var ci = el('input', 'width:34px;height:18px;padding:0;border:1px solid #444;background:none;cursor:pointer;', null, { type: 'color', value: P.p[q.k], 'data-pca-color': q.k, 'data-pca-id': L.id, 'aria-label': T.label + ' ' + q.label, title: q.label });
                r.appendChild(ci); rows.push(r); return;
            }
            var rg = hueRange(P, q);
            var inp = el('input', 'flex:1 1 0%;min-width:0;width:0;height:12px;cursor:pointer;', null, { type: 'range', min: rg.min, max: rg.max, step: q.step, value: P.p[q.k], 'data-pca-range': q.k, 'data-pca-id': L.id, 'aria-label': T.label + ' ' + q.label, title: T.label + ' ' + q.label + ' (double-click to reset)' });
            var num = el('span', 'font-size:8px;color:#ddd;flex:0 0 34px;text-align:right;white-space:nowrap;', fmt(q, P.p[q.k]), { 'data-pca-val': q.k });
            r.appendChild(inp); r.appendChild(num); rows.push(r);
        });
        if (typeof T.ui === 'function') { try { T.ui(L, rows, uiCtx(L)); } catch (e) { try { console.warn('[pca] ui failed', e); } catch (_e) {} } }
        rows.push(el('div', 'font-size:8px;line-height:1.35;color:#777;margin:0 0 6px;', T.hint + ' Paint the mask to limit where it applies; the chain button clips it to the layer below.'));
        rows.forEach(function (r) { r.setAttribute('data-pca-mine', '1'); });
        return rows;
    }
    function decorate() {
        if (off()) return;
        var panel = document.getElementById('layerPanelContent');
        if (!panel) return;
        wirePanel(panel);
        injectMenu();
        var sels = panel.querySelectorAll('select[data-layer-blend-control]');
        for (var i = 0; i < sels.length; i++) {
            var id = sels[i].getAttribute('data-layer-blend-control'), L = byId(id);
            if (!L || !L.pcAdj) continue;
            var blendRow = sels[i].parentElement;
            if (!blendRow || (blendRow.nextElementSibling && blendRow.nextElementSibling.hasAttribute('data-pca-row'))) continue;
            var at = blendRow.nextSibling;
            adjRows(L).forEach(function (r) { blendRow.parentNode.insertBefore(r, at); });
            hideNoOps(blendRow.parentNode);
        }
        var any = false;
        stack().forEach(function (l) { if (l && l.pcAdj) any = true; });
        if (any && typeof requestAnimationFrame === 'function') requestAnimationFrame(paintGlyphs);
    }
    // an adjustment layer has no pixels: the card's own Hue/Sat/Bright/Overlay rows and the pixel-only buttons would act on nothing
    function hideNoOps(root) {
        var kids = root.children, i, t;
        for (i = 0; i < kids.length; i++) {
            var k = kids[i];
            if (k.hasAttribute('data-pca-mine')) continue;
            t = (k.textContent || '').replace(/\s+/g, ' ').trim();
            if (/^(Hue|Sat|Bright|Overlay):/.test(t)) k.style.display = 'none';
        }
        var bs = root.querySelectorAll('button');
        for (i = 0; i < bs.length; i++) {
            t = (bs[i].textContent || '').trim().toUpperCase();
            if (t === 'MIRROR' || t === 'STROKE FX' || t === 'EXPORT' || t === 'MAKE ZONE') bs[i].style.display = 'none';
        }
    }
    function paintGlyphs() {   // layer thumbnails of adjustment layers: the half-filled circle every painter knows
        stack().forEach(function (l) {
            if (!l || !l.pcAdj) return;
            var c = document.getElementById('layerThumb_' + l.id);
            if (!c || !c.getContext) return;
            var g = c.getContext('2d'), w = c.width, h = c.height, r = Math.min(w, h) * 0.3;
            g.clearRect(0, 0, w, h); g.fillStyle = '#1b1b1b'; g.fillRect(0, 0, w, h);
            g.strokeStyle = '#ffd86b'; g.lineWidth = Math.max(1, w / 18);
            g.beginPath(); g.arc(w / 2, h / 2, r, 0, Math.PI * 2); g.stroke();
            g.fillStyle = '#ffd86b'; g.beginPath(); g.arc(w / 2, h / 2, r, -Math.PI / 2, Math.PI / 2); g.closePath(); g.fill();
        });
    }
    var collapseSub = null;   // [SPB-TLAY 2026-10-10 TL-18] set by injectMenu: folds the submenu so the Actions menu always opens collapsed
    function injectMenu(force) {
        var menu = document.getElementById('layerActionsMenu');
        if (!menu) return;
        var mb0 = document.getElementById('layerActionsMenuBtn');
        if (mb0 && !mb0.__pcaCollapse) { mb0.__pcaCollapse = true; mb0.addEventListener('click', function () { if (collapseSub) collapseSub(); }, true); }
        var old = menu.querySelector('[data-pca-menu]');
        if (old) { if (!force) return; old.parentNode.removeChild(old); }
        var items = menu.querySelectorAll('button[role="menuitem"]'), after = null;
        for (var i = 0; i < items.length; i++) if (/Blank layer/i.test(items[i].textContent)) after = items[i];
        var MI = 'display:block;width:100%;text-align:left;font-size:10px;padding:5px 8px;background:transparent;border:none;color:var(--text);border-radius:4px;cursor:pointer;';
        var wrap = el('div', '', null, { 'data-pca-menu': '1' });
        var top = el('button', MI, '+ Adjustment layer ▸', { type: 'button', role: 'menuitem', 'aria-haspopup': 'true', 'aria-expanded': 'false', title: 'Hue/Saturation, Levels, Brightness/Contrast ... as a layer you can mask, clip and turn off any time' });
        var sub = el('div', 'display:none;padding-left:8px;max-height:260px;overflow-y:auto;overflow-anchor:none;');
        collapseSub = function () { sub.style.display = 'none'; top.setAttribute('aria-expanded', 'false'); top.textContent = '+ Adjustment layer ▸'; };
        ORDER.forEach(function (ty) {
            var b = el('button', MI, TYPES[ty].label, { type: 'button', role: 'menuitem', 'data-pca-add': ty, title: TYPES[ty].hint });
            b.addEventListener('click', function (ev) {
                ev.stopPropagation();
                if (off()) return;
                menu.style.display = 'none'; collapseSub();
                var mb = document.getElementById('layerActionsMenuBtn'); if (mb) mb.setAttribute('aria-expanded', 'false');
                add(ty);
            });
            sub.appendChild(b);
        });
        top.addEventListener('click', function (ev) {
            ev.stopPropagation();
            var open = sub.style.display !== 'none';
            sub.style.display = open ? 'none' : 'block'; top.setAttribute('aria-expanded', String(!open));
            top.textContent = open ? '+ Adjustment layer ▸' : '+ Adjustment layer ▾';
            // [SPB-TLAY 2026-10-10 TL-18] the browser kept the submenu scrolled to its end after it was shown (first rows hidden under the Actions button): always open at the top
            if (!open) { sub.scrollTop = 0; if (typeof requestAnimationFrame === 'function') requestAnimationFrame(function () { sub.scrollTop = 0; }); }
        });
        wrap.appendChild(top); wrap.appendChild(sub);
        if (after && after.parentNode) after.parentNode.insertBefore(wrap, after.nextSibling);
        else menu.insertBefore(wrap, menu.firstChild);
    }
    var wired = [];
    function wirePanel(panel) {
        if (panel.__pcaWired === wired) return;
        if (typeof panel.__pcaOff === 'function') { try { panel.__pcaOff(); } catch (_e) {} }
        panel.__pcaWired = wired;
        var hs = [];
        var on = function (type, fn) { panel.addEventListener(type, fn, true); hs.push([type, fn]); };
        panel.__pcaOff = function () { hs.forEach(function (h) { panel.removeEventListener(h[0], h[1], true); }); hs = []; panel.__pcaWired = null; panel.__pcaOff = null; };
        wired.push(panel);
        on('click', function (ev) {
            var t = ev.target && ev.target.closest ? ev.target.closest('[data-pca]') : null;
            if (!t || off()) return;
            ev.stopPropagation(); ev.preventDefault();
            var act = t.getAttribute('data-pca'), id = t.getAttribute('data-pca-id');
            if (act === 'reset') reset(id);
            else if (act === 'bake') { var i = indexOf(id); if (i >= 0) bakeDown(i); }
        });
        on('input', function (ev) {
            var t = ev.target; if (!t || !t.getAttribute || off()) return;
            var ck = t.getAttribute('data-pca-color');
            if (ck) { setParam(t.getAttribute('data-pca-id'), ck, t.value, false); ev.stopPropagation(); return; }
            var key = t.getAttribute('data-pca-range'); if (!key) return;
            var id = t.getAttribute('data-pca-id'), L = byId(id); if (!L || !L.pcAdj) return;
            var q = null; TYPES[L.pcAdj.type].params.forEach(function (x) { if (x.k === key) q = x; });
            var v = Number(t.value);
            var lab = t.parentNode.querySelector('[data-pca-val]'); if (lab && q) lab.textContent = fmt(q, v);
            setParam(id, key, v, false);
            ev.stopPropagation();
        });
        on('change', function (ev) {
            var t = ev.target; if (!t || !t.getAttribute || off()) return;
            var key = t.getAttribute('data-pca-range'), bkey = t.getAttribute('data-pca-bool');
            if (t.getAttribute('data-pca-color')) { gesture = null; endFast(); ev.stopPropagation(); return; }
            if (bkey) { setParam(t.getAttribute('data-pca-id'), bkey, !!t.checked, true); ev.stopPropagation(); return; }
            if (!key) return;
            gesture = null; endFast();
            ev.stopPropagation();
        });
        on('dblclick', function (ev) {
            var t = ev.target; if (!t || !t.getAttribute || off()) return;
            var key = t.getAttribute('data-pca-range'); if (!key) return;
            var id = t.getAttribute('data-pca-id'), L = byId(id); if (!L || !L.pcAdj) return;
            var q = null; TYPES[L.pcAdj.type].params.forEach(function (x) { if (x.k === key) q = x; });
            if (!q) return;
            var def = q.def; if (L.pcAdj.type === 'hueSat' && L.pcAdj.p.colorize && key === 'saturation') def = 25;
            gesture = null; setParam(id, key, def, true);
            ev.stopPropagation(); ev.preventDefault();
        });
    }
    var prevPanel = window.renderLayerPanel;
    if (typeof prevPanel === 'function' && !prevPanel.__pca) {
        var wpanel = function () {
            var r = prevPanel.apply(this, arguments);
            try { decorate(); } catch (e) { try { console.warn('[pca] decorate failed', e); } catch (_e) {} }
            return r;
        };
        wpanel.__pca = true;
        for (var kp in prevPanel) { try { if (Object.prototype.hasOwnProperty.call(prevPanel, kp)) wpanel[kp] = prevPanel[kp]; } catch (_e2) {} }
        window.renderLayerPanel = wpanel;
        undoers.push(function () { if (window.renderLayerPanel === wpanel) window.renderLayerPanel = prevPanel; });
    }

    var util = { el: el, BTN: BTN, clamp: clamp, mk: mk, cx: cx, freeze: freeze, deepFreeze: deepFreeze, clone: clone, SRGB_DEC: SRGB_DEC, enc: enc, gammaOf: gammaOf, lutFor: lutFor, lutLoop: lutLoop };
    window.SPBPcAdjust = {
        version: VERSION, stats: stats, off: off, TYPES: TYPES, ORDER: ORDER, registerType: registerType, util: util, uiState: uiState,
        setHistHook: function (fn) { histHook = typeof fn === 'function' ? fn : null; },
        add: add, setParam: setParam, reset: reset, bake: function (id) { var i = indexOf(id); return i >= 0 ? bakeDown(i) : false; },
        serialize: serialize, deserialize: deserialize, decorate: decorate, defaults: defaults, isIdentity: isIdentity,
        processGpu: function (type, params, canvas, k) {   // test hook: GPU path on a copy of the canvas, returns the result canvas (or null)
            var P = { type: type, p: Object.assign(defaults(type), params || {}) };
            if (!gpuRun(P, canvas, null, k == null ? 1 : k)) return null;
            var o = mk(canvas.width, canvas.height), g = cx(o); g.drawImage(gpu.c, 0, gpu.c.height - canvas.height, canvas.width, canvas.height, 0, 0, canvas.width, canvas.height); return o;
        },
        gpuInfo: function () { gpuInit(); return { ok: gpu.ok, renderer: (function () { try { var e = gpu.gl.getExtension('WEBGL_debug_renderer_info'); return e ? gpu.gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'n/a'; } catch (_e) { return 'n/a'; } })() }; },
        process: function (type, params, rgba, sa, k) { processBytes({ type: type, p: Object.assign(defaults(type), params || {}) }, rgba, rgba.length >> 2, sa || null, k == null ? 1 : k); return rgba; },
        uninstall: function () {
            undoers.splice(0).reverse().forEach(function (f) { try { f(); } catch (_e) {} });
            wired.splice(0).forEach(function (p) { try { if (p.__pcaOff) p.__pcaOff(); } catch (_e) {} });
            var m = document.querySelector('[data-pca-menu]'); if (m && m.parentNode) m.parentNode.removeChild(m);
            delete window.SPBPcAdjust;
        }
    };
    try { injectMenu(); } catch (_e) {}
    setTimeout(function () { try { if (!off()) gpuInit(); } catch (_e) {} }, 2500);   // compile the shader before the first slider drag
})();
