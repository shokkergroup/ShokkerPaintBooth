/*
 * SPB-93 Pass 153 (2026-07-19)
 * Owner verdict: tools must be suited specifically to painting/editing car templates.
 * Pure Layer-placement geometry only: it never selects a target, mutates pixels,
 * touches Zone masks, or owns history. The canvas controller previews/commits.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLayerSelectionPlacement = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    function finite(value) {
        const number = Number(value);
        return Number.isFinite(number) ? number : null;
    }

    function normalizeRect(rect) {
        if (!rect) return null;
        const values = Array.isArray(rect)
            ? rect.slice(0, 4)
            : [rect.x1, rect.y1, rect.x2, rect.y2];
        if (values.length < 4) return null;
        const x1 = finite(values[0]);
        const y1 = finite(values[1]);
        const x2 = finite(values[2]);
        const y2 = finite(values[3]);
        if ([x1, y1, x2, y2].some(value => value === null)) return null;
        const left = Math.min(x1, x2);
        const top = Math.min(y1, y2);
        const right = Math.max(x1, x2);
        const bottom = Math.max(y1, y2);
        if (right - left < 1 || bottom - top < 1) return null;
        return {
            x1: left,
            y1: top,
            x2: right,
            y2: bottom,
            width: right - left,
            height: bottom - top,
        };
    }

    function planFit(sourceRect, targetRect, options) {
        const source = normalizeRect(sourceRect);
        const target = normalizeRect(targetRect);
        if (!source || !target) return null;

        const opts = options || {};
        const paddingRatio = Math.max(0, Math.min(0.4,
            Number.isFinite(Number(opts.paddingRatio)) ? Number(opts.paddingRatio) : 0.06));
        const innerWidth = Math.max(1, target.width * (1 - paddingRatio * 2));
        const innerHeight = Math.max(1, target.height * (1 - paddingRatio * 2));
        let scale = Math.min(innerWidth / source.width, innerHeight / source.height);
        const maxScale = Math.max(0.01,
            Number.isFinite(Number(opts.maxScale)) ? Number(opts.maxScale) : 8);
        scale = Math.max(0.01, Math.min(maxScale, scale));

        const width = Math.max(1, Math.round(source.width * scale));
        const height = Math.max(1, Math.round(source.height * scale));
        const centerX = (target.x1 + target.x2) / 2;
        const centerY = (target.y1 + target.y2) / 2;
        const x1 = Math.round(centerX - width / 2);
        const y1 = Math.round(centerY - height / 2);

        return Object.freeze({
            centerX,
            centerY,
            width,
            height,
            scale,
            paddingRatio,
            bbox: Object.freeze([x1, y1, x1 + width, y1 + height]),
            source: Object.freeze(source),
            target: Object.freeze(target),
        });
    }

    return Object.freeze({ normalizeRect, planFit });
});
