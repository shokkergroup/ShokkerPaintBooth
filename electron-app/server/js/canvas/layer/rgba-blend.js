(function initSPBRgbaBlend(global) {
    'use strict';

    function clamp01(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return 0;
        return Math.max(0, Math.min(1, number));
    }

    function writePixel(data, index, red, green, blue, alpha, apply) {
        const nextRed = Math.max(0, Math.min(255, Math.round(red)));
        const nextGreen = Math.max(0, Math.min(255, Math.round(green)));
        const nextBlue = Math.max(0, Math.min(255, Math.round(blue)));
        const nextAlpha = Math.max(0, Math.min(255, Math.round(alpha)));
        const changed = data[index] !== nextRed || data[index + 1] !== nextGreen
            || data[index + 2] !== nextBlue || data[index + 3] !== nextAlpha;
        if (changed && apply !== false) {
            data[index] = nextRed;
            data[index + 1] = nextGreen;
            data[index + 2] = nextBlue;
            data[index + 3] = nextAlpha;
        }
        return changed;
    }

    // SPB-93 Pass 54 (2026-07-17), owner verdict: tools must feel natural.
    // Straight-RGBA lerp turned 25%-opacity red on transparency into dark red
    // [64,0,0,64]. Source-over keeps straight color [255,0,0,64], matching
    // painter expectations and preventing black/gray fringes on layer edges.
    function sourceOverPixel(data, index, red, green, blue, sourceAlphaByte, coverage, apply) {
        const sourceAlpha = clamp01((Number(sourceAlphaByte) || 0) / 255) * clamp01(coverage);
        if (sourceAlpha <= 0) return false;
        const destinationAlpha = data[index + 3] / 255;
        const inverseSource = 1 - sourceAlpha;
        const outputAlpha = sourceAlpha + destinationAlpha * inverseSource;
        if (outputAlpha <= 1e-8) return writePixel(data, index, 0, 0, 0, 0, apply);
        const destinationWeight = destinationAlpha * inverseSource;
        return writePixel(
            data,
            index,
            (Number(red) * sourceAlpha + data[index] * destinationWeight) / outputAlpha,
            (Number(green) * sourceAlpha + data[index + 1] * destinationWeight) / outputAlpha,
            (Number(blue) * sourceAlpha + data[index + 2] * destinationWeight) / outputAlpha,
            outputAlpha * 255,
            apply
        );
    }

    // Interpolate between two pixel states in premultiplied-alpha space.
    // Unlike source-over, amount=1 restores the source RGBA exactly, including
    // transparent history pixels; partial restores never drag hidden black RGB
    // into a visible soft edge.
    function mixPixel(data, index, sourceData, sourceIndex, amount) {
        const mix = clamp01(amount);
        if (mix <= 0) return false;
        if (mix >= 1) {
            return writePixel(
                data,
                index,
                sourceData[sourceIndex],
                sourceData[sourceIndex + 1],
                sourceData[sourceIndex + 2],
                sourceData[sourceIndex + 3]
            );
        }
        const destinationAlpha = data[index + 3] / 255;
        const sourceAlpha = sourceData[sourceIndex + 3] / 255;
        const inverseMix = 1 - mix;
        const outputAlpha = destinationAlpha * inverseMix + sourceAlpha * mix;
        if (outputAlpha <= 1e-8) return writePixel(data, index, 0, 0, 0, 0);
        return writePixel(
            data,
            index,
            (data[index] * destinationAlpha * inverseMix + sourceData[sourceIndex] * sourceAlpha * mix) / outputAlpha,
            (data[index + 1] * destinationAlpha * inverseMix + sourceData[sourceIndex + 1] * sourceAlpha * mix) / outputAlpha,
            (data[index + 2] * destinationAlpha * inverseMix + sourceData[sourceIndex + 2] * sourceAlpha * mix) / outputAlpha,
            outputAlpha * 255
        );
    }

    global.SPBRgbaBlend = Object.freeze({
        sourceOverPixel,
        mixPixel,
        version: '1.1.0-spb93-pass55-fill-alpha-compositing',
    });
})(typeof window !== 'undefined' ? window : globalThis);
