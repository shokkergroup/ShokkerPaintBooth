(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSpecMaterialSelect = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    // SPB-93 tick 32, owner verdict: professional feel plus real spec-mapping
    // leverage. This is Photoshop Magic Wand / Color Range semantics over
    // iRacing M/R/CC/A—not source RGB—and writes only a Zone regionMask.

    function clampTolerance(value) {
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(0, Math.min(255, Math.round(number))) : 12;
    }

    function matches(data, offset, sample, tolerance) {
        return Math.abs(data[offset] - sample.m) <= tolerance &&
            Math.abs(data[offset + 1] - sample.r) <= tolerance &&
            Math.abs(data[offset + 2] - sample.cc) <= tolerance &&
            Math.abs(data[offset + 3] - sample.a) <= tolerance;
    }

    function buildAllMask(imageData, sample, tolerance) {
        if (!imageData || !imageData.data || !imageData.width || !imageData.height || !sample) return null;
        const tol = clampTolerance(tolerance);
        const count = imageData.width * imageData.height;
        const mask = new Uint8Array(count);
        let selected = 0;
        for (let index = 0, offset = 0; index < count; index++, offset += 4) {
            if (matches(imageData.data, offset, sample, tol)) {
                mask[index] = 255;
                selected++;
            }
        }
        return { mask, selected, width: imageData.width, height: imageData.height };
    }

    function findNearestMatchingSeed(imageData, sample, tolerance, startX, startY, radiusValue) {
        const width = imageData.width;
        const height = imageData.height;
        const originX = Math.max(0, Math.min(width - 1, Math.floor(Number(startX))));
        const originY = Math.max(0, Math.min(height - 1, Math.floor(Number(startY))));
        const maxRadius = Math.max(0, Math.min(8, Math.floor(Number(radiusValue) || 0)));
        for (let radius = 0; radius <= maxRadius; radius++) {
            for (let dy = -radius; dy <= radius; dy++) {
                for (let dx = -radius; dx <= radius; dx++) {
                    if (radius && Math.max(Math.abs(dx), Math.abs(dy)) !== radius) continue;
                    const x = originX + dx;
                    const y = originY + dy;
                    if (x < 0 || y < 0 || x >= width || y >= height) continue;
                    const index = y * width + x;
                    if (matches(imageData.data, index * 4, sample, tolerance)) return index;
                }
            }
        }
        return -1;
    }

    function buildConnectedMask(imageData, sample, tolerance, startX, startY) {
        if (!imageData || !imageData.data || !imageData.width || !imageData.height || !sample) return null;
        const width = imageData.width;
        const height = imageData.height;
        const x = Math.max(0, Math.min(width - 1, Math.floor(Number(startX))));
        const y = Math.max(0, Math.min(height - 1, Math.floor(Number(startY))));
        if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
        const tol = clampTolerance(tolerance);
        const count = width * height;
        const mask = new Uint8Array(count);
        const visited = new Uint8Array(count);
        const queue = new Int32Array(count);
        // SPB-93 T51 (2026-08-08), owner verdict: "ALL TOOLS MUST WORK
        // CORRECTLY." A robust 3x3/5x5 median can intentionally reject the
        // clicked flake, so that exact center may sit one value beyond tolerance.
        // Start from the nearest local pixel matching the displayed median;
        // point samples remain strict at radius zero.
        const medianRadius = Number(sample.sampleSize) > 1 ? Number(sample.sampleSize) : 0;
        const start = findNearestMatchingSeed(imageData, sample, tol, x, y, medianRadius);
        if (start < 0) {
            return { mask, selected: 0, width, height };
        }
        let head = 0;
        let tail = 0;
        let selected = 0;
        queue[tail++] = start;
        visited[start] = 1;
        while (head < tail) {
            const index = queue[head++];
            if (!matches(imageData.data, index * 4, sample, tol)) continue;
            mask[index] = 255;
            selected++;
            const px = index % width;
            const py = (index / width) | 0;
            const left = index - 1;
            const right = index + 1;
            const up = index - width;
            const down = index + width;
            if (px > 0 && !visited[left]) { visited[left] = 1; queue[tail++] = left; }
            if (px + 1 < width && !visited[right]) { visited[right] = 1; queue[tail++] = right; }
            if (py > 0 && !visited[up]) { visited[up] = 1; queue[tail++] = up; }
            if (py + 1 < height && !visited[down]) { visited[down] = 1; queue[tail++] = down; }
        }
        return { mask, selected, width, height };
    }

    function resizeMaskNearest(mask, sourceWidth, sourceHeight, targetWidth, targetHeight) {
        if (!mask || sourceWidth === targetWidth && sourceHeight === targetHeight) return mask ? new Uint8Array(mask) : null;
        const out = new Uint8Array(targetWidth * targetHeight);
        for (let y = 0; y < targetHeight; y++) {
            const sy = Math.min(sourceHeight - 1, Math.floor(y * sourceHeight / targetHeight));
            const sourceRow = sy * sourceWidth;
            const targetRow = y * targetWidth;
            for (let x = 0; x < targetWidth; x++) {
                const sx = Math.min(sourceWidth - 1, Math.floor(x * sourceWidth / targetWidth));
                out[targetRow + x] = mask[sourceRow + sx];
            }
        }
        return out;
    }

    function composeMask(existing, candidate, mode) {
        if (!candidate) return null;
        const normalizedMode = mode === 'add' || mode === 'subtract' ? mode : 'replace';
        const size = candidate.length;
        const out = new Uint8Array(size);
        let changed = 0;
        let selected = 0;
        for (let index = 0; index < size; index++) {
            const before = existing && existing.length === size ? existing[index] : 0;
            let after = candidate[index];
            if (normalizedMode === 'add') after = Math.max(before, after);
            else if (normalizedMode === 'subtract') after = candidate[index] > 0 ? 0 : before;
            out[index] = after;
            if (after !== before) changed++;
            if (after > 0) selected++;
        }
        return { mask: out, changed, selected, mode: normalizedMode };
    }

    function getActiveZone() {
        if (typeof zones === 'undefined' || !Array.isArray(zones) ||
                typeof selectedZoneIndex !== 'number' || selectedZoneIndex < 0 ||
                selectedZoneIndex >= zones.length) return null;
        return { zone: zones[selectedZoneIndex], index: selectedZoneIndex };
    }

    function showMessage(message, severity) {
        if (typeof showToast === 'function') showToast(message, severity || 'info');
    }

    function kickLivePreview() {
        if (root && typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview();
        else if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }

    function currentTolerance() {
        if (typeof document === 'undefined') return 12;
        return clampTolerance(document.getElementById('specMaterialSelectTolerance')?.value ?? 12);
    }

    function currentMode() {
        if (typeof document === 'undefined') return 'replace';
        const value = document.getElementById('selectionMode')?.value || 'replace';
        return value === 'add' || value === 'subtract' ? value : 'replace';
    }

    function applySelection(kind) {
        const active = getActiveZone();
        const sampler = root.SPBSpecMaterialSampler;
        const sample = sampler && typeof sampler.getLastSample === 'function' ? sampler.getLastSample() : null;
        // SPB-93 T51: share the sampler's authoritative cached compiled map so
        // Select Connected / All Similar cannot depend on a dormant controller.
        const imageData = sampler && typeof sampler.readInspectorImageData === 'function'
            ? sampler.readInspectorImageData()
            : null;
        const paintCanvas = typeof document !== 'undefined' ? document.getElementById('paintCanvas') : null;
        if (!active || !active.zone) {
            showMessage('Select a Zone before building a material selection', 'warning');
            return false;
        }
        if (!sample || !imageData || !paintCanvas || !paintCanvas.width || !paintCanvas.height) {
            showMessage('Click the compiled spec map before selecting similar material', 'info');
            return false;
        }
        const tolerance = currentTolerance();
        const started = typeof performance !== 'undefined' ? performance.now() : Date.now();
        const found = kind === 'connected'
            ? buildConnectedMask(imageData, sample, tolerance, sample.x, sample.y)
            : buildAllMask(imageData, sample, tolerance);
        if (!found || !found.selected) {
            showMessage('No spec pixels matched that material tolerance', 'info');
            return false;
        }
        const candidate = resizeMaskNearest(
            found.mask, found.width, found.height, paintCanvas.width, paintCanvas.height
        );
        const composed = composeMask(active.zone.regionMask, candidate, currentMode());
        // SPB-93 (2026-09-08): a material selection must activate Apply Area,
        // including an unchanged mask whose area was disabled. Subtracting the
        // last pixels disables it. Snapshot both states as one Zone action.
        const useRegion = !!composed && composed.selected > 0;
        if (!composed || (!composed.changed && !!active.zone.useRegion === useRegion)) {
            showMessage(`Material selection is unchanged at tolerance ${tolerance} - no history added`, 'info');
            return false;
        }
        if (typeof root._spbPushZoneMaskUndoSnapshot !== 'function') {
            showMessage('Material selection history is unavailable - reload the booth', 'warning');
            return false;
        }
        root._spbPushZoneMaskUndoSnapshot(active.index);
        active.zone.regionMask = composed.mask;
        active.zone.useRegion = useRegion;
        if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
        if (typeof updateRegionStatus === 'function') updateRegionStatus();
        if (typeof renderContextActionBar === 'function') renderContextActionBar();
        if (typeof renderZones === 'function') renderZones();
        kickLivePreview();
        if (typeof autoSave === 'function') autoSave();
        if (typeof closeSpecMapInspector === 'function') closeSpecMapInspector();
        const ended = typeof performance !== 'undefined' ? performance.now() : Date.now();
        const label = kind === 'connected' ? 'Connected material' : 'All similar material';
        showMessage(
            `${label} · tolerance ${tolerance} · ${composed.mode} · ` +
            `${composed.selected.toLocaleString()} selected · ${composed.changed.toLocaleString()} changed · ${Math.round(ended - started)}ms`,
            'success'
        );
        return true;
    }

    if (root && typeof document !== 'undefined') {
        root.selectConnectedSpecMaterial = function() { return applySelection('connected'); };
        root.selectAllSimilarSpecMaterial = function() { return applySelection('all'); };
    }

    return {
        clampTolerance,
        matches,
        findNearestMatchingSeed,
        buildAllMask,
        buildConnectedMask,
        resizeMaskNearest,
        composeMask,
    };
});
