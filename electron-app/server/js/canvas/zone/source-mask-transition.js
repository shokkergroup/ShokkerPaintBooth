(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSourceMaskTransition = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // SPB-93 2026-09-07: source swaps retained the old mask grid and failed
    // server validation. Stage independent Zone/history objects so failed
    // imports can restore the exact outgoing document. No Layer pixel writes.
    function stage(state, oldWidth, oldHeight, width, height, geometry, codec) {
        if (![width, height].every(v => Number.isInteger(v) && v > 0)) {
            throw new Error('Invalid source dimensions');
        }
        const cache = new WeakMap();
        function resize(mask, authoredWidth = oldWidth, authoredHeight = oldHeight) {
            if (!mask) return mask;
            if (authoredWidth * authoredHeight !== mask.length) {
                // Recover square masks saved before the source had loaded.
                const side = Math.sqrt(mask.length);
                if (!Number.isInteger(side) || side < 1) {
                    throw new Error('Cannot determine the saved selection dimensions');
                }
                authoredWidth = authoredHeight = side;
            }
            if (authoredWidth === width && authoredHeight === height) return mask;
            if (!cache.has(mask)) {
                // Preserve discrete include/exclude values and authored soft
                // strengths; source replacement maps the same UV footprint.
                cache.set(mask, geometry.resizeNearest(mask, authoredWidth, authoredHeight, width, height));
            }
            return cache.get(mask);
        }
        function history(entry) {
            if (!entry) return entry;
            if (entry.batchMasks) {
                return Object.assign({}, entry, { batchMasks: entry.batchMasks.map(history) });
            }
            let next = entry;
            for (const key of ['prevMask', 'prevSpatial']) {
                const rle = entry[key + 'RLE'];
                const raw = entry[key];
                if (!raw && !rle) continue;
                const input = raw || codec.decode(rle, rle.width, rle.height);
                const output = resize(input, raw ? oldWidth : rle.width, raw ? oldHeight : rle.height);
                if (output === input) continue;
                if (next === entry) next = Object.assign({}, entry);
                // Keep deep history compressed; do not inflate the whole stack.
                if (!raw && rle) next[key + 'RLE'] = codec.encode(output, width, height);
                else next[key] = output;
            }
            return next;
        }
        function resizeZone(zone) {
            if (!zone) return zone;
            const regionMask = resize(zone.regionMask);
            const spatialMask = resize(zone.spatialMask);
            return regionMask === zone.regionMask && spatialMask === zone.spatialMask
                ? zone : Object.assign({}, zone, { regionMask, spatialMask });
        }
        // SPB-93 2026-09-07: recipe Undo snapshots retain spatial masks even
        // though region masks live in the separate brush history. Stage both.
        function configHistory(entry) {
            if (!entry || !Array.isArray(entry.snapshot)) return entry;
            return Object.assign({}, entry, { snapshot: entry.snapshot.map(resizeZone) });
        }
        return { zones: state.zones.map(resizeZone), undo: state.undo.map(history), redo: state.redo.map(history),
            configUndo: (state.configUndo || []).map(configHistory), configRedo: (state.configRedo || []).map(configHistory) };
    }
    return { stage };
});
