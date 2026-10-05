/* SPB-93 urgent PSD import safety (2026-07-17).
 * PSD names are labels, never identities. This pure helper preserves full
 * hierarchy paths, stable positional raster keys, inherited visibility, and
 * provides a sampled source-vs-layer-stack fidelity gate. It owns no canvas,
 * Layer mutation, dispatch, history, or Zone state. */
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPSDImportSafety = api;
})(typeof window !== 'undefined' ? window : globalThis, function() {
    'use strict';

    const blendModes = Object.freeze({
        normal: 'source-over',
        multiply: 'multiply',
        screen: 'screen',
        overlay: 'overlay',
        darken: 'darken',
        lighten: 'lighten',
        color_dodge: 'color-dodge',
        color_burn: 'color-burn',
        hard_light: 'hard-light',
        soft_light: 'soft-light',
        difference: 'difference',
        exclusion: 'exclusion',
        hue: 'hue',
        saturation: 'saturation',
        color: 'color',
        luminosity: 'luminosity'
    });

    function blendModeKey(value) {
        return String(value || 'normal')
            .replace(/^BlendMode\./i, '')
            .trim()
            .toLowerCase()
            .replace(/[ -]+/g, '_');
    }

    function normalizeBlendMode(value) {
        const key = blendModeKey(value);
        return blendModes[key] || 'source-over';
    }

    function _groupDescriptor(node, indexPath, namePath, effectiveVisible) {
        const key = String(node.layer_key != null ? node.layer_key : indexPath.join('.'));
        const rawBlendMode = blendModeKey(node.blend_mode);
        const mode = node.group_mode === 'pass-through' || rawBlendMode === 'pass_through'
            ? 'pass-through'
            : 'isolated';
        return {
            key: key,
            name: String(node.name || 'Group'),
            path: node.path || namePath.join('/'),
            visible: effectiveVisible,
            ownVisible: node.visible !== false,
            opacity: Math.max(0, Math.min(255, Number(node.opacity == null ? 255 : node.opacity) || 0)),
            rawBlendMode: rawBlendMode,
            blendMode: mode === 'pass-through' ? 'source-over' : normalizeBlendMode(node.blend_mode),
            mode: mode,
            clipping: !!node.clipping
        };
    }

    function _groupIssue(group) {
        if (group.clipping) {
            return 'clipped group boundaries are not supported';
        }
        if (group.mode === 'pass-through' && group.opacity !== 255) {
            return 'pass-through group opacity below 100% is not supported';
        }
        if (group.mode === 'isolated' && !blendModes[group.rawBlendMode]) {
            return 'unsupported isolated group blend mode: ' + group.rawBlendMode;
        }
        return null;
    }

    function flattenLayerTree(layerTree, documentSize) {
        const size = documentSize || {};
        const result = [];
        // [SPB-LAYER-GAUNTLET C5 2026-08-21] pixel-less nodes (adjustment layers,
        // empty groups' own entries, type placeholders) used to vanish WITHOUT A
        // TRACE - a painter whose Hue/Sat adjustment layer drove the whole look
        // got a different-looking car and no explanation. Collect them.
        const dropped = [];
        const groupIssues = [];
        // [SPB-HEADER-SLIM 2026-08-29] blend audit: record silent Normal-downgrades for a UI toast.
        const blendDowngrades = [];
        function walk(nodes, indexPrefix, namePrefix, parentVisible, parentGroups) {
            (Array.isArray(nodes) ? nodes : []).forEach(function(node, index) {
                if (!node) return;
                const indexPath = indexPrefix.concat(index);
                const name = String(node.name || 'Layer');
                const namePath = namePrefix.concat(name);
                const ownVisible = node.visible !== false;
                const effectiveVisible = node.effective_visible != null
                    ? !!node.effective_visible
                    : !!parentVisible && ownVisible;
                if (Array.isArray(node.children)) {
                    const group = _groupDescriptor(node, indexPath, namePath, effectiveVisible);
                    const issue = _groupIssue(group);
                    if (issue) groupIssues.push({
                        key: group.key,
                        path: group.path,
                        mode: group.mode,
                        reason: issue
                    });
                    walk(node.children, indexPath, namePath, effectiveVisible, parentGroups.concat(group));
                    return;
                }
                if (!node.has_pixels) {
                    dropped.push(name + (node.kind ? ' (' + node.kind + ')' : ''));
                    return;
                }
                const rasterKey = String(node.layer_key != null
                    ? node.layer_key
                    : indexPath.join('.'));
                // Preserve the historical sequential public Layer IDs so saved
                // zone->Layer bindings keep resolving after this import fix.
                // rasterKey, not id, carries the collision-free PSD identity.
                const _bmKey = blendModeKey(node.blend_mode);
                if (!blendModes[_bmKey] && _bmKey !== 'normal') {
                    blendDowngrades.push(name + ' (' + _bmKey + ')');
                }
                const layerId = 'psd_' + result.length;
                result.push({
                    id: layerId,
                    name: name,
                    path: node.path || namePath.join('/'),
                    pathParts: Array.isArray(node.path_parts) ? node.path_parts.slice() : namePath,
                    rasterKey: rasterKey,
                    visible: effectiveVisible,
                    importVisible: effectiveVisible,
                    ownVisible: ownVisible,
                    opacity: node.opacity != null ? node.opacity : 255,
                    img: null,
                    bbox: Array.isArray(node.bbox) ? node.bbox.slice() : [0, 0, size.width || 0, size.height || 0],
                    groupName: namePath.slice(0, -1).join(' / '),
                    groupChain: parentGroups.map(function(group) { return Object.assign({}, group); }),
                    parentGroupKey: parentGroups.length ? parentGroups[parentGroups.length - 1].key : null,
                    blendMode: normalizeBlendMode(node.blend_mode),
                    clippingMask: !!node.clipping
                });
            });
        }
        walk(layerTree, [], [], true, []);
        // Expose without changing the return contract (callers index the array).
        try { result.droppedLayers = dropped; } catch (e) {}
        try { result.groupFidelityIssues = groupIssues; } catch (e) {}
        try { result.blendModeDowngrades = blendDowngrades; } catch (e) {}
        return result;
    }

    function assessComposite(reference, candidate, sampleStride) {
        if (!reference || !candidate || reference.length !== candidate.length) {
            return { valid: false, critical: true, reason: 'missing-or-mismatched-pixels' };
        }
        const pixelCount = reference.length / 4;
        const stride = Math.max(1, Number(sampleStride) || Math.ceil(pixelCount / 262144));
        let samples = 0, referenceVisible = 0, candidateVisible = 0;
        let missing = 0, extra = 0, different = 0, totalDifference = 0;
        let referenceLuma = 0, candidateLuma = 0;
        for (let pixel = 0; pixel < pixelCount; pixel += stride) {
            const i = pixel * 4;
            const ra = reference[i + 3], ca = candidate[i + 3];
            samples++;
            if (ra > 8) {
                referenceVisible++;
                if (ca <= 8) missing++;
                const rr = reference[i], rg = reference[i + 1], rb = reference[i + 2];
                const cr = candidate[i], cg = candidate[i + 1], cb = candidate[i + 2];
                const dr = Math.abs(rr - cr), dg = Math.abs(rg - cg), db = Math.abs(rb - cb);
                const maxDifference = Math.max(dr, dg, db, Math.abs(ra - ca));
                totalDifference += (dr + dg + db + Math.abs(ra - ca)) / 4;
                if (maxDifference > 32) different++;
                referenceLuma += rr * 0.2126 + rg * 0.7152 + rb * 0.0722;
                candidateLuma += cr * 0.2126 + cg * 0.7152 + cb * 0.0722;
            } else if (ca > 8) {
                extra++;
            }
            if (ca > 8) candidateVisible++;
        }
        const denom = Math.max(1, referenceVisible);
        const metrics = {
            valid: true,
            samples: samples,
            referenceVisible: referenceVisible,
            candidateVisible: candidateVisible,
            missingFraction: missing / denom,
            extraFraction: extra / Math.max(1, samples),
            differentFraction: different / denom,
            meanDifference: totalDifference / denom,
            referenceLuma: referenceLuma / denom,
            candidateLuma: candidateLuma / denom
        };
        metrics.critical = referenceVisible > 0 && (
            metrics.missingFraction > 0.01 ||
            metrics.extraFraction > 0.01 ||
            metrics.differentFraction > 0.20 ||
            metrics.meanDifference > 24 ||
            (metrics.referenceLuma > 24 && metrics.candidateLuma < metrics.referenceLuma * 0.18)
        );
        metrics.reason = metrics.critical ? 'layer-stack-does-not-match-source' : 'match';
        return metrics;
    }

    return Object.freeze({
        normalizeBlendMode: normalizeBlendMode,
        flattenLayerTree: flattenLayerTree,
        assessComposite: assessComposite
    });
});
