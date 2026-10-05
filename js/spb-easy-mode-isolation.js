/* ============================================================================
   SPB EASY MODE STATE ISOLATION — Easy is ITS OWN THING (owner mandate 2026-08-26)
   ----------------------------------------------------------------------------
   Owner: "when going to Easy Mode it does NOT need to mess with cars being
   edited in Pro mode if people are wanting to switch back and forth."

   Before this module, Easy Mode spliced/pushed into the SAME `zones` array Pro
   uses — applying any Easy look destroyed the Pro project in place. Now each
   mode owns a full-fidelity zone slot and the boundary swaps them:

   · Pro → Easy: snapshot Pro zones (region/spatial masks + strength maps
     included) into the PRO slot; load the EASY slot (or the factory-default 5
     zones on Easy's first visit — a buyer starts from their clean car, not
     from the middle of a Pro project).
   · Easy → Pro: snapshot Easy zones into the EASY slot; restore the PRO slot
     byte-for-byte. Undo/redo stacks are cleared at every boundary — cross-mode
     undo popping the other mode's states was a corruption footgun.
   · App closed while IN Easy: beforeunload restores the Pro slot synchronously
     and flushes autosave, so the boot autosave-restore always brings back the
     PRO project (Easy keeps its own looks in its own spb_easy_* storage).

   Bare lexical access to `zones` / `_cloneZoneState` / `_ensureZoneShape` /
   `zoneUndoStack` / `zoneRedoStack` follows the established Easy Mode pattern
   (top-level lets/consts in classic scripts share one global lexical scope;
   they are NOT window properties).
   ============================================================================ */
(function (global) {
    'use strict';

    var slots = { pro: null, easy: null, proSelected: 0, easySelected: 0 };
    var _inEasy = false;

    function _snapshot() {
        try {
            return zones.map(function (z) {
                return _cloneZoneState(z, {
                    preserveId: true,
                    includeRegionMask: true,
                    includeSpatialMask: true,
                    includePatternStrengthMap: true,
                });
            });
        } catch (e) {
            try { console.warn('[easy-isolation] snapshot failed:', e); } catch (_) {}
            return null;
        }
    }

    function _clearUndoStacks() {
        try { zoneUndoStack.length = 0; } catch (e) {}
        try { zoneRedoStack.length = 0; } catch (e) {}
        try { if (typeof renderUndoHistoryPanel === 'function') renderUndoHistoryPanel(); } catch (e) {}
    }

    function _restore(snap, selectedIdx) {
        try {
            zones.length = 0;
            (snap || []).forEach(function (z) {
                zones.push(_ensureZoneShape(z, { includeRegionMask: true, includeSpatialMask: true }));
            });
            if (!zones.length && typeof global.spbCreateDefaultZones === 'function') {
                global.spbCreateDefaultZones().forEach(function (z) { zones.push(_ensureZoneShape(z, {})); });
            }
            try { selectedZoneIndex = Math.max(0, Math.min(Number(selectedIdx) || 0, zones.length - 1)); } catch (e) {}
            try { if (typeof ensureAllZonesHaveIds === 'function') ensureAllZonesHaveIds(zones); } catch (e) {}
            try { if (typeof renderZones === 'function') renderZones(); } catch (e) {}
            try { if (typeof renderZoneDetail === 'function' && zones.length) renderZoneDetail(Math.max(0, Math.min(selectedZoneIndex, zones.length - 1))); } catch (e) {}
            return true;
        } catch (e) {
            try { console.warn('[easy-isolation] restore failed:', e); } catch (_) {}
            return false;
        }
    }

    function _defaultEasyZones() {
        try {
            if (typeof global.spbCreateDefaultZones === 'function') return global.spbCreateDefaultZones();
        } catch (e) {}
        // minimal safe fallback: one catch-all zone (same shape as the factory 'Everything Else')
        return [{ name: 'Everything Else', color: 'remaining', base: 'gloss', pattern: 'none', finish: null,
                  intensity: '50', colorMode: 'special', pickerColor: '#888888', pickerTolerance: 40, colors: [], regionMask: null }];
    }

    function enterEasy() {
        if (_inEasy) return;
        slots.pro = _snapshot();
        try { slots.proSelected = selectedZoneIndex; } catch (e) { slots.proSelected = 0; }
        _clearUndoStacks();
        _restore(slots.easy || _defaultEasyZones(), slots.easySelected);
        _inEasy = true;
    }

    function exitEasy() {
        if (!_inEasy) return;
        slots.easy = _snapshot();
        try { slots.easySelected = selectedZoneIndex; } catch (e) { slots.easySelected = 0; }
        _clearUndoStacks();
        if (slots.pro) _restore(slots.pro, slots.proSelected);
        _inEasy = false;
        // Pro's live preview must show the PRO design again, not Easy's last render
        try { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); } catch (e) {}
    }

    // App closed while in Easy: put the PRO project back before autosave flushes,
    // so the next boot restores the Pro car (never Easy's scratch state).
    global.addEventListener('beforeunload', function () {
        if (!_inEasy || !slots.pro) return;
        try {
            _restore(slots.pro, slots.proSelected);
            _inEasy = false;
            if (typeof flushAutoSave === 'function') flushAutoSave();
            else if (typeof global.flushAutoSave === 'function') global.flushAutoSave();
        } catch (e) {}
    });

    global.spbEasyIsolation = {
        enterEasy: enterEasy,
        exitEasy: exitEasy,
        isInEasy: function () { return _inEasy; },
        _slots: slots,   // debug/QA visibility
    };
})(window);
