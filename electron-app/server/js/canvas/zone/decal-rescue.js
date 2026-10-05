(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBDecalRescue = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    // SPB-93 tick 28, owner verdict: add only real car-paint/spec tools, not
    // gimmicks. Served/repo baseline was 0 implemented sim-stamp rescue tools;
    // the three promised preset ids existed only in PRIORITIES.md. These flat
    // Foundation bases are already engine-tested decal materials and source
    // mode is regression-tested to preserve the painter's exact RGB artwork.
    const PRESETS = Object.freeze({
        flat_vinyl: Object.freeze({
            id: 'flat_vinyl',
            label: 'Flat Vinyl',
            base: 'f_vinyl_wrap',
            metallic: 0,
            roughness: 100,
            clearcoat: 110,
            use: 'Neutralize chrome or candy beneath sim-stamped numbers and sponsors.',
        }),
        satin_decal: Object.freeze({
            id: 'satin_decal',
            label: 'Satin Decal',
            base: 'f_clear_satin',
            metallic: 0,
            roughness: 100,
            clearcoat: 75,
            use: 'Keep printed vinyl readable with a controlled soft sheen.',
        }),
        gloss_decal: Object.freeze({
            id: 'gloss_decal',
            label: 'Gloss Decal',
            base: 'f_soft_gloss',
            metallic: 0,
            roughness: 42,
            clearcoat: 22,
            use: 'Give a clean printed decal gloss without metallic contamination.',
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

    function buildZonePatch(presetId) {
        const preset = PRESETS[presetId];
        if (!preset) return null;
        return {
            base: preset.base,
            baseStrength: 1,
            baseSpecStrength: 1,
            baseSpecBlendMode: 'normal',
            baseColorMode: 'source',
            baseColorSource: null,
            baseColorStrength: 1,
            pattern: 'none',
            patternStack: [],
            specPatternStack: [],
            overlaySpecPatternStack: [],
            thirdOverlaySpecPatternStack: [],
            fourthOverlaySpecPatternStack: [],
            fifthOverlaySpecPatternStack: [],
            patternStrengthMap: null,
            patternStrengthMapEnabled: false,
            secondBasePattern: null,
            thirdBase: null,
            thirdBasePattern: null,
            thirdBaseStrength: 0,
            fourthBase: null,
            fourthBasePattern: null,
            fourthBaseStrength: 0,
            fifthBase: null,
            fifthBasePattern: null,
            fifthBaseStrength: 0,
            finish: null,
            finishColors: null,
            intensity: '100',
            customSpec: null,
            customPaint: null,
            customBright: null,
            zoneSpecMapPath: null,
            zoneSpecMapName: null,
            zoneSpecMapResolution: null,
            zoneSpecMapStrength: 100,
            // SPB-93 09-08: native Flat Vinyl retained Remapper's M20 floor,
            // contradicting the promised M0. Establish the advertised flat
            // material after all base texture; keep the separate lighting mask.
            specMaterialRemap: null,
            specMaterialOverride: { m: preset.metallic, r: preset.roughness, cc: preset.clearcoat, a: 255 },
            specShiftR: 0,
            specShiftG: 0,
            specShiftB: 0,
            spatialMask: null,
            sourceLayer: null,
            sourceLayers: [],
            sourceLayerBindings: {},
            wear: 0,
            muted: false,
            useRegion: true,
            color: null,
            colorMode: 'none',
            colors: [],
        };
    }

    function applyPatchToZone(zone, presetId) {
        const patch = buildZonePatch(presetId);
        if (!zone || !patch) return false;
        Object.assign(zone, patch);
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

    function closeDialog() {
        if (typeof document === 'undefined') return;
        const overlay = document.getElementById('decalRescueOverlay');
        if (overlay) overlay.classList.remove('active');
    }

    function openDialog() {
        if (typeof document === 'undefined') return false;
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        if (!zone || !selectedPixels) {
            showMessage('Decal Rescue needs an active Zone selection - draw the number or sponsor footprint first', 'info');
            return false;
        }
        const overlay = document.getElementById('decalRescueOverlay');
        if (!overlay) return false;
        const summary = document.getElementById('decalRescueSelectionSummary');
        if (summary) {
            summary.textContent = `${zone.name || `Zone ${selectedZoneIndex + 1}`} - ` +
                `${selectedPixels.toLocaleString()} selected pixels`;
        }
        const restriction = document.getElementById('decalRescueRestrictionNote');
        if (restriction) {
            restriction.hidden = !zone.sourceLayer;
            restriction.textContent = zone.sourceLayer
                ? 'This Zone has a PSD layer restriction. Rescue will clear it so the exact UV footprint reaches the compiled spec.'
                : '';
        }
        overlay.classList.add('active');
        const firstPreset = overlay.querySelector('.decal-rescue-preset');
        if (firstPreset && typeof firstPreset.focus === 'function') firstPreset.focus();
        return true;
    }

    function applyActiveZone(presetId) {
        const preset = PRESETS[presetId];
        const zone = getActiveZone();
        const selectedPixels = countSelected(zone && zone.regionMask);
        if (!preset || !zone || !selectedPixels) {
            closeDialog();
            showMessage('Decal Rescue could not find an active Zone selection', 'warning');
            return false;
        }
        if (zone.lockBase || zone.lockPattern || zone.lockIntensity) {
            showMessage('Unlock this Zone\'s Base, Pattern, and Intensity before applying Decal Rescue', 'warning');
            return false;
        }
        if (typeof pushZoneUndo === 'function') {
            pushZoneUndo(`Apply ${preset.label} decal rescue`);
        }
        applyPatchToZone(zone, presetId);
        if (typeof renderZones === 'function') renderZones();
        if (typeof renderZoneDetail === 'function') renderZoneDetail(selectedZoneIndex);
        if (typeof updateRegionStatus === 'function') updateRegionStatus();
        kickLivePreview();
        if (typeof autoSave === 'function') autoSave();
        closeDialog();
        showMessage(
            `${preset.label} Decal Rescue applied to ${selectedPixels.toLocaleString()} pixels - ` +
            `source paint preserved, spec M/R/CC ${preset.metallic}/${preset.roughness}/${preset.clearcoat}`,
            'success'
        );
        return true;
    }

    if (root && typeof document !== 'undefined') {
        root.openDecalRescueKit = openDialog;
        root.closeDecalRescueKit = closeDialog;
        root.applyDecalRescuePreset = applyActiveZone;
        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;
            const overlay = document.getElementById('decalRescueOverlay');
            if (overlay && overlay.classList.contains('active')) {
                event.preventDefault();
                closeDialog();
            }
        });
    }

    return { PRESETS, countSelected, buildZonePatch, applyPatchToZone };
});
