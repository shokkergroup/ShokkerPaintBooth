(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var getZones = typeof deps.getZones === 'function' ? deps.getZones : function() { return []; };
        var pushZoneUndo = typeof deps.pushZoneUndo === 'function' ? deps.pushZoneUndo : function() {};
        var renderZones = typeof deps.renderZones === 'function' ? deps.renderZones : function() {};
        var renderZoneDetail = typeof deps.renderZoneDetail === 'function' ? deps.renderZoneDetail : function() {};
        var triggerPreviewRender = typeof deps.triggerPreviewRender === 'function' ? deps.triggerPreviewRender : function() {};
        var showToast = typeof deps.showToast === 'function' ? deps.showToast : function() {};

        // FINISH DNA - Shareable zone configuration string (#25)
        // Format: SHOKK:v1:{base64_encoded_json}
        // ====================================================================
        
        /**
         * Extract the DNA payload from a zone - all settings that define its finish appearance.
         */
        function _extractZoneDNA(zoneIndex) {
            var zones = getZones();
            if (zoneIndex < 0 || zoneIndex >= zones.length) return null;
            var z = zones[zoneIndex];
            // 2026-04-21 HEENAN OVERNIGHT iter 9: switched numeric/boolean
            // `||` to `??` on fields where falsy is legitimate-and-non-default.
            // Pre-fix, a painter with explicit `scale=0` or `baseScale=0`
            // got the default silently promoted in at this capture step,
            // BEFORE the strip layer even ran. Arrays / strings where empty
            // ~ missing still use `||`.
            var dna = {
                v: 1,
                // Core finish
                base: z.base || null,
                finish: z.finish || null,
                pattern: z.pattern || 'none',
                intensity: z.intensity ?? '100',
                scale: z.scale ?? 1.0,
                // Base positioning
                baseRotation: z.baseRotation ?? 0,
                baseOffsetX: z.baseOffsetX != null ? z.baseOffsetX : 0.5,
                baseOffsetY: z.baseOffsetY != null ? z.baseOffsetY : 0.5,
                baseFlipH: z.baseFlipH ?? false,
                baseFlipV: z.baseFlipV ?? false,
                basePlacement: z.basePlacement || 'normal',
                // Base color settings
                baseColorMode: z.baseColorMode || 'source',
                baseColor: z.baseColor || '#ffffff',
                baseColorSource: z.baseColorSource || null,
                baseColorStrength: z.baseColorStrength != null ? z.baseColorStrength : 1,
                baseColorScale: z.baseColorScale != null ? z.baseColorScale : 1,
                baseColorRotation: z.baseColorRotation != null ? z.baseColorRotation : 0,
                baseColorFitZone: z.baseColorFitZone ?? false,
                alignBaseColorWithBase: z.alignBaseColorWithBase !== false,
                baseStrength: z.baseStrength ?? 1,
                baseSpecStrength: z.baseSpecStrength ?? 1,
                baseScale: z.baseScale ?? 1.0,
                specRotation: z.specRotation ?? 0,
                specScale: z.specScaleMode === 'independent' ? (z.specScale ?? 1.0) : (z.baseScale ?? 1.0),
                specScaleMode: z.specScaleMode === 'independent' ? 'independent' : 'match',
                patternSpecMult: z.patternSpecMult ?? 1,
                gradientStops: z.gradientStops || null,
                gradientDirection: z.gradientDirection || 'horizontal',
                baseHueOffset: z.baseHueOffset ?? 0,
                baseSaturationAdjust: z.baseSaturationAdjust ?? 0,
                baseBrightnessAdjust: z.baseBrightnessAdjust ?? 0,
                // Pattern positioning
                patternOffsetX: z.patternOffsetX != null ? z.patternOffsetX : 0.5,
                patternOffsetY: z.patternOffsetY != null ? z.patternOffsetY : 0.5,
                patternFlipH: z.patternFlipH ?? false,
                patternFlipV: z.patternFlipV ?? false,
                patternPlacement: z.patternPlacement || 'normal',
                // Wear
                wear: z.wear ?? 0,
                // 2nd base overlay
                secondBase: z.secondBase || null,
                secondBaseEnabled: z.secondBaseEnabled !== false,
                secondBaseColor: z.secondBaseColor || '#ffffff',
                secondBaseStrength: z.secondBaseStrength ?? 0,
                secondBaseBlendMode: z.secondBaseBlendMode || 'noise',
                secondBaseFractalScale: z.secondBaseFractalScale ?? 24,
                secondBaseScale: z.secondBaseScale ?? 1.0,
                secondBaseColorScale: z.secondBaseColorScale ?? 1.0,
                secondBaseSpecScale: z.secondBaseSpecScale ?? 1.0,
                secondBaseColorSource: z.secondBaseColorSource || null,
                secondBaseHueShift: z.secondBaseHueShift ?? 0,
                secondBaseSaturation: z.secondBaseSaturation ?? 0,
                secondBaseBrightness: z.secondBaseBrightness ?? 0,
                // 3rd base overlay
                thirdBase: z.thirdBase || null,
                thirdBaseEnabled: z.thirdBaseEnabled !== false,
                thirdBaseColor: z.thirdBaseColor || '#ffffff',
                thirdBaseStrength: z.thirdBaseStrength ?? 0,
                thirdBaseBlendMode: z.thirdBaseBlendMode || 'noise',
                thirdBaseFractalScale: z.thirdBaseFractalScale ?? 24,
                thirdBaseScale: z.thirdBaseScale ?? 1.0,
                thirdBaseColorScale: z.thirdBaseColorScale ?? 1.0,
                thirdBaseSpecScale: z.thirdBaseSpecScale ?? 1.0,
                thirdBaseColorSource: z.thirdBaseColorSource || null,
                thirdBaseHueShift: z.thirdBaseHueShift ?? 0,
                thirdBaseSaturation: z.thirdBaseSaturation ?? 0,
                thirdBaseBrightness: z.thirdBaseBrightness ?? 0,
                // 4th base overlay
                fourthBase: z.fourthBase || null,
                fourthBaseEnabled: z.fourthBaseEnabled !== false,
                fourthBaseColor: z.fourthBaseColor || '#ffffff',
                fourthBaseStrength: z.fourthBaseStrength ?? 0,
                fourthBaseBlendMode: z.fourthBaseBlendMode || 'noise',
                fourthBaseFractalScale: z.fourthBaseFractalScale ?? 24,
                fourthBaseScale: z.fourthBaseScale ?? 1.0,
                fourthBaseColorScale: z.fourthBaseColorScale ?? 1.0,
                fourthBaseSpecScale: z.fourthBaseSpecScale ?? 1.0,
                fourthBaseColorSource: z.fourthBaseColorSource || null,
                fourthBaseHueShift: z.fourthBaseHueShift ?? 0,
                fourthBaseSaturation: z.fourthBaseSaturation ?? 0,
                fourthBaseBrightness: z.fourthBaseBrightness ?? 0,
                // 5th base overlay
                fifthBase: z.fifthBase || null,
                fifthBaseEnabled: z.fifthBaseEnabled !== false,
                fifthBaseColor: z.fifthBaseColor || '#ffffff',
                fifthBaseStrength: z.fifthBaseStrength ?? 0,
                fifthBaseBlendMode: z.fifthBaseBlendMode || 'noise',
                fifthBaseFractalScale: z.fifthBaseFractalScale ?? 24,
                fifthBaseScale: z.fifthBaseScale ?? 1.0,
                fifthBaseColorScale: z.fifthBaseColorScale ?? 1.0,
                fifthBaseSpecScale: z.fifthBaseSpecScale ?? 1.0,
                fifthBaseColorSource: z.fifthBaseColorSource || null,
                fifthBaseHueShift: z.fifthBaseHueShift ?? 0,
                fifthBaseSaturation: z.fifthBaseSaturation ?? 0,
                fifthBaseBrightness: z.fifthBaseBrightness ?? 0,
            };
            // Keep Finish DNA in lockstep with the advanced overlay UI. These are
            // render-visible knobs that used to survive full config save/open but
            // not the quick SHOKK:v1 DNA copy/paste path.
            var _OVERLAY_DNA_DEFAULTS = {
                Enabled: true,
                SpecStrength: 1,
                Pattern: null,
                PatternOpacity: 100,
                PatternScale: 1,
                PatternRotation: 0,
                PatternStrength: 1,
                PatternInvert: false,
                PatternHarden: false,
                PatternOffsetX: 0.5,
                PatternOffsetY: 0.5,
                FitZone: false,
                PatternHueShift: 0,
                PatternSaturation: 0,
                PatternBrightness: 0,
                PatternFlipH: false,
                PatternFlipV: false,
            };
            ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'].forEach(function(prefix) {
                Object.keys(_OVERLAY_DNA_DEFAULTS).forEach(function(suffix) {
                    var key = prefix + suffix;
                    var val = z[key];
                    dna[key] = (val !== undefined && val !== null) ? val : _OVERLAY_DNA_DEFAULTS[suffix];
                });
            });
            // Strip default/null values to minimize DNA string size.
            // 2026-04-21 HEENAN OVERNIGHT iter 9: the old blanket strip removed
            // any `val === 0` OR `val === false`. That silently lost painter
            // intent on fields where 0 is NOT the canonical load-default - e.g.
            // `baseColorStrength=0` (no base-color overlay, load-default 1),
            // `baseStrength=0`, `baseSpecStrength=0`, `patternSpecMult=0`.
            // When the painter copied DNA from such a zone and pasted onto a
            // target that already had the non-zero default, the target stayed
            // unchanged because the stripped key was absent from DNA.
            //
            // Fix: explicit per-field canonical-default table; a value is
            // stripped only when it equals THAT field's documented default.
            // Falsy values on fields whose default is non-falsy (e.g.
            // `baseStrength=0`) now survive the round-trip. DNA strings may
            // grow slightly for zones with explicit-zero overrides; size
            // impact is bounded and worth the correctness.
            var _DNA_DEFAULTS = {
                // Fields whose canonical default is 0
                rotation: 0,
                wear: 0,
                baseRotation: 0,
                baseHueOffset: 0, baseSaturationAdjust: 0, baseBrightnessAdjust: 0,
                secondBaseStrength: 0, secondBaseHueShift: 0, secondBaseSaturation: 0, secondBaseBrightness: 0,
                thirdBaseStrength: 0,  thirdBaseHueShift: 0,  thirdBaseSaturation: 0,  thirdBaseBrightness: 0,
                fourthBaseStrength: 0, fourthBaseHueShift: 0, fourthBaseSaturation: 0, fourthBaseBrightness: 0,
                fifthBaseStrength: 0,  fifthBaseHueShift: 0,  fifthBaseSaturation: 0,  fifthBaseBrightness: 0,
                // Fields whose canonical default is 1 (NEW strip rules - these
                // were previously mishandled by the blanket val === 0 strip)
                scale: 1.0,
                baseColorStrength: 1,
                baseColorScale: 1.0,
                baseColorRotation: 0,
                baseScale: 1.0,
                specScale: 1.0,
                baseStrength: 1,
                baseSpecStrength: 1,
                patternSpecMult: 1,
                secondBaseScale: 1.0, thirdBaseScale: 1.0, fourthBaseScale: 1.0, fifthBaseScale: 1.0,
                // SPB-2026-05-19 owner: new per-tier Color/Spec scale knobs (parity with primary base)
                secondBaseColorScale: 1.0, thirdBaseColorScale: 1.0, fourthBaseColorScale: 1.0, fifthBaseColorScale: 1.0,
                secondBaseSpecScale: 1.0, thirdBaseSpecScale: 1.0, fourthBaseSpecScale: 1.0, fifthBaseSpecScale: 1.0,
                // Fields whose canonical default is a specific non-zero number
                secondBaseFractalScale: 24, thirdBaseFractalScale: 24,
                fourthBaseFractalScale: 24, fifthBaseFractalScale: 24,
                // Numeric-with-halving default (offsets)
                baseOffsetX: 0.5, baseOffsetY: 0.5,
                patternOffsetX: 0.5, patternOffsetY: 0.5,
                // Boolean flip fields - default false, safe to strip when false
                baseFlipH: false, baseFlipV: false,
                baseColorFitZone: false,
                alignBaseColorWithBase: true,
                patternFlipH: false, patternFlipV: false,
                // String defaults
                intensity: '100',
                baseColor: '#ffffff',
                secondBaseColor: '#ffffff', thirdBaseColor: '#ffffff',
                fourthBaseColor: '#ffffff', fifthBaseColor: '#ffffff',
                baseColorMode: 'source',
                specScaleMode: 'match',
                basePlacement: 'normal', patternPlacement: 'normal',
                secondBaseBlendMode: 'noise', thirdBaseBlendMode: 'noise',
                fourthBaseBlendMode: 'noise', fifthBaseBlendMode: 'noise',
                gradientDirection: 'horizontal',
                pattern: 'none',
            };
            ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'].forEach(function(prefix) {
                Object.keys(_OVERLAY_DNA_DEFAULTS).forEach(function(suffix) {
                    _DNA_DEFAULTS[prefix + suffix] = _OVERLAY_DNA_DEFAULTS[suffix];
                });
            });
        
            var cleaned = {};
            for (var key in dna) {
                var val = dna[key];
                // Universal strips: null/undefined are always absent-equivalent.
                if (val === null || val === undefined) continue;
                // Per-field canonical-default strip.
                if (key in _DNA_DEFAULTS && val === _DNA_DEFAULTS[key]) continue;
                // Keep everything else - painter-set falsy values on non-default-0
                // fields now survive.
                cleaned[key] = val;
            }
            cleaned.v = 1; // always include version
            return cleaned;
        }
        
        /**
         * Copy zone DNA to clipboard as SHOKK:v1:{base64} string.
         */
        function copyZoneDNA(zoneIndex) {
            var dna = _extractZoneDNA(zoneIndex);
            if (!dna) { if (typeof showToast === 'function') showToast('No zone to copy DNA from.'); return; }
            try {
                var json = JSON.stringify(dna);
                var b64 = btoa(unescape(encodeURIComponent(json)));
                var dnaStr = 'SHOKK:v1:' + b64;
                navigator.clipboard.writeText(dnaStr).then(function () {
                    if (typeof showToast === 'function') showToast('Finish DNA copied to clipboard!');
                }).catch(function () {
                    // Fallback: select a temp textarea
                    var ta = document.createElement('textarea');
                    ta.value = dnaStr;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    if (typeof showToast === 'function') showToast('Finish DNA copied (fallback).');
                });
            } catch (e) {
                if (typeof showToast === 'function') showToast('DNA copy failed: ' + e.message);
            }
        }
        
        /**
         * Parse a SHOKK:v1:{base64} DNA string and return the JSON payload, or null on error.
         */
        function _parseDNAString(dnaStr) {
            if (!dnaStr || typeof dnaStr !== 'string') return null;
            dnaStr = dnaStr.trim();
            if (!dnaStr.startsWith('SHOKK:v1:')) return null;
            var b64 = dnaStr.substring(9);
            try {
                var json = decodeURIComponent(escape(atob(b64)));
                var obj = JSON.parse(json);
                if (!obj || typeof obj !== 'object' || obj.v !== 1) return null;
                return obj;
            } catch (e) {
                return null;
            }
        }
        
        /**
         * Apply a DNA payload to a zone - merges DNA properties onto the existing zone.
         */
        function pasteZoneDNA(zoneIndex, dnaStr) {
            var zones = getZones();
            if (zoneIndex < 0 || zoneIndex >= zones.length) {
                if (typeof showToast === 'function') showToast('Invalid zone.');
                return;
            }
            var dna = _parseDNAString(dnaStr);
            if (!dna) {
                if (typeof showToast === 'function') showToast('Invalid DNA string. Expected format: SHOKK:v1:...');
                return;
            }
            pushZoneUndo('Paste DNA');
            var z = zones[zoneIndex];
            // Apply all DNA keys to zone
            var applyKeys = [
                'base', 'finish', 'pattern', 'intensity', 'scale',
                'baseRotation', 'baseOffsetX', 'baseOffsetY', 'baseFlipH', 'baseFlipV', 'basePlacement',
                'baseColorMode', 'baseColor', 'baseColorSource', 'baseColorStrength', 'baseColorScale', 'baseColorRotation', 'baseColorFitZone',
                'baseStrength', 'baseSpecStrength', 'baseScale', 'specRotation', 'specScale', 'specScaleMode', 'patternSpecMult',
                'gradientStops', 'gradientDirection',
                'baseHueOffset', 'baseSaturationAdjust', 'baseBrightnessAdjust',
                'patternOffsetX', 'patternOffsetY', 'patternFlipH', 'patternFlipV', 'patternPlacement',
                'wear',
                'secondBase', 'secondBaseEnabled', 'secondBaseColor', 'secondBaseStrength', 'secondBaseBlendMode',
                'secondBaseFractalScale', 'secondBaseScale', 'secondBaseColorScale', 'secondBaseSpecScale', 'secondBaseColorSource', 'secondBaseColorStrength', 'secondBaseRotation', 'secondBaseSpecRotation', 'secondBaseSpecScaleIndependent',
                'secondBaseHueShift', 'secondBaseSaturation', 'secondBaseBrightness',
                'thirdBase', 'thirdBaseEnabled', 'thirdBaseColor', 'thirdBaseStrength', 'thirdBaseBlendMode',
                'thirdBaseFractalScale', 'thirdBaseScale', 'thirdBaseColorScale', 'thirdBaseSpecScale', 'thirdBaseColorSource',
                'thirdBaseHueShift', 'thirdBaseSaturation', 'thirdBaseBrightness',
                'fourthBase', 'fourthBaseEnabled', 'fourthBaseColor', 'fourthBaseStrength', 'fourthBaseBlendMode',
                'fourthBaseFractalScale', 'fourthBaseScale', 'fourthBaseColorScale', 'fourthBaseSpecScale', 'fourthBaseColorSource',
                'fourthBaseHueShift', 'fourthBaseSaturation', 'fourthBaseBrightness',
                'fifthBase', 'fifthBaseEnabled', 'fifthBaseColor', 'fifthBaseStrength', 'fifthBaseBlendMode',
                'fifthBaseFractalScale', 'fifthBaseScale', 'fifthBaseColorScale', 'fifthBaseSpecScale', 'fifthBaseColorSource',
                'fifthBaseHueShift', 'fifthBaseSaturation', 'fifthBaseBrightness',
            ];
            var overlayApplySuffixes = [
                'Enabled',
                'SpecStrength',
                'Pattern', 'PatternOpacity', 'PatternScale', 'PatternRotation', 'PatternStrength',
                'PatternInvert', 'PatternHarden', 'PatternOffsetX', 'PatternOffsetY',
                'FitZone',
                'PatternHueShift', 'PatternSaturation', 'PatternBrightness',
                'PatternFlipH', 'PatternFlipV',
            ];
            ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'].forEach(function(prefix) {
                overlayApplySuffixes.forEach(function(suffix) {
                    applyKeys.push(prefix + suffix);
                });
            });
            for (var k = 0; k < applyKeys.length; k++) {
                var key = applyKeys[k];
                if (key in dna) {
                    z[key] = dna[key];
                }
            }
            renderZones();
            if (typeof renderZoneDetail === 'function') renderZoneDetail(zoneIndex);
            // FIVE-HOUR SHIFT Win C2: pre-fix this mutated 60+ render-relevant fields
            // (base, finish, pattern, all 4 base overlays' opacity/scale/rotation/etc)
            // but never fired triggerPreviewRender(). Painter pasted DNA, saw the
            // zone card update, but LIVE PREVIEW stayed on the old state until they
            // touched any other control. Same silent-stale class as Win C1 / TWENTY
            // WINS #8 (duplicateZone).
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            if (typeof showToast === 'function') showToast('Finish DNA applied to Zone ' + (zoneIndex + 1) + '!');
        }
        
        /**
         * Handle Paste DNA from the input field.
         */
        function handleDNAPaste(zoneIndex) {
            var inp = document.getElementById('dnaPasteInput_' + zoneIndex);
            if (!inp) return;
            var val = inp.value.trim();
            if (!val) { if (typeof showToast === 'function') showToast('Paste a DNA string first.'); return; }
            pasteZoneDNA(zoneIndex, val);
            inp.value = '';
        }
        
        // ================================================================
        

        global._extractZoneDNA = _extractZoneDNA;
        global.copyZoneDNA = copyZoneDNA;
        global._parseDNAString = _parseDNAString;
        global.pasteZoneDNA = pasteZoneDNA;
        global.handleDNAPaste = handleDNAPaste;
    }

    global.SPBZoneFinishDnaControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
