/* Photoshop-parity layer blend modes for Canvas2D, ported from PhotoCraft crates/color/src/blend.rs
 * (blend_channel, blend_rgb, composite) and the PSD blend-mode list in crates/psd/src/blend.rs.
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0 - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript for Shokker Paint Booth (typed arrays, straight-alpha RGBA8 ImageData).
 * Lane TOOLS-LAYERS (ticket TL-14), 2026-10-09. Owner direction: "tools feel like a feature, not half assed".
 *
 * Canvas2D has no native Linear Burn / Linear Dodge (Add) / Vivid Light / Linear Light / Pin Light / Hard Mix /
 * Darker Color / Lighter Color / Subtract / Divide / Dissolve, so a layer using one of them (for example a
 * Photoshop file with a Linear Dodge glow) used to be imported as Normal. SPBPcBlend.compositeRegion() blends
 * a source RGBA buffer over a backdrop RGBA buffer with the exact W3C/PDF general formula PhotoCraft uses:
 *     ao = as + ab (1 - as)
 *     ao Co = (1 - as) ab Cb + (1 - ab) as Cs + as ab B(Cb, Cs)
 * The existing native modes (Multiply, Screen, ...) stay on Canvas2D.
 * Disable everything with window.SPB_TLAY_OFF = true (this file only defines maths; callers check the switch).
 */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcBlend = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // id -> { label, psd key (psd-tools enum name), ch: separable channel fn or null }
    var EDGE = 1e-4;
    function colorBurn(cb, cs) { return cb >= 1 ? 1 : (cs <= 0 ? 0 : 1 - Math.min((1 - cb) / cs, 1)); }
    function colorDodge(cb, cs) { return cb <= 0 ? 0 : (cs >= 1 ? 1 : Math.min(cb / (1 - cs), 1)); }
    function vividHardMix(cb, cs) {
        if (cs <= 0.5) {
            if (cb >= 1 - EDGE) return 1;
            if (cs <= 0) return 0;
            return 1 - Math.min((1 - cb) / (2 * cs), 1);
        }
        if (cb <= EDGE) return 0;
        if (cs >= 1) return 1;
        return Math.min(cb / (2 * (1 - cs)), 1);
    }
    var CH = {
        linburn: function (cb, cs) { return Math.max(cb + cs - 1, 0); },
        lindodge: function (cb, cs) { return Math.min(cb + cs, 1); },
        vividlt: function (cb, cs) {
            if (cs <= 0) return 0;
            if (cs >= 1) return 1;
            return cs <= 0.5 ? colorBurn(cb, 2 * cs) : colorDodge(cb, 2 * (cs - 0.5));
        },
        linlight: function (cb, cs) { var v = cb + 2 * cs - 1; return v < 0 ? 0 : (v > 1 ? 1 : v); },
        pinlight: function (cb, cs) { return cs <= 0.5 ? Math.min(cb, 2 * cs) : Math.max(cb, 2 * cs - 1); },
        hardmix: function (cb, cs) { return vividHardMix(cb, cs) >= 0.5 - 1e-6 ? 1 : 0; },
        subtract: function (cb, cs) { return Math.max(cb - cs, 0); },
        divide: function (cb, cs) { return cs <= 0 ? (cb <= 0 ? 0 : 1) : Math.min(cb / cs, 1); },
        // native Canvas2D id whose Skia maths differs from Photoshop: exact PhotoCraft version
        'soft-light': function (cb, cs) { return cs <= 0.5 ? 2 * cb * cs + cb * cb * (1 - 2 * cs) : 2 * cb * (1 - cs) + Math.sqrt(Math.max(cb, 0)) * (2 * cs - 1); }
    };
    var MODES = {
        linburn:  { label: 'Linear Burn',   psd: 'LINEAR_BURN' },
        lindodge: { label: 'Linear Dodge (Add)', psd: 'LINEAR_DODGE' },
        vividlt:  { label: 'Vivid Light',   psd: 'VIVID_LIGHT' },
        linlight: { label: 'Linear Light',  psd: 'LINEAR_LIGHT' },
        pinlight: { label: 'Pin Light',     psd: 'PIN_LIGHT' },
        hardmix:  { label: 'Hard Mix',      psd: 'HARD_MIX' },
        darkcol:  { label: 'Darker Color',  psd: 'DARKER_COLOR' },
        lightcol: { label: 'Lighter Color', psd: 'LIGHTER_COLOR' },
        subtract: { label: 'Subtract',      psd: 'SUBTRACT' },
        divide:   { label: 'Divide',        psd: 'DIVIDE' },
        dissolve: { label: 'Dissolve',      psd: 'DISSOLVE' },
        // existing Canvas2D mode re-done with the Photoshop maths (same id, not in the new-mode list). Measured against the
        // PhotoCraft CLI on opaque pixels: Canvas2D soft-light is off by up to 12 levels; multiply, screen, overlay, darken,
        // lighten, hard-light, difference, exclusion, colour dodge/burn, hue, saturation, colour and luminosity are within 1-5.
        'soft-light':  { label: 'Soft Light',  psd: 'SOFT_LIGHT',  override: true }
    };
    var ORDER = ['dissolve', 'linburn', 'darkcol', 'lindodge', 'lightcol', 'vividlt', 'linlight', 'pinlight', 'hardmix', 'subtract', 'divide'];

    function has(id) { return Object.prototype.hasOwnProperty.call(MODES, id); }
    // psd-tools / PhotoCraft key ("BlendMode.LINEAR_DODGE", "linear dodge", "linear_dodge") -> our id or null
    function fromPsdKey(key) {
        var k = String(key || '').replace(/^BlendMode\./i, '').trim().toUpperCase().replace(/[ -]+/g, '_');
        for (var id in MODES) if (MODES[id].psd === k) return id;
        return null;
    }

    // 32-bit integer hash -> [0,1): stable per pixel so Dissolve does not shimmer between recomposites.
    function hash01(x, y) {
        var h = (Math.imul(x | 0, 0x9E3779B1) ^ Math.imul(y | 0, 0x85EBCA77)) >>> 0;
        h = Math.imul(h ^ (h >>> 15), 0x2C1B3C6D) >>> 0;
        h = Math.imul(h ^ (h >>> 12), 0x297A2D39) >>> 0;
        return ((h ^ (h >>> 15)) >>> 0) / 4294967296;
    }

    /* compositeRegion: blend src over bd in place.
     *   bd, src : Uint8ClampedArray RGBA straight alpha, same length (n*4)
     *   w       : pixel width of the region (for Dissolve coordinates), x0/y0 = region origin on the canvas
     *   mode    : one of MODES ids, opacity01 : layer opacity 0..1
     * Returns the number of pixels touched. */
    function compositeRegion(bd, src, n, mode, opacity01, w, x0, y0) {
        if (!has(mode)) return 0;
        var op = opacity01 < 0 ? 0 : (opacity01 > 1 ? 1 : opacity01);
        var touched = 0;
        var lut = lutFor(mode);   // 64K-entry table of B(cb, cs) over every 8-bit pair: no per-channel function call in the loop
        var dissolve = mode === 'dissolve';
        var darker = mode === 'darkcol', lighter = mode === 'lightcol';
        var opf = op / 255;
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            var sa = src[o + 3];
            if (sa === 0) continue;
            var as = sa * opf;
            if (dissolve) {
                as = hash01((i % w) + x0, ((i / w) | 0) + y0) < as ? 1 : 0;
            }
            if (as <= 0) continue;
            var rb = bd[o], gb = bd[o + 1], bb8 = bd[o + 2], ba = bd[o + 3];
            var rs = src[o], gs = src[o + 1], bs8 = src[o + 2];
            var br, bg, bb;   // B(Cb, Cs) on the 0..255 scale
            if (lut) { br = lut[(rb << 8) | rs] * 255; bg = lut[(gb << 8) | gs] * 255; bb = lut[(bb8 << 8) | bs8] * 255; }
            else if (dissolve) { br = rs; bg = gs; bb = bs8; }
            else {
                var lb = 0.3 * rb + 0.59 * gb + 0.11 * bb8, ls = 0.3 * rs + 0.59 * gs + 0.11 * bs8;
                var pickS = darker ? (ls < lb) : (ls > lb);
                if (pickS) { br = rs; bg = gs; bb = bs8; } else { br = rb; bg = gb; bb = bb8; }
            }
            if (ba === 255) {   // opaque backdrop (a livery composite): ao = 1, so Co = (1 - as) Cb + as B
                var ia = 1 - as;
                bd[o]     = Math.round(ia * rb + as * br);
                bd[o + 1] = Math.round(ia * gb + as * bg);
                bd[o + 2] = Math.round(ia * bb8 + as * bb);
                touched++;
                continue;
            }
            var ab = ba / 255;
            var ao = as + ab * (1 - as);
            if (ao <= 0) { bd[o] = bd[o + 1] = bd[o + 2] = bd[o + 3] = 0; continue; }
            var k1 = (1 - as) * ab, k2 = (1 - ab) * as, k3 = as * ab;
            bd[o]     = Math.round((k1 * rb + k2 * rs + k3 * br) / ao);
            bd[o + 1] = Math.round((k1 * gb + k2 * gs + k3 * bg) / ao);
            bd[o + 2] = Math.round((k1 * bb8 + k2 * bs8 + k3 * bb) / ao);
            bd[o + 3] = Math.round(ao * 255);
            touched++;
        }
        return touched;
    }

    var LUTS = {};
    function lutFor(mode) {
        var f = CH[mode];
        if (!f) return null;
        var t = LUTS[mode];
        if (t) return t;
        t = LUTS[mode] = new Float32Array(65536);
        for (var cb = 0; cb < 256; cb++) for (var cs = 0; cs < 256; cs++) t[(cb << 8) | cs] = f(cb / 255, cs / 255);
        return t;
    }

    function isOverride(id) { return has(id) && !!MODES[id].override; }

    return { MODES: MODES, ORDER: ORDER, has: has, isOverride: isOverride, fromPsdKey: fromPsdKey, compositeRegion: compositeRegion, hash01: hash01 };
});
