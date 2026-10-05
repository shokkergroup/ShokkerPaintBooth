(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSpecMaterialSampler = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    // SPB-93 tick 31, owner verdict: real car-template/spec tools only.
    // Baseline: Channels Inspector exposed whole-map min/max/mean but had no
    // point readout or transfer workflow. This adds Photoshop-like sampling
    // for SPB's actual M/R/CC/A material channels, with exact Zone ownership.
    let lastSample = null;
    let fallbackImageData = null;
    let fallbackImageElement = null;
    let fallbackImageSource = '';

    function clampByte(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) return null;
        return Math.max(0, Math.min(255, Math.round(number)));
    }

    function normalizeSample(sample) {
        if (!sample) return null;
        const m = clampByte(sample.m);
        const r = clampByte(sample.r);
        const cc = clampByte(sample.cc);
        const a = clampByte(sample.a);
        if ([m, r, cc, a].some(value => value == null)) return null;
        return { m, r, cc, a };
    }

    function sampleAt(imageData, x, y) {
        if (!imageData || !imageData.data || !imageData.width || !imageData.height) return null;
        const px = Math.max(0, Math.min(imageData.width - 1, Math.floor(Number(x))));
        const py = Math.max(0, Math.min(imageData.height - 1, Math.floor(Number(y))));
        if (!Number.isFinite(px) || !Number.isFinite(py)) return null;
        const offset = (py * imageData.width + px) * 4;
        const sample = normalizeSample({
            m: imageData.data[offset],
            r: imageData.data[offset + 1],
            cc: imageData.data[offset + 2],
            a: imageData.data[offset + 3],
        });
        return sample ? Object.assign({ x: px, y: py }, sample) : null;
    }

    function normalizeSampleSize(value) {
        const size = Math.round(Number(value));
        return [1, 3, 5].includes(size) ? size : 1;
    }

    // SPB-93 Pass 116 (2026-07-17): car spec maps deliberately contain fine
    // flakes, grain, and micro-highlight pixels. A point sample can capture one
    // outlier rather than the underlying material. Channel medians keep an
    // actual local tier, reject isolated sparkle/noise, and make Select Similar
    // useful without manufacturing the in-between values an average can create.
    function sampleMedianAt(imageData, x, y, sizeValue) {
        if (!imageData || !imageData.data || !imageData.width || !imageData.height) return null;
        const size = normalizeSampleSize(sizeValue);
        if (size === 1) return sampleAt(imageData, x, y);
        const px = Math.max(0, Math.min(imageData.width - 1, Math.floor(Number(x))));
        const py = Math.max(0, Math.min(imageData.height - 1, Math.floor(Number(y))));
        if (!Number.isFinite(px) || !Number.isFinite(py)) return null;
        const radius = (size - 1) / 2;
        const channels = [[], [], [], []];
        for (let sy = Math.max(0, py - radius); sy <= Math.min(imageData.height - 1, py + radius); sy++) {
            for (let sx = Math.max(0, px - radius); sx <= Math.min(imageData.width - 1, px + radius); sx++) {
                const offset = (sy * imageData.width + sx) * 4;
                for (let channel = 0; channel < 4; channel++) {
                    channels[channel].push(imageData.data[offset + channel]);
                }
            }
        }
        for (const values of channels) values.sort((left, right) => left - right);
        const middle = Math.floor(channels[0].length / 2);
        const sample = normalizeSample({
            m: channels[0][middle],
            r: channels[1][middle],
            cc: channels[2][middle],
            a: channels[3][middle],
        });
        return sample ? Object.assign({ x: px, y: py, sampleSize: size }, sample) : null;
    }

    function mapClientToPixel(clientX, clientY, rect, width, height) {
        if (!rect || !(rect.width > 0) || !(rect.height > 0) || !(width > 0) || !(height > 0)) return null;
        const nx = (Number(clientX) - rect.left) / rect.width;
        const ny = (Number(clientY) - rect.top) / rect.height;
        if (!Number.isFinite(nx) || !Number.isFinite(ny) || nx < 0 || ny < 0 || nx > 1 || ny > 1) return null;
        return {
            x: Math.min(width - 1, Math.max(0, Math.floor(nx * width))),
            y: Math.min(height - 1, Math.max(0, Math.floor(ny * height))),
        };
    }

    function samplesEqual(left, right) {
        const a = normalizeSample(left);
        const b = normalizeSample(right);
        return !!a && !!b && a.m === b.m && a.r === b.r && a.cc === b.cc && a.a === b.a;
    }

    function buildZonePatch(sample) {
        const normalized = normalizeSample(sample);
        // SPB-93 09-08: native Apply reported A255 but a prior Lighting Mask
        // forced saved A0. Applying all four sampled channels replaces that mask.
        return normalized ? { specMaterialOverride: normalized, specLightingMask: null } : null;
    }

    function countSelected(mask) {
        let count = 0;
        if (!mask || typeof mask.length !== 'number') return count;
        for (let index = 0; index < mask.length; index++) if (mask[index] > 0) count++;
        return count;
    }

    function getActiveZone() {
        if (typeof zones === 'undefined' || !Array.isArray(zones) ||
                typeof selectedZoneIndex !== 'number' || selectedZoneIndex < 0 ||
                selectedZoneIndex >= zones.length) return null;
        return zones[selectedZoneIndex] || null;
    }

    function showMessage(message, severity) {
        if (typeof showToast === 'function') showToast(message, severity || 'info');
    }

    function kickLivePreview() {
        if (root && typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview();
        else if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }

    function setText(id, value) {
        if (typeof document === 'undefined') return;
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    function setActionsEnabled(enabled) {
        if (typeof document === 'undefined') return;
        ['btnCopySpecSample', 'btnApplySpecSample', 'btnSelectConnectedMaterial', 'btnSelectAllMaterial'].forEach(id => {
            const button = document.getElementById(id);
            if (button) button.disabled = !enabled;
        });
    }

    function resetDisplay() {
        lastSample = null;
        setText('specSampleCoords', 'Click the map to sample a material');
        ['M', 'R', 'CC', 'A'].forEach(channel => setText(`specSample${channel}`, '—'));
        if (typeof document !== 'undefined') {
            const marker = document.getElementById('specMaterialSampleMarker');
            if (marker) marker.hidden = true;
        }
        setActionsEnabled(false);
    }

    function visibleInspectorSurface() {
        if (typeof document === 'undefined') return null;
        const canvas = document.getElementById('specMapInspectorCanvas');
        const image = document.getElementById('specMapInspectorImg');
        if (canvas && getComputedStyle(canvas).display !== 'none') return canvas;
        return image;
    }

    function readInspectorImageData() {
        const provided = typeof root.getSpecMapInspectorImageData === 'function'
            ? root.getSpecMapInspectorImageData()
            : null;
        if (provided && provided.data && provided.width && provided.height) return provided;
        // The installed inspector is authoritative, including its pending/error state.
        if (typeof root.getSpecMapInspectorImageData === 'function') return null;
        if (typeof document === 'undefined') return null;

        const image = document.getElementById('specMapInspectorImg');
        const width = image ? Number(image.naturalWidth) : 0;
        const height = image ? Number(image.naturalHeight) : 0;
        const source = image ? String(image.currentSrc || image.src || '') : '';
        if (!image || !image.complete || !width || !height || !source) return null;
        if (fallbackImageData && fallbackImageElement === image && fallbackImageSource === source) {
            return fallbackImageData;
        }

        try {
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const context = canvas.getContext('2d', { willReadFrequently: true });
            if (!context) return null;
            context.drawImage(image, 0, 0, width, height);
            fallbackImageData = context.getImageData(0, 0, width, height);
            fallbackImageElement = image;
            fallbackImageSource = source;
            return fallbackImageData;
        } catch (_) {
            return null;
        }
    }

    function sampleFromEvent(event) {
        if (!event || typeof document === 'undefined') return null;
        // SPB-93 T51 (2026-08-08), owner verdict: "ALL TOOLS MUST WORK
        // CORRECTLY." The visible inspector used the legacy preview controller,
        // while this extracted tool only asked an uninstalled controller for
        // pixels. Browser proof moved from 0/4 channel values after a click to
        // 4/4. Cache the compiled RGBA map so repeat samples remain instant.
        const imageData = readInspectorImageData();
        const surface = visibleInspectorSurface();
        const stage = document.getElementById('specMapInspectorStage');
        if (!imageData || !surface || !stage) {
            showMessage('Render a spec preview before sampling material values', 'info');
            return null;
        }
        const surfaceRect = surface.getBoundingClientRect();
        const point = mapClientToPixel(event.clientX, event.clientY, surfaceRect, imageData.width, imageData.height);
        if (!point) return null;
        const sampleSize = normalizeSampleSize(
            document.getElementById('specMaterialSampleSize')?.value
        );
        const sample = sampleMedianAt(imageData, point.x, point.y, sampleSize);
        if (!sample) return null;
        lastSample = sample;
        setText('specSampleCoords', sampleSize === 1
            ? `UV ${sample.x}, ${sample.y} · point`
            : `UV ${sample.x}, ${sample.y} · ${sampleSize}×${sampleSize} median`);
        setText('specSampleM', sample.m);
        setText('specSampleR', sample.r);
        setText('specSampleCC', sample.cc);
        setText('specSampleA', sample.a);
        setActionsEnabled(true);

        const marker = document.getElementById('specMaterialSampleMarker');
        if (marker) {
            const stageRect = stage.getBoundingClientRect();
            marker.style.left = `${surfaceRect.left - stageRect.left + (sample.x + 0.5) / imageData.width * surfaceRect.width}px`;
            marker.style.top = `${surfaceRect.top - stageRect.top + (sample.y + 0.5) / imageData.height * surfaceRect.height}px`;
            marker.hidden = false;
        }
        return sample;
    }

    function sampleText(sample) {
        const normalized = normalizeSample(sample);
        return normalized ? `M ${normalized.m} / R ${normalized.r} / CC ${normalized.cc} / A ${normalized.a}` : '';
    }

    async function copySample() {
        const text = sampleText(lastSample);
        if (!text) {
            showMessage('Click the spec map before copying material values', 'info');
            return false;
        }
        try {
            await navigator.clipboard.writeText(text);
            showMessage(`Copied ${text}`, 'success');
            return true;
        } catch (_) {
            showMessage(`Material sample: ${text}`, 'info');
            return false;
        }
    }

    function applySampleToActiveZone() {
        const sample = normalizeSample(lastSample);
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        if (!sample) {
            showMessage('Click the spec map before applying a material sample', 'info');
            return false;
        }
        if (!zone || !selectedPixels) {
            showMessage('Material Sampler needs an active Zone selection for the repair footprint', 'warning');
            return false;
        }
        if (zone.lockIntensity) {
            showMessage('Unlock this Zone\'s Intensity before applying sampled material channels', 'warning');
            return false;
        }
        if (samplesEqual(zone.specMaterialOverride, sample)
                && (zone.specLightingMask == null || Number(zone.specLightingMask) === sample.a)) {
            showMessage('That exact sampled material is already active - no history added', 'info');
            return false;
        }
        if (typeof pushZoneUndo === 'function') pushZoneUndo('Apply sampled spec material');
        Object.assign(zone, buildZonePatch(sample));
        if (typeof renderZones === 'function') renderZones();
        if (typeof renderZoneDetail === 'function') renderZoneDetail(selectedZoneIndex);
        kickLivePreview();
        if (typeof autoSave === 'function') autoSave();
        showMessage(
            `Sampled material applied to ${selectedPixels.toLocaleString()} pixels - ${sampleText(sample)}; source paint preserved`,
            'success'
        );
        return true;
    }

    function clearActiveZoneOverride() {
        const zone = getActiveZone();
        if (!zone || !zone.specMaterialOverride) {
            showMessage('The active Zone has no sampled material override', 'info');
            return false;
        }
        if (typeof pushZoneUndo === 'function') pushZoneUndo('Clear sampled spec material');
        zone.specMaterialOverride = null;
        if (typeof renderZones === 'function') renderZones();
        if (typeof renderZoneDetail === 'function') renderZoneDetail(selectedZoneIndex);
        kickLivePreview();
        if (typeof autoSave === 'function') autoSave();
        showMessage('Sampled material override cleared - Zone recipe restored', 'success');
        return true;
    }

    if (root && typeof document !== 'undefined') {
        root.sampleSpecMaterialAtEvent = sampleFromEvent;
        root.copySpecMaterialSample = copySample;
        root.applySpecMaterialSampleToZone = applySampleToActiveZone;
        root.clearSpecMaterialSampleFromZone = clearActiveZoneOverride;
        root.resetSpecMaterialSampleDisplay = resetDisplay;
    }

    return {
        clampByte,
        normalizeSample,
        sampleAt,
        normalizeSampleSize,
        sampleMedianAt,
        mapClientToPixel,
        samplesEqual,
        buildZonePatch,
        countSelected,
        sampleText,
        readInspectorImageData,
        getLastSample: () => lastSample,
    };
});
