/* [SPECIAL-ZONE 2026-10-11 owner] "If I go to Zone 1 and use a special brush can we make it where it works WITH the Zone Popout Panel? Like it fills in the
   BASE MATERIAL there with what you are painting? That way you can change the HSB sliders, the scale etc."

   Layer brush / Fill with Paint = Special, while the selected zone has "Clip to <zone>" ON and the option "Use as the zone's Base" is ON:
     - the stroke does NOT bake colour into the layer. Its per-pixel weight (pc-stroke fpOut: coverage x opacity x selection/zone clip x swatch alpha)
       becomes the zone's COVERAGE: zone.regionMask (+ useRegion) = the accumulated footprint; later strokes add, the eraser removes (copy-on-write,
       so snapshots are cheap references). regionMask is the zone's existing persisted drawn-region mask (RLE in the saved config), so save/reload keeps it.
     - the zone's Base Material becomes the Special through setZoneBase(i, 'mono:<id>') = the SAME function the Base picker calls, so the popout shows it
       and every popout slider (hue / sat / bright, base scale, spec scale, opacity ...) works and the engine renders it only on that footprint.
     - a zone that already has a DIFFERENT base is never overwritten: a new zone "<zone> - <Special>" with the same restrictions is inserted just above it.
     - ONE undo step ('special-zone' in the unified Ctrl+Z trail via SPBUndoExt) restores zones + mask together.
   Unpainted zone pixels look exactly as before. Option OFF / kill switch = the previous behaviour, byte for byte.
   KILL SWITCH: window.SPB_SPECIAL_ZONE_OFF = true (read on every call). Preference key: localStorage spb_special_zone ('0' = off, default ON). */
(function (root) {
    'use strict';
    const doc = root.document;
    const KIND = 'special-zone', PREF = 'spb_special_zone', MAXU = 20;
    const U = { stack: [], redo: [], reg: false };

    function killed() { return !!root.SPB_SPECIAL_ZONE_OFF; }
    function pref() { try { return root.localStorage.getItem(PREF) !== '0'; } catch (_) { return true; } }   // default ON (brief); was held OFF while the overlay bug was open
    function setPref(on) {
        try { root.localStorage.setItem(PREF, on ? '1' : '0'); } catch (_) {}
        const cb = doc && doc.getElementById('layerSpecialZoneToggle'); if (cb) cb.checked = !!on;
        refreshUi();
        return !!on;
    }
    function selZone() {
        try { return (typeof zones !== 'undefined' && selectedZoneIndex >= 0) ? (zones[selectedZoneIndex] || null) : null; } catch (_) { return null; }
    }
    function maskAny(m) { if (!m) return false; for (let i = 0; i < m.length; i++) if (m[i]) return true; return false; }
    function srcSpecial() { try { return typeof root.isLayerPaintSourceSpecial === 'function' && root.isLayerPaintSourceSpecial(); } catch (_) { return false; } }
    function userRegion(z) { return !!(z && !z._spzOwned && z.useRegion && z.regionMask && maskAny(z.regionMask)); }
    // the mode is in force for this stroke / fill
    function effective() {
        if (killed() || !pref() || !srcSpecial()) return false;
        const z = selZone(), zc = root.SPBZoneClip;
        if (!z || !zc || root.SPB_ZONECLIP_OFF || !zc.enabledFor(z)) return false;
        return !userRegion(z);
    }
    // the eraser / a Special stroke on an owned zone must not be clipped by the zone's OWN footprint (it is the thing being edited)
    function ignoreRegion(z) { return !!(z && z._spzOwned && !killed() && pref() && srcSpecial()); }
    function eraseOn() { const z = selZone(); return !!(z && z._spzOwned && effective()); }

    function finName(id) {
        try { const m = root._getLayerPaintSpecialMeta && root._getLayerPaintSpecialMeta(id); if (m && m.name) return m.name; } catch (_) {}
        return String(id || 'Special');
    }
    function toast(m, k) { try { if (typeof root.showToast === 'function') root.showToast(m, k); } catch (_) {} }

    // ------------------------------------------------------------------ undo (zones + mask in one step)
    function snap(ids) {
        const masks = new Map();
        (ids || []).forEach(function (id) { const z = zones.find(function (q) { return q && q.id === id; }); masks.set(id, z ? (z.regionMask || null) : null); });
        return {
            zs: zones.map(function (z) { return _cloneZoneState(z, { preserveId: true, includeRegionMask: false, includeSpatialMask: true, includePatternStrengthMap: true }); }),
            masks: masks, sel: selectedZoneIndex
        };
    }
    function restore(s) {
        const cur = new Map(); zones.forEach(function (z) { if (z && z.id != null) cur.set(z.id, z.regionMask || null); });
        zones.length = 0;
        s.zs.forEach(function (c) {
            const r = _ensureZoneShape(c, { includeRegionMask: false, includeSpatialMask: true });
            r.regionMask = s.masks.has(r.id) ? s.masks.get(r.id) : (cur.get(r.id) || null);
            zones.push(r);
        });
        selectedZoneIndex = Math.max(0, Math.min(s.sel, zones.length - 1));
        try { renderZones(); } catch (_) {}
        try { triggerPreviewRender(); } catch (_) {}
        clearOverlay();
    }
    function clearOverlay() { try { if (typeof root.renderRegionOverlay === 'function') root.renderRegionOverlay(); } catch (_) {} }
    function register() {
        if (U.reg || !root.SPBUndoExt) return !!U.reg;
        root.SPBUndoExt.register(KIND, {
            hasUndo: function () { return U.stack.length > 0; },
            hasRedo: function () { return U.redo.length > 0; },
            undo: function () { const e = U.stack.pop(); if (!e) return false; U.redo.push(e); restore(e.before); return true; },
            redo: function () { const e = U.redo.pop(); if (!e) return false; U.stack.push(e); restore(e.after); return true; },
            clearRedo: function () { U.redo.length = 0; },
            label: function () { const e = U.stack[U.stack.length - 1]; return e ? e.label : 'Special as zone Base'; }
        });
        U.reg = true; return true;
    }
    function reset() { U.stack.length = 0; U.redo.length = 0; clearOverlay(); }

    // ------------------------------------------------------------------ zone creation / base
    function sameRestrictions(a, b) {
        const k = function (z) { return JSON.stringify([z.sourceLayers || [], z.sourceLayer || null, z.colorMode, z.pickerColor, z.pickerTolerance, z.colors || [], z.color || null]); };
        return k(a) === k(b);
    }
    function newZoneAbove(z0, name) {
        const before = zones.length;
        if (typeof addZone !== 'function') return null;
        addZone(true);
        if (zones.length <= before) return null;               // zone limit reached
        const nz = zones[zones.length - 1];
        ['color', 'colorMode', 'pickerColor', 'pickerTolerance', 'colors', 'sourceLayer', 'sourceLayers', 'sourceLayerBindings', 'fitIntoApplyArea'].forEach(function (k) {
            if (z0[k] !== undefined) nz[k] = JSON.parse(JSON.stringify(z0[k] === undefined ? null : z0[k]));
        });
        nz.name = name;
        zones.pop();
        const at = zones.indexOf(z0);
        zones.splice(at < 0 ? 0 : at, 0, nz);                   // just above (a lower index wins overlaps)
        selectedZoneIndex = zones.indexOf(nz);
        return nz;
    }
    function setBase(zi, id) {
        const keep = root.pushZoneUndo;
        root.pushZoneUndo = function () {};                      // the whole action is ONE undo step ('special-zone')
        try { setZoneBase(zi, 'mono:' + id); } finally { root.pushZoneUndo = keep; }
    }

    // ------------------------------------------------------------------ the commit
    // buf: Float32Array(W*H) of weights 0..1 (only the bbox x0..x1 / y0..y1 is non-zero)
    function apply(id, W, H, buf, x0, y0, x1, y1, erase) {
        const z0 = selZone();
        if (!z0 || !id) return false;
        register();
        let any = false;
        for (let y = y0; y < y1 && !any; y++) { const o = y * W; for (let x = x0; x < x1; x++) if (buf[o + x] > 0) { any = true; break; } }
        if (!any) return false;
        const fin = _spbNormalizeFinishId(id) || id;
        // [SPECIAL-ALL 2026-10-12] the Choose Special picker now offers BASES; setZoneBase() files a base-registered id under zone.base (not zone.finish), so "same" must look there or every stroke would spawn a new zone
        const _isBaseId = typeof BASES !== 'undefined' && BASES.some(function (b) { return b && b.id === fin; });
        const isSame = function (z) { return !!z && (_isBaseId ? (z.base === fin && !z.finish) : ((z.finish === fin || z.finish === id) && !z.base)); };
        const hasBase = !!(z0.base || z0.finish);
        let target = z0, madeNew = false;
        if (erase) {
            if (!z0._spzOwned) return false;
        } else if (hasBase && !isSame(z0)) {
            // a sibling made earlier for this Special + these restrictions is reused; otherwise a new zone above
            const sib = zones.find(function (q) { return q && q._spzOwned && isSame(q) && sameRestrictions(q, z0); });
            if (sib) target = sib; else madeNew = true;
        }
        if (madeNew && zones.length >= (typeof MAX_ZONES === 'number' ? MAX_ZONES : 99)) { toast('Zone limit reached: delete a zone first.', true); return false; }
        const ids = [z0.id]; _ensureAllZonesHaveIds(zones);
        const before = snap([z0.id, target.id].filter(Boolean));
        before.masks.set(z0.id, z0.regionMask || null);
        const label = (erase ? 'Erase Special from ' : 'Special as Base: ') + finName(id);
        if (madeNew) {
            const nz = newZoneAbove(z0, (z0.name || 'Zone') + ' - ' + finName(id));
            if (!nz) return false;
            target = nz; _ensureAllZonesHaveIds(zones);
            before.masks.set(nz.id, null);
        }
        // accumulate the footprint (copy-on-write: the previous array stays valid for the undo snapshot)
        const old = (target._spzOwned && target.regionMask && target.regionMask.length === W * H) ? target.regionMask : null;
        const nm = old ? new Uint8Array(old) : new Uint8Array(W * H);
        for (let y = y0; y < y1; y++) {
            const o = y * W;
            for (let x = x0; x < x1; x++) {
                let a = buf[o + x]; if (!(a > 0)) continue; if (a > 1) a = 1;
                const i = o + x, p = nm[i];
                nm[i] = erase ? Math.round(p * (1 - a)) : Math.round(p + (255 - p) * a);
            }
        }
        target.regionMask = nm; target.useRegion = true; target._spzOwned = true;
        target._regionDesc = 'Special brush: ' + finName(id);
        if (!erase && !isSame(target)) setBase(zones.indexOf(target), id);
        else { try { if (typeof renderZones === 'function') renderZones(); } catch (_) {} }
        if (zones.indexOf(target) >= 0) selectedZoneIndex = zones.indexOf(target);
        const after = snap([z0.id, target.id].filter(Boolean));
        after.masks.set(target.id, nm); after.masks.set(z0.id, z0.regionMask || null);
        U.stack.push({ label: label, before: before, after: after });
        if (U.stack.length > MAX) U.stack.shift();
        U.redo.length = 0;
        try { if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND); } catch (_) {}
        try { if (typeof root.renderZones === 'function') root.renderZones(); } catch (_) {}
        try { if (typeof root.triggerPreviewRender === 'function') root.triggerPreviewRender(); } catch (_) {}
        clearOverlay();
        if (madeNew) toast('"' + z0.name + '" already has a different Base, so I made "' + target.name + '" above it with the same restrictions. Its Base is ' + finName(id) + '.');
        return true;
    }
    const MAX = MAXU;

    // layer-brush stroke commit (called from _commitLayerPaint). fp = { W, H, id, buf, x0, y0, x1, y1, erase? }. true = handled, layer untouched
    function commitStroke(fp) {
        if (!fp || !effective()) return false;
        return apply(fp.id, fp.W, fp.H, fp.buf, fp.x0, fp.y0, fp.x1, fp.y1, !!fp.erase);
    }
    // Special Fill: wt over the layer-local box at (lx, ly); W/H = the paint canvas
    function commitFill(id, W, H, lx, ly, lw, lh, wt) {
        if (!effective()) return false;
        const buf = new Float32Array(W * H);
        let x0 = W, y0 = H, x1 = 0, y1 = 0;
        for (let yy = 0; yy < lh; yy++) {
            const gy = ly + yy; if (gy < 0 || gy >= H) continue;
            for (let xx = 0; xx < lw; xx++) {
                const gx = lx + xx; if (gx < 0 || gx >= W) continue;
                const v = wt[yy * lw + xx]; if (!(v > 0)) continue;
                buf[gy * W + gx] = v; if (gx < x0) x0 = gx; if (gx >= x1) x1 = gx + 1; if (gy < y0) y0 = gy; if (gy >= y1) y1 = gy + 1;
            }
        }
        if (x1 <= x0) return false;
        return apply(id, W, H, buf, x0, y0, x1, y1, false);
    }

    // ------------------------------------------------------------------ UI
    function refreshUi() {
        if (!doc) return;
        const wrap = doc.getElementById('layerSpecialZoneWrap'), cb = doc.getElementById('layerSpecialZoneToggle');
        const sw = doc.getElementById('layerSpecialSpecToggle');
        const active = srcSpecial() && !killed();
        if (wrap) wrap.style.display = active ? 'inline-flex' : 'none';
        if (cb) cb.checked = pref();
        const on = effective();
        if (wrap) wrap.style.opacity = (cb && cb.checked && !on) ? '0.6' : '1';
        if (sw) {
            sw.disabled = !!on;
            const lab = sw.parentNode; if (lab && lab.style) lab.style.opacity = on ? '0.5' : '1';
        }
    }
    if (doc) {
        root.addEventListener('pointerdown', function () { try { refreshUi(); } catch (_) {} }, true);
        root.addEventListener('keyup', function () { try { refreshUi(); } catch (_) {} }, true);
    }

    root.SPBSpecialZone = { effective: effective, ignoreRegion: ignoreRegion, eraseOn: eraseOn, commitStroke: commitStroke, commitFill: commitFill, pref: pref, setPref: setPref,
        refreshUi: refreshUi, reset: reset, state: U };
    root.setSpecialZoneOn = setPref;
})(typeof window !== 'undefined' ? window : globalThis);
