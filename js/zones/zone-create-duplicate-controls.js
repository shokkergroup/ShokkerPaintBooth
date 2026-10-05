(function (global) {
    'use strict';

    function install(deps) {
        deps = deps || {};

        var documentRef = deps.document || (global && global.document);
        var confirmDialog = deps.confirm || function () { return true; };
        var setTimeoutFn = deps.setTimeout || function (fn, ms) { return setTimeout(fn, ms); };
        var getZones = deps.getZones || function () { return []; };
        var getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return -1; };
        var setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
        var maxZones = deps.maxZones || 50;
        var newZoneId = deps.newZoneId || function () { return String(Date.now()); };
        var cloneZoneState = deps.cloneZoneState || function (zone) { return JSON.parse(JSON.stringify(zone || {})); };
        var touchZoneTimestamp = deps.touchZoneTimestamp || function () {};
        var pushZoneUndo = deps.pushZoneUndo || function () {};
        var renderZones = deps.renderZones || function () {};
        var triggerPreviewRender = deps.triggerPreviewRender || function () {};
        var showToast = deps.showToast || function () {};

        function zones() {
            return getZones() || [];
        }

        function addZone(skipUndo) {
            var list = zones();
            if (list.length >= maxZones) {
                showToast('Zone limit reached (' + maxZones + ' max). Too many zones will severely degrade render performance. Delete unused zones first.', true);
                return;
            }
            if (list.length >= 30) {
                showToast('Warning: ' + list.length + ' zones active. Performance may degrade above 30 zones.');
            }
            if (!skipUndo) pushZoneUndo('Add zone');
            var fresh = {
                id: newZoneId(),
                name: 'Zone ' + (list.length + 1),
                color: null,
                base: null,
                pattern: 'none',
                finish: null,
                intensity: '100',
                customSpec: null,
                customPaint: null,
                customBright: null,
                colorMode: 'none',
                pickerColor: '#3366ff',
                pickerTolerance: 40,
                colors: [],
                regionMask: null,
                spatialMask: null,
                hint: 'Pick a base material + pattern, then set the color',
                lockBase: false,
                lockPattern: false,
                lockIntensity: false,
                lockColor: false,
                scale: 1.0,
                patternStack: [],
                specPatternStack: [],
                overlaySpecPatternStack: [],
                thirdOverlaySpecPatternStack: [],
                fourthOverlaySpecPatternStack: [],
                fifthOverlaySpecPatternStack: [],
                wear: 0,
                muted: false,
                patternOffsetX: 0.5,
                patternOffsetY: 0.5,
                patternPlacement: 'normal',
                fitIntoApplyArea: false,
                patternFlipH: false,
                patternFlipV: false,
                patternStrengthMap: null,
                patternStrengthMapEnabled: false,
                baseOffsetX: 0.5,
                baseOffsetY: 0.5,
                baseRotation: 0,
                baseFlipH: false,
                baseFlipV: false,
                basePlacement: 'normal',
                baseScale: 1.0,
                specScale: 1.0,
                specScaleMode: 'match',
                baseColorMode: 'source',
                baseColor: '#ffffff',
                baseColorSource: null,
                baseColorStrength: 1,
                baseColorScale: 1,
                baseColorRotation: 0,
                baseColorFitZone: false,
                alignBaseColorWithBase: true,
                zoneSpecMapPath: null,
                zoneSpecMapName: null,
                zoneSpecMapResolution: null,
                zoneSpecMapStrength: 100,
                gradientStops: null,
                gradientDirection: 'horizontal',
                baseHueOffset: 0,
                baseSaturationAdjust: 0,
                baseBrightnessAdjust: 0,
                secondBaseEnabled: true,
                secondBasePattern: null,
                secondBasePatternOpacity: 100,
                secondBasePatternScale: 1.0,
                secondBasePatternRotation: 0,
                secondBasePatternStrength: 1,
                secondBasePatternInvert: false,
                secondBasePatternHarden: false,
                secondBasePatternOffsetX: 0.5,
                secondBasePatternOffsetY: 0.5,
                secondBaseFitZone: false,
                secondBaseColorSource: null,
                secondBaseHueShift: 0,
                secondBaseSaturation: 0,
                secondBaseBrightness: 0,
                secondBasePatternHueShift: 0,
                secondBasePatternSaturation: 0,
                secondBasePatternBrightness: 0,
                thirdBaseEnabled: true,
                thirdBase: null,
                thirdBaseColor: '#ffffff',
                thirdBaseStrength: 0,
                thirdBaseBlendMode: 'noise',
                thirdBaseFractalScale: 24,
                thirdBaseScale: 1.0,
                thirdBaseColorScale: 1.0,
                thirdBaseSpecScale: 1.0,
                thirdBasePattern: null,
                thirdBasePatternOpacity: 100,
                thirdBasePatternScale: 1.0,
                thirdBasePatternRotation: 0,
                thirdBasePatternStrength: 1,
                thirdBasePatternInvert: false,
                thirdBasePatternHarden: false,
                thirdBasePatternOffsetX: 0.5,
                thirdBasePatternOffsetY: 0.5,
                thirdBaseFitZone: false,
                thirdBaseColorSource: null,
                thirdBaseHueShift: 0,
                thirdBaseSaturation: 0,
                thirdBaseBrightness: 0,
                thirdBasePatternHueShift: 0,
                thirdBasePatternSaturation: 0,
                thirdBasePatternBrightness: 0,
                fourthBaseEnabled: true,
                fourthBase: null,
                fourthBaseColor: '#ffffff',
                fourthBaseStrength: 0,
                fourthBaseBlendMode: 'noise',
                fourthBaseFractalScale: 24,
                fourthBaseScale: 1.0,
                fourthBaseColorScale: 1.0,
                fourthBaseSpecScale: 1.0,
                fourthBasePattern: null,
                fourthBasePatternOpacity: 100,
                fourthBasePatternScale: 1.0,
                fourthBasePatternRotation: 0,
                fourthBasePatternStrength: 1,
                fourthBasePatternInvert: false,
                fourthBasePatternHarden: false,
                fourthBasePatternOffsetX: 0.5,
                fourthBasePatternOffsetY: 0.5,
                fourthBaseFitZone: false,
                fourthBaseColorSource: null,
                fourthBaseHueShift: 0,
                fourthBaseSaturation: 0,
                fourthBaseBrightness: 0,
                fourthBasePatternHueShift: 0,
                fourthBasePatternSaturation: 0,
                fourthBasePatternBrightness: 0,
                fifthBaseEnabled: true,
                fifthBase: null,
                fifthBaseColor: '#ffffff',
                fifthBaseStrength: 0,
                fifthBaseBlendMode: 'noise',
                fifthBaseFractalScale: 24,
                fifthBaseScale: 1.0,
                fifthBaseColorScale: 1.0,
                fifthBaseSpecScale: 1.0,
                fifthBasePattern: null,
                fifthBasePatternOpacity: 100,
                fifthBasePatternScale: 1.0,
                fifthBasePatternRotation: 0,
                fifthBasePatternStrength: 1,
                fifthBasePatternInvert: false,
                fifthBasePatternHarden: false,
                fifthBasePatternOffsetX: 0.5,
                fifthBasePatternOffsetY: 0.5,
                fifthBaseFitZone: false,
                fifthBaseColorSource: null,
                fifthBaseHueShift: 0,
                fifthBaseSaturation: 0,
                fifthBaseBrightness: 0,
                fifthBasePatternHueShift: 0,
                fifthBasePatternSaturation: 0,
                fifthBasePatternBrightness: 0,
                baseStrength: 1,
                baseSpecBlendMode: 'normal',
                patternSpecMult: 1,
                hardEdge: true
            };
            if (global.SPBStableZoneSeeds) {
                global.SPBStableZoneSeeds.assignFresh(list, fresh, global._isSuppressedLegacyZone, global._zoneHasRenderableMaterial, global._renderMaskHasPixels);
            }
            list.push(fresh);
            setSelectedZoneIndex(list.length - 1);
            renderZones();
            var listEl = documentRef ? documentRef.getElementById('zoneList') : null;
            if (listEl) listEl.scrollTop = listEl.scrollHeight;
        }

        function duplicateZone(index) {
            var list = zones();
            var src = list[index];
            if (!src) return;
            pushZoneUndo('Duplicate zone "' + src.name + '"');
            var clone = cloneZoneState(src, {
                preserveId: false,
                includeRegionMask: true,
                includeSpatialMask: true,
                includePatternStrengthMap: true
            });
            clone.name = src.name + ' (copy)';
            if (global.SPBStableZoneSeeds) {
                global.SPBStableZoneSeeds.assignFresh(list, clone, global._isSuppressedLegacyZone, global._zoneHasRenderableMaterial, global._renderMaskHasPixels);
            }
            touchZoneTimestamp(clone);
            list.splice(index + 1, 0, clone);
            setSelectedZoneIndex(index + 1);
            renderZones();
            triggerPreviewRender();
            showToast('Duplicated "' + src.name + '" -- Ctrl+Z to undo');

            setTimeoutFn(function () {
                var newCard = documentRef ? documentRef.getElementById('zone-card-' + (index + 1)) : null;
                if (!newCard) return;
                newCard.classList.add('just-duplicated');
                setTimeoutFn(function () {
                    if (newCard) newCard.classList.remove('just-duplicated');
                }, 650);
            }, 40);
        }

        function applyFinishToAllZones() {
            var list = zones();
            var selectedIndex = getSelectedZoneIndex();
            var src = list[selectedIndex];
            if (!src || (!src.base && !src.finish)) {
                showToast('Selected zone has no finish to apply', true);
                return;
            }
            if (!confirmDialog('Apply "' + (src.base || src.finish) + '" to ALL ' + list.length + ' zones?')) return;
            pushZoneUndo('Apply finish to all zones');
            list.forEach(function (zone, index) {
                if (index === selectedIndex) return;
                zone.base = src.base;
                zone.pattern = src.pattern;
                zone.finish = src.finish;
                zone.intensity = src.intensity;
                zone.patternIntensity = src.patternIntensity;
                zone.scale = src.scale;
                zone.patternStack = JSON.parse(JSON.stringify(src.patternStack || []));
            });
            renderZones();
            triggerPreviewRender();
            showToast('Applied finish to all ' + list.length + ' zones');
        }

        global.addZone = addZone;
        global.duplicateZone = duplicateZone;
        global.applyFinishToAllZones = applyFinishToAllZones;
    }

    global.SPBZoneCreateDuplicateControls = {
        install: install
    };
})(typeof window !== 'undefined' ? window : globalThis);
