/* numbers-core.js - [SPB-REV-NUMBERS 2026-10-10] NUMBER KIT: the car number on both doors and the roof in one step.
 *
 * On the flat iRacing sheet the two sides and the roof are stored turned and flipped differently (the ARCA / truck right side is stored
 * upside-down, the roof is stored with the nose pointing along the sheet), so a number has to be turned per place to read right ON THE CAR.
 * This module:
 *   1. measures each place from the car map (SpbProCar: side panels, wheel arches = door, roof) and the Symmetry registration (SpbRevSym:
 *      part masks, the roof's own mirror axis, the left -> right map),
 *   2. renders the number (font, fill, 1-2 outline rings, drop shadow, optional number panel) UPRIGHT and turns it to read right at each place,
 *   3. creates one normal paint layer per place (movable, one undo step for the whole kit), and keeps the kit's settings on the layer's
 *      pixel canvas (img.__spbNumKit) so the Number Kit dialog can re-open it and update all places at once.
 * Everything is additive. Kill switch: window.SPB_REV_NUMBERS_OFF = true (or localStorage SPB_REV_NUMBERS_OFF = '1').
 * Uses only other tools' public APIs: SpbProCar, SpbRevSym / SpbRevSymTools._internal.axisOf, SPBRevLayerMat (optional), the layer stack.
 */
(function (root) {
    'use strict';
    if (root.SpbRevNumbers) return;
    var doc = root.document;
    var VER = 'nk1.0', TAG = '[SPB-REV-NUMBERS]', KEY = '__spbNumKit';
    var PLACES = ['left', 'right', 'roof'];
    var PLACE_LABEL = { left: 'Left Door', right: 'Right Door', roof: 'Roof', free: 'Sheet Centre' };
    var PLACE_PART = { left: 'left side', right: 'right side', roof: 'roof' };

    // ------------------------------------------------------------------ plumbing
    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_REV_NUMBERS_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_REV_NUMBERS_OFF')); }
        catch (e) { return flagOn(root.SPB_REV_NUMBERS_OFF); }
    }
    function warn(where, e) { try { console.warn(TAG, where, e && e.message || e); } catch (_) {} }
    function psdLayers() { try { return (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers; } catch (e) { return root._psdLayers; } }
    function toast(msg, kind) { try { if (typeof root.showToast === 'function') root.showToast(msg, kind); } catch (e) {} }
    function call(name) { try { var f = root[name]; if (typeof f === 'function') return f.apply(root, Array.prototype.slice.call(arguments, 1)); } catch (e) { warn(name, e); } return undefined; }
    function clone(o) { return JSON.parse(JSON.stringify(o)); }
    function sheetSize() { var c = doc.getElementById('paintCanvas'); return c ? [c.width || 2048, c.height || 2048] : [2048, 2048]; }

    // ------------------------------------------------------------------ the kit model
    var HEX = /^#[0-9a-f]{6}$/i;
    var DEFAULTS = {
        v: 1, number: '77',
        font: 'Impact', bold: true, italic: false, slant: 0, spacing: 6,
        fill: '#ffffff',
        ring1: { color: '#000000', w: 5 },                    // outline widths are % of the number size, so every place scales the same
        ring2: { color: '#ffffff', w: 0 },
        shadow: { on: true, color: '#000000', alpha: 85, dist: 4, soft: 0, angle: 45 },
        plate: { on: false, shape: 'rounded', color: '#ffffff', border: '#000000', bw: 2, pad: 16 },
        places: { left: true, right: true, roof: true },
        roofFrom: 'driver',                                   // 'driver' | 'passenger'
        size: 100,                                            // % of the default fit for each place
        turn: { left: 'auto', right: 'auto', roof: 'auto' },  // 'auto' | 0 | 90 | 180 | 270 (absolute turn in degrees, clockwise)
        material: 'none'                                      // 'none' | 'chrome' | 'gloss' | 'matte' | 'satin'
    };
    function num(v, lo, hi, d) { v = Number(v); if (!isFinite(v)) v = d; return Math.max(lo, Math.min(hi, v)); }
    function hex(v, d) { v = String(v == null ? '' : v).trim(); if (v.charAt(0) !== '#') v = '#' + v; return HEX.test(v) ? v.toLowerCase() : d; }
    function normalize(k) {
        k = k || {}; var D = DEFAULTS, o = {};
        o.v = 1;
        var n = String(k.number == null ? D.number : k.number).replace(/[^A-Za-z0-9]/g, '').slice(0, 4);
        o.number = n || D.number;
        o.font = String(k.font || D.font).replace(/["<>]/g, '').slice(0, 60) || D.font;
        o.bold = k.bold == null ? D.bold : !!k.bold; o.italic = !!k.italic;
        o.slant = num(k.slant, 0, 25, 0); o.spacing = num(k.spacing == null ? D.spacing : k.spacing, -10, 40, D.spacing);
        o.fill = hex(k.fill, D.fill);
        var r1 = k.ring1 || {}, r2 = k.ring2 || {}, sh = k.shadow || {}, pl = k.plate || {}, pc = k.places || {}, tn = k.turn || {};
        o.ring1 = { color: hex(r1.color, D.ring1.color), w: num(r1.w == null ? D.ring1.w : r1.w, 0, 25, D.ring1.w) };
        o.ring2 = { color: hex(r2.color, D.ring2.color), w: num(r2.w == null ? D.ring2.w : r2.w, 0, 25, D.ring2.w) };
        o.shadow = { on: sh.on == null ? D.shadow.on : !!sh.on, color: hex(sh.color, D.shadow.color), alpha: num(sh.alpha == null ? D.shadow.alpha : sh.alpha, 0, 100, D.shadow.alpha),
            dist: num(sh.dist == null ? D.shadow.dist : sh.dist, 0, 20, D.shadow.dist), soft: num(sh.soft == null ? D.shadow.soft : sh.soft, 0, 12, D.shadow.soft), angle: num(sh.angle == null ? D.shadow.angle : sh.angle, -180, 180, D.shadow.angle) };
        var shape = ['rounded', 'oval', 'circle', 'square'].indexOf(pl.shape) >= 0 ? pl.shape : D.plate.shape;
        o.plate = { on: pl.on == null ? D.plate.on : !!pl.on, shape: shape, color: hex(pl.color, D.plate.color), border: hex(pl.border, D.plate.border),
            bw: num(pl.bw == null ? D.plate.bw : pl.bw, 0, 10, D.plate.bw), pad: num(pl.pad == null ? D.plate.pad : pl.pad, 0, 60, D.plate.pad) };
        o.places = { left: pc.left == null ? D.places.left : !!pc.left, right: pc.right == null ? D.places.right : !!pc.right, roof: pc.roof == null ? D.places.roof : !!pc.roof, free: !!pc.free };
        o.roofFrom = k.roofFrom === 'passenger' ? 'passenger' : 'driver';
        o.size = num(k.size == null ? D.size : k.size, 20, 160, D.size);
        o.turn = {};
        PLACES.concat(['free']).forEach(function (p) { var t = tn[p]; o.turn[p] = (t === 0 || t === 90 || t === 180 || t === 270 || t === '0' || t === '90' || t === '180' || t === '270') ? Number(t) : 'auto'; });
        o.material = ['none', 'chrome', 'gloss', 'matte', 'satin'].indexOf(k.material) >= 0 ? k.material : 'none';
        return o;
    }

    // ------------------------------------------------------------------ fonts the app really has (same list as the Text tool)
    var fontCache = null;
    function installed(name) {
        try {
            var c = doc.createElement('canvas').getContext('2d'), s = 'mmmmmmmmmmlli0123456789', res = false;
            ['monospace', 'serif', 'sans-serif'].forEach(function (b) {
                c.font = '72px ' + b; var w0 = c.measureText(s).width; c.font = '72px "' + name + '",' + b; if (Math.abs(c.measureText(s).width - w0) > 0.01) res = true;
            });
            return res;
        } catch (e) { return true; }
    }
    function fonts() {
        if (fontCache) return fontCache;
        var out = [], sel = doc.getElementById('textFont');
        if (sel) for (var i = 0; i < sel.options.length; i++) out.push(sel.options[i].value);
        if (!out.length) out = ['Impact', 'Arial Black', 'Arial', 'Helvetica'];
        var ok = out.filter(installed);
        fontCache = ok.length ? ok : out;
        return fontCache;
    }

    // ------------------------------------------------------------------ rendering (upright art, then turned onto the sheet)
    var _sc = null;
    function scratchCtx() { if (!_sc) _sc = doc.createElement('canvas').getContext('2d'); return _sc; }
    function fontCss(k, S) { return (k.italic ? 'italic ' : '') + (k.bold ? 'bold ' : '') + S + 'px "' + k.font + '", Impact, "Arial Black", sans-serif'; }
    function evenUp(v) { v = Math.ceil(v - 1e-6); return v % 2 ? v + 1 : v; }

    /** Layout of the upright art at em size S: glyph positions, ink box, outline reach, plate and shadow extents. */
    function layoutArt(k, S) {
        var c = scratchCtx(); c.font = fontCss(k, S); c.textBaseline = 'alphabetic';
        var chars = Array.from(k.number), sp = k.spacing / 100 * S, x = 0, left = 1e9, right = -1e9, asc = 0, desc = 0, pos = [];
        chars.forEach(function (ch) {
            var m = c.measureText(ch); pos.push(x);
            left = Math.min(left, x - m.actualBoundingBoxLeft); right = Math.max(right, x + m.actualBoundingBoxRight);
            asc = Math.max(asc, m.actualBoundingBoxAscent); desc = Math.max(desc, m.actualBoundingBoxDescent); x += m.width + sp;
        });
        if (!(right > left)) { left = 0; right = S * 0.5; asc = S * 0.7; desc = 0; }
        var t = Math.tan(k.slant * Math.PI / 180);
        left -= t * desc; right += t * asc;                                         // shear x' = x - t*y (y is up-negative)
        var w1 = k.ring1.w / 100 * S, w2 = k.ring2.w / 100 * S, reach = w1 + w2;
        var cx0 = (left + right) / 2, cy0 = (-asc + desc) / 2;
        var hw = (right - left) / 2 + reach, hh = (asc + desc) / 2 + reach;
        var plate = null, hwP = hw, hhP = hh;
        if (k.plate.on) {
            var pad = k.plate.pad / 100 * S, bw = k.plate.bw / 100 * S;
            if (k.plate.shape === 'oval') { hwP = hw * 1.22 + pad; hhP = hh * 1.22 + pad; }
            else if (k.plate.shape === 'circle') { hwP = hhP = Math.hypot(hw, hh) + pad; }
            else if (k.plate.shape === 'square') { hwP = hhP = Math.max(hw, hh) + pad; }
            else { hwP = hw + pad; hhP = hh + pad; }
            plate = { hw: hwP, hh: hhP, bw: bw };
            hwP += bw / 2; hhP += bw / 2;
        }
        var sd = k.shadow.on ? k.shadow.dist / 100 * S : 0, sb = k.shadow.on ? k.shadow.soft / 100 * S : 0, extra = Math.ceil(sd + 2 * sb + 2);
        return { chars: chars, pos: pos, left: left, right: right, asc: asc, desc: desc, t: t, w1: w1, w2: w2, reach: reach, cx0: cx0, cy0: cy0, plate: plate,
            sd: sd, sb: sb, aw: evenUp(2 * (hwP + extra)), ah: evenUp(2 * (hhP + extra)), S: S };
    }
    function drawGlyphs(g, k, L, mode, ox, oy) {
        g.save(); g.translate(ox, oy); g.transform(1, 0, -L.t, 1, 0, 0);
        g.font = fontCss(k, L.S); g.textBaseline = 'alphabetic'; g.lineJoin = 'round'; g.miterLimit = 2;
        for (var i = 0; i < L.chars.length; i++) { if (mode === 'stroke') g.strokeText(L.chars[i], L.pos[i], 0); else g.fillText(L.chars[i], L.pos[i], 0); }
        g.restore();
    }
    function plateShape(g, k, L, cx, cy) {
        var P = L.plate, hw = P.hw, hh = P.hh; g.beginPath();
        if (k.plate.shape === 'oval' || k.plate.shape === 'circle') g.ellipse(cx, cy, hw, hh, 0, 0, Math.PI * 2);
        else {
            var r = k.plate.shape === 'square' ? Math.min(hw, hh) * 0.06 : Math.min(hw, hh) * 0.28, x = cx - hw, y = cy - hh, w = hw * 2, h = hh * 2;
            g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
        }
    }
    /** Upright art canvas for em size S. The number's ink centre sits exactly at the canvas centre. */
    function renderArt(k, S) {
        var L = layoutArt(k, S), cv = doc.createElement('canvas'); cv.width = L.aw; cv.height = L.ah;
        var g = cv.getContext('2d'); g.imageSmoothingQuality = 'high';
        var ox = L.aw / 2 - L.cx0, oy = L.ah / 2 - L.cy0;
        if (L.plate) {
            plateShape(g, k, L, L.aw / 2, L.ah / 2); g.fillStyle = k.plate.color; g.fill();
            if (L.plate.bw > 0) { g.lineWidth = L.plate.bw; g.strokeStyle = k.plate.border; g.lineJoin = 'round'; g.stroke(); }
        }
        if (k.shadow.on && k.shadow.alpha > 0) {
            var sil = doc.createElement('canvas'); sil.width = L.aw; sil.height = L.ah; var sg = sil.getContext('2d');
            sg.fillStyle = k.shadow.color; sg.strokeStyle = k.shadow.color;
            if (L.reach > 0) { sg.lineWidth = 2 * L.reach; drawGlyphs(sg, k, L, 'stroke', ox, oy); }
            drawGlyphs(sg, k, L, 'fill', ox, oy);
            var a = k.shadow.angle * Math.PI / 180;
            g.save(); g.globalAlpha = k.shadow.alpha / 100;
            if (L.sb > 0.4) { try { g.filter = 'blur(' + L.sb.toFixed(2) + 'px)'; } catch (e) {} }
            g.drawImage(sil, L.sd * Math.cos(a), L.sd * Math.sin(a)); g.restore();
        }
        if (L.w2 > 0) { g.strokeStyle = k.ring2.color; g.lineWidth = 2 * (L.w1 + L.w2); drawGlyphs(g, k, L, 'stroke', ox, oy); }
        if (L.w1 > 0) { g.strokeStyle = k.ring1.color; g.lineWidth = 2 * L.w1; drawGlyphs(g, k, L, 'stroke', ox, oy); }
        g.fillStyle = k.fill; drawGlyphs(g, k, L, 'fill', ox, oy);
        return { canvas: cv, aw: L.aw, ah: L.ah, L: L };
    }
    /** Turn an upright art canvas by theta (radians, clockwise on the sheet) onto a new canvas with even dimensions. */
    function turnArt(art, theta) {
        var aw = art.aw, ah = art.ah, ca = Math.abs(Math.cos(theta)), sa = Math.abs(Math.sin(theta));
        var quarter = Math.abs(sa * ca) < 1e-9, pad = quarter ? 0 : 2;
        var W = evenUp(aw * ca + ah * sa - 1e-6) + pad * 2, H = evenUp(aw * sa + ah * ca - 1e-6) + pad * 2;
        var cv = doc.createElement('canvas'); cv.width = W; cv.height = H; var g = cv.getContext('2d');
        g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
        var ct = Math.cos(theta), st = Math.sin(theta);
        if (Math.abs(st) < 1e-9) { st = 0; ct = ct < 0 ? -1 : 1; } else if (Math.abs(ct) < 1e-9) { ct = 0; st = st < 0 ? -1 : 1; }   // exact quarter turns: no resampling blur
        g.setTransform(ct, st, -st, ct, W / 2, H / 2);
        g.drawImage(art.canvas, -aw / 2, -ah / 2);
        return cv;
    }
    /** Em size that makes the whole art fit a (tw x th) box (before the user's Size %). Everything scales with S, so one probe is exact. */
    function fitSize(k, tw, th) {
        var a = layoutArt(k, 100), s = Math.min(tw / a.aw, th / a.ah) * 100;
        return Math.max(8, Math.min(900, s * k.size / 100));
    }

    // [SPB-REV-NUMBERS 2026-10-10 follow-up] Replace Existing matches the numbers it replaces: their ink box (and slant) become the default box of each place.
    /** Tight alpha box of a canvas -> [x0,y0,x1,y1] or null. */
    function tightBox(cv) {
        var w = cv.width, h = cv.height, d; try { d = cv.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, w, h).data; } catch (e) { return null; }
        var x0 = w, y0 = h, x1 = -1, y1 = -1, x, y;
        for (y = 0; y < h; y++) { var r = y * w * 4 + 3; for (x = 0; x < w; x++) if (d[r + x * 4] > 12) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
        return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
    }
    /** Em size (at Size 100%) whose TIGHT ink box (outline + shadow included, like the old number's) fits uw x uh. Two passes: the layout box over-reserves a little. */
    function fitMatched(k, uw, uh) {
        var k1 = Object.assign({}, k, { size: 100 }), S = fitSize(k1, uw, uh);
        for (var i = 0; i < 2; i++) {
            var art = renderArt(k1, S), tb = tightBox(art.canvas); if (!tb) break;
            var iw = tb[2] - tb[0], ih = tb[3] - tb[1]; if (iw < 1 || ih < 1) break;
            S = Math.max(8, Math.min(900, S * Math.min(uw / iw, uh / ih)));
        }
        return S;
    }
    /** Row-centroid lean of an upright alpha canvas, degrees (right lean positive): regress the ink centroid of each row against the row, middle 60% of the ink height. */
    function leanOf(cv) {
        var w = cv.width, h = cv.height, d; try { d = cv.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, w, h).data; } catch (e) { return null; }
        var rows = [], y, x;
        for (y = 0; y < h; y++) { var n = 0, sx = 0, r = y * w * 4 + 3; for (x = 0; x < w; x++) if (d[r + x * 4] > 128) { n++; sx += x; } if (n > 2) rows.push([y, sx / n]); }
        if (rows.length < 12) return null;
        var a = Math.floor(rows.length * 0.2), b = Math.ceil(rows.length * 0.8), sub = rows.slice(a, b), m = sub.length, sy = 0, sc = 0, syy = 0, syc = 0, i;
        for (i = 0; i < m; i++) { sy += sub[i][0]; sc += sub[i][1]; syy += sub[i][0] * sub[i][0]; syc += sub[i][0] * sub[i][1]; }
        var den = m * syy - sy * sy; if (Math.abs(den) < 1e-6) return null;
        return Math.atan(-((m * syc - sy * sc) / den)) * 180 / Math.PI;
    }
    /** Lean of an existing number: its pixels (the layer as it was before we erased anything), turned upright by theta, inside its box. */
    function oldLean(img, ibb, box, theta) {
        var bw = box[2] - box[0], bh = box[3] - box[1], q = Math.abs(Math.sin(theta)) > 0.7, uw = q ? bh : bw, uh = q ? bw : bh, pad = 24;
        var cv = doc.createElement('canvas'); cv.width = Math.ceil(uw + 2 * pad); cv.height = Math.ceil(uh + 2 * pad); var g = cv.getContext('2d');
        g.translate(cv.width / 2, cv.height / 2); g.rotate(-theta);
        g.drawImage(img, ibb[0] - (box[0] + box[2]) / 2, ibb[1] - (box[1] + box[3]) / 2);
        return leanOf(cv);
    }
    /** The lean this kit's own glyphs show at slant 0 (so the digits' own shape cancels out of the comparison with the old number). */
    function baseLean(k) {
        var k0 = Object.assign({}, k, { slant: 0, plate: Object.assign({}, k.plate, { on: false }) }), art = renderArt(k0, 160);
        return leanOf(art.canvas);
    }

    // ------------------------------------------------------------------ measuring the car (car map + Symmetry registration)
    function SP() { return root.SpbProCar; }
    function carMap() { try { return SP() && SP().map && SP().map(); } catch (e) { return null; } }
    function boxOf(name) { var m = carMap(), b = m && m.boxes && m.boxes[name]; return b || null; }
    function hasPart(name) { try { return (SP().parts() || []).indexOf(name) >= 0; } catch (e) { return false; } }
    function regCur() { try { var s = root.SpbRevSym; return s && !s.off() ? s.cur() : null; } catch (e) { return null; } }
    function bboxOfMask(m, W, H) {
        var x0 = W, y0 = H, x1 = -1, y1 = -1, n = 0;
        for (var y = 0; y < H; y++) { var r = y * W; for (var x = 0; x < W; x++) if (m[r + x]) { n++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
        return n ? { x0: x0, y0: y0, x1: x1, y1: y1, n: n } : null;
    }
    function dirOf(v) { return v === 'left' ? [-1, 0] : v === 'right' ? [1, 0] : v === 'top' ? [0, -1] : v === 'bottom' ? [0, 1] : null; }
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1]; }
    function snap(v) { return Math.abs(v[0]) >= Math.abs(v[1]) ? [v[0] < 0 ? -1 : 1, 0] : [0, v[1] < 0 ? -1 : 1]; }

    /** Side panel: the roof-line edge ("up") gives a proper (never mirrored) turn: the text's up vector points at the roof. */
    function sideFrame(which) {
        var b = boxOf(PLACE_PART[which]) || {}, up = b.up, guess = false;
        if (!dirOf(up)) { up = which === 'left' ? 'top' : 'bottom'; guess = true; }
        var u = dirOf(up), d = [-u[0], -u[1]], r = [d[1], -d[0]], note = null;
        // cross-check with the nose: on the left side the text reads nose -> tail, on the right side tail -> nose
        var f = dirOf(b.front);
        if (f) { var want = which === 'left' ? [-f[0], -f[1]] : f; if (dot(want, r) < 0) note = 'The car map says this panel is stored mirrored; the number is turned, not mirrored. Use Turn if it reads wrong.'; }
        return { r: r, u: u, guess: guess, note: note };
    }
    /** Nose direction along the centre line (hood against roof / trunk), snapped to a sheet axis, then tilted like the roof's own mirror axis. */
    function noseVector(C) {
        var m = carMap(), B = m && m.boxes || {}, cen = function (n) { var b = B[n]; return b && b.bbox ? [(b.bbox[0] + b.bbox[2]) / 2, (b.bbox[1] + b.bbox[3]) / 2] : null; };
        var hood = cen('hood'), roof = cen('roof'), rear = cen('trunk') || cen('bed') || cen('tailgate'), v = null, how = null;
        if (hood && roof) { v = [hood[0] - roof[0], hood[1] - roof[1]]; how = 'hood vs roof'; }
        else if (roof && rear) { v = [roof[0] - rear[0], roof[1] - rear[1]]; how = 'roof vs trunk'; }
        var f = null;
        if (v && Math.hypot(v[0], v[1]) > 0.03) f = snap(v);
        if (!f) { var fl = dirOf(B.roof && B.roof.front) || dirOf(B.hood && B.hood.front); if (fl) { f = fl; how = 'front flag'; } }
        var guess = false; if (!f) { f = [1, 0]; guess = true; how = 'assumed'; }
        var tilt = 0;
        try {
            var mp = C && C.maps && C.maps['roof>roof'], T = root.SpbRevSymTools && root.SpbRevSymTools._internal;
            if (mp && T && T.axisOf) {
                var n = T.axisOf(mp), t = [-n[1], n[0]]; if (dot(t, f) < 0) t = [-t[0], -t[1]];
                if (dot(t, f) > Math.cos(15 * Math.PI / 180)) { tilt = Math.atan2(t[1], t[0]) - Math.atan2(f[1], f[0]); f = t; }
            }
        } catch (e) { warn('tilt', e); }
        return { f: f, how: how, guess: guess, tiltDeg: tilt * 180 / Math.PI };
    }
    function pctRange(h, lo, hi, total) {
        var a = null, b = null, acc = 0, i;
        for (i = 0; i < h.length; i++) { acc += h[i]; if (a === null && acc >= total * lo) a = i; if (acc >= total * hi) { b = i; break; } }
        return [a === null ? 0 : a, b === null ? h.length - 1 : b];
    }
    function roofPlace(C, kit) {
        var m = C.masks && C.masks.roof; if (!m) return null; var W = C.W, H = C.H, bb = bboxOfMask(m, W, H); if (!bb) return null;
        var nv = noseVector(C), f = nv.f, l = [f[1], -f[0]];
        var sx = 0, sy = 0, n = 0, OFF = 4096, hf = new Uint32Array(8192), hl = new Uint32Array(8192);
        for (var y = bb.y0; y <= bb.y1; y++) { var r = y * W; for (var x = bb.x0; x <= bb.x1; x++) if (m[r + x]) { sx += x; sy += y; n++; hf[Math.round(x * f[0] + y * f[1]) + OFF]++; hl[Math.round(x * l[0] + y * l[1]) + OFF]++; } }
        var cx = sx / n, cy = sy / n;
        try { var mp = C.maps['roof>roof'], q = root.SpbRevSym.mapPt(mp.M, cx, cy); if (q && isFinite(q[0]) && isFinite(q[1])) { cx = (cx + q[0]) / 2; cy = (cy + q[1]) / 2; } } catch (e) { warn('roof axis', e); }
        var rf = pctRange(hf, 0.02, 0.98, n), rl = pctRange(hl, 0.02, 0.98, n);
        var driver = kit.roofFrom !== 'passenger';
        // text frame: reading direction r and up u. Reading from the driver's side the text runs nose -> tail with its top toward the passenger side.
        var r2 = driver ? [-f[0], -f[1]] : [f[0], f[1]], u = driver ? [-l[0], -l[1]] : [l[0], l[1]];
        var notes = []; if (nv.guess) notes.push('The car map does not say which way the nose points on the roof; assumed to the right. Use Turn if it reads wrong.');
        return { place: 'roof', part: 'roof', cx: cx, cy: cy, r: r2, u: u, tw: (rf[1] - rf[0]) * 0.6, th: (rl[1] - rl[0]) * 0.5,
            info: { nose: nv.how, tiltDeg: Math.round(nv.tiltDeg * 10) / 10, alongPx: rf[1] - rf[0], acrossPx: rl[1] - rl[0] }, notes: notes };
    }
    function doorRangeOf(which, C) {
        try {
            var g = SP().sideGeom(PLACE_PART[which]); if (!g) return null;
            if (g.arches && g.arches.length === 2) return { x0: g.arches[0][1] * C.W, x1: g.arches[1][0] * C.W, src: 'wheel arches' };
            return { g: g };
        } catch (e) { return null; }
    }
    function sidePlace(which, C, kit, door) {
        var m = C.masks && C.masks[PLACE_PART[which]]; if (!m) return null; var W = C.W, H = C.H, bb = bboxOfMask(m, W, H); if (!bb) return null;
        var fr = sideFrame(which), x0 = door.x0, x1 = door.x1, notes = [];
        x0 = Math.max(bb.x0, Math.round(x0)); x1 = Math.min(bb.x1, Math.round(x1)); if (x1 - x0 < 20) return null;
        var need = Math.max(1, Math.round((x1 - x0 + 1) * 0.6)), yt = -1, yb = -1;
        for (var y = bb.y0; y <= bb.y1; y++) { var n = 0, r = y * W; for (var x = x0; x <= x1; x++) if (m[r + x]) n++; if (n >= need) { if (yt < 0) yt = y; yb = y; } }
        if (yt < 0) { yt = bb.y0; yb = bb.y1; }
        var span = yb - yt + 1, roofEdge = fr.u[1] < 0 ? 'top' : (fr.u[1] > 0 ? 'bottom' : null);
        var cy = roofEdge === 'bottom' ? yb - 0.45 * span : yt + 0.45 * span;
        // 0.45 from the roof-line edge (the owner ARCA 32 sits at 0.42), centred on the door between the wheel arches
        if (fr.guess) notes.push('The car map does not say which edge of this side is the roof-line; assumed ' + (which === 'left' ? 'top' : 'bottom') + '. Use Turn if it reads wrong.');
        if (fr.note) notes.push(fr.note);
        return { place: which, part: PLACE_PART[which], cx: (x0 + x1) / 2, cy: cy, r: fr.r, u: fr.u, tw: (x1 - x0) * 0.6, th: span * 0.52,
            info: { door: [x0, x1], body: [yt, yb], doorFrom: door.src || 'default' }, notes: notes };
    }
    /** All places for this car. Returns { ok, why, places:{left,right,roof}, reg } - places are only present when the car map knows the part. */
    function measure(kit) {
        kit = kit || normalize(null);
        var C = regCur(), out = { ok: false, places: {}, why: '', reg: null, parts: [] };
        var sz = sheetSize(); out.W = sz[0]; out.H = sz[1];
        if (!SP() || !hasParts()) { out.why = 'This paint has no car map (flat file or no template), so the parts could not be found.'; return out; }
        if (!C) { out.why = 'The car shape is not measured yet.'; out.needBuild = true; return out; }
        out.reg = { key: C.key, W: C.W, H: C.H };
        var dr = { left: doorRangeOf('left', C), right: doorRangeOf('right', C) }, dd = {};
        ['left', 'right'].forEach(function (w) { if (dr[w] && dr[w].x0 != null) dd[w] = dr[w]; });
        // a side whose arches were not measured borrows the other side's door through the left <-> right registration
        ['left', 'right'].forEach(function (w) {
            if (dd[w]) return; var o = w === 'left' ? 'right' : 'left'; if (!dd[o]) return;
            try {
                var mp = C.maps[PLACE_PART[o] + '>' + PLACE_PART[w]], mid = (dd[o].x0 + dd[o].x1) / 2, S = root.SpbRevSym;
                var m = C.masks[PLACE_PART[o]], bbo = bboxOfMask(m, C.W, C.H), yc = (bbo.y0 + bbo.y1) / 2;
                var a = S.mapPt(mp.M, dd[o].x0, yc), b = S.mapPt(mp.M, dd[o].x1, yc);
                dd[w] = { x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), src: 'registered from the ' + o + ' side' };
            } catch (e) { warn('door via registration', e); }
        });
        ['left', 'right'].forEach(function (w) {
            if (!hasPart(PLACE_PART[w])) return;
            var d = dd[w]; if (!d) {                                          // last resort: the library's door fractions from the nose end
                var g = dr[w] && dr[w].g; if (!g) return;
                var nose = (boxOf(PLACE_PART[w]) || {}).front === 'right' ? 'right' : 'left', a0 = g.x0 * C.W, a1 = g.x1 * C.W, wd = a1 - a0;
                d = nose === 'right' ? { x0: a1 - 0.78 * wd, x1: a1 - 0.30 * wd, src: 'default fractions' } : { x0: a0 + 0.30 * wd, x1: a0 + 0.78 * wd, src: 'default fractions' };
            }
            var p = sidePlace(w, C, kit, d); if (p) out.places[w] = p;
        });
        if (hasPart('roof')) { var rp = roofPlace(C, kit); if (rp) out.places.roof = rp; }
        out.parts = Object.keys(out.places);
        out.ok = out.parts.length > 0;
        if (!out.ok) out.why = 'No door or roof was found on this car map.';
        return out;
    }
    function hasParts() { try { return !!(SP().parts && SP().parts().length); } catch (e) { return false; } }
    function placeAngle(p, turn) {
        if (turn === 0 || turn === 90 || turn === 180 || turn === 270) return turn * Math.PI / 180;
        return Math.atan2(p.r[1], p.r[0]);
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
    function layerRoleOf(l) {
        var r = ''; try { if (SP() && SP().roleOf) r = String(SP().roleOf(l) || ''); } catch (e) {}
        if (r === 'numbers') return r;
        var n = String(l.name || '').toLowerCase(); return /(^|\s)numbers?(\s|$)/.test(n) ? 'numbers' : r;
    }
    function numberLayers() {
        var L = psdLayers() || [], tpl = templateIndex(L), out = [];
        for (var i = 0; i < tpl; i++) { var l = L[i]; if (l && l.img && !isKitLayer(l) && layerRoleOf(l) === 'numbers') out.push(l); }
        return out;
    }
    function attachPayload(canvas, p) { try { canvas[KEY] = Object.freeze(p); } catch (e) {} }
    function serialize(layer) { var p = kitOf(layer); return p ? clone(p) : undefined; }
    function deserialize(layer, rec) {
        if (!layer || !layer.img || !rec || typeof rec !== 'object' || !rec.kit) return false;
        try { var p = { v: 1, kid: String(rec.kid || ''), place: String(rec.place || 'free'), kit: normalize(rec.kit), at: rec.at || null }; attachPayload(layer.img, p); return true; } catch (e) { return false; }
    }
    function newKid() { return 'nk' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5); }
    function layerName(kit, place) { return 'Number ' + kit.number + ' - ' + PLACE_LABEL[place]; }
    function matRec(kit) {
        var M = root.SPBRevLayerMat; if (kit.material === 'none' || !M || (M.off && M.off())) return null;
        try { return M.normalize({ preset: kit.material }); } catch (e) { return null; }
    }
    // the kit only clears a material it set itself (kit.material was not 'none' at some point in this session or when it was saved)
    function setMaterial(layer, kit, touched) {
        var M = root.SPBRevLayerMat, F = (M && M.FIELD) || 'spbMaterial', rec = matRec(kit);
        if (rec) layer[F] = rec; else if (kit.material === 'none' && touched) delete layer[F];
    }
    function bump() {
        root._spbLayerRev = (root._spbLayerRev | 0) + 1;
        call('invalidateLayerVisibleContributionCache'); call('recompositeFromLayers');
    }
    function refreshAll() {
        bump(); call('renderLayerPanel'); try { if (typeof root.drawLayerBounds === 'function') root.drawLayerBounds(); } catch (e) {}
        try { var M = root.SPBRevLayerMat; if (M && M.noticeChange) M.noticeChange(true); } catch (e) {}
        call('triggerPreviewRender');
    }

    // ------------------------------------------------------------------ existing numbers (the car's own Numbers layer)
    var DS = 4;
    function labelBlobs(layer) {
        var img = layer.img, w = img.width || img.naturalWidth, h = img.height || img.naturalHeight; if (!w || !h) return null;
        var gw = Math.ceil(w / DS), gh = Math.ceil(h / DS), cv = doc.createElement('canvas'); cv.width = gw; cv.height = gh;
        var g = cv.getContext('2d', { willReadFrequently: true }); g.imageSmoothingEnabled = true; g.drawImage(img, 0, 0, gw, gh);
        var d = g.getImageData(0, 0, gw, gh).data, a = new Uint8Array(gw * gh), i, x, y;
        for (i = 0; i < gw * gh; i++) a[i] = d[i * 4 + 3] > 12 ? 1 : 0;
        var R = 3, b = new Uint8Array(gw * gh);                              // dilate by 3 cells (12 px): the strokes of one number join into one blob
        for (y = 0; y < gh; y++) for (x = 0; x < gw; x++) if (a[y * gw + x]) { for (var yy = Math.max(0, y - R); yy <= Math.min(gh - 1, y + R); yy++) for (var xx = Math.max(0, x - R); xx <= Math.min(gw - 1, x + R); xx++) b[yy * gw + xx] = 1; }
        var lab = new Int32Array(gw * gh), st = new Int32Array(gw * gh), blobs = [], cur = 0;
        for (i = 0; i < gw * gh; i++) {
            if (!b[i] || lab[i]) continue;
            cur++; var sp = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1, n = 0; st[sp++] = i; lab[i] = cur;
            while (sp) {
                var q = st[--sp], qx = q % gw, qy = (q / gw) | 0; if (a[q]) { n++; if (qx < x0) x0 = qx; if (qx > x1) x1 = qx; if (qy < y0) y0 = qy; if (qy > y1) y1 = qy; }
                if (qx > 0 && b[q - 1] && !lab[q - 1]) { lab[q - 1] = cur; st[sp++] = q - 1; }
                if (qx < gw - 1 && b[q + 1] && !lab[q + 1]) { lab[q + 1] = cur; st[sp++] = q + 1; }
                if (qy > 0 && b[q - gw] && !lab[q - gw]) { lab[q - gw] = cur; st[sp++] = q - gw; }
                if (qy < gh - 1 && b[q + gw] && !lab[q + gw]) { lab[q + gw] = cur; st[sp++] = q + gw; }
            }
            if (n > 0) blobs.push({ id: cur, n: n, box: [x0 * DS + layer.bbox[0], y0 * DS + layer.bbox[1], (x1 + 1) * DS + layer.bbox[0], (y1 + 1) * DS + layer.bbox[1]] });
        }
        return { lab: lab, gw: gw, gh: gh, blobs: blobs, w: w, h: h };
    }
    /** Which existing number art sits at the places we are about to fill. -> { layer, hits:[{place, blob}], eraseIds } or null */
    function findExisting(geo) {
        var NL = numberLayers(); if (!NL.length || !geo || !geo.ok) return null;
        var C = regCur(), out = [];
        NL.forEach(function (layer) {
            var lb; try { lb = labelBlobs(layer); } catch (e) { warn('blobs', e); return; } if (!lb || !lb.blobs.length) return;
            var hits = [];
            lb.blobs.forEach(function (b) {
                if (b.n < 40) return;
                var cx = (b.box[0] + b.box[2]) / 2, cy = (b.box[1] + b.box[3]) / 2;
                PLACES.forEach(function (pl) {
                    var p = geo.places[pl]; if (!p) return; var m = C.masks[p.part]; if (!m) return;
                    var xi = Math.round(cx), yi = Math.round(cy); if (xi < 0 || yi < 0 || xi >= C.W || yi >= C.H || !m[yi * C.W + xi]) return;
                    if (pl !== 'roof') { var dx = p.info.door; var pad = (dx[1] - dx[0]) * 0.08; if (cx < dx[0] - pad || cx > dx[1] + pad) return; }   // a small number on the fender stays
                    if ((b.box[3] - b.box[1]) < 0.3 * Math.min(p.tw, p.th) && (b.box[2] - b.box[0]) < 0.3 * Math.min(p.tw, p.th)) return;
                    hits.push({ place: pl, blob: b });
                });
            });
            if (hits.length) out.push({ layer: layer, lb: lb, hits: hits });
        });
        return out.length ? out : null;
    }
    function erasedCanvas(layer, lb, ids) {
        var img = layer.img, cv = doc.createElement('canvas'); cv.width = lb.w; cv.height = lb.h; var g = cv.getContext('2d'); g.drawImage(img, 0, 0);
        var idset = {}; ids.forEach(function (i) { idset[i] = 1; });
        g.globalCompositeOperation = 'destination-out'; g.fillStyle = '#000';
        for (var cy = 0; cy < lb.gh; cy++) for (var cx = 0; cx < lb.gw; cx++) { if (idset[lb.lab[cy * lb.gw + cx]]) g.fillRect(cx * DS, cy * DS, DS, DS); }
        return cv;
    }

    // ------------------------------------------------------------------ the session: live layers, one undo step on commit
    var SESSION = null;
    function stateOfKitLayers(kid) {
        var L = psdLayers() || [];
        return L.map(function (l, i) { return { l: l, i: i }; }).filter(function (o) { var p = kitOf(o.l); return p && p.kid === kid; })
            .map(function (o) { var F = (root.SPBRevLayerMat && root.SPBRevLayerMat.FIELD) || 'spbMaterial'; return { layer: o.l, idx: o.i, img: o.l.img, bbox: o.l.bbox.slice(), name: o.l.name, path: o.l.path, mat: o.l[F] }; });
    }
    function applyKitState(kid, state, numbersState) {
        var L = psdLayers(), F = (root.SPBRevLayerMat && root.SPBRevLayerMat.FIELD) || 'spbMaterial';
        for (var i = L.length - 1; i >= 0; i--) { var p = kitOf(L[i]); if (p && p.kid === kid) L.splice(i, 1); }
        state.slice().sort(function (a, b) { return a.idx - b.idx; }).forEach(function (s) {
            s.layer.img = s.img; s.layer.bbox = s.bbox.slice(); s.layer.name = s.name; s.layer.path = s.path || '';
            if (s.mat) s.layer[F] = s.mat; else delete s.layer[F];
            L.splice(Math.min(s.idx, L.length), 0, s.layer);
        });
        if (numbersState) numbersState.forEach(function (ns) { ns.layer.img = ns.img; });
    }
    /** Begin a session. kit = existing kit (edit) or null (new). Returns the controller used by the dialog. */
    function begin(opts) {
        opts = opts || {};
        if (off()) return null;
        if (SESSION) { try { SESSION.cancel(); } catch (e) { warn('cancel old session', e); } }
        var L = psdLayers(); if (!Array.isArray(L)) { toast('Open a car paint first.', 'warn'); return null; }
        var editKid = opts.kid || null, existingKit = editKid ? kitLayers(editKid) : [];
        var first = existingKit[0], kit = editKid && first ? normalize(kitOf(first).kit) : normalize(opts.kit || null);
        var S = { kid: editKid && first ? editKid : newKid(), kit: kit, mode: editKid && first ? 'edit' : 'new', geo: null, replace: 'replace', existing: null, seq: 0, erased: [], moved: {}, closed: false };
        S.before = S.mode === 'edit' ? stateOfKitLayers(S.kid) : [];
        S.matTouched = kit.material !== 'none';
        S.boxes = {}; S.matched = {}; S.slantAuto = S.mode === 'new'; S.recentred = false; S.effSlant = kit.slant;
        if (S.mode === 'edit') existingKit.forEach(function (l) { var pk = kitOf(l); if (pk && pk.at && pk.at.tw) S.boxes[pk.place] = { tw: pk.at.tw, th: pk.at.th, m: !!pk.at.m }; });
        S.numbersBefore = null; S.at = {};      // S.at[place] = {cx, cy, theta} placement used the last time (a layer the user moved keeps its own centre)

        S.measure = function () { S.geo = measure(S.kit); return S.geo; };
        S.scanExisting = function () { S.existingHits = S.geo && S.geo.ok ? findExisting(S.geo) : null; return S.existingHits; };
        S.setReplace = function (mode) { S.replace = mode === 'add' ? 'add' : 'replace'; };

        function wantedPlaces() {
            var k = S.kit, geo = S.geo, out = [];
            if (geo && geo.ok) PLACES.forEach(function (p) { if (k.places[p] && geo.places[p]) out.push(p); });
            else if (k.places.free || !geo || !geo.ok) out.push('free');
            return out;
        }
        function freePlace() { var sz = sheetSize(); return { place: 'free', part: null, cx: sz[0] / 2, cy: sz[1] / 2, r: [1, 0], u: [0, -1], tw: sz[0] * 0.3, th: sz[1] * 0.14, info: {}, notes: [] }; }
        function insertIndex(Lx, liveLayers) {
            if (liveLayers.length) { var mx = -1; liveLayers.forEach(function (l) { mx = Math.max(mx, Lx.indexOf(l)); }); if (mx >= 0) return mx + 1; }   // above the kit's own highest layer
            var tpl = templateIndex(Lx), nl = S.numbersAnchor && Lx.indexOf(S.numbersAnchor);
            if (nl != null && nl >= 0) return Math.min(nl + 1, tpl);
            var nlayers = numberLayers(); if (nlayers.length) return Math.min(Lx.indexOf(nlayers[nlayers.length - 1]) + 1, tpl);
            return tpl;
        }
        function groupFrom(layer, Lx, at) {
            var tpl = templateIndex(Lx), nb = Lx[at - 1], src = (nb && at - 1 < tpl && nb.groupName) ? nb : ((Lx[at] && at < tpl && Lx[at].groupName) ? Lx[at] : null);
            if (src) { layer.groupName = src.groupName || ''; layer.groupChain = Array.isArray(src.groupChain) ? clone(src.groupChain) : []; layer.parentGroupKey = src.parentGroupKey || null; }
        }
        /** The old number's ink box at this place while Replace Existing is chosen: biggest blob at the place plus any piece of the same number. */
        function matchedBox(pl) {
            if (S.mode !== 'new' || S.replace !== 'replace' || !S.existingHits) return null;
            var bl = []; S.existingHits.forEach(function (e) { e.hits.forEach(function (h) { if (h.place === pl) bl.push({ b: h.blob, layer: e.layer }); }); });
            if (!bl.length) return null;
            bl.sort(function (a, b) { return b.b.n - a.b.n; });
            var b0 = bl[0].b.box.slice(), pad = 0.15 * Math.max(b0[2] - b0[0], b0[3] - b0[1]);
            bl.slice(1).forEach(function (o) { var q = o.b.box; if (q[0] < b0[2] + pad && q[2] > b0[0] - pad && q[1] < b0[3] + pad && q[3] > b0[1] - pad) b0 = [Math.min(b0[0], q[0]), Math.min(b0[1], q[1]), Math.max(b0[2], q[2]), Math.max(b0[3], q[3])]; });
            return { box: b0, layer: bl[0].layer };
        }
        /** (Re)build every layer of the kit from S.kit. Cheap enough to run on every keystroke. */
        S.apply = function () {
            if (S.closed) return false;
            var Lx = psdLayers(), k = S.kit, geo = S.geo || (S.measure()), want = wantedPlaces(), changed = false;
            // existing numbers: erase the ones at our places (live, so the preview is honest); put them back when we add instead
            if (S.mode === 'new' && S.existingHits) {
                if (!S.numbersBefore) S.numbersBefore = S.existingHits.map(function (e) { return { layer: e.layer, img: e.layer.img }; });
                S.existingHits.forEach(function (e) {
                    var ids = e.hits.filter(function (h) { return want.indexOf(h.place) >= 0; }).map(function (h) { return h.blob.id; });
                    var key = S.replace === 'replace' ? ids.join(',') : '';
                    if (e.__key !== key) { e.__key = key; var nb = S.numbersBefore.filter(function (n) { return n.layer === e.layer; })[0]; e.layer.img = ids.length && S.replace === 'replace' ? erasedCanvas(e.layer, e.lb, ids) : nb.img; changed = true; }
                });
                if (!S.numbersAnchor) S.numbersAnchor = S.existingHits[S.existingHits.length - 1].layer;
            }
            // slant: while Replace Existing is on (and the user has not typed a slant) use the lean of the numbers being replaced
            var kR = k, mbs = {}; S.matched = {};
            if (S.mode === 'new' && S.replace === 'replace' && S.existingHits) want.forEach(function (pl) { var m = matchedBox(pl); if (m) mbs[pl] = m; });
            S.effSlant = k.slant;
            if (S.slantAuto && S.mode === 'new' && !k.plate.on && Object.keys(mbs).length) {
                try {
                    var ls = [], b0 = baseLean(k);
                    Object.keys(mbs).forEach(function (pl) {
                        var nb = (S.numbersBefore || []).filter(function (n) { return n.layer === mbs[pl].layer; })[0], pp = geo.places[pl];
                        if (!nb || !pp) return; var lv = oldLean(nb.img, mbs[pl].layer.bbox, mbs[pl].box, placeAngle(pp, k.turn[pl])); if (lv != null) ls.push(lv);
                    });
                    if (ls.length && b0 != null) { ls.sort(function (a, b) { return a - b; }); var mean = ls.length % 2 ? ls[(ls.length - 1) / 2] : (ls[ls.length / 2 - 1] + ls[ls.length / 2]) / 2;   /* median: the doors lead, an odd roof design cannot drag it */ S.effSlant = Math.max(0, Math.min(25, Math.round(mean - b0))); kR = Object.assign({}, k, { slant: S.effSlant }); }
                } catch (e) { warn('slant match', e); }
            }
            var live = {}; kitLayers(S.kid).forEach(function (l) { live[kitOf(l).place] = l; });
            Object.keys(live).forEach(function (pl) { if (want.indexOf(pl) < 0) { var ix = Lx.indexOf(live[pl]); if (ix >= 0) Lx.splice(ix, 1); delete live[pl]; changed = true; } });
            want.forEach(function (pl) {
                var p = pl === 'free' ? freePlace() : geo.places[pl], layer = live[pl], turn = k.turn[pl];
                var theta = placeAngle(p, turn), q90 = Math.abs(Math.sin(theta)) > 0.7, mb = mbs[pl] || null, st = S.mode === 'edit' && !S.recentred ? S.boxes[pl] : null;
                var exact = null, cx = p.cx, cy = p.cy, twU = p.tw, thU = p.th;
                if (mb) { var bw = mb.box[2] - mb.box[0], bh = mb.box[3] - mb.box[1]; exact = { uw: q90 ? bh : bw, uh: q90 ? bw : bh }; cx = (mb.box[0] + mb.box[2]) / 2; cy = (mb.box[1] + mb.box[3]) / 2; }
                else if (st && st.m) exact = { uw: st.tw, uh: st.th };
                else if (st) { twU = st.tw; thU = st.th; }
                var S0, art, off = [0, 0];
                if (exact) { twU = exact.uw; thU = exact.uh; S0 = fitMatched(kR, exact.uw, exact.uh) * kR.size / 100; art = renderArt(kR, S0); var tbx = tightBox(art.canvas); if (tbx) off = [(tbx[0] + tbx[2]) / 2 - art.aw / 2, (tbx[1] + tbx[3]) / 2 - art.ah / 2]; }
                else { S0 = fitSize(kR, twU, thU); art = renderArt(kR, S0); }
                var img = turnArt(art, theta), prev = layer && layer.bbox ? layer.bbox : null, useprev = false;
                if (layer && prev) {
                    var pcx = (prev[0] + prev[2]) / 2, pcy = (prev[1] + prev[3]) / 2;
                    if (S.mode === 'edit' && !S.recentred) useprev = true;                                               // an edited kit keeps where its layers are
                    else if (S.at[pl] && (Math.abs(pcx - S.at[pl].cx) > 1.5 || Math.abs(pcy - S.at[pl].cy) > 1.5)) useprev = true;   // a moved layer keeps where the user put it
                    if (useprev) { cx = pcx; cy = pcy; }
                }
                if (!useprev && (off[0] || off[1])) { var ct0 = Math.cos(theta), st0 = Math.sin(theta); cx -= ct0 * off[0] - st0 * off[1]; cy -= st0 * off[0] + ct0 * off[1]; }   // put the INK centre on the old number's centre
                cx = Math.round(cx); cy = Math.round(cy);
                var bb = [cx - img.width / 2, cy - img.height / 2, cx + img.width / 2, cy + img.height / 2];
                if (mb) S.matched[pl] = { old: mb.box.slice(), uw: Math.round(twU), uh: Math.round(thU), slant: S.effSlant };
                attachPayload(img, { v: 1, kid: S.kid, place: pl, kit: clone(kR), at: { cx: cx, cy: cy, theta: Math.round(theta * 1800 / Math.PI) / 10, em: Math.round(S0 * 10) / 10, tw: Math.round(twU), th: Math.round(thU), m: exact ? 1 : 0 } });
                if (!layer) {
                    layer = { id: 'numkit_' + S.kid + '_' + pl, name: layerName(k, pl), path: '', visible: true, opacity: 255, blendMode: 'source-over', locked: false, alphaLock: false,
                        clippingMask: false, effects: null, bbox: bb, img: img };
                    var at = insertIndex(Lx, Object.keys(live).map(function (q) { return live[q]; })); groupFrom(layer, Lx, at); Lx.splice(Math.min(at, Lx.length), 0, layer); live[pl] = layer;
                    try { if (typeof _psdLayersLoaded !== 'undefined') _psdLayersLoaded = true; } catch (e) {}
                } else { layer.img = img; layer.bbox = bb; layer.name = layerName(k, pl); }
                if (k.material !== 'none') S.matTouched = true;
                setMaterial(layer, k, S.matTouched);
                S.at[pl] = { cx: cx, cy: cy, theta: theta, em: S0 };
                changed = true;
            });
            if (changed) bump();
            S.liveIds = Object.keys(live).map(function (p) { return live[p].id; });
            return true;
        };
        S.set = function (patch) { S.kit = normalize(Object.assign({}, S.kit, patch)); return S.apply(); };
        S.recentre = function () { S.at = {}; S.moved = {}; S.boxes = {}; S.recentred = true; S.measure(); var Lx = psdLayers(); kitLayers(S.kid).forEach(function (l) { var ix = Lx.indexOf(l); if (ix >= 0) Lx.splice(ix, 1); }); return S.apply(); };
        function finish(kind) {
            S.closed = true; if (SESSION === S) SESSION = null;
            refreshAll();
            try { S.onClose && S.onClose(kind); } catch (e) { warn('onClose', e); }
        }
        S.commit = function () {
            if (S.closed) return false;
            var Lx = psdLayers(), cur = stateOfKitLayers(S.kid); if (!cur.length) { return S.cancel(); }
            var curNum = S.numbersBefore ? S.numbersBefore.map(function (n) { return { layer: n.layer, img: n.layer.img }; }) : null;
            // snapshot BEFORE the kit existed, then put the live state back: ONE undo step for the whole kit
            applyKitState(S.kid, S.before, S.numbersBefore);
            call('_pushLayerStackUndo', S.mode === 'edit' ? 'edit number kit' : 'number kit');
            applyKitState(S.kid, cur, curNum);
            try { call('selectPSDLayer', cur[0].layer.id); } catch (e) {}
            S.committed = { n: cur.length, places: cur.map(function (c) { return kitOf(c.layer).place; }) };
            finish('commit');
            toast('Number ' + S.kit.number + ' placed on ' + cur.map(function (c) { return PLACE_LABEL[kitOf(c.layer).place]; }).join(', ') + '. Ctrl+Z removes the whole kit.', 'success');
            return true;
        };
        S.cancel = function () {
            if (S.closed) return false;
            applyKitState(S.kid, S.before, S.numbersBefore);
            finish('cancel'); return true;
        };
        S.remove = function () {                       // edit mode: take the whole kit off the car (one undo step)
            if (S.closed || S.mode !== 'edit') return false;
            var cur = stateOfKitLayers(S.kid);
            applyKitState(S.kid, S.before, null); call('_pushLayerStackUndo', 'remove number kit'); applyKitState(S.kid, [], null);
            finish('remove'); toast('Number Kit removed. Ctrl+Z brings it back.', 'info'); return cur.length > 0;
        };
        SESSION = S;
        S.measure();
        return S;
    }

    // ------------------------------------------------------------------ hit test (Text tool click on a kit layer opens the kit)
    function hitKit(x, y) {
        var L = psdLayers() || [], scratch = doc.createElement('canvas'); scratch.width = 11; scratch.height = 11;
        var sc = scratch.getContext('2d', { willReadFrequently: true });
        for (var i = L.length - 1; i >= 0; i--) {
            var l = L[i]; if (!l || l.visible === false || !isKitLayer(l) || !l.bbox) continue; var b = l.bbox;
            if (x < b[0] - 5 || y < b[1] - 5 || x > b[2] + 5 || y > b[3] + 5) continue;
            sc.clearRect(0, 0, 11, 11); try { sc.drawImage(l.img, b[0] - (x - 5), b[1] - (y - 5)); } catch (e) { continue; }
            var d = sc.getImageData(0, 0, 11, 11).data; for (var k = 3; k < d.length; k += 4) if (d[k] > 16) return l;
        }
        return null;
    }

    root.SpbRevNumbers = {
        version: VER, KEY: KEY, PLACES: PLACES, PLACE_LABEL: PLACE_LABEL, DEFAULTS: DEFAULTS, off: off,
        normalize: normalize, fonts: fonts, measure: measure, begin: begin, session: function () { return SESSION; },
        serialize: serialize, deserialize: deserialize, kitOf: kitOf, isKitLayer: isKitLayer, kitLayers: kitLayers, numberLayers: numberLayers, hitKit: hitKit,
        render: function (kit, tw, th, theta) { kit = normalize(kit); var S0 = fitSize(kit, tw, th), art = renderArt(kit, S0); return { canvas: turnArt(art, theta || 0), em: S0 }; },
        sideFrame: sideFrame, noseVector: function () { return noseVector(regCur()); }, templateIndex: templateIndex,
        _internal: { layoutArt: layoutArt, renderArt: renderArt, turnArt: turnArt, fitSize: fitSize, findExisting: findExisting, labelBlobs: labelBlobs, regCur: regCur, tightBox: tightBox, fitMatched: fitMatched, leanOf: leanOf, oldLean: oldLean, baseLean: baseLean }
    };
})(typeof window !== 'undefined' ? window : globalThis);
