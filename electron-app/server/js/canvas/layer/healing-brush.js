/**
 * SPB-93 tick 12 (2026-07-15) — Layer-only Healing Brush.
 * Owner verdict: tools still feel "jinky/off" and should behave more like Photoshop.
 * Movement: 0 Healing tool / 0 source feedback -> tone-adapting sampled repair with
 * explicit source readiness, aligned sampling, immutable stroke source, and Layer undo.
 */
(function () {
    'use strict';

    let source = null;
    let offset = null;
    let strokeSource = null;
    let toneDelta = [0, 0, 0];
    let strokeFootprintShape = 'round';
    let sourcePickArmed = false;

    function currentLayerId() {
        const layer = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
        return layer ? layer.id : null;
    }

    function isAligned() {
        return document.getElementById('healingAligned')?.checked !== false;
    }

    function isSourceReady() {
        return !!source && source.layerId === currentLayerId();
    }

    function syncSourceStatus() {
        const el = document.getElementById('healingSourceStatus');
        if (!el) return;
        const ready = isSourceReady();
        if (sourcePickArmed) el.textContent = 'Click the clean source area';
        else if (!source) el.textContent = 'Source not set — Alt+click';
        else if (!ready) el.textContent = 'Source is on another layer — Alt+click again';
        else el.textContent = `Source ready • ${source.x}, ${source.y}`;
        el.dataset.ready = ready ? 'true' : 'false';
        el.style.color = ready ? '#70f0a0' : '#ffb36b';
    }

    function setSource(x, y) {
        source = { x: Math.round(x), y: Math.round(y), layerId: currentLayerId() };
        sourcePickArmed = false;
        offset = null;
        syncSourceStatus();
        return source;
    }

    function clearSource() {
        source = null;
        offset = null;
        strokeSource = null;
        sourcePickArmed = false;
        syncSourceStatus();
    }

    function armSourcePick() {
        sourcePickArmed = true;
        syncSourceStatus();
    }

    function meanRgb(data, w, h, cx, cy, radius) {
        let r = 0, g = 0, b = 0, weight = 0;
        for (let y = Math.max(0, cy - radius); y <= Math.min(h - 1, cy + radius); y++) {
            for (let x = Math.max(0, cx - radius); x <= Math.min(w - 1, cx + radius); x++) {
                const i = (y * w + x) * 4;
                const a = data[i + 3] / 255;
                if (a <= 0) continue;
                r += data[i] * a; g += data[i + 1] * a; b += data[i + 2] * a; weight += a;
            }
        }
        return weight > 0 ? [r / weight, g / weight, b / weight] : null;
    }

    function beginStroke(x, y) {
        if (!isSourceReady() || typeof paintImageData === 'undefined' || !paintImageData) return false;
        if (!offset) offset = { dx: source.x - x, dy: source.y - y };
        strokeSource = new Uint8ClampedArray(paintImageData.data);
        // SPB-93 Pass 49 (2026-07-17), owner verdict: every tool should be as
        // good as it can be. Healing advertised the shared Brush Shape but
        // hard-coded a circle: 1/5 tip shapes -> 5/5, locked for this stroke.
        strokeFootprintShape = document.getElementById('brushShape')?.value || 'round';
        const pc = document.getElementById('paintCanvas');
        if (!pc) return false;
        const sampleRadius = Math.max(2, Math.min(12, Math.round(parseInt(document.getElementById('brushSize')?.value || 20) * 0.15)));
        const srcMean = meanRgb(strokeSource, pc.width, pc.height, Math.round(x + offset.dx), Math.round(y + offset.dy), sampleRadius);
        const dstMean = meanRgb(strokeSource, pc.width, pc.height, Math.round(x), Math.round(y), sampleRadius);
        if (!srcMean) {
            source = null;
            offset = null;
            strokeSource = null;
            sourcePickArmed = true;
            syncSourceStatus();
            if (typeof showToast === 'function') showToast('Healing source is transparent on this layer — click an opaque source', 'info');
            return false;
        }
        toneDelta = (srcMean && dstMean) ? dstMean.map((value, channel) => value - srcMean[channel]) : [0, 0, 0];
        return true;
    }

    function paintStroke(x, y) {
        const t0 = window._SPB_DEBUG_PAINT_PERF === true ? performance.now() : 0;
        const pc = document.getElementById('paintCanvas');
        if (!pc || !strokeSource || !offset || !paintImageData) return false;
        const w = pc.width, h = pc.height, data = paintImageData.data;
        const radiusBase = parseInt(document.getElementById('brushSize')?.value || 20);
        const hardness = parseInt(document.getElementById('brushHardness')?.value || 50) / 100;
        const opacityBase = parseInt(document.getElementById('brushOpacity')?.value || 100) / 100;
        const flow = parseInt(document.getElementById('brushFlow')?.value || 100) / 100;
        const dynamics = typeof window._resolveBrushDynamics === 'function'
            ? window._resolveBrushDynamics(radiusBase, opacityBase, flow)
            : { radius: radiusBase, opacity: opacityBase * flow };
        const radius = dynamics.radius;
        const opacity = dynamics.opacity;
        const selection = typeof _activeSelectionMask === 'function' ? _activeSelectionMask(w, h) : null;
        const footprint = typeof window._createBrushFootprint === 'function'
            ? window._createBrushFootprint(radius, strokeFootprintShape)
            : null;

        for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
                const dist2 = dx * dx + dy * dy;
                if (footprint ? !footprint.contains(dx, dy, dist2) : dist2 > radius * radius) continue;
                const sx = Math.round(x + offset.dx + dx), sy = Math.round(y + offset.dy + dy);
                const tx = Math.round(x + dx), ty = Math.round(y + dy);
                if (sx < 0 || sx >= w || sy < 0 || sy >= h || tx < 0 || tx >= w || ty < 0 || ty >= h) continue;
                const selectionCoverage = typeof window._selectionCoverage === 'function'
                    ? window._selectionCoverage(selection, ty * w + tx)
                    : (selection ? Math.max(0, Math.min(1, Number(selection[ty * w + tx]) / 255)) : 1);
                if (selectionCoverage <= 0) continue;
                const si = (sy * w + sx) * 4, ti = (ty * w + tx) * 4;
                const shapeDist2 = footprint ? footprint.distanceSquared(dx, dy) : dist2;
                const falloff = typeof window._brushFalloff === 'function'
                    ? window._brushFalloff(shapeDist2, radius, hardness)
                    : (window.SPBBrushFootprint?.softFalloff
                        ? window.SPBBrushFootprint.softFalloff(shapeDist2, radius, hardness)
                        : 1);
                const sourceAlpha = (strokeSource[si + 3] / 255) * opacity * falloff * selectionCoverage;
                if (sourceAlpha <= 0) continue;
                const targetAlpha = data[ti + 3] / 255;
                const outAlpha = sourceAlpha + targetAlpha * (1 - sourceAlpha);
                for (let channel = 0; channel < 3; channel++) {
                    const healed = Math.max(0, Math.min(255, strokeSource[si + channel] + toneDelta[channel]));
                    data[ti + channel] = Math.round((healed * sourceAlpha + data[ti + channel] * targetAlpha * (1 - sourceAlpha)) / outAlpha);
                }
                data[ti + 3] = Math.round(outAlpha * 255);
            }
        }
        if (typeof window._markActivePaintDirtyCircle === 'function') {
            window._markActivePaintDirtyCircle(x, y, radius, 1);
        }
        _flushPaintImageDataToCurrentSurface();
        if (typeof _logPaintPerf === 'function') _logPaintPerf('healing', t0, radius);
        return true;
    }

    function endStroke() {
        strokeSource = null;
        toneDelta = [0, 0, 0];
        strokeFootprintShape = 'round';
        if (!isAligned()) offset = null;
    }

    function resetStroke() {
        strokeSource = null;
        toneDelta = [0, 0, 0];
        strokeFootprintShape = 'round';
        offset = null;
    }

    window.setHealingSource = setSource;
    window.clearHealingSource = clearSource;
    window.armHealingSourcePick = armSourcePick;
    window.isHealingSourcePickArmed = function () { return sourcePickArmed; };
    window.hasHealingSourceForActiveLayer = isSourceReady;
    window.syncHealingSourceStatus = syncSourceStatus;
    window.beginHealingStroke = beginStroke;
    window.paintHealingStroke = paintStroke;
    window.endHealingStroke = endStroke;
    window.resetHealingStroke = resetStroke;
    window.SPBHealingBrush = { version: '1.3.0-spb93-pass108-hardness-core', meanRgb };
    document.documentElement.dataset.spbHealingBrush = 'ready';
})();
