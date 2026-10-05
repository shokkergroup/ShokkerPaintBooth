/*
 * SPB-93 Pass 154 (2026-07-19)
 * Owner verdict: the top-row tools must feel natural and Photoshop-quality.
 *
 * Pure pixel mutators used by both committed Layer adjustments and their live
 * previews. Keeping the math out of the canvas dispatcher makes preview and
 * Apply byte-identical instead of maintaining two subtly different filters.
 * Tool-quality metric: blind slider feedback 0/2 -> live/commit parity 2/2.
 */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBAdjustmentPreview = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    function requirePixels(pixels) {
        if (!pixels || typeof pixels.length !== 'number' || pixels.length % 4 !== 0) {
            throw new TypeError('RGBA pixels must be an array-like value whose length is divisible by four');
        }
        return pixels;
    }

    function applyBrightnessContrast(pixels, brightness, contrast) {
        var data = requirePixels(pixels);
        var b = Number.isFinite(Number(brightness)) ? Number(brightness) : 0;
        var c = (Number.isFinite(Number(contrast)) ? Number(contrast) : 0) / 100;
        var factor = (1 + c) / (1 - (c < 0.99 ? c : 0.99));
        for (var i = 0; i < data.length; i += 4) {
            data[i] = (factor * (data[i] + b - 128) + 128 + 0.5) | 0;
            data[i + 1] = (factor * (data[i + 1] + b - 128) + 128 + 0.5) | 0;
            data[i + 2] = (factor * (data[i + 2] + b - 128) + 128 + 0.5) | 0;
        }
        return data;
    }

    function applyHueSaturation(pixels, hueShift, saturation, lightness) {
        var data = requirePixels(pixels);
        var hs = (Number.isFinite(Number(hueShift)) ? Number(hueShift) : 0) / 360;
        var sat = 1 + (Number.isFinite(Number(saturation)) ? Number(saturation) : 0) / 100;
        var light = (Number.isFinite(Number(lightness)) ? Number(lightness) : 0) / 100;
        var inv255 = 1 / 255;

        function hue2rgb(p, q, t) {
            if (t < 0) t += 1;
            else if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 0.5) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        }

        for (var i = 0; i < data.length; i += 4) {
            var r = data[i] * inv255;
            var g = data[i + 1] * inv255;
            var b = data[i + 2] * inv255;
            var max = r > g ? (r > b ? r : b) : (g > b ? g : b);
            var min = r < g ? (r < b ? r : b) : (g < b ? g : b);
            var h = 0;
            var s = 0;
            var inputLightness = (max + min) * 0.5;
            if (max !== min) {
                var delta = max - min;
                s = inputLightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);
                if (max === r) h = ((g - b) / delta + (g < b ? 6 : 0)) / 6;
                else if (max === g) h = ((b - r) / delta + 2) / 6;
                else h = ((r - g) / delta + 4) / 6;
            }
            h = (h + hs) % 1;
            if (h < 0) h += 1;
            var outputSaturation = s * sat;
            if (outputSaturation < 0) outputSaturation = 0;
            else if (outputSaturation > 1) outputSaturation = 1;
            var outputLightness = inputLightness + light;
            if (outputLightness < 0) outputLightness = 0;
            else if (outputLightness > 1) outputLightness = 1;
            var rr;
            var gg;
            var bb;
            if (outputSaturation === 0) {
                rr = gg = bb = outputLightness;
            } else {
                var q = outputLightness < 0.5
                    ? outputLightness * (1 + outputSaturation)
                    : outputLightness + outputSaturation - outputLightness * outputSaturation;
                var p = 2 * outputLightness - q;
                rr = hue2rgb(p, q, h + 1 / 3);
                gg = hue2rgb(p, q, h);
                bb = hue2rgb(p, q, h - 1 / 3);
            }
            data[i] = (rr * 255 + 0.5) | 0;
            data[i + 1] = (gg * 255 + 0.5) | 0;
            data[i + 2] = (bb * 255 + 0.5) | 0;
        }
        return data;
    }

    /*
     * SPB-SIMPLIFY-2026-07-19m (owner: "a lot of the ADJUST tools don't seem to work right").
     * Root cause: only 2 of the 8 ADJUST tools had a preview mutator, so the other six either
     * moved a slider with NO visual feedback (adjust blind, hope, Apply) or fired instantly and
     * destructively with just a toast. These four are byte-identical ports of the committed
     * math already in paint-booth-3-canvas.js (adjustVibrance / adjustColorTemperature /
     * desaturateCanvas / invertCanvasColors) so live preview and Apply can never diverge.
     */
    function applyVibrance(pixels, amount) {
        var d = requirePixels(pixels);
        var a = Number.isFinite(Number(amount)) ? Number(amount) : 25;
        if (a < -100) a = -100; else if (a > 100) a = 100;
        var scale = a / 100;
        for (var i = 0; i < d.length; i += 4) {
            var r = d[i], g = d[i + 1], b = d[i + 2];
            var mx = r > g ? (r > b ? r : b) : (g > b ? g : b);
            var mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
            var sat = mx > 0 ? (mx - mn) / mx : 0;
            var boost = scale * (1 - sat);
            var avg = (r + g + b) * 0.3333333333333333;
            d[i] = (r + (r - avg) * boost + 0.5) | 0;
            d[i + 1] = (g + (g - avg) * boost + 0.5) | 0;
            d[i + 2] = (b + (b - avg) * boost + 0.5) | 0;
        }
        return d;
    }

    function applyColorTemperature(pixels, shift) {
        var d = requirePixels(pixels);
        var s = Number.isFinite(Number(shift)) ? Number(shift) : 0;
        if (s < -100) s = -100; else if (s > 100) s = 100;
        var rAdd = s > 0 ? s * 0.5 : 0;
        var bAdd = s < 0 ? -s * 0.5 : 0;
        var gAdd = s > 0 ? s * 0.1 : s * 0.05;
        for (var i = 0; i < d.length; i += 4) {
            d[i] = (d[i] + rAdd + 0.5) | 0;
            d[i + 1] = (d[i + 1] + gAdd + 0.5) | 0;
            d[i + 2] = (d[i + 2] + bAdd + 0.5) | 0;
        }
        return d;
    }

    /* Amount 0-100 so Grayscale/Invert become previewable, mixable dialogs instead of
       instant one-shot destruction. 100 == the classic full-strength result. */
    function applyDesaturate(pixels, amount) {
        var d = requirePixels(pixels);
        var amt = Number.isFinite(Number(amount)) ? Number(amount) : 100;
        if (amt < 0) amt = 0; else if (amt > 100) amt = 100;
        var k = amt / 100;
        if (k === 0) return d;
        for (var i = 0; i < d.length; i += 4) {
            if (d[i + 3] === 0) continue;
            var gray = (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2] + 0.5) | 0;
            d[i] = (d[i] + (gray - d[i]) * k + 0.5) | 0;
            d[i + 1] = (d[i + 1] + (gray - d[i + 1]) * k + 0.5) | 0;
            d[i + 2] = (d[i + 2] + (gray - d[i + 2]) * k + 0.5) | 0;
        }
        return d;
    }

    function applyInvert(pixels, amount) {
        var d = requirePixels(pixels);
        var amt = Number.isFinite(Number(amount)) ? Number(amount) : 100;
        if (amt < 0) amt = 0; else if (amt > 100) amt = 100;
        var k = amt / 100;
        if (k === 0) return d;
        for (var i = 0; i < d.length; i += 4) {
            if (d[i + 3] === 0) continue;
            d[i] = (d[i] + ((255 - d[i]) - d[i]) * k + 0.5) | 0;
            d[i + 1] = (d[i + 1] + ((255 - d[i + 1]) - d[i + 1]) * k + 0.5) | 0;
            d[i + 2] = (d[i + 2] + ((255 - d[i + 2]) - d[i + 2]) * k + 0.5) | 0;
        }
        return d;
    }

    /*
     * SPB-93 T35 (2026-08-08), owner: tools must feel like Photoshop/GIMP and
     * SOURCE must react while controls move. Gradient Map and Color Replace
     * were the last two ADJUST dialogs with apply-only feedback (live 0/2 ->
     * 2/2). Keep their preview and commit math byte-identical here.
     */
    function parseHex(hex, fallback) {
        var raw = typeof hex === 'string' ? hex.trim() : '';
        if (/^[0-9a-fA-F]{6}$/.test(raw)) raw = '#' + raw;
        if (!/^#[0-9a-fA-F]{6}$/.test(raw)) raw = fallback;
        return [
            parseInt(raw.slice(1, 3), 16),
            parseInt(raw.slice(3, 5), 16),
            parseInt(raw.slice(5, 7), 16),
        ];
    }

    function applyGradientMap(pixels, darkHex, lightHex) {
        var d = requirePixels(pixels);
        var dark = parseHex(darkHex, '#000000');
        var light = parseHex(lightHex, '#ffffff');
        var cR = 0.299 / 255, cG = 0.587 / 255, cB = 0.114 / 255;
        for (var i = 0; i < d.length; i += 4) {
            if (d[i + 3] === 0) continue;
            var lum = d[i] * cR + d[i + 1] * cG + d[i + 2] * cB;
            var inv = 1 - lum;
            d[i] = (dark[0] * inv + light[0] * lum + 0.5) | 0;
            d[i + 1] = (dark[1] * inv + light[1] * lum + 0.5) | 0;
            d[i + 2] = (dark[2] * inv + light[2] * lum + 0.5) | 0;
        }
        return d;
    }

    function applyColorReplace(pixels, targetHex, replacementHex, tolerance) {
        var d = requirePixels(pixels);
        var target = parseHex(targetHex, '#000000');
        var replacement = parseHex(replacementHex, '#ffffff');
        var tol = Number.isFinite(Number(tolerance)) ? Number(tolerance) : 40;
        if (tol < 0) tol = 0; else if (tol > 120) tol = 120;
        var tol2 = tol * tol * 3;
        var invSqrtTol = tol2 > 0 ? 1 / Math.sqrt(tol2) : 0;
        for (var i = 0; i < d.length; i += 4) {
            if (d[i + 3] === 0) continue;
            var dr = d[i] - target[0], dg = d[i + 1] - target[1], db = d[i + 2] - target[2];
            var dist2 = dr * dr + dg * dg + db * db;
            if (dist2 > tol2) continue;
            var blend = tol2 > 0 ? 1 - Math.sqrt(dist2) * invSqrtTol : 1;
            var inv = 1 - blend;
            d[i] = (d[i] * inv + replacement[0] * blend + 0.5) | 0;
            d[i + 1] = (d[i + 1] * inv + replacement[1] * blend + 0.5) | 0;
            d[i + 2] = (d[i + 2] * inv + replacement[2] * blend + 0.5) | 0;
        }
        return d;
    }

    return Object.freeze({
        applyBrightnessContrast: applyBrightnessContrast,
        applyHueSaturation: applyHueSaturation,
        applyVibrance: applyVibrance,
        applyColorTemperature: applyColorTemperature,
        applyDesaturate: applyDesaturate,
        applyInvert: applyInvert,
        applyGradientMap: applyGradientMap,
        applyColorReplace: applyColorReplace,
    });
});
