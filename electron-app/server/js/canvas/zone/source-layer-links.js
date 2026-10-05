// SPB-93 2026-09-07: a flat source has no PSD layer bindings. Apply the same
// boundary to retained recipe history so Undo cannot resurrect old layer IDs.
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSourceLayerLinks = api;
})(typeof window === 'object' ? window : globalThis, function() {
    'use strict';
    function detachZone(zone) {
        if (!zone || (!zone.sourceLayer && !(Array.isArray(zone.sourceLayers) && zone.sourceLayers.length))) return zone;
        return Object.assign({}, zone, {
            sourceLayer: zone.sourceLayer ? null : zone.sourceLayer,
            sourceLayers: Array.isArray(zone.sourceLayers) && zone.sourceLayers.length ? [] : zone.sourceLayers,
            sourceLayerBindings: {}
        });
    }
    function detachHistory(entry) {
        if (!entry || !Array.isArray(entry.snapshot)) return entry;
        const snapshot = entry.snapshot.map(detachZone);
        return snapshot.some((zone, i) => zone !== entry.snapshot[i]) ? Object.assign({}, entry, { snapshot }) : entry;
    }
    function stage(state) {
        return { zones: state.zones.map(detachZone),
            undo: (state.undo || []).map(detachHistory), redo: (state.redo || []).map(detachHistory) };
    }
    function identity(layer) {
        if (!layer) return null;
        const parts = Array.isArray(layer.pathParts) && layer.pathParts.length
            ? layer.pathParts.map(String) : layer.path ? [String(layer.path)] : layer.name ? [String(layer.name)] : null;
        return parts ? { parts, key: JSON.stringify(parts), label: parts.join(' / ') } : null;
    }
    // SPB-93: retain identities in recipes/projects, including unresolved links.
    // Rebuild keys from path components rather than trusting imported metadata.
    function snapshotBindings(zone, layers) {
        const ids = Array.isArray(zone.sourceLayers) && zone.sourceLayers.length ? zone.sourceLayers
            : zone.sourceLayer ? [zone.sourceLayer] : [];
        const byId = new Map((layers || []).map(layer => [layer.id, layer]));
        const counts = new Map();
        for (const layer of layers || []) {
            const ref = identity(layer);
            if (ref) counts.set(ref.key, (counts.get(ref.key) || 0) + 1);
        }
        return Object.fromEntries(ids.flatMap(id => {
            const live = identity(byId.get(id)), saved = zone.sourceLayerBindings?.[id];
            const ref = live || (Array.isArray(saved?.parts) && saved.parts.length
                && saved.parts.every(part => typeof part === 'string') ? identity({pathParts:saved.parts}) : null);
            if (!ref) return [];
            return [[id, { ...ref, ambiguous: live ? counts.get(ref.key) > 1 : saved.ambiguous === true }]];
        }));
    }
    function rebind(state, previousLayers, incomingLayers) {
        previousLayers = previousLayers || [];
        // Legacy saves without identities retain their initial-document IDs.
        // New saves can safely match an edited file even on first publication.
        const oldById = new Map(previousLayers.map(layer => [layer.id, layer]));
        const oldCounts = new Map(), incoming = new Map();
        for (const layer of previousLayers) {
            const ref = identity(layer);
            if (ref) oldCounts.set(ref.key, (oldCounts.get(ref.key) || 0) + 1);
        }
        for (const layer of incomingLayers) {
            const ref = identity(layer);
            if (ref) incoming.set(ref.key, [...(incoming.get(ref.key) || []), layer]);
        }
        function zoneBinding(zone) {
            if (!zone) return zone;
            const ids = Array.isArray(zone.sourceLayers) && zone.sourceLayers.length ? zone.sourceLayers
                : zone.sourceLayer ? [zone.sourceLayer] : [];
            if (!ids.length) return zone;
            if (!previousLayers.length && !Object.keys(zone.sourceLayerBindings || {}).length) return zone;
            const bindings = {}, mapped = [];
            for (const id of ids) {
                const ref = identity(oldById.get(id)) || zone.sourceLayerBindings?.[id]
                    || { key: String(id), label: 'Previously selected layer', ambiguous: true };
                const ambiguous = ref.ambiguous || (oldCounts.get(ref.key) || 0) > 1;
                const matches = incoming.get(ref.key) || [];
                const nextId = !ambiguous && matches.length === 1 ? matches[0].id
                    : String(id).startsWith('spb_missing_layer:') ? id
                    : 'spb_missing_layer:' + encodeURIComponent(ref.key) + ':' + encodeURIComponent(id);
                if (!mapped.includes(nextId)) mapped.push(nextId);
                bindings[nextId] = { ...ref, ambiguous: !!ambiguous };
            }
            return { ...zone, sourceLayer: mapped[0] || null, sourceLayers: mapped, sourceLayerBindings: bindings };
        }
        const history = entry => entry && Array.isArray(entry.snapshot)
            ? { ...entry, snapshot: entry.snapshot.map(zoneBinding) } : entry;
        return { zones: state.zones.map(zoneBinding), undo: (state.undo || []).map(history), redo: (state.redo || []).map(history) };
    }
    return Object.freeze({ stage, rebind, snapshotBindings });
});
