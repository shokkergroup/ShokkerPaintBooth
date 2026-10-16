/* PORT-W5B / ZONECLIP 2026-10-09 (owner): "When I click BRUSH and the zone has RESTRICT TO LAYERS = BASE01 selected and I
   colour red where the numbers are, the red colours over ANYTHING including the numbers. It should ONLY colour red on that
   ZONE I'm working in."

   Zone "Restrict to layers" / picked colours only decide which pixels the zone's FINISH covers; the Layer-mode brush family
   ignored them and painted the active layer wherever the pointer went.  This module builds the zone's VISIBLE coverage
   (the same footprint the finish uses: union of the restricted layers' visible-contribution masks, i.e. min(own alpha,
   255 - art above), AND the picked-colour match on the source paint) and hands it to the tools through the existing
   selection-coverage path (_activeSelectionMask -> pc-stroke `sel`), multiplied with any active selection / alpha lock.

   Scope: only the layer-painting gesture (a layer stroke canvas is open) and Fill / Gradient on a layer ask for the clip;
   adjustments, selections and Zone-mode tools never see it.  The per-zone checkbox "Clip to <zone>" lives in the tool-options
   band (tool-options-split.js moves #spbZoneClipLabel up like every other primary control).  A zone with no area (no
   restricted layers, no picked colours) shows no checkbox and paints exactly as before.  The marching-ants / region-mask
   selection clip is a different, always-on contract and is NOT governed by this toggle.

   KILL SWITCH: window.SPB_ZONECLIP_OFF = true (read on every call) restores the previous behaviour exactly. */
(function (root, factory) {
    const api = factory(root);
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.SPBZoneClip = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';
    const doc = root.document;
    const PAINT_MODES = ['brush', 'erase', 'colorbrush', 'pencil', 'history-brush', 'smudge', 'clone', 'heal', 'recolor',
        'fill', 'gradient', 'dodge', 'burn', 'blur-brush', 'sharpen-brush'];
    const st = { off: new WeakSet(), layerPart: null, layerPartCov: null, covMask: null, sigC: null, colorPart: null, clip: null, combo: null, ui: null, uiKey: '', timer: null, lastWarn: 0, stats: { builds: 0, lastMs: 0 } };

    function disabled() { return !!root.SPB_ZONECLIP_OFF; }

    function selZone() {
        try {
            if (typeof zones === 'undefined' || typeof selectedZoneIndex !== 'number' || selectedZoneIndex < 0) return null;
            return zones[selectedZoneIndex] || null;
        } catch (_) { return null; }
    }
    function layerIds(zone) {
        try { return (typeof root.zoneSourceLayerIds === 'function') ? root.zoneSourceLayerIds(zone) : (zone && zone.sourceLayer ? [zone.sourceLayer] : []); } catch (_) { return []; }
    }
    // same colour targets the zone's finish selects by (mirrors _getZoneClientColorTargets)
    function colorTargets(zone) {
        if (!zone) return [];
        if (zone.colorMode === 'multi' && Array.isArray(zone.colors) && zone.colors.length > 0) return zone.colors.filter(function (c) { return c && Array.isArray(c.color_rgb); });
        if (zone.color && typeof zone.color === 'object' && !Array.isArray(zone.color) && Array.isArray(zone.color.color_rgb)) return [zone.color];
        if (zone.colorMode === 'picker' && typeof zone.pickerColor === 'string' && /^#[0-9a-fA-F]{6}$/.test(zone.pickerColor)) {
            const hex = zone.pickerColor;
            return [{ color_rgb: [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)], tolerance: zone.pickerTolerance != null ? zone.pickerTolerance : 40 }];
        }
        return [];
    }
    function hasArea(zone) { return !!zone && (layerIds(zone).length > 0 || colorTargets(zone).length > 0); }
    function enabledFor(zone) { return !disabled() && !!zone && hasArea(zone) && !st.off.has(zone); }
    function zoneId(zone) { return zone && (zone.id || zone.name) || ''; }

    function stackSig() {
        try { return _psdLayers.map(function (l) { return l.id + (l.visible === false ? 'h' : 'v') + (l.opacity | 0) + (l.clippingMask ? 'c' : '') + (l.blendMode || ''); }).join(','); } catch (_) { return ''; }
    }
    function compositeData() {
        try {
            if (typeof _activeLayerCanvas !== 'undefined' && _activeLayerCanvas && typeof _savedPaintImageData !== 'undefined' && _savedPaintImageData) return _savedPaintImageData;
            return (typeof paintImageData !== 'undefined') ? paintImageData : null;
        } catch (_) { return null; }
    }
    function toast(msg, kind) {
        try { if (typeof root.showToast === 'function') root.showToast(msg, kind); } catch (_) {}
    }

    // ---- coverage build ---------------------------------------------------------------------------------------------
    // layer part: union of the restricted layers' visible-contribution masks. Re-keyed on the layer composite revision.
    // [RESTRICT-PERF 2026-10-12] owner: "RESTRICT TO Numbers ... it also feels like its lagging a little too. Our tools should be very responsive".
    // Measured (headless Chrome, 11-layer car, Zone restricted to Numbers): every stroke START rebuilt this union mask (63-73 ms: two 2048x2048
    // getImageData + a layer-stack composite) because the cache key carried the GLOBAL composite revision, which every stroke commit bumps - even
    // when the layer that was painted can have no effect on the zone's footprint (the painted layer is excluded from "art above"). The key now
    // carries a signature of what the mask truly depends on: every layer's visibility/opacity/blend/clip/bbox/numeric props and the identity of its
    // pixels (layer.img), minus the layer being painted unless it is one of the restricted layers. Painting on an unrelated layer keeps the mask (0 ms),
    // any real change to a restricted layer or to art above it still rebuilds. The signature itself is cached per composite revision.
    // Kill switch: window.SPB_RESTRICT_PERF_OFF = true restores the old revision key.
    const imgToks = (typeof WeakMap === 'function') ? new WeakMap() : null;
    let imgTokN = 0;
    function imgTok(img) {
        if (!img || !imgToks) return 0;
        let t = imgToks.get(img);
        if (!t) { t = ++imgTokN; imgToks.set(img, t); }
        return t;
    }
    function layerSig(ids, exId, rev) {
        const ck = ids.join('+') + '|' + exId + '|' + rev;
        if (st.sigC && st.sigC.ck === ck) return st.sigC.v;
        let v = '';
        try {
            v = _psdLayers.map(function (l) {
                if (!l) return '';
                if (exId && l.id === exId && ids.indexOf(l.id) < 0) return 'x';   // the layer being painted is not "art above"
                let p = String(l.id) + '|' + imgTok(l.img) + '|' + (Array.isArray(l.bbox) ? l.bbox.join(',') : '') + '|' + (l.blendMode || '');
                const ks = Object.keys(l);
                for (let i = 0; i < ks.length; i++) {
                    const x = l[ks[i]], t = typeof x;
                    if (t === 'number' || t === 'boolean') p += '|' + ks[i] + '=' + x;
                }
                if (l.effects) { try { p += '|fx' + JSON.stringify(l.effects).length; } catch (_) {} }
                return p;
            }).join(';');
        } catch (_) { v = 'rev' + rev; }
        st.sigC = { ck: ck, v: v };
        return v;
    }
    function currentRev() { try { return (typeof _layerCompositeRevision !== 'undefined') ? _layerCompositeRevision : 0; } catch (_) { return 0; } }
    // opts.noEx: build the zone's own coverage (what its finish covers - no layer excluded); opts.quiet: no "hidden layer" toast
    function layerPart(zone, w, h, opts) {
        const ids = layerIds(zone);
        if (!ids.length || typeof root.getZoneSourceLayersUnionMask !== 'function') return null;
        const noEx = !!(opts && opts.noEx), quiet = !!(opts && opts.quiet);
        const rev = currentRev();
        // the layer being painted must not count as "art above" the zone's layers (else repainting its own art is locked out)
        let exId = null;
        if (!noEx) { try { const sl = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null; exId = sl && sl.id || null; } catch (_) {} }
        const key = root.SPB_RESTRICT_PERF_OFF
            ? ids.join('+') + '|' + rev + '|' + w + 'x' + h + '|' + exId + '|' + stackSig()
            : ids.join('+') + '|' + w + 'x' + h + '|' + exId + '|' + layerSig(ids, exId, rev);
        const slot = noEx ? 'layerPartCov' : 'layerPart';
        if (st[slot] && st[slot].zone === zone && st[slot].key === key) return st[slot].mask;
        const t0 = (typeof performance !== 'undefined') ? performance.now() : 0;
        const u = root.getZoneSourceLayersUnionMask(zone, w, h, exId) || {};
        let mask = null;
        if (u.union && u.union.length === w * h) mask = u.union;
        else if (u.requested > 0) {
            // every restricted layer is hidden / missing: the zone covers nothing, so the brush paints nothing (fail closed like the finish)
            mask = new Uint8Array(w * h);
            if (!quiet) toast('Zone "' + (zone.name || '') + '": its restricted layer' + (u.requested > 1 ? 's are' : ' is') + ' hidden or missing, so there is nothing to paint on. Show it, or untick "Clip to ' + (zone.name || 'zone') + '".', true);
        }
        st[slot] = { zone: zone, key: key, mask: mask };
        st.stats.builds++; st.stats.lastLayerMs = (typeof performance !== 'undefined') ? performance.now() - t0 : 0;
        return mask;
    }
    // colour part: pixels of the SOURCE paint within tolerance of a picked colour. Sticky across our own strokes (keyed on the
    // layer-stack structure, not pixel revisions) so re-painting an area you already recoloured is not locked out.
    function colorPart(zone, w, h) {
        const targets = colorTargets(zone);
        if (!targets.length) return null;
        const key = JSON.stringify(targets.map(function (t) { return [t.color_rgb, t.tolerance != null ? t.tolerance : (zone.pickerTolerance != null ? zone.pickerTolerance : 40)]; })) + '|' + w + 'x' + h + '|' + stackSig();
        if (st.colorPart && st.colorPart.zone === zone && st.colorPart.key === key) return st.colorPart.mask;
        const src = compositeData();
        if (!src || !src.data || src.data.length < w * h * 4) return null;
        const data = src.data, m = new Uint8Array(w * h);
        const nT = targets.length, rgb = new Array(nT), tol = new Array(nT);
        for (let t = 0; t < nT; t++) { rgb[t] = targets[t].color_rgb || [128, 128, 128]; tol[t] = Number(targets[t].tolerance != null ? targets[t].tolerance : (zone.pickerTolerance != null ? zone.pickerTolerance : 40)); }
        for (let i = 0, di = 0; i < m.length; i++, di += 4) {
            if (data[di + 3] < 8) continue;
            for (let t = 0; t < nT; t++) {
                const c = rgb[t], tl = tol[t];
                if (Math.abs(data[di] - c[0]) <= tl && Math.abs(data[di + 1] - c[1]) <= tl && Math.abs(data[di + 2] - c[2]) <= tl) { m[i] = 255; break; }
            }
        }
        st.colorPart = { zone: zone, key: key, mask: m };
        return m;
    }
    function clipFor(zone, w, h) {
        const lp = layerPart(zone, w, h), cp = colorPart(zone, w, h);
        if (!lp && !cp) return null;
        if (st.clip && st.clip.lp === lp && st.clip.cp === cp && st.clip.zone === zone) return st.clip.mask;
        let mask;
        if (lp && cp) { mask = new Uint8Array(lp.length); for (let i = 0; i < mask.length; i++) mask[i] = (lp[i] && cp[i]) ? 255 : 0; }
        else mask = lp || cp;
        st.clip = { zone: zone, lp: lp, cp: cp, mask: mask };
        return mask;
    }

    // [RESTRICT-PERF 2026-10-12] the zone's own coverage for the SOURCE overlay (js/canvas/pc-zonecov.js): restricted layers' footprint AND picked colours,
    // with NO layer excluded (that is what the finish covers, not what the brush may touch). Cached; the cheap coverageKey() lets the overlay poll for change.
    function coverageKey(zone, w, h) {
        if (!zone || !hasArea(zone)) return '';
        const ids = layerIds(zone);
        const tg = colorTargets(zone).map(function (t) { return [t.color_rgb, t.tolerance != null ? t.tolerance : (zone.pickerTolerance != null ? zone.pickerTolerance : 40)]; });
        return ids.join('+') + '~' + JSON.stringify(tg) + '~' + w + 'x' + h + '~' + (ids.length ? layerSig(ids, null, currentRev()) : '') + '~' + stackSig();
    }
    function coverage(zone, w, h) {
        if (!zone || !hasArea(zone)) return null;
        const lp = layerPart(zone, w, h, { noEx: true, quiet: true }), cp = colorPart(zone, w, h);
        if (!lp && !cp) return null;
        if (st.covMask && st.covMask.zone === zone && st.covMask.lp === lp && st.covMask.cp === cp) return st.covMask.mask;
        let mask;
        if (lp && cp) { mask = new Uint8Array(lp.length); for (let i = 0; i < mask.length; i++) mask[i] = (lp[i] && cp[i]) ? 255 : 0; }
        else mask = lp || cp;
        st.covMask = { zone: zone, lp: lp, cp: cp, mask: mask };
        return mask;
    }

    // base (selection / alpha lock / null) x zone clip. Combined mask cached per stroke canvas.
    function apply(w, h, base) {
        if (disabled()) return base;
        const zone = selZone();
        if (!enabledFor(zone)) return base;
        const t0 = (typeof performance !== 'undefined') ? performance.now() : 0;
        const clip = clipFor(zone, w, h);
        if (!clip) return base;
        if (!base || base.length !== clip.length) return clip;
        const cv = (typeof _activeLayerCanvas !== 'undefined') ? _activeLayerCanvas : null;
        if (cv && st.combo && st.combo.base === base && st.combo.clip === clip && st.combo.cv === cv) return st.combo.mask;
        const out = new Uint8Array(clip.length);
        for (let i = 0; i < out.length; i++) {
            const b = base[i], c = clip[i];
            out[i] = c === 255 ? b : (b === 255 ? c : ((b * c + 127) / 255) | 0);
        }
        if (cv) st.combo = { base: base, clip: clip, cv: cv, mask: out };
        st.stats.lastMs = (typeof performance !== 'undefined') ? performance.now() - t0 : 0;
        return out;
    }

    // ---- stroke-start hooks ------------------------------------------------------------------------------------------
    function isNoExportLayer(layer) {
        // Use the render path's actual policy, not its former blanket folder test.
        // Car Mandatory artwork is retained; do not warn that it is discarded.
        return !!layer && typeof root._nuqIsGuideLayer === 'function' &&
            !(typeof root._nuqOff === 'function' && root._nuqOff()) && root._nuqIsGuideLayer(layer);
    }
    const noExportToasted = {};
    function onStrokeStart(layer) {
        if (!layer || !isNoExportLayer(layer)) return;
        if (noExportToasted[layer.id]) return;
        noExportToasted[layer.id] = true;
        toast('You\'re painting on "' + (layer.name || 'this layer') + '", which isn\'t exported — pick a Paintable Area layer.', 'warn');
    }
    // called by shouldBrushStrokeProceed: a stroke that STARTS outside the zone's coverage paints nothing there. Say why.
    function warnIfOutside(p, pc) {
        if (disabled() || !p || !pc) return;
        const zone = selZone();
        if (!enabledFor(zone)) return;
        const clip = clipFor(zone, pc.width, pc.height);
        if (!clip || clip[p.y * pc.width + p.x]) return;
        // [SPECIAL-ZONE 2026-10-11 owner] a stroke that STARTS outside the zone but drags into it does paint: only say so when the WHOLE stroke
        // painted nothing (flushWarn, called by the layer commit). Kill switch window.SPB_CLIPTOAST_OFF = old immediate toast.
        if (!root.SPB_CLIPTOAST_OFF) {
            st.pendingWarn = 'Nothing painted: that spot is outside "' + (zone.name || 'this zone') + '" (Clip to Zone is on). Start inside the zone, or untick "Clip to ' + (zone.name || 'zone') + '".';
            return;
        }
        const now = Date.now();
        if (now - st.lastWarn < 4000) return;
        st.lastWarn = now;
        toast('Painting is clipped to "' + (zone.name || 'this zone') + '" — this spot is outside its area, so nothing will paint here. Start inside the zone, or untick "Clip to ' + (zone.name || 'zone') + '".', 'warn');
    }

    // [SPECIAL-ZONE 2026-10-11] stroke end: show the deferred "outside" message only when the stroke painted nothing at all.
    function setPending(msg) { st.pendingWarn = msg || null; }
    function flushWarn(painted) {
        const m = st.pendingWarn; st.pendingWarn = null;
        if (!m || painted) return false;
        const now = Date.now();
        if (now - st.lastWarn < 1500) return false;
        st.lastWarn = now;
        toast(m, 'warn');
        return true;
    }

    // ---- UI: checkbox in the tool-options bar (moved up into the band by tool-options-split.js) ---------------------------
    function buildUi() {
        if (st.ui || !doc) return st.ui;
        const bar = doc.getElementById('toolSpecificOptions');
        if (!bar) return null;
        const label = doc.createElement('label');
        label.id = 'spbZoneClipLabel';
        label.setAttribute('style', 'font-size:9px; color:var(--text-dim); display:none; cursor:pointer; white-space:nowrap; margin-left:6px;');
        const input = doc.createElement('input');
        input.type = 'checkbox'; input.id = 'spbZoneClipToggle'; input.checked = true;
        input.setAttribute('style', 'margin-right:2px;vertical-align:middle;');
        const text = doc.createElement('span');
        text.id = 'spbZoneClipText';
        label.appendChild(input); label.appendChild(text);
        input.addEventListener('change', function () {
            const zone = selZone();
            if (!zone) return;
            if (input.checked) st.off.delete(zone); else st.off.add(zone);
            st.combo = null;
            toast(input.checked ? 'Painting is clipped to ' + (zone.name || 'the zone') + '.' : 'Clip off — painting can cover anything on the layer, not just ' + (zone.name || 'the zone') + '.');
        });
        bar.appendChild(label);
        st.ui = { label: label, input: input, text: text };
        return st.ui;
    }
    function layerMode() { try { return typeof isLayerToolbarMode === 'function' && isLayerToolbarMode(); } catch (_) { return false; } }
    function currentMode() { try { return (typeof canvasMode !== 'undefined') ? canvasMode : ''; } catch (_) { return ''; } }
    function sync() {
        const ui = buildUi();
        if (!ui) return;
        const zone = selZone();
        const show = !disabled() && !!zone && hasArea(zone) && layerMode() && PAINT_MODES.indexOf(currentMode()) >= 0;
        const nm = zone ? String(zone.name || 'zone') : '';
        const on = !!zone && !st.off.has(zone);
        const key = (show ? '1' : '0') + '|' + nm + '|' + (on ? '1' : '0');
        if (key === st.uiKey) return;
        st.uiKey = key;
        ui.label.style.display = show ? '' : 'none';
        ui.text.textContent = 'Clip to ' + (nm.length > 18 ? nm.slice(0, 17) + '…' : nm);
        ui.input.checked = on;
        ui.label.title = 'ON = the brush, eraser, fill, smudge, clone and the rest only change what is inside "' + nm + '"\'s own area (its Restrict-to-layers art / picked colours) — numbers and decals on layers above are left alone. Off = they paint anywhere on the active layer.';
    }
    function start() {
        if (!doc || st.timer) return;
        sync();
        st.timer = root.setInterval(sync, 400);
    }
    if (doc) {
        if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
    }

    return {
        apply: apply, warnIfOutside: warnIfOutside, onStrokeStart: onStrokeStart, enabledFor: enabledFor, hasArea: hasArea, coverage: coverage, coverageKey: coverageKey, colorTargets: colorTargets, layerIds: layerIds,
        clipFor: clipFor, flushWarn: flushWarn, setPending: setPending, isNoExportLayer: isNoExportLayer, sync: sync, state: st,
        setOff: function (zone, off) { if (!zone) return; if (off) st.off.add(zone); else st.off.delete(zone); st.combo = null; st.uiKey = ''; sync(); }
    };
});
