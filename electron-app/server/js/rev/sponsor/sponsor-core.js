/* sponsor-core.js - [SPB-REV-SPONSOR 2026-10-10] SPONSOR KIT: one cleaned logo, placed on every part of the car you pick, turned to read right ON THE CAR,
 * the same physical size everywhere, as normal live layers that stay linked.
 *
 * The car map only names: left / right side, hood, roof, trunk (or bed), bumpers. Door, rear quarter, TV panel and roof rail are DERIVED here:
 *   - sides:  wheel arches (SpbProCar.sideGeom, or borrowed through the Symmetry left<->right registration) give the door; the tail end is the end the car map
 *             does not call the front; rear quarter = door's rear edge -> tail end; TV panel = the strip under the roof line across the door's rear part.
 *   - hood / deck / roof rails: mask extents along and across the car (nose vector as in Number Kit), reading frame chosen like a person standing at the nose (hood),
 *             behind the car (deck) or at the driver / passenger door (rails).
 * Physical size: every part has its own px-per-cm (sides from the wheelbase between the arch centres, hood / deck / roof from the width of the part), so
 * "Size" is one number (area-based, so a banner and a badge weigh the same) and the logo is the same real size on the door and on the hood.
 * Everything is additive. Kill switch: window.SPB_REV_SPONSOR_OFF = true (or localStorage SPB_REV_SPONSOR_OFF = '1').
 * Uses only other tools' public APIs: SpbProCar, SpbRevSym, SPBRevLayerMat (optional), the layer stack, SpbRevSponsorClean.
 */
(function (root) {
    'use strict';
    if (root.SpbRevSponsor) return;
    var doc = root.document;
    var VER = 'sp1.0', TAG = '[SPB-REV-SPONSOR]', KEY = '__spbSponsorKit';
    var CM = { wheelbase: 279, hood: 140, deck: 125, roof: 120, bodyFallback: 470 };      // model constants (cm), see DESIGN.md
    var SLOTS = [
        { id: 'door_l', label: 'Left Door', part: 'left side', kind: 'side', side: 'left' },
        { id: 'door_r', label: 'Right Door', part: 'right side', kind: 'side', side: 'right' },
        { id: 'quarter_l', label: 'Left Rear Quarter', part: 'left side', kind: 'side', side: 'left' },
        { id: 'quarter_r', label: 'Right Rear Quarter', part: 'right side', kind: 'side', side: 'right' },
        { id: 'tv_l', label: 'Left TV Panel', part: 'left side', kind: 'side', side: 'left' },
        { id: 'tv_r', label: 'Right TV Panel', part: 'right side', kind: 'side', side: 'right' },
        { id: 'hood', label: 'Hood', part: 'hood', kind: 'hood' },
        { id: 'deck', label: 'Trunk / Deck', part: 'trunk', kind: 'deck' },
        { id: 'rail_l', label: 'Left Roof Rail', part: 'roof', kind: 'rail', side: 'left' },
        { id: 'rail_r', label: 'Right Roof Rail', part: 'roof', kind: 'rail', side: 'right' }
    ];
    var SLOT_BY = {}; SLOTS.forEach(function (s) { SLOT_BY[s.id] = s; });
    var MATERIALS = [['none', 'None'], ['chrome', 'Chrome Foil'], ['gold', 'Gold Leaf'], ['goldfoil', 'Gold Foil (solid)'], ['matte', 'Matte Vinyl'], ['gloss', 'Gloss Vinyl']];
    var GOLD_FINISH = 'efx_gold_leaf';
    // [SPB-REV-SPONSOR 2026-10-10] Gold Leaf = the engine's own leaf-in-sheets effect (patchy, keeps the logo's own colours underneath).  Gold Foil (solid) = a full-cover gold
    // finish for lettering / one-colour logos (real renders of both: gold_cmp_owner.png).  Both go through Layer Materials as finish coats clipped to the logo.
    var FINISH_OF = { gold: GOLD_FINISH, goldfoil: 'electroplated_gold' };

    // ------------------------------------------------------------------ plumbing
    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_REV_SPONSOR_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_REV_SPONSOR_OFF')); }
        catch (e) { return flagOn(root.SPB_REV_SPONSOR_OFF); }
    }
    function warn(where, e) { try { console.warn(TAG, where, e && e.message || e); } catch (_) {} }
    function psdLayers() { try { return (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers; } catch (e) { return root._psdLayers; } }
    function toast(msg, kind) { try { if (typeof root.showToast === 'function') root.showToast(msg, kind); } catch (e) {} }
    function call(name) { try { var f = root[name]; if (typeof f === 'function') return f.apply(root, Array.prototype.slice.call(arguments, 1)); } catch (e) { warn(name, e); } return undefined; }
    function clone(o) { return JSON.parse(JSON.stringify(o)); }
    function sheetSize() { var c = doc.getElementById('paintCanvas'); return c ? [c.width || 2048, c.height || 2048] : [2048, 2048]; }
    function mkCanvas(w, h) { var c = doc.createElement('canvas'); c.width = w; c.height = h; return c; }

    // ------------------------------------------------------------------ the kit model (settings only; the logo pixels live in LOGO[kid])
    var DEFAULTS = {
        v: 1, name: '', size: 100, material: 'none', extraTurn: 0,
        slots: { door_l: true, door_r: true, quarter_l: true, quarter_r: true, tv_l: false, tv_r: false, hood: true, deck: false, rail_l: false, rail_r: false },
        clean: { on: true, tol: 0, halo: 2, enclosed: false, bg: null }
    };
    function num(v, lo, hi, d) { v = Number(v); if (!isFinite(v)) v = d; return Math.max(lo, Math.min(hi, v)); }
    function normalize(k) {
        k = k || {}; var D = DEFAULTS, o = {}; o.v = 1;
        o.name = String(k.name == null ? D.name : k.name).replace(/[<>"]/g, '').slice(0, 40);
        o.size = num(k.size == null ? D.size : k.size, 20, 300, D.size);
        o.material = MATERIALS.some(function (m) { return m[0] === k.material; }) ? k.material : 'none';
        var et = Number(k.extraTurn); o.extraTurn = (et === 90 || et === 180 || et === 270) ? et : 0;
        o.slots = {}; var ks = k.slots || {}; SLOTS.forEach(function (s) { o.slots[s.id] = ks[s.id] == null ? !!D.slots[s.id] : !!ks[s.id]; });
        var c = k.clean || {}, bg = c.bg;
        o.clean = { on: c.on == null ? D.clean.on : !!c.on, tol: num(c.tol, 0, 80, 0), halo: Math.round(num(c.halo, 0, 4, D.clean.halo)), enclosed: !!c.enclosed,
            bg: (Array.isArray(bg) && bg.length === 3) ? bg.map(function (v) { return Math.max(0, Math.min(255, v | 0)); }) : null };
        return o;
    }

    // ------------------------------------------------------------------ measuring the car (car map + Symmetry registration)
    function SP() { return root.SpbProCar; }
    function carMap() { try { return SP() && SP().map && SP().map(); } catch (e) { return null; } }
    function boxOf(name) { var m = carMap(), b = m && m.boxes && m.boxes[name]; return b || null; }
    function hasPart(name) { try { return (SP().parts() || []).indexOf(name) >= 0; } catch (e) { return false; } }
    function hasParts() { try { return !!(SP().parts && SP().parts().length); } catch (e) { return false; } }
    function regCur() { try { var s = root.SpbRevSym; return s && !s.off() ? s.cur() : null; } catch (e) { return null; } }
    function bboxOfMask(m, W, H) {
        var x0 = W, y0 = H, x1 = -1, y1 = -1, n = 0;
        for (var y = 0; y < H; y++) { var r = y * W; for (var x = 0; x < W; x++) if (m[r + x]) { n++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
        return n ? { x0: x0, y0: y0, x1: x1, y1: y1, n: n } : null;
    }
    function dirOf(v) { return v === 'left' ? [-1, 0] : v === 'right' ? [1, 0] : v === 'top' ? [0, -1] : v === 'bottom' ? [0, 1] : null; }
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1]; }
    function snap(v) { return Math.abs(v[0]) >= Math.abs(v[1]) ? [v[0] < 0 ? -1 : 1, 0] : [0, v[1] < 0 ? -1 : 1]; }
    /** Side panel reading frame from the roof-line edge ("up"): a proper turn, never a mirror. */
    function sideFrame(which, part) {
        var b = boxOf(part) || {}, up = b.up, guess = false;
        if (!dirOf(up)) { up = which === 'left' ? 'top' : 'bottom'; guess = true; }
        var u = dirOf(up), d = [-u[0], -u[1]], r = [d[1], -d[0]];
        return { r: r, u: u, guess: guess };
    }
    function noseVector(C) {
        var m = carMap(), B = m && m.boxes || {}, cen = function (n) { var b = B[n]; return b && b.bbox ? [(b.bbox[0] + b.bbox[2]) / 2, (b.bbox[1] + b.bbox[3]) / 2] : null; };
        var hood = cen('hood'), roof = cen('roof'), rear = cen('trunk') || cen('bed') || cen('tailgate'), v = null, how = null;
        if (hood && roof) { v = [hood[0] - roof[0], hood[1] - roof[1]]; how = 'hood vs roof'; }
        else if (roof && rear) { v = [roof[0] - rear[0], roof[1] - rear[1]]; how = 'roof vs trunk'; }
        var f = null; if (v && Math.hypot(v[0], v[1]) > 0.03) f = snap(v);
        if (!f) { var fl = dirOf(B.roof && B.roof.front) || dirOf(B.hood && B.hood.front); if (fl) { f = fl; how = 'front flag'; } }
        var guess = false; if (!f) { f = [1, 0]; guess = true; how = 'assumed'; }
        try {
            var mp = C && C.maps && C.maps['roof>roof'], T = root.SpbRevSymTools && root.SpbRevSymTools._internal;
            if (mp && T && T.axisOf) { var n = T.axisOf(mp), t = [-n[1], n[0]]; if (dot(t, f) < 0) t = [-t[0], -t[1]]; if (dot(t, f) > Math.cos(15 * Math.PI / 180)) f = t; }
        } catch (e) { warn('tilt', e); }
        return { f: f, how: how, guess: guess };
    }
    function pctRange(h, lo, hi, total) {
        var a = null, b = null, acc = 0, i;
        for (i = 0; i < h.length; i++) { acc += h[i]; if (a === null && acc >= total * lo) a = i; if (acc >= total * hi) { b = i; break; } }
        return [a === null ? 0 : a, b === null ? h.length - 1 : b];
    }
    /** Extents of a mask along the nose axis f (a) and across the car l (c); l points to the DRIVER side. Percentile 2..98 so a stray corner does not stretch it. */
    function extents(m, W, H, f) {
        var bb = bboxOfMask(m, W, H); if (!bb) return null; var l = [f[1], -f[0]], OFF = 4096, ha = new Uint32Array(8192), hc = new Uint32Array(8192), n = 0;
        for (var y = bb.y0; y <= bb.y1; y++) { var r = y * W; for (var x = bb.x0; x <= bb.x1; x++) if (m[r + x]) { n++; ha[Math.round(x * f[0] + y * f[1]) + OFF]++; hc[Math.round(x * l[0] + y * l[1]) + OFF]++; } }
        var ra = pctRange(ha, 0.02, 0.98, n), rc = pctRange(hc, 0.02, 0.98, n);
        return { a0: ra[0] - OFF, a1: ra[1] - OFF, c0: rc[0] - OFF, c1: rc[1] - OFF, l: l, bb: bb };
    }
    function xyOf(f, l, a, c) { return [a * f[0] + c * l[0], a * f[1] + c * l[1]]; }

    function archesOf(part) { try { var g = SP().sideGeom(part); return g && g.arches && g.arches.length === 2 ? g.arches : null; } catch (e) { return null; } }
    function regScale(C, from, to) {            // local scale of the registration map between two parts (numeric: two points 100 px apart)
        try {
            var mp = C.maps[from + '>' + to], S = root.SpbRevSym, m = C.masks[from], bb = bboxOfMask(m, C.W, C.H), cx = (bb.x0 + bb.x1) / 2, cy = (bb.y0 + bb.y1) / 2;
            var a = S.mapPt(mp.M, cx, cy), b = S.mapPt(mp.M, cx + 100, cy), c = S.mapPt(mp.M, cx, cy + 100);
            return (Math.hypot(b[0] - a[0], b[1] - a[1]) + Math.hypot(c[0] - a[0], c[1] - a[1])) / 200;
        } catch (e) { return null; }
    }
    function localSpan(m, W, bb, xa, xb) {      // rows where >= 60% of the columns xa..xb are in the part
        xa = Math.max(bb.x0, Math.round(xa)); xb = Math.min(bb.x1, Math.round(xb)); if (xb - xa < 4) return null;
        var need = Math.max(1, Math.round((xb - xa + 1) * 0.6)), yt = -1, yb = -1;
        for (var y = bb.y0; y <= bb.y1; y++) { var n = 0, r = y * W; for (var x = xa; x <= xb; x++) if (m[r + x]) n++; if (n >= need) { if (yt < 0) yt = y; yb = y; } }
        if (yt < 0) return null; return { yt: yt, yb: yb, span: yb - yt + 1, xa: xa, xb: xb };
    }
    /** Door x-range per side: between the wheel arches; a side without measured arches borrows through the registration; last resort the library fractions. */
    function doorRanges(C) {
        var out = {}, W = C.W;
        ['left', 'right'].forEach(function (w) {
            var part = w + ' side'; if (!hasPart(part) || !C.masks[part]) return; var ar = archesOf(part), g = null; try { g = SP().sideGeom(part); } catch (e) {}
            if (ar) out[w] = { x0: ar[0][1] * W, x1: ar[1][0] * W, src: 'wheel arches', pxcm: Math.abs(((ar[1][0] + ar[1][1]) / 2 - (ar[0][0] + ar[0][1]) / 2) * W) / CM.wheelbase, arches: ar };
            else out[w] = { g: g, src: null };
        });
        ['left', 'right'].forEach(function (w) {
            var o = w === 'left' ? 'right' : 'left'; if (!out[w] || out[w].x0 != null || !out[o] || out[o].x0 == null) return;
            try {
                var mp = C.maps[o + ' side>' + w + ' side'], S = root.SpbRevSym, bbo = bboxOfMask(C.masks[o + ' side'], C.W, C.H), yc = (bbo.y0 + bbo.y1) / 2;
                var a = S.mapPt(mp.M, out[o].x0, yc), b = S.mapPt(mp.M, out[o].x1, yc), sc = regScale(C, o + ' side', w + ' side') || 1;
                out[w] = { x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), src: 'registered from the ' + o + ' side', pxcm: out[o].pxcm * sc, arches: null };
            } catch (e) { warn('door via registration', e); }
        });
        ['left', 'right'].forEach(function (w) {
            var d = out[w]; if (!d || d.x0 != null) return; var g = d.g; if (!g) { delete out[w]; return; }
            var nose = (boxOf(w + ' side') || {}).front === 'right' ? 'right' : 'left', a0 = g.x0 * W, a1 = g.x1 * W, wd = a1 - a0;
            out[w] = nose === 'right' ? { x0: a1 - 0.78 * wd, x1: a1 - 0.30 * wd, src: 'default fractions', pxcm: null } : { x0: a0 + 0.30 * wd, x1: a0 + 0.78 * wd, src: 'default fractions', pxcm: null };
        });
        return out;
    }
    function thetaOf(r, snapTo) {
        var t = Math.atan2(r[1], r[0]), q = Math.round(t / (Math.PI / 2)) * (Math.PI / 2);
        if (snapTo !== false && Math.abs(t - q) < 2 * Math.PI / 180) t = q; return t;
    }
    /** Every slot this car has. { ok, why, slots:{id:{ id,label,part,cx,cy,r,u,theta,boxW,boxH,pxcm,notes,info }}, reg } - boxW runs along the text, boxH across it (px on the sheet). */
    function measure() {
        var out = { ok: false, slots: {}, why: '', reg: null, ids: [], model: CM };
        var sz = sheetSize(); out.W = sz[0]; out.H = sz[1];
        if (!SP() || !hasParts()) { out.why = 'This paint has no car map (flat file or no template), so the car parts could not be found.'; return out; }
        var C = regCur(); if (!C) { out.why = 'The car shape is not measured yet.'; out.needBuild = true; return out; }
        out.reg = { key: C.key, W: C.W, H: C.H }; var W = C.W, H = C.H;
        var dr = doorRanges(C), pxcmSide = {}, nv = noseVector(C), f = nv.f, l = [f[1], -f[0]];
        out.nose = { how: nv.how, f: f, guess: nv.guess };
        // px per cm of each side (a side without arches borrows the other side's through the registration)
        ['left', 'right'].forEach(function (w) { if (dr[w] && dr[w].pxcm) pxcmSide[w] = dr[w].pxcm; });
        ['left', 'right'].forEach(function (w) {
            if (pxcmSide[w] || !dr[w]) return; var o = w === 'left' ? 'right' : 'left';
            if (pxcmSide[o]) pxcmSide[w] = pxcmSide[o] * (regScale(C, o + ' side', w + ' side') || 1);
        });
        // sides
        ['left', 'right'].forEach(function (w) {
            var part = w + ' side', d = dr[w], m = C.masks[part]; if (!d || !m) return; var bb = bboxOfMask(m, W, H); if (!bb) return;
            var fr = sideFrame(w, part), nose = (boxOf(part) || {}).front === 'right' ? 'right' : 'left', dirT = nose === 'left' ? 1 : -1;
            var tailX = dirT > 0 ? bb.x1 : bb.x0, doorRear = dirT > 0 ? d.x1 : d.x0, dw = Math.abs(d.x1 - d.x0), notes = [];
            var pxcm = pxcmSide[w] || ((bb.x1 - bb.x0) / CM.bodyFallback); if (!pxcmSide[w]) notes.push('Scale from the body length (the wheel arches were not measured).');
            if (fr.guess) notes.push('The car map does not say which edge of this side is the roof-line; assumed ' + (w === 'left' ? 'top' : 'bottom') + '.');
            var roofEdge = fr.u[1] < 0 ? 'top' : 'bottom';
            function slot(id, xa, xb, t, fw, fh, extra) {
                var lo = Math.min(xa, xb), hi = Math.max(xa, xb), ls = localSpan(m, W, bb, lo, hi); if (!ls || ls.xb - ls.xa < 60) return;
                var cy = roofEdge === 'bottom' ? ls.yb - t * ls.span : ls.yt + t * ls.span;
                out.slots[id] = { id: id, label: SLOT_BY[id].label, part: part, cx: (ls.xa + ls.xb) / 2, cy: cy, r: fr.r, u: fr.u, theta: thetaOf(fr.r), boxW: fw * (ls.xb - ls.xa), boxH: fh * ls.span, pxcm: pxcm,
                    notes: notes.slice(), info: Object.assign({ x: [ls.xa, ls.xb], body: [ls.yt, ls.yb], from: d.src, nose: nose }, extra || {}) };
            }
            var sfx = w === 'left' ? '_l' : '_r';
            slot('door' + sfx, d.x0, d.x1, 0.45, 0.8, 0.75);
            slot('quarter' + sfx, doorRear, tailX, 0.45, 0.9, 0.85);
            slot('tv' + sfx, doorRear - dirT * 0.42 * dw, doorRear + dirT * 0.12 * dw, 0.16, 0.9, 0.3);
        });
        // hood / deck / roof rails (nose axis f, driver direction l; text frames: hood read from the nose, deck from behind, rails from their own door)
        var ex = function (name) { var m = C.masks[name]; return m ? extents(m, W, H, f) : null; };
        var eh = hasPart('hood') ? ex('hood') : null;
        if (eh) {
            var ac = [(eh.a0 + eh.a1) / 2, (eh.c0 + eh.c1) / 2], p = xyOf(f, l, ac[0], ac[1]), acr = eh.c1 - eh.c0, pxcm = acr / CM.hood, r = l, u = [-f[0], -f[1]];
            out.slots.hood = { id: 'hood', label: 'Hood', part: 'hood', cx: p[0], cy: p[1], r: r, u: u, theta: thetaOf(r), boxW: 0.8 * acr, boxH: 0.5 * (eh.a1 - eh.a0), pxcm: pxcm, notes: [], info: { along: eh.a1 - eh.a0, across: acr, read: 'from the nose' } };
        }
        var dn = ['trunk', 'bed', 'tailgate'].filter(function (n) { return hasPart(n) && C.masks[n]; })[0], ed = dn ? ex(dn) : null;
        if (ed) {
            var ac2 = [(ed.a0 + ed.a1) / 2, (ed.c0 + ed.c1) / 2], p2 = xyOf(f, l, ac2[0], ac2[1]), acr2 = ed.c1 - ed.c0, r2 = [-l[0], -l[1]], u2 = [f[0], f[1]];
            out.slots.deck = { id: 'deck', label: dn === 'trunk' ? 'Trunk / Deck' : (dn === 'bed' ? 'Bed' : 'Tailgate'), part: dn, cx: p2[0], cy: p2[1], r: r2, u: u2, theta: thetaOf(r2), boxW: 0.8 * acr2, boxH: 0.6 * (ed.a1 - ed.a0), pxcm: acr2 / CM.deck, notes: [],
                info: { along: ed.a1 - ed.a0, across: acr2, read: 'from behind' } };
        }
        var er = hasPart('roof') ? ex('roof') : null;
        if (er) {
            var acr3 = er.c1 - er.c0, alen = er.a1 - er.a0, pxr = acr3 / CM.roof, am = (er.a0 + er.a1) / 2;
            [['rail_l', er.c1 - 0.13 * acr3, [-f[0], -f[1]], [-l[0], -l[1]]], ['rail_r', er.c0 + 0.13 * acr3, [f[0], f[1]], [l[0], l[1]]]].forEach(function (a) {
                var p3 = xyOf(f, l, am, a[1]);
                out.slots[a[0]] = { id: a[0], label: SLOT_BY[a[0]].label, part: 'roof', cx: p3[0], cy: p3[1], r: a[2], u: a[3], theta: thetaOf(a[2]), boxW: 0.7 * alen, boxH: 0.3 * acr3, pxcm: pxr, notes: [],
                    info: { along: alen, across: acr3, read: a[0] === 'rail_l' ? "from the driver's door" : "from the passenger's door" } };
            });
        }
        out.ids = SLOTS.map(function (s) { return s.id; }).filter(function (id) { return !!out.slots[id]; });
        out.ok = out.ids.length > 0; if (!out.ok) out.why = 'No door, hood, deck or roof was found on this car map.';
        out.pxcmSide = pxcmSide;
        try { out.regScaleLR = regScale(C, 'left side', 'right side'); } catch (e) {}
        return out;
    }

    // ------------------------------------------------------------------ size model + rendering
    /** Physical size in cm of the logo for a kit: AREA based, so a wide banner and a badge look equally big. Size 100% = a logo of 30 x 30 cm worth of area (a typical door / quarter decal). */
    function physical(kit, aspect) {
        var B = 30 * kit.size / 100, a = Math.max(0.05, Math.min(20, aspect || 1)), w = B * Math.sqrt(a), h = B / Math.sqrt(a);
        var lim = 3.2 * B; if (w > lim) { h *= lim / w; w = lim; } if (h > lim) { w *= lim / h; h = lim; }
        return { wcm: w, hcm: h };
    }
    function slotPx(kit, sl, aspect) {
        var p = physical(kit, aspect), wpx = Math.max(6, Math.round(p.wcm * sl.pxcm)), hpx = Math.max(6, Math.round(p.hcm * sl.pxcm));
        return { wcm: p.wcm, hcm: p.hcm, wpx: wpx, hpx: hpx, fit: Math.min(sl.boxW / wpx, sl.boxH / hpx) };
    }
    function scaleTo(master, w, h) {
        var src = master;
        while (src.width > w * 2 && src.height > h * 2) { var t = mkCanvas(Math.max(w, Math.ceil(src.width / 2)), Math.max(h, Math.ceil(src.height / 2))), g0 = t.getContext('2d'); g0.imageSmoothingQuality = 'high'; g0.drawImage(src, 0, 0, t.width, t.height); src = t; }
        var cv = mkCanvas(w, h), g = cv.getContext('2d'); g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(src, 0, 0, w, h); return cv;
    }
    function turnCanvas(cv, theta) {
        var aw = cv.width, ah = cv.height, ca = Math.abs(Math.cos(theta)), sa = Math.abs(Math.sin(theta)), quarter = Math.abs(sa * ca) < 1e-9, pad = quarter ? 0 : 2;
        var W = Math.ceil(aw * ca + ah * sa - 1e-6) + pad * 2, H = Math.ceil(aw * sa + ah * ca - 1e-6) + pad * 2, o = mkCanvas(W, H), g = o.getContext('2d');
        g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
        var ct = Math.cos(theta), st = Math.sin(theta);
        if (Math.abs(st) < 1e-9) { st = 0; ct = ct < 0 ? -1 : 1; } else if (Math.abs(ct) < 1e-9) { ct = 0; st = st < 0 ? -1 : 1; }
        g.setTransform(ct, st, -st, ct, W / 2, H / 2); g.drawImage(cv, -aw / 2, -ah / 2); return o;
    }

    // ------------------------------------------------------------------ logos (kept per kit id; saved with the project on the kit's first layer)
    var LOGO = {};       // kid -> { canvas, name, kind, cleaned, info, url }
    function setLogoRec(kid, rec) { LOGO[kid] = rec; return rec; }
    function logoOf(kid) { return LOGO[kid] || null; }
    function logoUrl(rec) { if (!rec) return null; if (!rec.url) { try { rec.url = rec.canvas.toDataURL('image/png'); } catch (e) { return null; } } return rec.url; }
    function capMaster(cv, max) {
        max = max || 1024; var m = Math.max(cv.width, cv.height); if (m <= max) return cv;
        var s = max / m; return scaleTo(cv, Math.max(1, Math.round(cv.width * s)), Math.max(1, Math.round(cv.height * s)));
    }

    // ------------------------------------------------------------------ layers
    function templateIndex(L) {
        for (var i = 0; i < L.length; i++) {
            var l = L[i]; if (!l) continue;
            if (/^\s*(wire|wireframe|mask|car mandatory)\s*$/i.test(String(l.name || '')) || /turn\s*off\s*before\s*export/i.test(String(l.groupName || ''))) return i;
        }
        return L.length;
    }
    function isKitLayer(l) { return !!(l && l.img && l.img[KEY]); }
    function kitOf(l) { return isKitLayer(l) ? l.img[KEY] : null; }
    function kitLayers(kid) { var L = psdLayers() || []; return L.filter(function (l) { var p = kitOf(l); return p && (!kid || p.kid === kid); }); }
    function attachPayload(canvas, p) { try { canvas[KEY] = Object.freeze(p); } catch (e) {} }
    function newKid() { return 'sk' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5); }
    function layerName(kit, slotId, logoName) { var nm = kit.name || (logoName ? String(logoName).replace(/\.[a-z0-9]+$/i, '') : 'Logo'); return 'Sponsor ' + nm.slice(0, 28) + ' - ' + (SLOT_BY[slotId] ? SLOT_BY[slotId].label : 'Sheet Centre'); }
    function matRec(kit) {
        var M = root.SPBRevLayerMat; if (kit.material === 'none' || !M || (M.off && M.off())) return null;
        try { return FINISH_OF[kit.material] ? M.normalize({ finishId: FINISH_OF[kit.material] }) : M.normalize({ preset: kit.material }); } catch (e) { return null; }
    }
    function setMaterial(layer, kit, touched) {
        var M = root.SPBRevLayerMat, F = (M && M.FIELD) || 'spbMaterial', rec = matRec(kit);
        if (rec) layer[F] = rec; else if (kit.material === 'none' && touched) delete layer[F];
    }
    function bump() { root._spbLayerRev = (root._spbLayerRev | 0) + 1; call('invalidateLayerVisibleContributionCache'); call('recompositeFromLayers'); }
    function refreshAll() {
        bump(); call('renderLayerPanel'); try { if (typeof root.drawLayerBounds === 'function') root.drawLayerBounds(); } catch (e) {}
        try { var M = root.SPBRevLayerMat; if (M && M.noticeChange) M.noticeChange(true); } catch (e) {}
        call('triggerPreviewRender');
    }

    // ------------------------------------------------------------------ [SPB-TICKETS-2 2026-10-10 IQ2-1] slots keep clear of Number Kit numbers and of other sponsor logos
    // Before: a slot only looked at the car map, so a Number Kit 46 on the same door was covered by the sponsor (85-100 % of the logo's ink sat on number ink on ARCA and on the flat TGA).
    // Now: when a slot's default box meets a number (or another sponsor kit's logo) the logo moves to the nearest free spot of the same part, and shrinks (88 .. 52 %) when the part is too
    // full; with no room at all it stays put and says so.  A layer the painter moved, or a kit that is being edited, is never touched.
    // Kill switch: window.SPB_TICKETS2_OFF = true, or window.SPB_T2_IQ21_OFF = true (or the same name = '1' in localStorage).
    var T2_SHRINK = [1, 0.88, 0.76, 0.64, 0.52], INK_BOX = (typeof WeakMap === 'function') ? new WeakMap() : null, BB_CACHE = {};
    function t2off() {
        var n = ['SPB_TICKETS2_OFF', 'SPB_T2_IQ21_OFF'], i;
        for (i = 0; i < n.length; i++) { try { if (flagOn(root[n[i]]) || flagOn(root.localStorage && root.localStorage.getItem(n[i]))) return true; } catch (e) { if (flagOn(root[n[i]])) return true; } }
        return false;
    }
    /** Sheet box [x0, y0, x1, y1] of a layer's visible ink (alpha > 40); falls back to the layer bbox. Cached per layer canvas. */
    function inkBox(l) {
        var cv = l.img, b = l.bbox, c = INK_BOX && cv ? INK_BOX.get(cv) : null;
        if (!c) {
            c = { x0: 0, y0: 0, x1: (cv && (cv.width || cv.naturalWidth)) || (b[2] - b[0]), y1: (cv && (cv.height || cv.naturalHeight)) || (b[3] - b[1]) };
            try {
                if (cv && typeof cv.getContext === 'function' && cv.width && cv.height) {
                    var d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, w = cv.width, h = cv.height, x0 = w, y0 = h, x1 = -1, y1 = -1, x, y, r;
                    for (y = 0; y < h; y++) { r = y * w * 4 + 3; for (x = 0; x < w; x++) if (d[r + x * 4] > 40) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
                    if (x1 >= x0 && y1 >= y0) c = { x0: x0, y0: y0, x1: x1 + 1, y1: y1 + 1 };
                }
            } catch (e) { /* tainted or detached canvas: the layer bbox stands in */ }
            if (INK_BOX && cv) { try { INK_BOX.set(cv, c); } catch (e) {} }
        }
        return [b[0] + c.x0, b[1] + c.y0, b[0] + c.x1, b[1] + c.y1];
    }
    /** What a sponsor must not sit on: every visible Number Kit layer and every layer of ANOTHER sponsor kit. */
    function obstaclesFor(kid) {
        var L = psdLayers() || [], out = [];
        L.forEach(function (l) {
            if (!l || l.visible === false || !l.img || !l.bbox) return;
            var nk = l.img.__spbNumKit, sp = l.img[KEY], name = null;
            if (nk) name = 'Number ' + String(nk.kit && nk.kit.number || '').trim();
            else if (sp && sp.kid !== kid) name = 'another sponsor logo';
            if (!name) return;
            var b = inkBox(l); if (b && b[2] > b[0] && b[3] > b[1]) out.push({ box: b, name: name.trim() });
        });
        return out;
    }
    function turnDims(w, h, theta) {      // the size turnCanvas() will give a w x h logo turned by theta
        var ca = Math.abs(Math.cos(theta)), sa = Math.abs(Math.sin(theta)), quarter = Math.abs(sa * ca) < 1e-9, pad = quarter ? 0 : 2;
        return { w: Math.ceil(w * ca + h * sa - 1e-6) + pad * 2, h: Math.ceil(w * sa + h * ca - 1e-6) + pad * 2 };
    }
    function t2Region(sl, C) {
        var sz = sheetSize(), W = C ? C.W : sz[0], H = C ? C.H : sz[1], m = (C && sl.part && C.masks && C.masks[sl.part]) || null, R = null;
        var ix = sl.info && sl.info.x, iy = sl.info && sl.info.body;
        if (m && !(ix && iy)) { var ck = C.key + '|' + sl.part, bb = BB_CACHE[ck] || (BB_CACHE[ck] = bboxOfMask(m, C.W, C.H)); if (bb) R = [bb.x0, bb.y0, bb.x1, bb.y1]; }
        if (!R) R = [Math.round(W * 0.05), Math.round(H * 0.05), Math.round(W * 0.95), Math.round(H * 0.95)];
        if (ix && ix.length === 2) { R[0] = ix[0]; R[2] = ix[1]; }
        if (iy && iy.length === 2) { R[1] = iy[0]; R[3] = iy[1]; }
        return { R: R, m: m, W: W, H: H };
    }
    /** { cx, cy, f, moved, by, blocked }: where the logo of slot sl goes so it clears the obstacles (by = '' when nothing was in the way). */
    function t2Clear(sl, px, theta, cx, cy, obst, C) {
        var res = { cx: cx, cy: cy, f: 1, moved: 0, by: '', blocked: false };
        if (!obst.length) return res;
        var gap = Math.max(10, Math.round((sl.pxcm || 4) * 2.5));
        function dimsOf(f) { return turnDims(Math.max(6, Math.round(px.wpx * f)), Math.max(6, Math.round(px.hpx * f)), theta); }
        function hitsAt(x, y, d) {
            var out = [], i, b;
            for (i = 0; i < obst.length; i++) { b = obst[i].box; if (x - d.w / 2 < b[2] + gap && x + d.w / 2 > b[0] - gap && y - d.h / 2 < b[3] + gap && y + d.h / 2 > b[1] - gap) out.push(obst[i]); }
            return out;
        }
        var d0 = dimsOf(1), h0 = hitsAt(cx, cy, d0);
        if (!h0.length) return res;
        var names = []; h0.forEach(function (o) { if (names.indexOf(o.name) < 0) names.push(o.name); }); res.by = names.join(' and ');
        var rg = t2Region(sl, C), R = rg.R, m = rg.m, W = rg.W, H = rg.H;
        function frac(x, y, d) {          // share of a 7 x 5 sample of the logo's box that lies on the part
            if (!m) return 1; var n = 0, i, j, qx, qy;
            for (i = 0; i < 7; i++) for (j = 0; j < 5; j++) { qx = Math.round(x - d.w / 2 + (i + 0.5) * d.w / 7); qy = Math.round(y - d.h / 2 + (j + 0.5) * d.h / 5); if (qx >= 0 && qy >= 0 && qx < W && qy < H && m[qy * W + qx]) n++; }
            return n / 35;
        }
        var need = Math.max(0.5, Math.min(0.94, frac(cx, cy, d0) - 0.02));
        for (var fi = 0; fi < T2_SHRINK.length; fi++) {
            var f = T2_SHRINK[fi], d = dimsOf(f), step = Math.max(5, Math.min(16, Math.round(Math.min(d.w, d.h) / 8))), best = null, x, y, dist;
            for (y = R[1] + d.h / 2; y <= R[3] - d.h / 2; y += step) for (x = R[0] + d.w / 2; x <= R[2] - d.w / 2; x += step) {
                dist = Math.hypot(x - cx, y - cy); if (best && dist >= best.dist) continue;
                if (hitsAt(x, y, d).length || frac(x, y, d) < need) continue;
                best = { x: x, y: y, dist: dist };
            }
            if (best) { res.cx = Math.round(best.x); res.cy = Math.round(best.y); res.f = f; res.moved = Math.round(best.dist); return res; }
        }
        res.blocked = true; return res;
    }
    function joinList(a) { return a.length < 3 ? a.join(' and ') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; }
    /** One sentence for the toast / dialog note, '' when nothing had to move. rep = S.report(). */
    function avoidSummary(rep) {
        var moved = [], shr = [], blocked = [], by = [];
        (rep || []).forEach(function (r) {
            var a = r.avoid; if (!a) return; var nm = (SLOT_BY[r.slot] || {}).label || 'the sheet';
            a.by.split(' and ').forEach(function (n) { if (n && by.indexOf(n) < 0) by.push(n); });
            if (a.blocked) blocked.push(nm); else { moved.push(nm); if (a.f < 1) shr.push(nm + ' ' + Math.round(a.f * 100) + '%'); }
        });
        var out = [];
        if (moved.length) out.push(joinList(moved) + (moved.length > 1 ? ' logos' : ' logo') + ' moved clear of ' + joinList(by) + (shr.length ? ' (smaller to fit: ' + shr.join(', ') + ')' : '') + '.');
        if (blocked.length) out.push('No clear room on ' + joinList(blocked) + ': the logo sits over ' + joinList(by) + '. Drag it or untick the slot.');
        return out.join(' ');
    }

    // ------------------------------------------------------------------ the session: live layers, one undo step on commit
    var SESSION = null;
    function stateOfKitLayers(kid) {
        var L = psdLayers() || [], F = (root.SPBRevLayerMat && root.SPBRevLayerMat.FIELD) || 'spbMaterial';
        return L.map(function (l, i) { return { l: l, i: i }; }).filter(function (o) { var p = kitOf(o.l); return p && p.kid === kid; })
            .map(function (o) { return { layer: o.l, idx: o.i, img: o.l.img, bbox: o.l.bbox.slice(), name: o.l.name, path: o.l.path, mat: o.l[F] }; });
    }
    function applyKitState(kid, state) {
        var L = psdLayers(), F = (root.SPBRevLayerMat && root.SPBRevLayerMat.FIELD) || 'spbMaterial';
        for (var i = L.length - 1; i >= 0; i--) { var p = kitOf(L[i]); if (p && p.kid === kid) L.splice(i, 1); }
        state.slice().sort(function (a, b) { return a.idx - b.idx; }).forEach(function (s) {
            s.layer.img = s.img; s.layer.bbox = s.bbox.slice(); s.layer.name = s.name; s.layer.path = s.path || '';
            if (s.mat) s.layer[F] = s.mat; else delete s.layer[F];
            L.splice(Math.min(s.idx, L.length), 0, s.layer);
        });
    }
    /** opts: { kid } edit an existing kit | { kit, logo:{canvas,name,kind,cleaned,info} } new. Returns the controller used by the dialog, or null. */
    function begin(opts) {
        opts = opts || {};
        if (off()) return null;
        if (SESSION) { try { SESSION.cancel(); } catch (e) { warn('cancel old session', e); } }
        var L = psdLayers(); if (!Array.isArray(L)) { toast('Open a car paint first.', 'warn'); return null; }
        var editKid = opts.kid || null, existing = editKid ? kitLayers(editKid) : [], first = existing[0];
        var kit = editKid && first ? normalize(kitOf(first).kit) : normalize(opts.kit || null);
        var S = { kid: editKid && first ? editKid : newKid(), kit: kit, mode: editKid && first ? 'edit' : 'new', geo: null, at: {}, force: {}, closed: false, liveIds: [], placed: {} };
        S.before = S.mode === 'edit' ? stateOfKitLayers(S.kid) : [];
        S.matTouched = kit.material !== 'none';
        S.keep = {};      // edit mode: where each slot's layer already is (a layer the user moved keeps its centre)
        if (S.mode === 'edit') existing.forEach(function (l) { var pk = kitOf(l); if (pk && pk.at) S.keep[pk.slot] = { cx: pk.at.cx, cy: pk.at.cy }; });
        S.logo = S.mode === 'edit' ? logoOf(S.kid) : (opts.logo ? setLogoRec(S.kid, Object.assign({ cleaned: false }, opts.logo)) : null);
        S.aspect = function () { var lg = S.logo; return lg && lg.canvas ? lg.canvas.width / Math.max(1, lg.canvas.height) : 1; };
        S.measure = function () { S.geo = measure(); return S.geo; };
        S.setLogo = function (cv, meta) { S.logo = setLogoRec(S.kid, Object.assign({ cleaned: false }, meta || {}, { canvas: capMaster(cv, 1024), url: null })); return S.apply(); };
        function wanted() { var geo = S.geo, out = []; if (geo && geo.ok) SLOTS.forEach(function (s) { if (S.kit.slots[s.id] && geo.slots[s.id]) out.push(s.id); }); return out; }
        function freeSlot() { var sz = sheetSize(); return { id: 'free', label: 'Sheet Centre', part: null, cx: sz[0] / 2, cy: sz[1] / 2, r: [1, 0], u: [0, -1], theta: 0, boxW: sz[0] * 0.3, boxH: sz[1] * 0.14, pxcm: 4.2, notes: [], info: {} }; }
        function insertIndex(Lx, live) {
            if (live.length) { var mx = -1; live.forEach(function (l) { mx = Math.max(mx, Lx.indexOf(l)); }); if (mx >= 0) return mx + 1; }
            return templateIndex(Lx);       // stamped on top of the paint, under the Wire / Mask template layers
        }
        function groupFrom(layer, Lx, at) {
            var tpl = templateIndex(Lx), nb = Lx[at - 1], src = (nb && at - 1 < tpl && nb.groupName) ? nb : ((Lx[at] && at < tpl && Lx[at].groupName) ? Lx[at] : null);
            if (src) { layer.groupName = src.groupName || ''; layer.groupChain = Array.isArray(src.groupChain) ? clone(src.groupChain) : []; layer.parentGroupKey = src.parentGroupKey || null; }
        }
        /** (Re)build every layer of the kit from S.kit + the logo. Cheap enough to run on every slider tick. */
        S.apply = function () {
            if (S.closed) return false;
            var Lx = psdLayers(), k = S.kit, geo = S.geo || S.measure(), want = wanted(), changed = false;
            var live = {}; kitLayers(S.kid).forEach(function (l) { live[kitOf(l).slot] = l; });
            if (!S.logo || !S.logo.canvas) { Object.keys(live).forEach(function (sid) { var ix = Lx.indexOf(live[sid]); if (ix >= 0) Lx.splice(ix, 1); changed = true; }); S.liveIds = []; S.placed = {}; if (changed) bump(); return true; }
            Object.keys(live).forEach(function (sid) { if (want.indexOf(sid) < 0) { var ix = Lx.indexOf(live[sid]); if (ix >= 0) Lx.splice(ix, 1); delete live[sid]; changed = true; delete S.keep[sid]; } });
            if (!(geo && geo.ok)) want = ['free'];
            S.placed = {};
            want.forEach(function (sid) {
                var sl = sid === 'free' ? freeSlot() : geo.slots[sid], layer = live[sid], px = slotPx(k, sl, S.aspect());
                var theta = sl.theta + k.extraTurn * Math.PI / 180;      // [SPB-TICKETS-2 2026-10-10 IQ2-1] the art is built AFTER the centre is known (it may shrink to clear a number)
                var cx = sl.cx, cy = sl.cy, prev = layer && layer.bbox ? layer.bbox : null, useprev = false;
                if (layer && prev && !S.force[sid]) {
                    var pcx = (prev[0] + prev[2]) / 2, pcy = (prev[1] + prev[3]) / 2;
                    if (S.mode === 'edit' && S.keep[sid] && !S.at[sid]) useprev = true;                                                         // an edited kit keeps where its layers are
                    else if (S.at[sid] && (Math.abs(pcx - S.at[sid].cx) > 1.5 || Math.abs(pcy - S.at[sid].cy) > 1.5)) useprev = true;          // a layer the user moved keeps its centre
                    if (useprev) { cx = pcx; cy = pcy; }
                } else if (!layer && S.mode === 'edit' && S.keep[sid]) { cx = S.keep[sid].cx; cy = S.keep[sid].cy; }
                delete S.force[sid];
                if (!useprev) { cx = Math.round(cx); cy = Math.round(cy); }       // a layer that already sits somewhere keeps its exact centre (no 1 px drift on every reopen)
                var avoid = null;      // [SPB-TICKETS-2 2026-10-10 IQ2-1] keep clear of Number Kit numbers / other sponsor logos (a layer the painter moved, or an edited kit's layer, stays where it is)
                if (!useprev && !(!layer && S.mode === 'edit' && S.keep[sid]) && !t2off()) {
                    try {
                        var cl = t2Clear(sl, px, theta, cx, cy, obstaclesFor(S.kid), regCur());
                        if (cl.by) {
                            avoid = { by: cl.by, moved: cl.moved, f: cl.f, blocked: cl.blocked };
                            if (!cl.blocked) {
                                cx = cl.cx; cy = cl.cy;
                                if (cl.f < 1) { var wq = Math.max(6, Math.round(px.wpx * cl.f)), hq = Math.max(6, Math.round(px.hpx * cl.f)); px = { wcm: px.wcm * cl.f, hcm: px.hcm * cl.f, wpx: wq, hpx: hq, fit: Math.min(sl.boxW / wq, sl.boxH / hq) }; }
                            }
                        }
                    } catch (e) { warn('keep clear of numbers', e); }
                }
                var art = turnCanvas(scaleTo(S.logo.canvas, px.wpx, px.hpx), theta);
                var bb = [Math.round(cx - art.width / 2), Math.round(cy - art.height / 2), 0, 0]; bb[2] = bb[0] + art.width; bb[3] = bb[1] + art.height;
                attachPayload(art, { v: 1, kid: S.kid, slot: sid, kit: clone(k), at: { cx: cx, cy: cy, theta: Math.round(theta * 1800 / Math.PI) / 10, wpx: px.wpx, hpx: px.hpx, pxcm: Math.round(sl.pxcm * 1000) / 1000 } });
                if (!layer) {
                    layer = { id: 'sponsor_' + S.kid + '_' + sid, name: layerName(k, sid, S.logo.name), path: '', visible: true, opacity: 255, blendMode: 'source-over', locked: false, alphaLock: false, clippingMask: false, effects: null, bbox: bb, img: art };
                    var at = insertIndex(Lx, Object.keys(live).map(function (q) { return live[q]; })); groupFrom(layer, Lx, at); Lx.splice(Math.min(at, Lx.length), 0, layer); live[sid] = layer;
                    try { if (typeof _psdLayersLoaded !== 'undefined') _psdLayersLoaded = true; } catch (e) {}
                } else { layer.img = art; layer.bbox = bb; layer.name = layerName(k, sid, S.logo.name); }
                if (k.material !== 'none') S.matTouched = true;
                setMaterial(layer, k, S.matTouched);
                S.at[sid] = { cx: cx, cy: cy, theta: theta }; S.placed[sid] = { avoid: avoid, slot: sid, label: sl.label, part: sl.part, wcm: px.wcm, hcm: px.hcm, wpx: px.wpx, hpx: px.hpx, pxcm: sl.pxcm, theta: theta, fit: px.fit, cx: cx, cy: cy, layerW: art.width, layerH: art.height, boxW: sl.boxW, boxH: sl.boxH };
                changed = true;
            });
            if (changed) bump();
            S.liveIds = Object.keys(live).map(function (p) { return live[p].id; });
            return true;
        };
        S.logo0 = S.logo;
        S.clearLogo = function () { S.logo = null; delete LOGO[S.kid]; return S.apply(); };
        S.set = function (patch) { S.kit = normalize(Object.assign({}, S.kit, patch)); return S.apply(); };
        S.setSlot = function (id, on) { var s = clone(S.kit.slots); s[id] = !!on; return S.set({ slots: s }); };
        /** Put one slot's layer back at its default centre (slotId) or all of them (no argument). */
        S.recentre = function (slotId) {
            S.measure(); S.keep = slotId ? Object.assign({}, S.keep) : {};
            if (slotId) { delete S.keep[slotId]; S.force[slotId] = true; delete S.at[slotId]; } else { SLOTS.forEach(function (s) { S.force[s.id] = true; }); S.at = {}; }
            S.mode === 'edit' && !slotId && (S.keep = {});
            return S.apply();
        };
        S.report = function () { return Object.keys(S.placed).map(function (k) { return S.placed[k]; }); };
        function finish(kind) { S.closed = true; if (SESSION === S) SESSION = null; refreshAll(); try { S.onClose && S.onClose(kind); } catch (e) { warn('onClose', e); } }
        S.commit = function () {
            if (S.closed) return false;
            var cur = stateOfKitLayers(S.kid); if (!cur.length) return S.cancel();
            // snapshot BEFORE the kit existed, then put the live state back: ONE undo step for the whole kit
            applyKitState(S.kid, S.before); call('_pushLayerStackUndo', S.mode === 'edit' ? 'edit sponsor kit' : 'sponsor kit'); applyKitState(S.kid, cur);
            try { call('selectPSDLayer', cur[0].layer.id); } catch (e) {}
            S.committed = { n: cur.length, slots: cur.map(function (c) { return kitOf(c.layer).slot; }) };
            finish('commit');
            var avs = ''; try { avs = avoidSummary(S.report()); } catch (e) { warn('avoid summary', e); }      // [SPB-TICKETS-2 2026-10-10 IQ2-1] say what was moved clear of a number
            toast('Sponsor logo placed on ' + cur.map(function (c) { return SLOT_BY[kitOf(c.layer).slot] ? SLOT_BY[kitOf(c.layer).slot].label : 'the sheet'; }).join(', ') + '. Ctrl+Z removes the whole kit.' + (avs ? ' ' + avs : ''), 'success');
            return true;
        };
        S.cancel = function () { if (S.closed) return false; applyKitState(S.kid, S.before); if (S.mode === 'new') delete LOGO[S.kid]; else if (S.logo0) LOGO[S.kid] = S.logo0; finish('cancel'); return true; };
        S.remove = function () {
            if (S.closed || S.mode !== 'edit') return false;
            var cur = stateOfKitLayers(S.kid); applyKitState(S.kid, S.before); call('_pushLayerStackUndo', 'remove sponsor kit'); applyKitState(S.kid, []);
            finish('remove'); toast('Sponsor Kit removed. Ctrl+Z brings it back.', 'info'); return cur.length > 0;
        };
        SESSION = S; S.measure();
        return S;
    }

    // ------------------------------------------------------------------ project Save / Open (hooked in js/features/spb-projects.js: serialize / deserialize next to spbMaterial)
    function serialize(layer) {
        var p = kitOf(layer); if (!p) return undefined; var rec = { v: 1, kid: p.kid, slot: p.slot, kit: clone(p.kit), at: p.at ? clone(p.at) : null };
        // the logo is saved once per kit, on the kit's first layer in the stack
        try { var L = psdLayers() || [], firstOf = null; for (var i = 0; i < L.length; i++) { var q = kitOf(L[i]); if (q && q.kid === p.kid) { firstOf = L[i]; break; } } if (firstOf === layer) { var lg = logoOf(p.kid); if (lg) { rec.logo = logoUrl(lg); rec.logoName = lg.name; rec.logoCleaned = !!lg.cleaned; } } } catch (e) { warn('serialize logo', e); }
        return rec;
    }
    function deserialize(layer, rec) {
        if (!layer || !layer.img || !rec || typeof rec !== 'object' || !rec.kit) return false;
        try {
            var p = { v: 1, kid: String(rec.kid || ''), slot: String(rec.slot || 'free'), kit: normalize(rec.kit), at: rec.at || null }; attachPayload(layer.img, p);
            if (rec.logo && typeof rec.logo === 'string' && /^data:image\/png;base64,/.test(rec.logo) && !LOGO[p.kid]) {
                var im = new Image(), r = { canvas: null, name: String(rec.logoName || 'Logo'), kind: 'png', cleaned: !!rec.logoCleaned, info: null, url: rec.logo, ready: null };
                r.ready = new Promise(function (res) { im.onload = function () { var cv = mkCanvas(im.naturalWidth || im.width, im.naturalHeight || im.height); cv.getContext('2d').drawImage(im, 0, 0); r.canvas = cv; res(r); }; im.onerror = function () { res(r); }; });
                im.src = rec.logo; LOGO[p.kid] = r;
            }
            return true;
        } catch (e) { return false; }
    }

    root.SpbRevSponsor = {
        version: VER, KEY: KEY, SLOTS: SLOTS, SLOT_BY: SLOT_BY, MATERIALS: MATERIALS, GOLD_FINISH: GOLD_FINISH, DEFAULTS: DEFAULTS, MODEL_CM: CM, off: off,
        normalize: normalize, measure: measure, begin: begin, session: function () { return SESSION; },
        serialize: serialize, deserialize: deserialize, kitOf: kitOf, isKitLayer: isKitLayer, kitLayers: kitLayers, logoOf: logoOf, templateIndex: templateIndex,
        avoidSummary: avoidSummary, physical: physical, slotPx: slotPx, capMaster: capMaster, scaleTo: scaleTo, turnCanvas: turnCanvas,
        _internal: { LOGO: LOGO, t2Clear: t2Clear, obstaclesFor: obstaclesFor, inkBox: inkBox, doorRanges: doorRanges, noseVector: noseVector, extents: extents, regScale: regScale }
    };
})(typeof window !== 'undefined' ? window : globalThis);
