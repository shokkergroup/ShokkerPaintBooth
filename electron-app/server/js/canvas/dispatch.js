/**
 * SPB Canvas Dispatch — Single Source of Truth for Tool Routing
 * 
 * This is the beginning of the architectural extraction from the 19k-line monster
 * (paint-booth-3-canvas.js).
 * 
 * Responsibilities:
 * - Owns toolbarEditMode ('zone' | 'layer')
 * - Owns the two guard maps (zoneOnlyToolNames / layerOnlyToolNames)
 * - Decides routing for every tool action
 * - Provides requireZoneToolbarMode / requireLayerToolbarTarget guards
 * 
 * Heenan Family Rule: This file is the ONLY place routing decisions should live.
 * 
 * @see docs/TOOL_ARCHITECTURE.html
 * @see docs/TOOL_ARCHITECTURE.md
 */

(function() {
    'use strict';

    // =====================================================
    // TOOLBAR EDIT MODE — THE ARCHITECTURAL BOUNDARY
    // =====================================================
    // 'zone'  = traditional zone mask painting (regionMask + spatialMask)
    // 'layer' = PSD layer painting (active layer pixels + transforms)
    window.toolbarEditMode = window.toolbarEditMode || 'zone';

    function getToolbarEditMode() {
        return window.toolbarEditMode === 'layer' ? 'layer' : 'zone';
    }
    window.getToolbarEditMode = getToolbarEditMode;

    function isLayerToolbarMode() {
        return getToolbarEditMode() === 'layer';
    }
    window.isLayerToolbarMode = isLayerToolbarMode;

    function isZoneToolbarMode() {
        return !isLayerToolbarMode();
    }
    window.isZoneToolbarMode = isZoneToolbarMode;

    // =====================================================
    // ZONE-ONLY vs LAYER-ONLY TOOL MAPS
    // These are the explicit contracts.
    // Every new tool MUST be registered here.
    // =====================================================
    const zoneOnlyToolNames = {
        'wand': 'Magic Wand',
        'selectall': 'Select All',
        'edge': 'Edge Detect',
        // SPB-93 2026-08-08 ownership audit, owner verdict: both Zone and
        // Layer workflows cannot be overlooked. Before: these advertised
        // Zone mutators were absent from dispatch and could stay armed in
        // Layer mode. After: activation routes to Zone before pointer input.
        'grab-object': 'Grab Object',
        'rect': 'Rectangle',
        'lasso': 'Lasso',
        'ellipse-marquee': 'Ellipse Marquee',
        'pen': 'Pen',
        'selection-move': 'Move Border',
        'zone-pick': 'Zone Pick',
        'spatial-include': 'Spatial Include',
        'spatial-exclude': 'Spatial Exclude',
        'spatial-erase': 'Spatial Erase',
        // Add new zone-only tools here
    };

    const layerOnlyToolNames = {
        'layer-move': 'Move Layer or Element',
        'layer-pick': 'Pick Layer Element',
        'text': 'Text',
        'shape': 'Shape',
        'clone': 'Clone Stamp',
        'heal': 'Healing Brush',
        'colorbrush': 'Color Brush',
        'recolor': 'Recolor',
        'smudge': 'Smudge',
        'history-brush': 'History Brush',
        'pencil': 'Pencil',
        'dodge': 'Dodge',
        'burn': 'Burn',
        'blur-brush': 'Blur Brush',
        'sharpen-brush': 'Sharpen Brush',
        // Add new layer-only tools here
    };

    // Layer creators respect the Layer/Zone boundary but do not need a
    // pre-existing selected Layer. Keep this subset beside the ownership maps
    // so dispatch guards and user-facing target labels share the same truth.
    const layerCreatorToolNames = {
        'text': 'Text',
        'shape': 'Shape',
    };

    // These tools intentionally work in either workflow, but Layer mode still
    // needs a real editable pixel target. Treat that as an activation contract
    // so a locked/missing Layer cannot produce an armed-looking no-op tool.
    const targetedDualToolNames = {
        'brush': 'Brush',
        'erase': 'Eraser',
        'fill': 'Fill',
        'gradient': 'Gradient',
    };

    window.zoneOnlyToolNames = zoneOnlyToolNames;
    window.layerOnlyToolNames = layerOnlyToolNames;
    window.layerCreatorToolNames = layerCreatorToolNames;
    window.targetedDualToolNames = targetedDualToolNames;

    // SPB-93 T62 (2026-08-09), owner verdict: tools must work like
    // Photoshop/GIMP while Pick Color and Spatial Exclude's pointer semantics
    // stay frozen.
    // Browser before: Wand Alt-click left the 526-pixel selection unchanged,
    // added 0 History, and sampled #EAFF00 because the global eyedropper won
    // before selection dispatch. Modifier ownership belongs beside tool
    // ownership so the controller can route Alt without changing any sampling
    // or selection kernel. Spatial Exclude intentionally remains on the legacy
    // temporary-eyedropper Alt result; its mask behavior is owner-frozen.
    const altSelectionToolNames = new Set([
        'wand', 'selectall', 'edge', 'grab-object', 'lasso',
    ]);
    const altSourceToolNames = new Set(['clone', 'heal']);
    const altGeometryToolNames = new Set([
        'shape', 'pen', 'ellipse-marquee', 'rect', 'selection-move',
        'zone-pick', 'layer-move',
    ]);

    function getAltPointerIntent(toolMode) {
        const mode = String(toolMode || '');
        if (altSelectionToolNames.has(mode)) return 'selection-subtract';
        if (altSourceToolNames.has(mode)) return 'source-sample';
        if (altGeometryToolNames.has(mode)) return 'tool-modifier';
        return 'temporary-eyedropper';
    }
    window.getAltPointerIntent = getAltPointerIntent;

    // =====================================================
    // GUARD FUNCTIONS
    // Called from mousedown / tool activation points.
    // =====================================================
    function requireZoneToolbarMode(toolName) {
        if (isLayerToolbarMode()) {
            if (typeof showToast === 'function') {
                showToast(`${toolName} only works in Zone mode. Switch to Zone toolbar.`, true);
            }
            // Future: could auto-switch or highlight the Zone button
            return false;
        }
        return true;
    }
    window.requireZoneToolbarMode = requireZoneToolbarMode;

    function requireLayerToolbarTarget(toolName) {
        if (!isLayerToolbarMode()) {
            if (typeof showToast === 'function') {
                showToast(`${toolName} requires Layer mode + an active PSD layer.`, true);
            }
            return false;
        }
        if (Object.values(layerCreatorToolNames).includes(toolName)) {
            return true;
        }
        
        // Additional check: is there actually an active editable layer?
        // SPB-93: match the canvas fallback guard. A selected layer id is not
        // enough; locked/unloaded layers must refuse layer-pixel tools.
        const layer = (typeof getSelectedEditableLayer === 'function') ? getSelectedEditableLayer() : null;
        if (!layer) {
            const reason = (typeof _diagnoseLayerPaintFail === 'function') ? _diagnoseLayerPaintFail() : null;
            if (typeof showToast === 'function') {
                showToast(reason || 'Import a PSD and select an editable layer first.', true);
            }
            return false;
        }
        return true;
    }
    window.requireLayerToolbarTarget = requireLayerToolbarTarget;

    // SPB-93 browser gauntlet (2026-08-08), owner verdict: tools must feel
    // Photoshop-like and WORK. Before: choosing Rectangle while a Layer was
    // active visibly armed the tool, but the first 93 ms drag did nothing and
    // only then told the painter to switch modes. After: the same Rectangle
    // activation routed first and committed 237,170 mask pixels in a 567 ms
    // drag. Route explicit tool choices to their owning toolbar immediately.
    // Layer-only tools without an editable target now refuse before arming
    // instead of failing on gesture. Owner 2026-09-03: Easy exposes Exclude as
    // a primary tool, so it must route to its Zone owner before it appears
    // armed. Its frozen Alt intent and red spatial-mask math remain untouched.
    function getToolbarToolActivation(toolMode) {
        const mode = String(toolMode || '');
        const currentMode = getToolbarEditMode();
        if (Object.prototype.hasOwnProperty.call(zoneOnlyToolNames, mode)) {
            return { allowed: true, mode: 'zone', toolName: zoneOnlyToolNames[mode] };
        }
        if (Object.prototype.hasOwnProperty.call(layerOnlyToolNames, mode)) {
            const createsLayer = Object.prototype.hasOwnProperty.call(layerCreatorToolNames, mode);
            const hasLayerTarget = typeof getSelectedEditableLayer === 'function' && !!getSelectedEditableLayer();
            if (createsLayer || hasLayerTarget) {
                return { allowed: true, mode: 'layer', toolName: layerOnlyToolNames[mode] };
            }
            return {
                allowed: false,
                mode: currentMode,
                toolName: layerOnlyToolNames[mode],
                reason: `${layerOnlyToolNames[mode]} needs an editable Layer. Select or create an unlocked Layer first.`,
            };
        }
        if (currentMode === 'layer' && Object.prototype.hasOwnProperty.call(targetedDualToolNames, mode)) {
            const hasLayerTarget = typeof getSelectedEditableLayer === 'function' && !!getSelectedEditableLayer();
            if (!hasLayerTarget) {
                return {
                    allowed: false,
                    mode: currentMode,
                    toolName: targetedDualToolNames[mode],
                    reason: `${targetedDualToolNames[mode]} needs an editable Layer. Select or create an unlocked Layer first.`,
                };
            }
        }
        return { allowed: true, mode: currentMode };
    }
    window.getToolbarToolActivation = getToolbarToolActivation;

    function alignToolbarModeForToolActivation(toolMode) {
        const activation = getToolbarToolActivation(toolMode);
        if (!activation.allowed) return getToolbarEditMode();
        if (activation.mode !== getToolbarEditMode()) {
            setToolbarEditMode(activation.mode, {
                preserveTool: true,
                allowWithoutTarget: Object.prototype.hasOwnProperty.call(layerCreatorToolNames, String(toolMode || '')),
            });
        }
        return getToolbarEditMode();
    }
    window.alignToolbarModeForToolActivation = alignToolbarModeForToolActivation;

    // =====================================================
    // MODE SWITCHING
    // =====================================================
    const _toolbarModeChangeListeners = [];
    window.onToolbarEditModeChange = function onToolbarEditModeChange(listener) {
        if (typeof listener === 'function') _toolbarModeChangeListeners.push(listener);
    };

    function setToolbarEditMode(mode, options = {}) {
        const nextMode = (mode === 'layer') ? 'layer' : 'zone';
        const opts = options || {};
        if (nextMode === 'layer' && !opts.allowWithoutTarget) {
            const hasLayerTarget = typeof getSelectedEditableLayer === 'function' && !!getSelectedEditableLayer();
            if (!hasLayerTarget) {
                if (!opts.silent && typeof showToast === 'function') {
                    showToast('Layer Mode needs an editable Layer. Select, unlock, or create one first.', true);
                }
                return getToolbarEditMode();
            }
        }
        const previousTool = String(window.canvasMode || '');
        const changed = window.toolbarEditMode !== nextMode;
        window.toolbarEditMode = nextMode;

        try {
            localStorage.setItem('spb_toolbar_edit_mode', nextMode);
        } catch (e) { /* quota / private mode */ }

        if (changed || opts.forceUiRefresh) {
            if (typeof _updateToolbarEditModeButtons === 'function') {
                _updateToolbarEditModeButtons();
            }
            if (typeof refreshToolbarModeSensitiveUi === 'function') {
                refreshToolbarModeSensitiveUi();
            }
        }

        for (let i = 0; i < _toolbarModeChangeListeners.length; i++) {
            try {
                _toolbarModeChangeListeners[i](nextMode, opts);
            } catch (err) {
                console.warn('[SPB Dispatch] toolbar mode listener failed', err);
            }
        }

        // A manual mode switch must never leave an impossible active-tool
        // badge such as "RECTANGLE · Layer Mode". Tool-triggered routing sets
        // preserveTool because the requested tool is armed immediately after
        // this call. Manual Layer uses Move; manual Zone uses the dual Brush.
        if (changed && !opts.preserveTool && typeof window.setCanvasMode === 'function') {
            if (nextMode === 'layer' && Object.prototype.hasOwnProperty.call(zoneOnlyToolNames, previousTool)) {
                window.setCanvasMode('layer-move');
            } else if (nextMode === 'zone' && Object.prototype.hasOwnProperty.call(layerOnlyToolNames, previousTool)) {
                window.setCanvasMode('brush');
            }
        }

        if (!opts.silent && typeof showToast === 'function') {
            const label = nextMode === 'layer' ? 'Layer Mode' : 'Zone Mode';
            showToast(`Switched to ${label}`, 'success');
        }

        return nextMode;
    }
    // Stable impl ref — canvas must not capture window.setToolbarEditMode (that alias gets replaced).
    window.__spbNativeDispatchSetMode = setToolbarEditMode;
    window.setToolbarEditMode = setToolbarEditMode;

    // =====================================================
    // INITIALIZATION
    // =====================================================
    function initDispatch() {
        // A persisted Layer preference is only valid when this document has
        // already restored an editable Layer. Flat-image startup must never
        // reopen into a dead Layer toolbar; layered import selects Layer after
        // publishing its target authority.
        const saved = localStorage.getItem('spb_toolbar_edit_mode');
        const canRestoreLayer = saved === 'layer'
            && typeof getSelectedEditableLayer === 'function'
            && !!getSelectedEditableLayer();
        window.toolbarEditMode = canRestoreLayer ? 'layer' : 'zone';
        
        // Make sure buttons reflect current state on load
        if (typeof _updateToolbarEditModeButtons === 'function') {
            setTimeout(_updateToolbarEditModeButtons, 50);
        }
        
        console.log('%c[SPB Dispatch] Tool routing system initialized. Mode:', 'color:#4ade80', window.toolbarEditMode);
    }

    // Auto-init when script loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDispatch);
    } else {
        initDispatch();
    }

    // Expose for debugging / future autonomous agents
    window._SPB_DISPATCH = {
        version: '1.0.0-foundation',
        getMode: getToolbarEditMode,
        setMode: setToolbarEditMode,
        isLayer: isLayerToolbarMode,
        isZone: isZoneToolbarMode,
        zoneOnlyTools: zoneOnlyToolNames,
        layerOnlyTools: layerOnlyToolNames,
        layerCreatorTools: layerCreatorToolNames,
        targetedDualTools: targetedDualToolNames,
        getAltPointerIntent
    };

})();
