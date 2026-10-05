(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const getSwatchPopupState = deps.getSwatchPopupState || function() {
            return { type: null, zoneIndex: -1, layerIndex: -1 };
        };
        const closeSwatchPicker = deps.closeSwatchPicker || function() {};
        const openDualShiftModal = deps.openDualShiftModal || function() {};
        const getBases = deps.getBases || function() { return []; };

        function call(fn, args) {
            if (typeof fn === 'function') fn.apply(null, args || []);
        }

        function selectSwatchItem(id) {
            const state = getSwatchPopupState();
            const type = state.type;
            const zoneIndex = state.zoneIndex;
            const layerIndex = state.layerIndex;
            if (type === 'specOverlay') {
                global.SPBSpecOverlayPicker.apply(id);
                closeSwatchPicker();
                return;
            }

            if (id === 'dualshift_custom' && type === 'base') {
                closeSwatchPicker();
                openDualShiftModal(zoneIndex);
                return;
            }

            if (type === 'base') {
                call(deps.setZoneBase, [zoneIndex, id]);
            } else if (type === 'pattern') {
                call(deps.setZonePattern, [zoneIndex, id]);
            } else if (type === 'stackPattern') {
                call(deps.setPatternLayerId, [zoneIndex, layerIndex, id]);
            } else if (type === 'secondBase') {
                call(deps.setZoneSecondBase, [zoneIndex, id || '']);
            } else if (type === 'thirdBase') {
                call(deps.setZoneThirdBase, [zoneIndex, id || '']);
            } else if (type === 'fourthBase') {
                call(deps.setZoneFourthBase, [zoneIndex, id || '']);
            } else if (type === 'fifthBase') {
                call(deps.setZoneFifthBase, [zoneIndex, id || '']);
            } else if (type === 'baseColorSource') {
                call(deps.setZoneBaseColorSource, [zoneIndex, id || null]);
            } else if (type === 'overlayBaseColor') {
                if (id) {
                    call(deps.setZoneSecondBaseColorSource, [zoneIndex, 'base:' + id]);
                    const baseObj = getBases().find(function(base) { return base.id === id; });
                    if (baseObj && baseObj.swatch) {
                        call(deps.setZoneSecondBaseColor, [zoneIndex, baseObj.swatch]);
                    }
                }
            } else if (type === 'secondBaseColorSource') {
                call(deps.setZoneSecondBaseColorSource, [zoneIndex, id || null]);
            } else if (type === 'thirdBaseColorSource') {
                call(deps.setZoneThirdBaseColorSource, [zoneIndex, id || null]);
            } else if (type === 'fourthBaseColorSource') {
                call(deps.setZoneFourthBaseColorSource, [zoneIndex, id || null]);
            } else if (type === 'fifthBaseColorSource') {
                call(deps.setZoneFifthBaseColorSource, [zoneIndex, id || null]);
            } else if (type === 'secondBasePattern') {
                call(deps.setZoneSecondBasePattern, [zoneIndex, (id === 'none' || id === '') ? '' : id]);
            } else if (type === 'thirdBasePattern') {
                call(deps.setZoneThirdBasePattern, [zoneIndex, (id === 'none' || id === '') ? '' : id]);
            } else if (type === 'layerSpecialPaint') {
                call(deps.setLayerPaintSpecial, [(id || '').replace(/^mono:/, '')]);
            }
            closeSwatchPicker();
        }

        Object.assign(global, { selectSwatchItem: selectSwatchItem });
    }

    global.SPBSwatchPopupSelectionControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
