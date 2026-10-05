/* SPB-93 Pass 132: Photoshop-style Layer clipping masks for car-art stacks. */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLayerClippingMask = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    var scratchCanvas = null;

    function _parentGroupKey(layer) {
        if (!layer) return null;
        if (layer.parentGroupKey != null) return String(layer.parentGroupKey);
        var chain = Array.isArray(layer.groupChain) ? layer.groupChain : [];
        var parent = chain.length ? chain[chain.length - 1] : null;
        return parent && parent.key != null ? String(parent.key) : null;
    }

    // [SPB-LAYER-ADJUST 2026-08-21] Non-destructive per-layer Hue/Sat/Brightness
    // as a GPU canvas filter. This module is the ONE pixel-draw path shared by
    // recompositeFromLayers and buildLivePaintCompositeCanvas, so the on-screen
    // canvas and the server render can never disagree.
    function adjustFilterFor(layer) {
        var h = Number(layer && layer.adjHue) || 0;
        var sAdj = Number(layer && layer.adjSat) || 0;
        var b = Number(layer && layer.adjBri) || 0;
        if (!h && !sAdj && !b) return null;
        return 'hue-rotate(' + h + 'deg) saturate(' + Math.max(0, 100 + sAdj) + '%) brightness(' + Math.max(0, 100 + b) + '%)';
    }

    function resolveBaseLayer(layers, layerIndex) {
        if (!Array.isArray(layers) || layerIndex <= 0 || layerIndex >= layers.length) return null;
        var layer = layers[layerIndex];
        if (!layer) return null;
        var parentGroupKey = _parentGroupKey(layer);
        for (var index = layerIndex - 1; index >= 0; index--) {
            var candidate = layers[index];
            if (!candidate || _parentGroupKey(candidate) !== parentGroupKey) break;
            if (candidate && !candidate.clippingMask) return candidate;
        }
        return null;
    }

    function normalizeStack(layers) {
        if (!Array.isArray(layers) || !layers.length) return false;
        var changed = false;
        for (var index = 0; index < layers.length; index++) {
            var layer = layers[index];
            if (layer && layer.clippingMask && !resolveBaseLayer(layers, index)) {
                // Never repair a missing in-group base by reaching through a
                // sibling/parent group. Release the invalid clip explicitly.
                layer.clippingMask = false;
                changed = true;
            }
        }
        return changed;
    }

    var supportedGroupBlendModes = Object.freeze({
        'source-over': true,
        multiply: true,
        screen: true,
        overlay: true,
        darken: true,
        lighten: true,
        'color-dodge': true,
        'color-burn': true,
        'hard-light': true,
        'soft-light': true,
        difference: true,
        exclusion: true,
        hue: true,
        saturation: true,
        color: true,
        luminosity: true,
    });

    function _groupChain(layer) {
        return layer && Array.isArray(layer.groupChain) ? layer.groupChain : [];
    }

    function inspectStack(layers) {
        if (!Array.isArray(layers)) return { ok: false, issues: [{ reason: 'layer stack is unavailable' }] };
        var groups = new Map();
        var issues = [];
        var previousGroupKeys = [];
        var closedGroupKeys = new Set();
        layers.forEach(function (layer, layerIndex) {
            // Hidden fallback/import-diagnostic layers do not participate in
            // the displayed composite. Validate them when they are shown,
            // before a wrong pixel can be published.
            if (layer && layer.visible !== false) {
                var chain = _groupChain(layer);
                var chainKeys = chain.map(function (group) { return String(group && group.key); });
                previousGroupKeys.forEach(function (key) {
                    if (chainKeys.indexOf(key) < 0) closedGroupKeys.add(key);
                });
                chain.forEach(function (group) {
                    if (!group || group.key == null) return;
                    var key = String(group.key);
                    if (closedGroupKeys.has(key)) {
                        issues.push({
                            groupKey: key,
                            path: group.path || group.name || key,
                            reason: 'group children are no longer contiguous in the Layer stack'
                        });
                    }
                    if (!groups.has(key)) {
                        groups.set(key, group);
                    } else {
                        var first = groups.get(key);
                        if ((first.mode || 'isolated') !== (group.mode || 'isolated') ||
                                Number(first.opacity == null ? 255 : first.opacity) !== Number(group.opacity == null ? 255 : group.opacity) ||
                                (first.blendMode || 'source-over') !== (group.blendMode || 'source-over')) {
                            issues.push({
                                groupKey: key,
                                path: group.path || group.name || key,
                                reason: 'group metadata is inconsistent across its children'
                            });
                        }
                    }
                });
                previousGroupKeys = chainKeys;
            }
            if (layer && layer.visible !== false && layer.clippingMask && !resolveBaseLayer(layers, layerIndex)) {
                issues.push({
                    layerId: layer.id || null,
                    path: layer.path || layer.name || ('Layer ' + layerIndex),
                    reason: 'clipped layer has no base inside its immediate group'
                });
            }
        });
        groups.forEach(function (group) {
            var mode = group.mode === 'pass-through' ? 'pass-through' : 'isolated';
            var opacity = Math.max(0, Math.min(255, Number(group.opacity == null ? 255 : group.opacity) || 0));
            var blendMode = group.blendMode || 'source-over';
            var reason = null;
            if (group.clipping) reason = 'clipped group boundaries are not supported';
            else if (mode === 'pass-through' && opacity !== 255) {
                reason = 'pass-through group opacity below 100% is not supported';
            } else if (mode === 'isolated' && !supportedGroupBlendModes[blendMode]) {
                reason = 'unsupported isolated group blend mode: ' + blendMode;
            }
            if (reason) issues.push({
                groupKey: String(group.key),
                path: group.path || group.name || String(group.key),
                reason: reason
            });
        });
        return { ok: issues.length === 0, issues: issues, groups: groups.size };
    }

    function hasGroupSemantics(layers) {
        return Array.isArray(layers) && layers.some(function (layer) { return _groupChain(layer).length > 0; });
    }

    function _buildCompositeTree(layers) {
        var root = { type: 'root', children: [] };
        var groups = new Map();
        layers.forEach(function (layer, layerIndex) {
            if (!layer) return;
            var parent = root;
            _groupChain(layer).forEach(function (descriptor) {
                var key = String(descriptor.key);
                var group = groups.get(key);
                if (!group) {
                    group = { type: 'group', descriptor: descriptor, children: [] };
                    groups.set(key, group);
                    parent.children.push(group);
                }
                parent = group;
            });
            parent.children.push({ type: 'layer', layer: layer, index: layerIndex });
        });
        return root;
    }

    function _createGroupCanvas(ctx) {
        if (typeof document === 'undefined' || !document.createElement || !ctx || !ctx.canvas) return null;
        var canvas = document.createElement('canvas');
        canvas.width = ctx.canvas.width;
        canvas.height = ctx.canvas.height;
        return canvas;
    }

    function composeLayerStack(ctx, layers, options) {
        var opts = options || {};
        var inspection = inspectStack(layers);
        if (!ctx || !ctx.canvas) return { ok: false, issues: [{ reason: 'target canvas is unavailable' }] };
        if (!inspection.ok) return inspection;
        if (typeof opts.drawLayer !== 'function') {
            return { ok: false, issues: [{ reason: 'layer draw callback is unavailable' }] };
        }
        var tree = _buildCompositeTree(layers);
        var groupCount = 0;

        function drawChildren(target, children) {
            var drawn = 0;
            children.forEach(function (node) {
                if (node.type === 'layer') {
                    if (node.layer.visible === false || !node.layer.img) return;
                    if (typeof opts.includeLayer === 'function' && !opts.includeLayer(node.layer, node.index)) return;
                    if (opts.drawLayer(target, node.layer, node.index) !== false) drawn += 1;
                    return;
                }
                var group = node.descriptor;
                if (group.visible === false || group.ownVisible === false) return;
                if (group.mode === 'pass-through') {
                    drawn += drawChildren(target, node.children);
                    return;
                }
                var scratchCanvas = _createGroupCanvas(target);
                if (!scratchCanvas) return;
                var scratch = scratchCanvas.getContext('2d');
                if (!scratch) return;
                if (typeof scratch.setTransform === 'function') scratch.setTransform(1, 0, 0, 1, 0, 0);
                scratch.globalAlpha = 1;
                scratch.globalCompositeOperation = 'source-over';
                if (typeof scratch.clearRect === 'function') {
                    scratch.clearRect(0, 0, scratchCanvas.width, scratchCanvas.height);
                }
                var childCount = drawChildren(scratch, node.children);
                if (!childCount) return;
                target.save();
                target.globalAlpha = Math.max(0, Math.min(1, Number(group.opacity == null ? 255 : group.opacity) / 255));
                target.globalCompositeOperation = opts.identityBlend ? 'source-over' : (group.blendMode || 'source-over');
                target.drawImage(scratchCanvas, 0, 0);
                target.restore();
                groupCount += 1;
                drawn += childCount;
            });
            return drawn;
        }

        var drawn = drawChildren(ctx, tree.children);
        return { ok: true, issues: [], drawn: drawn, groups: groupCount };
    }

    function _drawDirect(ctx, layer, sourceOverride) {
        var source = sourceOverride || layer.img;
        if (!source) return false;
        var x = sourceOverride ? 0 : (layer.bbox ? Number(layer.bbox[0]) || 0 : 0);
        var y = sourceOverride ? 0 : (layer.bbox ? Number(layer.bbox[1]) || 0 : 0);
        ctx.save();
        ctx.globalAlpha = (layer.opacity != null ? layer.opacity : 255) / 255;
        ctx.globalCompositeOperation = layer.blendMode || 'source-over';
        var _adj = adjustFilterFor(layer);
        if (_adj) ctx.filter = _adj;
        ctx.drawImage(source, x, y);
        ctx.restore();
        return true;
    }

    function drawLayerPixels(ctx, layer, baseLayer, sourceOverride) {
        if (!ctx || !ctx.canvas || !layer) return false;
        if (!layer.clippingMask || !baseLayer) return _drawDirect(ctx, layer, sourceOverride);
        if (baseLayer.visible === false || !baseLayer.img) return false;

        if (!scratchCanvas) scratchCanvas = document.createElement('canvas');
        if (scratchCanvas.width !== ctx.canvas.width) scratchCanvas.width = ctx.canvas.width;
        if (scratchCanvas.height !== ctx.canvas.height) scratchCanvas.height = ctx.canvas.height;
        var scratch = scratchCanvas.getContext('2d');
        scratch.setTransform(1, 0, 0, 1, 0, 0);
        scratch.globalAlpha = 1;
        scratch.globalCompositeOperation = 'source-over';
        scratch.clearRect(0, 0, scratchCanvas.width, scratchCanvas.height);

        var source = sourceOverride || layer.img;
        if (!source) return false;
        var x = sourceOverride ? 0 : (layer.bbox ? Number(layer.bbox[0]) || 0 : 0);
        var y = sourceOverride ? 0 : (layer.bbox ? Number(layer.bbox[1]) || 0 : 0);
        var _adjC = adjustFilterFor(layer);
        if (_adjC) scratch.filter = _adjC;
        scratch.drawImage(source, x, y);
        scratch.filter = 'none';   // scratch persists across calls - always reset
        scratch.globalCompositeOperation = 'destination-in';
        var baseX = baseLayer.bbox ? Number(baseLayer.bbox[0]) || 0 : 0;
        var baseY = baseLayer.bbox ? Number(baseLayer.bbox[1]) || 0 : 0;
        scratch.drawImage(baseLayer.img, baseX, baseY);
        scratch.globalCompositeOperation = 'source-over';

        ctx.save();
        ctx.globalAlpha = (layer.opacity != null ? layer.opacity : 255) / 255;
        ctx.globalCompositeOperation = layer.blendMode || 'source-over';
        ctx.drawImage(scratchCanvas, 0, 0);
        ctx.restore();
        return true;
    }

    return {
        resolveBaseLayer: resolveBaseLayer,
        normalizeStack: normalizeStack,
        inspectStack: inspectStack,
        hasGroupSemantics: hasGroupSemantics,
        composeLayerStack: composeLayerStack,
        drawLayerPixels: drawLayerPixels,
        adjustFilterFor: adjustFilterFor,
    };
});
