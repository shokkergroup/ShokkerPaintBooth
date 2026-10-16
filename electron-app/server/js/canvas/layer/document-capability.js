(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBDocumentCapability = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function isTemplateHelper(layer) {
        const re = /^\s*(wire|mask|car[ _]*mandatory)\s*$/i;
        const path = String(layer && layer.path || '');
        return re.test(String(layer && layer.name || '')) || re.test(path.split('/').pop());
    }

    function chooseInitialLayer(layerValues, importSafety) {
        const layers = Array.isArray(layerValues) ? layerValues.slice().reverse() : [];
        if (importSafety) {
            return layers.find(function (layer) { return layer && layer.importSafetyBase; }) || null;
        }
        // [SPB-TFX2 2026-10-09 TA-006] the template helper layers (Wire / Mask / Car Mandatory) sit on top of the stack, so the first
        // visible unlocked layer from the top was always the template "Wire" and the first stroke went into a layer that is not exported.
        // Prefer the topmost PAINTABLE (non-template) layer; the old order remains the fallback when a PSD has nothing else.
        const killed = typeof window !== 'undefined' && window.SPB_TFX2_OFF;
        if (!killed) {
            const paintable = layers.find(function (layer) {
                return layer && layer.img && layer.visible !== false && !layer.locked && !isTemplateHelper(layer);
            }) || layers.find(function (layer) {
                return layer && layer.img && !layer.locked && !isTemplateHelper(layer);
            });
            if (paintable) return paintable;
        }
        return layers.find(function (layer) {
            return layer && layer.img && layer.visible !== false && !layer.locked;
        }) || layers.find(function (layer) {
            return layer && layer.img && !layer.locked;
        }) || layers.find(function (layer) {
            return layer && layer.img && layer.visible !== false;
        }) || null;
    }

    return Object.freeze({ chooseInitialLayer });
});
