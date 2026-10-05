(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSpecLightingMask = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    // SPB-93 tick 30, owner verdict: build only real car-template/spec tools.
    // iRacing's official contract defines spec-TGA alpha as a lighting mask:
    // 255 keeps environment/spec lighting, 0 suppresses it. This is for fake
    // holes, grille openings, deep gaps, and other unlit geometry—not a matte
    // paint shortcut. Baseline: SPB exported/preserved alpha but exposed no
    // Zone control, so painters had to leave the app and edit the TGA channel.
    const PRESETS = Object.freeze({
        source: Object.freeze({
            id: 'source',
            label: 'Use Source Alpha',
            value: null,
            use: 'Remove the override and preserve the finish or imported spec map alpha.',
        }),
        full: Object.freeze({
            id: 'full',
            label: 'Full Lighting',
            value: 255,
            use: 'Force normal sun, reflection, and environment response in the selected footprint.',
        }),
        reduced: Object.freeze({
            id: 'reduced',
            label: 'Reduced Lighting',
            value: 128,
            use: 'Cut lighting response in half for recessed vents and deep seams.',
        }),
        kill: Object.freeze({
            id: 'kill',
            label: 'Kill Lighting',
            value: 0,
            use: 'Suppress spec and environment lighting for fake holes and open grille areas.',
        }),
    });

    function countSelected(mask) {
        let count = 0;
        if (!mask || typeof mask.length !== 'number') return count;
        for (let index = 0; index < mask.length; index++) {
            if (mask[index] > 0) count++;
        }
        return count;
    }

    function normalizeValue(value) {
        if (value == null || value === '') return null;
        const number = Number(value);
        if (!Number.isFinite(number)) return null;
        return Math.max(0, Math.min(255, Math.round(number)));
    }

    function buildZonePatch(presetId) {
        const preset = PRESETS[presetId];
        if (!preset) return null;
        return { specLightingMask: preset.value };
    }

    function applyPatchToZone(zone, presetId) {
        const patch = buildZonePatch(presetId);
        if (!zone || !patch) return false;
        zone.specLightingMask = patch.specLightingMask;
        return true;
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

    function valueLabel(value) {
        const normalized = normalizeValue(value);
        if (normalized == null) return 'Source alpha';
        return `A ${normalized} (${Math.round(normalized / 255 * 100)}% lighting)`;
    }

    function closeDialog() {
        if (typeof document === 'undefined') return;
        const overlay = document.getElementById('specLightingMaskOverlay');
        if (overlay) overlay.classList.remove('active');
    }

    function openDialog() {
        if (typeof document === 'undefined') return false;
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        if (!zone || !selectedPixels) {
            showMessage('Lighting Mask needs an active Zone selection - draw the hole, grille, vent, or seam footprint first', 'info');
            return false;
        }
        const overlay = document.getElementById('specLightingMaskOverlay');
        if (!overlay) return false;
        const summary = document.getElementById('specLightingMaskSelectionSummary');
        if (summary) {
            summary.textContent = `${zone.name || `Zone ${selectedZoneIndex + 1}`} - ` +
                `${selectedPixels.toLocaleString()} selected pixels - ${valueLabel(zone.specLightingMask)}`;
        }
        overlay.classList.add('active');
        const firstPreset = overlay.querySelector('.lighting-mask-preset');
        if (firstPreset && typeof firstPreset.focus === 'function') firstPreset.focus();
        return true;
    }

    function applyActiveZone(presetId) {
        const preset = PRESETS[presetId];
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        if (!preset || !zone || !selectedPixels) {
            closeDialog();
            showMessage('Lighting Mask could not find an active Zone selection', 'warning');
            return false;
        }
        if (zone.lockIntensity) {
            showMessage('Unlock this Zone\'s Intensity before changing its lighting mask', 'warning');
            return false;
        }
        const before = normalizeValue(zone.specLightingMask);
        const after = normalizeValue(preset.value);
        if (before === after) {
            closeDialog();
            showMessage(`${preset.label} is already active - no history added`, 'info');
            return false;
        }
        if (typeof pushZoneUndo === 'function') pushZoneUndo(`Set ${preset.label} spec lighting mask`);
        applyPatchToZone(zone, presetId);
        if (typeof renderZones === 'function') renderZones();
        if (typeof renderZoneDetail === 'function') renderZoneDetail(selectedZoneIndex);
        if (typeof updateRegionStatus === 'function') updateRegionStatus();
        kickLivePreview();
        if (typeof autoSave === 'function') autoSave();
        closeDialog();
        showMessage(
            `${preset.label} applied to ${selectedPixels.toLocaleString()} pixels - ${valueLabel(preset.value)}; RGB and M/R/CC unchanged`,
            'success'
        );
        return true;
    }

    if (root && typeof document !== 'undefined') {
        root.openSpecLightingMask = openDialog;
        root.closeSpecLightingMask = closeDialog;
        root.applySpecLightingMaskPreset = applyActiveZone;
        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;
            const overlay = document.getElementById('specLightingMaskOverlay');
            if (overlay && overlay.classList.contains('active')) {
                event.preventDefault();
                closeDialog();
            }
        });
    }

    return { PRESETS, countSelected, normalizeValue, valueLabel, buildZonePatch, applyPatchToZone };
});
