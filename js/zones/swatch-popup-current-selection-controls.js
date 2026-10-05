(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const getLayerPaintSpecialId = deps.getLayerPaintSpecialId || function() { return ''; };

        function getCurrentSwatchPickerId(args) {
            args = args || {};
            const zone = args.zone || {};
            const type = args.type;
            const layerIndex = args.layerIndex;
            if (type === 'specOverlay') return global.SPBSpecOverlayPicker.current();
            if (type === 'base') return zone.finish ? ('mono:' + zone.finish) : (zone.base || '');
            if (type === 'pattern') return zone.pattern || 'none';
            if (type === 'stackPattern') return (zone.patternStack && zone.patternStack[layerIndex]) ? zone.patternStack[layerIndex].id : 'none';
            if (type === 'secondBase') return zone.secondBase || '';
            if (type === 'thirdBase') return zone.thirdBase || '';
            if (type === 'fourthBase') return zone.fourthBase || '';
            if (type === 'fifthBase') return zone.fifthBase || '';
            if (type === 'baseColorSource') return zone.baseColorSource || '';
            if (type === 'secondBaseColorSource') return zone.secondBaseColorSource || '';
            if (type === 'thirdBaseColorSource') return zone.thirdBaseColorSource || '';
            if (type === 'fourthBaseColorSource') return zone.fourthBaseColorSource || '';
            if (type === 'fifthBaseColorSource') return zone.fifthBaseColorSource || '';
            if (type === 'secondBasePattern') return zone.secondBasePattern || 'none';
            if (type === 'thirdBasePattern') return zone.thirdBasePattern || 'none';
            if (type === 'layerSpecialPaint') {
                const specialId = getLayerPaintSpecialId();
                return specialId ? ('mono:' + specialId) : '';
            }
            return '';
        }

        Object.assign(global, { getCurrentSwatchPickerId: getCurrentSwatchPickerId });
    }

    global.SPBSwatchPopupCurrentSelectionControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
