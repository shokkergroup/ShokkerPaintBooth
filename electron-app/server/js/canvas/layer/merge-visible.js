/*
 * SPB-93 Pass 134 — pure Merge Visible stack planning.
 * Keeps stack/identity decisions out of the canvas compositor so they can be
 * tested without a DOM and eventually extracted with the rest of Layer tools.
 */
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLayerMergeVisible = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function() {
    'use strict';

    function resolveClippingBase(layers, layerIndex) {
        if (!Array.isArray(layers) || layerIndex <= 0 || layerIndex >= layers.length) return null;
        for (let index = layerIndex - 1; index >= 0; index--) {
            const candidate = layers[index];
            if (candidate && !candidate.clippingMask) return candidate;
        }
        return null;
    }

    function isEffectivelyVisible(layers, layerIndex) {
        const layer = layers[layerIndex];
        if (!layer || layer.visible === false || !layer.img) return false;
        if (!layer.clippingMask) return true;
        const base = resolveClippingBase(layers, layerIndex);
        // Match the live compositor: malformed bottom clip flags draw normally,
        // while a real hidden/missing-image base hides the clipped Layer.
        return !base || (base.visible !== false && !!base.img);
    }

    function plan(layers, selectedLayerId) {
        if (!Array.isArray(layers)) return null;
        const pendingVisible = layers.filter(layer => layer && layer.visible !== false && !layer.img);
        const visibleEntries = [];
        for (let index = 0; index < layers.length; index++) {
            if (isEffectivelyVisible(layers, index)) visibleEntries.push({ layer: layers[index], index: index });
        }
        const selectedEntry = visibleEntries.find(entry => entry.layer.id === selectedLayerId);
        const baseEntry = selectedEntry || visibleEntries[visibleEntries.length - 1] || null;
        const visibleIds = new Set(visibleEntries.map(entry => entry.layer.id));
        const releaseClippingIds = [];
        for (let index = 0; index < layers.length; index++) {
            const layer = layers[index];
            if (!layer || visibleIds.has(layer.id) || !layer.clippingMask) continue;
            const oldBase = resolveClippingBase(layers, index);
            if (oldBase && visibleIds.has(oldBase.id)) releaseClippingIds.push(layer.id);
        }
        return {
            baseLayer: baseEntry ? baseEntry.layer : null,
            visibleLayers: visibleEntries.map(entry => entry.layer),
            visibleIds: visibleIds,
            pendingVisible: pendingVisible,
            releaseClippingIds: releaseClippingIds,
        };
    }

    return Object.freeze({ plan: plan, isEffectivelyVisible: isEffectivelyVisible });
});
