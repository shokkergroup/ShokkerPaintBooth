/* [SPB-REV-SYM 2026-10-10] REV-SYMMETRY tools - Mirror Paint, Mirror To Other Side, Car Stripe.
 *
 * Built on SpbRevSym (sym-core.js), the per-car registration between the mirrored parts of the paint sheet
 * (left side <-> right side, and each centre island - hood, roof, trunk, bumpers - onto its own other half).
 *
 *  - MIRROR PAINT (toggle in the options bar, Symmetry menu): while on, every Brush / Eraser / Color Brush / Recolor /
 *    Dodge / Burn / Blur / Sharpen / History Brush dab is replayed at the registered mirror point, clipped to the target
 *    part (centre islands: to the other half) AND to the selection / zone clip exactly like the original dab.
 *    Smudge / Clone / Heal are not mirrored (they carry pixels picked up along their own path).
 *    Both sides land inside the same stroke, so the app's one-stroke undo covers both.
 *    Hooks: the app's global dab functions are wrapped from here (no edit to paint-booth-3-canvas.js); the mirrored dab's
 *    clip is injected through _activeSelectionMask, which every dab already reads.
 *  - MIRROR TO OTHER SIDE: copies the selected layer's content (or just the selection) through the registration - fitted
 *    to the other side's shape, not a flat flip - onto the matching part, as one undo step. "Text Reads Right" keeps
 *    numbers and lettering readable (position mirrored, the graphic itself turned instead of mirrored).
 *  - CAR STRIPE: a stripe on the car's centre line, measured on every island through its own mirror map, so it is
 *    centred on hood, roof, trunk and bumpers and meets itself at every seam. Width / offset / twin / gap / colour,
 *    live preview, added as a new "Car Stripe" layer (one undo step).
 *
 * KILL SWITCH: window.SPB_REV_SYM_OFF = true or localStorage SPB_REV_SYM_OFF = '1' -> the hooks pass straight through and
 * no Symmetry UI is shown.
 */
(function (root) {
    'use strict';
    const doc = root.document;
    if (!doc) return;
    const VER = 'symtools1.0';
    const sym = () => root.SpbRevSym || null;
    function off() { const s = sym(); if (!s) return true; try { return s.off(); } catch (e) { return true; } }
    function mode() { try { return (typeof canvasMode !== 'undefined') ? canvasMode : root.canvasMode; } catch (e) { return root.canvasMode; } }
    function layerMode() { try { return typeof root.isLayerToolbarMode === 'function' ? !!root.isLayerToolbarMode() : true; } catch (e) { return true; } }
    function psdLayers() { try { return (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers; } catch (e) { return root._psdLayers; } }
    function selectedLayerId() { try { return (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : root._selectedLayerId; } catch (e) { return root._selectedLayerId; } }
    function fg() { try { return (typeof _foregroundColor !== 'undefined') ? _foregroundColor : (root._foregroundColor || '#ffffff'); } catch (e) { return '#ffffff'; } }
    function toast(msg, kind) { try { if (typeof root.showToast === 'function') root.showToast(msg, kind); } catch (e) {} }
    function call(name) { try { const f = root[name]; if (typeof f === 'function') return f.apply(root, Array.prototype.slice.call(arguments, 1)); } catch (e) { warn(name, e); } return undefined; }
    let warned = 0;
    function warn(where, e) { if (warned++ < 5 && root.console) root.console.warn('[REV-SYM] ' + where, e); }

    // tools whose dabs are replayed on the other side (smudge / clone / heal carry their own path's pixels: not mirrored)
    const MODES = { brush: 1, erase: 1, colorbrush: 1, recolor: 1, dodge: 1, burn: 1, 'blur-brush': 1, 'sharpen-brush': 1, 'history-brush': 1 };
    const S = { on: false, inMirror: false, clip: null, clipKey: '', sig: '', key: '', building: false, stats: { mirrored: 0, skipped: 0, errors: 0 } };
    let COMBO = new WeakMap();       // base selection mask -> { clipKey -> combined mask } (reset every stroke)
    const LAT = new Map();           // part -> lateral field of a centre island (signed px from its centre line)
    const HALF = new Map();          // part|sign -> half mask of a centre island
    const BOX = new Map();           // clip key -> bbox

    function ready() { const s = sym(); try { return !!(s && !off() && s.ready()); } catch (e) { return false; } }
    // [SPB-REV-SYM2 2026-10-10] the Material tools (Material / Spec / Wear Brush, canvas modes rev-material / rev-spec / rev-wear) honour Mirror Paint too:
    // they replay each dab through materialDab() (called from ONE line in the Material core's applyDab). The Brush / Eraser / Retouch wrappers stay as they were.
    const MAT_MODES = { 'rev-material': 1, 'rev-spec': 1, 'rev-wear': 1 };
    function supportedPaint() { return MODES[mode()] === 1 && layerMode(); }
    function supportedMat() { return MAT_MODES[mode()] === 1; }
    function supported() { return supportedPaint() || supportedMat(); }            // the toggle / hint / ghost follow this
    function active() { return S.on && !S.inMirror && supportedPaint() && ready() && usable(); }
    function activeMat() { return S.on && !S.inMirror && supportedMat() && ready() && usable(); }
    // [SPB-REV-SYM2 2026-10-10] a car with nothing Symmetry can trust to mirror (no template found / sides could not be lined up without a Wire layer):
    // strokes are NOT mirrored, and the first stroke on each car says why (once), so paint is never placed silently wrong or silently left out.
    function fitMode(C) { return (C && C.reg && C.reg.mode) || 'wire'; }
    function usable() {
        const C = sym() && sym().cur(); if (!C || fitMode(C) !== 'none') return true;
        if (S.warnedNone !== C.key) { S.warnedNone = C.key; toast(noneMsg(C), 'warn'); }
        return false;
    }
    function hasTemplate() { try { const L = psdLayers(); return Array.isArray(L) && templateIndex(L) < L.length; } catch (e) { return false; } }
    function noneMsg(C) {
        const sk = (C.reg.skipped || []).map(x => x.part).filter((v, i, a) => a.indexOf(v) === i);
        return sk.length ? 'Mirror Paint could not line up this car’s ' + sk.join(', ') + ' without the Wire layer of its template, so strokes are not mirrored. Open the car’s PSD template (with its Wire layer) for an exact fit.'
            : (hasTemplate() ? 'Mirror Paint could not find this car’s left and right sides: the panels of its template are not recognised, so strokes are not mirrored. Only the side you paint changes.'
                : 'Mirror Paint needs this car’s template (its Mask and Wire layers). This file has none and the car is not in the library, so the left and right sides can’t be told apart. Strokes are not mirrored: only the side you paint changes.');
    }
    function fitNote(C) { // '' for a normal fit
        const md = fitMode(C), pl = (C.reg.plain || []).filter((v, i, a) => a.indexOf(v) === i), sk = (C.reg.skipped || []).map(x => x.part).filter((v, i, a) => a.indexOf(v) === i);
        if (md === 'outline') return ' No Wire layer in this file: the sides are lined up by their outline.';
        if (md === 'plain') return ' No Wire layer, and the outline fit is uncertain on the ' + pl.join(', ') + ': a plain flip is used there, so copies can sit up to about 20 px off the matching spot. The car’s template gives an exact fit.';
        if (md === 'partial') return ' Not mirrored: ' + sk.join(', ') + ' (no Wire layer to line them up).' + (pl.length ? ' Plain flip on: ' + pl.join(', ') + '.' : '');
        return '';
    }
    function hintTexts(C) {
        const md = fitMode(C);
        if (md === 'none') return ['Mirror Paint: no car template, strokes are not mirrored', 'Not mirrored: no template'];
        if (md === 'plain') return ['Mirror Paint on: plain flip (no Wire layer), copies can sit ~20 px off', 'Plain flip: no Wire layer'];
        if (md === 'partial') return ['Mirror Paint on: some parts not mirrored (no Wire layer)', 'Some parts not mirrored'];
        if (md === 'outline') return ['Mirror Paint on: strokes repeat on the matching part (outline fit)', 'Mirror Paint on (outline fit)'];
        return ['Mirror Paint on: strokes repeat on the matching part', 'Mirror Paint on'];
    }

    // ---------------------------------------------------------------- registration (built once per car, cached by the core)
    function wireId() { const L = psdLayers() || []; const w = L.find(l => l && /(^|\s)(wire|wireframe)(\s|$)/i.test(String(l.name || '').trim())); return w ? w.id : '-'; }
    function quickSig() {
        let sig = '';
        try { sig += String((root.SpbProCar && root.SpbProCar.layoutSig && root.SpbProCar.layoutSig()) || ''); } catch (e) {}
        try { sig += '|' + wireId(); } catch (e) {}
        const pc = doc.getElementById('paintCanvas'); if (pc) sig += '|' + pc.width + 'x' + pc.height;
        return sig;
    }
    function ensureBuilt(force) {
        const s = sym(); if (!s || off()) return Promise.resolve(null);
        const sig = quickSig();
        if (!force && s.ready() && sig === S.sig && s.cur()) return Promise.resolve(s.cur());
        S.building = true; refreshUi();
        return new Promise(res => setTimeout(res, 30)).then(() => s.build(!!force)).then(C => {
            S.building = false; S.sig = sig;
            if (C && C.key !== S.key) { S.key = C.key; LAT.clear(); HALF.clear(); BOX.clear(); COMBO = new WeakMap(); }
            refreshUi(); if (C && S.on) warm();
            return C;
        }, e => { S.building = false; refreshUi(); warn('build', e); toast('Could not read this car’s shape for Symmetry.', 'error'); return null; });
    }

    // ---------------------------------------------------------------- geometry helpers
    function axisOf(mp) { // unit normal of a centre island's mirror line = null vector of (A + I) of its reflection
        if (mp._n) return mp._n;
        const A = mp.M.A, a = A[0] + 1, b = A[1], c = A[3], d = A[4] + 1;
        let x = -b, y = a; const x2 = d, y2 = -c;
        if (x2 * x2 + y2 * y2 > x * x + y * y) { x = x2; y = y2; }
        const n = Math.hypot(x, y) || 1;
        mp._n = [x / n, y / n]; return mp._n;
    }
    function boxOf(key, mask) {
        let b = BOX.get(key); if (b) return b;
        const C = sym().cur(); b = sym()._internal.bboxOf(mask, C.W, C.H); BOX.set(key, b); return b;
    }
    // signed lateral distance (px) from a centre island's mirror line, for every pixel of its main panel
    function latField(part) {
        const s = sym(), C = s && s.cur(); if (!C) return null;
        let f = LAT.get(part); if (f) return f;
        const mp = C.maps[part + '>' + part], m = C.masks[part]; if (!mp || !mp.M || !m) return null;
        const bb = boxOf(part, m), n = axisOf(mp), w = bb.x1 - bb.x0 + 1, h = bb.y1 - bb.y0 + 1, W = C.W;
        const L = new Float32Array(w * h).fill(NaN);
        for (let y = bb.y0; y <= bb.y1; y++) for (let x = bb.x0; x <= bb.x1; x++) {
            if (!m[y * W + x]) continue;
            const q = s.mapPt(mp.M, x, y);
            L[(y - bb.y0) * w + (x - bb.x0)] = ((x - q[0]) * n[0] + (y - q[1]) * n[1]) / 2;
        }
        f = { part, bb, w, h, L, n }; LAT.set(part, f); return f;
    }
    function halfMask(part, sign) { // pixels of the island on one side of its centre line (+ a half-pixel overlap so the halves meet)
        const k = part + '|' + sign; let h = HALF.get(k); if (h) return h;
        const C = sym().cur(), f = latField(part); if (!f) return null;
        h = new Uint8Array(C.W * C.H);
        for (let j = 0; j < f.h; j++) for (let i = 0; i < f.w; i++) { const v = f.L[j * f.w + i]; if (v === v && v * sign > -0.5) h[(j + f.bb.y0) * C.W + i + f.bb.x0] = 255; }
        if (HALF.size >= 6) HALF.delete(HALF.keys().next().value);
        HALF.set(k, h); return h;
    }
    // where a sheet point lands on the other side; clip = the target part (centre islands: the other half)
    function mirrorPoint(x, y, needClip) {
        const s = sym(), C = s && s.cur(); if (!C) return null;
        const part = s.partAt(x, y); if (!part) return null;
        const mp = s.mirrorOf(part); if (!mp || !mp.M) return null;
        const q = s.mapPt(mp.M, x, y);
        if (!(q[0] >= 0 && q[1] >= 0 && q[0] <= C.W - 1 && q[1] <= C.H - 1)) return null;
        let clip = null, key = mp.to;
        if (mp.self) {
            const n = axisOf(mp), d = (x - q[0]) * n[0] + (y - q[1]) * n[1];
            if (Math.abs(d) < 1) return null; // on the centre line the dab is its own mirror
            key = mp.to + '|' + (d > 0 ? -1 : 1);
            if (needClip) clip = halfMask(mp.to, d > 0 ? -1 : 1);
        } else if (needClip) clip = C.masks[mp.to];
        if (needClip && !clip) return null;
        const J = s.jac(mp.M, x, y), sc = Math.sqrt(Math.abs(J[0] * J[3] - J[1] * J[2])) || 1;
        return { x: q[0], y: q[1], part, to: mp.to, self: !!mp.self, clip, key, scale: Math.max(0.5, Math.min(2, sc)) };
    }
    function combine(base, clip, key) { // base selection / zone clip x target part, computed once per stroke
        if (!base) return clip;
        if (base.length !== clip.length) return base;
        let m = COMBO.get(base); if (!m) { m = new Map(); COMBO.set(base, m); }
        let out = m.get(key); if (out) return out;
        const C = sym().cur(), W = C.W, b = boxOf(key, clip);
        out = new Uint8Array(clip.length);
        if (b) for (let y = b.y0; y <= b.y1; y++) {
            let i = y * W + b.x0;
            for (let x = b.x0; x <= b.x1; x++, i++) { const c = clip[i]; if (!c) continue; const v = base[i]; out[i] = c === 255 ? v : ((v * c + 127) / 255) | 0; }
        }
        m.set(key, out); return out;
    }

    // ---------------------------------------------------------------- MIRROR PAINT: hooks on the app's dab functions
    function wrapSelection() {
        const orig = root._activeSelectionMask;
        if (typeof orig !== 'function') return false;
        if (orig.__spbSym) return true;
        const w = function (wd, ht) {
            const base = orig.apply(this, arguments);
            if (!S.inMirror || !S.clip || wd * ht !== S.clip.length) return base;
            return combine(base, S.clip, S.clipKey);
        };
        w.__spbSym = true; w.__orig = orig; root._activeSelectionMask = w; return true;
    }
    function mirrored(m, fn) {
        S.inMirror = true; S.clip = m.clip; S.clipKey = m.key;
        try { fn(); S.stats.mirrored++; } catch (e) { S.stats.errors++; warn('mirrored dab', e); }
        finally { S.inMirror = false; S.clip = null; S.clipKey = ''; }
    }
    function wrapDab(name, kind) {
        const orig = root[name];
        if (typeof orig !== 'function') return false;
        if (orig.__spbSym) return true;
        let w;
        if (kind === 'layer') { // _paintOnLayerAt(x, y, radius, color, opacity, hardness, eraseMode, pcOpts) - Brush / Eraser on a layer
            w = function (x, y, radius, color, opacity, hardness, eraseMode, pcOpts) {
                const r = orig.apply(this, arguments);
                if (!active()) return r;
                const sx = pcOpts && Number.isFinite(pcOpts.fx) ? pcOpts.fx : x, sy = pcOpts && Number.isFinite(pcOpts.fy) ? pcOpts.fy : y;
                const m = mirrorPoint(sx, sy, true); if (!m) { S.stats.skipped++; return r; }
                const o2 = pcOpts ? Object.assign({}, pcOpts, { fx: m.x, fy: m.y }) : pcOpts;
                mirrored(m, () => orig.call(this, Math.round(m.x), Math.round(m.y), radius * m.scale, color, opacity, hardness, eraseMode, o2));
                return r;
            };
        } else if (kind === 'sym') { // _applyWithSymmetry(paintFn, x, y) - Recolor / Dodge / Burn / Blur / Sharpen
            w = function (paintFn, x, y) {
                const r = orig.apply(this, arguments);
                if (!active() || typeof paintFn !== 'function') return r;
                const m = mirrorPoint(x, y, true); if (!m) { S.stats.skipped++; return r; }
                mirrored(m, () => paintFn(Math.round(m.x), Math.round(m.y)));
                return r;
            };
        } else { // paintColorBrush(x, y) / paintHistoryBrush(x, y)
            w = function (x, y) {
                const r = orig.apply(this, arguments);
                if (!active()) return r;
                const m = mirrorPoint(x, y, true); if (!m) { S.stats.skipped++; return r; }
                mirrored(m, () => orig.call(this, Math.round(m.x), Math.round(m.y)));
                return r;
            };
        }
        w.__spbSym = true; w.__orig = orig; root[name] = w; return true;
    }
    function warm() { // lateral fields of the centre islands in idle slices, so the first dab on a hood has no hitch
        const C = sym() && sym().cur(); if (!C) return;
        const todo = (C.reg.selfs || []).map(s => s.part).filter(p => !LAT.has(p));
        const step = () => { const p = todo.shift(); if (!p) return; try { latField(p); } catch (e) {} idle(step); };
        idle(step);
    }
    function idle(fn) { if (root.requestIdleCallback) root.requestIdleCallback(fn, { timeout: 800 }); else setTimeout(fn, 60); }

    function setOn(v) {
        if (off()) { S.on = false; refreshUi(); return false; }
        S.on = !!v;
        if (S.on) {
            if (!ready() || quickSig() !== S.sig) {
                toast('Mirror Paint: measuring this car’s sides (once per car)…', 'info');
                ensureBuilt(false).then(C => { if (C && S.on) toast(onMsg(C)); });
            } else { toast(onMsg(sym().cur())); warm(); }
            if (!supported()) toast('Mirror Paint is on. Pick the Brush, Eraser, a Retouch brush or a Material brush to paint both sides.', 'info');
        }
        refreshUi(); return S.on;
    }
    function onMsg(C) {
        const pr = (C.reg.pairs || []).length, sf = (C.reg.selfs || []).map(s => s.part);
        if (!pr && !sf.length) return noneMsg(C);
        return 'Mirror Paint on: ' + (pr ? 'left side ↔ right side' : '') + (sf.length ? (pr ? ', and ' : '') + 'both halves of the ' + sf.join(', ') : '') + '. Ctrl+Z undoes both.' + fitNote(C);
    }

    // ---------------------------------------------------------------- MIRROR PAINT for the MATERIAL tools
    // [SPB-REV-SYM2 2026-10-10] Public API (other tools may use it):
    //   SpbRevSymTools.mirrorDab(x, y, radius, baseClip) -> { x, y, radius, clip, part, to, self, scale } | null
    //     x, y: sheet pixel-index coordinates, like the dab's own. radius comes back scaled by the local stretch of the car-aware map.
    //     clip: baseClip x the target part (the other half for a centre island), a Uint8Array 0..255 the size of the sheet.
    //     null when Mirror Paint is off, no Material brush is active, or the dab is not on a registered part.
    //   SpbRevSymTools.mirrorDir(x, y, angle) -> the stroke direction (radians) as it reads on the other side.
    //   SpbRevSymTools.materialDab(st, x, y, radius, hardness, apply) -> replays one dab through apply(st, x', y', r', hardness) with the clip
    //     swapped in (and the grain / flow direction mirrored for the Wear Brush and grained Spec presets). The Material core calls it
    //     from one line at the top of applyDab(), guarded by st.symBusy. Same stroke -> same undo step; the zone clip applies on both sides.
    function mirrorDab(x, y, radius, baseClip) {
        if (!S.on || S.inMirror || !ready() || !usable()) return null;
        const m = mirrorPoint(x, y, true); if (!m) return null;
        return { x: m.x, y: m.y, radius: Math.max(0.5, (+radius || 1) * m.scale), clip: combine(baseClip || null, m.clip, m.key), part: m.part, to: m.to, self: m.self, scale: m.scale };
    }
    function mirrorDir(x, y, angle) {
        const s = sym(), C = s && s.cur(); if (!C) return angle;
        const part = s.partAt(x, y); if (!part) return angle;
        const mp = s.mirrorOf(part); if (!mp || !mp.M) return angle;
        const J = s.jac(mp.M, x, y), c = Math.cos(angle), n = Math.sin(angle);
        return Math.atan2(J[2] * c + J[3] * n, J[0] * c + J[1] * n);
    }
    function wantsDir(o) { return !!o && (o.tool === 'wear' || (o.tool === 'spec' && !o.erase && o.preset && o.preset.grain > 0)); }
    function materialDab(st, x, y, radius, hard, apply) {
        if (!st || st.symBusy || typeof apply !== 'function' || !activeMat()) return;
        const m = mirrorDab(x, y, radius, st.clip); if (!m) { S.stats.skipped++; return; }
        const keepClip = st.clip, keepCtx = st.ctx, keepAngle = st.angle;
        st.symBusy = true; S.inMirror = true;
        try {
            st.clip = m.clip;
            if (st.ctx && wantsDir(st.o) && root.SPBRevMatRecipes) { // grain / flow direction as it reads on the mirrored side (10 degree steps, one context each)
                const q = Math.round(mirrorDir(x, y, st.angle || 0) * 18 / Math.PI), cache = st.symCtx || (st.symCtx = {});
                st.ctx = cache[q] || (cache[q] = root.SPBRevMatRecipes.makeContext(q * Math.PI / 18, st.seed));
            }
            apply(st, m.x, m.y, m.radius, hard); S.stats.mirrored++;
        } catch (e) { S.stats.errors++; warn('material dab', e); }
        finally { st.clip = keepClip; st.ctx = keepCtx; st.angle = keepAngle; st.symBusy = false; S.inMirror = false; }
    }
    function watchMaterial() { // a changed car is re-measured when a Material stroke starts (the Material tools stop the pointer events our Brush check listens to)
        const M = root.SPBRevMaterial; if (!M || typeof M.on !== 'function' || watchMaterial.done) return;
        watchMaterial.done = true;
        M.on((what) => { if (what === 'begin' && S.on && !S.building && !off() && supportedMat() && quickSig() !== S.sig) ensureBuilt(false); });
    }

    // ---------------------------------------------------------------- MIRROR TO OTHER SIDE (layer content / selection)
    function layerPixels(layer, W, H) {
        const c = doc.createElement('canvas'); c.width = W; c.height = H;
        const x = c.getContext('2d', { willReadFrequently: true }); const bb = layer.bbox || [0, 0];
        x.drawImage(layer.img, bb[0] || 0, bb[1] || 0);
        return x.getImageData(0, 0, W, H);
    }
    function selectionRaw(W, H) { const m = call('_activeSelectionMaskRaw', W, H); return (m && m.length === W * H) ? m : null; }
    function sample(d, W, H, sx, sy, out) { // bilinear, premultiplied
        const x0 = Math.floor(sx), y0 = Math.floor(sy), fx = sx - x0, fy = sy - y0;
        let r = 0, g = 0, b = 0, a = 0;
        for (let k = 0; k < 4; k++) {
            const xx = x0 + (k & 1), yy = y0 + (k >> 1);
            if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
            const w = ((k & 1) ? fx : 1 - fx) * ((k >> 1) ? fy : 1 - fy); if (w <= 0) continue;
            const o = (yy * W + xx) * 4, al = d[o + 3] * w; if (!al) continue;
            r += d[o] * al; g += d[o + 1] * al; b += d[o + 2] * al; a += al;
        }
        if (a > 0) { out[0] = r / a; out[1] = g / a; out[2] = b / a; }
        out[3] = a;
    }
    function over(od, i, c, a) { // source-over, a in 0..255
        if (a <= 0.5) return;
        const o = i * 4, sa = a / 255, da = od[o + 3] / 255, oa = sa + da * (1 - sa);
        if (oa <= 0) return;
        const k = da * (1 - sa);
        od[o] = (c[0] * sa + od[o] * k) / oa; od[o + 1] = (c[1] * sa + od[o + 1] * k) / oa; od[o + 2] = (c[2] * sa + od[o + 2] * k) / oa; od[o + 3] = oa * 255;
    }
    function frontOf(part) { try { const b = root.SpbProCar.map().boxes[part]; return b && b.front || null; } catch (e) { return null; } }
    // graphics = groups of content cells (8 px) joined across gaps < ~48 px; a selection is always ONE graphic
    function groupsOf(d, W, H, wt, box, single) {
        const cell = 8, gw = Math.ceil(W / cell), gh = Math.ceil(H / cell), occ = new Uint8Array(gw * gh), lab = new Int32Array(gw * gh);
        for (let y = box.y0; y <= box.y1; y++) for (let x = box.x0; x <= box.x1; x++) {
            const i = y * W + x; if (d[i * 4 + 3] * wt(i) >= 8) occ[((y / cell) | 0) * gw + ((x / cell) | 0)] = 1;
        }
        let n = 0;
        if (single) { for (let k = 0; k < occ.length; k++) if (occ[k]) lab[k] = 1; n = 1; }
        else {
            const R = 3, dil = new Uint8Array(gw * gh), dl = new Int32Array(gw * gh), st = [];
            for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) if (occ[j * gw + i])
                for (let b = Math.max(0, j - R); b <= Math.min(gh - 1, j + R); b++) for (let a = Math.max(0, i - R); a <= Math.min(gw - 1, i + R); a++) dil[b * gw + a] = 1;
            for (let k = 0; k < dil.length; k++) {
                if (!dil[k] || dl[k]) continue;
                n++; dl[k] = n; st.push(k);
                while (st.length) {
                    const p = st.pop(), px = p % gw, py = (p / gw) | 0;
                    const nb = [px > 0 ? p - 1 : -1, px < gw - 1 ? p + 1 : -1, py > 0 ? p - gw : -1, py < gh - 1 ? p + gw : -1];
                    for (const q of nb) if (q >= 0 && dil[q] && !dl[q]) { dl[q] = n; st.push(q); }
                }
            }
            for (let k = 0; k < occ.length; k++) if (occ[k]) lab[k] = dl[k];
        }
        const G = {};
        for (let y = box.y0; y <= box.y1; y++) for (let x = box.x0; x <= box.x1; x++) {
            const l = lab[((y / cell) | 0) * gw + ((x / cell) | 0)]; if (!l) continue;
            const i = y * W + x, a = d[i * 4 + 3] * wt(i); if (a <= 0) continue;
            const g = G[l] || (G[l] = { id: l, sx: 0, sy: 0, sa: 0, x0: 1e9, y0: 1e9, x1: -1, y1: -1 });
            g.sx += x * a; g.sy += y * a; g.sa += a;
            if (x < g.x0) g.x0 = x; if (x > g.x1) g.x1 = x; if (y < g.y0) g.y0 = y; if (y > g.y1) g.y1 = y;
        }
        const groups = Object.keys(G).map(k => G[k]).filter(g => g.sa > 255 * 4).map(g => ({ id: g.id, cs: [g.sx / g.sa, g.sy / g.sa], x0: g.x0, y0: g.y0, x1: g.x1, y1: g.y1 }));
        return { lab, cell, gw, groups };
    }
    // appearance of a readable copy: J (mirror, det < 0) times a flip -> a turn, so lettering is not mirrored.
    //   side panels: flip the along-car axis (keeps the car's "up": on the upside-down stored right panel that is a 180 turn);
    //   centre islands: flip across the island's own centre line (the copy is the same graphic, moved).
    function readableL(J, job, mp) {
        let F;
        if (job.self) { const n = axisOf(mp); F = [1 - 2 * n[0] * n[0], -2 * n[0] * n[1], -2 * n[0] * n[1], 1 - 2 * n[1] * n[1]]; }
        else { const fr = frontOf(job.from); F = (fr === 'top' || fr === 'bottom') ? [1, 0, 0, -1] : [-1, 0, 0, 1]; }
        return [J[0] * F[0] + J[1] * F[2], J[0] * F[1] + J[1] * F[3], J[2] * F[0] + J[3] * F[2], J[2] * F[1] + J[3] * F[3]];
    }
    function inv2(L) { const dt = L[0] * L[3] - L[1] * L[2] || 1e-9; return [L[3] / dt, -L[1] / dt, -L[2] / dt, L[0] / dt]; }

    function mirrorLayer(readable) {
        if (off()) return Promise.resolve(false);
        const layer = call('getSelectedEditableLayer');
        if (!layer || !layer.img) { toast('Pick an unlocked layer first (Layers panel), then Mirror To Other Side.', 'warn'); return Promise.resolve(false); }
        return ensureBuilt(false).then(C => {
            if (!C) return false;
            if (fitMode(C) === 'none') { toast(noneMsg(C), 'warn'); return false; }
            const s = sym(), W = C.W, H = C.H, t0 = performance.now();
            const src = layerPixels(layer, W, H), d = src.data, sel = selectionRaw(W, H);
            // which side holds the design: content weight per registered part
            const wt = {}; C.names.forEach(n => { wt[n] = 0; });
            const pm = C.partMap;
            for (let i = 0, N = W * H; i < N; i++) { const a = d[i * 4 + 3]; if (!a) continue; const p = pm[i]; if (!p) continue; wt[C.names[p - 1]] += sel ? a * sel[i] / 255 : a; }
            const MIN = 255 * 30, jobs = [];
            (C.reg.pairs || []).forEach(p => { const wa = wt[p.a] || 0, wb = wt[p.b] || 0; if (Math.max(wa, wb) >= MIN) jobs.push(wa >= wb ? { from: p.a, to: p.b } : { from: p.b, to: p.a }); });
            (C.reg.selfs || []).forEach(sf => {
                if ((wt[sf.part] || 0) < MIN) return;
                const f = latField(sf.part); if (!f) return;
                let wp = 0, wn = 0; // which half holds more of the design
                for (let j = 0; j < f.h; j++) for (let i = 0; i < f.w; i++) {
                    const v = f.L[j * f.w + i]; if (v !== v) continue; const k = (j + f.bb.y0) * W + i + f.bb.x0, a = d[k * 4 + 3]; if (!a) continue;
                    const aw = sel ? a * sel[k] / 255 : a; if (v > 0) wp += aw; else wn += aw;
                }
                jobs.push({ from: sf.part, to: sf.part, self: true, srcSign: wp >= wn ? 1 : -1 });
            });
            if (!jobs.length) { toast(sel ? 'Nothing selected on a side panel, hood, roof, trunk or bumper of this layer.' : 'This layer has nothing on a side panel, hood, roof, trunk or bumper to mirror.', 'warn'); return false; }
            const out = new ImageData(new Uint8ClampedArray(d), W, H), od = out.data, c = [0, 0, 0, 0];
            const done = [];
            jobs.forEach(job => {
                const mf = job.self ? C.maps[job.from + '>' + job.from] : C.maps[job.from + '>' + job.to];
                const mb = job.self ? mf : C.maps[job.to + '>' + job.from];
                if (!mf || !mb) return;
                const srcMask = job.self ? halfMask(job.from, job.srcSign) : C.masks[job.from];
                const tgt = job.self ? halfMask(job.to, -job.srcSign) : C.masks[job.to];
                if (!srcMask || !tgt) return;
                const wtf = i => srcMask[i] ? (sel ? sel[i] / 255 : 1) : 0;
                const tb = boxOf(job.self ? job.to + '|' + (-job.srcSign) : job.to, tgt);
                if (!tb) return;
                let painted = 0;
                if (!readable) {
                    for (let y = tb.y0; y <= tb.y1; y++) for (let x = tb.x0; x <= tb.x1; x++) {
                        const i = y * W + x; if (!tgt[i]) continue;
                        const q = s.mapPt(mb.M, x, y), si = Math.round(q[1]) * W + Math.round(q[0]);
                        if (q[0] < 0 || q[1] < 0 || q[0] > W - 1 || q[1] > H - 1) continue;
                        const w = wtf(si); if (!w) continue;
                        sample(d, W, H, q[0], q[1], c); if (c[3] <= 0) continue;
                        over(od, i, c, c[3] * w * tgt[i] / 255); painted++;
                    }
                } else {
                    const sb = boxOf(job.self ? job.from + '|' + job.srcSign : job.from, srcMask);
                    if (!sb) return;
                    const gr = groupsOf(d, W, H, wtf, sb, !!sel);
                    gr.groups.forEach(g => {
                        const cs = g.cs, ct = s.mapPt(mf.M, cs[0], cs[1]), L = readableL(s.jac(mf.M, cs[0], cs[1]), job, mf), Li = inv2(L);
                        let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
                        [[g.x0, g.y0], [g.x1, g.y0], [g.x0, g.y1], [g.x1, g.y1]].forEach(p => {
                            const dx = p[0] - cs[0], dy = p[1] - cs[1], X = ct[0] + L[0] * dx + L[1] * dy, Y = ct[1] + L[2] * dx + L[3] * dy;
                            x0 = Math.min(x0, X); y0 = Math.min(y0, Y); x1 = Math.max(x1, X); y1 = Math.max(y1, Y);
                        });
                        x0 = Math.max(tb.x0, Math.floor(x0) - 2); y0 = Math.max(tb.y0, Math.floor(y0) - 2); x1 = Math.min(tb.x1, Math.ceil(x1) + 2); y1 = Math.min(tb.y1, Math.ceil(y1) + 2);
                        for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
                            const i = y * W + x; if (!tgt[i]) continue;
                            const dx = x - ct[0], dy = y - ct[1], sx = cs[0] + Li[0] * dx + Li[1] * dy, sy = cs[1] + Li[2] * dx + Li[3] * dy;
                            if (sx < 0 || sy < 0 || sx > W - 1 || sy > H - 1) continue;
                            const rx = Math.round(sx), ry = Math.round(sy);
                            if (gr.lab[((ry / gr.cell) | 0) * gr.gw + ((rx / gr.cell) | 0)] !== g.id) continue;
                            const w = wtf(ry * W + rx); if (!w) continue;
                            sample(d, W, H, sx, sy, c); if (c[3] <= 0) continue;
                            over(od, i, c, c[3] * w * tgt[i] / 255); painted++;
                        }
                    });
                }
                if (painted) done.push(job.self ? 'the other half of the ' + job.to : job.to);
            });
            if (!done.length) { toast('Nothing landed on the other side (the design sits outside the matching parts).', 'warn'); return false; }
            const cand = doc.createElement('canvas'); cand.width = W; cand.height = H; cand.getContext('2d').putImageData(out, 0, 0);
            const ok = call('_commitDestructiveLayerTransform', layer, cand, [0, 0, W, H], readable ? 'copy to other side' : 'mirror to other side',
                (readable ? 'Copied (text reads right) to ' : 'Mirrored to ') + done.join(', ') + '. Ctrl+Z undoes it.' + fitNote(C));
            S.lastMirror = { jobs: jobs.map(j => j.from + '>' + j.to), done, ms: Math.round(performance.now() - t0), readable: !!readable, selection: !!sel };
            return !!ok;
        });
    }

    // ---------------------------------------------------------------- CAR STRIPE
    const STRIPE = { width: 60, offset: 0, twin: false, gap: 24, color: null, bumpers: true };
    const CHAIN = ['front bumper', 'hood', 'roof', 'trunk', 'bed', 'tailgate', 'rear bumper'];
    function chain(C) {
        const have = (C.reg.selfs || []).map(s => s.part);
        return CHAIN.filter(n => have.indexOf(n) >= 0 && (STRIPE.bumpers || !/bumper/.test(n)));
    }
    // which way is the car's left on an island's lateral axis: +1 when the island's + end sits relatively closer to the left
    // side panel (top islands: panel centres; bumpers: the panels' front / rear ends). A centred or twin stripe never
    // depends on this; it only decides which way a non-zero Offset goes, consistently on every island.
    function leftSign(C, part, f) {
        let boxes = null; try { boxes = root.SpbProCar.map().boxes; } catch (e) {}
        const Lb = boxes && boxes['left side'], Rb = boxes && boxes['right side'];
        if (!Lb || !Rb) return 1;
        const W = C.W, H = C.H;
        const end = (b, rear) => {
            const x0 = b.bbox[0] * W, x1 = b.bbox[2] * W, y0 = b.bbox[1] * H, y1 = b.bbox[3] * H, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
            let fr = b.front;
            if (rear) fr = { left: 'right', right: 'left', top: 'bottom', bottom: 'top' }[fr] || null;
            return fr === 'left' ? [x0, cy] : fr === 'right' ? [x1, cy] : fr === 'top' ? [cx, y0] : fr === 'bottom' ? [cx, y1] : [cx, cy];
        };
        let rl, rr;
        if (/front bumper/.test(part)) { rl = end(Lb, false); rr = end(Rb, false); }
        else if (/rear bumper|tailgate/.test(part)) { rl = end(Lb, true); rr = end(Rb, true); }
        else { rl = [(Lb.bbox[0] + Lb.bbox[2]) / 2 * W, (Lb.bbox[1] + Lb.bbox[3]) / 2 * H]; rr = [(Rb.bbox[0] + Rb.bbox[2]) / 2 * W, (Rb.bbox[1] + Rb.bbox[3]) / 2 * H]; }
        const bb = f.bb, n = f.n, c = [(bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2];
        const half = Math.abs(n[0]) * (bb.x1 - bb.x0) / 2 + Math.abs(n[1]) * (bb.y1 - bb.y0) / 2;
        const pp = [c[0] + n[0] * half, c[1] + n[1] * half], pn = [c[0] - n[0] * half, c[1] - n[1] * half];
        const dd = (p) => Math.hypot(p[0] - rl[0], p[1] - rl[1]) - Math.hypot(p[0] - rr[0], p[1] - rr[1]);
        return dd(pp) <= dd(pn) ? 1 : -1;
    }
    function hexRgb(h) { h = String(h || '#ffffff'); return [parseInt(h.slice(1, 3), 16) || 0, parseInt(h.slice(3, 5), 16) || 0, parseInt(h.slice(5, 7), 16) || 0]; }
    function stripeCentres() {
        const hw = Math.max(1, +STRIPE.width || 1) / 2, off0 = +STRIPE.offset || 0, gap = Math.max(0, +STRIPE.gap || 0);
        return { hw, cs: STRIPE.twin ? [off0 - (gap / 2 + hw), off0 + (gap / 2 + hw)] : [off0] };
    }
    function stripeData(C) {
        const W = C.W, H = C.H, img = new ImageData(W, H), d = img.data, col = hexRgb(STRIPE.color || fg()), st = stripeCentres(), islands = [];
        chain(C).forEach(part => {
            const f = latField(part); if (!f) return;
            const sg = leftSign(C, part, f);
            let n = 0;
            for (let j = 0; j < f.h; j++) for (let i = 0; i < f.w; i++) {
                const v = f.L[j * f.w + i]; if (v !== v) continue;
                const l = v * sg; let cov = 0;
                for (let k = 0; k < st.cs.length; k++) { const q = st.hw + 0.5 - Math.abs(l - st.cs[k]); if (q > cov) cov = q; }
                if (cov <= 0) continue;
                const a = Math.round(Math.min(1, cov) * 255), o = ((j + f.bb.y0) * W + i + f.bb.x0) * 4;
                if (a > d[o + 3]) { d[o] = col[0]; d[o + 1] = col[1]; d[o + 2] = col[2]; d[o + 3] = a; }
                n++;
            }
            if (n) islands.push({ part, px: n, sign: sg });
        });
        return { img, islands };
    }
    let panel = null, overlay = null, ovRaf = 0, ro = null;
    function ensureOverlay() {
        const pc = doc.getElementById('paintCanvas'); if (!pc || !pc.parentNode) return null;
        if (!overlay) { overlay = doc.createElement('canvas'); overlay.id = 'spbSymOverlay'; overlay.className = 'spb-sym-overlay'; overlay.setAttribute('aria-hidden', 'true'); }
        if (overlay.parentNode !== pc.parentNode) pc.parentNode.insertBefore(overlay, pc.nextSibling);
        if (!ro && root.ResizeObserver) { ro = new ResizeObserver(syncOverlay); ro.observe(pc); }
        syncOverlay(); return overlay;
    }
    function syncOverlay() {
        const pc = doc.getElementById('paintCanvas'); if (!overlay || !pc) return;
        if (overlay.width !== pc.width) overlay.width = pc.width;
        if (overlay.height !== pc.height) overlay.height = pc.height;
        overlay.style.left = pc.offsetLeft + 'px'; overlay.style.top = pc.offsetTop + 'px';
        overlay.style.width = pc.offsetWidth + 'px'; overlay.style.height = pc.offsetHeight + 'px';
    }
    function drawStripe() {
        ovRaf = 0;
        const C = sym() && sym().cur(); if (!C || !panel || panel.style.display === 'none') return;
        const ov = ensureOverlay(); if (!ov) return;
        const r = stripeData(C);
        ov.style.display = ''; ov.getContext('2d').putImageData(r.img, 0, 0);
        const note = panel.querySelector('.spb-sym-note');
        if (note) note.textContent = r.islands.length ? 'Centred on: ' + r.islands.map(i => i.part).join(', ') : 'No hood, roof or trunk found on this car map.';
    }
    function queueStripe() { if (!ovRaf) ovRaf = root.requestAnimationFrame(drawStripe); }
    function buildPanel() {
        if (panel && panel.isConnected) return panel;
        panel = doc.createElement('div'); panel.id = 'spbSymStripe'; panel.className = 'spb-sym-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Car Stripe');
        panel.innerHTML =
            '<div class="spb-sym-ph"><span class="spb-sym-pt">' + svg('stripe') + 'Car Stripe</span><button type="button" class="spb-sym-x" data-k="cancel" title="Close without adding (Esc)" aria-label="Close">' + svg('x', 12) + '</button></div>' +
            '<div class="spb-sym-row"><label for="spbSymSW">Width</label><input id="spbSymSW" type="number" data-k="width" min="2" max="600" step="2"><span>px</span></div>' +
            '<div class="spb-sym-row"><label for="spbSymSO">Offset</label><input id="spbSymSO" type="number" data-k="offset" min="-600" max="600" step="2"><span>px</span></div>' +
            '<div class="spb-sym-row"><label for="spbSymST">Twin</label><input id="spbSymST" type="checkbox" data-k="twin"><label for="spbSymSG" class="spb-sym-sub">Gap</label><input id="spbSymSG" type="number" data-k="gap" min="0" max="600" step="2"><span>px</span></div>' +
            '<div class="spb-sym-row"><label for="spbSymSC">Colour</label><input id="spbSymSC" type="color" data-k="color"><label for="spbSymSB" class="spb-sym-sub">Bumpers</label><input id="spbSymSB" type="checkbox" data-k="bumpers"></div>' +
            '<div class="spb-sym-note"></div>' +
            '<div class="spb-sym-pb"><button type="button" data-k="cancel">Cancel</button><button type="button" data-k="apply" class="spb-sym-primary">Add Stripe</button></div>';
        doc.body.appendChild(panel);
        panel.addEventListener('input', e => {
            const k = e.target && e.target.getAttribute('data-k'); if (!k) return;
            STRIPE[k] = e.target.type === 'checkbox' ? e.target.checked : (e.target.type === 'number' ? +e.target.value : e.target.value);
            queueStripe();
        });
        panel.addEventListener('change', e => { const k = e.target && e.target.getAttribute('data-k'); if (k) { STRIPE[k] = e.target.type === 'checkbox' ? e.target.checked : (e.target.type === 'number' ? +e.target.value : e.target.value); queueStripe(); } });
        panel.addEventListener('click', e => {
            const b = e.target.closest && e.target.closest('button[data-k]'); if (!b) return;
            e.preventDefault();
            if (b.getAttribute('data-k') === 'apply') applyStripe(); else closeStripe();
        });
        return panel;
    }
    function fillPanel() {
        panel.querySelectorAll('[data-k]').forEach(i => {
            const k = i.getAttribute('data-k'); if (i.tagName !== 'INPUT') return;
            if (i.type === 'checkbox') i.checked = !!STRIPE[k]; else i.value = STRIPE[k];
        });
    }
    function placePanel() {
        const a = (menu && menu.isConnected && menu.getBoundingClientRect()) || { left: 80, bottom: 120 };
        const w = panel.offsetWidth || 260, vw = root.innerWidth || 1200;
        panel.style.left = Math.max(8, Math.min(vw - w - 8, a.left)) + 'px';
        panel.style.top = Math.round(a.bottom + 6) + 'px';
    }
    function openStripe() {
        if (off()) return Promise.resolve(false);
        return ensureBuilt(false).then(C => {
            if (!C) return false;
            if (!(C.reg.selfs || []).some(s => CHAIN.indexOf(s.part) >= 0)) { toast(fitMode(C) === 'none' ? noneMsg(C) : 'This car map has no hood, roof or trunk to lay a stripe on.', 'warn'); return false; }
            if (!STRIPE.color) STRIPE.color = fg();
            buildPanel(); fillPanel(); panel.style.display = ''; placePanel(); drawStripe();
            const w = panel.querySelector('#spbSymSW'); if (w) try { w.focus({ preventScroll: true }); } catch (e) {}
            return true;
        });
    }
    function closeStripe() {
        if (panel) panel.style.display = 'none';
        if (overlay) { overlay.style.display = 'none'; try { overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height); } catch (e) {} }
    }
    function templateIndex(L) {
        for (let i = 0; i < L.length; i++) {
            const l = L[i]; if (!l) continue;
            if (/^\s*(wire|wireframe|mask|car mandatory)\s*$/i.test(String(l.name || '')) || /turn\s*off\s*before\s*export/i.test(String(l.groupName || ''))) return i;
        }
        return L.length;
    }
    // [SPB-REV-SYM2 2026-10-10] A stripe is LIVERY PAINT: numbers, sponsors and logos are stamped ON TOP of paint (SPB doctrine), so the
    // stripe layer goes UNDER the car's decal / element layers: just below the lowest numbers / sponsors / logos layer, above the body
    // paint below it (the layer stack lists the bottom layer first). Roles come from the car map's own layer classifier
    // (SpbProCar.roleOf), with a name check as a fallback. Without any element layer: above the selected layer, below the template.
    const ELEMENT_ROLES = /^(numbers|sponsors|decals \/ logos)$/;
    function layerRole(l) {
        let r = ''; try { if (root.SpbProCar && root.SpbProCar.roleOf) r = String(root.SpbProCar.roleOf(l) || ''); } catch (e) {}
        if (r && r !== 'other art') return r;
        const n = String(l.name || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
        if (/number/.test(n)) return 'numbers'; if (/sponsor/.test(n)) return 'sponsors';
        if (/logo|decal|banner|pitbox|windshield|sticker|badge/.test(n)) return 'decals / logos';
        if (/(^| )(base|body|livery|paint)( |$)|car paint|base (coat|layer|colou?r)/.test(n)) return 'body paint';
        return r || 'other art';
    }
    function stripeInsertIndex(L, selId) {
        const tpl = templateIndex(L); let elem = -1;
        for (let i = 0; i < tpl; i++) { const l = L[i]; if (l && l.img && ELEMENT_ROLES.test(layerRole(l))) { elem = i; break; } }
        const sel = L.findIndex(l => l && l.id === selId);
        if (elem < 0) return sel >= 0 ? Math.min(sel + 1, tpl) : tpl;                 // nothing to stay under: the old rule
        let body = -1; for (let i = 0; i < elem; i++) { const l = L[i]; if (l && l.img && layerRole(l) === 'body paint') body = i; }
        // a layer the buyer picked between the body paint and the first decal layer is respected; everything else lands just under the decals
        if (sel > body && sel < elem) return sel + 1;
        return elem;
    }
    function applyStripe() {
        const C = sym() && sym().cur(); if (!C || off()) return false;
        const r = stripeData(C); if (!r.islands.length) { toast(fitMode(C) === 'none' ? noneMsg(C) : 'No hood, roof or trunk found for the stripe.', 'warn'); return false; }
        const L = psdLayers(); if (!Array.isArray(L)) { toast('Open a car paint first.', 'warn'); return false; }
        const W = C.W, H = C.H, cv = doc.createElement('canvas'); cv.width = W; cv.height = H; cv.getContext('2d').putImageData(r.img, 0, 0);
        call('_pushLayerStackUndo', 'car stripe');
        const layer = { id: 'symstripe_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6), name: 'Car Stripe', path: '', visible: true, opacity: 255, blendMode: 'source-over',
            locked: false, alphaLock: false, clippingMask: false, effects: null, bbox: [0, 0, W, H], img: cv };
        const at = stripeInsertIndex(L, selectedLayerId());                   // UNDER the numbers / sponsors / logos (see stripeInsertIndex)
        // join the group of the body paint right below it, so the Layers panel keeps that group in one piece
        const nb = L[at - 1], tplL = templateIndex(L), gsrc = (nb && at - 1 < tplL && nb.groupName) ? nb : ((L[at] && at < tplL && L[at].groupName) ? L[at] : null);
        if (gsrc) { layer.groupName = gsrc.groupName || ''; layer.groupChain = Array.isArray(gsrc.groupChain) ? JSON.parse(JSON.stringify(gsrc.groupChain)) : []; layer.parentGroupKey = gsrc.parentGroupKey || null; }
        L.splice(at, 0, layer);
        try { if (typeof _psdLayersLoaded !== 'undefined') _psdLayersLoaded = true; } catch (e) {} // eslint-disable-line no-undef
        call('selectPSDLayer', layer.id); call('invalidateLayerVisibleContributionCache'); call('recompositeFromLayers'); call('renderLayerPanel'); call('triggerPreviewRender');
        closeStripe();
        S.lastStripe = { layerId: layer.id, islands: r.islands, opts: Object.assign({}, STRIPE), index: at };
        toast('Car Stripe added on the ' + r.islands.map(i => i.part).join(', ') + '. Ctrl+Z removes it.');
        return true;
    }
    doc.addEventListener('keydown', e => { if (e.key === 'Escape' && panel && panel.style.display !== 'none') { e.preventDefault(); closeStripe(); } }, true);

    // ---------------------------------------------------------------- UI: options-bar toggle, tool-band hint, Symmetry menu, ghost ring
    const ICON = {
        mirror: '<path d="m3 7 5 5-5 5V7"/><path d="m21 7-5 5 5 5V7"/><path d="M12 20v2"/><path d="M12 14v2"/><path d="M12 8v2"/><path d="M12 2v2"/>',
        copy: '<path d="M8 19H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h3"/><path d="M16 5h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-3"/><path d="M12 4v16"/>',
        text: '<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>',
        stripe: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M10 3v18"/><path d="M14 3v18"/>',
        scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M12 7v10"/>',
        x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
    };
    function svg(k, sz) { return '<svg class="spb-sym-svg" viewBox="0 0 24 24" width="' + (sz || 14) + '" height="' + (sz || 14) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[k] + '</svg>'; }
    let toggle = null, hint = null, menu = null, ghost = null;
    function ensureToggle() {
        const tso = doc.getElementById('toolSpecificOptions'); if (!tso || !tso.parentNode) return false;
        if (!toggle) {
            toggle = doc.createElement('button'); toggle.type = 'button'; toggle.id = 'spbSymToggle'; toggle.className = 'spb-sym-toggle';
            toggle.setAttribute('aria-pressed', 'false');
            toggle.title = 'Mirror Paint: every stroke also lands on the matching part of the car - left side ↔ right side, and the other half of the hood, roof, trunk and bumpers. Ctrl+Z undoes both sides.';
            toggle.innerHTML = svg('mirror') + '<span>Mirror Paint</span>';
            toggle.addEventListener('click', e => { e.preventDefault(); setOn(!S.on); });
        }
        if (toggle.parentNode !== tso.parentNode || toggle.nextSibling !== tso) tso.parentNode.insertBefore(toggle, tso);
        return true;
    }
    function ensureHint() {
        const band = doc.getElementById('spbToolRowTop'); if (!band) return false;
        if (!hint) { hint = doc.createElement('span'); hint.id = 'spbSymHint'; hint.className = 'spb-sym-hint'; hint.setAttribute('aria-live', 'polite'); }
        if (hint.parentNode !== band) band.appendChild(hint);
        return true;
    }
    function item(id, ic, label, title) {
        return '<button type="button" class="vtool-btn" data-sym="' + id + '" title="' + title + '"' + (id === 'paint' ? ' aria-pressed="false"' : '') + '><span class="spb-mi-ico spb-sym-ico">' + svg(ic) + '</span> ' + label + '</button>';
    }
    function ensureMenu() {
        if (menu && menu.isConnected) return true;
        const anchor = doc.getElementById('spbRevMatMenu') || doc.getElementById('spbRetouchMenu');
        if (!anchor || !anchor.parentNode) return false;
        menu = doc.createElement('details'); menu.className = 'spb-tb-menu'; menu.id = 'spbSymMenu';
        menu.innerHTML = '<summary class="spb-tb-summary" title="Symmetry: paint both sides of the car at once, copy a design to the other side, lay a stripe down the middle">Symmetry <span class="spb-tb-caret">▾</span></summary>' +
            '<div class="spb-tb-pop">' +
            item('paint', 'mirror', 'Mirror Paint', 'Brush, Eraser and Retouch strokes also land on the matching part: left side ↔ right side, and the other half of the hood, roof, trunk and bumpers') +
            item('copy', 'copy', 'Mirror To Other Side', 'Copy the selected layer (or just the selection) onto the matching part, fitted to that side’s shape - not a flat flip. Ctrl+Z undoes it.') +
            item('readable', 'text', 'Copy To Other Side (Text Reads Right)', 'Like Mirror To Other Side, but numbers and lettering are turned so they still read the right way on the other side') +
            item('stripe', 'stripe', 'Car Stripe…', 'A stripe down the middle of the car: centred on the hood, roof, trunk and bumpers and lined up at every seam') +
            item('reread', 'scan', 'Re-Measure Car Sides', 'Measure again how this car’s left and right sides line up (after changing the template)') +
            '<div class="spb-sym-note" role="note" style="display:none;max-width:300px;padding:6px 10px 4px;margin-top:4px;border-top:1px solid rgba(255,255,255,.14);font-size:11.5px;line-height:1.35;opacity:.85;white-space:normal"></div>' +
            '</div>';
        anchor.parentNode.insertBefore(menu, anchor.nextSibling);
        menu.addEventListener('click', e => {
            const b = e.target.closest && e.target.closest('[data-sym]'); if (!b) return;
            e.preventDefault(); menu.removeAttribute('open'); act(b.getAttribute('data-sym'));
        });
        return true;
    }
    function act(id) {
        if (off()) return;
        if (id === 'paint') { setOn(!S.on); return; }
        if (id === 'copy') { mirrorLayer(false); return; }
        if (id === 'readable') { mirrorLayer(true); return; }
        if (id === 'stripe') { openStripe(); return; }
        if (id === 'reread') { toast('Measuring this car’s sides…', 'info'); ensureBuilt(true).then(C => { if (C) toast(qualityMsg()); }); }
    }
    function qualityMsg() {
        const C0 = sym().cur(); if (C0 && fitMode(C0) === 'none') return noneMsg(C0);
        const s = sym().summary(); if (!s || !s.pairs.length) return 'This car map has no left / right side panels.';
        const p = s.pairs[0], e = p.errAB;
        return 'Left and right sides line up within about ' + Math.max(e.outline.median || 0, e.lines.median || 0) + ' px (9 in 10 within ' + Math.max(e.outline.p90 || 0, e.lines.p90 || 0) + ' px).' + (C0 ? fitNote(C0) : '');
    }
    function hideGhost() { if (ghost) ghost.style.display = 'none'; }
    function refreshUi() {
        if (off()) { [toggle, hint, menu, ghost].forEach(e => { if (e) e.style.display = 'none'; }); closeStripe(); return; }
        ensureToggle(); ensureHint(); ensureMenu();
        const sup = supported();
        if (toggle) { toggle.style.display = sup ? '' : 'none'; toggle.setAttribute('aria-pressed', S.on ? 'true' : 'false'); toggle.classList.toggle('spb-sym-busy', S.building); }
        if (hint) {
            const show = sup && S.on; hint.style.display = show ? '' : 'none';
            // one line that never widens the tool band: full text, else a short one, else hidden (the toggle's tooltip says it all)
            // - all in this one synchronous pass, so nothing flickers. 1100 px: the band already scrolls, so the hint stays hidden.
            const band = hint.parentNode, fits = () => !band || band.scrollWidth <= band.clientWidth + 1;
            const ts = S.building ? ['Mirror Paint: measuring this car’s sides…', 'Measuring sides…'] : hintTexts(sym() && sym().cur());
            if (show) {
                if (hint.textContent !== ts[0]) hint.textContent = ts[0];
                if (!fits()) { hint.textContent = ts[1]; if (!fits()) hint.style.display = 'none'; }
            }
        }
        if (menu) { menu.style.display = ''; const b = menu.querySelector('[data-sym="paint"]'); if (b) b.setAttribute('aria-pressed', S.on ? 'true' : 'false'); }
        // how well this car could be lined up (Wire template / outline only / plain flip / not mirrored): menu note + toggle tooltip
        const C = sym() && sym().cur(), md = C ? fitMode(C) : 'wire', note = (C && md !== 'wire') ? (md === 'none' ? noneMsg(C) : fitNote(C).trim()) : '';
        if (menu) { const nd = menu.querySelector('.spb-sym-note'); if (nd) { nd.textContent = note; nd.style.display = note ? '' : 'none'; } }
        if (toggle) { const base = toggle.getAttribute('data-base-title') || toggle.title; toggle.setAttribute('data-base-title', base); toggle.title = note ? base + '\n\n' + note : base; }
        if (toggle) { // a small amber '!' on the toggle while strokes are not (fully) mirrored on this car (also visible when the options bar is too narrow for the hint line)
            let w = toggle.querySelector('.spb-sym-warn'); const bad = S.on && (md === 'none' || md === 'plain' || md === 'partial');
            if (bad && !w) { w = doc.createElement('span'); w.className = 'spb-sym-warn'; w.setAttribute('aria-hidden', 'true'); w.textContent = '!'; w.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;width:13px;height:13px;margin-left:5px;border-radius:50%;background:#e0a030;color:#1b1b1f;font-weight:700;font-size:10px;line-height:1;flex:0 0 auto'; toggle.appendChild(w); }
            else if (!bad && w) w.remove();
        }
        if (!S.on || !sup) hideGhost();
    }
    let gq = null, graf = 0;
    function brushRadius() { const v = call('getBrushSize'); if (Number.isFinite(v)) return v; const e = doc.getElementById('brushSize'); return e ? +e.value || 20 : 20; }
    function drawGhost() {
        graf = 0; const e = gq; gq = null; if (!e) return;
        if (!active() && !activeMat()) { hideGhost(); return; }
        const pc = doc.getElementById('paintCanvas'); if (!pc) { hideGhost(); return; }
        const r = pc.getBoundingClientRect();
        if (e.clientX < r.left || e.clientY < r.top || e.clientX > r.right || e.clientY > r.bottom || !r.width) { hideGhost(); return; }
        const k = pc.width / r.width, m = mirrorPoint((e.clientX - r.left) * k, (e.clientY - r.top) * k, false);
        if (!m) { hideGhost(); return; }
        const gx = r.left + m.x / k, gy = r.top + m.y / k, D = Math.max(6, 2 * brushRadius() * m.scale / k);
        const sc = call('getScrollContainer');
        if (sc && sc.getBoundingClientRect) { const b = sc.getBoundingClientRect(); if (gx < b.left || gy < b.top || gx > b.right || gy > b.bottom) { hideGhost(); return; } }
        if (!ghost) { ghost = doc.createElement('div'); ghost.id = 'spbSymGhost'; ghost.className = 'spb-sym-ghost'; ghost.setAttribute('aria-hidden', 'true'); doc.body.appendChild(ghost); }
        ghost.style.display = 'block'; ghost.style.left = (gx - D / 2) + 'px'; ghost.style.top = (gy - D / 2) + 'px'; ghost.style.width = D + 'px'; ghost.style.height = D + 'px';
    }
    doc.addEventListener('pointermove', e => { if (!S.on) return; gq = e; if (!graf) graf = root.requestAnimationFrame(drawGhost); }, { passive: true, capture: true });
    doc.addEventListener('pointerdown', e => { // every stroke starts with fresh combined clips; a changed car is re-measured
        if (!S.on || off()) return;
        const pc = doc.getElementById('paintCanvas'); if (!pc || e.target !== pc && !(e.target && e.target.closest && e.target.closest('#splitSource'))) return;
        COMBO = new WeakMap();
        if (!S.building && quickSig() !== S.sig) ensureBuilt(false);
    }, true);

    // ---------------------------------------------------------------- install
    let lastUi = '';
    function install() {
        if (off()) return false;
        const need = ['_paintOnLayerAt', '_applyWithSymmetry', 'paintColorBrush', 'paintHistoryBrush', '_activeSelectionMask'];
        if (!need.every(n => typeof root[n] === 'function')) return false;
        wrapSelection(); wrapDab('_paintOnLayerAt', 'layer'); wrapDab('_applyWithSymmetry', 'sym'); wrapDab('paintColorBrush', 'xy'); wrapDab('paintHistoryBrush', 'xy');
        watchMaterial();
        refreshUi();
        setInterval(() => { // tool / layer-mode changes have no event: a cheap poll keeps the toggle + hint in step
            const k = (off() ? 'off' : '') + mode() + '|' + layerMode() + '|' + S.on + '|' + S.building;
            if (k !== lastUi || (menu && !menu.isConnected) || (toggle && !toggle.isConnected)) { lastUi = k; refreshUi(); }
        }, 400);
        // the hint's fit depends on the tool band's width: re-check when the window / band resizes (1920 -> 1100 etc.)
        let rq = 0; const again = () => { if (rq) return; rq = requestAnimationFrame(() => { rq = 0; refreshUi(); }); };
        root.addEventListener('resize', again);
        try { const band = doc.getElementById('spbToolRowTop'); if (band && root.ResizeObserver) new root.ResizeObserver(again).observe(band); } catch (e) {}
        return true;
    }
    // [SPB-REV-SYM2 2026-10-10] Booted OFF, then switched on live (window flag cleared / localStorage removed): the old boot gave up after
    // 20 s, so the hooks and the UI never came back until a reload. While the switch is off, nothing is installed (no hooks, no UI) and a
    // 1 s check (one flag + one localStorage read) waits for it to be lifted; the retry budget only counts while it is on.
    let tries = 0;
    function boot() { if (install()) return; if (off()) { setTimeout(boot, 1000); return; } if (++tries < 40) setTimeout(boot, 500); }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot); else boot();

    root.SpbRevSymTools = {
        version: VER, setOn, isOn: () => S.on, stats: () => Object.assign({}, S.stats), ensureBuilt, refreshUi,
        mirrorLayer, openStripe, applyStripe, closeStripe, mirrorDab, mirrorDir, materialDab, stripe: STRIPE, last: () => ({ mirror: S.lastMirror || null, stripe: S.lastStripe || null }),
        _internal: { mirrorPoint, latField, leftSign, chain, stripeData, halfMask, axisOf, readableL, groupsOf, stripeInsertIndex, layerRole }
    };
})(typeof window !== 'undefined' ? window : globalThis);
