/* [SPB-FLATWIPE 2026-10-10 lane FLAT-WIPE] Flat source paint = a locked "Background" layer under added layers (Photoshop model).
 *
 * BUG (found by TOOLS-FIX-4, measured by this lane with probe_flat1.py on a 2048 flat PNG): a flat TGA/PNG/JPEG has no layer stack,
 * its pixels live only in paintImageData + the paint canvas. "+ Layer" (and every other path that pushes the first layer: text,
 * paste, Sponsor/Number Kit, PhotoCraft, adjustment layers, crash recovery...) set _psdLayersLoaded = true, and the next full
 * recompositeFromLayers() cleared the canvas and drew ONLY the layers. px(100,100): 35,63,118,255 after load -> 0,0,0,0 after the
 * first full recomposite, and still 0,0,0,0 after undoing the stroke AND the + Layer (the undo snapshot was an empty stack).
 * The render then sent that layers-only composite as the paint.
 *
 * FIX (this file + 5 one-line hooks in paint-booth-3-canvas.js):
 *  - flat state = no layer stack, no PSD, paintImageData the size of the canvas. A layer-stack snapshot taken in flat state is
 *    tagged and keeps a copy of the flat pixels, so Undo back to "before the first layer" restores the exact flat paint.
 *  - _pushLayerStackUndo() in flat state: AFTER the snapshot, the flat pixels become a locked "Background" layer at index 0
 *    (exact copy of paintImageData). The caller then adds its layer on top.
 *  - recompositeFromLayers() safety net: when the stack left flat state through a path that never pushed an undo first
 *    (live text/sponsor/number preview, colourway, old crash-recovery checkpoints), the Background is inserted before compositing.
 *  - a LOCKED Background stays at the bottom (nothing can hide under it, as in Photoshop). Smart Separate is unchanged (its layers
 *    already decompose the flat paint): no Background is added for it.
 * Kill switch: window.SPB_FLATWIPE_OFF = true (or localStorage SPB_FLATWIPE_OFF = '1') = the old behaviour byte for byte.
 */
(function () {
    'use strict';
    var BG_PREFIX = 'spb_flatbg_';
    var NO_PROMOTE = { 'Smart TGA auto-build layers': 1, 'restore interrupted layer session': 1 };
    var NO_PENDING = { 'Smart TGA auto-build layers': 1 };
    var st = { pending: false, promoted: 0, last: null };
    var lsOff = false;
    try { lsOff = localStorage.getItem('SPB_FLATWIPE_OFF') === '1'; } catch (_) { }

    function off() { return lsOff || window.SPB_FLATWIPE_OFF === true; }
    function layers() { try { return _psdLayers; } catch (_) { return null; } }            // eslint-disable-line no-undef
    function loaded() { try { return !!_psdLayersLoaded; } catch (_) { return false; } }   // eslint-disable-line no-undef
    function psdDoc() { try { return !!(_psdPath || _psdData); } catch (_) { return false; } }   // eslint-disable-line no-undef
    function pid() { try { return paintImageData; } catch (_) { return null; } }            // eslint-disable-line no-undef
    function canvas() { return document.getElementById('paintCanvas'); }
    function isBg(l) { return !!(l && (l.flatBackground === true || String(l.id || '').indexOf(BG_PREFIX) === 0)); }
    function pidFits() {
        var d = pid(), pc = canvas();
        return !!(d && d.data && pc && d.width === pc.width && d.height === pc.height && d.data.length === d.width * d.height * 4);
    }
    function flatState() {
        var L = layers();
        return !off() && Array.isArray(L) && L.length === 0 && !loaded() && !psdDoc() && pidFits();
    }
    function makeBg() {
        var d = pid(), c = document.createElement('canvas');
        c.width = d.width; c.height = d.height;
        // CPU-backed like the paint canvas: the stroke flush crops/draws this into willReadFrequently canvases (no GPU readback)
        c.getContext('2d', { willReadFrequently: true }).putImageData(d, 0, 0);
        st.promoted++;
        return {
            id: BG_PREFIX + Date.now().toString(36) + '_' + st.promoted, name: 'Background', path: '',
            visible: true, opacity: 255, blendMode: 'source-over', locked: true, alphaLock: false, clippingMask: false,
            effects: null, groupName: '', bbox: [0, 0, d.width, d.height], img: c, flatBackground: true
        };
    }
    function promote(where) {
        var L = layers(); if (!Array.isArray(L) || L.some(isBg) || !pidFits() || psdDoc()) return null;
        var bg = makeBg();
        L.unshift(bg);                   // in place: tools that hold the array (text, kits, colourway) keep a live reference
        try { _psdLayersLoaded = true; window._psdLayersLoaded = true; } catch (_) { }   // eslint-disable-line no-undef
        st.pending = false;
        st.last = { at: Date.now(), where: where, id: bg.id };
        try { if (typeof _gestureCompositeCache !== 'undefined') _gestureCompositeCache = null; } catch (_) { }   // eslint-disable-line no-undef
        return bg;
    }

    /** A restored Background with no pixels (crash recovery: "N layers had not been saved yet and will come back empty") on a
     *  freshly loaded flat source = the source itself. 16 sampled rows all transparent = empty (a real paint never is). */
    function refillIfEmpty(b) {
        var d = pid(); if (!b || !d || !pidFits()) return false;
        try {
            var img = b.img, w = d.width, h = d.height;
            if (img && img.width === w && img.height === h) {
                var cx = img.getContext && img.getContext('2d', { willReadFrequently: true });
                if (!cx) return false;
                for (var k = 0; k < 16; k++) {
                    var row = cx.getImageData(0, Math.floor((k + 0.5) * h / 16), w, 1).data;
                    for (var i = 3; i < row.length; i += 4) if (row[i]) return false;
                }
            } else if (img && img.width && img.height) return false;
            var nb = makeBg(); b.img = nb.img; b.bbox = nb.bbox; st.promoted--;
            st.last = { at: Date.now(), where: 'refill', id: b.id };
            try { if (typeof _gestureCompositeCache !== 'undefined') _gestureCompositeCache = null; } catch (_) { }   // eslint-disable-line no-undef
            return true;
        } catch (_) { return false; }
    }

    // ---- hooks (called from paint-booth-3-canvas.js) -------------------------------------------------------------------------
    /** clearPSDDocumentState: a new flat document starts. */
    function docReset() { st.pending = !off(); }
    /** _snapshotLayerStack(): tag a flat-state snapshot with a copy of the flat pixels (exact Undo to before the first layer). */
    function tagSnapshot(snap) {
        if (!Array.isArray(snap) || snap.length || !flatState()) return snap;
        try {
            var d = pid();
            snap.__spbFlatPx = { width: d.width, height: d.height, data: new Uint8ClampedArray(d.data) };
            st.pending = true;
        } catch (_) { }
        return snap;
    }
    /** _pushLayerStackUndo(label), after the entry is pushed. */
    function afterStackUndo(label) {
        if (off()) return;
        if (NO_PENDING[label]) { st.pending = false; return; }
        if (NO_PROMOTE[label]) return;
        if (flatState()) promote('push:' + label);
    }
    /** _restoreLayerStack(snapshot), after the stack is rebuilt and before it recomposites. */
    function afterRestore(snap) {
        if (off() || !snap || !snap.__spbFlatPx) return false;
        var L = layers(); if (!Array.isArray(L) || L.length) return false;
        var f = snap.__spbFlatPx, pc = canvas(); if (!pc) return false;
        try {
            if (pc.width !== f.width) pc.width = f.width;
            if (pc.height !== f.height) pc.height = f.height;
            var ctx = pc.getContext('2d', { willReadFrequently: true });
            var img = ctx.createImageData(f.width, f.height);
            img.data.set(f.data);
            ctx.putImageData(img, 0, 0);
            paintImageData = img; window.paintImageData = img;   // eslint-disable-line no-undef
            _psdLayersLoaded = false; window._psdLayersLoaded = false;   // eslint-disable-line no-undef
            window._spbLayerRev = (window._spbLayerRev || 0) + 1;
            if (typeof invalidateLayerVisibleContributionCache === 'function') invalidateLayerVisibleContributionCache();   // eslint-disable-line no-undef
            st.pending = true;
            return true;
        } catch (_) { return false; }
    }
    /** spb-projects.js, right after a saved Layer stack is put back on a FLAT source (project Open).
     *  Measured 2026-10-10 (probe_project.py, ARCA 1-superflo.tga + Layer + stroke, save, open): the layers came back
     *  (n=2) but _psdLayersLoaded stayed false, so the canvas showed the bare flat source (diff vs flat 0, stroke gone,
     *  hash 5d1ed4d0 vs saved a8ae9a32 / on-fix save). Now: a saved Background -> just composite; an old layers-only
     *  project (saved before this fix) -> the freshly loaded flat source goes under it as the Background. */
    function afterProjectRestore() {
        if (off()) return false;
        var L = layers(); if (!Array.isArray(L) || !L.length || loaded() || psdDoc() || !pidFits()) return false;
        var auto = L.some(function (l) { return l && (String(l.id || '').indexOf('autolayer_') === 0 || l.groupName === 'Auto-Separated'); });
        if (!L.some(isBg) && !auto) { promote('project'); return true; }   // Smart TGA layers already decompose the flat paint
        if (L.some(isBg)) refillIfEmpty(L.filter(isBg)[0]);
        try { _psdLayersLoaded = true; window._psdLayersLoaded = true; } catch (_) { }   // eslint-disable-line no-undef
        try { if (typeof _gestureCompositeCache !== 'undefined') _gestureCompositeCache = null; } catch (_) { }   // eslint-disable-line no-undef
        st.pending = false;
        return true;
    }
    /** recompositeFromLayers(), after the "stack loaded" check and before anything is drawn. */
    function beforeComposite() {
        if (off()) return;
        var L = layers(); if (!Array.isArray(L) || !L.length) return;
        if (st.pending) {
            if (!psdDoc()) { var b0 = L.filter(isBg)[0]; if (!b0) promote('composite'); else refillIfEmpty(b0); }
            st.pending = false;
        }
        // a locked Background stays at the bottom (a layer under an opaque full-canvas Background would be invisible)
        for (var i = 1; i < L.length; i++) {
            if (isBg(L[i]) && L[i].locked) {
                var b = L.splice(i, 1)[0]; L.unshift(b);
                try { if (typeof _gestureCompositeCache !== 'undefined') _gestureCompositeCache = null; } catch (_) { }   // eslint-disable-line no-undef
                break;
            }
        }
    }

    window.SPBFlatBg = {
        docReset: docReset, tagSnapshot: tagSnapshot, afterStackUndo: afterStackUndo, afterRestore: afterRestore,
        beforeComposite: beforeComposite, afterProjectRestore: afterProjectRestore, isBackground: isBg, flatState: flatState, off: off,
        state: function () { return { pending: st.pending, promoted: st.promoted, last: st.last, off: off() }; }
    };
})();
