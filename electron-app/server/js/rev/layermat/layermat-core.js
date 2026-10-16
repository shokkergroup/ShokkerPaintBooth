/* [SPB-REV-LAYERMAT 2026-10-10] Layer Materials: the spec map follows the art.
 *
 * Every paint layer (sponsor, number, logo, text, placed image) can carry ONE optional field,
 * `layer.spbMaterial` (a frozen plain object, replaced - never mutated - so the app's own layer-stack
 * undo/redo restores it exactly). At serialization time the spec for that layer's pixels is derived
 * from the layer's OWN composited alpha (opacity, layer mask, clipping, group opacity; hidden = none),
 * so moving / scaling / rotating / editing the layer moves its spec with it. No second mask.
 *
 * Data flow (design: _easy_claude_work/rev_tools/layermat/DESIGN.md) reuses REV-MATERIAL's paths only:
 *  - spec presets (Gloss Vinyl, Matte Vinyl, Satin, Chrome Foil, Brushed Metal; values read from
 *    engine.BASE_REGISTRY) + Edge + Vinyl Edge Lip -> merged into `_spb_rev_material.spec` (bbox PNG
 *    pair, per-channel coverage) UNDER the Spec / Wear brush layer;
 *  - full SPB finishes (Holographic, Carbon, any finish from the app's picker) -> virtual coats in
 *    `_spb_rev_material.coats` (rendered by the engine itself), masked by the layer's visible alpha.
 *  The stack is composited exactly: a higher layer wins where it covers, a plain layer above a material
 *  layer gives that spot back to the zones, coat masks are pre-divided so the engine's coats->spec
 *  order reproduces the ideal stack. REV-MATERIAL brushwork always sits on top of layer materials.
 *  No engine change: engine/rev_material_layer.py already applies both parts.
 *
 * Kill switch: window.SPB_REV_LAYERMAT_OFF = true or localStorage SPB_REV_LAYERMAT_OFF = '1'
 * (no UI, no payload; the per-layer field is still saved/loaded untouched so nothing is lost).
 */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    const FIELD = 'spbMaterial';
    const TAG = '[REV-LAYERMAT]';

    function off() {
        if (root.SPB_REV_LAYERMAT_OFF) return true;
        try { return root.localStorage.getItem('SPB_REV_LAYERMAT_OFF') === '1'; } catch (_) { return false; }
    }

    // ---------------------------------------------------------------- presets
    // M / R / CC read from engine.BASE_REGISTRY on 2026-10-10 (_easy_claude_work/rev_tools/layermat/dump_registry.py
    // -> registry_presets.json). grain = the same fine grain REV-MATERIAL's Spec Brush uses for that preset,
    // anchored to the LAYER (it moves with the art). The engine floors CC >= 16 and R >= 15 (unless M >= 240).
    const PRESETS = [
        { id: 'gloss', name: 'Gloss Vinyl', kind: 'spec', src: 'gloss', m: 0, r: 30, cc: 16, grain: 0, tip: 'Glossy printed vinyl under clear' },
        { id: 'matte', name: 'Matte Vinyl', kind: 'spec', src: 'matte', m: 0, r: 200, cc: 160, grain: 20, tip: 'Flat matte vinyl, zero shine' },
        { id: 'satin', name: 'Satin', kind: 'spec', src: 'satin', m: 0, r: 95, cc: 70, grain: 15, tip: 'Soft semi-gloss vinyl' },
        { id: 'chrome', name: 'Chrome Foil', kind: 'spec', src: 'chrome', m: 255, r: 2, cc: 0, grain: 0, tip: 'Mirror chrome foil' },
        { id: 'brushed', name: 'Brushed Metal', kind: 'spec', src: 'brushed_aluminum', m: 200, r: 55, cc: 16, grain: 60, grainKind: 'brushed', tip: 'Brushed aluminium foil, horizontal grain' },
        { id: 'holo', name: 'Holographic', kind: 'finish', finishId: 'holographic_base', tip: 'SPB Holographic Base finish (engine-rendered paint + spec)' },
        { id: 'carbon', name: 'Carbon', kind: 'finish', finishId: 'carbon_base', tip: 'SPB Carbon Base finish (engine-rendered weave paint + spec)' }
    ];
    const PRESET_BY_ID = {};
    PRESETS.forEach(function (p) { PRESET_BY_ID[p.id] = p; });
    // Vinyl Edge Lip: the clear pooled over a vinyl edge reads as a thin satin line (R / CC of BASE_REGISTRY satin).
    const LIP = { r: 95, cc: 70, radius: 1 };
    const EDGE_MAX = 24;

    // ---------------------------------------------------------------- material records
    function rawId(id) { return String(id || '').replace(/^mono:/, ''); }
    function finishName(id) {
        const raw = rawId(id);
        try { if (typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID[raw]) return BASES_BY_ID[raw].name || raw; } catch (_) {}
        try { if (typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID[raw]) return MONOLITHICS_BY_ID[raw].name || raw; } catch (_) {}
        return raw.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }
    /** {preset:'matte'} | {finishId:'x'} -> canonical material ref, or null. */
    function normRef(o) {
        if (!o || typeof o !== 'object') return null;
        if (o.preset && PRESET_BY_ID[o.preset]) {
            const p = PRESET_BY_ID[o.preset];
            return p.kind === 'finish' ? { preset: p.id, finishId: p.finishId } : { preset: p.id };
        }
        if (o.finishId && typeof o.finishId === 'string' && o.finishId !== 'none') return { finishId: String(o.finishId).slice(0, 120) };
        return null;
    }
    /** Validate + canonicalise a stored/incoming record. Returns a FROZEN record or null. */
    function normalize(rec) {
        if (!rec || typeof rec !== 'object') return null;
        const main = normRef(rec);
        if (!main) return null;
        const out = { v: 1 };
        if (main.preset) out.preset = main.preset;
        if (main.finishId) out.finishId = main.finishId;
        if (out.finishId && rec.keep) out.keep = true;
        // [SPB-REV-FLAKE 2026-10-10] (lane REV-FLAKE, additive) a Flake Studio recipe on the layer's finish coat (js/rev/flake/flake-studio.js)
        if (out.finishId && rec.flake && typeof rec.flake === 'object' && !root.SPB_FLAKE_OFF) { try { out.flake = Object.freeze(JSON.parse(JSON.stringify(rec.flake))); } catch (_) {} }
        if (rec.edge && typeof rec.edge === 'object') {
            const e = normRef(rec.edge);
            if (e) {
                const w = Math.max(1, Math.min(EDGE_MAX, Math.round(Number(rec.edge.width) || 4)));
                out.edge = Object.freeze(Object.assign(e, { width: w, pos: rec.edge.pos === 'outside' ? 'outside' : 'inside' }));
            }
        }
        const lip = Math.round(Number(rec.lip) || 0);
        if (lip > 0) out.lip = Math.min(100, lip);
        return Object.freeze(out);
    }
    function refName(ref) {
        if (!ref) return 'None';
        if (ref.preset && PRESET_BY_ID[ref.preset]) return PRESET_BY_ID[ref.preset].name;
        return finishName(ref.finishId);
    }
    function refKind(ref) {
        if (!ref) return null;
        if (ref.preset && PRESET_BY_ID[ref.preset]) return PRESET_BY_ID[ref.preset].kind;
        return 'finish';
    }
    function describe(rec) {
        if (!rec) return 'None';
        let s = refName(rec);
        if (rec.keep) s += ' (keep art colour)';
        if (rec.flake) s += ' + flake ' + String(rec.flake.look || 'custom').replace(/_/g, ' ');   // [SPB-REV-FLAKE 2026-10-10]
        if (rec.edge) s += ' + ' + refName(rec.edge) + ' edge ' + rec.edge.width + ' px ' + rec.edge.pos;
        if (rec.lip) s += ' + vinyl edge lip';
        return s;
    }

    // ---------------------------------------------------------------- layer access
    function layers() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; }
    function byId(id) { const s = layers(); for (let i = 0; i < s.length; i++) if (s[i] && String(s[i].id) === String(id)) return s[i]; return null; }
    function get(idOrLayer) {
        const L = (idOrLayer && typeof idOrLayer === 'object') ? idOrLayer : byId(idOrLayer);
        const r = L && L[FIELD];
        return (r && typeof r === 'object') ? r : null;
    }
    function isHelper(l) { return /^\s*(mask|wire)\b/i.test(String((l && l.name) || '')); }
    function canvasDims() { const pc = doc.getElementById('paintCanvas'); return pc ? [pc.width | 0, pc.height | 0] : [0, 0]; }

    // ---------------------------------------------------------------- assign (one app undo step)
    const listeners = [];
    function emit(what, info) { listeners.forEach(function (f) { try { f(what, info); } catch (_) {} }); }
    let lastSig = null, kickTimer = null;
    function sig() {
        const s = layers(); const parts = [];
        for (let i = 0; i < s.length; i++) { const r = get(s[i]); if (r) parts.push(s[i].id + '=' + JSON.stringify(r)); }
        return parts.join('|');
    }
    /** Any path that changed materials (assign, the app's undo / redo, project open): repaint the live preview. */
    function noticeChange(force) {
        const now = sig();
        if (!force && now === lastSig) return false;
        lastSig = now;
        if (kickTimer) clearTimeout(kickTimer);
        kickTimer = setTimeout(function () {
            kickTimer = null;
            emit('changed');
            if (off()) return;
            try { if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); else if (typeof root.triggerPreviewRender === 'function') root.triggerPreviewRender(); } catch (_) {}
        }, 40);
        return true;
    }
    /**
     * Set (rec) or clear (null) the material of one or more layers. ONE undo step through the app's own
     * layer-stack history (`_pushLayerStackUndo`), so Ctrl+Z / Ctrl+Y / the History panel restore it exactly.
     * patch=true merges rec into each layer's current record (e.g. only the edge changes).
     */
    function assign(ids, rec, opts) {
        opts = opts || {};
        if (off()) return { ok: false, why: 'off' };
        ids = (Array.isArray(ids) ? ids : [ids]).map(String);
        const targets = ids.map(byId).filter(function (l) { return l && !isHelper(l); });
        if (!targets.length) return { ok: false, why: 'no layer' };
        const next = targets.map(function (L) {
            const cur = get(L);
            let r = rec;
            if (opts.patch && rec && cur) r = Object.assign({}, cur, rec);
            else if (opts.patch && rec && !cur) r = (rec.preset || rec.finishId) ? rec : null;
            return r ? normalize(r) : null;
        });
        let changedAny = false;
        for (let i = 0; i < targets.length; i++) if (JSON.stringify(get(targets[i])) !== JSON.stringify(next[i])) changedAny = true;
        if (!changedAny) return { ok: true, changed: 0 };
        const label = opts.label || ('Layer Material: ' + (next[0] ? refName(next[0]) : 'None') + (targets.length > 1 ? ' (' + targets.length + ' layers)' : ''));
        try { if (typeof root._pushLayerStackUndo === 'function') root._pushLayerStackUndo(label); } catch (e) { console.warn(TAG, 'undo push', e); }
        targets.forEach(function (L, i) { if (next[i]) L[FIELD] = next[i]; else delete L[FIELD]; });
        root._spbLayerRev = (root._spbLayerRev | 0) + 1;
        try { if (typeof root.renderLayerPanel === 'function') root.renderLayerPanel(); } catch (_) {}
        noticeChange(true);
        return { ok: true, changed: targets.length, label: label };
    }

    // ---------------------------------------------------------------- persistence (one optional per-layer field)
    function serialize(layer) {
        const r = get(layer);
        return r ? JSON.parse(JSON.stringify(r)) : undefined;
    }
    function deserialize(layer, rec) {
        if (!layer) return;
        const r = rec ? normalize(rec) : null;
        if (r) layer[FIELD] = r; else delete layer[FIELD];
    }

    // ---------------------------------------------------------------- alpha of one layer, exactly as the composite draws it
    const imgIds = new WeakMap(); let imgSeq = 0;
    function objId(o) { if (!o || (typeof o !== 'object' && typeof o !== 'function')) return 0; let v = imgIds.get(o); if (!v) { v = ++imgSeq; imgIds.set(o, v); } return v; }
    let scratch = null, sctx = null;
    function scratchCtx(W, H) {
        if (!scratch) scratch = doc.createElement('canvas');
        if (scratch.width !== W || scratch.height !== H) { scratch.width = W; scratch.height = H; sctx = null; }
        if (!sctx) sctx = scratch.getContext('2d', { willReadFrequently: true });
        return sctx;
    }
    function canComposite(ls, i) {
        try { return typeof root._layerAtIndexCanComposite === 'function' ? !!root._layerAtIndexCanComposite(ls, i) : true; } catch (_) { return true; }
    }
    /** Layer i rendered alone (identity blend, no FX) -> Uint8 alpha over rect [x0,y0,x1,y1]. */
    function layerAlpha(ls, i, rect, W, H) {
        const ctx = scratchCtx(W, H);
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
        ctx.clearRect(0, 0, W, H);
        const copy = ls.slice();
        const draw = function (c, layer, li) {
            // the same footprint the ownership code measures: blend normalised to source-over, pixel content only
            copy[li] = Object.assign({}, layer, { blendMode: 'source-over' });
            const fn = root._drawLayerPixelContent;
            const drew = typeof fn === 'function' ? fn(c, copy, li, null) : false;
            c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
            return drew;
        };
        let res = null;
        if (typeof root._spbCompositeLayerStack === 'function') {
            res = root._spbCompositeLayerStack(ctx, copy, { includeLayer: function (_l, li) { return li === i; }, identityBlend: true, drawLayer: draw });
        } else {
            res = { ok: !!draw(ctx, ls[i], i) };
        }
        if (!res || !res.ok) return null;
        const rw = rect[2] - rect[0], rh = rect[3] - rect[1];
        if (rw <= 0 || rh <= 0) return null;
        const d = ctx.getImageData(rect[0], rect[1], rw, rh).data;
        const a = new Uint8Array(rw * rh);
        let any = 0;
        for (let k = 0, j = 3; k < a.length; k++, j += 4) { const v = d[j]; a[k] = v; any |= v; }
        return any ? a : null;
    }

    // ---------------------------------------------------------------- morphology (octagonal grey dilate / erode, soft alpha)
    // open = [left, top, right, bottom]: true where the crop edge is NOT the canvas edge (beyond it = empty art);
    // at the canvas edge the art continues off-sheet, so the border pixel is replicated instead.
    function morph(src, w, h, r, dilate, open) {
        open = open || [true, true, true, true];
        let a = src, b = new Uint8Array(src.length);
        for (let it = 0; it < r; it++) {
            const diag = (it % 2) === 0;   // square step then cross step -> octagon (rounder outlines than a square)
            for (let y = 0; y < h; y++) {
                const y0 = y > 0 ? y - 1 : y, y1 = y < h - 1 ? y + 1 : y;
                for (let x = 0; x < w; x++) {
                    const x0 = x > 0 ? x - 1 : x, x1 = x < w - 1 ? x + 1 : x;
                    let v = a[y * w + x];
                    const n1 = a[y0 * w + x], n2 = a[y1 * w + x], n3 = a[y * w + x0], n4 = a[y * w + x1];
                    if (dilate) {
                        if (n1 > v) v = n1; if (n2 > v) v = n2; if (n3 > v) v = n3; if (n4 > v) v = n4;
                        if (diag) { const d1 = a[y0 * w + x0], d2 = a[y0 * w + x1], d3 = a[y1 * w + x0], d4 = a[y1 * w + x1]; if (d1 > v) v = d1; if (d2 > v) v = d2; if (d3 > v) v = d3; if (d4 > v) v = d4; }
                    } else {
                        // erode: outside the crop counts as empty (the crop is padded around the art)
                        if ((y === 0 && open[1]) || (y === h - 1 && open[3]) || (x === 0 && open[0]) || (x === w - 1 && open[2])) v = 0;
                        else {
                            if (n1 < v) v = n1; if (n2 < v) v = n2; if (n3 < v) v = n3; if (n4 < v) v = n4;
                            if (diag) { const d1 = a[y0 * w + x0], d2 = a[y0 * w + x1], d3 = a[y1 * w + x0], d4 = a[y1 * w + x1]; if (d1 < v) v = d1; if (d2 < v) v = d2; if (d3 < v) v = d3; if (d4 < v) v = d4; }
                        }
                    }
                    b[y * w + x] = v;
                }
            }
            const t = a === src ? new Uint8Array(src.length) : a;
            a = b; b = t;
        }
        return a === src ? new Uint8Array(src) : a;
    }

    // ---------------------------------------------------------------- build (cached on a fingerprint of everything that affects it)
    function layerFp(l) {
        let g = '';
        try { if (Array.isArray(l.groupChain) && l.groupChain.length) g = JSON.stringify(l.groupChain.map(function (c) { return [c && c.key, c && c.visible, c && c.ownVisible, c && c.opacity, c && c.mode]; })); } catch (_) {}
        return [l.id, objId(l.img), (l.bbox || []).join(','), l.opacity, l.visible === false ? 0 : 1, l.clippingMask ? 1 : 0,
            objId(l.pcMask), l.name, g, JSON.stringify(get(l) || null)].join('~');
    }
    const cache = { fp: null, res: null, ver: 0, alpha: new Map() };
    function presetCtx(p) {
        const R = root.SPBRevMatRecipes;
        if (!R || !p.grain) return null;
        try { return R.makeContext(0, 7).sampleSpec; } catch (_) { return null; }
    }
    function matOf(ref, coatKeys, coats, keep) {
        if (!ref) return null;
        const kind = refKind(ref);
        if (kind === 'spec') {
            const p = PRESET_BY_ID[ref.preset];
            return { kind: 'spec', p: p, samp: presetCtx(p), o: { m: 0, r: 0, cc: 0 } };
        }
        const fid = ref.finishId;
        const key = fid + (keep ? '|keep' : '') + (ref.flake ? '|flake:' + JSON.stringify(ref.flake) : '');   // [SPB-REV-FLAKE 2026-10-10] a flake coat is its own coat
        if (!(key in coatKeys)) { coatKeys[key] = coats.length; coats.push({ finishId: fid, keep: !!keep, name: finishName(fid), flake: ref.flake || null }); }
        return { kind: 'coat', k: coatKeys[key] };
    }
    function build() {
        const dims = canvasDims(), W = dims[0], H = dims[1];
        const ls = layers();
        if (!W || !H || !ls.length) return null;
        let lo = -1;
        for (let i = 0; i < ls.length; i++) { const l = ls[i]; if (l && get(l) && l.img && l.visible !== false && !isHelper(l)) { lo = i; break; } }
        if (lo < 0) { cache.fp = 'none'; cache.res = null; return null; }
        const fpParts = [W, H, lo];
        for (let i = lo; i < ls.length; i++) {
            fpParts.push(ls[i] ? layerFp(ls[i]) : '-');
            if (ls[i] && ls[i].clippingMask) {
                try { const bl = typeof root._clippingBaseForLayerIndex === 'function' ? root._clippingBaseForLayerIndex(ls, i) : null; if (bl) fpParts.push('base:' + layerFp(bl)); } catch (_) {}
            }
        }
        const fp = fpParts.join('\u0001');
        if (fp === cache.fp) return cache.res;
        const t0 = performance.now();
        const coatKeys = {}, coats = [], seq = [], aliveAlpha = new Map();
        let RX0 = W, RY0 = H, RX1 = 0, RY1 = 0;
        for (let i = lo; i < ls.length; i++) {
            const l = ls[i];
            if (!l || !l.img || l.visible === false || isHelper(l) || !canComposite(ls, i)) continue;
            const rec = get(l);
            const b = l.bbox || [0, 0, W, H];
            const edgeOut = rec && rec.edge && rec.edge.pos === 'outside' ? rec.edge.width : 0;
            const pad = rec ? Math.max(edgeOut, rec.lip ? LIP.radius : 0) + 2 : 0;
            const rect = [Math.max(0, Math.floor(b[0]) - pad), Math.max(0, Math.floor(b[1]) - pad), Math.min(W, Math.ceil(b[2]) + pad), Math.min(H, Math.ceil(b[3]) + pad)];
            if (rect[2] <= rect[0] || rect[3] <= rect[1]) continue;
            let baseFp = '';
            if (l.clippingMask) {   // a clipped layer's footprint depends on its base layer's pixels too
                try { const bl = typeof root._clippingBaseForLayerIndex === 'function' ? root._clippingBaseForLayerIndex(ls, i) : null; baseFp = bl ? layerFp(bl) : ''; } catch (_) {}
            }
            const akey = layerFp(l) + '#' + baseFp + '#' + rect.join(',') + '#' + i + '#' + W + 'x' + H;
            let a = cache.alpha.get(akey);
            if (a === undefined) a = layerAlpha(ls, i, rect, W, H);
            aliveAlpha.set(akey, a);
            if (!a) continue;
            const e = { i: i, id: l.id, name: l.name, x0: rect[0], y0: rect[1], x1: rect[2], y1: rect[3], w: rect[2] - rect[0], a: a, ox: Math.floor(b[0]), oy: Math.floor(b[1]) };
            if (rec) {
                e.main = matOf(rec, coatKeys, coats, rec.keep);
                const open = [rect[0] > 0, rect[1] > 0, rect[2] < W, rect[3] < H];
                if (rec.edge) {
                    e.edge = matOf(rec.edge, coatKeys, coats, false);
                    const h = rect[3] - rect[1];
                    if (rec.edge.pos === 'outside') {
                        const dl = morph(a, e.w, h, rec.edge.width, true, open);
                        for (let k = 0; k < dl.length; k++) dl[k] = dl[k] > a[k] ? dl[k] - a[k] : 0;
                        e.outBand = dl;
                    } else {
                        const er = morph(a, e.w, h, rec.edge.width, false, open);
                        for (let k = 0; k < er.length; k++) er[k] = a[k] > er[k] ? a[k] - er[k] : 0;
                        e.inBand = er;
                    }
                }
                if (rec.lip) {
                    const h = rect[3] - rect[1];
                    const dl = morph(a, e.w, h, LIP.radius, true, open), er = morph(a, e.w, h, LIP.radius, false, open);
                    for (let k = 0; k < dl.length; k++) dl[k] = dl[k] > er[k] ? dl[k] - er[k] : 0;
                    e.lip = dl; e.lipK = rec.lip / 100;
                }
                if (rect[0] < RX0) RX0 = rect[0]; if (rect[1] < RY0) RY0 = rect[1];
                if (rect[2] > RX1) RX1 = rect[2]; if (rect[3] > RY1) RY1 = rect[3];
            }
            seq.push(e);
        }
        cache.alpha = aliveAlpha;   // keep only what this stack uses (unchanged layers skip the re-render next time)
        const tA = performance.now();
        if (RX1 <= RX0 || RY1 <= RY0) { cache.fp = fp; cache.res = null; return null; }
        const RW = RX1 - RX0, RH = RY1 - RY0, N = RW * RH;
        const cov = new Uint8Array(N * 3), val = new Uint8Array(N * 3);
        const coatMasks = coats.map(function () { return new Uint8Array(W * H); });
        const nc = coats.length, wk = new Float64Array(Math.max(1, nc));
        let specPx = 0;
        const S = { cM: 0, cR: 0, cC: 0, sM: 0, sR: 0, sC: 0 };
        function mul(f) {
            S.cM *= f; S.cR *= f; S.cC *= f; S.sM *= f; S.sR *= f; S.sC *= f;
            for (let q = 0; q < nc; q++) wk[q] *= f;
        }
        function add(mt, w, x, y, e) {
            if (!mt || w <= 0) return;
            if (mt.kind === 'coat') { wk[mt.k] += w; return; }
            const p = mt.p;
            let m = p.m, r = p.r, cc = p.cc;
            if (mt.samp) { const o = mt.o; mt.samp(p, x - e.ox, y - e.oy, o); m = o.m; r = o.r; cc = o.cc; }
            S.cM += w; S.sM += m * w; S.cR += w; S.sR += r * w; S.cC += w; S.sC += cc * w;
        }
        const ns = seq.length;
        for (let y = RY0; y < RY1; y++) {
            for (let x = RX0; x < RX1; x++) {
                S.cM = S.cR = S.cC = S.sM = S.sR = S.sC = 0;
                for (let q = 0; q < nc; q++) wk[q] = 0;
                let any = false;
                for (let s = 0; s < ns; s++) {
                    const e = seq[s];
                    if (x < e.x0 || x >= e.x1 || y < e.y0 || y >= e.y1) continue;
                    const idx = (y - e.y0) * e.w + (x - e.x0);
                    const av = e.a[idx];
                    if (!e.main) {                       // a plain layer above: its pixels go back to the zones
                        if (av && any) mul(1 - av / 255);
                        continue;
                    }
                    if (av) {
                        const aa = av / 255;
                        if (any) mul(1 - aa);
                        const ib = e.inBand ? e.inBand[idx] / 255 : 0;
                        add(e.main, aa - ib, x, y, e);
                        if (ib > 0) add(e.edge, ib, x, y, e);
                        any = true;
                    }
                    if (e.outBand) {
                        const bv = e.outBand[idx];
                        if (bv) { const bb = bv / 255; if (any) mul(1 - bb); add(e.edge, bb, x, y, e); any = true; }
                    }
                    if (e.lip) {
                        const lv = e.lip[idx];
                        if (lv) {
                            const ll = (lv / 255) * e.lipK, f = 1 - ll;
                            S.cR = S.cR * f + ll; S.sR = S.sR * f + LIP.r * ll;
                            S.cC = S.cC * f + ll; S.sC = S.sC * f + LIP.cc * ll;
                            any = true;
                        }
                    }
                }
                if (!any) continue;
                const o = ((y - RY0) * RW + (x - RX0)) * 3;
                if (S.cM > 0 || S.cR > 0 || S.cC > 0) {
                    specPx++;
                    cov[o] = Math.round(S.cM * 255); cov[o + 1] = Math.round(S.cR * 255); cov[o + 2] = Math.round(S.cC * 255);
                    val[o] = S.cM > 1e-6 ? Math.round(S.sM / S.cM) : 0;
                    val[o + 1] = S.cR > 1e-6 ? Math.round(S.sR / S.cR) : 0;
                    val[o + 2] = S.cC > 1e-6 ? Math.round(S.sC / S.cC) : 0;
                }
                if (nc) {
                    // the engine composites coats BEFORE the spec layer: pre-divide by what the spec layer will cover
                    // so coats -> spec reproduces the ideal stack exactly (w_coat / (1 - c_spec)).
                    const rest = 1 - S.cM;
                    for (let q = 0; q < nc; q++) {
                        if (wk[q] <= 0) continue;
                        const m = rest > 1e-3 ? Math.min(1, wk[q] / rest) : 0;
                        coatMasks[q][y * W + x] = Math.round(m * 255);
                    }
                }
            }
        }
        const res = {
            ver: ++cache.ver, W: W, H: H, rect: [RX0, RY0, RX1, RY1], cov: specPx ? cov : null, val: specPx ? val : null,
            coats: coats.map(function (c, q) { return Object.assign({ mask: coatMasks[q] }, c); }),
            layers: seq.filter(function (e) { return e.main; }).map(function (e) { return { id: e.id, name: e.name, rect: [e.x0, e.y0, e.x1, e.y1] }; }),
            ms: { alpha: Math.round(tA - t0), compose: Math.round(performance.now() - tA) }
        };
        cache.fp = fp; cache.res = res;
        return res;
    }

    // ---------------------------------------------------------------- REV-MATERIAL brushwork sits on top: read its buffers (sync)
    function brushState() {
        const RM = root.SPBRevMaterial;
        if (!RM || (typeof RM.off === 'function' && RM.off()) || !RM.state) return null;
        return RM.state;
    }
    function brushCoatUnion(st, rect, W) {
        // 1 - prod(1 - mask) of the brushed coats inside rect (null when none touch it)
        if (!st || !Array.isArray(st.coats) || !st.coats.length || st.W !== W) return null;
        const live = st.coats.filter(function (c) { return c && c.mask && c.box && c.box[0] < rect[2] && c.box[2] > rect[0] && c.box[1] < rect[3] && c.box[3] > rect[1]; });
        if (!live.length) return null;
        const RW = rect[2] - rect[0], RH = rect[3] - rect[1];
        const keep = new Float32Array(RW * RH).fill(1);
        let any = false;
        live.forEach(function (c) {
            for (let y = Math.max(rect[1], c.box[1]); y < Math.min(rect[3], c.box[3]); y++) {
                for (let x = Math.max(rect[0], c.box[0]); x < Math.min(rect[2], c.box[2]); x++) {
                    const v = c.mask[y * W + x];
                    if (v) { keep[(y - rect[1]) * RW + (x - rect[0])] *= (1 - v / 255); any = true; }
                }
            }
        });
        return any ? keep : null;
    }

    // ---------------------------------------------------------------- payload merge + encode (cached)
    function pngOf(w, h, fill) {
        const cv = doc.createElement('canvas');
        cv.width = w; cv.height = h;
        const ctx = cv.getContext('2d');
        const id = ctx.createImageData(w, h);
        fill(id.data);
        ctx.putImageData(id, 0, 0);
        return cv.toDataURL('image/png');
    }
    const enc = { key: null, spec: null, coatObjs: null, coatKey: null };
    function zoneTemplate() {
        if (enc.tpl) return JSON.parse(enc.tpl);
        if (typeof addZone !== 'function' || typeof zones === 'undefined') return null;
        const n = zones.length, sel = selectedZoneIndex, rz = root.renderZones;
        let fresh = null;
        root.renderZones = function () {};
        try { addZone(true); if (zones.length === n + 1) fresh = zones.pop(); }
        catch (e) { console.warn(TAG, 'template', e); }
        finally { root.renderZones = rz; selectedZoneIndex = sel; }
        if (!fresh) return null;
        delete fresh.renderSeedIndex;
        enc.tpl = JSON.stringify(fresh);
        return JSON.parse(enc.tpl);
    }
    function makeCoatZone(finishId, name) {
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
        t.name = 'Layer Material: ' + name;
        return t;
    }
    /** -> {coats:[{zone, keep_colour?}], spec:{bbox,val,cov}|null, stats} merged with REV-MATERIAL's layer (theirs on top). */
    function partsFor(theirs, serializer) {
        const res = build();
        if (!res) return null;
        const W = res.W, H = res.H;
        const st = brushState();
        const brushKey = st ? [st.layerVer, st.coatVer, st.W].join(':') : 'none';
        const key = res.ver + '|' + brushKey + '|' + (theirs && theirs.spec ? 'S' : '-');
        if (enc.key !== key) {
            // ---- spec part: mine (x (1 - brushed coats)), then REV-MATERIAL's Spec/Wear layer over it
            let rect = res.rect.slice();
            const bspec = (theirs && theirs.spec && st && st.sv && st.sc && st.lb) ? st : null;
            if (bspec) rect = [Math.min(rect[0], bspec.lb[0]), Math.min(rect[1], bspec.lb[1]), Math.max(rect[2], bspec.lb[2]), Math.max(rect[3], bspec.lb[3])];
            const RW = rect[2] - rect[0], RH = rect[3] - rect[1];
            const keep = res.cov ? brushCoatUnion(st, res.rect, W) : null;
            let spec = null;
            if (res.cov || bspec) {
                const cv = new Uint8Array(RW * RH * 3), vv = new Uint8Array(RW * RH * 3);
                let any = false;
                const mr = res.rect, mW = mr[2] - mr[0];
                for (let y = rect[1]; y < rect[3]; y++) {
                    for (let x = rect[0]; x < rect[2]; x++) {
                        const o = ((y - rect[1]) * RW + (x - rect[0])) * 3;
                        const inMine = res.cov && x >= mr[0] && x < mr[2] && y >= mr[1] && y < mr[3];
                        const mo = inMine ? ((y - mr[1]) * mW + (x - mr[0])) * 3 : -1;
                        const kf = (inMine && keep) ? keep[(y - mr[1]) * mW + (x - mr[0])] : 1;
                        const inB = bspec && x >= bspec.lb[0] && x < bspec.lb[2] && y >= bspec.lb[1] && y < bspec.lb[3];
                        const bi = inB ? (y * W + x) * 3 : -1;
                        for (let ch = 0; ch < 3; ch++) {
                            const c1 = mo >= 0 ? (res.cov[mo + ch] / 255) * kf : 0;
                            const c2 = bi >= 0 ? bspec.sc[bi + ch] / 255 : 0;
                            if (c1 <= 0 && c2 <= 0) continue;
                            const v1 = mo >= 0 ? res.val[mo + ch] : 0, v2 = bi >= 0 ? bspec.sv[bi + ch] : 0;
                            const c = c1 + c2 - c1 * c2;
                            cv[o + ch] = Math.round(c * 255);
                            vv[o + ch] = Math.round((v1 * c1 * (1 - c2) + v2 * c2) / c);
                            any = true;
                        }
                    }
                }
                if (any) {
                    const fill = function (src) {
                        return function (d) { for (let k = 0, j = 0; k < src.length; k += 3, j += 4) { d[j] = src[k]; d[j + 1] = src[k + 1]; d[j + 2] = src[k + 2]; d[j + 3] = 255; } };
                    };
                    spec = { bbox: [rect[0], rect[1], RW, RH], val: pngOf(RW, RH, fill(vv)), cov: pngOf(RW, RH, fill(cv)) };
                }
            }
            enc.spec = spec;
            enc.key = key;
            enc.coatKey = null;
        }
        // ---- coats: built by the ORIGINAL serializer (exactly what a real zone would send), x (1 - brushed coats)
        const ckey = res.ver + '|' + brushKey;
        if (enc.coatKey !== ckey) {
            let objs = [];
            const live = res.coats.filter(function (c) { for (let i = 0; i < c.mask.length; i += 7) if (c.mask[i]) return true; for (let i = 0; i < c.mask.length; i++) if (c.mask[i]) return true; return false; });
            if (live.length && typeof serializer === 'function') {
                const keepAll = brushCoatUnion(st, [0, 0, W, H], W);
                const zs = [];
                live.forEach(function (c) {
                    const z = makeCoatZone(c.finishId, c.name + (c.keep ? ' (keep colour)' : ''));
                    if (!z) return;
                    let m = c.mask;
                    if (keepAll) { m = new Uint8Array(c.mask); for (let i = 0; i < m.length; i++) if (m[i] && keepAll[i] < 1) m[i] = Math.round(m[i] * keepAll[i]); }
                    z.regionMask = m;
                    z.__lmCoat = c;
                    if (c.flake && !root.SPB_FLAKE_OFF) z.spbFlake = c.flake;   // [SPB-REV-FLAKE 2026-10-10] -> spb_flake (engine/rev_flake.py)
                    zs.push(z);
                });
                const made = zs.length ? (serializer(zs) || []) : [];
                objs = made.map(function (zo, i) {
                    const c = made.length === zs.length ? zs[i].__lmCoat : (zs.find(function (z) { return z.name === zo.name; }) || {}).__lmCoat;
                    const o = { zone: zo };
                    if (c && c.keep) o.keep_colour = true;
                    return o;
                });
            }
            enc.coatObjs = objs;
            enc.coatKey = ckey;
        }
        return { coats: enc.coatObjs || [], spec: enc.spec, res: res };
    }
    /** The merged `_spb_rev_material` object for this serialization (null = nothing to add). Exposed for tests. */
    function payload(theirs, serializer) {
        if (off()) return theirs || null;
        const p = partsFor(theirs || null, serializer);
        if (!p || (!p.coats.length && !p.spec)) return theirs || null;
        const lay = Object.assign({ v: 1, size: [p.res.W, p.res.H] }, theirs || {});
        lay.size = [p.res.W, p.res.H];
        // theirs first: in the engine's coat pass a lower index wins overlaps, and brushwork sits on top
        lay.coats = ((theirs && theirs.coats) || []).concat(p.coats);
        if (!lay.coats.length) delete lay.coats;
        if (p.spec) lay.spec = p.spec;
        lay.layermat = { v: 1, layers: p.res.layers.length };   // informational only (the engine ignores it)
        return lay;
    }

    // ---------------------------------------------------------------- serializer wrap (outermost, after REV-MATERIAL's)
    function wrapSerializer() {
        const cur = root.buildServerZonesForRender;
        if (typeof cur !== 'function') return false;
        if (cur.__spbLayerMat) return true;
        const RM = root.SPBRevMaterial;
        const revOn = !!(RM && !(typeof RM.off === 'function' && RM.off()));
        if (revOn && !cur.__spbRevMatOrig) return false;   // let REV-MATERIAL wrap first so ours stays outermost
        const orig = cur.__spbRevMatOrig || cur;
        const w = function (zs) {
            const out = cur.apply(this, arguments);
            try {
                if (off() || !Array.isArray(out) || !out.length || typeof zones === 'undefined' || zs !== zones) return out;
                const lay = payload(out[0]._spb_rev_material || null, orig);
                if (lay) out[0]._spb_rev_material = lay;
            } catch (e) { console.warn(TAG, 'payload skipped', e); }
            return out;
        };
        w.__spbLayerMat = true;
        if (cur.__spbRevMatOrig) w.__spbRevMatOrig = cur.__spbRevMatOrig;   // REV-MATERIAL's own re-wrap check stays satisfied
        root.buildServerZonesForRender = w;
        return true;
    }

    function stats() {
        const r = build();
        return {
            off: off(), layers: layers().filter(function (l) { return !!get(l); }).map(function (l) { return { id: l.id, name: l.name, mat: describe(get(l)) }; }),
            built: r ? { rect: r.rect, coats: r.coats.map(function (c) { return c.finishId; }), spec: !!r.cov, ms: r.ms } : null
        };
    }

    function init() {
        if (off()) return;
        lastSig = sig();
        let tries = 0;
        const t = setInterval(function () { wrapSerializer(); if (++tries > 40) clearInterval(t); }, 500);
        wrapSerializer();
    }

    root.SPBRevLayerMat = {
        FIELD: FIELD, PRESETS: PRESETS, PRESET_BY_ID: PRESET_BY_ID, LIP: LIP, EDGE_MAX: EDGE_MAX,
        off: off, get: get, assign: assign, normalize: normalize, describe: describe, refName: refName, refKind: refKind, finishName: finishName,
        serialize: serialize, deserialize: deserialize, build: build, payload: payload, stats: stats, sig: sig, noticeChange: noticeChange,
        wrapSerializer: wrapSerializer, on: function (f) { listeners.push(f); }, isHelper: isHelper, byId: byId,
        _cache: cache, _morph: morph
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
