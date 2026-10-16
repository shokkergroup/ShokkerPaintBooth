"""Reviewable diagnostic-only proposal: painting ownership is not opaque artwork."""


def edits(relative):
    if relative == 'paint-booth-3-canvas.js':
        return [
            ('function getLayerVisibleContributionMask(srcLayer, w, h, excludeLayerId) {', 'function getLayerVisibleContributionMask(srcLayer, w, h, excludeLayerId, opaqueDiagnostic) {', 1),
            ("const cacheKey = `${_layerCompositeRevision}:${srcLayer.id}:${w}x${h}` + (excludeLayerId ? `:x${excludeLayerId}` : '');", "const cacheKey = `${_layerCompositeRevision}:${srcLayer.id}:${w}x${h}` + (excludeLayerId ? `:x${excludeLayerId}` : '') + (opaqueDiagnostic ? ':opaque-diagnostic' : '');", 1),
            ('if (srcData[pi * 4 + 3] < 128) continue;', 'if (srcData[pi * 4 + 3] < (opaqueDiagnostic ? 255 : 128)) continue;', 1),
            ('if (aboveData[pi * 4 + 3] >= 128) continue;', 'if (aboveData[pi * 4 + 3] >= (opaqueDiagnostic ? 1 : 128)) continue;', 1),
            ("if (typeof window !== 'undefined') window.getLayerVisibleContributionMask = getLayerVisibleContributionMask;", """if (typeof window !== 'undefined') window.getLayerVisibleContributionMask = getLayerVisibleContributionMask;
// Private SPB AI acceptance Oct10: reuse exact compositor alpha for diagnostics.
// Painting ownership keeps its existing >=50% rule and original cache keys.
// No mask writes, history, renderer or Zone/Layer dispatch changes.
if (typeof window !== 'undefined') window.getLayerOpaqueContributionMask = function(layer, w, h) {
    return getLayerVisibleContributionMask(layer, w, h, null, true);
};""", 1),
        ]
    if relative == 'js/spb-intent-report.js':
        return [
            ("qy += 2) for (qx = x0; qx < x1; qx += 2)", "qy += mode2 === 'solid' ? 1 : 2) for (qx = x0; qx < x1; qx += mode2 === 'solid' ? 1 : 2)", 1),
            ("if (full[qy * Wd + qx] > 0) { h++;", "if (mode2 === 'solid' ? full[qy * Wd + qx] === 255 : full[qy * Wd + qx] > 0) { h++;", 1),
            ("(n && h >= 0.9 * n)", "(n && (mode2 === 'solid' ? h === n : h >= 0.9 * n))", 1),
            ('    function layerFull(name, Wd, Hd) {', '''    function opaqueArtworkGrid(name, Wd, Hd) {
        if (W.SPB_AI_OPAQUE_CHECK_OFF || typeof W.getLayerOpaqueContributionMask !== 'function') return null;
        try {
            var l = layerObj(name), f = l && W.getLayerOpaqueContributionMask(l, Wd, Hd);
            if (!f || f.length !== Wd * Hd) return null;
            // Full-alpha cells with a two-cell filter margin. Never call a
            // >=50% ownership mask an opaque artwork preservation check.
            var g = erode(grid(f, Wd, Hd, 'solid'), 2), count = 0;
            for (var i = 0; i < g.length; i++) count += g[i] ? 1 : 0;
            return count ? {mask:g,cells:count} : null;
        } catch (e) { return null; }
    }
    function layerFull(name, Wd, Hd) {''', 1),
            ('M.decalMin = 150; if (sc.protect.length)', 'M.decalCoreCells = 0; M.decalCoreLayers = []; M.decalFallbackLayers = []; M.decalMin = 150; if (sc.protect.length)', 1),
            ("var g = grid(f, Wd, Hd, 'core'); for (var i", "var core = opaqueArtworkGrid(l, Wd, Hd), g = core ? core.mask : grid(f, Wd, Hd, 'core'); if (core) { M.decalCoreCells += core.cells; M.decalCoreLayers.push(l); } else M.decalFallbackLayers.push(l); for (var i", 1),
            ('decal: o.decal, findings: []', "decal: o.decal, artwork_check: {basis:M.decalCoreLayers.length ? 'opaque interiors with filter margin' : 'binary ownership estimate',checked_core_cells:M.decalCoreCells,core_layers:M.decalCoreLayers,fallback_layers:M.decalFallbackLayers,edges_verified:false}, findings: []", 1),
            ("' The preview check found no change in protected artwork; it does not verify every pixel.'", "(M.decalCoreLayers && M.decalCoreLayers.length ? ' The preview check found no change in the checked solid artwork interiors; translucent edges and every source pixel are not verified.' : ' The preview check found no change in protected artwork; it does not verify every pixel.')", 2),
        ]
    if relative == 'js/spb-mcp-frames.js':
        return [('scope: { colour_target:', 'artwork_check: rep.artwork_check || undefined, scope: { colour_target:', 1)]
    return []
