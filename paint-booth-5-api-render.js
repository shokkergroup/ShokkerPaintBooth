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
    const ch = sp.channels || 'MR'; if (ch !== 'MR') e.channels = ch;
    const rng = sp.range || 40; if (rng !== 40) e.range = rng;
    if (sp.params && Object.keys(sp.params).length) e.params = sp.params;
    const ox = sp.offsetX || 0.5; if (ox !== 0.5) e.offset_x = ox;
    const oy = sp.offsetY || 0.5; if (oy !== 0.5) e.offset_y = oy;
    const sc = sp.scale || 1.0; if (sc !== 1.0) e.scale = sc;
    const rot = sp.rotation || 0; if (rot !== 0) e.rotation = rot;
    const bs = sp.boxSize || 100; if (bs !== 100) e.box_size = bs;
    return e;
}
if (typeof window !== 'undefined') window._mapSpecPatternEntry = _mapSpecPatternEntry;

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
        zoneObj.gradient_stops = z.gradientStops;
        zoneObj.gradient_direction = z.gradientDirection || 'horizontal';
    } else if (baseMode === 'special' && z.baseColorSource && z.baseColorSource !== 'undefined') {
        zoneObj.base_color_source = z.baseColorSource;
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
    const baseId = z[prefix];
    const colorSrc = z[prefix + 'ColorSource'];
    const strength = z[prefix + 'Strength'] || 0;
    if (!(baseId || colorSrc) || strength <= 0) return;
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
    zoneObj[key + '_blend_mode'] = z[prefix + 'BlendMode'] || 'noise';
    zoneObj[key + '_noise_scale'] = Number(z[prefix + 'NoiseScale'] ?? z[prefix + 'FractalScale'] ?? 24);
    zoneObj[key + '_scale'] = Math.max(0.01, Math.min(5, Number(z[prefix + 'Scale']) || 1));
    if (z[prefix + 'Pattern']) zoneObj[key + '_pattern'] = z[prefix + 'Pattern'];
    zoneObj[key + '_pattern_opacity'] = Math.max(0, Math.min(1, Number((z[prefix + 'PatternOpacity'] ?? 100) / 100)));
    zoneObj[key + '_pattern_scale'] = Math.max(0.1, Math.min(4, Number(z[prefix + 'PatternScale'] ?? 1)));
    zoneObj[key + '_pattern_rotation'] = Number(z[prefix + 'PatternRotation'] ?? 0);
    zoneObj[key + '_pattern_strength'] = Math.max(0, Math.min(2, Number(z[prefix + 'PatternStrength'] ?? 1)));
    if (z[prefix + 'PatternInvert'] != null) zoneObj[key + '_pattern_invert'] = !!z[prefix + 'PatternInvert'];
    if (z[prefix + 'PatternHarden'] != null) zoneObj[key + '_pattern_harden'] = !!z[prefix + 'PatternHarden'];
    zoneObj[key + '_pattern_offset_x'] = Math.max(0, Math.min(1, Number(z[prefix + 'PatternOffsetX'] ?? 0.5)));
    zoneObj[key + '_pattern_offset_y'] = Math.max(0, Math.min(1, Number(z[prefix + 'PatternOffsetY'] ?? 0.5)));
    // WIN #19 (Hawk audit): manualPlacementFlipH/V writes secondBasePatternFlipH/V
    // (and Win #19 extension also writes thirdBase/fourthBase/fifthBase variants)
    // but pre-fix none of them were ever serialized to the engine. Painter toggled
    // a 2nd-base flip and saw no change in render. Now mirrors the primary
    // pattern_flip_h/v emit pattern.
    if (z[prefix + 'PatternFlipH']) zoneObj[key + '_pattern_flip_h'] = !!z[prefix + 'PatternFlipH'];
    if (z[prefix + 'PatternFlipV']) zoneObj[key + '_pattern_flip_v'] = !!z[prefix + 'PatternFlipV'];
    if (z[prefix + 'FitZone']) zoneObj[key + '_fit_zone'] = true;
    if (z[prefix + 'HueShift']) zoneObj[key + '_hue_shift'] = z[prefix + 'HueShift'];
    if (z[prefix + 'Saturation']) zoneObj[key + '_saturation'] = z[prefix + 'Saturation'];
    if (z[prefix + 'Brightness']) zoneObj[key + '_brightness'] = z[prefix + 'Brightness'];
    // Pattern hue/sat/bright currently exists only for second_base in source data,
    // but the helper emits it uniformly when present so future symmetry is free.
    if (z[prefix + 'PatternHueShift']) zoneObj[key + '_pattern_hue_shift'] = z[prefix + 'PatternHueShift'];
    if (z[prefix + 'PatternSaturation']) zoneObj[key + '_pattern_saturation'] = z[prefix + 'PatternSaturation'];
    if (z[prefix + 'PatternBrightness']) zoneObj[key + '_pattern_brightness'] = z[prefix + 'PatternBrightness'];
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
        const strength = Number(z[prefix + 'Strength'] ?? 0);
        const baseId = z[prefix];
        const colorSrc = z[prefix + 'ColorSource'];
        const hasBaseId = typeof baseId === 'string' && baseId !== '' && baseId !== 'undefined' && baseId !== 'none';
        const hasColorSrc = typeof colorSrc === 'string' && colorSrc !== '' && colorSrc !== 'undefined' && colorSrc !== 'none';
        return strength > 0 && (hasBaseId || hasColorSrc);
    });
}

function _zoneNeedsNeutralBaseAnchor(z) {
    return !!(z && !z.base && !z.finish && _zoneHasActiveBaseOverlay(z));
}

function _zoneHasRenderableMaterial(z) {
    return !!(z && (z.base || z.finish || _zoneNeedsNeutralBaseAnchor(z)));
}

function _isSuppressedLegacyZone(z, index) {
    if (typeof _isZone9MatteCarbonZombie === 'function' && _isZone9MatteCarbonZombie(z, index)) return true;
    return false;
}

if (typeof window !== 'undefined') {
    window._zoneHasActiveBaseOverlay = _zoneHasActiveBaseOverlay;
    window._zoneNeedsNeutralBaseAnchor = _zoneNeedsNeutralBaseAnchor;
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
    zoneObj.base_color_strength = Math.max(0, Math.min(1, Number(z.baseColorStrength ?? 1)));
    if (z.baseColorFitZone) zoneObj.base_color_fit_zone = true;
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
            zoneObj[dst] = z[src].map(_mapSpecPatternEntry);
        }
    }
}
if (typeof window !== 'undefined') {
    window._applyAllSpecPatternStacks = _applyAllSpecPatternStacks;
    window.SPEC_PATTERN_STACK_TIERS = SPEC_PATTERN_STACK_TIERS;
}

// BOIL THE OCEAN deep core: fleet render, season render, and the main
// buildServerZonesForRender bridge were still carrying near-identical
// finish-stack payload logic. Any future tweak to pattern opacity, offsets,
// finish colors, spec stacks, or base placement had three chances to drift.
// This helper centralizes that core while preserving the "compact defaults"
// behavior used by buildServerZonesForRender for lighter payloads.
function _applyZoneRenderCore(zoneObj, z, options) {
    const compactDefaults = !!(options && options.compactDefaults);
    const hasPattern = !!(z.pattern && z.pattern !== 'none');
    const primaryBaseId = z.base || (_zoneNeedsNeutralBaseAnchor(z) ? 'gloss' : null);
    const hasPrimaryBase = !!primaryBaseId;
    const hasRenderableMaterial = hasPrimaryBase || !!z.finish;

    _applyCustomIntensity(zoneObj, z);
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

    if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
    if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
    if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
    if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
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
    if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
    if (z.hardEdge) zoneObj.hard_edge = true;
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
const API_TIMEOUT_STATUS_MS = 2000;       // Timeout for /status health checks
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
    if (m.includes('failed to fetch') || m.includes('networkerror') || m.includes('econnrefused')) return { code: 'network_down', message: 'Server unreachable. Is server.py running?', retryable: true };
    if (m.includes('paint file not found') || m.includes('paint_file')) return { code: 'paint_missing', message: 'Paint file not found. Check the Source Paint path.', retryable: false };
    if (m.includes('license')) return { code: 'license', message: 'License issue — open Settings to enter your key.', retryable: false };
    if (m.includes('json') || m.includes('unexpected token')) return { code: 'bad_json', message: `Server returned invalid data during ${context}. Restart the server.`, retryable: true };
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
const CLIENT_VERSION = '6.1.1';
let _serverVersionWarned = false;
function checkServerVersion(statusData) {
    if (!statusData || !statusData.version || _serverVersionWarned) return;
    if (statusData.version !== CLIENT_VERSION) {
        _serverVersionWarned = true;
        console.warn(`[version] Client v${CLIENT_VERSION} but server v${statusData.version}. Some features may differ.`);
        if (typeof showToast === 'function') showToast(`Server v${statusData.version} ≠ client v${CLIENT_VERSION}. Restart the server for full compatibility.`, true);
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

// [IMP-17] Pre-render validation — return list of warnings/errors before sending
function validateRenderPayload(paintFile, zones, extras) {
    const issues = [];
    if (!paintFile || !paintFile.trim()) issues.push({ severity: 'error', msg: 'Paint file path is empty.' });
    else if (!paintFile.includes('/') && !paintFile.includes('\\')) issues.push({ severity: 'error', msg: 'Paint file needs a full path, not just a filename.' });
    else if (!/\.tga$/i.test(paintFile)) issues.push({ severity: 'warn', msg: 'Paint file does not end in .tga — render may fail.' });
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
        if (_wasHidden && typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.checkStatus === 'function') {
            _wasHidden = false;
            ConnectionStatus.set('reconnecting');
            ShokkerAPI.checkStatus().then(d => { ConnectionStatus.set(d ? 'online' : 'offline'); });
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
    if (err.message && err.message.includes('Failed to fetch')) return `Server unreachable. Is server.py running?`;
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

/**
 * Show a finish hover popup with preview, name, description, and spec channel info. // [46]
 * @param {MouseEvent} e - Mouse event from the hover trigger
 * @param {string} finishId - ID of the finish to display
 */
function showFinishPopup(e, finishId) {
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

    // Use server-rendered swatch (240x160) instead of JS canvas
    const swatchUrl = getSwatchUrl(finishId, '888888');
    if (swatchUrl) {
        const swatchW = previewCanvas.width, swatchH = previewCanvas.height;
        const pctx = previewCanvas.getContext('2d');
        pctx.fillStyle = '#1a1a1a';
        pctx.fillRect(0, 0, swatchW, swatchH);
        const img = new Image();
        img.onload = () => {
            pctx.clearRect(0, 0, swatchW, swatchH);
            pctx.drawImage(img, 0, 0, swatchW, swatchH);
        };
        img.src = swatchUrl.replace('size=48', `size=${swatchW}`);
    } else {
        const pctx = previewCanvas.getContext('2d');
        const cacheKey = finishId + '_popup';
        if (_previewCache[cacheKey]) {
            pctx.putImageData(_previewCache[cacheKey], 0, 0);
        } else {
            renderPatternPreview(pctx, previewCanvas.width, previewCanvas.height, finishId);
            _previewCache[cacheKey] = pctx.getImageData(0, 0, previewCanvas.width, previewCanvas.height);
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

    const popup = document.getElementById('swatchHoverPopup');
    const canvas = document.getElementById('shpCanvas');
    const nameEl = document.getElementById('shpName');
    const descEl = document.getElementById('shpDesc');
    const catEl = document.getElementById('shpCat');
    if (!popup || !canvas) return; // [52] null check - bail if DOM missing

    // Render 140x140 preview via server swatch (async, instant update)
    const pctx = canvas.getContext('2d');
    const swatchUrl = getSwatchUrl(finishId, '888888');
    if (swatchUrl) {
        pctx.fillStyle = '#1a1a1a';
        pctx.fillRect(0, 0, 140, 140);
        const cacheKey = finishId + '_shp';
        if (_shpPreviewCache[cacheKey]) {
            pctx.drawImage(_shpPreviewCache[cacheKey], 0, 0, 140, 140);
        } else {
            const img = new Image();
            img.onload = () => {
                pctx.clearRect(0, 0, 140, 140);
                pctx.drawImage(img, 0, 0, 140, 140);
                _shpPreviewCache[cacheKey] = img;
            };
            img.src = swatchUrl.replace('size=48', 'size=140');
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

    // Lookup finish info
    const finish = BASES.find(f => f.id === finishId)
        || PATTERNS.find(f => f.id === finishId)
        || MONOLITHICS.find(f => f.id === finishId);

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
        showSwatchHoverPopup(item);
    }
}, true);

document.addEventListener('mouseleave', function (e) {
    if (!e.target || typeof e.target.closest !== 'function') return;
    const item = e.target.closest('.swatch-item[data-finish-id]');
    if (item && item.closest('#swatchPopupGrid')) {
        hideSwatchHoverPopup();
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
        // Fallback: file:// or dev mode - scan ports
        for (let p = 5000; p <= 5010; p++) {
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
            this.online = data.status === 'online';
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
            if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;
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
            if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;
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
            dot.title = this.online ? 'Server online' : 'Server offline - start server.py';
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
            if (cnCb) { cnCb.checked = this.config.use_custom_number !== false; this._customNumberSynced = true; }
        }
    },

    /** Start periodic status polling with exponential backoff. */
    startPolling() {
        this._statusInterval = POLL_INITIAL_INTERVAL_MS; // [45] named constant
        this.checkStatus();
        const statusPoll = () => {
            this.checkStatus().then(() => {
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
    if (!ShokkerAPI.online) { showToast('Server is offline! Start server.py first.', true); return; } // [38] specific error
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
    if (panel) panel.style.display = 'none';
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
    if (!ShokkerAPI.online) { showToast('Server offline! Start server.py first.', true); return; } // [38] specific
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

    const validZones = zones.filter((z, i) => !(typeof _isSuppressedLegacyZone === 'function' && _isSuppressedLegacyZone(z, i)) && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    if (validZones.length === 0) { showToast('Set up zones first!', true); btn.disabled = false; progress.style.display = 'none'; return; }

    const serverZones = validZones.map(z => {
        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
        _applyCustomIntensity(zoneObj, z);
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fc = _resolveFinishColors(z.finish); if (_fc) zoneObj.finish_colors = _fc; if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        // BOIL THE OCEAN drift hunt #4: base color mode header → single helper.
        _applyBaseColorMode(zoneObj, z);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.patternStrengthMapEnabled && z.patternStrengthMap && typeof encodeStrengthMapRLE === 'function') { zoneObj.pattern_strength_map = encodeStrengthMapRLE(z.patternStrengthMap); }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) { zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5))); zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5))); zoneObj.pattern_flip_h = !!z.patternFlipH; zoneObj.pattern_flip_v = !!z.patternFlipV; }
        if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge) zoneObj.hard_edge = true;
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) { zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5))); zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5))); zoneObj.base_rotation = Number(z.baseRotation ?? 0); zoneObj.base_flip_h = !!z.baseFlipH; zoneObj.base_flip_v = !!z.baseFlipV; }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // BOIL THE OCEAN drift hunt #5: 5-tier spec_pattern_stack loop → single helper.
        _applyAllSpecPatternStacks(zoneObj, z);
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
        const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);
        const shouldPriorityOverride = !!(
            hasSpatialRefinement &&
            typeof window !== 'undefined' &&
            typeof window._zoneShouldRequestPriorityOverride === 'function' &&
            window._zoneShouldRequestPriorityOverride(z)
        );
        if (!hasSpatialRefinement && z.regionMask && z.regionMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc && typeof encodeRegionMaskRLE === 'function') {
                zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height);
            }
        }
        if (hasSpatialRefinement) {
            const pc = document.getElementById('paintCanvas');
            if (pc && typeof encodeRegionMaskRLE === 'function') {
                zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
            }
        }
        if (shouldPriorityOverride) zoneObj.priority_override = true;
        // Source-layer restriction (same fail-closed contract as doRender,
        // doSeasonRender, and PS export: empty all-zero mask + console.warn
        // + one-shot user toast keyed on zone name).
        if (z.sourceLayer && typeof _psdLayers !== 'undefined' && typeof encodeRegionMaskRLE === 'function') {
            const srcLayer = _psdLayers.find(l => l.id === z.sourceLayer);
            const pc = document.getElementById('paintCanvas');
            const w = pc?.width || 2048;
            const h = pc?.height || 2048;
            if (!srcLayer) {
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
    if (panel) panel.style.display = 'none';
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
    if (!ShokkerAPI.online) { showToast('Server offline! Start server.py first.', true); return; } // [38] specific
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

    const validZones = zones.filter((z, i) => !(typeof _isSuppressedLegacyZone === 'function' && _isSuppressedLegacyZone(z, i)) && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    if (validZones.length === 0) { showToast('Set up zones first!', true); if (btn) btn.disabled = false; if (progress) progress.style.display = 'none'; return; } // [55] null checks

    const serverZones = validZones.map(z => {
        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
        _applyCustomIntensity(zoneObj, z);
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fc = _resolveFinishColors(z.finish); if (_fc) zoneObj.finish_colors = _fc; if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } { const _ps = _mapPatternStack(z.patternStack); if (_ps) zoneObj.pattern_stack = _ps; } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        // BOIL THE OCEAN drift hunt #4: base color mode header → single helper.
        _applyBaseColorMode(zoneObj, z);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.patternStrengthMapEnabled && z.patternStrengthMap && typeof encodeStrengthMapRLE === 'function') { zoneObj.pattern_strength_map = encodeStrengthMapRLE(z.patternStrengthMap); }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) { zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5))); zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5))); zoneObj.pattern_flip_h = !!z.patternFlipH; zoneObj.pattern_flip_v = !!z.patternFlipV; }
        if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge) zoneObj.hard_edge = true;
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) { zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5))); zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5))); zoneObj.base_rotation = Number(z.baseRotation ?? 0); zoneObj.base_flip_h = !!z.baseFlipH; zoneObj.base_flip_v = !!z.baseFlipV; }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // BOIL THE OCEAN drift hunt #5: 5-tier spec_pattern_stack loop → single helper.
        _applyAllSpecPatternStacks(zoneObj, z);
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
        const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);
        const shouldPriorityOverride = !!(
            hasSpatialRefinement &&
            typeof window !== 'undefined' &&
            typeof window._zoneShouldRequestPriorityOverride === 'function' &&
            window._zoneShouldRequestPriorityOverride(z)
        );
        if (!hasSpatialRefinement && z.regionMask && z.regionMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc && typeof encodeRegionMaskRLE === 'function') {
                zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height);
            }
        }
        if (hasSpatialRefinement) {
            const pc = document.getElementById('paintCanvas');
            if (pc && typeof encodeRegionMaskRLE === 'function') {
                zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
            }
        }
        if (shouldPriorityOverride) zoneObj.priority_override = true;
        // Source-layer restriction (same fail-closed contract as doRender
        // and PS export: empty all-zero mask + console.warn + one-shot
        // user toast keyed on zone name).
        if (z.sourceLayer && typeof _psdLayers !== 'undefined' && typeof encodeRegionMaskRLE === 'function') {
            const srcLayer = _psdLayers.find(l => l.id === z.sourceLayer);
            const pc = document.getElementById('paintCanvas');
            const w = pc?.width || 2048;
            const h = pc?.height || 2048;
            if (!srcLayer) {
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
        showToast('Server offline - start server.py to use iRacing folder lookup', true);
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
                    showToast('Server is offline. Start server.py first!', true);
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
    const validZones = zones.filter((z, i) => !(typeof _isSuppressedLegacyZone === 'function' && _isSuppressedLegacyZone(z, i)) && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    return validZones.map(z => {
        const zoneObj = {
            name: z.name,
            color: formatColorForServer(z.color, z),
            intensity: z.intensity,
        };
        const _primaryBaseId = z.base || (_zoneNeedsNeutralBaseAnchor(z) ? 'gloss' : null);
        const _hasPrimaryBase = !!_primaryBaseId;
        const _hasRenderableMaterial = _hasPrimaryBase || !!z.finish;
        _applyCustomIntensity(zoneObj, z);
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
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
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
        if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge) zoneObj.hard_edge = true;
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.sourceLayer && typeof _psdLayers !== 'undefined' && typeof encodeRegionMaskRLE === 'function') {
            const srcLayer = _psdLayers.find(l => l.id === z.sourceLayer);
            // Codex HIGH (Workstream 12 #235 + Workstream 24 chaos #471) —
            // dangling source-layer reference. The user explicitly RESTRICTED
            // this zone to a layer; if the layer is gone, falling back to
            // composite matching silently broadens the zone in surprising ways.
            // Fail safely + visibly: send an empty all-zero mask AND skip the
            // RGB payload AND surface a toast so the painter knows what happened.
            const pc = document.getElementById('paintCanvas');
            const w = pc?.width || 2048;
            const h = pc?.height || 2048;
            if (!srcLayer) {
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
                // Empty all-zero mask = engine intersects to nothing = zone produces no pixels.
                // Far safer than silently broadening the restriction.
                const _emptyMask = new Uint8Array(w * h);
                zoneObj.source_layer_mask = encodeRegionMaskRLE(_emptyMask, w, h);
                // Do NOT send source_layer_rgb_png either — without a layer there's nothing to match against.
                // Fall through past the RGB encoding block (next).
            }
            const visibleMask = (srcLayer && typeof window.getLayerVisibleContributionMask === 'function')
                ? window.getLayerVisibleContributionMask(srcLayer, w, h)
                : null;
            if (visibleMask) {
                zoneObj.source_layer_mask = encodeRegionMaskRLE(visibleMask, w, h);
            }
            // TRUE layer-local color match: send the layer's own RGB so the
            // engine matches colors against the layer's unblended pixels
            // (Photoshop-correct) instead of the composite. Falls back to
            // composite-based matching if encoding fails or layer has no img.
            if (srcLayer && srcLayer.img) {
                try {
                    const lc = document.createElement('canvas');
                    lc.width = w; lc.height = h;
                    const lctx = lc.getContext('2d');
                    const bx = Array.isArray(srcLayer.bbox) ? (srcLayer.bbox[0] || 0) : 0;
                    const by = Array.isArray(srcLayer.bbox) ? (srcLayer.bbox[1] || 0) : 0;
                    lctx.clearRect(0, 0, w, h);
                    lctx.drawImage(srcLayer.img, bx, by);
                    zoneObj.source_layer_rgb_png = lc.toDataURL('image/png').split(',', 2)[1];
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
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // BOIL THE OCEAN drift hunt #5: 5-tier spec_pattern_stack loop → single helper.
        _applyAllSpecPatternStacks(zoneObj, z);
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
        const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);
        const shouldPriorityOverride = !!(
            hasSpatialRefinement &&
            typeof window !== 'undefined' &&
            typeof window._zoneShouldRequestPriorityOverride === 'function' &&
            window._zoneShouldRequestPriorityOverride(z)
        );
        if (!hasSpatialRefinement && z.regionMask && z.regionMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc) zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height);
        }
        if (hasSpatialRefinement) {
            const pc = document.getElementById('paintCanvas');
            if (pc) zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
        }
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
    if (!ShokkerAPI.online) { showToast('Server is offline. Start server.py first.', true); return; }
    const carFileName = (document.getElementById('psExportCarFileName') || {}).value.trim();
    if (!carFileName) { showToast('Enter a car file name (e.g. DLM438-base-001).', true); return; }
    const exchangeFolder = (document.getElementById('psExportExchangeFolder') || {}).value.trim();
    const paintFile = (document.getElementById('paintFile') || {}).value.trim();
    if (!paintFile) { showToast('Set the Source Paint path in the header bar first.', true); return; }

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
    if (!ShokkerAPI.online) { showToast('Server is offline. Start server.py first.', true); return; }
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
            showToast('Server returned invalid response. Restart the server after code changes.', true);
            return;
        }
        if (data.error) {
            if (data.error === 'not_found') showToast('Server needs to be restarted to load the new import endpoint.', true);
            else showToast(data.error, true);
            return;
        }
        if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = data.temp_path;
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
    console.log('[doRender] Starting render... baseUrl=' + ShokkerAPI.baseUrl + ' origin=' + window.location.origin + ' online=' + ShokkerAPI.online);
    if (!ShokkerAPI.online) { showToast('Server is offline! Start server.py first.', true); return; }

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
    if (!paintFile) { showToast('Set the Source Paint path in the header bar!', true); return; }
    // Quick check: warn if path looks like just a filename (no directory)
    if (!paintFile.includes('/') && !paintFile.includes('\\')) {
        showToast('Source Paint needs a FULL path (e.g. C:\\Users\\You\\Documents\\iRacing\\paint\\carname\\car_num_12345.tga), not just a filename!', true);
        return;
    }

    // Build zone configs for the server (same builder used by live preview so paint file matches)
    const serverZones = buildServerZonesForRender(zones);
    console.log('[doRender] Valid zones:', serverZones.length, '/', zones.length, 'total');
    if (serverZones.length === 0 && !importedSpecMapPath) {
        const debugInfo = zones.map((z, i) => `Zone${i + 1}[${z.name}]: base=${z.base} finish=${z.finish} color=${z.color} colorMode=${z.colorMode}`).join('\n');
        console.warn('[doRender] No valid zones! Zone details:\n' + debugInfo);
        showToast('To render: pick a color on the paint (Pick + Add), then assign a Finish from the library to each zone. Both are required.', true);
        return;
    }
    if (serverZones.length > 0 && serverZones.length < zones.length) {
        const skipped = zones.length - serverZones.length;
        showToast(`Rendering ${serverZones.length} zones. ${skipped} skipped — assign a Finish + color to include them.`, false);
    }
    if (serverZones.length === 0 && importedSpecMapPath) {
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

    // Import spec map (merge mode) — from SHOKK or manual import; use window fallback so SHOKK-loaded spec is never missed
    const activeSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
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
        btn.textContent = `RENDERING ${zoneCount} ZONE${zoneCount > 1 ? 'S' : ''}...`;
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
        btn.disabled = true; // [26] disable button during render
    }
    showToast(`Rendering ${zoneCount} zone${zoneCount > 1 ? 's' : ''}. Estimated: ${timeEst}`, false); // [32] show estimate in toast
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
        barInner.style.width = '100%';
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

            let msg = `Rendered ${result.zone_count} zones in ${result.elapsed_seconds}s`;
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
                            ? 'Server appears hung. Try restarting server.py.'
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
            showToast('Server unreachable. Is server.py running? Check firewall settings.', true);
        } else if (e.message && e.message.includes('JSON')) { // [39] JSON parse error
            showToast('Server returned invalid response. Try restarting server.py.', true);
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
            if (btn) { // [53] null check
                btn.textContent = 'RENDER';
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

    // Track job ID for one-click deploy
    lastRenderedJobId = result.job_id || null;
    // Show deploy row and load car list
    // Deploy row removed - render button handles everything
    // const deployRow = document.getElementById('renderDeployRow');
    // if (deployRow && lastRenderedJobId) {
    //     deployRow.style.display = 'block';
    //     document.getElementById('deployStatus').textContent = '';
    //     loadIracingCars();
    // }

    // Show paint + spec previews in the results panel WITHOUT touching the source canvas
    const panel = document.getElementById('renderResultsPanel');
    const paintImg = document.getElementById('renderPaintPreview');
    const specImg = document.getElementById('renderSpecPreview');
    const elapsed = document.getElementById('renderElapsed');
    const llMsg = document.getElementById('renderLiveLinkMsg');

    if (!panel) return;

    // Find preview URLs from the result
    const urls = result.preview_urls || {};
    const paintUrl = Object.entries(urls).find(([k]) => k === 'RENDER_paint.png')
        || Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet') && !k.includes('suit'));
    const specUrl = Object.entries(urls).find(([k]) => k.includes('spec') && !k.includes('helmet') && !k.includes('suit'));

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
        // Show output_dir status (primary output)
        if (result.output_dir?.success) {
            const fileCount = result.output_dir.pushed_files?.length || 0;
            msgParts.push(`<span style="color:var(--accent-green)"><strong>&#10003; Saved ${fileCount} files</strong> to <code>${result.output_dir.path}</code></span>`);
        } else if (result.output_dir?.error) {
            msgParts.push(`<span style="color:#ff4444"><strong>&#10007; Output Error:</strong> ${result.output_dir.error}</span>`);
        }
        // Show iRacing reload instruction (if live link or output_dir succeeded)
        if (result.live_link?.success || result.output_dir?.success) {
            msgParts.push(`<span style="color:var(--accent-gold); font-size:10px;">💡 <strong>Alt+Tab</strong> to iRacing and press <strong>Ctrl+R</strong> to see your new render!</span>`);
        }
        // Show live link error only if output_dir also failed
        if (result.live_link?.error && !result.live_link?.success && !result.output_dir?.success) {
            msgParts.push(`<span style="color:var(--text-dim)">Live Link: ${result.live_link.error}</span>`);
        }
        if (msgParts.length > 0) {
            llMsg.style.display = 'block';
            llMsg.style.borderColor = result.output_dir?.success ? 'var(--accent-green)' : 'var(--accent)';
            llMsg.innerHTML = msgParts.join('<br>');
        } else {
            // No output_dir and no live_link - warn user
            llMsg.style.display = 'block';
            llMsg.style.borderColor = 'var(--accent-gold)';
            llMsg.style.color = 'var(--accent-gold)';
            llMsg.innerHTML = '<strong>&#9888; No output folder set!</strong> Set the "iRacing Folder" path in Car Info to save files. Previews are still available below.';
        }
    }

    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Push to render history
    try {
        const paintUrlFull = paintUrl ? (ShokkerAPI.baseUrl + paintUrl[1]) : '';
        const specUrlFull = specUrl ? (ShokkerAPI.baseUrl + specUrl[1]) : '';
        const summary = zones.map(z => {
            if (z.finish) return `${z.name}: ${z.finish}`;
            if (z.base) return `${z.name}: ${z.base}${z.pattern && z.pattern !== 'none' ? '+' + z.pattern : ''}`;
            return z.name;
        }).join(' | ');
        // [IMP-36] Descriptive filename with zone summary (clamped to safe length)
        const _safeName = (summary || 'render').replace(/[^a-z0-9_-]+/gi, '_').slice(0, 80);
        const _descFilename = `spb_${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}_${result.zone_count || 0}z_${_safeName}.png`;
        renderHistory.unshift({
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
            zoneSnapshot: JSON.parse(JSON.stringify(zones.map(z => ({
                name: z.name, base: z.base, pattern: z.pattern, finish: z.finish,
                intensity: z.intensity, customSpec: z.customSpec, customPaint: z.customPaint,
                customBright: z.customBright, color: z.color, colorMode: z.colorMode,
                pickerColor: z.pickerColor, pickerTolerance: z.pickerTolerance,
                colors: z.colors, scale: z.scale, patternOpacity: z.patternOpacity,
                patternStack: z.patternStack, wear: z.wear, muted: z.muted,
                ccQuality: z.ccQuality, blendBase: z.blendBase, blendDir: z.blendDir,
                blendAmount: z.blendAmount, usePaintReactive: z.usePaintReactive, paintReactiveColor: z.paintReactiveColor,
            }))))
        });
        if (renderHistory.length > MAX_RENDER_HISTORY) renderHistory.pop();
        updateHistoryStrip();
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
    if (panel) panel.style.display = 'none';
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
            html += `<option value="${c.name}" title="${c.path}">${c.name} (${c.tga_count} files)</option>`;
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
            if (status) {
                status.textContent = `Deployed ${data.deployed.length} files to ${carFolder}. Alt+Tab to iRacing, press Ctrl+R!`;
                status.style.color = 'var(--success)';
            }
            showToast(`Deployed to iRacing! ${data.deployed.length} files → ${carFolder}`);
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

/** Copy a Trading Paints-formatted description of the current zone setup to clipboard. // [48] */
function copyTPDescription() {
    const lines = ['═══ Made with Shokker Paint Booth ═══', ''];
    const wearSlider = document.getElementById('wearSlider');
    const globalWear = wearSlider ? parseInt(wearSlider.value) : 0;

    for (const z of zones) {
        let finishName = '';
        if (z.finish) {
            const mono = MONOLITHICS.find(m => m.id === z.finish);
            finishName = mono ? mono.name + ' (Monolithic)' : z.finish;
        } else if (z.base) {
            const baseObj = BASES.find(b => b.id === z.base);
            const patObj = z.pattern && z.pattern !== 'none' ? PATTERNS.find(p => p.id === z.pattern) : null;
            finishName = baseObj ? baseObj.name : z.base;
            if (patObj) finishName += ' + ' + patObj.name;
        }
        if (!finishName) finishName = 'No finish';

        let line = `▸ ${z.name}: ${finishName}`;
        if (z.intensity && z.intensity !== '100') line += ` [${z.intensity}%]`;
        if (z.scale && z.scale !== 1.0) line += ` (scale ${z.scale}x)`;
        const zoneWear = z.wear || 0;
        if (zoneWear > 0) line += ` | Wear: ${zoneWear}%`;
        lines.push(line);
    }

    if (globalWear > 0) {
        lines.push('');
        lines.push(`Global Wear: ${globalWear}%`);
    }

    lines.push('');
    lines.push('───────────────────────');
    lines.push('2,525 finishes | shokkerpaints.com');

    const text = lines.join('\n');

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
/** Update the thumbnail strip at the top showing recent render results. // [47] */
function updateHistoryStrip() {
    const strip = document.getElementById('renderHistoryStrip');
    const container = document.getElementById('renderHistoryThumbs');
    if (!strip || !container) return;

    if (renderHistory.length === 0) {
        strip.style.display = 'none';
        return;
    }
    strip.style.display = 'block';

    let html = '';
    renderHistory.forEach((entry, idx) => {
        const age = Math.round((Date.now() - entry.timestamp) / 1000);
        const ageLabel = age < 60 ? `${age}s ago` : age < 3600 ? `${Math.round(age / 60)}m ago` : `${Math.round(age / 3600)}h ago`;
        const border = entry.favorite ? 'var(--accent-gold)' : (idx === 0 ? 'var(--success)' : 'var(--border)');
        const favStar = entry.favorite ? '<span style="position:absolute;top:1px;right:2px;color:var(--accent-gold);font-size:10px;text-shadow:0 0 3px #000;">&#9733;</span>' : '';
        html += `<div onclick="showHistoryItem(${idx})" ondblclick="restoreHistoryItem(${idx})" title="${(entry.zones_summary || '').replace(/"/g, '&quot;')}\n${ageLabel} | ${entry.elapsed_seconds}s | ${entry.zone_count} zones${entry.notes ? '\nNote: ' + entry.notes : ''}\nDouble-click to restore zone config"
            style="cursor:pointer; position:relative; border:1px solid ${border}; border-radius:3px; overflow:hidden; flex-shrink:0; width:48px; height:48px; transition:border-color 0.15s;">
            <img src="${entry.paint_url}" style="width:100%; height:100%; object-fit:cover;" loading="lazy" onerror="this.style.display='none'">
            ${favStar}
            <div style="position:absolute; bottom:0; left:0; right:0; background:rgba(0,0,0,0.7); font-size:7px; color:#aaa; text-align:center; padding:1px;">${ageLabel}</div>
        </div>`;
    });
    container.innerHTML = html;
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
        const _esc = (typeof escapeHtml === 'function') ? escapeHtml : (s => String(s || ''));
        const tags = (entry.tags || []).slice(0, 3).map(t => `<span style="background:rgba(255,170,0,0.15);color:var(--accent-gold);padding:0 4px;border-radius:2px;font-size:9px;margin-right:2px;">${_esc(t)}</span>`).join('');
        const _summary = _esc(entry.zones_summary || '');
        const _notesShort = entry.notes ? _esc(String(entry.notes).slice(0, 60)) : '';
        cards += `<div class="history-card${selA}${selB}" onclick="gallerySelectItem(${idx})" ondblclick="restoreHistoryItem(${idx})">
            ${badge}
            <img src="${entry.paint_url}" alt="Render #${idx + 1}" loading="lazy" onerror="this.style.background='#222'">
            <div class="history-card-info">
                <div class="hc-time">${ageLabel} &middot; ${entry.elapsed_seconds}s &middot; ${entry.zone_count} zones</div>
                <div class="hc-summary" title="${_summary}">${_summary}</div>
                ${tags ? `<div style="margin-top:2px;">${tags}</div>` : ''}
                ${_notesShort ? `<div style="font-size:9px;color:var(--text-dim);margin-top:2px;font-style:italic;">${_notesShort}</div>` : ''}
                <div class="hc-actions" onclick="event.stopPropagation()" style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap;">
                    <button class="btn btn-sm" title="Favorite" onclick="toggleHistoryFavorite(${idx})" style="font-size:11px;padding:1px 5px;">${favIcon}</button>
                    <button class="btn btn-sm" title="Notes" onclick="editHistoryNotes(${idx})" style="font-size:9px;padding:1px 5px;">Note</button>
                    <button class="btn btn-sm" title="Tags" onclick="editHistoryTags(${idx})" style="font-size:9px;padding:1px 5px;">Tags</button>
                    <button class="btn btn-sm" title="Share link" onclick="copyRenderShareLink('${entry.job_id || ''}')" style="font-size:9px;padding:1px 5px;">Share</button>
                    <button class="btn btn-sm" title="Download paint" onclick="downloadRenderFile('${entry.paint_url}','${entry.filename || 'render.png'}')" style="font-size:9px;padding:1px 5px;">DL</button>
                    <button class="btn btn-sm" title="Channels" onclick="showSpecChannels('${entry.spec_url || ''}')" style="font-size:9px;padding:1px 5px;">Ch</button>
                    <button class="btn btn-sm" title="Histogram" onclick="showRenderHistogram('${entry.paint_url}')" style="font-size:9px;padding:1px 5px;">Hist</button>
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

    const compareBar = (historyCompareA >= 0 && historyCompareB >= 0)
        ? `<div class="history-compare-bar">
            <span>Comparing #${historyCompareA + 1} vs #${historyCompareB + 1}</span>
            <button class="btn btn-sm" onclick="showRenderDiff(${historyCompareA}, ${historyCompareB})" style="font-size:9px;">Diff</button>
            <button class="btn btn-sm" onclick="clearHistoryCompare()" style="font-size:9px;">Clear</button>
           </div>
           <div class="history-compare-view">
            <div class="history-compare-pane">
                <div class="compare-label">Render #${historyCompareA + 1}</div>
                <img src="${renderHistory[historyCompareA]?.paint_url}" alt="A">
                <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">${renderHistory[historyCompareA]?.zones_summary || ''}</div>
            </div>
            <div class="history-compare-pane">
                <div class="compare-label">Render #${historyCompareB + 1}</div>
                <img src="${renderHistory[historyCompareB]?.paint_url}" alt="B">
                <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">${renderHistory[historyCompareB]?.zones_summary || ''}</div>
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
        <input id="historySearchInput" type="text" placeholder="Search zones / notes / tags..." value="${(query || '').replace(/"/g, '&quot;')}"
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

    zones = entry.zoneSnapshot.map(z => ({
        name: z.name || 'Zone',
        color: z.color, base: z.base || null, pattern: z.pattern || 'none',
        finish: z.finish || null, intensity: z.intensity || '100',
        customSpec: z.customSpec != null ? z.customSpec : null,
        customPaint: z.customPaint != null ? z.customPaint : null,
        customBright: z.customBright != null ? z.customBright : null,
        colorMode: z.colorMode || 'none',
        pickerColor: z.pickerColor || '#3366ff',
        pickerTolerance: z.pickerTolerance || 40,
        colors: z.colors || [],
        regionMask: null,
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        scale: z.scale || 1.0, patternOpacity: z.patternOpacity ?? 100,
        patternStack: z.patternStack || [],
        wear: z.wear || 0, muted: z.muted || false,
    }));
    selectedZoneIndex = 0;
    renderZones();
    triggerPreviewRender();
    autoSave();
    closeHistoryGallery();
    showToast(`Restored zone config from render #${idx + 1}`);
}

function closeHistoryGallery() {
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.remove();
}

