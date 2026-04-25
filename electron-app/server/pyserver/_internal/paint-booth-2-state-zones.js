// ============================================================
// PAINT-BOOTH-2-STATE-ZONES.JS - State, init, zones UI, config
// ============================================================
// Purpose: App state (zones, selectedZoneIndex), init(), zone list/detail rendering,
//          zone actions & setters, favorites, finish library UI, config, script gen.
// Deps:    paint-booth-1-data.js (BASES, PATTERNS, MONOLITHICS, INTENSITY_VALUES, etc.).
// Edit:    Zone UI/setters → renderZones, renderZoneDetail, setZoneBase, setZoneIntensity, …
//          Undo → pushZoneUndo, zoneUndoStack. Config → load_config, autoSave.
// See:     PROJECT_STRUCTURE.md in this folder.
// ============================================================

// Cache-bust: new value every page load so hard reload fetches fresh swatches (avoids 24h browser cache)
if (typeof window !== 'undefined') window._SHOKKER_SWATCH_V = Date.now();

/** Clear server swatch cache and reload all thumbnails. Use after rebuilding thumbnails or when previews look wrong. */
async function refreshThumbnails() {
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    try {
        const r = await fetch(base + '/api/clear-cache', { method: 'POST', mode: 'cors' }).catch(() => fetch(base + '/api/clear-cache', { method: 'GET', mode: 'cors' }));
        if (r && r.ok) { /* cache cleared */ }
    } catch (e) { /* ignore if server unreachable */ }
    const newV = Date.now();
    if (typeof window !== 'undefined') window._SHOKKER_SWATCH_V = newV;
    // Force every visible swatch img to refetch (picker + zone list)
    try {
        document.querySelectorAll('img[src*="/api/swatch/"], img[data-swatch-url*="/api/swatch/"]').forEach(function (img) {
            const currentUrl = img.getAttribute('data-swatch-url') || img.getAttribute('src') || '';
            if (!currentUrl) return;
            let u = currentUrl.replace(/\bv=\d+\b/, 'v=' + newV);
            if (u.indexOf('nocache=') === -1) u += (u.indexOf('?') >= 0 ? '&' : '?') + 'nocache=1';
            if (img.getAttribute('data-swatch-url')) img.setAttribute('data-swatch-url', u);
            if (img.getAttribute('src')) img.src = u;
        });
    } catch (_) { /* ignore */ }
    if (typeof _installSwatchPopupLazyLoader === 'function') _installSwatchPopupLazyLoader();
    renderZones();
    if (typeof renderZoneDetail === 'function' && selectedZoneIndex >= 0 && selectedZoneIndex < zones.length) renderZoneDetail(selectedZoneIndex);
    if (typeof showToast === 'function') showToast('Thumbnails refreshed - cache cleared. Swatches will reload.');
    if (typeof checkThumbnailStatus === 'function') checkThumbnailStatus();
}

/** Call /api/thumbnail-status and show a dismissible banner if thumbnails are missing or dir empty. */
async function checkThumbnailStatus() {
    const banner = document.getElementById('thumbnailWarningBanner');
    // Alpha UX: hide this dev-only warning entirely.
    if (banner) banner.style.display = 'none';
}

// ===== STATE =====
let zones = [];
let selectedZoneIndex = 0;
/** 'none' | 'pattern' | 'second_base' | 'third_base' - which layer to position by dragging on the map (GIMP/PS-style) */
let placementLayer = 'none';
let lastRenderedZoneDetailIndex = -1; // used to preserve scroll when re-rendering same zone
let categoryCollapsed = {};
let importedSpecMapPath = null;  // Path to imported spec map TGA (merge mode = "Zone 0")

// ===== SIMPLE / ADVANCED MODE =====
let _uiMode = localStorage.getItem('shokker_ui_mode') || 'advanced';
window._uiMode = _uiMode;

// Apply saved mode on load
if (_uiMode === 'simple') {
    document.body.classList.add('simple-mode');
}

// Update pill toggle visual state
function _updateModeToggleUI() {
    const toggle = document.getElementById('ui-mode-toggle');
    if (!toggle) return;
    toggle.querySelectorAll('.ui-mode-option').forEach(function(opt) {
        opt.classList.toggle('active', opt.getAttribute('data-mode') === _uiMode);
    });
}

// Restore toggle visual on load
requestAnimationFrame(_updateModeToggleUI);

window.toggleUIMode = function() {
    _uiMode = _uiMode === 'advanced' ? 'simple' : 'advanced';
    window._uiMode = _uiMode;
    localStorage.setItem('shokker_ui_mode', _uiMode);
    document.body.classList.toggle('simple-mode', _uiMode === 'simple');
    // Legacy compat: keep easy-mode in sync
    document.body.classList.toggle('easy-mode', _uiMode === 'simple');
    _updateModeToggleUI();
    renderZones();
};

// Legacy support: toggleEasyMode maps to toggleUIMode
window.toggleEasyMode = window.toggleUIMode;
let easyMode = _uiMode === 'simple';
window.easyMode = easyMode;

// ===== UI SCALE =====
let _uiScale = parseFloat(localStorage.getItem('shokker_ui_scale') || '1.0');
if (_uiScale !== 1.0) document.body.style.zoom = _uiScale;

window.setUIScale = function(direction) {
    // direction: +1 = zoom in, -1 = zoom out, 0 = reset
    const steps = [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4, 1.5];
    if (direction === 0) {
        _uiScale = 1.0;
    } else {
        const currentIdx = steps.indexOf(_uiScale);
        const idx = currentIdx >= 0 ? currentIdx : steps.findIndex(s => s >= _uiScale);
        const newIdx = Math.max(0, Math.min(steps.length - 1, (idx >= 0 ? idx : 6) + direction));
        _uiScale = steps[newIdx];
    }
    document.body.style.zoom = _uiScale;
    localStorage.setItem('shokker_ui_scale', String(_uiScale));
    const label = document.getElementById('uiScaleLabel');
    if (label) label.textContent = Math.round(_uiScale * 100) + '%';
};

// Keyboard shortcuts for zoom: Ctrl+Plus, Ctrl+Minus, Ctrl+0 (reset)
// SESSION ROUTER: bail on defaultPrevented so transform/master listeners win first.
document.addEventListener('keydown', function(e) {
    if (e.defaultPrevented) return;
    if (e.ctrlKey && (e.key === '=' || e.key === '+')) { e.preventDefault(); setUIScale(1); }
    else if (e.ctrlKey && e.key === '-') { e.preventDefault(); setUIScale(-1); }
    else if (e.ctrlKey && e.key === '0') { e.preventDefault(); setUIScale(0); }
});

// Update label on load
requestAnimationFrame(() => {
    const label = document.getElementById('uiScaleLabel');
    if (label) label.textContent = Math.round(_uiScale * 100) + '%';
});

/** When non-null, the overlay "From special" picker for this zone+layer is expanded (big grid). Clear on select. */
let _overlaySpecialPickerExpanded = null; // { zoneIndex: number, layer: 'second'|'third'|'fourth'|'fifth' } | null

function toggleOverlaySpecialPicker(zoneIndex, layer) {
    if (_overlaySpecialPickerExpanded && _overlaySpecialPickerExpanded.zoneIndex === zoneIndex && _overlaySpecialPickerExpanded.layer === layer) {
        _overlaySpecialPickerExpanded = null;
    } else {
        _overlaySpecialPickerExpanded = { zoneIndex, layer };
    }
    if (typeof renderZoneDetail === 'function') renderZoneDetail(zoneIndex);
}

/** Clear the imported spec canvas. Next render will use default spec (no background layer). */
function clearImportedSpec() {
    // 2026-04-19 Hennig polish P3: don't run a destructive-looking action
    // and show "Spec cleared" toast when there was nothing to clear.
    if (!importedSpecMapPath) {
        if (typeof showToast === 'function') showToast('Nothing to clear — no spec map is loaded');
        return;
    }
    // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W10a): destructive without confirm.
    // A SHOKK-loaded spec is expensive to re-import — guard with a confirm.
    if (typeof confirm === 'function' &&
        !confirm('Clear the imported spec map? You will need to re-import or re-load from SHOKK to restore it.')) {
        return;
    }
    importedSpecMapPath = null;
    try { if (typeof window !== 'undefined') window.importedSpecMapPath = null; } catch (e) {}
    const specStatus = document.getElementById('importSpecMapStatus');
    if (specStatus) { specStatus.textContent = 'No spec map — zones render on default base'; specStatus.style.color = ''; }
    const clearBtn = document.getElementById('btnClearSpecMap');
    if (clearBtn) clearBtn.disabled = true;
    const specBanner = document.getElementById('specFromShokkBanner');
    if (specBanner) specBanner.style.display = 'none';
    const specChip = document.getElementById('shokkSpecStateChip');
    if (specChip) {
        specChip.textContent = 'SPEC: none';
        specChip.style.color = 'var(--text-dim)';
        specChip.style.borderColor = 'var(--border)';
        specChip.style.background = 'rgba(255,255,255,0.03)';
    }
    renderZones();
    // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W10b): silent-stale.
    // Sister clearImportedSpecMap calls triggerPreviewRender — this one didn't.
    // Painter clicked Clear → status flipped but car kept rendering w/ old spec.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast('Spec cleared — zones render on default base');
}

// Scale slider: 5% steps. Pattern scale 0.10–4.0 (slider 10–400); base scale 1.0–10.0 (100–1000); overlay noise 0.10–5.0 (10–500).
const SCALE_PATTERN_MIN = 0.10, SCALE_PATTERN_MAX = 4.0, SCALE_STEP = 0.05;
const SCALE_BASE_MIN = 1.0, SCALE_BASE_MAX = 10.0;
const SCALE_OVERLAY_MIN = 0.10, SCALE_OVERLAY_MAX = 5.0;
function roundToStep(val, step) { return Math.round(val / step) * step; }

// Render History
const renderHistory = [];
const MAX_RENDER_HISTORY = 20;

// Multi-color per zone: each zone can have a `colors` array
// of {color_rgb: [R,G,B], tolerance: N, hex: "#RRGGBB"} objects
// This allows zones like "Car Number" to capture gold + blue + red
// All matched pixels get the SAME finish applied uniformly

// Spatial regions: each zone can have a `regionMask` (Uint8Array)
// that marks which pixels belong to this zone by position (not color).
// Great for numbers, sponsors, artwork where colors overlap body paint.
// regionMask is canvas-resolution: 1 = pixel belongs, 0 = doesn't

let canvasMode = 'eyedropper'; // 'eyedropper' | 'brush' | 'rect' | 'erase' | 'wand' | 'spatial-include' | 'spatial-exclude'
let spatialBrushRadius = 15; // Radius for spatial include/exclude brush
let isDrawing = false;
let rectStart = null; // {x, y} for rectangle start point
let paintImageData = null;
let lastEyedropperColor = null;

// Undo stack for draw region strokes
// Each entry: { zoneIndex, prevMask (Uint8Array snapshot or null) }
const undoStack = [];
let redoStack = []; // Draw/mask redo (cleared on new draw action)
const MAX_UNDO = 30;

// Zone undo/redo for property changes (base, pattern, intensity, add/delete, etc.)
const zoneUndoStack = [];   // Each entry: { label, timestamp, snapshot }
const zoneRedoStack = [];   // Each entry: { label, timestamp, snapshot }
const MAX_ZONE_UNDO = 50;
let undoHistoryPointer = -1; // Current position in history for visual highlighting

function _newZoneId() {
    if (typeof crypto !== 'undefined' && crypto && typeof crypto.randomUUID === 'function') {
        return 'zone_' + crypto.randomUUID();
    }
    return 'zone_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
}

function _cloneUint8ArrayLike(value) {
    if (!value) return null;
    if (value instanceof Uint8Array) return new Uint8Array(value);
    if (Array.isArray(value)) return new Uint8Array(value);
    if (typeof value === 'object') {
        const numericKeys = Object.keys(value)
            .filter(function (k) { return /^\d+$/.test(k); })
            .sort(function (a, b) { return Number(a) - Number(b); });
        if (numericKeys.length) {
            return new Uint8Array(numericKeys.map(function (k) { return value[k] || 0; }));
        }
    }
    return null;
}

function _clonePatternStrengthMap(map) {
    if (!map || !map.data || !map.width || !map.height) return null;
    const data = _cloneUint8ArrayLike(map.data);
    if (!data) return null;
    return {
        width: map.width,
        height: map.height,
        data: data,
    };
}

function _cloneZoneState(zone, options) {
    const opts = options || {};
    const baseClone = JSON.parse(JSON.stringify({
        ...zone,
        regionMask: null,
        spatialMask: null,
        patternStrengthMap: null,
    }));
    baseClone.id = (opts.preserveId === false || baseClone.id == null || baseClone.id === '')
        ? _newZoneId()
        : baseClone.id;
    baseClone.regionMask = opts.includeRegionMask ? _cloneUint8ArrayLike(zone && zone.regionMask) : null;
    baseClone.spatialMask = opts.includeSpatialMask ? _cloneUint8ArrayLike(zone && zone.spatialMask) : null;
    if (opts.includePatternStrengthMap !== false) {
        baseClone.patternStrengthMap = _clonePatternStrengthMap(zone && zone.patternStrengthMap);
    }
    return baseClone;
}

function _ensureZoneShape(zone, options) {
    const opts = options || {};
    const next = _cloneZoneState(zone || {}, {
        preserveId: true,
        includeRegionMask: !!opts.includeRegionMask,
        includeSpatialMask: !!opts.includeSpatialMask,
        includePatternStrengthMap: true,
    });
    if (next.id == null || next.id === '') next.id = _newZoneId();
    return next;
}

function _ensureAllZonesHaveIds(zoneList) {
    if (!Array.isArray(zoneList)) return;
    zoneList.forEach(function (z) {
        if (z && (z.id == null || z.id === '')) z.id = _newZoneId();
    });
}

function _hasAnyMaskPixels(mask) {
    if (!mask) return false;
    try {
        if (typeof mask.some === 'function') return mask.some(function(v) { return v > 0; });
        if (Array.isArray(mask) || typeof mask.length === 'number') {
            for (var i = 0; i < mask.length; i++) if (mask[i] > 0) return true;
        }
    } catch (_) {}
    return false;
}

function _zoneHasAuthoredLayerWork(zone) {
    if (!zone) return false;
    if (zone.sourceLayer) return true;
    var stackKeys = [
        'patternStack', 'specPatternStack', 'overlaySpecPatternStack',
        'thirdOverlaySpecPatternStack', 'fourthOverlaySpecPatternStack',
        'fifthOverlaySpecPatternStack',
    ];
    for (var i = 0; i < stackKeys.length; i++) {
        if (Array.isArray(zone[stackKeys[i]]) && zone[stackKeys[i]].length > 0) return true;
    }
    var overlayKeys = ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'];
    for (var j = 0; j < overlayKeys.length; j++) {
        if (zone[overlayKeys[j]]) return true;
    }
    return false;
}

function _isZone9MatteCarbonZombie(zone, index) {
    if (!zone) return false;
    var name = String(zone.name || '').trim().toLowerCase();
    var looksLikeZone9 = index === 8 || name === 'zone 9' || name === 'open zone 9' || /\bzone\s*9\b/.test(name);
    if (!looksLikeZone9) return false;
    if (zone.base !== 'matte' || zone.pattern !== 'carbon_fiber') return false;
    if (zone.finish) return false;
    if (_hasAnyMaskPixels(zone.regionMask) || _hasAnyMaskPixels(zone.spatialMask)) return false;
    if (_zoneHasAuthoredLayerWork(zone)) return false;
    return true;
}

function _sanitizeZone9MatteCarbonZombie(zone, index, source) {
    if (!_isZone9MatteCarbonZombie(zone, index)) return false;
    zone.base = null;
    zone.pattern = 'none';
    zone.finish = null;
    if (zone.color == null || zone.color === 'dark') {
        zone.color = null;
        zone.colorMode = 'none';
    }
    zone.hint = 'Empty by default. Legacy matte carbon auto-fill was removed.';
    try {
        console.warn('[SPB][zone-sanitize] stripped legacy Zone 9 matte/carbon zombie from ' + (source || 'zone state'));
    } catch (_) {}
    return true;
}

function _sanitizeZonesInPlace(zoneList, source) {
    if (!Array.isArray(zoneList)) return 0;
    var fixed = 0;
    zoneList.forEach(function(zone, index) {
        if (_sanitizeZone9MatteCarbonZombie(zone, index, source)) fixed++;
    });
    return fixed;
}
if (typeof window !== 'undefined') {
    window._sanitizeZonesInPlace = _sanitizeZonesInPlace;
    window._isZone9MatteCarbonZombie = _isZone9MatteCarbonZombie;
}

let undoActiveDragTimer = null;
function pushZoneUndo(label, isDrag = false) {
    if (isDrag && undoActiveDragTimer) {
        // Extend the timer and skip pushing a new state
        clearTimeout(undoActiveDragTimer);
        undoActiveDragTimer = setTimeout(() => { undoActiveDragTimer = null; }, 500);
        return;
    }
    // BUG #75 (Slaughter, HIGH): invalidate ALL redo stacks on new action, not
    // just zoneRedoStack. Stale entries in _layerRedoStack / _pixelRedoStack /
    // redoStack would silently fire on the next Ctrl+Y and destroy work.
    if (typeof window !== 'undefined' && typeof window._clearAllRedos === 'function') window._clearAllRedos();
    else zoneRedoStack.length = 0;
    const snapshot = zones.map(function (z) {
        // Region masks are intentionally omitted here because they are large and
        // have dedicated brush undo handling. Spatial masks and strength maps
        // must survive zone undo/redo because they're part of the authored state.
        return _cloneZoneState(z, {
            preserveId: true,
            includeRegionMask: false,
            includeSpatialMask: true,
            includePatternStrengthMap: true,
        });
    });

    // Capture richer context: which zone was affected, what property changed
    const context = {
        zoneIndex: selectedZoneIndex,
        zoneName: (zones[selectedZoneIndex] && zones[selectedZoneIndex].name) || 'Unknown',
        zoneCount: zones.length,
    };

    zoneUndoStack.push({
        label: label || 'Change',
        timestamp: Date.now(),
        snapshot: snapshot,
        context: context,
    });
    if (zoneUndoStack.length > MAX_ZONE_UNDO) zoneUndoStack.shift();
    undoHistoryPointer = zoneUndoStack.length; // Points past top = current state
    renderUndoHistoryPanel();
    if (typeof window !== 'undefined' && typeof window._recordUndoAction === 'function') {
        window._recordUndoAction('zone-config');
    }

    if (isDrag) {
        undoActiveDragTimer = setTimeout(() => { undoActiveDragTimer = null; }, 500);
    }
}

function undoZoneChange() {
    if (zoneUndoStack.length === 0) { showToast('Nothing to undo — no zone changes recorded yet'); return false; }
    const currentSnapshot = zones.map(function (z) {
        return _cloneZoneState(z, {
            preserveId: true,
            includeRegionMask: false,
            includeSpatialMask: true,
            includePatternStrengthMap: true,
        });
    });
    const entry = zoneUndoStack.pop();
    zoneRedoStack.push({
        label: entry.label,
        timestamp: Date.now(),
        snapshot: currentSnapshot,
    });
    // BUG #62: Restore masks by zone id (NOT positional index). Positional index
    // corrupts masks whenever zones were added/deleted/reordered between snapshots.
    const masksById = new Map();
    for (const z of zones) { if (z && z.id != null) masksById.set(z.id, z.regionMask); }
    zones.length = 0;
    entry.snapshot.forEach((z) => {
        const restored = _ensureZoneShape(z, { includeRegionMask: false, includeSpatialMask: true });
        restored.regionMask = (restored && restored.id != null && masksById.has(restored.id))
            ? _cloneUint8ArrayLike(masksById.get(restored.id))
            : null;
        zones.push(restored);
    });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = zoneUndoStack.length;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Undo: ' + entry.label);
    return true;
}

function redoZoneChange() {
    if (zoneRedoStack.length === 0) { showToast('Nothing to redo — make a change and undo it first'); return false; }
    const currentSnapshot = zones.map(function (z) {
        return _cloneZoneState(z, {
            preserveId: true,
            includeRegionMask: false,
            includeSpatialMask: true,
            includePatternStrengthMap: true,
        });
    });
    const entry = zoneRedoStack.pop();
    zoneUndoStack.push({
        label: entry.label,
        timestamp: Date.now(),
        snapshot: currentSnapshot,
    });
    // BUG #62: restore masks by id (see undoZoneChange for full rationale).
    const masksById = new Map();
    for (const z of zones) { if (z && z.id != null) masksById.set(z.id, z.regionMask); }
    zones.length = 0;
    entry.snapshot.forEach((z) => {
        const restored = _ensureZoneShape(z, { includeRegionMask: false, includeSpatialMask: true });
        restored.regionMask = (restored && restored.id != null && masksById.has(restored.id))
            ? _cloneUint8ArrayLike(masksById.get(restored.id))
            : null;
        zones.push(restored);
    });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = zoneUndoStack.length;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Redo: ' + entry.label);
    return true;
}

function jumpToUndoState(index) {
    // Jump to a specific point in the undo stack
    // index 0 = oldest state, zoneUndoStack.length = current (no undo applied)
    if (index < 0 || index >= zoneUndoStack.length) return;
    const entry = zoneUndoStack[index];
    // Save current state to redo
    const currentSnapshot = zones.map(function (z) {
        return _cloneZoneState(z, {
            preserveId: true,
            includeRegionMask: false,
            includeSpatialMask: true,
            includePatternStrengthMap: true,
        });
    });
    zoneRedoStack.push({ label: 'Jump', timestamp: Date.now(), snapshot: currentSnapshot });
    // Restore — BUG #62: lookup masks by id, not positional index.
    const masksById = new Map();
    for (const z of zones) { if (z && z.id != null) masksById.set(z.id, z.regionMask); }
    zones.length = 0;
    entry.snapshot.forEach((z) => {
        const restored = _ensureZoneShape(z, { includeRegionMask: false, includeSpatialMask: true });
        restored.regionMask = (restored && restored.id != null && masksById.has(restored.id))
            ? _cloneUint8ArrayLike(masksById.get(restored.id))
            : null;
        zones.push(restored);
    });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = index;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Jumped to: ' + entry.label);
}

function renderUndoHistoryPanel() {
    const list = document.getElementById('undoHistoryList');
    if (!list) return;
    const count = document.getElementById('undoHistoryCount');
    if (count) count.textContent = zoneUndoStack.length + ' actions';

    let html = '';
    if (zoneUndoStack.length === 0) {
        html = '<div style="color:var(--text-dim); font-size:10px; padding:8px; text-align:center;">No history yet. Make changes to see them here.</div>';
    } else {
        // Show newest first
        for (let i = zoneUndoStack.length - 1; i >= 0; i--) {
            const e = zoneUndoStack[i];
            const isActive = (i === undoHistoryPointer);
            const isCurrent = (i === zoneUndoStack.length - 1 && undoHistoryPointer >= zoneUndoStack.length);
            const dimmed = (i > undoHistoryPointer && undoHistoryPointer < zoneUndoStack.length);
            const timeAgo = formatTimeAgo(e.timestamp);
            const ctxInfo = e.context ? ' (Z' + (e.context.zoneIndex + 1) + ': ' + escapeHtml(e.context.zoneName) + ')' : '';
            html += `<div class="undo-history-item${isActive ? ' active' : ''}${dimmed ? ' dimmed' : ''}" onclick="jumpToUndoState(${i})" title="Click to restore this state${e.context ? ' | Zone: ' + e.context.zoneName : ''}">
                <span class="undo-history-label">${escapeHtml(e.label)}${ctxInfo}</span>
                <span class="undo-history-time">${timeAgo}</span>
            </div>`;
        }
        // Current state marker
        if (undoHistoryPointer >= zoneUndoStack.length) {
            html = `<div class="undo-history-item active" style="cursor:default;">
                <span class="undo-history-label" style="color:var(--accent-green);">Current State</span>
                <span class="undo-history-time">now</span>
            </div>` + html;
        }
    }
    list.innerHTML = html;
}

function formatTimeAgo(ts) {
    const diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 5) return 'just now';
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return Math.floor(diff / 3600) + 'h ago';
}

function toggleUndoHistoryPanel() {
    const panel = document.getElementById('undoHistoryPanel');
    if (!panel) return;
    const isOpen = panel.classList.contains('open');
    if (isOpen) {
        panel.classList.remove('open');
    } else {
        panel.classList.add('open');
        renderUndoHistoryPanel();
    }
}

function clearUndoHistory() {
    if (!confirm('Clear ALL undo history (zone, region, pixel, and layer stacks)? This cannot be undone.')) return;
    // WIN #7 (TWENTY WINS shift): pre-fix, this only cleared the zone stacks
    // but left _pixelUndoStack / _pixelRedoStack / _layerUndoStack / _layerRedoStack
    // / undoStack / redoStack populated. Painter expected "all undo history"
    // to mean ALL stacks. Now uniformly clears every stack the app maintains.
    zoneUndoStack.length = 0;
    zoneRedoStack.length = 0;
    if (typeof undoStack !== 'undefined' && undoStack) undoStack.length = 0;
    if (typeof window !== 'undefined') {
        try { if (window._pixelUndoStack) window._pixelUndoStack.length = 0; } catch (_) {}
        try { if (window._pixelRedoStack) window._pixelRedoStack.length = 0; } catch (_) {}
        try { if (window._layerUndoStack) window._layerUndoStack.length = 0; } catch (_) {}
        try { if (window._layerRedoStack) window._layerRedoStack.length = 0; } catch (_) {}
        try { if (window.redoStack) window.redoStack.length = 0; } catch (_) {}
        // Also clear via _clearAllRedos for the canvas-scoped redo stacks
        // (zone/pixel/layer/region) that may not be on window.
        try { if (typeof window._clearAllRedos === 'function') window._clearAllRedos(); } catch (_) {}
    }
    undoHistoryPointer = -1;
    renderUndoHistoryPanel();
    showToast('Cleared all undo history (zone + region + pixel + layer stacks)');
}

// Escape: cancel active canvas operation (lasso / rect drag) so Escape feels like Photoshop/GIMP
window.cancelCanvasOperation = function () {
    const placementDragActive = (typeof hasActiveManualPlacementDrag === 'function' && hasActiveManualPlacementDrag())
        || (typeof window !== 'undefined' && !!window._manualPlacementDragState);
    if (placementDragActive && typeof cancelManualPlacementSession === 'function' && cancelManualPlacementSession(true)) {
        showToast('Placement drag cancelled');
        return true;
    }
    if (typeof cancelSelectionMove === 'function' && cancelSelectionMove(true)) {
        showToast('Selection move cancelled');
        return true;
    }
    if (typeof cancelManualPlacementSession === 'function' && cancelManualPlacementSession(true)) {
        showToast('Placement editing closed');
        return true;
    }
    if (typeof cancelLasso === 'function' && cancelLasso()) {
        showToast('Lasso cancelled');
        return true;
    }
    if (isDrawing && rectStart !== null) {
        rectStart = null;
        isDrawing = false;
        if (typeof hideRectPreview === 'function') hideRectPreview();
        renderRegionOverlay();
        showToast('Rect cancelled');
        return true;
    }
    return false;
};

function _isTextEntryTargetForGlobalUndo(target) {
    if (!target) return false;
    if (target.isContentEditable) return true;
    const tag = String(target.tagName || '').toLowerCase();
    if (tag === 'textarea') return true;
    if (tag !== 'input') return false;
    const type = String(target.type || '').toLowerCase();
    return !type || [
        'text', 'search', 'email', 'url', 'tel', 'password', 'number',
        'date', 'datetime-local', 'month', 'time', 'week'
    ].includes(type);
}

// Keyboard shortcuts: Ctrl+Z = undo, Ctrl+Y / Ctrl+Shift+Z = redo
// UNIFIED: prefers draw/mask undo (undoStack) over zone history undo (zoneUndoStack)
document.addEventListener('keydown', function (e) {
    if (e.defaultPrevented) return;
    if (e.repeat) return;
    // Let true text-entry fields keep native undo, but still honor Ctrl+Z when
    // focus is sitting on toolbar sliders / dropdowns / buttons.
    if (_isTextEntryTargetForGlobalUndo(e.target)) return;
    const placementActive = typeof placementLayer !== 'undefined' && placementLayer && placementLayer !== 'none';
    const placementDragActive = (typeof hasActiveManualPlacementDrag === 'function' && hasActiveManualPlacementDrag())
        || (typeof window !== 'undefined' && !!window._manualPlacementDragState);

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        // Transform sessions own Ctrl+Z. Without this guard, the older global
        // zone/layer undo handler can consume the shortcut before the
        // transform-specific handler gets to cancel the active box, which
        // makes free transform feel randomly "immune" to undo.
        if (typeof freeTransformState !== 'undefined' && freeTransformState &&
            typeof cancelActiveTransformSession === 'function') {
            e.preventDefault();
            cancelActiveTransformSession();
            return;
        }
        if (placementDragActive) {
            e.preventDefault();
            if (typeof window !== 'undefined'
                    && typeof window._cancelActivePlacementDrag === 'function'
                    && window._cancelActivePlacementDrag()) {
                return;
            }
            if (typeof renderZones === 'function') renderZones();
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();
            return;
        }
        if (typeof cancelSelectionMove === 'function' && cancelSelectionMove()) {
            e.preventDefault();
            return;
        }
        e.preventDefault();
        // Always call undoDrawStroke — it checks pixel stack first, then zone mask stack internally
        if (typeof undoDrawStroke === 'function') {
            undoDrawStroke();
        } else {
            undoZoneChange();
        }
    } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        if (typeof freeTransformState !== 'undefined' && freeTransformState) {
            e.preventDefault();
            return;
        }
        if (placementDragActive) {
            e.preventDefault();
            if (typeof showToast === 'function') showToast('Finish or cancel placement drag before redo');
            return;
        }
        e.preventDefault();
        if (typeof redoDrawStroke === 'function') {
            redoDrawStroke();
        } else {
            redoZoneChange();
        }
    } else if (!e.ctrlKey && !e.metaKey && !e.altKey && e.key === 'Enter') {
        if (placementActive) {
            e.preventDefault();
            if (typeof finishManualPlacementSession === 'function') finishManualPlacementSession();
        }
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'd' && !e.shiftKey) {
        // Ctrl+D = Deselect (clear zone mask)
        e.preventDefault();
        if (typeof freeTransformState !== 'undefined' && freeTransformState) {
            return;
        }
        if (placementDragActive) {
            return;
        }
        if (typeof cancelSelectionMove === 'function' && cancelSelectionMove(true)) {
            if (typeof deselectRegion === 'function') deselectRegion();
            return;
        }
        if (typeof deselectRegion === 'function') deselectRegion();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'a' && !e.shiftKey) {
        // Ctrl+A = Select all pixels in current zone
        e.preventDefault();
        if (typeof _ctxSelectAll === 'function') _ctxSelectAll();
    } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'I') {
        // Ctrl+Shift+I = Invert selection
        e.preventDefault();
        if (typeof invertRegionMask === 'function') invertRegionMask();
    } else if (e.altKey && e.key === 'Backspace') {
        e.preventDefault();
        if (typeof fillSelectionWithColor === 'function') fillSelectionWithColor(false);
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'Backspace') {
        e.preventDefault();
        if (typeof fillSelectionWithColor === 'function') fillSelectionWithColor(true);
    } else if (e.key === 'Delete' && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        const _dZone = zones[selectedZoneIndex];
        if (_dZone && _dZone.regionMask && _dZone.regionMask.some(v => v > 0)) {
            e.preventDefault();
            if (typeof deleteSelection === 'function') deleteSelection();
        }
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'c' && !e.shiftKey) {
        // Ctrl+C = Copy selected pixels
        e.preventDefault();
        if (typeof copySelection === 'function') copySelection();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'x' && !e.shiftKey) {
        // Ctrl+X = Cut selected pixels
        e.preventDefault();
        if (typeof cutSelection === 'function') cutSelection();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'v' && !e.shiftKey) {
        // Ctrl+V = Paste as new layer
        e.preventDefault();
        if (typeof pasteAsLayer === 'function') pasteAsLayer();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'j' && !e.shiftKey) {
        // Ctrl+J = New Layer via Copy (Photoshop standard)
        e.preventDefault();
        if (typeof newLayerViaCopy === 'function') newLayerViaCopy();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'e' && !e.shiftKey) {
        // Ctrl+E = Merge layer down
        e.preventDefault();
        const _selLayer = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
        if (_selLayer && typeof mergeLayerDown === 'function') mergeLayerDown(_selLayer.id);
    } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'E') {
        // Ctrl+Shift+E = Flatten all layers
        e.preventDefault();
        if (typeof flattenAllLayers === 'function') flattenAllLayers();
    } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
        // Ctrl+Shift+N = New blank layer
        e.preventDefault();
        if (typeof addBlankLayer === 'function') addBlankLayer();
    }
});

// Zone colors for region overlay visualization
const ZONE_OVERLAY_COLORS = [
    [255, 50, 50, 200],    // Red
    [50, 255, 50, 200],    // Green
    [50, 100, 255, 200],   // Blue
    [255, 255, 50, 200],   // Yellow
    [255, 50, 255, 200],   // Magenta
    [50, 255, 255, 200],   // Cyan
    [255, 150, 50, 200],   // Orange
    [150, 50, 255, 200],   // Purple
    [255, 100, 100, 200],  // Salmon
    [100, 255, 200, 200],  // Mint
    [200, 150, 255, 200],  // Lavender
    [255, 200, 100, 200],  // Peach
];

// ===== INITIALIZATION =====
function init() {
    // Start with 4 body color slots + number + sponsors + dark + remainder
    // User deletes body color slots they don't need
    zones = [
        {
            name: "Body Color 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#3366ff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Pick Color mode - click your PRIMARY body color on the paint"
        },
        {
            name: "Body Color 2", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffcc00", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Click your SECOND body color (delete this zone if single-color car)"
        },
        {
            name: "Body Color 3", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#cc2222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Third body color if needed (delete if not)"
        },
        {
            name: "Body Color 4", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#22cc22", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Fourth body color if needed (delete if not)"
        },
        {
            name: "Car Number", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffaa00", pickerTolerance: 35, colors: [], regionMask: null,
            hint: "Magic Wand each number color, or Draw Region/Rectangle manually."
        },
        {
            name: "Custom Art 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ff3366", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Magic Wand to click artwork or Draw Region manually. Delete if not needed."
        },
        {
            name: "Custom Art 2", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#33ccff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Another art element - Magic Wand + Shift+click. Delete if not needed."
        },
        {
            name: "Sponsors / Logos", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#ffffff", pickerTolerance: 30, colors: [], regionMask: null,
            hint: "Draw regions over sponsor areas, or pick a color if sponsors share one color"
        },
        {
            name: "Open Zone 9", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#777777", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Empty by default. Use this only if you need another custom zone before Remaining."
        },
        {
            name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", finish: null, intensity: "50", colorMode: "special", pickerColor: "#888888", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Safety net - catches any pixels not claimed by zones above"
        },
    ];
    selectedZoneIndex = 0;
    CATEGORIES.forEach(c => categoryCollapsed[c] = false);
    renderZones();
    if (typeof renderZoneDetail === 'function' && zones.length > 0) renderZoneDetail(0);
    renderFinishLibrary();
    updateOutputPath();
    refreshTemplateDropdown();
    refreshComboDropdown();
}

// ===== ZONE RENDERING =====
function renderZones() {
    closeSwatchPicker(); // Close any open swatch popup before re-rendering
    if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'renderZones');
    if (typeof autoSave === 'function') autoSave(); // Auto-save on every zone change
    if (typeof zones === 'undefined' || zones.length === 0) {
        if (typeof init === 'function') init();
    }
    const container = document.getElementById('zoneList');
    const countEl = document.getElementById('zoneCount');
    if (countEl) countEl.textContent = '(' + (zones ? zones.length : 0) + ')';
    if (!container) {
        if (typeof init === 'function' && (!zones || zones.length === 0)) init();
        if (!renderZones._zoneListRetry) {
            renderZones._zoneListRetry = true;
            setTimeout(function () { renderZones._zoneListRetry = false; renderZones(); }, 50);
        }
        return;
    }
    /* Force zone list area to be visible (fixes empty list when flex gives 0 height) */
    container.style.minHeight = '200px';
    container.style.display = 'block';
    container.style.overflowY = 'auto';
    const specmapContent = document.getElementById('specmapModeContent');
    if (specmapContent) {
        specmapContent.style.minHeight = '300px';
        specmapContent.style.display = 'flex';
        specmapContent.style.flexDirection = 'column';
    }
    let html = '';

    // ── EMPTY STATE GUIDE ────────────────────────────────────────────────
    if (zones.length === 0 && typeof getEmptyStateGuide === 'function') {
        container.innerHTML = getEmptyStateGuide();
        return;
    }

    // ── ZONE TOOLBAR (search + bulk + collapse) ──────────────────────────
    html += `<div class="zone-toolbar" style="display:flex;align-items:center;gap:6px;padding:4px 6px;margin-bottom:6px;background:rgba(0,0,0,0.25);border-radius:4px;flex-wrap:wrap;">
        <input id="zoneSearchInput" type="text" placeholder="Search zones (/)" oninput="setZoneSearchQuery(this.value)" value="${escapeHtml(typeof _zoneSearchQuery !== 'undefined' ? _zoneSearchQuery : '')}" title="Filter zones by name / finish / color">
        <button class="btn btn-sm" onclick="event.stopPropagation();collapseAllZones()" title="Collapse all zone cards" style="padding:2px 6px;font-size:9px;">\u25BC All</button>
        <button class="btn btn-sm" onclick="event.stopPropagation();expandAllZones()" title="Expand all zone cards" style="padding:2px 6px;font-size:9px;">\u25B2 All</button>
        <button class="btn btn-sm" onclick="event.stopPropagation();showCombinedWarnings()" title="Validate all zones (overlaps, missing finishes, performance)" style="padding:2px 6px;font-size:9px;border-color:#ff8c1a;color:#ff8c1a;">\u26A0 Check</button>
        <span style="flex:1;"></span>
        ${(typeof _bulkSelectedZones !== 'undefined' && _bulkSelectedZones.size > 0) ? `
        <span style="font-size:10px;color:#00ccff;">${_bulkSelectedZones.size} selected</span>
        <button class="btn btn-sm" onclick="event.stopPropagation();bulkMute()" title="Mute selected" style="padding:2px 6px;font-size:9px;">Mute</button>
        <button class="btn btn-sm" onclick="event.stopPropagation();bulkUnmute()" title="Unmute selected" style="padding:2px 6px;font-size:9px;">Unmute</button>
        <button class="btn btn-sm" onclick="event.stopPropagation();bulkDelete()" title="Delete selected" style="padding:2px 6px;font-size:9px;color:#ff5555;">Del</button>
        <button class="btn btn-sm" onclick="event.stopPropagation();clearBulkSelection()" title="Clear selection" style="padding:2px 6px;font-size:9px;">\u2715</button>` : ''}
    </div>`;

    // ── ZONE 0: SPEC CANVAS BANNER ───────────────────────────────────────
    // Shows when an imported spec map is active (from SHOKK or spec import). Renders ABOVE Zone 1 so user sees spec is loaded.
    if (importedSpecMapPath) {
        const specLabel = document.getElementById('importSpecMapStatus')?.innerText || document.getElementById('importSpecMapStatus')?.textContent || 'Imported spec';
        const fname = importedSpecMapPath.split('/').pop().split('\\').pop();
        html += `<div id="specCanvasBanner" class="zone-card" style="
            display:flex; align-items:center; gap:8px; padding:10px 12px; margin-bottom:8px;
            background: linear-gradient(135deg, rgba(0,200,80,0.15), rgba(0,150,200,0.08));
            border:1px solid rgba(0,200,80,0.5); border-radius:6px; font-size:11px; flex-shrink:0;">
            <span class="zone-number" style="background:var(--accent-green); color:#000; font-weight:800;">0</span>
            <span style="font-size:16px;">🎯</span>
            <div style="flex:1; min-width:0;">
                <div style="font-weight:800; color:var(--accent-green); font-size:11px; letter-spacing:0.5px;">✓ SPEC MAP · LAYER 0 (loaded)</div>
                <div style="color:var(--text-dim); font-size:9px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(specLabel)}">
                    ${escapeHtml(fname)} — zones paint on top
                </div>
            </div>
            <button onclick="event.stopPropagation(); clearImportedSpec()" class="btn btn-sm"
                style="padding:2px 6px; font-size:9px; border-color:var(--accent-red,#ff4444); color:var(--accent-red,#ff4444);"
                title="Remove imported spec canvas - zones will render on default spec">✕ Clear</button>
        </div>`;
    }
    try {
        zones.forEach((zone, i) => {
            const isSelected = i === selectedZoneIndex;
            const accordionClass = ' zone-card-collapsed' + (isSelected ? ' selected' : '');
            const stackCount = (zone.patternStack || []).filter(l => l.id && l.id !== 'none').length;
            const finishName = zone.finish
                ? (MONOLITHICS.find(m => m.id === zone.finish)?.name || BASES.find(b => b.id === zone.finish)?.name || zone.finish) +
                (zone.pattern && zone.pattern !== 'none' ? ' + ' + (PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern) : '')
                : zone.base
                    ? (BASES.find(b => b.id === zone.base)?.name || zone.base) +
                    (zone.pattern && zone.pattern !== 'none' ? ' + ' + (PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern) : '') +
                    (stackCount > 0 ? ` +${stackCount}` : '')
                    : '(not set)';
            const intensityName = zone.customSpec != null ? 'Custom' : (INTENSITY_OPTIONS.find(o => o.id === zone.intensity)?.name || zone.intensity || '');
            const summaryHtml = `<span class="zone-summary">${escapeHtml(finishName)}${intensityName ? ` <span class="finish-badge">${escapeHtml(intensityName)}</span>` : ''}</span>`;
            const colorStatus = getColorStatusText(zone);

            const zoneHint = zone.hint || '';

            // Determine zone dot color: use picked color if available, fall back to overlay color
            let dotColor;
            let dotTitle;
            if (zone.colorMode === 'picker' && zone.pickerColor) {
                dotColor = zone.pickerColor;
                dotTitle = `Zone color: ${zone.pickerColor}`;
            } else if (zone.colorMode === 'quick' && zone.color) {
                const qc = QUICK_COLORS.find(c => c.value === zone.color);
                dotColor = qc ? qc.bg : '#888';
                dotTitle = `Zone color: ${zone.color}`;
            } else if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
                const [r, g, b] = zone.colors[0].color_rgb || [128, 128, 128];
                dotColor = `rgb(${r},${g},${b})`;
                dotTitle = `Zone color: ${zone.colors.length} color(s)`;
            } else if (zone.colorMode === 'text' && zone.color) {
                // Try matching text color to a quick color, or use CSS color name
                const qc = QUICK_COLORS.find(c => String(zone.color).toLowerCase().includes(c.value));
                dotColor = qc ? qc.bg : '#888';
                dotTitle = `Zone color: "${zone.color}"`;
            } else if (zone.colorMode === 'special' && zone.color === 'remaining') {
                dotColor = '#555';
                dotTitle = 'Remainder (unclaimed pixels)';
            } else if (zone.colorMode === 'special' && zone.color === 'everything') {
                dotColor = 'linear-gradient(135deg, #888, #ccc)';
                dotTitle = 'Everything (all pixels)';
            } else if (zone.regionMask && zone.regionMask.some(v => v > 0)) {
                // Zone has a drawn region but no color - that's valid, region replaces color detection
                dotColor = '#cc88ff';
                dotTitle = 'Region-based zone (lasso/brush drawn)';
            } else {
                dotColor = 'NOCOLOR';
                dotTitle = 'No color selected \u2014 pick a color first';
            }

            // Region badge: show a purple indicator when zone has a drawn region
            const hasRegion = zone.regionMask && zone.regionMask.some(v => v > 0);
            const regionBadge = hasRegion
                ? `<span style="font-size:8px; color:#cc88ff; margin-left:2px; white-space:nowrap;" title="Region drawn (${zone.regionMask.reduce((s, v) => s + (v > 0 ? 1 : 0), 0).toLocaleString()} pixels)">🎯</span>`
                : '';

            const mutedClass = zone.muted ? ' zone-muted' : '';
            const _zoneStatusBadge = (typeof getZoneStatusBadgeHTML === 'function') ? getZoneStatusBadgeHTML(zone) : '';
            const _zoneDiagnostic = (typeof getZoneDiagnostic === 'function') ? getZoneDiagnostic(zone) : '';
            const _bulkSelectedClass = (typeof _bulkSelectedZones !== 'undefined' && _bulkSelectedZones.has(i)) ? ' zone-bulk-selected' : '';
            html += `<div class="zone-card${accordionClass}${mutedClass}${_bulkSelectedClass}" onclick="selectZone(${i})" id="zone-card-${i}"
            ondragover="zoneDragOver(event,${i})" ondragenter="zoneDragEnter(event,${i})" ondragleave="zoneDragLeave(event)" ondrop="zoneDrop(event,${i})" ondragend="zoneDragEnd(event)"
            title="${escapeHtml(_zoneDiagnostic)}">
            <div class="zone-card-header">
                <span class="zone-drag-handle" draggable="true" ondragstart="zoneDragStart(event,${i})" title="Drag to reorder">&#x2630;</span>
                <span class="zone-number">${i + 1}</span>
                ${_zoneStatusBadge}
                <span class="zone-overlay-dot${dotColor === 'NOCOLOR' ? ' no-color' : ''}" style="${dotColor !== 'NOCOLOR' ? 'background:' + dotColor + ';' : ''}" title="${dotTitle}">${dotColor === 'NOCOLOR' ? '\u26A0' : ''}</span>
                <input class="zone-name-input" type="text" value="${escapeHtml(zone.name)}"
                    onclick="event.stopPropagation()"
                    onchange="updateZoneName(${i}, this.value)">
                ${summaryHtml}${regionBadge}
                <button class="zone-mute-btn${zone.muted ? ' muted' : ''}" onclick="event.stopPropagation(); toggleZoneMute(${i})" title="Temporarily disable this zone without deleting it">${zone.muted ? '&#x1F6AB;' : '&#x1F441;'}</button>
                <button class="zone-move-btn" onclick="event.stopPropagation(); duplicateZone(${i})" title="Duplicate this zone" style="font-size:12px; padding:1px 5px;">&#x29C9;</button>
                <div class="zone-reorder-group">
                    <button class="zone-move-btn" onclick="event.stopPropagation(); moveZoneUp(${i})" title="Move zone up (higher priority)"${i === 0 ? ' disabled' : ''}>&#9650;</button>
                    <button class="zone-move-btn" onclick="event.stopPropagation(); moveZoneDown(${i})" title="Move zone down (lower priority)"${i === zones.length - 1 ? ' disabled' : ''}>&#9660;</button>
                </div>
                <button class="zone-move-btn" onclick="event.stopPropagation(); promptLinkZone(${i})" title="${zone.linkGroup ? 'Linked (click to unlink)' : 'Link this zone to another'}" style="font-size:11px; padding:1px 4px;${zone.linkGroup ? ' color:var(--accent-gold); border-color:var(--accent-gold);' : ''}">${zone.linkGroup ? '&#128279;' : '&#9741;'}</button>
                <button class="zone-delete-btn" onclick="event.stopPropagation(); deleteZone(${i})" title="Delete zone">&times;</button>
            </div>
            ${zone.linkGroup ? `<div style="font-size:8px; color:var(--accent-gold); padding:0 8px 2px; letter-spacing:0.5px;">&#128279; LINKED: ${zones.filter(z => z.linkGroup === zone.linkGroup).map(z => z.name).join(' + ')}</div>` : ''}
        </div>`;
        });
    } catch (err) {
        console.error('[renderZones] Error building zone list:', err);
        html = zones.map((z, i) => `<div class="zone-card zone-card-collapsed${i === selectedZoneIndex ? ' selected' : ''}" onclick="selectZone(${i})" id="zone-card-${i}"><div class="zone-card-header"><span class="zone-number">${i + 1}</span><input class="zone-name-input" type="text" value="${escapeHtml(z.name || 'Zone ' + (i + 1))}" onchange="updateZoneName(${i}, this.value)"></div></div>`).join('');
    }
    // Preserve search input focus + selection across renders
    const _prevSearch = document.getElementById('zoneSearchInput');
    const _hadSearchFocus = (_prevSearch === document.activeElement);
    const _searchSelStart = _hadSearchFocus ? _prevSearch.selectionStart : 0;
    const _searchSelEnd = _hadSearchFocus ? _prevSearch.selectionEnd : 0;
    container.innerHTML = html;
    // Restore search focus if it was active
    if (_hadSearchFocus) {
        const newInp = document.getElementById('zoneSearchInput');
        if (newInp) {
            newInp.focus();
            try { newInp.setSelectionRange(_searchSelStart, _searchSelEnd); } catch (e) {}
        }
    }
    // Re-apply zone search filter if active
    if (typeof _zoneSearchQuery !== 'undefined' && _zoneSearchQuery) setZoneSearchQuery(_zoneSearchQuery);
    // Render zone quick-view bar
    renderZoneQuickView();
    // Render the detail panel for selected zone
    renderZoneDetail(selectedZoneIndex);
    // Auto-save after any zone change
    if (typeof autoSave === 'function') autoSave();
    // Update onboarding hints
    if (typeof updateOnboardingHints === 'function') updateOnboardingHints();
    // Update auto-save badge
    if (typeof updateAutoSaveBadge === 'function') updateAutoSaveBadge();
    if (typeof renderContextActionBar === 'function') renderContextActionBar();
}

/** Render the zone quick-view bar — colored chips for each zone with a base assigned */
function renderZoneQuickView() {
    const bar = document.getElementById('zoneQuickViewBar');
    if (!bar) return;
    const OVERLAY_COLORS = (typeof ZONE_OVERLAY_COLORS !== 'undefined') ? ZONE_OVERLAY_COLORS : [
        [255,50,50,200],[50,255,50,200],[50,100,255,200],[255,255,50,200],
        [255,50,255,200],[50,255,255,200],[255,150,50,200],[150,50,255,200],
        [255,100,100,200],[100,255,200,200],[200,150,255,200]
    ];
    let chips = '';
    zones.forEach(function(zone, i) {
        if (!zone.base && !zone.finish) return; // skip unconfigured
        const c = OVERLAY_COLORS[i % OVERLAY_COLORS.length];
        const bg = 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',0.7)';
        const baseName = zone.finish
            ? ((typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : []).find(function(m){return m.id===zone.finish;}) || {}).name || zone.finish
            : ((typeof BASES !== 'undefined' ? BASES : []).find(function(b){return b.id===zone.base;}) || {}).name || zone.base;
        const shortName = baseName.length > 16 ? baseName.substring(0, 14) + '..' : baseName;
        const sel = i === selectedZoneIndex ? ' selected' : '';
        chips += '<span class="zone-qv-chip' + sel + '" style="background:' + bg + ';" onclick="selectZone(' + i + ')" title="' + escapeHtml(zone.name + ': ' + baseName) + '">' + (i + 1) + ': ' + escapeHtml(shortName) + '</span>';
    });
    bar.innerHTML = chips;
}

function getColorStatusText(zone) {
    // Check for drawn region first
    const hasRegion = zone.regionMask && zone.regionMask.some(v => v > 0);
    const regionPixels = hasRegion ? zone.regionMask.reduce((sum, v) => sum + v, 0) : 0;
    const regionNote = hasRegion ? `<br><span style="color: var(--accent-blue);">&#9998; Drawn region: <strong>${regionPixels.toLocaleString()} pixels</strong> marked</span>` : '';

    if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
        return `&#10004; Multi-color zone: <strong>${zone.colors.length} colors stacked</strong> - all pixels get the same finish${regionNote}`;
    }
    if (hasRegion && (zone.colorMode === 'none' || zone.color === null)) {
        return `<span style="color: var(--accent-blue);">&#9998; Drawn region: <strong>${regionPixels.toLocaleString()} pixels</strong> - zone applies only here (no color match). Assign base/finish and Render.</span>`;
    }
    if (zone.colorMode === 'none' || zone.color === null) return '<span style="color: #ff6644;">&#9888; No color or region set - use Pick Color, Draw Region, or buttons</span>';
    if (zone.colorMode === 'quick') return `&#10004; Matching all <strong>${zone.color}</strong> pixels`;
    if (zone.colorMode === 'special') {
        if (zone.color === 'everything') return '&#10004; Covers <strong>ALL</strong> pixels on the car';
        if (zone.color === 'remaining') return '&#10004; Catches anything <strong>not claimed</strong> by zones above';
        return `&#10004; Special: <strong>${zone.color}</strong>`;
    }
    if (zone.colorMode === 'picker') {
        const c = zone.color;
        const hex = zone.pickerColor || '#???';
        return `&#10004; Matching pixels near <strong>${hex.toUpperCase()}</strong> (tolerance: ${c.tolerance})`;
    }
    if (zone.colorMode === 'text') return `&#10004; Matching: <strong>${escapeHtml(String(zone.color))}</strong>`;
    return '';
}

function renderMultiColorChips(zone, zoneIndex) {
    const colors = zone.colors || [];
    if (colors.length === 0 && zone.colorMode !== 'multi') return '';

    let chips = colors.map((c, ci) => {
        const hex = c.hex || '#???';
        return `<div style="display: flex; flex-direction: column; gap: 2px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 4px; padding: 3px 6px; font-size: 10px;">
            <div style="display: flex; align-items: center; gap: 3px;">
                <span style="width: 14px; height: 14px; border-radius: 3px; background: ${hex}; border: 1px solid var(--border); display: inline-block;"></span>
                <span style="font-family: 'Consolas', monospace; color: var(--accent-green);">${hex.toUpperCase()}</span>
                <button onclick="event.stopPropagation(); removeColorFromZone(${zoneIndex}, ${ci})" style="background:none; border:none; color:#ff4444; cursor:pointer; font-size:12px; padding:0 2px; line-height:1;" title="Remove this color">&times;</button>
            </div>
            <div style="display: flex; align-items: center; gap: 3px;">
                <span style="font-size:8px; color:var(--text-dim);">TOL:</span>
                <input type="range" min="5" max="100" value="${c.tolerance || 40}" style="width:60px; height:10px;"
                    oninput="updateColorTolerance(${zoneIndex}, ${ci}, parseInt(this.value)); this.nextElementSibling.textContent='±'+this.value"
                    title="Tolerance for this specific color">
                <span style="font-size:8px; color:var(--text-dim); min-width:18px;">±${c.tolerance || 40}</span>
            </div>
        </div>`;
    }).join('');

    return `<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; align-items: center;">
        ${chips}
        <button onclick="event.stopPropagation(); addColorToZoneFromPicker(${zoneIndex})" class="quick-color-btn" style="font-size: 9px; padding: 2px 6px; border-color: var(--accent-green); color: var(--accent-green);" title="Add another color to this zone (use hex input or eyedropper first)">+ Add Color</button>
        ${colors.length > 0 ? `<button onclick="event.stopPropagation(); clearZoneColors(${zoneIndex})" class="quick-color-btn" style="font-size: 9px; padding: 2px 6px; border-color: #ff4444; color: #ff4444;" title="Clear all stacked colors">Clear All</button>` : ''}
    </div>`;
}

function addColorToZoneFromPicker(zoneIndex) {
    // ADD a color to the zone's colors array.
    // Priority: 1) most recently picked eyedropper color (from canvas click)
    //           2) hex input field value
    //           3) zone's existing pickerColor
    //           4) fallback blue
    const zone = (typeof zoneIndex === 'number' && zoneIndex >= 0) ? zones[zoneIndex] : null;
    let hex = null;

    // 1. Most recent eyedropper pick
    if (typeof lastEyedropperColor !== 'undefined' && lastEyedropperColor) {
        const ec = lastEyedropperColor;
        hex = '#' + [ec.r, ec.g, ec.b].map(c => c.toString(16).padStart(2, '0')).join('').toUpperCase();
    }
    // 2. Hex input
    if (!hex) {
        const hexInput = document.getElementById('hexInput');
        if (hexInput && hexInput.value && /^#[0-9A-Fa-f]{6}$/.test(hexInput.value)) {
            hex = hexInput.value.toUpperCase();
        }
    }
    // 3. Zone's existing pickerColor
    if (!hex) hex = zone.pickerColor || '#3366FF';

    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    // 2026-04-21 HEENAN POST-AUDIT: `??` not `||` so painter-set tolerance=0
    // (exact-match selector) survives the color-stack path. See Codex audit
    // on the overnight-loop final summary — preset import preserved 0 but
    // this runtime tagger silently coerced 0→40.
    const tol = zone.pickerTolerance ?? 40;

    // Check for duplicate
    if (!Array.isArray(zone.colors)) zone.colors = [];
    if (zone.colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
        showToast('That color is already added to this zone', true);
        return;
    }

    zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
    zone.colorMode = 'multi';
    zone.color = zone.colors; // color becomes the array
    zone.pickerColor = hex; // also update picker display
    renderZones();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Added ${hex} to ${zone.name} (${zone.colors.length} color${zone.colors.length !== 1 ? 's' : ''} stacked)`);
}

function removeColorFromZone(zoneIndex, colorIndex) {
    const zone = (typeof zoneIndex === 'number' && zoneIndex >= 0) ? zones[zoneIndex] : null;
    if (!zone || !zone.colors || colorIndex < 0 || colorIndex >= zone.colors.length) return;
    // FIVE-HOUR SHIFT Win C3: pre-fix this destructive op pushed NO undo and
    // fired NO preview refresh. Painter accidentally clicked the × on a
    // multi-color stack entry → entry gone forever, no Ctrl+Z, and the LIVE
    // PREVIEW stayed on the old palette until they touched another control.
    // Same class as marathon #56 (clearZoneColors) and #57 (updateColorTolerance).
    const removedHex = zone.colors[colorIndex] && zone.colors[colorIndex].hex;
    pushZoneUndo('Remove multi-color: ' + (removedHex || ''));
    zone.colors.splice(colorIndex, 1);
    if (zone.colors.length === 0) {
        zone.colorMode = 'none';
        zone.color = null;
    } else {
        zone.color = zone.colors;
    }
    renderZones();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function updateColorTolerance(zoneIndex, colorIndex, value) {
    const zone = zones[zoneIndex];
    if (zone.colors && zone.colors[colorIndex]) {
        // 2026-04-18 MARATHON bug #57 (MED): drag-coalesced undo so the
        // painter can Ctrl+Z a tolerance slider drag session.
        pushZoneUndo('Multi-color tolerance', true);
        zone.colors[colorIndex].tolerance = value;
        zone.color = zone.colors;
        triggerPreviewRender();
    }
}

function clearZoneColors(zoneIndex) {
    // 2026-04-18 MARATHON bug #56 (HIGH): destructive op — wipes the
    // multi-color stack AND colorMode AND color. Pre-fix, painter clicked
    // "Clear" by accident and lost the entire stack with no undo. Now
    // pushes zone undo first.
    pushZoneUndo('Clear zone colors');
    zones[zoneIndex].colors = [];
    zones[zoneIndex].colorMode = 'none';
    zones[zoneIndex].color = null;
    renderZones();
    triggerPreviewRender();
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ===== ZONE DETAIL PANEL (Floating Side Panel or Left-Panel Fallback) =====
function renderZoneDetail(index) {
    const floatPanel = document.getElementById('zoneEditorFloat');
    const fallbackPanel = document.getElementById('zoneDetailPanel');
    // Prefer floating panel; if missing (e.g. different build), use bottom drawer in left panel
    const panel = floatPanel || fallbackPanel;
    if (!panel) return;
    // Save scroll position before re-render to prevent scroll jumping
    let _savedScrollTop = 0;
    if (floatPanel) {
        const body = floatPanel.querySelector('.zone-detail-body');
        if (body) _savedScrollTop = body.scrollTop;
        floatPanel.innerHTML = '';
        floatPanel.classList.remove('active', 'collapsed');
    }
    if (fallbackPanel) fallbackPanel.innerHTML = '';
    if (index < 0 || index >= zones.length) {
        panel.innerHTML = '';
        if (floatPanel) { floatPanel.classList.remove('active'); floatPanel.style.display = ''; floatPanel.style.visibility = ''; }
        updateBottomBarShift();
        return;
    }
    const wasActive = floatPanel && floatPanel.classList.contains('active');
    const sameZone = lastRenderedZoneDetailIndex === index;
    if (floatPanel) {
        floatPanel.classList.add('active');
        floatPanel.classList.remove('collapsed');
        floatPanel.style.display = 'flex';
        floatPanel.style.visibility = 'visible';
    }
    if (fallbackPanel && panel === fallbackPanel) {
        fallbackPanel.style.display = 'block';
        fallbackPanel.style.visibility = 'visible';
    }
    updateBottomBarShift();
    const zone = zones[index];
    const i = index;
    if (typeof refreshToolbarModeSensitiveUi === 'function') refreshToolbarModeSensitiveUi();

    // Build the detail panel HTML with all zone controls
    let html = '';

    // Header bar
    const _hdrStatusBadge = (typeof getZoneStatusBadgeHTML === 'function') ? getZoneStatusBadgeHTML(zone) : '';
    const _hdrColorPill = (typeof getZoneColorPillHTML === 'function') ? getZoneColorPillHTML(zone) : '';
    html += `<div class="zone-detail-header">
        <span class="zone-number">${i + 1}</span>
        ${_hdrStatusBadge}
        ${_hdrColorPill}
        <span class="zone-detail-title">${escapeHtml(zone.name)}</span>
        <button class="btn btn-sm" onclick="event.stopPropagation(); autoNameZone(${i})" title="Auto-suggest a name based on the assigned finish" style="padding:1px 5px;font-size:9px;border-color:#888;color:#bbb;margin-left:4px;">\u270D Auto-name</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); copyZoneToClipboard(${i})" title="Copy zone settings (Ctrl+Shift+C)" style="padding:1px 5px;font-size:9px;">\u2398</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); pasteZoneFromClipboard(${i})" title="Paste zone settings (Ctrl+Shift+V)" style="padding:1px 5px;font-size:9px;">\u2399</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); duplicateZoneWithHueOffset(${i})" title="Duplicate this zone with a hue offset" style="padding:1px 5px;font-size:9px;border-color:#cc88ff;color:#cc88ff;">+Hue</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); soloZone(${i})" title="Solo: mute all other zones" style="padding:1px 5px;font-size:9px;border-color:#ffaa00;color:#ffaa00;">Solo</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); exportSingleZone(${i})" title="Export this zone as JSON" style="padding:1px 5px;font-size:9px;">\u21E9</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); resetZone(${i})" title="Reset this zone to defaults" style="padding:1px 5px;font-size:9px;color:#ff8855;">\u21BB</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); if(typeof shokkMe==='function') shokkMe(${i})" title="⚡ SHOKK ME — totally randomize this zone (base, pattern, overlays, colors, everything)" style="padding:1px 6px;font-size:9px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;border:none;border-radius:3px;cursor:pointer;margin-left:auto;margin-right:4px;font-weight:bold;letter-spacing:0.5px;">⚡ SHOKK ME</button>
        <button class="zone-detail-close" onclick="event.stopPropagation(); toggleZoneFloat()" title="Collapse panel (E)" style="font-size:13px;">&#9664;</button>
        <button class="zone-detail-close" onclick="event.stopPropagation(); collapseZoneDetail()" title="Close detail panel">&times;</button>
    </div>`;

    // Body
    html += `<div class="zone-detail-body" onclick="event.stopPropagation()">`;

    // Hint
    if (zone.hint) {
        html += `<div class="zone-hint">${escapeHtml(zone.hint)}</div>`;
    }

    // Color selector
    const colorStatus = getColorStatusText(zone);
    html += `<div class="section-collapsible" id="sectionColor${i}">
    <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
        <span class="section-header-label">COLOR</span>
        <span class="collapse-arrow section-header-arrow">&#9660;</span>
    </div>
    <div class="color-selector">
        ${(typeof _psdLayers !== 'undefined' && _psdLayers.length > 0) ? `
        <div style="margin-bottom:8px;padding:6px 8px;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.15);border-radius:6px;">
            <div style="font-size:10px;color:var(--accent-cyan);font-weight:bold;margin-bottom:4px;">RESTRICT TO LAYER</div>
            <select style="width:100%;font-size:11px;padding:4px;background:var(--bg-dark);color:var(--text);border:1px solid var(--border);border-radius:4px;"
                onchange="setZoneSourceLayer(${i}, this.value)">
                <option value="">All layers (no restriction)</option>
                ${_psdLayers.filter(l => l.img).map(l =>
                    '<option value="' + l.id + '"' + (zone.sourceLayer === l.id ? ' selected' : '') + '>' + l.name + ' (' + l.groupName + ')</option>'
                ).join('')}
            </select>
            ${zone.sourceLayer ? '<div style="font-size:9px;color:var(--accent-green);margin-top:3px;">Zone restricted to: ' + (_psdLayers.find(l => l.id === zone.sourceLayer)?.name || zone.sourceLayer) + '</div>' : ''}
        </div>` : ''}
        <div class="color-selector-label">What pixels does this zone cover?</div>
        <div class="color-selector-help">${(typeof _psdLayers !== 'undefined' && _psdLayers.length > 0) ? 'Pick a color on the selected layer, or use any selection method below' : 'Pick a color below, type a color name, enter a hex code, or use the eyedropper on your paint'}</div>
        <div class="quick-colors">
            ${QUICK_COLORS.map(c =>
        `<button class="quick-color-btn${zone.colorMode === 'quick' && zone.color === c.value ? ' active' : ''}"
                    style="border-left: 3px solid ${c.bg};"
                    onclick="setQuickColor(${i}, '${c.value}')"
                    title="Selects all ${c.label.toLowerCase()}-ish pixels">${c.label}</button>`
    ).join('')}
            ${SPECIAL_COLORS.map(c =>
        `<button class="quick-color-btn special${zone.colorMode === 'special' && zone.color === c.value ? ' active' : ''}"
                    onclick="setSpecialColor(${i}, '${c.value}')"
                    title="${c.value === 'everything' ? 'Selects ALL pixels on the car' : 'Catches any pixels not claimed by higher-priority zones'}">${c.label}</button>`
    ).join('')}
        </div>
        <div class="color-text-row">
            <input class="color-text-input" type="text" placeholder="Type a color: &quot;dark blue&quot;, &quot;bright red&quot;, &quot;navy&quot;..."
                value="${zone.colorMode === 'text' ? escapeHtml(String(zone.color)) : ''}"
                onchange="setTextColor(${i}, this.value)"
                onfocus="this.select()">
            <span style="font-size:7px; color:var(--text-dim); margin-left:4px;" title="Text colors use hue-range matching which is approximate. For precise selection, use the hex/eyedropper picker below or the color buttons above.">&#9432; approximate</span>
        </div>
        <div class="color-hex-row">
            <span class="hex-label">HEX / Eyedropper:</span>
            <input class="hex-code-input" type="text" placeholder="#FF3366"
                value="${zone.colorMode === 'picker' && !zone.colors?.length ? (zone.pickerColor || '') : ''}"
                onchange="setHexColor(${i}, this.value)"
                onfocus="this.select()"
                maxlength="7">
            <input class="color-picker-input" id="colorPickerInput${i}" type="color" value="${zone.pickerColor || '#3366ff'}"
                onchange="setPickerColor(${i}, this.value)"
                title="Color picker">
            <button onclick="(function(){var inp=document.getElementById('colorPickerInput${i}');if(inp)setPickerColor(${i},inp.value);})()"
                    style="background:#E87A20; color:#fff; border:none; padding:4px 10px; border-radius:4px; cursor:pointer; font-weight:bold; font-size:10px; white-space:nowrap;"
                    title="Apply the selected color to this zone">&#10003; Apply</button>
        </div>
        <div class="color-tol-row">
            <span class="tol-label">TOL:</span>
            <input class="tolerance-slider" type="range" min="5" max="100" value="${zone.pickerTolerance ?? 40}"
                onchange="setPickerTolerance(${i}, this.value)"
                title="How loosely colors are matched — low = exact, high = approximate">
            <span class="tolerance-val">&plusmn;${zone.pickerTolerance ?? 40}</span>
            <button class="btn btn-sm" onclick="event.stopPropagation();setTolerancePreset(${i},'tight')" title="Tight: ±5 — exact color match" style="padding:1px 5px;font-size:9px;">Tight</button>
            <button class="btn btn-sm" onclick="event.stopPropagation();setTolerancePreset(${i},'default')" title="Default: ±40 — balanced" style="padding:1px 5px;font-size:9px;">Std</button>
            <button class="btn btn-sm" onclick="event.stopPropagation();setTolerancePreset(${i},'loose')" title="Loose: ±80 — wide capture" style="padding:1px 5px;font-size:9px;">Loose</button>
            <label style="display:inline-flex; align-items:center; gap:4px; font-size:11px; color:#aaa; margin-left:12px;"
                   title="Hard Edge — removes soft blending at zone boundaries for crisp, clean edges. Prevents pattern bleed into adjacent colors.">
              <input type="checkbox" ${zone.hardEdge ? 'checked' : ''}
                     onchange="zones[${i}].hardEdge = this.checked; renderZones();">
              <span style="color:#E87A20;">&#11041;</span> Hard Edge
            </label>
        </div>
        ${renderMultiColorChips(zone, i)}
        <div class="color-status">${colorStatus}</div>
        ${typeof renderHarmonyPanel === 'function' && i === selectedZoneIndex ? renderHarmonyPanel(zone, i) : ''}
    </div>
    </div>`;

    // Base/Finish row — gold border section (collapsible)
    html += `<div class="section-collapsible" id="sectionBase${i}">
    <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
        <span class="section-header-label">BASE</span>
        <span class="collapse-arrow section-header-arrow">&#9660;</span>
    </div>
    <div style="border-left:2px solid var(--accent-gold, #FFB300); padding-left:6px; margin-top:4px; background:rgba(255,179,0,0.03);">`;
    html += `<div style="display:flex; flex-direction:column; gap:6px;">
        <div class="zone-finish-row" style="flex-wrap:wrap; gap:6px;">
            <label style="color:var(--accent-gold, #FFB300); font-weight:700; min-width:40px;">Base</label>
            <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'base', ${i})" title="The base material that defines how light interacts with this zone&#39;s surface" style="flex:1; min-width:0;">
                ${zone.finish ? renderSwatchDot(zone.finish, getSwatchColor(zone), getZoneColorHex(zone)) : zone.base ? renderSwatchDot(zone.base, getSwatchColor(zone), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                <span class="swatch-name" style="overflow:hidden; text-overflow:ellipsis;">${getBaseName(zone)}</span>
                <span class="swatch-arrow">&#9662;</span>
            </div>
            <span class="lock-toggle${zone.lockBase ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockBase')" title="Lock base during randomize">${zone.lockBase ? '&#128274;' : '&#128275;'}</span>
        </div>
        <div style="display:flex; gap:6px; padding-left:46px;">
            <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishBrowser(${i})" title="Opens a full-screen gallery of all finishes with thumbnail previews. Filter by type, search by name, click to apply." style="padding:2px 8px; font-size:9px; border-color:var(--accent-gold); color:var(--accent-gold);">🎨 Browse</button>
            <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishCompare(${i})" title="Compare two finishes side-by-side on your car" style="padding:2px 8px; font-size:9px; border-color:var(--accent-blue); color:var(--accent-blue);">🔍 Compare</button>
            <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishMixer(${i})" title="Mix 2-3 finishes together at custom ratios to create a hybrid finish" style="padding:2px 8px; font-size:9px; border-color:#e844e8; color:#e844e8;">&#129514; Mixer</button>
        </div>
    </div>`;

    if (zone.base || zone.finish) {
        const _baseColorMode = (zone.baseColorMode || 'source');
        const _baseColorHex = (zone.baseColor || '#ffffff');
        const _baseColorStrengthPct = Math.round(Math.max(0, Math.min(1, Number(zone.baseColorStrength ?? 1))) * 100);
        const _baseHueOffset = Math.round(Number(zone.baseHueOffset ?? 0));
        const _baseSatAdj = Math.round(Number(zone.baseSaturationAdjust ?? 0));
        const _baseBrightAdj = Math.round(Number(zone.baseBrightnessAdjust ?? 0));
        const _baseSrcId = (zone.baseColorSource || '');
        const _baseSrcDisp = _baseSrcId ? (getOverlayBaseDisplay(_baseSrcId) || {}) : null;
        const _baseSrcName = _baseSrcDisp ? (_baseSrcDisp.name || _baseSrcId) : '- Select special -';
        const _baseSrcSwatch = _baseSrcDisp ? (_baseSrcDisp.swatch || '#888') : '#333';
        html += `<div class="zone-finish-row" style="padding-left:24px; align-items:flex-start; flex-direction:column; gap:6px;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; width:100%;">
                <span class="stack-label-mini" style="min-width:70px;">Base Color</span>
                <select class="mini-select" style="min-width:170px; flex:1; max-width:220px;" onchange="setZoneBaseColorMode(${i}, this.value)">
                    <option value="source" ${_baseColorMode === 'source' ? 'selected' : ''}>Use source paint</option>
                    <option value="solid" ${_baseColorMode === 'solid' ? 'selected' : ''}>Use solid color</option>
                    <option value="special" ${_baseColorMode === 'special' ? 'selected' : ''}>From special</option>
                    <option value="gradient" ${_baseColorMode === 'gradient' ? 'selected' : ''}>Custom gradient</option>
                </select>
                ${_baseColorMode === 'solid' ? `<input type="color" id="baseColorPicker${i}" value="${_baseColorHex}" onchange="setZoneBaseColor(${i}, this.value)" title="Pick base tint">` : ''}
                ${_baseColorMode === 'solid' ? `<input type="text" value="${_baseColorHex}" onchange="setZoneBaseColor(${i}, this.value)" style="width:78px;font-size:10px;">` : ''}
                ${_baseColorMode === 'solid' ? `<button onclick="(function(){var inp=document.getElementById('baseColorPicker${i}');if(inp)setZoneBaseColor(${i},inp.value);})()" style="background:#E87A20;color:#fff;border:none;padding:3px 8px;border-radius:3px;cursor:pointer;font-weight:bold;font-size:9px;" title="Apply the selected color">✓ Apply</button>` : ''}
                ${_baseColorMode === 'gradient' ? _buildGradientEditorHTML(i, zone) : ''}
                ${_baseColorMode === 'special' ? `</div>
            <div style="display:flex; align-items:center; gap:8px; width:100%; padding-left:0; margin-top:2px;">
                <span class="stack-label-mini" style="min-width:70px;">Special</span>
                <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'baseColorSource', ${i})" title="Pick special color source" style="display:inline-flex;align-items:center;gap:6px; flex:1; min-width:0;">
                    ${_baseSrcId ? renderSwatchDot(_baseSrcId, _baseSrcSwatch, _baseColorHex) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                    <span class="swatch-name" style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${_baseSrcName}</span>
                    <span class="swatch-arrow">&#9662;</span>
                </div>` : ''}
                ${_baseColorMode === 'special' && _baseSrcId ? `<button class="btn btn-sm" onclick="event.stopPropagation(); setZoneBaseColorSource(${i}, null)" title="Clear source" style="padding:0px 5px;font-size:9px;line-height:1.2;">✕</button>` : ''}
            </div>
            ${_baseColorMode !== 'source' ? `<div style="display:flex; align-items:center; gap:8px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini">Color Strength</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseColorStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                <input type="range" min="0" max="100" step="5" value="${_baseColorStrengthPct}" oninput="setZoneBaseColorStrength(${i}, this.value)" class="stack-slider">
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseColorStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                <span class="stack-val" id="detBaseColorStrVal${i}">${_baseColorStrengthPct}%</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px; width:100%; padding:6px 0; border-top:1px solid rgba(255,122,24,0.12); margin-top:2px;">
                <label style="display:inline-flex; align-items:center; gap:6px; font-size:11px; color:var(--pro-text-primary,#e8ecf2); cursor:pointer;">
                    <input type="checkbox" ${zone.baseColorFitZone ? 'checked' : ''} onchange="setZoneBaseColorFitZone(${i}, this.checked)">
                    <span>🎯 Fit to Selection</span>
                </label>
                <span style="font-size:10px; color:var(--pro-text-tertiary,#5a6b7d);" title="When enabled, the full base color/gradient/special AND the base spec compress into your selection rectangle instead of being cropped by it. Perfect for small regions like car numbers.">Compress full pattern into drawn area (base + spec)</span>
            </div>` : ''}
            <div class="hsb-controls" style="display:flex; align-items:center; gap:4px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:62px;">Hue Shift</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseHueOffset(${i}, Math.max(-180, (zones[${i}].baseHueOffset||0)-1))" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                <input type="range" min="-180" max="180" step="1" value="${_baseHueOffset}" oninput="setZoneBaseHueOffset(${i}, this.value)" class="stack-slider" title="Shift all colors around the color wheel — negative = cool, positive = warm">
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseHueOffset(${i}, Math.min(180, (zones[${i}].baseHueOffset||0)+1))" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                <span class="stack-val" id="detBaseHueVal${i}" style="min-width:32px;">${_baseHueOffset}°</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseHueOffset(${i}, 0)" title="Reset" style="padding:0 4px;font-size:9px;">↺</button>
            </div>
            <div class="hsb-controls" style="display:flex; align-items:center; gap:4px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:62px;">Saturation</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseSaturation(${i}, Math.max(-100, (zones[${i}].baseSaturationAdjust||0)-1))" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                <input type="range" min="-100" max="100" step="1" value="${_baseSatAdj}" oninput="setZoneBaseSaturation(${i}, this.value)" class="stack-slider" title="Color intensity — negative = more grey, positive = more vivid">
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseSaturation(${i}, Math.min(100, (zones[${i}].baseSaturationAdjust||0)+1))" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                <span class="stack-val" id="detBaseSatVal${i}" style="min-width:32px;">${_baseSatAdj}</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseSaturation(${i}, 0)" title="Reset" style="padding:0 4px;font-size:9px;">↺</button>
            </div>
            <div class="hsb-controls" style="display:flex; align-items:center; gap:4px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:62px;">Brightness</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseBrightness(${i}, Math.max(-100, (zones[${i}].baseBrightnessAdjust||0)-1))" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                <input type="range" min="-100" max="100" step="1" value="${_baseBrightAdj}" oninput="setZoneBaseBrightness(${i}, this.value)" class="stack-slider" title="Overall lightness — negative = darker, positive = brighter">
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseBrightness(${i}, Math.min(100, (zones[${i}].baseBrightnessAdjust||0)+1))" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                <span class="stack-val" id="detBaseBrightVal${i}" style="min-width:32px;">${_baseBrightAdj}</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseBrightness(${i}, 0)" title="Reset" style="padding:0 4px;font-size:9px;">↺</button>
            </div>
        </div>`;
    }

    // ===== SPEC PATTERN OVERLAYS =====
    // Build spec patterns HTML here, but inject it AFTER base rotate/scale/strength block
    let specPatternsHtml = '';
    if (zone.base || zone.finish) {
        const specStack = zone.specPatternStack || [];
        const specStackActive = specStack.length > 0;
        const MAX_SPEC_PATTERN_LAYERS = 5;
        specPatternsHtml += `<div class="section-collapsible" id="sectionSpecPatterns${i}">
        <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
            <span class="section-header-label" style="display:flex;align-items:center;">SPEC PATTERNS
                <span class="whats-this" onclick="event.stopPropagation(); var p=this.nextElementSibling; p.style.display=p.style.display===\'none\'?\'block\':\'none\';" title="Click for explanation">?</span>
                <div class="whats-this-panel" style="display:none; font-weight:normal; letter-spacing:0; font-size:11px;">Procedurally generated texture overlays that modulate your spec map channels (Metallic, Roughness, Clearcoat) independently. Stack up to 5 for complex material surfaces.</div>
            </span>
            <span class="collapse-arrow section-header-arrow">&#9660;</span>
        </div>
        <div class="pattern-stack-section spec-patterns-section" style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px; border-left:2px solid #ff4444; background:rgba(255,68,68,0.04);">
            <div class="pattern-stack-header" style="color:#ff4444;font-size:10px;">
                &#9670; Spec Patterns
                <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">stackable spec map overlays</span>
                ${specStackActive ? '<span style="font-size:9px;margin-left:auto;color:#ff4444;">&#9679; ACTIVE (' + specStack.length + ')</span>' : ''}
            </div>
            <div style="padding:4px 8px;">`;

        specStack.forEach((sp, si) => {
            const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === sp.pattern);
            const spName = spDef ? spDef.name : (sp.pattern || '???');
            const chM = (sp.channels || 'MR').includes('M');
            const chR = (sp.channels || 'MR').includes('R');
            const chCC = (sp.channels || 'MR').includes('CC');
            specPatternsHtml += `<div style="margin-bottom:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                    <span style="font-size:10px; color:#ff4444; font-weight:bold;">${si + 1}.</span>
                    <img src="/thumbnails/spec_patterns/${sp.pattern}.png" alt="" style="width:32px;height:32px;object-fit:cover;border-radius:3px;border:1px solid var(--border);vertical-align:middle;" onerror="this.src='/api/spec-pattern-preview/${sp.pattern}?v=live';this.onerror=null;">
                    <button onclick="event.stopPropagation(); toggleSpecPatternPicker(${i}, ${si})" style="background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:10px;cursor:pointer;flex:1;text-align:left;" title="Click to change spec pattern">${spName} &#9660;</button>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); removeSpecPatternLayer(${i}, ${si})" title="Remove" style="margin-left:auto; padding:0px 5px; font-size:9px; line-height:1.2;">&times;</button>
                </div>
                <div id="specPatternPicker_${i}_${si}" style="display:none; max-height:360px; overflow-y:auto; background:#0d0d1a; border:1px solid #ff444466; border-radius:6px; margin-bottom:6px; padding:6px;" data-zone="${i}" data-layer="${si}" data-current="${sp.pattern}"></div>
                <div style="display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center;">
                    <div class="stack-control-group" style="flex:1; min-width:100px;">
                        <span class="stack-label-mini">Opacity</span>
                        <input type="range" min="0" max="100" step="5" value="${sp.opacity ?? 50}"
                            oninput="setSpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value)); this.nextElementSibling.textContent=this.value+'%'"
                            class="stack-slider" title="Opacity (5% steps)">
                        <span class="stack-val">${sp.opacity ?? 50}%</span>
                    </div>
                    <div class="stack-control-group" style="flex:1; min-width:90px;">
                        <span class="stack-label-mini">Range</span>
                        <input type="range" min="1" max="100" step="1" value="${sp.range || 40}"
                            oninput="setSpecPatternLayerProp(${i}, ${si}, 'range', parseInt(this.value)); this.nextElementSibling.textContent=this.value"
                            class="stack-slider" title="Range (1-100)">
                        <span class="stack-val">${sp.range || 40}</span>
                    </div>
                    <div class="stack-control-group" style="min-width:80px;">
                        <span class="stack-label-mini">Blend</span>
                        <select onchange="setSpecPatternLayerProp(${i}, ${si}, 'blendMode', this.value)"
                            style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                            <option value="normal"${(sp.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                            <option value="multiply"${sp.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                            <option value="screen"${sp.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                            <option value="overlay"${sp.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                            <option value="hardlight"${sp.blendMode === 'hardlight' ? ' selected' : ''}>Hard Light</option>
                            <option value="softlight"${sp.blendMode === 'softlight' ? ' selected' : ''}>Soft Light</option>
                        </select>
                    </div>
                    <div class="stack-control-group" style="min-width:100px;">
                        <span class="stack-label-mini">Channels</span>
                        <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chM ? 'checked' : ''} onchange="toggleSpecPatternChannel(${i}, ${si}, 'M', this.checked)"> M</label>
                        <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chR ? 'checked' : ''} onchange="toggleSpecPatternChannel(${i}, ${si}, 'R', this.checked)"> R</label>
                        <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chCC ? 'checked' : ''} onchange="toggleSpecPatternChannel(${i}, ${si}, 'CC', this.checked)"> CC</label>
                    </div>
                </div>
                <div style="margin-top:6px; display:grid; grid-template-columns:42px auto 1fr auto 36px; gap:2px 4px; align-items:center;">
                    <span style="color:#888; font-size:10px;">POS X</span>
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'offsetX', -1, 0, 100)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((sp.offsetX||0.5)*100)}"
                           oninput="pushZoneUndo('', true); zones[${i}].specPatternStack[${si}].offsetX=this.value/100; this.parentElement.querySelector('.spValPosX${i}_${si}').textContent=this.value+'%'; triggerPreviewRender();" style="width:100%;">
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'offsetX', 1, 0, 100)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">+</button>
                    <span class="spValPosX${i}_${si}" style="color:#ccc; font-size:10px;">${Math.round((sp.offsetX||0.5)*100)}%</span>
                    <span style="color:#888; font-size:10px;">POS Y</span>
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'offsetY', -1, 0, 100)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((sp.offsetY||0.5)*100)}"
                           oninput="pushZoneUndo('', true); zones[${i}].specPatternStack[${si}].offsetY=this.value/100; this.parentElement.querySelector('.spValPosY${i}_${si}').textContent=this.value+'%'; triggerPreviewRender();" style="width:100%;">
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'offsetY', 1, 0, 100)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">+</button>
                    <span class="spValPosY${i}_${si}" style="color:#ccc; font-size:10px;">${Math.round((sp.offsetY||0.5)*100)}%</span>
                    <span style="color:#ff4444; font-size:10px; font-weight:bold;">SCALE</span>
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'scale', -1, 5, 400)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">−</button>
                    <input type="range" min="5" max="400" step="5" value="${Math.round((sp.scale||1)*100)}"
                           oninput="pushZoneUndo('', true); zones[${i}].specPatternStack[${si}].scale=this.value/100; this.parentElement.querySelector('.spValScale${i}_${si}').textContent=(this.value/100).toFixed(2)+'x'; triggerPreviewRender();" style="width:100%; accent-color:#ff4444;">
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'scale', 1, 5, 400)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">+</button>
                    <span class="spValScale${i}_${si}" style="color:#ff4444; font-size:10px; font-weight:bold;">${(sp.scale||1).toFixed(2)}x</span>
                    <span style="color:#00C8C8; font-size:10px; font-weight:bold;">BOX</span>
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'boxSize', -5, 5, 100)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">−</button>
                    <input type="range" min="5" max="100" step="5" value="${sp.boxSize||100}"
                           oninput="pushZoneUndo('', true); zones[${i}].specPatternStack[${si}].boxSize=parseInt(this.value); this.parentElement.querySelector('.spValBox${i}_${si}').textContent=this.value+'%'; triggerPreviewRender();" style="width:100%; accent-color:#00C8C8;">
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'boxSize', 5, 5, 100)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">+</button>
                    <span class="spValBox${i}_${si}" style="color:#00C8C8; font-size:10px; font-weight:bold;">${sp.boxSize||100}%</span>
                    <span style="color:#888; font-size:10px;">ROT</span>
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'rotation', -1, 0, 359)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">−</button>
                    <input type="range" min="0" max="359" step="5" value="${sp.rotation||0}"
                           oninput="pushZoneUndo('', true); zones[${i}].specPatternStack[${si}].rotation=parseInt(this.value); this.parentElement.querySelector('.spValRot${i}_${si}').textContent=this.value+'°'; triggerPreviewRender();" style="width:100%;">
                    <button onclick="event.stopPropagation(); stepSpecPatternLayerProp(${i}, ${si}, 'rotation', 1, 0, 359)" style="padding:0 5px;cursor:pointer;background:none;border:1px solid var(--border);color:var(--text);border-radius:3px;font-size:11px;line-height:1;">+</button>
                    <span class="spValRot${i}_${si}" style="color:#ccc; font-size:10px;">${sp.rotation||0}°</span>
                </div>
                <div style="margin-top:4px;">
                    <button onclick="activateManualPlacement(${i}, 'spec_pattern_${si}'); showToast('Drag on canvas to position spec pattern','info');"
                            style="background:#1a1a1a; color:#00C8C8; border:1px solid #00C8C8; padding:2px 8px; font-size:10px; cursor:pointer; border-radius:3px;"
                            title="Drag on canvas to position this spec pattern">
                      ✋ Manual Place
                    </button>
                </div>
            </div>`;
        });

        if (specStack.length < MAX_SPEC_PATTERN_LAYERS) {
            const _spg1 = typeof SPEC_PATTERN_GROUPS !== 'undefined' ? SPEC_PATTERN_GROUPS : {};
            const _spgMap1 = {};
            Object.entries(_spg1).forEach(([g, ids]) => ids.forEach(id => { _spgMap1[id] = g; }));
            const _tabBtns1 = ['All', ...Object.keys(_spg1)].map(g =>
                `<button class="spec-cat-tab${g==='All'?' active':''}" data-cat="${g}" onclick="specPickerCatTab('specPatternGrid${i}',this,'${g.replace(/'/g,'\\\'')}')" title="${g}">${g}</button>`
            ).join('');
            specPatternsHtml += `<div style="margin-top:4px;">
                <div id="specPatternGrid${i}_tabs" class="spec-cat-tab-row" style="display:none;">${_tabBtns1}</div>
                <div id="specPatternGrid${i}" style="display:none; max-height:370px; overflow-y:auto; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;" class="spec-pattern-grid spec-pattern-grid-4col">`;
            (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                const _sg1 = _spgMap1[sp.id] || 'Misc';
                const _shortName1 = sp.name.length > 12 ? sp.name.slice(0,12)+'…' : sp.name;
                specPatternsHtml += `<div class="spec-pattern-thumb-card" data-category="${_sg1}"
                    onclick="if(this._spPopup){this._spPopup.remove();this._spPopup=null;} document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); var _g=document.getElementById('specPatternGrid${i}'); var _gt=document.getElementById('specPatternGrid${i}_tabs'); if(_g){_g.style.display='none';} if(_gt){_gt.style.display='none';} addSpecPatternLayer(${i}, '${sp.id}');"
                    title="${sp.name}: ${sp.desc}"
                    onmouseenter="(function(el){var img=el.querySelector('img');if(!img)return;var popup=document.createElement('div');popup.className='spec-thumb-popup';popup.innerHTML='<img src=\\''+img.src+'\\' style=\\'width:200px;height:100px;object-fit:contain;\\'><div style=\\'text-align:center;font-size:11px;color:#ccc;padding:4px;\\'>${sp.name.replace(/'/g,'&#39;')}</div>';var rect=el.getBoundingClientRect();popup.style.left=Math.min(rect.left+rect.width/2-104, window.innerWidth-260)+'px';popup.style.top=Math.max(rect.top-140,4)+'px';document.body.appendChild(popup);el._spPopup=popup;})(this)"
                    onmouseleave="if(this._spPopup){this._spPopup.remove();this._spPopup=null;}">
                    <img src="/thumbnails/spec_patterns/${sp.id}.png" alt="${sp.name}" loading="eager" style="width:48px;height:48px;object-fit:cover;" onerror="this.src='/api/spec-pattern-preview/${sp.id}?v=live';this.onerror=null;">
                    <div class="thumb-label">${_shortName1}</div>
                </div>`;
            });
            specPatternsHtml += `</div>
                <button onclick="document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); const g=document.getElementById('specPatternGrid${i}'); const t=document.getElementById('specPatternGrid${i}_tabs'); const show=!g.style.display||g.style.display==='none'; if(show){g.style.display='grid';g.style.gridTemplateColumns='repeat(4,1fr)';g.style.gap='6px';g.style.padding='6px';if(t)t.style.display='flex';}else{g.style.display='none';if(t)t.style.display='none';}" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #ff444444; color:#ff4444; margin-top:4px;">
                    + Add Spec Pattern (click to browse)
                </button>
            </div>`;
        } else {
            specPatternsHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 5 spec pattern layers reached.</div>';
        }

        // SPEC PREVIEW panel
        specPatternsHtml += `<div class="section-collapsible collapsed" id="sectionSpecPreview${i}" style="margin-top:6px;">
            <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
                <span class="section-header-label">SPEC PREVIEW</span>
                <span class="collapse-arrow section-header-arrow">&#9660;</span>
            </div>
            <div class="spec-preview-panel">
                <div class="spec-preview-tabs">
                    <button class="spec-preview-tab active" data-base="chrome" onclick="setSpecPreviewBase(${i},this,'chrome')">Chrome</button>
                    <button class="spec-preview-tab" data-base="matte" onclick="setSpecPreviewBase(${i},this,'matte')">Matte Black</button>
                    <button class="spec-preview-tab" data-base="brushed" onclick="setSpecPreviewBase(${i},this,'brushed')">Brushed Metal</button>
                    <button class="spec-preview-tab" data-base="carbon" onclick="setSpecPreviewBase(${i},this,'carbon')">Carbon</button>
                </div>
                <canvas id="specPreviewCanvas_${i}" width="256" height="128" class="spec-preview-canvas" style="background:#111;display:block;"></canvas>
                <div style="margin-top:4px;display:flex;align-items:center;gap:8px;">
                    <button onclick="event.stopPropagation(); updateSpecPreview(${i})" class="btn btn-sm" style="font-size:10px;padding:2px 10px;border:1px solid #E87A2044;color:#E87A20;">&#8635; Refresh</button>
                    <span id="specPreviewStatus_${i}" style="font-size:9px;color:var(--text-dim);"></span>
                </div>
            </div>
        </div>`;

        specPatternsHtml += `</div></div>
        </div>`;
    }

    // Base rotation, scale, strength + base position (horizontal rows under BASE)
    if (zone.base || zone.finish) {
        html += `<div class="zone-finish-row zone-base-rotate-row base-rotate-scale" style="padding-left:24px; flex-direction: column; align-items: stretch;">
            <div style="display:flex; flex-wrap: wrap; gap: 8px 12px; width: 100%;">
                <div class="stack-control-group" style="flex: 1; min-width: 120px;">
                    <span class="stack-label-mini">Base Rotate</span>
                    <input type="range" min="0" max="359" step="1" value="${zone.baseRotation || 0}"
                        oninput="setZoneBaseRotation(${i}, this.value)"
                        class="stack-slider" title="Rotate the base material in degrees">
                    <input type="number" min="0" max="359" step="1" value="${zone.baseRotation || 0}"
                        onchange="setZoneBaseRotation(${i}, this.value)"
                        oninput="setZoneBaseRotation(${i}, this.value)"
                        id="detBaseRotVal${i}"
                        style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text-main,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;" title="Type exact degrees">
                    <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneBaseRotation(${i})" title="Reset to 0°" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                </div>
                <div class="stack-control-group" style="flex: 1; min-width: 120px;">
                    <span class="stack-label-mini">Base Scale</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="100" max="1000" step="5" value="${Math.round((zone.baseScale || 1.0) * 100)}"
                        oninput="setZoneBaseScale(${i}, parseFloat(this.value)/100)"
                        class="stack-slider" title="Scale the base material texture">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detBaseScaleVal${i}">${(zone.baseScale || 1.0).toFixed(2)}x</span>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneBaseScale(${i})" title="Reset to 1.0x" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                </div>
                <div class="stack-control-group" style="flex: 1; min-width: 120px;">
                    <span class="stack-label-mini">Base Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.baseStrength ?? 1) * 100)}"
                        oninput="setZoneBaseStrength(${i}, this.value)"
                        class="stack-slider" title="How strongly the base affects the spec map — 0% = no effect, 100% = full">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detBaseStrVal${i}">${Math.round((zone.baseStrength ?? 1) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="flex: 1; min-width: 120px;">
                    <span class="stack-label-mini" title="Weakens this base's MATERIAL itself (metallic/roughness/clearcoat shift toward neutral). 100% = full chrome/matte/etc.; 10% = chrome reads as nearly dielectric; 0% = neutral finish (flat M=0, R=128, CC=16).">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.baseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Overall strength of the spec map output">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detBaseSpecStrVal${i}">${Math.round((zone.baseSpecStrength ?? 1) * 100)}%</span>
                </div>
                <div class="stack-control-group spec-blend-section" style="flex: 1; min-width: 140px;">
                    <span class="stack-label-mini" style="display:flex;align-items:center;gap:2px;">Spec Blend
                        <span class="whats-this" onclick="event.stopPropagation(); var p=document.getElementById('specBlendHelp${i}'); p.style.display=p.style.display===\'none\'?\'block\':\'none\';" title="Click for explanation">?</span>
                    </span>
                    <select class="mini-select" style="min-width:100px;font-size:10px;" onchange="setZoneBaseSpecBlendMode(${i}, this.value)" title="How spec patterns combine with the base — Normal, Multiply, Screen, Overlay, etc.">
                        <option value="normal" ${(zone.baseSpecBlendMode || 'normal') === 'normal' ? 'selected' : ''}>Normal</option>
                        <option value="multiply" ${zone.baseSpecBlendMode === 'multiply' ? 'selected' : ''}>Multiply</option>
                        <option value="screen" ${zone.baseSpecBlendMode === 'screen' ? 'selected' : ''}>Screen</option>
                        <option value="overlay" ${zone.baseSpecBlendMode === 'overlay' ? 'selected' : ''}>Overlay</option>
                        <option value="hardlight" ${zone.baseSpecBlendMode === 'hardlight' ? 'selected' : ''}>Hard Light</option>
                        <option value="softlight" ${zone.baseSpecBlendMode === 'softlight' ? 'selected' : ''}>Soft Light</option>
                    </select>
                    <div id="specBlendHelp${i}" class="whats-this-panel" style="display:none; width:100%; margin-top:4px;">Controls how spec pattern values combine with the base spec — Normal replaces, Multiply darkens, Screen brightens, Overlay enhances contrast.</div>
                </div>
            </div>
            ${renderPlacementModeControls(i, 'base', { label: 'Base placement', targetLabel: 'the base finish', centeredLabel: 'Centered + Numeric' })}
            <div class="base-position-controls" style="display:flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; width: 100%; margin-top: 6px;">
                <span class="stack-label-mini" style="white-space:nowrap;">Base position</span>
                <div class="stack-control-group" style="flex: 1; min-width: 90px;">
                    <span class="stack-label-mini">Pos X</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseOffset(${i}, 'X', -1)" title="-1%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.baseOffsetX ?? 0.5) * 100)}" oninput="setZoneBaseOffsetX(${i}, this.value)" class="stack-slider" title="Pan base left/right">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseOffset(${i}, 'X', 1)" title="+1%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detBasePosXVal${i}">${Math.round((zone.baseOffsetX ?? 0.5) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="flex: 1; min-width: 90px;">
                    <span class="stack-label-mini">Pos Y</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseOffset(${i}, 'Y', -1)" title="-1%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.baseOffsetY ?? 0.5) * 100)}" oninput="setZoneBaseOffsetY(${i}, this.value)" class="stack-slider" title="Pan base up/down">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneBaseOffset(${i}, 'Y', 1)" title="+1%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detBasePosYVal${i}">${Math.round((zone.baseOffsetY ?? 0.5) * 100)}%</span>
                </div>
                <span class="stack-val" id="detBasePosRotVal${i}" style="display:none;">${zone.baseRotation ?? 0}°</span>
                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px; white-space:nowrap;"><input type="checkbox" ${(zone.baseFlipH || false) ? 'checked' : ''} onchange="setZoneBaseFlipH(${i}, this.checked)"> Flip H</label>
                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px; white-space:nowrap;"><input type="checkbox" ${(zone.baseFlipV || false) ? 'checked' : ''} onchange="setZoneBaseFlipV(${i}, this.checked)"> Flip V</label>
            </div>
            <div class="stack-control-group" style="margin-top:8px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                ${(() => {
                    const stackCount = (zone.patternStack || []).filter(l => l.id && l.id !== 'none').length;
                    const hasPrimaryPattern = (zone.pattern && zone.pattern !== 'none');
                    const hasSecondBasePattern = zone.secondBase && zone.secondBasePattern;
                    const hasThirdBasePattern = zone.thirdBase && zone.thirdBasePattern;
                    const hasFourthBasePattern = zone.fourthBase && zone.fourthBasePattern;
                    const hasFifthBasePattern = zone.fifthBase && zone.fifthBasePattern;
                    const hasBaseForPlacement = !!(zone.base || zone.finish);
                    const canPlaceAnything = hasPrimaryPattern || hasSecondBasePattern || hasThirdBasePattern || hasFourthBasePattern || hasFifthBasePattern || hasBaseForPlacement;
                    
                    let pHtml = canPlaceAnything ? `
                    <div class="stack-control-group advanced-only" style="margin-bottom:8px; padding:8px 10px; background:rgba(0,0,0,0.3); border:1px dotted var(--border,#2a2a4a); border-radius:4px;">
                        <span class="stack-label-mini" style="margin-right:8px;">Placement workspace</span>
                        <select id="placementLayerSelect${i}" onchange="setPlacementLayer(this.value); updatePlacementBanner();" style="font-size:10px; padding:4px 8px; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:4px; min-width:140px;" title="Then click and drag on the template to move this layer">
                            <option value="none" ${placementLayer === 'none' ? 'selected' : ''}>- None -</option>
                            ${hasBaseForPlacement ? `<option value="base" ${placementLayer === 'base' ? 'selected' : ''}>Base (gradient/duo)</option>` : ''}
                            ${hasPrimaryPattern ? `<option value="pattern" ${placementLayer === 'pattern' ? 'selected' : ''}>Primary pattern</option>` : ''}
                            ${hasSecondBasePattern ? `<option value="second_base" ${placementLayer === 'second_base' ? 'selected' : ''}>2nd base overlay</option>` : ''}
                            ${hasThirdBasePattern ? `<option value="third_base" ${placementLayer === 'third_base' ? 'selected' : ''}>3rd base overlay</option>` : ''}
                            ${hasFourthBasePattern ? `<option value="fourth_base" ${placementLayer === 'fourth_base' ? 'selected' : ''}>4th base overlay</option>` : ''}
                            ${hasFifthBasePattern ? `<option value="fifth_base" ${placementLayer === 'fifth_base' ? 'selected' : ''}>5th base overlay</option>` : ''}
                        </select>
                        <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); var sel=document.getElementById('placementLayerSelect${i}'); if(sel && sel.value && sel.value!=='none'){ setPlacementMode(${i}, sel.value, 'manual'); } else { showToast('Choose a placement target first', true); }" style="padding:3px 8px;font-size:10px;border-color:#1d8ba3;color:#bff7ff;background:#0f2830;">Edit Selected</button>
                        <button type="button" class="btn btn-sm" title="Done editing placement &mdash; keep current values and exit placement mode (matches the &times; Done button on the floating placement bar)" onclick="event.stopPropagation(); if(typeof deactivateManualPlacement==='function')deactivateManualPlacement(); setPlacementLayer('none'); renderZones();" style="padding:3px 8px;font-size:10px;">Done Editing</button>
                        <div style="font-size:9px; color:var(--text-dim); margin-top:4px; width:100%;">Pick which finish layer the <strong>template drag</strong> should move. The section-level placement buttons above are the quickest route.</div>
                    </div>` : '';

                    // Inject spec patterns HTML (moved here from above BASE controls)
                    pHtml += specPatternsHtml;

                    pHtml += `<div class="section-collapsible" id="sectionPattern${i}">
                    <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
                        <span class="section-header-label">PATTERN</span>
                        <span class="collapse-arrow section-header-arrow">&#9660;</span>
                    </div>
                    <div style="border-left:2px dotted #22c55e; padding-left:6px; margin-top:6px; background:rgba(34,197,94,0.03);">`;
                    pHtml += `<span class="stack-label-mini" style="margin-bottom:4px; color:#22c55e;">Pattern 1 on this Layer/Zone</span>
                    <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'pattern', ${i})" style="display:inline-flex;align-items:center;gap:6px;margin-bottom:6px;" title="Visual texture pattern that tiles across the zone">
                        ${hasPrimaryPattern ? renderSwatchDot(zone.pattern, getPatternSwatchColor(zone.pattern), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                        <span class="swatch-name">${getPatternName(zone.pattern)}</span>
                        <span class="swatch-arrow">&#9662;</span>
                    </div>`;

                    if (hasPrimaryPattern) {
                        pHtml += `<div class="pattern-advanced-controls">
                        <div class="stack-control-group"><span class="stack-label-mini">Opacity</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternOpacity(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${zone.patternOpacity ?? 100}" oninput="setZonePatternOpacity(${i}, this.value)" class="stack-slider" title="How visible the pattern is — 0% = invisible, 100% = full">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternOpacity(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detPatOpVal${i}">${zone.patternOpacity ?? 100}%</span></div>
                        <div class="stack-control-group"><span class="stack-label-mini">Scale</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="10" max="400" step="5" value="${Math.round((zone.scale || 1.0) * 100)}" oninput="setZoneScale(${i}, parseFloat(this.value)/100)" class="stack-slider" title="Pattern size — smaller values = more repetitions, larger = zoomed in">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detScaleVal${i}">${(zone.scale || 1.0).toFixed(2)}x</span>
                            <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneScale(${i})" title="Reset" style="padding:0 4px;font-size:9px;">↺</button></div>
                        <div class="stack-control-group"><span class="stack-label-mini">Rotate</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneRotation(${i}, -1)" title="-1°" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="359" step="1" value="${zone.rotation || 0}" oninput="setZoneRotation(${i}, this.value)" class="stack-slider" title="Rotate the pattern in degrees (0-359)">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneRotation(${i}, 1)" title="+1°" style="padding:0 4px;font-size:10px;">+</button>
                            <input type="number" min="0" max="359" value="${zone.rotation || 0}" onchange="setZoneRotation(${i}, this.value)" id="detRotVal${i}" style="width:42px;font-size:10px;text-align:center;padding:1px 2px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:3px;">
                            <span style="font-size:10px;color:var(--text-dim);">°</span>
                            <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneRotation(${i})" style="padding:0 4px;font-size:9px;">↺</button></div>
                        ${renderPlacementModeControls(i, 'pattern', { label: 'Pattern placement', targetLabel: 'the primary pattern', allowFit: true, centeredLabel: 'Full Canvas' })}
                        <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternOffsetX(${i}, -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'pattern')}>−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.patternOffsetX ?? 0.5) * 100)}" oninput="setZonePatternOffsetX(${i}, this.value)" class="stack-slider" title="Slide the pattern left/right across the canvas" ${_placementOffsetControlAttrs(zone, 'pattern')}>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternOffsetX(${i}, 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'pattern')}>+</button>
                            <span class="stack-val" id="detPatPosXVal${i}" ${_placementOffsetValueAttrs(zone, 'pattern')}>${Math.round((zone.patternOffsetX ?? 0.5) * 100)}%</span></div>
                        <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternOffsetY(${i}, -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'pattern')}>−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.patternOffsetY ?? 0.5) * 100)}" oninput="setZonePatternOffsetY(${i}, this.value)" class="stack-slider" title="Slide the pattern up/down across the canvas" ${_placementOffsetControlAttrs(zone, 'pattern')}>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternOffsetY(${i}, 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'pattern')}>+</button>
                            <span class="stack-val" id="detPatPosYVal${i}" ${_placementOffsetValueAttrs(zone, 'pattern')}>${Math.round((zone.patternOffsetY ?? 0.5) * 100)}%</span></div>
                        <div class="stack-control-group" style="flex-wrap:wrap; gap:6px;">
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Mirror the pattern horizontally"><input type="checkbox" ${(zone.patternFlipH || false) ? 'checked' : ''} onchange="setZonePatternFlipH(${i}, this.checked)"> Flip H</label>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Mirror the pattern vertically"><input type="checkbox" ${(zone.patternFlipV || false) ? 'checked' : ''} onchange="setZonePatternFlipV(${i}, this.checked)"> Flip V</label>
                        </div>
                        <div class="stack-control-group"><span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternSpecMult(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.patternSpecMult ?? 1) * 100)}" oninput="setZonePatternSpecMult(${i}, this.value)" class="stack-slider" title="Pattern punch (spec map), 5% steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternSpecMult(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detPatStrVal${i}">${Math.round((zone.patternSpecMult ?? 1) * 100)}%</span></div>
                        <div class="stack-control-group strength-map-toggle-row" style="margin-top:4px;">
                            <button class="btn btn-sm ${zone.patternStrengthMapEnabled ? 'strength-map-btn-active' : 'strength-map-btn'}" onclick="event.stopPropagation(); toggleStrengthMap(${i})" title="Paint where the pattern is strong vs weak — like a heat map brush">
                                Strength Map ${zone.patternStrengthMapEnabled ? 'ON' : 'OFF'}
                            </button>
                        </div>
                        ${zone.patternStrengthMapEnabled ? `
                        <div class="strength-map-panel" id="strengthMapPanel${i}">
                            <div class="strength-map-canvas-wrap">
                                <canvas id="strengthMapCanvas${i}" class="strength-map-canvas" width="256" height="256"
                                    onmousedown="strengthMapStartPaint(event, ${i})"
                                    onmousemove="strengthMapPaint(event, ${i})"
                                    onmouseup="strengthMapStopPaint(${i})"
                                    onmouseleave="strengthMapStopPaint(${i})"></canvas>
                            </div>
                            <div class="strength-map-controls">
                                <div class="strength-map-brush-row">
                                    <span class="stack-label-mini">Brush</span>
                                    <input type="range" min="2" max="80" step="1" value="${window._strengthMapBrushSize || 20}" oninput="window._strengthMapBrushSize = parseInt(this.value); document.getElementById('smBrushSizeVal${i}').textContent = this.value + 'px'" class="stack-slider" title="Brush size">
                                    <span class="stack-val" id="smBrushSizeVal${i}">${window._strengthMapBrushSize || 20}px</span>
                                </div>
                                <div class="strength-map-brush-row">
                                    <span class="stack-label-mini">Value</span>
                                    <input type="range" min="0" max="255" step="1" value="${window._strengthMapBrushValue ?? 0}" oninput="window._strengthMapBrushValue = parseInt(this.value); document.getElementById('smBrushValLabel${i}').textContent = Math.round(this.value/255*100)+'%'" class="stack-slider" title="Brush value: 0=no pattern, 255=full pattern">
                                    <span class="stack-val" id="smBrushValLabel${i}">${Math.round((window._strengthMapBrushValue ?? 0)/255*100)}%</span>
                                </div>
                                <div class="strength-map-quick-btns">
                                    <button class="btn btn-xs" onclick="event.stopPropagation(); strengthMapFill(${i}, 255)" title="Reset to 100% everywhere">Fill White</button>
                                    <button class="btn btn-xs" onclick="event.stopPropagation(); strengthMapFill(${i}, 0)" title="Zero out everywhere">Fill Black</button>
                                    <button class="btn btn-xs" onclick="event.stopPropagation(); strengthMapGradient(${i}, 'tb')" title="Top=100% fading to Bottom=0%">Top-Bottom</button>
                                    <button class="btn btn-xs" onclick="event.stopPropagation(); strengthMapGradient(${i}, 'lr')" title="Left=100% fading to Right=0%">Left-Right</button>
                                    <button class="btn btn-xs" onclick="event.stopPropagation(); strengthMapGradient(${i}, 'center')" title="Center=100% fading to edges=0%">Center Fade</button>
                                </div>
                            </div>
                        </div>` : ''}
                        </div>`;
                    }

                    (zone.patternStack || []).forEach((layer, li) => {
                        pHtml += `<div class="pattern-layer-card pattern-stack-section" data-layer-idx="${li}" data-zone-idx="${i}" style="margin-top: 8px; border-top: 1px dotted var(--border,#2a2a4a); padding-top: 8px;">
                            <div class="pattern-layer-card-header">
                                <span class="stack-label-mini" style="margin-bottom:0px; color:var(--accent-green);">Pattern ${li + 2} on this Layer/Zone</span>
                                <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'stackPattern', ${i}, ${li})" style="display:inline-flex;align-items:center;gap:6px;margin-bottom:0px;">
                                    ${(layer.id && layer.id !== 'none') ? renderSwatchDot(layer.id, getPatternSwatchColor(layer.id), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                                    <span class="swatch-name">${getPatternName(layer.id)}</span>
                                    <span class="swatch-arrow">&#9662;</span>
                                </div>
                                <button class="stack-remove-btn" onclick="removePatternLayer(${i}, ${li})" title="Remove layer" style="margin-left:auto;">&times;</button>
                            </div>
                            <div class="pattern-layer-card-controls" style="margin-top: 6px;">
                                <div class="stack-control-group">
                                    <span class="stack-label-mini">Opacity</span>
                                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepPatternLayerOpacity(${i}, ${li}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                    <input type="range" min="0" max="100" step="5" value="${layer.opacity ?? 100}"
                                        oninput="setPatternLayerOpacity(${i}, ${li}, this.value)"
                                        class="stack-slider" title="Opacity (5% steps)">
                                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepPatternLayerOpacity(${i}, ${li}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                    <span class="stack-val">${layer.opacity ?? 100}%</span>
                                </div>
                                <div class="stack-control-group">
                                    <span class="stack-label-mini">Scale</span>
                                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepPatternLayerScale(${i}, ${li}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                                    <input type="range" min="10" max="400" step="5" value="${Math.round((layer.scale || 1.0) * 100)}"
                                        oninput="setPatternLayerScale(${i}, ${li}, parseFloat(this.value)/100)"
                                        class="stack-slider" title="Scale (5% steps)">
                                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepPatternLayerScale(${i}, ${li}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                                    <span class="stack-val">${(layer.scale || 1.0).toFixed(2)}x</span>
                                </div>
                                <div class="stack-control-group">
                                    <span class="stack-label-mini">Rotate</span>
                                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepPatternLayerRotation(${i}, ${li}, -1)" title="-1°" style="padding:0 4px;font-size:10px;">−</button>
                                    <input type="range" min="0" max="359" step="1" value="${layer.rotation || 0}"
                                        oninput="setPatternLayerRotation(${i}, ${li}, this.value)"
                                        class="stack-slider" title="Rotation">
                                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepPatternLayerRotation(${i}, ${li}, 1)" title="+1°" style="padding:0 4px;font-size:10px;">+</button>
                                    <input type="number" min="0" max="359" step="1" value="${layer.rotation || 0}"
                                        onchange="setPatternLayerRotation(${i}, ${li}, this.value)"
                                        oninput="setPatternLayerRotation(${i}, ${li}, this.value)"
                                        class="stack-val-input"
                                        style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;">
                                    <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                                </div>
                                <div class="stack-control-group">
                                    <span class="stack-label-mini">Blend</span>
                                    <select onchange="setPatternLayerBlend(${i}, ${li}, this.value)"
                                        style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                        <option value="normal"${(layer.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                        <option value="multiply"${layer.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                        <option value="screen"${layer.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                        <option value="overlay"${layer.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                                    </select>
                                </div>
                            </div>
                        </div>`;
                    });

                    if ((zone.patternStack || []).length < MAX_PATTERN_STACK_LAYERS) {
                        pHtml += `<div class="pattern-stack-add-btn-wrap" style="margin-top: 8px;">
                            <button type="button" class="btn btn-sm stack-add-btn" onclick="event.stopPropagation(); addPatternLayer(${i})" title="Add another pattern to this layer">+ Add Layer</button>
                        </div>`;
                    }

                    pHtml += `</div>`; // close green dotted Pattern 1 section inner div
                    pHtml += `</div>`; // close section-collapsible PATTERN wrapper
                    return pHtml;
                })()}
            </div>
        </div>`;
        html += `</div>`; // close gold BASE section inner div
        html += `</div>`; // close section-collapsible BASE wrapper
    }

    // ===== ⚗️ BASE OVERLAY LAYER (Dual Material Blend) - available for ALL base layers and monolithics =====
    if (zone.base || zone.finish) {
        // Overlay mini-map summary
        const _ovl2active = !!(zone.secondBase || zone.secondBaseColorSource);
        const _ovl3active = !!(zone.thirdBase || zone.thirdBaseColorSource);
        const _ovl4active = !!(zone.fourthBase || zone.fourthBaseColorSource);
        const _ovl5active = !!(zone.fifthBase || zone.fifthBaseColorSource);
        html += `<div class="overlay-minimap" id="overlayMinimap${i}">
            <div class="overlay-minimap-row">
                <span style="font-size:10px;font-weight:700;color:var(--text-dim);letter-spacing:1px;">OVERLAYS:</span>
                <span class="overlay-minimap-item">2nd <span class="overlay-minimap-swatch" style="background:#ffffff;"></span> <span style="color:${_ovl2active ? '#33ff66' : '#555'};font-size:9px;">${_ovl2active ? 'Active' : 'Off'}</span></span>
                <span style="color:#444;">|</span>
                <span class="overlay-minimap-item">3rd <span class="overlay-minimap-swatch" style="background:#FFD700;"></span> <span style="color:${_ovl3active ? '#33ff66' : '#555'};font-size:9px;">${_ovl3active ? 'Active' : 'Off'}</span></span>
                <span style="color:#444;">|</span>
                <span class="overlay-minimap-item">4th <span class="overlay-minimap-swatch" style="background:#AA44FF;"></span> <span style="color:${_ovl4active ? '#33ff66' : '#555'};font-size:9px;">${_ovl4active ? 'Active' : 'Off'}</span></span>
                <span style="color:#444;">|</span>
                <span class="overlay-minimap-item">5th <span class="overlay-minimap-swatch" style="background:#00C8C8;"></span> <span style="color:${_ovl5active ? '#33ff66' : '#555'};font-size:9px;">${_ovl5active ? 'Active' : 'Off'}</span></span>
            </div>
            <button class="overlay-minimap-btn" onclick="event.stopPropagation(); openFineTuning(${i})">&#9881; Open Fine Tuning &rarr;</button>
        </div>`;

        html += `<div class="section-collapsible" id="sectionOverlays${i}">
        <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
            <span class="section-header-label">OVERLAYS
                <span class="whats-this" onclick="event.stopPropagation(); var p=this.nextElementSibling; p.style.display=p.style.display===\'none\'?\'block\':\'none\';" title="Click for explanation">?</span>
                <div class="whats-this-panel" style="display:none; font-weight:normal; letter-spacing:0; font-size:11px;">Stack additional base finishes on top of your primary base. Each overlay has its own pattern, blend mode, and opacity. Think of them as Photoshop layers for spec maps.</div>
            </span>
            <span class="collapse-arrow section-header-arrow">&#9660;</span>
        </div>
        <div class="pattern-stack-section overlay-section" style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;">
            <div class="pattern-stack-header" style="color:#c084fc;font-size:10px;">
                ⚗️ Base Overlay Layer
                <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">blend a 2nd material into this zone</span>
                ${(zone.secondBase || zone.secondBaseColorSource) ? `<span style="font-size:9px;margin-left:auto;color:#a78bfa;">● ACTIVE</span>` : ''}
            </div>
            <div style="padding:4px 8px;">
                <div class="stack-control-group">
                    <span class="stack-label-mini">2nd Base</span>
                    <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'secondBase', ${i})" title="Click to pick 2nd base (thumbnail preview)">
                        ${(zone.secondBase || zone.secondBaseColorSource) ? renderSwatchDot(zone.secondBase || zone.secondBaseColorSource, (getOverlayBaseDisplay(zone.secondBase || zone.secondBaseColorSource) || {}).swatch || '#888', zone.secondBaseColor || '#ffffff') : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                        <span class="swatch-name">${(zone.secondBase || zone.secondBaseColorSource) ? (getOverlayBaseDisplay(zone.secondBase || zone.secondBaseColorSource) || {}).name || (zone.secondBase || zone.secondBaseColorSource) : '- None -'}</span>
                        <span class="swatch-arrow">&#9662;</span>
                    </div>
                    ${(zone.secondBase || zone.secondBaseColorSource) ? `<button class="btn btn-sm" onclick="event.stopPropagation(); setZoneSecondBase(${i}, ''); setZoneSecondBaseColorSource(${i}, null)" title="Remove overlay" style="padding:0px 5px;font-size:9px;line-height:1.2;margin-left:4px;">✕</button>` : ''}
                </div>
                ${(zone.secondBase || zone.secondBaseColorSource) ? `
                <div class="stack-control-group" style="margin-top:4px;flex-wrap:wrap;gap:6px 10px;">
                    <span class="stack-label-mini">Overlay Color</span>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;">
                        <input type="radio" name="sbColorSource${i}" value="solid" ${!zone.secondBaseColorSource || zone.secondBaseColorSource === 'solid' ? 'checked' : ''} onchange="setZoneSecondBaseColorSource(${i}, 'solid')">
                        <span>Solid</span>
                    </label>
                    <span style="display:flex;align-items:center;gap:4px;"> <input type="color" id="overlayColorPicker${i}" value="${zone.secondBaseColor || '#ffffff'}"
                        onchange="setZoneSecondBaseColor(${i}, this.value)"
                        title="Paint color for the overlay"
                        style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                    <input type="text" value="${zone.secondBaseColor || '#ffffff'}" onchange="setZoneSecondBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7">
                    <button onclick="(function(){var inp=document.getElementById('overlayColorPicker${i}');if(inp)setZoneSecondBaseColor(${i},inp.value);})()" style="background:#E87A20;color:#fff;border:none;padding:2px 6px;border-radius:3px;cursor:pointer;font-weight:bold;font-size:9px;" title="Apply the selected color">✓ Apply</button></span>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color (e.g. Bronze Heat stays bronze/gold)">
                        <input type="radio" name="sbColorSource${i}" value="overlay" ${zone.secondBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneSecondBaseColorSourceToOverlay(${i})">
                        <span>Same as overlay</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use a base finish color — picks from bases that have distinctive colors">
                        <input type="radio" name="sbColorSource${i}" value="frombase" ${zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('base:') ? 'checked' : ''} onchange="openSwatchPicker(this.parentElement, 'overlayBaseColor', ${i})">
                        <span>From base</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;">
                        <input type="radio" name="sbColorSource${i}" value="special" ${zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'second' }; setZoneSecondBaseColorSource(${i}, '${(zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('mono:') ? zone.secondBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')">
                        <span>From special</span>
                    </label>
                    ${zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'second') : ''}
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBaseStrength || 0) * 100)}"
                        oninput="setZoneSecondBaseStrength(${i}, this.value)"
                        class="stack-slider" title="0%=primary only, 100%=overlay only, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detSBStrVal${i}">${Math.round((zone.secondBaseStrength || 0) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini" title="Blend-amount for this OVERLAY's spec onto the primary base: 100% = overlay reaches its full M/R/CC where it shows; 50% = overlay contributes in roughly half the pixels with reduced intensity; 0% = overlay is fully suppressed (primary base alone shows). Unlike the primary Spec Strength this is layer-opacity semantics, not material-weakening.">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneSecondBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detSBSpecStrVal${i}">${Math.round((zone.secondBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
                <div class="hsb-controls" style="margin-top:6px;border-top:1px solid #333;padding-top:4px;">
                    <div style="color:#aaa;font-size:10px;font-weight:bold;margin-bottom:3px;">Overlay HSB Adjust</div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Hue</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].secondBaseHueShift=Math.max(-180,(zones[${i}].secondBaseHueShift||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-180" max="180" step="5" value="${zone.secondBaseHueShift || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].secondBaseHueShift=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value+'°'; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Shift overlay colors (-180° to +180°), drag=5° steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].secondBaseHueShift=Math.min(180,(zones[${i}].secondBaseHueShift||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.secondBaseHueShift || 0}°</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Sat</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].secondBaseSaturation=Math.max(-100,(zones[${i}].secondBaseSaturation||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.secondBaseSaturation || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].secondBaseSaturation=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay saturation (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].secondBaseSaturation=Math.min(100,(zones[${i}].secondBaseSaturation||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.secondBaseSaturation || 0}</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Brt</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].secondBaseBrightness=Math.max(-100,(zones[${i}].secondBaseBrightness||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.secondBaseBrightness || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].secondBaseBrightness=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay brightness (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].secondBaseBrightness=Math.min(100,(zones[${i}].secondBaseBrightness||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.secondBaseBrightness || 0}</span>
                    </div>
                </div>
                ` : ''}
                ${(zone.secondBase || zone.secondBaseColorSource) ? (() => {
                    const ovSpecStack = zone.overlaySpecPatternStack || [];
                    const ovSpecStackActive = ovSpecStack.length > 0;
                    const MAX_OVERLAY_SPEC_PATTERN_LAYERS = 5;
                    let ovSpHtml = `<div class="overlay-spec-patterns" style="border-top:1px solid #c084fc33;margin-top:6px;padding-top:6px;">
                        <div style="color:#c084fc;font-size:10px;margin-bottom:4px;">
                            &#9670; Overlay Spec Patterns
                            <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">spec overlays for 2nd base</span>
                            ${ovSpecStackActive ? '<span style="font-size:9px;margin-left:auto;color:#c084fc;">&#9679; ACTIVE (' + ovSpecStack.length + ')</span>' : ''}
                        </div>`;

                    ovSpecStack.forEach((sp, si) => {
                        const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === sp.pattern);
                        const spName = spDef ? spDef.name : (sp.pattern || '???');
                        const chM = (sp.channels || 'MR').includes('M');
                        const chR = (sp.channels || 'MR').includes('R');
                        const chCC = (sp.channels || 'MR').includes('CC');
                        ovSpHtml += `<div style="margin-bottom:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                            <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                                <span style="font-size:10px; color:#c084fc; font-weight:bold;">${si + 1}.</span>
                                <span style="font-size:10px; color:var(--text);">${spName}</span>
                                <span style="font-size:8px; color:var(--text-dim);">${spDef ? spDef.desc : ''}</span>
                                <button class="btn btn-sm" onclick="event.stopPropagation(); removeOverlaySpecPatternLayer(${i}, ${si})" title="Remove" style="margin-left:auto; padding:0px 5px; font-size:9px; line-height:1.2;">&times;</button>
                            </div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center;">
                                <div class="stack-control-group" style="flex:1; min-width:100px;">
                                    <span class="stack-label-mini">Opacity</span>
                                    <input type="range" min="0" max="100" step="5" value="${sp.opacity ?? 50}"
                                        oninput="setOverlaySpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value)); this.nextElementSibling.textContent=this.value+'%'"
                                        class="stack-slider" title="Opacity (5% steps)">
                                    <span class="stack-val">${sp.opacity ?? 50}%</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Range</span>
                                    <input type="range" min="1" max="100" step="1" value="${sp.range || 40}"
                                        oninput="setOverlaySpecPatternLayerProp(${i}, ${si}, 'range', parseInt(this.value)); this.nextElementSibling.textContent=this.value"
                                        class="stack-slider" title="Range (1-100)">
                                    <span class="stack-val">${sp.range || 40}</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Scale</span>
                                    <input type="range" min="5" max="400" step="5" value="${Math.round((sp.scale || 1) * 100)}"
                                        oninput="setOverlaySpecPatternLayerProp(${i}, ${si}, 'scale', this.value/100); this.nextElementSibling.textContent=this.value+'%'; renderZones(); triggerPreviewRender();"
                                        class="stack-slider" title="Spec pattern scale — 100% = default">
                                    <span class="stack-val">${Math.round((sp.scale || 1) * 100)}%</span>
                                </div>
                                <div class="stack-control-group" style="min-width:80px;">
                                    <span class="stack-label-mini">Blend</span>
                                    <select onchange="setOverlaySpecPatternLayerProp(${i}, ${si}, 'blendMode', this.value)"
                                        style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                        <option value="normal"${(sp.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                        <option value="multiply"${sp.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                        <option value="screen"${sp.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                        <option value="overlay"${sp.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                                        <option value="hardlight"${sp.blendMode === 'hardlight' ? ' selected' : ''}>Hard Light</option>
                                        <option value="softlight"${sp.blendMode === 'softlight' ? ' selected' : ''}>Soft Light</option>
                                    </select>
                                </div>
                                <div class="stack-control-group" style="min-width:100px;">
                                    <span class="stack-label-mini">Channels</span>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chM ? 'checked' : ''} onchange="toggleOverlaySpecPatternChannel(${i}, ${si}, 'M', this.checked)"> M</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chR ? 'checked' : ''} onchange="toggleOverlaySpecPatternChannel(${i}, ${si}, 'R', this.checked)"> R</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chCC ? 'checked' : ''} onchange="toggleOverlaySpecPatternChannel(${i}, ${si}, 'CC', this.checked)"> CC</label>
                                </div>
                            </div>
                        </div>`;
                    });

                    if (ovSpecStack.length < MAX_OVERLAY_SPEC_PATTERN_LAYERS) {
                        const _spg2 = typeof SPEC_PATTERN_GROUPS !== 'undefined' ? SPEC_PATTERN_GROUPS : {};
                        const _spgMap2 = {};
                        Object.entries(_spg2).forEach(([g, ids]) => ids.forEach(id => { _spgMap2[id] = g; }));
                        const _tabBtns2 = ['All', ...Object.keys(_spg2)].map(g =>
                            `<button class="spec-cat-tab${g==='All'?' active':''}" data-cat="${g}" onclick="specPickerCatTab('overlaySpecPatternGrid${i}',this,'${g.replace(/'/g,'\\\'')}')" title="${g}">${g}</button>`
                        ).join('');
                        ovSpHtml += `<div style="margin-top:4px;">
                            <div id="overlaySpecPatternGrid${i}_tabs" class="spec-cat-tab-row" style="display:none;">${_tabBtns2}</div>
                            <div id="overlaySpecPatternGrid${i}" style="display:none; max-height:220px; overflow-y:auto; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;" class="spec-pattern-grid spec-pattern-grid-4col">`;
                        (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                            const _sg2 = _spgMap2[sp.id] || 'Misc';
                            const _shortName2 = sp.name.length > 12 ? sp.name.slice(0,12)+'…' : sp.name;
                            ovSpHtml += `<div class="spec-pattern-thumb-card" data-category="${_sg2}"
                                onclick="if(this._spPopup){this._spPopup.remove();this._spPopup=null;} document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); var _og=document.getElementById('overlaySpecPatternGrid${i}'); var _ogt=document.getElementById('overlaySpecPatternGrid${i}_tabs'); if(_og){_og.style.display='none';} if(_ogt){_ogt.style.display='none';} addOverlaySpecPatternLayer(${i}, '${sp.id}');"
                                title="${sp.name}: ${sp.desc}"
                                onmouseenter="(function(el){var img=el.querySelector('img');if(!img)return;var popup=document.createElement('div');popup.className='spec-thumb-popup';popup.innerHTML='<img src=\\''+img.src+'\\' style=\\'width:200px;height:100px;object-fit:contain;\\'><div style=\\'text-align:center;font-size:11px;color:#ccc;padding:4px;\\'>${sp.name.replace(/'/g,'&#39;')}</div>';var rect=el.getBoundingClientRect();popup.style.left=Math.min(rect.left+rect.width/2-104, window.innerWidth-260)+'px';popup.style.top=Math.max(rect.top-140,4)+'px';document.body.appendChild(popup);el._spPopup=popup;})(this)"
                                onmouseleave="if(this._spPopup){this._spPopup.remove();this._spPopup=null;}">
                                <img src="/thumbnails/spec_patterns/${sp.id}.png" alt="${sp.name}" loading="eager" style="width:48px;height:48px;object-fit:cover;" onerror="this.src='/api/spec-pattern-preview/${sp.id}?v=live';this.onerror=null;">
                                <div class="thumb-label">${_shortName2}</div>
                            </div>`;
                        });
                        ovSpHtml += `</div>
                            <button onclick="document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); const g=document.getElementById('overlaySpecPatternGrid${i}'); const t=document.getElementById('overlaySpecPatternGrid${i}_tabs'); const show=!g.style.display||g.style.display==='none'; if(show){g.style.display='grid';g.style.gridTemplateColumns='repeat(4,1fr)';g.style.gap='6px';g.style.padding='6px';if(t)t.style.display='flex';}else{g.style.display='none';if(t)t.style.display='none';}" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #c084fc44; color:#c084fc; margin-top:4px;">
                                + Add Overlay Spec Pattern (click to browse)
                            </button>
                        </div>`;
                    } else {
                        ovSpHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 5 overlay spec pattern layers reached.</div>';
                    }

                    ovSpHtml += `</div>`;
                    return ovSpHtml;
                })() : ''}
                ${(zone.secondBase || zone.secondBaseColorSource) ? `
                <div class="stack-control-group blend-mode-section" style="margin-top:4px;align-items:flex-start;">
                    <span class="stack-label-mini" style="padding-top:2px;">Blend Mode</span>
                    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="sbBlendMode${i}" value="noise" ${['noise', 'dust'].includes(zone.secondBaseBlendMode || 'noise') ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'noise')">
                            <span>✨ Fractal Dust</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="sbBlendMode${i}" value="marble" ${zone.secondBaseBlendMode === 'marble' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'marble')">
                            <span>🌪️ Liquid Swirl</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Overlay along pattern edges/outlines">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-edges" ${['pattern-edges', 'uniform'].includes(zone.secondBaseBlendMode || '') ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-edges')">
                            <span>📐 Pattern Edges</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="sbBlendMode${i}" value="pattern" ${zone.secondBaseBlendMode === 'pattern' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern')">
                            <span>🔷 Pattern-Reactive</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Same as Pattern-Reactive but the overlay color always shows at FULL saturation where the pattern hits - strength controls coverage area, not color intensity">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-vivid" ${zone.secondBaseBlendMode === 'pattern-vivid' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-vivid')">
                            <span>💥 Pattern-Pop <span style="font-size:8px;color:var(--text-dim);">full color</span></span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Overlay tints the base (max 35%) - does not fully cover; good for subtle color shift in pattern areas">
                            <input type="radio" name="sbBlendMode${i}" value="tint" ${(zone.secondBaseBlendMode || '') === 'tint' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'tint')">
                            <span>🎨 Tint (subtle)</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Overlay on pattern ridges/peaks (brightest ridges)">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-peaks" ${zone.secondBaseBlendMode === 'pattern-peaks' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-peaks')">
                            <span>⛰️ Pattern Peaks</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Overlay in a narrow band (contour line) - strength sets band position">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-contour" ${zone.secondBaseBlendMode === 'pattern-contour' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-contour')">
                            <span>〰️ Pattern Contour</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Screen blend in pattern areas - brightens">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-screen" ${zone.secondBaseBlendMode === 'pattern-screen' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-screen')">
                            <span>✨ Pattern Screen</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Overlay in darks and lights; base in midtones">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-threshold" ${zone.secondBaseBlendMode === 'pattern-threshold' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-threshold')">
                            <span>◐ Pattern Threshold</span></label>
                    </div>
                </div>
                ${['noise', 'dust', 'marble'].includes(zone.secondBaseBlendMode || 'noise') ? `
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Fractal Detail</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseFractalScale(${i}, -1)" title="-4px" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="4" max="128" step="4" value="${zone.secondBaseFractalScale || 24}"
                        oninput="setZoneSecondBaseFractalScale(${i}, this.value)"
                        class="stack-slider" title="Fine (small) ↔ Coarse (large) Fractal Detail">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseFractalScale(${i}, 1)" title="+4px" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detSBNSVal${i}">${zone.secondBaseFractalScale || 24}px</span>
                </div>` : ''}
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Overlay Scale</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="10" max="500" step="5" value="${Math.min(500, Math.max(10, Math.round((zone.secondBaseScale ?? 1) * 100)))}"
                        oninput="setZoneSecondBaseScale(${i}, parseFloat(this.value)/100)"
                        class="stack-slider" title="5% steps (Fractal/Dust only)">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detSBScaleVal${i}">${(zone.secondBaseScale ?? 1).toFixed(2)}</span>
                    <span class="stack-label-mini" style="font-size:9px;color:var(--text-dim);margin-left:4px;">Fractal/Dust only</span>
                </div>
                <div class="stack-control-group" style="margin-top:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                    <span class="stack-label-mini" style="margin-bottom:4px;">React to zone pattern</span>
                    <p style="font-size:9px;color:var(--text-dim);margin:0 0 6px 0;">All blend modes use the selected pattern (Invert, Harden, Opacity, Scale, Rotate, Strength, Position) to control where the overlay appears. With <strong>From special</strong>, the special's full color/effect is overlayed; use Strength &gt; 0 and set <strong>React to</strong> to a pattern for pattern-based blend modes (e.g. Pattern-Reactive, Pattern-Pop).</p>
                    <div class="stack-control-group" style="margin-bottom:6px;">
                        <label class="stack-label-mini">React to</label>
                        <select onchange="setZoneSecondBasePattern(${i}, this.value)" style="font-size:10px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;min-width:140px;">
                            ${(function () { const opts = getZonePatternReactOptions(zone); let sel = getOverlayReactToSelectValue(zone, zone.secondBasePattern); if (!opts.some(o => o.value === sel)) sel = ''; return opts.map(o => `<option value="${(o.value === '' ? '' : o.value)}" ${sel === o.value ? 'selected' : ''}>${o.label}</option>`).join(''); })()}
                        </select>
                    </div>
                    <div class="stack-control-group" style="flex-wrap:wrap;gap:8px 12px;">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.secondBasePatternInvert || false) ? 'checked' : ''} onchange="setZoneSecondBasePatternInvert(${i}, this.checked)"> Invert mask (color background)</label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.secondBasePatternHarden || false) ? 'checked' : ''} onchange="setZoneSecondBasePatternHarden(${i}, this.checked)"> Harden (only in pattern)</label>
                    </div>
                    <div class="stack-control-group"><span class="stack-label-mini">Opacity</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternOpacity(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="100" step="5" value="${zone.secondBasePatternOpacity ?? 100}" oninput="setZoneSecondBasePatternOpacity(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternOpacity(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detSBPatOpVal${i}">${zone.secondBasePatternOpacity ?? 100}%</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Scale</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="10" max="400" step="5" value="${Math.round((zone.secondBasePatternScale ?? 1.0) * 100)}" oninput="setZoneSecondBasePatternScale(${i}, parseFloat(this.value)/100)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detSBPatScaleVal${i}">${(zone.secondBasePatternScale ?? 1.0).toFixed(2)}x</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Rotate</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternRotation(${i}, -1)" title="-5°" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="359" step="5" value="${zone.secondBasePatternRotation ?? 0}" id="detSBPatRotRange${i}" oninput="setZoneSecondBasePatternRotation(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternRotation(${i}, 1)" title="+5°" style="padding:0 4px;font-size:10px;">+</button>
                        <input type="number" min="0" max="359" value="${zone.secondBasePatternRotation ?? 0}" onchange="setZoneSecondBasePatternRotation(${i}, this.value)" id="detSBPatRotVal${i}" style="width:42px;font-size:10px;text-align:center;padding:1px 2px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:3px;"> <span style="font-size:10px;color:var(--text-dim);">°</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBasePatternStrength ?? 1) * 100)}" oninput="setZoneSecondBasePatternStrength(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detSBPatStrVal${i}">${Math.round((zone.secondBasePatternStrength ?? 1) * 100)}%</span></div>
                    ${renderPlacementModeControls(i, 'second_base', { label: 'Overlay placement', targetLabel: 'the 2nd base overlay', allowFit: true, centeredLabel: 'Centered + Numeric' })}
                    <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternOffset(${i}, 'X', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'second_base')}>−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneSecondBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right" ${_placementOffsetControlAttrs(zone, 'second_base')}>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternOffset(${i}, 'X', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'second_base')}>+</button>
                        <span class="stack-val" id="detSBPatPosXVal${i}" ${_placementOffsetValueAttrs(zone, 'second_base')}>${Math.round((zone.secondBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternOffset(${i}, 'Y', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'second_base')}>−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneSecondBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down" ${_placementOffsetControlAttrs(zone, 'second_base')}>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternOffset(${i}, 'Y', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'second_base')}>+</button>
                        <span class="stack-val" id="detSBPatPosYVal${i}" ${_placementOffsetValueAttrs(zone, 'second_base')}>${Math.round((zone.secondBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group" style="margin-top:6px;">
                        <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); alignSecondBaseOverlayWithSelectedPattern(${i})" title="Copy primary pattern position, scale, and rotation so the 2nd overlay lines up exactly (e.g. after you moved/resized the pattern on the map)">
                            ✓ Align with selected pattern
                        </button>
                    </div>
                    <div class="hsb-controls" style="margin-top:6px;border-top:1px solid #333;padding-top:4px;">
                        <div style="color:#aaa;font-size:10px;font-weight:bold;margin-bottom:3px;">Pattern Reaction HSB</div>
                        <div class="stack-control-group" style="margin-bottom:2px;">
                            <span class="stack-label-mini" style="min-width:28px;">Hue</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); zones[${i}].secondBasePatternHueShift=Math.max(-180,(zones[${i}].secondBasePatternHueShift||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                            <input type="range" min="-180" max="180" step="5" value="${zone.secondBasePatternHueShift || 0}"
                                oninput="pushZoneUndo('', true); zones[${i}].secondBasePatternHueShift=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value+'°'; renderZones(); triggerPreviewRender();"
                                class="stack-slider" title="Shift pattern reaction colors (-180° to +180°), drag=5° steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); zones[${i}].secondBasePatternHueShift=Math.min(180,(zones[${i}].secondBasePatternHueShift||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                            <span class="stack-val" style="min-width:35px;">${zone.secondBasePatternHueShift || 0}°</span>
                        </div>
                        <div class="stack-control-group" style="margin-bottom:2px;">
                            <span class="stack-label-mini" style="min-width:28px;">Sat</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); zones[${i}].secondBasePatternSaturation=Math.max(-100,(zones[${i}].secondBasePatternSaturation||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                            <input type="range" min="-100" max="100" step="5" value="${zone.secondBasePatternSaturation || 0}"
                                oninput="pushZoneUndo('', true); zones[${i}].secondBasePatternSaturation=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                                class="stack-slider" title="Adjust pattern reaction saturation (-100 to +100), drag=5 steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); zones[${i}].secondBasePatternSaturation=Math.min(100,(zones[${i}].secondBasePatternSaturation||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                            <span class="stack-val" style="min-width:35px;">${zone.secondBasePatternSaturation || 0}</span>
                        </div>
                        <div class="stack-control-group" style="margin-bottom:2px;">
                            <span class="stack-label-mini" style="min-width:28px;">Brt</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); zones[${i}].secondBasePatternBrightness=Math.max(-100,(zones[${i}].secondBasePatternBrightness||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                            <input type="range" min="-100" max="100" step="5" value="${zone.secondBasePatternBrightness || 0}"
                                oninput="pushZoneUndo('', true); zones[${i}].secondBasePatternBrightness=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                                class="stack-slider" title="Adjust pattern reaction brightness (-100 to +100), drag=5 steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); zones[${i}].secondBasePatternBrightness=Math.min(100,(zones[${i}].secondBasePatternBrightness||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                            <span class="stack-val" style="min-width:35px;">${zone.secondBasePatternBrightness || 0}</span>
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
        </div>`;

        // 3rd Base Overlay (rollback: server omits when ENABLE_THIRD_BASE_OVERLAY=False)
        html += `<div class="base-overlay-section overlay-section" style="margin-top:6px;">
            <div class="base-overlay-header" style="background:var(--bg-card,#16162a);padding:4px 8px;border-radius:4px;border:1px solid var(--border,#2a2a4a);">
                <span class="stack-label-mini">3rd Base Overlay</span>
                ${(zone.thirdBase || zone.thirdBaseColorSource) ? `<span style="font-size:9px;margin-left:auto;color:#a78bfa;">● ACTIVE</span>` : ''}
            </div>
            <div style="padding:4px 8px;">
                <div class="stack-control-group">
                    <span class="stack-label-mini">3rd Base</span>
                    <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'thirdBase', ${i})" title="Click to pick 3rd base (thumbnail preview)">
                        ${(zone.thirdBase || zone.thirdBaseColorSource) ? renderSwatchDot(zone.thirdBase || zone.thirdBaseColorSource, (getOverlayBaseDisplay(zone.thirdBase || zone.thirdBaseColorSource) || {}).swatch || '#888', zone.thirdBaseColor || '#ffffff') : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                        <span class="swatch-name">${(zone.thirdBase || zone.thirdBaseColorSource) ? (getOverlayBaseDisplay(zone.thirdBase || zone.thirdBaseColorSource) || {}).name || (zone.thirdBase || zone.thirdBaseColorSource) : '- None -'}</span>
                        <span class="swatch-arrow">&#9662;</span>
                    </div>
                    ${(zone.thirdBase || zone.thirdBaseColorSource) ? `<button class="btn btn-sm" onclick="event.stopPropagation(); setZoneThirdBase(${i}, ''); setZoneThirdBaseColorSource(${i}, null)" title="Remove 3rd overlay" style="padding:0px 5px;font-size:9px;line-height:1.2;margin-left:4px;">✕</button>` : ''}
                </div>
                ${(zone.thirdBase || zone.thirdBaseColorSource) ? `
                <div class="stack-control-group" style="margin-top:4px;flex-wrap:wrap;gap:6px 10px;">
                    <span class="stack-label-mini">Overlay Color</span>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="tbColorSource${i}" value="solid" ${!zone.thirdBaseColorSource || zone.thirdBaseColorSource === 'solid' ? 'checked' : ''} onchange="setZoneThirdBaseColorSource(${i}, 'solid')"><span>Solid</span></label>
                    <span style="display:flex;align-items:center;gap:4px;"><input type="color" value="${zone.thirdBaseColor || '#ffffff'}" onchange="setZoneThirdBaseColor(${i}, this.value)" style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                    <input type="text" value="${zone.thirdBaseColor || '#ffffff'}" onchange="setZoneThirdBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color"><input type="radio" name="tbColorSource${i}" value="overlay" ${zone.thirdBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneThirdBaseColorSourceToOverlay(${i})"><span>Same as overlay</span></label>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="tbColorSource${i}" value="special" ${zone.thirdBaseColorSource && zone.thirdBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'third' }; setZoneThirdBaseColorSource(${i}, '${(zone.thirdBaseColorSource && zone.thirdBaseColorSource.startsWith('mono:') ? zone.thirdBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')"><span>From special</span></label>
                    ${zone.thirdBaseColorSource && zone.thirdBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'third') : ''}
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBaseStrength || 0) * 100)}"
                        oninput="setZoneThirdBaseStrength(${i}, this.value)"
                        class="stack-slider" title="3rd overlay strength, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detTBStrVal${i}">${Math.round((zone.thirdBaseStrength || 0) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini" title="Blend-amount for this OVERLAY's spec onto the primary base: 100% = overlay reaches its full M/R/CC where it shows; 50% = overlay contributes in roughly half the pixels with reduced intensity; 0% = overlay is fully suppressed (primary base alone shows). Unlike the primary Spec Strength this is layer-opacity semantics, not material-weakening.">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneThirdBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detTBSpecStrVal${i}">${Math.round((zone.thirdBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
                <div class="hsb-controls" style="margin-top:6px;border-top:1px solid #333;padding-top:4px;">
                    <div style="color:#aaa;font-size:10px;font-weight:bold;margin-bottom:3px;">Overlay HSB Adjust</div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Hue</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].thirdBaseHueShift=Math.max(-180,(zones[${i}].thirdBaseHueShift||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-180" max="180" step="5" value="${zone.thirdBaseHueShift || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].thirdBaseHueShift=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value+'°'; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Shift overlay colors (-180° to +180°), drag=5° steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].thirdBaseHueShift=Math.min(180,(zones[${i}].thirdBaseHueShift||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.thirdBaseHueShift || 0}°</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Sat</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].thirdBaseSaturation=Math.max(-100,(zones[${i}].thirdBaseSaturation||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.thirdBaseSaturation || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].thirdBaseSaturation=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay saturation (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].thirdBaseSaturation=Math.min(100,(zones[${i}].thirdBaseSaturation||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.thirdBaseSaturation || 0}</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Brt</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].thirdBaseBrightness=Math.max(-100,(zones[${i}].thirdBaseBrightness||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.thirdBaseBrightness || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].thirdBaseBrightness=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay brightness (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].thirdBaseBrightness=Math.min(100,(zones[${i}].thirdBaseBrightness||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.thirdBaseBrightness || 0}</span>
                    </div>
                </div>
                ${(zone.thirdBase || zone.thirdBaseColorSource) ? (() => {
                    const thirdOvSpecStack = zone.thirdOverlaySpecPatternStack || [];
                    const thirdOvSpecStackActive = thirdOvSpecStack.length > 0;
                    const MAX_OVERLAY_SPEC_PATTERN_LAYERS = 5;
                    let thirdOvSpHtml = `<div class="overlay-spec-patterns" style="border-top:1px solid #c084fc33;margin-top:6px;padding-top:6px;">
                        <div style="color:#c084fc;font-size:10px;margin-bottom:4px;">
                            &#9670; Overlay Spec Patterns
                            <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">spec overlays for 3rd base</span>
                            ${thirdOvSpecStackActive ? '<span style="font-size:9px;margin-left:auto;color:#c084fc;">&#9679; ACTIVE (' + thirdOvSpecStack.length + ')</span>' : ''}
                        </div>`;

                    thirdOvSpecStack.forEach((sp, si) => {
                        const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === sp.pattern);
                        const spName = spDef ? spDef.name : (sp.pattern || '???');
                        const chM = (sp.channels || 'MR').includes('M');
                        const chR = (sp.channels || 'MR').includes('R');
                        const chCC = (sp.channels || 'MR').includes('CC');
                        thirdOvSpHtml += `<div style="margin-bottom:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                            <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                                <span style="font-size:10px; color:#c084fc; font-weight:bold;">${si + 1}.</span>
                                <span style="font-size:10px; color:var(--text);">${spName}</span>
                                <span style="font-size:8px; color:var(--text-dim);">${spDef ? spDef.desc : ''}</span>
                                <button class="btn btn-sm" onclick="event.stopPropagation(); removeThirdOverlaySpecPatternLayer(${i}, ${si})" title="Remove" style="margin-left:auto; padding:0px 5px; font-size:9px; line-height:1.2;">&times;</button>
                            </div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center;">
                                <div class="stack-control-group" style="flex:1; min-width:100px;">
                                    <span class="stack-label-mini">Opacity</span>
                                    <input type="range" min="0" max="100" step="5" value="${sp.opacity ?? 50}"
                                        oninput="setThirdOverlaySpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value)); this.nextElementSibling.textContent=this.value+'%'"
                                        class="stack-slider" title="Opacity (5% steps)">
                                    <span class="stack-val">${sp.opacity ?? 50}%</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Range</span>
                                    <input type="range" min="1" max="100" step="1" value="${sp.range || 40}"
                                        oninput="setThirdOverlaySpecPatternLayerProp(${i}, ${si}, 'range', parseInt(this.value)); this.nextElementSibling.textContent=this.value"
                                        class="stack-slider" title="Range (1-100)">
                                    <span class="stack-val">${sp.range || 40}</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Scale</span>
                                    <input type="range" min="5" max="400" step="5" value="${Math.round((sp.scale || 1) * 100)}"
                                        oninput="setThirdOverlaySpecPatternLayerProp(${i}, ${si}, 'scale', this.value/100); this.nextElementSibling.textContent=this.value+'%'; renderZones(); triggerPreviewRender();"
                                        class="stack-slider" title="Spec pattern scale — 100% = default">
                                    <span class="stack-val">${Math.round((sp.scale || 1) * 100)}%</span>
                                </div>
                                <div class="stack-control-group" style="min-width:80px;">
                                    <span class="stack-label-mini">Blend</span>
                                    <select onchange="setThirdOverlaySpecPatternLayerProp(${i}, ${si}, 'blendMode', this.value)"
                                        style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                        <option value="normal"${(sp.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                        <option value="multiply"${sp.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                        <option value="screen"${sp.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                        <option value="overlay"${sp.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                                        <option value="hardlight"${sp.blendMode === 'hardlight' ? ' selected' : ''}>Hard Light</option>
                                        <option value="softlight"${sp.blendMode === 'softlight' ? ' selected' : ''}>Soft Light</option>
                                    </select>
                                </div>
                                <div class="stack-control-group" style="min-width:100px;">
                                    <span class="stack-label-mini">Channels</span>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chM ? 'checked' : ''} onchange="toggleThirdOverlaySpecPatternChannel(${i}, ${si}, 'M', this.checked)"> M</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chR ? 'checked' : ''} onchange="toggleThirdOverlaySpecPatternChannel(${i}, ${si}, 'R', this.checked)"> R</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chCC ? 'checked' : ''} onchange="toggleThirdOverlaySpecPatternChannel(${i}, ${si}, 'CC', this.checked)"> CC</label>
                                </div>
                            </div>
                        </div>`;
                    });

                    if (thirdOvSpecStack.length < MAX_OVERLAY_SPEC_PATTERN_LAYERS) {
                        const _spg3 = typeof SPEC_PATTERN_GROUPS !== 'undefined' ? SPEC_PATTERN_GROUPS : {};
                        const _spgMap3 = {};
                        Object.entries(_spg3).forEach(([g, ids]) => ids.forEach(id => { _spgMap3[id] = g; }));
                        const _tabBtns3 = ['All', ...Object.keys(_spg3)].map(g =>
                            `<button class="spec-cat-tab${g==='All'?' active':''}" data-cat="${g}" onclick="specPickerCatTab('thirdOverlaySpecPatternGrid${i}',this,'${g.replace(/'/g,'\\\'')}')" title="${g}">${g}</button>`
                        ).join('');
                        thirdOvSpHtml += `<div style="margin-top:4px;">
                            <div id="thirdOverlaySpecPatternGrid${i}_tabs" class="spec-cat-tab-row" style="display:none;">${_tabBtns3}</div>
                            <div id="thirdOverlaySpecPatternGrid${i}" style="display:none; max-height:220px; overflow-y:auto; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;" class="spec-pattern-grid spec-pattern-grid-4col">`;
                        (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                            const _sg3 = _spgMap3[sp.id] || 'Misc';
                            const _shortName3 = sp.name.length > 12 ? sp.name.slice(0,12)+'…' : sp.name;
                            thirdOvSpHtml += `<div class="spec-pattern-thumb-card" data-category="${_sg3}"
                                onclick="if(this._spPopup){this._spPopup.remove();this._spPopup=null;} document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); var _og=document.getElementById('thirdOverlaySpecPatternGrid${i}'); var _ogt=document.getElementById('thirdOverlaySpecPatternGrid${i}_tabs'); if(_og){_og.style.display='none';} if(_ogt){_ogt.style.display='none';} addThirdOverlaySpecPatternLayer(${i}, '${sp.id}');"
                                title="${sp.name}: ${sp.desc}"
                                onmouseenter="(function(el){var img=el.querySelector('img');if(!img)return;var popup=document.createElement('div');popup.className='spec-thumb-popup';popup.innerHTML='<img src=\\''+img.src+'\\' style=\\'width:200px;height:100px;object-fit:contain;\\'><div style=\\'text-align:center;font-size:11px;color:#ccc;padding:4px;\\'>${sp.name.replace(/'/g,'&#39;')}</div>';var rect=el.getBoundingClientRect();popup.style.left=Math.min(rect.left+rect.width/2-104, window.innerWidth-260)+'px';popup.style.top=Math.max(rect.top-140,4)+'px';document.body.appendChild(popup);el._spPopup=popup;})(this)"
                                onmouseleave="if(this._spPopup){this._spPopup.remove();this._spPopup=null;}">
                                <img src="/thumbnails/spec_patterns/${sp.id}.png" alt="${sp.name}" loading="eager" style="width:48px;height:48px;object-fit:cover;" onerror="this.src='/api/spec-pattern-preview/${sp.id}?v=live';this.onerror=null;">
                                <div class="thumb-label">${_shortName3}</div>
                            </div>`;
                        });
                        thirdOvSpHtml += `</div>
                            <button onclick="document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); const g=document.getElementById('thirdOverlaySpecPatternGrid${i}'); const t=document.getElementById('thirdOverlaySpecPatternGrid${i}_tabs'); const show=!g.style.display||g.style.display==='none'; if(show){g.style.display='grid';g.style.gridTemplateColumns='repeat(4,1fr)';g.style.gap='6px';g.style.padding='6px';if(t)t.style.display='flex';}else{g.style.display='none';if(t)t.style.display='none';}" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #c084fc44; color:#c084fc; margin-top:4px;">
                                + Add Overlay Spec Pattern (click to browse)
                            </button>
                        </div>`;
                    } else {
                        thirdOvSpHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 5 overlay spec pattern layers reached.</div>';
                    }

                    thirdOvSpHtml += `</div>`;
                    return thirdOvSpHtml;
                })() : ''}
                <div class="stack-control-group" style="margin-top:4px;align-items:flex-start;">
                    <span class="stack-label-mini" style="padding-top:2px;">Blend Mode</span>
                    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="tbBlendMode${i}" value="noise" ${['noise', 'dust'].includes(zone.thirdBaseBlendMode || 'noise') ? 'checked' : ''}
                                onchange="setZoneThirdBaseBlendMode(${i}, 'noise')">
                            <span>✨ Fractal Dust</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="tbBlendMode${i}" value="marble" ${zone.thirdBaseBlendMode === 'marble' ? 'checked' : ''}
                                onchange="setZoneThirdBaseBlendMode(${i}, 'marble')">
                            <span>🌪️ Liquid Swirl</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern-edges" ${['pattern-edges', 'uniform'].includes(zone.thirdBaseBlendMode || '') ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern-edges')"><span>📐 Pattern Edges</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern" ${zone.thirdBaseBlendMode === 'pattern' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern')"><span>🔷 Pattern-Reactive</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern-vivid" ${zone.thirdBaseBlendMode === 'pattern-vivid' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern-vivid')"><span>💥 Pattern-Pop <span style="font-size:8px;color:var(--text-dim);">full color</span></span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="tint" ${(zone.thirdBaseBlendMode || '') === 'tint' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'tint')"><span>🎨 Tint (subtle)</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern-peaks" ${zone.thirdBaseBlendMode === 'pattern-peaks' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern-peaks')"><span>⛰️ Pattern Peaks</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern-contour" ${zone.thirdBaseBlendMode === 'pattern-contour' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern-contour')"><span>〰️ Pattern Contour</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern-screen" ${zone.thirdBaseBlendMode === 'pattern-screen' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern-screen')"><span>✨ Pattern Screen</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="tbBlendMode${i}" value="pattern-threshold" ${zone.thirdBaseBlendMode === 'pattern-threshold' ? 'checked' : ''} onchange="setZoneThirdBaseBlendMode(${i}, 'pattern-threshold')"><span>◐ Pattern Threshold</span></label>
                    </div>
                </div>
                ${['noise', 'dust', 'marble'].includes(zone.thirdBaseBlendMode || 'noise') ? `
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Fractal Detail</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseFractalScale(${i}, -1)" title="-4px" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="4" max="128" step="4" value="${zone.thirdBaseFractalScale || 24}"
                        oninput="setZoneThirdBaseFractalScale(${i}, this.value)"
                        class="stack-slider" title="Fractal Detail">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseFractalScale(${i}, 1)" title="+4px" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detTBNSVal${i}">${zone.thirdBaseFractalScale || 24}px</span>
                </div>` : ''}
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Overlay Scale</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="10" max="500" step="5" value="${Math.min(500, Math.max(10, Math.round((zone.thirdBaseScale ?? 1) * 100)))}"
                        oninput="setZoneThirdBaseScale(${i}, parseFloat(this.value)/100)"
                        class="stack-slider" title="5% steps (Fractal/Dust only)">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detTBScaleVal${i}">${(zone.thirdBaseScale ?? 1).toFixed(2)}</span>
                </div>
                <div class="stack-control-group" style="margin-top:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                    <span class="stack-label-mini" style="margin-bottom:4px;">React to zone pattern</span>
                    <p style="font-size:9px;color:var(--text-dim);margin:0 0 6px 0;">All blend modes use the selected pattern (Invert, Harden, Opacity, Scale, Rotate, Strength, Position).</p>
                    <div class="stack-control-group" style="margin-bottom:6px;">
                        <label class="stack-label-mini">React to</label>
                        <select onchange="setZoneThirdBasePattern(${i}, this.value)" style="font-size:10px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;min-width:140px;">
                            ${(function () { const opts = getZonePatternReactOptions(zone); let sel = getOverlayReactToSelectValue(zone, zone.thirdBasePattern); if (!opts.some(o => o.value === sel)) sel = ''; return opts.map(o => `<option value="${(o.value === '' ? '' : o.value)}" ${sel === o.value ? 'selected' : ''}>${o.label}</option>`).join(''); })()}
                        </select>
                    </div>
                    <div class="stack-control-group" style="flex-wrap:wrap;gap:8px 12px;">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.thirdBasePatternInvert || false) ? 'checked' : ''} onchange="setZoneThirdBasePatternInvert(${i}, this.checked)"> Invert mask (color background)</label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.thirdBasePatternHarden || false) ? 'checked' : ''} onchange="setZoneThirdBasePatternHarden(${i}, this.checked)"> Harden (only in pattern)</label>
                    </div>
                    <div class="stack-control-group"><span class="stack-label-mini">Opacity</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternOpacity(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="100" step="5" value="${zone.thirdBasePatternOpacity ?? 100}" oninput="setZoneThirdBasePatternOpacity(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternOpacity(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detTBPatOpVal${i}">${zone.thirdBasePatternOpacity ?? 100}%</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Scale</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="10" max="400" step="5" value="${Math.round((zone.thirdBasePatternScale ?? 1.0) * 100)}" oninput="setZoneThirdBasePatternScale(${i}, parseFloat(this.value)/100)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detTBPatScaleVal${i}">${(zone.thirdBasePatternScale ?? 1.0).toFixed(2)}x</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Rotate</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternRotation(${i}, -1)" title="-5°" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="359" step="5" value="${zone.thirdBasePatternRotation ?? 0}" id="detTBPatRotRange${i}" oninput="setZoneThirdBasePatternRotation(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternRotation(${i}, 1)" title="+5°" style="padding:0 4px;font-size:10px;">+</button>
                        <input type="number" min="0" max="359" value="${zone.thirdBasePatternRotation ?? 0}" onchange="setZoneThirdBasePatternRotation(${i}, this.value)" id="detTBPatRotVal${i}" style="width:42px;font-size:10px;text-align:center;padding:1px 2px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:3px;"> <span style="font-size:10px;color:var(--text-dim);">°</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBasePatternStrength ?? 1) * 100)}" oninput="setZoneThirdBasePatternStrength(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detTBPatStrVal${i}">${Math.round((zone.thirdBasePatternStrength ?? 1) * 100)}%</span></div>
                    ${renderPlacementModeControls(i, 'third_base', { label: 'Overlay placement', targetLabel: 'the 3rd base overlay', allowFit: true, centeredLabel: 'Centered + Numeric' })}
                    <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'third', 'X', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'third_base')}>−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneThirdBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right" ${_placementOffsetControlAttrs(zone, 'third_base')}>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'third', 'X', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'third_base')}>+</button>
                        <span class="stack-val" id="detTBPatPosXVal${i}" ${_placementOffsetValueAttrs(zone, 'third_base')}>${Math.round((zone.thirdBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'third', 'Y', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'third_base')}>−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneThirdBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down" ${_placementOffsetControlAttrs(zone, 'third_base')}>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'third', 'Y', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'third_base')}>+</button>
                        <span class="stack-val" id="detTBPatPosYVal${i}" ${_placementOffsetValueAttrs(zone, 'third_base')}>${Math.round((zone.thirdBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group" style="margin-top:6px;">
                        <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); alignThirdBaseOverlayWithSelectedPattern(${i})" title="Copy primary pattern position, scale, and rotation so the 3rd overlay lines up exactly">
                            ✓ Align with selected pattern
                        </button>
                    </div>
                </div>
                ` : ''}
                <!-- 4th Base Overlay (same structure as 2nd/3rd) -->
                <div class="base-overlay-section overlay-section" style="margin-top:6px;">
                    <div class="base-overlay-header" style="background:var(--bg-card,#16162a);padding:4px 8px;border-radius:4px;border:1px solid var(--border,#2a2a4a);">
                        <span class="stack-label-mini">4th Base Overlay</span>
                        ${(zone.fourthBase || zone.fourthBaseColorSource) ? `<span style="font-size:9px;margin-left:auto;color:#a78bfa;">● ACTIVE</span>` : ''}
                    </div>
                    <div style="padding:4px 8px;">
                        <div class="stack-control-group">
                            <span class="stack-label-mini">4th Base</span>
                            <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'fourthBase', ${i})" title="Click to pick 4th base">
                                ${(zone.fourthBase || zone.fourthBaseColorSource) ? renderSwatchDot(zone.fourthBase || zone.fourthBaseColorSource, (getOverlayBaseDisplay(zone.fourthBase || zone.fourthBaseColorSource) || {}).swatch || '#888', zone.fourthBaseColor || '#ffffff') : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                                <span class="swatch-name">${(zone.fourthBase || zone.fourthBaseColorSource) ? (getOverlayBaseDisplay(zone.fourthBase || zone.fourthBaseColorSource) || {}).name || (zone.fourthBase || zone.fourthBaseColorSource) : '- None -'}</span>
                                <span class="swatch-arrow">&#9662;</span>
                            </div>
                            ${(zone.fourthBase || zone.fourthBaseColorSource) ? `<button class="btn btn-sm" onclick="event.stopPropagation(); setZoneFourthBase(${i}, ''); setZoneFourthBaseColorSource(${i}, null)" title="Remove 4th overlay" style="padding:0px 5px;font-size:9px;line-height:1.2;margin-left:4px;">✕</button>` : ''}
                        </div>
                        ${(zone.fourthBase || zone.fourthBaseColorSource) ? `
                        <div class="stack-control-group" style="margin-top:4px;flex-wrap:wrap;gap:6px 10px;">
                            <span class="stack-label-mini">Overlay Color</span>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fbColorSource${i}" value="solid" ${!zone.fourthBaseColorSource || zone.fourthBaseColorSource === 'solid' ? 'checked' : ''} onchange="setZoneFourthBaseColorSource(${i}, 'solid')"><span>Solid</span></label>
                            <span style="display:flex;align-items:center;gap:4px;"><input type="color" value="${zone.fourthBaseColor || '#ffffff'}" onchange="setZoneFourthBaseColor(${i}, this.value)" style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                            <input type="text" value="${zone.fourthBaseColor || '#ffffff'}" onchange="setZoneFourthBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color"><input type="radio" name="fbColorSource${i}" value="overlay" ${zone.fourthBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneFourthBaseColorSourceToOverlay(${i})"><span>Same as overlay</span></label>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fbColorSource${i}" value="special" ${zone.fourthBaseColorSource && zone.fourthBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'fourth' }; setZoneFourthBaseColorSource(${i}, '${(zone.fourthBaseColorSource && zone.fourthBaseColorSource.startsWith('mono:') ? zone.fourthBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')"><span>From special</span></label>
                            ${zone.fourthBaseColorSource && zone.fourthBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'fourth') : ''}
                        </div>
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBaseStrength || 0) * 100)}" oninput="setZoneFourthBaseStrength(${i}, this.value)" class="stack-slider" title="4th overlay strength, 5% steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFBStrVal${i}">${Math.round((zone.fourthBaseStrength || 0) * 100)}%</span>
                        </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini" title="Blend-amount for this OVERLAY's spec onto the primary base: 100% = overlay reaches its full M/R/CC where it shows; 50% = overlay contributes in roughly half the pixels with reduced intensity; 0% = overlay is fully suppressed (primary base alone shows). Unlike the primary Spec Strength this is layer-opacity semantics, not material-weakening.">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneFourthBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detFBSpecStrVal${i}">${Math.round((zone.fourthBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
                <div class="hsb-controls" style="margin-top:6px;border-top:1px solid #333;padding-top:4px;">
                    <div style="color:#aaa;font-size:10px;font-weight:bold;margin-bottom:3px;">Overlay HSB Adjust</div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Hue</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fourthBaseHueShift=Math.max(-180,(zones[${i}].fourthBaseHueShift||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-180" max="180" step="5" value="${zone.fourthBaseHueShift || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].fourthBaseHueShift=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value+'°'; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Shift overlay colors (-180° to +180°), drag=5° steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fourthBaseHueShift=Math.min(180,(zones[${i}].fourthBaseHueShift||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.fourthBaseHueShift || 0}°</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Sat</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fourthBaseSaturation=Math.max(-100,(zones[${i}].fourthBaseSaturation||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.fourthBaseSaturation || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].fourthBaseSaturation=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay saturation (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fourthBaseSaturation=Math.min(100,(zones[${i}].fourthBaseSaturation||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.fourthBaseSaturation || 0}</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Brt</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fourthBaseBrightness=Math.max(-100,(zones[${i}].fourthBaseBrightness||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.fourthBaseBrightness || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].fourthBaseBrightness=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay brightness (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fourthBaseBrightness=Math.min(100,(zones[${i}].fourthBaseBrightness||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.fourthBaseBrightness || 0}</span>
                    </div>
                </div>
                ${(zone.fourthBase || zone.fourthBaseColorSource) ? (() => {
                    const fourthOvSpecStack = zone.fourthOverlaySpecPatternStack || [];
                    const fourthOvSpecStackActive = fourthOvSpecStack.length > 0;
                    const MAX_OVERLAY_SPEC_PATTERN_LAYERS = 5;
                    let fourthOvSpHtml = `<div class="overlay-spec-patterns" style="border-top:1px solid #c084fc33;margin-top:6px;padding-top:6px;">
                        <div style="color:#c084fc;font-size:10px;margin-bottom:4px;">
                            &#9670; Overlay Spec Patterns
                            <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">spec overlays for 4th base</span>
                            ${fourthOvSpecStackActive ? '<span style="font-size:9px;margin-left:auto;color:#c084fc;">&#9679; ACTIVE (' + fourthOvSpecStack.length + ')</span>' : ''}
                        </div>`;

                    fourthOvSpecStack.forEach((sp, si) => {
                        const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === sp.pattern);
                        const spName = spDef ? spDef.name : (sp.pattern || '???');
                        const chM = (sp.channels || 'MR').includes('M');
                        const chR = (sp.channels || 'MR').includes('R');
                        const chCC = (sp.channels || 'MR').includes('CC');
                        fourthOvSpHtml += `<div style="margin-bottom:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                            <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                                <span style="font-size:10px; color:#c084fc; font-weight:bold;">${si + 1}.</span>
                                <span style="font-size:10px; color:var(--text);">${spName}</span>
                                <span style="font-size:8px; color:var(--text-dim);">${spDef ? spDef.desc : ''}</span>
                                <button class="btn btn-sm" onclick="event.stopPropagation(); removeFourthOverlaySpecPatternLayer(${i}, ${si})" title="Remove" style="margin-left:auto; padding:0px 5px; font-size:9px; line-height:1.2;">&times;</button>
                            </div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center;">
                                <div class="stack-control-group" style="flex:1; min-width:100px;">
                                    <span class="stack-label-mini">Opacity</span>
                                    <input type="range" min="0" max="100" step="5" value="${sp.opacity ?? 50}"
                                        oninput="setFourthOverlaySpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value)); this.nextElementSibling.textContent=this.value+'%'"
                                        class="stack-slider" title="Opacity (5% steps)">
                                    <span class="stack-val">${sp.opacity ?? 50}%</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Range</span>
                                    <input type="range" min="1" max="100" step="1" value="${sp.range || 40}"
                                        oninput="setFourthOverlaySpecPatternLayerProp(${i}, ${si}, 'range', parseInt(this.value)); this.nextElementSibling.textContent=this.value"
                                        class="stack-slider" title="Range (1-100)">
                                    <span class="stack-val">${sp.range || 40}</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Scale</span>
                                    <input type="range" min="5" max="400" step="5" value="${Math.round((sp.scale || 1) * 100)}"
                                        oninput="setFourthOverlaySpecPatternLayerProp(${i}, ${si}, 'scale', this.value/100); this.nextElementSibling.textContent=this.value+'%'; renderZones(); triggerPreviewRender();"
                                        class="stack-slider" title="Spec pattern scale — 100% = default">
                                    <span class="stack-val">${Math.round((sp.scale || 1) * 100)}%</span>
                                </div>
                                <div class="stack-control-group" style="min-width:80px;">
                                    <span class="stack-label-mini">Blend</span>
                                    <select onchange="setFourthOverlaySpecPatternLayerProp(${i}, ${si}, 'blendMode', this.value)"
                                        style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                        <option value="normal"${(sp.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                        <option value="multiply"${sp.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                        <option value="screen"${sp.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                        <option value="overlay"${sp.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                                        <option value="hardlight"${sp.blendMode === 'hardlight' ? ' selected' : ''}>Hard Light</option>
                                        <option value="softlight"${sp.blendMode === 'softlight' ? ' selected' : ''}>Soft Light</option>
                                    </select>
                                </div>
                                <div class="stack-control-group" style="min-width:100px;">
                                    <span class="stack-label-mini">Channels</span>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chM ? 'checked' : ''} onchange="toggleFourthOverlaySpecPatternChannel(${i}, ${si}, 'M', this.checked)"> M</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chR ? 'checked' : ''} onchange="toggleFourthOverlaySpecPatternChannel(${i}, ${si}, 'R', this.checked)"> R</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chCC ? 'checked' : ''} onchange="toggleFourthOverlaySpecPatternChannel(${i}, ${si}, 'CC', this.checked)"> CC</label>
                                </div>
                            </div>
                        </div>`;
                    });

                    if (fourthOvSpecStack.length < MAX_OVERLAY_SPEC_PATTERN_LAYERS) {
                        const _spg4 = typeof SPEC_PATTERN_GROUPS !== 'undefined' ? SPEC_PATTERN_GROUPS : {};
                        const _spgMap4 = {};
                        Object.entries(_spg4).forEach(([g, ids]) => ids.forEach(id => { _spgMap4[id] = g; }));
                        const _tabBtns4 = ['All', ...Object.keys(_spg4)].map(g =>
                            `<button class="spec-cat-tab${g==='All'?' active':''}" data-cat="${g}" onclick="specPickerCatTab('fourthOverlaySpecPatternGrid${i}',this,'${g.replace(/'/g,'\\\'')}')" title="${g}">${g}</button>`
                        ).join('');
                        fourthOvSpHtml += `<div style="margin-top:4px;">
                            <div id="fourthOverlaySpecPatternGrid${i}_tabs" class="spec-cat-tab-row" style="display:none;">${_tabBtns4}</div>
                            <div id="fourthOverlaySpecPatternGrid${i}" style="display:none; max-height:220px; overflow-y:auto; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;" class="spec-pattern-grid spec-pattern-grid-4col">`;
                        (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                            const _sg4 = _spgMap4[sp.id] || 'Misc';
                            const _shortName4 = sp.name.length > 12 ? sp.name.slice(0,12)+'…' : sp.name;
                            fourthOvSpHtml += `<div class="spec-pattern-thumb-card" data-category="${_sg4}"
                                onclick="if(this._spPopup){this._spPopup.remove();this._spPopup=null;} document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); var _og=document.getElementById('fourthOverlaySpecPatternGrid${i}'); var _ogt=document.getElementById('fourthOverlaySpecPatternGrid${i}_tabs'); if(_og){_og.style.display='none';} if(_ogt){_ogt.style.display='none';} addFourthOverlaySpecPatternLayer(${i}, '${sp.id}');"
                                title="${sp.name}: ${sp.desc}"
                                onmouseenter="(function(el){var img=el.querySelector('img');if(!img)return;var popup=document.createElement('div');popup.className='spec-thumb-popup';popup.innerHTML='<img src=\\''+img.src+'\\' style=\\'width:200px;height:100px;object-fit:contain;\\'><div style=\\'text-align:center;font-size:11px;color:#ccc;padding:4px;\\'>${sp.name.replace(/'/g,'&#39;')}</div>';var rect=el.getBoundingClientRect();popup.style.left=Math.min(rect.left+rect.width/2-104, window.innerWidth-260)+'px';popup.style.top=Math.max(rect.top-140,4)+'px';document.body.appendChild(popup);el._spPopup=popup;})(this)"
                                onmouseleave="if(this._spPopup){this._spPopup.remove();this._spPopup=null;}">
                                <img src="/thumbnails/spec_patterns/${sp.id}.png" alt="${sp.name}" loading="eager" style="width:48px;height:48px;object-fit:cover;" onerror="this.src='/api/spec-pattern-preview/${sp.id}?v=live';this.onerror=null;">
                                <div class="thumb-label">${_shortName4}</div>
                            </div>`;
                        });
                        fourthOvSpHtml += `</div>
                            <button onclick="document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); const g=document.getElementById('fourthOverlaySpecPatternGrid${i}'); const t=document.getElementById('fourthOverlaySpecPatternGrid${i}_tabs'); const show=!g.style.display||g.style.display==='none'; if(show){g.style.display='grid';g.style.gridTemplateColumns='repeat(4,1fr)';g.style.gap='6px';g.style.padding='6px';if(t)t.style.display='flex';}else{g.style.display='none';if(t)t.style.display='none';}" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #c084fc44; color:#c084fc; margin-top:4px;">
                                + Add Overlay Spec Pattern (click to browse)
                            </button>
                        </div>`;
                    } else {
                        fourthOvSpHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 5 overlay spec pattern layers reached.</div>';
                    }

                    fourthOvSpHtml += `</div>`;
                    return fourthOvSpHtml;
                })() : ''}
                        <div class="stack-control-group" style="margin-top:4px;align-items:flex-start;">
                            <span class="stack-label-mini" style="padding-top:2px;">Blend Mode</span>
                            <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="noise" ${['noise', 'dust'].includes(zone.fourthBaseBlendMode || 'noise') ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'noise')"><span>✨ Fractal Dust</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="marble" ${zone.fourthBaseBlendMode === 'marble' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'marble')"><span>🌪️ Liquid Swirl</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern-edges" ${['pattern-edges', 'uniform'].includes(zone.fourthBaseBlendMode || '') ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern-edges')"><span>📐 Pattern Edges</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern" ${zone.fourthBaseBlendMode === 'pattern' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern')"><span>🔷 Pattern-Reactive</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern-vivid" ${zone.fourthBaseBlendMode === 'pattern-vivid' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern-vivid')"><span>💥 Pattern-Pop <span style="font-size:8px;color:var(--text-dim);">full color</span></span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="tint" ${(zone.fourthBaseBlendMode || '') === 'tint' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'tint')"><span>🎨 Tint (subtle)</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern-peaks" ${zone.fourthBaseBlendMode === 'pattern-peaks' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern-peaks')"><span>⛰️ Pattern Peaks</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern-contour" ${zone.fourthBaseBlendMode === 'pattern-contour' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern-contour')"><span>〰️ Pattern Contour</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern-screen" ${zone.fourthBaseBlendMode === 'pattern-screen' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern-screen')"><span>✨ Pattern Screen</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fbBlendMode${i}" value="pattern-threshold" ${zone.fourthBaseBlendMode === 'pattern-threshold' ? 'checked' : ''} onchange="setZoneFourthBaseBlendMode(${i}, 'pattern-threshold')"><span>◐ Pattern Threshold</span></label>
                            </div>
                        </div>
                        ${['noise', 'dust', 'marble'].includes(zone.fourthBaseBlendMode || 'noise') ? `
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini">Fractal Detail</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseFractalScale(${i}, -1)" title="-4px" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="4" max="128" step="4" value="${zone.fourthBaseFractalScale || 24}" oninput="setZoneFourthBaseFractalScale(${i}, this.value)" class="stack-slider" title="Fractal Detail">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseFractalScale(${i}, 1)" title="+4px" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFBNSVal${i}">${zone.fourthBaseFractalScale || 24}px</span>
                        </div>` : ''}
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini">Overlay Scale</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="10" max="500" step="5" value="${Math.min(500, Math.max(10, Math.round((zone.fourthBaseScale ?? 1) * 100)))}" oninput="setZoneFourthBaseScale(${i}, parseFloat(this.value)/100)" class="stack-slider" title="5% steps (Fractal/Dust only)">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFBScaleVal${i}">${(zone.fourthBaseScale ?? 1).toFixed(2)}</span>
                        </div>
                        <div class="stack-control-group" style="margin-top:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                            <span class="stack-label-mini" style="margin-bottom:4px;">React to zone pattern</span>
                            <p style="font-size:9px;color:var(--text-dim);margin:0 0 6px 0;">All blend modes use the selected pattern (Invert, Harden, Opacity, Scale, Rotate, Strength, Position).</p>
                            <div class="stack-control-group" style="margin-bottom:6px;">
                                <label class="stack-label-mini">React to</label>
                                <select onchange="setZoneFourthBasePattern(${i}, this.value)" style="font-size:10px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;min-width:140px;">
                                    ${(function () { const opts = getZonePatternReactOptions(zone); let sel = getOverlayReactToSelectValue(zone, zone.fourthBasePattern); if (!opts.some(o => o.value === sel)) sel = ''; return opts.map(o => `<option value="${(o.value === '' ? '' : o.value)}" ${sel === o.value ? 'selected' : ''}>${o.label}</option>`).join(''); })()}
                                </select>
                            </div>
                            <div class="stack-control-group" style="flex-wrap:wrap;gap:8px 12px;">
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.fourthBasePatternInvert || false) ? 'checked' : ''} onchange="setZoneFourthBasePatternInvert(${i}, this.checked)"> Invert mask (color background)</label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.fourthBasePatternHarden || false) ? 'checked' : ''} onchange="setZoneFourthBasePatternHarden(${i}, this.checked)"> Harden (only in pattern)</label>
                            </div>
                            <div class="stack-control-group"><span class="stack-label-mini">Opacity</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternOpacity(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="100" step="5" value="${zone.fourthBasePatternOpacity ?? 100}" oninput="setZoneFourthBasePatternOpacity(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternOpacity(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFBPatOpVal${i}">${zone.fourthBasePatternOpacity ?? 100}%</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Scale</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="10" max="400" step="5" value="${Math.round((zone.fourthBasePatternScale ?? 1.0) * 100)}" oninput="setZoneFourthBasePatternScale(${i}, parseFloat(this.value)/100)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFBPatScaleVal${i}">${(zone.fourthBasePatternScale ?? 1.0).toFixed(2)}x</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Rotate</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternRotation(${i}, -1)" title="-5°" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="359" step="5" value="${zone.fourthBasePatternRotation ?? 0}" id="detFBPatRotRange${i}" oninput="setZoneFourthBasePatternRotation(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternRotation(${i}, 1)" title="+5°" style="padding:0 4px;font-size:10px;">+</button>
                                <input type="number" min="0" max="359" value="${zone.fourthBasePatternRotation ?? 0}" onchange="setZoneFourthBasePatternRotation(${i}, this.value)" id="detFBPatRotVal${i}" style="width:42px;font-size:10px;text-align:center;padding:1px 2px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:3px;"> <span style="font-size:10px;color:var(--text-dim);">°</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBasePatternStrength ?? 1) * 100)}" oninput="setZoneFourthBasePatternStrength(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFBPatStrVal${i}">${Math.round((zone.fourthBasePatternStrength ?? 1) * 100)}%</span></div>
                            ${renderPlacementModeControls(i, 'fourth_base', { label: 'Overlay placement', targetLabel: 'the 4th base overlay', allowFit: true, centeredLabel: 'Centered + Numeric' })}
                            <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fourth', 'X', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fourth_base')}>−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneFourthBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right" ${_placementOffsetControlAttrs(zone, 'fourth_base')}>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fourth', 'X', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fourth_base')}>+</button>
                                <span class="stack-val" id="detFBPatPosXVal${i}" ${_placementOffsetValueAttrs(zone, 'fourth_base')}>${Math.round((zone.fourthBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fourth', 'Y', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fourth_base')}>−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneFourthBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down" ${_placementOffsetControlAttrs(zone, 'fourth_base')}>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fourth', 'Y', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fourth_base')}>+</button>
                                <span class="stack-val" id="detFBPatPosYVal${i}" ${_placementOffsetValueAttrs(zone, 'fourth_base')}>${Math.round((zone.fourthBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
                            <div class="stack-control-group" style="margin-top:6px;">
                                <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); alignFourthBaseOverlayWithSelectedPattern(${i})" title="Copy primary pattern position, scale, and rotation so the 4th overlay lines up exactly">✓ Align with selected pattern</button>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                <!-- 5th Base Overlay (same structure as 2nd/3rd) -->
                <div class="base-overlay-section overlay-section" style="margin-top:6px;">
                    <div class="base-overlay-header" style="background:var(--bg-card,#16162a);padding:4px 8px;border-radius:4px;border:1px solid var(--border,#2a2a4a);">
                        <span class="stack-label-mini">5th Base Overlay</span>
                        ${(zone.fifthBase || zone.fifthBaseColorSource) ? `<span style="font-size:9px;margin-left:auto;color:#a78bfa;">● ACTIVE</span>` : ''}
                    </div>
                    <div style="padding:4px 8px;">
                        <div class="stack-control-group">
                            <span class="stack-label-mini">5th Base</span>
                            <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'fifthBase', ${i})" title="Click to pick 5th base">
                                ${(zone.fifthBase || zone.fifthBaseColorSource) ? renderSwatchDot(zone.fifthBase || zone.fifthBaseColorSource, (getOverlayBaseDisplay(zone.fifthBase || zone.fifthBaseColorSource) || {}).swatch || '#888', zone.fifthBaseColor || '#ffffff') : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                                <span class="swatch-name">${(zone.fifthBase || zone.fifthBaseColorSource) ? (getOverlayBaseDisplay(zone.fifthBase || zone.fifthBaseColorSource) || {}).name || (zone.fifthBase || zone.fifthBaseColorSource) : '- None -'}</span>
                                <span class="swatch-arrow">&#9662;</span>
                            </div>
                            ${(zone.fifthBase || zone.fifthBaseColorSource) ? `<button class="btn btn-sm" onclick="event.stopPropagation(); setZoneFifthBase(${i}, ''); setZoneFifthBaseColorSource(${i}, null)" title="Remove 5th overlay" style="padding:0px 5px;font-size:9px;line-height:1.2;margin-left:4px;">✕</button>` : ''}
                        </div>
                        ${(zone.fifthBase || zone.fifthBaseColorSource) ? `
                        <div class="stack-control-group" style="margin-top:4px;flex-wrap:wrap;gap:6px 10px;">
                            <span class="stack-label-mini">Overlay Color</span>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fifColorSource${i}" value="solid" ${!zone.fifthBaseColorSource || zone.fifthBaseColorSource === 'solid' ? 'checked' : ''} onchange="setZoneFifthBaseColorSource(${i}, 'solid')"><span>Solid</span></label>
                            <span style="display:flex;align-items:center;gap:4px;"><input type="color" value="${zone.fifthBaseColor || '#ffffff'}" onchange="setZoneFifthBaseColor(${i}, this.value)" style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                            <input type="text" value="${zone.fifthBaseColor || '#ffffff'}" onchange="setZoneFifthBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color"><input type="radio" name="fifColorSource${i}" value="overlay" ${zone.fifthBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneFifthBaseColorSourceToOverlay(${i})"><span>Same as overlay</span></label>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fifColorSource${i}" value="special" ${zone.fifthBaseColorSource && zone.fifthBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'fifth' }; setZoneFifthBaseColorSource(${i}, '${(zone.fifthBaseColorSource && zone.fifthBaseColorSource.startsWith('mono:') ? zone.fifthBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')"><span>From special</span></label>
                            ${zone.fifthBaseColorSource && zone.fifthBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'fifth') : ''}
                        </div>
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBaseStrength || 0) * 100)}" oninput="setZoneFifthBaseStrength(${i}, this.value)" class="stack-slider" title="5th overlay strength, 5% steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFifStrVal${i}">${Math.round((zone.fifthBaseStrength || 0) * 100)}%</span>
                        </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini" title="Blend-amount for this OVERLAY's spec onto the primary base: 100% = overlay reaches its full M/R/CC where it shows; 50% = overlay contributes in roughly half the pixels with reduced intensity; 0% = overlay is fully suppressed (primary base alone shows). Unlike the primary Spec Strength this is layer-opacity semantics, not material-weakening.">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneFifthBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detFifSpecStrVal${i}">${Math.round((zone.fifthBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
                <div class="hsb-controls" style="margin-top:6px;border-top:1px solid #333;padding-top:4px;">
                    <div style="color:#aaa;font-size:10px;font-weight:bold;margin-bottom:3px;">Overlay HSB Adjust</div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Hue</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fifthBaseHueShift=Math.max(-180,(zones[${i}].fifthBaseHueShift||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-180" max="180" step="5" value="${zone.fifthBaseHueShift || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].fifthBaseHueShift=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value+'°'; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Shift overlay colors (-180° to +180°), drag=5° steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fifthBaseHueShift=Math.min(180,(zones[${i}].fifthBaseHueShift||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.fifthBaseHueShift || 0}°</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Sat</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fifthBaseSaturation=Math.max(-100,(zones[${i}].fifthBaseSaturation||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.fifthBaseSaturation || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].fifthBaseSaturation=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay saturation (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fifthBaseSaturation=Math.min(100,(zones[${i}].fifthBaseSaturation||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.fifthBaseSaturation || 0}</span>
                    </div>
                    <div class="stack-control-group" style="margin-bottom:2px;">
                        <span class="stack-label-mini" style="min-width:28px;">Brt</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fifthBaseBrightness=Math.max(-100,(zones[${i}].fifthBaseBrightness||0)-1); renderZones(); triggerPreviewRender();" title="-1" style="padding:0 3px;font-size:9px;">−</button>
                        <input type="range" min="-100" max="100" step="5" value="${zone.fifthBaseBrightness || 0}"
                            oninput="pushZoneUndo('', true); zones[${i}].fifthBaseBrightness=parseInt(this.value); var lbl=this.parentElement.querySelector('.stack-val'); if(lbl) lbl.textContent=this.value; renderZones(); triggerPreviewRender();"
                            class="stack-slider" title="Adjust overlay brightness (-100 to +100), drag=5 steps">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); pushZoneUndo('', true); zones[${i}].fifthBaseBrightness=Math.min(100,(zones[${i}].fifthBaseBrightness||0)+1); renderZones(); triggerPreviewRender();" title="+1" style="padding:0 3px;font-size:9px;">+</button>
                        <span class="stack-val" style="min-width:35px;">${zone.fifthBaseBrightness || 0}</span>
                    </div>
                </div>
                ${(zone.fifthBase || zone.fifthBaseColorSource) ? (() => {
                    const fifthOvSpecStack = zone.fifthOverlaySpecPatternStack || [];
                    const fifthOvSpecStackActive = fifthOvSpecStack.length > 0;
                    const MAX_OVERLAY_SPEC_PATTERN_LAYERS = 5;
                    let fifthOvSpHtml = `<div class="overlay-spec-patterns" style="border-top:1px solid #c084fc33;margin-top:6px;padding-top:6px;">
                        <div style="color:#c084fc;font-size:10px;margin-bottom:4px;">
                            &#9670; Overlay Spec Patterns
                            <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">spec overlays for 5th base</span>
                            ${fifthOvSpecStackActive ? '<span style="font-size:9px;margin-left:auto;color:#c084fc;">&#9679; ACTIVE (' + fifthOvSpecStack.length + ')</span>' : ''}
                        </div>`;

                    fifthOvSpecStack.forEach((sp, si) => {
                        const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === sp.pattern);
                        const spName = spDef ? spDef.name : (sp.pattern || '???');
                        const chM = (sp.channels || 'MR').includes('M');
                        const chR = (sp.channels || 'MR').includes('R');
                        const chCC = (sp.channels || 'MR').includes('CC');
                        fifthOvSpHtml += `<div style="margin-bottom:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                            <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
                                <span style="font-size:10px; color:#c084fc; font-weight:bold;">${si + 1}.</span>
                                <span style="font-size:10px; color:var(--text);">${spName}</span>
                                <span style="font-size:8px; color:var(--text-dim);">${spDef ? spDef.desc : ''}</span>
                                <button class="btn btn-sm" onclick="event.stopPropagation(); removeFifthOverlaySpecPatternLayer(${i}, ${si})" title="Remove" style="margin-left:auto; padding:0px 5px; font-size:9px; line-height:1.2;">&times;</button>
                            </div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center;">
                                <div class="stack-control-group" style="flex:1; min-width:100px;">
                                    <span class="stack-label-mini">Opacity</span>
                                    <input type="range" min="0" max="100" step="5" value="${sp.opacity ?? 50}"
                                        oninput="setFifthOverlaySpecPatternLayerProp(${i}, ${si}, 'opacity', parseInt(this.value)); this.nextElementSibling.textContent=this.value+'%'"
                                        class="stack-slider" title="Opacity (5% steps)">
                                    <span class="stack-val">${sp.opacity ?? 50}%</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Range</span>
                                    <input type="range" min="1" max="100" step="1" value="${sp.range || 40}"
                                        oninput="setFifthOverlaySpecPatternLayerProp(${i}, ${si}, 'range', parseInt(this.value)); this.nextElementSibling.textContent=this.value"
                                        class="stack-slider" title="Range (1-100)">
                                    <span class="stack-val">${sp.range || 40}</span>
                                </div>
                                <div class="stack-control-group" style="flex:1; min-width:90px;">
                                    <span class="stack-label-mini">Scale</span>
                                    <input type="range" min="5" max="400" step="5" value="${Math.round((sp.scale || 1) * 100)}"
                                        oninput="setFifthOverlaySpecPatternLayerProp(${i}, ${si}, 'scale', this.value/100); this.nextElementSibling.textContent=this.value+'%'; renderZones(); triggerPreviewRender();"
                                        class="stack-slider" title="Spec pattern scale — 100% = default">
                                    <span class="stack-val">${Math.round((sp.scale || 1) * 100)}%</span>
                                </div>
                                <div class="stack-control-group" style="min-width:80px;">
                                    <span class="stack-label-mini">Blend</span>
                                    <select onchange="setFifthOverlaySpecPatternLayerProp(${i}, ${si}, 'blendMode', this.value)"
                                        style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                        <option value="normal"${(sp.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                        <option value="multiply"${sp.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                        <option value="screen"${sp.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                        <option value="overlay"${sp.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                                        <option value="hardlight"${sp.blendMode === 'hardlight' ? ' selected' : ''}>Hard Light</option>
                                        <option value="softlight"${sp.blendMode === 'softlight' ? ' selected' : ''}>Soft Light</option>
                                    </select>
                                </div>
                                <div class="stack-control-group" style="min-width:100px;">
                                    <span class="stack-label-mini">Channels</span>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chM ? 'checked' : ''} onchange="toggleFifthOverlaySpecPatternChannel(${i}, ${si}, 'M', this.checked)"> M</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chR ? 'checked' : ''} onchange="toggleFifthOverlaySpecPatternChannel(${i}, ${si}, 'R', this.checked)"> R</label>
                                    <label style="display:inline-flex;align-items:center;gap:2px;cursor:pointer;font-size:9px;"><input type="checkbox" ${chCC ? 'checked' : ''} onchange="toggleFifthOverlaySpecPatternChannel(${i}, ${si}, 'CC', this.checked)"> CC</label>
                                </div>
                            </div>
                        </div>`;
                    });

                    if (fifthOvSpecStack.length < MAX_OVERLAY_SPEC_PATTERN_LAYERS) {
                        fifthOvSpHtml += `<div style="margin-top:4px;">
                            <div id="fifthOverlaySpecPatternGrid${i}" style="display:none; max-height:220px; overflow-y:auto; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;" class="spec-pattern-grid">`;
                        (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                            fifthOvSpHtml += `<div class="spec-pattern-thumb-card"
                                onclick="if(this._spPopup){this._spPopup.remove();this._spPopup=null;} document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); var _og=document.getElementById('fifthOverlaySpecPatternGrid${i}'); if(_og){_og.style.display='none';} addFifthOverlaySpecPatternLayer(${i}, '${sp.id}');"
                                title="${sp.desc}"
                                onmouseenter="(function(el){var img=el.querySelector('img');if(!img)return;var popup=document.createElement('div');popup.className='spec-thumb-popup';popup.innerHTML='<img src=\\''+img.src+'\\' style=\\'width:200px;height:200px;object-fit:contain;\\'>';var rect=el.getBoundingClientRect();popup.style.left=(rect.left+rect.width/2-104)+'px';popup.style.top=(rect.top-216)+'px';document.body.appendChild(popup);el._spPopup=popup;})(this)"
                                onmouseleave="if(this._spPopup){this._spPopup.remove();this._spPopup=null;}">
                                <img src="/thumbnails/spec_patterns/${sp.id}.png" alt="${sp.name}" loading="eager" onerror="this.src='/api/spec-pattern-preview/${sp.id}?v=live';this.onerror=null;">
                                <div class="thumb-label">${sp.name}</div>
                            </div>`;
                        });
                        fifthOvSpHtml += `</div>
                            <button onclick="document.querySelectorAll('.spec-thumb-popup').forEach(p=>p.remove()); const g=document.getElementById('fifthOverlaySpecPatternGrid${i}'); if(g.style.display==='none'||!g.style.display){g.style.display='grid';g.style.gridTemplateColumns='repeat(3,1fr)';g.style.gap='6px';g.style.padding='6px';}else{g.style.display='none';}" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #c084fc44; color:#c084fc; margin-top:4px;">
                                + Add Overlay Spec Pattern (click to browse)
                            </button>
                        </div>`;
                    } else {
                        fifthOvSpHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 5 overlay spec pattern layers reached.</div>';
                    }

                    fifthOvSpHtml += `</div>`;
                    return fifthOvSpHtml;
                })() : ''}
                        <div class="stack-control-group" style="margin-top:4px;align-items:flex-start;">
                            <span class="stack-label-mini" style="padding-top:2px;">Blend Mode</span>
                            <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="noise" ${['noise', 'dust'].includes(zone.fifthBaseBlendMode || 'noise') ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'noise')"><span>✨ Fractal Dust</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="marble" ${zone.fifthBaseBlendMode === 'marble' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'marble')"><span>🌪️ Liquid Swirl</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern-edges" ${['pattern-edges', 'uniform'].includes(zone.fifthBaseBlendMode || '') ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern-edges')"><span>📐 Pattern Edges</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern" ${zone.fifthBaseBlendMode === 'pattern' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern')"><span>🔷 Pattern-Reactive</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern-vivid" ${zone.fifthBaseBlendMode === 'pattern-vivid' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern-vivid')"><span>💥 Pattern-Pop <span style="font-size:8px;color:var(--text-dim);">full color</span></span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="tint" ${(zone.fifthBaseBlendMode || '') === 'tint' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'tint')"><span>🎨 Tint (subtle)</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern-peaks" ${zone.fifthBaseBlendMode === 'pattern-peaks' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern-peaks')"><span>⛰️ Pattern Peaks</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern-contour" ${zone.fifthBaseBlendMode === 'pattern-contour' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern-contour')"><span>〰️ Pattern Contour</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern-screen" ${zone.fifthBaseBlendMode === 'pattern-screen' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern-screen')"><span>✨ Pattern Screen</span></label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;"><input type="radio" name="fifBlendMode${i}" value="pattern-threshold" ${zone.fifthBaseBlendMode === 'pattern-threshold' ? 'checked' : ''} onchange="setZoneFifthBaseBlendMode(${i}, 'pattern-threshold')"><span>◐ Pattern Threshold</span></label>
                            </div>
                        </div>
                        ${['noise', 'dust', 'marble'].includes(zone.fifthBaseBlendMode || 'noise') ? `
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini">Fractal Detail</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseFractalScale(${i}, -1)" title="-4px" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="4" max="128" step="4" value="${zone.fifthBaseFractalScale || 24}" oninput="setZoneFifthBaseFractalScale(${i}, this.value)" class="stack-slider" title="Fractal Detail">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseFractalScale(${i}, 1)" title="+4px" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFifNSVal${i}">${zone.fifthBaseFractalScale || 24}px</span>
                        </div>` : ''}
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini">Overlay Scale</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="10" max="500" step="5" value="${Math.min(500, Math.max(10, Math.round((zone.fifthBaseScale ?? 1) * 100)))}" oninput="setZoneFifthBaseScale(${i}, parseFloat(this.value)/100)" class="stack-slider" title="5% steps (Fractal/Dust only)">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFifScaleVal${i}">${(zone.fifthBaseScale ?? 1).toFixed(2)}</span>
                        </div>
                        <div class="stack-control-group" style="margin-top:6px; padding:6px 8px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">
                            <span class="stack-label-mini" style="margin-bottom:4px;">React to zone pattern</span>
                            <p style="font-size:9px;color:var(--text-dim);margin:0 0 6px 0;">All blend modes use the selected pattern (Invert, Harden, Opacity, Scale, Rotate, Strength, Position).</p>
                            <div class="stack-control-group" style="margin-bottom:6px;">
                                <label class="stack-label-mini">React to</label>
                                <select onchange="setZoneFifthBasePattern(${i}, this.value)" style="font-size:10px;padding:4px 6px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:4px;min-width:140px;">
                                    ${(function () { const opts = getZonePatternReactOptions(zone); let sel = getOverlayReactToSelectValue(zone, zone.fifthBasePattern); if (!opts.some(o => o.value === sel)) sel = ''; return opts.map(o => `<option value="${(o.value === '' ? '' : o.value)}" ${sel === o.value ? 'selected' : ''}>${o.label}</option>`).join(''); })()}
                                </select>
                            </div>
                            <div class="stack-control-group" style="flex-wrap:wrap;gap:8px 12px;">
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.fifthBasePatternInvert || false) ? 'checked' : ''} onchange="setZoneFifthBasePatternInvert(${i}, this.checked)"> Invert mask (color background)</label>
                                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="checkbox" ${(zone.fifthBasePatternHarden || false) ? 'checked' : ''} onchange="setZoneFifthBasePatternHarden(${i}, this.checked)"> Harden (only in pattern)</label>
                            </div>
                            <div class="stack-control-group"><span class="stack-label-mini">Opacity</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternOpacity(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="100" step="5" value="${zone.fifthBasePatternOpacity ?? 100}" oninput="setZoneFifthBasePatternOpacity(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternOpacity(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFifPatOpVal${i}">${zone.fifthBasePatternOpacity ?? 100}%</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Scale</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternScale(${i}, -1)" title="-1 step (5%)" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="10" max="400" step="5" value="${Math.round((zone.fifthBasePatternScale ?? 1.0) * 100)}" oninput="setZoneFifthBasePatternScale(${i}, parseFloat(this.value)/100)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternScale(${i}, 1)" title="+1 step (5%)" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFifPatScaleVal${i}">${(zone.fifthBasePatternScale ?? 1.0).toFixed(2)}x</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Rotate</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternRotation(${i}, -1)" title="-5°" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="359" step="5" value="${zone.fifthBasePatternRotation ?? 0}" id="detFifPatRotRange${i}" oninput="setZoneFifthBasePatternRotation(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternRotation(${i}, 1)" title="+5°" style="padding:0 4px;font-size:10px;">+</button>
                                <input type="number" min="0" max="359" value="${zone.fifthBasePatternRotation ?? 0}" onchange="setZoneFifthBasePatternRotation(${i}, this.value)" id="detFifPatRotVal${i}" style="width:42px;font-size:10px;text-align:center;padding:1px 2px;background:var(--bg-input);color:var(--text);border:1px solid var(--border);border-radius:3px;"> <span style="font-size:10px;color:var(--text-dim);">°</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini" title="Controls how visible this overlay layer is. 0%=hidden, 50%=blended, 100%=fully opaque over the base">Strength</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBasePatternStrength ?? 1) * 100)}" oninput="setZoneFifthBasePatternStrength(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFifPatStrVal${i}">${Math.round((zone.fifthBasePatternStrength ?? 1) * 100)}%</span></div>
                            ${renderPlacementModeControls(i, 'fifth_base', { label: 'Overlay placement', targetLabel: 'the 5th base overlay', allowFit: true, centeredLabel: 'Centered + Numeric' })}
                            <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fifth', 'X', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fifth_base')}>−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneFifthBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right" ${_placementOffsetControlAttrs(zone, 'fifth_base')}>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fifth', 'X', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fifth_base')}>+</button>
                                <span class="stack-val" id="detFifPatPosXVal${i}" ${_placementOffsetValueAttrs(zone, 'fifth_base')}>${Math.round((zone.fifthBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fifth', 'Y', -1)" title="-1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fifth_base')}>−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneFifthBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down" ${_placementOffsetControlAttrs(zone, 'fifth_base')}>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneNthBasePatternOffset(${i}, 'fifth', 'Y', 1)" title="+1%" style="padding:0 4px;font-size:10px;" ${_placementOffsetControlAttrs(zone, 'fifth_base')}>+</button>
                                <span class="stack-val" id="detFifPatPosYVal${i}" ${_placementOffsetValueAttrs(zone, 'fifth_base')}>${Math.round((zone.fifthBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
                            <div class="stack-control-group" style="margin-top:6px;">
                                <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); alignFifthBaseOverlayWithSelectedPattern(${i})" title="Copy primary pattern position, scale, and rotation so the 5th overlay lines up exactly">✓ Align with selected pattern</button>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
        </div>`;
    }

    // Pattern stack moved upwards.

    // Wear row
    if (zone.base || zone.finish) {
        html += `<div class="zone-finish-row zone-wear-row">
            <label>Wear</label>
            <input type="range" min="0" max="100" step="5" value="${zone.wear || 0}"
                oninput="setZoneWear(${i}, this.value)"
                style="flex:1; min-width:60px;">
            <span class="slider-val" id="detWearVal${i}" style="min-width:30px; text-align:center;">${zone.wear || 0}%</span>
        </div>`;
    }

    // Material Properties block
    html += `<div class="zone-finish-row intensity-row-stacked" style="display:flex; flex-direction:column; gap:6px; padding:8px; background:var(--bg-dark); border:1px solid var(--border); border-radius:4px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <label style="font-size:10px; color:var(--accent-green); font-weight:bold;">🛠️ Material Properties</label>
            <span class="lock-toggle${zone.lockIntensity ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockIntensity')" title="Lock intensity during randomize">${zone.lockIntensity ? '&#128274;' : '&#128275;'}</span>
        </div>
        
        <div class="intensity-slider-row" style="margin-top:2px;">
            <label title="Zone intensity — controls the overall strength of all effects in this zone">Master PBR</label>
            <input type="range" min="0" max="100" step="1" value="${parseInt(zone.intensity) || 100}"
                oninput="setZoneIntensity(${i}, this.value, true); document.getElementById('detIntVal${i}').textContent=this.value+'%'; document.getElementById('detIntInput${i}').value=this.value"
                style="flex:1;"
                title="Zone intensity — controls the overall strength of all effects in this zone">
            <input type="number" id="detIntInput${i}" min="0" max="200" step="1" value="${parseInt(zone.intensity) || 100}"
                onchange="setZoneIntensityNumeric(${i}, this.value); document.getElementById('detIntVal${i}').textContent=this.value+'%'"
                style="width:48px;font-size:10px;text-align:center;padding:1px 2px;background:var(--bg-input,#1a1a2e);color:var(--text,#e0e0e0);border:1px solid var(--border,#333);border-radius:3px;"
                title="Type exact intensity 0-200">
            <span class="slider-val" id="detIntVal${i}">${parseInt(zone.intensity) || 100}%</span>
        </div>

        <div class="intensity-slider-row">
            <label title="Specular Highlight Strength Override" style="color:var(--text-dim, #888);">Spec</label>
            <input type="range" min="0" max="1.00" step="0.05" value="${zone.customSpec != null ? zone.customSpec : INTENSITY_VALUES[zone.intensity]?.spec || 1.0}" oninput="setCustomIntensity(${i},'spec',this.value); document.getElementById('detIntSpecVal${i}').textContent=parseFloat(this.value).toFixed(2)" onpointerdown="event.stopPropagation()">
            <span class="slider-val" id="detIntSpecVal${i}">${(zone.customSpec != null ? zone.customSpec : INTENSITY_VALUES[zone.intensity]?.spec || 1.0).toFixed(2)}</span>
        </div>
        
        <div class="intensity-slider-row">
            <label title="Paint Roughness/Color Strength Override" style="color:var(--text-dim, #888);">Paint</label>
            <input type="range" min="0" max="1.00" step="0.05" value="${zone.customPaint != null ? zone.customPaint : INTENSITY_VALUES[zone.intensity]?.paint || 1.0}" oninput="setCustomIntensity(${i},'paint',this.value); document.getElementById('detIntPaintVal${i}').textContent=parseFloat(this.value).toFixed(2)" onpointerdown="event.stopPropagation()">
            <span class="slider-val" id="detIntPaintVal${i}">${(zone.customPaint != null ? zone.customPaint : INTENSITY_VALUES[zone.intensity]?.paint || 1.0).toFixed(2)}</span>
        </div>
        
        <div class="intensity-slider-row">
            <label title="Brightness/Albedo Overlay Override" style="color:var(--text-dim, #888);">Bright</label>
            <input type="range" min="0" max="1.00" step="0.05" value="${zone.customBright != null ? zone.customBright : INTENSITY_VALUES[zone.intensity]?.bright || 1.0}" oninput="setCustomIntensity(${i},'bright',this.value); document.getElementById('detIntBrightVal${i}').textContent=parseFloat(this.value).toFixed(2)" onpointerdown="event.stopPropagation()">
            <span class="slider-val" id="detIntBrightVal${i}">${(zone.customBright != null ? zone.customBright : INTENSITY_VALUES[zone.intensity]?.bright || 1.0).toFixed(2)}</span>
        </div>
    </div>`;

    if (i === 0) {
        html += '<div class="zone-priority-note">First zone = highest priority</div>';
    }

    // ===== SPATIAL SELECTION - Include/Exclude refinement =====
    if (zone.base || zone.finish) {
        const hasSpatial = hasSpatialMask(zone);
        const isSpatialActive = canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude';
        html += `<div class="pattern-stack-section" style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;">
            <div class="pattern-stack-header" style="color:var(--accent-green);font-size:10px;">
                🎯 Spatial Selection
                <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">Refine color match with include/exclude regions</span>
                ${hasSpatial ? '<span style="font-size:8px;color:var(--accent-green);margin-left:auto;float:right;">ACTIVE</span>' : ''}
            </div>
            <div style="padding:4px 8px;">
                <div style="font-size:9px;color:var(--text-dim);margin-bottom:6px;">
                    Paint on the preview to include (green) or exclude (red) areas from this zone's color selection.
                </div>
                <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;">
                    <button class="btn btn-sm${canvasMode === 'spatial-include' ? ' active' : ''}" 
                        onclick="event.stopPropagation(); toggleSpatialMode('include')" 
                        style="padding:3px 8px;font-size:10px;${canvasMode === 'spatial-include' ? 'background:rgba(0,200,100,0.3);border-color:var(--accent-green);color:var(--accent-green);' : ''}"
                        title="Include brush: paint areas to KEEP in this zone">
                        🟢 Include
                    </button>
                    <button class="btn btn-sm${canvasMode === 'spatial-exclude' ? ' active' : ''}" 
                        onclick="event.stopPropagation(); toggleSpatialMode('exclude')" 
                        style="padding:3px 8px;font-size:10px;${canvasMode === 'spatial-exclude' ? 'background:rgba(220,50,50,0.3);border-color:#ff4444;color:#ff4444;' : ''}"
                        title="Exclude brush: paint areas to REMOVE from this zone">
                        🔴 Exclude
                    </button>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); clearSpatialMask(${i})" 
                        style="padding:3px 8px;font-size:10px;" title="Clear all include/exclude marks">
                        🗑️ Clear
                    </button>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); undoSpatialStroke()" 
                        style="padding:3px 8px;font-size:10px;" title="Undo last spatial stroke">
                        ↩ Undo
                    </button>
                    ${isSpatialActive ? '<button class="btn btn-sm" onclick="event.stopPropagation(); toggleSpatialMode(\'off\')" style="padding:3px 8px;font-size:10px;color:var(--accent-orange);border-color:var(--accent-orange);">✋ Stop Drawing</button>' : ''}
                </div>
                ${isSpatialActive ? `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-size:9px;color:var(--text-dim);min-width:60px;">Brush Size</span>
                    <input type="range" min="3" max="80" value="${spatialBrushRadius}" 
                        oninput="spatialBrushRadius = parseInt(this.value); document.getElementById('spatialBrushVal').textContent = this.value + 'px'"
                        style="flex:1;">
                    <span id="spatialBrushVal" style="font-size:10px;color:var(--text-dim);min-width:30px;">${spatialBrushRadius}px</span>
                </div>` : ''}
            </div>
        </div>`;
    }

    // ── FINISH DNA SECTION ──
    html += `<div class="section-collapsible collapsed" id="sectionDNA${i}">
    <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
        <span class="section-header-label">FINISH DNA</span>
        <span class="collapse-arrow section-header-arrow">&#9660;</span>
    </div>
    <div style="padding:6px 4px; display:flex; flex-direction:column; gap:6px;">
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
            <button class="btn btn-sm" onclick="event.stopPropagation(); copyZoneDNA(${i})" title="Copy this zone's finish configuration as a shareable DNA string" style="padding:3px 10px; font-size:10px; border-color:var(--accent-gold); color:var(--accent-gold); font-weight:bold;">&#128203; Copy DNA</button>
            <span style="font-size:9px; color:var(--text-dim);">Copies a shareable string with all finish settings</span>
        </div>
        <div style="display:flex; gap:4px; align-items:center;">
            <input type="text" id="dnaPasteInput_${i}" placeholder="Paste DNA string: SHOKK:v1:..." style="flex:1; font-size:10px; padding:4px 6px; background:var(--bg-input, #1a1a2e); color:var(--text-main, #e0e0e0); border:1px solid var(--border-dim, #333); border-radius:3px; font-family:monospace;" onclick="event.stopPropagation();" onfocus="this.select();">
            <button class="btn btn-sm" onclick="event.stopPropagation(); handleDNAPaste(${i})" title="Apply a DNA string to this zone" style="padding:3px 10px; font-size:10px; border-color:var(--accent-blue, #4488ff); color:var(--accent-blue, #4488ff); font-weight:bold; white-space:nowrap;">&#128203; Paste DNA</button>
        </div>
    </div>
    </div>`;

    html += `</div>`; // close zone-detail-body

    // Footer removed to keep panel persistent.

    // 2026-04-18 MARATHON bug #38 (Animal, MED): pre-fix, scroll restore
    // ran unconditionally even when the painter switched to a DIFFERENT
    // zone — the new zone's detail panel opened at the old zone's
    // scrollTop. `sameZone` was computed but never consulted. Now only
    // restore scroll when we're re-rendering the same zone.
    const scrollRestore = (sameZone && _savedScrollTop > 0) ? _savedScrollTop : 0;

    panel.innerHTML = html;
    lastRenderedZoneDetailIndex = index;

    const newBody = panel.querySelector('.zone-detail-body');
    if (newBody) {
        if (scrollRestore > 0) {
            newBody.scrollTop = scrollRestore;
            requestAnimationFrame(() => { newBody.scrollTop = scrollRestore; });
        } else {
            // Switching zones: always start at top of the new panel.
            newBody.scrollTop = 0;
        }
    }

    // Refresh Fine Tuning panel if open (must happen after DOM is built so cloning works)
    if (typeof _refreshFineTuningIfOpen === 'function') _refreshFineTuningIfOpen();
}

function collapseZoneDetail() {
    lastRenderedZoneDetailIndex = -1;
    const fallbackPanel = document.getElementById('zoneDetailPanel');
    if (fallbackPanel) fallbackPanel.innerHTML = '';
    const floatPanel = document.getElementById('zoneEditorFloat');
    if (floatPanel) {
        floatPanel.innerHTML = '';
        floatPanel.classList.remove('active', 'collapsed');
        floatPanel.style.display = '';
        floatPanel.style.visibility = '';
    }
    const tab = document.getElementById('zoneFloatExpandTab');
    if (tab) tab.classList.remove('visible');
    updateBottomBarShift();
}

// Toggle floating panel collapsed/expanded (hides panel, shows expand tab)
function toggleZoneFloat() {
    const floatPanel = document.getElementById('zoneEditorFloat');
    const tab = document.getElementById('zoneFloatExpandTab');
    if (!floatPanel || !floatPanel.classList.contains('active')) return;

    if (floatPanel.classList.contains('collapsed')) {
        // Expand - show panel, hide tab
        floatPanel.classList.remove('collapsed');
        if (tab) { tab.classList.remove('visible'); tab.innerHTML = '&#9664;'; }
    } else {
        // Collapse - hide panel, show tab
        floatPanel.classList.add('collapsed');
        if (tab) { tab.classList.add('visible'); tab.innerHTML = '&#9654;'; }
    }
    updateBottomBarShift();
}

// Shift the entire center panel right when the floating zone panel is visible (not collapsed)
function updateBottomBarShift() {
    const floatPanel = document.getElementById('zoneEditorFloat');
    const isOpen = floatPanel && floatPanel.classList.contains('active') && !floatPanel.classList.contains('collapsed');
    const shiftPx = isOpen ? '370px' : '0';
    // Shift entire center panel content
    const centerPanel = document.getElementById('centerPanel');
    if (centerPanel) centerPanel.style.paddingLeft = shiftPx;
}

// ===== ZONE ACTIONS =====
function selectZone(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] selectZone: invalid index', index, '(zones.length=' + zones.length + ')');
        return;
    }
    // Only reset placement layer when switching to a DIFFERENT zone
    if (index !== selectedZoneIndex && placementLayer !== 'none' && zones[index]) {
        const z = zones[index];
        const ok = (placementLayer === 'pattern' && z.pattern && z.pattern !== 'none') ||
            (placementLayer === 'second_base' && z.secondBase && z.secondBasePattern) ||
            (placementLayer === 'third_base' && z.thirdBase && z.thirdBasePattern) ||
            (placementLayer === 'fourth_base' && z.fourthBase && z.fourthBasePattern) ||
            (placementLayer === 'fifth_base' && z.fifthBase && z.fifthBasePattern) ||
            (placementLayer === 'base' && (z.base || z.finish)) ||
            placementLayer.startsWith('spec_pattern');
        if (!ok) {
            placementLayer = 'none';
            if (typeof deactivateManualPlacement === 'function') deactivateManualPlacement();
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();
        }
    }
    selectedZoneIndex = index;
    if (typeof setToolbarEditMode === 'function') setToolbarEditMode('zone', { silent: true });
    renderZones();
    // Ensure the zone detail popout is shown when a zone is selected (fixes missing popout after Restore All or new session)
    if (typeof renderZoneDetail === 'function' && selectedZoneIndex >= 0 && selectedZoneIndex < zones.length) {
        renderZoneDetail(selectedZoneIndex);
    }
    // Update draw zone indicator if in drawing mode
    if (canvasMode !== 'eyedropper') {
        updateDrawZoneIndicator();
    }
    // Sync the right-side eyedropper panel to match the selected zone
    syncEyedropperPanel();
    // Update region status indicator in bottom bar
    if (typeof updateRegionStatus === 'function') updateRegionStatus();
    // Refresh overlay to show only the selected zone's masks
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
    if (typeof refreshActiveToolLabel === 'function') refreshActiveToolLabel();
}

function updateZoneName(index, name) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    zones[index].name = (typeof name === 'string' ? name : '').substring(0, 100); // Cap name length
}

function deleteZone(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    if (zones.length <= 1) { showToast('Cannot delete the last zone — at least one zone is required', true); return; }
    const z = zones[index];
    const hasFinish = z.base || z.finish;
    const hasColor = z.color !== null || z.colorMode === 'multi';
    const hasRegion = z.regionMask && z.regionMask.some(v => v > 0);
    // Confirm if zone has meaningful config (finish, color, or drawn region)
    if (hasFinish || hasColor || hasRegion) {
        const details = [];
        if (hasFinish) details.push('finish assigned');
        if (hasColor) details.push('color set');
        if (hasRegion) details.push('region drawn');
        if (!confirm(`Delete "${z.name}"? This zone has ${details.join(', ')}.`)) return;
    }
    pushZoneUndo('Delete zone "' + z.name + '"');
    zones.splice(index, 1);
    // 2026-04-18 marathon chaos audit: pre-fix, deleting zone[0] while
    // zone[1] was selected left selectedZoneIndex=1 pointing at what was
    // zone[2] (silent selection drift). Now shift the index down by 1 if
    // we deleted a zone at or before the selection.
    if (index < selectedZoneIndex) {
        selectedZoneIndex = Math.max(0, selectedZoneIndex - 1);
    } else if (selectedZoneIndex >= zones.length) {
        selectedZoneIndex = zones.length - 1;
    }
    renderZones();
    triggerPreviewRender();
    autoSave();
    showToast('Deleted zone "' + z.name + '" -- Ctrl+Z to undo');
}

function moveZoneUp(index) {
    if (index <= 0) return;
    pushZoneUndo('Move zone up');
    [zones[index - 1], zones[index]] = [zones[index], zones[index - 1]];
    if (selectedZoneIndex === index) selectedZoneIndex = index - 1;
    else if (selectedZoneIndex === index - 1) selectedZoneIndex = index;
    renderZones();
    // 2026-04-18 marathon silent-drop fix: zone order affects render
    // priority (higher-index zones paint on top). Pre-fix, reordering zones
    // did NOT refresh Live Preview — painter saw the new zone order in the
    // panel but the rendered car kept showing the old layering.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function moveZoneDown(index) {
    if (index >= zones.length - 1) return;
    pushZoneUndo('Move zone down');
    [zones[index], zones[index + 1]] = [zones[index + 1], zones[index]];
    if (selectedZoneIndex === index) selectedZoneIndex = index + 1;
    else if (selectedZoneIndex === index + 1) selectedZoneIndex = index;
    renderZones();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

// ===== ZONE DRAG & DROP REORDER =====
let zoneDragIndex = -1;

function zoneDragStart(e, index) {
    // Drag is now ONLY on the handle (☰), so no need to check for controls.
    // The handle has draggable="true"; the card div does NOT.
    // This prevents slider/input interactions from triggering drag ghosts.
    zoneDragIndex = index;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
    // Use the whole card as drag image for visual feedback
    const card = document.getElementById('zone-card-' + index);
    if (card) {
        e.dataTransfer.setDragImage(card, 20, 20);
    }
    // Slight delay so the dragging class doesn't affect the drag image
    requestAnimationFrame(() => {
        if (card) card.classList.add('dragging');
    });
}

function zoneDragOver(e, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function zoneDragEnter(e, index) {
    e.preventDefault();
    // Clear all drag-over classes first
    document.querySelectorAll('.zone-card.drag-over').forEach(el => el.classList.remove('drag-over'));
    if (index !== zoneDragIndex) {
        const card = document.getElementById('zone-card-' + index);
        if (card) card.classList.add('drag-over');
    }
}

function zoneDragLeave(e) {
    // Only remove if actually leaving the card (not entering a child)
    const card = e.target.closest?.('.zone-card');
    if (card && !card.contains(e.relatedTarget)) {
        card.classList.remove('drag-over');
    }
}

function zoneDrop(e, targetIndex) {
    e.preventDefault();
    document.querySelectorAll('.zone-card.drag-over, .zone-card.dragging').forEach(el => {
        el.classList.remove('drag-over', 'dragging');
    });
    if (zoneDragIndex < 0 || zoneDragIndex === targetIndex) return;
    pushZoneUndo('Reorder zones');
    const [moved] = zones.splice(zoneDragIndex, 1);
    zones.splice(targetIndex, 0, moved);
    // Update selected index to follow the moved zone
    if (selectedZoneIndex === zoneDragIndex) {
        selectedZoneIndex = targetIndex;
    } else if (zoneDragIndex < selectedZoneIndex && targetIndex >= selectedZoneIndex) {
        selectedZoneIndex--;
    } else if (zoneDragIndex > selectedZoneIndex && targetIndex <= selectedZoneIndex) {
        selectedZoneIndex++;
    }
    zoneDragIndex = -1;
    renderZones();
    triggerPreviewRender();
    autoSave();
}

function zoneDragEnd(e) {
    zoneDragIndex = -1;
    document.querySelectorAll('.zone-card.drag-over, .zone-card.dragging').forEach(el => {
        el.classList.remove('drag-over', 'dragging');
    });
}

// ===== ZONE MUTE (SOLO/DISABLE) =====
function toggleZoneMute(index) {
    // 2026-04-18 MARATHON (Pillman bug #17): zone mute toggle was mutating
    // state without pushing undo. Painter muted a zone, hated it, hit Ctrl+Z
    // — nothing happened. Bulk mute siblings already push undo; this was
    // the asymmetric exception.
    pushZoneUndo(zones[index].muted ? 'Unmute zone' : 'Mute zone');
    zones[index].muted = !zones[index].muted;
    renderZones();
    triggerPreviewRender();
    autoSave();
    showToast(zones[index].muted
        ? `${zones[index].name} muted (excluded from render)`
        : `${zones[index].name} unmuted`);
}

// ===== RECENT PAINT PATHS =====
const RECENT_PATHS_KEY = 'shokker_recent_paths';
const MAX_RECENT_PATHS = 8;

function getRecentPaths() {
    try {
        return JSON.parse(localStorage.getItem(RECENT_PATHS_KEY) || '[]');
    } catch { return []; }
}

function addRecentPath(path) {
    if (!path) return;
    let paths = getRecentPaths();
    // Remove if already exists (will re-add at top)
    paths = paths.filter(p => p.toLowerCase() !== path.toLowerCase());
    paths.unshift(path);
    if (paths.length > MAX_RECENT_PATHS) paths = paths.slice(0, MAX_RECENT_PATHS);
    localStorage.setItem(RECENT_PATHS_KEY, JSON.stringify(paths));
}

function showRecentPaths() {
    const paths = getRecentPaths();
    const dropdown = document.getElementById('recentPathsDropdown');
    const currentVal = document.getElementById('paintFile').value.trim();
    if (!dropdown || paths.length === 0) { if (dropdown) dropdown.style.display = 'none'; return; }
    // Filter out current value
    const filtered = paths.filter(p => p.toLowerCase() !== currentVal.toLowerCase());
    if (filtered.length === 0) { dropdown.style.display = 'none'; return; }
    dropdown.innerHTML = filtered.map(p => {
        const shortName = p.split(/[/\\]/).pop();
        const folder = p.split(/[/\\]/).slice(-2, -1)[0] || '';
        return `<div class="recent-path-item" onmousedown="selectRecentPath('${p.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')" title="${p}">${folder ? folder + '/' : ''}${shortName}</div>`;
    }).join('');
    dropdown.style.display = '';
}

function hideRecentPaths() {
    const dropdown = document.getElementById('recentPathsDropdown');
    if (dropdown) dropdown.style.display = 'none';
}

function selectRecentPath(path) {
    document.getElementById('paintFile').value = path;
    hideRecentPaths();
    validatePaintPath();
}

// ===== LIVE PREVIEW (PAINT + SPEC INSET) =====
// Paint fills the preview pane. Spec map shows as a clickable inset thumbnail.
// Click the spec inset to expand it full-size (hides paint). Click again to shrink back.
let specExpanded = false;
function toggleSpecInset() {
    const specPane = document.getElementById('previewSpecPane');
    const paintPane = document.getElementById('previewPaintPane');
    specExpanded = !specExpanded;
    specPane.classList.toggle('spec-expanded', specExpanded);
    paintPane.style.display = specExpanded ? 'none' : '';
}

// ===== SPEC MAP CHANNEL VISUALIZER =====
let activeSpecChannel = 'all';  // 'all', 'r', 'g', 'b', 'a'

function setSpecChannel(ch) {
    activeSpecChannel = ch;
    // Update button states
    document.querySelectorAll('.spec-channel-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.ch === ch);
    });
    // Update label
    const labels = { all: 'SPEC MAP', r: 'METALLIC (R)', g: 'ROUGHNESS (G)', b: 'CLEARCOAT (B)', a: 'SPEC MASK (A)' };
    const label = document.querySelector('#previewSpecPane .preview-dual-label');
    if (label) label.textContent = labels[ch] || 'SPEC MAP';
    // Render channel
    renderSpecChannel();
}

function renderSpecChannel() {
    const img = document.getElementById('livePreviewSpecImg');
    const canvas = document.getElementById('specChannelCanvas');
    if (!img || !canvas || !img.src || !img.naturalWidth) return;

    if (activeSpecChannel === 'all') {
        // Show original image, hide canvas
        img.style.display = '';
        canvas.style.display = 'none';
        return;
    }

    // Draw spec image to canvas and extract channel
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, w, h);
    const imageData = ctx.getImageData(0, 0, w, h);
    const d = imageData.data;

    const chIndex = { r: 0, g: 1, b: 2, a: 3 }[activeSpecChannel];
    const chColors = {
        r: [1.0, 0.3, 0.3],   // reddish tint for metallic
        g: [0.3, 1.0, 0.3],   // greenish tint for roughness
        b: [0.3, 0.5, 1.0],   // bluish tint for clearcoat
        a: [1.0, 0.7, 0.3],   // orange tint for spec mask
    };
    const tint = chColors[activeSpecChannel] || [1, 1, 1];

    for (let i = 0; i < d.length; i += 4) {
        const val = d[i + chIndex];
        d[i] = Math.min(255, Math.round(val * tint[0]));  // R
        d[i + 1] = Math.min(255, Math.round(val * tint[1]));  // G
        d[i + 2] = Math.min(255, Math.round(val * tint[2]));  // B
        d[i + 3] = 255;  // Full opacity
    }

    ctx.putImageData(imageData, 0, 0);

    // Show canvas, hide original img
    img.style.display = 'none';
    canvas.style.display = '';
}

// Re-apply channel filter whenever spec preview updates
const _origSpecImgOnload = null;
function hookSpecImageLoad() {
    const img = document.getElementById('livePreviewSpecImg');
    if (!img) return;
    img.addEventListener('load', () => {
        if (activeSpecChannel !== 'all') {
            renderSpecChannel();
        }
    });
}
// Hook after DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hookSpecImageLoad);
} else {
    hookSpecImageLoad();
}

// ===== SPEC MAP INSPECTOR (separate modal: channels + values) =====
let specMapInspectorChannel = 'all';
let specMapInspectorImageData = null;  // cached RGBA from last spec image for stats + channel view

function openSpecMapInspector() {
    const modal = document.getElementById('specMapInspectorModal');
    const noData = document.getElementById('specMapInspectorNoData');
    const content = document.getElementById('specMapInspectorContent');
    const hint = document.getElementById('specMapInspectorHint');
    if (!modal) return;
    const specImg = document.getElementById('livePreviewSpecImg');
    if (!specImg || !specImg.src || specImg.src.startsWith('data:') === false) {
        noData.style.display = '';
        content.style.display = 'none';
        hint.textContent = 'No spec map yet. Switch to CAR or SPLIT view, configure zones, and wait for the preview to render. Then open this again to see each channel and values.';
    } else {
        noData.style.display = 'none';
        content.style.display = '';
        hint.textContent = 'How each channel is drawn (R=Metallic, G=Roughness, B=Clearcoat, A=Spec mask). Values are 0–255.';
        const inspectorImg = document.getElementById('specMapInspectorImg');
        const inspectorCanvas = document.getElementById('specMapInspectorCanvas');
        if (inspectorImg) inspectorImg.src = specImg.src;
        if (inspectorImg && inspectorImg.complete && inspectorImg.naturalWidth > 0) {
            refreshSpecMapInspectorData(inspectorImg);
        } else if (inspectorImg) {
            inspectorImg.onload = function () { refreshSpecMapInspectorData(inspectorImg); };
        }
    }
    modal.style.display = 'flex';
}

function closeSpecMapInspector() {
    const modal = document.getElementById('specMapInspectorModal');
    if (modal) modal.style.display = 'none';
}

function setSpecMapInspectorChannel(ch) {
    specMapInspectorChannel = ch;
    document.querySelectorAll('#specMapInspectorContent .spec-channel-btn').forEach(b => {
        b.classList.toggle('active', (b.dataset.ch || '') === ch);
    });
    renderSpecMapInspectorChannel();
}

function refreshSpecMapInspectorData(img) {
    if (!img || img.naturalWidth === 0) return;
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, w, h);
    specMapInspectorImageData = ctx.getImageData(0, 0, w, h);
    updateSpecMapInspectorValues();
    renderSpecMapInspectorChannel();
}

function updateSpecMapInspectorValues() {
    const d = specMapInspectorImageData ? specMapInspectorImageData.data : null;
    if (!d) return;
    const n = d.length >> 2;
    let rMin = 255, rMax = 0, rSum = 0;
    let gMin = 255, gMax = 0, gSum = 0;
    let bMin = 255, bMax = 0, bSum = 0;
    let aMin = 255, aMax = 0, aSum = 0;
    for (let i = 0; i < d.length; i += 4) {
        const r = d[i], g = d[i + 1], b = d[i + 2], a = d[i + 3];
        if (r < rMin) rMin = r; if (r > rMax) rMax = r; rSum += r;
        if (g < gMin) gMin = g; if (g > gMax) gMax = g; gSum += g;
        if (b < bMin) bMin = b; if (b > bMax) bMax = b; bSum += b;
        if (a < aMin) aMin = a; if (a > aMax) aMax = a; aSum += a;
    }
    const ids = ['specValRMin', 'specValRMax', 'specValRMean', 'specValGMin', 'specValGMax', 'specValGMean', 'specValBMin', 'specValBMax', 'specValBMean', 'specValAMin', 'specValAMax', 'specValAMean'];
    const vals = [rMin, rMax, Math.round(rSum / n), gMin, gMax, Math.round(gSum / n), bMin, bMax, Math.round(bSum / n), aMin, aMax, Math.round(aSum / n)];
    ids.forEach((id, i) => { const el = document.getElementById(id); if (el) el.textContent = vals[i]; });
}

function renderSpecMapInspectorChannel() {
    const img = document.getElementById('specMapInspectorImg');
    const canvas = document.getElementById('specMapInspectorCanvas');
    if (!img || !canvas) return;
    if (specMapInspectorChannel === 'all' || !specMapInspectorImageData) {
        img.style.display = '';
        canvas.style.display = 'none';
        return;
    }
    const d = specMapInspectorImageData.data;
    const w = specMapInspectorImageData.width;
    const h = specMapInspectorImageData.height;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    const chIndex = { r: 0, g: 1, b: 2, a: 3 }[specMapInspectorChannel];
    const tint = { r: [1, 0.3, 0.3], g: [0.3, 1, 0.3], b: [0.3, 0.5, 1], a: [1, 0.7, 0.3] }[specMapInspectorChannel] || [1, 1, 1];
    const out = ctx.createImageData(w, h);
    for (let i = 0; i < d.length; i += 4) {
        const v = d[i + chIndex];
        out.data[i] = Math.min(255, Math.round(v * tint[0]));
        out.data[i + 1] = Math.min(255, Math.round(v * tint[1]));
        out.data[i + 2] = Math.min(255, Math.round(v * tint[2]));
        out.data[i + 3] = 255;
    }
    ctx.putImageData(out, 0, 0);
    img.style.display = 'none';
    canvas.style.display = 'block';
}

// ===== BEFORE/AFTER COMPARISON =====
let beforeAfterActive = false;
let beforeImageCaptured = false;

function captureBeforeImage(srcOverride) {
    // Snapshot the last successful rendered preview, not the raw source canvas.
    const livePreviewImg = document.getElementById('livePreviewImg');
    const nextSrc = srcOverride || (livePreviewImg && livePreviewImg.src) || '';
    if (!nextSrc) return;
    const beforeImg = document.getElementById('beforePreviewImg');
    if (!beforeImg) return;
    beforeImg.src = nextSrc;
    beforeImageCaptured = true;
    if (typeof window !== 'undefined' && typeof window.updatePreviewControlAvailability === 'function') {
        window.updatePreviewControlAvailability();
    }
}

function toggleBeforeAfter() {
    if (!beforeImageCaptured) {
        showToast('No earlier rendered preview yet - make a change first');
        return;
    }
    beforeAfterActive = !beforeAfterActive;
    const beforePane = document.getElementById('previewBeforePane');
    const btn = document.getElementById('btnBeforeAfter');
    const sourceBtn = document.getElementById('btnBeforeAfterSource');
    if (beforeAfterActive) {
        if (beforePane) beforePane.style.display = '';
        [btn, sourceBtn].forEach(function (node) {
            if (node) {
                node.style.borderColor = 'var(--accent-gold)';
                node.style.background = 'rgba(255,170,0,0.15)';
            }
        });
    } else {
        if (beforePane) beforePane.style.display = 'none';
        [btn, sourceBtn].forEach(function (node) {
            if (node) {
                node.style.borderColor = 'var(--accent-gold)';
                node.style.background = '';
            }
        });
    }
    if (typeof window !== 'undefined' && typeof window.syncRenderedCanvasPreview === 'function') {
        window.syncRenderedCanvasPreview();
    }
    if (typeof window !== 'undefined' && typeof window.updatePreviewControlAvailability === 'function') {
        window.updatePreviewControlAvailability();
    }
}

// Keyboard shortcut: hold B to show before, release to show after
// SESSION ROUTER: bail on defaultPrevented.
document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented) return;
    if (e.key === 'b' && !e.ctrlKey && !e.altKey && !e.metaKey && !e.repeat) {
        const tag = e.target.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (beforeImageCaptured && !beforeAfterActive) {
            toggleBeforeAfter();
        }
    }
});
document.addEventListener('keyup', (e) => {
    if (e.key === 'b') {
        if (beforeAfterActive) toggleBeforeAfter();
    }
});

function clearAllZones() {
    if (!confirm('Reset ALL zones to defaults? This cannot be undone.')) return;
    pushZoneUndo('Clear all zones');
    init();
    showToast('All zones cleared and reset to defaults');
}

function restoreAllZones() {
    // Restore all 10 default zones without losing existing finishes on matching zones
    pushZoneUndo('Restore all zones');
    const defaults = [
        {
            name: "Body Color 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#3366ff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Pick Color mode - click your PRIMARY body color on the paint"
        },
        {
            name: "Body Color 2", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffcc00", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Click your SECOND body color (delete this zone if single-color car)"
        },
        {
            name: "Body Color 3", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#cc2222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Third body color if needed (delete if not)"
        },
        {
            name: "Body Color 4", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#22cc22", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Fourth body color if needed (delete if not)"
        },
        {
            name: "Car Number", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffaa00", pickerTolerance: 35, colors: [], regionMask: null,
            hint: "Magic Wand each number color, or Draw Region/Rectangle manually."
        },
        {
            name: "Custom Art 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ff3366", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Magic Wand to click artwork or Draw Region manually. Delete if not needed."
        },
        {
            name: "Custom Art 2", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#33ccff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Another art element - Magic Wand + Shift+click. Delete if not needed."
        },
        {
            name: "Sponsors / Logos", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#ffffff", pickerTolerance: 30, colors: [], regionMask: null,
            hint: "Draw regions over sponsor areas, or pick a color if sponsors share one color"
        },
        {
            name: "Open Zone 9", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#777777", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Empty by default. Use this only if you need another custom zone before Remaining."
        },
        {
            name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", finish: null, intensity: "50", colorMode: "special", pickerColor: "#888888", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Safety net - catches any pixels not claimed by zones above"
        },
    ];
    _ensureAllZonesHaveIds(defaults);
    zones = defaults;
    selectedZoneIndex = 0;
    renderZones();
    // Force the zone detail popout to open so it's visible after restore (fixes empty right area)
    if (typeof renderZoneDetail === 'function') renderZoneDetail(0);
    autoSave();
    showToast('All 10 default zones restored');
}

const MAX_ZONES = 50;
function addZone(skipUndo) {
    if (zones.length >= MAX_ZONES) {
        showToast('Zone limit reached (' + MAX_ZONES + ' max). Too many zones will severely degrade render performance. Delete unused zones first.', true);
        return;
    }
    if (zones.length >= 30) {
        showToast('Warning: ' + zones.length + ' zones active. Performance may degrade above 30 zones.');
    }
    if (!skipUndo) pushZoneUndo('Add zone');
    zones.push({
        id: _newZoneId(),
        name: `Zone ${zones.length + 1}`,
        color: null,
        base: null,
        pattern: "none",
        finish: null,
        intensity: "100",
        customSpec: null, customPaint: null, customBright: null,
        colorMode: "none",
        pickerColor: "#3366ff",
        pickerTolerance: 40,
        colors: [],
        regionMask: null,
        spatialMask: null, // Uint8Array: 0=unset, 1=include(green), 2=exclude(red)
        hint: "Pick a base material + pattern, then set the color",
        lockBase: false,
        lockPattern: false,
        lockIntensity: false,
        lockColor: false,
        scale: 1.0,
        patternStack: [],
        specPatternStack: [],  // Array of {pattern, opacity, blendMode, channels, range, params}
        overlaySpecPatternStack: [],  // Array of {pattern, opacity, blendMode, channels, range, params} for overlay layer
        thirdOverlaySpecPatternStack: [],  // Overlay spec patterns for 3rd base overlay
        fourthOverlaySpecPatternStack: [],  // Overlay spec patterns for 4th base overlay
        fifthOverlaySpecPatternStack: [],  // Overlay spec patterns for 5th base overlay
        wear: 0,
        muted: false,
        patternOffsetX: 0.5,
        patternOffsetY: 0.5,
        patternPlacement: 'normal',  // 'normal' | 'fit' | 'manual'
        patternFlipH: false,
        patternFlipV: false,
        patternStrengthMap: null,       // null = uniform (slider only), or {width, height, data: Uint8Array}
        patternStrengthMapEnabled: false, // toggle for per-pixel strength map
        baseOffsetX: 0.5,
        baseOffsetY: 0.5,
        baseRotation: 0,
        baseFlipH: false,
        baseFlipV: false,
        basePlacement: 'normal',
        baseColorMode: 'source',
        baseColor: '#ffffff',
        baseColorSource: null,
        baseColorStrength: 1,
        baseColorFitZone: false,
        gradientStops: null,
        gradientDirection: 'horizontal',
        baseHueOffset: 0,
        baseSaturationAdjust: 0,
        baseBrightnessAdjust: 0,
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
        thirdBase: null,
        thirdBaseColor: '#ffffff',
        thirdBaseStrength: 0,
        thirdBaseBlendMode: 'noise',
        thirdBaseFractalScale: 24,
        thirdBaseScale: 1.0,
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
        fourthBase: null,
        fourthBaseColor: '#ffffff',
        fourthBaseStrength: 0,
        fourthBaseBlendMode: 'noise',
        fourthBaseFractalScale: 24,
        fourthBaseScale: 1.0,
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
        fifthBase: null,
        fifthBaseColor: '#ffffff',
        fifthBaseStrength: 0,
        fifthBaseBlendMode: 'noise',
        fifthBaseFractalScale: 24,
        fifthBaseScale: 1.0,
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
        hardEdge: false,
    });
    selectedZoneIndex = zones.length - 1;
    renderZones();
    const listEl = document.getElementById('zoneList');
    if (listEl) listEl.scrollTop = listEl.scrollHeight;
}
if (typeof window !== 'undefined') { window.addZone = addZone; }

function duplicateZone(index) {
    pushZoneUndo('Duplicate zone "' + (zones[index] && zones[index].name) + '"');
    const src = zones[index];
    const clone = _cloneZoneState(src, {
        preserveId: false,
        includeRegionMask: true,
        includeSpatialMask: true,
        includePatternStrengthMap: true,
    });
    clone.name = src.name + ' (copy)';
    if (typeof touchZoneTimestamp === 'function') clone._lastModified = Date.now();
    zones.splice(index + 1, 0, clone);
    selectedZoneIndex = index + 1;
    renderZones();
    // WIN #8 (Hawk audit, HIGH): pre-fix, duplicateZone mutated zones[] with
    // a clone whose finish/base/pattern/color all flow into the render payload,
    // but never fired triggerPreviewRender(). Sister functions
    // (duplicateZoneWithHueOffset, pasteZoneFromClipboard, etc.) all do.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Duplicated "${src.name}" \u2014 Ctrl+Z to undo`);
}

function applyFinishToAllZones() {
    const src = zones[selectedZoneIndex];
    if (!src.base && !src.finish) { showToast('Selected zone has no finish to apply', true); return; }
    if (!confirm(`Apply "${src.base || src.finish}" to ALL ${zones.length} zones?`)) return;
    pushZoneUndo('Apply finish to all zones');
    zones.forEach((z, i) => {
        if (i === selectedZoneIndex) return;
        z.base = src.base;
        z.pattern = src.pattern;
        z.finish = src.finish;
        z.intensity = src.intensity;
        z.patternIntensity = src.patternIntensity;
        z.scale = src.scale;
        z.patternStack = JSON.parse(JSON.stringify(src.patternStack || []));
    });
    renderZones();
    // FIVE-HOUR SHIFT Win C1: pre-fix this mutated 7 render-relevant fields
    // on every zone but never fired triggerPreviewRender(). Painter clicked
    // "Apply to all", saw zone cards update, but the LIVE PREVIEW stayed on
    // the old state until they touched any other control. Same silent-stale
    // class as marathon #24/#25 and TWENTY WINS #8 (duplicateZone).
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    showToast(`Applied finish to all ${zones.length} zones`);
}

// ===== COLOR SELECTORS =====
function setZoneSourceLayer(index, layerId) {
    pushZoneUndo('Set source layer');
    zones[index].sourceLayer = layerId || null;
    renderZones();
    renderZoneDetail(index);
    triggerPreviewRender();
    if (layerId) {
        const layer = (typeof _psdLayers !== 'undefined') ? _psdLayers.find(l => l.id === layerId) : null;
        showToast(`Zone restricted to layer: ${layer ? layer.name : layerId}`);
    } else {
        showToast('Zone restriction removed — applies to all layers');
    }
}

function setQuickColor(index, value) {
    pushZoneUndo('Set color');
    zones[index].color = value;
    zones[index].colorMode = 'quick';
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setSpecialColor(index, value) {
    pushZoneUndo('Set special color: ' + value);
    zones[index].color = value;
    zones[index].colorMode = 'special';
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setTextColor(index, value) {
    pushZoneUndo('Set text color: ' + (value || '(cleared)'));
    if (!value.trim()) {
        zones[index].color = null;
        zones[index].colorMode = 'none';
    } else {
        zones[index].color = value.trim();
        zones[index].colorMode = 'text';
    }
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setPickerColor(index, hexValue) {
    // 2026-04-18 MARATHON (Pillman bug #19): pre-fix, setPickerColor wiped
    // the zone's multi-color stack AND flipped colorMode to 'picker'
    // without any undo push. A painter who had built a careful 4-color
    // stack could lose it permanently by accidentally clicking the picker.
    // Peer setters (setQuickColor / setSpecialColor / setTextColor) all
    // push undo first — this was the asymmetric exception. Label hints at
    // the destructive nature ("Clear multi-color stack") so the undo
    // must capture it.
    pushZoneUndo('Switch to picker color');
    const r = parseInt(hexValue.substr(1, 2), 16);
    const g = parseInt(hexValue.substr(3, 2), 16);
    const b = parseInt(hexValue.substr(5, 2), 16);
    zones[index].pickerColor = hexValue;
    zones[index].color = { color_rgb: [r, g, b], tolerance: zones[index].pickerTolerance ?? 40 };
    zones[index].colorMode = 'picker';
    zones[index].colors = []; // Clear multi-color stack when setting single color via picker
    renderZones();
    triggerPreviewRender();
}

function setPickerTolerance(index, value) {
    // 2026-04-18 MARATHON (Pillman bug #19): drag-coalesced undo so the
    // painter can Ctrl+Z a tolerance drag session. Pre-fix the slider
    // mutated state with no undo entry at all.
    pushZoneUndo('Picker tolerance', true);
    zones[index].pickerTolerance = parseInt(value);
    if (zones[index].colorMode === 'picker' && typeof zones[index].color === 'object' && zones[index].color !== null) {
        zones[index].color.tolerance = parseInt(value);
    }
    renderZones();
    triggerPreviewRender();
}

// ===== HEX CODE COLOR =====
function setHexColor(index, hex) {
    // 2026-04-18 MARATHON (Windham bug #22): setHexColor was the asymmetric
    // exception — peer setters (setQuickColor / setSpecialColor /
    // setTextColor / setPickerColor / setPickerTolerance) all push undo
    // before mutating. This one silently mutated the multi-color stack,
    // pickerColor, colorMode — painter typed a wrong hex, Ctrl+Z did
    // nothing or jumped past the edit entirely. Push undo before the
    // validation so even a partial edit is recoverable.
    hex = hex.trim();
    if (!hex) {
        // Only clear if NOT in multi-color mode (don't wipe the stack)
        if (zones[index].colorMode !== 'multi') {
            pushZoneUndo('Clear hex color');
            zones[index].color = null;
            zones[index].colorMode = 'none';
        }
        renderZones();
        triggerPreviewRender();
        return;
    }
    // Normalize: add # if missing
    if (!hex.startsWith('#')) hex = '#' + hex;
    // Validate hex
    if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) {
        showToast('Enter a valid hex code like #FF3366', true);
        return;
    }
    // Push undo BEFORE mutating (multi-stack push, pickerColor, colorMode,
    // color all change below).
    pushZoneUndo('Set hex color ' + hex.toUpperCase());
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    const tol = zones[index].pickerTolerance ?? 40;
    zones[index].pickerColor = hex;

    // If zone is already in multi-color mode, add to the stack
    if (zones[index].colorMode === 'multi' && zones[index].colors.length > 0) {
        if (zones[index].colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
            showToast('That color is already in this zone', true);
            return;
        }
        zones[index].colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
        zones[index].color = zones[index].colors;
        renderZones();
        triggerPreviewRender();
        showToast(`Added ${hex.toUpperCase()} to ${zones[index].name} (${zones[index].colors.length} colors stacked)`);
    } else {
        // Single color mode
        zones[index].color = { color_rgb: [r, g, b], tolerance: tol };
        zones[index].colorMode = 'picker';
        renderZones();
        triggerPreviewRender();
        showToast(`Zone ${index + 1}: color set to ${hex.toUpperCase()}`);
    }
}

// ===== SWATCH PICKER POPUP =====
let swatchPopupState = { open: false, type: null, zoneIndex: -1, layerIndex: -1 };
let _swatchPopupObserver = null;

function _disconnectSwatchPopupLazyLoader() {
    if (_swatchPopupObserver) {
        try { _swatchPopupObserver.disconnect(); } catch (_) { /* ignore */ }
        _swatchPopupObserver = null;
    }
}

function _hydrateDeferredSwatchImage(img) {
    if (!img || img.dataset.swatchLoaded === '1') return;
    const url = img.getAttribute('data-swatch-url');
    if (!url) return;
    img.dataset.swatchLoaded = '1';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.src = url;
}

function _installSwatchPopupLazyLoader() {
    const grid = document.getElementById('swatchPopupGrid');
    if (!grid) return;
    const imgs = Array.from(grid.querySelectorAll('img.deferred-swatch[data-swatch-url]'));
    _disconnectSwatchPopupLazyLoader();
    if (imgs.length === 0) return;

    // Prime the first visible row or two so the picker feels instant without
    // stampeding the server for the entire library.
    const visibleImgs = imgs.filter(img => {
        const item = img.closest('.swatch-item');
        return !item || item.style.display !== 'none';
    });
    visibleImgs.slice(0, 24).forEach(_hydrateDeferredSwatchImage);

    if (typeof window === 'undefined' || typeof window.IntersectionObserver !== 'function') {
        visibleImgs.forEach(_hydrateDeferredSwatchImage);
        return;
    }

    _swatchPopupObserver = new window.IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            _hydrateDeferredSwatchImage(entry.target);
            try { _swatchPopupObserver && _swatchPopupObserver.unobserve(entry.target); } catch (_) { /* ignore */ }
        });
    }, { root: grid, rootMargin: '240px 0px' });

    visibleImgs.forEach(img => {
        if (img.dataset.swatchLoaded === '1') return;
        _swatchPopupObserver.observe(img);
    });
}

// Resolve overlay base id (base id or "mono:xyz" for specials) to display { name, swatch }.
function getOverlayBaseDisplay(id) {
    if (!id) return null;
    if (typeof id === 'string' && id.startsWith('mono:')) {
        const _mid = id.slice(5);
        const m = (typeof MONOLITHICS !== 'undefined' && MONOLITHICS.find(m => m.id === _mid)) ||
                  (typeof BASES !== 'undefined' && BASES.find(b => b.id === _mid));
        return m ? { name: m.name, swatch: m.swatch || '#888' } : { name: id, swatch: '#888' };
    }
    const b = typeof BASES !== 'undefined' && BASES.find(b => b.id === id);
    return b ? { name: b.name, swatch: b.swatch || '#888' } : { name: id, swatch: '#888' };
}

// Determine finish type for a given ID (needed to pick the right /api/swatch path).
// Use server-authoritative FINISH_TYPE_BY_ID when available so thumbnails always use correct path.
function getFinishType(id) {
    if (!id || id === 'none') return null;
    if (typeof id === 'string' && id.startsWith('mono:')) {
        // Migrated base finishes (COLORSHOXX, MORTAL SHOKK, etc.) show as mono: but are actually bases
        const _rawId = id.slice(5);
        if (typeof BASES !== 'undefined' && BASES.find(b => b.id === _rawId)) return 'base';
        return 'monolithic';
    }
    if (typeof FINISH_TYPE_BY_ID !== 'undefined' && FINISH_TYPE_BY_ID[id]) return FINISH_TYPE_BY_ID[id];
    if (typeof BASES !== 'undefined' && BASES.find(b => b.id === id)) return 'base';
    if (typeof PATTERNS !== 'undefined' && PATTERNS.find(p => p.id === id)) return 'pattern';
    return 'monolithic';
}

// Build the /api/swatch URL for a given finish + optional hint color
// Returns null if ShokkerAPI is not yet online (fallback to color dot)
// Split view for pattern, monolithic (FUSIONS etc.), and base: left=neutral/structure, right=with color
// size: optional pixel size (default 48); use larger (e.g. 80) for overlay special picker popout
function getSwatchUrl(finishId, colorHex, forceSplit, size) {
    const effectiveId = (typeof finishId === 'string' && finishId.startsWith('mono:')) ? finishId.slice(5) : finishId;
    const type = getFinishType(finishId);
    if (!type) return null;
    const col = (colorHex || '888888').replace('#', '');
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl)
        ? ShokkerAPI.baseUrl
        : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    const sz = (size != null && size > 0) ? size : 48;
    // Split view for patterns, monolithics (FUSIONS, Ghost Geometry, etc.), and bases
    const splitMode = (forceSplit !== false && (type === 'pattern' || type === 'monolithic' || type === 'base')) ? '&mode=split' : '';
    const v = (typeof window !== 'undefined' && window._SHOKKER_SWATCH_V) ? window._SHOKKER_SWATCH_V : Date.now();
    return `${base}/api/swatch/${type}/${effectiveId}?color=${col}&size=${sz}${splitMode}&prefer=live&v=${v}`;
}

/** Build HTML for the "From special" overlay color picker: summary (name + tiny swatch) when collapsed, or big grid when expanded. */
function getOverlaySpecialPickerHtml(zone, i, layer) {
    const key = { second: 'secondBaseColorSource', third: 'thirdBaseColorSource', fourth: 'fourthBaseColorSource', fifth: 'fifthBaseColorSource' }[layer];
    const current = zone[key];
    const isMono = current && current.startsWith('mono:');
    const monolithics = (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : []);
    const bases = (typeof BASES !== 'undefined' ? BASES : []);
    const monoId = isMono ? current.slice(5) : null;
    const selectedMono = monoId ? (monolithics.find(m => m.id === monoId) || bases.find(b => b.id === monoId) || null) : null;
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    const v = (typeof window !== 'undefined' && window._SHOKKER_SWATCH_V) ? window._SHOKKER_SWATCH_V : Date.now();
    const swatchUrl = (id, sz) => id ? `${base}/api/swatch/monolithic/${id}?color=888888&size=${sz || 48}&prefer=live&v=${v}` : null;
    const popupType = { second: 'secondBaseColorSource', third: 'thirdBaseColorSource', fourth: 'fourthBaseColorSource', fifth: 'fifthBaseColorSource' }[layer];
    let html = '';
    if (selectedMono) {
        const smallUrl = swatchUrl(selectedMono.id, 32);
        html += `<div class="stack-control-group" style="flex-basis:100%;margin-top:2px;align-items:center;gap:6px;">
            <div style="display:flex;align-items:center;gap:6px;min-width:0;" title="From special — ${escapeHtml(selectedMono.name || selectedMono.id)}">
                ${smallUrl ? `<img src="${smallUrl}" alt="" style="width:24px;height:24px;border-radius:3px;border:1px solid var(--border);object-fit:cover;flex-shrink:0;" loading="eager" onerror="this.style.display='none'; this.nextElementSibling && (this.nextElementSibling.style.display='block');">` : ''}<span style="width:24px;height:24px;border-radius:3px;background:#${(selectedMono.swatch || '888').replace('#','')};flex-shrink:0;${smallUrl ? 'display:none;' : ''}" class="ov-fb"></span>
                <span style="font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(selectedMono.name || selectedMono.id)}</span>
                <button type="button" class="btn btn-sm swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, '${popupType}', ${i});" style="font-size:9px;padding:2px 6px;">Change…</button>
            </div>
        </div>`;
    } else {
        html += `<div class="stack-control-group" style="flex-basis:100%;margin-top:4px;">
            <span class="stack-label-mini" style="margin-bottom:4px;">From special</span>
            <button type="button" class="btn btn-sm swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, '${popupType}', ${i});" style="font-size:9px;padding:2px 8px;">Choose special…</button>
        </div>`;
    }
    return html;
}

function renderSwatchSquare(finishId, fallbackColor, title, colorHex) {
    if (!finishId || finishId === 'none') {
        return `<div class="swatch-square" style="background:${fallbackColor || '#444'};" title="${title || ''}"></div>`;
    }
    const type = getFinishType(finishId);
    const isSplit = (type === 'pattern' || type === 'monolithic' || type === 'base');
    const url = getSwatchUrl(finishId, colorHex);  // pattern/mono/base get mode=split
    if (url) {
        // Split view: 72x36 (left=neutral/structure, right=with color). Single: 36x36
        const w = isSplit ? 72 : 36;
        const h = 36;
        const titleSafe = (title || '').replace(/"/g, '&quot;');
        const fallback = fallbackColor || '#444';
        return `<img class="swatch-square deferred-swatch${isSplit ? ' swatch-split' : ''}" data-swatch-url="${url}" title="${title || ''}" alt=""
                    loading="lazy" decoding="async"
                    style="width:${w}px;height:${h}px;border-radius:4px;border:1px solid rgba(255,255,255,0.12);object-fit:${isSplit ? 'contain' : 'cover'};"
                    onerror="this.outerHTML='<div class=&quot;swatch-square&quot; title=&quot;${titleSafe}&quot; style=&quot;width:${w}px;height:${h}px;background:${fallback};&quot;></div>'">`;
    }
    return `<div class="swatch-square" style="background:${fallbackColor || '#444'};" title="${title || ''}"></div>`;
}

function renderSwatchDot(finishId, fallbackColor, colorHex) {
    // Small inline dot for trigger buttons / zone cards - always single swatch, no split
    if (!finishId || finishId === 'none') {
        return `<div class="swatch-dot" style="background:${fallbackColor || '#444'};"></div>`;
    }
    const url = getSwatchUrl(finishId, colorHex, false);  // false = no split mode for dots
    if (url) {
        return `<img class="swatch-dot" src="${url}" loading="eager"
                    style="width:14px;height:14px;border-radius:3px;border:1px solid rgba(255,255,255,0.15);flex-shrink:0;object-fit:cover;"
                    onerror="this.outerHTML='<div class=&quot;swatch-dot&quot; style=&quot;background:${fallbackColor || '#444'};&quot;></div>'">`;
    }
    return `<div class="swatch-dot" style="background:${fallbackColor || '#444'};"></div>`;
}

function getSwatchColor(zone) {
    if (zone.finish) {
        const m = MONOLITHICS.find(x => x.id === zone.finish);
        return m ? m.swatch : '#444';
    }
    if (zone.base) {
        const b = BASES.find(x => x.id === zone.base);
        return b ? b.swatch : '#444';
    }
    return '#333';
}

function getPatternSwatchColor(patternId) {
    if (!patternId || patternId === 'none') return 'transparent';
    const p = PATTERNS.find(x => x.id === patternId);
    return p ? p.swatch : '#444';
}

// Extract zone's paint color as a 6-char hex string (no #) for /api/swatch tinting
function getZoneColorHex(zone) {
    let rgb = null;
    if (zone.color) {
        if (Array.isArray(zone.color) && zone.color.length > 0) {
            // Multi-color stack - use first color
            const first = zone.color[0];
            rgb = first.color_rgb || null;
        } else if (zone.color.color_rgb) {
            rgb = zone.color.color_rgb;
        }
    }
    if (!rgb || !Array.isArray(rgb) || rgb.length < 3) return '888888';
    const toHex = v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0');
    return toHex(rgb[0]) + toHex(rgb[1]) + toHex(rgb[2]);
}

function getBaseName(zone) {
    if (zone.finish) {
        const m = MONOLITHICS.find(x => x.id === zone.finish);
        return m ? m.name : '(not set)';
    }
    if (zone.base) {
        const b = BASES.find(x => x.id === zone.base);
        return b ? b.name : '(not set)';
    }
    return '(not set)';
}

function getPatternName(patternId) {
    if (!patternId || patternId === 'none') return 'None (Base Only)';
    const p = PATTERNS.find(x => x.id === patternId);
    return p ? p.name : patternId;
}

// Max pattern layers per zone: 1 primary + 4 stack = 5 total. Used for "React to Pattern 1/2/3/4/5" and stack limit.
const MAX_PATTERN_LAYERS_PER_ZONE = 5;
const MAX_PATTERN_STACK_LAYERS = MAX_PATTERN_LAYERS_PER_ZONE - 1; // 4

/** Build options for overlay "React to" dropdown: None (independent), Pattern 1 (primary), Pattern 2–5 from zone stack. Value '__none__' = independent, '' = zone primary. */
function getZonePatternReactOptions(zone) {
    const opts = [];
    opts.push({ value: '__none__', label: 'None (Independent)' });
    const primaryId = zone.pattern && zone.pattern !== 'none' ? zone.pattern : null;
    opts.push({ value: '', label: `Pattern 1 (${primaryId ? getPatternName(primaryId) : 'Primary - None'})` });
    const stack = zone.patternStack || [];
    if (stack[0] && stack[0].id && stack[0].id !== 'none') {
        opts.push({ value: stack[0].id, label: `Pattern 2 (${getPatternName(stack[0].id)})` });
    }
    if (stack[1] && stack[1].id && stack[1].id !== 'none') {
        opts.push({ value: stack[1].id, label: `Pattern 3 (${getPatternName(stack[1].id)})` });
    }
    if (stack[2] && stack[2].id && stack[2].id !== 'none') {
        opts.push({ value: stack[2].id, label: `Pattern 4 (${getPatternName(stack[2].id)})` });
    }
    if (stack[3] && stack[3].id && stack[3].id !== 'none') {
        opts.push({ value: stack[3].id, label: `Pattern 5 (${getPatternName(stack[3].id)})` });
    }
    return opts;
}

/** Current value for overlay "React to" select: '__none__' = independent, '' = Pattern 1 (primary), else the stored pattern ID. */
function getOverlayReactToSelectValue(zone, overlayPatternId) {
    if (overlayPatternId === '__none__') return '__none__';
    if (!overlayPatternId || overlayPatternId === 'none') return '';
    const stack = zone.patternStack || [];
    if (stack[0] && overlayPatternId === stack[0].id) return overlayPatternId;
    if (stack[1] && overlayPatternId === stack[1].id) return overlayPatternId;
    if (stack[2] && overlayPatternId === stack[2].id) return overlayPatternId;
    if (stack[3] && overlayPatternId === stack[3].id) return overlayPatternId;
    if (zone.pattern && overlayPatternId === zone.pattern) return '';
    return overlayPatternId; // legacy: show as-is (Pattern 1 if matches primary)
}

function openSwatchPicker(triggerEl, type, zoneIndex, layerIndex) {
    const popup = document.getElementById('swatchPopup');
    const grid = document.getElementById('swatchPopupGrid');
    const searchInput = document.getElementById('swatchSearchInput');

    // Close if same trigger clicked again
    if (swatchPopupState.open && swatchPopupState.type === type &&
        swatchPopupState.zoneIndex === zoneIndex && swatchPopupState.layerIndex === (layerIndex ?? -1)) {
        closeSwatchPicker();
        return;
    }

    swatchPopupState = { open: true, type, zoneIndex, layerIndex: layerIndex ?? -1 };

    // Determine current selection
    const zone = zones[zoneIndex];
    let currentId = '';
    if (type === 'base') {
        currentId = zone.finish ? ('mono:' + zone.finish) : (zone.base || '');
    } else if (type === 'pattern') {
        currentId = zone.pattern || 'none';
    } else if (type === 'stackPattern') {
        currentId = (zone.patternStack && zone.patternStack[layerIndex]) ? zone.patternStack[layerIndex].id : 'none';
    } else if (type === 'secondBase') {
        currentId = zone.secondBase || '';
    } else if (type === 'thirdBase') {
        currentId = zone.thirdBase || '';
    } else if (type === 'fourthBase') {
        currentId = zone.fourthBase || '';
    } else if (type === 'fifthBase') {
        currentId = zone.fifthBase || '';
    } else if (type === 'baseColorSource') {
        currentId = zone.baseColorSource || '';
    } else if (type === 'secondBaseColorSource') {
        currentId = zone.secondBaseColorSource || '';
    } else if (type === 'thirdBaseColorSource') {
        currentId = zone.thirdBaseColorSource || '';
    } else if (type === 'fourthBaseColorSource') {
        currentId = zone.fourthBaseColorSource || '';
    } else if (type === 'fifthBaseColorSource') {
        currentId = zone.fifthBaseColorSource || '';
    } else if (type === 'secondBasePattern') {
        currentId = zone.secondBasePattern || 'none';
    } else if (type === 'thirdBasePattern') {
        currentId = zone.thirdBasePattern || 'none';
    } else if (type === 'layerSpecialPaint') {
        currentId = (typeof getLayerPaintSpecialId === 'function' && getLayerPaintSpecialId())
            ? ('mono:' + getLayerPaintSpecialId())
            : '';
    }

    // Build grid HTML with canvas-rendered previews
    const _nameSort = (a, b) => (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' });
    let html = '';
    const isOverlaySpecialSourcePicker = (type === 'secondBaseColorSource' || type === 'thirdBaseColorSource' || type === 'fourthBaseColorSource' || type === 'fifthBaseColorSource');
    const isOverlayBaseColorPicker = (type === 'overlayBaseColor');
    const isLayerSpecialPaintPicker = (type === 'layerSpecialPaint');
    if (type === 'base' || type === 'secondBase' || type === 'thirdBase' || type === 'fourthBase' || type === 'fifthBase' || type === 'baseColorSource' || isOverlaySpecialSourcePicker || isOverlayBaseColorPicker || isLayerSpecialPaintPicker) {
        // Bases section - grouped by BASE_GROUPS with collapsible sections
        if (!isOverlaySpecialSourcePicker && !isLayerSpecialPaintPicker) {
            html += `<div class="swatch-item${currentId === '' ? ' selected' : ''}" data-name="not set none clear" onclick="selectSwatchItem('')" style="margin-bottom:4px;">
            <div class="swatch-square" style="background:#333;display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:10px;">&#8709;</div>
            <div class="swatch-label">(not set)</div></div>`;
            const baseGroupedIds = new Set();
            Object.keys(BASE_GROUPS).sort((a, b) => a === 'Foundation' ? -1 : b === 'Foundation' ? 1 : a.localeCompare(b)).forEach(groupName => {
            const ids = BASE_GROUPS[groupName];
            if (!ids || ids.length === 0) return;
            const groupBases = ids.map(id => BASES.find(b => b.id === id)).filter(Boolean).sort(_nameSort);
            if (groupBases.length === 0) return;
            groupBases.forEach(b => baseGroupedIds.add(b.id));
            const collapsed = groupName !== 'Foundation';
            html += `<div class="swatch-group${collapsed ? ' collapsed' : ''}">`;
            html += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupBases.length})</span></div>`;
            html += `<div class="swatch-grid-row">`;
            groupBases.forEach(b => {
                const ft = typeof getFinishType === 'function' ? getFinishType(b.id) : 'base';
                html += `<div class="swatch-item${currentId === b.id ? ' selected' : ''}" data-name="${b.name.toLowerCase()}" data-finish-id="${b.id}" data-finish-type="${ft || 'base'}" data-desc="${(b.desc || b.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${b.id}')">
                    ${renderSwatchSquare(b.id, b.swatch, b.desc)}
                    <div class="swatch-label">${b.colorSafe ? '<span style="color:#22c55e;font-size:8px;margin-right:2px;" title="Color-safe: won\'t change your car\'s base color">●</span>' : ''}${b.name}</div></div>`;
            });
            html += `</div></div>`;
            });
            // Ungrouped bases (safety net) — exclude bases that moved to SPECIAL_GROUPS
            const specialIds = new Set();
            if (typeof SPECIAL_GROUPS !== 'undefined') Object.values(SPECIAL_GROUPS).forEach(ids => { if (Array.isArray(ids)) ids.forEach(id => specialIds.add(id)); });
            const ungroupedBases = BASES.filter(b => !baseGroupedIds.has(b.id) && !specialIds.has(b.id));
            if (ungroupedBases.length > 0) {
            html += `<div class="swatch-group"><div class="swatch-group-label">Other Bases <span class="swatch-group-count">(${ungroupedBases.length})</span></div><div class="swatch-grid-row">`;
            ungroupedBases.forEach(b => {
                const ft = typeof getFinishType === 'function' ? getFinishType(b.id) : 'base';
                html += `<div class="swatch-item${currentId === b.id ? ' selected' : ''}" data-name="${b.name.toLowerCase()}" data-finish-id="${b.id}" data-finish-type="${ft || 'base'}" data-desc="${(b.desc || b.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${b.id}')">
                    ${renderSwatchSquare(b.id, b.swatch, b.desc)}
                    <div class="swatch-label">${b.colorSafe ? '<span style="color:#22c55e;font-size:8px;margin-right:2px;" title="Color-safe: won\'t change your car\'s base color">●</span>' : ''}${b.name}</div></div>`;
            });
            html += '</div></div>';
            }
        }
        // Special paints (monolithics): primary base and all overlay base pickers (2nd–5th)
        if (type === 'base' || type === 'secondBase' || type === 'thirdBase' || type === 'fourthBase' || type === 'fifthBase' || type === 'baseColorSource' || isOverlaySpecialSourcePicker || isLayerSpecialPaintPicker) {
            const groupedIds = new Set();
            const COLOR_CHANGING_GROUPS = new Set(["Chameleon Classic", "Prizm Series"]);
            const SECTION_ICONS = { "Color-Changing": "🎨", "Effects & Aesthetic": "✨", "PARADIGM": "◇", "Shokk Series": "⚡", "Weather & Element": "🌤", "Gradients": "〰", "Multi": "🔀", "FUSIONS": "◈" };

            function renderGroupSection(groups, sectionLabel, sectionIcon) {
                if (!groups || groups.length === 0) return '';
                let s = `<div class="swatch-section-divider" style="margin:10px 0 6px; padding:6px 8px; background:var(--bg-dark); border:1px solid var(--border); border-radius:6px; display:flex; align-items:center; gap:6px;">
                <span style="font-size:12px;">${sectionIcon || '•'}</span>
                <span style="font-size:11px; font-weight:700; color:var(--accent-green); text-transform:uppercase; letter-spacing:1px;">${sectionLabel}</span>
                <span style="font-size:9px; color:var(--text-dim); margin-left:auto;">${groups.reduce((n, g) => n + (SPECIAL_GROUPS[g] || []).length, 0)} finishes</span>
            </div>`;
                groups.forEach(groupName => {
                    const ids = SPECIAL_GROUPS[groupName];
                    if (!ids) return;
                    const groupMonos = ids.map(id => MONOLITHICS.find(m => m.id === id) || (typeof BASES !== 'undefined' && BASES.find(b => b.id === id))).filter(Boolean);
                    if (groupMonos.length === 0) return;
                    groupMonos.forEach(m => groupedIds.add(m.id));
                    const hasSelected = groupMonos.some(m => 'mono:' + m.id === currentId);
                    const isColorGroup = groupName.startsWith('Solid') || groupName.startsWith('Gradient') || groupName.startsWith('Multi');
                    const collapsed = isColorGroup && !hasSelected;
                    s += `<div class="swatch-group${collapsed ? ' collapsed' : ''}">`;
                    s += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupMonos.length})</span></div>`;
                    s += `<div class="swatch-grid-row">`;
                    groupMonos.forEach(m => {
                        s += `<div class="swatch-item${currentId === 'mono:' + m.id ? ' selected' : ''}" data-name="${m.name.toLowerCase()}" data-finish-id="${m.id}" data-finish-type="monolithic" data-desc="${(m.desc || m.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('mono:${m.id}')">
                        ${renderSwatchSquare(m.id, m.swatch, m.desc)}
                        <div class="swatch-label">${m.name}</div></div>`;
                    });
                    s += `</div></div>`;
                });
                return s;
            }

            if (typeof SPECIALS_SECTION_ORDER !== 'undefined' && typeof SPECIALS_SECTIONS !== 'undefined') {
                const renderedGroups = new Set();
                SPECIALS_SECTION_ORDER.forEach(sectionKey => {
                    const groupNames = SPECIALS_SECTIONS[sectionKey];
                    const list = Array.isArray(groupNames) ? groupNames : [];
                    list.forEach(g => renderedGroups.add(g));
                    html += renderGroupSection(list, sectionKey, SECTION_ICONS[sectionKey]);
                });
                // Groups merged from COLOR_MONO_GROUPS (Solid *, Gradient, Ghost Gradient, etc.) not in SPECIALS_SECTIONS
                const remaining = Object.keys(SPECIAL_GROUPS).filter(g => !renderedGroups.has(g));
                if (remaining.length > 0) {
                    html += renderGroupSection(remaining, 'Solid & Gradients', '〰');
                }
            } else {
                const allGroupNames = Object.keys(SPECIAL_GROUPS).sort();
                const colorChangingGroups = allGroupNames.filter(g => COLOR_CHANGING_GROUPS.has(g));
                const effectGroups = allGroupNames.filter(g => !COLOR_CHANGING_GROUPS.has(g));
                html += renderGroupSection(colorChangingGroups, 'Color-Changing Finishes', '🎨');
                html += renderGroupSection(effectGroups, 'Effect Finishes (keeps paint color)', '✨');
            }
            // No ungrouped monolithic "Other" bucket in Alpha UX.
            // Shipping special surfaces must stay inside SPECIAL_GROUPS so
            // legacy / unsorted registry leftovers cannot leak back into the picker.
        }
    }
    if (type === 'pattern' || type === 'stackPattern' || type === 'secondBasePattern' || type === 'thirdBasePattern') {
        // Pattern / stackPattern - grouped by PATTERN_GROUPS with collapsible sections
        const noneLabel = (type === 'secondBasePattern' || type === 'thirdBasePattern') ? '- Zone primary -' : 'None';
        html += `<div class="swatch-item${(currentId === 'none' || currentId === '') ? ' selected' : ''}" data-name="none not set clear" onclick="selectSwatchItem('${(type === 'secondBasePattern' || type === 'thirdBasePattern') ? '' : 'none'}')" style="margin-bottom:4px;">
            <div class="swatch-square" style="background:#333;display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:10px;">&#8709;</div>
            <div class="swatch-label">${noneLabel}</div></div>`;
        Object.keys(PATTERN_GROUPS).sort((a, b) => a === 'Abstract & Experimental' ? -1 : b === 'Abstract & Experimental' ? 1 : a.localeCompare(b)).forEach(groupName => {
            const ids = PATTERN_GROUPS[groupName];
            if (!ids || ids.length === 0) return;
            const groupPats = ids.map(id => PATTERNS.find(p => p.id === id)).filter(Boolean).sort(_nameSort);
            if (groupPats.length === 0) return;
            const collapsed = groupName !== 'Abstract & Experimental';
            html += `<div class="swatch-group${collapsed ? ' collapsed' : ''}">`;
            html += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupPats.length})</span></div>`;
            html += `<div class="swatch-grid-row">`;
            groupPats.forEach(p => {
                html += `<div class="swatch-item${currentId === p.id ? ' selected' : ''}" data-name="${p.name.toLowerCase()}" data-finish-id="${p.id}" data-finish-type="pattern" data-desc="${(p.desc || p.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${p.id}')">
                    ${renderSwatchSquare(p.id, p.swatch, p.desc)}
                    <div class="swatch-label">${p.name}</div></div>`;
            });
            html += `</div></div>`;
        });
        // No ungrouped "Other" pattern bucket in Alpha UX.
    }

    grid.innerHTML = html;
    _installSwatchPopupLazyLoader();

    // Position popup near trigger
    const rect = triggerEl.getBoundingClientRect();
    const popupW = 480;
    const popupH = Math.min(520, window.innerHeight - 40);

    let left = rect.right + 8;
    if (left + popupW > window.innerWidth - 10) left = rect.left - popupW - 8;
    if (left < 10) left = 10;

    let top = rect.top;
    if (top + popupH > window.innerHeight - 10) top = window.innerHeight - popupH - 10;
    if (top < 10) top = 10;

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.classList.add('active');

    searchInput.value = '';
    setTimeout(() => searchInput.focus(), 50);
}

function closeSwatchPicker() {
    const popup = document.getElementById('swatchPopup');
    if (popup) popup.classList.remove('active');
    _disconnectSwatchPopupLazyLoader();
    swatchPopupState = { open: false, type: null, zoneIndex: -1, layerIndex: -1 };
}

// ----- Swatch Preview Modal: see exactly what a finish does on your paint -----
let swatchPreviewState = { finishType: null, finishId: null, label: '' };

function openSwatchPreviewFromPicker() {
    const grid = document.getElementById('swatchPopupGrid');
    const selected = grid ? grid.querySelector('.swatch-item.selected') : null;
    if (!selected) {
        if (typeof showToast === 'function') showToast('Select a finish first (click one in the list).', true);
        return;
    }
    const id = selected.getAttribute('data-finish-id');
    let ft = selected.getAttribute('data-finish-type');
    if (!ft && typeof getFinishType === 'function') ft = getFinishType(id);
    if (!id || id === 'none' || id === '') {
        if (typeof showToast === 'function') showToast('Select a specific finish to preview.', true);
        return;
    }
    const label = selected.querySelector('.swatch-label') ? selected.querySelector('.swatch-label').textContent : id;
    openSwatchPreviewModal(ft || 'base', id, label);
}

function openSwatchPreviewModal(finishType, finishId, label) {
    swatchPreviewState = { finishType: finishType || 'base', finishId: finishId, label: label || finishId };
    const modal = document.getElementById('swatchPreviewModal');
    const titleEl = document.getElementById('swatchPreviewModalTitle');
    const imgEl = document.getElementById('swatchPreviewLargeImg');
    const wrap = document.getElementById('swatchPreviewOnPaintWrap');
    if (!modal || !imgEl) return;
    titleEl.textContent = label || finishId;
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    imgEl.src = `${base}/api/swatch/${finishType}/${finishId}?color=888888&size=256&v=${Date.now()}`;
    imgEl.onerror = function () { this.style.background = '#333'; this.alt = 'Swatch failed to load'; };
    wrap.innerHTML = '<span style="color:var(--text-dim); font-size:11px;">Click &quot;Preview on paint&quot; to see this finish on your loaded paint.</span>';
    modal.style.display = 'flex';
    modal.onclick = function (e) { if (e.target === modal) closeSwatchPreviewModal(); };
    const btn = document.getElementById('swatchPreviewOnPaintBtn');
    if (btn) btn.onclick = runSwatchPreviewOnPaint;
}

function closeSwatchPreviewModal() {
    const modal = document.getElementById('swatchPreviewModal');
    if (modal) modal.style.display = 'none';
}

async function runSwatchPreviewOnPaint() {
    const { finishType, finishId } = swatchPreviewState;
    const paintFile = document.getElementById('paintFile') ? document.getElementById('paintFile').value.trim() : '';
    if (!paintFile || (!paintFile.includes('/') && !paintFile.includes('\\'))) {
        if (typeof showToast === 'function') showToast('Load a paint file first (Car Info / Source Paint).', true);
        return;
    }
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    const zone = { name: 'Preview', color: 'remaining', intensity: '100' };
    if (finishType === 'base') {
        zone.base = finishId;
        zone.pattern = 'none';
    } else if (finishType === 'pattern') {
        zone.base = 'living_matte';
        zone.pattern = finishId;
    } else {
        zone.finish = finishId;
        const m = (typeof MONOLITHICS !== 'undefined' && MONOLITHICS.find(x => x.id === finishId)) || (typeof BASES !== 'undefined' && BASES.find(x => x.id === finishId));
        if (m && (m.swatch || m.swatch2 || m.swatch3)) zone.finish_colors = { c1: m.swatch, c2: m.swatch2 || null, c3: m.swatch3 || null, ghost: m.ghostPattern || null };
    }
    const wrap = document.getElementById('swatchPreviewOnPaintWrap');
    const btn = document.getElementById('swatchPreviewOnPaintBtn');
    if (wrap) wrap.innerHTML = '<span style="color:var(--text-dim);">Rendering...</span>';
    if (btn) btn.disabled = true;
    try {
        const resp = await fetch(base + '/preview-render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paint_file: paintFile, zones: [zone], seed: 51, preview_scale: 0.25 }),
        });
        const data = await resp.json();
        if (data.success && data.paint_preview) {
            wrap.innerHTML = '';
            const img = document.createElement('img');
            img.src = data.paint_preview;
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'contain';
            img.style.borderRadius = '6px';
            wrap.appendChild(img);
        } else {
            wrap.innerHTML = '<span style="color:#cc6666;">Preview failed</span>';
        }
    } catch (e) {
        if (wrap) wrap.innerHTML = '<span style="color:#cc6666;">Request failed</span>';
        if (typeof showToast === 'function') showToast('Preview failed. Is the server running?', true);
    }
    if (btn) btn.disabled = false;
}

// ----- end Swatch Preview Modal -----

function filterSwatchPopup(query) {
    const grid = document.getElementById('swatchPopupGrid');
    const items = grid.querySelectorAll('.swatch-item');
    const q = query.toLowerCase().trim();
    items.forEach(item => {
        const name = item.getAttribute('data-name') || '';
        const desc = (item.getAttribute('data-desc') || '').toLowerCase();
        item.style.display = (!q || name.includes(q) || desc.includes(q)) ? '' : 'none';
    });
    // Show/hide groups based on visible items; expand all when searching
    const groups = grid.querySelectorAll('.swatch-group');
    groups.forEach(grp => {
        const visibleItems = grp.querySelectorAll('.swatch-item:not([style*="display: none"])');
        grp.style.display = (q && visibleItems.length === 0) ? 'none' : '';
        if (q) grp.classList.remove('collapsed');
        else if (visibleItems.length > 0 && !grp.querySelector('.swatch-item.selected')) grp.classList.add('collapsed');
    });
    _installSwatchPopupLazyLoader();
}

function selectSwatchItem(id) {
    const { type, zoneIndex, layerIndex } = swatchPopupState;
    // Intercept: custom color shift opens the modal instead of setting a finish
    if ((id === 'dualshift_custom' || id === 'cx_custom_shift') && type === 'base') {
        closeSwatchPicker();
        if (typeof openDualShiftModal === 'function') openDualShiftModal(zoneIndex);
        return;
    }
    if (type === 'base') {
        setZoneBase(zoneIndex, id);
    } else if (type === 'pattern') {
        setZonePattern(zoneIndex, id);
    } else if (type === 'stackPattern') {
        setPatternLayerId(zoneIndex, layerIndex, id);
    } else if (type === 'secondBase') {
        setZoneSecondBase(zoneIndex, id || '');
    } else if (type === 'thirdBase') {
        setZoneThirdBase(zoneIndex, id || '');
    } else if (type === 'fourthBase') {
        setZoneFourthBase(zoneIndex, id || '');
    } else if (type === 'fifthBase') {
        setZoneFifthBase(zoneIndex, id || '');
    } else if (type === 'baseColorSource') {
        setZoneBaseColorSource(zoneIndex, id || null);
    } else if (type === 'overlayBaseColor') {
        // "From base" overlay color — set the color source to 'base:<id>' and extract the base's paint color
        if (id) {
            setZoneSecondBaseColorSource(zoneIndex, 'base:' + id);
            // Try to extract the base's representative color from BASES array
            const basesArr = (typeof BASES !== 'undefined' ? BASES : null) || (typeof window.BASES !== 'undefined' ? window.BASES : null) || [];
            const baseObj = basesArr.find(b => b.id === id);
            if (baseObj && baseObj.swatch) {
                setZoneSecondBaseColor(zoneIndex, baseObj.swatch);
            }
        }
    } else if (type === 'secondBaseColorSource') {
        setZoneSecondBaseColorSource(zoneIndex, id || null);
    } else if (type === 'thirdBaseColorSource') {
        setZoneThirdBaseColorSource(zoneIndex, id || null);
    } else if (type === 'fourthBaseColorSource') {
        setZoneFourthBaseColorSource(zoneIndex, id || null);
    } else if (type === 'fifthBaseColorSource') {
        setZoneFifthBaseColorSource(zoneIndex, id || null);
    } else if (type === 'secondBasePattern') {
        setZoneSecondBasePattern(zoneIndex, (id === 'none' || id === '') ? '' : id);
    } else if (type === 'thirdBasePattern') {
        setZoneThirdBasePattern(zoneIndex, (id === 'none' || id === '') ? '' : id);
    } else if (type === 'layerSpecialPaint') {
        if (typeof setLayerPaintSpecial === 'function') setLayerPaintSpecial((id || '').replace(/^mono:/, ''));
    }
    closeSwatchPicker();
}

// Close swatch picker on click outside
document.addEventListener('mousedown', function (e) {
    if (!swatchPopupState.open) return;
    const popup = document.getElementById('swatchPopup');
    if (!popup.contains(e.target) && !e.target.closest('.swatch-trigger')) {
        closeSwatchPicker();
    }
});
// Close swatch picker on Escape
// SESSION ROUTER: bail on defaultPrevented (transform Esc wins first).
document.addEventListener('keydown', function (e) {
    if (e.defaultPrevented) return;
    if (e.key === 'Escape' && swatchPopupState.open) {
        closeSwatchPicker();
        e.stopPropagation();
    }
});

// ===== FINISH SELECTORS =====
// ===== ZONE LINKING / GROUPS =====
let nextLinkGroupId = 1;

function linkZones(indices) {
    if (!indices || indices.length < 2) return;
    pushZoneUndo('Link ' + indices.length + ' zones');
    const groupId = 'link_' + (nextLinkGroupId++);
    indices.forEach(i => { if (zones[i]) zones[i].linkGroup = groupId; });
    renderZones();
    showToast(`Linked ${indices.length} zones (Group ${groupId.replace('link_', '')})`);
}

function unlinkZone(index) {
    if (!zones[index] || !zones[index].linkGroup) return;
    pushZoneUndo('Unlink zone "' + zones[index].name + '"');
    const group = zones[index].linkGroup;
    zones[index].linkGroup = null;
    // If only 1 zone left in group, auto-unlink it too
    const remaining = zones.filter(z => z.linkGroup === group);
    if (remaining.length === 1) remaining[0].linkGroup = null;
    renderZones();
    showToast('Zone unlinked');
}

function linkSelectedToZone(targetIndex) {
    // Link the currently selected zone to the target zone's group (or create new group)
    const srcIdx = selectedZoneIndex;
    if (srcIdx < 0 || srcIdx === targetIndex) return;
    pushZoneUndo('Link zone ' + (srcIdx+1) + ' \u2194 ' + (targetIndex+1));
    if (zones[targetIndex].linkGroup) {
        zones[srcIdx].linkGroup = zones[targetIndex].linkGroup;
    } else {
        const groupId = 'link_' + (nextLinkGroupId++);
        zones[srcIdx].linkGroup = groupId;
        zones[targetIndex].linkGroup = groupId;
    }
    renderZones();
    showToast(`Zones linked together`);
}

function propagateToLinkedZones(sourceIndex, props) {
    // Copy finish properties from source zone to all zones in the same link group
    const zone = zones[sourceIndex];
    if (!zone || !zone.linkGroup) return;
    zones.forEach((z, i) => {
        if (i === sourceIndex || z.linkGroup !== zone.linkGroup) return;
        props.forEach(p => { z[p] = zone[p]; });
    });
}

const LINK_FINISH_PROPS = ['base', 'pattern', 'finish', 'intensity', 'scale', 'rotation',
    'patternOpacity', 'customSpec', 'customPaint', 'customBright', 'patternStack', 'wear',
    'baseColorMode', 'baseColor', 'baseColorSource', 'baseColorStrength',
    'gradientStops', 'gradientDirection', '_autoBaseColorFill'];

function promptLinkZone(index) {
    if (zones[index].linkGroup) {
        // Already linked - offer to unlink
        unlinkZone(index);
        return;
    }
    // Show a simple picker: which zone to link with?
    const options = zones.map((z, i) => i === index ? null : `${i + 1}. ${z.name}`).filter(Boolean);
    const choice = prompt(`Link "${zones[index].name}" with which zone?\n\n${options.join('\n')}\n\nEnter zone number:`);
    if (!choice) return;
    const targetIdx = parseInt(choice) - 1;
    if (isNaN(targetIdx) || targetIdx < 0 || targetIdx >= zones.length || targetIdx === index) {
        showToast('Invalid zone number');
        return;
    }
    pushZoneUndo('Link "' + zones[index].name + '" + "' + zones[targetIdx].name + '"');
    if (zones[targetIdx].linkGroup) {
        zones[index].linkGroup = zones[targetIdx].linkGroup;
    } else {
        const groupId = 'link_' + (nextLinkGroupId++);
        zones[index].linkGroup = groupId;
        zones[targetIdx].linkGroup = groupId;
    }
    // Copy finish from target to source so they match
    LINK_FINISH_PROPS.forEach(p => { zones[index][p] = zones[targetIdx][p]; });
    renderZones();
    triggerPreviewRender();
    showToast(`Linked: ${zones[index].name} + ${zones[targetIdx].name}`);
}

function setZoneBase(index, value) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] setZoneBase: invalid zone index', index);
        return;
    }
    if (value !== null && value !== undefined && typeof value !== 'string') {
        console.warn('[SPB] setZoneBase: value must be a string or null, got', typeof value);
        return;
    }
    pushZoneUndo('Set base: ' + (value || 'none'));
    if (value && value.startsWith('mono:')) {
        const monoId = value.replace('mono:', '');
        // Check if this "mono:" ID is actually a base-registered finish (migrated from Bases to Specials)
        const isBase = typeof BASES !== 'undefined' && BASES.find(b => b.id === monoId);
        if (isBase) {
            // Migrated base finish — keep base-picker behavior aligned with the
            // finish browser so material bases don't inherit stale auto tints.
            _spbApplyPickedBaseToZone(zones[index], monoId);
        } else {
            // True monolithic — set as finish
            _spbApplyPickedMonolithicToZone(zones[index], monoId);
        }
        // Don't clear pattern/patternStack - user may want patterns on top of specials
        if (!zones[index].pattern) zones[index].pattern = 'none';
    } else {
        _spbApplyPickedBaseToZone(zones[index], value || null);
    }
    propagateToLinkedZones(index, LINK_FINISH_PROPS);
    renderZones();
    triggerPreviewRender();
}
function setZoneBaseColorMode(index, value) {
    pushZoneUndo('Set base color mode', true);
    const mode = (value === 'solid' || value === 'special' || value === 'gradient') ? value : 'source';
    zones[index].baseColorMode = mode;
    zones[index]._autoBaseColorFill = false;
    zones[index]._scopedBrushAutoBaseColor = false;
    if (!zones[index].baseColor) zones[index].baseColor = '#ffffff';
    if (zones[index].baseColorStrength == null) zones[index].baseColorStrength = 1;
    if (mode !== 'special') zones[index].baseColorSource = null;
    if (mode === 'gradient' && (!zones[index].gradientStops || zones[index].gradientStops.length < 2)) {
        zones[index].gradientStops = [
            { pos: 0, color: '#000000' },
            { pos: 100, color: '#ffffff' },
        ];
        zones[index].gradientDirection = 'horizontal';
    }
    renderZoneDetail(index);
    triggerPreviewRender();
}

// ---- Custom Gradient Editor Functions ----

function _buildGradientEditorHTML(zoneIdx, zone) {
    const stops = zone.gradientStops || [{ pos: 0, color: '#000000' }, { pos: 100, color: '#ffffff' }];
    const dir = zone.gradientDirection || 'horizontal';
    const cssGrad = _buildCSSGradient(stops, dir);
    let stopsHTML = '';
    for (let s = 0; s < stops.length; s++) {
        const canDelete = stops.length > 2;
        stopsHTML += `<div class="gradient-stop-row" style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
            <input type="color" value="${stops[s].color}" onchange="setGradientStopColor(${zoneIdx}, ${s}, this.value)" style="width:28px;height:22px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
            <input type="range" min="0" max="100" step="1" value="${stops[s].pos}" oninput="setGradientStopPos(${zoneIdx}, ${s}, this.value)" class="stack-slider" style="width:80px;" title="Position ${stops[s].pos}%">
            <span class="stack-val" style="min-width:28px;font-size:9px;">${stops[s].pos}%</span>
            ${canDelete ? `<button class="btn btn-sm" onclick="event.stopPropagation(); removeGradientStop(${zoneIdx}, ${s})" title="Remove stop" style="padding:0 4px;font-size:9px;color:#ff5555;border-color:#ff555533;">x</button>` : ''}
        </div>`;
    }
    return `</div>
        <div class="gradient-editor" style="width:100%;margin-top:4px;">
            <div class="gradient-bar" id="gradBar_${zoneIdx}" onclick="addGradientStopAtClick(${zoneIdx}, event)" title="Click to add a color stop" style="width:100%;height:20px;border-radius:4px;border:1px solid var(--border);cursor:crosshair;background:${cssGrad};margin-bottom:6px;"></div>
            <div class="gradient-stops">${stopsHTML}</div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:4px;flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:55px;">Direction</span>
                <select class="mini-select" style="min-width:140px;flex:1;max-width:180px;" onchange="setGradientDirection(${zoneIdx}, this.value)">
                    <option value="horizontal" ${dir === 'horizontal' ? 'selected' : ''}>&#x2190; &#x2192; Horizontal</option>
                    <option value="vertical" ${dir === 'vertical' ? 'selected' : ''}>&#x2191; &#x2193; Vertical</option>
                    <option value="diagonal_down" ${dir === 'diagonal_down' ? 'selected' : ''}>&#x2198; Diagonal Down</option>
                    <option value="diagonal_up" ${dir === 'diagonal_up' ? 'selected' : ''}>&#x2197; Diagonal Up</option>
                    <option value="radial" ${dir === 'radial' ? 'selected' : ''}>&#x25CE; Radial</option>
                    <option value="angular" ${dir === 'angular' ? 'selected' : ''}>&#x21BB; Angular</option>
                </select>
                ${stops.length < 10 ? `<button class="btn btn-sm" onclick="event.stopPropagation(); addGradientStop(${zoneIdx})" style="padding:2px 8px;font-size:9px;border-color:var(--accent-blue);color:var(--accent-blue);">+ Add Stop</button>` : ''}
            </div>
        </div>
    <div style="display:flex; align-items:center; gap:8px; width:100%; flex-wrap:wrap;">`;
}

function _buildCSSGradient(stops, direction) {
    if (!stops || stops.length < 2) return 'linear-gradient(to right, #000, #fff)';
    const sorted = [...stops].sort((a, b) => a.pos - b.pos);
    const colorStops = sorted.map(s => `${s.color} ${s.pos}%`).join(', ');
    if (direction === 'radial') return `radial-gradient(circle, ${colorStops})`;
    if (direction === 'angular') return `conic-gradient(from 0deg, ${colorStops})`;
    const dirMap = {
        horizontal: 'to right',
        vertical: 'to bottom',
        diagonal_down: 'to bottom right',
        diagonal_up: 'to top right',
    };
    return `linear-gradient(${dirMap[direction] || 'to right'}, ${colorStops})`;
}

function setGradientStopColor(zoneIdx, stopIdx, color) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].gradientStops) return;
    zones[zoneIdx].gradientStops[stopIdx].color = color;
    _refreshGradientBar(zoneIdx);
    triggerPreviewRender();
}

function setGradientStopPos(zoneIdx, stopIdx, val) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].gradientStops) return;
    zones[zoneIdx].gradientStops[stopIdx].pos = Math.max(0, Math.min(100, parseInt(val) || 0));
    _refreshGradientBar(zoneIdx);
    triggerPreviewRender();
}

function setGradientDirection(zoneIdx, dir) {
    pushZoneUndo('Set gradient direction', true);
    zones[zoneIdx].gradientDirection = dir;
    _refreshGradientBar(zoneIdx);
    triggerPreviewRender();
}

function addGradientStop(zoneIdx) {
    pushZoneUndo('Add gradient stop', true);
    const stops = zones[zoneIdx].gradientStops || [];
    if (stops.length >= 10) { if (typeof showToast === 'function') showToast('Maximum 10 gradient stops'); return; }
    // Insert at midpoint between last two stops
    const last = stops[stops.length - 1] || { pos: 100, color: '#ffffff' };
    const prev = stops.length >= 2 ? stops[stops.length - 2] : { pos: 0, color: '#000000' };
    const midPos = Math.round((prev.pos + last.pos) / 2);
    stops.push({ pos: midPos, color: '#888888' });
    zones[zoneIdx].gradientStops = stops;
    renderZoneDetail(zoneIdx);
    triggerPreviewRender();
}

function addGradientStopAtClick(zoneIdx, event) {
    const stops = zones[zoneIdx].gradientStops || [];
    if (stops.length >= 10) { if (typeof showToast === 'function') showToast('Maximum 10 gradient stops'); return; }
    const bar = event.currentTarget;
    const rect = bar.getBoundingClientRect();
    const pos = Math.round(Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100)));
    pushZoneUndo('Add gradient stop', true);
    stops.push({ pos: pos, color: '#888888' });
    zones[zoneIdx].gradientStops = stops;
    renderZoneDetail(zoneIdx);
    triggerPreviewRender();
}

function removeGradientStop(zoneIdx, stopIdx) {
    const stops = zones[zoneIdx].gradientStops || [];
    if (stops.length <= 2) return;
    pushZoneUndo('Remove gradient stop', true);
    stops.splice(stopIdx, 1);
    zones[zoneIdx].gradientStops = stops;
    renderZoneDetail(zoneIdx);
    triggerPreviewRender();
}

function _refreshGradientBar(zoneIdx) {
    const bar = document.getElementById('gradBar_' + zoneIdx);
    if (!bar) return;
    const stops = zones[zoneIdx].gradientStops || [];
    const dir = zones[zoneIdx].gradientDirection || 'horizontal';
    bar.style.background = _buildCSSGradient(stops, dir);
}
function setZoneBaseColor(index, val) {
    pushZoneUndo('Set base color', true);
    val = (val || '').trim();
    if (val && !val.startsWith('#')) val = '#' + val;
    if (val && !/^#[0-9A-Fa-f]{6}$/.test(val)) {
        showToast('Enter a valid hex code like #FF3366', true);
        renderZoneDetail(index);
        return;
    }
    zones[index].baseColor = val || '#ffffff';
    if (!zones[index].baseColorMode || zones[index].baseColorMode === 'source') zones[index].baseColorMode = 'solid';
    zones[index]._autoBaseColorFill = false;
    zones[index]._scopedBrushAutoBaseColor = false;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBaseColorSource(index, val) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    pushZoneUndo('Set base color source', true);
    // Accept any finish ID as base color source — mono:, base:, pattern:, or raw ID
    let src = null;
    if (val && typeof val === 'string') {
        // If it already has a prefix (mono:, base:, pattern:), keep it
        // Otherwise treat it as a raw finish ID and accept it as-is
        src = val.trim() || null;
    }
    zones[index].baseColorSource = src;
    if (src) zones[index].baseColorMode = 'special';
    zones[index]._autoBaseColorFill = false;
    zones[index]._scopedBrushAutoBaseColor = false;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBaseColorStrength(index, val) {
    pushZoneUndo('', true);
    const n = Math.max(0, Math.min(100, parseInt(val) || 0));
    zones[index].baseColorStrength = n / 100;
    const pct = Math.round((zones[index].baseColorStrength ?? 1) * 100);
    const el = document.getElementById('detBaseColorStrVal' + index);
    if (el) el.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        const span = panel.querySelector('#detBaseColorStrVal' + index);
        if (span) span.textContent = pct + '%';
    }
    triggerPreviewRender();
}
function stepZoneBaseColorStrength(index, delta) {
    const cur = Math.round((zones[index].baseColorStrength ?? 1) * 100);
    setZoneBaseColorStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
// Fit-to-Selection: when ON, the full base color source + base spec compress
// into the zone mask's bounding box instead of being cropped by it. Solves the
// "I drew a small rectangle and only see a tiny slice of my gradient" problem.
function setZoneBaseColorFitZone(index, enabled) {
    if (index < 0 || index >= zones.length) return;
    pushZoneUndo('Set base color fit-to-selection');
    zones[index].baseColorFitZone = !!enabled;
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof showToast === 'function') {
        showToast(enabled
            ? '🎯 Fit-to-Selection ON — base color & spec will compress into your selected area'
            : 'Fit-to-Selection OFF — base will sample from full canvas (original behavior)');
    }
}
if (typeof window !== 'undefined') window.setZoneBaseColorFitZone = setZoneBaseColorFitZone;
function setZoneBaseHueOffset(index, val) {
    pushZoneUndo('', true);
    const n = Math.max(-180, Math.min(180, parseInt(val) || 0));
    zones[index].baseHueOffset = n;
    const el = document.getElementById('detBaseHueVal' + index);
    if (el) el.textContent = n + '°';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const s = panel.querySelector('#detBaseHueVal' + index); if (s) s.textContent = n + '°'; }
    triggerPreviewRender();
}
function setZoneBaseSaturation(index, val) {
    pushZoneUndo('', true);
    const n = Math.max(-100, Math.min(100, parseInt(val) || 0));
    zones[index].baseSaturationAdjust = n;
    const el = document.getElementById('detBaseSatVal' + index);
    if (el) el.textContent = n;
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const s = panel.querySelector('#detBaseSatVal' + index); if (s) s.textContent = n; }
    triggerPreviewRender();
}
function setZoneBaseBrightness(index, val) {
    pushZoneUndo('', true);
    const n = Math.max(-100, Math.min(100, parseInt(val) || 0));
    zones[index].baseBrightnessAdjust = n;
    const el = document.getElementById('detBaseBrightVal' + index);
    if (el) el.textContent = n;
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const s = panel.querySelector('#detBaseBrightVal' + index); if (s) s.textContent = n; }
    triggerPreviewRender();
}
function setPlacementLayer(layer) {
    placementLayer = (layer === 'pattern' || layer === 'second_base' || layer === 'third_base' || layer === 'fourth_base' || layer === 'fifth_base' || layer === 'base') ? layer : 'none';
    updatePlacementBanner();
    // Sync canvas cursor in 3-canvas (it reads placementLayer)
    const cvs = document.getElementById('paintCanvas');
    if (cvs) cvs.style.cursor = placementLayer !== 'none' ? 'grab' : '';
}

function getPlacementMode(zone, target) {
    if (!zone) return 'normal';
    const manualActive = (typeof placementLayer !== 'undefined' && placementLayer === target && typeof selectedZoneIndex !== 'undefined' && zones && zones[selectedZoneIndex] === zone);
    if (target === 'base') return manualActive ? 'manual' : 'normal';
    if (target === 'pattern') {
        if (manualActive) return 'manual';
        return zone.patternPlacement === 'fit' ? 'fit' : 'normal';
    }
    if (manualActive) return 'manual';
    if (target === 'second_base') return zone.secondBaseFitZone ? 'fit' : 'normal';
    if (target === 'third_base') return zone.thirdBaseFitZone ? 'fit' : 'normal';
    if (target === 'fourth_base') return zone.fourthBaseFitZone ? 'fit' : 'normal';
    if (target === 'fifth_base') return zone.fifthBaseFitZone ? 'fit' : 'normal';
    return 'normal';
}

function isPlacementOffsetLocked(zone, target) {
    return getPlacementMode(zone, target) === 'fit';
}

function _placementOffsetControlAttrs(zone, target) {
    return isPlacementOffsetLocked(zone, target) ? 'disabled style="opacity:0.35;pointer-events:none;"' : '';
}

function _placementOffsetValueAttrs(zone, target) {
    return isPlacementOffsetLocked(zone, target) ? 'style="opacity:0.35;"' : '';
}

function clearPlacementEditingState(index, target) {
    const zone = zones[index];
    if (!zone) return;
    if (target === 'base' && zone.basePlacement === 'manual') zone.basePlacement = 'normal';
    if (target === 'pattern' && zone.patternPlacement === 'manual') zone.patternPlacement = 'normal';
}
window.clearPlacementEditingState = clearPlacementEditingState;

function setPlacementMode(index, target, mode) {
    const zone = zones[index];
    if (!zone) return;
    if (typeof selectedZoneIndex !== 'undefined') selectedZoneIndex = index;
    const nextMode = (mode === 'manual' || mode === 'fit') ? mode : 'normal';

    if (target === 'base') {
        zone.basePlacement = nextMode === 'manual' ? 'manual' : 'normal';
    } else if (target === 'pattern') {
        zone.patternPlacement = nextMode;
    } else if (target === 'second_base') {
        zone.secondBaseFitZone = nextMode === 'fit';
    } else if (target === 'third_base') {
        zone.thirdBaseFitZone = nextMode === 'fit';
    } else if (target === 'fourth_base') {
        zone.fourthBaseFitZone = nextMode === 'fit';
    } else if (target === 'fifth_base') {
        zone.fifthBaseFitZone = nextMode === 'fit';
    }

    if (nextMode === 'manual') {
        if (typeof activateManualPlacement === 'function') activateManualPlacement(index, target);
    } else {
        if (typeof clearPlacementEditingState === 'function') clearPlacementEditingState(index, target);
        if (typeof placementLayer !== 'undefined' && placementLayer === target) {
            if (typeof deactivateManualPlacement === 'function') deactivateManualPlacement();
            setPlacementLayer('none');
        }
    }

    renderZones();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}
window.setPlacementMode = setPlacementMode;

function _renderPlacementModeButton(index, target, mode, label, active, title, tone) {
    const palette = {
        neutral: { border: '#3a4357', fg: '#d6dcef', bg: '#141b27' },
        cyan: { border: '#1d8ba3', fg: '#bff7ff', bg: '#0f2830' },
        gold: { border: '#8f6a11', fg: '#ffe7a0', bg: '#2b2210' }
    };
    const swatch = palette[tone] || palette.neutral;
    const border = active ? swatch.border : '#2c3240';
    const fg = active ? swatch.fg : '#9ea8bd';
    const bg = active ? swatch.bg : '#111723';
    return `<button type="button" class="btn btn-sm"
        onclick="event.stopPropagation(); setPlacementMode(${index}, '${target}', '${mode}')"
        title="${escapeHtml(title)}"
        style="padding:2px 7px;font-size:10px;border-color:${border};color:${fg};background:${bg};">${escapeHtml(label)}</button>`;
}

function renderPlacementModeControls(index, target, options) {
    const zone = zones[index];
    if (!zone) return '';
    const opts = options || {};
    const mode = getPlacementMode(zone, target);
    const allowFit = !!opts.allowFit;
    const label = opts.label || 'Placement';
    const targetLabel = opts.targetLabel || 'this target';
    const centeredLabel = opts.centeredLabel || 'Centered';
    let hint = mode === 'manual'
        ? 'Drag directly on the template. Use the top strip for quick rotate/flip while placement is active.'
        : 'Use the numeric X/Y controls below for fine tuning.';
    if (mode === 'fit') {
        hint = 'Fit to Zone is active, so template offsets are locked until you switch back to Centered or Edit on Template.';
    }
    let html = `<div class="zone-target-mode" style="margin: 6px 0; display:flex; gap:6px; align-items:flex-start; flex-wrap:wrap;">
        <label style="color:#aaa; font-size:11px; white-space:nowrap; padding-top:4px;">${escapeHtml(label)}:</label>
        <div style="display:flex; gap:4px; align-items:center; flex-wrap:wrap;">`;
    html += _renderPlacementModeButton(index, target, 'normal', centeredLabel, mode === 'normal', `Use centered tiling plus the numeric controls for ${targetLabel}`, 'neutral');
    if (allowFit) {
        html += _renderPlacementModeButton(index, target, 'fit', 'Fit to Zone', mode === 'fit', `Constrain ${targetLabel} to the current zone bounds`, 'gold');
    }
    html += _renderPlacementModeButton(index, target, 'manual', 'Edit on Template', mode === 'manual', `Drag ${targetLabel} directly on the template`, 'cyan');
    html += `</div>
        <div style="flex-basis:100%; font-size:9px; color:var(--text-dim); line-height:1.35;">${escapeHtml(hint)}</div>
    </div>`;
    return html;
}
// Debounce timer for re-fetching the pattern overlay image
var _placementPatternRefetchTimer = null;

function _buildPlacementPatternUrl(z, canvas) {
    const pat = z.pattern && z.pattern !== 'none' ? z.pattern : null;
    if (!pat || !canvas || canvas.width <= 0 || canvas.height <= 0) return null;
    if (typeof ShokkerAPI === 'undefined' || !ShokkerAPI.baseUrl) return null;
    const sc = z.scale ?? 1;
    const rot = z.rotation ?? 0;
    const flipH = z.patternFlipH ? 1 : 0;
    const flipV = z.patternFlipV ? 1 : 0;
    return ShokkerAPI.baseUrl + '/api/pattern-layer?pattern=' + encodeURIComponent(pat)
        + '&w=' + canvas.width + '&h=' + canvas.height
        + '&scale=' + sc + '&rotation=' + rot
        + '&flip_h=' + flipH + '&flip_v=' + flipV + '&seed=42';
}

function applyPlacementPatternTransform() {
    const img = document.getElementById('placementPatternImg');
    const z = zones[selectedZoneIndex];
    if (!img || !z || placementLayer !== 'pattern') return;

    // Only apply CSS translation for the drag offset —
    // scale and rotation are baked into the fetched image.
    const ox = (0.5 - (z.patternOffsetX ?? 0.5)) * 100;
    const oy = (0.5 - (z.patternOffsetY ?? 0.5)) * 100;
    img.style.transform = `translate(${ox}%, ${oy}%)`;

    // Re-fetch the pattern at the current scale/rotation (debounced so rapid
    // scroll-wheel changes don't flood the server with requests).
    const canvas = document.getElementById('paintCanvas');
    const newUrl = _buildPlacementPatternUrl(z, canvas);
    if (!newUrl) return;

    // If scale/rotation changed (URL differs), schedule a re-fetch
    if (img._lastPlacementUrl !== newUrl) {
        clearTimeout(_placementPatternRefetchTimer);
        _placementPatternRefetchTimer = setTimeout(function () {
            if (!img) return;
            const hint = document.getElementById('placementMapOverlayHint');
            if (hint) {
                hint.style.display = 'flex';
                const msg = hint.querySelector('span:first-child');
                if (msg) msg.textContent = 'Loading pattern…';
            }
            img._lastPlacementUrl = newUrl;
            img.onload = function () {
                if (hint) hint.style.display = 'none';
                // Re-apply translation only (scale/rotation now baked in)
                const z2 = zones[selectedZoneIndex];
                if (z2) {
                    const ox2 = (0.5 - (z2.patternOffsetX ?? 0.5)) * 100;
                    const oy2 = (0.5 - (z2.patternOffsetY ?? 0.5)) * 100;
                    img.style.transform = `translate(${ox2}%, ${oy2}%)`;
                }
            };
            img.src = newUrl;
        }, 120);
    }
}

function updatePlacementBanner() {
    const banner = document.getElementById('placementBanner');
    const label = document.getElementById('placementBannerLabel');
    const overlay = document.getElementById('placementMapOverlay');
    const hint = document.getElementById('placementMapOverlayHint');
    const patternLayerDiv = document.getElementById('placementPatternLayer');
    const patternImg = document.getElementById('placementPatternImg');
    if (!banner || !label) return;
    if (placementLayer === 'none') {
        banner.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
        if (patternLayerDiv) patternLayerDiv.style.display = 'none';
        if (hint) hint.style.display = 'flex';
        return;
    }
    const names = { pattern: 'Primary pattern', second_base: '2nd base overlay', third_base: '3rd base overlay', fourth_base: '4th base overlay', fifth_base: '5th base overlay', base: 'Base (gradient/duo)' };
    label.textContent = names[placementLayer] || placementLayer;
    banner.style.display = 'flex';
    if (overlay) overlay.style.display = 'flex';
    if (placementLayer === 'pattern' && patternImg && zones[selectedZoneIndex]) {
        const z = zones[selectedZoneIndex];
        const pat = z.pattern && z.pattern !== 'none' ? z.pattern : null;
        const canvas = document.getElementById('paintCanvas');
        if (pat && canvas && canvas.width > 0 && canvas.height > 0 && typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) {
            hint.style.display = 'flex';
            hint.querySelector('span:first-child').textContent = 'Loading pattern...';
            patternLayerDiv.style.display = 'block';
            const url = _buildPlacementPatternUrl(z, canvas) || (ShokkerAPI.baseUrl + '/api/pattern-layer?pattern=' + encodeURIComponent(pat) + '&w=' + canvas.width + '&h=' + canvas.height + '&scale=1&rotation=0&seed=42');
            patternImg._lastPlacementUrl = url;
            patternImg.onload = function () {
                hint.style.display = 'none';
                applyPlacementPatternTransform();
                setupPlacementOverlayDrag();
            };
            patternImg.onerror = function () {
                hint.querySelector('span:first-child').textContent = 'Drag on the template to move the selected pattern.';
                patternLayerDiv.style.display = 'none';
            };
            patternImg.src = url;
        } else {
            if (hint) {
                hint.style.display = 'flex';
                const msg = hint.querySelector('span:first-child');
                if (msg) msg.textContent = 'Load paint first, then drag on the template to move the selected pattern.';
            }
            if (patternLayerDiv) patternLayerDiv.style.display = 'none';
        }
    } else {
        if (hint) {
            hint.style.display = 'flex';
            const msg = hint.querySelector('span:first-child');
            if (msg) msg.textContent = 'Drag on the template to move ' + (placementLayer === 'second_base' ? 'the 2nd overlay.' : placementLayer === 'third_base' ? 'the 3rd overlay.' : placementLayer === 'fourth_base' ? 'the 4th overlay.' : placementLayer === 'fifth_base' ? 'the 5th overlay.' : placementLayer === 'base' ? 'the base finish.' : 'the selected target.');
        }
        if (patternLayerDiv) patternLayerDiv.style.display = 'none';
    }
    // Sync zone detail dropdown when open
    const sel = document.getElementById('placementLayerSelect' + selectedZoneIndex);
    if (sel && sel.value !== placementLayer) sel.value = placementLayer;
}

var _placementOverlayDragStart = null;
var _placementOverlayPreviewTimer = null;
function setupPlacementOverlayDrag() {
    const overlay = document.getElementById('placementMapOverlay');
    const patternLayerDiv = document.getElementById('placementPatternLayer');
    if (!overlay || !patternLayerDiv || placementLayer !== 'pattern') return;
    patternLayerDiv.onmousedown = function (e) {
        if (e.button !== 0 || !zones[selectedZoneIndex]) return;
        e.preventDefault();
        const z = zones[selectedZoneIndex];
        const rect = overlay.getBoundingClientRect();
        _placementOverlayDragStart = {
            clientX: e.clientX, clientY: e.clientY,
            offsetX: z.patternOffsetX ?? 0.5, offsetY: z.patternOffsetY ?? 0.5
        };
        if (typeof pushZoneUndo === 'function') pushZoneUndo('', true);
        document.addEventListener('mousemove', _onPlacementOverlayMove);
        document.addEventListener('mouseup', _onPlacementOverlayUp);
    };
}
function _onPlacementOverlayMove(e) {
    if (!_placementOverlayDragStart) return;
    const overlay = document.getElementById('placementMapOverlay');
    const z = zones[selectedZoneIndex];
    if (!overlay || !z) return;
    const rect = overlay.getBoundingClientRect();
    const dx = (e.clientX - _placementOverlayDragStart.clientX) / rect.width;
    const dy = (e.clientY - _placementOverlayDragStart.clientY) / rect.height;
    const nx = Math.max(0, Math.min(1, _placementOverlayDragStart.offsetX + dx));
    const ny = Math.max(0, Math.min(1, _placementOverlayDragStart.offsetY + dy));
    z.patternOffsetX = nx;
    z.patternOffsetY = ny;
    const pctX = Math.round(nx * 100) + '%', pctY = Math.round(ny * 100) + '%';
    const vx = Math.round(nx * 100), vy = Math.round(ny * 100);
    ['patPosXVal', 'detPatPosXVal'].forEach(id => { const el = document.getElementById(id + selectedZoneIndex); if (el) { el.textContent = pctX; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; } });
    ['patPosYVal', 'detPatPosYVal'].forEach(id => { const el = document.getElementById(id + selectedZoneIndex); if (el) { el.textContent = pctY; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; } });
    applyPlacementPatternTransform();
    clearTimeout(_placementOverlayPreviewTimer);
    _placementOverlayPreviewTimer = setTimeout(function () { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); }, 150);
}
function _onPlacementOverlayUp() {
    document.removeEventListener('mousemove', _onPlacementOverlayMove);
    document.removeEventListener('mouseup', _onPlacementOverlayUp);
    _placementOverlayDragStart = null;
    clearTimeout(_placementOverlayPreviewTimer);
    _placementOverlayPreviewTimer = null;
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

function setZonePatternOffsetX(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].patternOffsetX = v;
    const pct = Math.round(v * 100) + '%';
    const el = document.getElementById('patPosXVal' + index); if (el) el.textContent = pct;
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detPatPosXVal' + index); if (span) span.textContent = pct; }
    triggerPreviewRender();
    if (typeof applyPlacementPatternTransform === 'function') applyPlacementPatternTransform();
}
function setZonePatternOffsetY(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].patternOffsetY = v;
    const pct = Math.round(v * 100) + '%';
    const el = document.getElementById('patPosYVal' + index); if (el) el.textContent = pct;
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detPatPosYVal' + index); if (span) span.textContent = pct; }
    triggerPreviewRender();
    if (typeof applyPlacementPatternTransform === 'function') applyPlacementPatternTransform();
}
function stepZonePatternOffsetX(index, delta) {
    const cur = Math.round((zones[index].patternOffsetX ?? 0.5) * 100);
    setZonePatternOffsetX(index, Math.max(0, Math.min(100, cur + delta)));
}
function stepZonePatternOffsetY(index, delta) {
    const cur = Math.round((zones[index].patternOffsetY ?? 0.5) * 100);
    setZonePatternOffsetY(index, Math.max(0, Math.min(100, cur + delta)));
}
function stepZoneSecondBasePatternOffset(index, axis, delta) {
    const prop = 'secondBasePatternOffset' + axis;
    const cur = Math.round((zones[index][prop] ?? 0.5) * 100);
    const setter = axis === 'X' ? setZoneSecondBasePatternOffsetX : setZoneSecondBasePatternOffsetY;
    setter(index, Math.max(0, Math.min(100, cur + delta)));
}
function stepZoneNthBasePatternOffset(index, nth, axis, delta) {
    const prop = nth + 'BasePatternOffset' + axis;
    const cur = Math.round((zones[index][prop] ?? 0.5) * 100);
    const newVal = Math.max(0, Math.min(100, cur + delta));
    pushZoneUndo('', true);
    zones[index][prop] = newVal / 100;
    renderZones();
    triggerPreviewRender();
}
function stepZoneBaseOffset(index, axis, delta) {
    const prop = 'baseOffset' + axis;
    const cur = Math.round((zones[index][prop] ?? 0.5) * 100);
    const newVal = Math.max(0, Math.min(100, cur + delta));
    pushZoneUndo('', true);
    zones[index][prop] = newVal / 100;
    renderZones();
    triggerPreviewRender();
}
function setZonePatternFlipH(index, val) {
    pushZoneUndo('', true);
    zones[index].patternFlipH = !!val;
    triggerPreviewRender();
    if (typeof applyPlacementPatternTransform === 'function') applyPlacementPatternTransform();
}
function setZonePatternFlipV(index, val) {
    pushZoneUndo('', true);
    zones[index].patternFlipV = !!val;
    triggerPreviewRender();
    if (typeof applyPlacementPatternTransform === 'function') applyPlacementPatternTransform();
}

function setZoneBaseOffsetX(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].baseOffsetX = v;
    const pct = Math.round(v * 100) + '%';
    const el = document.getElementById('detBasePosXVal' + index); if (el) el.textContent = pct;
    triggerPreviewRender();
}
function setZoneBaseOffsetY(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].baseOffsetY = v;
    const pct = Math.round(v * 100) + '%';
    const el = document.getElementById('detBasePosYVal' + index); if (el) el.textContent = pct;
    triggerPreviewRender();
}
function setZoneBaseRotation(index, val) {
    pushZoneUndo('', true);
    const v = (Number(val) % 360 + 360) % 360;
    zones[index].baseRotation = v;
    const inp = document.getElementById('detBaseRotVal' + index); if (inp) { if (inp.tagName === 'INPUT') inp.value = v; else inp.textContent = v + '°'; }
    const span = document.getElementById('detBasePosRotVal' + index); if (span) span.textContent = v + '°';
    triggerPreviewRender();
}
function stepZoneBaseRotation(index, delta) {
    const cur = zones[index].baseRotation ?? 0;
    setZoneBaseRotation(index, cur + delta);
}
function resetZoneBaseRotation(index) {
    setZoneBaseRotation(index, 0);
}
function setZoneBaseFlipH(index, val) {
    pushZoneUndo('', true);
    zones[index].baseFlipH = !!val;
    triggerPreviewRender();
}
function setZoneBaseFlipV(index, val) {
    pushZoneUndo('', true);
    zones[index].baseFlipV = !!val;
    triggerPreviewRender();
}

function setZonePattern(index, patternId) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] setZonePattern: invalid zone index', index);
        return;
    }
    if (patternId !== null && patternId !== undefined && typeof patternId !== 'string') {
        console.warn('[SPB] setZonePattern: patternId must be a string, got', typeof patternId);
        return;
    }
    pushZoneUndo('Set pattern: ' + (patternId || 'none'));
    zones[index].pattern = patternId || 'none';
    propagateToLinkedZones(index, ['pattern']);
    renderZones();  // Re-render to show/hide scale slider
    triggerPreviewRender();
}

function setZoneBaseStrength(index, val) {
    pushZoneUndo('Set base strength', true);
    zones[index].baseStrength = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const pct = Math.round((zones[index].baseStrength) * 100);
    const label = document.getElementById('detBaseStrVal' + index);
    if (label) label.textContent = pct + '%';
    triggerPreviewRender();
}
function stepZoneBaseStrength(index, delta) {
    const cur = Math.round((zones[index].baseStrength ?? 1) * 100);
    setZoneBaseStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}

function setZoneBaseSpecStrength(index, val) {
    pushZoneUndo('Set base spec strength', true);
    zones[index].baseSpecStrength = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const label = document.getElementById('detBaseSpecStrVal' + index);
    if (label) label.textContent = Math.round((zones[index].baseSpecStrength) * 100) + '%';
    triggerPreviewRender();
}
function stepZoneBaseSpecStrength(index, delta) {
    const cur = Math.round((zones[index].baseSpecStrength ?? 1) * 100);
    setZoneBaseSpecStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}

function setZoneBaseSpecBlendMode(index, val) {
    pushZoneUndo('Set spec blend mode');
    zones[index].baseSpecBlendMode = val || 'normal';
    triggerPreviewRender();
}

function setZoneSecondBaseSpecStrength(index, val) {
    pushZoneUndo('Set second base spec strength', true);
    zones[index].secondBaseSpecStrength = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const label = document.getElementById('detSBSpecStrVal' + index);
    if (label) label.textContent = Math.round((zones[index].secondBaseSpecStrength) * 100) + '%';
    triggerPreviewRender();
}
function stepZoneSecondBaseSpecStrength(index, delta) {
    const cur = Math.round((zones[index].secondBaseSpecStrength ?? 1) * 100);
    setZoneSecondBaseSpecStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}

function setZoneThirdBaseSpecStrength(index, val) {
    pushZoneUndo('Set third base spec strength', true);
    zones[index].thirdBaseSpecStrength = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const label = document.getElementById('detTBSpecStrVal' + index);
    if (label) label.textContent = Math.round((zones[index].thirdBaseSpecStrength) * 100) + '%';
    triggerPreviewRender();
}
function stepZoneThirdBaseSpecStrength(index, delta) {
    const cur = Math.round((zones[index].thirdBaseSpecStrength ?? 1) * 100);
    setZoneThirdBaseSpecStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}

function setZoneFourthBaseSpecStrength(index, val) {
    pushZoneUndo('Set fourth base spec strength', true);
    zones[index].fourthBaseSpecStrength = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const label = document.getElementById('detFBSpecStrVal' + index);
    if (label) label.textContent = Math.round((zones[index].fourthBaseSpecStrength) * 100) + '%';
    triggerPreviewRender();
}
function stepZoneFourthBaseSpecStrength(index, delta) {
    const cur = Math.round((zones[index].fourthBaseSpecStrength ?? 1) * 100);
    setZoneFourthBaseSpecStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}

function setZoneFifthBaseSpecStrength(index, val) {
    pushZoneUndo('Set fifth base spec strength', true);
    zones[index].fifthBaseSpecStrength = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const label = document.getElementById('detFifBSpecStrVal' + index);
    if (label) label.textContent = Math.round((zones[index].fifthBaseSpecStrength) * 100) + '%';
    triggerPreviewRender();
}
function stepZoneFifthBaseSpecStrength(index, delta) {
    const cur = Math.round((zones[index].fifthBaseSpecStrength ?? 1) * 100);
    setZoneFifthBaseSpecStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}

function setZonePatternSpecMult(index, val) {
    pushZoneUndo('Set pattern strength', true);
    zones[index].patternSpecMult = Math.max(0, Math.min(2, (!isNaN(parseInt(val)) ? parseInt(val) : 100) / 100));
    const pct = Math.round((zones[index].patternSpecMult) * 100);
    const label = document.getElementById('detPatStrVal' + index);
    if (label) label.textContent = pct + '%';
    triggerPreviewRender();
}
function stepZonePatternSpecMult(index, delta) {
    const cur = Math.round((zones[index].patternSpecMult ?? 1) * 100);
    setZonePatternSpecMult(index, Math.max(0, Math.min(200, cur + delta * 5)));
}
function setZonePatternOpacity(index, val) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    // 2026-04-18 marathon: pattern opacity slider was changing state without
    // an undo entry — painter dragged too far, Ctrl+Z did nothing. Added
    // drag-coalesced undo so a slider drag session collapses to one entry.
    pushZoneUndo('Pattern opacity', true);
    const v = Math.max(0, Math.min(100, parseInt(val) || 100));
    zones[index].patternOpacity = v;
    const label = document.getElementById('detPatOpVal' + index) || document.getElementById('patOpVal' + index);
    if (label) label.textContent = v + '%';
    triggerPreviewRender();
}
function stepZonePatternOpacity(index, delta) {
    const cur = zones[index].patternOpacity ?? 100;
    setZonePatternOpacity(index, Math.max(0, Math.min(100, cur + delta * 5)));
}

function setZoneScale(index, val) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] setZoneScale: invalid zone index', index);
        return;
    }
    pushZoneUndo('Set scale', true);
    let v = parseFloat(val) || 1.0;
    if (isNaN(v)) v = 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].scale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
    const label = document.getElementById('detScaleVal' + index) || document.getElementById('scaleVal' + index);
    if (label) label.textContent = zones[index].scale.toFixed(2) + 'x';
    const pct = Math.round(zones[index].scale * 100);
    document.querySelectorAll(`input[type="range"][oninput^="setZoneScale(${index},"]`).forEach(sl => { sl.value = pct; });
    triggerPreviewRender();
    if (typeof applyPlacementPatternTransform === 'function') applyPlacementPatternTransform();
}
function stepZoneScale(index, delta) {
    const cur = zones[index].scale || 1.0;
    setZoneScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}

function resetZoneScale(index) {
    pushZoneUndo('Reset scale');
    zones[index].scale = 1.0;
    renderZones();
    triggerPreviewRender();
}

function setZoneBaseScale(index, val) {
    pushZoneUndo('Set base scale', true);
    let v = parseFloat(val) || 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].baseScale = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));
    const label = document.getElementById('detBaseScaleVal' + index);
    if (label) label.textContent = zones[index].baseScale.toFixed(2) + 'x';
    const pct = Math.round(zones[index].baseScale * 100);
    document.querySelectorAll(`input[type="range"][oninput*="setZoneBaseScale(${index},"]`).forEach(sl => { sl.value = pct; });
    triggerPreviewRender();
}
function stepZoneBaseScale(index, delta) {
    const cur = zones[index].baseScale || 1.0;
    setZoneBaseScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}

function resetZoneBaseScale(index) {
    pushZoneUndo('Reset base scale');
    zones[index].baseScale = 1.0;
    renderZones();
    triggerPreviewRender();
}

function setZoneRotation(index, val) {
    pushZoneUndo('Set rotation', true);
    const v = Math.max(0, Math.min(359, parseInt(val) || 0));
    zones[index].rotation = v;
    // Sync both number inputs and sliders
    ['detRotVal', 'rotVal'].forEach(prefix => {
        const el = document.getElementById(prefix + index);
        if (el) el.value = v;
    });
    document.querySelectorAll(`input[type="range"][oninput^="setZoneRotation(${index},"]`).forEach(sl => { sl.value = v; });
    triggerPreviewRender();
    if (typeof applyPlacementPatternTransform === 'function') applyPlacementPatternTransform();
}
function stepZoneRotation(index, delta) {
    const cur = zones[index].rotation || 0;
    setZoneRotation(index, Math.max(0, Math.min(359, cur + delta)));
}

function resetZoneRotation(index) {
    pushZoneUndo('Reset pattern rotation');
    zones[index].rotation = 0;
    renderZones();
    triggerPreviewRender();
}

function setZoneBaseRotation(index, val) {
    pushZoneUndo('Set base rotation', true);
    const v = Math.max(0, Math.min(359, parseInt(val) || 0));
    zones[index].baseRotation = v;
    // Sync both number inputs and sliders
    ['detBaseRotVal', 'baseRotVal'].forEach(prefix => {
        const el = document.getElementById(prefix + index);
        if (el) el.value = v;
    });
    // Sync range sliders too (they won't have these IDs, find via parent)
    document.querySelectorAll(`input[type="range"][oninput*="setZoneBaseRotation(${index},"]`).forEach(sl => { sl.value = v; });
    triggerPreviewRender();
}

// FIVE-HOUR SHIFT Win H3: removed duplicate definition of resetZoneBaseRotation
// at this line — there's a canonical version at L5374 that delegates to
// setZoneBaseRotation(index, 0), which handles label sync via the
// querySelector loop at L5599. The duplicate here mutated baseRotation
// directly and skipped that sync, so the slider/number inputs in the zone
// detail panel kept showing the OLD rotation value after reset until next
// renderZones (panel out of sync with zone state).

// ===== DUAL LAYER BASE OVERLAY SETTERS =====
function _markZoneBaseOverlayUserEdit(index) {
    if (!zones[index]) return;
    zones[index]._scopedBrushAutoBaseColor = false;
}
function setZoneSecondBase(index, val) {
    pushZoneUndo('Set overlay base');
    _markZoneBaseOverlayUserEdit(index);
    zones[index].secondBase = val || '';
    if (!val) { zones[index].secondBaseStrength = 0; zones[index].secondBaseColorSource = null; }
    else {
        // Only auto-set color source if this is the FIRST time adding an overlay (no existing source)
        const hadSource = !!zones[index].secondBaseColorSource;
        // Default to 100% strength when first adding an overlay so it's visible immediately
        if (!zones[index].secondBaseStrength) zones[index].secondBaseStrength = 1.0;
        // Default blend mode to pattern-pop with harden when first set
        if (!zones[index].secondBaseBlendMode) zones[index].secondBaseBlendMode = 'pattern-vivid';
        if (zones[index].secondBaseHarden === undefined) zones[index].secondBaseHarden = true;
        // Default color source to "Same As Overlay" ONLY on first setup
        if (!hadSource && !zones[index].secondBaseColorSource) {
            zones[index].secondBaseColorSource = 'overlay';
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].secondBaseColor = hex;
        }
    }
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBaseColorSource(index, val) {
    pushZoneUndo('Overlay color source', true);
    _markZoneBaseOverlayUserEdit(index);
    zones[index].secondBaseColorSource = val || null;
    renderZoneDetail(index);
    triggerPreviewRender();
}
/** Set overlay color to "Same as overlay" and sync secondBaseColor to the overlay base's swatch. */
function setZoneSecondBaseColorSourceToOverlay(index) {
    pushZoneUndo('Overlay color same as base', true);
    _markZoneBaseOverlayUserEdit(index);
    const baseId = zones[index].secondBase || zones[index].secondBaseColorSource;
    const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(baseId);
    const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
    zones[index].secondBaseColorSource = 'overlay';
    zones[index].secondBaseColor = hex;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBaseColorSourceToOverlay(index) {
    pushZoneUndo('3rd overlay color same as base', true);
    _markZoneBaseOverlayUserEdit(index);
    const baseId = zones[index].thirdBase || zones[index].thirdBaseColorSource;
    const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(baseId);
    const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
    zones[index].thirdBaseColorSource = 'overlay';
    zones[index].thirdBaseColor = hex;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneFourthBaseColorSourceToOverlay(index) {
    pushZoneUndo('4th overlay color same as base', true);
    _markZoneBaseOverlayUserEdit(index);
    const baseId = zones[index].fourthBase || zones[index].fourthBaseColorSource;
    const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(baseId);
    const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
    zones[index].fourthBaseColorSource = 'overlay';
    zones[index].fourthBaseColor = hex;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneFifthBaseColorSourceToOverlay(index) {
    pushZoneUndo('5th overlay color same as base', true);
    _markZoneBaseOverlayUserEdit(index);
    const baseId = zones[index].fifthBase || zones[index].fifthBaseColorSource;
    const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(baseId);
    const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
    zones[index].fifthBaseColorSource = 'overlay';
    zones[index].fifthBaseColor = hex;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBaseColor(index, val) {
    pushZoneUndo('Set overlay color', true);
    _markZoneBaseOverlayUserEdit(index);
    val = (val || "").trim();
    if (val && !val.startsWith("#")) val = "#" + val;
    if (val && !/^#[0-9A-Fa-f]{6}$/.test(val)) {
        showToast('Enter a valid hex code like #FF3366', true);
        renderZoneDetail(index);
        return;
    }
    zones[index].secondBaseColor = val || '#ffffff';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBaseStrength(index, val) {
    pushZoneUndo('Set overlay strength', true);
    zones[index].secondBaseStrength = (parseInt(val) || 0) / 100;
    const pct = Math.round((zones[index].secondBaseStrength) * 100);
    const label = document.getElementById('detSBStrVal' + index);
    if (label) label.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detSBStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneSecondBaseStrength(index, delta) {
    const cur = Math.round((zones[index].secondBaseStrength ?? 0) * 100);
    setZoneSecondBaseStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneSecondBaseBlendMode(index, val) {
    pushZoneUndo('Set overlay blend mode');
    zones[index].secondBaseBlendMode = val || 'noise';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBaseFractalScale(index, val) {
    pushZoneUndo('Set overlay Fractal Detail', true);
    zones[index].secondBaseFractalScale = Math.max(4, Math.min(128, parseInt(val) || 24));
    const v = zones[index].secondBaseFractalScale;
    const label = document.getElementById('detSBNSVal' + index);
    if (label) label.textContent = v + 'px';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detSBNSVal' + index); if (span) span.textContent = v + 'px'; }
    triggerPreviewRender();
}
function stepZoneSecondBaseFractalScale(index, delta) {
    const cur = zones[index].secondBaseFractalScale ?? 24;
    setZoneSecondBaseFractalScale(index, Math.max(4, Math.min(128, cur + delta * 4)));
}
function setZoneSecondBaseScale(index, val) {
    if (index < 0 || index >= zones.length) return;
    let v = parseFloat(val) || 1;
    v = roundToStep(v, SCALE_STEP);
    const n = Math.max(SCALE_OVERLAY_MIN, Math.min(SCALE_OVERLAY_MAX, v));
    zones[index].secondBaseScale = n;
    propagateToLinkedZones(index, 'secondBaseScale', n);
    pushZoneUndoCoalesced('Set 2nd overlay scale');
    const card = document.getElementById(`zone-card-${index}`);
    if (card) {
        const span = card.querySelector('#detSBScaleVal' + index);
        if (span) span.textContent = n.toFixed(2);
    }
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        const span = panel.querySelector('#detSBScaleVal' + index);
        if (span) span.textContent = n.toFixed(2);
    }
    triggerPreviewRender();
}
function stepZoneSecondBaseScale(index, delta) {
    const cur = zones[index].secondBaseScale ?? 1;
    setZoneSecondBaseScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneSecondBasePattern(index, val) {
    pushZoneUndo('Set 2nd base pattern');
    zones[index].secondBasePattern = val || null;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBase(index, val) {
    pushZoneUndo('Set 3rd overlay base');
    _markZoneBaseOverlayUserEdit(index);
    zones[index].thirdBase = val || '';
    if (!val) { zones[index].thirdBaseStrength = 0; zones[index].thirdBaseColorSource = null; }
    else {
        const hadSource = !!zones[index].thirdBaseColorSource;
        if (!zones[index].thirdBaseStrength) zones[index].thirdBaseStrength = 1.0;
        if (!zones[index].thirdBaseBlendMode) zones[index].thirdBaseBlendMode = 'pattern-vivid';
        if (zones[index].thirdBaseHarden === undefined) zones[index].thirdBaseHarden = true;
        if (!hadSource && !zones[index].thirdBaseColorSource) {
            zones[index].thirdBaseColorSource = 'overlay';
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].thirdBaseColor = hex;
        }
        if (!zones[index].thirdBasePattern && val) zones[index].thirdBasePattern = (() => {
            const z = zones[index];
            const s = z.patternStack || [];
            // Default to Pattern 2 if it exists, otherwise Pattern 1
            if (s[1] && s[1].id && s[1].id !== 'none') return s[1].id;
            if (s[0] && s[0].id && s[0].id !== 'none') return s[0].id;
            return '';
        })();
    }
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBaseColorSource(index, val) {
    pushZoneUndo('3rd overlay color from special', true);
    _markZoneBaseOverlayUserEdit(index);
    zones[index].thirdBaseColorSource = val || null;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBaseColor(index, val) {
    pushZoneUndo('Set 3rd overlay color', true);
    _markZoneBaseOverlayUserEdit(index);
    val = (val || "").trim();
    if (val && !val.startsWith("#")) val = "#" + val;
    if (val && !/^#[0-9A-Fa-f]{6}$/.test(val)) {
        showToast('Enter a valid hex code like #FF3366', true);
        renderZoneDetail(index);
        return;
    }
    zones[index].thirdBaseColor = val || '#ffffff';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBaseStrength(index, val) {
    pushZoneUndo('Set 3rd overlay strength', true);
    zones[index].thirdBaseStrength = (parseInt(val) || 0) / 100;
    const pct = Math.round((zones[index].thirdBaseStrength) * 100);
    const label = document.getElementById('detTBStrVal' + index);
    if (label) label.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detTBStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneThirdBaseStrength(index, delta) {
    const cur = Math.round((zones[index].thirdBaseStrength ?? 0) * 100);
    setZoneThirdBaseStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneThirdBaseBlendMode(index, val) {
    pushZoneUndo('Set 3rd overlay blend mode');
    zones[index].thirdBaseBlendMode = val || 'noise';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBaseFractalScale(index, val) {
    pushZoneUndo('Set 3rd overlay Fractal Detail', true);
    zones[index].thirdBaseFractalScale = Math.max(4, Math.min(128, parseInt(val) || 24));
    const v = zones[index].thirdBaseFractalScale;
    const label = document.getElementById('detTBNSVal' + index);
    if (label) label.textContent = v + 'px';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detTBNSVal' + index); if (span) span.textContent = v + 'px'; }
    triggerPreviewRender();
}
function stepZoneThirdBaseFractalScale(index, delta) {
    const cur = zones[index].thirdBaseFractalScale ?? 24;
    setZoneThirdBaseFractalScale(index, Math.max(4, Math.min(128, cur + delta * 4)));
}
function setZoneThirdBaseScale(index, val) {
    if (index < 0 || index >= zones.length) return;
    let v = parseFloat(val) || 1;
    v = roundToStep(v, SCALE_STEP);
    const n = Math.max(SCALE_OVERLAY_MIN, Math.min(SCALE_OVERLAY_MAX, v));
    zones[index].thirdBaseScale = n;
    pushZoneUndoCoalesced('Set 3rd overlay scale');
    const card = document.getElementById('zone-card-' + index);
    if (card) {
        const span = card.querySelector('#detTBScaleVal' + index);
        if (span) span.textContent = n.toFixed(2);
    }
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        const span = panel.querySelector('#detTBScaleVal' + index);
        if (span) span.textContent = n.toFixed(2);
    }
    triggerPreviewRender();
}
function stepZoneThirdBaseScale(index, delta) {
    const cur = zones[index].thirdBaseScale ?? 1;
    setZoneThirdBaseScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneThirdBasePattern(index, val) {
    pushZoneUndo('Set 3rd base pattern');
    zones[index].thirdBasePattern = val || null;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBasePatternOpacity(index, val) {
    pushZoneUndo('', true);
    zones[index].secondBasePatternOpacity = Math.max(0, Math.min(100, parseInt(val) ?? 100));
    const v = zones[index].secondBasePatternOpacity;
    const el = document.getElementById('detSBPatOpVal' + index); if (el) el.textContent = v + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detSBPatOpVal' + index); if (span) span.textContent = v + '%'; }
    triggerPreviewRender();
}
function stepZoneSecondBasePatternOpacity(index, delta) {
    const cur = zones[index].secondBasePatternOpacity ?? 100;
    setZoneSecondBasePatternOpacity(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneSecondBasePatternScale(index, val) {
    pushZoneUndo('', true);
    let v = parseFloat(val) ?? 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].secondBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
    const el = document.getElementById('detSBPatScaleVal' + index); if (el) el.textContent = (zones[index].secondBasePatternScale).toFixed(2) + 'x';
    triggerPreviewRender();
}
function stepZoneSecondBasePatternScale(index, delta) {
    const cur = zones[index].secondBasePatternScale ?? 1.0;
    setZoneSecondBasePatternScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneSecondBasePatternRotation(index, val) {
    pushZoneUndo('', true);
    let v = parseInt(val) ?? 0;
    v = ((v % 360) + 360) % 360;
    zones[index].secondBasePatternRotation = v;
    const el = document.getElementById('detSBPatRotVal' + index); if (el) el.value = v;
    const numEl = document.getElementById('detSBPatRotVal' + index); if (numEl) numEl.value = v;
    const rangeEl = document.getElementById('detSBPatRotRange' + index); if (rangeEl) rangeEl.value = v;
    triggerPreviewRender();
}
function stepZoneSecondBasePatternRotation(index, delta) {
    const cur = zones[index].secondBasePatternRotation ?? 0;
    setZoneSecondBasePatternRotation(index, cur + delta * 5);
}
function setZoneSecondBasePatternStrength(index, val) {
    pushZoneUndo('', true);
    zones[index].secondBasePatternStrength = Math.max(0, Math.min(2, (parseInt(val) ?? 100) / 100));
    const pct = Math.round((zones[index].secondBasePatternStrength) * 100);
    const el = document.getElementById('detSBPatStrVal' + index); if (el) el.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detSBPatStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneSecondBasePatternStrength(index, delta) {
    const cur = Math.round((zones[index].secondBasePatternStrength ?? 1) * 100);
    setZoneSecondBasePatternStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}
function setZoneSecondBasePatternInvert(index, val) {
    pushZoneUndo('', true);
    zones[index].secondBasePatternInvert = !!val;
    triggerPreviewRender();
}
function setZoneSecondBasePatternHarden(index, val) {
    pushZoneUndo('', true);
    zones[index].secondBasePatternHarden = !!val;
    triggerPreviewRender();
}
function setZoneSecondBasePatternOffsetX(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].secondBasePatternOffsetX = v;
    const el = document.getElementById('detSBPatPosXVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detSBPatPosXVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
function setZoneSecondBasePatternOffsetY(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].secondBasePatternOffsetY = v;
    const el = document.getElementById('detSBPatPosYVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detSBPatPosYVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
/** Copy primary pattern position, scale, and rotation to 2nd base overlay so it lines up exactly (e.g. when overlay is pattern-reactive). */
function alignSecondBaseOverlayWithSelectedPattern(index) {
    const z = zones[index];
    if (!z || !z.secondBase) return;
    pushZoneUndo('', true);

    const targetPatId = z.secondBasePattern || '';
    let sx = 1.0, rot = 0, px = 0.5, py = 0.5;

    if (!targetPatId || targetPatId === 'none') {
        sx = z.scale ?? 1.0;
        rot = z.rotation ?? 0;
        px = z.patternOffsetX ?? 0.5;
        py = z.patternOffsetY ?? 0.5;
    } else {
        // Check patternStack first (Pattern 2, 3, 4 — the stacked additional patterns)
        const stack = z.patternStack || [];
        let foundInStack = false;
        const pat = stack.find(p => p.id === targetPatId);
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.offsetX ?? 0.5;
            py = pat.offsetY ?? 0.5;
            foundInStack = true;
        }
        // Check if it matches the primary pattern (Pattern 1) — stored directly on z, not in patternStack
        if (!foundInStack && z.pattern && z.pattern === z.secondBasePattern) {
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
            foundInStack = true;
        }
        if (!foundInStack) {
            // Fall back to primary pattern position as best guess
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
        }
    }

    z.secondBasePatternOffsetX = px;
    z.secondBasePatternOffsetY = py;
    z.secondBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, sx));
    z.secondBasePatternRotation = ((rot % 360) + 360) % 360;
    
    const pctX = Math.round((z.secondBasePatternOffsetX) * 100) + '%', pctY = Math.round((z.secondBasePatternOffsetY) * 100) + '%';
    const scaleVal = (z.secondBasePatternScale).toFixed(2), rotVal = z.secondBasePatternRotation;
    
    ['detSBPatPosXVal', 'detSBPatPosYVal'].forEach((id, idx) => {
        const span = document.getElementById(id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.secondBasePatternOffsetY * 100) : Math.round(z.secondBasePatternOffsetX * 100); }
    });
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        ['detSBPatPosXVal', 'detSBPatPosYVal'].forEach((id, idx) => {
            const span = panel.querySelector('#' + id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.secondBasePatternOffsetY * 100) : Math.round(z.secondBasePatternOffsetX * 100); }
        });
    }
    const scaleSpan = document.getElementById('detSBPatScaleVal' + index); if (scaleSpan) scaleSpan.textContent = scaleVal + 'x';
    const scaleInput = scaleSpan && scaleSpan.previousElementSibling && scaleSpan.previousElementSibling.previousElementSibling; if (scaleInput && scaleInput.type === 'range') scaleInput.value = Math.round(z.secondBasePatternScale * 100);
    const rotInput = document.getElementById('detSBPatRotVal' + index); if (rotInput) rotInput.value = rotVal;
    const rotRange = document.getElementById('detSBPatRotRange' + index); if (rotRange) rotRange.value = rotVal;
    
    triggerPreviewRender();
    showToast('Overlay aligned with selected pattern (position, scale, rotation)');
}

function setZoneThirdBasePatternOpacity(index, val) {
    pushZoneUndo('', true);
    zones[index].thirdBasePatternOpacity = Math.max(0, Math.min(100, parseInt(val) ?? 100));
    const v = zones[index].thirdBasePatternOpacity;
    const el = document.getElementById('detTBPatOpVal' + index); if (el) el.textContent = v + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detTBPatOpVal' + index); if (span) span.textContent = v + '%'; }
    triggerPreviewRender();
}
function stepZoneThirdBasePatternOpacity(index, delta) {
    const cur = zones[index].thirdBasePatternOpacity ?? 100;
    setZoneThirdBasePatternOpacity(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneThirdBasePatternScale(index, val) {
    pushZoneUndo('', true);
    let v = parseFloat(val) ?? 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].thirdBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
    const el = document.getElementById('detTBPatScaleVal' + index); if (el) el.textContent = (zones[index].thirdBasePatternScale).toFixed(2) + 'x';
    triggerPreviewRender();
}
function stepZoneThirdBasePatternScale(index, delta) {
    const cur = zones[index].thirdBasePatternScale ?? 1.0;
    setZoneThirdBasePatternScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneThirdBasePatternRotation(index, val) {
    pushZoneUndo('', true);
    let v = parseInt(val) ?? 0;
    v = ((v % 360) + 360) % 360;
    zones[index].thirdBasePatternRotation = v;
    const el = document.getElementById('detTBPatRotVal' + index); if (el) el.value = v;
    const rangeEl = document.getElementById('detTBPatRotRange' + index); if (rangeEl) rangeEl.value = v;
    triggerPreviewRender();
}
function stepZoneThirdBasePatternRotation(index, delta) {
    const cur = zones[index].thirdBasePatternRotation ?? 0;
    setZoneThirdBasePatternRotation(index, cur + delta * 5);
}
function setZoneThirdBasePatternStrength(index, val) {
    pushZoneUndo('', true);
    zones[index].thirdBasePatternStrength = Math.max(0, Math.min(2, (parseInt(val) ?? 100) / 100));
    const pct = Math.round((zones[index].thirdBasePatternStrength) * 100);
    const el = document.getElementById('detTBPatStrVal' + index); if (el) el.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detTBPatStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneThirdBasePatternStrength(index, delta) {
    const cur = Math.round((zones[index].thirdBasePatternStrength ?? 1) * 100);
    setZoneThirdBasePatternStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}
function setZoneThirdBasePatternInvert(index, val) {
    pushZoneUndo('', true);
    zones[index].thirdBasePatternInvert = !!val;
    triggerPreviewRender();
}
function setZoneThirdBasePatternHarden(index, val) {
    pushZoneUndo('', true);
    zones[index].thirdBasePatternHarden = !!val;
    triggerPreviewRender();
}
function setZoneThirdBasePatternOffsetX(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].thirdBasePatternOffsetX = v;
    const el = document.getElementById('detTBPatPosXVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detTBPatPosXVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
function setZoneThirdBasePatternOffsetY(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].thirdBasePatternOffsetY = v;
    const el = document.getElementById('detTBPatPosYVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detTBPatPosYVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}

function allocateUnusedPatternForOverlay(zone) {
    if (!zone) return '';
    const used = new Set([
        zone.secondBasePattern,
        zone.thirdBasePattern,
        zone.fourthBasePattern,
        zone.fifthBasePattern,
    ].filter(x => x && x !== 'none'));
    const stack = zone.patternStack || [];
    const available = [''];
    if (stack[0] && stack[0].id && stack[0].id !== 'none') available.push(stack[0].id);
    if (stack[1] && stack[1].id && stack[1].id !== 'none') available.push(stack[1].id);
    for (const p of available) {
        if (!used.has(p)) return p;
    }
    return '';
}

function setZoneFourthBase(index, val) { 
    pushZoneUndo('Set 4th overlay base'); 
    _markZoneBaseOverlayUserEdit(index);
    zones[index].fourthBase = val || '';
    if (!val) { zones[index].fourthBaseStrength = 0; zones[index].fourthBaseColorSource = null; }
    else {
        const hadSource = !!zones[index].fourthBaseColorSource;
        if (!zones[index].fourthBaseStrength) zones[index].fourthBaseStrength = 1.0;
        if (!zones[index].fourthBaseBlendMode) zones[index].fourthBaseBlendMode = 'pattern-vivid';
        if (zones[index].fourthBaseHarden === undefined) zones[index].fourthBaseHarden = true;
        if (!hadSource && !zones[index].fourthBaseColorSource) {
            zones[index].fourthBaseColorSource = 'overlay';
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].fourthBaseColor = hex;
        }
        if (!zones[index].fourthBasePattern && val) zones[index].fourthBasePattern = allocateUnusedPatternForOverlay(zones[index]);
    } 
    renderZoneDetail(index); 
    triggerPreviewRender(); 
}
function setZoneFourthBaseColorSource(index, val) { pushZoneUndo('4th overlay color from special', true); _markZoneBaseOverlayUserEdit(index); zones[index].fourthBaseColorSource = val || null; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFourthBaseColor(index, val) {
    pushZoneUndo('Set 4th overlay color', true);
    _markZoneBaseOverlayUserEdit(index);
    val = (val || "").trim();
    if (val && !val.startsWith("#")) val = "#" + val;
    if (val && !/^#[0-9A-Fa-f]{6}$/.test(val)) {
        showToast('Enter a valid hex code like #FF3366', true);
        renderZoneDetail(index);
        return;
    }
    zones[index].fourthBaseColor = val || '#ffffff';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneFourthBaseStrength(index, val) {
    pushZoneUndo('', true);
    zones[index].fourthBaseStrength = (parseInt(val) || 0) / 100;
    const pct = Math.round((zones[index].fourthBaseStrength) * 100);
    const label = document.getElementById('detFBStrVal' + index);
    if (label) label.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFBStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneFourthBaseStrength(index, delta) {
    const cur = Math.round((zones[index].fourthBaseStrength ?? 0) * 100);
    setZoneFourthBaseStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneFourthBaseBlendMode(index, val) { pushZoneUndo('Set 4th overlay blend'); zones[index].fourthBaseBlendMode = val || 'noise'; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFourthBaseFractalScale(index, val) {
    pushZoneUndo('Set 4th overlay Fractal Detail', true);
    zones[index].fourthBaseFractalScale = Math.max(4, Math.min(128, parseInt(val) || 24));
    const v = zones[index].fourthBaseFractalScale;
    const label = document.getElementById('detFBNSVal' + index);
    if (label) label.textContent = v + 'px';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFBNSVal' + index); if (span) span.textContent = v + 'px'; }
    triggerPreviewRender();
}
function stepZoneFourthBaseFractalScale(index, delta) {
    const cur = zones[index].fourthBaseFractalScale ?? 24;
    setZoneFourthBaseFractalScale(index, Math.max(4, Math.min(128, cur + delta * 4)));
}
function setZoneFourthBaseScale(index, val) {
    if (index < 0 || index >= zones.length) return;
    let v = parseFloat(val) || 1;
    v = roundToStep(v, SCALE_STEP);
    const n = Math.max(SCALE_OVERLAY_MIN, Math.min(SCALE_OVERLAY_MAX, v));
    zones[index].fourthBaseScale = n;
    pushZoneUndoCoalesced('Set 4th overlay scale');
    const card = document.getElementById('zone-card-' + index);
    if (card) { const span = card.querySelector('#detFBScaleVal' + index); if (span) span.textContent = n.toFixed(2); }
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFBScaleVal' + index); if (span) span.textContent = n.toFixed(2); }
    triggerPreviewRender();
}
function stepZoneFourthBaseScale(index, delta) {
    const cur = zones[index].fourthBaseScale ?? 1;
    setZoneFourthBaseScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneFourthBasePattern(index, val) { pushZoneUndo('Set 4th base pattern'); zones[index].fourthBasePattern = val || null; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFourthBasePatternOpacity(index, val) {
    pushZoneUndo('', true);
    zones[index].fourthBasePatternOpacity = Math.max(0, Math.min(100, parseInt(val) ?? 100));
    const v = zones[index].fourthBasePatternOpacity;
    const el = document.getElementById('detFBPatOpVal' + index); if (el) el.textContent = v + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFBPatOpVal' + index); if (span) span.textContent = v + '%'; }
    triggerPreviewRender();
}
function stepZoneFourthBasePatternOpacity(index, delta) {
    const cur = zones[index].fourthBasePatternOpacity ?? 100;
    setZoneFourthBasePatternOpacity(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneFourthBasePatternScale(index, val) {
    pushZoneUndo('', true);
    let v = parseFloat(val) ?? 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].fourthBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
    const el = document.getElementById('detFBPatScaleVal' + index); if (el) el.textContent = (zones[index].fourthBasePatternScale).toFixed(2) + 'x';
    triggerPreviewRender();
}
function stepZoneFourthBasePatternScale(index, delta) {
    const cur = zones[index].fourthBasePatternScale ?? 1.0;
    setZoneFourthBasePatternScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneFourthBasePatternRotation(index, val) {
    pushZoneUndo('', true);
    let v = parseInt(val) ?? 0;
    v = ((v % 360) + 360) % 360;
    zones[index].fourthBasePatternRotation = v;
    const el = document.getElementById('detFBPatRotVal' + index); if (el) el.value = v;
    const rangeEl = document.getElementById('detFBPatRotRange' + index); if (rangeEl) rangeEl.value = v;
    triggerPreviewRender();
}
function stepZoneFourthBasePatternRotation(index, delta) {
    const cur = zones[index].fourthBasePatternRotation ?? 0;
    setZoneFourthBasePatternRotation(index, cur + delta * 5);
}
function setZoneFourthBasePatternStrength(index, val) {
    pushZoneUndo('', true);
    zones[index].fourthBasePatternStrength = Math.max(0, Math.min(2, (parseInt(val) ?? 100) / 100));
    const pct = Math.round((zones[index].fourthBasePatternStrength) * 100);
    const el = document.getElementById('detFBPatStrVal' + index); if (el) el.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detFBPatStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneFourthBasePatternStrength(index, delta) {
    const cur = Math.round((zones[index].fourthBasePatternStrength ?? 1) * 100);
    setZoneFourthBasePatternStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}
function setZoneFourthBasePatternInvert(index, val) { pushZoneUndo('', true); zones[index].fourthBasePatternInvert = !!val; triggerPreviewRender(); }
function setZoneFourthBasePatternHarden(index, val) { pushZoneUndo('', true); zones[index].fourthBasePatternHarden = !!val; triggerPreviewRender(); }
function setZoneFourthBasePatternOffsetX(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].fourthBasePatternOffsetX = v;
    const el = document.getElementById('detFBPatPosXVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detFBPatPosXVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
function setZoneFourthBasePatternOffsetY(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].fourthBasePatternOffsetY = v;
    const el = document.getElementById('detFBPatPosYVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detFBPatPosYVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
/** Copy primary pattern position, scale, and rotation to 4th base overlay so it lines up exactly. */
function alignFourthBaseOverlayWithSelectedPattern(index) {
    const z = zones[index];
    if (!z || !z.fourthBase) return;
    pushZoneUndo('', true);

    const targetPatId = z.fourthBasePattern || '';
    let sx = 1.0, rot = 0, px = 0.5, py = 0.5;

    if (!targetPatId || targetPatId === 'none') {
        sx = z.scale ?? 1.0;
        rot = z.rotation ?? 0;
        px = z.patternOffsetX ?? 0.5;
        py = z.patternOffsetY ?? 0.5;
    } else {
        // Check patternStack first (Pattern 2, 3, 4 — the stacked additional patterns)
        const stack = z.patternStack || [];
        let foundInStack = false;
        const pat = stack.find(p => p.id === targetPatId);
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.offsetX ?? 0.5;
            py = pat.offsetY ?? 0.5;
            foundInStack = true;
        }
        // Check if it matches the primary pattern (Pattern 1) — stored directly on z, not in patternStack
        if (!foundInStack && z.pattern && z.pattern === z.fourthBasePattern) {
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
            foundInStack = true;
        }
        if (!foundInStack) {
            // Fall back to primary pattern position as best guess
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
        }
    }

    z.fourthBasePatternOffsetX = px;
    z.fourthBasePatternOffsetY = py;
    z.fourthBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, sx));
    z.fourthBasePatternRotation = ((rot % 360) + 360) % 360;
    
    const pctX = Math.round((z.fourthBasePatternOffsetX) * 100) + '%', pctY = Math.round((z.fourthBasePatternOffsetY) * 100) + '%';
    const scaleVal = (z.fourthBasePatternScale).toFixed(2), rotVal = z.fourthBasePatternRotation;
    
    ['detFBPatPosXVal', 'detFBPatPosYVal'].forEach((id, idx) => {
        const span = document.getElementById(id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.fourthBasePatternOffsetY * 100) : Math.round(z.fourthBasePatternOffsetX * 100); }
    });
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        ['detFBPatPosXVal', 'detFBPatPosYVal'].forEach((id, idx) => {
            const span = panel.querySelector('#' + id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.fourthBasePatternOffsetY * 100) : Math.round(z.fourthBasePatternOffsetX * 100); }
        });
    }
    const scaleSpan = document.getElementById('detFBPatScaleVal' + index); if (scaleSpan) scaleSpan.textContent = scaleVal + 'x';
    const scaleInput = scaleSpan && scaleSpan.previousElementSibling && scaleSpan.previousElementSibling.previousElementSibling; if (scaleInput && scaleInput.type === 'range') scaleInput.value = Math.round(z.fourthBasePatternScale * 100);
    const rotInput = document.getElementById('detFBPatRotVal' + index); if (rotInput) rotInput.value = rotVal;
    const rotRange = document.getElementById('detFBPatRotRange' + index); if (rotRange) rotRange.value = rotVal;
    
    triggerPreviewRender();
    showToast('Overlay aligned with selected pattern (position, scale, rotation)');
}

function setZoneFifthBase(index, val) { 
    pushZoneUndo('Set 5th overlay base'); 
    _markZoneBaseOverlayUserEdit(index);
    zones[index].fifthBase = val || ''; 
    if (!val) { zones[index].fifthBaseStrength = 0; zones[index].fifthBaseColorSource = null; } 
    else {
        const hadSource = !!zones[index].fifthBaseColorSource;
        if (!zones[index].fifthBaseStrength) zones[index].fifthBaseStrength = 1.0;
        if (!zones[index].fifthBaseBlendMode) zones[index].fifthBaseBlendMode = 'pattern-vivid';
        if (zones[index].fifthBaseHarden === undefined) zones[index].fifthBaseHarden = true;
        if (!hadSource && !zones[index].fifthBaseColorSource) {
            zones[index].fifthBaseColorSource = 'overlay';
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].fifthBaseColor = hex;
        }
        if (!zones[index].fifthBasePattern && val) zones[index].fifthBasePattern = allocateUnusedPatternForOverlay(zones[index]);
    }
    renderZoneDetail(index); 
    triggerPreviewRender(); 
}
function setZoneFifthBaseColorSource(index, val) { pushZoneUndo('5th overlay color from special', true); _markZoneBaseOverlayUserEdit(index); zones[index].fifthBaseColorSource = val || null; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFifthBaseColor(index, val) {
    pushZoneUndo('Set 5th overlay color', true);
    _markZoneBaseOverlayUserEdit(index);
    val = (val || "").trim();
    if (val && !val.startsWith("#")) val = "#" + val;
    if (val && !/^#[0-9A-Fa-f]{6}$/.test(val)) {
        showToast('Enter a valid hex code like #FF3366', true);
        renderZoneDetail(index);
        return;
    }
    zones[index].fifthBaseColor = val || '#ffffff';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneFifthBaseStrength(index, val) {
    pushZoneUndo('', true);
    zones[index].fifthBaseStrength = (parseInt(val) || 0) / 100;
    const pct = Math.round((zones[index].fifthBaseStrength) * 100);
    const label = document.getElementById('detFifStrVal' + index);
    if (label) label.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFifStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneFifthBaseStrength(index, delta) {
    const cur = Math.round((zones[index].fifthBaseStrength ?? 0) * 100);
    setZoneFifthBaseStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneFifthBaseBlendMode(index, val) { pushZoneUndo('Set 5th overlay blend'); zones[index].fifthBaseBlendMode = val || 'noise'; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFifthBaseFractalScale(index, val) {
    pushZoneUndo('Set 5th overlay Fractal Detail', true);
    zones[index].fifthBaseFractalScale = Math.max(4, Math.min(128, parseInt(val) || 24));
    const v = zones[index].fifthBaseFractalScale;
    const label = document.getElementById('detFifNSVal' + index);
    if (label) label.textContent = v + 'px';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFifNSVal' + index); if (span) span.textContent = v + 'px'; }
    triggerPreviewRender();
}
function stepZoneFifthBaseFractalScale(index, delta) {
    const cur = zones[index].fifthBaseFractalScale ?? 24;
    setZoneFifthBaseFractalScale(index, Math.max(4, Math.min(128, cur + delta * 4)));
}
function setZoneFifthBaseScale(index, val) {
    if (index < 0 || index >= zones.length) return;
    let v = parseFloat(val) || 1;
    v = roundToStep(v, SCALE_STEP);
    const n = Math.max(SCALE_OVERLAY_MIN, Math.min(SCALE_OVERLAY_MAX, v));
    zones[index].fifthBaseScale = n;
    pushZoneUndoCoalesced('Set 5th overlay scale');
    const card = document.getElementById('zone-card-' + index);
    if (card) { const span = card.querySelector('#detFifScaleVal' + index); if (span) span.textContent = n.toFixed(2); }
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFifScaleVal' + index); if (span) span.textContent = n.toFixed(2); }
    triggerPreviewRender();
}
function stepZoneFifthBaseScale(index, delta) {
    const cur = zones[index].fifthBaseScale ?? 1;
    setZoneFifthBaseScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneFifthBasePattern(index, val) { pushZoneUndo('Set 5th base pattern'); zones[index].fifthBasePattern = val || null; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFifthBasePatternOpacity(index, val) {
    pushZoneUndo('', true);
    zones[index].fifthBasePatternOpacity = Math.max(0, Math.min(100, parseInt(val) ?? 100));
    const v = zones[index].fifthBasePatternOpacity;
    const el = document.getElementById('detFifPatOpVal' + index); if (el) el.textContent = v + '%';
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) { const span = panel.querySelector('#detFifPatOpVal' + index); if (span) span.textContent = v + '%'; }
    triggerPreviewRender();
}
function stepZoneFifthBasePatternOpacity(index, delta) {
    const cur = zones[index].fifthBasePatternOpacity ?? 100;
    setZoneFifthBasePatternOpacity(index, Math.max(0, Math.min(100, cur + delta * 5)));
}
function setZoneFifthBasePatternScale(index, val) {
    pushZoneUndo('', true);
    let v = parseFloat(val) ?? 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[index].fifthBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
    const el = document.getElementById('detFifPatScaleVal' + index); if (el) el.textContent = (zones[index].fifthBasePatternScale).toFixed(2) + 'x';
    triggerPreviewRender();
}
function stepZoneFifthBasePatternScale(index, delta) {
    const cur = zones[index].fifthBasePatternScale ?? 1.0;
    setZoneFifthBasePatternScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function setZoneFifthBasePatternRotation(index, val) {
    pushZoneUndo('', true);
    let v = parseInt(val) ?? 0;
    v = ((v % 360) + 360) % 360;
    zones[index].fifthBasePatternRotation = v;
    const el = document.getElementById('detFifPatRotVal' + index); if (el) el.value = v;
    const rangeEl = document.getElementById('detFifPatRotRange' + index); if (rangeEl) rangeEl.value = v;
    triggerPreviewRender();
}
function stepZoneFifthBasePatternRotation(index, delta) {
    const cur = zones[index].fifthBasePatternRotation ?? 0;
    setZoneFifthBasePatternRotation(index, cur + delta * 5);
}
function setZoneFifthBasePatternStrength(index, val) {
    pushZoneUndo('', true);
    zones[index].fifthBasePatternStrength = Math.max(0, Math.min(2, (parseInt(val) ?? 100) / 100));
    const pct = Math.round((zones[index].fifthBasePatternStrength) * 100);
    const el = document.getElementById('detFifPatStrVal' + index); if (el) el.textContent = pct + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detFifPatStrVal' + index); if (span) span.textContent = pct + '%'; }
    triggerPreviewRender();
}
function stepZoneFifthBasePatternStrength(index, delta) {
    const cur = Math.round((zones[index].fifthBasePatternStrength ?? 1) * 100);
    setZoneFifthBasePatternStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
}
function setZoneFifthBasePatternInvert(index, val) { pushZoneUndo('', true); zones[index].fifthBasePatternInvert = !!val; triggerPreviewRender(); }
function setZoneFifthBasePatternHarden(index, val) { pushZoneUndo('', true); zones[index].fifthBasePatternHarden = !!val; triggerPreviewRender(); }
function setZoneFifthBasePatternOffsetX(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].fifthBasePatternOffsetX = v;
    const el = document.getElementById('detFifPatPosXVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detFifPatPosXVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
function setZoneFifthBasePatternOffsetY(index, val) {
    pushZoneUndo('', true);
    const v = Math.max(0, Math.min(1, Number(val) / 100));
    zones[index].fifthBasePatternOffsetY = v;
    const el = document.getElementById('detFifPatPosYVal' + index); if (el) el.textContent = Math.round(v * 100) + '%';
    const panel = document.getElementById('zoneEditorFloat'); if (panel) { const span = panel.querySelector('#detFifPatPosYVal' + index); if (span) span.textContent = Math.round(v * 100) + '%'; }
    triggerPreviewRender();
}
/** Copy primary pattern position, scale, and rotation to 5th base overlay so it lines up exactly. */
function alignFifthBaseOverlayWithSelectedPattern(index) {
    const z = zones[index];
    if (!z || !z.fifthBase) return;
    pushZoneUndo('', true);

    const targetPatId = z.fifthBasePattern || '';
    let sx = 1.0, rot = 0, px = 0.5, py = 0.5;

    if (!targetPatId || targetPatId === 'none') {
        sx = z.scale ?? 1.0;
        rot = z.rotation ?? 0;
        px = z.patternOffsetX ?? 0.5;
        py = z.patternOffsetY ?? 0.5;
    } else {
        // Check patternStack first (Pattern 2, 3, 4 — the stacked additional patterns)
        const stack = z.patternStack || [];
        let foundInStack = false;
        const pat = stack.find(p => p.id === targetPatId);
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.offsetX ?? 0.5;
            py = pat.offsetY ?? 0.5;
            foundInStack = true;
        }
        // Check if it matches the primary pattern (Pattern 1) — stored directly on z, not in patternStack
        if (!foundInStack && z.pattern && z.pattern === z.fifthBasePattern) {
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
            foundInStack = true;
        }
        if (!foundInStack) {
            // Fall back to primary pattern position as best guess
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
        }
    }

    z.fifthBasePatternOffsetX = px;
    z.fifthBasePatternOffsetY = py;
    z.fifthBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, sx));
    z.fifthBasePatternRotation = ((rot % 360) + 360) % 360;
    
    const pctX = Math.round((z.fifthBasePatternOffsetX) * 100) + '%', pctY = Math.round((z.fifthBasePatternOffsetY) * 100) + '%';
    const scaleVal = (z.fifthBasePatternScale).toFixed(2), rotVal = z.fifthBasePatternRotation;
    
    ['detFifPatPosXVal', 'detFifPatPosYVal'].forEach((id, idx) => {
        const span = document.getElementById(id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.fifthBasePatternOffsetY * 100) : Math.round(z.fifthBasePatternOffsetX * 100); }
    });
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        ['detFifPatPosXVal', 'detFifPatPosYVal'].forEach((id, idx) => {
            const span = panel.querySelector('#' + id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.fifthBasePatternOffsetY * 100) : Math.round(z.fifthBasePatternOffsetX * 100); }
        });
    }
    const scaleSpan = document.getElementById('detFifPatScaleVal' + index); if (scaleSpan) scaleSpan.textContent = scaleVal + 'x';
    const scaleInput = scaleSpan && scaleSpan.previousElementSibling && scaleSpan.previousElementSibling.previousElementSibling; if (scaleInput && scaleInput.type === 'range') scaleInput.value = Math.round(z.fifthBasePatternScale * 100);
    const rotInput = document.getElementById('detFifPatRotVal' + index); if (rotInput) rotInput.value = rotVal;
    const rotRange = document.getElementById('detFifPatRotRange' + index); if (rotRange) rotRange.value = rotVal;
    
    triggerPreviewRender();
    showToast('Overlay aligned with selected pattern (position, scale, rotation)');
}

/** Copy primary pattern position, scale, and rotation to 3rd base overlay so it lines up exactly. */
function alignThirdBaseOverlayWithSelectedPattern(index) {
    const z = zones[index];
    if (!z || !z.thirdBase) return;
    pushZoneUndo('', true);

    const targetPatId = z.thirdBasePattern || '';
    let sx = 1.0, rot = 0, px = 0.5, py = 0.5;

    if (!targetPatId || targetPatId === 'none') {
        sx = z.scale ?? 1.0;
        rot = z.rotation ?? 0;
        px = z.patternOffsetX ?? 0.5;
        py = z.patternOffsetY ?? 0.5;
    } else {
        // Check patternStack first (Pattern 2, 3, 4 — the stacked additional patterns)
        const stack = z.patternStack || [];
        let foundInStack = false;
        const pat = stack.find(p => p.id === targetPatId);
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.offsetX ?? 0.5;
            py = pat.offsetY ?? 0.5;
            foundInStack = true;
        }
        // Check if it matches the primary pattern (Pattern 1) — stored directly on z, not in patternStack
        if (!foundInStack && z.pattern && z.pattern === z.thirdBasePattern) {
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
            foundInStack = true;
        }
        if (!foundInStack) {
            // Fall back to primary pattern position as best guess
            sx = z.scale ?? 1.0;
            rot = z.rotation ?? 0;
            px = z.patternOffsetX ?? 0.5;
            py = z.patternOffsetY ?? 0.5;
        }
    }

    z.thirdBasePatternOffsetX = px;
    z.thirdBasePatternOffsetY = py;
    z.thirdBasePatternScale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, sx));
    z.thirdBasePatternRotation = ((rot % 360) + 360) % 360;
    
    const pctX = Math.round((z.thirdBasePatternOffsetX) * 100) + '%', pctY = Math.round((z.thirdBasePatternOffsetY) * 100) + '%';
    const scaleVal = (z.thirdBasePatternScale).toFixed(2), rotVal = z.thirdBasePatternRotation;
    
    ['detTBPatPosXVal', 'detTBPatPosYVal'].forEach((id, idx) => {
        const span = document.getElementById(id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.thirdBasePatternOffsetY * 100) : Math.round(z.thirdBasePatternOffsetX * 100); }
    });
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
        ['detTBPatPosXVal', 'detTBPatPosYVal'].forEach((id, idx) => {
            const span = panel.querySelector('#' + id + index); if (span) { span.textContent = idx ? pctY : pctX; const inp = span.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? Math.round(z.thirdBasePatternOffsetY * 100) : Math.round(z.thirdBasePatternOffsetX * 100); }
        });
    }
    const scaleSpan = document.getElementById('detTBPatScaleVal' + index); if (scaleSpan) scaleSpan.textContent = scaleVal + 'x';
    const scaleInput = scaleSpan && scaleSpan.previousElementSibling && scaleSpan.previousElementSibling.previousElementSibling; if (scaleInput && scaleInput.type === 'range') scaleInput.value = Math.round(z.thirdBasePatternScale * 100);
    const rotInput = document.getElementById('detTBPatRotVal' + index); if (rotInput) rotInput.value = rotVal;
    const rotRange = document.getElementById('detTBPatRotRange' + index); if (rotRange) rotRange.value = rotVal;
    
    triggerPreviewRender();
    showToast('Overlay aligned with selected pattern (position, scale, rotation)');
}

// ===== LEGACY v6 SETTERS (kept for backward compat) =====
function setZoneCCQuality(index, val) {
    pushZoneUndo('Set CC quality', true);
    zones[index].ccQuality = parseInt(val) || 100;
    const label = document.getElementById('detCCQVal' + index);
    if (label) label.textContent = zones[index].ccQuality + '%';
    triggerPreviewRender();
}
function resetZoneCCQuality(index) {
    pushZoneUndo('Reset CC quality');
    zones[index].ccQuality = 100;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBlendBase(index, val) {
    pushZoneUndo('Set blend base');
    zones[index].blendBase = val || '';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBlendDir(index, val) {
    pushZoneUndo('Set blend direction');
    zones[index].blendDir = val || 'horizontal';
    triggerPreviewRender();
}
function setZoneBlendAmount(index, val) {
    pushZoneUndo('Set blend amount');
    zones[index].blendAmount = parseInt(val) || 50;
    const label = document.getElementById('detBlendAmtVal' + index);
    if (label) label.textContent = zones[index].blendAmount + '%';
    triggerPreviewRender();
}
function setZonePaintReactiveColor(index, val) {
    pushZoneUndo('Set paint-reactive color');
    zones[index].paintReactiveColor = val || '#000000';
    triggerPreviewRender();
}
function setZoneUsePaintReactive(index, checked) {
    pushZoneUndo('Toggle paint-reactive');
    zones[index].usePaintReactive = !!checked;
    triggerPreviewRender();
}

function setPatternLayerRotation(zoneIdx, layerIdx, val) {
    pushZoneUndoCoalesced('Rotate pattern layer ' + (layerIdx + 1));
    const intVal = parseInt(val) || 0;
    if (zones[zoneIdx].patternStack && zones[zoneIdx].patternStack[layerIdx]) {
        zones[zoneIdx].patternStack[layerIdx].rotation = intVal;
    }
    // Live update both slider and number input
    const row = document.querySelector(`#zoneEditorFloat .pattern-layer-card[data-layer-idx="${layerIdx}"][data-zone-idx="${zoneIdx}"]`)
        || document.querySelector(`#zone-card-${zoneIdx} .pattern-layer-card[data-layer-idx="${layerIdx}"]`);
    if (row) {
        const groups = row.querySelectorAll('.stack-control-group');
        const rotGroup = groups[2]; // 0=opacity, 1=scale, 2=rotate
        if (rotGroup) {
            const slider = rotGroup.querySelector('input[type="range"]');
            const numInput = rotGroup.querySelector('input[type="number"]');
            if (slider && slider !== document.activeElement) slider.value = intVal;
            if (numInput && numInput !== document.activeElement) numInput.value = intVal;
        }
    }
    triggerPreviewRender();
}

// ===== IMPORT SPEC MAP (MERGE MODE) =====
function importSpecMapFromFile() {
    // Use the existing browse filesystem to pick a TGA
    let startPath = '';
    const currentPaint = document.getElementById('paintFile').value.trim();
    if (currentPaint) startPath = currentPaint.replace(/[/\\][^/\\]+$/, '');
    openFilePicker({
        title: 'Select Spec Map TGA to Import',
        filter: '.tga',
        mode: 'file',
        startPath: startPath,
        onSelect: function (filePath) {
            if (!filePath) return;
            fetch('/upload-spec-map', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ spec_path: filePath })
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        importedSpecMapPath = data.temp_path;
                        const status = document.getElementById('importSpecMapStatus');
                        if (status) {
                            const fname = filePath.split('/').pop().split('\\').pop();
                            status.innerHTML = `<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active · Layer 0</span> — ${escapeHtml(fname)} (${data.resolution[0]}×${data.resolution[1]})`;
                        }
                        document.getElementById('btnClearSpecMap').disabled = false;
                        showToast('Spec map imported — Layer 0 active');
                        triggerPreviewRender();
                    } else {
                        showToast('Failed to import spec map: ' + (data.error || 'unknown'), true);
                    }
                })
                .catch(err => showToast('Spec map import error: ' + err, true));
        }
    });
}

function importSpecMapFromDrop(file) {
    // Handle drag-drop or file input of a TGA/PNG spec map
    const reader = new FileReader();
    reader.onload = function (e) {
        fetch('/upload-spec-map', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spec_data: e.target.result })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    importedSpecMapPath = data.temp_path;
                    const status = document.getElementById('importSpecMapStatus');
                    if (status) {
                        status.innerHTML = `<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active · Layer 0</span> — ${escapeHtml(file.name)} (${data.resolution[0]}×${data.resolution[1]})`;
                    }
                    document.getElementById('btnClearSpecMap').disabled = false;
                    showToast('Spec map imported — Layer 0 active');
                    triggerPreviewRender();
                } else {
                    showToast('Failed to import spec map: ' + (data.error || 'unknown'), true);
                }
            })
            .catch(err => showToast('Spec map import error: ' + err, true));
    };
    reader.readAsDataURL(file);
}

function clearImportedSpecMap() {
    // 2026-04-19 Hennig polish P3: parity early-return.
    if (!importedSpecMapPath) {
        if (typeof showToast === 'function') showToast('Nothing to clear — no spec map is loaded');
        return;
    }
    // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W10c): destructive without confirm.
    if (typeof confirm === 'function' &&
        !confirm('Clear the imported spec map? You will need to re-import or re-load from SHOKK to restore it.')) {
        return;
    }
    importedSpecMapPath = null;
    const status = document.getElementById('importSpecMapStatus');
    if (status) status.textContent = 'No spec map — zones render on default base';
    document.getElementById('btnClearSpecMap').disabled = true;
    showToast('Spec cleared — zones render on default base');
    triggerPreviewRender();
}

// ===== PATTERN STACK CONTROLS =====
function addPatternLayer(zoneIdx) {
    pushZoneUndo('Add pattern layer');
    if (!zones[zoneIdx].patternStack) zones[zoneIdx].patternStack = [];
    if (zones[zoneIdx].patternStack.length >= MAX_PATTERN_STACK_LAYERS) { showToast(`Max ${MAX_PATTERN_LAYERS_PER_ZONE} patterns (Pattern 1 + ${MAX_PATTERN_STACK_LAYERS} layers)`, true); return; }
    zones[zoneIdx].patternStack.push({ id: 'none', opacity: 100, scale: 1.0, rotation: 0, blendMode: 'normal', offsetX: 0.5, offsetY: 0.5 });
    renderZones();
    triggerPreviewRender();
}

function removePatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo('Remove pattern layer ' + (layerIdx + 1));
    zones[zoneIdx].patternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}

function setPatternLayerId(zoneIdx, layerIdx, val) {
    pushZoneUndo('Set pattern layer ' + (layerIdx + 1) + ': ' + val);
    zones[zoneIdx].patternStack[layerIdx].id = val;
    renderZones();
    triggerPreviewRender();
}

function setPatternLayerOpacity(zoneIdx, layerIdx, val) {
    // 2026-04-18 MARATHON bug #58 (MED): setPatternLayerRotation already
    // uses pushZoneUndoCoalesced — opacity and scale siblings were
    // asymmetric. Painter dragged the opacity slider on a pattern stack
    // layer, Ctrl+Z did nothing (or lost an unrelated prior edit).
    if (typeof pushZoneUndoCoalesced === 'function') {
        pushZoneUndoCoalesced('Pattern layer opacity ' + (layerIdx + 1));
    }
    const v = Math.max(0, Math.min(100, parseInt(val) || 100));
    zones[zoneIdx].patternStack[layerIdx].opacity = v;
    // Live update the value label (use data-layer-idx for robust lookup)
    const row = document.querySelector(`#zoneEditorFloat .pattern-layer-card[data-layer-idx="${layerIdx}"][data-zone-idx="${zoneIdx}"]`)
        || document.querySelector(`#zone-card-${zoneIdx} .pattern-layer-card[data-layer-idx="${layerIdx}"]`);
    if (row) {
        const groups = row.querySelectorAll('.stack-control-group');
        const opGroup = groups[0];
        if (opGroup) {
            const span = opGroup.querySelector('.stack-val');
            if (span) span.textContent = v + '%';
        }
    }
    triggerPreviewRender();
}
function stepPatternLayerOpacity(zoneIdx, layerIdx, delta) {
    const cur = (zones[zoneIdx].patternStack[layerIdx] && zones[zoneIdx].patternStack[layerIdx].opacity) ?? 100;
    setPatternLayerOpacity(zoneIdx, layerIdx, Math.max(0, Math.min(100, cur + delta * 5)));
}

function setPatternLayerScale(zoneIdx, layerIdx, val) {
    // 2026-04-18 MARATHON bug #58 family: match setPatternLayerRotation's
    // pushZoneUndoCoalesced contract for the scale slider too.
    if (typeof pushZoneUndoCoalesced === 'function') {
        pushZoneUndoCoalesced('Pattern layer scale ' + (layerIdx + 1));
    }
    let v = parseFloat(val) || 1.0;
    v = roundToStep(v, SCALE_STEP);
    zones[zoneIdx].patternStack[layerIdx].scale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
    // Live update label
    const row = document.querySelector(`#zoneEditorFloat .pattern-layer-card[data-layer-idx="${layerIdx}"][data-zone-idx="${zoneIdx}"]`)
        || document.querySelector(`#zone-card-${zoneIdx} .pattern-layer-card[data-layer-idx="${layerIdx}"]`);
    if (row) {
        const groups = row.querySelectorAll('.stack-control-group');
        const scaleGroup = groups[1];
        if (scaleGroup) {
            const span = scaleGroup.querySelector('.stack-val');
            if (span) span.textContent = (zones[zoneIdx].patternStack[layerIdx].scale).toFixed(2) + 'x';
            const scaleInput = scaleGroup.querySelector('input[type="range"]');
            if (scaleInput) scaleInput.value = Math.round(zones[zoneIdx].patternStack[layerIdx].scale * 100);
        }
    }
    triggerPreviewRender();
}
function stepPatternLayerScale(zoneIdx, layerIdx, delta) {
    const cur = (zones[zoneIdx].patternStack[layerIdx] && zones[zoneIdx].patternStack[layerIdx].scale) || 1.0;
    setPatternLayerScale(zoneIdx, layerIdx, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
}
function stepPatternLayerRotation(zoneIdx, layerIdx, delta) {
    const cur = (zones[zoneIdx].patternStack[layerIdx] && zones[zoneIdx].patternStack[layerIdx].rotation) || 0;
    setPatternLayerRotation(zoneIdx, layerIdx, Math.max(0, Math.min(359, cur + delta)));
}

function setPatternLayerBlend(zoneIdx, layerIdx, val) {
    // FIVE-HOUR SHIFT Win C4: pre-fix this was the asymmetric outlier — every
    // sister mutator (setPatternLayerOpacity / setPatternLayerScale /
    // setPatternLayerRotation) pushes zoneUndoCoalesced, but the blend-mode
    // dropdown skipped undo entirely. Painter switched blend modes hunting for
    // the right look, lost the prior choice with no Ctrl+Z. Aligning with sisters.
    if (typeof pushZoneUndoCoalesced === 'function') {
        pushZoneUndoCoalesced('Pattern layer blend ' + (layerIdx + 1));
    } else if (typeof pushZoneUndo === 'function') {
        pushZoneUndo('Pattern layer blend ' + (layerIdx + 1));
    }
    if (zones[zoneIdx] && zones[zoneIdx].patternStack && zones[zoneIdx].patternStack[layerIdx]) {
        zones[zoneIdx].patternStack[layerIdx].blendMode = val;
    }
    triggerPreviewRender();
}

function setZoneWear(index, val) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] setZoneWear: invalid zone index', index);
        return;
    }
    pushZoneUndoCoalesced('Set wear');
    const clamped = Math.max(0, Math.min(100, parseInt(val) || 0));
    zones[index].wear = clamped;
    const label = document.getElementById('detWearVal' + index) || document.getElementById('wearVal' + index);
    if (label) label.textContent = clamped + '%';
    triggerPreviewRender();
}

// ===== SPEC PATTERN STACK CONTROLS =====

function _getSpecPatternDef(patternId) {
    const allSp = (typeof SPEC_PATTERNS !== 'undefined' && Array.isArray(SPEC_PATTERNS)) ? SPEC_PATTERNS : [];
    for (let i = 0; i < allSp.length; i++) {
        if (allSp[i] && allSp[i].id === patternId) return allSp[i];
    }
    return null;
}

function _inferSpecPatternDefaultChannels(spDef) {
    if (!spDef) return 'MR';
    if (typeof spDef.defaultChannels === 'string' && spDef.defaultChannels.trim()) {
        return spDef.defaultChannels.trim().toUpperCase();
    }
    const desc = String(spDef.desc || '');
    let channels = '';
    if (/R=Metallic\b/i.test(desc)) channels += 'M';
    if (/G=Roughness\b/i.test(desc)) channels += 'R';
    if (/B=Clearcoat\b/i.test(desc)) channels += 'C';
    return channels || 'MR';
}

function _getSpecPatternLayerDefaults(patternId) {
    const spDef = _getSpecPatternDef(patternId);
    const parsedOpacity = Number(spDef && spDef.defaultOpacity);
    const parsedRange = Number(spDef && spDef.defaultRange);
    return {
        spDef: spDef,
        opacity: Number.isFinite(parsedOpacity) ? Math.max(0, Math.min(100, parsedOpacity)) : 50,
        blendMode: (spDef && typeof spDef.defaultBlendMode === 'string' && spDef.defaultBlendMode.trim()) ? spDef.defaultBlendMode : 'normal',
        channels: _inferSpecPatternDefaultChannels(spDef),
        range: Number.isFinite(parsedRange) ? parsedRange : 40,
        params: spDef ? JSON.parse(JSON.stringify(spDef.defaults || {})) : {}
    };
}

function _buildSpecPatternLayer(patternId) {
    const defaults = _getSpecPatternLayerDefaults(patternId);
    return {
        pattern: patternId,
        opacity: defaults.opacity,
        blendMode: defaults.blendMode,
        channels: defaults.channels,
        channelsCustomized: false,
        range: defaults.range,
        params: defaults.params,
        offsetX: 0.5,
        offsetY: 0.5,
        scale: 1.0,
        rotation: 0,
        boxSize: 100,
        placement: 'normal'
    };
}

function _getSpecPatternFallbackChannels(entry) {
    const defaults = _getSpecPatternLayerDefaults(entry && entry.pattern);
    return defaults.channels || 'MR';
}

// Tab-filter helper for spec overlay picker grids
// gridId: the id of the grid div (e.g. "specPatternGrid0")
// group:  group name to show, or "All" to show everything
function addSpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add spec pattern');
    if (!zones[zoneIdx].specPatternStack) zones[zoneIdx].specPatternStack = [];
    if (zones[zoneIdx].specPatternStack.length >= 5) { showToast('Maximum 5 spec pattern layers', true); return; }
    zones[zoneIdx].specPatternStack.push(_buildSpecPatternLayer(patternId));
    renderZones();
    triggerPreviewRender();
}

function removeSpecPatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo('Remove spec pattern');
    zones[zoneIdx].specPatternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}

function setSpecPatternLayerProp(zoneIdx, layerIdx, prop, val) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].specPatternStack || !zones[zoneIdx].specPatternStack[layerIdx]) return;
    zones[zoneIdx].specPatternStack[layerIdx][prop] = val;
    triggerPreviewRender();
}

function stepSpecPatternLayerProp(zoneIdx, layerIdx, prop, delta, minVal, maxVal) {
    if (!zones[zoneIdx].specPatternStack || !zones[zoneIdx].specPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].specPatternStack[layerIdx];
    let cur;
    if (prop === 'offsetX' || prop === 'offsetY') {
        cur = Math.round((sp[prop] ?? 0.5) * 100);
        const nv = Math.max(minVal, Math.min(maxVal, cur + delta));
        setSpecPatternLayerProp(zoneIdx, layerIdx, prop, nv / 100);
    } else if (prop === 'scale') {
        cur = Math.round((sp[prop] ?? 1) * 100);
        const nv = Math.max(minVal, Math.min(maxVal, cur + delta));
        setSpecPatternLayerProp(zoneIdx, layerIdx, prop, nv / 100);
    } else if (prop === 'rotation') {
        cur = sp[prop] ?? 0;
        const nv = Math.max(minVal, Math.min(maxVal, cur + delta));
        setSpecPatternLayerProp(zoneIdx, layerIdx, prop, nv);
    } else if (prop === 'boxSize') {
        cur = sp[prop] ?? 100;
        const nv = Math.max(minVal, Math.min(maxVal, cur + delta));
        setSpecPatternLayerProp(zoneIdx, layerIdx, prop, nv);
    }
    renderZones();
}

// Tracks active category per picker: key = "zoneIdx_layerIdx", value = category name
var _specPickerActiveCat = {};

function specPickerCatTab(gridId, btnEl, catName) {
    // Toggle category filter for a spec pattern grid (used by both inline pickers and add-grid)
    var grid = document.getElementById(gridId);
    if (!grid) return;
    // Update active tab styling
    var tabRow = btnEl.parentElement;
    tabRow.querySelectorAll('.spec-cat-tab').forEach(function(b) { b.classList.remove('active'); });
    btnEl.classList.add('active');
    // Filter cards
    grid.querySelectorAll('.spec-pattern-thumb-card').forEach(function(card) {
        if (catName === 'All' || card.dataset.category === catName) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Get the URL for a spec pattern thumbnail.
 * Prefers pre-baked static file; JS onerror on <img> falls back to live API.
 * @param {string} patternId - The spec pattern ID
 * @param {string} [type='preview'] - 'preview' for M/R/CC split, 'metal' for metallic sim
 * @returns {string} URL
 */
function getSpecThumbUrl(patternId, type) {
    var folder = (type === 'metal') ? 'spec_patterns_metal' : 'spec_patterns';
    return '/thumbnails/' + folder + '/' + patternId + '.png';
}

function toggleSpecPatternPicker(zoneIdx, layerIdx) {
    document.querySelectorAll('.spec-thumb-popup').forEach(p => p.remove());
    const picker = document.getElementById('specPatternPicker_' + zoneIdx + '_' + layerIdx);
    if (!picker) return;
    if (picker.dataset.pickerOpen === '1') {
        picker.dataset.pickerOpen = '0';
        picker.style.display = 'none';
        var tabRowOld = document.getElementById('specPickerTabs_' + zoneIdx + '_' + layerIdx);
        if (tabRowOld) tabRowOld.style.display = 'none';
        return;
    }
    // Close any other open pickers
    document.querySelectorAll('[id^="specPatternPicker_"]').forEach(function(p) {
        p.style.display = 'none';
        p.dataset.pickerOpen = '0';
    });
    document.querySelectorAll('[id^="specPickerTabs_"]').forEach(function(t) { t.style.display = 'none'; });

    // Build grid content if not yet built
    if (!picker.dataset.built) {
        var currentId = picker.dataset.current || '';
        var allSp = typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : [];
        var spGroups = typeof SPEC_PATTERN_GROUPS !== 'undefined' ? SPEC_PATTERN_GROUPS : {};
        // Build category map
        var catMap = {};
        Object.entries(spGroups).forEach(function(e) { e[1].forEach(function(id) { catMap[id] = e[0]; }); });

        // Build tab row (inserted before picker in DOM)
        var tabRowId = 'specPickerTabs_' + zoneIdx + '_' + layerIdx;
        var existingTabRow = document.getElementById(tabRowId);
        if (!existingTabRow) {
            existingTabRow = document.createElement('div');
            existingTabRow.id = tabRowId;
            existingTabRow.className = 'spec-cat-tab-row';
            existingTabRow.style.display = 'none';
            picker.parentNode.insertBefore(existingTabRow, picker);
        }
        var tabsHtml = ['All', ...Object.keys(spGroups)].map(function(g) {
            return '<button class="spec-cat-tab' + (g === 'All' ? ' active' : '') + '" data-cat="' + g.replace(/"/g, '&quot;') + '" onclick="(function(btn){var pickerId=\'specPatternPicker_' + zoneIdx + '_' + layerIdx + '\';var grid=document.getElementById(pickerId);if(!grid)return;grid.querySelectorAll(\'.spec-cat-tab-row .spec-cat-tab\').forEach(function(b){b.classList.remove(\'active\')});btn.classList.add(\'active\');var cn=btn.dataset.cat;grid.querySelectorAll(\'.spec-pattern-thumb-card\').forEach(function(c){c.style.display=(cn===\'All\'||c.dataset.category===cn)?\'\':\' none\';}); })(this)" title="' + g.replace(/"/g, '&quot;') + '">' + g + '</button>';
        }).join('');
        existingTabRow.innerHTML = tabsHtml;

        // Build cards
        var html = '';
        allSp.forEach(function(p) {
            var isActive = p.id === currentId ? ' sp-thumb-active' : '';
            var cat = catMap[p.id] || 'Misc';
            var shortName = p.name.length > 12 ? p.name.slice(0, 12) + '\u2026' : p.name;
            html += '<div class="spec-pattern-thumb-card' + isActive + '" data-spid="' + p.id + '" data-category="' + cat + '" title="' + p.name + ': ' + (p.desc || '').replace(/"/g, '&quot;') + '" style="cursor:pointer;">';
            html += '<img src="/thumbnails/spec_patterns/' + p.id + '.png" alt="' + p.name + '" loading="eager" style="width:48px;height:48px;object-fit:cover;" onerror="this.src=\'/api/spec-pattern-preview/' + p.id + '?v=live\';this.onerror=null;">';
            html += '<div class="thumb-label">' + shortName + '</div></div>';
        });
        picker.innerHTML = html;

        // Restore last active category
        var savedCat = _specPickerActiveCat[zoneIdx + '_' + layerIdx] || 'All';
        if (savedCat !== 'All') {
            picker.querySelectorAll('.spec-pattern-thumb-card').forEach(function(card) {
                card.style.display = (card.dataset.category === savedCat) ? '' : 'none';
            });
            var savedBtn = existingTabRow.querySelector('[data-cat="' + savedCat + '"]');
            if (savedBtn) {
                existingTabRow.querySelectorAll('.spec-cat-tab').forEach(function(b) { b.classList.remove('active'); });
                savedBtn.classList.add('active');
            }
        }

        // Attach click and hover handlers via delegation
        picker.addEventListener('click', function(e) {
            var card = e.target.closest('.spec-pattern-thumb-card');
            if (!card) return;
            document.querySelectorAll('.spec-thumb-popup').forEach(function(p) { p.remove(); });
            // Save active cat
            var activeTabBtn = existingTabRow.querySelector('.spec-cat-tab.active');
            _specPickerActiveCat[zoneIdx + '_' + layerIdx] = activeTabBtn ? activeTabBtn.dataset.cat : 'All';
            changeSpecPatternType(zoneIdx, layerIdx, card.dataset.spid);
            picker.style.display = 'none';
            picker.dataset.pickerOpen = '0';
            existingTabRow.style.display = 'none';
        });
        picker.addEventListener('mouseover', function(e) {
            var card = e.target.closest('.spec-pattern-thumb-card');
            if (!card || card._spPopup) return;
            var img = card.querySelector('img');
            if (!img) return;
            var popup = document.createElement('div');
            popup.className = 'spec-thumb-popup';
            var pName = card.querySelector('.thumb-label');
            popup.innerHTML = '<img src="' + img.src + '" style="width:200px;height:100px;object-fit:contain;border-radius:6px;"><div style="text-align:center;font-size:11px;color:#ccc;padding:4px;">' + (pName ? pName.textContent : '') + '</div>';
            var rect = card.getBoundingClientRect();
            popup.style.left = Math.min(rect.left + rect.width / 2 - 104, window.innerWidth - 220) + 'px';
            popup.style.top = Math.max(rect.top - 148, 4) + 'px';
            document.body.appendChild(popup);
            card._spPopup = popup;
        });
        picker.addEventListener('mouseout', function(e) {
            var card = e.target.closest('.spec-pattern-thumb-card');
            if (card && card._spPopup) { card._spPopup.remove(); card._spPopup = null; }
        });
        picker.dataset.built = '1';
    } else {
        // Already built: restore saved category tab
        var tabRowExist = document.getElementById('specPickerTabs_' + zoneIdx + '_' + layerIdx);
        var savedCat2 = _specPickerActiveCat[zoneIdx + '_' + layerIdx] || 'All';
        if (tabRowExist) {
            tabRowExist.querySelectorAll('.spec-cat-tab').forEach(function(b) { b.classList.remove('active'); });
            var savedBtn2 = tabRowExist.querySelector('[data-cat="' + savedCat2 + '"]');
            if (savedBtn2) savedBtn2.classList.add('active');
            tabRowExist.style.display = 'flex';
        }
        picker.querySelectorAll('.spec-pattern-thumb-card').forEach(function(card) {
            card.style.display = (savedCat2 === 'All' || card.dataset.category === savedCat2) ? '' : 'none';
        });
    }

    // Show the tab row
    var tabRowFinal = document.getElementById('specPickerTabs_' + zoneIdx + '_' + layerIdx);
    if (tabRowFinal) tabRowFinal.style.display = 'flex';

    picker.style.display = 'grid';
    picker.dataset.pickerOpen = '1';
    picker.style.gridTemplateColumns = 'repeat(4, 1fr)';
    picker.style.gap = '6px';
    picker.style.padding = '6px';

    // Scroll active into view
    var active = picker.querySelector('.sp-thumb-active');
    if (active) setTimeout(function() { active.scrollIntoView({ block: 'center', behavior: 'smooth' }); }, 50);
}

function changeSpecPatternType(zoneIdx, layerIdx, newPatternId) {
    pushZoneUndo('Change spec pattern type');
    if (!zones[zoneIdx].specPatternStack || !zones[zoneIdx].specPatternStack[layerIdx]) return;
    const defaults = _getSpecPatternLayerDefaults(newPatternId);
    const layer = zones[zoneIdx].specPatternStack[layerIdx];
    layer.pattern = newPatternId;
    layer.params = defaults.params;
    layer.channels = defaults.channels;
    layer.channelsCustomized = false;
    renderZones();
    triggerPreviewRender();
}

function toggleSpecPatternChannel(zoneIdx, layerIdx, ch, checked) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].specPatternStack || !zones[zoneIdx].specPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].specPatternStack[layerIdx];
    let channels = sp.channels || _getSpecPatternFallbackChannels(sp);
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    if (!channels) channels = _getSpecPatternFallbackChannels(sp); // At least one must be selected
    sp.channels = channels;
    sp.channelsCustomized = true;
    renderZoneDetail(selectedZoneIndex);
    triggerPreviewRender();
}

// ===== SPEC PREVIEW PANEL =====
// Tracks base finish per zone preview
var _specPreviewBase = {};
// Tracks in-flight AbortControllers per zone (prevents stale fetch stalls)
var _specPreviewAbort = {};

function setSpecPreviewBase(zoneIdx, btnEl, base) {
    _specPreviewBase[zoneIdx] = base;
    var panel = btnEl.closest('.spec-preview-panel');
    if (panel) panel.querySelectorAll('.spec-preview-tab').forEach(function(b) { b.classList.remove('active'); });
    btnEl.classList.add('active');
    updateSpecPreview(zoneIdx);
}

function updateSpecPreview(zoneIdx) {
    var canvas = document.getElementById('specPreviewCanvas_' + zoneIdx);
    var status = document.getElementById('specPreviewStatus_' + zoneIdx);
    if (!canvas) return;
    var base = _specPreviewBase[zoneIdx] || 'chrome';
    var specStack = (zones[zoneIdx] && zones[zoneIdx].specPatternStack) ? zones[zoneIdx].specPatternStack : [];

    // Abort any in-progress fetch for this zone before starting a new one
    if (_specPreviewAbort[zoneIdx]) {
        _specPreviewAbort[zoneIdx].abort();
    }
    var controller = new AbortController();
    _specPreviewAbort[zoneIdx] = controller;
    var timeoutId = setTimeout(function() { controller.abort(); }, 5000);

    if (status) status.textContent = 'Rendering...';
    fetch('/api/spec-preview-composite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_spec_stack: specStack, base_finish: base }),
        signal: controller.signal
    }).then(function(r) {
        clearTimeout(timeoutId);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.blob();
    }).then(function(blob) {
        _specPreviewAbort[zoneIdx] = null;
        var url = URL.createObjectURL(blob);
        var img = new Image();
        img.onload = function() {
            var ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            URL.revokeObjectURL(url);
            if (status) status.textContent = '';
        };
        img.src = url;
    }).catch(function(err) {
        clearTimeout(timeoutId);
        _specPreviewAbort[zoneIdx] = null;
        if (err.name === 'AbortError') {
            if (status) status.textContent = 'Timed out';
        } else {
            if (status) status.textContent = 'Preview unavailable';
            console.warn('Spec preview error:', err);
        }
    });
}

// ===== OVERLAY SPEC PATTERN STACK CONTROLS =====
function addOverlaySpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add overlay spec pattern');
    if (!zones[zoneIdx].overlaySpecPatternStack) zones[zoneIdx].overlaySpecPatternStack = [];
    if (zones[zoneIdx].overlaySpecPatternStack.length >= 5) { showToast('Maximum 5 overlay spec pattern layers', true); return; }
    const layer = _buildSpecPatternLayer(patternId);
    delete layer.boxSize;
    delete layer.placement;
    zones[zoneIdx].overlaySpecPatternStack.push(layer);
    renderZones();
    triggerPreviewRender();
}
function removeOverlaySpecPatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo('Remove overlay spec pattern');
    zones[zoneIdx].overlaySpecPatternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}
function setOverlaySpecPatternLayerProp(zoneIdx, layerIdx, prop, val) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].overlaySpecPatternStack || !zones[zoneIdx].overlaySpecPatternStack[layerIdx]) return;
    zones[zoneIdx].overlaySpecPatternStack[layerIdx][prop] = val;
    triggerPreviewRender();
}
function toggleOverlaySpecPatternChannel(zoneIdx, layerIdx, ch, checked) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].overlaySpecPatternStack || !zones[zoneIdx].overlaySpecPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].overlaySpecPatternStack[layerIdx];
    let channels = sp.channels || _getSpecPatternFallbackChannels(sp);
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    sp.channels = channels || _getSpecPatternFallbackChannels(sp);
    sp.channelsCustomized = true;
    triggerPreviewRender();
}

// ===== THIRD OVERLAY SPEC PATTERN STACK CONTROLS =====
function addThirdOverlaySpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add third overlay spec pattern');
    if (!zones[zoneIdx].thirdOverlaySpecPatternStack) zones[zoneIdx].thirdOverlaySpecPatternStack = [];
    if (zones[zoneIdx].thirdOverlaySpecPatternStack.length >= 5) { showToast('Maximum 5 overlay spec pattern layers', true); return; }
    const layer = _buildSpecPatternLayer(patternId);
    delete layer.boxSize;
    delete layer.placement;
    zones[zoneIdx].thirdOverlaySpecPatternStack.push(layer);
    renderZones();
    triggerPreviewRender();
}
function removeThirdOverlaySpecPatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo('Remove third overlay spec pattern');
    zones[zoneIdx].thirdOverlaySpecPatternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}
function setThirdOverlaySpecPatternLayerProp(zoneIdx, layerIdx, prop, val) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].thirdOverlaySpecPatternStack || !zones[zoneIdx].thirdOverlaySpecPatternStack[layerIdx]) return;
    zones[zoneIdx].thirdOverlaySpecPatternStack[layerIdx][prop] = val;
    triggerPreviewRender();
}
function toggleThirdOverlaySpecPatternChannel(zoneIdx, layerIdx, ch, checked) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].thirdOverlaySpecPatternStack || !zones[zoneIdx].thirdOverlaySpecPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].thirdOverlaySpecPatternStack[layerIdx];
    let channels = sp.channels || _getSpecPatternFallbackChannels(sp);
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    sp.channels = channels || _getSpecPatternFallbackChannels(sp);
    sp.channelsCustomized = true;
    triggerPreviewRender();
}

// ===== FOURTH OVERLAY SPEC PATTERN STACK CONTROLS =====
function addFourthOverlaySpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add fourth overlay spec pattern');
    if (!zones[zoneIdx].fourthOverlaySpecPatternStack) zones[zoneIdx].fourthOverlaySpecPatternStack = [];
    if (zones[zoneIdx].fourthOverlaySpecPatternStack.length >= 5) { showToast('Maximum 5 overlay spec pattern layers', true); return; }
    const layer = _buildSpecPatternLayer(patternId);
    delete layer.boxSize;
    delete layer.placement;
    zones[zoneIdx].fourthOverlaySpecPatternStack.push(layer);
    renderZones();
    triggerPreviewRender();
}
function removeFourthOverlaySpecPatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo('Remove fourth overlay spec pattern');
    zones[zoneIdx].fourthOverlaySpecPatternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}
function setFourthOverlaySpecPatternLayerProp(zoneIdx, layerIdx, prop, val) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].fourthOverlaySpecPatternStack || !zones[zoneIdx].fourthOverlaySpecPatternStack[layerIdx]) return;
    zones[zoneIdx].fourthOverlaySpecPatternStack[layerIdx][prop] = val;
    triggerPreviewRender();
}
function toggleFourthOverlaySpecPatternChannel(zoneIdx, layerIdx, ch, checked) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].fourthOverlaySpecPatternStack || !zones[zoneIdx].fourthOverlaySpecPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].fourthOverlaySpecPatternStack[layerIdx];
    let channels = sp.channels || _getSpecPatternFallbackChannels(sp);
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    sp.channels = channels || _getSpecPatternFallbackChannels(sp);
    sp.channelsCustomized = true;
    triggerPreviewRender();
}

// ===== FIFTH OVERLAY SPEC PATTERN STACK CONTROLS =====
function addFifthOverlaySpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add fifth overlay spec pattern');
    if (!zones[zoneIdx].fifthOverlaySpecPatternStack) zones[zoneIdx].fifthOverlaySpecPatternStack = [];
    if (zones[zoneIdx].fifthOverlaySpecPatternStack.length >= 5) { showToast('Maximum 5 overlay spec pattern layers', true); return; }
    const layer = _buildSpecPatternLayer(patternId);
    delete layer.boxSize;
    delete layer.placement;
    zones[zoneIdx].fifthOverlaySpecPatternStack.push(layer);
    renderZones();
    triggerPreviewRender();
}
function removeFifthOverlaySpecPatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo('Remove fifth overlay spec pattern');
    zones[zoneIdx].fifthOverlaySpecPatternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}
function setFifthOverlaySpecPatternLayerProp(zoneIdx, layerIdx, prop, val) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].fifthOverlaySpecPatternStack || !zones[zoneIdx].fifthOverlaySpecPatternStack[layerIdx]) return;
    zones[zoneIdx].fifthOverlaySpecPatternStack[layerIdx][prop] = val;
    triggerPreviewRender();
}
function toggleFifthOverlaySpecPatternChannel(zoneIdx, layerIdx, ch, checked) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].fifthOverlaySpecPatternStack || !zones[zoneIdx].fifthOverlaySpecPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].fifthOverlaySpecPatternStack[layerIdx];
    let channels = sp.channels || _getSpecPatternFallbackChannels(sp);
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    sp.channels = channels || _getSpecPatternFallbackChannels(sp);
    sp.channelsCustomized = true;
    triggerPreviewRender();
}

function setZoneFinish(index, finishId) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] setZoneFinish: invalid zone index', index);
        return;
    }
    // Legacy compat — historically called from old UI paths. The function
    // is currently unreached by any live caller (verified 2026-04-24 Iter 5
    // setter-render-parity audit), but the invalidation calls below are
    // defensive: if a future wiring re-introduces a caller (saved-config
    // migration, plugin script, etc.) the painter must see both the
    // zone-list UI and the live preview update — silent state mutation
    // would be a trust violation per the project's render-parity contract.
    zones[index].finish = finishId || null;
    zones[index].base = null;
    zones[index].pattern = null;
    zones[index]._autoBaseColorFill = false;
    zones[index]._scopedBrushAutoBaseColor = false;
    if (typeof renderZones === 'function') renderZones();
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    if (typeof autoSave === 'function') autoSave();
}

function setZoneIntensity(index, intensity, fromSlider) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) {
        console.warn('[SPB] setZoneIntensity: invalid zone index', index);
        return;
    }
    if (intensity === 'custom') {
        // Switching to custom - keep current slider values or init from current preset
        pushZoneUndo('Switch to custom intensity');
        const z = zones[index];
        if (z.customSpec == null) {
            const vals = INTENSITY_VALUES[z.intensity] || INTENSITY_VALUES["100"];
            z.customSpec = vals.spec;
            z.customPaint = vals.paint;
            z.customBright = vals.bright;
        }
        renderZones();
        triggerPreviewRender();
        return;
    }
    // Clamp to 0-100
    const numVal = Math.max(0, Math.min(100, parseInt(intensity) || 100));
    // Store as string for backward compat with existing presets
    zones[index].intensity = String(numVal);
    zones[index].customSpec = null;
    zones[index].customPaint = null;
    zones[index].customBright = null;
    propagateToLinkedZones(index, ['intensity', 'customSpec', 'customPaint', 'customBright']);
    // CRITICAL: Do NOT call renderZones() when called from a slider drag event -
    // doing so rebuilds the DOM and repositions the slider back to stored value (jump bug).
    // Instead, just sync sibling inputs and labels without touching the slider itself.
    if (!fromSlider) {
        pushZoneUndo('Set intensity ' + numVal + '%');
        renderZones();
    } else {
        // Sync only the number input and summary text in the card without rebuilding DOM
        // Find sibling number input: the range and number input are siblings in the row
        const card = document.getElementById('zone-card-' + index);
        if (card) {
            // Sync number inputs that share value with this slider
            card.querySelectorAll('.intensity-control-group input[type="number"]').forEach(el => {
                if (el !== document.activeElement) el.value = numVal;
            });
            // Also sync the detail panel if open
            const detPanel = document.getElementById('zoneDetailPanel');
            if (detPanel) {
                detPanel.querySelectorAll('.intensity-control-group input[type="number"]').forEach(el => {
                    if (el !== document.activeElement) el.value = numVal;
                });
                detPanel.querySelectorAll('.intensity-control-group input[type="range"]').forEach(el => {
                    if (el !== document.activeElement) el.value = numVal;
                });
            }
        }
    }
    triggerPreviewRender();
}

// Tick intensity up or down by delta (usually ±1)
function tickZoneIntensity(index, delta) {
    const current = parseInt(zones[index].intensity) || 100;
    const next = Math.max(0, Math.min(100, current + delta));
    setZoneIntensity(index, String(next));
}

function setZonePatternIntensity(index, value) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    const numVal = Math.max(0, Math.min(100, parseInt(value) || 100));
    zones[index].patternIntensity = String(numVal);
    propagateToLinkedZones(index, ['patternIntensity']);
    pushZoneUndoCoalesced('Set pattern intensity');
    // Do NOT call renderZones() - it rebuilds the panel and resets scroll (panel.scrollTop = 0),
    // causing the Pattern slider to jump. Sync the other view's inputs without rebuilding.
    const card = document.getElementById('zone-card-' + index);
    if (card) {
        const groups = card.querySelectorAll('.intensity-rows-wrap .intensity-control-group');
        if (groups[1]) {
            const r = groups[1].querySelector('input[type="range"]');
            const n = groups[1].querySelector('input[type="number"]');
            if (r && r !== document.activeElement) r.value = numVal;
            if (n && n !== document.activeElement) n.value = numVal;
        }
    }
    const detPanel = document.getElementById('zoneEditorFloat');
    if (detPanel) {
        const groups = detPanel.querySelectorAll('.intensity-rows-wrap .intensity-control-group');
        if (groups[1]) {
            const r = groups[1].querySelector('input[type="range"]');
            const n = groups[1].querySelector('input[type="number"]');
            if (r && r !== document.activeElement) r.value = numVal;
            if (n && n !== document.activeElement) n.value = numVal;
        }
    }
    triggerPreviewRender();
}

// Helper: get intensity multiplier for any 0-100 value
// Falls back to INTENSITY_VALUES for exact presets, otherwise linearly maps
function getIntensityMultiplier(zone) {
    if (zone.customSpec != null) {
        return { spec: zone.customSpec, paint: zone.customPaint, bright: zone.customBright };
    }
    const preset = INTENSITY_VALUES[zone.intensity];
    if (preset) return preset;
    // Fallback: linear 0-100 → 0.0-1.0
    const pct = (parseInt(zone.intensity) || 100) / 100;
    return { spec: pct, paint: pct, bright: pct };
}

function setCustomIntensity(index, param, value) {
    pushZoneUndo('Set intensity', true);
    const z = zones[index];
    const v = parseFloat(value);
    // Ensure we're in custom mode
    if (z.customSpec == null) {
        const vals = INTENSITY_VALUES[z.intensity] || INTENSITY_VALUES["100"];
        z.customSpec = vals.spec;
        z.customPaint = vals.paint;
        z.customBright = vals.bright;
    }
    if (param === 'spec') z.customSpec = v;
    else if (param === 'paint') z.customPaint = v;
    else if (param === 'bright') z.customBright = v;
    // Update value display (check detail panel first, then card)
    const el = document.getElementById(`detIntSpecVal${index}`) || document.getElementById(`intSpecVal${index}`);
    if (el) el.textContent = z.customSpec.toFixed(2);
    const el2 = document.getElementById(`detIntPaintVal${index}`) || document.getElementById(`intPaintVal${index}`);
    if (el2) el2.textContent = z.customPaint.toFixed(2);
    const el3 = document.getElementById(`detIntBrightVal${index}`) || document.getElementById(`intBrightVal${index}`);
    if (el3) el3.textContent = z.customBright.toFixed(3);
    triggerPreviewRender();
}

function toggleIntensitySliders(index) {
    // Check detail panel first, then card
    const panel = document.getElementById(`detIntSliders${index}`) || document.getElementById(`intSliders${index}`);
    const arrow = document.getElementById(`detIntArrow${index}`) || document.getElementById(`intArrow${index}`);
    if (panel) {
        panel.classList.toggle('open');
        if (arrow) arrow.classList.toggle('open');
    }
}

// Track recently used finishes
// 2026-04-18 MARATHON bug #39 (HIGH): pre-fix, a corrupt localStorage
// value (from extension, crash, or dev-tools edit) caused JSON.parse to
// throw DURING script evaluation, before any function was defined —
// every downstream helper became undefined and the app wouldn't boot.
// Safe parse with empty fallback.
var _recentFinishes = (function () {
    try { return JSON.parse(localStorage.getItem('spb_recent_finishes') || '[]') || []; }
    catch (e) { console.warn('[SPB] corrupt spb_recent_finishes, starting empty'); return []; }
})();
function _trackRecentFinish(id) {
    _recentFinishes = _recentFinishes.filter(f => f !== id);
    _recentFinishes.unshift(id);
    if (_recentFinishes.length > 12) _recentFinishes.pop();
    localStorage.setItem('spb_recent_finishes', JSON.stringify(_recentFinishes));
}

// -- Categories where ordinary BASE picks keep "Use source paint" by default.
// Shipping Specials / Monolithics bypass this list: they default Base Color to
// "From special" using the same finish ID, so a ColorShoxx/Paradigm/etc. pick
// visibly owns its color immediately without flattening the paint_fn to a swatch.
const _SPB_NO_AUTO_COLOR_GROUPS = new Set([
    'Foundation',
    // 2026-04-22 painter-reported state-mutation bug: f_* bases appear
    // in BOTH 'Foundation' and 'Reference Foundations'. The inverse-
    // lookup at _spbGetBaseGroup used to pick the LAST iterated group
    // (see fix there), so f_metallic/f_pearl/etc. ended up labelled
    // 'Reference Foundations' and escaped this set — triggering
    // auto-color and painting the base's swatch (e.g. pearl-gray)
    // over the painter's picked colors. Adding the group here closes
    // the hole as a belt-and-suspenders in case the inverse-lookup
    // fix ever drifts.
    'Reference Foundations',
    '★ Enhanced Foundation', 'Enhanced Foundation',
    'Candy & Pearl', 'Candy and Pearl',
    'Ceramic & Glass', 'Ceramic and Glass',
    'Chrome & Mirror', 'Chrome and Mirror',
    'Exotic Metal',
    'Extreme & Experimental', 'Extreme and Experimental',
    'Industrial & Tactical', 'Industrial and Tactical',
    'Metallic Standard',
    'OEM Automotive',
    'Premium Luxury',
    'Racing Heritage',
    'Satin & Wrap', 'Satin and Wrap',
    'Weathered & Aged', 'Weathered and Aged',
    'Carbon & Composite',  // Carbon fibers are also material-not-color
    // Rich paint_fn groups should never be replaced by a flat swatch. If one
    // of these IDs is also in SPECIAL_GROUPS, the special-first default below
    // promotes it to baseColorMode='special' instead of a solid-color wash.
    'Iridescent Insects',
    'PARADIGM',
    'Textile-Inspired',
    'Stone & Mineral',
    'Paint Technique',
]);

// Lazy-built inverse lookup: base id → group name
let _SPB_BASE_GROUP_LOOKUP = null;
function _spbGetBaseGroup(baseId) {
    if (!_SPB_BASE_GROUP_LOOKUP) {
        _SPB_BASE_GROUP_LOOKUP = {};
        if (typeof BASE_GROUPS !== 'undefined') {
            // 2026-04-22 painter-reported state-mutation bug fix.
            //
            // Bug: many bases appear in multiple groups. f_metallic /
            // f_pearl / etc. live in BOTH 'Foundation' AND 'Reference
            // Foundations'. The previous build here OVERWROTE lookup
            // entries on every iteration, so the LAST-iterated group
            // won (JS object-key iteration order = insertion order,
            // and 'Reference Foundations' was inserted after 'Foundation').
            // That caused _spbShouldAutoFillBaseColor to consult the
            // wrong group ('Reference Foundations' was not in
            // _SPB_NO_AUTO_COLOR_GROUPS), which flipped the zone's
            // baseColorMode to 'solid' and painted the base's swatch
            // (pearl-grey, etc.) over the painter's paint.
            //
            // Fix: prefer the FIRST group that contains the id. That
            // matches the order the groups are declared in
            // paint-booth-0-finish-data.js BASE_GROUPS, so the
            // authoritative "primary" group wins. Foundation comes
            // first in that file, so all f_* bases correctly resolve
            // to 'Foundation' now.
            for (const groupName in BASE_GROUPS) {
                const list = BASE_GROUPS[groupName] || [];
                for (const id of list) {
                    if (!(id in _SPB_BASE_GROUP_LOOKUP)) {
                        _SPB_BASE_GROUP_LOOKUP[id] = groupName;
                    }
                }
            }
        }
    }
    return _SPB_BASE_GROUP_LOOKUP[baseId] || null;
}

function _spbNormalizeFinishId(id) {
    if (!id || typeof id !== 'string') return '';
    return id.replace(/^mono:/, '');
}

function _spbIsShippingSpecialLikeFinishId(id) {
    const raw = _spbNormalizeFinishId(id);
    if (!raw) return false;
    if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS) && MONOLITHICS.some(m => m && m.id === raw)) {
        return true;
    }
    if (typeof SPECIAL_GROUPS !== 'undefined' && SPECIAL_GROUPS) {
        for (const groupName in SPECIAL_GROUPS) {
            const ids = SPECIAL_GROUPS[groupName];
            if (Array.isArray(ids) && ids.includes(raw)) return true;
        }
    }
    return false;
}

function _spbFindFinishDisplay(id) {
    const raw = _spbNormalizeFinishId(id);
    if (!raw) return null;
    const bases = (typeof BASES !== 'undefined' && Array.isArray(BASES)) ? BASES : [];
    const monos = (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) ? MONOLITHICS : [];
    return monos.find(m => m && m.id === raw) || bases.find(b => b && b.id === raw) || null;
}

function _spbExtractSwatchHex(swatch, fallback) {
    const fb = /^#[0-9a-fA-F]{6}$/.test(fallback || '') ? fallback : '#ffffff';
    if (typeof swatch !== 'string') return fb;
    const six = swatch.match(/#[0-9a-fA-F]{6}\b/);
    if (six) return six[0];
    const three = swatch.match(/#[0-9a-fA-F]{3}\b/);
    if (three) return '#' + three[0].slice(1).split('').map(ch => ch + ch).join('');
    return fb;
}

function _spbDefaultBaseColorToFinish(zone, finishId) {
    if (!zone) return;
    const raw = _spbNormalizeFinishId(finishId);
    if (!raw) return;
    const display = _spbFindFinishDisplay(raw);
    zone.baseColorMode = 'special';
    zone.baseColorSource = 'mono:' + raw;
    zone.baseColor = _spbExtractSwatchHex(display && display.swatch, zone.baseColor || '#ffffff');
    if (zone.baseColorStrength == null) zone.baseColorStrength = 1;
    zone._autoBaseColorFill = true;
}

// Returns true if this ordinary base should auto-set the zone color. In the
// current UX this is intentionally conservative: regular bases stay source-
// driven; Specials are handled by _spbDefaultBaseColorToFinish above.
function _spbShouldAutoFillBaseColor(baseId) {
    if (_spbIsShippingSpecialLikeFinishId(baseId)) return true;
    return false;
}

function _spbApplyPickedMonolithicToZone(zone, monoId) {
    if (!zone) return;
    const raw = _spbNormalizeFinishId(monoId);
    zone.finish = raw || null;
    zone.base = null;
    if (!zone.pattern) zone.pattern = 'none';
    zone._scopedBrushAutoBaseColor = false;
    if (raw && _spbIsShippingSpecialLikeFinishId(raw)) {
        _spbDefaultBaseColorToFinish(zone, raw);
    } else if (zone._autoBaseColorFill) {
        zone.baseColorMode = 'source';
        zone.baseColorSource = null;
        zone._autoBaseColorFill = false;
    }
}

function _spbApplyPickedBaseToZone(zone, baseId) {
    if (!zone) return;
    zone.base = baseId || null;
    zone.finish = null;
    if (!zone.pattern) zone.pattern = 'none';
    zone._scopedBrushAutoBaseColor = false;
    const base = (typeof BASES !== 'undefined' && Array.isArray(BASES))
        ? BASES.find(b => b.id === baseId)
        : null;
    if (baseId && _spbIsShippingSpecialLikeFinishId(baseId)) {
        _spbDefaultBaseColorToFinish(zone, baseId);
        return;
    }
    const shouldAutoFill = !!(base && base.swatch && _spbShouldAutoFillBaseColor(baseId));
    if (shouldAutoFill) {
        zone.baseColor = base.swatch;
        zone.baseColorMode = 'solid';
        zone.baseColorSource = null;
        zone._autoBaseColorFill = true;
        return;
    }
    // Only unwind the tint if it came from auto-fill. Manual solid/special/
    // gradient base-color choices should survive neutral-material swaps.
    if (zone._autoBaseColorFill) {
        zone.baseColorMode = 'source';
        zone.baseColorSource = null;
        zone._autoBaseColorFill = false;
    }
}

// FAMILY INTELLIGENCE pass (2026-04-18): one-time albedo compensation hint.
// Painters intuitively pick silver/grey for chrome but iRacing's PBR pipeline
// requires near-WHITE albedo for metallic finishes (R=255 metallic + dark
// albedo = nearly black render). This is documented in the iRacing PBR docs
// but every new painter trips on it. Show a one-shot toast when chrome /
// mirror / dark_chrome is assigned to a zone whose effective color is dark.
// localStorage gate: painter sees this AT MOST 3 times across sessions.
const _ALBEDO_HINT_KEY = '_spb_albedo_hint_shown_count';
const _ALBEDO_HINT_MAX_SHOWS = 3;
function _hexLooksDark(hex) {
    if (!hex || typeof hex !== 'string' || hex.length < 7) return false;
    try {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        // Perceptual luminance threshold: anything below ~140/255 will look
        // significantly darker than expected when chrome PBR multiplies it.
        const lum = 0.299 * r + 0.587 * g + 0.114 * b;
        return lum < 140;
    } catch (_) { return false; }
}
function _finishNeedsAlbedoHint(finishId) {
    if (!finishId || typeof finishId !== 'string') return false;
    try {
        if (typeof isChromeLikeBase === 'function') return !!isChromeLikeBase(finishId);
        // Fallback if finish-data helper is unavailable for some reason.
        if (typeof getBaseMetadata === 'function') {
            const meta = getBaseMetadata(finishId);
            if (meta && (meta.family === 'chrome' || meta.family === 'satin_chrome')) return true;
        }
        const base = (typeof BASES !== 'undefined' && Array.isArray(BASES)) ? BASES.find(b => b.id === finishId) : null;
        const hay = `${finishId} ${(base && base.name) || ''} ${(base && base.desc) || ''}`.toLowerCase();
        return /\b(chrome|mirror)\b/.test(hay);
    } catch (_) {
        return false;
    }
}
function _maybeShowAlbedoHint(finishId, zone) {
    if (typeof localStorage === 'undefined' || typeof showToast !== 'function') return;
    if (!_finishNeedsAlbedoHint(finishId)) return;
    // Effective color: zone.color (named iRacing slot) trumps zone.baseColor.
    // We only act on a pickable hex; named-slot colors get a separate softer hint.
    const hex = (zone && (zone.baseColor || (typeof zone.color === 'string' && zone.color.startsWith('#') ? zone.color : null))) || null;
    if (!hex) return;
    if (!_hexLooksDark(hex)) return;
    let shown = 0;
    try { shown = parseInt(localStorage.getItem(_ALBEDO_HINT_KEY) || '0', 10) || 0; } catch (_) {}
    if (shown >= _ALBEDO_HINT_MAX_SHOWS) return;
    try { localStorage.setItem(_ALBEDO_HINT_KEY, String(shown + 1)); } catch (_) {}
    showToast(
        'Chrome reads best on light/white albedo. Your color is dark — iRacing\'s PBR will render this nearly black. Try a near-white base for true mirror look.',
        'warn'
    );
}
if (typeof window !== 'undefined') {
    window._maybeShowAlbedoHint = _maybeShowAlbedoHint;
    window._hexLooksDark = _hexLooksDark;
    window._finishNeedsAlbedoHint = _finishNeedsAlbedoHint;
}

function assignFinishToSelected(finishId) {
    if (selectedZoneIndex >= 0 && selectedZoneIndex < zones.length) {
        _trackRecentFinish(finishId);
        pushZoneUndo('Assign finish: ' + finishId);
        const zone = zones[selectedZoneIndex];
        // Check if it's a base, pattern, or monolithic
        const base = BASES.find(b => b.id === finishId);
        const pattern = PATTERNS.find(p => p.id === finishId);
        const mono = MONOLITHICS.find(m => m.id === finishId);

        if (base) {
            _spbApplyPickedBaseToZone(zone, finishId);
            renderZones();
            triggerPreviewRender();
            showToast(`Base: ${base.name} => ${zone.name}`);
            // FAMILY INTELLIGENCE pass (2026-04-18): albedo compensation hint.
            // Source: Flair painter-pain #2 (iRacing PBR docs explicitly warn
            // "metallic albedo colors need to be much lighter than normal --
            // chrome pixels should be white"). Painters intuitively pick
            // silver/grey for chrome and get black-looking cars in iRacing.
            // SPB now warns when the painter just assigned a chrome/mirror
            // finish to a zone whose color reads dark.
            try { _maybeShowAlbedoHint(finishId, zone); } catch (_) {}
        } else if (pattern) {
            // If a monolithic is already set, ADD the pattern on top (don't clear the monolithic)
            if (zone.finish) {
                zone.pattern = finishId;
                // Keep zone.finish intact - pattern overlays on monolithic
                renderZones();
                triggerPreviewRender();
                const monoName = MONOLITHICS.find(m => m.id === zone.finish)?.name || zone.finish;
                showToast(`Pattern: ${pattern.name} over ${monoName} => ${zone.name}`);
            } else {
                if (!zone.base) zone.base = 'gloss'; // Default base if none set
                zone.pattern = finishId;
                renderZones();
                triggerPreviewRender();
                showToast(`Pattern: ${pattern.name} => ${zone.name}`);
            }
        } else if (mono) {
            _spbApplyPickedMonolithicToZone(zone, finishId);
            // Keep existing pattern if one is set (pattern can overlay on monolithic)
            // zone.pattern is preserved - user can keep or remove it
            renderZones();
            triggerPreviewRender();
            const patLabel = (zone.pattern && zone.pattern !== 'none') ? ` (keeping ${PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern} overlay)` : '';
            showToast(`Special: ${mono.name}${patLabel} => ${zone.name}`);
        } else {
            // Legacy fallback
            zone.finish = finishId;
            zone.base = null;
            zone.pattern = null;
            renderZones();
            triggerPreviewRender();
            showToast(`Assigned ${finishId} to ${zone.name}`);
        }
    }
}


// ===== FINISH FAVORITES (localStorage) =====
// 2026-04-18 MARATHON bug #39 same class: safe parse.
let _favoriteFinishes = new Set((function () {
    try { return JSON.parse(localStorage.getItem('shokker_favorites') || '[]') || []; }
    catch (e) { console.warn('[SPB] corrupt shokker_favorites, starting empty'); return []; }
})());
let _showFavoritesOnly = false;

function toggleFavorite(finishId, event) {
    if (event) { event.stopPropagation(); event.preventDefault(); }
    if (_favoriteFinishes.has(finishId)) {
        _favoriteFinishes.delete(finishId);
    } else {
        _favoriteFinishes.add(finishId);
    }
    localStorage.setItem('shokker_favorites', JSON.stringify([..._favoriteFinishes]));
    renderFinishLibrary();
}

function isFavorite(finishId) {
    return _favoriteFinishes.has(finishId);
}

function toggleFavoritesOnly() {
    _showFavoritesOnly = !_showFavoritesOnly;
    const btn = document.getElementById('btnFavoritesOnly');
    if (btn) {
        btn.textContent = _showFavoritesOnly ? '★' : '☆';
        btn.style.color = _showFavoritesOnly ? '#ffaa00' : '';
        btn.style.borderColor = _showFavoritesOnly ? '#ffaa00' : '';
    }
    renderFinishLibrary();
}

// ===== FINISH LIBRARY RENDERING (v3.0 tabbed) =====
let activeLibraryTab = 'bases'; // 'bases' | 'patterns' | 'specials'

let activeLibraryGroup = null; // legacy compat
const _expandedGroups = new Set(); // tracks which accordion groups are open
let _lastLibraryTabForDefaults = null;

function toggleLibraryGroup(groupName) {
    if (_expandedGroups.has(groupName)) {
        _expandedGroups.delete(groupName);
    } else {
        _expandedGroups.add(groupName);
    }
    renderFinishLibrary();
}

function expandAllLibraryGroups() {
    const GROUP_MAPS = { bases: BASE_GROUPS, patterns: PATTERN_GROUPS, specials: SPECIAL_GROUPS };
    const groupMap = GROUP_MAPS[activeLibraryTab] || {};
    Object.keys(groupMap).forEach(gn => _expandedGroups.add(gn));
    renderFinishLibrary();
}

function collapseAllLibraryGroups() {
    _expandedGroups.clear();
    renderFinishLibrary();
}

// Registry status cache — loaded once on boot
var _registeredFinishes = null;
function _loadRegistryStatus() {
    if (_registeredFinishes) return;
    fetch(ShokkerAPI.baseUrl + '/api/finish-registry-status')
        .then(r => r.json())
        .then(data => {
            if (data.registered) {
                _registeredFinishes = new Set(data.registered);
                console.log(`[Registry] ${_registeredFinishes.size} registered finishes loaded`);
            }
        })
        .catch(() => { _registeredFinishes = null; });
}
// Auto-load on first renderFinishLibrary call
var _registryLoadAttempted = false;

function _renderFinishItem(item, type) {
    if (!_registryLoadAttempted) { _registryLoadAttempted = true; _loadRegistryStatus(); }
    const isRegistered = !_registeredFinishes || _registeredFinishes.has(item.id);
    const isFav = isFavorite(item.id);
    const starIcon = isFav ? '★' : '☆';
    const starColor = isFav ? 'color:#ffaa00;' : 'color:var(--text-dim);';
    const swatchUrl = getSwatchUrl(item.id, '888888');
    const zoneCtx = _getFinishLibraryZoneContext();
    const baseMeta = type === 'base' && typeof getBaseMetadata === 'function' ? getBaseMetadata(item.id) : null;
    const patternMeta = type === 'pattern' && typeof getPatternMetadata === 'function' ? getPatternMetadata(item.id) : null;
    const familyId = baseMeta && typeof getBaseFamily === 'function' ? getBaseFamily(item.id) : '';
    const familyLabel = familyId && typeof FAMILY_DISPLAY_NAMES !== 'undefined' ? (FAMILY_DISPLAY_NAMES[familyId] || familyId) : '';
    const sponsorSafe = baseMeta && typeof isBaseSponsorSafe === 'function' ? isBaseSponsorSafe(item.id) : true;
    const isReferenceBase = type === 'base' && /^(f_|enh_)/.test(item.id || '');
    const isEnhancedBase = type === 'base' && /^enh_/.test(item.id || '');
    const qualityFlags = typeof getFinishQualityFlags === 'function' ? getFinishQualityFlags(item.id) : [];
    const isRecommendedPattern = type === 'pattern'
        && zoneCtx
        && zoneCtx.base
        && typeof isRecommendedCombo === 'function'
        && isRecommendedCombo(zoneCtx.base.id, item.id);
    const inlineChips = [];
    if (type === 'base' && familyLabel) {
        inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid #333; color:#9ad9ff; background:#091722;">${familyLabel}</span>`);
        if (baseMeta && baseMeta.tier) {
            const tierTone = baseMeta.tier === 'hero'
                ? { border: '#7a6214', color: '#ffd86a', bg: 'rgba(255,215,0,0.08)' }
                : baseMeta.tier === 'premium'
                    ? { border: '#5a3c83', color: '#c9a7ff', bg: 'rgba(165,102,255,0.08)' }
                    : { border: '#334', color: '#d7d7e8', bg: 'rgba(255,255,255,0.03)' };
            inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid ${tierTone.border}; color:${tierTone.color}; background:${tierTone.bg};">${String(baseMeta.tier).toUpperCase()}</span>`);
        }
        if (baseMeta && typeof baseMeta.aggression === 'number') {
            const aggressionLabel = baseMeta.aggression >= 4
                ? 'Wild'
                : baseMeta.aggression <= 1
                    ? 'Subtle'
                    : baseMeta.aggression === 2
                        ? 'Balanced'
                        : 'Bold';
            const aggressionTone = baseMeta.aggression >= 4
                ? { border: '#7a2f14', color: '#ffb37d', bg: 'rgba(255,128,64,0.08)' }
                : baseMeta.aggression <= 1
                    ? { border: '#245d35', color: '#7ae29c', bg: 'rgba(0,255,136,0.06)' }
                    : { border: '#3f4b6e', color: '#c6d6ff', bg: 'rgba(96,128,255,0.08)' };
            inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid ${aggressionTone.border}; color:${aggressionTone.color}; background:${aggressionTone.bg};">${aggressionLabel}</span>`);
        }
        inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid ${sponsorSafe ? '#245d35' : '#6b4922'}; color:${sponsorSafe ? '#7ae29c' : '#ffbf7d'}; background:${sponsorSafe ? 'rgba(0,255,136,0.06)' : 'rgba(255,170,68,0.06)'};">${sponsorSafe ? 'Sponsor Safe' : 'Sponsor Caution'}</span>`);
        if (baseMeta && Array.isArray(baseMeta.best_with) && baseMeta.best_with.length > 0) {
            const bestWithId = baseMeta.best_with.find(function(id) { return id && id !== 'none'; });
            if (bestWithId) {
                const bestWithPattern = (typeof PATTERNS !== 'undefined' && Array.isArray(PATTERNS))
                    ? PATTERNS.find(function(pattern) { return pattern.id === bestWithId; })
                    : null;
                if (bestWithPattern) {
                    inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid #2f4b67; color:#9fd1ff; background:rgba(64,128,255,0.08);">Best with ${bestWithPattern.name}</span>`);
                }
            }
        }
        if (baseMeta && Array.isArray(baseMeta.similar_to) && baseMeta.similar_to.length > 0 && typeof BASES !== 'undefined' && Array.isArray(BASES)) {
            const similarId = baseMeta.similar_to.find(function(id) { return id && id !== item.id; });
            const similarBase = similarId ? BASES.find(function(base) { return base.id === similarId; }) : null;
            if (similarBase) {
                inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid #4a4a68; color:#d6d6f7; background:rgba(160,160,255,0.05);">Similar to ${similarBase.name}</span>`);
            }
        }
        if (isReferenceBase) {
            inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid #555; color:#c7c7c7; background:rgba(255,255,255,0.03);">${isEnhancedBase ? 'Enhanced Lab' : 'Reference'}</span>`);
        }
    }
    if (type === 'pattern' && patternMeta) {
        if (isRecommendedPattern) {
            inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid #7a6214; color:#ffd86a; background:rgba(255,215,0,0.08);">Recommended</span>`);
        }
        if (patternMeta.readability) {
            const readabilityTone = patternMeta.readability === 'good'
                ? { border: '#245d35', color: '#7ae29c', bg: 'rgba(0,255,136,0.06)' }
                : patternMeta.readability === 'fair'
                    ? { border: '#5f5f23', color: '#ece58c', bg: 'rgba(255,235,59,0.06)' }
                    : { border: '#6b2b2b', color: '#ff9f9f', bg: 'rgba(255,82,82,0.06)' };
            const readabilityLabel = patternMeta.readability === 'good'
                ? 'Text Friendly'
                : patternMeta.readability === 'fair'
                    ? 'Medium Readability'
                    : 'Busy / Low Readability';
            inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid ${readabilityTone.border}; color:${readabilityTone.color}; background:${readabilityTone.bg};">${readabilityLabel}</span>`);
        }
    }
    if ((type === 'base' || type === 'mono') && qualityFlags.length > 0) {
        const qualityChips = {
            broken: { label: 'Audit: Broken', border: '#7a2b2b', color: '#ff9f9f', bg: 'rgba(255,82,82,0.08)' },
            ggx_risk: { label: 'Audit: GGX Risk', border: '#7a5a14', color: '#ffd36a', bg: 'rgba(255,193,7,0.08)' },
            spec_flat: { label: 'Audit: Flat Spec', border: '#4b4b4b', color: '#d8d8d8', bg: 'rgba(255,255,255,0.05)' },
            slow: { label: 'Audit: Slow', border: '#5f2f83', color: '#d5a7ff', bg: 'rgba(165,102,255,0.08)' },
        };
        qualityFlags.forEach(function(flag) {
            const chip = qualityChips[flag];
            if (!chip) return;
            inlineChips.push(`<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid ${chip.border}; color:${chip.color}; background:${chip.bg};">${chip.label}</span>`);
        });
    }
    const swatchHtml = swatchUrl
        ? `<img class="finish-swatch-canvas" src="${swatchUrl}" loading="eager"
                       style="width:40px;height:40px;border-radius:4px;object-fit:cover;flex-shrink:0;"
                       onerror="this.style.background='${item.swatch || '#444'}';this.removeAttribute('src')">`
        : `<div class="finish-swatch-canvas" style="width:40px;height:40px;border-radius:4px;background:${item.swatch || '#444'};flex-shrink:0;"></div>`;
    return `
        <div class="finish-item" onclick="assignFinishToSelected('${item.id}')"
             onmouseenter="showFinishPopup(event, '${item.id}')"
             onmouseleave="hideFinishPopup()"
             data-name="${escapeHtml(item.name).toLowerCase()}"
             data-desc="${escapeHtml(item.desc).toLowerCase()}"
             data-id="${item.id}">
            ${swatchHtml}
            <div class="finish-item-info">
                <div class="finish-item-name">${item.name}${!isRegistered ? ' <span style="font-size:7px;color:#ff8800;border:1px solid #ff8800;border-radius:2px;padding:0 2px;vertical-align:middle;" title="Preview — this finish uses a generic render path">PREVIEW</span>' : ''}</div>
                <div class="finish-item-desc">${item.desc}</div>
                ${inlineChips.length > 0 ? `<div class="finish-item-chips" style="display:flex; flex-wrap:wrap; gap:3px; margin-top:3px;">${inlineChips.join('')}</div>` : ''}
            </div>
            <span onclick="toggleFavorite('${item.id}', event)" title="${isFav ? 'Remove from favorites' : 'Add to favorites'}" style="cursor:pointer; font-size:14px; ${starColor} padding:0 4px; flex-shrink:0; transition:color 0.15s;">${starIcon}</span>
            <span class="finish-item-assign">${type === 'base' ? 'Set Base' : type === 'pattern' ? 'Set Pattern' : 'Assign'}</span>
        </div>`;
}

var _libraryBrowseMode = 'all'; // 'quick', 'materials', 'specials', 'events', 'all', 'advanced'
var _libraryBaseFamilyFilter = 'all';
var _libraryBaseQualityFilter = 'all';
var _librarySpecialQualityFilter = 'all';
var _libraryFeaturedCollectionFilter = 'all';
var _libraryPatternFilter = 'all';
// FIVE-HOUR SHIFT Wins E1 + F1: ALL 16 SPEC_FLAT (B) identity-violation
// candidates from Animal's TWENTY WINS recon are now FIXED IN ENGINE.
// 7 fixed via spec-function rewrites (A1-A7 — liquid_titanium, platinum,
// obsidian, alubeam, electroplated_gold, electric_ice, antique_chrome).
// 9 fixed via dispatcher re-routing (F1 — foundation entries whose names
// promise material character now route to _spec_metallic_flake /
// _spec_matte_rough / _spec_weathered instead of _spec_foundation_flat).
//
// Result: the chip table is empty. The browser no longer surfaces ANY
// audit chip — because the fresh audit (now 0 broken / 0 slow / 0 ggx /
// 0 spec_flat after F1) has nothing to flag. This matches reality.
//
// If a future audit surfaces NEW issues, populate this table with the
// failing ids and the chip rendering machinery will surface them again.
const FINISH_BROWSER_QUALITY_FLAGS = {
    // Empty by design after FIVE-HOUR SHIFT engine repairs. See:
    //   - audit_finish_quality.py SPEC_FLAT_ALLOWED_BY_DESIGN (Win #16)
    //   - shokker_engine_v2.py _SPEC_FN_EXPLICIT_WIN_F1 (Win F1)
    //   - engine/paint_v2/exotic_metal.py spec_liquid_titanium / spec_platinum (Wins A1, A2)
    //   - engine/paint_v2/ceramic_glass.py spec_obsidian_glass (Win A3)
    //   - engine/spec_paint.py spec_alubeam_base / spec_electroplated_gold_base (Wins A4, A5)
    //   - engine/paint_v2/metallic_flake.py spec_electric_ice (Win A6)
    //   - engine/paint_v2/chrome_mirror.py spec_antique_chrome (Win A7)
};
function getFinishQualityFlags(id) {
    return FINISH_BROWSER_QUALITY_FLAGS[id] ? FINISH_BROWSER_QUALITY_FLAGS[id].slice() : [];
}
const _LIBRARY_BASE_FAMILY_ORDER = [
    'chrome', 'satin_chrome', 'metallic', 'pearl', 'candy', 'gloss',
    'satin', 'matte', 'ceramic', 'weathered', 'brushed', 'vinyl',
    'carbon', 'industrial', 'optical', 'exotic'
];

function _getMetadata(id) {
    return (typeof FINISH_METADATA !== 'undefined' && FINISH_METADATA[id]) || null;
}

function _filterBasesByFamily(items) {
    if (_libraryBaseFamilyFilter === 'all') return items;
    return items.filter(function(item) {
        return (typeof getBaseFamily === 'function') && getBaseFamily(item.id) === _libraryBaseFamilyFilter;
    });
}

function _filterBasesByFeaturedCollection(items) {
    if (_libraryFeaturedCollectionFilter === 'all') return items;
    if (typeof FEATURED_COLLECTIONS === 'undefined' || !FEATURED_COLLECTIONS || !FEATURED_COLLECTIONS[_libraryFeaturedCollectionFilter]) {
        return items;
    }
    const allowed = new Set(FEATURED_COLLECTIONS[_libraryFeaturedCollectionFilter]);
    return items.filter(function(item) {
        const hasQualityFlags = (typeof getFinishQualityFlags === 'function') && getFinishQualityFlags(item.id).length > 0;
        return allowed.has(item.id) && !hasQualityFlags;
    });
}

function _filterBasesByQuality(items) {
    if (_libraryBaseQualityFilter === 'all') return items;
    return items.filter(function(item) {
        const meta = (typeof getBaseMetadata === 'function') ? getBaseMetadata(item.id) : {};
        const sponsorSafe = (typeof isBaseSponsorSafe === 'function') ? isBaseSponsorSafe(item.id) : true;
        const isReference = /^(f_|enh_)/.test(item.id || '');
        const qualityFlags = typeof getFinishQualityFlags === 'function' ? getFinishQualityFlags(item.id) : [];
        if (_libraryBaseQualityFilter === 'sponsor_safe') return sponsorSafe && !isReference;
        if (_libraryBaseQualityFilter === 'high_impact') {
            return !isReference && (!sponsorSafe || (meta && typeof meta.aggression === 'number' && meta.aggression >= 4));
        }
        if (_libraryBaseQualityFilter === 'reference_lab') return isReference;
        if (_libraryBaseQualityFilter === 'audit_flags') return qualityFlags.length > 0;
        return true;
    });
}

function _filterSpecialsByQuality(items) {
    if (_librarySpecialQualityFilter === 'all') return items;
    return items.filter(function(item) {
        const flags = typeof getFinishQualityFlags === 'function' ? getFinishQualityFlags(item.id) : [];
        if (_librarySpecialQualityFilter === 'audit_flags') return flags.length > 0;
        if (_librarySpecialQualityFilter === 'slow') return flags.indexOf('slow') >= 0;
        if (_librarySpecialQualityFilter === 'known_good') return flags.length === 0;
        return true;
    });
}

function _filterPatternsByGuidance(items, zoneCtx) {
    if (_libraryPatternFilter === 'all') return items;
    return items.filter(function(item) {
        const meta = typeof getPatternMetadata === 'function' ? getPatternMetadata(item.id) : {};
        if (_libraryPatternFilter === 'recommended') {
            return !!(zoneCtx && zoneCtx.base && typeof isRecommendedCombo === 'function' && isRecommendedCombo(zoneCtx.base.id, item.id));
        }
        if (_libraryPatternFilter === 'text_friendly') {
            return meta.readability === 'good';
        }
        if (_libraryPatternFilter.indexOf('style:') === 0) {
            return meta.style === _libraryPatternFilter.split(':', 2)[1];
        }
        return true;
    });
}

function _getFinishLibraryZoneContext() {
    if (typeof zones === 'undefined' || !Array.isArray(zones) || selectedZoneIndex < 0 || selectedZoneIndex >= zones.length) return null;
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.base) return null;
    const base = (typeof BASES !== 'undefined' && Array.isArray(BASES)) ? BASES.find(function(b) { return b.id === zone.base; }) : null;
    if (!base) return null;
    const meta = (typeof getBaseMetadata === 'function') ? getBaseMetadata(base.id) : {};
    const familyId = (typeof getBaseFamily === 'function') ? getBaseFamily(base.id) : (meta.family || 'other');
    const familyLabel = (typeof FAMILY_DISPLAY_NAMES !== 'undefined' && FAMILY_DISPLAY_NAMES[familyId]) || familyId || 'Other';
    const recommendedPatterns = (typeof getRecommendedPatterns === 'function')
        ? getRecommendedPatterns(base.id)
            .map(function(id) { return (typeof PATTERNS !== 'undefined' && Array.isArray(PATTERNS)) ? PATTERNS.find(function(p) { return p.id === id; }) : null; })
            .filter(Boolean)
            .slice(0, 6)
        : [];
    const currentPattern = zone.pattern && zone.pattern !== 'none' && typeof PATTERNS !== 'undefined' && Array.isArray(PATTERNS)
        ? PATTERNS.find(function(p) { return p.id === zone.pattern; }) || null
        : null;
    const currentPatternMeta = currentPattern && typeof getPatternMetadata === 'function'
        ? getPatternMetadata(currentPattern.id)
        : {};
    let similarBases = Array.isArray(meta.similar_to) ? meta.similar_to.slice() : [];
    if (similarBases.length === 0 && typeof getFamilyBases === 'function') {
        similarBases = getFamilyBases(base.id).filter(function(id) { return id !== base.id; });
    }
    similarBases = similarBases
        .map(function(id) { return (typeof BASES !== 'undefined' && Array.isArray(BASES)) ? BASES.find(function(b) { return b.id === id; }) : null; })
        .filter(Boolean)
        .slice(0, 6);
    return {
        zone: zone,
        base: base,
        meta: meta || {},
        familyId: familyId,
        familyLabel: familyLabel,
        sponsorSafe: (typeof isBaseSponsorSafe === 'function') ? isBaseSponsorSafe(base.id) : true,
        recommendedPatterns: recommendedPatterns,
        similarBases: similarBases,
        currentPattern: currentPattern,
        currentPatternMeta: currentPatternMeta,
        currentPatternRecommended: !!(currentPattern && typeof isRecommendedCombo === 'function' && isRecommendedCombo(base.id, currentPattern.id))
    };
}

function _filterByBrowseMode(items, tabId) {
    if (_libraryBrowseMode === 'all') return items;
    return items.filter(item => {
        const meta = _getMetadata(item.id);
        const hasQualityFlags = (typeof getFinishQualityFlags === 'function') && getFinishQualityFlags(item.id).length > 0;
        if (!meta) return _libraryBrowseMode === 'all';
        switch (_libraryBrowseMode) {
            case 'quick':
                // FAMILY INTELLIGENCE follow-up: bases need a truly curated
                // quick-start lane, not the old noisy meta.hero heuristic that
                // tagged ~100 finishes. Use HERO_BASES for bases; keep the
                // metadata path for patterns/specials.
                if (tabId === 'bases' && typeof HERO_BASES !== 'undefined' && Array.isArray(HERO_BASES) && HERO_BASES.length > 0) {
                    return HERO_BASES.some(function(hero) { return hero.id === item.id; })
                        && !hasQualityFlags;
                }
                return (meta.hero || (meta.featured && meta.readability >= 75)) && !hasQualityFlags;
            case 'materials': return meta.browserGroup === 'Materials' || meta.browserGroup === 'Utility';
            case 'specials': return meta.browserGroup === 'Specials';
            case 'events': return meta.browserGroup === 'Surface Events';
            case 'advanced': return meta.advanced || meta.browserGroup === 'Advanced';
            default: return true;
        }
    });
}

function _sortByMetadata(items) {
    return [...items].sort((a, b) => {
        const ma = _getMetadata(a.id), mb = _getMetadata(b.id);
        const aFlags = typeof getFinishQualityFlags === 'function' ? getFinishQualityFlags(a.id) : [];
        const bFlags = typeof getFinishQualityFlags === 'function' ? getFinishQualityFlags(b.id) : [];
        if (!!aFlags.length !== !!bFlags.length) return aFlags.length - bFlags.length;
        const pa = ma ? ma.sortPriority : 50, pb = mb ? mb.sortPriority : 50;
        return pb - pa; // Higher priority first
    });
}

function _sortPatternsForZoneContext(items, zoneCtx) {
    if (!zoneCtx || !zoneCtx.base) return items;
    const readabilityRank = { good: 0, fair: 1, poor: 2 };
    return [...items].sort(function(a, b) {
        const aRecommended = typeof isRecommendedCombo === 'function' && isRecommendedCombo(zoneCtx.base.id, a.id) ? 0 : 1;
        const bRecommended = typeof isRecommendedCombo === 'function' && isRecommendedCombo(zoneCtx.base.id, b.id) ? 0 : 1;
        if (aRecommended !== bRecommended) return aRecommended - bRecommended;
        const aMeta = typeof getPatternMetadata === 'function' ? getPatternMetadata(a.id) : {};
        const bMeta = typeof getPatternMetadata === 'function' ? getPatternMetadata(b.id) : {};
        const aReadability = Object.prototype.hasOwnProperty.call(readabilityRank, aMeta.readability) ? readabilityRank[aMeta.readability] : 3;
        const bReadability = Object.prototype.hasOwnProperty.call(readabilityRank, bMeta.readability) ? readabilityRank[bMeta.readability] : 3;
        if (aReadability !== bReadability) return aReadability - bReadability;
        return (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' });
    });
}

function renderFinishLibrary() {
    const container = document.getElementById('finishLibrary');
    const GROUP_MAPS = { bases: BASE_GROUPS, patterns: PATTERN_GROUPS, specials: SPECIAL_GROUPS };
    const _libraryZoneContext = _getFinishLibraryZoneContext();

    // Apply browse mode filtering
    const browseModeBases = _sortByMetadata(_filterByBrowseMode(BASES, 'bases'));
    const collectionBases = _filterBasesByFeaturedCollection(browseModeBases);
    const qualityBases = _filterBasesByQuality(collectionBases);
    const filteredBases = _filterBasesByFamily(qualityBases);
    const browseModePatterns = _sortPatternsForZoneContext(_sortByMetadata(_filterByBrowseMode(PATTERNS, 'patterns')), _libraryZoneContext);
    const filteredPatterns = _filterPatternsByGuidance(browseModePatterns, _libraryZoneContext);
    const browseModeMonos = _sortByMetadata(_filterByBrowseMode(MONOLITHICS, 'specials'));
    const filteredMonos = _filterSpecialsByQuality(browseModeMonos);

    const tabs = [
        { id: 'bases', label: `Bases (${filteredBases.length})`, items: filteredBases, type: 'base' },
        { id: 'patterns', label: `Patterns (${filteredPatterns.length})`, items: filteredPatterns, type: 'pattern' },
        { id: 'specials', label: `Specials (${filteredMonos.length})`, items: filteredMonos, type: 'mono' },
    ];

    // Browse mode selector (tier system)
    const modes = [
        { id: 'quick', label: 'Quick Start', color: '#00ff88', desc: 'Best picks, high confidence' },
        { id: 'materials', label: 'Materials', color: '#00e5ff', desc: 'Chrome, carbon, ceramic, pearl...' },
        { id: 'specials', label: 'Specials', color: '#ffd700', desc: 'Color shifts, prizm, micro-flake' },
        { id: 'events', label: 'Surface', color: '#ff8844', desc: 'Clearcoat, weathering, aging' },
        { id: 'all', label: 'All', color: '#aaa', desc: 'Full library' },
        { id: 'advanced', label: 'Adv', color: '#888', desc: 'Experimental & niche' },
    ];
    let html = `<div style="display:flex; gap:1px; margin-bottom:3px; flex-wrap:wrap;">
        ${modes.map(m => `<button onclick="_libraryBrowseMode='${m.id}'; renderFinishLibrary();"
            style="flex:1; min-width:40px; font-size:7px; padding:3px 2px; border:1px solid ${_libraryBrowseMode === m.id ? m.color : '#333'};
            color:${_libraryBrowseMode === m.id ? m.color : '#666'}; background:${_libraryBrowseMode === m.id ? m.color + '15' : 'transparent'};
            cursor:pointer; border-radius:3px; font-weight:${_libraryBrowseMode === m.id ? '700' : '400'};"
            title="${m.desc}">${m.label}</button>`).join('')}
    </div>`;

    // Main category tabs
    html += `<div style="display:flex; gap:2px; margin-bottom:4px;">
        ${tabs.map(t => `<button class="btn btn-sm${activeLibraryTab === t.id ? ' active' : ''}"
            onclick="activeLibraryTab='${t.id}'; renderFinishLibrary();"
            style="flex:1; font-size:10px; padding:4px 2px; ${activeLibraryTab === t.id ? 'background:var(--accent); color:#000; border-color:var(--accent);' : ''}"
        >${t.label}</button>`).join('')}
    </div>`;

    // Combo count
    const totalFiltered = filteredBases.length + filteredPatterns.length + filteredMonos.length;
    const totalAll = BASES.length + PATTERNS.length + MONOLITHICS.length;
    html += `<div style="text-align:center; font-size:8px; color:var(--text-dim); margin-bottom:3px;">
        ${_libraryBrowseMode === 'all' ? `${totalAll.toLocaleString()} finishes` : `${totalFiltered} of ${totalAll.toLocaleString()} finishes`}
    </div>`;

    // FAMILY INTELLIGENCE pass (2026-04-18): Material Quick-Pick row
    // Surfaces the curated HERO_BASES list with painter-friendly intent
    // labels. Pre-pass, HERO_BASES was defined in finish-data.js but no UI
    // surfaced it — painters had to scroll 100+ finishes (the legacy
    // 'quick' browse mode tags `meta.hero` on 100 finishes, defeating the
    // purpose). Market research (Trading Paints, Photoshop forums) flagged
    // "I don't know which finish is the chrome one" as the #1 painter pain.
    // Solution: a 12-tile painter-intent strip that one-click assigns.
    if (activeLibraryTab === 'bases'
            && typeof HERO_BASES !== 'undefined'
            && Array.isArray(HERO_BASES)
            && HERO_BASES.length > 0) {
        html += `<div class="material-quick-pick" style="margin-bottom:6px; padding:5px 4px; border:1px solid #00ff8830; background:rgba(0,255,136,0.04); border-radius:4px;">
            <div style="font-size:8px; color:#00ff88; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">
                MATERIAL QUICK-PICK <span style="color:var(--text-dim); font-weight:400;">— what kind of paint?</span>
            </div>
            <div style="display:grid; grid-template-columns:repeat(6,1fr); gap:2px;">`;
        HERO_BASES.forEach(hero => {
            const baseEntry = (typeof BASES !== 'undefined' && BASES.find) ? BASES.find(b => b.id === hero.id) : null;
            const swatchUrl = (typeof getSwatchUrl === 'function') ? getSwatchUrl(hero.id, '888888') : '';
            const swatchBg = baseEntry && baseEntry.swatch ? baseEntry.swatch : '#444';
            const safeHint = (hero.hint || '').replace(/"/g, '&quot;');
            html += `
                <div onclick="assignFinishToSelected('${hero.id}')"
                     title="${safeHint}"
                     style="cursor:pointer; padding:3px; border:1px solid #333; border-radius:3px; background:#1a1a1a; text-align:center; transition:all 0.15s;"
                     onmouseenter="this.style.borderColor='#00ff88'; this.style.background='rgba(0,255,136,0.08)';"
                     onmouseleave="this.style.borderColor='#333'; this.style.background='#1a1a1a';">
                    ${swatchUrl
                        ? `<img src="${swatchUrl}" loading="eager" style="width:100%; aspect-ratio:1; border-radius:2px; object-fit:cover; display:block; margin-bottom:2px;" onerror="this.style.background='${swatchBg}'; this.removeAttribute('src');">`
                        : `<div style="width:100%; aspect-ratio:1; border-radius:2px; background:${swatchBg}; margin-bottom:2px;"></div>`}
                    <div style="font-size:7px; color:#ddd; line-height:1.1; font-weight:600;">${hero.label}</div>
                </div>`;
        });
        html += `</div></div>`;
    }

    if (activeLibraryTab === 'bases'
            && typeof FEATURED_COLLECTIONS !== 'undefined'
            && FEATURED_COLLECTIONS) {
        const featuredEntries = Object.keys(FEATURED_COLLECTIONS).map(function(name) {
            const ids = Array.isArray(FEATURED_COLLECTIONS[name]) ? FEATURED_COLLECTIONS[name] : [];
            const count = browseModeBases.filter(function(base) {
                const hasQualityFlags = (typeof getFinishQualityFlags === 'function') && getFinishQualityFlags(base.id).length > 0;
                return ids.indexOf(base.id) >= 0 && !hasQualityFlags;
            }).length;
            return { name: name, count: count };
        }).filter(function(entry) { return entry.count > 0; });
        if (featuredEntries.length > 0) {
            html += `<div class="featured-collections-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #ffd70022; background:rgba(255,215,0,0.04); border-radius:4px;">
                <div style="font-size:8px; color:#ffd700; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">
                    FEATURED COLLECTIONS <span style="color:var(--text-dim); font-weight:400;">— curated finish lanes</span>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:3px;">`;
            const _renderFeaturedChip = function(name, count) {
                const active = _libraryFeaturedCollectionFilter === name;
                return `<button onclick="_libraryFeaturedCollectionFilter='${name}'; renderFinishLibrary();"
                    title="${name}"
                    style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid ${active ? '#ffd700' : '#333'}; color:${active ? '#ffd700' : '#bbb'}; background:${active ? 'rgba(255,215,0,0.10)' : '#1a1a1a'};">
                    ${name} <span style="color:${active ? '#ffe8a3' : '#777'};">${count}</span>
                </button>`;
            };
            html += _renderFeaturedChip('all', browseModeBases.length);
            featuredEntries.forEach(function(entry) {
                html += _renderFeaturedChip(entry.name, entry.count);
            });
            html += `</div></div>`;
        }
    }

    if (activeLibraryTab === 'bases') {
        const qualityCounts = {
            all: collectionBases.length,
            sponsor_safe: collectionBases.filter(function(base) {
                return (typeof isBaseSponsorSafe === 'function') ? isBaseSponsorSafe(base.id) && !/^(f_|enh_)/.test(base.id || '') : false;
            }).length,
            high_impact: collectionBases.filter(function(base) {
                const meta = (typeof getBaseMetadata === 'function') ? getBaseMetadata(base.id) : {};
                const sponsorSafe = (typeof isBaseSponsorSafe === 'function') ? isBaseSponsorSafe(base.id) : true;
                return !/^(f_|enh_)/.test(base.id || '') && (!sponsorSafe || (meta && typeof meta.aggression === 'number' && meta.aggression >= 4));
            }).length,
            reference_lab: collectionBases.filter(function(base) { return /^(f_|enh_)/.test(base.id || ''); }).length,
            audit_flags: collectionBases.filter(function(base) {
                return (typeof getFinishQualityFlags === 'function') ? getFinishQualityFlags(base.id).length > 0 : false;
            }).length,
        };
        const renderQualityChip = function(id, label, count, tone) {
            const active = _libraryBaseQualityFilter === id;
            return `<button onclick="_libraryBaseQualityFilter='${id}'; renderFinishLibrary();"
                title="${label}"
                style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid ${active ? tone : '#333'}; color:${active ? tone : '#bbb'}; background:${active ? tone + '18' : '#1a1a1a'};">
                ${label} <span style="color:${active ? '#fff' : '#777'};">${count}</span>
            </button>`;
        };
        html += `<div class="base-quality-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #8bd7ff22; background:rgba(139,215,255,0.04); border-radius:4px;">
            <div style="font-size:8px; color:#8bd7ff; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">
                QUALITY SIGNALS <span style="color:var(--text-dim); font-weight:400;">— separate practical paints from showcase or lab finishes</span>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:3px;">
                ${renderQualityChip('all', 'All', qualityCounts.all, '#8bd7ff')}
                ${renderQualityChip('sponsor_safe', 'Sponsor Safe', qualityCounts.sponsor_safe, '#7ae29c')}
                ${renderQualityChip('high_impact', 'High Impact', qualityCounts.high_impact, '#ffbf7d')}
                ${renderQualityChip('audit_flags', 'Audit Flags', qualityCounts.audit_flags, '#ff9f9f')}
                ${renderQualityChip('reference_lab', 'Reference / Lab', qualityCounts.reference_lab, '#c7c7c7')}
            </div>
        </div>`;
    }

    if (activeLibraryTab === 'specials') {
        const specialQualityCounts = {
            all: browseModeMonos.length,
            known_good: browseModeMonos.filter(function(item) {
                return (typeof getFinishQualityFlags === 'function') ? getFinishQualityFlags(item.id).length === 0 : true;
            }).length,
            audit_flags: browseModeMonos.filter(function(item) {
                return (typeof getFinishQualityFlags === 'function') ? getFinishQualityFlags(item.id).length > 0 : false;
            }).length,
            slow: browseModeMonos.filter(function(item) {
                return (typeof getFinishQualityFlags === 'function') ? getFinishQualityFlags(item.id).indexOf('slow') >= 0 : false;
            }).length,
        };
        const renderSpecialQualityChip = function(id, label, count, tone) {
            const active = _librarySpecialQualityFilter === id;
            return `<button onclick="_librarySpecialQualityFilter='${id}'; renderFinishLibrary();"
                title="${label}"
                style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid ${active ? tone : '#333'}; color:${active ? tone : '#bbb'}; background:${active ? tone + '18' : '#1a1a1a'};">
                ${label} <span style="color:${active ? '#fff' : '#777'};">${count}</span>
            </button>`;
        };
        html += `<div class="special-quality-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #ffcf7d22; background:rgba(255,207,125,0.04); border-radius:4px;">
            <div style="font-size:8px; color:#ffcf7d; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">
                SPECIALS HEALTH <span style="color:var(--text-dim); font-weight:400;">— surface slower or audit-flagged specials honestly</span>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:3px;">
                ${renderSpecialQualityChip('all', 'All', specialQualityCounts.all, '#ffcf7d')}
                ${renderSpecialQualityChip('known_good', 'Known Good', specialQualityCounts.known_good, '#7ae29c')}
                ${renderSpecialQualityChip('audit_flags', 'Audit Flags', specialQualityCounts.audit_flags, '#ff9f9f')}
                ${renderSpecialQualityChip('slow', 'Heavy / Slow', specialQualityCounts.slow, '#d5a7ff')}
            </div>
        </div>`;
    }

    if (activeLibraryTab === 'bases'
            && typeof getBaseFamily === 'function'
            && typeof FAMILY_DISPLAY_NAMES !== 'undefined') {
        const familiesPresent = {};
        qualityBases.forEach(function(base) {
            const fam = getBaseFamily(base.id);
            familiesPresent[fam] = (familiesPresent[fam] || 0) + 1;
        });
        const orderedFamilies = _LIBRARY_BASE_FAMILY_ORDER
            .filter(function(fam) { return familiesPresent[fam]; })
            .concat(Object.keys(familiesPresent).filter(function(fam) { return _LIBRARY_BASE_FAMILY_ORDER.indexOf(fam) < 0; }).sort());
        html += `<div class="finish-family-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #00e5ff22; background:rgba(0,229,255,0.04); border-radius:4px;">
            <div style="font-size:8px; color:#00e5ff; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">
                MATERIAL FAMILIES <span style="color:var(--text-dim); font-weight:400;">— filter by finish behavior</span>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:3px;">`;
        const _renderFamChip = function(fam, label, count) {
            const active = _libraryBaseFamilyFilter === fam;
            const chipTitle = label;
            return `<button onclick="_libraryBaseFamilyFilter='${fam}'; renderFinishLibrary();"
                title="${chipTitle}"
                style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid ${active ? '#00e5ff' : '#333'}; color:${active ? '#00e5ff' : '#bbb'}; background:${active ? 'rgba(0,229,255,0.10)' : '#1a1a1a'};">
                ${label} <span style="color:${active ? '#9ff4ff' : '#777'};">${count}</span>
            </button>`;
        };
        html += _renderFamChip('all', 'All', browseModeBases.length);
        orderedFamilies.forEach(function(fam) {
            html += _renderFamChip(fam, FAMILY_DISPLAY_NAMES[fam] || fam, familiesPresent[fam]);
        });
        html += `</div></div>`;
    }

    const activeTab = tabs.find(t => t.id === activeLibraryTab);
    if (!activeTab) { container.innerHTML = html; return; }
    const _activeItemOrder = new Map(activeTab.items.map(function(item, idx) { return [item.id, idx]; }));

    if (activeLibraryTab === 'bases' && _libraryZoneContext) {
        const tone = _libraryZoneContext.sponsorSafe ? '#6be28b' : '#ffb366';
        const similarHtml = _libraryZoneContext.similarBases.length > 0
            ? _libraryZoneContext.similarBases.map(function(base) {
                return `<button onclick="assignFinishToSelected('${base.id}')"
                    style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid #333; color:#ddd; background:#1a1a1a;"
                    title="${(base.desc || '').replace(/"/g, '&quot;')}">${base.name}</button>`;
            }).join('')
            : `<span style="font-size:8px; color:var(--text-dim);">No curated alternates yet</span>`;
        html += `<div class="finish-context-card" style="margin-bottom:6px; padding:6px; border:1px solid ${tone}33; background:rgba(255,255,255,0.02); border-radius:4px;">
            <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:4px;">
                <div style="font-size:9px; color:#ddd; font-weight:700;">CURRENT ZONE BASE: ${_libraryZoneContext.base.name}</div>
                <button onclick="_libraryBaseFamilyFilter='${_libraryZoneContext.familyId}'; renderFinishLibrary();"
                    style="font-size:8px; padding:2px 6px; border-radius:999px; cursor:pointer; border:1px solid ${tone}; color:${tone}; background:transparent;">${_libraryZoneContext.familyLabel}</button>
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; font-size:8px; color:var(--text-dim); margin-bottom:5px;">
                <span>Tier: <span style="color:#ddd;">${_libraryZoneContext.meta.tier || 'n/a'}</span></span>
                <span>Intensity: <span style="color:#ddd;">${_libraryZoneContext.meta.aggression || 'n/a'}/5</span></span>
                <span style="color:${tone};">${_libraryZoneContext.sponsorSafe ? 'Sponsor-safe' : 'High-impact / sponsor caution'}</span>
            </div>
            <div style="font-size:8px; color:var(--text-dim); margin-bottom:3px;">Try these similar finishes:</div>
            <div style="display:flex; flex-wrap:wrap; gap:4px;">${similarHtml}</div>
        </div>`;
    }

    if (activeLibraryTab === 'patterns') {
        const patternStyleCounts = {};
        let recommendedCount = 0;
        let textFriendlyCount = 0;
        browseModePatterns.forEach(function(pattern) {
            const meta = (typeof getPatternMetadata === 'function') ? getPatternMetadata(pattern.id) : {};
            if (meta.style) patternStyleCounts[meta.style] = (patternStyleCounts[meta.style] || 0) + 1;
            if (meta.readability === 'good') textFriendlyCount += 1;
            if (_libraryZoneContext && _libraryZoneContext.base && typeof isRecommendedCombo === 'function' && isRecommendedCombo(_libraryZoneContext.base.id, pattern.id)) {
                recommendedCount += 1;
            }
        });
        const styleKeys = Object.keys(patternStyleCounts).sort(function(a, b) {
            if (patternStyleCounts[b] !== patternStyleCounts[a]) return patternStyleCounts[b] - patternStyleCounts[a];
            return a.localeCompare(b);
        });
        const renderPatternChip = function(id, label, count) {
            const active = _libraryPatternFilter === id;
            return `<button onclick="_libraryPatternFilter='${id}'; renderFinishLibrary();"
                title="${label}"
                style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid ${active ? '#ffd700' : '#333'}; color:${active ? '#ffd700' : '#bbb'}; background:${active ? 'rgba(255,215,0,0.10)' : '#1a1a1a'};">
                ${label} <span style="color:${active ? '#ffe7a0' : '#777'};">${count}</span>
            </button>`;
        };
        html += `<div class="pattern-guidance-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #ffd70022; background:rgba(255,215,0,0.04); border-radius:4px;">
            <div style="font-size:8px; color:#ffd700; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">
                PATTERN FILTERS <span style="color:var(--text-dim); font-weight:400;">— guide by readability and fit</span>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:3px;">`;
        html += renderPatternChip('all', 'All', browseModePatterns.length);
        if (_libraryZoneContext && _libraryZoneContext.base) {
            html += renderPatternChip('recommended', 'Recommended', recommendedCount);
        }
        html += renderPatternChip('text_friendly', 'Text Friendly', textFriendlyCount);
        styleKeys.forEach(function(styleId) {
            html += renderPatternChip(`style:${styleId}`, styleId.replace(/_/g, ' '), patternStyleCounts[styleId]);
        });
        html += `</div></div>`;
    }

    if (activeLibraryTab === 'patterns' && _libraryZoneContext && _libraryZoneContext.currentPattern) {
        const currentPattern = _libraryZoneContext.currentPattern;
        const currentMeta = _libraryZoneContext.currentPatternMeta || {};
        const matchTone = _libraryZoneContext.currentPatternRecommended ? '#6be28b' : '#ffb366';
        const readabilityTone = currentMeta.readability === 'good'
            ? '#6be28b'
            : currentMeta.readability === 'fair'
                ? '#ece58c'
                : '#ff9f9f';
        html += `<div class="pattern-current-status" style="margin-bottom:6px; padding:6px; border:1px solid ${matchTone}33; background:rgba(255,255,255,0.02); border-radius:4px;">
            <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:4px;">
                <div style="font-size:9px; color:#ddd; font-weight:700;">CURRENT PATTERN: ${currentPattern.name}</div>
                <span style="font-size:8px; padding:2px 6px; border-radius:999px; border:1px solid ${matchTone}; color:${matchTone};">${_libraryZoneContext.currentPatternRecommended ? 'Recommended Match' : 'Try a Better Match'}</span>
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; font-size:8px; color:var(--text-dim);">
                <span>Readability: <span style="color:${readabilityTone};">${currentMeta.readability || 'unknown'}</span></span>
                <span>Style: <span style="color:#ddd;">${currentMeta.style || 'n/a'}</span></span>
                <span>Density: <span style="color:#ddd;">${currentMeta.density || 'n/a'}</span></span>
            </div>
        </div>`;
    }

    if (activeLibraryTab === 'patterns' && _libraryZoneContext && _libraryZoneContext.recommendedPatterns.length > 0) {
        const recHtml = _libraryZoneContext.recommendedPatterns.map(function(pattern) {
            const pmeta = (typeof getPatternMetadata === 'function') ? getPatternMetadata(pattern.id) : {};
            const readability = pmeta.readability ? ` • ${pmeta.readability} text` : '';
            return `<button onclick="assignFinishToSelected('${pattern.id}')"
                title="${(pattern.desc || '').replace(/"/g, '&quot;')}"
                style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid #333; color:#ddd; background:#1a1a1a;">
                ${pattern.name}${readability}
            </button>`;
        }).join('');
        html += `<div class="pattern-advisor" style="margin-bottom:6px; padding:6px; border:1px solid #ffd70033; background:rgba(255,215,0,0.04); border-radius:4px;">
            <div style="font-size:9px; color:#ffd700; font-weight:700; margin-bottom:4px;">PATTERN ADVISOR</div>
            <div style="font-size:8px; color:#ddd; margin-bottom:4px;">Recommended over <span style="color:#fff;">${_libraryZoneContext.base.name}</span>:</div>
            <div style="display:flex; flex-wrap:wrap; gap:4px;">${recHtml}</div>
        </div>`;
    }

    // Group accordion
    const groupMap = GROUP_MAPS[activeLibraryTab] || {};
    let groupNames = Object.keys(groupMap);
    // Deterministic group order:
    // - Bases: Foundation first, then alphabetical
    // - Patterns: Abstract & Experimental first, then alphabetical
    // - Specials: keep configured order from object / sections
    if (activeLibraryTab === 'bases') {
        const baseGroupOrder = { 'Foundation': 0, 'Reference Foundations': 98, '★ Enhanced Foundation': 99 };
        groupNames = groupNames.sort((a, b) => {
            const ao = Object.prototype.hasOwnProperty.call(baseGroupOrder, a) ? baseGroupOrder[a] : 99;
            const bo = Object.prototype.hasOwnProperty.call(baseGroupOrder, b) ? baseGroupOrder[b] : 99;
            if (ao !== bo) return ao - bo;
            return a.localeCompare(b);
        });
    } else if (activeLibraryTab === 'patterns') {
        groupNames = groupNames.sort((a, b) => a === 'Abstract & Experimental' ? -1 : b === 'Abstract & Experimental' ? 1 : a.localeCompare(b));
    }
    // Default expanded groups per tab when entering tab
    if (_lastLibraryTabForDefaults !== activeLibraryTab) {
        _expandedGroups.clear();
        if (activeLibraryTab === 'bases' && groupNames.includes('Foundation')) _expandedGroups.add('Foundation');
        if (activeLibraryTab === 'patterns' && groupNames.includes('Abstract & Experimental')) _expandedGroups.add('Abstract & Experimental');
        _lastLibraryTabForDefaults = activeLibraryTab;
    }

    // === FAVORITES GROUP (always at top if any exist for this tab) ===
    const allTabIds = new Set(activeTab.items.map(it => it.id));
    const favItems = activeTab.items.filter(it => _favoriteFinishes.has(it.id));
    if (favItems.length > 0 && !_showFavoritesOnly) {
        html += `<div class="finish-group-accordion" style="margin-bottom:4px;">
                <div style="display:flex; align-items:center; gap:6px; padding:5px 8px; border-radius:4px; border-left:3px solid #ffaa00; background:rgba(255,170,0,0.06);">
                    <span style="font-size:14px; color:#ffaa00;">★</span>
                    <span style="font-size:10px; font-weight:700; color:#ffaa00; flex:1;">Favorites</span>
                    <span style="font-size:9px; color:var(--text-dim);">${favItems.length}</span>
                </div>
                <div style="padding:2px 0 4px 0;">`;
        favItems.forEach(item => { html += _renderFinishItem(item, activeTab.type); });
        html += `</div></div>`;
    }

    // === RECENT GROUP (show recently used finishes) ===
    if (!_showFavoritesOnly && _recentFinishes.length > 0) {
        const recentItems = _recentFinishes
            .map(id => activeTab.items.find(it => it.id === id))
            .filter(Boolean);
        if (recentItems.length > 0) {
            html += `<div class="finish-group-accordion" style="margin-bottom:4px;">
                <div style="display:flex; align-items:center; gap:6px; padding:5px 8px; border-radius:4px; border-left:3px solid #00e5ff; background:rgba(0,229,255,0.04);">
                    <span style="font-size:12px; color:#00e5ff;">⏱</span>
                    <span style="font-size:10px; font-weight:700; color:#00e5ff; flex:1;">Recent</span>
                    <span style="font-size:9px; color:var(--text-dim);">${recentItems.length}</span>
                </div>
                <div style="padding:2px 0 4px 0;">`;
            recentItems.forEach(item => { html += _renderFinishItem(item, activeTab.type); });
            html += `</div></div>`;
        }
    }

    // If favorites-only mode, skip groups
    if (_showFavoritesOnly) {
        if (favItems.length === 0) {
            html += `<div style="text-align:center; padding:30px 10px; color:var(--text-dim); font-size:11px;">No favorites in this tab yet. Click the ☆ star on any finish to add it.</div>`;
        } else {
            favItems.forEach(item => { html += _renderFinishItem(item, activeTab.type); });
        }
        container.innerHTML = html;
        return;
    }

    if (activeTab.items.length === 0) {
        let resetHtml = '';
        if (activeLibraryTab === 'bases' && _libraryFeaturedCollectionFilter !== 'all') {
            resetHtml += `<button onclick="_libraryFeaturedCollectionFilter='all'; renderFinishLibrary();"
                style="font-size:8px; padding:4px 8px; border-radius:999px; cursor:pointer; border:1px solid #ffd700; color:#ffd700; background:transparent;">Clear Collection Filter</button>`;
        }
        if (activeLibraryTab === 'bases' && _libraryBaseQualityFilter !== 'all') {
            resetHtml += `<button onclick="_libraryBaseQualityFilter='all'; renderFinishLibrary();"
                style="font-size:8px; padding:4px 8px; border-radius:999px; cursor:pointer; border:1px solid #8bd7ff; color:#8bd7ff; background:transparent;">Clear Quality Filter</button>`;
        }
        if (activeLibraryTab === 'bases' && _libraryBaseFamilyFilter !== 'all') {
            resetHtml += `<button onclick="_libraryBaseFamilyFilter='all'; renderFinishLibrary();"
                style="font-size:8px; padding:4px 8px; border-radius:999px; cursor:pointer; border:1px solid #00e5ff; color:#00e5ff; background:transparent;">Clear Family Filter</button>`;
        }
        if (activeLibraryTab === 'patterns' && _libraryPatternFilter !== 'all') {
            resetHtml += `<button onclick="_libraryPatternFilter='all'; renderFinishLibrary();"
                style="font-size:8px; padding:4px 8px; border-radius:999px; cursor:pointer; border:1px solid #ffd700; color:#ffd700; background:transparent;">Clear Pattern Filter</button>`;
        }
        if (activeLibraryTab === 'specials' && _librarySpecialQualityFilter !== 'all') {
            resetHtml += `<button onclick="_librarySpecialQualityFilter='all'; renderFinishLibrary();"
                style="font-size:8px; padding:4px 8px; border-radius:999px; cursor:pointer; border:1px solid #ffcf7d; color:#ffcf7d; background:transparent;">Clear Special Filter</button>`;
        }
        if (_libraryBrowseMode !== 'all') {
            resetHtml += `<button onclick="_libraryBrowseMode='all'; renderFinishLibrary();"
                style="font-size:8px; padding:4px 8px; border-radius:999px; cursor:pointer; border:1px solid #666; color:#ddd; background:transparent;">Show Full Library</button>`;
        }
        html += `<div class="finish-library-empty" style="text-align:center; padding:24px 10px; border:1px dashed #333; border-radius:6px; color:var(--text-dim); font-size:11px;">
            <div style="font-size:12px; color:#ddd; margin-bottom:4px;">No finishes match the current filters.</div>
            <div style="margin-bottom:8px;">Try widening the library scope or clearing the active filter.</div>
            <div style="display:flex; justify-content:center; gap:6px; flex-wrap:wrap;">${resetHtml || '<span style="font-size:9px;">Switch browse mode or search for another finish family.</span>'}</div>
        </div>`;
        container.innerHTML = html;
        return;
    }

    if (groupNames.length > 0) {
        // Expand/Collapse All controls
        html += `<div style="display:flex; justify-content:flex-end; gap:6px; margin-bottom:4px; padding:0 2px;">
            <span onclick="expandAllLibraryGroups()" style="font-size:9px; color:var(--accent); cursor:pointer; text-decoration:underline;">Expand All</span>
            <span onclick="collapseAllLibraryGroups()" style="font-size:9px; color:var(--text-dim); cursor:pointer; text-decoration:underline;">Collapse All</span>
        </div>`;

        const _libSectionIcons = { "Color-Changing": "🎨", "Effects & Aesthetic": "✨", "PARADIGM": "◇", "Shokk Series": "⚡", "Weather & Element": "🌤", "Gradients": "〰", "Multi": "🔀", "FUSIONS": "◈", "Solid & Gradients": "•" };
        const useSpecialsSections = activeLibraryTab === 'specials' && typeof SPECIALS_SECTION_ORDER !== 'undefined' && typeof SPECIALS_SECTIONS !== 'undefined';

        function renderLibraryGroup(gn) {
            const isParadigm = gn.startsWith('PARADIGM');
            const isEffect = ["Effect & Visual", "Dark & Gothic", "Neon & Glow", "Weather & Element"].indexOf(gn) >= 0;
            const isOpen = _expandedGroups.has(gn);
            const groupIds = new Set(groupMap[gn]);
            let groupItems = activeTab.items.filter(it => groupIds.has(it.id));
            if (activeLibraryTab === 'patterns') {
                groupItems = groupItems.slice().sort(function(a, b) {
                    const ao = _activeItemOrder.has(a.id) ? _activeItemOrder.get(a.id) : 99999;
                    const bo = _activeItemOrder.has(b.id) ? _activeItemOrder.get(b.id) : 99999;
                    if (ao !== bo) return ao - bo;
                    return (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' });
                });
            } else if (activeLibraryTab === 'bases') {
                groupItems = groupItems.slice().sort((a, b) => (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' }));
            }
            if (groupItems.length === 0) return;
            const chevron = isOpen ? '▾' : '▸';
            const headerBorder = isParadigm ? 'border-left:3px solid var(--accent);' : isEffect ? 'border-left:3px solid var(--accent-gold);' : 'border-left:3px solid var(--accent-green);';
            const headerBg = isOpen ? 'background:var(--surface-hover);' : '';
            html += `<div class="finish-group-accordion" style="margin-bottom:2px;">
                <div onclick="toggleLibraryGroup('${gn.replace(/'/g, "\\'")}')"
                     style="display:flex; align-items:center; gap:6px; padding:5px 8px; cursor:pointer; border-radius:4px; ${headerBorder} ${headerBg} transition:background 0.15s;"
                     onmouseenter="this.style.background='var(--surface-hover)'" onmouseleave="this.style.background='${isOpen ? 'var(--surface-hover)' : ''}'">
                    <span style="font-size:11px; color:var(--accent); width:12px;">${chevron}</span>
                    <span style="font-size:10px; font-weight:600; color:${isParadigm ? 'var(--accent)' : 'var(--text)'}; flex:1;">${gn}</span>
                    <span style="font-size:9px; color:var(--text-dim);">${groupItems.length}</span>
                </div>`;
            if (isOpen) {
                html += `<div style="padding:2px 0 4px 0;">`;
                groupItems.forEach(item => { html += _renderFinishItem(item, activeTab.type); });
                html += `</div>`;
            }
            html += `</div>`;
        }

        if (useSpecialsSections) {
            const rendered = new Set();
            SPECIALS_SECTION_ORDER.forEach(sectionKey => {
                const list = Array.isArray(SPECIALS_SECTIONS[sectionKey]) ? SPECIALS_SECTIONS[sectionKey] : [];
                const icon = _libSectionIcons[sectionKey] || '•';
                html += `<div style="width:100%; font-size:8px; color:var(--accent-green); font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:4px 2px 2px; margin-top:6px; border-top:1px solid var(--border);">${icon} ${sectionKey}</div>`;
                list.forEach(gn => { rendered.add(gn); renderLibraryGroup(gn); });
            });
            const remaining = groupNames.filter(gn => !rendered.has(gn));
            if (remaining.length > 0) {
                html += `<div style="width:100%; font-size:8px; color:var(--accent-green); font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:4px 2px 2px; margin-top:6px; border-top:1px solid var(--border);">• Solid & Gradients</div>`;
                remaining.forEach(gn => renderLibraryGroup(gn));
            }
        } else {
            const _effSet = new Set(["Effect & Visual", "Weather & Element", "Dark & Gothic", "Neon & Glow"]);
            let _prevWasEffect = false;
            let _addedColorLabel = false;
            groupNames.forEach(gn => {
                const isEffect = _effSet.has(gn);
                const isParadigm = gn.startsWith('PARADIGM');
                if (activeLibraryTab === 'specials' && !_addedColorLabel && !isEffect && !isParadigm) {
                    html += `<div style="width:100%; font-size:8px; color:var(--accent-green); font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:3px 2px 1px; margin-top:2px;">Color-Changing</div>`;
                    _addedColorLabel = true;
                }
                if (activeLibraryTab === 'specials' && isEffect && !_prevWasEffect) {
                    html += `<div style="width:100%; font-size:8px; color:var(--accent-gold); font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:3px 2px 1px; margin-top:4px; border-top:1px solid var(--border);">Effect (keeps paint color)</div>`;
                }
                _prevWasEffect = isEffect;
                renderLibraryGroup(gn);
            });
        }

        // Ungrouped items (items not in any group)
        const allGroupedIds = new Set();
        groupNames.forEach(gn => groupMap[gn].forEach(id => allGroupedIds.add(id)));
        const ungrouped = activeTab.items.filter(it => !allGroupedIds.has(it.id));
        if (ungrouped.length > 0 && activeLibraryTab !== 'patterns' && activeLibraryTab !== 'specials') {
            const uIsOpen = _expandedGroups.has('__ungrouped__');
            const uChevron = uIsOpen ? '▾' : '▸';
            const ungroupedLabel = activeLibraryTab === 'bases'
                ? 'Reference / Legacy'
                : 'Other';
            html += `<div class="finish-group-accordion" style="margin-bottom:2px; margin-top:4px;">
                <div onclick="toggleLibraryGroup('__ungrouped__')"
                     style="display:flex; align-items:center; gap:6px; padding:5px 8px; cursor:pointer; border-radius:4px; border-left:3px solid var(--border); transition:background 0.15s;"
                     onmouseenter="this.style.background='var(--surface-hover)'" onmouseleave="this.style.background=''">
                    <span style="font-size:11px; color:var(--text-dim); width:12px;">${uChevron}</span>
                    <span style="font-size:10px; font-weight:600; color:var(--text-dim); flex:1;">${ungroupedLabel}</span>
                    <span style="font-size:9px; color:var(--text-dim);">${ungrouped.length}</span>
                </div>`;
            if (uIsOpen) {
                html += `<div style="padding:2px 0 4px 0;">`;
                ungrouped.forEach(item => {
                    html += _renderFinishItem(item, activeTab.type);
                });
                html += `</div>`;
            }
            html += `</div>`;
        }
    } else {
        // No groups - render all items flat
        activeTab.items.forEach(item => {
            html += _renderFinishItem(item, activeTab.type);
        });
    }

    container.innerHTML = html;
    // No deferred canvas rendering needed - swatches are server-rendered <img> tags
}

function filterFinishes(query) {
    const q = query.toLowerCase().trim();
    const items = document.querySelectorAll('#finishLibrary .finish-item');
    let visibleCount = 0;
    // Multi-word search: ALL words must match (AND logic)
    const words = q.split(/\s+/).filter(w => w.length > 0);
    items.forEach(item => {
        if (!q) { item.style.display = ''; visibleCount++; return; }
        const name = item.getAttribute('data-name') || '';
        const desc = item.getAttribute('data-desc') || '';
        const id = item.getAttribute('data-id') || '';
        // Also search metadata tags if available
        const meta = (typeof FINISH_METADATA !== 'undefined' && FINISH_METADATA[id]) || {};
        const family = (meta.family || '').toLowerCase();
        const group = (meta.browserGroup || '').toLowerCase();
        const section = (meta.browserSection || '').toLowerCase();
        const searchText = `${name} ${desc} ${id} ${family} ${group} ${section}`;
        // Every word must appear somewhere
        const matches = words.every(w => searchText.includes(w));
        item.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });
    // Show/hide "no results" message
    let noResults = document.getElementById('finishNoResults');
    if (visibleCount === 0 && q) {
        if (!noResults) {
            noResults = document.createElement('div');
            noResults.id = 'finishNoResults';
            noResults.style.cssText = 'text-align:center; padding:20px; color:var(--text-dim); font-size:11px;';
            document.getElementById('finishLibrary').appendChild(noResults);
        }
        noResults.textContent = `No finishes matching "${query}"`;
        noResults.style.display = '';
    } else if (noResults) {
        noResults.style.display = 'none';
    }
}

function toggleCategory(cat) {
    categoryCollapsed[cat] = !categoryCollapsed[cat];
    renderFinishLibrary();
}

// ===== SECTION TOGGLE =====
function toggleSection(id) {
    const body = document.getElementById(id + '-body');
    const toggle = document.getElementById(id + '-toggle');
    const header = toggle.closest('.section-header');
    if (body.classList.contains('collapsed')) {
        body.classList.remove('collapsed');
        header.classList.remove('collapsed');
    } else {
        body.classList.add('collapsed');
        header.classList.add('collapsed');
    }
}


// ===== PRESETS =====
// 2026-04-21 HEENAN OVERNIGHT iter 1: polymorphic applyPreset dispatcher
// replaces the two silently-dueling definitions that used to exist at this
// location and at ~line 9598. The object-form used to hoist over the
// ID-form, breaking every preset-gallery card click (they call
// `applyPreset('some_id')` — which was dispatched to the object-form
// function, which then threw TypeError on `preset.zones.map` because
// `preset` was the string id).
//
// Contract:
//   applyPreset(presetId: string)  → gallery card click, loads a built-in
//                                    preset from the PRESETS catalog.
//   applyPreset(preset: object)    → .shokker file import, loads a preset
//                                    object already parsed from JSON.
// Anything else is silently ignored (return) with a warning.
function applyPreset(arg) {
    if (typeof arg === 'string') {
        return _applyPresetById(arg);
    }
    if (arg && typeof arg === 'object' && Array.isArray(arg.zones)) {
        return _applyPresetFromObject(arg);
    }
    console.warn('[SPB] applyPreset called with unsupported arg:', arg);
}

function _applyPresetById(presetId) {
    if (!presetId || !PRESETS[presetId]) return;
    const preset = PRESETS[presetId];
    zones = preset.zones.map(z => ({
        id: _newZoneId(),
        name: z.name,
        color: z.color,
        base: z.base || null,
        pattern: z.pattern || 'none',
        finish: z.finish || null,
        intensity: z.intensity,
        customSpec: null, customPaint: null, customBright: null,
        hint: z.hint || '',
        colorMode: z.color === null ? 'none' :
            SPECIAL_COLORS.some(sc => sc.value === z.color) ? 'special' :
                QUICK_COLORS.some(qc => qc.value === z.color) ? 'quick' : 'text',
        pickerColor: '#3366ff',
        pickerTolerance: 40,
        colors: [],
        regionMask: null,
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        patternStack: [],
    }));
    if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'built-in preset: ' + presetId);
    selectedZoneIndex = 0;
    renderZones();
    showToast(`Loaded preset: ${preset.name} — set colors using the eyedropper!`);
}

// ===== TOAST =====
// showToast(msg, isError, details) -- details is optional extra text shown smaller below main message
function showToast(msg, isError, details) {
    const toast = document.getElementById('toast');
    if (!toast) { console.warn('[SPB] Toast element not found, message:', msg); return; }
    const _toastSeverity = typeof isError === 'string' ? String(isError).toLowerCase() : '';
    const _toastSeverityNormalized = _toastSeverity === 'warn' ? 'warning' : _toastSeverity;
    const _toastExplicitError = _toastSeverityNormalized === 'error';
    const _toastExplicitSuccess = _toastSeverityNormalized === 'success';
    const _toastExplicitWarning = _toastSeverityNormalized === 'warning';
    const _toastExplicitInfo = _toastSeverityNormalized === 'info';
    // Auto-detect styling from message content
    const isSuccess = typeof msg === 'string' && (msg.startsWith('✅') || msg.startsWith('🔥'));
    const isErr = isError === true || (typeof msg === 'string' && msg.startsWith('❌'));
    const isWarning = typeof msg === 'string' && msg.toLowerCase().startsWith('warning');
    toast.className = 'toast show' + (
        _toastExplicitError || isErr ? ' error' :
        _toastExplicitSuccess || isSuccess ? ' success' :
        _toastExplicitWarning || isWarning ? ' warning' :
        _toastExplicitInfo ? ' info' : ''
    );
    // Build content with close button
    toast.innerHTML = '';
    const msgSpan = document.createElement('span');
    msgSpan.textContent = msg;
    // Optional detail line for error context
    if (details) {
        const detSpan = document.createElement('div');
        detSpan.textContent = details;
        detSpan.style.cssText = 'font-size:10px; color:rgba(255,255,255,0.6); margin-top:2px;';
        const wrapper = document.createElement('div');
        wrapper.appendChild(msgSpan);
        wrapper.appendChild(detSpan);
        toast.appendChild(wrapper);
    } else {
        toast.appendChild(msgSpan);
    }
    const closeBtn = document.createElement('span');
    closeBtn.innerHTML = '&#x2715;';
    closeBtn.style.cssText = 'cursor:pointer; margin-left:12px; font-weight:bold; opacity:0.7; flex-shrink:0;';
    closeBtn.title = 'Dismiss';
    closeBtn.onclick = () => { toast.className = 'toast'; clearTimeout(showToast._timer); };
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.appendChild(closeBtn);
    // 60 seconds auto-dismiss
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => toast.className = 'toast', 60000);
}

// ===== RENDER NOTIFICATION SYSTEM =====
const RenderNotify = {
    _originalTitle: document.title,
    _flashTimer: null,

    // Play a short success/error tone using Web Audio API (no external files needed)
    playSound(success) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            if (success) {
                // Two-tone success chime
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.frequency.setValueAtTime(1175, ctx.currentTime + 0.12);
                gain.gain.setValueAtTime(0.15, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.35);
            } else {
                // Low buzz for error
                osc.type = 'square';
                osc.frequency.setValueAtTime(220, ctx.currentTime);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.3);
            }
        } catch (e) { /* Audio not available */ }
    },

    // Flash the tab title to get attention when tabbed away
    flashTitle(msg) {
        if (this._flashTimer) clearInterval(this._flashTimer);
        let on = true;
        this._flashTimer = setInterval(() => {
            document.title = on ? msg : this._originalTitle;
            on = !on;
        }, 800);
        // Stop flashing when window gets focus
        const stop = () => {
            clearInterval(this._flashTimer);
            this._flashTimer = null;
            document.title = this._originalTitle;
            window.removeEventListener('focus', stop);
        };
        window.addEventListener('focus', stop);
        // Auto-stop after 30 seconds
        setTimeout(stop, 30000);
    },

    // Browser notification (only if page is not focused)
    browserNotify(title, body) {
        if (document.hasFocus()) return;
        if (Notification.permission === 'granted') {
            new Notification(title, { body, icon: '🎨' });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    },

    // Call this when render completes
    onRenderComplete(success, elapsed, zoneCount) {
        this.playSound(success);
        if (!document.hasFocus()) {
            if (success) {
                this.flashTitle(`✅ Render done! (${elapsed}s)`);
                this.browserNotify('Shokker Render Complete', `${zoneCount} zones rendered in ${elapsed}s`);
            } else {
                this.flashTitle('❌ Render failed!');
                this.browserNotify('Shokker Render Failed', 'Check the Paint Booth for details');
            }
        }
    }
};

// Request notification permission early (on user interaction)
document.addEventListener('click', () => {
    if (window.Notification && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}, { once: true });

// ===== RENDER ELAPSED TIMER =====
let renderStartTime = null;
let renderElapsedTimer = null;
function startRenderTimer() {
    renderStartTime = Date.now();
    const btn = document.getElementById('btnRender');
    renderElapsedTimer = setInterval(() => {
        const elapsed = ((Date.now() - renderStartTime) / 1000).toFixed(0);
        btn.textContent = `RENDERING... ${elapsed}s`;
    }, 500);
}
function stopRenderTimer() {
    if (renderElapsedTimer) { clearInterval(renderElapsedTimer); renderElapsedTimer = null; }
    renderStartTime = null;
}

// ===== OUTPUT PATH AUTO-FILL =====
const BASE_DRIVER_PATH = "";  // Set via config or leave blank - output path is user-defined

function updateOutputPath() {
    const iracingId = document.getElementById('iracingId').value.trim();

    // Update filename preview if element exists (moved to header, may not have preview span)
    const preview = document.getElementById('outputFilenamePreview');
    if (preview) preview.textContent = `car_num_${iracingId}.tga + car_spec_${iracingId}.tga`;
}

// ===== CONFIG SAVE / LOAD =====
function getConfig() {
    const canonicalSourcePaintFile = (typeof window !== 'undefined' && typeof window.getCurrentSourcePaintFile === 'function')
        ? (window.getCurrentSourcePaintFile() || '')
        : (document.getElementById('paintFile')?.value || '');
    return {
        version: "3.0",
        driverName: document.getElementById('driverName')?.value || '',
        carName: document.getElementById('carName')?.value || '',
        iracingId: document.getElementById('iracingId')?.value || '',
        paintFile: document.getElementById('paintFile')?.value || '',
        sourcePaintFile: canonicalSourcePaintFile,
        outputDir: document.getElementById('outputDir').value,
        helmetFile: document.getElementById('helmetFile')?.value || '',
        suitFile: document.getElementById('suitFile')?.value || '',
        wearLevel: parseInt(document.getElementById('wearSlider')?.value || '0', 10),
        exportZip: document.getElementById('exportZipCheckbox')?.checked || false,
        dualSpec: document.getElementById('dualSpecCheckbox')?.checked || false,
        nightBoost: parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7'),
        zones: zones.map(z => ({
            name: z.name,
            color: z.color,
            base: z.base,
            pattern: z.pattern,
            finish: z.finish,
            intensity: z.intensity,
            customSpec: z.customSpec != null ? z.customSpec : undefined,
            customPaint: z.customPaint != null ? z.customPaint : undefined,
            customBright: z.customBright != null ? z.customBright : undefined,
            colorMode: z.colorMode,
            pickerColor: z.pickerColor,
            pickerTolerance: z.pickerTolerance,
            colors: z.colors || [],
            scale: z.scale ?? 1.0,
            rotation: z.rotation ?? 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternOffsetX: z.patternOffsetX ?? 0.5,
            patternOffsetY: z.patternOffsetY ?? 0.5,
            patternStack: z.patternStack || [],
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
            patternIntensity: z.patternIntensity ?? '100',
            wear: z.wear ?? 0,
            muted: z.muted ?? false,
            linkGroup: z.linkGroup || null,
            baseStrength: z.baseStrength ?? 1,
            baseSpecStrength: z.baseSpecStrength ?? 1,
            patternSpecMult: z.patternSpecMult ?? 1,
            patternFlipH: z.patternFlipH ?? false,
            patternFlipV: z.patternFlipV ?? false,
            baseOffsetX: z.baseOffsetX ?? 0.5,
            baseOffsetY: z.baseOffsetY ?? 0.5,
            baseRotation: z.baseRotation ?? 0,
            baseFlipH: z.baseFlipH ?? false,
            baseFlipV: z.baseFlipV ?? false,
            // BOIL THE OCEAN audit: baseScale was the ONLY scale field in the
            // zone payload without a default, while every sibling
            // (secondBaseScale, thirdBaseScale, fourthBaseScale, fifthBaseScale)
            // defaults to 1. Aligning with the family so an unset zone never
            // sends `undefined` to the engine for the primary base scale.
            baseScale: z.baseScale ?? 1,
            baseColorMode: z.baseColorMode ?? 'source',
            baseColor: z.baseColor ?? '#ffffff',
            baseColorSource: z.baseColorSource ?? null,
            baseColorStrength: z.baseColorStrength ?? 1,
            baseColorFitZone: z.baseColorFitZone ?? false,
            gradientStops: z.gradientStops || null,
            gradientDirection: z.gradientDirection || 'horizontal',
            baseHueOffset: z.baseHueOffset ?? 0,
            baseSaturationAdjust: z.baseSaturationAdjust ?? 0,
            baseBrightnessAdjust: z.baseBrightnessAdjust ?? 0,
            secondBase: z.secondBase ?? null,
            secondBaseColor: z.secondBaseColor ?? '#ffffff',
            secondBaseStrength: z.secondBaseStrength ?? 0,
            secondBaseSpecStrength: z.secondBaseSpecStrength ?? 1,
            secondBaseColorSource: z.secondBaseColorSource ?? null,
            secondBaseBlendMode: z.secondBaseBlendMode ?? 'noise',
            secondBaseFractalScale: z.secondBaseFractalScale ?? z.secondBaseNoiseScale ?? 24,
            secondBaseScale: z.secondBaseScale ?? 1,
            secondBasePattern: z.secondBasePattern ?? null,
            secondBasePatternOpacity: z.secondBasePatternOpacity ?? 100,
            secondBasePatternScale: z.secondBasePatternScale ?? 1,
            secondBasePatternRotation: z.secondBasePatternRotation ?? 0,
            secondBasePatternStrength: z.secondBasePatternStrength ?? 1,
            secondBasePatternInvert: z.secondBasePatternInvert ?? false,
            secondBasePatternHarden: z.secondBasePatternHarden ?? false,
            secondBasePatternOffsetX: z.secondBasePatternOffsetX ?? 0.5,
            secondBasePatternOffsetY: z.secondBasePatternOffsetY ?? 0.5,
            secondBaseHueShift: z.secondBaseHueShift ?? 0,
            secondBaseSaturation: z.secondBaseSaturation ?? 0,
            secondBaseBrightness: z.secondBaseBrightness ?? 0,
            secondBasePatternHueShift: z.secondBasePatternHueShift ?? 0,
            secondBasePatternSaturation: z.secondBasePatternSaturation ?? 0,
            secondBasePatternBrightness: z.secondBasePatternBrightness ?? 0,
            secondBasePatternFlipH: z.secondBasePatternFlipH ?? false,
            secondBasePatternFlipV: z.secondBasePatternFlipV ?? false,
            thirdBase: z.thirdBase ?? null,
            thirdBaseColor: z.thirdBaseColor ?? '#ffffff',
            thirdBaseStrength: z.thirdBaseStrength ?? 0,
            thirdBaseSpecStrength: z.thirdBaseSpecStrength ?? 1,
            thirdBaseColorSource: z.thirdBaseColorSource ?? null,
            thirdBaseBlendMode: z.thirdBaseBlendMode ?? 'noise',
            thirdBaseFractalScale: z.thirdBaseFractalScale ?? z.thirdBaseNoiseScale ?? 24,
            thirdBaseScale: z.thirdBaseScale ?? 1,
            thirdBasePattern: z.thirdBasePattern ?? null,
            thirdBasePatternOpacity: z.thirdBasePatternOpacity ?? 100,
            thirdBasePatternScale: z.thirdBasePatternScale ?? 1,
            thirdBasePatternRotation: z.thirdBasePatternRotation ?? 0,
            thirdBasePatternStrength: z.thirdBasePatternStrength ?? 1,
            thirdBasePatternInvert: z.thirdBasePatternInvert ?? false,
            thirdBasePatternHarden: z.thirdBasePatternHarden ?? false,
            thirdBasePatternOffsetX: z.thirdBasePatternOffsetX ?? 0.5,
            thirdBasePatternOffsetY: z.thirdBasePatternOffsetY ?? 0.5,
            thirdBaseHueShift: z.thirdBaseHueShift ?? 0,
            thirdBaseSaturation: z.thirdBaseSaturation ?? 0,
            thirdBaseBrightness: z.thirdBaseBrightness ?? 0,
            thirdBasePatternHueShift: z.thirdBasePatternHueShift ?? 0,
            thirdBasePatternSaturation: z.thirdBasePatternSaturation ?? 0,
            thirdBasePatternBrightness: z.thirdBasePatternBrightness ?? 0,
            thirdBasePatternFlipH: z.thirdBasePatternFlipH ?? false,
            thirdBasePatternFlipV: z.thirdBasePatternFlipV ?? false,
            fourthBase: z.fourthBase ?? null,
            fourthBaseColor: z.fourthBaseColor ?? '#ffffff',
            fourthBaseStrength: z.fourthBaseStrength ?? 0,
            fourthBaseSpecStrength: z.fourthBaseSpecStrength ?? 1,
            fourthBaseColorSource: z.fourthBaseColorSource ?? null,
            fourthBaseBlendMode: z.fourthBaseBlendMode ?? 'noise',
            fourthBaseFractalScale: z.fourthBaseFractalScale ?? z.fourthBaseNoiseScale ?? 24,
            fourthBaseScale: z.fourthBaseScale ?? 1,
            fourthBasePattern: z.fourthBasePattern ?? null,
            fourthBasePatternOpacity: z.fourthBasePatternOpacity ?? 100,
            fourthBasePatternScale: z.fourthBasePatternScale ?? 1,
            fourthBasePatternRotation: z.fourthBasePatternRotation ?? 0,
            fourthBasePatternStrength: z.fourthBasePatternStrength ?? 1,
            fourthBasePatternInvert: z.fourthBasePatternInvert ?? false,
            fourthBasePatternHarden: z.fourthBasePatternHarden ?? false,
            fourthBasePatternOffsetX: z.fourthBasePatternOffsetX ?? 0.5,
            fourthBasePatternOffsetY: z.fourthBasePatternOffsetY ?? 0.5,
            fourthBaseHueShift: z.fourthBaseHueShift ?? 0,
            fourthBaseSaturation: z.fourthBaseSaturation ?? 0,
            fourthBaseBrightness: z.fourthBaseBrightness ?? 0,
            fourthBasePatternHueShift: z.fourthBasePatternHueShift ?? 0,
            fourthBasePatternSaturation: z.fourthBasePatternSaturation ?? 0,
            fourthBasePatternBrightness: z.fourthBasePatternBrightness ?? 0,
            fourthBasePatternFlipH: z.fourthBasePatternFlipH ?? false,
            fourthBasePatternFlipV: z.fourthBasePatternFlipV ?? false,
            fifthBase: z.fifthBase ?? null,
            fifthBaseColor: z.fifthBaseColor ?? '#ffffff',
            fifthBaseStrength: z.fifthBaseStrength ?? 0,
            fifthBaseSpecStrength: z.fifthBaseSpecStrength ?? 1,
            fifthBaseColorSource: z.fifthBaseColorSource ?? null,
            fifthBaseBlendMode: z.fifthBaseBlendMode ?? 'noise',
            fifthBaseFractalScale: z.fifthBaseFractalScale ?? z.fifthBaseNoiseScale ?? 24,
            fifthBaseScale: z.fifthBaseScale ?? 1,
            fifthBasePattern: z.fifthBasePattern ?? null,
            fifthBasePatternOpacity: z.fifthBasePatternOpacity ?? 100,
            fifthBasePatternScale: z.fifthBasePatternScale ?? 1,
            fifthBasePatternRotation: z.fifthBasePatternRotation ?? 0,
            fifthBasePatternStrength: z.fifthBasePatternStrength ?? 1,
            fifthBasePatternInvert: z.fifthBasePatternInvert ?? false,
            fifthBasePatternHarden: z.fifthBasePatternHarden ?? false,
            fifthBasePatternOffsetX: z.fifthBasePatternOffsetX ?? 0.5,
            fifthBasePatternOffsetY: z.fifthBasePatternOffsetY ?? 0.5,
            fifthBaseHueShift: z.fifthBaseHueShift ?? 0,
            fifthBaseSaturation: z.fifthBaseSaturation ?? 0,
            fifthBaseBrightness: z.fifthBaseBrightness ?? 0,
            fifthBasePatternHueShift: z.fifthBasePatternHueShift ?? 0,
            fifthBasePatternSaturation: z.fifthBasePatternSaturation ?? 0,
            fifthBasePatternBrightness: z.fifthBasePatternBrightness ?? 0,
            fifthBasePatternFlipH: z.fifthBasePatternFlipH ?? false,
            fifthBasePatternFlipV: z.fifthBasePatternFlipV ?? false,
            ccQuality: z.ccQuality,
            blendBase: z.blendBase,
            blendDir: z.blendDir,
            blendAmount: z.blendAmount,
            usePaintReactive: z.usePaintReactive,
            paintReactiveColor: z.paintReactiveColor,
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
            // Placement & edge properties
            patternPlacement: z.patternPlacement ?? 'normal',
            basePlacement: z.basePlacement ?? 'normal',
            baseSpecBlendMode: z.baseSpecBlendMode ?? 'normal',
            hardEdge: z.hardEdge ?? false,
            // Overlay fit-to-zone flags
            secondBaseFitZone: z.secondBaseFitZone ?? false,
            thirdBaseFitZone: z.thirdBaseFitZone ?? false,
            fourthBaseFitZone: z.fourthBaseFitZone ?? false,
            fifthBaseFitZone: z.fifthBaseFitZone ?? false,
            // Layer restriction
            id: z.id || _newZoneId(),
            sourceLayer: z.sourceLayer || null,
            spatialMask: z.spatialMask ? Array.from(_cloneUint8ArrayLike(z.spatialMask) || []) : null,
            // 2026-04-18 MARATHON bug #28 (Bockwinkel, HIGH): pre-fix,
            // patternStrengthMap + Enabled flag were never saved by
            // getConfig, so autoSave silently lost them across page
            // reloads. Painter carefully painted a heatmap, F5'd, came
            // back to uniform pattern. Now both survive the roundtrip.
            // We serialize the Uint8Array data as a plain Array for JSON
            // compatibility; loadConfigFromObj reconstitutes a Uint8Array.
            patternStrengthMapEnabled: z.patternStrengthMapEnabled ?? false,
            patternStrengthMap: (z.patternStrengthMap && z.patternStrengthMap.data) ? {
                width: z.patternStrengthMap.width,
                height: z.patternStrengthMap.height,
                data: Array.from(z.patternStrengthMap.data),
            } : null,
        })),
        // Decals disabled - future feature
        importedSpecMapPath: importedSpecMapPath || null,
        activeSpecChannel: activeSpecChannel || 'all',
    };
}

function loadConfigFromObj(cfg) {
    if (cfg.driverName !== undefined) { const el = document.getElementById('driverName'); if (el) el.value = cfg.driverName; }
    if (cfg.carName !== undefined) { const el = document.getElementById('carName'); if (el) el.value = cfg.carName; }
    if (cfg.iracingId !== undefined) { const el = document.getElementById('iracingId'); if (el) el.value = cfg.iracingId; }
    // 2026-04-18 MARATHON bug #41 (Raven, MED): null-guard these two
    // critical inputs. Pre-fix, if paintFile or outputDir input was
    // missing from the DOM (custom embed, future layout refactor), the
    // `.value = ...` threw and the rest of loadConfigFromObj silently
    // skipped — zones loaded but other settings never applied.
    if (cfg.paintFile !== undefined) { const el = document.getElementById('paintFile'); if (el) el.value = cfg.paintFile; }
    if (cfg.outputDir !== undefined) { const el = document.getElementById('outputDir'); if (el) el.value = cfg.outputDir; }
    // Extras
    if (cfg.helmetFile !== undefined && document.getElementById('helmetFile')) document.getElementById('helmetFile').value = cfg.helmetFile;
    if (cfg.suitFile !== undefined && document.getElementById('suitFile')) document.getElementById('suitFile').value = cfg.suitFile;
    if (cfg.wearLevel !== undefined && document.getElementById('wearSlider')) {
        document.getElementById('wearSlider').value = cfg.wearLevel;
        updateWearDisplay(cfg.wearLevel);
    }
    if (cfg.exportZip !== undefined && document.getElementById('exportZipCheckbox')) document.getElementById('exportZipCheckbox').checked = cfg.exportZip;
    if (cfg.dualSpec !== undefined && document.getElementById('dualSpecCheckbox')) { document.getElementById('dualSpecCheckbox').checked = cfg.dualSpec; toggleNightBoostSlider(); }
    if (cfg.nightBoost !== undefined && document.getElementById('nightBoostSlider')) { document.getElementById('nightBoostSlider').value = cfg.nightBoost; document.getElementById('nightBoostVal').textContent = parseFloat(cfg.nightBoost).toFixed(2); }
    updateOutputPath();
    if (cfg.zones) {
        // 2026-04-19 HEENAN HP-MIGRATE: rewrite legacy finish/pattern/spec
        // ids IN-PLACE on the incoming cfg.zones BEFORE materializing into
        // the live zones array. Codex audit: pre-fix, saves from before the
        // HP1-HP4 + HB2 rename pass silently orphaned on load. Migration
        // map lives at `_SPB_LEGACY_ID_MIGRATIONS` above.
        if (typeof _migrateZoneFinishIds === 'function') {
            cfg.zones.forEach(function (z) {
                try { _migrateZoneFinishIds(z); } catch (_) {}
            });
        }
        zones = cfg.zones.map(z => ({
            id: z.id || _newZoneId(),
            name: z.name || 'Zone',
            color: z.color,
            base: z.base ?? null,
            pattern: z.pattern ?? 'none',
            finish: z.finish ?? null,
            intensity: z.intensity ?? '100',
            customSpec: z.customSpec != null ? z.customSpec : null,
            customPaint: z.customPaint != null ? z.customPaint : null,
            customBright: z.customBright != null ? z.customBright : null,
            colorMode: z.colorMode ?? 'none',
            pickerColor: z.pickerColor ?? '#3366ff',
            pickerTolerance: z.pickerTolerance ?? 40,
            colors: z.colors || [],
            regionMask: null,
            spatialMask: _cloneUint8ArrayLike(z.spatialMask),
            lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
            scale: z.scale ?? 1.0,
            rotation: z.rotation ?? 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternOffsetX: z.patternOffsetX ?? 0.5,
            patternOffsetY: z.patternOffsetY ?? 0.5,
            patternStack: z.patternStack || [],
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
            patternIntensity: z.patternIntensity ?? '100',
            wear: z.wear ?? 0,
            muted: z.muted ?? false,
            linkGroup: z.linkGroup ?? null,
            baseStrength: z.baseStrength ?? 1,
            baseSpecStrength: z.baseSpecStrength ?? 1,
            patternSpecMult: z.patternSpecMult ?? 1,
            patternFlipH: z.patternFlipH ?? false,
            patternFlipV: z.patternFlipV ?? false,
            baseOffsetX: z.baseOffsetX ?? 0.5,
            baseOffsetY: z.baseOffsetY ?? 0.5,
            baseRotation: z.baseRotation ?? 0,
            baseFlipH: z.baseFlipH ?? false,
            baseFlipV: z.baseFlipV ?? false,
            baseScale: z.baseScale ?? 1.0,
            baseColorMode: z.baseColorMode ?? 'source',
            baseColor: z.baseColor ?? '#ffffff',
            baseColorSource: z.baseColorSource ?? null,
            baseColorStrength: z.baseColorStrength ?? 1,
            baseColorFitZone: z.baseColorFitZone ?? false,
            gradientStops: z.gradientStops || null,
            gradientDirection: z.gradientDirection || 'horizontal',
            baseHueOffset: z.baseHueOffset ?? 0,
            baseSaturationAdjust: z.baseSaturationAdjust ?? 0,
            baseBrightnessAdjust: z.baseBrightnessAdjust ?? 0,
            secondBase: z.secondBase ?? null,
            secondBaseColor: z.secondBaseColor ?? '#ffffff',
            secondBaseStrength: z.secondBaseStrength ?? 0,
            secondBaseSpecStrength: z.secondBaseSpecStrength ?? 1,
            secondBaseColorSource: z.secondBaseColorSource ?? null,
            secondBaseBlendMode: z.secondBaseBlendMode ?? 'noise',
            secondBaseFractalScale: z.secondBaseFractalScale ?? z.secondBaseNoiseScale ?? 24,
            secondBaseScale: z.secondBaseScale ?? 1,
            secondBasePattern: z.secondBasePattern ?? null,
            secondBasePatternOpacity: z.secondBasePatternOpacity ?? 100,
            secondBasePatternScale: z.secondBasePatternScale ?? 1,
            secondBasePatternRotation: z.secondBasePatternRotation ?? 0,
            secondBasePatternStrength: z.secondBasePatternStrength ?? 1,
            secondBasePatternInvert: z.secondBasePatternInvert ?? false,
            secondBasePatternHarden: z.secondBasePatternHarden ?? false,
            secondBasePatternOffsetX: z.secondBasePatternOffsetX ?? 0.5,
            secondBasePatternOffsetY: z.secondBasePatternOffsetY ?? 0.5,
            secondBaseHueShift: z.secondBaseHueShift ?? 0,
            secondBaseSaturation: z.secondBaseSaturation ?? 0,
            secondBaseBrightness: z.secondBaseBrightness ?? 0,
            secondBasePatternHueShift: z.secondBasePatternHueShift ?? 0,
            secondBasePatternSaturation: z.secondBasePatternSaturation ?? 0,
            secondBasePatternBrightness: z.secondBasePatternBrightness ?? 0,
            secondBasePatternFlipH: z.secondBasePatternFlipH ?? false,
            secondBasePatternFlipV: z.secondBasePatternFlipV ?? false,
            thirdBase: z.thirdBase ?? null,
            thirdBaseColor: z.thirdBaseColor ?? '#ffffff',
            thirdBaseStrength: z.thirdBaseStrength ?? 0,
            thirdBaseSpecStrength: z.thirdBaseSpecStrength ?? 1,
            thirdBaseColorSource: z.thirdBaseColorSource ?? null,
            thirdBaseBlendMode: z.thirdBaseBlendMode ?? 'noise',
            thirdBaseFractalScale: z.thirdBaseFractalScale ?? z.thirdBaseNoiseScale ?? 24,
            thirdBaseScale: z.thirdBaseScale ?? 1,
            thirdBasePattern: z.thirdBasePattern ?? null,
            thirdBasePatternOpacity: z.thirdBasePatternOpacity ?? 100,
            thirdBasePatternScale: z.thirdBasePatternScale ?? 1,
            thirdBasePatternRotation: z.thirdBasePatternRotation ?? 0,
            thirdBasePatternStrength: z.thirdBasePatternStrength ?? 1,
            thirdBasePatternInvert: z.thirdBasePatternInvert ?? false,
            thirdBasePatternHarden: z.thirdBasePatternHarden ?? false,
            thirdBasePatternOffsetX: z.thirdBasePatternOffsetX ?? 0.5,
            thirdBasePatternOffsetY: z.thirdBasePatternOffsetY ?? 0.5,
            thirdBaseHueShift: z.thirdBaseHueShift ?? 0,
            thirdBaseSaturation: z.thirdBaseSaturation ?? 0,
            thirdBaseBrightness: z.thirdBaseBrightness ?? 0,
            thirdBasePatternHueShift: z.thirdBasePatternHueShift ?? 0,
            thirdBasePatternSaturation: z.thirdBasePatternSaturation ?? 0,
            thirdBasePatternBrightness: z.thirdBasePatternBrightness ?? 0,
            thirdBasePatternFlipH: z.thirdBasePatternFlipH ?? false,
            thirdBasePatternFlipV: z.thirdBasePatternFlipV ?? false,
            fourthBase: z.fourthBase ?? null,
            fourthBaseColor: z.fourthBaseColor ?? '#ffffff',
            fourthBaseStrength: z.fourthBaseStrength ?? 0,
            fourthBaseSpecStrength: z.fourthBaseSpecStrength ?? 1,
            fourthBaseColorSource: z.fourthBaseColorSource ?? null,
            fourthBaseBlendMode: z.fourthBaseBlendMode ?? 'noise',
            fourthBaseFractalScale: z.fourthBaseFractalScale ?? z.fourthBaseNoiseScale ?? 24,
            fourthBaseScale: z.fourthBaseScale ?? 1,
            fourthBasePattern: z.fourthBasePattern ?? null,
            fourthBasePatternOpacity: z.fourthBasePatternOpacity ?? 100,
            fourthBasePatternScale: z.fourthBasePatternScale ?? 1,
            fourthBasePatternRotation: z.fourthBasePatternRotation ?? 0,
            fourthBasePatternStrength: z.fourthBasePatternStrength ?? 1,
            fourthBasePatternInvert: z.fourthBasePatternInvert ?? false,
            fourthBasePatternHarden: z.fourthBasePatternHarden ?? false,
            fourthBasePatternOffsetX: z.fourthBasePatternOffsetX ?? 0.5,
            fourthBasePatternOffsetY: z.fourthBasePatternOffsetY ?? 0.5,
            fourthBaseHueShift: z.fourthBaseHueShift ?? 0,
            fourthBaseSaturation: z.fourthBaseSaturation ?? 0,
            fourthBaseBrightness: z.fourthBaseBrightness ?? 0,
            fourthBasePatternHueShift: z.fourthBasePatternHueShift ?? 0,
            fourthBasePatternSaturation: z.fourthBasePatternSaturation ?? 0,
            fourthBasePatternBrightness: z.fourthBasePatternBrightness ?? 0,
            fourthBasePatternFlipH: z.fourthBasePatternFlipH ?? false,
            fourthBasePatternFlipV: z.fourthBasePatternFlipV ?? false,
            fifthBase: z.fifthBase ?? null,
            fifthBaseColor: z.fifthBaseColor ?? '#ffffff',
            fifthBaseStrength: z.fifthBaseStrength ?? 0,
            fifthBaseSpecStrength: z.fifthBaseSpecStrength ?? 1,
            fifthBaseColorSource: z.fifthBaseColorSource ?? null,
            fifthBaseBlendMode: z.fifthBaseBlendMode ?? 'noise',
            fifthBaseFractalScale: z.fifthBaseFractalScale ?? z.fifthBaseNoiseScale ?? 24,
            fifthBaseScale: z.fifthBaseScale ?? 1,
            fifthBasePattern: z.fifthBasePattern ?? null,
            fifthBasePatternOpacity: z.fifthBasePatternOpacity ?? 100,
            fifthBasePatternScale: z.fifthBasePatternScale ?? 1,
            fifthBasePatternRotation: z.fifthBasePatternRotation ?? 0,
            fifthBasePatternStrength: z.fifthBasePatternStrength ?? 1,
            fifthBasePatternInvert: z.fifthBasePatternInvert ?? false,
            fifthBasePatternHarden: z.fifthBasePatternHarden ?? false,
            fifthBasePatternOffsetX: z.fifthBasePatternOffsetX ?? 0.5,
            fifthBasePatternOffsetY: z.fifthBasePatternOffsetY ?? 0.5,
            fifthBaseHueShift: z.fifthBaseHueShift ?? 0,
            fifthBaseSaturation: z.fifthBaseSaturation ?? 0,
            fifthBaseBrightness: z.fifthBaseBrightness ?? 0,
            fifthBasePatternHueShift: z.fifthBasePatternHueShift ?? 0,
            fifthBasePatternSaturation: z.fifthBasePatternSaturation ?? 0,
            fifthBasePatternBrightness: z.fifthBasePatternBrightness ?? 0,
            fifthBasePatternFlipH: z.fifthBasePatternFlipH ?? false,
            fifthBasePatternFlipV: z.fifthBasePatternFlipV ?? false,
            ccQuality: z.ccQuality ?? 100,
            blendBase: z.blendBase ?? null,
            blendDir: z.blendDir ?? 'horizontal',
            blendAmount: z.blendAmount ?? 50,
            usePaintReactive: z.usePaintReactive ?? false,
            paintReactiveColor: z.paintReactiveColor ?? null,
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
            // Placement & edge properties (with backward-compatible defaults)
            patternPlacement: z.patternPlacement ?? 'normal',
            basePlacement: z.basePlacement ?? 'normal',
            baseSpecBlendMode: z.baseSpecBlendMode ?? 'normal',
            hardEdge: z.hardEdge ?? false,
            // Overlay fit-to-zone flags (with backward-compatible defaults)
            secondBaseFitZone: z.secondBaseFitZone ?? false,
            thirdBaseFitZone: z.thirdBaseFitZone ?? false,
            fourthBaseFitZone: z.fourthBaseFitZone ?? false,
            fifthBaseFitZone: z.fifthBaseFitZone ?? false,
            // Layer restriction
            sourceLayer: z.sourceLayer || null,
            // 2026-04-18 MARATHON bug #28 (Bockwinkel, HIGH): reconstitute
            // patternStrengthMap from the plain-array JSON form back into a
            // Uint8Array so the engine payload builder's
            // encodeStrengthMapRLE call still works.
            patternStrengthMapEnabled: z.patternStrengthMapEnabled ?? false,
            patternStrengthMap: (z.patternStrengthMap && z.patternStrengthMap.data && z.patternStrengthMap.width && z.patternStrengthMap.height) ? {
                width: z.patternStrengthMap.width,
                height: z.patternStrengthMap.height,
                data: new Uint8Array(z.patternStrengthMap.data),
            } : null,
        }));
        if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'loaded config');
        selectedZoneIndex = 0;
        // Restore nextLinkGroupId to avoid collisions
        const maxLinkId = zones.reduce((max, z) => {
            if (z.linkGroup) {
                const n = parseInt(z.linkGroup.replace('link_', '')) || 0;
                return Math.max(max, n);
            }
            return max;
        }, 0);
        if (maxLinkId >= nextLinkGroupId) nextLinkGroupId = maxLinkId + 1;
        renderZones();
        if (typeof renderZoneDetail === 'function' && zones.length > 0) renderZoneDetail(selectedZoneIndex);
    }
    // Decal restore disabled - future feature
    // Restore imported spec map (merge mode)
    if (cfg.importedSpecMapPath) {
        importedSpecMapPath = cfg.importedSpecMapPath;
        try { if (typeof window !== 'undefined') window.importedSpecMapPath = cfg.importedSpecMapPath; } catch (e) {}
        const status = document.getElementById('importSpecMapStatus');
        if (status) {
            const fname = cfg.importedSpecMapPath.split('/').pop().split('\\').pop();
            status.innerHTML = `<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active · Layer 0</span> — ${escapeHtml(fname)}`;
        }
        const btn = document.getElementById('btnClearSpecMap');
        if (btn) btn.disabled = false;
        const specBanner = document.getElementById('specFromShokkBanner');
        const specLabel = document.getElementById('specFromShokkLabel');
        if (specBanner) {
            specBanner.style.display = 'block';
            if (specLabel) specLabel.textContent = fname + ' — zones paint on top. Render uses this spec.';
        }
    }
    // Restore spec channel visualizer state
    if (cfg.activeSpecChannel && cfg.activeSpecChannel !== 'all') {
        setSpecChannel(cfg.activeSpecChannel);
    }
}

// SHOKK / templates: session round-trip (same shape as getConfig/loadConfigFromObj)
function getSessionConfig() {
    return getConfig();
}

function applySessionConfig(cfg) {
    if (cfg && (cfg.zones || cfg.driverName !== undefined)) {
        loadConfigFromObj(cfg);
    }
}

function saveConfig() {
    const cfg = getConfig();
    const json = JSON.stringify(cfg, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_paintbooth_config_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast('Config saved!');
}

// ===== SHAREABLE PAINT PRESETS (.shokker files) =====
function exportPreset() {
    const driverName = (document.getElementById('driverName')?.value || '').trim() || 'Unknown';
    const carName = (document.getElementById('carName')?.value || '').trim() || 'Unknown Car';
    const presetName = prompt('Preset name:', `${driverName} - ${carName}`);
    if (!presetName) return;

    const preset = {
        _shokker_preset: true,
        version: "1.0",
        name: presetName,
        author: driverName,
        car: carName,
        created: new Date().toISOString(),
        description: buildPresetDescription(),
        zones: zones.map(z => ({
            name: z.name,
            base: z.base,
            pattern: z.pattern,
            finish: z.finish,
            intensity: z.intensity,
            customSpec: z.customSpec != null ? z.customSpec : undefined,
            customPaint: z.customPaint != null ? z.customPaint : undefined,
            customBright: z.customBright != null ? z.customBright : undefined,
            color: z.color,
            colorMode: z.colorMode,
            pickerColor: z.pickerColor,
            pickerTolerance: z.pickerTolerance,
            colors: z.colors || [],
            // 2026-04-21 HEENAN OVERNIGHT iter 8: `||` → `??` on numeric/
            // boolean persistence fields in the preset EXPORT path. Pre-fix,
            // a painter who had `scale: 0` (degenerate but legitimate) would
            // get `scale: 1.0` serialized into the shareable .shokker file.
            // Arrays (patternStack etc.) stay on `||` because an empty array
            // is legitimately equivalent to a missing field on this path.
            scale: z.scale ?? 1.0,
            rotation: z.rotation ?? 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternOffsetX: z.patternOffsetX ?? 0.5,
            patternOffsetY: z.patternOffsetY ?? 0.5,
            patternStack: z.patternStack || [],
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
            wear: z.wear ?? 0,
            muted: z.muted ?? false,
            // Region masks are intentionally excluded - they're car-specific
        })),
        settings: {
            wearLevel: parseInt(document.getElementById('wearSlider')?.value || '0', 10),
            dualSpec: document.getElementById('dualSpecCheckbox')?.checked || false,
            nightBoost: parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7'),
        },
        finishCount: zones.filter(z => z.base || z.finish).length,
        colorCount: zones.filter(z => z.color !== null || z.colorMode === 'multi').length,
    };

    const json = JSON.stringify(preset, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const safeName = presetName.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_');
    a.download = `${safeName}.shokker`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast(`Preset exported: ${presetName}`);
}

function buildPresetDescription() {
    return zones.map(z => {
        let finish = '';
        if (z.finish) {
            const mono = MONOLITHICS.find(m => m.id === z.finish);
            finish = mono ? mono.name : z.finish;
        } else if (z.base) {
            const b = BASES.find(b => b.id === z.base);
            const p = z.pattern && z.pattern !== 'none' ? PATTERNS.find(p => p.id === z.pattern) : null;
            finish = b ? b.name : z.base;
            if (p) finish += ' + ' + p.name;
        }
        return `${z.name}: ${finish || 'No finish'}`;
    }).join(' | ');
}

function importPreset() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.shokker,.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                if (data._shokker_preset) {
                    applyPreset(data);
                } else if (data.zones) {
                    // Fallback: it's a regular config file
                    loadConfigFromObj(data);
                    showToast('Loaded as config (not a preset file)');
                } else {
                    throw new Error('Not a valid .shokker preset');
                }
            } catch (err) {
                showToast('Invalid preset file: ' + err.message, true);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

// 2026-04-21 HEENAN OVERNIGHT iter 1: renamed from `applyPreset(preset)` (which
// previously shadowed the gallery-ID-form applyPreset(presetId) at ~line 8801
// via JS function-declaration hoisting, silently deadening the gallery path).
// Now a clearly-named helper dispatched by the polymorphic `applyPreset(arg)`
// router below. Also: switched `||` → `??` on numeric/boolean persistence
// fields so a preset author who saved `pickerTolerance: 0`, `scale: 0`, etc.
// round-trips faithfully on recipient load.
function _applyPresetFromObject(preset) {
    // Show preset info before applying
    const info = `"${preset.name}"${preset.author ? ' by ' + preset.author : ''}\n${preset.zones.length} zones | ${preset.finishCount || '?'} finishes\n\nApply this preset? (Your current zones will be replaced)`;
    if (!confirm(info)) return;

    // Apply zones
    zones = preset.zones.map(z => ({
        id: _newZoneId(),
        name: z.name || 'Zone',
        color: z.color,
        base: z.base || null,
        pattern: z.pattern || 'none',
        finish: z.finish || null,
        intensity: z.intensity ?? '100',
        customSpec: z.customSpec != null ? z.customSpec : null,
        customPaint: z.customPaint != null ? z.customPaint : null,
        customBright: z.customBright != null ? z.customBright : null,
        colorMode: z.colorMode || 'none',
        pickerColor: z.pickerColor || '#3366ff',
        pickerTolerance: z.pickerTolerance ?? 40,
        colors: z.colors || [],
        regionMask: null, // Regions are car-specific, not imported
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        scale: z.scale ?? 1.0,
        patternOpacity: z.patternOpacity ?? 100,
        patternOffsetX: z.patternOffsetX ?? 0.5,
        patternOffsetY: z.patternOffsetY ?? 0.5,
        patternStack: z.patternStack || [],
        specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
        wear: z.wear ?? 0,
        muted: z.muted ?? false,
    }));
    if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'imported preset: ' + (preset.name || 'unnamed'));
    selectedZoneIndex = 0;

    // Apply settings if present
    if (preset.settings) {
        if (preset.settings.wearLevel !== undefined && document.getElementById('wearSlider')) {
            document.getElementById('wearSlider').value = preset.settings.wearLevel;
            updateWearDisplay(preset.settings.wearLevel);
        }
        if (preset.settings.dualSpec !== undefined && document.getElementById('dualSpecCheckbox')) {
            document.getElementById('dualSpecCheckbox').checked = preset.settings.dualSpec;
            toggleNightBoostSlider();
        }
        if (preset.settings.nightBoost !== undefined && document.getElementById('nightBoostSlider')) {
            document.getElementById('nightBoostSlider').value = preset.settings.nightBoost;
            document.getElementById('nightBoostVal').textContent = parseFloat(preset.settings.nightBoost).toFixed(2);
        }
    }

    renderZones();
    triggerPreviewRender();
    autoSave();
    showToast(`Preset loaded: "${preset.name}" - ${preset.zones.length} zones`);
}

function loadConfig() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const cfg = JSON.parse(ev.target.result);
                loadConfigFromObj(cfg);
                showToast('Config loaded!');
            } catch (err) {
                showToast('Invalid config file', true);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

// ===== AUTO-SAVE / AUTO-RESTORE =====
const AUTOSAVE_KEY = 'shokker_autosave';
let autosaveTimer = null;
let _autosavePendingChanges = 0;  // Count batched changes for smarter save timing
// Periodic auto-save every 60 seconds as safety net (in addition to change-triggered saves)
setInterval(() => {
    try {
        const cfg = typeof getConfig === 'function' ? getConfig() : null;
        if (cfg && cfg.zones && cfg.zones.length > 0) {
            cfg._autosave_time = Date.now();
            localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(cfg));
        }
    } catch (e) { /* ignore */ }
}, 60000);

function autoSave() {
    // Debounce: batch changes within 500ms window before saving
    _autosavePendingChanges++;
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
        try {
            const cfg = getConfig();
            cfg._autosave_time = Date.now();
            const json = JSON.stringify(cfg);
            // Guard against localStorage quota (typically 5-10MB)
            if (json.length > 4 * 1024 * 1024) {
                console.warn('[SPB] Auto-save payload too large (' + Math.round(json.length / 1024) + 'KB), skipping');
                return;
            }
            localStorage.setItem(AUTOSAVE_KEY, json);
            const badge = document.getElementById('autosaveBadge');
            if (badge) {
                badge.textContent = 'Auto-saved (' + _autosavePendingChanges + ' changes)';
                badge.style.opacity = '1';
                setTimeout(() => { badge.style.opacity = '0.4'; }, 1500);
            }
            _autosavePendingChanges = 0;
        } catch (e) {
            if (e.name === 'QuotaExceededError') {
                showToast('Auto-save failed: localStorage full. Export your config to free space.', true);
            }
            // Other errors silently ignored
        }
    }, 500);
}

// BUG #72 (Owen, HIGH): `autoSave()` uses a 500ms debounce, so calling it
// from a `beforeunload` / `pagehide` handler schedules a timer that never
// fires — the tab unloads first and up to 500ms of batched painter work
// is silently lost. This synchronous helper bypasses the debounce and
// writes immediately. It also cancels the pending debounced save so we
// don't double-write.
function flushAutoSave() {
    try {
        if (autosaveTimer) { clearTimeout(autosaveTimer); autosaveTimer = null; }
        if (typeof getConfig !== 'function') return;
        const cfg = getConfig();
        if (!cfg || !cfg.zones || cfg.zones.length === 0) return;
        cfg._autosave_time = Date.now();
        const json = JSON.stringify(cfg);
        if (json.length > 4 * 1024 * 1024) return; // quota guard, same as autoSave
        localStorage.setItem(AUTOSAVE_KEY, json);
        _autosavePendingChanges = 0;
    } catch (e) { /* swallow — unload path, no painter to notify */ }
}
window.flushAutoSave = flushAutoSave;

// Default PSD to auto-load on FIRST RUN (when no autosave exists yet)
const SPB_DEFAULT_PSD = 'C:/1Shokker Paint Car Examples/Shokker Paint Booth Chevy Truck PSD.psd';
const SPB_LAST_FILE_KEY = 'spb_last_paint_file';  // Tracks last loaded file across sessions

function _spbReadStoredLastFile() {
    try {
        return (localStorage.getItem(SPB_LAST_FILE_KEY) || '').trim();
    } catch (e) {
        return '';
    }
}

function _spbGetPreferredRestorePaintFile(cfg) {
    const cfgSource = (cfg && typeof cfg.sourcePaintFile === 'string') ? cfg.sourcePaintFile.trim() : '';
    const storedLastFile = _spbReadStoredLastFile();
    const uiPaintFile = (cfg && typeof cfg.paintFile === 'string') ? cfg.paintFile.trim() : '';
    return cfgSource || storedLastFile || uiPaintFile || SPB_DEFAULT_PSD;
}

function _spbSetPaintHeaderPath(path) {
    const pathField = document.getElementById('paintFile');
    if (pathField && path) pathField.value = path;
}

function _spbRestorePaintFile(path) {
    const normalizedPath = (path || '').trim();
    if (!normalizedPath) return false;
    _spbSetPaintHeaderPath(normalizedPath);
    if (typeof validatePaintPath === 'function') validatePaintPath();
    const ok = _spbAutoLoadPaintFile(normalizedPath);
    if (ok) {
        try { localStorage.setItem(SPB_LAST_FILE_KEY, normalizedPath); } catch (e) {}
    }
    return ok;
}

// Smart auto-loader: detects PSD vs TGA/image and calls the right loader
function _spbAutoLoadPaintFile(filePath) {
    if (!filePath) return false;
    const ext = (filePath.split('.').pop() || '').toLowerCase();
    if (ext === 'psd') {
        if (typeof window.importPSDFromPath === 'function') {
            try { window.importPSDFromPath(filePath); return true; } catch (e) {}
        }
        // Fallback: open import dialog at this path
        return false;
    }
    // TGA / PNG / JPG / BMP path
    if (typeof window.loadPaintPreviewFromServer === 'function') {
        try { window.loadPaintPreviewFromServer(filePath); return true; } catch (e) {}
    }
    if (typeof window.loadPaintImageFromPath === 'function') {
        try { window.loadPaintImageFromPath(filePath); return true; } catch (e) {}
    }
    return false;
}
window._spbAutoLoadPaintFile = _spbAutoLoadPaintFile;

function autoRestore() {
    try {
        const raw = localStorage.getItem(AUTOSAVE_KEY);

        // ── FIRST-RUN: no saved session yet → load the default Chevy Silverado PSD ──
        if (!raw) {
            const defaultPath = _spbGetPreferredRestorePaintFile(null);
            _spbSetPaintHeaderPath(defaultPath);
            // Auto-load after server is ready
            setTimeout(() => {
                const ok = _spbRestorePaintFile(defaultPath);
                if (ok) {
                    showToast(`First launch — loading default: ${defaultPath.split(/[/\\]/).pop()}`, false);
                } else {
                    showToast('Welcome — click Import PSD or Load TGA to get started', false);
                }
            }, 1500);
            return false;
        }

        const cfg = JSON.parse(raw);
        if (!cfg || !cfg.zones || cfg.zones.length === 0) {
            // Saved config exists but has no zones — still try to restore last paint file
            const lastFile = _spbGetPreferredRestorePaintFile(cfg);
            if (lastFile) {
                setTimeout(() => {
                    _spbRestorePaintFile(lastFile);
                }, 1500);
            }
            return false;
        }

        loadConfigFromObj(cfg);
        const age = cfg._autosave_time ? Math.round((Date.now() - cfg._autosave_time) / 1000) : 0;
        let ageStr;
        if (age < 60) ageStr = `${age}s ago`;
        else if (age < 3600) ageStr = `${Math.round(age / 60)}m ago`;
        else ageStr = `${Math.round(age / 3600)}h ago`;
        showToast(`Session restored (saved ${ageStr}) — ${cfg.zones.length} zones, ${cfg.driverName || 'no driver'} — reloading paint...`);

        // Validate path and auto-load paint file after server is ready
        setTimeout(() => {
            const savedPath = _spbGetPreferredRestorePaintFile(cfg);
            if (savedPath) {
                _spbRestorePaintFile(savedPath);
            }
        }, 1500);
        return true;
    } catch (e) {
        console.warn('[autoRestore] failed:', e);
        return false;
    }
}

// ===== ZONE VALIDATION BEFORE RENDER =====
// Returns array of warning strings for zones that may not render correctly
function validateZonesBeforeRender() {
    const warnings = [];
    zones.forEach(function(z, i) {
        if (z.muted) return; // Skip muted zones
        // Warn: zone has no finish assigned
        if (!z.base && !z.finish) {
            warnings.push('Zone ' + (i + 1) + ' "' + z.name + '": no finish assigned');
        }
        // Warn: zone has no color and no region mask
        const hasColor = z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special';
        const hasRegion = z.regionMask && z.regionMask.some(function(v) { return v > 0; });
        if (!hasColor && !hasRegion) {
            warnings.push('Zone ' + (i + 1) + ' "' + z.name + '": no color or region defined (zone will not apply to any pixels)');
        }
        // Warn: zone has finish but no color coverage
        if ((z.base || z.finish) && !hasColor && !hasRegion) {
            warnings.push('Zone ' + (i + 1) + ' "' + z.name + '": finish set but no pixels targeted');
        }
    });
    return warnings;
}

// Show validation warnings in a toast if any exist
function showZoneValidationWarnings() {
    const warnings = validateZonesBeforeRender();
    if (warnings.length > 0) {
        const msg = warnings.length === 1 ? warnings[0] : warnings.length + ' zone warnings: ' + warnings.slice(0, 3).join('; ') + (warnings.length > 3 ? '...' : '');
        showToast(msg, true);
    }
    return warnings;
}

// ===== ZONE STATISTICS =====
// Returns stats about zone coverage
function getZoneStatistics() {
    const pc = document.getElementById('paintCanvas');
    const totalPixels = pc ? (pc.width * pc.height) : 0;
    const stats = {
        totalZones: zones.length,
        activeZones: zones.filter(function(z) { return !z.muted; }).length,
        mutedZones: zones.filter(function(z) { return z.muted; }).length,
        zonesWithFinish: zones.filter(function(z) { return z.base || z.finish; }).length,
        zonesWithColor: zones.filter(function(z) { return z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special'; }).length,
        zonesWithRegion: 0,
        totalRegionPixels: 0,
        coveragePercent: 0,
        perZone: [],
    };
    zones.forEach(function(z, i) {
        const hasRegion = z.regionMask && z.regionMask.some(function(v) { return v > 0; });
        let regionPixels = 0;
        if (hasRegion) {
            stats.zonesWithRegion++;
            regionPixels = z.regionMask.reduce(function(sum, v) { return sum + (v > 0 ? 1 : 0); }, 0);
            stats.totalRegionPixels += regionPixels;
        }
        stats.perZone.push({
            name: z.name,
            index: i,
            muted: z.muted,
            hasFinish: !!(z.base || z.finish),
            hasColor: z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special',
            hasRegion: hasRegion,
            regionPixels: regionPixels,
            regionPercent: totalPixels > 0 ? Math.round(regionPixels / totalPixels * 10000) / 100 : 0,
        });
    });
    stats.coveragePercent = totalPixels > 0 ? Math.round(stats.totalRegionPixels / totalPixels * 10000) / 100 : 0;
    return stats;
}

// ============================================================
// ZONE WORKFLOW IMPROVEMENTS (v6.2 — Platinum)
// ============================================================
// Bulk operations, presets, copy/paste, search, validation,
// link groups, smart suggestions, locks, and ergonomics.
// All additions are non-invasive — they extend, never replace.
// ============================================================

// ---------- IMPROVEMENT 01: getZoneStatus — single-source-of-truth status badge ----------
/** Returns 'ok' | 'no_finish' | 'no_pixels' | 'muted' | 'incomplete'. */
function getZoneStatus(zone) {
    if (!zone) return 'no_finish';
    if (zone.muted) return 'muted';
    const hasFinish = !!(zone.base || zone.finish);
    const hasColor = zone.color !== null || zone.colorMode === 'multi' || zone.colorMode === 'special';
    const hasRegion = zone.regionMask && zone.regionMask.some(function(v){ return v > 0; });
    if (!hasFinish && !hasColor && !hasRegion) return 'incomplete';
    if (!hasFinish) return 'no_finish';
    if (!hasColor && !hasRegion) return 'no_pixels';
    return 'ok';
}

// ---------- IMPROVEMENT 02: getZoneStatusBadgeHTML — small dot/badge HTML ----------
function getZoneStatusBadgeHTML(zone) {
    const s = getZoneStatus(zone);
    const map = {
        ok:         { color: '#22c55e', icon: '\u2713', label: 'Will render' },
        no_finish:  { color: '#ff8c1a', icon: '\u26A0', label: 'No finish assigned' },
        no_pixels:  { color: '#ff8c1a', icon: '\u26A0', label: 'No color/region — zone targets nothing' },
        muted:      { color: '#666',    icon: '\u{1F6AB}', label: 'Muted (excluded from render)' },
        incomplete: { color: '#888',    icon: '\u00B7', label: 'Empty zone — set color & finish' },
    };
    const m = map[s] || map.incomplete;
    return '<span class="zone-status-badge" data-status="' + s + '" title="' + m.label +
           '" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + m.color +
           ';margin-right:3px;vertical-align:middle;box-shadow:0 0 4px ' + m.color + '88;"></span>';
}
if (typeof window !== 'undefined') { window.getZoneStatus = getZoneStatus; window.getZoneStatusBadgeHTML = getZoneStatusBadgeHTML; }

// ---------- IMPROVEMENT 03: getZoneDiagnostic — human-readable explanation ----------
function getZoneDiagnostic(zone) {
    if (!zone) return 'Zone is missing.';
    if (zone.muted) return 'Zone is muted. Click the eye icon to unmute.';
    const hasFinish = !!(zone.base || zone.finish);
    const hasColor = zone.color !== null || zone.colorMode === 'multi' || zone.colorMode === 'special';
    const hasRegion = zone.regionMask && zone.regionMask.some(function(v){ return v > 0; });
    if (!hasFinish && !hasColor && !hasRegion) return 'Empty zone — pick a base finish AND a color (or draw a region).';
    if (!hasFinish) return 'No finish assigned. Pick a base material from the BASE row to make this zone visible.';
    if (!hasColor && !hasRegion) return 'No color or region defined — this zone will not affect any pixels. Use Pick Color or Draw Region.';
    return 'Zone is ready to render.';
}
if (typeof window !== 'undefined') { window.getZoneDiagnostic = getZoneDiagnostic; }

// ---------- IMPROVEMENT 04: toggleLock — lock individual zone properties ----------
function toggleLock(index, propKey) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    const allowed = { lockBase: 1, lockPattern: 1, lockIntensity: 1, lockColor: 1, lockOverlays: 1 };
    if (!allowed[propKey]) return;
    zones[index][propKey] = !zones[index][propKey];
    pushZoneUndo((zones[index][propKey] ? 'Lock ' : 'Unlock ') + propKey.replace('lock','').toLowerCase());
    renderZones();
    showToast((zones[index][propKey] ? 'Locked: ' : 'Unlocked: ') + propKey.replace('lock','').toLowerCase() + ' on ' + zones[index].name);
}
if (typeof window !== 'undefined') { window.toggleLock = toggleLock; }

// ---------- IMPROVEMENT 05: zoneCoverageEstimate — % of canvas this zone covers ----------
function zoneCoverageEstimate(index) {
    const zone = zones[index]; if (!zone) return 0;
    const pc = document.getElementById('paintCanvas');
    if (!pc) return 0;
    const totalPixels = pc.width * pc.height;
    if (!totalPixels) return 0;
    if (zone.regionMask) {
        let count = 0;
        for (let i = 0; i < zone.regionMask.length; i++) if (zone.regionMask[i] > 0) count++;
        return Math.round(count / totalPixels * 1000) / 10;
    }
    if (zone.colorMode === 'special' && zone.color === 'everything') return 100;
    // Color-based: rough estimate by sampling paintImageData
    if (paintImageData && (zone.colorMode === 'picker' || zone.colorMode === 'multi')) {
        const data = paintImageData.data;
        const targets = zone.colorMode === 'multi' ? (zone.colors || []) : [{ color_rgb: (zone.color && zone.color.color_rgb) || [128,128,128], tolerance: zone.pickerTolerance ?? 40 }];
        let hits = 0, sampled = 0;
        const stride = 16; // sample every 16 pixels for speed
        for (let i = 0; i < data.length; i += 4 * stride) {
            sampled++;
            const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
            if (a < 8) continue;
            for (let t = 0; t < targets.length; t++) {
                const tc = targets[t]; const rgb = tc.color_rgb || [128,128,128]; const tol = tc.tolerance || 40;
                if (Math.abs(r - rgb[0]) <= tol && Math.abs(g - rgb[1]) <= tol && Math.abs(b - rgb[2]) <= tol) { hits++; break; }
            }
        }
        return sampled > 0 ? Math.round(hits / sampled * 1000) / 10 : 0;
    }
    return 0;
}
if (typeof window !== 'undefined') { window.zoneCoverageEstimate = zoneCoverageEstimate; }

// ---------- IMPROVEMENT 06: bulk zone operations ----------
const _bulkSelectedZones = new Set();
function toggleBulkSelect(index) {
    if (_bulkSelectedZones.has(index)) _bulkSelectedZones.delete(index);
    else _bulkSelectedZones.add(index);
    renderZones();
}
function clearBulkSelection() { _bulkSelectedZones.clear(); renderZones(); }
function bulkSelectAll() { _bulkSelectedZones.clear(); for (let i = 0; i < zones.length; i++) _bulkSelectedZones.add(i); renderZones(); }
function bulkApplyFinish(finishId) {
    if (_bulkSelectedZones.size === 0) { showToast('No zones selected for bulk action', true); return; }
    pushZoneUndo('Bulk apply finish to ' + _bulkSelectedZones.size + ' zones');
    const isBase = (typeof BASES !== 'undefined') && BASES.find(b => b.id === finishId);
    const isMono = (typeof MONOLITHICS !== 'undefined') && MONOLITHICS.find(m => m.id === finishId);
    _bulkSelectedZones.forEach(function(i) {
        const z = zones[i]; if (!z) return;
        if (z.lockBase) return;
        if (isBase) { z.base = finishId; z.finish = null; }
        else if (isMono) { z.finish = finishId; z.base = null; }
    });
    renderZones(); triggerPreviewRender();
    showToast('Bulk applied finish to ' + _bulkSelectedZones.size + ' zones');
}
function bulkSetIntensity(value) {
    if (_bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
    pushZoneUndo('Bulk set intensity');
    _bulkSelectedZones.forEach(function(i) { if (zones[i] && !zones[i].lockIntensity) zones[i].intensity = value; });
    renderZones(); triggerPreviewRender();
    showToast('Bulk set intensity = ' + value + ' on ' + _bulkSelectedZones.size + ' zones');
}
function bulkSetTolerance(tolerance) {
    if (_bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
    pushZoneUndo('Bulk set tolerance');
    _bulkSelectedZones.forEach(function(i) {
        const z = zones[i]; if (!z) return;
        z.pickerTolerance = tolerance;
        if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) z.color.tolerance = tolerance;
        if (Array.isArray(z.colors)) z.colors.forEach(c => { c.tolerance = tolerance; });
    });
    renderZones(); triggerPreviewRender();
    showToast('Bulk set tolerance = ' + tolerance + ' on ' + _bulkSelectedZones.size + ' zones');
}
function bulkMute() {
    if (_bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
    pushZoneUndo('Bulk mute');
    _bulkSelectedZones.forEach(function(i) { if (zones[i]) zones[i].muted = true; });
    renderZones(); triggerPreviewRender();
}
function bulkUnmute() {
    if (_bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
    pushZoneUndo('Bulk unmute');
    _bulkSelectedZones.forEach(function(i) { if (zones[i]) zones[i].muted = false; });
    renderZones(); triggerPreviewRender();
}
function bulkDelete() {
    if (_bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
    if (_bulkSelectedZones.size >= zones.length) { showToast('Cannot delete all zones — keep at least one', true); return; }
    if (!confirm('Delete ' + _bulkSelectedZones.size + ' selected zones?')) return;
    pushZoneUndo('Bulk delete ' + _bulkSelectedZones.size + ' zones');
    const indices = Array.from(_bulkSelectedZones).sort(function(a,b){ return b-a; });
    // 2026-04-18 MARATHON bug #35 (MED): pre-fix, bulkDelete only clamped
    // selectedZoneIndex to zones.length - 1. If the selection was a zone
    // AFTER some of the deleted indices, the index drifted to point at a
    // different zone. Now we compute the exact shift: count how many
    // deleted indices are strictly less than selectedZoneIndex and
    // subtract. Also handle the case where the selection itself is
    // being deleted (fall back to max 0).
    const selDeleted = _bulkSelectedZones.has(selectedZoneIndex);
    const deletedBefore = indices.filter(i => i < selectedZoneIndex).length;
    indices.forEach(function(i) { zones.splice(i, 1); });
    _bulkSelectedZones.clear();
    if (selDeleted) {
        // Selection was in the delete set — shift back and clamp.
        selectedZoneIndex = Math.max(0, Math.min(selectedZoneIndex - deletedBefore, zones.length - 1));
    } else {
        selectedZoneIndex = Math.max(0, Math.min(selectedZoneIndex - deletedBefore, zones.length - 1));
    }
    renderZones(); triggerPreviewRender();
    showToast('Bulk deleted ' + indices.length + ' zones');
}
if (typeof window !== 'undefined') {
    window.toggleBulkSelect = toggleBulkSelect; window.clearBulkSelection = clearBulkSelection; window.bulkSelectAll = bulkSelectAll;
    window.bulkApplyFinish = bulkApplyFinish; window.bulkSetIntensity = bulkSetIntensity; window.bulkSetTolerance = bulkSetTolerance;
    window.bulkMute = bulkMute; window.bulkUnmute = bulkUnmute; window.bulkDelete = bulkDelete;
}

// ---------- IMPROVEMENT 07: zone presets — save/load named zone configurations ----------
const ZONE_PRESETS_KEY = 'shokker_zone_presets';
function _loadZonePresets() { try { return JSON.parse(localStorage.getItem(ZONE_PRESETS_KEY) || '[]'); } catch (e) { return []; } }
function _saveZonePresetsList(arr) { try { localStorage.setItem(ZONE_PRESETS_KEY, JSON.stringify(arr)); } catch (e) {} }
function saveZonePreset(presetName) {
    if (!presetName) presetName = prompt('Name this preset (e.g. "Kyle\'s Setup"):');
    if (!presetName || !presetName.trim()) return;
    const presets = _loadZonePresets();
    const snapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null, spatialMask: null }))));
    const entry = { name: presetName.trim(), savedAt: Date.now(), zoneCount: zones.length, snapshot: snapshot };
    const existingIdx = presets.findIndex(p => p.name === entry.name);
    if (existingIdx >= 0) { if (!confirm('Overwrite existing preset "' + entry.name + '"?')) return; presets[existingIdx] = entry; }
    else presets.push(entry);
    _saveZonePresetsList(presets);
    showToast('Saved preset: ' + entry.name);
}
function loadZonePreset(presetName) {
    const presets = _loadZonePresets();
    const p = presets.find(p => p.name === presetName);
    if (!p) { showToast('Preset not found: ' + presetName, true); return; }
    if (!confirm('Replace current ' + zones.length + ' zones with preset "' + p.name + '" (' + p.zoneCount + ' zones)?')) return;
    pushZoneUndo('Load preset: ' + p.name);
    zones.length = 0;
    p.snapshot.forEach(function(z) {
        const restored = _ensureZoneShape(z, { includeRegionMask: false, includeSpatialMask: false });
        restored.regionMask = null;
        restored.spatialMask = null;
        zones.push(restored);
    });
    selectedZoneIndex = 0;
    renderZones(); triggerPreviewRender();
    showToast('Loaded preset: ' + p.name + ' (' + p.zoneCount + ' zones)');
}
function deleteZonePreset(presetName) {
    if (!confirm('Delete preset "' + presetName + '"?')) return;
    const presets = _loadZonePresets().filter(p => p.name !== presetName);
    _saveZonePresetsList(presets);
    showToast('Deleted preset: ' + presetName);
}
function listZonePresets() { return _loadZonePresets(); }
if (typeof window !== 'undefined') {
    window.saveZonePreset = saveZonePreset; window.loadZonePreset = loadZonePreset;
    window.deleteZonePreset = deleteZonePreset; window.listZonePresets = listZonePresets;
}

// ---------- IMPROVEMENT 08: duplicate-with-hue-offset — clone with shifted hue ----------
function duplicateZoneWithHueOffset(index, hueShiftDeg) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    if (typeof hueShiftDeg !== 'number') {
        const v = prompt('Hue shift in degrees (-180 to 180):', '60');
        if (v === null) return;
        hueShiftDeg = parseFloat(v);
        if (isNaN(hueShiftDeg)) { showToast('Invalid hue value', true); return; }
    }
    pushZoneUndo('Duplicate with hue offset ' + hueShiftDeg + 'deg');
    const src = zones[index];
    const clone = _cloneZoneState(src, {
        preserveId: false,
        includeRegionMask: true,
        includeSpatialMask: true,
        includePatternStrengthMap: true,
    });
    clone.name = src.name + ' (hue+' + Math.round(hueShiftDeg) + ')';
    // Shift the picker color
    function shiftHex(hex) {
        if (!hex || !/^#[0-9A-Fa-f]{6}$/.test(hex)) return hex;
        const r = parseInt(hex.substr(1,2),16) / 255, g = parseInt(hex.substr(3,2),16) / 255, b = parseInt(hex.substr(5,2),16) / 255;
        const max = Math.max(r,g,b), min = Math.min(r,g,b);
        let h = 0, s = 0, l = (max+min)/2;
        if (max !== min) {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        h = (h * 360 + hueShiftDeg + 360) % 360 / 360;
        function hue2rgb(p,q,t){ if(t<0)t+=1; if(t>1)t-=1; if(t<1/6)return p+(q-p)*6*t; if(t<1/2)return q; if(t<2/3)return p+(q-p)*(2/3-t)*6; return p; }
        const q = l < 0.5 ? l * (1+s) : l + s - l*s, p = 2*l - q;
        const nr = Math.round(hue2rgb(p,q,h+1/3) * 255);
        const ng = Math.round(hue2rgb(p,q,h) * 255);
        const nb = Math.round(hue2rgb(p,q,h-1/3) * 255);
        return '#' + [nr,ng,nb].map(x => x.toString(16).padStart(2,'0')).join('').toUpperCase();
    }
    if (clone.pickerColor) clone.pickerColor = shiftHex(clone.pickerColor);
    if (clone.color && typeof clone.color === 'object' && !Array.isArray(clone.color) && clone.color.color_rgb) {
        const newHex = shiftHex('#' + clone.color.color_rgb.map(c => c.toString(16).padStart(2,'0')).join(''));
        const r = parseInt(newHex.substr(1,2),16), g = parseInt(newHex.substr(3,2),16), b = parseInt(newHex.substr(5,2),16);
        clone.color = { color_rgb: [r,g,b], tolerance: clone.color.tolerance || 40 };
    }
    if (Array.isArray(clone.colors)) {
        clone.colors = clone.colors.map(function(c) {
            const newHex = shiftHex(c.hex || '#888888');
            const r = parseInt(newHex.substr(1,2),16), g = parseInt(newHex.substr(3,2),16), b = parseInt(newHex.substr(5,2),16);
            return { color_rgb: [r,g,b], tolerance: c.tolerance || 40, hex: newHex };
        });
    }
    // Also shift the base hue offset stored on the zone
    clone.baseHueOffset = ((clone.baseHueOffset || 0) + hueShiftDeg + 540) % 360 - 180;
    zones.splice(index + 1, 0, clone);
    selectedZoneIndex = index + 1;
    renderZones();
    showToast('Duplicated with hue +' + Math.round(hueShiftDeg) + '\u00B0');
}
if (typeof window !== 'undefined') { window.duplicateZoneWithHueOffset = duplicateZoneWithHueOffset; }

// ---------- IMPROVEMENT 09: link-group helpers — propagate intensity/scale ----------
const LINK_INTENSITY_PROPS = ['intensity', 'patternOpacity', 'patternSpecMult', 'baseStrength', 'baseSpecStrength'];
function propagateIntensityToLinked(sourceIndex) {
    const z = zones[sourceIndex]; if (!z || !z.linkGroup) return;
    zones.forEach(function(other, i) {
        if (i === sourceIndex || other.linkGroup !== z.linkGroup) return;
        LINK_INTENSITY_PROPS.forEach(function(p) { if (z[p] !== undefined) other[p] = z[p]; });
    });
}
function unlinkAllZones() {
    if (!confirm('Unlink ALL zones from their groups?')) return;
    pushZoneUndo('Unlink all zones');
    zones.forEach(function(z) { delete z.linkGroup; });
    renderZones();
    showToast('All link groups removed');
}
if (typeof window !== 'undefined') { window.propagateIntensityToLinked = propagateIntensityToLinked; window.unlinkAllZones = unlinkAllZones; }

// ---------- IMPROVEMENT 10: zone copy/paste — clipboard for zone settings ----------
let _zoneClipboard = null;
function copyZoneToClipboard(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) index = selectedZoneIndex;
    const z = zones[index];
    if (!z) { showToast('No zone to copy', true); return; }
    _zoneClipboard = _cloneZoneState({ ...z, colors: z.colors || [] }, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
    });
    _zoneClipboard._copiedAt = Date.now();
    _zoneClipboard._copiedFromName = z.name;
    showToast('Copied "' + z.name + '" settings — Ctrl+Shift+V to paste');
}
function pasteZoneFromClipboard(index) {
    if (!_zoneClipboard) { showToast('Nothing in zone clipboard — copy a zone first', true); return; }
    if (typeof index !== 'number' || index < 0 || index >= zones.length) index = selectedZoneIndex;
    pushZoneUndo('Paste zone settings to "' + zones[index].name + '"');
    const target = zones[index];
    const preserveName = target.name;
    const preserveId = target.id;
    const preserveMask = target.regionMask;
    const preserveSpatial = target.spatialMask;
    const fresh = _cloneZoneState(_zoneClipboard, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
    });
    delete fresh._copiedAt; delete fresh._copiedFromName;
    Object.keys(fresh).forEach(function(k) { target[k] = fresh[k]; });
    target.id = preserveId;
    target.name = preserveName;
    target.regionMask = preserveMask;
    target.spatialMask = preserveSpatial;
    renderZones(); triggerPreviewRender();
    showToast('Pasted settings from "' + _zoneClipboard._copiedFromName + '" \u2192 "' + target.name + '"');
}
function pasteZoneAsNew() {
    if (!_zoneClipboard) { showToast('Nothing in zone clipboard', true); return; }
    if (zones.length >= MAX_ZONES) { showToast('Zone limit reached', true); return; }
    pushZoneUndo('Paste as new zone');
    const fresh = _cloneZoneState(_zoneClipboard, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
    });
    delete fresh._copiedAt;
    fresh.name = (_zoneClipboard._copiedFromName || 'Zone') + ' (paste)';
    delete fresh._copiedFromName;
    fresh.regionMask = null;
    fresh.spatialMask = null;
    zones.push(fresh);
    selectedZoneIndex = zones.length - 1;
    renderZones(); triggerPreviewRender();
    showToast('Pasted as new zone: ' + fresh.name);
}
if (typeof window !== 'undefined') {
    window.copyZoneToClipboard = copyZoneToClipboard;
    window.pasteZoneFromClipboard = pasteZoneFromClipboard;
    window.pasteZoneAsNew = pasteZoneAsNew;
}

// ---------- IMPROVEMENT 11: zone export/import as standalone JSON ----------
function exportSingleZone(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) index = selectedZoneIndex;
    const z = zones[index]; if (!z) return;
    const data = { __spbZone: 1, version: 1, exportedAt: Date.now(), zone: { ...z, regionMask: null, spatialMask: null } };
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const safeName = (z.name || 'zone').replace(/[^a-z0-9_-]+/gi, '_').toLowerCase();
    a.download = 'spb_zone_' + safeName + '_' + Date.now() + '.json';
    a.click(); URL.revokeObjectURL(a.href);
    showToast('Exported zone: ' + z.name);
}
function importZoneFromFile() {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = '.json,application/json';
    inp.onchange = function(e) {
        const f = e.target.files && e.target.files[0]; if (!f) return;
        const reader = new FileReader();
        reader.onload = function(ev) {
            try {
                const data = JSON.parse(ev.target.result);
                if (!data || !data.__spbZone || !data.zone) { showToast('Not a valid SPB zone JSON', true); return; }
                if (zones.length >= MAX_ZONES) { showToast('Zone limit reached', true); return; }
                pushZoneUndo('Import zone');
                const z = _cloneZoneState(data.zone, {
                    preserveId: false,
                    includeRegionMask: false,
                    includeSpatialMask: false,
                    includePatternStrengthMap: true,
                });
                z.regionMask = null;
                z.spatialMask = null;
                z.name = (z.name || 'Imported Zone') + ' (imported)';
                zones.push(z);
                selectedZoneIndex = zones.length - 1;
                renderZones(); triggerPreviewRender();
                showToast('Imported zone: ' + z.name);
            } catch (err) { showToast('Import failed: ' + err.message, true); }
        };
        reader.readAsText(f);
    };
    inp.click();
}
if (typeof window !== 'undefined') { window.exportSingleZone = exportSingleZone; window.importZoneFromFile = importZoneFromFile; }

// ---------- IMPROVEMENT 12: zone search/filter ----------
let _zoneSearchQuery = '';
function setZoneSearchQuery(q) {
    _zoneSearchQuery = (q || '').toLowerCase().trim();
    // Apply CSS filter to zone cards
    const cards = document.querySelectorAll('#zoneList .zone-card');
    cards.forEach(function(card, i) {
        if (!_zoneSearchQuery) { card.style.display = ''; return; }
        const z = zones[i]; if (!z) return;
        const haystack = [z.name, z.base, z.finish, z.pattern, z.color, z.colorMode, z.pickerColor].filter(Boolean).join(' ').toLowerCase();
        card.style.display = haystack.includes(_zoneSearchQuery) ? '' : 'none';
    });
}
function clearZoneSearch() { _zoneSearchQuery = ''; const inp = document.getElementById('zoneSearchInput'); if (inp) inp.value = ''; setZoneSearchQuery(''); }
if (typeof window !== 'undefined') { window.setZoneSearchQuery = setZoneSearchQuery; window.clearZoneSearch = clearZoneSearch; }

// ---------- IMPROVEMENT 13: collapse-all / expand-all zones ----------
function collapseAllZones() {
    const cards = document.querySelectorAll('#zoneList .zone-card');
    cards.forEach(function(c) { c.classList.add('zone-card-collapsed'); c.classList.remove('expanded'); });
    showToast('All zones collapsed');
}
function expandAllZones() {
    const cards = document.querySelectorAll('#zoneList .zone-card');
    cards.forEach(function(c) { c.classList.remove('zone-card-collapsed'); c.classList.add('expanded'); });
    showToast('All zones expanded');
}
if (typeof window !== 'undefined') { window.collapseAllZones = collapseAllZones; window.expandAllZones = expandAllZones; }

// ---------- IMPROVEMENT 14: smart name suggestion based on finish ----------
function suggestZoneName(zone) {
    if (!zone) return 'Zone';
    const finishId = zone.finish || zone.base || '';
    const lookup = (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : []).find(m => m.id === finishId)
                || (typeof BASES !== 'undefined' ? BASES : []).find(b => b.id === finishId);
    const finishName = lookup ? lookup.name : finishId;
    const finishWord = (finishName || '').replace(/v\d+$/i, '').replace(/[_-]+/g, ' ').trim().split(/\s+/)[0] || '';
    const cap = finishWord ? (finishWord.charAt(0).toUpperCase() + finishWord.slice(1).toLowerCase()) : '';
    // Map common patterns
    const colorWord = (function(){
        if (zone.colorMode === 'quick' && zone.color) return String(zone.color).charAt(0).toUpperCase() + String(zone.color).slice(1);
        if (zone.colorMode === 'special' && zone.color === 'remaining') return 'Remainder';
        if (zone.colorMode === 'picker' && zone.pickerColor) return zone.pickerColor.toUpperCase();
        return '';
    })();
    const parts = [cap, colorWord, 'Zone'].filter(Boolean);
    return parts.slice(0, 2).join(' ') || 'Zone';
}
function autoNameZone(index) {
    const z = zones[index]; if (!z) return;
    const newName = suggestZoneName(z);
    if (!newName || newName === z.name) { showToast('No better name available', true); return; }
    pushZoneUndo('Auto-name zone');
    z.name = newName;
    renderZones();
    showToast('Renamed to "' + newName + '"');
}
function autoNameAllZones() {
    pushZoneUndo('Auto-name all zones');
    let renamed = 0;
    zones.forEach(function(z) {
        const n = suggestZoneName(z);
        if (n && n !== z.name && (z.base || z.finish)) { z.name = n; renamed++; }
    });
    renderZones();
    showToast('Auto-renamed ' + renamed + ' zones');
}
if (typeof window !== 'undefined') { window.suggestZoneName = suggestZoneName; window.autoNameZone = autoNameZone; window.autoNameAllZones = autoNameAllZones; }

// ---------- IMPROVEMENT 15: zone color tolerance presets ----------
function setTolerancePreset(index, preset) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const z = zones[index]; if (!z) return;
    const map = { tight: 5, default: 40, loose: 80 };
    const tol = map[preset]; if (!tol) return;
    pushZoneUndo('Set tolerance preset: ' + preset);
    z.pickerTolerance = tol;
    if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) z.color.tolerance = tol;
    if (Array.isArray(z.colors)) z.colors.forEach(function(c) { c.tolerance = tol; });
    renderZones(); triggerPreviewRender();
    showToast('Tolerance: ' + preset + ' (\u00B1' + tol + ')');
}
if (typeof window !== 'undefined') { window.setTolerancePreset = setTolerancePreset; }

// ---------- IMPROVEMENT 16: renumber zones after gaps (re-name "Zone N" entries) ----------
function renumberZones() {
    pushZoneUndo('Renumber zones');
    let counter = 1;
    zones.forEach(function(z) {
        if (/^Zone \d+$/.test(z.name || '')) { z.name = 'Zone ' + counter; counter++; }
    });
    renderZones();
    showToast('Renumbered generic zones (' + (counter - 1) + ' updated)');
}
if (typeof window !== 'undefined') { window.renumberZones = renumberZones; }

// ---------- IMPROVEMENT 17: smarter undo coalescing — explicit drag begin/end ----------
let _undoCoalesceTimer = null;
let _undoCoalesceLabel = null;
function pushZoneUndoCoalesced(label, windowMs) {
    windowMs = windowMs || 1000;
    if (_undoCoalesceTimer && _undoCoalesceLabel === label) {
        clearTimeout(_undoCoalesceTimer);
        _undoCoalesceTimer = setTimeout(function() {
            _undoCoalesceTimer = null; _undoCoalesceLabel = null;
        }, windowMs);
        return; // Skip — already a recent push with same label
    }
    pushZoneUndo(label);
    _undoCoalesceLabel = label;
    _undoCoalesceTimer = setTimeout(function() { _undoCoalesceTimer = null; _undoCoalesceLabel = null; }, windowMs);
}
if (typeof window !== 'undefined') { window.pushZoneUndoCoalesced = pushZoneUndoCoalesced; }

// ---------- IMPROVEMENT 18: per-zone undo (history scoped to one zone) ----------
const _perZoneUndoStacks = {};
function pushPerZoneUndo(index, label) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    if (!_perZoneUndoStacks[index]) _perZoneUndoStacks[index] = [];
    _perZoneUndoStacks[index].push({ label: label, timestamp: Date.now(), snapshot: JSON.parse(JSON.stringify({ ...zones[index], regionMask: null })) });
    if (_perZoneUndoStacks[index].length > 20) _perZoneUndoStacks[index].shift();
}
function undoPerZone(index) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const stack = _perZoneUndoStacks[index]; if (!stack || !stack.length) { showToast('No per-zone history for this zone', true); return; }
    const entry = stack.pop();
    const mask = zones[index].regionMask;
    Object.assign(zones[index], entry.snapshot);
    zones[index].regionMask = mask;
    renderZones(); triggerPreviewRender();
    showToast('Per-zone undo: ' + entry.label);
}
if (typeof window !== 'undefined') { window.undoPerZone = undoPerZone; window.pushPerZoneUndo = pushPerZoneUndo; }

// ---------- IMPROVEMENT 19: Ctrl+Up/Down zone reorder shortcut + Ctrl+Shift+C/V copy/paste ----------
// SESSION ROUTER: bail on defaultPrevented.
document.addEventListener('keydown', function(e) {
    if (e.defaultPrevented) return;
    if (_isTextEntryTargetForGlobalUndo(e.target)) return;
    // Ctrl+Up = move zone up
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key === 'ArrowUp') {
        e.preventDefault();
        if (selectedZoneIndex > 0) moveZoneUp(selectedZoneIndex);
    }
    else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key === 'ArrowDown') {
        e.preventDefault();
        if (selectedZoneIndex < zones.length - 1) moveZoneDown(selectedZoneIndex);
    }
    // Ctrl+Shift+C = copy zone, Ctrl+Shift+V = paste zone
    else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'C' || e.key === 'c')) {
        e.preventDefault();
        copyZoneToClipboard(selectedZoneIndex);
    }
    else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'V' || e.key === 'v')) {
        e.preventDefault();
        pasteZoneFromClipboard(selectedZoneIndex);
    }
    // Ctrl+Shift+D = duplicate selected zone
    else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
        e.preventDefault();
        duplicateZone(selectedZoneIndex);
    }
    // F = focus search
    else if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const inp = document.getElementById('zoneSearchInput'); if (inp) { e.preventDefault(); inp.focus(); inp.select(); }
    }
});

// ---------- IMPROVEMENT 20: zone color sorting by hue ----------
function sortZoneColorsByHue(index) {
    const z = zones[index]; if (!z || !Array.isArray(z.colors) || z.colors.length < 2) { showToast('Need 2+ colors to sort', true); return; }
    pushZoneUndo('Sort colors by hue');
    function rgbToHue(r,g,b) {
        r/=255; g/=255; b/=255;
        const max = Math.max(r,g,b), min = Math.min(r,g,b), d = max - min;
        if (d === 0) return 0;
        let h = 0;
        if (max === r) h = ((g - b) / d) % 6;
        else if (max === g) h = (b - r) / d + 2;
        else h = (r - g) / d + 4;
        return ((h * 60) + 360) % 360;
    }
    z.colors.sort(function(a, b) {
        const ha = rgbToHue.apply(null, a.color_rgb || [0,0,0]);
        const hb = rgbToHue.apply(null, b.color_rgb || [0,0,0]);
        return ha - hb;
    });
    renderZones(); triggerPreviewRender();
    showToast('Sorted ' + z.colors.length + ' colors by hue');
}
if (typeof window !== 'undefined') { window.sortZoneColorsByHue = sortZoneColorsByHue; }

// ---------- IMPROVEMENT 21: zone analysis — recently used finishes per zone ----------
const _perZoneRecentFinishes = {};
function trackRecentFinishOnZone(index, finishId) {
    if (typeof index !== 'number' || !finishId) return;
    if (!_perZoneRecentFinishes[index]) _perZoneRecentFinishes[index] = [];
    const arr = _perZoneRecentFinishes[index];
    const existing = arr.indexOf(finishId);
    if (existing >= 0) arr.splice(existing, 1);
    arr.unshift(finishId);
    if (arr.length > 6) arr.length = 6;
}
function getRecentFinishesForZone(index) { return (_perZoneRecentFinishes[index] || []).slice(); }
if (typeof window !== 'undefined') { window.getRecentFinishesForZone = getRecentFinishesForZone; window.trackRecentFinishOnZone = trackRecentFinishOnZone; }

// ---------- IMPROVEMENT 22: localStorage size monitor + warning ----------
function getLocalStorageUsage() {
    let total = 0;
    try {
        for (const k in localStorage) {
            if (Object.prototype.hasOwnProperty.call(localStorage, k)) {
                total += (localStorage[k].length + k.length) * 2; // UTF-16
            }
        }
    } catch (e) {}
    return total;
}
function checkLocalStorageQuota() {
    const used = getLocalStorageUsage();
    const QUOTA_WARN = 4 * 1024 * 1024; // 4 MB
    if (used > QUOTA_WARN) {
        const mb = (used / 1024 / 1024).toFixed(2);
        showToast('Warning: localStorage at ' + mb + ' MB. Consider exporting and clearing presets.', true);
        return true;
    }
    return false;
}
if (typeof window !== 'undefined') { window.checkLocalStorageQuota = checkLocalStorageQuota; window.getLocalStorageUsage = getLocalStorageUsage; }

// ---------- IMPROVEMENT 23: smart export filename builder ----------
function buildExportFilename(suffix) {
    const date = new Date();
    const dateStr = date.toISOString().slice(0, 10);
    const driver = (function() {
        const f = document.getElementById('driverName');
        return f && f.value ? f.value.replace(/[^a-z0-9_-]+/gi, '_') : 'unsigned';
    })();
    const carField = document.getElementById('paintFile');
    const carFile = carField && carField.value ? carField.value.split(/[/\\]/).pop().replace(/\.[^.]+$/, '') : 'car';
    const safeCar = carFile.replace(/[^a-z0-9_-]+/gi, '_').slice(0, 20);
    return ['shokker', dateStr, safeCar, driver, suffix || 'config'].filter(Boolean).join('_');
}
if (typeof window !== 'undefined') { window.buildExportFilename = buildExportFilename; }

// ---------- IMPROVEMENT 24: prompt before auto-restoring last session ----------
let _autoRestorePrompted = false;
function promptForAutoRestore() {
    if (_autoRestorePrompted) return;
    _autoRestorePrompted = true;
    const raw = (function() { try { return localStorage.getItem('shokker_autosave'); } catch (e) { return null; } })();
    if (!raw) return false;
    try {
        const cfg = JSON.parse(raw);
        const ageSec = cfg._autosave_time ? Math.round((Date.now() - cfg._autosave_time) / 1000) : 0;
        const ageStr = ageSec < 60 ? ageSec + 's' : ageSec < 3600 ? Math.round(ageSec/60) + 'm' : Math.round(ageSec/3600) + 'h';
        const zc = (cfg.zones || []).length;
        if (confirm('Restore last session?\n\n' + zc + ' zones, saved ' + ageStr + ' ago.\n\nClick OK to restore, Cancel to start fresh.')) {
            if (typeof loadConfigFromObj === 'function') loadConfigFromObj(cfg);
            return true;
        }
    } catch (e) {}
    return false;
}
if (typeof window !== 'undefined') { window.promptForAutoRestore = promptForAutoRestore; }

// ---------- IMPROVEMENT 25: validate before render — overlap detection ----------
function detectZoneOverlaps() {
    const overlaps = [];
    for (let i = 0; i < zones.length; i++) {
        for (let j = i + 1; j < zones.length; j++) {
            const za = zones[i], zb = zones[j];
            if (za.muted || zb.muted) continue;
            // Same color zone overlap
            if (za.colorMode === 'quick' && zb.colorMode === 'quick' && za.color === zb.color) {
                overlaps.push({ a: i, b: j, reason: 'both target color "' + za.color + '"' });
            }
            // Region overlap
            if (za.regionMask && zb.regionMask && za.regionMask.length === zb.regionMask.length) {
                let overlapPx = 0;
                for (let k = 0; k < za.regionMask.length && overlapPx < 100; k++) {
                    if (za.regionMask[k] > 0 && zb.regionMask[k] > 0) overlapPx++;
                }
                if (overlapPx >= 100) overlaps.push({ a: i, b: j, reason: 'region masks overlap' });
            }
        }
    }
    return overlaps;
}
function checkOverlapsBeforeRender() {
    const overlaps = detectZoneOverlaps();
    if (overlaps.length === 0) return true;
    const msg = overlaps.slice(0, 3).map(function(o) {
        return 'Zone ' + (o.a+1) + ' "' + zones[o.a].name + '" overlaps Zone ' + (o.b+1) + ' "' + zones[o.b].name + '" (' + o.reason + ')';
    }).join('\n') + (overlaps.length > 3 ? '\n... +' + (overlaps.length - 3) + ' more' : '');
    return confirm('Possible zone overlaps detected:\n\n' + msg + '\n\nLater zones will overwrite earlier ones. Continue rendering?');
}
if (typeof window !== 'undefined') { window.detectZoneOverlaps = detectZoneOverlaps; window.checkOverlapsBeforeRender = checkOverlapsBeforeRender; }

// ---------- IMPROVEMENT 26: combined validation toast ----------
function getCombinedZoneWarnings() {
    const ws = validateZonesBeforeRender();
    const overlaps = detectZoneOverlaps();
    overlaps.forEach(function(o) {
        ws.push('Overlap: Zone ' + (o.a+1) + ' & Zone ' + (o.b+1) + ' (' + o.reason + ')');
    });
    if (zones.length > 30) ws.push('Heavy load: ' + zones.length + ' zones (recommend < 30 for fast renders)');
    return ws;
}
function showCombinedWarnings() {
    const ws = getCombinedZoneWarnings();
    if (ws.length === 0) { showToast('All zones look good \u2713'); return false; }
    const summary = ws.length + ' warning' + (ws.length !== 1 ? 's' : '') + ': ' + ws.slice(0, 2).join(' | ') + (ws.length > 2 ? ' (+' + (ws.length - 2) + ' more)' : '');
    showToast(summary, true);
    console.warn('[SPB Validation] All warnings:\n' + ws.map(function(w, i) { return (i+1) + '. ' + w; }).join('\n'));
    return true;
}
if (typeof window !== 'undefined') { window.showCombinedWarnings = showCombinedWarnings; window.getCombinedZoneWarnings = getCombinedZoneWarnings; }

// ---------- IMPROVEMENT 27: claim-this-color suggestions from sampled paint ----------
function suggestClaimableColors(maxColors) {
    maxColors = maxColors || 6;
    if (!paintImageData) return [];
    const buckets = {};
    const data = paintImageData.data;
    const stride = 64; // sample sparsely
    for (let i = 0; i < data.length; i += 4 * stride) {
        const a = data[i + 3]; if (a < 32) continue;
        // Quantize to 32-step bins
        const r = (data[i] >> 5) << 5, g = (data[i+1] >> 5) << 5, b = (data[i+2] >> 5) << 5;
        const key = r + ',' + g + ',' + b;
        buckets[key] = (buckets[key] || 0) + 1;
    }
    const sorted = Object.entries(buckets).sort(function(a,b){ return b[1] - a[1]; }).slice(0, maxColors * 2);
    // Filter out colors very close to claimed picker colors
    const claimed = zones.filter(function(z) { return z.colorMode === 'picker' && z.pickerColor; }).map(function(z) {
        return [parseInt(z.pickerColor.substr(1,2),16), parseInt(z.pickerColor.substr(3,2),16), parseInt(z.pickerColor.substr(5,2),16)];
    });
    const out = [];
    for (let s = 0; s < sorted.length && out.length < maxColors; s++) {
        const rgb = sorted[s][0].split(',').map(Number);
        let tooClose = false;
        for (const c of claimed) {
            if (Math.abs(c[0]-rgb[0]) < 24 && Math.abs(c[1]-rgb[1]) < 24 && Math.abs(c[2]-rgb[2]) < 24) { tooClose = true; break; }
        }
        if (tooClose) continue;
        const hex = '#' + rgb.map(c => c.toString(16).padStart(2,'0')).join('').toUpperCase();
        out.push({ hex: hex, rgb: rgb, count: sorted[s][1] });
    }
    return out;
}
function applySuggestedColorToZone(index, hex) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    if (typeof setHexColor === 'function') setHexColor(index, hex);
}
if (typeof window !== 'undefined') { window.suggestClaimableColors = suggestClaimableColors; window.applySuggestedColorToZone = applySuggestedColorToZone; }

// ---------- IMPROVEMENT 28: zone numeric intensity input ----------
function setZoneIntensityNumeric(index, value) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const z = zones[index]; if (!z) return;
    const num = Math.max(0, Math.min(200, parseInt(value) || 0));
    pushZoneUndoCoalesced('Set intensity ' + num);
    z.intensity = String(num);
    z.customSpec = null; z.customPaint = null; z.customBright = null; // Reset custom
    renderZones(); triggerPreviewRender();
}
if (typeof window !== 'undefined') { window.setZoneIntensityNumeric = setZoneIntensityNumeric; }

// ---------- IMPROVEMENT 29: harmonized zone color suggestions (complementary, triad) ----------
function suggestColorHarmony(hex, mode) {
    if (!hex || !/^#[0-9A-Fa-f]{6}$/.test(hex)) return [];
    function toHsl(h) {
        const r = parseInt(h.substr(1,2),16)/255, g = parseInt(h.substr(3,2),16)/255, b = parseInt(h.substr(5,2),16)/255;
        const mx = Math.max(r,g,b), mn = Math.min(r,g,b);
        let hh = 0, s = 0, l = (mx+mn)/2;
        if (mx !== mn) { const d = mx - mn; s = l > 0.5 ? d/(2-mx-mn) : d/(mx+mn);
            switch(mx){ case r: hh = (g-b)/d + (g<b?6:0); break; case g: hh = (b-r)/d + 2; break; case b: hh = (r-g)/d + 4; break; }
            hh /= 6;
        }
        return [hh*360, s, l];
    }
    function fromHsl(h, s, l) {
        h = ((h % 360) + 360) % 360 / 360;
        function hue2rgb(p,q,t){ if(t<0)t+=1; if(t>1)t-=1; if(t<1/6)return p+(q-p)*6*t; if(t<1/2)return q; if(t<2/3)return p+(q-p)*(2/3-t)*6; return p; }
        const q = l < 0.5 ? l * (1+s) : l + s - l*s, p = 2*l - q;
        const r = Math.round(hue2rgb(p,q,h+1/3) * 255);
        const g = Math.round(hue2rgb(p,q,h) * 255);
        const b = Math.round(hue2rgb(p,q,h-1/3) * 255);
        return '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join('').toUpperCase();
    }
    const [h, s, l] = toHsl(hex);
    if (mode === 'complementary') return [fromHsl(h + 180, s, l)];
    if (mode === 'triad') return [fromHsl(h + 120, s, l), fromHsl(h + 240, s, l)];
    if (mode === 'analogous') return [fromHsl(h - 30, s, l), fromHsl(h + 30, s, l)];
    if (mode === 'split') return [fromHsl(h + 150, s, l), fromHsl(h + 210, s, l)];
    if (mode === 'tetrad') return [fromHsl(h + 90, s, l), fromHsl(h + 180, s, l), fromHsl(h + 270, s, l)];
    return [];
}
if (typeof window !== 'undefined') { window.suggestColorHarmony = suggestColorHarmony; }

// ---------- IMPROVEMENT 30: zone scroll-to / focus helpers ----------
function focusZone(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    selectedZoneIndex = index;
    renderZones();
    const card = document.getElementById('zone-card-' + index);
    if (card && card.scrollIntoView) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.style.animation = 'zoneFlash 0.6s ease';
        setTimeout(function() { card.style.animation = ''; }, 600);
    }
}
if (typeof window !== 'undefined') { window.focusZone = focusZone; }

// ---------- IMPROVEMENT 31: empty-state guidance ----------
function getEmptyStateGuide() {
    if (zones.length > 0) return '';
    return '<div class="empty-zones-guide" style="padding:18px 14px;text-align:center;color:#aaa;font-size:11px;border:1px dashed #333;border-radius:6px;margin:12px;">' +
        '<div style="font-size:20px;margin-bottom:8px;">\u{1F3A8}</div>' +
        '<div style="font-weight:bold;color:#ddd;margin-bottom:6px;font-size:13px;">No zones yet</div>' +
        '<div style="margin-bottom:10px;line-height:1.5;">Zones tell SPB which pixels to paint with which finish.<br>Get started by adding your first zone.</div>' +
        '<button class="btn" onclick="addZone()" style="background:#E87A20;color:#fff;border:none;padding:7px 14px;border-radius:4px;cursor:pointer;font-weight:bold;">+ Add First Zone</button>' +
        '<div style="margin-top:10px;font-size:9px;color:#666;">Or load a preset: <a href="#" onclick="event.preventDefault();const p=listZonePresets();if(p.length===0){alert(\'No saved presets\');return;}const n=prompt(\'Load which preset?\\n\\n\'+p.map(p=>p.name).join(\'\\n\'));if(n)loadZonePreset(n);" style="color:#0af;">Load Preset</a></div>' +
        '</div>';
}
if (typeof window !== 'undefined') { window.getEmptyStateGuide = getEmptyStateGuide; }

// ---------- IMPROVEMENT 32: auto-save metadata getters (last save time + dirty state) ----------
let _spbDirtyState = false;
function markDirty() { _spbDirtyState = true; updateAutoSaveBadge(); }
function markClean() { _spbDirtyState = false; updateAutoSaveBadge(); }
function getLastAutoSaveTime() {
    try { const cfg = JSON.parse(localStorage.getItem('shokker_autosave') || '{}'); return cfg._autosave_time || 0; } catch (e) { return 0; }
}
function updateAutoSaveBadge() {
    const badge = document.getElementById('autosaveBadge'); if (!badge) return;
    const t = getLastAutoSaveTime();
    if (!t) { badge.textContent = 'Not saved'; return; }
    const ago = Math.round((Date.now() - t) / 1000);
    const agoStr = ago < 60 ? ago + 's ago' : ago < 3600 ? Math.round(ago/60) + 'm ago' : Math.round(ago/3600) + 'h ago';
    badge.textContent = (_spbDirtyState ? '\u26A0 Unsaved | ' : '\u2713 Auto-saved ') + agoStr;
}
if (typeof window !== 'undefined') { window.updateAutoSaveBadge = updateAutoSaveBadge; window.markDirty = markDirty; window.markClean = markClean; window.getLastAutoSaveTime = getLastAutoSaveTime; }
// Update badge once a minute
setInterval(updateAutoSaveBadge, 60000);

// ---------- IMPROVEMENT 33: zone limit warnings ----------
function checkZoneLimitWarning() {
    if (zones.length >= MAX_ZONES) { showToast('Hard limit (' + MAX_ZONES + ' zones) reached. Delete some to add more.', true); return 'hard'; }
    if (zones.length >= 30) { showToast('Heavy load: ' + zones.length + ' zones. Render performance will drop above 30.', true); return 'soft'; }
    if (zones.length >= 20) { return 'caution'; }
    return 'ok';
}
if (typeof window !== 'undefined') { window.checkZoneLimitWarning = checkZoneLimitWarning; }

// ---------- IMPROVEMENT 34: layer thumbnails for restrict-to-layer dropdown ----------
function getLayerThumbnailUrl(layerId) {
    if (typeof _psdLayers === 'undefined' || !_psdLayers) return '';
    const layer = _psdLayers.find(l => l.id === layerId);
    if (!layer || !layer.img) return '';
    return layer.img.src || '';
}
if (typeof window !== 'undefined') { window.getLayerThumbnailUrl = getLayerThumbnailUrl; }

// ---------- IMPROVEMENT 35: mute-others (solo) — quickly isolate a zone ----------
function soloZone(index) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    pushZoneUndo('Solo zone ' + (index + 1));
    zones.forEach(function(z, i) { z.muted = (i !== index); });
    renderZones(); triggerPreviewRender();
    showToast('Solo: only "' + zones[index].name + '" will render');
}
function unmuteAllZones() {
    pushZoneUndo('Unmute all');
    zones.forEach(function(z) { z.muted = false; });
    renderZones(); triggerPreviewRender();
    showToast('All zones unmuted');
}
if (typeof window !== 'undefined') { window.soloZone = soloZone; window.unmuteAllZones = unmuteAllZones; }

// ---------- IMPROVEMENT 36: zone reset to defaults ----------
function resetZone(index) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const z = zones[index]; if (!z) return;
    if (!confirm('Reset "' + z.name + '" to defaults? (Color, finish, all overlays will be cleared)')) return;
    pushZoneUndo('Reset zone "' + z.name + '"');
    const preserveName = z.name;
    Object.keys(z).forEach(function(k) { delete z[k]; });
    Object.assign(z, {
        name: preserveName, color: null, base: null, pattern: 'none', finish: null, intensity: '100',
        colorMode: 'none', pickerColor: '#3366ff', pickerTolerance: 40, colors: [], regionMask: null,
        muted: false, patternStack: [], specPatternStack: [],
    });
    renderZones(); triggerPreviewRender();
    showToast('Reset zone: ' + preserveName);
}
if (typeof window !== 'undefined') { window.resetZone = resetZone; }

// ---------- IMPROVEMENT 37: zone clone-to-N — multi-duplicate ----------
function cloneZoneNTimes(index, n) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    if (!n) { const v = prompt('Clone how many copies?', '3'); n = parseInt(v); if (!n) return; }
    n = Math.min(n, MAX_ZONES - zones.length);
    if (n <= 0) { showToast('Not enough room (zone limit reached)', true); return; }
    pushZoneUndo('Clone zone x' + n);
    const src = zones[index];
    for (let i = 0; i < n; i++) {
        const clone = _cloneZoneState(src, {
            preserveId: false,
            includeRegionMask: false,
            includeSpatialMask: false,
            includePatternStrengthMap: true,
        });
        clone.name = src.name + ' (' + (i + 2) + ')';
        clone.regionMask = null;
        clone.spatialMask = null;
        zones.splice(index + 1 + i, 0, clone);
    }
    renderZones(); triggerPreviewRender();
    showToast('Cloned ' + n + ' copies of "' + src.name + '"');
}
if (typeof window !== 'undefined') { window.cloneZoneNTimes = cloneZoneNTimes; }

// ---------- IMPROVEMENT 38: clear all zones ----------
function clearAllZones() {
    if (!confirm('Delete ALL ' + zones.length + ' zones and start fresh?')) return;
    pushZoneUndo('Clear all zones');
    zones.length = 0;
    addZone(true);
    selectedZoneIndex = 0;
    renderZones(); triggerPreviewRender();
    showToast('All zones cleared. Started fresh with one empty zone.');
}
if (typeof window !== 'undefined') { window.clearAllZones = clearAllZones; }

// ---------- IMPROVEMENT 39: filter zones by status (errors only) ----------
function filterZonesByStatus(status) {
    const cards = document.querySelectorAll('#zoneList .zone-card');
    cards.forEach(function(card, i) {
        const z = zones[i]; if (!z) return;
        const s = getZoneStatus(z);
        card.style.display = (status === 'all' || s === status) ? '' : 'none';
    });
    showToast('Filtered: ' + status);
}
function showOnlyProblemZones() { filterZonesByStatus('no_finish'); }
function showAllZones() { filterZonesByStatus('all'); }
if (typeof window !== 'undefined') {
    window.filterZonesByStatus = filterZonesByStatus;
    window.showOnlyProblemZones = showOnlyProblemZones;
    window.showAllZones = showAllZones;
}

// ---------- IMPROVEMENT 40: getZoneSummary — concise text summary ----------
function getZoneSummary(index) {
    const z = zones[index]; if (!z) return '';
    const parts = [];
    if (z.muted) parts.push('MUTED');
    if (z.base) parts.push('Base: ' + z.base);
    if (z.finish) parts.push('Finish: ' + z.finish);
    if (z.pattern && z.pattern !== 'none') parts.push('Pattern: ' + z.pattern);
    if (z.colorMode === 'picker' && z.pickerColor) parts.push('Color: ' + z.pickerColor);
    if (z.colorMode === 'multi') parts.push((z.colors||[]).length + ' colors');
    if (z.colorMode === 'special') parts.push('Special: ' + z.color);
    if (z.regionMask && z.regionMask.some(v => v > 0)) parts.push('Has region');
    if (z.linkGroup) parts.push('Linked');
    if ((z.patternStack||[]).length) parts.push((z.patternStack||[]).length + ' pattern layers');
    if ((z.specPatternStack||[]).length) parts.push((z.specPatternStack||[]).length + ' spec patterns');
    return parts.join(' | ') || 'Empty zone';
}
if (typeof window !== 'undefined') { window.getZoneSummary = getZoneSummary; }

// ---------- IMPROVEMENT 41: configure-import preview ----------
function previewImportedConfig(json) {
    try {
        const cfg = typeof json === 'string' ? JSON.parse(json) : json;
        if (!cfg || !cfg.zones) return null;
        return {
            zoneCount: cfg.zones.length,
            driver: cfg.driverName || cfg.driver_name || 'unknown',
            zoneNames: cfg.zones.map(z => z.name).slice(0, 10),
            hasMore: cfg.zones.length > 10,
            saveTime: cfg._autosave_time ? new Date(cfg._autosave_time).toLocaleString() : 'unknown',
        };
    } catch (e) { return null; }
}
function showConfigImportPreview(json) {
    const preview = previewImportedConfig(json); if (!preview) { showToast('Invalid config JSON', true); return false; }
    const msg = 'Import this config?\n\n' +
                'Zones: ' + preview.zoneCount + '\n' +
                'Driver: ' + preview.driver + '\n' +
                'Saved: ' + preview.saveTime + '\n\n' +
                'First zones:\n' + preview.zoneNames.map((n,i) => (i+1)+'. '+n).join('\n') +
                (preview.hasMore ? '\n... +' + (preview.zoneCount - 10) + ' more' : '');
    return confirm(msg);
}
if (typeof window !== 'undefined') { window.showConfigImportPreview = showConfigImportPreview; window.previewImportedConfig = previewImportedConfig; }

// ---------- IMPROVEMENT 42: zone bringToFront / sendToBack ----------
function bringZoneToFront(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    if (index === 0) return;
    pushZoneUndo('Bring zone to front');
    const [moved] = zones.splice(index, 1);
    zones.unshift(moved);
    selectedZoneIndex = 0;
    renderZones(); triggerPreviewRender();
}
function sendZoneToBack(index) {
    if (typeof index !== 'number' || index < 0 || index >= zones.length) return;
    if (index === zones.length - 1) return;
    pushZoneUndo('Send zone to back');
    const [moved] = zones.splice(index, 1);
    zones.push(moved);
    selectedZoneIndex = zones.length - 1;
    renderZones(); triggerPreviewRender();
}
if (typeof window !== 'undefined') { window.bringZoneToFront = bringZoneToFront; window.sendZoneToBack = sendZoneToBack; }

// ---------- IMPROVEMENT 43: tooltip text for "Remaining" vs "Everything" ----------
function getSpecialColorExplanation(value) {
    if (value === 'remaining') return 'Catches every pixel NOT already claimed by a zone above this one. Use as a safety net for unclaimed body paint.';
    if (value === 'everything') return 'Targets ALL pixels on the car (overrides other zones). Use sparingly — typically for a base monolithic finish covering the whole car.';
    return value;
}
if (typeof window !== 'undefined') { window.getSpecialColorExplanation = getSpecialColorExplanation; }

// ---------- IMPROVEMENT 44: getZoneRenderOrder — visualize compositing order ----------
function getZoneRenderOrder() {
    return zones.map(function(z, i) {
        return {
            order: i + 1,
            name: z.name,
            status: getZoneStatus(z),
            muted: !!z.muted,
            specialFlag: z.colorMode === 'special' ? z.color : null,
        };
    });
}
if (typeof window !== 'undefined') { window.getZoneRenderOrder = getZoneRenderOrder; }

// ---------- IMPROVEMENT 45: invertZoneMute — flip all mute states ----------
function invertAllZoneMutes() {
    pushZoneUndo('Invert all mutes');
    zones.forEach(function(z) { z.muted = !z.muted; });
    renderZones(); triggerPreviewRender();
    showToast('Inverted all mute states');
}
if (typeof window !== 'undefined') { window.invertAllZoneMutes = invertAllZoneMutes; }

// ---------- IMPROVEMENT 46: zone tag system — categorize zones ----------
function setZoneTag(index, tag) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const z = zones[index]; if (!z) return;
    pushZoneUndo('Set tag: ' + tag);
    z.tag = tag;
    renderZones();
}
function getZonesByTag(tag) { return zones.filter(z => z.tag === tag); }
if (typeof window !== 'undefined') { window.setZoneTag = setZoneTag; window.getZonesByTag = getZonesByTag; }

// ---------- IMPROVEMENT 47: validate & repair zone data ----------
// 2026-04-19 HEENAN HP-MIGRATE — saved-config legacy-ID migration.
// Codex audit of the HP1-HP4 + HB2 rename pass identified that saved zone
// configs / autosaves / presets created BEFORE the renames would silently
// orphan on load: the engine gets a raw id that no longer exists in the
// registry, producing an invisible finish where the painter expected their
// prior work. No migration layer existed. This map rewrites old ids to
// new ids wherever zone state is loaded from disk.
//
// Each row documents the win that introduced the rename (HP/HB prefix).
// Migration is scoped per field because the same bare string can be a valid
// id in one registry and a renamed id in another (e.g., `shokk_cipher` is
// a live BASE but the renamed PATTERN).
const _SPB_LEGACY_ID_MIGRATIONS = Object.freeze({
    // z.finish — monolithic id field
    monolithic: Object.freeze({
        'acid_rain': 'acid_rain_drip',                  // HP1
        // HP4: `mystichrome` kept its id (the DUPLICATE was renamed to
        // `mystichrome_classic`). No migration entry needed — painters'
        // old saves that referenced `mystichrome` still resolve to the
        // surviving entry.
        // 2026-04-19 4-HOUR RUN H4HR-3: crystal_lattice MONO → crystal_lattice_mono.
        'crystal_lattice': 'crystal_lattice_mono',
    }),
    // z.pattern + patternStack[].id — pattern id field
    pattern: Object.freeze({
        'shokk_cipher': 'shokk_cipher_pattern',         // HB2
        // 2026-04-19 4-HOUR RUN H4HR-1/H4HR-2: pattern-tier collisions.
        'dragonfly_wing': 'dragonfly_wing_pattern',     // H4HR-1
        'carbon_weave': 'carbon_weave_pattern',         // H4HR-2
    }),
    // specPatternStack[].id + four overlay stacks — spec-pattern id field
    specPattern: Object.freeze({
        'carbon_weave': 'spec_carbon_weave',            // HP2
        'diffraction_grating': 'spec_diffraction_grating_cd', // HP3
        // 2026-04-19 4-HOUR RUN H4HR-4..H4HR-8: spec-tier collisions vs MONOLITHICS.
        'oil_slick': 'spec_oil_slick',                  // H4HR-4
        'gravity_well': 'spec_gravity_well',            // H4HR-5
        'sparkle_constellation': 'spec_sparkle_constellation', // H4HR-6
        'sparkle_firefly': 'spec_sparkle_firefly',      // H4HR-7
        'sparkle_champagne': 'spec_sparkle_champagne',  // H4HR-8
    }),
});

function _migrateZoneFinishIds(zone) {
    if (!zone) return 0;
    let changed = 0;
    const M = _SPB_LEGACY_ID_MIGRATIONS;
    if (zone.finish && M.monolithic[zone.finish]) {
        zone.finish = M.monolithic[zone.finish]; changed++;
    }
    if (zone.pattern && M.pattern[zone.pattern]) {
        zone.pattern = M.pattern[zone.pattern]; changed++;
    }
    if (Array.isArray(zone.patternStack)) {
        zone.patternStack.forEach(function (entry) {
            if (entry && entry.id && M.pattern[entry.id]) {
                entry.id = M.pattern[entry.id]; changed++;
            }
        });
    }
    // Main spec pattern stack + four overlay stacks (overlaySpecPatternStack
    // through fifthOverlaySpecPatternStack — see loadConfigFromObj).
    ['specPatternStack', 'overlaySpecPatternStack',
     'thirdOverlaySpecPatternStack', 'fourthOverlaySpecPatternStack',
     'fifthOverlaySpecPatternStack'].forEach(function (stackKey) {
        const stack = zone[stackKey];
        if (!Array.isArray(stack)) return;
        stack.forEach(function (entry) {
            if (entry && entry.id && M.specPattern[entry.id]) {
                entry.id = M.specPattern[entry.id]; changed++;
            }
        });
    });
    return changed;
}
if (typeof window !== 'undefined') {
    window._SPB_LEGACY_ID_MIGRATIONS = _SPB_LEGACY_ID_MIGRATIONS;
    window._migrateZoneFinishIds = _migrateZoneFinishIds;
}

function _normalizeLegacySpecPatternChannels(zone) {
    if (!zone) return 0;
    let changed = 0;
    ['specPatternStack', 'overlaySpecPatternStack',
     'thirdOverlaySpecPatternStack', 'fourthOverlaySpecPatternStack',
     'fifthOverlaySpecPatternStack'].forEach(function (stackKey) {
        const stack = zone[stackKey];
        if (!Array.isArray(stack)) return;
        stack.forEach(function (entry) {
            if (!entry || !entry.pattern) return;
            const defaults = _getSpecPatternLayerDefaults(entry.pattern);
            const currentChannels = String(entry.channels || '').trim().toUpperCase();
            if (!currentChannels) {
                entry.channels = defaults.channels;
                entry.channelsCustomized = false;
                changed++;
                return;
            }
            if (entry.channelsCustomized == null) {
                if (currentChannels === 'MR' && defaults.channels !== 'MR') {
                    entry.channels = defaults.channels;
                    entry.channelsCustomized = false;
                    changed++;
                    return;
                }
                entry.channelsCustomized = currentChannels !== defaults.channels;
            }
        });
    });
    return changed;
}
if (typeof window !== 'undefined') {
    window._normalizeLegacySpecPatternChannels = _normalizeLegacySpecPatternChannels;
}

function repairZoneData() {
    let fixed = 0;
    let migrated = 0;
    let specDefaultsFixed = 0;
    zones.forEach(function(z) {
        if (typeof z.name !== 'string' || !z.name.trim()) { z.name = 'Zone'; fixed++; }
        if (typeof z.intensity !== 'string' && typeof z.intensity !== 'number') { z.intensity = '100'; fixed++; }
        if (!Array.isArray(z.colors)) { z.colors = []; fixed++; }
        if (!Array.isArray(z.patternStack)) { z.patternStack = []; fixed++; }
        if (!Array.isArray(z.specPatternStack)) { z.specPatternStack = []; fixed++; }
        if (z.pickerTolerance == null || isNaN(z.pickerTolerance)) { z.pickerTolerance = 40; fixed++; }
        if (z.pickerColor && !/^#[0-9A-Fa-f]{6}$/.test(z.pickerColor)) { z.pickerColor = '#3366ff'; fixed++; }
        if (typeof z.muted !== 'boolean') { z.muted = false; fixed++; }
        // HP-MIGRATE: rewrite any legacy ids (HP1-HP4, HB2) so the painter's
        // prior work still resolves after a cross-registry collision rename.
        migrated += _migrateZoneFinishIds(z);
        specDefaultsFixed += _normalizeLegacySpecPatternChannels(z);
    });
    if (fixed > 0 || migrated > 0 || specDefaultsFixed > 0) {
        renderZones();
        let parts = [];
        if (fixed > 0) parts.push('Repaired ' + fixed + ' zone fields');
        if (migrated > 0) parts.push('Migrated ' + migrated + ' legacy finish id(s)');
        if (specDefaultsFixed > 0) parts.push('Normalized ' + specDefaultsFixed + ' spec pattern channel default(s)');
        showToast(parts.join(' · '));
    }
    return fixed + migrated + specDefaultsFixed;
}
if (typeof window !== 'undefined') { window.repairZoneData = repairZoneData; }
// Auto-repair on init
setTimeout(function() { try { repairZoneData(); } catch (e) {} }, 2000);

// ---------- IMPROVEMENT 48: keyboard shortcut — N to add new zone ----------
// SESSION ROUTER: bail on defaultPrevented.
document.addEventListener('keydown', function(e) {
    if (e.defaultPrevented) return;
    if (_isTextEntryTargetForGlobalUndo(e.target)) return;
    if (e.key === 'n' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
        e.preventDefault();
        addZone();
    } else if (e.key === 'm' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
        // M = mute selected zone
        e.preventDefault();
        toggleZoneMute(selectedZoneIndex);
    } else if (e.key === 'Delete' && e.shiftKey) {
        // Shift+Delete = delete selected zone
        e.preventDefault();
        deleteZone(selectedZoneIndex);
    }
});

// ---------- IMPROVEMENT 49: get-best-tolerance — analyze color spread, pick smart tolerance ----------
function suggestSmartTolerance(hex) {
    if (!hex || !paintImageData) return 40;
    const r0 = parseInt(hex.substr(1,2),16), g0 = parseInt(hex.substr(3,2),16), b0 = parseInt(hex.substr(5,2),16);
    const data = paintImageData.data;
    let nearMatches = 0, totalSamples = 0;
    const stride = 32;
    for (let i = 0; i < data.length; i += 4 * stride) {
        if (data[i+3] < 32) continue; totalSamples++;
        const dr = Math.abs(data[i]-r0), dg = Math.abs(data[i+1]-g0), db = Math.abs(data[i+2]-b0);
        if (dr < 80 && dg < 80 && db < 80) nearMatches++;
    }
    if (totalSamples === 0) return 40;
    const ratio = nearMatches / totalSamples;
    // If a lot of pixels are near, use tighter tolerance to avoid over-grabbing
    if (ratio > 0.4) return 15;
    if (ratio > 0.2) return 25;
    if (ratio > 0.1) return 40;
    return 60;
}
if (typeof window !== 'undefined') { window.suggestSmartTolerance = suggestSmartTolerance; }

// ---------- IMPROVEMENT 50: zone duplicate-with-new-color (offers a hex prompt) ----------
function duplicateZoneWithColor(index) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const newHex = prompt('New hex color for the duplicate (e.g. #FF3366):', '#FFFFFF');
    if (!newHex) return;
    if (!/^#?[0-9A-Fa-f]{6}$/.test(newHex)) { showToast('Invalid hex', true); return; }
    pushZoneUndo('Duplicate with new color');
    const src = zones[index];
    const clone = _cloneZoneState(src, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
    });
    clone.name = src.name + ' (' + newHex.toUpperCase() + ')';
    clone.regionMask = null;
    const norm = newHex.startsWith('#') ? newHex : '#' + newHex;
    clone.pickerColor = norm.toUpperCase();
    clone.colorMode = 'picker';
    clone.colors = [];
    const r = parseInt(norm.substr(1,2),16), g = parseInt(norm.substr(3,2),16), b = parseInt(norm.substr(5,2),16);
    clone.color = { color_rgb: [r,g,b], tolerance: clone.pickerTolerance ?? 40 };
    zones.splice(index + 1, 0, clone);
    selectedZoneIndex = index + 1;
    renderZones(); triggerPreviewRender();
    showToast('Duplicated with color ' + norm.toUpperCase());
}
if (typeof window !== 'undefined') { window.duplicateZoneWithColor = duplicateZoneWithColor; }

// ---------- IMPROVEMENT 51: smart-pattern-suggestion based on base ----------
const BASE_PATTERN_SUGGESTIONS = {
    'matte':   ['none', 'matte_grain', 'hex_mesh'],
    'gloss':   ['none', 'flake_fine', 'metallic_subtle'],
    'chrome':  ['none', 'brushed_horizontal', 'mirror_distort'],
    'metallic':['flake_fine', 'flake_medium', 'flake_coarse'],
    'pearl':   ['pearl_shimmer', 'pearl_fine'],
    'candy':   ['flake_medium', 'candy_drift'],
    'flake':   ['flake_fine', 'flake_medium', 'flake_coarse'],
};
function getSuggestedPatternsForBase(baseId) {
    const cat = (baseId || '').toLowerCase();
    for (const key in BASE_PATTERN_SUGGESTIONS) { if (cat.includes(key)) return BASE_PATTERN_SUGGESTIONS[key]; }
    return ['none'];
}
if (typeof window !== 'undefined') { window.getSuggestedPatternsForBase = getSuggestedPatternsForBase; }

// ---------- IMPROVEMENT 52: zone-card flash animation (CSS injection) ----------
(function injectZoneFlashCSS() {
    if (document.getElementById('spbZoneFlashCSS')) return;
    const style = document.createElement('style');
    style.id = 'spbZoneFlashCSS';
    style.textContent = '@keyframes zoneFlash { 0%{box-shadow:0 0 0 2px #ffaa00;} 50%{box-shadow:0 0 16px 4px #ffaa00aa;} 100%{box-shadow:0 0 0 2px transparent;} }' +
                        ' .zone-bulk-selected { outline: 2px dashed #00ccff; outline-offset: 2px; }' +
                        ' .zone-status-badge { transition: all 0.2s ease; }' +
                        ' .zone-warn { color:#ff8c1a; font-weight:bold; }' +
                        ' #zoneSearchInput { background:#1a1a2e; color:#fff; border:1px solid #333; padding:4px 8px; border-radius:4px; font-size:11px; width:140px; }' +
                        ' #zoneSearchInput:focus { border-color:#E87A20; outline:none; }';
    document.head.appendChild(style);
})();

// ---------- IMPROVEMENT 53: get number of unrendered zones ----------
function getUnrenderableZoneCount() {
    return zones.filter(function(z) {
        if (z.muted) return true;
        const hasFinish = !!(z.base || z.finish);
        const hasColor = z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special';
        const hasRegion = z.regionMask && z.regionMask.some(v => v > 0);
        return !hasFinish || (!hasColor && !hasRegion);
    }).length;
}
if (typeof window !== 'undefined') { window.getUnrenderableZoneCount = getUnrenderableZoneCount; }

// ---------- IMPROVEMENT 54: getZoneAge — when was zone last modified? ----------
function touchZoneTimestamp(index) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    if (zones[index]) zones[index]._lastModified = Date.now();
}
function getZoneAge(index) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const t = (zones[index] && zones[index]._lastModified) || 0;
    if (!t) return 'never';
    const ago = Math.round((Date.now() - t) / 1000);
    return ago < 60 ? ago + 's ago' : ago < 3600 ? Math.round(ago/60) + 'm ago' : Math.round(ago/3600) + 'h ago';
}
if (typeof window !== 'undefined') { window.getZoneAge = getZoneAge; window.touchZoneTimestamp = touchZoneTimestamp; }

// ---------- IMPROVEMENT 55: bulk hex shift on multi-color zones ----------
function bulkShiftMultiColors(index, hueShift) {
    if (typeof index !== 'number') index = selectedZoneIndex;
    const z = zones[index]; if (!z || !Array.isArray(z.colors) || z.colors.length === 0) { showToast('No multi-color stack', true); return; }
    pushZoneUndo('Shift all colors hue ' + hueShift + 'deg');
    function shift(rgb, deg) {
        const hex = '#' + rgb.map(c => c.toString(16).padStart(2,'0')).join('');
        // Reuse hue shift logic
        function toHsl(h) {
            const r = parseInt(h.substr(1,2),16)/255, g = parseInt(h.substr(3,2),16)/255, b = parseInt(h.substr(5,2),16)/255;
            const mx = Math.max(r,g,b), mn = Math.min(r,g,b);
            let hh = 0, s = 0, l = (mx+mn)/2;
            if (mx !== mn) { const d = mx - mn; s = l > 0.5 ? d/(2-mx-mn) : d/(mx+mn);
                switch(mx){ case r: hh = (g-b)/d + (g<b?6:0); break; case g: hh = (b-r)/d + 2; break; case b: hh = (r-g)/d + 4; break; }
                hh /= 6;
            }
            return [hh*360, s, l];
        }
        function fromHsl(h, s, l) {
            h = ((h % 360) + 360) % 360 / 360;
            function hue2rgb(p,q,t){ if(t<0)t+=1; if(t>1)t-=1; if(t<1/6)return p+(q-p)*6*t; if(t<1/2)return q; if(t<2/3)return p+(q-p)*(2/3-t)*6; return p; }
            const q = l < 0.5 ? l * (1+s) : l + s - l*s, p = 2*l - q;
            return [Math.round(hue2rgb(p,q,h+1/3) * 255), Math.round(hue2rgb(p,q,h) * 255), Math.round(hue2rgb(p,q,h-1/3) * 255)];
        }
        const [h, s, l] = toHsl(hex);
        return fromHsl(h + deg, s, l);
    }
    z.colors.forEach(function(c) {
        c.color_rgb = shift(c.color_rgb, hueShift);
        c.hex = '#' + c.color_rgb.map(v => v.toString(16).padStart(2,'0')).join('').toUpperCase();
    });
    renderZones(); triggerPreviewRender();
    showToast('Shifted ' + z.colors.length + ' colors by ' + hueShift + '\u00B0');
}
if (typeof window !== 'undefined') { window.bulkShiftMultiColors = bulkShiftMultiColors; }

// ---------- IMPROVEMENT 56: import-zone preview (parse before commit) ----------
function previewImportedZone(jsonStr) {
    try {
        const data = JSON.parse(jsonStr); if (!data || !data.__spbZone || !data.zone) return null;
        return { name: data.zone.name, base: data.zone.base, finish: data.zone.finish, pattern: data.zone.pattern, exportedAt: data.exportedAt ? new Date(data.exportedAt).toLocaleString() : 'unknown' };
    } catch (e) { return null; }
}
if (typeof window !== 'undefined') { window.previewImportedZone = previewImportedZone; }

// ---------- IMPROVEMENT 57: track recent finishes — extended/per-zone version ----------
const _spbRecentFinishesV2 = [];
function _trackRecentFinishV2(finishId) {
    if (!finishId) return;
    const idx = _spbRecentFinishesV2.indexOf(finishId);
    if (idx >= 0) _spbRecentFinishesV2.splice(idx, 1);
    _spbRecentFinishesV2.unshift(finishId);
    if (_spbRecentFinishesV2.length > 12) _spbRecentFinishesV2.length = 12;
    try { localStorage.setItem('shokker_recent_finishes_v2', JSON.stringify(_spbRecentFinishesV2)); } catch (e) {}
    // Also track per-zone
    if (selectedZoneIndex >= 0) trackRecentFinishOnZone(selectedZoneIndex, finishId);
}
function getRecentFinishesV2() { return _spbRecentFinishesV2.slice(); }
// Restore on load
try {
    const raw = localStorage.getItem('shokker_recent_finishes_v2');
    if (raw) { const arr = JSON.parse(raw); if (Array.isArray(arr)) { _spbRecentFinishesV2.push.apply(_spbRecentFinishesV2, arr.slice(0, 12)); } }
} catch (e) {}
if (typeof window !== 'undefined') { window.getRecentFinishesV2 = getRecentFinishesV2; window._trackRecentFinishV2 = _trackRecentFinishV2; }

// ---------- IMPROVEMENT 58: zone click-to-isolate-and-edit ----------
function isolateAndEditZone(index) {
    soloZone(index);
    selectZone(index);
    if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
    showToast('Isolated "' + zones[index].name + '" — only this zone visible');
}
if (typeof window !== 'undefined') { window.isolateAndEditZone = isolateAndEditZone; }

// ---------- IMPROVEMENT 59: helper — name-based fallback for auto-fill detection ----------
// (Augments the canonical group-based _spbShouldAutoFillBaseColor with a name-pattern fallback.)
function _spbShouldAutoFillByName(finishId) {
    if (!finishId) return false;
    const lower = finishId.toLowerCase();
    return lower.includes('colorshoxx') || lower.includes('mortal') || lower.includes('shokk') ||
           lower.includes('paradigm') || lower.includes('candy') || lower.includes('chameleon') ||
           lower.includes('atelier');
}
if (typeof window !== 'undefined') { window._spbShouldAutoFillByName = _spbShouldAutoFillByName; }

// ---------- IMPROVEMENT 60: zone batch tolerance update across ALL zones ----------
function setAllZonesTolerance(tolerance) {
    if (typeof tolerance !== 'number' || tolerance < 1 || tolerance > 200) {
        const v = prompt('Tolerance for ALL zones (1-200):', '40');
        tolerance = parseInt(v); if (isNaN(tolerance)) return;
    }
    pushZoneUndo('Set all tolerances to ' + tolerance);
    zones.forEach(function(z) {
        z.pickerTolerance = tolerance;
        if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) z.color.tolerance = tolerance;
        if (Array.isArray(z.colors)) z.colors.forEach(c => { c.tolerance = tolerance; });
    });
    renderZones(); triggerPreviewRender();
    showToast('All ' + zones.length + ' zones now use \u00B1' + tolerance + ' tolerance');
}
if (typeof window !== 'undefined') { window.setAllZonesTolerance = setAllZonesTolerance; }

// ---------- IMPROVEMENT 61: undo description enhancement — improved labels for common ops ----------
function _enhanceUndoLabel(action, zoneIndex, value) {
    const z = zones[zoneIndex] || {};
    const zname = z.name ? '"' + z.name + '"' : 'Zone ' + (zoneIndex + 1);
    return action + ' on ' + zname + (value !== undefined ? ' \u2192 ' + value : '');
}
if (typeof window !== 'undefined') { window._enhanceUndoLabel = _enhanceUndoLabel; }

// ---------- IMPROVEMENT 62: reset bulk selection on zone reorder ----------
const _origMoveZoneUp = (typeof moveZoneUp === 'function') ? moveZoneUp : null;
const _origMoveZoneDown = (typeof moveZoneDown === 'function') ? moveZoneDown : null;
// (handled via wrappers in window assignments above)

// ---------- IMPROVEMENT 63: ensure init creates zones with locks defined ----------
// (covered by addZone() already setting lockBase/lockPattern/lockIntensity/lockColor)

// ---------- IMPROVEMENT 64: getZoneEffectiveTargetCount — helper for diagnostics ----------
function getZoneEffectiveTargetCount(index) {
    const z = zones[index]; if (!z) return 0;
    if (z.regionMask) {
        let c = 0; for (let i = 0; i < z.regionMask.length; i++) if (z.regionMask[i] > 0) c++;
        return c;
    }
    return -1; // unknown without rendering
}
if (typeof window !== 'undefined') { window.getZoneEffectiveTargetCount = getZoneEffectiveTargetCount; }

// ---------- IMPROVEMENT 65: zone color pill — small swatch for zone summary ----------
function getZoneColorPillHTML(zone) {
    if (!zone) return '';
    let bg = '#444';
    if (zone.colorMode === 'picker' && zone.pickerColor) bg = zone.pickerColor;
    else if (zone.colorMode === 'multi' && zone.colors && zone.colors.length) {
        const colors = zone.colors.slice(0, 4).map(c => c.hex || '#888').join(',');
        bg = 'linear-gradient(90deg, ' + colors + ')';
    }
    else if (zone.colorMode === 'quick' && zone.color) {
        const qc = (typeof QUICK_COLORS !== 'undefined') ? QUICK_COLORS.find(c => c.value === zone.color) : null;
        bg = qc ? qc.bg : '#888';
    }
    else if (zone.colorMode === 'special') bg = (zone.color === 'remaining') ? '#555' : 'linear-gradient(135deg,#888,#ccc)';
    return '<span class="zone-color-pill" style="display:inline-block;width:22px;height:10px;border-radius:3px;background:' + bg + ';border:1px solid #333;vertical-align:middle;" title="Zone color"></span>';
}
if (typeof window !== 'undefined') { window.getZoneColorPillHTML = getZoneColorPillHTML; }

// ---------- IMPROVEMENT 66: comprehensive workflow help getter ----------
function getZoneWorkflowHelp() {
    return [
        { keys: 'N', action: 'Add new zone' },
        { keys: 'M', action: 'Mute / unmute selected zone' },
        { keys: 'Shift+Delete', action: 'Delete selected zone' },
        { keys: 'Ctrl+Up / Down', action: 'Reorder selected zone' },
        { keys: 'Ctrl+Shift+C / V', action: 'Copy / paste zone settings' },
        { keys: 'Ctrl+Shift+D', action: 'Duplicate selected zone' },
        { keys: '/', action: 'Focus zone search' },
        { keys: 'Ctrl+Z / Y', action: 'Undo / redo' },
        { keys: 'Esc', action: 'Cancel current canvas operation' },
    ];
}
if (typeof window !== 'undefined') { window.getZoneWorkflowHelp = getZoneWorkflowHelp; }

// ============================================================
// END ZONE WORKFLOW IMPROVEMENTS (v6.2 — Platinum)
// ============================================================

function exportJSON() {
    const zoneData = zones.map(z => {
        const entry = { name: z.name, finish: z.finish, intensity: z.intensity };
        if (z.customSpec != null) entry.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
        if (z.color !== null) entry.color = z.color;
        return entry;
    });
    const json = JSON.stringify(zoneData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_zones_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast('Zone JSON exported!');
}

// ===== MODAL =====
function openModal() {
    const modal = document.getElementById('scriptModal');
    if (modal) modal.classList.add('active');
    else console.warn('[SPB] scriptModal element not found');
}

function closeModal() {
    const modal = document.getElementById('scriptModal');
    if (modal) modal.classList.remove('active');
}

function copyScript() {
    const el = document.getElementById('scriptOutput');
    if (!el) { showToast('Script output element not found', true); return; }
    const text = el.textContent;
    if (!text) { showToast('No script to copy — generate a script first', true); return; }
    navigator.clipboard.writeText(text).then(() => {
        const fb = document.getElementById('copyFeedback');
        if (fb) {
            fb.classList.add('show');
            setTimeout(() => fb.classList.remove('show'), 2000);
        }
        showToast('Script copied to clipboard');
    }).catch(err => {
        showToast('Copy failed: ' + err.message, true);
    });
}

function saveScriptFile() {
    const scriptEl = document.getElementById('scriptOutput');
    const text = scriptEl ? scriptEl.textContent : '';
    if (!text) { showToast('No script generated yet — click Generate first', true); return; }

    const filenameEl = document.getElementById('scriptFilename');
    let filename = filenameEl ? filenameEl.value.trim() : '';
    if (!filename) filename = 'shokker_multizone.py';
    if (!filename.endsWith('.py')) filename += '.py';

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Saved ${filename}`);
}

function saveBatLauncher() {
    // Generate a .bat file that launches the .py script
    // Uses RUN_ prefix so it won't get confused with browser-renamed .py files
    let pyFilename = document.getElementById('scriptFilename').value.trim();
    if (!pyFilename) pyFilename = 'shokker_multizone.py';
    if (!pyFilename.endsWith('.py')) pyFilename += '.py';

    const driverName = document.getElementById('driverName')?.value.trim() || 'Paint';
    // Use RUN_ prefix so the bat has a distinct name from the .py
    const baseName = pyFilename.replace(/\.py$/, '');
    const batName = `RUN_${baseName}.bat`;

    // ROBUST bat launcher:
    // 1. Auto-unblocks all .py files (fixes Windows Zone.Identifier blocking)
    // 2. Tries exact filename first
    // 3. Falls back to PowerShell to find the NEWEST .py file matching the base name
    //    (handles browser renaming: script.py -> script (1).py, script (2).py, etc.)
    // 4. Last resort: runs the newest .py file in the folder
    const batContent = `@echo off\r
REM Auto-unblock .py files in this folder (browser downloads get Zone.Identifier)\r
powershell -ExecutionPolicy Bypass -Command "Get-ChildItem '%~dp0*.py' | Unblock-File" >nul 2>&1\r
\r
echo ============================================================\r
echo   SHOKKER PAINT BOOTH - ${driverName} Build\r
echo ============================================================\r
echo.\r
\r
REM Try the exact script name first\r
if exist "%~dp0${pyFilename}" (\r
    echo   Running: ${pyFilename}\r
    python "%~dp0${pyFilename}"\r
    goto :done\r
)\r
\r
REM Browser renamed the file - use PowerShell to find newest matching .py\r
echo   ${pyFilename} not found, searching for latest version...\r
for /f "usebackq delims=" %%f in (\`powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Filter '${baseName}*.py' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"\`) do (\r
    echo   Found: %%f\r
    python "%~dp0%%f"\r
    goto :done\r
)\r
\r
REM Last resort: find ANY .py file (newest first, skip RUN_ bat scripts)\r
for /f "usebackq delims=" %%f in (\`powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Filter '*.py' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"\`) do (\r
    echo   Using newest script found: %%f\r
    python "%~dp0%%f"\r
    goto :done\r
)\r
\r
echo   ERROR: No .py scripts found in this folder!\r
echo   Make sure the .py file is in the same folder as this .bat file.\r
echo   Current folder: %~dp0\r
\r
:done\r
echo.\r
echo ============================================================\r
echo   DONE! Check the output files above.\r
echo ============================================================\r
echo.\r
pause\r\n`;

    const blob = new Blob([batContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = batName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Saved ${batName} - double-click to run!`);
}

function getAutoScriptName() {
    const driver = document.getElementById('driverName')?.value.trim() || '';
    const car = document.getElementById('carName')?.value.trim() || '';
    // Use underscores instead of spaces to prevent Windows batch issues
    // and reduce browser rename collisions (script.py -> script (1).py)
    if (driver && car) {
        return `${driver}_${car}.py`.replace(/[<>:"/\\|?*\s]+/g, '_');
    }
    if (driver) return `${driver}.py`.replace(/[<>:"/\\|?*\s]+/g, '_');
    return 'shokker_multizone.py';
}

// ===== ADDITIONAL KEYBOARD SHORTCUTS (tools & view) =====
document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented) return;
    if (e.key === 'Backspace' && canvasMode === 'lasso' && lassoActive && lassoPoints.length > 0) {
        e.preventDefault();
        lassoPoints.pop();
        drawLassoPreview();
        updateDrawZoneIndicator(); // Update point count in hint
        showToast(`Removed last vertex (${lassoPoints.length} points remaining)`);
        return;
    }
    if (e.key === 'Escape') {
        // Cancel active lasso first
        if (canvasMode === 'lasso' && lassoActive && lassoPoints.length > 0) {
            lassoActive = false; lassoPoints = []; hideLassoPreview();
            showToast('Lasso cancelled');
            return;
        }
        if (typeof compareMode !== 'undefined' && compareMode) { toggleCompareMode(); return; }
        if (document.getElementById('finishCompareOverlay')?.classList.contains('active')) { closeFinishCompare(); return; }
        if (document.getElementById('finishBrowserOverlay')?.classList.contains('active')) { closeFinishBrowser(); return; }
        if (document.getElementById('presetGalleryOverlay')?.classList.contains('active')) { closePresetGallery(); return; }
        closeModal();
    }
});

// ===== REGION MASK ENCODING =====
function encodeRegionMaskRLE(mask, width, height) {
    // Run-length encode a binary mask: [[value, count], [value, count], ...]
    // For sparse masks (few drawn areas on big canvas), this compresses massively
    if (!mask) return null;
    const runs = [];
    let currentVal = mask[0];
    let count = 1;
    for (let i = 1; i < mask.length; i++) {
        if (mask[i] === currentVal) {
            count++;
        } else {
            runs.push([currentVal, count]);
            currentVal = mask[i];
            count = 1;
        }
    }
    runs.push([currentVal, count]);
    return { width, height, runs };
}

function hasAnyRegionMasks() {
    return zones.some(z => z.regionMask && z.regionMask.some(v => v > 0));
}

// ===== PATTERN STRENGTH MAP =====
// Globals for brush state
if (typeof window._strengthMapBrushSize === 'undefined') window._strengthMapBrushSize = 20;
if (typeof window._strengthMapBrushValue === 'undefined') window._strengthMapBrushValue = 0;
if (typeof window._strengthMapPainting === 'undefined') window._strengthMapPainting = false;

const STRENGTH_MAP_SIZE = 256; // low-res grayscale canvas dimension

/** Toggle the strength map on/off for a zone */
function toggleStrengthMap(zoneIdx) {
    pushZoneUndo('Toggle strength map');
    const z = zones[zoneIdx];
    z.patternStrengthMapEnabled = !z.patternStrengthMapEnabled;
    if (z.patternStrengthMapEnabled && !z.patternStrengthMap) {
        // Initialize to all-white (100% strength everywhere)
        z.patternStrengthMap = {
            width: STRENGTH_MAP_SIZE,
            height: STRENGTH_MAP_SIZE,
            data: new Uint8Array(STRENGTH_MAP_SIZE * STRENGTH_MAP_SIZE).fill(255)
        };
    }
    renderZoneDetail(zoneIdx);
    // After DOM update, initialize the canvas display
    if (z.patternStrengthMapEnabled) {
        requestAnimationFrame(() => strengthMapRedraw(zoneIdx));
    }
    // FIVE-HOUR SHIFT Win C6: pre-fix this toggled patternStrengthMapEnabled
    // (engine-relevant — hash includes it via patternStrengthMapEnabled +
    // patternStrengthMapSum) but never fired triggerPreviewRender(). Hash
    // can't recompute itself; preview stayed on the old state until painter
    // touched any other control. Same silent-stale class as Wins C1/C2.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

/** Redraw the strength map canvas from zone data */
function strengthMapRedraw(zoneIdx) {
    const z = zones[zoneIdx];
    if (!z || !z.patternStrengthMap) return;
    const canvas = document.getElementById('strengthMapCanvas' + zoneIdx);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = z.patternStrengthMap.width;
    const h = z.patternStrengthMap.height;
    canvas.width = w;
    canvas.height = h;
    const imgData = ctx.createImageData(w, h);
    const data = z.patternStrengthMap.data;
    for (let i = 0; i < data.length; i++) {
        const v = data[i];
        imgData.data[i * 4] = v;       // R
        imgData.data[i * 4 + 1] = v;   // G
        imgData.data[i * 4 + 2] = v;   // B
        imgData.data[i * 4 + 3] = 255; // A
    }
    ctx.putImageData(imgData, 0, 0);
}

/** Start painting on the strength map canvas */
function strengthMapStartPaint(event, zoneIdx) {
    // FIVE-HOUR SHIFT Win H4: pre-fix, the strength-map paint stroke pushed
    // NO undo entry. Painter spent 30s sculpting strength-map gradients,
    // pressed Ctrl+Z, and nothing happened. Push ONE coalesced undo entry
    // at stroke start so the whole stroke is one Ctrl+Z step (matches the
    // canvas brush-stroke contract from marathon).
    if (typeof pushZoneUndo === 'function') {
        pushZoneUndo('Strength map paint', /* isDrag */ true);
    }
    window._strengthMapPainting = true;
    strengthMapPaint(event, zoneIdx);
}

/** Paint on the strength map canvas (mousemove while button held) */
function strengthMapPaint(event, zoneIdx) {
    if (!window._strengthMapPainting) return;
    const z = zones[zoneIdx];
    if (!z || !z.patternStrengthMap) return;
    const canvas = document.getElementById('strengthMapCanvas' + zoneIdx);
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    // Map mouse position to canvas coordinates (canvas may be CSS-scaled)
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const cx = (event.clientX - rect.left) * scaleX;
    const cy = (event.clientY - rect.top) * scaleY;
    const brushR = (window._strengthMapBrushSize || 20) / 2;
    const val = window._strengthMapBrushValue ?? 0;
    const w = z.patternStrengthMap.width;
    const h = z.patternStrengthMap.height;
    const data = z.patternStrengthMap.data;
    const x0 = Math.max(0, Math.floor(cx - brushR));
    const y0 = Math.max(0, Math.floor(cy - brushR));
    const x1 = Math.min(w - 1, Math.ceil(cx + brushR));
    const y1 = Math.min(h - 1, Math.ceil(cy + brushR));
    const rSq = brushR * brushR;
    for (let y = y0; y <= y1; y++) {
        for (let x = x0; x <= x1; x++) {
            const dx = x - cx;
            const dy = y - cy;
            const distSq = dx * dx + dy * dy;
            if (distSq <= rSq) {
                // Soft brush: alpha falloff at edges
                const t = Math.sqrt(distSq) / brushR;
                const alpha = t < 0.7 ? 1.0 : 1.0 - ((t - 0.7) / 0.3);
                const idx = y * w + x;
                data[idx] = Math.round(data[idx] * (1 - alpha) + val * alpha);
            }
        }
    }
    strengthMapRedraw(zoneIdx);
}

/** Stop painting */
function strengthMapStopPaint(zoneIdx) {
    // 2026-04-18 marathon silent-drop fix: pre-fix, painter stroked on the
    // strength-map canvas and _strengthMapPainting was set false on stroke
    // end — but NO Live Preview refresh was triggered, so the preview kept
    // rendering the pre-stroke strength map. Trust break. Also note that
    // getZoneConfigHash now includes a strength-map checksum so the hash
    // actually changes when the data changes (see _strengthMapChecksum).
    const wasPainting = !!window._strengthMapPainting;
    window._strengthMapPainting = false;
    if (wasPainting && typeof triggerPreviewRender === 'function') {
        triggerPreviewRender();
    }
}

/** Fill the entire strength map with a value (0-255) */
function strengthMapFill(zoneIdx, value) {
    const z = zones[zoneIdx];
    if (!z || !z.patternStrengthMap) return;
    pushZoneUndo('Strength map fill');
    z.patternStrengthMap.data.fill(value);
    strengthMapRedraw(zoneIdx);
    // 2026-04-18 marathon silent-drop fix: Fill mutated the data but never
    // poked the preview. Now it does.
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

/** Apply a gradient preset to the strength map */
function strengthMapGradient(zoneIdx, direction) {
    const z = zones[zoneIdx];
    if (!z || !z.patternStrengthMap) return;
    pushZoneUndo('Strength map gradient');
    const w = z.patternStrengthMap.width;
    const h = z.patternStrengthMap.height;
    const data = z.patternStrengthMap.data;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            let v;
            if (direction === 'tb') {
                v = 1.0 - (y / (h - 1)); // top=white, bottom=black
            } else if (direction === 'lr') {
                v = 1.0 - (x / (w - 1)); // left=white, right=black
            } else if (direction === 'center') {
                const cx = (x / (w - 1)) * 2 - 1; // -1 to 1
                const cy = (y / (h - 1)) * 2 - 1;
                const dist = Math.sqrt(cx * cx + cy * cy) / Math.SQRT2; // 0 at center, 1 at corners
                v = 1.0 - dist;
            } else {
                v = 1.0;
            }
            data[y * w + x] = Math.round(Math.max(0, Math.min(1, v)) * 255);
        }
    }
    strengthMapRedraw(zoneIdx);
    // 2026-04-18 marathon silent-drop fix: gradient fill now refreshes the
    // Live Preview (pre-fix the painter saw the gradient change in the
    // strength-map canvas but the rendered car did not update).
    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
}

/** Encode a strength map as RLE for server transmission */
function encodeStrengthMapRLE(strengthMap) {
    if (!strengthMap || !strengthMap.data) return null;
    const data = strengthMap.data;
    const runs = [];
    let currentVal = data[0];
    let count = 1;
    for (let i = 1; i < data.length; i++) {
        if (data[i] === currentVal) {
            count++;
        } else {
            runs.push([currentVal, count]);
            currentVal = data[i];
            count = 1;
        }
    }
    runs.push([currentVal, count]);
    return { width: strengthMap.width, height: strengthMap.height, runs };
}

// ===== FINE TUNING PANEL =====
// State
window._fineTuningOpen = false;
window._fineTuningZone = -1;
window._ftAccordionMode = true;

/**
 * Open the Fine Tuning panel for a given zone index.
 * Hides the Finish Library and shows the Fine Tuning panel with overlay controls.
 */
function openFineTuning(zoneIndex) {
    if (zoneIndex < 0 || zoneIndex >= zones.length) return;
    window._fineTuningOpen = true;
    window._fineTuningZone = zoneIndex;

    // Hide finish library area, show fine tuning panel
    const libHeader = document.querySelector('.right-panel > .section-header');
    const libSearch = document.querySelector('.right-panel > .finish-search-bar');
    const libPanel = document.getElementById('finishLibrary');
    const ftPanel = document.getElementById('fineTuningPanel');
    if (libHeader) libHeader.style.display = 'none';
    if (libSearch) libSearch.style.display = 'none';
    if (libPanel) libPanel.style.display = 'none';
    if (ftPanel) ftPanel.style.display = 'flex';

    // Update title
    const titleEl = document.getElementById('fineTuningTitle');
    if (titleEl) titleEl.textContent = 'FINE TUNING \u2014 Zone ' + (zoneIndex + 1);

    // Build content
    _buildFineTuningContent(zoneIndex);
}

/**
 * Close the Fine Tuning panel and restore the Finish Library.
 */
function closeFineTuning() {
    window._fineTuningOpen = false;
    window._fineTuningZone = -1;

    const libHeader = document.querySelector('.right-panel > .section-header');
    const libSearch = document.querySelector('.right-panel > .finish-search-bar');
    const libPanel = document.getElementById('finishLibrary');
    const ftPanel = document.getElementById('fineTuningPanel');
    if (libHeader) libHeader.style.display = '';
    if (libSearch) libSearch.style.display = '';
    if (libPanel) libPanel.style.display = '';
    if (ftPanel) ftPanel.style.display = 'none';
}

/**
 * Toggle a Fine Tuning section's collapsed state.
 * If accordion mode is on, collapse all other sections first.
 */
function toggleFineTuningSection(n) {
    const section = document.getElementById('ftSection' + n);
    if (!section) return;
    const isCollapsed = section.classList.contains('ft-collapsed');

    if (window._ftAccordionMode && isCollapsed) {
        // Collapse all others first
        document.querySelectorAll('#fineTuningBody .ft-section').forEach(function(s) {
            s.classList.add('ft-collapsed');
        });
    }

    if (isCollapsed) {
        section.classList.remove('ft-collapsed');
    } else {
        section.classList.add('ft-collapsed');
    }
}

/**
 * Build the Fine Tuning panel content by extracting overlay section HTML
 * from the rendered zone detail panel (DOM cloning approach).
 */
function _buildFineTuningContent(zoneIndex) {
    const body = document.getElementById('fineTuningBody');
    if (!body) return;
    body.innerHTML = '';

    const zone = zones[zoneIndex];
    if (!zone) { body.innerHTML = '<div style="padding:16px;color:var(--text-dim);">No zone selected.</div>'; return; }
    if (!zone.base && !zone.finish) { body.innerHTML = '<div style="padding:16px;color:var(--text-dim);">Select a base finish first to enable overlays.</div>'; return; }

    const i = zoneIndex;

    // Define overlay layer info
    const layers = [
        {
            n: 2, key: 'second', label: '2nd Base',
            cssClass: 'ft-2nd',
            hasBase: !!(zone.secondBase || zone.secondBaseColorSource),
            baseName: (zone.secondBase || zone.secondBaseColorSource) ? ((typeof getOverlayBaseDisplay === 'function' ? (getOverlayBaseDisplay(zone.secondBase || zone.secondBaseColorSource) || {}).name : null) || zone.secondBase || zone.secondBaseColorSource || 'Set') : 'None'
        },
        {
            n: 3, key: 'third', label: '3rd Base',
            cssClass: 'ft-3rd',
            hasBase: !!(zone.thirdBase || zone.thirdBaseColorSource),
            baseName: (zone.thirdBase || zone.thirdBaseColorSource) ? ((typeof getOverlayBaseDisplay === 'function' ? (getOverlayBaseDisplay(zone.thirdBase || zone.thirdBaseColorSource) || {}).name : null) || zone.thirdBase || zone.thirdBaseColorSource || 'Set') : 'None'
        },
        {
            n: 4, key: 'fourth', label: '4th Base',
            cssClass: 'ft-4th',
            hasBase: !!(zone.fourthBase || zone.fourthBaseColorSource),
            baseName: (zone.fourthBase || zone.fourthBaseColorSource) ? ((typeof getOverlayBaseDisplay === 'function' ? (getOverlayBaseDisplay(zone.fourthBase || zone.fourthBaseColorSource) || {}).name : null) || zone.fourthBase || zone.fourthBaseColorSource || 'Set') : 'None'
        },
        {
            n: 5, key: 'fifth', label: '5th Base',
            cssClass: 'ft-5th',
            hasBase: !!(zone.fifthBase || zone.fifthBaseColorSource),
            baseName: (zone.fifthBase || zone.fifthBaseColorSource) ? ((typeof getOverlayBaseDisplay === 'function' ? (getOverlayBaseDisplay(zone.fifthBase || zone.fifthBaseColorSource) || {}).name : null) || zone.fifthBase || zone.fifthBaseColorSource || 'Set') : 'None'
        }
    ];

    // Try to clone overlay sections from the rendered zone detail DOM
    const overlayContainer = document.getElementById('sectionOverlays' + i);
    // Find all base-overlay-section elements (or the first overlay-section which is 2nd base)
    let overlaySections = [];
    if (overlayContainer) {
        // The structure: first child after header is the pattern-stack-section (2nd base content),
        // then subsequent .base-overlay-section elements for 3rd, 4th, 5th
        const allSections = overlayContainer.querySelectorAll('.overlay-section');
        overlaySections = Array.from(allSections);
    }

    layers.forEach(function(layer, idx) {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'ft-section ' + layer.cssClass + (idx > 0 ? ' ft-collapsed' : '');
        sectionDiv.id = 'ftSection' + layer.n;

        // Header
        const header = document.createElement('div');
        header.className = 'ft-section-header';
        header.onclick = function() { toggleFineTuningSection(layer.n); };
        header.innerHTML = '<span>' + layer.label + ' <span style="font-size:9px;color:var(--text-dim);">' +
            layer.baseName + '</span>' +
            '<span class="ft-status-dot ' + (layer.hasBase ? 'active' : 'inactive') + '"></span></span>' +
            '<span class="ft-section-arrow">&#9660;</span>';
        sectionDiv.appendChild(header);

        // Body - clone from DOM if available
        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'ft-section-body';

        if (overlaySections[idx]) {
            // Deep clone the overlay section content
            const clone = overlaySections[idx].cloneNode(true);
            // Re-enable all inputs/buttons in clone (cloning preserves state)
            bodyDiv.appendChild(clone);
        } else {
            bodyDiv.innerHTML = '<div style="padding:8px;color:var(--text-dim);font-size:10px;">Overlay controls not available. Open the zone detail panel first.</div>';
        }

        sectionDiv.appendChild(bodyDiv);
        body.appendChild(sectionDiv);
    });
}

/**
 * Refresh the Fine Tuning panel if it is currently open.
 * Called when zones change or a new zone is selected.
 */
function _refreshFineTuningIfOpen() {
    if (!window._fineTuningOpen) return;
    // If the zone changed, update for the new zone
    var zi = (typeof selectedZoneIndex !== 'undefined') ? selectedZoneIndex : window._fineTuningZone;
    if (zi >= 0 && zi < zones.length) {
        window._fineTuningZone = zi;
        var titleEl = document.getElementById('fineTuningTitle');
        if (titleEl) titleEl.textContent = 'FINE TUNING \u2014 Zone ' + (zi + 1);
        _buildFineTuningContent(zi);
    }
}

// ════════════════════════════════════════════════════════════════════
// FINISH DNA — Shareable zone configuration string (#25)
// Format: SHOKK:v1:{base64_encoded_json}
// ════════════════════════════════════════════════════════════════════

/**
 * Extract the DNA payload from a zone — all settings that define its finish appearance.
 */
function _extractZoneDNA(zoneIndex) {
    if (zoneIndex < 0 || zoneIndex >= zones.length) return null;
    var z = zones[zoneIndex];
    // 2026-04-21 HEENAN OVERNIGHT iter 9: switched numeric/boolean
    // `||` to `??` on fields where falsy is legitimate-and-non-default.
    // Pre-fix, a painter with explicit `scale=0` or `baseScale=0`
    // got the default silently promoted in at this capture step,
    // BEFORE the strip layer even ran. Arrays / strings where empty
    // ≈ missing still use `||`.
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
        secondBaseColor: z.secondBaseColor || '#ffffff',
        secondBaseStrength: z.secondBaseStrength ?? 0,
        secondBaseBlendMode: z.secondBaseBlendMode || 'noise',
        secondBaseFractalScale: z.secondBaseFractalScale ?? 24,
        secondBaseScale: z.secondBaseScale ?? 1.0,
        secondBaseColorSource: z.secondBaseColorSource || null,
        secondBaseHueShift: z.secondBaseHueShift ?? 0,
        secondBaseSaturation: z.secondBaseSaturation ?? 0,
        secondBaseBrightness: z.secondBaseBrightness ?? 0,
        // 3rd base overlay
        thirdBase: z.thirdBase || null,
        thirdBaseColor: z.thirdBaseColor || '#ffffff',
        thirdBaseStrength: z.thirdBaseStrength ?? 0,
        thirdBaseBlendMode: z.thirdBaseBlendMode || 'noise',
        thirdBaseFractalScale: z.thirdBaseFractalScale ?? 24,
        thirdBaseScale: z.thirdBaseScale ?? 1.0,
        thirdBaseColorSource: z.thirdBaseColorSource || null,
        thirdBaseHueShift: z.thirdBaseHueShift ?? 0,
        thirdBaseSaturation: z.thirdBaseSaturation ?? 0,
        thirdBaseBrightness: z.thirdBaseBrightness ?? 0,
        // 4th base overlay
        fourthBase: z.fourthBase || null,
        fourthBaseColor: z.fourthBaseColor || '#ffffff',
        fourthBaseStrength: z.fourthBaseStrength ?? 0,
        fourthBaseBlendMode: z.fourthBaseBlendMode || 'noise',
        fourthBaseFractalScale: z.fourthBaseFractalScale ?? 24,
        fourthBaseScale: z.fourthBaseScale ?? 1.0,
        fourthBaseColorSource: z.fourthBaseColorSource || null,
        fourthBaseHueShift: z.fourthBaseHueShift ?? 0,
        fourthBaseSaturation: z.fourthBaseSaturation ?? 0,
        fourthBaseBrightness: z.fourthBaseBrightness ?? 0,
        // 5th base overlay
        fifthBase: z.fifthBase || null,
        fifthBaseColor: z.fifthBaseColor || '#ffffff',
        fifthBaseStrength: z.fifthBaseStrength ?? 0,
        fifthBaseBlendMode: z.fifthBaseBlendMode || 'noise',
        fifthBaseFractalScale: z.fifthBaseFractalScale ?? 24,
        fifthBaseScale: z.fifthBaseScale ?? 1.0,
        fifthBaseColorSource: z.fifthBaseColorSource || null,
        fifthBaseHueShift: z.fifthBaseHueShift ?? 0,
        fifthBaseSaturation: z.fifthBaseSaturation ?? 0,
        fifthBaseBrightness: z.fifthBaseBrightness ?? 0,
    };
    // Strip default/null values to minimize DNA string size.
    // 2026-04-21 HEENAN OVERNIGHT iter 9: the old blanket strip removed
    // any `val === 0` OR `val === false`. That silently lost painter
    // intent on fields where 0 is NOT the canonical load-default — e.g.
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
        // Fields whose canonical default is 1 (NEW strip rules — these
        // were previously mishandled by the blanket val === 0 strip)
        scale: 1.0,
        baseColorStrength: 1,
        baseScale: 1.0,
        secondBaseScale: 1.0, thirdBaseScale: 1.0, fourthBaseScale: 1.0, fifthBaseScale: 1.0,
        // Fields whose canonical default is a specific non-zero number
        secondBaseFractalScale: 24, thirdBaseFractalScale: 24,
        fourthBaseFractalScale: 24, fifthBaseFractalScale: 24,
        // Numeric-with-halving default (offsets)
        baseOffsetX: 0.5, baseOffsetY: 0.5,
        patternOffsetX: 0.5, patternOffsetY: 0.5,
        // Boolean flip fields — default false, safe to strip when false
        baseFlipH: false, baseFlipV: false,
        patternFlipH: false, patternFlipV: false,
        // String defaults
        intensity: '100',
        baseColor: '#ffffff',
        secondBaseColor: '#ffffff', thirdBaseColor: '#ffffff',
        fourthBaseColor: '#ffffff', fifthBaseColor: '#ffffff',
        baseColorMode: 'source',
        basePlacement: 'normal', patternPlacement: 'normal',
        secondBaseBlendMode: 'noise', thirdBaseBlendMode: 'noise',
        fourthBaseBlendMode: 'noise', fifthBaseBlendMode: 'noise',
        gradientDirection: 'horizontal',
        pattern: 'none',
    };

    var cleaned = {};
    for (var key in dna) {
        var val = dna[key];
        // Universal strips: null/undefined are always absent-equivalent.
        if (val === null || val === undefined) continue;
        // Per-field canonical-default strip.
        if (key in _DNA_DEFAULTS && val === _DNA_DEFAULTS[key]) continue;
        // Keep everything else — painter-set falsy values on non-default-0
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
 * Apply a DNA payload to a zone — merges DNA properties onto the existing zone.
 */
function pasteZoneDNA(zoneIndex, dnaStr) {
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
        'baseColorMode', 'baseColor', 'baseColorSource', 'baseColorStrength',
        'gradientStops', 'gradientDirection',
        'baseHueOffset', 'baseSaturationAdjust', 'baseBrightnessAdjust',
        'patternOffsetX', 'patternOffsetY', 'patternFlipH', 'patternFlipV', 'patternPlacement',
        'wear',
        'secondBase', 'secondBaseColor', 'secondBaseStrength', 'secondBaseBlendMode',
        'secondBaseFractalScale', 'secondBaseScale', 'secondBaseColorSource',
        'secondBaseHueShift', 'secondBaseSaturation', 'secondBaseBrightness',
        'thirdBase', 'thirdBaseColor', 'thirdBaseStrength', 'thirdBaseBlendMode',
        'thirdBaseFractalScale', 'thirdBaseScale', 'thirdBaseColorSource',
        'thirdBaseHueShift', 'thirdBaseSaturation', 'thirdBaseBrightness',
        'fourthBase', 'fourthBaseColor', 'fourthBaseStrength', 'fourthBaseBlendMode',
        'fourthBaseFractalScale', 'fourthBaseScale', 'fourthBaseColorSource',
        'fourthBaseHueShift', 'fourthBaseSaturation', 'fourthBaseBrightness',
        'fifthBase', 'fifthBaseColor', 'fifthBaseStrength', 'fifthBaseBlendMode',
        'fifthBaseFractalScale', 'fifthBaseScale', 'fifthBaseColorSource',
        'fifthBaseHueShift', 'fifthBaseSaturation', 'fifthBaseBrightness',
    ];
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
// FINISH MIXER - Blend 2-3 finishes at custom ratios
// ================================================================

var _mixerState = {
    zoneIndex: 0,
    slots: [
        { id: 'chrome', weight: 50 },
        { id: 'candy_burgundy', weight: 50 }
    ],
    previewImg: null,
    panelOpen: false,
    mixMode: 'both',      // 'both', 'color', 'spec'
    activeSlot: -1,      // which slot is picking a base (-1 = none)
    pickerFilter: '',     // search filter text
    pickerCategory: ''    // category filter
};

function openFinishMixer(zoneIndex) {
    _mixerState.zoneIndex = zoneIndex;
    _mixerState.panelOpen = true;
    _mixerState.activeSlot = -1;
    var z = (typeof zones !== 'undefined' && zones[zoneIndex]) ? zones[zoneIndex] : null;
    if (z && z.base) {
        _mixerState.slots[0].id = z.base;
    }
    _renderMixerPanel();
}

function closeMixerPanel() {
    _mixerState.panelOpen = false;
    _mixerState.activeSlot = -1;
    var el = document.getElementById('finishMixerOverlay');
    if (el) el.remove();
}

function _mixerGetBaseName(baseId) {
    if (typeof BASES !== 'undefined') {
        for (var i = 0; i < BASES.length; i++) {
            if (BASES[i].id === baseId) return BASES[i].name;
        }
    }
    if (typeof MONOLITHICS !== 'undefined') {
        for (var i = 0; i < MONOLITHICS.length; i++) {
            if (MONOLITHICS[i].id === baseId) return MONOLITHICS[i].name;
        }
    }
    if (typeof _customMixFinishes !== 'undefined') {
        for (var j = 0; j < _customMixFinishes.length; j++) {
            if (_customMixFinishes[j].id === baseId) return _customMixFinishes[j].name;
        }
    }
    return baseId;
}

function _mixerGetBaseSwatch(baseId) {
    if (typeof BASES !== 'undefined') {
        for (var i = 0; i < BASES.length; i++) {
            if (BASES[i].id === baseId) return BASES[i].swatch || '#444';
        }
    }
    if (typeof MONOLITHICS !== 'undefined') {
        for (var i = 0; i < MONOLITHICS.length; i++) {
            if (MONOLITHICS[i].id === baseId) return MONOLITHICS[i].swatch || '#666';
        }
    }
    return '#e844e8';
}

function _normalizeMixerWeights() {
    var total = 0;
    for (var i = 0; i < _mixerState.slots.length; i++) total += _mixerState.slots[i].weight;
    if (total <= 0) {
        var eq = Math.round(100 / _mixerState.slots.length);
        for (var j = 0; j < _mixerState.slots.length; j++) _mixerState.slots[j].weight = eq;
    }
}

function _mixerSlotChange(idx, newId) {
    _mixerState.slots[idx].id = newId;
    _mixerState.activeSlot = -1;
    _renderMixerPanel();
}

function _mixerWeightChange(idx, val) {
    _mixerState.slots[idx].weight = Math.max(0, Math.min(100, parseInt(val) || 0));
    var lbl = document.getElementById('mixerWtLabel' + idx);
    if (lbl) lbl.textContent = _mixerState.slots[idx].weight + '%';
}

function _mixerAddSlot() {
    if (_mixerState.slots.length >= 3) return;
    _mixerState.slots.push({ id: 'carbon_base', weight: 33 });
    _renderMixerPanel();
}

function _mixerRemoveSlot(idx) {
    if (_mixerState.slots.length <= 2) return;
    _mixerState.slots.splice(idx, 1);
    _renderMixerPanel();
}

function _mixerOpenPicker(slotIdx) {
    _mixerState.activeSlot = slotIdx;
    _mixerState.pickerFilter = '';
    _mixerState.pickerCategory = '';
    _renderMixerPanel();
}

function _mixerClosePicker() {
    _mixerState.activeSlot = -1;
    _renderMixerPanel();
}

function _mixerFilterBases(text) {
    _mixerState.pickerFilter = text.toLowerCase();
    _renderMixerBasePicker();
}

function _mixerSetCategory(cat) {
    _mixerState.pickerCategory = cat;
    _renderMixerBasePicker();
}

function _renderMixerBasePicker() {
    var container = document.getElementById('mixerBasePickerGrid');
    if (!container) return;
    var filter = _mixerState.pickerFilter;
    var cat = _mixerState.pickerCategory;
    var baseGroups = (typeof BASE_GROUPS !== 'undefined') ? BASE_GROUPS : {};
    var specialGroups = (typeof SPECIAL_GROUPS !== 'undefined') ? SPECIAL_GROUPS : {};
    // Merge base + special groups for the mixer (specials are valid mix components)
    var groups = {};
    var bKeys = Object.keys(baseGroups);
    for (var bk = 0; bk < bKeys.length; bk++) groups[bKeys[bk]] = baseGroups[bKeys[bk]];
    var sKeys = Object.keys(specialGroups);
    for (var sk = 0; sk < sKeys.length; sk++) {
        // Don't double-prefix keys that already have ★
        var sKey = sKeys[sk].charAt(0) === '\u2605' ? sKeys[sk] : '\u2605 ' + sKeys[sk];
        groups[sKey] = specialGroups[sKeys[sk]];
    }
    var html = '';

    // Build list of finishes to show (bases + specials)
    var basesToShow = [];
    if (cat && groups[cat]) {
        // Specific category
        var catIds = groups[cat];
        for (var i = 0; i < catIds.length; i++) {
            basesToShow.push(catIds[i]);
        }
    } else {
        // All categories
        var groupKeys = Object.keys(groups);
        for (var g = 0; g < groupKeys.length; g++) {
            var gIds = groups[groupKeys[g]];
            for (var j = 0; j < gIds.length; j++) {
                if (basesToShow.indexOf(gIds[j]) < 0) basesToShow.push(gIds[j]);
            }
        }
    }

    // Apply text filter
    if (filter) {
        basesToShow = basesToShow.filter(function(bid) {
            var name = _mixerGetBaseName(bid).toLowerCase();
            return name.indexOf(filter) >= 0 || bid.toLowerCase().indexOf(filter) >= 0;
        });
    }

    // Add custom mixes
    if (!cat && typeof _customMixFinishes !== 'undefined' && _customMixFinishes.length) {
        for (var c = 0; c < _customMixFinishes.length; c++) {
            var cid = _customMixFinishes[c].id;
            if (!filter || _customMixFinishes[c].name.toLowerCase().indexOf(filter) >= 0) {
                basesToShow.push(cid);
            }
        }
    }

    // Render thumbnail grid — use actual split-view swatch images (same as main picker)
    for (var b = 0; b < basesToShow.length; b++) {
        var bid = basesToShow[b];
        var bname = _mixerGetBaseName(bid);
        var swatchUrl = (typeof getSwatchUrl === 'function') ? getSwatchUrl(bid, '888888', true, 48) : null;
        var fallbackColor = _mixerGetBaseSwatch(bid) || '#444';
        var thumbHtml;
        if (swatchUrl) {
            thumbHtml = '<img src="' + swatchUrl + '" style="width:48px;height:48px;border-radius:4px;border:1px solid #555;object-fit:cover;background:' + fallbackColor + ';" loading="lazy" onerror="this.style.background=\'' + fallbackColor + '\';this.src=\'\';">';
        } else {
            thumbHtml = '<div style="width:48px;height:48px;border-radius:4px;border:1px solid #555;background:' + fallbackColor + ';"></div>';
        }
        html += '<div onclick="_mixerSlotChange(' + _mixerState.activeSlot + ', \'' + bid + '\')" '
            + 'style="cursor:pointer;width:56px;text-align:center;padding:2px;" '
            + 'title="' + bname + '">'
            + thumbHtml
            + '<div style="color:#bbb;font-size:8px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:56px;">' + bname + '</div>'
            + '</div>';
    }

    if (basesToShow.length === 0) {
        html = '<div style="color:#666;padding:20px;text-align:center;">No bases match filter</div>';
    }

    container.innerHTML = html;
}

function _mixerGetZoneColor() {
    // Get the current zone's hex color for the preview (fallback to '888888')
    var zi = _mixerState.zoneIndex;
    var z = (typeof zones !== 'undefined' && zones[zi]) ? zones[zi] : null;
    if (z) {
        // pickerColor is always a string hex like '#3366ff'
        if (z.pickerColor && typeof z.pickerColor === 'string') {
            return z.pickerColor.replace('#', '');
        }
        // z.color can be a string OR an object { color_rgb: [...], tolerance: N }
        if (z.color && typeof z.color === 'string') {
            return z.color.replace('#', '');
        }
        // If z.color is an object with color_rgb, convert to hex
        if (z.color && z.color.color_rgb) {
            var rgb = z.color.color_rgb;
            var r = Math.round(rgb[0] * 255).toString(16).padStart(2, '0');
            var g = Math.round(rgb[1] * 255).toString(16).padStart(2, '0');
            var b = Math.round(rgb[2] * 255).toString(16).padStart(2, '0');
            return r + g + b;
        }
    }
    return '888888';
}

function _mixerPreview() {
    var ids = [];
    var weights = [];
    for (var i = 0; i < _mixerState.slots.length; i++) {
        ids.push(_mixerState.slots[i].id);
        weights.push(_mixerState.slots[i].weight / 100.0);
    }
    var previewEl = document.getElementById('mixerPreviewImg');
    var statusEl = document.getElementById('mixerStatus');
    var specEl = document.getElementById('mixerSpecInfo');
    if (statusEl) statusEl.textContent = 'Generating paint preview...';

    fetch('/api/mix-paint-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finish_ids: ids, weights: weights, seed: 51, color: _mixerGetZoneColor() })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            if (statusEl) statusEl.textContent = 'Error: ' + data.error;
            return;
        }
        if (previewEl) {
            previewEl.src = data.image;
            previewEl.style.display = 'block';
        }
        _mixerState.previewImg = data.image;
        if (statusEl) statusEl.textContent = 'Preview ready';
        if (specEl && data.spec_summary) {
            specEl.textContent = 'M:' + data.spec_summary.M_avg + '  R:' + data.spec_summary.R_avg + '  CC:' + data.spec_summary.CC_avg;
            specEl.style.display = 'block';
        }
    })
    .catch(function(err) {
        if (statusEl) statusEl.textContent = 'Error: ' + err.message;
    });
}

function _mixerApplyDirect() {
    // Apply the mix recipe directly to the active zone without saving
    var zi = _mixerState.zoneIndex;
    var ids = [];
    var weights = [];
    for (var i = 0; i < _mixerState.slots.length; i++) {
        ids.push(_mixerState.slots[i].id);
        weights.push(_mixerState.slots[i].weight / 100.0);
    }
    // Generate a temp name
    var tempName = ids.map(function(id) { return _mixerGetBaseName(id); }).join(' + ');

    // Save as temp custom finish, then apply to zone
    var statusEl = document.getElementById('mixerStatus');
    if (statusEl) statusEl.textContent = 'Applying mix...';

    fetch('/api/save-custom-finish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: tempName, finish_ids: ids, weights: weights, mix_mode: _mixerState.mixMode })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            if (statusEl) statusEl.textContent = 'Error: ' + data.error;
            return;
        }
        // Apply to zone
        if (typeof zones !== 'undefined' && zones[zi]) {
            zones[zi].base = data.id;
            if (typeof updateZonePanel === 'function') updateZonePanel(zi);
        }
        _loadCustomFinishes();
        if (statusEl) statusEl.textContent = 'Applied!';
        if (typeof showToast === 'function') showToast('Mix applied: ' + tempName);
        setTimeout(function() { closeMixerPanel(); }, 600);
    })
    .catch(function(err) {
        if (statusEl) statusEl.textContent = 'Error: ' + err.message;
    });
}

function _mixerSave() {
    var nameInput = document.getElementById('mixerSaveName');
    var name = nameInput ? nameInput.value.trim() : '';
    if (!name) {
        if (typeof showToast === 'function') showToast('Enter a name for your custom finish');
        return;
    }
    var ids = [];
    var weights = [];
    for (var i = 0; i < _mixerState.slots.length; i++) {
        ids.push(_mixerState.slots[i].id);
        weights.push(_mixerState.slots[i].weight / 100.0);
    }
    var statusEl = document.getElementById('mixerStatus');
    if (statusEl) statusEl.textContent = 'Saving...';

    fetch('/api/save-custom-finish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, finish_ids: ids, weights: weights, mix_mode: _mixerState.mixMode })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            if (statusEl) statusEl.textContent = 'Error: ' + data.error;
            return;
        }
        if (statusEl) statusEl.textContent = 'Saved as ' + data.id + '!';
        if (typeof showToast === 'function') showToast('Custom finish saved: ' + data.name);
        _loadCustomFinishes();
    })
    .catch(function(err) {
        if (statusEl) statusEl.textContent = 'Error: ' + err.message;
    });
}

function _mixerDeleteCustom(customId) {
    if (!confirm('Delete custom finish "' + customId + '"?')) return;
    fetch('/api/delete-custom-finish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: customId })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            if (typeof showToast === 'function') showToast('Error: ' + data.error);
            return;
        }
        if (typeof showToast === 'function') showToast('Deleted: ' + customId);
        // Remove from BASES array
        if (typeof BASES !== 'undefined') {
            for (var i = BASES.length - 1; i >= 0; i--) {
                if (BASES[i].id === customId) { BASES.splice(i, 1); break; }
            }
        }
        _loadCustomFinishes();
        _renderMixerPanel();
    })
    .catch(function(err) {
        if (typeof showToast === 'function') showToast('Error: ' + err.message);
    });
}

function _renderMixerPanel() {
    var existing = document.getElementById('finishMixerOverlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'finishMixerOverlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:10000;display:flex;align-items:center;justify-content:center;';
    overlay.onclick = function(e) { if (e.target === overlay) closeMixerPanel(); };

    var picking = _mixerState.activeSlot >= 0;

    // === BUILD SLOT CARDS ===
    var slotsHtml = '';
    for (var i = 0; i < _mixerState.slots.length; i++) {
        var s = _mixerState.slots[i];
        var slotSwatchUrl = (typeof getSwatchUrl === 'function') ? getSwatchUrl(s.id, '888888', true, 40) : null;
        var slotFallback = _mixerGetBaseSwatch(s.id) || '#444';
        var slotThumbHtml = slotSwatchUrl
            ? '<img src="' + slotSwatchUrl + '" style="width:40px;height:40px;border-radius:4px;border:1px solid #555;flex-shrink:0;object-fit:cover;background:' + slotFallback + ';" onerror="this.style.background=\'' + slotFallback + '\';this.src=\'\';">'
            : '<div style="width:40px;height:40px;border-radius:4px;border:1px solid #555;flex-shrink:0;background:' + slotFallback + ';"></div>';
        var removeBtn = _mixerState.slots.length > 2
            ? '<button onclick="event.stopPropagation();_mixerRemoveSlot(' + i + ')" style="position:absolute;top:-4px;right:-4px;background:#c0392b;border:none;color:#fff;width:16px;height:16px;border-radius:50%;font-size:10px;line-height:16px;text-align:center;cursor:pointer;" title="Remove">x</button>'
            : '';
        var activeBorder = (_mixerState.activeSlot === i) ? 'border-color:#e844e8;box-shadow:0 0 8px #e844e8;' : '';
        slotsHtml += '<div style="position:relative;display:flex;align-items:center;gap:8px;background:#1a1a2e;border:1px solid #444;border-radius:6px;padding:8px;margin-bottom:6px;cursor:pointer;' + activeBorder + '" onclick="_mixerOpenPicker(' + i + ')">'
            + removeBtn
            + slotThumbHtml
            + '<div style="flex:1;min-width:0;">'
            + '<div style="color:#eee;font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + _mixerGetBaseName(s.id) + '</div>'
            + '<div style="display:flex;align-items:center;gap:6px;margin-top:4px;">'
            + '<span id="mixerWtLabel' + i + '" style="color:#aaa;font-size:10px;min-width:28px;">' + s.weight + '%</span>'
            + '<input type="range" min="0" max="100" value="' + s.weight + '" oninput="event.stopPropagation();_mixerWeightChange(' + i + ', this.value)" onclick="event.stopPropagation()" style="flex:1;height:4px;accent-color:#e844e8;">'
            + '</div></div></div>';
    }

    var addBtn = _mixerState.slots.length < 3
        ? '<button onclick="_mixerAddSlot()" style="background:none;border:1px dashed #555;color:#888;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:11px;width:100%;margin-bottom:8px;">+ Add 3rd Finish</button>'
        : '';

    // === BUILD CATEGORY TABS (for picker) ===
    var categoryTabsHtml = '';
    if (picking) {
        // Merge BASE_GROUPS + SPECIAL_GROUPS for category tabs
        var allGroups = {};
        if (typeof BASE_GROUPS !== 'undefined') { var bk = Object.keys(BASE_GROUPS); for (var bi = 0; bi < bk.length; bi++) allGroups[bk[bi]] = BASE_GROUPS[bk[bi]]; }
        if (typeof SPECIAL_GROUPS !== 'undefined') { var sk = Object.keys(SPECIAL_GROUPS); for (var si = 0; si < sk.length; si++) { var sKey = sk[si].charAt(0) === '\u2605' ? sk[si] : '\u2605 ' + sk[si]; allGroups[sKey] = SPECIAL_GROUPS[sk[si]]; } }
        var groupKeys = Object.keys(allGroups);
        categoryTabsHtml += '<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:6px;">';
        var allActive = !_mixerState.pickerCategory ? 'background:#e844e8;color:#fff;' : 'background:#222;color:#aaa;';
        categoryTabsHtml += '<button onclick="_mixerSetCategory(\'\')" style="border:none;padding:2px 8px;border-radius:3px;font-size:9px;cursor:pointer;' + allActive + '">All</button>';
        for (var g = 0; g < groupKeys.length; g++) {
            var isActive = _mixerState.pickerCategory === groupKeys[g] ? 'background:#e844e8;color:#fff;' : 'background:#222;color:#aaa;';
            categoryTabsHtml += '<button onclick="_mixerSetCategory(\'' + groupKeys[g].replace(/'/g, "\\'") + '\')" style="border:none;padding:2px 8px;border-radius:3px;font-size:9px;cursor:pointer;' + isActive + '">' + groupKeys[g] + '</button>';
        }
        categoryTabsHtml += '</div>';
    }

    // === BUILD PICKER PANEL ===
    var pickerHtml = '';
    if (picking) {
        pickerHtml = '<div style="border:1px solid #444;border-radius:6px;padding:8px;margin-bottom:10px;max-height:480px;overflow:hidden;display:flex;flex-direction:column;">'
            + '<div style="display:flex;gap:6px;margin-bottom:6px;align-items:center;">'
            + '<span style="color:#e844e8;font-size:11px;font-weight:bold;">Pick for Slot ' + (_mixerState.activeSlot + 1) + '</span>'
            + '<button onclick="_mixerClosePicker()" style="margin-left:auto;background:none;border:1px solid #555;color:#aaa;padding:1px 8px;border-radius:3px;cursor:pointer;font-size:10px;">Done</button>'
            + '</div>'
            + '<input type="text" placeholder="Search bases + specials..." oninput="_mixerFilterBases(this.value)" style="background:#111;color:#eee;border:1px solid #444;padding:4px 8px;border-radius:4px;font-size:11px;margin-bottom:4px;width:100%;box-sizing:border-box;">'
            + '<div style="max-height:60px;overflow-y:auto;margin-bottom:4px;flex-shrink:0;">' + categoryTabsHtml + '</div>'
            + '<div id="mixerBasePickerGrid" style="display:flex;flex-wrap:wrap;gap:4px;overflow-y:auto;flex:1;min-height:150px;align-content:flex-start;padding:4px 0;"></div>'
            + '</div>';
    }

    // === BUILD PREVIEW AREA ===
    var previewImgHtml = _mixerState.previewImg
        ? '<img id="mixerPreviewImg" src="' + _mixerState.previewImg + '" style="width:100%;max-width:400px;height:auto;border:1px solid #444;border-radius:4px;image-rendering:auto;">'
          + '<div style="display:flex;justify-content:space-around;font-size:9px;color:#666;margin-top:2px;"><span>PAINT</span><span>SPEC MAP</span></div>'
        : '<img id="mixerPreviewImg" style="display:none;width:100%;max-width:400px;height:auto;border:1px solid #444;border-radius:4px;image-rendering:auto;">';

    // === BUILD SAVED MIXES LIST ===
    var savedHtml = '';
    if (typeof _customMixFinishes !== 'undefined' && _customMixFinishes.length > 0) {
        savedHtml = '<div style="margin-top:8px;max-height:80px;overflow-y:auto;">';
        for (var s = 0; s < _customMixFinishes.length; s++) {
            var cm = _customMixFinishes[s];
            savedHtml += '<div style="display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px solid #222;">'
                + '<span style="color:#ccc;font-size:10px;flex:1;">' + cm.name + '</span>'
                + '<button onclick="_mixerDeleteCustom(\'' + cm.id + '\')" style="background:none;border:1px solid #c0392b;color:#e74c3c;padding:1px 6px;border-radius:3px;cursor:pointer;font-size:9px;">Del</button>'
                + '</div>';
        }
        savedHtml += '</div>';
    }

    // === ASSEMBLE FULL PANEL ===
    var html = '<div style="background:#12122a;border:1px solid #e844e8;border-radius:10px;padding:18px 20px;width:520px;max-height:92vh;overflow-y:auto;box-shadow:0 8px 32px rgba(232,68,232,0.3);" onclick="event.stopPropagation();">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        + '<h3 style="margin:0;color:#e844e8;font-size:15px;letter-spacing:1px;">&#129514; FINISH MIXER</h3>'
        + '<button onclick="closeMixerPanel()" style="background:none;border:none;color:#888;font-size:18px;cursor:pointer;">&times;</button>'
        + '</div>'
        // Slot cards
        + '<div style="margin-bottom:8px;">' + slotsHtml + '</div>'
        + addBtn
        // Base picker (shown when picking)
        + pickerHtml
        // Action buttons
        + '<div style="display:flex;gap:6px;margin-bottom:10px;">'
        + '<button onclick="_mixerPreview()" style="background:linear-gradient(135deg,#7c3aed,#e844e8);color:#fff;border:none;padding:7px 14px;border-radius:5px;cursor:pointer;font-size:11px;font-weight:bold;flex:1;">&#128065; Preview</button>'
        + '<button onclick="_mixerApplyDirect()" style="background:linear-gradient(135deg,#2563eb,#3b82f6);color:#fff;border:none;padding:7px 14px;border-radius:5px;cursor:pointer;font-size:11px;font-weight:bold;flex:1;">&#9889; Apply to Zone</button>'
        + '</div>'
        // Mix mode selector
        + '<div style="display:flex;gap:4px;margin-bottom:10px;justify-content:center;">'
        + '<span style="color:#888;font-size:10px;align-self:center;margin-right:4px;">Apply:</span>'
        + '<button onclick="_mixerState.mixMode=\'both\';_renderMixerPanel()" style="border:1px solid ' + (_mixerState.mixMode === 'both' ? '#e844e8' : '#444') + ';background:' + (_mixerState.mixMode === 'both' ? '#e844e822' : 'none') + ';color:' + (_mixerState.mixMode === 'both' ? '#e844e8' : '#888') + ';padding:3px 10px;border-radius:3px;cursor:pointer;font-size:10px;font-weight:' + (_mixerState.mixMode === 'both' ? 'bold' : 'normal') + ';">Color + Spec</button>'
        + '<button onclick="_mixerState.mixMode=\'color\';_renderMixerPanel()" style="border:1px solid ' + (_mixerState.mixMode === 'color' ? '#22c55e' : '#444') + ';background:' + (_mixerState.mixMode === 'color' ? '#22c55e22' : 'none') + ';color:' + (_mixerState.mixMode === 'color' ? '#22c55e' : '#888') + ';padding:3px 10px;border-radius:3px;cursor:pointer;font-size:10px;font-weight:' + (_mixerState.mixMode === 'color' ? 'bold' : 'normal') + ';">Color Only</button>'
        + '<button onclick="_mixerState.mixMode=\'spec\';_renderMixerPanel()" style="border:1px solid ' + (_mixerState.mixMode === 'spec' ? '#3b82f6' : '#444') + ';background:' + (_mixerState.mixMode === 'spec' ? '#3b82f622' : 'none') + ';color:' + (_mixerState.mixMode === 'spec' ? '#3b82f6' : '#888') + ';padding:3px 10px;border-radius:3px;cursor:pointer;font-size:10px;font-weight:' + (_mixerState.mixMode === 'spec' ? 'bold' : 'normal') + ';">Spec Only</button>'
        + '</div>'
        // Preview image + spec info
        + '<div style="text-align:center;">' + previewImgHtml
        + '<div id="mixerSpecInfo" style="display:none;color:#888;font-size:10px;margin-top:4px;font-family:monospace;"></div>'
        + '</div>'
        + '<div id="mixerStatus" style="color:#888;font-size:10px;margin-top:6px;text-align:center;min-height:14px;"></div>'
        // Save section
        + '<hr style="border-color:#333;margin:10px 0;">'
        + '<div style="display:flex;gap:6px;align-items:center;">'
        + '<input id="mixerSaveName" type="text" placeholder="My Chrome Candy Carbon" style="flex:1;background:#1a1a2e;color:#eee;border:1px solid #444;padding:6px 8px;border-radius:4px;font-size:11px;">'
        + '<button onclick="_mixerSave()" style="background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:bold;white-space:nowrap;">&#128190; Save</button>'
        + '</div>'
        // Saved custom mixes with delete
        + savedHtml
        + '</div>';

    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    // If picker is open, render the thumbnail grid
    if (picking) {
        _renderMixerBasePicker();
    }
}

// ================================================================
// CUSTOM FINISHES LOADER
// ================================================================

var _customMixFinishes = [];

function _loadCustomFinishes() {
    fetch('/api/custom-finishes')
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!Array.isArray(data)) return;
        _customMixFinishes = data;
        if (typeof BASES !== 'undefined') {
            for (var i = 0; i < data.length; i++) {
                var exists = false;
                for (var j = 0; j < BASES.length; j++) {
                    if (BASES[j].id === data[i].id) { exists = true; break; }
                }
                if (!exists) {
                    var recipe = data[i].finish_ids.join(' + ');
                    BASES.push({
                        id: data[i].id,
                        name: data[i].name,
                        desc: 'Custom mix: ' + recipe,
                        swatch: '#e844e8'
                    });
                }
            }
        }
        if (typeof BASE_GROUPS !== 'undefined' && data.length > 0) {
            var customIds = [];
            for (var k = 0; k < data.length; k++) customIds.push(data[k].id);
            BASE_GROUPS["\u2605 CUSTOM MIXES"] = customIds;
        }
    })
    .catch(function() { /* silent fail */ });
}

if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _loadCustomFinishes);
    } else {
        _loadCustomFinishes();
    }
}

