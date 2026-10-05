// ============================================================
// PAINT-BOOTH-5-API-RENDER.JS - API, render, history gallery
// ============================================================
// Purpose: Finish hover popup, swatch hover popup, ShokkerAPI (server calls),
//          render pipeline (doRender, preview), render history gallery.
// Deps:    paint-booth-1-data.js, paint-booth-2-state-zones.js (zones, build payload).
// Edit:    Server API → ShokkerAPI, baseUrl. Render → doRender, safeDoRender.
//          History → openHistoryGallery, render history state.
// See:     PROJECT_STRUCTURE.md in this folder.
// ============================================================

// BOIL THE OCEAN audit (2026-04-18): single source of truth for spec-pattern
// entry serialization. Three identical _mapSPE bodies were duplicated across
// preview, /render, and export-to-photoshop payload builders. A change to
// one (e.g., a new spec-pattern field) had to be remembered in all three —
// silent payload divergence risk. Now all three callers use this helper.
function _mapSpecPatternEntry(sp) {
    const e = { pattern: sp.pattern, opacity: (sp.opacity ?? 50) / 100 };
    const bm = sp.blendMode || 'normal'; if (bm !== 'normal') e.blend_mode = bm;
    const ch = sp.channels ?? 'MR'; e.channels = ch;
    const rng = sp.range ?? 40; if (rng !== 40) e.range = rng;
    if (sp.params && Object.keys(sp.params).length) e.params = sp.params;
    const ox = sp.offsetX ?? 0.5; if (ox !== 0.5) e.offset_x = ox;
    const oy = sp.offsetY ?? 0.5; if (oy !== 0.5) e.offset_y = oy;
    const sc = sp.scale || 1.0; if (sc !== 1.0) e.scale = sc;
    const rot = sp.rotation || 0; if (rot !== 0) e.rotation = rot;
    const bs = sp.boxSize || 100; if (bs !== 100) e.box_size = bs;
    if (sp.render_version != null) e.render_version = Number(sp.render_version);
    if (sp.seed != null) e.seed = Number(sp.seed);
    if (sp.muted) e.muted = true;
    if (sp.solo) e.solo = true;
    return e;
}
if (typeof window !== 'undefined') window._mapSpecPatternEntry = _mapSpecPatternEntry;

/** Encode region/spatial masks for render — shape (useRegion) + optional green refine can coexist. */

// [ULTRACODE 2026-08-22 M7] ONE offline message. The old copy said "start
// server.py first" in 14 places - a file that does not exist for packaged-app
// buyers, so the most likely failure ended in an instruction nobody could
// follow. Paired with the M6 engine auto-restart, this message is also TRUE.
const SPB_ENGINE_OFFLINE_MSG = 'Paint engine is offline - it restarts automatically in a few seconds. If it stays offline, close and reopen Shokker Paint Booth.';
// SPB-93 tools 2026-09-07, owner: remove lag after edits. Native preview
// serialization took97ms, repeatedly callback-scanning the same4096 mask.
// Share byte-mask presence with the current synchronous render/hash pass.
// Other mask types and early loading keep their original >0 semantics.
function _renderMaskHasPixels(mask) {
    if (!mask) return false;
    if ((mask instanceof Uint8Array || mask instanceof Uint8ClampedArray) &&
        typeof window !== 'undefined' && window.SPBMaskStats?.any) {
        return window.SPBMaskStats.any(mask);
    }
    return mask.some(value => value > 0);
}

function _encodeZoneApplyMasks(zoneObj, z) {
    const pc = typeof document !== 'undefined' ? document.getElementById('paintCanvas') : null;
    if (!pc || typeof encodeRegionMaskRLE !== 'function') return;
    const hasRegion = !!(_renderMaskHasPixels(z.regionMask));
    const hasSpatial = !!(_renderMaskHasPixels(z.spatialMask));
    if (hasRegion && z.useRegion) {
        zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height);
    }
    if (hasSpatial) {
        zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
    }
}
if (typeof window !== 'undefined') window._encodeZoneApplyMasks = _encodeZoneApplyMasks;

function _attachSourceLayerCacheHints(zoneObj, z, srcLayer, w, h) {
    // [SPB-MULTILAYER 2026-08-21] the id doubles as a render-cache key, so it
    // must change when the restricted SET changes - join every id.
    const _slIds = (typeof window !== 'undefined' && typeof window.zoneSourceLayerIds === 'function')
        ? window.zoneSourceLayerIds(z)
        : (z && z.sourceLayer ? [z.sourceLayer] : []);
    if (!zoneObj || !z || !_slIds.length) return;
    zoneObj.source_layer_id = _slIds.map(String).join('+');
    try {
        zoneObj.source_layer_revision = (typeof _layerCompositeRevision !== 'undefined')
            ? (Number(_layerCompositeRevision) || 0)
            : 0;
    } catch (_) {
        zoneObj.source_layer_revision = 0;
    }
    zoneObj.source_layer_size = [Number(w) || 2048, Number(h) || 2048];
    if (srcLayer && Array.isArray(srcLayer.bbox)) {
        zoneObj.source_layer_bbox = srcLayer.bbox.slice(0, 4).map(v => Number(v) || 0);
    }
}
if (typeof window !== 'undefined') window._attachSourceLayerCacheHints = _attachSourceLayerCacheHints;

/** Fit-to-apply-area breaks monolithic finishes (squashes whole-car spec into the box). */
function _zoneShouldFitIntoApplyArea(z) {
    if (!z || !z.fitIntoApplyArea) return false;
    if (z.finish && !z.base) return false;
    return true;
}
if (typeof window !== 'undefined') window._zoneShouldFitIntoApplyArea = _zoneShouldFitIntoApplyArea;

function _spbEscapeRenderHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// 2026-10-04 SHOW MY FILES: the render status banner's button opens Explorer on the folder the last render wrote to,
// with the paint TGA highlighted (server_routes/support_routes.py /api/support/show-files). The offline helper
// (js/spb-support.js) calls the same function. Set by the banner code in the render-results handler.
let _spbLastRenderFiles = null;
async function spbShowRenderFiles(btn) {
    const target = _spbLastRenderFiles;
    const say = (txt) => { if (btn) { btn.textContent = txt; } };
    if (!target) { say('Render first'); return { ok: false, error: 'no render yet' }; }
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/api/support/show-files', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(target)
        });
        const j = await res.json().catch(() => ({ ok: false, error: 'bad reply' }));
        if (j.ok) say('\u{1F4C2} Opened in File Explorer');
        else say('Could not open: ' + (j.error || res.status));
        return j;
    } catch (e) {
        say('Could not open the folder');
        return { ok: false, error: String(e && e.message || e) };
    }
}
if (typeof window !== 'undefined') {
    window.spbShowRenderFiles = spbShowRenderFiles;
    window.spbLastRenderFiles = () => _spbLastRenderFiles;
}

// BOIL THE OCEAN deep core: write the base color/gradient/special branch
// into zoneObj. Three payload builders (preview / render / export) used
// to inline the same 11-line switch — risked silent drift on every change.
// All three now delegate to this single source of truth.
function _applyBaseColorBranch(zoneObj, z, baseMode) {
    if (baseMode === 'solid') {
        const _bHex = (z.baseColor || '#ffffff').toString();
        const hex = _bHex.length >= 7 ? _bHex : '#ffffff';
        zoneObj.base_color = [
            parseInt(hex.slice(1, 3), 16) / 255,
            parseInt(hex.slice(3, 5), 16) / 255,
            parseInt(hex.slice(5, 7), 16) / 255,
        ];
    } else if (baseMode === 'gradient' && z.gradientStops && z.gradientStops.length >= 2) {
        const normalizedStops = (typeof normalizeBaseGradientStopsForPayload === 'function')
            ? normalizeBaseGradientStopsForPayload(z.gradientStops)
            : z.gradientStops;
        if (!normalizedStops || normalizedStops.length < 2) return;
        zoneObj.gradient_stops = normalizedStops;
        zoneObj.gradient_direction = z.gradientDirection || 'horizontal';
    } else if (baseMode === 'special' && z.baseColorSource && z.baseColorSource !== 'undefined') {
        zoneObj.base_color_source = z.baseColorSource;
    }
    if ((baseMode === 'special' || baseMode === 'gradient') && z.baseColorScale != null) {
        zoneObj.base_color_scale = Math.max(0.01, Math.min(5, Number(z.baseColorScale) || 1));
    }
    if ((baseMode === 'special' || baseMode === 'gradient') && z.baseColorRotation != null) {
        zoneObj.base_color_rotation = Math.max(0, Math.min(359, Number(z.baseColorRotation) || 0));
    }
}
if (typeof window !== 'undefined') window._applyBaseColorBranch = _applyBaseColorBranch;

// Same pattern: custom_intensity assembly was duplicated 3x as a one-liner.
// Single source of truth; null-guards live here too.
function _applyCustomIntensity(zoneObj, z) {
    if (z.customSpec != null) {
        zoneObj.custom_intensity = {
            spec: z.customSpec,
            paint: z.customPaint,
            bright: z.customBright,
        };
    }
}
if (typeof window !== 'undefined') window._applyCustomIntensity = _applyCustomIntensity;

function _zoneShouldPreserveScopedBrushExactColorPayload(z) {
    if (typeof window !== 'undefined' && typeof window._zoneShouldPreserveScopedBrushExactColor === 'function') {
        return !!window._zoneShouldPreserveScopedBrushExactColor(z);
    }
    if (_zoneHasActiveBaseOverlay(z)) return false;
    return !!(
        z &&
        z._scopedBrushAutoBaseColor &&
        String(z.baseColorMode || 'source').toLowerCase() === 'solid' &&
        Array.isArray(z.spatialMask) &&
        z.spatialMask.some(v => v === 1)
    );
}

function _applyBlendBaseOverlay(zoneObj, z) {
    if (_zoneShouldPreserveScopedBrushExactColorPayload(z)) return;
    if (z.blendBase && z.blendBase !== 'undefined' && z.blendBase !== 'none' && z.blendBase !== 'null') {
        zoneObj.blend_base = z.blendBase;
        zoneObj.blend_dir = z.blendDir || 'horizontal';
        zoneObj.blend_amount = (z.blendAmount ?? 50) / 100;
    }
}
if (typeof window !== 'undefined') window._applyBlendBaseOverlay = _applyBlendBaseOverlay;

// BOIL THE OCEAN deep core: pattern stack mapper. The same .filter+.map
// chain was inlined in three payload builders. Centralizing prevents
// silent drift if a new field is added (e.g., per-layer flip flags).
function _mapPatternStackEntry(l) {
    return {
        id: l.id,
        opacity: (l.opacity ?? 100) / 100,
        scale: l.scale || 1.0,
        rotation: l.rotation || 0,
        blend_mode: l.blendMode || 'normal',
        hue_shift: Number(l.hueShift ?? 0),
        saturation: Number(l.saturation ?? 0),
        spec_opacity: Math.max(0, Math.min(100, Number(l.specOpacity ?? 0))) / 100,
    };
}
function _mapPatternStack(stackArray) {
    if (!stackArray || !stackArray.length) return null;
    const filtered = stackArray.filter(l => l.id && l.id !== 'none');
    if (!filtered.length) return null;
    return filtered.map(_mapPatternStackEntry);
}
if (typeof window !== 'undefined') {
    window._mapPatternStackEntry = _mapPatternStackEntry;
    window._mapPatternStack = _mapPatternStack;
}

function _normalizeExtraBaseOverlayPatternValue(value) {
    if (value === '') return '';
    if (value == null) return '';
    const raw = String(value).trim();
    const normalized = raw.toLowerCase().replace(/[\s-]+/g, '_');
    if (
        normalized === 'none' ||
        normalized === '_none_' ||
        normalized === '__none__' ||
        normalized === 'none_(base_only)' ||
        normalized === 'none_(independent)' ||
        normalized === 'base_only'
    ) {
        return '__none__';
    }
    return raw;
}
if (typeof window !== 'undefined') window._normalizeExtraBaseOverlayPatternValue = _normalizeExtraBaseOverlayPatternValue;

function _extraBaseOverlayInheritsPrimaryPattern(z, reactPattern) {
    if (!z || !z.pattern || z.pattern === 'none') return false;
    const normalized = _normalizeExtraBaseOverlayPatternValue(reactPattern);
    if (normalized === '') return true;
    if (normalized === '__none__') return false;
    return String(reactPattern || '') === String(z.pattern || '');
}

function _extraBaseOverlayBlendModeRequiresPattern(mode) {
    const normalized = String(mode || '').trim().toLowerCase().replace(/[\s_]+/g, '-');
    return [
        'pattern',
        'pattern-reactive',
        'pattern-vivid',
        'pattern-pop',
        'pattern-edges',
        'pattern-peaks',
        'pattern-contour',
        'pattern-screen',
        'pattern-stream',
        'pattern-threshold',
    ].includes(normalized);
}

function _extraBaseOverlayNumberOrInherited(z, prefix, suffix, defaultValue, primaryKey, minValue, maxValue, reactPattern) {
    const raw = z[prefix + suffix];
    let value = Number(raw ?? defaultValue);
    if (
        _extraBaseOverlayInheritsPrimaryPattern(z, reactPattern) &&
        (raw == null || Math.abs(Number(raw) - defaultValue) < 1e-9) &&
        z[primaryKey] != null
    ) {
        value = Number(z[primaryKey]);
    }
    if (!Number.isFinite(value)) value = defaultValue;
    return Math.max(minValue, Math.min(maxValue, value));
}
if (typeof window !== 'undefined') {
    window._extraBaseOverlayInheritsPrimaryPattern = _extraBaseOverlayInheritsPrimaryPattern;
    window._extraBaseOverlayBlendModeRequiresPattern = _extraBaseOverlayBlendModeRequiresPattern;
    window._extraBaseOverlayNumberOrInherited = _extraBaseOverlayNumberOrInherited;
}

// BOIL THE OCEAN deep core (drift hunt #2): the second/third/fourth/fifth base
// overlay payload blocks were inlined 4x in EACH of 3 builders = 12 near-clones.
// Audit caught real silent drift between them:
//   - Builder #3 used `if (z.X != null)` guards on pattern_opacity/scale/rotation/
//     strength while #1/#2 always emit clamped defaults — preview/render and
//     export sent DIFFERENT payloads for any zone whose UI hadn't touched those
//     sliders (server-side default differs from JS-side default).
//   - Builders #1/#2 silently DROPPED fourth/fifth base pattern_invert and
//     pattern_harden fields, while #3 emitted them. WYSIWYG broken: painter
//     sees pattern non-inverted in preview, then export inverts it.
// Single helper now owns one canonical contract: always-emit, always-clamped,
// always-defaulted, all four overlay layers, all three builders.
function _applyExtraBaseOverlay(zoneObj, z, prefix, key) {
    // prefix: 'secondBase' | 'thirdBase' | 'fourthBase' | 'fifthBase'
    // key:    'second_base' | 'third_base' | 'fourth_base' | 'fifth_base'
    if (z[prefix + 'Enabled'] === false) return;
    const baseId = z[prefix];
    let colorSrc = z[prefix + 'ColorSource'];
    if (colorSrc && typeof colorSrc === 'string' && !colorSrc.includes(':')) {
        const ft = (typeof _pickerCatalogItemType === 'function') ? _pickerCatalogItemType(colorSrc) : null;
        if (ft === 'monolithic') colorSrc = 'mono:' + colorSrc;
    }
    const strength = z[prefix + 'Strength'] || 0;
    // [SPB-OVERLAY-PARITY-2 2026-08-20] paint 0 + spec >0 is a spec-only overlay
    const specStrengthGate = z[prefix + 'SpecStrength'] ?? 1;
    if (!(baseId || colorSrc) || (strength <= 0 && specStrengthGate <= 0)) return;
    const isSpecialBase = typeof baseId === 'string' && baseId.startsWith('mono:');
    const effectiveColorSrc = (!colorSrc && isSpecialBase) ? 'overlay' : colorSrc;
    const _hexRaw = (z[prefix + 'Color'] || '#ffffff').toString();
    const hex = _hexRaw.length >= 7 ? _hexRaw : '#ffffff';
    if (baseId && baseId !== 'undefined') zoneObj[key] = baseId;
    zoneObj[key + '_color'] = [
        parseInt(hex.slice(1, 3), 16) / 255,
        parseInt(hex.slice(3, 5), 16) / 255,
        parseInt(hex.slice(5, 7), 16) / 255,
    ];
    zoneObj[key + '_strength'] = strength;
    zoneObj[key + '_spec_strength'] = z[prefix + 'SpecStrength'] ?? 1;
    if (effectiveColorSrc && effectiveColorSrc !== 'undefined') zoneObj[key + '_color_source'] = effectiveColorSrc;
    const blendMode = z[prefix + 'BlendMode'] || 'noise';
    zoneObj[key + '_blend_mode'] = blendMode;
    zoneObj[key + '_noise_scale'] = Number(z[prefix + 'NoiseScale'] ?? z[prefix + 'FractalScale'] ?? 24);
    zoneObj[key + '_scale'] = Math.max(0.01, Math.min(5, Number(z[prefix + 'Scale']) || 1));
    // SPB-2026-05-19 owner: new per-tier Color/Spec scale knobs (parity with primary base)
    {
        const _csz = Math.max(0.01, Math.min(5, Number(z[prefix + 'ColorScale']) || 1));
        const _ssz = Math.max(0.01, Math.min(5, Number(z[prefix + 'SpecScale']) || 1));
        zoneObj[key + '_color_scale'] = _csz;
        zoneObj[key + '_spec_scale'] = _ssz;
        // [SPB-OVERLAY-PARITY-2 2026-08-20] rotation / spec rotation / color strength
        zoneObj[key + '_rotation'] = Number(z[prefix + 'Rotation']) || 0;
        zoneObj[key + '_spec_rotation'] = Number(z[prefix + 'SpecRotation']) || 0;
        zoneObj[key + '_color_strength'] = Math.max(0, Math.min(1, (z[prefix + 'ColorStrength'] ?? 1)));
    }
    let reactPattern = _normalizeExtraBaseOverlayPatternValue(z[prefix + 'Pattern']);
    if (
        reactPattern === '__none__' &&
        _extraBaseOverlayBlendModeRequiresPattern(blendMode) &&
        z.pattern &&
        z.pattern !== 'none'
    ) {
        reactPattern = '';
    }
    zoneObj[key + '_pattern'] = reactPattern;
    zoneObj[key + '_pattern_opacity'] = _extraBaseOverlayNumberOrInherited(z, prefix, 'PatternOpacity', 100, 'patternOpacity', 0, 100, reactPattern) / 100;
    zoneObj[key + '_pattern_scale'] = _extraBaseOverlayNumberOrInherited(z, prefix, 'PatternScale', 1, 'scale', 0.1, 4, reactPattern);
    zoneObj[key + '_pattern_rotation'] = _extraBaseOverlayNumberOrInherited(z, prefix, 'PatternRotation', 0, 'rotation', -3600, 3600, reactPattern);
    zoneObj[key + '_pattern_strength'] = Math.max(0, Math.min(2, Number(z[prefix + 'PatternStrength'] ?? 1)));
    if (z[prefix + 'PatternInvert'] != null) zoneObj[key + '_pattern_invert'] = !!z[prefix + 'PatternInvert'];
    if (z[prefix + 'PatternHarden'] != null) zoneObj[key + '_pattern_harden'] = !!z[prefix + 'PatternHarden'];
    zoneObj[key + '_pattern_offset_x'] = _extraBaseOverlayNumberOrInherited(z, prefix, 'PatternOffsetX', 0.5, 'patternOffsetX', 0, 1, reactPattern);
    zoneObj[key + '_pattern_offset_y'] = _extraBaseOverlayNumberOrInherited(z, prefix, 'PatternOffsetY', 0.5, 'patternOffsetY', 0, 1, reactPattern);
    // WIN #19 (Hawk audit): manualPlacementFlipH/V writes secondBasePatternFlipH/V
    // (and Win #19 extension also writes thirdBase/fourthBase/fifthBase variants)
    // but pre-fix none of them were ever serialized to the engine. Painter toggled
    // a 2nd-base flip and saw no change in render. Now mirrors the primary
    // pattern_flip_h/v emit pattern.
    if (z[prefix + 'PatternFlipH'] || (_extraBaseOverlayInheritsPrimaryPattern(z, reactPattern) && z.patternFlipH && z[prefix + 'PatternFlipH'] == null)) zoneObj[key + '_pattern_flip_h'] = true;
    if (z[prefix + 'PatternFlipV'] || (_extraBaseOverlayInheritsPrimaryPattern(z, reactPattern) && z.patternFlipV && z[prefix + 'PatternFlipV'] == null)) zoneObj[key + '_pattern_flip_v'] = true;
    if (z[prefix + 'FitZone']) zoneObj[key + '_fit_zone'] = true;
    // SPB-2026-05-28 owner: always emit overlay-tier HSB when this overlay is active.
    // Truthy guards silently dropped zero resets and let preview cache serve stale paint.
    zoneObj[key + '_hue_shift'] = Number(z[prefix + 'HueShift'] ?? 0);
    zoneObj[key + '_saturation'] = Number(z[prefix + 'Saturation'] ?? 0);
    zoneObj[key + '_brightness'] = Number(z[prefix + 'Brightness'] ?? 0);
    // Pattern hue/sat/bright currently exists only for second_base in source data,
    // but the helper emits it uniformly when present so future symmetry is free.
    if (z[prefix + 'PatternHueShift'] != null) zoneObj[key + '_pattern_hue_shift'] = Number(z[prefix + 'PatternHueShift'] ?? 0);
    if (z[prefix + 'PatternSaturation'] != null) zoneObj[key + '_pattern_saturation'] = Number(z[prefix + 'PatternSaturation'] ?? 0);
    if (z[prefix + 'PatternBrightness'] != null) zoneObj[key + '_pattern_brightness'] = Number(z[prefix + 'PatternBrightness'] ?? 0);
}
function _applyAllExtraBaseOverlays(zoneObj, z) {
    if (_zoneShouldPreserveScopedBrushExactColorPayload(z)) return;
    _applyExtraBaseOverlay(zoneObj, z, 'secondBase', 'second_base');
    _applyExtraBaseOverlay(zoneObj, z, 'thirdBase', 'third_base');
    _applyExtraBaseOverlay(zoneObj, z, 'fourthBase', 'fourth_base');
    _applyExtraBaseOverlay(zoneObj, z, 'fifthBase', 'fifth_base');
}
if (typeof window !== 'undefined') {
    window._applyExtraBaseOverlay = _applyExtraBaseOverlay;
    window._applyAllExtraBaseOverlays = _applyAllExtraBaseOverlays;
}

function _zoneHasActiveBaseOverlay(z) {
    if (!z) return false;
    const prefixes = ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'];
    return prefixes.some(prefix => {
        if (z[prefix + 'Enabled'] === false) return false;
        const strength = Number(z[prefix + 'Strength'] ?? 0);
        const baseId = z[prefix];
        const colorSrc = z[prefix + 'ColorSource'];
        const hasBaseId = typeof baseId === 'string' && baseId !== '' && baseId !== 'undefined' && baseId !== 'none';
        const hasColorSrc = typeof colorSrc === 'string' && colorSrc !== '' && colorSrc !== 'undefined' && colorSrc !== 'none';
        return strength > 0 && (hasBaseId || hasColorSrc);
    });
}

// SPB-EASY-WHOLE-MIX-20260721: first-class material-only Whole Car plan.
// Keep explicit registry identity all the way to Python; raw ids are not safe
// because a base and monolithic may intentionally share one id.
function _normalizeZoneMaterialStack(z) {
    if (!z) return null;
    const raw = Array.isArray(z.materialStack) ? z.materialStack
        : (Array.isArray(z.material_stack) ? z.material_stack : null);
    if (!raw || raw.length === 0) return null;
    if (raw.length > 4) throw new Error('Whole Car material mix supports at most four finishes.');
    const rows = raw.map((entry, index) => {
        if (!entry || typeof entry !== 'object') throw new Error(`Whole Car material ${index + 1} is invalid.`);
        const id = String(entry.id || entry.finish_id || '').trim();
        const registryType = String(entry.registryType || entry.registry_type || entry.type || '').trim().toLowerCase();
        const weight = Number(entry.weight);
        if (!id) throw new Error(`Whole Car material ${index + 1} is missing its finish id.`);
        if (registryType !== 'base' && registryType !== 'monolithic') {
            throw new Error(`Whole Car material '${id}' is missing its exact base/monolithic type.`);
        }
        if (!Number.isFinite(weight) || weight <= 0) throw new Error(`Whole Car material '${id}' needs a positive mix share.`);
        let known = true;
        try {
            if (registryType === 'base' && typeof BASES_BY_ID !== 'undefined') known = !!BASES_BY_ID[id];
            else if (registryType === 'monolithic' && typeof MONOLITHICS_BY_ID !== 'undefined') known = !!MONOLITHICS_BY_ID[id];
        } catch (_) {}
        if (!known) throw new Error(`Unknown ${registryType} Whole Car material '${id}'.`);
        return { id, registry_type: registryType, weight };
    });
    const total = rows.reduce((sum, row) => sum + row.weight, 0);
    return rows.map(row => ({ id: row.id, registry_type: row.registry_type, weight: row.weight / total }));
}

function _zoneHasMaterialStack(z) {
    try { return !!_normalizeZoneMaterialStack(z); }
    catch (error) {
        try { console.error('[SPB][material_stack]', error.message || error); } catch (_) {}
        return false;
    }
}

function _applyZoneMaterialStack(zoneObj, z) {
    const stack = _normalizeZoneMaterialStack(z);
    if (!stack) return null;
    zoneObj.material_stack = stack;
    zoneObj.material_stack_mode = 'auto_trace';
    const raw = Array.isArray(z.materialStack) ? z.materialStack : z.material_stack;
    const inferredAmount = Math.min(1, raw.reduce((sum, entry) => sum + Math.max(0, Number(entry && entry.weight) || 0), 0) / 100);
    const requestedAmount = Number(z.materialStackAmount ?? z.material_stack_amount ?? inferredAmount);
    zoneObj.material_stack_amount = Math.max(0, Math.min(1, Number.isFinite(requestedAmount) ? requestedAmount : inferredAmount));
    const scale = Number(z.materialScale ?? z.material_scale ?? 1);
    zoneObj.material_scale = Math.max(0.25, Math.min(1, Number.isFinite(scale) ? scale : 1));
    return stack;
}

function _zoneNeedsNeutralBaseAnchor(z) {
    // 2026-07-22 owner beta blocker: Easy Spec Sculpt's By Color picker must
    // show an explicitly selected replacement color before a finish is chosen.
    // Reuse the real render pipeline with a temporary neutral anchor; Save still
    // requires a real base/finish and Easy clears this marker then. M7 N/A.
    return !!(z && !z.base && !z.finish && (_zoneHasActiveBaseOverlay(z) || z._easyPendingColorPreview === true));
}

function _zoneHasImportedSpecSource(z) {
    return !!(z && typeof z.zoneSpecMapPath === 'string' && z.zoneSpecMapPath.trim());
}

function _zoneSpecSourceStrength(z) {
    const pct = Number(z && z.zoneSpecMapStrength != null ? z.zoneSpecMapStrength : 100);
    return Math.max(0, Math.min(1, (Number.isFinite(pct) ? pct : 100) / 100));
}

function _applyZoneSpecSource(zoneObj, z) {
    if (!_zoneHasImportedSpecSource(z)) return;
    zoneObj.zone_spec_map = z.zoneSpecMapPath.trim();
    zoneObj.zone_spec_map_strength = _zoneSpecSourceStrength(z);
}

function _zoneHasRenderableMaterial(z) {
    return !!(z && (z.base || z.finish || _zoneNeedsNeutralBaseAnchor(z) || _zoneHasImportedSpecSource(z) || _zoneHasMaterialStack(z)));
}

function _isSuppressedLegacyZone(z, index) {
    if (typeof _isZone9MatteCarbonZombie === 'function' && _isZone9MatteCarbonZombie(z, index)) return true;
    return false;
}

if (typeof window !== 'undefined') {
    window._zoneHasActiveBaseOverlay = _zoneHasActiveBaseOverlay;
    window._normalizeZoneMaterialStackForServer = _normalizeZoneMaterialStack;
    window._zoneHasMaterialStack = _zoneHasMaterialStack;
    window._applyZoneMaterialStack = _applyZoneMaterialStack;
    window._zoneNeedsNeutralBaseAnchor = _zoneNeedsNeutralBaseAnchor;
    window._zoneHasImportedSpecSource = _zoneHasImportedSpecSource;
    window._zoneSpecSourceStrength = _zoneSpecSourceStrength;
    window._applyZoneSpecSource = _applyZoneSpecSource;
    window._zoneHasRenderableMaterial = _zoneHasRenderableMaterial;
    window._isSuppressedLegacyZone = _isSuppressedLegacyZone;
}

// BOIL THE OCEAN deep core (drift hunt #3): finish_colors lookup was inlined
// in three builders. The PS-export builder had a STALE regex missing the
// `mc_` (multi-color) prefix. Painter's MC finish rendered correctly via
// preview/render but exported WITHOUT finish_colors -- Photoshop side then
// had no idea what colors to use. Single helper enforces parity.
const FINISH_COLORS_PROCEDURAL_RE = /^(grad_|gradm_|grad3_|ghostg_|mc_)/;
function _resolveFinishColors(finishId) {
    if (!finishId) return null;
    const monos = (typeof MONOLITHICS !== 'undefined') ? MONOLITHICS : null;
    const mono = monos ? monos.find(m => m.id === finishId) : null;
    if (mono) {
        return {
            c1: mono.swatch || null,
            c2: mono.swatch2 || null,
            c3: mono.swatch3 || null,
            ghost: mono.ghostPattern || null,
        };
    }
    if (FINISH_COLORS_PROCEDURAL_RE.test(finishId) && typeof getFinishColorsForId === 'function') {
        return getFinishColorsForId(finishId);
    }
    return null;
}
if (typeof window !== 'undefined') {
    window._resolveFinishColors = _resolveFinishColors;
    window.FINISH_COLORS_PROCEDURAL_RE = FINISH_COLORS_PROCEDURAL_RE;
}

// BOIL THE OCEAN deep core (drift hunt #4): the "base color mode" header
// (mode + strength + fit_zone + hue/sat/bright tweaks + branch dispatch)
// was inlined IDENTICALLY in three builders. 7 lines × 3 = 21 lines that
// had to stay in sync forever; one forgotten edit would silently change
// only one render path. Single helper now owns the contract.
function _applyBaseColorMode(zoneObj, z) {
    if (!_zoneHasRenderableMaterial(z)) return;
    const baseMode = (z.baseColorMode || 'source');
    zoneObj.base_color_mode = baseMode;
    // SPB base-mode hotfix 2026-09-09: the UI's displayed mode is authoritative.
    // Untouched Everything Else and loaded source-mode zones are spec-only too.
    zoneObj.base_color_explicit = true;
    zoneObj.base_color_strength = Math.max(0, Math.min(1, Number(z.baseColorStrength ?? 1)));
    // [SPB COLOR LAB 2026-08-27] presence of base_color_depth switches the engine to the
    // DEPTH/FLIP/UNDERGLOW pipeline; absent = legacy crossfade (old saves render unchanged)
    if (z.baseColorDepth != null) {
        zoneObj.base_color_depth = Math.max(0, Math.min(1, Number(z.baseColorDepth)));
        zoneObj.base_color_flip = Math.max(0, Math.min(355, Number(z.baseColorFlip || 0)));
        zoneObj.base_color_underglow = Math.max(0, Math.min(1, Number(z.baseColorUnderglow || 0)));
    }
    if (z.baseColorFitZone || _zoneShouldFitIntoApplyArea(z)) zoneObj.base_color_fit_zone = true;
    if (z.baseHueOffset) zoneObj.base_hue_offset = Number(z.baseHueOffset);
    if (z.baseSaturationAdjust) zoneObj.base_saturation_adjust = Number(z.baseSaturationAdjust);
    if (z.baseBrightnessAdjust) zoneObj.base_brightness_adjust = Number(z.baseBrightnessAdjust);
    _applyBaseColorBranch(zoneObj, z, baseMode);
}
if (typeof window !== 'undefined') window._applyBaseColorMode = _applyBaseColorMode;

// BOIL THE OCEAN deep core (drift hunt #5): the 5-tier spec_pattern_stack
// loop (5 src/dst tuples + map _mapSPE) was inlined in three builders. If
// a 6th overlay tier ever lands, the tuple list must be edited in 3
// places. Single helper now owns the contract.
const SPEC_PATTERN_STACK_TIERS = [
    ['specPatternStack', 'spec_pattern_stack'],
    ['overlaySpecPatternStack', 'overlay_spec_pattern_stack'],
    ['thirdOverlaySpecPatternStack', 'third_overlay_spec_pattern_stack'],
    ['fourthOverlaySpecPatternStack', 'fourth_overlay_spec_pattern_stack'],
    ['fifthOverlaySpecPatternStack', 'fifth_overlay_spec_pattern_stack'],
];
function _applyAllSpecPatternStacks(zoneObj, z) {
    for (const [src, dst] of SPEC_PATTERN_STACK_TIERS) {
        if (z[src] && z[src].length > 0) {
            const activeStack = z[src]
                .map(_mapSpecPatternEntry)
                .filter(e => {
                    const pattern = String(e.pattern || '').trim().toLowerCase();
                    return pattern && !['none', 'null', 'undefined', '__none__', '_none_'].includes(pattern) && Number(e.opacity ?? 0.5) > 0.001;
                });
            if (activeStack.length > 0) zoneObj[dst] = activeStack;
        }
    }
}
if (typeof window !== 'undefined') {
    window._applyAllSpecPatternStacks = _applyAllSpecPatternStacks;
    window.SPEC_PATTERN_STACK_TIERS = SPEC_PATTERN_STACK_TIERS;
}

function _applySpecLightingMask(zoneObj, z) {
    if (!zoneObj || !z || z.specLightingMask == null || z.specLightingMask === '') return;
    const alpha = Number(z.specLightingMask);
    if (!Number.isFinite(alpha)) return;
    zoneObj.spec_lighting_mask = Math.max(0, Math.min(255, Math.round(alpha)));
}
if (typeof window !== 'undefined') window._applySpecLightingMask = _applySpecLightingMask;

function _applySpecMaterialOverride(zoneObj, z) {
    const sample = z && z.specMaterialOverride;
    if (!zoneObj || !sample || typeof sample !== 'object') return;
    const values = {};
    for (const key of ['m', 'r', 'cc', 'a']) {
        const value = Number(sample[key]);
        if (!Number.isFinite(value)) return;
        values[key] = Math.max(0, Math.min(255, Math.round(value)));
    }
    zoneObj.spec_material_override = values;
}
if (typeof window !== 'undefined') window._applySpecMaterialOverride = _applySpecMaterialOverride;

function _applySpecMaterialRemap(zoneObj, z) {
    const remap = z && z.specMaterialRemap;
    if (!zoneObj || !remap || typeof remap !== 'object') return;
    const normalized = {};
    for (const key of ['m', 'r', 'cc']) {
        const range = remap[key];
        if (!range || typeof range !== 'object') return;
        const low = Number(range.low);
        const high = Number(range.high);
        if (!Number.isFinite(low) || !Number.isFinite(high) || low > high) return;
        normalized[key] = {
            low: Math.max(0, Math.min(255, Math.round(low))),
            high: Math.max(0, Math.min(255, Math.round(high))),
        };
    }
    zoneObj.spec_material_remap = normalized;
}
if (typeof window !== 'undefined') window._applySpecMaterialRemap = _applySpecMaterialRemap;

// BOIL THE OCEAN deep core: fleet render, season render, and the main
// buildServerZonesForRender bridge were still carrying near-identical
// finish-stack payload logic. Any future tweak to pattern opacity, offsets,
// finish colors, spec stacks, or base placement had three chances to drift.
// This helper centralizes that core while preserving the "compact defaults"
// behavior used by buildServerZonesForRender for lighter payloads.
function _applyPatternMaterialControls(zoneObj, z) {
    // Owner 2026-09-08: active builders bypass the extracted render core.
    // Keep preview, normal render, Fleet and Season on the same pattern contract.
    zoneObj.pattern_paint_mode = z.patternPaintMode === 'blend' ? 'blend' : 'overlay';
    zoneObj.pattern_hue_shift = Number(z.patternHueShift ?? 0);
    zoneObj.pattern_saturation = Number(z.patternSaturation ?? 0);
    zoneObj.pattern_spec_opacity = Math.max(0, Math.min(100, Number(z.patternSpecOpacity ?? 0))) / 100;
}
function _applyZoneRenderCore(zoneObj, z, options) {
    _applyPatternMaterialControls(zoneObj, z);
    const compactDefaults = !!(options && options.compactDefaults);
    const hasPattern = !!(z.pattern && z.pattern !== 'none');
    const primaryBaseId = z.base || (_zoneNeedsNeutralBaseAnchor(z) ? 'gloss' : null);
    const hasPrimaryBase = !!primaryBaseId;
    const hasImportedSpecSource = _zoneHasImportedSpecSource(z);
    const hasMaterialStack = _zoneHasMaterialStack(z);
    const hasRenderableMaterial = hasPrimaryBase || !!z.finish || hasImportedSpecSource || hasMaterialStack;

    _applyCustomIntensity(zoneObj, z);
    if (hasMaterialStack) _applyZoneMaterialStack(zoneObj, z);
    if ((hasPrimaryBase && hasPattern) || (z.finish && hasPattern)) {
        zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
    }

    if (hasPrimaryBase) {
        // Overlay-only zones still need a neutral primary surface so the
        // engine has a stable anchor for tint/spec compositing. Without this,
        // the UI can show an active Base Overlay Layer while the payload
        // silently drops the zone as "no base/finish", making it look like
        // source-layer restriction or Remaining selection found zero pixels.
        zoneObj.base = primaryBaseId;
        zoneObj.pattern = z.pattern || 'none';
        if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
        if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation;
        const _po = (z.patternOpacity ?? 100) / 100;
        if (!compactDefaults || _po !== 1.0) zoneObj.pattern_opacity = _po;
        const _ps = _mapPatternStack(z.patternStack);
        if (_ps) zoneObj.pattern_stack = _ps;
    } else if (z.finish) {
        zoneObj.finish = z.finish;
        const _finishRot = z.baseRotation || z.rotation || 0;
        if (_finishRot && _finishRot !== 0) zoneObj.rotation = _finishRot;
        const _fc = _resolveFinishColors(z.finish);
        if (_fc) zoneObj.finish_colors = _fc;
        if (hasPattern) {
            zoneObj.pattern = z.pattern;
            if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
            zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
        }
        const _ps = _mapPatternStack(z.patternStack);
        if (_ps) zoneObj.pattern_stack = _ps;
    }

    _applyZoneSpecSource(zoneObj, z);
    if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
    if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
    if (z.baseSpecStrength != null) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
    if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
    if (z.specShiftR || z.specShiftG || z.specShiftB) zoneObj.spec_channel_shift = [Number(z.specShiftR) || 0, Number(z.specShiftG) || 0, Number(z.specShiftB) || 0];
    _applySpecMaterialRemap(zoneObj, z);
    _applySpecMaterialOverride(zoneObj, z);
    _applySpecLightingMask(zoneObj, z);
    _applyBaseColorMode(zoneObj, z);

    if (hasPrimaryBase || (z.finish && hasPattern)) {
        const _psm = Number(z.patternSpecMult ?? 1);
        if (!compactDefaults || _psm !== 1) zoneObj.pattern_spec_mult = _psm;
    }
    if (z.patternStrengthMapEnabled && z.patternStrengthMap && typeof encodeStrengthMapRLE === 'function') {
        zoneObj.pattern_strength_map = encodeStrengthMapRLE(z.patternStrengthMap);
    }
    if (hasPrimaryBase || (z.finish && hasPattern)) {
        const _pox = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5)));
        const _poy = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5)));
        if (!compactDefaults || _pox !== 0.5) zoneObj.pattern_offset_x = _pox;
        if (!compactDefaults || _poy !== 0.5) zoneObj.pattern_offset_y = _poy;
        if (!compactDefaults || z.patternFlipH) zoneObj.pattern_flip_h = !!z.patternFlipH;
        if (!compactDefaults || z.patternFlipV) zoneObj.pattern_flip_v = !!z.patternFlipV;
    }
    if (z.patternPlacement === 'fit' || z.patternFitZone || _zoneShouldFitIntoApplyArea(z)) zoneObj.pattern_fit_zone = true;
    if (z.hardEdge !== false) zoneObj.hard_edge = true;  // [SPB 2026-06-02 owner] hard edge is the DEFAULT; only an explicit uncheck (false) sends soft
    if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;

    if (hasRenderableMaterial) {
        const _box = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5)));
        const _boy = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5)));
        const _brot = Number(z.baseRotation ?? 0);
        if (!compactDefaults || _box !== 0.5) zoneObj.base_offset_x = _box;
        if (!compactDefaults || _boy !== 0.5) zoneObj.base_offset_y = _boy;
        if (!compactDefaults || _brot !== 0) zoneObj.base_rotation = _brot;
        if (!compactDefaults || z.baseFlipH) zoneObj.base_flip_h = !!z.baseFlipH;
        if (!compactDefaults || z.baseFlipV) zoneObj.base_flip_v = !!z.baseFlipV;
    }

    const _specRot = Number(z.specRotation ?? 0);
    const _specScale = (window._spbResolveSpecScale ? window._spbResolveSpecScale(z) : Number(z.specScale ?? z.baseScale ?? 1));
    if (_specRot !== 0) zoneObj.spec_rotation = _specRot;
    // [spb-indspec-20260803a] independent spec must SEND 1.0 explicitly: the engine treats a MISSING spec_scale as follow-base, so omitting the 1.0 sentinel silently re-linked spec to base (owner: base 0.10x + spec 1.00x did nothing).
    if (_specScale !== 1 || (window._spbSpecIndependent && window._spbSpecIndependent(z))) zoneObj.spec_scale = _specScale;

    if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
    _applyAllSpecPatternStacks(zoneObj, z);
    if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
    _applyBlendBaseOverlay(zoneObj, z);
    if (z.usePaintReactive && z.paintReactiveColor) {
        const _pc = z.paintReactiveColor;
        zoneObj.paint_color = [
            parseInt(_pc.slice(1, 3), 16) / 255,
            parseInt(_pc.slice(3, 5), 16) / 255,
            parseInt(_pc.slice(5, 7), 16) / 255,
        ];
    }
    _applyAllExtraBaseOverlays(zoneObj, z);
}
if (typeof window !== 'undefined') window._applyZoneRenderCore = _applyZoneRenderCore;

// ===== NAMED CONSTANTS (replaces magic numbers) ===== // [41-45]
const API_TIMEOUT_STATUS_MS = 8000;       // Timeout for /status health checks.
// [2026-06-12 preview-deadlock fix] Was 2000ms: a CPU-saturated server (boot
// swatch warm re-bake storm after engine changes) missed the 2s window, the
// API got marked offline, and doPreviewRender silently no-opped FOREVER (the
// painter saw a dead live preview that only RENDER could revive).
const API_TIMEOUT_PORT_SCAN_MS = 800;     // Timeout for port-scan fallback
const API_TIMEOUT_RENDER_MS = 300000;     // 5 min max for render requests
const API_TIMEOUT_GENERAL_MS = 15000;     // General API call timeout (config, cleanup, etc.)
const POLL_INITIAL_INTERVAL_MS = 10000;   // Status polling start interval
const POLL_MAX_INTERVAL_MS = 120000;      // Status polling max interval (2 min)
const POLL_BACKOFF_FACTOR = 1.5;          // Status polling backoff multiplier
const RENDER_PROGRESS_POLL_MS = 2000;     // Render progress poll interval
const RENDER_TERMINATE_DELAY_MS = 3000;   // Delay before showing TERMINATE button
const RENDER_RESET_DELAY_MS = 1500;       // Delay before resetting render button
const FINISH_POPUP_HIDE_DELAY_MS = 100;   // Delay before hiding finish popup
const SWATCH_POPUP_HIDE_DELAY_MS = 120;   // Delay before hiding swatch popup
const RENDER_ESTIMATE_PER_ZONE_S = 4;     // Estimated seconds per zone for time estimates
const RENDER_ESTIMATE_BASE_S = 8;         // Base overhead for any render
const MAX_RETRY_COUNT = 2;                // Max retry attempts for failed requests
// [IMP-1] Added: timeout tiers for different endpoint categories
const API_TIMEOUT_LIGHT_MS = 5000;        // Light reads (/health, /version, etc.)
const API_TIMEOUT_HEAVY_MS = 60000;       // Heavy uploads (TGA, big PSDs)
// [IMP-2] Retry with exponential backoff defaults
const RETRY_BASE_DELAY_MS = 400;          // First retry waits ~400ms
const RETRY_MAX_DELAY_MS = 8000;          // Cap retry delay
// [IMP-3] Concurrent request limiter
const MAX_CONCURRENT_FETCHES = 3;
// [IMP-4] Stale request detection — abort idle requests after this many ms with no progress
const STALE_REQUEST_MS = 60000;
// [IMP-5] GZip threshold (bytes) — only compress payloads above this
const GZIP_THRESHOLD_BYTES = 64 * 1024;   // 64 KB
// [IMP-6] Render queue cap — refuse to enqueue beyond this many pending renders
const RENDER_QUEUE_MAX = 5;
// [IMP-7] Browser notification rate-limit window
const NOTIFICATION_COOLDOWN_MS = 5000;

// [IMP-8] Helper: sleep with abort signal awareness — used by retry/backoff loops
function _sleepAbortable(ms, signal) {
    return new Promise((resolve, reject) => {
        if (signal && signal.aborted) { reject(new DOMException('Aborted', 'AbortError')); return; }
        const t = setTimeout(resolve, ms);
        if (signal) signal.addEventListener('abort', () => { clearTimeout(t); reject(new DOMException('Aborted', 'AbortError')); }, { once: true });
    });
}

// [IMP-9] Concurrent request limiter — caps in-flight fetches at MAX_CONCURRENT_FETCHES
const _activeFetches = new Set();
const _fetchWaitQueue = [];
async function _acquireFetchSlot() {
    if (_activeFetches.size < MAX_CONCURRENT_FETCHES) { const tk = Symbol('slot'); _activeFetches.add(tk); return tk; }
    return new Promise(resolve => { _fetchWaitQueue.push(resolve); });
}
function _releaseFetchSlot(tk) {
    _activeFetches.delete(tk);
    if (_fetchWaitQueue.length) {
        const next = _fetchWaitQueue.shift();
        const ntk = Symbol('slot'); _activeFetches.add(ntk);
        next(ntk);
    }
}

// [IMP-10] Categorize fetch errors more granularly than classifyFetchError
function categorizeError(err, context) {
    if (!err) return { code: 'unknown', message: `${context} failed: unknown error`, retryable: false };
    if (err.name === 'AbortError') return { code: 'abort', message: `${context} was cancelled.`, retryable: false };
    if (err.name === 'TimeoutError') return { code: 'timeout', message: `${context} timed out — server may be hung.`, retryable: true };
    const m = (err.message || '').toLowerCase();
    if (m.includes('failed to fetch') || m.includes('networkerror') || m.includes('econnrefused')) return { code: 'network_down', message: SPB_ENGINE_OFFLINE_MSG, retryable: true };
    if (m.includes('paint file not found') || m.includes('paint_file')) return { code: 'paint_missing', message: 'Paint file not found. Check the Source Paint path.', retryable: false };
    if (m.includes('license')) return { code: 'license', message: 'License issue — open Settings to enter your key.', retryable: false };
    if (m.includes('json') || m.includes('unexpected token')) return { code: 'bad_json', message: `SPB returned invalid data during ${context}. Use Restart Server from the SPB tray, then try again.`, retryable: true };
    if (m.includes('http 5')) return { code: 'server_5xx', message: `${context} failed (server error). Try again.`, retryable: true };
    if (m.includes('http 4')) return { code: 'http_4xx', message: `${context} failed (client error). Check inputs.`, retryable: false };
    return { code: 'unknown', message: `${context} failed: ${err.message || 'unknown error'}`, retryable: false };
}

// [IMP-11] Limited fetch with retry/backoff + concurrency cap. Use for non-render endpoints.
async function limitedFetch(url, init, opts) {
    init = init || {};
    opts = opts || {};
    const maxRetries = opts.retries != null ? opts.retries : MAX_RETRY_COUNT;
    const ctx = opts.context || 'request';
    let attempt = 0;
    let lastErr = null;
    const tk = await _acquireFetchSlot();
    try {
        while (attempt <= maxRetries) {
            try {
                const res = await fetch(url, init);
                if (res.ok || (res.status >= 400 && res.status < 500)) return res;
                // 5xx — retryable
                throw new Error(`HTTP ${res.status}: ${res.statusText || 'server error'}`);
            } catch (e) {
                lastErr = e;
                const cat = categorizeError(e, ctx);
                if (!cat.retryable || attempt === maxRetries) throw e;
                const delay = Math.min(RETRY_MAX_DELAY_MS, RETRY_BASE_DELAY_MS * Math.pow(2, attempt)) + Math.random() * 200;
                console.warn(`[limitedFetch] ${ctx} attempt ${attempt + 1} failed (${cat.code}). Retrying in ${Math.round(delay)}ms...`);
                try { await _sleepAbortable(delay, init.signal); } catch (_) { throw e; }
                attempt++;
            }
        }
        throw lastErr;
    } finally {
        _releaseFetchSlot(tk);
    }
}

// [IMP-12] Connection status manager — single source of truth for online/reconnecting UI
const ConnectionStatus = {
    state: 'unknown',  // 'online' | 'offline' | 'reconnecting' | 'unknown'
    lastChange: 0,
    set(state) {
        if (this.state === state) return;
        this.state = state;
        this.lastChange = Date.now();
        this._render();
    },
    _render() {
        const dot = document.getElementById('serverStatus');
        if (!dot) return;
        if (this.state === 'reconnecting') {
            dot.classList.add('reconnecting');
            dot.title = 'Reconnecting...';
        } else {
            dot.classList.remove('reconnecting');
        }
    },
};
if (typeof window !== 'undefined') window.ConnectionStatus = ConnectionStatus;

// [IMP-13] Server version mismatch detection
const CLIENT_VERSION = '10.0.3-beta';
let _serverVersionWarned = false;
function checkServerVersion(statusData) {
    if (!statusData || !statusData.version || _serverVersionWarned) return;
    // 2026-06-08: only warn on a real MAJOR.MINOR drift. Patch bumps (7.0.6 vs 7.0.7)
    // are wire-compatible and must NOT nag the user (this fired every release because
    // CLIENT_VERSION was a hardcoded string nobody remembered to bump).
    const mm = v => String(v || '').split('.').slice(0, 2).join('.');
    if (mm(statusData.version) !== mm(CLIENT_VERSION)) {
        _serverVersionWarned = true;
        console.warn(`[version] Client v${CLIENT_VERSION} but server v${statusData.version}.`);
        if (typeof showToast === 'function') showToast(`Heads up: app v${statusData.version} vs UI v${CLIENT_VERSION} — if anything looks off, fully close and reopen the app.`, true);
    }
}

// [IMP-14] Render queue — serialize back-to-back render requests instead of dropping them
const RenderQueue = {
    pending: [],
    running: false,
    enqueue(fn, label) {
        if (this.pending.length >= RENDER_QUEUE_MAX) {
            if (typeof showToast === 'function') showToast(`Render queue full (max ${RENDER_QUEUE_MAX}). Wait for in-progress renders.`, true);
            return Promise.reject(new Error('Render queue full'));
        }
        return new Promise((resolve, reject) => {
            this.pending.push({ fn, label: label || 'render', resolve, reject, queuedAt: Date.now() });
            this._updateBadge();
            this._drain();
        });
    },
    async _drain() {
        if (this.running) return;
        const next = this.pending.shift();
        if (!next) return;
        this.running = true;
        this._updateBadge();
        try { const r = await next.fn(); next.resolve(r); }
        catch (e) { next.reject(e); }
        finally { this.running = false; this._updateBadge(); this._drain(); }
    },
    _updateBadge() {
        const el = document.getElementById('renderQueueBadge');
        if (el) {
            if (this.pending.length === 0 && !this.running) { el.style.display = 'none'; }
            else { el.style.display = 'inline-block'; el.textContent = `Q:${this.pending.length}${this.running ? '+1' : ''}`; }
        }
    },
    clear() { this.pending = []; this._updateBadge(); }
};
if (typeof window !== 'undefined') window.RenderQueue = RenderQueue;

// [IMP-15] Phase-based progress reporter — translates server stage strings into user-friendly text
function formatProgressPhase(status) {
    if (!status) return null;
    const stage = (status.stage || '').toLowerCase();
    const pct = Math.max(0, Math.min(100, Number(status.percent) || 0));
    if (stage === 'preparing' || stage === 'masks') return `Phase 1: building masks (${pct}%)...`;
    if (stage === 'rendering' || stage === 'zones') return `Phase 2: rendering zones (${pct}%)...`;
    if (stage === 'composing' || stage === 'compose') return `Phase 3: composing layers (${pct}%)...`;
    if (stage === 'spec' || stage === 'spec_overlay') return `Phase 4: applying spec overlays (${pct}%)...`;
    if (stage === 'writing' || stage === 'output') return `Phase 5: writing output files (${pct}%)...`;
    if (stage === 'done' || stage === 'complete') return `Complete!`;
    if (status.zone_name) return `Zone ${status.current_zone}/${status.total_zones} — ${status.zone_name} (${pct}%)`;
    return null;
}

// [IMP-16] Smart deduplication — fingerprint zone payload to skip identical re-renders
let _lastRenderFingerprint = null;
function _zonesFingerprint(zones, extras) {
    try {
        const slim = JSON.stringify({ z: zones, e: extras || {} });
        // FNV-1a 32-bit hash — fast & adequate for change detection
        let h = 0x811c9dc5;
        for (let i = 0; i < slim.length; i++) { h ^= slim.charCodeAt(i); h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0; }
        return h.toString(16);
    } catch (_) { return null; }
}

// Live iRacing auto-render is intentionally disabled. The owner wants full
// iRacing renders to run only from the Render button; live preview may update,
// but it must never queue a full export on edit.
const LIVE_IRACING_RENDER_KEY = 'spb_live_iracing_render_enabled';

function _setLiveIracingRenderBadge(text, active) {
    const badge = document.getElementById('liveIracingRenderBadge');
    if (!badge) return;
    badge.style.display = active ? 'inline' : 'none';
    if (text) badge.textContent = text;
}

function isLiveIracingRenderEnabled() {
    return false;
}

function toggleLiveIracingRender() {
    const cb = document.getElementById('liveIracingRenderCheckbox');
    if (cb) cb.checked = false;
    try { localStorage.removeItem(LIVE_IRACING_RENDER_KEY); } catch (_) {}
    _setLiveIracingRenderBadge('', false);
    if (typeof showToast === 'function') showToast('Auto-render is off. Use Render to export to iRacing.');
}

function scheduleLiveIracingRender() {
    return false;
}

function initLiveIracingRenderControls() {
    const cb = document.getElementById('liveIracingRenderCheckbox');
    if (cb) cb.checked = false;
    try { localStorage.removeItem(LIVE_IRACING_RENDER_KEY); } catch (_) {}
    _setLiveIracingRenderBadge('', false);
}

if (typeof window !== 'undefined') {
    window.isLiveIracingRenderEnabled = isLiveIracingRenderEnabled;
    window.toggleLiveIracingRender = toggleLiveIracingRender;
    window.scheduleLiveIracingRender = scheduleLiveIracingRender;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLiveIracingRenderControls);
    } else {
        setTimeout(initLiveIracingRenderControls, 0);
    }
}

// [IMP-17] Pre-render validation — return list of warnings/errors before sending
function validateRenderPayload(paintFile, zones, extras) {
    const issues = [];
    const hasLivePaintPayload = !!(extras && extras.paint_image_base64);
    if (!hasLivePaintPayload) {
        if (!paintFile || !paintFile.trim()) issues.push({ severity: 'error', msg: 'Paint file path is empty.' });
        else if (!paintFile.includes('/') && !paintFile.includes('\\')) issues.push({ severity: 'error', msg: 'Paint file needs a full path, not just a filename.' });
        else if (!/\.tga$/i.test(paintFile)) issues.push({ severity: 'warn', msg: 'Paint file does not end in .tga - render may fail.' });
    }
    if (!zones || zones.length === 0) {
        if (!extras || !extras.import_spec_map) issues.push({ severity: 'error', msg: 'No zones to render and no spec map imported.' });
    }
    if (zones && zones.length > 30) issues.push({ severity: 'warn', msg: `${zones.length} zones — render may be slow.` });
    return issues;
}

// [IMP-18] Toast helper that supports retry — lazily wraps showToast if available
function showRetryableToast(message, retryFn) {
    if (typeof showToast !== 'function') return;
    showToast(message, true);
    // Stash last retry function so a global Retry button (if present) can call it
    window._lastRetryFn = retryFn || null;
}

// [PACK-UX] A render failed because the finish needs an un-bundled Finish Pack
// the buyer hasn't downloaded (server returns error_code:'pack_missing'). Prompt
// them to open the in-app Finish Packs downloader rather than blame their paint
// file path. `result` carries pack_label / pack from engine/asset_packs.
function promptFinishPackDownload(result) {
    const label = (result && result.pack_label) ? result.pack_label : 'Finish';
    const headline = (result && result.pack_label)
        ? `This finish needs the “${label}” pack.`
        : 'This finish needs a Finish Pack that isn\'t installed yet.';
    const openDownloader = function () {
        if (typeof window !== 'undefined' && typeof window.openFinishPacksModal === 'function') {
            try { window.openFinishPacksModal(); return true; } catch (_) { /* fall through */ }
        }
        return false;
    };

    // Preferred: a small in-app modal with a Download button.
    try {
        if (typeof document !== 'undefined' && document.body) {
            // Don't stack duplicates if the user re-renders.
            const existing = document.getElementById('packMissingPrompt');
            if (existing) existing.remove();

            const overlay = document.createElement('div');
            overlay.id = 'packMissingPrompt';
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.78);z-index:10000;display:flex;align-items:center;justify-content:center;padding:24px;';

            const card = document.createElement('div');
            card.style.cssText = 'max-width:440px;background:#1c1c22;color:#eee;border:1px solid #3a3a44;border-radius:10px;padding:22px 24px;box-shadow:0 10px 40px rgba(0,0,0,0.55);font-size:14px;line-height:1.45;';

            const title = document.createElement('div');
            title.style.cssText = 'font-size:16px;font-weight:600;margin-bottom:10px;';
            title.textContent = 'Finish Pack needed';

            const body = document.createElement('div');
            body.style.cssText = 'margin-bottom:18px;color:#cfcfd6;';
            body.textContent = headline + ' Download it from Finish Packs, then restart to use it.';

            const btnRow = document.createElement('div');
            btnRow.style.cssText = 'display:flex;gap:10px;justify-content:flex-end;';

            const dismiss = document.createElement('button');
            dismiss.textContent = 'Not now';
            dismiss.style.cssText = 'padding:8px 14px;background:#2a2a33;color:#ccc;border:1px solid #44444f;border-radius:6px;cursor:pointer;';
            dismiss.onclick = () => overlay.remove();

            const download = document.createElement('button');
            download.textContent = 'Download ' + label + ' pack';
            download.style.cssText = 'padding:8px 16px;background:var(--accent,#e0457b);color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;';
            download.onclick = () => {
                overlay.remove();
                if (!openDownloader() && typeof showToast === 'function') {
                    showToast('Open the gear menu → Finish Packs to download ' + label + '.', true);
                }
            };

            btnRow.appendChild(dismiss);
            btnRow.appendChild(download);
            card.appendChild(title);
            card.appendChild(body);
            card.appendChild(btnRow);
            overlay.appendChild(card);
            overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
            document.body.appendChild(overlay);
            return;
        }
    } catch (_) { /* fall through to confirm/toast */ }

    // Fallback: native confirm, then toast.
    try {
        if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
            if (window.confirm(headline + '\n\nOpen Finish Packs to download it now?')) {
                if (openDownloader()) return;
            }
        }
    } catch (_) { /* ignore */ }
    if (typeof showToast === 'function') {
        showToast(headline + ' Open Finish Packs (gear menu) to download it, then restart.', true);
    }
}
if (typeof window !== 'undefined') window.promptFinishPackDownload = promptFinishPackDownload;

// [IMP-19] Browser Notification API — notify when render completes if tab is hidden
let _lastNotifyAt = 0;
function notifyRenderComplete(success, zoneCount, elapsed) {
    if (typeof window === 'undefined' || !('Notification' in window)) return;
    if (document.visibilityState === 'visible') return;            // user already looking
    if (Date.now() - _lastNotifyAt < NOTIFICATION_COOLDOWN_MS) return;
    _lastNotifyAt = Date.now();
    const post = () => {
        try {
            const title = success ? 'Shokker Paint Booth — render complete' : 'Shokker Paint Booth — render failed';
            const body = success ? `${zoneCount} zones in ${elapsed}s. Click to view.` : 'Render failed. Click to view details.';
            const n = new Notification(title, { body, tag: 'spb-render', renotify: false });
            n.onclick = () => { window.focus(); n.close(); };
        } catch (_) { /* ignore */ }
    };
    if (Notification.permission === 'granted') post();
    else if (Notification.permission !== 'denied') Notification.requestPermission().then(p => { if (p === 'granted') post(); });
}

// [IMP-20] Optional ding sound on render complete — disabled unless localStorage flag set
function playRenderDing(success) {
    try {
        if (typeof localStorage === 'undefined' || localStorage.getItem('shokker_render_ding') !== '1') return;
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        const ctx = new Ctx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.value = success ? 880 : 220;
        gain.gain.value = 0.0001;
        gain.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.4);
        osc.start();
        osc.stop(ctx.currentTime + 0.45);
        setTimeout(() => { try { ctx.close(); } catch (_) {} }, 600);
    } catch (_) { /* ignore audio errors */ }
}

// [IMP-21] Render time history & estimator — adapts based on past render durations
const _renderTimeHistory = []; // ring buffer of { zoneCount, seconds }
const RENDER_TIME_HISTORY_MAX = 20;
function recordRenderTime(zoneCount, seconds) {
    if (!zoneCount || !seconds || seconds <= 0) return;
    _renderTimeHistory.push({ zoneCount, seconds });
    if (_renderTimeHistory.length > RENDER_TIME_HISTORY_MAX) _renderTimeHistory.shift();
}
function smartEstimateRenderTime(zoneCount) {
    if (_renderTimeHistory.length === 0) return estimateRenderTime(zoneCount);
    // Linear regression: seconds ≈ a + b * zoneCount
    let n = _renderTimeHistory.length, sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (const h of _renderTimeHistory) { sx += h.zoneCount; sy += h.seconds; sxx += h.zoneCount * h.zoneCount; sxy += h.zoneCount * h.seconds; }
    const denom = (n * sxx - sx * sx) || 1;
    const b = (n * sxy - sx * sy) / denom;
    const a = (sy - b * sx) / n;
    const est = Math.max(2, Math.round(a + b * zoneCount));
    return `~${est}s`;
}

// [IMP-22] Background notification permission probe on first user gesture
function _probeNotificationPermission() {
    try {
        if (typeof Notification === 'undefined') return;
        if (Notification.permission === 'default') {
            // Don't auto-request, let user opt in via a UI button.
            console.log('[notify] Notification permission default — call requestNotificationPermission() to enable.');
        }
    } catch (_) {}
}
function requestNotificationPermission() {
    if (typeof Notification !== 'undefined' && Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
}
if (typeof window !== 'undefined') window.requestNotificationPermission = requestNotificationPermission;

// [IMP-23] Refocus reconnect handler — re-probe server when tab gains focus after being hidden
let _wasHidden = false;
if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) { _wasHidden = true; return; }
        if (_wasHidden && typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.checkStatusLight === 'function') {
            _wasHidden = false;
            ConnectionStatus.set('reconnecting');
            ShokkerAPI.checkStatusLight().then(d => { ConnectionStatus.set(d ? 'online' : 'offline'); });
        }
    });
}

// [IMP-24] Cache invalidation hooks — clear specific entries when zones change
function invalidateCacheKey(key) { _responseCache.delete(key); }
function invalidateAllCaches() { _responseCache.clear(); }
if (typeof window !== 'undefined') {
    window.invalidateCacheKey = invalidateCacheKey;
    window.invalidateAllCaches = invalidateAllCaches;
}

// [IMP-25] GZip request body using CompressionStream when available
async function maybeGzipBody(jsonBody) {
    try {
        if (typeof CompressionStream === 'undefined') return { body: jsonBody, headers: {} };
        const bytes = new TextEncoder().encode(jsonBody);
        if (bytes.byteLength < GZIP_THRESHOLD_BYTES) return { body: jsonBody, headers: {} };
        const cs = new CompressionStream('gzip');
        const stream = new Blob([bytes]).stream().pipeThrough(cs);
        const blob = await new Response(stream).blob();
        return { body: blob, headers: { 'Content-Encoding': 'gzip' } };
    } catch (_) { return { body: jsonBody, headers: {} }; }
}

// [IMP-26] Active in-flight registry — used by global abort cascade
const _inFlightControllers = new Set();
function registerController(ctrl) { if (ctrl) _inFlightControllers.add(ctrl); return ctrl; }
function unregisterController(ctrl) { _inFlightControllers.delete(ctrl); }
function abortAllInFlight(reason) {
    for (const c of Array.from(_inFlightControllers)) { try { c.abort(reason || 'global abort'); } catch (_) {} }
    _inFlightControllers.clear();
}
if (typeof window !== 'undefined') window.abortAllInFlight = abortAllInFlight;

// ===== REQUEST DEDUPLICATION ===== // [16-20]
const _pendingRequests = new Map();       // endpoint -> Promise (prevents duplicate in-flight requests)

/**
 * Deduplicated fetch wrapper. Prevents duplicate simultaneous requests to the same endpoint.
 * If a request to the same key is already in-flight, returns the existing promise.
 * @param {string} key - Unique key for deduplication (typically the URL)
 * @param {Function} fetchFn - Function that returns a fetch Promise
 * @returns {Promise} The fetch result
 */
function deduplicatedFetch(key, fetchFn) {
    if (_pendingRequests.has(key)) {
        console.log(`[dedup] Reusing in-flight request: ${key}`);
        return _pendingRequests.get(key);
    }
    const promise = fetchFn().finally(() => {
        _pendingRequests.delete(key);
    });
    _pendingRequests.set(key, promise);
    return promise;
}

// ===== CANVAS TO BASE64 (async, non-blocking) ===== // [PERF]
/**
 * Convert a canvas to a base64 data URL using toBlob (async, off-main-thread).
 * ~2-3x faster than synchronous toDataURL for large canvases because the
 * PNG encoding runs on a separate thread. Falls back to toDataURL if toBlob
 * is unavailable or fails.
 * @param {HTMLCanvasElement} canvas - The canvas to encode
 * @param {string} [mimeType='image/png'] - MIME type for encoding
 * @returns {Promise<string>} Base64 data URL
 */
function canvasToBase64Async(canvas, mimeType = 'image/png') {
    return new Promise((resolve, reject) => {
        if (!canvas || typeof canvas.toBlob !== 'function') {
            // Fallback for OffscreenCanvas or missing toBlob
            try { resolve(canvas.toDataURL(mimeType)); } catch (e) { reject(e); }
            return;
        }
        canvas.toBlob(blob => {
            if (!blob) {
                // toBlob failed, fall back to sync
                try { resolve(canvas.toDataURL(mimeType)); } catch (e) { reject(e); }
                return;
            }
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => {
                try { resolve(canvas.toDataURL(mimeType)); } catch (e) { reject(e); }
            };
            reader.readAsDataURL(blob);
        }, mimeType);
    });
}

// ===== RESPONSE CACHE (for static data) ===== // [21-25]
const _responseCache = new Map();         // key -> { data, timestamp }
const CACHE_TTL_MS = 300000;              // 5 min cache TTL for static data

/**
 * Cached fetch wrapper. Returns cached data if fresh, otherwise fetches and caches.
 * @param {string} key - Cache key
 * @param {Function} fetchFn - Async function that returns parsed data
 * @param {number} [ttl=CACHE_TTL_MS] - Cache time-to-live in ms
 * @returns {Promise} Cached or fresh data
 */
async function cachedFetch(key, fetchFn, ttl = CACHE_TTL_MS) {
    const cached = _responseCache.get(key);
    if (cached && (Date.now() - cached.timestamp) < ttl) {
        return cached.data;
    }
    const data = await fetchFn();
    _responseCache.set(key, { data, timestamp: Date.now() });
    return data;
}

/**
 * Classify a fetch/network error into a user-friendly message. // [11-15]
 * @param {Error} err - The caught error
 * @param {string} context - What operation failed (e.g. "render", "config save")
 * @returns {string} User-friendly error message
 */
function classifyFetchError(err, context) {
    if (!err) return `${context} failed: unknown error`;
    if (err.name === 'AbortError') return `${context} was cancelled or timed out.`;
    if (err.name === 'TimeoutError') return `${context} timed out. The server may be overloaded.`;
    if (err.message && err.message.includes('Failed to fetch')) return SPB_ENGINE_OFFLINE_MSG;
    if (err.message && err.message.includes('NetworkError')) return `Network error during ${context}. Check your connection.`;
    if (err.message && err.message.includes('JSON')) return `Server returned invalid data during ${context}. Try restarting the server.`;
    return `${context} failed: ${err.message || 'unknown error'}`;
}

/**
 * Safely parse JSON from a fetch response, with a friendly error on failure. // [13]
 * @param {Response} res - Fetch Response object
 * @param {string} context - Operation context for error messages
 * @returns {Promise<Object>} Parsed JSON
 */
async function safeParseJSON(res, context) {
    try {
        return await res.json();
    } catch (e) {
        throw new Error(`Server returned invalid JSON during ${context}. Status: ${res.status}`);
    }
}

/**
 * Show a render time estimate in the progress bar based on zone count. // [36-40]
 * @param {number} zoneCount - Number of zones to render
 * @returns {string} Estimated time string like "~12s"
 */
function estimateRenderTime(zoneCount) {
    const estimate = RENDER_ESTIMATE_BASE_S + (zoneCount * RENDER_ESTIMATE_PER_ZONE_S);
    return `~${estimate}s`;
}

// ===== FINISH HOVER POPUP =====
let finishPopupTimeout = null;
// [spb-hover-20260803a] owner: "the instant popup is BACK... it's supposed to
// have the delay and then the larger popup." The finish LIBRARY cards called
// this instantly on mouseenter — the one hover surface the 2026-08-02 fix
// missed. Same 2s intent delay as the swatch picker popout; hideFinishPopup
// cancels a pending intent so scrolling the list never flashes popups.
let _finishPopupIntentTimer = null;
const FINISH_POPUP_INTENT_DELAY_MS = 2000;

function showFinishPopup(e, finishId) {
    if (_finishPopupIntentTimer) clearTimeout(_finishPopupIntentTimer);
    // e.currentTarget is only valid during dispatch — capture the element NOW;
    // the rect is measured fresh at fire time (the list may scroll meanwhile).
    const el = e ? e.currentTarget : null;
    const ex = e ? e.clientX : 0, ey = e ? e.clientY : 0;
    _finishPopupIntentTimer = setTimeout(function() {
        _finishPopupIntentTimer = null;
        if (!el || !el.isConnected) return;
        _showFinishPopupNow({ clientX: ex, clientY: ey, currentTarget: el }, finishId);
    }, FINISH_POPUP_INTENT_DELAY_MS);
}

/**
 * Show a finish hover popup with preview, name, description, and spec channel info. // [46]
 * @param {MouseEvent} e - Mouse event from the hover trigger
 * @param {string} finishId - ID of the finish to display
 */
function _showFinishPopupNow(e, finishId) {
    const finish = BASES.find(f => f.id === finishId) || PATTERNS.find(f => f.id === finishId) || MONOLITHICS.find(f => f.id === finishId) || FINISHES.find(f => f.id === finishId);
    if (!finish) return;
    const isBase = !!BASES.find(f => f.id === finishId);
    const isPattern = !!PATTERNS.find(f => f.id === finishId);
    const baseMeta = (isBase && typeof getBaseMetadata === 'function') ? getBaseMetadata(finishId) : null;
    const patternMeta = (isPattern && typeof getPatternMetadata === 'function') ? getPatternMetadata(finishId) : null;

    clearTimeout(finishPopupTimeout);
    const popup = document.getElementById('finishPopup');
    const previewCanvas = document.getElementById('finishPopupPreview');
    const nameEl = document.getElementById('finishPopupName');
    const descEl = document.getElementById('finishPopupDesc');
    const catEl = document.getElementById('finishPopupCat');
    const chanEl = document.getElementById('finishPopupChannels');
    if (!popup || !previewCanvas) return; // [51] null check - bail if DOM missing

    const _fpFt = isBase ? 'base' : (isPattern ? 'pattern' : 'monolithic');
    const _fpTint = (typeof _normalizeSwatchTintHex === 'function')
        ? _normalizeSwatchTintHex(null, finish && finish.swatch)
        : '888888';
    const _fpKey = (typeof _pickerSwatchFinishKey === 'function')
        ? _pickerSwatchFinishKey(finishId, _fpFt)
        : finishId;
    const swatchW = previewCanvas.width;
    const swatchH = previewCanvas.height;
    const swatchUrl = getSwatchUrl(_fpKey, _fpTint, true, swatchW, _fpFt);
    if (swatchUrl) {
        const pctx = previewCanvas.getContext('2d');
        pctx.fillStyle = '#1a1a1a';
        pctx.fillRect(0, 0, swatchW, swatchH);
        const img = new Image();
        img.onload = () => {
            pctx.clearRect(0, 0, swatchW, swatchH);
            pctx.drawImage(img, 0, 0, swatchW, swatchH);
        };
        img.src = swatchUrl;
    } else {
        const pctx = previewCanvas.getContext('2d');
        const cacheKey = finishId + '_popup';
        if (_previewCache[cacheKey]) {
            pctx.putImageData(_previewCache[cacheKey], 0, 0);
        } else {
            renderPatternPreview(pctx, previewCanvas.width, previewCanvas.height, finishId);
            _previewCache[cacheKey] = pctx.getImageData(0, 0, previewCanvas.width, previewCanvas.height);
            // 2026-06-28 OOM fix: bound the popup-preview cache — drop oldest over 200 entries.
            var _ppk = Object.keys(_previewCache);
            if (_ppk.length > 200) delete _previewCache[_ppk[0]];
        }
    }

    nameEl.textContent = finish.name;
    descEl.textContent = finish.desc;
    const popupChips = [];
    const _chip = function(label, color) {
        return `<span style="display:inline-block; margin:2px 4px 0 0; padding:1px 6px; border-radius:999px; border:1px solid ${color}; color:${color}; font-size:8px;">${label}</span>`;
    };
    if (isBase && baseMeta) {
        if (baseMeta.family && typeof FAMILY_DISPLAY_NAMES !== 'undefined') popupChips.push(_chip(FAMILY_DISPLAY_NAMES[baseMeta.family] || baseMeta.family, '#00e5ff'));
        if (baseMeta.tier) popupChips.push(_chip(String(baseMeta.tier).toUpperCase(), '#ffd700'));
        popupChips.push(_chip(baseMeta.sponsor_safe === false ? 'SPONSOR CAUTION' : 'SPONSOR SAFE', baseMeta.sponsor_safe === false ? '#ff9b66' : '#6be28b'));
        if (baseMeta.aggression != null) popupChips.push(_chip(`IMPACT ${baseMeta.aggression}/5`, '#c68bff'));
    } else if (isPattern && patternMeta) {
        if (patternMeta.style) popupChips.push(_chip(String(patternMeta.style).toUpperCase(), '#00e5ff'));
        if (patternMeta.readability) popupChips.push(_chip(`TEXT ${String(patternMeta.readability).toUpperCase()}`, patternMeta.readability === 'good' ? '#6be28b' : patternMeta.readability === 'fair' ? '#ffd700' : '#ff9b66'));
        if (patternMeta.density) popupChips.push(_chip(String(patternMeta.density).toUpperCase(), '#c68bff'));
    }
    const popupType = finish.cat || (isBase ? 'Base Material' : isPattern ? 'Pattern' : 'Special');
    catEl.innerHTML = `<div>${popupType}</div>${popupChips.length ? `<div style="margin-top:2px;">${popupChips.join('')}</div>` : ''}`;

    // Show spec channel hints based on finish type
    const channelHints = {
        'gloss': 'M:0 R:20 CC:16 - smooth mirror clearcoat',
        'matte': 'M:0 R:215 CC:0 - zero metallic, max rough',
        'satin': 'M:0 R:100 CC:10 - mid sheen partial clearcoat',
        'metallic': 'M:200 R:50 CC:16 - visible flake sparkle',
        'pearl': 'M:100 R:40 CC:16 - pearlescent shimmer',
        'chrome': 'M:255 R:2 CC:0 - perfect mirror reflection',
        'candy': 'M:130 R:15 CC:16 - deep wet tinted glass',
        'satin_metal': 'M:235 R:65 CC:16 - subtle brushed metallic',
        'brushed_titanium': 'M:180 R:70 CC:0 - heavy directional grain',
        'anodized': 'M:170 R:80 CC:0 - gritty matte aluminum',
        'frozen': 'M:225 R:140 CC:0 - frozen icy matte metal',
        'blackout': 'M:30 R:220 CC:0 - stealth murdered out',
        'carbon_fiber': 'Pattern: tight 2x2 twill weave, R modulation ±50',
        'forged_carbon': 'Pattern: chopped chunks, M±40 R±50',
        'diamond_plate': 'Pattern: raised diamond tread, R-132 M+60',
        'dragon_scale': 'Pattern: image-based scales (Artistic & Cultural)',
        'dragon_scale_alt': 'Pattern: image-based vibrant scales',
        'aztec_alt1': 'Pattern: image-based geometric Aztec alt 1',
        'aztec_alt2': 'Pattern: image-based geometric Aztec alt 2',
        'fleur_de_lis': 'Pattern: image-based French lily motif',
        'fleur_de_lis_alt': 'Pattern: image-based damask lily',
        'japanese_wave': 'Pattern: image-based Kanagawa wave',
        'mandala': 'Pattern: image-based mandala',
        'mandela_ornate': 'Pattern: image-based ornate mandala',
        'mosaic': 'Pattern: image-based mosaic tiles',
        'muertos_dod1': 'Pattern: image-based Day of the Dead (dark)',
        'muertos_dod2': 'Pattern: image-based Day of the Dead (light)',
        'norse_rune': 'Pattern: image-based rune grid',
        'steampunk_gears': 'Pattern: image-based clockwork gears',
        'hex_mesh': 'Pattern: honeycomb wire grid, R-155 M+155',
        'ripple': 'Pattern: concentric ring waves, R-85 M+100',
        'hammered': 'Pattern: hand-hammered dimples, R-112 M+95',
        'lightning': 'Pattern: forked bolt paths, R-177 M+175',
        'plasma': 'Pattern: branching electric veins, R-118 M+95',
        'hologram': 'Pattern: 6px scanlines, R-75 only',
        'interference': 'Pattern: rainbow wave bands, R+100 only',
        'battle_worn': 'Pattern: scratch damage + variable clearcoat',
        'acid_wash': 'Pattern: acid etch + variable clearcoat',
        'cracked_ice': 'Pattern: frozen crack network, R+115',
        'metal_flake': 'Pattern: coarse sparkle, M+50 + R noise',
        'holographic_flake': 'Pattern: prismatic micro-grid, R+40',
        'stardust': 'Pattern: sparse star pinpoints, R-52 M+95',
        'phantom': 'Special: paint vanishes into mirror',
        'ember_glow': 'Special: hot metal glowing from within',
        'liquid_metal': 'Special: flowing mercury T-1000 pools',
        'frost_bite': 'Special: coarse ice crystal texture',
        'worn_chrome': 'Special: patchy chrome with patina wear',
        // --- Expansion Pack Bases ---
        'ceramic': 'M:60 R:8 CC:16 - ultra-smooth ceramic coating',
        'satin_wrap': 'M:0 R:130 CC:0 - vinyl wrap satin sheen',
        'primer': 'M:0 R:200 CC:0 - raw flat primer gray',
        'gunmetal': 'M:220 R:40 CC:16 - dark blue-gray metallic',
        'copper': 'M:190 R:55 CC:16 - warm oxidized copper',
        'chameleon': 'M:160 R:25 CC:16 - dual-tone color-shift',
        // --- Expansion Pack Patterns ---
        'pinstripe': 'Pattern: thin parallel stripes, R-60 M+40',
        'camo': 'Pattern: digital splinter blocks, R+60 M-30',
        'wood_grain': 'Pattern: flowing grain lines, R+80 M-50',
        'snake_skin': 'Pattern: elongated scales, R-100 M+80',
        'tire_tread': 'Pattern: V-groove rubber, R+80 M-40',
        'circuit_board': 'Pattern: PCB traces + pads, R-120 M+140',
        'lava_flow': 'Pattern: molten cracks + variable CC',
        'rain_drop': 'Pattern: water beading, R-80 M+60',
        'barbed_wire': 'Pattern: twisted wire + barbs, R-100 M+130',
        'chainmail': 'Pattern: interlocking rings, R-90 M+100',
        // brick removed - Artistic & Cultural image-based
        'leopard': 'Pattern: organic rosette spots, R+50 M-60',
        'crocodile': 'Pattern: rectangular interlocking scales, R-80 M+70',
        'feather': 'Pattern: layered barbs from rachis shaft, R+40 M-20',
        'giraffe': 'Pattern: Voronoi polygon patches, R+30 M-40',
        'tiger_stripe': 'Pattern: noise-warped diagonal stripes, R-60 M+50',
        'zebra': 'Pattern: bold B/W organic stripes, R-40 M+30',
        'snake_skin_2': 'Pattern: diamond python scales, R-90 M+75',
        'snake_skin_3': 'Pattern: hourglass viper scales, R-85 M+70',
        'snake_skin_4': 'Pattern: cobblestone boa scales, R-70 M+60',
        'razor': 'Pattern: diagonal slash marks, R-80 M+120',
        // --- Expansion Pack Specials ---
        'oil_slick': 'Special: rainbow oil pools + variable roughness',
        'galaxy': 'Special: deep space nebula + star clusters',
        'rust': 'Special: progressive oxidation + no clearcoat',
        'neon_glow': 'Special: UV reactive fluorescent glow',
        'weathered_paint': 'Special: faded peeling layers to primer',
        // Your image patterns (patternexamples folder)
        '12155818_4903117': 'Pattern: image from file (tiled)',
        '12267458_4936872': 'Pattern: image from file (tiled)',
        '12284536_4958169': 'Pattern: image from file (tiled)',
        '12428555_4988298': 'Pattern: image from file (tiled)',
        '144644845_10133112': 'Pattern: image from file (tiled)',
        '17852162_5911715': 'Pattern: image from file (tiled)',
        '248169': 'Pattern: image from file (tiled)',
        '6868396_23455': 'Pattern: image from file (tiled)',
        '78534344_9837553_1': 'Pattern: image from file (tiled)',
        '8488198_3924387': 'Pattern: image from file (tiled)',
        'Groovy_Swirl': 'Pattern: image from file (60s/70s style)',
        'Halftone_Rainbow': 'Pattern: image from file (tiled)',
        'Plad_Wrapper': 'Pattern: image from file (tiled)',
    };
    const infoBits = [];
    if (channelHints[finishId]) infoBits.push(`<div>${channelHints[finishId]}</div>`);
    if (isBase && baseMeta) {
        if (Array.isArray(baseMeta.best_with) && baseMeta.best_with.length > 0) {
            const bestNames = baseMeta.best_with
                .map(id => (typeof PATTERNS !== 'undefined' && PATTERNS.find(p => p.id === id)) || null)
                .filter(Boolean)
                .slice(0, 4)
                .map(p => p.name)
                .join(', ');
            if (bestNames) infoBits.push(`<div style="margin-top:4px;color:#ddd;"><span style="color:#999;">Best with:</span> ${bestNames}</div>`);
        }
        if (Array.isArray(baseMeta.similar_to) && baseMeta.similar_to.length > 0) {
            const similarNames = baseMeta.similar_to
                .map(id => (typeof BASES !== 'undefined' && BASES.find(b => b.id === id)) || null)
                .filter(Boolean)
                .slice(0, 4)
                .map(b => b.name)
                .join(', ');
            if (similarNames) infoBits.push(`<div style="margin-top:2px;color:#ddd;"><span style="color:#999;">Similar:</span> ${similarNames}</div>`);
        }
    } else if (isPattern && patternMeta && Array.isArray(patternMeta.best_bases) && patternMeta.best_bases.length > 0) {
        const bestBases = patternMeta.best_bases
            .slice(0, 4)
            .map(fam => (typeof FAMILY_DISPLAY_NAMES !== 'undefined' && FAMILY_DISPLAY_NAMES[fam]) || fam)
            .join(', ');
        if (bestBases) infoBits.push(`<div style="margin-top:4px;color:#ddd;"><span style="color:#999;">Best on:</span> ${bestBases}</div>`);
    }
    chanEl.innerHTML = infoBits.join('') || '';

    // Position popup to the left of the finish list item
    const rect = e.currentTarget.getBoundingClientRect();
    popup.style.left = Math.max(10, rect.left - 270) + 'px';
    popup.style.top = Math.max(10, Math.min(rect.top - 30, window.innerHeight - 300)) + 'px';
    popup.classList.add('visible');
}

/** Hide the finish hover popup after a short delay. */
function hideFinishPopup() {
    // [spb-hover-20260803a] cancel a pending 2s intent before it fires
    if (_finishPopupIntentTimer) { clearTimeout(_finishPopupIntentTimer); _finishPopupIntentTimer = null; }
    finishPopupTimeout = setTimeout(() => {
        const popup = document.getElementById('finishPopup'); // [51] null check
        if (popup) popup.classList.remove('visible');
    }, FINISH_POPUP_HIDE_DELAY_MS); // [42] named constant
}

// ===== SWATCH HOVER POPUP (for swatch picker grid) =====
let _shpTimeout = null;
const _shpPreviewCache = {}; // Separate cache for 140x140 popup previews

/**
 * Show a swatch hover popup with 140x140 preview for the swatch picker grid. // [47]
 * @param {HTMLElement} el - The swatch grid item element
 */
function showSwatchHoverPopup(el) {
    clearTimeout(_shpTimeout);
    const finishId = el.getAttribute('data-finish-id');
    if (!finishId) return;
    const finishType = el.getAttribute('data-finish-type') || '';

    const popup = document.getElementById('swatchHoverPopup');
    const canvas = document.getElementById('shpCanvas');
    const nameEl = document.getElementById('shpName');
    const descEl = document.getElementById('shpDesc');
    const catEl = document.getElementById('shpCat');
    if (!popup || !canvas) return; // [52] null check - bail if DOM missing

    const finish = BASES.find(f => f.id === finishId)
        || PATTERNS.find(f => f.id === finishId)
        || MONOLITHICS.find(f => f.id === finishId);
    const catalogSwatch = finish && finish.swatch ? finish.swatch : null;
    const tintHex = (typeof _normalizeSwatchTintHex === 'function')
        ? _normalizeSwatchTintHex(null, catalogSwatch)
        : '888888';
    const swatchKey = (typeof _pickerSwatchFinishKey === 'function')
        ? _pickerSwatchFinishKey(finishId, finishType || null)
        : finishId;

    // Render 140x140 preview via server swatch (async, instant update)
    const pctx = canvas.getContext('2d');
    const swatchUrl = getSwatchUrl(swatchKey, tintHex, true, 140, finishType || null);
    if (swatchUrl) {
        pctx.fillStyle = '#1a1a1a';
        pctx.fillRect(0, 0, 140, 140);
        const cacheKey = swatchKey + ':' + tintHex + '_shp';
        if (_shpPreviewCache[cacheKey]) {
            pctx.drawImage(_shpPreviewCache[cacheKey], 0, 0, 140, 140);
        } else {
            const img = new Image();
            img.onload = () => {
                pctx.clearRect(0, 0, 140, 140);
                pctx.drawImage(img, 0, 0, 140, 140);
                _shpPreviewCache[cacheKey] = img;
            };
            img.src = swatchUrl;
        }
    } else {
        const cacheKey = finishId + '_shp';
        if (_shpPreviewCache[cacheKey]) {
            pctx.putImageData(_shpPreviewCache[cacheKey], 0, 0);
        } else {
            renderPatternPreview(pctx, 140, 140, finishId);
            _shpPreviewCache[cacheKey] = pctx.getImageData(0, 0, 140, 140);
        }
    }

    nameEl.textContent = finish ? finish.name : finishId;
    descEl.textContent = el.getAttribute('data-desc') || (finish ? finish.desc : '');

    // Category label
    if (BASES.some(f => f.id === finishId)) catEl.textContent = 'Base Material';
    else if (PATTERNS.some(f => f.id === finishId)) catEl.textContent = 'Pattern';
    else if (finishId.startsWith('clr_')) catEl.textContent = 'Solid Color';
    else if (finishId.startsWith('grad_') || finishId.startsWith('gradm_') || finishId.startsWith('grad3_')) catEl.textContent = 'Gradient';
    else if (finishId.startsWith('ghostg_')) catEl.textContent = 'Ghost Gradient';
    else if (finishId.startsWith('cs_')) catEl.textContent = 'Color Shift';
    else if (finishId.startsWith('mc_')) catEl.textContent = 'Multi-Color';
    else catEl.textContent = 'Special';

    // Position popup near the swatch
    const rect = el.getBoundingClientRect();
    let left = rect.right + 10;
    if (left + 230 > window.innerWidth) left = rect.left - 230;
    if (left < 5) left = 5;
    let top = rect.top - 40;
    if (top + 240 > window.innerHeight) top = window.innerHeight - 245;
    if (top < 5) top = 5;

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.style.display = 'block';
}

/** Hide the swatch hover popup after a short delay. */
function hideSwatchHoverPopup() {
    _shpTimeout = setTimeout(() => {
        const popup = document.getElementById('swatchHoverPopup'); // [52] null check
        if (popup) popup.style.display = 'none';
    }, SWATCH_POPUP_HIDE_DELAY_MS); // [43] named constant
}

// Delegate hover events on swatch picker grid (uses event delegation)
document.addEventListener('mouseenter', function (e) {
    if (!e.target || typeof e.target.closest !== 'function') return;
    const item = e.target.closest('.swatch-item[data-finish-id]');
    if (item && item.closest('#swatchPopupGrid')) {
        // [2026-08-06 owner: "there's STILL that instant little popup"] This
        // 140x140 popup fired with NO delay on every card mouseenter — the
        // second hover surface (the 2026-08-03 note flagged the same recurring
        // class). The finish grid is click-to-enlarge now: NO hover popups.
        // The live-mode on-car Stage paint below stays — it is not a popup.
        if (typeof previewFinishOnStage === 'function') previewFinishOnStage(item);
    }
}, true);

document.addEventListener('mouseleave', function (e) {
    if (!e.target || typeof e.target.closest !== 'function') return;
    const item = e.target.closest('.swatch-item[data-finish-id]');
    if (item && item.closest('#swatchPopupGrid')) {
        // SPB live-picker: revert the Stage to the committed zone when the cursor leaves
        // a card (live mode only). Cheap no-op when not in live mode.
        if (typeof window.isPickerLiveMode === 'function' && window.isPickerLiveMode()
            && typeof revertSwatchStage === 'function') {
            revertSwatchStage();
        }
    }
}, true);

// ===== SHOKKER API - Server Connectivity (v4.0 - Build 19: Origin-Based) =====
/** @namespace ShokkerAPI - Central API client for all server communication */
const ShokkerAPI = {
    // Build 19 FIX: Use the page's own origin instead of scanning ports.
    baseUrl: window.location.origin || 'http://localhost:5001',
    online: false,
    config: null,
    _renderAbort: null,
    _renderInProgress: false, // [16] dedup guard for render requests
    _portDiscovered: !!(window.location.origin && window.location.protocol === 'http:'),

    /**
     * Discover the server port. Uses page origin for HTTP, falls back to port scanning. // [46]
     * @returns {Promise<Object|null>} Server status data or null
     */
    async discoverPort() {
        // Build 19: If loaded from HTTP (Electron app), the origin IS the server - no scanning needed
        if (window.location.protocol === 'http:') {
            this.baseUrl = window.location.origin;
            this._portDiscovered = true;
            console.log(`[ShokkerAPI] Using page origin: ${this.baseUrl} (no port scan needed)`);
            try { // [1] try/catch around fetch
                const res = await fetch(this.baseUrl + '/status', { signal: AbortSignal.timeout(API_TIMEOUT_STATUS_MS) }); // [44] named constant
                return await safeParseJSON(res, 'status check'); // [13] safe JSON parse
            } catch (e) {
                console.warn('[ShokkerAPI] Origin status check failed:', e.message);
                return null;
            }
        }
        // Fallback: file:// or dev mode - scan the SPB ports first, then old dev ports.
        const fallbackPorts = [59876, 59877, 59878, 59879, 60876, 60877, 60878, 60879, 61876];
        for (let p = 5000; p <= 5010; p++) fallbackPorts.push(p);
        for (const p of fallbackPorts) {
            try { // [2] try/catch around fetch
                const url = `http://localhost:${p}/status`;
                const res = await fetch(url, { signal: AbortSignal.timeout(API_TIMEOUT_PORT_SCAN_MS) }); // [44] named constant
                const data = await safeParseJSON(res, 'port scan'); // [14] safe JSON parse
                if (data.status === 'online') {
                    this.baseUrl = `http://localhost:${p}`;
                    this._portDiscovered = true;
                    console.log(`[ShokkerAPI] Server found on port ${p} (scan fallback)`);
                    return data;
                }
            } catch { /* try next port */ }
        }
        return null;
    },

    /**
     * Check server status and update UI. Discovers port on first call. // [47]
     * @returns {Promise<Object|null>} Status data or null if offline
     */
    async checkStatus() {
        try { // [3] try/catch around fetch
            // First call: discover which port the server is on
            if (!this._portDiscovered) {
                const discovered = await this.discoverPort();
                if (discovered) {
                    this.online = true;
                    this.config = discovered.config || null;
                    this._lastStatusData = discovered;
                    if (discovered.license) {
                        licenseActive = discovered.license.active;
                        if (typeof updateLicenseUI === 'function') updateLicenseUI(discovered.license);
                    }
                    // [IMP] Connection status + version mismatch detection
                    ConnectionStatus.set('online');
                    checkServerVersion(discovered);
                    this.updateUI();
                    return discovered;
                }
                this.online = false;
                this.config = null;
                ConnectionStatus.set('offline');
                this.updateUI();
                return null;
            }
            const res = await fetch(this.baseUrl + '/status', { signal: AbortSignal.timeout(API_TIMEOUT_STATUS_MS) }); // [6] timeout
            const data = await safeParseJSON(res, 'status check'); // [14] safe JSON parse
            const _wasOffline = !this.online;
            this.online = data.status === 'online';
            // [2026-06-12 preview-deadlock fix] offline->online transition: the
            // live preview was silently skipping while offline, so kick one
            // fresh preview now that the server is reachable again.
            if (_wasOffline && this.online && typeof window.spbKickLivePreview === 'function') {
                try { window.spbKickLivePreview(); } catch (_) { /* never break status */ }
            }
            this.config = data.config || null;
            this._lastStatusData = data;
            // Sync license state from server status
            if (data.license) {
                licenseActive = data.license.active;
                if (typeof updateLicenseUI === 'function') updateLicenseUI(data.license);
            }
            // [IMP] Update central connection status + version check
            ConnectionStatus.set(this.online ? 'online' : 'offline');
            checkServerVersion(data);
            this.updateUI();
            return data;
        } catch (e) {
            this.online = false;
            this.config = null;
            this._portDiscovered = false; // Re-discover on next check
            ConnectionStatus.set('reconnecting');
            this.updateUI();
            return null;
        }
    },

    /**
     * Cheap steady-state liveness probe. The full /status payload includes the
     * entire finish/pattern catalog and is only needed for initial discovery or
     * reconnect. Keeping background polls on /health avoids repeatedly parsing
     * that catalog while the owner is driving in iRacing.
     * @returns {Promise<Object|null>} Small health payload, or null if offline
     */
    async checkStatusLight() {
        try {
            if (!this._portDiscovered) return this.checkStatus();
            const res = await fetch(this.baseUrl + '/health', {
                signal: AbortSignal.timeout(API_TIMEOUT_LIGHT_MS),
                cache: 'no-store'
            });
            const data = await safeParseJSON(res, 'health check');
            const wasOffline = !this.online;
            this.online = !!(res.ok && data && (data.ok || data.status === 'ok'));

            // A successful reconnect needs one full refresh so config, license,
            // version, and live-link state cannot remain stale.
            if (wasOffline && this.online) return this.checkStatus();

            ConnectionStatus.set(this.online ? 'online' : 'offline');
            if (this.online) checkServerVersion(data);
            this.updateUI();
            return this.online ? data : null;
        } catch (e) {
            this.online = false;
            this._portDiscovered = false;
            ConnectionStatus.set('reconnecting');
            this.updateUI();
            return null;
        }
    },

    /** Cancel the current in-flight render request. // [48]
     * [IMP] Render aborting UI — also propagate to other in-flight requests + reset queue.
     */
    cancelRender(reason) {
        if (this._renderAbort) {
            try { this._renderAbort.abort(reason || new DOMException('User cancelled', 'AbortError')); } catch (_) { this._renderAbort.abort(); }
            this._renderAbort = null;
            this._renderInProgress = false; // [17] clear dedup flag
            console.log('[ShokkerAPI] Render cancelled by user');
        }
        // [IMP] Visual feedback — flash the render button red briefly
        const btn = document.getElementById('btnRender');
        if (btn) {
            btn.classList.add('cancelled');
            btn.textContent = 'CANCELLED';
            setTimeout(() => { if (btn) btn.classList.remove('cancelled'); }, 600);
        }
    },

    /**
     * Send a render request to the server. // [49]
     * @param {string} paintFile - Path to the source paint TGA
     * @param {Array} zones - Array of zone configuration objects
     * @param {string} iracingId - iRacing customer ID
     * @param {number} [seed=51] - Random seed
     * @param {boolean} [liveLink=false] - Whether to push to iRacing live
     * @param {Object} [extras] - Optional extras (wear, export, output, decals, etc.)
     * @returns {Promise<Object>} Render result data
     */
    async render(paintFile, zones, iracingId, seed, liveLink, extras) {
        // [18] Request deduplication - prevent double-render from rapid clicks
        if (this._renderInProgress) {
            console.warn('[ShokkerAPI] Render already in progress, ignoring duplicate request');
            return { error: 'Render already in progress. Please wait.' };
        }
        this._renderInProgress = true;

        // Create AbortController for this render
        this._renderAbort = new AbortController();
        const useCustomNumber = document.getElementById('useCustomNumberCheckbox')?.checked ?? true;
        const body = {
            paint_file: paintFile,
            zones: zones,
            iracing_id: iracingId,
            seed: seed || 51,
            live_link: liveLink || false,
            use_custom_number: useCustomNumber,
        };
        // Optional extras: wear, export, output_dir, imported spec, decal data
        if (extras) {
            if (extras.wear_level !== undefined) body.wear_level = extras.wear_level;
            if (extras.export_zip) body.export_zip = true;
            if (extras.dual_spec) { body.dual_spec = true; body.night_boost = extras.night_boost || 0.7; }
            if (extras.output_dir) body.output_dir = extras.output_dir;
            if (extras.import_spec_map) body.import_spec_map = extras.import_spec_map;
            if (extras.paint_image_base64) body.paint_image_base64 = extras.paint_image_base64;
            if (extras.decal_mask_base64) body.decal_mask_base64 = extras.decal_mask_base64;
            // SmartSep (flat-image protect, 2026-06-26): keep numbers & sponsors on render
            // when the user enabled protection in the Layers-column Smart Separate panel.
            // Only fills in when nothing else already set a decal mask (won't clobber fleet/season).
            try {
                if (!body.decal_mask_base64 && window.SmartSep && typeof window.SmartSep.renderPayload === 'function') {
                    var _ssp = window.SmartSep.renderPayload();
                    if (_ssp && _ssp.decal_mask_base64) body.decal_mask_base64 = _ssp.decal_mask_base64;
                }
            } catch (_ssErr) {}
            if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;
            if (extras.stamp_image_base64) body.stamp_image_base64 = extras.stamp_image_base64;
            if (extras.stamp_spec_finish) body.stamp_spec_finish = extras.stamp_spec_finish;
        }
        this.resetStatusInterval(); // Reset polling backoff on every render
        let renderSignal = this._renderAbort ? this._renderAbort.signal : undefined;
        let renderTimeoutId = null;
        let renderTimeoutController = null;
        if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.any === 'function') {
            renderSignal = AbortSignal.any([this._renderAbort.signal, AbortSignal.timeout(API_TIMEOUT_RENDER_MS)]);
        } else {
            renderTimeoutController = new AbortController();
            renderTimeoutId = setTimeout(() => {
                try {
                    renderTimeoutController.abort(new DOMException('Render timed out', 'TimeoutError'));
                } catch (_) {
                    renderTimeoutController.abort();
                }
            }, API_TIMEOUT_RENDER_MS);
            this._renderAbort.signal.addEventListener('abort', () => {
                try {
                    renderTimeoutController.abort(this._renderAbort.signal.reason);
                } catch (_) {
                    renderTimeoutController.abort();
                }
            }, { once: true });
            renderSignal = renderTimeoutController.signal;
        }
        try { // [4] try/catch around fetch
            const res = await fetch(this.baseUrl + '/render', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: renderSignal,
            });
            const data = await safeParseJSON(res, 'render'); // [15] safe JSON parse
            if (!res.ok && !data.error) data.error = `Server returned HTTP ${res.status}: ${res.statusText || 'unknown'}`; // [36] specific error
            return data;
        } finally {
            if (renderTimeoutId) clearTimeout(renderTimeoutId);
            this._renderInProgress = false; // [19] always clear dedup flag
        }
    },

    /**
     * SHOKKE Spec Sculpt — JSON ``paint_file`` path (same as Source Paint on desktop).
     * @param {Object} body — paint_file, seed, chromatic_shift, iracing_id, use_custom_number,
     *   output_dir, live_link, deploy_car_folder (optional iRacing car folder basename).
     */
    async specSculptGenerate(body) {
        const res = await fetch(this.baseUrl + '/api/spec-sculpt/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
            signal: typeof AbortSignal !== 'undefined' && AbortSignal.timeout
                ? AbortSignal.timeout(API_TIMEOUT_GENERAL_MS)
                : undefined,
        });
        const data = await safeParseJSON(res, 'spec-sculpt');
        if (!res.ok && !data.error) {
            data.error = `Server returned HTTP ${res.status}: ${res.statusText || 'unknown'}`;
        }
        return data;
    },

    /**
     * Export current design to Photoshop exchange format. // [50]
     * @param {string} carFileName - Name for the exported car file
     * @param {string} exchangeFolder - Path to the exchange directory
     * @param {string} paintFile - Source paint file path
     * @param {Array} zones - Zone configuration array
     * @param {Object} [extras] - Optional extras
     * @returns {Promise<Object>} Export result
     */
    async exportToPhotoshop(carFileName, exchangeFolder, paintFile, zones, extras) {
        const useCustomNumber = document.getElementById('useCustomNumberCheckbox')?.checked ?? true;
        const body = {
            paint_file: paintFile,
            zones: zones,
            seed: 51,
            car_file_name: carFileName,
            use_custom_number: useCustomNumber,
        };
        if (exchangeFolder && exchangeFolder.trim()) body.exchange_folder = exchangeFolder.trim();
        if (extras) {
            if (extras.import_spec_map) body.import_spec_map = extras.import_spec_map;
            if (extras.paint_image_base64) body.paint_image_base64 = extras.paint_image_base64;
            if (extras.decal_mask_base64) body.decal_mask_base64 = extras.decal_mask_base64;
            // SmartSep (flat-image protect, 2026-06-26): keep numbers & sponsors on render
            // when the user enabled protection in the Layers-column Smart Separate panel.
            // Only fills in when nothing else already set a decal mask (won't clobber fleet/season).
            try {
                if (!body.decal_mask_base64 && window.SmartSep && typeof window.SmartSep.renderPayload === 'function') {
                    var _ssp = window.SmartSep.renderPayload();
                    if (_ssp && _ssp.decal_mask_base64) body.decal_mask_base64 = _ssp.decal_mask_base64;
                }
            } catch (_ssErr) {}
            if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;
            if (extras.stamp_image_base64) body.stamp_image_base64 = extras.stamp_image_base64;
            if (extras.stamp_spec_finish) body.stamp_spec_finish = extras.stamp_spec_finish;
        }
        try { // [5] try/catch around fetch
            const res = await fetch(this.baseUrl + '/api/export-to-photoshop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: AbortSignal.timeout(API_TIMEOUT_RENDER_MS), // [8] timeout for export (can be slow)
            });
            const data = await safeParseJSON(res, 'Photoshop export'); // [15] safe JSON parse
            if (!res.ok && !data.error) data.error = `Export failed: server returned HTTP ${res.status}`; // [37] specific error
            return data;
        } catch (e) {
            return { error: classifyFetchError(e, 'Photoshop export') }; // [11] user-friendly error
        }
    },

    /**
     * Get the Photoshop exchange root directory from server config. // [50]
     * @returns {Promise<string>} Exchange root path or empty string
     */
    async getPhotoshopExchangeRoot() {
        // [22] Cache this since it rarely changes
        return cachedFetch('ps_exchange_root', async () => {
            try { // [5] try/catch
                const res = await fetch(this.baseUrl + '/api/photoshop-exchange-root', {
                    signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS) // [9] timeout
                });
                const data = await safeParseJSON(res, 'PS exchange root');
                return data.path || '';
            } catch (e) {
                console.warn('[ShokkerAPI] Failed to get PS exchange root:', e.message);
                return '';
            }
        });
    },

    /**
     * Reset the paint backup to factory state.
     * @param {string} paintFile - Paint file path
     * @param {string} iracingId - iRacing ID
     * @returns {Promise<Object>} Result
     */
    async resetBackup(paintFile, iracingId) {
        try { // [5] try/catch
            const res = await fetch(this.baseUrl + '/reset-backup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paint_file: paintFile, iracing_id: iracingId }),
                signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [10] timeout
            });
            return await safeParseJSON(res, 'backup reset');
        } catch (e) {
            return { error: classifyFetchError(e, 'Backup reset') }; // [12] user-friendly error
        }
    },

    /**
     * Save configuration to server.
     * @param {Object} cfg - Configuration object to save
     * @returns {Promise<Object>} Save result
     */
    async saveConfig(cfg) {
        try { // [5] try/catch
            const res = await fetch(this.baseUrl + '/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg),
                signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [10] timeout
            });
            return await safeParseJSON(res, 'config save');
        } catch (e) {
            return { error: classifyFetchError(e, 'Config save') }; // [12] user-friendly error
        }
    },

    /** Update the UI to reflect current online/offline state. */
    updateUI() {
        const dot = document.getElementById('serverStatus'); // [53] null checks throughout
        const btn = document.getElementById('btnRender');
        const llRow = document.getElementById('liveLinkRow');
        if (dot) {
            dot.className = 'server-status ' + (this.online ? 'online' : 'offline');
            dot.title = this.online ? 'Server online' : 'Engine offline - restarting automatically';
        }
        if (btn) {
            btn.textContent = this.online ? 'RENDER' : 'RENDER (Offline)';
            btn.style.opacity = this.online ? '1' : '0.5';
        }
        if (llRow && this.config) {
            llRow.style.display = 'flex';
            const badge = document.getElementById('liveLinkBadge');
            if (!this._liveLinkSynced) {
                const cb = document.getElementById('liveLinkCheckbox');
                if (cb) { cb.checked = this.config.live_link_enabled || false; this._liveLinkSynced = true; }
            }
            if (badge) badge.style.display = this.config.live_link_enabled ? 'inline' : 'none';
        }
        // Sync car file naming checkbox from saved config (only on first load, not every poll)
        if (this.config && !this._customNumberSynced) {
            const cnCb = document.getElementById('useCustomNumberCheckbox');
            if (cnCb && typeof this.config.use_custom_number === 'boolean') { cnCb.checked = this.config.use_custom_number; this._customNumberSynced = true; } // 2026-10-02: an older server never sent the field, and `undefined !== false` forced Custom Number ON at every launch (sim-stamped users silently rendered car_num_<id>.tga)
            // SPB-SIMPLIFY-2026-07-18: the header's mutually-exclusive twin (Sim-Stamped Number)
            const simCb = document.getElementById('useSimStampedCheckbox');
            if (simCb && cnCb) simCb.checked = !cnCb.checked;
        }
    },

    /** Start periodic status polling with exponential backoff. */
    startPolling() {
        this._statusInterval = POLL_INITIAL_INTERVAL_MS; // [45] named constant
        this.checkStatus();
        const statusPoll = () => {
            this.checkStatusLight().then(() => {
                // Slow down polling when idle (no recent renders)
                this._statusInterval = Math.min(this._statusInterval * POLL_BACKOFF_FACTOR, POLL_MAX_INTERVAL_MS); // [45] named constants
                setTimeout(statusPoll, this._statusInterval);
            }).catch(() => {
                setTimeout(statusPoll, this._statusInterval);
            });
        };
        setTimeout(statusPoll, this._statusInterval);
    },

    /** Reset status polling interval to fast rate (called after renders). */
    resetStatusInterval() {
        this._statusInterval = POLL_INITIAL_INTERVAL_MS; // [45] named constant
    }
};

// ===== DISK CLEANUP =====
/**
 * Delete old render job folders to free disk space. // [46]
 * Shows confirmation dialog before proceeding.
 */
async function cleanupOldRenders() {
    if (!ShokkerAPI.online) { showToast(SPB_ENGINE_OFFLINE_MSG, true); return; } // [38] specific error
    if (!confirm('Delete ALL old render job folders from output/? This frees disk space but removes cached render results.')) return;
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/cleanup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
            signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [8] timeout
        });
        const data = await safeParseJSON(res, 'cleanup'); // [15] safe parse
        if (data.success) {
            showToast(`Cleaned ${data.deleted} render jobs, freed ${data.freed_mb}MB`);
        } else {
            showToast('Cleanup failed: ' + (data.error || 'unknown server error'), true); // [39] specific
        }
    } catch (e) {
        showToast(classifyFetchError(e, 'Disk cleanup'), true); // [12] user-friendly error
    }
}

// ===== HELMET / SUIT BROWSE =====
function browseHelmetFile(input) {
    if (input.files && input.files[0]) {
        // For local file browsing, extract the path
        const fileName = input.files[0].name;
        // Try to build a path from the paint file's directory
        const paintFile = document.getElementById('paintFile').value.trim();
        if (paintFile) {
            const dir = paintFile.replace(/[/\\][^/\\]+$/, '');
            document.getElementById('helmetFile').value = dir + '/' + fileName;
        } else {
            document.getElementById('helmetFile').value = fileName;
        }
        showToast(`Helmet paint: ${fileName}`);
    }
}

function browseSuitFile(input) {
    if (input.files && input.files[0]) {
        const fileName = input.files[0].name;
        const paintFile = document.getElementById('paintFile').value.trim();
        if (paintFile) {
            const dir = paintFile.replace(/[/\\][^/\\]+$/, '');
            document.getElementById('suitFile').value = dir + '/' + fileName;
        } else {
            document.getElementById('suitFile').value = fileName;
        }
        showToast(`Suit paint: ${fileName}`);
    }
}

// ===== WEAR SLIDER =====
function updateWearDisplay(val) {
    const v = parseInt(val, 10);
    const valueEl = document.getElementById('wearValue');
    const descEl = document.getElementById('wearDesc');
    if (valueEl) valueEl.textContent = v;
    if (descEl) {
        if (v === 0) descEl.textContent = 'Fresh / Factory New';
        else if (v <= 10) descEl.textContent = 'Light use - micro-scratches only';
        else if (v <= 20) descEl.textContent = 'Weekend warrior - clearcoat fading';
        else if (v <= 40) descEl.textContent = 'Season worn - paint chips starting';
        else if (v <= 60) descEl.textContent = 'Battle scarred - visible edge wear';
        else if (v <= 80) descEl.textContent = 'Heavily worn - significant damage';
        else descEl.textContent = 'Destroyed - maximum wear & tear';
    }
}

function toggleNightBoostSlider() {
    const checked = document.getElementById('dualSpecCheckbox')?.checked;
    const row = document.getElementById('nightBoostRow');
    if (row) row.style.display = checked ? 'block' : 'none';
}

// ===== PBR MATERIAL VISUALIZER =====
function togglePbrVisualizer() {
    const sec = document.getElementById('pbrVisualizerSection');
    if (!sec) return;
    const show = sec.style.display === 'none';
    sec.style.display = show ? 'block' : 'none';
    if (show) updatePbrBall();
}

function setPbrPreset(m, r, c) {
    document.getElementById('pbrMetallic').value = m;
    document.getElementById('pbrRoughness').value = r;
    document.getElementById('pbrClearcoat').value = c;
    updatePbrBall();
}

function updatePbrBall() {
    const canvas = document.getElementById('pbrBallCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h / 2, radius = w / 2 - 4;

    const metallic = parseInt(document.getElementById('pbrMetallic').value);
    const roughness = parseInt(document.getElementById('pbrRoughness').value);
    const clearcoat = parseInt(document.getElementById('pbrClearcoat').value);

    document.getElementById('pbrMetallicVal').textContent = metallic;
    document.getElementById('pbrRoughnessVal').textContent = roughness;
    document.getElementById('pbrClearcoatVal').textContent = clearcoat;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // PBR ball simulation
    const mf = metallic / 255;   // 0-1
    const rf = roughness / 255;   // 0-1
    // iRacing clearcoat: 16=max shine, higher=duller
    const ccf = clearcoat <= 16 ? (1 - clearcoat / 16) : Math.max(0, 1 - (clearcoat - 16) / 239);

    const imgData = ctx.createImageData(w, h);
    const data = imgData.data;

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const dx = (x - cx) / radius;
            const dy = (y - cy) / radius;
            const dist2 = dx * dx + dy * dy;
            if (dist2 > 1) continue;

            const nz = Math.sqrt(1 - dist2);
            const nx = dx, ny = dy;

            // Light direction (upper-left)
            const lx = -0.4, ly = -0.6, lz = 0.7;
            const llen = Math.sqrt(lx * lx + ly * ly + lz * lz);
            const ndotl = Math.max(0, (nx * lx + ny * ly + nz * lz) / llen);

            // Specular (Blinn-Phong approximation)
            const hx = lx, hy = ly, hz = lz + 1;
            const hlen = Math.sqrt(hx * hx + hy * hy + hz * hz);
            const ndoth = Math.max(0, (nx * hx + ny * hy + nz * hz) / hlen);
            const specPower = Math.max(4, 200 * (1 - rf));
            const spec = Math.pow(ndoth, specPower);

            // Fresnel effect (metallic surfaces reflect more at glancing angles)
            const fresnel = Math.pow(1 - nz, 3) * mf;

            // Base color (use neutral gray as paint proxy)
            const baseColor = 0.45;
            // Metallic dims diffuse, boosts reflection
            const diffuse = baseColor * ndotl * (1 - mf * 0.6);
            const reflection = (spec * (0.3 + mf * 0.7) + fresnel * 0.4) * (1 - rf * 0.8);

            // Clearcoat adds a secondary specular highlight
            const ccSpec = ccf > 0 ? Math.pow(ndoth, 300) * ccf * 0.8 : 0;

            let r = Math.min(1, diffuse + reflection + ccSpec);
            let g = Math.min(1, diffuse + reflection + ccSpec);
            let b = Math.min(1, diffuse + reflection * 1.05 + ccSpec * 1.1);

            // Metallic tint - shift toward blue-ish for high metallic
            if (mf > 0.5) {
                const tint = (mf - 0.5) * 0.15;
                r -= tint * 0.3;
                b += tint * 0.2;
            }

            // Edge darkening (ambient occlusion approximation)
            const ao = 0.3 + 0.7 * nz;
            r *= ao; g *= ao; b *= ao;

            const idx = (y * w + x) * 4;
            data[idx] = Math.min(255, Math.max(0, r * 255)) | 0;
            data[idx + 1] = Math.min(255, Math.max(0, g * 255)) | 0;
            data[idx + 2] = Math.min(255, Math.max(0, b * 255)) | 0;
            data[idx + 3] = 255;
        }
    }
    ctx.putImageData(imgData, 0, 0);

    // Draw border circle
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.stroke();
}

// ===== FLEET MODE =====
let fleetCars = [];
let fleetModeActive = false;

function _showRetiredBatchModeToast(modeLabel) {
    showToast(`${modeLabel} is disabled in this booth build. Use the normal single-car paint workflow instead.`, 'warn');
}

function toggleFleetMode() {
    fleetModeActive = false;
    const panel = document.getElementById('fleetPanel');
    const btn = document.getElementById('btnFleetToggle');
    if (panel) {
        panel.style.display = 'none';
        panel.style.marginBottom = '';
    }
    if (btn) {
        btn.style.background = 'transparent';
        btn.textContent = 'Fleet Mode';
    }
    _showRetiredBatchModeToast('Fleet mode');
    return false;
}

function addFleetCar() {
    const paintFile = document.getElementById('paintFile')?.value || '';
    const id = document.getElementById('iracingId')?.value || '';
    fleetCars.push({ name: `Car ${fleetCars.length + 1}`, paintFile: paintFile, iracingId: id });
    renderFleetList();
}

function removeFleetCar(idx) {
    fleetCars.splice(idx, 1);
    renderFleetList();
}

function renderFleetList() {
    const container = document.getElementById('fleetList');
    const count = document.getElementById('fleetCount');
    if (count) count.textContent = `(${fleetCars.length} cars)`;
    if (!container) return;
    // FIVE-HOUR SHIFT Win H8 (security): pre-fix this interpolated user-controlled
    // car.name / car.paintFile / car.iracingId raw into value="..." attributes.
    // A painter (or injected paste) typing `"><img src=x onerror=alert(1)>` would
    // break the attribute and execute script. Same XSS class as marathon #68
    // (renderLayerPanel) and #69 (history gallery). Escape every user-string
    // before interpolation.
    const _escFleet = (typeof escapeHtml === 'function') ? escapeHtml : (s => String(s == null ? '' : s));
    container.innerHTML = fleetCars.map((car, i) => `
        <div class="batch-entry">
            <span style="color: var(--accent-gold); font-weight: 600; min-width: 14px;">${i + 1}</span>
            <input type="text" value="${_escFleet(car.name)}" onchange="fleetCars[${i}].name=this.value" placeholder="Car name" style="max-width: 80px;">
            <input type="text" value="${_escFleet(car.paintFile)}" onchange="fleetCars[${i}].paintFile=this.value" placeholder="Paint TGA path" title="Full path to paint TGA">
            <input type="text" value="${_escFleet(car.iracingId)}" onchange="fleetCars[${i}].iracingId=this.value" placeholder="ID" style="max-width: 45px;" title="iRacing ID">
            <span class="batch-remove" onclick="removeFleetCar(${i})" title="Remove car">&times;</span>
        </div>
    `).join('');
}

/**
 * Render all cars in the fleet queue sequentially. // [49]
 * Shows progress and results for each car as it completes.
 */
async function doFleetRender() {
    _showRetiredBatchModeToast('Fleet mode');
    return;
    if (!ShokkerAPI.online) { showToast(SPB_ENGINE_OFFLINE_MSG, true); return; } // [38] specific
    if (fleetCars.length === 0) { showToast('Add at least one car to the fleet!', true); return; }

    // BUG #66 (Neidhart, HIGH): pre-fix, fleet loop called ShokkerAPI.render
    // with car.paintFile even when that was '' — server 400'd silently per
    // car and the painter saw only "FAILED" with no reason. Also, two cars
    // with the same paintFile would silently clobber each other's render
    // output. Validate up-front and fail fast before starting the batch.
    const _fleetMissing = fleetCars
        .map((c, i) => ({ c, i }))
        .filter(({ c }) => !((c.paintFile || '').trim()));
    if (_fleetMissing.length) {
        const names = _fleetMissing.map(({ c, i }) => (c.name || ('Car ' + (i + 1)))).join(', ');
        showToast('Fleet render aborted: paintFile is empty for ' + names + '. Fill in the TGA path for every car.', true);
        return;
    }
    const _fleetSeen = new Map();
    const _fleetDupes = [];
    fleetCars.forEach((c, i) => {
        const key = (c.paintFile || '').trim().toLowerCase();
        if (_fleetSeen.has(key)) _fleetDupes.push({ first: _fleetSeen.get(key), second: i });
        else _fleetSeen.set(key, i);
    });
    if (_fleetDupes.length) {
        const { first, second } = _fleetDupes[0];
        const _a = fleetCars[first].name || ('Car ' + (first + 1));
        const _b = fleetCars[second].name || ('Car ' + (second + 1));
        if (!confirm('Cars "' + _a + '" and "' + _b + '" share the same paintFile. The second render will OVERWRITE the first on disk (iRacing paint folder or output_dir). Continue anyway?')) {
            showToast('Fleet render cancelled — resolve duplicate paintFile paths first.', true);
            return;
        }
    }

    const btn = document.getElementById('btnFleetRender');
    const progress = document.getElementById('fleetProgress');
    const results = document.getElementById('fleetResults');
    if (btn) { btn.disabled = true; btn.textContent = 'Rendering Fleet...'; } // [27] loading indicator + null check
    if (progress) progress.style.display = 'block'; // [55] null check
    if (results) results.innerHTML = ''; // [55] null check

    const validZones = zones.filter((z, i) => !(typeof _isSuppressedLegacyZone === 'function' && _isSuppressedLegacyZone(z, i)) && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || (_renderMaskHasPixels(z.regionMask))));
    if (validZones.length === 0) { showToast('Set up zones first!', true); btn.disabled = false; progress.style.display = 'none'; return; }

    const serverZones = validZones.map(z => {
        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
        _applyPatternMaterialControls(zoneObj, z);
        _applyCustomIntensity(zoneObj, z);
        _applyZoneMaterialStack(zoneObj, z);
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fc = _resolveFinishColors(z.finish); if (_fc) zoneObj.finish_colors = _fc; if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        if (z.specShiftR || z.specShiftG || z.specShiftB) zoneObj.spec_channel_shift = [Number(z.specShiftR) || 0, Number(z.specShiftG) || 0, Number(z.specShiftB) || 0];
        _applySpecMaterialRemap(zoneObj, z);
        _applySpecMaterialOverride(zoneObj, z);
        _applySpecLightingMask(zoneObj, z);
        // BOIL THE OCEAN drift hunt #4: base color mode header → single helper.
        _applyBaseColorMode(zoneObj, z);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.patternStrengthMapEnabled && z.patternStrengthMap && typeof encodeStrengthMapRLE === 'function') { zoneObj.pattern_strength_map = encodeStrengthMapRLE(z.patternStrengthMap); }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) { zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5))); zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5))); zoneObj.pattern_flip_h = !!z.patternFlipH; zoneObj.pattern_flip_v = !!z.patternFlipV; }
        if (z.patternPlacement === 'fit' || z.patternFitZone || _zoneShouldFitIntoApplyArea(z)) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge !== false) zoneObj.hard_edge = true;  // [SPB 2026-06-02 owner] hard edge is the DEFAULT; only an explicit uncheck (false) sends soft
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) { zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5))); zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5))); zoneObj.base_rotation = Number(z.baseRotation ?? 0); zoneObj.base_flip_h = !!z.baseFlipH; zoneObj.base_flip_v = !!z.baseFlipV; }
        { const _sr = Number(z.specRotation ?? 0); const _ss = (window._spbResolveSpecScale ? window._spbResolveSpecScale(z) : Number(z.specScale ?? z.baseScale ?? 1)); if (_sr !== 0) zoneObj.spec_rotation = _sr; if (_ss !== 1 || (window._spbSpecIndependent && window._spbSpecIndependent(z))) zoneObj.spec_scale = _ss; }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // BOIL THE OCEAN drift hunt #5: 5-tier spec_pattern_stack loop → single helper.
        _applyAllSpecPatternStacks(zoneObj, z);
        window.SPBZoneMaterialInstancePayload?.apply(zoneObj, z);
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        _applyBlendBaseOverlay(zoneObj, z);
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // BOIL THE OCEAN drift hunt #2: 4 base overlay blocks → single helper.
        // See _applyAllExtraBaseOverlays for canonical contract.
        _applyAllExtraBaseOverlays(zoneObj, z);
        // 2026-04-23 HEENAN FAMILY 6h Alpha-hardening Iter 6 (Animal): pre-fix,
        // doFleetRender's zone mapper emitted no region_mask / spatial_mask /
        // source_layer_mask at all. Same bug class as MARATHON #27 (Bockwinkel)
        // for doSeasonRender — never patched in the fleet builder. Painters
        // who set source-layer / region restrictions saw every car in the fleet
        // rendered with the zone painted across the WHOLE car body. Block
        // copied verbatim from doSeasonRender (same fail-closed contract:
        // dangling source → empty all-zero mask + console.warn + throttled
        // toast keyed on zone name). Pinned by
        // tests/test_regression_fleet_render_restriction_mask_parity.py.
        _encodeZoneApplyMasks(zoneObj, z);
        const hasSpatialRefinement = _renderMaskHasPixels(z.spatialMask);
        const shouldPriorityOverride = !!(
            hasSpatialRefinement &&
            typeof window !== 'undefined' &&
            typeof window._zoneShouldRequestPriorityOverride === 'function' &&
            window._zoneShouldRequestPriorityOverride(z)
        );
        if (shouldPriorityOverride) zoneObj.priority_override = true;
        // Source-layer restriction (same fail-closed contract as doRender,
        // doSeasonRender, and PS export: empty all-zero mask + console.warn
        // + one-shot user toast keyed on zone name).
        if ((z.sourceLayer || (Array.isArray(z.sourceLayers) && z.sourceLayers.length)) && typeof _psdLayers !== 'undefined' && typeof encodeRegionMaskRLE === 'function') {
            // [SPB-MULTILAYER 2026-08-21] fail-closed union across the restricted set.
            const _slu = (typeof window.getZoneSourceLayersUnionMask === 'function')
                ? window.getZoneSourceLayersUnionMask(z, (document.getElementById('paintCanvas')?.width || 2048), (document.getElementById('paintCanvas')?.height || 2048))
                : null;
            const srcLayer = _slu ? _slu.firstLayer : _psdLayers.find(l => l.id === z.sourceLayer);
            const pc = document.getElementById('paintCanvas');
            const w = pc?.width || 2048;
            const h = pc?.height || 2048;
            _attachSourceLayerCacheHints(zoneObj, z, srcLayer, w, h);
            // [ULTRACODE 2026-08-22 synthesis #1+#6] union first (a dangling
            // ids[0] must not swallow a SURVIVING union of sibling layers —
            // doRender's structure is the reference), then fail CLOSED on any
            // unresolvable restriction (the old hiddenCount>0 gate let a
            // hidden PARENT GROUP / img-less layer / boot race ship NO mask =
            // the zone painted the whole car). Legacy single-layer fallback
            // only when no union machinery was involved at all.
            if (_slu && _slu.union) {
                zoneObj.source_layer_mask = encodeRegionMaskRLE(_slu.union, w, h);
            } else if (_slu && _slu.requested > 0) {
                zoneObj.source_layer_mask = encodeRegionMaskRLE(new Uint8Array(w * h), w, h);
                if (_slu.hiddenCount > 0) {
                    try { if (typeof window._spbHiddenSourceToast === 'function') window._spbHiddenSourceToast(z, _slu); } catch (_) {}
                }
            } else if (!srcLayer) {
                try {
                    console.warn('[SPB][source_layer] zone "%s" references missing layer "%s" — emitting empty mask (zone will paint nothing until source is restored or sourceLayer is cleared)',
                        z.name || '?', z.sourceLayer);
                } catch (_) {}
                try {
                    if (typeof window !== 'undefined') {
                        window._SPB_DANGLING_SOURCE_TOASTED = window._SPB_DANGLING_SOURCE_TOASTED || {};
                        const _key = (z.name || '?') + '|' + z.sourceLayer;
                        if (!window._SPB_DANGLING_SOURCE_TOASTED[_key] && typeof showToast === 'function') {
                            window._SPB_DANGLING_SOURCE_TOASTED[_key] = true;
                            showToast(`Zone "${z.name || ''}" source layer is missing — painting nothing. Re-restrict or clear source.`, 'warn');
                        }
                    }
                } catch (_) {}
                const _emptyMask = new Uint8Array(w * h);
                zoneObj.source_layer_mask = encodeRegionMaskRLE(_emptyMask, w, h);
            } else if (typeof window.getLayerVisibleContributionMask === 'function') {
                const visibleMask = window.getLayerVisibleContributionMask(srcLayer, w, h);
                if (visibleMask) zoneObj.source_layer_mask = encodeRegionMaskRLE(visibleMask, w, h);
            }
        }
        return zoneObj;
    });

    // 2026-04-18 MARATHON bug #31 (Hawk, HIGH): pre-fix, doFleetRender
    // only emitted wear_level + import_spec_map in extras. EVERY car in
    // the fleet lost: decals (with spec finishes), decal mask, PSD live
    // composite, stamps (with finish), helmet/suit files, exportZip,
    // dualSpec, nightBoost, output_dir. Single-car render had all of
    // these; the fleet had none. Fleet output was therefore a
    // stripped-down alternate-reality render. This now mirrors doRender's
    // full extras construction.
    const extras = {};
    const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
    if (wearLevel > 0) extras.wear_level = wearLevel;
    const fleetSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
    if (fleetSpecPath) extras.import_spec_map = fleetSpecPath;
    const _fleetOutputDir = document.getElementById('outputDir')?.value.trim();
    const _fleetHelmetFile = document.getElementById('helmetFile')?.value.trim();
    const _fleetSuitFile = document.getElementById('suitFile')?.value.trim();
    const _fleetExportZip = document.getElementById('exportZipCheckbox')?.checked || false;
    const _fleetDualSpec = document.getElementById('dualSpecCheckbox')?.checked || false;
    if (_fleetOutputDir) extras.output_dir = _fleetOutputDir;
    if (_fleetHelmetFile) extras.helmet_paint_file = _fleetHelmetFile;
    if (_fleetSuitFile) extras.suit_paint_file = _fleetSuitFile;
    if (_fleetExportZip) extras.export_zip = true;
    if (_fleetDualSpec) {
        extras.dual_spec = true;
        extras.night_boost = parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7');
    }
    // Decals + per-decal spec finishes + decal mask.
    if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
        const _fleetComposite = compositeDecalsForRender();
        if (_fleetComposite) extras.paint_image_base64 = await canvasToBase64Async(_fleetComposite);
        if (typeof compositeDecalMaskForRender === 'function') {
            const _fleetMaskUrl = compositeDecalMaskForRender();
            if (_fleetMaskUrl) extras.decal_mask_base64 = _fleetMaskUrl;
        }
        const _fleetDecalSpecs = decalLayers
            .filter(dl => dl.visible && dl.specFinish && dl.specFinish !== 'none')
            .map(dl => ({ specFinish: dl.specFinish }));
        if (_fleetDecalSpecs.length > 0) extras.decal_spec_finishes = _fleetDecalSpecs;
    }
    // PSD layer composite if no decal composite ran and layers exist.
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0 &&
        !extras.paint_image_base64) {
        const _fleetPc = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
            ? window.buildLivePaintCompositeCanvas()
            : document.getElementById('paintCanvas');
        if (_fleetPc) extras.paint_image_base64 = await canvasToBase64Async(_fleetPc);
    }
    // Spec stamps + finish.
    if (typeof compositeStampsForRender === 'function' && typeof window.stampLayers !== 'undefined' && window.stampLayers.length > 0) {
        const _fleetStamp = compositeStampsForRender();
        if (_fleetStamp) {
            extras.stamp_image_base64 = await canvasToBase64Async(_fleetStamp);
            extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';
        }
    }

    for (let i = 0; i < fleetCars.length; i++) {
        const car = fleetCars[i];
        progress.textContent = `Rendering car ${i + 1}/${fleetCars.length}: ${car.name}...`;

        try {
            const result = await ShokkerAPI.render(car.paintFile, serverZones, car.iracingId, 51, false, extras);
            const urls = result.preview_urls || {};
            const paintUrl = Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet'));
            results.innerHTML += `
                <div class="batch-result-card">
                    ${paintUrl ? `<img src="${ShokkerAPI.baseUrl + paintUrl[1]}" alt="${car.name}">` : '<div style="height: 60px; background: #111; border-radius: 3px;"></div>'}
                    <div class="batch-result-name">${car.name}</div>
                </div>`;
        } catch (err) {
            results.innerHTML += `<div class="batch-result-card"><div class="batch-result-name" style="color: #ff4444;">FAILED: ${car.name}</div></div>`;
        }
    }

    if (progress) progress.textContent = `Fleet render complete! ${fleetCars.length} cars rendered.`; // [55] null check
    if (btn) { btn.disabled = false; btn.textContent = 'Render Fleet'; } // [29] restore button

}

// ===== SEASON MODE =====
let seasonJobs = [];
let seasonModeActive = false;

function toggleSeasonMode() {
    seasonModeActive = false;
    const panel = document.getElementById('seasonPanel');
    const btn = document.getElementById('btnSeasonToggle');
    if (panel) {
        panel.style.display = 'none';
        panel.style.marginBottom = '';
    }
    if (btn) {
        btn.style.background = 'transparent';
        btn.textContent = 'Season Mode';
    }
    _showRetiredBatchModeToast('Season mode');
    return false;
}

function addSeasonRace() {
    seasonJobs.push({ name: `Race ${seasonJobs.length + 1}`, wearLevel: 0 });
    renderSeasonList();
}

function removeSeasonRace(idx) {
    seasonJobs.splice(idx, 1);
    renderSeasonList();
}

function renderSeasonList() {
    const container = document.getElementById('seasonList');
    const count = document.getElementById('seasonCount');
    if (count) count.textContent = `(${seasonJobs.length} races)`;
    if (!container) return;
    // FIVE-HOUR SHIFT Win H8 (security): same XSS class as the fleet list above.
    // Painter-typed race name was interpolated raw into value="..." attribute.
    const _escSeason = (typeof escapeHtml === 'function') ? escapeHtml : (s => String(s == null ? '' : s));
    container.innerHTML = seasonJobs.map((job, i) => `
        <div class="batch-entry">
            <span style="color: var(--accent-blue); font-weight: 600; min-width: 14px;">${i + 1}</span>
            <input type="text" value="${_escSeason(job.name)}" onchange="seasonJobs[${i}].name=this.value" placeholder="Race name" style="max-width: 100px;">
            <label style="font-size: 9px; color: var(--text-dim); min-width: 32px;">Wear:</label>
            <input type="range" min="0" max="100" value="${Number(job.wearLevel) || 0}" oninput="seasonJobs[${i}].wearLevel=parseInt(this.value); this.nextElementSibling.textContent=this.value+'%'" style="width: 60px;">
            <span style="font-size: 9px; color: var(--accent-orange); min-width: 28px;">${Number(job.wearLevel) || 0}%</span>
            <span class="batch-remove" onclick="removeSeasonRace(${i})" title="Remove race">&times;</span>
        </div>
    `).join('');
}

function quickFillSeasonWear() {
    if (seasonJobs.length < 2) { showToast('Add at least 2 races for wear progression!', true); return; }
    for (let i = 0; i < seasonJobs.length; i++) {
        seasonJobs[i].wearLevel = Math.round((i / (seasonJobs.length - 1)) * 100);
    }
    renderSeasonList();
    showToast(`Wear ramp: 0% to 100% across ${seasonJobs.length} races`);
}

/**
 * Render all races in the season queue with progressive wear levels. // [50]
 */
async function doSeasonRender() {
    _showRetiredBatchModeToast('Season mode');
    return;
    if (!ShokkerAPI.online) { showToast(SPB_ENGINE_OFFLINE_MSG, true); return; } // [38] specific
    if (seasonJobs.length === 0) { showToast('Add at least one race!', true); return; }

    const paintFile = document.getElementById('paintFile')?.value.trim();
    const iracingId = document.getElementById('iracingId')?.value.trim();
    if (!paintFile) { showToast('Set paint file in Car Info!', true); return; }

    const btn = document.getElementById('btnSeasonRender');
    const progress = document.getElementById('seasonProgress');
    const results = document.getElementById('seasonResults');
    if (btn) { btn.disabled = true; btn.textContent = 'Rendering Season...'; } // [28] loading indicator + null check
    if (progress) progress.style.display = 'block'; // [55] null check
    if (results) results.innerHTML = ''; // [55] null check

    const validZones = zones.filter((z, i) => !(typeof _isSuppressedLegacyZone === 'function' && _isSuppressedLegacyZone(z, i)) && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || (_renderMaskHasPixels(z.regionMask))));
    if (validZones.length === 0) { showToast('Set up zones first!', true); if (btn) btn.disabled = false; if (progress) progress.style.display = 'none'; return; } // [55] null checks

    const serverZones = validZones.map(z => {
        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
        _applyPatternMaterialControls(zoneObj, z);
        _applyCustomIntensity(zoneObj, z);
        _applyZoneMaterialStack(zoneObj, z);
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fc = _resolveFinishColors(z.finish); if (_fc) zoneObj.finish_colors = _fc; if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        if (z.specShiftR || z.specShiftG || z.specShiftB) zoneObj.spec_channel_shift = [Number(z.specShiftR) || 0, Number(z.specShiftG) || 0, Number(z.specShiftB) || 0];
        _applySpecMaterialRemap(zoneObj, z);
        _applySpecMaterialOverride(zoneObj, z);
        _applySpecLightingMask(zoneObj, z);
        // BOIL THE OCEAN drift hunt #4: base color mode header → single helper.
        _applyBaseColorMode(zoneObj, z);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.patternStrengthMapEnabled && z.patternStrengthMap && typeof encodeStrengthMapRLE === 'function') { zoneObj.pattern_strength_map = encodeStrengthMapRLE(z.patternStrengthMap); }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) { zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5))); zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5))); zoneObj.pattern_flip_h = !!z.patternFlipH; zoneObj.pattern_flip_v = !!z.patternFlipV; }
        if (z.patternPlacement === 'fit' || z.patternFitZone || _zoneShouldFitIntoApplyArea(z)) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge !== false) zoneObj.hard_edge = true;  // [SPB 2026-06-02 owner] hard edge is the DEFAULT; only an explicit uncheck (false) sends soft
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) { zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5))); zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5))); zoneObj.base_rotation = Number(z.baseRotation ?? 0); zoneObj.base_flip_h = !!z.baseFlipH; zoneObj.base_flip_v = !!z.baseFlipV; }
        { const _sr = Number(z.specRotation ?? 0); const _ss = (window._spbResolveSpecScale ? window._spbResolveSpecScale(z) : Number(z.specScale ?? z.baseScale ?? 1)); if (_sr !== 0) zoneObj.spec_rotation = _sr; if (_ss !== 1 || (window._spbSpecIndependent && window._spbSpecIndependent(z))) zoneObj.spec_scale = _ss; }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // BOIL THE OCEAN drift hunt #5: 5-tier spec_pattern_stack loop → single helper.
        _applyAllSpecPatternStacks(zoneObj, z);
        window.SPBZoneMaterialInstancePayload?.apply(zoneObj, z);
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        _applyBlendBaseOverlay(zoneObj, z);
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // BOIL THE OCEAN drift hunt #2: 4 base overlay blocks → single helper.
        _applyAllExtraBaseOverlays(zoneObj, z);
        // 2026-04-18 MARATHON bug #27 (Bockwinkel, HIGH): pre-fix, season
        // render mapper (this builder) emitted no region_mask / spatial_mask
        // / source_layer_mask at all. Season renders painted every zone's
        // finish across the WHOLE car body instead of restricting to the
        // mask. The other 2 builders (doRender + PS export) emit these;
        // this was the asymmetric drop. Now mirrors their behavior.
        _encodeZoneApplyMasks(zoneObj, z);
        const hasSpatialRefinement = _renderMaskHasPixels(z.spatialMask);
        const shouldPriorityOverride = !!(
            hasSpatialRefinement &&
            typeof window !== 'undefined' &&
            typeof window._zoneShouldRequestPriorityOverride === 'function' &&
            window._zoneShouldRequestPriorityOverride(z)
        );
        if (shouldPriorityOverride) zoneObj.priority_override = true;
        // Source-layer restriction (same fail-closed contract as doRender
        // and PS export: empty all-zero mask + console.warn + one-shot
        // user toast keyed on zone name).
        if ((z.sourceLayer || (Array.isArray(z.sourceLayers) && z.sourceLayers.length)) && typeof _psdLayers !== 'undefined' && typeof encodeRegionMaskRLE === 'function') {
            // [SPB-MULTILAYER 2026-08-21] fail-closed union across the restricted set.
            const _slu = (typeof window.getZoneSourceLayersUnionMask === 'function')
                ? window.getZoneSourceLayersUnionMask(z, (document.getElementById('paintCanvas')?.width || 2048), (document.getElementById('paintCanvas')?.height || 2048))
                : null;
            const srcLayer = _slu ? _slu.firstLayer : _psdLayers.find(l => l.id === z.sourceLayer);
            const pc = document.getElementById('paintCanvas');
            const w = pc?.width || 2048;
            const h = pc?.height || 2048;
            _attachSourceLayerCacheHints(zoneObj, z, srcLayer, w, h);
            // [ULTRACODE 2026-08-22 synthesis #6] a dangling ids[0] must not
            // swallow a SURVIVING union of sibling layers.
            if (!srcLayer && !(_slu && _slu.union)) {
                try {
                    console.warn('[SPB][source_layer] zone "%s" references missing layer "%s" — emitting empty mask (zone will paint nothing until source is restored or sourceLayer is cleared)',
                        z.name || '?', z.sourceLayer);
                } catch (_) {}
                try {
                    if (typeof window !== 'undefined') {
                        window._SPB_DANGLING_SOURCE_TOASTED = window._SPB_DANGLING_SOURCE_TOASTED || {};
                        const _key = (z.name || '?') + '|' + z.sourceLayer;
                        if (!window._SPB_DANGLING_SOURCE_TOASTED[_key] && typeof showToast === 'function') {
                            window._SPB_DANGLING_SOURCE_TOASTED[_key] = true;
                            showToast(`Zone "${z.name || ''}" source layer is missing — painting nothing. Re-restrict or clear source.`, 'warn');
                        }
                    }
                } catch (_) {}
                const _emptyMask = new Uint8Array(w * h);
                zoneObj.source_layer_mask = encodeRegionMaskRLE(_emptyMask, w, h);
            } else if (_slu && _slu.union) {
                zoneObj.source_layer_mask = encodeRegionMaskRLE(_slu.union, w, h);
            } else if (_slu && _slu.requested > 0) {
                // [ULTRACODE 2026-08-22 synthesis #1] fail CLOSED on ANY
                // unresolvable restriction (hidden group / img-less / boot
                // race) — the hiddenCount>0 gate let those ship NO mask.
                zoneObj.source_layer_mask = encodeRegionMaskRLE(new Uint8Array(w * h), w, h);
                if (_slu.hiddenCount > 0) {
                    try { if (typeof window._spbHiddenSourceToast === 'function') window._spbHiddenSourceToast(z, _slu); } catch (_) {}
                }
            } else if (typeof window.getLayerVisibleContributionMask === 'function') {
                const visibleMask = window.getLayerVisibleContributionMask(srcLayer, w, h);
                if (visibleMask) zoneObj.source_layer_mask = encodeRegionMaskRLE(visibleMask, w, h);
            }
        }
        return zoneObj;
    });

    // FIVE-HOUR SHIFT Win H5 (asymmetric outlier — same class as MARATHON #31):
    // pre-fix doSeasonRender's per-race extras was just { wear_level } when
    // present. EVERY race in a season render lost: decals (with spec finishes),
    // decal mask, PSD live composite, stamps (with finish), helmet/suit files,
    // exportZip, dualSpec, nightBoost, output_dir, import_spec_map.
    // doFleetRender already has the full extras construction (Marathon #31);
    // doSeasonRender was the asymmetric outlier — now mirrors that pattern.
    const _seasonSharedExtras = {};
    const _seasonSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
    if (_seasonSpecPath) _seasonSharedExtras.import_spec_map = _seasonSpecPath;
    const _seasonOutputDir = document.getElementById('outputDir')?.value.trim();
    const _seasonHelmetFile = document.getElementById('helmetFile')?.value.trim();
    const _seasonSuitFile = document.getElementById('suitFile')?.value.trim();
    const _seasonExportZip = document.getElementById('exportZipCheckbox')?.checked || false;
    const _seasonDualSpec = document.getElementById('dualSpecCheckbox')?.checked || false;
    if (_seasonOutputDir) _seasonSharedExtras.output_dir = _seasonOutputDir;
    if (_seasonHelmetFile) _seasonSharedExtras.helmet_paint_file = _seasonHelmetFile;
    if (_seasonSuitFile) _seasonSharedExtras.suit_paint_file = _seasonSuitFile;
    if (_seasonExportZip) _seasonSharedExtras.export_zip = true;
    if (_seasonDualSpec) {
        _seasonSharedExtras.dual_spec = true;
        _seasonSharedExtras.night_boost = parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7');
    }
    // Decals + per-decal spec finishes + decal mask.
    if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
        const _seasonDecalComposite = compositeDecalsForRender();
        if (_seasonDecalComposite) _seasonSharedExtras.paint_image_base64 = await canvasToBase64Async(_seasonDecalComposite);
        if (typeof compositeDecalMaskForRender === 'function') {
            const _seasonMaskUrl = compositeDecalMaskForRender();
            if (_seasonMaskUrl) _seasonSharedExtras.decal_mask_base64 = _seasonMaskUrl;
        }
        const _seasonDecalSpecs = decalLayers
            .filter(dl => dl.visible && dl.specFinish && dl.specFinish !== 'none')
            .map(dl => ({ specFinish: dl.specFinish }));
        if (_seasonDecalSpecs.length > 0) _seasonSharedExtras.decal_spec_finishes = _seasonDecalSpecs;
    }
    // PSD layer composite if no decal composite ran and layers exist.
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0 &&
        !_seasonSharedExtras.paint_image_base64) {
        const _seasonPc = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
            ? window.buildLivePaintCompositeCanvas()
            : document.getElementById('paintCanvas');
        if (_seasonPc) _seasonSharedExtras.paint_image_base64 = await canvasToBase64Async(_seasonPc);
    }
    // Spec stamps + finish.
    if (typeof compositeStampsForRender === 'function' && typeof window.stampLayers !== 'undefined' && window.stampLayers.length > 0) {
        const _seasonStamp = compositeStampsForRender();
        if (_seasonStamp) {
            _seasonSharedExtras.stamp_image_base64 = await canvasToBase64Async(_seasonStamp);
            _seasonSharedExtras.stamp_spec_finish = window.stampSpecFinish || 'gloss';
        }
    }

    for (let i = 0; i < seasonJobs.length; i++) {
        const job = seasonJobs[i];
        progress.textContent = `Rendering race ${i + 1}/${seasonJobs.length}: ${job.name} (wear ${job.wearLevel}%)...`;

        // Per-race extras = shared baseline + the per-race wear level.
        const extras = Object.assign({}, _seasonSharedExtras);
        if (job.wearLevel > 0) extras.wear_level = job.wearLevel;

        try {
            const result = await ShokkerAPI.render(paintFile, serverZones, iracingId, 51, false, extras);
            const urls = result.preview_urls || {};
            const paintUrl = Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet'));
            results.innerHTML += `
                <div class="batch-result-card">
                    ${paintUrl ? `<img src="${ShokkerAPI.baseUrl + paintUrl[1]}" alt="${job.name}">` : '<div style="height: 60px; background: #111; border-radius: 3px;"></div>'}
                    <div class="batch-result-name">${job.name}</div>
                    ${job.wearLevel > 0 ? `<span class="batch-wear-badge">WEAR ${job.wearLevel}%</span>` : ''}
                </div>`;
        } catch (err) {
            results.innerHTML += `<div class="batch-result-card"><div class="batch-result-name" style="color: #ff4444;">FAILED: ${job.name}</div></div>`;
        }
    }

    if (progress) progress.textContent = `Season render complete! ${seasonJobs.length} races rendered.`; // [55] null check
    if (btn) { btn.disabled = false; btn.textContent = 'Render Season'; } // [29] restore button
}

// ===== iRACING FOLDER HELPER =====
/**
 * Auto-fill the output directory with the iRacing paint folder from server config. // [47]
 * Uses cached config data to avoid redundant requests. // [23]
 */
async function setOutputToIracingFolder() {
    if (!ShokkerAPI.online) {
        showToast(SPB_ENGINE_OFFLINE_MSG, true);
        return;
    }
    try {
        // [23] Cache config lookups - they don't change during a session
        const cfg = await cachedFetch('iracing_config', async () => {
            const res = await fetch(ShokkerAPI.baseUrl + '/config', {
                signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [9] timeout
            });
            return await safeParseJSON(res, 'config fetch');
        });
        const activeCar = cfg.active_car;
        const carPath = cfg.car_paths?.[activeCar];
        const outputDir = document.getElementById('outputDir'); // [54] null check
        if (carPath && outputDir) {
            outputDir.value = carPath;
            showToast(`Save To set to: ${activeCar} (${carPath})`);
        } else if (!carPath) {
            showToast('No active car configured on server. Check shokker_config.json', true); // [39] specific
        }
    } catch (e) {
        showToast(classifyFetchError(e, 'iRacing folder lookup'), true); // [12] friendly error
    }
}

// ===== RENDER =====
/**
 * Safe wrapper around doRender that handles edge cases: // [47]
 * - Terminate mode (cancel in-flight render)
 * - Already rendering guard // [20] dedup
 * - Offline server recheck
 */
function safeDoRender() {
    try {
        const btn = document.getElementById('btnRender'); // [55] null check via ?.
        if (btn && btn.classList.contains('terminate-mode')) {
            // Button is in terminate mode - clicking it should cancel, not start new render
            ShokkerAPI.cancelRender();
            return;
        }
        if (btn && btn.textContent.includes('RENDERING')) {
            showToast('Already rendering - please wait...', true);
            return;
        }
        if (!ShokkerAPI.online) {
            showToast('Server appears offline - rechecking...', true);
            // Force recheck, then try render if now online
            ShokkerAPI.checkStatus().then(() => {
                if (ShokkerAPI.online) {
                    showToast('Server is back! Starting render...');
                    doRender();
                } else {
                    showToast(SPB_ENGINE_OFFLINE_MSG, true);
                }
            });
            return;
        }
        doRender();
    } catch (e) {
        console.error('[safeDoRender] Error:', e);
        showToast('Error starting render: ' + e.message, true);
    }
}

/**
 * Build the server-compatible zone payload from local zones state. // [46]
 * Used by both full render and live preview so paint file matching stays consistent.
 * @param {Array} zones - Array of local zone objects
 * @returns {Array} Array of server-compatible zone configuration objects
 */
function buildServerZonesForRender(zones) {
    const validZones = (window.SPBStableZoneSeeds && Array.isArray(zones))
        ? window.SPBStableZoneSeeds.prepare(zones, _isSuppressedLegacyZone, _zoneHasRenderableMaterial, _renderMaskHasPixels)
        : zones.filter((z, i) => !(typeof _isSuppressedLegacyZone === 'function' && _isSuppressedLegacyZone(z, i)) && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || (_renderMaskHasPixels(z.regionMask))));
    // [RENDER-BUDGET 2026-10-04] one build = one layer state (this runs synchronously), so
    // zones restricted to the SAME layer set get the same union mask, RLE and layer RGB.
    // They used to be recomputed per zone: the owner's ARCA design ran toDataURL on the
    // same 2048 canvas 3x (Spray Can left/right + hood) and the AI's per-part splits
    // multiply that. Memoised per build, keyed by the exact ordered id list + canvas size;
    // nothing outlives this call, so it can never serve stale layer pixels.
    const _slBuildMemo = new Map();
    return validZones.map(z => {
        const zoneObj = {
            name: z.name,
            color: formatColorForServer(z.color, z),
            intensity: z.intensity,
        };
        if (window.SPBStableZoneSeeds && window.SPBStableZoneSeeds.validIndex(z.renderSeedIndex)) {
            zoneObj.render_seed_index = z.renderSeedIndex;
        }
        _applyPatternMaterialControls(zoneObj, z);
        const _primaryBaseId = z.base || (_zoneNeedsNeutralBaseAnchor(z) ? 'gloss' : null);
        const _hasPrimaryBase = !!_primaryBaseId;
        const _hasImportedSpecSource = _zoneHasImportedSpecSource(z);
        const _hasMaterialStack = _zoneHasMaterialStack(z);
        const _hasRenderableMaterial = _hasPrimaryBase || !!z.finish || _hasImportedSpecSource || _hasMaterialStack;
        _applyCustomIntensity(zoneObj, z);
        if (_hasMaterialStack) _applyZoneMaterialStack(zoneObj, z);
        if ((_hasPrimaryBase && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) {
            zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        }
        if (_hasPrimaryBase) {
            zoneObj.base = _primaryBaseId;
            zoneObj.pattern = z.pattern || 'none';
            if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
            if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation;
            // [PERF] Only send pattern_opacity if not default (1.0) to reduce payload
            { const _po = (z.patternOpacity ?? 100) / 100; if (_po !== 1.0) zoneObj.pattern_opacity = _po; }
            // BOIL THE OCEAN deep core — CRITICAL DRIFT FIX:
            // This payload builder previously inlined a pattern_stack
            // mapper that DROPPED the blend_mode field. Painters who set
            // a non-normal blend mode on any stack layer would lose it
            // in this code path while preview/render preserved it.
            // Now delegates to the central helper (parity with other 2 builders).
            { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; }
        } else if (z.finish) {
            zoneObj.finish = z.finish;
            const _finishRot = z.baseRotation || z.rotation || 0;
            if (_finishRot && _finishRot !== 0) zoneObj.rotation = _finishRot;
            // BOIL THE OCEAN drift hunt #3: this builder USED to inline a stale
            // regex missing the `mc_` prefix → multi-color finishes silently
            // exported without finish_colors. Now uses the same helper as the
            // other 2 builders (single source of truth).
            const fc = _resolveFinishColors(z.finish);
            if (fc) zoneObj.finish_colors = fc;
            if (z.pattern && z.pattern !== 'none') {
                zoneObj.pattern = z.pattern;
                if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
                zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
            }
            // Same drift fix in the finish branch.
            { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; }
        }
        _applyZoneSpecSource(zoneObj, z);
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        if (z.specShiftR || z.specShiftG || z.specShiftB) zoneObj.spec_channel_shift = [Number(z.specShiftR) || 0, Number(z.specShiftG) || 0, Number(z.specShiftB) || 0];
        _applySpecMaterialRemap(zoneObj, z);
        _applySpecMaterialOverride(zoneObj, z);
        _applySpecLightingMask(zoneObj, z);
        // BOIL THE OCEAN drift hunt #4: base color mode header → single helper.
        _applyBaseColorMode(zoneObj, z);
        // [PERF] Only send non-default values to reduce JSON payload size
        if (_hasPrimaryBase || (z.finish && z.pattern && z.pattern !== 'none')) {
            const _psm = Number(z.patternSpecMult ?? 1);
            if (_psm !== 1) zoneObj.pattern_spec_mult = _psm;
        }
        if (z.patternStrengthMapEnabled && z.patternStrengthMap && typeof encodeStrengthMapRLE === 'function') { zoneObj.pattern_strength_map = encodeStrengthMapRLE(z.patternStrengthMap); }
        if (_hasPrimaryBase || (z.finish && z.pattern && z.pattern !== 'none')) {
            const _pox = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5)));
            const _poy = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5)));
            if (_pox !== 0.5) zoneObj.pattern_offset_x = _pox;
            if (_poy !== 0.5) zoneObj.pattern_offset_y = _poy;
            if (z.patternFlipH) zoneObj.pattern_flip_h = true;
            if (z.patternFlipV) zoneObj.pattern_flip_v = true;
        }
        if (z.patternPlacement === 'fit' || z.patternFitZone || _zoneShouldFitIntoApplyArea(z)) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge !== false) zoneObj.hard_edge = true;  // [SPB 2026-06-02 owner] hard edge is the DEFAULT; only an explicit uncheck (false) sends soft
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if ((z.sourceLayer || (Array.isArray(z.sourceLayers) && z.sourceLayers.length)) && typeof _psdLayers !== 'undefined' && typeof encodeRegionMaskRLE === 'function') {
            // [SPB-MULTILAYER 2026-08-21] union of every restricted layer; the
            // engine consumes only the mask, so it needs zero changes.
            const _sluW = (document.getElementById('paintCanvas')?.width || 2048);
            const _sluH = (document.getElementById('paintCanvas')?.height || 2048);
            const _sluKey = (typeof window.zoneSourceLayerIds === 'function')
                ? ('u|' + _sluW + 'x' + _sluH + '|' + window.zoneSourceLayerIds(z).map(String).join('\u0001'))
                : null;
            let _sluC = _sluKey ? _slBuildMemo.get(_sluKey) : undefined;
            if (_sluC === undefined) {
                _sluC = (typeof window.getZoneSourceLayersUnionMask === 'function')
                    ? window.getZoneSourceLayersUnionMask(z, _sluW, _sluH)
                    : null;
                if (_sluKey) _slBuildMemo.set(_sluKey, _sluC);
            }
            const srcLayer = _sluC ? _sluC.firstLayer : _psdLayers.find(l => l.id === z.sourceLayer);
            // Codex HIGH (Workstream 12 #235 + Workstream 24 chaos #471) —
            // dangling source-layer reference. The user explicitly RESTRICTED
            // this zone to a layer; if the layer is gone, falling back to
            // composite matching silently broadens the zone in surprising ways.
            // Fail safely + visibly: send an empty all-zero mask AND skip the
            // RGB payload AND surface a toast so the painter knows what happened.
            const pc = document.getElementById('paintCanvas');
            const w = pc?.width || 2048;
            const h = pc?.height || 2048;
            _attachSourceLayerCacheHints(zoneObj, z, srcLayer, w, h);
            if (!srcLayer) {
                // Distinguish a GENUINE dangling reference from the PSD simply not having finished
                // loading yet. On the example-car / PSD boot the first preview render can fire before
                // _psdLayers is populated — the layer isn't "missing", it just isn't loaded yet, and the
                // post-load re-render resolves it (verified 2026-06-01: all 5 example zones resolve once
                // loaded, danglingCount=0). Only warn (+ toast) when the PSD IS loaded and the layer is
                // still genuinely gone, so we keep the real dangling-ref diagnostic without boot spam.
                const _psdReady = (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded) && _psdLayers.length > 0;
                if (_psdReady) {
                    try {
                        console.warn('[SPB][source_layer] zone "%s" references missing layer "%s" — emitting empty mask (zone will paint nothing until source is restored or sourceLayer is cleared)',
                            z.name || '?', z.sourceLayer);
                    } catch (_) {}
                    // User-visible toast (throttled per zone via window state).
                    try {
                        if (typeof window !== 'undefined') {
                            window._SPB_DANGLING_SOURCE_TOASTED = window._SPB_DANGLING_SOURCE_TOASTED || {};
                            const _key = (z.name || '?') + '|' + z.sourceLayer;
                            if (!window._SPB_DANGLING_SOURCE_TOASTED[_key] && typeof showToast === 'function') {
                                window._SPB_DANGLING_SOURCE_TOASTED[_key] = true;
                                showToast(`Zone "${z.name || ''}" source layer is missing — painting nothing. Re-restrict or clear source.`, 'warn');
                            }
                        }
                    } catch (_) {}
                }
                // Empty all-zero mask = engine intersects to nothing = zone produces no pixels.
                // Far safer than silently broadening the restriction.
                const _emptyMask = new Uint8Array(w * h);
                zoneObj.source_layer_mask = encodeRegionMaskRLE(_emptyMask, w, h);
                // Do NOT send source_layer_rgb_png either — without a layer there's nothing to match against.
                // Fall through past the RGB encoding block (next).
            }
            const visibleMask = (_sluC && _sluC.union)
                ? _sluC.union
                : ((_sluC && _sluC.requested > 0)
                    ? null   // [A3] union path is authoritative; no single-layer fallback that would ignore visibility
                    : ((srcLayer && typeof window.getLayerVisibleContributionMask === 'function')
                        ? window.getLayerVisibleContributionMask(srcLayer, w, h)
                        : null));
            if (visibleMask) {
                // [RENDER-BUDGET 2026-10-04] same union array (memoised above) -> same RLE.
                const _rleKey = (_sluC && _sluC.union === visibleMask && _sluKey) ? ('m|' + w + 'x' + h + '|' + _sluKey) : null;
                let _rle = _rleKey ? _slBuildMemo.get(_rleKey) : undefined;
                if (_rle === undefined) {
                    _rle = encodeRegionMaskRLE(visibleMask, w, h);
                    if (_rleKey) _slBuildMemo.set(_rleKey, _rle);
                }
                zoneObj.source_layer_mask = _rle;
            } else if (_sluC && _sluC.requested > 0) {
                // [ULTRACODE 2026-08-22 synthesis #1] FAIL CLOSED on ANY
                // unresolvable restriction — the old condition required
                // hiddenCount>0, so a restricted layer whose PARENT GROUP was
                // hidden (canComposite false, l.visible still true), an
                // img-less layer, or a pre-load boot race attached NO mask at
                // all and the zone painted the ENTIRE CAR while the highlight
                // showed nothing (render/UI inverted). Owner hit this by
                // toggling "Turn Off Before Exporting TGA". Restricted +
                // unresolvable = paint nothing, loudly.
                zoneObj.source_layer_mask = encodeRegionMaskRLE(new Uint8Array(w * h), w, h);
                if (_sluC.hiddenCount > 0) {
                    try { if (typeof window._spbHiddenSourceToast === 'function') window._spbHiddenSourceToast(z, _sluC); } catch (_) {}
                }
            }
            // TRUE layer-local color match: send the layer's own RGB so the
            // engine matches colors against the layer's unblended pixels
            // (Photoshop-correct) instead of the composite. Falls back to
            // composite-based matching if encoding fails or layer has no img.
            if (srcLayer && srcLayer.img) {
                try {
                    // [SPB-MULTILAYER 2026-08-21] colour-match against ALL restricted
                    // layers' unblended pixels, drawn bottom-to-top at their bboxes.
                    const _rgbIds = (_sluC && _sluC.ids && _sluC.ids.length) ? _sluC.ids : [z.sourceLayer];
                    // [ULTRACODE 2026-08-22 synthesis #6] hidden restricted
                    // layers must not contribute colour-match pixels either.
                    const _rgbLayers = _psdLayers.filter(l => l && _rgbIds.indexOf(l.id) > -1 && l.img && l.visible !== false);
                    // [RENDER-BUDGET 2026-10-04] identical drawn layer list -> identical PNG: encode once per build.
                    const _rgbKey = 'r|' + w + 'x' + h + '|' + _rgbLayers.map(l => String(l.id)).join('\u0001');
                    let _rgbPng = _slBuildMemo.get(_rgbKey);
                    if (_rgbPng === undefined) {
                        const lc = document.createElement('canvas');
                        lc.width = w; lc.height = h;
                        const lctx = lc.getContext('2d');
                        lctx.clearRect(0, 0, w, h);
                        for (const _rl of _rgbLayers) {
                            const bx = Array.isArray(_rl.bbox) ? (_rl.bbox[0] || 0) : 0;
                            const by = Array.isArray(_rl.bbox) ? (_rl.bbox[1] || 0) : 0;
                            lctx.drawImage(_rl.img, bx, by);
                        }
                        _rgbPng = lc.toDataURL('image/png').split(',', 2)[1];
                        _slBuildMemo.set(_rgbKey, _rgbPng);
                    }
                    zoneObj.source_layer_rgb_png = _rgbPng;
                } catch (_lrErr) { /* fall back to composite matching */ }
            }
            // Workstream 8 task #159: opt-in diagnostic for source-layer payload.
            // Enable in console with:  window._SPB_DEBUG_SOURCE_LAYER = true
            // Emits ONE log per zone per send (not per pixel) so a developer can
            // confirm payload contents without running pytest. Quiet by default.
            if (typeof window !== 'undefined' && window._SPB_DEBUG_SOURCE_LAYER === true) {
                try {
                    const _maskBytes = (typeof zoneObj.source_layer_mask === 'string')
                        ? zoneObj.source_layer_mask.length
                        : (zoneObj.source_layer_mask ? JSON.stringify(zoneObj.source_layer_mask).length : 0);
                    const _rgbBytes = (typeof zoneObj.source_layer_rgb_png === 'string')
                        ? zoneObj.source_layer_rgb_png.length
                        : 0;
                    const _bbox = (srcLayer && Array.isArray(srcLayer.bbox)) ? srcLayer.bbox.slice() : null;
                    console.log('[SPB][source_layer]', {
                        layerId: z.sourceLayer,
                        layerName: (srcLayer && srcLayer.name) || null,
                        zoneName: z.name || null,
                        maskBytes: _maskBytes,
                        rgbBytes: _rgbBytes,
                        bbox: _bbox,
                        canvas: [w, h],
                    });
                } catch (_dbgErr) { /* diagnostics must never break payload send */ }
            }
        }
        // [PERF] Only send base offset/rotation/flip if non-default
        if (_hasRenderableMaterial) {
            const _box = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5)));
            const _boy = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5)));
            const _brot = Number(z.baseRotation ?? 0);
            if (_box !== 0.5) zoneObj.base_offset_x = _box;
            if (_boy !== 0.5) zoneObj.base_offset_y = _boy;
            if (_brot !== 0) zoneObj.base_rotation = _brot;
            if (z.baseFlipH) zoneObj.base_flip_h = true;
            if (z.baseFlipV) zoneObj.base_flip_v = true;
        }
        const _specRot = Number(z.specRotation ?? 0);
        const _specScale = (window._spbResolveSpecScale ? window._spbResolveSpecScale(z) : Number(z.specScale ?? z.baseScale ?? 1));
        if (_specRot !== 0) zoneObj.spec_rotation = _specRot;
        if (_specScale !== 1 || (window._spbSpecIndependent && window._spbSpecIndependent(z))) zoneObj.spec_scale = _specScale;
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // BOIL THE OCEAN drift hunt #5: 5-tier spec_pattern_stack loop → single helper.
        _applyAllSpecPatternStacks(zoneObj, z);
        window.SPBZoneMaterialInstancePayload?.apply(zoneObj, z);
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        _applyBlendBaseOverlay(zoneObj, z);
        if (z.usePaintReactive && z.paintReactiveColor) {
            const _pc = z.paintReactiveColor;
            zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255];
        }
        // BOIL THE OCEAN drift hunt #2: 4 base overlay blocks → single helper.
        // PRE-FIX: this builder used `if (z.X != null)` guards on pattern_opacity/
        // scale/rotation/strength while the other two builders always emitted
        // clamped defaults. Old saved zones (sliders untouched) sent DIFFERENT
        // payloads to /export-to-photoshop than to /render. Helper enforces
        // single contract.
        _applyAllExtraBaseOverlays(zoneObj, z);
        _encodeZoneApplyMasks(zoneObj, z);
        const hasSpatialRefinement = _renderMaskHasPixels(z.spatialMask);
        const shouldPriorityOverride = !!(
            hasSpatialRefinement &&
            typeof window !== 'undefined' &&
            typeof window._zoneShouldRequestPriorityOverride === 'function' &&
            window._zoneShouldRequestPriorityOverride(z)
        );
        if (shouldPriorityOverride) zoneObj.priority_override = true;
        return zoneObj;
    });
}
if (typeof window !== 'undefined') window.buildServerZonesForRender = buildServerZonesForRender;

// --- Photoshop round-trip: Export modal + Import ---
const PS_EXPORT_FOLDER_KEY = 'shokker_ps_export_folder';

function openExportToPhotoshopModal() {
    const modal = document.getElementById('exportToPhotoshopModal');
    const exchangeInput = document.getElementById('psExportExchangeFolder');
    if (modal) modal.classList.add('active');
    // Pre-fill export folder: saved preference first, then server default
    if (exchangeInput) {
        const saved = (typeof localStorage !== 'undefined' && localStorage.getItem(PS_EXPORT_FOLDER_KEY)) || '';
        if (saved) {
            exchangeInput.value = saved;
        } else if (ShokkerAPI.online) {
            ShokkerAPI.getPhotoshopExchangeRoot().then(function (path) {
                if (path) exchangeInput.value = path;
            }).catch(function () {});
        }
    }
}

function closeExportToPhotoshopModal() {
    const modal = document.getElementById('exportToPhotoshopModal');
    if (modal) modal.classList.remove('active');
}

/**
 * Export the current zone setup to Photoshop exchange format. // [50]
 * Sends zone data + optional decal/stamp overlays to the server.
 */
async function doExportToPhotoshop() {
    if (!ShokkerAPI.online) { showToast(SPB_ENGINE_OFFLINE_MSG, true); return; }
    const carFileName = (document.getElementById('psExportCarFileName') || {}).value.trim();
    if (!carFileName) { showToast('Enter a car file name (e.g. DLM438-base-001).', true); return; }
    const exchangeFolder = (document.getElementById('psExportExchangeFolder') || {}).value.trim();
    const paintFile = (document.getElementById('paintFile') || {}).value.trim();
    const hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);
    if (!paintFile && !hasLiveFlatSource) { showToast('Set the Source Paint path in the header bar first.', true); return; }

    const serverZones = buildServerZonesForRender(typeof zones !== 'undefined' ? zones : []);
    const extras = {};
    const exportSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
    if (exportSpecPath) extras.import_spec_map = exportSpecPath;
    // [PERF] Use async canvasToBase64Async for PS export too
    if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
        const compositeCanvas = compositeDecalsForRender();
        if (compositeCanvas) extras.paint_image_base64 = await canvasToBase64Async(compositeCanvas);
        if (typeof compositeDecalMaskForRender === 'function') {
            const maskDataUrl = compositeDecalMaskForRender();
            if (maskDataUrl) extras.decal_mask_base64 = maskDataUrl;
        }
        // 2026-04-18 MARATHON (Windham bug #21): pre-fix, PS export silently
        // dropped per-decal spec finishes. Painter assigned chrome spec to
        // a sponsor decal → preview/render showed chrome → PS export
        // produced a PSD with default gloss where the decal sat. Now PS
        // export emits decal_spec_finishes just like doRender does.
        const _psDecalSpecs = decalLayers
            .filter(dl => dl.visible && dl.specFinish && dl.specFinish !== 'none')
            .map(dl => ({ specFinish: dl.specFinish }));
        if (_psDecalSpecs.length > 0) extras.decal_spec_finishes = _psDecalSpecs;
    }
    // Spec Stamps for PS export
    if (typeof compositeStampsForRender === 'function' && typeof window.stampLayers !== 'undefined' && window.stampLayers.length > 0) {
        const stampCanvas = compositeStampsForRender();
        if (stampCanvas) {
            extras.stamp_image_base64 = await canvasToBase64Async(stampCanvas);
            extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';
        }
    }

    // Match Full Render: Change File/browser-selected flat images are live
    // canvas sources, not trusted local paths. Export the visible canvas.
    if (hasLiveFlatSource && !extras.paint_image_base64) {
        const _flatPcExp = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
            ? window.buildLivePaintCompositeCanvas()
            : document.getElementById('paintCanvas');
        if (_flatPcExp) {
            extras.paint_image_base64 = await canvasToBase64Async(_flatPcExp);
            extras.source_mode = 'live_flat_canvas';
            console.log('[doExportToPhotoshop] Live flat image source: sending visible canvas as base64 paint', window._spbFlatPaintLiveSource);
        }
    }

    // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W14): silent-drop.
    // doRender (line ~2579) has a PSD-layer composite-fallback block: if
    // the painter has PSD layers loaded but no decals (so paint_image_base64
    // wasn't set above), it ships the live paint canvas as the source so
    // user edits actually appear in the render. doExportToPhotoshop was
    // missing this block — a painter with PSD layers and no decals would
    // export a PSD that silently dropped all their layer paint work.
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0 &&
        !extras.paint_image_base64) {
        const _pcExp = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
            ? window.buildLivePaintCompositeCanvas()
            : document.getElementById('paintCanvas');
        if (_pcExp) {
            extras.paint_image_base64 = await canvasToBase64Async(_pcExp);
            console.log('[doExportToPhotoshop] Layer mode: sending live canvas as base64 paint (' + _psdLayers.length + ' layers)');
        }
    }

    const btn = document.getElementById('btnDoExportToPs');
    if (btn) { btn.disabled = true; btn.textContent = 'Exporting...'; }
    try {
        const result = await ShokkerAPI.exportToPhotoshop(carFileName, exchangeFolder || undefined, paintFile, serverZones, extras);
        if (result.error) { showToast('Export failed: ' + result.error, true); return; }
        // Remember the folder we used (exchange root) for next time
        if (result.exchange_dir && typeof localStorage !== 'undefined') {
            const root = result.exchange_dir.replace(/[/\\][^/\\]+$/, '');
            if (root) localStorage.setItem(PS_EXPORT_FOLDER_KEY, root);
        } else if (exchangeFolder && typeof localStorage !== 'undefined') {
            localStorage.setItem(PS_EXPORT_FOLDER_KEY, exchangeFolder);
        }
        showToast('Exported to Photoshop: ' + (result.exchange_dir || carFileName));
        closeExportToPhotoshopModal();
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Export'; }
    }
}

/**
 * Import spec map from the last Photoshop export (one-click round-trip). // [48]
 * Loads the spec map from the exchange folder and triggers a preview render.
 */
async function importSpecFromLastExport() {
    if (!ShokkerAPI.online) { showToast(SPB_ENGINE_OFFLINE_MSG, true); return; }
    var folder = (typeof localStorage !== 'undefined' && localStorage.getItem(PS_EXPORT_FOLDER_KEY)) || '';
    showToast('Loading spec from last PS export...');
    try {
        var res = await fetch(ShokkerAPI.baseUrl + '/api/photoshop-import-spec-from-last-export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exchange_folder: folder || undefined }),
            signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [10] timeout
        });
        var data;
        try { data = await res.json(); } catch (e) {
            showToast('SPB returned an invalid response. Use Restart Server from the SPB tray after code changes.', true);
            return;
        }
        if (data.error) {
            if (data.error === 'not_found') showToast('Server needs to be restarted to load the new import endpoint.', true);
            else showToast(data.error, true);
            return;
        }
        if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = data.temp_path;
        try { if (typeof window !== 'undefined') window.importedSpecMapPath = data.temp_path; } catch (e) {}
        var status = document.getElementById('importSpecMapStatus');
        var label = data.source_file || 'spec from PS export';
        if (status && data.resolution) status.innerHTML = '<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active · Layer 0</span> — ' + label + ' (' + data.resolution[0] + '×' + data.resolution[1] + ')';
        var clearBtn = document.getElementById('btnClearSpecMap');
        if (clearBtn) clearBtn.disabled = false;
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Spec loaded: ' + label);
    } catch (err) {
        showToast('Failed to import spec: ' + (err.message || 'unknown error'), true);
    }
}

/**
 * Main render pipeline. Builds zone payload, sends to server, handles progress polling, // [46]
 * displays results, and updates render history. Called by safeDoRender().
 */
async function doRender() {
    // SPB-93 09-08: keyboard/direct calls must also reject an unpublished source.
    if (window.SPBRenderReadiness && !window.SPBRenderReadiness.allowRender()) return;
    // [SPB DOUBLE-RENDER 2026-08-17] Front-door guard: a second click while a render is in
    // flight used to run this whole function again — double timer start (the leaked-interval
    // "RENDERING... 1786xxxxxx s" bug), double canvas serialization, and a second POST that
    // ShokkerAPI's dedup rejected AFTER the damage. The visibly-busy button is now the truth:
    // one render at a time, second click gets a toast instead of a broken session.
    if (ShokkerAPI._renderInProgress) {
        showToast('A render is already running — hang tight, it will finish on its own.', true);
        return;
    }
    // Fast-double-click debounce: _renderInProgress is only set once the API call actually
    // fires, and the canvas serialization before it can take a second or two — a rapid second
    // click lands in that window. Time-based, so it can never stick "busy" after an early
    // return the way a boolean flag could.
    const _drNow = Date.now();
    if (window._spbLastDoRenderAt && (_drNow - window._spbLastDoRenderAt) < 1500) {
        return;
    }
    window._spbLastDoRenderAt = _drNow;
    console.log('[doRender] Starting render... baseUrl=' + ShokkerAPI.baseUrl + ' origin=' + window.location.origin + ' online=' + ShokkerAPI.online);
    _ensureRenderFloatVisible();
    if (!ShokkerAPI.online) { showToast(SPB_ENGINE_OFFLINE_MSG, true); return; }

    // License gate - disabled for Alpha testing
    // if (!licenseActive) {
    //     showToast('License required for full renders. Enter your key in Settings.', true);
    //     const settingsPanel = document.getElementById('settingsPanel');
    //     if (settingsPanel) settingsPanel.style.display = '';
    //     const licenseInput = document.getElementById('licenseKeyInput');
    //     if (licenseInput) { licenseInput.focus(); licenseInput.scrollIntoView({behavior:'smooth', block:'center'}); }
    //     return;
    // }

    const paintFile = document.getElementById('paintFile').value.trim();
    const iracingId = document.getElementById('iracingId').value.trim();
    let hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);
    // Flat loads set _spbFlatPaintLiveSource so doRender ships canvas→base64. That is correct for
    // browser-only picks, but when Source Paint is a real disk path and there are no PSD layers,
    // full render must re-read paint_file on the server — otherwise external saves (Photoshop, etc.)
    // update the TGA on disk while the canvas stays stale and iRacing gets old pixels.
    const _diskPaintPath = paintFile && (paintFile.includes('/') || paintFile.includes('\\') || /^[a-zA-Z]:/.test(paintFile));
    const _liveFlatSourceKind = (hasLiveFlatSource && typeof window !== 'undefined' && window._spbFlatPaintLiveSource)
        ? String(window._spbFlatPaintLiveSource.source || '')
        : '';
    const _hasPsdLayers = (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0);
    // If we have a real Source Paint path, prefer a fresh server disk read over stale in-memory
    // flat canvas payloads (common after external Photoshop/TGA saves).
    if (_diskPaintPath && /^(change-file|programmatic|shokk)/.test(_liveFlatSourceKind) && typeof window.clearFlatPaintLiveSource === 'function') {
        window.clearFlatPaintLiveSource('full render prefers fresh disk paint_file');
        hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);
    }
    if (!paintFile && !hasLiveFlatSource) { showToast('Set the Source Paint path in the header bar!', true); return; }
    // Quick check: warn if path looks like just a filename (no directory)
    if (paintFile && !hasLiveFlatSource && !paintFile.includes('/') && !paintFile.includes('\\')) {
        showToast('Source Paint needs a FULL path (e.g. C:\\Users\\You\\Documents\\iRacing\\paint\\carname\\car_num_12345.tga), not just a filename!', true);
        return;
    }
    // [SPB-ALPHA-GUARD 2026-06-06] Block render when the iRacing User ID is blank/invalid. Every
    // render output is named car_num_<ID>.tga / car_spec_<ID>.tga; with no ID the server writes
    // car_num_.tga (no number), which iRacing CANNOT load — so a new buyer's first car silently
    // never appears in-sim and the app reads as broken on day one. The header field is
    // aria-required (pattern=\d{4,7}) but nothing enforced it. Pure client guard.
    if (!/^\d{4,7}$/.test(iracingId)) {
        showToast('Enter your iRacing User ID (4–7 digits) in the header bar — it names the car_num_/car_spec_ files iRacing loads.', true);
        const _idEl = document.getElementById('iracingId');
        if (_idEl) { _idEl.focus(); try { _idEl.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) {} }
        return;
    }

    // Build zone configs for the server (same builder used by live preview so paint file matches)
    const serverZones = buildServerZonesForRender(zones);
    console.log('[doRender] Valid zones:', serverZones.length, '/', zones.length, 'total');
    const activeSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath)
        ? importedSpecMapPath
        : ((typeof window !== 'undefined' && window.importedSpecMapPath) ? window.importedSpecMapPath : null);
    const easySculptLock = (typeof window !== 'undefined') ? window._spbEasySculptSpecOverride : null;
    const easySculptLockPath = (easySculptLock && easySculptLock.path) ||
        ((typeof document !== 'undefined' && document.body) ? document.body.dataset.spbEasySculptSpecPath : '');
    const easySculptSpecOnly = !!(easySculptLockPath && activeSpecPath &&
        String(easySculptLockPath).replace(/\\/g, '/') === String(activeSpecPath).replace(/\\/g, '/'));
    if (easySculptSpecOnly && serverZones.length) {
        // Owner 2026-07-19: a normal Main Render 36 seconds after Spec Sculpt
        // silently replaced the chosen material with the pre-existing whole-car
        // zone. Preserve the explicit Sculpt result as the authoritative spec
        // payload without mutating any Zone mask, Zone config, or Layer pixels.
        console.log('[doRender] Spec Sculpt lock active: preserving imported spec and omitting', serverZones.length, 'zone override(s) from this render');
        serverZones.splice(0, serverZones.length);
    }
    if (serverZones.length === 0 && !activeSpecPath) {
        const debugInfo = zones.map((z, i) => `Zone${i + 1}[${z.name}]: base=${z.base} finish=${z.finish} color=${z.color} colorMode=${z.colorMode}`).join('\n');
        console.warn('[doRender] No valid zones! Zone details:\n' + debugInfo);
        showToast('To render: pick a color on the paint (Pick + Add), then assign a Finish from the library to each zone. Both are required.', true);
        return;
    }
    if (serverZones.length > 0 && serverZones.length < zones.length) {
        const skipped = zones.length - serverZones.length;
        showToast(`Rendering ${serverZones.length} zones. ${skipped} skipped — assign a Finish + color to include them.`, false);
    }
    if (serverZones.length === 0 && activeSpecPath) {
        console.log('[doRender] No user zones, but imported spec canvas exists - rendering with spec canvas only');
        showToast('Rendering with Spec Canvas only (no zone overrides)...');
    }

    const liveLink = document.getElementById('liveLinkCheckbox')?.checked || false;

    // Gather extras (wear, export, output folder)
    const extras = {};
    const outputDir = document.getElementById('outputDir').value.trim();
    const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
    const exportZip = document.getElementById('exportZipCheckbox')?.checked || false;
    if (outputDir) extras.output_dir = outputDir;
    if (wearLevel > 0) extras.wear_level = wearLevel;
    if (exportZip) extras.export_zip = true;
    const dualSpec = document.getElementById('dualSpecCheckbox')?.checked || false;
    if (dualSpec) {
        extras.dual_spec = true;
        extras.night_boost = parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7');
    }

    // Change File/browser-selected flat images can use visible-canvas payloads when
    // no usable disk path exists. If a full Source Paint path is present, prefer server disk
    // reads so external edits are never masked by stale in-memory canvas bytes.
    if (hasLiveFlatSource && !extras.paint_image_base64) {
        const flatCanvas = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
            ? window.buildLivePaintCompositeCanvas()
            : document.getElementById('paintCanvas');
        if (flatCanvas) {
            extras.paint_image_base64 = await canvasToBase64Async(flatCanvas);
            extras.source_mode = 'live_flat_canvas';
            console.log('[doRender] Live flat image source: sending visible canvas as base64 paint', window._spbFlatPaintLiveSource);
        }
    }

    // Import spec map (merge mode) — from SHOKK or manual import; use window fallback so SHOKK-loaded spec is never missed
    if (activeSpecPath) {
        extras.import_spec_map = activeSpecPath;
        console.log('[doRender] Merge mode: imported spec map =', activeSpecPath);
    }

    // Decals: composite paint + decals and send as image so render includes them
    // [PERF] Use async canvasToBase64Async (toBlob) instead of sync toDataURL (~2-3x faster)
    if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
        const compositeCanvas = compositeDecalsForRender();
        if (compositeCanvas) {
            extras.paint_image_base64 = await canvasToBase64Async(compositeCanvas);
        }
        // Send separate decal-only alpha mask
        if (typeof compositeDecalMaskForRender === 'function') {
            const maskDataUrl = compositeDecalMaskForRender();
            if (maskDataUrl) extras.decal_mask_base64 = maskDataUrl;
        }
        // Send per-decal spec finish info to server
        const decalSpecs = decalLayers
            .filter(dl => dl.visible && dl.specFinish && dl.specFinish !== 'none')
            .map(dl => ({ specFinish: dl.specFinish }));
        if (decalSpecs.length > 0) {
            extras.decal_spec_finishes = decalSpecs;
        }
    }

    // PSD/Layer mode: if any PSD layers exist (loaded from PSD OR added by user),
    // always send the live composited canvas as the paint source so user edits
    // (erase, paint, move, transforms, layer effects) actually appear in the render.
    if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded &&
        typeof _psdLayers !== 'undefined' && _psdLayers.length > 0 &&
        !extras.paint_image_base64) {
        const pc = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
            ? window.buildLivePaintCompositeCanvas()
            : document.getElementById('paintCanvas');
        if (pc) {
            extras.paint_image_base64 = await canvasToBase64Async(pc);
            console.log('[doRender] Layer mode: sending live canvas as base64 paint (' + _psdLayers.length + ' layers)');
        }
    }


    // Spec Stamps: composite stamp images and send to server
    // [PERF] Use async canvasToBase64Async
    if (typeof compositeStampsForRender === 'function' && typeof window.stampLayers !== 'undefined' && window.stampLayers.length > 0) {
        const stampCanvas = compositeStampsForRender();
        if (stampCanvas) {
            extras.stamp_image_base64 = await canvasToBase64Async(stampCanvas);
            extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';
            console.log('[doRender] Stamp overlay included:', window.stampLayers.filter(function(s) { return s.visible; }).length, 'visible stamps, finish=' + (window.stampSpecFinish || 'gloss'));
        }
    }

    // Final source-of-truth sync: render exactly what the painter currently sees.
    // This avoids disk-path vs live-canvas drift for Change File / flat workflows.
    try {
        if (!extras.paint_image_base64) {
            const _pcFinal = (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function')
                ? window.buildLivePaintCompositeCanvas()
                : document.getElementById('paintCanvas');
            if (_pcFinal && _pcFinal.width > 0 && _pcFinal.height > 0) {
                extras.paint_image_base64 = await canvasToBase64Async(_pcFinal);
                extras.source_mode = hasLiveFlatSource ? 'live_flat_canvas' : (_diskPaintPath ? 'canvas_sync_from_disk_path' : 'canvas_sync');
            }
        }
    } catch (e) {
        console.warn('[doRender] final canvas sync skipped:', e);
    }

    // [IMP-27] Pre-render validation — warn or abort on obviously-bad config
    const _preIssues = validateRenderPayload(paintFile, serverZones, extras);
    for (const iss of _preIssues) {
        if (iss.severity === 'error') { showToast('Cannot render: ' + iss.msg, true); return; }
        else console.warn('[doRender] validation warning:', iss.msg);
    }

    // [IMP-28] Smart deduplication — skip if zones+extras unchanged from last successful render
    const _fp = _zonesFingerprint(serverZones, extras);
    if (_fp && _fp === _lastRenderFingerprint && document.getElementById('skipDuplicateRenders')?.checked) {
        showToast('Zones unchanged since last render — skipping. Uncheck "Skip duplicates" to force.', false);
        return;
    }

    // Show progress // [26-30] loading indicators
    const btn = document.getElementById('btnRender');
    const bar = document.getElementById('renderProgress');
    const barInner = document.getElementById('renderProgressBar');
    const barText = document.getElementById('renderProgressText');
    const zoneCount = serverZones.length;
    const timeEst = smartEstimateRenderTime(zoneCount); // [IMP-29] use smart estimator that learns from history
    if (btn) { // [53] null check
        btn.textContent = easySculptSpecOnly ? 'RENDERING SPEC SCULPT...' : `RENDERING ${zoneCount} ZONE${zoneCount > 1 ? 'S' : ''}...`;
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
        btn.disabled = true; // [26] disable button during render
    }
    showToast(easySculptSpecOnly
        ? `Rendering the active Spec Sculpt material. Estimated: ${timeEst}`
        : `Rendering ${zoneCount} zone${zoneCount > 1 ? 's' : ''}. Estimated: ${timeEst}`, false); // [32] show estimate in toast
    if (bar) bar.classList.add('active'); // [54] null check
    if (barInner) barInner.style.width = '5%'; // [54] null check
    if (barText) barText.textContent = `Preparing render... (Estimated: ${timeEst})`; // [33] show estimate in progress bar
    startRenderTimer();
    // After RENDER_TERMINATE_DELAY_MS, enable TERMINATE mode on the button // [44] named constant
    const _terminateTimeout = setTimeout(() => {
        if (btn) { // [55] null check
            btn.classList.add('terminate-mode');
            btn.textContent = 'TERMINATE RENDER';
            btn.disabled = false; // [27] re-enable for terminate click
            btn.onclick = function () {
                ShokkerAPI.cancelRender();
                if (btn) {
                    btn.textContent = 'CANCELLING...';
                    btn.classList.remove('terminate-mode');
                    btn.style.opacity = '0.5';
                    btn.style.pointerEvents = 'none';
                    btn.disabled = true; // [28] disable during cancel
                }
            };
        }
    }, RENDER_TERMINATE_DELAY_MS);
    // Poll /api/render-status for progress // [44] named constant
    const _progressPoll = setInterval(async () => {
        try {
            const resp = await fetch(ShokkerAPI.baseUrl + '/api/render-status', {
                signal: AbortSignal.timeout(API_TIMEOUT_STATUS_MS), // [9] timeout on poll
            });
            if (resp.ok) {
                const status = await safeParseJSON(resp, 'render status');
                if (status.active && status.total_zones > 0) {
                    const pct = Math.max(5, Math.min(95, status.percent));
                    if (barInner) barInner.style.width = pct + '%'; // [54] null check
                    if (barText) {
                        // [IMP-30] Phase-based progress text instead of bare zone counter
                        const phaseLabel = formatProgressPhase(status);
                        barText.textContent = phaseLabel || (`Rendering zone ${status.current_zone} of ${status.total_zones}` +
                            (status.zone_name ? ` — ${status.zone_name}` : '') + '...');
                    }
                } else if (status.stage === 'preparing') {
                    if (barInner) barInner.style.width = '5%';
                    if (barText) barText.textContent = `Preparing render... (Estimated: ${timeEst})`; // [34] estimate in preparing
                }
            }
        } catch (_) { /* ignore polling errors */ }
    }, RENDER_PROGRESS_POLL_MS);

    try {
        const result = await ShokkerAPI.render(paintFile, serverZones, iracingId, 51, liveLink, extras);
        clearInterval(_progressPoll);
        stopRenderTimer();
        if (barInner) barInner.style.width = '100%';
        if (barText) barText.textContent = 'Complete!';

        if (result.success) {
            // [IMP-31] Record render time for smart estimator
            recordRenderTime(result.zone_count || zoneCount, result.elapsed_seconds || 0);
            // [IMP-32] Update successful-render fingerprint for dedup
            _lastRenderFingerprint = _fp;
            // [IMP-33] Post-render verification — confirm preview URLs exist
            if (!result.preview_urls || Object.keys(result.preview_urls).length === 0) {
                console.warn('[doRender] Server reported success but returned no preview URLs!');
                showToast('Render succeeded but no preview files were returned. Check server logs.', true);
            }

            let msg = easySculptSpecOnly
                ? `Rendered the active Spec Sculpt material in ${result.elapsed_seconds}s`
                : `Rendered ${result.zone_count} zones in ${result.elapsed_seconds}s`;
            if (result.includes?.helmet) msg += ' + helmet';
            if (result.includes?.suit) msg += ' + suit';
            if (result.includes?.wear) msg += ` (wear ${result.wear_level})`;
            if (result.output_dir?.success) {
                msg += ` | Saved to ${result.output_dir.pushed_files?.length || 0} files!`;
            } else if (result.output_dir?.error) {
                msg += ' | OUTPUT FOLDER ERROR: ' + result.output_dir.error;
            }
            if (result.live_link?.success) {
                msg += ' | Files pushed to iRacing!';
            }
            showToast(msg);
            RenderNotify.onRenderComplete(true, result.elapsed_seconds, result.zone_count);
            // [IMP-34] Browser notification + optional ding
            notifyRenderComplete(true, result.zone_count, result.elapsed_seconds);
            playRenderDing(true);

            // Show both previews in the results panel (NOT on the source canvas)
            showRenderResults(result);
        } else if (result.error_code === 'pack_missing') {
            // This finish depends on an un-bundled reference_textures Finish Pack
            // the buyer hasn't downloaded. Steer them to the in-app downloader
            // instead of surfacing a misleading "paint file path" error.
            promptFinishPackDownload(result);
            RenderNotify.onRenderComplete(false, 0, 0);
            notifyRenderComplete(false, 0, 0);
            playRenderDing(false);
        } else if (result.license_required) {
            showToast('License required for full renders. Open Settings to enter your key.', true);
            licenseActive = false;
            RenderNotify.onRenderComplete(false, 0, 0);
        } else {
            const err = result.error || 'unknown';
            // [IMP-35] More categories in error mapping (paint missing, license, server hung, etc.)
            const friendly = (err.includes('Paint file not found') || err.includes('not found'))
                ? 'Paint file not found. Check the Source Paint path.'
                : (err.includes('No zones') || err.includes('zones'))
                    ? 'No valid zones. Add a finish and color to at least one zone.'
                    : (err.includes('License') || err.includes('license'))
                        ? 'License required. Open Settings to enter your key.'
                        : (err.includes('hung') || err.includes('timeout'))
                            ? 'Engine appears hung - it recovers automatically; if not, close and reopen Shokker Paint Booth.'
                            : (err.includes('memory') || err.includes('OOM'))
                                ? 'Out of memory. Try fewer zones or simpler patterns.'
                                : err;
            showRetryableToast('Render failed: ' + friendly, () => doRender());
            RenderNotify.onRenderComplete(false, 0, 0);
            notifyRenderComplete(false, 0, 0);
            playRenderDing(false);
        }
    } catch (e) {
        clearInterval(_progressPoll);
        stopRenderTimer();
        if (e.name === 'AbortError') {
            showToast('Render cancelled.', false);
        } else if (e.name === 'TimeoutError') { // [40] specific timeout error
            showToast('Render timed out after 5 minutes. Try fewer zones or simpler finishes.', true);
        } else if (e.message && (e.message.includes('Failed to fetch') || e.message.includes('NetworkError'))) { // [38] specific
            showToast(SPB_ENGINE_OFFLINE_MSG, true);
        } else if (e.message && e.message.includes('JSON')) { // [39] JSON parse error
            showToast('Engine returned an invalid response - if it keeps happening, close and reopen Shokker Paint Booth.', true);
        } else {
            showToast(classifyFetchError(e, 'Render'), true); // [12] user-friendly error
        }
        if (typeof RenderNotify !== 'undefined') RenderNotify.onRenderComplete(false, 0, 0); // [55] null check
    } finally {
        clearTimeout(_terminateTimeout);
        clearInterval(_progressPoll);
        ShokkerAPI._renderAbort = null;
        ShokkerAPI._renderInProgress = false; // [20] clear dedup flag
        setTimeout(() => {
            _ensureRenderFloatVisible();
            if (btn) { // [53] null check
                btn.textContent = 'RENDER'; try { var _rs = document.getElementById('spbRenderStatus'); if (_rs) _rs.textContent = 'last render ' + new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}); } catch (_e) {}
                btn.classList.remove('terminate-mode');
                btn.style.opacity = '1';
                btn.style.pointerEvents = '';
                btn.disabled = false; // [29] re-enable button
                btn.onclick = function () { safeDoRender(); };
            }
            if (bar) bar.classList.remove('active'); // [54] null check
            if (barInner) barInner.style.width = '0%'; // [54] null check
            if (barText) barText.textContent = '';
        }, RENDER_RESET_DELAY_MS); // [45] named constant
    }
}

/**
 * Format a zone's color data for the server API. // [47]
 * Handles multi-pick, picker, string, and object color modes.
 * @param {*} color - Raw color value from zone
 * @param {Object} zone - Zone object with colorMode, colors, etc.
 * @returns {*} Formatted color for server payload
 */
function formatColorForServer(color, zone) {
    if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
        return zone.colors.map(c => ({ color_rgb: c.color_rgb, tolerance: c.tolerance || 40 }));
    }
    if (zone.colorMode === 'picker' && zone.pickerColor) {
        const hex = zone.pickerColor;
        const r = parseInt(hex.substr(1, 2), 16);
        const g = parseInt(hex.substr(3, 2), 16);
        const b = parseInt(hex.substr(5, 2), 16);
        return { color_rgb: [r, g, b], tolerance: zone.pickerTolerance || 40 };
    }
    if (typeof color === 'string') return color;
    if (color && typeof color === 'object' && !Array.isArray(color)) return color;
    return 'everything';
}


function _ensureRenderFloatVisible() {
    try {
        const renderFloat = document.getElementById('renderFloat');
        if (!renderFloat) return;
        const bar = document.getElementById('previewBottomBar');
        if (bar) {
            // [SPB QoL 2026-06-02 owner v2] Dock RENDER/Shortcuts INTO the bottom command bar, to the
            // RIGHT of the +Add/Exclude/Set/Use-Region note (in the empty space at that row) — NOT
            // floated at the bottom-right corner. In-flow = correct height, responsive, never covers
            // the zone controls. Owner: "go BESIDE that note where the empty space is."
            if (renderFloat.parentElement !== bar) bar.appendChild(renderFloat);
            // [SPB-HEADER-SLIM 2026-08-29] owner: "RENDER moves when you click it the first time".
            // The 2026-06-02 dock-right re-parent + inline shrink fought the 2026-07-18b bar
            // rebuild (renderFloat is built FIRST in the bar); the fight fired on first click.
            // The float now stays where the builder put it; CSS owns the button size.
            ['position', 'left', 'right', 'top', 'bottom', 'transform', 'width', 'max-width', 'max-height', 'z-index']
                .forEach(p => renderFloat.style.removeProperty(p));
            renderFloat.style.setProperty('display', 'flex', 'important');
            renderFloat.style.setProperty('visibility', 'visible', 'important');
            renderFloat.style.setProperty('opacity', '1', 'important');
            renderFloat.style.setProperty('flex', '0 0 auto', 'important');
 // push to the far right
            renderFloat.style.setProperty('pointer-events', 'auto', 'important');
        } else {
            // Fallback (unified bottom bar absent): right-aligned fixed, NOT dead-center.
            if (document.body && renderFloat.parentElement !== document.body) document.body.appendChild(renderFloat);
            renderFloat.style.setProperty('display', 'flex', 'important');
            renderFloat.style.setProperty('visibility', 'visible', 'important');
            renderFloat.style.setProperty('opacity', '1', 'important');
            renderFloat.style.setProperty('position', 'fixed', 'important');
            renderFloat.style.setProperty('left', 'auto', 'important');
            renderFloat.style.setProperty('right', '14px', 'important');
            renderFloat.style.setProperty('transform', 'none', 'important');
            renderFloat.style.setProperty('bottom', '8px', 'important');
            renderFloat.style.setProperty('z-index', '1500', 'important');
            renderFloat.style.setProperty('pointer-events', 'auto', 'important');
            renderFloat.style.setProperty('width', 'min(280px, calc(100vw - 14px))', 'important');
        }

        const mainBtn = renderFloat.querySelector('#btnRender');
        if (mainBtn && mainBtn.style) {
        }
    } catch (err) {
        console.warn('[renderFloat] visibility guard failed:', err);
    }
}

/**
 * Display render results in the results panel. // [48]
 * Shows paint/spec previews, helmet/suit extras, live link status, and updates history.
 * @param {Object} result - Server render result containing preview_urls, elapsed_seconds, etc.
 */
function showRenderResults(result) {
    // Stop render pulse after first successful render
    hasRenderedOnce = true;
    const renderBtn = document.getElementById('btnRender');
    if (renderBtn) renderBtn.classList.remove('pulse');
    _ensureRenderFloatVisible();

    // Track job ID for one-click deploy
    lastRenderedJobId = result.job_id || null;
    // Show deploy row and load car list
    const deployRow = document.getElementById('renderDeployRow');
    const deployStatus = document.getElementById('deployStatus');
    if (deployRow) {
        if (lastRenderedJobId) {
            deployRow.style.display = 'block';
            if (deployStatus) deployStatus.textContent = '';
            loadIracingCars();
        } else {
            deployRow.style.display = 'none';
            if (deployStatus) deployStatus.textContent = '';
        }
    }

    // Show paint + spec previews in the results panel WITHOUT touching the source canvas
    const panel = document.getElementById('renderResultsPanel');
    const paintImg = document.getElementById('renderPaintPreview');
    const specImg = document.getElementById('renderSpecPreview');
    const paintLabel = document.getElementById('renderPaintPreviewLabel');
    const specLabel = document.getElementById('renderSpecPreviewLabel');
    const elapsed = document.getElementById('renderElapsed');
    const llMsg = document.getElementById('renderLiveLinkMsg');

    if (!panel) return;

    // Find preview URLs from the result
    const urls = result.preview_urls || {};
    const paintUrl = Object.entries(urls).find(([k]) => k === 'RENDER_paint.png')
        || Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet') && !k.includes('suit'));
    const specUrl = Object.entries(urls).find(([k]) => k.includes('spec') && !k.includes('helmet') && !k.includes('suit'));
    const downloadKeys = Object.keys(result.download_urls || {});
    const paintDownloadKey = downloadKeys.find(k => /^car_num_\d+$/.test(k))
        || downloadKeys.find(k => /^car_\d+$/.test(k));
    const specDownloadKey = downloadKeys.find(k => /^car_spec_\d+$/.test(k));
    if (paintLabel) paintLabel.textContent = paintDownloadKey ? `PAINT (${paintDownloadKey}.tga)` : 'PAINT';
    if (specLabel) specLabel.textContent = specDownloadKey ? `SPEC MAP (${specDownloadKey}.tga)` : 'SPEC MAP';

    const cacheBust = '?v=' + (window.APP_SESSION_ID || Date.now());
    if (paintImg && paintUrl) paintImg.src = ShokkerAPI.baseUrl + paintUrl[1] + cacheBust;
    if (specImg && specUrl) specImg.src = ShokkerAPI.baseUrl + specUrl[1] + cacheBust;
    // [IMP] Attach eyedropper to paint preview (toast color on click)
    if (paintImg && !paintImg._spbEyedropperBound) { attachEyedropperToImage(paintImg); paintImg._spbEyedropperBound = true; }
    // [IMP] Sync scroll/zoom between paint & spec preview panes
    if (paintImg && specImg && !paintImg._spbSyncBound) { syncPreviewPanes('renderPaintPreview', 'renderSpecPreview'); paintImg._spbSyncBound = true; }

    // Load rendered paint for Before/After compare mode
    if (paintUrl) {
        loadRenderedImageForCompare(ShokkerAPI.baseUrl + paintUrl[1] + cacheBust);
    }

    // [SPB LIVE-PANE SYNC 2026-08-16 — owner: "the LIVE PREVIEW starts to DEGRADE as we go"]
    // Diagnosis from the owner's console log: across ~11 full renders the live pane updated
    // ONCE. Full renders only ever touched THIS results panel; the live pane refreshes solely
    // through doPreviewRender, whose dedupe keys on the ZONE CONFIG hash — and LAYER-content
    // edits (mask painting, PSD layer moves) never change that hash, so in Layer mode the pane
    // drifted further behind the design with every iteration ("degradation" = staleness; page
    // reload rebuilt everything = the "heal"). A completed full render is the freshest truth
    // available at 2048 — push it into the live pane every time. The per-render job id makes
    // the URL unique, so no stale-cache concerns.
    try {
        const _lpImg = document.getElementById('livePreviewImg');
        const _lpSpec = document.getElementById('livePreviewSpecImg');
        if (_lpImg && paintUrl) {
            _lpImg.src = ShokkerAPI.baseUrl + paintUrl[1] + cacheBust;
            const _pPane = document.getElementById('previewPaintPane');
            if (_pPane) _pPane.style.display = '';
            const _pEmpty = document.getElementById('previewEmpty');
            if (_pEmpty) _pEmpty.style.display = 'none';
        }
        if (_lpSpec && specUrl) _lpSpec.src = ShokkerAPI.baseUrl + specUrl[1] + cacheBust;
    } catch (_) { /* live-pane sync must never break the render flow */ }

    // Elapsed + zone info
    let elapsedText = `${result.elapsed_seconds}s | ${result.zone_count} zones`;
    if (elapsed) elapsed.textContent = elapsedText;

    // Wear badge
    const wearBadge = document.getElementById('renderWearBadge');
    if (wearBadge) {
        if (result.includes?.wear && result.wear_level > 0) {
            wearBadge.textContent = `WEAR: ${result.wear_level}%`;
            wearBadge.style.display = 'inline-block';
        } else {
            wearBadge.style.display = 'none';
        }
    }

    // Helmet + Suit previews are retired in this booth build.
    const helmetSuitRow = document.getElementById('renderHelmetSuitRow');
    const helmetCol = document.getElementById('renderHelmetCol');
    const suitCol = document.getElementById('renderSuitCol');
    const helmetImg = document.getElementById('renderHelmetPreview');
    const suitImg = document.getElementById('renderSuitPreview');

    if (helmetImg) helmetImg.removeAttribute('src');
    if (suitImg) suitImg.removeAttribute('src');
    if (helmetCol) helmetCol.style.display = 'none';
    if (suitCol) suitCol.style.display = 'none';
    if (helmetSuitRow) helmetSuitRow.style.display = 'none';

    // Night spec preview
    const nightRow = document.getElementById('renderNightRow');
    const nightImg = document.getElementById('renderNightPreview');
    if (nightRow && nightImg) {
        const nightUrl = Object.entries(urls).find(([k]) => k.includes('spec_night') && !k.includes('helmet') && !k.includes('suit'));
        if (nightUrl) {
            nightImg.src = ShokkerAPI.baseUrl + nightUrl[1] + cacheBust;
            nightRow.style.display = 'flex';
        } else {
            nightRow.style.display = 'none';
        }
    }

    // Export ZIP link
    const zipRow = document.getElementById('renderZipRow');
    const zipLink = document.getElementById('renderZipLink');
    if (zipRow && zipLink) {
        if (result.export_zip_url) {
            zipLink.href = ShokkerAPI.baseUrl + result.export_zip_url;
            zipRow.style.display = 'block';
        } else {
            zipRow.style.display = 'none';
        }
    }

    // Output directory + live link combined status
    if (llMsg) {
        let msgParts = [];
        const requestedLiveLink = !!(result.live_link || document.getElementById('liveLinkCheckbox')?.checked);
        // Show output_dir status (primary output)
        if (result.output_dir?.success) {
            const fileCount = result.output_dir.pushed_files?.length || 0;
            msgParts.push(`<span style="color:var(--accent-green)"><strong>&#10003; Saved ${fileCount} files</strong> to <code>${_spbEscapeRenderHtml(result.output_dir.path)}</code></span>`);
        } else if (result.output_dir?.error) {
            msgParts.push(`<span style="color:#ff4444"><strong>&#10007; Output Error:</strong> ${_spbEscapeRenderHtml(result.output_dir.error)}</span>`);
        }
        if (result.live_link?.success) {
            const liveCount = result.live_link.pushed_files?.length || 0;
            const livePath = result.live_link.path || result.live_link.active_car_path || result.live_link.destination || 'Live Link destination';
            msgParts.push(`<span style="color:var(--accent-green)"><strong>&#10003; Live Link pushed ${liveCount} files</strong> to <code>${_spbEscapeRenderHtml(livePath)}</code></span>`);
        } else if (result.live_link?.error) {
            msgParts.push(`<span style="color:#ff4444"><strong>&#10007; Live Link Error:</strong> ${_spbEscapeRenderHtml(result.live_link.error)}</span>`);
        } else if (requestedLiveLink) {
            msgParts.push(`<span style="color:var(--text-dim)"><strong>Live Link:</strong> no deployment status returned. Verify the destination folder timestamp before blaming iRacing.</span>`);
        }
        // Show iRacing reload instruction (if live link or output_dir succeeded)
        if (result.live_link?.success || result.output_dir?.success) {
            msgParts.push(`<span style="color:var(--accent-gold); font-size:10px;">💡 <strong>Alt+Tab</strong> to iRacing and press <strong>Ctrl+R</strong> to see your new render!</span>`);
        }
        if (msgParts.length > 0) {
            llMsg.style.display = 'block';
            llMsg.style.borderColor = (result.output_dir?.error || result.live_link?.error) ? '#ff4444' : (result.output_dir?.success || result.live_link?.success ? 'var(--accent-green)' : 'var(--accent)');
            llMsg.innerHTML = msgParts.join('<br>');
        } else {
            // No output_dir and no live_link - warn user
            llMsg.style.display = 'block';
            llMsg.style.borderColor = 'var(--accent-gold)';
            llMsg.style.color = 'var(--accent-gold)';
            llMsg.innerHTML = '<strong>&#9888; No output folder set!</strong> Set the "iRacing Car Folder" path in the header to save files. Previews are still available below.';
        }
    }

    // 2026-06-07 render status banner (owner: keep card + show status)
    // The recipe card pops full-screen over #renderLiveLinkMsg, so testers couldn't see whether
    // the render actually saved. Surface a prominent, always-visible banner PINNED at the top of
    // the modal (above the card image) using the SAME result fields the #renderLiveLinkMsg logic
    // above checks: a save SUCCEEDED iff result.output_dir?.success OR result.live_link?.success;
    // otherwise (neither set, the "No output folder set!" path) we show the amber folder warning.
    const _statusBanner = document.getElementById('renderStatusBanner');
    if (_statusBanner) {
        const _saveSucceeded = !!(result.output_dir?.success || result.live_link?.success);
        const _saveErrored = !!(result.output_dir?.error || result.live_link?.error);
        const _savedPath = result.output_dir?.path
            || result.live_link?.path
            || result.live_link?.active_car_path
            || result.live_link?.destination
            || '';
        _statusBanner.style.display = 'block';
        // 2026-10-04 SHOW MY FILES (owner: a buyer kept looking in the wrong folder for his car_num/car_spec files and
        // tried uploading the .shokker project to Trading Paints). Name the exact files and open Explorer ON them.
        const _pushed = (result.output_dir?.success && result.output_dir.pushed_files) || (result.live_link?.success && result.live_link.pushed_files) || [];
        const _paintName = _pushed.find(n => /^car_(num_)?\d+\.tga$/i.test(n)) || '';
        const _specName = _pushed.find(n => /^car_spec_\d+\.tga$/i.test(n)) || '';
        const _jobPaintKey = Object.keys(result.download_urls || {}).find(k => /^car_(num_)?\d+$/i.test(k));
        _spbLastRenderFiles = _saveSucceeded
            ? { folder: _savedPath, select: _paintName }
            : (!_saveErrored && result.job_id ? { job_id: result.job_id, select: _jobPaintKey ? _jobPaintKey + '.tga' : '' } : null);
        const _showBtn = (label) => ` <button type="button" class="spb-show-files-btn" style="margin-left:6px; padding:3px 10px; font-weight:700; cursor:pointer; border-radius:4px; border:1px solid currentColor; background:transparent; color:inherit;">&#128194; ${label}</button>`;
        if (_saveSucceeded) {
            // Green success line — reuse the existing "Alt+Tab → Ctrl+R" hint + show the saved path.
            _statusBanner.style.background = 'rgba(0,255,136,0.14)';
            _statusBanner.style.border = '2px solid var(--accent-green, #00ff88)';
            _statusBanner.style.color = 'var(--accent-green, #00ff88)';
            const _pathHtml = _savedPath
                ? ` <span style="color:var(--text-dim); font-weight:600;">&rarr; <code>${_spbEscapeRenderHtml(_savedPath)}</code></span>`
                : '';
            const _filesHtml = _paintName
                ? '<div style="margin-top:5px; font-size:12px; color:var(--text, #ddd); font-weight:600;">Your iRacing files: <code>' + _spbEscapeRenderHtml(_paintName) + '</code>' +
                  (_specName ? ' + <code>' + _spbEscapeRenderHtml(_specName) + '</code>' : '') +
                  '. <b>Trading Paints:</b> upload <code>' + _spbEscapeRenderHtml(_paintName) + '</code> as the paint (never the .spb / .shokk file you save, that is your Shokker project). ' +
                  'The spec must be the <code>.mip</code> iRacing makes next to it the first time you drive the car.</div>'
                : '';
            _statusBanner.innerHTML =
                '<strong style="font-size:14px;">&#10003; Saved!</strong> ' +
                '<strong>Alt+Tab</strong> to iRacing and press <strong>Ctrl+R</strong> to load it on your car.' +
                _pathHtml + _showBtn('Show my files') + _filesHtml;
        } else if (_saveErrored) {
            // A save was attempted but the folder errored — surface it clearly (red).
            const _errMsg = result.output_dir?.error || result.live_link?.error || 'Unknown save error.';
            _statusBanner.style.background = 'rgba(255,68,68,0.14)';
            _statusBanner.style.border = '2px solid #ff4444';
            _statusBanner.style.color = '#ff6b6b';
            _statusBanner.innerHTML =
                '<strong style="font-size:14px;">&#10007; Save failed</strong> &mdash; ' +
                _spbEscapeRenderHtml(_errMsg) +
                ' Check your iRacing Car Folder in the header.';
        } else {
            // No output folder set — amber warning (matches the #renderLiveLinkMsg "No output folder set!" path).
            _statusBanner.style.background = 'rgba(255,176,0,0.14)';
            _statusBanner.style.border = '2px solid var(--accent-gold, #ffb000)';
            _statusBanner.style.color = 'var(--accent-gold, #ffb000)';
            _statusBanner.innerHTML =
                '<strong style="font-size:14px;">&#9888; No iRacing folder set</strong> &mdash; ' +
                'set your <strong>iRacing Car Folder</strong> in the header or the paint won\'t appear on your car.' +
                (_spbLastRenderFiles ? '<div style="margin-top:5px; font-size:11px; font-weight:600;">This render is only in Shokker\'s own render folder (iRacing never looks there, and only the two newest renders are kept).' + _showBtn('Show where it was saved') + '</div>' : '');
        }
        const _showFilesBtn = _statusBanner.querySelector('.spb-show-files-btn');
        if (_showFilesBtn) _showFilesBtn.addEventListener('click', () => spbShowRenderFiles(_showFilesBtn));
    }

    // [SPB-RECIPE-CARD-001] Show as a FLOATING modal (NOT inline) so it can never shove the
    // center column down. The card is dismissed manually (X / ESC / backdrop click).
    panel.style.display = 'block';
    panel.style.marginBottom = '';
    panel.scrollTop = 0;
    const _recipeBackdrop = document.getElementById('renderResultsBackdrop');
    if (_recipeBackdrop) _recipeBackdrop.style.display = 'block';
    try { document.addEventListener('keydown', _renderRecipeEscHandler); } catch (_) {}
    // [SPB-RECIPE-CARD-002] Render the designed, shareable recipe card (logo + hero snapshots +
    // FULL per-zone recipe) onto a canvas. Falls back to the simple HTML table if anything throws.
    try { renderRecipeCardUI(result); } catch (e) { console.warn('[recipe] card render failed:', e); try { buildRenderRecipeZones(); } catch (_) {} }

    // Push to render history
    try {
        // [ULTRACODE 2026-08-22 M8b] SAME cacheBust as the results panel —
        // '?v=' vs bare URL are distinct HTTP cache keys, so history-thumb
        // baking re-downloaded the full PNG even with the immutable header.
        const paintUrlFull = paintUrl ? (ShokkerAPI.baseUrl + paintUrl[1] + cacheBust) : '';
        const specUrlFull = specUrl ? (ShokkerAPI.baseUrl + specUrl[1] + cacheBust) : '';
        const summary = zones.map(z => {
            if (z.finish) return `${z.name}: ${z.finish}`;
            if (z.base) return `${z.name}: ${z.base}${z.pattern && z.pattern !== 'none' ? '+' + z.pattern : ''}`;
            return z.name;
        }).join(' | ');
        // [IMP-36] Descriptive filename with zone summary (clamped to safe length)
        const _safeName = (summary || 'render').replace(/[^a-z0-9_-]+/gi, '_').slice(0, 80);
        const _descFilename = `spb_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}_${result.zone_count || 0}z_${_safeName}.png`;
        const _histEntry = {
            job_id: result.job_id || '',
            timestamp: Date.now(),
            elapsed_seconds: result.elapsed_seconds || 0,
            zone_count: result.zone_count || zones.length,
            paint_url: paintUrlFull,
            spec_url: specUrlFull,
            zones_summary: summary,
            // [IMP-37] Per-render notes/tags (user-editable)
            notes: '',
            tags: [],
            favorite: false,
            // [IMP-38] Suggested filename for downloads
            filename: _descFilename,
            // [IMP-39] Bake metadata snapshot for download/permalink
            metadata: { wear: result.wear_level || 0, includes: result.includes || {}, ccVersion: CLIENT_VERSION },
            // [2026-06-12 owner: "EXACTLY REPLICATE THIS"] FULL-FIDELITY zone
            // snapshot. The old whitelist silently dropped every field it
            // didn't know about (spec sliders, base HSB, overlay tiers, blend
            // modes...), so a saved recipe could never round-trip new dials.
            // Now: every serializable zone field rides along automatically;
            // only heavy/transient buffers are skipped.
            zoneSnapshot: JSON.parse(JSON.stringify(zones.map(z => {
                const o = {};
                for (const k of Object.keys(z)) {
                    if (k === 'regionMask' || k === 'spatialMask' || k === 'sourceLayerMask' ||
                        k === 'sourceLayerRgb' || k === 'pattern_strength_map' || k.startsWith('_')) continue;
                    const v = z[k];
                    if (typeof v === 'function' || v === undefined) continue;
                    o[k] = v;
                }
                return o;
            })))
        };
        renderHistory.unshift(_histEntry);
        if (renderHistory.length > MAX_RENDER_HISTORY) renderHistory.pop();
        updateHistoryStrip();
        persistRenderHistory();
        // [SPB HISTORY-THUMBS 2026-08-16] The strip's <img src> pointed at /preview/<job>/ URLs,
        // but the server keeps only the last ~2 job dirs — every strip rebuild refetched every
        // dead job (the owner's log: the SAME stale id 404ing after EVERY render) and old thumbs
        // went blank. Bake a small data-URL thumbnail while the job is still alive; the strip
        // prefers it and it survives job rotation AND app restarts (persisted with the entry).
        if (paintUrlFull) {
            try {
                const _tImg = new Image();
                _tImg.crossOrigin = 'anonymous';
                _tImg.onload = () => {
                    try {
                        const _tc = document.createElement('canvas');
                        const _ts = Math.min(1, 96 / Math.max(_tImg.naturalWidth, _tImg.naturalHeight));
                        _tc.width = Math.max(1, Math.round(_tImg.naturalWidth * _ts));
                        _tc.height = Math.max(1, Math.round(_tImg.naturalHeight * _ts));
                        _tc.getContext('2d').drawImage(_tImg, 0, 0, _tc.width, _tc.height);
                        _histEntry.thumb = _tc.toDataURL('image/jpeg', 0.7);
                        updateHistoryStrip();
                        // The thumbnail arrives asynchronously after the entry
                        // was first saved. Persist again so restart history owns
                        // the durable 96px asset instead of a rotating job URL.
                        persistRenderHistory();
                    } catch (_) { /* tainted canvas or encode failure: strip falls back to the URL */ }
                };
                _tImg.src = paintUrlFull;
            } catch (_) { /* thumbnail is best-effort */ }
        }
        // [SPB-RECENTS-001] persist this render to the rotating last-10 on disk so it can be
        // recalled (full recipe restored) even after an app restart. Fire-and-forget.
        try { saveRecentRenderToDisk(_histEntry); } catch (_) {}
        // [IMP-40] Auto-export hook — write rendered PNG to Documents/SPB_Exports if checkbox set
        if (typeof localStorage !== 'undefined' && localStorage.getItem('shokker_auto_export') === '1' && paintUrlFull) {
            console.log('[auto-export] Render saved; manual download will be triggered by Auto-Export panel.');
        }
    } catch (e) { console.warn('History push failed:', e); }
}

// [IMP-41] Channels view — render R/G/B/A as separate canvas overlays so users can inspect spec map
async function showSpecChannels(specUrl) {
    if (!specUrl) { showToast('No spec URL for channel view', true); return; }
    try {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = specUrl; });
        const w = img.naturalWidth, h = img.naturalHeight;
        const src = document.createElement('canvas'); src.width = w; src.height = h;
        src.getContext('2d').drawImage(img, 0, 0);
        const data = src.getContext('2d').getImageData(0, 0, w, h).data;
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:24px;overflow:auto;';
        overlay.id = 'specChannelsOverlay';
        const labels = [['R — Metallic', 0], ['G — Roughness', 1], ['B — Clearcoat', 2], ['A — Spec Mask', 3]];
        for (const [label, ch] of labels) {
            const c = document.createElement('canvas'); c.width = w; c.height = h;
            const ctx = c.getContext('2d');
            const out = ctx.createImageData(w, h);
            for (let i = 0; i < data.length; i += 4) {
                const v = data[i + ch];
                out.data[i] = v; out.data[i + 1] = v; out.data[i + 2] = v; out.data[i + 3] = 255;
            }
            ctx.putImageData(out, 0, 0);
            const wrap = document.createElement('div');
            wrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px;color:#eee;font-size:12px;';
            wrap.innerHTML = `<div>${label}</div>`;
            const dispScale = Math.min(1, 480 / Math.max(w, h));
            c.style.width = (w * dispScale) + 'px'; c.style.height = (h * dispScale) + 'px';
            c.style.imageRendering = 'pixelated';
            wrap.appendChild(c);
            overlay.appendChild(wrap);
        }
        const close = document.createElement('button');
        close.textContent = 'Close';
        close.style.cssText = 'position:absolute;top:8px;right:8px;padding:6px 12px;';
        close.onclick = () => overlay.remove();
        overlay.appendChild(close);
        document.body.appendChild(overlay);
    } catch (e) {
        showToast('Failed to load spec for channel view: ' + (e.message || e), true);
    }
}
if (typeof window !== 'undefined') window.showSpecChannels = showSpecChannels;

// [IMP-42] Histogram — show pixel distribution of rendered paint
async function showRenderHistogram(paintUrl) {
    if (!paintUrl) { showToast('No paint URL', true); return; }
    try {
        const img = new Image(); img.crossOrigin = 'anonymous';
        await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = paintUrl; });
        const cv = document.createElement('canvas'); cv.width = img.naturalWidth; cv.height = img.naturalHeight;
        cv.getContext('2d').drawImage(img, 0, 0);
        const data = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
        const r = new Uint32Array(256), g = new Uint32Array(256), b = new Uint32Array(256), L = new Uint32Array(256);
        for (let i = 0; i < data.length; i += 4) {
            r[data[i]]++; g[data[i + 1]]++; b[data[i + 2]]++;
            const lum = (data[i] * 0.2126 + data[i + 1] * 0.7152 + data[i + 2] * 0.0722) | 0;
            L[lum]++;
        }
        let max = 0; for (let i = 0; i < 256; i++) { if (r[i] > max) max = r[i]; if (g[i] > max) max = g[i]; if (b[i] > max) max = b[i]; }
        const w = 512, h = 200;
        const c = document.createElement('canvas'); c.width = w; c.height = h;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#111'; ctx.fillRect(0, 0, w, h);
        const draw = (arr, color) => {
            ctx.strokeStyle = color; ctx.beginPath();
            for (let i = 0; i < 256; i++) {
                const x = (i / 255) * w;
                const y = h - (arr[i] / max) * h;
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        };
        draw(r, 'rgba(255,80,80,0.85)');
        draw(g, 'rgba(80,255,80,0.85)');
        draw(b, 'rgba(80,140,255,0.85)');
        draw(L, 'rgba(255,255,255,0.6)');
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:20px;';
        overlay.appendChild(c);
        const lbl = document.createElement('div'); lbl.style.color = '#ddd'; lbl.style.fontSize = '12px';
        lbl.textContent = 'Histogram — R / G / B / Luma (white)';
        overlay.appendChild(lbl);
        const close = document.createElement('button'); close.textContent = 'Close'; close.onclick = () => overlay.remove();
        close.style.cssText = 'padding:6px 14px;';
        overlay.appendChild(close);
        document.body.appendChild(overlay);
    } catch (e) { showToast('Histogram failed: ' + (e.message || e), true); }
}
if (typeof window !== 'undefined') window.showRenderHistogram = showRenderHistogram;

// [IMP-43] Eyedropper / color-pick on rendered output preview
function attachEyedropperToImage(imgEl, callback) {
    if (!imgEl) return;
    imgEl.style.cursor = 'crosshair';
    imgEl.addEventListener('click', async (e) => {
        try {
            const cv = document.createElement('canvas');
            cv.width = imgEl.naturalWidth; cv.height = imgEl.naturalHeight;
            const ctx = cv.getContext('2d');
            ctx.drawImage(imgEl, 0, 0);
            const r = imgEl.getBoundingClientRect();
            const x = ((e.clientX - r.left) / r.width) * cv.width;
            const y = ((e.clientY - r.top) / r.height) * cv.height;
            const px = ctx.getImageData(x | 0, y | 0, 1, 1).data;
            const hex = '#' + [px[0], px[1], px[2]].map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase();
            if (typeof callback === 'function') callback(hex, [px[0], px[1], px[2]]);
            else if (typeof showToast === 'function') showToast(`Picked ${hex} (R:${px[0]} G:${px[1]} B:${px[2]})`);
        } catch (err) { console.warn('eyedropper failed:', err); }
    }, { passive: true });
}
if (typeof window !== 'undefined') window.attachEyedropperToImage = attachEyedropperToImage;

// [IMP-44] Per-zone statistics overlay — compute % metallic / roughness / clearcoat
// BOIL THE OCEAN audit fix: when customSpec/Paint/Bright is null, fall through
// to the actual effective intensity profile for the zone's finish, not an
// arbitrary "50". The slider scale is 0.0–1.0 (see line ~2801 in
// paint-booth-2-state-zones.js), so display as percentage for the overlay.
function computeZoneStats(zones) {
    if (!zones || !zones.length) return [];
    const _IV = (typeof INTENSITY_VALUES !== 'undefined') ? INTENSITY_VALUES : {};
    const _DEFAULT_PROFILE = { spec: 1.0, paint: 1.0, bright: 1.0 };
    return zones.map(z => {
        const intensity = parseInt(z.intensity || '100', 10) / 100;
        const profile = _IV[z.intensity] || _DEFAULT_PROFILE;
        // Effective slider value = explicit custom override OR the intensity profile's value.
        const ms = (z.customSpec != null) ? Number(z.customSpec) : Number(profile.spec || 0);
        const ps = (z.customPaint != null) ? Number(z.customPaint) : Number(profile.paint || 0);
        const bs = (z.customBright != null) ? Number(z.customBright) : Number(profile.bright || 0);
        return {
            name: z.name,
            metallicPct: Math.round(intensity * 100),
            roughnessIdx: Math.round(ms * 100), // 0–100 for overlay readability
            paintIdx: Math.round(ps * 100),
            brightIdx: Math.round(bs * 100),
        };
    });
}
if (typeof window !== 'undefined') window.computeZoneStats = computeZoneStats;

// [IMP-45] Render share — copy a permalink-style URL containing the job_id
function copyRenderShareLink(jobId) {
    if (!jobId) { showToast('No job ID for this render', true); return; }
    const link = `${window.location.origin}/render/${encodeURIComponent(jobId)}`;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(link).then(() => showToast('Render link copied: ' + link)).catch(() => showToast('Could not copy link', true));
    } else {
        const ta = document.createElement('textarea'); ta.value = link; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); showToast('Link copied'); } catch (_) { showToast('Copy failed', true); }
        document.body.removeChild(ta);
    }
}
if (typeof window !== 'undefined') window.copyRenderShareLink = copyRenderShareLink;

// [IMP-46] Render diff — compare two consecutive renders pixel-by-pixel and visualize delta
async function showRenderDiff(idxA, idxB) {
    const a = renderHistory[idxA], b = renderHistory[idxB];
    if (!a || !b) { showToast('Need two history entries', true); return; }
    try {
        const [imgA, imgB] = await Promise.all([a.paint_url, b.paint_url].map(url => new Promise((res, rej) => {
            const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = rej; i.src = url;
        })));
        const w = Math.min(imgA.naturalWidth, imgB.naturalWidth), h = Math.min(imgA.naturalHeight, imgB.naturalHeight);
        const cA = document.createElement('canvas'); cA.width = w; cA.height = h; cA.getContext('2d').drawImage(imgA, 0, 0, w, h);
        const cB = document.createElement('canvas'); cB.width = w; cB.height = h; cB.getContext('2d').drawImage(imgB, 0, 0, w, h);
        const dA = cA.getContext('2d').getImageData(0, 0, w, h).data;
        const dB = cB.getContext('2d').getImageData(0, 0, w, h).data;
        const out = document.createElement('canvas'); out.width = w; out.height = h;
        const oCtx = out.getContext('2d');
        const oimg = oCtx.createImageData(w, h);
        let changedPx = 0;
        for (let i = 0; i < dA.length; i += 4) {
            const dr = Math.abs(dA[i] - dB[i]), dg = Math.abs(dA[i + 1] - dB[i + 1]), db = Math.abs(dA[i + 2] - dB[i + 2]);
            const m = Math.max(dr, dg, db);
            if (m > 4) changedPx++;
            oimg.data[i] = m * 2; oimg.data[i + 1] = 0; oimg.data[i + 2] = m; oimg.data[i + 3] = 255;
        }
        oCtx.putImageData(oimg, 0, 0);
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:20px;';
        const dispScale = Math.min(1, 700 / Math.max(w, h));
        out.style.width = (w * dispScale) + 'px'; out.style.height = (h * dispScale) + 'px';
        const lbl = document.createElement('div'); lbl.style.cssText = 'color:#eee;font-size:13px;';
        lbl.textContent = `Diff #${idxA + 1} vs #${idxB + 1} — ${((changedPx / (w * h)) * 100).toFixed(2)}% pixels differ`;
        overlay.appendChild(lbl); overlay.appendChild(out);
        const close = document.createElement('button'); close.textContent = 'Close'; close.style.cssText = 'padding:6px 14px;';
        close.onclick = () => overlay.remove();
        overlay.appendChild(close);
        document.body.appendChild(overlay);
    } catch (e) { showToast('Diff failed: ' + (e.message || e), true); }
}
if (typeof window !== 'undefined') window.showRenderDiff = showRenderDiff;

// [IMP-47] Render history search/filter — filter by zone summary text + favorites toggle
function filterRenderHistory(query) {
    const q = (query || '').trim().toLowerCase();
    const favOnly = !!(typeof window !== 'undefined' && window._historyFavOnly);
    let arr = renderHistory.map((e, i) => ({ e, i }));
    if (favOnly) arr = arr.filter(({ e }) => e.favorite);
    if (q) arr = arr.filter(({ e }) => (e.zones_summary || '').toLowerCase().includes(q) || (e.notes || '').toLowerCase().includes(q) || (e.tags || []).some(t => t.toLowerCase().includes(q)));
    return arr.map(({ i }) => i);
}
if (typeof window !== 'undefined') window.filterRenderHistory = filterRenderHistory;

// [IMP-48] Delete a history entry
function deleteHistoryItem(idx) {
    if (idx < 0 || idx >= renderHistory.length) return;
    if (!confirm(`Delete render #${idx + 1} from history?`)) return;
    renderHistory.splice(idx, 1);
    updateHistoryStrip();
    persistRenderHistory();
    showToast('Render removed from history');
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}
if (typeof window !== 'undefined') window.deleteHistoryItem = deleteHistoryItem;

// [IMP-49] Toggle favorite on a history entry
function toggleHistoryFavorite(idx) {
    const e = renderHistory[idx];
    if (!e) return;
    e.favorite = !e.favorite;
    updateHistoryStrip();
    persistRenderHistory();
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}
if (typeof window !== 'undefined') window.toggleHistoryFavorite = toggleHistoryFavorite;

// [IMP-50] Pagination helpers — slice history into pages of size N
const HISTORY_PAGE_SIZE = 24;
let _historyPage = 0;
function setHistoryPage(p) {
    const maxPage = Math.max(0, Math.ceil(renderHistory.length / HISTORY_PAGE_SIZE) - 1);
    _historyPage = Math.max(0, Math.min(maxPage, p | 0));
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}
if (typeof window !== 'undefined') window.setHistoryPage = setHistoryPage;

// [IMP-51] Edit notes on a history entry
function editHistoryNotes(idx) {
    const e = renderHistory[idx];
    if (!e) return;
    const v = prompt('Notes for render #' + (idx + 1) + ':', e.notes || '');
    if (v == null) return;
    e.notes = v.slice(0, 500);
    persistRenderHistory();
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}
if (typeof window !== 'undefined') window.editHistoryNotes = editHistoryNotes;

// [IMP-52] Add/remove tags on a history entry
function editHistoryTags(idx) {
    const e = renderHistory[idx];
    if (!e) return;
    const v = prompt('Tags (comma-separated):', (e.tags || []).join(', '));
    if (v == null) return;
    e.tags = v.split(',').map(t => t.trim()).filter(Boolean).slice(0, 12);
    persistRenderHistory();
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}
if (typeof window !== 'undefined') window.editHistoryTags = editHistoryTags;

// [IMP-53] Download a render — paint TGA, spec TGA, or preview PNG
async function downloadRenderFile(url, suggestedName) {
    if (!url) { showToast('No file URL', true); return; }
    try {
        const res = await fetch(url, { signal: AbortSignal.timeout(API_TIMEOUT_HEAVY_MS) });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = suggestedName || 'render.png';
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
        showToast('Downloaded: ' + a.download);
    } catch (e) { showToast('Download failed: ' + (e.message || e), true); }
}
if (typeof window !== 'undefined') window.downloadRenderFile = downloadRenderFile;

// [IMP-54] Export presets — save & load common render configurations to localStorage
const EXPORT_PRESETS_KEY = 'shokker_export_presets';
function listExportPresets() {
    try { return JSON.parse(localStorage.getItem(EXPORT_PRESETS_KEY) || '[]'); }
    catch (_) { return []; }
}
function saveExportPreset(name, data) {
    try {
        const list = listExportPresets();
        const idx = list.findIndex(p => p.name === name);
        const entry = { name, data, savedAt: Date.now() };
        if (idx >= 0) list[idx] = entry; else list.push(entry);
        localStorage.setItem(EXPORT_PRESETS_KEY, JSON.stringify(list.slice(0, 20)));
        showToast('Preset saved: ' + name);
    } catch (e) { showToast('Could not save preset: ' + e.message, true); }
}
function loadExportPreset(name) {
    const list = listExportPresets();
    const p = list.find(x => x.name === name);
    if (!p) { showToast('Preset not found', true); return null; }
    return p.data;
}
function deleteExportPreset(name) {
    const list = listExportPresets().filter(p => p.name !== name);
    localStorage.setItem(EXPORT_PRESETS_KEY, JSON.stringify(list));
    showToast('Preset deleted');
}
if (typeof window !== 'undefined') {
    window.listExportPresets = listExportPresets;
    window.saveExportPreset = saveExportPreset;
    window.loadExportPreset = loadExportPreset;
    window.deleteExportPreset = deleteExportPreset;
}

// [IMP-55] Render scheduling — call doRender at a specific local time (overnight batch)
const _scheduledRenders = [];
function scheduleRender(whenISO, label) {
    const t = new Date(whenISO).getTime();
    if (!isFinite(t) || t <= Date.now()) { showToast('Pick a future time', true); return; }
    const handle = setTimeout(() => {
        showToast('Scheduled render firing: ' + (label || ''));
        try { (window.safeDoRender || doRender)(); } catch (e) { console.error(e); }
    }, t - Date.now());
    _scheduledRenders.push({ when: t, label: label || '', handle });
    showToast(`Scheduled render at ${new Date(t).toLocaleTimeString()}`);
}
function listScheduledRenders() { return _scheduledRenders.map(s => ({ when: new Date(s.when).toISOString(), label: s.label })); }
function cancelScheduledRender(idx) {
    const s = _scheduledRenders[idx];
    if (!s) return;
    clearTimeout(s.handle);
    _scheduledRenders.splice(idx, 1);
    showToast('Scheduled render cancelled');
}
if (typeof window !== 'undefined') {
    window.scheduleRender = scheduleRender;
    window.listScheduledRenders = listScheduledRenders;
    window.cancelScheduledRender = cancelScheduledRender;
}

// [IMP-56] Smart preview scale — pick rendering scale based on viewport / canvas size
function smartPreviewScale(canvasW, canvasH) {
    if (!canvasW || !canvasH) return 1.0;
    const vp = Math.min(window.innerWidth, window.innerHeight);
    if (canvasW <= vp) return 1.0;
    if (canvasW <= vp * 2) return 0.75;
    if (canvasW <= vp * 4) return 0.5;
    return 0.33;
}
if (typeof window !== 'undefined') window.smartPreviewScale = smartPreviewScale;

// [IMP-57] Sync zoom & scroll between paint and spec preview panes
function syncPreviewPanes(paintImgId, specImgId) {
    const a = document.getElementById(paintImgId);
    const b = document.getElementById(specImgId);
    if (!a || !b) return;
    const sync = (src, dst) => {
        dst.style.transform = src.style.transform;
        const pa = src.parentElement, pb = dst.parentElement;
        if (pa && pb) {
            pb.scrollLeft = pa.scrollLeft;
            pb.scrollTop = pa.scrollTop;
        }
    };
    a.addEventListener('scroll', () => sync(a, b), { passive: true });
    b.addEventListener('scroll', () => sync(b, a), { passive: true });
    if (a.parentElement) a.parentElement.addEventListener('scroll', () => sync(a, b), { passive: true });
    if (b.parentElement) b.parentElement.addEventListener('scroll', () => sync(b, a), { passive: true });
}
if (typeof window !== 'undefined') window.syncPreviewPanes = syncPreviewPanes;

// [IMP-58] Progressive image loading — show low-res first, swap to high-res when loaded
function loadProgressiveImage(imgEl, lowSrc, highSrc) {
    if (!imgEl) return;
    if (lowSrc) imgEl.src = lowSrc;
    if (!highSrc) return;
    const hi = new Image();
    hi.onload = () => { imgEl.src = highSrc; };
    hi.onerror = () => { /* keep low-res */ };
    hi.src = highSrc;
}
if (typeof window !== 'undefined') window.loadProgressiveImage = loadProgressiveImage;

// [IMP-59] Better thumbnails — generate a downsampled blob URL for the history strip
async function generateThumbnail(srcUrl, maxDim) {
    maxDim = maxDim || 96;
    try {
        const img = new Image(); img.crossOrigin = 'anonymous';
        await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = srcUrl; });
        const w = img.naturalWidth, h = img.naturalHeight;
        const scale = Math.min(1, maxDim / Math.max(w, h));
        const tw = Math.max(1, (w * scale) | 0), th = Math.max(1, (h * scale) | 0);
        const c = document.createElement('canvas'); c.width = tw; c.height = th;
        c.getContext('2d').drawImage(img, 0, 0, tw, th);
        return await new Promise(res => c.toBlob(b => res(b ? URL.createObjectURL(b) : srcUrl), 'image/webp', 0.85));
    } catch (_) { return srcUrl; }
}
if (typeof window !== 'undefined') window.generateThumbnail = generateThumbnail;

// [IMP-60] TGA loader with progress + ETA + size readout
async function fetchTGAWithProgress(url, onProgress) {
    const t0 = performance.now();
    const ctrl = new AbortController();
    registerController(ctrl);
    try {
        const res = await fetch(url, { signal: ctrl.signal });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const total = parseInt(res.headers.get('Content-Length') || '0', 10);
        const reader = res.body && res.body.getReader ? res.body.getReader() : null;
        if (!reader) {
            const buf = await res.arrayBuffer();
            if (onProgress) onProgress({ loaded: buf.byteLength, total: buf.byteLength, pct: 100, etaMs: 0, sizeMB: (buf.byteLength / 1048576).toFixed(2) });
            return buf;
        }
        const chunks = []; let loaded = 0;
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            chunks.push(value); loaded += value.byteLength;
            const pct = total ? (loaded / total) * 100 : 0;
            const elapsed = performance.now() - t0;
            const etaMs = total && loaded ? Math.max(0, ((elapsed / loaded) * (total - loaded)) | 0) : 0;
            if (onProgress) onProgress({ loaded, total, pct, etaMs, sizeMB: (loaded / 1048576).toFixed(2) });
        }
        const out = new Uint8Array(loaded); let off = 0;
        for (const c of chunks) { out.set(c, off); off += c.byteLength; }
        return out.buffer;
    } finally { unregisterController(ctrl); }
}
if (typeof window !== 'undefined') window.fetchTGAWithProgress = fetchTGAWithProgress;

// [IMP-61] /health endpoint helper — fast checks separate from full /status
async function probeHealth() {
    try {
        const ctrl = new AbortController(); registerController(ctrl);
        const res = await fetch(ShokkerAPI.baseUrl + '/health', {
            signal: AbortSignal.any
                ? AbortSignal.any([ctrl.signal, AbortSignal.timeout(API_TIMEOUT_LIGHT_MS)])
                : ctrl.signal
        });
        unregisterController(ctrl);
        if (!res.ok) return false;
        try { const d = await res.json(); return !!(d && (d.ok || d.status === 'ok')); }
        catch (_) { return res.ok; }
    } catch (_) { return false; }
}
if (typeof window !== 'undefined') window.probeHealth = probeHealth;

// [IMP-62] Stale-request watchdog — periodically abort requests that have been pending too long.
// Simple wall-clock check; real use would track per-controller start times.
const _controllerBirth = new WeakMap();
function registerControllerWithTimer(ctrl, label) {
    if (!ctrl) return ctrl;
    _controllerBirth.set(ctrl, { t: Date.now(), label: label || 'request' });
    return registerController(ctrl);
}
setInterval(() => {
    const now = Date.now();
    for (const ctrl of Array.from(_inFlightControllers)) {
        const meta = _controllerBirth.get(ctrl);
        if (!meta) continue;
        if (now - meta.t > STALE_REQUEST_MS) {
            console.warn(`[stale] aborting ${meta.label} after ${(now - meta.t) / 1000}s`);
            try { ctrl.abort(new DOMException('Stale request', 'TimeoutError')); } catch (_) {}
            _inFlightControllers.delete(ctrl);
        }
    }
}, 15000);
if (typeof window !== 'undefined') window.registerControllerWithTimer = registerControllerWithTimer;

// [IMP-63] Render priority — high (full render) vs low (preview).
// Low-priority work yields if a high-priority job comes in.
let _lowPrioJobs = 0;
function withRenderPriority(priority, fn) {
    if (priority === 'low') {
        _lowPrioJobs++;
        return Promise.resolve().then(fn).finally(() => { _lowPrioJobs--; });
    }
    // high — interrupt low-prio work where possible (best-effort)
    return Promise.resolve().then(fn);
}
function lowPrioJobCount() { return _lowPrioJobs; }
if (typeof window !== 'undefined') {
    window.withRenderPriority = withRenderPriority;
    window.lowPrioJobCount = lowPrioJobCount;
}

function closeRenderResults() {
    const panel = document.getElementById('renderResultsPanel');
    if (panel) {
        panel.style.display = 'none';
        panel.style.marginBottom = '';
    }
    // [SPB-RECIPE-CARD-001] tear down the floating-modal chrome too.
    const backdrop = document.getElementById('renderResultsBackdrop');
    if (backdrop) backdrop.style.display = 'none';
    try { document.removeEventListener('keydown', _renderRecipeEscHandler); } catch (_) {}
}

/** [SPB-RECIPE-CARD-001] ESC closes the render recipe card. */
function _renderRecipeEscHandler(e) {
    if (e && (e.key === 'Escape' || e.key === 'Esc')) {
        e.preventDefault();
        closeRenderResults();
    }
}

/**
 * [SPB-RECIPE-CARD preview-crush PERMANENT FIX — 2026-06-01, per docs/TOOL_QA_PROGRESS.md]
 * Move the recipe modal + its backdrop OUT of #centerPanel to be direct children of <body>.
 *
 * Why: a sibling chat found the recipe modal was crushing the SOURCE + LIVE PREVIEW squares.
 * Two bugs conspired — (1) a forced `display` on `.spb-render-modal` overrode the inline
 * `display:none` (fixed separately: base rule is `display:none`, shown only via inline display),
 * and (2) `#centerPanel > * { position: relative !important }` (ID specificity) beat the modal's
 * `position: fixed`, forcing it IN-FLOW where it squeezed #canvasViewport to ~96px. As a direct
 * child of <body> the modal can NEVER be pinned in-flow by that `#centerPanel > *` rule, so it
 * always floats — this removes the dependency on the CSS specificity battle entirely.
 *
 * Idempotent + defensive; all show/hide + selectors are parent-agnostic so this is purely additive.
 * IMPORTANT for future edits: do NOT put `display: flex !important` (or any forced display) on the
 * base `.spb-render-modal` rule — show/hide runs off inline `display` (block/none).
 */
function _spbDetachRecipeModalToBody() {
    try {
        if (typeof document === 'undefined' || !document.body) return;
        const backdrop = document.getElementById('renderResultsBackdrop');
        const panel = document.getElementById('renderResultsPanel');
        // Move backdrop first, then the panel, so the panel ends up after it in the body.
        if (backdrop && backdrop.parentElement !== document.body) document.body.appendChild(backdrop);
        if (panel && panel.parentElement !== document.body) document.body.appendChild(panel);
    } catch (_) {}
}
if (typeof window !== 'undefined') window._spbDetachRecipeModalToBody = _spbDetachRecipeModalToBody;
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(_spbDetachRecipeModalToBody, 0));
    else setTimeout(_spbDetachRecipeModalToBody, 0);
}

/**
 * [SPB-RECIPE-CARD-001] Build the per-zone recipe breakdown on the render card:
 * for EACH zone, what base color / pattern / finish / spec-pattern overlays /
 * intensity were applied. Reads the LIVE zone state (current at render time) so it
 * always reflects exactly what was just rendered. Owner ask: "a RECIPE CARD that
 * shows what is done to EACH ZONE, any SPEC PATTERNS, OVERLAYS, ETC."
 */
function buildRenderRecipeZones() {
    const host = document.getElementById('renderRecipeZones');
    if (!host) return;
    const zs = (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : [];
    const esc = (typeof _spbEscapeRenderHtml === 'function') ? _spbEscapeRenderHtml : (s => String(s == null ? '' : s));
    if (!zs.length) {
        host.innerHTML = '<div class="render-recipe-empty">No zones configured for this render.</div>';
        return;
    }
    const swatch = (z) => {
        const c = z.color || (Array.isArray(z.colors) && z.colors.length ? z.colors[0] : null) || z.pickerColor || '#222';
        return `<span class="render-recipe-swatch" style="background:${esc(c)}"></span>`;
    };
    const specSummary = (z) => {
        const stack = Array.isArray(z.specPatternStack) ? z.specPatternStack.filter(sp => sp && sp.pattern && sp.pattern !== 'none') : [];
        if (!stack.length) return '<span class="muted">—</span>';
        return stack.map(sp => esc(sp.pattern)).join(', ');
    };
    const patSummary = (z) => {
        const base = (z.pattern && z.pattern !== 'none') ? esc(z.pattern) : '';
        const extra = Array.isArray(z.patternStack) ? z.patternStack.filter(p => p && p.pattern && p.pattern !== 'none').length : 0;
        if (!base && !extra) return '<span class="muted">—</span>';
        return base + (extra ? ` <span class="muted">(+${extra})</span>` : '');
    };
    let html = '<div class="render-recipe-zone-row header">' +
        '<span></span><span>Zone</span><span>Base / Finish</span><span>Pattern</span><span>Spec / Overlay</span><span>Int.</span></div>';
    zs.forEach(z => {
        const finish = (z.finish && z.finish !== 'none') ? esc(z.finish) : '';
        const baseTxt = finish
            ? `<span class="render-recipe-spec">${finish}</span>`
            : (z.base ? esc(z.base) : '<span class="muted">—</span>');
        const intensity = (z.intensity != null && z.intensity !== '') ? esc(z.intensity) + '%' : '—';
        html += '<div class="render-recipe-zone-row">' +
            swatch(z) +
            `<span class="render-recipe-zone-name" title="${esc(z.name || 'Zone')}">${esc(z.name || 'Zone')}</span>` +
            `<span class="render-recipe-cell" title="${finish || esc(z.base || '')}">${baseTxt}</span>` +
            `<span class="render-recipe-cell">${patSummary(z)}</span>` +
            `<span class="render-recipe-cell render-recipe-spec" title="spec pattern overlays">${specSummary(z)}</span>` +
            `<span class="render-recipe-cell">${intensity}</span>` +
            '</div>';
    });
    host.innerHTML = html;
}
if (typeof window !== 'undefined') {
    window.closeRenderResults = closeRenderResults;
    window.buildRenderRecipeZones = buildRenderRecipeZones;
}

// ============================================================================
// [SPB-RECIPE-CARD-002 — 2026-06-01 owner] DESIGNED, SHAREABLE RECIPE CARD.
// Owner: "near-full-screen ... MORE information (opacity, sliders, BASE OVERLAY
// LAYERS) ... a COOL graphical element ... SNAPSHOTS of paint AND combined spec
// ... SHOKKER PAINT BOOTH logo stamped ... look like an actual RECIPE CARD with
// pizzazz ... so people could share RECIPE CARDS." Rendered on a <canvas> (offline
// reliable, full design control, WYSIWYG) so it exports cleanly to PNG / clipboard.
// ============================================================================
const _RC = {
    // [SPB-RECIPE-CARD-005 2026-08-26] gold/black theme matching the Abbey-Road logo banner
    W: 1480, PAD: 46, GAP: 22,
    bg0: '#0b0905', bg1: '#161006',
    panel: 'rgba(26,20,10,0.94)', panelEdge: 'rgba(255,200,80,0.24)',
    ink: '#f6efdc', dim: '#c9b98d', faint: '#8d7f5b',
    blue: '#3b82ff', cyan: '#63d8ff', gold: '#ffd142', goldDeep: '#b8871f', green: '#00e08a',
    mono: "12px 'Consolas','SF Mono','Courier New',monospace",
};
function _rcRoundRect(ctx, x, y, w, h, r) {
    r = Math.max(0, Math.min(r, w / 2, h / 2));
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
}
function _rcChip(ctx, text, x, y, opts) {
    opts = opts || {};
    const padX = 9, h = opts.h || 20;
    ctx.font = opts.font || "700 12px 'Segoe UI',Arial,sans-serif";
    const w = Math.ceil(ctx.measureText(text).width) + padX * 2;
    _rcRoundRect(ctx, x, y, w, h, h / 2);
    ctx.fillStyle = opts.bg || 'rgba(59,130,255,0.18)';
    ctx.fill();
    ctx.fillStyle = opts.color || _RC.cyan;
    ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
    ctx.fillText(text, x + padX, y + h / 2 + 0.5);
    ctx.textBaseline = 'alphabetic';
    return w;
}
function _rcWrap(ctx, text, x, y, maxW, lineH) {
    const words = String(text).split(/\s+/);
    let line = '', yy = y;
    for (const wd of words) {
        const test = line ? line + ' ' + wd : wd;
        if (ctx.measureText(test).width > maxW && line) { ctx.fillText(line, x, yy); yy += lineH; line = wd; }
        else line = test;
    }
    if (line) { ctx.fillText(line, x, yy); yy += lineH; }
    return yy;
}
function _rcWrapCount(ctx, text, maxW) {
    const words = String(text).split(/\s+/);
    let line = '', n = 0;
    for (const wd of words) {
        const test = line ? line + ' ' + wd : wd;
        if (ctx.measureText(test).width > maxW && line) { n++; line = wd; } else line = test;
    }
    if (line) n++;
    return Math.max(1, n);
}
function _rcContain(ctx, img, x, y, w, h) {
    if (!img || !img.width) return;
    const s = Math.min(w / img.width, h / img.height);
    const dw = img.width * s, dh = img.height * s;
    ctx.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
}
const _rcOp = (v) => (v != null && +v !== 100) ? ` ${v}%` : '';
const _rcSc = (v) => (v != null && Number(v) !== 1) ? ` ${(+v).toFixed(2)}x` : '';
const _rcBl = (b) => (b && b !== 'normal') ? ` ${b}` : '';

/**
 * [SPB-RECIPE-CARD-002] Extract the FULL recipe from the live zone objects:
 * base/finish, pattern (+stack), spec-pattern overlays (all layers), the 2nd–5th
 * base OVERLAY LAYERS (base/pattern/opacity/strength/blend/scale/color), base color
 * HSB, intensity, multi-colors, blend / cc-quality / wear / paint-reactive / zone
 * spec map. Only active / non-default items are kept so the card stays readable.
 */
// [SPB-RECIPE-CARD-005] resolve catalog ids to the names the owner actually sees in the picker.
function _spbPrettyId(id) {
    return String(id || '').replace(/^mono:/, '').replace(/[_\-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
function _spbResolveFinishName(id) {
    if (!id) return '';
    const raw = String(id).replace(/^mono:/, '');
    try { if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) { const m = MONOLITHICS.find(m => m && m.id === raw); if (m && m.name) return m.name; } } catch (_) {}
    try { if (typeof BASES !== 'undefined' && Array.isArray(BASES)) { const b = BASES.find(b => b && b.id === raw); if (b && b.name) return b.name; } } catch (_) {}
    try { if (typeof getOverlayBaseDisplay === 'function') { const d = getOverlayBaseDisplay(raw); if (d && d.name) return d.name; } } catch (_) {}
    try { if (typeof PATTERNS !== 'undefined' && Array.isArray(PATTERNS)) { const p = PATTERNS.find(p => p && p.id === raw); if (p && p.name) return p.name; } } catch (_) {}
    return _spbPrettyId(raw);
}
function _spbIsMonolithicId(id) {
    const raw = String(id || '').replace(/^mono:/, '');
    try { return typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS) && MONOLITHICS.some(m => m && m.id === raw); } catch (_) { return false; }
}
function _spbLayerNames(ids) {
    const arr = Array.isArray(ids) ? ids : (ids != null ? [ids] : []);
    return arr.map(id => {
        try { const l = (window._psdLayers || []).find(l => l && l.id === id); if (l && l.name) return l.name; } catch (_) {}
        return 'Layer ' + id;
    });
}
function _spbCatalogCount() {
    let n = 0;
    try { if (typeof BASES !== 'undefined' && Array.isArray(BASES)) n += BASES.length; } catch (_) {}
    try { if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) n += MONOLITHICS.length; } catch (_) {}
    return n;
}

function buildRecipeModel(zonesArr, result) {
    const tiers = [
        { k: 'second', label: '2nd' }, { k: 'third', label: '3rd' },
        { k: 'fourth', label: '4th' }, { k: 'fifth', label: '5th' },
    ];
    const specGroups = [
        ['specPatternStack', 'spec'], ['overlaySpecPatternStack', '2nd-spec'],
        ['thirdOverlaySpecPatternStack', '3rd-spec'], ['fourthOverlaySpecPatternStack', '4th-spec'],
        ['fifthOverlaySpecPatternStack', '5th-spec'],
    ];
    const zoneModels = (zonesArr || []).map((z, i) => {
        const swatch = z.color || (Array.isArray(z.colors) && z.colors.length ? z.colors[0] : null) || z.pickerColor || null;
        const baseOrFinish = (z.finish && z.finish !== 'none') ? { type: 'finish', val: z.finish }
            : (z.base ? { type: 'base', val: z.base } : null);
        const pattern = (z.pattern && z.pattern !== 'none')
            ? { id: z.pattern, opacity: z.patternOpacity, scale: z.scale } : null;
        const patternStack = (Array.isArray(z.patternStack) ? z.patternStack : [])
            .filter(p => p && p.pattern && p.pattern !== 'none')
            .map(p => ({ id: p.pattern, opacity: p.opacity, blend: p.blendMode, scale: p.scale }));
        const specStacks = [];
        specGroups.forEach(([key]) => {
            (Array.isArray(z[key]) ? z[key] : []).filter(sp => sp && sp.pattern && sp.pattern !== 'none')
                .forEach(sp => specStacks.push({ id: sp.pattern, opacity: sp.opacity, blend: sp.blendMode }));
        });
        const baseLayers = [];
        tiers.forEach(t => {
            const base = z[t.k + 'Base'], pat = z[t.k + 'BasePattern'], enabled = z[t.k + 'BaseEnabled'];
            const active = (base && base !== 'none') || (pat && pat !== 'none') || enabled;
            if (!active) return;
            baseLayers.push({
                tier: t.label,
                base: (base && base !== 'none') ? base : null,
                pattern: (pat && pat !== 'none') ? pat : null,
                opacity: z[t.k + 'BasePatternOpacity'],
                strength: (z[t.k + 'BaseStrength'] != null ? z[t.k + 'BaseStrength'] : z[t.k + 'BasePatternStrength']),
                blend: z[t.k + 'BaseBlendMode'],
                scale: (z[t.k + 'BaseScale'] != null ? z[t.k + 'BaseScale'] : z[t.k + 'BasePatternScale']),
                color: z[t.k + 'BaseColor'],
            });
        });
        const hsb = [];
        if (z.baseHueOffset) hsb.push('H' + (z.baseHueOffset > 0 ? '+' : '') + z.baseHueOffset);
        if (z.baseSaturationAdjust) hsb.push('S' + (z.baseSaturationAdjust > 0 ? '+' : '') + z.baseSaturationAdjust);
        if (z.baseBrightnessAdjust) hsb.push('B' + (z.baseBrightnessAdjust > 0 ? '+' : '') + z.baseBrightnessAdjust);
        const flags = [];
        if (z.wear) flags.push('Wear ' + z.wear + '%');
        if (z.muted) flags.push('Muted');
        if (z.ccQuality) flags.push('CC ' + z.ccQuality);
        if (z.usePaintReactive) flags.push('Paint-reactive');
        if (z.blendBase) flags.push('Blend ' + z.blendBase + (z.blendAmount != null ? ' ' + z.blendAmount : ''));
        if (z.zoneSpecMapName) flags.push('SpecMap ' + z.zoneSpecMapName + ' ' + (z.zoneSpecMapStrength != null ? z.zoneSpecMapStrength : 100) + '%');
        const colors = Array.isArray(z.colors) ? z.colors.filter(Boolean) : [];
        // ---- [SPB-RECIPE-CARD-005] deep facts the owner flagged as missing/inaccurate ----
        if (baseOrFinish) { baseOrFinish.name = _spbResolveFinishName(baseOrFinish.val) + (baseOrFinish.type === 'finish' && _spbIsMonolithicId(baseOrFinish.val) ? '' : ''); }
        if (pattern) pattern.name = _spbResolveFinishName(pattern.id);
        patternStack.forEach(pp => { pp.name = _spbResolveFinishName(pp.id); });
        specStacks.forEach(sp => { sp.name = _spbResolveFinishName(sp.id); });
        baseLayers.forEach(b => { if (b.base) b.baseName = _spbResolveFinishName(b.base); if (b.pattern) b.patternName = _spbResolveFinishName(b.pattern); });
        const colorInfo = [];
        const src = z.baseColorSource;
        if (z.color === 'remaining') colorInfo.push('Remaining — keeps the source paint');
        else if (typeof src === 'string' && src && src !== 'undefined') colorInfo.push('From special: ' + _spbResolveFinishName(src));
        else if ((z.colorMode === 'multi' || colors.length > 1) && colors.length) colorInfo.push(colors.length + ' colors  ' + colors.slice(0, 6).join('  '));
        else if (typeof z.color === 'string' && z.color.charAt(0) === '#') colorInfo.push('Solid ' + z.color.toUpperCase());
        else if (typeof z.color === 'string' && z.color && z.color !== 'remaining') colorInfo.push('Special: ' + _spbResolveFinishName(z.color));
        if (Array.isArray(z.gradientStops) && z.gradientStops.length) colorInfo.push('Gradient · ' + z.gradientStops.length + ' stops · ' + (z.gradientDirection || 'horizontal'));
        if (z.lockBaseColor) colorInfo.push('color locked');
        const restriction = (Array.isArray(z.sourceLayers) && z.sourceLayers.length)
            ? { layers: _spbLayerNames(z.sourceLayers), hard: z.hardEdge !== false }
            : (z.sourceLayer != null ? { layers: _spbLayerNames(z.sourceLayer), hard: z.hardEdge !== false } : null);
        const pctOf = v => Math.round(Number(v) * 100) + '%';
        const dials = [];
        if (z.baseStrength != null && Number(z.baseStrength) !== 1) dials.push('Base ' + pctOf(z.baseStrength));
        if (z.baseColorDepth != null) {
            if (Math.round(Number(z.baseColorDepth) * 100) !== 65) dials.push('Depth ' + pctOf(z.baseColorDepth));
            if (Number(z.baseColorFlip)) dials.push('Flip ' + Math.round(Number(z.baseColorFlip)) + '\u00b0');
            if (Number(z.baseColorUnderglow)) dials.push('Under ' + pctOf(z.baseColorUnderglow));
        } else if (z.baseColorStrength != null && Number(z.baseColorStrength) !== 1) dials.push('Color ' + pctOf(z.baseColorStrength));
        if (z.baseSpecStrength != null && Number(z.baseSpecStrength) !== 1) dials.push('Spec ' + pctOf(z.baseSpecStrength));
        if (z.baseScale != null && Number(z.baseScale) !== 1) dials.push('Scale ' + Number(z.baseScale).toFixed(2) + 'x');
        if (z.baseRotation) dials.push('Rot ' + z.baseRotation + '\u00b0');
        if (z.specScale != null && Number(z.specScale) !== 1 && z.specScaleMode === 'independent') dials.push('SpecScale ' + Number(z.specScale).toFixed(2) + 'x');
        if (z.specRotation) dials.push('SpecRot ' + z.specRotation + '\u00b0');
        const sgn = v => (v > 0 ? '+' : '') + v;
        const specShift = (z.specShiftR || z.specShiftG || z.specShiftB)
            ? ('Metal ' + sgn(z.specShiftR || 0) + '   Rough ' + sgn(z.specShiftG || 0) + '   Coat ' + sgn(z.specShiftB || 0)) : null;
        return {
            idx: i + 1, name: z.name || ('Zone ' + (i + 1)), swatch, baseOrFinish, pattern,
            patternStack, specStacks, baseLayers, hsb, flags, colors,
            intensity: z.intensity, colorMode: z.colorMode,
            colorInfo, restriction, dials, specShift,
        };
    });
    let paintFile = '';
    try { paintFile = (document.getElementById('paintFile') || {}).value || ''; } catch (_) {}
    paintFile = String(paintFile).split(/[\\/]/).pop() || '';
    return {
        title: 'RENDER RECIPE',
        elapsed: result && result.elapsed_seconds,
        zoneCount: (result && result.zone_count) || zoneModels.length,
        timestamp: Date.now(),
        paintFile,
        zones: zoneModels,
    };
}

/** Detail rows shown under each zone header. */
function _recipeZoneRows(z) {
    // [SPB-RECIPE-CARD-005] every row now speaks picker display names + the full zone truth
    const rows = [];
    if (z.colorInfo && z.colorInfo.length) rows.push({ label: 'Color', value: z.colorInfo.join('   \u00b7   '), color: _RC.ink });
    if (z.restriction) rows.push({
        label: 'Layer lock', color: '#ffcf6e',
        value: 'Restricted to: ' + z.restriction.layers.join('  +  ') + (z.restriction.hard ? '   (hard edge)' : '   (soft edge)'),
    });
    const patParts = [];
    if (z.pattern) patParts.push(`${z.pattern.name || z.pattern.id}${_rcOp(z.pattern.opacity)}${_rcSc(z.pattern.scale)}`);
    z.patternStack.forEach(p => patParts.push(`${p.name || p.id}${_rcOp(p.opacity)}${_rcBl(p.blend)}${_rcSc(p.scale)}`));
    if (patParts.length) rows.push({ label: 'Pattern', value: patParts.join('   \u00b7   '), color: _RC.cyan });
    if (z.specStacks.length) rows.push({ label: 'Spec overlays', value: z.specStacks.map(s => `${s.name || s.id}${_rcOp(s.opacity)}${_rcBl(s.blend)}`).join('   \u00b7   '), color: '#9be7ff' });
    if (z.baseLayers.length) {
        rows.push({
            label: 'Overlay bases', color: _RC.gold,
            value: z.baseLayers.map(b => {
                let t = b.tier + ': ' + ([b.baseName || b.base, b.patternName || b.pattern].filter(Boolean).join(' / ') || '\u2014');
                const extra = [];
                if (b.blend) extra.push(b.blend);
                if (b.strength != null) extra.push(Math.round(Number(b.strength) * 100) + '%');
                if (b.opacity != null && +b.opacity !== 100) extra.push('op ' + b.opacity + '%');
                if (b.scale != null && Number(b.scale) !== 1) extra.push((+b.scale).toFixed(2) + 'x');
                if (extra.length) t += '  (' + extra.join(' \u00b7 ') + ')';
                return t;
            }).join('      '),
        });
    }
    if (z.dials && z.dials.length) rows.push({ label: 'Dials', value: z.dials.join('   \u00b7   '), color: _RC.dim });
    if (z.specShift) rows.push({ label: 'Spec shift', value: z.specShift, color: '#9be7ff' });
    const fin = [];
    if (z.intensity != null && z.intensity !== '' && z.intensity !== '100') fin.push('Intensity ' + z.intensity + '%');
    if (z.hsb.length) fin.push('HSB ' + z.hsb.join('/'));
    z.flags.forEach(f => fin.push(f));
    if (fin.length) rows.push({ label: 'Extras', value: fin.join('   \u00b7   '), color: _RC.dim });
    return rows;
}

/** Draw (or measure, when draw=false) one zone panel; returns its height. */
function _recipeZonePanel(ctx, z, x, y, w, draw) {
    const P = 14, lineH = 18, headH = 30, labelColW = 104;
    const rows = _recipeZoneRows(z);
    const valX = x + P + labelColW, valMaxW = w - P * 2 - labelColW;
    ctx.font = _RC.mono;
    const rowHeights = rows.map(r => Math.max(lineH, _rcWrapCount(ctx, r.value, valMaxW) * lineH));
    const rowsH = rowHeights.reduce((a, b) => a + b + 5, 0);
    const panelH = headH + 10 + (rows.length ? rowsH : 6) + 8;
    if (draw) {
        _rcRoundRect(ctx, x, y, w, panelH, 12); ctx.fillStyle = _RC.panel; ctx.fill();
        ctx.strokeStyle = _RC.panelEdge; ctx.lineWidth = 1; ctx.stroke();
        // accent bar down the left edge in the zone's swatch color
        _rcRoundRect(ctx, x, y, 6, panelH, 3);
        ctx.fillStyle = z.swatch || '#445'; ctx.fill();
        const hy = y + 8;
        ctx.fillStyle = z.swatch || '#334'; _rcRoundRect(ctx, x + P, hy, 22, 22, 5); ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.28)'; ctx.lineWidth = 1; _rcRoundRect(ctx, x + P, hy, 22, 22, 5); ctx.stroke();
        ctx.fillStyle = _RC.ink; ctx.font = "800 16px 'Segoe UI',Arial,sans-serif"; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
        ctx.fillText(`Z${z.idx}  ${z.name}`, x + P + 32, hy + 12);
        ctx.textBaseline = 'alphabetic';
        if (z.baseOrFinish) {
            const isFin = z.baseOrFinish.type === 'finish';
            const chipTxt = z.baseOrFinish.name || z.baseOrFinish.val;   // picker display name, not the raw id
            ctx.font = "700 12px 'Segoe UI',Arial,sans-serif";
            const cw = Math.ceil(ctx.measureText(chipTxt).width) + 18;
            _rcChip(ctx, chipTxt, x + w - P - cw, hy + 1, { color: isFin ? '#171106' : _RC.ink, bg: isFin ? _RC.gold : 'rgba(255,200,80,0.16)', h: 20 });
        }
        let ry = y + headH + 12;
        rows.forEach((r, i) => {
            ctx.font = "700 10px 'Segoe UI',Arial,sans-serif"; ctx.fillStyle = _RC.faint; ctx.textAlign = 'left';
            ctx.fillText(r.label.toUpperCase(), x + P, ry + 11);
            ctx.font = _RC.mono; ctx.fillStyle = r.color || _RC.ink;
            _rcWrap(ctx, r.value, valX, ry + 11, valMaxW, lineH);
            ry += rowHeights[i] + 5;
        });
    }
    return panelH;
}

function _drawRecipeBg(ctx, W, H) {
    // [SPB-RECIPE-CARD-005] black-gold stage with the brand's EKG heartbeat echoed faintly
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, _RC.bg0); g.addColorStop(0.5, _RC.bg1); g.addColorStop(1, _RC.bg0);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    let gl = ctx.createRadialGradient(W * 0.10, 0, 0, W * 0.10, 0, W * 0.55);
    gl.addColorStop(0, 'rgba(255,190,60,0.10)'); gl.addColorStop(1, 'rgba(255,190,60,0)');
    ctx.fillStyle = gl; ctx.fillRect(0, 0, W, H);
    gl = ctx.createRadialGradient(W * 0.92, H, 0, W * 0.92, H, W * 0.60);
    gl.addColorStop(0, 'rgba(255,160,30,0.08)'); gl.addColorStop(1, 'rgba(255,160,30,0)');
    ctx.fillStyle = gl; ctx.fillRect(0, 0, W, H);
    // fine diagonal pinstripes
    ctx.save(); ctx.globalAlpha = 0.045; ctx.strokeStyle = '#ffd142'; ctx.lineWidth = 1;
    for (let x = -H; x < W; x += 28) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + H, H); ctx.stroke(); }
    ctx.restore();
    // EKG heartbeat lines (the logo motif) drifting behind the panels
    const ekg = (yB, amp, alpha) => {
        ctx.save(); ctx.globalAlpha = alpha; ctx.strokeStyle = '#ffd142'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(0, yB);
        for (let x = 0; x < W; x += 340) {
            ctx.lineTo(x + 150, yB);
            ctx.lineTo(x + 168, yB + amp * 0.28);
            ctx.lineTo(x + 190, yB - amp);
            ctx.lineTo(x + 212, yB + amp * 0.72);
            ctx.lineTo(x + 230, yB - amp * 0.18);
            ctx.lineTo(x + 250, yB);
        }
        ctx.lineTo(W, yB); ctx.stroke(); ctx.restore();
    };
    for (let yy = 300; yy < H - 140; yy += 760) ekg(yy, 46, 0.055);
    // gold double border
    const bd = ctx.createLinearGradient(0, 0, W, H);
    bd.addColorStop(0, 'rgba(255,209,66,0.60)'); bd.addColorStop(0.5, 'rgba(184,135,31,0.35)'); bd.addColorStop(1, 'rgba(255,209,66,0.60)');
    ctx.strokeStyle = bd; ctx.lineWidth = 3;
    _rcRoundRect(ctx, 5, 5, W - 10, H - 10, 20); ctx.stroke();
    ctx.strokeStyle = 'rgba(255,209,66,0.14)'; ctx.lineWidth = 1;
    _rcRoundRect(ctx, 11, 11, W - 22, H - 22, 16); ctx.stroke();
}

/** Lay out the whole card; draw=false returns total height for the 2-pass sizing. */
function _layoutRecipeCard(ctx, model, imgs, draw) {
    const W = _RC.W, P = _RC.PAD;
    let y = P;
    // ---------- TOP QR BANNER (SPB-RECIPE-CARD-003) — branding + scannable QR ----------
    if (imgs.qr) {
        const bw = Math.min(W - 2 * P, 700);
        const bh = Math.round(bw * imgs.qr.height / imgs.qr.width);
        if (draw) {
            const bx = (W - bw) / 2;
            _rcRoundRect(ctx, bx, y, bw, bh, 12); ctx.save(); ctx.clip();
            ctx.drawImage(imgs.qr, bx, y, bw, bh); ctx.restore();
            ctx.strokeStyle = _RC.panelEdge; ctx.lineWidth = 1; _rcRoundRect(ctx, bx, y, bw, bh, 12); ctx.stroke();
        }
        y += bh + 18;
    }
    // ---------- HEADER ----------
    const headH = 132;
    if (draw) {
        _rcRoundRect(ctx, P, y, W - 2 * P, headH, 16);
        const g = ctx.createLinearGradient(P, y, W - P, y);
        g.addColorStop(0, 'rgba(255,190,60,0.16)'); g.addColorStop(1, 'rgba(255,120,0,0.04)');
        ctx.fillStyle = g; ctx.fill();
        ctx.strokeStyle = _RC.panelEdge; ctx.lineWidth = 1; ctx.stroke();
        const tx = P + 24;
        ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
        const tg = ctx.createLinearGradient(0, y + 28, 0, y + 62);
        tg.addColorStop(0, '#ffe9a8'); tg.addColorStop(1, '#ffb000');
        ctx.fillStyle = tg; ctx.font = "800 34px 'Segoe UI',Arial,sans-serif";
        ctx.fillText(model.title || 'RENDER RECIPE', tx, y + 60);
        ctx.fillStyle = _RC.dim; ctx.font = "600 13px 'Segoe UI',Arial,sans-serif";
        ctx.fillText('SHOKKER PAINT BOOTH   ·   ' + new Date(model.timestamp).toLocaleDateString(), tx, y + 86);
        const sx = W - P - 24;
        ctx.textAlign = 'right';
        ctx.fillStyle = _RC.gold; ctx.font = "800 30px 'Segoe UI',Arial,sans-serif";
        ctx.fillText((model.elapsed != null ? model.elapsed : '?') + 's', sx, y + 50);
        ctx.fillStyle = _RC.dim; ctx.font = "600 13px 'Segoe UI',Arial,sans-serif";
        ctx.fillText(`${model.zoneCount} zones   ·   2048²`, sx, y + 74);
        if (model.paintFile) { ctx.fillStyle = _RC.faint; ctx.font = _RC.mono; ctx.fillText(model.paintFile, sx, y + 98); }
        ctx.textAlign = 'left';
    }
    y += headH + 26;
    // ---------- HERO SNAPSHOTS ----------
    const heroLabelH = 22;
    const heroBoxW = (W - 2 * P - _RC.GAP) / 2;
    const heroBoxH = Math.min(heroBoxW, 470);
    if (draw) {
        [['PAINT — car file', imgs.paint, P], ['COMBINED SPEC — surface map', imgs.spec, P + heroBoxW + _RC.GAP]].forEach(([lbl, img, bx]) => {
            ctx.font = "700 13px 'Segoe UI',Arial,sans-serif"; ctx.fillStyle = _RC.dim; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
            ctx.fillText(lbl, bx + 2, y + 14);
            const iy = y + heroLabelH;
            _rcRoundRect(ctx, bx, iy, heroBoxW, heroBoxH, 12); ctx.fillStyle = '#05070e'; ctx.fill();
            ctx.save(); _rcRoundRect(ctx, bx, iy, heroBoxW, heroBoxH, 12); ctx.clip();
            if (img) _rcContain(ctx, img, bx, iy, heroBoxW, heroBoxH);
            else { ctx.fillStyle = _RC.faint; ctx.font = "14px 'Segoe UI',Arial"; ctx.textAlign = 'center'; ctx.fillText('no image', bx + heroBoxW / 2, iy + heroBoxH / 2); ctx.textAlign = 'left'; }
            ctx.restore();
            ctx.strokeStyle = _RC.panelEdge; ctx.lineWidth = 1.5; _rcRoundRect(ctx, bx, iy, heroBoxW, heroBoxH, 12); ctx.stroke();
        });
    }
    y += heroLabelH + heroBoxH + 30;
    // ---------- PER-ZONE RECIPE ----------
    if (draw) {
        ctx.fillStyle = _RC.gold; ctx.font = "800 18px 'Segoe UI',Arial,sans-serif"; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
        ctx.fillText('PER-ZONE RECIPE', P, y + 14);
        ctx.strokeStyle = 'rgba(255,200,80,0.22)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(P + 175, y + 10); ctx.lineTo(W - P, y + 10); ctx.stroke();
    }
    y += 30;
    if (!model.zones.length) {
        if (draw) { ctx.fillStyle = _RC.dim; ctx.font = "14px 'Segoe UI',Arial"; ctx.fillText('No zones configured for this render.', P, y + 18); }
        y += 40;
    } else {
        model.zones.forEach(z => { y += _recipeZonePanel(ctx, z, P, y, W - 2 * P, draw) + 12; });
    }
    // ---------- BOTTOM QR BANNER (SPB-RECIPE-CARD-003) — bigger, primary scannable copy ----------
    if (imgs.qr) {
        const bw = Math.min(W - 2 * P, 900);
        const bh = Math.round(bw * imgs.qr.height / imgs.qr.width);
        if (draw) {
            const bx = (W - bw) / 2;
            ctx.fillStyle = _RC.gold; ctx.font = "800 14px 'Segoe UI',Arial,sans-serif"; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
            ctx.fillText('SCAN  \u2014  JOIN THE DISCORD   \u00b7   GET THE APP', W / 2, y + 12);
            const iy = y + 22;
            _rcRoundRect(ctx, bx, iy, bw, bh, 12); ctx.save(); ctx.clip();
            ctx.drawImage(imgs.qr, bx, iy, bw, bh); ctx.restore();
            ctx.strokeStyle = _RC.panelEdge; ctx.lineWidth = 1.5; _rcRoundRect(ctx, bx, iy, bw, bh, 12); ctx.stroke();
            ctx.textAlign = 'left';
        }
        y += 22 + bh + 22;
    }
    // ---------- FOOTER ----------
    const footH = 44;
    if (draw) {
        ctx.strokeStyle = 'rgba(255,200,80,0.20)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(P, y + 6); ctx.lineTo(W - P, y + 6); ctx.stroke();
        ctx.fillStyle = _RC.dim; ctx.font = "600 12px 'Segoe UI',Arial,sans-serif"; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('Made with SHOKKER PAINT BOOTH   \u00b7   payhip.com/b/AhgpV   \u00b7   discord.gg/GwXxyhwtDu', W / 2, y + 26);
        ctx.textAlign = 'right'; ctx.fillStyle = _RC.faint;
        ctx.fillText(new Date(model.timestamp).toLocaleString(), W - P, y + 26);
        ctx.textAlign = 'left';
    }
    y += footH + P;
    return y;
}

/** Build the high-res card canvas (2-pass: measure height, then draw). */
function renderRecipeCardToCanvas(model, imgs) {
    const canvas = document.createElement('canvas');
    canvas.width = _RC.W;
    canvas.height = 200;
    const H = Math.ceil(_layoutRecipeCard(canvas.getContext('2d'), model, imgs, false));
    canvas.height = H;
    const ctx = canvas.getContext('2d');
    _drawRecipeBg(ctx, _RC.W, H);
    if (imgs.logo) {
        ctx.save(); ctx.globalAlpha = 0.04;
        const ww = _RC.W * 0.62, hh = imgs.logo.height * (ww / imgs.logo.width);
        ctx.drawImage(imgs.logo, (_RC.W - ww) / 2, (H - hh) / 2, ww, hh);
        ctx.restore();
    }
    _layoutRecipeCard(ctx, model, imgs, true);
    return canvas;
}

function _rcLoadImg(src, allowCorsRetry) {
    return new Promise(res => {
        if (!src) { res(null); return; }
        const isHttp = !/^data:/i.test(src);
        const img = new Image();
        let done = false; const fin = (v) => { if (!done) { done = true; res(v); } };
        // Request CORS-clean (server has CORS enabled) so the exported canvas isn't tainted
        // and Save-PNG / Copy work. If that errors (cache/CORS hiccup), retry once WITHOUT
        // crossOrigin so the snapshot still shows (export may taint then — handled with a toast).
        if (isHttp) { try { img.crossOrigin = 'anonymous'; } catch (_) {} }
        img.onload = () => fin(img);
        img.onerror = () => { if (isHttp && allowCorsRetry !== false) { _rcLoadImg(src, false).then(fin); } else fin(null); };
        setTimeout(() => fin(null), 6000);
        try { img.src = src; } catch (_) { fin(null); }
    });
}

/** Build the recipe model, load the snapshots + logo, draw the card into the modal stage. */
async function renderRecipeCardUI(result) {
    const stage = document.getElementById('recipeCardStage');
    if (!stage) { try { buildRenderRecipeZones(); } catch (_) {} return; }
    stage.innerHTML = '<div class="recipe-card-loading">Building recipe card…</div>';
    const model = buildRecipeModel((typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : [], result);
    const paintSrc = (document.getElementById('renderPaintPreview') || {}).src || '';
    const specSrc = (document.getElementById('renderSpecPreview') || {}).src || '';
    const [paintImg, specImg, logoImg, qrImg] = await Promise.all([
        _rcLoadImg(paintSrc), _rcLoadImg(specSrc),
        _rcLoadImg((typeof window !== 'undefined' && window.SPB_LOGO_DATAURL) || ''),
        _rcLoadImg((typeof window !== 'undefined' && window.SPB_QR_LOGO_DATAURL) || ''),
    ]);
    let canvas;
    try { canvas = renderRecipeCardToCanvas(model, { paint: paintImg, spec: specImg, logo: logoImg, qr: qrImg }); }
    catch (e) {
        // Fallback: never leave the stage stuck on "Building…". Show the simple HTML table instead.
        console.warn('[recipe-card] draw failed:', e);
        stage.innerHTML = '';
        const tbl = document.getElementById('renderRecipeZones');
        if (tbl) { tbl.style.display = 'block'; stage.appendChild(tbl); }
        try { buildRenderRecipeZones(); } catch (_) {}
        return;
    }
    window._recipeCardCanvas = canvas;
    window._recipeCardModel = model;
    canvas.className = 'recipe-card-canvas';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', 'Render recipe card — ' + model.zoneCount + ' zones');
    stage.innerHTML = '';
    stage.appendChild(canvas);
}

/** [SPB-RECIPE-CARD-002] Download the recipe card as a PNG (Discord-shareable). */
function exportRecipeCardPNG() {
    const canvas = window._recipeCardCanvas;
    if (!canvas) { showToast('No recipe card to save yet', true); return; }
    const model = window._recipeCardModel || {};
    const stamp = new Date(model.timestamp || Date.now()).toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const name = `shokker-recipe-${stamp}.png`;
    try {
        canvas.toBlob(blob => {
            if (!blob) { showToast('Could not export card image', true); return; }
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = name;
            document.body.appendChild(a); a.click();
            setTimeout(() => { try { URL.revokeObjectURL(url); a.remove(); } catch (_) {} }, 1500);
            showToast('Recipe card saved: ' + name);
        }, 'image/png');
    } catch (e) { showToast('Export failed (canvas may be tainted): ' + (e && e.message || e), true); }
}

/** [SPB-RECIPE-CARD-002] Copy the recipe card image to the clipboard (paste into Discord). */
async function copyRecipeCardToClipboard() {
    const canvas = window._recipeCardCanvas;
    if (!canvas) { showToast('No recipe card to copy yet', true); return; }
    try {
        if (!navigator.clipboard || typeof window.ClipboardItem === 'undefined') {
            showToast('Image clipboard not supported here — use Save PNG instead', true); return;
        }
        const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
        if (!blob) { showToast('Could not render card image', true); return; }
        await navigator.clipboard.write([new window.ClipboardItem({ 'image/png': blob })]);
        showToast('Recipe card copied — paste it into Discord!');
    } catch (e) { showToast('Copy failed: ' + (e && e.message || e) + ' — try Save PNG', true); }
}

if (typeof window !== 'undefined') {
    window.buildRecipeModel = buildRecipeModel;
    window.buildTPDescription = buildTPDescription;   // [SPB-RECIPE-CARD-005]
    window.renderRecipeCardUI = renderRecipeCardUI;
    window.renderRecipeCardToCanvas = renderRecipeCardToCanvas;
    window.exportRecipeCardPNG = exportRecipeCardPNG;
    window.copyRecipeCardToClipboard = copyRecipeCardToClipboard;
}

// ============================================================================
// [SPB-RECIPE-SHARE-001 — 2026-06-01 owner] Save-as-PDF + portable recipe file
// (Save Recipe Style / Share Recipe / Import). The full per-zone snapshot is
// already captured each render (renderHistory[].zoneSnapshot) and restored by
// _recipeSnapshotToZones() — so save/share = write that snapshot to a tiny
// `.shokkerrecipe` JSON; import = read it back + restore. No server, no library.
// ============================================================================

/** One-page PDF embedding the card canvas as a JPEG (DCTDecode) — no dependency. */
function _canvasToPdfBlob(canvas, opts) {
    opts = opts || {};
    const q = opts.quality || 0.9;
    const jpeg = atob(canvas.toDataURL('image/jpeg', q).split(',')[1]); // binary string, chars 0-255
    const iw = canvas.width, ih = canvas.height;
    const pw = Math.min(iw, opts.maxW || 1200);
    const ph = Math.round(pw * ih / iw);
    let pdf = '';
    const off = [];
    const obj = (n, body) => { off[n] = pdf.length; pdf += n + ' 0 obj\n' + body + '\nendobj\n'; };
    pdf += '%PDF-1.3\n';
    obj(1, '<< /Type /Catalog /Pages 2 0 R >>');
    obj(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
    obj(3, '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' + pw + ' ' + ph + '] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>');
    off[4] = pdf.length;
    pdf += '4 0 obj\n<< /Type /XObject /Subtype /Image /Width ' + iw + ' /Height ' + ih +
        ' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ' + jpeg.length + ' >>\nstream\n';
    pdf += jpeg;
    pdf += '\nendstream\nendobj\n';
    const content = 'q\n' + pw + ' 0 0 ' + ph + ' 0 0 cm\n/Im0 Do\nQ\n';
    obj(5, '<< /Length ' + content.length + ' >>\nstream\n' + content + 'endstream');
    const xrefPos = pdf.length;
    let xref = 'xref\n0 6\n0000000000 65535 f \n';
    for (let i = 1; i <= 5; i++) xref += String(off[i]).padStart(10, '0') + ' 00000 n \n';
    pdf += xref + 'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + xrefPos + '\n%%EOF';
    return new Blob([Uint8Array.from(pdf, c => c.charCodeAt(0) & 0xff)], { type: 'application/pdf' });
}

function exportRecipeCardPDF() {
    const canvas = window._recipeCardCanvas;
    if (!canvas) { showToast('No recipe card to save yet', true); return; }
    const model = window._recipeCardModel || {};
    const stamp = new Date(model.timestamp || Date.now()).toISOString().replace(/[:.]/g, '-').slice(0, 19);
    try {
        const blob = _canvasToPdfBlob(canvas, { quality: 0.9, maxW: 1200 });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `shokker-recipe-${stamp}.pdf`;
        document.body.appendChild(a); a.click();
        setTimeout(() => { try { URL.revokeObjectURL(url); a.remove(); } catch (_) {} }, 1500);
        showToast('Recipe card saved as PDF');
    } catch (e) { showToast('PDF export failed (canvas may be tainted): ' + (e && e.message || e), true); }
}

function _hasRecipeToExport() {
    return !!(window._recipeCardModel || (typeof renderHistory !== 'undefined' && renderHistory[0]));
}

/** The portable recipe object that SAVE/SHARE write and IMPORT reads. */
function _buildRecipeFileObject(includeThumb) {
    const model = window._recipeCardModel || {};
    const snap = (typeof renderHistory !== 'undefined' && renderHistory[0] && renderHistory[0].zoneSnapshot)
        ? renderHistory[0].zoneSnapshot
        : (typeof zones !== 'undefined' && Array.isArray(zones) ? zones : []);
    const out = {
        format: 'shokker-recipe',
        version: 1,
        app: 'Shokker Paint Booth',
        savedAt: new Date().toISOString(),
        meta: {
            zoneCount: model.zoneCount || (snap ? snap.length : 0),
            elapsed_seconds: model.elapsed,
            paintFile: model.paintFile || '',
        },
        zoneSnapshot: snap,
    };
    if (includeThumb) {
        try {
            const src = document.getElementById('renderPaintPreview');
            if (src && src.naturalWidth) {
                const c = document.createElement('canvas');
                const tw = 360, th = Math.max(1, Math.round(tw * (src.naturalHeight / src.naturalWidth)));
                c.width = tw; c.height = th;
                c.getContext('2d').drawImage(src, 0, 0, tw, th);
                out.thumbnail = c.toDataURL('image/jpeg', 0.7);
            }
        } catch (_) {}
    }
    return out;
}

function _downloadRecipeFile(obj, label) {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const base = ((obj.meta && obj.meta.paintFile) ? obj.meta.paintFile.replace(/\.[^.]+$/, '') : 'recipe')
        .replace(/[^a-z0-9_-]+/gi, '_').slice(0, 40) || 'recipe';
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${base}-${stamp}.shokkerrecipe`;
    document.body.appendChild(a); a.click();
    setTimeout(() => { try { URL.revokeObjectURL(url); a.remove(); } catch (_) {} }, 1500);
    showToast(label);
}

/** SAVE RECIPE STYLE — download a compact recipe file you can re-import any time. */
function saveRecipeStyleFile() {
    if (!_hasRecipeToExport()) { showToast('Render first, then save the recipe style', true); return; }
    _downloadRecipeFile(_buildRecipeFileObject(false), 'Recipe style saved (.shokkerrecipe) — re-import it any time with Import Recipe');
}

/** SHARE RECIPE — download a portable recipe file (with preview) to send to others. */
function shareRecipeFile() {
    if (!_hasRecipeToExport()) { showToast('Render first, then share the recipe', true); return; }
    _downloadRecipeFile(_buildRecipeFileObject(true), 'Shareable recipe saved — send the .shokkerrecipe file to anyone; they open it via Import Recipe');
}

/** IMPORT — open the OS file picker for a .shokkerrecipe (or .json) and restore the full recipe. */
function importRecipeFile() {
    let inp = document.getElementById('recipeImportInput');
    if (!inp) {
        inp = document.createElement('input');
        inp.type = 'file'; inp.id = 'recipeImportInput';
        inp.accept = '.shokkerrecipe,.json,application/json';
        inp.style.display = 'none';
        inp.addEventListener('change', (e) => {
            const f = e.target.files && e.target.files[0];
            if (f) _applyImportedRecipeFile(f);
            e.target.value = '';
        });
        document.body.appendChild(inp);
    }
    inp.click();
}

function _applyImportedRecipeFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
        let data;
        try { data = JSON.parse(reader.result); } catch (_) { showToast('That file is not a valid Shokker recipe', true); return; }
        const snap = data && (data.zoneSnapshot || data.zones);
        if (!Array.isArray(snap) || !snap.length) { showToast('No recipe data found in that file', true); return; }
        if (!confirm(`Import this recipe (${snap.length} zones)? Your current zones will be replaced.`)) return;
        try {
            zones = _recipeSnapshotToZones(snap);
            selectedZoneIndex = 0;
            renderZones();
            triggerPreviewRender();
            autoSave();
            if (typeof closeRecentRendersPanel === 'function') closeRecentRendersPanel();
            if (typeof closeRenderResults === 'function') closeRenderResults();
            showToast('Recipe imported — ' + snap.length + ' zones restored');
        } catch (e) { showToast('Import failed: ' + (e && e.message || e), true); }
    };
    reader.onerror = () => showToast('Could not read that file', true);
    reader.readAsText(file);
}

if (typeof window !== 'undefined') {
    window.exportRecipeCardPDF = exportRecipeCardPDF;
    window.saveRecipeStyleFile = saveRecipeStyleFile;
    window.shareRecipeFile = shareRecipeFile;
    window.importRecipeFile = importRecipeFile;
}

// ===== SAVE TO SHOKKER PAINT BOOTH FOLDER (keep; not overwritten) =====
/**
 * Save the last render to a permanent "keep" folder that won't be overwritten. // [48]
 */
async function saveRenderToKeep() {
    const outputDir = document.getElementById('outputDir')?.value?.trim(); // [55] optional chaining
    if (!outputDir) {
        showToast('Set the iRacing Folder (output path) first, then render. After render, click Save to keep.', true);
        return;
    }
    const btn = document.getElementById('btnSaveToKeep');
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; } // [30] loading indicator
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/save-render-to-keep', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                output_dir: outputDir,
                iracing_id: document.getElementById('iracingId')?.value?.trim() || '00000'
            }),
            signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [10] timeout
        });
        const data = await safeParseJSON(res, 'save render'); // [15] safe parse
        if (data.success) {
            showToast(`Saved ${data.saved_files?.length || 0} file(s) to Shokker Paint Booth folder. They will not be overwritten.`);
        } else {
            showToast('Save failed: ' + (data.error || 'unknown server error'), true); // [40] specific
        }
    } catch (e) {
        showToast(classifyFetchError(e, 'Save render'), true); // [12] user-friendly error
    }
    if (btn) { btn.disabled = false; btn.textContent = 'Save to Keep'; } // [30] restore button
}

// ===== ONE-CLICK DEPLOY TO iRACING =====
let lastRenderedJobId = null;

/**
 * Load iRacing car folders into the deploy dropdown. // [49]
 * Uses response caching to avoid redundant server calls. // [24]
 */
async function loadIracingCars() {
    try {
        // [24] Cache car list - it doesn't change during a session
        const data = await cachedFetch('iracing_cars', async () => {
            const res = await fetch(ShokkerAPI.baseUrl + '/iracing-cars', {
                signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [10] timeout
            });
            return await safeParseJSON(res, 'iRacing cars'); // [15] safe parse
        });
        const sel = document.getElementById('deployCarSelect'); // [55] null check
        if (!sel || !data.cars) return;
        let html = '<option value="">Select car folder...</option>';
        data.cars.forEach(c => {
            const name = _spbEscapeRenderHtml(c.name || '');
            const path = _spbEscapeRenderHtml(c.path || '');
            const count = _spbEscapeRenderHtml(c.tga_count ?? 0);
            html += `<option value="${name}" title="${path}">${name} (${count} files)</option>`;
        });
        sel.innerHTML = html;
        // Try to auto-select based on current paint file path
        const paintPath = document.getElementById('paintFile')?.value || '';
        if (paintPath) {
            const parts = paintPath.replace(/\\/g, '/').split('/');
            for (const car of data.cars) {
                if (parts.includes(car.name)) {
                    sel.value = car.name;
                    break;
                }
            }
        }
    } catch (e) {
        console.warn('[loadIracingCars]', classifyFetchError(e, 'car list load')); // [13] friendly log
    }
}

/**
 * Deploy the last render result to an iRacing car folder. // [50]
 */
async function deployToIracing() {
    const sel = document.getElementById('deployCarSelect'); // [55] null checks
    const status = document.getElementById('deployStatus');
    const carFolder = sel?.value;
    if (!carFolder) {
        showToast('Select a car folder first', true);
        return;
    }
    if (!lastRenderedJobId) {
        showToast('No render available to deploy. Render first!', true); // [40] specific
        return;
    }
    const iracingId = document.getElementById('iracingId')?.value?.trim() || '00000';
    if (status) { status.textContent = 'Deploying...'; status.style.color = 'var(--accent-blue)'; } // [55] null check
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/deploy-to-iracing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: lastRenderedJobId, car_folder: carFolder, iracing_id: iracingId }),
            signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS), // [10] timeout
        });
        const data = await safeParseJSON(res, 'deploy'); // [15] safe parse
        if (data.success) {
            const deployedCount = Array.isArray(data.deployed) ? data.deployed.length : 0;
            if (status) {
                status.textContent = `Deployed ${deployedCount} files to ${carFolder}. Alt+Tab to iRacing, press Ctrl+R!`;
                status.style.color = 'var(--success)';
            }
            showToast(`Deployed to iRacing! ${deployedCount} files → ${carFolder}`);
        } else {
            if (status) { status.textContent = data.error || 'Deploy failed'; status.style.color = 'var(--error)'; }
            showToast('Deploy failed: ' + (data.error || 'Unknown server error'), true); // [40] specific
        }
    } catch (e) {
        const msg = classifyFetchError(e, 'Deploy'); // [12] friendly error
        if (status) { status.textContent = msg; status.style.color = 'var(--error)'; }
        showToast(msg, true);
    }
}

/** Build the Trading Paints description — the full, ACCURATE recipe. // [48] [SPB-RECIPE-CARD-005]
    Owner 2026-08-26: the old one listed raw finish lines, padded "No finish" zones, and printed a
    FALSE domain (shokkerpaints.com). This one reuses buildRecipeModel's deep facts (display names,
    colors, layer locks, overlay bases, dials) and signs off with the real Payhip + Discord links. */
function buildTPDescription() {
    const model = buildRecipeModel((typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : [], null);
    const lines = ['\u2550\u2550\u2550 MADE WITH SHOKKER PAINT BOOTH \u2550\u2550\u2550', ''];
    const wearSlider = document.getElementById('wearSlider');
    const globalWear = wearSlider ? parseInt(wearSlider.value) : 0;
    let skipped = 0;
    for (const z of model.zones) {
        const finishName = z.baseOrFinish
            ? (z.baseOrFinish.name || z.baseOrFinish.val) + (z.baseOrFinish.type === 'finish' ? ' (Monolithic)' : '')
            : null;
        const hasContent = finishName || (z.colorInfo && z.colorInfo.length) || z.pattern ||
            (z.patternStack && z.patternStack.length) || (z.baseLayers && z.baseLayers.length);
        if (!hasContent) { skipped++; continue; }
        let line = '\u25b8 ' + z.name + ' \u2014 ' + (finishName || 'source paint');
        if (z.pattern) line += ' + ' + (z.pattern.name || z.pattern.id);
        if (z.intensity && z.intensity !== '' && z.intensity !== '100') line += ' [' + z.intensity + '%]';
        lines.push(line);
        const sub1 = [];
        if (z.colorInfo && z.colorInfo.length) sub1.push(z.colorInfo.join(' \u00b7 '));
        if (z.restriction) sub1.push('Locked to ' + z.restriction.layers.join(' + ') + (z.restriction.hard ? ' (hard edge)' : ''));
        if (sub1.length) lines.push('    ' + sub1.join('  \u00b7  '));
        if (z.baseLayers && z.baseLayers.length) {
            lines.push('    ' + z.baseLayers.map(b => {
                let t = b.tier + ' base: ' + ([b.baseName || b.base, b.patternName || b.pattern].filter(Boolean).join(' / ') || '\u2014');
                const ex = [];
                if (b.blend) ex.push(b.blend);
                if (b.strength != null) ex.push(Math.round(Number(b.strength) * 100) + '%');
                if (ex.length) t += ' (' + ex.join(' ') + ')';
                return t;
            }).join('  \u00b7  '));
        }
        const sub3 = [];
        if (z.patternStack && z.patternStack.length) sub3.push('Patterns: ' + z.patternStack.map(pp => pp.name || pp.id).join(', '));
        if (z.specStacks && z.specStacks.length) sub3.push('Spec: ' + z.specStacks.map(sp => sp.name || sp.id).join(', '));
        if (z.dials && z.dials.length) sub3.push(z.dials.join(' \u00b7 '));
        if (z.specShift) sub3.push('Spec shift ' + z.specShift.replace(/\s+/g, ' '));
        if (z.hsb && z.hsb.length) sub3.push('HSB ' + z.hsb.join('/'));
        if (z.flags && z.flags.length) sub3.push(z.flags.join(' \u00b7 '));
        if (sub3.length) lines.push('    ' + sub3.join('  \u00b7  '));
    }
    if (globalWear > 0) { lines.push(''); lines.push('Global Wear: ' + globalWear + '%'); }
    lines.push('');
    lines.push('\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500');
    const cnt = _spbCatalogCount();
    lines.push((cnt ? cnt.toLocaleString() + ' finishes \u00b7 ' : '') + 'SHOKKER PAINT BOOTH');
    lines.push('Get the app \u2192 payhip.com/b/AhgpV');
    lines.push('Discord \u2192 discord.gg/GwXxyhwtDu');
    return lines.join('\n');
}

/** Copy the Trading Paints description to the clipboard. */
function copyTPDescription() {
    const text = buildTPDescription();

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Trading Paints description copied!');
        }).catch(() => {
            fallbackCopyTP(text);
        });
    } else {
        fallbackCopyTP(text);
    }
}

function fallbackCopyTP(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand('copy');
        showToast('Trading Paints description copied!');
    } catch (e) {
        showToast('Could not copy - check browser permissions', true);
    }
    document.body.removeChild(ta);
}

// ===== RENDER HISTORY =====
const RENDER_HISTORY_STORAGE_KEY = 'spb_render_history_v1';
const RENDER_HISTORY_STORAGE_LIMIT = 1500000;

function _persistableRenderHistoryEntry(entry) {
    entry = entry && typeof entry === 'object' ? entry : {};
    const thumb = String(entry.thumb || '');
    return {
        job_id: String(entry.job_id || '').slice(0, 160),
        timestamp: Number(entry.timestamp) || Date.now(),
        elapsed_seconds: Number(entry.elapsed_seconds) || 0,
        zone_count: Number(entry.zone_count) || 0,
        paint_url: String(entry.paint_url || '').slice(0, 2048),
        spec_url: String(entry.spec_url || '').slice(0, 2048),
        zones_summary: String(entry.zones_summary || '').slice(0, 4000),
        notes: String(entry.notes || '').slice(0, 500),
        tags: Array.isArray(entry.tags) ? entry.tags.map(t => String(t).slice(0, 80)).slice(0, 12) : [],
        favorite: !!entry.favorite,
        filename: String(entry.filename || 'render.png').slice(0, 240),
        metadata: entry.metadata && typeof entry.metadata === 'object' ? entry.metadata : {},
        zoneSnapshot: Array.isArray(entry.zoneSnapshot) ? entry.zoneSnapshot : [],
        thumb: thumb.length <= 250000 && /^data:image\/(?:jpeg|png|webp);base64,/i.test(thumb)
            ? thumb : ''
    };
}

function persistRenderHistory() {
    if (typeof localStorage === 'undefined') return false;
    try {
        const entries = renderHistory.slice(0, MAX_RENDER_HISTORY).map(_persistableRenderHistoryEntry);
        let encoded = JSON.stringify(entries);
        while (entries.length > 1 && encoded.length > RENDER_HISTORY_STORAGE_LIMIT) {
            entries.pop();
            encoded = JSON.stringify(entries);
        }
        if (encoded.length > RENDER_HISTORY_STORAGE_LIMIT && entries.length) {
            // Preserve the durable thumbnail/metadata even when one unusually
            // large zone recipe would otherwise make the entire write fail.
            entries[0].zoneSnapshot = [];
            entries[0].metadata = {};
            encoded = JSON.stringify(entries);
        }
        if (encoded.length > RENDER_HISTORY_STORAGE_LIMIT) return false;
        localStorage.setItem(RENDER_HISTORY_STORAGE_KEY, encoded);
        return true;
    } catch (_) {
        return false;
    }
}

function restorePersistedRenderHistory() {
    if (typeof localStorage === 'undefined') return false;
    try {
        const parsed = JSON.parse(localStorage.getItem(RENDER_HISTORY_STORAGE_KEY) || '[]');
        if (!Array.isArray(parsed)) return false;
        const restored = parsed.slice(0, MAX_RENDER_HISTORY).map(_persistableRenderHistoryEntry);
        renderHistory.splice(0, renderHistory.length, ...restored);
        return restored.length > 0;
    } catch (_) {
        return false;
    }
}

/** Update the thumbnail strip at the top showing recent render results. // [47] */
function updateHistoryStrip() {
    // [SPB-HEADER-SLIM 2026-08-29] filmstrip -> RENDER HISTORY toolbar dropdown. Same thumbs
    // container id; the <details> menu needs no show/hide toggling.
    const container = document.getElementById('renderHistoryThumbs');
    if (!container) return;

    if (renderHistory.length === 0) {
        container.innerHTML = '<div style="grid-column:1/-1;font-size:10px;color:var(--text-dim);padding:10px;text-align:center;">No renders yet — hit RENDER and your last 20 land here.</div>';
        return;
    }

    const _escHistory = (typeof escapeHtml === 'function') ? escapeHtml : (s => String(s == null ? '' : s)
        .replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
    let html = '';
    renderHistory.forEach((entry, idx) => {
        const age = Math.round((Date.now() - entry.timestamp) / 1000);
        const ageLabel = age < 60 ? `${age}s ago` : age < 3600 ? `${Math.round(age / 60)}m ago` : `${Math.round(age / 3600)}h ago`;
        const border = entry.favorite ? 'var(--accent-gold)' : (idx === 0 ? 'var(--success)' : 'var(--border)');
        const favStar = entry.favorite ? '<span style="position:absolute;top:1px;right:2px;color:var(--accent-gold);font-size:10px;text-shadow:0 0 3px #000;">&#9733;</span>' : '';
        const _stripTitle = _escHistory((entry.zones_summary || '') + '\n' + ageLabel + ' | ' + entry.elapsed_seconds + 's | ' + entry.zone_count + ' zones' + (entry.notes ? '\nNote: ' + entry.notes : '') + '\nClick to rebuild this render');
        const _stripThumb = _escHistory(entry.thumb || entry.paint_url || '');
        html += `<div onclick="restoreHistoryItem(${idx})" title="${_stripTitle}"
            style="cursor:pointer; position:relative; border:1px solid ${border}; border-radius:3px; overflow:hidden; flex-shrink:0; width:56px; height:56px; transition:border-color 0.15s;">
            <img src="${_stripThumb}" style="width:100%; height:100%; object-fit:cover;" loading="lazy" onerror="this.style.display='none'">
            ${favStar}
            <div style="position:absolute; bottom:0; left:0; right:0; background:rgba(0,0,0,0.7); font-size:7px; color:#aaa; text-align:center; padding:1px;">${ageLabel}</div>
        </div>`;
    });
    container.innerHTML = html;
}

// Scripts load after the UI shell; hydrate once and immediately paint the
// strip. Corrupt/quota-hostile storage is ignored by the bounded parser above.
restorePersistedRenderHistory();
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateHistoryStrip, { once: true });
} else {
    updateHistoryStrip();
}

/** Show a specific history item's preview in the results panel. // [48]
 * @param {number} index - Index in renderHistory array
 */
function showHistoryItem(index) {
    const entry = renderHistory[index];
    if (!entry) return;

    const paintImg = document.getElementById('renderPaintPreview');
    const specImg = document.getElementById('renderSpecPreview');
    const elapsed = document.getElementById('renderElapsed');
    const panel = document.getElementById('renderResultsPanel');

    if (paintImg && entry.paint_url) paintImg.src = entry.paint_url;
    if (specImg && entry.spec_url) specImg.src = entry.spec_url;
    if (elapsed) elapsed.textContent = `${entry.elapsed_seconds}s | ${entry.zone_count} zones (history #${index + 1})`;
    if (panel) panel.style.display = 'block';

    // Load for compare mode too
    if (entry.paint_url) loadRenderedImageForCompare(entry.paint_url);

    showToast(`Loaded render #${index + 1} from history`);
}

/** Toggle iRacing Live Link setting on/off and save to server config. // [49]
 * @param {boolean} enabled - Whether live link should be enabled
 */
function toggleLiveLink(enabled) {
    ShokkerAPI.saveConfig({ live_link_enabled: enabled }).then(res => {
        if (res && res.success) { // [55] null check on res
            const badge = document.getElementById('liveLinkBadge');
            if (badge) badge.style.display = enabled ? 'inline' : 'none';
            showToast(enabled ? 'iRacing Live Link enabled!' : 'Live Link disabled');
        } else if (res && res.error) {
            showToast('Could not save Live Link setting: ' + res.error, true); // [40] specific
        }
    }).catch(() => showToast('Could not save config. Is the server running?', true)); // [38] specific
}

/** Toggle custom number mode for car file naming. // [49]
 * @param {boolean} enabled - Whether to use custom number format
 */
function toggleCustomNumber(enabled) {
    ShokkerAPI.saveConfig({ use_custom_number: enabled }).then(res => {
        if (res && res.success) { // [55] null check
            showToast(enabled ? 'Car files: car_num_XXXXX.tga (custom numbers)' : 'Car files: car_XXXXX.tga (no custom numbers)');
        } else if (res && res.error) {
            showToast('Could not save number setting: ' + res.error, true); // [40] specific
        }
    }).catch(() => showToast('Could not save config. Is the server running?', true)); // [38] specific
}

// ===== RENDER HISTORY GALLERY WITH COMPARE =====
let historyCompareA = -1;
let historyCompareB = -1;

// Inline handlers receive only a numeric history index. Entry strings never
// enter JavaScript-in-HTML contexts; helpers resolve the trusted object here.
function historyShareRender(idx) {
    const entry = renderHistory[idx];
    if (entry) copyRenderShareLink(entry.job_id || '');
}
function historyDownloadPaint(idx) {
    const entry = renderHistory[idx];
    if (entry) downloadRenderFile(entry.paint_url || '', entry.filename || 'render.png');
}
function historyShowChannels(idx) {
    const entry = renderHistory[idx];
    if (entry) showSpecChannels(entry.spec_url || '');
}
function historyShowHistogram(idx) {
    const entry = renderHistory[idx];
    if (entry) showRenderHistogram(entry.paint_url || '');
}
if (typeof window !== 'undefined') {
    window.historyShareRender = historyShareRender;
    window.historyDownloadPaint = historyDownloadPaint;
    window.historyShowChannels = historyShowChannels;
    window.historyShowHistogram = historyShowHistogram;
}

/** Open the full-screen render history gallery with compare support. // [50] */
function openHistoryGallery() {
    if (renderHistory.length === 0) { showToast('No render history yet', true); return; }

    historyCompareA = -1;
    historyCompareB = -1;

    let overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.id = 'historyGalleryOverlay';
    overlay.className = 'history-gallery-overlay';
    overlay.innerHTML = buildGalleryHTML();
    document.body.appendChild(overlay);
}

function buildGalleryHTML() {
    // [IMP] Pagination + search + filter
    const searchInput = document.getElementById('historySearchInput');
    const query = searchInput ? searchInput.value : (window._historySearchQuery || '');
    const visibleIdx = (typeof filterRenderHistory === 'function' ? filterRenderHistory(query) : renderHistory.map((_, i) => i));
    const start = _historyPage * HISTORY_PAGE_SIZE;
    const slice = visibleIdx.slice(start, start + HISTORY_PAGE_SIZE);
    const totalPages = Math.max(1, Math.ceil(visibleIdx.length / HISTORY_PAGE_SIZE));
    const _esc = (typeof escapeHtml === 'function') ? escapeHtml : (s => String(s || '')
        .replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));

    let cards = '';
    slice.forEach((idx) => {
        const entry = renderHistory[idx];
        if (!entry) return;
        const age = Math.round((Date.now() - entry.timestamp) / 1000);
        const ageLabel = age < 60 ? `${age}s ago` : age < 3600 ? `${Math.round(age / 60)}m ago` : `${Math.round(age / 3600)}h ago`;
        const selA = idx === historyCompareA ? ' compare-selected' : '';
        const selB = idx === historyCompareB ? ' compare-selected' : '';
        const badge = idx === 0 ? '<span class="history-card-badge" style="background:rgba(0,255,136,0.2);color:var(--success);">LATEST</span>' : '';
        const favIcon = entry.favorite ? '&#9733;' : '&#9734;';
        // BUG #69 (Bigelow, HIGH): tags / notes / zones_summary come from the
        // painter's own `prompt()` input via editHistoryTags / editHistoryNotes
        // and were being interpolated RAW into innerHTML. A note like
        // `<img src=x onerror=alert(1)>` executed on every gallery re-render.
        // Escape EVERY user-originated string before it lands in this template.
        const tags = (entry.tags || []).slice(0, 3).map(t => `<span style="background:rgba(255,170,0,0.15);color:var(--accent-gold);padding:0 4px;border-radius:2px;font-size:9px;margin-right:2px;">${_esc(t)}</span>`).join('');
        const _summary = _esc(entry.zones_summary || '');
        const _notesShort = entry.notes ? _esc(String(entry.notes).slice(0, 60)) : '';
        // Use the already-persisted 96px data thumbnail for the grid. The full
        // 2048 image remains available for compare/lightbox actions on demand.
        const _gridThumb = _esc(entry.thumb || entry.paint_url || '');
        cards += `<div class="history-card${selA}${selB}" onclick="gallerySelectItem(${idx})" ondblclick="restoreHistoryItem(${idx})">
            ${badge}
            <img src="${_gridThumb}" alt="Render #${idx + 1}" loading="lazy" onerror="this.style.background='#222'">
            <div class="history-card-info">
                <div class="hc-time">${ageLabel} &middot; ${entry.elapsed_seconds}s &middot; ${entry.zone_count} zones</div>
                <div class="hc-summary" title="${_summary}">${_summary}</div>
                ${tags ? `<div style="margin-top:2px;">${tags}</div>` : ''}
                ${_notesShort ? `<div style="font-size:9px;color:var(--text-dim);margin-top:2px;font-style:italic;">${_notesShort}</div>` : ''}
                <div class="hc-actions" onclick="event.stopPropagation()" style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap;">
                    <button class="btn btn-sm" title="Favorite" onclick="toggleHistoryFavorite(${idx})" style="font-size:11px;padding:1px 5px;">${favIcon}</button>
                    <button class="btn btn-sm" title="Notes" onclick="editHistoryNotes(${idx})" style="font-size:9px;padding:1px 5px;">Note</button>
                    <button class="btn btn-sm" title="Tags" onclick="editHistoryTags(${idx})" style="font-size:9px;padding:1px 5px;">Tags</button>
                    <button class="btn btn-sm" title="Share link" onclick="historyShareRender(${idx})" style="font-size:9px;padding:1px 5px;">Share</button>
                    <button class="btn btn-sm" title="Download paint" onclick="historyDownloadPaint(${idx})" style="font-size:9px;padding:1px 5px;">DL</button>
                    <button class="btn btn-sm" title="Channels" onclick="historyShowChannels(${idx})" style="font-size:9px;padding:1px 5px;">Ch</button>
                    <button class="btn btn-sm" title="Histogram" onclick="historyShowHistogram(${idx})" style="font-size:9px;padding:1px 5px;">Hist</button>
                    <button class="btn btn-sm" title="Delete" onclick="deleteHistoryItem(${idx})" style="font-size:9px;padding:1px 5px;color:#ff6666;">&times;</button>
                </div>
            </div>
        </div>`;
    });
    const pager = totalPages > 1
        ? `<div class="history-pager" style="display:flex;gap:6px;justify-content:center;padding:8px;">
                <button class="btn btn-sm" onclick="setHistoryPage(${_historyPage - 1})" ${_historyPage === 0 ? 'disabled' : ''}>Prev</button>
                <span style="font-size:10px;color:var(--text-dim);align-self:center;">Page ${_historyPage + 1} / ${totalPages} (${visibleIdx.length} renders)</span>
                <button class="btn btn-sm" onclick="setHistoryPage(${_historyPage + 1})" ${_historyPage >= totalPages - 1 ? 'disabled' : ''}>Next</button>
           </div>`
        : '';

    const _compareA = historyCompareA >= 0 ? renderHistory[historyCompareA] : null;
    const _compareB = historyCompareB >= 0 ? renderHistory[historyCompareB] : null;
    const _compareASummary = _esc((_compareA && _compareA.zones_summary) || '');
    const _compareBSummary = _esc((_compareB && _compareB.zones_summary) || '');
    const _compareAUrl = _esc((_compareA && _compareA.paint_url) || '');
    const _compareBUrl = _esc((_compareB && _compareB.paint_url) || '');
    const compareBar = (_compareA && _compareB)
        ? `<div class="history-compare-bar">
            <span>Comparing #${historyCompareA + 1} vs #${historyCompareB + 1}</span>
            <button class="btn btn-sm" onclick="showRenderDiff(${historyCompareA}, ${historyCompareB})" style="font-size:9px;">Diff</button>
            <button class="btn btn-sm" onclick="clearHistoryCompare()" style="font-size:9px;">Clear</button>
           </div>
           <div class="history-compare-view">
            <div class="history-compare-pane">
                <div class="compare-label">Render #${historyCompareA + 1}</div>
                <img src="${_compareAUrl}" alt="A">
                <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">${_compareASummary}</div>
            </div>
            <div class="history-compare-pane">
                <div class="compare-label">Render #${historyCompareB + 1}</div>
                <img src="${_compareBUrl}" alt="B">
                <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">${_compareBSummary}</div>
            </div>
           </div>`
        : '';

    const hint = historyCompareA < 0 ? 'Click to select for compare. Double-click to restore zone config.'
        : historyCompareB < 0 ? 'Click another render to compare. Double-click to restore.'
            : 'Comparing two renders — click Diff for pixel delta. Double-click any card to restore.';

    // [IMP] Search box wired to filterRenderHistory + favorites filter
    const favOnly = window._historyFavOnly ? 'checked' : '';
    return `<div class="history-gallery-header">
        <h3>RENDER HISTORY GALLERY (${renderHistory.length})</h3>
        <input id="historySearchInput" type="text" placeholder="Search zones / notes / tags..." value="${_esc(query || '')}"
               oninput="window._historySearchQuery=this.value; setHistoryPage(0);"
               style="flex:1;max-width:240px;padding:3px 6px;font-size:11px;background:#222;border:1px solid var(--border);color:#eee;border-radius:3px;">
        <label style="font-size:10px;color:var(--text-dim);cursor:pointer;"><input type="checkbox" ${favOnly} onchange="window._historyFavOnly=this.checked; setHistoryPage(0);"> Favorites only</label>
        <span style="font-size:10px; color:var(--text-dim);">${hint}</span>
        <button class="btn btn-sm" onclick="closeHistoryGallery()" style="font-size:11px;">&times; Close</button>
    </div>
    <div class="history-gallery-body">${cards || '<div style="padding:20px;color:var(--text-dim);">No renders match.</div>'}</div>
    ${pager}
    ${compareBar}`;
}

function gallerySelectItem(idx) {
    if (historyCompareA < 0) {
        historyCompareA = idx;
    } else if (historyCompareB < 0 && idx !== historyCompareA) {
        historyCompareB = idx;
    } else {
        // Reset and start new selection
        historyCompareA = idx;
        historyCompareB = -1;
    }
    // Re-render gallery
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}

function clearHistoryCompare() {
    historyCompareA = -1;
    historyCompareB = -1;
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}

/** Restore zone configuration from a history entry (double-click in gallery). // [50]
 * @param {number} idx - Index in renderHistory array
 */
function restoreHistoryItem(idx) {
    const entry = renderHistory[idx];
    if (!entry || !entry.zoneSnapshot) {
        showToast('No zone snapshot for this render', true);
        return;
    }
    if (!confirm(`Restore zone config from render #${idx + 1}? Your current zones will be replaced.`)) return;

    zones = _recipeSnapshotToZones(entry.zoneSnapshot);
    selectedZoneIndex = 0;
    renderZones();
    triggerPreviewRender();
    autoSave();
    closeHistoryGallery();
    // [SPB-HEADER-SLIM 2026-08-29] the toolbar glue only auto-closes .vtool-btn clicks
    var _rhMenu = document.getElementById('spbRenderHistMenu');
    if (_rhMenu) _rhMenu.removeAttribute('open');
    showToast(`Restored zone config from render #${idx + 1}`);
    // owner: "Fully rebuilt if you click on any of them" — fire the full render, not just the preview
    if (typeof safeDoRender === 'function') safeDoRender();
}

function closeHistoryGallery() {
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.remove();
}

/**
 * [SPB-RECENTS-001] Map a saved zone snapshot back to full live zone objects.
 * Restores the FULL recipe — base/pattern/finish + colors AND the spec-pattern
 * overlays + blend / cc-quality / paint-reactive fields that the old restore
 * dropped. Owner ask: recall must "restore the FULL recipe".
 */
function _recipeSnapshotToZones(snapshot) {
    if (!Array.isArray(snapshot)) return [];
    // [2026-06-12 owner: "EXACTLY REPLICATE THIS"] full-fidelity restore —
    // spread EVERY saved field (spec sliders, base HSB, overlay tiers, blend
    // modes, future dials), then normalize the required ones and reset
    // transient state. The old whitelist dropped unknown fields on restore.
    return snapshot.map(z => {
        const o = Object.assign({}, z);
        o.name = z.name || 'Zone';
        o.base = z.base || null;
        o.pattern = z.pattern || 'none';
        o.finish = z.finish || null;
        o.intensity = z.intensity || '100';
        o.customSpec = z.customSpec != null ? z.customSpec : null;
        o.customPaint = z.customPaint != null ? z.customPaint : null;
        o.customBright = z.customBright != null ? z.customBright : null;
        o.colorMode = z.colorMode || 'none';
        o.pickerColor = z.pickerColor || '#3366ff';
        o.pickerTolerance = z.pickerTolerance || 40;
        o.colors = Array.isArray(z.colors) ? z.colors : [];
        o.scale = z.scale || 1.0;
        o.patternOpacity = z.patternOpacity ?? 100;
        o.patternStack = Array.isArray(z.patternStack) ? z.patternStack : [];
        o.specPatternStack = Array.isArray(z.specPatternStack) ? z.specPatternStack : [];
        o.overlaySpecPatternStack = Array.isArray(z.overlaySpecPatternStack) ? z.overlaySpecPatternStack : [];
        o.wear = z.wear || 0;
        o.muted = z.muted || false;
        o.regionMask = null;
        o.lockBase = false; o.lockPattern = false; o.lockIntensity = false; o.lockColor = false;
        return o;
    });
}

/** [SPB-LIVERY-APPLY-001] Canonical in-scope zone installer used by the Prompt-to-Livery
 *  and Photo->Livery experimental panels (js/features/*). Runs in the bundle scope so it CAN
 *  reassign the top-level `let zones` binding (a separate feature <script> cannot reach it).
 *  Mirrors restoreRecipeFromRecent(). Returns true on success, false (non-destructive) on miss. */
function spbApplyZones(rawZones) {
    if (!Array.isArray(rawZones) || !rawZones.length) return false;
    try {
        zones = _recipeSnapshotToZones(rawZones);   // normalize + full-fidelity restore
        selectedZoneIndex = 0;
        renderZones();                              // rebuild the zone-list UI
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        else if (typeof window.spbKickLivePreview === 'function') window.spbKickLivePreview();
        if (typeof autoSave === 'function') autoSave();
        if (typeof showToast === 'function') showToast('Livery applied — ' + zones.length + ' zones');
        return true;
    } catch (e) {
        console.error('[spbApplyZones] failed:', e);
        if (typeof showToast === 'function') showToast('Could not apply livery: ' + (e && e.message || e), true);
        return false;
    }
}
if (typeof window !== 'undefined') { window.spbApplyZones = spbApplyZones; }

/** [SPB-RECENTS-001] Persist a render-history entry to the rotating last-10 on disk. */
async function saveRecentRenderToDisk(entry) {
    if (!entry) return;
    try {
        await fetch(ShokkerAPI.baseUrl + '/recent-renders/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: entry.job_id || '',
                recipe: {
                    timestamp: entry.timestamp,
                    elapsed_seconds: entry.elapsed_seconds,
                    zone_count: entry.zone_count,
                    zones_summary: entry.zones_summary,
                    filename: entry.filename,
                    metadata: entry.metadata,
                    zoneSnapshot: entry.zoneSnapshot,
                },
            }),
            signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS),
        });
    } catch (e) {
        console.warn('[recent-renders] disk save failed:', e);
    }
}

/** [SPB-RECENTS-001] Open the recall panel listing the last 10 disk-saved renders. */
async function openRecentRendersPanel() {
    let overlay = document.getElementById('recentRendersOverlay');
    if (overlay) overlay.remove();
    overlay = document.createElement('div');
    overlay.id = 'recentRendersOverlay';
    overlay.className = 'recent-renders-overlay';
    overlay.innerHTML =
        '<div class="recent-renders-card" role="dialog" aria-label="Recent renders">' +
        '<div class="recent-renders-header"><h3>📁 RECENT RENDERS — last 10 (auto-saved)</h3>' +
        '<span style="flex:1 1 auto;"></span>' +
        '<button class="btn btn-sm" onclick="importRecipeFile()" style="border-color:var(--accent-gold);color:var(--accent-gold);" title="Import a .shokkerrecipe file (yours or shared by someone) and restore the full recipe">📥 Import Recipe</button>' +
        '<button class="btn btn-sm" onclick="closeRecentRendersPanel()" aria-label="Close recent renders">&times; Close</button></div>' +
        '<div class="recent-renders-body" id="recentRendersBody"><div style="padding:20px;color:var(--text-dim);">Loading…</div></div></div>';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeRecentRendersPanel(); });
    document.body.appendChild(overlay);
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/recent-renders/list', { signal: AbortSignal.timeout(API_TIMEOUT_GENERAL_MS) });
        const data = await safeParseJSON(res, 'recent renders');
        const body = document.getElementById('recentRendersBody');
        if (!body) return;
        const renders = (data && data.renders) || [];
        if (!renders.length) {
            body.innerHTML = '<div style="padding:20px;color:var(--text-dim);">No saved renders yet. Render a car and it gets saved here automatically (last 10 kept).</div>';
            return;
        }
        window._recentRendersCache = renders;
        const esc = (typeof _spbEscapeRenderHtml === 'function') ? _spbEscapeRenderHtml : (s => String(s == null ? '' : s));
        body.innerHTML = renders.map((r, i) => {
            const rec = r.recipe || {};
            const when = rec.timestamp ? new Date(rec.timestamp).toLocaleString() : '';
            const secs = rec.elapsed_seconds != null ? `${rec.elapsed_seconds}s` : '';
            const zc = rec.zone_count != null ? `${rec.zone_count} zones` : '';
            const summary = esc(rec.zones_summary || '');
            const paint = r.has_paint ? `${ShokkerAPI.baseUrl}${r.paint_url}` : '';
            const spec = r.has_spec ? `${ShokkerAPI.baseUrl}${r.spec_url}` : '';
            const canLoad = !!(rec.zoneSnapshot && rec.zoneSnapshot.length);
            return `<div class="recent-render-card">
                <div class="recent-render-thumbs">
                    ${paint ? `<img src="${paint}" alt="Rendered car" title="Rendered car">` : '<div class="recent-render-noimg">no paint</div>'}
                    ${spec ? `<img src="${spec}" alt="Spec map" title="Spec map">` : '<div class="recent-render-noimg">no spec</div>'}
                </div>
                <div class="recent-render-meta">
                    <div class="recent-render-time">${secs}${secs && zc ? ' · ' : ''}${zc}</div>
                    <div class="recent-render-when">${esc(when)}</div>
                    <div class="recent-render-summary" title="${summary}">${summary || '—'}</div>
                </div>
                <button class="btn btn-sm recent-render-load" ${canLoad ? '' : 'disabled'} onclick="restoreRecipeFromRecent(${i})"
                    title="${canLoad ? 'Restore this full recipe (all zones, patterns, spec overlays)' : 'No recipe data saved for this render'}">↺ Load recipe</button>
            </div>`;
        }).join('');
    } catch (e) {
        const body = document.getElementById('recentRendersBody');
        const msg = (typeof classifyFetchError === 'function') ? classifyFetchError(e, 'recent renders') : String(e);
        if (body) body.innerHTML = `<div style="padding:20px;color:#ff6b6b;">Could not load recent renders: ${msg}</div>`;
    }
}

function closeRecentRendersPanel() {
    const overlay = document.getElementById('recentRendersOverlay');
    if (overlay) overlay.remove();
}

/** [SPB-RECENTS-001] Restore the full recipe from a recalled disk-saved render. */
function restoreRecipeFromRecent(i) {
    const renders = window._recentRendersCache || [];
    const r = renders[i];
    const snap = r && r.recipe && r.recipe.zoneSnapshot;
    if (!snap || !Array.isArray(snap) || !snap.length) { showToast('No recipe data for this render', true); return; }
    if (!confirm('Restore this full recipe? Your current zones will be replaced.')) return;
    zones = _recipeSnapshotToZones(snap);
    selectedZoneIndex = 0;
    renderZones();
    triggerPreviewRender();
    autoSave();
    closeRecentRendersPanel();
    closeRenderResults();
    showToast('Recipe restored from saved render');
}

if (typeof window !== 'undefined') {
    window.openRecentRendersPanel = openRecentRendersPanel;
    window.closeRecentRendersPanel = closeRecentRendersPanel;
    window.restoreRecipeFromRecent = restoreRecipeFromRecent;
    window.saveRecentRenderToDisk = saveRecentRenderToDisk;
}

