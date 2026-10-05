(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSpecMaterialRemap = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    const CHANNELS = Object.freeze(['m', 'r', 'cc']);
    const IDENTITY = Object.freeze({
        m: Object.freeze({ low: 0, high: 255 }),
        r: Object.freeze({ low: 0, high: 255 }),
        cc: Object.freeze({ low: 0, high: 255 }),
    });
    const PRESETS = Object.freeze({
        original: IDENTITY,
        metallic: Object.freeze({
            m: Object.freeze({ low: 205, high: 255 }),
            r: Object.freeze({ low: 8, high: 90 }),
            cc: Object.freeze({ low: 8, high: 55 }),
        }),
        vinyl: Object.freeze({
            m: Object.freeze({ low: 0, high: 24 }),
            r: Object.freeze({ low: 70, high: 155 }),
            cc: Object.freeze({ low: 55, high: 135 }),
        }),
        matte: Object.freeze({
            m: Object.freeze({ low: 0, high: 24 }),
            r: Object.freeze({ low: 180, high: 255 }),
            cc: Object.freeze({ low: 160, high: 230 }),
        }),
        gloss: Object.freeze({
            m: Object.freeze({ low: 0, high: 24 }),
            r: Object.freeze({ low: 0, high: 70 }),
            cc: Object.freeze({ low: 0, high: 55 }),
        }),
    });
    let previewSession = null;
    let previewTimer = 0;

    function clampByte(value) {
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(0, Math.min(255, Math.round(number))) : null;
    }

    function normalizeRemap(value) {
        if (!value || typeof value !== 'object') return null;
        const normalized = {};
        for (const channel of CHANNELS) {
            const range = value[channel];
            if (!range || typeof range !== 'object') return null;
            const low = clampByte(range.low);
            const high = clampByte(range.high);
            if (low == null || high == null || low > high) return null;
            normalized[channel] = { low, high };
        }
        return normalized;
    }

    function isIdentity(value) {
        const remap = normalizeRemap(value);
        return !!remap && CHANNELS.every(channel => remap[channel].low === 0 && remap[channel].high === 255);
    }

    function remapsEqual(left, right) {
        const a = normalizeRemap(left || IDENTITY);
        const b = normalizeRemap(right || IDENTITY);
        return !!a && !!b && CHANNELS.every(channel =>
            a[channel].low === b[channel].low && a[channel].high === b[channel].high
        );
    }

    function remapByte(value, range) {
        const source = clampByte(value);
        const low = clampByte(range && range.low);
        const high = clampByte(range && range.high);
        if (source == null || low == null || high == null || low > high) return null;
        return Math.round(low + (source / 255) * (high - low));
    }

    function remapRgba(data, value) {
        const remap = normalizeRemap(value);
        if (!data || typeof data.length !== 'number' || !remap) return null;
        const output = new Uint8ClampedArray(data);
        const m = remap.m, r = remap.r, cc = remap.cc;
        const mScale = (m.high - m.low) / 255;
        const rScale = (r.high - r.low) / 255;
        const ccScale = (cc.high - cc.low) / 255;
        for (let index = 0; index + 3 < output.length; index += 4) {
            output[index] = Math.round(m.low + output[index] * mScale);
            output[index + 1] = Math.round(r.low + output[index + 1] * rScale);
            output[index + 2] = Math.round(cc.low + output[index + 2] * ccScale);
        }
        return output;
    }

    function remapRgbaMasked(data, fromValue, toValue, mask, maskWidth, maskHeight, width, height) {
        const from = normalizeRemap(fromValue || IDENTITY);
        const to = normalizeRemap(toValue || IDENTITY);
        if (!data || !from || !to || !mask || !maskWidth || !maskHeight || !width || !height) return null;
        const output = new Uint8ClampedArray(data);
        for (let y = 0; y < height; y++) {
            const my = Math.min(maskHeight - 1, Math.floor(y * maskHeight / height));
            for (let x = 0; x < width; x++) {
                const mx = Math.min(maskWidth - 1, Math.floor(x * maskWidth / width));
                const strength = Number(mask[my * maskWidth + mx] || 0) / 255;
                if (strength <= 0) continue;
                const offset = (y * width + x) * 4;
                for (let channelIndex = 0; channelIndex < CHANNELS.length; channelIndex++) {
                    const channel = CHANNELS[channelIndex];
                    const sourceRange = from[channel];
                    const targetRange = to[channel];
                    const span = sourceRange.high - sourceRange.low;
                    const normalized = span > 0
                        ? Math.max(0, Math.min(1, (data[offset + channelIndex] - sourceRange.low) / span))
                        : 0;
                    const mapped = targetRange.low + normalized * (targetRange.high - targetRange.low);
                    output[offset + channelIndex] = Math.round(
                        data[offset + channelIndex] * (1 - strength) + mapped * strength
                    );
                }
            }
        }
        return output;
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

    // SPB-93 T52: extracted Spec Tools cannot see triggerPreviewRender inside
    // the canvas IIFE. Use its public dedup-safe bridge; before this, 0/5 Spec
    // Tool families refreshed the live compiled preview from their modules.
    function kickLivePreview() {
        if (root && typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview();
        else if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }

    function cloneValue(value) {
        return value == null ? null : JSON.parse(JSON.stringify(value));
    }

    function captureLiveSpecPreview(session) {
        if (!session || typeof document === 'undefined') return false;
        const image = document.getElementById('livePreviewSpecImg');
        if (!image || !image.complete || !image.naturalWidth || !image.naturalHeight || !image.src) return false;
        try {
            const canvas = document.createElement('canvas');
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            const context = canvas.getContext('2d', { willReadFrequently: true });
            if (!context) return false;
            context.drawImage(image, 0, 0, canvas.width, canvas.height);
            session.previewElement = image;
            session.previewSource = image.src;
            session.previewSpecSig = root ? root.__spbSpecSig : undefined;
            session.previewCanvas = canvas;
            session.previewContext = context;
            session.previewPixels = new Uint8ClampedArray(
                context.getImageData(0, 0, canvas.width, canvas.height).data
            );
            session.previewWidth = canvas.width;
            session.previewHeight = canvas.height;
            return true;
        } catch (_) {
            return false;
        }
    }

    function renderLocalSpecPreview(value) {
        const session = previewSession;
        const zone = session && session.zone;
        if (!session || !zone || !session.previewPixels || !session.previewContext) return false;
        const paintCanvas = document.getElementById('paintCanvas');
        const maskWidth = paintCanvas && paintCanvas.width ? paintCanvas.width : Math.round(Math.sqrt(zone.regionMask?.length || 0));
        const maskHeight = paintCanvas && paintCanvas.height ? paintCanvas.height : maskWidth;
        const pixels = remapRgbaMasked(
            session.previewPixels,
            session.beforeRemap || IDENTITY,
            value || IDENTITY,
            zone.regionMask,
            maskWidth,
            maskHeight,
            session.previewWidth,
            session.previewHeight
        );
        if (!pixels) return false;
        const frame = session.previewContext.createImageData(session.previewWidth, session.previewHeight);
        frame.data.set(pixels);
        session.previewContext.putImageData(frame, 0, 0);
        session.previewElement.src = session.previewCanvas.toDataURL('image/png');
        // The displayed pixels are now a private client draft, not the image
        // represented by the server-owned signature. Clearing it forces the
        // next real render (including Ctrl+Z) to return authoritative pixels
        // instead of replying `spec_unchanged` and leaving this draft onscreen.
        if (root) root.__spbSpecSig = '';
        session.lastLocalPreview = true;
        return true;
    }

    function refreshPreviewOnly() {
        if (typeof renderZones === 'function') renderZones();
        if (typeof renderZoneDetail === 'function') renderZoneDetail(selectedZoneIndex);
        kickLivePreview();
    }

    function endPreviewSession(restore) {
        if (previewTimer) clearTimeout(previewTimer);
        previewTimer = 0;
        const session = previewSession;
        previewSession = null;
        if (restore && session && session.zone) {
            session.zone.specMaterialRemap = cloneValue(session.beforeRemap);
            session.zone.specMaterialOverride = cloneValue(session.beforeOverride);
            if (session.previewElement && session.previewSource) {
                session.previewElement.src = session.previewSource;
                if (root) root.__spbSpecSig = session.previewSpecSig;
            }
            else refreshPreviewOnly();
        }
    }

    function closeDialog() {
        if (typeof document === 'undefined') return;
        endPreviewSession(true);
        document.getElementById('specMaterialRemapOverlay')?.classList.remove('active');
    }

    function updateBars(value) {
        if (typeof document === 'undefined') return;
        const remap = normalizeRemap(value) || normalizeRemap(IDENTITY);
        const labels = { m: 'M', r: 'R', cc: 'CC' };
        for (const channel of CHANNELS) {
            const prefix = `specRemap${labels[channel]}`;
            const bar = document.getElementById(`${prefix}Bar`);
            if (bar) bar.style.background = `linear-gradient(90deg, rgb(${remap[channel].low},${remap[channel].low},${remap[channel].low}), rgb(${remap[channel].high},${remap[channel].high},${remap[channel].high}))`;
        }
    }

    function setInputs(value) {
        if (typeof document === 'undefined') return;
        const remap = normalizeRemap(value) || normalizeRemap(IDENTITY);
        const labels = { m: 'M', r: 'R', cc: 'CC' };
        for (const channel of CHANNELS) {
            const prefix = `specRemap${labels[channel]}`;
            const low = document.getElementById(`${prefix}Low`);
            const high = document.getElementById(`${prefix}High`);
            if (low) low.value = remap[channel].low;
            if (high) high.value = remap[channel].high;
        }
        updateBars(remap);
    }

    function readInputs() {
        if (typeof document === 'undefined') return null;
        const labels = { m: 'M', r: 'R', cc: 'CC' };
        const value = {};
        for (const channel of CHANNELS) {
            const prefix = `specRemap${labels[channel]}`;
            value[channel] = {
                low: document.getElementById(`${prefix}Low`)?.value,
                high: document.getElementById(`${prefix}High`)?.value,
            };
        }
        return normalizeRemap(value);
    }

    function choosePreset(presetId) {
        const preset = PRESETS[presetId];
        if (!preset) return false;
        setInputs(preset);
        scheduleLivePreview();
        return true;
    }

    function applyLivePreview() {
        if (!previewSession || !previewSession.zone) return false;
        const remap = readInputs();
        if (!remap) return false;
        // SPB-93 T52 (2026-08-08), owner verdict: "if you are dragging stuff
        // around on the SOURCE panel side then you can see the changes happening
        // in real time." Before: preset values changed but preview source stayed
        // byte-for-byte identical. Now the draft Zone recipe renders privately;
        // history and autosave remain untouched until Apply.
        previewSession.zone.specMaterialRemap = isIdentity(remap) ? null : remap;
        previewSession.zone.specMaterialOverride = null;
        if (!renderLocalSpecPreview(remap)) refreshPreviewOnly();
        return true;
    }

    function scheduleLivePreview() {
        const remap = readInputs();
        if (remap) updateBars(remap);
        if (!previewSession || !remap) return false;
        if (previewTimer) clearTimeout(previewTimer);
        previewTimer = setTimeout(function () {
            previewTimer = 0;
            applyLivePreview();
        }, 80);
        return true;
    }

    function openDialog() {
        if (typeof document === 'undefined') return false;
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        if (!zone || !selectedPixels) {
            showMessage('Material Range Remapper needs an active Zone selection', 'info');
            return false;
        }
        const overlay = document.getElementById('specMaterialRemapOverlay');
        if (!overlay) return false;
        endPreviewSession(true);
        previewSession = {
            zone,
            index: selectedZoneIndex,
            beforeRemap: cloneValue(zone.specMaterialRemap),
            beforeOverride: cloneValue(zone.specMaterialOverride),
        };
        captureLiveSpecPreview(previewSession);
        setInputs(zone.specMaterialRemap || IDENTITY);
        const summary = document.getElementById('specMaterialRemapSelectionSummary');
        if (summary) summary.textContent = `${zone.name || `Zone ${selectedZoneIndex + 1}`} - ${selectedPixels.toLocaleString()} selected pixels`;
        overlay.classList.add('active');
        overlay.querySelector('input')?.focus();
        return true;
    }

    function refresh(kickPreview) {
        if (typeof renderZones === 'function') renderZones();
        if (typeof renderZoneDetail === 'function') renderZoneDetail(selectedZoneIndex);
        if (typeof updateRegionStatus === 'function') updateRegionStatus();
        if (kickPreview !== false) kickLivePreview();
        if (typeof autoSave === 'function') autoSave();
    }

    function applyActiveZone() {
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        const remap = readInputs();
        if (!zone || !selectedPixels) {
            closeDialog();
            showMessage('Material Range Remapper could not find an active Zone selection', 'warning');
            return false;
        }
        if (zone.lockIntensity) {
            showMessage('Unlock this Zone\'s Intensity before remapping material channels', 'warning');
            return false;
        }
        if (!remap) {
            showMessage('Every Low value must be less than or equal to its High value', 'warning');
            return false;
        }
        const next = isIdentity(remap) ? null : remap;
        const session = previewSession && previewSession.zone === zone ? previewSession : null;
        const beforeRemap = session ? cloneValue(session.beforeRemap) : cloneValue(zone.specMaterialRemap);
        const beforeOverride = session ? cloneValue(session.beforeOverride) : cloneValue(zone.specMaterialOverride);
        if (remapsEqual(beforeRemap, next) && !beforeOverride) {
            closeDialog();
            showMessage('Those material ranges are already active - no history added', 'info');
            return false;
        }
        if (previewTimer) clearTimeout(previewTimer);
        previewTimer = 0;
        zone.specMaterialRemap = beforeRemap;
        zone.specMaterialOverride = beforeOverride;
        if (typeof pushZoneUndo === 'function') pushZoneUndo('Remap spec material ranges');
        zone.specMaterialRemap = next;
        zone.specMaterialOverride = null;
        const keepLocalPreview = !!(session && session.lastLocalPreview);
        previewSession = null;
        refresh(!keepLocalPreview);
        closeDialog();
        showMessage(`Material ranges remapped across ${selectedPixels.toLocaleString()} pixels - M/R/CC detail preserved; paint RGB and alpha unchanged`, 'success');
        return true;
    }

    function clearActiveZone() {
        const zone = getActiveZone();
        const session = previewSession && previewSession.zone === zone ? previewSession : null;
        const beforeRemap = session ? cloneValue(session.beforeRemap) : cloneValue(zone && zone.specMaterialRemap);
        const beforeOverride = session ? cloneValue(session.beforeOverride) : cloneValue(zone && zone.specMaterialOverride);
        if (!zone || !beforeRemap) {
            closeDialog();
            showMessage('The active Zone already uses its original material ranges', 'info');
            return false;
        }
        if (zone.lockIntensity) {
            showMessage('Unlock this Zone\'s Intensity before restoring material ranges', 'warning');
            return false;
        }
        if (previewTimer) clearTimeout(previewTimer);
        previewTimer = 0;
        setInputs(IDENTITY);
        const keepLocalPreview = !!(session && renderLocalSpecPreview(IDENTITY));
        zone.specMaterialRemap = beforeRemap;
        zone.specMaterialOverride = beforeOverride;
        if (typeof pushZoneUndo === 'function') pushZoneUndo('Restore original spec material ranges');
        zone.specMaterialRemap = null;
        zone.specMaterialOverride = beforeOverride;
        previewSession = null;
        refresh(!keepLocalPreview);
        closeDialog();
        showMessage('Original M/R/CC ranges restored; source texture remains intact', 'success');
        return true;
    }

    if (root && typeof document !== 'undefined') {
        root.openSpecMaterialRemap = openDialog;
        root.closeSpecMaterialRemap = closeDialog;
        root.chooseSpecMaterialRemapPreset = choosePreset;
        root.applySpecMaterialRemapToZone = applyActiveZone;
        root.clearSpecMaterialRemapFromZone = clearActiveZone;
        root.updateSpecMaterialRemapPreview = scheduleLivePreview;
        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;
            const overlay = document.getElementById('specMaterialRemapOverlay');
            if (overlay?.classList.contains('active')) {
                event.preventDefault();
                closeDialog();
            }
        });
    }

    return {
        CHANNELS, IDENTITY, PRESETS, clampByte, normalizeRemap, isIdentity,
        remapsEqual, remapByte, remapRgba, remapRgbaMasked, countSelected,
    };
});
