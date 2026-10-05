/**
 * SPB-93 tick 16 (2026-07-15) — Layer-only Recolor color math.
 * Owner verdict: tools still feel "jinky/off" and should behave more like Photoshop.
 * Movement: flat RGB replacement + one-dab Flow -> source-lightness-preserving Color
 * mode + immutable stroke matching so repeated low-Flow dabs build naturally.
 */
(function () {
    'use strict';

    let strokeSource = null;

    function rgbToHsl(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        const lightness = (max + min) / 2;
        if (max === min) return [0, 0, lightness];
        const delta = max - min;
        const saturation = lightness > 0.5
            ? delta / (2 - max - min)
            : delta / (max + min);
        let hue;
        if (max === r) hue = (g - b) / delta + (g < b ? 6 : 0);
        else if (max === g) hue = (b - r) / delta + 2;
        else hue = (r - g) / delta + 4;
        return [hue / 6, saturation, lightness];
    }

    function hueToRgb(p, q, t) {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
    }

    function hslToRgb(h, s, l) {
        if (s === 0) {
            const gray = Math.round(l * 255);
            return [gray, gray, gray];
        }
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        return [
            Math.round(hueToRgb(p, q, h + 1 / 3) * 255),
            Math.round(hueToRgb(p, q, h) * 255),
            Math.round(hueToRgb(p, q, h - 1 / 3) * 255)
        ];
    }

    function colorizePreservingLightness(sr, sg, sb, rr, rg, rb) {
        const source = rgbToHsl(sr, sg, sb);
        const replacement = rgbToHsl(rr, rg, rb);
        return hslToRgb(replacement[0], replacement[1], source[2]);
    }

    function beginStroke(data) {
        strokeSource = data ? new Uint8ClampedArray(data) : null;
        return strokeSource;
    }

    function getStrokeSource(currentData) {
        return strokeSource && currentData && strokeSource.length === currentData.length
            ? strokeSource
            : currentData;
    }

    function endStroke() {
        strokeSource = null;
    }

    const api = {
        version: '1.0.0-spb93-tick16',
        rgbToHsl,
        hslToRgb,
        colorizePreservingLightness,
        beginStroke,
        getStrokeSource,
        endStroke
    };
    window.SPBRecolorBrush = api;
    document.documentElement.dataset.spbRecolorBrush = 'ready';
})();
