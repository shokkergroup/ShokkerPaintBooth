(function (global) {
    'use strict';

    var MIN_SCALE = 0.05;
    var MAX_SCALE = 5.0;
    var STEP = 0.05;

    function normalizeScale(value, fallback) {
        var parsed = Number(value);
        if (!Number.isFinite(parsed)) parsed = Number(fallback);
        if (!Number.isFinite(parsed)) parsed = 1.0;
        parsed = Number((Math.round(parsed / STEP) * STEP).toFixed(2));
        return Math.max(MIN_SCALE, Math.min(MAX_SCALE, parsed));
    }

    function isIndependent(zone) {
        return !!zone && zone.specScaleMode === 'independent';
    }

    function resolve(zone) {
        if (!zone) return 1.0;
        if (isIndependent(zone)) {
            return normalizeScale(zone.specScale, 1.0);
        }
        return normalizeScale(zone.baseScale, 1.0);
    }

    function applyBaseScale(zone, value) {
        if (!zone) return 1.0;
        var next = normalizeScale(value, zone.baseScale);
        zone.baseScale = next;
        if (!isIndependent(zone)) {
            zone.specScaleMode = 'match';
            zone.specScale = next;
        }
        return next;
    }

    function applySpecScale(zone, value) {
        if (!zone) return 1.0;
        var next = normalizeScale(value, resolve(zone));
        zone.specScaleMode = 'independent';
        zone.specScale = next;
        return next;
    }

    function setIndependent(zone, enabled) {
        if (!zone) return 1.0;
        var linkedValue = normalizeScale(zone.baseScale, 1.0);
        if (enabled) {
            if (!isIndependent(zone)) zone.specScale = linkedValue;
            zone.specScaleMode = 'independent';
            zone.specScale = normalizeScale(zone.specScale, linkedValue);
        } else {
            zone.specScaleMode = 'match';
            zone.specScale = linkedValue;
        }
        return resolve(zone);
    }

    var api = {
        MIN_SCALE: MIN_SCALE,
        MAX_SCALE: MAX_SCALE,
        STEP: STEP,
        normalizeScale: normalizeScale,
        isIndependent: isIndependent,
        resolve: resolve,
        applyBaseScale: applyBaseScale,
        applySpecScale: applySpecScale,
        setIndependent: setIndependent
    };

    global.SPBBaseSpecScaleLink = api;
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
