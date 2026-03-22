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
        document.querySelectorAll('img[src*="/api/swatch/"]').forEach(function (img) {
            let u = img.src.replace(/\bv=\d+\b/, 'v=' + newV);
            if (u.indexOf('nocache=') === -1) u += (u.indexOf('?') >= 0 ? '&' : '?') + 'nocache=1';
            img.src = u;
        });
    } catch (_) { /* ignore */ }
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

// ===== EASY MODE =====
let easyMode = false;
window.easyMode = false;
window.toggleEasyMode = function() {
    easyMode = !easyMode;
    window.easyMode = easyMode;
    document.body.classList.toggle('easy-mode', easyMode);
    const btn = document.getElementById('easy-mode-btn');
    if (btn) {
        btn.textContent = easyMode ? '🎯 EASY MODE' : '⚡ ADVANCED';
        btn.style.color = easyMode ? '#00C8C8' : '#E87A20';
    }
    renderZones();
};

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

let undoActiveDragTimer = null;
function pushZoneUndo(label, isDrag = false) {
    if (isDrag && undoActiveDragTimer) {
        // Extend the timer and skip pushing a new state
        clearTimeout(undoActiveDragTimer);
        undoActiveDragTimer = setTimeout(() => { undoActiveDragTimer = null; }, 500);
        return;
    }
    zoneRedoStack.length = 0; // Clear redo on new action
    const snapshot = JSON.parse(JSON.stringify(
        zones.map(z => ({ ...z, regionMask: null })) // Exclude large masks from undo
    ));
    zoneUndoStack.push({
        label: label || 'Change',
        timestamp: Date.now(),
        snapshot: snapshot,
    });
    if (zoneUndoStack.length > MAX_ZONE_UNDO) zoneUndoStack.shift();
    undoHistoryPointer = zoneUndoStack.length; // Points past top = current state
    renderUndoHistoryPanel();

    if (isDrag) {
        undoActiveDragTimer = setTimeout(() => { undoActiveDragTimer = null; }, 500);
    }
}

function undoZoneChange() {
    if (zoneUndoStack.length === 0) { showToast('Nothing to undo'); return; }
    const currentSnapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null }))));
    const entry = zoneUndoStack.pop();
    zoneRedoStack.push({
        label: entry.label,
        timestamp: Date.now(),
        snapshot: currentSnapshot,
    });
    // Restore zone properties while preserving regionMask
    const masks = zones.map(z => z.regionMask);
    zones.length = 0;
    entry.snapshot.forEach((z, i) => { z.regionMask = masks[i] || null; zones.push(z); });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = zoneUndoStack.length;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Undo: ' + entry.label);
}

function redoZoneChange() {
    if (zoneRedoStack.length === 0) { showToast('Nothing to redo'); return; }
    const currentSnapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null }))));
    const entry = zoneRedoStack.pop();
    zoneUndoStack.push({
        label: entry.label,
        timestamp: Date.now(),
        snapshot: currentSnapshot,
    });
    const masks = zones.map(z => z.regionMask);
    zones.length = 0;
    entry.snapshot.forEach((z, i) => { z.regionMask = masks[i] || null; zones.push(z); });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = zoneUndoStack.length;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Redo: ' + entry.label);
}

function jumpToUndoState(index) {
    // Jump to a specific point in the undo stack
    // index 0 = oldest state, zoneUndoStack.length = current (no undo applied)
    if (index < 0 || index >= zoneUndoStack.length) return;
    const entry = zoneUndoStack[index];
    // Save current state to redo
    const currentSnapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null }))));
    zoneRedoStack.push({ label: 'Jump', timestamp: Date.now(), snapshot: currentSnapshot });
    // Restore
    const masks = zones.map(z => z.regionMask);
    zones.length = 0;
    entry.snapshot.forEach((z, i) => { z.regionMask = masks[i] || null; zones.push(z); });
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
            html += `<div class="undo-history-item${isActive ? ' active' : ''}${dimmed ? ' dimmed' : ''}" onclick="jumpToUndoState(${i})" title="Click to restore this state">
                <span class="undo-history-label">${escapeHtml(e.label)}</span>
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
    if (!confirm('Clear all undo history?')) return;
    zoneUndoStack.length = 0;
    zoneRedoStack.length = 0;
    undoHistoryPointer = -1;
    renderUndoHistoryPanel();
    showToast('Undo history cleared');
}

// Escape: cancel active canvas operation (lasso / rect drag) so Escape feels like Photoshop/GIMP
window.cancelCanvasOperation = function () {
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

// Keyboard shortcuts: Ctrl+Z = undo, Ctrl+Y / Ctrl+Shift+Z = redo
// UNIFIED: prefers draw/mask undo (undoStack) over zone history undo (zoneUndoStack)
document.addEventListener('keydown', function (e) {
    // Skip if focused on input/textarea/select
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        // If there are draw/mask actions to undo, do those first; else undo zone config change
        if (typeof undoStack !== 'undefined' && undoStack.length > 0) {
            undoDrawStroke();
        } else {
            undoZoneChange();
        }
    } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        // Prefer draw/mask redo when available; else zone config redo
        if (typeof redoStack !== 'undefined' && redoStack.length > 0 && typeof redoDrawStroke === 'function') {
            redoDrawStroke();
        } else {
            redoZoneChange();
        }
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
            name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", finish: null, intensity: "80", colorMode: "quick", pickerColor: "#222222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Auto-catches dark/black areas - matte carbon fiber by default"
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
                ? (MONOLITHICS.find(m => m.id === zone.finish)?.name || zone.finish) +
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
            html += `<div class="zone-card${accordionClass}${mutedClass}" onclick="selectZone(${i})" id="zone-card-${i}"
            ondragover="zoneDragOver(event,${i})" ondragenter="zoneDragEnter(event,${i})" ondragleave="zoneDragLeave(event)" ondrop="zoneDrop(event,${i})" ondragend="zoneDragEnd(event)">
            <div class="zone-card-header">
                <span class="zone-drag-handle" draggable="true" ondragstart="zoneDragStart(event,${i})" title="Drag to reorder">&#x2630;</span>
                <span class="zone-number">${i + 1}</span>
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
    container.innerHTML = html;
    // Render the detail panel for selected zone
    renderZoneDetail(selectedZoneIndex);
    // Auto-save after any zone change
    if (typeof autoSave === 'function') autoSave();
    // Update onboarding hints
    if (typeof updateOnboardingHints === 'function') updateOnboardingHints();
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
    // Grab current hex input value or picker color and ADD it to the zone's colors array
    const zone = zones[zoneIndex];
    const hex = zone.pickerColor || '#3366ff';
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    const tol = zone.pickerTolerance || 40;

    // Check for duplicate
    if (zone.colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
        showToast('That color is already added to this zone', true);
        return;
    }

    zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
    zone.colorMode = 'multi';
    zone.color = zone.colors; // color becomes the array
    renderZones();
    showToast(`Added ${hex.toUpperCase()} to ${zone.name} (${zone.colors.length} colors stacked)`);
}

function removeColorFromZone(zoneIndex, colorIndex) {
    const zone = zones[zoneIndex];
    zone.colors.splice(colorIndex, 1);
    if (zone.colors.length === 0) {
        zone.colorMode = 'none';
        zone.color = null;
    } else {
        zone.color = zone.colors;
    }
    renderZones();
}

function updateColorTolerance(zoneIndex, colorIndex, value) {
    const zone = zones[zoneIndex];
    if (zone.colors && zone.colors[colorIndex]) {
        zone.colors[colorIndex].tolerance = value;
        zone.color = zone.colors;
        triggerPreviewRender();
    }
}

function clearZoneColors(zoneIndex) {
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

    // Build the detail panel HTML with all zone controls
    let html = '';

    // Header bar
    html += `<div class="zone-detail-header">
        <span class="zone-number">${i + 1}</span>
        <span class="zone-detail-title">${escapeHtml(zone.name)}</span>
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
        <div class="color-selector-label">What pixels does this zone cover?</div>
        <div class="color-selector-help">Pick a color below, type a color name, enter a hex code, or use the eyedropper on your paint</div>
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
            <input class="color-picker-input" type="color" value="${zone.pickerColor || '#3366ff'}"
                onchange="setPickerColor(${i}, this.value)"
                title="Color picker">
        </div>
        <div class="color-tol-row">
            <span class="tol-label">TOL:</span>
            <input class="tolerance-slider" type="range" min="5" max="100" value="${zone.pickerTolerance || 40}"
                onchange="setPickerTolerance(${i}, this.value)"
                title="How loosely colors are matched — low = exact, high = approximate">
            <span class="tolerance-val">&plusmn;${zone.pickerTolerance || 40}</span>
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
    html += `<div class="zone-finish-row">
        <label style="color:var(--accent-gold, #FFB300); font-weight:700;">Base</label>
        <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'base', ${i})" title="The base material that defines how light interacts with this zone&#39;s surface">
            ${zone.finish ? renderSwatchDot(zone.finish, getSwatchColor(zone), getZoneColorHex(zone)) : zone.base ? renderSwatchDot(zone.base, getSwatchColor(zone), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
            <span class="swatch-name">${getBaseName(zone)}</span>
            <span class="swatch-arrow">&#9662;</span>
        </div>
        <span class="lock-toggle${zone.lockBase ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockBase')" title="Lock base during randomize">${zone.lockBase ? '&#128274;' : '&#128275;'}</span>
        <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishBrowser(${i})" title="Opens a full-screen gallery of all finishes with thumbnail previews. Filter by type, search by name, click to apply." style="padding:1px 6px; font-size:9px; margin-left:2px; border-color:var(--accent-gold); color:var(--accent-gold);">🎨 Browse</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishCompare(${i})" title="Compare two finishes side-by-side on your car" style="padding:1px 6px; font-size:9px; border-color:var(--accent-blue); color:var(--accent-blue);">🔍 Compare</button>
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
                <span class="stack-label-mini">Base Color</span>
                <select class="mini-select" style="min-width:150px;" onchange="setZoneBaseColorMode(${i}, this.value)">
                    <option value="source" ${_baseColorMode === 'source' ? 'selected' : ''}>Use source paint</option>
                    <option value="solid" ${_baseColorMode === 'solid' ? 'selected' : ''}>Use solid color</option>
                    <option value="special" ${_baseColorMode === 'special' ? 'selected' : ''}>From special</option>
                </select>
                ${_baseColorMode === 'solid' ? `<input type="color" value="${_baseColorHex}" onchange="setZoneBaseColor(${i}, this.value)" title="Pick base tint">` : ''}
                ${_baseColorMode === 'solid' ? `<input type="text" value="${_baseColorHex}" onchange="setZoneBaseColor(${i}, this.value)" style="width:78px;font-size:10px;">` : ''}
                ${_baseColorMode === 'special' ? `<div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'baseColorSource', ${i})" title="Pick special color source" style="display:inline-flex;align-items:center;gap:6px;">
                    ${_baseSrcId ? renderSwatchDot(_baseSrcId, _baseSrcSwatch, _baseColorHex) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                    <span class="swatch-name">${_baseSrcName}</span>
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
            </div>` : ''}
            <div class="hsb-controls" style="display:flex; align-items:center; gap:8px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:62px;">Hue Shift</span>
                <input type="range" min="-180" max="180" step="5" value="${_baseHueOffset}" oninput="setZoneBaseHueOffset(${i}, this.value)" class="stack-slider" title="Shift all colors around the color wheel — negative = cool, positive = warm">
                <span class="stack-val" id="detBaseHueVal${i}" style="min-width:32px;">${_baseHueOffset}°</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseHueOffset(${i}, 0)" title="Reset" style="padding:0 4px;font-size:9px;">↺</button>
            </div>
            <div class="hsb-controls" style="display:flex; align-items:center; gap:8px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:62px;">Saturation</span>
                <input type="range" min="-100" max="100" step="5" value="${_baseSatAdj}" oninput="setZoneBaseSaturation(${i}, this.value)" class="stack-slider" title="Color intensity — negative = more grey, positive = more vivid">
                <span class="stack-val" id="detBaseSatVal${i}" style="min-width:32px;">${_baseSatAdj}</span>
                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); setZoneBaseSaturation(${i}, 0)" title="Reset" style="padding:0 4px;font-size:9px;">↺</button>
            </div>
            <div class="hsb-controls" style="display:flex; align-items:center; gap:8px; width:100%; flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:62px;">Brightness</span>
                <input type="range" min="-100" max="100" step="5" value="${_baseBrightAdj}" oninput="setZoneBaseBrightness(${i}, this.value)" class="stack-slider" title="Overall lightness — negative = darker, positive = brighter">
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
                    <span style="font-size:10px; color:var(--text);">${spName}</span>
                    <span style="font-size:8px; color:var(--text-dim);">${spDef ? spDef.desc : ''}</span>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); removeSpecPatternLayer(${i}, ${si})" title="Remove" style="margin-left:auto; padding:0px 5px; font-size:9px; line-height:1.2;">&times;</button>
                </div>
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
            </div>`;
        });

        if (specStack.length < MAX_SPEC_PATTERN_LAYERS) {
            specPatternsHtml += `<div style="margin-top:4px;">
                <div id="specPatternGrid${i}" style="display:none; flex-wrap:wrap; gap:4px; max-height:200px; overflow-y:auto; padding:4px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">`;
            (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                specPatternsHtml += `<div onclick="addSpecPatternLayer(${i}, '${sp.id}'); document.getElementById('specPatternGrid${i}').style.display='none';"
                    style="cursor:pointer; width:128px; padding:3px; background:var(--bg-input,#1a1a2e); border:1px solid var(--border,#333); border-radius:3px; text-align:center; transition:border-color 0.15s;"
                    onmouseover="this.style.borderColor='#f59e0b'" onmouseout="this.style.borderColor='var(--border,#333)'"
                    title="${sp.desc}">
                    <img src="/api/spec-pattern-preview/${sp.id}" alt="${sp.name}" style="width:120px; height:40px; object-fit:cover; border-radius:2px; display:block; margin:0 auto;" onerror="this.style.display='none'">
                    <div style="font-size:8px; color:var(--text,#e0e0e0); margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${sp.name}</div>
                </div>`;
            });
            specPatternsHtml += `</div>
                <button onclick="const g=document.getElementById('specPatternGrid${i}'); g.style.display=g.style.display==='none'?'flex':'none';" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #ff444444; color:#ff4444; margin-top:4px;">
                    + Add Spec Pattern (click to browse)
                </button>
            </div>`;
        } else {
            specPatternsHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 5 spec pattern layers reached.</div>';
        }

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
                    <span class="stack-label-mini">Spec Strength</span>
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
            <div class="base-position-controls" style="display:flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; width: 100%; margin-top: 6px;">
                <span class="stack-label-mini" style="white-space:nowrap;">Base position</span>
                <div class="stack-control-group" style="flex: 1; min-width: 90px;">
                    <span class="stack-label-mini">Pos X</span>
                    <input type="range" min="0" max="100" step="1" value="${Math.round((zone.baseOffsetX ?? 0.5) * 100)}" oninput="setZoneBaseOffsetX(${i}, this.value)" class="stack-slider" title="Pan base left/right">
                    <span class="stack-val" id="detBasePosXVal${i}">${Math.round((zone.baseOffsetX ?? 0.5) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="flex: 1; min-width: 90px;">
                    <span class="stack-label-mini">Pos Y</span>
                    <input type="range" min="0" max="100" step="1" value="${Math.round((zone.baseOffsetY ?? 0.5) * 100)}" oninput="setZoneBaseOffsetY(${i}, this.value)" class="stack-slider" title="Pan base up/down">
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
                    <div class="stack-control-group" style="margin-bottom:8px; padding:8px 10px; background:rgba(0,0,0,0.3); border:1px dotted var(--border,#2a2a4a); border-radius:4px;">
                        <span class="stack-label-mini" style="margin-right:8px;">Place on map</span>
                        <select id="placementLayerSelect${i}" onchange="setPlacementLayer(this.value); updatePlacementBanner();" style="font-size:10px; padding:4px 8px; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:4px; min-width:140px;" title="Then click and drag on the source map to move this layer">
                            <option value="none" ${placementLayer === 'none' ? 'selected' : ''}>- None -</option>
                            ${hasBaseForPlacement ? `<option value="base" ${placementLayer === 'base' ? 'selected' : ''}>Base (gradient/duo)</option>` : ''}
                            ${hasPrimaryPattern ? `<option value="pattern" ${placementLayer === 'pattern' ? 'selected' : ''}>Primary pattern</option>` : ''}
                            ${hasSecondBasePattern ? `<option value="second_base" ${placementLayer === 'second_base' ? 'selected' : ''}>2nd base overlay</option>` : ''}
                            ${hasThirdBasePattern ? `<option value="third_base" ${placementLayer === 'third_base' ? 'selected' : ''}>3rd base overlay</option>` : ''}
                            ${hasFourthBasePattern ? `<option value="fourth_base" ${placementLayer === 'fourth_base' ? 'selected' : ''}>4th base overlay</option>` : ''}
                            ${hasFifthBasePattern ? `<option value="fifth_base" ${placementLayer === 'fifth_base' ? 'selected' : ''}>5th base overlay</option>` : ''}
                        </select>
                        <div style="font-size:9px; color:var(--text-dim); margin-top:4px; width:100%;">When active, the <strong>source map</strong> gets a blue border - click and drag there to move.</div>
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
                        pHtml += `
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
                        <div class="zone-target-mode" style="margin: 6px 0; display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                            <label style="color: #aaa; font-size: 11px; white-space: nowrap;">Pattern Placement:</label>
                            <select onchange="zones[${i}].patternPlacement = this.value; if(this.value === 'manual') { activateManualPlacement(${i}); } renderZones();"
                                    style="background: #1a1a1a; color: #ccc; border: 1px solid #333; padding: 2px 6px; font-size: 11px;"
                                    title="Full Canvas tiles across the whole car; Fit to Zone concentrates the pattern into just this zone; Manual lets you drag to position">
                                <option value="normal" ${zone.patternPlacement !== 'fit' && zone.patternPlacement !== 'manual' ? 'selected' : ''}>Full Canvas (Normal)</option>
                                <option value="fit" ${zone.patternPlacement === 'fit' ? 'selected' : ''}>Fit to Zone</option>
                                <option value="manual" ${zone.patternPlacement === 'manual' ? 'selected' : ''}>Manual Placement</option>
                            </select>
                            <span class="whats-this" onclick="event.stopPropagation(); var p=this.nextElementSibling; p.style.display=p.style.display===\'none\'?\'block\':\'none\';" title="Click for explanation">?</span>
                            <div class="whats-this-panel" style="display:none; width:100%;">Concentrates the pattern into just this zone&#39;s area instead of spreading across the full canvas. Great for small zones like car numbers. Manual lets you drag on the preview to position it.</div>
                        </div>
                        <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                            <input type="range" min="0" max="100" step="1" value="${Math.round((zone.patternOffsetX ?? 0.5) * 100)}" oninput="setZonePatternOffsetX(${i}, this.value)" class="stack-slider" title="Slide the pattern left/right across the canvas" ${zone.patternPlacement === 'fit' ? 'disabled style="opacity:0.35;pointer-events:none;"' : ''}>
                            <span class="stack-val" id="detPatPosXVal${i}" ${zone.patternPlacement === 'fit' ? 'style="opacity:0.35;"' : ''}>${Math.round((zone.patternOffsetX ?? 0.5) * 100)}%</span></div>
                        <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                            <input type="range" min="0" max="100" step="1" value="${Math.round((zone.patternOffsetY ?? 0.5) * 100)}" oninput="setZonePatternOffsetY(${i}, this.value)" class="stack-slider" title="Slide the pattern up/down across the canvas" ${zone.patternPlacement === 'fit' ? 'disabled style="opacity:0.35;pointer-events:none;"' : ''}>
                            <span class="stack-val" id="detPatPosYVal${i}" ${zone.patternPlacement === 'fit' ? 'style="opacity:0.35;"' : ''}>${Math.round((zone.patternOffsetY ?? 0.5) * 100)}%</span></div>
                        <div class="stack-control-group" style="flex-wrap:wrap; gap:6px;">
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Mirror the pattern horizontally"><input type="checkbox" ${(zone.patternFlipH || false) ? 'checked' : ''} onchange="setZonePatternFlipH(${i}, this.checked)"> Flip H</label>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Mirror the pattern vertically"><input type="checkbox" ${(zone.patternFlipV || false) ? 'checked' : ''} onchange="setZonePatternFlipV(${i}, this.checked)"> Flip V</label>
                        </div>
                        <div class="stack-control-group"><span class="stack-label-mini">Strength</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternSpecMult(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.patternSpecMult ?? 1) * 100)}" oninput="setZonePatternSpecMult(${i}, this.value)" class="stack-slider" title="Pattern punch (spec map), 5% steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZonePatternSpecMult(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detPatStrVal${i}">${Math.round((zone.patternSpecMult ?? 1) * 100)}%</span></div>`;
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
                        <input type="radio" name="sbColorSource${i}" value="solid" ${!zone.secondBaseColorSource ? 'checked' : ''} onchange="setZoneSecondBaseColorSource(${i}, null)">
                        <span>Solid</span>
                    </label>
                    <span style="display:flex;align-items:center;gap:4px;"> <input type="color" value="${zone.secondBaseColor || '#ffffff'}"
                        onchange="setZoneSecondBaseColor(${i}, this.value)"
                        title="Paint color for the overlay"
                        style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                    <input type="text" value="${zone.secondBaseColor || '#ffffff'}" onchange="setZoneSecondBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color (e.g. Bronze Heat stays bronze/gold)">
                        <input type="radio" name="sbColorSource${i}" value="overlay" ${zone.secondBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneSecondBaseColorSourceToOverlay(${i})">
                        <span>Same as overlay</span>
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;">
                        <input type="radio" name="sbColorSource${i}" value="special" ${zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'second' }; setZoneSecondBaseColorSource(${i}, '${(zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('mono:') ? zone.secondBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')">
                        <span>From special</span>
                    </label>
                    ${zone.secondBaseColorSource && zone.secondBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'second') : ''}
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBaseStrength || 0) * 100)}"
                        oninput="setZoneSecondBaseStrength(${i}, this.value)"
                        class="stack-slider" title="0%=primary only, 100%=overlay only, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detSBStrVal${i}">${Math.round((zone.secondBaseStrength || 0) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneSecondBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detSBSpecStrVal${i}">${Math.round((zone.secondBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
                ` : ''}
                ${(zone.secondBase || zone.secondBaseColorSource) ? (() => {
                    const ovSpecStack = zone.overlaySpecPatternStack || [];
                    const ovSpecStackActive = ovSpecStack.length > 0;
                    const MAX_OVERLAY_SPEC_PATTERN_LAYERS = 3;
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
                        ovSpHtml += `<div style="margin-top:4px;">
                            <div id="overlaySpecPatternGrid${i}" style="display:none; flex-wrap:wrap; gap:4px; max-height:200px; overflow-y:auto; padding:4px; background:var(--bg-card,#16162a); border:1px solid var(--border,#2a2a4a); border-radius:4px;">`;
                        (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).forEach(sp => {
                            ovSpHtml += `<div onclick="addOverlaySpecPatternLayer(${i}, '${sp.id}'); document.getElementById('overlaySpecPatternGrid${i}').style.display='none';"
                                style="cursor:pointer; width:128px; padding:3px; background:var(--bg-input,#1a1a2e); border:1px solid var(--border,#333); border-radius:3px; text-align:center; transition:border-color 0.15s;"
                                onmouseover="this.style.borderColor='#c084fc'" onmouseout="this.style.borderColor='var(--border,#333)'"
                                title="${sp.desc}">
                                <img src="/api/spec-pattern-preview/${sp.id}" alt="${sp.name}" style="width:120px; height:40px; object-fit:cover; border-radius:2px; display:block; margin:0 auto;" onerror="this.style.display='none'">
                                <div style="font-size:8px; color:var(--text,#e0e0e0); margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${sp.name}</div>
                            </div>`;
                        });
                        ovSpHtml += `</div>
                            <button onclick="const g=document.getElementById('overlaySpecPatternGrid${i}'); g.style.display=g.style.display==='none'?'flex':'none';" class="btn btn-sm" style="width:100%; font-size:10px; padding:4px 6px; border:1px solid #c084fc44; color:#c084fc; margin-top:4px;">
                                + Add Overlay Spec Pattern (click to browse)
                            </button>
                        </div>`;
                    } else {
                        ovSpHtml += '<div style="font-size:9px; color:var(--text-dim); margin-top:4px;">Maximum 3 overlay spec pattern layers reached.</div>';
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
                    <div class="stack-control-group"><span class="stack-label-mini">Strength</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBasePatternStrength ?? 1) * 100)}" oninput="setZoneSecondBasePatternStrength(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSecondBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detSBPatStrVal${i}">${Math.round((zone.secondBasePatternStrength ?? 1) * 100)}%</span></div>
                    <div class="zone-target-mode" style="margin: 6px 0; display: flex; gap: 6px; align-items: center;">
                        <label style="color: #aaa; font-size: 11px;">Overlay Placement:</label>
                        <select onchange="zones[${i}].secondBaseFitZone = this.value === 'fit'; renderZones();"
                                style="background: #1a1a1a; color: #ccc; border: 1px solid #333; padding: 2px 6px; font-size: 11px;">
                            <option value="normal" ${!zone.secondBaseFitZone ? 'selected' : ''}>Full Canvas</option>
                            <option value="fit" ${zone.secondBaseFitZone ? 'selected' : ''}>Fit to Zone</option>
                        </select>
                    </div>
                    <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                        <input type="range" min="0" max="100" step="1" value="${Math.round((zone.secondBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneSecondBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right">
                        <span class="stack-val" id="detSBPatPosXVal${i}">${Math.round((zone.secondBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                        <input type="range" min="0" max="100" step="1" value="${Math.round((zone.secondBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneSecondBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down">
                        <span class="stack-val" id="detSBPatPosYVal${i}">${Math.round((zone.secondBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group" style="margin-top:6px;">
                        <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); alignSecondBaseOverlayWithSelectedPattern(${i})" title="Copy primary pattern position, scale, and rotation so the 2nd overlay lines up exactly (e.g. after you moved/resized the pattern on the map)">
                            ✓ Align with selected pattern
                        </button>
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
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="tbColorSource${i}" value="solid" ${!zone.thirdBaseColorSource ? 'checked' : ''} onchange="setZoneThirdBaseColorSource(${i}, null)"><span>Solid</span></label>
                    <span style="display:flex;align-items:center;gap:4px;"><input type="color" value="${zone.thirdBaseColor || '#ffffff'}" onchange="setZoneThirdBaseColor(${i}, this.value)" style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                    <input type="text" value="${zone.thirdBaseColor || '#ffffff'}" onchange="setZoneThirdBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color"><input type="radio" name="tbColorSource${i}" value="overlay" ${zone.thirdBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneThirdBaseColorSourceToOverlay(${i})"><span>Same as overlay</span></label>
                    <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="tbColorSource${i}" value="special" ${zone.thirdBaseColorSource && zone.thirdBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'third' }; setZoneThirdBaseColorSource(${i}, '${(zone.thirdBaseColorSource && zone.thirdBaseColorSource.startsWith('mono:') ? zone.thirdBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')"><span>From special</span></label>
                    ${zone.thirdBaseColorSource && zone.thirdBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'third') : ''}
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBaseStrength || 0) * 100)}"
                        oninput="setZoneThirdBaseStrength(${i}, this.value)"
                        class="stack-slider" title="3rd overlay strength, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detTBStrVal${i}">${Math.round((zone.thirdBaseStrength || 0) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneThirdBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detTBSpecStrVal${i}">${Math.round((zone.thirdBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
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
                    <div class="stack-control-group"><span class="stack-label-mini">Strength</span>
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                        <input type="range" min="0" max="100" step="5" value="${Math.round((zone.thirdBasePatternStrength ?? 1) * 100)}" oninput="setZoneThirdBasePatternStrength(${i}, this.value)" class="stack-slider">
                        <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneThirdBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                        <span class="stack-val" id="detTBPatStrVal${i}">${Math.round((zone.thirdBasePatternStrength ?? 1) * 100)}%</span></div>
                    <div class="zone-target-mode" style="margin: 6px 0; display: flex; gap: 6px; align-items: center;">
                        <label style="color: #aaa; font-size: 11px;">Overlay Placement:</label>
                        <select onchange="zones[${i}].thirdBaseFitZone = this.value === 'fit'; renderZones();"
                                style="background: #1a1a1a; color: #ccc; border: 1px solid #333; padding: 2px 6px; font-size: 11px;">
                            <option value="normal" ${!zone.thirdBaseFitZone ? 'selected' : ''}>Full Canvas</option>
                            <option value="fit" ${zone.thirdBaseFitZone ? 'selected' : ''}>Fit to Zone</option>
                        </select>
                    </div>
                    <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                        <input type="range" min="0" max="100" step="1" value="${Math.round((zone.thirdBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneThirdBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right">
                        <span class="stack-val" id="detTBPatPosXVal${i}">${Math.round((zone.thirdBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                    <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                        <input type="range" min="0" max="100" step="1" value="${Math.round((zone.thirdBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneThirdBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down">
                        <span class="stack-val" id="detTBPatPosYVal${i}">${Math.round((zone.thirdBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
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
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fbColorSource${i}" value="solid" ${!zone.fourthBaseColorSource ? 'checked' : ''} onchange="setZoneFourthBaseColorSource(${i}, null)"><span>Solid</span></label>
                            <span style="display:flex;align-items:center;gap:4px;"><input type="color" value="${zone.fourthBaseColor || '#ffffff'}" onchange="setZoneFourthBaseColor(${i}, this.value)" style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                            <input type="text" value="${zone.fourthBaseColor || '#ffffff'}" onchange="setZoneFourthBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color"><input type="radio" name="fbColorSource${i}" value="overlay" ${zone.fourthBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneFourthBaseColorSourceToOverlay(${i})"><span>Same as overlay</span></label>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fbColorSource${i}" value="special" ${zone.fourthBaseColorSource && zone.fourthBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'fourth' }; setZoneFourthBaseColorSource(${i}, '${(zone.fourthBaseColorSource && zone.fourthBaseColorSource.startsWith('mono:') ? zone.fourthBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')"><span>From special</span></label>
                            ${zone.fourthBaseColorSource && zone.fourthBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'fourth') : ''}
                        </div>
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini">Strength</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBaseStrength || 0) * 100)}" oninput="setZoneFourthBaseStrength(${i}, this.value)" class="stack-slider" title="4th overlay strength, 5% steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFBStrVal${i}">${Math.round((zone.fourthBaseStrength || 0) * 100)}%</span>
                        </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneFourthBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detFBSpecStrVal${i}">${Math.round((zone.fourthBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
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
                            <div class="stack-control-group"><span class="stack-label-mini">Strength</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fourthBasePatternStrength ?? 1) * 100)}" oninput="setZoneFourthBasePatternStrength(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFourthBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFBPatStrVal${i}">${Math.round((zone.fourthBasePatternStrength ?? 1) * 100)}%</span></div>
                            <div class="zone-target-mode" style="margin: 6px 0; display: flex; gap: 6px; align-items: center;">
                                <label style="color: #aaa; font-size: 11px;">Overlay Placement:</label>
                                <select onchange="zones[${i}].fourthBaseFitZone = this.value === 'fit'; renderZones();"
                                        style="background: #1a1a1a; color: #ccc; border: 1px solid #333; padding: 2px 6px; font-size: 11px;">
                                    <option value="normal" ${!zone.fourthBaseFitZone ? 'selected' : ''}>Full Canvas</option>
                                    <option value="fit" ${zone.fourthBaseFitZone ? 'selected' : ''}>Fit to Zone</option>
                                </select>
                            </div>
                            <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                                <input type="range" min="0" max="100" step="1" value="${Math.round((zone.fourthBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneFourthBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right">
                                <span class="stack-val" id="detFBPatPosXVal${i}">${Math.round((zone.fourthBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                                <input type="range" min="0" max="100" step="1" value="${Math.round((zone.fourthBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneFourthBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down">
                                <span class="stack-val" id="detFBPatPosYVal${i}">${Math.round((zone.fourthBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
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
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fifColorSource${i}" value="solid" ${!zone.fifthBaseColorSource ? 'checked' : ''} onchange="setZoneFifthBaseColorSource(${i}, null)"><span>Solid</span></label>
                            <span style="display:flex;align-items:center;gap:4px;"><input type="color" value="${zone.fifthBaseColor || '#ffffff'}" onchange="setZoneFifthBaseColor(${i}, this.value)" style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                            <input type="text" value="${zone.fifthBaseColor || '#ffffff'}" onchange="setZoneFifthBaseColor(${i}, this.value)" style="font-size:9px;color:var(--text-dim);width:45px;background:none;border:none;" maxlength="7"></span>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;" title="Use the overlay base's own color"><input type="radio" name="fifColorSource${i}" value="overlay" ${zone.fifthBaseColorSource === 'overlay' ? 'checked' : ''} onchange="setZoneFifthBaseColorSourceToOverlay(${i})"><span>Same as overlay</span></label>
                            <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:10px;"><input type="radio" name="fifColorSource${i}" value="special" ${zone.fifthBaseColorSource && zone.fifthBaseColorSource.startsWith('mono:') ? 'checked' : ''} onchange="_overlaySpecialPickerExpanded = { zoneIndex: ${i}, layer: 'fifth' }; setZoneFifthBaseColorSource(${i}, '${(zone.fifthBaseColorSource && zone.fifthBaseColorSource.startsWith('mono:') ? zone.fifthBaseColorSource : (typeof MONOLITHICS !== 'undefined' && MONOLITHICS[0] ? 'mono:' + MONOLITHICS[0].id : 'mono:chameleon_fire')).replace(/'/g, "\\'")}')"><span>From special</span></label>
                            ${zone.fifthBaseColorSource && zone.fifthBaseColorSource.startsWith('mono:') ? getOverlaySpecialPickerHtml(zone, i, 'fifth') : ''}
                        </div>
                        <div class="stack-control-group" style="margin-top:4px;">
                            <span class="stack-label-mini">Strength</span>
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                            <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBaseStrength || 0) * 100)}" oninput="setZoneFifthBaseStrength(${i}, this.value)" class="stack-slider" title="5th overlay strength, 5% steps">
                            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                            <span class="stack-val" id="detFifStrVal${i}">${Math.round((zone.fifthBaseStrength || 0) * 100)}%</span>
                        </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Spec Strength</span>
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseSpecStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBaseSpecStrength ?? 1) * 100)}"
                        oninput="setZoneFifthBaseSpecStrength(${i}, this.value)"
                        class="stack-slider" title="Physical finish intensity, 5% steps">
                    <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBaseSpecStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                    <span class="stack-val" id="detFifSpecStrVal${i}">${Math.round((zone.fifthBaseSpecStrength ?? 1) * 100)}%</span>
                </div>
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
                            <div class="stack-control-group"><span class="stack-label-mini">Strength</span>
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;">−</button>
                                <input type="range" min="0" max="100" step="5" value="${Math.round((zone.fifthBasePatternStrength ?? 1) * 100)}" oninput="setZoneFifthBasePatternStrength(${i}, this.value)" class="stack-slider">
                                <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneFifthBasePatternStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;">+</button>
                                <span class="stack-val" id="detFifPatStrVal${i}">${Math.round((zone.fifthBasePatternStrength ?? 1) * 100)}%</span></div>
                            <div class="zone-target-mode" style="margin: 6px 0; display: flex; gap: 6px; align-items: center;">
                                <label style="color: #aaa; font-size: 11px;">Overlay Placement:</label>
                                <select onchange="zones[${i}].fifthBaseFitZone = this.value === 'fit'; renderZones();"
                                        style="background: #1a1a1a; color: #ccc; border: 1px solid #333; padding: 2px 6px; font-size: 11px;">
                                    <option value="normal" ${!zone.fifthBaseFitZone ? 'selected' : ''}>Full Canvas</option>
                                    <option value="fit" ${zone.fifthBaseFitZone ? 'selected' : ''}>Fit to Zone</option>
                                </select>
                            </div>
                            <div class="stack-control-group"><span class="stack-label-mini">Position X</span>
                                <input type="range" min="0" max="100" step="1" value="${Math.round((zone.fifthBasePatternOffsetX ?? 0.5) * 100)}" oninput="setZoneFifthBasePatternOffsetX(${i}, this.value)" class="stack-slider" title="Pan overlay pattern left/right">
                                <span class="stack-val" id="detFifPatPosXVal${i}">${Math.round((zone.fifthBasePatternOffsetX ?? 0.5) * 100)}%</span></div>
                            <div class="stack-control-group"><span class="stack-label-mini">Position Y</span>
                                <input type="range" min="0" max="100" step="1" value="${Math.round((zone.fifthBasePatternOffsetY ?? 0.5) * 100)}" oninput="setZoneFifthBasePatternOffsetY(${i}, this.value)" class="stack-slider" title="Pan overlay pattern up/down">
                                <span class="stack-val" id="detFifPatPosYVal${i}">${Math.round((zone.fifthBasePatternOffsetY ?? 0.5) * 100)}%</span></div>
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
                oninput="setZoneIntensity(${i}, this.value, true); document.getElementById('detIntVal${i}').textContent=this.value+'%'"
                style="flex:1;"
                title="Zone intensity — controls the overall strength of all effects in this zone">
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

    html += `</div>`; // close zone-detail-body

    // Footer removed to keep panel persistent.

    // Preserve scroll when re-rendering (we saved scrollTop BEFORE innerHTML was cleared)
    const scrollRestore = _savedScrollTop > 0 ? _savedScrollTop : 0;

    panel.innerHTML = html;
    lastRenderedZoneDetailIndex = index;

    const newBody = panel.querySelector('.zone-detail-body');
    if (newBody) {
        if (scrollRestore > 0) {
            newBody.scrollTop = scrollRestore;
            requestAnimationFrame(() => { newBody.scrollTop = scrollRestore; });
        }
    }
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
    selectedZoneIndex = index;
    // If placement mode is on but this zone doesn't have that layer, clear it
    if (placementLayer !== 'none' && zones[index]) {
        const z = zones[index];
        const ok = (placementLayer === 'pattern' && z.pattern && z.pattern !== 'none') ||
            (placementLayer === 'second_base' && z.secondBase && z.secondBasePattern) ||
            (placementLayer === 'third_base' && z.thirdBase && z.thirdBasePattern) ||
            (placementLayer === 'fourth_base' && z.fourthBase && z.fourthBasePattern) ||
            (placementLayer === 'fifth_base' && z.fifthBase && z.fifthBasePattern) ||
            (placementLayer === 'base' && (z.base || z.finish));
        if (!ok) {
            placementLayer = 'none';
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();
        }
    }
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
}

function updateZoneName(index, name) {
    zones[index].name = name;
}

function deleteZone(index) {
    if (zones.length <= 1) { showToast('Need at least one zone', true); return; }
    const z = zones[index];
    const hasFinish = z.base || z.finish;
    const hasColor = z.color !== null || z.colorMode === 'multi';
    // Only confirm if zone has meaningful config (finish + color assigned)
    if (hasFinish && hasColor) {
        if (!confirm(`Delete "${z.name}"? This zone has a finish and color assigned.`)) return;
    }
    pushZoneUndo('Delete zone "' + z.name + '"');
    zones.splice(index, 1);
    if (selectedZoneIndex >= zones.length) selectedZoneIndex = zones.length - 1;
    renderZones();
    triggerPreviewRender();
    autoSave();
}

function moveZoneUp(index) {
    if (index <= 0) return;
    pushZoneUndo('Move zone up');
    [zones[index - 1], zones[index]] = [zones[index], zones[index - 1]];
    if (selectedZoneIndex === index) selectedZoneIndex = index - 1;
    else if (selectedZoneIndex === index - 1) selectedZoneIndex = index;
    renderZones();
}

function moveZoneDown(index) {
    if (index >= zones.length - 1) return;
    pushZoneUndo('Move zone down');
    [zones[index], zones[index + 1]] = [zones[index + 1], zones[index]];
    if (selectedZoneIndex === index) selectedZoneIndex = index + 1;
    else if (selectedZoneIndex === index + 1) selectedZoneIndex = index;
    renderZones();
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
        hint.textContent = 'No spec map yet. Enable SPLIT view, configure zones, and wait for the preview to render. Then open this again to see each channel and values.';
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

function captureBeforeImage() {
    // Capture the current paint canvas as the "before" image
    const paintCanvas = document.getElementById('paintCanvas');
    if (!paintCanvas || paintCanvas.width === 0) return;
    const beforeImg = document.getElementById('beforePreviewImg');
    if (!beforeImg) return;
    beforeImg.src = paintCanvas.toDataURL('image/png');
    beforeImageCaptured = true;
    // Show the B/A button
    const btn = document.getElementById('btnBeforeAfter');
    if (btn) btn.style.display = '';
}

function toggleBeforeAfter() {
    if (!beforeImageCaptured) {
        showToast('No paint loaded yet - load a paint file first');
        return;
    }
    beforeAfterActive = !beforeAfterActive;
    const beforePane = document.getElementById('previewBeforePane');
    const btn = document.getElementById('btnBeforeAfter');
    if (beforeAfterActive) {
        beforePane.style.display = '';
        if (btn) { btn.style.borderColor = 'var(--accent-gold)'; btn.style.background = 'rgba(255,170,0,0.15)'; }
    } else {
        beforePane.style.display = 'none';
        if (btn) { btn.style.borderColor = 'var(--accent-gold)'; btn.style.background = ''; }
    }
}

// Keyboard shortcut: hold B to show before, release to show after
document.addEventListener('keydown', (e) => {
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
            name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", finish: null, intensity: "80", colorMode: "quick", pickerColor: "#222222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Auto-catches dark/black areas - matte carbon fiber by default"
        },
        {
            name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", finish: null, intensity: "50", colorMode: "special", pickerColor: "#888888", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Safety net - catches any pixels not claimed by zones above"
        },
    ];
    zones = defaults;
    selectedZoneIndex = 0;
    renderZones();
    // Force the zone detail popout to open so it's visible after restore (fixes empty right area)
    if (typeof renderZoneDetail === 'function') renderZoneDetail(0);
    autoSave();
    showToast('All 10 default zones restored');
}

function addZone(skipUndo) {
    if (!skipUndo) pushZoneUndo('Add zone');
    zones.push({
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
        wear: 0,
        muted: false,
        patternOffsetX: 0.5,
        patternOffsetY: 0.5,
        patternPlacement: 'normal',  // 'normal' | 'fit' | 'manual'
        patternFlipH: false,
        patternFlipV: false,
        baseOffsetX: 0.5,
        baseOffsetY: 0.5,
        baseRotation: 0,
        baseFlipH: false,
        baseFlipV: false,
        baseColorMode: 'source',
        baseColor: '#ffffff',
        baseColorSource: null,
        baseColorStrength: 1,
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
        baseStrength: 1,
        baseSpecBlendMode: 'normal',
        patternSpecMult: 1,
    });
    selectedZoneIndex = zones.length - 1;
    renderZones();
    const listEl = document.getElementById('zoneList');
    if (listEl) listEl.scrollTop = listEl.scrollHeight;
}
if (typeof window !== 'undefined') { window.addZone = addZone; }

function duplicateZone(index) {
    pushZoneUndo('Duplicate zone');
    const src = zones[index];
    const clone = JSON.parse(JSON.stringify(src));
    clone.name = src.name + ' (copy)';
    clone.regionMask = src.regionMask ? [...src.regionMask] : null;
    zones.splice(index + 1, 0, clone);
    selectedZoneIndex = index + 1;
    renderZones();
    showToast(`Duplicated "${src.name}"`);
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
    showToast(`Applied finish to all ${zones.length} zones`);
}

// ===== COLOR SELECTORS =====
function setQuickColor(index, value) {
    pushZoneUndo('Set color');
    zones[index].color = value;
    zones[index].colorMode = 'quick';
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setSpecialColor(index, value) {
    pushZoneUndo();
    zones[index].color = value;
    zones[index].colorMode = 'special';
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setTextColor(index, value) {
    pushZoneUndo();
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
    const r = parseInt(hexValue.substr(1, 2), 16);
    const g = parseInt(hexValue.substr(3, 2), 16);
    const b = parseInt(hexValue.substr(5, 2), 16);
    zones[index].pickerColor = hexValue;
    zones[index].color = { color_rgb: [r, g, b], tolerance: zones[index].pickerTolerance || 40 };
    zones[index].colorMode = 'picker';
    zones[index].colors = []; // Clear multi-color stack when setting single color via picker
    renderZones();
    triggerPreviewRender();
}

function setPickerTolerance(index, value) {
    zones[index].pickerTolerance = parseInt(value);
    if (zones[index].colorMode === 'picker' && typeof zones[index].color === 'object' && zones[index].color !== null) {
        zones[index].color.tolerance = parseInt(value);
    }
    renderZones();
    triggerPreviewRender();
}

// ===== HEX CODE COLOR =====
function setHexColor(index, hex) {
    hex = hex.trim();
    if (!hex) {
        // Only clear if NOT in multi-color mode (don't wipe the stack)
        if (zones[index].colorMode !== 'multi') {
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
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    const tol = zones[index].pickerTolerance || 40;
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

// Resolve overlay base id (base id or "mono:xyz" for specials) to display { name, swatch }.
function getOverlayBaseDisplay(id) {
    if (!id) return null;
    if (typeof id === 'string' && id.startsWith('mono:')) {
        const m = typeof MONOLITHICS !== 'undefined' && MONOLITHICS.find(m => m.id === id.slice(5));
        return m ? { name: m.name, swatch: m.swatch || '#888' } : { name: id, swatch: '#888' };
    }
    const b = typeof BASES !== 'undefined' && BASES.find(b => b.id === id);
    return b ? { name: b.name, swatch: b.swatch || '#888' } : { name: id, swatch: '#888' };
}

// Determine finish type for a given ID (needed to pick the right /api/swatch path).
// Use server-authoritative FINISH_TYPE_BY_ID when available so thumbnails always use correct path.
function getFinishType(id) {
    if (!id || id === 'none') return null;
    if (typeof id === 'string' && id.startsWith('mono:')) return 'monolithic';
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
    return `${base}/api/swatch/${type}/${effectiveId}?color=${col}&size=${sz}${splitMode}&v=${v}`;
}

/** Build HTML for the "From special" overlay color picker: summary (name + tiny swatch) when collapsed, or big grid when expanded. */
function getOverlaySpecialPickerHtml(zone, i, layer) {
    const key = { second: 'secondBaseColorSource', third: 'thirdBaseColorSource', fourth: 'fourthBaseColorSource', fifth: 'fifthBaseColorSource' }[layer];
    const current = zone[key];
    const isMono = current && current.startsWith('mono:');
    const monolithics = (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : []);
    const selectedMono = isMono ? monolithics.find(m => 'mono:' + m.id === current) : null;
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    const v = (typeof window !== 'undefined' && window._SHOKKER_SWATCH_V) ? window._SHOKKER_SWATCH_V : Date.now();
    const swatchUrl = (id, sz) => id ? `${base}/api/swatch/monolithic/${id}?color=888888&size=${sz || 48}&v=${v}` : null;
    const popupType = { second: 'secondBaseColorSource', third: 'thirdBaseColorSource', fourth: 'fourthBaseColorSource', fifth: 'fifthBaseColorSource' }[layer];
    let html = '';
    if (selectedMono) {
        const smallUrl = swatchUrl(selectedMono.id, 32);
        html += `<div class="stack-control-group" style="flex-basis:100%;margin-top:2px;align-items:center;gap:6px;">
            <div style="display:flex;align-items:center;gap:6px;min-width:0;" title="From special — ${escapeHtml(selectedMono.name || selectedMono.id)}">
                ${smallUrl ? `<img src="${smallUrl}" alt="" style="width:24px;height:24px;border-radius:3px;border:1px solid var(--border);object-fit:cover;flex-shrink:0;" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling && (this.nextElementSibling.style.display='block');">` : ''}<span style="width:24px;height:24px;border-radius:3px;background:#${(selectedMono.swatch || '888').replace('#','')};flex-shrink:0;${smallUrl ? 'display:none;' : ''}" class="ov-fb"></span>
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
        return `<img class="swatch-square${isSplit ? ' swatch-split' : ''}" src="${url}" title="${title || ''}"
                    loading="lazy"
                    style="width:${w}px;height:${h}px;border-radius:4px;border:1px solid rgba(255,255,255,0.12);object-fit:${isSplit ? 'contain' : 'cover'};"
                    onerror="this.outerHTML='<div class=&quot;swatch-square&quot; title=&quot;${titleSafe}&quot; style=&quot;width:36px;height:36px;background:${fallback};&quot;></div>'">`;
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
        return `<img class="swatch-dot" src="${url}" loading="lazy"
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

/** Build options for overlay "React to" dropdown: Pattern 1 (primary), Pattern 2, Pattern 3 from zone. Value '' = zone primary. */
function getZonePatternReactOptions(zone) {
    const opts = [];
    const primaryId = zone.pattern && zone.pattern !== 'none' ? zone.pattern : null;
    opts.push({ value: '', label: `Pattern 1 (${primaryId ? getPatternName(primaryId) : 'Primary - None'})` });
    const stack = zone.patternStack || [];
    if (stack[0] && stack[0].id && stack[0].id !== 'none') {
        opts.push({ value: stack[0].id, label: `Pattern 2 (${getPatternName(stack[0].id)})` });
    }
    if (stack[1] && stack[1].id && stack[1].id !== 'none') {
        opts.push({ value: stack[1].id, label: `Pattern 3 (${getPatternName(stack[1].id)})` });
    }
    return opts;
}

/** Current value for overlay "React to" select: '' = Pattern 1 (primary), else the stored pattern ID. */
function getOverlayReactToSelectValue(zone, overlayPatternId) {
    if (!overlayPatternId || overlayPatternId === 'none') return '';
    const stack = zone.patternStack || [];
    if (stack[0] && overlayPatternId === stack[0].id) return overlayPatternId;
    if (stack[1] && overlayPatternId === stack[1].id) return overlayPatternId;
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
    // Force fresh swatch URLs so browser doesn't show cached thumbnails (e.g. after server fix)
    if (typeof window !== 'undefined') window._SHOKKER_SWATCH_V = Date.now();

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
    }

    // Build grid HTML with canvas-rendered previews
    const _nameSort = (a, b) => (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' });
    let html = '';
    const isOverlaySpecialSourcePicker = (type === 'secondBaseColorSource' || type === 'thirdBaseColorSource' || type === 'fourthBaseColorSource' || type === 'fifthBaseColorSource');
    if (type === 'base' || type === 'secondBase' || type === 'thirdBase' || type === 'fourthBase' || type === 'fifthBase' || type === 'baseColorSource' || isOverlaySpecialSourcePicker) {
        // Bases section - grouped by BASE_GROUPS with collapsible sections
        if (!isOverlaySpecialSourcePicker) {
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
            // Ungrouped bases (safety net)
            const ungroupedBases = BASES.filter(b => !baseGroupedIds.has(b.id));
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
        if (type === 'base' || type === 'secondBase' || type === 'thirdBase' || type === 'fourthBase' || type === 'fifthBase' || type === 'baseColorSource' || isOverlaySpecialSourcePicker) {
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
                    const groupMonos = ids.map(id => MONOLITHICS.find(m => m.id === id)).filter(Boolean);
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
            // Ungrouped monolithics (safety net)
            const ungrouped = MONOLITHICS.filter(m => !groupedIds.has(m.id));
            if (ungrouped.length > 0) {
                html += '<div class="swatch-group"><div class="swatch-group-label">Other</div><div class="swatch-grid-row">';
                ungrouped.forEach(m => {
                    html += `<div class="swatch-item${currentId === 'mono:' + m.id ? ' selected' : ''}" data-name="${m.name.toLowerCase()}" data-finish-id="${m.id}" data-finish-type="monolithic" data-desc="${(m.desc || m.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('mono:${m.id}')">
                    ${renderSwatchSquare(m.id, m.swatch, m.desc)}
                    <div class="swatch-label">${m.name}</div></div>`;
                });
                html += '</div></div>';
            }
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
        const m = typeof MONOLITHICS !== 'undefined' && MONOLITHICS.find(x => x.id === finishId);
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
}

function selectSwatchItem(id) {
    const { type, zoneIndex, layerIndex } = swatchPopupState;
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
document.addEventListener('keydown', function (e) {
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
    pushZoneUndo();
    const groupId = 'link_' + (nextLinkGroupId++);
    indices.forEach(i => { if (zones[i]) zones[i].linkGroup = groupId; });
    renderZones();
    showToast(`Linked ${indices.length} zones (Group ${groupId.replace('link_', '')})`);
}

function unlinkZone(index) {
    if (!zones[index] || !zones[index].linkGroup) return;
    pushZoneUndo();
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
    pushZoneUndo();
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
    'baseColorMode', 'baseColor', 'baseColorSource', 'baseColorStrength'];

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
    pushZoneUndo();
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
    pushZoneUndo('Set base: ' + (value || 'none'));
    if (value && value.startsWith('mono:')) {
        // Monolithic finish selected - keep existing patterns & overlays
        const monoId = value.replace('mono:', '');
        zones[index].finish = monoId;
        zones[index].base = null;
        // Don't clear pattern/patternStack - user may want patterns on top of specials
        if (!zones[index].pattern) zones[index].pattern = 'none';
    } else {
        zones[index].base = value || null;
        zones[index].finish = null; // Clear monolithic
        if (!zones[index].pattern) zones[index].pattern = 'none';
    }
    propagateToLinkedZones(index, LINK_FINISH_PROPS);
    renderZones();
    triggerPreviewRender();
}
function setZoneBaseColorMode(index, value) {
    pushZoneUndo('Set base color mode', true);
    const mode = (value === 'solid' || value === 'special') ? value : 'source';
    zones[index].baseColorMode = mode;
    if (!zones[index].baseColor) zones[index].baseColor = '#ffffff';
    if (zones[index].baseColorStrength == null) zones[index].baseColorStrength = 1;
    if (mode !== 'special') zones[index].baseColorSource = null;
    renderZoneDetail(index);
    triggerPreviewRender();
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
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBaseColorSource(index, val) {
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
function applyPlacementPatternTransform() {
    const img = document.getElementById('placementPatternImg');
    const z = zones[selectedZoneIndex];
    if (!img || !z || placementLayer !== 'pattern') return;
    const ox = (0.5 - (z.patternOffsetX ?? 0.5)) * 100;
    const oy = (0.5 - (z.patternOffsetY ?? 0.5)) * 100;
    const rot = z.rotation ?? 0;
    const sc = z.scale ?? 1;
    const flipX = z.patternFlipH ? -1 : 1;
    const flipY = z.patternFlipV ? -1 : 1;
    img.style.transform = `translate(${ox}%, ${oy}%) rotate(${rot}deg) scale(${sc}) scaleX(${flipX}) scaleY(${flipY})`;
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
            hint.querySelector('span:first-child').textContent = 'Loading pattern…';
            patternLayerDiv.style.display = 'block';
            const url = ShokkerAPI.baseUrl + '/api/pattern-layer?pattern=' + encodeURIComponent(pat) + '&w=' + canvas.width + '&h=' + canvas.height + '&scale=1&rotation=0&seed=42';
            patternImg.onload = function () {
                hint.style.display = 'none';
                applyPlacementPatternTransform();
                setupPlacementOverlayDrag();
            };
            patternImg.onerror = function () {
                hint.querySelector('span:first-child').textContent = '👆 Drag on map to move pattern';
                patternLayerDiv.style.display = 'none';
            };
            patternImg.src = url;
        } else {
            if (hint) {
                hint.style.display = 'flex';
                const msg = hint.querySelector('span:first-child');
                if (msg) msg.textContent = '👆 Load paint first, then drag on map to move pattern';
            }
            if (patternLayerDiv) patternLayerDiv.style.display = 'none';
        }
    } else {
        if (hint) {
            hint.style.display = 'flex';
            const msg = hint.querySelector('span:first-child');
            if (msg) msg.textContent = '👆 Drag on map to move ' + (placementLayer === 'second_base' ? '2nd overlay' : placementLayer === 'third_base' ? '3rd overlay' : placementLayer === 'fourth_base' ? '4th overlay' : placementLayer === 'fifth_base' ? '5th overlay' : placementLayer === 'base' ? 'base (gradient/duo)' : 'overlay');
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
    pushZoneUndo('Set scale', true);
    let v = parseFloat(val) || 1.0;
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
    pushZoneUndo();
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

function resetZoneBaseRotation(index) {
    pushZoneUndo('Reset base rotation');
    zones[index].baseRotation = 0;
    renderZones();
    triggerPreviewRender();
}

// ===== DUAL LAYER BASE OVERLAY SETTERS =====
function setZoneSecondBase(index, val) {
    pushZoneUndo('Set overlay base');
    zones[index].secondBase = val || '';
    if (!val) { zones[index].secondBaseStrength = 0; zones[index].secondBaseColorSource = null; }
    else {
        if (typeof val === 'string' && val.startsWith('mono:')) { zones[index].secondBaseColorSource = val; }
        // If user had "Same as overlay", keep it and update the color to the new base's swatch
        if (zones[index].secondBaseColorSource === 'overlay' && val) {
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].secondBaseColor = hex;
        }
        // Default to 100% strength when first adding an overlay so it's visible immediately
        if (!zones[index].secondBaseStrength) zones[index].secondBaseStrength = 1.0;
        // Default blend mode to pattern-pop with harden when first set
        if (!zones[index].secondBaseBlendMode) zones[index].secondBaseBlendMode = 'pattern-vivid';
        if (zones[index].secondBaseHarden === undefined) zones[index].secondBaseHarden = true;
        // Default color source to "Same As Overlay"
        if (!zones[index].secondBaseColorSource) {
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
    zones[index].secondBaseColorSource = val || null;
    renderZoneDetail(index);
    triggerPreviewRender();
}
/** Set overlay color to "Same as overlay" and sync secondBaseColor to the overlay base's swatch. */
function setZoneSecondBaseColorSourceToOverlay(index) {
    pushZoneUndo('Overlay color same as base', true);
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
    pushZoneUndo();
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
    zones[index].thirdBase = val || '';
    if (!val) { zones[index].thirdBaseStrength = 0; zones[index].thirdBaseColorSource = null; }
    else {
        if (typeof val === 'string' && val.startsWith('mono:')) { zones[index].thirdBaseColorSource = val; }
        if (zones[index].thirdBaseColorSource === 'overlay' && val) {
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].thirdBaseColor = hex;
        }
        if (!zones[index].thirdBaseStrength) zones[index].thirdBaseStrength = 1.0;
        // Default blend mode and color source for 3rd overlay
        if (!zones[index].thirdBaseBlendMode) zones[index].thirdBaseBlendMode = 'pattern-vivid';
        if (zones[index].thirdBaseHarden === undefined) zones[index].thirdBaseHarden = true;
        if (!zones[index].thirdBaseColorSource) {
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
    zones[index].thirdBaseColorSource = val || null;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneThirdBaseColor(index, val) {
    pushZoneUndo('Set 3rd overlay color', true);
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
    pushZoneUndo();
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
        const stack = z.patternStack || [];
        const pat = stack.find(p => p.id === targetPatId) || stack[0];
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.patternOffsetX ?? 0.5;
            py = pat.patternOffsetY ?? 0.5;
        } else {
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
    zones[index].fourthBase = val || ''; 
    if (!val) { zones[index].fourthBaseStrength = 0; zones[index].fourthBaseColorSource = null; } 
    else { 
        if (typeof val === 'string' && val.startsWith('mono:')) { zones[index].fourthBaseColorSource = val; } 
        if (!zones[index].fourthBaseStrength) zones[index].fourthBaseStrength = 1.0; 
        if (!zones[index].fourthBasePattern && val) zones[index].fourthBasePattern = allocateUnusedPatternForOverlay(zones[index]);
    } 
    renderZoneDetail(index); 
    triggerPreviewRender(); 
}
function setZoneFourthBaseColorSource(index, val) { pushZoneUndo('4th overlay color from special', true); zones[index].fourthBaseColorSource = val || null; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFourthBaseColor(index, val) {
    pushZoneUndo('Set 4th overlay color', true);
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
    pushZoneUndo();
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
        const stack = z.patternStack || [];
        const pat = stack.find(p => p.id === targetPatId) || stack[0];
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.patternOffsetX ?? 0.5;
            py = pat.patternOffsetY ?? 0.5;
        } else {
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
    zones[index].fifthBase = val || ''; 
    if (!val) { zones[index].fifthBaseStrength = 0; zones[index].fifthBaseColorSource = null; } 
    else {
        if (typeof val === 'string' && val.startsWith('mono:')) { zones[index].fifthBaseColorSource = val; } 
        if (zones[index].fifthBaseColorSource === 'overlay' && val) {
            const display = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(val);
            const hex = (display && display.swatch) ? (display.swatch.startsWith('#') ? display.swatch : '#' + display.swatch) : '#c9a227';
            zones[index].fifthBaseColor = hex;
        }
        if (!zones[index].fifthBaseStrength) zones[index].fifthBaseStrength = 1.0;
        if (!zones[index].fifthBasePattern && val) zones[index].fifthBasePattern = allocateUnusedPatternForOverlay(zones[index]);
    }
    renderZoneDetail(index); 
    triggerPreviewRender(); 
}
function setZoneFifthBaseColorSource(index, val) { pushZoneUndo('5th overlay color from special', true); zones[index].fifthBaseColorSource = val || null; renderZoneDetail(index); triggerPreviewRender(); }
function setZoneFifthBaseColor(index, val) {
    pushZoneUndo('Set 5th overlay color', true);
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
    pushZoneUndo();
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
        const stack = z.patternStack || [];
        const pat = stack.find(p => p.id === targetPatId) || stack[0];
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.patternOffsetX ?? 0.5;
            py = pat.patternOffsetY ?? 0.5;
        } else {
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
        const stack = z.patternStack || [];
        const pat = stack.find(p => p.id === targetPatId) || stack[0];
        if (pat) {
            sx = pat.scale ?? 1.0;
            rot = pat.rotation ?? 0;
            px = pat.patternOffsetX ?? 0.5;
            py = pat.patternOffsetY ?? 0.5;
        } else {
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
    pushZoneUndo();
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
    importedSpecMapPath = null;
    const status = document.getElementById('importSpecMapStatus');
    if (status) status.textContent = 'No spec map — zones render on default base';
    document.getElementById('btnClearSpecMap').disabled = true;
    showToast('Spec cleared — zones render on default base');
    triggerPreviewRender();
}

// ===== PATTERN STACK CONTROLS =====
function addPatternLayer(zoneIdx) {
    pushZoneUndo();
    if (!zones[zoneIdx].patternStack) zones[zoneIdx].patternStack = [];
    if (zones[zoneIdx].patternStack.length >= MAX_PATTERN_STACK_LAYERS) { showToast(`Max ${MAX_PATTERN_LAYERS_PER_ZONE} patterns (Pattern 1 + ${MAX_PATTERN_STACK_LAYERS} layers)`, true); return; }
    zones[zoneIdx].patternStack.push({ id: 'none', opacity: 100, scale: 1.0, rotation: 0, blendMode: 'normal' });
    renderZones();
    triggerPreviewRender();
}

function removePatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo();
    zones[zoneIdx].patternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}

function setPatternLayerId(zoneIdx, layerIdx, val) {
    pushZoneUndo();
    zones[zoneIdx].patternStack[layerIdx].id = val;
    renderZones();
    triggerPreviewRender();
}

function setPatternLayerOpacity(zoneIdx, layerIdx, val) {
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
    zones[zoneIdx].patternStack[layerIdx].blendMode = val;
    triggerPreviewRender();
}

function setZoneWear(index, val) {
    pushZoneUndo();
    zones[index].wear = parseInt(val) || 0;
    const label = document.getElementById('detWearVal' + index) || document.getElementById('wearVal' + index);
    if (label) label.textContent = zones[index].wear + '%';
    triggerPreviewRender();
}

// ===== SPEC PATTERN STACK CONTROLS =====
function addSpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add spec pattern');
    if (!zones[zoneIdx].specPatternStack) zones[zoneIdx].specPatternStack = [];
    if (zones[zoneIdx].specPatternStack.length >= 5) { showToast('Maximum 5 spec pattern layers', true); return; }
    const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === patternId);
    zones[zoneIdx].specPatternStack.push({
        pattern: patternId,
        opacity: 50,
        blendMode: 'normal',
        channels: 'MR',
        range: 40,
        params: spDef ? JSON.parse(JSON.stringify(spDef.defaults || {})) : {}
    });
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

function toggleSpecPatternChannel(zoneIdx, layerIdx, ch, checked) {
    pushZoneUndo('', true);
    if (!zones[zoneIdx].specPatternStack || !zones[zoneIdx].specPatternStack[layerIdx]) return;
    const sp = zones[zoneIdx].specPatternStack[layerIdx];
    let channels = sp.channels || 'MR';
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    if (!channels) channels = 'MR'; // At least one must be selected
    sp.channels = channels;
    renderZoneDetail(selectedZoneIndex);
    triggerPreviewRender();
}

// ===== OVERLAY SPEC PATTERN STACK CONTROLS =====
function addOverlaySpecPatternLayer(zoneIdx, patternId) {
    if (!patternId) return;
    pushZoneUndo('Add overlay spec pattern');
    if (!zones[zoneIdx].overlaySpecPatternStack) zones[zoneIdx].overlaySpecPatternStack = [];
    if (zones[zoneIdx].overlaySpecPatternStack.length >= 3) { showToast('Maximum 3 overlay spec pattern layers', true); return; }
    const spDef = (typeof SPEC_PATTERNS !== 'undefined' ? SPEC_PATTERNS : []).find(p => p.id === patternId);
    zones[zoneIdx].overlaySpecPatternStack.push({
        pattern: patternId,
        opacity: 50,
        blendMode: 'normal',
        channels: 'MR',
        range: 40,
        params: spDef ? { ...spDef.defaults } : {}
    });
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
    let channels = sp.channels || 'MR';
    if (checked && !channels.includes(ch)) {
        channels += ch;
    } else if (!checked) {
        channels = channels.replace(ch, '');
    }
    sp.channels = channels || 'M';
    triggerPreviewRender();
}

function setZoneFinish(index, finishId) {
    // Legacy compat
    zones[index].finish = finishId || null;
    zones[index].base = null;
    zones[index].pattern = null;
}

function setZoneIntensity(index, intensity, fromSlider) {
    if (intensity === 'custom') {
        // Switching to custom - keep current slider values or init from current preset
        pushZoneUndo();
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
        pushZoneUndo();
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
    const numVal = Math.max(0, Math.min(100, parseInt(value) || 100));
    zones[index].patternIntensity = String(numVal);
    propagateToLinkedZones(index, ['patternIntensity']);
    pushZoneUndo();
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

function assignFinishToSelected(finishId) {
    if (selectedZoneIndex >= 0 && selectedZoneIndex < zones.length) {
        pushZoneUndo('Assign finish: ' + finishId);
        const zone = zones[selectedZoneIndex];
        console.log(`[assignFinish] Zone ${selectedZoneIndex} (${zone.name}): assigning ${finishId}, was base=${zone.base} finish=${zone.finish}`);
        // Check if it's a base, pattern, or monolithic
        const base = BASES.find(b => b.id === finishId);
        const pattern = PATTERNS.find(p => p.id === finishId);
        const mono = MONOLITHICS.find(m => m.id === finishId);

        if (base) {
            zone.base = finishId;
            zone.finish = null;
            if (!zone.pattern) zone.pattern = 'none';
            console.log(`[assignFinish] Set base=${zone.base}, finish=${zone.finish}`);
            renderZones();
            triggerPreviewRender();
            showToast(`Base: ${base.name} => ${zone.name}`);
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
            zone.finish = finishId;
            zone.base = null;
            // Keep existing pattern if one is set (pattern can overlay on monolithic)
            // zone.pattern is preserved - user can keep or remove it
            console.log(`[assignFinish] Set mono finish=${zone.finish}, base=${zone.base}`);
            renderZones();
            triggerPreviewRender();
            const patLabel = (zone.pattern && zone.pattern !== 'none') ? ` (keeping ${PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern} overlay)` : '';
            showToast(`Special: ${mono.name}${patLabel} => ${zone.name}`);
        } else {
            // Legacy fallback
            zone.finish = finishId;
            zone.base = null;
            zone.pattern = null;
            console.log(`[assignFinish] Legacy fallback: finish=${zone.finish}`);
            renderZones();
            triggerPreviewRender();
            showToast(`Assigned ${finishId} to ${zone.name}`);
        }
        console.log(`[assignFinish] AFTER: zone ${selectedZoneIndex} base=${zones[selectedZoneIndex].base} finish=${zones[selectedZoneIndex].finish}`);
    }
}


// ===== FINISH FAVORITES (localStorage) =====
let _favoriteFinishes = new Set(JSON.parse(localStorage.getItem('shokker_favorites') || '[]'));
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

function _renderFinishItem(item, type) {
    const isFav = isFavorite(item.id);
    const starIcon = isFav ? '★' : '☆';
    const starColor = isFav ? 'color:#ffaa00;' : 'color:var(--text-dim);';
    const swatchUrl = getSwatchUrl(item.id, '888888');
    const swatchHtml = swatchUrl
        ? `<img class="finish-swatch-canvas" src="${swatchUrl}" loading="lazy"
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
                <div class="finish-item-name">${item.name}</div>
                <div class="finish-item-desc">${item.desc}</div>
            </div>
            <span onclick="toggleFavorite('${item.id}', event)" title="${isFav ? 'Remove from favorites' : 'Add to favorites'}" style="cursor:pointer; font-size:14px; ${starColor} padding:0 4px; flex-shrink:0; transition:color 0.15s;">${starIcon}</span>
            <span class="finish-item-assign">${type === 'base' ? 'Set Base' : type === 'pattern' ? 'Set Pattern' : 'Assign'}</span>
        </div>`;
}

function renderFinishLibrary() {
    const container = document.getElementById('finishLibrary');
    const GROUP_MAPS = { bases: BASE_GROUPS, patterns: PATTERN_GROUPS, specials: SPECIAL_GROUPS };
    const tabs = [
        { id: 'bases', label: `Bases (${BASES.length})`, items: BASES, type: 'base' },
        { id: 'patterns', label: `Patterns (${PATTERNS.length})`, items: PATTERNS, type: 'pattern' },
        { id: 'specials', label: `Specials (${MONOLITHICS.length})`, items: MONOLITHICS, type: 'mono' },
    ];

    // Main category tabs
    let html = `<div style="display:flex; gap:2px; margin-bottom:4px;">
        ${tabs.map(t => `<button class="btn btn-sm${activeLibraryTab === t.id ? ' active' : ''}"
            onclick="activeLibraryTab='${t.id}'; renderFinishLibrary();"
            style="flex:1; font-size:10px; padding:4px 2px; ${activeLibraryTab === t.id ? 'background:var(--accent); color:#000; border-color:var(--accent);' : ''}"
        >${t.label}</button>`).join('')}
    </div>`;

    // Combo count
    html += `<div style="text-align:center; font-size:9px; color:var(--text-dim); margin-bottom:3px;">
        ${BASES.length} bases x ${PATTERNS.length} patterns + ${MONOLITHICS.length} specials = <strong style="color:var(--accent);">${(BASES.length * PATTERNS.length + MONOLITHICS.length).toLocaleString()} finishes</strong>
    </div>`;

    const activeTab = tabs.find(t => t.id === activeLibraryTab);
    if (!activeTab) { container.innerHTML = html; return; }

    // Group accordion
    const groupMap = GROUP_MAPS[activeLibraryTab] || {};
    let groupNames = Object.keys(groupMap);
    // Deterministic group order:
    // - Bases: Foundation first, then alphabetical
    // - Patterns: Abstract & Experimental first, then alphabetical
    // - Specials: keep configured order from object / sections
    if (activeLibraryTab === 'bases') {
        groupNames = groupNames.sort((a, b) => a === 'Foundation' ? -1 : b === 'Foundation' ? 1 : a.localeCompare(b));
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
            if (activeLibraryTab === 'bases' || activeLibraryTab === 'patterns') {
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
        if (ungrouped.length > 0 && activeLibraryTab !== 'patterns') {
            const uIsOpen = _expandedGroups.has('__ungrouped__');
            const uChevron = uIsOpen ? '▾' : '▸';
            html += `<div class="finish-group-accordion" style="margin-bottom:2px; margin-top:4px;">
                <div onclick="toggleLibraryGroup('__ungrouped__')"
                     style="display:flex; align-items:center; gap:6px; padding:5px 8px; cursor:pointer; border-radius:4px; border-left:3px solid var(--border); transition:background 0.15s;"
                     onmouseenter="this.style.background='var(--surface-hover)'" onmouseleave="this.style.background=''">
                    <span style="font-size:11px; color:var(--text-dim); width:12px;">${uChevron}</span>
                    <span style="font-size:10px; font-weight:600; color:var(--text-dim); flex:1;">Other</span>
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
    items.forEach(item => {
        const name = item.getAttribute('data-name') || '';
        const desc = item.getAttribute('data-desc') || '';
        const matches = !q || name.includes(q) || desc.includes(q);
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
function applyPreset(presetId) {
    if (!presetId || !PRESETS[presetId]) return;
    const preset = PRESETS[presetId];
    zones = preset.zones.map(z => ({
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
    selectedZoneIndex = 0;
    renderZones();
    showToast(`Loaded preset: ${preset.name} -- set colors using the eyedropper!`);
}

// ===== TOAST =====
function showToast(msg, isError) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    // Auto-detect styling from message content
    const isSuccess = msg.startsWith('✅') || msg.startsWith('🔥');
    const isErr = isError === true || msg.startsWith('❌');
    toast.className = 'toast show' + (isErr ? ' error' : isSuccess ? ' success' : '');
    // Show longer for save/success messages, shorter for quick info
    const duration = (isSuccess || isErr) ? 5000 : 2500;
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => toast.className = 'toast', duration);
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
    return {
        version: "3.0",
        driverName: document.getElementById('driverName')?.value || '',
        carName: document.getElementById('carName')?.value || '',
        iracingId: document.getElementById('iracingId')?.value || '',
        paintFile: document.getElementById('paintFile').value,
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
            baseScale: z.baseScale,
            baseColorMode: z.baseColorMode ?? 'source',
            baseColor: z.baseColor ?? '#ffffff',
            baseColorSource: z.baseColorSource ?? null,
            baseColorStrength: z.baseColorStrength ?? 1,
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
            ccQuality: z.ccQuality,
            blendBase: z.blendBase,
            blendDir: z.blendDir,
            blendAmount: z.blendAmount,
            usePaintReactive: z.usePaintReactive,
            paintReactiveColor: z.paintReactiveColor,
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
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
    if (cfg.paintFile !== undefined) document.getElementById('paintFile').value = cfg.paintFile;
    if (cfg.outputDir !== undefined) document.getElementById('outputDir').value = cfg.outputDir;
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
        zones = cfg.zones.map(z => ({
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
            spatialMask: null,
            lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
            scale: z.scale ?? 1.0,
            rotation: z.rotation ?? 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternOffsetX: z.patternOffsetX ?? 0.5,
            patternOffsetY: z.patternOffsetY ?? 0.5,
            patternStack: z.patternStack || [],
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
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
            ccQuality: z.ccQuality ?? 100,
            blendBase: z.blendBase ?? null,
            blendDir: z.blendDir ?? 'horizontal',
            blendAmount: z.blendAmount ?? 50,
            usePaintReactive: z.usePaintReactive ?? false,
            paintReactiveColor: z.paintReactiveColor ?? null,
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
        }));
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
            scale: z.scale || 1.0,
            rotation: z.rotation || 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternOffsetX: z.patternOffsetX ?? 0.5,
            patternOffsetY: z.patternOffsetY ?? 0.5,
            patternStack: z.patternStack || [],
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            wear: z.wear || 0,
            muted: z.muted || false,
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

function applyPreset(preset) {
    // Show preset info before applying
    const info = `"${preset.name}"${preset.author ? ' by ' + preset.author : ''}\n${preset.zones.length} zones | ${preset.finishCount || '?'} finishes\n\nApply this preset? (Your current zones will be replaced)`;
    if (!confirm(info)) return;

    // Apply zones
    zones = preset.zones.map(z => ({
        name: z.name || 'Zone',
        color: z.color,
        base: z.base || null,
        pattern: z.pattern || 'none',
        finish: z.finish || null,
        intensity: z.intensity || '100',
        customSpec: z.customSpec != null ? z.customSpec : null,
        customPaint: z.customPaint != null ? z.customPaint : null,
        customBright: z.customBright != null ? z.customBright : null,
        colorMode: z.colorMode || 'none',
        pickerColor: z.pickerColor || '#3366ff',
        pickerTolerance: z.pickerTolerance || 40,
        colors: z.colors || [],
        regionMask: null, // Regions are car-specific, not imported
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        scale: z.scale || 1.0,
        patternOpacity: z.patternOpacity ?? 100,
        patternOffsetX: z.patternOffsetX ?? 0.5,
        patternOffsetY: z.patternOffsetY ?? 0.5,
        patternStack: z.patternStack || [],
        specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
        wear: z.wear || 0,
        muted: z.muted || false,
    }));
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

function autoSave() {
    // Debounce: wait 500ms after last change before saving
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
        try {
            const cfg = getConfig();
            cfg._autosave_time = Date.now();
            localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(cfg));
            const badge = document.getElementById('autosaveBadge');
            if (badge) {
                badge.textContent = 'Auto-saved';
                badge.style.opacity = '1';
                setTimeout(() => { badge.style.opacity = '0.4'; }, 1500);
            }
        } catch (e) {
            // localStorage full or unavailable - silently ignore
        }
    }, 500);
}

function autoRestore() {
    try {
        const raw = localStorage.getItem(AUTOSAVE_KEY);
        if (!raw) return false;
        const cfg = JSON.parse(raw);
        if (!cfg || !cfg.zones || cfg.zones.length === 0) return false;
        loadConfigFromObj(cfg);
        const age = cfg._autosave_time ? Math.round((Date.now() - cfg._autosave_time) / 1000) : 0;
        let ageStr;
        if (age < 60) ageStr = `${age}s ago`;
        else if (age < 3600) ageStr = `${Math.round(age / 60)}m ago`;
        else ageStr = `${Math.round(age / 3600)}h ago`;
        showToast(`Session restored (saved ${ageStr}) - ${cfg.zones.length} zones, ${cfg.driverName || 'no driver'}`);
        // Validate restored paint path after a short delay (server needs to be up)
        setTimeout(() => { if (typeof validatePaintPath === 'function') validatePaintPath(); }, 800);
        return true;
    } catch (e) {
        return false;
    }
}

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
    document.getElementById('scriptModal').classList.add('active');
}

function closeModal() {
    document.getElementById('scriptModal').classList.remove('active');
}

function copyScript() {
    const text = document.getElementById('scriptOutput').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const fb = document.getElementById('copyFeedback');
        fb.classList.add('show');
        setTimeout(() => fb.classList.remove('show'), 2000);
    });
}

function saveScriptFile() {
    const text = document.getElementById('scriptOutput').textContent;
    if (!text) { showToast('No script generated yet!', true); return; }

    let filename = document.getElementById('scriptFilename').value.trim();
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

