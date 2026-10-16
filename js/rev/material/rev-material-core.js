/* [SPB-REV-MATERIAL 2026-10-10] Material Brush / Spec Brush / Wear Brush: state, strokes, undo, payload.
 *
 * Data model (design: _easy_claude_work/rev_tools/material/DESIGN.md)
 *  - coats[]: one per brushed SPB finish. mask = soft brush alpha 0..255 (document pixels). Sent as
 *    extra server zones inside `_spb_rev_material.coats`; the engine renders the real finish there and
 *    blends it by this alpha (engine/rev_material_layer.py), so opacity + feathered edges are linear.
 *  - spec layer: sv (M,R,CC values) + sc (per-channel coverage). Spec Brush + Wear write it.
 *  - paint layer: pv (RGB) + pc (coverage). Wear (and a picked material with Paint on) write it.
 *  Later strokes cover earlier ones: a Material stroke lowers the other coats and the spec/paint layer
 *  coverage under it; Spec/Wear strokes composite over everything (post-pass).
 *
 * Undo: one entry per stroke = 64 px tiles snapshotted before/after (exact bytes), routed through the
 * app's chronological Ctrl+Z trail via the generic `window.SPBUndoExt` registry (kind 'rev-material').
 * Kill switch: window.SPB_REV_MAT_OFF = true or localStorage SPB_REV_MAT_OFF = '1'.
 */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    const KIND = 'rev-material';
    const TS = 64, TSH = 6, UNDO_MAX = 40;

    function off() {
        if (root.SPB_REV_MAT_OFF) return true;
        try { return root.localStorage.getItem('SPB_REV_MAT_OFF') === '1'; } catch (_) { return false; }
    }
    // [BRUSH-STUDIO 2026-10-10] (lane BRUSH-STUDIO, owner 11:15 "PAINT with the brush that has that pattern/style ... OR just paint Spec on").
    // A studio coat = (finish, plane, keep, params). plane 'paint' | 'spec': "Paint + Spec" strokes a paint coat AND a spec coat,
    // "Spec only" a spec coat (the paint stays byte-identical; with the opt-in Surface texture it is a keep coat = the T-2 Keep Colour
    // texture), "Paint only" a paint coat (the spec under it stays). params are the zone sliders (colour as Tint = Color Lab Depth or
    // Solid, base scale, base rotation, strength, spec strength) written into the coat zone with the SAME fields
    // the zone setters write, so a brushed finish renders like the same finish on a zone. The engine renders each (finish, params)
    // ONCE on the full canvas (car-space anchor) and only re-composites per stroke (engine/rev_material_layer.py _composite_studio).
    // Kill switch: window.SPB_BRUSH_STUDIO_OFF = true or localStorage SPB_BRUSH_STUDIO_OFF = '1' (today's brushes); server env SPB_BRUSH_STUDIO_OFF=1.
    function bsOff() {
        if (root.SPB_BRUSH_STUDIO_OFF) return true;
        try { return root.localStorage.getItem('SPB_BRUSH_STUDIO_OFF') === '1'; } catch (_) { return false; }
    }
    const PDEF = { color: null, colorMode: 'tint', colorDepth: 0.65, colorStrength: 1, scale: 1, rotation: 0, strength: 1, specStrength: 1 };
    function clampN(v, lo, hi, d) { v = Number(v); return isFinite(v) ? Math.max(lo, Math.min(hi, v)) : d; }
    function normParams(p) {
        p = p || {};
        const hex = /^#?([0-9a-f]{6})$/i.exec(String(p.color || ''));
        return {
            color: hex ? '#' + hex[1].toLowerCase() : null,
            // [BRUSH-STUDIO 2026-10-10] 'tint' (default) = the zone's COLOR LAB Depth: the colour multiplies over the finish's own
            // value structure, so the pattern survives (a plain solid override at 100% flattens a Far Out paint to one flat colour;
            // ARCA proof shots/zone_refs_peek.png). 'solid' = the zone's Use solid color + Color Strength.
            colorMode: p.colorMode === 'solid' ? 'solid' : 'tint',
            colorDepth: Math.round(clampN(p.colorDepth, 0, 1, 0.65) * 100) / 100,
            colorStrength: Math.round(clampN(p.colorStrength, 0, 1, 1) * 100) / 100,
            scale: +Math.max(0.05, Math.round(clampN(p.scale, 0.05, 10, 1) / 0.05) * 0.05).toFixed(2),
            rotation: Math.round(clampN(p.rotation, 0, 359, 0) / 5) * 5 % 360,
            strength: Math.round(clampN(p.strength, 0, 2, 1) * 100) / 100,
            specStrength: Math.round(clampN(p.specStrength, 0, 2, 1) * 100) / 100,
            flake: normFlake(p.flake)
        };
    }
    // [SPB-REV-FLAKE 2026-10-10] (lane REV-FLAKE, additive) a Flake Studio recipe rides on the coat: applyParams -> zone.spbFlake ->
    // serializer spb_flake -> the engine's per-zone flake hook (engine/rev_flake.py). JSON clone or null; window.SPB_FLAKE_OFF drops it.
    function normFlake(f) {
        if (!f || typeof f !== 'object' || root.SPB_FLAKE_OFF) return null;
        try { return JSON.parse(JSON.stringify(f)); } catch (_) { return null; }
    }
    function psig(p) {
        const n = normParams(p), col = n.color ? [n.color, n.colorMode, n.colorMode === 'solid' ? n.colorStrength : n.colorDepth] : ['-'];
        return col.concat([n.scale, n.rotation, n.strength, n.specStrength]).join('|') + (n.flake ? '|flake:' + JSON.stringify(n.flake) : '');
    }
    function isDefaultParams(p) { return psig(p) === psig(PDEF); }
    // the zone setters' field writes (paint-booth-2-state-zones.js setZoneBaseColorMode('solid') + setZoneBaseColor, setZoneBaseColorStrength,
    // setZoneBaseScale -> SPBBaseSpecScaleLink.applyBaseScale, setZoneBaseRotation, setZoneBaseStrength, setZoneBaseSpecStrength); defaults are left untouched
    function applyParams(z, p) {
        const n = normParams(p);
        if (n.color) {
            z.baseColorMode = 'solid'; z.baseColorModeExplicit = true; z.baseColor = n.color; z.baseColorSource = null;
            z._autoBaseColorFill = false; z._scopedBrushAutoBaseColor = false; z.baseColorStrength = n.colorStrength;
            if (n.colorMode === 'tint') {   // = _spbEnsureColorLab + setZoneBaseColorDepth (paint-booth-2-state-zones.js)
                if (z.baseColorFlip == null) z.baseColorFlip = 0;
                if (z.baseColorUnderglow == null) z.baseColorUnderglow = 0;
                z.baseColorStrength = 1; z.baseColorDepth = n.colorDepth;
            }
        }
        if (n.scale !== 1) {
            const link = root.SPBBaseSpecScaleLink;
            if (link && typeof link.applyBaseScale === 'function') link.applyBaseScale(z, n.scale);
            else { z.baseScale = n.scale; if (z.specScaleMode !== 'independent') { z.specScaleMode = 'match'; z.specScale = n.scale; } }
        }
        if (n.rotation !== 0) z.baseRotation = n.rotation;
        if (n.strength !== 1) z.baseStrength = n.strength;
        if (n.specStrength !== 1) z.baseSpecStrength = n.specStrength;
        if (n.flake) z.spbFlake = n.flake;   // [SPB-REV-FLAKE 2026-10-10]
        return z;
    }
    function paramsLabel(p) {
        const n = normParams(p), out = [];
        if (n.color) out.push(n.colorMode === 'tint' ? 'tint ' + n.color + ' ' + Math.round(n.colorDepth * 100) + '%' : 'colour ' + n.color + (n.colorStrength !== 1 ? ' ' + Math.round(n.colorStrength * 100) + '%' : ''));
        if (n.scale !== 1) out.push('scale ' + Math.round(n.scale * 100) + '%');
        if (n.rotation) out.push('rotation ' + n.rotation + '°');
        if (n.strength !== 1) out.push('strength ' + Math.round(n.strength * 100) + '%');
        if (n.specStrength !== 1) out.push('spec strength ' + Math.round(n.specStrength * 100) + '%');
        if (n.flake) out.push('flake ' + String(n.flake.look || 'custom').replace(/_/g, ' ') + (n.flake.size_cm ? ' ' + n.flake.size_cm + ' cm' : ''));   // [SPB-REV-FLAKE 2026-10-10]
        return out.join(', ');
    }
    const MODE_NAME = { both: 'Paint + Spec', spec: 'Spec only', paint: 'Paint only' };

    // ---------------------------------------------------------------- generic undo extension registry
    // paint-booth-3-canvas.js routes any trail kind registered here (4 tiny kill-switched hooks).
    if (!root.SPBUndoExt) {
        const reg = Object.create(null);
        root.SPBUndoExt = {
            register: function (kind, impl) { reg[kind] = impl; },
            owns: function (kind) { return !root.SPB_UNDOEXT_OFF && !!reg[kind]; },
            has: function (kind, which) {
                const r = reg[kind];
                if (!r || root.SPB_UNDOEXT_OFF) return false;
                try { return which === 'redo' ? !!r.hasRedo() : !!r.hasUndo(); } catch (_) { return false; }
            },
            undo: function (kind) { const r = reg[kind]; try { return !!(r && r.undo()); } catch (e) { console.warn('[SPBUndoExt] undo', kind, e); return false; } },
            redo: function (kind) { const r = reg[kind]; try { return !!(r && r.redo()); } catch (e) { console.warn('[SPBUndoExt] redo', kind, e); return false; } },
            clearRedo: function () { for (const k in reg) { try { if (reg[k].clearRedo) reg[k].clearRedo(); } catch (_) {} } },
            label: function (kind) { const r = reg[kind]; try { return r && r.label ? String(r.label() || '') : ''; } catch (_) { return ''; } }
        };
    }

    // ---------------------------------------------------------------- state
    const S = {
        W: 0, H: 0, coats: [], sv: null, sc: null, pv: null, pc: null,
        hasSpec: false, hasPaint: false, lb: null,          // layer bbox [x0,y0,x1,y1]
        coatVer: 0, layerVer: 0, enc: { ver: -1 }, coatEnc: { ver: -1, objs: null },
        undo: [], redo: [], st: null, cov: null, seq: 0, strokeSeq: 0, tpl: null, gen: 0,
        listeners: []
    };
    function emit(what, info) { S.listeners.forEach(function (f) { try { f(what, info); } catch (_) {} }); }

    function canvasDims() {
        const pc = doc.getElementById('paintCanvas');
        return pc ? [pc.width | 0, pc.height | 0] : [0, 0];
    }
    function ensure() {
        const d = canvasDims();
        if (!d[0] || !d[1]) return false;
        if (d[0] !== S.W || d[1] !== S.H) reset(d[0], d[1]);
        return true;
    }
    function reset(w, h) {
        S.W = w; S.H = h; S.coats = []; S.sv = S.sc = S.pv = S.pc = null; S.hasSpec = S.hasPaint = false; S.lb = null;
        S.undo.length = 0; S.redo.length = 0; S.cov = null; S.st = null;
        S.coatVer++; S.layerVer++; S.gen++;
        emit('reset');
    }
    function ensureLayers() {
        if (S.sv) return;
        const n = S.W * S.H;
        S.sv = new Uint8Array(n * 3); S.sc = new Uint8Array(n * 3); S.pv = new Uint8Array(n * 3); S.pc = new Uint8Array(n);
    }

    // ---------------------------------------------------------------- finishes / coats
    function rawId(id) { return String(id || '').replace(/^mono:/, ''); }
    function finishName(id) {
        const raw = rawId(id);
        try { if (typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID[raw]) return BASES_BY_ID[raw].name || raw; } catch (_) {}
        try { if (typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID[raw]) return MONOLITHICS_BY_ID[raw].name || raw; } catch (_) {}
        return raw.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }
    // A coat zone must look EXACTLY like a zone the picker made, so borrow addZone's fresh-zone shape
    // once (without leaving a zone behind) and apply the finish through the picker's own helpers.
    function zoneTemplate() {
        if (S.tpl) return JSON.parse(S.tpl);
        if (typeof addZone !== 'function' || typeof zones === 'undefined') return null;
        const n = zones.length, sel = selectedZoneIndex, rz = root.renderZones;
        let fresh = null;
        root.renderZones = function () {};
        try {
            addZone(true);
            if (zones.length === n + 1) fresh = zones.pop();
        } catch (e) { console.warn('[REV-MATERIAL] template', e); }
        finally { root.renderZones = rz; selectedZoneIndex = sel; }
        if (!fresh) return null;
        delete fresh.renderSeedIndex;
        S.tpl = JSON.stringify(fresh);
        return JSON.parse(S.tpl);
    }
    function makeCoatZone(finishId, params) {
        const t = zoneTemplate();
        if (!t) return null;
        const raw = rawId(finishId);
        try {
            const isMono = String(finishId).indexOf('mono:') === 0;
            const isBase = typeof BASES !== 'undefined' && BASES.find(function (b) { return b.id === raw; });
            if (isMono && !isBase && typeof _spbApplyPickedMonolithicToZone === 'function') _spbApplyPickedMonolithicToZone(t, raw);
            else if (typeof _spbApplyPickedBaseToZone === 'function') _spbApplyPickedBaseToZone(t, raw);
            else { t.base = isMono ? null : raw; t.finish = isMono ? raw : null; }
        } catch (e) { t.base = raw; }
        if (!t.pattern) t.pattern = 'none';
        t.color = null; t.colorMode = 'none'; t.colors = [];
        t.useRegion = true; t.hardEdge = true; t.muted = false;
        if (params) {
            // [BRUSH-STUDIO 2026-10-10] studio coat: zone sliders + car-space anchor. renderSeedIndex is fixed (0) so every coat of a finish
            // (its paint AND spec coat, every stroke) shares one seed / one engine render; the serializer's seed prepare keeps a valid index.
            applyParams(t, params);
            t.textureAnchor = 'canvas';
            t.renderSeedIndex = 0;
        }
        return t;
    }
    // [REV-MATERIAL-2 2026-10-10] a coat is (finish, keep-colour): the same finish brushed with Keep Colour on
    // and off are two coats (the engine blends paint differently for each; see engine/rev_material_layer.py).
    // [BRUSH-STUDIO 2026-10-10] + plane ('paint' | 'spec', legacy coats have none) + the slider params signature.
    function coatFor(finishId, create, keep, plane, params) {
        keep = !!keep;
        const studio = plane === 'paint' || plane === 'spec';
        const sig = studio ? psig(params) : '';
        for (let i = 0; i < S.coats.length; i++) {
            const c = S.coats[i];
            if (c.finishId !== finishId || !!c.keep !== keep) continue;
            if ((c.plane || '') !== (studio ? plane : '')) continue;
            if (studio && c.psig !== sig) continue;
            return c;
        }
        if (!create) return null;
        const np = studio ? normParams(params) : null;
        const z = makeCoatZone(finishId, np);
        if (!z) return null;
        const c = { id: 'rmc' + (++S.seq), finishId: finishId, keep: keep, name: finishName(finishId), mask: new Uint8Array(S.W * S.H), zone: z, box: null };
        if (studio) { c.plane = plane; c.params = np; c.psig = sig; }
        z.name = coatZoneName(c);
        z.regionMask = c.mask;
        S.coats.push(c);
        return c;
    }
    function coatZoneName(c) {
        if (!c.plane) return 'Material: ' + c.name + (c.keep ? ' (keep colour)' : '');
        const pl = paramsLabel(c.params);
        return 'Brush Studio: ' + c.name + ' [' + c.plane + (c.keep ? ', keep colour' : '') + ']' + (pl ? ' (' + pl + ')' : '') + ' #' + c.id;
    }
    // [BRUSH-STUDIO 2026-10-10] which brush mode made a studio coat: a paint coat and a spec coat of the same finish + sliders
    // (spec without the surface texture) are the two halves of Paint + Spec; alone they are Paint only / Spec only.
    function studioMode(c, list) {
        if (!c || !c.plane) return null;
        if (c.plane === 'spec' && c.keep) return 'spec';
        const twin = (list || S.coats).some(function (x) { return x !== c && x.plane && x.plane !== c.plane && !x.keep && x.finishId === c.finishId && x.psig === c.psig && coatHasPixels(x); });
        return twin ? 'both' : c.plane;
    }
    function growBox(b, x0, y0, x1, y1) {
        if (!b) return [x0, y0, x1, y1];
        if (x0 < b[0]) b[0] = x0; if (y0 < b[1]) b[1] = y0; if (x1 > b[2]) b[2] = x1; if (y1 > b[3]) b[3] = y1;
        return b;
    }

    // ---------------------------------------------------------------- clip (selection x zone coverage)
    function clipMask() {
        const W = S.W, H = S.H;
        try {
            if (typeof _activeSelectionMask === 'function') {
                const m = _activeSelectionMask(W, H, true);
                if (m && m.length === W * H) return m;
            }
        } catch (_) {}
        try {
            const zc = root.SPBZoneClip;
            if (zc && !root.SPB_ZONECLIP_OFF && typeof zones !== 'undefined') {
                const z = zones[selectedZoneIndex];
                if (z && zc.enabledFor(z)) { const m = zc.clipFor(z, W, H); if (m && m.length === W * H) return m; }
            }
        } catch (_) {}
        return null;
    }
    function clipInfo() {
        try {
            if (typeof zones === 'undefined') return null;
            const z = zones[selectedZoneIndex];
            const zc = root.SPBZoneClip;
            if (!z || !zc || root.SPB_ZONECLIP_OFF || !zc.hasArea(z)) return { zone: z, on: false, can: false };
            return { zone: z, on: zc.enabledFor(z), can: true };
        } catch (_) { return null; }
    }

    // ---------------------------------------------------------------- tiles (undo snapshots)
    function tilesX() { return (S.W + TS - 1) >> TSH; }
    function capture(tx, ty) {
        const W = S.W, H = S.H, x0 = tx << TSH, y0 = ty << TSH, x1 = Math.min(W, x0 + TS), y1 = Math.min(H, y0 + TS), rw = x1 - x0;
        const snap = { coat: {}, sv: null, sc: null, pv: null, pc: null };
        S.coats.forEach(function (c) {
            const a = new Uint8Array(TS * TS);
            for (let y = y0; y < y1; y++) a.set(c.mask.subarray(y * W + x0, y * W + x1), (y - y0) * TS);
            snap.coat[c.id] = a;
        });
        if (S.sv) {
            snap.sv = new Uint8Array(TS * TS * 3); snap.sc = new Uint8Array(TS * TS * 3);
            snap.pv = new Uint8Array(TS * TS * 3); snap.pc = new Uint8Array(TS * TS);
            for (let y = y0; y < y1; y++) {
                const s = (y * W + x0), d = (y - y0) * TS;
                snap.sv.set(S.sv.subarray(s * 3, (s + rw) * 3), d * 3);
                snap.sc.set(S.sc.subarray(s * 3, (s + rw) * 3), d * 3);
                snap.pv.set(S.pv.subarray(s * 3, (s + rw) * 3), d * 3);
                snap.pc.set(S.pc.subarray(s, s + rw), d);
            }
        }
        return snap;
    }
    function restoreTile(key, snap, coatsById) {
        const W = S.W, H = S.H, tx = key % tilesX(), ty = (key / tilesX()) | 0;
        const x0 = tx << TSH, y0 = ty << TSH, x1 = Math.min(W, x0 + TS), y1 = Math.min(H, y0 + TS), rw = x1 - x0;
        Object.keys(snap.coat).forEach(function (id) {
            const c = coatsById[id];
            if (!c) return;
            const a = snap.coat[id];
            for (let y = y0; y < y1; y++) c.mask.set(a.subarray((y - y0) * TS, (y - y0) * TS + rw), y * W + x0);
        });
        if (snap.sv && S.sv) {
            for (let y = y0; y < y1; y++) {
                const s = (y * W + x0), d = (y - y0) * TS;
                S.sv.set(snap.sv.subarray(d * 3, (d + rw) * 3), s * 3);
                S.sc.set(snap.sc.subarray(d * 3, (d + rw) * 3), s * 3);
                S.pv.set(snap.pv.subarray(d * 3, (d + rw) * 3), s * 3);
                S.pc.set(snap.pc.subarray(d, d + rw), s);
            }
        }
        return [x0, y0, x1, y1];
    }
    function snapTiles(st, x0, y0, x1, y1) {
        const TX = tilesX();
        for (let ty = y0 >> TSH; ty <= (y1 - 1) >> TSH; ty++) {
            for (let tx = x0 >> TSH; tx <= (x1 - 1) >> TSH; tx++) {
                const k = ty * TX + tx;
                if (!st.tiles.has(k)) { const s = capture(tx, ty); st.tiles.set(k, s); st.tarr[k] = s; }
            }
        }
    }

    // ---------------------------------------------------------------- strokes
    const DIR_PX = 6;
    function needsDir(o) { return o.tool === 'wear' || (o.tool === 'spec' && !o.erase && o.preset && o.preset.grain > 0); }

    /**
     * o = { tool: 'material'|'spec'|'wear', erase, finishId, preset {m,r,cc,chan:[1,1,1],grain,grainKind},
     *       paint: [r,g,b]|null (spec tool: also write paint, e.g. a picked material), wearType,
     *       opacity 0..1, hardness 0..1 }
     */
    function beginStroke(o) {
        if (off() || !ensure()) return false;
        if (S.st) endStroke();
        const n = S.W * S.H;
        if (!S.cov || S.cov.length !== n) S.cov = new Float32Array(n);
        const st = {
            o: o, tiles: new Map(), tarr: new Array(tilesX() * ((S.H + TS - 1) >> TSH)), box: null,
            created: null, coat: null, clip: o.noClip ? null : clipMask(), ctx: null, pend: [], start: null,
            seed: ((S.strokeSeq++) * 7919 + 17) | 0, changed: false, layersTouched: false, coatsTouched: false
        };
        if (o.tool === 'material' && o.studio && !bsOff()) {
            // [BRUSH-STUDIO 2026-10-10] one stroke -> the coats of its mode; st.planes = the planes this stroke paints over / erases
            const md = o.mode === 'spec' || o.mode === 'paint' ? o.mode : 'both';
            st.studio = true; st.mode = md;
            st.planes = { paint: md !== 'spec', spec: md !== 'paint' };
            st.targets = [];
            if (!o.erase) {
                const want = md === 'both' ? [['paint', false], ['spec', false]] : (md === 'spec' ? [['spec', !!o.keep]] : [['paint', false]]);   // Spec only: keep = the opt-in Surface texture
                for (let k = 0; k < want.length; k++) {
                    let c = coatFor(o.finishId, false, want[k][1], want[k][0], o.params);
                    if (!c) { c = coatFor(o.finishId, true, want[k][1], want[k][0], o.params); if (c) (st.createdList || (st.createdList = [])).push(c); }
                    if (!c) { (st.createdList || []).forEach(function (x) { const ix = S.coats.indexOf(x); if (ix >= 0) S.coats.splice(ix, 1); }); return false; }
                    st.targets.push(c);
                }
                st.coat = st.targets[0];
                if (st.createdList && st.createdList.length) st.created = st.createdList.length === 1 ? st.createdList[0] : st.createdList.slice();
            }
        } else if (o.tool === 'material' && !o.erase) {
            st.coat = coatFor(o.finishId, false, o.keep);
            if (!st.coat) { st.coat = coatFor(o.finishId, true, o.keep); st.created = st.coat; }
            if (!st.coat) return false;
        }
        if ((o.tool === 'spec' || o.tool === 'wear') && !o.erase) ensureLayers();
        if (!needsDir(o)) st.ctx = makeCtx(st, o.angle || 0);
        S.st = st;
        emit('begin', st);
        return true;
    }
    function makeCtx(st, angle) {
        st.angle = angle;
        return root.SPBRevMatRecipes ? root.SPBRevMatRecipes.makeContext(angle, st.seed) : null;
    }
    function dab(x, y, radius, hardnessOverride) {
        const st = S.st;
        if (!st) return null;
        if (!st.start) st.start = [x, y];
        if (!st.ctx) {
            st.pend.push([x, y, radius, hardnessOverride]);
            const dx = x - st.start[0], dy = y - st.start[1];
            if (dx * dx + dy * dy < DIR_PX * DIR_PX) return null;
            st.ctx = makeCtx(st, Math.atan2(dy, dx));
            const q = st.pend; st.pend = [];
            let r = null;
            q.forEach(function (d) { const b = applyDab(st, d[0], d[1], d[2], d[3]); if (b) r = b; });
            return r;
        }
        return applyDab(st, x, y, radius, hardnessOverride);
    }

    const _tex = { pr: 0, pg: 0, pb: 0, pa: 0, m: 0, r: 0, cc: 0, am: 0, ar: 0, ac: 0 };
    const _spv = { m: 0, r: 0, cc: 0 };
    function cov8(oc8, a) { return oc8 + (255 - oc8) * a; }

    function applyDab(st, x, y, radius, hardnessOverride) {
        // [SPB-REV-SYM2 2026-10-10] Mirror Paint for the Material tools (lane REV-SYMMETRY): with Mirror Paint on, symmetry replays this dab at the
        // matching spot of the other side (same stroke, same undo step, zone clip x target part). Pass-through when the hook is absent or off.
        if (!st.symBusy && root.SpbRevSymTools && root.SpbRevSymTools.materialDab) root.SpbRevSymTools.materialDab(st, x, y, radius, hardnessOverride, applyDab);
        const W = S.W, H = S.H, o = st.o;
        const r = Math.max(0.5, +radius || 1);
        const cx = (+x) + 0.5, cy = (+y) + 0.5;
        const x0 = Math.max(0, Math.floor(cx - r - 1)), y0 = Math.max(0, Math.floor(cy - r - 1));
        const x1 = Math.min(W, Math.ceil(cx + r + 1)), y1 = Math.min(H, Math.ceil(cy + r + 1));
        if (x1 <= x0 || y1 <= y0) return null;
        snapTiles(st, x0, y0, x1, y1);
        const hard = hardnessOverride == null ? (o.hardness == null ? 0.8 : o.hardness) : hardnessOverride;
        const cap = Math.max(0, Math.min(1, o.opacity == null ? 1 : o.opacity));
        const clip = st.clip, cov = S.cov, TX = tilesX(), tarr = st.tarr;
        const fall = (root.SPBPcStroke && root.SPBPcStroke.dabCoverage) || function (d, rr, h) {
            if (d >= rr + 0.5) return 0; const inner = rr * h; if (d <= inner) return 1; const t = (d - inner) / Math.max(1e-3, rr - inner); return Math.max(0, 1 - t * t * (3 - 2 * t));
        };
        const tool = o.tool, erase = !!o.erase, coats = S.coats, tgt = st.coat;
        const sv = S.sv, sc = S.sc, pv = S.pv, pc = S.pc, ctx = st.ctx;
        // [BRUSH-STUDIO 2026-10-10] per-coat role for this stroke: 2 = a target (grows), 1 = painted over (lowered), 0 = other plane (kept).
        // Legacy strokes: the one target grows, every other coat is lowered (unchanged behaviour). Studio strokes lower only coats of the
        // planes they paint (a Paint-only stroke keeps the spec coats under it); legacy coats are lowered only by a full Paint + Spec stroke.
        const roles = st.studio ? coats.map(function (c) {
            if (!erase && st.targets.indexOf(c) >= 0) return 2;
            if (c.plane) return st.planes[c.plane] ? 1 : 0;
            return st.planes.paint && st.planes.spec ? 1 : 0;
        }) : null;
        const lowSpec = !st.studio || st.planes.spec, lowPaint = !st.studio || st.planes.paint;
        const preset = o.preset, chan = preset ? (preset.chan || [1, 1, 1]) : null, flatSpec = preset && !(preset.grain > 0);
        const paintCol = o.paint;
        let touched = false;
        for (let py = y0; py < y1; py++) {
            const dy = py + 0.5 - cy;
            for (let px = x0; px < x1; px++) {
                const dx = px + 0.5 - cx, d2 = dx * dx + dy * dy;
                if (d2 >= (r + 0.5) * (r + 0.5)) continue;
                const v = fall(Math.sqrt(d2), r, hard);
                if (v <= 0) continue;
                const i = py * W + px, c = cov[i], nv = c + v * (1 - c);
                if (!(nv > c)) continue;
                cov[i] = nv;
                let a = nv * cap;
                if (clip) a *= clip[i] / 255;
                if (a <= 0) continue;
                const snap = tarr[(py >> TSH) * TX + (px >> TSH)];
                const li = ((py & (TS - 1)) << TSH) | (px & (TS - 1));
                touched = true;
                if (tool === 'material') {
                    if (roles) {
                        for (let k = 0; k < coats.length; k++) {
                            const rl = roles[k];
                            if (!rl) continue;
                            const cc = coats[k], om = snap.coat[cc.id] ? snap.coat[cc.id][li] : 0;
                            if (rl === 2) cc.mask[i] = Math.round(om + (255 - om) * a);
                            else if (om) cc.mask[i] = Math.round(om * (1 - a));
                        }
                    } else {
                        for (let k = 0; k < coats.length; k++) {
                            const cc = coats[k], om = snap.coat[cc.id] ? snap.coat[cc.id][li] : 0;
                            if (!erase && cc === tgt) cc.mask[i] = Math.round(om + (255 - om) * a);
                            else if (om) cc.mask[i] = Math.round(om * (1 - a));
                        }
                    }
                    if (!erase && sv && snap.sc) {
                        const l3 = li * 3, i3 = i * 3;
                        if (lowSpec) for (let ch = 0; ch < 3; ch++) { const oc = snap.sc[l3 + ch]; if (oc) sc[i3 + ch] = Math.round(oc * (1 - a)); }
                        if (lowPaint) { const op = snap.pc[li]; if (op) pc[i] = Math.round(op * (1 - a)); }
                    }
                    continue;
                }
                if (!sv || !snap.sc) continue;
                const l3 = li * 3, i3 = i * 3;
                if (erase) {
                    for (let ch = 0; ch < 3; ch++) { const oc = snap.sc[l3 + ch]; if (oc) sc[i3 + ch] = Math.round(oc * (1 - a)); }
                    const op = snap.pc[li]; if (op) pc[i] = Math.round(op * (1 - a));
                    continue;
                }
                if (tool === 'spec') {
                    let vm = preset.m, vr = preset.r, vc = preset.cc;
                    if (!flatSpec && ctx) { ctx.sampleSpec(preset, px, py, _spv); vm = _spv.m; vr = _spv.r; vc = _spv.cc; }
                    if (chan[0]) overCh(sv, sc, i3, snap.sv[l3], snap.sc[l3], vm, a);
                    if (chan[1]) overCh(sv, sc, i3 + 1, snap.sv[l3 + 1], snap.sc[l3 + 1], vr, a);
                    if (chan[2]) overCh(sv, sc, i3 + 2, snap.sv[l3 + 2], snap.sc[l3 + 2], vc, a);
                    if (paintCol) overPaint(pv, pc, i, snap.pv, snap.pc, li, paintCol[0], paintCol[1], paintCol[2], a);
                } else if (tool === 'wear' && ctx) {
                    ctx.sampleWear(o.wearType, px, py, a, _tex);
                    if (_tex.am > 0) overCh(sv, sc, i3, snap.sv[l3], snap.sc[l3], _tex.m, _tex.am);
                    if (_tex.ar > 0) overCh(sv, sc, i3 + 1, snap.sv[l3 + 1], snap.sc[l3 + 1], _tex.r, _tex.ar);
                    if (_tex.ac > 0) overCh(sv, sc, i3 + 2, snap.sv[l3 + 2], snap.sc[l3 + 2], _tex.cc, _tex.ac);
                    if (_tex.pa > 0) overPaint(pv, pc, i, snap.pv, snap.pc, li, _tex.pr, _tex.pg, _tex.pb, _tex.pa);
                }
            }
        }
        if (!touched) return null;
        st.changed = true;
        st.box = growBox(st.box, x0, y0, x1, y1);
        if (tool === 'material') {
            st.coatsTouched = true;
            if (st.studio) (st.targets || []).forEach(function (c) { c.box = growBox(c.box, x0, y0, x1, y1); });
            else if (tgt) tgt.box = growBox(tgt.box, x0, y0, x1, y1);
            if (sv) st.layersTouched = true;
        } else {
            st.layersTouched = true;
            if (!erase) {
                S.lb = growBox(S.lb, x0, y0, x1, y1);
                if (tool === 'wear' || paintCol) S.hasPaint = true;
                S.hasSpec = true;
            }
        }
        const rect = { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
        emit('dab', rect);
        return rect;
    }
    // value/coverage "over" for one channel, from the stroke's ORIGINAL (snapshot) bytes
    function overCh(vals, covs, idx, ov, oc8, V, a) {
        if (a >= 1) { covs[idx] = 255; vals[idx] = V < 0 ? 0 : (V > 255 ? 255 : Math.round(V)); return; }
        const oc = oc8 / 255, nc = oc + a * (1 - oc);
        if (nc <= 0) return;
        const nvv = (ov * oc * (1 - a) + V * a) / nc;
        covs[idx] = Math.round(nc * 255);
        vals[idx] = nvv < 0 ? 0 : (nvv > 255 ? 255 : Math.round(nvv));
    }
    function overPaint(pv, pc, i, spv, spc, li, r, g, b, a) {
        const oc = spc[li] / 255, nc = oc + a * (1 - oc);
        if (nc <= 0) return;
        const k0 = oc * (1 - a) / nc, k1 = a / nc, i3 = i * 3, l3 = li * 3;
        pc[i] = Math.round(nc * 255);
        pv[i3] = Math.max(0, Math.min(255, Math.round(spv[l3] * k0 + r * k1)));
        pv[i3 + 1] = Math.max(0, Math.min(255, Math.round(spv[l3 + 1] * k0 + g * k1)));
        pv[i3 + 2] = Math.max(0, Math.min(255, Math.round(spv[l3 + 2] * k0 + b * k1)));
    }

    function endStroke() {
        const st = S.st;
        if (!st) return null;
        if (!st.ctx && st.pend.length) {
            st.ctx = makeCtx(st, st.o.angle || 0);
            const q = st.pend; st.pend = [];
            q.forEach(function (d) { applyDab(st, d[0], d[1], d[2], d[3]); });
        }
        S.st = null;
        // clear the stroke coverage plane over the stroke box only
        if (st.box && S.cov) {
            const W = S.W;
            for (let y = st.box[1]; y < st.box[3]; y++) S.cov.fill(0, y * W + st.box[0], y * W + st.box[2]);
        }
        if (!st.changed) {
            asList(st.created).forEach(function (c) { const ix = S.coats.indexOf(c); if (ix >= 0) S.coats.splice(ix, 1); });
            emit('end', null);
            return null;
        }
        const TX = tilesX();
        const tiles = [];
        st.tiles.forEach(function (before, key) {
            const after = capture(key % TX, (key / TX) | 0);
            tiles.push([key, before, after]);
        });
        const entry = {
            label: labelFor(st.o), tiles: tiles, created: st.created,
            createdIndex: Array.isArray(st.created) ? st.created.map(function (c) { return S.coats.indexOf(c); }) : (st.created ? S.coats.indexOf(st.created) : -1),
            targets: st.studio ? (st.targets || []).map(function (c) { return c.id; }) : null,
            coats: st.coatsTouched, layers: st.layersTouched, box: st.box,
            hadSpec: S.hasSpec, hadPaint: S.hasPaint
        };
        S.undo.push(entry);
        let dropped = false;
        if (S.undo.length > UNDO_MAX) { S.undo.shift(); dropped = true; }
        S.redo.length = 0;
        try { if (typeof root._clearAllRedos === 'function') root._clearAllRedos(); } catch (_) {}
        try { if (dropped && typeof root._discardOldestUndoAction === 'function') root._discardOldestUndoAction(KIND); } catch (_) {}
        try { if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND); } catch (_) {}
        if (st.coatsTouched) S.coatVer++;
        if (st.layersTouched) S.layerVer++;
        emit('end', entry);
        changed();
        return entry;
    }
    // [SPECIAL-SPEC 2026-10-11] (owner bug) "a Special brush paints its own spec where it paints". Lays a Spec-only studio coat of
    // `finishId` over EXACTLY the pixels a layer stroke/fill painted: f = { finishId, params, x, y, w, h, wt: Float32Array(w*h) 0..1 }
    // (wt = the paint's own per-pixel weight: coverage x opacity x selection/zone clip x swatch alpha). One undo entry of kind 'rev-material'
    // (label "Special spec"). Same coat/mask/undo machinery as the Spec brush; the paint is never touched. Kill: window.SPB_SPECIAL_SPEC_OFF.
    function paintFootprint(f) {
        if (root.SPB_SPECIAL_SPEC_OFF || off() || bsOff() || !f || !f.finishId || !f.wt || !ensure()) return false;
        const o = { tool: 'material', studio: true, mode: 'spec', erase: false, keep: false, finishId: f.finishId, params: f.params || null, noClip: true, opacity: 1, hardness: 1, specialSpec: true };
        if (!beginStroke(o)) return false;
        const st = S.st, W = S.W, H = S.H;
        const x0 = Math.max(0, f.x | 0), y0 = Math.max(0, f.y | 0), x1 = Math.min(W, (f.x | 0) + f.w), y1 = Math.min(H, (f.y | 0) + f.h);
        if (x1 <= x0 || y1 <= y0) { cancelStroke(); return false; }
        snapTiles(st, x0, y0, x1, y1);
        const coats = S.coats, sc = S.sc, sv = S.sv, TX = tilesX(), tarr = st.tarr;
        const roles = coats.map(function (c) {
            if (st.targets.indexOf(c) >= 0) return 2;
            if (c.plane) return st.planes[c.plane] ? 1 : 0;
            return 0;
        });
        let touched = false;
        for (let py = y0; py < y1; py++) {
            for (let px = x0; px < x1; px++) {
                const a = f.wt[(py - (f.y | 0)) * f.w + (px - (f.x | 0))];
                if (!(a > 0)) continue;
                const i = py * W + px;
                const snap = tarr[(py >> TSH) * TX + (px >> TSH)];
                const li = ((py & (TS - 1)) << TSH) | (px & (TS - 1));
                touched = true;
                for (let k = 0; k < coats.length; k++) {
                    const rl = roles[k];
                    if (!rl) continue;
                    const cc = coats[k], om = snap.coat[cc.id] ? snap.coat[cc.id][li] : 0;
                    if (rl === 2) cc.mask[i] = Math.round(om + (255 - om) * a);
                    else if (om) cc.mask[i] = Math.round(om * (1 - a));
                }
                if (sv && snap.sc) {
                    const l3 = li * 3, i3 = i * 3;
                    for (let ch = 0; ch < 3; ch++) { const oc = snap.sc[l3 + ch]; if (oc) sc[i3 + ch] = Math.round(oc * (1 - a)); }
                }
            }
        }
        if (!touched) { cancelStroke(); return false; }
        st.changed = true; st.coatsTouched = true;
        st.box = growBox(st.box, x0, y0, x1, y1);
        (st.targets || []).forEach(function (c) { c.box = growBox(c.box, x0, y0, x1, y1); });
        if (sv) st.layersTouched = true;
        emit('dab', { x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
        return !!endStroke();
    }

    function cancelStroke() {
        const st = S.st;
        if (!st) return;
        S.st = null;
        const map = coatsById(st.created);
        st.tiles.forEach(function (before, key) { restoreTile(key, before, map); });
        if (st.box && S.cov) { const W = S.W; for (let y = st.box[1]; y < st.box[3]; y++) S.cov.fill(0, y * W + st.box[0], y * W + st.box[2]); }
        asList(st.created).forEach(function (c) { const ix = S.coats.indexOf(c); if (ix >= 0) S.coats.splice(ix, 1); });
        emit('redraw', null);
    }
    function asList(x) { return !x ? [] : (Array.isArray(x) ? x : [x]); }
    function labelFor(o) {
        if (o.specialSpec) return 'Special spec: ' + finishName(o.finishId);
        if (o.tool === 'material' && o.studio && !bsOff()) {
            const md = MODE_NAME[o.mode] || MODE_NAME.both;
            if (o.erase) return 'Brush Studio Erase (' + md + ')';
            const pl = paramsLabel(o.params);
            return 'Brush Studio: ' + finishName(o.finishId) + ' (' + md + (o.mode === 'spec' && o.keep ? ' + surface texture' : '') + (pl ? ', ' + pl : '') + ')';
        }
        if (o.tool === 'material') return o.erase ? 'Material Erase' : ('Material Brush: ' + finishName(o.finishId) + (o.keep ? ' (keep colour)' : ''));
        if (o.tool === 'spec') return o.erase ? 'Spec Erase' : ('Spec Brush: ' + ((o.preset && o.preset.name) || 'Custom'));
        if (o.tool === 'wear') {
            const w = root.SPBRevMatRecipes && root.SPBRevMatRecipes.WEAR.find(function (x) { return x.id === o.wearType; });
            return o.erase ? 'Wear Erase' : ('Wear Brush: ' + (w ? w.name : o.wearType));
        }
        return 'Material edit';
    }
    function coatsById(extra) {
        const m = {};
        S.coats.forEach(function (c) { m[c.id] = c; });
        asList(extra).forEach(function (c) { m[c.id] = c; });
        return m;
    }

    // ---------------------------------------------------------------- undo / redo
    function applyEntry(entry, useAfter) {
        if (S.st) cancelStroke();
        const map = coatsById(entry.created);
        if (useAfter && entry.created) {
            // [BRUSH-STUDIO 2026-10-10] a Paint + Spec stroke may create two coats: put each back at its recorded index (ascending)
            const cl = asList(entry.created), ix = Array.isArray(entry.createdIndex) ? entry.createdIndex : [entry.createdIndex];
            cl.forEach(function (c, k) {
                if (S.coats.indexOf(c) >= 0) return;
                const at = Math.max(0, Math.min(S.coats.length, ix[k] == null ? S.coats.length : ix[k]));
                S.coats.splice(at, 0, c);
            });
        }
        entry.tiles.forEach(function (t) { restoreTile(t[0], useAfter ? t[2] : t[1], map); });
        if (!useAfter && entry.created) asList(entry.created).forEach(function (c) { const ix = S.coats.indexOf(c); if (ix >= 0) S.coats.splice(ix, 1); });
        if (entry.coats || entry.created) S.coatVer++;
        if (entry.layers) S.layerVer++;
        emit('redraw', entry);
        changed();
    }
    function undo() { const e = S.undo.pop(); if (!e) return false; applyEntry(e, false); S.redo.push(e); return true; }
    function redo() { const e = S.redo.pop(); if (!e) return false; applyEntry(e, true); S.undo.push(e); return true; }
    root.SPBUndoExt.register(KIND, {
        hasUndo: function () { return S.undo.length > 0; },
        hasRedo: function () { return S.redo.length > 0; },
        undo: undo, redo: redo,
        clearRedo: function () { S.redo.length = 0; },
        label: function () { const e = S.undo[S.undo.length - 1]; return e ? e.label : 'Material edit'; }
    });

    // ---------------------------------------------------------------- payload (preview + RENDER)
    let changeTimer = null;
    function changed() {
        S.gen++; // any edit / undo / restore: lets the autosave module notice that live work happened
        if (changeTimer) clearTimeout(changeTimer);
        changeTimer = setTimeout(function () {
            changeTimer = null;
            try { encodeLayers(); } catch (e) { console.warn('[REV-MATERIAL] encode', e); }
            emit('changed');
            try { if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); } catch (_) {}
        }, 30);
    }
    function pngOf(w, h, fill) {
        const cv = doc.createElement('canvas');
        cv.width = w; cv.height = h;
        const ctx = cv.getContext('2d');
        const id = ctx.createImageData(w, h), d = id.data;
        fill(d);
        ctx.putImageData(id, 0, 0);
        return cv.toDataURL('image/png');
    }
    function encodeLayers() {
        if (S.enc.ver === S.layerVer) return S.enc;
        const enc = { ver: S.layerVer, spec: null, paint: null };
        if (S.sv && S.lb && (S.hasSpec || S.hasPaint)) {
            const W = S.W, b = S.lb, bw = b[2] - b[0], bh = b[3] - b[1];
            let anySpec = false, anyPaint = false;
            for (let y = b[1]; y < b[3] && !(anySpec && anyPaint); y++) {
                const s = y * W + b[0];
                for (let k = s * 3; k < (s + bw) * 3; k++) if (S.sc[k]) { anySpec = true; break; }
                for (let k = s; k < s + bw; k++) if (S.pc[k]) { anyPaint = true; break; }
            }
            const crop3 = function (src) {
                return function (d) {
                    for (let y = 0; y < bh; y++) {
                        let s = ((y + b[1]) * W + b[0]) * 3, o = y * bw * 4;
                        for (let x = 0; x < bw; x++, s += 3, o += 4) { d[o] = src[s]; d[o + 1] = src[s + 1]; d[o + 2] = src[s + 2]; d[o + 3] = 255; }
                    }
                };
            };
            const bbox = [b[0], b[1], bw, bh];
            if (anySpec) enc.spec = { bbox: bbox, val: pngOf(bw, bh, crop3(S.sv)), cov: pngOf(bw, bh, crop3(S.sc)) };
            if (anyPaint) {
                enc.paint = {
                    bbox: bbox, val: pngOf(bw, bh, crop3(S.pv)),
                    cov: pngOf(bw, bh, function (d) {
                        for (let y = 0; y < bh; y++) {
                            let s = (y + b[1]) * W + b[0], o = y * bw * 4;
                            for (let x = 0; x < bw; x++, s++, o += 4) { const v = S.pc[s]; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255; }
                        }
                    })
                };
            }
        }
        S.enc = enc;
        return enc;
    }
    function coatHasPixels(c) {
        if (!c.box) return false;
        const W = S.W, b = c.box, m = c.mask;
        for (let y = b[1]; y < b[3]; y++) { const s = y * W; for (let x = b[0]; x < b[2]; x++) if (m[s + x]) return true; }
        return false;
    }
    function coatObjs(orig) {
        if (S.coatEnc.ver === S.coatVer && S.coatEnc.objs) return S.coatEnc.objs;
        const live = S.coats.filter(coatHasPixels);
        let objs = [];
        if (live.length) {
            const zs = live.map(function (c) { c.zone.regionMask = c.mask; c.zone.useRegion = true; c.zone.hardEdge = true; c.zone.muted = false; return c.zone; });
            const made = orig(zs) || [];
            // Keep Colour travels beside the server zone (the serializer would drop an unknown zone field).
            // Pair by position when the serializer kept every zone, otherwise by the unique zone name.
            objs = made.map(function (zo, i) {
                const c = made.length === live.length ? live[i] : live.find(function (x) { return x.zone.name === zo.name; });
                const o = { zone: zo };
                if (c && c.keep) o.keep_colour = true;
                if (c && c.plane && !bsOff()) {
                    // [BRUSH-STUDIO 2026-10-10] additive fields: the engine's car-space path + what RENDER-CARD lists ("Far Out X brushed, scale 150%")
                    // a paint coat whose twin spec coat (same finish + sliders, not Keep Colour) is on the car came from Paint + Spec strokes
                    const md = studioMode(c, live), pl = paramsLabel(c.params);
                    o.anchor = 'car'; o.plane = c.plane;
                    o.bs = { finish_id: rawId(c.finishId), finish_name: c.name, mode: md, mode_name: MODE_NAME[md], params: normParams(c.params), surface_texture: !!c.keep,
                        label: c.name + ' brushed (' + MODE_NAME[md] + (c.keep ? ' + surface texture' : '') + (pl ? ', ' + pl : '') + ')' };
                }
                return o;
            });
        }
        S.coatEnc = { ver: S.coatVer, objs: objs };
        return objs;
    }
    /** The `_spb_rev_material` payload (null when nothing is painted). Exposed for tests. */
    function payload(orig) {
        if (off() || !S.W) return null;
        orig = orig || (root.buildServerZonesForRender && root.buildServerZonesForRender.__spbRevMatOrig);
        const coats = typeof orig === 'function' ? coatObjs(orig) : [];
        const enc = encodeLayers();
        if (!coats.length && !enc.spec && !enc.paint) return null;
        const lay = { v: 1, size: [S.W, S.H] };
        if (coats.length) lay.coats = coats;
        if (enc.spec) lay.spec = enc.spec;
        if (enc.paint) lay.paint = enc.paint;
        return lay;
    }
    // [PERF-4 2026-10-10] (lane PERF-4, item 2) The server zone a studio coat of (finish, params) sends, built exactly like coatObjs does (same serializer,
    // same flags) but with a one-pixel region. The server renders + memoises that finish on the FULL canvas from it (POST /api/perf4/warm-coat, see
    // js/spb-perf4-client.js), so the first stroke of a slow finish (candy 4.4 s, terrazzo 5.8 s, sequin 6.0 s) finds its coat render ready. Pure read: no state
    // is touched. Kill switch: window.SPB_PERF4_OFF (client) / env SPB_PERF4_OFF (server).
    function warmZone(finishId, params) {
        try {
            if (off() || bsOff() || !S.W || !finishId) return null;
            const orig = root.buildServerZonesForRender && root.buildServerZonesForRender.__spbRevMatOrig;
            if (typeof orig !== 'function') return null;
            const z = makeCoatZone(finishId, normParams(params));
            if (!z) return null;
            const m = new Uint8Array(S.W * S.H);
            m[(S.H >> 1) * S.W + (S.W >> 1)] = 255;
            z.regionMask = m; z.useRegion = true; z.hardEdge = true; z.muted = false; z.name = 'Brush Studio warm';
            const made = orig([z]) || [];
            return made[0] ? { zone: made[0], size: [S.W, S.H] } : null;
        } catch (e) { return null; }
    }
    function wrapSerializer() {
        const cur = root.buildServerZonesForRender;
        if (typeof cur !== 'function') return false;
        if (cur.__spbRevMatOrig) return true;
        const orig = cur;
        const wrapped = function (zs) {
            const out = orig.apply(this, arguments);
            try {
                if (off() || !Array.isArray(out) || !out.length || typeof zones === 'undefined' || zs !== zones) return out;
                const lay = payload(orig);
                if (lay) out[0]._spb_rev_material = lay;
            } catch (e) { console.warn('[REV-MATERIAL] payload skipped', e); }
            return out;
        };
        wrapped.__spbRevMatOrig = orig;
        root.buildServerZonesForRender = wrapped;
        return true;
    }

    // ---------------------------------------------------------------- persistence (project Save/Open + autosave)
    // [REV-MATERIAL-2 2026-10-10] serialize() -> ONE plain JSON-able object, restore(obj) puts it back.
    //   {v:1, size:[W,H], seq, coats:[{id, finishId, keep, name, bbox:[x,y,w,h], mask:PNG, zdiff}],
    //    spec:{bbox,val,cov}|null, paint:{bbox,val,cov}|null, lb:[x0,y0,x1,y1], hasSpec, hasPaint}
    //  - a coat is its finish id + the soft mask CROPPED to the tight box of its non-zero pixels (8-bit gray PNG,
    //    lossless); the zone is rebuilt through the app's own picker helpers, only fields that differ from a fresh
    //    coat zone are stored (zdiff). Spec / wear layers reuse the bbox-cropped PNG pairs the render payload
    //    already uses (encodeLayers), so a stroke costs a few KB, never a 2048x2048 buffer.
    //  - the document is NOT touched when anything fails to decode (all-or-nothing).
    //  - undo history starts fresh after a restore (the old entries point at buffers that no longer exist).
    function tightBox(mask, b) {
        const W = S.W;
        let x0 = b[2], y0 = b[3], x1 = b[0], y1 = b[1];
        for (let y = b[1]; y < b[3]; y++) {
            const s = y * W;
            for (let x = b[0]; x < b[2]; x++) if (mask[s + x]) { if (x < x0) x0 = x; if (x >= x1) x1 = x + 1; if (y < y0) y0 = y; if (y >= y1) y1 = y + 1; }
        }
        return x1 > x0 && y1 > y0 ? [x0, y0, x1, y1] : null;
    }
    function maskSig(mask, tb) {
        let h = 0x811c9dc5 >>> 0;
        const W = S.W;
        for (let y = tb[1]; y < tb[3]; y++) {
            const s = y * W;
            for (let x = tb[0]; x < tb[2]; x++) { const v = mask[s + x]; if (v) h = Math.imul(h ^ v ^ (x << 8), 16777619) >>> 0; }
            h = Math.imul(h ^ y, 16777619) >>> 0;
        }
        return tb.join(',') + ':' + h.toString(16);
    }
    function zoneDiff(c) {
        const fresh = makeCoatZone(c.finishId, c.plane ? c.params : undefined) || {}, d = {};
        Object.keys(c.zone).forEach(function (k) {
            if (k === 'regionMask' || k === 'name') return;
            const v = c.zone[k];
            if (v == null || ArrayBuffer.isView(v) || typeof v === 'function') return;
            try { if (JSON.stringify(v) !== JSON.stringify(fresh[k])) d[k] = JSON.parse(JSON.stringify(v)); } catch (_) {}
        });
        return d;
    }
    function encodeCoat(c) {
        if (!c.box) return null;
        const tb = tightBox(c.mask, c.box);
        if (!tb) return null;
        const sig = maskSig(c.mask, tb);
        if (c._enc && c._enc.sig === sig) return c._enc.out;
        const W = S.W, bw = tb[2] - tb[0], bh = tb[3] - tb[1], m = c.mask;
        const png = pngOf(bw, bh, function (d) {
            for (let y = 0; y < bh; y++) {
                let s = (y + tb[1]) * W + tb[0], o = y * bw * 4;
                for (let x = 0; x < bw; x++, s++, o += 4) { const v = m[s]; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255; }
            }
        });
        const out = { id: c.id, finishId: c.finishId, keep: !!c.keep, name: c.name, bbox: [tb[0], tb[1], bw, bh], mask: png, zdiff: zoneDiff(c) };
        if (c.plane) { out.plane = c.plane; out.params = normParams(c.params); }   // [BRUSH-STUDIO 2026-10-10] additive (older readers ignore it)
        c._enc = { sig: sig, out: out };
        return out;
    }
    /** The whole brushed state as one JSON-able object, or null when nothing is painted. */
    function serialize() {
        if (off() || !S.W) return null;
        const out = { v: 1, size: [S.W, S.H], seq: S.seq, coats: [], spec: null, paint: null, lb: S.lb ? S.lb.slice() : null, hasSpec: !!S.hasSpec, hasPaint: !!S.hasPaint };
        S.coats.forEach(function (c) { const e = encodeCoat(c); if (e) out.coats.push(e); });
        const enc = encodeLayers();
        out.spec = enc.spec; out.paint = enc.paint;
        if (!out.coats.length && !out.spec && !out.paint) return null;
        return out;
    }
    function isEmpty() { return !S.coats.some(coatHasPixels) && !(S.sc && S.lb && (S.hasSpec || S.hasPaint) && layersHavePixels()); }
    function layersHavePixels() {
        const W = S.W, b = S.lb;
        if (!b || !S.sc) return false;
        for (let y = b[1]; y < b[3]; y++) { const s = y * W + b[0]; for (let k = s * 3; k < (y * W + b[2]) * 3; k++) if (S.sc[k]) return true; for (let k = s; k < y * W + b[2]; k++) if (S.pc[k]) return true; }
        return false;
    }
    function dataUrlBlob(u) {
        const i = u.indexOf(','), bin = atob(u.slice(i + 1)), a = new Uint8Array(bin.length);
        for (let k = 0; k < bin.length; k++) a[k] = bin.charCodeAt(k);
        return new Blob([a], { type: 'image/png' });
    }
    // PNG data URL -> {w,h,data RGBA} without colour management or premultiplication (exact bytes back)
    function decodePng(u) {
        return createImageBitmap(dataUrlBlob(u), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' }).then(function (bmp) {
            const cv = doc.createElement('canvas'); cv.width = bmp.width; cv.height = bmp.height;
            const cx = cv.getContext('2d', { willReadFrequently: true });
            cx.drawImage(bmp, 0, 0);
            const r = { w: bmp.width, h: bmp.height, data: cx.getImageData(0, 0, bmp.width, bmp.height).data };
            if (bmp.close) bmp.close();
            return r;
        });
    }
    /** Put a serialize() object back. obj == null empties the brushed state (a document that has none).
     *  Resolves {ok, why?, coats, spec, paint}. Never throws. */
    function restore(obj) {
        try {
            if (off()) return Promise.resolve({ ok: false, why: 'off' });
            const d = canvasDims();
            if (!d[0] || !d[1]) return Promise.resolve({ ok: false, why: 'no canvas' });
            if (!obj) {
                if (S.W && (S.coats.length || S.sv || S.undo.length || S.redo.length)) { reset(d[0], d[1]); changed(); }
                return Promise.resolve({ ok: true, coats: 0, spec: false, paint: false });
            }
            if (!obj.size || obj.size[0] !== d[0] || obj.size[1] !== d[1]) return Promise.resolve({ ok: false, why: 'size' });
            if (obj.coats && obj.coats.length && !zoneTemplate()) return Promise.resolve({ ok: false, why: 'zones not ready' });
            const jobs = [];
            const want = function (u) { const p = decodePng(u); jobs.push(p); return p; };
            const cp = (obj.coats || []).map(function (c) { return want(c.mask); });
            const sv = obj.spec ? [want(obj.spec.val), want(obj.spec.cov)] : null;
            const pv = obj.paint ? [want(obj.paint.val), want(obj.paint.cov)] : null;
            return Promise.all(jobs).then(function (all) {
                const W = d[0], H = d[1];
                reset(W, H);
                S.seq = Math.max(S.seq, obj.seq | 0);
                (obj.coats || []).forEach(function (ce, k) {
                    const studio = (ce.plane === 'paint' || ce.plane === 'spec');
                    const img = all[k], z = makeCoatZone(ce.finishId, studio ? normParams(ce.params) : undefined);
                    if (!z) return;
                    Object.assign(z, ce.zdiff || {});
                    const mask = new Uint8Array(W * H), bx = ce.bbox[0], by = ce.bbox[1];
                    let x0 = W, y0 = H, x1 = 0, y1 = 0;
                    for (let y = 0; y < img.h && by + y < H; y++) for (let x = 0; x < img.w && bx + x < W; x++) {
                        const v = img.data[(y * img.w + x) * 4];
                        if (v) { mask[(by + y) * W + bx + x] = v; if (bx + x < x0) x0 = bx + x; if (bx + x >= x1) x1 = bx + x + 1; if (by + y < y0) y0 = by + y; if (by + y >= y1) y1 = by + y + 1; }
                    }
                    const c = { id: ce.id || ('rmc' + (++S.seq)), finishId: ce.finishId, keep: !!ce.keep, name: ce.name || finishName(ce.finishId), mask: mask, zone: z, box: x1 > x0 ? [x0, y0, x1, y1] : null };
                    if (studio) { c.plane = ce.plane; c.params = normParams(ce.params); c.psig = psig(c.params); }
                    z.name = coatZoneName(c);
                    z.regionMask = mask;
                    S.coats.push(c);
                });
                let at = (obj.coats || []).length;
                if (obj.spec || obj.paint) {
                    ensureLayers();
                    const put3 = function (dst, img, bb) {
                        for (let y = 0; y < img.h && bb[1] + y < H; y++) for (let x = 0; x < img.w && bb[0] + x < W; x++) {
                            const s = (y * img.w + x) * 4, o = ((bb[1] + y) * W + bb[0] + x) * 3;
                            dst[o] = img.data[s]; dst[o + 1] = img.data[s + 1]; dst[o + 2] = img.data[s + 2];
                        }
                    };
                    const put1 = function (dst, img, bb) {
                        for (let y = 0; y < img.h && bb[1] + y < H; y++) for (let x = 0; x < img.w && bb[0] + x < W; x++) dst[(bb[1] + y) * W + bb[0] + x] = img.data[(y * img.w + x) * 4];
                    };
                    if (obj.spec) { put3(S.sv, all[at], obj.spec.bbox); put3(S.sc, all[at + 1], obj.spec.bbox); at += 2; }
                    if (obj.paint) { put3(S.pv, all[at], obj.paint.bbox); put1(S.pc, all[at + 1], obj.paint.bbox); at += 2; }
                    S.lb = obj.lb ? obj.lb.slice() : null;
                    S.hasSpec = !!obj.spec; S.hasPaint = !!obj.paint;
                }
                S.coatVer++; S.layerVer++; S.enc = { ver: -1 }; S.coatEnc = { ver: -1, objs: null };
                emit('redraw', null);
                changed();
                return { ok: true, coats: S.coats.length, spec: !!obj.spec, paint: !!obj.paint };
            }).catch(function (e) { console.warn('[REV-MATERIAL] restore failed', e); return { ok: false, why: String(e && e.message || e) }; });
        } catch (e) {
            console.warn('[REV-MATERIAL] restore failed', e);
            return Promise.resolve({ ok: false, why: String(e && e.message || e) });
        }
    }

    // ---------------------------------------------------------------- readouts
    function sampleAt(x, y) {
        if (!S.W || x < 0 || y < 0 || x >= S.W || y >= S.H) return null;
        const i = y * S.W + x, out = { coats: [], spec: null, paint: null };
        S.coats.forEach(function (c) { if (c.mask[i]) out.coats.push({ id: c.id, finishId: c.finishId, keep: !!c.keep, name: c.name, a: c.mask[i], plane: c.plane || null, params: c.plane ? normParams(c.params) : null }); });
        if (S.sv) {
            out.spec = { m: S.sv[i * 3], r: S.sv[i * 3 + 1], cc: S.sv[i * 3 + 2], cm: S.sc[i * 3], cr: S.sc[i * 3 + 1], ccc: S.sc[i * 3 + 2] };
            out.paint = { r: S.pv[i * 3], g: S.pv[i * 3 + 1], b: S.pv[i * 3 + 2], a: S.pc[i] };
        }
        return out;
    }
    function stats() {
        return {
            W: S.W, H: S.H, coats: S.coats.map(function (c) { return { id: c.id, finishId: c.finishId, keep: !!c.keep, name: c.name, box: c.box, plane: c.plane || null, params: c.plane ? normParams(c.params) : null }; }),
            hasSpec: S.hasSpec, hasPaint: S.hasPaint, lb: S.lb, undo: S.undo.length, redo: S.redo.length,
            coatVer: S.coatVer, layerVer: S.layerVer
        };
    }
    /** FNV-1a over every NON-ZERO byte and its index, per buffer (exact undo proof; an allocated
     *  all-zero buffer hashes the same as a buffer that was never allocated). */
    function crc() {
        let h = 0x811c9dc5 >>> 0;
        function eat(a, tag) {
            h = Math.imul(h ^ tag, 16777619) >>> 0;
            if (!a) return;
            for (let i = 0; i < a.length; i++) {
                const v = a[i];
                if (!v) continue;
                h = Math.imul(h ^ v, 16777619) >>> 0;
                h = Math.imul(h ^ (i & 0xffff), 16777619) >>> 0;
                h = Math.imul(h ^ (i >>> 16), 16777619) >>> 0;
            }
        }
        S.coats.forEach(function (c, k) { eat(c.mask, 100 + k); });
        eat(S.sv, 1); eat(S.sc, 2); eat(S.pv, 3); eat(S.pc, 4);
        return (h >>> 0).toString(16) + ':' + S.coats.length;
    }
    function clearAll() {
        if (!S.W) return false;
        // one undoable stroke-like entry covering every painted tile
        const st = { tiles: new Map(), tarr: [] };
        const boxes = S.coats.map(function (c) { return c.box; }).concat([S.lb]).filter(Boolean);
        if (!boxes.length) return false;
        boxes.forEach(function (b) { snapTiles(st, b[0], b[1], b[2], b[3]); });
        S.coats.forEach(function (c) { if (c.box) for (let y = c.box[1]; y < c.box[3]; y++) c.mask.fill(0, y * S.W + c.box[0], y * S.W + c.box[2]); });
        if (S.sc && S.lb) for (let y = S.lb[1]; y < S.lb[3]; y++) { S.sc.fill(0, (y * S.W + S.lb[0]) * 3, (y * S.W + S.lb[2]) * 3); S.pc.fill(0, y * S.W + S.lb[0], y * S.W + S.lb[2]); }
        const TX = tilesX(), tiles = [];
        st.tiles.forEach(function (before, key) { tiles.push([key, before, capture(key % TX, (key / TX) | 0)]); });
        S.undo.push({ label: 'Clear Material Layers', tiles: tiles, created: null, createdIndex: -1, coats: true, layers: true });
        S.redo.length = 0;
        try { if (typeof root._clearAllRedos === 'function') root._clearAllRedos(); } catch (_) {}
        try { if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND); } catch (_) {}
        S.coatVer++; S.layerVer++;
        emit('redraw', null);
        changed();
        return true;
    }

    function init() {
        if (off()) return;
        wrapSerializer();
        // the serializer may be (re)defined by a later script: re-check a few times
        let tries = 0;
        const t = setInterval(function () { wrapSerializer(); if (++tries > 20) clearInterval(t); }, 500);
    }

    root.SPBRevMaterial = {
        KIND: KIND, off: off, state: S, ensure: ensure, beginStroke: beginStroke, dab: dab, endStroke: endStroke, cancelStroke: cancelStroke, paintFootprint: paintFootprint,
        undo: undo, redo: redo, payload: payload, encodeLayers: encodeLayers, sampleAt: sampleAt, stats: stats, crc: crc,
        clearAll: clearAll, clipInfo: clipInfo, clipMask: clipMask, finishName: finishName, coatFor: coatFor,
        on: function (f) { S.listeners.push(f); }, changed: changed, wrapSerializer: wrapSerializer,
        serialize: serialize, restore: restore, isEmpty: isEmpty, reset: reset, canvasDims: canvasDims,
        makeCoatZone: makeCoatZone,   // [SPB-REV-FADE 2026-10-10] additive export: a Car-Space Fade finish stop builds its zone exactly like a brushed coat (js/rev/fade/fade-ui.js)
        // [BRUSH-STUDIO 2026-10-10] additive exports (UI + proofs)
        bsOff: bsOff, normParams: normParams, applyParams: applyParams, paramsLabel: paramsLabel, psig: psig, isDefaultParams: isDefaultParams, MODE_NAME: MODE_NAME, studioMode: studioMode,
        warmZone: warmZone   // [PERF-4 2026-10-10] additive export
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
