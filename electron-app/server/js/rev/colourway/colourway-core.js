/* [SPB-REV-COLOURWAY 2026-10-10] Colourway Studio, core: the "Colourway" adjustment-layer type, the session (palette, variants, live apply),
 * sponsor protection, zones that follow the new colours, and one-step undo. UI is in colourway-ui.js, the maths in colourway-math.js.
 *
 * What it does (the Photoshop + iRacing chore it replaces): the same livery in several colourways (teammate cars, sponsor swaps, a night race
 * version). By hand that is "recolour every layer, then redo every zone". Here ONE adjustment layer carries a palette map (see the maths file)
 * so line work and shading stay, the layer is masked so sponsor / logo art keeps its own brand colours, and every zone that picks paint by
 * colour is re-aimed at the new colour (picker and multi-colour zones; tolerance rescaled so the zone still owns the same pixels).
 *
 * Data (all persisted by the existing adjustment-layer + layer-mask project fields, nothing new in the project file):
 *   layer.pcAdj = { type:'colourway', p:{ cw:{ v, act, name, pal:[{hex,role,name,cov,implicit}], to:[hex per palette entry], lib:[saved variants],
 *                  zb:[the zones' ORIGINAL colour / finish fields], prot:[protected layer ids], inc } } }
 *   layer.pcMask = the protect mask (white = recolour, black = sponsor / logo art that shows through)
 * Undo: the app's own Ctrl+Z trail through window.SPBUndoExt, kind 'rev-colourway': ONE step for layer + mask + zones.
 * The WebGL adjustment path has no shader for a palette map, so only this layer is routed through pc-adjust's documented CPU path
 * (window.SPB_TLAY_ADJ_CPU is raised for the duration of this layer's draw only).
 * Kill switch: window.SPB_REV_COLOURWAY_OFF = true, or localStorage SPB_REV_COLOURWAY_OFF = '1' (no type, no menu entry, no wrapper).
 */
(function (root) {
    'use strict';
    if (!root || root.SPBRevColourway) return;
    var doc = root.document;
    function off() {
        if (root.SPB_REV_COLOURWAY_OFF) return true;
        try { return root.localStorage && root.localStorage.getItem('SPB_REV_COLOURWAY_OFF') === '1'; } catch (_) { return false; }
    }
    if (off()) { root.SPBRevColourway = { off: true }; return; }
    var MA = root.SPBRevColourwayMath;
    if (!MA) { root.SPBRevColourway = { off: true, why: 'math missing' }; return; }
    var KIND = 'rev-colourway', TYPE = 'colourway';

    // ------------------------------------------------------------------ small helpers
    function toast(msg, isErr) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!isErr); } catch (_) {} }
    function mk(w, h) { var c = doc.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }
    function ctx2(c) { return c.getContext('2d', { willReadFrequently: true }); }
    function dims() { var pc = doc.getElementById('paintCanvas'); return { w: pc ? pc.width : 2048, h: pc ? pc.height : 2048 }; }
    function layers() { try { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; } catch (_) { return []; } }
    function zlist() { try { return (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : []; } catch (_) { return []; } }
    function clone(o) { return o === undefined ? undefined : JSON.parse(JSON.stringify(o)); }
    function deepFreeze(o) { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.keys(o).forEach(function (k) { deepFreeze(o[k]); }); Object.freeze(o); } return o; }
    function isCw(l) { return !!(l && l.pcAdj && l.pcAdj.type === TYPE); }
    function cwLayer() { var ls = layers(); for (var i = 0; i < ls.length; i++) if (isCw(ls[i])) return ls[i]; return null; }
    function isHex(h) { return MA.isHex(h); }
    function helperLayer(l) {
        var n = String((l && l.name) || ''), g = String((l && l.groupName) || '');
        return /^\s*(mask|wire|wireframe)\b/i.test(n) || /mandatory/i.test(n) || /turn off|before exporting/i.test(g);
    }

    // ------------------------------------------------------------------ the cw parameter object
    var EMPTY = { v: 1, act: 'orig', name: 'Original', pal: [], to: [], lib: [], zb: null, zk: [], zh: {}, prot: [], inc: false };
    function cleanCw(x) {
        if (!x || typeof x !== 'object') return null;
        var pal = (Array.isArray(x.pal) ? x.pal : []).filter(function (c) { return c && isHex(c.hex); }).slice(0, 12).map(function (c) {
            return { hex: String(c.hex).toLowerCase(), role: String(c.role || 'detail').slice(0, 12), name: String(c.name || '').slice(0, 24), cov: +c.cov || 0, implicit: !!c.implicit };
        });
        var to = (Array.isArray(x.to) ? x.to : []).slice(0, pal.length).map(function (h, i) { return isHex(h) ? String(h).toLowerCase() : pal[i].hex; });
        while (to.length < pal.length) to.push(pal[to.length].hex);
        var lib = (Array.isArray(x.lib) ? x.lib : []).slice(0, 24).map(function (v) {
            if (!v || !Array.isArray(v.to)) return null;
            return { id: String(v.id || ('u' + Math.random().toString(36).slice(2, 7))).slice(0, 24), name: String(v.name || 'Colourway').slice(0, 40), harmony: String(v.harmony || '').slice(0, 20),
                to: v.to.slice(0, pal.length).map(function (h, i) { return isHex(h) ? String(h).toLowerCase() : pal[i].hex; }), mats: v.mats && typeof v.mats === 'object' ? clone(v.mats) : {}, saved: true };
        }).filter(Boolean);
        var zb = Array.isArray(x.zb) ? clone(x.zb).slice(0, 64) : null;
        var prot = (Array.isArray(x.prot) ? x.prot : []).map(String).slice(0, 64);
        var zk = (Array.isArray(x.zk) ? x.zk : []).map(String).slice(0, 64);
        var zh = {}; if (x.zh && typeof x.zh === 'object') Object.keys(x.zh).slice(0, 64).forEach(function (k) { if (Array.isArray(x.zh[k])) zh[String(k)] = x.zh[k].map(function (v) { return v | 0; }).slice(0, 12); });
        return { v: 1, act: String(x.act || 'orig').slice(0, 24), name: String(x.name || 'Original').slice(0, 40), pal: pal, to: to, lib: lib, zb: zb, zk: zk, zh: zh, prot: prot, inc: !!x.inc };
    }
    function cwIdentity(cw) {
        if (!cw || !cw.pal || !cw.pal.length) return true;
        for (var i = 0; i < cw.pal.length; i++) if (String(cw.to[i]).toLowerCase() !== String(cw.pal[i].hex).toLowerCase()) return false;
        return true;
    }
    var mapCache = new Map();
    function mapperOf(from, to) {
        var key = from.join(',') + '>' + to.join(',');
        var m = mapCache.get(key);
        if (!m) {
            m = MA.buildMapper(from.map(function (h, i) { return { from: h, to: to[i] }; }));
            if (mapCache.size > 40) mapCache.delete(mapCache.keys().next().value);
            mapCache.set(key, m);
        }
        return m;
    }
    function mapperFor(cw) { return mapperOf(cw.pal.map(function (c) { return c.hex; }), cw.to); }

    // ------------------------------------------------------------------ the adjustment type (registered with pc-adjust)
    var registered = false;
    function register() {
        var A = root.SPBPcAdjust;
        if (registered || !A || typeof A.registerType !== 'function') return !!registered;
        var ok = A.registerType(TYPE, {
            label: 'Colourway', glyph: 'C',
            hint: 'Recolours the whole livery from a palette: every palette colour goes to its new colour and the mixes in between follow, so line work and shading stay. Open Colourway Studio (Adjust menu) to make and switch colourways.',
            params: [{ k: 'cw', label: 'Colourway', type: 'json', hidden: true, def: EMPTY, clean: cleanCw }],
            identity: function (p) { return cwIdentity(p && p.cw); },
            cpu: function (d, n, p, sa, k0) { var cw = p && p.cw; if (!cw || cwIdentity(cw)) return; MA.applyMapper(mapperFor(cw), d, n, sa, k0); },
            ui: cardUi
        }, 'gradientMap');
        registered = true;
        return ok !== false;
    }
    // pc-adjust's WebGL branch has no palette shader and would draw an identity: route THIS layer through its CPU path only
    var wrapped = false;
    function wrapDraw() {
        if (wrapped) return;
        var prev = root._drawLayerPixelContent;
        if (typeof prev !== 'function') return;
        var w = function (c, ls, idx, so) {
            var L = ls && ls[idx];
            if (L && L.pcAdj && L.pcAdj.type === TYPE && !off()) {
                var keep = root.SPB_TLAY_ADJ_CPU; root.SPB_TLAY_ADJ_CPU = true;
                try { return prev.apply(this, arguments); } finally { root.SPB_TLAY_ADJ_CPU = keep; }
            }
            return prev.apply(this, arguments);
        };
        for (var k in prev) { try { if (Object.prototype.hasOwnProperty.call(prev, k)) w[k] = prev[k]; } catch (_) {} }
        w.__cw = true;
        root._drawLayerPixelContent = w; wrapped = true;
    }

    // ------------------------------------------------------------------ composite of the livery WITHOUT any colourway layer
    function compositeSource() {
        var d = dims(), c = mk(d.w, d.h), g = ctx2(c), ls = layers();
        if (typeof root._spbCompositeLayerStack === 'function') {
            root._spbCompositeLayerStack(g, ls, { includeLayer: function (l) { return !isCw(l) && !helperLayer(l); } });
        }
        return c;
    }
    function sampleOf(canvas, S, smooth) {
        var c = mk(S, S), g = ctx2(c);
        g.imageSmoothingEnabled = !!smooth; if (smooth) g.imageSmoothingQuality = 'high';
        g.drawImage(canvas, 0, 0, canvas.width, canvas.height, 0, 0, S, S);
        return { canvas: c, id: g.getImageData(0, 0, S, S) };
    }

    // ------------------------------------------------------------------ sponsor / logo protection
    var PROT_ROLES = { 'sponsors': 1, 'decals / logos': 1 };
    function roleMap() {
        var m = {};
        try { if (root.SpbProCar && typeof root.SpbProCar.roles === 'function') root.SpbProCar.roles().forEach(function (r) { m[r.id] = r.role; }); } catch (_) {}
        return m;
    }
    function roleOfLayer(l, rm) {
        if (rm && rm[l.id]) return rm[l.id];
        var n = String(l.name || '').toLowerCase();
        if (/number/.test(n)) return 'numbers';
        if (/sponsor|contingency/.test(n)) return 'sponsors';
        if (/logo|decal|banner|sticker|badge/.test(n)) return 'decals / logos';
        return 'other art';
    }
    /** art layers the Studio lists: [{id, name, role, protectedByDefault, visible}] (template / helper layers and colourway layers left out) */
    function layerList() {
        var rm = roleMap();
        return layers().filter(function (l) { return l && l.img && !isCw(l) && !helperLayer(l) && !(l.pcAdj); }).map(function (l) {
            var role = roleOfLayer(l, rm);
            return { id: l.id, name: l.name || l.id, role: role, def: !!PROT_ROLES[role], visible: l.visible !== false };
        });
    }
    var scratch = null, sctx = null;
    function layerAlpha(ls, i, W, H) {
        if (!scratch) scratch = mk(W, H);
        if (scratch.width !== W || scratch.height !== H) { scratch.width = W; scratch.height = H; sctx = null; }
        if (!sctx) sctx = ctx2(scratch);
        sctx.setTransform(1, 0, 0, 1, 0, 0); sctx.globalAlpha = 1; sctx.globalCompositeOperation = 'source-over'; sctx.clearRect(0, 0, W, H);
        var copy = ls.slice();
        var draw = function (c, layer, li) {
            copy[li] = Object.assign({}, layer, { blendMode: 'source-over' });
            var fn = root._drawLayerPixelContent, drew = typeof fn === 'function' ? fn(c, copy, li, null) : false;
            c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; return drew;
        };
        var res = root._spbCompositeLayerStack(sctx, copy, { includeLayer: function (_l, li) { return li === i; }, identityBlend: true, drawLayer: draw });
        if (!res || !res.ok) return null;
        var d = sctx.getImageData(0, 0, W, H).data, a = new Uint8Array(W * H), any = 0;
        for (var k = 0, j = 3; k < a.length; k++, j += 4) { var v = d[j]; a[k] = v; any |= v; }
        return any ? a : null;
    }
    /** Uint8 W*H: how much of each pixel the protected layers OWN in the finished composite (alpha x what is not covered by layers above). null = none. */
    function protectOwnership(ids) {
        if (!ids || !ids.length) return null;
        var ls = layers(), d = dims(), W = d.w, H = d.h, N = W * H, occ = new Float32Array(N), own = new Float32Array(N), any = false;
        var set = {}; ids.forEach(function (id) { set[id] = 1; });
        for (var i = ls.length - 1; i >= 0; i--) {
            var l = ls[i];
            if (!l || l.visible === false || !l.img || isCw(l) || helperLayer(l) || l.pcAdj) continue;
            var a = layerAlpha(ls, i, W, H); if (!a) continue;
            var op = (l.opacity == null ? 255 : l.opacity) / 255, prot = !!set[l.id];
            for (var p = 0; p < N; p++) {
                var av = a[p]; if (!av) continue;
                var ow = (av / 255) * (1 - occ[p]); if (ow <= 0) continue;
                if (prot) { own[p] += ow; any = true; }
                occ[p] += ow;
            }
        }
        if (!any) return null;
        var out = new Uint8Array(N);
        for (var q = 0; q < N; q++) { var v = own[q]; out[q] = v >= 1 ? 255 : (v <= 0 ? 0 : Math.round(v * 255)); }
        return out;
    }
    function maskCanvasFrom(own) {   // white = recolour, black = protected art
        var d = dims(), c = mk(d.w, d.h), g = ctx2(c), id = g.createImageData(d.w, d.h), px = id.data;
        for (var i = 0, p = 0; i < own.length; i++, p += 4) { var v = 255 - own[i]; px[p] = px[p + 1] = px[p + 2] = v; px[p + 3] = 255; }
        g.putImageData(id, 0, 0); c.__pcOpaque = true; return c;
    }

    // ------------------------------------------------------------------ zones (colour-picked) follow the colours
    var ZFIELDS = ['colorMode', 'color', 'pickerColor', 'pickerTolerance', 'colors', 'base', 'finish'];
    function zoneSnap() {
        return zlist().map(function (z, i) {
            var o = { i: i, name: z && z.name }; ZFIELDS.forEach(function (k) { o[k] = clone(z[k]); }); return o;
        });
    }
    function zoneRestore(snap) {
        var zs = zlist(); if (!snap) return 0; var n = 0;
        snap.forEach(function (s) {
            var z = zs[s.i]; if (!z || (s.name != null && z.name !== s.name)) return;
            ZFIELDS.forEach(function (k) { z[k] = clone(s[k]); });
            if (z.colorMode === 'multi' && Array.isArray(z.colors)) z.color = z.colors;   // the app keeps color === colors for a multi-colour stack
            n++;
        });
        return n;
    }
    function rgbOf(h) { return MA.hex2rgb(h); }
    function zoneSpecColours(z) {   // [{rgb, tol, kind, j}] the colours this zone matches by (z: a zone or a zone snapshot)
        if (z.colorMode === 'picker' && z.pickerColor && isHex(z.pickerColor)) return [{ rgb: rgbOf(z.pickerColor), tol: z.pickerTolerance == null ? 40 : +z.pickerTolerance, kind: 'picker', j: 0 }];
        if (z.colorMode === 'multi' && Array.isArray(z.colors)) return z.colors.filter(function (c) { return c && c.color_rgb; }).map(function (c, j) { return { rgb: c.color_rgb.slice(0, 3), tol: c.tolerance == null ? 40 : +c.tolerance, kind: 'multi', j: j }; });
        return [];
    }
    /** Which zones sit on sponsor art, and which of a zone's colours ALSO occur in protected art. Pixel facts, variant independent.
     *  zk: zones that are mostly sponsor art (they do not move). zh: { zone: [colour index] } colours that keep a second life on
     *  sponsor art: the zone keeps selecting the OLD colour as well so the sponsor art keeps exactly its finish. */
    function analyseZones(zb, samp) {
        var zk = [], zh = {};
        if (!samp || !samp.prot || !samp.data) return { zk: zk, zh: zh };
        var d = samp.data, pr = samp.prot, n = pr.length;
        (zb || []).forEach(function (s) {
            var cols = zoneSpecColours(s); if (!cols.length) return;
            var tot = new Array(cols.length).fill(0), pm = new Array(cols.length).fill(0), T = 0, PM = 0;
            for (var i = 0, o = 0; i < n; i++, o += 4) {
                if (d[o + 3] < 128) continue;
                for (var c = 0; c < cols.length; c++) {
                    if (MA.zoneDist(cols[c].rgb, [d[o], d[o + 1], d[o + 2]]) < cols[c].tol * 0.5) { tot[c]++; T++; if (pr[i] > 127) { pm[c]++; PM++; } break; }
                }
            }
            if (T && PM / T > 0.5) { zk.push(s.name); return; }
            var hold = [];
            for (var k = 0; k < cols.length; k++) if (pm[k] >= 150 && tot[k] && pm[k] / tot[k] >= 0.02) hold.push(k);
            if (hold.length) zh[s.name] = hold;
        });
        return { zk: zk, zh: zh };
    }
    /** Re-aim the colour-picked zones from their ORIGINAL specs (zb) at the mapped colours; always starts from the originals, so switching
     *  between variants never compounds. A colour that also lives on protected sponsor art stays selected as well (cw.zh) unless that
     *  old colour is one of the variant's new colours (then the zone would grab the recoloured body). The tolerance is rescaled by how
     *  the map stretches colour space at that colour AND capped so the zone cannot reach the nearest OTHER palette colour's new place. */
    function followZones(cw, mapper) {
        var zs = zlist(), zb = cw.zb || [], moved = [], kept = [], held = [];
        zoneRestore(zb);
        if (!mapper || mapper.identity) return { moved: moved, kept: kept, held: held };
        var zkeep = {}; (cw.zk || []).forEach(function (n) { zkeep[n] = 1; });
        var Sx = mapper.S, Tx = mapper.T;
        function nearestOther(old, nw) {   // distance from the NEW colour to the new places of every palette colour except the one the old colour belongs to
            var jb = -1, bd = 1e9, k;
            for (k = 0; k < Sx.length; k++) { var dd = MA.zoneDist(old, Sx[k]); if (dd < bd) { bd = dd; jb = k; } }
            var m = 1e9; for (k = 0; k < Tx.length; k++) { if (k === jb) continue; var d2 = MA.zoneDist(nw, Tx[k]); if (d2 < m) m = d2; }
            return m;
        }
        function collides(old, tol) {      // would the OLD colour (tol) grab any of the variant's new colours?
            for (var k = 0; k < Tx.length; k++) if (MA.zoneDist(old, Tx[k]) < tol + 14) return true; return false;
        }
        zb.forEach(function (s) {
            var z = zs[s.i]; if (!z || z.name !== s.name) return;
            var cols = zoneSpecColours(z); if (!cols.length) return;
            if (zkeep[z.name]) { kept.push({ zone: z.name, why: 'sponsor art' }); return; }
            var holdIdx = (cw.zh && cw.zh[z.name]) || [], changed = false, extra = [];
            cols.forEach(function (c) {
                var m = mapper.map(c.rgb[0], c.rgb[1], c.rgb[2]).map(Math.round), sc = MA.localScale(mapper, c.rgb);
                if (Math.abs(m[0] - c.rgb[0]) + Math.abs(m[1] - c.rgb[1]) + Math.abs(m[2] - c.rgb[2]) < 6) return;
                var cap = 0.9 * nearestOther(c.rgb, m);
                var tol = Math.max(3, Math.min(140, Math.round(Math.min(c.tol * sc, cap)))), hex = MA.rgb2hex(m[0], m[1], m[2]);
                if (c.kind === 'picker') { z.pickerColor = hex; z.pickerTolerance = tol; z.color = { color_rgb: m, tolerance: tol }; }
                else { var e = z.colors[c.j]; e.color_rgb = m; e.hex = hex; e.tolerance = tol; z.color = z.colors; if (c.j === 0) z.pickerColor = hex; }
                changed = true;
                if (holdIdx.indexOf(c.j) >= 0) {
                    if (collides(c.rgb, c.tol)) held.push({ zone: z.name, why: 'old colour is a new colour of this variant', held: false });
                    else extra.push({ color_rgb: c.rgb.slice(0, 3), tolerance: c.tol, hex: MA.rgb2hex(c.rgb[0], c.rgb[1], c.rgb[2]) });
                }
            });
            if (extra.length) {
                if (z.colorMode === 'picker') {   // a picker zone becomes a two-colour stack: [new colour, old colour kept for the sponsor art]
                    var first = { color_rgb: z.color.color_rgb.slice(0, 3), tolerance: z.color.tolerance, hex: z.pickerColor };
                    z.colors = [first].concat(extra); z.colorMode = 'multi'; z.color = z.colors;
                } else { extra.forEach(function (x) { z.colors.push(x); }); z.color = z.colors; }
                held.push({ zone: z.name, held: true, n: extra.length });
            }
            if (changed) moved.push({ zone: z.name, mode: z.colorMode });
        });
        return { moved: moved, kept: kept, held: held };
    }
    var MAT_RX = { candy: /candy/i, pearl: /pearl/i, chrome: /^chrome|chrome_/i, matte: /^matte/i, satin: /^satin/i, gloss: /^gloss/i };
    function materialId(kind) {
        var rx = MAT_RX[kind] || new RegExp('^' + String(kind).replace(/[^a-z0-9_]/gi, '') + '$', 'i'); if (!kind) return null;
        try {
            var list = (typeof BASES !== 'undefined' && Array.isArray(BASES)) ? BASES : [];
            var hit = list.find(function (b) { return b && String(b.id || '').toLowerCase() === kind; }) || list.find(function (b) { return b && String(b.name || '').toLowerCase() === kind; }) ||
                list.find(function (b) { return b && rx.test(String(b.id || '')); }) || list.find(function (b) { return b && rx.test(String(b.name || '')); });
            return hit ? { id: hit.id, name: hit.name || hit.id } : null;
        } catch (_) { return null; }
    }
    /** optional: aim each colour-picked zone's BASE at the variant's material suggestion for the role its colour plays */
    function applyMaterials(cw, variant) {
        var zs = zlist(), done = [];
        (cw.zb || []).forEach(function (s) {
            var z = zs[s.i]; if (!z || z.name !== s.name) return;
            var cols = zoneSpecColours(Object.assign({}, z, { colorMode: s.colorMode, pickerColor: s.pickerColor, pickerTolerance: s.pickerTolerance, colors: s.colors }));
            if (!cols.length) return;
            var lab = MA.rgb2lab(cols[0].rgb[0], cols[0].rgb[1], cols[0].rgb[2]), best = -1, bd = 9;
            cw.pal.forEach(function (p, i) { var dd = MA.labDist(lab, MA.hexLab(p.hex)); if (dd < bd) { bd = dd; best = i; } });
            if (best < 0 || bd > 0.14) return;
            var kind = (variant.mats || {})[cw.pal[best].role], m = kind && materialId(kind);
            if (m) { z.base = m.id; z.finish = null; done.push({ zone: z.name, role: cw.pal[best].role, base: m.name }); }
        });
        return done;
    }

    // ------------------------------------------------------------------ undo (one step for layer + mask + zones)
    var U = { undo: [], redo: [], max: 30 };
    function snap() {
        var L = cwLayer(), ls = layers();
        return { layer: L, idx: L ? ls.indexOf(L) : -1, pcAdj: L ? L.pcAdj : null, pcMask: L ? L.pcMask : null, vis: L ? L.visible !== false : true, zones: zoneSnap() };
    }
    function restore(s) {
        var ls = layers(), L = s.layer;
        if (!L) { for (var i = ls.length - 1; i >= 0; i--) if (isCw(ls[i])) ls.splice(i, 1); }
        else {
            if (ls.indexOf(L) < 0) { for (var j = ls.length - 1; j >= 0; j--) if (isCw(ls[j])) ls.splice(j, 1); ls.splice(Math.min(Math.max(s.idx, 0), ls.length), 0, L); }
            L.pcAdj = s.pcAdj; if (s.pcMask) L.pcMask = s.pcMask; else delete L.pcMask; L.visible = s.vis;
        }
        zoneRestore(s.zones);
        redraw(true);
    }
    var kickT = 0;
    function kickPreview() {
        clearTimeout(kickT);
        kickT = setTimeout(function () { try { if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); else if (typeof root.triggerPreviewRender === 'function') root.triggerPreviewRender(); } catch (_) {} }, 350);
    }
    function redraw(structure) {
        root._spbLayerRev = (root._spbLayerRev | 0) + 1;
        try { if (typeof root.recompositeFromLayers === 'function') root.recompositeFromLayers(); } catch (e) { console.warn('[colourway] recomposite', e); }
        try { if (typeof root.renderLayerPanel === 'function') root.renderLayerPanel(); } catch (_) {}
        try { if (typeof root.renderZones === 'function') root.renderZones(); } catch (_) {}
        listeners.forEach(function (f) { try { f('change'); } catch (_) {} });
        kickPreview();
    }
    function pushUndo(label, before, after) {
        U.undo.push({ label: label, before: before, after: after }); if (U.undo.length > U.max) U.undo.shift(); U.redo.length = 0;
        if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND);
    }
    function undoStep() { var e = U.undo.pop(); if (!e) return false; restore(e.before); U.redo.push(e); return true; }
    function redoStep() { var e = U.redo.pop(); if (!e) return false; restore(e.after); U.undo.push(e); return true; }
    function registerUndo() {
        if (!root.SPBUndoExt) {
            var reg = Object.create(null);
            root.SPBUndoExt = {
                register: function (kind, impl) { reg[kind] = impl; },
                owns: function (kind) { return !root.SPB_UNDOEXT_OFF && !!reg[kind]; },
                has: function (kind, which) { var r = reg[kind]; if (!r || root.SPB_UNDOEXT_OFF) return false; try { return which === 'redo' ? !!r.hasRedo() : !!r.hasUndo(); } catch (_) { return false; } },
                undo: function (kind) { var r = reg[kind]; try { return !!(r && r.undo()); } catch (e) { return false; } },
                redo: function (kind) { var r = reg[kind]; try { return !!(r && r.redo()); } catch (e) { return false; } },
                clearRedo: function () { for (var k in reg) { try { if (reg[k].clearRedo) reg[k].clearRedo(); } catch (_) {} } },
                label: function (kind) { var r = reg[kind]; try { return r && r.label ? String(r.label() || '') : ''; } catch (_) { return ''; } }
            };
        }
        root.SPBUndoExt.register(KIND, {
            hasUndo: function () { return U.undo.length > 0; }, hasRedo: function () { return U.redo.length > 0; }, undo: undoStep, redo: redoStep,
            clearRedo: function () { U.redo.length = 0; }, label: function () { var e = U.undo[U.undo.length - 1]; return e ? e.label : 'Colourway'; }
        });
    }

    // ------------------------------------------------------------------ session (Studio open) and applying a variant
    var listeners = [];
    var S = null;   // { base: snapshot, pal, vars, team, prot:Set, inc, src, thumb, prev, protOwn, sampleData, ... }
    function frozenAdj(cw) { return Object.freeze({ type: TYPE, p: Object.freeze({ cw: deepFreeze(clone(cw)) }) }); }
    function curCw() { var L = cwLayer(); return L && L.pcAdj ? L.pcAdj.p.cw : null; }
    function insertIndex(protIds) {
        var ls = layers(), top = -1, lowProt = -1, set = {}; protIds.forEach(function (id) { set[id] = 1; });
        for (var i = 0; i < ls.length; i++) {
            var l = ls[i]; if (!l || helperLayer(l) || isCw(l)) continue;
            top = i;
            if (set[l.id] && lowProt < 0) lowProt = i;
        }
        // every non-protected art layer sits below the lowest protected one: the colourway goes right under the sponsors and needs no mask
        var anyAbove = false;
        if (lowProt >= 0) for (var j = lowProt + 1; j < ls.length; j++) { var m = ls[j]; if (m && !helperLayer(m) && !isCw(m) && !set[m.id] && m.visible !== false) { anyAbove = true; break; } }
        if (lowProt >= 0 && !anyAbove) return { at: lowProt, mask: false };
        return { at: top + 1, mask: lowProt >= 0 };
    }
    function ensureLayer(cw, protIds, protOwn) {
        var ls = layers(), L = cwLayer(), plan = insertIndex(protIds), d = dims();
        if (!L) {
            var ref = ls[Math.max(0, plan.at - 1)];
            L = { id: 'cw_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6), name: 'Colourway', path: '', visible: true, opacity: 255, blendMode: 'source-over', locked: false, alphaLock: false, clippingMask: false, effects: null, bbox: [0, 0, d.w, d.h], img: mk(d.w, d.h) };
            if (ref) { if (ref.groupName != null) L.groupName = ref.groupName; if (ref.groupChain) L.groupChain = ref.groupChain; if (ref.path) L.path = ref.path; if (ref.parentGroupKey != null) L.parentGroupKey = ref.parentGroupKey; }
            ls.splice(plan.at, 0, L);
            root._psdLayersLoaded = true;
        }
        L.pcAdj = frozenAdj(cw);
        // protect mask: white = recolour, black = sponsor / logo art that keeps its brand colours
        var A = root.SPBPcLayerMask;
        if (plan.mask && protOwn && A && typeof A.add === 'function') {
            if (!L.pcMask) A.add(L.id, 'reveal', true);
            if (L.pcMask) {
                var m = L.pcMask, c = maskCanvasFrom(protOwn);
                L.pcMask = Object.freeze(Object.assign({}, m, { c: c, enabled: true, density: 1, feather: 0, def: 255 }));
            }
        } else if (L.pcMask) delete L.pcMask;
        return L;
    }
    function protIdsOf(st) { return st.inc ? [] : Array.from(st.prot); }
    function baseCw(st) {
        var cur = curCw();
        return {
            v: 1, act: 'orig', name: 'Original', pal: st.pal.map(function (c) { return { hex: c.hex, role: c.role, name: c.name, cov: Math.round(c.cov * 1000) / 1000, implicit: !!c.implicit }; }),
            to: st.pal.map(function (c) { return c.hex; }), lib: cur ? clone(cur.lib) : [], zb: st.zb, zk: st.zk || [], zh: st.zh || {}, prot: Array.from(st.prot), inc: !!st.inc
        };
    }
    function sampleKeep(st) {   // palette pixels = real art pixels (alpha), not sponsor art
        var S1 = st.srcS, n = S1.id.width * S1.id.height, keep = new Uint8Array(n), pr = st.protS;
        for (var i = 0; i < n; i++) keep[i] = (pr && pr[i] > 127) ? 0 : 1;
        return keep;
    }
    /** Open a session: read the livery as it is now (without any colourway), find its palette, build the variants. */
    function open(opts) {
        opts = opts || {};
        var ls = layers();
        if (!ls.length) { toast('Colourway Studio needs a layered paint (a PSD or a project with layers).', true); return null; }
        register(); wrapDraw();
        var t0 = performance.now();
        var cur = curCw();
        var st = { base: snap(), team: [], vars: [], thumbs: {}, activeId: cur ? cur.act : 'orig', t: {} };
        var list = layerList();
        st.prot = new Set(cur && cur.prot && cur.prot.length ? cur.prot : list.filter(function (l) { return l.def; }).map(function (l) { return l.id; }));
        st.inc = cur ? !!cur.inc : false;
        // the "original" look: when a colourway is active, show/measure the livery with it switched off
        var L0 = cwLayer(), hadVis = L0 ? L0.visible : true;
        if (L0) L0.visible = false;
        try { st.comp = compositeSource(); } finally { if (L0) L0.visible = hadVis; }
        st.zb = (cur && cur.zb) ? clone(cur.zb) : zoneSnap().filter(function (z) { return z.colorMode === 'picker' || z.colorMode === 'multi' || z.base || z.finish; });
        // zb must keep every zone's identity even when it carries no colours: only zones with colour fields are re-aimed
        st.protOwnFull = null;
        st.srcS = sampleOf(st.comp, 512, false);
        st.t.composite = performance.now() - t0;
        S = st;
        refreshProtection(true);
        runExtract();
        analyse();
        st.t.total = performance.now() - t0;
        return st;
    }
    function refreshProtection(force) {
        if (!S) return;
        var ids = protIdsOf(S), key = ids.slice().sort().join('|') + '#' + (root._spbLayerRev | 0);
        if (!force && S.protKey === key) return;
        var t0 = performance.now(), own = ids.length ? protectOwnership(ids) : null;
        S.protOwnFull = own; S.protKey = key;
        var n512 = 512 * 512, pr = new Uint8Array(n512), d = dims();
        if (own) for (var y = 0; y < 512; y++) for (var x = 0; x < 512; x++) pr[y * 512 + x] = own[(y * d.h / 512 | 0) * d.w + (x * d.w / 512 | 0)];
        S.protS = own ? pr : null;
        S.t.protect = performance.now() - t0;
    }
    function analyse() {
        if (!S) return;
        var r = analyseZones(S.zb, S.protS ? { data: S.srcS.id.data, prot: S.protS } : null);
        S.zk = r.zk; S.zh = r.zh;
    }
    function runExtract() {
        var keep = sampleKeep(S), ex = MA.extract(S.srcS.id.data, 512 * 512, keep, {});
        S.pal = ex.colours; S.total = ex.total;
        var cur = curCw();
        if (cur && cur.pal.length) {   // an applied colourway keeps ITS palette (the livery as it was when the colourway was made)
            S.pal = cur.pal.map(function (c) { return { hex: c.hex, role: c.role, name: c.name, cov: c.cov, implicit: c.implicit, lab: MA.hexLab(c.hex), L: MA.hexLab(c.hex)[0], neutral: c.role === 'ink' || c.role === 'paper' || c.role === 'grey' }; });
        }
        buildVariants();
    }
    function buildVariants() {
        var cur = curCw(), gen = MA.variants(S.pal, S.team);
        gen.forEach(function (v) { v.saved = false; });
        var lib = (cur && cur.lib ? cur.lib : []).filter(function (v) { return v.to && v.to.length === S.pal.length; }).map(function (v) { return Object.assign({}, v, { saved: true }); });
        S.lib = lib; S.gen = gen;
        S.vars = [{ id: 'orig', name: 'Original', harmony: 'original', to: S.pal.map(function (c) { return c.hex; }), mats: {}, saved: false }].concat(gen, lib);
        S.thumbs = {};
    }
    function variantById(id) { if (!S) return null; for (var i = 0; i < S.vars.length; i++) if (S.vars[i].id === id) return S.vars[i]; return null; }
    function setTeam(arr) { if (!S) return; S.team = (arr || []).filter(isHex); buildVariants(); }
    function setProtected(ids, inc) {
        if (!S) return; S.prot = new Set(ids || []); S.inc = !!inc; refreshProtection(true);
        analyse();
        if (S.activeId && S.activeId !== 'orig') setVariant(S.activeId, { keepMats: true });
        listeners.forEach(function (f) { try { f('protect'); } catch (_) {} });
    }
    /** Apply a variant to the livery, live (no undo step yet: the session commits or cancels). */
    function setVariant(id, o) {
        o = o || {};
        if (!S) return null;
        var v = variantById(id); if (!v) return null;
        var cw = baseCw(S), prevCur = curCw();
        cw.act = v.id; cw.name = v.name; cw.to = v.to.slice();
        cw.lib = (S.lib || []).map(function (x) { return { id: x.id, name: x.name, harmony: x.harmony, to: x.to, mats: x.mats || {} }; });
        var protIds = protIdsOf(S);
        // zones: a mapper from the palette -> this variant
        var mapper = mapperFor(cw);
        var zr = followZones(cw, mapper);
        var L = ensureLayer(cw, protIds, S.protOwnFull);
        var mats = [];
        if (S.matsOn && v.mats) mats = applyMaterials(cw, v);
        S.activeId = v.id; S.lastZones = zr; S.lastMats = mats;
        redraw(true);
        return { layer: L && L.id, zones: zr, mats: mats };
    }
    function saveVariant(name) {
        if (!S) return null;
        var v = variantById(S.activeId); if (!v || v.id === 'orig') { toast('Pick a colourway first, then save it.', true); return null; }
        name = String(name || '').trim().slice(0, 40) || (v.name + ' (saved)');
        var id = 'u' + Date.now().toString(36);
        var rec = { id: id, name: name, harmony: v.harmony, to: v.to.slice(), mats: clone(v.mats || {}), saved: true };
        S.lib.push(rec); S.vars.push(rec);
        S.activeId = id;
        setVariant(id);
        return rec;
    }
    function deleteVariant(id) {
        if (!S) return false;
        var i = S.lib.findIndex(function (v) { return v.id === id; }); if (i < 0) return false;
        S.lib.splice(i, 1); S.vars = S.vars.filter(function (v) { return v.id !== id; });
        if (S.activeId === id) setVariant('orig'); else setVariant(S.activeId);
        return true;
    }
    function renameVariant(id, name) {
        if (!S) return false; var v = variantById(id); if (!v || !v.saved) return false;
        v.name = String(name || '').trim().slice(0, 40) || v.name; if (S.activeId === id) setVariant(id); return true;
    }
    function close(keep) {
        if (!S) return { changed: false };
        var st = S, res = { changed: false };
        if (keep) {
            // an Original colourway with nothing saved leaves no trace: the layer goes away and the zones come back
            var L = cwLayer(), cw = L && L.pcAdj ? L.pcAdj.p.cw : null;
            if (cw && cwIdentity(cw) && !(cw.lib && cw.lib.length)) {
                zoneRestore(cw.zb); var ls = layers(); var ix = ls.indexOf(L); if (ix >= 0) ls.splice(ix, 1);
                redraw(true);
            }
            var after = snap();
            res.changed = !sameSnap(st.base, after);
            if (res.changed) pushUndo(after.layer ? ('Colourway: ' + (cw && cw.name || 'Original')) : 'Remove Colourway', st.base, after);
        } else {
            restore(st.base);
        }
        S = null;
        listeners.forEach(function (f) { try { f('close'); } catch (_) {} });
        return res;
    }
    function sameSnap(a, b) {
        if (a.layer !== b.layer || a.pcAdj !== b.pcAdj || a.pcMask !== b.pcMask || a.vis !== b.vis || a.idx !== b.idx) return false;
        return JSON.stringify(a.zones) === JSON.stringify(b.zones);
    }
    /** Switch the applied colourway outside the Studio (layer card, API): one undo step. */
    function switchTo(id) {
        var L = cwLayer(), cw = L && L.pcAdj && L.pcAdj.p.cw; if (!cw) return false;
        var v = null;
        if (id === 'orig') v = { id: 'orig', name: 'Original', to: cw.pal.map(function (c) { return c.hex; }), mats: {} };
        else v = (cw.lib || []).find(function (x) { return x.id === id; });
        if (!v) return false;
        var before = snap(), ncw = clone(cw); ncw.act = v.id; ncw.name = v.name; ncw.to = v.to.slice();
        L.pcAdj = frozenAdj(ncw);
        followZones(ncw, mapperFor(ncw));
        redraw(true);
        pushUndo('Colourway: ' + v.name, before, snap());
        return true;
    }

    // ------------------------------------------------------------------ thumbnails + the big preview (client side, downscaled)
    function ensureThumbBase(S2) {
        if (S2.thumbBase) return;
        var T = 256, sm = sampleOf(S2.comp, T, true), pr = null;
        if (S2.protOwnFull) {
            var d = dims(); pr = new Uint8Array(T * T);
            for (var y = 0; y < T; y++) for (var x = 0; x < T; x++) pr[y * T + x] = S2.protOwnFull[(y * d.h / T | 0) * d.w + (x * d.w / T | 0)];
        }
        S2.thumbBase = { id: sm.id, T: T, strength: pr ? pr.map(function (v) { return 255 - v; }) : null };
    }
    function paintInto(canvas, base, T, strength, to) {
        var g = ctx2(canvas); canvas.width = T; canvas.height = T;
        var id = new ImageData(new Uint8ClampedArray(base.data), T, T);
        var mapper = mapperOf(S.pal.map(function (c) { return c.hex; }), to);
        if (!mapper.identity) MA.applyMapper(mapper, id.data, T * T, strength, 1);
        g.fillStyle = '#26262b'; g.fillRect(0, 0, T, T);
        var tmp = mk(T, T); ctx2(tmp).putImageData(id, 0, 0); g.drawImage(tmp, 0, 0);
        return canvas;
    }
    function thumbFor(id, canvas) {
        if (!S) return null; var v = variantById(id); if (!v) return null;
        if (S.protKeyThumb !== S.protKey) { S.thumbBase = null; S.protKeyThumb = S.protKey; }
        ensureThumbBase(S);
        return paintInto(canvas || mk(256, 256), S.thumbBase.id, S.thumbBase.T, S.thumbBase.strength, v.to);
    }
    function previewFor(id, canvas, size) {
        if (!S) return null; var v = variantById(id); if (!v) return null;
        size = size || 720;
        if (!S.prevBase || S.prevBase.T !== size || S.prevBase.key !== S.protKey) {
            var sm = sampleOf(S.comp, size, true), pr = null;
            if (S.protOwnFull) { var d = dims(); pr = new Uint8Array(size * size); for (var y = 0; y < size; y++) for (var x = 0; x < size; x++) pr[y * size + x] = 255 - S.protOwnFull[(y * d.h / size | 0) * d.w + (x * d.w / size | 0)]; }
            S.prevBase = { id: sm.id, T: size, strength: pr, key: S.protKey };
        }
        return paintInto(canvas || mk(size, size), S.prevBase.id, size, S.prevBase.strength, v.to);
    }

    /** change the role of one palette entry (main / accent / trim / detail): the harmony variants are rebuilt around it */
    function setRole(i, role) {
        if (!S || !S.pal[i] || !/^(main|accent|trim|detail)$/.test(role)) return false;
        if (role !== 'detail') S.pal.forEach(function (c, k) { if (k !== i && c.role === role) c.role = 'detail'; });
        S.pal[i].role = role; var keep = S.activeId; buildVariants();
        if (keep && variantById(keep)) setVariant(keep); else setVariant('orig');
        return true;
    }
    /** set ONE colour of the active variant by hand: becomes a "Custom" variant (Save As Variant keeps it) */
    function editColour(i, hex) {
        if (!S || !S.pal[i] || !isHex(hex)) return null;
        var src = variantById(S.activeId) || S.vars[0], to = src.to.slice(); to[i] = String(hex).toLowerCase();
        var v = variantById('custom');
        if (!v) { v = { id: 'custom', name: 'Custom', harmony: 'custom', mats: {}, saved: false }; S.vars.push(v); }
        v.to = to; v.mats = clone(src.mats || {}); S.thumbs = {};
        return setVariant('custom') && v;
    }

    // ------------------------------------------------------------------ layer-card UI (the adjustment layer's own rows)
    function swatch(hex, title) {
        var s = doc.createElement('i'); s.style.cssText = 'display:inline-block;width:14px;height:14px;border-radius:3px;border:1px solid rgba(255,255,255,.2);background:' + hex + ';vertical-align:middle;flex:0 0 14px;'; if (title) s.title = title; return s;
    }
    function cardUi(L, rows) {
        // block layout with inline styles only: the layer card's own CSS spreads flex children, so every group below is its own block / inline-flex pair
        var cw = L.pcAdj && L.pcAdj.p.cw; if (!cw) return;
        var row = doc.createElement('div'); row.style.cssText = 'display:block;margin:0 0 6px;min-width:0;max-width:100%;box-sizing:border-box;';
        row.setAttribute('data-cw-card', L.id);
        var nm = doc.createElement('div'); nm.style.cssText = 'display:block;font-size:10px;color:#ddd;margin:0 0 4px;white-space:normal;overflow-wrap:anywhere;';
        nm.textContent = (cw.pal.length ? cw.name : 'No palette yet') + (cw.pal.length ? ' - ' + cw.pal.length + ' colours' : ''); row.appendChild(nm);
        var chips = doc.createElement('div'); chips.style.cssText = 'display:flex;flex-wrap:wrap;justify-content:flex-start;align-items:center;gap:4px 10px;margin:0 0 5px;';
        cw.pal.forEach(function (c, i) {
            if (c.implicit && c.hex === cw.to[i]) return;
            var pair = doc.createElement('span'); pair.style.cssText = 'display:inline-flex;align-items:center;gap:3px;flex:0 0 auto;';
            pair.appendChild(swatch(c.hex, c.name + ' (' + c.role + ')'));
            var ar = doc.createElement('span'); ar.textContent = '>'; ar.style.cssText = 'font-size:9px;color:#888;'; pair.appendChild(ar);
            pair.appendChild(swatch(cw.to[i], 'now ' + cw.to[i])); chips.appendChild(pair);
        });
        row.appendChild(chips);
        var lib = cw.lib || [];
        if (lib.length || (cw.act && cw.act !== 'orig')) {
            var sel = doc.createElement('select'); sel.style.cssText = 'display:block;width:100%;min-width:100%;box-sizing:border-box;font-size:10px;height:22px;background:#17171a;color:#e8e8ea;border:1px solid #3a3a42;border-radius:4px;margin:0 0 4px;';
            sel.setAttribute('aria-label', 'Switch colourway');
            var opts = [{ id: 'orig', name: 'Original' }].concat(lib);
            if (cw.act && cw.act !== 'orig' && !lib.some(function (v) { return v.id === cw.act; })) opts.push({ id: cw.act, name: (cw.name || 'Colourway') + ' (not saved)' });
            opts.forEach(function (v) { var o = doc.createElement('option'); o.value = v.id; o.textContent = v.name; if (v.id === cw.act) o.selected = true; sel.appendChild(o); });
            sel.addEventListener('change', function (ev) { ev.stopPropagation(); if (sel.value !== cw.act) switchTo(sel.value); }); sel.addEventListener('click', function (ev) { ev.stopPropagation(); });
            row.appendChild(sel);
        }
        // a div, not a <button>: the layer card's CSS squeezes any <button> in a detail row to an icon square (and spb-perf1-client reads .layer-act-btn rows as button groups)
        var b = doc.createElement('div'); b.setAttribute('role', 'button'); b.tabIndex = 0; b.className = 'spb-cw-cardbtn'; b.textContent = 'Open Colourway Studio';
        b.style.cssText = 'display:block;width:100%;min-width:100%;box-sizing:border-box;font-size:10px;line-height:16px;padding:3px 6px;text-align:center;background:#1a1a1a;color:#ccc;border:1px solid #444;border-radius:3px;cursor:pointer;';
        var go = function (ev) { ev.stopPropagation(); ev.preventDefault(); if (root.SPBRevColourwayUI) root.SPBRevColourwayUI.open(); };
        b.addEventListener('click', go); b.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') go(ev); });
        row.appendChild(b);
        // the framework's own Reset / Apply-down buttons would leave the zones retargeted (Reset) or bake into ONE layer only (Apply down):
        // Reset becomes "Original" (colours AND zones back, saved colourways stay, one undo step); Apply-down is hidden
        rows.forEach(function (r) {
            var rb = r.querySelector && r.querySelector('[data-pca="reset"]'), bb = r.querySelector && r.querySelector('[data-pca="bake"]');
            if (rb) {
                rb.removeAttribute('data-pca'); rb.textContent = 'Original'; rb.title = 'Back to the original colours and zones (your saved colourways stay)';
                rb.addEventListener('click', function (ev) { ev.stopPropagation(); ev.preventDefault(); if (cw.act !== 'orig') switchTo('orig'); });
            }
            if (bb) { bb.removeAttribute('data-pca'); bb.style.display = 'none'; }
        });
        rows.push(row);
    }

    // ------------------------------------------------------------------ boot + public API
    function boot() {
        var tries = 0;
        function tick() {
            register(); wrapDraw();
            if ((registered && wrapped) || ++tries > 80) { clearInterval(iv); }
        }
        var iv = setInterval(tick, 500); tick();
        registerUndo();
    }
    root.SPBRevColourway = {
        version: 'cw-1', KIND: KIND, isOff: off, open: open, close: close, state: function () { return S; }, active: function () { return !!S; },
        setVariant: setVariant, saveVariant: saveVariant, deleteVariant: deleteVariant, renameVariant: renameVariant, switchTo: switchTo, setTeam: setTeam,
        setProtected: setProtected, setRole: setRole, editColour: editColour, refreshProtection: refreshProtection, layerList: layerList, layer: cwLayer, current: curCw, variantById: variantById,
        thumbFor: thumbFor, previewFor: previewFor, materialId: materialId, setMaterials: function (on) { if (S) S.matsOn = !!on; },
        on: function (f) { listeners.push(f); }, mapperOf: mapperOf, mapperFor: mapperFor, isCw: isCw, snap: snap, restore: restore, undoSteps: function () { return U.undo.length; },
        _undo: U, _protectOwnership: protectOwnership, _zoneSnap: zoneSnap, _compositeSource: compositeSource, _helper: helperLayer
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot); else boot();
})(typeof window !== 'undefined' ? window : null);
