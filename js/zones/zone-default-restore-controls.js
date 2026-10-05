(function (global) {
    'use strict';

    function install(deps) {
        deps = deps || {};

        var ensureAllZonesHaveIds = deps.ensureAllZonesHaveIds || function () {};
        var setZones = deps.setZones || function () {};
        var setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
        var pushZoneUndo = deps.pushZoneUndo || function () {};
        var renderZones = deps.renderZones || function () {};
        var renderZoneDetail = deps.renderZoneDetail || function () {};
        var autoSave = deps.autoSave || function () {};
        var showToast = deps.showToast || function () {};

        // SPB-SIMPLIFY-2026-07-19 owner curation: default zones 10 -> 5, kept identical to the two
        // default sets in paint-booth-2-state-zones.js (boot init + restoreAllZones).
        function createDefaultZones() {
            return [
                {
                    name: 'Zone 1', color: null, base: null, pattern: 'none', finish: null, intensity: '100', colorMode: 'none', pickerColor: '#3366ff', pickerTolerance: 40, colors: [], regionMask: null,
                    hint: 'Use Pick Color mode - click your PRIMARY body color on the paint'
                },
                {
                    name: 'Zone 2', color: null, base: null, pattern: 'none', finish: null, intensity: '100', colorMode: 'none', pickerColor: '#ffcc00', pickerTolerance: 40, colors: [], regionMask: null,
                    hint: 'Click your SECOND body color (delete this zone if single-color car)'
                },
                {
                    name: 'Zone 3', color: null, base: null, pattern: 'none', finish: null, intensity: '100', colorMode: 'none', pickerColor: '#ffaa00', pickerTolerance: 35, colors: [], regionMask: null,
                    hint: 'Numbers or a third color - Magic Wand each color, or Draw Region manually'
                },
                {
                    name: 'Zone 4', color: null, base: null, pattern: 'none', finish: null, intensity: '80', colorMode: 'none', pickerColor: '#ffffff', pickerTolerance: 30, colors: [], regionMask: null,
                    hint: 'Sponsors / artwork - draw regions or pick a shared color. + Add Zone for more'
                },
                {
                    name: 'Everything Else', color: 'remaining', base: 'gloss', pattern: 'none', finish: null, intensity: '50', colorMode: 'special', pickerColor: '#888888', pickerTolerance: 40, colors: [], regionMask: null,
                    hint: 'Safety net - catches any pixels not claimed by zones above'
                }
            ];
        }

        function restoreAllZones() {
            pushZoneUndo('Restore all zones');
            var defaults = createDefaultZones();
            ensureAllZonesHaveIds(defaults);
            setZones(defaults);
            setSelectedZoneIndex(0);
            renderZones();
            renderZoneDetail(0);
            autoSave();
            showToast('All 5 default zones restored');
        }

        global.restoreAllZones = restoreAllZones;
        // [SPB-EASY-ISOLATION 2026-08-26] Easy Mode's clean first-entry state reuses the
        // ONE canonical default-zone factory instead of growing a third drifting copy.
        global.spbCreateDefaultZones = createDefaultZones;
    }

    global.SPBZoneDefaultRestoreControls = {
        install: install
    };
})(typeof window !== 'undefined' ? window : globalThis);
