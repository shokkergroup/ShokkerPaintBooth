/* SPB-93 2026-09-08: retain the source read already made at stroke start.
   One transient byte copy replaces a full original-canvas draw/read on release.
   Off-canvas art still uses the complete original-raster preservation path. */
(function(root) {
    'use strict';
    const snapshots = new WeakMap();
    function geometry(layer) {
        return [layer?.bbox?.[0] ?? 0, layer?.bbox?.[1] ?? 0,
            Number(layer?.img?.naturalWidth || layer?.img?.width),
            Number(layer?.img?.naturalHeight || layer?.img?.height)];
    }
    function capture(surface, layer, pixels) {
        if (!surface || !layer?.img || !pixels) return false;
        snapshots.delete(surface);
        const bounds = geometry(layer), [x, y, w, h] = bounds;
        if (!bounds.every(Number.isInteger) || w < 1 || h < 1 || x < 0 || y < 0
            || x + w > surface.width || y + h > surface.height
            || pixels.width !== surface.width || pixels.height !== surface.height
            || pixels.data?.length !== surface.width * surface.height * 4) return false;
        snapshots.set(surface, { image: layer.img, id: layer.id, bounds,
            pixels: { width: pixels.width, height: pixels.height, data: pixels.data.slice() } });
        return true;
    }
    function take(surface, layer) {
        const saved = surface && snapshots.get(surface);
        if (surface) snapshots.delete(surface);
        if (!saved || saved.image !== layer?.img || saved.id !== layer.id
            || saved.pixels.width !== surface.width || saved.pixels.height !== surface.height
            || geometry(layer).some((v, i) => v !== saved.bounds[i])) return null;
        return saved.pixels;
    }
    const api = { capture, take };
    root.SPBPaintSourceSnapshot = api;
    if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
