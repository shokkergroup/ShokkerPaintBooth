(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBDocumentCapability = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function chooseInitialLayer(layerValues, importSafety) {
        const layers = Array.isArray(layerValues) ? layerValues.slice().reverse() : [];
        if (importSafety) {
            return layers.find(function (layer) { return layer && layer.importSafetyBase; }) || null;
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
